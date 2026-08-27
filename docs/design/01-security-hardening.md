# Design Doc 1: Security Hardening (Phase 0)

> 前置条件：无
> 产出物：secrets.env, .gitignore 更新, cloudflared cred-file, Redis 强密码
> 预计耗时：30 分钟

---

## 1.1 创建 secrets.env

### 目标
统一管理所有凭据，代码零明文，chmod 600 保护。

### 实现步骤

**步骤 1：创建 secrets.env**
```bash
cat > /opt/calibre-stack/secrets.env << EOF
# Calibre Stack Secrets — chmod 600, never commit
# Created: $(date -Iseconds)

# z-library (fill when credentials available)
ZLIB_EMAIL=
ZLIB_PASSWORD=
EOF

chmod 600 /opt/calibre-stack/secrets.env
chown calibreweb:calibreweb /opt/calibre-stack/secrets.env
```

> 本栈任务队列用 SQLite（`tasks.db`），**不引入 Redis/MQ**（见 project-plan.md「队列 | SQLite 表」）。故 secrets.env 不含 Redis 密码；§1.4 仅作本机其他应用若用 Redis 的参考。

**步骤 2：验证文件权限**
```bash
ls -la /opt/calibre-stack/secrets.env
# Expected: -rw------- 1 calibreweb calibreweb
stat -c "%a" /opt/calibre-stack/secrets.env
# Expected: 600
```

---

## 1.2 更新 .gitignore

### 目标
防止敏感文件和生成文件进入 Git。

### 实现步骤

**步骤 1：追加规则到 .gitignore**
```bash
cat >> /opt/calibre-stack/.gitignore << 'EOF'

# Security
secrets.env
.env*
*.db

# Generated
reports/
tasks.db
EOF
```

**步骤 2：验证当前 Git 状态无敏感文件**
```bash
cd /opt/calibre-stack
git status
# 确认 secrets.env 未被追踪
git ls-files | grep -E '\.env|\.db|secrets'
# 应为空输出
```

**步骤 3：如已有追踪的敏感文件，从 Git 中移除**
```bash
# 仅当 git ls-files 返回结果时执行
git rm --cached secrets.env 2>/dev/null
git rm --cached *.db 2>/dev/null
git commit -m "Remove sensitive files from tracking"
```

---

## 1.3 cloudflared token 文件化改造

### 目标
将明文 token 从 systemd 单元迁移到文件，消除 ps/journald 泄露面。
> 经 `cloudflared tunnel run --help` 核实：`--token-file <path>` 接受**原始 token 字符串**（与现运行的 `--token` 同内容），**不是** credentials JSON。故只采用单一清晰路径，不再混用 JSON 写法。

### 当前状态
```
ExecStart=/usr/local/bin/cloudflared tunnel --no-autoupdate run --token eyJhIjoi...
```
token 在 `ps aux`、`journalctl`、单元文件中全部可见。

### 实现步骤（单一路径）

**步骤 1：提取当前 raw token 并写入文件**
```bash
# 从 systemd 单元提取 raw token
TOKEN=$(grep -oP '(?<=--token )\S+' /etc/systemd/system/cloudflared.service)

# 创建凭据目录并写入（纯文本，内容即原 --token 的值）
mkdir -p /etc/cloudflared
chmod 700 /etc/cloudflared
printf '%s' "$TOKEN" > /etc/cloudflared/token
chmod 600 /etc/cloudflared/token
chown root:root /etc/cloudflared/token
```

**步骤 2：修改 systemd 单元**
```bash
# 备份原单元
cp /etc/systemd/system/cloudflared.service /etc/systemd/system/cloudflared.service.bak

# 仅替换 --token <任意值> 为 --token-file（避免 token 内容作为正则导致 sed 报错）
sed -i 's|--token [^ ]*|--token-file /etc/cloudflared/token|' /etc/systemd/system/cloudflared.service
grep ExecStart /etc/systemd/system/cloudflared.service
# 期望：ExecStart=/usr/local/bin/cloudflared tunnel --no-autoupdate run --token-file /etc/cloudflared/token
```

