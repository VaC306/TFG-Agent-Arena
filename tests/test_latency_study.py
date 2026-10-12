import copy
import csv
import io
import json
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from arena.api import create_app
from arena.comparisons import ComparisonRequest,submit_comparison
from arena.evaluator import EVALUATOR_VERSION
from arena.latency_analysis import latency_analysis
from arena.protocol import inference_identity
from arena.store import Store
from arena.scheduler import schedule
from arena.contracts import Task
from arena.task_analysis import campaign_analysis
from conftest import register_client
from test_task_analysis import fixture

ROOT = Path(__file__).resolve().parents[1]


def cohort(count=10,repetitions=2,attempts=2):
    snapshot,reports,evidence=fixture(count=count,repetitions=repetitions,attempts=attempts)
    snapshot['config'].update(latency_study=True,planned_attempts=2,order_policy='balanced',warmup='per_run')
    snapshot['conditions'].update(order_policy='balanced',warmup='per_run',latency_plan={
        'version':'arena-latency-plan-v1','endpoint':'task_s','planned_attempts':2})
    for attempt,item in zip(reports,evidence):
        item['snapshot']=copy.deepcopy(snapshot)
        for i,task in enumerate(snapshot['tasks']):
            for repetition in range(repetitions):
                first='A' if (i+repetition)%2==0 else 'B'
                base=repetition*count*2+i*2
                for run in [r for r in item['runs'] if r['task_id']==task['id'] and r['repetition']==repetition]:
                    position=base+(run['branch']!=first)
                    time=attempt['sequence']*10000+position*10
                    t=1+i/8+(0 if run['branch']=='A' else [-.25,0,.5][i%3])
                    run.update(position=position,started_at=time,finished_at=time+8,status='succeeded')
                    run['result'].update(success=True,answer='yes',agent_s=t+1,task_s=t,warmup={'status':'completed','duration_s':.5})
    return snapshot,reports,evidence


def analysis(snapshot,reports,evidence):return campaign_analysis(snapshot,reports,evidence)['latency']


def test_balanced_order_is_seeded_per_case_and_validated_before_storage(tmp_path):
    store=Store(tmp_path/'order.sqlite')
    body={'name':'Plan','adapter':'simulated','comparison':'same_model','agents':{b:{'model':'demo','system_prompt':'same'} for b in ('A','B')},
          'dataset':[{'id':f'case-{i}','input':f'unique {i}','expected_answer':'yes'} for i in range(3)],
          'settings':{'latency_study':True,'warmup':'per_run','order_policy':'balanced','planned_attempts':2},'repetitions':4}
    ids=[submit_comparison(store,ComparisonRequest.model_validate(body)) for _ in range(2)]
    sequences=[]
    for eid in ids:
        runs=store.list_runs(eid);sequences.append([(r['task_id'],r['repetition'],r['branch']) for r in sorted(runs,key=lambda r:r['position'])])
        for task in ['case-0','case-1','case-2']:
            first=[min((r for r in runs if r['task_id']==task and r['repetition']==rep),key=lambda r:r['position'])['branch'] for rep in range(4)]
            assert first.count('A')==first.count('B')==2 and first[0]!=first[1] and first[0]==first[2]
    assert sequences[0]==sequences[1]
    assert store.snapshot(ids[0])['conditions']['latency_plan']['endpoint']=='task_s'
    for change in [{'repetitions':3},{'settings':body['settings']|{'warmup':'none'}},{'settings':body['settings']|{'order_policy':'random'}},
                   {'settings':body['settings']|{'planned_attempts':21}}, {'evaluation':'none'}, {'dataset':[{'id':'open','input':'open'}]}]:
        with pytest.raises(ValueError):ComparisonRequest.model_validate(body|change)
    config=ComparisonRequest.model_validate(body).config()
    with pytest.raises(ValueError):schedule(store,config,[Task(id='open',input='open',environment='empty',split='dev')],{'empty':{}})


def test_latency_clusters_tasks_and_separates_quality_coverage_and_order():
    s,r,e=cohort();a=analysis(s,r,e)
    assert a['timed_pairs']==a['planned_pairs']==40 and a['missing_pairs']==0
    assert a['incorrect_pairs']==a['unscored_pairs']==0 and not a['unbalanced']
    assert a['interval'] is not None and a['mean_B_minus_A_s']==pytest.approx(.05)
    assert a==analysis(s,r,e)
    b=analysis(*cohort(repetitions=10))
    assert b['timed_pairs']==200 and b['task_count']==10
    assert b['interval']==a['interval'] and b['method']['input_sha256']==a['method']['input_sha256']
    assert a['by_order']['A']['timed_pairs']==a['by_order']['B']['timed_pairs']==20


