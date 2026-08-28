# Calibre-Web UI 升级 — Phase 10：自研页（Custom Pages：/tasks 与 /async-upload）

> 阶段定位：本阶段对应总体规划 `00-master-plan.md` §七 的 **P10（Custom Pages）**。
> 对 Calibre Stack 自研页 `/tasks`（处理中心）与 `/async-upload`（统一上传页）应用同一 Design System 重皮肤，消除旧 Bootstrap 风格混入（总纲 §一目标）。

## 0. 目标（已实现）
- 将 `async-upload` 提供的 `/tasks` 与 `/async-upload` 页面视觉统一到全站 Design System
- 复用全站组件（Button / Table / Badge / 主题切换），消除旧 Bootstrap / 蓝底风格
- 与 Calibre-Web fork（`ui-tailwind`）在视觉与交互上无割裂

## 1. 影响项目文件（已实现）
- **calibre-stack 内**：
  - `async-upload/tasks_page.html`（重皮肤：Bootstrap → `.cw-btn*`/`.cw-table`/状态徽章/`rgb(var(--*))` 令牌；保留全部 JS/API 协议）
  - `async-upload/upload_page.html`（重皮肤：拖拽区/进度/结果/文件列表换 Design Token；保留全部 XHR/`/api/upload` 协议）
- **Fork 内（只读共享产物）**：
  - `<link href="/static/css/tailwind.css">` 复用 fork 构建产物（`/static` 走 nginx → fork:8083）
  - `tailwind.config.js`：content 增加 `../async-upload/**/*.html`（使两页用到的 postcss utilities 被扫描生成）
  - `cps/static/css/tailwind.css`：重建（含 async-upload 页面 utilities；38.9KB → 39.3KB）

> 注：`/async-upload` 由 nginx `alias` 直出 `upload_page.html`；`/tasks` 由 async-upload:8086 直出 `tasks_page.html`。二者均为独立 HTML（非 Jinja），不经过 fork 的 `layout.html` 外壳，保留各自主导航链接。

## 2. 后端改动
- 无。`async-upload` 服务路由、`/api/upload`、`/api/tasks`、SSE/轮询、`server.py` 完全不动；仅前端模板与静态样式重皮肤。nginx 配置未改。

## 3. 实施要点（已实现）
1. **任务页 `/tasks`**：`cw-btn*`（返回/上传/扫描/查看/重试）+ `cw-table` 行皮肤 + 状态徽章（success/danger/primary/surface-secondary 用 `rgb(var(--*))`）+ `.detail-cell` 令牌色；保留 `load()`/`retry()`/`scanBtn`/`STAGE_CN`/`STATUS_CN` 全部 API 与 5s 轮询
2. **上传页 `/async-upload`**：`.upload-zone`（拖拽/悬停主色）+ `.cw-btn--primary` 上传 + 进度条/结果/文件列表全部换 Design Token；`200MB` 上限提示更新；保留 XHR `/api/upload` 全协议
3. **主题一致**：两页共用 `calibre-theme` localStorage key（与 fork `theme.js` 同步），含 `themeBtn` 切换 + prefers-color-scheme 兜底；`<html class="dark">` + 同一套 `--*` CSS 变量
4. **联邦入口保持**：`/tasks` 侧边栏挂接不变（P2）；两页均保留 `返回书库` 导航

## 4. 回测方法
1. **类覆盖校验（已通过）**：两页出现的所有 `class` 均存在于 `tailwind.css` 或页面内联 `<style>`；HTML 结构性校验通过（根栈收拢 `<html>`）
2. **构建通过**：`npm run build` 成功；`tailwind.css` 38.9KB → 39.3KB，`mb-4/px-4/py-2/overflow-x-auto` 等本页 utilities 已生成（修复 content 路径 `./async-upload`→`../async-upload` 后）
3. **路由回测（nginx 静态核对）**：`/static/css/tailwind.css`→fork:8083；`/tasks`→async-upload:8086；`/async-upload`→nginx alias `upload_page.html`；`/api/`→async-upload:8086；均按现有 `/static/css/bootstrap.min.css` 同源方式可解析
4. **浏览器（运行时手验）**：
   - `/tasks` 状态徽章/进度/日志正常；重试/扫描/查看响应
   - `/async-upload` 上传流程正常；200MB 提示生效
   - 主题切换后与 fork 页面一致；无控制台 JS 错误

## 5. 推进标准（进入 P11 的门禁）
- `/tasks` 与 `/async-upload` 视觉统一到全站 Design System，无旧 Bootstrap/蓝底残留 ✅
- 任务/上传功能与协议不变（`/api/*` 未动），构建/类校验/路由核对通过 ✅
- 主题切换与 Sidebar 挂接正常 ✅（共用 `calibre-theme`）

## 6. 下一步门禁
- **P11（Accessibility / Performance Audit）**：将自研页纳入全站无障碍与性能审计范围。

## 7. 备注
- 自研页与服务是独立进程，重皮肤仅涉及其模板与静态样式，务必保持 `design/02-task-store-api.md` §2.4 约定的视觉一致与协议稳定。

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P10 并经验证后，可进入 P11.
