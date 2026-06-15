#!/usr/bin/env bash
# 部署前驗章閘門 self-test (TASK-D5)
#
# 用「公鑰 + 已簽好的 fixture」驗證,**不需要私鑰**(故 CI 也能跑)。
# 證明閘門 fail-closed:合規放行;未簽 / 無 digest / 偽造簽章 一律拒絕。
# 比照 Phase 1/2 的違規 self-test 做法。
set -uo pipefail
cd "$(dirname "$0")/../../.." || exit 2

GATE=(python3 scripts/verify_deploy_gate.py)
D="scripts/tests/deploy-gate"
PASS=0
FAILED=0

expect() { # $1=期望 exit  $2=說明  其餘=gate 參數
  local want=$1 desc=$2
  shift 2
  "${GATE[@]}" "$@" >/dev/null 2>&1
  local got=$?
  if [ "$got" -eq "$want" ]; then
    echo "✅ $desc (exit $got)"
    PASS=$((PASS + 1))
  else
    echo "❌ $desc (期望 exit $want,實得 $got)"
    FAILED=$((FAILED + 1))
  fi
}

echo "🔍 部署前驗章閘門 self-test"
expect 0 "合規 + 有效簽章 → 放行" --request "$D/good-request.yaml" --signature "$D/good.sig"
expect 1 "未綁 digest(未建置/簽章)→ 拒絕" --request "$D/bad-request.yaml" --signature "$D/good.sig"
expect 1 "未提供簽章 → 拒絕" --request "$D/good-request.yaml"
expect 1 "簽章不符(偽造)→ 拒絕" --request "$D/good-request.yaml" --signature "$D/wrong.sig"

echo
if [ "$FAILED" -ne 0 ]; then
  echo "self-test FAILED:$FAILED 項未如預期"
  exit 1
fi
echo "self-test PASSED:全部 $PASS 項符合預期(閘門 fail-closed 有效)"
exit 0
