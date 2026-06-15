#!/usr/bin/env python3
"""CMDB 登錄器 (TASK-D7) — 把一次成功部署登錄為組態項目(CI)。

黃金路徑階段⑦的前半:部署成功後,把「這次部署」寫成一筆 **CMDB-as-code** 的
Configuration Item(CI)。版控史 = 天然的組態基線與變更史(GitOps 雛形)。

資料來源(單一真相,皆為版控內檔案):
  - DeploymentRequest(deployments/<env>/<app>.yaml):app/環境/請求者/來源/分級/runtime
  - 部署證據(deployments/<env>/last-deploy.json):部署時間/結果/閘門/實際映像
  - 簽章檔(deployments/<env>/sig/<app>.sig):簽章物證

產出:cmdb/<env>/<app>.yaml(一個 CI = 一個應用在某環境的已部署實例)。
冪等:重跑會以最新部署狀態覆寫同一 CI(版控 diff 即變更史)。

對應治理控制項:
  ISO 20000 組態管理;ISO 27001 A.8.9 組態管理。

用法:
  cmdb_register.py \
    --request deployments/openliberty-sandbox/supply-chain-backend.yaml \
    [--record deployments/openliberty-sandbox/last-deploy.json] \
    [--cmdb-dir cmdb]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("✗ 需要 PyYAML(pip install pyyaml)")


def main() -> int:
    ap = argparse.ArgumentParser(description="CMDB 登錄器 [TASK-D7]")
    ap.add_argument("--request", required=True, help="DeploymentRequest YAML")
    ap.add_argument("--record", help="部署證據 last-deploy.json(預設:同目錄)")
    ap.add_argument("--cmdb-dir", default="cmdb", help="CMDB 根目錄(預設 cmdb)")
    args = ap.parse_args()

    req_path = Path(args.request)
    if not req_path.is_file():
        sys.exit(f"✗ 找不到 DeploymentRequest:{req_path}")
    req = yaml.safe_load(req_path.read_text(encoding="utf-8")) or {}
    meta = req.get("metadata", {}) or {}
    spec = req.get("spec", {}) or {}
    source = spec.get("source", {}) or {}
    runtime = spec.get("runtime", {}) or {}

    app = meta.get("app")
    env = meta.get("environment")
    if not app or not env:
        sys.exit("✗ DeploymentRequest 缺 metadata.app / metadata.environment")

    # 部署證據(預設與 request 同目錄的 last-deploy.json)
    record_path = Path(args.record) if args.record else req_path.parent / "last-deploy.json"
    if not record_path.is_file():
        sys.exit(f"✗ 找不到部署證據:{record_path}(請先成功部署,見 TASK-D6)")
    record = json.loads(record_path.read_text(encoding="utf-8"))

    if record.get("result") != "success":
        sys.exit(f"✗ 部署證據 result={record.get('result')!r},非 success——不登錄失敗的部署。")

    http_port = runtime.get("httpPort", record.get("httpPort", 9080))
    sig_rel = f"deployments/{env}/sig/{app}.sig"
    deploy_req_rel = f"deployments/{env}/{app}.yaml"

    ci = {
        "apiVersion": "cmdb/v1",
        "kind": "ConfigurationItem",
        "metadata": {
            "ciId": f"ci-{app}-{env}",
            "type": "deployed-application",
            "app": app,
            "environment": env,
        },
        "spec": {
            "source": {
                "artifact": source.get("artifact"),
                "version": source.get("version"),
                "digest": source.get("digest"),
                "gitCommit": source.get("gitCommit", ""),   # 血統:源碼 commit(供過版傳遞)
                "gitTag": source.get("gitTag", ""),          # 發布 tag
                "signature": sig_rel,
            },
            "runtime": {
                "type": runtime.get("type", "openliberty"),
                "instance": app,                       # 容器名 = 實例識別
                "url": f"http://127.0.0.1:{http_port}",
                "httpPort": http_port,
            },
            "provenance": {
                "serviceRequest": meta.get("serviceRequest", ""),
                "requestedBy": meta.get("requestedBy", ""),
                "deploymentRequest": deploy_req_rel,
                "gate": record.get("gate", ""),
                "deployedAt": record.get("deployedAt", ""),
                "result": record.get("result", ""),
            },
            "dataClassification": spec.get("dataClassification", ""),
            # 組態關係(CI 之間的依存):稽核可據此追溯「誰部署誰/誰簽誰」。
            "relationships": [
                {"type": "deployed-from", "target": deploy_req_rel},
                {"type": "signed-by", "target": "trust/cosign.pub"},
                {"type": "runs-on", "target": env},
            ],
        },
    }

    out_dir = Path(args.cmdb_dir) / env
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{app}.yaml"
    header = (
        "# CMDB Configuration Item(CI)— 由 scripts/cmdb_register.py 於部署成功後產出。\n"
        "# 一個 CI = 一個應用在某環境的已部署實例;版控史即組態基線與變更史。\n"
        "# 對應:ISO 20000 組態管理 / ISO 27001 A.8.9。請勿手改——重跑 register 會覆寫。\n"
    )
    out_path.write_text(
        header + yaml.safe_dump(ci, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(f"✅ 已登錄 CI:{out_path}  ({app} @ {env}, {source.get('digest')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
