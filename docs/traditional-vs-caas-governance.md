---
title: 傳統 VM 治理 vs CaaS 治理 — 同一套合規論述的演進
type: explainer
created: 2026-06-05
updated: 2026-06-05
tags: [governance, vm, caas, kubernetes, openscap, kyverno, compliance, positioning]
status: draft
---

# 傳統 VM 治理 vs CaaS 治理

> 用途:對 CAB / 稽核 / 內控溝通時,說明「我們不是丟掉傳統治理,而是把它
> 自動化、左移、變成預設且無法繞過」。這是本 PoC 的核心賣點之一,接續
> `COMPLIANCE_MAP.md` 開頭「人工審核 vs 自動化護欄」那張表,延伸到容器層。

## 一、為什麼要寫這份

銀行既有的治理是圍繞 **VM / 虛擬機**建立的(你熟的 RHEL / 企業世界)。
要說服 CAB 與稽核接受容器/Kubernetes,不能只說「比較潮」,而要證明:
**每一個傳統控制點,在新平台都有對應,而且更強。**本文逐項對照。

## 二、傳統用 VM,這套東西怎麼做?

同樣要達成「部署 App + 強制治理合規」,傳統企業的生命週期大致如下:

| 階段 | 傳統 VM 做法 | 用到的東西 |
|------|------------|-----------|
| 供裝 | 從 golden image 複製 VM | VMware vSphere / RHV / 裸機 |
| 部署 | SSH 手動 or 推送腳本;打包成 RPM,用 systemd 拉起 | Ansible / Shell / RPM |
| 設定管理 | 維持各機狀態一致、防飄移 | Puppet / Chef / Ansible |
| 合規治理 | SOP 文件 + CAB 人工審核;**上線後**才掃描基線與弱點 | OpenSCAP / Nessus / 稽核抽查 |
| 隔離 | 一台 VM 跑少數 App,靠 hypervisor 隔離 | Hypervisor |

## 三、對照:傳統 VM ↔ 本 PoC 的 CaaS

| 面向 | 傳統 VM 做法 | CaaS 做法(Phase 3) |
|------|------------|---------------------|
| 供裝 | golden image 複製 VM(重、開機慢、利用率低) | kind / K8s 宣告式(輕、秒級、高密度) |
| 部署模型 | **push**:人主動連進去改 | **pull / GitOps**:叢集自己收斂到 Git 宣告狀態 |
| 部署工具 | Ansible / RPM + systemd | ArgoCD |
| 飄移 | 常見(手改沒留記錄) | 自動收斂、Git 可溯,飄移即被糾正 |
| 合規時機 | 上線**之後**掃描 | 進叢集**之前**攔截(admission) |
| 合規覆蓋 | 抽樣 | 100% |
| 合規靠什麼 | SOP + CAB 人工判斷 | Kyverno 政策即程式碼 |
| 不合規結果 | 事後發現 → 開單修 | **根本進不來**,附明確理由 |
| 稽核證據 | 工單 / 簽核文件 | Git 歷史 + admission log |

> Java 類比:Kyverno 之於叢集,像 AOP 攔截器 / Bean Validation 掛在系統入口
> ——每個請求進來都先過驗證,不合規直接擋,而不是上線後再 code review。

## 四、關鍵反駁:「傳統 VM 也能自動化啊?」(OpenSCAP 角度)

這是稽核或資深 RHEL 工程師一定會問的。**誠實回答:對,傳統也在往自動化走。**

- **OpenSCAP** 可以用 SCAP/CIS/STIG 基線自動掃 RHEL,甚至 `oscap-anaconda-addon`
  在裝機時套用基線;Ansible 也能把修補自動化。
- 所以「自動 vs 手動」不是非黑即白——傳統那端也在進步。

那真正的**質的差異**是什麼?三點:

1. **預設即合規(Secure by Default)**
   OpenSCAP 多半是「掃出偏差 → 再修」;K8s 的 Kyverno + 合規模組是「**一開始就開不出不合規的東西**」。前者是糾正,後者是預防。

2. **無法繞過(unbypassable)**
   VM 上的基線掃描,管理員仍可手動關掉服務、改設定、跳過掃描(有 root 就有後門)。Kyverno 是 admission controller,**所有**進叢集的請求都過它,連叢集管理員的部署也擋;搭配 GitOps,連「手改」這條路都被堵死。

3. **左移(shift-left)+ 即時**
   OpenSCAP 通常在「機器已經跑起來」之後掃;政策即程式碼可以在 **PR 階段**(用 Kyverno CLI / checkov)就先驗,問題在合併前就攔下,而非上線後。

一句話:**傳統是「事後稽核求補救」,平台是「事前護欄求預防」。**兩者不互斥——
最佳實務是兩層都有,但把重心從「人盯」移到「機器擋」,從稽核角度是**降低風險**。

## 五、貫穿三階段的同一套論述

這套「人工 → 自動護欄」的論述,在本 PoC 一路貫穿、層層下沉:

| 層 | 階段 | 護欄機制 | 傳統對應 |
|----|------|---------|---------|
| 原始碼 / 變更 | Phase 1 | GitHub Actions(機敏掃描、結構檢查)+ branch protection | 人工 code review + 變更單 |
| 基礎設施 | Phase 2 | OpenTofu 合規模組 + checkov 閘門 | 手寫設定 + 上線後弱掃 |
| 容器 / 執行期 | Phase 3 | ArgoCD GitOps + Kyverno admission | VM golden image + OpenSCAP 事後掃 |

→ 同一句話講三遍:**把合規寫成程式碼、變成預設、自動執行、無法繞過、全程留痕。**

## See Also

- `COMPLIANCE_MAP.md` — 技術控制 ↔ ISO 27001 / 20000 對照(本文的論述根基)
- `docs/adr/0001-phase2-iac-stack.md` — Phase 2 技術棧決策
- (待補)`docs/adr/000x-phase3-caas-stack.md` — Phase 3 CaaS 技術棧決策(若 Phase 3 動工)
