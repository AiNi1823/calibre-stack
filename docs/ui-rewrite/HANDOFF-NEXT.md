# 续接文档 (HANDOFF) — 重启对话后从此继续

> 目标：让新会话立即知道施工到哪、还剩什么、如何收尾。
> 分支：`calibre-stack` `rewrite` 分支（`origin/rewrite` 远端已跟踪）。
> 施工对象：vendored 源码树 `calibre-web/`（Calibre-Web 0.6.27）。
> 约束：后端 `web.py/db.py/helper.py` 不改；UI 渐进迁移；每阶段 commit+push。

## 0. 当前施工方向 = P16（UI Bug Fix P0）
> 完整指令/改动清单见 `docs/ui-rewrite/16-ui-bugfix-p0.md`。P15（Final Design Spec）已完成；P14（Desktop Density）已完成；P13（统一收口）见 §0b；P0–P12 见 §1。
> **P16 目标**：修复 3 个 P0 UI Bug + 1 个 P1 Bug，不重新设计，不重构，不继续叠加 CSS。
> - Bug 1：Book Detail 点击后跑到页面底部（应为 Overlay/Drawer）
> - Bug 2：/author 页面文字逐字换行
> - Bug 3：/category 页面文字逐字换行
> - Bug 4（P1）：ASIN identifier 被错误拼接到 Amazon URL

## 0.1 P16 约束（极重要）
> **本次不是 UI 设计，不是重新设计页面，不是继续增加 CSS。只解决已存在的 Bug。**
> - 必须先定位根因 → 修改最少代码 → 浏览器验证 → 再提交
> - 禁止新增大量 CSS / !important / position:absolute / transform / 负 margin / 固定 height
> - 禁止重新设计 Author / Category / Book Detail 页面
> - 禁止删除原有页面重新写一个假的页面
> - 必须在现有 Calibre-Web 页面结构上修复
> - 完整禁止清单见 `16-ui-bugfix-p0.md` §二

## 0. 会话卡死根因（重要）
`big-pickle` 模型在**超长上下文**（尤其大段 Python 拼接模板 + 反复调试文本）下生成退化、死循环，无报错、连接不断、静默 30 分钟级。
- **对策**：保持**极简、单步 bash 收尾**，不要一次性输出大段文本/并行巨调用。
- 若再卡：`tail -f /root/.local/share/opencode/log/opencode.log`。

## 0b. P13 施工进度（UI Consistency Pass）
已完成（Batch 1，commit 见 §1 顶部）：
- `index.html` 收口：Bootstrap 排序条 → `cw-btn--ghost/sm` + 文案（保留全部 id/order/sort_param）；`glyphicon-music` → Lucide；书库网格 → 自适应 `cw-book-grid`（auto-fill minmax(150px,1fr)）；`layout.html` 修复「奇怪代码」——补全 `#bookDetailsModal` 的 `<div class="modal fade">` 开标签（原为裸 `aria-labelledby` 破损片段）。
- `admin.html` 完整重写：`container-fluid/row/col` → `cw-card` 分节；`table table-striped` → `cw-table`（thead/tbody 结构）；`btn btn-default` → `cw-btn--secondary/danger`；glyphicon 布尔 → `cw-status-badge 是/否`；保留全部 JS 钩子 id。
- `config_edit.html` 完整重写：Bootstrap `panel-group/panel` 手风琴 → `cw-card + panel-collapse`（保留 Bootstrap collapse 手风琴机制与 `data-toggle="collapse"`）；`form-control` → `cw-input/cw-select`；`btn btn-default` → `cw-btn`；glyphicon folder-open → Lucide；保留全部 `name/id/data-control/data-related/data-controlall/intend-form`。**已用 feature 全开渲染校验所有字段保留。**
- `src/input.css`：新增 `.cw-book-grid`；`.cw-main__inner` 加 `max-width:1440px; margin:auto`（content 统一限宽）。

**保留的 legacy**（勿动，非本轮范围）：`modal_dialogs.html`（Bootstrap modal 体系，jQuery 驱动）、admin.html 内 `RestartDialog/ShutdownDialog/StatusDialog`、`filechooser_modal()`、`user_table/book_table` 的 Bootstrap-Table 插件、`book_edit/user_edit/config_db/grid.html`（仍旧）。

