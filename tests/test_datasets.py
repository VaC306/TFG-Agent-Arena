import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from arena.api import create_app
from arena.comparisons import ComparisonRequest, submit_comparison
from arena.datasets import parse_dataset
from arena.export import csv_text
from arena.store import Store
from arena.worker import work


def body(mode='same_model'):
    return {'name': 'Dataset propio', 'adapter': 'simulated', 'comparison': mode,
            'agents': {branch: {'model': 'demo' if branch == 'A' or mode == 'same_model' else 'other',
                                'system_prompt': 'Responde brevemente'} for branch in ('A', 'B')},
            'dataset': [{'id': 'one', 'input': 'Entrada uno', 'expected_answer': 'REFERENCIA_SECRETA'},
                        {'id': 'two', 'input': 'Entrada dos'}], 'repetitions': 2}


def test_csv_bom_quotes_multiline_and_optional_reference():
    cases = parse_dataset('datos.CSV', '\ufeffid,input,expected_answer\r\na,"Texto, con coma\ny salto",\r\nb,Capital,París\r\n')
    assert cases[0].input == 'Texto, con coma\ny salto'
    assert cases[0].expected_answer is None
    assert cases[1].expected_answer == 'París'


@pytest.mark.parametrize('filename,content', [
    ('a.csv', 'id,input\nx,uno\nx,dos'),
    ('a.csv', 'id,input\nx'),
    ('a.csv', 'id,input\nx,uno,extra'),
    ('a.csv', 'id,input,input\nx,uno,dos'),
    ('a.csv', 'id,input,unknown\nx,uno,dos'),
    ('a.csv', 'id,input\nx,"sin cerrar'),
    ('a.csv', 'id,input\nx,   '),
    ('a.csv', 'id,input\n'),
    ('a.jsonl', '{bad}'),
    ('a.jsonl', '[1,2]'),
    ('a.jsonl', '{"id":"x","input":"hola","path":"file.txt"}'),
    ('a.jsonl', '{"id":"x","input":null}'),
    ('a.txt', 'id,input\nx,hola'),
    ('a.csv', 'id,input\n' + '\n'.join(f'x{i},hola' for i in range(101))),
    ('a.csv', 'x' * (1024 * 1024 + 1)),
    ('a.csv', 'id,input\nx,' + 'a' * 6001),
], ids=[f'invalid-{i}' for i in range(16)])
def test_invalid_datasets(filename, content):
    with pytest.raises(ValueError):
        parse_dataset(filename, content)


@pytest.mark.parametrize('mode', ['same_model', 'different_models'])
def test_dataset_worker_shared_inputs_reference_isolation_and_export(tmp_path, mode):
    store = Store(tmp_path / 'arena.sqlite')
    request = ComparisonRequest.model_validate(body(mode))
    eid = submit_comparison(store, request)
    snapshot = store.snapshot(eid)
    assert snapshot['conditions']['inputs_shared'] is True
    assert len(snapshot['tasks']) == 2
    asyncio.run(work(store, once=True))
    runs = store.list_runs(eid)
    assert len(runs) == 8
    for task_id in ('one', 'two'):
        messages = []
        for run in (r for r in runs if r['task_id'] == task_id):
            event = next(e for e in store.events(run['id']) if e['kind'] == 'input')
            messages.append(event['payload']['messages'][1])
            assert 'REFERENCIA_SECRETA' not in json.dumps(event)
            assert run['result']['success'] is (False if task_id == 'one' else None)
        assert all(message == messages[0] for message in messages)
    assert 'exact_match' in csv_text(store, eid) and 'not_evaluated' in csv_text(store, eid)
    assert snapshot == store.snapshot(eid)


@pytest.mark.parametrize('change', ['duplicate', 'empty', 'mixed'])
def test_direct_submission_cannot_bypass_validation(change):
    data = body()
    if change == 'duplicate': data['dataset'][1]['id'] = 'one'
    if change == 'empty': data['dataset'] = []
    if change == 'mixed': data['shared_input'] = {'text': 'different'}
    with pytest.raises(ValueError):
        ComparisonRequest.model_validate(data)


def test_dataset_api(tmp_path):
    client = TestClient(create_app(tmp_path / 'api.sqlite', Path(__file__).resolve().parents[1]))
    from conftest import register_client
    register_client(client)
    template = client.get('/datasets/template.csv')
    assert template.status_code == 200
    result = client.post('/datasets/validate', json={'filename': 'mine.csv', 'content': template.text})
    assert result.status_code == 200
    assert result.json()['count'] == 2 and result.json()['scored'] == 1
    invalid = client.post('/datasets/validate', json={'filename': 'mine.csv', 'content': 'bad'})
    assert invalid.status_code == 422
    data = body()
    data['dataset'] = result.json()['cases']
    created = client.post('/comparisons', json=data)
    assert created.status_code == 201
    detail = client.get('/experiments/' + created.json()['id']).json()
    assert len(detail['runs']) == 8
    jsonl = '\n'.join(json.dumps(case, ensure_ascii=False) for case in data['dataset'])
    assert len(parse_dataset('mine.jsonl', jsonl)) == 2
