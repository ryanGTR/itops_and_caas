# iac/ — Phase 2:基礎設施即程式碼(IaC)合規護欄

> 把 Phase 1 的「護欄即程式碼」延伸到基礎設施層:開發者開出來的雲端資源
> **預設就合規**,想開不合規的都開不出來。
>
> 技術棧:OpenTofu + LocalStack(本機模擬 AWS)+ Podman + checkov。
> 決策緣由見 [`docs/adr/0001-phase2-iac-stack.md`](../docs/adr/0001-phase2-iac-stack.md)。

## 結構

```
iac/
├── modules/secure-bucket/     合規 S3 模組(安全預設焊死)
├── examples/golden-path/      黃金路徑:開發者怎麼用模組
├── examples/localstack-smoke/ 對 LocalStack apply 的 smoke test
├── tests/violation/           故意違規(證明閘門擋得住)
└── .checkov.yaml              IaC 政策閘門設定(合規基線 + 可稽核豁免)
```

## 合規基線與「可稽核豁免」(SoA 精神)

`.checkov.yaml` 明確宣告:

- **必過核心**(不豁免):加密 at rest、封鎖公開存取、版本控制、強制標籤
- **可稽核豁免**(`skip-check`,各附理由):跨區複寫、生命週期、事件通知、
  存取日誌 —— 屬 use-case / 成本考量,非安全核心。類比 ISO 27001 SoA。

| 控制 | checkov | 對應 ISO |
|------|---------|----------|
| 加密 at rest | CKV_AWS_19/145 等 | A.8.24 加密 |
| 封鎖公開存取 | CKV2_AWS_6 / CKV_AWS_20 | A.8.12 / A.5.15 |
| 版本控制 | CKV_AWS_21 | A.8.13 完整性 |
| 強制標籤 | 模組 variable validation | A.5.9 / A.5.12 資產/分級 |

## 怎麼跑(本機驗證,零雲端)

```bash
# 主閘門:掃 iac/(排除 tests/),應 Passed/Failed=0
checkov -d iac --config-file iac/.checkov.yaml --compact

# 違規 self-test:應有 FAILED(證明擋得住)
checkov -d iac/tests/violation --compact
```

已驗結果:主閘門 **Passed 12 / Failed 0**;違規 self-test **Failed 8**(被擋)。

## LocalStack smoke test(選配)

需先把 LocalStack 起來(見 `scripts/localstack-up.sh`),再:

```bash
cd iac/examples/localstack-smoke
tofu init && tofu apply -auto-approve
aws --endpoint-url=http://localhost:4566 s3 ls
```

> 注意:LocalStack 大映像在某些網路下拉取會逾時(IPv6↔Docker CDN),
> 屬已知問題,見 ADR-0001。合規價值不依賴它。
