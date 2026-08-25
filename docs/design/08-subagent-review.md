# Design Doc 8: Subagent 审阅与可行性测试设计

> 目标：每个开发设计文档（Doc 1-7）产出后，由独立 subagent 审阅并实测可行性；
> 不可行则迭代修正文档，直至满足 plan.md 目标。

---

## 8.1 审阅 Agent 职责

对每个 Doc 执行：
1. **静态检查**：代码片段引用的路径/模块/命令是否存在
2. **依赖检查**：`pip` 包、`calibredb`/`ebook-convert` 命令、外部 API 可达性
3. **语法检查**：`python3 -m py_compile` 验证模块可编译
4. **干跑测试**：在 `/tmp` 用最小样本验证核心函数（不改生产数据）
5. **集成检查**：与现有 server.py / nginx 配置是否冲突
6. **输出报告**：PASS / FAIL + 具体问题 + 建议修正

## 8.2 验收标准（映射 plan.md）

| 模块 | 验收标准 |
|------|----------|
| Doc1 安全 | secrets.env 600；git 无敏感文件；cloudflared ps 无明文；Redis 需密码 |
| Doc2 任务 | tasks.db 建表；/api/tasks 返回 JSON；/tasks 页面可加载 |
| Doc3 转换 | ebook-convert 成功；DRM 文件正确识别；add_format 生效 |
| Doc4 源 | Gutendex/IA 返回候选；zlib 配额逻辑正确；下载落地 |
| Doc5 元数据 | Douban/OL 补全字段；去重保留 EPUB |
| Doc6 流水线 | 上传 TXT → 自动搜 EPUB → 入库 → 阶段可见 |
| Doc7 扫描 | /api/scan 创建 82 任务并逐步完成 |

## 8.3 迭代流程

```
写 Doc N → 派 subagent 审阅 →
  ├─ PASS → 标记完成，进入 N+1
  └─ FAIL → 根据报告修正 Doc N → 重审（最多 3 轮）
```

## 8.4 审阅 Prompt 模板

```
你是 Calibre 栈的审阅 agent。请审查以下设计文档的可行性：
<Doc N 内容>

执行：
1. 静态检查所有路径/命令是否存在（用 bash ls/which 验证）
2. 对 Python 代码片段执行 py_compile
3. 用最小样本干跑核心函数（仅 /tmp，不碰 /opt/calibre-library）
4. 验证外部 API（Gutendex/IA/Douban）当前可达性
5. 检查与现有 server.py / nginx 的兼容性

输出 JSON：
{
  "doc": "N",
  "verdict": "PASS|FAIL",
  "checks": [{"name":"...","status":"ok|fail","detail":"..."}],
  "issues": ["..."],
  "fixes": ["..."]
}
```

## 8.5 并发策略

可并行派多个 subagent 分别审 Doc 2-7（互不依赖），汇总后统一修正。
Doc 1 安全项需先单独过（影响后续凭据读取）。

## 8.6 终止条件

所有 Doc 验收标准全部 PASS，且 subagent 报告无阻断性问题 → 进入实施阶段。
