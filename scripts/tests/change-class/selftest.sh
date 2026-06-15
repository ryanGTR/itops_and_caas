#!/usr/bin/env bash
# 變更分類驗證器 self-test (TASK-E1)
#
# 證明 fail-closed:合規分類放行;例外缺理由 / 非法型別 / 插單缺授權 / 繞過旗標 一律被擋。
# 比照 D5 / CMDB self-test 做法,用 tmp 夾具不污染 repo。
set -uo pipefail
cd "$(dirname "$0")/../../.." || exit 2

PASS=0
FAILED=0
check() { # $1=期望 exit  $2=說明  其餘=參數
  local want=$1 desc=$2
  shift 2
  python3 scripts/validate_change_class.py "$@" >/dev/null 2>&1
  local got=$?
  if [ "$got" -eq "$want" ]; then
    echo "✅ $desc (exit $got)"; PASS=$((PASS + 1))
  else
    echo "❌ $desc (期望 exit $want,實得 $got)"; FAILED=$((FAILED + 1))
  fi
}

echo "🔍 變更分類驗證器 self-test"

# 1) 真實 deployments → 通過(標準變更)
check 0 "合規(標準變更)→ 通過" --deployments-dir deployments

# 用 python 造違規夾具
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 - "$TMP" <<'PY'
import yaml
from pathlib import Path
base = {
    "apiVersion": "golden-path/v1", "kind": "DeploymentRequest",
    "metadata": {"app": "x", "environment": "test", "requestedBy": "dev"},
    "spec": {"source": {"digest": "sha256:" + "0"*64}},
}
def write(sub, meta_extra=None, spec_extra=None):
    import copy
    r = copy.deepcopy(base)
    if meta_extra: r["metadata"].update(meta_extra)
    if spec_extra: r["spec"].update(spec_extra)
    d = Path(__import__("sys").argv[1], sub); d.mkdir(parents=True)
    (d / "x.yaml").write_text(yaml.safe_dump(r, allow_unicode=True), encoding="utf-8")

# A: 急件缺 justification
write("noreason", {"changeType": "emergency"})
# B: 非法 changeType
write("badtype", {"changeType": "yolo"})
# C: 插單缺 by/reason
write("badexpedite", {"expedite": {"reason": "急"}})
# D: 繞過旗標(試圖關閉驗章)
write("bypass", {"changeType": "emergency", "justification": "prod down",
                 "pir": {"owner": "oncall", "dueBy": "2026-06-20"}},
      {"skipVerify": True})
# E: 急件缺 PIR 承諾(TASK-E2)
write("nopir", {"changeType": "emergency", "justification": "prod incident #42"})
# F: 急件附理由 + PIR 承諾 → 合法
write("okemerg", {"changeType": "emergency", "justification": "prod incident #42",
                  "pir": {"owner": "oncall", "dueBy": "2026-06-20"}})
PY

check 1 "急件缺 justification → 拒絕"        --deployments-dir "$TMP/noreason"
check 1 "非法 changeType → 拒絕"             --deployments-dir "$TMP/badtype"
check 1 "插單缺 by/reason → 拒絕"            --deployments-dir "$TMP/badexpedite"
check 1 "繞過旗標(skipVerify)→ 拒絕"        --deployments-dir "$TMP/bypass"
check 1 "急件缺 PIR 承諾 → 拒絕"             --deployments-dir "$TMP/nopir"
check 0 "急件附 justification + PIR → 通過"  --deployments-dir "$TMP/okemerg"

echo
if [ "$FAILED" -ne 0 ]; then
  echo "self-test FAILED:$FAILED 項未如預期"; exit 1
fi
echo "self-test PASSED:全部 $PASS 項符合預期(變更分類 fail-closed 有效)"
exit 0
