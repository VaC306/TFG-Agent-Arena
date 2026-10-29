"""Account-scoped research tools. Stored evidence is never rewritten."""
import hashlib
import json
import secrets
import time
import uuid
import asyncio
from typing import Literal

from fastapi import Depends, HTTPException, Query, Request
from pydantic import Field, model_validator

from .contracts import Contract
from .comparisons import ComparisonRequest, submit_comparison
from .datasets import DatasetCase, validate_cases
from .adapters import Ollama
from .model_results import outcome, summarize
from .protocol import quality_value, protocol_report
import httpx


class LibraryItem(Contract):
    kind: Literal['dataset', 'prompt']
    name: str = Field(min_length=1, max_length=120)
    text: str | None = Field(default=None, min_length=1, max_length=6000)
    cases: list[DatasetCase] | None = Field(default=None, min_length=1, max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=12)

    @model_validator(mode='after')
    def valid_content(self):
        self.name = self.name.strip()
        if not self.name or any(not t.strip() or len(t)>40 for t in self.tags):
            raise ValueError('Nombre o etiquetas inválidos')
        if self.kind == 'dataset':
            if self.cases is None or self.text is not None:
                raise ValueError('El dataset requiere casos y no texto de prompt')
            validate_cases(self.cases)
        elif not self.text or not self.text.strip() or self.cases is not None:
            raise ValueError('El prompt requiere texto y no casos')
        return self


class Recovery(Contract):
    workers_stopped: Literal[True]


class ReviewStart(Contract):
    task_id: str = Field(min_length=1, max_length=180)
    repetition: int = Field(ge=0, le=99, strict=True)


class RubricScore(Contract):
    correctness: int = Field(ge=1,le=5,strict=True)
    clarity: int = Field(ge=1,le=5,strict=True)
    usefulness: int = Field(ge=1,le=5,strict=True)


class ReviewScore(Contract):
    left: RubricScore
    right: RubricScore
    preference: Literal['left','right','tie']
    comment: str = Field(default='',max_length=2000)


class BatchRequest(Contract):
    comparisons: list[ComparisonRequest] = Field(min_length=1,max_length=10)

    @model_validator(mode='after')
    def keys(self):
        keys = [c.request_id for c in self.comparisons]
        if any(not k for k in keys) or len(set(keys)) != len(keys):
            raise ValueError('Cada configuración necesita una clave de envío distinta')
        if sum((len(c.dataset) if c.dataset else 1)*c.repetitions*2 for c in self.comparisons)>2000:
            raise ValueError('El lote supera 2.000 ejecuciones')
        return self


def progress(store, experiment_id):
    snapshot = store.snapshot(experiment_id)
    runs = store.list_runs(experiment_id)
    # Never transmit source code or attachment bytes during polling.
    with store.connect() as db:
        for run in runs:
            if run['status'] == 'running':
                row = db.execute("SELECT payload FROM events WHERE run_id=? AND kind='answer_chunk' ORDER BY seq DESC LIMIT 1",(run['id'],)).fetchone()
                if row:
                    run['result'] = (run['result'] or {}) | {'answer':json.loads(row[0])['text'],'partial':True}
    return {'runs':runs, 'protocol':protocol_report(snapshot | {'operator_annotations':store.annotations(experiment_id)},runs),
            'campaign':store.experiment_campaign(experiment_id), 'overviews':{b:summarize([r for r in runs if r['branch']==b],
        [snapshot['branch_tasks'][b]] if snapshot.get('branch_tasks') else snapshot['tasks']) for b in ('A','B')}}


def recover_owned(store):
    now = store.clock()
    count = 0
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute("SELECT 1 FROM worker_signals WHERE state!='stopped' AND updated_at>?",(now-60,)).fetchone():
            raise ValueError('Detén todos los workers y espera 60 segundos desde su última señal antes de recuperar.')
        rows = db.execute("""SELECT r.* FROM runs r JOIN experiment_owners o ON o.experiment_id=r.experiment_id
            WHERE o.owner_id=? AND r.status='running'""",(store.owner_id,)).fetchall()
        if any(now-json.loads(r['data']).get('started_at',now)<60 for r in rows):
            raise ValueError('Hay ejecuciones iniciadas hace menos de 60 segundos. Espera antes de recuperar.')
        for row in rows:
            run = json.loads(row['data'])
            result = store.failure_result(db,run,'Recuperación manual tras detener todos los workers; consulta las trazas parciales')
            run.update(status='interrupted',finished_at=now,result=result)
            db.execute("UPDATE runs SET status='interrupted',data=?,cancel_requested=1 WHERE id=?",(json.dumps(run),run['id']))
            db.execute('INSERT INTO events(run_id,kind,at,payload) VALUES (?,?,?,?)',
                       (run['id'],'finished',now,json.dumps({'status':'interrupted',**result})))
            count += 1
    return {'recovered':count}


