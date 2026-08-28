# Calibre-Web UI 升级 — Phase 2：App Shell（应用外壳）

> 阶段定位：本阶段对应总体规划 `00-master-plan.md` §七 的 **P2（App Shell）**。
> 在 P1 已锁定的 Design System 上建立全站骨架：左侧 Sidebar、Header、全局搜索入口、移动端 Drawer、跨端响应式。

## 0. 目标
- 重写 `layout.html` 为全站统一「应用外壳」：左侧 Sidebar（220–240px）+ Header + 内容区
- 桌面端（`xl: 1200px` 及以上）Sidebar 常驻；平板/移动端（`< md`）Sidebar 折叠为 Drawer（抽屉），顶部汉堡按钮唤起
- 在 Header 提供全局搜索入口（`Ctrl+K` 快捷键在此挂接，详情页与脚本在 P6 完善）
- 主题切换按钮（`class="dark"`）在 Header 常驻（令牌来自 P1）
- 所有子页面通过继承 `layout.html` 自动获得一致外壳，`dark` / `sidebarOpen` 状态跨页共享

## 1. 影响项目文件
- **Fork 内**：
  - `cps/templates/layout.html`（完整重写为 App Shell：Sidebar + Header + Drawer + 内容区）
  - `cps/templates/base.html`（保持 `{% extends "layout.html" %}` 与根 `x-data` 状态：`dark`、`sidebarOpen`）
  - `cps/templates/include/_sidebar.html`（新增：导航项组件，含 aria 与选中态）
  - `cps/templates/include/_header.html`（新增：顶部栏，含搜索、主题切换、账户菜单）
  - `cps/static/css/tailwind.config.js` / `input.css`（App Shell 相关工具类：`.sidebar`、`.drawer`、`.header-bar`）

- **calibre-stack（暂不涉及，P10 处理）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。`layout.html`/`base.html` 仅前端骨架改写；后端路由、导航链接、权限判断完全不动。

## 3. 实施要点

### 3.1 Sidebar（桌面常驻 + 移动端 Drawer）
- 桌面：`xl`（≥1200px）常驻 `aside.fixed`（宽 220–240px）；内容区 `ml-[sidebar-width]`
- 平板/移动：`< md`（768px）Sidebar 转 Drawer，初始 `x-transition` 从左侧滑出，遮罩层覆盖内容区
- 导航项：书库 / 搜索 / 作者 / 分类 / 标签 / 系列 / 书架 / 任务（`/tasks`）/ 管理（`/admin`）
- 当前页高亮（`aria-current="page"` + 主色背景）
- Drawer 关闭：点遮罩、`Esc`、选完导航项后自动收起

### 3.2 Header
- 左侧：移动端「汉堡」按钮（`< md` 显示），桌面隐藏
- 中部/右侧：全局搜索框（`Ctrl+K` 唤起，P6 完善行为）、主题切换按钮（`@click="dark = !dark"` + `aria-label="切换护眼模式"`）、账户菜单
- 搜索框在移动端可收进 Drawer 或图标唤起

### 3.3 跨端状态
- 根 `x-data="{ dark: false, sidebarOpen: false }"` 在 `base.html` 维护
- `layout.html` 通过 `x-show` / `x-transition` 根据 `sidebarOpen` 控制 Sidebar/Drawer
- `dark` 状态持久化（localStorage）并在所有子页面保持一致

## 4. 回测方法
1. **本地构建**：`npm install && npx tailwindcss -i ./cps/static/css/input.css -o ./cps/static/css/tailwind.css`
2. **浏览器/Playwright 分端验证**：
   - Desktop（≥1200px）：Sidebar 常驻，Header 搜索/主题/账户可用
   - Tablet（768–1199px）与 Mobile（<768px）：Sidebar 折叠，汉堡打开 Drawer，遮罩点击 / `Esc` 关闭
   - 主题切换在任意子页面生效且状态跨页保持
   - `Ctrl+K` 唤起搜索框焦点
3. **无控制台 JS 错误**（Alpine 未定义变量等）

## 5. 推进标准（进入 P3 的门禁）
- 桌面/平板/移动三端外壳布局正确，无断层
- Drawer 打开/关闭流畅（遮罩、汉堡、`Esc`）
- 导航项均可跳转且当前项高亮
- 主题切换跨页一致；无控制台错误

## 6. 下一步门禁
- **P3（Library）**：在 App Shell 之上重皮肤网格/列表书库页。

## 7. 备注
- App Shell 是后续所有页面的「皮肤载体」，务必与 P1 Design System 的组件/令牌严格一致。
- `sidebarOpen` 与 `dark` 状态继承机制是本阶段关键，任何子页面不得另辟状态管理。

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P2 并经验证后，可进入 P3.
