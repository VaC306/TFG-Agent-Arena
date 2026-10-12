import asyncio
import csv
import io
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from arena.api import create_app
from arena.store import Store
from arena.worker import work
from conftest import register_client
from test_campaigns import source

ROOT = Path(__file__).resolve().parents[1]


def campaign(tmp_path):
    path = tmp_path/'notes.sqlite'
    client = TestClient(create_app(path,ROOT))
    register_client(client)
    eid = source(client,path)
    cid = client.post('/campaigns',json={'name':'Conditions','experiment_id':eid}).json()['id']
    return path,client,cid,eid


def test_annotations_idempotent_append_only_account_scoped_and_exports(tmp_path):
    path,client,cid,eid = campaign(tmp_path)
    before = client.get('/experiments/'+eid).json()['snapshot']
    url = f'/campaigns/{cid}/attempts/{eid}/annotations'
    body = {'request_id':str(uuid.uuid4()),'kind':'observation','text':' GPU libre al inicio\nobservación posterior '}
    assert client.post(url,json=body).status_code == 201
    assert client.post(url,json=body).status_code == 201
    report = client.get('/campaigns/'+cid).json()
    assert report['attempts'][0]['compatible']
    assert len(report['attempts'][0]['annotations']) == 1
    assert client.post(url,json=body | {'text':'changed'}).status_code == 409
    assert client.post(url,json=body | {'request_id':str(uuid.uuid4()),'text':'  '}).status_code == 422
    assert client.post(url,json=body | {'text':'x'*2001}).status_code == 422
    assert client.post(url,json=body | {'kind':'measurement'}).status_code == 422
    assert client.post(f'/campaigns/{cid}/attempts/missing/annotations',json=body).status_code == 404
    other = TestClient(create_app(path,ROOT)); register_client(other,'other')
    assert other.post(url,json=body).status_code == 404
    deviation = {'request_id':str(uuid.uuid4()),'kind':'deviation','text':'Carga externa distinta durante este intento.'}
    assert client.post(url,json=deviation).status_code == 201
    report = client.get('/campaigns/'+cid).json()
    attempt = report['attempts'][0]
    assert not attempt['compatible'] and len(attempt['annotations']) == 2
    assert len(report['analysis']['excluded_attempts']) == 1
    assert report['analysis']['paired']['mean_B_minus_A'] is None
    assert report['analysis']['paired']['interval'] is None
    assert client.get('/experiments/'+eid).json()['snapshot'] == before
    detail = client.get('/experiments/'+eid).json()
    assert detail['annotations'] == attempt['annotations']
    assert any(deviation['text'] in w for w in detail['protocol']['warnings'])
    exported = client.get('/experiments/'+eid+'/reproducibility.json').json()
    assert exported['annotations'] == attempt['annotations']
    assert deviation['text'] in client.get('/experiments/'+eid+'/report.md').text
    for row in csv.DictReader(io.StringIO(client.get('/experiments/'+eid+'/metrics.csv').text)):
        assert json.loads(row['operator_annotations']) == attempt['annotations']
    for row in csv.DictReader(io.StringIO(client.get('/campaigns/'+cid+'/export.csv').text)):
        assert row['compatible'] == 'False'
        assert json.loads(row['annotations']) == attempt['annotations']
    assert client.get('/campaigns/'+cid+'/export.json').json()['attempts'][0]['annotations'] == attempt['annotations']
    assert deviation['text'] in client.get('/campaigns/'+cid+'/export.md').text
    entries = client.get('/model-results').json()['entries']
    assert all(e['external_deviation'] and e['annotations'] == attempt['annotations'] for e in entries)
    revision = client.get('/profile/history').json()['revision']
    assert client.request('DELETE','/profile/history',json={'confirmation':'clear-history','revision':revision}).status_code == 200
    with Store(path).connect() as db:
        assert db.execute('SELECT COUNT(*) FROM attempt_annotations').fetchone()[0] == 0


def test_concurrent_annotation_retry_is_atomic(tmp_path):
    path,client,cid,eid = campaign(tmp_path)
    owner = client.get('/auth/session').json()['user']['id']
    key = str(uuid.uuid4())
    def save(_):
        return Store(path,owner).annotate_attempt(cid,eid,key,'observation','Same note')
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(save,range(2))) == [key,key]
    assert len(Store(path,owner).annotations(eid)) == 1


def test_worker_status_signal_stale_stopped_and_owner_queue(tmp_path,monkeypatch):
    path = tmp_path/'worker.sqlite'
    client,other = TestClient(create_app(path,ROOT)),TestClient(create_app(path,ROOT))
    register_client(client);register_client(other,'other')
    store = Store(path)
    assert client.get('/worker/status').json()['state'] == 'unobserved'
    from test_comparisons import request_data
    client.post('/comparisons',json=request_data())
    status = client.get('/worker/status').json()
    assert status['queued'] == 2 and status['running'] == 0 and status['oldest_pending_age_s'] >= 0
    assert other.get('/worker/status').json()['queued'] == 0
    store.worker_signal('a','idle');store.worker_signal('b','busy')
    status = client.get('/worker/status').json()
    assert status['state'] == 'active' and status['active_workers'] == 2 and status['busy_workers'] == 1
    assert 'id' not in status and 'runs' not in status
    store.worker_signal('a','stopped')
    assert client.get('/worker/status').json()['active_workers'] == 1
    with store.connect() as db:
        db.execute('UPDATE worker_signals SET updated_at=updated_at-16 WHERE id=?',('b',))
    assert client.get('/worker/status').json()['state'] == 'no_recent_signal'
    assert client.get('/worker/status').json()['queued'] == 2
    assert TestClient(create_app(path,ROOT)).get('/worker/status').status_code == 401


def test_worker_heartbeats_during_run_and_stops_on_cancellation(tmp_path,monkeypatch):
    path,client,_,_ = campaign(tmp_path)
    from test_comparisons import request_data
    client.post('/comparisons',json=request_data())
    entered = asyncio.Event()
    async def blocked(*args):
        entered.set()
        await asyncio.Event().wait()
    monkeypatch.setattr('arena.worker.execute',blocked)
    store = Store(path)
    async def check():
        task = asyncio.create_task(work(store))
        await entered.wait()
        first = store.worker_status()['last_signal_at']
        await asyncio.sleep(2.1)
        status = store.worker_status()
        assert status['active_workers'] == status['busy_workers'] == 1
        assert status['last_signal_at'] > first
        task.cancel()
        with pytest.raises(asyncio.CancelledError): await task
        assert store.worker_status()['state'] == 'no_recent_signal'
        assert any(r['status']=='running' for r in store.list_runs())  # No automatic recovery.
    asyncio.run(check())


def test_once_worker_records_stopped_and_exceptions_release_signal(tmp_path,monkeypatch):
    store = Store(tmp_path/'empty.sqlite')
    asyncio.run(work(store,once=True))
    assert store.worker_status()['state'] == 'no_recent_signal'
    monkeypatch.setattr(store,'claim',lambda: (_ for _ in ()).throw(RuntimeError('broken')))
    with pytest.raises(RuntimeError): asyncio.run(work(store))
    assert store.worker_status()['active_workers'] == 0