async def preflight(request, store):
    def prepare():
        return [c.task() for c in request.dataset] if request.dataset else [b.task() for b in
               ([request.shared_input] if request.shared_input else request.branch_inputs.values())]
    tasks = await asyncio.to_thread(prepare)
    errors, warnings, models = [], [], []
    if request.adapter == 'codex':
        from .openai_codex import inspect_session
        session = await inspect_session(store.provider_link()) if store.provider_link() else None
        names = {m['name'] for m in session['models']} if session else set()
        if any(a.model not in names for a in request.agents.values()):
            errors.append('Vincula ChatGPT y selecciona modelos del catálogo actual.')
        warnings.append('El contexto y los límites de generación los gestiona Codex.')
    elif request.adapter == 'ollama':
        import os
        adapter = Ollama(os.environ.get('ARENA_OLLAMA_URL',request.config().ollama_url))
        for branch, agent in request.config().agents.items():
            metadata = await adapter.metadata(agent.model)
            capabilities = metadata.get('show',{}).get('capabilities',[])
            if any(a.media_type.startswith('image/') for t in tasks for a in t.attachments) and 'vision' not in capabilities:
                errors.append(f'{branch}: el modelo no declara visión.')
            info = metadata.get('show',{}).get('model_info',{})
            contexts = [v for k,v in info.items() if k.endswith('.context_length') and isinstance(v,int)]
            if contexts and agent.num_ctx>max(contexts):
                errors.append(f'{branch}: contexto solicitado superior al declarado por el modelo.')
            from .attachments import user_message
            chars = max(len(agent.system_prompt)+len(user_message(t)['content']) for t in tasks)
            # Deliberately conservative warning, not a claim about the tokenizer.
            if chars+agent.limits.max_output_tokens>agent.num_ctx:
                warnings.append(f'{branch}: revisa el presupuesto de contexto; {chars} caracteres de entrada más la salida reservada. Estimación conservadora sin tokenizador.')
            models.append({'branch':branch,'model':agent.model,'capabilities':capabilities})
    else:
        warnings.append('El simulador solo valida el recorrido de la plataforma.')
    return {'ready':not errors,'errors':errors,'warnings':warnings,'models':models,
            'planned_runs':len(tasks)*request.repetitions*2}


