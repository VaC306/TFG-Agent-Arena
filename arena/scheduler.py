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
from .evaluator import EVALUATOR_VERSION


def submit(store, config_path, tasks_path):
    config_path, tasks_path = Path(config_path), Path(tasks_path)
    config = Experiment.model_validate_json(config_path.read_text(encoding="utf-8"))
    tasks = [Task.model_validate_json(line) for line in tasks_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len({t.id for t in tasks}) != len(tasks):
        raise ValueError("Identificadores de tareas duplicados")
    tasks = [t for t in tasks if t.split == config.split]
    if not tasks:
        raise ValueError("No hay tareas para el split seleccionado")
    environments = {t.environment: json.loads((tasks_path.parent / t.environment).read_text(encoding="utf-8")) for t in tasks}
    return schedule(store, config, tasks, environments)


def schedule(store, config, tasks, environments, branch_tasks=None, benchmark=None, campaign=None, conditions=None):
    if campaign is None and config.adapter == "ollama" and os.environ.get("ARENA_OLLAMA_URL"):
        config.ollama_url = os.environ["ARENA_OLLAMA_URL"]
    code_files = list(Path(__file__).parent.glob("*.py"))
    code_sources = {p.name:p.read_bytes() for p in code_files}
    try:
        repo = Path(__file__).resolve().parent.parent
        git = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True)
        commit = git.stdout.strip() or None
        state = subprocess.run(['git', '-C', str(repo), 'status', '--porcelain'], capture_output=True, text=True)
        dirty = bool(state.stdout.strip()) if state.returncode == 0 else None
    except FileNotFoundError:
        commit = None
        dirty = None
    snapshot = {"config": config.model_dump(), "tasks": [t.model_dump() for t in tasks],
                "branch_tasks": branch_tasks,
                "environments": environments, "host": provenance(), "git_commit": commit, "git_worktree_dirty":dirty,
                "source_sha256": {name: hashlib.sha256(content).hexdigest() for name,content in code_sources.items()},
                "source": {name:content.decode("utf-8") for name,content in code_sources.items()},
                "conditions": {"mode": "sequential", "inputs_shared": branch_tasks is None,
                               "warmup": "none", "keep_alive": "0",
                               "resource_scope": "host_and_worker", "seed_determinism": "not guaranteed"}}
    snapshot['protocol'] = {'version':'arena-protocol-v1', 'evaluator_version':EVALUATOR_VERSION,
                            'identity_capture':'before each run; first observed identity pinned per model',
                            'order':'seeded random A/B within each case and repetition',
                            'reference_sent_to_model':False}
    if conditions is not None:
        snapshot['conditions'] = conditions
    if benchmark is not None:
        snapshot['benchmark'] = benchmark
    snapshot["data_sha256"] = hashlib.sha256(json.dumps({"tasks": snapshot["tasks"], "branch_tasks": branch_tasks, "environments": environments}, sort_keys=True).encode()).hexdigest()
    experiment_id = str(uuid.uuid4())
    rng, runs = random.Random(config.order_seed), []
    for repetition in range(config.repetitions):
        for task in tasks:
            branches = ["A", "B"]
            rng.shuffle(branches)
            for branch in branches:
                runs.append(Run(id=str(uuid.uuid4()), experiment_id=experiment_id, task_id=task.id,
                                branch=branch, repetition=repetition, position=len(runs), queued_at=time.time()))
    return store.create(experiment_id, snapshot, runs, campaign=campaign)
