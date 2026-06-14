---
title: ADR-0002 部署黃金路徑：OpenLiberty 執行環境與部署/簽章決策
type: adr
created: 2026-06-14
updated: 2026-06-14
status: accepted
tags: [phase-d, openliberty, podman, opentofu, cosign, cmdb, itil, supply-chain]
---

# ADR-0002：部署黃金路徑的執行環境與部署/簽章決策

> ADR：記錄「為什麼這樣決定」。延續 ADR-0001 的稽核留痕文化。
> 本 ADR 服務於 `docs/golden-path-request-to-deploy.md`（需求單 → 部署 OpenLiberty）。

## 脈絡（Context）

要在**個人筆電、零雲端成本、公開 PoC** 的限制下，示範「一個 Java 應用程式經治理化供應鏈安全部署到應用伺服器」的完整流程，並能對映 ISMS / ITIL / ISO 20000 / 組態管理。需與既有選型（ADR-0001：OpenTofu + Podman + checkov）一致。

## 決策（Decisions）

| 項目 | 選擇 | 為什麼 |
|------|------|--------|
| 應用伺服器 | **OpenLiberty** | 開源（EPL）、輕量、雲原生取向的 Jakarta EE / MicroProfile runtime；符合 Ryan 的 Java 背景與銀行 Java 生態 |
| 執行載體 | **Podman 容器**跑 OpenLiberty 官方映像 | 與 ADR-0001 的 Podman 選型一致；daemonless/rootless、本機零成本、可重現 |
| 佈建工具 | **OpenTofu** 模組 `openliberty-service` | 與 ADR-0001 一致；「填參數即開出預設合規的 runtime」（護欄而非閘門） |
| 部署產物形式 | **容器映像**（OpenLiberty base + 應用層），非 WAR 手動丟入 | 不可變部署、可簽章可驗章、digest 可登錄 CMDB |
| 簽章工具 | **cosign** | de-facto 容器簽章；補上 supply-chain 專案的 L4 缺口 |
| 簽章信任模式 | **PoC＝cosign 金鑰對（key-pair）**；文件標註**銀行真實環境＝考慮 keyless/KMS** | 見下節「金鑰選型」 |
| 組態管理載體 | **CMDB-as-code**（`cmdb/*.yaml` + schema 驗證） | 一切即程式碼、版控即組態基線與變更史；零外部工具 |
| 服務請求載體 | **GitHub Issue Forms** | 結構化、可自動化讀取、不離開 Git；即 ISO 20000 服務目錄項目 |
| IaC 政策閘門 | 沿用 **checkov**（＋必要時 tfsec 補容器面向） | 與 ADR-0001 一致，規則可對映 ISO |

## 金鑰選型（cosign）— 這是 supply-chain 專案的待決缺口

| 模式 | 優點 | 缺點 | 用在 |
|------|------|------|------|
| **key-pair（本地金鑰）** | 離線可用、無外部相依、最易在筆電/氣隙環境重現 | 金鑰保管責任在自己（需妥善存放，**絕不進版控**） | **本 PoC ★** |
| **keyless（OIDC + Fulcio + Rekor）** | 無長期金鑰、有透明度日誌、供應鏈最佳實務 | 需連外部 CA/log，氣隙銀行環境受限 | 公開展示時的進階對照 |
| **KMS-backed（雲 KMS / HSM）** | 金鑰不落地、符合銀行金鑰治理 | 需雲/HSM 基礎設施 | **銀行真實環境建議** |

> 決策：**PoC 先用 key-pair**（公鑰入庫驗章、私鑰本地保管、`.gitignore` + gitleaks 雙重防進版控），並在文件明列「正式環境應升級為 KMS/HSM-backed」。此舉同時**收斂 supply-chain 專案「L4 簽章金鑰選型」的開放缺口**。

## 後果（Consequences）

- ✅ 一條可在筆電完整跑通、可稽核、可展示的部署黃金路徑。
- ✅ 治理價值（變更/SoD/驗章/組態/證據）**不依賴雲**；Podman+OpenTofu 本機即可。
- ✅ 三個旗艦專案（itops / supply-chain / OpenTofu IaC）縫成一個故事。
- ⚠️ OpenLiberty 容器映像體積較大，首拉較慢（緩解同 ADR-0001 已知問題：換網路 / 強制 IPv4 / 公司 pull-through）。
- ⚠️ CMDB-as-code 是「夠用」的組態管理示範，非取代企業級 CMDB 工具；定位需在文件講清楚。

## 核准與執行

本 ADR 已 **accepted**（2026-06-14，含 cosign 金鑰選型 PoC=key-pair）。依 `PROJECT_PLAN.md` Phase D 逐 TASK 執行；[TASK-D3] OpenLiberty 模組已落實本 ADR 的執行環境決策。

## See Also
- `docs/adr/0001-phase2-iac-stack.md`
- `docs/golden-path-request-to-deploy.md`
- `PROJECT_PLAN.md`（Phase D）
