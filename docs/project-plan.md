# Calibre 书库自动化工作流 — 项目计划 v3

> 状态：**可执行**（安全基础已就绪，待逐 Phase 实施）
> 更新：2026-08-23

---

## 〇、方案演进记录

| 版本 | 思路 | 结论 |
|------|------|------|
| v1 | 夜间定时批量任务 + 队列 | 队列过重 |
| v2 | 夜间流水线，仅处理「需转EPUB且当日未完成」的书 + 增量扫描 | 被事件驱动思路取代 |
| **v3（本版）** | **上传时异步即时处理；多源EPUB搜索；统一鉴权；可视化处理中心；原子化功能手动可调** | 可执行 |

核心转变：不再依赖夜间批量和长驻队列。新书入库即触发处理流水线，当场完成绝大部分工作；每个功能同时暴露为独立接口，供用户对漏网书籍手动补充执行。

---

## 一、已完成事项

### 1.1 nginx 缓存修复 ✅
- **问题**：Calibre-Web 每个响应带 `Set-Cookie` + `Vary: Cookie` + `Cache-Control: no-cache`，nginx proxy_cache 全部跳过
- **修复**：三个缓存 location 添加 `proxy_ignore_headers Set-Cookie Vary Cache-Control` + `proxy_cache_key $scheme$proxy_host$uri`
- **效果**：封面 MISS → HIT，55ms → 27ms

### 1.2 分页 Bug 修复 + 全页加载 ✅
- **Bug**：`web.py render_hot_books` 把当前页条目数当总数传给 `Pagination`
- **修复**：`total_count = all_books.count()` + `config_books_per_page=999`
- **效果**：82 本一次加载，分页导航消失

### 1.3 安全审计 + nginx auth_request ✅
- 全部端点扫描完毕，无泄露
- `/async-upload`、`/api/*` 添加 nginx auth_request，复用 Calibre-Web 会话
- 未登录全部返回 302 → `/login?next=原路径`
- `/health` 不再暴露（404）
- 移除无效 `/thumb/` 缓存

---

## 二、统一鉴权：复用 Calibre-Web 登录

用 nginx `auth_request` 做门禁：

```
浏览器 → nginx auth_request 子请求 → Calibre-Web
    ├── 已登录(200) → 放行
    └── 未登录(302) → 重定向到 /login?next=原路径
```

受保护范围：`/async-upload`、`/api/*`、`/tasks`（新增）
Calibre-Web 自有路由自带鉴权（`@login_required_if_no_ano`）

---

## 三、安全加固（待实施）

### 3.1 secrets.env 统一凭证入口
```
/opt/calibre-stack/secrets.env    # chmod 600, 不进 git
ZLIB_EMAIL=
ZLIB_PASSWORD=
```
> 本栈任务队列用 SQLite（`tasks.db`），**不引入 Redis/MQ**，故 secrets.env 不含 Redis 密码。

### 3.2 cloudflared cred-file
```ini
ExecStart=/usr/local/bin/cloudflared tunnel --cred-file /etc/cloudflared/token
```
- install.sh 自动迁移，chmod 600，不要求轮换 token

### 3.3 .gitignore 加固
追加：`secrets.env`、`.env*`、`*.db`、`reports/`

---

## 四、书籍处理中心

### 页面（/tasks，登录后可见）
```
📚 书籍处理中心
[全库扫描]              今日 zlib 配额: 7/10
─────────────────────────────────────────────
射雕英雄传.txt
 ✓入库 → ⏳搜索EPUB(Gutenberg→IA→zlib)
 [转格式][搜EPUB][补信息][去重][重试]
─────────────────────────────────────────────
```

### API
| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/tasks` | 任务清单 JSON |
| POST | `/api/tasks/{id}/retry` | 重试 |
| POST | `/api/books/{id}/convert` | 手动格式转换 |
| POST | `/api/books/{id}/search_epub` | 手动 EPUB 搜索 |
| POST | `/api/books/{id}/metadata` | 手动元数据补全 |
| POST | `/api/books/{id}/dedupe` | 手动去重 |
| POST | `/api/scan` | 全库扫描 |

### 任务表
```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER, title TEXT,
    stage TEXT,  -- uploaded/adding/converting/searching_epub/enriching/deduping/done
    status TEXT DEFAULT 'pending',
    detail TEXT,
    attempt_count INTEGER DEFAULT 0,   -- 重试次数（幂等）
    last_error TEXT DEFAULT '',       -- 最近错误（排查用）
    owner TEXT DEFAULT '',             -- 认领 worker 标识
    started_at TIMESTAMP, finished_at TIMESTAMP,
    created_at TIMESTAMP, updated_at TIMESTAMP
);
```

> 执行模型见 design/02-task-store-api.md §2.2.1：**常驻单 worker 轮询认领**，不再每请求 spawn daemon thread；
> 启动 `reset_interrupted()` 把残留 `running` 重置为 `pending`（重启不丢任务）；各动作幂等可安全重试。

---

## 五、原子模块

### 目录结构
```
async-upload/
├── server.py            # 路由 + 鉴权
├── post_process.py      # 流水线编排
├── format_converter.py  # ebook-convert + DRM 检测 + 归档
├── epub_sources.py      # Gutendex/IA/zlib 多源
├── metadata_enricher.py # 豆瓣/OpenLibrary
├── deduplicator.py      # 同名检测 + 归档
├── task_store.py        # tasks.db
├── upload_page.html     # 现有
└── tasks_page.html      # 新增
```

### EPUB 资源优先级（已实测）
| 优先级 | 来源 | 免费 | 中文 |
|--------|------|------|------|
| 1 | ebook-convert | ✅ | — |
| 2 | Gutendex | ✅ | 444本古典 |
| 3 | Internet Archive | ✅ | 有 |
| 4 | z-library | 10/天 | 强 |

### 上传自动流水线
```
上传 → staging → 入库 → 格式判断
  ├─ EPUB → 元数据 → 去重 → 完成
  ├─ MOBI/AZW → convert → 成功则归档 / DRM则search_epub
  └─ TXT → search_epub
每步写 tasks.db
```

---

## 六、存量书籍

| 指标 | 数值 |
|------|------|
| 总数 | 82 |
| EPUB | 53（不处理） |
| TXT | 25 → 去重 14 本金庸小说 |
| MOBI/AZW/AZW3 | 30（部分 DRM） |
| 缺 ISBN | 69 |
| 缺简介 | 27 |
| 缺封面 | 26 |

---

## 七、实施阶段

| Phase | 内容 | 前置 |
|-------|------|------|
| **0 安全加固** | secrets.env + .gitignore + cloudflared cred-file + Redis 密码 | 无 |
| **1 处理中心** | task_store + API + tasks_page.html | Phase 0 |
| **2 原子模块** | 四模块 + post_process + 上传接入 + zlibrary | Phase 1 |
| **3 存量处理** | 全库扫描 | Phase 2 |
| **收尾** | 测试 → git push → 文档更新 | Phase 3 |

---

## 八、决策存档

| 问题 | 决策 |
|------|------|
| 原文件处理 | 归档 `_archive/`，不删除 |
| 元数据 | 增量（缺字段才查），并入流水线 |
| z-library 凭据 | secrets.env，用户稍后提供 |
| 队列 | SQLite 表，不引入 Redis/MQ |
| 分页 | 已移除，全页加载 |
| DRM 文件 | 尝试 z-library 重新下载 |
| TXT 优先级 | TXT 优先于 DRM（获取 EPUB 收益最大） |
