---
title: supply-chain → itops 交接契約(整合邊界)
type: contract
created: 2026-06-15
updated: 2026-06-15
tags: [integration, supply-chain, itops, handoff, slsa]
---

# supply-chain → itops 交接契約

> 這是兩個**各自活著**的系統之間的邊界。supply-chain 負責「供應鏈左側」(build/掃描/簽章),
> itops 負責「部署右側治理」(驗章閘門/部署/CMDB/多環境晉級)。中間只靠這一份 **handoff manifest**
> + 已簽章 artifact 串起來——像企業裡資安組(供應鏈)交棒給平台組(部署治理)。

## 邊界圖

```
[ supply-chain 系統 ]                          [ itops 系統 ]
 build → test → scan → sign                     ingest → 部署前驗章閘門(fail-closed)
   │                                              → 部署(OpenLiberty)→ 煙霧測試
   └── 產出:已簽章 artifact + handoff manifest ──▶  → CMDB 登錄 + 端到端證據
       (integration/inbox/<app>.handoff.yaml)     → (後續)build once promote 多環境
```

## handoff manifest 欄位

supply-chain 端在 build+sign 完成後產出 `integration/inbox/<app>.handoff.yaml`:

```yaml
apiVersion: handoff/v1
kind: SignedArtifact
app: supply-chain-backend
environment: openliberty-sandbox      # itops 要部署的目標環境
source:
  artifact: localhost/supply-chain-backend   # 映像名(不含 tag)
  version: b1                                 # 版本 tag
  digest: "sha256:..."                        # 不可變 digest(itops verify-blob 驗這個)
  gitCommit: "..."                            # 血統(可選)
  gitTag: "..."
  testReport: "sha256:..."                    # 測試證據指紋(surefire 報告雜湊)
  testCount: 3                                # 測試數(>=1)
signature: supply-chain-backend.sig           # 對 digest 的 cosign blob 簽章(與 manifest 同目錄)
provenance:                                    # 供稽核追溯(itops 不強制,但記錄)
  builtBy: supply-chain
  pipeline: github/app/.github/workflows/supply-chain.yml
```

## itops 端如何消費

`integration/itops_ingest.sh <app>.handoff.yaml`:
1. 把 manifest 的 `source` 寫進對應環境的 itops DeploymentRequest(只搬 source,config 隨環境)。
2. 把簽章放到 `deployments/<env>/sig/`。
3. 跑 `deploy_openliberty.sh`(D5 部署前驗章閘門 fail-closed → tofu apply → 煙霧測試)。
4. 跑 `cmdb_register.py` 登錄 CI(含測試證據 + 端到端證據鏈)。

**itops 不重建、不重簽**——只消費 supply-chain 已簽好的產物並治理它的部署。這就是「整合」而非「重做」。

## 真實環境的演進(自動化)

本地 demo 是手動跑兩支腳本。真實自動化:
- supply-chain 的 GitHub Actions 在 sign 後 `repository_dispatch` 觸發 itops 的 ingest workflow(帶 manifest)。
- itops 端用 self-hosted runner(有 podman / 之後 QEMU)跑 ingest。
- 部署目標可從 podman 容器升級為 OpenTofu 開的 QEMU/libvirt Linux VM(下一步)。
