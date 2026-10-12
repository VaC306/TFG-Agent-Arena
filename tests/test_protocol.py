import asyncio
import copy
import csv
import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from arena.api import create_app
from arena.contracts import Task, AgentConfig
from arena.comparisons import ComparisonRequest, submit_comparison
from arena.evaluator import evaluate
from arena.export import csv_text
from arena.protocol import inference_identity, protocol_report
from arena.runner import execute
from arena.store import Store
from conftest import register_client
from test_comparisons import request_data

ROOT = Path(__file__).resolve().parents[1]


def task(reference='{"a":1,"b":[true,null]}', mode='json_match'):
    return Task(id='one', input='Return structured data', environment='empty', split='dev',
                expected_answer=reference, evaluation=mode)


@pytest.mark.parametrize('answer,correct,format_ok', [
    (' {"b":[true,null],"a":1.0} ',True,True),
    ('{"a":true,"b":[true,null]}',False,True),
    ('{"a":1,"b":[null,true]}',False,True),
    ('{"a":1,"a":1,"b":[true,null]}',False,False),
    ('```json\n{"a":1}\n```',False,False),
    ('{"a":1e999}',False,False),
])
def test_json_comparison_is_structural_and_strict(answer, correct, format_ok):
    result = evaluate(answer, task(), [])
    assert result['success'] is correct and result['format_ok'] is format_ok


def test_no_automatic_quality_and_text_contract():
    assert evaluate('anything', task(mode='none'), [])['success'] is None
    exact = task(' París ', 'exact_match')
    assert evaluate('París\n', exact, [])['success']
    assert not evaluate('parís', exact, [])['success']
    with pytest.raises(ValueError):
        task('not JSON')


@pytest.mark.parametrize('settings', [{'seed':True},{'seed':'42'},{'seed':-1},{'temperature':True},
                                     {'temperature':3},{'num_ctx':511},{'max_output_tokens':0},{'timeout_s':3601}])
def test_parameters_rejected_before_storage(settings):
    data = request_data()
    data['settings'] = settings
    with pytest.raises(ValueError):
        ComparisonRequest.model_validate(data)


def test_json_references_and_settings_round_trip(tmp_path):
    store = Store(tmp_path / 'test.sqlite')
    data = request_data()
    data['evaluation'] = 'json_match'
    data['branch_inputs']['A']['expected_answer'] = '{bad'
    with pytest.raises(ValueError):
        ComparisonRequest.model_validate(data)
    assert store.list_experiments() == []
    data['branch_inputs']['A']['expected_answer'] = '{"a":1}'
    data['settings'] = {'temperature':0.4, 'seed':99, 'num_ctx':4096, 'max_output_tokens':128, 'timeout_s':30}
    eid = submit_comparison(store, ComparisonRequest.model_validate(data))
    snapshot = store.snapshot(eid)
    assert snapshot['branch_tasks']['A']['evaluation'] == 'json_match'
    assert snapshot['config']['agents']['A']['seed'] == snapshot['config']['agents']['B']['seed'] == 99
    assert snapshot['config']['agents']['A']['limits']['timeout_s'] == 30
    assert snapshot['protocol']['reference_sent_to_model'] is False
    assert snapshot['conditions']['keep_alive'] == '0'


def test_reference_never_sent_and_model_change_stops_inference(tmp_path):
    store = Store(tmp_path / 'test.sqlite')
    data = request_data()
    data['branch_inputs']['A']['expected_answer'] = 'SECRET-REFERENCE'
    data['branch_inputs']['B']['expected_answer'] = 'SECRET-REFERENCE'
    eid = submit_comparison(store, ComparisonRequest.model_validate(data))
    snapshot = store.snapshot(eid)
    class Changing:
        calls = 0
        digest = 'first'
        async def metadata(self, model):
            return {'version':{'version':'1.0'},'model':{'digest':self.digest,'details':{'quantization_level':'Q4'}}}
        async def chat(self, messages, config, remaining):
            self.calls += 1
            assert 'SECRET-REFERENCE' not in str(messages)
            return {'message':{'content':'Other answer'},'done':True,'prompt_eval_count':2,'eval_count':2,'eval_duration':20}
    adapter = Changing()
    for i in range(2):
        run = store.claim()
        bundle = Task.model_validate(snapshot['branch_tasks'][run['branch']])
        config = AgentConfig.model_validate(snapshot['config']['agents'][run['branch']])
        asyncio.run(execute(run, bundle, {'orders':[]}, config, adapter, store))
        adapter.digest = 'changed'
    runs = store.list_runs(eid)
    assert adapter.calls == 1
    assert sum(bool(r['result'].get('error')) for r in runs) == 1
    report = protocol_report(snapshot, runs)
    assert sum(b['evaluated'] for b in report['branches'].values()) == 1
    assert any('cambio de modelo' in warning for warning in report['warnings'])
    assert snapshot == store.snapshot(eid)