**待做（P13 未完）**：`book_edit/user_edit/config_db/grid.html` 收口；首页「我的收藏」区块（需书架数据）；全站截图为验收（Playwright 暂缺）；`modal_dialogs.html` Alpine 化需先退 legacy JS（大工程，谨慎）。

## 1. 已提交 && 已推送（origin/rewrite）—— P0/P1/P2/P3 全部完成
- `d44bccd` P0 基线：vendored `calibre-web/` + Tailwind 链 + 主题/组件初版 + 旧 patch 归档
- `7f0b737` P0 施工：`src/input.css` 令牌+基础组件、`tailwind.css`、vendored `alpine.min.js`/`lucide.min.js`、`js/theme.js`、`js/ui.js`、`postcss.config.js`
- `81fff12` P1 Design System：BookCard/Table/Dialog/Drawer/Dropdown/Toast/Tabs/Pagination + Layout 原语（`cw-app/cw-sidebar/cw-main/cw-header/cw-page-header`）
- `f8cf47f` P2 App Shell：`layout.html` 重写为 App Shell（Sidebar/Drawer/Header/搜索/主题切换/账户菜单）+ doc（**无 `base.html`**，App Shell 内聚在 `layout.html`）
- `bf5d649` **P3 Library**：`index.html` 书卡重皮肤（`cw-book-card` 响应式网格 + `cw-status-badge` 未读/在读/已读，`entry[2]` read_status 驱动）+ 文档更新
- `73091b8` **P4 Book Detail**：`detail.html` 重皮肤（`cw-detail__layout` 封面居左/元数据居右 + 操作栏 `cw-btn-*` + 封面状态徽章 已读/未读；保留全部 id/表单/`data-*` 钩子保 `details.js`/`main.js`/`fullscreen.js` 行为）+ 文档更新
- `bb2283b` **P7 Library navigation**：`list.html` 首字母导航列表重皮肤（`cw-nav-item` 名称+数量徽章，保留 `filter_list.js` 钩子）+ `author.html`/`shelf.html` 书卡改 `cw-book-card`
- `P8` **Batch** ✅ 详见 `docs/ui-rewrite/08-phase8.md`（见下 §4 描述）

## 2. P3 范围裁定（会话确认，勿回退）
- 带封面书库网格实际渲染在 `index.html`（各库路由均 render 它）；`grid.html`/`list.html` 是作者/系列/标签的**首字母浏览视图**（无封面、无 Grid⇄List 切换）→ **归 P7**。
- P3 落在 `index.html` 书卡；`index.html` 的 Home 板块拆解（继续阅读/最近/收藏）留待 **P5**。
- P3 未做：Batch Action Bar、Grid⇄List 切换、Alpine 批量选中、键盘导航（待 P10 HTTP/JSON 化时一并强化）。
- 状态徽章映射（P3 书库网格）：`entry[2]==0`→unread(gray)、`==2`→reading(green `bg-success/10`)、`==1`→finished(blue `bg-primary/10`)。
- **P4 状态徽章为 2 态**：详情页 `show_book` 把 `entry.read_status` 设成**布尔**（`read_book == STATUS_FINISHED`），故详情徽章只显示 已读/未读（`cw-status-badge--finished/--unread`），无"在读"态。

## 3. 验证方法（P3/P4 已通过）
- 构建：`cd /opt/calibre-stack/calibre-web && npm run build` → `tailwind.css` 现 **29683 B**
- 渲染冒烟脚本（可复用，适配任意继承 `layout.html` 的模板）：
  - `/tmp/opencode/smoke_index.py`（P3 书库网格模板）
  - `/tmp/opencode/smoke_detail.py`（P4 详情模板）
  - 方式：裸 Flask app(template_folder=cps/templates) + `register_blueprint(cps.jinjia.jinjia)` 拿全部自定义 filter/global，override 部分 filter 为稳定桩，`test_request_context` 内 render。
  - **关键桩坑**：`current_user.is_anonymous`/`is_authenticated`/`shelf` 须是 **property**（非方法）——本 Jinja **不会自动调用**零参方法（`not bound_method`=False，导致 `{% if not current_user.is_anonymous %}` 区块不渲染）；`_`/`gettext` 须支持 `**kwargs`（模板用 `_("...%(index)s...", index=...)`）；`formatdate` 需 override（depends babel extension）；`Shelf` 需 `.books.all()`（sidebar）。
  - 结果（P4）：`detail.html` render len=17805，`cw-status-badge`/`#have_read_cb`/`#archived_cb`/`#btnGroupDrop1`/`#readbtn`/`#edit_book`/`#add-to-shelf`/`template-shelf-add` 全 OK（`id="Download"` 仅单格式出现、`details.js` 因 url_for 桩为 `#` 属预期假阴性）。

