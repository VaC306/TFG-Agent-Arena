"""Versioned synthetic datasets, isolated execution and independent result audits."""
import base64
import csv
import hashlib
import io
import json
import math
import re
from pathlib import Path

from .attachments import AttachmentUpload, prepare_attachment
from .contracts import AgentConfig, Experiment, Task
from .datasets import parse_dataset
from .evaluator import evaluate
from .export import csv_text, export_bundle
from .json_input import load_json
from .protocol import protocol_report, quality_value
from .scheduler import schedule
from .store import Store
from .worker import work

SUITES = ('text','json','attachments','orders')


def bundle_path(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('El archivo debe permanecer dentro de la batería')
    return path


def load_suite(root, suite, split):
    root = Path(root)
    if suite not in SUITES or split not in ('dev','eval'):
        raise ValueError('Suite o fase desconocida')
    if suite in ('text','json'):
        path = root/'datasets'/f'{suite}-{split}.{"csv" if suite == "text" else "jsonl"}'
        cases = parse_dataset(path.name,path.read_text(encoding='utf-8'))
        tasks = [Task.model_validate(c.task().model_dump() | {'split':split,
                    'evaluation':'exact_match' if suite == 'text' else 'json_match'}) for c in cases]
        environment = {'empty':{'orders':[]}}
    elif suite == 'orders':
        path = root/'datasets'/f'orders-{split}.jsonl'
        tasks = [Task.model_validate(load_json(line)) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
        environment = {'orders':load_json((root/'fixtures/orders.json').read_text(encoding='utf-8'))}
        for task in tasks:
            customer = re.search(r'cliente=(\w+)',task.input).group(1)
            month = re.search(r'mes=(\d{4}-\d{2})',task.input).group(1)
            included = [o for o in environment['orders']['orders'] if o['customer_id'] == customer
                        and o['status'] == 'delivered' and o['date'].startswith(month)
                        and any(l['quantity'] > l['returned_quantity'] for l in o['lines'])]
            total = sum(l['unit_cents']*(l['quantity']-l['returned_quantity']) for o in included for l in o['lines'])
            if task.criteria is None or task.criteria.total_cents != total or set(task.criteria.order_ids) != {o['id'] for o in included}:
                raise ValueError('Referencia de pedidos incoherente con el entorno')
    else:
        rows = load_json((root/'datasets'/f'attachments-{split}.json').read_text(encoding='utf-8'))
        tasks = []
        for row in rows:
            attachments = []
            for filename in row['files']:
                path = bundle_path(root,'fixtures/'+filename)
                attachments.append(prepare_attachment(AttachmentUpload(name=path.name,
                    data_base64=base64.b64encode(path.read_bytes()).decode())))
            tasks.append(Task(id=row['id'],split=split,input=row['input'],expected_answer=row['expected_answer'],
                              evaluation='json_match',environment='empty',attachments=attachments))
        environment = {'empty':{'orders':[]}}
    if not tasks or any(t.split != split for t in tasks) or len({t.id for t in tasks}) != len(tasks):
        raise ValueError('Tareas vacías, IDs duplicados o fase incorrecta')
    return tasks, environment


def validate_bundle(root):
    root = Path(root)
    manifest = load_json((root/'manifest.json').read_text(encoding='utf-8'))
    expected = manifest['sha256']
    actual_files = {p.relative_to(root).as_posix() for directory in ('datasets','fixtures','configs','diagnostics')
                    for p in (root/directory).rglob('*') if p.is_file()}
    if actual_files != set(expected):
        raise ValueError('El manifiesto no cubre exactamente los archivos de la batería')
    for name, digest in expected.items():
        if hashlib.sha256(bundle_path(root,name).read_bytes()).hexdigest() != digest:
            raise ValueError('SHA-256 distinto al manifiesto: '+name)
    ids, inputs = {}, {}
    for split in ('dev','eval'):
        tasks = [t for suite in SUITES for t in load_suite(root,suite,split)[0]]
        ids[split] = {t.id for t in tasks}
        inputs[split] = {t.input.strip() for t in tasks}
        if len(ids[split]) != len(tasks):
            raise ValueError('IDs duplicados entre suites')
    if ids['dev'] & ids['eval'] or inputs['dev'] & inputs['eval']:
        raise ValueError('Casos de desarrollo repetidos en evaluación')
    return manifest


def audit_experiment(store, eid):
    snapshot, runs = store.snapshot(eid), store.list_runs(eid)
    errors = []
    if any(r['status'] in ('queued','running') for r in runs):
        errors.append('Hay ejecuciones sin finalizar')
    tasks = {t['id']:Task.model_validate(t) for t in snapshot['tasks']}
    for run in runs:
        result = run.get('result') or {}
        events = store.events(run['id'])
        calls = [e for e in events if e['kind'] == 'tool_request']
        tool_results = [e for e in events if e['kind'] == 'tool_result']
        if result.get('tool_calls',0) != len(calls):
            errors.append(run['id']+': contador de herramientas incoherente')
        if len(calls) != len(tool_results) or result.get('tool_errors',0) != sum(bool(e['payload']['error']) for e in tool_results):
            errors.append(run['id']+': resultados o errores de herramientas incoherentes')
        for request,response in zip(calls,tool_results):
            from .tools import Tools
            arguments = request['payload']
            try:
                actual = Tools(snapshot['environments'][tasks[run['task_id']].environment]).call(arguments['name'],arguments['arguments'])
                if response['payload']['error'] or response['payload']['result'] != actual:
                    errors.append(run['id']+': herramienta distinta al recalcular')
            except Exception:
                if not response['payload']['error']:
                    errors.append(run['id']+': error de herramienta no registrado')
        if not result.get('error') and 'answer' in result:
            evaluation = evaluate(result['answer'],tasks[run['task_id']], [e['payload']['name'] for e in calls])
            if any(result.get(k) != evaluation[k] for k in ('success','format_ok','evaluation')):
                errors.append(run['id']+': evaluación distinta al recalcular')
            expected_status = 'completed' if evaluation['success'] is None else 'succeeded' if evaluation['success'] else 'failed'
            if run['status'] != expected_status:
                errors.append(run['id']+': estado no corresponde a la respuesta')
        if result.get('usage_complete'):
            responses = [e['payload']['response'] for e in events if e['kind'] == 'inference_response']
            for metric, counter in [('input_tokens','prompt_eval_count'),('output_tokens','eval_count')]:
                if result.get(metric) != sum(r.get(counter,0) for r in responses):
                    errors.append(run['id']+': contador de tokens incoherente')
            duration = sum(r.get('eval_duration',0) for r in responses)/1e9
            if not math.isclose(result.get('server_eval_s',0),duration,rel_tol=1e-9,abs_tol=1e-9):
                errors.append(run['id']+': duración de generación incoherente')
    rows = list(csv.DictReader(io.StringIO(csv_text(store,eid))))
    if len(rows) != len(runs):
        errors.append('Número de filas del CSV distinto de las ejecuciones')
    for row,run in zip(rows,runs):
        value = quality_value(run)
        if row['id'] != run['id'] or row['success'] != ('' if value is None else str(value)):
            errors.append('Puntuación CSV incoherente: '+run['id'])
    report = protocol_report(snapshot,runs)
    for branch in ('A','B'):
        selected = [r for r in runs if r['branch'] == branch]
        scored = [quality_value(r) for r in selected if quality_value(r) is not None]
        if report['branches'][branch]['correct'] != sum(scored) or report['branches'][branch]['evaluated'] != len(scored):
            errors.append('Resumen de rama incoherente: '+branch)
    return {'passed':not errors,'errors':errors,'runs':len(runs),'report':report}


async def run_benchmark(root, output, model_a, model_b, split='dev', suites=SUITES, repetitions=1):
    root, output = Path(root), Path(output)
    manifest = validate_bundle(root)
    if output.resolve().is_relative_to(root.resolve()):
        raise ValueError('Guarda los resultados fuera de la batería versionada')
    if not 1 <= repetitions <= 10:
        raise ValueError('Entre 1 y 10 repeticiones')
    profile = load_json((root/'configs/protocol.json').read_text(encoding='utf-8'))
    settings = profile['settings']
    # Validate settings and all cases before starting a model or creating output.
    config_agents = {b:AgentConfig(model=m,system_prompt=profile['prompts']['text'],
        temperature=settings['temperature'],seed=settings['seed'],num_ctx=settings['num_ctx'],
        limits={k:v for k,v in settings.items() if k in ('timeout_s','max_calls','max_tool_calls','max_output_tokens')})
        for b,m in [('A',model_a),('B',model_b)]}
    config = Experiment(name='benchmark',adapter='ollama',agents=config_agents,
        comparison='same_model' if model_a == model_b else 'different_models',repetitions=repetitions,split=split,order_seed=profile['order_seed'])
    loaded = {suite:load_suite(root,suite,split) for suite in suites}
    from .adapters import Ollama
    adapter = Ollama(config.ollama_url)
    for model in set((model_a,model_b)):
        await adapter.metadata(model)
    output.mkdir(parents=True,exist_ok=False)
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    store = Store(output/'arena.sqlite')
    results = []
    for suite,(tasks,environments) in loaded.items():
        for agent in config.agents.values():
            agent.system_prompt = profile['prompts'][suite]
            agent.tools_enabled = suite == 'orders'
        config.name = f'{manifest["version"]} {suite} {split}'
        eid = schedule(store,config,tasks,environments,benchmark={'version':manifest['version'],'suite':suite,
            'split':split,'manifest_sha256':hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest()})
        print(f'RUNNING {suite} {split} {eid}',flush=True)
        await work(store,once=True)
        audit = audit_experiment(store,eid)
        export_bundle(store,eid,output/suite)
        (output/suite/'audit.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False),encoding='utf-8')
        results.append({'suite':suite,'experiment_id':eid,'audit_passed':audit['passed'],'report':audit['report']})
        (output/'report.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
        print(f'FINISHED {suite}: audit={audit["passed"]} branches={audit["report"]["branches"]}',flush=True)
        if not audit['passed']:
            raise ValueError('Resultados incoherentes: '+str(audit['errors']))
    return results
