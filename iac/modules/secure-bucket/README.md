# module: secure-bucket — 合規 S3(Secure by Default)

> 把銀行要求的安全預設「焊死」在模組裡。呼叫者只填業務參數,
> **開不出不合規的 bucket**。這是 Phase 1「護欄」在 IaC 層的延伸。

## 合規契約(這個模組保證了什麼)

| 強制的控制 | 怎麼做 | 對應 ISO 27001 |
|------------|--------|----------------|
| 加密 at rest | SSE 設定(KMS 或 AES256),呼叫者無法關 | A.8.24 加密技術 |
| 封鎖公開存取 | public access block 四項全 true | A.8.12 資料外洩 / A.5.15 存取控制 |
| 版本控制 | versioning 預設 Enabled,無法關 | A.8.13 完整性 / 備份 |
| 強制標籤 | variable validation 強制 owner + data_classification | A.5.9 資產盤點 / A.5.12 分級 |

> 設計原則:安全設定**不開放關閉**——「合規寫進預設值」就是讓不合規無從選擇。

## 用法

```hcl
module "app_bucket" {
  source = "../../modules/secure-bucket"

  name = "my-app-data-bucket"
  tags = {
    owner               = "team-payments"   # 必填
    data_classification = "internal"        # 必填
  }
  # kms_key_arn = "arn:aws:kms:..."         # 選填;留空則用 AES256
}
```

## 輸入

| 變數 | 必填 | 說明 |
|------|------|------|
| `name` | ✅ | bucket 名稱 |
| `tags` | ✅ | 必含 `owner` 與 `data_classification`,否則 plan 直接報錯 |
| `kms_key_arn` | — | 指定則用 KMS 加密;留空用 SSE-S3(AES256)。兩者皆合規 |

## 輸出

| 輸出 | 說明 |
|------|------|
| `bucket_id` | bucket 名稱 / ID |
| `bucket_arn` | bucket ARN |

## 已知豁免(見 iac/.checkov.yaml)

存取日誌、生命週期、事件通知、跨區複寫屬 use-case/成本型,於閘門設定做
「可稽核豁免」並附理由(SoA 精神),非本模組安全核心。
