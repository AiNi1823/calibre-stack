# Calibre-Web UI 升级 — Phase 6：搜索 + 筛选（Search / Filter）

## 0. 目标
- 在 Header 添加 **Ctrl+K** 唤起全局搜索的快捷键
- 搜索结果页面支持：书名、作者、ISBN、标签、系列、出版社、出版社
- 筛选器采用 **Dropdown / Popover** 形式，Desktop 端用顶部 Filter Bar，移动端用 Bottom Sheet / Drawer
- 搜索结果页面保持高信息密度，不堆砌无效卡片

## 1. 影响项目文件
- **Fork 内**：
  - `cps/templates/search.html`（重写：搜索框、结果页布局、无结果提示）
  - `cps/templates/search_form.html`（新增：紧凑的搜索输入框组件）
  - `cps/templates/include/_search-filter.html`（新增：筛选器组合框）
  - `cps/templates/include/_search-skeleton.html`（新增：占位加载动画）
  - `cps/static/css/tailwind.css` / `input.css`（新增搜索相关样式：`.search-input`、`.result-item`、`.no-result`）
  - `cps/static/js/`（Alpine.js 绑定 Ctrl+K、搜索交互）

- **calibre-stack（暂不涉及）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。搜索 API `simple_search`、`advanced_search` 完全不动；仅前端展示层改写。

## 2. 实施要点
1. **Header 搜索框**：
   - `Ctrl+K` 唤起焦点（Alpine `@keydown.ctrl.k`）
   - 输入实时筛选 `cps/web.py` 的 `search_results`，无需刷新页
   - `placeholder`：「搜索书名、作者、ISBN、标签...」

2. **搜索结果页**：
   - 结果按相关性排序，展示：封面、标题、作者、简介片段
   - `no-result` 状态：当无匹配时显示「没有找到相关书籍」「尝试调整筛选条件」
   - 每行：`.result-item`（封面 `.cover`、标题 `.title`、作者 `.author`、简介 `.summary`）

3. **筛选器**：
   - Desktop：顶部 `.filter-bar`（筛选：作者、分类、标签、语言、格式、阅读状态）
   - Mobile：`menu` 触发 `.bottom-sheet`（筛选面板）
   - 筛选条件通过 `query` 参数拼接传递给后端（如 `?author=xxx&tag=xxx`）

4. **Alpine 交互**：
   - `x-show` 控制搜索结果的显隐
   - `x-on:input` 实时筛选
   - `Esc` 键关闭搜索框

## 2. 后端改动
- 无。搜索逻辑完全由前端驱动，后端仅提供 `search_results` 数据接口（已存在，不动）。

## 3. 回测方法
1. **本地构建**：同上
2. **浏览器验证**：
   - `Ctrl+K` 唤起焦点并定位到输入框
   - 输入关键字（如「西游」），结果列表即时出现，匹配书名/作者/ISBN/标签
   - `Esc` 键关闭搜索框，焦点返回原位置
   - 点击结果项跳转至书籍详情页
   - 筛选器Desktop/移动端均可正常使用，筛选后结果正确

## 3. 推进标准（进入 P7 的门禁）
- Ctrl+K 正常唤起并聚焦输入框
- 搜索结果匹配书名/作者/ISBN/标签
- 筛选器Desktop/移动端均可使用，筛选后结果正确
- 无控制台 JS 错误

## 3. 下一步门禁
- P7（书库导航）：作者 / 分类 / 标签 / 系列 / 书架

## 3. 备注
- 搜索结果中，对 `isbn`、 `出版社`、 `系列` 的匹配优先级低于书名/作者，避免误匹配。
- 移动端筛选器高度有限，仅保留「分类」和「语言」两个最常用条件，其他条件在 Desktop 端展开。

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P6 并经验证后，可进入 P7.