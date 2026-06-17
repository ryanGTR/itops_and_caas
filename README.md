# itops_and_caas — 銀行內部開發者平台(IDP)Phase 1 雛形

> Platform Engineering × ISO 27001 / ISO 20000 治理對齊
> **進度**:Phase 1 + 2 + D + E + F 全數落地(原始碼 → IaC → 部署 → 例外 → 多環境晉級)
>
> 👉 **想快速理解這個專案**,先讀 [`docs/case-study.md`](./docs/case-study.md)(一頁案例:把治理從「人工審核」重寫成「自動護欄」)。
>
> 📢 **這是公開的學習用 PoC(proof-of-concept)**,用來示範一個銀行內部開發者
> 平台「該長什麼樣」。**不含任何真實資料或憑證**,文件中的「內部/機密」字眼
> 屬於模擬情境,非真實機密分級。詳見 [`LICENSE`](./LICENSE)。

本 repo 是一個銀行內部開發者平台(Internal Developer Platform)的 Phase 1 雛形。
核心不是「裝工具」,而是用最輕的技術(Git + GitHub Actions)體現 Platform
Engineering 的三個理念,並嚴格對齊 ISO 27001(資安)與 ISO 20000(服務管理),
產出可稽核的證據。

## 三個指導理念

1. **護欄,而非閘門(Guardrails, not Gates)** — 合規規則寫成程式碼自動執行,
   不合規的產出根本無法生成,而非靠人工事後 review。
2. **平台即產品(Platform as a Product)** — 內部開發者是「客戶」,衡量成功的是
   採用率與開發者體驗。
3. **降低認知負荷(Reduce Cognitive Load)** — 平台吸收基礎設施、資安、合規的
   複雜性,讓開發者只專注業務邏輯。

## 如何使用本平台

> Phase 1 + 2 + D + E + F 的能力均已落地;部署黃金路徑已**真 live 端到端跑通**(見 [`docs/case-study.md`](./docs/case-study.md) 第五節)。

- **要開新專案**:從 `scaffold/`(TASK-02)提供的範本一鍵生成,自動帶 CI 與合規檢查。
- **要部署 app 到 OpenLiberty**:從服務目錄(`docs/service-catalogue.md`)送出**服務請求單**(Issue Form),平台會把它轉為變更並走治理化部署流程。詳見 `docs/golden-path-request-to-deploy.md`。
- **想知道有哪些護欄**:見 `policies/`(TASK-03 起),每條規則都對應一個 ISO 控制項。
- **稽核 / 提案**:見 `COMPLIANCE_MAP.md`(ISO 對照)與 `GOVERNANCE_BRIEF.md`(提案說明)。

## 儲存庫結構

完整結構定義見 [`STRUCTURE.md`](./STRUCTURE.md)。重點:

| 路徑 | 用途 | 變更權限(SoD) |
|------|------|----------------|
| `scaffold/` | 自助專案範本(「用護欄」) | 一般開發者可貢獻 |
| `policies/` | 政策即程式碼(「改護欄」) | 平台 + 資安群組 |
| `.github/workflows/` | 護欄執行引擎 | 平台 + 資安群組 |
| `scripts/` | 結構檢查 / 稽核證據產出工具 | 平台 + 資安群組 |

權限分離由 [`CODEOWNERS`](./CODEOWNERS) 落實,這是職責分離(Separation of
Duties)的技術核心。

## 文件導覽

| 檔案 | 給誰看 | 內容 |
|------|--------|------|
| `docs/case-study.md` | 想快速理解 / 面試 | 一頁案例:人工審核 → 自動護欄,Phase 1→F 全貌 + 真 live 驗證 |
| `docs/everything-as-code-journey.md` | 想理解整合脈絡 | 「X as code」如何層層整合進 itops 的全歷程 + 治理價值鏈 |
| `docs/framework-conformance-assessment.md` | 稽核 / 資安 / 面試 | ISMS/ISO20000/ITIL 精神符合度**誠實自評** + 逐項**系統落地解法**(規定→資料欄位→閘門→物證);附「控制項↔系統綁定」對照表與給公司的落地模式 |
| `docs/governance-console.html` | 稽核 / 主管 / demo | 治理後台(鳥瞰):開單→變更→換版軌跡→執行→關單 的單據生命週期;頂部「其它治理視圖」入口可跳拓樸圖 / 單據追溯(firefox 開) |
| `docs/cmdb-topology.html` | 稽核 / 工程 | CMDB 拓樸:host → middleware → software 多層 CI 關係圖(可「← 回治理後台」) |
| `docs/ticket-34.html` | 稽核 / 工程 | 單據追溯(鑽取):單一服務請求從開單到關單的證據鏈;`scripts/ticket_trace.py --issue <n>` 可生其它單(可「← 回治理後台」) |
| `TODO.md` | 工程 / 接續 | 待辦 backlog + 「斷 session 如何接續」指南 |
| `integration/handoff-contract.md` | 工程 | supply-chain → itops 交接契約(整合邊界) |
| `PROJECT_PLAN.md` | 工程 + 治理 | 完整工作分解,逐 `[TASK-xx]` 執行 |
| `STRUCTURE.md` | 工程 | repo 結構定義 |
| `COMPLIANCE_MAP.md` | 稽核 / 資安 | 技術控制 ↔ ISO 27001 / 20000 對照表 |
| `GOVERNANCE_BRIEF.md` | 主管 / 稽核 | 提案說明 |
| `CLAUDE.md` | Claude Code | 專案脈絡與執行慣例 |

## 環境需求

- Git
- (後續 TASK)GitHub 帳號、GitHub Actions、Python 3、Shell

## 授權

公開的學習用 PoC,可自由使用、修改、學習,見 [`LICENSE`](./LICENSE)。
