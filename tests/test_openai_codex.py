import asyncio
import json
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from arena.api import create_app
from arena.comparisons import ComparisonRequest, submit_comparison
from arena.openai_codex import CodexClient, CodexError, inspect_session
from arena.store import Store
from arena.worker import work
from conftest import register_client

ROOT = Path(__file__).resolve().parents[1]

def test_process_exit_race_during_cleanup():
    class Stdin:
        def close(self): pass
    class ExitingProcess:
        returncode=None
        stdin=Stdin()
        waits=0
        async def wait(self):
            self.waits+=1
            if self.waits==1: raise TimeoutError()
            return 0
        def kill(self):
            self.returncode=0
            raise ProcessLookupError()
    client=CodexClient(command=['controlled'])
    process=ExitingProcess();client.process=process
    asyncio.run(client.close())
    assert client.process is None and process.waits==2

@pytest.mark.parametrize('failures',[1,6])
def test_temporary_directory_lock_does_not_discard_answer(failures):
    class LockedDirectory:
        calls=0
        def cleanup(self):
            self.calls+=1
            if self.calls<=failures: raise PermissionError('controlled Windows cwd lock')
    client=CodexClient(command=['controlled']);client.directory=LockedDirectory()
    asyncio.run(client.close())
    assert client.directory.calls==min(failures+1,6)
    assert bool(client.cleanup_warning)==(failures==6)

@pytest.fixture(autouse=True)
def fake_client(monkeypatch):
    monkeypatch.setenv('ARENA_CODEX_COMMAND',json.dumps([sys.executable,str(ROOT/'tests/fake_codex.py')]))
    monkeypatch.delenv('FAKE_CODEX_ACCOUNT',raising=False)
    monkeypatch.delenv('FAKE_CODEX_ID',raising=False)

def design(text='Saluda',reference=None):
    return ComparisonRequest.model_validate({'name':'ChatGPT controlado','adapter':'codex','comparison':'same_model',
        'agents':{b:{'model':'fixture-gpt','system_prompt':'Responde brevemente'} for b in ['A','B']},
        'shared_input':{'text':text,'expected_answer':reference}})

def linked_store(tmp_path):
    store=Store(tmp_path/'isolated.sqlite',owner_id='local-test')
    session=asyncio.run(inspect_session())
    store.link_provider(session['fingerprint'])
    return store

def test_native_protocol_and_account_mismatch(monkeypatch):
    session=asyncio.run(inspect_session())
    assert session['models']==[{'name':'fixture-gpt','display_name':'Controlled GPT'}]
    assert 'email' not in session
    with pytest.raises(CodexError,match='cambió'): asyncio.run(inspect_session('another-account'))
    monkeypatch.setenv('FAKE_CODEX_ACCOUNT','apiKey')
    with pytest.raises(CodexError,match='no una API key'): asyncio.run(inspect_session())

@pytest.mark.parametrize('text,reference,status', [('Saluda',None,'completed'),('Saluda','hola','succeeded'),
    ('Saluda','adios','failed'),('[early]',None,'completed'),('[no-usage]',None,'completed'),('[fail]',None,'failed'),('[tool]',None,'failed')])
def test_worker_text_usage_references_and_errors(tmp_path,monkeypatch,text,reference,status):
    capture=tmp_path/'sent.jsonl';monkeypatch.setenv('FAKE_CODEX_CAPTURE',str(capture))
    store=linked_store(tmp_path)
    eid=submit_comparison(store,design(text,reference))
    asyncio.run(work(Store(store.path),once=True))
    for run in store.list_runs(eid):
        assert run['status']==status
        result=run['result']
        assert result['server_tps'] is None and result['server_eval_s'] is None
        assert result['inference_identity']['identifier']=='fixture-gpt'
        evidence=json.dumps(store.events(run['id']))
        assert 'PRIVATE_REASONING' not in evidence and 'PRIVATE_SERVER_ERROR' not in evidence
        if text=='[no-usage]': assert result['input_tokens'] is None and result['usage_complete'] is False
        if text=='Saluda': assert result['input_tokens']==11 and result['usage_complete'] is True
    if reference: assert reference not in capture.read_text(encoding='utf-8')

@pytest.mark.parametrize('action,status',[('cancel','cancelled'),('unlink','failed'),('timeout','timeout')])
def test_cancel_timeout_and_unlink(tmp_path,action,status):
    store=linked_store(tmp_path)
    request=design('[block]');request.settings.timeout_s=1
    eid=submit_comparison(store,request)
    async def run():
        worker=asyncio.create_task(work(Store(store.path),once=True))
        for _ in range(100):
            active=next((r for r in store.list_runs(eid) if r['status']=='running'),None)
            if active and store.events(active['id']): break
            await asyncio.sleep(.02)
        assert active
        if action=='cancel':
            for r in store.list_runs(eid): store.cancel(r['id'])
        elif action=='unlink': store.link_provider(None)
        await asyncio.wait_for(worker,10)
    asyncio.run(run())
    assert store.list_runs(eid)[0]['status']==status

def test_changed_native_account_does_not_send_input(tmp_path,monkeypatch):
    store=linked_store(tmp_path);eid=submit_comparison(store,design())
    capture=tmp_path/'sent.jsonl';monkeypatch.setenv('FAKE_CODEX_CAPTURE',str(capture));monkeypatch.setenv('FAKE_CODEX_ID','changed')
    asyncio.run(work(Store(store.path),once=True))
    assert all(r['status']=='failed' for r in store.list_runs(eid))
    assert not capture.exists()

def test_alternative_endpoint_does_not_send_input(tmp_path,monkeypatch):
    store=linked_store(tmp_path);eid=submit_comparison(store,design())
    capture=tmp_path/'sent.jsonl';monkeypatch.setenv('FAKE_CODEX_CAPTURE',str(capture))
    monkeypatch.setenv('FAKE_CODEX_ORIGIN','https://example.invalid/backend-api/')
    asyncio.run(work(Store(store.path),once=True))
    assert all(r['status']=='failed' for r in store.list_runs(eid))
    assert not capture.exists()

def test_profile_isolation_and_http_validation(tmp_path):
    app=create_app(tmp_path/'api.sqlite',ROOT)
    with TestClient(app) as a,TestClient(app) as b:
        register_client(a,'first');register_client(b,'second')
        assert a.get('/openai/status').json()=={'linked':False}
        assert a.post('/comparisons',json=design().model_dump()).status_code==422
        assert a.post('/openai/connect').status_code==200
        assert a.get('/openai/models').json()['models'][0]['name']=='fixture-gpt'
        assert b.get('/openai/status').json()=={'linked':False}
        assert b.get('/openai/models').status_code==422
        assert a.post('/comparisons',json=design().model_dump()).status_code==201
        assert a.post('/openai/disconnect').json()=={'linked':False}
        assert a.get('/openai/models').status_code==422

def test_unowned_scheduling_and_unsupported_capabilities(tmp_path):
    with pytest.raises(ValueError,match='Vincula'): submit_comparison(Store(tmp_path/'none.sqlite'),design())
    body=design().model_dump();body['shared_input']['files']=[{'name':'x.txt','data_base64':'eA=='}]
    with pytest.raises(ValueError,match='solo texto'): ComparisonRequest.model_validate(body)
    body=design().model_dump();body['settings']['warmup']='per_run'
    with pytest.raises(ValueError,match='calentamiento'): ComparisonRequest.model_validate(body)
