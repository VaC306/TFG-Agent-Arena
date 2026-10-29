"""Opt-in integration against an EMPTY disposable, loopback PostgreSQL database.

ARENA_TEST_POSTGRES_URL must point to a temporary local database, never Supabase.
"""
import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
from urllib.parse import urlsplit
import pytest
from fastapi import HTTPException
from arena.accounts import Accounts, Credentials
from arena.campaigns import CampaignRequest, create_campaign, campaign_report
from arena.model_results import latest_model_results
from arena.scheduler import submit
from arena.store import Store
from arena.worker import work
from scripts.migrate_sqlite_postgres import migrate

ROOT = Path(__file__).resolve().parents[1]


def test_postgres_accounts_queue_reports_and_sqlite_import(tmp_path):
    target = os.environ.get('ARENA_TEST_POSTGRES_URL')
    if not target:
        pytest.skip('Requires a disposable local PostgreSQL database')
    assert urlsplit(target).hostname in {'127.0.0.1', 'localhost', '::1'}
    store = Store(target)
    accounts = Accounts(store)
    assert not accounts.has_users(), 'Use an empty disposable test database'
    assert store.list_experiments() == []
    uid = accounts.create_user('postgres-test', 'test-password-123', 'PG test')
    with pytest.raises(HTTPException) as duplicate:
        accounts.create_user('postgres-test', 'another-password', 'Duplicate')
    assert duplicate.value.status_code == 409
    assert accounts.login(Credentials(username='postgres-test', password='test-password-123')) == uid
    token = accounts.new_session(uid)
    assert accounts.current(token)['id'] == uid
    with pytest.raises(ValueError):
        with store.connect() as db:
            db.execute('UPDATE users SET display_name=? WHERE id=?', ('rolled back', uid))
            raise ValueError('rollback')
    assert accounts.current(token)['display_name'] == 'PG test'
    scoped = store.for_owner(uid)
    eid = submit(scoped, ROOT/'configs/simulated.json', ROOT/'data/tasks.jsonl')
    assert scoped.list_experiments()[0]['name'] == scoped.snapshot(eid)['config']['name']
    assert isinstance(scoped.list_experiments()[0]['created_at'], float)
    assert scoped.result_experiments()[0][1]['config']['adapter'] == 'simulated'
    # Competing workers may claim only one run globally.
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda _: store.claim(), range(2)))
    assert sum(run is not None for run in claims) == 1
    claimed = next(run for run in claims if run is not None)
    store.cancel(claimed['id'])
    assert store.finish(claimed, {'success': False}, 'failed') == 'cancelled'
    asyncio.run(work(store, once=True))
    assert all(run['status'] not in {'queued', 'running'} for run in scoped.list_runs(eid))
    assert any(event['kind'] == 'finished' for event in scoped.events(claimed['id']))
    cid = create_campaign(scoped, CampaignRequest(name='Postgres campaign', experiment_id=eid))
    assert scoped.list_campaigns()[0]['id'] == cid
    assert campaign_report(scoped, cid)['id'] == cid
    assert latest_model_results(scoped)
    assert scoped.clear_history(scoped.history_state()['revision']) == 1
    accounts.logout(token)
    with store.connect() as db:
        db.execute('DELETE FROM users WHERE id=?', (uid,))
        db.execute('DELETE FROM worker_signals')
    # Import preserves IDs, results, accounts and event sequencing.
    source = tmp_path/'source.sqlite'
    local = Store(source)
    local_accounts = Accounts(local)
    owner = local_accounts.create_user('import-test', 'test-password-123', 'Imported')
    local = local.for_owner(owner)
    original = submit(local, ROOT/'configs/simulated.json', ROOT/'data/tasks.jsonl')
    asyncio.run(work(local, once=True))
    with local.connect() as db:
        db.execute('INSERT INTO library_items(id,owner_id,kind,name,version,created_at,content,sha256) VALUES (?,?,?,?,?,?,?,?)',
                   ('import-library',owner,'prompt','Imported prompt',1,time.time(),json.dumps({'text':'Brief','tags':[]}), 'a'*64))
        db.execute('INSERT INTO human_reviews(id,owner_id,experiment_id,data,created_at) VALUES (?,?,?,?,?)',
                   ('import-review',owner,original,json.dumps({'rubric':'arena-human-v1','score':{'preference':'tie'}}),time.time()))
        db.execute('INSERT INTO submissions(owner_id,request_id,fingerprint,experiment_id) VALUES (?,?,?,?)',
                   (owner,'import-request','b'*64,original))
    counts = migrate(source, target)
    assert counts['experiments'] == 1
    assert counts['library_items'] == counts['human_reviews'] == counts['submissions'] == 1
    imported = store.for_owner(owner)
    assert imported.snapshot(original) == local.snapshot(original)
    assert imported.list_runs(original) == local.list_runs(original)
    assert Accounts(store).login(Credentials(username='import-test', password='test-password-123')) == owner
    assert imported.submission('import-request','b'*64) == original
    with imported.connect() as db:
        assert db.execute('SELECT name FROM library_items WHERE owner_id=?',(owner,)).fetchone()[0]=='Imported prompt'
        assert json.loads(db.execute('SELECT data FROM human_reviews WHERE owner_id=?',(owner,)).fetchone()[0])['rubric']=='arena-human-v1'
    with pytest.raises(ValueError, match='vacío'):
        migrate(source, target)
    run_id = imported.list_runs(original)[0]['id']
    before = imported.events(run_id)[-1]['seq']
    imported.event(run_id, 'after_import', {})
    assert imported.events(run_id)[-1]['seq'] > before


