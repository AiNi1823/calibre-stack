# 部署指南

## 1. 环境要求

- Linux（Debian/Ubuntu），2 核 / 1.6GB 内存 VPS（已实测可运行）
- Python 3.12+
- Calibre 7.x（提供 `calibredb`）
- nginx + cloudflared（Cloudflare Tunnel）
- 出站代理（可选，用于豆瓣抓取）：本机 mihomo `127.0.0.1:7890`

## 2. 组件部署

### 2.1 Calibre-Web（已有，端口 8083）

```bash
systemctl enable --now calibre-web
```

服务单元：`deploy/calibre-web.service` → `/etc/systemd/system/`

### 2.2 异步上传服务（端口 8086）

```bash
# 安装单元文件并启动
cp deploy/calibre-async-upload.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now calibre-async-upload
```

服务单元：`deploy/calibre-async-upload.service`。注意 `Environment` 必须带引号（见开发说明 §4.1）。

### 2.3 nginx 反向代理（端口 8084）

```bash
cp deploy/nginx-calibre-web.conf /etc/nginx/sites-available/calibre-web
ln -sf /etc/nginx/sites-available/calibre-web /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

配置要点：
- 所有 upstream 均指向 `127.0.0.1`，对外只暴露 8084（供 Cloudflare Tunnel 使用）。
- 静态资源/封面走 `proxy_cache` 缓存。
- `/api/upload` 转发到 async-upload（8086），关闭请求缓冲，超时 60s。
- `client_max_body_size 100M`，如需更大文件同步调大 `server.py` 内的 200MB 检查。

### 2.4 统一上传入口

Calibre-Web 导航栏 Upload 已改为链接到 `/async-upload`（即异步上传页），确保新增书籍只有一个入口。**修改为模板文件**：`venv/lib/python3.12/site-packages/calibreweb/cps/templates/layout.html`（Calibre-Web 升级会覆盖，升级后需重新打补丁）。

## 3. 元数据补全工具

```bash
cd /opt/calibre-stack/metadata-tool
pip install -r requirements.txt          # requests, pyyaml
python3 main.py --check                   # 干运行，看缺什么
python3 main.py --report                  # 全量报表
python3 main.py                           # 自动补全
```

配置文件 `config.yaml` 中 `network.proxy` 需与本机代理地址一致；如无代理可置空或指向其他出口。

## 4. 验证

```bash
# 服务状态
systemctl is-active calibre-web calibre-async-upload nginx cloudflared
# 健康检查
curl http://127.0.0.1:8086/health        # {"status":"ok"}
# 上传链路（应毫秒级返回 accepted）
curl -X POST -F "files=@/tmp/book.epub" http://127.0.0.1:8084/api/upload
# 后台处理日志
journalctl -u calibre-async-upload -f     # 观察 "Added:" 字样
```

## 5. 运维

### 5.1 查看上传处理结果

- 成功：文件从 `async-upload/upload_staging/` 移入 `async-upload/upload_processed/`。
- 失败：文件留在 `upload_staging/`，日志输出 `Failed:` 与原因。

### 5.2 常见故障

| 现象 | 原因 | 处理 |
|------|------|------|
| 上传后书不出现 | `CALIBRE_DBPATH` 被截断，写入错误库 | 检查 `cat /proc/<pid>/environ`，单元文件加引号 |
| 上传页面打不开 | async-upload 服务未运行 | `systemctl status calibre-async-upload` |
| calibre-web 反复被杀 | OOM | `free -h`，关闭多余进程或分批上传 |
| 上传大文件超时 | 走了同步入口 | 确认使用 `/async-upload`，勿用原生 Upload |

### 5.3 日志

- Calibre-Web：`journalctl -u calibre-web -f`
- 异步上传：`journalctl -u calibre-async-upload -f`
- nginx：`/var/log/nginx/error.log`
