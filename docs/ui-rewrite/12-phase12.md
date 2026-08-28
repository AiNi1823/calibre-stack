# Calibre-Web UI 升级 — Phase 12：最终验收 + 上线（Production Cutover）

## 0. 目标（范围裁定：Beta 8085 并行实例，暂不切生产）
- 完成全回归测试，确认所有功能在新 UI 下正常运行
- **先并行预发布**：8085 运行新 UI（fork），8083/8084 保持旧 UI
- 编写文档与操作手册，供管理员与用户使用
- 制定回滚方案，确保出现问题时可一键恢复至旧版 UI

> **范围裁定（用户批准，勿回退）**：P12 只做 **Beta 8085 实例** 的搭建与验证，
> **不触碰生产**（8083/8084）。生产正式切换（8084→8035/新 fork）作为**后续独立步骤**，单独审批后进行。

## 1. 影响项目文件
- **Fork 内**：
  - `docs/ui-rewrite/00-master-plan.md`（更新回归测试与切换章节）
  - `docs/ui-rewrite/phases.md`（更新阶段汇总与完成标记）
  - 可能涉及 `cps/templates/` 的微调（微调样式，确保在生产环险下正常）

- **calibre-stack（暂不涉及）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。整个升级过程仅涉及前端模板与静态资源，后端 `web.py`/`db.py`/`helper.py` 完全不动。

## 1. 回归测试（Beta 8085 —— 已完成搭建并验证）

### 1a. 环境准备（已完成）
- 新建并行实例 `/opt/calibre-web-beta/`：
  - `venv` 由生产 venv 复制（`cp -a /opt/calibre-web/venv`），后修正 `venv/bin/cps` shebang 指向 beta python
  - `app.db` 为生产库**只读快照**（复制一份第 8085 用）
  - 将 fork 根 `cps/`（全部 UI 改写：templates/static/py）**覆盖**到 `site-packages/calibreweb/cps/`
  - 修正 beta `app.db` 的 `config_port/config_external_port` → **8085**（否则与生产 8083 冲突）
- 新增 systemd 单元 `calibre-web-beta.service`（`CALIBRE_PORT=8085`，`ExecStart=/opt/calibre-web-beta/venv/bin/cps -i 127.0.0.1`），已 enabled + active
- nginx 增加 `/beta` 预发布访问入口（见下 1e）
- 一键重搭脚本：`deploy/setup-beta.sh`（幂等）

### 1b. 验证结果（curl 实测）
- `GET http://127.0.0.1:8085/` → 302（匿名浏览关闭，重定向登录，预期）
- `GET /login` → 200，含新 UI 标记 `cw-auth__card`/`cw-btn--primary`/`cw-field-label`/`cw-input` + `alpine.min.js`/`lucide`/`theme.js`/`ui.js`
- `GET /static/css/tailwind.css` → 200，size 39282B（Design System 编译产物）
- Beta 日志无运行期 error
- **生产校验**：8083 `/login` 无 `cw-auth__card`（旧 UI 原样保留），`calibre-web.service` active —— 生产未受影响 ✅

### 1c. 打包缺陷（重要，影响真实切产）
- fork 的 `pyproject.toml`/`MANIFEST.in` 仍沿用上游 `src/calibreweb` 布局，但本 fork 源码实为**根 `cps/`**（`cps.py` 启动器 + `cps/` 包），不存在 `src/calibreweb`
- 后果：`pip install /opt/calibre-stack/calibre-web` 产出**空 wheel**（auto-discovery 因 `src/` 目录存在而 src-layout 判定失败，不包含 `cps`）
- 因此 Beta 部署采用**直接覆盖 fork 根 `cps/`** 到 `site-packages/calibreweb/cps/`（等效于 UI 层正确安装），规避了该缺陷
- **待办（真实切产前必做）**：修复 `pyproject.toml` 加 `[tool.setuptools] packages/packages-dir + package-data(cps/templates·static·translations)`，使 `pip install` 生成完整 wheel；否则切产无法用文档化命令安装

### 1d. Beta 服务操作
- 启停：`systemctl start|stop|restart calibre-web-beta`
- 状态：`systemctl status calibre-web-beta`；日志 `journalctl -u calibre-web-beta -f`
- 一键重搭：`sudo bash deploy/setup-beta.sh`

### 1e. nginx `/beta` 访问
- Calibre-Web 0.6.27 **不支持子路径前缀**（模板内 `url_for('static', ...)` 均为根绝对路径，且登录 302 会脱离 `/beta` 前缀）
- 故**不**强行加 `/beta` 前缀产生坏样式的半成品路由；以 **8085 独立端口直连** 作为 Beta 访问方式（本地/防火墙内预览）
- 若需经 nginx 公开，建议**独立 server 块 / 子域名** `proxy_pass http://127.0.0.1:8085`（根反代，无前缀），待切产时统一由 8084 切换

