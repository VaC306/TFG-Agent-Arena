import asyncio
from .adapters import Ollama, Simulated
from .contracts import Experiment, Task
from .runner import execute


async def work(store, once=False):
    while True:
        run = store.claim()
        if run is None:
            if once:
                return
            await asyncio.sleep(0.5)
            continue
        snapshot = store.snapshot(run["experiment_id"])
        config = Experiment.model_validate(snapshot["config"])
        task = (Task.model_validate(snapshot['branch_tasks'][run['branch']]) if snapshot.get('branch_tasks') else
                next(Task.model_validate(t) for t in snapshot["tasks"] if t["id"] == run["task_id"]))
        adapter = Simulated() if config.adapter == "simulated" else Ollama(
            config.ollama_url, keep_alive='0' if config.comparison == 'different_models' else '5m')
        status = await execute(run, task, snapshot["environments"][task.environment], config.agents[run["branch"]], adapter, store)
        if status == "interrupted":
            return