def baseline_report(store, current_id, baseline_id):
    current, base = store.snapshot(current_id),store.snapshot(baseline_id)
    reasons = []
    for key in ('data_sha256','source_sha256','protocol','conditions'):
        if not current.get(key) or current.get(key)!=base.get(key):
            reasons.append('Diferencias o ausencia de '+key)
    def host(s):
        return {k:v for k,v in s.get('host',{}).items() if k!='resources'}
    if not host(current) or host(current)!=host(base):
        reasons.append('Diferencias o ausencia de equipo y dependencias')
    if current.get('branch_tasks') or base.get('branch_tasks'):
        reasons.append('Las entradas deben ser compartidas entre ramas')
    for key in ('adapter','split','repetitions','warmup','order_policy','order_seed','latency_study'):
        if current['config'].get(key)!=base['config'].get(key):
            reasons.append('Diferencia en '+key)
    for branch in ('A','B'):
        for key in ('temperature','seed','num_ctx','limits','tools_enabled'):
            if current['config']['agents'][branch].get(key)!=base['config']['agents'][branch].get(key):
                reasons.append(f'{branch}: diferencia en {key}')
    if any(a['kind']=='deviation' for eid in (current_id,baseline_id) for a in store.annotations(eid)):
        reasons.append('Hay condiciones externas declaradas diferentes')
    cr, br = store.list_runs(current_id),store.list_runs(baseline_id)
    if current['config']['adapter']=='ollama':
        for branch in ('A','B'):
            identities = [[(r.get('result') or {}).get('inference_identity') for r in runs if r['branch']==branch] for runs in (cr,br)]
            if any(not values or any(not i or not i.get('verified') for i in values) for values in identities):
                reasons.append(f'{branch}: identidad de modelo o servidor sin verificar')
            else:
                versions = [{i.get('server_version') for i in values} for values in identities]
                if versions[0]!=versions[1] or len(versions[0])!=1:
                    reasons.append(f'{branch}: versiones distintas del servidor de inferencia')
    if any(r['status'] in ('queued','running') for r in cr+br):
        reasons.append('Finaliza ambas comparaciones')
    old = {(r['task_id'],r['repetition'],r['branch']):r for r in br}
    if set(old)!={(r['task_id'],r['repetition'],r['branch']) for r in cr}:
        reasons.append('Los casos y las repeticiones no coinciden')
    cases = []
    if not reasons:
        for run in cr:
            previous = old[(run['task_id'],run['repetition'],run['branch'])]
            before, after = quality_value(previous),quality_value(run)
            cases.append({'task_id':run['task_id'],'branch':run['branch'],'repetition':run['repetition'],
                'before':outcome(previous),'after':outcome(run),
                'change':'improved' if before is False and after is True else 'regressed' if before is True and after is False
                         else 'unchanged' if before is not None and after is not None else 'unscored',
                'before_answer':(previous['result'] or {}).get('answer'),'after_answer':(run['result'] or {}).get('answer')})
    return {'compatible':not reasons,'reasons':reasons,'cases':cases,
            'note':'Comparación descriptiva por caso; no demuestra significación estadística. Los proveedores remotos no ofrecen un digest verificable.'}


