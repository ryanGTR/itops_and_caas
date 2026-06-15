#!/usr/bin/env python3
"""漂移偵測 / 對帳 (TASK-E4)。

把「CMDB 記的期望態」與「線上實際跑的態」對帳,主動抓出**沒走流程的變更**(補單):
有人手動改了線上、或塞了來路不明的映像、或把實例移掉——CMDB 與真相一漂移就被偵測。

對帳邏輯(每個 CMDB CI):
  期望 = CI.spec.source.digest;實例 = CI.spec.runtime.instance(容器名)
  實際 = 線上該實例正在跑的 image digest
    ├─ 實例不存在        → 漂移(expected running but missing:被移除/未部署/補單沒登錄)
    ├─ 實際 digest ≠ 期望 → 漂移(out-of-band:跑的不是 CMDB 記的那個)
    └─ 相符              → OK

實際態來源(可換,利於測試與正式環境對映):
  - 預設:`podman inspect <instance>`(PoC 本機)。
  - --observed-file <json>:{instance: "sha256:..."|null},供 self-test / 離線 / 正式環境
    以監控或 registry 匯出的實際態餵入。

漂移處置:預設僅報告並 exit 1(fail);--open-issue 則對每筆漂移開 GitHub issue 留痕。

對應治理控制項:ISO 27001 A.8.9 組態管理、A.5.36 合規審查;ISO 20000 組態管理。

用法:
  reconcile.py [--cmdb-dir cmdb] [--observed-file state.json] [--open-issue] [--repo o/r]
Exit code:0 無漂移;1 偵測到漂移(或讀取錯誤)。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("✗ 需要 PyYAML(pip install pyyaml)")


def podman_digest(instance: str) -> str | None:
    """線上實際 running image digest;實例不存在回 None。"""
    try:
        out = subprocess.run(
            ["podman", "inspect", instance, "--format", "{{.Image}}"],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        sys.exit("✗ 找不到 podman(或改用 --observed-file)")
    if out.returncode != 0:
        return None  # 實例不存在
    img = out.stdout.strip()
    return img if img.startswith("sha256:") else f"sha256:{img}"


def open_issue(repo: str, title: str, body: str) -> None:
    cmd = ["gh", "issue", "create", "--title", title, "--body", body,
           "--label", "drift"]
    if repo:
        cmd += ["--repo", repo]
    try:
        out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
        print(f"   → 已開漂移 issue:{out}")
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(f"   ⚠️ 開 issue 失敗:{exc}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description="漂移偵測 / 對帳 [TASK-E4]")
    ap.add_argument("--cmdb-dir", default="cmdb")
    ap.add_argument("--observed-file", help="實際態 JSON {instance: digest|null}(預設用 podman)")
    ap.add_argument("--open-issue", action="store_true", help="對每筆漂移開 GitHub issue")
    ap.add_argument("--repo", default="", help="<org>/<repo>(--open-issue 用)")
    args = ap.parse_args()

    root = Path(args.cmdb_dir)
    if not root.is_dir():
        print(f"✗ 找不到 CMDB 目錄:{root}")
        return 1

    observed = None
    if args.observed_file:
        observed = json.loads(Path(args.observed_file).read_text(encoding="utf-8"))

    cis = sorted(root.rglob("*.yaml"))
    drifts = []
    print(f"🔍 漂移對帳:CMDB 期望態 vs 線上實際態(共 {len(cis)} 個 CI)")
    for f in cis:
        ci = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        if ci.get("kind") != "ConfigurationItem":
            continue
        spec = ci.get("spec", {}) or {}
        expected = str((spec.get("source", {}) or {}).get("digest", "") or "")
        rt = spec.get("runtime", {}) or {}
        instance = rt.get("instance", "")
        app = (ci.get("metadata", {}) or {}).get("app", instance)

        actual = observed.get(instance) if observed is not None else podman_digest(instance)

        if actual is None:
            reason = f"實例 `{instance}` 不在線上(期望在跑 {expected[:23]}…)——被移除 / 未部署 / 補單未登錄。"
            drifts.append((app, instance, reason))
            print(f"  ❌ DRIFT  {app}:{reason}")
        elif actual != expected:
            reason = f"線上 `{instance}` 跑的是 {actual[:23]}…,≠ CMDB 期望 {expected[:23]}…——out-of-band 變更。"
            drifts.append((app, instance, reason))
            print(f"  ❌ DRIFT  {app}:{reason}")
        else:
            print(f"  ✅ OK     {app}:線上 == CMDB 期望({expected[:23]}…)")

    if not drifts:
        print("✅ 無漂移:CMDB 與線上一致。")
        return 0

    print(f"\n✗ 偵測到 {len(drifts)} 筆漂移(沒走流程的變更)。")
    if args.open_issue:
        for app, instance, reason in drifts:
            open_issue(
                args.repo,
                f"[DRIFT] {app} — CMDB 與線上不一致",
                f"漂移對帳偵測到未授權 / 未登錄變更(TASK-E4)。\n\n"
                f"- 實例:`{instance}`\n- 原因:{reason}\n\n"
                f"請依「補單≠漂白」處理:(a) 補登 retroactive 變更 + PIR;"
                f"(b) root cause 為何繞得過流程。對應 ISO 27001 A.8.9 / A.5.36。",
            )
    return 1


if __name__ == "__main__":
    sys.exit(main())
