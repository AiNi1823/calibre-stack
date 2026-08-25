#!/usr/bin/env python3
"""异步上传服务（8086）：接收文件 → 建任务 → 后台加入 Calibre 书库（best-effort EPUB）。

路由：
  POST /api/upload              原生 Calibre-Web 上传按钮 & 自定义页都打这里
  POST /api/scan                （占位）触发全库扫描
  POST /api/tasks/{id}/retry    重试某任务
  POST /api/books/{id}/{action} （占位）对书籍的手动操作
  GET  /api/tasks               任务列表 JSON
  GET  /api/tasks/{id}          单任务 JSON
  GET  /tasks                   任务看板页面
  GET  /health                  健康检查
"""

import os
import re
import sys
import time
import json
import uuid
import shutil
import logging
import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import task_store as ts

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger('async-upload')

LIBRARY = os.environ.get('CALIBRE_DBPATH', '/opt/calibre-library/Calibre Library')
STAGING = '/opt/calibre-web/upload_staging'
PROCESSED = '/opt/calibre-web/upload_processed'
PORT = int(os.environ.get('ASYNC_UPLOAD_PORT', '8086'))
MAX_SIZE = 200 * 1024 * 1024  # 200MB，与 nginx client_max_body_size 对齐

os.makedirs(STAGING, exist_ok=True)
os.makedirs(PROCESSED, exist_ok=True)

# 串行化 calibredb，避免与 calibre-web 及并发线程争抢数据库锁
CALIBRE_LOCK = threading.Lock()

# 直接以 EPUB 入库的格式（无需转换）
EPUB_LIKE = {'.epub', '.kepub'}


# ───────────────────────── 管线 ─────────────────────────
def _run(cmd, timeout=600):
    """在 CALIBRE_LOCK 保护下执行 calibre 命令，返回 (rc, out, err)。"""
    with CALIBRE_LOCK:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return r.returncode, r.stdout, r.stderr
        except subprocess.TimeoutExpired as e:
            return 124, '', 'timeout: ' + ' '.join(cmd)
        except Exception as e:  # noqa
            return 1, '', str(e)


def _parse_added_book_id(out):
    """calibredb add 输出形如 'Added book ids: 123'。"""
    m = re.search(r'Added book ids?:\s*(\d+)', out)
    if m:
        return int(m.group(1))
    m = re.search(r'\b(\d+)\b', out)
    return int(m.group(1)) if m else None


def _enrich_best_effort(book_id, title):
    """补充元数据/封面（best-effort、静默、凭据门控）。

    当前未配置任何来源凭据（z-library / Anna's 均未提供），
    故此处为空操作占位；接入凭据后可在此实现来源猎取与元数据补全，
    失败时静默跳过，绝不影响入库结果。
    """
    return


def run_pipeline(task_id, filepath, original_filename):
    fname = os.path.basename(filepath)
    ts.update_task(task_id, status='running', stage='adding',
                   detail='正在加入书库…')
    log.info("[task %d] adding %s", task_id, fname)

    ext = os.path.splitext(original_filename)[1].lower()
    rc, out, err = _run([
        'calibredb', 'add', '--with-library', LIBRARY,
        '--automerge', 'overwrite', filepath
    ])

    if rc != 0:
        ts.update_task(task_id, status='failed', stage='adding',
                       detail='加入书库失败：' + (err.strip() or 'unknown error'))
        log.error("[task %d] add failed: %s", task_id, err.strip())
        return

    book_id = _parse_added_book_id(out)
    if book_id is None:
        ts.update_task(task_id, status='failed', stage='adding',
                       detail='加入书库成功但无法解析书籍 ID')
        log.error("[task %d] added but no book id parsed", task_id)
        return
    ts.update_task(task_id, book_id=book_id)

    # best-effort EPUB：非 EPUB 格式尝试转成 EPUB，便于 Kindle 投递
    if ext not in EPUB_LIKE:
        ts.update_task(task_id, stage='converting',
                       detail='正在转换为 EPUB（best-effort）…')
        epub_path = os.path.join(STAGING, fname.rsplit('.', 1)[0] + '.epub')
        rc2, _, err2 = _run(['ebook-convert', filepath, epub_path], timeout=600)
        if rc2 == 0 and os.path.exists(epub_path):
            _run([
                'calibredb', 'add', '--with-library', LIBRARY,
                '--automerge', 'overwrite', epub_path
            ])
            try:
                os.remove(epub_path)
            except OSError:
                pass
            log.info("[task %d] epub added for book %d", task_id, book_id)
        else:
            log.warning("[task %d] epub conversion skipped/failed: %s",
                        task_id, err2.strip())

    # best-effort 元数据补全（当前无凭据 → 空操作）
    ts.update_task(task_id, stage='enriching', detail='补充信息（best-effort）…')
    _enrich_best_effort(book_id, os.path.splitext(original_filename)[0])
    ts.update_task(task_id, stage='enriching',
                   detail='补充信息已跳过（未配置来源）')

    # 归档原始文件
    try:
        dest = os.path.join(PROCESSED, fname)
        if os.path.exists(dest):
            dest = os.path.join(PROCESSED, f"{uuid.uuid4().hex[:6]}_{fname}")
        shutil.move(filepath, dest)
    except OSError as e:
        log.warning("[task %d] cannot archive %s: %s", task_id, fname, e)

    ts.update_task(task_id, status='success', stage='done',
                   detail='已加入书库')
    log.info("[task %d] done → book %d", task_id, book_id)


