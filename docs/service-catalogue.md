---
title: 服務目錄（Service Catalogue）
type: reference
created: 2026-06-14
updated: 2026-06-14
tags: [iso20000, itil, service-catalogue, request-fulfillment, standard-change]
---

# 服務目錄（Service Catalogue）

> ISO 20000 / ITIL 的**服務目錄**＝「平台對開發者公開、可自助請求的服務清單」。
> 每個項目都是一個**預核准的標準變更（Standard Change）**：低風險、可重複、依框架本就免逐次 CAB。
> 本目錄是「活的、可用的」——每個項目都對應一個真實可送出的入口（GitHub Issue Form）。
>
> 對應 `PROJECT_PLAN.md` [TASK-D1]；整體流程見 `docs/golden-path-request-to-deploy.md`。

## 目錄項目

### SVC-001 — 部署應用到 OpenLiberty 沙箱

| 屬性 | 內容 |
|---|---|
| **服務類型** | 標準變更（Standard Change，預核准） |
| **入口** | [服務請求 Issue Form](../.github/ISSUE_TEMPLATE/service-request.yml)（GitHub → New issue → 「服務請求 — 部署應用到 OpenLiberty」） |
| **請求者** | 開發者（自助） |
| **核准** | 預先核准（範本與流程已經平台+資安一次性審核）；不需逐次 CAB |
| **產出** | 一個跑在 OpenLiberty 上、經簽章驗證、已登錄 CMDB 的應用實例 |
| **前提** | 來源 artifact 通過供應鏈建置/SBOM/SCA/cosign 簽章；部署前驗章通過（fail-closed） |
| **環境** | `openliberty-sandbox`（PoC 唯一環境，本機 Podman 容器） |
| **SLA（模擬）** | 自助、即時觸發；以自動化流程完成，無人工搬運瓶頸 |

**治理意涵**：此項目即 ISO 20000 服務目錄的一個條目，也是「標準變更」的具體實踐——
預核准、低風險、可重複，不需每次走完整變更審核委員會（CAB）。這不是繞過變更管理，
是其最進步的形態（與 `scaffold/docs/golden-path.md` 對「建專案」的論述一致）。

## 從「服務請求」到「變更」的銜接

```
開發者送出 Service Request (Issue Form)
        │  ITIL 請求履行 / ISO 20000 服務請求
        ▼
轉為一個 PR（變更紀錄：目的 / 風險 / 回退）   ← TASK-D2
        │  ISO 27001 A.8.32 / ISO 20000 變更管理
        ▼
通過所有護欄 + 供應鏈簽章 + 部署前驗章後才落地
        │  ISMS / fail-closed
        ▼
部署到 OpenLiberty → 登錄 CMDB → 產稽核證據     ← TASK-D6 / D7
```

> 「請求 → 變更」的具體對應機制（手動或自動化）在 [TASK-D2] 定義與落實。

## 對應治理控制項

| 控制項 | 在本目錄如何體現 |
|---|---|
| ISO 20000 服務目錄 | 本文件即活的服務目錄 |
| ISO 20000 服務請求（Request Fulfillment） | 結構化 Issue Form 作為自助入口 |
| ISO 20000 標準變更 | 每個項目為預核准、低風險、可重複的變更 |
| ISO 27001 A.5.3 職責分離 | 開發者「請求/使用」，平台+資安「維護目錄與護欄」 |

## See Also
- `docs/golden-path-request-to-deploy.md`（部署黃金路徑全貌）
- `.github/ISSUE_TEMPLATE/service-request.yml`（本目錄項目的入口）
- `scaffold/docs/golden-path.md`（建專案黃金路徑，互補）
- `COMPLIANCE_MAP.md`（技術控制 ↔ ISO 對照）
