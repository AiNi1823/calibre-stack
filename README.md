# Calibre Stack

自托管电子书管理栈：Calibre-Web + 异步上传服务 + 元数据自动补全工具，针对低配 VPS（1.6GB 内存）与 Cloudflare Tunnel 环境优化。

## 背景

直接通过 Cloudflare Tunnel 上传大文件到 Calibre-Web 会触发 Cloudflare 边缘节点 100 秒硬超时（HTTP 层超时不可配置），导致上传"卡顿无反应 / a timeout occurred"。本项目的异步上传服务将「文件接收」与「入库处理」解耦，毫秒级响应彻底规避该限制。

## 组件

| 组件 | 说明 | 运行方式 |
|------|------|----------|
| [metadata-tool](metadata-tool/) | 从豆瓣 / Open Library 自动补全书籍元数据（ISBN、出版日期、简介、封面） | CLI 手动/cron |
| [async-upload](async-upload/) | HTTP 异步上传服务：立即返回 → 后台 `calibredb add` 入库 | systemd 常驻 |
| [deploy](deploy/) | nginx 配置、systemd 单元、部署脚本 | — |

## 架构

```
浏览器 ──Cloudflare Tunnel──> nginx:8084 ─┬─ /async-upload      静态上传页
                                          ├─ /api/upload ──────> async-upload:8086
                                          │                        ├─ 立即返回 accepted
                                          │                        └─ 后台 calibredb add
                                          └─ 其余请求 ─────────> Calibre-Web(Tornado):8083
                                                                        │
                                                  共享 metadata.db <────┘
```

## 快速开始

### 异步上传

访问 `https://<你的域名>/async-upload`，拖拽或选择文件后点击上传。文件传输完成后即显示成功，书籍在后台处理完成后自动出现在 Calibre-Web 书库中。

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

## 文档

- [需求说明](docs/requirements.md)
- [开发说明](docs/development.md)
- [部署指南](docs/deployment.md)

## 环境

- Linux (Debian/Ubuntu)，1.6GB 内存 VPS
- Python 3.12+
- Calibre 7.x（提供 `calibredb`）
- nginx + Cloudflare Tunnel（cloudflared）
