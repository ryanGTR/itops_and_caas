# 銀行內部開發者平台(IDP)落地計畫
## Platform Engineering × ISO 27001 / ISO 20000 治理對齊

> **文件用途**:本文件為技術 + 治理雙軌的完整工作說明書。
> 既可給工程團隊逐項執行,也可作為向資安 / 稽核 / 主管提案的治理依據。
> 設計為可直接放入 Git repo,並交由 Claude Code(CLI)逐任務執行。
>
> **落地策略**:輕量起步(Git + GitHub Actions),文件含完整版(K8s / ArgoCD / Kyverno)演進路線圖。
>
> **版本**:v1.0 | **最後更新**:2026-06

---

## 0. 如何使用本文件(給 Claude Code 的執行指引)

本文件每個任務都標註了 `[TASK-xx]` 編號。在 Claude CLI 中,你可以逐一下達:

```
讀取 PROJECT_PLAN.md,執行 [TASK-01],完成後停下來讓我確認。
```

每個任務包含:**目標 / 前置條件 / 具體步驟 / 驗收標準 / 對應的治理控制項**。
請嚴格按 Phase 順序執行,不要跳階段。每個 Phase 結束有一個 **Gate(關卡檢查)**,通過才進下一階段。

---

## 1. 專案背景與核心理念

### 1.1 要解決的組織矛盾

本平台存在的根本目的,是同時滿足兩個傳統上互相衝突的需求:

- **速度**:讓開發者能自助、快速地取得環境與部署能力,不必層層等待。
- **合規**:每個產出都必須符合 ISO 27001(資安)與 ISO 20000(服務管理)的要求,且全程可稽核。

傳統做法用「人工審核關卡」來達成合規,代價是慢。本平台用「自動化護欄」取代「人工閘門」,在不犧牲速度的前提下達成 **100% 覆蓋、即時、可追溯** 的管控。

### 1.2 三個指導理念

1. **護欄,而非閘門(Guardrails, not Gates)**
   合規規則寫成程式碼,自動執行。開發者在安全範圍內自由行動,不合規的產出根本無法生成。

2. **平台即產品(Platform as a Product)**
   內部開發者是「客戶」。衡量成功的是採用率與開發者體驗,不是平台的技術複雜度。

3. **降低認知負荷(Reduce Cognitive Load)**
   平台吸收基礎設施、資安、合規的複雜性,讓開發者只需專注業務邏輯。

### 1.3 治理立場(對稽核的核心論述)

> 「我們沒有取消管控。我們把管控從『人工、事後、抽樣』,轉變為『自動、即時、全面』。
> 每個變更都比過去更可追溯;合規從『靠人記得做』變成『系統強制做到』。」

---

## 2. 範圍與非範圍

### 2.1 範圍(本計畫涵蓋)
- 自助式專案範本(降低認知負荷)
- 政策即程式碼的自動合規檢查(護欄)
- Git 為唯一真相來源的變更管理(可追溯)
- 技術控制項對應 ISO 27001 / 20000 的稽核證據產出

### 2.2 非範圍(本計畫不涵蓋,避免失焦)
- 正式生產環境的部署(本計畫為 PoC / 雛形)
- 真實客戶資料(全程使用測試資料)
- 取代既有的正式變更管理流程(本計畫為「標準變更」的補強,非取代)

---

## 3. 演進路線圖(輕量 → 完整)

| 階段 | 技術載體 | 體現的 PE 概念 | 對應治理 |
|------|----------|----------------|----------|
| **Phase 1(本計畫主體)** | GitHub Template Repo | 自助範本 | ISO 20000 服務目錄 / 標準變更 |
| **Phase 1** | GitHub Actions(policy checks) | 政策即程式碼 | ISO 27001 存取控制 / 變更可追溯 |
| **Phase 1** | Git 歷史 + PR 流程 | GitOps 雛形 | ISO 20000 變更管理 |
| **Phase 2(演進)** | Terraform 模組(預設合規) | 基礎設施自助化 | ISO 27001 Secure by Default |
| **Phase 3(演進)** | kind/AKS + ArgoCD | 完整 GitOps | 設定偏移自動校正 |
| **Phase 3** | Kyverno / OPA | K8s 層級政策即程式碼 | 全面性護欄 |
| **Phase 4(演進)** | Backstage | 統一開發者入口 | 完整服務目錄 |

> **重要**:Phase 1 學到的概念(自助、護欄、Git 為真相來源),
> 在 Phase 2-4 是「同一件事的重型版」,不是全新概念。先把肌肉練在輕量層。

