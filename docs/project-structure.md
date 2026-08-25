# Calibre Stack — 项目结构完整文档

> 适用范围：本自托管电子书管理栈（Calibre-Web + 异步上传服务 + 元数据补全工具）。
> 文档基于实机状态梳理（2026-08-25），覆盖目录结构、组件职责、数据存放、配置与请求流。

---

## 1. 项目总览

本栈面向**低配 VPS（约 1.6GB 内存）+ Cloudflare Tunnel** 场景，解决「经 Tunnel 直传大文件触发 Cloudflare 100 秒边缘超时」的痛点：用一层**异步上传服务**把「文件接收」与「入库处理」解耦，毫秒级响应规避超时，后台再慢慢 `calibredb add`。

| 组件 | 路径 | 运行方式 | 端口 |
|------|------|----------|------|
| Calibre-Web（书库 UI + OPDS + 邮件推送） | `/opt/calibre-web/venv/.../calibreweb` | systemd `calibre-web` | 8083 |
| 异步上传服务（自研） | `/opt/calibre-stack/async-upload` | systemd `calibre-async-upload` | 8086 |
| nginx 反代 + 鉴权门禁 | `/etc/nginx/sites-available/calibre-web` | systemd `nginx` | 8084（对内） |
| 元数据补全工具（自研 CLI） | `/opt/calibre-stack/metadata-tool` | 手动 / cron | — |
| 书籍库（calibredb 库） | `/opt/calibre-library/Calibre Library` | — | — |

对外只暴露 **nginx:8084**（经 Cloudflare Tunnel），其余服务均仅监听 `127.0.0.1`。

---

## 2. 目录树（实机）

```
/opt/calibre-stack/                   ← 自定义代码栈根（git 仓库）
├── README.md                         ← 项目说明（组件/架构/快速开始）
├── .git/  .gitignore
├── async-upload/                     ← 【自研】异步上传服务
│   ├── server.py                     ← HTTP 服务：/api/upload、/api/tasks、/tasks、/health
│   ├── task_store.py                 ← SQLite 任务状态存储（tasks.db）
│   ├── tasks_page.html               ← 任务看板页面（复用 Calibre-Web Bootstrap 主题）
│   ├── upload_page.html              ← 独立上传页（/async-upload，隐藏后备入口）
│   └── tasks.db                      ← 任务状态库（运行中生成）
├── metadata-tool/                    ← 【自研】元数据补全 CLI
│   ├── main.py                       ← 入口：扫描缺失字段、补 ISBN/出版日期/简介/封面
│   ├── config.yaml                   ← 代理、数据源优先级、字段规则
│   ├── requirements.txt
│   └── src/
│       ├── db.py                     ← 封装 calibredb / metadata.db 读写
│       ├── douban.py                 ← 豆瓣 API 客户端
│       ├── openlibrary.py            ← Open Library API 客户端
│       ├── covers.py                 ← 封面下载器
│       ├── utils.py                  ← 出版日期解析等工具
│       └── __init__.py
├── deploy/                           ← 部署物料（幂等）
│   ├── install.sh                    ← 一键部署：装服务/配 nginx/启动/验证
│   ├── calibre-web.service           ← systemd 单元（Calibre-Web）
│   ├── calibre-async-upload.service  ← systemd 单元（上传服务）
│   ├── nginx-calibre-web.conf        ← nginx 配置「模板」（注意：已与线上偏离，见 §7）
│   ├── web.py.patch                  ← 对 Calibre-Web cps/web.py 的源码定制
│   ├── layout.html.patch             ← 对 Calibre-Web templates/layout.html 的定制（导航）
│   └── uploadprogress.js.patch       ← 对 Calibre-Web static/js/uploadprogress.js 的定制
└── docs/
    ├── project-plan.md               ← 项目计划
    ├── requirements.md               ← 需求说明
    ├── development.md                ← 开发说明
    ├── deployment.md                 ← 部署指南
    └── design/                       ← 设计文档 01–11
        ├── 01-security-hardening.md
        ├── 02-task-store-api.md      ← 任务存储 + API（已实现）
        ├── 03-format-converter.md
        ├── 04-epub-sources.md
        ├── 05-metadata-dedupe.md
        ├── 06-pipeline-dashboard.md  ← 任务看板设计（已实现）
        ├── 07-full-scan.md
        ├── 08-subagent-review.md
        ├── 09-process-review-findings.md
        ├── 10-config-secrets.md      ← 反钓鱼信任模型
        └── 11-library-maintenance.md ← 去重/封面/元数据维护（Phase 1 已执行）

/opt/calibre-web/                     ← Calibre-Web 安装与数据根
├── venv/                             ← Python 虚拟环境
│   └── lib/python3.12/site-packages/calibreweb/
│       ├── cps/                      ← Calibre-Web 应用代码（见 §3.1）
│       ├── __main__.py
│       └── requirements.txt
├── app.db                            ← Calibre-Web 配置库（用户/设置/权限）★核心配置在此
├── gdrive.db                         ← Google Drive 集成状态库
├── async_upload.py                   ← 旧版/内置异步上传脚本（已被 8086 服务取代，保留）
├── upload_page.html                  ← 被 nginx 用作 /async-upload 的页面（与 stack 内同名文件二选一生效）
├── upload_staging/                   ← 上传文件暂存（server.py 写入）
├── upload_processed/                 ← 处理完成后的归档
├── calibre-web.log                   ← 运行日志
├── init.log
├── .key                              ← 会话密钥
└── .config/  .cache/  .calibre-web/

/opt/calibre-library/                 ← 书籍库根
└── Calibre Library/                  ← config_calibre_dir 指向此处
    ├── metadata.db                   ← calibre 书库元数据（71 本，含格式/作者/封面指针）
    └── <作者名>/<书名 (ID)>/<书名>.<格式>   ← 实际书文件（EPUB/AZW3/KFX/MOBI/PDF/TXT…）

/etc/nginx/
├── sites-available/calibre-web       ← 【线上生效】反代 + 鉴权配置（见 §6）
├── sites-enabled/calibre-web         ← 软链 → sites-available/calibre-web
└── sites-available/default           ← 默认站点（未用）

/etc/systemd/system/
├── calibre-web.service               ← 来自 deploy/
└── calibre-async-upload.service      ← 来自 deploy/
```

