#!/usr/bin/env python3
"""分級→控制矩陣閘門 — 讓 dataClassification 從裝飾變成「會驅動、被強制」的 policy 輸入。

ISMS 風險為本的核心:控制強度要與資料風險(分級)相稱。本閘門讀
policies/classification-matrix.yaml(治理端擁有的政策),對每個 DeploymentRequest:
  分級要求的控制(核可數 + 加密 + 網路 + 漏洞掃描…),有沒有在 spec.controls 裡被滿足?
缺 → 擋(enforce 模式 exit 1)。這就是「翻一個分級標籤,系統當場改變要求」的 demo 核心,
也把 docs/framework-conformance-assessment.md 第 2.2 條(分級沒驅動控制=名目)做成真的。

漸進收緊:--mode observe 只報不擋(exit 0,先收集衝擊);--mode enforce fail-closed。
證據:--evidence-out 寫一份稽核級「分級合規」記錄(把工程證據翻成公文/regulator 認的當責)。

對應:ISO 27001 風險為本 / A.8.24 加密 / A.8.20 網路 / A.8.8 漏洞 / A.5.3 SoD。

用法:
  validate_classification_controls.py [--deployments-dir deployments]
      [--matrix policies/classification-matrix.yaml] [--mode enforce|observe]
      [--evidence-out path.md]
Exit:0 全通過(或 observe);1 enforce 下有不合規。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("✗ 需要 PyYAML(pip install pyyaml)")

# 控制名 → 人類可讀(報表/證據用)
CONTROL_LABEL = {
    "encryptionInTransit": "傳輸加密",
    "encryptionAtRest": "靜態加密",
    "networkRestricted": "網路不對外暴露",
    "vulnScanClean": "漏洞掃描零 HIGH/CRITICAL",
}


def load_yaml(p: Path) -> dict:
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        print(f"✗ 無法解析 {p}:{exc}")
        return {}


def control_satisfied(name: str, controls: dict) -> tuple[bool, str]:
    """回 (是否滿足, 實際值描述)。"""
    if name == "vulnScanClean":
        vs = controls.get("vulnScan", {}) or {}
        try:
            high, crit = int(vs.get("high", 1)), int(vs.get("critical", 1))
        except (TypeError, ValueError):
            return False, "vulnScan 數值非法"
        return (high == 0 and crit == 0), f"high={vs.get('high')},critical={vs.get('critical')}"
    val = controls.get(name)
    return (val is True), f"{name}={val!r}"


def evaluate(req: dict, matrix: dict) -> dict:
    """回單筆評估結果:{env, cls, ok, checks:[(label, ok, detail)], missing:[...]}"""
    meta = req.get("metadata", {}) or {}
    spec = req.get("spec", {}) or {}
    cls = spec.get("dataClassification", "internal")
    controls = spec.get("controls", {}) or {}
    rule = matrix.get("classifications", {}).get(cls)
    checks, missing = [], []

    if rule is None:
        return {"env": meta.get("environment"), "cls": cls, "ok": False,
                "checks": [], "missing": [f"分級 {cls!r} 不在矩陣內"]}

    # 核可數
    min_appr = int(rule.get("minApprovals", 0))
    try:
        appr = int(controls.get("approvals", 0))
    except (TypeError, ValueError):
        appr = 0
    appr_ok = appr >= min_appr
    checks.append((f"核可數 ≥ {min_appr}(SoD/CAB)", appr_ok, f"approvals={appr}"))
    if not appr_ok:
        missing.append(f"核可數不足(需 {min_appr}、現 {appr})")

    # 必要控制
    for name in rule.get("require", []):
        ok, detail = control_satisfied(name, controls)
        checks.append((CONTROL_LABEL.get(name, name), ok, detail))
        if not ok:
            missing.append(CONTROL_LABEL.get(name, name))

    return {"env": meta.get("environment"), "cls": cls,
            "ok": not missing, "checks": checks, "missing": missing}


def render_evidence(results: list[dict]) -> str:
    """稽核級『分級合規』證據記錄(公文/regulator 認得的當責物證)。"""
    lines = ["# 分級合規證據(classification compliance evidence)", "",
             "> 由 scripts/validate_classification_controls.py 依 policies/classification-matrix.yaml 產出。",
             "> 證明:每個部署的控制強度與其資料分級相稱(ISMS 風險為本),且為系統強制。", ""]
    for r in results:
        verdict = "✅ PASS" if r["ok"] else "❌ FAIL"
        lines.append(f"## {r['env']} — 分級 {r['cls']} — {verdict}")
        lines.append("| 要求控制 | 結果 | 實際 |")
        lines.append("|---|:--:|---|")
        for label, ok, detail in r["checks"]:
            lines.append(f"| {label} | {'✓' if ok else '✗'} | `{detail}` |")
        if r["missing"]:
            lines.append(f"\n> 缺:{', '.join(r['missing'])}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="分級→控制矩陣閘門(fail-closed)")
    ap.add_argument("--deployments-dir", default="deployments")
    ap.add_argument("--matrix", default="policies/classification-matrix.yaml")
    ap.add_argument("--mode", choices=["enforce", "observe"], default="enforce")
    ap.add_argument("--evidence-out", default="")
    args = ap.parse_args()

    matrix = load_yaml(Path(args.matrix))
    if not matrix.get("classifications"):
        print(f"✗ 矩陣無效:{args.matrix}")
        return 2

    root = Path(args.deployments_dir)
    reqs = sorted(p for p in root.rglob("*.yaml") if "/sig/" not in p.as_posix())
    results = []
    for f in reqs:
        req = load_yaml(f)
        if req.get("kind") != "DeploymentRequest":
            continue
        results.append(evaluate(req, matrix))

    print(f"🔍 分級→控制矩陣驗證:共 {len(results)} 個 DeploymentRequest(mode={args.mode})")
    failed = [r for r in results if not r["ok"]]
    for r in results:
        icon = "✅" if r["ok"] else ("⚠️" if args.mode == "observe" else "❌")
        print(f"  {icon} [{r['env']}] 分級={r['cls']}"
              + ("" if r["ok"] else f" → 缺:{', '.join(r['missing'])}"))

    if args.evidence_out:
        Path(args.evidence_out).write_text(render_evidence(results), encoding="utf-8")
        print(f"   📄 證據記錄已寫:{args.evidence_out}")

    if failed and args.mode == "enforce":
        print(f"\n✗ 分級控制不合規:{len(failed)} 筆(fail-closed)。"
              "高分級部署未滿足相稱控制——風險為本要求擋下。")
        return 1
    if failed:
        print(f"\n⚠️ observe 模式:{len(failed)} 筆不合規(只報不擋;enforce 會擋)。")
        return 0
    print("\n✅ 全部通過:每個部署的控制強度與其資料分級相稱(系統強制,非貼標籤)。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