**步骤 3：重启验证**
```bash
systemctl daemon-reload
systemctl restart cloudflared.service
sleep 3
systemctl status cloudflared.service
# 确认 active (running)

# 验证 token 不再出现在 ps 中
ps aux | grep cloudflared
# 应只看到 --token-file，不看到 token 值
```

**步骤 4：清理备份**
```bash
rm /etc/systemd/system/cloudflared.service.bak
```

---

## 1.4 Redis 强密码（可选 — 本栈未使用 Redis）

> **架构原则（见 Doc 9 §9.10）**：本栈任务队列用 SQLite（`tasks.db`），**不引入 Redis/MQ**（见 project-plan.md「队列 | SQLite 表，不引入 Redis/MQ」）。
> 经核实：`/opt/calibre-web` 应用代码与 `/opt/calibre-stack`（server.py / metadata-tool）均**无 `import redis`**；本机 Redis 仅因其他无关用途运行。
> 因此 **§1.4 对本项目属不必要开销**，保留仅作「若该 box 上其他应用确实用 Redis」的参考。

### 目标
替换默认弱密码 `redis` 为随机强密码（**仅当 Redis 被本机其他应用实际使用时执行**）。

### 实现步骤

**步骤 1：探测现有 Redis 消费者**
```bash
# 查看哪些进程连接 Redis
ss -tnp | grep 6379
# 或
redis-cli CLIENT LIST 2>/dev/null
```

**步骤 2：更新 Redis 配置**
```bash
# 读取 secrets.env 中的密码
source /opt/calibre-stack/secrets.env

# 备份原配置
cp /etc/redis/redis.conf /etc/redis/redis.conf.bak

# 替换密码（注释掉旧的，添加新的）
sed -i 's/^requirepass .*/# &/' /etc/redis/redis.conf
echo "requirepass ${REDIS_PASSWORD}" >> /etc/redis/redis.conf
```

**步骤 3：重启 Redis 并更新消费者**
```bash
systemctl restart redis-server
sleep 2

# 测试新密码
redis-cli -a "${REDIS_PASSWORD}" ping
# Expected: PONG
```

**步骤 4：检查 Calibre-Web 是否使用 Redis**
```bash
# 本栈 Calibre-Web 代码无 import redis（§1.4 开头已核实），通常无需此步。
# 仅当你在本机其他应用启用 Redis 后，需同步那些应用的密码配置。
grep -r "redis" /opt/calibre-web/ 2>/dev/null | grep -i pass || echo "Calibre-Web 未使用 Redis，跳过"
```

**步骤 5：清理备份**
```bash
rm /etc/redis/redis.conf.bak
```

---

## 1.5 安全验证清单

完成所有步骤后，执行以下验证：

```bash
echo "=== 1. secrets.env ==="
stat -c "%a %U %G" /opt/calibre-stack/secrets.env
# Expected: 600 calibreweb calibreweb

echo "=== 2. .gitignore ==="
cd /opt/calibre-stack && git ls-files | grep -E '\.env|secrets|\.db$'
# Expected: (empty)

echo "=== 3. cloudflared ==="
ps aux | grep cloudflared | grep -o '\-\-token [^ ]*' | head -1
# Expected: --token-file /etc/cloudflared/token (no raw token)
stat -c "%a" /etc/cloudflared/token 2>/dev/null
# Expected: 600

echo "=== 4. Services ==="
systemctl is-active cloudflared
# Expected: active
```

---

## 1.6 回滚方案

如果任何步骤失败：

| 问题 | 回滚 |
|------|------|
| secrets.env 创建失败 | 检查磁盘空间和权限，修复后重试 |
| cloudflared 启动失败 | `cp /etc/systemd/system/cloudflared.service.bak /etc/systemd/system/cloudflared.service && systemctl daemon-reload && systemctl restart cloudflared` |

---

## 1.7 依赖关系

```
Phase 0 (本阶段)
    │
    ├── secrets.env → Phase 2 (zlibrary 凭据)
    ├── .gitignore → Phase 收尾 (git push)
    └── cloudflared → 无后续依赖
```
