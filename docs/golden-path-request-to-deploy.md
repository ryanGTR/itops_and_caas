---
title: 部署黃金路徑 — 需求單 → 部署到 OpenLiberty
type: design
created: 2026-06-14
updated: 2026-06-14
status: blueprint（待核准後逐 TASK 執行）
tags: [golden-path, itil, iso20000, iso27001, isms, configuration-management, opentofu, openliberty, supply-chain, cosign]
---

# 部署黃金路徑：需求單 → 部署到 OpenLiberty

> **這是藍圖（blueprint），不是實作。** 依 `CLAUDE.md` 鐵則：逐 TASK 執行、每步停下確認、不跳階段、決策留痕。
> 本文件描述「一個開發者從**提出服務請求**，到應用程式**安全地部署上 OpenLiberty**」的完整治理化流程，並把每一步對映到 ISMS / ITIL / ISO 20000 / 組態管理。
>
> 對應的工作分解見 `PROJECT_PLAN.md` 的 **Phase D**；關鍵技術決策見 `docs/adr/0002-openliberty-runtime-and-deploy.md`。

## 0. 這條路徑與既有「黃金路徑」的關係

本專案已有一條**建專案黃金路徑**（`scaffold/docs/golden-path.md`：點 template → 生出合規新 repo）。本文件新增的是一條**部署黃金路徑**：把「一個既存的應用程式」經過治理化的供應鏈與變更流程，**安全地佈建與部署到執行環境（OpenLiberty）**。

| | 建專案黃金路徑（既有） | 部署黃金路徑（本文件，新增） |
|---|---|---|
| 觸發 | 「我要開一個新專案」 | 「我要把 app 部署到一個環境」 |
| 產物 | 一個預設合規的 repo | 一個跑在 OpenLiberty 上、可稽核的應用實例 |
| 體現 | 降低認知負荷 | 護欄 + 平台即產品 + 端到端可追溯 |

## 1. 一句話總結（給稽核 / 主管）

> 開發者**填一張服務請求單**，平台就自動把應用程式**建置→產 SBOM→掃描→簽章→驗章→佈建環境→部署→登錄 CMDB→產出稽核證據**——全程沒有人工搬運、每一步都留痕、不合規的產物**根本部署不上去**。

## 2. 角色與職責分離（SoD｜ISO 27001 A.5.3）

| 角色 | 能做什麼 | 不能做什麼 |
|---|---|---|
| 開發者（請求者） | 提服務請求單、改自己 app 的業務碼 | 改護欄、改政策、直接部署 |
| 平台 + 資安群組 | 維護護欄 / OpenTofu 模組 / 簽章信任根 / CMDB schema | （流程上）替自己的請求核准 |
| 自動化護欄（CI/CD） | 強制執行：掃描、簽章、驗章、佈建、登錄、產證據 | 被單一開發者繞過 |

> Java 類比：護欄像 framework 的 `final` + 編譯期檢查——你能在框架給的安全範圍內自由寫業務碼，但改不動框架本身的保證。

## 3. 端到端流程（七階段）

```
[開發者]                          [平台自動化護欄]                         [框架對映]
   │
   ① 提服務請求單 ───────────────────────────────────────────────▶ ITIL 請求履行
   │   (GitHub Issue Form：要部署哪個 app / 哪個環境 / 版本)         ISO 20000 服務請求/服務目錄
   │                                                                  （標準變更：預核准、低風險、可重複）
   ▼
   ② 請求轉變更 (PR) ─────────────────▶ 變更紀錄：目的/風險/回退      ISO 27001 A.8.32 變更管理
   │                                      main 受保護、需通過所有護欄    ISO 20000 變更管理
   ▼
   ③ 供應鏈建置 ──────────────────────▶ build → SBOM → SCA 掃描       ISMS / ISO 27001 A.8.28
   │   (Java/Maven app, 來自 supply-chain) → cosign 簽章(L4)            供應鏈完整性
   ▼
   ④ 佈建環境 (OpenTofu) ─────────────▶ 「預設合規」開出 OpenLiberty   ISO 27001 Secure by Default
   │   (Podman 容器, checkov 閘門)        runtime                        IaC 護欄
   ▼
   ⑤ 部署前驗章閘門 ──────────────────▶ cosign verify + 掃描通過 +     ISO 27001 完整性 / ITIL 發布驗證
   │   (fail-closed)                      CMDB 條目存在，否則拒絕部署
   ▼
   ⑥ 部署到 OpenLiberty ──────────────▶ 部署已驗章的 artifact + 煙霧測試 ISO 20000 發布與部署管理
   │
   ▼
   ⑦ 登錄 CMDB + 產稽核證據 ──────────▶ 登錄/更新 CI（app/版本/實例/   ISO 20000 組態管理 / ISO 27001 A.8.9
       (組態管理 + 服務報告)              簽章 digest/關係）；產出端到端    ISO 27001 A.5.36 合規審查
                                          證據鏈報告                        ISO 20000 服務報告
```

