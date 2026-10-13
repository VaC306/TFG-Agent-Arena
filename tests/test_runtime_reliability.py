import asyncio
import sqlite3
import threading
import httpx
import pytest
from arena.resources import ResourceMonitor,resources_csv
from arena.runner import execute
from arena.model_results import summarize
from arena.store import Store
from controlled_time import Clock,Ticks,checkpoint
from test_measurement import run_fixture,Controlled
from arena.worker import work


def test_suite_rejects_live_http_but_accepts_mock_transport():
    with pytest.raises(AssertionError,match='Live HTTP'):
        httpx.get('http://127.0.0.1:11434/api/tags')
    async def check():
        async with httpx.AsyncClient() as client:
            with pytest.raises(AssertionError,match='Live HTTP'):
                await client.get('http://127.0.0.1:11434/api/tags')
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(200,json={'controlled':True}))) as client:
            assert (await client.get('http://controlled.test')).json()=={'controlled':True}
    asyncio.run(check())


def test_store_closes_connections_and_rolls_back_failed_transactions(tmp_path):
    store=Store(tmp_path/'store.sqlite')
    with store.connect() as db:db.execute('CREATE TABLE probe(value TEXT)')
    with pytest.raises(sqlite3.ProgrammingError):db.execute('SELECT 1')
    with pytest.raises(RuntimeError):
        with store.connect() as db:
            db.execute('INSERT INTO probe VALUES (?)',('should roll back',))
            raise RuntimeError('abort')
    with store.connect() as db:assert db.execute('SELECT COUNT(*) FROM probe').fetchone()[0]==0


def test_resource_write_failure_does_not_leave_run_running(tmp_path,monkeypatch):
    store,run,task,config=run_fixture(tmp_path)
    monkeypatch.setattr('arena.runner.sample',lambda:{'at':1,'worker_rss_bytes':10,'unavailable':[]})
    original=store.event;failed=[False]
    def event(run_id,kind,payload):
        if kind=='resources' and not failed[0]:
            failed[0]=True;raise sqlite3.OperationalError('controlled telemetry failure')
        return original(run_id,kind,payload)
    monkeypatch.setattr(store,'event',event)
    assert asyncio.run(execute(run,task,{},config,Controlled(),store))=='succeeded'
    result=store.list_runs(run['experiment_id'])[0]['result']
    assert result['resources']['samples']==1
    assert result['resources']['unavailable']==['Trace persistence: OperationalError']
    assert len(resources_csv(store,run['experiment_id']).splitlines())==2
    assert len([e for e in store.events(run['id']) if e['kind']=='finished'])==1


@pytest.mark.parametrize('action',['interrupt','cancel'])
def test_interruption_while_final_capture_is_blocked_preserves_terminal_state(tmp_path,monkeypatch,action):
    store,run,task,config=run_fixture(tmp_path)
    captured=asyncio.Event();release=threading.Event();calls=[0]
    async def check():
        loop=asyncio.get_running_loop()
        def sample():
            calls[0]+=1
            if calls[0]==2:
                loop.call_soon_threadsafe(captured.set)
                if not release.wait(5):raise RuntimeError('test capture was not released')
            return {'at':1,'worker_rss_bytes':10,'unavailable':[]}
        monkeypatch.setattr('arena.runner.sample',sample)
        pending=asyncio.create_task(execute(run,task,{},config,Controlled(),store))
        try:
            await checkpoint(captured)
            if action=='interrupt':pending.cancel();await asyncio.sleep(0);pending.cancel()
            else:store.cancel(run['id'])
        finally:release.set()
        assert await asyncio.wait_for(pending,5)==('interrupted' if action=='interrupt' else 'cancelled')
        result=store.list_runs(run['experiment_id'])[0]['result']
        assert result['answer']=='yes' and not result['quality_evaluated']
        if action=='interrupt':assert result['failure_phase']=='measurement_cleanup'
        assert summarize(store.list_runs(run['experiment_id']),[task.model_dump()])['evaluated']==0
        assert result['resources']['samples']==2 and calls[0]==2
        events=store.events(run['id']);assert events[-1]['kind']=='finished'
        assert len([e for e in events if e['kind']=='finished'])==1
    asyncio.run(check())


