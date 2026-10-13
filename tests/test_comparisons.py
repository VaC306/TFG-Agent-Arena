import asyncio
import base64
import copy
import io
import json
from pathlib import Path
import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from arena.api import create_app
from arena.attachments import AttachmentUpload, prepare_attachment
from arena.comparisons import ComparisonRequest, submit_comparison
from arena.contracts import AgentConfig, Task
from arena.adapters import Ollama, Simulated
from arena.evaluator import evaluate
from arena.export import paired_summary, csv_text
from arena.runner import execute
from arena.store import Store
from arena.worker import work

ROOT = Path(__file__).resolve().parents[1]


def upload(name='datos.txt', data=b'Hola A'):
    return {'name': name, 'data_base64': base64.b64encode(data).decode()}


def request_data(mode='same_model'):
    data = {'name':'Archivos de prueba', 'adapter':'simulated', 'comparison':mode,
            'agents': {branch: {'model':'demo', 'system_prompt':'Resume el archivo', 'prompt_template':'summary'} for branch in ['A','B']}}
    if mode == 'same_model':
        data['branch_inputs'] = {'A': {'text':'Resume A', 'files':[upload()]},
                                 'B': {'text':'Resume B', 'files':[upload(data=b'Hola B')]}}
    else:
        data['agents']['B']['model'] = 'otro'
        data['shared_input'] = {'text':'Resume el contenido', 'files':[upload()]}
    return data


@pytest.mark.parametrize('mode', ['same_model', 'different_models'])
def test_input_design_roundtrip(tmp_path, mode):
    store = Store(tmp_path/'test.sqlite')
    data = request_data(mode)
    eid = submit_comparison(store, ComparisonRequest.model_validate(data))
    original = copy.deepcopy(store.snapshot(eid))
    asyncio.run(work(store, once=True))
    runs = store.list_runs(eid)
    assert len(runs) == 2 and all(r['status'] == 'completed' for r in runs)
    assert all(r['result']['success'] is None for r in runs)
    assert store.snapshot(eid) == original
    messages = {r['branch']: next(e['payload']['messages'] for e in store.events(r['id']) if e['kind']=='input') for r in runs}
    if mode == 'same_model':
        assert 'Hola A' in messages['A'][1]['content'] and 'Hola B' not in messages['A'][1]['content']
        assert 'Hola B' in messages['B'][1]['content'] and 'Hola A' not in messages['B'][1]['content']
    else:
        assert messages['A'][1] == messages['B'][1]
    summary = paired_summary(store, eid)
    assert summary['success_rate'] == {'A':None,'B':None}
    assert summary['pairs'] == 0 and summary['mcnemar_exact_p'] is None
    assert 'not_evaluated' in csv_text(store,eid)


@pytest.mark.parametrize('case', ['shared_missing', 'shared_and_private', 'different_in_single', 'equal_in_dual', 'alias_equal', 'branch_missing'])
def test_invalid_comparison_rules(case):
    data = request_data('different_models' if case in ['shared_missing','shared_and_private','equal_in_dual','alias_equal'] else 'same_model')
    if case=='shared_missing': del data['shared_input']
    if case=='shared_and_private': data['branch_inputs'] = {'A':{'text':'different'},'B':{'text':'other'}}
    if case=='different_in_single': data['agents']['B']['model']='other'
    if case=='equal_in_dual': data['agents']['B']['model']='demo'
    if case=='alias_equal': data['agents']['B']['model']='demo:latest'
    if case=='branch_missing': del data['branch_inputs']['B']
    with pytest.raises(ValueError): ComparisonRequest.model_validate(data)


def test_shared_input_for_one_model_preserves_references_and_original_design(tmp_path):
    data = request_data()
    data['shared_input'] = data.pop('branch_inputs')['A'] | {'expected_answer': 'PRIVATE_REFERENCE'}
    store = Store(tmp_path / 'shared.sqlite')
    eid = submit_comparison(store, ComparisonRequest.model_validate(data))
    original = copy.deepcopy(store.snapshot(eid))
    assert original['branch_tasks'] is None
    assert original['conditions']['inputs_shared'] is True
    asyncio.run(work(store, once=True))
    assert store.snapshot(eid) == original
    messages = [next(e['payload']['messages'] for e in store.events(run['id']) if e['kind'] == 'input') for run in store.list_runs(eid)]
    assert messages[0][1] == messages[1][1]
    assert 'Hola A' in messages[0][1]['content']
    assert 'PRIVATE_REFERENCE' not in json.dumps(messages)
    data['branch_inputs'] = {'A': {'text': 'one'}, 'B': {'text': 'two'}}
    with pytest.raises(ValueError, match='no ambas'):
        ComparisonRequest.model_validate(data)


@pytest.mark.parametrize('name,data', [
    ('file.txt',b'plain'), ('file.json',b'{"value":42}'), ('file.csv',b'name,value\nuno,1')])
def test_text_attachment(name,data):
    attachment = prepare_attachment(AttachmentUpload.model_validate(upload(name,data)))
    assert attachment.text == data.decode() and attachment.size == len(data)
    assert base64.b64decode(attachment.data_base64) == data and len(attachment.sha256)==64


def test_model_receives_readable_multiline_files_without_reference():
    from arena.attachments import user_message
    from arena.contracts import Task
    csv_content = 'sku,cantidad\nA,2\nB,3\n'
    json_content = '{"A":10,"B":5}'
    attachments = [prepare_attachment(AttachmentUpload.model_validate(upload(name,data.encode())))
                   for name,data in [('cantidades.csv',csv_content),('catalogo.json',json_content)]]
    task = Task(id='files',split='dev',input='Calculate the total',environment='empty',
                expected_answer='REFERENCE-NOT-FOR-MODEL',attachments=attachments)
    message = user_message(task)
    assert csv_content in message['content'] and json_content in message['content']
    assert 'cantidades.csv' in message['content'] and 'catalogo.json' in message['content']
    assert 'REFERENCE-NOT-FOR-MODEL' not in message['content']