## 4. 各階段設計細節

### ① 服務請求單（ITIL 請求履行 / ISO 20000 服務請求）
- **載體**：GitHub Issue Form（`.github/ISSUE_TEMPLATE/service-request.yml`）。欄位：應用名、來源 artifact/版本、目標環境、商業理由、資料分級（模擬）。
- **治理意涵**：這是**服務目錄**裡一個**預核准的標準服務**（部署到 OpenLiberty 沙箱）。標準變更依框架本就免逐次 CAB。
- **為什麼用 Issue Form**：表單即結構化資料，可被自動化讀取轉成 PR/CMDB，全程不離開 Git。

### ② 變更（ISO 27001 A.8.32 / ISO 20000 變更管理）
- 請求 → 一個 PR（沿用 Phase 1 `TASK-06`：PR 範本要求目的/風險/回退；main 受保護）。
- 護欄變更（policies/、workflows/）需平台+資安額外核准（`TASK-05` SoD）。

### ③ 供應鏈建置 + 簽章（ISMS / ISO 27001 A.8.28、A.8.x）
- **app 來源**：`supply-chain/github/app/backend`（Java/Maven）。
- **產物**：容器映像 + **SBOM**（CycloneDX/SPDX）+ **SCA 掃描結果** + **cosign 簽章**。
- **這一步補上 supply-chain 專案的 L4 缺口**（部署驗證/簽章）。金鑰選型見 ADR-0002。

### ④ 佈建（ISO 27001 Secure by Default / checkov 閘門）
- **OpenTofu 模組** `openliberty-service`：開出一個跑 OpenLiberty 的 **Podman 容器**，預設安全（非 root、資源上限、健康檢查、不放明文機密、最小權限）。
- 沿用 Phase 2 secure-bucket 的模式：模組 + `checkov` 靜態掃 + 違規測試 + 可稽核豁免（SoA 精神）。

### ⑤ 部署前驗章閘門（ISO 27001 完整性 / ITIL 發布驗證）
- 部署前**強制**：`cosign verify` 通過 + SCA 無高風險 + 該 artifact 在 CMDB 有對應 CI。
- **Fail-closed**：任一不過 → 拒絕部署，留下攔截紀錄。

### ⑥ 部署（ISO 20000 發布與部署管理）
- 把**已驗章**的 artifact 部署到 ④ 開出的 OpenLiberty，跑煙霧測試（打 app 端點確認 200）。

### ⑦ 組態管理 + 稽核證據（ISO 20000 組態管理 / ISO 27001 A.8.9、A.5.36）
- **CMDB-as-code**：`cmdb/*.yaml` 登錄 CI——應用、版本、artifact digest、簽章、OpenLiberty 實例、所屬環境、關係（誰部署誰）。版控 = 天然的組態基線與變更史。
- **端到端證據鏈**：擴充 `scripts/generate_audit_report.py`，把「請求 → PR → 建置/簽章 → 驗章 → 部署 → CMDB」串成一份對映 ISO 控制項的報告。

## 5. 用到的現成資產（不重造輪子）

| 來源 | 提供什麼 | 用在哪一階段 |
|---|---|---|
| `itops_and_caas`（本 repo） | PR 變更管理、SoD、CODEOWNERS、稽核報告骨架、OpenTofu+checkov 模式 | ②④⑦ |
| `supply-chain/github/app/backend` | Java/Maven 應用（部署標的） | ③⑥ |
| `supply-chain`（github demo） | build/SBOM/SCA 流程；cosign 簽章（補 L4） | ③⑤ |
| OpenTofu（ADR-0001 已選型） | IaC 佈建 OpenLiberty runtime | ④ |

## 6. 範圍與非範圍

**範圍**：本機、零雲端成本的 PoC；以模擬資料示範完整治理鏈；OpenLiberty 跑在 Podman 容器。
**非範圍**：正式生產部署；真實機密分級/資料；取代既有 CAB（本路徑只補強「標準變更」這一類）；k8s/ArgoCD（屬原 roadmap 後續 Phase，本路徑不依賴）。

## 7. 完成定義（Gate D）

見 `PROJECT_PLAN.md` Phase D 的 Gate D：能從「提一張服務請求單」一路自動走到「app 跑在 OpenLiberty 上」，且產出涵蓋七階段、對映 ISO 控制項的稽核證據，CMDB 同步更新——全數打勾才算完成。

## See Also
- `PROJECT_PLAN.md`（Phase D 工作分解）
- `docs/adr/0002-openliberty-runtime-and-deploy.md`（技術決策）
- `docs/adr/0001-phase2-iac-stack.md`（OpenTofu/LocalStack/Podman/checkov 選型）
- `COMPLIANCE_MAP.md`（技術控制 ↔ ISO 對照）
- `scaffold/docs/golden-path.md`（建專案黃金路徑，互補）
