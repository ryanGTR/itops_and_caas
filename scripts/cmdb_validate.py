#!/usr/bin/env python3
"""CMDB 驗證器 (TASK-D7) — fail-closed。

把 CMDB 當「受治理的組態基線」來驗:每個 CI 結構完整、欄位齊全、引用的物證
(簽章 / DeploymentRequest / 信任根)確實存在,且 CI 記的 digest 與其來源
DeploymentRequest **一致**(防 CMDB 與真相漂移)。任一不過 → exit 1。

這讓「CMDB 即程式碼」不只是一份 YAML,而是受 CI 閘門保護的組態基線
(由 .github/workflows/policy-cmdb.yml 在每個 PR 重跑)。

對應治理控制項:
  ISO 20000 組態管理;ISO 27001 A.8.9 組態管理;A.5.36 合規審查。

用法:
  cmdb_validate.py [--cmdb-dir cmdb] [--deployments-dir deployments]
Exit code:0 全通過;1 任一 CI 不合規(fail-closed)。
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

DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def main() -> int:
    ap = argparse.ArgumentParser(description="CMDB 驗證器 [TASK-D7]")
    ap.add_argument("--cmdb-dir", default="cmdb")
    ap.add_argument("--deployments-dir", default="deployments")
    args = ap.parse_args()

    root = Path(args.cmdb_dir)
    if not root.is_dir():
        print(f"✗ 找不到 CMDB 目錄:{root}")
        return 1

    ci_files = sorted(p for p in root.rglob("*.yaml"))
    if not ci_files:
        print(f"✗ CMDB 目錄無任何 CI:{root}")
        return 1

    errors: list[str] = []

    def err(f: Path, control: str, msg: str) -> None:
        errors.append(f"  ❌ {f} [{control}]:{msg}")

    for f in ci_files:
        try:
            ci = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            err(f, "結構", f"YAML 解析失敗:{exc}")
            continue

        if ci.get("kind") != "ConfigurationItem":
            err(f, "結構", f"kind 應為 ConfigurationItem(得:{ci.get('kind')!r})")
        meta = ci.get("metadata", {}) or {}
        spec = ci.get("spec", {}) or {}
        for k in ("ciId", "app", "environment"):
            if not meta.get(k):
                err(f, "ISO 20000 組態管理", f"metadata 缺 {k}")

        source = spec.get("source", {}) or {}
        digest = str(source.get("digest", "") or "")
        if not DIGEST_RE.match(digest):
            err(f, "ISO 27001 A.8.28 完整性", f"source.digest 非有效 sha256:{digest!r}")

        # 引用物證須存在
        for ref_key in ("signature",):
            ref = source.get(ref_key)
            if not ref or not Path(ref).is_file():
                err(f, "ISO 27001 A.8.28", f"source.{ref_key} 指向的物證不存在:{ref!r}")

        prov = spec.get("provenance", {}) or {}
        if prov.get("result") != "success":
            err(f, "ISO 20000 組態管理", f"只應登錄成功部署(provenance.result={prov.get('result')!r})")
        dep_ref = prov.get("deploymentRequest")
        if not dep_ref or not Path(dep_ref).is_file():
            err(f, "ISO 20000 組態管理", f"provenance.deploymentRequest 不存在:{dep_ref!r}")
        else:
            # 一致性:CI 的 digest 必須等於來源 DeploymentRequest 的 digest
            dep = yaml.safe_load(Path(dep_ref).read_text(encoding="utf-8")) or {}
            dep_digest = str(((dep.get("spec") or {}).get("source") or {}).get("digest", "") or "")
            if dep_digest != digest:
                err(f, "ISO 27001 A.8.9 組態基線",
                    f"CI digest 與 DeploymentRequest 不一致(CI:{digest} ≠ 來源:{dep_digest})")

        rels = spec.get("relationships") or []
        if not isinstance(rels, list) or not rels:
            err(f, "ISO 20000 組態管理", "relationships 不可為空(CI 須記錄組態關係)")

        # 信任根須在版控內
        if not Path("trust/cosign.pub").is_file():
            err(f, "信任根", "trust/cosign.pub 不存在")

    print(f"🔍 CMDB 驗證:共 {len(ci_files)} 個 CI")
    if errors:
        print("\n".join(errors))
        print(f"\n✗ CMDB 驗證失敗:{len(errors)} 項不合規(fail-closed)")
        return 1
    print("✅ CMDB 驗證通過:所有 CI 結構完整、物證存在、digest 與來源一致。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