## 4. 下一步（新会话必做）
1. **P5（Home）✅ 已完成**：首页 `index.html` 区块重组（继续阅读 / 最近阅读 / 最近添加）。
   - 用户已在会话中**批准一次极简后端改动**：`web.py` 新增 `get_home_reading()`（join `ub.ReadBook`），仅在首页 `page == 'newest'` 注入 `currently_reading`/`recently_read`。此批准仅限 P5 本次。
   - **未实现**：我的收藏区块（需书架数据）、`_reading-item`/`_book-card` include 组件拆分。
2. **P6（搜索 + 筛选）✅ 已完成**：首页/`search.html` 高密度结果列表 + 无结果态 + `Ctrl+K`/`/` 唤起搜索（`ui.js` `focusSearch()` + `layout.html` body keydown）。后端未改。
   - **未做**：筛选器 popover/bottom-sheet 重构（保留既有 `search_form.html` 高级搜索页）。
3. **P7（书库导航）✅ 已完成**：导航列表共用 `list.html` 重皮肤（`.cw-nav-item` 名称+数量徽章，保留 `filter_list.js` 全部钩子）+ `author.html`/`shelf.html` 书卡网格改 `cw-book-card` + `cw-author-bio`。后端未改。
4. **P8（Batch）✅ 已完成**：书库网格（`index.html`）书卡加复选框 + 底部批量操作栏（改标签/改系列/改作者/删除，复用既有 JSON 端点，不改后端）。
   - 新文件：`cps/templates/include/_batch-action-bar.html`、`cps/static/js/batch.js`（`calibreBatch()` Alpine 组件）；`index.html` 加 `x-data` 包裹 + `batch-checkbox` + `{% block js %}` 加载。
   - 样式：`src/input.css` 新增 `.batch-checkbox`/`.cw-batch-bar*`/`.cw-book-card--selectable`/`.cw-batch-grid`。
   - 冒烟：`/tmp/opencode/smoke_batch.py`（index.html render OK，全部 marker 通过）。
   - **偏差记录**：批量端点均为 JSON，故用 fetch 走既有 `edit-book.edit_list_book`/`delete_books_ajax`（非"表单提交"）；下载批量/收藏(书架) 后端无多书端点，暂缓 P10。
5. **P9（Auth + Admin）✅ 已完成**：登录/注册完整重皮肤（`.cw-auth__card` 居中卡片 + `.cw-auth__error` 错误态 + 保留全部 name/CSRF/submit/OAuth/忘记密码/魔法链接语义）；后台表格 `book_table.html`/`user_table.html` 叠加 `cw-table`/`cw-section-title`（不动 DataTable `<th data-*>` 结构）。后端未改。
   - 样式：`src/input.css` 新增 `.cw-auth*`、`.cw-field-label`。
   - 冒烟：`/tmp/opencode/smoke_auth.py`（login 含错误态 + register 全 marker OK）；`get_template` 编译 login/register/user_table/book_table 全通过。
   - **偏差/延后**：`admin.html`/`config_edit.html` 深度改版因改动面大，留待专项（防会话冻结风险）。
