#!/usr/bin/env python3
"""异步上传服务：接收文件 → 立即返回 → 后台 calibredb add"""

import os
import sys
import time
import json
import uuid
import shutil
import logging
import subprocess
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger('async-upload')

LIBRARY = os.environ.get('CALIBRE_DBPATH', '/opt/calibre-library/Calibre Library')
STAGING = '/opt/calibre-web/upload_staging'
PROCESSED = '/opt/calibre-web/upload_processed'
PORT = int(os.environ.get('ASYNC_UPLOAD_PORT', '8086'))

os.makedirs(STAGING, exist_ok=True)
os.makedirs(PROCESSED, exist_ok=True)


def process_book(filepath):
    fname = os.path.basename(filepath)
    log.info("Processing: %s", fname)
    try:
        result = subprocess.run(
            ['calibredb', 'add', '--with-library', LIBRARY,
             '--automerge', 'overwrite', filepath],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            log.info("Added: %s", fname)
            dest = os.path.join(PROCESSED, fname)
            shutil.move(filepath, dest)
        else:
            log.error("Failed: %s → %s", fname, result.stderr.strip())
    except subprocess.TimeoutExpired:
        log.error("Timeout: %s", fname)
    except Exception as e:
        log.error("Error %s: %s", fname, e)


class UploadHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log.info(fmt, *args)

    def _send_json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        if self.path == '/health':
            self._send_json(200, {'status': 'ok'})
        else:
            self._send_json(404, {'error': 'not found'})

    def do_POST(self):
        if self.path != '/upload':
            self._send_json(404, {'error': 'not found'})
            return

        content_type = self.headers.get('Content-Type', '')
        if 'multipart/form-data' not in content_type:
            self._send_json(400, {'error': 'expected multipart/form-data'})
            return

        boundary = None
        for part in content_type.split(';'):
            part = part.strip()
            if part.startswith('boundary='):
                boundary = part.split('=', 1)[1].strip('"')
        if not boundary:
            self._send_json(400, {'error': 'no boundary'})
            return

        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 200 * 1024 * 1024:
            self._send_json(413, {'error': 'file too large'})
            return

        body = self.rfile.read(content_length)

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
            file_data = part[header_end + 4:]
            if file_data.endswith(b'\r\n'):
                file_data = file_data[:-2]
            if file_data.endswith(b'--'):
                file_data = file_data[:-2]

            for line in header.split('\r\n'):
                if 'filename="' in line:
                    start = line.find('filename="') + 10
                    end = line.find('"', start)
                    if end > start:
                        filename = line[start:end]
                        files.append((filename, file_data))
                        break

        if not files:
            self._send_json(400, {'error': 'no files'})
            return

        saved = []
        for filename, data in files:
            safe_name = f"{uuid.uuid4().hex[:8]}_{filename}"
            filepath = os.path.join(STAGING, safe_name)
            with open(filepath, 'wb') as f:
                f.write(data)
            saved.append(filename)
            threading.Thread(target=process_book, args=(filepath,), daemon=True).start()

        self._send_json(200, {
            'status': 'accepted',
            'files': saved,
            'message': f'{len(saved)} file(s) accepted, processing in background'
        })
        log.info("Accepted: %s", ', '.join(saved))


if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', PORT), UploadHandler)
    log.info("Async upload server on 127.0.0.1:%d", PORT)
    server.serve_forever()
