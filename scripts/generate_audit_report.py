#!/usr/bin/env python3
"""Audit evidence generator ([TASK-07]).

Translates the platform's technical records (GitHub PRs, approvers, and
policy-check runs) into an auditor-readable compliance report, mapping each
technical control to its ISO control number (the "translation layer" that is
this platform's core value to the bank).

Each policy is mapped to ISO controls per COMPLIANCE_MAP.md.

Governance controls implemented here:
  - ISO 27001 A.5.36  Compliance review (automated evidence)
  - ISO 20000         Service reporting

Data source: the `gh` CLI (must be installed and authenticated; read access is
enough). On GitHub Actions the built-in GITHUB_TOKEN is sufficient.

Usage:
    python3 scripts/generate_audit_report.py \\
        [--repo <org>/<repo>] [--since YYYY-MM-DD] [--until YYYY-MM-DD] \\
        [--output <path.md>]

If --repo is omitted it is inferred from the current repo. If --since is
omitted it defaults to 30 days ago.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

# --- Policy -> ISO control mapping (source of truth: COMPLIANCE_MAP.md) ----
# Keyed by the workflow name as it appears in GitHub Actions.
POLICY_CONTROLS = {
    "policy-secrets": {
        "label": "機敏資訊掃描",
        "iso": ["ISO 27001 A.8.12", "ISO 27001 A.5.17"],
        "task": "TASK-03",
    },
    "policy-structure": {
        "label": "結構與命名規範",
        "iso": ["ISO 27001 A.5.37"],
        "task": "TASK-04",
    },
}

# Cross-cutting controls reflected by the PR-based change-management process.
CHANGE_MGMT_CONTROLS = ["ISO 20000 變更管理", "ISO 27001 A.8.32"]
SOD_CONTROLS = ["ISO 27001 A.5.3", "ISO 27001 A.8.4"]


def gh_json(args: list[str]):
    """Run a `gh` command that emits JSON and return the parsed result."""
    try:
        out = subprocess.run(
            ["gh", *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except FileNotFoundError:
        sys.exit("錯誤:找不到 gh CLI。請先安裝並登入 gh。")
    except subprocess.CalledProcessError as exc:
        sys.exit(f"錯誤:gh 指令失敗:{exc.stderr.strip()}")
    return json.loads(out) if out.strip() else []


def infer_repo() -> str:
    data = gh_json(["repo", "view", "--json", "nameWithOwner"])
    return data["nameWithOwner"]


def parse_ts(value: str) -> dt.datetime:
    """Parse a GitHub ISO-8601 timestamp into an aware datetime (UTC)."""
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def collect_runs(repo: str, since: dt.datetime, until: dt.datetime):
    """Collect policy-check workflow runs in the period, grouped by policy."""
    runs = gh_json([
        "run", "list", "--repo", repo, "--limit", "200",
        "--json", "name,conclusion,status,createdAt,event,headBranch,databaseId",
    ])
    grouped: dict[str, list[dict]] = {k: [] for k in POLICY_CONTROLS}
    for run in runs:
        name = run.get("name")
        if name not in POLICY_CONTROLS:
            continue
        created = parse_ts(run["createdAt"])
        if since <= created <= until:
            grouped[name].append(run)
    return grouped


def collect_merged_prs(repo: str, since: dt.datetime):
    """Collect merged PRs since the given date, with approvers and checks."""
    search = f"merged:>={since.date().isoformat()}"
    prs = gh_json([
        "pr", "list", "--repo", repo, "--state", "merged",
        "--search", search, "--limit", "100",
        "--json", "number,title,author,mergedAt,reviews,statusCheckRollup",
    ])
    result = []
    for pr in prs:
        approvers = sorted({
            r["author"]["login"]
            for r in pr.get("reviews", [])
            if r.get("state") == "APPROVED" and r.get("author")
        })
        checks = {
            c.get("name"): c.get("conclusion")
            for c in (pr.get("statusCheckRollup") or [])
            if c.get("name")
        }
        result.append({
            "number": pr["number"],
            "title": pr["title"],
            "author": (pr.get("author") or {}).get("login", "?"),
            "mergedAt": pr.get("mergedAt", ""),
            "approvers": approvers,
            "checks": checks,
        })
    return result


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    line = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows)
    return "\n".join([line, sep, body]) if rows else line + "\n" + sep + "\n| (無資料) |"


def build_report(repo, since, until, runs, prs) -> str:
    md: list[str] = []
    md.append("# 稽核證據報告(Audit Evidence Report)")
    md.append("")
    md.append("> 自動產出 — 由 GitHub 技術紀錄翻譯為對應 ISO 控制項的合規證據。")
    md.append("> 對應控制:ISO 27001 A.5.36 合規審查、ISO 20000 服務報告。")
    md.append("")
    md.append(f"- **儲存庫**:`{repo}`")
    md.append(f"- **期間**:{since.date()} ~ {until.date()}")
    md.append(f"- **產出時間(UTC)**:{until.isoformat(timespec='seconds')}")
    md.append("")

    # --- Section 1: policy -> ISO mapping ---
    md.append("## 一、政策護欄 ↔ ISO 控制項對照")
    md.append("")
    rows = [
        [meta["task"], meta["label"], pol, ", ".join(meta["iso"])]
        for pol, meta in POLICY_CONTROLS.items()
    ]
    rows.append(["TASK-06", "PR 流程變更管理", "branch protection", ", ".join(CHANGE_MGMT_CONTROLS)])
    rows.append(["TASK-05", "職責分離 (SoD)", "CODEOWNERS", ", ".join(SOD_CONTROLS)])
    md.append(md_table(["任務", "技術控制", "載體", "對應 ISO 控制項"], rows))
    md.append("")

    # --- Section 2: policy-check execution summary ---
    md.append("## 二、政策檢查執行統計(護欄覆蓋證據)")
    md.append("")
    md.append("> 證明「期間內變更都經過合規檢查」,並列出通過率與攔截(failure)紀錄。")
    md.append("")
    rows = []
    for pol, meta in POLICY_CONTROLS.items():
        items = runs.get(pol, [])
        total = len(items)
        passed = sum(1 for r in items if r.get("conclusion") == "success")
        blocked = sum(1 for r in items if r.get("conclusion") == "failure")
        other = total - passed - blocked
        rate = f"{(passed / total * 100):.0f}%" if total else "—"
        rows.append([
            meta["label"], pol, str(total), str(passed),
            str(blocked), str(other), rate, ", ".join(meta["iso"]),
        ])
    md.append(md_table(
        ["技術控制", "workflow", "執行次數", "通過", "攔截(fail)", "其他", "通過率", "ISO 控制項"],
        rows,
    ))
    md.append("")

    # --- Section 3: change (PR) detail ---
    md.append("## 三、變更(PR)明細 — 誰改的/誰核准的/檢查結果")
    md.append("")
    md.append("> 每個合併都可追溯:變更者、核准者、政策檢查結果(ISO 20000 / A.8.32)。")
    md.append("")
    if prs:
        rows = []
        for pr in prs:
            checks = "; ".join(f"{k}={v}" for k, v in pr["checks"].items()) or "—"
            approvers = ", ".join(pr["approvers"]) or "(0,SOLO 模式)"
            rows.append([
                f"#{pr['number']}", pr["title"][:40], pr["author"],
                pr["mergedAt"][:10], approvers, checks,
            ])
        md.append(md_table(
            ["PR", "標題", "變更者", "合併日", "核准者", "檢查結果"], rows,
        ))
    else:
        md.append("_期間內無已合併的 PR。_")
        md.append("")
        md.append("> 註:branch protection 啟用前的提交為直接 push;啟用後所有變更")
        md.append("> 均須經 PR。後續報告此區將累積完整的「誰改/誰核准」證據。")
    md.append("")

    # --- Section 4: conclusion ---
    md.append("## 四、稽核結論")
    md.append("")
    total_runs = sum(len(v) for v in runs.values())
    total_blocked = sum(
        1 for v in runs.values() for r in v if r.get("conclusion") == "failure"
    )
    md.append(f"- 期間內政策檢查共執行 **{total_runs}** 次,攔截(failure)**{total_blocked}** 次。")
    md.append(f"- 已合併變更(PR)**{len(prs)}** 件,全部須通過上述護欄方可合併。")
    md.append("- 每項技術控制均對應具體 ISO 控制項編號(見第一節),可供稽核逐項查核。")
    md.append("")
    md.append("> 本報告為自動產出之合規證據(ISO 27001 A.5.36 / ISO 20000 服務報告)。")
    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="稽核證據自動產出 [TASK-07]")
    parser.add_argument("--repo", help="<org>/<repo>(預設:自動推斷)")
    parser.add_argument("--since", help="起始日 YYYY-MM-DD(預設:30 天前)")
    parser.add_argument("--until", help="結束日 YYYY-MM-DD(預設:今天)")
    parser.add_argument("--output", help="輸出檔路徑(預設:印到 stdout)")
    args = parser.parse_args()

    now = dt.datetime.now(dt.timezone.utc)
    until = (
        parse_ts(args.until + "T23:59:59+00:00") if args.until else now
    )
    since = (
        parse_ts(args.since + "T00:00:00+00:00")
        if args.since
        else now - dt.timedelta(days=30)
    )
    repo = args.repo or infer_repo()

    runs = collect_runs(repo, since, until)
    prs = collect_merged_prs(repo, since)
    report = build_report(repo, since, until, runs, prs)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"已輸出稽核報告:{args.output}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
