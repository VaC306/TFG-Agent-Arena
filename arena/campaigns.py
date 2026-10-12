"""Frozen experiment designs and distinct, account-owned attempts."""
import csv
import io
import json
import uuid
from typing import Literal
from pydantic import Field, field_validator
from .contracts import Contract, Experiment, Task
from .model_results import fingerprint, summarize
from .scheduler import schedule
from .result_report import code_block
from .resources import measurement_records
from .task_analysis import campaign_analysis, task_analysis_csv, SOURCES as ANALYSIS_SOURCES


class CampaignRequest(Contract):
    name: str = Field(min_length=1,max_length=120)
    experiment_id: str = Field(min_length=1,max_length=100)

    @field_validator('name')
    @classmethod
    def nonblank(cls,value):
        if not value.strip():
            raise ValueError('Escribe un nombre para la campaña')
        return value.strip()


class AttemptRequest(Contract):
    request_id: uuid.UUID


class AnnotationRequest(Contract):
    request_id: uuid.UUID
    kind: Literal['observation','deviation'] = 'deviation'
    text: str = Field(min_length=1,max_length=2000)

    @field_validator('text')
    @classmethod
    def nonblank(cls,value):
        if not value.strip():
            raise ValueError('Describe las condiciones observadas')
        return value.strip()


def observed_models(runs, adapter):
    models = {}
    if adapter == 'simulated':
        return models
    for branch in ('A','B'):
        selected = [r for r in runs if r['branch'] == branch]
        identities = [(r.get('result') or {}).get('inference_identity') for r in selected]
        if not identities or not all(i and i.get('verified') and i.get('fingerprint') for i in identities):
            raise ValueError('La campaña real necesita identidades verificadas en todas las ejecuciones de A y B.')
        if len({i['fingerprint'] for i in identities}) != 1:
            raise ValueError('Hay versiones de modelo distintas en la comparación de origen.')
        models[branch] = identities[0]
    return models


def frozen_design(snapshot):
    return {k:snapshot.get(k) for k in ('config','tasks','branch_tasks','environments','conditions','protocol','benchmark')}


def create_campaign(store, request):
    snapshot, runs = store.snapshot(request.experiment_id), store.list_runs(request.experiment_id)
    if not runs or any(r['status'] in ('queued','running') for r in runs):
        raise ValueError('Finaliza o cancela la comparación antes de crear una campaña.')
    if not (snapshot.get('protocol') or {}).get('evaluator_version') or not snapshot.get('conditions'):
        raise ValueError('La comparación antigua no registra un protocolo completo. Ejecuta una comparación nueva.')
    data = {'snapshot':snapshot, 'design_sha256':fingerprint(frozen_design(snapshot)),
            'expected_models':observed_models(runs,snapshot['config']['adapter'])}
    return store.create_campaign(str(uuid.uuid4()),request.name,request.experiment_id,data)


def repeat_campaign(store, campaign_id, request_id):
    data = store.campaign(campaign_id)['data']
    snapshot = data['snapshot']
    config = Experiment.model_validate(snapshot['config'])
    tasks = [Task.model_validate(t) for t in snapshot['tasks']]
    # Endpoint, inputs, prompts and limits come from the frozen design, not current UI preferences or env vars.
    return schedule(store,config,tasks,snapshot['environments'],snapshot.get('branch_tasks'),snapshot.get('benchmark'),
                    campaign={'id':campaign_id,'design_sha256':data['design_sha256'],
                              'expected_models':data['expected_models'],'request_id':str(request_id)},
                    conditions=snapshot['conditions'])


def host_conditions(snapshot):
    host = snapshot.get('host') or {}
    result = {k:host.get(k) for k in ('platform','python','cpu','logical_cpus','ram_total_bytes','packages')}
    gpu = (host.get('resources') or {}).get('gpu')
    result['gpu'] = [{k:g.get(k) for k in ('index','name','total_bytes')} for g in gpu] if gpu is not None else None
    return result


