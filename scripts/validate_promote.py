#!/usr/bin/env python3
"""過版閘門 policy-promote (TASK-F3) — fail-closed。

過版(promote)PR 是「把上一區已驗章、確認在跑的 digest 推進下一區」。
本閘門對這種 PR 強制三道守衛,任一不過即擋(exit 1):

  1. Diff 範圍守衛:過版 PR **只准動目標環境 DeploymentRequest 的 spec.source**。
     動到別的檔(程式/護欄/scripts)、動到 config/runtime/metadata、或動到別環境 →
     視為「夾帶私貨」,擋。(語意比對 base↔head,source 以外必須完全相同。)

  2. 血統 + 順序守衛:要晉級的 digest 必須**存在於「上一區」CMDB 的確認態**。
     上一區沒這個 app、digest 對不上、或目標環境無上游(如直推 sandbox/跳關)→ 擋。
     這就是「禁跳關、只能 promote 真的在上一區跑通且登錄的東西」。

  3. 重新驗章:對目標環境的請求 + 上一區 CMDB 記的簽章,重跑 D5 部署前驗章閘門
     (verify_deploy_gate.py)。build once 同一 digest,上一區對該 digest 的 cosign
     簽章對目標一樣有效;驗不過(未簽/偽造/非本平台信任根)→ 擋。

非過版 PR(沒動部署檔,或動到的不只是 source)不在本閘門管轄 → 放行(no-op),
交由 change-class / deploy-gate 等既有閘門處理。故本檢查可安全列為必過狀態檢查。

對應治理控制項:
  ISO 27001 A.8.28 完整性(只搬已驗章產物、禁夾帶);A.8.32 變更管理(順序/禁跳關);
  ISO 20000 發布驗證(每區重驗)。

用法:
  # CI(PR)模式:用 git 算出本分支相對 base 的變更
  validate_promote.py --base origin/main [--promote-pr]
  # self-test 模式:直接餵變更清單與 base 版本
  validate_promote.py --changed <path> [--changed ...] --base-dir <dir> [--promote-pr]

  共用選項:--deployments-dir --cmdb-dir --pubkey --cosign
           --order env1,env2,...(晉級順序,預設 openliberty-sandbox,test,uat,prod)

Exit code:0 放行(合規過版 / 非過版 PR);1 任一守衛不過(fail-closed);2 輸入錯誤。
"""
from __future__ import annotations

import argparse
import copy
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("✗ 需要 PyYAML(pip install pyyaml)")

import re

# 目標部署檔:deployments/<env>/<app>.yaml(sig/ 等更深層不算,動到即非 source 範圍)
TARGET_RE = re.compile(r"^deployments/([^/]+)/([^/]+)\.yaml$")
# 過版只准搬這些 source 欄位(對齊 promote.py);其餘 source 欄位也不准動。
PROMOTE_KEYS = {"artifact", "version", "digest", "gitCommit", "gitTag"}
DEFAULT_ORDER = ["openliberty-sandbox", "test", "uat", "prod"]


