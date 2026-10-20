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
    if config.adapter == 'codex':
        if not store.provider_link():
            raise ValueError('Vincula primero ChatGPT para esta cuenta local de Arena.')
        if any(t.attachments or t.criteria for t in tasks) or any(t.get('attachments') or t.get('criteria') for t in (branch_tasks or {}).values()):
            raise ValueError('ChatGPT solo admite tareas de texto sin herramientas ni adjuntos.')
    if config.latency_study and (branch_tasks is not None or not tasks or any(not(t.criteria or t.expected_answer is not None and t.evaluation!='none') for t in tasks)):
        raise ValueError('El estudio de latencia requiere tareas compartidas con referencia evaluable; también se aplica a la CLI.')
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
                               "warmup": config.warmup, "keep_alive": "5m" if config.warmup == 'per_run' else "0",
                               "resource_sample_interval_s": 1.0,
                               "resource_sampling": "periodic-v1; observed samples, not guaranteed peaks",
                               "order_policy":config.order_policy,
                               "latency_plan":{'version':'arena-latency-plan-v1','endpoint':'task_s',
                                  'estimand':'equal-task mean paired B-minus-A seconds','planned_attempts':config.planned_attempts,
                                  'question':'Diferencia de tiempo de tarea B−A bajo el diseño fijado; sin ranking general.'} if config.latency_study else None,
                               "resource_scope": "host_and_worker", "seed_determinism": "not guaranteed"}}
    snapshot['protocol'] = {'version':'arena-protocol-v1', 'evaluator_version':EVALUATOR_VERSION,
                            'identity_capture':'before each run; first observed identity pinned per model',
                            'order':'seeded initial A/B per case, reversed each repetition' if config.order_policy == 'balanced' else 'seeded random A/B within each case and repetition',
                            'reference_sent_to_model':False}
    if conditions is not None:
        snapshot['conditions'] = conditions
    if config.adapter == 'codex':
        from .openai_codex import RUNTIME_INSTRUCTIONS
        snapshot['conditions'].update(provider='ChatGPT subscription via local Codex App Server',
            provider_link=store.provider_link(), resource_scope='host_and_worker; excludes remote inference and Codex child',
            runtime_instructions=RUNTIME_INSTRUCTIONS, native_instructions='Codex also adds its own internal instructions',
            unsupported_settings=['temperature','seed','num_ctx','max_output_tokens','keep_alive'],
            account_limits='Shared with Codex; credits may apply according to account settings')
    if benchmark is not None:
        snapshot['benchmark'] = benchmark
    snapshot["data_sha256"] = hashlib.sha256(json.dumps({"tasks": snapshot["tasks"], "branch_tasks": branch_tasks, "environments": environments}, sort_keys=True).encode()).hexdigest()
    experiment_id = str(uuid.uuid4())
    rng, runs = random.Random(config.order_seed), []
    first_orders = {}
    if config.order_policy == 'balanced':
        for task in tasks:
            branches = ['A','B'];rng.shuffle(branches);first_orders[task.id] = branches
    for repetition in range(config.repetitions):
        for task in tasks:
            branches = ["A", "B"]
            if config.order_policy == 'balanced':
                branches = first_orders[task.id][:] if repetition % 2 == 0 else list(reversed(first_orders[task.id]))
            else:
                rng.shuffle(branches)
            for branch in branches:
                runs.append(Run(id=str(uuid.uuid4()), experiment_id=experiment_id, task_id=task.id,
                                branch=branch, repetition=repetition, position=len(runs), queued_at=time.time()))
    return store.create(experiment_id, snapshot, runs, campaign=campaign)
