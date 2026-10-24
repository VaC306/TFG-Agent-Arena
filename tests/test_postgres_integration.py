"""Opt-in integration against an EMPTY disposable, loopback PostgreSQL database.

ARENA_TEST_POSTGRES_URL must point to a temporary local database, never Supabase.
"""
import asyncio
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
    counts = migrate(source, target)
    assert counts['experiments'] == 1
    imported = store.for_owner(owner)
    assert imported.snapshot(original) == local.snapshot(original)
    assert imported.list_runs(original) == local.list_runs(original)
    assert Accounts(store).login(Credentials(username='import-test', password='test-password-123')) == owner
    with pytest.raises(ValueError, match='vacío'):
        migrate(source, target)
    run_id = imported.list_runs(original)[0]['id']
    before = imported.events(run_id)[-1]['seq']
    imported.event(run_id, 'after_import', {})
    assert imported.events(run_id)[-1]['seq'] > before
