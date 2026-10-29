import copy
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from arena.api import create_app
from arena.comparisons import ComparisonRequest, submit_comparison
from arena.model_results import comparison_metrics, latest_model_results, outcome, summarize
from arena.store import Store
from conftest import register_client
from test_comparisons import request_data

ROOT = Path(__file__).resolve().parents[1]


def finish(store,eid,answers=True):
    for _ in range(2):
        run = store.claim()
        assert run['experiment_id'] == eid
        result = {'answer':'42','success':answers,'format_ok':None,'agent_s':2,
                  'inference_identity':{'verified':True,'fingerprint':run['branch'],'digest':run['branch']*64,'server_version':'1'}}
        store.finish(run,result,'succeeded' if answers else 'failed')


def test_summary_distinguishes_wrong_format_errors_and_unscored():
    runs = [{'task_id':'one','status':s,'result':r} for s,r in [
        ('succeeded',{'answer':'42','success':True,'agent_s':2}),
        ('failed',{'answer':'43','success':False,'format_ok':None,'agent_s':4}),
        ('failed',{'answer':'bad JSON','success':False,'format_ok':False,'agent_s':6}),
        ('limit',{'error':'model_calls','success':False,'agent_s':100}),
        ('completed',{'answer':'open','success':None,'agent_s':8}),('queued',None)]]
    result = summarize(runs,[{'id':'one','expected_answer':'42'}])
    assert (result['correct'],result['incorrect'],result['invalid_format'],result['execution_errors'],result['unscored'],result['pending']) == (1,1,1,1,1,1)
    assert result['evaluated'] == 3 and result['planned_evaluable'] == 6
    assert result['mean_answer_s'] == 5 and result['timed_answers'] == 4
    assert outcome(runs[2]) == 'invalid_format'


def test_latest_completed_model_results_do_not_pool_prompts_or_partial_runs(tmp_path):
    store = Store(tmp_path/'results.sqlite')
    data = request_data('different_models')
    data['adapter'] = 'ollama'
    data['shared_input']['expected_answer'] = '42'
    first = submit_comparison(store,ComparisonRequest.model_validate(data))
    finish(store,first)
    entries = latest_model_results(store)
    assert len(entries) == 2
    assert entries[0]['cohort_key'] == entries[1]['cohort_key']
    assert all(e['verified'] and e['summary']['correct'] == 1 for e in entries)
    assert all(e['metrics']['p95_answer_s'] == 2 and e['metrics']['input_tokens'] is None for e in entries)
    changed = copy.deepcopy(data)
    changed['agents']['A']['system_prompt'] = 'Different prompt'
    second = submit_comparison(store,ComparisonRequest.model_validate(changed))
    assert {e['experiment_id'] for e in latest_model_results(store)} == {first}
    finish(store,second,answers=False)
    entries = latest_model_results(store)
    assert {e['experiment_id'] for e in entries} == {second}
    assert entries[0]['cohort_key'] != entries[1]['cohort_key']
    assert all(e['summary']['correct'] == 0 and e['summary']['incorrect'] == 1 for e in entries)


def test_model_library_is_account_scoped_and_history_clear_removes_entries(tmp_path):
    path = tmp_path/'results.sqlite'
    client = TestClient(create_app(path,ROOT))
    other = TestClient(create_app(path,ROOT))
    assert client.get('/model-results').status_code == 401
    user = register_client(client)
    register_client(other,'other')
    data = request_data('different_models')
    data['shared_input']['expected_answer'] = '42'
    response = client.post('/comparisons',json=data)
    eid = response.json()['id']
    store = Store(path)
    finish(store,eid)
    detail = client.get('/experiments/'+eid).json()
    assert detail['overviews']['A']['planned_evaluable'] == 1
    assert len(client.get('/model-results').json()['entries']) == 2
    assert other.get('/model-results').json()['entries'] == []
    report = client.get('/experiments/'+eid+'/report.md')
    assert report.status_code == 200 and 'attachment;' in report.headers['content-disposition']
    assert 'Ejecuciones programadas: 1' in report.text and 'Referencia:' in report.text
    assert other.get('/experiments/'+eid+'/report.md').status_code == 404
    state = client.get('/profile/history').json()
    assert client.request('DELETE','/profile/history',json={'confirmation':'clear-history','revision':state['revision']}).status_code == 200
    assert client.get('/model-results').json()['entries'] == []


