# 環境即程式碼:openliberty-sandbox(PoC 唯一環境)— TASK-D6
#
# 這是「真實部署的期望狀態」,不是範例(範例見 iac/examples/openliberty-golden-path)。
# 由 scripts/deploy_openliberty.sh 在「D5 驗章閘門放行後」才 apply,
# 把『已驗章的映像』部署成一個預設安全的 OpenLiberty 容器。
#
# image 一律由部署 harness 以 -var 注入(來源:DeploymentRequest 的 artifact:version,
# 且其 digest 已過 D5 閘門)——環境配置本身不寫死映像,確保「只部署驗過的東西」。
#
# 安全基線焊死在 modules/openliberty-service(非 root / 唯讀根檔 / drop caps / 僅綁 127.0.0.1…),
# 此處只填業務參數(ISO 27001 Secure by Default)。

terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = ">= 3.0"
    }
  }
}

variable "podman_socket" {
  description = "rootless podman 的 Docker 相容 socket(部署 harness 以 `id -u` 帶入)"
  type        = string
  default     = "unix:///run/user/1000/podman/podman.sock"
}

variable "image" {
  description = "已驗章的應用映像(由 deploy harness 注入;對應 DeploymentRequest 的 artifact:version)"
  type        = string
}

variable "name" {
  description = "服務 / 容器名稱"
  type        = string
  default     = "supply-chain-backend"
}

variable "http_port" {
  description = "OpenLiberty HTTP 埠"
  type        = number
  default     = 9080
}

provider "docker" {
  host = var.podman_socket
}

module "backend" {
  source    = "../../modules/openliberty-service"
  name      = var.name
  image     = var.image
  http_port = var.http_port

  # 強制標籤(資產盤點 / 資料分級);模組會驗證缺一不可
  labels = {
    owner               = "platform-team"
    data_classification = "internal"
  }
}

output "backend_url" {
  description = "服務本機存取位址(僅綁 127.0.0.1)"
  value       = module.backend.url
}

output "container_name" {
  value = module.backend.container_name
}
