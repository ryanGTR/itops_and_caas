#!/usr/bin/env python3
"""部署前驗章閘門 (TASK-D5) — fail-closed。

對一個 DeploymentRequest 執行「部署前」的強制檢查;**任一不過即拒絕部署(exit 1)**。
這是「不合規的產物根本部署不上去」的最後一道閘門。

檢查(全部 fail-closed):
  1. 不可變 digest:spec.source.digest 必須是 sha256:<64 hex>(否則=未經建置/簽章)。
  2. 簽章驗證:用本平台信任根(trust/cosign.pub)驗證對該 digest 的 cosign 簽章。
     - 本機 / self-test:對 digest 做 blob 驗證(cosign verify-blob),不需 registry。
     - 正式部署(TASK-D6):改用 `cosign verify --key trust/cosign.pub <image>@<digest>`。
  3. 組態登錄(CMDB):DeploymentRequest 必要欄位齊全(app/environment/requestedBy)。
     TASK-D7 接真正的 cmdb/ 後,改查 CI 是否存在。

對應治理控制項:
  ISO 27001 完整性控制 / A.8.28 供應鏈;ITIL 發布驗證 / 部署前檢查。

用法:
  verify_deploy_gate.py --request <req.yaml> --signature <sig> [--pubkey trust/cosign.pub]

Exit code:
  0  全部通過,放行
  1  任一檢查失敗,拒絕部署(fail-closed)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    print("✗ 需要 PyYAML(pip install pyyaml)", file=sys.stderr)
    sys.exit(1)

DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REQUIRED_META = ["app", "environment", "requestedBy"]


def reject(control: str, msg: str) -> None:
    """印出拒絕原因並以 fail-closed 結束。"""
    print(f"❌ 部署被拒(fail-closed)[{control}]:{msg}")
    sys.exit(1)


def main() -> int:
    ap = argparse.ArgumentParser(description="部署前驗章閘門 [TASK-D5]")
    ap.add_argument("--request", required=True, help="DeploymentRequest YAML")
    ap.add_argument("--signature", help="對 digest 的 cosign 簽章檔(blob 簽章)")
    ap.add_argument("--pubkey", default="trust/cosign.pub", help="信任根公鑰")
    ap.add_argument("--cosign", default="cosign", help="cosign 執行檔")
    args = ap.parse_args()

    req_path = Path(args.request)
    if not req_path.is_file():
        reject("輸入", f"找不到 DeploymentRequest:{req_path}")
    req = yaml.safe_load(req_path.read_text(encoding="utf-8")) or {}
    meta = req.get("metadata", {}) or {}
    spec = req.get("spec", {}) or {}
    source = spec.get("source", {}) or {}

    # --- 檢查 3(先做,便宜):CMDB 登錄 / 必要欄位 ---
    missing = [k for k in REQUIRED_META if not meta.get(k)]
    if missing:
        reject("ISO 20000 組態管理", f"DeploymentRequest 缺必要欄位:{', '.join(missing)}")

    # --- 檢查 1:不可變 digest ---
    digest = str(source.get("digest", "") or "")
    if not DIGEST_RE.match(digest):
        reject(
            "ISO 27001 A.8.28 完整性",
            f"spec.source.digest 不是有效的 sha256 digest(目前:{digest!r})"
            "——代表此 artifact 尚未經建置/簽章,不可部署。",
        )

    # --- 檢查 2:簽章驗證 ---
    if not args.signature:
        reject("ISO 27001 A.8.28 完整性", "未提供簽章——未簽章的 artifact 不可部署。")
    sig_path = Path(args.signature)
    if not sig_path.is_file():
        reject("ISO 27001 A.8.28 完整性", f"找不到簽章檔:{sig_path}")
    if not Path(args.pubkey).is_file():
        reject("信任根", f"找不到信任根公鑰:{args.pubkey}")

    # 對 digest 字串做 blob 驗證(payload = digest,不含換行)
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".payload") as f:
        f.write(digest)
        payload = f.name
    try:
        # key-pair 模型不用 Rekor 透明日誌(那是 keyless/Fulcio 用的);
        # --insecure-ignore-tlog 讓驗章離線自足,符合銀行氣隙情境。
        proc = subprocess.run(
            [args.cosign, "verify-blob", "--key", args.pubkey,
             "--signature", str(sig_path), "--insecure-ignore-tlog=true", payload],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        reject("工具", f"找不到 cosign 執行檔:{args.cosign}")
    finally:
        Path(payload).unlink(missing_ok=True)

    if proc.returncode != 0:
        reject(
            "ISO 27001 A.8.28 完整性",
            "cosign 驗章失敗——簽章無效或非本平台信任根所簽。\n"
            f"      cosign: {proc.stderr.strip() or proc.stdout.strip()}",
        )

    print(f"✅ 驗章通過,放行部署:{meta['app']} → {meta['environment']}  ({digest})")
    print("   通過:digest 不可變 + 簽章有效(本平台信任根)+ 組態欄位齊全。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