def test_library_includes_older_results_beyond_history_page(tmp_path):
    store = Store(tmp_path/'results.sqlite',owner_id='owner')
    data = request_data('different_models')
    first = submit_comparison(store,ComparisonRequest.model_validate(data))
    worker = Store(store.path)
    finish(worker,first)
    for _ in range(51):
        submit_comparison(store,ComparisonRequest.model_validate(data))
    assert first not in {e['id'] for e in store.list_experiments()}
    assert {e['experiment_id'] for e in latest_model_results(store)} == {first}


def test_report_fences_untrusted_content_without_changing_it():
    from arena.result_report import code_block
    content = '```\n# Content supplied by a user\n````'
    block = code_block(content)
    assert block.startswith('`````\n') and content in block and block.endswith('\n`````\n')


@pytest.mark.parametrize('condition', ['dataset','prompt','parameters','repetitions','split','source','server','host','order'])
def test_library_comparison_fingerprint_changes_with_conditions(tmp_path,condition):
    store = Store(tmp_path/'conditions.sqlite')
    data = request_data('different_models')
    data['adapter'] = 'ollama'
    eid = submit_comparison(store,ComparisonRequest.model_validate(data))
    finish(store,eid)
    entries = latest_model_results(store)
    before = {e['branch']:e for e in entries}
    snapshot = copy.deepcopy(store.snapshot(eid))
    if condition == 'dataset': snapshot['tasks'][0]['input'] += ' changed'
    if condition == 'prompt': snapshot['config']['agents']['A']['system_prompt'] += ' changed'
    if condition == 'parameters': snapshot['config']['agents']['A']['seed'] += 1
    if condition == 'repetitions': snapshot['config']['repetitions'] += 1
    if condition == 'split': snapshot['config']['split'] = 'eval'
    if condition == 'source': snapshot['source_sha256']['runner.py'] = 'different'
    if condition == 'host': snapshot['host']['python'] = 'different'
    if condition == 'order': snapshot['config']['order_seed'] += 1
    # Read-only snapshot substitution: leave the persisted experiment intact.
    store.result_experiments = lambda: [(eid,snapshot)]
    if condition == 'server':
        original_evidence = store.result_evidence
        original_runs, original_notes = original_evidence()
        store.result_evidence = lambda: ({eid:[r | {'result':r['result'] | {'inference_identity':r['result']['inference_identity'] | {'server_version':'2'}}} for r in original_runs[eid]]}, original_notes)
    after = {e['branch']:e for e in latest_model_results(store)}
    assert after['A']['cohort_key'] != before['A']['cohort_key']
    if condition in ('prompt','parameters'):
        assert after['A']['cohort_key'] != after['B']['cohort_key']


def test_summary_excludes_cancelled_answers_and_nonfinite_measurements():
    runs = [{'task_id':'case','status':status,'result':result} for status,result in [
        ('cancelled',{'answer':'late','success':True,'agent_s':100}),
        ('timeout',{'agent_s':80}), ('limit',{}), ('interrupted',{}),
        ('succeeded',{'answer':'ok','success':True,'agent_s':float('nan')}),
        ('completed',{'answer':'ok','success':None,'agent_s':-1})]]
    summary = summarize(runs,[{'id':'case','evaluation':'none'}])
    assert summary['execution_errors'] == 3 and summary['cancelled'] == 1
    assert summary['finished'] == len(runs) and summary['evaluated'] == 1
    assert summary['mean_answer_s'] is None and summary['timed_answers'] == 0


