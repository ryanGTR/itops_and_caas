#!/usr/bin/env python3
"""急件 PIR 開單器 (TASK-E2)。

急件(changeType: emergency)走「先做後審」——本腳本負責「後審」那一半的觸發:
把一個 emergency DeploymentRequest 轉成一張 PIR(部署後回顧)issue,帶承諾的
owner 與到期日(dueBy)。由 .github/workflows/emergency-pir.yml 於急件合併進 main 後
自動呼叫;也可手動補開。

非 emergency 的請求 → 直接略過(no-op),不開 PIR。

對應治理控制項:ISO 27001 A.8.32(緊急變更)、A.5.36(事後合規審查)。

用法:
  open_pir.py --request deployments/<env>/<app>.yaml [--commit <sha>] [--create]
    預設 dry-run:只印 PIR 標題 + 內文(可在 CI/本機檢視、可測)。
    --create:用 gh issue create 真的開 issue(需 gh 已登入、issues:write)。
Exit code:0 正常(含 no-op);2 輸入錯誤。
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("✗ 需要 PyYAML(pip install pyyaml)")


def build_pir(req: dict, commit: str) -> tuple[str, str]:
    """從 emergency DeploymentRequest 組出 PIR 的 (title, body)。"""
    meta = req.get("metadata", {}) or {}
    spec = req.get("spec", {}) or {}
    source = spec.get("source", {}) or {}
    pir = meta.get("pir", {}) or {}
    app, env = meta.get("app", "?"), meta.get("environment", "?")
    digest = source.get("digest", "?")
    git_commit = commit or source.get("gitCommit", "?")
    title = f"[PIR] {app} @ {env} — 急件事後回顧"
    body = f"""> 自動產出(TASK-E2):此急件走「先做後審」,本 PIR 是強制的事後審查。
> 對應 ISO 27001 A.8.32 緊急變更 / A.5.36 事後合規審查。

## 關聯部署
- **應用 / 環境**:`{app}` @ `{env}`
- **image digest**:`{digest}`
- **源碼 commit**:`{git_commit}`
- **服務請求**:{meta.get('serviceRequest', '—')}
- **請求者**:{meta.get('requestedBy', '—')}

## 急件理由(justification)
{meta.get('justification', '—')}

## PIR 承諾
- **負責人(owner)**:{pir.get('owner', '—')}
- **到期(dueBy)**:{pir.get('dueBy', '—')}

## 待回顧者填寫
- [ ] 做了什麼變更
- [ ] 影響與風險
- [ ] 根因(為何需要急件)
- [ ] 後續矯正措施(讓下次不必再走急件)
- [ ] 安全閘門確認(簽章/掃描/驗章仍全過——急件不鬆綁護欄)
"""
    return title, body


def main() -> int:
    ap = argparse.ArgumentParser(description="急件 PIR 開單器 [TASK-E2]")
    ap.add_argument("--request", required=True, help="DeploymentRequest YAML")
    ap.add_argument("--commit", default="", help="觸發此次部署的 commit SHA(可選)")
    ap.add_argument("--create", action="store_true", help="真的開 issue(預設 dry-run)")
    ap.add_argument("--repo", default="", help="<org>/<repo>(--create 用;預設由 gh 推斷)")
    args = ap.parse_args()

    p = Path(args.request)
    if not p.is_file():
        print(f"✗ 找不到 DeploymentRequest:{p}", file=sys.stderr)
        return 2
    req = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if req.get("kind") != "DeploymentRequest":
        print(f"↷ 略過(非 DeploymentRequest):{p}")
        return 0

    change_type = (req.get("metadata", {}) or {}).get("changeType", "standard")
    if change_type != "emergency":
        print(f"↷ 略過(changeType={change_type},非 emergency,不需 PIR):{p}")
        return 0

    title, body = build_pir(req, args.commit)

    if not args.create:
        print("=== DRY-RUN PIR(未開 issue;加 --create 才真開)===")
        print(f"TITLE: {title}\n")
        print(body)
        return 0

    cmd = ["gh", "issue", "create", "--title", title, "--body", body,
           "--label", "pir", "--label", "emergency"]
    if args.repo:
        cmd += ["--repo", args.repo]
    try:
        out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
    except FileNotFoundError:
        print("✗ 找不到 gh CLI", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        print(f"✗ gh issue create 失敗:{exc.stderr.strip()}", file=sys.stderr)
        return 2
    print(f"✅ 已開 PIR issue:{out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
