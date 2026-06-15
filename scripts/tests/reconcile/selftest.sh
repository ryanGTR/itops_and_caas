#!/usr/bin/env bash
# 漂移對帳 self-test (TASK-E4)
#
# 用 --observed-file(不需 podman)餵入「實際態」,確定性驗證:
#   相符 → 無漂移(0);digest 不符 → 漂移(1);實例缺漏 → 漂移(1)。
set -uo pipefail
cd "$(dirname "$0")/../../.." || exit 2

PASS=0
FAILED=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 從真實 CMDB 取 instance 與 expected digest,組三種「實際態」夾具(與 CMDB 同步)
python3 - "$TMP" <<'PY'
import json, sys, yaml
from pathlib import Path
# 取 software 層 CI(有 runtime.instance + source.digest);多層 CMDB 後 host/middleware 沒有這些。
ci = next(c for c in (yaml.safe_load(p.read_text(encoding="utf-8")) for p in Path("cmdb").rglob("*.yaml"))
          if (c.get("metadata") or {}).get("type") == "deployed-application")
inst = ci["spec"]["runtime"]["instance"]
dig = ci["spec"]["source"]["digest"]
d = Path(sys.argv[1])
(d / "match.json").write_text(json.dumps({inst: dig}))
(d / "mismatch.json").write_text(json.dumps({inst: "sha256:" + "0"*64}))
(d / "missing.json").write_text(json.dumps({inst: None}))
PY

check() { # $1=期望 exit  $2=說明  $3=observed-file
  python3 scripts/reconcile.py --observed-file "$3" >/dev/null 2>&1
  local got=$?
  if [ "$got" -eq "$1" ]; then echo "✅ $2 (exit $got)"; PASS=$((PASS+1))
  else echo "❌ $2 (期望 $1,實得 $got)"; FAILED=$((FAILED+1)); fi
}

echo "🔍 漂移對帳 self-test"
check 0 "線上 == CMDB 期望 → 無漂移"        "$TMP/match.json"
check 1 "線上 digest ≠ 期望 → 漂移"         "$TMP/mismatch.json"
check 1 "實例缺漏(被移除)→ 漂移"           "$TMP/missing.json"

echo
if [ "$FAILED" -ne 0 ]; then echo "self-test FAILED:$FAILED 項未如預期"; exit 1; fi
echo "self-test PASSED:全部 $PASS 項符合預期(漂移偵測有效)"
exit 0
