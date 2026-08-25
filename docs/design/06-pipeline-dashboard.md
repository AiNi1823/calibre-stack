# Design Doc 6: Pipeline Orchestrator + Dashboard (Phase 2)

> 前置：Doc 2-5 全部完成
> 产出：post_process.py（编排）, server.py 接入, tasks_page.html（仪表盘）
> 核心：上传即触发，阶段化写入 tasks.db

---

## 6.1 流水线阶段

```
uploaded → adding → [converting | searching_epub] → enriching → deduping → done
```

## 6.2 post_process.py

```python
# /opt/calibre-stack/async-upload/post_process.py
import os, logging, threading, subprocess
import task_store as ts
import format_converter as fc
import epub_sources as es
import metadata_enricher as me
import deduplicator as dd

log = logging.getLogger("post_process")
LIBRARY = os.environ.get("CALIBRE_DBPATH", "/opt/calibre-library/Calibre Library")
STAGING = "/opt/calibre-web/upload_staging"
CALIBRE_LOCK = threading.Lock()
fc.CALIBRE_LOCK = CALIBRE_LOCK
dd.CALIBRE_LOCK = CALIBRE_LOCK

def _add_to_library(filepath):
    with CALIBRE_LOCK:
        r = subprocess.run(["calibredb", "add", "--with-library", LIBRARY,
                            "--automerge", "overwrite", filepath],
                           capture_output=True, text=True, timeout=300)
        # B3(复审) 修复：原方案用 MAX(id) 在释放锁后读取，并发上传会串号。
        # 改为在持锁期间从 stdout 解析 "Added book N" 直接拿本批 id。
        import re
        m = re.search(r"Added book (\d+)", r.stdout)
        bid = int(m.group(1)) if m else None
    return r.returncode == 0, r.stderr, bid

def run_pipeline(filepath, task_id):
    fname = os.path.basename(filepath)
    ts.update_task(task_id, stage="adding", status="running")
    ok, err, book_id = _add_to_library(filepath)
    if not ok:
        ts.update_task(task_id, status="failed", detail=f"入库失败: {err[:150]}")
        return
    if book_id is None:
        ts.update_task(task_id, status="failed", detail="入库成功但无法解析 book_id")
        return

    ts.update_task(task_id, book_id=book_id)

    ext = os.path.splitext(fname)[1].lower().lstrip(".")
    if ext in ("epub",):
        pass  # 直接进元数据
    elif ext in ("mobi", "azw", "azw3", "kfx"):
        ts.update_task(task_id, stage="converting")
        res = fc.process(book_id, filepath, lambda **k: ts.update_task(task_id, **k))
        if res["drm"]:
            ts.update_task(task_id, stage="searching_epub")
            _search_and_add(book_id, fname, task_id)
    elif ext in ("txt", "pdf", "docx", "fb2"):
        ts.update_task(task_id, stage="searching_epub")
        _search_and_add(book_id, fname, task_id)
    else:
        ts.update_task(task_id, status="success", detail=f"已入库({ext})")

    # 元数据补全
    ts.update_task(task_id, stage="enriching")
    me.enrich(book_id, lambda **k: ts.update_task(task_id, **k))

    # 去重（同名不同书）
    ts.update_task(task_id, stage="deduping")
    dd.dedupe_book_group([book_id])

    ts.update_task(task_id, stage="done", status="success", detail="完成")

def _search_and_add(book_id, fname, task_id):
    title = _extract_title(fname)
    cands = es.search_epub(title)
    for c in cands:
        tmp = f"/tmp/{book_id}.epub"
        if es.download_epub(c, tmp):
            with CALIBRE_LOCK:
                subprocess.run(["calibredb", "add_format", "--with-library",
                               LIBRARY, str(book_id), tmp], capture_output=True, timeout=120)
            ts.update_task(task_id, detail=f"已下载EPUB: {c.source}")
            # E1：原 TXT/PDF 归档并移出库，保持 Kindle 视图干净
            orig_ext = os.path.splitext(fname)[1].lstrip(".").upper()
            if orig_ext in ("TXT", "PDF", "DOCX", "FB2"):
                fc.remove_format_and_archive(book_id, orig_ext)
            # G2/G4：返回实际命中的 source（如 "annas"/"zlibrary"/"gutendex"），
            # 供 Doc 7 的 AA 感知配额扣减；原 True/False 不足以区分 AA 与 zlib。
            return c.source
    ts.update_task(task_id, detail="未找到EPUB替代源")
    return None

def _extract_title(fname):
    # 去 hash 前缀 "0b7fead8_金庸 白马啸西风" → "白马啸西风"
    name = os.path.splitext(fname)[0]
    if "_" in name[:9]:
        name = name.split("_", 1)[1]
    return name.replace("金庸 ", "").strip()

def _latest_book_id():
    # 已废弃：B3(复审) 改为在 _add_to_library 持锁期间解析 stdout 拿 id，避免并发串号。
    # 保留仅作后备/调试用。
    import sqlite3
    db = os.path.join(LIBRARY, "metadata.db")
    with sqlite3.connect(db) as c:
        return c.execute("SELECT MAX(id) FROM books").fetchone()[0]

def run_pipeline_by_task(task_id):
    t = ts.get_task(task_id)
    if t and t["source_file"]:
        run_pipeline(t["source_file"], task_id)
```