# ───────────────────────── 请求处理 ─────────────────────────
class UploadHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log.info(fmt, *args)

    # ---- 响应辅助 ----
    def _send_json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        try:
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            log.warning("Client disconnected before response sent")

    def _send_html(self, code, html):
        try:
            self.send_response(code)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(html.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _read_json(self):
        length = int(self.headers.get('Content-Length', 0))
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length))
        except Exception:
            return {}

    # ---- 解析 multipart，返回 [(filename, bytes), ...] ----
    def _parse_multipart(self, boundary, body):
        boundary_bytes = ('--' + boundary).encode()
        parts = body.split(boundary_bytes)
        files = []
        for part in parts:
            if b'filename="' not in part:
                continue
            header_end = part.find(b'\r\n\r\n')
            if header_end == -1:
                continue
            header = part[:header_end].decode('utf-8', errors='replace')
            data = part[header_end + 4:]
            if data.endswith(b'\r\n'):
                data = data[:-2]
            if data.endswith(b'--'):  # 尾部边界标记残留
                data = data[:-2]
            fn = None
            for line in header.split('\r\n'):
                if 'filename="' in line:
                    s = line.find('filename="') + 10
                    e = line.find('"', s)
                    if e > s:
                        fn = line[s:e]
                    break
            if fn:
                files.append((fn, data))
        return files

    # ---- GET ----
    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/health':
            self._send_json(200, {'status': 'ok'})
        elif path == '/tasks':
            try:
                html = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        'tasks_page.html')).read()
            except OSError:
                html = '<h1>tasks page missing</h1>'
            self._send_html(200, html)
        elif path == '/api/tasks':
            self._send_json(200, {
                'tasks': ts.list_tasks(200),
                'counts': ts.count_by_status(),
            })
        elif re.fullmatch(r'/api/tasks/\d+', path):
            tid = int(path.rsplit('/', 1)[1])
            t = ts.get_task(tid)
            if t:
                self._send_json(200, {'task': t})
            else:
                self._send_json(404, {'error': 'task not found'})
        else:
            self._send_json(404, {'error': 'not found'})

    # ---- POST ----
    def do_POST(self):
        path = self.path.split('?')[0]

        if path == '/api/upload':
            return self._handle_upload()
        if path == '/api/scan':
            return self._handle_scan()

        m = re.fullmatch(r'/api/tasks/(\d+)/retry', path)
        if m:
            tid = int(m.group(1))
            self._send_json(200, {'ok': True, 'task_id': tid})
            threading.Thread(target=retry_task, args=(tid,), daemon=True).start()
            return

        m = re.fullmatch(r'/api/books/(\d+)/(\w+)', path)
        if m:
            bid, action = int(m.group(1)), m.group(2)
            self._send_json(202, {'ok': True, 'book_id': bid, 'action': action})
            return

        self._send_json(404, {'error': 'not found'})

    # ---- 上传处理 ----
    def _handle_upload(self):
        content_type = self.headers.get('Content-Type', '')
        if 'multipart/form-data' not in content_type:
            self._send_json(400, {'error': 'expected multipart/form-data',
                                  'location': '/'})
            return
        boundary = None
        for part in content_type.split(';'):
            part = part.strip()
            if part.startswith('boundary='):
                boundary = part.split('=', 1)[1].strip('"')
        if not boundary:
            self._send_json(400, {'error': 'no boundary', 'location': '/'})
            return

        try:
            content_length = int(self.headers.get('Content-Length', 0))
        except ValueError:
            content_length = 0

        if content_length > MAX_SIZE:
            self._send_json(413, {
                'error': '文件超过 200MB 上限',
                'location': '/',
            })
            return

        body = self.rfile.read(content_length) if content_length else b''
        files = self._parse_multipart(boundary, body)
        if not files:
            self._send_json(400, {'error': 'no files', 'location': '/'})
            return

        accepted = []
        for filename, data in files:
            safe = f"{uuid.uuid4().hex[:8]}_{filename}"
            filepath = os.path.join(STAGING, safe)
            with open(filepath, 'wb') as f:
                f.write(data)
            tid = ts.create_task(title=filename, source_file=safe)
            threading.Thread(
                target=run_pipeline, args=(tid, filepath, filename),
                daemon=True).start()
            accepted.append(filename)
            log.info("Accepted task %d: %s", tid, filename)

        # 原生 Calibre-Web 上传按钮靠 response.location 跳转页面；
        # 这里跳到 /tasks，让用户立即看到处理进度。
        self._send_json(200, {
            'location': '/tasks',
            'ok': True,
            'task_id': None,
            'message': '已收到，正在后台加入书库',
            'files': accepted,
        })

    def _handle_scan(self):
        # 触发一次轻量全库扫描（统计缺 EPUB 的书籍），结果写入任务看板
        tid = ts.create_task(title='全库扫描', source_file='(scan)')
        ts.update_task(tid, status='running', stage='scan', detail='扫描中…')
        threading.Thread(target=run_scan, args=(tid,), daemon=True).start()
        self._send_json(200, {'ok': True, 'task_id': tid, 'message': '已触发全库扫描'})


