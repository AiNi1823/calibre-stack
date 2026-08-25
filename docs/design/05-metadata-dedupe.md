# Design Doc 5: Metadata Enricher + Deduplicator (Phase 2)

> 前置：Phase 1；复用 metadata-tool/src/*
> 产出：metadata_enricher.py, deduplicator.py

---

## 5.1 Metadata Enricher

复用现有 metadata-tool 的 `DoubanAPI`/`OpenLibraryAPI`/`CoverDownloader`/`CalibreDB`。
增量补全：仅填缺字段（与 main.py 逻辑一致）。

```python
# /opt/calibre-stack/async-upload/metadata_enricher.py
import os, sys, logging
sys.path.insert(0, "/opt/calibre-stack/metadata-tool")
from src.db import CalibreDB
from src.douban import DoubanAPI
from src.openlibrary import OpenLibraryAPI
from src.covers import CoverDownloader
from src.utils import parse_pubdate
import epub_sources as es   # Doc 4 §4.8：enrich_google（Google Books 元数据，第 3 源）

log = logging.getLogger("metadata_enricher")

LIBRARY = os.environ.get("CALIBRE_DBPATH", "/opt/calibre-library/Calibre Library")
PROXY = os.environ.get("HTTP_PROXY", "http://127.0.0.1:7890")

# B5 修复：CalibreDB 期望 metadata.db 文件路径（见 metadata-tool/config.yaml db_path），
# 传目录会令 sqlite3.connect 报 "unable to open database file"。
_db = CalibreDB(os.path.join(LIBRARY, "metadata.db"))
_douban = DoubanAPI(proxy=PROXY, timeout=15, delay=1.5)
_ol = OpenLibraryAPI(proxy=PROXY, timeout=15, delay=1.5)
_cover = CoverDownloader(proxy=PROXY, timeout=20, min_size=2000)

# 元数据三源优先级（与 Doc 10 §10.2 metadata_order 一致：douban → google_books → open_library）
# enrich_google 失败/未配 key 时返回 None，降级到 OpenLibrary（见 Doc 4 §4.8）。
def _find_meta(title, author=""):
    return (_douban.find_book(title, author)
            or es.enrich_google(title, author)
            or _ol.find_book(title, author))

def enrich(book_id, task_update=None):
    """补全缺失元数据；返回更新字段数"""
    book = _db.get_book_by_id(book_id)
    if not book: return 0
    missing = _db.get_missing_fields(book)
    if not missing:
        if task_update: task_update(detail="元数据已完整")
        return 0
    title = book["title"]; author = (book.get("authors") or "").split(",")[0]
    if task_update: task_update(detail=f"缺失: {','.join(missing)}")

    src = _find_meta(title, author)
    if not src:
        if task_update: task_update(detail="未找到元数据来源")
        return 0

    updates = {}
    if "isbn" in missing and src.get("isbn"):
        updates["isbn"] = src["isbn"][0] if isinstance(src["isbn"], list) else src["isbn"]
    # B5 修复：OpenLibrary 的 find_book 返回 first_publish_year（非 pubdate），
    # 原 `src.get("pubdate")` 对 OL 源永远为空 → pubdate 不被补全。二者都接受。
    # Google Books 亦返回 publishedDate（见 Doc 4 §4.8 enrich_google），一并接受。
    _pub = (src.get("pubdate") or src.get("first_publish_year")
            or src.get("publishedDate"))
    if "pubdate" in missing and _pub:
        pd = parse_pubdate(str(_pub))
        if pd: updates["pubdate"] = pd
    if "description" in missing and src.get("description"):
        _db.add_description(book_id, src["description"])
    # B5 修复：get_missing_fields 从不返回 "tags"，原 `if "tags" in missing` 为死分支。
    # tags 为可叠加字段，只要源有就补（不受 missing 限制）。
    if src.get("tags"):
        for t in src["tags"][:5]:
            _db.add_tag(book_id, t)
    if "cover" in missing:
        path = os.path.join(_db.get_book_path(book), "cover.jpg")
        if not os.path.exists(path):
            ok = False
            if src.get("douban_id"):
                ok, _ = _cover.download_douban_cover(src["douban_id"], path)
            # Google Books 封面走 imageLinks.thumbnail，统一归一为 cover_url 复用 OL 下载器
            _cover_url = src.get("cover_url") or src.get("image_url")
            if not ok and _cover_url:
                ok, _ = _cover.download_openlibrary_cover(_cover_url, path)
            if ok: updates["has_cover"] = 1
    if updates:
        _db.update_book(book_id, updates)
    if task_update: task_update(detail=f"已更新 {len(updates)} 字段")
    return len(updates)
```

> **G1 整合（Google Books 作为第 3 元数据源，本轮新增）**：
> - 原 `enrich()` 仅链 `Douban → OpenLibrary`，缺 Google Books（Doc 4 §4.7.2 强烈推荐、Doc 10 §10.2 `metadata_order` 列第 2）。现改为 `_find_meta()` = `Douban → enrich_google → OpenLibrary`，与 Doc 10 顺序一致。
> - `enrich_google`（Doc 4 §4.8）返回 `isbn / publishedDate / description / imageLinks.thumbnail`，本模块已将其 `publishedDate→pubdate`、`imageLinks.thumbnail→cover_url` 归一进通用 `src` 结构，复用既有 `parse_pubdate` 与 `download_openlibrary_cover` 路径。
> - 未配 `GOOGLE_BOOKS_API_KEY` 时 `enrich_google` 返回 `None`（Doc 4 §4.8 守卫），无缝降级到 OpenLibrary，不阻断流水线。
> - 频控：`enrich_google` 内部调用须遵守 Doc 10 §10.5 的 `google_books: 1` 最小间隔（由 Doc 4 §4.10 `rate_limit` 统一节流）。

## 5.2 Deduplicator

同名书（归一化标题后相同）→ 保留最优格式副本（EPUB > AZW3 > MOBI > 其他），
其余归档 `_archive/` 并从库移除。

```python
# /opt/calibre-stack/async-upload/deduplicator.py
import os, re, sqlite3, subprocess, logging, shutil
log = logging.getLogger("dedupe")

LIBRARY = os.environ.get("CALIBRE_DBPATH", "/opt/calibre-library/Calibre Library")
ARCHIVE = "/opt/calibre-library/_archive"
CALIBRE_LOCK = None

# E3：格式优先级可配置，默认 EPUB 优先（Send-to-Kindle 兼容、跨设备通用）
# 通过环境变量 PREFERRED_FORMAT 可切到 AZW3（老款 Kindle 生态更稳）
_PREF = os.environ.get("PREFERRED_FORMAT", "EPUB").upper()
_BASE_RANK = {"EPUB": 0, "AZW3": 1, "MOBI": 2, "AZW": 3, "KFX": 4, "PDF": 5, "TXT": 6}
def _rank(fmt):
    fmt = fmt.upper()
    if fmt == _PREF:
        return -1          # 用户偏好永远最优先
    return _BASE_RANK.get(fmt, 9)

def _norm(title):
    t = re.sub(r"[（(].*?[)）]", "", title)
    t = re.sub(r"[\s_\-—–].*$", "", t)
    return t.strip().lower()

def _connect():
    # B5 修复：LIBRARY 是目录，sqlite3 直连需拼 metadata.db（与 Doc 6/7 保持一致）
    c = sqlite3.connect(os.path.join(LIBRARY, "metadata.db")); c.row_factory = sqlite3.Row; return c

def find_duplicates():
    """返回 {norm_title: [book_id,...]} 有多本的"""
    c = _connect()
    rows = c.execute("""SELECT id,title FROM books""").fetchall()
    c.close()
    groups = {}
    for r in rows:
        groups.setdefault(_norm(r["title"]), []).append(r["id"])
    return {k: v for k, v in groups.items() if len(v) > 1}

def dedupe_book_group(book_ids):
    """保留最优格式，其余归档移除"""
    c = _connect()
    best, rest = None, []
    for bid in book_ids:
        fmts = [r["format"] for r in c.execute(
            "SELECT format FROM data WHERE book=?", (bid,)).fetchall()]
        rank = min((_rank(f) for f in fmts), default=9)
        if best is None or rank < best[1]:
            if best: rest.append(best[0])
            best = (bid, rank)
        else:
            rest.append(bid)
    c.close()
    for bid in rest:
        _archive_and_remove(bid)
    return best[0] if best else None

def _archive_and_remove(book_id):
    # 移动文件到 _archive
    c = _connect()
    path = c.execute("SELECT path FROM books WHERE id=?", (book_id,)).fetchone()["path"]
    c.close()
    src = os.path.join(os.path.dirname(LIBRARY), path)
    if os.path.exists(src):
        os.makedirs(ARCHIVE, exist_ok=True)
        shutil.move(src, os.path.join(ARCHIVE, os.path.basename(path)))
    with CALIBRE_LOCK:
        subprocess.run(["calibredb", "remove", "--with-library", LIBRARY,
                       str(book_id)], capture_output=True, timeout=60)

def dedupe_all(task_update=None):
    groups = find_duplicates()
    n = 0
    for norm, ids in groups.items():
        keep = dedupe_book_group(ids)
        n += len(ids) - 1
        if task_update: task_update(detail=f"去重 {norm}: 保留 #{keep}")
    return n
```

## 5.3 验证

```bash
# 元数据
python3 -c "import metadata_enricher as m; print(m.enrich(70))"
# 去重
python3 -c "import deduplicator as d; d.CALIBRE_LOCK=__import__('threading').Lock(); print(d.find_duplicates())"
```

## 5.4 边界

- 仅移除多余副本，保留最优格式（**E3**：默认 EPUB 优先，可由 `PREFERRED_FORMAT=AZW3` 切换）
- 移除前先归档文件，可恢复
- 元数据补全尊重缺字段，不覆盖已有
- **E1 配合**：当流水线给 TXT/PDF 书搜到 EPUB 后，由 `format_converter.remove_format_and_archive`（见 Doc 3）把原 TXT/PDF 移出库并归档；本模块只处理"同名不同书"的去重，不触碰同书多格式
