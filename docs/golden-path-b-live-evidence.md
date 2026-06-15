# 稽核證據報告(Audit Evidence Report)

> 自動產出 — 由 GitHub 技術紀錄翻譯為對應 ISO 控制項的合規證據。
> 對應控制:ISO 27001 A.5.36 合規審查、ISO 20000 服務報告。

- **儲存庫**:`ryanGTR/itops_and_caas`
- **期間**:2026-05-16 ~ 2026-06-15
- **產出時間(UTC)**:2026-06-15T12:18:23+00:00

## 一、政策護欄 ↔ ISO 控制項對照

| 任務 | 技術控制 | 載體 | 對應 ISO 控制項 |
| --- | --- | --- | --- |
| TASK-03 | 機敏資訊掃描 | policy-secrets | ISO 27001 A.8.12, ISO 27001 A.5.17 |
| TASK-04 | 結構與命名規範 | policy-structure | ISO 27001 A.5.37 |
| TASK-06 | PR 流程變更管理 | branch protection | ISO 20000 變更管理, ISO 27001 A.8.32 |
| TASK-05 | 職責分離 (SoD) | CODEOWNERS | ISO 27001 A.5.3, ISO 27001 A.8.4 |

## 二、政策檢查執行統計(護欄覆蓋證據)

> 證明「期間內變更都經過合規檢查」,並列出通過率與攔截(failure)紀錄。

| 技術控制 | workflow | 執行次數 | 通過 | 攔截(fail) | 其他 | 通過率 | ISO 控制項 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 機敏資訊掃描 | policy-secrets | 32 | 32 | 0 | 0 | 100% | ISO 27001 A.8.12, ISO 27001 A.5.17 |
| 結構與命名規範 | policy-structure | 32 | 32 | 0 | 0 | 100% | ISO 27001 A.5.37 |

## 三、變更(PR)明細 — 誰改的/誰核准的/檢查結果

> 每個合併都可追溯:變更者、核准者、政策檢查結果(ISO 20000 / A.8.32)。

