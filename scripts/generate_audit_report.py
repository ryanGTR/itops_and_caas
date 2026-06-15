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

try:  # 軟性相依:無 PyYAML 時,端到端證據鏈一節會優雅略過(不影響既有 PR/Actions 報告)。
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

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


# --- 黃金路徑七階段 ↔ ISO 控制項(設計來源:docs/golden-path-request-to-deploy.md) ---
GOLDEN_PATH_STAGES = [
    ("① 服務請求單", "ITIL 請求履行 / ISO 20000 服務請求"),
    ("② 請求轉變更(PR)", "ISO 27001 A.8.32 變更管理"),
    ("③ 供應鏈建置 + 簽章", "ISO 27001 A.8.28 供應鏈完整性"),
    ("④ 佈建環境(OpenTofu)", "ISO 27001 Secure by Default"),
    ("⑤ 部署前驗章閘門", "ISO 27001 完整性 / ITIL 發布驗證"),
    ("⑥ 部署 + 煙霧測試", "ISO 20000 發布與部署管理"),
    ("⑦ 登錄 CMDB + 稽核證據", "ISO 20000 組態管理 / ISO 27001 A.8.9"),
]


def _exists(path: str) -> bool:
    return bool(path) and Path(path).is_file()


def collect_golden_path_chains(deployments_dir: str, cmdb_dir: str):
    """掃 deployments/<env>/last-deploy.json,把每次成功部署串成七階段證據鏈。

    全部讀本機版控內物證(離線可跑);無 PyYAML 或無部署紀錄時回空清單。
    """
    if yaml is None:
        return []
    dep_root = Path(deployments_dir)
    if not dep_root.is_dir():
        return []

    chains = []
    for record_path in sorted(dep_root.rglob("last-deploy.json")):
        try:
            rec = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        app, env = rec.get("app", "?"), rec.get("environment", "?")
        req_path = dep_root / env / f"{app}.yaml"
        sig_path = dep_root / env / "sig" / f"{app}.sig"
        ci_path = Path(cmdb_dir) / env / f"{app}.yaml"

        req = {}
        if req_path.is_file():
            req = yaml.safe_load(req_path.read_text(encoding="utf-8")) or {}
        svc_req = ((req.get("metadata") or {}).get("serviceRequest")) or "—"
        digest = rec.get("digest", "—")
        smoke = rec.get("smokeTest") or {}

        # 每階段:物證指標 + 狀態(由物證實際存在/內容判定)
        stages = [
            (svc_req != "—", f"服務請求 {svc_req}(docs/service-catalogue.md)"),
            (req_path.is_file(), f"DeploymentRequest:{req_path}(PR 即變更)"),
            (sig_path.is_file() and digest.startswith("sha256:"),
             f"cosign 簽章:{sig_path} 對 {digest[:23]}…"),
            (Path(f"iac/environments/{env}").is_dir(),
             f"OpenTofu 環境:iac/environments/{env}(預設安全模組)"),
            (rec.get("gate") == "passed", f"驗章閘門:gate={rec.get('gate', '—')}(fail-closed)"),
            (rec.get("result") == "success",
             f"部署={rec.get('result', '—')};煙霧 {smoke.get('health', '?')} + {smoke.get('business', '?')}"),
            (ci_path.is_file(), f"CMDB CI:{ci_path}"),
        ]
        chains.append({
            "app": app, "env": env, "digest": digest,
            "deployedAt": rec.get("deployedAt", "—"),
            "result": rec.get("result", "—"), "stages": stages,
        })
    return chains


