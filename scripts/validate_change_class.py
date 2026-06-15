#!/usr/bin/env python3
"""變更分類驗證器 (TASK-E1) — fail-closed。

例外路徑(急件/插單/補單)的地基:每個 DeploymentRequest 都要帶「變更分類」,
且分類規則受強制檢查。任一不過即 exit 1。

驗證規則(全部 fail-closed):
  1. changeType 必須是 standard|normal|emergency|retroactive(缺 = standard)。
  2. priority 若有,必須是 P1..P4。
  3. emergency / retroactive ⇒ 必附 justification(非空)——例外要有理由。
  3b. emergency ⇒ 必附 pir{owner, dueBy}——「先做後審」的事後回顧不可賴帳(TASK-E2)。
  4. expedite(插單)若有,必須同時有 by 與 reason(誰批 + 為何加急,SoD + 留痕)。
  5. ★ 安全閘門不可因 changeType 關閉:請求內不得出現任何「繞過旗標」
     (如 skipVerify / bypassGate / disableScan…)——這是本層的核心鐵則,
     簽章/掃描/驗章對所有 changeType 一律強制,急件也不例外。

對應治理控制項:
  ISO 27001 A.8.32 變更管理(變更分類);A.8.28 完整性(閘門不鬆綁);
  ISO 27001 A.5.3 職責分離(插單需授權)。

用法:
  validate_change_class.py [--deployments-dir deployments]
Exit code:0 全通過;1 任一不合規(fail-closed)。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("✗ 需要 PyYAML(pip install pyyaml)")

CHANGE_TYPES = {"standard", "normal", "emergency", "retroactive"}
NEEDS_JUSTIFICATION = {"emergency", "retroactive"}
NEEDS_PIR = {"emergency"}  # 急件:先做後審 → 必須先「承諾」一張 PIR(TASK-E2)
PRIORITY_RE = re.compile(r"^P[1-4]$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# 「繞過旗標」偵測:任何 key 名同時帶「關閉意圖」+「安全閘門對象」即視為試圖鬆綁護欄。
BYPASS_INTENT = r"(skip|bypass|disable|ignore|no|force)"
GATE_TARGET = r"(gate|verif|sign|signature|scan|sca|check|policy|attest)"
BYPASS_RE = re.compile(BYPASS_INTENT + r"[_-]?" + GATE_TARGET, re.IGNORECASE)


def walk_keys(node, prefix=""):
    """遞迴收集所有 key 的點分路徑(供繞過旗標掃描)。"""
    if isinstance(node, dict):
        for k, v in node.items():
            path = f"{prefix}.{k}" if prefix else str(k)
            yield path
            yield from walk_keys(v, path)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_keys(v, f"{prefix}[{i}]")


def main() -> int:
    ap = argparse.ArgumentParser(description="變更分類驗證器 [TASK-E1]")
    ap.add_argument("--deployments-dir", default="deployments")
    args = ap.parse_args()

    root = Path(args.deployments_dir)
    if not root.is_dir():
        print(f"✗ 找不到部署目錄:{root}")
        return 1

    reqs = sorted(
        p for p in root.rglob("*.yaml")
        if "/sig/" not in p.as_posix()
    )
    errors: list[str] = []

    def err(f: Path, control: str, msg: str) -> None:
        errors.append(f"  ❌ {f} [{control}]:{msg}")

    checked = 0
    for f in reqs:
        try:
            req = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            err(f, "結構", f"YAML 解析失敗:{exc}")
            continue
        if req.get("kind") != "DeploymentRequest":
            continue  # 只驗 DeploymentRequest
        checked += 1
        meta = req.get("metadata", {}) or {}

        # 1. changeType(缺 = standard)
        change_type = meta.get("changeType", "standard")
        if change_type not in CHANGE_TYPES:
            err(f, "ISO 27001 A.8.32",
                f"changeType={change_type!r} 非法(應為 {sorted(CHANGE_TYPES)})")

        # 2. priority
        priority = meta.get("priority")
        if priority is not None and not PRIORITY_RE.match(str(priority)):
            err(f, "ISO 20000 變更管理", f"priority={priority!r} 非法(應為 P1..P4)")

        # 3. emergency / retroactive ⇒ justification
        if change_type in NEEDS_JUSTIFICATION:
            if not str(meta.get("justification", "") or "").strip():
                err(f, "ISO 27001 A.8.32",
                    f"changeType={change_type} 必須附 justification(例外要有理由)")

        # 3b. emergency ⇒ 必須先承諾 PIR(owner + dueBy)——「先做後審」的事後審不可賴帳(TASK-E2)
        if change_type in NEEDS_PIR:
            pir = meta.get("pir")
            if not isinstance(pir, dict):
                err(f, "ISO 27001 A.8.32 / A.5.36",
                    "emergency 必須附 pir{owner, dueBy}(承諾事後回顧的負責人與到期日)")
            else:
                if not str(pir.get("owner", "") or "").strip():
                    err(f, "ISO 27001 A.5.36", "emergency 的 pir 缺 owner(PIR 負責人)")
                due = str(pir.get("dueBy", "") or "")
                if not DATE_RE.match(due):
                    err(f, "ISO 27001 A.5.36",
                        f"emergency 的 pir.dueBy 須為 YYYY-MM-DD(目前:{due!r})")

        # 4. expedite(插單)需 by + reason
        expedite = meta.get("expedite")
        if expedite is not None:
            if not isinstance(expedite, dict) or not str(expedite.get("by", "") or "").strip() \
                    or not str(expedite.get("reason", "") or "").strip():
                err(f, "ISO 27001 A.5.3",
                    "expedite(插單)必須同時有 by 與 reason(誰批 + 為何加急)")

        # 5. ★ 繞過旗標守衛:任一 changeType 都不可關閉安全閘門
        for key_path in walk_keys(req):
            leaf = key_path.split(".")[-1]
            if BYPASS_RE.search(leaf):
                err(f, "ISO 27001 A.8.28 完整性",
                    f"偵測到繞過旗標 {key_path!r}——簽章/掃描/驗章不可因 changeType 關閉。")

    print(f"🔍 變更分類驗證:共 {checked} 個 DeploymentRequest")
    if errors:
        print("\n".join(errors))
        print(f"\n✗ 變更分類驗證失敗:{len(errors)} 項不合規(fail-closed)")
        return 1
    print("✅ 變更分類驗證通過:分類合法、例外附理由、插單留痕、無繞過旗標。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
