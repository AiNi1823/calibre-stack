# P15 — Final Design Spec 实施（极简个人电子书档案馆）

> 状态：**施工中**
> 基线：P14 完成（Sidebar 248 / Header 64 / 书库 160-190 / 字体已放大）
> 目标：按 **Final Design Specification** 统一收口，达到“现代个人电子书档案馆，极简、安静、清晰、高信息密度，桌面端舒适，长期使用不疲劳”

---

## 核心差异（P14 → P15 关键调整）

| 项目 | P14 (当前) | P15 (目标) | 备注 |
|------|------------|------------|------|
| Sidebar | 248px | **232px** | 更紧凑 |
| Header | 64px | **60px** | 更紧凑 |
| Content max | 1600 / 1720 | **1600** | 不再分两档 |
| Content padding | 32 / 40 | **32–40** | 兼容范围 |
| Page Title | 28px / 600 | **28px / 700** | 加粗 |
| Section Title | 18→20 / 600 | **20px / 600** | 统一 |
| Body | 14px | **15px** | +1px |
| Book Title | 14px / 500 | **16px / 600** | 更大更粗 |
| Author | 13px | **14px** | +1px |
| Metadata | 13px | **13px** | 同 |
| Book Grid | minmax(160,190) gap 16 | **minmax(160,180) gap 24** | 更大间距、上限更小 |
| Book Card | 卡片阴影/圆角 | **弱化卡片、强化封面** | 无阴影、无放大、封面 4px |
| Radius | 4/6 | **4/6/8** | 新增 8px (Modal) |
| Font | 默认 | **System UI 栈** | 显式声明 |
| Design Tokens | 部分 | **完整 --cw-* 变量** | §24 |

---

## 实施清单

### 1. CSS 变量设计令牌（§24）
在 `:root` / `html.dark` 下补充：
```css
--cw-sidebar-width: 232px;
--cw-header-height: 60px;
--cw-content-max: 1600px;
--cw-content-padding: 32px;
--cw-font-body: 15px;
--cw-font-book-title: 16px;
--cw-font-author: 14px;
--cw-font-meta: 13px;
--cw-page-title: 28px;
--cw-section-title: 20px;
--cw-control-height: 40px;
--cw-radius-sm: 4px;
--cw-radius-md: 6px;
--cw-radius-lg: 8px;
```
并在 `tailwind.config.js` `extend` 中映射为可用工具类。

### 2. Typography（§3）
| Class | 目标值 | 现有 → 变更 |
|-------|--------|-------------|
| `.cw-page-title` | 28px / 700 | `md:text-2xl font-semibold` → `text-[28px] font-bold` |
| `.cw-section-title` | 20px / 600 | `text-lg font-semibold xl:text-xl` → `text-[20px] font-semibold` (统一，移除响应式) |
| `.cw-title` (详情书名) | 28px / 700 | `xl:text-[28px] font-semibold` → `text-[28px] font-bold` |
| `.cw-body` | 15px / 400 | `text-sm` → `text-[15px]` |
| `.cw-book-title` | 16px / 600 | `text-sm font-medium` → `text-[16px] font-semibold` |
| `.cw-book-author` | 14px / 400 | `md:text-[13px]` → `text-[14px]` |
| `.cw-book-meta` | 13px / 400 | `md:text-[13px]` → `text-[13px]` (同) |
| `.cw-subtitle` | 16px? | 现有 `text-base md:text-lg` → `text-[16px] font-medium` |
| `.cw-status-badge` | 12px | `md:text-[11px]` → `text-[12px]` |
| Sidebar link | 14px / 500 | 已 14px，加 `font-medium` |
| Header / Button / Input | 14/15px | 调整到 spec |

### 3. Layout Scale（§2）
- `.cw-sidebar`：`xl:w-[248px]` → `xl:w-[232px]`
- `.cw-header`：`md:h-16` (64px) → `md:h-15` (60px) —— 或用任意值 `h-[60px]`
- `.cw-main__inner`：移除 `2xl:px-10` 与 `max-width:1720px`，统一 `max-width:1600px`，padding `xl:px-8` (32px) `2xl:px-10` (40px) 保留范围
- `@media (min-width:1600px) { max-width:1720px }` → 删除

### 4. Book Grid（§9）
```css
.cw-book-grid {
  display: grid;
  gap: 24px;  /* was 1rem */
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
}
@media (min-width: 1280px) {
  .cw-book-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 180px));
    justify-content: start;
  }
}
```

### 5. Book Card（§10）
- `.cw-book-card`：移除 `hover:shadow-md`、移除卡片 `bg-surface` `rounded-6` `p-2`，改为**极简**：仅封面 + meta，无可见卡片容器
- `.cw-book-cover`：保持 `rounded-4`，**移除** `hover img scale-105`，改为极微妙 `hover:opacity-90` 或极淡 border
- meta 间距调整

### 6. System Font Stack（§4）
```css
@layer base {
  html { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", "Noto Sans SC", sans-serif; }
}
```

### 7. Radius / Shadow（§19/20）
- Tailwind `extend.borderRadius` 新增 `'8': '8px'`
- `.cw-book-card`、`cw-card` 移除默认阴影，仅 Dropdown/Modal/Tooltip 用极淡 shadow
- Modal 使用 `rounded-8`

### 8. Settings（§14）—— 模板层面调整（不重构导航结构，仅 token 对齐）
- `config_edit.html` 现有 `max-w-4xl` (896px) 落在 760-900 范围，保留
- 标题/描述/控件字号对齐 spec

### 9. Admin Table（§15）
- `.cw-table thead th`：`text-xs` (12px) → `text-[13px] font-semibold`，去 uppercase
- `.cw-table tbody td`：`text-sm` (14px) 保持
- Row `py-3` (12px) → `py-4` (16px) 使行高 ≥ 48px

### 10. Sidebar 结构（§5）—— 仅类名/结构微调，不改业务
- Group labels: LIBRARY / BROWSE / SYSTEM（现有已近似，对齐命名）
- `.cw-sidebar__head` 字号 12px uppercase → 12px semibold
- `.cw-sidebar__link` icon 18px (现有可能 16px，调大)

### 11. Header 搜索（§6）
- `.cw-search--flex` 宽度范围 360-480px（现有 360-400，扩展到 480）
- Input height 40px，font 15px

---

## 验收标准（UI Final Review）

必须在真实浏览器验证：
- **1920 × 1080**
- **1440 × 900**  
- **390 × 844**

产出：
- 修改文件清单
- Typography Token 表
- Layout Token 表
- Book Grid / Book Card 实测尺寸
- Sidebar / Header 实测
- Settings / Admin 实测
- Desktop / Mobile / Dark Mode 截图
- Console errors
- Remaining issues

---

## 禁止事项
- 不引入新框架/库
- 不改 Database / API / Routes / Upload / Tasks / Metadata
- 不用 `zoom` / `transform: scale()` / 全局 `font-size` 放大
- 不做 Dashboard 化、不加统计卡片
- 不做大阴影/大圆角/Gradient/Glassmorphism/Hover 放大
- 不让内容区过窄