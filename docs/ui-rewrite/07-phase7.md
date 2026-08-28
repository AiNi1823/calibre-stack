# Calibre-Web UI 升级 — Phase 7：书库导航（作者/分类/标签/系列/书架）

> 阶段定位：本阶段对应总体规划 `00-master-plan.md` §七 的 **P7（Library Navigation）**。
> 重皮肤书库的纵向导航页面：作者、分类、标签、系列、书架，保持既有数据组织不变。

## 0. 目标
- 重皮肤作者页（authors）、分类页（categories）、标签页（tags）、系列页（series）、书架页（shelves）
- 保持既有层级：导航列表页（如所有作者）→ 该项下的书籍列表页
- 视觉与 P1 Design System 统一，复用 `_book-card` / `_status-badge` 组件
- 在 App Shell（P2）内导航，面包屑/返回清晰

## 1. 影响项目文件
- **Fork 内**：
  - `cps/templates/authors.html`（作者列表，重皮肤）
  - `cps/templates/categories.html`（分类列表，重皮肤）
  - `cps/templates/tags.html`（标签列表，重皮肤）
  - `cps/templates/series.html`（系列列表，重皮肤）
  - `cps/templates/shelf/`（书架列表与详情，重皮肤）
  - `cps/templates/include/_nav-group.html`（复用/新增：纵向条目组组件：封面缩略、名称、数量徽章）
  - `cps/static/css/tailwind.config.js` / `input.css`（纵向条目组样式）

- **calibre-stack（暂不涉及，P10 处理）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。各导航页的查询与路由（`web.authors`/`web.categories`/`web.tags`/`web.series`/`web.shelf`）完全不动；仅前缀式重皮肤。

## 3. 实施要点
1. **条目组**：`.nav-group` 列表项 = 缩略封面（`rounded-4`）+ 名称 + 数量徽章（`Badge` 组件，`text-xs`/`px-2`/`py-1`）
2. **网格/列表**：导航页用紧凑列表（高信息密度），点击跳转该项下的书库列表（复用 P3 网格/列表）
3. **面包屑**：`Home > 系列 > 系列名` 等，提供返回
4. **选中态**：当前浏览的导航项高亮
5. **书架**：保留「我的书架 / 公共书架」，仅重皮肤

## 4. 回测方法
1. **本地构建**：同上
2. **浏览器验证**：
   - 作者 / 分类 / 标签 / 系列 / 书架入口在 Sidebar 可进入
   - 各列表页条目、数量徽章、封面缩略正确
   - 点击条目跳转至对应书库列表，布局正常
   - 主题切换在各导航页生效；无 JS 错误

## 5. 推进标准（进入 P8 的门禁）
- 五种导航页（作者/分类/标签/系列/书架）均正常渲染且视觉统一
- 条目跳转正确，数量徽章与缩略图无误
- 面包屑/返回可用；无控制台 JS 错误

## 6. 下一步门禁
- **P8（Batch）**：在书库/导航页强化批量选择与批量操作栏。

## 7. 备注
- 书架为既有功能，仅重皮肤，不改其多用户权限语义。
- 若某一类导航页数据量较大，复用 P11 的性能基线结论评估展示方式（本期不强制分页）。

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P7 并经验证后，可进入 P8.
