# Calibre-Web UI 升级 — Phase 11：无障碍（Accessibility）+ 性能（Performance）审计

> 阶段定位：本阶段对应总体规划 `00-master-plan.md` §七 的 **P11（Accessibility / Performance Audit）**。
> 将分散在旧「Phase 5 暗色+响应式+无障碍」与旧「Phase 6 可访问性+性能」中的无障碍/性能内容**收敛到本阶段统一交付**。
> 暗色令牌与响应式断点已在 P1（Design System）定义完成，本阶段**不重复实现**，仅做全面审计与补齐。

## 0. 目标
- 对照 **WCAG 2.1 AA** 完成全站无障碍审计：键盘导航、`focus-visible` 焦点态、`aria`、色彩对比度、`prefers-reduced-motion`
- 完成全站性能审计：首屏加载 ≤ 2s、Lighthouse 综合得分 ≥ 90、关键路径/懒加载/DOM 精简
- 引入 **Playwright** 自动化回归（自 P0 建立的基础环境深化），覆盖无障碍断言与加载耗时
- 建立 **大书库性能基线**（1 000 / 5 000 / 10 000 本），量化 DOM 规模对首屏/交互的耗时，为后续分页/虚拟滚动评估提供依据（不在本期强制落地）

## 1. 与 P0/P1 的衔接（明确边界）
- **P0**：已建立 Playwright 基础环境与现有功能基线（见 `01-phase0.md`）。本阶段在其上补齐 `@axe-core/playwright` 无障碍断言与性能计时。
- **P1**：已定义 light/dark 设计令牌、`class="dark"` 切换、断点（sm 640 / md 768 / lg 1024 / xl 1200）、`focus-visible` 轮廓规范（见 `01-phase1.md`）。本阶段**验证并强制**这些规范在全站被一致遵守，不重新设计。
- 本阶段**不得**修改已交付的组件视觉定义；只做审计、补齐缺失的无障碍属性与性能调优。

## 2. 影响项目文件
- **Fork 内**：
  - `cps/static/css/tailwind.css` / `input.css`（若需补充 `prefers-reduced-motion`、`focus-visible` 兜底样式）
  - `cps/templates/*.html`（补齐缺失的 `aria-label`、`role`、`alt`、语义化标签、`loading="lazy"`、清醒的 heading 层级）
  - `cps/static/js/*`（键盘事件、焦点管理、滚动性能无关的微调）
  - `tests/`（新增 Playwright a11y/perf 断言，若 fork 已有测试目录）
- **calibre-stack（若涉及）**：
  - `async-upload/tasks_page.html`、`upload_page.html`（同一 Design System 下的无障碍与性能审计，见 `docs/design/02-task-store-api.md` §2.4）

## 3. 后端改动
- **无**。无障碍与性能均属前端模板/静态资源范畴；`web.py`/`db.py`/`helper.py` 完全不动。
- 若大书库性能基线暴露出「模板传 ORM 全量关联对象」导致 DOM 过大，可作为后续阶段评估分页/虚拟滚动 API 的依据，**本期不落地后端改动**（遵守「后端默认禁止」政策）。

## 4. 实施要点

### 4.1 无障碍审计（WCAG 2.1 AA）
1. **键盘导航**：Tab 顺序自然（符合视觉顺序）；所有可交互元素可键盘触达；`Esc` 关闭 Drawer/Dialog/Dropdown；触发元素焦点正确回移。
2. **焦点态**：所有可交互元素有清晰 `focus-visible` 轮廓（主色 `#2563EB`、2px、无 outline 影响布局），对照 P1 规范逐项检查。
3. **ARIA / 语义**：图标按钮须有 `aria-label`；`aria-expanded`/`aria-controls` 与展开控件联动；dialog 用 `role="dialog"` + `aria-modal`；表单控件有可关联的 `label`；封面 `<img>` 有合适的 `alt`。
4. **色彩对比度**：正文/次要文字、按钮、徽章、链接对比度满足 WCAG 2.1 AA（正文 ≥ 4.5:1，大号文本/UI 组件 ≥ 3:1），light/dark 两套均验证。
5. **`prefers-reduced-motion`**：尊重用户动画偏好，关闭或缩短非必要动画（封面 hover 缩放、Drawer 过渡）。
6. **heading 层级**：`<h1>` 唯一且语义正确，后续按 `h2→h3` 递减，无跳级。

