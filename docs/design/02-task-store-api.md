# Design Doc 2: Task Store + API (Phase 1)

> 前置：Phase 0 完成
> 产出：task_store.py, server.py 扩展, tasks_page.html, nginx /tasks
> 预计：45 分钟

---

## 2.1 task_store.py

SQLite 任务状态跟踪，与 Calibre metadata.db 分离。

```python
# /opt/calibre-stack/async-upload/task_store.py
import sqlite3, threading, time
from contextlib import contextmanager

DB_PATH = "/opt/calibre-stack/async-upload/tasks.db"
_lock = threading.Lock()

STAGES = ["uploaded", "adding", "converting", "searching_epub",
          "enriching", "deduping", "done", "scan"]
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
            attempt_count INTEGER DEFAULT 0,
            last_error TEXT DEFAULT '',
            owner TEXT DEFAULT '',
            started_at TIMESTAMP,
            finished_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")

@contextmanager
def _conn():
    with _lock, sqlite3.connect(DB_PATH) as c:
        c.row_factory = sqlite3.Row
        yield c

def create_task(title, source_file=None, book_id=None):
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO tasks (title, source_file, book_id) VALUES (?,?,?)",
            (title, source_file, book_id))
        c.commit()
        return cur.lastrowid

def update_task(tid, stage=None, status=None, detail=None, book_id=None):
    sets, params = [], []
    if stage: sets.append("stage=?"); params.append(stage)
    if status: sets.append("status=?"); params.append(status)
    if detail is not None: sets.append("detail=?"); params.append(detail)
    if book_id is not None: sets.append("book_id=?"); params.append(book_id)
    sets.append("updated_at=CURRENT_TIMESTAMP")
    params.append(tid)
    with _conn() as c:
        c.execute(f"UPDATE tasks SET {','.join(sets)} WHERE id=?", params)
        c.commit()

def get_task(tid):
    with _conn() as c:
        return dict(c.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone())

def list_tasks(limit=100, status=None):
    with _conn() as c:
        if status:
            rows = c.execute("SELECT * FROM tasks WHERE status=? ORDER BY id DESC LIMIT ?",
                             (status, limit)).fetchall()
        else:
            rows = c.execute("SELECT * FROM tasks ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

def count_by_status():
    with _conn() as c:
        rows = c.execute("SELECT status, count(*) n FROM tasks GROUP BY status").fetchall()
        return {r["status"]: r["n"] for r in rows}

def reset_interrupted(owner=""):
    """启动恢复：把上次运行残留的 running 任务（崩溃/重启）重置为 pending。
    返回被重置的任务数。"""
    with _conn() as c:
        n = c.execute(
            "UPDATE tasks SET status='pending', detail='重启恢复：上次未完成', owner='' "
            "WHERE status='running' AND (owner=? OR ?='')", (owner, owner)).rowcount
        c.commit()
        return n

def claim_next(owner):
    """原子认领：取一条 pending 任务置为 running，返回任务 dict 或 None。
    单 worker 下认领即串行；多 worker 时 owner 区分，避免重复处理。"""
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM tasks WHERE status='pending' "
            "ORDER BY id ASC LIMIT 1").fetchone()
        if not row:
            return None
        c.execute(
            "UPDATE tasks SET status='running', owner=?, attempt_count=attempt_count+1, "
            "started_at=CURRENT_TIMESTAMP, finished_at=NULL, detail='处理中' "
            "WHERE id=?", (owner, row["id"]))
        c.commit()
        return dict(row)

def mark_finished(tid, status, detail="", last_error=""):
    with _conn() as c:
        c.execute(
            "UPDATE tasks SET status=?, detail=?, last_error=?, finished_at=CURRENT_TIMESTAMP "
            "WHERE id=?", (status, detail, last_error, tid))
        c.commit()

if __name__ == "__main__":
    init_db()
    print("tasks.db ready")
```

## 2.1.1 库级操作锁（library lock，跨进程串行化）

`tasks.db` 的 `_lock` 仅保护任务表自身；而 `metadata.db` 的并发写入（入库 / 加格式 / 移除 / 元数据 / 去重 / 扫描）须另用**跨进程**锁串行化——worker 线程、手动 CLI、扫描可能同时跑。线程级 `threading.Lock` 跨进程无效，故统一改用 `fcntl.flock` 文件锁：

