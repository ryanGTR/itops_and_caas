---
title: Session 接續狀態(repo 自足的 handoff)
type: handoff
updated: 2026-06-16
---

# Session 接續狀態 — repo 自足版

> 這份把「原本只在 Claude 跨 session 記憶裡」的脈絡/決策/踩雷,固化進 **repo 本身**。
> 目的:**不依賴任何外部記憶**,光靠這個 git repo 就能讓任何人 / 任何工具 / 任何新 session 接續。
> 搭配 [`TODO.md`](../TODO.md)(待辦 + 操作步驟)一起看。

## 1. 現在到哪了(2026-06-17)

itops 從「治理 PoC」做成「真被用、看得到、可治理的活系統」。本波 PR #28~#45 全合進 main
(#41~#43 iTop 真整合、#44 iTop config 收唯讀、#45 治理三視圖互通=A 收口完成):
- **測試 gate**(兩層 fail-closed)、**真 live 端到端**(四環境同 digest、build once promote)
- **收口**:COMPLIANCE_MAP 補 D/E/F、`docs/case-study.md`、`docs/everything-as-code-journey.md`
- **真整合**:`integration/`(supply-chain build/test/sign → handoff manifest → itops 驗章/部署/CMDB)
- **可視化**:`docs/governance-console.html`(後台)、`scripts/ticket_trace.py`(單據鑽取)、`docs/cmdb-topology.html`
- **真 VM 部署目標**:`scripts/deploy_openliberty_vm.sh` + `iac/environments/vm-openliberty/`(OpenTofu→QEMU VM→OpenLiberty)
- **CMDB 多層拓樸**:`cmdb_register/validate/topology.py`(host→middleware→software,15 CI)

## 2. 現在「活著」的東西(實際狀態,別只信文件)

> **2026-06-16 早上更新**:Ryan 上班,本機資源已全部關閉(VM + iTop 容器 destroy/stop)。
> 重站方式都在文件裡,不依賴本機殘留狀態。

- **✅ 主線完成:itops × iTop(Combodo)真整合** — 見 `integration/itop/README.md`(PR 待合)。
  iTop 3.2.2 完整 ITIL 模型(220 表)+ REST + 服務帳號 + `itop_sync.py`(五環境 15 CI 跑通,冪等)。
  重站 = `bash integration/itop/setup-itop.sh`(已腳本化,~3 分鐘);觸發點在 `itops_ingest.sh`(opt-in `ITOP_SYNC=1`)。
- QEMU VM `itops-ol-vm`:已 `tofu destroy`(原服務於 192.168.122.180:9080)。重開 = `scripts/deploy_openliberty_vm.sh`。
- podman 容器已清空。`git status` 應乾淨。

## 3. 關鍵設計決策(為什麼這樣做)

- **護欄不是閘門 / build once promote / 鬆綁審核不鬆綁護欄 / 補單≠漂白 / fail-closed**(招牌論述,見 case-study)。
- **itops 與 supply-chain 各司其職**:supply-chain = 左側(掃描/簽章);itops = 右側部署治理(驗章/promote/CMDB/變更)。靠 handoff manifest 串,**不互相重做**。
- **CMDB 是 CI + 關係拓樸**(host→middleware→software);itops 版賣點在 as-code + 版控,但**仍非真企業 CMDB**(無網路/DB/服務依賴、無 discovery)。
- 部署目標:podman 容器 → 真 QEMU VM(更貼近銀行「部署到主機」)。

## 4. 踩過的雷(再做別重踩)

- **btrfs + qcow2 雙重 CoW 會開機 I/O 卡死**:映像目錄 `chattr +C`(No_COW);輕量單 VM 不觸發,重負載才需要。(= k8s-lab 同款雷)
- **dmacvicar/libvirt provider 0.9.x 是低階 XML API**,不相容友善寫法 → **釘 0.7.6**。
- **缺 mkisofs** → `pacman -S cdrtools`。
- **qemu:///session 在此機 daemon 佈局不順** → 用 `qemu:///system + default pool`(root 讀家目錄 base image)。
- **VM→host TCP 被 libvirt 擋** → 推檔走 **SSH/scp host→VM**(正常方向)。
- **zsh 不對未引用變數分詞** → ssh `-o` 旗標要 inline,別塞變數。
- **WAR 是 Java 21 編譯、VM 預設 Java 17**(class 65 vs 61)→ 裝 Temurin 21。
- **多層 CMDB 後 self-test 用 `next(rglob)` 可能抓到 host CI**(無 source/runtime)→ 過濾 `type==deployed-application`。
- **加新 required check 順序雷**:該 check 的 workflow 要先在 main 才能設 required。
- **iTop 安裝模組清單要填「真實模組名」**(`itop-datacenter-mgmt`…),不是 installation.xml 的 `extension_code`
  (`itop-config-mgmt-datacenter`…)——後者被靜默忽略 → 只裝出最小模型(只有 Person)。驗收要查類別,別只看表數。
- **iTop install 用 root CLI 跑 → 檔案 root:root + DB root 限 unix_socket**:必須 chown 給 www-data + 建專用 DB 帳號。
- **iTop 3.2.x REST 閘門 = `secure_rest_services`+`HasProfile('REST Services User')`**;`allowed_rest_profiles` 無效。
- **runit 容器別 `apachectl -k graceful`**(會起 rogue apache)→ 改 `podman restart`。以上都已固化進 `integration/itop/setup-itop.sh`。
- token/密鑰一律走環境變數/keyring,別貼對話、別進 commit。

## 5. 怎麼接著做

見 [`TODO.md`](../TODO.md)。**2026-06-17 更新**:
- **A 收口/可見性 = 已完成**(PR #45 治理三視圖互通;PR #44 iTop config 收唯讀)。
- **B 主線「已畢業」搬進 `supply-chain-demo` repo**(`~/Documents/supply-chain/github/app/`),
  **不在本 itops repo**。B 的單一真相是 `~/Documents/supply-chain/itops-l4-integration-plan.md`
  (Tier1 已 merged、Tier2 在 PR #45 開著、T2.4/T2.5/T2.6 待續)。本 repo 的 itops 是右側治理的
  「來源/參考實作」,被移植過去當 supply-chain 的 L4。
- C 補強 / D 清理仍在本 repo。

驗證當前可跑:`scripts/cmdb_validate.py`、`scripts/tests/*/selftest.sh`、`git log`。

## 6. 操作慣例

逐項做 → 開分支 → PR → **7 道必過檢查綠**(policy-secrets/structure/iac、cmdb-validate、deploy-gate-selftest、change-class、promote-gate)→ squash 合併。護欄變更(policies/、workflows/、scripts 閘門)PR 標「需資安審核(SoD)」。`main` 禁直接 push。
