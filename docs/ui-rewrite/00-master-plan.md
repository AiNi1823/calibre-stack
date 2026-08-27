# Calibre-Web UI/UX 全面升级 — 总体规划（00-master-plan）

> 状态：**规划文档（未施工）**
> 更新：2026-08-26
> 范围：仅文档。所有代码改动在对应阶段施工时执行，本文档不落地任何代码。

---

## 〇、决策记录（来自需求确认）

| 项 | 决策 |
|----|------|
| 导航布局 | 改为**左侧 Sidebar**（220–240px），移动端 Drawer |
| 技术栈 | **全量 Tailwind 重写**（非 Bootstrap 叠加） |
| 分支/仓库 | 独立 fork（`AiNi1823/calibre-web`）+ 独立分支 `ui-tailwind`；回测前不碰生产 |
| 后端改动 | **允许**。若某功能的操作逻辑/依赖关系有更优雅、高效、极简的实现，可大胆改后端（路由/ORM/序列化/API），不限于前端重皮肤 |
| 交付物 | 本规划 + 分阶段施工文档；每阶段明确「影响文件 / 回测方法 / 推进标准」 |

---

## 一、目标

把自部署 Calibre-Web（0.6.27）从「Bootstrap 3 老界面」升级为：

- 现代、专业、简洁的**个人数字图书馆**
- 内容优先、封面优先、操作效率优先、视觉克制
- Desktop / Tablet / Mobile 均可用
- 暗色模式完整
- 保留**全部现有功能**（浏览/搜索/下载/在线阅读/收藏/标签/批量/上传/任务/Admin）

视觉禁令（沿用原始 prompt）：禁止 AI SaaS 风、大渐变、玻璃拟态、超大圆角、大阴影、花哨动画、过度留白、彩色按钮堆、为视觉牺牲信息密度。

---

## 二、当前前端架构（实测，非假设）

| 维度 | 现状 |
|------|------|
| 后端框架 | Flask + Jinja2（服务端渲染，非 SPA） |
| 前端框架 | **Bootstrap 3** + **Glyphicons** + **jQuery / Bootstrap JS** |
| 版本 | `calibreweb` 0.6.27（上游 `github.com/janeczku/calibre-web`，GPL-3.0，仍在维护） |
| 模板 | `cps/templates/*.html`，全部 `{% extends "layout.html" %}` |
| 模板目录 | 硬编码 `TEMPLATES_DIR = cps/templates`（**无内置覆盖钩子**）→ 改模板即等于改包 |
| 静态资源 | `cps/static/{css,js}`：`main.js`(31K) `table.js`(52K) `uploadprogress.js` `filter_grid.js` `filter_list.js` 等 |
| 已具备功能 | Grid+List 视图、简单/高级搜索、详情页、阅读状态 `ub.ReadBook`、书架/收藏 `shelf`、系列/作者/标签/分类、在线阅读（epub/pdf/cbr/txt/djvu/mp3）、批量选择/编辑、下载/发 Kindle/编辑/删除、Admin |

> **关键推论**：因模板目录硬编码且无覆盖机制，「改前端」必然改到 pip 包。因此采用 fork 自维护模型（见第四节），从根本上消除「升级覆盖改动」问题。

---

## 三、原始 prompt 24 节 → 现实校验

| 原始要求 | 现状判定 | 处理 |
|----------|----------|------|
| 侧边栏导航 | 现有顶部 navbar | **新建**（决策） |
| Grid / List 视图 | 已有 | 重皮肤（可顺带精简卡片 DOM） |
| 全局搜索 + Ctrl+K | 已有简单搜索 | 重皮肤 + Ctrl+K（纯前端 JS） |
| 书籍详情 | 已有 | 重皮肤 |
| 阅读状态 / 进度 | 已有 `ub.ReadBook.read_status` + 阅读进度 | 重皮肤；首页「继续阅读」区块见后端改动 |
| 继续阅读 / 最近阅读 | 无首页区块 | **新增**（后端轻量查询，见 §五） |
| 收藏 / 书架 | 已有 `shelf` | 重皮肤 |
| 系列 / 作者 / 标签 / 分类 | 已有 | 重皮肤 |
| 批量操作 | 已有（list + book_table） | 重皮肤 + 强化 BatchActionBar（可改 JSON API，见 §五） |
| 在线阅读 | 已有多格式阅读器（独立页面） | **保持不动**，仅外壳/退出条统一 |
| 暗色模式 | 仅 `theme==1`（blur/plex 风，非真暗色） | **新建** 真暗色（CSS 变量 + 用户偏好持久化） |
| Lucide 图标 | Glyphicons | **替换**（新组件用 Lucide；渐进，不一次性全量替换） |
| shadcn/ui | React 组件库 | **不可直接用**（非 SPA）→ 用 Tailwind 复刻其视觉语言（中性色 / 细边框 / 小圆角 / focus ring） |
| Tailwind CSS | 无 | **全量引入**（决策） |
| 上传 / 任务页 | 自研 `/tasks` `/async-upload`（async-upload:8086） | 重皮肤，独立于 fork |
| 响应式 / 无障碍 / 性能 | Bootstrap3 部分具备 | 按 prompt 标准补齐 |

