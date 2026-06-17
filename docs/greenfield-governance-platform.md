---
title: Greenfield 治理平台 — 讓紙上合規機制真正有效的技術架構與組織設計
type: reference
created: 2026-06-17
updated: 2026-06-17
tags: [platform-engineering, policy-as-code, gitops, zero-trust, iso27001, iso20000, itil, operating-model, cloud]
sources:
  - docs/framework-conformance-assessment.md（控制→系統綁定的配方）
  - itops_and_caas 本專案（CI/CD→部署治理的窄切片驗證）
---

# Greenfield 治理平台:讓紙上機制真正有效

> **問題**:組織知道規定(ISMS / ISO 20000 / ITIL),也寫成政策文件,但這些機制留在紙上——
> 系統照舊跑、合規靠人工事後補證據。如果有**一次從頭建立的機會**,搭配現代 cloud,
> 該怎麼規劃技術架構,**以及相對應的組織與管理機制要怎麼調整**?
>
> 本文是 itops 專案討論的「拉高一層」總結:itops 只示範了 CI/CD → 部署治理這條**窄切片**;
> 這份描述把同一套原理放大成**整體治理平台 + 組織操作模型**。

---

## 0. 核心原則:合規 by construction,平台即控制

控制不是「事後檢查的文件」,而是**內建在「變更進入系統的唯一通道」上的護欄**。
紙上機制要有效,只有一條路:把每條控制做成**鋪好的路(paved road)** 的護欄,
**離開路 = 明確、被治理的例外**(不是悄悄繞過)。

承接 [`framework-conformance-assessment.md`](framework-conformance-assessment.md) 的配方:
> 每條控制 → ①記錄它的資料欄位 → ②缺它就 fail-closed 的自動閘門 → ③自動產出的物證。

本文回答:**把這個配方做成一個完整平台,長什麼樣;以及要讓它運轉,組織得怎麼變。**

---

## 1. 技術架構(現代 cloud 參考架構,8 層)

由下往上,每層都點名「它讓哪些框架控制從紙上變有效」。

```
8  證據與可觀測平面   ← 連續保證、management-by-exception 儀表板
7  ITSM 平台(營運面)  ← 事件 / 問題 / SLA(CI/CD 不碰的那半)
6  CMDB / 資產清冊     ← 自動 discovery,單一真相
5  Runtime 預設安全    ← secure-by-default(加密/網路/secrets)
4  部署控制平面(右側) ← GitOps + admission control,連續收斂
3  供應鏈左側          ← SLSA:簽章/SBOM/SCA/provenance
2  Policy-as-code 控制平面 ← 控制基線矩陣(治理端擁有的 code)
1  身分基座            ← 一切控制的地基
```

| 層 | 技術選型(雲原生) | 讓哪些控制變有效 |
|---|---|---|
| 1 身分基座 | 雲 IAM + SSO/OIDC + **workload identity**(OIDC 聯邦,CI 零靜態金鑰)、短期憑證 | A.5.15/16/17 存取控制、A.5.3 SoD、所有稽核可歸責性。**沒這層其它全是空的** |
| 2 Policy-as-code 控制平面 | OPA/Gatekeeper 或 Azure Policy / AWS SCP+Config;Conftest 入 pipeline | A.8.32 變更、ISMS 風險為本(分級→控制矩陣版控在此=治理端的 code) |
| 3 供應鏈左側 | SLSA build provenance attestation + Syft(SBOM)+ Grype/Trivy(SCA)+ cosign(keyless/KMS) | A.8.28 供應鏈完整性、A.8.29 開發中測試 |
| 4 部署控制平面 | **GitOps**(Argo CD/Flux)desired-state 收斂 + **admission control**(Kyverno)邊界 fail-close | A.8.28 完整性、A.8.32 變更、ISO 20000 發布與部署。連續(非一次性) |
| 5 Runtime 預設安全 | 加密 at-rest 預設(KMS)、網路分段預設、secrets manager(Vault)、runtime 偵測(Falco) | A.8.24 加密、A.8.20/22 網路、A.8.12 資料外洩。**讓分級矩陣有真旋鈕可轉** |
| 6 CMDB / 資產清冊 | 雲原生 discovery 自動發現 + 服務目錄,連 ITSM | ISO 20000 組態管理、A.8.9。**自動非手維護** |
| 7 ITSM 平台 | ServiceNow / iTop,由平台餵資料(CMDB、變更記錄) | ISO 20000/ITIL 事件、問題、SLA(營運面迴路) |
| 8 證據與可觀測平面 | 集中不可變稽核日誌 + 治理儀表板 + 連續合規監控(漂移/覆蓋率/例外老化) | A.5.36 合規審查、ISO 20000 服務報告。**證據是系統副產品** |

**統一概念**:開發者拿到鋪好的路,合規是路上的護欄,很難離開路。
這就是 **Platform Engineering × Policy-as-Code × GitOps × Zero-Trust** 的合體。

---

## 2. 組織與管理機制調整(技術只是一半)

