# Calibre-Web UI 升级 — Phase 9：登录/注册

## 0. 目标
- 重皮肤 `login.html` 与 `register.html`
- 保持原有的 Calibre-Web 登录流程不变（CAS/Ticket、表单验证）
- 视觉风格与首页/书库页统一：深色模式、圆角 4–6px、按钮统一、Alpine.js 交互
- 为登录/注册页添加「忘记密码」入口，与 CAS /CAS 子系统保持联动

## 1. 影响项目文件
- **Fork 内**：
  - `cps/templates/login.html`（重写：登录表单、CAS 链接、忘记密码、主题切换按钮）
  - `cps/templates/register.html`（重写：注册表单、协议链接、主题切换按钮）
  - `cps/templates/include/_form-field.html`（新增：统一的输入框组件，含标签、icon、错误信息）
  - `cps/templates/include/_cassistant.html`（新增：CAS 登录助手，显示 CAS 状态、重新登录链接）
  - `cps/static/css/tailwind.css` / `input.css`（新增登录/注册页样式：`.login-box`、`.register-box`、`.form-field`）

- **calibre-stack（暂不涉及）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。`web.py`、`helper.py`、`db.py` 完全不动；仅前端模板改写，保持所有验证逻辑、CAS 链接、重定向地址不变。

## 2. 实施要点
1. **登录页布局**：
   - `.login-box`：`max-w-md` `mx-auto` `mt-8`，卡片式居中布局
   - `.login-header`：站点名称 + 主题切换按钮
   - `.login-body`：`.form-field`（用户名）+ `.form-field`（密码） + `.btn`（登录）
   - `.login-footer`：`忘记密码` 链接 → `CAS` 重置页面 / `创建账户` 链接 → 注册页

2. **注册页布局**：
   - `.register-box`：与登录页布局一致，字段含 用户名/邮箱/密码/确认密码/协议确认
   - `.register-footer`：已有账户链接 → 登录页

3. **主题切换**：
   - 与首页/书库页保持一致：`class="dark"` 控制、按钮 `@click="dark = !dark"`，`aria-label="切换护眼模式"`

4. **Alpine 交互**：
   - 表单 `submit` 前的简单验证：`x-on:submit.prevent.prevent`
   - 输入框 `x-on:focus` 添加 `focus-visible` 样式
   - 错误信息 `x-show` 绑定后端返回的 `error` 变量

## 1. 后端改动
- 无。`web.py` 的 `login()`、`register()` 函数不动；前端模板仅在原有表单上进行视觉与交互增强。

## 2. 回测方法
1. **本地构建**：同上
2. **浏览器验证**：
   - 打开 `login.html`：界面布局美观，主题切换生效，CAS 链接正常
   - 打开 `register.html`：表单字段完整，主题切换生效
   - `忘记密码` 链接正常跳转至 CAS 重置页面
   - 表单提交：正确填写验证通过，错误填写显示错误信息
   - `Esc` 关闭模态框（若以模态框形式），或 `Tab` 顺序自然

## 3. 推进标准（进入 P10 的门禁）
- 登录页/注册页视觉与首页统一（深色模式、圆角、统一按钮）
- 所有表单验证正常，`忘记密码` 跳转正常
- 主题切换在登录/注册页生效
- 无控制台 JS 错误

## 3. 下一步门禁
- P10（管理后台重皮肤）

## 3. 备注
- 登录/注册页作为用户的首次触点，视觉质量至关重要；需确保与首页/书库页风格完全一致
- `x-data` 中的 `dark` 变量通过 `base.html` 继承，确保三端（Desktop/Tablet/Mobile）一致

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P9 并经验证后，可进入 P10.