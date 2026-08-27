# 需求说明

## 1. 项目目标

为自托管 Calibre 电子书库提供三项能力：

1. **稳定上传**：在 Cloudflare Tunnel 环境下上传大体积电子书不超时、不卡顿。
2. **元数据自动补全**：自动填充缺失的 ISBN、出版日期、简介、标签、封面。
3. **低资源占用**：全部组件可在 1.6GB 内存 VPS 上与 Calibre-Web 共存运行。

## 2. 背景与问题

### 2.1 上传超时（核心问题）

访问链路：`浏览器 → Cloudflare CDN → cloudflared → nginx:8084 → Calibre-Web(Tornado):8083`

- Cloudflare 边缘节点对 HTTP 请求有 **100 秒硬超时**，隧道配置中仅可调 TCP 层参数（连接超时/空闲连接/keep-alive），HTTP 层超时不可配置。
- Calibre-Web 的 `/upload` 处理是**同步**的：保存临时文件 → 解析元数据 → 写数据库 → 移动文件到书库目录 → 全部完成后才返回响应。大文件处理耗时超过 100s 即被 Cloudflare 掐断，浏览器表现为「卡顿无反应 / a timeout occurred」。

### 2.2 元数据缺失

导入的书源混杂（扫描件、自制 epub），普遍缺 ISBN、出版日期、简介、封面，人工补全低效。

## 3. 功能需求

### 3.1 异步上传服务（async-upload）

| 编号 | 需求 |
|------|------|
| AU-1 | 提供 Web 上传页：拖拽 + 多选 + 进度条 |
| AU-2 | 接收文件后**立即**返回 HTTP 200（毫秒级），不等待入库 |
| AU-3 | 后台线程调用 `calibredb add --automerge overwrite` 入库，与 Calibre-Web 共享 `metadata.db` |
| AU-4 | 支持格式：epub/pdf/mobi/azw/azw3/cbz/cbr/txt/docx/fb2/kepub/djvu 等 |
| AU-5 | 单文件上限 200MB；multipart/form-data 协议 |
| AU-6 | systemd 守护，崩溃自动拉起 |

**明确排除 / 边界澄清**：
- **服务自身不实现 Calibre-Web 会话/CSRF**：`async-upload` 是一个独立 HTTP 服务，不依赖 Calibre-Web 内部登录/CSRF 实现，避免耦合其内部细节。
- **但公网入口由 nginx 统一鉴权**：生产环境 `async-upload` 仅监听 `127.0.0.1`，对外只暴露 nginx（Cloudflare Tunnel 入口）；nginx 通过 `auth_request` 复用 Calibre-Web 登录态做门禁（未登录 → 302 `/login`）。即「服务不实现 session」与「入口使用 Calibre-Web 登录态」二者同时成立，互不矛盾。
- 不开放公网直连端口（必须走 Cloudflare Tunnel，方案已被否决）

### 3.2 元数据补全工具（metadata-tool）

| 编号 | 需求 |
|------|------|
| MT-1 | 数据源：豆瓣读书（优先）、Open Library（兜底），按序回退 |
| MT-2 | 补全字段：ISBN13、出版日期、简介、标签、封面图片 |
| MT-3 | 支持 dry-run 检查（`--check`）、单本处理（`--book-id`）、仅封面（`--covers-only`）、全量报表（`--report`） |
| MT-4 | 出站请求走本地代理，限速防封禁 |
| MT-5 | 直接操作 calibre `metadata.db`，需正确维护 authors/tags/comments 关联表及 `has_cover` 状态 |

## 4. 非功能需求

| 类别 | 要求 |
|------|------|
| 性能 | 上传接口响应 < 1s（不含文件传输）；异步入库单本 < 300s |
| 资源 | async-upload 常驻内存 ~13MB；metadata-tool 仅运行时占用 |
| 可靠性 | 服务异常 systemd 自动重启；入库失败保留暂存文件便于排查 |
| 安全 | 所有入口仅监听 127.0.0.1，公网暴露面只有 Cloudflare Tunnel |
| 兼容 | 不修改 Calibre-Web 源码（pip 安装包，升级会被覆盖） |

## 5. 验收标准

1. 通过 Cloudflare 域名上传 50MB+ 电子书，进度条走完后立即得到成功反馈，无超时。
2. 后台处理完成后书籍出现在 Calibre-Web 中，元数据完整。
3. `python3 main.py --check` 对 55 本藏书报 55/55 Complete。
4. `systemctl restart` 任一服务后功能自愈，无需人工干预。
