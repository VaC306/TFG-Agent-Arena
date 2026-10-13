"""Explicit ticks and checkpoints; deadlines only detect hung tests."""
import asyncio


class Clock:
    def __init__(self,value=1000.):self.value=value
    def __call__(self):return self.value
    def advance(self,seconds):self.value+=seconds


class Ticks:
    def __init__(self):
        self.queue=asyncio.Queue();self.delays=[]
    async def __call__(self,delay):
        self.delays.append(delay)
        await self.queue.get()
    def release(self):self.queue.put_nowait(None)


async def checkpoint(event):
    await asyncio.wait_for(event.wait(),5)
