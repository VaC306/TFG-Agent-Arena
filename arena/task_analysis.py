"""Descriptive task stability and conservative, task-clustered paired inference."""
import csv
import io
import json
import math
import hashlib
import platform
from pathlib import Path
import numpy as np
import scipy
from scipy.stats import bootstrap
from .model_results import evaluable, fingerprint, outcome, summarize
from .protocol import quality_value, protocol_report
from .latency_analysis import latency_analysis

VERSION = 'arena-task-analysis-v2'
MIN_TASKS = 10
MIN_ATTEMPTS = 2
RESAMPLES = 4000
SEED = 42
SOURCES = {name:(Path(__file__).parent/name).read_bytes().decode('utf-8')
           for name in ('task_analysis.py','model_results.py','protocol.py','latency_analysis.py')}
SOURCE_HASHES = {name:hashlib.sha256(source.encode('utf-8')).hexdigest() for name,source in SOURCES.items()}


def branch_tasks(snapshot,branch):
    return [snapshot['branch_tasks'][branch]] if snapshot.get('branch_tasks') else snapshot['tasks']


def complete_run_plan(snapshot,runs):
    expected = {(t['id'],b,r) for b in ('A','B') for t in branch_tasks(snapshot,b)
                for r in range(snapshot['config']['repetitions'])}
    actual = [(r['task_id'],r['branch'],r['repetition']) for r in runs]
    return bool(expected) and len(actual) == len(expected) and set(actual) == expected


def ratio(numerator,denominator):
    return numerator/denominator if denominator else None


def task_branch(task,branch,included):
    series, collected = [],[]
    for attempt,evidence in included if task else []:
        runs = [r for r in evidence['runs'] if task and r['task_id'] == task['id'] and r['branch'] == branch]
        collected.extend(runs)
        summary = summarize(runs,[task] if task else [])
        series.append({'sequence':attempt['sequence'],'experiment_id':attempt['experiment_id'],
                       'summary':summary,'quality_rate':ratio(summary['correct'],summary['evaluated']),
                       'outcomes':[outcome(r) for r in sorted(runs,key=lambda r:r['repetition'])]})
    summary = summarize(collected,[task] if task else [])
    scored = summary['evaluated']
    stability = ('insufficient' if scored < 2 else 'variable' if 0 < summary['correct'] < scored
                 else 'always_correct' if summary['correct'] == scored else 'always_incorrect')
    # Compare entire per-repetition outcome vectors between successive included attempts.
    # This detects error/format changes even when their correctness rate is identical.
    changes = sum(a['outcomes'] != b['outcomes'] for a,b in zip(series,series[1:]))
    return {'present':task is not None,'reference_evaluable':evaluable(task) if task else False,
            'input_preview':task['input'][:160] if task else '', 'summary':summary,
            'quality_rate':ratio(summary['correct'],scored),
            'coverage':ratio(scored,summary['planned_evaluable']),
            'correct_reference_rate':ratio(summary['correct'],summary['planned_evaluable']),
            'quality_stability':stability,'between_attempt_changes':changes,
            'between_attempt_comparisons':max(0,len(series)-1),'series':series}


