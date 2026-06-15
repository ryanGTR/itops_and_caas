#!/usr/bin/env python3
"""過版生成器 (TASK-F2)。

把「上一區已驗章、確認在跑的 digest」推進下一區——build once, promote。
**只改目標環境 DeploymentRequest 的 `spec.source`(逐行外科手術,保留註解與 config)**,
runtime / dataClassification / metadata 一律不碰。這就是 promote PR 的靈魂:
審核者打開只看到「從 digest X 換成 digest Y,其他沒動」。

來源真相 = **上一區的 CMDB CI(確認態)**,不是 DeploymentRequest(期望態)——
你只能 promote「真的跑通且驗過章」的東西。

對應治理控制項:ISO 20000 變更管理 / 發布管理;ISO 27001 A.8.32。

用法:
  promote.py --from <env> --to <env> --app <app>
             [--cmdb-dir cmdb] [--deployments-dir deployments]
  生成檔案變更(由 promote.yml workflow 接著開 PR);印出過版摘要。
Exit code:0 成功;2 輸入錯誤;3 來源 CMDB 無此 CI。
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("✗ 需要 PyYAML(pip install pyyaml)")

# 過版只搬這些 source 欄位;其餘(尤其 runtime/config)絕不動。
# 值的引號樣式對齊 deployments 慣例,確保未變動的欄位零 cosmetic diff。
# testReport/testCount=測試證據,與 digest 同屬「這次 build 的不可分身分」,
# 必須一起過版——否則目標環境會留著上一個 digest 的舊測試證據(漂白)。
PROMOTE_KEYS = ["artifact", "version", "digest", "gitCommit", "gitTag",
                "testReport", "testCount"]
QUOTED = {"digest", "gitCommit", "gitTag", "testReport"}


def fmt(key: str, val: str) -> str:
    return f'"{val}"' if key in QUOTED else val


def surgical_update(text: str, new: dict) -> tuple[str, dict]:
    """只改 spec.source 區塊內 PROMOTE_KEYS 的值,保留註解/縮排/其餘所有行。"""
    lines = text.splitlines(keepends=True)
    out, changes = [], {}
    in_source = False
    src_indent = None
    for line in lines:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        # 進入 / 離開 spec.source 區塊(以縮排判定)
        # 允許 source: 行尾帶註解(真實 deployments 檔的 source: 常有說明註解;
        # 早期只比對 `source:$` 會漏進區塊 → 過版「無變更」。真 live 才抓到的雷)。
        if re.match(r"^\s*source:\s*(#.*)?$", line):
            in_source = True
            src_indent = indent
            out.append(line)
            continue
        if in_source:
            # 區塊結束:遇到縮排 <= source 的非空白行
            if stripped.strip() and indent <= src_indent:
                in_source = False
            else:
                m = re.match(r"^(\s*)([A-Za-z]+):(\s*)(.*?)(\s*#.*)?$", line.rstrip("\n"))
                if m and m.group(2) in PROMOTE_KEYS and m.group(2) in new:
                    key = m.group(2)
                    old_val = m.group(4).strip().strip('"')
                    new_val = str(new[key])
                    comment = m.group(5) or ""
                    nl = line[len(line.rstrip("\n")):]  # 保留原行尾
                    out.append(f"{m.group(1)}{key}:{m.group(3)}{fmt(key, new_val)}{comment}{nl}")
                    if old_val != new_val:
                        changes[key] = (old_val, new_val)
                    continue
        out.append(line)
    return "".join(out), changes


def main() -> int:
    ap = argparse.ArgumentParser(description="過版生成器 [TASK-F2]")
    ap.add_argument("--from", dest="src", required=True, help="來源環境")
    ap.add_argument("--to", dest="dst", required=True, help="目標環境")
    ap.add_argument("--app", required=True)
    ap.add_argument("--cmdb-dir", default="cmdb")
    ap.add_argument("--deployments-dir", default="deployments")
    args = ap.parse_args()

    if args.src == args.dst:
        print("✗ --from 與 --to 不可相同", file=sys.stderr)
        return 2

    ci_path = Path(args.cmdb_dir) / args.src / f"{args.app}.yaml"
    if not ci_path.is_file():
        print(f"✗ 來源 CMDB 無此 CI:{ci_path}(只能 promote 已部署且登錄的環境)", file=sys.stderr)
        return 3
    ci = yaml.safe_load(ci_path.read_text(encoding="utf-8")) or {}
    src_source = (ci.get("spec", {}) or {}).get("source", {}) or {}
    new = {k: src_source.get(k, "") for k in PROMOTE_KEYS if src_source.get(k)}
    if "digest" not in new:
        print(f"✗ 來源 CI 無有效 digest:{ci_path}", file=sys.stderr)
        return 3

    tgt_path = Path(args.deployments_dir) / args.dst / f"{args.app}.yaml"
    if not tgt_path.is_file():
        print(f"✗ 目標環境無 DeploymentRequest:{tgt_path}(請先建環境骨架,TASK-F1)", file=sys.stderr)
        return 2

    updated, changes = surgical_update(tgt_path.read_text(encoding="utf-8"), new)
    tgt_path.write_text(updated, encoding="utf-8")

    # 簽章一起過版:build once → 同一 digest → 同一簽章。目標環境的部署閘門 / CMDB
    # 驗證需要該環境目錄下有簽章物證,故把來源環境的 .sig 複製過去(內容相同)。
    sig_note = ""
    src_sig = Path(args.deployments_dir) / args.src / "sig" / f"{args.app}.sig"
    if src_sig.is_file():
        dst_sig = Path(args.deployments_dir) / args.dst / "sig" / f"{args.app}.sig"
        dst_sig.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_sig, dst_sig)
        sig_note = f"  簽章物證:已複製 {src_sig} → {dst_sig}(同 digest 同簽章)。"

    print(f"▶ 過版:{args.src} → {args.dst}  ({args.app})")
    print(f"  來源(CMDB 確認態):{ci_path}")
    print(f"  目標(只改 source):{tgt_path}")
    if changes:
        for k, (old, nw) in changes.items():
            print(f"  • {k}: {old} → {nw}")
    else:
        print("  • 無變更(目標已與來源同步)")
    print("  config / runtime 未動(promotion 只搬 artifact 身分,不搬設定)。")
    if sig_note:
        print(sig_note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
