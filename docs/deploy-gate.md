---
title: 部署前驗章閘門（Deploy Gate, fail-closed）
type: howto
created: 2026-06-15
updated: 2026-06-15
tags: [deploy-gate, cosign, verify, fail-closed, iso27001, itil]
---

# 部署前驗章閘門（fail-closed）

> 對應 `PROJECT_PLAN.md` [TASK-D5]。這是黃金路徑的最後一道閘門:**任一檢查不過,就拒絕部署**。
> 體現「不合規的產物根本部署不上去」——位置在 [TASK-D4] 簽章之後、[TASK-D6] 部署之前。

## 三道強制檢查(全部 fail-closed)

| # | 檢查 | 不過代表 | 控制項 |
|---|---|---|---|
| 1 | `spec.source.digest` 是有效 `sha256:...` | 未經建置/簽章,沒有不可變指紋 | ISO 27001 A.8.28 完整性 |
| 2 | cosign 用信任根 `trust/cosign.pub` 驗章通過 | 未簽 / 簽章無效 / 非本平台所簽 | ISO 27001 A.8.28 供應鏈 |
| 3 | DeploymentRequest 必要欄位齊全(app/environment/requestedBy) | 未登錄組態 | ISO 20000 組態管理 |

任一失敗 → `verify_deploy_gate.py` 以 **exit 1** 拒絕並印出是哪個控制項擋的。

## 用法

```bash
python3 scripts/verify_deploy_gate.py \
  --request deployments/openliberty-sandbox/supply-chain-backend.yaml \
  --signature <對 digest 的簽章> \
  --pubkey trust/cosign.pub
```

## 已驗證(self-test,真 cosign 加密)

`scripts/tests/deploy-gate/selftest.sh`(只用公鑰 + 已簽 fixture,不需私鑰):

| 情境 | 期望 | 結果 |
|---|---|---|
| 合規 + 有效簽章 | 放行(exit 0) | ✅ |
| 未綁 digest(未建置/簽章) | 拒絕(exit 1) | ✅ |
| 未提供簽章 | 拒絕(exit 1) | ✅ |
| 簽章不符(偽造/竄改) | 拒絕(exit 1) | ✅ |

> 由 `.github/workflows/policy-deploy-gate.yml` 在 CI 重跑這個 self-test。
> 簽章驗證用 **key-pair + `--insecure-ignore-tlog`**(離線自足,符合銀行氣隙;Rekor 透明日誌是 keyless 才需要)。

## key-pair vs 正式環境

- PoC:對 digest 做 `cosign verify-blob`(本機可測、不需 registry)。
- 正式部署([TASK-D6]):對實際映像做 `cosign verify --key trust/cosign.pub <image>@<digest>`。
- 金鑰:PoC=key-pair;正式=KMS/HSM(見 `docs/adr/0002`)。

## See Also
- `scripts/verify_deploy_gate.py`（閘門實作）
- `docs/supply-chain-signing.md`（上游:簽章）
- `trust/README.md`（信任根）
- `docs/golden-path-request-to-deploy.md`（全貌,階段⑤）
