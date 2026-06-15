#!/usr/bin/env bash
# CMDB 驗證器 self-test (TASK-D7)
#
# 證明 CMDB 閘門 fail-closed:合規 CI 通過;digest 與來源漂移 / 缺組態關係 一律被擋。
# 比照 D5 驗章閘門與 Phase 1/2 的違規 self-test 做法。
set -uo pipefail
cd "$(dirname "$0")/../../.." || exit 2

PASS=0
FAILED=0
check() { # $1=期望 exit  $2=說明  其餘=validate 參數
  local want=$1 desc=$2
  shift 2
  python3 scripts/cmdb_validate.py "$@" >/dev/null 2>&1
  local got=$?
  if [ "$got" -eq "$want" ]; then
    echo "✅ $desc (exit $got)"; PASS=$((PASS + 1))
  else
    echo "❌ $desc (期望 exit $want,實得 $got)"; FAILED=$((FAILED + 1))
  fi
}

echo "🔍 CMDB 驗證器 self-test"

# 1) 真實 CMDB → 通過
check 0 "合規 CMDB → 通過" --cmdb-dir cmdb

# 用 python 從真實 CI 衍生「違規夾具」放進 tmp 目錄(不污染 repo)
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 - "$TMP" <<'PY'
import sys, copy, yaml
from pathlib import Path
src = next(Path("cmdb").rglob("*.yaml"))
ci = yaml.safe_load(src.read_text(encoding="utf-8"))
env = ci["metadata"]["environment"]

# 夾具 A:digest 與來源 DeploymentRequest 漂移(竄改 / 過期 CMDB)
a = copy.deepcopy(ci)
a["spec"]["source"]["digest"] = "sha256:" + "0" * 64
d = Path(sys.argv[1], "drift", env); d.mkdir(parents=True)
(d / "app.yaml").write_text(yaml.safe_dump(a, allow_unicode=True), encoding="utf-8")

# 夾具 B:缺組態關係(relationships 空)
b = copy.deepcopy(ci)
b["spec"]["relationships"] = []
d = Path(sys.argv[1], "norel", env); d.mkdir(parents=True)
(d / "app.yaml").write_text(yaml.safe_dump(b, allow_unicode=True), encoding="utf-8")
PY

# 2) digest 與來源漂移 → 拒絕
check 1 "digest 與來源漂移 → 拒絕" --cmdb-dir "$TMP/drift"
# 3) 缺組態關係 → 拒絕
check 1 "缺組態關係(relationships 空)→ 拒絕" --cmdb-dir "$TMP/norel"

echo
if [ "$FAILED" -ne 0 ]; then
  echo "self-test FAILED:$FAILED 項未如預期"; exit 1
fi
echo "self-test PASSED:全部 $PASS 項符合預期(CMDB 閘門 fail-closed 有效)"
exit 0
