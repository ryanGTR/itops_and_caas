---
title: 組態管理（CMDB-as-code）+ 端到端稽核證據鏈
type: howto
created: 2026-06-15
updated: 2026-06-15
tags: [cmdb, configuration-management, audit, evidence-chain, iso20000, iso27001, golden-path]
---

# 組態管理（CMDB-as-code）+ 端到端稽核證據鏈

> 對應 `PROJECT_PLAN.md` [TASK-D7]，黃金路徑**階段⑦**(收尾)。
> 把一次部署**登錄為組態項目(CI)**,並把整條路徑串成一份**對映 ISO 控制項**的稽核證據。
> 上游:[TASK-D6] 部署 + `last-deploy.json`。

## 兩個產物

### 1. CMDB-as-code(組態基線）

部署成功後,`scripts/cmdb_register.py` 讀 DeploymentRequest + `last-deploy.json`,
產出 `cmdb/<env>/<app>.yaml`(一個 CI)。內容涵蓋 [TASK-D7] 要求的:
**應用、版本、artifact digest、簽章、OpenLiberty 實例、環境、組態關係**。

受 `policy-cmdb.yml` 閘門保護:`cmdb_validate.py` 在每個 PR 驗結構 / 物證存在 /
**CI digest 與來源 DeploymentRequest 一致**(防漂移),fail-closed。細節見 `cmdb/README.md`。

### 2. 端到端稽核證據鏈(七階段)

`scripts/generate_audit_report.py` 新增一節「**黃金路徑端到端證據鏈**」,把每次部署
沿七階段串起來,每階段附**物證指標**與對映 ISO 控制項:

| 階段 | 物證來源 | 對映 ISO |
|---|---|---|
| ① 服務請求單 | DeploymentRequest.serviceRequest | ITIL 請求履行 / ISO 20000 服務請求 |
| ② 請求轉變更(PR) | deployments/<env>/<app>.yaml | ISO 27001 A.8.32 |
| ③ 建置 + 簽章 | sig/<app>.sig + digest | ISO 27001 A.8.28 |
| ④ 佈建環境 | iac/environments/<env> | ISO 27001 Secure by Default |
| ⑤ 驗章閘門 | last-deploy.json: gate=passed | ISO 27001 完整性 |
| ⑥ 部署 + 煙霧 | last-deploy.json: result + smokeTest | ISO 20000 發布與部署管理 |
| ⑦ CMDB | cmdb/<env>/<app>.yaml | ISO 20000 組態管理 / A.8.9 |

> 這一節**離線可跑**(只讀版控內物證);其餘節(PR/Actions 統計)仍走 `gh`。

## 用法

```bash
# 登錄 CI(部署成功後)
python3 scripts/cmdb_register.py --request deployments/openliberty-sandbox/supply-chain-backend.yaml

# 驗證 CMDB 基線(CI 閘門也會跑)
python3 scripts/cmdb_validate.py

# 產出含「端到端證據鏈」的稽核報告(需 gh 登入;月報由 audit-report.yml 自動跑)
python3 scripts/generate_audit_report.py --output audit-report.md
```

## 已驗證(本機實跑)

| 檢查 | 結果 |
|---|---|
| 登錄 CI(讀真實 last-deploy.json） | ✅ `cmdb/openliberty-sandbox/supply-chain-backend.yaml` |
| CMDB 驗證(合規） | ✅ exit 0 |
| CMDB self-test(digest 漂移 / 缺關係被擋） | ✅ 3/3 fail-closed |
| 端到端證據鏈(七階段） | ✅ 七階段物證齊備 |

## 正式環境差異（PoC vs 銀行）

- **CI 範圍**:PoC 只登錄「已部署應用實例」;正式可擴及主機 / 中介軟體 / 網路等 CI 與其關係圖。
- **漂移偵測**:PoC 比對 digest 與 DeploymentRequest;正式可加「實際運行態 vs 期望態」對帳。
- **證據鏈來源**:PoC 用本機物證;正式可串 registry digest、Rekor 透明日誌、真實 issue/PR 編號。

## See Also
- `cmdb/README.md`（CMDB-as-code 慣例與 schema）
- `scripts/cmdb_register.py` / `scripts/cmdb_validate.py`
- `scripts/generate_audit_report.py`（端到端證據鏈一節）
- `docs/deploy-to-openliberty.md`（上游:TASK-D6 部署 + 證據）
- `docs/golden-path-request-to-deploy.md`（全貌,階段⑦）