---

## 4. 技術棧(分階段)

### Phase 1(只需這些,皆為你已熟悉或極易上手)
- **Git / GitHub**:範本與真相來源
- **GitHub Actions**:政策即程式碼的執行引擎
- **YAML**:workflow 與政策設定
- **Shell / Python**:檢查腳本與稽核證據產出

### Phase 2+（演進時才需要)
- Terraform / Bicep(IaC,你已有底子)
- kind → AKS(Kubernetes)
- ArgoCD(GitOps)
- Kyverno / OPA(政策即程式碼,K8s 層)
- Backstage(開發者入口)

---

## 5. 詳細工作分解(Phase 1)

### Phase 1-A:建立自助範本(體現「降低認知負荷」)

---

#### [TASK-01] 初始化專案儲存庫結構

**目標**:建立一個結構清晰、可作為「黃金路徑」起點的 repo。

**前置條件**:本機已安裝 Git;有 GitHub 帳號。

**步驟**:
1. 建立 repo 根目錄結構(見 `STRUCTURE.md`)。
2. 加入 `README.md`、`.gitignore`、`LICENSE`、`CODEOWNERS`。
3. 初始化 git,首次 commit。

**驗收標準**:
- repo 可被 clone,結構符合 `STRUCTURE.md`。
- `CODEOWNERS` 已定義「誰能改政策」與「誰能用範本」的分離(SoD 基礎)。

**對應治理控制項**:
- ISO 27001 A.5.15(存取控制)— 透過 CODEOWNERS 實踐職責分離
- ISO 20000 服務管理 — 建立服務的基礎結構

---

#### [TASK-02] 建立標準專案範本(Template Repository)

**目標**:讓開發者能「點一下」就生出一個合規的新專案,不必自己從零搭建。

**步驟**:
1. 在範本中內建:標準資料夾結構、CI 設定檔骨架、README 範本、必要的合規設定檔。
2. 在 GitHub repo 設定中啟用 **Template repository**。
3. 撰寫 `scaffold/` 說明,定義範本包含哪些「預設合規」內容。

**驗收標準**:
- 從範本生成的新專案,自動帶有 CI 與合規檢查,無需手動設定。
- 文件清楚說明「這個範本替開發者省掉了哪些原本要自己操心的事」。

**對應治理控制項**:
- ISO 20000 — 服務目錄(Service Catalogue):範本即活的服務目錄項目
- ISO 20000 — 標準變更(Standard Change):預先核准、可重複、低風險

**治理論述**:此範本即 ISO 20000 定義的「標準變更」——預先核准的低風險可重複變更,
依框架本就不需要每次走完整 CAB 審核。這不是繞過變更管理,是實踐其最進步的形態。

---

### Phase 1-B:建立政策即程式碼護欄(體現「護欄而非閘門」)

---

#### [TASK-03] 機敏資訊掃描守門員

**目標**:任何 PR 中若含寫死的密碼 / 金鑰 / Token,自動擋下,不靠人工 review。

**步驟**:
1. 建立 `.github/workflows/policy-secrets.yml`。
2. 整合 secret scanning(如 gitleaks 或 GitHub 內建 secret scanning)。
3. 設定:偵測到機敏資訊 → 檢查失敗 → PR 無法合併。
4. 撰寫一個「故意違規」的測試 PR,證明它會被擋。

**驗收標準**:
- 含假金鑰的 PR 被自動擋下,檢查狀態為 failed。
- 乾淨的 PR 順利通過。
- 留下可稽核的執行紀錄(Actions log)。

**對應治理控制項**:
- ISO 27001 A.8.12(資料外洩防護)
- ISO 27001 A.5.15 / A.8.2 — 防止憑證外洩
- 銀行特別關注:防止金鑰進入版控,降低憑證外洩風險

---

#### [TASK-04] 結構與命名規範守門員

**目標**:強制專案符合組織規範(命名、必要文件、結構),不合規無法合併。

**步驟**:
1. 建立 `.github/workflows/policy-structure.yml`。
2. 撰寫檢查腳本(`scripts/check_structure.py`):驗證必要檔案存在、命名符合規範。
3. 每個規則的程式碼註解中,標註它對應的 ISO 控制項編號。

**驗收標準**:
- 缺少必要文件的 PR 被擋下,並給出明確的修正提示。
- 每條規則可追溯到一個治理控制項。

**對應治理控制項**:
- ISO 20000 — 服務管理一致性
- ISO 27001 A.5.37(文件化操作程序)

---

#### [TASK-05] 政策變更的職責分離(SoD)強化