---

## 3. 组件职责

### 3.1 Calibre-Web（`/opt/calibre-web/venv/.../calibreweb/cps`）
第三方应用（janeczku/calibre-web），经 **patch** 定制后运行。关键模块：

| 模块 | 职责 |
|------|------|
| `web.py` | 主 Flask 路由（首页/列表/详情/下载/OPDS/管理） |
| `admin.py` / `config_sql.py` | 后台管理与配置持久化（写入 `app.db`） |
| `db.py` | 封装 calibre `metadata.db` 访问 |
| `uploader.py` | 上传文件的元数据抽取（EPUB/PDF/MOBI…） |
| `editbooks.py` | 书籍编辑、格式上传（`/upload`、`/edit/...`） |
| `tasks_status.py` / `tasks.html` | Calibre-Web 自带「Tasks」看板 |
| `converter.py` / `epub_helper.py` / `mobi.py` / `fb2.py` / `comic.py` | 格式转换与解析 |
| `kobo*.py` | Kobo 设备同步 |
| `gdrive.py` / `gdriveutils.py` | Google Drive 备份 |
| `search.py` / `search_metadata.py` | 搜索与元数据在线搜索 |
| `usermanagement.py` / `MyLoginManager.py` | 用户/登录/权限 |
| `reverseproxy.py` / `reverse_proxy_auth.py` | 反向代理鉴权（本栈用 nginx 前置鉴权） |
| `server.py` / `tornado_wsgi.py` / `gevent_wsgi.py` | WSGI 服务器入口（服务以 `cps -i 127.0.0.1` 启动） |

模板 `templates/layout.html` 内含**原生 Upload 按钮**（POST `/api/upload`，即本栈接管路径）与「Tasks」链接；`static/js/uploadprogress.js` 负责上传模态与进度。

> 注意：`deploy/*.patch` 是对上述源码/模板的定制快照。线上 venv 中的 `web.py` 与 `deploy/web.py.patch` 字节一致（83983 B），说明 patch 已落地。但 **`install.sh` 仅部署服务与 nginx，并不执行 patch 应用**——patch 由人工/独立步骤打入，存在「模板漂移」风险（升级 Calibre-Web 后需重打）。

### 3.2 异步上传服务（`/opt/calibre-stack/async-upload`）
自研、零依赖（`http.server` + `sqlite3`），常驻 8086。