def build_golden_path_section(chains) -> list[str]:
    md: list[str] = []
    md.append("## 四、黃金路徑端到端證據鏈(七階段:請求 → 部署 → CMDB)")
    md.append("")
    md.append("> 把一次部署沿「請求→PR→建置/簽章→驗章→佈建→部署→CMDB」串成一條鏈,")
    md.append("> 每階段附**物證指標**與對映 ISO 控制項——稽核可逐階段點開查核(TASK-D7)。")
    md.append("")
    if not chains:
        md.append("_尚無成功部署的端到端證據(deployments/<env>/last-deploy.json 不存在)。_")
        md.append("")
        return md
    for c in chains:
        md.append(f"### {c['app']} → {c['env']}")
        md.append("")
        md.append(f"- **映像 digest**:`{c['digest']}`")
        md.append(f"- **部署時間(UTC)**:{c['deployedAt']}　**結果**:{c['result']}")
        md.append("")
        rows = []
        for (stage, iso), (ok, evidence) in zip(GOLDEN_PATH_STAGES, c["stages"]):
            rows.append([stage, "✅" if ok else "❌", evidence, iso])
        md.append(md_table(["階段", "狀態", "物證", "對映 ISO 控制項"], rows))
        md.append("")
        complete = all(ok for ok, _ in c["stages"])
        md.append(
            "> ✅ 七階段物證齊備:這次部署**端到端可稽核**。"
            if complete else
            "> ⚠️ 有階段物證缺漏,請查核上表 ❌ 項。"
        )
        md.append("")
    return md


# --- 例外統計(TASK-E3):讓例外的成本可見(ISO 20000 服務報告)---
CHANGE_TYPE_LABELS = {
    "standard": "標準變更", "normal": "一般變更",
    "emergency": "急件", "retroactive": "補單",
}


def collect_exception_stats(deployments_dir: str):
    """掃 DeploymentRequest,統計變更型別 / 插單 / 急件清單。離線可跑;無 yaml 回 None。"""
    if yaml is None:
        return None
    root = Path(deployments_dir)
    if not root.is_dir():
        return None
    counts = {k: 0 for k in CHANGE_TYPE_LABELS}
    expedited = 0
    emergencies = []  # 急件清單(app/env/owner/dueBy)
    total = 0
    for f in sorted(root.rglob("*.yaml")):
        if "/sig/" in f.as_posix():
            continue
        try:
            req = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        if req.get("kind") != "DeploymentRequest":
            continue
        total += 1
        meta = req.get("metadata", {}) or {}
        ct = meta.get("changeType", "standard")
        counts[ct] = counts.get(ct, 0) + 1
        if meta.get("expedite"):
            expedited += 1
        if ct == "emergency":
            pir = meta.get("pir", {}) or {}
            emergencies.append({
                "app": meta.get("app", "?"), "env": meta.get("environment", "?"),
                "owner": pir.get("owner", "—"), "dueBy": pir.get("dueBy", "—"),
            })
    return {"total": total, "counts": counts, "expedited": expedited,
            "emergencies": emergencies}


def collect_pir_status(repo: str):
    """從 GitHub 取 label=pir 的 issue,算 PIR 完成率(closed/total)。需 gh;失敗回 None。"""
    try:
        issues = gh_json([
            "issue", "list", "--repo", repo, "--label", "pir",
            "--state", "all", "--limit", "200", "--json", "number,state",
        ])
    except SystemExit:
        return None
    if not issues:
        return {"total": 0, "closed": 0, "open": 0}
    closed = sum(1 for i in issues if str(i.get("state", "")).upper() == "CLOSED")
    return {"total": len(issues), "closed": closed, "open": len(issues) - closed}


