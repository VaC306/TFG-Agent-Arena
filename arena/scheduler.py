import hashlib
import json
import os
import random
import subprocess
import time
import uuid
from pathlib import Path
from .contracts import Experiment, Task, Run
from .resources import provenance


def submit(store, config_path, tasks_path):
    config_path, tasks_path = Path(config_path), Path(tasks_path)
    config = Experiment.model_validate_json(config_path.read_text(encoding="utf-8"))
    if config.adapter == "ollama" and os.environ.get("ARENA_OLLAMA_URL"):
        config.ollama_url = os.environ["ARENA_OLLAMA_URL"]
    tasks = [Task.model_validate_json(line) for line in tasks_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len({t.id for t in tasks}) != len(tasks):
        raise ValueError("Identificadores de tareas duplicados")
    tasks = [t for t in tasks if t.split == config.split]
    if not tasks:
        raise ValueError("No hay tareas para el split seleccionado")
    environments = {t.environment: json.loads((tasks_path.parent / t.environment).read_text(encoding="utf-8")) for t in tasks}
    code_files = list(Path(__file__).parent.glob("*.py"))
    try:
        git = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
        commit = git.stdout.strip() or None
    except FileNotFoundError:
        commit = None
    snapshot = {"config": config.model_dump(), "tasks": [t.model_dump() for t in tasks],
                "environments": environments, "host": provenance(), "git_commit": commit,
                "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in code_files},
                "source": {p.name: p.read_text(encoding="utf-8") for p in code_files},
                "conditions": {"mode": "sequential", "warmup": "none", "keep_alive": "5m", "resource_scope": "host_and_worker", "seed_determinism": "not guaranteed"}}
    snapshot["data_sha256"] = hashlib.sha256(json.dumps({"tasks": snapshot["tasks"], "environments": environments}, sort_keys=True).encode()).hexdigest()
    experiment_id = str(uuid.uuid4())
    rng, runs = random.Random(config.order_seed), []
    for repetition in range(config.repetitions):
        for task in tasks:
            branches = ["A", "B"]
            rng.shuffle(branches)
            for branch in branches:
                runs.append(Run(id=str(uuid.uuid4()), experiment_id=experiment_id, task_id=task.id,
                                branch=branch, repetition=repetition, position=len(runs), queued_at=time.time()))
    store.create(experiment_id, snapshot, runs)
    return experiment_id
