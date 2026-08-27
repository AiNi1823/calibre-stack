# Calibre-Web UI 升级 — Phase 10：管理后台

## 0. 目标
- 重皮肤 `admin.html`、`book_table.html`、`user_table.html`、`config_edit.html`
- 保持全部功能不变：图书管理（增删改查）、用户管理、系统配置、日志查看
- 视觉风格与全站统一：深色模式、圆角 4–6px、统一的间距与间距、统一的操作按钮
- 表格 `book_table` 增加「状态」与「操作」列，Alpine 实现行高亮与批量操作

## 1. 影响项目文件
- **Fork 内**：
  - `cps/templates/admin.html`（重写：侧边栏+内容区布局，保持左侧 Sidebar + 主题切换）
  - `cps/templates/book_table.html`（重写：表格结构、状态徽章、操作按钮、批量勾选）
  - `cps/templates/user_table.html`（重写：用户列表、状态、权限、操作）
  - `cps/templates/config_edit.html`（重写：配置项美化、开关开关）
  - `cps/static/css/tailwind.css` / `input.css`（新增表格相关样式：`.data-table`、`.action-btn`、`.status-badge` 等）
  - `cps/templates/include/_operation-btn.html`（新增：操作按钮组：编辑/删除/查看）
  - `cps/templates/include/_status-badge.html`（复用，见 Phase 3）

- **calibre-stack（暂不涉及）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。`web.py`、`db.py` 完全不动；`book_table` 的查询数据 (`entries`、`entries[0]` 等) 完全不动；仅前端展示重写。

## 2. 实施要点
1. **书籍表格 `book_table.html`**：
   - `.data-table`：`w-full` `min-w` `rounded-2xl` `overflow-hidden`，交替行行颜色 `bg-white` `/ `bg-gray-50`
   - `.header`：`.data-header`（`.data-header .row`）`.data-header .row .col`（`.data-header .row .col .col-span-1` `.data-header .row .col .col-span-2`）
   - `.status-badge`：状态徽章（未读/在读/已读），右上角 `.row .row .row .data-actions .row .data-actions .row .data-actions .row .data-actions`（编辑/删除/查看）
   - `.data-actions .row .data-actions .row .data-actions`（操作按钮：编辑/删除/查看）
   - `.data-footer`：分页、导出

2. **用户表格 `user_table.html`**：
   - `.data-table`：同书籍表格结构
   - `.data-header`：用户名、组、状态、操作
   - `.data-actions`：编辑/禁用/删除

3. **配置编辑 `config_edit.html`**：
   - `.config-group`：分组折叠/展开
   - `.config-item`：键名/键值 `.config-item .row .col`（键名 `.col-span-1`、键值 `.col-span-2`}
   - `.save-btn`：保存按钮（Alpine `x-on:submit`）

4. **操作按钮**（`_operation-btn.html`）：
   - `.btn .btn-sm .btn-primary .btn-danger`：编辑/删除/查看
   - `data-id` 传递至后端（Alpine `x-on:click`）

5. **Alpine 交互**：
   - 表格行高亮：`row-hover` 类，`x-on:mouseenter`/`x-on:mouseleave` 切换 `bg-gray-100`
   - 批量勾选：同 Phase 4 的批量操作逻辑
   - 状态徽章 `x-show` 根据 `ub.ReadBook.read_status` 显示

## 2. 后端改动
- 无。前端完全独立，后端路由、数据、API完全不动。

## 3. 回测方法
1. **本地构建**：同上
2. **浏览器验证**：
   - 后台登录后进入「书籍管理」->书籍列表，表格正常显示，状态徽章颜色正确
   - 操作按钮（编辑/删除/查看）点击正常，跳转至相应页面
   - 用户管理页面列出所有用户，状态、权限正常显示
   - 配置编辑页各项可编辑，保存后生效

## 3. 推进标准（进入 P11 的门禁）
- 后台各页面正常渲染，无 JS 错误
- 所有操作按钮功能正常（编辑/删除/查看/保存）
- 状态徽章颜色正确（未读/在读/已读）
- 表格交替行色正常

## 3. 下一步门禁
- P11（最终验收 + 上线）

## 3. 备注
- `admin.html` 的左侧Sidebar需保持与首页/书库页统一的 Sidebar 设计
- `book_table.html` 的操作列保持 Calibre-Web 原有的功能入口（编辑/删除/查看），仅外观重写

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P10 并经验证后，可进入 P11.