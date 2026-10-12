import asyncio
import csv
import io
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from arena.api import create_app
from arena.comparisons import ComparisonRequest,submit_comparison
from arena.contracts import AgentConfig,Task
from arena.resources import ResourceMonitor
from arena.runner import execute
from arena.store import Store
from arena.worker import work
from conftest import register_client
from test_comparisons import request_data

ROOT = Path(__file__).resolve().parents[1]


class Controlled:
    def __init__(self,mode='ok'):
        self.calls=[];self.mode=mode
    async def metadata(self,model):
        return {'adapter':'controlled','model':{'digest':'a'*64},'version':{'version':'test'},'show':{}}
    async def chat(self,messages,config,remaining):
        self.calls.append((messages,config.tools_enabled,remaining))
        if remaining == 1 and self.mode != 'ok':
            if self.mode == 'error': raise RuntimeError('Warmup offline')
            await asyncio.sleep(10)
        await asyncio.sleep(.03)
        return {'message':{'role':'assistant','content':'yes'},'done':True,'done_reason':'length' if remaining==1 else 'stop',
                'prompt_eval_count':7 if remaining==1 else 11,'eval_count':1 if remaining==1 else 2,'eval_duration':1_000_000}


def run_fixture(tmp_path):
    store=Store(tmp_path/'measure.sqlite')
    eid=submit_comparison(store,ComparisonRequest.model_validate(request_data()))
    run=store.claim()
    task=Task(id=run['task_id'],input='Private task input',expected_answer='yes',environment='empty',split='dev')
    return store,run,task,AgentConfig(model='test',system_prompt='Private instructions',tools_enabled=False)


def test_warmup_neutral_counters_separate_and_periodic_lifecycle(tmp_path,monkeypatch):
    store,run,task,config=run_fixture(tmp_path)
    count=[0]
    def sample():
        count[0]+=1
        return {'at':count[0],'worker_rss_bytes':90 if count[0]==3 else 10,'ram_available_bytes':100,'worker_cpu_s':count[0]/10,'gpu':None,'unavailable':['NVML unavailable']}
    monkeypatch.setattr('arena.runner.sample',sample)
    adapter=Controlled()
    async def check():
        status=await execute(run,task,{},config,adapter,store,{'warmup':'per_run','resource_sample_interval_s':.01})
        assert status=='succeeded'
        events=store.events(run['id']);n=len(events)
        await asyncio.sleep(.03)
        assert len(store.events(run['id']))==n  # No sampler writes survive finishing.
        result=store.list_runs(run['experiment_id'])[0]['result']
        assert result['output_tokens']==2 and result['input_tokens']==11 and result['calls']==1
        assert result['warmup']['usage']['eval_count']==1
        assert result['warmup']['status']=='completed' and result['warmup']['duration_s']>0
        assert result['failure_phase'] is None
        assert 0 < result['task_s'] < result['agent_s']
        assert result['resources']['samples']>=4 and result['resources']['peak_worker_rss_bytes']==90
        assert result['resources']['unavailable']==['NVML unavailable']
        assert {e['payload']['phase'] for e in events if e['kind']=='resources'} >= {'preparation','warmup','task','finished'}
    asyncio.run(check())
    assert adapter.calls[0]==([{'role':'user','content':'Reply OK.'}],False,1)
    assert adapter.calls[1][0][0]['content']=='Private instructions'
    assert adapter.calls[1][0][1]['content']=='Private task input'


@pytest.mark.parametrize('mode,status',[('error','failed'),('timeout','timeout'),('cancel','cancelled'),('interrupt','interrupted')])
def test_warmup_failure_never_sends_actual_input_and_releases_sampler(tmp_path,monkeypatch,mode,status):
    store,run,task,config=run_fixture(tmp_path)
    config.limits.timeout_s=.05
    adapter=Controlled(mode)
    async def check():
        pending=asyncio.create_task(execute(run,task,{},config,adapter,store,{'warmup':'per_run','resource_sample_interval_s':.01}))
        if mode in ('cancel','interrupt'):
            for _ in range(100):
                if adapter.calls:break
                await asyncio.sleep(.001)
            assert adapter.calls
            if mode=='cancel':store.cancel(run['id'])
            else:pending.cancel()
        assert await pending==status
        result=store.list_runs(run['experiment_id'])[0]['result']
        assert result['task_s'] is None and result['output_tokens']==0 and result['calls']==0
        assert result['warmup']['status']=='failed' and result['failure_phase']=='warmup'
        n=len(store.events(run['id']));await asyncio.sleep(.02)
        assert len(store.events(run['id']))==n
    asyncio.run(check())
    assert len(adapter.calls)==1


