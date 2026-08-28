# P13 — UI Consistency & UX Stabilization Pass（统一收口施工）

> 状态：**施工中（第二轮统一收口）**
> 更新：2026-08-28
> 分支：`calibre-stack` `rewrite`
> 对象：vendored 源码树 `calibre-web/cps/`（Calibre-Web 0.6.27）+ 自研页 `async-upload/`
> 原则：**暂停「按 Phase 序号逐个新增功能」**；改为让整个系统视觉与交互一致。

---

## 〇、为什么需要这一轮（根因）

P0–P12 已完成分阶段落地，但实际运行后暴露：**新旧 UI 混用、全局尺寸体系不统一、旧页面未迁移、首页残留旧模板结构**。

判断（来自实际代码审计，非文档假设）：

1. **UI Rewrite 未完成「全局替换」**——它是增量渐进迁移，Bootstrap/jQuery 仍作为兜底加载，新旧组件并存。
2. **首页出现「奇怪代码」**——优先怀疑模板迁移残留（裸 Jinja / 旧 Bootstrap DOM / 双 modal 体系并存），不是纯 CSS 问题。
3. **「界面比例不对」**——Design Token 未真正贯彻到所有页面（Sidebar/Header/Book grid/Book detail/Settings 各自 define 自己的 container/width）。
4. **Settings/Admin 仍陈旧**——`admin.html`/`config_edit.html`/`book_table.html`/`user_table.html` 仍为 Bootstrap 密集型表单/表格，未迁移。
5. **新旧组件体系混用**——同一产品内 H1 新 UI 与 Bootstrap 并存。

> 评价标准从「P3 完没完成？」转为：
> **「用户打开 Calibre-Web，是否感觉这是一个完整、统一、现代的电子书管理系统？」**

---

## 一、第一原则

目标不是「让每个页面变漂亮」，而是：

> **让整个 Calibre-Web 看起来像同一个现代电子书管理产品。**

所有页面共享同一套：Sidebar、Header、Content Container、Typography、Button、Input、Card、Modal、Table、Badge、颜色系统、spacing 体系、Dark Mode。

**禁止**出现 Bootstrap UI 与 Tailwind UI 并存。

---

## 二、审计：不要根据文档假设，直接查实际代码

第一轮已完成的逐页审计（后续施工须保持并及时更新）：

| 页面 | 当前 UI | Bootstrap 依赖 | Tailwind | Alpine | 备注 |
|------|---------|--------|----------|--------|------|
| layout.html | 新（App Shell） | 部分残留（bootstrap.min.css 仍加载） | ✅ | ✅ | modal/tasks 残留见 §三 |
| index.html | 新（home+书库网格） | 残留（`btn btn-primary` 排序条 / `glyphicon` / `data-toggle=modal`） | ✅ | ✅ | 排序条需重做 |
| detail.html | 新（P4） | 部分操作按钮 | ✅ | ✅ | 复核一致性 |
| search.html | 新（P6） | 低 | ✅ | ✅ | 复核 |
| login.html | 新（P9） | 低 | ✅ | ✅ | 复核 |
| register.html | 新（P9） | 低 | ✅ | ✅ | 复核 |
| list.html | 新（P7） | 低 | ✅ | ✅ | 复核 |
| author/shelf | 新（P7） | 低 | ✅ | ✅ | 复核 |
| **admin.html** | **旧** | **高** | 少 | 低 | **需重写（P13 重点）** |
| **config_edit.html** | **旧** | **高** | 少 | 低 | **需重写（P13 重点）** |
| **book_table.html** | **旧** | **高** | 少 | — | **需重写** |
| **user_table.html** | **旧** | **高** | 少 | — | **需重写** |
| book_edit.html | 旧 | 高 | 少 | 低 | 需重做 |
| user_edit.html | 旧 | 高 | 少 | 低 | 需重做 |
| config_db.html | 旧 | 高 | 少 | — | 需重做 |
| tasks.html（fork 内） | 旧 | 中 | 少 | — | 复核（自研 `/tasks` 已由 P10 处理） |
| grid.html | Bootstrap 字段视图 | 高 | 少 | — | 复核归属 |
| modal_dialogs.html | **旧 Bootstrap modal** | **高** | 少 | — | **需重构为 Alpine modal** |

审计输出工具：`grep -lE 'class="btn btn|form-control|col-sm-|col-md-|col-lg-|glyphicon|navbar-|panel panel|row-fluid|modal fade|modal-dialog' cps/templates/*.html`

---

## 三、统一 App Shell

最终结构（全站唯一）：

```
App
├── Sidebar     240px（lg 常驻；移动端 Drawer）
└── Main
    ├── Header  64px
    └── Content
         max-width: 1440px; margin: auto; padding: 24–32px
```

- Mobile：Sidebar → Drawer；Header compact；Content padding → 16px。
- **禁止任何页面自行定义另一套 container**（`container` / `container-fluid` / 自造 `max-w-*` 覆盖）。

## 四、统一页面比例（Design Token 落地）

在 `src/input.css` 建立并统一引用：

```
--sidebar-width:     240px
--header-height:     64px
--content-max-width: 1440px
--page-padding:      24px（md+）/ 16px（移动）
--section-gap
--card-gap
--radius-sm: 4px
--radius-md: 6px
```

禁止不同页面随意出现互不协调的 `max-w-*` / `px-*` / `gap-*` / `rounded-*` / `text-*`。

## 五、彻底检查首页

目标最终形态：