def test_report_does_not_claim_causality_or_score_execution_errors():
    snapshot = {'config':{'adapter':'ollama', 'repetitions':2, 'agents':{'A':{'system_prompt':'A'}, 'B':{'system_prompt':'B'}}},
                'tasks':[task().model_dump()], 'conditions':{'inputs_shared':False}}
    runs = [{'task_id':task().id,'branch':'A','status':'failed','result':{'success':False,'error':'Connection failure','agent_s':2}},
            {'task_id':task().id,'branch':'B','status':'failed','result':{'success':False,'answer':'wrong','agent_s':1}}]
    report = protocol_report(snapshot, runs)
    assert report['comparison_scope'] == 'configurations'
    assert report['branches']['A']['evaluated'] == 0 and report['branches']['A']['mean_answer_s'] is None
    assert report['branches']['B']['evaluated'] == 1
    assert report['version'] == 'legacy'


def test_identity_changes_on_digest_server_or_defaults():
    metadata = {'version':{'version':'1'}, 'model':{'digest':'abc'}, 'show':{'template':'x'}}
    original = inference_identity('demo', metadata)
    assert original == inference_identity('demo:latest', metadata)
    for path, value in [('version','2'),('digest','def'),('template','y')]:
        changed = copy.deepcopy(metadata)
        changed['version' if path == 'version' else 'model' if path == 'digest' else 'show'][path] = value
        assert inference_identity('demo', changed)['fingerprint'] != original['fingerprint']


def test_reproducibility_export_scoped_and_csv_safe(tmp_path):
    path = tmp_path / 'test.sqlite'
    app = create_app(path, ROOT)
    client, other = TestClient(app), TestClient(app)
    register_client(client)
    eid = client.post('/comparisons', json=request_data()).json()['id']
    download = client.get('/experiments/' + eid + '/reproducibility.json')
    assert download.status_code == 200 and 'attachment;' in download.headers['content-disposition']
    assert download.json()['snapshot']['protocol']['evaluator_version'] == 'arena-evaluation-v2'
    register_client(other, 'other')
    assert other.get('/experiments/' + eid + '/reproducibility.json').status_code == 404
    store = Store(path)
    run = store.claim()
    store.finish(run, {'success':False,'error':'connection','answer':'=HYPERLINK("bad")'}, 'failed')
    # Whichever branch ran first, raw formula content must never become an Excel formula.
    rows = list(csv.DictReader(io.StringIO(csv_text(store, eid))))
    failed = next(r for r in rows if r['error'])
    assert failed['success'] == '' and failed['answer'].startswith("'=")


def test_eval_phase_and_examples_are_valid(tmp_path):
    from arena.datasets import parse_dataset
    data = request_data()
    data['split'] = 'eval'
    data['dataset'] = [c.model_dump() for c in parse_dataset('extract.jsonl', (ROOT / 'data/examples/extraccion.jsonl').read_text(encoding='utf-8'))]
    data.pop('branch_inputs')
    data['evaluation'] = 'json_match'
    store = Store(tmp_path / 'test.sqlite')
    eid = submit_comparison(store, ComparisonRequest.model_validate(data))
    assert store.snapshot(eid)['config']['split'] == 'eval'
    assert all(t['split'] == 'eval' for t in store.snapshot(eid)['tasks'])
    assert len(parse_dataset('answers.csv', (ROOT / 'data/examples/respuestas-concretas.csv').read_text(encoding='utf-8'))) == 3
    with pytest.raises(ValueError):
        ComparisonRequest.model_validate(request_data() | {'settings':{'num_ctx':512,'max_output_tokens':512}})


def test_same_model_shared_data_is_repeatability_and_example_downloads(tmp_path):
    store = Store(tmp_path / 'test.sqlite')
    data = request_data()
    data.pop('branch_inputs')
    data['dataset'] = [{'id':'one','input':'Question','expected_answer':None}]
    eid = submit_comparison(store, ComparisonRequest.model_validate(data))
    assert protocol_report(store.snapshot(eid), store.list_runs(eid))['comparison_scope'] == 'repeatability'
    client = TestClient(create_app(store.path, ROOT))
    register_client(client)
    assert client.get('/datasets/examples/exact_match').status_code == 200
    assert client.get('/datasets/examples/json_match').status_code == 200
    assert client.get('/datasets/examples/unknown').status_code == 422