def attempt_report(store, attempt, data, snapshot=None, runs=None):
    snapshot = store.snapshot(attempt['experiment_id']) if snapshot is None else snapshot
    runs = store.list_runs(attempt['experiment_id']) if runs is None else runs
    baseline = data['snapshot']
    warnings = []
    annotations = store.annotations(attempt['experiment_id'])
    if any(a['kind'] == 'deviation' for a in annotations):
        warnings.append('Diferencia de condiciones externas declarada por el operador; intento excluido del análisis compatible.')
    if fingerprint(frozen_design(snapshot)) != data['design_sha256']:
        warnings.append('Diseño distinto: configuración, datos, evaluación o condiciones.')
    if snapshot.get('source_sha256') != baseline.get('source_sha256'):
        warnings.append('Versión del código distinta de la comparación de origen.')
    if host_conditions(snapshot) != host_conditions(baseline):
        warnings.append('Equipo o dependencias distintos de la comparación de origen.')
    summaries = {b:summarize([r for r in runs if r['branch'] == b],
                            [snapshot['branch_tasks'][b]] if snapshot.get('branch_tasks') else snapshot['tasks']) for b in ('A','B')}
    pending = sum(s['pending'] for s in summaries.values())
    if pending:
        warnings.append('Resultado parcial: quedan ejecuciones pendientes.')
    if not pending:
        try:
            if observed_models(runs,snapshot['config']['adapter']) != data['expected_models']:
                warnings.append('Identidad del modelo o servidor distinta de la campaña.')
        except ValueError:
            warnings.append('No se pudo verificar la identidad de todos los modelos.')
    versions = {(r.get('result') or {}).get('evaluator_version') for r in runs if (r.get('result') or {}).get('answer')}
    if versions and versions != {baseline['protocol']['evaluator_version']}:
        warnings.append('Versión del evaluador distinta de la campaña.')
    return attempt | {'created_at':min(r['queued_at'] for r in runs),'complete':pending == 0,
                      'compatible':not warnings,'warnings':warnings,'overviews':summaries,
                      'annotations':annotations,
                      'measurements':measurement_records(runs),
                      'data_sha256':snapshot.get('data_sha256'),'source_sha256':snapshot.get('source_sha256')}


def campaign_report(store,campaign_id, include_evidence=False):
    campaign = store.campaign(campaign_id)
    data = campaign.pop('data')
    # Read each attempt's runs once: a worker finishing during export must not make
    # the summary and the embedded evidence describe different states.
    evidence = [{'experiment_id':a['experiment_id'],'snapshot':store.snapshot(a['experiment_id']),
                 'runs':store.list_runs(a['experiment_id'])} for a in campaign['attempts']]
    campaign['attempts'] = [attempt_report(store,a,data,e['snapshot'],e['runs']) for a,e in zip(campaign['attempts'],evidence)]
    snapshot = data['snapshot']
    campaign['design_sha256'] = data['design_sha256']
    campaign['design'] = frozen_design(snapshot)
    campaign['expected_models'] = data['expected_models']
    campaign['case_count'] = len(snapshot['tasks'])
    campaign['pending'] = sum(s['pending'] for a in campaign['attempts'] for s in a['overviews'].values())
    campaign['analysis'] = campaign_analysis(snapshot,campaign['attempts'],evidence)
    campaign['note'] = ('Cada intento conserva sus propias métricas. No se mezcla evidencia incompatible ni se declara un ganador. '
                        'Las repeticiones de un caso no son observaciones independientes. '
                        'Código y equipo pueden cambiar; las diferencias se indican. Semilla fija no garantiza respuestas idénticas.')
    if snapshot['config']['adapter'] == 'simulated':
        campaign['note'] += ' Simulación de plataforma: no mide calidad ni velocidad de modelos reales.'
    agents = snapshot['config']['agents']
    if snapshot.get('branch_tasks') or snapshot.get('conditions',{}).get('inputs_shared') is False:
        campaign['note'] += ' A y B reciben entradas independientes; sus diferencias no se atribuyen solo al modelo o al prompt.'
    if agents['A']['system_prompt'] != agents['B']['system_prompt']:
        campaign['note'] += ' Los prompts A y B son distintos: se comparan configuraciones.'
    if any(agents['A'].get(k) != agents['B'].get(k) for k in ('temperature','seed','num_ctx','limits','tools_enabled')):
        campaign['note'] += ' Los parámetros de A y B son distintos.'
    if include_evidence:
        campaign['baseline_snapshot'] = snapshot
        campaign['evidence'] = evidence
        campaign['analysis_sources'] = ANALYSIS_SOURCES
    return campaign


