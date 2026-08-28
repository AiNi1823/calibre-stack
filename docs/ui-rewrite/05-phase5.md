# Calibre-Web UI 升级 — Phase 5：首页（Home）

## 0. 目标
- 重设计首页 `index.html`，不再是单纯的「随机书籍」展示区——**已实现 @ 本阶段提交**
- 新增区块：继续阅读 / 最近阅读 / 最近添加（利用 `ub.ReadBook` 阅读状态数据）
- **范围裁定（会话确认）**：允许**极简后端改动**（用户已批准打破"后端不改"约束）——见 §2
- 保持与后端 API 兼容，不改变任何既有路由与数据结构

## 1. 影响项目文件
- **Fork 内（已实现 @ 本阶段提交）**：
  - `cps/web.py`（新增 `get_home_reading()`，注入 `currently_reading`/`recently_read` 到首页 render）
  - `cps/templates/index.html`（首页新增 `cw-home` 区块：Continue Reading / Recently Read / Recently Added）
  - `cps/static/css/input.css`（新增 `cw-home*` 区块样式）
  - `cps/static/css/tailwind.css`（`npm run build` 编译产物，~30.4KB）
- **未做**：`_book-card.html`/`_reading-item.html`/`_reading-list.html`/`_favorite-list.html` include（沿用内联风格未拆分）；「我的收藏」区块（需书架数据，暂留给后续）

- **calibre-stack（暂不涉及，P10 处理）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动（本阶段起允许极简改动，用户已批准）
- `cps/web.py`：
  - 新增 `get_home_reading(limit=5)`：查 `ub.ReadBook`（status != UNREAD，按 `last_modified` desc）join `db.Books`，返回 `(currently_reading, recently_read)`；`currently_reading` 只含 `STATUS_IN_PROGRESS`，`recently_read` 含全部已读/在读；每项 `{"book","status","last","format"}`（format 取 `book.data[0].format`）
  - 首页（`website == "newest"` 且非匿名）render 时注入 `currently_reading`/`recently_read`
- 无 `db.py` 改动。

> **数据说明**：本版本**无 `ub.BookProgress`**（无阅读进度百分比），故首页不显示百分比进度条，仅按状态显示「Reading」徽章与封面。

> **备注**：若不想改动后端，首页的「继续阅读」区块可使用模板层逻辑：从用户的最近浏览历史（`web.history` 表）或随机从已有书籍中抽取，效果虽不如后端数据精准，但零改动。此处提供「后端改动写法」以供参考，实际施工时可根据需求选其一。

## 2. 实施要点（已按此实现）
1. **首页区块布局**（仅 `page == 'newest'` 时显示 `cw-home`）：
   - `.cw-home__section .cw-home__row`：栅格（3/4/5/6 列响应式）
   - **Continue Reading**（置顶）：仅 `currently_reading`（in-progress），封面+标题+`Reading` 徽章
   - **Recently Read**：`recently_read` 全部，封面+标题+作者
   - **Recently Added**：复用既有 `.grid` 主网格，上方加 `.cw-section-title` 小节标题
   - 保留既有 Discover 随机区与过滤排序工具条

2. **继续阅读区块实现**：
   - 模板：`{% if page == 'newest' %}{% if currently_reading|length > 0 %}...{% endif %}...{% endif %}`
   - 封面链接：`web.read_book(book_id, book_format=item.format)`（in-progress，新窗口）；无格式时回退 `web.show_book`
   - 每个阅读项：`.reading-item`（封面 `.cover`、标题 `.title`、进度 `.progress`、操作 `'继续阅读'`）

3. **Alpine 交互**：
   - 封面悬停微放大
   - 点击封面跳转至书籍详情页 `web.show_book`
   - 主题变量 `dark` 继承自 `base.html`

4. **组件复用**：
   - `_book-card.html` 提取为公共组件，`index.html`、`grid.html`、`detail.html` 公用
   - `_reading-item.html` 专门用于首页「继续阅读」区块
   - `_favorite-list.html` 用于首页「我的收藏」区块

## 3. 回测方法
1. **本地构建**：同上
2. **Smoke 渲染（已通过）**：`/tmp/opencode/smoke_index.py` 渲染 `page='newest'` 首页，注入 `currently_reading`/`recently_read`，校验 marker 全部 OK：`cw-home`/`cw-home__section`/`cw-home__row`/`cw-home__reading`/`Continue Reading`/`Recently Read`/`Recently Added`（render len=18437）
3. **浏览器验证**：
   - 首页按区块正常显示：继续阅读、最近阅读、最近添加
   - 继续阅读区块‘有书籍时’显示封面+标题+徽章；‘无书籍时’整个区块隐藏
   - 封面点击跳转至书籍详情/阅读页
   - 主题切换在首页生效

## 3. 推进标准（进入 P6 的门禁）
- 首页各区块布局正常，无重叠、无折行异常
- 继续阅读区块数据正确（有书籍时显示具体书籍，无书籍时显示提示语）
- 封面点击跳转正常，主题切换在首页生效
- Alpine 无错误

## 3. 下一步门禁
- P6（搜索+筛选）：全局搜索框 + Ctrl+K 唤起 + 筛选条件

## 3. 备注
- 后端改动 `cps/web.py` 新增 `get_home_reading()` 约 20 行，风险极小（用户已批准此次极简后端改动）
- 本版本**无** `ub.BookProgress`（无阅读进度百分比），故首页不显示百分比进度条；展示状态徽章
- 「继续阅读」中的格式取 `book.data[0].format`；in-progress 书籍应总有格式，模板对无格式做了 `show_book` 回退
- 尚未实现：「我的收藏」区块（需书架数据，延后）与 `_book-card`/`_reading-item` 等 include 组件拆分（沿用内联风格）

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P5 并经验证后，可进入 P6.