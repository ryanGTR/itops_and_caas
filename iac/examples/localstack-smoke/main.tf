# LocalStack smoke test:用合規模組在「本機模擬的 AWS」開一個 bucket。
# 證明同一份合規 HCL 真的 apply 得出來(P2-1 / P2-3 的活體驗證)。
#
# 先啟動 LocalStack:bash scripts/localstack-up.sh
# 再:tofu init && tofu apply -auto-approve

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

# provider 指向 LocalStack(localhost:4566)。
# access_key/secret_key 為 LocalStack 慣用假值,LocalStack 不驗證憑證——
# 非真實機敏資訊(checkov: skip CKV_AWS_41 不適用此本機端點設定)。
provider "aws" {
  # checkov:skip=CKV_AWS_41:LocalStack 本機端點假憑證,非真實機敏(可稽核豁免)
  region                      = "us-east-1"
  access_key                  = "test" # LocalStack dummy
  secret_key                  = "test" # LocalStack dummy
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true

  endpoints {
    s3  = "http://127.0.0.1:4566"
    sts = "http://127.0.0.1:4566"
    iam = "http://127.0.0.1:4566"
    kms = "http://127.0.0.1:4566"
  }
}

module "smoke_bucket" {
  source = "../../modules/secure-bucket"

  name = "smoke-test-bucket"
  tags = {
    owner               = "platform-team"
    data_classification = "test"
  }
}

output "bucket_id" {
  value = module.smoke_bucket.bucket_id
}