```
Search
↓
Continue Reading
↓
Recently Read / Recently Added
↓
Shelves / Collections
↓
Library（书库网格）
```

逐项检查（index.html）：
- Jinja 是否完整渲染？有无裸模板代码？
- 是否残留 Bootstrap HTML（排序条 `btn btn-primary` + `glyphicon`）→ 重建为 `cw-btn--*` + Lucide。
- 是否残留旧 modal（`data-toggle="modal" data-target="#bookDetailsModal"`）与 `#bookDetailsModal` 本体？
- 是否重复 navigation / search / upload？
- 有无异常 HTML 嵌套 / JS 错误？

后端数据不足时保持现有数据源，不修改数据库模型。

## 六、重新设计书库（信息密度优先）

书籍管理优先于视觉效果。桌面端 5–8 列自适应，不强制固定 5 列。

优先推荐：

```css
grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
/* 外层 max-width: 1440px */
```

封面 `aspect-ratio: 2 / 3; object-fit: cover`，禁止无限放大封面。
书卡含：Cover / Title / Author / Series / Reading Status。

## 七、Settings / Admin 完整重写（弃用旧 Bootstrap 形式）

不只要改 CSS——重写：`admin.html`、`config_edit.html`、`book_table.html`、`user_table.html`。

Settings 采用「左导航 + 右内容」：

```
设置
├── 常规   （网站名/语言/时区/首页设置）
├── 书库   （默认排序/每页数量/封面/显示方式）
├── 阅读   （阅读状态/默认阅读器/进度）
├── 上传与处理（上传/自动转换/tasks）
├── 元数据 （数据源/自动补全/封面）
├── 用户   （注册/权限/用户管理）
└── 系统   （日志/数据库/服务状态/关于）
```

每个设置项 = **Label + Description + Control**：

```
每页显示书籍数量
控制书库页面一次显示多少本书。数值越大页面加载越多。
                          [ 50 ]
```

## 八、Settings 交互（Alpine，不引新框架）

用 Alpine.js 实现：Settings 导航、Accordion、Toggle、Modal、Toast、Save state、Unsaved-changes indicator。

## 九、表格统一

Admin 表格：compact、可读、移动端横向滚动、可 sticky header、row hover、status badge、action buttons。禁用旧 Bootstrap table 样式。

## 十、所有表单统一

统一 Input / Select / Checkbox / Radio / Textarea / Toggle 的 height、border、radius、focus ring、label、description、error state。

## 十一、所有 Modal 统一（清除 Bootstrap modal）

彻底清除 Bootstrap modal。统一 Alpine modal：`x-data` / `x-show` / `x-transition`；支持 Escape、click outside、focus handling。
重点改造 `modal_dialogs.html`（现有 Bootstrap modal 均为其产出）。

## 十二、图标

禁用 glyphicon，统一 Lucide；语义正确、尺寸统一、stroke width 统一；icon-only 按钮必须有 `aria-label`。

## 十三、Dark Mode

所有页面须同时检查 Light / Dark——重点：Settings、Tables、Forms、Modal、Book Detail、Search、Empty State。
禁止白色 Bootstrap 卡片 / 黑字 / 白背景残留在 Dark Mode。

## 十四、操作流程优化

- 上传：Upload → accepted → 自动进入 Tasks → 查看处理 → 完成 → 回到 Library。
- 搜索：Ctrl+K → 输入 → 结果 → Book Detail。
- 书籍：Book → Read/Download → Edit → Metadata → More。
- 设置：Settings → 分类 → 修改 → Save → Toast → **保持当前页**（避免保存后被跳回首页）。

## 十五、兼容性（不改）

不修改：数据库模型、Calibre metadata schema、现有路由、现有权限模型。除非发现明确 bug。

## 十六、完成标准（逐页核对）

Home / Library / Book Detail / Search / Login / Register / Tasks / Upload / Settings / Admin / Users / Book Management

每页必须：无 Bootstrap UI / 无裸 Jinja / 无控制台错误 / 无水平溢出 / Desktop·Tablet·Mobile 正常 / Dark Mode 正常 / Sidebar·Header·Content width 一致。

## 十七、最终验收（Playwright）

- Desktop 1440×900
- Tablet 1024×768
- Mobile 390×844

逐页截图 + 检查：首页 / 书库 / 书籍详情 / 搜索 / 设置 / Admin / Tasks / Upload。

最终输出 **UI Consistency Report**：已修改文件、删除的 Bootstrap 依赖、保留的 legacy JS、新增组件、Settings 改造情况、首页异常修复情况、Desktop/Mobile 截图验证、Dark Mode 验证、Console errors、剩余问题。

---

## 十八、本轮施工顺序（建议）

1. **首页收口**：去掉 `index.html` 的 Bootstrap 排序条 + glyphicon + 旧 modal 引用（视觉比例 + 模板残留）。
2. **Modal 统一**：重构 `modal_dialogs.html` → Alpine（清掉 Bootstrap modal 体系）。
3. **Settings/Admin 重写**：`config_edit.html` + `admin.html`（左导航 + Label/Description/Control）。
4. **Admin 表格**：`book_table.html` / `user_table.html` 完整迁移 cw-table（去 DataTable 视觉依赖）。
5. **其余旧页收口**：`book_edit.html` / `user_edit.html` / `config_db.html` / `grid.html` 复核迁移。
6. **全站比例统一**：`src/input.css` token 落地 + 书库 auto-fill 自适应。
7. **最终逐页审计 + Playwright 验收报告**。

> 完成上述后，不要继续添加新功能，先做到视觉与交互一致。
