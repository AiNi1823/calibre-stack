# Calibre-Web UI 升级 — Phase 9：认证 + 管理后台（Auth + Admin）

> 阶段定位：本阶段对应总体规划 `00-master-plan.md` §七 的 **P9（Auth + Admin）**。
> 合并「登录/注册」与「管理后台」两类页面重皮肤，保持既有认证与后台功能语义完全不变。

## 0. 目标
- 重皮肤 `login.html` / `register.html`：保持 Calibre-Web 登录流程（表单验证、CAS/Ticket）不变
- 重皮肤后台：`admin.html`、`book_table.html`、`user_table.html`、`config_edit.html`
- 全站视觉统一：深色模式、圆角 4–6px、统一按钮与间距、Alpine.js 交互
- 登录/注册页作为首次触点，质量优先；后台表格增加「状态 / 操作」列并支持批量勾选

## 1. 影响项目文件
- **Fork 内**：
  - `cps/templates/login.html`（重写：登录表单、CAS 链接、忘记密码、主题切换）
  - `cps/templates/register.html`（重写：注册表单、协议链接、主题切换）
  - `cps/templates/admin.html`（重写：侧边栏 + 内容区，保持统一 Sidebar）
  - `cps/templates/book_table.html`（重写：表格结构、状态徽章、操作按钮、批量勾选）
  - `cps/templates/user_table.html`（重写：用户列表、状态、权限、操作）
  - `cps/templates/config_edit.html`（重写：配置项分组与保存）
  - `cps/templates/include/_form-field.html`（新增：统一输入框，含 label/icon/错误信息）
  - `cps/templates/include/_operation-btn.html`（新增：编辑/删除/查看操作按钮组）
  - `cps/templates/include/_status-badge.html`（复用 P1）
  - `cps/static/css/tailwind.config.js` / `input.css`（登录/后台相关样式）

- **calibre-stack（暂不涉及，P10 处理）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。`web.py` 的 `login()`/`register()`、后台各路由与数据查询（`entries` 等）完全不动；仅前端展示与交互改写。

## 3. 实施要点

### 3.1 登录 / 注册
1. `.login-box` / `.register-box`：`max-w-md` 居中卡片，`class="dark"` 主题切换
2. 表单 `submit` 保持原有后端行为；`focus-visible` 焦点态；错误信息 `x-show` 绑定后端 `error`
3. `忘记密码` → CAS 重置；`创建账户` ↔ 登录页互链；`Tab` 顺序自然

### 3.2 管理后台
1. `book_table.html`：`.data-table` 交替行色，含状态徽章列与操作列（编辑/删除/查看），复用 P1 `Table`/`Badge`
2. 批量勾选：复用 P8 的批量选择与操作栏逻辑；操作保持**表单提交**、不引入新 API
3. `user_table.html`：用户名、组、状态、权限、操作（编辑/禁用/删除）
4. `config_edit.html`：`.config-group` 分组折叠，`.save-btn` 保存，`x-on:submit`
5. 表格行 hover 高亮（Alpine），保持原有功能入口

## 4. 回测方法
1. **本地构建**：同上
2. **浏览器验证**：
   - 登录/注册流程、CAS 链接、忘记密码跳转正常；错误信息正确显示
   - 后台各页正常渲染，状态徽章与操作按钮功能正确（编辑/删除/查看/保存）
   - 批量勾选在后台表格可用；移动端表格可用
   - 主题切换在登录/后台生效；无控制台 JS 错误

## 5. 推进标准（进入 P10 的门禁）
- 登录/注册与后台各页视觉统一，功能与原有路由一致
- 后台表格批量操作保持表单提交语义，后端返回正常
- 主题切换生效；无控制台 JS 错误

## 6. 下一步门禁
- **P10（Custom Pages）**：将 `/tasks`、`/async-upload` 自研页统一到同一 Design System。

## 7. 备注
- 登录/注册与后台是权限敏感面，重皮肤时不得改动任何认证/授权逻辑与 CAS 语义。
- 后台操作列保持 Calibre-Web 原有功能入口，仅外观重写。

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P9 并经验证后，可进入 P10.
