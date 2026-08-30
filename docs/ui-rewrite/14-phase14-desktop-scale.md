# P14 — Desktop Scale & Density Fix（桌面端比例/密度修正）

> 状态：**完成（2026-08-28）**
> 分支：`calibre-stack` `rewrite`
> 对象：`calibre-web/src/input.css` + `calibre-web/tailwind.config.js` + `cps/templates/layout.html`
> 范围：**只修 Desktop UI Scale / Layout density / Responsive sizing**。不加功能、不改 Design System、不重新设计。
> 约束：不用 `zoom` / `transform:scale()` / 全局 `font-size` 强制放大，全走真正 Token / Breakpoint。

---

## 〇、为什么需要这一轮（根因）

UI Rewrite（P0–P13）视觉已统一，但实际运行后暴露 **PC 端比例失衡**：

1. **Sidebar/Header/Button/Input/字体全面偏小**——沿用了偏"移动优先"的紧凑尺寸，放大到 1440/1920 后像"手机 UI 拉到 PC"。
2. **Content 限宽 1440px 太窄**，大屏中心缩成一团（"缩在中间"）。
3. **书库网格 `minmax(150px,1fr)`** 在大屏会无限加列 → 单本书封面过小。
4. 各页面 `max-width/padding` 各处自定，未统一 Layout token。
5. 移动端 Header 有原生 `<input type=file>` 未隐藏 → 390px 下横向溢出。

> 评价标准：**打开 Calibre-Web，是否感觉这是一个正常的桌面应用比例，而不是"移动端放大到 PC"。**

---

## 一、Desktop Density 分档（新 Breakpoint）

`tailwind.config.js` 屏幕档位重新对齐：

| 档位 | 阈值 | 密度 |
|------|------|------|
| `md` | 768px | Comfortable |
| `lg` | 1024px | Comfortable（Sidebar 240px 常驻） |
| `xl` | **1280px**（原 1200） | Desktop / Spacious |
| `2xl` | **1600px**（新增） | Wide Desktop |

原 `xl:1200px` 移为 `xl:1280px`，并新增 `2xl:1600px`。全站模板此前无任何 `xl:`/`2xl:` 用法，改档安全。

---

## 二、Layout Tokens（`src/input.css`）

| Token | Mobile | `md` | `lg` | `xl`(≥1280) | `2xl`(≥1600) |
|-------|--------|------|------|------|------|
| Sidebar width | drawer 15rem | drawer | 240px | **248px** | 248px |
| Header height | 56px | **64px** | 64px | 64px | 64px |
| Content max-width | auto | auto | 1440 | **1600px** | **1720px** |
| Content padding-x | 16px | 24px | 32px | 32px | **40px** |
| Content padding-y | 16px | 24px | **28px** | 28px | 28px |

实现方式：`.cw-main__inner` 用 `xl:max-w` / `2xl:max-w` + 外层 `@media(min-width:1280/1600){ max-width }` 兜底；padding 用响应式 `px/py` 类。

---

## 三、Typography（Desktop 上不再大范围 `text-xs/10/11/12`）

| Class | Mobile | Desktop(xl) | 说明 |
|-------|--------|-------------|------|
| `.cw-page-title` | 20px (`text-xl`) | **24px** (`md:text-2xl`) | 页面标题 |
| `.cw-title`（详情书名） | 24px | **28px** (`xl:text-[28px]`) | Book Detail |
| `.cw-section-title` | 18px | **20px** (`xl:text-xl`) | 统一为一处定义，去掉重复 override |
| `.cw-subtitle` | 16px | 18px | 区块标题 |
| `.cw-book-title` | 14px | 14px | 书名（达标） |
| `.cw-book-author` | 12px | **13px** (`md:text-[13px]`) | 作者 |
| `.cw-book-meta` | 12px | 13px | 元数据 |
| `.cw-status-badge` | 10px | 11px | 徽章（caption） |

`text-[10/11/12px]` 只保留在真正 metadata/caption/badge 场景。

---

## 四、Sidebar

- 宽度：`xl:w-[248px]`（桌面 ≥1280）。
- `.cw-sidebar__link`：`min-height:40px`、`gap-3`（12px）、`text-sm`（14px）、`px-3`（12px）。
- 移动端 drawer 仍 `width:15rem`，不受影响。

---

## 五、Header

- 高度：`md:h-16`（64px）。
- 图标钮 `.cw-btn--icon`：`md:w-10 md:h-10`（40×40）。
- 搜索 `.cw-search--flex`：`md:w-80 lg:w-[360px] xl:w-[400px]`（宽 360–480）；输入 `md:h-10`（40px）；搜索图标 18px。
- **修复移动端 Header 溢出**：`layout.html` 给 `#btn-upload` / `#btn-upload-m` 补 `class="hide"`（原生 file input 不再以 ~356px 可见块撑开 Header；上传流程不改）。

