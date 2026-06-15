#!/usr/bin/env bash
# 過版生成器 self-test (TASK-F2)
#
# 證明 promote.py 的靈魂:只搬 source.digest(及血統),**runtime/config 與註解一律不動**。
set -uo pipefail
cd "$(dirname "$0")/../../.." || exit 2

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
NEW="sha256:$(printf '1%.0s' {1..64})"
OLD="sha256:$(printf '0%.0s' {1..64})"

# 來源 CMDB CI(確認態):新 digest
mkdir -p "$TMP/cmdb/uat"
cat > "$TMP/cmdb/uat/app.yaml" <<YAML
apiVersion: cmdb/v1
kind: ConfigurationItem
metadata: { ciId: ci-app-uat, app: app, environment: uat }
spec:
  source:
    artifact: reg/app
    version: v2
    digest: ${NEW}
    gitCommit: newsha
    signature: x
YAML

# 目標 DeploymentRequest:舊 digest + 獨特 config + 註解(promote 後須完整保留)
mkdir -p "$TMP/deploy/prod"
cat > "$TMP/deploy/prod/app.yaml" <<YAML
kind: DeploymentRequest
metadata:
  app: app
  environment: prod
spec:
  source:
    artifact: reg/app
    version: v1
    digest: "${OLD}"          # 會被換成新 digest
    gitCommit: "oldsha"
  dataClassification: confidential   # ← config:不可被動
  runtime:
    httpPort: 9099            # ← config:不可被動(獨特標記)
YAML

python3 scripts/promote.py --from uat --to prod --app app \
  --cmdb-dir "$TMP/cmdb" --deployments-dir "$TMP/deploy" >/dev/null 2>&1

T="$TMP/deploy/prod/app.yaml"
PASS=0; FAILED=0
chk() { if eval "$2"; then echo "✅ $1"; PASS=$((PASS+1)); else echo "❌ $1"; FAILED=$((FAILED+1)); fi; }

echo "🔍 過版生成器 self-test"
chk "digest 已換成來源新值"        "grep -q '$NEW' '$T'"
chk "舊 digest 已消失"             "! grep -q '$OLD' '$T'"
chk "gitCommit 已更新(血統傳遞)"   "grep -q 'newsha' '$T'"
chk "config:httpPort 9099 保留"    "grep -q 'httpPort: 9099' '$T'"
chk "config:分級 confidential 保留" "grep -q 'dataClassification: confidential' '$T'"
chk "註解保留(# ← config:不可被動)" "grep -q '不可被動' '$T'"

echo
if [ "$FAILED" -ne 0 ]; then echo "self-test FAILED:$FAILED 項未如預期"; exit 1; fi
echo "self-test PASSED:全部 $PASS 項符合預期(只搬 source,config 不動)"
exit 0