| PR | 標題 | 變更者 | 合併日 | 核准者 | 檢查結果 |
| --- | --- | --- | --- | --- | --- |
| #29 | feat(test-gate): 把測試做成不可繞過的供應鏈閘門(補最大缺口) | ryanGTR | 2026-06-15 | (0,SOLO 模式) | change-class=SUCCESS; cmdb-validate=SUCCESS; deploy-gate-selftest=SUCCESS; policy-iac=SUCCESS; promote-gate=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #28 | docs(governance): 傳統 VM 治理 vs CaaS 治理 對照 | ryanGTR | 2026-06-15 | (0,SOLO 模式) | change-class=SUCCESS; cmdb-validate=SUCCESS; deploy-gate-selftest=SUCCESS; policy-iac=SUCCESS; promote-gate=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #27 | chore(branch-protection): 將 promote-gate | ryanGTR | 2026-06-15 | (0,SOLO 模式) | change-class=SUCCESS; cmdb-validate=SUCCESS; deploy-gate-selftest=SUCCESS; policy-iac=SUCCESS; promote-gate=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #26 | [Phase F][TASK-F4] CAB-as-code 正式區核准 + G | ryanGTR | 2026-06-15 | (0,SOLO 模式) | change-class=SUCCESS; cmdb-validate=SUCCESS; deploy-gate-selftest=SUCCESS; policy-iac=SUCCESS; promote-gate=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #25 | [Phase F][TASK-F3] 過版閘門 policy-promote:三 | ryanGTR | 2026-06-15 | (0,SOLO 模式) | change-class=SUCCESS; cmdb-validate=SUCCESS; deploy-gate-selftest=SUCCESS; policy-iac=SUCCESS; promote-gate=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #24 | [Phase F][TASK-F2] 過版生成器:只改目標環境 source.d | ryanGTR | 2026-06-15 | (0,SOLO 模式) | change-class=SUCCESS; cmdb-validate=SUCCESS; deploy-gate-selftest=SUCCESS; policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #23 | [Phase F][TASK-F1] 多環境骨架:test/uat/prod(同 | ryanGTR | 2026-06-15 | (0,SOLO 模式) | change-class=SUCCESS; cmdb-validate=SUCCESS; deploy-gate-selftest=SUCCESS; policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #22 | [Phase E][TASK-E5] 補單流程:補單≠漂白(收關 Gate E) | ryanGTR | 2026-06-15 | (0,SOLO 模式) | change-class=SUCCESS; cmdb-validate=SUCCESS; deploy-gate-selftest=SUCCESS; policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #20 | [Phase E][TASK-E4] 漂移偵測 / 對帳:主動抓出沒走流程的變更 | ryanGTR | 2026-06-15 | (0,SOLO 模式) | change-class=SUCCESS; cmdb-validate=SUCCESS; deploy-gate-selftest=SUCCESS; policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #19 | [Phase E][TASK-E3] 例外可見性:稽核報告加「例外統計 + PI | ryanGTR | 2026-06-15 | (0,SOLO 模式) | change-class=SUCCESS; cmdb-validate=SUCCESS; deploy-gate-selftest=SUCCESS; policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #18 | [Phase E][TASK-E2] 急件路徑 + 強制 PIR:先做後審不賴帳 | ryanGTR | 2026-06-15 | (0,SOLO 模式) | change-class=SUCCESS; cmdb-validate=SUCCESS; deploy-gate-selftest=SUCCESS; policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #17 | chore(branch-protection): deploy-gate-se | ryanGTR | 2026-06-15 | (0,SOLO 模式) | change-class=SUCCESS; cmdb-validate=SUCCESS; deploy-gate-selftest=SUCCESS; policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #16 | [Phase E][TASK-E1] 變更分類模型:例外路徑的地基(fail-c | ryanGTR | 2026-06-15 | (0,SOLO 模式) | change-class=SUCCESS; cmdb-validate=SUCCESS; deploy-gate-selftest=SUCCESS; policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #15 | [Phase F][TASK-F0] 多環境晉級與過版藍圖 + 識別子血統觀念頁 | ryanGTR | 2026-06-15 | (0,SOLO 模式) | cmdb-validate=SUCCESS; deploy-gate-selftest=SUCCESS; policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #14 | [Phase E][TASK-E0] 例外與漂移治理藍圖:急件/插單/補單的受控 | ryanGTR | 2026-06-15 | (0,SOLO 模式) | cmdb-validate=SUCCESS; deploy-gate-selftest=SUCCESS; policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #13 | chore(branch-protection): 將 cmdb-validat | ryanGTR | 2026-06-15 | (0,SOLO 模式) | cmdb-validate=SUCCESS; deploy-gate-selftest=SUCCESS; policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #12 | [TASK-D7] CMDB-as-code + 端到端稽核證據鏈:黃金路徑階段 | ryanGTR | 2026-06-15 | (0,SOLO 模式) | cmdb-validate=SUCCESS; deploy-gate-selftest=SUCCESS; policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #11 | [TASK-D6] 部署到 OpenLiberty + 煙霧測試:黃金路徑階段⑥ | ryanGTR | 2026-06-15 | (0,SOLO 模式) | deploy-gate-selftest=SUCCESS; policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #10 | [TASK-D5] 部署前驗章閘門(fail-closed) | ryanGTR | 2026-06-15 | (0,SOLO 模式) | deploy-gate-selftest=SUCCESS; policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #9 | [TASK-D4] 供應鏈簽章:可重用 pipeline + cosign 信任 | ryanGTR | 2026-06-14 | (0,SOLO 模式) | policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #8 | [TASK-D3] OpenTofu openliberty-service 模 | ryanGTR | 2026-06-14 | (0,SOLO 模式) | policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #7 | [TASK-D2] 請求→變更 銜接:部署請求即程式碼 + PR 可追溯 | ryanGTR | 2026-06-14 | (0,SOLO 模式) | policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #6 | [TASK-D1] 服務目錄 + 服務請求單(Issue Form) | ryanGTR | 2026-06-14 | (0,SOLO 模式) | policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #5 | [Phase D] 部署黃金路徑藍圖:設計 + ADR-0002 + Phase | ryanGTR | 2026-06-14 | (0,SOLO 模式) | policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #4 | chore(branch-protection): policy-iac 納入  | ryanGTR | 2026-06-05 | (0,SOLO 模式) | policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #3 | [Phase 2] IaC 合規護欄:secure-bucket 模組 + ch | ryanGTR | 2026-06-05 | (0,SOLO 模式) | policy-iac=SUCCESS; policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #2 | [follow-up] 收尾 Phase 1：排程稽核報告 + 穩定 check | ryanGTR | 2026-06-05 | (0,SOLO 模式) | policy-secrets=SUCCESS; policy-structure=SUCCESS |
| #1 | [TASK-07] 稽核證據自動產出 generate_audit_report | ryanGTR | 2026-06-04 | (0,SOLO 模式) | 機敏資訊掃描 (ISO 27001 A.8.12)=SUCCESS; 結構與命名規範檢查 (ISO 27001 A.5.37)=SUCCESS |

## 四、黃金路徑端到端證據鏈(七階段:請求 → 部署 → CMDB)

> 把一次部署沿「請求→PR→建置/簽章→驗章→佈建→部署→CMDB」串成一條鏈,
> 每階段附**物證指標**與對映 ISO 控制項——稽核可逐階段點開查核(TASK-D7)。

### supply-chain-backend → openliberty-sandbox

- **映像 digest**:`sha256:707f88c2ef9be6f4001f93b494b8db2a7e0fb997a4e293f60f3cd4a8ac020b77`
- **部署時間(UTC)**:2026-06-15T12:06:08Z　**結果**:success