def test_sampler_failure_records_unavailability_without_failing_answer(tmp_path,monkeypatch):
    store,run,task,config=run_fixture(tmp_path)
    def broken(): raise OSError('Unavailable sensor')
    monkeypatch.setattr('arena.runner.sample',broken)
    assert asyncio.run(execute(run,task,{},config,Controlled(),store,{'resource_sample_interval_s':.01}))=='succeeded'
    result=store.list_runs(run['experiment_id'])[0]['result']
    assert result['resources']['peak_worker_rss_bytes'] is None
    assert result['resources']['unavailable']==['Sampler: OSError']
    assert result['warmup']['status']=='not_requested'


def test_identity_drift_after_warmup_blocks_actual_input(tmp_path):
    store,run,task,config=run_fixture(tmp_path)
    class Changed(Controlled):
        async def metadata(self,model):
            result=await super().metadata(model)
            result['model']['digest']=('b' if self.calls else 'a')*64
            return result
    adapter=Changed()
    assert asyncio.run(execute(run,task,{},config,adapter,store,{'warmup':'per_run'}))=='failed'
    result=store.list_runs(run['experiment_id'])[0]['result']
    assert result['task_s'] is None and result['output_tokens']==0
    assert len(adapter.calls)==1 and result['warmup']['status']=='failed'
    assert 'identidad' in result['error']


def test_legacy_policy_keeps_endpoint_sampling_and_no_warmup(tmp_path):
    store,run,task,config=run_fixture(tmp_path)
    assert asyncio.run(execute(run,task,{},config,Controlled(),store,{'warmup':'none'}))=='succeeded'
    result=store.list_runs(run['experiment_id'])[0]['result']
    assert result['resources']['samples']==2 and result['resources']['sampling']=='endpoints'


def test_policy_and_measurements_survive_api_library_campaign_and_exports(tmp_path,monkeypatch):
    path=tmp_path/'api.sqlite';client=TestClient(create_app(path,ROOT));register_client(client)
    # The sampler is real host instrumentation; the inference adapter is controlled.
    monkeypatch.setattr('arena.worker.Simulated',Controlled)
    body=request_data();body['settings']={'warmup':'per_run'}
    eid=client.post('/comparisons',json=body).json()['id']
    asyncio.run(work(Store(path),once=True))
    detail=client.get('/experiments/'+eid).json()
    assert detail['snapshot']['conditions']['warmup']=='per_run'
    assert detail['snapshot']['conditions']['keep_alive']=='5m'
    assert detail['snapshot']['conditions']['resource_sample_interval_s']==1
    result=detail['runs'][0]['result']
    assert result['warmup']['policy']=='per_run' and result['resources']['samples']>=2
    metrics=list(csv.DictReader(io.StringIO(client.get('/experiments/'+eid+'/metrics.csv').text)))
    row=next(r for r in metrics if r['id']==detail['runs'][0]['id'])
    assert float(row['task_s'])==result['task_s'] and json.loads(row['resource_summary'])==result['resources']
    samples=list(csv.DictReader(io.StringIO(client.get('/experiments/'+eid+'/resources.csv').text)))
    assert len([s for s in samples if s['run_id']==row['id']])==result['resources']['samples']
    assert len({s['phase'] for s in samples})>=2
    library=client.get('/model-results').json()['entries']
    assert all(e['conditions']['warmup_policy']=='per_run' and e['measurements'] for e in library)
    cid=client.post('/campaigns',json={'name':'Measurement','experiment_id':eid}).json()['id']
    report=client.get('/campaigns/'+cid).json()
    assert report['attempts'][0]['measurements'][0]['warmup']==result['warmup']
    evolution=list(csv.DictReader(io.StringIO(client.get('/campaigns/'+cid+'/export.csv').text)))
    assert all(json.loads(r['measurements']) for r in evolution)
    assert 'sampling_overhead_s' in client.get('/campaigns/'+cid+'/export.md').text
    assert 'peak_worker_rss_bytes' in client.get('/experiments/'+eid+'/report.md').text
    repeat=client.post('/campaigns/'+cid+'/attempts',json={'request_id':__import__('uuid').uuid4().__str__()}).json()['id']
    assert Store(path).snapshot(repeat)['conditions']==detail['snapshot']['conditions']
    other=TestClient(create_app(path,ROOT));register_client(other,'other')
    assert other.get('/experiments/'+eid+'/resources.csv').status_code==404
    assert client.post('/comparisons',json=body | {'settings':{'warmup':'cold'}}).status_code==422
