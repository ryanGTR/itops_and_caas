#!/usr/bin/env python3
"""Structure & naming policy gatekeeper ([TASK-04]).

Enforces that the repository conforms to the organization's required
structure, mandatory documents, and naming conventions. Non-conformant
changes fail this check and therefore cannot be merged (guardrail, not gate).

Each rule is annotated with the governance control it implements
(see COMPLIANCE_MAP.md). On failure, every rule prints a concrete
remediation hint so the developer knows exactly how to fix it.

Governance controls implemented here:
  - ISO 27001 A.5.37  Documented operating procedures (mandatory docs/structure)
  - ISO 27001 A.5.3   Segregation of duties (CODEOWNERS protects guardrails)
  - ISO 20000         Service management consistency

Usage:
    python3 scripts/check_structure.py [--root <repo_root>]

Exit code:
    0  all rules pass
    1  one or more rules failed
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Result:
    """Outcome of a single rule evaluation."""

    ok: bool
    rule: str
    control: str
    # Human-facing remediation hints (Chinese, shown to developers on failure).
    problems: list[str] = field(default_factory=list)


# --- Rule 1: mandatory root documents -------------------------------------
# Control: ISO 27001 A.5.37 (documented operating procedures) + ISO 20000
# (service consistency). A service without its baseline docs is non-conformant.
REQUIRED_ROOT_FILES = [
    "README.md",
    "LICENSE",
    "CLAUDE.md",
    ".gitignore",
    "CODEOWNERS",
    "PROJECT_PLAN.md",
    "STRUCTURE.md",
    "COMPLIANCE_MAP.md",
    "GOVERNANCE_BRIEF.md",
]

# --- Rule 2: mandatory directories ----------------------------------------
# Control: ISO 20000 service management consistency. The skeleton defined in
# STRUCTURE.md must be present so every project has the same shape.
REQUIRED_DIRS = [
    ".github/workflows",
    "policies",
    "scaffold",
    "scripts",
]

# --- Rule 3: mandatory guardrail workflows --------------------------------
# Control: ISO 27001 A.5.37. The policy-as-code gates must exist; a repo
# missing its guardrails is non-conformant by definition.
REQUIRED_WORKFLOWS = [
    ".github/workflows/policy-secrets.yml",
    ".github/workflows/policy-structure.yml",
]

# --- Rule 5: CODEOWNERS must protect the guardrails (SoD) ------------------
# Control: ISO 27001 A.5.3 (segregation of duties). The people who *use*
# guardrails must not be able to silently *change* them.
CODEOWNERS_PROTECTED_PATHS = [
    "/policies/",
    "/.github/workflows/",
]


def check_required_files(root: Path) -> Result:
    missing = [f for f in REQUIRED_ROOT_FILES if not (root / f).is_file()]
    problems = [
        f"缺少必要文件:{f} — 請在 repo 根目錄補上(見 STRUCTURE.md)"
        for f in missing
    ]
    return Result(not missing, "必要根目錄文件存在", "ISO 27001 A.5.37 / ISO 20000", problems)


def check_required_dirs(root: Path) -> Result:
    missing = [d for d in REQUIRED_DIRS if not (root / d).is_dir()]
    problems = [
        f"缺少必要目錄:{d}/ — 請依 STRUCTURE.md 建立"
        for d in missing
    ]
    return Result(not missing, "必要目錄結構存在", "ISO 20000 服務一致性", problems)


def check_required_workflows(root: Path) -> Result:
    missing = [w for w in REQUIRED_WORKFLOWS if not (root / w).is_file()]
    problems = [
        f"缺少護欄 workflow:{w} — 護欄不可缺席(見 TASK-03 / TASK-04)"
        for w in missing
    ]
    return Result(not missing, "護欄 workflow 存在", "ISO 27001 A.5.37", problems)


def check_workflow_naming(root: Path) -> Result:
    """Rule 4: naming convention for workflow files.

    Control: ISO 27001 A.5.37 (consistent, documented procedures).
    Convention:
      - Workflow files use the .yml extension (not .yaml) for consistency.
      - Policy guardrail workflows are named policy-<name>.yml.
    """
    wf_dir = root / ".github" / "workflows"
    problems: list[str] = []
    if wf_dir.is_dir():
        name_re = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.yml$")
        for path in sorted(wf_dir.iterdir()):
            if path.name == ".gitkeep" or not path.is_file():
                continue
            if path.suffix == ".yaml":
                problems.append(
                    f"workflow 副檔名應為 .yml 而非 .yaml:{path.name} — 請改名"
                )
                continue
            if not name_re.match(path.name):
                problems.append(
                    f"workflow 檔名不符規範(小寫 + 連字號 + .yml):{path.name}"
                )
    return Result(not problems, "workflow 命名規範", "ISO 27001 A.5.37", problems)


def check_codeowners_sod(root: Path) -> Result:
    """Rule 5: CODEOWNERS protects the guardrail paths (SoD)."""
    co = root / "CODEOWNERS"
    problems: list[str] = []
    if not co.is_file():
        problems.append("缺少 CODEOWNERS — 無法落實職責分離(SoD)")
        return Result(False, "CODEOWNERS 保護護欄路徑 (SoD)", "ISO 27001 A.5.3", problems)
    text = co.read_text(encoding="utf-8")
    for protected in CODEOWNERS_PROTECTED_PATHS:
        # The protected path must appear as an ownership rule with at least
        # one owner (an @-handle) on the same line.
        pattern = re.compile(
            rf"^\s*{re.escape(protected)}\S*\s+.*@\S+", re.MULTILINE
        )
        if not pattern.search(text):
            problems.append(
                f"CODEOWNERS 未保護 {protected} — 政策變更須指定平台+資安群組審核"
            )
    return Result(not problems, "CODEOWNERS 保護護欄路徑 (SoD)", "ISO 27001 A.5.3", problems)


CHECKS = [
    check_required_files,
    check_required_dirs,
    check_required_workflows,
    check_workflow_naming,
    check_codeowners_sod,
]


def main() -> int:
    parser = argparse.ArgumentParser(description="結構與命名規範守門員 [TASK-04]")
    parser.add_argument(
        "--root", default=".", help="repo 根目錄(預設:目前目錄)"
    )
    args = parser.parse_args()
    root = Path(args.root).resolve()

    print(f"🔍 結構檢查:{root}\n")
    results = [check(root) for check in CHECKS]

    failed = [r for r in results if not r.ok]
    for r in results:
        mark = "✅" if r.ok else "❌"
        print(f"{mark} [{r.control}] {r.rule}")
        for p in r.problems:
            print(f"      ↳ {p}")

    print()
    if failed:
        print(f"結構檢查 FAILED:{len(failed)} 項規則未通過。")
        print("請依上方「↳」修正提示處理後重新提交。")
        return 1
    print(f"結構檢查 PASSED:全部 {len(results)} 項規則通過。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
