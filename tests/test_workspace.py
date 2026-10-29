import asyncio
import base64
import copy
import io
import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from arena.api import create_app
from arena.store import Store
from arena.comparisons import ComparisonRequest,submit_comparison
from arena.workspace import recover_owned,baseline_report
from arena.worker import work
from arena.backups import copy_database
from arena.attachments import AttachmentUpload,prepare_attachment
from conftest import register_client

ROOT=Path(__file__).resolve().parents[1]


def body(key='request-0001'):
    return {'request_id':key,'name':'Nueva prueba','adapter':'simulated','comparison':'same_model',
            'agents':{b:{'model':'demo','system_prompt':'Responde brevemente'} for b in ('A','B')},
            'shared_input':{'text':'Hola'},'evaluation':'none'}


@pytest.fixture
def workspace(tmp_path):
    path=tmp_path/'workspace.sqlite'
    client=TestClient(create_app(path,ROOT))
    register_client(client,'alice')
    owner=client.get('/auth/session').json()['user']['id']
    return client,Store(path,owner_id=owner),path


def test_idempotency_replay_conflict_account_scope_and_concurrent_creation(workspace):
    client,store,path=workspace
    first=client.post('/comparisons',json=body())
    assert first.status_code==201
    assert client.post('/comparisons',json=body()).json()==first.json()
    reordered=body();reordered['agents']={b:reordered['agents'][b] for b in ('B','A')}
    assert client.post('/comparisons',json=reordered).json()==first.json()
    assert client.post('/comparisons',json=body()|{'name':'Otro contenido'}).status_code==422
    def submit(_):
        return submit_comparison(Store(path,owner_id=store.owner_id),ComparisonRequest.model_validate(body('concurrent-key')))
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert len(set(pool.map(submit,range(2))))==1
    other=TestClient(create_app(path,ROOT));register_client(other,'other')
    assert other.post('/comparisons',json=body()).json()!=first.json()
    assert len(client.get('/experiments').json())==2


def test_history_search_pagination_and_compact_progress(workspace):
    client,store,path=workspace
    one=client.post('/comparisons',json=body()|{'name':'Primera'}).json()['id']
    two=client.post('/comparisons',json=body('request-0002')|{'name':'Segunda'}).json()['id']
    assert client.get('/experiments?limit=1&offset=1').json()[0]['id']==one
    assert client.get('/experiments?search=segunda').json()[0]['id']==two
    assert len(client.get('/experiments?search=demo&status=pending').json())==2
    assert client.get('/experiments?adapter=ollama').json()==[]
    assert client.get('/experiments?search=%25').json()==[]
    original=store.snapshot(one)
    compact=client.get(f'/experiments/{one}?compact=true').json()['snapshot']
    assert 'source' not in compact and 'source' in original
    update=client.get(f'/experiments/{one}/progress').json()
    assert set(update)=={'runs','overviews','protocol','campaign'}
    assert store.snapshot(one)==original
    asyncio.run(work(Store(path),once=True))
    update=client.get(f'/experiments/{one}/progress').json()
    assert update['protocol']==client.get(f'/experiments/{one}').json()['protocol']


def test_recovery_stale_only_owned_and_fences_late_finish(workspace):
    client,store,path=workspace
    eid=client.post('/comparisons',json=body()).json()['id']
    run=store.claim('worker-1')
    with store.connect() as db:
        value=json.loads(db.execute('SELECT data FROM runs WHERE id=?',(run['id'],)).fetchone()[0])
        value['started_at']=time.time()-120
        db.execute('UPDATE runs SET data=? WHERE id=?',(json.dumps(value),run['id']))
    store.worker_signal('worker-1','busy')
    assert client.post('/worker/recover',json={'workers_stopped':True}).status_code==409
    store.worker_signal('worker-1','stopped')
    assert client.post('/worker/recover',json={'workers_stopped':False}).status_code==422
    assert client.post('/worker/recover',json={'workers_stopped':True}).json()=={'recovered':1}
    assert store.finish(run,{'answer':'late'},'completed')=='interrupted'
    assert store.list_runs(eid)[0]['status'] in ('queued','interrupted')
    assert len([e for e in store.events(run['id']) if e['kind']=='finished'])==1


def test_library_immutable_versions_and_account_scope(workspace):
    client,store,path=workspace
    item={'kind':'dataset','name':'Mis casos','cases':[{'id':'one','input':'Hola'}],'tags':['saludos']}
    first=client.post('/library',json=item).json()
    assert client.post('/library',json=item).json()==first
    item['cases'][0]['input']='Adiós'
    assert client.post('/library',json=item).json()['version']==2
    rows=client.get('/library').json()
    assert rows[1]['content']['cases'][0]['input']=='Hola'
    other=TestClient(create_app(path,ROOT));register_client(other,'other')
    assert other.get('/library').json()==[]
    assert client.post('/library',json={'kind':'prompt','name':' ','text':'Hola'}).status_code==422