def test_manual_sampling_clock_and_idempotent_stop(tmp_path):
    store,run,_,_=run_fixture(tmp_path);clock,ticks=Clock(),Ticks()
    monitor=ResourceMonitor(store,run['id'],1,lambda:{'at':1,'worker_rss_bytes':10,'unavailable':[]},wait=ticks,clock=clock)
    async def check():
        await monitor.start();clock.advance(2);await monitor.stop()
        count=len(store.events(run['id']));await monitor.stop();ticks.release();await asyncio.sleep(0)
        assert len(store.events(run['id']))==count and monitor.task.done() and monitor.closed
        assert monitor.summary()['samples']==2 and monitor.summary()['observed_span_s']==2
    asyncio.run(check())


def test_heartbeat_freshness_boundaries_use_controlled_clock(tmp_path):
    clock=Clock();store=Store(tmp_path/'signals.sqlite',clock=clock)
    assert store.worker_status()['state']=='unobserved'
    store.worker_signal('a','idle');clock.advance(15)
    assert store.worker_status()['state']=='active'
    clock.advance(.001);assert store.worker_status()['state']=='no_recent_signal'
    store.worker_signal('a','busy');assert store.worker_status()['busy_workers']==1
    clock.advance(-1);assert store.worker_status()['state']=='no_recent_signal'


def test_repeated_interruption_during_initial_capture_drains_before_finishing(tmp_path,monkeypatch):
    store,run,task,config=run_fixture(tmp_path)
    entered=asyncio.Event();release=threading.Event();calls=[]
    async def check():
        loop=asyncio.get_running_loop()
        def sample():
            calls.append(len(calls)+1)
            if len(calls)==1:
                loop.call_soon_threadsafe(entered.set)
                assert release.wait(5)
            return {'at':1,'unavailable':[]}
        monkeypatch.setattr('arena.runner.sample',sample)
        pending=asyncio.create_task(execute(run,task,{},config,Controlled(),store))
        try:
            await checkpoint(entered)
            pending.cancel();await asyncio.sleep(0);pending.cancel();await asyncio.sleep(0)
            assert not pending.done()
        finally:release.set()
        assert await asyncio.wait_for(pending,5)=='interrupted'
        events=store.events(run['id'])
        assert calls==[1,2] and events[-1]['kind']=='finished'
        assert len([e for e in events if e['kind']=='resources'])==2
        assert len([e for e in events if e['kind']=='finished'])==1
    asyncio.run(check())


def test_repeated_worker_interruption_drains_heartbeat_before_stopped(tmp_path,monkeypatch):
    store=Store(tmp_path/'heartbeat.sqlite');ticks=Ticks()
    entered=asyncio.Event();release=threading.Event();states=[]
    original=store.worker_signal
    async def check():
        loop=asyncio.get_running_loop()
        def signal(worker_id,state):
            if state=='idle' and states:
                loop.call_soon_threadsafe(entered.set)
                assert release.wait(5)
            original(worker_id,state);states.append(state)
        monkeypatch.setattr(store,'worker_signal',signal)
        pending=asyncio.create_task(work(store,heartbeat_wait=ticks))
        ticks.release()
        try:
            await checkpoint(entered)
            pending.cancel();await asyncio.sleep(0);pending.cancel();await asyncio.sleep(0)
            assert not pending.done()
        finally:release.set()
        with pytest.raises(asyncio.CancelledError):await asyncio.wait_for(pending,5)
        assert states==['idle','idle','stopped']
        assert store.worker_status()['state']=='no_recent_signal'
    asyncio.run(check())