- **`server.py`**
  - `POST /api/upload`：解析 multipart → 每文件建任务 → 后台线程 `run_pipeline` → 立即返回 `{location:'/tasks', ok, files}`（原生按钮靠 `location` 跳转，自定义页读 `message/files`）。
  - `POST /api/scan`：触发轻量全库扫描（统计缺 EPUB 书籍），结果入任务看板。
  - `POST /api/tasks/{id}/retry`：重试失败任务。
  - `POST /api/books/{id}/{action}`：书籍级手动操作（占位）。
  - `GET /api/tasks`、`GET /api/tasks/{id}`：任务列表/详情 JSON。
  - `GET /tasks`：任务看板 HTML。
  - `GET /health`：健康检查。
  - 上限 **200MB**（`MAX_SIZE`），与 nginx 对齐。
  - `run_pipeline`：`calibredb add --with-library LIBRARY --automerge overwrite` → 非 EPUB 则 best-effort `ebook-convert` 转 EPUB 并合入 → best-effort 元数据补全（当前无凭据即跳过）→ 源文件归档至 `upload_processed/`。所有 `calibredb` 调用经 `CALIBRE_LOCK` 串行化，避免与 Calibre-Web 抢库锁。
- **`task_store.py`**：SQLite `tasks` 表（id/title/source_file/stage/status/detail/book_id/时间戳），全写加锁。
- **`tasks_page.html`**：看板，复用 Calibre-Web 的 Bootstrap CSS（`/static/css/...`），每 5s 轮询 `/api/tasks`，含状态色标、重试、扫描按钮。
- **`upload_page.html`**：独立上传页（拖拽 + 进度），经 nginx `/async-upload` 提供，作为隐藏后备入口（不在界面常驻导航）。

### 3.3 元数据补全工具（`/opt/calibre-stack/metadata-tool`）
CLI，从**豆瓣 / Open Library** 补 ISBN、出版日期、简介、标签、封面。经 `config.yaml` 配置代理（`http://127.0.0.1:7890`）、数据源优先级、字段规则。与上传服务解耦，单独运行（手动/cron），**不自动接入上传管线**（上传管线仅在配置凭据后才会触发 best-effort 补全，当前未配置）。

### 3.4 nginx（`/etc/nginx/sites-available/calibre-web`）
对外 `listen 127.0.0.1:8084`，内部反代 + 鉴权门禁。路由见 §6。

---

## 4. 数据存放

| 数据 | 位置 | 说明 |
|------|------|------|
| Calibre-Web 配置 | `/opt/calibre-web/app.db` | 用户、角色、权限、`config_calibre_dir`、`config_uploading` 等。**关键**：`config_calibre_dir = /opt/calibre-library/Calibre Library`；`config_uploading=1`（原生上传开启，即界面唯一 Upload 按钮）。 |
| 书籍元数据 | `/opt/calibre-library/Calibre Library/metadata.db` | calibre 库（71 本）。上传服务经 `--with-library` 显式写入此处，与 Calibre-Web 共享。 |
| 书文件 | `/opt/calibre-library/Calibre Library/<作者>/<书名 (ID)>/` | 实际 EPUB/AZW3/… 文件。 |
| 任务状态 | `/opt/calibre-stack/async-upload/tasks.db` | 上传/扫描任务记录，与书库分离。 |
| 上传暂存/归档 | `/opt/calibre-web/upload_staging/`、`upload_processed/` | 上传服务写入/归档。 |
| 服务日志 | `/opt/calibre-web/calibre-web.log`、`journalctl -u calibre-async-upload` | — |
| 会话密钥 | `/opt/calibre-web/.key` | Calibre-Web 会话签名。 |

> 易错点：Calibre-Web 服务以 `CALIBRE_DBPATH=/opt/calibre-web` 运行（这是**配置目录**，放 `app.db`），书籍库另由 `config_calibre_dir` 指定。上传服务以 `CALIBRE_DBPATH=/opt/calibre-library/Calibre Library` 运行，但因始终显式传 `--with-library`，环境变量仅作兜底，二者一致指向正确书库。

---

## 5. 配置与凭据

- **代理**：所有外网调用走 `http://127.0.0.1:7890`（metadata-tool 在 `config.yaml`；上传管线若启用补全也须走此代理）。
- **来源凭据**：z-library / Anna's Archive **均未配置**（用户无账号）→ 相关来源在当前管线中禁用，补全静默跳过。
- **域名白名单 / 反钓鱼**：见 `docs/design/10-config-secrets.md`，trust anchor 为用户维护的域名白名单 + TLS 校验。
- **系统级**：`/etc/systemd/system/*.service` 定义运行用户（`calibreweb`）、环境变量、重启策略；`/etc/nginx/...` 定义反代与 `client_max_body_size 200M`。

---

## 6. nginx 路由（线上生效版）

