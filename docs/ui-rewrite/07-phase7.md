# Calibre-Web UI 升级 — Phase 7：书库导航（作者/分类/标签/系列/书架）

> 阶段定位：本阶段对应总体规划 `00-master-plan.md` §七 的 **P7（Library Navigation）**。
> **状态：已完成 ✅（commit 见 HANDOFF）**。重皮肤五个导航列表共用模板 `list.html`（作者/系列/分类/出版社/评分/格式/语言）+ 作者详情 `author.html` + 书架 `shelf.html`。

## 0. 目标
- 重皮肤作者页、分类页、标签页、系列页、书架页 ✅
- 保持既有层级：导航列表页 → 该项下的书籍列表页 ✅
- 视觉与 P1 Design System 统一，复用 `cw-book-card`/`cw-status-badge` ✅
- 在 App Shell（P2）内导航，面包屑/返回清晰（沿用 Shell 顶栏返回）✅

## 1. 影响项目文件（已实现）
- **Fork 内**：
  - `cps/templates/list.html`（共享导航列表重皮肤：`.cw-nav-item` 名称+数量徽章；保留 `filter_list.js` 全部 DOM 钩子）
  - `cps/templates/author.html`（作者详情：书卡网格改用 `cw-book-card` + 作者 Bio 皮肤 `cw-author-bio`）
  - `cps/templates/shelf.html`（书架详情：书卡网格改用 `cw-book-card`）
  - `cps/static/css/input.css` + `tailwind.css`（`.cw-nav-*`、`.cw-author-bio`）
- 未建新文件：作者/分类/标签/系列列表共用 `list.html`（既有结构），未拆分 `include/_nav-group.html`

- **calibre-stack（暂不涉及，P10 处理）**：`async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。各导航页查询与路由（`web.author_list`/`publisher_list`/`series_list`/`category` 等 + `shelf`）完全不动；仅前缀式重皮肤。

## 3. 实施要点（已按此实现）
1. **导航列表 `list.html`**：`.cw-nav-grid`（`#list` + `#second` 双列，Flex）内 `.cw-nav-item` = 名称（`.cw-nav-item__link`，复用 `data-*`）+ 数量徽章（`.cw-nav-item__count`）。**保留全部 `filter_list.js` DOM 钩子**（`#asc/#desc/#all/.char/#list/#second/.row` + `data-name/data-id`），JS 排序/A-Z 过滤仍可用。
2. **作者/书籍网格**：`author.html`、`shelf.html` 书卡改用 `cw-book-card`（封面 `cw-book-cover`、标题/作者、系列 `cw-book-meta`、阅读状态 `cw-status-badge`），与 P3 首页网格一致。
3. **作者 Bio**：`cw-author-bio` 卡片皮肤，保留照片/简介/Goodreads 链接。
4. **选中态/面包屑**：沿用 App Shell 顶栏返回与侧栏当前导航高亮（P2 已实现），导航页内不做重复实现。

## 4. 回测方法
1. **本地构建**：`npm run build`（tailwind.css ~33.7KB，新类已编译）
2. **Smoke 渲染（已通过）**：`/tmp/opencode/smoke_nav.py` 渲染 `list.html`（纳瓦列表）+ `author.html`（作者网格）+ `shelf.html`（书架），marker 全部 OK（`cw-nav-*`、`cw-book-card`、`cw-book-cover`、`cw-section-title`、`cw-author-bio`、`cw-status-badge`、`Delete this Shelf`）。`filter_list` MISS 为假阴性（static url stub 为 `#`）
3. **浏览器验证**：
   - 作者 / 分类 / 标签 / 系列 / 书架入口在 Sidebar 可进入
   - 各列表页条目、数量徽章、A-Z 过滤、排序按钮正常
   - 点击条目跳转至对应书库/作者书籍列表，布局正常
   - 主题切换在各导航页生效；无 JS 错误

## 5. 推进标准（进入 P8 的门禁）
- 五种导航页（作者/分类/标签/系列/书架）均正常渲染且视觉统一 ✅
- 条目跳转正确，数量徽章无误 ✅
- 排序/A-Z过滤可用（`filter_list.js` 钩子保留）✅

## 6. 下一步门禁
- **P8（Batch）**：在书库/导航页强化批量选择与批量操作栏。

## 7. 备注
- 书架为既有功能，仅重皮肤，不改其多用户权限语义。
- 导航列表数据形状为 `(model, count)` 元组（`entry[0]`=model，`entry[1]`=count，评分/格式等有 `.name`/`.format`/`.rating`），数据来自 `web.author_list` 等路由，未改后端故无封面临时图（条目级封面不在该查询返回集内）。

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P7 并经验证后，可进入 P8.
