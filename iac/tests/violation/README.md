# 故意違規測試 — 證明 IaC 政策閘門擋得住

> 對應治理:ISO 27001 A.8.27 Secure by Default / A.5.36 合規審查

`main.tf` 是開發者「手刻、繞過合規模組」的陽春 bucket(未加密、未封鎖公開、
未開版本控制,還手動設成 public-read)。預期被 checkov 擋下。

## 為什麼放在 tests/(被主閘門排除)

比照 Phase 1 機敏掃描:違規夾具本來就該失敗,故在 `iac/.checkov.yaml` 用
`skip-path: iac/tests/` 排除於「主閘門」之外,避免主閘門被自身夾具長期觸發;
另以本 self-test 證明它確實會被擋。

## 重現

```bash
# 主閘門(不含本夾具)→ 應乾淨
checkov -d iac --config-file iac/.checkov.yaml --compact

# 對違規夾具單獨掃 → 應 FAILED(被擋)
checkov -d iac/tests/violation --compact
```

## 已驗結果(checkov 3.2.533)

```
主閘門 iac/         → Passed 12 / Failed 0   (exit 0,通過)
違規 tests/violation → Passed 6  / Failed 8   (exit 1,被擋)
```

擋下的核心項目包含:未封鎖公開存取(CKV2_AWS_6)、未加密(CKV_AWS_145)、
未開版本控制(CKV_AWS_21)、公開讀 ACL(CKV_AWS_20)等。

> 結論:不走合規模組 = 不合規 = 進不了 main。護欄即程式碼,在 IaC 層同樣成立。
