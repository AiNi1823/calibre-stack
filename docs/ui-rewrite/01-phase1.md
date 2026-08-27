# Calibre-Web UI 升级 — Phase 1：布局

## 0. 目标
- 在 `layout.html` 中实现左侧 Sidebar（220–240px） + Header + 内容区
- 移动端（<768px）自动折叠为 Drawer（抽屉）模式
- Header 包含：搜索框 / 用户头像 / 主题切换 / 导航入口
- 保持 Alpine.js 交互连贯（继承 Phase 0 的 `base.html` 行为）
- 侧边栏与内容区采用 CSS Grid / Flexbox 栅格，在桌面端 220px，移动端自动全宽

## 1. 影响项目文件
- **Fork 内**：
  - `cps/templates/layout.html`（核心改写：从顶部 navbar 改为左侧 Sidebar + 内容区；移动端加 media query 控制 Sidebar/Drawer）
  - `cps/templates/base.html`（继承 `layout.html`，保持 Alpine 根数据 `x-data`，确保主题变量 `dark` 在两模式下共享）
  - `cps/static/css/tailwind.css` / `input.css`（可能须扩展媒体查询，见下 '实施要点'）
  - `cps/static/js/`（若有必要，微调 Alpine 数据属性，确保 Sidebar/Drawer 状态在桌面/移动间同步）

- **calibre-stack（暂不涉及）**：
  - `async-upload/tasks_page.html`、`upload_page.html`（保持不变）

## 2. 后端改动
- 无。`layout.html` 与 `base.html` 仅改写 HTML structure + Tailwind 类；后端路由、数据查询完全不动。

## 2. 实施要点
1. **Sidebar 结构**：
   - 宽度固定 220px（桌面） / 全宽（移动端）
   - 包含：首页 / 书库 / 最近阅读 / 收藏 / 作者 / 分类 / 标签 / 系列 / 设置 / 退出
   - 每个导航项用 `x-show` 控制对应内容区的显示/隐藏
   - 移动端点击 Sidebar 图标，Sidebar 收起，内容区宽度自动扩展；再次点击或点击遮罩层，返回

2. **Header 结构**：
   - Logo / 站点名称（居中或左对齐）
   - 搜索框：`x-on:input` 触发 `search.simple_search`（保持原有行为）
   - 用户菜单：下拉列表，含 个人资料 / 设置 / 退出
   - 主题切换按钮：`@click="dark = !dark"`，状态在桌面/移动间共享

3. **移动端 Drawer**：
   - `x-show` 绑定在 `<body>` 或特定容器，`x-transition` 给出淡入淡出效果
   - 遮罩层 `x-show` 控制点击关闭
   - 侧边栏在移动端 `transform: translateX(-100%)` / `translateX(0)` 切换

4. **Tailwind 媒体查询**：
   - `@media (min-width: 768px)`：Sidebar 可见（`w-20` / `w-64` 对应 220–240px）
   - `@media (max-width: 767px)`：Sidebar 隐藏，通过汉堡菜单按钮触发 Drawer
   - 在 `tailwind.config.js` 或 `input.css` 中添加对应断点类

5. **Alpine 状态共享**：
   - 定义 `dark`（主题）、`sidebarOpen`（Sidebar 打开/关闭状态）在 `base.html` 的 `x-data` 中
   - 子模板 `layout.html` 继承这些变量，确保主题切换和 Sidebar 状态在任意页面一致

## 2. 后端改动
- 无。所有路由 URL、`auth_request` 鉴权、Calibre-Web 原有功能完全不动。

## 3. 回测方法
1. **本地预览**：`npm run dev`（或 `npx tailwindcss -i ./cps/static/css/input.css -o ./cps/static/css/tailwind.css` 后重启）
2. **浏览器验证**（分三端）：
   - **Desktop（1200px+）**：Sidebar 固定 220px，内容区 `wcalc(100% - 220px)`；Header 固定；主题切换生效
   - **Tablet（768–1199px）**：Sidebar 折叠为汉堡菜单图标，点击后 Drawer 从左侧滑出
   - **Mobile (<768px)**：Header 仅含搜索/用户/主题，点击菜单按钮 Drawer 全宽滑出
3. **功能验证清单**：
   - Sidebar/Drawer 在三端均可打开/关闭
   - 搜索框聚焦后能输入并触发搜索
   - 主题切换按钮在三端均能切换 light/dark
   - 无控制台 Alpine 错误（`x-show` 变量未定义等）
   - 点击遮罩层或 Sidebar 外部区域，Sidebar/Drawer 关闭

## 4. 推进标准（进入 P2 的门禁）
- `layout.html` 在 Desktop/Tablet/Mobile 三端均能正常渲染，无 JS 错误
- Sidebar 与内容区的宽度比例符合设计（桌面 220px，移动全宽）
- 主题切换在三端生效
- Alpine 无控制台错误
- `git status` 仅显示 `layout.html`、`base.html`、`tailwind.css`（及相关子文件）被修改

## 4. 下一步门禁
- P2（书库页面）：重皮肤 `grid.html` / `list.html`（封面、状态徽章、Grid⇄List 切换），保持 Alpine 交互连贯

## 备注
- `layout.html` 与 `base.html` 的改动必须保持 `{% extends "base.html" %}` / `{% block body %}` 等 Jinja2 结构不变，仅在块内改写 HTML structure + Tailwind 类
- 若涉及 `cps/static/js/` 的微调，建议先在 `base.html` 中写好 Alpine 数据属性，再在 `layout.html` 中使用；避免一次性大改所有 JS 文件
- 媒体查询阈值 768px 可根据实际视觉效果微调，但原则上 Desktop 侧边栏 >= 768px，移动端 < 768px

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P1 并经验证后，可进入 P2。