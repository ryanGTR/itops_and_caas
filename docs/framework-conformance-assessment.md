---
title: 框架精神符合度自評 + 系統落地解法（ISMS / ISO 20000 / ITIL）
type: assessment
created: 2026-06-17
updated: 2026-06-17
tags: [iso27001, iso20000, itil, compliance, policy-as-code, gap-analysis]
sources:
  - deployments/*/*.yaml（DeploymentRequest）
  - cmdb/*/*.yaml（多層 CI）
  - deployments/*/last-deploy.json（執行記錄）
  - .github/ISSUE_TEMPLATE/service-request.yml
  - scripts/generate_audit_report.py
  - COMPLIANCE_MAP.md
---

# 框架精神符合度自評 + 系統落地解法

> 兩個問題分開回答:
> 1. **itops 記錄的資料,符不符合 ISMS / ISO 20000 / ITIL 的「精神」?**(誠實自評,不貼標籤充數)
> 2. **規定知道了,對應到系統到底該怎麼做?**(這是多數組織真正卡住的地方——有政策文件、沒系統綁定)
>
> 結論先講:itops 在「**完整性 + 組態 + 變更賦能概念**」這條軸上是真的吃透精神;
> 但「**人的治理**」(SoD / CAB / 核准)幾乎是模擬空殼,「**風險為本**」沒兌現,
> 且只覆蓋 ITSM 的**建置面**(請求→變更→發布→組態),沒碰**營運面**(SLA / 事件 / 問題)。

---

## 0. 為什麼組織會卡在「知道規定、不知道怎麼做」

合規框架是用**散文寫的政策與控制目標**(「變更須經 CAB 核准」「控制應與風險相稱」),
它**不告訴你系統綁定點**——哪個資料結構記錄它、哪道自動閘門強制它、哪份物證證明它。
於是組織把規定寫成 Word 政策,貼在 wiki,然後**系統照舊跑**,稽核時再人工補證據。
這就是「名目合規」:有政策、無強制、出事才發現護欄是畫上去的。

**橋接的通用配方(itops 的核心論述「護欄而非閘門 / policy-as-code」):**

> 每一條控制 → ①**記錄它的資料欄位** → ②**缺它就 fail-closed 的自動閘門** → ③**自動產出的物證**

只要一條控制能填滿這三格,它就從「名目」變「真」。itops 對**部分**控制做到了(完整性鏈、
組態管理);本文把同一個配方套用到**還只有散文、沒系統綁定**的控制上,給出具體做法。
這套配方本身就是給公司的答案:**先建「控制項 ↔ 系統綁定」對照表(下節),再逐列補齊三格。**

---

## 1. 控制項 ↔ 系統綁定對照表（規定→系統的橋）

> 這張表就是「規定對應到系統怎麼做」的具體化。`COMPLIANCE_MAP.md` 是它的種子;
> 差別在這裡每一列都點名 **①資料欄位 ②閘門 ③物證**,並誠實標 **現況(真/名目/缺)**。

| 框架控制 | ①資料綁定點 | ②自動閘門(fail-closed) | ③物證 | itops 現況 |
|---|---|---|---|---|
| A.8.28 供應鏈完整性 | `source.digest`(不可變身分) | verify 驗章 + 部署完整性閉環 | last-deploy `integrityCheck` | ✅ **真** |
| A.8.28 來源血統(SLSA) | `gitCommit`/`gitTag`/builder | attestation 驗 source↔artifact | build provenance 簽章 | ⚠️ **名目**(假值,無 attestation) |
| ISO20000 組態管理 | `cmdb/**` 多層 CI + relationships | cmdb_validate + reconcile 漂移 | CMDB CI + 漂移對帳報告 | ✅ **真** |
| A.8.32 變更管理(分類) | `changeType`/`priority` | validate_change_class | 變更分類驗證 + PR | ✅ **真**(機制);⚠️ 無例外實例 |
| A.5.3 職責分離(SoD) | `requestedBy`/`approvedBy` | branch protection:requester≠approver | PR review 記錄 | ❌ **名目**(approver=0,自填角色) |
| ITIL 變更賦能(CAB) | CODEOWNERS / `approvedBy` | prod 需 N 位 CAB team 核可 | merge 的核准軌跡 | ❌ **名目**(SOLO,空殼) |
| ISMS 風險為本(分級驅動) | `dataClassification` | 分級→控制矩陣 policy 閘門 | 閘門 run + 達標欄位 | ❌ **名目**(分級是裝飾) |
| ISO20000 服務請求→變更 | `serviceRequest`(工單號) | 解析工單存在且已核准 | iTop UserRequest / issue | ⚠️ **半真**(僅 sandbox #34 真,prod=#0) |
| A.5.36 合規審查 | 全部物證 | 自動稽核報告 | generate_audit_report 輸出 | ✅ **真** |
| ISO20000 SLA/服務水準 | (無) | (無) | (無) | ❌ **缺** |
| ISO20000/ITIL 事件管理 | (無) | (無) | (無) | ❌ **缺**(iTop 原生可補) |
| ISO20000/ITIL 問題管理 | (無) | (無) | (無) | ❌ **缺**(iTop 原生可補) |

---

## 2. 逐項系統解法（針對「名目 / 缺」的格子）

每一項都給:**規定的精神 → 為什麼卡 → 系統怎麼做(資料/閘門/物證) → itops 落地路徑**。

### 2.1 SoD / CAB 從空殼變真(A.5.3 / ITIL 變更賦能)
- **精神**:提議變更的人 ≠ 核准變更的人;高風險變更要有權責者評估風險後核准。
- **為什麼卡**:核准發生在 email / 會議記錄,**沒綁在 artifact / PR 上**,系統照樣放行。
- **系統怎麼做**:
  - **資料**:變更記錄帶 `approvedBy` + `approverRole` + `approvalRef`;機器檢查 `requestedBy ≠ approvedBy`。
  - **閘門**:branch protection 要求來自 **排除作者**的 CODEOWNERS group 核可;prod 要求 ≥N 位
    `@org/change-advisory-board` team 成員核可;`enforce_admins=true`。閘門讀 PR 的真實 review 身分,
    `approver==author` 或 approver 不在 CAB team → 擋。
  - **物證**:merge commit 的 review 記錄(誰、何時核准)即不可變稽核軌跡,不需另存 email。
- **itops 落地**:CODEOWNERS + 規則已具備,缺的只是**真實多重身分**。公司端=接真 org team(零障礙);
  PoC 端=用 2 個帳號或文件化 `@org/cab` 對映。**關鍵是閘門讀真實 review 身分並強制 requester≠approver**——
  這一步把「核准」從文件變成不可繞過的系統事實。

### 2.2 資料分級真的驅動差異化控制(ISMS 風險為本)
- **精神**:控制強度與風險(資料分級)相稱——機密系統該比內部系統管得更嚴。
- **為什麼卡**:分級是試算表裡的標籤,**不是 policy 的輸入**;所有系統一視同仁。
- **系統怎麼做**:
  - **資料**:`dataClassification` 已記錄。新增**分級→控制矩陣(as-code)**:
    `confidential` ⇒ 需 `encryptionAtRest:true` + 加密驗章 + ≥2 CAB 核可 + 限制網路政策 + 滲透測試物證;
    `internal` ⇒ 1 核可;`public` ⇒ 標準閘門。
  - **閘門**:policy engine(OPA/Conftest 或 checkov 自訂)讀 `dataClassification`,
    **缺該等級要求的控制就 fail-closed**。例:`confidential` 部署但 manifest 無 `encryptionAtRest`
    或 `approvals<2` → 拒絕。
  - **物證**:閘門 run + manifest 欄位,證明高分級部署「真的」過了較高的門檻。
- **itops 落地**:新增 `policies/classification-matrix.yaml` + 一支讀 `dataClassification` 的 fail-closed 閘門。
  完全可建,且把「分級」從裝飾變成驅動真實控制差異的決策輸入。

### 2.3 血統 / Provenance 變真(A.8.28 完整性的源碼段)
- **精神**:不只證明「artifact 沒被竄改」,還要證明「它由哪份源碼、哪個 builder 產出」。
- **為什麼卡**:組織簽了 artifact,但 `gitCommit` 是人手打的(可造假),source→artifact 段是斷的。
- **系統怎麼做**:
  - **資料**:`gitCommit`/`gitTag`/builder **由 CI 上下文帶入**(`$GITHUB_SHA`、runner identity),
    禁止人手填;加 SLSA build provenance attestation。
  - **閘門**:verify 步驟用 `cosign verify-attestation` / `gh attestation verify` 檢查
    artifact digest ↔ source commit ↔ builder 身分。
  - **物證**:attestation 即 source→artifact 的密碼學連結。
- **itops 落地**:supply-chain-demo 的 `supply-chain.yml` **已有 `attestations: write` + keyless OIDC**,
  距離很近。修法=`emit_manifest` 從 `$GITHUB_SHA` 取真 commit + 加一道 attestation 驗證閘門。
  把目前的假值(`def4567`/`v0.0.0-EXAMPLE`)換成 CI 帶入的真值。

### 2.4 請求→變更鏈不再斷(ISO 20000 服務請求履行)
- **精神**:每個變更可追溯回一張**真實、已核准**的服務請求工單。
- **為什麼卡**:工單在 ITSM 系統、部署在 pipeline,兩邊**沒對接**;單號用佔位值或事後補填。
- **系統怎麼做**:
  - **資料**:`serviceRequest` 必須是真工單 ID。
  - **閘門**:一道 check 把 `serviceRequest` 對 ticketing 系統(iTop REST / GitHub issue)**解析**,
    工單不存在或狀態非「已核准」→ fail-closed。
  - **物證**:iTop UserRequest / GitHub issue 的開→核→關軌跡。
- **itops 落地**:`integration/itop` 的 `itop_sync` **已會建 iTop UserRequest**——把迴路收口即可:
  部署閘門驗 `serviceRequest` 能解析成一張真實、已核准的 iTop UserRequest。
  把 prod 的假單號 `#0` 換成真工單,鏈就不斷。

### 2.5 例外治理留下真實記錄(ITIL 變更賦能 + A.5.36)
- **現況**:機制(emergency/retroactive 分類 + PIR + 補單≠漂白)+ self-test 都有,但 5 張請求單全 standard,
  **真實例外記錄 0 筆**——「能力具備、無資料體現」。
- **系統怎麼做 / 落地**:跑**一次真的急件流程**:開 emergency DeploymentRequest(附 justification+pir)→
  先部署後補審 → 系統自動開 PIR issue → PIR 到期前完成檢討 → 留軌跡。低成本、立刻把例外治理從
  「設計」變「演過」。漂移 demo issue #21 已是這類真實記錄的先例。

### 2.6 ITSM 營運面:SLA / 事件 / 問題(整個流程沒碰)
- **精神**:ITSM 不只「把變更上線」,還要「維持服務水準、處理事件、根除問題」。itops 只做了建置面。
- **系統怎麼做(關鍵:別重造,接 iTop)**:
  - **事件 Incident**:iTop **原生有** Incident/Problem 模組。資料綁定=`CMDB CI ↔ Incident ↔ 肇因 Change`。
    itops 已同步 CMDB 進 iTop,只要再讓事件能連回「影響的 CI」與「造成它的變更」。
  - **SLA**:服務水準目標當資料掛在服務目錄條目上;用 last-deploy 時戳 / 事件 MTTR 衡量達成率。
  - **問題 Problem**:重複事件 → 問題記錄 → 連回 `nonconformity`(itops 補單≠漂白已有此概念)。
  - **清楚分工**:這些是 iTop(真 ITSM 產品)的原生強項。**解法不是在 itops 重建,是用 iTop 補營運面**,
    讓 supply-chain/itops 餵建置面資料(Change/Release/CMDB)進去。建置面 as-code、營運面用 ITSM 平台,
    各司其職。

---

## 3. 給公司的落地模式(可直接複製)

公司卡在「知道規定、沒人知道對應系統怎麼做」,可照這個順序破題:

1. **建「控制項 ↔ 系統綁定」對照表**(本文第 1 節的格式):把每條稽核控制攤成
   ①資料欄位 ②自動閘門 ③物證 三格。光是攤開,就會暴露哪些控制目前是「名目」(三格有空)。
2. **逐列補三格,優先補「名目」**:政策已寫但系統沒綁的,就是風險最高、稽核最虛的。
   每補一格就用 policy-as-code 讓它 fail-closed(缺資料/缺核准/缺物證就擋)。
3. **核准與職責分離優先做真**:這是最常見的空殼,也是稽核最愛抓的。把核准綁進 PR/pipeline 的
   review 機制(requester≠approver、CAB team、enforce admins),核准就從文件變系統事實。
4. **分級驅動控制矩陣**:讓 `dataClassification` 變 policy 輸入,而非標籤。風險為本才算兌現。
5. **建置面 as-code、營運面接 ITSM 平台(iTop)**:別在 pipeline 重造事件/問題/SLA;
   讓兩邊靠 CMDB + 工單號對接。
6. **稽核 = 重跑閘門 + 讀版控史**,不是事後湊文件。物證是系統副產品,不是額外工作。

> 一句話總結給公司:**把每條規定翻譯成「一個資料欄位 + 一道 fail-closed 閘門 + 一份自動物證」,
> 規定就從牆上的政策變成系統裡不可繞過的事實。** 這正是 itops 想示範的「翻譯層」。

---

## 4. itops 自身的下一步(對齊本文解法)

按「對履歷與真實價值」排序的候選(都不依賴 ADO):
- **(高 CP)** 2.2 分級→控制矩陣閘門:把 `dataClassification` 變真,展示 ISMS 風險為本。
- **(高 CP)** 2.3 真 provenance:`emit_manifest` 取 `$GITHUB_SHA` + attestation 驗章(supply-chain-demo 已備 OIDC)。
- **(中)** 2.4 serviceRequest 解析閘門:收口 iTop UserRequest 迴路,把假單號 `#0` 變真。
- **(低成本高效)** 2.5 跑一次真急件 + PIR,讓例外治理有真實記錄。
- **(較大)** 2.6 接 iTop 事件/問題,補 ITSM 營運面。

> 誠實定位:本文承認 itops 有大量「名目」格子。**但能逐格指出「名目在哪、怎麼補成真」本身就是能力證明**
> ——看得懂框架精神、知道規定到系統的綁定點,不是貼 ISO 編號充數。這比一個假裝全綠的 PoC 更有說服力。

## See Also
- [`COMPLIANCE_MAP.md`](../COMPLIANCE_MAP.md) — 控制項對照(本文對照表的種子)
- [`docs/case-study.md`](case-study.md) — 人工審核→自動護欄的整體論述
- [`docs/exception-and-drift-governance.md`](exception-and-drift-governance.md) — 例外/漂移治理設計
- [`integration/itop/README.md`](../integration/itop/README.md) — iTop 整合(營運面落地點)
