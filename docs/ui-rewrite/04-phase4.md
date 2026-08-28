# Calibre-Web UI 升级 — Phase 4：书籍详情（Book Detail）

## 0. 目标
- 重皮肤 `detail.html`（书籍详情页）——**已实现 @ 本阶段提交**
- 保持原有功能不变：封面、元数据、操作按钮（下载/发送到 eReader / 在线阅读 / 收藏 / 编辑 / 删除）
- 封面居左，元数据居右（桌面端）；移动端垂直堆叠
- 状态徽章：详情页仅 2 态（已读/未读）——后端 `show_book` 把 `entry.read_status` 设为**布尔** `read_book == STATUS_FINISHED`（非 0/1/2 三态），故详情页徽章只可靠显示 已读/未读
- 侧边栏/主题状态在详情页保持同步（继承 `layout.html`）

## 1. 影响项目文件
- **Fork 内（已实现 @ 本阶段提交）**：
  - `cps/templates/detail.html`（重写 body：`cw-detail__layout` 封面居左/元数据居右；操作栏 `cw-detail__actions`；Bootstrap `btn btn-*` → `cw-btn cw-btn--*`；保留全部 id/表单/data-* 与 `{% block js %}`）
  - `cps/static/css/input.css`（新增 `cw-detail__layout/cover/meta/actions/toggles/shelves`，封面 hover 微放大）
  - `cps/static/css/tailwind.css`（`npm run build` 编译产物，~29.7KB）
- **未做**：`_book-card.html`/`_status-badge.html` include（未拆分，沿用 P3 内联风格）；进度条（后端无 per-user 进度数据）

- **calibre-stack（暂不涉及，P10 处理）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。`detail.html` 仅改写前端展示结构，保持所有按钮链接、数据调用完全不动。

## 2. 实施要点（已实现）
1. **结构布局**：
   - `.cw-detail__layout`：`grid grid-cols-1 gap-6 md:grid-cols-[13rem_minmax(0,1fr)]`（桌面封面居左/元数据居右；移动端垂直堆叠）
   - `.cw-detail__cover`：`rounded-4`、`aspect-[2/3] object-cover`、hover `scale-[1.02]`；全尺寸 `#detailcover`（详情页不加 lazy）
   - `.cw-detail__actions`：`flex flex-wrap gap-2`，下载/发送eReader/在线读/在线听按钮
2. **状态徽章**（`cw-status-badge` 内联，非 include）：
   - `entry.read_status`（详情页为布尔）=`True`→`cw-status-badge--finished`(已读)；否则 `--unread`(未读)；放在封面左上角
   - 详情页**不做三态**——后端 `show_book` 只传布尔，无 `在读` 态可显示
3. **操作按钮**：Bootstrap `btn btn-primary/btn-sm/btn-xs` → `cw-btn cw-btn--primary/--secondary/--outline/--sm`；下拉统一套 `cw-dropdown`+`cw-dropdown__menu`
   - 保留全部 **id/表单/`data-*`/`data-toggle="dropdown"`**：`#Download`、`#btnGroupDrop1`、`#sendbtn(2)`、`#readbtn`、`#listenbtn`、`#have_read_form/#have_read_cb`、`#archived_form/#archived_cb`、`#edit_book`、`#back`、`#add-to-shelf`、`#template-shelf-add/remove` —— 保证 `details.js`/`main.js`/`fullscreen.js` 行为不变
   - `#back` 由 `div` 改为 `button`（`main.js` 用 `.click()`+`.data('back')` 兼容）
4. **面包屑/返回**：未加独立面包屑（保留原 `#back`）；返回按钮 `data-back`→`web.index` 行为不变
5. **Alpine / 主题**：详情页继承 `layout.html` 的 `x-data` 与 `dark` 状态，无需另设

## 3. 回测方法
1. **本地构建**：`npm run build`，校验 `tailwind.css` 含 `cw-detail__layout/cover/actions` 等
2. **渲染冒烟**：Jinja render `detail.html`（`/tmp/opencode/smoke_detail.py`），断言 `cw-status-badge`、`#have_read_cb`、`#archived_cb`、`#btnGroupDrop1`、`#readbtn`、`#edit_book`、`#add-to-shelf`、`template-shelf-add` 出现（`id="Download"` 仅单格式时出现、`details.js` 因 url_for 桩为 `#` 属预期）
3. **浏览器验证**：
   - 桌面端：封面居左、元数据居右，操作按钮在一行
   - 移动端：封面全宽，元数据垂直堆叠
   - 操作按钮（阅读/下载/eReader/编辑/收藏）均可点击并跳转/执行

## 3. 推进标准（进入 P5 的门禁）
- `detail.html` 在桌面/移动端正常渲染：封面与元数据并排/堆叠正确
- 所有操作按钮功能正常（下载/阅读/eReader/编辑/收藏），id/表单钩子未被破坏
- 封面圆角 4–6px，无 `rounded-4xl`；状态徽章 已读/未读 正确
- 无控制台 JS 错误

## 3. 下一步门禁
- P5（Home）：重皮肤首页 `index.html`（继续阅读 / 最近 / 收藏区块）

## 3. 备注
- `detail.html` 布局保持「封面优先、操作明确」；未被过度拆分（无多余 include）
- 详情页封面/徽章沿用 P3 的 `cw-status-badge` 内联风格；`dark` 状态继承 `layout.html` 生效
- 状态徽章后端仅布尔（`show_book` 传 `entry.read_status`），故详情页只显示 已读/未读；三态只存在于书库网格（P3 `entry[2]`）

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P4 并经验证后，可进入 P5.