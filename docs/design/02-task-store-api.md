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

if __name__ == "__main__":
    init_db()
    print("tasks.db ready")
```

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
        ts.update_task(tid, status="pending", detail="")
        self._send_json(200, {"ok": True, "task_id": tid})
        # 触发后台重跑
        threading.Thread(target=run_pipeline_by_task, args=(tid,), daemon=True).start()
        return
    # books/{id}/{action}
    m = re.match(r"/api/books/(\d+)/(\w+)", path)
    if m:
        bid, action = int(m.group(1)), m.group(2)
        threading.Thread(target=manual_action, args=(bid, action), daemon=True).start()
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

风格沿用 upload_page.html，表格轮询 `/api/tasks` 每 5s。
- 列：ID | 标题 | 源文件 | 阶段 | 状态 | 详情 | 操作
- 操作按钮：`重试`(tasks/{id}/retry)、`转格式/搜EPUB/补信息/去重`(books/{id}/{action})
- 顶部：`[全库扫描]` 按钮 POST `/api/scan`；显示 counts

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
