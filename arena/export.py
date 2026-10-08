import csv
import io
import json
from pathlib import Path
import pandas as pd
from scipy.stats import binomtest


FIELDS = ["id", "experiment_id", "task_id", "branch", "repetition", "position", "status", "adapter",
          "success", "format_ok", "queue_s", "agent_s", "input_tokens", "output_tokens", "usage_complete",
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
    frame = pd.DataFrame([{**r, "success": int((r["result"] or {}).get("success", False))} for r in runs])
    pairs = frame.pivot(index=["task_id", "repetition"], columns="branch", values="success")
    wins_a = int(((pairs.A == 1) & (pairs.B == 0)).sum())
    wins_b = int(((pairs.B == 1) & (pairs.A == 0)).sum())
    # Repetitions are clustered by task; avoid treating them as independent observations.
    repeats = store.snapshot(experiment_id)["config"]["repetitions"]
    p_value = binomtest(wins_a, wins_a + wins_b).pvalue if wins_a + wins_b and repeats == 1 else None
    return {"pairs": len(pairs), "success_rate": frame.groupby("branch").success.mean().to_dict(),
            "A_only_success": wins_a, "B_only_success": wins_b, "mcnemar_exact_p": p_value,
            "note": "Descriptive results; p omitted with repetitions or no discordant pairs. Synthetic tasks are not a population sample."}


def export_bundle(store, experiment_id, directory):
    summary = paired_summary(store, experiment_id)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "metrics.csv").write_text(csv_text(store, experiment_id), encoding="utf-8")
    runs = store.list_runs(experiment_id)
    (directory / "snapshot.json").write_text(json.dumps(store.snapshot(experiment_id), indent=2, ensure_ascii=False), encoding="utf-8")
    (directory / "runs.json").write_text(json.dumps(runs, indent=2, ensure_ascii=False), encoding="utf-8")
    with (directory / "events.jsonl").open("w", encoding="utf-8") as file:
        for run in runs:
            for event in store.events(run["id"]):
                file.write(json.dumps(event, ensure_ascii=False) + "\n")
    (directory / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