def paired_analysis(snapshot,included,excluded):
    shared = not snapshot.get('branch_tasks') and snapshot.get('conditions',{}).get('inputs_shared',True)
    tasks = [t for t in snapshot['tasks'] if evaluable(t)] if shared else []
    counts = {k:0 for k in ('planned_pairs','evaluated_pairs','both_correct','A_only_correct','B_only_correct','both_incorrect','missing_pairs')}
    deltas = []
    for task in tasks:
        differences = []
        expected = len(included)*snapshot['config']['repetitions']
        for _,evidence in included:
            runs = {(r['branch'],r['repetition']):r for r in evidence['runs'] if r['task_id'] == task['id']}
            for repetition in range(snapshot['config']['repetitions']):
                counts['planned_pairs'] += 1
                a,b = (quality_value(runs[(branch,repetition)]) for branch in ('A','B'))
                if a is None or b is None:
                    counts['missing_pairs'] += 1
                    continue
                counts['evaluated_pairs'] += 1
                counts['both_correct' if a and b else 'A_only_correct' if a else 'B_only_correct' if b else 'both_incorrect'] += 1
                differences.append(int(b)-int(a))
        if expected and len(differences) == expected:
            deltas.append({'task_id':task['id'],'B_minus_A':sum(differences)/len(differences)})
    complete = bool(counts['planned_pairs']) and counts['missing_pairs'] == 0
    mean = sum(d['B_minus_A'] for d in deltas)/len(deltas) if complete else None
    scope = protocol_report(snapshot,included[0][1]['runs'] if included else [])['comparison_scope']
    reasons = []
    if not shared: reasons.append('A y B usan entradas independientes; no se emparejan por ID.')
    if not included: reasons.append('No hay intentos terminados con condiciones compatibles.')
    if snapshot['config']['adapter'] == 'simulated': reasons.append('Simulación: no se calcula incertidumbre sobre calidad de modelos reales.')
    if snapshot['config']['split'] != 'eval': reasons.append('Fase de desarrollo: el intervalo se reserva a campañas etiquetadas como evaluación.')
    if not tasks: reasons.append('No hay tareas compartidas con referencia evaluable.')
    if counts['missing_pairs']: reasons.append('Faltan puntuaciones en pares A/B; errores de ejecución no se imputan como calidad incorrecta.')
    if excluded: reasons.append('Hay intentos excluidos o pendientes; el intervalo requiere una campaña completa y homogénea.')
    latency_plan = snapshot.get('conditions',{}).get('latency_plan')
    if latency_plan and len(included)!=latency_plan['planned_attempts']:
        reasons.append('El estudio todavía no tiene todos los intentos fijados en su plan; no se presenta inferencia intermedia.')
    if len(included) < MIN_ATTEMPTS: reasons.append(f'Se requieren al menos {MIN_ATTEMPTS} intentos compatibles para este análisis de incertidumbre.')
    if len(tasks) < MIN_TASKS: reasons.append(f'Se requieren al menos {MIN_TASKS} tareas con referencia; repetir una tarea no aumenta este número.')
    stimuli = [fingerprint({'input':t['input'].strip(),'environment':snapshot['environments'].get(t['environment']),
                           'attachments':[(f['sha256'],f['name']) for f in t.get('attachments',[])]}) for t in tasks]
    if len(set(stimuli)) != len(stimuli): reasons.append('Hay entradas duplicadas bajo distintos IDs; no se asume que sean tareas independientes.')
    if deltas and len({d['B_minus_A'] for d in deltas}) == 1:
        reasons.append('Las diferencias por tarea son constantes; un intervalo degenerado daría una impresión falsa de precisión.')
    interval = None
    if not reasons and complete:
        values = np.array([d['B_minus_A'] for d in deltas],dtype=float)
        result = bootstrap((values,),np.mean,method='BCa',confidence_level=.95,n_resamples=RESAMPLES,
                           batch=256,rng=np.random.default_rng(SEED))
        low,high = float(result.confidence_interval.low),float(result.confidence_interval.high)
        if math.isfinite(low) and math.isfinite(high): interval = {'low':low,'high':high}
        else: reasons.append('El remuestreo no produjo límites finitos; no se presenta un intervalo.')
    return {'inputs_shared':shared,'scope':scope,**counts,'complete':complete,
            'coverage':ratio(counts['evaluated_pairs'],counts['planned_pairs']),
            'task_count':len(tasks),'task_differences':deltas,'mean_B_minus_A':mean,
            'interval':interval,'interval_unavailable_reasons':reasons,
            'method':{'name':'task_cluster_bootstrap_BCa','confidence_level':.95,'resamples':RESAMPLES,'seed':SEED,
                      'unit':'task','min_tasks':MIN_TASKS,'min_attempts':MIN_ATTEMPTS,
                      'required_split':'eval','python_version':platform.python_version(),
                      'numpy_version':np.__version__,'scipy_version':scipy.__version__,
                      'input_sha256':fingerprint(deltas)},
            'note':('B−A es la media de diferencias por tarea con el mismo peso para cada caso. '
                    'Los pares y cambios son descriptivos, no observaciones independientes. '
                    'El intervalo remuestrea tareas completas, conservando agrupadas todas sus repeticiones e intentos. '
                    'Supone tareas independientes y representativas: IDs distintos no prueban ese supuesto. '
                    'El mínimo de tareas/intentos es una política conservadora de la aplicación, no una garantía estadística. '
                    'No se declara un ganador ni se generaliza a otros datasets o máquinas.')}


