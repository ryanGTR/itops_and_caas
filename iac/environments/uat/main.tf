# 環境即程式碼:uat — TASK-F1(多環境骨架)
#
# build once, promote the same digest:image 由部署 harness 以 -var 注入(來源=已驗章 digest),
# 三區共用同一個 image;**差異只在本檔的 config**(埠 / 記憶體 / 環境變數 / 分級標籤)。
# 安全基線焊死在 modules/openliberty-service(非 root / 唯讀根檔 / drop caps / 僅綁 127.0.0.1)。

terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = ">= 3.0"
    }
  }
}

variable "podman_socket" {
  type    = string
  default = "unix:///run/user/1000/podman/podman.sock"
}

variable "image" {
  description = "已驗章的應用映像(由 deploy harness 注入;三區相同 digest)"
  type        = string
}

provider "docker" {
  host = var.podman_socket
}

module "backend" {
  source    = "../../modules/openliberty-service"
  name      = "supply-chain-backend-uat"   # 容器名含環境,三區可並存不衝突
  image     = var.image
  http_port = 9082
  memory_mb = 512

  env = {
    LOG_LEVEL = "INFO"   # 隨環境的非機密設定(機密走 secrets 機制,勿放這裡)
  }

  labels = {
    owner               = "platform-team"
    data_classification = "internal"
    environment         = "uat"
  }
}

output "backend_url" {
  value = module.backend.url
}

output "container_name" {
  value = module.backend.container_name
}
