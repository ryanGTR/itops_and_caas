#!/usr/bin/env bash
# itops_ingest.sh — [itops 端] 消費 supply-chain 的交接 manifest,治理並部署。
#
# itops 不重建、不重簽——只 ingest 已簽好的 artifact,跑自己的部署右側治理:
#   更新 DeploymentRequest(只搬 source)→ D5 部署前驗章閘門(fail-closed)
#   → 部署 OpenLiberty + 煙霧測試 → CMDB 登錄(端到端證據)
#
# 用法:integration/itops_ingest.sh <app>.handoff.yaml
set -euo pipefail

ITOPS="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ITOPS"
INBOX="$ITOPS/integration/inbox"
MANIFEST="$INBOX/${1:?用法: itops_ingest.sh <app>.handoff.yaml}"
[ -f "$MANIFEST" ] || { echo "✗ 找不到 manifest:$MANIFEST"; exit 2; }
export PATH="$HOME/.local/bin:$PATH"
say() { printf '\n\033[1m▶ %s\033[0m\n' "$*"; }

# ── 讀 manifest ────────────────────────────────────────────
read -r APP ENVIRONMENT SIG < <(python3 - "$MANIFEST" <<'PY'
import sys, yaml
m = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
print(m["app"], m["environment"], m["signature"])
PY
)
REQUEST="deployments/${ENVIRONMENT}/${APP}.yaml"
[ -f "$REQUEST" ] || { echo "✗ 目標環境無 DeploymentRequest:$REQUEST"; exit 2; }
echo "▶ ingest:$APP → $ENVIRONMENT(來源 manifest:$(basename "$MANIFEST"))"

# ── 1. 把 manifest.source 寫進 DeploymentRequest(重用 promote 的 surgical_update,保留註解)──
say "[1/4] 套用 manifest 到 DeploymentRequest(只搬 source)"
python3 - "$MANIFEST" "$REQUEST" <<'PY'
import sys, yaml
sys.path.insert(0, "scripts")
from promote import surgical_update, PROMOTE_KEYS
m = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
src = m["source"]
new = {k: src[k] for k in PROMOTE_KEYS if k in src and src[k] != ""}
text = open(sys.argv[2], encoding="utf-8").read()
updated, changes = surgical_update(text, new)
open(sys.argv[2], "w", encoding="utf-8").write(updated)
for k,(o,n) in changes.items():
    print(f"  • {k}: {o} → {n}")
print("  (config/runtime 未動)" if changes else "  (已同步,無變更)")
PY

# ── 2. 放置簽章物證 ────────────────────────────────────────
say "[2/4] 放置簽章到環境目錄"
mkdir -p "deployments/${ENVIRONMENT}/sig"
cp "$INBOX/$SIG" "deployments/${ENVIRONMENT}/sig/${APP}.sig"
echo "  → deployments/${ENVIRONMENT}/sig/${APP}.sig"

# ── 3. itops 部署右側治理:D5 閘門 → 部署 → 煙霧測試 ──────────
say "[3/4] itops 部署前驗章閘門 + 部署(deploy_openliberty.sh)"
bash scripts/deploy_openliberty.sh \
  --request "$REQUEST" \
  --signature "deployments/${ENVIRONMENT}/sig/${APP}.sig"

# ── 4. CMDB 登錄(端到端證據)──────────────────────────────
say "[4/4] CMDB 登錄(組態 + 證據鏈)"
python3 scripts/cmdb_register.py --request "$REQUEST"

# ── 5.(可選)推進真 iTop(Combodo)當系統 of record ──────────
# iTop 是下游 ITSM/CMDB,不是部署閘門——它掛了不該擋部署,故 opt-in 且軟失敗。
# 啟用:export ITOP_SYNC=1 且設好 ITOP_PWD(REST 服務帳號密碼;見 integration/itop/README.md)。
if [ "${ITOP_SYNC:-0}" = "1" ]; then
  say "[5] 推進真 iTop(opt-in;系統 of record)"
  if [ -z "${ITOP_PWD:-}" ]; then
    echo "  ⚠ 已開 ITOP_SYNC 但未設 ITOP_PWD——略過 iTop 同步(不擋部署)。"
  elif python3 scripts/itop_sync.py --env "$ENVIRONMENT" --org "${ITOP_ORG:-Demo}"; then
    :
  else
    echo "  ⚠ iTop 同步失敗(可能 iTop 未啟動)——不擋部署;CMDB-as-code 仍是真相。稍後可手動重跑 itop_sync.py。"
  fi
fi

echo
echo "✅ itops 已 ingest 並治理 supply-chain 的 artifact:$APP @ $ENVIRONMENT"
