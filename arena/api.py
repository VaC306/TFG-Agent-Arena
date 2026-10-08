import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from typing import Literal
from .contracts import Contract
from .store import Store
from .scheduler import submit
from .export import csv_text


class Submission(Contract):
    config: Literal["simulated", "ollama"] = "simulated"


def create_app(db_path=None, root=None):
    app = FastAPI(title="Agent Arena Local", version="0.1.0")
    store = Store(db_path or os.environ.get("ARENA_DB", "runtime/arena.sqlite"))
    root = Path(root or os.environ.get("ARENA_ROOT", "."))

    @app.post("/experiments", status_code=201)
    def create(body: Submission):
        return {"id": submit(store, root / "configs" / f"{body.config}.json", root / "data/tasks.jsonl")}

    @app.get("/experiments/{experiment_id}")
    def get(experiment_id: str):
        try:
            return {"snapshot": store.snapshot(experiment_id), "runs": store.list_runs(experiment_id)}
        except KeyError:
            raise HTTPException(404, "Experimento inexistente")

    @app.get("/experiments/{experiment_id}/metrics.csv")
    def export(experiment_id: str):
        try:
            return Response(csv_text(store, experiment_id), media_type="text/csv")
        except KeyError:
            raise HTTPException(404, "Experimento inexistente")

    @app.get("/runs/{run_id}/events")
    def events(run_id: str):
        return store.events(run_id)

    @app.post("/runs/{run_id}/cancel")
    def cancel(run_id: str):
        try:
            store.cancel(run_id)
            return {"requested": True}
        except KeyError:
            raise HTTPException(404, "Ejecución inexistente")

    return app


app = create_app()
