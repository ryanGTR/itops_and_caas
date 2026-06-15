---
title: ADR-0004 多環境晉級與過版：build once, promote the same digest
type: adr
created: 2026-06-15
updated: 2026-06-15
status: accepted
tags: [phase-f, promotion, multi-env, release, gitops, change-management, iso27001, iso20000]
---

# ADR-0004：多環境晉級與過版

> ADR：記錄「為什麼這樣決定」。延續 ADR-0001/0002/0003 的稽核留痕文化。
> 本 ADR 服務於 `docs/multi-env-promotion.md`。

## 脈絡（Context）

黃金路徑(Phase D)只示範了單一環境。真實銀行交付必經 **測試 → 驗收(UAT) → 正式** 逐區晉級(過版)。需在本機、零雲端的 PoC 限制下,示範一條**可稽核、防出錯、可回退**的過版流程,並把「環境差異」與「產物完整性」清楚切開。

## 決策（Decisions）

| 項目 | 選擇 | 為什麼 |
|------|------|--------|
| 晉級單位 | **同一個 image digest**(build once) | 「測的就是上線的」;重編譯=斷鏈,稽核必挑 |
| 環境表示 | **資料夾 `deployments/<env>/`**,非 branch-per-env | 環境是宣告式設定,不綁會動的分支 |
| 環境差異 | **只在 config**(env vars / 資源 / 密鑰),image 不變 | 12-factor;同一 artifact 跨環境 |
| 過版動作 | **一張只改目標環境 `source.digest` 的 PR** | 最小 diff、最易審、可 revert |
| 過版來源真相 | **上一區的 CMDB CI(確認態)**,非 DeploymentRequest(期望態) | 只能 promote「真的跑通且驗過章」的 |
| 過版生成 | `promote.py` + `promote.yml`(workflow_dispatch) 生成 PR | 禁手貼 digest(必出錯) |
| 過版閘門 | **`policy-promote`**:Diff 範圍 / 血統+順序 / 重新驗章 | 擋夾帶、擋跳關、每區各自驗 |
| 完整性錨點 | **digest**(tag 可變,只當入口) | 人用 tag 挑、系統用 digest 釘 |
| 正式核准 | **CODEOWNERS on `deployments/prod/`**(CAB-as-code) | 正式過版需變更權責者核准(SoD) |
| 回退 | **`git revert` promote PR** | GitOps 式回退到上一已知良好 digest |
| 緊急過版 | 走 **Phase E 急件**(先做後審 + PIR),技術閘門不鬆綁 | 例外有受控通道,護欄不變 |

## 關鍵取捨:跨環境什麼變、什麼不變

| | 跨環境不變 | 隨環境變 |
|---|---|---|
| 內容 | image digest / 簽章 / 程式碼 | config / 密鑰 / 資源大小 / replica |
| 識別 | digest(釘) | image 名/registry、image tag(入口) |

> 一句話:**速度與差異化妥協在「config / 名字」,絕不妥協在「digest / 簽章 / 可稽核性」。**

## 過版的 PoC vs 正式環境

| | PoC(本專案) | 銀行正式環境 |
|---|---|---|
| 環境 | 多個本機 podman「環境」 | 分離網路區 / 叢集 |
| 跨區搬 image | 本機共用 / tag 模擬 | registry 間用 digest 複製(簽章隨之有效) |
| 正式 build? | 否(promote 同 digest) | 否(正式只驗章不 build,離線 cosign verify) |
| 核准 | CODEOWNERS(SOLO 以文件對映多人) | 真實 CAB / 維護窗口 |

## 後果（Consequences）

- ✅ 「build once, promote」杜絕「測的不是上線的」這個稽核高頻缺失。
- ✅ promote PR 是最小 diff,審核成本低、可 `git revert` 回退。
- ✅ 三道 `policy-promote` 閘門把「跳關 / 夾帶 / 未驗章」焊死,不靠人記得。
- ✅ 環境差異收斂在 config,完整性錨在 digest,兩者不混。
- ⚠️ PoC 用本機模擬多環境與 registry 間複製,與真實網路分區有差,需文件標註。
- ⚠️ 多環境會放大「config 重複」——需注意 DRY(共用基底 + 各區覆寫),屬後續最佳化。
- ⚠️ 正式 CAB 多人核准在 SOLO 單人 repo 只能以文件對映,非真演。

## 核准與執行

本 ADR 已 **accepted**(2026-06-15,Ryan 審核藍圖與本 ADR 後核准)。依 `PROJECT_PLAN.md` Phase F 逐 TASK 執行(F1 多環境骨架起)。

## See Also
- `docs/multi-env-promotion.md`（藍圖）
- `docs/provenance-and-identifiers.md`（identifiers / 血統）
- `docs/adr/0002-openliberty-runtime-and-deploy.md`（單環境部署決策）
- `docs/adr/0003-exception-path-and-drift.md`（例外路徑,正式 hotfix 走急件）
- `PROJECT_PLAN.md`（Phase F）
