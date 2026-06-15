# deployments/ — 部署請求即程式碼（Deployment-Request-as-Code）

> 這個目錄是「**變更的真相來源**」。每一個檔案 = 一個應用在某環境的**期望部署狀態**。
> 服務請求單（`docs/service-catalogue.md`）一旦受理，就轉為一個 **PR**，在此目錄
> 新增 / 更新一個 `DeploymentRequest` 檔——**這個 PR 就是 ISO 20000 / ISO 27001 A.8.32
> 意義下的「變更紀錄」**：有目的、風險、回退、審核、可回溯。

## 為什麼用「宣告式檔案」而非「按一顆部署鈕」

- **可追溯**：每次部署都是一個 Git commit / PR，誰改的、改什麼、為什麼、誰核准，全留痕。
- **可回退**：`git revert` 即回到上一個已知良好狀態（GitOps 雛形）。
- **可稽核**：版控史天然就是組態基線與變更史（銜接 [TASK-D7] CMDB）。

> Java 類比：像把部署參數從「執行時手動敲」搬進 `application.yaml` 並納入版控——
> 環境狀態變成可審查、可 diff、可回溯的程式碼。

## 目錄慣例

```
deployments/
└── <環境>/                       # 目前僅 openliberty-sandbox（PoC 唯一環境）
    └── <應用名>.yaml             # 一個應用一份 DeploymentRequest
```

## DeploymentRequest 欄位（schema 草案）

| 欄位 | 意義 | 由哪個 TASK 寫入 |
|---|---|---|
| `metadata.app` | 應用識別名 | D2（請求時） |
| `metadata.environment` | 目標環境 | D2 |
| `metadata.serviceRequest` | 關聯的服務請求 issue 編號（可追溯） | D2 |
| `metadata.requestedBy` | 請求者角色（SoD） | D2 |
| `metadata.changeType` | 變更分類 `standard｜normal｜emergency｜retroactive`（缺＝standard） | E1 |
| `metadata.priority` | 優先序 `P1..P4`（插單用） | E1 |
| `metadata.justification` | 例外理由（emergency/retroactive 必填） | E1 |
| `metadata.expedite` | 插單授權 `{by, reason}`（誰批＋為何加急） | E1 |
| `metadata.pir` | 急件 PIR 承諾 `{owner, dueBy}`（emergency 必填；合併後自動開 PIR issue） | E2 |
| `spec.source.artifact` / `version` | 來源映像與版本 | D2 |
| `spec.source.digest` | 簽章後的 image digest（`sha256:...`） | D4（簽章後回填） |
| `spec.dataClassification` | 資料分級（模擬） | D2 |
| `spec.runtime` | OpenLiberty runtime 參數（給 D3 OpenTofu 模組消費） | D3 |

> 此檔串起整條黃金路徑：D3 佈建讀它、D4 回填 digest、D5 驗章比對它、D6 部署它、D7 據它登錄 CMDB。

## 範例

見 `openliberty-sandbox/supply-chain-backend.yaml`（值皆為公開 PoC 假值）。

## See Also
- `docs/request-to-change.md`（請求 → 變更 的完整程序）
- `docs/service-catalogue.md`（服務請求入口）
- `docs/golden-path-request-to-deploy.md`（全貌）
