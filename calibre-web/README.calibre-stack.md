# Calibre-Web — vendored UI source tree (`calibre-web/`)

本目录是 Calibre-Web 在 `calibre-stack` 仓库内的**可编辑、可版本控制的源码树（施工现场）**。

## 来源与基线

- 上游：`github.com/janeczku/calibre-web`，`pip` 包名 `calibreweb`，**tag `0.6.27`**。
- 本目录即上游 0.6.27 的完整源码（`cps/` + 打包文件），并已并入本栈现有自定义（迁移自旧 `deploy/*.patch` 与运行中的 site-packages）：
  - `cps/templates/layout.html`（含上传表单 → `/api/upload`、「我的上传」→ `/tasks` 导航链）
  - `cps/static/js/uploadprogress.js`
  - `cps/web.py`
  - `cps/helper.py`（超时微调 `(10,200)`）
- 校验：`calibre-web/cps/` 与运行中 `site-packages/calibreweb/cps` 的源码**零差异**（排除第三方静态库/翻译）。

> 旧的 `deploy/*.patch`（patch 模型）已归档至 `deploy/patches-archive/*.legacy`，**不再作为主要维护机制**。

## 构建（Tailwind）

```bash
cd calibre-web
npm install            # 一次性；产物不入库
npm run build          # 生成 cps/static/css/tailwind.css（提交产物，VPS 运行期无需 Node）
npm run watch          # 开发期监听
```

配置文件：
- `package.json`（tailwindcss 3 + postcss + autoprefixer）
- `tailwind.config.js`（扫描 `cps/templates/**/*.html` 与 `async-upload/**/*.html`；`darkMode:'class'`；设计令牌见 `docs/ui-rewrite/P1`）
- `src/input.css`（`@tailwind` 指令 + light/dark 令牌 + focus-visible + prefers-reduced-motion）

## 安装 / 部署

从本目录安装（替代旧 pip/patch 流程）：

```bash
pip install --force-reinstall --no-deps ./calibre-web
```

这是因为本栈即该 UI 的源码所有者；`deploy/install.sh` 与 `docs/deployment.md` 已据此更新。

## 升级上游

```bash
git remote add upstream https://github.com/janeczku/calibre-web.git
git fetch upstream && git merge upstream/<tag>   # 在独立工作流中处理冲突
```

> 注意：子目录内的独立 `.git` 不含（本目录非嵌套仓库），合并在上层 `calibre-stack` 管理。
