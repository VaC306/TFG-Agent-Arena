import csv
import io
import json
from pathlib import Path
import pandas as pd
from scipy.stats import binomtest


FIELDS = ["id", "experiment_id", "task_id", "branch", "repetition", "position", "status", "adapter",
          "success", "format_ok", "evaluation", "queue_s", "agent_s", "input_tokens", "output_tokens", "usage_complete",
          "calls", "tool_calls", "tool_errors", "tool_s", "server_eval_s", "server_tps", "agent_output_tps", "error"]


def csv_text(store, experiment_id):
    adapter = store.snapshot(experiment_id)["config"]["adapter"]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, extrasaction="ignore")
    writer.writeheader()
    for run in store.list_runs(experiment_id):
        writer.writerow(run | {"adapter": adapter} | (run["result"] or {}))
    return output.getvalue()


def paired_summary(store, experiment_id):
    runs = store.list_runs(experiment_id)
    if any(r["status"] in {"queued", "running"} for r in runs):
        raise ValueError("Finaliza o cancela las ejecuciones antes de analizar")
    frame = pd.DataFrame([{**r, "success": (r["result"] or {}).get("success")} for r in runs])
    pairs = frame.pivot(index=["task_id", "repetition"], columns="branch", values="success")
    snapshot = store.snapshot(experiment_id)
    inputs_shared = snapshot.get('conditions', {}).get('inputs_shared', True)
    paired = pairs.dropna() if inputs_shared else pairs.iloc[0:0]
    wins_a = int(((paired.A == 1) & (paired.B == 0)).sum())
    wins_b = int(((paired.B == 1) & (paired.A == 0)).sum())
    # Repetitions are clustered by task; avoid treating them as independent observations.
    repeats = snapshot["config"]["repetitions"]
    p_value = binomtest(wins_a, wins_a + wins_b).pvalue if wins_a + wins_b and repeats == 1 else None
    rates = {branch: (float(group.success.dropna().mean()) if group.success.notna().any() else None)
             for branch, group in frame.groupby('branch')}
    return {"pairs": len(paired), "inputs_shared": inputs_shared, "success_rate": rates,
            "A_only_success": wins_a, "B_only_success": wins_b, "mcnemar_exact_p": p_value,
            "note": "Descriptive results. Quality is unavailable without reference; no paired inference for different inputs. Repetitions are not independent."}


def export_bundle(store, experiment_id, directory):
    summary = paired_summary(store, experiment_id)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "metrics.csv").write_text(csv_text(store, experiment_id), encoding="utf-8", newline='')
    runs = store.list_runs(experiment_id)
    (directory / "snapshot.json").write_text(json.dumps(store.snapshot(experiment_id), indent=2, ensure_ascii=False), encoding="utf-8")
    (directory / "runs.json").write_text(json.dumps(runs, indent=2, ensure_ascii=False), encoding="utf-8")
    with (directory / "events.jsonl").open("w", encoding="utf-8") as file:
        for run in runs:
            for event in store.events(run["id"]):
                file.write(json.dumps(event, ensure_ascii=False) + "\n")
    (directory / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
