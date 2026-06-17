#!/usr/bin/env bash
# 分級→控制矩陣閘門 self-test —— 含「翻一個分級標籤 → 系統當場改變要求」的 demo。
#
# 證明:同一個部署,只把 dataClassification 從 internal 翻成 confidential,
# 系統就要求更高的控制、缺了就 fail-closed 擋下。這把 dataClassification 從裝飾標籤
# 變成「會驅動、被強制」的 policy 輸入(ISMS 風險為本),也是對決公文文化的 demo 核武。
#
# 用 fixtures(臨時 DeploymentRequest),不動真實 deployments/。需 python3 + PyYAML。
set -uo pipefail
cd "$(dirname "$0")/../../.." || exit 2

GATE=(python3 scripts/validate_classification_controls.py)
MATRIX=policies/classification-matrix.yaml
PASS=0; FAILED=0

WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT

# 寫一張 DeploymentRequest fixture:write_req <file> <classification> <controls-yaml>
write_req() {
  mkdir -p "$(dirname "$1")"
  { cat <<YAML
apiVersion: golden-path/v1
kind: DeploymentRequest
metadata: { app: demo, environment: fixture }
spec:
  dataClassification: $2
  controls:
$3
YAML
  } > "$1"
}

expect() { # $1=期望 exit  $2=說明  其餘=gate 參數
  local want=$1 desc=$2; shift 2
  "${GATE[@]}" "$@" >/tmp/cls-selftest.out 2>&1; local got=$?
  if [ "$got" -eq "$want" ]; then echo "✅ $desc (exit $got)"; PASS=$((PASS+1))
  else echo "❌ $desc (期望 $want,實得 $got)"; sed 's/^/     /' /tmp/cls-selftest.out; FAILED=$((FAILED+1)); fi
}

INTERNAL_CTL=$'    encryptionInTransit: true\n    approvals: 1'
CONF_CTL=$'    encryptionInTransit: true\n    encryptionAtRest: true\n    networkRestricted: true\n    approvals: 2\n    vulnScan: { high: 0, critical: 0 }'

echo "▶ 分級→控制矩陣 self-test(在 $WORK)"

# 1) 正向:internal + internal 控制 → 放行
D1="$WORK/d1"; write_req "$D1/r.yaml" internal "$INTERNAL_CTL"
expect 0 "正向:internal 滿足 internal 控制 → 放行" --deployments-dir "$D1" --matrix "$MATRIX"

# 2) 正向:confidential + 完整高階控制 → 放行
D2="$WORK/d2"; write_req "$D2/r.yaml" confidential "$CONF_CTL"
expect 0 "正向:confidential 滿足高階控制 → 放行" --deployments-dir "$D2" --matrix "$MATRIX"

# 3) ★ DEMO:同一張只把 internal 翻成 confidential(控制沒跟上)→ 當場被擋
D3="$WORK/d3"; write_req "$D3/r.yaml" confidential "$INTERNAL_CTL"
expect 1 "★ 翻標籤 internal→confidential(控制沒跟上)→ 被擋" --deployments-dir "$D3" --matrix "$MATRIX"

# 4) 負向:confidential 缺核可數(只 1、需 2)
D4="$WORK/d4"; write_req "$D4/r.yaml" confidential $'    encryptionInTransit: true\n    encryptionAtRest: true\n    networkRestricted: true\n    approvals: 1\n    vulnScan: { high: 0, critical: 0 }'
expect 1 "負向:confidential 核可數不足 → 被擋" --deployments-dir "$D4" --matrix "$MATRIX"

# 5) 負向:confidential 有 HIGH 漏洞
D5="$WORK/d5"; write_req "$D5/r.yaml" confidential $'    encryptionInTransit: true\n    encryptionAtRest: true\n    networkRestricted: true\n    approvals: 2\n    vulnScan: { high: 3, critical: 0 }'
expect 1 "負向:confidential 有 HIGH 漏洞 → 被擋" --deployments-dir "$D5" --matrix "$MATRIX"

# 6) 漸進:同樣不合規,observe 模式只報不擋(exit 0)
expect 0 "漸進:observe 模式不合規只報不擋(exit 0)" --deployments-dir "$D3" --matrix "$MATRIX" --mode observe

echo
echo "self-test 結果:PASS=$PASS FAILED=$FAILED"
[ "$FAILED" -eq 0 ] && { echo "✅ 全部符合預期(分級→控制矩陣 fail-closed 有效)"; exit 0; } \
                    || { echo "✗ 有案例不符預期"; exit 1; }
