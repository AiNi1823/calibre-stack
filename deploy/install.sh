#!/usr/bin/env bash
# Calibre Stack 一键部署脚本（幂等）
set -euo pipefail

STACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$STACK_DIR/deploy"

echo "==> 1/4 安装 systemd 单元"
sudo cp "$DEPLOY_DIR/calibre-web.service" /etc/systemd/system/
sudo cp "$DEPLOY_DIR/calibre-async-upload.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable calibre-web calibre-async-upload

echo "==> 2/4 配置 nginx"
sudo cp "$DEPLOY_DIR/nginx-calibre-web.conf" /etc/nginx/sites-available/calibre-web
sudo ln -sf /etc/nginx/sites-available/calibre-web /etc/nginx/sites-enabled/calibre-web
sudo nginx -t
sudo systemctl reload nginx

echo "==> 3/4 启动服务"
sudo systemctl restart calibre-web calibre-async-upload

echo "==> 4/4 验证"
sleep 3
curl -sf http://127.0.0.1:8086/health && echo " async-upload OK"
curl -sf -o /dev/null http://127.0.0.1:8083/ && echo " calibre-web OK"
curl -sf -o /dev/null http://127.0.0.1:8084/ && echo " nginx OK"

echo "部署完成。上传入口：https://<域名>/async-upload"
