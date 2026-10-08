import asyncio
import copy
import csv
import io
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from arena.adapters import Simulated, Ollama
from arena.contracts import AgentConfig, Task
from arena.evaluator import evaluate
from arena.export import csv_text, paired_summary, export_bundle
from arena.runner import execute
from arena.scheduler import submit
from arena.store import Store
from arena.tools import Tools
from arena.worker import work

ROOT = Path(__file__).resolve().parents[1]
TASKS = [Task.model_validate_json(line) for line in (ROOT / 'data/tasks.jsonl').read_text(encoding='utf-8').splitlines()]
ENV = json.loads((ROOT / 'data/orders.json').read_text(encoding='utf-8'))


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / 'arena.sqlite')


def enqueue(store):
    return submit(store, ROOT / 'configs/simulated.json', ROOT / 'data/tasks.jsonl')


def test_independent_environments_and_outputs():
    original = copy.deepcopy(ENV)
    a, b = Tools(ENV), Tools(ENV)
    a.environment['orders'][0]['lines'][0]['unit_cents'] = 1
    output = b.call('order_lines', {'order_id':'O1'})
    output[0]['unit_cents'] = 2
    assert b.call('order_lines', {'order_id':'O1'})[0]['unit_cents'] == 500
    assert ENV == original


@pytest.mark.parametrize('task', TASKS, ids=lambda t:t.id)
def test_evaluator_accepts_reference_and_rejects_wrong_amount(task):
    reference = {'total_cents': task.criteria.total_cents, 'order_ids': list(reversed(task.criteria.order_ids))}
    assert evaluate(json.dumps(reference), task, ['calculate'])['success']
    reference['total_cents'] += 1
    result = evaluate(json.dumps(reference), task, [])
    assert result['format_ok'] and not result['success']


@pytest.mark.parametrize('content', ['not json', '{"total_cents":true,"order_ids":[]}', '{"total_cents":"3500","order_ids":["O1","O2"]}', '{"total_cents":3500,"order_ids":["O1","O2"],"extra":1}'])
def test_strict_format(content):
    assert not evaluate(content, TASKS[0], [])['format_ok']


def test_evaluator_constraints():
    assert not evaluate('{"total_cents":3500,"order_ids":["O1","O2","O2"]}', TASKS[0], [])['success']
    assert not evaluate('{"total_cents":3500,"order_ids":["O1","O2"]}', TASKS[0], ['shell'])['success']


def test_tool_validation():
    tools = Tools(ENV)
    assert tools.call('calculate', {'operation':'subtract','values':[10,3,2]}) == {'value':5}
    assert tools.call('calculate', {'operation':'multiply','values':[3,333]}) == {'value':999}
    for name, args in [('shell', {}), ('calculate', {'operation':'eval','values':[1]}), ('calculate', {'operation':'sum','values':[True]})]:
        with pytest.raises(ValueError):
            tools.call(name,args)


@pytest.mark.parametrize('task', TASKS, ids=lambda t:t.id)
def test_simulator_solves_all_tasks_without_reference(task, store):
    enqueue(store)
    run = store.claim()
    config = AgentConfig.model_validate(store.snapshot(run['experiment_id'])['config']['agents']['A'])
    assert asyncio.run(execute(run, task, ENV, config, Simulated(), store)) == 'succeeded'


def test_paired_end_to_end_and_metrics(store, tmp_path):
    eid = enqueue(store)
    asyncio.run(work(store, once=True))
    runs = store.list_runs(eid)
    assert len(runs) == 16 and all(r['status'] == 'succeeded' for r in runs)
    first_task = [r for r in runs if r['task_id'] == TASKS[0].id and r['repetition'] == 0]
    paths = {}
    for run in first_task:
        events = store.events(run['id'])
        responses = [e['payload']['response'] for e in events if e['kind'] == 'inference_response']
        metrics = run['result']
        assert metrics['input_tokens'] == sum(r['prompt_eval_count'] for r in responses)
        assert metrics['output_tokens'] == 40
        assert metrics['server_tps'] == pytest.approx(1000)
        assert metrics['tool_calls'] == 4
        assert metrics['queue_s'] >= 0 and metrics['agent_s'] > 0
        paths[run['branch']] = [e['payload']['arguments']['order_id'] for e in events if e['kind'] == 'tool_request' and e['payload']['name'] == 'order_lines']
    assert paths == {'A':['O1','O2'], 'B':['O2','O1']}
    assert len(list(csv.DictReader(io.StringIO(csv_text(store, eid))))) == 16
    assert paired_summary(store, eid)['success_rate'] == {'A':1, 'B':1}
    export_bundle(store, eid, tmp_path / 'bundle')
    with pytest.raises(FileExistsError):
        export_bundle(store, eid, tmp_path / 'bundle')
    second = enqueue(store)
    assert second != eid and len(store.list_runs(eid)) == 16
    assert [(r['task_id'],r['branch']) for r in store.list_runs(second)] == [(r['task_id'],r['branch']) for r in runs]


class Slow(Simulated):
    async def chat(self, *args):
        await asyncio.sleep(10)


class Broken(Simulated):
    async def chat(self, *args):
        raise RuntimeError('server unavailable')


@pytest.mark.parametrize('limits,adapter,status,error', [
    ({'max_calls':1}, Simulated(), 'limit', 'model_calls'),
    ({'max_tool_calls':0}, Simulated(), 'limit', 'tool_calls'),
    ({'max_output_tokens':8}, Simulated(), 'limit', 'output_tokens'),
    ({'timeout_s':0.05}, Slow(), 'timeout', 'TimeoutError'),
    ({}, Broken(), 'failed', 'RuntimeError')])
