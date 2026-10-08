import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from .contracts import Event


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS experiments(id TEXT PRIMARY KEY, snapshot TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS runs(
                    id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL REFERENCES experiments(id),
                    position INTEGER NOT NULL, status TEXT NOT NULL, data TEXT NOT NULL,
                    cancel_requested INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS events(
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL REFERENCES runs(id),
                    kind TEXT NOT NULL, at REAL NOT NULL, payload TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS events_run ON events(run_id, seq);
            """)

    @contextmanager
    def connect(self):
        with sqlite3.connect(self.path, timeout=30) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys=ON")
            yield db

    def create(self, experiment_id, snapshot, runs):
        with self.connect() as db:
            db.execute("INSERT INTO experiments VALUES (?,?)", (experiment_id, json.dumps(snapshot)))
            for run in runs:
                db.execute("INSERT INTO runs(id,experiment_id,position,status,data) VALUES (?,?,?,?,?)",
                           (run.id, experiment_id, run.position, run.status, run.model_dump_json()))

    def snapshot(self, experiment_id):
        with self.connect() as db:
            row = db.execute("SELECT snapshot FROM experiments WHERE id=?", (experiment_id,)).fetchone()
            if not row:
                raise KeyError(experiment_id)
            return json.loads(row[0])

    def list_runs(self, experiment_id=None):
        with self.connect() as db:
            rows = db.execute("SELECT data FROM runs " + ("WHERE experiment_id=? " if experiment_id else "") +
                              "ORDER BY rowid", (experiment_id,) if experiment_id else ()).fetchall()
            return [json.loads(r[0]) for r in rows]

    def claim(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            # A single active run globally preserves sequential resource conditions even with two workers.
            if db.execute("SELECT 1 FROM runs WHERE status='running'").fetchone():
                return None
            row = db.execute("SELECT * FROM runs WHERE status='queued' ORDER BY rowid LIMIT 1").fetchone()
            if not row:
                return None
            run = json.loads(row["data"])
            run.update(status="running", started_at=time.time())
            db.execute("UPDATE runs SET status='running',data=? WHERE id=?", (json.dumps(run), run["id"]))
            return run

    def event(self, run_id, kind, payload):
        event = Event(run_id=run_id, kind=kind, payload=payload, at=time.time())
        with self.connect() as db:
            db.execute("INSERT INTO events(run_id,kind,at,payload) VALUES (?,?,?,?)",
                       (event.run_id, event.kind, event.at, json.dumps(event.payload)))

    def events(self, run_id):
        with self.connect() as db:
            return [dict(row) | {"payload": json.loads(row["payload"])} for row in
                    db.execute("SELECT * FROM events WHERE run_id=? ORDER BY seq", (run_id,))]

    def cancelled(self, run_id):
        with self.connect() as db:
            return bool(db.execute("SELECT cancel_requested FROM runs WHERE id=?", (run_id,)).fetchone()[0])

    def cancel(self, run_id):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT data,status FROM runs WHERE id=?", (run_id,)).fetchone()
            if not row:
                raise KeyError(run_id)
            if row["status"] == "queued":
                run = json.loads(row["data"])
                run.update(status="cancelled", finished_at=time.time(), result={"success": False, "format_ok": False, "error": "Cancelled before execution"})
                db.execute("UPDATE runs SET status='cancelled',data=?,cancel_requested=1 WHERE id=?", (json.dumps(run), run_id))
            elif row["status"] == "running":
                db.execute("UPDATE runs SET cancel_requested=1 WHERE id=?", (run_id,))
        self.event(run_id, "cancel_requested", {})

    def finish(self, run, result, status):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT status,cancel_requested FROM runs WHERE id=?", (run["id"],)).fetchone()
            if row["status"] != "running":
                return row["status"]
            if row["cancel_requested"]:
                status = "cancelled"
                result.update(success=False, error="Cancelled")
            run.update(status=status, finished_at=time.time(), result=result)
            db.execute("UPDATE runs SET status=?,data=? WHERE id=?", (status, json.dumps(run), run["id"]))
            db.execute("INSERT INTO events(run_id,kind,at,payload) VALUES (?,?,?,?)",
                       (run["id"], "finished", run["finished_at"], json.dumps({"status": status, **result})))
            return status

    def recover(self):
        """Explicit recovery only: caller must have stopped all workers first."""
        for run in self.list_runs():
            if run["status"] == "running":
                self.event(run["id"], "interruption", {"reason": "Manual recovery after worker loss"})
                self.finish(run, {"success": False, "format_ok": False, "error": "Worker interrupted; partial metrics in events"}, "interrupted")
