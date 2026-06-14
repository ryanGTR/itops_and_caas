# 黃金路徑範例:用合規預設開出一個 OpenLiberty 服務
# 呼叫者只填業務參數(name/image/port/labels),安全由模組焊死。

terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = ">= 3.0"
    }
  }
}

variable "podman_socket" {
  description = "rootless podman 的 Docker 相容 socket(用 `id -u` 取代下方 1000)"
  type        = string
  default     = "unix:///run/user/1000/podman/podman.sock"
}

provider "docker" {
  host = var.podman_socket
}

module "backend" {
  source    = "../../modules/openliberty-service"
  name      = "supply-chain-backend"
  image     = "icr.io/appcafe/open-liberty:full-java17-openj9-ubi" # 範例假值;實際走 D4 簽章驗證後的 image
  http_port = 9080

  labels = {
    owner               = "platform-team"
    data_classification = "internal"
  }
}

output "backend_url" {
  value = module.backend.url
}
