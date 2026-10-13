"""Frozen latency estimand; paired task clusters, coverage and execution order."""
import csv
import io
import json
import math
import platform
import numpy as np
import scipy
from scipy.stats import bootstrap
from .model_results import fingerprint, outcome
from .protocol import protocol_report, quality_value

VERSION = 'arena-latency-analysis-v1'


def finite(value):
    return type(value) in (int,float) and math.isfinite(value) and value >= 0


def task_time(run):
    result = run.get('result') or {}
    return result.get('task_s') if outcome(run) not in ('execution_error','cancelled','pending') and 'answer' in result and finite(result.get('task_s')) and finite(result.get('agent_s')) and result['task_s']<=result['agent_s'] else None


def latency_analysis(snapshot,included,excluded):
    plan = snapshot.get('conditions',{}).get('latency_plan')
    shared = not snapshot.get('branch_tasks') and snapshot.get('conditions',{}).get('inputs_shared',True)
    rows, tasks, unbalanced = [],[],[]
    for task in snapshot['tasks'] if shared else []:
        observed = []
        for attempt,item in included:
            by_key = {(r['branch'],r['repetition']):r for r in item['runs'] if r['task_id']==task['id']}
            orders = []
            for repetition in range(snapshot['config']['repetitions']):
                a,b = (by_key[(branch,repetition)] for branch in ('A','B'))
                first = ('A' if a['position']<b['position'] else 'B') if type(a.get('position')) is int and type(b.get('position')) is int and a['position']!=b['position'] else None
                earlier,later = (a,b) if first=='A' else (b,a)
                sequential = first is not None and all(finite(r.get(k)) for r in (a,b) for k in ('started_at','finished_at')) and all(r['finished_at']>=r['started_at'] for r in (a,b)) and earlier['finished_at']<=later['started_at']
                ta,tb = task_time(a),task_time(b)
                valid = ta is not None and tb is not None
                orders.append(first)
                row = {'task_id':task['id'],'attempt':attempt['sequence'],'experiment_id':attempt['experiment_id'],
                       'repetition':repetition,'A_run_id':a['id'],'B_run_id':b['id'],'first':first,'sequential_verified':sequential,
                       'A_status':a['status'],'B_status':b['status'],'A_quality':quality_value(a),'B_quality':quality_value(b),
                       'A_task_s':ta,'B_task_s':tb,'B_minus_A_s':tb-ta if valid else None,
                       'A_agent_s':(a.get('result') or {}).get('agent_s') if finite((a.get('result') or {}).get('agent_s')) else None,
                       'B_agent_s':(b.get('result') or {}).get('agent_s') if finite((b.get('result') or {}).get('agent_s')) else None,
                       'A_warmup':(a.get('result') or {}).get('warmup'),'B_warmup':(b.get('result') or {}).get('warmup')}
                rows.append(row);observed.append(row)
            if not orders or orders.count('A')!=orders.count('B') or None in orders:
                unbalanced.append({'task_id':task['id'],'attempt':attempt['sequence']})
        deltas = [r['B_minus_A_s'] for r in observed if r['B_minus_A_s'] is not None]
        complete = bool(observed) and len(deltas)==len(observed)
        tasks.append({'task_id':task['id'],'planned_pairs':len(observed),'timed_pairs':len(deltas),
                      'mean_B_minus_A_s':sum(deltas)/len(deltas) if complete else None,
                      'A_first_pairs':sum(r['first']=='A' for r in observed),'B_first_pairs':sum(r['first']=='B' for r in observed)})
    timed = [r for r in rows if r['B_minus_A_s'] is not None]
    complete = bool(rows) and len(timed)==len(rows)
    mean = sum(t['mean_B_minus_A_s'] for t in tasks)/len(tasks) if complete else None
    wrong = sum(r['A_quality'] is False or r['B_quality'] is False for r in rows)
    unscored = sum(r['A_quality'] is None or r['B_quality'] is None for r in rows)
    reasons = []
    if not plan: reasons.append('No se fijó un plan de latencia antes de ejecutar la comparación de origen.')
    elif plan.get('version')!='arena-latency-plan-v1' or plan.get('endpoint')!='task_s' or not snapshot['config'].get('latency_study'):
        reasons.append('El plan registrado no identifica un protocolo de latencia compatible.')
    if not shared: reasons.append('Entradas independientes: no se calcula una diferencia emparejada por ID.')
    if snapshot['config']['adapter']!='ollama': reasons.append('Simulación: no se infiere rendimiento de modelos reales.')
    if snapshot['config']['split']!='eval': reasons.append('Desarrollo/piloto: el intervalo requiere fase de evaluación.')
    target = plan.get('planned_attempts') if plan else None
    if target is None or len(included)!=target or excluded: reasons.append('El análisis requiere todos los intentos previstos completos y compatibles, sin exclusiones.')
    if not complete: reasons.append('Hay pares sin tiempo de tarea válido; no se imputan errores, tiempos ausentes ni valores no finitos.')
    if wrong or unscored: reasons.append('Hay pares con respuesta incorrecta o sin calidad verificada; una respuesta rápida no prueba rendimiento útil.')
    if unbalanced or snapshot.get('conditions',{}).get('order_policy')!='balanced': reasons.append('El orden A/B observado no está equilibrado por tarea e intento.')
    if any(not r['sequential_verified'] for r in rows): reasons.append('Los timestamps no permiten verificar ejecución secuencial de todos los pares.')
    if snapshot.get('conditions',{}).get('warmup')!='per_run' or any((r.get(k) or {}).get('status')!='completed' or not finite((r.get(k) or {}).get('duration_s')) for r in rows for k in ('A_warmup','B_warmup')):
        reasons.append('Falta calentamiento completado registrado en alguna ejecución.')
    if len(tasks)<10: reasons.append('Se requieren al menos 10 tareas; las repeticiones no aumentan el número de casos independientes.')
    stimuli = [fingerprint({'input':t['input'].strip(),'environment':snapshot['environments'].get(t['environment']),
                           'attachments':[(f['sha256'],f['name']) for f in t.get('attachments',[])]}) for t in snapshot['tasks']] if shared else []
    if len(stimuli)!=len(set(stimuli)): reasons.append('Entradas duplicadas: IDs distintos no prueban tareas independientes.')
    values = [t['mean_B_minus_A_s'] for t in tasks if t['mean_B_minus_A_s'] is not None]
    if values and len(set(values))==1: reasons.append('Diferencias constantes por tarea: se evita un intervalo degenerado.')
    interval = None
    if not reasons:
        result = bootstrap((np.array(values),),np.mean,method='BCa',confidence_level=.95,n_resamples=4000,batch=256,rng=np.random.default_rng(42))
        low,high = float(result.confidence_interval.low),float(result.confidence_interval.high)
        if math.isfinite(low) and math.isfinite(high): interval = {'low_s':low,'high_s':high}
        else: reasons.append('El remuestreo no produjo límites finitos.')
    by_order = {}
    for first in ('A','B'):
        selected = [r for r in timed if r['first']==first]
        by_order[first] = {'timed_pairs':len(selected),'mean_B_minus_A_s':sum(r['B_minus_A_s'] for r in selected)/len(selected) if selected else None}
    return {'version':VERSION,'plan':plan,'scope':protocol_report(snapshot,included[0][1]['runs'] if included else [])['comparison_scope'],
            'included_attempts':len(included),'excluded_attempts':len(excluded),'task_count':len(tasks),
            'planned_pairs':len(rows),'timed_pairs':len(timed),'missing_pairs':len(rows)-len(timed),
            'incorrect_pairs':wrong,'unscored_pairs':unscored,'mean_B_minus_A_s':mean,'by_order':by_order,
            'unbalanced':unbalanced,'tasks':tasks,'pairs':rows,'interval':interval,'interval_unavailable_reasons':reasons,
            'method':{'name':'task_cluster_bootstrap_BCa','confidence_level':.95,'resamples':4000,'seed':42,'unit':'task',
                      'endpoint':'task_s','min_tasks':10,'python_version':platform.python_version(),
                      'numpy_version':np.__version__,'scipy_version':scipy.__version__,
                      'input_sha256':fingerprint([{'task_id':t['task_id'],'mean_B_minus_A_s':t['mean_B_minus_A_s']} for t in tasks])},
            'note':'B−A promedia diferencias dentro de cada tarea y da igual peso a los casos. Un valor negativo describe menor tiempo observado de B, no un ganador. Los tiempos incluyen herramientas y evaluación; el total incluye preparación y calentamiento. El intervalo agrupa todas las repeticiones e intentos de una tarea; requiere tareas independientes y representativas, supuesto que la aplicación no puede demostrar. Se muestran diferencias según quién ejecutó primero, sin corregir automáticamente efectos de caché, orden o recursos. No se generaliza a otras máquinas o datasets.'}


def latency_csv(report):
    output = io.StringIO(newline='')
    fields = ['campaign_id','design_sha256','analysis_version','included_attempts','excluded_attempts','task_id','attempt','experiment_id','repetition','A_run_id','B_run_id','first','sequential_verified',
              'A_status','B_status','A_quality','B_quality','A_task_s','B_task_s','B_minus_A_s','A_agent_s','B_agent_s','A_warmup','B_warmup']
    writer = csv.DictWriter(output,fieldnames=fields);writer.writeheader()
    analysis = report['analysis']['latency']
    for pair in analysis['pairs']:
        row = {'campaign_id':report['id'],'design_sha256':report['design_sha256'],'analysis_version':analysis['version'],
               'included_attempts':analysis['included_attempts'],'excluded_attempts':analysis['excluded_attempts'],**pair}
        for key in ('A_warmup','B_warmup'):row[key] = json.dumps(row[key],ensure_ascii=False)
        writer.writerow({k:"'"+str(v) if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v for k,v in row.items()})
    return output.getvalue()
