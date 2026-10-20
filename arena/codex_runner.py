"""Text-only execution; unavailable remote measurements remain null."""
import asyncio
import time
from .openai_codex import CodexClient, CodexError
from .evaluator import evaluate, EVALUATOR_VERSION
from .protocol import inference_identity
from .resources import ResourceMonitor, sample
from .async_cleanup import drain


async def execute_codex(run, task, config, store, measurement):
    started = time.perf_counter()
    metrics = dict(success=None, format_ok=None, quality_evaluated=False, evaluator_version=EVALUATOR_VERSION,
        queue_s=max(0,run['started_at']-run['queued_at']), input_tokens=None, output_tokens=None,
        server_eval_s=None, server_tps=None, agent_output_tps=None, calls=0, tool_calls=0, tool_errors=0,
        tool_s=0, usage_complete=False, task_s=None, warmup={'policy':'none','status':'not_requested'})
    monitor = ResourceMonitor(store,run['id'],measurement.get('resource_sample_interval_s'),sample)
    phase, task_started = 'preparation', None
    expected = measurement.get('provider_link')

    async def infer():
        nonlocal phase, task_started
        if not expected or store.provider_link(run['experiment_id']) != expected:
            raise CodexError('La vinculación ChatGPT fue retirada o cambió. No se envió la entrada.')
        async with CodexClient() as client:
            account = await client.account()
            if account['fingerprint'] != expected:
                raise CodexError('La sesión ChatGPT del equipo cambió. Vuelve a vincularla en Arena. No se envió la entrada.')
            if task.attachments or task.criteria or config.tools_enabled:
                raise CodexError('Esta conexión solo admite texto sin herramientas ni adjuntos.')
            if config.model not in {m['name'] for m in await client.models()}:
                raise CodexError('El modelo ya no figura en el catálogo de Codex.')
            metadata = {'adapter':'codex','model':{'name':config.model},'version':{'version':client.version}}
            identity = inference_identity(config.model,metadata)
            store.record_inference_metadata(run,metadata,identity)
            metrics.update(inference_identity=identity,preparation_s=time.perf_counter()-started,calls=1)
            store.event(run['id'],'input',{'messages':[{'role':'system','content':config.system_prompt},
                {'role':'user','content':task.input}], 'environment':{}})
            store.event(run['id'],'inference_request',{'provider':'codex','model':config.model,
                'system_prompt':config.system_prompt,'text':task.input,'runtime_instructions':measurement.get('runtime_instructions')})
            phase, monitor.phase, task_started = 'task', 'task', time.perf_counter()
            answer, usage = await client.answer(config.model,config.system_prompt,task.input)
            if isinstance(usage,dict) and all(type(usage.get(k)) is int and usage[k] >= 0 for k in ('inputTokens','outputTokens')):
                metrics.update(input_tokens=usage['inputTokens'],output_tokens=usage['outputTokens'],usage_complete=True)
            # Only final text and token counts are persisted, never reasoning or raw account events.
            store.event(run['id'],'inference_response',{'message':{'role':'assistant','content':answer},
                'usage':{'input_tokens':metrics['input_tokens'],'output_tokens':metrics['output_tokens']}})
            metrics.update(answer=answer, **evaluate(answer,task,[]))
            metrics['quality_evaluated'] = metrics['success'] is not None
            status = 'completed' if metrics['success'] is None else 'succeeded' if metrics['success'] else 'failed'
        if client.cleanup_warning:
            metrics['cleanup_warning'] = client.cleanup_warning
            store.event(run['id'],'cleanup_warning',{'message':client.cleanup_warning})
        return status

    pending = None
    try:
        await monitor.start()
        async with asyncio.timeout(config.limits.timeout_s):
            pending = asyncio.create_task(infer())
            while not pending.done():
                if store.cancelled(run['id']):
                    status = 'cancelled'
                    break
                if store.provider_link(run['experiment_id']) != expected:
                    raise CodexError('Se retiró o cambió la vinculación ChatGPT durante la ejecución.')
                await asyncio.wait({pending},timeout=.1)
            else:
                status = await pending
    except TimeoutError:
        status, metrics['error'] = 'timeout','Tiempo límite agotado; se solicitó detener el turno de Codex.'
    except asyncio.CancelledError:
        status, metrics['error'] = 'interrupted','Worker interrupted'
    except Exception as exc:
        metrics['client_error_type'] = type(exc).__name__
        status, metrics['error'] = 'failed',str(exc) if isinstance(exc,CodexError) else 'No se pudo ejecutar el cliente oficial Codex. Comprueba su instalación y sesión.'
    finally:
        async def cleanup():
            if pending and not pending.done():
                pending.cancel()
                await asyncio.gather(pending,return_exceptions=True)
            await monitor.stop()
        closing = asyncio.create_task(cleanup())
        try:
            await drain(closing)
        except asyncio.CancelledError:
            status,metrics['error'] = 'interrupted','Worker interrupted during cleanup'
    if status in ('cancelled','interrupted','timeout') or 'error' in metrics:
        metrics['quality_evaluated'] = False
    if status == 'cancelled':
        metrics['reason'] = 'Cancelada por la persona que opera Arena; se solicitó interrumpir el turno de Codex.'
    metrics.update(agent_s=time.perf_counter()-started,resources=monitor.summary(),
                   task_s=time.perf_counter()-task_started if task_started else None,
                   failure_phase=phase if 'error' in metrics else None)
    return store.finish(run,metrics,status)