@pytest.mark.parametrize('name,data', [
    ('bad.json',b'{bad'), ('nan.json',b'{"x":NaN}'), ('bad.txt',b'\xff'),
    ('bad.txt',b'\x00'), ('../file.txt',b'x'), ('file.exe',b'MZ'), ('fake.png',b'not an image'),
    ('big.txt',b'x'*20001), ('empty.txt',b''), ('file.csv',b'"unclosed')])
def test_invalid_files(name,data):
    with pytest.raises(ValueError): prepare_attachment(AttachmentUpload.model_validate(upload(name,data)))


def test_invalid_base64_and_file_count():
    with pytest.raises(ValueError): prepare_attachment(AttachmentUpload(name='file.txt',data_base64='%%%'))
    data=request_data()
    data['branch_inputs']['A']['files']=[upload()]*5
    with pytest.raises(ValueError): ComparisonRequest.model_validate(data)


def test_combined_attachment_text_limit(tmp_path):
    data=request_data()
    data['branch_inputs']['A']['files']=[upload('one.txt',b'a'*12000),upload('two.txt',b'b'*12000)]
    with pytest.raises(ValueError,match='20.000'):
        submit_comparison(Store(tmp_path/'test.sqlite'),ComparisonRequest.model_validate(data))


def image_upload():
    buffer=io.BytesIO()
    Image.new('RGB',(4,4),'red').save(buffer,format='PNG')
    return upload('red.png',buffer.getvalue())


@pytest.mark.parametrize('vision', [True,False])
def test_vision_gate_and_payload(tmp_path,vision):
    class Model(Simulated):
        received=None
        async def metadata(self,model): return {'show':{'capabilities':['vision'] if vision else []}}
        async def chat(self,messages,config,remaining):
            self.received=messages
            return await super().chat(messages,config,remaining)
    data=request_data('different_models')
    data['shared_input']['files']=[image_upload()]
    store=Store(tmp_path/'test.sqlite')
    eid=submit_comparison(store,ComparisonRequest.model_validate(data))
    run=store.claim()
    snapshot=store.snapshot(eid)
    task=Task.model_validate(snapshot['tasks'][0])
    adapter=Model()
    status=asyncio.run(execute(run,task,{'orders':[]},AgentConfig.model_validate(snapshot['config']['agents'][run['branch']]),adapter,store))
    assert status == ('completed' if vision else 'failed')
    if vision: assert adapter.received[1]['images'] == [data['shared_input']['files'][0]['data_base64']]
    else: assert adapter.received is None


def test_reference_is_not_in_messages_and_exact_evaluation(tmp_path):
    data=request_data()
    data['branch_inputs']['A']['expected_answer']='SECRET_REFERENCE'
    store=Store(tmp_path/'test.sqlite')
    eid=submit_comparison(store,ComparisonRequest.model_validate(data))
    asyncio.run(work(store,once=True))
    a=next(r for r in store.list_runs(eid) if r['branch']=='A')
    assert a['status']=='failed' and a['result']['success'] is False
    assert 'SECRET_REFERENCE' not in json.dumps(store.events(a['id']))
    task=Task(id='free',split='dev',input='hello',environment='empty',expected_answer='42')
    assert evaluate(' 42\n',task,[])['success']
    assert not evaluate('43',task,[])['success']


def test_cancellation_without_reference_is_not_scored(tmp_path):
    store=Store(tmp_path/'test.sqlite')
    eid=submit_comparison(store,ComparisonRequest.model_validate(request_data()))
    for run in store.list_runs(eid): store.cancel(run['id'])
    assert paired_summary(store,eid)['success_rate']=={'A':None,'B':None}


def test_custom_api_and_models_unavailable(tmp_path,monkeypatch):
    async def offline(self): raise httpx.ConnectError('offline')
    monkeypatch.setattr(Ollama,'models',offline)
    with TestClient(create_app(tmp_path/'test.sqlite',ROOT)) as client:
        from conftest import register_client
        register_client(client)
        assert len(client.get('/prompt-templates').json())==6
        assert client.get('/models').json()['available'] is False
        response=client.post('/comparisons',json=request_data())
        assert response.status_code==201
        snapshot=client.get('/experiments/'+response.json()['id']).json()['snapshot']
        assert snapshot['branch_tasks']['B']['attachments'][0]['text']=='Hola B'
        bad=request_data()
        bad['branch_inputs']['A']['files']=[upload('file.json',b'SECRET_INVALID_JSON')]
        result=client.post('/comparisons',json=bad)
        assert result.status_code==422 and 'SECRET' not in result.text
        assert client.post('/comparisons',content=b'x'*(12*1024*1024+1)).status_code==413


def test_ollama_multimodal_no_tools_and_unload(monkeypatch):
    requests=[]
    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200,json={'message':{'role':'assistant','content':'ok'}})
    original=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs: original(transport=httpx.MockTransport(handler),**kwargs))
    config=AgentConfig(model='vision',system_prompt='describe',tools_enabled=False)
    messages=[{'role':'user','content':'describe','images':[image_upload()['data_base64']]}]
    asyncio.run(Ollama('http://localhost:11434',keep_alive='0').chat(messages,config,100))
    assert requests[0]['messages']==messages and 'tools' not in requests[0]
    assert requests[0]['keep_alive']=='0'
