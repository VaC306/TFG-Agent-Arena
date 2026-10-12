import os
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import ValidationError
from pydantic import Field
from fastapi.exceptions import RequestValidationError
from typing import Literal
from .contracts import Contract, Experiment
from .store import Store
from .scheduler import submit
from .export import csv_text
from .comparisons import ComparisonRequest, PROMPTS, submit_comparison
from .adapters import Ollama
from .datasets import DatasetUpload, parse_dataset
from .accounts import Accounts, COOKIE, SESSION_SECONDS, Credentials, Registration, Preferences, ProfileUpdate
from .json_input import load_json
from .protocol import protocol_report
from .model_results import latest_model_results, summarize
from .result_report import markdown_report
from .campaigns import CampaignRequest, AttemptRequest, create_campaign, repeat_campaign, campaign_report, campaign_csv, campaign_markdown, task_analysis_csv
import json


class Submission(Contract):
    config: Literal["simulated", "ollama"] = "simulated"


class ClearHistory(Contract):
    confirmation: Literal['clear-history']
    revision: str = Field(pattern=r'^[a-f0-9]{64}$')


def create_app(db_path=None, root=None):
    app = FastAPI(title="Agent Arena Local", version="0.1.0")
    store = Store(db_path or os.environ.get("ARENA_DB", "runtime/arena.sqlite"))
    accounts = Accounts(store)
    root = Path(root or os.environ.get("ARENA_ROOT", "."))
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        return JSONResponse({'detail': [{key: item[key] for key in ('loc', 'msg', 'type')}
                                       for item in exc.errors()]}, status_code=422)

    @app.middleware('http')
    async def session_access(request: Request, call_next):
        if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
            if request.headers.get('x-arena-request') != '1' or request.headers.get('sec-fetch-site') == 'cross-site':
                return JSONResponse({'detail': 'Solicitud no permitida'}, status_code=403)
        user = accounts.current(request.cookies.get(COOKIE))
        request.state.user = user
        public = {'/auth/session', '/auth/login', '/auth/register'}
        if request.url.path not in public and not user:
            return JSONResponse({'detail': 'Inicia sesión para continuar'}, status_code=401)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    def user_store(request: Request):
        return Store(store.path, owner_id=request.state.user['id'])

    async def bounded_body(request, limit):
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > limit:
                raise HTTPException(413, 'La solicitud supera el tamaño permitido')
            body.extend(chunk)
        return bytes(body)

    async def auth_body(request, model, limit=64 * 1024):
        try:
            return model.model_validate(load_json(await bounded_body(request, limit)))
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_input=False, include_context=False))
        except ValueError as exc:
            raise HTTPException(422, str(exc)[:500])

    @app.get('/auth/session')
    def auth_session(request: Request):
        return {'user': request.state.user, 'has_users': accounts.has_users()}

    async def authenticate(request, response, register=False):
        accounts.limited(request.client.host if request.client else 'local')
        data = await auth_body(request, Registration if register else Credentials, 16 * 1024)
        user_id = accounts.register(data) if register else accounts.login(data)
        accounts.logout(request.cookies.get(COOKIE))
        token = accounts.new_session(user_id)
        response.set_cookie(COOKIE, token, httponly=True, samesite='strict', max_age=SESSION_SECONDS,
                            secure=request.url.scheme == 'https', path='/')
        return {'user': accounts.current(token)}

    @app.post('/auth/register', status_code=201)
    async def register(request: Request, response: Response):
        return await authenticate(request, response, register=True)

    @app.post('/auth/login')
    async def login(request: Request, response: Response):
        return await authenticate(request, response)

    @app.post('/auth/logout')
    def logout(request: Request, response: Response):
        accounts.logout(request.cookies.get(COOKIE))
        response.delete_cookie(COOKIE, path='/')
        return {'ok': True}

    @app.put('/profile/preferences')
    async def preferences(request: Request):
        data = await auth_body(request, Preferences)
        accounts.update(request.state.user['id'], 'preferences', data.model_dump_json())
        return data.model_dump()

    @app.patch('/profile')
    async def profile(request: Request):
        data = await auth_body(request, ProfileUpdate)
        accounts.update(request.state.user['id'], 'display_name', data.display_name)
        return {'display_name': data.display_name}

    @app.get('/profile/history')
    def history_state(store: Store = Depends(user_store)):
        return store.history_state()

    @app.delete('/profile/history')
    async def clear_history(request: Request, store: Store = Depends(user_store)):
        data = await auth_body(request, ClearHistory, 1024)
        try:
            return {'deleted': store.clear_history(data.revision)}
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    @app.post('/datasets/validate')
    async def validate_dataset(request: Request):
        body = await bounded_body(request, 8 * 1024 * 1024)
        try:
            upload = DatasetUpload.model_validate(load_json(body))
            cases = parse_dataset(upload.filename, upload.content)
            return {'cases': [case.model_dump() for case in cases],
                    'count': len(cases), 'scored': sum(case.expected_answer is not None for case in cases)}
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_input=False, include_context=False))
        except ValueError as exc:
            raise HTTPException(422, str(exc)[:500])

    @app.get('/datasets/template.csv')
    def dataset_template():
        return Response('id,input,expected_answer\ncapital,¿Cuál es la capital de Francia? Responde solo el nombre.,París\nresumen,Resume en una frase las ventajas de probar modelos localmente.,\n',
                        media_type='text/csv; charset=utf-8',
                        headers={'Content-Disposition': 'attachment; filename="dataset-ejemplo.csv"'})

    @app.get('/datasets/examples/{kind}')
    def dataset_example(kind: Literal['exact_match', 'json_match']):
        name = 'respuestas-concretas.csv' if kind == 'exact_match' else 'extraccion.jsonl'
        return Response((root / 'data/examples' / name).read_text(encoding='utf-8'),
                        media_type='text/csv; charset=utf-8' if kind == 'exact_match' else 'application/x-ndjson',
                        headers={'Content-Disposition':f'attachment; filename="{name}"'})

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
            return {'available': False, 'models': [], 'error': 'Ollama no está disponible. Inícialo y actualiza la lista de modelos instalados.'}

    @app.post('/comparisons', status_code=201)
    async def create_comparison(request: Request, store: Store = Depends(user_store)):
        comparison = await auth_body(request, ComparisonRequest, 12 * 1024 * 1024)
        try:
            return {'id': submit_comparison(store, comparison)}
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_input=False, include_context=False))
        except ValueError as exc:
            raise HTTPException(422, str(exc)[:500])

    @app.get("/experiments")
    def list_experiments(limit: int = Query(default=50, ge=1, le=200), store: Store = Depends(user_store)):
        return store.list_experiments(limit)

    @app.get("/presets")
    def presets():
        return [{"id": name, "config": Experiment.model_validate_json(
            (root / "configs" / f"{name}.json").read_text(encoding="utf-8")
        ).model_dump()} for name in ("simulated", "ollama")]

    @app.get('/model-results')
    def model_results(store: Store = Depends(user_store)):
        return {'entries':latest_model_results(store)}

    @app.get('/campaigns')
    def campaigns(store: Store = Depends(user_store)):
        return store.list_campaigns()

    @app.post('/campaigns',status_code=201)
    async def new_campaign(request: Request, store: Store = Depends(user_store)):
        body = await auth_body(request,CampaignRequest,4096)
        try:
            return {'id':create_campaign(store,body)}
        except KeyError:
            raise HTTPException(404,'Comparación inexistente')
        except ValueError as exc:
            raise HTTPException(409,str(exc))

    @app.get('/campaigns/{campaign_id}')
    def get_campaign(campaign_id: str, store: Store = Depends(user_store)):
        try:
            return campaign_report(store,campaign_id)
        except KeyError:
            raise HTTPException(404,'Campaña inexistente')

    @app.post('/campaigns/{campaign_id}/attempts',status_code=201)
    async def new_attempt(campaign_id: str,request: Request,store: Store = Depends(user_store)):
        body = await auth_body(request,AttemptRequest,1024)
        try:
            return {'id':repeat_campaign(store,campaign_id,body.request_id)}
        except KeyError:
            raise HTTPException(404,'Campaña inexistente')
        except ValueError as exc:
            raise HTTPException(409,str(exc))

    @app.get('/campaigns/{campaign_id}/export.{kind}')
    def export_campaign(campaign_id: str,kind: Literal['json','csv','md'],store: Store = Depends(user_store)):
        try:
            report = campaign_report(store,campaign_id,include_evidence=kind == 'json')
            content = json.dumps(report,ensure_ascii=False,indent=2) if kind == 'json' else campaign_csv(report) if kind == 'csv' else campaign_markdown(report)
            return Response(content,media_type={'json':'application/json','csv':'text/csv; charset=utf-8','md':'text/markdown; charset=utf-8'}[kind],
                            headers={'Content-Disposition':f'attachment; filename="arena-campaign.{kind}"'})
        except KeyError:
            raise HTTPException(404,'Campaña inexistente')

    @app.get('/campaigns/{campaign_id}/analysis.csv')
    def export_task_analysis(campaign_id: str,store: Store = Depends(user_store)):
        try:
            return Response(task_analysis_csv(campaign_report(store,campaign_id)),media_type='text/csv; charset=utf-8',
                            headers={'Content-Disposition':'attachment; filename="arena-task-analysis.csv"'})
        except KeyError:
            raise HTTPException(404,'Campaña inexistente')

    @app.post("/experiments", status_code=201)
    async def create(request: Request, store: Store = Depends(user_store)):
        body = await auth_body(request, Submission, 1024)
        return {"id": submit(store, root / "configs" / f"{body.config}.json", root / "data/tasks.jsonl")}

    @app.get("/experiments/{experiment_id}")
    def get(experiment_id: str, store: Store = Depends(user_store)):
        try:
            snapshot, runs = store.snapshot(experiment_id), store.list_runs(experiment_id)
            overviews = {b:summarize([r for r in runs if r['branch'] == b],
                [snapshot['branch_tasks'][b]] if snapshot.get('branch_tasks') else snapshot['tasks']) for b in ('A','B')}
            return {"snapshot": snapshot, "runs": runs, "protocol":protocol_report(snapshot, runs),'overviews':overviews,
                    'campaign':store.experiment_campaign(experiment_id)}
        except KeyError:
            raise HTTPException(404, "Experimento inexistente")

    @app.get('/experiments/{experiment_id}/reproducibility.json')
    def reproducibility(experiment_id: str, store: Store = Depends(user_store)):
        try:
            snapshot, runs = store.snapshot(experiment_id), store.list_runs(experiment_id)
            data = {'experiment_id':experiment_id, 'snapshot':snapshot, 'runs':runs,
                    'campaign':store.experiment_campaign(experiment_id),
                    'report':protocol_report(snapshot, runs),
                    'overviews':{b:summarize([r for r in runs if r['branch'] == b],
                        [snapshot['branch_tasks'][b]] if snapshot.get('branch_tasks') else snapshot['tasks']) for b in ('A','B')},
                    'note':'Partial while runs are pending. Contains inputs and attachments. Full traces remain in the application.'}
            return Response(json.dumps(data, ensure_ascii=False, indent=2), media_type='application/json',
                            headers={'Content-Disposition':'attachment; filename="arena-reproducibility.json"'})
        except KeyError:
            raise HTTPException(404, 'Experimento inexistente')

    @app.get('/experiments/{experiment_id}/report.md')
    def readable_report(experiment_id: str, store: Store = Depends(user_store)):
        try:
            return Response(markdown_report(store.snapshot(experiment_id),store.list_runs(experiment_id)),
                media_type='text/markdown; charset=utf-8',headers={'Content-Disposition':'attachment; filename="arena-results.md"'})
        except KeyError:
            raise HTTPException(404,'Experimento inexistente')

    @app.get("/experiments/{experiment_id}/metrics.csv")
    def export(experiment_id: str, store: Store = Depends(user_store)):
        try:
            return Response(csv_text(store, experiment_id), media_type="text/csv",
                            headers={'Content-Disposition':'attachment; filename="metrics.csv"'})
        except KeyError:
            raise HTTPException(404, "Experimento inexistente")

    @app.get("/runs/{run_id}/events")
    def events(run_id: str, store: Store = Depends(user_store)):
        try:
            return store.events(run_id)
        except KeyError:
            raise HTTPException(404, 'Ejecución inexistente')

    @app.post("/runs/{run_id}/cancel")
    def cancel(run_id: str, store: Store = Depends(user_store)):
        try:
            store.cancel(run_id)
            return {"requested": True}
        except KeyError:
            raise HTTPException(404, "Ejecución inexistente")

    return app


app = create_app()
