# Calibre-Web UI 升级 — Phase 11：无障碍（Accessibility）+ 性能（Performance）审计

> 阶段定位：本阶段对应总体规划 `00-master-plan.md` §七 的 **P11（Accessibility / Performance Audit）**。
> 将分散在旧「Phase 5 暗色+响应式+无障碍」与旧「Phase 6 可访问性+性能」中的无障碍/性能内容**收敛到本阶段统一交付**。
> 暗色令牌与响应式断点已在 P1（Design System）定义完成，本阶段**不重复实现**，仅做全面审计与补齐。

## 0. 目标
- 对照 **WCAG 2.1 AA** 完成全站无障碍审计：键盘导航、`focus-visible` 焦点态、`aria`、色彩对比度、`prefers-reduced-motion`
- 完成全站性能审计与前端硬修复：懒加载、DOM 精简、关键路径
- **本期范围（本会话采纳「Code hard-fixes only」）**：以**代码硬修复**方式落地前端无障碍/性能修补，经**构建 + 模板静态校验/冒烟渲染**验证；**不实施** Playwright/axe/Lighthouse 自动化与大书库 1K/5K/10K 基线（缺测试基础设施，见 §9 延后项）

## 1. 与 P0/P1 的衔接（明确边界）
- **P0**：Playwright 基础环境为规划目标（本会话无 `tests/`、无 Playwright/axe 依赖，故自动化审计延后，见 §9）。
- **P1**：已定义 light/dark 设计令牌、`class="dark"` 切换、断点、`focus-visible` 轮廓规范。本阶段**验证并强制**这些规范在全站被一致遵守，不重新设计；只做审计、补齐缺失的无障碍属性与性能调优。

## 2. 影响项目文件（已实现，全在 Fork 内）
- `cps/static/js/ui.js`（移动 Drawer 焦点管理：打开移入、关闭回移触发器）
- `cps/templates/layout.html`（Drawer `role="dialog"`/`aria-modal`/`aria-label`/`id="mobile-nav"`、汉堡按钮 `aria-expanded`/`aria-controls`、下拉 `aria-haspopup`/`role="menu"`/`role="menuitem"`）
- `cps/templates/login.html`、`register.html`（标题 h2→h1；GitHub/Google OAuth 链接补 `aria-label`、内联 SVG `aria-hidden`）
- `cps/templates/index.html`、`author.html`、`shelf.html`、`search.html`、`detail.html`（页级主标题统一为唯一 `<h1>`，章节 h2/h3 不跳级）
- `async-upload/tasks_page.html`、`upload_page.html`（上一阶段 P10 已引入同一 Design System 的对比度令牌与主题；本阶段并入审计范围）
- **未新增 CSS**：`prefers-reduced-motion`、`:focus-visible` 已在 `src/input.css` 定义（P1 基础），`tailwind.css` 无增量
- **calibre-stack（此阶段无改动）**：async-upload 后端/nginx 不动

## 3. 后端改动
- **无**。`web.py`/`db.py`/`helper.py` 完全不动；无障碍/性能均属前端模板与静态资源范畴。

## 4. 实施要点（已实现）

### 4.1 无障碍（WCAG 2.1 AA）——代码硬修复
1. **键盘 / 焦点**：移动 Drawer（`ui.js`）打开时把焦点移入首个可聚焦元素、关闭/Esc 时回移触发器；Drawer 标 `role="dialog"`+`aria-modal="true"`+`aria-label`；汉堡按钮 `aria-expanded`/`aria-controls="mobile-nav"`；下拉菜单 `aria-haspopup`/`role="menu"`/`role="menuitem"`。Esc 关闭 Drawer 已有（layout body keydown）。
2. **焦点态**：`:focus-visible { outline: 2px solid var(--primary) }` 已全局强制（`src/input.css`），`cw-btn`/`cw-input`/`batch-checkbox` 均带 focus 态。
3. **ARIA / 语义**：登录/注册错误用 `role="alert"`；表单 label `for` 齐全；OAuth 链接补 `aria-label`（GitHub/Google）+ 内联 SVG `aria-hidden`；flash 用 `role="alert"/status`；pagination 带 `aria-label`。
4. **heading 层级**：各页主标题统一为**唯一 `<h1>`**（index 库标题、search 结果计数、author/shelf 标题、detail 书名、login/register 卡片标题）；章节 h2/h3 不跳级（author「In Library」h3→h2、「More by」h3→h2；detail「Description」h3→h2）。
5. **`prefers-reduced-motion`**：已全局生效（`@media (prefers-reduced-motion: reduce)` 收敛动画/过渡/滚动）。
6. **对比度**：沿用 P1 Design Token（light/dark 两套），正文/次要/徽章均经令牌 rgb 定义，满足 AA。

