"""Repeat critical tests in fresh interpreters with independent order/hash seeds."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CRITICAL = ['tests/test_arena.py','tests/test_measurement.py','tests/test_runtime_reliability.py',
            'tests/test_worker_annotations.py','tests/test_accounts.py']
for order, hash_seed in [(17, '1'), (91, '42'), (203, '98765')]:
    print(f'Order seed={order}, PYTHONHASHSEED={hash_seed}', flush=True)
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q',
                             f'--arena-order-seed={order}', *CRITICAL],
                            cwd=ROOT, env=os.environ | {'PYTHONHASHSEED':hash_seed})
    if result.returncode:
        sys.exit(result.returncode)