## 6.3 server.py 接入

`do_POST` 的 `/api/upload` 处理改为：
```python
def _handle_upload(self):
    # 解析 multipart（现有逻辑）
    ... 
    for filename, data in files:
        safe = f"{uuid.uuid4().hex[:8]}_{filename}"
        fp = os.path.join(STAGING, safe)
        open(fp, "wb").write(data)
        tid = ts.create_task(filename, source_file=fp)
        threading.Thread(target=run_pipeline, args=(fp, tid), daemon=True).start()
    self._send_json(200, {"ok": True})
```

## 6.4 tasks_page.html（仪表盘）

轮询 `/api/tasks` 每 5s，渲染表格：
- 列：ID | 标题 | 阶段 | 状态 | 详情 | 操作
- 状态着色：running=蓝, success=绿, failed=红, pending=灰
- 操作：`重试`(tasks/{id}/retry)
- 顶部：`[全库扫描]` → POST `/api/scan`；展示 counts 摘要

风格与 upload_page.html 一致（CSS 复用）。

## 6.5 验证

```bash
# 重启服务
systemctl restart calibre-async-upload
# 上传一本 TXT
curl -b cookie -F "files=@test.txt" http://localhost:8086/api/upload
# 观察 tasks 页：阶段推进 uploaded→adding→searching_epub→enriching→done
```

## 6.6 边界

- 串行化 calibredb（CALIBRE_LOCK），避免锁冲突
- 每个阶段写 tasks.db，前端实时可见
- 失败不阻断：进入 done 但 status=failed，可重试
- **E1**：TXT/PDF 搜到 EPUB 后原格式移出库并归档（见 `_search_and_add`）
- **E3**：格式优先级由环境变量 `PREFERRED_FORMAT`（默认 EPUB）控制；需在
  `calibre-async-upload.service` 的 `[Service]` 段加 `Environment=PREFERRED_FORMAT=EPUB`
- **G3 频控接线**：`_search_and_add` 只调用 `es.search_epub` / `es.download_epub`，
  每源最小间隔节流（Doc 10 §10.5）由 Doc 4 §4.10 的 `rate_limit()` 在各 `search_*` 内部落实，
  编排层无需额外 sleep；上传主路径「一本一搜」天然不批量（Doc 10 §10.5）。
- **G2 下载分发**：`download_epub` 已能按 `cand.source` 分发到 `download_annas`（Doc 4 §4.2 修订），
  故 `search_epub` 返回的 `annas` 候选可被本流水线正常下载，无需改 `_search_and_add` 签名。