**目標**:確保「改政策的人」與「用政策的人」分離——這是稽核最常挑的弱點。

**步驟**:
1. 在 `CODEOWNERS` 中,將 `.github/workflows/` 與 `policies/` 目錄的審核權,
   指定給「平台 + 資安」群組(非一般開發者)。
2. 設定 branch protection:修改政策檔的 PR 需要指定群組額外核准。
3. 文件化:一般開發者可「使用」護欄(受其約束),但「修改護欄」需更嚴格審核。

**驗收標準**:
- 一般開發者無法單獨修改政策規則。
- 政策變更留下獨立、更嚴格的審核軌跡。

**對應治理控制項**:
- ISO 27001 A.5.3(職責分離)— 核心
- ISO 27001 A.8.4(原始碼存取控制)

**治理論述**:若同一人能改規則、又能核准、又能部署,護欄形同虛設。
本任務確保護欄本身的變更受更嚴格管控,SoD 不但沒破,反而比人工流程更清晰可稽核。

---

### Phase 1-C:變更管理與可追溯性(體現「GitOps 雛形」)

---

#### [TASK-06] PR 流程即變更管理

**目標**:讓每個變更都是一個有紀錄、有審核、可回溯的 Git 事件。

**步驟**:
1. 建立 PR 範本(`.github/pull_request_template.md`),要求填寫:變更目的、風險、回退方案。
2. 設定 branch protection:main 分支禁止直接 push,必須經 PR。
3. 要求所有 PR 通過 Phase 1-B 的全部政策檢查才能合併。

**驗收標準**:
- 無法繞過 PR 直接改 main。
- 每個合併都有:誰改的、改什麼、為什麼、誰核准的——完整紀錄。

**對應治理控制項**:
- ISO 20000 — 變更管理(Change Management)
- ISO 27001 A.8.32(變更管理)

---

#### [TASK-07] 稽核證據自動產出

**目標**:把 Git / Actions 的技術紀錄,轉譯成稽核員看得懂的「合規證據」。

**步驟**:
1. 建立 `scripts/generate_audit_report.py`:
   - 蒐集指定期間的所有 PR、核准者、政策檢查結果。
   - 輸出一份對應 ISO 控制項的證據報告(Markdown / CSV)。
2. 將每條政策規則對應到 ISO 控制項編號(見 `COMPLIANCE_MAP.md`)。
3. 設定可定期(或按需)產生此報告。

**驗收標準**:
- 能產出一份報告,證明「期間內所有變更都經過 X 項合規檢查,通過率 / 攔截紀錄」。
- 報告中每項控制都對應到具體 ISO 編號。

**對應治理控制項**:
- ISO 27001 A.5.36(合規性審查)
- ISO 20000 — 服務報告(Service Reporting)
- 這層「技術控制 ↔ 框架控制項」的翻譯,是本計畫對銀行的最大價值。

---

## 5-D. Phase D 工作分解 — 部署黃金路徑(需求單 → OpenLiberty)

> 本階段把 Phase 1 的治理骨架(變更/SoD/稽核) + Phase 2 的 IaC 護欄模式,延伸成一條
> 「**開發者提服務請求 → 應用安全部署上 OpenLiberty**」的端到端黃金路徑,並串接 supply-chain 專案。
> 設計與框架對映見 `docs/golden-path-request-to-deploy.md`;技術決策見 `docs/adr/0002-openliberty-runtime-and-deploy.md`。
> 執行慣例同前:逐 TASK、每步停下確認、不跳階段。

---

#### [TASK-D1] 服務目錄與服務請求單(ITIL 請求履行)

**目標**:讓開發者用一張結構化表單提出「部署到 OpenLiberty」的請求,即服務目錄裡一個預核准的標準服務。

**前置條件**:Phase 1 完成(PR 流程、SoD 已就位)。

**步驟**:
1. 建立 `.github/ISSUE_TEMPLATE/service-request.yml`(Issue Form):欄位含應用名、來源 artifact/版本、目標環境、商業理由、資料分級(模擬)。
2. 在 `scaffold/docs/` 或服務目錄文件登錄此項目為「標準變更」。
3. 文件化此請求如何轉為後續 PR(TASK-D2 銜接)。

**驗收標準**:能開出一張格式正確、欄位齊全的服務請求單;文件說明其為預核准標準變更。

**對應治理控制項**:ISO 20000 服務目錄 / 服務請求(Request Fulfillment);ISO 20000 標準變更。

---

#### [TASK-D2] 請求轉變更(PR)的銜接(ISO 20000 / ISO 27001 變更管理)

