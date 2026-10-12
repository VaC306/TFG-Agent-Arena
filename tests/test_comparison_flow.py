"""Exercise submission, worker, reporting and exports with known responses."""
import asyncio
import csv
import io
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from arena.api import create_app
from arena.export import paired_summary
from arena.protocol import protocol_report
from arena.store import Store
from arena.worker import work
from conftest import register_client

ROOT = Path(__file__).resolve().parents[1]


def test_comparison_quality_matches_answers_through_api_worker_and_csv(tmp_path, monkeypatch):
    class Controlled:
        def __init__(self, *args, **kwargs):
            pass

        async def metadata(self, model):
            return {'version': {'version': 'test-server'},
                    'model': {'digest': ('a' if model == 'fixture-a' else 'b') * 64}, 'show': {}}

        async def chat(self, messages, config, remaining):
            text = messages[-1]['content']
            # A reference must never leak into the model's messages.
            assert 'REFERENCE-PRIVATE' not in str(messages)
            key = next(k for k in ('valid', 'wrong', 'invalid', 'empty', 'open') if k in text)
            answers = {'fixture-a': {'valid':'{"b":2,"a":1}', 'wrong':'{"a":true}',
                                    'invalid':'```json\n{"a":1}\n```', 'empty':'  ', 'open':'An open answer'},
                       'fixture-b': {'valid':'{"a":1,"b":2}', 'wrong':'{"a":1}',
                                    'invalid':'{"a":1,"a":1}', 'open':'Another open answer'}}
            if key == 'empty' and config.model == 'fixture-b':
                raise httpx.ConnectError('Controlled connection failure')
            return {'message': {'content': answers[config.model][key]}, 'done': True,
                    'prompt_eval_count': 10, 'eval_count': 5, 'eval_duration': 50_000_000}

    monkeypatch.setattr('arena.worker.Ollama', Controlled)
    path = tmp_path / 'flow.sqlite'
    client = TestClient(create_app(path, ROOT))
    register_client(client)
    response = client.post('/comparisons', json={
        'name':'Controlled quality check', 'adapter':'ollama', 'comparison':'different_models',
        'agents': {b: {'model':m, 'system_prompt':'Return only JSON.'}
                   for b, m in [('A','fixture-a'), ('B','fixture-b')]},
        'evaluation':'json_match', 'dataset':[
            {'id':'valid','input':'valid','expected_answer':'{"a":1,"b":2}'},
            {'id':'wrong','input':'wrong','expected_answer':'{"a":1}'},
            {'id':'invalid','input':'invalid','expected_answer':'{"a":1}'},
            {'id':'empty','input':'empty','expected_answer':'"REFERENCE-PRIVATE"'},
            {'id':'open','input':'open'}]})
    assert response.status_code == 201, response.text
    eid = response.json()['id']
    store = Store(path)
    asyncio.run(work(store, once=True))
    detail = client.get('/experiments/' + eid).json()
    for branch, correct in [('A',1), ('B',2)]:
        stats = detail['protocol']['branches'][branch]
        assert (stats['total'],stats['answers'],stats['evaluated'],stats['correct'],stats['execution_errors']) == (5,4,3,correct,1)
        assert stats['mean_answer_s'] > 0
    rows = list(csv.DictReader(io.StringIO(client.get('/experiments/' + eid + '/metrics.csv').text)))
    assert len(rows) == 10
    assert all(r['success'] == '' and r['quality_evaluated'] == 'False' for r in rows if r['task_id'] in ('empty','open'))
    summary = paired_summary(store, eid)
    assert summary['pairs'] == 3
    assert summary['success_rate'] == {'A':pytest.approx(1/3), 'B':pytest.approx(2/3)}
    assert (summary['A_only_success'],summary['B_only_success']) == (0,1)
    assert summary['complete_pairs'] is False and summary['mcnemar_exact_p'] is None
    exported = client.get('/experiments/' + eid + '/reproducibility.json').json()
    assert exported['report'] == detail['protocol']
    assert len(exported['runs']) == 10


def test_verified_model_aliases_report_repeatability():
    snapshot = {'config':{'adapter':'ollama','repetitions':1,'agents':{
        b:{'model':m,'system_prompt':'Same prompt'} for b,m in [('A','alias-a'),('B','alias-b')]}},
        'tasks':[{'expected_answer':'42'}]}
    runs = [{'branch':b,'status':'succeeded','result':{'success':True,'inference_identity':{
        'verified':True,'digest':'a'*64}}} for b in ('A','B')]
    report = protocol_report(snapshot,runs)
    assert report['comparison_scope'] == 'repeatability'
    assert any('mismo digest' in warning for warning in report['warnings'])
