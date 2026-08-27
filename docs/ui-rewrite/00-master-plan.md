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
| 后端改动 | **默认禁止**。UI Rewrite 期间禁止后端业务重构。仅在以下 4 种情形允许后端微调：① 当前 UI 无法合理获取必要数据；② 存在性能瓶颈；③ 现有接口无法支持无刷新交互；④ 修改不改变已有 API 语义，且有独立回归测试覆盖。任何后端改动须在该阶段「回测方法」中显式覆盖，并注明改动原因。 |
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

## 四、架构方案：fork 自维护模型

(保持原有内容不变)

## 五、Design System 前置（P1核心）

Design System 必须在 P1 阶段即刻锁定，所有后续 UI 组件必须复用这些标准，避免各页自行发明：

1. **设计令牌**：
   - Light/Dark 调色板（已在总纲 §六提供），所有颜色、间距、圆角通过 CSS 变量统一声明
   - `border-radius: 4–6px`（封面/按卡片），`text-xs`/`text-sm`/`text-base` 等字体层级
   - `spacing`：`px-2`/`px-4`/`py-2`/`py-4` 等间距体系
   - `border`：`border` / `border-2` / `border-gray-200` 等边框风格

2. **组件库**：
   - `Button`：若干变体（default/primary/outline/danger），`focus-visible` 焦点轮廓
   - `Input`：文本输入框，`focus-visible` 状态
   - `Badge`：状态徽章（未读/在读/已读），尺寸 `text-xs` / `px-2` / `py-1` / `rounded-2`
   - `BookCard` / `BookListItem`：封面 `rounded-4` / `object-cover` / `lazy-loading`，标题/作者/系列三行布局
   - `Table`：交替行色 `bg-white` / `bg-gray-50`，状态徽章列，操作按钮列
   - `Dialog` / `Drawer` / `Dropdown`：遮罩层、Esc 关闭、`aria-label`、`focus-visible` 焦点
   - `BookCover`：封面组件，`rounded-4` / `transition-transform` / `hover:scale-105`

3. **使用原则**：
   - 所有新增模板片段必须复用上述组件；不得自行编写 inline CSS/JS
   - 深色模式通过 `class="dark"` + CSS 变量 全局生效，组件须通过 `dark:` 前缀自动切换
   - 响应式断点：`sm: 640px` / `md: 768px` / `lg: 1024px` / `xl: 1200px`，Sidebar 在 `md` 以上可见，`md` 以下转抽屉

## 五、允许的后端改动（更严格）

后端改动**默认禁止**。UI Rewrite 期间禁止后端业务重构。仅在以下 4 种情形允许后端微调：① 当前 UI 无法合理获取必要数据；② 存在性能瓶颈；③ 现有接口无法支持无刷新交互；④ 修改不改变已有 API 语义，且有独立回归测试覆盖。任何后端改动须在该阶段「回测方法」中显式覆盖，并注明改动原因。

1. **继续阅读首页区块**
   - 新增 `web.currently_reading()` 或在 `index()` 注入 `currently_reading` 列表（按 `ub.BookProgress` 最近位置 / `ReadBook` 最近访问排序）
   - 影响：`cps/web.py`、`cps/db.py`（查询）、`cps/templates/index.html`
   - 比模板层近似更优雅，且数据准确

2. **书库列表数据序列化**
   - 现有 `books_list`/`index` 直接传 ORM 对象（含大量关联）到模板，模板复杂。引入轻量 dict 序列化减少模板复杂度
   - 影响：`cps/web.py`、`cps/db.py`
   - 分页已去除（全页加载）；若未来书库过大，可加虚拟滚动 / 分页 API（独立评估，不在本期强制）

3. **阅读状态即时切换**
   - 现有 `helper.edit_book_read_status` 已支持；前端用 Alpine 直接 `fetch` 调用，无整页刷新
   - 影响：仅前端交互（复用现有 API），后端可不改

4. **上传 / 任务**
   - async-upload 保持独立服务；`/tasks` 看板并入侧边栏（已做）。后端无需改，仅前端重皮肤
   - 若需更紧耦合（如任务进度实时推送），可加 SSE/轮询 API，独立评估

> 以上改动**不破坏**既有路由契约（`/api/upload`、OPDS、Kindle 发送、在线阅读等保持原样）。任何后端改动须在该阶段「回测方法」中显式覆盖，并注明改动原因。

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
| P0 | 基线与隔离 | fork；生产快照；8085 并行；Playwright 基础环境；现有功能基线 |
| P1 | Frontend Foundation | Tailwind；Design Tokens；Light/Dark；Typography；spacing；基础组件 |
| P2 | App Shell | Sidebar；Header；Search；Drawer；Responsive |
| P3 | Library | Grid；List；BookCard；Selection；Performance |
| P4 | Book Detail | Cover；Metadata；Actions；Reading status |
| P5 | Home | Continue Reading；Recent；Favorites |
| P6 | Search / Filter | Search；Ctrl+K；Filter |
| P7 | Library Navigation | Authors；Categories；Tags；Series；Shelves |
| P8 | Batch Operations | UI only（后续再考虑 API 化） |
| P9 | Auth + Admin | Login；Register；Admin |
| P10 | Custom Pages | tasks / upload |
| P11 | Accessibility / Performance Audit | WCAG；Lighthouse；Playwright；large library benchmark |
| P12 | Production Cutover | full regression；nginx switch；rollback |

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
