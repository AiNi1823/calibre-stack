# Design Doc 7: Full Library Scan (Phase 3)

> 前置：Phase 2 完成
> 产出：server.py `/api/scan` 端点 + scan 逻辑
> 目标：一次性处理存量 82 本书

---

## 7.1 扫描逻辑

识别需处理的书：
1. 仅有 TXT/PDF/DOCX 格式（无 EPUB）→ 搜替代 EPUB
2. 有 MOBI/AZW/AZW3 但无 EPUB → 尝试转换
3. 缺元数据（ISBN/简介/封面）→ 补全
4. 同名重复 → 去重

## 7.2 代码

```python
# 在 post_process.py 中追加
import sys, sqlite3
sys.path.insert(0, "/opt/calibre-stack/metadata-tool")
from src.db import CalibreDB as _MDB
_mdb = _MDB(os.path.join(LIBRARY, "metadata.db"))   # B5 修复：需传 metadata.db 路径

def scan_library(task_update=None):
    c = sqlite3.connect(LIBRARY); c.row_factory = sqlite3.Row
    books = c.execute("""SELECT b.id, b.title,
        GROUP_CONCAT(d.format) fmts
        FROM books b LEFT JOIN data d ON b.id=d.book
        GROUP BY b.id""").fetchall()
    c.close()

    plan = []
    for b in books:
        fmts = (b["fmts"] or "").split(",")
        fmts = [f.upper() for f in fmts]
        needs_epub = "EPUB" not in fmts
        # B5 修复：get_missing_fields 需完整记录（isbn/has_cover 等），
        # dict(b) 仅含 id/title/fmts，会误判每本都缺 isbn+cover。改用 get_book_by_id。
        needs_meta = bool(_mdb.get_missing_fields(_mdb.get_book_by_id(b["id"])))   # B4：复用 metadata-tool
        if needs_epub or needs_meta:
            plan.append((b["id"], b["title"], needs_epub, needs_meta, fmts))

    total = len(plan)
    remaining_zlib = es.zlib_remaining()      # E2：今日剩余配额（仅 zlib 自身）
    for i, (bid, title, ne, nm, fmts) in enumerate(plan, 1):
        tid = ts.create_task(f"[扫描] {title}")
        ts.update_task(tid, book_id=bid, stage="scan", status="running",
                       detail=f"{i}/{total}")
        if ne:
            if any(f in fmts for f in ("MOBI","AZW","AZW3")):
                fc.process(bid, _book_file(bid), lambda **k: ts.update_task(tid,**k))
            else:
                # G4（AA 感知，本轮修订）：先判断该书是否会落到 zlib 配额。
                # 免费四源无果 且 AA 不可用/未配 key → 才需 zlib 日配额；
                # AA 可用时视为由 AA 满足（Doc 4 §4.8 顺序：AA 在 zlib 之前），不计入 zlib needed。
                if remaining_zlib <= 0 and _needs_zlib_quota(title):
                    ts.update_task(tid, status="pending",
                        detail=f"等待 zlib 配额（ETA {es.zlib_eta(_count_zlib_pending()+1)} 天）")
                    continue
                used_src = _search_and_add(bid, title, tid)
                # 仅当真正由 zlibrary 命中时才扣减 zlib 配额；AA/免费源命中不扣
                if used_src == "zlibrary":
                    remaining_zlib -= 1
        if nm:
            me.enrich(bid, lambda **k: ts.update_task(tid, **k))
        # B7 修复：原 per-book dedupe_book_group([bid]) 对单本书永远无操作，
        # 跨书「同名重复」去重从未触发。改为循环结束后统一跑一次全库去重。
        ts.update_task(tid, stage="done", status="success")
    # 全库同名去重（需在全部书 enrich 之后，避免误合并未补全元数据的书）
    dtid = ts.create_task("[扫描] 全库去重", stage="deduping", status="running")
    removed = dd.dedupe_all(lambda **k: ts.update_task(dtid, **k))
    ts.update_task(dtid, stage="done", status="success",
                   detail=f"移除非优副本 {removed} 本")
    return total

def _aa_available():
    """Anna's 是否可用：设计选定 RapidAPI 形态，仅检查 ANNAS_RAPIDAPI_KEY（见 Doc 10 §10.3）。
    用户当前无账号 → 返回 False，非 PD 书走 zlib 兜底（若 zlib 也未配则无自动来源）。"""
    import os
    return bool(os.environ.get("ANNAS_RAPIDAPI_KEY"))

def _needs_zlib_quota(title):
    """G4（AA 感知）：免费四源无果 且 AA 不可用/未配 → 才需 zlib 配额。
    AA 可用时非 PD 书优先由 AA 满足（Doc 4 §4.8 顺序），不计入 zlib needed。
    注：免费四源命中即 False；免费全 miss 但 AA 可用亦 False（交由 search_epub 走 AA）。"""
    free = (es.search_standard_ebooks(title) or es.search_wikisource(title)
            or es.search_gutendex(title) or es.search_ia(title))
    if free:
        return False
    return not _aa_available()

def _used_zlib():
    return es.zlib_remaining() < es._zlib_quota()["daily_limit"]

def _count_zlib_pending():
    return len(ts.list_tasks(status="pending"))

def _book_file(book_id):
    c = sqlite3.connect(LIBRARY); c.row_factory = sqlite3.Row
    row = c.execute("SELECT path FROM books WHERE id=?",(book_id,)).fetchone()
    c.close()
    base = os.path.dirname(LIBRARY)
    for f in os.listdir(os.path.join(base, row["path"])):
        if f.lower().endswith((".mobi",".azw",".azw3",".txt",".pdf")):
            return os.path.join(base, row["path"], f)
    return None
```