def run(cmd: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def git_changed_files(base: str) -> list[str]:
    """本分支相對 base(merge-base)變動的檔案清單(repo 相對 posix 路徑)。"""
    rc, mb, err = run(["git", "merge-base", base, "HEAD"])
    if rc != 0:
        sys.exit(f"✗ 無法求 merge-base({base}↔HEAD):{err.strip()}")
    merge_base = mb.strip()
    rc, out, err = run(["git", "diff", "--name-only", merge_base, "HEAD"])
    if rc != 0:
        sys.exit(f"✗ git diff 失敗:{err.strip()}")
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def git_base_text(base: str, path: str) -> str | None:
    """檔案在 merge-base 時的內容;新檔回 None。"""
    rc, mb, _ = run(["git", "merge-base", base, "HEAD"])
    ref = mb.strip() if rc == 0 else base
    rc, out, _ = run(["git", "show", f"{ref}:{path}"])
    return out if rc == 0 else None


def load_yaml(text: str | None) -> dict:
    if not text:
        return {}
    return yaml.safe_load(text) or {}


def strip_source(req: dict) -> dict:
    """回傳「拿掉 spec.source」的深複本,供語意比對(source 以外是否被動)。"""
    r = copy.deepcopy(req)
    if isinstance(r.get("spec"), dict):
        r["spec"].pop("source", None)
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="過版閘門 policy-promote [TASK-F3]")
    ap.add_argument("--base", help="git base ref(CI/PR 模式,如 origin/main)")
    ap.add_argument("--changed", action="append", default=[],
                    help="變更檔(self-test 模式,可重複)")
    ap.add_argument("--base-dir", help="self-test:存放 base 版本檔案的根目錄")
    ap.add_argument("--promote-pr", action="store_true",
                    help="本 PR 已被標記為過版 PR(branch promote/* 或 label);範圍守衛從嚴")
    ap.add_argument("--deployments-dir", default="deployments")
    ap.add_argument("--cmdb-dir", default="cmdb")
    ap.add_argument("--pubkey", default="trust/cosign.pub")
    ap.add_argument("--cosign", default="cosign")
    ap.add_argument("--order", default=",".join(DEFAULT_ORDER),
                    help="晉級順序(逗號分隔)")
    args = ap.parse_args()

    order = [e.strip() for e in args.order.split(",") if e.strip()]

    # --- 取得變更清單與各檔 base 版本 ---
    if args.base:
        changed = git_changed_files(args.base)
        def base_of(p: str) -> str | None:
            return git_base_text(args.base, p)
    elif args.changed:
        changed = list(args.changed)
        bd = Path(args.base_dir) if args.base_dir else None
        def base_of(p: str) -> str | None:
            if not bd:
                return None
            f = bd / p
            return f.read_text(encoding="utf-8") if f.is_file() else None
    else:
        print("✗ 需提供 --base(CI)或 --changed(self-test)", file=sys.stderr)
        return 2

    errors: list[str] = []

    def reject(control: str, msg: str) -> None:
        errors.append(f"  ❌ [{control}]:{msg}")

    # 分類變更:目標部署檔 vs 其他
    target_files = [p for p in changed if TARGET_RE.match(p)]
    other_files = [p for p in changed if not TARGET_RE.match(p)]

    # 判定每個目標部署檔是否「只動 source」(語意上)
    source_only: dict[str, dict] = {}   # path -> {env, app, head, base}
    impure: list[str] = []              # 動到 source 以外的目標檔
    for p in target_files:
        m = TARGET_RE.match(p)
        env, app = m.group(1), m.group(2)
        head = load_yaml(Path(p).read_text(encoding="utf-8") if Path(p).is_file() else None)
        base = load_yaml(base_of(p))
        if head.get("kind") != "DeploymentRequest":
            # 不是部署請求(理論上不會發生);當作非 source 變更
            impure.append(p)
            continue
        if not base:
            # 過版 PR 不應新增部署檔——目標環境骨架(F1)應已存在
            impure.append(p)
            continue
        non_src_changed = strip_source(base) != strip_source(head)
        b_src = (base.get("spec", {}) or {}).get("source", {}) or {}
        h_src = (head.get("spec", {}) or {}).get("source", {}) or {}
        # source 內:鍵集合不可變;只有 PROMOTE_KEYS 的值可不同
        keys_changed = set(b_src) != set(h_src)
        bad_value_change = any(
            b_src.get(k) != h_src.get(k)
            for k in set(b_src) | set(h_src)
            if k not in PROMOTE_KEYS
        )
        if non_src_changed or keys_changed or bad_value_change:
            impure.append(p)
        else:
            source_only[p] = {"env": env, "app": app, "head": head, "base": base}

    # 判定本 PR 是否為「過版 PR」
    is_promote = args.promote_pr or (
        bool(target_files) and not other_files and not impure
    )

    if not is_promote:
        # 非過版 PR:本閘門不管轄,放行(交由其他閘門)
        print("🔍 過版閘門 policy-promote")
        print("✅ 本 PR 非過版 PR(未限定於目標環境 source),policy-promote 略過放行。")
        return 0

    # === 守衛 1:Diff 範圍 ===
    if other_files:
        reject("ISO 27001 A.8.28 完整性",
               "過版 PR 夾帶了部署檔以外的變更(禁止):\n      - "
               + "\n      - ".join(other_files))
    if impure:
        reject("ISO 27001 A.8.28 完整性",
               "過版 PR 動到 spec.source 以外的內容(config/runtime/metadata/別的 source 欄位):"
               "\n      - " + "\n      - ".join(impure))
    if not source_only:
        reject("ISO 27001 A.8.32 變更管理",
               "過版 PR 未對任何目標環境 spec.source 產生變更(空過版)。")

    # 範圍不過就不必往下(避免對不可信的變更做血統/驗章)
    if errors:
        return _report(errors)

    # === 守衛 2+3:逐目標檔 血統+順序、重新驗章 ===
    for p, info in source_only.items():
        env, app, head = info["env"], info["app"], info["head"]
        new_digest = str(((head.get("spec") or {}).get("source") or {}).get("digest", "") or "")

        # 上游環境(順序前一格)
        if env not in order:
            reject("ISO 27001 A.8.32 變更管理",
                   f"{p}:目標環境 {env!r} 不在晉級順序 {order} 內。")
            continue
        idx = order.index(env)
        if idx == 0:
            reject("ISO 27001 A.8.32 變更管理",
                   f"{p}:{env!r} 無上游環境,不可被過版進入(它是產物的起點,"
                   "請走部署黃金路徑而非 promote)。")
            continue
        upstream = order[idx - 1]

        up_ci_path = Path(args.cmdb_dir) / upstream / f"{app}.yaml"
        if not up_ci_path.is_file():
            reject("ISO 27001 A.8.32 變更管理",
                   f"{p}:上一區 {upstream!r} 的 CMDB 無此 app(尚未部署登錄)——"
                   "禁跳關,只能 promote 已在上一區跑通的產物。")
            continue
        up_ci = load_yaml(up_ci_path.read_text(encoding="utf-8"))
        up_src = (up_ci.get("spec", {}) or {}).get("source", {}) or {}
        up_digest = str(up_src.get("digest", "") or "")
        if not up_digest or new_digest != up_digest:
            reject("ISO 27001 A.8.28 完整性",
                   f"{p}:要晉級的 digest 與上一區 {upstream!r} 確認態不符——"
                   f"\n      目標 digest:{new_digest}"
                   f"\n      上一區確認:{up_digest}"
                   "\n      只能 promote「上一區真的在跑、已登錄」的 digest。")
            continue

        # === 守衛 3:重新驗章(委派 D5 閘門;同 digest 用上一區的簽章)===
        sig_ref = up_src.get("signature")
        if not sig_ref or not Path(sig_ref).is_file():
            reject("ISO 27001 A.8.28 完整性",
                   f"{p}:上一區 CMDB 未記有效簽章物證(signature={sig_ref!r}),無法重驗。")
            continue
        gate = Path(__file__).resolve().parent / "verify_deploy_gate.py"
        rc, out, err = run([
            sys.executable, str(gate),
            "--request", p, "--signature", str(sig_ref),
            "--pubkey", args.pubkey, "--cosign", args.cosign,
        ])
        if rc != 0:
            detail = (err or out).strip().replace("\n", "\n      ")
            reject("ISO 27001 A.8.28 完整性 / ISO 20000 發布驗證",
                   f"{p}:目標環境重新驗章未通過(digest 未經本平台信任根簽章)。"
                   f"\n      {detail}")
            continue

        print(f"  ✓ {p}:{upstream} → {env}  digest 對齊上一區確認態 + 重新驗章通過")

    return _report(errors)


def _report(errors: list[str]) -> int:
    print("🔍 過版閘門 policy-promote(三閘門:範圍 / 血統+順序 / 重新驗章)")
    if errors:
        print("\n".join(errors))
        print(f"\n✗ 過版被拒:{len(errors)} 項不合規(fail-closed)")
        return 1
    print("✅ 過版放行:只動目標環境 source、digest 來自上一區確認態、且重新驗章通過。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
