#!/usr/bin/env bash
# 部署到 OpenLiberty + 煙霧測試 — TASK-D6(ISO 20000 發布與部署管理)
#
# 黃金路徑階段⑥:把『已驗章的 artifact』部署到 [TASK-D3] 開出的 OpenLiberty runtime,
# 並以煙霧測試證明「可服務」。本腳本把整條尾段焊成一條不可繞過的鏈:
#
#   D5 驗章閘門(fail-closed) ──放行──▶ tofu apply(預設安全容器) ──▶ 煙霧測試(/health + 業務端點)
#        │                                                              │
#        └─ 不過就 exit,根本不部署                                       └─ 不回 200 就視為部署失敗
#
# 並做一道「部署即驗章物」的閉環檢查:跑起來的容器 image ID 必須等於 D5 驗過的 digest——
# 確保「部署的就是驗章的那一個」,不是別的映像偷渡(ISO 27001 A.8.28 完整性)。
#
# 對應治理控制項:
#   - ISO 20000 發布與部署管理(本階段主軸)
#   - ISO 27001 A.8.28 完整性(部署 == 驗章物)
#   - ITIL 發布驗證 / 部署後煙霧測試
#
# 用法:
#   scripts/deploy_openliberty.sh \
#     [--request deployments/openliberty-sandbox/supply-chain-backend.yaml] \
#     [--signature deployments/openliberty-sandbox/sig/supply-chain-backend.sig]
set -euo pipefail

# --- repo 根目錄 ---
cd "$(dirname "$0")/.." || exit 2
ROOT="$(pwd)"

REQUEST="deployments/openliberty-sandbox/supply-chain-backend.yaml"
SIGNATURE="deployments/openliberty-sandbox/sig/supply-chain-backend.sig"
ENV_DIR="iac/environments/openliberty-sandbox"

while [ $# -gt 0 ]; do
  case "$1" in
    --request)   REQUEST="$2"; shift 2 ;;
    --signature) SIGNATURE="$2"; shift 2 ;;
    *) echo "未知參數:$1" >&2; exit 2 ;;
  esac
done

say() { printf '\n\033[1m▶ %s\033[0m\n' "$*"; }

# ─────────────────────────────────────────────────────────────
# 階段⑤:部署前驗章閘門(fail-closed)——不過就根本不部署
# ─────────────────────────────────────────────────────────────
say "[1/5] D5 部署前驗章閘門(fail-closed)"
if ! python3 scripts/verify_deploy_gate.py --request "$REQUEST" --signature "$SIGNATURE"; then
  echo "✗ 驗章閘門拒絕,中止部署(沒有任何容器被啟動)。" >&2
  exit 1
fi

# 從 DeploymentRequest 取部署參數(單一真相來源)
read -r APP ENVIRONMENT ARTIFACT VERSION DIGEST HTTP_PORT < <(
  python3 - "$REQUEST" <<'PY'
import sys, yaml
r = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
m, s = r["metadata"], r["spec"]
src, rt = s["source"], s.get("runtime", {})
print(m["app"], m["environment"], src["artifact"], src["version"],
      src["digest"], rt.get("httpPort", 9080))
PY
)
IMAGE="${ARTIFACT}:${VERSION}"
SOCKET="unix:///run/user/$(id -u)/podman/podman.sock"
echo "  部署標的:$APP → $ENVIRONMENT"
echo "  映像:$IMAGE  (已驗 digest:$DIGEST)"

# ─────────────────────────────────────────────────────────────
# 階段④/⑥:tofu apply —— 用 D3 模組開出預設安全容器並部署映像
# ─────────────────────────────────────────────────────────────
say "[2/5] OpenTofu apply(預設安全的 OpenLiberty 容器)"
tofu -chdir="$ENV_DIR" init -input=false -upgrade >/dev/null
tofu -chdir="$ENV_DIR" apply -input=false -auto-approve \
  -var "image=$IMAGE" \
  -var "http_port=$HTTP_PORT" \
  -var "podman_socket=$SOCKET"

# ─────────────────────────────────────────────────────────────
# 完整性閉環:跑起來的容器 == D5 驗過的 digest
# ─────────────────────────────────────────────────────────────
say "[3/5] 完整性閉環檢查(部署的映像 == 驗章的 digest)"
RUNNING_ID="sha256:$(podman inspect "$APP" --format '{{.Image}}' 2>/dev/null | sed 's/^sha256://')"
if [ "$RUNNING_ID" != "$DIGEST" ]; then
  echo "✗ 完整性失敗:跑起來的映像($RUNNING_ID)≠ 驗章 digest($DIGEST)。" >&2
  echo "  視為部署失敗,請排查。" >&2
  exit 1
fi
echo "  ✅ 跑起來的容器映像 == D5 驗過的 digest。"

# ─────────────────────────────────────────────────────────────
# 階段⑥:煙霧測試 —— /health(平台存活)+ /api/products(業務可服務)
# ─────────────────────────────────────────────────────────────
say "[4/5] 煙霧測試(等服務起來,最多 90s)"
BASE="http://127.0.0.1:${HTTP_PORT}"
smoke() { # $1=path  $2=說明
  local path="$1" desc="$2" code i
  for i in $(seq 1 45); do
    code="$(curl -s -o /dev/null -w '%{http_code}' "${BASE}${path}" || true)"
    if [ "$code" = "200" ]; then
      echo "  ✅ ${desc}:GET ${path} → 200"
      return 0
    fi
    sleep 2
  done
  echo "  ✗ ${desc}:GET ${path} 未在時限內回 200(最後 code=${code:-無回應})" >&2
  return 1
}
SMOKE_OK=true
smoke /health        "平台健康檢查(mpHealth)" || SMOKE_OK=false
smoke /api/products  "業務端點(可服務)"        || SMOKE_OK=false

# ─────────────────────────────────────────────────────────────
# 留痕:部署證據(供 TASK-D7 CMDB / 稽核報告取用)
# ─────────────────────────────────────────────────────────────
say "[5/5] 記錄部署結果(部署證據留痕)"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RESULT=$([ "$SMOKE_OK" = true ] && echo success || echo failed)
RECORD="deployments/openliberty-sandbox/last-deploy.json"
cat > "$RECORD" <<JSON
{
  "app": "${APP}",
  "environment": "${ENVIRONMENT}",
  "image": "${IMAGE}",
  "digest": "${DIGEST}",
  "httpPort": ${HTTP_PORT},
  "deployedAt": "${TS}",
  "gate": "passed",
  "integrityCheck": "deployed-image == verified-digest",
  "smokeTest": {
    "health": "GET /health",
    "business": "GET /api/products"
  },
  "result": "${RESULT}"
}
JSON
echo "  → 已寫入 ${RECORD}(result=${RESULT})"

if [ "$SMOKE_OK" != true ]; then
  echo "✗ 部署完成但煙霧測試失敗,result=failed。" >&2
  exit 1
fi

say "部署成功 ✅  ${APP} 已在 ${ENVIRONMENT} 的 OpenLiberty 上可服務(${BASE})"
