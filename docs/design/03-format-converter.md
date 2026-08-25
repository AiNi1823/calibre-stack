# Design Doc 3: Format Converter (Phase 2)

> 前置：Phase 1
> 产出：format_converter.py
> 依赖：ebook-convert (calibre 7.6), calibredb

---

## 3.1 职责

- 将非 EPUB 格式（MOBI/AZW/AZW3/TXT/PDF）转为 EPUB
- 检测 DRM 保护文件（KFX "CR! ..."，或 convert 报错 "DRM"）
- 转换成功后 `calibredb add_format` 将 EPUB 加入同名书；原文件归档 `_archive/`
- 转换失败（DRM）则标记，交由 epub_sources 搜替代源

## 3.2 代码

```python
# /opt/calibre-stack/async-upload/format_converter.py
import os, subprocess, shutil, logging
log = logging.getLogger("format_converter")

LIBRARY = os.environ.get("CALIBRE_DBPATH", "/opt/calibre-library/Calibre Library")
ARCHIVE = "/opt/calibre-library/_archive"
CALIBRE_LOCK = None   # 由 server 注入

DRM_MAGICS = [b"CR!", b"\x00\x00\x00\x0c\x6a\x50\x20\x20\x0d\x0a\x87\x0a"]  # KFX/DRM 标记

def is_drm_file(path):
    with open(path, "rb") as f:
        head = f.read(512)
    for m in DRM_MAGICS:
        if m in head:
            return True
    # AZW3/AZW DRM 通常在文件头 "CRES" 或无法解包
    return False

def convert_to_epub(src_path, workdir="/tmp/calibre_conv"):
    """返回 (ok, epub_path|None, reason)"""
    os.makedirs(workdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(src_path))[0]
    out = os.path.join(workdir, base + ".epub")
    try:
        r = subprocess.run(
            ["ebook-convert", src_path, out,
             "--output-profile", "kindle"],
            capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            err = r.stderr.lower()
            if "drm" in err or "cannot read" in err:
                return False, None, "drm"
            return False, None, r.stderr[:200]
        if os.path.exists(out) and os.path.getsize(out) > 1000:
            return True, out, ""
        return False, None, "empty output"
    except subprocess.TimeoutExpired:
        return False, None, "timeout"

def add_format(book_id, epub_path):
    """把 EPUB 加进已有书；返回是否成功"""
    with CALIBRE_LOCK:
        r = subprocess.run(
            ["calibredb", "add_format", "--with-library", LIBRARY,
             str(book_id), epub_path],
            capture_output=True, text=True, timeout=120)
    return r.returncode == 0

def archive_original(src_path, book_title):
    os.makedirs(ARCHIVE, exist_ok=True)
    dest = os.path.join(ARCHIVE, os.path.basename(src_path))
    shutil.move(src_path, dest)
    return dest

def remove_format_and_archive(book_id, fmt):
    """E1：把某书指定格式从库移除并归档原文件（用于 TXT/PDF 找到 EPUB 后的清理）"""
    from contextlib import contextmanager
    base = os.path.dirname(LIBRARY)
    with CALIBRE_LOCK:
        # 取该格式文件所在路径
        r = subprocess.run(
            ["calibredb", "list", "--with-library", LIBRARY, "--fields", "path,formats",
             "--search", f"id:{book_id}"], capture_output=True, text=True, timeout=60)
        # 定位文件
        book_dir = None
        for line in r.stdout.splitlines():
            if str(book_id) in line:
                # 行形如: id  path   formats
                parts = line.split(None, 2)
                if len(parts) >= 2:
                    book_dir = os.path.join(base, parts[1])
        if book_dir and os.path.isdir(book_dir):
            for f in os.listdir(book_dir):
                if f.upper().endswith("." + fmt.upper()):
                    archive_original(os.path.join(book_dir, f), "")
        # 从库移除该格式
        subprocess.run(
            ["calibredb", "remove_format", "--with-library", LIBRARY,
             str(book_id), fmt.upper()], capture_output=True, text=True, timeout=60)

def process(book_id, src_path, task_update=None):
    """完整处理：DRM 检测 → 转换 → 入库 → 归档
    返回 dict: {converted, drm, epub, error}"""
    res = {"converted": False, "drm": False, "epub": None, "error": None}
    if is_drm_file(src_path):
        res["drm"] = True
        res["error"] = "DRM protected"
        if task_update: task_update(detail="DRM 保护，需搜替代源")
        return res
    ok, epub, why = convert_to_epub(src_path)
    if not ok:
        res["error"] = why
        if task_update: task_update(detail=f"转换失败: {why}")
        return res
    if add_format(book_id, epub):
        res["converted"] = True
        res["epub"] = epub
        archive_original(src_path, "")
        if task_update: task_update(detail="已转换并归档原文件")
    else:
        res["error"] = "add_format failed"
    return res
```

## 3.3 调用约定

`post_process.py` 在收到 MOBI/AZW/AZW3 入库后调用 `process()`：
- DRM=True → 进入 `searching_epub` 阶段
- 成功 → 进入 `enriching`

TXT 文件不在此转换（直接进 `searching_epub`，见 Doc 4）。

## 3.4 验证

```bash
# 取一本测试的 MOBI
python3 -c "
import format_converter as fc, task_store as ts
fc.CALIBRE_LOCK = __import__('threading').Lock()
# 用真实文件测试（dry）
print('DRM check on test.mobi:', fc.is_drm_file('test.mobi'))
"
# 真实转换
ebook-convert book.mobi /tmp/out.epub && echo OK
```

## 3.5 边界

- 转换超时 180s（大 PDF 可能更久，可上调）
- 转换产物落临时目录，成功后才 add_format
- 归档不删原文件（决策：保留）
- KFX 几乎都 DRM，直接判 DRM 跳过
