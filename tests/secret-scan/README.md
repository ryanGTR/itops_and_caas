# 機敏資訊掃描守門員 — 測試說明([TASK-03] 步驟 4)

> 對應治理控制項:ISO 27001 A.8.12 資料外洩防護 / A.5.17 鑑別資訊

本目錄記錄 `policy-secrets`(機敏掃描守門員)的驗證方式與證據,
證明「含機敏資訊的變更會被擋、乾淨的變更會通過」。

## 測試設計

| 案例 | 內容 | 預期 |
|------|------|------|
| **故意違規 PR** | 分支 `test/secret-scan-violation` 內含 `VIOLATION_fixture.txt`(明顯假值私鑰) | 掃描 **failed**,PR 無法合併 |
| **乾淨樹** | `main` 分支(無任何機敏資訊) | 掃描 **passed** |

> 違規夾具刻意只放在 `test/secret-scan-violation` 分支(模擬一個未合併的違規 PR),
> 不進 `main`,以免 main 的閘門被自身夾具長期觸發。

## 在本機重現(無需 GitHub)

```bash
# 1) 安裝與 workflow 相同版本的 gitleaks(v8.18.4)
# 2) 違規分支 — 預期偵測到、結束碼 1
git checkout test/secret-scan-violation
gitleaks detect --source . --no-git --config .gitleaks.toml --redact --exit-code 1 --verbose

# 3) main — 預期乾淨、結束碼 0
git checkout main
gitleaks detect --source . --no-git --config .gitleaks.toml --redact --exit-code 1 --verbose
```

## 已驗證的結果(本機 gitleaks v8.18.4)

```
# 違規分支:
RuleID:      private-key
File:        tests/secret-scan/VIOLATION_fixture.txt
leaks found: 1
→ gitleaks 結束碼: 1   (檢查 failed,PR 應被擋)

# main:
no leaks found
→ gitleaks 結束碼: 0   (檢查 passed,PR 通過)
```

## 稽核軌跡

在 GitHub Actions 上,`policy-secrets` workflow 會把 SARIF 報告以 artifact
(`gitleaks-report`)保留,作為「期間內掃描已執行、結果為何」的可稽核證據,
供 `[TASK-07]` 的稽核報告彙整。
