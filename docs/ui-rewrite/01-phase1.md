# Calibre-Web UI 升级 — Phase 1：Design System

## 0. 目标
- 确立完整的 Design System，作为后续所有 UI 组件的唯一权威来源
- 定义浅色/深色设计令牌（变量）、排版、间距、边界、组件样式
- 确保三端（Desktop/Tablet/Mobile）视觉一致性
- 所有后续阶段（P2-P11）必须复用这些标准，禁止自行发明样式
- 实现 `class="dark"` 切换，以及响应式断点，使其贯穿全篇而非临时加入

## 1. 影响项目文件
- **Fork 内**：
  - `cps/static/css/tailwind.config.js`（设计令牌：light/dark 调色板、字体、断点、radius、shadow）
  - `cps/static/css/input.css`（Tailwind 指令 `@tailwind base; @tailwind components; @tailwind utilities`，含所有组件基础样式）
  - `cps/templates/base.html`（引入 Alpine.js、`x-data` 根数据 `dark` / `sidebarOpen`，保持 `{% extends "layout.html" %}`）
  - `cps/templates/layout.html`（侧边栏/页脚使用 Design System 组件类；保持与 base.html 的变量继承）
  - `cps/static/css/tailwind.css`（编译产物，提交仓库）

- **calibre-stack（暂不涉及）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。Design System 完全由前端模板与静态资源决定，`web.py`/`db.py`/`helper.py` 完全不动。

## 2. 实施要点

### 1. Design Token（设计令牌）
在 `tailwind.config.js` 中预声明：

**Light:**
```
--background:#F8F8F7  --surface:#FFFFFF  --surface-secondary:#F3F3F1
--border:#E5E5E3     --text-primary:#1F1F1F  --text-secondary:#737373  --text-muted:#A3A3A3
--primary:#2563EB    --danger:#DC2626  --success:#16A34A
```

**Dark（`class="dark"`）：**
```
--background:#111111  --surface:#181818  --surface-secondary:#202020
--border:#2A2A2A     --text-primary:#E5E5E5  --text-secondary:#A3A3A3  --text-muted:#737373
```
约束：主色仅用于当前导航/主按钮/链接/选中/进度/focus；封面圆角 4–6px；动画 100–200ms。

### 2. 组件库（全部通过 Tailwind 类 + Alpine 状态实现）

| 组件 | 规范 |
|------|------|
| **Button** | 默认/primary/outline/danger 变体；`focus-visible: outline-2 focus-visible:ring-2`；`disabled: opacity-50 cursor-not-allowed` |
| **Input** | 文本输入框；`focus-visible` 状态有明显轮廓；`resize-none` 防止用户调整尺寸 |
| **Badge** | 状态徽章（未读/在读/已读），尺寸 `text-xs` / `px-2` / `py-1` / `rounded-2`；颜色沿用 `gray-100` / `green-100` / `blue-100` |
| **BookCard** | 封面 `rounded-4` / `object-cover` / `lazy-loading`；标题单行截断 `.line-clamp-1`；作者/系列小号灰色 |
| **Table** | 交替行 `bg-white` / `bg-gray-50`；状态徽章列；操作按钮列 |
| **Dialog** / **Drawer** / **Dropdown** | 遮罩层、Esc 关闭、`aria-label`、`focus-visible` 焦点轮廓 |
| **BookCover** | 封面组件 `rounded-4` / `transition-transform` / `hover:scale-105` |

### 3. 响应式断点
在 `tailwind.config.js` 中：
```js
screens: { sm: '640px', md: '768px', lg: '1024px', xl: '1200px' }
```
原则：Desktop（>=1200px）左侧 Sidebar + 内容区；平板（768–1199px）Sidebar 折叠为汉堡菜单，内容区自动宽度；移动端（<768px）Sidebar 完全隐藏，顶部含菜单按钮，Drawer 全宽滑出。

### 4. 主题切换
- `<html>` 标签 `class="dark"` 控制深色模式
- 顶部主题切换按钮：`<button @click="dark = !dark" class="btn btn-sm btn-outline" aria-label="切换护眼模式"`
- `x-data=" { dark: false }"` 在 `base.html` 根层维护
- 所有组件通过 `dark:` 前缀自动切换颜色（按钮背景、边框、文字、背景）

### 5. 使用原则
- **所有新增模板片段必须复用上述组件**（Button、Input、Badge、BookCard、Table、Dialog 等），不得自行编写 inline CSS/JS
- **禁止**在任何页面自行定义颜色值、间距、圆角，必须引用 Design Token
- **深色模式**必须在组件设计之一开始即支持，而非临时在最后阶段添加
- **响应式断点**必须在组件库层面预先定义，而非每个页面单独写媒体查询

## 3. 后端改动
- 无。全部由前端模板与静态资源决定。

## 3. 回测方法
1. **本地构建**：`npm install && npx tailwindcss -i ./cps/static/css/input.css -o ./cps/static/css/tailwind.css`
2. **功能验证清单**：
   - Tailwind 已编译，`tailwind.css` 已提交仓库
   - `base.html` 加载正常，`x-data` 中 `dark` 变量可用
   - 所有常用组件（Button、Input、Badge、BookCard）按 Design Token 渲染
   - `class="dark"` 切换 light/dark，CSS 变量生效
   - 响应式布局：Desktop/Tablet/Mobile 三端布局均无折层
   - 无控制台 Alpine 错误

## 4. 推进标准（进入 P2 的门禁）
- Design Token 在 `tailwind.config.js` 中已声明，`input.css` 编译无误
- `base.html` 中 `x-data` 维护 `dark` 变量，`layout.html` 继承生效
- 所有组件渲染符合 Design System 规范（检查圆角 4–6px、颜色变量、间距）
- `class="dark"` 在三端均可开启/关闭，CSS 变量生效
- 无控制台 JS 错误

## 4. 下一步门禁
- P2（App Shell）：在通过上述 Design System 验证后，开始实现左侧 Sidebar + Header + 移动端 Drawer（`layout.html` 重写），保持 Alpine 交互连贯，所有组件复用 P1 中的 Design System。

## 备注
- 本阶段是整个 UI 升级的**基石**。后续所有阶段（P2-P11）的组件定义、样式、交互均必须复用本阶段的 Design System，不得自行发明。
- 若后续发现 Design System 缺失某组件，必须在修改前先在本文档中补充，再波及后续阶段。
- `rounded-4xl` 在任何上下文中一律**不使用**，封面/卡片仅使用 `rounded-4` / `rounded` / `rounded-lg`（对应 4–6px）。
- `focus-visible` 焦点轮廓是强制要求，任何可交互元素必须有明显的焦点状态。

---
> **施工文档**：影响文件/回测/推进标准如上。完成 P1 并经验证后，可进入 P2.