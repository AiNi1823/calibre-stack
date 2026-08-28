# Calibre-Web UI 升级 — Phase 0：脚手架（建立施工现场基线）

## 0. 目标
- **建立可编辑、可版本控制的「施工现场」**：将 janeczku/calibre-web **0.6.27** 源码 vendored 到 `calibre-stack/calibre-web/`（`cps/` + 打包文件），使其成为本仓库内的真实源码树
- **并入现有自定义**：迁移旧 `deploy/*.patch` / 运行中 site-packages 的自定义（`layout.html`、`uploadprogress.js`、`web.py`、`helper.py`），使 vendored 树与运行中 UI **源码零差异**
- 搭建 Tailwind CSS 构建链（`package.json`、`tailwind.config.js`、`src/input.css`），编译产物 `cps/static/css/tailwind.css`（提交产物，VPS 运行期无需 Node）
- 建立设计令牌（浅色/深色变量），为 P1 Design System 打底
- **Bootstrap CSS → Tailwind**（全量替换，无缝过渡）
- **Bootstrap JS → Alpine**（渐进迁移，见「实施要点」第 5 条）
- **jQuery 暂时保留**，禁止新增 jQuery 代码；现有 jQuery 按页面迁移到 Alpine，待所有依赖迁移完成后再删除
- 保持 SSR 兼容

## 1. 影响项目文件
- **本仓库内（vendored 源码树 `calibre-web/`）**：
  - `cps/templates/base.html`（删 Bootstrap 引用、引入 Alpine、添加主题切换）
  - `cps/static/css/tailwind.css`（构建产物，提交仓库）
  - `cps/static/css/input.css` → 实为 `src/input.css`（Tailwind 源文件）
  - `package.json`、`tailwind.config.js`、`postcss.config.js`（Tailwind 构建链）
  - `cps/static/js/` 中逐步移除 jQuery 代码，改用 Alpine 数据属性
- **calibre-stack（若涉及）**：
  - `async-upload/tasks_page.html`、`upload_page.html`（暂不改，后续 P10 处理）

## 2. 后端改动
- 无。前端行为改动全由前端实现；保持 `web.py`/`db.py`/`helper.py` 完全不变，只改前端模板和静态资源。

## 3. 实施要点
1. **vendored 源码树**：`calibre-stack/calibre-web/` = 上游 0.6.27（tag）完整源码（`cps/` + 打包文件）；剔除运行数据（`library/*.db`、`.key`、`__pycache__`）；不嵌套 `.git`（在上层 `calibre-stack` 管理）
2. **并入自定义基线**：将运行中 `site-packages/calibreweb/cps` 的自定义文件（`templates/layout.html`、`static/js/uploadprogress.js`、`web.py`、`helper.py`）复制进 vendored 树，使两者**源码零差异**（排除第三方静态库/翻译）
3. 在 vendored 根新增 Tailwind 构建链：
   - `package.json`（依赖 tailwindcss、postcss、autoprefixer）
   - `tailwind.config.js`（design tokens: light/dark color vars, font family, radius, shadow；content 扫描 `cps/templates/**/*.html` 与 `async-upload/**/*.html`；`darkMode:'class'`）
   - `src/input.css`（`@tailwind base/components/utilities` + ligth/dark 令牌 + focus-visible + prefers-reduced-motion）
   - `npm install` 后 `npm run build` → 提交 `cps/static/css/tailwind.css`
4. 修改 `cps/templates/base.html`：
   - 删 `<link .../bootstrap.min.css>`、`caliBlur.css`、`style.css`（在 tailwind.css 中已覆盖）
   - 删 Glyphicons 使用（`<span class="glyphicon glyphicon-xxx">`），改用 Alpine 数据属性或 Lucide SVG
   - 在 `<body>` 加 `x-data=""`（Alpine 初始化根），必要处加 `x-show`/`x-transition` 替代 jQuery 动画
   - 加入主题切换按钮：`<button @click="dark = !dark" class="btn btn-primary">`
5. `cps/static/js/` jQuery → Alpine 渐进迁移：
   - **禁止新增 jQuery 代码**：仅在已有 jQuery 函数的页面进行迁移
   - 导航抽屉：先用 `x-show` 替代对应 jQuery 事件绑定；若有复杂逻辑保留 jQuery 临时版本，待后续阶段全面搬迁
   - 模态框：`x-show` + `x-on:keydown.esc` 替代 jQuery `.modal('show')`；逐步搬迁
   - 批量选择：`x-data` 维护 `selected` 数组，`x-on` 处理 checkbox，逐步搬迁 jQuery 版本
   - 表单提交：保留原有 `form` 提交，但取消 `onclick` 中的 jQuery `$.ajax`，改用原生 `form.submit()` 或 `fetch` 配合 Alpine 状态；若存在依赖 jQuery 的复杂表单逻辑，保留 jQuery 版本并注明迁移计划
   - **所有 jQuery 代码应在 P5 前完成迁移到 Alpine**，P5 前未迁移的保留 jQuery 但不得新增
6. **重部署验证**：以 venv 为源执行 `pip install --force-reinstall --no-deps ./calibre-web` 后重启，确保与运行中行为一致

## 4. 回测方法
1. **本地构建**：`cd calibre-web && npm install && npm run build`（产出 `cps/static/css/tailwind.css`）
2. **重装包（vendored 安装）**：`pip install --force-reinstall --no-deps ./calibre-web`
3. **服务重启**：`systemctl restart calibre-web`
4. **功能验证清单**：
   - 页面无 JS 错误（F12 Console 无红字）
   - Sidebar 可见且可点击
   - 主题切换按钮可点击（切换 light/dark，CSS 变量生效）
   - 封面卡片可点击（指向书籍详情）
   - 无控制台 Alpine 错误（`x-show` 等未定义变量）

## 5. 推进标准（进入 P1 的门禁）
- Tailwind CSS 已编译并提交 `cps/static/css/tailwind.css`
- `base.html` 无报错且在浏览器中正常渲染（未 FOUC、无 404 的资源请求）
- Alpine.js 行为基本成立（Sidebar 抽屉可开关，主题切换有效，jQuery 行为未新增）
- 无 `git` 冲突（`git status` 干净，仅 phase0 相关文件被修改）
- jQuery 迁移进度：P0 结束时，不得有新增 jQuery 代码；若项目中仍保留 jQuery，须有明确的迁移计划（见备注）

## 6. 下一步门禁
- P1（布局）：在通过上述验证后，开始实现左侧 Sidebar + Header + 移动端 Drawer（`layout.html` 重写），保持 Alpine 交互连贯。

## 备注
- `cps/templates/base.html` 的改动是本阶段最大的改动，务必保持 `{% extends "layout.html" %}` 等 Jinja2 语法不变，仅在块内改写 HTML/CSS/Alpine
- `cps/static/js/` 的 jQuery->Alpine 搬迁可分步进行，P0 主要完成 `base.html` 的架构互换；后续阶段逐步搬迁具体交互（P3–P5 涉及）

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P0 并经验证后，可进入 P1.