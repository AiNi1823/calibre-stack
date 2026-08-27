# Calibre-Web UI 升级 — Phase 5：暗色模式 + 响应式 + 无障碍

## 0. 目标
- 实现真正的深色模式（`class="dark"`），而非原有的 blur/plex 风格
- 确保桌面（>=1200px）、平板（768–1199px）和移动端（<768px）三端布局均匀
- 符合无障碍访问标准：焦点态、aria-label、键盘导航、色彩对比度
- 所有组件在三端保持一致的视觉与交互

## 1. 影响项目文件
- **Fork 内**：
  - `cps/templates/base.html`（添加 `dark` 类切换按钮，及 `x-data` 维持主题状态）
  - `cps/templates/layout.html`（在移动端实现抽屉，三端断点控制）
  - `cps/static/css/tailwind.css` / `input.css`（深色模式变量、响应式断点、焦点样式）
  - `cps/static/js/`（微调 Alpine 数据，确保 `dark` 状态在三端共享）

- **calibre-stack（暂不涉及）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。仅在 `base.html` 中添加主题切换按钮和 `x-data` 数据维护，不涉及业务逻辑。

## 2. 实施要点
1. **深色模式实现**：
   - `class="dark"` 在 `<html>` 标签上控制；Tailwind 内置 `dark:` 前缀使用
   - 顶部主题切换按钮：`<button @click="dark = !dark" class="btn btn-sm btn-outline">`
   - `tailwind.config.js` 中预先声明浅色/深色变量（沿用 Phase 0 设计令牌）
   - 所有组件通过 `dark:` 前缀自动切换颜色（按钮背景、边框、文字、背景）

2. **响应式断点**：
   - `>=1200px`：桌面端——左侧 Sidebar（220px）+ 内容区
   - `768–1199px`：平板端——Sidebar 折叠为汉堡菜单，内容区宽度自动
   - `<768px`：移动端——Sidebar 完全隐藏，顶部含菜单按钮，Drawer（抽屉）从左侧滑出
   - 在 `tailwind.config.js` 的 `theme.screens` 中预先声明断点

3. **无障碍访问**：
   - **焦点样式**：`focus-visible` 类，边框颜色 `#2563EB`，宽度 `2px`，轮廓 `none`
   - **aria-label**：导航按钮、收起/展开按钮、主题切换按钮均添加 `aria-label`
   - **键盘导航**：`Tab` 顺序自然，`Esc` 关闭抽屉/模态框
   - **色彩对比度**：`color-contrast` utility，确保浅色背景下深色文字、深色背景下浅色文字

4. **跨端状态同步**：
   - `x-data=" { dark: false, sidebarOpen: false }"` 在 `base.html` 根层维护
   - `layout.html` 通过 `x-show`/`x-transition` 根据 `sidebarOpen` 控制 Sidebar/Drawer
   - `maintain` 主题切换 `dark` 变量在所有页面一致

## 1. 影响项目文件
- **Fork 内**：
  - `cps/templates/base.html`（添加主题切换按钮、`x-data` 根数据）
  - `cps/templates/layout.html`（三端断点控制 Sidebar/Drawer）
  - `cps/static/css/tailwind.css` / `input.css`（深色模式变量、响应式断点、焦点样式）
  - `cps/static/js/`（微调 Alpine 数据，确保 `dark` 状态同步）

- **calibre-stack（暂不涉及）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。`base.html` 与 `layout.html` 仅在前端模板层改写，后端路由和数据完全不动。

## 2. 实施要点
1. **主题切换按钮**：
   - 放置在 Header 右侧
   - 点击切换 `dark` 变量，Tailwind 自动切换颜色集
   - 按钮 `aria-label="切换护眼模式"`，`x-data` 中 `dark` 状态同步

2. **响应式断点**：
   - 使用 Tailwind `screens: { sm: '640px', md: '768px', lg: '1024px', xl: '1200px' }`
   - Sidebar 在 `md`（768px）以上可见，`md` 以下自动转为抽屉
   - 移动端（<768px）顶部含菜单按钮 `бургер`，点击后 Drawer 从左侧 `transform-x-0` 进入

3. **焦点样式**：
   - `Tailwind` 预置 `focus-visible` 类：`focus-visible: outline-2 focus-visible:outline-2 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-2 focus-visible:ring-color`
   - 确保键盘导航时每个可交互元素都有明显的焦点轮廓

4. **色彩对比度检查**：
   - 使用 `contrast-contrast` utility 或手动验证：浅色背景下深色文字对比度 ≥ 4.5:1，深色背景下浅色文字对比度 ≥ 4.5:1
   - `tailwind.config.js` 中 `theme.extend.colors` 已预先声明满足 WCAG 2.1 AA 标准的颜色值

## 1. 回测方法
1. **本地构建**：同上
2. **浏览器验证**（分三端测试）：
   - **Desktop (1200px+)**：左侧 Sidebar  visible，主题切换按钮可点击，焦点轮廓明显
   - **Tablet (768–1199px)**：Sidebar 折叠，汉堡菜单出现，点击后 Drawer 滑出
   - **Mobile (<768px)**：顶部含菜单按钮，Drawer 全宽滑出，焦点轮廈可见
   - **色彩对比度**：人工或工具检查关键元素（按钮、文字、背景）的对比度
   - **焦点导航**：`Tab` 遍历所有可交互元素，`Esc` 关闭抽屉/模态框

## 3. 推进标准（进入 P6 的门禁）
- 深色模式在三端均可开启/关闭，CSS 变量生效
- 三端布局（桌面/平板/移动）均正常，无断层
- 焦点轮廈可见，`aria-label` 完整，`Esc` 关闭抽屉/模态框
- 色彩对比度符合 WCAG 2.1 AA 标准

## 3. 下一步门禁
- P6（可访问性 + 性能）：键盘导航、加载延迟、图片占位符

## 3. 备注
- `base.html` 中的 `dark` 变量状态在所有子页面通过 `x-data` 继承，确保主题切换不出现“卡顿”或“不同步”
- `tailwind.config.js` 的 `darkMode: 'class'` 模式，意味着仅当 `<html>` 有 `class="dark"` 时才应用深色样式，不会影响其他页面

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P5 并经验证后，可进入 P6.