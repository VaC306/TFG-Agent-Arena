"""Consistent SQLite backup and verified restore to a NEW database only."""
import os
import sqlite3
from contextlib import closing
from pathlib import Path


def verify(db):
    if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
        raise ValueError('La base no supera la comprobación de integridad')
    if db.execute('PRAGMA foreign_key_check').fetchall():
        raise ValueError('La base contiene referencias inconsistentes')
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {'experiments','runs','events'}<=tables:
        raise ValueError('No es una copia de Arena')


def copy_database(source, destination, restore=False):
    from .database import is_postgres
    if is_postgres(source) or is_postgres(destination):
        raise ValueError('Esta copia/restauración admite solo SQLite. Para PostgreSQL utiliza su procedimiento de backup.')
    source, destination = Path(source).resolve(),Path(destination).resolve()
    if not source.is_file() or source == destination:
        raise ValueError('Selecciona una base origen existente y un destino nuevo')
    destination.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation prevents accidental overwrite, including concurrent requests.
    fd = os.open(destination,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    os.close(fd)
    try:
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as src:
            verify(src)
            with closing(sqlite3.connect(destination)) as dst:
                src.backup(dst)
                if restore:
                    # Restored processes and browser sessions are never live.
                    tables = {r[0] for r in dst.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    for table in ('sessions','provider_links','worker_signals'):
                        if table in tables:
                            dst.execute('DELETE FROM '+table)
                    dst.commit()
                verify(dst)
        return str(destination)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
