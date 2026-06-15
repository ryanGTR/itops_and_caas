#!/usr/bin/env bash
# 急件 PIR 開單器 self-test (TASK-E2)
#
# 用 dry-run(不真開 issue)驗證 open_pir.py 的判斷:
#   emergency → 產出帶必要欄位的 PIR 內文;standard → 略過(no-op)。
set -uo pipefail
cd "$(dirname "$0")/../../.." || exit 2

PASS=0
FAILED=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 造夾具
python3 - "$TMP" <<'PY'
import yaml, sys
from pathlib import Path
def write(name, meta_extra):
    r = {"apiVersion": "golden-path/v1", "kind": "DeploymentRequest",
         "metadata": {"app": "x", "environment": "prod", "requestedBy": "dev",
                      "serviceRequest": "#9", **meta_extra},
         "spec": {"source": {"digest": "sha256:" + "a"*64, "gitCommit": "def456"}}}
    Path(sys.argv[1], name).write_text(yaml.safe_dump(r, allow_unicode=True), encoding="utf-8")
write("emerg.yaml", {"changeType": "emergency", "justification": "prod down #42",
                     "pir": {"owner": "oncall", "dueBy": "2026-06-20"}})
write("std.yaml", {"changeType": "standard"})
PY

want() { # $1=說明  $2=檔  $3=期望在輸出中出現的字串
  local desc="$1" file="$2" needle="$3"
  if python3 scripts/open_pir.py --request "$file" 2>&1 | grep -qF "$needle"; then
    echo "✅ $desc"; PASS=$((PASS + 1))
  else
    echo "❌ $desc(輸出未含:$needle)"; FAILED=$((FAILED + 1))
  fi
}

echo "🔍 急件 PIR 開單器 self-test(dry-run)"
want "emergency → 產出 PIR 標題"        "$TMP/emerg.yaml" "[PIR] x @ prod"
want "emergency → 內文含 PIR 承諾"       "$TMP/emerg.yaml" "PIR 承諾"
want "emergency → 內文含安全閘門確認"    "$TMP/emerg.yaml" "安全閘門確認"
want "standard → 略過(no-op)"          "$TMP/std.yaml"   "略過"

echo
if [ "$FAILED" -ne 0 ]; then
  echo "self-test FAILED:$FAILED 項未如預期"; exit 1
fi
echo "self-test PASSED:全部 $PASS 項符合預期"
exit 0
