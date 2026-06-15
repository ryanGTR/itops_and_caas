#!/usr/bin/env bash
# 過版閘門 policy-promote self-test (TASK-F3)
#
# 證明三閘門 fail-closed:
#   合規過版(只動 source + digest 來自上一區 + 重新驗章過)→ 放行;
#   夾帶 config / 夾帶他檔 / 跳關(digest 對不上上一區)/ 偽造簽章 → 一律擋;
#   非過版 PR → 不管轄,放行(no-op)。
# 比照 D5 / change-class self-test:用 tmp 夾具,不污染 repo。
# 重新驗章相關案例需要 cosign;無 cosign 時自動略過(CI 會裝 cosign 跑全套)。
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
SCRIPT="$REPO/scripts/validate_promote.py"
PUB="$REPO/trust/cosign.pub"
GOODSIG="$REPO/scripts/tests/deploy-gate/good.sig"     # 簽 SIGNED 這個 digest
WRONGSIG="$REPO/scripts/tests/deploy-gate/wrong.sig"   # 簽別的 digest

# good.sig 所簽的 digest(= deploy-gate good-request.yaml 的 digest)
SIGNED="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
OLD="sha256:$(printf '0%.0s' {1..64})"
DIFF="sha256:$(printf '1%.0s' {1..64})"

HAVE_COSIGN=0
command -v cosign >/dev/null 2>&1 && HAVE_COSIGN=1

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cd "$TMP" || exit 2

PASS=0; FAILED=0; SKIP=0

# --- 夾具產生器 ---
write_head() { # $1=digest $2=httpPort
  mkdir -p deployments/uat
  cat > deployments/uat/app.yaml <<YAML
apiVersion: golden-path/v1
kind: DeploymentRequest
metadata:
  app: app
  environment: uat
  requestedBy: developer
spec:
  source:
    artifact: reg/app
    version: v1
    digest: $1
  dataClassification: confidential
  runtime:
    type: openliberty
    httpPort: $2
YAML
}
write_cmdb() { # $1=upstream-digest $2=signature-path
  mkdir -p cmdb/test
  cat > cmdb/test/app.yaml <<YAML
apiVersion: cmdb/v1
kind: ConfigurationItem
metadata: { ciId: ci-app-test, app: app, environment: test }
spec:
  source:
    digest: $1
    signature: $2
YAML
}

# base 版本(過版前):OLD digest、config httpPort 9099
mkdir -p base/deployments/uat
write_head "$OLD" 9099
cp deployments/uat/app.yaml base/deployments/uat/app.yaml

run_gate() { python3 "$SCRIPT" --pubkey "$PUB" "$@" >/dev/null 2>&1; }
expect() { # $1=want-exit $2=desc  其餘=gate 參數
  local want=$1 desc=$2; shift 2
  run_gate "$@"; local got=$?
  if [ "$got" -eq "$want" ]; then echo "✅ $desc (exit $got)"; PASS=$((PASS+1))
  else echo "❌ $desc (期望 $want,實得 $got)"; FAILED=$((FAILED+1)); fi
}
skip() { echo "⏭  $1(無 cosign,略過)"; SKIP=$((SKIP+1)); }

echo "🔍 過版閘門 policy-promote self-test"

# 1) 合規過版:只動 source,digest = 上一區確認態,簽章對得上 → 放行(需 cosign)
write_head "$SIGNED" 9099
write_cmdb "$SIGNED" "$GOODSIG"
if [ "$HAVE_COSIGN" = 1 ]; then
  expect 0 "合規過版(source-only + 血統符 + 驗章過)→ 放行" \
    --promote-pr --changed deployments/uat/app.yaml --base-dir base
else
  skip "合規過版 → 放行"
fi

# 2) 夾帶 config(連 httpPort 也改)→ 範圍守衛擋
write_head "$SIGNED" 9098
write_cmdb "$SIGNED" "$GOODSIG"
expect 1 "夾帶 config 變更 → 擋" \
  --promote-pr --changed deployments/uat/app.yaml --base-dir base

# 3) 夾帶部署檔以外的檔案 → 範圍守衛擋
write_head "$SIGNED" 9099
write_cmdb "$SIGNED" "$GOODSIG"
expect 1 "夾帶他檔(scripts/evil.py)→ 擋" \
  --promote-pr --changed deployments/uat/app.yaml --changed scripts/evil.py --base-dir base

# 4) 跳關/血統不符:目標 digest 不存在於上一區確認態 → 擋(驗章前就擋)
write_head "$DIFF" 9099
write_cmdb "$SIGNED" "$GOODSIG"
expect 1 "跳關(digest 對不上上一區)→ 擋" \
  --promote-pr --changed deployments/uat/app.yaml --base-dir base

# 4b) 上一區根本沒登錄(CMDB 無此 app)→ 擋
write_head "$SIGNED" 9099
rm -rf cmdb
expect 1 "上一區未部署登錄(禁跳關)→ 擋" \
  --promote-pr --changed deployments/uat/app.yaml --base-dir base

# 5) 偽造簽章:血統符但上一區簽章驗不過 → 重新驗章擋(需 cosign)
write_head "$SIGNED" 9099
write_cmdb "$SIGNED" "$WRONGSIG"
if [ "$HAVE_COSIGN" = 1 ]; then
  expect 1 "血統符但簽章偽造 → 重新驗章擋" \
    --promote-pr --changed deployments/uat/app.yaml --base-dir base
else
  skip "偽造簽章 → 重新驗章擋"
fi

# 6) 非過版 PR(只改 config、未動 source、未標記)→ 不管轄,放行
write_head "$OLD" 9098
write_cmdb "$SIGNED" "$GOODSIG"
expect 0 "非過版 PR(只改 config)→ no-op 放行" \
  --changed deployments/uat/app.yaml --base-dir base

echo
[ "$SKIP" -gt 0 ] && echo "(略過 $SKIP 項需 cosign 的案例)"
if [ "$FAILED" -ne 0 ]; then echo "self-test FAILED:$FAILED 項未如預期"; exit 1; fi
echo "self-test PASSED:全部 $PASS 項符合預期(過版三閘門 fail-closed 有效)"
exit 0