@pytest.mark.parametrize('result', [None, {'error':'Cancelled before execution'},
    {'answer':'late','success':True,'agent_s':100,'task_s':90}])
def test_cancellation_is_separate_even_with_partial_or_late_result(result):
    from arena.protocol import quality_value
    from arena.latency_analysis import task_time
    run = {'task_id':'case','status':'cancelled','result':result}
    summary = summarize([run],[{'id':'case','expected_answer':'late'}])
    assert outcome(run) == 'cancelled'
    assert summary['cancelled'] == summary['finished'] == summary['planned_evaluable'] == 1
    assert summary['execution_errors'] == summary['evaluated'] == summary['unscored'] == summary['pending'] == 0
    assert summary['mean_answer_s'] is None and summary['timed_answers'] == 0
    assert quality_value(run) is None and task_time(run) is None


def test_snapshot_sources_preserve_crlf_and_verify_their_hashes(tmp_path,monkeypatch):
    import hashlib
    import arena.scheduler as scheduler
    code = tmp_path/'code'
    code.mkdir()
    content = b'# Windows source\r\nvalue = 42\r\n'
    (code/'fixture.py').write_bytes(content)
    monkeypatch.setattr(scheduler,'__file__',str(code/'scheduler.py'))
    store = Store(tmp_path/'sources.sqlite')
    eid = submit_comparison(store,ComparisonRequest.model_validate(request_data('different_models')))
    snapshot = store.snapshot(eid)
    assert snapshot['source']['fixture.py'].encode('utf-8') == content
    assert hashlib.sha256(snapshot['source']['fixture.py'].encode('utf-8')).hexdigest() == snapshot['source_sha256']['fixture.py']


def test_legacy_failure_without_answer_is_never_quality_evaluated():
    from arena.protocol import quality_value
    run = {'status':'failed','result':{'success':False}}
    assert outcome(run) == 'execution_error'
    assert quality_value(run) is None


def test_comparison_metrics_include_failed_usage_without_polluting_answer_latency():
    runs = [
        {'status':'completed','result':{'answer':'ok','success':True,'agent_s':2,'usage_complete':True,'input_tokens':10,'output_tokens':4,'server_tps':8}},
        {'status':'timeout','result':{'error':'timeout','agent_s':8,'usage_complete':True,'input_tokens':20,'output_tokens':2,'server_tps':100}},
    ]
    metrics = comparison_metrics(runs)
    assert metrics['p95_answer_s'] == 2 and metrics['latency_samples'] == 1
    assert metrics['mean_server_tps'] == 8 and metrics['speed_samples'] == 1
    assert metrics['input_tokens'] == 30 and metrics['output_tokens'] == 6
    assert metrics['total_run_s'] == 10
    runs[1]['result']['usage_complete'] = False
    assert comparison_metrics(runs)['input_tokens'] is None
    assert comparison_metrics(runs)['usage_samples'] == 1


def test_comparison_metrics_p95_and_missing_zero_invalid_measurements():
    runs = [{'status':'completed','result':{'answer':'ok','agent_s':n}} for n in range(1,21)]
    assert comparison_metrics(runs)['p95_answer_s'] == 19
    assert comparison_metrics([])['total_run_s'] is None
    for invalid in (None, -1, float('nan'), float('inf'), True):
        metrics = comparison_metrics([{'status':'completed','result':{'answer':'ok','agent_s':invalid,'usage_complete':True,'input_tokens':invalid,'output_tokens':0,'server_tps':invalid}}])
        assert metrics['p95_answer_s'] is None and metrics['total_run_s'] is None
        assert metrics['input_tokens'] is None and metrics['mean_server_tps'] is None
    metrics = comparison_metrics([{'status':'completed','result':{'answer':'','agent_s':0,'usage_complete':True,'input_tokens':0,'output_tokens':0,'server_tps':0}}])
    assert metrics['p95_answer_s'] == metrics['input_tokens'] == metrics['mean_server_tps'] == 0
