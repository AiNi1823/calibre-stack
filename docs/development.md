# 开发说明

本文档面向维护与扩展 Calibre Stack 的开发者，说明代码结构、核心逻辑与扩展点。

## 1. 目录结构

```
/opt/calibre-stack/
├── README.md
├── docs/
│   ├── requirements.md       # 需求说明
│   ├── development.md        # 开发说明（本文档）
│   └── deployment.md         # 部署指南
├── metadata-tool/            # 元数据补全工具
│   ├── main.py               # CLI 入口
│   ├── config.yaml           # 配置（代理/数据源/字段规则）
│   ├── requirements.txt
│   └── src/
│       ├── __init__.py
│       ├── db.py             # metadata.db 读写
│       ├── douban.py         # 豆瓣读书数据源
│       ├── openlibrary.py    # Open Library 数据源
│       ├── covers.py         # 封面下载与校验
│       └── utils.py          # 日期解析、标题清洗等
├── async-upload/             # 异步上传服务
│   ├── server.py             # HTTP 服务（仅依赖标准库）
│   └── upload_page.html      # 单文件上传页（无构建依赖）
└── deploy/
    ├── nginx-calibre-web.conf
    ├── calibre-web.service
    ├── calibre-async-upload.service
    └── install.sh
```

## 2. 核心设计

### 2.1 异步上传（async-upload/server.py）

**设计目标**：规避 Cloudflare Tunnel 100s HTTP 硬超时。

```
浏览器 POST /api/upload
  → nginx (127.0.0.1:8084, client_max_body_size=100M, proxy_request_buffering off)
  → async-upload (127.0.0.1:8086)
      ├── 解析 multipart → 存暂存目录 → 立即返回 {"status":"accepted"}
      └── 后台线程: calibredb add --with-library <库路径> --automerge overwrite <file>
```

关键点：
- **立即返回**：文件写入 `upload_staging/` 后马上响应，网络侧（Cloudflare）只经历文件传输时间。
- **后台入库**：每个文件一个 daemon 线程调用 `calibredb add`，与 Calibre-Web 共享 `metadata.db`，处理完成后文件移入 `upload_processed/`。
- **零依赖**：仅用 Python 标准库 `http.server`，便于部署与维护。
- **仅监听 127.0.0.1**，公网只有 Cloudflare Tunnel 一个暴露面。

### 2.2 上传入口统一

Calibre-Web 导航栏的原生 Upload 表单（`layout.html`）已替换为指向 `/async-upload` 的链接，避免用户误走同步上传路径触发 Cloudflare 超时。**新增书籍只有一个入口：`/async-upload`。**

保留的例外：书籍编辑页（`book_edit.html`）的"上传格式"表单用于给**已有**书籍追加格式，不属于新增书籍入口，保留不动。

### 2.3 元数据补全（metadata-tool）

```
main.py --check/--report/--book-id/--covers-only
  └─ src/db.py 读取 metadata.db 中缺字段的书籍
      └─ 数据源回退链：douban → openlibrary
          ├─ 命中后回填 ISBN/出版日期/简介/标签
          └─ covers.py 校验并下载封面，更新 has_cover
```

- 数据源优先级在 `config.yaml` 的 `sources` 数组中定义，按顺序回退。
- 写库须正确维护关联表：`authors`/`books_authors_link`、`tags`/`books_tags_link`、`comments` 等，并更新 `books.sort`（依赖 `title_sort` 函数）。
- 封面下载失败或尺寸过小（`cover.min_size`）时跳过，不计为成功。

## 3. 部署配置说明（deploy/）

| 文件 | 用途 | 关键参数 |
|------|------|----------|
| `nginx-calibre-web.conf` | 反向代理 + 缓存 | `client_max_body_size 100M`；`/api/upload` 超时 60s + 关闭请求缓冲 |
| `calibre-web.service` | Calibre-Web 应用 | `CALIBRE_DBPATH`、端口 8083 |
| `calibre-async-upload.service` | 异步上传服务 | `CALIBRE_DBPATH`（**必须加引号**，见 §4） |

## 4. 踩坑记录

### 4.1 systemd `Environment=` 带空格值必须加引号

```ini
# 错误：值被截断为 /opt/calibre-library/Calibre
Environment=CALIBRE_DBPATH=/opt/calibre-library/Calibre Library

# 正确
Environment="CALIBRE_DBPATH=/opt/calibre-library/Calibre Library"
```

未加引号会导致 `calibredb add` 写入**错误的空库**（`/opt/calibre-library/Calibre/metadata.db`），书不会出现在 Calibre-Web。排查时检查进程环境变量：`cat /proc/<pid>/environ`。

### 4.2 Cloudflare Tunnel 超时

- HTTP 层 100s 超时**不可配置**（隧道设置里只有 TCP 层参数）。
- 因此大文件上传**必须走异步入口**，任何试图调整 tunnel HTTP 超时的方案均无效。

### 4.3 内存受限（1.6GB VPS）

- Calibre-Web 曾被 OOM Killer 反复 kill（systemd 日志 `status=9/KILL`）。
- 本机并存多个常驻进程（mihomo、cloudflared、Calibre-Web、async-upload），监控内存：`free -h`。
- 处理大量上传时建议分批，避免瞬时内存峰值。

## 5. 扩展指南

- **新增数据源**：仿照 `src/douban.py` 实现「搜索 + 详情解析」，返回统一 dict，并在 `config.yaml` 的 `sources` 中注册。
- **新增上传格式**：Calibre-Web 的 `config_upload_formats` 控制 UI 接受范围；异步服务侧 `ALLOWED_EXT` 仅用于展示，实际以 `calibredb add` 能力为准。
- **增加上传上限**：改 nginx `client_max_body_size` 与 `server.py` 的 200MB 检查，保持二者一致。
- **健康检查**：`GET /health` 返回 `{"status":"ok"}`，可接入 uptime 监控。
