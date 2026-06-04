# 故意違規測試:開發者「手刻」一個陽春 bucket,繞過合規模組。
# 預期被 checkov 政策閘門擋下(未加密、未封鎖公開、未開版本控制…)。
# 證明:不走合規模組 = 不合規 = 進不了 main。
#
# 此檔僅供測試,不應真的部署。

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_s3_bucket" "bad" {
  bucket = "totally-public-unencrypted-bucket"
}

# 雪上加霜:還手動設成公開讀
resource "aws_s3_bucket_acl" "bad" {
  bucket = aws_s3_bucket.bad.id
  acl    = "public-read"
}
