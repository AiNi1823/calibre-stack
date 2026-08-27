# Calibre-Web UI 升级 — Phase 11：最终验收 + 上线

## 0. 目标
- 完成全回归测试，确认所有功能在新 UI 下正常运行
- 将新 UI 版本正式切换至生产环境（8084 端口）
- 编写文档与操作手册，供管理员与用户使用
- 制定回滚方案，确保出现问题时可一键恢复至旧版 UI

## 1. 影响项目文件
- **Fork 内**：
  - `docs/ui-rewrite/00-master-plan.md`（更新回归测试与切换章节）
  - `docs/ui-rewrite/phases.md`（更新阶段汇总与完成标记）
  - 可能涉及 `cps/templates/` 的微调（微调样式，确保在生产环险下正常）

- **calibre-stack（暂不涉及）**：
  - `async-upload/tasks_page.html`、`upload_page.html`

## 2. 后端改动
- 无。整个升级过程仅涉及前端模板与静态资源，后端 `web.py`/`db.py`/`helper.py` 完全不动。

## 1. 回归测试
1. **环境准备**：
   - 在 VPS 上另开端口 8085，安装 fork `ui-tailwind` 版本
   - 数据库使用生产库的只读快照（或复制一份 `metadata.db` 用于只读测试）
   - nginx 配置增加 `/beta` 路径 → 8085，保持 8084 为旧版 UI

2. **功能清单测试**：
   - **登录/权限**：普通用户/管理员登录，权限正常
   - **书库浏览**：网格/列表视图切换，正常
   - **搜索/筛选**：Ctrl+K 唤起、关键字匹配、筛选条件生效
   - **书籍详情**：封面/元数据/操作按钮全部正常
   - **在线阅读**：epub/pdf 打开无误
   - **收藏/标签/分类**：增删改查均正常
   - **批量操作**：全选/取消、操作按钮均正常
   - **上传/任务**：`/api/upload` 经 async-upload 服务正常、任务看板 `/tasks` 正常

3. **Lighthouse 评估**：
   - 打开 `http://VPS-IP:8085`（或 `/beta`），运行 Chrome DevTools · Lighthouse
   - 综合得分 ≥ 90
   - 首屏时间 ≤ 2 秒
   - 无控制台 JS 错误

4. **视觉检查**：
   - 全局一致的深色模式（`class="dark"`）
   - 统一的圆角（4–6px）
   - 统一的间距、字体、阴影
   - 移动端/桌面端/平板端三端布局均匀

## 2. 生产环境切换
1. **正式切换**：
   - `nginx :8084` 反代切至 `http://127.0.0.1:8085`（或 `http://IP:8085`）
   - `systemctl restart calibre-web`（加载新版本）
   - 保留 `/beta` 暴露旧版本，以便随时回滚

2. **回滚方案**：
   - 若在切换后发现严重问题，`nginx :8084` 立即改回指向 8083（旧版）
   - `git checkout` 恢复旧版 `cps/templates/`（或 `git checkout master` 在 fork 中）
   - `pip install --force-reinstall --no-deps git+https://github.com/janeczku/calibre-web.git`（恢复原 pip 包）

3. **文档与培训**：
   - `docs/ui-rewrite/00-master-plan.md` 更新「切换说明」与「回滚方案」
   - 对管理员进行「新版使用」简短培训（重点：主题切换、批量勾选、搜索快捷键）

## 2. 最终交付
- `docs/ui-rewrite/` 完整文档（P0–P13）
- `calibre-web` fork 仓库 `ui-tailwind` 分支（含全部前端改写）
- `calibre-stack` 主仓库更新记录（`docs/ui-rewrite/` 路径与变更摘要）
- 部署脚本/操作手册（`deploy/ui-upgrade.sh` 或类似）

## 3. 备注
- 全程「不破坏后端」，所有前端改写均通过 fork + 分支实现，升级时 `pip install` 即可切换，无需重构业务逻辑
- 若后续 Calibre-Web 官方更新，可 `git merge upstream master` 到 fork `master`，再 `rebase ui-tailwind`，或根据冲突情况人工冲突解决

## 3. 备注
- 此阶段标志着 UI 升级工作的**全部完成**，进入「运营」阶段。

---

> **施工文档**：影响文件/回测/推进标准如上。完成 P11 并经验证后，UI 升级工作全部完成。

---

## 七、文档索引
- `00-master-plan.md`（总体规划 / 决策 / 架构 / 后端改动政策 / 全局回归）
- `01-phase0.md`（P0 脚手架）
- `01-phase1.md`（P1 布局）
- `02-phase2.md`（P2 书库页）
- `03-phase3.md`（P3 详情页）
- `04-phase4.md`（P4 批量操作）
- `05-phase5.md`（P5 暗色+响应式+无障碍）
- `06-phase6.md`（P6 可访问性+性能）
- `07-phase7.md`（P7 首页）
- `08-phase8.md`（P8 搜索+筛选）
- `09-phase9.md`（P9 登录注册）
- `10-phase10.md`（P10 管理后台）

> **施工说明**：
> - 每个 `phase*.md` 文件均明确注明「影响项目文件 / 后端改动 / 回测方法 / 推进标准 / 下一步门禁」
> - 每个阶段通过 `8085` 并行实例 + Lighthouse / 手工清单 通过后，再执行 `nginx 8084 切换` 至新版
> - `git fork` + `ui-tainwind` 分支 彻底解决「升级覆盖改动」问题；`calibre-stack` 主仓库仅作记录，不再直接改动模板