`server.py` 的 `/api/scan`：
```python
def _handle_scan(self):
    threading.Thread(target=scan_library, daemon=True).start()
    self._send_json(202, {"ok": True, "msg": "扫描已启动"})
```

## 7.3 z-library 配额保护（E2 修订：AA 优先，zlib 仅真兜底）

- 金庸 14 本 TXT 免费源(Gutendex/IA/Standard Ebooks/Wikisource)均无 → 属非 PD，原只能走 zlib 的 10/天（约 2 天）。
- **G4 提速**：引入 Anna's Archive 后，`search_epub`（Doc 4 §4.8）把 AA 排在 zlib **之前**；
  金庸类非 PD 书优先由 AA 满足（无 10/日硬上限），**仅 AA 也缺时才烧 zlib 配额**。
- 扫描逻辑：`_needs_zlib_quota()` 先试免费四源；免费全 miss 且 `AA 不可用` 才计为需 zlib。
  **配额扣减以实际命中为准**：`_search_and_add` 返回 `zlibrary` 才 `remaining_zlib -= 1`，
  AA/免费源命中不扣 zlib（消除「非 PD 必烧 zlib」的误扣）。
- 当日 zlib 配额耗尽后，剩余真需 zlib 的书标记为 `pending` + 「ETA N 天」（N 基于 AA 感知后的 `needed`），不阻塞其余书。
- **自动跨天**：用 systemd timer 每日跑一次 `scan_library`（见 §7.6），逐日消耗 zlib 配额直至清空。
- /tasks 页读取 `es.zlib_eta()` 展示「今日剩余 + 预计还需 N 天」（入参 `needed` 已为 AA 感知值，见 Doc 4 §4.6 E2）。
- **G3 频控**：扫描循环本身不 sleep，但每本书的外部检索经 `search_epub` 内 `rate_limit()` 自动节流（Doc 4 §4.10 / Doc 10 §10.5），各源不被高频打。

## 7.4 验证

```bash
curl -b cookie -X POST http://localhost:8086/api/scan
# 观察 /tasks 页面：82 本书逐一创建任务；金庸书部分标记 ETA
```

## 7.5 边界

- 扫描为后台线程，不阻塞响应
- 每本书独立 task，可重试单本
- 大库（82本）预计：免费源书秒级；非 PD 书优先走 AA（无 10/日硬上限，金庸 14 本可显著快于原 2 天），仅 AA 也缺的书按 zlib 10/天 铺开
- 已处理的书跳过（needs_epub/needs_meta 判断）
- **G4**：`_needs_zlib_quota` 依赖免费四源 + AA 可用性的预探测；若 AA 已配 key，金庸类书不进 zlib 配额池，ETA 归零

## 7.6 每日定时续扫（E2 自动跨天）

```ini
# /etc/systemd/system/calibre-scan.timer
[Unit]
Description=Daily Calibre library scan (drains zlib quota)

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```
```ini
# /etc/systemd/system/calibre-scan.service
[Unit]
Description=Calibre Scan

[Service]
Type=oneshot
User=calibreweb
ExecStart=/usr/bin/curl -s -b /var/lib/calibreweb/cookie http://127.0.0.1:8086/api/scan
```
> 注：scan 本身幂等（已处理书跳过），每日跑安全。需先为定时任务准备可用的登录 cookie。
