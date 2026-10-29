"""Check the configured database without printing its credentials."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arena.database import database_target, is_postgres
from arena.store import Store
from arena.accounts import Accounts


def main():
    target = database_target()
    try:
        store = Store(target)
        Accounts(store)
        with store.connect() as db:
            assert db.execute('SELECT 1').fetchone()[0] == 1
        print('Conexión correcta: ' + ('PostgreSQL, esquema privado arena.' if is_postgres(target) else 'SQLite local.'))
    except Exception:
        print('No se pudo comprobar la base. Revisa las dependencias, la red y la configuración local.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