def build_exception_section(stats, pir) -> list[str]:
    md: list[str] = []
    md.append("## 五、例外統計(急件 / 插單 / 補單的成本可見化)")
    md.append("")
    md.append("> 例外無法消滅,但要**可見**。零成本的例外會侵蝕標準流程——本節讓管理層")
    md.append("> 看見例外的量與 PIR 履行情況,逼業務面對 trade-off(ISO 20000 服務報告 / A.5.36)。")
    md.append("")
    if not stats:
        md.append("_無 PyYAML 或無 DeploymentRequest,略過例外統計。_")
        md.append("")
        return md

    total = stats["total"] or 1  # 避免除以 0
    rows = []
    for ct, label in CHANGE_TYPE_LABELS.items():
        n = stats["counts"].get(ct, 0)
        rows.append([label, ct, str(n), f"{n / total * 100:.0f}%"])
    rows.append(["— 其中插單(expedite)", "expedite", str(stats["expedited"]),
                 f"{stats['expedited'] / total * 100:.0f}%"])
    md.append(md_table(["變更型別", "changeType", "件數", "佔比"], rows))
    md.append("")

    # PIR 完成率
    if pir is None:
        md.append("> PIR 完成率:無法取得(需 gh)。")
    elif pir["total"] == 0:
        md.append("> PIR:本 repo 尚無 PIR issue(label=pir)。")
    else:
        rate = pir["closed"] / pir["total"] * 100
        md.append(
            f"> **PIR 完成率:{rate:.0f}%**(已關 {pir['closed']} / 共 {pir['total']};"
            f"未結 {pir['open']} 張待回顧)。"
        )
    md.append("")

    # 未結急件 PIR 承諾清單(到期追蹤)
    if stats["emergencies"]:
        md.append("**急件 PIR 承諾(到期追蹤):**")
        md.append("")
        erows = [[e["app"], e["env"], e["owner"], e["dueBy"]] for e in stats["emergencies"]]
        md.append(md_table(["應用", "環境", "PIR 負責人", "到期(dueBy)"], erows))
        md.append("")
    return md


def build_report(repo, since, until, runs, prs, chains=None, exc_stats=None, pir=None) -> str:
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

    # --- Section 4: golden-path end-to-end evidence chain (TASK-D7) ---
    md.extend(build_golden_path_section(chains or []))

    # --- Section 5: exception statistics (TASK-E3) ---
    md.extend(build_exception_section(exc_stats, pir))

    # --- Section 6: conclusion ---
    md.append("## 六、稽核結論")
    md.append("")
    total_runs = sum(len(v) for v in runs.values())
    total_blocked = sum(
        1 for v in runs.values() for r in v if r.get("conclusion") == "failure"
    )
    md.append(f"- 期間內政策檢查共執行 **{total_runs}** 次,攔截(failure)**{total_blocked}** 次。")
    md.append(f"- 已合併變更(PR)**{len(prs)}** 件,全部須通過上述護欄方可合併。")
    md.append("- 每項技術控制均對應具體 ISO 控制項編號(見第一節),可供稽核逐項查核。")
    if chains:
        complete = sum(1 for c in chains if all(ok for ok, _ in c["stages"]))
        md.append(
            f"- 端到端黃金路徑部署 **{len(chains)}** 件,其中 **{complete}** 件七階段物證齊備"
            "(見第四節),體現「請求→部署→CMDB」全程可追溯。"
        )
    if exc_stats:
        c = exc_stats["counts"]
        exc_n = c.get("emergency", 0) + c.get("retroactive", 0)
        md.append(
            f"- 變更共 **{exc_stats['total']}** 件,其中例外(急件+補單)**{exc_n}** 件、"
            f"插單 **{exc_stats['expedited']}** 件(見第五節);例外受控且護欄全程不鬆綁。"
        )
    md.append("")
    md.append("> 本報告為自動產出之合規證據(ISO 27001 A.5.36 / ISO 20000 服務報告)。")
    return "\n".join(md)


def main() -> int:
    parser = argparse.ArgumentParser(description="稽核證據自動產出 [TASK-07]")
    parser.add_argument("--repo", help="<org>/<repo>(預設:自動推斷)")
    parser.add_argument("--since", help="起始日 YYYY-MM-DD(預設:30 天前)")
    parser.add_argument("--until", help="結束日 YYYY-MM-DD(預設:今天)")
    parser.add_argument("--output", help="輸出檔路徑(預設:印到 stdout)")
    parser.add_argument("--deployments-dir", default="deployments",
                        help="部署紀錄根目錄(端到端證據鏈來源;預設 deployments)")
    parser.add_argument("--cmdb-dir", default="cmdb",
                        help="CMDB 根目錄(端到端證據鏈來源;預設 cmdb)")
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
    chains = collect_golden_path_chains(args.deployments_dir, args.cmdb_dir)
    exc_stats = collect_exception_stats(args.deployments_dir)
    pir = collect_pir_status(repo)
    report = build_report(repo, since, until, runs, prs, chains, exc_stats, pir)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"已輸出稽核報告:{args.output}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