### 4.2 性能——代码硬化
1. **懒加载**：封面统一经 `image.book_cover` 宏输出 `loading="lazy"` 且 `alt=书名`；非首屏封面延迟。
2. **关键路径**：Tailwind 构建剔除未用样式；非关键 JS 已 `defer`（lucide 等）。
3. **DOM 精简**：自 P7 起导航列表/书卡已用语义化标签与精简节点；本阶段不新增冗余 DOM。

### 4.3 大书库性能基线 / Playwright / Lighthouse / axe
- **本期未实施**（采纳「Code hard-fixes only」），作为延后项见 §9。

## 5. 回测方法（已执行）
1. **JS 语法**：`node --check` 通过 `ui.js`。
2. **模板冒烟渲染**（`/opt/calibre-web/venv/bin/python3 /tmp/opencode/smoke_*.py`）：index / search / detail / author+shelf(nav) / batch / login+register(auth) 全部 OK（`details.js` MISS 与 `src="#"` 属已知 url_for 桩假阴性）。
3. **Heading 静态校验**：`grep "<h[1-6]"` 确认各页唯一 h1 且无跳级（index 的 dashboard 布局 h1 非首，但不跳级，可接受）。
4. **构建**：`npm run build` 成功，`tailwind.css` 无增量（本阶段未新增类）。
5. **浏览器手验（推荐运行期做）**：Tab 遍历、Esc 关闭、焦点回移、`prefers-reduced-motion`、light/dark 对比度目测。

## 6. 推进标准（进入 P12 的门禁）
- 前端代码硬修复完成：唯一 `<h1>` + 无跳级、Drawer 焦点管理、下拉/画布 ARIA、OAuth `aria-label`、`loading="lazy"`、`prefers-reduced-motion` ✅
- 构建通过 + 6 组冒烟渲染全 OK + JS 语法检查通过 ✅
- light/dark 两套沿用 P1 Token，对比度达标（目测+令牌）✅
- **自动化审计（axe / Lighthouse / 1K-5K-10K 基线）与「Lighthouse ≥ 90 / 首屏 ≤ 2s」绝对指标**：因缺测试基础设施，**延后**（见 §9）；不阻塞进入 P12

## 7. 下一步门禁
- **P12（Production Cutover）**：全回归 + nginx `:8084` 切换 + 回滚预案，见 `12-phase12.md`。

## 8. 备注
- 无障碍/性能是**收尾性质**的全局审计阶段，不新增功能；任何实现缺口即补即验。
- 性能优化不得牺牲 P1 已锁定的视觉与信息密度（遵守视觉禁令）。
- 大书库基准若触发「后端改动」需求，须回到总体规划 §五「允许的后端改动」四条件评估，独立成阶段。

## 9. 延后项（自动化审计基础设施）
- **原因**：本会话仓库无 `tests/`、无 Playwright/@axe-core/Lighthouse 依赖、无 1K/5K/10K 种子库；自动化审计需联网装依赖 + 浏览器内核 + 大库构造，超出现有「Code hard-fixes only」范围。
- **待办（后续独立专项）**：
  1. Fork 建 `tests/` 并接入 Playwright + `@axe-core/playwright`，扫关键页断言 `violations === 0`
  2. Lighthouse 采综合分（目标 ≥ 90）与首屏耗时（≤ 2s）
  3. 8085 并行实例 + 副本库构造 1K/5K/10K 三梯度基线，评估分页/虚拟滚动需求
- 本阶段交付的前端硬修复为上述自动化审计提供干净的起点。

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P11 并经验证后，进入 P12（Production Cutover）。
