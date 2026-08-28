# 续接文档 (HANDOFF) — 重启对话后从此继续

> 目标：让新会话立即知道施工到哪、还剩什么、如何收尾。
> 分支：`calibre-stack` `rewrite` 分支（`origin/rewrite` 远端已跟踪）。
> 施工对象：vendored 源码树 `calibre-web/`（Calibre-Web 0.6.27）。
> 约束：后端 `web.py/db.py/helper.py` 不改；UI 渐进迁移；每阶段 commit+push。

## 0. 会话卡死根因（重要）
`big-pickle` 模型在**超长上下文**（尤其大段 Python 拼接模板 + 反复调试文本）下生成退化、死循环，无报错、连接不断、静默 30 分钟级。
- **对策**：保持**极简、单步 bash 收尾**，不要一次性输出大段文本/并行巨调用。
- 若再卡：`tail -f /root/.local/share/opencode/log/opencode.log`。

## 1. 已提交 && 已推送（origin/rewrite）—— P0/P1/P2/P3 全部完成
- `d44bccd` P0 基线：vendored `calibre-web/` + Tailwind 链 + 主题/组件初版 + 旧 patch 归档
- `7f0b737` P0 施工：`src/input.css` 令牌+基础组件、`tailwind.css`、vendored `alpine.min.js`/`lucide.min.js`、`js/theme.js`、`js/ui.js`、`postcss.config.js`
- `81fff12` P1 Design System：BookCard/Table/Dialog/Drawer/Dropdown/Toast/Tabs/Pagination + Layout 原语（`cw-app/cw-sidebar/cw-main/cw-header/cw-page-header`）
- `f8cf47f` P2 App Shell：`layout.html` 重写为 App Shell（Sidebar/Drawer/Header/搜索/主题切换/账户菜单）+ doc（**无 `base.html`**，App Shell 内聚在 `layout.html`）
- `bf5d649` **P3 Library**：`index.html` 书卡重皮肤（`cw-book-card` 响应式网格 + `cw-status-badge` 未读/在读/已读，`entry[2]` read_status 驱动）+ `02-phase2.md`/`03-phase3.md` 文档更新

## 2. P3 范围裁定（会话确认，勿回退）
- 带封面书库网格实际渲染在 `index.html`（各库路由均 render 它）；`grid.html`/`list.html` 是作者/系列/标签的**首字母浏览视图**（无封面、无 Grid⇄List 切换）→ **归 P7**。
- P3 落在 `index.html` 书卡；`index.html` 的 Home 板块拆解（继续阅读/最近/收藏）留待 **P5**。
- P3 未做：Batch Action Bar、Grid⇄List 切换、Alpine 批量选中、键盘导航（待 P10 HTTP/JSON 化时一并强化）。
- 状态徽章映射：`entry[2]==0`→unread(gray)、`==2`→reading(green `bg-success/10`)、`==1`→finished(blue `bg-primary/10`)。

## 3. 验证方法（P3 已通过）
- 构建：`cd /opt/calibre-stack/calibre-web && npm run build` → `tailwind.css` 现 **28413 B**
- 渲染冒烟脚本留在 `/tmp/opencode/smoke_index.py`（可复用，适配任意继承 `layout.html` 的模板）：
  - 方式：裸 Flask app(template_folder=cps/templates) + `register_blueprint(cps.jinjia.jinjia)` 拿到全部自定义 filter/global，再 override 部分 filter 为稳定桩，`test_request_context` 内 render。
  - 结果：`index.html` render len=16523，`cw-book-card`/三态 `cw-status-badge`/`grid grid-cols-2`/`bookDetailsModal`/`loading="lazy"` 全 OK。

## 4. 下一步（新会话必做）
1. **P4（Book Detail）**：重皮肤 `cps/templates/detail.html` —— 封面 + 元数据 + 操作按钮优先级（阅读/下载/收藏/更多）。见 `docs/ui-rewrite/04-phase4.md`。
2. 完成后 `git add -A && git commit && git push origin rewrite`，并更新该阶段 doc 的影响文件/回测/实现项 + 本 HANDOFF。
3. 之后 P5→P12 按 `docs/ui-rewrite/0X-phaseX.md` 顺序，每阶段 commit+push。

## 5. 环境备忘
- 构建：`cd /opt/calibre-stack/calibre-web && npm install && npm run build`（产物提交，VPS 运行期无需 Node；node_modules 已 gitignore）
- 重新部署：`/opt/calibre-web/venv/bin/pip install --force-reinstall --no-deps /opt/calibre-stack/calibre-web`
- 模板是 `cps/templates/layout.html`（**无 `base.html`**）
- Bootstrap/jQuery 仍加载（渐进迁移保留）；Alpine/Lucide 已 vendored 本地
- 关键 CSS：`src/input.css` 顶层声明组件类（**勿用 `@layer components` 包裹**——本 Tailwind 3.4 会整体丢弃 `@apply`）
- 渲染冒烟测试桩需：`current_user.check_visibility/role_upload/role_admin/is_anonymous/name`、`g.allow_upload/allow_anonymous/allow_registration/current_theme/shelves_access/sidebar/config_authors_max`、`simple`/`entry[2]`、filters `shortentitle/formatfloat/music/last_modified/get_cover_srcset/get_series_srcset/cache_timestamp/url_for_other_page`
