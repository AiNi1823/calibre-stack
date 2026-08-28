# Calibre-Web UI 升级 — Phase 10：自研页（Custom Pages：/tasks 与 /async-upload）

> 阶段定位：本阶段对应总体规划 `00-master-plan.md` §七 的 **P10（Custom Pages）**。
> 对 Calibre Stack 自研页 `/tasks`（处理中心）与 `/async-upload`（统一上传页）应用同一 Design System 重皮肤，消除旧 Bootstrap 风格混入（总纲 §一目标）。

## 0. 目标
- 将 `async-upload`（端口 8086）提供的 `/tasks` 与 `/async-upload` 页面视觉统一到全站 Design System
- 复用全站组件（Button / Badge / Table / Dialog / Drawer / 主题切换），禁止旧 Bootstrap 风格
- 与前端的任务/上传信息交互（进度、状态、日志）保持一致，不破坏现有协议
- 与 Calibre-Web fork（`ui-tailwind`）在视觉与交互上无割裂

## 1. 影响项目文件
- **calibre-stack 内**：
  - `async-upload/tasks_page.html`（重皮肤：任务列表、状态徽章、进度条、日志）
  - `async-upload/upload_page.html`（重皮肤：统一上传页，含 `MAX_UPLOAD_SIZE=200MB` 提示）
  - `async-upload/static/css/*`（引入 Tailwind 产物或同步 Design Token）
- **Fork 内**（仅共享视觉，不改服务）：
  - 依赖 `cps/static/css/tailwind.css` 构建产物或独立构建的 `calibre-stack` 版本

## 2. 后端改动
- 无。`async-upload` 服务的路由、任务协议、`/api/upload`、SSE/轮询接口完全不动；仅前端模板与静态样式重皮肤。

## 3. 实施要点
1. **任务页 `/tasks`**：若任务列表为服务端渲染，套用 P1 组件与暗色令牌；状态（排队/处理中/成功/失败）用 `Badge` 区分，进度条用主色
2. **上传页 `/async-upload`**：统一按钮/拖拽区视觉，明确展示 `200MB` 上限与格式说明；成功/失败反馈对齐全站
3. **主题一致**：`class="dark"` + 同一套 CSS 变量；若独立于 fork，则单独引入同 Token 的 Tailwind 产物
4. **联邦导航**：`/tasks` 已在侧边栏（App Shell P2）挂接，保持入口一致

## 4. 回测方法
1. **本地/8086**：`systemctl restart async-upload`（或热更新）后验证
2. **浏览器验证**：
   - `/tasks` 任务状态徽章、进度条、日志展示正确
   - `/async-upload` 上传流程正常，200MB 提示与校验生效
   - 主题切换在自研页生效，与 fork 页面风格一致
   - 无控制台 JS 错误

## 5. 推进标准（进入 P11 的门禁）
- `/tasks` 与 `/async-upload` 视觉统一到全站 Design System，无旧 Bootstrap 残留
- 任务/上传功能与协议不变，回测通过
- 主题切换与 Sidebar 挂接正常

## 6. 下一步门禁
- **P11（Accessibility / Performance Audit）**：将自研页纳入全站无障碍与性能审计范围。

## 7. 备注
- 自研页与服务是独立进程，重皮肤仅涉及其模板与静态样式，务必保持 `design/02-task-store-api.md` §2.4 约定的视觉一致与协议稳定。

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P10 并经验证后，可进入 P11.
