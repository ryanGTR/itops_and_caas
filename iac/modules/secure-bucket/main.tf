# secure-bucket — 合規預設的 S3 模組(Secure by Default)
#
# 把銀行要求的安全預設「焊死」在模組裡:呼叫者只填業務參數,
# 開不出不合規的 bucket。這是 Phase 1「護欄」概念在 IaC 層的延伸。
#
# 強制的控制 ↔ ISO 27001 控制項:
#   - 加密 at rest            → A.8.24 加密技術使用 / Secure by Default
#   - 全面封鎖公開存取         → A.8.12 資料外洩防護 / A.5.15 存取控制
#   - 版本控制(防誤刪/竄改)   → A.8.13 資訊備份 / 完整性
#   - 強制標籤(擁有者/分級)    → A.5.9 資產盤點 / A.5.12 資訊分級

resource "aws_s3_bucket" "this" {
  bucket = var.name
  tags   = var.tags
}

# 版本控制:預設啟用,呼叫者無法關閉
resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  versioning_configuration {
    status = "Enabled"
  }
}

# 加密 at rest:給了 KMS 用 KMS,否則 SSE-S3(AES256);兩者皆合規
resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  bucket = aws_s3_bucket.this.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = var.kms_key_arn == null ? "AES256" : "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = true
  }
}

# 封鎖一切公開存取:四項全部 true
resource "aws_s3_bucket_public_access_block" "this" {
  bucket                  = aws_s3_bucket.this.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