**目標**:把服務請求單轉成一個有目的/風險/回退、需通過所有護欄、可追溯的變更(PR)。

**步驟**:
1. 定義「請求單 → PR」的對應(可手動或後續自動化),PR 沿用 Phase 1 PR 範本與 main 保護。
2. 確認部署相關變更一律走 PR,護欄變更額外需平台+資安核准(沿用 TASK-05)。

**驗收標準**:一張請求單能對應到一個合規 PR;無法繞過 PR 觸發部署。

**對應治理控制項**:ISO 27001 A.8.32;ISO 20000 變更管理。

---

#### [TASK-D3] OpenTofu 模組:openliberty-service(Secure by Default)

**目標**:用 OpenTofu「填參數即開出一個預設安全的 OpenLiberty(Podman 容器)執行環境」。

**前置條件**:ADR-0002 核准;本機有 OpenTofu + Podman。

**步驟**:
1. 在 `iac/modules/openliberty-service/` 建模組:Podman 容器跑 OpenLiberty 官方映像,預設安全(非 root、資源上限、健康檢查、無明文機密、最小權限)。
2. 在 `iac/examples/` 加 golden-path 範例;`iac/tests/violation/` 加違規測試。
3. checkov(必要時 tfsec)掃描,沿用 `iac/.checkov.yaml` 的可稽核豁免(SoA)模式,每條豁免附理由。

**驗收標準**:`tofu apply` 能在本機開出可連的 OpenLiberty;checkov 對模組通過,違規範例被擋。

**對應治理控制項**:ISO 27001 Secure by Default;IaC 政策即程式碼(護欄)。

---

#### [TASK-D4] 供應鏈建置 + 簽章(ISMS / 補 supply-chain L4)

**目標**:把 Java 應用建成可驗證來源的容器映像:build → SBOM → SCA 掃描 → cosign 簽章。

**前置條件**:`supply-chain/github/app/backend`(Java/Maven)可建置;cosign 金鑰對已產(私鑰本地保管,絕不進版控)。

**步驟**:
1. 建置應用容器映像。
2. 產 SBOM(CycloneDX/SPDX)、跑 SCA 掃描。
3. `cosign sign` 簽章(金鑰選型見 ADR-0002);公鑰入庫供驗章。
4. `.gitignore` + gitleaks 確保私鑰不進版控。

**驗收標準**:產出帶 SBOM + 掃描結果 + 有效簽章的映像;私鑰確認未進版控。

**對應治理控制項**:ISO 27001 A.8.28(安全開發/供應鏈);供應鏈完整性。

---

#### [TASK-D5] 部署前驗章閘門(fail-closed)

**目標**:部署前強制驗證,任一不過即拒絕部署並留痕。

**步驟**:
1. 驗章閘門檢查:`cosign verify` 通過 + SCA 無高風險 + 該 artifact 在 CMDB 有對應 CI。
2. 設為 fail-closed:任一不過 → 阻擋部署 + 記錄攔截。
3. 加一個「故意未簽/未登錄」的反例,證明會被擋。

**驗收標準**:已簽且合規的映像放行;未簽/有高風險/未登錄的被擋,留下攔截紀錄。

**對應治理控制項**:ISO 27001 完整性控制;ITIL 發布驗證 / 部署前檢查。

---

#### [TASK-D6] 部署到 OpenLiberty + 煙霧測試(ISO 20000 發布與部署管理)

**目標**:把已驗章的 artifact 部署到 TASK-D3 開出的 OpenLiberty,並驗證可服務。

**步驟**:
1. 部署映像到 OpenLiberty runtime。
2. 煙霧測試:打應用端點確認回 200 / 預期回應。
3. 記錄部署結果(成功/失敗、版本、時間)。

**驗收標準**:應用在 OpenLiberty 上可正常回應;煙霧測試通過並留紀錄。

**對應治理控制項**:ISO 20000 發布與部署管理。

---

#### [TASK-D7] 組態管理(CMDB-as-code)+ 端到端稽核證據

**目標**:把這次部署登錄為組態項目(CI),並把整條鏈串成對映 ISO 的稽核證據。

**步驟**:
1. 建 `cmdb/` 與 CI schema:應用、版本、artifact digest、簽章、OpenLiberty 實例、環境、關係;加 `scripts/cmdb_validate.py` 與驗證 workflow。
2. 部署成功後登錄/更新對應 CI(版控即組態基線與變更史)。
3. 擴充 `scripts/generate_audit_report.py`:把「請求 → PR → 建置/SBOM/掃描/簽章 → 驗章 → 部署 → CMDB」串成一份對映 ISO 控制項的報告。

