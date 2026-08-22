# Calibre 书库夜间维护流水线 — 项目计划

## 一、项目目标

建立自动化夜间维护流水线，解决以下问题：
1. 书籍格式不统一（MOBI/AZW/AZW3/TXT 需转 EPUB）
2. DRM 保护的书籍无法本地转换，需从 z-library 获取
3. 书籍元数据不完整（ISBN、简介、封面、出版日期缺失）
4. z-library 每日 10 本下载限制，需队列化处理

## 二、已完成

### nginx 缓存修复（已完成）
- **问题**：Calibre-Web 每个响应带 `Set-Cookie` + `Vary: Cookie` + `Cache-Control: no-cache`，导致 nginx proxy_cache 全部跳过，封面每次都回源
- **修复**：在 `/etc/nginx/sites-enabled/calibre-web` 的三个缓存 location 添加：
  ```nginx
  proxy_ignore_headers Set-Cookie Vary Cache-Control;
  proxy_hide_header Set-Cookie;
  proxy_hide_header Vary;
  proxy_cache_key $scheme$proxy_host$uri;
  ```
- **效果**：封面从 MISS → HIT，响应时间 55ms → 27ms（本地），通过 Cloudflare 后差距更大

## 三、待实施

### 目录结构
```
/opt/calibre-stack/nightly-job/
├── orchestrator.py       # 主调度器
├── queue.py              # SQLite 作业队列
├── scanner.py            # 增量扫描（识别需要处理的书）
├── convert_worker.py     # ebook-convert 格式转换
├── zlib_worker.py        # z-library 下载
├── validator.py          # 验证报告
├── config.yaml           # 配置
└── reports/              # 每日报告

/opt/calibre-stack/deploy/
├── calibre-nightly.service
└── calibre-nightly.timer
```

### Job Queue (SQLite)
```sql
CREATE TABLE jobs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type     TEXT NOT NULL,          -- 'convert' | 'zlib'
    book_id      INTEGER NOT NULL,
    title        TEXT,
    status       TEXT DEFAULT 'pending', -- pending/in_progress/completed/failed/skipped
    priority     INTEGER DEFAULT 0,      -- TXT=1, DRM=2
    attempts     INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    error_msg    TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at   TIMESTAMP,
    completed_at TIMESTAMP,
    UNIQUE(job_type, book_id)
);

CREATE TABLE daily_limits (
    date            TEXT PRIMARY KEY,
    zlib_downloads  INTEGER DEFAULT 0,
    max_downloads   INTEGER DEFAULT 10
);
```

### 书库现状
| 指标 | 数值 |
|------|------|
| 书籍总数 | 82 |
| EPUB | 53 (已有，不处理) |
| TXT | 25 (去重后 14 本金庸小说，无封面/简介) |
| MOBI/AZW/AZW3 | 30 (部分有 DRM) |
| 缺少 ISBN | 69 |
| 缺少简介 | 27 |
| 缺少封面 | 26 |

### 处理流程

```
扫描非 EPUB 书籍
    │
    ├── MOBI/AZW/AZW3 (30本)
    │     └── Stage 1: ebook-convert 转换
    │           ├── 成功 → calibredb add_format + 原文件移到 _archive/
    │           └── DRM 失败 → 创建作业进队列 (type=convert, priority=2)
    │
    └── TXT (25本 → 14本去重)
          └── Stage 2: z-library 搜索
                ├── 找到 EPUB → 下载入库 + 原 TXT 移到 _archive/
                └── 未找到/配额用完 → 创建作业进队列 (type=zlib, priority=1)

次日凌晨：
    队列中 pending 作业 → 重试（TXT 优先于 DRM）
```

### 四个阶段

**Stage 1: 增量元数据扫描**
- 扫描条件：`nightly_checked = 0` 或仍有缺失字段
- 处理完标记 `nightly_checked = 1`
- 已完成/无缺失 → 跳过
- 需在 books 表新增 `nightly_checked BOOL DEFAULT 0`

**Stage 2: 格式转换**
- 扫描：有 MOBI/AZW/AZW3 且无 EPUB 的书
- ebook-convert 转换，DRM 失败自动进队列
- 成功后原文件移到 `/opt/calibre-library/_archive/`

**Stage 3: z-library 下载**
- 来源：TXT 书籍 (priority=1) + Stage 2 DRM 失败 (priority=2)
- 每日限额 10 本，通过 daily_limits 表跟踪
- 用 `pip install zlibrary`（异步库，需 SingleLogin 账户）

**Stage 4: 验证报告**
- 生成 `reports/YYYY-MM-DD.json`
- 包含各阶段统计和书库最终状态

### 调度
```ini
# calibre-nightly.timer
OnCalendar=*-*-* 02:00:00
Persistent=true
RandomizedDelaySec=300

# calibre-nightly.service
Nice=19
IOSchedulingClass=idle
TimeoutStartSec=3600
```

### 用户决策
| 问题 | 决策 |
|------|------|
| DRM 文件处理 | 尝试 z-library 重新下载 |
| z-library 凭据 | 稍后手动配置 |
| 原文件处理 | 归档到 `_archive/` |
| 调度时间 | 凌晨 2:00 |
| TXT 原文件 | 归档到 `_archive/` |
| 下载优先级 | TXT 优先于 DRM |

## 四、实施步骤

1. ~~修复 nginx 缓存~~ ✅
2. 创建 nightly-job 目录和 queue.py
3. 实现 scanner.py（增量扫描非 EPUB 书籍）
4. 实现 convert_worker.py（ebook-convert + DRM 检测 + 归档）
5. 实现 zlib_worker.py（zlibrary 异步下载 + 配额管理）
6. 实现 orchestrator.py + validator.py（主调度 + 报告）
7. 安装 zlibrary（pip install zlibrary）
8. 创建 systemd timer/service
9. 首次手动运行验证
10. 推送 GitHub

## 五、安全注意事项

- nginx 缓存修改不影响安全（只缓存静态资源和封面图片）
- 匿名浏览 (`config_anonbrowse`) 测试后已恢复为 0
- z-library 凭据存放在 config.yaml，不提交 Git
- systemd 服务以最低优先级运行（Nice=19），不影响其他服务