```
listen 127.0.0.1:8084;  client_max_body_size 200M;
_location = /_auth_check      → 内部子请求到 Calibre-Web /，200=已登录 / 302=未登录
_error_page 500 = @login_redirect → return 302 /login?next=$request_uri   (覆盖所有 auth_request 位置)
~* \.(css|js|woff|…)$       → Calibre-Web:8083（公开静态，带缓存）
/cover/                    → Calibre-Web:8083（封面缓存）
/upload                    → Calibre-Web:8083（原生上传，自带鉴权）
/async-upload              → 静态 alias 到 upload_page.html（auth_request 门禁）
/tasks                     → 异步服务:8086/tasks（auth_request 门禁）
/api/                      → 异步服务:8086（auth_request 门禁，proxy_request_buffering off，200M）
/                          → Calibre-Web:8083（兜底，自带鉴权）
```

鉴权机制：`auth_request /_auth_check` 把子请求发给 Calibre-Web；已登录返回 200 放行，未登录返回 302 → nginx 将其映射为 500 → `error_page 500` 重定向到登录页。子请求会**转发原始 Cookie**，故已登录用户的 XHR 上传能正常通过。

---

## 7. 请求流

**上传（界面唯一 Upload 按钮）：**
```
浏览器(Calibre-Web UI) --POST /api/upload--> nginx:8084(/api/)
   → auth_request 校验登录(Cookie 转发) → 8086 异步服务
   → server.py 解析 multipart、建任务、后台 run_pipeline(calibredb add)
   → 立即返回 {location:'/tasks'} → uploadprogress.js 跳转 /tasks
后台: calibredb add → (非EPUB)转EPUB → (best-effort)补全 → 归档
用户在 /tasks 看板看到 处理中→成功，书库出现该书
```

**普通浏览/下载/邮件推送：** `nginx /` → Calibre-Web:8083（自带鉴权）。

**元数据补全：** 独立运行 `metadata-tool/main.py`，直接读写 `metadata.db`，不经过 nginx/8086。

---

## 8. 部署与运维

- **一键部署**：`deploy/install.sh`（复制 service、nginx 配置、reload、启动、健康检查）。
  - ⚠️ 该脚本**不应用 `deploy/*.patch`**；patch 需另行打入 venv，升级 Calibre-Web 后会丢失定制（导航/上传模态），需重打。
- **启动/重启**：
  - `systemctl restart calibre-web calibre-async-upload`
  - `systemctl reload nginx`
- **健康检查**：`curl http://127.0.0.1:8086/health` → `{"status":"ok"}`
- **验证上传**：界面点 Upload → 跳 /tasks → 任务 success 且书库出现。
- **常用排错**：
  - 任务写库报 `readonly database` → 检查 `tasks.db` 属主（`calibreweb:calibreweb`）。
  - 上传 404 → 确认 nginx `/api/` 指向 8086 且 `server.py` 处理 `/api/upload`。
  - 上传后书库不出现 → 确认上传服务 `CALIBRE_DBPATH` 与 Calibre-Web `config_calibre_dir` 指向同一书库。
  - 未登录被弹登录页 → 正常（auth_request）。

---

## 9. 设计文档索引（docs/design）
- **02-task-store-api**：任务存储 + API 契约（已落地）。
- **06-pipeline-dashboard**：任务看板（已落地）。
- **10-config-secrets**：来源域名白名单 / 反钓鱼信任模型。
- **11-library-maintenance**：去重/封面/元数据维护（Phase 1 已执行：去重 82→71、补 15 张豆瓣封面）。
- 其余（03 格式转换 / 04 EPUB 来源 / 05 去重 / 07 全库扫描 / 08-09 review）为规划或评审记录。

---

## 10. 已知偏离与风险
1. **deploy 模板与线上配置不一致**：`deploy/nginx-calibre-web.conf` 仍为 `100M` 且无 `/tasks`；线上 `/etc/nginx/sites-available/calibre-web` 已改为 `200M` + `/tasks`。重跑 `install.sh` 会覆盖线上配置，须先同步模板。
2. **patch 未纳入 install.sh**：Calibre-Web 升级后定制（导航/上传模态）需手动重打。
3. **`/opt/calibre-web/async_upload.py` 与 `/opt/calibre-web/upload_page.html`** 为旧版/冗余资产，功能已被 `calibre-stack/async-upload` 取代；保留以免误删，但非活跃路径。
4. **上传管线补全依赖外部凭据**：当前 z-library/Anna's 未配置，补全为静默 no-op；接入后须在 `server.py` 的 `_enrich_best_effort` 实现并走代理。
5. **EPUB 仅此**：维持仅 EPUB（非 EPUB best-effort 转 EPUB）；Kindle 投递走 Calibre-Web 内置邮件，未自研。
