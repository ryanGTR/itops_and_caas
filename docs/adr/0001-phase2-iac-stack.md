---
title: ADR-0001 Phase 2 IaC 技術棧與本機模擬決策
type: adr
created: 2026-06-05
updated: 2026-06-05
tags: [phase2, iac, opentofu, localstack, podman, checkov]
status: accepted
---

# ADR-0001:Phase 2 IaC 技術棧與本機模擬決策

> ADR(Architecture Decision Record):記錄「為什麼這樣決定」。
> 銀行稽核特別在意決策留痕,本檔即此用途。

## 脈絡(Context)

Phase 2 要把 Phase 1 的「護欄即程式碼」概念延伸到基礎設施層:
讓開發者開出來的雲端資源「預設就合規」。需要在**個人筆電、零雲端成本**下
能開發與驗證,且符合本專案公開 PoC 的定位。

## 決策(Decisions)

| 項目 | 選擇 | 為什麼 |
|------|------|--------|
| IaC 工具 | **OpenTofu**(非 Terraform) | 開源(MPL),與 Terraform 相容;契合公開 PoC 與避免 BSL 授權疑慮 |
| 雲端模擬 | **LocalStack**(本機跑) | 不連真 AWS,零成本;`apply` 出的資源真的被建立,流程與真 AWS 一致 |
| 容器執行 | **Podman**(非 Docker) | daemonless、可 rootless,安全姿態較佳;符合 RHEL 生態與 hardening 取向 |
| IaC 政策閘門 | **checkov** | 靜態掃 HCL,規則對應 CKV 編號便於 ISO 對照;de-facto IaC 合規掃描器 |

## 合規基線與「可稽核豁免」(SoA 精神)

checkov 對 S3 有數十條檢查。我們**明確宣告**核心安全基線為:加密、封鎖公開
存取、版本控制、強制標籤。其餘(跨區複寫、生命週期、事件通知、存取日誌)
在 `iac/.checkov.yaml` 以 `skip-check` 做**有意識、可稽核的豁免**,每條附理由
——類比 ISO 27001 的 SoA(適用性聲明)。詳見 `iac/README.md`。

## 後果(Consequences)

- ✅ 開發者只需呼叫合規模組,開不出不合規資源(護欄而非閘門)。
- ✅ checkov 閘門可在 CI 自動擋下違規 IaC(待 workflow scope 後接 CI)。
- ⚠️ 合規價值(模組 + 閘門 + 違規測試)**不依賴 LocalStack**;LocalStack 僅供
  `apply` smoke test。

## 已知問題(Known Issue):LocalStack 大映像拉取

在某些網路下,`podman pull localstack/localstack`(大映像)會在 **IPv6 連到
Docker CDN(CloudFront)時讀取逾時**(小映像正常)。

錯誤樣態:`read tcp [2001:b011…]→[2600:9000…]:443: connection timed out`

緩解(擇一):
1. **換網路**(最簡單;不同網路的 IPv6/CDN 狀況不同)
2. **強制 IPv4**:拉取前 `sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1`,拉完再設回 `0`
3. **公司 Nexus pull-through**(若 `nexus.corp.local:5000` 有代理 Docker Hub)

拉取與啟動指令見 `scripts/localstack-up.sh`。
