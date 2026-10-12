import asyncio
from .adapters import Ollama, Simulated
from .contracts import Experiment, Task
from .runner import execute


async def work(store, once=False):
    import uuid
    worker_id = str(uuid.uuid4())
    state = ['idle']
    store.worker_signal(worker_id,'idle')
    async def signal():
        while True:
            await asyncio.sleep(2)
            writing = asyncio.create_task(asyncio.to_thread(store.worker_signal,worker_id,state[0]))
            try:
                await asyncio.shield(writing)
            except asyncio.CancelledError:
                await writing  # Finish the in-flight write before recording stopped.
                raise
    heartbeat = asyncio.create_task(signal())
    try:
        while True:
            run = store.claim()
            if run is None:
                if once:
                    return
                await asyncio.sleep(0.5)
                continue
            state[0] = 'busy'
            store.worker_signal(worker_id,'busy')
            snapshot = store.snapshot(run["experiment_id"])
            config = Experiment.model_validate(snapshot["config"])
            task = (Task.model_validate(snapshot['branch_tasks'][run['branch']]) if snapshot.get('branch_tasks') else
                    next(Task.model_validate(t) for t in snapshot["tasks"] if t["id"] == run["task_id"]))
            adapter = Simulated() if config.adapter == "simulated" else Ollama(
                config.ollama_url, keep_alive=snapshot.get('conditions', {}).get('keep_alive', '0' if config.comparison == 'different_models' else '5m'))
            status = await execute(run, task, snapshot["environments"][task.environment], config.agents[run["branch"]], adapter, store,
                                   measurement=snapshot.get('conditions'))
            state[0] = 'idle'
            store.worker_signal(worker_id,'idle')
            if status == "interrupted":
                return
    finally:
        heartbeat.cancel()
        try:
            await heartbeat
        except asyncio.CancelledError:
            pass
        finally:
            store.worker_signal(worker_id,'stopped')
