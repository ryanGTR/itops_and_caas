---
title: ADR-0003 例外路徑與漂移治理：急件 / 插單 / 補單怎麼受控
type: adr
created: 2026-06-15
updated: 2026-06-15
status: proposed
tags: [phase-e, emergency-change, expedite, retroactive, drift, reconciliation, change-management, itil, iso27001, iso20000]
---

# ADR-0003：例外路徑與漂移治理

> ADR：記錄「為什麼這樣決定」。延續 ADR-0001/0002 的稽核留痕文化。
> 本 ADR 服務於 `docs/exception-and-drift-governance.md`（急件 / 插單 / 補單的受控通道）。

## 脈絡（Context）

黃金路徑把部署做成**預核准的標準變更**(自動放行、全程護欄)。但真實維運必然遇到三種不走標準路徑的請求:**急件**(等不了核准)、**插單**(要求加急跳排程)、**補單**(沒走流程就動了、事後補)。若不設計,結果不是「沒有例外」,而是「例外在檯面下繞過所有控制」——這正是稽核最常開的缺失。需在**單人 PoC、零雲端、本機**限制下,示範如何把例外收進受控通道,並對映 ISO 27001 / ISO 20000 / ITIL。

## 決策（Decisions）

| 項目 | 選擇 | 為什麼 |
|------|------|--------|
| 例外分類載體 | **DeploymentRequest** 加 `changeType / priority / justification / expedite` | 沿用「請求即程式碼」單一真相,diff 即變更史,不另立新檔 |
| 急件鬆綁的對象 | **只鬆綁「人工審核時點」(先做後審)**,技術閘門不動 | 簽章/掃描/驗章是銀行紅線,不因急件 bypass |
| 急件的事後控制 | **強制 PIR**(自動開 issue + 到期日) | 例外不能變永久後門;ITIL 緊急變更本就要求事後審 |
| 規則強制方式 | 新增 CI 檢查 **`policy-change-class`**(fail-closed) | 「emergency⇒附理由+PIR、retroactive⇒綁不符合事項、安全閘門未被關」寫成程式碼 |
| 插單的本質 | 視為**優先序問題**,非新變更型別;以 `priority`+`expedite{by,reason}` 留痕 | 插單調順序、不跳閘門;誰能插是 SoD |
| 例外可見性 | 擴充 **`generate_audit_report.py`** 加「例外統計」一節 | 讓例外成本可見(ISO 20000 服務報告),逼業務面對 trade-off |
| 補單的處理原則 | **「補單≠漂白」**:記錄事實(retroactive+PIR) 與 矯正根因(nonconformity) **分開** | 只補單不矯正 = 縱容繞過 |
| 補單的偵測 | **漂移對帳 `reconcile.py`**:CMDB 期望態 digest vs 線上 running digest | 主動抓出「沒走流程的變更」;版控=真相 |
| 多人核准(CAB) | PoC SOLO 模式以**規則+自動產物+文件對映**體現,不假裝有多人 | 誠實面對單人 repo 限制(沿用 tooling-roles 文件做法) |

## 關鍵取捨:鬆綁什麼、不鬆綁什麼

這是本 ADR 的核心,也是最容易被做錯的地方:

| 維度 | 標準變更 | 急件 / 插單 / 補單 |
|---|---|---|
| 技術安全閘門(簽章/掃描/驗章) | 強制 | **同樣強制(不鬆綁)** |
| 人工審核時點 | 事前 | 急件可事後(+強制 PIR) |
| 優先序 | 正常批次 | 插單可加急(需留痕+授權) |
| 是否登錄 CMDB | 是 | **同樣要(補單事後補登 + 漂移抓漏)** |

> 一句話:**速度可以妥協在「人/時點/順序」,絕不妥協在「可稽核性」與「技術安全閘門」。**

## 漂移偵測的 PoC vs 正式環境

| | PoC(本專案) | 銀行正式環境 |
|---|---|---|
| 期望態來源 | `cmdb/*.yaml` 的 CI digest | CMDB / GitOps 期望態 |
| 實際態來源 | `podman inspect` 線上容器 image ID | registry digest / orchestrator(k8s)/ 監控 |
| 觸發 | 本機 / 排程跑 `reconcile.py` | 持續對帳(GitOps controller / 定期 job) |
| 不符處置 | 開 GitHub issue | 告警 + 自動矯正(GitOps)或變更工單 |

## 後果（Consequences）

- ✅ 三種真實例外都有**受控通道**,而非檯面下繞過——直接回應稽核最常見缺失。
- ✅ 技術護欄的「不鬆綁」原則被 `policy-change-class` 焊死,不靠人記得。
- ✅ 漂移對帳讓「補單/未授權變更」**可被主動偵測**,接上 D7 CMDB 的期望態。
- ✅ 例外統計讓管理層看見例外成本(服務報告)。
- ⚠️ PoC 單人 repo 無法真正演示多人 ECAB/CAB;以文件對映真實組織,需在文件講清楚定位。
- ⚠️ 漂移偵測在 PoC 限本機 podman;正式環境的實際態來源不同,需文件標註。
- ⚠️ 新增一道必過檢查(`policy-change-class`)會增加 PR 阻力——這是刻意的(護欄),但要確保訊息清楚、可快速修正。

## 核准與執行

本 ADR 目前 **proposed**。待 Ryan 審核藍圖與本 ADR 後改 **accepted**,再依 `PROJECT_PLAN.md` Phase E 逐 TASK 執行(E0 藍圖→E1 分類模型→…)。

## See Also
- `docs/exception-and-drift-governance.md`（藍圖）
- `docs/adr/0002-openliberty-runtime-and-deploy.md`（黃金路徑決策）
- `docs/cmdb-and-evidence-chain.md`（D7 CMDB,漂移期望態來源）
- `PROJECT_PLAN.md`（Phase E）
