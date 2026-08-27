# Calibre-Web UI 升级 — Phase 4：批量操作优化

## 0. 目标
- 优化书库页面的批量选择体验
- 优化后的批量操作栏：出现更快、交互更流畅、视觉更清晰
- 保持与原有功能完全兼容：下载、收藏、修改标签/分类、删除
- 在网格视图和列表视图中均可用

## 1. 影响项目文件
- **Fork 内**：
  - `cps/templates/include/_batch-action-bar.html`（重写：从头改写，不再依赖原有 jQuery 逻辑，全Alpine实现）
  - `cps/templates/grid.html`（在书卡行尾添加复选框 `data-id`）
  - `cps/templates/list.html`（在每行尾添加复选框 `data-id`）
  - `cps/static/css/tailwind.css` / `input.css`（新增 `.batch-action-bar`、`.batch-checkbox` 等样式）
  - `cps/templates/include/_status-badge.html`（复用，见 Phase 3）

- **calibre-stack（暂不涉及）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。批量操作的后端路由（`editbooks.py`、`helper.py`）完全不动；仅前端交互改写。

## 2. 实施要点
1. **复选框**：
   - 每本书行末尾（grid.html/list.html）添加 `<input type="checkbox" data-id="{{entry.id}}" class="batch-checkbox hidden">`
   - 头部添加 ‘全选/全不选’ 按钮 `<button class="batch-select-all">全选</button>`

2. **批量操作栏**（`_batch-action-bar.html`）：
   - 初始状态：`hidden`（不显示）
   - 点击 ‘全选’ 按钮后，显示栏并高亮已选书籍数量
   - 隐藏规则：点击遮罩层或 ‘取消’ 按钮后隐藏
   - 按钮包含：`下载`（下拉选格式）・`收藏`・「修改标签」・「修改分类」・「删除」

3. **Alpine 交互**：
    - `x-data=" { selected: [], }` 维护被选书籍 ID 数组
    - `'input[type="checkbox"]': { selected.indexOf($event.dataset.id) !== -1 ? selected.splice(selected.indexOf($event.dataset.id), 1) : selected.push($event.dataset.id) }` 维护选中状态
    - `'全选'@click='selected = selected.includes(id) ? [] : [id]'`（其中 id 通过遍历 book-row 动态绑定）
    - 批量操作栏显示：`x-show="selected.length > 0"`，`x-transition` 淡入淡出
    - **点击操作按钮后：保持原有后端行为，通过表单提交（form submission）完成下载/收藏/标签/分类/删除等操作，不使用新的 fetch API。**——保持与原有 `editbooks.py`/`helper.py` 行为完全一致，避免在 UI 重构期间引入新的后端协议。

4. **视觉设计**：
   - 批量操作栏顶部显示 ‘已选 N 本’
   - 按钮样式与常规按钮一致，`hover` 态有轻微颜色变化
   - 遮罩层 `bg-black/20` `absolute inset-0`，`x-show` 控制显隐

5. **grid.html / listhtml 变更**：
   - 在每本书行末尾添加复选框：`'<input type="checkbox" data-id="{{entry.id}}" class="batch-checkbox hidden dark:inline-block">'`
   - 确保复选框在移动端也能正常工作（`dark:inline-block` 仅移动端显示，desktop端可隐藏或保持）

## 2. 后端改动
- 无。后端 `editbooks.py`、`helper.py` 等不动；前端仅改写交互，保持原有表单提交行为不变.。

## 3. 回测方法
1. **本地构建**：同上
2. **浏览器验证**：
   - grid.html/list.html 进入批量选择模式：点击 ‘全选’，复选框出现，已选数量显示
   - 取消勾选：点击 ‘取消’ 或点击遮罩层，批量操作栏消失，已选数量清零
   - 点击操作按钮（下载/收藏/标签/分类/删除）：后端正常响应（此处以原有后端行为为准，前端发送请求符合原有规范）
   - 多次点击 ‘全选/全不选’ 循环测试，确保状态正确

## 3. 推进标准（进入 P5 的门禁）
- 批量勾选功能在 grid.html 和 list.html 均可用
- ‘全选/全不选’ 按钮正常工作
- 批量操作栏出现/消失动画流畅
- 点击操作按钮后，后端正常响应（保持原有行为）

## 3. 下一步门禁
- P5（暗色模式 + 响应式 + 无障碍）：`class="dark"` 切换、断点适配、无障碍访问检查

## 4. 备注
- 为避免重复造轮，`_batch-action-bar.html` 尽量复用 Phase 3 中的 `_status-badge.html` 组件格式
- 若后端后续新增批量操作 API，仅需在前端 `fetch` 相应参数即可，无需大改结构

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P4 并经验证后，可进入 P5.