def test_blind_review_hides_mapping_and_preserves_closed_scores(workspace):
    client,store,path=workspace
    eid=client.post('/comparisons',json=body()).json()['id']
    asyncio.run(work(Store(path),once=True))
    task=store.snapshot(eid)['tasks'][0]['id']
    response=client.post(f'/experiments/{eid}/reviews',json={'task_id':task,'repetition':0})
    assert response.status_code==201,response.text
    pair=response.json()
    assert set(pair)=={'id','task_id','input','left','right','rubric'}
    assert client.get(f'/experiments/{eid}/reviews').json()==[]
    score={'left':{'correctness':4,'clarity':3,'usefulness':5},'right':{'correctness':3,'clarity':4,'usefulness':5},'preference':'tie','comment':'Revisión humana'}
    saved=client.post('/reviews/'+pair['id'],json=score)
    assert saved.status_code==200 and set(saved.json()['mapping'].values())=={'A','B'}
    assert client.post('/reviews/'+pair['id'],json=score).json()==saved.json()
    assert client.post('/reviews/'+pair['id'],json=score|{'preference':'left'}).status_code==409
    other=TestClient(create_app(path,ROOT));register_client(other,'other')
    assert other.post('/reviews/'+pair['id'],json=score).status_code==404
    assert other.get(f'/experiments/{eid}/reviews').status_code==404
    assert len(client.get(f'/experiments/{eid}/reviews').json())==1
    assert all(r['result']['success'] is None for r in store.list_runs(eid))


def test_batch_retry_atomic_rollback_and_preflight(workspace,monkeypatch):
    client,store,path=workspace
    data=[body(),body('request-0002')]
    assert client.post('/comparisons/preflight',json=data[0]).json()['ready'] is True
    first=client.post('/comparisons/batch',json={'comparisons':data})
    assert first.status_code==201,first.text
    assert client.post('/comparisons/batch',json={'comparisons':data}).json()==first.json()
    assert len(client.get('/experiments').json())==2
    assert client.post('/comparisons/batch',json={'comparisons':[body(),body()]}).status_code==422
    from arena import workspace as module
    original=module.submit_comparison
    def broken(store,request):
        if request.request_id=='request-bad':raise ValueError('controlled failure')
        return original(store,request)
    monkeypatch.setattr(module,'submit_comparison',broken)
    response=client.post('/comparisons/batch',json={'comparisons':[body('request-new'),body('request-bad')]})
    assert response.status_code==422
    assert len(client.get('/experiments').json())==2


def test_baseline_compares_quality_only_with_matching_design(workspace):
    client,store,path=workspace
    data=body()|{'shared_input':{'text':'Hola','expected_answer':'hola'},'evaluation':'exact_match'}
    one=client.post('/comparisons',json=data).json()['id']
    two=client.post('/comparisons',json=data|{'request_id':'request-0002'}).json()['id']
    for eid,success in ((one,False),(two,True)):
        while (run:=store.claim()) is not None:
            if run['experiment_id']!=eid:
                store.finish(run,{'answer':'hola','success':True},'succeeded')
                continue
            store.finish(run,{'answer':'hola' if success else 'otra','success':success},'succeeded' if success else 'failed')
    # Explicitly create a differing quality result; no actual model is involved.
    with store.connect() as db:
        for row in db.execute('SELECT * FROM runs WHERE experiment_id=?',(two,)).fetchall():
            run=json.loads(row['data']);run['status']='succeeded';run['result']={'answer':'hola','success':True}
            db.execute("UPDATE runs SET status='succeeded',data=? WHERE id=?",(json.dumps(run),run['id']))
    report=client.get(f'/experiments/{two}/baseline/{one}').json()
    assert report['compatible'],report
    assert all(c['change']=='improved' for c in report['cases'])
    snap=store.snapshot(two);snap['config']['agents']['A']['seed']+=1
    with store.connect() as db:db.execute('UPDATE experiments SET snapshot=? WHERE id=?',(json.dumps(snap),two))
    report=baseline_report(store,two,one)
    assert not report['compatible'] and report['cases']==[]


def test_backup_restore_integrity_and_no_overwrite(workspace,tmp_path):
    client,store,path=workspace
    client.post('/comparisons',json=body())
    backup=tmp_path/'backup.sqlite';restored=tmp_path/'restored.sqlite'
    copy_database(path,backup)
    with pytest.raises(FileExistsError):copy_database(path,backup)
    copy_database(backup,restored,restore=True)
    assert len(Store(restored,owner_id=store.owner_id).list_experiments())==1
    with sqlite3.connect(restored) as db:
        assert db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]==0
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    invalid=tmp_path/'invalid.sqlite';invalid.write_bytes(b'not a database')
    with pytest.raises(sqlite3.DatabaseError):copy_database(invalid,tmp_path/'bad.sqlite')
    assert not (tmp_path/'bad.sqlite').exists()