@pytest.mark.parametrize('problem',['pilot','simulation','few_tasks','unfinished','no_plan','duplicate','unbalanced','overlap','missing','negative','nan','impossible','wrong','unscored','warmup','constant','excluded','independent'])
def test_interval_guards_and_no_imputation(problem):
    s,r,e=cohort(count=3 if problem=='few_tasks' else 10,attempts=1 if problem=='unfinished' else 2)
    run=e[0]['runs'][0]
    if problem=='pilot':s['config']['split']='dev'
    elif problem=='simulation':s['config']['adapter']='simulated'
    elif problem=='no_plan':s['conditions']['latency_plan']=None
    elif problem=='duplicate':s['tasks'][1]['input']=s['tasks'][0]['input']
    elif problem=='unbalanced':
        for item in e:
            for run in item['runs']:run['position']=0 if run['branch']=='A' else 100
    elif problem=='overlap':run['finished_at']=run['started_at']+100
    elif problem in ('missing','negative','nan','impossible'):
        run['result']['task_s']={'missing':None,'negative':-1,'nan':float('nan'),'impossible':100}[problem]
    elif problem=='wrong':run['result']['success']=False
    elif problem=='unscored':run['result']['success']=None
    elif problem=='warmup':run['result']['warmup']['status']='not_requested'
    elif problem=='constant':
        for item in e:
            for run in item['runs']:run['result']['task_s']=1
    elif problem=='excluded':r[0].update(compatible=False,warnings=['External deviation'])
    elif problem=='independent':s['conditions']['inputs_shared']=False
    a=analysis(s,r,e)
    assert a['interval'] is None and a['interval_unavailable_reasons']
    if problem in ('missing','negative','nan','impossible'):
        assert a['mean_B_minus_A_s'] is None and a['missing_pairs']==1
    if problem=='wrong':assert a['incorrect_pairs']==1 and a['mean_B_minus_A_s'] is not None
    if problem=='unscored':assert a['unscored_pairs']==1
    if problem=='independent':assert not a['pairs'] and a['mean_B_minus_A_s'] is None


def test_planned_study_limits_attempts_atomically_and_exports(tmp_path):
    path=tmp_path/'plan.sqlite';client=TestClient(create_app(path,ROOT));register_client(client)
    body={'name':'Controlled latency','adapter':'ollama','comparison':'different_models','split':'eval','repetitions':2,
          'agents':{b:{'model':'model-'+b,'system_prompt':'same'} for b in ('A','B')},
          'dataset':[{'id':f'case-{i}','input':f'unique {i}','expected_answer':'yes'} for i in range(10)],
          'settings':{'latency_study':True,'warmup':'per_run','order_policy':'balanced','planned_attempts':2}}
    eid=client.post('/comparisons',json=body).json()['id'];store=Store(path)
    def finish():
        while run:=store.claim():
            i=int(run['task_id'].split('-')[1]);b=run['branch'];t=.001+i*.001+(0 if b=='A' else [.001,.002,.004][i%3])
            identity=inference_identity('model-'+b,{'version':{'version':'controlled'},'model':{'digest':b.lower()*64},'show':{}})
            store.finish(run,{'answer':'yes','success':True,'agent_s':t+.01,'task_s':t,
                              'warmup':{'status':'completed','duration_s':.005},'evaluator_version':EVALUATOR_VERSION,'inference_identity':identity},'succeeded')
    finish()
    cid=client.post('/campaigns',json={'name':'Plan','experiment_id':eid}).json()['id']
    initial=client.get('/campaigns/'+cid).json()['analysis']
    assert initial['latency']['interval'] is None and initial['paired']['interval'] is None
    key=str(uuid.uuid4());url='/campaigns/'+cid+'/attempts'
    second=client.post(url,json={'request_id':key}).json()['id'];finish()
    assert client.post(url,json={'request_id':key}).json()['id']==second
    assert client.post(url,json={'request_id':str(uuid.uuid4())}).status_code==409
    report=client.get('/campaigns/'+cid).json();a=report['analysis']['latency']
    assert a['interval'] is not None and a['timed_pairs']==40
    exported=client.get('/campaigns/'+cid+'/export.json').json()
    assert exported['analysis']['latency']==a
    assert 'latency_analysis.py' in exported['analysis_sources']
    rows=list(csv.DictReader(io.StringIO(client.get('/campaigns/'+cid+'/latency.csv').text)))
    assert len(rows)==40
    for row,pair in zip(rows,a['pairs']):
        assert float(row['B_minus_A_s'])==pair['B_minus_A_s'] and row['first']==pair['first']
    assert 'Tiempo de tarea y orden de ejecución' in client.get('/campaigns/'+cid+'/export.md').text
    other=TestClient(create_app(path,ROOT));register_client(other,'other')
    assert other.get('/campaigns/'+cid+'/latency.csv').status_code==404
    annotation={'request_id':str(uuid.uuid4()),'kind':'deviation','text':'External load changed'}
    assert client.post(f'/campaigns/{cid}/attempts/{second}/annotations',json=annotation).status_code==201
    assert client.get('/campaigns/'+cid).json()['analysis']['latency']['interval'] is None
