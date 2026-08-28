#!/usr/bin/env bash
# Calibre-Web UI-Rewrite 预发布 Beta（8085 并行实例）搭建脚本（幂等）
# 仅创建/更新 /opt/calibre-web-beta 与 systemd 单元，不改动生产（8083/8084）。
# 用法：sudo bash deploy/setup-beta.sh
set -euo pipefail

STACK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FORK="$STACK/calibre-web"
BETA=/opt/calibre-web-beta
BETA_CPS="$BETA/venv/lib/python3.12/site-packages/calibreweb/cps"

echo "==> 1/4 准备 beta 目录（venv 复制 + 生产 app.db 快照）"
mkdir -p "$BETA"
cp -a /opt/calibre-web/venv "$BETA/venv"
cp /opt/calibre-web/app.db "$BETA/app.db"

echo "==> 2/4 修正 beta venv 的 cps 脚本 shebang（指向 beta venv python）"
sed -i '1s|#!/opt/calibre-web/venv/bin/python3|#!/opt/calibre-web-beta/venv/bin/python3|' "$BETA/venv/bin/cps"

echo "==> 3/4 覆盖 fork 的 cps 源（含全部 UI 改写：templates/static/js/py）到 beta 站点包"
cp -a "$FORK/cps/." "$BETA_CPS"/

echo "==> 4/4 修正 beta app.db 端口为 8085（避免与生产 8083 冲突）"
"$BETA/venv/bin/python3" - <<'PY'
import sqlite3
c = sqlite3.connect('/opt/calibre-web-beta/app.db')
c.execute('update settings set config_port=8085, config_external_port=8085')
c.commit()
print('beta app.db port set to 8085')
PY

chown -R calibreweb:calibreweb "$BETA"

echo "==> 安装/刷新 systemd 单元并启动"
cp "$STACK/deploy/calibre-web-beta.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable calibre-web-beta >/dev/null 2>&1 || true
systemctl restart calibre-web-beta

echo "==> 验证"
sleep 6
systemctl is-active calibre-web-beta
grep -q cw-app "$BETA_CPS/templates/layout.html" && echo "new UI markers: OK"
curl -s -o /dev/null -w "beta /static/css/tailwind.css -> HTTP %{http_code}\n" http://127.0.0.1:8085/static/css/tailwind.css

echo "完成：预览访问 http://127.0.0.1:8085/ （生产 8083/8084 未受影响）"