def campaign_csv(report):
    output = io.StringIO(newline='')
    fields = ['campaign_id','design_sha256','attempt','experiment_id','branch','complete','compatible','warnings','annotations','measurements',
              'total','finished','planned_evaluable','evaluated','correct','incorrect','invalid_format','execution_errors',
              'unscored','pending','mean_answer_s','timed_answers']
    writer = csv.DictWriter(output,fieldnames=fields)
    writer.writeheader()
    for attempt in report['attempts']:
        for branch,summary in attempt['overviews'].items():
            writer.writerow({'campaign_id':report['id'],'design_sha256':report['design_sha256'],'attempt':attempt['sequence'],
                'experiment_id':attempt['experiment_id'],'branch':branch,'complete':attempt['complete'],
                'compatible':attempt['compatible'],'warnings':' · '.join(attempt['warnings']),
                'annotations':json.dumps(attempt['annotations'],ensure_ascii=False),
                'measurements':json.dumps([m for m in attempt['measurements'] if m['branch']==branch],ensure_ascii=False),**summary})
    return output.getvalue()


def campaign_markdown(report):
    lines = ['# Campaña experimental',code_block(report['name']),code_block(report['id']),report['note'],
             '## Diseño fijado',code_block(json.dumps(report['design'],ensure_ascii=False,indent=2)),
             'SHA-256 del diseño: '+report['design_sha256'],
             '## Modelos fijados',code_block(json.dumps(report['expected_models'],ensure_ascii=False,indent=2))]
    for attempt in report['attempts']:
        lines += [f"## Intento {attempt['sequence']}",code_block(attempt['experiment_id']),
                  'Condiciones registradas compatibles.' if attempt['compatible'] else ' · '.join(attempt['warnings'])]
        lines += ['### Anotaciones del operador (no son mediciones automáticas)',code_block(json.dumps(attempt['annotations'],ensure_ascii=False,indent=2))]
        lines += ['### Tiempos separados y recursos observados',code_block(json.dumps(attempt['measurements'],ensure_ascii=False,indent=2))]
        for branch,s in attempt['overviews'].items():
            lines += [f"### Variante {branch}",f"Aciertos: {s['correct']}/{s['planned_evaluable']} casos con referencia evaluable." if s['planned_evaluable'] else 'Sin casos con referencia evaluable.',
                      code_block(json.dumps(s,ensure_ascii=False,indent=2))]
    analysis = report['analysis']
    lines += ['## Análisis por tarea y estabilidad',analysis['note'],
              '### Intentos incluidos',code_block(json.dumps(analysis['included_attempts'],ensure_ascii=False,indent=2)),
              '### Intentos excluidos',code_block(json.dumps(analysis['excluded_attempts'],ensure_ascii=False,indent=2))]
    for task in analysis['tasks']:
        lines += ['### Tarea',code_block(task['task_id'])]
        for branch,values in task['branches'].items():
            lines += [f'#### Variante {branch}',code_block(json.dumps(values,ensure_ascii=False,indent=2))]
    lines += ['## Diferencias emparejadas e incertidumbre',analysis['paired']['note'],
              code_block(json.dumps(analysis['paired'],ensure_ascii=False,indent=2)),
              'El JSON de la campaña conserva las fuentes, entradas y resultados de cada intento. Las trazas se consultan en cada comparación.']
    return '\n\n'.join(lines)+'\n'
