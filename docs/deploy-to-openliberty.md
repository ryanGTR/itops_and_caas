---
title: 部署到 OpenLiberty + 煙霧測試（Deploy & Smoke Test）
type: howto
created: 2026-06-15
updated: 2026-06-15
tags: [deploy, openliberty, opentofu, podman, smoke-test, iso20000, release-management, golden-path]
---

# 部署到 OpenLiberty + 煙霧測試

> 對應 `PROJECT_PLAN.md` [TASK-D6]，黃金路徑**階段⑥**：把『**已驗章的 artifact**』部署到
> [TASK-D3] 的 OpenLiberty runtime，並用煙霧測試證明「可服務」。
> 位置在 [TASK-D5] 驗章閘門**之後**、[TASK-D7] 登錄 CMDB **之前**。

## 一句話

> 驗章閘門放行 → OpenTofu 用「預設安全模組」開出容器並部署映像 → 煙霧測試打 `/health` 與業務端點 → 全綠才算發布成功，全程留痕。

## 不可繞過的尾段鏈（`scripts/deploy_openliberty.sh`）

```
[1] D5 驗章閘門(fail-closed) ──不過就 exit,根本不部署──┐
[2] tofu apply(D3 預設安全容器:非 root/唯讀根檔/drop caps/僅綁 127.0.0.1)
[3] 完整性閉環:跑起來的容器 image ID  ==  D5 驗過的 digest   ← 防「驗 A 部署 B」偷渡
[4] 煙霧測試:GET /health → 200  且  GET /api/products → 200
[5] 留痕:deployments/openliberty-sandbox/last-deploy.json(供 D7 取用)
```

`image` 一律由 harness 從 **DeploymentRequest 注入**（單一真相來源），環境配置本身不寫死映像——確保「**只部署驗過的東西**」。

## 用法

```bash
scripts/deploy_openliberty.sh \
  --request   deployments/openliberty-sandbox/supply-chain-backend.yaml \
  --signature deployments/openliberty-sandbox/sig/supply-chain-backend.sig
```

前置（黃金路徑上游已備齊）：本機 podman socket 已起、`localhost/supply-chain-backend:<ver>`
映像已 build、DeploymentRequest 的 `spec.source.digest` 已回填、對該 digest 的 blob 簽章已產。

## 已驗證（本機實跑，真容器）

| 檢查 | 期望 | 結果 |
|---|---|---|
| D5 驗章閘門 | 放行(exit 0) | ✅ |
| 容器安全姿態 | User=1001 / ReadOnly=true / Privileged=false / drop ALL caps / 僅綁 127.0.0.1 | ✅ |
| 完整性閉環 | 部署的 image ID == 驗過的 digest | ✅ |
| 煙霧測試 `/health`（mpHealth） | 200 | ✅ |
| 煙霧測試 `/api/products`（業務） | 200 + 回真實 JSON | ✅ |
| 部署證據 | `last-deploy.json` result=success | ✅ |

## 踩過的坑：唯讀根檔系統 vs OpenLiberty keystore

OpenLiberty 官方映像啟動時會無條件把預設 `keystore.xml` 寫進
`/config/configDropins/defaults/`（`docker-server.sh` 的 `importKeyCert`）。模組的
**唯讀根檔系統**基線會讓這個寫入失敗、容器 `exit(1)`。

**解法**：在 `openliberty-service` 模組的 `writable_paths` 預設加入
`/config/configDropins/defaults`，掛 **tmpfs**（可寫但不落地）。既保住「根檔系統唯讀」
這條 ISO 27001 A.8.27 基線，又讓官方映像能正常啟動——是 OpenLiberty 跑在唯讀根檔上的標準模式。

## 對應治理控制項

| 步驟 | 控制項 |
|---|---|
| 部署發布 | ISO 20000 發布與部署管理 |
| 完整性閉環（部署 == 驗章物） | ISO 27001 A.8.28 完整性 |
| 部署後煙霧測試 | ITIL 發布驗證 / 部署後驗證 |
| 預設安全容器 | ISO 27001 A.8.27 Secure by Default |

## 正式環境差異（PoC vs 銀行）

- **映像參照**：PoC 用本機 tag + image-ID 當不可變 digest；正式應用 registry digest（`<image>@sha256:...`）並 `cosign verify --key ... <image>@<digest>`。
- **部署目標**：PoC 是單一 Podman 容器；正式可換 k8s/OpenShift（屬後續 Phase，本路徑不依賴）。
- **狀態管理**：PoC 用本機 tfstate（gitignore）；正式應用遠端 state + 鎖。

## See Also
- `scripts/deploy_openliberty.sh`（部署 harness 實作）
- `iac/environments/openliberty-sandbox/main.tf`（環境即程式碼）
- `iac/modules/openliberty-service/`（預設安全容器模組）
- `docs/deploy-gate.md`（上游：D5 驗章閘門）
- `deployments/README.md`（DeploymentRequest 即程式碼）
- `docs/golden-path-request-to-deploy.md`（全貌，階段⑥）