---

## 四、架构方案：fork 自维护模型

### 4.1 仓库与分支
- **fork**：`github.com/AiNi1823/calibre-web`（fork 自 `janeczku/calibre-web`，对齐 0.6.27）
- **分支**：`ui-tailwind`（从对应 tag / master 切出）
- **现有 `calibre-stack` 仓库**：不动主分支；仅新增 `docs/ui-rewrite/*` 规划与施工文档；自研页重皮肤在 `calibre-stack/async-upload/*.html`（独立阶段）

### 4.2 前端技术栈（在 fork 内）
- **Tailwind CSS**：新增 `package.json`（tailwindcss + postcss + autoprefixer）、`tailwind.config.js`、`src/input.css` → 构建产物 `cps/static/css/tailwind.css`（**提交构建产物**，VPS 运行期无需 Node）
- **Alpine.js**（≈15KB）：替换 jQuery / Bootstrap JS，承载 dropdown / drawer / modal / tabs / 批量选择等交互（SSR HTML 友好，无构建负担）；**保留** `uploadprogress.js` 核心逻辑（改为 Alpine 或保留精简版）
- **Lucide**：静态 SVG / `lucide-static` 替换 Glyphicons
- **设计令牌**：在 `tailwind.config.js` 定义 light/dark 调色板（沿用 prompt 的 `--background/--surface/--primary/...`）；暗色靠 `class="dark"` + CSS 变量
- **不引入 React/Vue**：Calibre-Web 服务端渲染，shadcn 仅取其视觉语言，用纯 HTML + Tailwind 实现

### 4.3 升级覆盖 / 重部署解决方案
- **覆盖**：包即我们的 fork 代码。上游更新 = `git fetch upstream && merge` 进 fork `master`，再 rebase `ui-tailwind`。覆盖问题消失。
- **重部署**：`pip install --force-reinstall --no-deps git+https://github.com/AiNi1823/calibre-web.git@ui-tailwind` → `systemctl restart calibre-web`
- **nginx 不变**：`auth_request`、`/tasks`、`/api/upload` 路由 URL 不变（`/tasks`、`/api/upload` 由 async-upload:8086 提供，不在 fork 内）
- **自研页**：`/tasks`、`/async-upload` HTML 在 `calibre-stack`，独立重皮肤

---

## 五、允许的后端改动（更优雅实现方向）

后端改动**允许**，以下为推荐方向（每项下标注预期影响文件，具体在阶段文档落实）：

1. **继续阅读首页区块**
   - 新增 `web.currently_reading()` 或在 `index()` 注入 `currently_reading` 列表（按 `ub.BookProgress` 最近位置 / `ReadBook` 最近访问排序）
   - 影响：`cps/web.py`、`cps/db.py`（查询）、`cps/templates/index.html`
   - 比模板层近似更优雅，且数据准确

2. **书库列表数据序列化**
   - 现有 `books_list`/`index` 直接传 ORM 对象（含大量关联）到模板，模板复杂。引入轻量 dict 序列化减少模板复杂度
   - 影响：`cps/web.py`、`cps/db.py`
   - 分页已去除（全页加载）；若未来书库过大，可加虚拟滚动 / 分页 API（独立评估，不在本期强制）

3. **批量操作 JSON API**
   - 现有批量编辑走 form post 整页刷新。新增 `POST /api/books/batch`（操作：标签/分类/收藏/删除/状态）供 Alpine 调用，体验更顺
   - 影响：`cps/web.py`（新增路由）、`cps/editbooks.py` / `cps/helper.py`（复用现有编辑函数）
   - 前端 BatchActionBar 用 Alpine `fetch` 调用，无整页刷新

4. **暗色模式用户偏好**
   - 扩展用户偏好持久化 `ui_theme`（light/dark），替代仅 `current_theme`（0/1 blur）
   - 影响：`cps/web.py`（context processor 注入 `ui_theme`）、`cps/db.py`（`ub.User` 加列或复用 `ui_theme` 设置）、前端 theme toggle 写回 API
   - 保持 `current_theme` 兼容（blur 主题可保留为可选项）

5. **阅读状态即时切换**
   - 现有 `helper.edit_book_read_status` 已支持；前端用 Alpine 直接 `fetch` 调用，无整页刷新
   - 影响：仅前端交互（复用现有 API），后端可不改

