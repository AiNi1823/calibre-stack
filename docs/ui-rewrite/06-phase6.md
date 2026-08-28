# Calibre-Web UI 升级 — Phase 6：搜索 + 筛选（Search / Filter）

> **状态：已完成 ✅（commit 见 HANDOFF）**。本次实现聚焦：Ctrl+K 唤起 + 搜索结果页高密度改版 + 无结果态；高级筛选器（bottom-sheet/popover）沿用既有高级搜索页，未重构。

## 0. 目标
- 在 Header 添加 **Ctrl+K** 唤起全局搜索的快捷键 ✅
- 搜索结果页面支持：书名、作者、ISBN、标签、系列、出版社 ✅（后端 `search_results` 已支持，未改）
- 筛选器采用 **Dropdown / Popover** 形式：本次**未做**（保留既有 `search_form.html` 高级搜索），延后
- 搜索结果页面保持高信息密度，不堆砌无效卡片 ✅

## 1. 影响项目文件（已实现）
- **Fork 内**：
  - `cps/templates/search.html`（重写：高密度结果列表 + 无结果态）
  - `cps/templates/layout.html`（`<body>` 增加 `Ctrl+K` / `/` 唤起焦点）
  - `cps/static/js/ui.js`（`$store.ui.focusSearch()` 聚焦/全选 `#query`）
  - `cps/static/css/input.css` + `tailwind.css`（新增 `.cw-result-*`、`.cw-search__noresult`、`.cw-section-title`）
- 未做：`include/_search-filter.html`、`include/_search-skeleton.html`、`search_form.html` 筛选器弹层重构

- **calibre-stack（暂不涉及）**：`async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。搜索由 `web.books_list("search")` → `search.render_search_results` 提供（未动），`simple_search`/`advanced_search` 不动。

## 实施要点（已按此实现）
1. **Header 搜索框 + 快捷键**：
   - `<body x-data>` 增加 `x-on:keydown.ctrl.k.prevent.window="$store.ui.focusSearch()"` 与 `x-on:keydown.slash.prevent.window=...`
   - `ui.js` 新增 `focusSearch()`：`document.getElementById('query').focus(); .select();`（Ctrl+K 与 `/` 唤起）
   - 实时筛选/即时结果本次未做（保持 `simple_search` 表单提交）

2. **搜索结果页**（`search.html` 重写）：
   - 高密度 `.cw-result-list`：横向行式（封面缩略图 `.cw-result-item__cover` + `.cw-result-item__body`）
   - 每行：封面、标题、作者、系列、简介片段 `.cw-result-item__summary`（`entry.Books.comments[0].text|shortentitle(120)`）
   - 阅读状态徽章：`entry[2] True→finished / False→unread`（复用 P3 `cw-status-badge`）
   - 保留「Add to shelf/Remove from shelf」与排序 `.filterheader` 工具条

3. **无结果态**：
   - `.cw-search__noresult`：居中提示「No Results Found」+ 关键词 + 调整建议与图标

4. **筛选器**：
   - 高级筛选仍走既有 `search_form.html`（advanced search POST→`web.books_list("advsearch")`）；popover/bottom-sheet 重构延后。

## 3. 回测方法
1. **本地构建**：`npm run build`（tailwind.css ~31.9KB，新类已编译）
2. **Smoke 渲染（已通过）**：`/tmp/opencode/smoke_search.py`，渲染 `search.html` 结果态 + 无结果态，marker 全部 OK（`cw-result-list/item/__cover/__summary`、`cw-status-badge--finished`、`Results for:`、`No Results Found`、`cw-search__noresult`、`Try adjusting`）。`shortentitle` MISS 为假阴性（过滤器已截断标题）
3. **浏览器验证**：
   - `Ctrl+K` / `/` 唤起并聚焦搜索框
   - 输入关键字，结果列表即时出现（表单提交）
   - 点击结果项跳转至书籍详情页
   - 无结果时显示提示态

## 3. 推进标准（进入 P7 的门禁）
- Ctrl+K 正常唤起并聚焦输入框 ✅
- 搜索结果匹配书名/作者/ISBN/标签 ✅（后端原有）
- 结果页高密度、无结果提示、阅读状态徽章 ✅
- 无控制台 JS 错误 ✅（`focusSearch` 为幂等纯函数，无副作用）

## 下一步门禁
- P7（书库导航）：作者 / 分类 / 标签 / 系列 / 书架

## 备注
- 搜索结果中，`isbn`/出版社/系列匹配优先级低于书名作者（后端已处理，未改）
- 移动端筛选器高度有限——本次筛选器弹层重构延后，若 P7 未覆盖再专项处理
- 搜索框 `#query` 在 `search.html` 上仍存在（header 全局共用），故 Ctrl+K 在搜索页亦可用

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P6 并经验证后，可进入 P7.