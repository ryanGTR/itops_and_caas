# policies/ — 政策即程式碼(受 SoD 保護)

> 本目錄收錄平台的「護欄」政策。**改這裡的東西 = 改護欄**,
> 需平台 + 資安群組依職責分離(SoD)審核。

## 一、政策清單與對應 ISO 控制項

| 政策 | 載體 | 對應 ISO 控制項 | 任務 |
|------|------|----------------|------|
| 機敏資訊掃描 | `.github/workflows/policy-secrets.yml` + `.gitleaks.toml` | ISO 27001 A.8.12 / A.5.17 | TASK-03 |
| 結構與命名規範 | `.github/workflows/policy-structure.yml` + `scripts/check_structure.py` | ISO 27001 A.5.37 / A.5.3、ISO 20000 | TASK-04 |
| 職責分離強制 | `CODEOWNERS` + `scripts/setup_branch_protection.sh` | ISO 27001 A.5.3 / A.8.4 | TASK-05 |

> `policies/rules/` 預留給未來「每條規則獨立成檔」的細化(Phase 2+),目前規則
> 內嵌於上述載體中。

## 二、職責分離模型:用護欄 vs 改護欄

這是稽核最常挑的弱點,本平台用技術手段明確分離:

| | **用護欄**(一般開發者) | **改護欄**(平台 + 資安) |
|---|--------------------------|---------------------------|
| 能做什麼 | 在 `scaffold/` 貢獻範本、開自己的專案、受護欄約束 | 修改 `policies/`、`.github/workflows/`、`scripts/`、`.gitleaks.toml`、`CODEOWNERS`、`tests/` |
| 審核要求 | 一般 PR review | **必須**由 CODEOWNERS 指定的平台 + 資安群組核准 |
| 強制機制 | branch protection 禁止直接 push main | `require_code_owner_reviews` + `enforce_admins` |
| 對應控制 | — | ISO 27001 A.5.3 職責分離 / A.8.4 原始碼存取控制 |

> **核心論述**:若同一人能改規則、又能核准、又能部署,護欄形同虛設。
> 本模型確保「護欄本身的變更」受比一般程式碼更嚴格的管控——
> SoD 不但沒破,反而比人工流程更清晰可稽核。

## 三、如何讓 SoD 具有強制力(落地步驟)

`CODEOWNERS` 只「指定 owner」,本身不強制。要真正擋住未經授權的政策變更,
須在 GitHub 開啟 branch protection。**此為一次性 GitHub 設定,無法用本機
git 完成**,請由平台 + 資安群組執行:

### 方式 A:用腳本(建議,可版控可稽核)

```bash
REPO="<org>/<repo>" BRANCH="main" ./scripts/setup_branch_protection.sh
```

腳本會設定(關鍵項):

| 設定 | 作用 | 對應控制 |
|------|------|----------|
| `require_code_owner_reviews=true` | 動到政策路徑必須對應 owner(平台+資安)核准 | A.5.3 |
| `enforce_admins=true` | 連 admin 也不能繞過,SoD 不留後門 | A.5.3 |
| 禁止直接 push main(需 PR) | 所有變更走可追溯流程 | A.8.32 / A.8.4 |
| required status checks:`policy-secrets`、`policy-structure` | 兩道護欄須通過才可合併 | A.8.12 / A.5.37 |
| `allow_force_pushes=false`、`allow_deletions=false` | 保護歷史可追溯性 | A.8.4 |

### 方式 B:GitHub UI(手動,不建議)

Settings → Branches → Add branch protection rule → 對 `main` 勾選上表對應選項。
缺點:不可版控、不可稽核、易漏設,違反「policy as code」精神。

## 四、稽核軌跡

開啟上述設定後,任何政策變更都會留下:

- **誰提的**:PR 作者
- **改了什麼**:diff(政策即程式碼,每行可溯源)
- **誰核准的**:CODEOWNERS 指定的平台 + 資安群組(獨立、更嚴格的核准紀錄)
- **護欄是否通過**:required status checks 結果

這份「比一般變更更嚴格的核准軌跡」即驗收標準所要求的證據,
並由 `[TASK-07]` 的稽核報告自動彙整。
