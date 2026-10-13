"""Rebuild a reviewed, allowlisted static selection. Never reads runtime or a DB."""
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from arena.model_results import summarize, fingerprint
from demo_showcase import build_showcase

OUT = ROOT / 'frontend/demo-assets/demo'
SOURCES = {}
LF_NORMALIZED_SOURCES = {
    'experiments/simulated-dev-final-2026-10-08/' + name
    for name in ('snapshot.json', 'runs.json', 'events.jsonl')
}
NOTE = ('Resultados guardados del 12/10/2026. Muestras pequeñas y exploratorias; '
        'sin ranking ni conclusión de superioridad. A/B secuenciales, sin aislamiento del host; '
        'tiempo total puede incluir carga y preparación. Semilla fija no garantiza determinismo. '
        'No se publican fuentes, entornos, adjuntos binarios ni trazas completas del worker.')


def read(relative):
    path = ROOT / relative
    raw = path.read_bytes()
    # These historical files were tracked as Git text before immutable evidence
    # rules existed. Record canonical LF provenance without changing originals.
    digest = hashlib.sha256(raw.replace(b'\r\n', b'\n') if relative in LF_NORMALIZED_SOURCES else raw).hexdigest()
    if relative.startswith(('benchmarks/v1/datasets/', 'benchmarks/v1/fixtures/')):
        manifest = json.loads((ROOT / 'benchmarks/v1/results/2026-10-12/manifest.json').read_text(encoding='utf-8'))
        if digest != manifest['sha256'][relative.removeprefix('benchmarks/v1/')]:
            raise ValueError(f'Dataset no longer matches the saved evidence: {relative}')
    if relative.startswith('experiments/local-flow-2026-10-12/') and relative.endswith('reproducibility.json'):
        manifest = json.loads((ROOT / 'experiments/local-flow-2026-10-12/manifest.json').read_text(encoding='utf-8'))
        if digest != manifest[Path(relative).name]:
            raise ValueError(f'Original evidence checksum changed: {relative}')
    SOURCES[relative] = digest
    return raw.decode('utf-8')


def pick(value, keys):
    return {key: value[key] for key in keys.split() if key in value}


def tasks_for(suite, split):
    base = f'benchmarks/v1/datasets/{suite}-{split}'
    if suite == 'text':
        tasks = list(csv.DictReader(io.StringIO(read(base + '.csv'))))
    elif suite == 'attachments':
        tasks = json.loads(read(base + '.json'))
    else:
        tasks = [json.loads(line) for line in read(base + '.jsonl').splitlines() if line]
    for task in tasks:
        task['evaluation'] = 'order_benchmark' if suite == 'orders' else 'exact_match' if suite == 'text' else 'json_match'
    return tasks


def config_for(config):
    result = pick(config, 'name adapter split repetitions comparison')
    result['agents'] = {b: pick(a, 'model system_prompt temperature seed num_ctx limits') for b, a in config['agents'].items()}
    for agent in result['agents'].values():
        agent['limits'] = pick(agent.get('limits', {}), 'max_output_tokens timeout_s')
    return result


def save(path, value):
    target = OUT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2) + '\n' if not isinstance(value, str) else value
    # Fail closed even for free text in otherwise allowlisted fields.
    if re.search(r'(?i)(localhost|127\.0\.0\.1|(?<![a-z])[A-Z]:[\\/]|/Users/|/home/|@(?:ucm|gmail)\.|sk-[a-z0-9]{12}|password_hash|data_base64|cookie|authorization|ollama_url)', text):
        raise ValueError(f'Potential private content in {path}; review selection before publishing')
    target.write_text(text, encoding='utf-8', newline='')


