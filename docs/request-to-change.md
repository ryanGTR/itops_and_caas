---
title: 從服務請求到變更（Request → Change）
type: howto
created: 2026-06-14
updated: 2026-06-14
tags: [itil, iso20000, iso27001, change-management, gitops, request-fulfillment]
---

# 從服務請求到變更（Request → Change）

> 對應 `PROJECT_PLAN.md` [TASK-D2]。本文件定義「一張服務請求單」如何轉成「一個可追溯的變更（PR）」，
> 把 ITIL 請求履行接到 ISO 20000 / ISO 27001 A.8.32 的變更管理。

## 為什麼要這一步

服務請求（[TASK-D1] 的 Issue Form）是「**意圖**」；變更（PR）是「**受控的執行**」。
中間這一步把意圖轉成一個有目的/風險/回退、通過護欄、留下審核軌跡的 Git 事件——
這就是把「請求」納入變更管理的銜接點。

## 程序（目前：手動；可後續自動化）

```
① 服務請求 (Issue Form, SVC-001)          ITIL 請求履行 / ISO 20000 服務請求
        │
        ▼
② 開分支 + 在 deployments/<環境>/<app>.yaml
   新增/更新一個 DeploymentRequest          部署請求即程式碼（變更的真相來源）
        │
        ▼
③ 開 PR：填 目的/風險/回退 + 關聯服務請求    ISO 20000 / ISO 27001 A.8.32 變更管理
        │
        ▼
④ 通過全部護欄（secrets / structure / iac） 護欄而非閘門
        │   護欄變更另需平台+資安核准（SoD）  ISO 27001 A.5.3
        ▼
⑤ 合併 = 已核准的標準變更                    可追溯：誰改/改什麼/為什麼/誰核准
```

> 之所以「手動也成立」：DeploymentRequest 是宣告式檔案，PR 是標準變更流程——
> 兩者都已就位，差別只在「②③ 由人做還是由 workflow 自動產生」。自動化是體驗優化（平台即產品），
> 非合規前提。自動化版本可作為後續增強（依 Issue 事件自動開出對應 PR）。

## 可追溯性（Traceability）兩端對接

- **請求 → 變更**：DeploymentRequest 的 `metadata.serviceRequest` 記錄來源 issue 編號；
  PR 範本新增「關聯服務請求」欄填同一個 issue。雙向可查。
- **變更 → 部署 → 組態**：合併後的這個檔，後續被 [TASK-D3]~[TASK-D6] 消費、[TASK-D7] 據以登錄 CMDB。

## 規則

1. **部署相關變更一律走 PR**：不可直接 push main（main 受保護，沿用 [TASK-06]）。
2. **PR 必填**：變更目的、風險、回退、關聯服務請求。
3. **護欄變更更嚴格**：動到 `policies/`、`.github/workflows/`、`scripts/`、`.gitleaks.toml`、
   `CODEOWNERS`、`tests/` 需平台+資安額外核准（[TASK-05] SoD）。

## 對應治理控制項

| 控制項 | 體現 |
|---|---|
| ISO 20000 變更管理 | 每次部署＝一個 PR 變更 |
| ISO 27001 A.8.32 變更管理 | PR 必填目的/風險/回退 |
| ISO 27001 A.5.3 職責分離 | 護欄變更需額外核准；請求者角色入檔 |
| ISO 20000 服務請求 ↔ 變更 銜接 | serviceRequest 欄 + PR 關聯欄雙向追溯 |

## See Also
- `deployments/README.md`（部署請求即程式碼）
- `docs/service-catalogue.md`（請求入口）
- `.github/pull_request_template.md`（變更紀錄欄位）
- `docs/golden-path-request-to-deploy.md`（全貌）