6. **P10（Custom Pages）✅ 已完成**：`async-upload` 自研页 `/tasks`（`tasks_page.html`）与 `/async-upload`（`upload_page.html`）重皮肤到全站 Design System——Bootstrap/蓝底 → `.cw-btn*`/`.cw-table`/状态徽章/`rgb(var(--*))` 令牌；两页共用 `calibre-theme` localStorage key（与 fork `theme.js` 同步）+ `themeBtn` + prefers-color-scheme。后端/`server.py`/nginx 全未改。
   - 关键：`tailwind.config.js` content 修复 `./async-upload` → `../async-upload`（否则 utilities 不生成）；重建 `tailwind.css`（38.9→39.3KB）。
   - 路由：`<link href="/static/css/tailwind.css">` 走 nginx `css` regex→fork:8083，与原有 `/static/css/bootstrap.min.css` 同源可解析。
   - 校验：两页所有 class 均解析（tailwind.css 或页面内联 `<style>`）；HTML 结构收拢 OK；构建通过。
7. **P11（A11y + Performance Audit）✅ 已完成（Code hard-fixes only）**：前端代码硬修复——唯一 `<h1>`+无跳级（index/search/author/shelf/detail/login/register）、移动 Drawer 焦点管理（`ui.js`）+`role="dialog"`/`aria-modal`、汉堡 `aria-expanded`/`aria-controls`、下拉 `role="menu"`/`menuitem`/`aria-haspopup`、OAuth 链接 `aria-label`+SVG `aria-hidden`；`loading="lazy"`/`prefers-reduced-motion`/`:focus-visible` 已在 P1 baseline 就位。后端未改；`tailwind.css` 无增量。
   - 校验：`node --check` + 6 组冒烟渲染全 OK + heading 静态校验 + `npm run build`。
   - **延后（§9 专项）**：Playwright + `@axe-core/playwright`、Lighthouse ≥90、1K/5K/10K 大书库基线 —— 缺测试基础设施，未实施；不阻塞 P12。
8. **P12（Production Cutover — Beta 8085 已完成；生产切产暂缓）**：见 `docs/ui-rewrite/12-phase12.md`。
   - ✅ **已完成**：Beta 并行实例 `/opt/calibre-web-beta/`（venv 复制 + prod app.db 快照 + **fork 根 `cps/` 覆盖**到 `site-packages/calibreweb/cps/` + app.db 端口改 8085）+ systemd 单元 `calibre-web-beta.service`（8085）+ 一键重搭脚本 `deploy/setup-beta.sh`。curl 验证 `127.0.0.1:8085` 登录页含新 UI（`cw-auth__card`/`cw-input`/`tailwind.css` 39282B），生产 8083 旧 UI 未受影响。
   - **打包缺陷（重要）**：fork `pyproject.toml`/`MANIFEST.in` 仍指上游 `src/calibreweb` 布局，本 fork 实为根 `cps/`→`pip install` 产出**空 wheel**。因此 Beta 用「直接覆盖根 `cps/`」部署；**真实切产前必须先修复 pyproject 打包**（`[tool.setuptools] packages + package-data`）。
   - **生产切产（8084/8083 上新 fork）暂缓**，待独立审批后执行（步骤见 12-phase12.md §2）。
9. 之后 P12 生产切产按 `docs/ui-rewrite/12-phase12.md` §2，commit + push。

## 5. 环境备忘
- 构建：`cd /opt/calibre-stack/calibre-web && npm install && npm run build`（产物提交，VPS 运行期无需 Node；node_modules 已 gitignore）
- 重新部署：`/opt/calibre-web/venv/bin/pip install --force-reinstall --no-deps /opt/calibre-stack/calibre-web`
- 模板是 `cps/templates/layout.html`（**无 `base.html`**）
- Bootstrap/jQuery 仍加载（渐进迁移保留）；Alpine/Lucide 已 vendored 本地
- 关键 CSS：`src/input.css` 顶层声明组件类（**勿用 `@layer components` 包裹**——本 Tailwind 3.4 会整体丢弃 `@apply`）
- 渲染冒烟测试桩需：`current_user.check_visibility/role_upload/role_admin/is_anonymous/name`、`g.allow_upload/allow_anonymous/allow_registration/current_theme/shelves_access/sidebar/config_authors_max`、`simple`/`entry[2]`、filters `shortentitle/formatfloat/music/last_modified/get_cover_srcset/get_series_srcset/cache_timestamp/url_for_other_page`
