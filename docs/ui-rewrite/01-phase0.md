# Calibre-Web UI 升级 — Phase 0：脚手架

## 0. 目标
- Fork 源仓库 `github.com/janeczku/calibre-web` → `github.com/AiNi1823/calibre-web`，在 master 基础上切分支 `ui-tailwind`（对应版本 0.6.27）
- 搭建 Tailwind CSS 构建链（`package.json`、`tailwind.config.js`、`src/input.css`），编译产物 `cps/static/css/tailwind.css`
- 建立设计令牌（浅色/深色变量），在 `base.html` 中替代 Bootstrap 3 + Glyphicons
- **Bootstrap CSS → Tailwind**（全量替换，无缝过渡）
- **Bootstrap JS → Alpine**（渐进迁移，见「实施要点」第 5 条）
- **jQuery 暂时保留**，禁止在 P0 中新增 jQuery 代码；现有 jQuery 按页面迁移到 Alpine，待所有依赖迁移完成后再删除
- 保持 SSR 兼容

## 1. 影响项目文件
- **Fork 内**：
  - `cps/templates/base.html`（删 Bootstrap 引用、引入 Alpine、添加主题切换）
  - `cps/static/css/tailwind.css`（构建产物，提交仓库）
  - `cps/static/css/input.css`（Tailwind 源文件）
  - `cps/package.json`、`tailwind.config.js`、`postcss.config.js`
  - `cps/static/js/` 中逐步移除 jQuery 代码，改用 Alpine 数据属性
- **calibre-stack（若涉及）**：
  - `async-upload/tasks_page.html`、`upload_page.html`（暂不改，后续 P10 处理）

## 2. 后端改动
- 无。前端行为改动全由前端实现；保持 `web.py`/`db.py`/`helper.py` 完全不变，只改前端模板和静态资源。

## 3. 实施要点
1. Fork `github.com/janeczku/calibre-web` → `github.com/AiNi1823/calibre-web`，切分支 `ui-tailwind`（基于 tag `0.6.27`）
2. 在 fork repo 根目录新增：
   - `package.json`（依赖 tailwindcss、postcss、autoprefixer）
   - `tailwind.config.js`（design tokens: light/dark color vars, font family, radius, shadow）
   - `src/input.css`（@tailwind base; @tailwind components; @tailwind utilities; + 保留必要的 Bootstrap 类覆盖）
3. 在 `cps/static/css/` 中建立 `input.css`，内联 `@tailwind base; @tailwind components; @tailwind utilities`，必要时保留关键 Bootstrap 类的覆盖（如 `.navbar`、`.btn` 的关键样式，防止瞬间 FOUC）
4. 修改 `cps/templates/base.html`：
   - 删 `<link rel="stylesheet" href=".../bootstrap.min.css">`、`<link rel="stylesheet" href=".../caliBlur.css">`、`<link rel="stylesheet" href=".../style.css">`（在 tailwind.css 中已覆盖）
   - 删 Glyphicons 使用（`<span class="glyphicon glyphicon-xxx">`），改用 Alpine 数据属性或 Lucide SVG
   - 在 `<body>` 加 `x-data=""`（Alpine 初始化根），必要处加 `x-show`/`x-transition` 替代 jQuery 动画
   - 加入主题切换按钮：`<button @click="dark = !dark" class="btn btn-primary">`

5. `cps/static/js/` jQuery → Alpine 渐进迁移：
    - **禁止在 P0 中新增 jQuery 代码**：仅在已有 jQuery 函数的页面进行迁移
    - 导航抽屉：先用 `x-show` 替代对应 jQuery 事件绑定；若有复杂逻辑保留 jQuery 临时版本，待后续阶段全面搬迁
    - 模态框：`x-show` + `x-on:keydown.esc` 替代 jQuery `.modal('show')`；逐步搬迁
    - 批量选择：`x-data` 维护 `selected` 数组，`x-on` 处理 checkbox，逐步搬迁 jQuery 版本
    - 表单提交：保留原有 `form` 提交，但取消 `onclick` 中的 jQuery `$.ajax`，改用原生 `form.submit()` 或 `fetch` 配合 Alpine 状态；若存在依赖 jQuery 的复杂表单逻辑，保留 jQuery 版本并注明迁移计划
    - **所有 jQuery 代码应在 P5 前完成迁移到 Alpine**，P5 前未迁移的保留 jQuery 但不得新增

6. `TEMPLATES_DIR` 路径问题：因 fork 源已修改 `cps/templates` 路径或保持一致，确保 `render_template` 能加载新 `base.html`。不涉及 pip 包覆盖问题（因已 fork）。

## 4. 回测方法
1. **本地构建**：`npm install && npx tailwindcss -i ./cps/static/css/input.css -o ./cps/static/css/tailwind.css`
2. **重装包**：`pip install --force-reinstall --no-deps git+https://github.com/AiNi1823/calibre-web.git@ui-tailwind`
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