---

## 六、Library Grid（重点：单本不过小）

```css
.cw-book-grid {
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); /* 移动/平板：2 列起 */
}
@media (min-width: 1280px) {
  .cw-book-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 190px)); /* 桌面：160–190px */
  }
}
```

实测列数（Content 内）：
- 1280 → **4 列**（190px）
- 1440 → **5 列**（190px）
- 1920 → **7 列**（190px）
- 封面（2:3）宽约 174px，处于目标 150–180px。

> 注意：桌面若直接全用 `minmax(160px,190px)`，固定 max 会让 390px 移动端退化成 1 列（过大）——故移动/平板保留 `1fr`，仅在 ≥1280 启用固定 max。

---

## 七、Book Card

- 封面 `aspect-[2/3]` 不变。
- vertical gap `gap-2`（8px），`md:gap-1` 于 meta。
- 书名 14px / 作者 13px / 元数据 13px（桌面）。

---

## 八、Content Container 统一

- 全站页面（Home / Library / Search / Detail / Settings / Admin / Tasks）统一继承 `.cw-main__inner`（不再各自定义 max-width）。
- 例外且合规：Settings 本页 `max-w-4xl`（896px，落在 700–900 目标；不作左导航重构）；Admin 表格用满 Content 宽；async-upload 独立页 `.cw-wrap`（tasks 1100px / upload 620px）保持其自身语义宽。

---

## 九、Book Detail

- `.cw-detail__layout` 封面列宽：
  - `md:13rem`(208) / `lg:15rem`(240) / `2xl:17rem`(272)，落在目标 220–280px。
- 元数据区 `minmax(0,1fr)` 占剩余空间，不无限拉伸。

---

## 十、Responsive（全部保持）

| Viewport | Sidebar | Header | 书库列 | Cover | 横向溢出 |
|----------|---------|--------|--------|-------|----------|
| 390×844 | drawer | 56px | 2 (171px) | 155px | **无** |
| 768×1024 | drawer | 64px | 4 (168px) | 152px | 无 |
| 1024×768 | 240px | 64px | 4 (168px) | 152px | 无 |
| 1280×800 | 248px | 64px | 4 (190px) | 174px | 无 |
| 1440×900 | 248px | 64px | 5 (190px) | 174px | 无 |
| 1920×1080 | 248px | 64px | 7 (190px) | 174px | 无 |

> 已知残余（非本轮范围）：**Admin 用户表**（12 列数据表）在 <1024 需要横向滚动——桌面（≥1280）无溢出；这是宽数据表的正常特性，且属于表结构改造（超出"不重新设计"约束），留待后续。

---

## 十一、Dark Mode

本轮仅改 Layout/Typography/Spacing token，**颜色体系未动**（CSS 变量与 `html.dark` 不变），深浅模式同时成立。

---

## 十二、验证方法（本轮新增 Playwright 链）

真实模板 + 真实 `tailwind.css` 渲染到本地 HTML，用 Playwright Chromium 在 6 个 viewport 实测 computed layout：

- 渲染桩：复用 `/tmp/opencode/smoke_*.py` 的 stub 模式 → `render_pages.py`（产出 home/search/detail/settings/admin.html）。
- 测量：`measure.js`（读取 sidebar/header/content/grid/cover/title/search 实际渲染尺寸）。
- 关键坑：桩环境未加载 `bootstrap.min.css`，须以等价 `.hide{display:none}` 近似，否则 file input 撑宽 Header 造成假溢出。

---

## 十三、本轮修改文件

| 文件 | 改动 |
|------|------|
| `tailwind.config.js` | `xl:1200→1280px`，新增 `2xl:1600px` |
| `src/input.css` | buttons/inputs/search 尺寸、typography、sidebar/header/content、book grid（media 分档）、book card、detail cover、section-title 收敛 |
| `cps/templates/layout.html` | `#btn-upload` / `#btn-upload-m` 补 `class="hide"`（修移动端 Header 溢出） |
| `cps/static/css/tailwind.css` | 重新构建产物 |

---

## 十四、下一步（可选，非本轮强项）

1. Admin/User 宽表在 <1024 加 `overflow-x-auto` 容器（表结构微调，非重设计）。
2. 如需更接近"行数目标"（1440≈6 / 1600≈7 / 1920≈8），可把桌面 `minmax` 上限调到 165–170，但当前 174px 封面已足够、且更不牺牲面积。
3. 生产切产/打包缺陷按 `12-phase12.md` §2 执行。