def campaign_analysis(snapshot,attempts,evidence):
    included,excluded = [],[]
    for attempt,item in zip(attempts,evidence):
        reasons = list(attempt['warnings'])
        if not complete_run_plan(snapshot,item['runs']): reasons.append('El plan de ejecuciones contiene casos ausentes o repetidos.')
        if attempt['complete'] and attempt['compatible'] and not reasons: included.append((attempt,item))
        else: excluded.append({'sequence':attempt['sequence'],'experiment_id':attempt['experiment_id'],'reasons':reasons})
    task_maps = {b:{t['id']:t for t in branch_tasks(snapshot,b)} for b in ('A','B')}
    ids = list(dict.fromkeys(t['id'] for b in ('A','B') for t in branch_tasks(snapshot,b)))
    rows = [{'task_id':tid,'branches':{b:task_branch(task_maps[b].get(tid),b,included) for b in ('A','B')}} for tid in ids]
    return {'version':VERSION,'source_sha256':SOURCE_HASHES,'included_attempts':[{'sequence':a['sequence'],'experiment_id':a['experiment_id']} for a,_ in included],
            'excluded_attempts':excluded,'tasks':rows,'paired':paired_analysis(snapshot,included,excluded),
            'latency':latency_analysis(snapshot,included,excluded),
            'note':('Los contadores por tarea describen solo intentos terminados con condiciones compatibles. '
                    'Calidad = aciertos/respuestas evaluadas; cobertura = evaluadas/casos con referencia evaluable. '
                    'Los errores quedan separados. Estabilidad de calidad no significa respuestas idénticas. '
                    'Cambios entre intentos compara los estados de cada repetición entre intentos consecutivos incluidos.')}


def task_analysis_csv(report):
    fields = ['campaign_id','analysis_version','design_sha256','task_id','branch','present','reference_evaluable','input_preview',
              'included_attempts','excluded_attempts','total','finished','planned_evaluable','evaluated','correct','incorrect',
              'invalid_format','execution_errors','unscored','pending','mean_answer_s','timed_answers',
              'quality_rate','coverage','correct_reference_rate','quality_stability','between_attempt_changes','between_attempt_comparisons','series']
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output,fieldnames=fields)
    writer.writeheader()
    analysis = report['analysis']
    for task in analysis['tasks']:
        for branch,values in task['branches'].items():
            row = {'campaign_id':report['id'],'analysis_version':analysis['version'],'design_sha256':report['design_sha256'],
                   'task_id':task['task_id'],'branch':branch,'included_attempts':len(analysis['included_attempts']),
                   'excluded_attempts':len(analysis['excluded_attempts']),**values,**values['summary']}
            row.pop('summary')
            row['series'] = json.dumps(row['series'],ensure_ascii=False)
            writer.writerow({k:"'"+str(row[k]) if isinstance(row[k],str) and row[k].lstrip().startswith(('=','+','-','@')) else row[k] for k in fields})
    return output.getvalue()
