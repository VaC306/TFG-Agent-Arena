"""Development worker with cooperative shutdown requested by dev.ps1."""
import argparse
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arena.store import Store
from arena.worker import work


async def main(database: str, directory: Path):
    pending = asyncio.create_task(work(Store(database)))
    try:
        await asyncio.sleep(0)
        if pending.done():
            await pending
        (directory / 'worker-ready').touch()
        while not (directory / 'stop-worker').exists():
            if pending.done():
                await pending
                return
            await asyncio.sleep(.25)
    finally:
        pending.cancel()
        try:
            await pending
        except asyncio.CancelledError:
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', required=True)
    parser.add_argument('--session-directory', type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(main(args.db, args.session_directory))
