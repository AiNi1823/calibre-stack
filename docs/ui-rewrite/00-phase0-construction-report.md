# Phase 0 施工报告 — UI Rewrite 基础设施

> 仓库：`calibre-stack`（`rewrite` 分支）· 施工对象：`calibre-web/`（vendored 源码树）
> 基线：Calibre-Web **0.6.27**（janeczku/calibre-web tag）· 构建机：本 VPS（node 18 / npm 9）

## 1. 结论速览

| 检查项 | 结果 |
|--------|------|
| Tailwind 正常生成 | ✅ `cps/static/css/tailwind.css`（13295 B，minify） |
| 设计令牌 | ✅ light/dark CSS 变量 + `darkMode:class` |
| Alpine | ✅ `js/libs/alpine.min.js`（54K，vendored 本地，无 CDN 依赖） |
| Lucide | ✅ `js/libs/lucide.min.js`（419K，vendored 本地） |
| Dark Mode | ✅ `calibre-theme` 持久化 + `<head>` FOUC 保护 + 切换器全局函数 |
| 基础组件 | ✅ `cw-*` 组件类（btn/input/select/search/checkbox/badge/card/state…） |
| Bootstrap | ⚠️ 仍加载（渐进迁移保留，见 §5） |
| jQuery | ⚠️ 仍加载（仅未迁移旧业务），禁止新增 jQuery 代码 |
| 生产构建方式 | `cd calibre-web && npm run build`（构建产物提交，VPS 运行期无需 Node） |

## 2. 修改 / 新增 / 删除文件

### 修改
- `calibre-web/cps/templates/layout.html`
  - `<head>`：追加 `css/tailwind.css`（主样式）、`js/libs/lucide.min.js`、FOUC 保护内联脚本（`calibre-theme`）
  - `<body>`：加 `x-data` + `x-on:keydown.escape.window="$store.ui.closeSidebar()"`
  - 尾部：追加 `js/theme.js`、`js/ui.js`、`js/libs/alpine.min.js`
- `calibre-web/src/input.css`
  - 补全 light/dark 设计令牌；新增 `@layer` 顶层 cw- 基础组件类
  - **修复**：本 Tailwind 3.4 下 `@layer components` 包裹的 `@apply` 会整体被丢弃，改为顶层声明（hong验证）
- `calibre-stack/README.md`、`docs/ui-rewrite/00-master-plan.md`（§四）、`docs/ui-rewrite/01-phase0.md`
  - 已改写为 vendored 源码树施工模型（非 fork 模型）

### 新增
- `calibre-web/package.json`、`tailwind.config.js`、`postcss.config.js`、`src/input.css`（Tailwind 构建链）
- `calibre-web/cps/static/js/libs/alpine.min.js`、`js/libs/lucide.min.js`（vendored，本地无 CDN）
- `calibre-web/cps/static/js/theme.js`（暗色模式 + 持久化 + Lucide 初始化）
- `calibre-web/cps/static/js/ui.js`（Alpine `$store.ui`：dark / sidebar 状态 + 切换器）
- `calibre-web/cps/static/css/tailwind.css`（构建产物，提交）
- `calibre-web/README.calibre-stack.md`（vendored 树说明/构建/安装）
- `docs/ui-rewrite/00-phase0-construction-report.md`（本报告）
- `deploy/patches-archive/*.legacy`（旧 patch 归档，普通模型退役）

### 删除
- `deploy/{layout.html,uploadprogress.js,web.py}.patch` → 归档为 `patches-archive/*.legacy`
- 旧 `docs/ui-rewrite/05-phase5.md`（P5 已折叠）等（上轮已完成，非本阶段新增）

## 3. 构建命令 / 开发启动

```bash
# 生产构建（产物 cps/static/css/tailwind.css，提交仓库）
cd /opt/calibre-stack/calibre-web
npm install          # 一次性（dev 依赖，node_modules 不入库）
npm run build        # tailwindcss -i src/input.css -o cps/static/css/tailwind.css --minify

# 开发监听
npm run watch
```

**运行期无需 Node/npm**：Tailwind 产物已提交；Alpine/Lucide 已 vendored 到 `cps/static/js/libs/`。

## 4. Tailwind / Alpine / Lucide / Dark Mode 验证

- Tailwind：`npm run build` 成功，`.cw-btn`、`.cw-btn--primary`、`.cw-input`、`.cw-card`、`.cw-badge`、`.cw-page-title`、`.cw-state` 均生成；令牌编译为 `rgb(var(--primary)/<alpha>)`，暗色经 `<html class="dark">` 切换。
- Alpine/Lucide/theme/ui：`node --check` 全部通过（语法合法）。
- **渲染冒烟测试**：`layout.html` 用 Jinja 完整 render 无报错（len=4137），确认以下标签均输出：
  - `css/tailwind.css`、`js/libs/alpine.min.js`、`js/libs/lucide.min.js`、`js/theme.js`、`js/ui.js`
  - `calibre-theme` 暗色初始化、`x-data`、抽屉 Esc 关闭
- 说明：真实浏览器级验证（Playwright、图标渲染、暗色视觉）放 P0 验收/CI 或开发环境执行；本阶段完成静态 + 模板层验证。

## 5. Bootstrap / jQuery 当前剩余依赖

- **Bootstrap CSS/JS：仍加载**（`bootstrap.min.css` + `bootstrap.min.js`）。按「渐进迁移、不一次性删除」规则保留，保证未迁移页面可用；P1 起逐页面以 Tailwind+Alpine 替代。
- **jQuery：仍加载**（`jquery.min.js`）；仅用于尚未迁移到 Alpine 的旧业务（main.js/table.js/uploadprogress.js/filter_*）。**禁止新增 jQuery 代码。**
- 下一步（P1）将建立 Design System 全量组件并开始逐页面剥离 Bootstrap。

## 6. 下一阶段建议

1. **P1（Design System）**：在 `src/input.css` / `tailwind.config.js` 之上补全 BookCover、Modal、Drawer、Dropdown、Toast、Tabs、Pagination 等组件；统一 light/dark 视觉。
2. **P2（App Shell）**：用 Alpine `$store.ui` 搭 Sidebar/Header/Mobile Drawer/Search 入口/主题切换器，替换 Bootstrap navbar。
3. **P0 验收**（进入 P1 门禁）：建议在开发环境跑 Playwright 打开首页，检查 Console 无红字、Tailwind 生效、图标渲染、暗色切换、无回归。

## 7. 备注：Tailwind `@layer` 坑（已解决）

本机 Tailwind 3.4.17 + `@tailwind base/components/utilities` 三指令齐备时，`@layer components { .x { @apply … } }` 内的规则**整体丢失**（无报错但不出产物）；移除 `@layer` 包裹、顶层声明即正常。施工注意勿再套用 `@layer components` 包裹自定义组件类。