def test_limits_and_failures(store, limits, adapter, status, error):
    enqueue(store)
    run = store.claim()
    config = AgentConfig(model='mock',system_prompt='test',limits=limits)
    assert asyncio.run(execute(run, TASKS[0], ENV, config, adapter, store)) == status
    result = store.list_runs()[0]['result']
    assert not result['success'] and error in result['error']
    if status in {'timeout', 'failed'}:
        assert not result['usage_complete'] and result['server_tps'] is None


def test_cancel_during_inference(store):
    enqueue(store)
    run = store.claim()
    async def scenario():
        pending = asyncio.create_task(execute(run,TASKS[0],ENV,AgentConfig(model='mock',system_prompt='test'),Slow(),store))
        await asyncio.sleep(0.02)
        store.cancel(run['id'])
        return await pending
    assert asyncio.run(scenario()) == 'cancelled'


def test_interrupt_during_inference(store):
    enqueue(store)
    run = store.claim()
    async def scenario():
        pending = asyncio.create_task(execute(run,TASKS[0],ENV,AgentConfig(model='mock',system_prompt='test'),Slow(),store))
        await asyncio.sleep(0.02)
        pending.cancel()
        return await pending
    assert asyncio.run(scenario()) == 'interrupted'


def test_claim_cancel_recovery_and_failure_denominator(store):
    eid = enqueue(store)
    active = store.claim()
    assert Store(store.path).claim() is None
    store.recover()
    assert store.list_runs()[0]['status'] == 'interrupted'
    for run in store.list_runs()[1:]:
        store.cancel(run['id'])
    assert paired_summary(store, eid)['success_rate'] == {'A':0,'B':0}
    assert store.claim() is None


def test_api(tmp_path):
    from arena.api import create_app
    with TestClient(create_app(tmp_path/'api.sqlite',ROOT)) as client:
        response = client.post('/experiments',json={'config':'simulated'})
        assert response.status_code == 201
        eid = response.json()['id']
        runs = client.get(f'/experiments/{eid}').json()['runs']
        assert len(runs) == 16
        assert client.post(f"/runs/{runs[0]['id']}/cancel").status_code == 200
        assert client.get(f'/experiments/{eid}/metrics.csv').status_code == 200
        assert client.get('/experiments/missing').status_code == 404
        assert client.post('/experiments',json={'config':'../../etc/passwd'}).status_code == 422


def test_native_ollama_payload(monkeypatch):
    import httpx
    requests = []
    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        return httpx.Response(200,json={'message':{'role':'assistant','content':'{}','thinking':'private'},'done':True,'eval_count':2,'prompt_eval_count':9,'eval_duration':100})
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs: original(transport=httpx.MockTransport(handler),**kwargs))
    response = asyncio.run(Ollama('http://localhost:11434').chat([{'role':'user','content':'test'}], AgentConfig(model='mock',system_prompt='test'),100))
    assert requests[0]['stream'] is False
    assert requests[0]['options']['num_predict'] == 100
    assert len(requests[0]['tools']) == 3
    assert 'thinking' not in response['message']


def test_snapshot_and_submit_without_git(store, monkeypatch):
    import arena.scheduler as scheduler
    def missing(*args, **kwargs):
        raise FileNotFoundError()
    monkeypatch.setattr(scheduler.subprocess, 'run', missing)
    eid = enqueue(store)
    snapshot = store.snapshot(eid)
    assert snapshot['git_commit'] is None
    assert snapshot['source']['runner.py'] and snapshot['data_sha256']


def test_export_pending_is_not_partial(store, tmp_path):
    eid = enqueue(store)
    with pytest.raises(ValueError):
        export_bundle(store, eid, tmp_path/'pending')
    assert not (tmp_path/'pending').exists()


def test_cancel_finish_race_has_consistent_event(store):
    enqueue(store)
    run = store.claim()
    store.cancel(run['id'])
    assert store.finish(run, {'success':True}, 'succeeded') == 'cancelled'
    assert store.events(run['id'])[-1]['payload']['success'] is False


@pytest.mark.parametrize('mutation,status', [
    ({'done_reason':'length'},'limit'),
    ({'done':False},'failed'),
    ({'eval_count':-1},'failed'),
    ({'prompt_eval_count':None},'failed')])
def test_bad_server_responses(store, mutation, status):
    class Bad(Simulated):
        async def chat(self, *args):
            return await super().chat(*args) | mutation
    enqueue(store)
    run=store.claim()
    assert asyncio.run(execute(run,TASKS[0],ENV,AgentConfig(model='mock',system_prompt='test'),Bad(),store)) == status


def test_tool_error_is_recorded(store):
    class UnknownTool(Simulated):
        async def chat(self, *args):
            response = await super().chat(*args)
            response['message']['tool_calls'][0]['function']['name']='shell'
            return response
    enqueue(store)
    run=store.claim()
    config=AgentConfig(model='mock',system_prompt='test',limits={'max_calls':1})
    assert asyncio.run(execute(run,TASKS[0],ENV,config,UnknownTool(),store)) == 'limit'
    result=store.list_runs()[0]['result']
    assert result['tool_calls'] == 1 and result['tool_errors'] == 1
    assert any(e['kind']=='tool_result' and e['payload']['error'] for e in store.events(run['id']))
