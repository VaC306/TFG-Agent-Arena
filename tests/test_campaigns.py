import asyncio
import copy
import csv
import io
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from arena.api import create_app
from arena.campaigns import CampaignRequest, create_campaign, repeat_campaign, campaign_report
from arena.store import Store
from arena.worker import work
from conftest import register_client
from test_comparisons import request_data

ROOT = Path(__file__).resolve().parents[1]


def source(client,path,mode='different_models'):
    body = request_data(mode)
    response = client.post('/comparisons',json=body)
    assert response.status_code == 201
    eid = response.json()['id']
    asyncio.run(work(Store(path),once=True))
    return eid


def test_campaign_roundtrip_frozen_inputs_worker_exports_and_history(tmp_path,monkeypatch):
    path = tmp_path/'campaigns.sqlite'
    client = TestClient(create_app(path,ROOT))
    register_client(client)
    eid = source(client,path,'same_model')  # Distinct branch inputs and attached files must survive.
    before = client.get('/experiments/'+eid).json()['snapshot']
    response = client.post('/campaigns',json={'name':'Frozen campaign','experiment_id':eid})
    assert response.status_code == 201,response.text
    cid = response.json()['id']
    # Creation is idempotent, and never modifies the original snapshot or runs.
    assert client.post('/campaigns',json={'name':'Retry','experiment_id':eid}).json()['id'] == cid
    assert client.get('/experiments/'+eid).json()['snapshot'] == before
    assert client.get('/experiments/'+eid).json()['campaign'] == {'id':cid,'sequence':1}
    assert client.get('/campaigns').json()[0]['attempts'] == 1
    key = str(uuid.uuid4())
    monkeypatch.setenv('ARENA_OLLAMA_URL','http://127.0.0.1:1')
    response = client.post('/campaigns/'+cid+'/attempts',json={'request_id':key})
    assert response.status_code == 201,response.text
    second = response.json()['id']
    assert second != eid
    assert client.post('/campaigns/'+cid+'/attempts',json={'request_id':key}).json()['id'] == second
    assert client.post('/campaigns/'+cid+'/attempts',json={'request_id':str(uuid.uuid4())}).status_code == 409
    assert client.post('/campaigns/'+cid+'/attempts',json={'request_id':str(uuid.uuid4()),'repetitions':3}).status_code == 422
    partial = client.get('/campaigns/'+cid).json()
    assert partial['pending'] == 2
    assert partial['attempts'][1]['compatible'] is False
    state = client.get('/profile/history').json()
    assert client.request('DELETE','/profile/history',json={'confirmation':'clear-history','revision':state['revision']}).status_code == 409
    replay = client.get('/experiments/'+second).json()['snapshot']
    for field in ('config','tasks','branch_tasks','environments','conditions','data_sha256'):
        assert replay[field] == before[field]
    assert replay['campaign']['sequence'] == 2
    asyncio.run(work(Store(path),once=True))
    detail = client.get('/campaigns/'+cid).json()
    assert detail['pending'] == 0 and len(detail['attempts']) == 2
    assert all(a['compatible'] and a['complete'] for a in detail['attempts'])
    assert all(a['overviews']['A']['planned_evaluable'] == 0 for a in detail['attempts'])
    json_export = client.get('/campaigns/'+cid+'/export.json')
    assert json_export.status_code == 200 and 'attachment;' in json_export.headers['content-disposition']
    exported = json_export.json()
    assert exported['baseline_snapshot'] == before
    assert len(exported['evidence']) == 2
    assert exported['attempts'] == detail['attempts']
    rows = list(csv.DictReader(io.StringIO(client.get('/campaigns/'+cid+'/export.csv').text)))
    assert len(rows) == 4
    for row in rows:
        overview = detail['attempts'][int(row['attempt'])-1]['overviews'][row['branch']]
        for metric in ('correct','pending','unscored','execution_errors','cancelled','evaluated','planned_evaluable'):
            assert int(row[metric]) == overview[metric]
    report = client.get('/campaigns/'+cid+'/export.md').text
    assert 'Sin casos con referencia evaluable' in report and '## Intento 2' in report
    assert 'ni se declara un ganador' in report
    assert 'entradas independientes' in report
    # History deletion also removes campaign-owned copies of inputs and sources.
    state = client.get('/profile/history').json()
    assert client.request('DELETE','/profile/history',json={'confirmation':'clear-history','revision':state['revision']}).status_code == 200
    assert client.get('/campaigns').json() == []
    assert client.get('/campaigns/'+cid).status_code == 404


