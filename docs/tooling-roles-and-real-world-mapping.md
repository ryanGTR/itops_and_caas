---
title: 工具角色與正式環境對映（itops × GitHub × 企業 ITSM）
type: explanation
created: 2026-06-14
updated: 2026-06-14
tags: [architecture, governance, github, itsm, cmdb, servicenow, everything-as-code, portability]
---

# 工具角色與正式環境對映

> 這頁回答三個常被問到的設計問題:
> 1. 為什麼用 GitHub 當「專案/服務管理」?它在這裡的角色是什麼?
> 2. `itops_and_caas`(這個 repo)與 GitHub 的關係、權責怎麼分?
> 3. 這套 PoC 怎麼對映回銀行正式環境(ServiceNow / 真 CMDB / CAB)?

## 1. 核心立場:一切皆程式碼(Everything-as-Code)

本平台的論點是:把銀行原本散在多套企業系統的治理角色(服務台、變更、組態、稽核),
**全部收斂進 Git**,讓每件事都**版控、可 diff、可自動驗證、可回溯**。
GitHub 不是被當成「專案管理工具」,而是整條治理流程的 **單一真相來源 + 控制平面**。

## 2. GitHub 各部件的治理角色

| GitHub 部件 | 角色 | 對應框架 |
|---|---|---|
| Issue(Issue Form) | 服務請求單入口(服務台) | ITIL 請求履行 / ISO 20000 服務目錄 |
| Repo 檔案(`deployments/`、`iac/`) | 期望狀態真相來源(GitOps) | 組態管理 |
| `cmdb/`(D7) | 組態項目(CI)登錄 | ISO 20000 組態管理 / A.8.9 |
| Pull Request | 變更紀錄(可審核/回溯) | ISO 27001 A.8.32 / ISO 20000 變更管理 |
| Branch protection + CODEOWNERS | SoD + 存取控制強制點 | ISO 27001 A.5.3 / A.8.4 |
| GitHub Actions | 護欄(政策即程式碼)執行引擎 + CI/CD | ISO 27001 A.8.27 / A.5.36 |
| PR 歷史 / Actions log | 稽核證據軌跡 | ISO 27001 A.5.36 / ISO 20000 服務報告 |

## 3. itops_and_caas 與 GitHub 的權責邊界

**一句話:`itops` 是「規則與期望狀態的定義者」,GitHub 是「承載並執行這些規則的平台」。**
itops 寫「該怎樣」,GitHub 負責「真的讓它這樣」。

| 面向 | `itops_and_caas` 負責(定義) | GitHub 負責(承載 / 執行) |
|---|---|---|
| 政策 / 護欄 | checkov 規則、`CODEOWNERS` 內容、檢查腳本 | Actions 執行、protection 強制 |
| 服務請求 | 表單欄位、服務目錄內容 | Issue 系統承載 |
| 變更 | PR 範本(填什麼)、什麼算護欄變更 | PR 機制、合併控制 |
| 基礎設施 | OpenTofu 模組、`deployments/` 期望狀態 | 存 repo、觸發 apply |
| 組態 CMDB | schema + CI 資料 | 版控承載 + 變更史 |
| 稽核 | 要產什麼證據(報告腳本、對照表) | 原始事件資料(PR / log) |

> Java 類比:`itops`＝你的應用原始碼 + 設定;GitHub＝跑它的 application server / 平台。
> 換一台 server,程式邏輯大致不動,只有部署描述要改。

## 4. 可攜性:設計 vs 載體

這套設計的精髓:**治理設計幾乎平台無關,GitHub 只是其中一個實作載體。**

| 層次 | 換平台時 |
|---|---|
| 治理設計(服務目錄、變更模型、SoD、組態 schema、ISO 對照) | **大多可平移** |
| GitHub 專屬接線(Actions YAML、branch protection 腳本、Issue Form 格式) | 需在新平台**重做** |

> 這正是 **`supply-chain` 專案已經證明過的事**:同一套供應鏈治理理念,
> 在 GitLab → GitHub → Azure DevOps 三平台落地。itops 同理:設計可攜、載體可換。