| 階段 | 狀態 | 物證 | 對映 ISO 控制項 |
| --- | --- | --- | --- |
| ① 服務請求單 | ✅ | 服務請求 #0(docs/service-catalogue.md) | ITIL 請求履行 / ISO 20000 服務請求 |
| ② 請求轉變更(PR) | ✅ | DeploymentRequest:deployments/openliberty-sandbox/supply-chain-backend.yaml(PR 即變更) | ISO 27001 A.8.32 變更管理 |
| ③ 供應鏈建置 + 簽章 | ✅ | cosign 簽章:deployments/openliberty-sandbox/sig/supply-chain-backend.sig 對 sha256:707f88c2ef9be6f4… | ISO 27001 A.8.28 供應鏈完整性 |
| ④ 佈建環境(OpenTofu) | ✅ | OpenTofu 環境:iac/environments/openliberty-sandbox(預設安全模組) | ISO 27001 Secure by Default |
| ⑤ 部署前驗章閘門 | ✅ | 驗章閘門:gate=passed(fail-closed) | ISO 27001 完整性 / ITIL 發布驗證 |
| ⑥ 部署 + 煙霧測試 | ✅ | 部署=success;煙霧 GET /health + GET /api/products | ISO 20000 發布與部署管理 |
| ⑦ 登錄 CMDB + 稽核證據 | ✅ | CMDB CI:cmdb/openliberty-sandbox/supply-chain-backend.yaml | ISO 20000 組態管理 / ISO 27001 A.8.9 |

> ✅ 七階段物證齊備:這次部署**端到端可稽核**。

### supply-chain-backend → test

- **映像 digest**:`sha256:707f88c2ef9be6f4001f93b494b8db2a7e0fb997a4e293f60f3cd4a8ac020b77`
- **部署時間(UTC)**:2026-06-15T12:16:52Z　**結果**:success

| 階段 | 狀態 | 物證 | 對映 ISO 控制項 |
| --- | --- | --- | --- |
| ① 服務請求單 | ✅ | 服務請求 #0(docs/service-catalogue.md) | ITIL 請求履行 / ISO 20000 服務請求 |
| ② 請求轉變更(PR) | ✅ | DeploymentRequest:deployments/test/supply-chain-backend.yaml(PR 即變更) | ISO 27001 A.8.32 變更管理 |
| ③ 供應鏈建置 + 簽章 | ❌ | cosign 簽章:deployments/test/sig/supply-chain-backend.sig 對 sha256:707f88c2ef9be6f4… | ISO 27001 A.8.28 供應鏈完整性 |
| ④ 佈建環境(OpenTofu) | ✅ | OpenTofu 環境:iac/environments/test(預設安全模組) | ISO 27001 Secure by Default |
| ⑤ 部署前驗章閘門 | ✅ | 驗章閘門:gate=passed(fail-closed) | ISO 27001 完整性 / ITIL 發布驗證 |
| ⑥ 部署 + 煙霧測試 | ✅ | 部署=success;煙霧 GET /health + GET /api/products | ISO 20000 發布與部署管理 |
| ⑦ 登錄 CMDB + 稽核證據 | ✅ | CMDB CI:cmdb/test/supply-chain-backend.yaml | ISO 20000 組態管理 / ISO 27001 A.8.9 |

> ⚠️ 有階段物證缺漏,請查核上表 ❌ 項。

## 五、例外統計(急件 / 插單 / 補單的成本可見化)

> 例外無法消滅,但要**可見**。零成本的例外會侵蝕標準流程——本節讓管理層
> 看見例外的量與 PIR 履行情況,逼業務面對 trade-off(ISO 20000 服務報告 / A.5.36)。

| 變更型別 | changeType | 件數 | 佔比 |
| --- | --- | --- | --- |
| 標準變更 | standard | 4 | 100% |
| 一般變更 | normal | 0 | 0% |
| 急件 | emergency | 0 | 0% |
| 補單 | retroactive | 0 | 0% |
| — 其中插單(expedite) | expedite | 0 | 0% |

> PIR:本 repo 尚無 PIR issue(label=pir)。

## 六、稽核結論

- 期間內政策檢查共執行 **64** 次,攔截(failure)**0** 次。
- 已合併變更(PR)**28** 件,全部須通過上述護欄方可合併。
- 每項技術控制均對應具體 ISO 控制項編號(見第一節),可供稽核逐項查核。
- 端到端黃金路徑部署 **2** 件,其中 **1** 件七階段物證齊備(見第四節),體現「請求→部署→CMDB」全程可追溯。
- 變更共 **4** 件,其中例外(急件+補單)**0** 件、插單 **0** 件(見第五節);例外受控且護欄全程不鬆綁。

> 本報告為自動產出之合規證據(ISO 27001 A.5.36 / ISO 20000 服務報告)。