def test_postgres_workspace_endpoints(tmp_path):
    from fastapi.testclient import TestClient
    from arena.api import create_app
    from conftest import register_client
    from test_workspace import body
    target=os.environ.get('ARENA_TEST_POSTGRES_WORKSPACE_URL')
    if not target:
        pytest.skip('Requires a separate disposable local PostgreSQL database for workspace endpoints')
    assert urlsplit(target).hostname in {'127.0.0.1','localhost','::1'}
    store=Store(target)
    assert not Accounts(store).has_users(), 'Use an empty disposable test database'
    client=TestClient(create_app(target,ROOT))
    register_client(client,'pg-workspace')
    owner=client.get('/auth/session').json()['user']['id']
    scoped=store.for_owner(owner)
    first=client.post('/comparisons',json=body())
    assert first.status_code==201,first.text
    eid=first.json()['id']
    assert client.post('/comparisons',json=body()).json()['id']==eid
    query=client.get('/experiments?search=Nueva&adapter=simulated&status=pending&since=0&until=9999999999')
    assert query.status_code==200,query.text
    assert query.json()[0]['id']==eid
    assert client.get('/experiments?search=%25').json()==[]
    prompt={'kind':'prompt','name':'Reusable','text':'Be brief'}
    saved=client.post('/library',json=prompt)
    assert saved.status_code==201,saved.text
    assert client.post('/library',json=prompt|{'text':'New version'}).json()['version']==2
    assert len(client.get('/library').json())==2
    batch={'comparisons':[body('pg-batch-one'),body('pg-batch-two')]}
    created=client.post('/comparisons/batch',json=batch)
    assert created.status_code==201,created.text
    assert client.post('/comparisons/batch',json=batch).json()==created.json()
    assert len(client.get('/experiments?limit=1&offset=1').json())==1
    asyncio.run(work(store,once=True))
    assert client.get('/model-results').status_code==200
    assert client.get(f'/experiments/{eid}/progress').json()['overviews']['A']['pending']==0
    review=client.post(f'/experiments/{eid}/reviews',json={'task_id':'custom-input','repetition':0})
    assert review.status_code==201,review.text
    score={'left':{'correctness':4,'clarity':4,'usefulness':4},'right':{'correctness':4,'clarity':4,'usefulness':4},'preference':'tie'}
    assert client.post('/reviews/'+review.json()['id'],json=score).status_code==200
    assert len(client.get(f'/experiments/{eid}/reviews').json())==1
    # A late failure in the second creation must roll back the entire batch.
    with pytest.raises(ValueError):
        from arena.comparisons import ComparisonRequest,submit_comparison
        with scoped.atomic():
            submit_comparison(scoped,ComparisonRequest.model_validate(body('pg-rollback-key')))
            raise ValueError('rollback')
    assert scoped.submission('pg-rollback-key',ComparisonRequest.model_validate(body('pg-rollback-key')).submission()['fingerprint']) is None
