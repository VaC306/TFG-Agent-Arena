"""Controlled stdio peer for tests. Never contacts a model or reads credentials."""
import json
import os
import sys

def emit(message):
    print(json.dumps(message),flush=True)

for line in sys.stdin:
    message = json.loads(line)
    method, params = message.get('method'), message.get('params',{})
    if 'id' not in message:
        continue
    result = {}
    if method == 'initialize': result = {'userAgent':'controlled-codex-test-v1'}
    elif method == 'account/read':
        result = {'account':{'type':os.environ.get('FAKE_CODEX_ACCOUNT','chatgpt'),'email':'fictitious@example.invalid','planType':'plus'},
                  'workspaceRouting':{'chatgptAccountId':os.environ.get('FAKE_CODEX_ID','fictitious-account'),'backendOrigin':'https://chatgpt.com'}}
    elif method == 'model/list': result = {'data':[{'model':'fixture-gpt','displayName':'Controlled GPT','inputModalities':['text']}], 'nextCursor':None}
    elif method == 'config/read': result = {'config':{'mcp_servers':{'controlled':{}},'plugins':{'controlled':{}},
        'chatgpt_base_url':os.environ.get('FAKE_CODEX_ORIGIN','https://chatgpt.com/backend-api/')}}
    elif method == 'thread/start':
        assert params['environments'] == [] and params['dynamicTools'] == [] and params['ephemeral']
        assert params['config']['mcp_servers']['controlled']['enabled'] is False
        assert params['config']['plugins']['controlled']['enabled'] is False
        assert params['config']['features']['shell_tool'] is False
        result = {'thread':{'id':'thread-test'},'model':params['model'],'modelProvider':'openai','instructionSources':[]}
    elif method == 'turn/start':
        text = params['input'][0]['text']
        if os.environ.get('FAKE_CODEX_CAPTURE'):
            with open(os.environ['FAKE_CODEX_CAPTURE'],'a',encoding='utf-8') as log: log.write(json.dumps(params)+'\n')
        reply = {'id':message['id'],'result':{'turn':{'id':'turn-test'}}}
        if '[early]' not in text:
            emit(reply)
        if '[block]' in text:
            # Keep consuming stdin so an interrupt/EOF is respected.
            continue
        if '[tool]' in text:
            emit({'id':999,'method':'item/commandExecution/requestApproval','params':{'threadId':'thread-test'}})
            continue
        emit({'method':'item/completed','params':{'threadId':'thread-test','turnId':'turn-test',
            'item':{'type':'reasoning','id':'reason-test','text':'PRIVATE_REASONING_MUST_NOT_PERSIST'}}})
        emit({'method':'item/completed','params':{'threadId':'thread-test','turnId':'turn-test',
            'item':{'type':'agentMessage','phase':'final_answer','id':'answer-test','text':'hola'}}})
        if '[no-usage]' not in text:
            emit({'method':'thread/tokenUsage/updated','params':{'threadId':'thread-test','turnId':'turn-test',
                  'tokenUsage':{'total':{'inputTokens':11,'outputTokens':2}}}})
        emit({'method':'turn/completed','params':{'threadId':'thread-test','turn':{'id':'turn-test',
              'status':'failed' if '[fail]' in text else 'completed','error':{'message':'PRIVATE_SERVER_ERROR'}}}})
        if '[early]' in text:
            emit(reply)
        continue
    emit({'id':message['id'],'result':result})