def test_campaigns_and_all_exports_are_account_scoped(tmp_path):
    path = tmp_path/'scoped.sqlite'
    alice, bob = TestClient(create_app(path,ROOT)),TestClient(create_app(path,ROOT))
    assert alice.get('/campaigns').status_code == 401
    register_client(alice)
    register_client(bob,'other')
    eid = source(alice,path)
    assert bob.post('/campaigns',json={'name':'Private','experiment_id':eid}).status_code == 404
    cid = alice.post('/campaigns',json={'name':'Private','experiment_id':eid}).json()['id']
    assert bob.get('/campaigns').json() == []
    for suffix in ('','/export.json','/export.csv','/export.md'):
        assert bob.get('/campaigns/'+cid+suffix).status_code == 404
    assert bob.post('/campaigns/'+cid+'/attempts',json={'request_id':str(uuid.uuid4())}).status_code == 404


def test_campaign_rejects_pending_source_and_extra_mutable_design(tmp_path):
    client = TestClient(create_app(tmp_path/'validate.sqlite',ROOT))
    register_client(client)
    eid = client.post('/comparisons',json=request_data()).json()['id']
    assert client.post('/campaigns',json={'name':'Pending','experiment_id':eid}).status_code == 409
    assert client.post('/campaigns',json={'name':' ','experiment_id':eid}).status_code == 422
    assert client.post('/campaigns',json={'name':'Mutable','experiment_id':eid,'dataset':[]}).status_code == 422


def test_concurrent_attempts_have_no_orphans_and_retry_after_completion_is_idempotent(tmp_path):
    path = tmp_path/'concurrent.sqlite'
    client = TestClient(create_app(path,ROOT))
    owner = register_client(client)['id']
    eid = source(client,path)
    store = Store(path,owner_id=owner)
    cid = create_campaign(store,CampaignRequest(name='Concurrent',experiment_id=eid))
    key = uuid.uuid4()
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(lambda _:repeat_campaign(Store(path,owner_id=owner),cid,key),range(2)))
    assert len(set(ids)) == 1 and len(store.list_experiments()) == 2
    asyncio.run(work(Store(path),once=True))
    assert repeat_campaign(store,cid,key) == ids[0]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(repeat_campaign,Store(path,owner_id=owner),cid,uuid.uuid4()) for _ in range(2)]
        successes, errors = [],[]
        for future in futures:
            try: successes.append(future.result())
            except ValueError as error: errors.append(error)
    assert len(successes) == len(errors) == 1
    assert len(store.campaign(cid)['attempts']) == len(store.list_experiments()) == 3


@pytest.mark.parametrize('field',['source_sha256','host','conditions','config','tasks'])
def test_campaign_warns_about_changed_conditions_without_pooling(tmp_path,field):
    path = tmp_path/'changed.sqlite'
    client = TestClient(create_app(path,ROOT))
    owner = register_client(client)['id']
    eid = source(client,path)
    store = Store(path,owner_id=owner)
    cid = create_campaign(store,CampaignRequest(name='Changes',experiment_id=eid))
    repeat = repeat_campaign(store,cid,uuid.uuid4())
    asyncio.run(work(Store(path),once=True))
    real_snapshot = store.snapshot
    def changed(experiment_id):
        snapshot = copy.deepcopy(real_snapshot(experiment_id))
        if experiment_id == repeat:
            if field == 'source_sha256': snapshot[field]['runner.py'] = 'changed'
            elif field == 'host': snapshot[field]['cpu'] = 'Different CPU'
            elif field == 'conditions': snapshot[field]['keep_alive'] = '5m'
            elif field == 'config': snapshot[field]['agents']['A']['system_prompt'] += ' changed'
            else: snapshot[field][0]['input'] += ' changed'
        return snapshot
    store.snapshot = changed
    report = campaign_report(store,cid)
    assert report['attempts'][0]['compatible'] is True
    assert report['attempts'][1]['compatible'] is False
    assert report['attempts'][1]['warnings']
    assert 'overviews' not in report  # No pooled campaign quality score.


@pytest.mark.parametrize('changed',['digest','server'])
def test_campaign_pins_model_and_server_before_chat(tmp_path,monkeypatch,changed):
    class Controlled:
        digest = 'a'*64
        server = 'test-server'
        chats = 0
        def __init__(self,*args,**kwargs): pass
        async def metadata(self,model):
            return {'version':{'version':self.server},'model':{'digest':self.digest},'show':{}}
        async def chat(self,messages,config,remaining):
            Controlled.chats += 1
            return {'message':{'content':'ok'},'done':True,'prompt_eval_count':1,'eval_count':1,'eval_duration':1}
    monkeypatch.setattr('arena.worker.Ollama',Controlled)
    path = tmp_path/'pin.sqlite'
    client = TestClient(create_app(path,ROOT))
    register_client(client)
    body = request_data('different_models');body['adapter']='ollama'
    eid = client.post('/comparisons',json=body).json()['id']
    asyncio.run(work(Store(path),once=True))
    cid = client.post('/campaigns',json={'name':'Pinned','experiment_id':eid}).json()['id']
    before = client.get('/experiments/'+eid).json()['snapshot']
    if changed == 'digest': Controlled.digest = 'b'*64
    else: Controlled.server = 'new-server'
    monkeypatch.setenv('ARENA_OLLAMA_URL','http://127.0.0.1:1')
    repeat = client.post('/campaigns/'+cid+'/attempts',json={'request_id':str(uuid.uuid4())}).json()['id']
    assert client.get('/experiments/'+repeat).json()['snapshot']['config']['ollama_url'] == before['config']['ollama_url']
    asyncio.run(work(Store(path),once=True))
    assert Controlled.chats == 2
    runs = client.get('/experiments/'+repeat).json()['runs']
    assert all(r['status'] == 'failed' and 'campaña' in r['result']['error'] for r in runs)
    report = client.get('/campaigns/'+cid).json()
    assert report['attempts'][1]['compatible'] is False
    assert all(s['execution_errors'] == 1 and s['evaluated'] == 0 for s in report['attempts'][1]['overviews'].values())