### 4.2 性能优化
1. **懒加载**：非首屏封面 `loading="lazy"` + 占位背景；首屏关键封面 `loading="eager"`。
2. **关键路径**：`base.html` 只加载必要 CSS/JS；非关键 JS `defer`；Tailwind 构建已剔除未用样式。
3. **DOM 精简**：网格/列表页清除多余 `div/span`，使用语义化标签；封面卡片 DOM 尽量只含必要节点。
4. **字体**：若第三方字体（如 Google Fonts）影响首屏，改用国内可直连字体源或延迟加载（见旧备注）。

### 4.3 大书库性能基线（Playwright）
在 8085 并行实例上，以副本库构造 **1 000 / 5 000 / 10 000 本** 三个梯度，记录：

| 指标 | 采集方式 |
|------|----------|
| 首页首屏 DOM 节点数 | Playwright 计数 `document.querySelectorAll('*').length` |
| 首页首屏渲染耗时 | `page.goto` + `performance.timing` / `LargestContentfulPaint` |
| 搜索/筛选交互耗时 | 从输入到结果渲染的 TTI 计时 |
| Grid/List 切换耗时 | 交互动作计时 |
| Lighthouse 得分 | 三个梯度下首屏 PWA/Performance 简易采样 |

**基线目标（相对值，非绝对）**：
- 1 000 本：首屏 ≤ 2s，DOM 节点在有界范围内
- 5 000 / 10 000 本：记录并归档耗时曲线，识别是否线性劣化；不强制单页承载
- 若大书库明显劣化，输出「分页 / 虚拟滚动」需求单，作为后续独立评估项（本期不落地）

## 5. 回测方法
1. **本地/8085**：`systemctl restart calibre-web`（8085 并行实例）后走全站清单。
2. **Playwright 无障碍**：`@axe-core/playwright` 扫关键页（首页/网格/详情/搜索/批量/上传/tasks），`violations.length === 0` 为通过项之一。
3. **手动键盘验证**：Tab 遍历、Esc 关闭、焦点回移、`prefers-reduced-motion` 模拟。
4. **色彩对比度**：light/dark 两套，关键元素用对比度工具人工复核 + axe 断言。
5. **Lighthouse**：综合得分 ≥ 90，首屏 ≤ 2s。
6. **大书库基线**：按 §4.3 三梯度跑 Playwright 计时并归档结果。

## 6. 推进标准（进入 P12 的门禁）
- axe 扫描关键页 `violations = 0`，键盘/Esc/焦点回移/`prefers-reduced-motion` 均通过
- light/dark 两套对比度满足 WCAG 2.1 AA
- Lighthouse 综合 ≥ 90，首屏 ≤ 2s，无控制台 JS 报错
- 大书库基线（1K/5K/10K）已采集并归档；若线性劣化已输出后续需求单

## 7. 下一步门禁
- **P12（Production Cutover）**：全回归 + nginx `:8084` 切换 + 回滚预案，见 `12-phase12.md`。

## 8. 备注
- 无障碍/性能是**收尾性质**的全局审计阶段，不新增功能；任何实现缺口即补即验。
- 性能优化不得牺牲 P1 已锁定的视觉与信息密度（遵守视觉禁令）。
- 大书库基准若触发「后端改动」需求，须回到总体规划 §五「允许的后端改动」四条件评估，独立成阶段。

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P11 并经验证后，进入 P12（Production Cutover）。
