# secure-bucket 對外只開放「業務需要」的參數;安全設定不開放關閉。
# 這就是「合規寫進預設值」——呼叫者無從選擇不合規。

variable "name" {
  description = "S3 bucket 名稱"
  type        = string
}

variable "tags" {
  description = "資源標籤;強制包含 owner 與 data_classification(可追溯 / 資料分級)"
  type        = map(string)

  # 強制標籤:缺 owner 或 data_classification 直接報錯(ISO 27001 A.5.9 / A.5.12)
  validation {
    condition     = contains(keys(var.tags), "owner") && contains(keys(var.tags), "data_classification")
    error_message = "tags 必須包含 owner 與 data_classification(資產管理與資料分級要求)。"
  }
}

variable "kms_key_arn" {
  description = "選用:指定 KMS 金鑰加密;留空則用 SSE-S3(AES256)。兩者皆為加密,皆合規。"
  type        = string
  default     = null
}
