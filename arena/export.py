import csv
import io
import json
from pathlib import Path
import pandas as pd
from scipy.stats import binomtest
from .protocol import quality_value
from .model_results import outcome, evaluable
from .resources import resources_csv


FIELDS = ["id", "experiment_id", "task_id", "branch", "repetition", "position", "status", "adapter",
          "success", "format_ok", "evaluation", "queue_s", "agent_s", "input_tokens", "output_tokens", "usage_complete",
          "calls", "tool_calls", "tool_errors", "tool_s", "server_eval_s", "server_tps", "agent_output_tps", "error",
          "evaluator_version", "quality_evaluated", "model_digest", "server_version", "answer", "outcome", "has_reference", "reference",
          "agent_config", "split", "repetitions", "order_seed", "data_sha256", "source_sha256", "conditions", "operator_annotations",
          "preparation_s", "task_s", "warmup_policy", "warmup_status", "warmup_s", "warmup_usage", "failure_phase", "resource_summary", "first_visible_token_s"]


def csv_text(store, experiment_id):
    snapshot = store.snapshot(experiment_id)
    adapter = snapshot["config"]["adapter"]
    annotations = store.annotations(experiment_id)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, extrasaction="ignore")
    writer.writeheader()
    for run in store.list_runs(experiment_id):
        result = run['result'] or {}
        identity = result.get('inference_identity') or {}
        warm = result.get('warmup') or {}
        tasks = [snapshot['branch_tasks'][run['branch']]] if snapshot.get('branch_tasks') else snapshot['tasks']
        task = next(t for t in tasks if t['id'] == run['task_id'])
        config = snapshot['config']
        row = run | {"adapter": adapter} | result | {'success':quality_value(run), 'quality_evaluated':quality_value(run) is not None,
              'model_digest':identity.get('digest'), 'server_version':identity.get('server_version'),
              'outcome':outcome(run), 'has_reference':evaluable(task),
              'reference':json.dumps(task['criteria'],ensure_ascii=False) if task.get('criteria') else task.get('expected_answer'),
              'agent_config':json.dumps(config['agents'][run['branch']],ensure_ascii=False),
              'split':config['split'], 'repetitions':config['repetitions'], 'order_seed':config.get('order_seed'),
              'data_sha256':snapshot.get('data_sha256'),
              'source_sha256':json.dumps(snapshot.get('source_sha256'),sort_keys=True),
              'conditions':json.dumps(snapshot.get('conditions'),sort_keys=True),
              'operator_annotations':json.dumps(annotations,ensure_ascii=False)}
        row.update(warmup_policy=warm.get('policy'),warmup_status=warm.get('status'),warmup_s=warm.get('duration_s'),
                   warmup_usage=json.dumps(warm.get('usage'),ensure_ascii=False),resource_summary=json.dumps(result.get('resources'),ensure_ascii=False))
        writer.writerow({k: "'" + v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v for k, v in row.items()})
    return output.getvalue()


def paired_summary(store, experiment_id):
    runs = store.list_runs(experiment_id)
    if any(r["status"] in {"queued", "running"} for r in runs):
        raise ValueError("Finaliza o cancela las ejecuciones antes de analizar")
    frame = pd.DataFrame([{**r, "success": quality_value(r)} for r in runs])
    pairs = frame.pivot(index=["task_id", "repetition"], columns="branch", values="success")
    snapshot = store.snapshot(experiment_id)
    inputs_shared = snapshot.get('conditions', {}).get('inputs_shared', True)
    paired = pairs.dropna() if inputs_shared else pairs.iloc[0:0]
    wins_a = int(((paired.A == 1) & (paired.B == 0)).sum())
    wins_b = int(((paired.B == 1) & (paired.A == 0)).sum())
    # Repetitions are clustered by task; avoid treating them as independent observations.
    repeats = snapshot["config"]["repetitions"]
    complete_pairs = inputs_shared and len(paired) == len(pairs)
    annotations = store.annotations(experiment_id)
    deviation = any(a['kind'] == 'deviation' for a in annotations)
    p_value = binomtest(wins_a, wins_a + wins_b).pvalue if wins_a + wins_b and repeats == 1 and complete_pairs and not deviation else None
    rates = {branch: (float(group.success.dropna().mean()) if group.success.notna().any() else None)
             for branch, group in frame.groupby('branch')}
    return {"pairs": len(paired), "inputs_shared": inputs_shared, "complete_pairs":complete_pairs, "success_rate": rates,
            "A_only_success": wins_a, "B_only_success": wins_b, "mcnemar_exact_p": p_value,
            'operator_annotations':annotations,'external_deviation':deviation,
            "note": "Descriptive results. Rates are conditional on evaluated responses; inspect execution errors and coverage. No paired inference for different inputs, missing scores or repeated cases."}


def export_bundle(store, experiment_id, directory):
    summary = paired_summary(store, experiment_id)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "metrics.csv").write_text(csv_text(store, experiment_id), encoding="utf-8", newline='')
    (directory / "resources.csv").write_text(resources_csv(store,experiment_id),encoding='utf-8',newline='')
    runs = store.list_runs(experiment_id)
    (directory / "snapshot.json").write_text(json.dumps(store.snapshot(experiment_id), indent=2, ensure_ascii=False), encoding="utf-8")
    (directory / "runs.json").write_text(json.dumps(runs, indent=2, ensure_ascii=False), encoding="utf-8")
    (directory / "operator-annotations.json").write_text(json.dumps(store.annotations(experiment_id),indent=2,ensure_ascii=False),encoding='utf-8')
    with (directory / "events.jsonl").open("w", encoding="utf-8") as file:
        for run in runs:
            for event in store.events(run["id"]):
                file.write(json.dumps(event, ensure_ascii=False) + "\n")
    (directory / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
