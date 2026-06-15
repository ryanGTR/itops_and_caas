---
title: 例外與漂移治理 — 急件 / 插單 / 補單的受控通道
type: design
created: 2026-06-15
updated: 2026-06-15
status: blueprint（待核准後逐 TASK 執行）
tags: [exception, emergency-change, expedite, retroactive, drift, reconciliation, itil, iso20000, iso27001, change-management, golden-path]
---

# 例外與漂移治理：急件 / 插單 / 補單的受控通道

> **這是藍圖（blueprint），不是實作。** 依 `CLAUDE.md` 鐵則:逐 TASK、每步停下確認、不跳階段、決策留痕。
> 黃金路徑（`docs/golden-path-request-to-deploy.md`）把「部署」做成**預核准的標準變更**——自動放行、全程護欄。
> 但真實維運會遇到**走不進、或繞過、或對不上**標準路徑的請求。本文件設計這層「**現實校正層**」:
> 把急件 / 插單 / 補單收進**受控通道**,而不是假裝它們不存在。
>
> 對應工作分解見 `PROJECT_PLAN.md` 的 **Phase E**；關鍵決策見 `docs/adr/0003-exception-path-and-drift.md`。

## 0. 與黃金路徑的關係

```
標準變更（黃金路徑本體）── 預核准、自動放行、全程護欄
   │
   ├─ 急件（Emergency）── 壓縮「審核時點」(先做後審 + 強制 PIR)，技術護欄不動
   ├─ 插單（Expedite）── 調「優先序」，留痕 + 量化，技術護欄不動
   └─ 補單（Retroactive）── 事後「補證 + 矯正」，並用漂移偵測抓出來
```

> 本層**疊在黃金路徑之上**,不取代它。標準變更仍是主幹,例外是有意識管理的支線。

## 1. 一句話總結（給稽核 / 主管）

> 例外無法消滅。本平台**鬆綁的是「人工審核的時點與對象」,永遠不是技術安全閘門**——急件照樣要簽章、掃描、驗章。每一次例外都**留痕、事後強制回顧(PIR)、並量化成報表**,讓管理層看見例外的真實成本;繞過流程的變更則由**漂移偵測**主動抓出來矯正。

## 2. 設計總則（貫穿三場景）

| 原則 | 意涵 | 為什麼 |
|---|---|---|
| **護欄不鬆綁** | D4 簽章 / D5 驗章 / SCA 掃描對所有 changeType **無 bypass** | 急著上線 ≠ 上線沒驗過的東西(銀行紅線) |
| **鬆綁有時限** | 急件「先做後審」,但 PIR 強制、有到期 | 例外不能變成永久後門 |
| **一切留痕** | 分類、理由、誰批、PIR、漂移,全進 Git / Issue | ISO 可稽核性 |
| **例外可見** | 例外量做成報表,逼業務面對 trade-off | 零成本的例外會侵蝕標準流程 |
| **終極解是讓繞過不可能** | 補單只是過渡期的審計 + 矯正,根因要修護欄 | 偵測 ≠ 縱容 |

> Java 類比:急件像 `try { fastPath() } finally { mandatoryAudit() }`——可以走快路徑,但 `finally` 一定補上稽核,逃不掉。

## 3. 三場景設計細節

### ① 急件（Emergency Change｜ITIL 緊急變更 / ISO 27001 A.8.32）

- **長相**:線上出事或有時效壓力,等不了正常核准週期。
- **ITIL 定位**:**不是「沒流程」,是「壓縮過的流程」**——核准走 ECAB(緊急變更小組,人少快),允許先實作後審核,但**事後 PIR(Post-Implementation Review)強制**。
- **設計**:
  - DeploymentRequest 加 `changeType: emergency` + 必填 `justification`。
  - 合併後 workflow **自動開一張 PIR issue**(含到期日,如 48h)。
  - 新增 CI 檢查 `policy-change-class`:`emergency ⇒ 必附 justification + 必有 PIR 連結`;並確認**安全閘門未被依 changeType 關閉**。
- **關鍵**:急件只壓縮「審核」,**簽章/掃描/驗章原封不動照跑**。

### ② 插單（Expedite / 加急｜優先序問題,非變更型別）

