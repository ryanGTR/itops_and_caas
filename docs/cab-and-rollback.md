---
title: 正式區核准（CAB-as-code）與 GitOps 回退演練
type: design
created: 2026-06-15
updated: 2026-06-15
status: implemented（TASK-F4）
tags: [cab, ecab, sod, codeowners, rollback, revert, gitops, change-management, itil, iso20000, iso27001, phase-f]
---

# 正式區核准（CAB-as-code）與 GitOps 回退演練

> **一句話**：正式環境的過版多一道**人工核准閘**（變更權責者 / CAB），但回退不靠手動改回去，而是
> **前向 `git revert`**——歷史只進不退，revert commit 本身就是可稽核的回退軌跡。
>
> 這是 Phase F 的收關任務（TASK-F4），對應 `PROJECT_PLAN.md` 的 Gate F 最後一項。
> 過版的技術三閘門見 `docs/multi-env-promotion.md` 與 `validate_promote.py`（TASK-F3）；
> 本文件補上「正式區的人工核准」與「出事怎麼退」。

## 1. 設計總則：鬆綁對象/時點，不鬆綁技術閘門

延續 Phase E 的鐵則。正式過版相較於 test/uat **只多一件事：一個獨立的人工核准**。
技術安全閘門（範圍守衛 / 血統+順序 / 重新驗章 / 簽章 / 掃描）對所有環境**一律強制、不因環境放寬**。

| 環境 | 過版誰可合併 | 技術閘門（policy-promote 等） |
|---|---|---|
| sandbox | 走部署黃金路徑，非 promote | 全程強制 |
| test / uat | 開發者自助過版（無額外 code owner） | 全程強制 |
| **prod** | **變更權責者（CAB）核准**（CODEOWNERS 強制） | 全程強制 |

> 重點：prod 多的是「對象（誰能批）」這道**人工**閘，不是放寬任何**技術**檢查。

## 2. CAB-as-code：把 ITIL 的 CAB 寫進 CODEOWNERS

ITIL 的 **CAB（Change Advisory Board，變更諮詢委員會）** 與緊急時的 **ECAB**，
在本平台落成兩行 `CODEOWNERS`：

```gitignore
# 正式環境過版:CAB-as-code,需「變更權責者」核准(TASK-F4)
/deployments/prod/          @ryanGTR
```

任何動到 `deployments/prod/` 的 PR（即 prod 過版單）→ GitHub 自動要求對應 code owner 核准。
這就是「**正式過版需獨立核准軌跡**」的技術強制：核准事件記在 PR 上，可稽核、不可繞過。

### 單人 → 多人對映（正式落地）

本 repo 在個人帳號下，所有 owner 暫共用 `@ryanGTR`（個人帳號無法核准自己的 PR，故無法達成真正
SoD——這是已知限制，見 `CODEOWNERS` 註解）。正式落地時替換為 organization team：

| 角色 | PoC 暫用 | 正式對映 | 適用 |
|---|---|---|---|
| 常規正式變更核准 | `@ryanGTR` | `@org/change-advisory-board` | normal change，CAB 例會核准 |
| 緊急正式變更核准 | `@ryanGTR` | `@org/ecab` | emergency change，先核後審，仍受 PIR 約束（見 `docs/exception-and-drift-governance.md`） |

### 讓它有強制力

`CODEOWNERS` 只「指定 owner」；真正的強制來自 branch protection 開啟
**Require review from Code Owners**——見 `scripts/setup_branch_protection.sh`
（嚴格 SoD 模式 `REQUIRE_CODEOWNER=true`；個人帳號的 `SOLO=1` 模式下無法自我核准，
此為帳號數限制而非設計缺陷）。

## 3. GitOps 回退：`git revert`，不是手動改回去

正式部署的 digest 在版控裡，所以回退 = 對「上一個過版 commit」做 `git revert`：

- **歷史只進不退**：不 `reset`、不強推；revert 新增一個 commit，把 digest 換回上一個已知良好值。
- **revert commit 即回退軌跡**：誰、何時、從哪個 digest 退到哪個，全留在 git 史（A.8.32 變更管理 / 可追溯）。
- **退回去的也受閘門**：回退後重新部署，照樣經過 policy-promote / D5 重新驗章——退回去的同樣是已驗章產物。
- **回退也走 PR + CAB 核准**：revert 一樣是動到 `deployments/prod/` 的變更，照樣要變更權責者核准（SoD 不開後門）。

runbook-as-code：`scripts/rollback.sh`（預設 dry-run，`--apply` 才真的 revert）。

```bash
# 預覽會退到哪個 digest(不動任何東西)
scripts/rollback.sh --app supply-chain-backend --env prod
# 確認後執行:新增 revert commit,推上去開回退 PR,經 CAB 核准後合併,再重新部署
scripts/rollback.sh --app supply-chain-backend --env prod --apply
```

## 4. 回退演練紀錄（drill log）

於隔離 git 沙箱實跑一次「已知良好 → 過版到壞版本 → 回退」，證明可靠回退 + 留痕：

```text
場景:prod 過版到壞版本(digest bbbb…),需退回上一個已知良好(digest aaaa…)

===== 1) dry-run 預覽 =====
🔁 GitOps 回退 — supply-chain-backend @ prod
  目標檔        :deployments/prod/supply-chain-backend.yaml
  欲回退 commit :96ce562 [promote] supply-chain-backend: uat → prod(只改 source.digest)
  目前 digest   :sha256:bbbb…bbbb
  回退後 digest :sha256:aaaa…aaaa(上一個已知良好)
  （dry-run:未變更。）

===== 2) --apply 真的回退 =====
▶ git revert --no-edit 96ce562   @ 2026-06-15T06:10:05Z
[master b07c10f] Revert "[promote] supply-chain-backend: uat → prod(只改 source.digest)"
✅ 已回退:digest 現為 sha256:aaaa…aaaa
  回退軌跡 = 新增的 revert commit:b07c10f

===== 3) 驗證 =====
    digest: "sha256:aaaa…aaaa"        # 確實退回已知良好
b07c10f Revert "[promote] ... uat → prod"   ← 回退軌跡(前向新增)
96ce562 [promote] ... uat → prod            ← 壞版本(被退)
a545184 deploy prod: 已知良好版 v1
```

**結果**：digest 可靠退回上一個已知良好；回退以新增 revert commit 的方式留痕，歷史完整可追溯。

## 5. 對應治理控制項

| 控制項 | 如何滿足 |
|---|---|
| ISO 27001 A.5.3 職責分離 | prod 過版／回退需變更權責者（CAB）以 code owner 核准，與提交者分離 |
| ISO 20000 變更管理（回退） | `git revert` 可靠回退到前一已知良好，revert commit 留痕 |
| ISO 27001 A.8.32 變更管理 | 正式變更／回退皆走 PR + 核准 + 必過閘門，全程可追溯 |
| ITIL CAB / ECAB | CODEOWNERS 把常規／緊急核准對映到 CAB／ECAB team |

## See Also

- `docs/multi-env-promotion.md` — 多環境晉級與過版藍圖（build once, promote）
- `docs/exception-and-drift-governance.md` — 急件 / ECAB / PIR / 漂移治理
- `scripts/validate_promote.py`、`.github/workflows/policy-promote.yml` — 過版技術三閘門（TASK-F3）
- `scripts/rollback.sh` — GitOps 回退 runbook-as-code（TASK-F4）
- `scripts/setup_branch_protection.sh` — 讓 CODEOWNERS 具強制力
