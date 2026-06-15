#!/usr/bin/env bash
# supplychain_emit.sh — [supply-chain 端] build+test+sign,產出交接 manifest 給 itops。
#
# 代表 supply-chain pipeline 在「左側」(build→test→sign)完成後,要交棒給 itops 的那一步。
# 本機 demo:直接對 supply-chain backend 跑;真實環境是 supply-chain 的 CI 產出這份 manifest。
#
# 產出:itops_and_caas/integration/inbox/<app>.handoff.yaml + 同名 .sig
set -euo pipefail

APP="supply-chain-backend"
ENVIRONMENT="${1:-openliberty-sandbox}"
VERSION="${2:-b1}"
BACKEND="$HOME/Documents/supply-chain/github/app/backend"
ITOPS="$(cd "$(dirname "$0")/.." && pwd)"
INBOX="$ITOPS/integration/inbox"
KEY="$ITOPS/trust/cosign.key"        # PoC key-pair(tier2 換成 hashivault transit)
IMAGE="localhost/${APP}"

export PATH="$HOME/.local/bin:$PATH"
say() { printf '\n\033[1m▶ %s\033[0m\n' "$*"; }
mkdir -p "$INBOX"

# ── 1. 測試(test gate 的證據來源)──────────────────────────
say "[1/4] mvn test(supply-chain 左側:測試)"
cd "$BACKEND"
mvn -B -q test
shopt -s globstar nullglob
xmls=( **/target/surefire-reports/TEST-*.xml )
[ ${#xmls[@]} -gt 0 ] || { echo "✗ 無 surefire 報告"; exit 1; }
TEST_COUNT=$(grep -ho '<testcase[ >]' "${xmls[@]}" | wc -l | tr -d ' ')
TEST_REPORT="sha256:$(cat $(printf '%s\n' "${xmls[@]}" | sort) | sha256sum | cut -d' ' -f1)"
echo "  測試:$TEST_COUNT 筆,報告指紋 $TEST_REPORT"

# ── 2. build(取不可變 digest)────────────────────────────
say "[2/4] podman build(供應鏈產物)"
podman build -q -t "${IMAGE}:${VERSION}" . >/dev/null
DIGEST="sha256:$(podman image inspect "${IMAGE}:${VERSION}" --format '{{.Id}}' | sed 's/^sha256://')"
echo "  digest:$DIGEST"

# ── 3. sign(cosign blob 簽 digest)───────────────────────
say "[3/4] cosign 簽章(對 digest)"
printf '%s' "$DIGEST" > /tmp/emit-digest.payload
COSIGN_PASSWORD="" cosign sign-blob --key "$KEY" --yes \
  --output-signature "$INBOX/${APP}.sig" /tmp/emit-digest.payload >/dev/null 2>&1
rm -f /tmp/emit-digest.payload
echo "  簽章:$INBOX/${APP}.sig"

# ── 4. 產出 handoff manifest(交接契約)──────────────────────
say "[4/4] 產出 handoff manifest"
cat > "$INBOX/${APP}.handoff.yaml" <<YAML
apiVersion: handoff/v1
kind: SignedArtifact
app: ${APP}
environment: ${ENVIRONMENT}
source:
  artifact: ${IMAGE}
  version: ${VERSION}
  digest: "${DIGEST}"
  gitCommit: "def4567"
  gitTag: "v0.0.0-EXAMPLE"
  testReport: "${TEST_REPORT}"
  testCount: ${TEST_COUNT}
signature: ${APP}.sig
provenance:
  builtBy: supply-chain
  pipeline: github/app/.github/workflows/supply-chain.yml
YAML
echo "  manifest:$INBOX/${APP}.handoff.yaml"
echo
echo "✅ supply-chain 端完成交棒。itops 端執行:integration/itops_ingest.sh ${APP}.handoff.yaml"
