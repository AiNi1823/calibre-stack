# Calibre-Web UI 升级 — Phase 3：书库（Library）

## 0. 目标
- 重皮肤**书库书网格**（封面+元数据+状态徽章），板式响应式
- **范围裁定（会话确认）**：本 fork 中带封面的书库网格实际渲染在 `cps/templates/index.html`（`web.books_list`、各库路由均 render `index.html`）；而 `grid.html`/`list.html` 是「作者/系列/标签」首字母浏览视图（无封面、无 Grid⇄List 切换）。→ **P3 落在 `index.html` 的书卡**；`grid.html`/`list.html` 的首字母视图归 P7（Library Navigation）。`index.html` 的 Home 板块拆解（继续阅读/最近/收藏）留待 P5。
- 封面更显重点：圆角 4–6px，裁剪保持比例，`loading="lazy"`（沿用 `image.html` 的 `book_cover` 宏）
- 状态徽章：未读/在读/已读 用颜色极简标记（不使用鲜艳色）
- **未做（后续评估）**：Batch Action Bar（批量操作栏）与 Grid⇄List 切换暂未在本阶段落地——书网格由后端/既有脚本控制，批量操作待 P10 HTTP/JSON 化时一并强化

## 1. 影响项目文件
- **Fork 内（已实现 @ 本阶段提交）**：
  - `cps/templates/index.html`（重写书卡：`cw-book-card` 网格 + `cw-book-cover` + `cw-book-card__meta` + `cw-status-badge`；Random 与主列表两处书卡统一）
  - `cps/static/css/input.css`（新增 `cw-book-card__meta`、`cw-status-badge`/`--unread`/`--reading`/`--finished`）
  - `cps/static/css/tailwind.css`（`npm run build` 编译产物，~28KB）
- **未做 / 后续**：`grid.html`、`list.html`（归 P7）、`_book-card.html`/`_batch-action-bar.html`（暂未拆分，书卡内联在 `index.html`）

- **calibre-stack（暂不涉及，P10 处理）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 实施要点（已实现于 index.html）
1. **书卡结构**（index.html 书网格）：
   - 外层改为 Tailwind 响应式网格：`grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5`
   - 每卡 `article.cw-book-card`：封面 `a.cw-book-cover`（`aspect-[2/3]`、`rounded-4`、`object-cover`、`loading="lazy"`、hover 轻微放大——沿用 P1 BookCover 原语）
   - 元数据区 `div.cw-book-card__meta`：`.cw-book-title`（单行截断）、`.cw-book-author`、`.cw-book-meta`（系列，可选）+ `.cw-status-badge`
   - 保留 `data-toggle="modal" data-target="#bookDetailsModal"`（`simple=false` 时）与 `#books`/`#books_rand` 标识；`{% if simple==false %}` 未变

2. **状态徽章**（`cw-status-badge`，基于 `entry[2]` = `ub.ReadBook.read_status`）：
   - `read_status == 0`（`STATUS_UNREAD`）→ `cw-status-badge--unread`：`bg-surfaceSecondary text-textSecondary`（未读）
   - `read_status == 2`（`STATUS_IN_PROGRESS`）→ `cw-status-badge--reading`：`bg-success/10 text-success`（在读）
   - `read_status == 1`（`STATUS_FINISHED`）→ `cw-status-badge--finished`：`bg-primary/10 text-primary`（已读）
   - 文字：`Reading` / `Read` / `Unread`（走 `_(...)`，可翻译）；尺寸 `text-[10px]`、`px-1.5 py-0.5`

3. **未做（后续阶段）**：Grid⇄List 切换、Batch Action Bar、列表视图、Alpine 批量选中、键盘导航——书区模板行为由后端/既有脚本控制，批量操作待 P10 HTTP/JSON 化时一并强化。

## 2. 后端改动
- 无。`index.html` 数据（`entries`、`entries[0]`、`entry[2]` read_status）完全不动；仅改模板呈现样式。

## 3. 回测方法
1. **本地构建**：`npm run build`，校验 `cps/static/css/tailwind.css` 含 `cw-book-card__meta`/`cw-status-badge(--unread/--reading/--finished)`
2. **渲染冒烟**：Jinja render `index.html`（stub 补 `g.allow_upload` + `current_user.*` + `entry[2]`=0/1/2），断言书卡三状态徽章、`grid grid-cols-2`、`bookDetailsModal`、`loading="lazy"` 均出现
3. **浏览器验证**：
   - Grid 视图：封面正常，圆角 4–6px，状态徽章颜色正确，Hover 有轻微放大
   - 三端（桌面/平板/移动）：书网格列数响应式（2/3/4/5）
   - 无控制台 JS 错误

## 3. 推进标准（进入 P4 的门禁）
- index.html 书网格在桌面/移动端均能正常渲染，响应式列数正确
- 状态徽章颜色符合设计（未读/在读/已读）且与 `entry[2]` 映射一致
- 封面 lazy-loading + hover 放大正常；无控制台错误

## 4. 下一步门禁
- P4（书籍详情页）：重皮肤 `detail.html`（封面+元数据+操作按钮优先级：阅读/下载/收藏/更多）

## 备注
- 书卡内联在 `index.html`（P3 阶段未拆 include）；若后续多处复用可抽 `_book-card.html`。
- `cw-status-badge` 颜色走 P1 令牌（`bg-surfaceSecondary`/`bg-success/10`/`bg-primary/10`），深浅色自动互换；若要精确设计色可后续在 `tailwind.config.js` 的 `theme.extend.colors` 统一声明。

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P3 并经验证后，可进入 P4.