import asyncio
import copy
import json
import time
import httpx
from .evaluator import evaluate
from .tools import Tools
from .resources import sample, ResourceMonitor
from .attachments import user_message
from .protocol import inference_identity
from .evaluator import EVALUATOR_VERSION


class LimitReached(Exception):
    pass


class Cancelled(Exception):
    pass


async def execute(run, task, environment, config, adapter, store, measurement=None):
    started = time.perf_counter()
    tools = Tools(environment)
    messages = [{"role": "system", "content": config.system_prompt}, user_message(task)]
    names = []
    metrics = {"success": False, "format_ok": False, "queue_s": max(0, run["started_at"] - run["queued_at"]),
               "input_tokens": 0, "output_tokens": 0, "server_eval_s": 0., "calls": 0,
               "tool_calls": 0, "tool_errors": 0, "tool_s": 0., "usage_complete": True}
    metrics.update(evaluator_version=EVALUATOR_VERSION, quality_evaluated=False)
    measurement = measurement or {}
    warmup = measurement.get('warmup','none')
    metrics.update(warmup={'policy':warmup,'status':'not_requested' if warmup == 'none' else 'not_started'},task_s=None)
    monitor = ResourceMonitor(store,run['id'],measurement.get('resource_sample_interval_s'),sample)
    task_started = None
    if task.criteria is None and (task.expected_answer is None or task.evaluation == 'none'):
        metrics.update(success=None, format_ok=None, evaluation='not_evaluated')
    store.event(run["id"], "input", {"messages": messages, "environment": environment})

    async def checked(awaitable):
        pending = asyncio.create_task(awaitable)
        try:
            while not pending.done():
                if store.cancelled(run["id"]):
                    raise Cancelled()
                await asyncio.wait({pending}, timeout=0.1)
            return await pending
        finally:
            if not pending.done():
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)

    async def loop():
        nonlocal task_started
        prepare_start = time.perf_counter()
        metadata = await checked(adapter.metadata(config.model))
        identity = inference_identity(config.model, metadata)
        store.record_inference_metadata(run, metadata, identity)
        metrics['inference_identity'] = identity
        metrics['preparation_s'] = time.perf_counter()-prepare_start
        if any(a.media_type.startswith('image/') for a in task.attachments):
            if 'simulated' not in metadata.get('adapter', '') and 'vision' not in metadata.get('show', {}).get('capabilities', []):
                raise ValueError('El modelo no declara capacidad de visión; no se enviaron las imágenes')
        if warmup == 'per_run':
            monitor.phase = 'warmup'
            warm_config = config.model_copy(update={'tools_enabled':False})
            warm_messages = [{'role':'user','content':'Reply OK.'}]
            request = {'messages':warm_messages,'max_output_tokens':1}
            if callable(getattr(adapter,'payload',None)):
                request['payload'] = adapter.payload(warm_messages,warm_config,1)
            store.event(run['id'],'warmup_request',request)
            warm_start = time.perf_counter()
            metrics['warmup']['status'] = 'running'
            try:
                response = await checked(adapter.chat(warm_messages,warm_config,1))
                if response.get('done') is not True:
                    raise ValueError('Incomplete warmup response')
                counters = {k:response.get(k) for k in ('prompt_eval_count','eval_count','eval_duration','load_duration','total_duration')}
                for key in ('prompt_eval_count','eval_count','eval_duration'):
                    if type(counters[key]) is not int or counters[key] < 0:
                        raise ValueError('Invalid warmup usage counters')
                metrics['warmup'].update(status='completed',usage=counters)
                store.event(run['id'],'warmup_response',{'usage':counters,'done_reason':response.get('done_reason')})
                # Model identity must still match before sending the actual input.
                metadata = await checked(adapter.metadata(config.model))
                identity = inference_identity(config.model,metadata)
                store.record_inference_metadata(run,metadata,identity)
            except BaseException:
                metrics['warmup']['status'] = 'failed'
                raise
            finally:
                metrics['warmup']['duration_s'] = time.perf_counter()-warm_start
        monitor.phase = 'task'
        task_started = time.perf_counter()
        for _ in range(config.limits.max_calls):
            if store.cancelled(run["id"]):
                raise Cancelled()
            remaining = config.limits.max_output_tokens - metrics["output_tokens"]
            if remaining <= 0:
                raise LimitReached("output_tokens")
            metrics["calls"] += 1
            request = {"messages": copy.deepcopy(messages), "max_output_tokens": remaining}
            if callable(getattr(adapter, 'payload', None)):
                request['payload'] = copy.deepcopy(adapter.payload(messages, config, remaining))
            store.event(run["id"], "inference_request", request)
            call_start = time.perf_counter()
            try:
                response = await checked(adapter.chat(copy.deepcopy(messages), config, remaining))
            except BaseException:
                metrics["usage_complete"] = False
                raise
            message = response["message"]
            store.event(run["id"], "inference_response", {"response": response, "duration_s": time.perf_counter() - call_start})
            if not all(k in response for k in ("prompt_eval_count", "eval_count", "eval_duration")):
                metrics["usage_complete"] = False
                raise ValueError("Missing inference usage counters")
            if any(type(response[k]) is not int or response[k] < 0 for k in ("prompt_eval_count", "eval_count", "eval_duration")):
                metrics["usage_complete"] = False
                raise ValueError("Invalid inference usage counters")
            metrics["input_tokens"] += response["prompt_eval_count"]
            metrics["output_tokens"] += response["eval_count"]
            metrics["server_eval_s"] += response["eval_duration"] / 1e9
            if response.get("done") is not True:
                raise ValueError("Incomplete server response")
            if response.get("done_reason") == "length" or metrics["output_tokens"] > config.limits.max_output_tokens:
                raise LimitReached("output_tokens")
            messages.append(message)
            calls = message.get("tool_calls") or []
            if not calls:
                content = message.get("content")
                if not isinstance(content, str) or not content.strip():
                    raise ValueError('El servidor no devolvió una respuesta de texto válida')
                metrics["answer"] = content
                metrics.update(evaluate(metrics["answer"], task, names))
                metrics['quality_evaluated'] = metrics['success'] is not None
                if metrics['success'] is None:
                    return 'completed'
                return "succeeded" if metrics["success"] else "failed"
            if not config.tools_enabled:
                raise ValueError('Esta comparación de archivos no permite llamadas a herramientas')
            for call in calls:
                if store.cancelled(run["id"]):
                    raise Cancelled()
                if metrics["tool_calls"] >= config.limits.max_tool_calls:
                    raise LimitReached("tool_calls")
                function = call["function"]
                name, arguments = function["name"], function["arguments"]
                names.append(name)
                metrics["tool_calls"] += 1
                tool_start = time.perf_counter()
                store.event(run["id"], "tool_request", {"name": name, "arguments": arguments})
                error = None
                try:
                    result = tools.call(name, arguments)
                except Exception as exc:
                    error = str(exc)
                    metrics["tool_errors"] += 1
                    result = {"error": error}
                duration = time.perf_counter() - tool_start
                metrics["tool_s"] += duration
                store.event(run["id"], "tool_result", {"name": name, "result": result, "error": error, "duration_s": duration})
                messages.append({"role": "tool", "tool_name": name, "content": json.dumps(result)})
        raise LimitReached("model_calls")

    try:
        await monitor.start()
        async with asyncio.timeout(config.limits.timeout_s):
            status = await loop()
    except (TimeoutError, httpx.TimeoutException) as exc:
        status, metrics["error"] = "timeout", type(exc).__name__
    except LimitReached as exc:
        status, metrics["error"] = "limit", str(exc)
    except Cancelled:
        status, metrics["error"] = "cancelled", "Cancelled by user"
    except asyncio.CancelledError:
        status, metrics["error"] = "interrupted", "Worker interrupted"
    except Exception as exc:
        status, metrics["error"] = "failed", f"{type(exc).__name__}: {exc}"
    if task_started is not None:
        metrics['task_s'] = time.perf_counter()-task_started
    monitor.phase = 'finished'
    closing = asyncio.create_task(monitor.stop())
    try:
        await asyncio.shield(closing)
    except asyncio.CancelledError:
        # Interruption can arrive after the answer, while a capture is being drained.
        # Persist a terminal state instead of leaking a running execution.
        status,metrics['error'] = 'interrupted','Worker interrupted during measurement cleanup'
        while not closing.done():
            try:
                await asyncio.shield(closing)
            except asyncio.CancelledError:
                continue
        await closing
        metrics['failure_phase'] = 'measurement_cleanup'
    if 'error' in metrics:
        metrics['quality_evaluated'] = False
    metrics['resources'] = monitor.summary()
    metrics['failure_phase'] = metrics.get('failure_phase') or (('task' if task_started is not None else 'warmup' if metrics['warmup']['status'] == 'failed' else 'preparation') if 'error' in metrics else None)
    metrics["agent_s"] = time.perf_counter() - started
    metrics["server_tps"] = metrics["output_tokens"] / metrics["server_eval_s"] if metrics["server_eval_s"] and metrics["usage_complete"] else None
    metrics["agent_output_tps"] = metrics["output_tokens"] / metrics["agent_s"] if metrics["usage_complete"] else None
    return store.finish(run, metrics, status)
