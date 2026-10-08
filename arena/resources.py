import platform
import time
import importlib.metadata
import psutil
from .contracts import ResourceSample


def sample():
    result = ResourceSample(at=time.time())
    try:
        result.ram_available_bytes = psutil.virtual_memory().available
        result.worker_rss_bytes = psutil.Process().memory_info().rss
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