def register_workspace(app, user_store, auth_body):
    def ensure_experiment(store,eid):
        try:
            store.check_experiment(eid)
        except KeyError:
            raise HTTPException(404,'Experimento inexistente')
    @app.post('/attachments/preview')
    async def attachment_preview(request:Request):
        from .attachments import AttachmentUpload,prepare_attachment
        import asyncio
        data = await auth_body(request,AttachmentUpload,2*1024*1024)
        try:
            attachment = await asyncio.to_thread(prepare_attachment,data)
            return {'text':attachment.text,'sha256':attachment.sha256}
        except ValueError as exc:
            raise HTTPException(422,str(exc))
    @app.get('/experiments/{eid}/progress')
    def experiment_progress(eid:str, store=Depends(user_store)):
        ensure_experiment(store,eid)
        return progress(store,eid)

    @app.post('/worker/recover')
    async def recover(request:Request,store=Depends(user_store)):
        await auth_body(request,Recovery,1024)
        try:
            return recover_owned(store)
        except ValueError as exc:
            raise HTTPException(409,str(exc))

    @app.post('/comparisons/preflight')
    async def check(request:Request,store=Depends(user_store)):
        data = await auth_body(request,ComparisonRequest,12*1024*1024)
        try:
            return await preflight(data,store)
        except (ValueError,OSError,TimeoutError) as exc:
            raise HTTPException(422,str(exc)[:500])
        except httpx.HTTPError:
            raise HTTPException(422,'No se pudo consultar Ollama. Comprueba el servicio y los modelos instalados.')

    @app.post('/comparisons/batch',status_code=201)
    async def batch(request:Request,store=Depends(user_store)):
        data = await auth_body(request,BatchRequest,24*1024*1024)
        try:
            for item in data.comparisons:
                identity = item.submission()
                if store.submission(identity['key'],identity['fingerprint']):
                    continue
                report = await preflight(item,store)
                if not report['ready']:
                    raise ValueError('; '.join(report['errors']))
            def save_batch():
                with store.atomic():
                    return [submit_comparison(store,item) for item in data.comparisons]
            ids = await asyncio.to_thread(save_batch)
            return {'ids':ids}
        except (ValueError,OSError,TimeoutError) as exc:
            raise HTTPException(422,str(exc)[:500])
        except httpx.HTTPError:
            raise HTTPException(422,'No se pudo consultar Ollama para el lote.')

    @app.get('/library')
    def library(store=Depends(user_store)):
        with store.connect() as db:
            return [dict(r)|{'content':json.loads(r['content'])} for r in db.execute(
                'SELECT id,kind,name,version,created_at,sha256,content FROM library_items WHERE owner_id=? ORDER BY created_at DESC,rowid DESC',(store.owner_id,))]

    @app.post('/library',status_code=201)
    async def save_library(request:Request,store=Depends(user_store)):
        data = await auth_body(request,LibraryItem,2*1024*1024)
        content = data.model_dump_json(exclude={'kind','name'})
        digest = hashlib.sha256(content.encode()).hexdigest()
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            same = db.execute('SELECT id,version FROM library_items WHERE owner_id=? AND kind=? AND name=? AND sha256=?',
                              (store.owner_id,data.kind,data.name,digest)).fetchone()
            if same:
                return dict(same)
            version = db.execute('SELECT COALESCE(MAX(version),0)+1 FROM library_items WHERE owner_id=? AND kind=? AND name=?',
                                 (store.owner_id,data.kind,data.name)).fetchone()[0]
            ident = str(uuid.uuid4())
            db.execute('INSERT INTO library_items VALUES (?,?,?,?,?,?,?,?)',
                       (ident,store.owner_id,data.kind,data.name,version,time.time(),content,digest))
        return {'id':ident,'version':version}

    @app.get('/experiments/{eid}/baseline/{baseline_id}')
    def baseline(eid:str,baseline_id:str,store=Depends(user_store)):
        ensure_experiment(store,eid)
        ensure_experiment(store,baseline_id)
        return baseline_report(store,eid,baseline_id)

    @app.get('/experiments/{eid}/reviews')
    def reviews(eid:str,store=Depends(user_store)):
        ensure_experiment(store,eid)
        with store.connect() as db:
            # Only completed reviews reveal identity.
            rows = db.execute('SELECT id,data,created_at FROM human_reviews WHERE owner_id=? AND experiment_id=? ORDER BY created_at', (store.owner_id,eid)).fetchall()
        return [dict(id=r['id'],created_at=r['created_at'],**json.loads(r['data'])) for r in rows if json.loads(r['data']).get('score')]

    @app.post('/experiments/{eid}/reviews',status_code=201)
    async def start_review(eid:str,request:Request,store=Depends(user_store)):
        data = await auth_body(request,ReviewStart,2048)
        ensure_experiment(store,eid)
        snapshot = store.snapshot(eid)
        if snapshot.get('branch_tasks') or snapshot.get('conditions',{}).get('inputs_shared') is False:
            raise HTTPException(422,'La revisión ciega requiere entradas compartidas.')
        runs = [r for r in store.list_runs(eid) if r['task_id']==data.task_id and r['repetition']==data.repetition]
        if len(runs)!=2 or any(r['status'] not in ('completed','succeeded','failed') or not (r['result'] or {}).get('answer') or (r['result'] or {}).get('error') for r in runs):
            raise HTTPException(422,'Se necesitan dos respuestas completas sin errores de ejecución.')
        secrets.SystemRandom().shuffle(runs)
        payload = {'task_id':data.task_id,'repetition':data.repetition,'rubric':'arena-human-v1',
                   'mapping':{side:r['branch'] for side,r in zip(('left','right'),runs)},'score':None}
        ident = str(uuid.uuid4())
        with store.connect() as db:
            db.execute('INSERT INTO human_reviews VALUES (?,?,?,?,?)', (ident,store.owner_id,eid,json.dumps(payload),time.time()))
        return {'id':ident,'task_id':data.task_id,'input':next(t['input'] for t in snapshot['tasks'] if t['id']==data.task_id),
                'left':runs[0]['result']['answer'],'right':runs[1]['result']['answer'],'rubric':'arena-human-v1'}

    @app.post('/reviews/{review_id}')
    async def score_review(review_id:str,request:Request,store=Depends(user_store)):
        score = await auth_body(request,ReviewScore,8192)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM human_reviews WHERE id=? AND owner_id=?',(review_id,store.owner_id)).fetchone()
            if not row:
                raise HTTPException(404,'Revisión inexistente')
            data = json.loads(row['data'])
            if data.get('score') and data['score']!=score.model_dump():
                raise HTTPException(409,'La valoración ya está cerrada; inicia otra para conservar el historial.')
            data['score'] = score.model_dump()
            db.execute('UPDATE human_reviews SET data=? WHERE id=?',(json.dumps(data),review_id))
        return data