def pdf_bytes(text='Hola PDF'):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
    writer=PdfWriter();page=writer.add_blank_page(width=200,height=100)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(f'BT /F1 12 Tf 10 50 Td ({text}) Tj ET'.encode())
    page[NameObject('/Contents')]=writer._add_object(stream)
    output=io.BytesIO();writer.write(output);return output.getvalue()


def test_pdf_text_preview_ingestion_and_rejection(workspace):
    client,store,path=workspace
    upload={'name':'entrada.pdf','data_base64':base64.b64encode(pdf_bytes()).decode()}
    preview=client.post('/attachments/preview',json=upload)
    assert preview.status_code==200,preview.text
    assert 'Hola PDF' in preview.json()['text']
    file=prepare_attachment(AttachmentUpload.model_validate(upload))
    assert file.media_type=='application/pdf' and 'Hola PDF' in file.text
    bad={'name':'entrada.pdf','data_base64':base64.b64encode(b'not pdf').decode()}
    assert client.post('/attachments/preview',json=bad).status_code==422
    assert client.post('/attachments/preview',json={'name':'scan.pdf','data_base64':base64.b64encode(pdf_bytes('')).decode()}).status_code==422


def test_streaming_assembles_content_usage_and_drops_thinking(monkeypatch):
    from arena.adapters import Ollama
    from arena.contracts import AgentConfig
    real=httpx.AsyncClient
    chunks=[{'message':{'content':'Ho','thinking':'private'}}, {'message':{'content':'la'}},
            {'done':True,'done_reason':'stop','message':{'content':''},'prompt_eval_count':2,'eval_count':2,'eval_duration':100}]
    def handler(request):
        assert json.loads(request.content)['stream'] is True
        return httpx.Response(200,text='\n'.join(json.dumps(c) for c in chunks))
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:real(transport=httpx.MockTransport(handler),**kwargs))
    adapter=Ollama('http://controlled.test');seen=[];adapter.on_chunk=seen.append
    result=asyncio.run(adapter.chat([],AgentConfig(model='demo',system_prompt='hola',tools_enabled=False),100))
    assert seen==['Ho','Hola']
    assert result['message']=={'role':'assistant','content':'Hola'} and result['eval_count']==2
    assert 'private' not in json.dumps(result)


def test_preflight_rejects_missing_vision_and_excess_context(workspace,monkeypatch):
    from PIL import Image
    from arena import workspace as module
    class Metadata:
        def __init__(self,*args,**kwargs):pass
        async def metadata(self,model):
            return {'show':{'capabilities':['completion'],'model_info':{'demo.context_length':1024}}}
    monkeypatch.setattr(module,'Ollama',Metadata)
    client,store,path=workspace
    output=io.BytesIO();Image.new('RGB',(1,1)).save(output,format='PNG')
    data=body()|{'adapter':'ollama','shared_input':{'text':'Describe la imagen','files':[{'name':'one.png','data_base64':base64.b64encode(output.getvalue()).decode()}]}}
    report=client.post('/comparisons/preflight',json=data)
    assert report.status_code==200 and report.json()['ready'] is False
    assert any('visión' in error for error in report.json()['errors'])
    assert any('contexto' in error for error in report.json()['errors'])
    assert client.get('/experiments').json()==[]


def test_streaming_cancel_preserves_partial_answer_without_scoring(tmp_path,monkeypatch):
    from test_measurement import run_fixture,Controlled
    from arena.runner import execute
    store,run,task,config=run_fixture(tmp_path)
    monkeypatch.setattr('arena.runner.sample',lambda:{'at':1,'unavailable':[]})
    class Partial(Controlled):
        on_chunk=None
        async def chat(self,*args):
            self.on_chunk('Texto parcial')
            store.cancel(run['id'])
            await asyncio.Event().wait()
    status=asyncio.run(execute(run,task,{},config,Partial(),store))
    assert status=='cancelled'
    result=next(r for r in store.list_runs(run['experiment_id']) if r['id']==run['id'])['result']
    assert result['answer']=='Texto parcial' and result['quality_evaluated'] is False
    assert result['first_visible_token_s']>=0
    assert any(e['kind']=='answer_chunk' for e in store.events(run['id']))


def test_presets_reuse_submission_key(workspace):
    client,store,path=workspace
    payload={'config':'simulated','request_id':'preset-request-1'}
    first=client.post('/experiments',json=payload)
    assert first.status_code==201
    assert client.post('/experiments',json=payload).json()==first.json()
    assert len(client.get('/experiments').json())==1
