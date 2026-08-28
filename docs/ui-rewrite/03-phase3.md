# Calibre-Web UI 升级 — Phase 3：书库（Library）

## 0. 目标
- 重皮肤 `grid.html`（书网格视图）和 `list.html`（书列表视图）
- 保持 Grid⇄List 切换功能
- 封面更显重点：圆角 4–6px，裁剪保持比例， lazy-loading
- 状态徽章：未读/在读/已读 用颜色极简标记（不使用鲜艳色）
- 工具栏：保留 Grid/List 切换按钮，并新增 ‘Batch Action Bar’（批量操作栏），点击后出现 ‘下载 / 收藏 / 修改标签 / 修改分类 / 删除’ 等选项
- 支持键盘导航（Alpine 数据属性）

## 1. 影响项目文件
- **Fork 内**：
  - `cps/templates/grid.html`（重写书卡结构，Tailwind 类，Alpine 交互）
  - `cps/templates/list.html`（重写列表结构，保持原有列表形式但调整视觉）
  - `cps/static/css/tailwind.css` / `input.css`（新增网格/列表相关的工具类，如 `.book-card`、`.book-list-item`、`.status-badge` 等）
  - `cps/templates/include/_book-card.html`（提取为可复用组件，`grid.html` 和 `list.html` 共享）
  - `cps/templates/include/_batch-action-bar.html`（新增：批量操作栏，含下载/收藏/标签/分类/删除）

- **calibre-stack（暂不涉及）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。 grid.html/list.html 的数据传输（`entries`、`entries[0]` 等）完全不动；仅改模板呈现样式。

## 2. 实施要点
1. **书卡结构**（grid.html）：
   - `.book-card`：`grid-grid-flow-col gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`（响应式网格）
   - `.book-card .cover`：`rounded-4xl`（替代原来的大圆角），`object-cover`，`lazy-loading`，`transition-transform` 轻微放大 hover 态
   - `.book-card .meta`：`.title`（单行截断）、`.author`、`.series`（小号、灰色）
   - `.book-card .status`：`status-badge`（见下）

2. **状态徽章**（`status-badge`）：
   - `bg-gray-100 text-gray-800`：未读
   - `bg-green-100 text-green-800`：在读
   - `bg-blue-100 text-blue-800`：已读
   - 尺寸：`text-xs`、`px-2`、`py-1`，圆角 `2px`
   - 徽章上可能含简短文字：`未读`/`在读`/`已读`

3. **列表视图**（list.html）：
   - 保持原有的表格/行结构，但 `.book-row` 的 `.cover` 圆角改为 `rounded-4`
   - `.book-row .meta`：`.title` 左对齐、`.author` 右对齐
   - 每行高度固定，纵向间距 `my-2`，横向间距 `mx-2`
   - 每行末尾保留 ‘Grid / List’ 切换按钮（Alpine 控制 `grid-view` / `list-view` 的显示/隐藏）

4. **批量操作栏**（`_batch-action-bar.html`）：
   - 初始隐藏：`hidden`，点击左上角「复选框」图标后 `x-show` 变 `block`
   - 包含按钮：`Download`（下拉选格式）・`Add to shelf`（收藏）・`Edit tags`（修改标签）・`Edit category`（修改分类）・`Delete`（删除）
   - 选中状态：左上角显示 ‘已选 N 本’，点击按钮前样式 `hidden`，点击后 `block`；点击任意其他位置收起

5. **Alpine 交互**：
   - Grid/List 切换：`x-data="{ view: 'grid' }`，`'grid-button'@click='view = \'grid\'` / `'list-button'@click='view = \'list\'``
   - 批量选中：`x-data=" { selected: [], }`，`'book-row'@click='selected.indexOf($event.dataset.id) !== -1 ? selected.splice(selected.indexOf($event.dataset.id), 1) : selected.push($event.dataset.id)'`}
   - 批量操作栏显示：`x-show="selected.length > 0`，`x-transition` 淡入淡出

## 2. 后端改动
- 无。grid.html/list.html 的数据完全不动。

## 3. 回测方法
1. **本地构建**：同上
2. **浏览器验证**：
   - Grid 视图：封面正常，圆角 4–6px，状态徽章颜色正确，Hover 有轻微放大
   - List 视图：列表形式正常，圆角 4，状态徽章颜色正确
   - Grid⇄List 切换：点击按钮，视图平滑切换（无闪烁）
   - 批量操作：勾选复选框（或点击头像），批量操作栏出现；点击外部或‘取消’收起
   - Ctrl 多选（若浏览器支持）：`Cmd/Ctrl + click` 追加/取消勾选

## 3. 推进标准（进入 P4 的门禁）
- grid.html 和 list.html 在桌面/移动端均能正常渲染
- Grid⇄List 切换流畅，无闪烁
- 状态徽章颜色符合设计（未读/在读/已读）
- 批量操作栏在勾选后出现，点击外部或‘取消’收起
- Alpine 无错误

## 4. 下一步门禁
- P4（书籍详情页）：重皮肤 `detail.html`（封面+元数据+操作按钮优先级：阅读/下载/收藏/更多）

## 备注
- `_book-card.html` 与 `_batch-action-bar.html` 的提取若对代码量有顾虑，可直接在 grid.html/list.html 中写 inline；提取目的是为了复用与保持代码整洁。
- `status-badge` 的颜色可在 `tailwind.config.js` 的 `theme.extend.colors` 中统一声明，便于后续深浅色互换。

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P3 并经验证后，可进入 P4.