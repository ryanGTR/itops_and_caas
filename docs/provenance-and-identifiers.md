---
title: 識別子與血統 — branch / tag / commit SHA / image digest 各自的角色
type: reference
created: 2026-06-15
updated: 2026-06-15
tags: [provenance, git, commit-sha, tag, branch, image-digest, traceability, slsa, supply-chain, golden-path]
---

# 識別子與血統：branch / tag / commit SHA / image digest 各自的角色

> 觀念參考頁。整條黃金路徑的「可追溯性」都靠這幾個識別子各司其職。
> 核心一句:**人用 tag 挑、開發在 branch 進行、但只能用 SHA / digest「證明」。**

## 1. 四種識別子（一張表看懂）

| 識別子 | 是什麼 | 不可變? | 給誰用 | Java 類比 |
|---|---|---|---|---|
| **git commit SHA** | 源碼某一刻的內容指紋 | ✅ 內容定址 | 機器 / 完整性 | 某次原始碼狀態的 hash |
| **git tag**（`v1.2.3`） | 指向某 commit 的人類標籤 | ❌ 可移動/刪除 | 人 / 發布 | 賦值後「打算別動」的參考 |
| **git branch**（`main`） | 指向某 commit、且**會前進**的指標 | ❌ **最會動** | 人 / 工作流 | 一直 reassign 到新物件的可變變數 |
| **image digest**（`sha256:…`） | 建出來的映像內容指紋 | ✅ 內容定址 | 機器 / 完整性 | 那包 JAR / 容器的 checksum |

> **可變性光譜**:branch（一直動）→ tag（貼了別動，但能動）→ commit SHA / digest（永不變）。
> 完整性永遠錨在最右邊那兩個。

## 2. 兩個分類:身分錨點 vs 工作流

| 用途 | 工具 | 性質 |
|---|---|---|
| **追溯 / 完整性**(證明「就是這個」) | commit SHA、image digest | 不可變、內容定址 |
| **發布標記**(人挑哪一版) | git tag | 可變,約定別動(故需 protected / signed tag) |
| **工作流 / 協作**(開發在哪進行) | git branch | 可變、會前進 |

branch 不是完整性錨點——它是「變更怎麼流進來」的載體。我們**全程都在用 branch**(每個 TASK 開分支 → PR → main),但它不進「身分」那張表。

## 3. 兩個 repo、兩個 commit SHA（容易混）

這條路徑橫跨兩個 git repo,各有各的 SHA、意義不同:

| | repo | 那個 SHA 代表 |
|---|---|---|
| **App 源碼 SHA** | `supply-chain`(Java app) | **改了什麼程式碼** → 被 build 成 image(digest) |
| **變更紀錄 SHA** | `itops_and_caas`(本 repo) | **部署/過版這個決定**(DeploymentRequest 的 PR merge SHA) |

→「誰決定部署/過版」靠 itops 的 PR SHA(已有,每個 DeploymentRequest 都是 PR)。
→「部署的東西是哪段源碼編的」靠 app 的 commit SHA(provenance,建議記進 `source.gitCommit`)。

## 4. 為什麼部署紀錄記 commit SHA、不記 branch

若 DeploymentRequest 寫「deployed from `main`」,**五個 commit 後 `main` 早就不是當時那個**,等於沒記。要記的是「當下指到的 **commit SHA**」——branch 名對稽核無意義,**只有 SHA 可重現**。

> 規則:**provenance 欄位記 `gitCommit`(SHA),不記 `gitBranch`。**

## 5. 環境也不用 branch 表示

老式 GitOps 會 branch-per-env(`main`→prod)。本平台**用資料夾 `deployments/<env>/` 代表環境**,不綁分支。原因:環境狀態是**宣告式設定**(可 diff、可 review),不該綁在會動的分支上。**branch 負責「變更怎麼流進來」,不負責「環境長怎樣」。**

## 6. 完整血統鏈（identifiers 怎麼串）

```
[app repo]  commit SHA ──build──▶ image digest ──sign──▶ 已簽映像
   │  (D4: image_tag 預設 = github.sha,                │
   │   映像 tag 即 app commit SHA)                      │
   ▼                                                    ▼
[itops repo] DeploymentRequest(記 digest + gitCommit)─驗章─部署─CMDB
                      │
                      └ 這份檔的 PR merge SHA = 變更/過版紀錄的身分
```

- **build once**:一個 commit → 一個 digest,簽一次。
- **promote**:同一個 digest 跨環境搬,**不重編**(見 `docs/multi-env-promotion.md`)。
- **tag 治理**:release 用 annotated + signed + protected tag;但**部署釘 digest**,tag 只是入口。

## 7. 對漂移偵測的意義

reconcile 抓到線上 running digest 後可**回連 commit SHA**:若這個 digest 對不到任何「來自已知 commit + 已簽」的建置 → 就是來路不明的映像。**commit SHA 讓漂移偵測從「比對數字」升級成「驗證血統」。**

## See Also
- `docs/multi-env-promotion.md`（多環境晉級 / 過版,build once promote）
- `docs/supply-chain-signing.md`（D4:build→簽章,image_tag=commit SHA）
- `docs/cmdb-and-evidence-chain.md`（D7:CMDB 記 digest,漂移對帳）
- `docs/deploy-gate.md`（D5:驗章釘 digest）
- `docs/exception-and-drift-governance.md`（Phase E:漂移偵測用得上血統）
