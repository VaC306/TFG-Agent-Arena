"""Account-scoped latest evidence, without pooling incompatible experiments."""
import hashlib
import json
import math
from .protocol import quality_value

TERMINAL_ERRORS = {'timeout','limit','cancelled','interrupted'}


def outcome(run):
    result = run.get('result') or {}
    if run['status'] in ('queued','running'):
        return 'pending'
    if result.get('error') or run['status'] in TERMINAL_ERRORS or run['status'] == 'failed' and 'answer' not in result:
        return 'execution_error'
    quality = quality_value(run)
    if quality is True:
        return 'correct'
    if quality is False:
        return 'invalid_format' if result.get('format_ok') is False else 'incorrect'
    return 'unscored'


def evaluable(task):
    return bool(task.get('criteria')) or task.get('evaluation','exact_match') != 'none' and task.get('expected_answer') is not None


def summarize(runs, tasks):
    counts = {key:0 for key in ('correct','incorrect','invalid_format','execution_error','unscored','pending')}
    for run in runs:
        counts[outcome(run)] += 1
    times = [(r.get('result') or {}).get('agent_s') for r in runs
             if outcome(r) not in ('execution_error','pending') and 'answer' in (r.get('result') or {})]
    times = [t for t in times if type(t) in (float,int) and math.isfinite(t) and t >= 0]
    by_id = {task['id']:task for task in tasks}
    return {'total':len(runs),'finished':len(runs)-counts['pending'],
            'evaluated':counts['correct']+counts['incorrect']+counts['invalid_format'],
            'planned_evaluable':sum(evaluable(by_id[r['task_id']]) for r in runs),
            'correct':counts['correct'],'incorrect':counts['incorrect'],'invalid_format':counts['invalid_format'],
            'execution_errors':counts['execution_error'],'unscored':counts['unscored'],'pending':counts['pending'],
            'mean_answer_s':sum(times)/len(times) if times else None,'timed_answers':len(times)}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def test_kind(task):
    evaluation = 'order_benchmark' if task.get('criteria') else task.get('evaluation','exact_match') if task.get('expected_answer') is not None else 'none'
    files = task.get('attachments') or []
    modality = 'images' if any(f['media_type'].startswith('image/') for f in files) else 'files' if files else 'text'
    return evaluation + ':' + modality


def latest_model_results(store):
    latest = {}
    for eid,snapshot in store.result_experiments():
        runs = store.list_runs(eid)
        annotations = store.annotations(eid)
        deviations = [a for a in annotations if a['kind'] == 'deviation']
        config = snapshot['config']
        for branch in ('A','B'):
            selected = [r for r in runs if r['branch'] == branch]
            # A partial branch never replaces its last complete result.
            if not selected or any(r['status'] in ('queued','running') for r in selected):
                continue
            tasks = [snapshot['branch_tasks'][branch]] if snapshot.get('branch_tasks') else snapshot['tasks']
            agent = config['agents'][branch]
            identities = [(r.get('result') or {}).get('inference_identity') for r in selected]
            verified = all(i and i.get('verified') for i in identities)
            identities = [i for i in identities if i]
            identity = identities[-1] if identities else {}
            stable = verified and len({i['fingerprint'] for i in identities}) == 1
            model = agent['model'] if ':' in agent['model'] else agent['model']+':latest'
            for kind in sorted({test_kind(t) for t in tasks}):
                cases = [t for t in tasks if test_kind(t) == kind]
                ids = {t['id'] for t in cases}
                chosen = [r for r in selected if r['task_id'] in ids]
                timestamp = max(r.get('finished_at') or r.get('queued_at') or 0 for r in chosen)
                key = (config['adapter'],model,identity.get('digest'),kind)
                versions = sorted({(r.get('result') or {}).get('evaluator_version','legacy') for r in chosen})
                host = snapshot.get('host') or {}
                cohort = {'data':fingerprint({'tasks':cases,'environments':snapshot.get('environments')}),
                          'prompt':agent['system_prompt'],'parameters':{k:agent.get(k) for k in ('temperature','seed','num_ctx','limits','tools_enabled')},
                          'repetitions':config['repetitions'],'split':config['split'],'adapter':config['adapter'],
                          'conditions':snapshot.get('conditions'),'source_sha256':snapshot.get('source_sha256'),
                          'evaluator_versions':versions,'server_version':identity.get('server_version'),
                          'order_seed':config.get('order_seed'),
                          'host':{k:host.get(k) for k in ('platform','python','cpu','logical_cpus','ram_total_bytes','packages')}}
                if deviations:
                    # A declared deviation cannot silently match any other result's cohort.
                    cohort['external_deviations'] = {'experiment_id':eid,'annotations':deviations}
                record = {'id':fingerprint(key),'model':model,'adapter':config['adapter'],'digest':identity.get('digest'),
                          'verified':stable,'external_deviation':bool(deviations),'annotations':annotations,
                          'kind':kind,'experiment_id':eid,'experiment_name':config['name'],'branch':branch,
                          'updated_at':timestamp,'split':config['split'],'repetitions':config['repetitions'],
                          'summary':summarize(chosen,cases),'cohort_key':fingerprint(cohort),'comparison_conditions':cohort,
                          'conditions':{'system_prompt':agent['system_prompt'],'temperature':agent.get('temperature'),
                                        'seed':agent.get('seed'),'num_ctx':agent.get('num_ctx'),'limits':agent.get('limits'),
                                        'server_version':identity.get('server_version'),'quantization':identity.get('quantization'),
                                        'data_sha256':fingerprint(cases),'evaluator_versions':versions}}
                if key not in latest or timestamp > latest[key]['updated_at']:
                    latest[key] = record
    return sorted(latest.values(),key=lambda r:(-r['updated_at'],r['model'],r['kind']))
