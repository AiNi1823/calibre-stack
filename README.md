# Calibre Stack

自托管电子书管理栈：Calibre-Web + 异步上传服务 + 元数据自动补全工具，针对低配 VPS（1.6GB 内存）与 Cloudflare Tunnel 环境优化。

## 背景

直接通过 Cloudflare Tunnel 上传大文件到 Calibre-Web 会触发 Cloudflare 边缘节点 100 秒硬超时（HTTP 层超时不可配置），导致上传"卡顿无反应 / a timeout occurred"。本项目的异步上传服务将「文件接收」与「入库处理」解耦，毫秒级响应彻底规避该限制。

## 组件

| 组件 | 说明 | 运行方式 |
|------|------|----------|
| [calibre-web](calibre-web/) | **Calibre-Web 0.6.27 源码树（vendored）**：可编辑、可版本控制的 UI「施工现场」。含 `cps/templates`、`cps/static`、Tailwind 构建链与设计令牌 | pip 从本目录安装；UI 在此直接改造 |
| [metadata-tool](metadata-tool/) | 从豆瓣 / Open Library 自动补全书籍元数据（ISBN、出版日期、简介、封面） | CLI 手动/cron |
| [async-upload](async-upload/) | HTTP 异步上传服务：立即返回 → 后台 `calibredb add` 入库；含任务看板 `/tasks` 与 `task_store.py` | systemd 常驻 |
| [deploy](deploy/) | nginx 配置、systemd 单元、部署脚本；旧 `.patch` 归档于 `patches-archive/*.legacy` | — |

## 架构

```
浏览器 ──Cloudflare Tunnel──> nginx:8084 ─┬─ /async-upload      静态上传页（隐藏后备入口）
                                          ├─ /tasks ───────────> async-upload:8086 任务看板
                                          ├─ /api/upload ──────> async-upload:8086
                                          │                        ├─ 立即返回 accepted
                                          │                        └─ 后台 calibredb add
                                          └─ 其余请求 ─────────> Calibre-Web(Tornado):8083
                                                                         │
                                                   共享 metadata.db <────┘
```

## 快速开始

### 异步上传

在 Calibre-Web 界面使用原生的 **Upload** 按钮即可（它 POST 到 `/api/upload`，由本栈异步服务接管）。上传后自动跳转到**「我的上传」**（任务看板 `/tasks`），可实时查看「接收 → 入库 → 转 EPUB → 完成」各阶段；书籍在后台处理完成后自动出现在书库中。

> 另提供 `https://<你的域名>/async-upload` 作为隐藏后备上传页（不在界面常驻导航）。上传上限 **200MB**。

### 元数据补全

```bash
cd metadata-tool
pip install -r requirements.txt
python3 main.py --check        # 检查缺失字段（干运行）
python3 main.py --report       # 全部书籍状态报表
python3 main.py                # 自动补全所有缺失字段
python3 main.py --book-id 12   # 处理指定书籍
python3 main.py --covers-only  # 仅补全缺失封面
```

代理、数据源、字段规则等在 `metadata-tool/config.yaml` 中配置。

## UI 开发（施工现场）

UI 升级在 **vendored `calibre-web/` 源码树**内直接施工（替代旧的 patch 模型），方案见 [docs/ui-rewrite/00-master-plan.md](docs/ui-rewrite/00-master-plan.md)。

```bash
cd calibre-web
npm install        # 一次性开发依赖
npm run build      # 生成 cps/static/css/tailwind.css（提交产物）
# 编辑 cps/templates/*.html、cps/static/、src/input.css、tailwind.config.js
# 部署：pip install --force-reinstall --no-deps ./calibre-web
```

- 阶段文档：`docs/ui-rewrite/0X-phaseX.md`（P0 基线 → P1 Design System → … → P12 上线）
- Tailwind / 令牌 / 断点 / 暗色：见 `calibre-web/tailwind.config.js` 与 `calibre-web/src/input.css`
- 旧 patch 机理的说明与归档：`calibre-web/README.calibre-stack.md`、`deploy/patches-archive/`

## 文档

- [项目结构（完整）](docs/project-structure.md)
- [需求说明](docs/requirements.md)
- [开发说明](docs/development.md)
- [部署指南](docs/deployment.md)

## 环境

- Linux (Debian/Ubuntu)，1.6GB 内存 VPS
- Python 3.12+
- Calibre 7.x（提供 `calibredb`）
- nginx + Cloudflare Tunnel（cloudflared）
