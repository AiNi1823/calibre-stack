# Calibre-Web UI 升级 — Phase 8：批量操作（Batch Operations）

> 阶段定位：本阶段对应总体规划 `00-master-plan.md` §七 的 **P8（Batch Operations，UI only）**。
> **状态：已完成 ✅（提交见 HANDOFF-NEXT）**

## 0. 目标
- 优化书库页面的批量选择体验
- 优化后的批量操作栏：出现更快、交互更流畅、视觉更清晰
- 保持与原有功能完全兼容：下载、收藏、修改标签/分类、删除
- 在网格视图和列表视图中均可用；以订阅的 P3（Library）网格/列表为基础
- 批量操作保持**表单提交**，不引入新的 fetch API（UI only，后续再评估 API 化）

## 1. 影响项目文件
- **Fork 内（已实施）**：
  - `cps/templates/include/_batch-action-bar.html`（**新建 include/** 目录；Alpine 批量操作栏）
  - `cps/templates/index.html`（书库书卡加复选框 `data-id` + `x-data="calibreBatch(...)"` 包裹 + 全选/全不选 + 底部操作栏）
  - `cps/static/js/batch.js`（**新建**：Alpine `calibreBatch()` 组件，复用现有 JSON 端点）
  - `cps/templates/index.html` 底部 `{% block js %}`（加载 `batch.js` + 注入 `calibreBatchT` 文案）
  - `cps/static/css/tailwind.config.js` / `input.css`（新增 `.batch-checkbox`、`.cw-batch-bar*`、`.cw-book-card--selectable`、`.cw-batch-grid`）

- **范围裁定（重要，修正原稿误导）**：
  - 实际书库书卡网格渲染在 **`index.html`**（P3 已裁定）；`grid.html`/`list.html` 是作者/系列/标签的**首字母导航视图**（无 cover、无书 id 操作），P7 已重皮肤。因此 P8 把复选框放在 `index.html` 书卡上，而非 `grid.html`/`list.html`。

- **calibre-stack（暂不涉及，P10 处理）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。批量操作的后端路由（`editbooks.py`、`shelf.py`、`helper.py`）完全不动；仅前端交互改写。

## 3. 实施要点
1. **复选框**：每本书卡顶部添加 `<input type="checkbox" value="{{entry.Books.id}}" x-model="selected" class="batch-checkbox">`；外层 `x-data="calibreBatch(editUrlBase, delUrl)"`
2. **批量操作栏**（`include/_batch-action-bar.html`）：`x-data` 继承外层选中状态；`x-show="selected.length > 0"` + `x-transition` 显示；遮罩 `bg-black/20`；含 已选 N 本・全选/全不选・取消・改标签・改系列・改作者・删除（删除有确认步骤）
3. **Alpine 交互**：
   - `selected: []` 维护选中 ID 数组；`toggleAll()`/`isAllSelected()`/`clear()`
   - 操作按钮通过**复用现有后端 JSON 端点**完成：`edit-book.edit_list_book('/ajax/editbooks/<param>')`（multi）+ `edit-book.delete_books_ajax('/ajax/deletebook')`
   - **传输说明（重要偏差）**：本 fork 的后端批量端点均为 **JSON API**（`edit_list_book`/`delete_books_ajax`），不存在"表单提交"型的批量端点；且约束禁止改后端。故前端用 `fetch` 提交 JSON 到**既有**端点，等价于原 app 其它页面用 jQuery 走的同一信道（未新增后端协议，也未新增后端行为）。
4. **视觉**：栏顶部显示「Selected N books」；按钮与 P1 组件一致；移动端可用（flex-wrap + 底部固定）
5. **移动端**：复选框绝对定位在书卡左上角（z-20），底部操作栏 `flex-wrap` 自适应

## 4. 回测方法
1. **本地构建**：`npm run build` 通过（产物 `tailwind.css` 36,890 B）。
2. **渲染冒烟**：`/tmp/opencode/smoke_batch.py` —— `index.html` render len≈21468，全部 marker OK（batch-checkbox×3、x-data="calibreBatch(、x-model="selected"、x-show、cw-batch-bar__panel/count、Edit field、Select all / none、Delete selected books?、calibreBatchT）。
3. **浏览器验证**：
   - grid 进入批量选择：勾选/全选，复选框出现，已选数量显示
   - 取消勾选 / 点击遮罩 / 取消：栏消失，数量清零
   - 点击改标签/改系列/改作者/删除（确认）：后端 JSON 正常响应
   - 多次「全选/全不选」循环测试，状态正确

## 5. 推进标准（进入 P9 的门禁）
- [x] 批量勾选在书库书卡可用（index.html，网格离散为 2/3/4/5 列）
- [x] 「全选/全不选」正常；栏出现/消失动画流畅（x-transition）
- [x] 点击操作按钮后，后端正常响应（复用既有 JSON 端点，行为一致）

## 5.1 未实现/{defer到P10}
- **下载（批量）**：后端无多书批量下载端点（`download_link` 为单书+格式），暂不作为批量按钮（书卡/详情已有单书下载）。
- **收藏/加书架（批量）**：`shelf` 的 `massadd` 依赖服务端 `ub.searched_ids`（搜索会话），无法由纯前端任意选中集合触发，暂缓。
- 网格⇄列表切换、键盘导航、`grid.html`/`list.html`（导航视图本身）不逐卡加复选框——见范围裁定。

## 6. 下一步门禁
- **P9（Auth + Admin）**：后台表格同样复用本阶段批量选择逻辑（table.js 已有 `mass_selection` 模式可对接）。

## 7. 备注
- `_batch-action-bar.html` 复用 P1 按钮/输入样式（`cw-btn`、`cw-input`）；状态徽章沿用 P3 inline `cw-status-badge`。
- 若后续后端新增批量下载/收藏 API，仅需前端 `fetch` 相应参数即可，无需大改结构。

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P8 并经验证后，可进入 P9.