def run_scan(tid):
    """轻量扫描：统计库中缺少 EPUB 格式的书籍（best-effort）。"""
    try:
        rc, out, err = _run([
            'calibredb', 'list', '--with-library', LIBRARY,
            '-f', 'formats', '--for-machine'
        ])
        if rc != 0:
            ts.update_task(tid, status='failed', stage='scan',
                           detail='扫描失败：' + (err.strip() or 'unknown'))
            return
        books = json.loads(out)
        total = len(books)
        no_epub = 0
        for b in books:
            fmts = ' '.join(b.get('formats') or []).upper()
            if 'EPUB' not in fmts:
                no_epub += 1
        ts.update_task(tid, status='success', stage='done',
                       detail=f'扫描完成：共 {total} 本，缺 EPUB {no_epub} 本')
        log.info("[scan %d] total=%d no_epub=%d", tid, total, no_epub)
    except Exception as e:  # noqa
        ts.update_task(tid, status='failed', stage='scan', detail='扫描异常：' + str(e))


def retry_task(tid):
    t = ts.get_task(tid)
    if not t or not t.get('source_file'):
        ts.update_task(tid, status='failed', detail='无法重试：缺少源文件')
        return
    src = os.path.join(STAGING, t['source_file'])
    if not os.path.exists(src):
        # 源文件已归档，从 PROCESSED 找回
        for f in os.listdir(PROCESSED):
            if f.endswith(t['source_file'].split('_', 1)[-1]):
                src = os.path.join(PROCESSED, f)
                break
    if not os.path.exists(src):
        ts.update_task(tid, status='failed', detail='无法重试：源文件已不存在')
        return
    ts.update_task(tid, status='pending', stage='uploaded', detail='')
    run_pipeline(tid, src, t['title'])


if __name__ == '__main__':
    ts.init_db()
    server = HTTPServer(('127.0.0.1', PORT), UploadHandler)
    log.info("Async upload server on 127.0.0.1:%d", PORT)
    server.serve_forever()
