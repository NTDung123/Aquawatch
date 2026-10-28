import json
import sqlite3
from datetime import datetime, timezone
from .settings import DATA

DB = DATA / "aquawatch.sqlite3"


def now():
    return datetime.now(timezone.utc).isoformat()


def connect():
    db = sqlite3.connect(DB, timeout=30)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS videos (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS acknowledgments (job_id TEXT, event_id TEXT, body TEXT, PRIMARY KEY(job_id,event_id))")
    return db


def put(kind, item):
    if kind not in ("videos", "jobs"):
        raise ValueError("Invalid collection")
    with connect() as db:
        db.execute(f"INSERT OR REPLACE INTO {kind} VALUES (?,?)", (item["id"], json.dumps(item, ensure_ascii=False)))
    return item


def get(kind, key):
    if kind not in ("videos", "jobs"):
        raise ValueError("Invalid collection")
    with connect() as db:
        row = db.execute(f"SELECT body FROM {kind} WHERE id=?", (key,)).fetchone()
    return json.loads(row[0]) if row else None


def all_items(kind):
    if kind not in ("videos", "jobs"):
        raise ValueError("Invalid collection")
    with connect() as db:
        rows = db.execute(f"SELECT body FROM {kind} ORDER BY rowid DESC").fetchall()
    return [json.loads(r[0]) for r in rows]


def delete_library_video(key):
    with connect() as db:
        row = db.execute("SELECT body FROM videos WHERE id=?", (key,)).fetchone()
        if row and json.loads(row[0]).get("library"):
            db.execute("DELETE FROM videos WHERE id=?", (key,))


def acknowledge(job_id, event_id, note):
    body = {"acknowledged": True, "acknowledged_at": now(), "note": note}
    with connect() as db:
        db.execute("INSERT OR REPLACE INTO acknowledgments VALUES (?,?,?)", (job_id, event_id, json.dumps(body, ensure_ascii=False)))
    return body


def acknowledgments(job_id):
    with connect() as db:
        return {r[0]: json.loads(r[1]) for r in db.execute("SELECT event_id,body FROM acknowledgments WHERE job_id=?", (job_id,))}
