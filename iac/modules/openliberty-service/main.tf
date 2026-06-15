# openliberty-service — 合規預設的 OpenLiberty(Podman 容器)執行環境(Secure by Default)
#
# 把容器安全基線「焊死」進模組:呼叫者只填業務參數,開不出不合規的容器。
# 這是 secure-bucket(S3)那套「護欄即 IaC」在「執行環境」層的延伸。
#
# 強制的控制 ↔ ISO 27001 控制項:
#   - 非 root 執行                 → A.8.2  特權存取 / 最小權限
#   - 唯讀根檔系統 + 僅必要 tmpfs   → A.8.27 安全系統架構 / 完整性
#   - drop 所有 capabilities        → A.8.2  最小權限
#   - 禁止 privileged                → A.8.27 主機隔離
#   - no-new-privileges             → A.8.2  防止提權
#   - 記憶體上限                     → A.8.6  容量管理 / 可用性
#   - 僅綁 127.0.0.1                 → A.8.20 網路安全(不對外曝險)
#   - 健康檢查                       → A.8.16 監視活動
#   - 強制標籤(owner / 分級)         → A.5.9  資產盤點 / A.5.12 資訊分級

resource "docker_image" "openliberty" {
  name         = var.image
  keep_locally = true
}

resource "docker_container" "this" {
  name     = var.name
  image    = docker_image.openliberty.image_id
  must_run = true
  restart  = "unless-stopped"

  # --- 安全焊死(呼叫者無從關閉)---
  user       = var.run_as_user # 非 root
  read_only  = true            # 唯讀根檔系統
  privileged = false           # 禁特權

  capabilities {
    add  = []
    drop = ["ALL"] # 丟掉所有 Linux capabilities,要用再逐項加
  }

  security_opts = ["no-new-privileges:true"] # 禁止子行程提權

  memory     = var.memory_mb
  cpu_shares = var.cpu_shares

  # 唯讀根檔系統下,僅必要路徑掛 tmpfs(可寫但不落地)
  dynamic "mounts" {
    for_each = toset(var.writable_paths)
    content {
      target = mounts.value
      type   = "tmpfs"
    }
  }

  # 僅綁回環位址,不對外曝險。
  # internal 固定 9080:OpenLiberty 在容器內永遠聽 9080(base image 的 open-default-port);
  # 只有 host 埠(external)隨環境變。早期 internal=var.http_port,sandbox 用 9080 剛好矇對,
  # 但 test/uat/prod 用 9081/9082/... 時容器內沒人聽該埠 → 服務不可達(真 live 才抓到)。
  ports {
    internal = 9080
    external = var.http_port
    ip       = "127.0.0.1"
  }

  healthcheck {
    test         = ["CMD", "curl", "-f", "http://localhost:9080/health"]
    interval     = "30s"
    timeout      = "5s"
    retries      = 3
    start_period = "30s"
  }

  env = [for k, v in var.env : "${k}=${v}"]

  dynamic "labels" {
    for_each = var.labels
    content {
      label = labels.key
      value = labels.value
    }
  }
}
