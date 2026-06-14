# 模組:openliberty-service(合規預設的 OpenLiberty 執行環境)

> 「填參數即開出一個**預設安全**的 OpenLiberty(Podman 容器)」。
> 安全基線焊死在模組裡,呼叫者只填業務參數,**開不出不合規的容器**。
> 這是 `secure-bucket`(S3)那套「護欄即 IaC」在「執行環境」層的延伸。

## 用法

```hcl
module "backend" {
  source    = "../../modules/openliberty-service"
  name      = "supply-chain-backend"
  image     = "icr.io/appcafe/open-liberty:full-java17-openj9-ubi"  # 走 D4 簽章驗證後的 image
  http_port = 9080
  labels = {
    owner               = "platform-team"
    data_classification = "internal"   # 強制標籤,缺則報錯
  }
}
```

完整可跑範例見 `iac/examples/openliberty-golden-path/`。

## 焊死的安全基線 ↔ ISO 27001 控制項

| 焊死設定 | 控制項 |
|---|---|
| 非 root 執行(`user`) | A.8.2 最小權限 |
| 唯讀根檔系統(`read_only=true`)+ 僅必要 tmpfs | A.8.27 安全架構 / 完整性 |
| drop 所有 capabilities | A.8.2 最小權限 |
| 禁 `privileged` | A.8.27 主機隔離 |
| `no-new-privileges` | A.8.2 防提權 |
| 記憶體上限(`memory`) | A.8.6 容量管理 / 可用性 |
| 僅綁 `127.0.0.1` | A.8.20 網路安全 |
| 健康檢查 | A.8.16 監視活動 |
| 強制標籤(owner / data_classification) | A.5.9 資產盤點 / A.5.12 分級 |

> 這些設定**不開放呼叫者關閉**;對應的 checkov 自訂政策(`policies/rules/openliberty_*`,
> CKV_OL_1~6)在 CI 再驗一次——模組焊死 + 護欄複查,雙保險。

## 輸入參數

| 參數 | 必填 | 預設 | 說明 |
|---|---|---|---|
| `name` | ✅ | — | 服務 / 容器名稱 |
| `image` | ✅ | — | OpenLiberty 應用映像(應為簽章驗證後的 image) |
| `labels` | ✅ | — | 須含 `owner` 與 `data_classification` |
| `http_port` | | 9080 | HTTP 埠(僅綁 127.0.0.1) |
| `memory_mb` | | 512 | 記憶體上限(MB) |
| `cpu_shares` | | 512 | CPU 權重 |
| `run_as_user` | | "1001" | 非 root UID |
| `writable_paths` | | OpenLiberty 所需 | 唯讀根下掛 tmpfs 的可寫路徑 |
| `env` | | {} | 非機密環境變數;機密走 secrets,勿放這裡 |

## Provider:為什麼用 docker provider 接 Podman

目前無成熟的官方 OpenTofu **Podman** provider。rootless Podman 會暴露一個 **Docker 相容
socket**,所以用 `kreuzwerker/docker` provider 指向它即可(見 `docs/adr/0002`)。範例中:

```hcl
provider "docker" {
  host = "unix:///run/user/<你的 uid>/podman/podman.sock"   # 用 `id -u` 取得 uid
}
```

## 驗證狀態(誠實標註)

- ✅ `tofu validate`:HCL + provider schema 通過。
- ✅ checkov 主閘門:模組 CKV_OL_1~6 全 PASS;違規 self-test 全 FAIL(護欄雙向有效)。
- ⏳ `tofu apply` 實跑(拉 OpenLiberty 映像、起容器、煙霧測試):**留到 [TASK-D6]**。
  實跑時若唯讀根 + tmpfs 路徑需微調(OpenLiberty 可寫目錄),以 `writable_paths` 調整。
