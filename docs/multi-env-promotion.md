---
title: 多環境晉級與過版 — build once, promote the same digest
type: design
created: 2026-06-15
updated: 2026-06-15
status: blueprint（待核准後逐 TASK 執行）
tags: [promotion, multi-env, release, environments, gitops, change-management, itil, iso20000, iso27001, golden-path]
---

# 多環境晉級與過版（test → UAT → 正式）

> **這是藍圖（blueprint），不是實作。** 依 `CLAUDE.md` 鐵則:逐 TASK、每步停下確認、不跳階段、決策留痕。
> 黃金路徑(`docs/golden-path-request-to-deploy.md`)目前只有一區。本文件把它延伸成
> 「**一個產物經測試 → 驗收 → 正式逐區晉級**」的過版流程。
>
> 對應工作分解見 `PROJECT_PLAN.md` 的 **Phase F**;關鍵決策見 `docs/adr/0004-multi-env-promotion.md`;
> 識別子觀念見 `docs/provenance-and-identifiers.md`。

## 1. 一句話總結

> **Build 一次、簽一次,然後讓「同一個 digest」一路往下搬**(測試 → UAT → 正式)。環境之間
> **不重編譯**——差異只在 config,不在 artifact。**過版 = 一張只把目標環境 digest 往前推的 PR。**

## 2. 鐵律:promote the artifact, not the source

```
build 一次（CI）──▶ image digest（簽章一次,tag = app commit SHA）
   │   ★ 同一個 digest 一路往下搬,每一區都不重編
   ├─ 測試區   deploy → 跑測試 → 通過
   ├─ 驗收區(UAT) promote(同 digest)→ 業務驗收
   └─ 正式區   promote(同 digest)→ CAB 核准 → 部署
        每一區:重跑 D5 驗章 + 自己的 config + 自己的 CMDB CI + 自己的漂移對帳
```

**為什麼**:正式區若「重新 build」,digest 與測試區**不一樣** → 你測的不是你上線的。看到正式 digest ≠ 測試 digest,就代表流程被破壞了。

> **例外**:若正式真需要不同 image(如 base image 打 patch),那是**一個新 build,必須從測試區重走一遍**,不能只在正式區改。

## 3. 同一個 image,不同的只有 config

| 跨環境**不變** | 隨環境**變** |
|---|---|
| 程式碼 / image digest / 簽章 | 連線字串、DB host、資源上限 |
| (= 你測過的那包) | feature flag、log level、**密鑰** |

- **同一 artifact + 不同 config**,config 部署時注入。
- image 的**名字/registry 可不同**(銀行常每區一個 registry),但 `@sha256:…` **必須一樣**;用 digest 複製會保留 digest,**簽章跟著有效**(簽章對 digest 簽,不綁 registry 路徑)。
- **密鑰絕不進 git**(gitleaks 已焊死);正式 = Vault / KMS,runtime 注入。

## 4. 目錄結構（環境即程式碼）

```
deployments/{test,uat,prod}/<app>.yaml   同一個 digest,各自 config
iac/environments/{test,uat,prod}/         每區一份環境配置
cmdb/{test,uat,prod}/                      每區一個 CMDB CI + 各自漂移對帳
```

> PoC 用多個本機 podman「環境」模擬;正式 = 分離的 registry / 叢集 / 網路區。

## 5. promote PR 怎麼設計（核心）

### 5.1 PR 只動一件事

promote PR **只動目標環境 DeploymentRequest 的 `source` 區塊**,config 一律不碰:

```diff
# deployments/prod/<app>.yaml
 spec:
   source:
-    version:  v1.2.2
-    digest:   "sha256:OLD..."
-    gitCommit: "abc123"
+    version:  v1.2.3
+    digest:   "sha256:NEW..."   # ← 從 uat CMDB 取得、已驗章的那個
+    gitCommit: "def456"
   runtime:               # ← 不動！prod 自己的 config
     httpPort: 9080
```

審核者看到的就是:「**從 digest X 換成 digest Y,其他沒動。**」這是 promote PR 的靈魂。