```python
# /opt/calibre-stack/async-upload/lib_lock.py
import fcntl, threading, os
from contextlib import contextmanager

LOCK_PATH = "/opt/calibre-stack/async-upload/library.lock"
_local = threading.Lock()  # 仅防止同一进程内重入

@contextmanager
def library_lock():
    """串行化所有 Calibre 库写操作（add/remove/metadata/dedupe/scan）。
    跨进程有效；多进程/手动 CLI 并发也不损坏 metadata.db。"""
    with _local:
        with open(LOCK_PATH, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

- `format_converter.py` / `deduplicator.py` 中的 `CALIBRE_LOCK = None`（占位）改为 `from lib_lock import library_lock`，并用 `with library_lock():` 包裹所有 `calibredb` 调用。
- 所有写库端点（convert / search_epub / metadata / dedupe / scan）统一经此锁，避免与 Calibre-Web 自身写操作互相踩踏。

## 2.2 server.py 扩展

在现有 `server.py` 基础上新增路由（保留 `/upload`、`/health`）。

新增导入与使用：
```python
import task_store as ts
ts.init_db()
```

`do_GET` 扩展：
```python
def do_GET(self):
    path = self.path.split("?")[0]
    if path == "/health":
        self._send_json(200, {"status": "ok"})
    elif path == "/tasks":
        self._send_html(open("/opt/calibre-stack/async-upload/tasks_page.html").read())
    elif path == "/api/tasks":
        self._send_json(200, {"tasks": ts.list_tasks(200), "counts": ts.count_by_status()})
    else:
        self._send_json(404, {"error": "not found"})
```

`do_POST` 扩展（解析 JSON body 辅助）：
```python
def _read_json(self):
    length = int(self.headers.get("Content-Length", 0))
    return json.loads(self.rfile.read(length)) if length else {}

def do_POST(self):
    path = self.path.split("?")[0]
    if path == "/api/upload":
        return self._handle_upload()   # 现有逻辑重命名
    if path == "/api/scan":
        return self._handle_scan()
    # /api/tasks/{id}/retry | /api/books/{id}/convert ...
    import re
    m = re.match(r"/api/tasks/(\d+)/retry", path)
    if m:
        tid = int(m.group(1))
        # 仅入队：置 pending，由持久化 worker 认领执行（不再 spawn daemon thread）
        ts.update_task(tid, status="pending", detail="", last_error="")
        self._send_json(200, {"ok": True, "task_id": tid})
        return
    # books/{id}/{action}
    m = re.match(r"/api/books/(\d+)/(\w+)", path)
    if m:
        bid, action = int(m.group(1)), m.group(2)
        # 入队一条手动动作任务，worker 认领后调用 manual_action(bid, action)
        create_and_enqueue_manual(bid, action)
        self._send_json(202, {"ok": True, "book_id": bid, "action": action})
        return
    self._send_json(404, {"error": "not found"})
```

新增 `_send_html` 辅助：
```python
def _send_html(self, html):
    try:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html.encode())))
        self.end_headers()
        self.wfile.write(html.encode())
    except (BrokenPipeError, ConnectionResetError):
        pass

## 2.2.1 持久化 Worker（替换 daemon thread）

> **变更要点**：旧设计在每个请求里 `threading.Thread(target=..., daemon=True).start()`，
> 进程重启即丢失在途任务、崩溃无恢复、无法限并发。改为**常驻单 worker 轮询认领**模型。

```python
import threading, time, uuid

WORKER_ID = uuid.uuid4().hex[:8]

def run_worker(interval=2.0):
    """常驻线程：循环认领 pending 任务并执行流水线。进程启动调用一次。"""
    while True:
        try:
            task = ts.claim_next(WORKER_ID)
            if task:
                run_pipeline_by_task(task["id"])   # 现有流水线，内部用 library_lock
            else:
                time.sleep(interval)
        except Exception as e:
            log.exception("worker loop error: %s", e)
            time.sleep(interval)

# 启动恢复 + 启动 worker（server 模块加载时执行一次）
ts.reset_interrupted()                 # 把残留 running 重置为 pending
threading.Thread(target=run_worker, daemon=True, name="task-worker").start()
```

