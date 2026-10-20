"""ChatGPT subscription via the official local Codex App Server. No token access."""
import asyncio
import hashlib
import json
import os
import shutil
import tempfile
from collections import deque
from pathlib import Path


class CodexError(ValueError):
    pass


# Per-process overrides: never edit the user's Codex configuration.
FEATURES_OFF = ('apps', 'browser_use', 'browser_use_external', 'browser_use_full_cdp_access',
                'computer_use', 'shell_tool', 'shell_snapshot', 'hooks', 'image_generation',
                'view_image', 'multi_agent', 'multi_agent_v2', 'remote_plugin', 'skill_search',
                'skill_mcp_dependency_install', 'sleep_tool', 'goals', 'workspace_dependencies')
RUNTIME_INSTRUCTIONS = ('Answer the supplied text request only. Do not use tools, files, network, '
                        'skills, other agents or external environments. Return the answer as text.')


class CodexClient:
    def __init__(self, command=None):
        # This environment setting is administrator configuration, never an HTTP parameter.
        self.command = command or (json.loads(os.environ['ARENA_CODEX_COMMAND']) if os.environ.get('ARENA_CODEX_COMMAND')
                                   else [shutil.which('codex') or 'codex'])
        self.process = None
        self.sequence = 0
        self.thread_id = self.turn_id = None
        self.events = deque()
        self.cleanup_warning = None

    async def __aenter__(self):
        self.directory = tempfile.TemporaryDirectory(prefix='arena-codex-')
        args = [*self.command, 'app-server', '--listen', 'stdio://']
        for name in FEATURES_OFF:
            args.extend(['-c', f'features.{name}=false'])
        args.extend(['-c', 'web_search="disabled"', '-c', 'project_doc_max_bytes=0'])
        environment = {k:v for k,v in os.environ.items() if k.upper() not in
                       ('OPENAI_API_KEY','CODEX_API_KEY','OPENAI_BASE_URL')}
        try:
            self.process = await asyncio.create_subprocess_exec(*args, cwd=self.directory.name,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL, limit=8*1024*1024, env=environment)
            result = await self.rpc('initialize', {'clientInfo':{'name':'agent_arena_local',
                'title':'Agent Arena Local','version':'0.1.0'}, 'capabilities':{'experimentalApi':True}})
            self.version = result.get('userAgent', 'Codex App Server')
            await self.send({'method':'initialized','params':{}})
            return self
        except BaseException:
            await self.close()
            raise

    async def __aexit__(self, *args):
        await self.close()

    async def close(self):
        if self.process:
            if self.process.returncode is None:
                if self.thread_id and self.turn_id:
                    try:
                        await self.send({'id':-1,'method':'turn/interrupt',
                            'params':{'threadId':self.thread_id,'turnId':self.turn_id}})
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                self.process.stdin.close()
                try:
                    await asyncio.wait_for(self.process.wait(), 2)
                except TimeoutError:
                    # Windows can report process exit while pipe cleanup is still
                    # pending. Never turn a completed answer into a kill race.
                    if self.process.returncode is None:
                        try:
                            self.process.kill()
                        except ProcessLookupError:
                            pass
                    await self.process.wait()
            self.process = None
        if getattr(self, 'directory', None):
            # Windows may briefly retain a cwd handle after process exit.
            # A scratch-directory cleanup failure is not an inference failure.
            for attempt in range(6):
                try:
                    self.directory.cleanup()
                    break
                except PermissionError:
                    if attempt == 5:
                        self.cleanup_warning = 'No se pudo retirar un directorio temporal de Codex después de cerrar el proceso.'
                    else:
                        await asyncio.sleep(.1)

    async def send(self, message):
        self.process.stdin.write((json.dumps(message)+'\n').encode())
        await self.process.stdin.drain()

    async def receive(self):
        if self.events:
            return self.events.popleft()
        return await self.read_message()

    async def read_message(self):
        line = await self.process.stdout.readline()
        if not line:
            raise CodexError('El cliente Codex se cerró antes de completar la solicitud.')
        message = json.loads(line)
        if 'method' in message and 'id' in message:
            await self.send({'id':message['id'],'error':{'code':-32601,'message':'Arena only supports text without tools'}})
            raise CodexError('Codex solicitó una herramienta o permiso no admitido. Se detuvo la ejecución.')
        return message

    async def rpc(self, method, params):
        self.sequence += 1
        request_id = self.sequence
        await self.send({'id':request_id,'method':method,'params':params})
        while True:
            message = await self.read_message()
            if message.get('id') == request_id:
                if message.get('error'):
                    # No raw server errors: may contain account data, paths or credentials.
                    raise CodexError(f'Codex rechazó {method}. Comprueba la sesión, el modelo y los límites en el cliente oficial.')
                return message['result']
            if self.thread_id and message.get('method'):
                self.events.append(message)

    async def account(self):
        response = await self.rpc('account/read', {'refreshToken':False})
        account = response.get('account') or {}
        origin = (response.get('workspaceRouting') or {}).get('backendOrigin')
        if origin and origin.rstrip('/') != 'https://chatgpt.com':
            raise CodexError('Arena requiere el servicio oficial ChatGPT sin un endpoint alternativo.')
        if account.get('type') != 'chatgpt':
            raise CodexError('Inicia sesión con ChatGPT en el cliente oficial: codex login. Arena requiere la sesión de suscripción, no una API key.')
        identity = (response.get('workspaceRouting') or {}).get('chatgptAccountId') or account.get('email')
        if not identity:
            raise CodexError('El cliente no permite identificar la cuenta de ChatGPT. Actualiza Codex antes de vincularla.')
        return {'fingerprint':hashlib.sha256(identity.encode()).hexdigest(), 'plan':account.get('planType')}

    async def models(self):
        models, cursor = [], None
        for _ in range(20):
            page = await self.rpc('model/list', {'cursor':cursor} if cursor else {})
            models.extend({'name':m['model'], 'display_name':m['displayName']}
                          for m in page['data'] if not m.get('hidden') and 'text' in m.get('inputModalities',['text']))
            cursor = page.get('nextCursor')
            if not cursor:
                return models
        raise CodexError('El catálogo de Codex no pudo completarse.')

    async def answer(self, model, instructions, text):
        current = (await self.rpc('config/read', {'includeLayers':False})).get('config', {})
        if (current.get('model_providers') or {}).get('openai') or (current.get('chatgpt_base_url') or 'https://chatgpt.com').rstrip('/') not in ('https://chatgpt.com','https://chatgpt.com/backend-api'):
            raise CodexError('El cliente configura un proveedor OpenAI alternativo. No se envió la entrada.')
        overrides = {'web_search':'disabled', 'project_doc_max_bytes':0,
                     'include_environment_context':False, 'include_environment_context_time':False,
                     'features':{name:False for name in FEATURES_OFF},
                     'mcp_servers':{key:{'enabled':False} for key in current.get('mcp_servers',{})},
                     'plugins':{key:{'enabled':False} for key in current.get('plugins',{})}}
        thread = await self.rpc('thread/start', {'model':model,'modelProvider':'openai',
            'cwd':str(Path(self.directory.name).resolve()), 'approvalPolicy':'on-request','sandbox':'read-only',
            'ephemeral':True, 'environments':[], 'dynamicTools':[], 'config':overrides,
            'allowProviderModelFallback':False, 'baseInstructions':instructions,
            'developerInstructions':RUNTIME_INSTRUCTIONS})
        self.thread_id = thread['thread']['id']
        if thread['model'] != model or thread['modelProvider'] != 'openai':
            raise CodexError('El cliente cambió de modelo o proveedor. No se envió la entrada.')
        if thread.get('instructionSources'):
            raise CodexError('Codex cargó instrucciones externas. No se envió la entrada.')
        turn = await self.rpc('turn/start', {'threadId':self.thread_id,
            'input':[{'type':'text','text':text}], 'environments':[]})
        self.turn_id = turn['turn']['id']
        final, usage = {}, None
        while True:
            event = await self.receive()
            params = event.get('params',{})
            if params.get('threadId') != self.thread_id:
                continue
            kind = event.get('method')
            if kind == 'item/completed':
                item = params.get('item',{})
                if item.get('type') == 'agentMessage' and item.get('phase') != 'commentary':
                    final[item['id']] = item.get('text','')
                elif item.get('type') not in ('agentMessage','userMessage','reasoning'):
                    raise CodexError('El cliente intentó usar capacidades distintas de texto. Se detuvo la ejecución.')
            elif kind == 'thread/tokenUsage/updated':
                usage = params.get('tokenUsage',{}).get('total')
            elif kind == 'turn/completed' and params.get('turn',{}).get('id') == self.turn_id:
                self.turn_id = None
                if params['turn']['status'] != 'completed':
                    raise CodexError('Codex no completó la respuesta. Revisa el modelo, la conexión y los límites de tu suscripción en el cliente oficial.')
                answer = '\n'.join(final.values()).strip()
                if not answer:
                    raise CodexError('Codex terminó sin una respuesta de texto.')
                return answer, usage


async def inspect_session(fingerprint=None):
    async with asyncio.timeout(25), CodexClient() as client:
        account = await client.account()
        if fingerprint is not None and fingerprint != account['fingerprint']:
            raise CodexError('La sesión de ChatGPT del equipo cambió. Vuelve a vincularla explícitamente en Arena.')
        return account | {'models':await client.models()}
