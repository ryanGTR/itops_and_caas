#!/usr/bin/env bash
# 例外統計 self-test (TASK-E3)
#
# 驗證 generate_audit_report.collect_exception_stats 的計數邏輯:
# 變更型別分佈、插單計數、急件清單。離線(不需 gh)。
set -uo pipefail
cd "$(dirname "$0")/../../.." || exit 2

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 造夾具:2 標準(其中1插單)、1 急件、1 一般
python3 - "$TMP" <<'PY'
import yaml, sys
from pathlib import Path
def w(name, meta):
    r = {"apiVersion": "golden-path/v1", "kind": "DeploymentRequest",
         "metadata": {"app": "x", "environment": "e", "requestedBy": "d", **meta},
         "spec": {"source": {"digest": "sha256:" + "a"*64}}}
    Path(sys.argv[1], name).write_text(yaml.safe_dump(r, allow_unicode=True), encoding="utf-8")
w("a.yaml", {"changeType": "standard"})
w("b.yaml", {"changeType": "standard", "expedite": {"by": "mgr", "reason": "急"}})
w("c.yaml", {"changeType": "emergency", "justification": "down",
             "pir": {"owner": "oncall", "dueBy": "2026-06-20"}})
w("d.yaml", {"changeType": "normal"})
PY

python3 - "$TMP" <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("ar", "scripts/generate_audit_report.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
s = m.collect_exception_stats(sys.argv[1])
fails = []
def eq(name, got, want):
    if got != want: fails.append(f"{name}: 得 {got} 期望 {want}")
eq("total", s["total"], 4)
eq("standard", s["counts"]["standard"], 2)
eq("emergency", s["counts"]["emergency"], 1)
eq("normal", s["counts"]["normal"], 1)
eq("expedited", s["expedited"], 1)
eq("emergencies len", len(s["emergencies"]), 1)
eq("emergency owner", s["emergencies"][0]["owner"], "oncall")
if fails:
    print("❌ 例外統計 self-test FAILED:"); print("\n".join("  "+x for x in fails)); sys.exit(1)
print("✅ 例外統計 self-test PASSED:型別分佈 / 插單計數 / 急件清單皆正確。")
PY
