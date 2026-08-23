# Calibre 书库自动化工作流 — 项目计划 v3

> 状态：**待 review**（本文档为最终方案定稿，未执行）
> 更新：2026-08-23

---

## 〇、方案演进记录

| 版本 | 思路 | 结论 |
|------|------|------|
| v1 | 夜间定时批量任务 + 队列 | 队列过重 |
| v2 | 夜间流水线，仅处理「需转EPUB且当日未完成」的书 + 增量扫描 | 被事件驱动思路取代 |
| **v3（本版）** | **上传时异步即时处理；多源EPUB搜索；统一鉴权；可视化处理中心；原子化功能手动可调** | 待执行 |

核心转变：不再依赖夜间批量和长驻队列。新书入库即触发处理流水线，当场完成绝大部分工作；每个功能同时暴露为独立接口，供用户对漏网书籍手动补充执行。

---

## 一、已完成事项（历史）

### 1.1 nginx 缓存修复 ✅
- **问题**：Calibre-Web 每个响应带 `Set-Cookie` + `Vary: Cookie` + `Cache-Control: no-cache`，nginx proxy_cache 全部跳过，封面每次回源
- **修复**：`/etc/nginx/sites-enabled/calibre-web` 三个缓存 location 添加：
  ```nginx
  proxy_ignore_headers Set-Cookie Vary Cache-Control;
  proxy_hide_header Set-Cookie;
  proxy_hide_header Vary;
  proxy_cache_key $scheme$proxy_host$uri;
  ```
- **效果**：封面 MISS → HIT，本地 55ms → 27ms；Cloudflare 链路收益更大
- 已提交 GitHub（含 `deploy/web.py.patch`）

### 1.2 分页 Bug 修复 + 全页加载 ✅
- **Bug**：`web.py render_hot_books` 把当前页条目数当总数传给 `Pagination`，`has_next` 永远 False，infinite-scroll 失去 `.next` 目标后停止加载（即"偶尔分页、滑动后又不分页"现象）
- **修复**：`total_count = all_books.count()`；并设 `config_books_per_page=999`
- **效果**：82 本书一次全量加载，分页导航消失
- 注意：Calibre-Web 升级会覆盖 `web.py`，需重新应用 `deploy/web.py.patch`

### 1.3 安全审计结论 ✅（仅审计，未整改）
| 发现 | 等级 | 现状 |
|------|------|------|
| Cloudflare tunnel token 明文在 systemd 单元，world-readable 且 ps 可见 | 高 | 未整改 → 见 §3.2 |
| Redis 弱密码 `redis`（仅绑定 localhost 缓解） | 中 | 未整改 → 见 §3.3 |
| `.gitignore` 未排除 `.env*`/`*.db` | 低 | 未整改 → 见 §3.4 |
| `/api/upload` 在隧道后完全公开，任何人可传书占磁盘 | 高 | 未整改 → 见 §2 统一鉴权 |
| GitHub 历史 | — | 已扫描全部 commit，无泄露 |

---

## 二、统一鉴权：复用 Calibre-Web 登录（用户已确认）

### 设计
用 nginx `auth_request` 做门禁——受保护路径进入后端前，nginx 携带浏览器 Cookie 向 Calibre-Web 发起子请求验证会话：

```
浏览器访问 /tasks / /async-upload 或 POST /api/*
    │
    ▼
nginx auth_request 子请求 → http://127.0.0.1:8083/
    ├── 已登录(200)   → 放行到 async-upload:8086
    └── 未登录(302)   → 重定向到 Calibre-Web 登录页，登录后原路返回
```

```nginx
location = /_auth_check {
    internal;
    proxy_pass http://127.0.0.1:8083/;
    proxy_pass_request_body off;
    proxy_set_header Content-Length "";
}
# 受保护 location 均加：
auth_request /_auth_check;
error_page 500 = @login_redirect;   # 子请求 302 → auth_request 视为失败 → 重定向登录
```

### 受保护范围
| 路径 | 说明 |
|------|------|
| `/async-upload`（上传页）、`/upload` | 堵住匿名传书漏洞 |
| `/tasks`（新处理中心页） | |
| `/api/upload`、`/api/tasks*`、`/api/books*`、`/api/scan` | 全部管理 API |