技術建好但組織不調整 = 白做。關鍵轉變:**決策端從「逐筆審核」換檔成「治理政策 + 管例外 + 看趨勢」。**

### 2.1 團隊拓樸(Team Topologies)
- **平台團隊**:擁有「鋪好的路 / 引擎」,當**內部產品**經營(有路線圖、有 SLA、有客戶=開發者)。
- **串流對齊產品團隊**:消費平台、專心出業務功能,合規對他們盡量無感。
- **賦能 / 治理團隊(風險 / 資安)**:擁有「**政策矩陣 + 例外流程**」,**不再逐筆 gatekeeping**。

> 最大轉變:**資安從「擋每個變更的審查會」變成「政策作者 + 平台賦能者」。**
> 他們的產出從「會議核准」變成「版控的政策 code + 例外裁決」。

### 2.2 管理機制四個調整
1. **從 gatekeeping → management by exception**:高層不再核每筆交易,改成
   「治理政策 + 看指標 + 跑例外 / 風險接受流程 + 定期管理審查(ISO 27001 §9.3)」。
   這是組織版的「引擎接管逐筆強制」。
2. **決策權限模型(RACI 編碼化)**:誰分級、誰擁基線矩陣、誰能批 waiver(多久)、誰在高風險 CAB——
   對映系統裡的 approver group / CODEOWNERS 設定。授權委派從口頭變成 code。
3. **風險接受 = 一等公民、time-boxed**:合法的例外出口(owner + 到期 + 理由 + 審查)。
   **沒有它,人就偷繞護欄**;有它,「繞」變成「被治理的繞」。對映本專案的 補單≠漂白 + nonconformity。
4. **文化 / 誘因**:合規是「平台功能」不是「稅」。衡量**平台採用率、控制覆蓋率、例外老化**——
   不是「過了幾次稽核」。稽核變成「連續重跑閘門 + 讀版控史」,稽核員拿證據平面唯讀權,不再一年一次救火。

### 2.3 兩層如何對接(承接 conformance 文件的「介面」論)
脫鉤不是 bug,是該有的關注點分離;缺的是中間的**介面**:

```
治理端(決定風險)          平台端(強制執行)         產品端(業務)
擁有:分級準則 + 控制矩陣    擁有:引擎(閘門/admission)  擁有:workload
─────── 版控的 policy code (matrix) ───────▶ 引擎讀矩陣照做
            ▲ 例外/waiver 裁決                   │ fail-closed + 物證
            └──────── 治理儀表板(指標/趨勢)◀──────┘
```
管理層改一行矩陣 → 系統行為就變,不用找工程師、不用開會。這就是「政策 as code」當 API 的意義。

---

## 3. 從頭建的階段計劃(窄切片先驗 → 外化政策 → 接營運面 → 規模化)

| 階段 | 做什麼 | 完成定義 |
|---|---|---|
| **P0 基座** | 身分(OIDC / workload identity)、IaC 基線、git 當單一真相 | 零靜態金鑰;一切變更走 git |
| **P1 一條串流的鋪好的路** | 供應鏈簽章/SBOM/SCA + 一條部署路徑 + CMDB;**一條控制端到端打通三格** | 一個 app 從 source 到部署全程 fail-closed + 留證 |
| **P2 政策控制平面** | 外化矩陣(分級→控制)、admission control、GitOps 漂移收斂;上幾個團隊 | 翻分級標籤 → 控制強度自動變;漂移自動偵測 |
| **P3 營運面** | 接 ITSM(事件/問題/SLA)、治理儀表板、例外 / waiver 流程上線 | 事件能連回 CI 與肇因變更;例外可見可審 |
| **P4 規模化 + 連續保證** | 全組織上線、管理審查節奏、連續合規監控、稽核員唯讀 | 稽核 = 連續重跑閘門 + 讀版控史 |

> 順序的邏輯:**先在窄切片把引擎驗熟(P1),再把政策外化給治理端(P2),
> 再補營運面(P3),最後才規模化(P4)。** 不要一開始就想覆蓋全框架——會回到「紙上」。

---

## 4. 一句話總結

> 你不是「導入 ISO」,而是**建一個「控制 by construction」的平台,再把組織重組成
> 「治理端寫政策、靠例外與指標掌舵」而非逐筆把關**。
> 紙上機制之所以有效,是因為它變成**唯一的路**,偏離 = 明確、被治理的例外。

itops 是這套理念在「CI/CD → 部署治理」窄切片上的可動 PoC;本文是它放大成
整體平台 + 組織操作模型的藍圖。

## See Also
- [`framework-conformance-assessment.md`](framework-conformance-assessment.md) — 控制→系統綁定配方 + 逐項解法
- [`case-study.md`](case-study.md) — 人工審核→自動護欄的整體論述
- [`tooling-roles-and-real-world-mapping.md`](tooling-roles-and-real-world-mapping.md) — 工具角色與真實世界對映
- [`traditional-vs-caas-governance.md`](traditional-vs-caas-governance.md) — 傳統 VM vs CaaS 治理定位