6. **上传 / 任务**
   - async-upload 保持独立服务；`/tasks` 看板并入侧边栏（已做）。后端无需改，仅前端重皮肤
   - 若需更紧耦合（如任务进度实时推送），可加 SSE/轮询 API，独立评估

> 以上改动**不破坏**既有路由契约（`/api/upload`、OPDS、Kindle 发送、在线阅读等保持原样）。任何后端改动须在该阶段「回测方法」中显式覆盖。

---

## 六、设计系统令牌（摘要，详见 phase01）

Light：
```
--background:#F8F8F7  --surface:#FFFFFF  --surface-secondary:#F3F3F1
--border:#E5E5E3     --text-primary:#1F1F1F  --text-secondary:#737373  --text-muted:#A3A3A3
--primary:#2563EB    --danger:#DC2626  --success:#16A34A
```
Dark（`class="dark"`）：
```
--background:#111111  --surface:#181818  --surface-secondary:#202020
--border:#2A2A2A     --text-primary:#E5E5E5  --text-secondary:#A3A3A3  --text-muted:#737373
```
约束：主色仅用于当前导航 / 主按钮 / 链接 / 选中 / 进度 / focus；封面圆角 4–6px；动画 100–200ms。

---

## 七、阶段索引（详见 `01-phases.md`）

| Phase | 标题 | 一句话 |
|-------|------|--------|
| P0 | 脚手架 | fork+分支；Tailwind 构建链；设计令牌；删 Bootstrap/Glyphicons 引用；`base.html` 壳 |
| P1 | 布局 | 左侧 Sidebar + Header + 移动 Drawer；替换 `layout.html` |
| P2 | 设计系统组件 | 可复用 Tailwind+Alpine 片段（button/badge/modal/drawer/table/progress/bookcard/booklist） |
| P3 | 书库 Grid/List | 重皮肤 `grid.html`/`list.html`；封面/状态徽章；Grid⇄List |
| P4 | 书籍详情 | 重皮肤 `detail.html`；操作优先级 |
| P5 | 首页 | `index.html`：继续阅读/最近添加/最近阅读/收藏/发现（含后端查询） |
| P6 | 搜索+筛选 | 全局搜索 + Ctrl+K；筛选 Popover |
| P7 | 导航页 | author/list(分类)/shelf(收藏)/系列/标签 重皮肤 |
| P8 | 登录/注册 | `login.html`/`register.html` 重皮肤 |
| P9 | 管理后台 | admin/book_table/user_table/config_edit 重皮肤（功能不变） |
| P10 | 自研页 | `/tasks` `/async-upload` HTML 对齐新设计 |
| P11 | 暗色+响应式+无障碍 | `class="dark"` 切换；断点；aria/focus/ESC |
| P12 | 回归+切换 | 8085 并行回测；全绿后切 8084；合 fork master 打 tag |

---

## 八、全局回归与隔离策略（不影响现有项目）

- **并行实例**：VPS 另起 venv + 端口 **8085**，装 fork `ui-tailwind`，指向 **metadata.db 副本**（回归期不写生产库）
- **nginx**：加 `/beta` → 8085；生产 `:8084` → 8083 旧 UI 并行
- **全局回测清单**（每阶段增量 + P12 全量）：
  登录 / 权限(普通+管理员) / 书库浏览(Grid+List) / 搜索(简单+高级+Ctrl+K) / 书籍详情 / 下载 / 在线阅读(epub/pdf) / 收藏(书架) / 标签 / 批量编辑 / 上传(`/api/upload` 经 nginx) / 任务页 `/tasks` / Admin(书表/用户/配置)
- **切换门禁**：P12 全绿 → nginx `:8084` 反代切 8085，停 8083；fork `ui-tailwind` 合回 `master` 打 tag
- **回滚**：任一阶段出问题，`/beta` 不影响生产；全量切换后回滚 = nginx 切回 8083

---

## 九、风险与缓解

| 风险 | 缓解 |
|------|------|
| Alpine 复刻原 jQuery 交互遗漏 | 逐页对照 `main.js`/`table.js`/`uploadprogress.js` 行为写回测 |
| Tailwind 构建产物未提交导致样式缺失 | CI/本地构建后 `git add cps/static/css/tailwind.css` |
| 后端改动引入回归 | 每阶段「回测方法」显式覆盖改动面；8085 并行 |
| fork 与上游漂移 | 定期 `fetch upstream`；仅在 `master` 合 upstream，`ui-tailwind` rebase |
| 大书库 DOM 过多 | 封面 lazy-load + skeleton；必要时后续评估分页 API（不在本期强制） |

---

## 十、文档索引

- `00-master-plan.md`（本文件）— 总体规划 / 决策 / 架构 / 后端改动政策 / 全局回归
- `01-phases.md` — 分阶段施工文档（P0–P12，每阶段含：目标 / 影响文件 / 后端改动 / 实施要点 / 回测方法 / 推进标准 / 下一步门禁）
