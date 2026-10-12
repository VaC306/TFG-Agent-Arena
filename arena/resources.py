import platform
import time
import importlib.metadata
import asyncio
import math
import csv
import io
import json
import psutil
from .contracts import ResourceSample


def sample():
    result = ResourceSample(at=time.time())
    try:
        result.ram_available_bytes = psutil.virtual_memory().available
        result.worker_rss_bytes = psutil.Process().memory_info().rss
        cpu = psutil.Process().cpu_times()
        result.worker_cpu_s = cpu.user + cpu.system
    except (OSError, psutil.Error) as exc:
        result.unavailable.append(f"RAM: {type(exc).__name__}")
    try:
        import pynvml
        pynvml.nvmlInit()
        try:
            result.gpu = []
            for i in range(pynvml.nvmlDeviceGetCount()):
                device = pynvml.nvmlDeviceGetHandleByIndex(i)
                memory = pynvml.nvmlDeviceGetMemoryInfo(device)
                result.gpu.append({"index": i, "name": pynvml.nvmlDeviceGetName(device),
                                   "total_bytes": memory.total, "used_bytes": memory.used})
        finally:
            pynvml.nvmlShutdown()
    except Exception as exc:
        result.gpu = None
        result.unavailable.append(f"NVML: {type(exc).__name__}")
    return result.model_dump()


def provenance():
    return {"platform": platform.platform(), "python": platform.python_version(),
            "cpu": platform.processor(), "logical_cpus": psutil.cpu_count(),
            "ram_total_bytes": psutil.virtual_memory().total,
            "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
            "resources": sample()}


class ResourceMonitor:
    """One sampler per run; never leave writes behind after finishing the run."""
    def __init__(self,store,run_id,interval,sampler=sample):
        self.store,self.run_id,self.interval,self.sampler = store,run_id,interval,sampler
        self.started = time.perf_counter()
        self.phase = 'preparation'
        self.samples = []
        self.overhead_s = 0.
        self.task = None

    def capture(self):
        started = time.perf_counter()
        phase = self.phase
        try:
            value = self.sampler()
        except Exception as exc:
            value = {'at':time.time(),'scope':'host_and_worker','unavailable':[f'Sampler: {type(exc).__name__}']}
        value = value | {'elapsed_s':time.perf_counter()-self.started,'phase':phase}
        self.store.event(self.run_id,'resources',value)
        self.samples.append(value)
        self.overhead_s += time.perf_counter()-started

    async def capture_async(self):
        writing = asyncio.create_task(asyncio.to_thread(self.capture))
        try:
            await asyncio.shield(writing)
        except asyncio.CancelledError:
            await writing
            raise

    async def start(self):
        await self.capture_async()
        async def periodic():
            while True:
                await asyncio.sleep(self.interval)
                await self.capture_async()
        if self.interval is not None:
            self.task = asyncio.create_task(periodic())

    async def stop(self):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        await self.capture_async()

    def summary(self):
        def numbers(field):
            return [s[field] for s in self.samples if type(s.get(field)) in (int,float) and math.isfinite(s[field]) and s[field]>=0]
        rss,ram,cpu = numbers('worker_rss_bytes'),numbers('ram_available_bytes'),numbers('worker_cpu_s')
        gpu = {}
        for s in self.samples:
            for g in s.get('gpu') or []:
                if type(g.get('used_bytes')) is int and g['used_bytes']>=0:
                    key = str(g['index'])
                    gpu[key] = max(gpu.get(key,0),g['used_bytes'])
        return {'sampling':'periodic-v1' if self.interval is not None else 'endpoints',
                'requested_interval_s':self.interval,'samples':len(self.samples),
                'observed_span_s':self.samples[-1]['elapsed_s']-self.samples[0]['elapsed_s'] if len(self.samples)>1 else None,
                'max_gap_s':max((b['elapsed_s']-a['elapsed_s'] for a,b in zip(self.samples,self.samples[1:])),default=None),
                'sampling_overhead_s':self.overhead_s,
                'peak_worker_rss_bytes':max(rss) if rss else None,'min_host_ram_available_bytes':min(ram) if ram else None,
                'worker_cpu_delta_s':max(0,cpu[-1]-cpu[0]) if len(cpu)>1 else None,
                'peak_host_gpu_used_bytes':gpu or None,
                'unavailable':sorted({v for s in self.samples for v in s.get('unavailable',[])}),
                'note':'Observed samples, not guaranteed peaks. Host GPU/RAM includes other processes; worker RSS/CPU excludes the Ollama server. Sampling includes preparation and warmup and may affect timing.'}


def measurement_records(runs):
    return [{'run_id':r['id'],'task_id':r['task_id'],'repetition':r['repetition'],'branch':r['branch'],
             **{k:(r.get('result') or {}).get(k) for k in ('agent_s','preparation_s','task_s','warmup','resources','failure_phase')}} for r in runs]


def resources_csv(store,experiment_id):
    runs = store.list_runs(experiment_id)  # Also verifies ownership before reading traces.
    fields = ['run_id','task_id','branch','repetition','at','elapsed_s','phase','scope',
              'ram_available_bytes','worker_rss_bytes','worker_cpu_s','gpu','unavailable']
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output,fieldnames=fields)
    writer.writeheader()
    for run in runs:
        for event in store.events(run['id']):
            if event['kind'] != 'resources': continue
            row = event['payload'] | {'run_id':run['id'],'task_id':run['task_id'],'branch':run['branch'],'repetition':run['repetition']}
            for key in ('gpu','unavailable'): row[key] = json.dumps(row.get(key),ensure_ascii=False)
            writer.writerow({k:"'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v for k,v in row.items() if k in fields})
    return output.getvalue()