- **長相**:請求本身合規,但被要求「插隊、加急」,打亂正常排程。
- **ITIL 定位**:這是**優先序 / 排程**問題,不是新的變更型別。
- **設計**:
  - DeploymentRequest 加 `priority: P1..P4` + `expedite: {by, reason}`。
  - **誰有權插**是 SoD 問題——由有權者(服務經理/值班主管)批,不是請求者自封。
  - **讓成本可見**:擴充 `generate_audit_report.py` 加「例外統計」一節(emergency/expedite 件數與佔比)——這正是 ISO 20000 服務報告的價值。
- **關鍵**:插單只調順序,**不跳任何閘門**。

> Java 類比:`PriorityQueue` / `Thread.setPriority()`——調的是優先序,那個 task **還是要過同一套 validation**。

### ③ 補單（Retroactive / Out-of-band｜最敏感）

- **長相**:有人沒開單就直接上線(手動改設定、直接推 prod),事後才補單。
- **核心觀念**:**補單不是「漂白違規」,是「留下事實 + 啟動矯正」。** 兩件事分開:

  | | 做什麼 | 對應控制 |
  |---|---|---|
  | (a) 記錄變更 | 補成 `retroactive` 變更 + PIR,把實際做了什麼登錄回 CMDB | A.8.32 / A.8.9 |
  | (b) 處理「竟然繞得過」 | 當成 nonconformity / 事故 root cause:為什麼有人能不走流程? | A.5.36 / 矯正措施 |

- **偵測(關鍵)**:**漂移對帳(reconciliation)**——`reconcile.py` 比對「線上 running image digest」vs「CMDB CI 的 digest」。不符或缺漏 → **自動開 issue**(系統發現有人沒走流程)。
- **設計**:
  - `changeType: retroactive` 的 DeploymentRequest **強制綁一張 PIR / 不符合事項**(由 `policy-change-class` 驗)。
  - `scripts/reconcile.py` + 反例 self-test;漂移 → 開 issue。
- **關鍵**:**版控 = 真相;補單 = 把脫離版控的現實拉回版控。** 終極解是讓繞過根本發生不了(呼應黃金路徑「不合規的根本部署不上去」)。

> Java 類比:補單像「先在 prod 熱修,事後一定要把 patch 補回版控 + 補測試 + code review」,否則下次 deploy 會用舊版蓋掉你的熱修(這就是 drift)。

## 4. 用到的現成資產（不重造輪子）

| 來源 | 提供什麼 | 用在 |
|---|---|---|
| DeploymentRequest（D2） | 變更紀錄載體;加 changeType/priority/justification | ①②③ |
| CMDB-as-code（D7） | 期望態 digest,供漂移對帳比對 | ③ |
| `generate_audit_report.py`（D7/07） | 報告框架;加「例外統計」一節 | ② |
| D4 簽章 / D5 驗章閘門 | 對所有 changeType 不鬆綁的技術護欄 | ①②③ |
| CODEOWNERS / branch protection（05/06） | SoD 與必過檢查;CAB-as-code(選配 E6) | ①③ |

## 5. 範圍與非範圍

**範圍**:本機、零雲端成本 PoC;以規則即程式碼 + 自動產物(PIR/issue)體現治理邏輯;漂移偵測在本機對 podman 實際態對帳。
**非範圍**:正式 ECAB 多人流程(PoC 單人 repo,以文件對映真實組織);取代企業 CMDB / ITSM 工具;真實機密分級。SOLO 模式下「多人核准」以文件說明對映,不假裝有 CAB。

## 6. 完成定義（Gate E）

見 `PROJECT_PLAN.md` Phase E 的 Gate E:三場景都有受控通道、技術護欄全程不鬆綁、急件有 PIR、漂移抓得到並開 issue、例外量可報表化——全數打勾才算完成。

## See Also
- `docs/golden-path-request-to-deploy.md`（黃金路徑本體,標準變更）
- `docs/adr/0003-exception-path-and-drift.md`（本層核心決策）
- `docs/deploy-to-openliberty.md`（D6 部署）
- `docs/cmdb-and-evidence-chain.md`（D7 CMDB,漂移對帳的期望態來源）
- `PROJECT_PLAN.md`（Phase E 工作分解）
