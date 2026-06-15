---
title: 案例研究 — 把銀行治理從「人工審核」重寫成「自動護欄」
type: case-study
created: 2026-06-15
updated: 2026-06-15
tags: [platform-engineering, governance, iso27001, iso20000, supply-chain, case-study]
---

# 案例研究:把銀行治理從「人工審核」重寫成「自動護欄」

> 一句話:**用 Git + GitHub Actions,把「合規」從事後人工抽查,重寫成「不合規根本做不出來」的自動護欄——預設啟用、無法繞過、全程留痕。**

## 一、問題

銀行 IT 的治理長年靠**人工審核 + 工單**:覆蓋是抽樣的、時機是事後的、一致性因人而異、證據要人工彙整。開發者覺得是阻礙,稽核覺得看不清,兩邊都累。

核心提問:**能不能讓「合規」變成系統的預設屬性,而不是一道要人盯的關卡?**

## 二、論點(一條線貫穿全程)

| | 人工審核(傳統) | 自動護欄(本 PoC) |
|---|---|---|
| 覆蓋 | 抽樣 | 100% |
| 時機 | 事後 | 事前(PR / admission) |
| 一致性 | 因人而異、會放水 | 規則固定、不講人情 |
| 不合規 | 事後發現 → 開單修 | **根本做不出來**,附明確理由 |
| 證據 | 工單 / 簽核文件 | Git 歷史 + 政策即程式碼,每行可溯源 |

> Java 類比:把合規從「上線後 code review」改成「掛在系統入口的 Bean Validation / AOP 攔截器」——每個請求進來先過驗證,不合規直接擋。

## 三、做法:同一個想法,層層下沉

每個 Phase 都是同一句話「把合規寫成程式碼、變成預設、無法繞過、全程留痕」套用到更深的一層:

| Phase | 下沉到哪一層 | 關鍵護欄 | 對應 ISO |
|-------|------------|---------|---------|
| **1** | 原始碼 / 變更 | 機敏掃描 + 結構檢查 + branch protection + CODEOWNERS(SoD) | A.5.3 / A.8.12 / A.8.32 |
| **2** | 基礎設施(IaC) | OpenTofu 合規模組(加密/禁公開焊死)+ checkov 閘門 | A.8.24 / A.8.27 |
| **D** | 執行期 / 供應鏈 | 簽章鏈(SBOM/SCA/cosign)+ 部署前驗章 fail-closed + CMDB-as-code | A.8.28 / A.8.8 |
| **E** | 例外 / 現實 | 變更分類 + 急件 PIR + 漂移偵測 + 補單≠漂白 | A.8.32 / A.8.16 |
| **F** | 多環境晉級 | build once promote + 過版三閘門 + CAB-as-code + GitOps 回退 | A.8.28 / A.5.3 |

完整 ISO 對照見 [`COMPLIANCE_MAP.md`](../COMPLIANCE_MAP.md)。

## 四、幾個「自己最滿意」的設計(面試可展開)

- **護欄,不是閘門**:不是「審核後放行」,是「不合規的東西根本生不出來」。例:沒通過測試的程式碼 build 不出可簽章的映像;未驗章的 artifact 部署不上去。
- **build once, promote same digest**:同一個已簽章的產物逐區晉級,環境差異只在 config。過版 PR 只改一行 digest,審核者一眼看懂。**真 live 驗過**:sandbox 與 test 兩環境同時跑同一個 digest。
- **鬆綁審核,不鬆綁護欄**:急件/插單可以鬆綁「人工審核的時點與對象」,但簽章/掃描/驗章這些技術閘門**永遠不鬆**。這是例外治理不變質的關鍵。
- **補單 ≠ 漂白**:事後補的變更單強制綁 justification + PIR + 不符合事項,連回原始漂移,讓「補登記」無法變成「洗白」。
- **fail-closed 一以貫之**:每道閘門預設「不過就拒絕」,缺證據視同不合規。防的是「綠燈空殼」(把測試刪光讓它假裝通過)。

## 五、我怎麼證明它真的成立(不是只有 happy path)

治理 PoC 最容易的失敗是「self-test 全綠、`tofu validate` 通過,但從沒真跑過」。所以我做了一次**真 live 端到端**:真 `podman build` → 真 `mvn test` → 真 `cosign` 簽章 → 過四道部署閘門 → 真起 OpenLiberty 容器 → 真 promote → 真 reconcile 對帳。

**這一跑,抓出 6 個 self-test 一直矇混過去的真 bug**(全被「sandbox 剛好用 9080」這個巧合遮住):

| # | bug | 為什麼 self-test 沒抓到 |
|---|-----|----------------------|
| 1 | promote 偵測 `source:` 的正則不吃行尾註解 → 過版「無變更」 | fixture 的 `source:` 剛好沒註解 |
| 2 | 部署腳本環境目錄寫死 sandbox | 從沒部署過別的環境 |
| 3 | 對 test/uat/prod 硬傳它們未宣告的 `http_port` 變數 | 多環境 tofu 介面從沒被呼叫 |
| 4 | 容器名 / 證據路徑寫死 sandbox | 同上 |
| 5 | 模組把容器**內部**埠也設成可變,但 OpenLiberty 固定聽 9080 → 非 9080 環境不可達 | sandbox 用 9080 巧合相等 |
| 6 | 過版沒把簽章複製到目標環境 → 物證驗證失敗 | self-test 不檢查跨環境物證 |

> 這正是我想展示的工程成熟度:**設計對、self-test 綠,不代表上線會動;接縫只有在真實環境才會漏。**六個全部修掉並補了回歸驗證。

## 六、誠實的邊界(不誇大)

- **SoD 是單人模擬**:個人 repo 無法真正核准自己的 PR,CAB 核准是文件化對映,非多人實演。
- **供應鏈 L4(真 SBOM/SCA 掃描)目前是設計稿**:簽章鏈 pipeline 已定義,syft/grype 實掃留待落地。
- **uat/prod 真容器未起**:機制已備(test 已真跑),只是沒再起兩個容器。
- 詳細缺口盤點見 `PROJECT_PLAN.md`。

## 七、技術棧

Git / GitHub Actions(護欄引擎)· OpenTofu + checkov(IaC 合規)· Podman + OpenLiberty(執行期)· cosign + syft + grype(供應鏈簽章/SBOM/SCA)· Python(閘門 / CMDB / 稽核報告)。**刻意用最輕的技術**:重點是治理模型,不是堆工具。

## See Also

- [`COMPLIANCE_MAP.md`](../COMPLIANCE_MAP.md) — 技術控制 ↔ ISO 27001 / 20000 全對照
- [`docs/traditional-vs-caas-governance.md`](./traditional-vs-caas-governance.md) — 傳統 VM 治理 vs CaaS,對 CAB / 稽核溝通用
- [`docs/golden-path-request-to-deploy.md`](./golden-path-request-to-deploy.md) — 部署黃金路徑七階段設計
- [`PROJECT_PLAN.md`](../PROJECT_PLAN.md) — 完整工作分解與 Gate 檢查