## 5. 對映回銀行正式環境

PoC 用 GitHub 一套扮演全部角色,是為了在零成本下示範**模式**。正式落地時,各角色對映回企業既有系統:

| PoC(GitHub) | 銀行正式環境對應 | 對映時的重點 |
|---|---|---|
| Issue Form(服務請求) | ServiceNow / Jira Service Management 工單 | 表單欄位與分類對齊既有服務目錄 |
| Pull Request(變更) | 正式變更單 / RFC / CAB 紀錄 | 標準變更免逐次 CAB;高風險仍走 CAB |
| `deployments/` + `cmdb/`(組態) | 企業 CMDB(ServiceNow CMDB 等) | CI 與關係同步進真 CMDB(可用 API 雙寫) |
| Branch protection + CODEOWNERS(SoD) | 企業 IAM + 變更核准矩陣 | 角色群組對映到 AD / 權限矩陣 |
| GitHub Actions(護欄 / CI) | 企業 CI/CD(ADO Pipelines、Jenkins) + 政策引擎 | checkov / cosign 步驟平移 |
| cosign 簽章(金鑰對) | KMS / HSM-backed 簽章 | 金鑰治理升級(見 `docs/adr/0002`) |
| PR / Actions log(證據) | 稽核證據庫 / GRC 平台 | 報告對映 ISO 控制項(見 `COMPLIANCE_MAP.md`) |

**對稽核的論述**:我們不是「用 GitHub 取代企業治理工具」,而是用它示範一個
**可攜的、自動化的、全程可追溯的治理模式**;模式本身與平台解耦,正式落地時對映回公司既有系統。

## 6. 機密性與資料落地(Data Residency)— 稽核必問

> 常見且正確的質疑:「企業很多資料是機密,把這些放 GitHub 對嗎?」分四層回答:

### 6.1 公開 GitHub 只因這是「全假資料的學習 PoC」
本 repo 公開,是因為它**不含任何真實資料或憑證**(見 `README` / `LICENSE`),
目的是示範「該長什麼樣」。**真銀行不會把機密放公開 GitHub.com。**

### 6.2 正式環境用自架 / 內網平台,資料不出網段
| 公開 PoC | 銀行正式環境 |
|---|---|
| GitHub.com(公開) | GitHub **Enterprise Server**(自架機房) / GitLab **self-managed** / Azure DevOps **Server** |

同樣的 Issue / PR / Actions / CODEOWNERS 機制,只是跑在**銀行自己的網段內**,code 與元資料不出門。
> `supply-chain` 專案已示範:self-hosted GitLab 版 + Azure DevOps 版(公司真實落地)。

### 6.3 最關鍵:Git 存「治理設定 + 元資料」,不存機密本體
| 放進 Git(可版控) | **不**放進 Git(留在專用系統) |
|---|---|
| 部署設定、IaC、政策、文件 | **Secrets / 金鑰** → Vault / KMS / HSM |
| CMDB 的**元資料**(CI 記錄、關係) | **客戶 / 業務資料** → 資料庫 |
| 服務請求、變更紀錄 | **cosign 私鑰** → KMS / HSM(ADR-0002) |

- **機敏掃描護欄(TASK-03)就是強制這條**:金鑰想進版控會被自動擋下。
- 服務請求的**「資料分級」欄位**用來追蹤每個服務碰什麼等級的資料。
- 原則:**Git 是治理的真相來源,不是機密的儲存庫。** 真機密永遠在 Vault / DB / KMS。

### 6.4 不依賴平台的機密性控制
私有 repo、RBAC、自架 / 網路隔離、Vault/KMS 機密管理、機敏掃描護欄、資料分級——
這些**與用哪個平台無關**,換載體都適用。

## See Also
- `docs/golden-path-request-to-deploy.md`(部署黃金路徑全貌)
- `GOVERNANCE_BRIEF.md`(給稽核 / 主管的提案說明)
- `policies/README.md`(用護欄 vs 改護欄 的 SoD 模型)
- `COMPLIANCE_MAP.md`(技術控制 ↔ ISO 對照)
