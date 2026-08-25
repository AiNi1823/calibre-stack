#!/usr/bin/env python3
"""任务状态存储：SQLite，与 Calibre metadata.db 分离。

用于跟踪每次上传/扫描的后台处理阶段与结果，供 /tasks 页面与 API 读取。
所有写入加锁，避免并发写损坏。
"""

import sqlite3
import threading
from contextlib import contextmanager

DB_PATH = "/opt/calibre-stack/async-upload/tasks.db"
_lock = threading.Lock()

STAGES = [
    "uploaded", "adding", "converting", "enriching",
    "searching_epub", "deduping", "done", "scan",
]
STATUSES = ["pending", "running", "success", "failed", "cancelled"]


def init_db():
    with _lock, sqlite3.connect(DB_PATH) as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER,
            title TEXT NOT NULL,
            source_file TEXT,
            stage TEXT DEFAULT 'uploaded',
            status TEXT DEFAULT 'pending',
            detail TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at)")


@contextmanager
def _conn():
    with _lock, sqlite3.connect(DB_PATH) as c:
        c.row_factory = sqlite3.Row
        yield c


def create_task(title, source_file=None, book_id=None):
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO tasks (title, source_file, book_id, status, stage) "
            "VALUES (?,?,?, 'pending', 'uploaded')",
            (title, source_file, book_id))
        c.commit()
        return cur.lastrowid


def update_task(tid, stage=None, status=None, detail=None, book_id=None):
    sets, params = [], []
    if stage:
        sets.append("stage=?")
        params.append(stage)
    if status:
        sets.append("status=?")
        params.append(status)
    if detail is not None:
        sets.append("detail=?")
        params.append(detail)
    if book_id is not None:
        sets.append("book_id=?")
        params.append(book_id)
    sets.append("updated_at=CURRENT_TIMESTAMP")
    params.append(tid)
    with _conn() as c:
        c.execute("UPDATE tasks SET {} WHERE id=?".format(",".join(sets)), params)
        c.commit()


def get_task(tid):
    with _conn() as c:
        row = c.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
        return dict(row) if row else None


def list_tasks(limit=200, status=None):
    with _conn() as c:
        if status:
            rows = c.execute(
                "SELECT * FROM tasks WHERE status=? ORDER BY id DESC LIMIT ?",
                (status, limit)).fetchall()
        else:
            rows = c.execute(
                "SELECT * FROM tasks ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def count_by_status():
    with _conn() as c:
        rows = c.execute(
            "SELECT status, count(*) n FROM tasks GROUP BY status").fetchall()
        return {r["status"]: r["n"] for r in rows}


if __name__ == "__main__":
    init_db()
    print("tasks.db ready at", DB_PATH)