### 5.2 由腳本生成,絕不手貼 digest

```
promote.yml（workflow_dispatch: from=uat, to=prod, app=...）
   └─ scripts/promote.py
        ├─ 讀「來源環境的 CMDB CI」cmdb/uat/<app>.yaml  ← 已確認跑通+驗章的真相
        ├─ 把 digest/gitCommit/gitTag 寫進 deployments/prod/<app>.yaml 的 source
        ├─ 不碰 prod 的 runtime/config
        └─ 開 PR,body 自動填「過版單」
```

> 讀 **CMDB(確認態)**,不是來源的 DeploymentRequest(期望態)——**你只能 promote「上一區真的跑通且驗過章」的東西。**

### 5.3 三道 promote 專屬閘門（`policy-promote`）

| 閘門 | 擋什麼 | 為什麼 |
|---|---|---|
| **Diff 範圍守衛** | PR 改了 `source` 以外(程式、護欄、別環境、runtime config) | promotion ≠ 夾帶私貨 |
| **血統 + 順序守衛** | 要 promote 的 digest 不存在於「上一區」CMDB | 禁跳關、只能 promote 通過前一關的 |
| **重新驗章** | 在目標環境重跑 D5 deploy gate(digest + 簽章) | 每區各自驗,上一區綠 ≠ 這區綠 |

外加既有必過檢查(secrets/structure/iac/cmdb-validate)照跑。

### 5.4 SoD / 核准

- **CODEOWNERS**:`deployments/prod/` 指定變更權責者(平台+資安)→ **prod promote PR 需其核准**(CAB-as-code)。
- 低區(test)走 `standard` 自動;正式走 `normal` 需核准;緊急 hotfix 走 **Phase E 急件**(先做後審 + 強制 PIR),digest 一樣要簽要驗。

### 5.5 合併後 & 回退

- 合併 promote PR = **過版事件**(merge SHA = 過版身分)→ 部署目標區 → 登錄該區 CMDB → 漂移對帳。
- **回退**:`git revert` 那張 promote PR → digest 退回上一個已知良好值 → 重新部署。**GitOps 式回退。**

## 6. 過版單 = PR（留痕）

promote PR body 自動帶:`app / from→to / 舊digest→新digest / 來源 commit SHA + tag / 觸發者 / 連回上一區證據(CMDB CI、測試結果)`。這張 PR **就是** ISO 20000 / A.8.32 意義下的過版變更紀錄。

## 7. 與其他 Phase 的關係

- **Phase D**:單一環境的部署黃金路徑(本 Phase 的地基)。
- **Phase E**:例外(急件/插單/補單)——正式區 hotfix 走急件路徑、過版頻率進例外統計。
- **Phase F(本文件)**:把單環境延伸成多環境晉級。

## 8. 範圍與非範圍

**範圍**:本機多 podman「環境」模擬 test/uat/prod;promote PR 機制 + 三道閘門 + CAB-as-code + GitOps 回退。
**非範圍**:真實分離網路/叢集;真實 registry 間 digest 複製(PoC 用本機 tag 模擬,文件標註正式做法);真實密鑰管理(以 gitleaks + 注入機制示意)。

## 9. 完成定義（Gate F）

見 `PROJECT_PLAN.md` Phase F 的 Gate F:同一 digest 能逐區晉級、promote PR 只動 source、三道閘門擋住跳關/夾帶/未驗章、正式需 CAB 核准、可 revert 回退——全數打勾才算完成。

## See Also
- `docs/provenance-and-identifiers.md`（identifiers:為何釘 digest、記 commit SHA）
- `docs/adr/0004-multi-env-promotion.md`（決策）
- `docs/golden-path-request-to-deploy.md`（Phase D 單環境黃金路徑）
- `docs/exception-and-drift-governance.md`（Phase E 例外,正式 hotfix 走急件）
- `docs/cmdb-and-evidence-chain.md`（D7 CMDB,promote 的確認態來源）
- `deployments/README.md`（部署請求即程式碼）
