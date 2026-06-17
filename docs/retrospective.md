---
title: 收尾回顧 — itops 證明了什麼、真 vs 模擬、為了什麼
type: retrospective
created: 2026-06-18
updated: 2026-06-18
tags: [retrospective, honesty, real-vs-simulated, closure]
---

# 收尾回顧:誠實的 capstone

> itops 在此凍結為 **v1.0**。這份回顧誠實講:它證明了什麼、哪些是真哪些是模擬、它為了什麼。
> 誠實本身就是它的價值——一個敢攤開「哪裡是名目」的 PoC,比假裝全綠的更可信。

## 1. 做到了什麼(走過的弧)
- **Phase 1/2**:合規護欄即程式碼(機敏掃描、結構、IaC checkov),main 七道必過閘門、branch protection。
- **Phase D**:服務請求 → 部署到 OpenLiberty 的黃金路徑(驗章閘門 / CMDB / 簽章 pipeline)。
- **Phase E/F**:例外與漂移治理(變更分類 / 急件+PIR / 補單≠漂白 / 漂移對帳)、build-once 多環境晉級 + CAB。
- **真 live**:真 cosign / podman / OpenLiberty / QEMU VM 跑過端到端,抓修十幾個只有真跑才現形的 bug。
- **真整合**:supply-chain(左側簽章) → itops(右側部署治理)靠交接契約串接;itops × iTop(真 ITSM/CMDB)。
- **收尾(v1.0)**:把自評標為「名目」的**分級→控制矩陣**做成真的(翻標籤 demo);門面 + 本回顧 + 凍結。

## 2. 真 vs 模擬(最重要的誠實)
| 面向 | 狀態 | 說明 |
|---|---|---|
| 部署前驗章 fail-closed | ✅ **真** | 真 cosign verify-blob;未簽/竄改/缺證據/偽造 全擋 |
| build-once 多環境晉級 | ✅ **真** | 同一 digest test→uat→prod,每區重驗;真 live 過 |
| CMDB-as-code + 漂移對帳 | ✅ **真** | 多層 CI + 關係拓樸;真 podman digest 比對偵測到漂移 |
| 分級→控制矩陣(風險為本) | ✅ **真**(v1.0 新) | prod confidential 實扛 5 道高階控制;翻標籤即被擋 |
| 變更分類 / 繞過旗標守衛 | ✅ **真**(機制) | self-test 完整;但**無真實例外實例**(5 單全 standard) |
| 血統 gitCommit/gitTag | ⚠️ **模擬** | 範例值(`def4567`),無 SLSA provenance;digest 之後才是真的 |
| serviceRequest 連結 | ⚠️ **半真** | 僅 sandbox #34 真;其餘 `#0` 佔位 |
| SoD / CAB 核准 | ❌ **模擬** | SOLO repo,approver=0;CODEOWNERS 機制在,缺真實多重身分 |
| SLA / 事件 / 問題(ITSM 營運面) | ❌ **未做** | 只覆蓋建置面;營運面解法=接 iTop(已整合,未深化) |

## 3. 招牌設計(面試能打的論點)
- **護欄而非閘門**:合規寫成程式碼自動執行,不靠人工 review。
- **鬆綁審核不鬆綁技術閘門**:急件鬆綁的是人工審核的時點/對象,簽章/掃描/驗章一律強制。
- **build once, promote the same digest**:環境差異只在 config,完整性可證。
- **補單≠漂白**:retroactive 必綁 nonconformity,連回根因。
- **簽核 = 意圖,不 = 執行證據**:這是「公文 vs 工程」藩籬的範疇錯誤診斷(見 form-based-governance 文件)。
- **分級驅動控制**:dataClassification 從裝飾變成被系統強制的 policy 輸入。

## 4. 它「為了什麼」(定位)
**不是為了被某家公司採用**(成功與否跟組織會不會變脫鉤)。它是一個:
- **無可否認的資格證**:會動的治理系統 + 翻標籤 demo,證明能把框架變成系統事實。
- **雙語能力的證據**:看得懂工程 ↔ 公文/監理兩邊的語言(見 management-direction-doctrine、form-based-governance)。
- **論述資產**:從現況自評到整體平台藍圖到簡報,一條完整的對外故事。

> 對齊作者職涯(銀行 → 金融資安 → 顧問):itops 是「我能把治理落地、且當公文↔工程橋」的證明。

## 5. 模式切換(收尾的真正意義)
itops 凍結為 v1.0,能量從 **「建系統」** 轉向 **「用它 + 學公文側 + 等對的時機」**:
- 用它:當提案/面試/對話的可動證據。
- 學:讀監理/控制原始文本(見 `docs/learning-sources.md`),補公文側語言。
- 等時機:稽核缺失 / 事故 / 金檢 / 新長官——窗口開時,當手上已有可動答案的人。
> 工程師最大的失敗模式是「永遠不收、一直 polish」。**有紀律地宣告夠了,本身就是一種成熟。**

## 6. 若要再推(明確未竟,都不依賴特定公司)
- 真 SLSA provenance(gitCommit 從 CI 帶入 + attestation 驗章)。
- serviceRequest 解析閘門(接 iTop UserRequest,收口請求→變更鏈)。
- 跑一次真急件 + PIR,讓例外治理有真實記錄。
- ITSM 營運面接 iTop(事件/問題/SLA),補建置面之外的另一半。
- 主線在 `supply-chain-demo`(L4 已落地);事件驅動自動化(repository_dispatch)。

## See Also
- [`PORTFOLIO.md`](../PORTFOLIO.md) — 一頁總覽(門面)
- [`framework-conformance-assessment.md`](framework-conformance-assessment.md) — 名目 vs 真 + 逐項解法
- [`case-study.md`](case-study.md) — 人工審核→自動護欄的整體論述
