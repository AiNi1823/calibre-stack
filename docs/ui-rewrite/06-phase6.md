# Calibre-Web UI 升级 — Phase 6：可访问性 + 性能

## 0. 目标
- 确保键盘导航流畅、无障碍符合 WCAG 2.1 AA 标准
- 优化页面加载性能：减少 DOM 节点、懒加载、延迟加载
- 图片和封面使用 `loading="lazy"` 与 `placeholder` 占位
- 关键路径加速，首屏加载时间控制在 2 秒以内

## 1. 影响项目文件
- **Fork 内**：
  - `cps/templates/base.html`（添加 `lazy-loading` 占位、焦点管理相关代码）
  - `cps/templates/layout.html`（加入 `loading` 属性及性能监控相关注释）
  - `cps/static/css/tailwind.css` / `input.css`（新增 `prefers-reduced-motion`、 `lazy-loading` 相关样式）
  - `cps/static/js/`（微调，主要是性能监控相关代码的精简）

- **calibre-stack（暂不涉及）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。前端性能优化不涉及后端业务逻辑。

## 2. 实施要点
1. **图片懒加载**：
   - 封面 `<img>` 标签添加 `loading="lazy"` 属性
   - 封面占位图使用 `placeholder-gray-200` / `placeholder-cyan-200` 等 Tailwind 占位类
   - 关键图片（首屏封面）保持 `loading="eager"`，其余图片使用 `loading="lazy"`

2. **关键路径优化**：
   - `base.html` 只加载必要的核心 CSS/JS（Tailwind 构建已剔除未使用的 CSS）
   - 非关键 JS（如批量操作、高级搜索）延迟加载，`defer` 属性
   - CSS 仅引入必要的组件样式（`@apply` 仅提取必须的样式类）

3. **性能监控**：
   - 在 `base.html` 中引入 `PerformanceObserver`（或简单的 `console.time`）记录首屏加载时间
   - 在 `console` 中输出 `DOMContentLoaded`、`load` 时间，便于回测对比

4. **减少无效 DOM**：
   - grid.html/list.html 中的书卡仅在可视区域内渲染（结合 `intersection observer` 思想，虽然不引入库，但可在模板层按需渲染关键数据）
   - 清理无用的 `div`、`span`，使用更语义化的 HTML 标签

## 1. 回测方法
1. **本地构建**：同上
2. **性能测试工具**：
   - **Lighthouse**（Chrome DevTools）——首屏时间、总时间、可访问性得分
   - **Chrome DevTools · Network面板**：查看关键路径资源加载时间
   - **手动记录**：打开 F12 控制台，记录 `DOMContentLoaded` 与 `load` 两个时间点
3. **验证清单**：
   - 页首加载时间 ≤ 2 秒（Lighthouse 得分 ≥ 90）
   - 封面懒加载：滚动至下方封面，图片平滑加载
   - 关键路径资源已按优先级加载
   - 没有控制台报错 `lazy-loading` 相关错误

## 3. 推进标准（进入 P7 的门禁）
- Lighthouse 综合得分 ≥ 90
- 首屏加载时间 ≤ 2 秒
- 封面懒加载平滑，无卡顿
- 没有明显的卡顿或 JS 报错

## 3. 下一步门禁
- P7（最终验收 + 上线）：全回归测试、Lighthouse 评分、部署上线

## 3. 备注
- 性能优化在不牺牲视觉质量和功能的前提下进行。若 Lighthouse 得分受限于第三方资源（如 Google 字体、谷歌字体加载慢），可考虑使用国内免费字体替代，或延迟加载字体。

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P6 并经验证后，可进入 P7.