### 要点
- 零新增账号体系：登录一次全站通用，session 过期自动重登
- Guest 匿名浏览已关闭（config_anonbrowse=0），只有真实账号能通过
- async-upload 服务本身不实现认证逻辑，继续只绑 127.0.0.1
- 纯 nginx 层实现，Calibre-Web 升级不受影响

---

## 三、安全加固（全部自动化，零定期人工维护）

### 3.1 secrets.env 统一凭证入口
```
/opt/calibre-stack/secrets.env    # chmod 600, 不进 git
```
```bash
ZLIB_EMAIL=
ZLIB_PASSWORD=
REDIS_PASSWORD=<随机强密码>
```
规则：
- 所有凭据只存此文件；代码一律从环境变量读取，源码零明文
- systemd 服务通过 `EnvironmentFile=/opt/calibre-stack/secrets.env` 注入
- 用户后续提供 zlibrary 账户时填入此处即可

### 3.2 cloudflared cred-file 改造（不要求轮换 token）
```ini
# 改造前：token 在命令行，ps/journald/world-readable 可见
ExecStart=/usr/local/bin/cloudflared tunnel --no-autoupdate run --token eyJh...
# 改造后：凭据文件锁死权限
ExecStart=/usr/local/bin/cloudflared tunnel --cred-file /etc/cloudflared/tunnel.json
```
- install.sh 自动迁移：token 写入 JSON 文件 chmod 600，目录 700，systemd 单元移除明文
- 效果：ps、journald、单元文件三处泄露面全消除
- 决策：单用户 VPS、无其他登录账号，旧 token 实际被读取概率低，**跳过轮换**；将来用户若在 CF 后台轮换，重跑 install 即可

### 3.3 Redis 强密码
- 先探测现有消费者（`ss -tnp | grep 6379`）避免破坏其他服务
- 生成随机密码写入 secrets.env + redis.conf，重启 redis 并同步受影响服务

### 3.4 .gitignore 加固
追加：`secrets.env`、`.env*`、`*.db`、`reports/`

---

## 四、书籍处理中心（可视化清单页面）

扩展 async-upload 服务（它已是后台处理中枢），新增 SQLite 任务跟踪 + 页面。

### 页面示意（/tasks，登录后可见，风格沿用 upload_page.html）
```
📚 书籍处理中心
─────────────────────────────────────────────
[全库扫描]              今日 zlib 配额: 7/10
─────────────────────────────────────────────
射雕英雄传.txt
 ✓入库 → ⏳搜索EPUB(Gutenberg→IA→zlib)
 [转格式][搜EPUB][补信息][去重][重试]

The Selfish Gene.azw3
 ✓入库 → ✗DRM失败 → ✓已下载EPUB替换归档
─────────────────────────────────────────────
```
- 每 5 秒轮询刷新，展示每本书各阶段状态、时间戳、错误详情
- 失败项可单步重试或手动触发任一原子功能
- 显示 z-library 当日配额余量

### API 设计
| 方法/路径 | 功能 |
|-----------|------|
| `GET /api/tasks` | 任务清单 JSON（供页面轮询） |
| `POST /api/tasks/{id}/retry` \| `cancel` | 重试/取消 |
| `POST /api/books/{id}/convert` | 手动格式转换 |
| `POST /api/books/{id}/search_epub` | 手动 EPUB 多源搜索下载 |
| `POST /api/books/{id}/metadata` | 手动元数据补全 |
| `POST /api/books/{id}/dedupe` | 手动去重归档 |
| `POST /api/scan` | 手动全库增量扫描 |

鉴权由 nginx 门禁统一保证，服务端不做二次认证。

### 任务表结构（task_store.py, tasks.db）
```sql
CREATE TABLE tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id     INTEGER,              -- 入库前可为空(仅上传)
    title       TEXT,
    stage       TEXT,                 -- uploaded/adding/converting/searching_epub/enriching/deduping/done
    status      TEXT DEFAULT 'pending',  -- pending/running/success/failed/cancelled
    detail      TEXT,                 -- 各阶段结果或错误信息
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP
);
```

---

## 五、原子化功能模块（自动流水线与手动接口同一套代码）