**驗收標準**:CMDB 正確記錄本次部署的 CI 與關係;能產出涵蓋七階段、每項對映 ISO 編號的端到端證據報告。

**對應治理控制項**:ISO 20000 組態管理;ISO 27001 A.8.9(組態管理)、A.5.36(合規審查);ISO 20000 服務報告。

---

## 6. Phase Gate(階段關卡檢查)

每階段結束,需確認以下才可進入下一階段:

### Gate 1(Phase 1 完成檢查)
- [ ] 範本可自助生成合規專案(TASK-01, 02)
- [ ] 機敏掃描與結構檢查能自動攔截違規(TASK-03, 04)
- [ ] 政策變更受 SoD 保護(TASK-05)
- [ ] main 分支受 PR 流程保護(TASK-06)
- [ ] 能產出對應 ISO 的稽核證據報告(TASK-07)
- [ ] 已準備一份給資安/稽核的提案說明(見 `GOVERNANCE_BRIEF.md`)

> 通過 Gate 1 後,才考慮 Phase 2(Terraform 模組化)。
> 不要在概念還沒練熟前就跳進 K8s。

### Gate D(Phase D 部署黃金路徑完成檢查)
- [ ] 能開出服務請求單,且定位為預核准標準變更(TASK-D1)
- [ ] 請求能轉成合規 PR,無法繞過 PR 觸發部署(TASK-D2)
- [ ] OpenTofu 能開出預設安全的 OpenLiberty,checkov 通過、違規被擋(TASK-D3)
- [ ] 應用映像帶 SBOM + 掃描 + cosign 簽章,私鑰未進版控(TASK-D4)
- [ ] 部署前驗章閘門 fail-closed:未簽/高風險/未登錄被擋(TASK-D5)
- [ ] 已驗章 artifact 部署上 OpenLiberty 且煙霧測試通過(TASK-D6)
- [ ] CMDB 登錄本次 CI;能產出涵蓋七階段、對映 ISO 的端到端證據報告(TASK-D7)

> 全數打勾 = 一張服務請求單能自動走到 app 跑在 OpenLiberty 上,且全程可稽核。

---

## 7. 風險與緩解

| 風險 | 緩解措施 |
|------|----------|
| 開發者覺得護欄是阻礙,不採用 | 以「平台即產品」思維,蒐集回饋、優化體驗;讓護欄盡量無感 |
| 稽核員看不懂技術控制 | TASK-07 的證據報告做「翻譯層」,對應 ISO 編號 |
| SoD 被質疑 | TASK-05 明確分離政策變更權限 |
| 範圍蔓延、跳階段 | 嚴守 Phase Gate,通過才前進 |
| 自動化護欄本身有漏洞 | 護欄規則需有測試、版控、變更審核(視同程式碼) |

---

## 8. 後續演進(Phase 2-4 摘要)

- **Phase 2**:把 Terraform 包成「填參數就開出合規資源」的模組,合規寫進預設值。
- **Phase 3**:導入 kind(本機)→ AKS,加上 ArgoCD 做完整 GitOps,Kyverno 做 K8s 層護欄。
- **Phase 4**:用 Backstage 把範本與服務目錄縫成統一入口。

每個 Phase 的詳細任務,待 Phase 1 通過 Gate 後再展開。

---

## 附錄:配套文件清單
- `STRUCTURE.md` — repo 結構定義
- `COMPLIANCE_MAP.md` — 技術控制 ↔ ISO 27001 / 20000 對照表
- `GOVERNANCE_BRIEF.md` — 給資安 / 稽核 / 主管的提案說明
- `CLAUDE.md` — 給 Claude Code 的專案脈絡與執行慣例
- `docs/golden-path-request-to-deploy.md` — Phase D 部署黃金路徑設計與框架對映
- `docs/service-catalogue.md` — 服務目錄（TASK-D1）
- `docs/request-to-change.md` — 請求→變更 程序（TASK-D2）
- `docs/tooling-roles-and-real-world-mapping.md` — itops × GitHub × 企業 ITSM 角色與正式環境對映
- `docs/supply-chain-signing.md` — 供應鏈 build/SBOM/掃描/簽章（TASK-D4）
- `trust/README.md` — 簽章信任根（cosign 公鑰）
- `docs/adr/0001-phase2-iac-stack.md` — Phase 2 IaC 技術棧決策
- `docs/adr/0002-openliberty-runtime-and-deploy.md` — Phase D 執行環境與部署/簽章決策