- **原子认领**：`claim_next` 先 `SELECT` 再 `UPDATE status='running'`，单 worker 下天然串行；
  多 worker 时靠 `owner` 区分，互不重复（必要时改 `claim_next` 为 `UPDATE ... WHERE id=? AND status='pending'` 的原子语句）。
- **幂等**：每个动作（convert / search_epub / metadata / dedupe）本身幂等——`add_format` 已存在则跳过、
  `dedupe` 仅移多余副本、`metadata` 只补缺字段。重试同一任务安全。
- **重启恢复**：`reset_interrupted()` 在启动时把上次 `running` 残留（崩溃/重启）重置为 `pending`，
  由 worker 重新认领，不丢任务。
- **手动动作**：`create_and_enqueue_manual(bid, action)` 写入一条 `stage=action, status='pending'` 任务，
  与上传任务走同一 worker，避免额外线程。
- **限并发**：单 worker 即单并发；如需并发，启动 N 个 `run_worker` 并依赖 `claim_next` 的原子认领。
```

## 2.3 nginx /tasks 路由

在 `/etc/nginx/sites-available/calibre-web` 的 `server` 块内新增（与 /async-upload 同层级）：
```nginx
location /tasks {
    auth_request /_auth_check;
    proxy_pass http://127.0.0.1:8086/tasks;
    proxy_set_header Host $host;
}
```
重载：`nginx -t && systemctl reload nginx`

### 登录跳转机制（已核实 live nginx，修正既往误判）
- `/_auth_check` 代理到 Calibre-Web 根路径：已登录返回 `200`，**未登录返回 `302`**（跳转 /login）。
- nginx `auth_request` 对子请求返回 `302` 视作**内部错误 → 映射为 `500`**（只有 401/403 才会映射成 401/403）。
- 因此 live `/etc/nginx/sites-available/calibre-web` 第 18 行的 **server 级 `error_page 500 = @login_redirect;`** 才是真正生效的登录跳转钩子，它覆盖所有 `auth_request` 位置：`/async-upload`、`/api/`、以及本节的 `/tasks`。
- **既往 Doc 9 §9.2.4 的「需补 `error_page 401`」系误判**：本流程中 `401` 永不产生（子请求返回 302 而非 401），`error_page 401` 实为永不触发的死配置。故上面 `/tasks` 片段**不写** `error_page 401`，依赖已有的 server 级 `error_page 500` 即可。
- 结论：**所有新端点已在 nginx 鉴权覆盖下**，无需额外 error_page。

> 注：最大上传文件统一为 `200MB`（`MAX_UPLOAD_SIZE=200MB`）。nginx `client_max_body_size 200M` 与 `server.py` 的 `200*1024*1024` 上限现已对齐；任何调整必须同时改 nginx 与 `server.py`，以 `MAX_UPLOAD_SIZE` 为单一事实来源（见 deployment.md §2.3）。

## 2.4 tasks_page.html

**采用 UI Rewrite Design System（见 `docs/ui-rewrite/01-phase1.md`），与 Calibre-Web / 上传页统一视觉**，不使用旧 Bootstrap 风格（旧 `upload_page.html` 亦须在 P1 后迁移到 Design System）。表格轮询 `/api/tasks` 每 5s。
- 列：ID | 标题 | 源文件 | 阶段 | 状态 | 详情 | 操作
- 操作按钮：`重试`(tasks/{id}/retry)、`转格式/搜EPUB/补信息/去重`(books/{id}/{action})
- 顶部：`[全库扫描]` 按钮 POST `/api/scan`；显示 counts
- 状态/阶段用 Design System 的 badge 组件（成功=绿、失败=红、运行中=蓝脉冲），暗色模式自动适配。

## 2.5 验证

```bash
python3 task_store.py          # 建表
# 重启服务
systemctl restart calibre-async-upload
curl -u <user>:<pass> -b cookie http://localhost:8086/api/tasks
# 期望 {"tasks":[],"counts":{}}
```

## 2.6 边界

- tasks.db 写入加锁，避免并发写损坏
- 页面仅读，所有动作走后台线程
- 大表限制 200 行返回