### 目录结构
```
/opt/calibre-stack/async-upload/
├── server.py            # HTTP 路由：上传 + 任务API + 手动API + 页面服务
├── post_process.py      # 流水线编排（入库后自动触发）
├── format_converter.py  # ebook-convert 封装 + DRM 检测 + 归档
├── epub_sources.py      # EPUB 多源客户端（见 §5.1）
├── metadata_enricher.py # 元数据补全（复用 metadata-tool 的豆瓣/OpenLibrary 逻辑）
├── deduplicator.py      # 同名检测 + 归档到 /opt/calibre-library/_archive/
├── task_store.py        # 任务状态跟踪 (tasks.db)
├── upload_page.html     # 现有上传页
└── tasks_page.html      # NEW 处理中心页
```

### 5.1 EPUB 替代源优先级（已实测验证）
| 顺序 | 来源 | 免费 | 中文支持 | 说明 |
|------|------|------|----------|------|
| 1 | 本地 ebook-convert | ✅ | — | 无 DRM 的 MOBI/AZW/AZW3 直接转换 |
| 2 | Gutendex (Project Gutenberg) | ✅ 无需认证 | 444 本古典文学，31/32 有 EPUB3 直链 | 公版书（三国/水浒/红楼等）；无现代版权书 |
| 3 | Internet Archive | ✅ 无需认证 | 有 | 广覆盖补充搜索 |
| 4 | z-library | 配额 10/天，需账户 | 强 | 现代版权书兜底（金庸等免费源均无） |

匹配策略：
- TXT：从文件名提取核心书名（去 hash 前缀）→ 同书去重后逐源搜索
- DRM 失败书：取库中书名+作者 → 逐源搜索 → 校验标题/作者匹配后下载替换

### 5.2 上传链路自动流水线
```
POST /api/upload → 存 staging → 立即返回 200
    │ 后台线程
    ▼
calibredb add 入库
    ├─ EPUB → 跳到元数据步骤
    ├─ MOBI/AZW/AZW3 → ebook-convert
    │     ├─ 成功 → add_format + 原文件归档 _archive/
    │     └─ DRM 失败 → search_epub（多源）
    └─ TXT → 提取书名 → 去重 → search_epub（多源）
元数据补全（缺失字段才查，增量）
同名去重检测 → 冗余副本归档
每一步写 tasks.db → 处理中心可见
```

### 5.3 手动执行定位
所有原子功能既是自动流水线的一环，也是独立 HTTP 接口。用途：
- 流水线跑完后仍有未处理书籍时的**补充操作**
- 单本书想重跑某个环节（如换了 zlib 账户后重搜）
- 全库扫描 `POST /api/scan` 用于存量清理和新规则启用后的回溯

---

## 六、存量书籍现状（实施基线）

| 指标 | 数值 |
|------|------|
| 书籍总数 | 82 |
| EPUB | 53（不处理） |
| TXT | 25 个文件 → 去重后 14 本金庸小说（无封面/简介，hash 命名） |
| MOBI/AZW/AZW3 | 30 本（部分有 DRM，已见 CR! 头） |
| 缺 ISBN | 69 |
| 缺简介 | 27 |
| 缺封面 | 26 |

Phase 3 一次性全库扫描预计：Gutenberg 覆盖古典类，z-library 配额分日消化剩余现代版权书。

---

## 七、实施阶段

| Phase | 内容 | 前置依赖 |
|-------|------|----------|
| **0 安全加固** | secrets.env + .gitignore + cloudflared cred-file + Redis 密码探测与更换 + nginx auth_request 门禁 | 无 |
| **1 处理中心骨架** | task_store.py + server.py 扩展 API + tasks_page.html | Phase 0 |
| **2 原子模块+流水线** | 四个功能模块 + post_process 编排 + 上传链路接入 + 安装 zlibrary | Phase 1；zlibrary 凭据填入 secrets.env（用户提供） |
| **3 存量处理** | POST /api/scan 全库一次性扫描 | Phase 2 |
| **收尾** | 端到端测试 → git push（复核无敏感文件）→ 文档更新 | Phase 3 |

---

## 八、历史决策存档（仍有效）

| 问题 | 决策 |
|------|------|
| 原始文件（MOBI/AZW/TXT）处理 | 归档到 `_archive/`，不删除 |
| 元数据清洗 | 独立能力保留，但改为增量（缺字段才查），并入流水线而非夜间批量 |
| z-library 凭据 | 用户稍后提供，只入 secrets.env |
| 队列组件 | 不引入 Redis/MQ；SQLite 表足够，多数任务当场完成无需排队 |
| 分页 | 已移除，82 本全页加载 |
