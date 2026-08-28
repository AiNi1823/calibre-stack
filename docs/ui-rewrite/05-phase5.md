# Calibre-Web UI 升级 — Phase 5：首页（Home）

## 0. 目标
- 重设计首页 `index.html`，不再是单纯的「随机书籍」展示区
- 成为用户最关心的入口：继续阅读 / 最近添加 / 最近阅读 / 我的收藏 / 推荐/发现
- 利用已有的阅读进度数据 `ub.ReadBook` 与 `ub.BookProgress`，展示「继续阅读」
- 保持与后端 API 的兼容，不改变任何路由与数据结构

## 1. 影响项目文件
- **Fork 内**：
  - `cps/templates/index.html`（首页完整重写：区块布局、Alpine交互、lazy-loading）
  - `cps/templates/layout.html`（继承 `index.html`，保持 `x-data` 状态同步，主题切换）
  - `cps/templates/include/_book-card.html`（提取为可复用组件，复用于首页、网格、详情页）
  - `cps/static/css/tailwind.css` / `input.css`（新增首页区块样式：`.hero-section`、`.reading-item`、`.favorite-item` 等）
  - `cps/templates/include/_reading-item.html`（新增：继续阅读项组件，封面+标题+进度+操作）
  - `cps/templates/include/_reading-list.html`（新增：最近添加/最近阅读区块组件）
  - `cps/templates/include/_favorite-list.html`（新增：我的收藏区块组件）

- **calibre-stack（暂不涉及）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- **极简后端改动**（高度推荐，虽属「后端改动」但改动极其微小）：
  - `cps/web.py`：新增 `def currently_reading_books()`，按 `ub.BookProgress.read_progress` 降序排列，返回最近阅读过的书籍列表（最多 5 本），用于首页「继续阅读」区块
  - `cps/web.py` 中 `index()` 函数：在现有上下文 `context['currently_reading'] = currently_reading_books()` 中注入
  - `cps/db.py`：无需改动（`ub.BookProgress` 表已存在，仅新增一个轻量查询）

> **备注**：若不想改动后端，首页的「继续阅读」区块可使用模板层逻辑：从用户的最近浏览历史（`web.history` 表）或随机从已有书籍中抽取，效果虽不如后端数据精准，但零改动。此处提供「后端改动写法」以供参考，实际施工时可根据需求选其一。

## 2. 实施要点
1. **首页区块布局**：
   - `.hero-section`：显示「继续阅读」区块（置顶）
   - `.recent-adding`：最近添加的 4 本书（封面+标题+作者）
   - `.recent-reading`：继续阅读的 4 本书（封面+标题+进度条）
   - `.favorite-list`：我的收藏的 4 本书（封面+标题）
   - `.recommend-discovery`：推荐/发现区（随机书籍 + 分类入口）

2. **继续阅读区块实现**（以后端改动版为例）：
   - 在 `index.html` 模板顶部：`{% if currently_reading %} ... {% endif %}`
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
2. **浏览器验证**：
   - 首页按区块正常显示：继续阅读、最近添加、最近阅读、收藏、推荐/发现
   - 继续阅读区块‘有书籍时’显示 4 本书的封面+标题+进度；‘无书籍时’显示「暂无继续阅读记录」
   - 封面点击跳转至书籍详情页
   - 主题切换在首页生效
   - 点击封面跳转至书籍详情页正常

## 3. 推进标准（进入 P6 的门禁）
- 首页各区块布局正常，无重叠、无折行异常
- 继续阅读区块数据正确（有书籍时显示具体书籍，无书籍时显示提示语）
- 封面点击跳转正常，主题切换在首页生效
- Alpine 无错误

## 3. 下一步门禁
- P6（搜索+筛选）：全局搜索框 + Ctrl+K 唤起 + 筛选条件

## 3. 备注
- 后端改动 `cps/web.py` 仅 10 行左右，风险极小， strongly 推荐采用「有后端查询」版本，以获得最佳用户体验
- 若不想改后端，「模板层实现」可通过 `ub.BookProgress` 相关字段的模板层推断，或随机从现有书籍列表中抽取 4 本展示「继续阅读」，效果虽不如后端查询精准，但零改动

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P5 并经验证后，可进入 P6.