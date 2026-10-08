import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import ValidationError
from typing import Literal
from .contracts import Contract, Experiment
from .store import Store
from .scheduler import submit
from .export import csv_text
from .comparisons import ComparisonRequest, PROMPTS, submit_comparison
from .adapters import Ollama


class Submission(Contract):
    config: Literal["simulated", "ollama"] = "simulated"


def create_app(db_path=None, root=None):
    app = FastAPI(title="Agent Arena Local", version="0.1.0")
    store = Store(db_path or os.environ.get("ARENA_DB", "runtime/arena.sqlite"))
    root = Path(root or os.environ.get("ARENA_ROOT", "."))

    @app.get('/prompt-templates')
    def prompt_templates():
        return PROMPTS

    @app.get('/models')
    async def models():
        config = Experiment.model_validate_json((root / 'configs/ollama.json').read_text(encoding='utf-8'))
        adapter = Ollama(os.environ.get('ARENA_OLLAMA_URL', config.ollama_url))
        try:
            return {'available': True, 'models': await adapter.models(), 'error': None}
        except Exception:
            return {'available': False, 'models': [], 'error': 'Ollama no está disponible. Puedes introducir el nombre del modelo manualmente; necesitarás instalarlo para ejecutarlo.'}

    @app.post('/comparisons', status_code=201)
    async def create_comparison(request: Request):
        # Bound the body before JSON/base64 decoding, including chunked requests.
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > 12 * 1024 * 1024:
                raise HTTPException(413, 'La solicitud supera 12 MiB')
            body.extend(chunk)
        try:
            comparison = ComparisonRequest.model_validate_json(bytes(body))
            return {'id': submit_comparison(store, comparison)}
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_input=False, include_context=False))
        except ValueError as exc:
            raise HTTPException(422, str(exc)[:500])

    @app.get("/experiments")
    def list_experiments(limit: int = Query(default=50, ge=1, le=200)):
        return store.list_experiments(limit)

    @app.get("/presets")
    def presets():
        return [{"id": name, "config": Experiment.model_validate_json(
            (root / "configs" / f"{name}.json").read_text(encoding="utf-8")
        ).model_dump()} for name in ("simulated", "ollama")]

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