def test_real_campaign_requires_verified_identity(tmp_path):
    path = tmp_path/'unverified.sqlite'
    client = TestClient(create_app(path,ROOT))
    register_client(client)
    body = request_data('different_models');body['adapter']='ollama'
    eid = client.post('/comparisons',json=body).json()['id']
    for run in Store(path).list_runs(eid): Store(path).cancel(run['id'])
    assert client.post('/campaigns',json={'name':'Unverified','experiment_id':eid}).status_code == 409


def test_export_reads_runs_once_for_consistent_summary_and_evidence(tmp_path):
    path = tmp_path/'export.sqlite'
    client = TestClient(create_app(path,ROOT))
    owner = register_client(client)['id']
    eid = source(client,path)
    store = Store(path,owner_id=owner)
    cid = create_campaign(store,CampaignRequest(name='Consistent export',experiment_id=eid))
    real_runs = store.list_runs
    reads = []
    def only_once(experiment_id):
        assert experiment_id not in reads, 'Export re-read a live result after computing its metrics'
        reads.append(experiment_id)
        return real_runs(experiment_id)
    store.list_runs = only_once
    report = campaign_report(store,cid,include_evidence=True)
    assert reads == [eid]
    assert sum(s['finished'] for s in report['attempts'][0]['overviews'].values()) == len(report['evidence'][0]['runs'])


def test_cancelled_results_are_consistent_in_campaign_library_and_exports(tmp_path):
    path = tmp_path/'cancelled.sqlite'
    client = TestClient(create_app(path,ROOT))
    register_client(client)
    data = request_data('different_models')
    data['shared_input']['expected_answer'] = '42'
    eid = client.post('/comparisons',json=data).json()['id']
    store = Store(path)
    for run in store.list_runs(eid):
        store.cancel(run['id'])
    detail = client.get('/experiments/'+eid).json()
    for branch in ('A','B'):
        summary = detail['overviews'][branch]
        assert summary['cancelled'] == summary['finished'] == summary['planned_evaluable'] == 1
        assert summary['execution_errors'] == summary['evaluated'] == summary['timed_answers'] == 0
        assert detail['protocol']['branches'][branch]['answers'] == 0
    entries = client.get('/model-results').json()['entries']
    assert len(entries) == 2
    assert all(e['summary']['cancelled'] == 1 and e['summary']['execution_errors'] == 0 for e in entries)
    rows = list(csv.DictReader(io.StringIO(client.get('/experiments/'+eid+'/metrics.csv').text)))
    assert all(r['status'] == r['outcome'] == 'cancelled' and r['quality_evaluated'] == 'False' for r in rows)
    markdown = client.get('/experiments/'+eid+'/report.md').text
    assert markdown.count('Errores de ejecución: 0. Canceladas: 1.') == 2
    assert markdown.count('Repetición 1 · Cancelada') == 2
    response = client.post('/campaigns',json={'name':'Cancellation audit','experiment_id':eid})
    assert response.status_code == 201, response.text
    cid = response.json()['id']
    report = client.get('/campaigns/'+cid+'/export.json').json()
    for values in report['analysis']['tasks'][0]['branches'].values():
        assert values['summary']['cancelled'] == 1 and values['summary']['execution_errors'] == 0
        assert values['series'][0]['outcomes'] == ['cancelled']
        assert values['coverage'] == 0 and values['quality_rate'] is None
    for endpoint in ('export.csv','analysis.csv'):
        rows = list(csv.DictReader(io.StringIO(client.get('/campaigns/'+cid+'/'+endpoint).text)))
        assert len(rows) == 2
        assert all(r['cancelled'] == '1' and r['execution_errors'] == '0' for r in rows)
    markdown = client.get('/campaigns/'+cid+'/export.md').text
    assert '"cancelled": 1' in markdown and '"execution_errors": 0' in markdown
