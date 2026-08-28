# 续接文档 (HANDOFF) — 重启对话后从此继续

> 生成于会话中断时。目标：让新会话立即知道施工到哪、还剩什么、如何收尾。
> 分支：`calibre-stack` `rewrite` 分支（`origin/rewrite` 远端已跟踪）。
> 施工对象：vendored 源码树 `calibre-web/`（Calibre-Web 0.6.27）。
> 约束：后端 `web.py/db.py/helper.py` 不改；UI 渐进迁移；每阶段 commit+push。

## 0. 会话卡死根因（重要）
`big-pickle` 模型在**超长上下文**（尤其那段 400 行 Python 拼接 layout.html + 反复调试文本）下生成退化、死循环，无报错、连接不断、30 分钟级静默。
- **对策**：本会话已重启。新会话务必**用极简、单步 bash 收尾**，不要一次性输出大段文本/并行巨调用，避免再次触发。
- 若再卡：`tail -f /root/.local/share/opencode/log/opencode.log`；进程直连 `172.65.90.20/21:443`（未走 mihomo 7890，链路健康）。

## 1. 已提交 && 已推送（origin/rewrite）
- `d44bccd` P0 基线：vendored `calibre-web/` + Tailwind 链 + 主题/组件初版 + 旧 patch 归档到 `deploy/patches-archive/*.legacy`
- `7f0b737` P0 施工：`src/input.css` 令牌+基础组件、`tailwind.css`、vendored `js/libs/alpine.min.js`/`lucide.min.js`、`js/theme.js`、`js/ui.js`、`postcss.config.js`
- `81fff12` P1 Design System：`src/input.css` 补全 BookCard/Table/Dialog/Drawer/Dropdown/Toast/Tabs/Pagination + Layout 原语（`cw-app/cw-sidebar/cw-main/cw-header/cw-page-header`）

## 2. P2（App Shell）当前状态：代码已改写，**未提交**
工作区有 3 个文件改动（`git status -s` 应为）：
```
 M calibre-web/cps/static/css/tailwind.css
 M calibre-web/cps/templates/layout.html
 M calibre-web/src/input.css
```
- `layout.html`：已用 Python 把 body 外壳（原 Bootstrap navbar + col-sm-2/col-sm-10）整体替换为 Tailwind App Shell：
  - 桌面 `cw-sidebar` 常驻（`lg:flex`）+ 移动端 `cw-sidebar--drawer` 抽屉（`x-show` 由 `$store.ui.sidebarOpen` 控制）
  - 遮罩层 `x-show sidebarOpen` + 点击/Esc 关闭
  - `cw-header`：汉堡按钮、搜索框（`#query`）、上传表单（`#form-upload`/`#btn-upload`）、`#top_tasks`/`#top_mytasks`/`#top_admin`、主题切换 `$store.ui.toggleDark()`、账户下拉 `#top_user`/`#login`/`#register`/`#logout`
  - `cw-main__inner` 内含 flash（保留 `#flash_danger/success/info/warning`）+ `{% block body %}` + 分页 `cw-pagination`
- `src/input.css`：新增 `[x-cloak]{display:none!important}`、`cw-sidebar--drawer`（off-canvas + `--open`）、`cw-sidebar__head`、`.cw-search--flex`
- `tailwind.css`：已重编译到 **27230 B**（27.2KB）

## 3. 已验证结果
- `npm run build` 成功 → `cps/static/css/tailwind.css` 27230 B（含全部 App Shell 类）
- 渲染冒烟：`layout.html` 用 Jinja 完整 render 成功，**len=9064**，以下均出现：
  - `/static/css/tailwind.css`、`alpine.min.js`、`js/theme.js`、`lucide.min.js`
  - `id="query"`、`id="btn-upload"`、`toggleDark()`、`sidebarOpen`、`bookDetailsModal`、`cw-sidebar`
- 上一步 4 个 MISS 已定位为**测试桩问题非模板问题**：
  - `id="form-upload"`/`id="btn-upload"`：stub 缺 `g.allow_upload` → 让 upload 段没渲染；补 `g.allow_upload=True` 即可出现
  - `id="flash_danger"`：无 flash 消息，循环不渲染，正常
  - `cw-drawer`：检查词写错；实际用的是 `cw-sidebar--drawer`，非 `cw-drawer`

## 4. 下一步（新会话必做）
1. **`cd /opt/calibre-stack && git add -A && git commit && git push origin rewrite`** —— 提交 P2 三个改动文件。**这是当务之急，代码未提交，别丢。**
2. **快速复验**（单步、静默）：跑一次渲染冒烟，stub 里补 `g.allow_upload=True`，确认 `id="form-upload"`/`id="btn-upload"` 出现、`cw-sidebar--drawer` 存在，全部 OK 后再提交。
3. 更新 `docs/ui-rewrite/02-phase2.md` 的影响文件路径（实际用 `layout.html`，非 `base.html`；校验命令用 `npm run build`）+ 记录 App Shell 已实现项。
4. **P3（Library）**：在 App Shell 上重皮肤书库页（`{% block body %}` 内容）。
5. 之后 P4→P12 按文档顺序，每阶段 commit+push。

## 5. 环境备忘
- 构建：`cd /opt/calibre-stack/calibre-web && npm install && npm run build`（产物提交，VPS 运行期无需 Node；node_modules 已 gitignore）
- 重新部署：`/opt/calibre-web/venv/bin/pip install --force-reinstall --no-deps /opt/calibre-stack/calibre-web`
- 模板是 `cps/templates/layout.html`（**无 `base.html`**，P1 文档已改）
- Bootstrap/jQuery 仍加载（渐进迁移保留）；Alpine/Lucide 已 vendored 本地
- 关键 CSS：`src/input.css` 顶层声明组件类（**勿用 `@layer components` 包裹**——本 Tailwind 3.4 会整体丢弃 `@apply`）
- 渲染冒烟测试桩需：`current_user.check_visibility`、`role_upload`、`role_admin`、`g.allow_upload`、`g.current_theme`、`g.shelves_access`、`sidebar`、`accept`、`searchterm`、`simple`、filters `shortentitle` 等
