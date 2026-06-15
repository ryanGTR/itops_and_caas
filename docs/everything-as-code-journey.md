---
title: 全歷程 — 「X as code」如何層層整合進 itops
type: explainer
created: 2026-06-15
updated: 2026-06-15
tags: [as-code, gitops, policy-as-code, journey, itops]
---

# 全歷程:「X as code」如何整合進 itops

> 一句話:**凡是傳統靠「人工流程 / 文件 / 在 UI 點按」做的治理,itops 都把它變成 Git 裡的「程式碼」——於是它可版控、可審核(PR)、可自動執行、可稽核留痕。** itops 不是一個工具,而是這些「as code」層一層層疊起來的治理平台。Git 是唯一真相。

## 核心轉換:從「人工/文件/點按」→「Git 裡的程式碼」

| 傳統做法 | itops 的 as-code 化 | 換來什麼 |
|---------|---------------------|---------|
| 資安規則寫在 SOP 文件、人工 review | **policy as code**(GitHub Actions + checks) | 100% 覆蓋、不疲勞、PR 階段就擋 |
| 在 GitHub UI 點分支保護 | **branch protection as code**(`setup_branch_protection.sh`) | 可重複、可版控、可稽核 |
| 手刻雲端資源、上線後弱掃 | **infrastructure as code**(OpenTofu 模組 + checkov) | 合規焊進預設值、開不出不合規 |
| 變更單寫在工單系統 | **change/deployment request as code**(`deployments/*.yaml`) | 變更即 PR、有目的/風險/回退 |
| 簽章/SBOM 靠人工跑 | **supply-chain as code**(reusable sign workflow + 信任根) | build→SBOM→SCA→sign 一條鏈 |
| 部署前檢查靠人記得做 | **deploy gate as code**(`verify_deploy_gate.py`,fail-closed) | 不合規根本部署不上去 |
| CMDB 在獨立系統人工維護 | **CMDB as code**(`cmdb/*.yaml`,部署後自動登錄) | 版控史 = 組態基線與變更史 |
| 緊急變更/補單靠口頭、事後補登 | **change-class / exception as code**(分類+PIR+補單≠漂白) | 鬆綁審核不鬆綁護欄,補登無法漂白 |
| 換版靠人重 build/手改設定 | **promotion as code**(`promote.py`,build once) | 同一 digest 逐區晉級,最小 diff |
| CAB 核准、回退靠流程文件 | **CAB as code**(CODEOWNERS) + **回退 runbook**(`rollback.sh`) | 正式區需核准、可靠回退留痕 |
| 「測試過了才上」靠自律 | **test gate as code**(測試證據 fail-closed,隨 digest 過版) | promote what passed test 名副其實 |
| 兩系統靠人工交接 | **handoff as code**(`integration/handoff-contract.md` + manifest) | supply-chain 簽完 → itops 治理,自動交棒 |
| 稽核報告人工彙整 | **console / 證據 as code**(`governance_console.py`,從記錄生成) | 一頁後台:稽核/主管看得懂 |

## 時間線:每個 Phase 疊上一層 as-code

```
Phase 1 ── policy-as-code(機敏掃描/結構)+ branch-protection-as-code + CODEOWNERS(SoD)
   │            「護欄,而非閘門」的地基:Git + Actions 就能做治理
   ▼
Phase 2 ── infrastructure-as-code(OpenTofu secure 模組 + checkov 閘門)
   │            合規下沉到基礎設施層,焊進預設值
   ▼
Phase D ── deployment-request-as-code + supply-chain-as-code(簽章鏈)
   │            + deploy-gate-as-code(fail-closed)+ CMDB-as-code(端到端證據)
   │            治理延伸到執行期:從服務請求到 App 跑在 OpenLiberty
   ▼
Phase E ── change-classification / exception / drift-as-code
   │            現實校正:急件/插單/補單也受控,護欄不鬆
   ▼
Phase F ── promotion-as-code(build once)+ CAB-as-code + rollback runbook
   │            多環境晉級,正式區需核准、可回退
   ▼
A     ── test-gate-as-code(測試證據變不可繞過的閘門)
   ▼
整合  ── handoff-as-code(supply-chain → itops 交接)+ governance-console
              itops 當活的部署治理中樞,消費 supply-chain 已簽好的 artifact;
              後台把所有 as-code 記錄聚合成單據生命週期視圖
```

## 為什麼這是「整合」而非「一堆腳本」

關鍵是**它們共用同一個真相來源(Git)、同一套交接資料(YAML 記錄)**,彼此串成一條鏈:

```
服務請求(Issue Form)
  → 變更單(DeploymentRequest YAML)
    → 供應鏈簽章(cosign)+ 測試證據
      → 部署前驗章閘門(讀 DeploymentRequest + 簽章,fail-closed)
        → 部署(OpenTofu 起 OpenLiberty)+ 完整性閉環
          → CMDB 登錄(讀部署證據,寫 CI YAML)
            → 換版(promote.py 讀上一區 CMDB 確認態,搬 digest+測試證據+簽章)
              → 漂移對帳(reconcile 比對 CMDB vs 線上)
                → 治理後台(governance_console 讀以上全部,渲染單據生命週期)
```

每一步的輸出是下一步的輸入,全部是版控檔。這就是「整合」:不是工具堆疊,是**一條以 Git 為骨幹、資料互相銜接的治理價值鏈**。

## 對映標準

- **ITIL**:請求實現 → 變更管理 → 發布/部署管理 → PIR/變更收尾。
- **ISO 27001**:A.5.3 SoD、A.8.32 變更、A.8.28 完整性/供應鏈、A.8.29 安全測試、A.8.9 組態、A.5.36 合規審查。
- **ISO 20000 / ITSM**:服務目錄、標準變更、發布管理、組態管理、服務報告。
- **ISMS**:政策即程式碼 + 證據自動產出 = 可持續稽核的管理系統。

完整逐項對照見 [`COMPLIANCE_MAP.md`](../COMPLIANCE_MAP.md);單據生命週期的具象後台見 [`docs/governance-console.html`](./governance-console.html);整合架構見 [`integration/handoff-contract.md`](../integration/handoff-contract.md)。

## See Also
- [`docs/case-study.md`](./case-study.md) — 人工審核 → 自動護欄的整體論述
- [`itops-l4-integration-plan.md`](../../supply-chain/itops-l4-integration-plan.md) — itops × supply-chain 整合計畫
