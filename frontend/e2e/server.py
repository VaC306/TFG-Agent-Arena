"""Test-only API + real worker. No production history or model server access."""
import asyncio
from contextlib import asynccontextmanager
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


class ControlledAdapter:
    def __init__(self, *args, **kwargs): pass

    async def models(self):
        return [{'name':'fixture:latest','digest':'a'*64,'details':{'quantization_level':'fixture'}}]

    async def metadata(self, model):
        return {'adapter':'e2e-controlled','model':(await self.models())[0],
                'version':{'version':'e2e-v1'},'show':{'capabilities':['completion']}}

    async def chat(self, messages, config, remaining):
        text = next((m['content'] for m in messages if m['role']=='user'), '')
        if '[block]' in text:
            await asyncio.Event().wait()  # Real worker cancellation/deadline, no fixed delay.
        if '[fail]' in text:
            raise RuntimeError('Controlled adapter failure')
        return {'message':{'role':'assistant','content':'hola'},'done':True,'done_reason':'stop',
                'prompt_eval_count':11,'eval_count':2,'eval_duration':1_000_000}


if __name__ == '__main__':
    # Set before importing api: its module-level application must also stay isolated.
    temporary = Path(os.environ['ARENA_E2E_DB_DIRECTORY']).resolve()
    if not temporary.is_dir() or not temporary.name.startswith('arena-e2e-'):
        raise ValueError('Use npm run e2e to create a temporary database directory')
    os.environ['ARENA_DB'] = str(temporary/'arena.sqlite')
    os.environ['ARENA_ROOT'] = str(ROOT)
    import json
    os.environ['ARENA_CODEX_COMMAND'] = json.dumps([sys.executable,str(ROOT/'tests/fake_codex.py')])
    os.environ.pop('ARENA_OLLAMA_URL', None)
    from arena import api, worker, resources, runner, codex_runner
    from arena.store import Store
    import uvicorn
    api.Ollama = worker.Ollama = ControlledAdapter
    # Browser tests must not wait for a host GPU driver. Sensor integration has
    # dedicated Python coverage; keep the real monitor lifecycle and persistence.
    def sample():
        return {'at':time.time(),'scope':'host_and_worker','worker_rss_bytes':1024,
                'worker_cpu_s':0.0,'ram_available_bytes':4096,'gpu':None,
                'unavailable':['Controlled E2E sensor; not a hardware measurement']}
    resources.sample = runner.sample = codex_runner.sample = sample
    app = api.create_app()

    @asynccontextmanager
    async def lifespan(app):
        pending = asyncio.create_task(worker.work(Store(os.environ['ARENA_DB'])))
        try:
            yield
        finally:
            pending.cancel()
            try: await pending
            except asyncio.CancelledError: pass
    app.router.lifespan_context = lifespan
    uvicorn.run(app, host='127.0.0.1', port=int(os.environ['ARENA_E2E_API_PORT']), forwarded_allow_ips='127.0.0.1')
