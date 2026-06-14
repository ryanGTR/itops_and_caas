# 故意違規夾具 — 證明容器護欄(policies/rules/openliberty_*)會擋下不安全容器。
# 不納入主閘門(.checkov.yaml 已 skip-path iac/tests/);由 self-test 直接掃此檔證明會 FAIL。
# 比照 Phase 1 機敏掃描、Phase 2 secure-bucket 的違規分支做法。

terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = ">= 3.0"
    }
  }
}

# 多項違規:privileged、root、唯讀關閉、無記憶體上限、未 drop capabilities、
# 無 no-new-privileges、綁 0.0.0.0(對外曝險)
resource "docker_container" "insecure" {
  name       = "insecure-openliberty"
  image      = "open-liberty:latest"
  privileged = true
  read_only  = false
  user       = "root"

  ports {
    internal = 9080
    external = 9080
    ip       = "0.0.0.0"
  }
}
