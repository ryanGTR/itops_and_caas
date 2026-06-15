# openliberty-service 對外只開「業務需要」的參數;安全設定焊死、不可關閉(Secure by Default)。
# 呼叫者無從選擇不合規——這是 secure-bucket 那套「護欄即 IaC」在執行環境層的延伸。

variable "name" {
  description = "服務 / 容器名稱"
  type        = string
}

variable "image" {
  description = "OpenLiberty 應用映像(OpenLiberty base + 應用層);應為經簽章驗證的 image"
  type        = string
}

variable "http_port" {
  description = "OpenLiberty HTTP 埠(僅綁 127.0.0.1,不對外曝險)"
  type        = number
  default     = 9080
}

variable "labels" {
  description = "容器標籤;強制含 owner 與 data_classification(資產盤點 / 資料分級)"
  type        = map(string)

  # 強制標籤:缺 owner 或 data_classification 直接報錯(ISO 27001 A.5.9 / A.5.12)
  validation {
    condition     = contains(keys(var.labels), "owner") && contains(keys(var.labels), "data_classification")
    error_message = "labels 必須包含 owner 與 data_classification(資產管理與資料分級要求)。"
  }
}

variable "memory_mb" {
  description = "記憶體上限(MB);避免單一容器吃垮主機(可用性 / 容量管理)"
  type        = number
  default     = 512
}

variable "cpu_shares" {
  description = "CPU 權重"
  type        = number
  default     = 512
}

variable "run_as_user" {
  description = "以非 root 使用者執行(UID);預設 1001(OpenLiberty 映像的非 root 使用者)"
  type        = string
  default     = "1001"
}

variable "writable_paths" {
  description = "唯讀根檔系統下仍需可寫的路徑(掛 tmpfs,可寫但不落地);預設為 OpenLiberty 執行所需"
  type        = list(string)
  default = [
    "/tmp",
    "/opt/ol/wlp/output",
    "/opt/ol/wlp/usr/servers/defaultServer/workarea",
    "/logs",
    # OpenLiberty 官方映像啟動時會把預設 keystore.xml 寫進 configDropins/defaults
    # (importKeyCert)。唯讀根檔系統下這會失敗導致容器 exit;掛 tmpfs 讓它可寫但不落地,
    # 既保住「根檔系統唯讀」基線,又讓映像能正常啟動。
    "/config/configDropins/defaults",
  ]
}

variable "env" {
  description = "非機密環境變數(K=V map);機密請走 secrets 機制,勿放這裡"
  type        = map(string)
  default     = {}
}
