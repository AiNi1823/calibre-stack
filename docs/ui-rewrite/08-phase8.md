# Calibre-Web UI 升级 — Phase 8：批量操作（Batch Operations）

> 阶段定位：本阶段对应总体规划 `00-master-plan.md` §七 的 **P8（Batch Operations，UI only）**。

## 0. 目标
- 优化书库页面的批量选择体验
- 优化后的批量操作栏：出现更快、交互更流畅、视觉更清晰
- 保持与原有功能完全兼容：下载、收藏、修改标签/分类、删除
- 在网格视图和列表视图中均可用；以订阅的 P3（Library）网格/列表为基础
- 批量操作保持**表单提交**，不引入新的 fetch API（UI only，后续再评估 API 化）

## 1. 影响项目文件
- **Fork 内**：
  - `cps/templates/include/_batch-action-bar.html`（重写：基于 Alpine，不依赖原 jQuery）
  - `cps/templates/grid.html`（在书卡行尾添加复选框 `data-id`）
  - `cps/templates/list.html`（在每行尾添加复选框 `data-id`）
  - `cps/static/css/tailwind.config.js` / `input.css`（新增 `.batch-action-bar`、`.batch-checkbox` 等样式）
  - `cps/templates/include/_status-badge.html`（复用 P1）

- **calibre-stack（暂不涉及，P10 处理）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。批量操作的后端路由（`editbooks.py`、`helper.py`）完全不动；仅前端交互改写。

## 3. 实施要点
1. **复选框**：每本书行末尾添加 `<input type="checkbox" data-id="{{entry.id}}" class="batch-checkbox">`；头部加「全选/全不选」按钮
2. **批量操作栏**（`_batch-action-bar.html`）：初始 `hidden`；勾选后显示并高亮已选数量；点击遮罩/取消收起；按钮含 下载（选格式）・收藏・改标签・改分类・删除
3. **Alpine 交互**：
   - `x-data="{ selected: [] }"` 维护选中 ID 数组
   - `x-show="selected.length > 0"` + `x-transition` 显示/隐藏
   - **点击操作按钮保持原有后端行为，通过表单提交完成（不使用新的 fetch API）**，避免在 UI 重构期间引入新协议
4. **视觉**：栏顶部显示「已选 N 本」；遮罩 `bg-black/20`；按钮与常规一致，hover 有轻微变化
5. **移动端**：复选框在移动端亦可用

## 4. 回测方法
1. **本地构建**：同上
2. **浏览器验证**：
   - grid/list 进入批量选择：勾选/全选，复选框出现，已选数量显示
   - 取消勾选 / 点击遮罩 / 取消：栏消失，数量清零
   - 点击操作按钮（下载/收藏/标签/分类/删除）：后端正常响应（保持原表单行为）
   - 多次「全选/全不选」循环测试，状态正确

## 5. 推进标准（进入 P9 的门禁）
- 批量勾选在 grid 与 list 均可用
- 「全选/全不选」正常；栏出现/消失动画流畅
- 点击操作按钮后，后端正常响应（保持原有行为）

## 6. 下一步门禁
- **P9（Auth + Admin）**：后台表格同样复用本阶段批量选择逻辑。

## 7. 备注
- `_batch-action-bar.html` 尽量复用 P1 的 `_status-badge` 等组件格式。
- 若后续后端新增批量操作 API，仅需前端 `fetch` 相应参数，无需大改结构（本期不落地）。

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P8 并经验证后，可进入 P9.
