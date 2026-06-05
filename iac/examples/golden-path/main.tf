# 黃金路徑:開發者只需這幾行,就得到一個「必然合規」的 bucket。
# 不必懂加密、公開存取、版本控制怎麼設——模組已替你焊死合規預設。

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

module "app_bucket" {
  source = "../../modules/secure-bucket"

  name = "my-app-data-bucket"
  tags = {
    owner               = "team-payments"
    data_classification = "internal"
  }
}