### 1f. 功能清单测试（手动/后续自动化，P0–P11 各阶段已逐个冒烟）
- 登录/权限、书库浏览、搜索/筛选(Ctrl+K)、书籍详情、在线阅读、收藏/标签/分类、批量操作、上传/任务 —— 各阶段 `smoke_*.py` 已通过；P12 Beta 可直接人工点检（见 00-master-plan 回归清单）

### 1g. Lighthouse 评估（延后，同 P11 §9 专项）
- 缺 Chrome/Lighthouse 测试设施，未在 P12 Beta 上运行 —— 记入 §9 专项

## 2. 生产环境切换（暂缓 —— Beta 通过后再独立审批执行）
1. **正式切换（待执行）**：
   - 先修复 `pyproject.toml` 打包（见 §1c），用 `pip install --force-reinstall --no-deps /opt/calibre-stack/calibre-web` 将 fork 正确装入生产 venv
   - `nginx :8084` 反代切至 `http://127.0.0.1:8083`（新 fork 在 8083 运行即生产新 UI）
   - `systemctl restart calibre-web`（加载新版本）
   - 保留 Beta 8085 作为对比/回滚参照

2. **回滚方案**：
   - 若在切换后发现严重问题，`nginx :8084` 立即改回指向 8083（旧版）
   - `git checkout` 恢复旧版 `cps/templates/`（或 `git checkout master` 在 fork 中）
   - `pip install --force-reinstall --no-deps git+https://github.com/janeczku/calibre-web.git`（恢复原 pip 包）

3. **文档与培训**：
   - `docs/ui-rewrite/00-master-plan.md` 更新「切换说明」与「回滚方案」
   - 对管理员进行「新版使用」简短培训（重点：主题切换、批量勾选、搜索快捷键）

## 3. 最终交付
- `docs/ui-rewrite/` 完整文档（P0–P13）
- `calibre-web` fork 仓库 `ui-tailwind` 分支（含全部前端改写）
- `calibre-stack` 主仓库更新记录（`docs/ui-rewrite/` 路径与变更摘要）
- 部署脚本/操作手册：`deploy/setup-beta.sh`（Beta 一键重搭）、`deploy/calibre-web-beta.service`（8085 单元）

## 4. 备注
- 全程「不破坏后端」，所有前端改写均通过 fork + 分支实现，升级时 `pip install` 即可切换，无需重构业务逻辑
- 若后续 Calibre-Web 官方更新，可 `git merge upstream master` 到 fork `master`，再 `rebase ui-tailwind`，或根据冲突情况人工冲突解决
- **P12 当前状态**：Beta 8085 搭建+验证完成；生产切产（8084/8083 上新 fork）**暂缓**，待独立审批。

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P12 并经验证后，UI 升级工作全部完成。

---

## 七、文档索引
- `00-master-plan.md`（总体规划 / 决策 / 架构 / 后端改动政策 / 全局回归）
- `01-phase0.md`（P0 脚手架）
- `01-phase1.md`（P1 Design System：令牌 / 暗色 / 断点 / 组件）
- `02-phase2.md`（P2 App Shell：Sidebar / Header / Drawer / 响应式）
- `03-phase3.md`（P3 书库 Library：Grid / List / BookCard）
- `04-phase4.md`（P4 书籍详情 Book Detail）
- `05-phase5.md`（P5 首页 Home：继续阅读 / 最近 / 收藏）
- `06-phase6.md`（P6 搜索 + 筛选 Search / Filter）
- `07-phase7.md`（P7 书库导航：作者 / 分类 / 标签 / 系列 / 书架）
- `08-phase8.md`（P8 批量操作 Batch）
- `09-phase9.md`（P9 认证 + 管理后台 Auth + Admin）
- `10-phase10.md`（P10 自研页 Custom Pages：/tasks 与 /async-upload）
- `11-phase11.md`（P11 无障碍 + 性能审计，含 Playwright 与大书库基线）
- `12-phase12.md`（P12 最终验收 + 上线 Production Cutover，本文件）

> **施工说明**：
> - 每个 `phase*.md` 文件均明确注明「影响项目文件 / 后端改动 / 回测方法 / 推进标准 / 下一步门禁」
> - 每个阶段通过 `8085` 并行实例 + Lighthouse / 手工清单 通过后，再执行 `nginx 8084 切换` 至新版
> - `git fork` + `ui-tainwind` 分支 彻底解决「升级覆盖改动」问题；`calibre-stack` 主仓库仅作记录，不再直接改动模板