def main():
    experiments, details, library = [], {}, []
    selection = []
    for split in ('dev', 'eval'):
        for suite in ('text', 'json', 'orders', 'attachments'):
            source = f'benchmarks/v1/results/2026-10-12/{split}/{suite}.json'
            data = json.loads(read(source))
            selection.append((source, data, {'config': data['config'], 'tasks': tasks_for(suite, split), 'conditions': data['conditions'], 'data_sha256': data['data_sha256']}, suite))
    for prefix in ('', 'simulated-'):
        source = f'experiments/local-flow-2026-10-12/{prefix}reproducibility.json'
        data = json.loads(read(source))
        selection.append((source, data, data['snapshot'], 'text'))
    for source, data, snapshot, suite in selection:
        eid = data['experiment_id']
        tasks = [pick(t, 'id input expected_answer evaluation criteria') for t in snapshot['tasks']]
        runs = []
        for r in data['runs']:
            run = pick(r, 'id task_id branch repetition status')
            run['result'] = pick(r.get('result') or {}, 'success format_ok agent_s queue_s input_tokens output_tokens usage_complete tool_calls tool_errors server_tps error answer reason')
            runs.append(run)
        config = config_for(snapshot['config'])
        protocol = pick(data['report'], 'version evaluator_version comparison_scope inputs_shared prompts_equal evaluations warnings branches')
        protocol['models'] = {b: pick(m, 'digest server_version quantization verified') for b, m in data['report'].get('models', {}).items()}
        protocol['warnings'] = protocol.get('warnings', []) + [NOTE]
        if suite == 'attachments':
            protocol['warnings'].append('Los adjuntos originales no se incluyen. La entrada visible no contiene todo el contexto usado por el modelo.')
        detail = {'snapshot': {'config': config, 'tasks': tasks, 'conditions': pick(snapshot['conditions'], 'inputs_shared'), 'data_sha256': snapshot.get('data_sha256')},
                  'runs': runs, 'protocol': protocol,
                  'overviews': {b: summarize([r for r in runs if r['branch'] == b], tasks) for b in ('A', 'B')}}
        detail['selection'] = {'source': source, 'sha256': SOURCES[source], 'note': NOTE,
                               'summary_policy': 'Recomputed with current backend outcome semantics; cancellations separated from execution errors.'}
        details[eid] = detail
        timestamp = max(r.get('queued_at', 0) for r in data['runs'])
        experiments.append({'id': eid, 'name': config['name'], 'adapter': config['adapter'], 'split': config['split'], 'created_at': timestamp, 'total': len(runs), 'completed': sum(r['status'] not in ('queued', 'running') for r in runs)})
        for b in ('A', 'B'):
            agent = config['agents'][b]
            identity = protocol['models'].get(b, {})
            conditions = {**pick(agent, 'system_prompt temperature seed num_ctx limits'), **pick(identity, 'server_version quantization'), 'data_sha256': snapshot.get('data_sha256'), 'evaluator_versions': [protocol['evaluator_version']]}
            # Do not infer cross-export cohort equivalence after removing infrastructure metadata.
            library.append({'id': eid + '-' + b, 'model': agent['model'], 'adapter': config['adapter'], 'digest': identity.get('digest'), 'verified': identity.get('verified', False), 'kind': ('order_benchmark' if suite == 'orders' else 'json_match' if suite in ('json', 'attachments') else 'exact_match') + (':files' if suite == 'attachments' else ':text'), 'experiment_id': eid, 'experiment_name': config['name'], 'branch': b, 'updated_at': timestamp, 'split': config['split'], 'repetitions': config['repetitions'], 'summary': detail['overviews'][b], 'cohort_key': fingerprint({'experiment': eid, 'prompt': agent['system_prompt'], 'parameters': pick(agent, 'temperature seed num_ctx limits')}), 'conditions': conditions})
        save(f'exports/{eid}/reproducibility.json', detail)
        fields = ['task_id', 'branch', 'repetition', 'status', 'success', 'format_ok', 'agent_s', 'input_tokens', 'output_tokens', 'tool_calls', 'error', 'answer']
        output = io.StringIO(newline='')
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for run in runs:
            row = {**run, **run['result']}
            writer.writerow({k: "'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v for k, v in row.items() if k in fields})
        save(f'exports/{eid}/metrics.csv', output.getvalue())
        save(f'exports/{eid}/report.md', f"# {config['name']}\n\n{NOTE}\n\nTipo: {config['adapter']}.\n\n" + '\n'.join(f"- Rama {b}: {s['correct']}/{s['evaluated']} respuestas evaluadas correctas; {s['execution_errors']} errores; {s['cancelled']} canceladas; tiempo medio {s['mean_answer_s']} s ({s['timed_answers']} respuestas)." for b, s in detail['overviews'].items()) + '\n')
    diagnostic = json.loads(read('benchmarks/v1/results/2026-10-12/tool-diagnostics.json'))
    probes = []
    for p in diagnostic['probes']:
        probe = pick(p, 'model case condition assessment continuation_correct elapsed_s')
        # Real saved request/response messages on synthetic fixtures; no fabricated worker events.
        for key in ('request', 'response', 'continuation_request', 'continuation_response'):
            if p.get(key): probe[key] = pick(p[key], 'messages message options done_reason prompt_eval_count eval_count')
        probes.append(probe)
    save('diagnostics.json', {'note': 'Inferencias reales con fixtures sintéticos de desarrollo; una observación por condición. No son un ranking ni una traza completa del worker.', 'probes': probes})
    save('catalog.json', {'experiments': experiments, 'details': details, 'entries': library, 'campaigns': [], 'note': NOTE})
    build_showcase(read, pick, save, details)
    save('manifest.json', {'schema': 2, 'sources': SOURCES, 'lf_normalized_sources': sorted(LF_NORMALIZED_SOURCES), 'selection': '10 comparisons, saved terminal runs; diagnostics; synthetic text fixtures; one selected simulated replay. No runtime or database.', 'omissions': ['host', 'source code', 'full environments', 'binary attachments', 'full worker traces', 'campaigns (not exported)'], 'note': NOTE})
    print(f'Generated {len(experiments)} comparisons, {sum(len(d["runs"]) for d in details.values())} runs, {len(probes)} diagnostic probes in {OUT}')


if __name__ == '__main__':
    main()
