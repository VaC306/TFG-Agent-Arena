"""Import a stopped SQLite arena into an empty PostgreSQL arena schema atomically."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from arena.database import database_target, is_postgres
from arena.store import Store
from arena.accounts import Accounts

TABLES = (
    'users', 'experiments', 'experiment_owners', 'runs', 'events', 'campaigns',
    'campaign_attempts', 'attempt_annotations', 'library_items', 'human_reviews', 'submissions',
)


def migrate(source_path, target):
    if not is_postgres(target):
        raise ValueError('Configura ARENA_DATABASE_URL con el destino PostgreSQL.')
    source_path = Path(source_path).resolve(strict=True)
    source = sqlite3.connect(source_path.as_uri() + '?mode=ro', uri=True)
    source.row_factory = sqlite3.Row
    try:
        source.execute('BEGIN')
        if source.execute("SELECT 1 FROM runs WHERE status IN ('queued','running') LIMIT 1").fetchone():
            raise ValueError('Finaliza o cancela los trabajos locales antes de importar.')
        store = Store(target)
        Accounts(store)
        counts = {}
        with store.connect() as destination:
            destination.execute('BEGIN IMMEDIATE')
            for table in (*TABLES, 'sessions', 'auth_attempts', 'provider_links', 'worker_signals', 'run_workers'):
                if destination.execute(f'SELECT 1 FROM {table} LIMIT 1').fetchone():
                    raise ValueError('El destino contiene datos. La importación exige un destino vacío.')
            source_tables = {row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table in TABLES:
                if table not in source_tables:
                    counts[table] = 0
                    continue
                columns = [row['name'] for row in source.execute(f'PRAGMA table_info({table})')]
                # Column identifiers come exclusively from this allowlisted local schema.
                if any(not name.replace('_', '').isalnum() for name in columns):
                    raise ValueError('El esquema de origen contiene columnas no admitidas.')
                quoted = ','.join('"' + name + '"' for name in columns)
                placeholders = ','.join('?' for _ in columns)
                rows = source.execute(f'SELECT {quoted} FROM {table} ORDER BY rowid')
                count = 0
                for row in rows:
                    destination.execute(f'INSERT INTO {table}({quoted}) VALUES ({placeholders})', tuple(row))
                    count += 1
                counts[table] = count
            destination.connection.execute("SELECT setval(pg_get_serial_sequence('arena.events','seq'), COALESCE(MAX(seq),1), MAX(seq) IS NOT NULL) FROM arena.events")
        return counts
    finally:
        source.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    try:
        counts = migrate(args.source, database_target())
        print('Importación completada. La base SQLite original permanece intacta.')
        print(json.dumps(counts, ensure_ascii=False))
    except (ValueError, FileNotFoundError) as exc:
        # Only our explicit validation messages; never echo provider errors/URLs.
        if isinstance(exc, FileNotFoundError):
            print('No existe la base SQLite de origen.', file=sys.stderr)
        else:
            print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        print('Importación fallida; los datos insertados se han revertido. Revisa la conexión y el esquema.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
