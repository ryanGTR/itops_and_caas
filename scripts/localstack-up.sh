#!/usr/bin/env bash
# localstack-up.sh — 用 Podman 啟動本機 LocalStack,供 Phase 2 IaC smoke test
#
# 用法:  bash scripts/localstack-up.sh
#
# 已知問題:某些網路下大映像會在 IPv6 連 Docker CDN 時逾時(小映像正常)。
#   緩解(擇一):
#     1) 換網路(最簡單)
#     2) 強制 IPv4:拉取前
#          sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1
#        拉完再設回:
#          sudo sysctl -w net.ipv6.conf.all.disable_ipv6=0
#     3) 公司 Nexus pull-through(若 nexus.corp.local:5000 有代理 Docker Hub):
#          podman pull nexus.corp.local:5000/localstack/localstack:latest
#   詳見 docs/adr/0001-phase2-iac-stack.md

set -euo pipefail

IMAGE="${LOCALSTACK_IMAGE:-docker.io/localstack/localstack:latest}"
NAME="localstack"

echo "==> 拉取映像(加 retry):$IMAGE"
podman pull --retry 8 --retry-delay 10s "$IMAGE"

echo "==> 啟動容器(port 4566)"
podman rm -f "$NAME" >/dev/null 2>&1 || true
podman run -d --name "$NAME" -p 4566:4566 "$IMAGE"

echo "==> 等待 LocalStack 就緒(最多 60 秒)"
ready=0
for _ in $(seq 1 30); do
  if curl -sf http://localhost:4566/_localstack/health >/dev/null 2>&1; then
    ready=1; break
  fi
  sleep 2
done
if [ "$ready" = "1" ]; then
  echo "LocalStack ready ✅"
  curl -s http://localhost:4566/_localstack/health | head -c 300; echo
else
  echo "!! LocalStack 尚未就緒,檢查:podman logs localstack"
  exit 1
fi

cat <<'EOF'

下一步 — 用合規模組在 LocalStack 開一個 bucket(P2-1 smoke test):
  cd ~/Documents/itops_and_caas/iac/examples/localstack-smoke
  tofu init
  tofu apply -auto-approve
  aws --endpoint-url=http://localhost:4566 s3 ls

收工關閉:
  podman rm -f localstack
EOF
