"""Drain owned tasks even when the caller receives repeated cancellation."""
import asyncio


async def drain(task):
    interruption = None
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError as exc:
            interruption = exc
    result = task.result()
    if interruption is not None:
        raise interruption
    return result
