---
title: 補單流程（Retroactive Change）— 補單≠漂白
type: howto
created: 2026-06-15
updated: 2026-06-15
tags: [retroactive, out-of-band, nonconformity, pir, drift, change-management, iso27001, iso20000]
---

# 補單流程：補單≠漂白

> 對應 `PROJECT_PLAN.md` [TASK-E5],收關 Phase E。
> 當有人**沒走流程就動了線上**(out-of-band 變更),事後要補單。本文件定義「**補單≠漂白**」
> 的處理:記錄事實 **與** 矯正根因**分開**,並用程式碼強制「補單一定綁回不符合事項」。

## 1. 核心原則

> **補單不是把違規漂白,是留下事實 + 啟動矯正。** 只補單、不追根因 = 縱容繞過。

兩件事**分開**處理:

| | 做什麼 | 載體 | 控制 |
|---|---|---|---|
| (a) **記錄變更** | 補一張 `retroactive` DeploymentRequest,把實際做了什麼登錄回 CMDB | deployments/ + cmdb/ | A.8.32 / A.8.9 |
| (b) **矯正根因** | 連回「為何繞得過流程」的不符合事項,啟動矯正(終極解=修護欄讓繞過不可能) | nonconformity / PIR | A.5.36 / 矯正措施 |

## 2. 怎麼觸發:漂移偵測(E4)→ 補單(E5)

```
reconcile.py 偵測到漂移 ──開── [DRIFT] issue(不符合事項)
        │                              │
        │  「線上跑的 ≠ CMDB / 實例被動過」  │ 例:issue #21
        ▼                              ▼
   補一張 retroactive DeploymentRequest,綁回那張 issue(nonconformity: "#21")
        │
        ▼
   policy-change-class 強制驗:retroactive ⇒ justification + pir{owner,dueBy} + nonconformity
        │  缺任一即擋(補單不能只記事實、不追根因)
        ▼
   合併後 emergency-pir 自動為這張 retroactive 開 PIR(回顧為何繞得過)
```

## 3. 閘門強制(policy-change-class｜TASK-E5)

`scripts/validate_change_class.py` 對 `changeType: retroactive` 強制:

1. `justification`——補了什麼、為何當初沒走流程。
2. `pir{owner, dueBy}`——承諾事後回顧(同急件)。
3. **`nonconformity`**——關聯的不符合事項 / 漂移 issue 編號(連回根因)。

缺任一即 `fail-closed`(self-test 證明補單缺 nonconformity 會被擋)。

## 4. 範例(retroactive DeploymentRequest)

```yaml
apiVersion: golden-path/v1
kind: DeploymentRequest
metadata:
  app: supply-chain-backend
  environment: openliberty-sandbox
  requestedBy: sre                      # 補單者
  changeType: retroactive               # 補單
  justification: "值班為止血,手動把實例移除,當下未開單"
  pir:                                  # 事後回顧承諾
    owner: sre-lead
    dueBy: "2026-06-22"
  nonconformity: "#21"                  # ★ 連回漂移偵測開的不符合事項(E4)
spec:
  source:
    artifact: localhost/supply-chain-backend
    version: d6
    digest: "sha256:98a5…"
  runtime: { type: openliberty, httpPort: 9080 }
```

> 注意:補單**仍要過所有技術閘門**(簽章/驗章)——補單是補「流程紀錄」,不是給不合規開後門。

## 5. 正式環境差異

- **不符合事項**:PoC 用 GitHub issue;正式接 ITSM 的 nonconformity / incident 編號。
- **矯正措施**:正式會要求根因分析(RCA)+ 預防再發,並追蹤到關閉。
- **終極解**:讓繞過根本發生不了(更強的護欄 / 唯一變更入口),補單趨近於零才是目標。

## See Also
- `scripts/validate_change_class.py`（補單閘門:retroactive ⇒ justification+pir+nonconformity）
- `scripts/reconcile.py`（E4 漂移偵測:補單的觸發來源）
- `docs/exception-and-drift-governance.md`（Phase E 藍圖,三場景全貌）
- `docs/adr/0003-exception-path-and-drift.md`（決策）
