# itops × iTop(Combodo)整合 — WIP

> 目標:把 itops 的 git 治理記錄推進**真正的 ITSM/CMDB 產品 iTop**(Combodo),
> 讓 iTop 當系統 of record(真 CMDB 拓樸 + 服務台 UI),itops 保留 git 的 fail-closed 護欄。
> 起因:Ryan 一路說的「itop」其實是這個產品;他的 CMDB「硬體→middleware→軟體」心智模型 = iTop 的資料模型。

## 進度(2026-06-16)

- ✅ **iTop 3.2.2 已在本機跑起來並安裝完成**(Docker `vbkunin/itop`,ITIL 模組,101 張表)。
- ⏳ **下一步(到公司接續)**:啟用 REST API → 寫 `scripts/itop_sync.py` 把 itops 記錄推進 iTop。

## 如何重現(在任何機器把 iTop 站起來)

```bash
# 1. 跑容器(含 MySQL/MariaDB)
podman run -d -p 8000:80 --name itop docker.io/vbkunin/itop:latest

# 2. 無人值守安裝(param 範本在本目錄;先把 __SET_YOUR_ADMIN_PWD__ 換成你的密碼)
podman cp integration/itop/itop-install.xml itop:/tmp/itop-install.xml
podman exec itop sh -c 'rm -f /var/www/html/data/.maintenance; \
  cd /var/www/html/setup/unattended-install && \
  php unattended-install.php --param-file=/tmp/itop-install.xml'
# 完成後 → http://localhost:8000  (admin / 你設的密碼)
```

## 安裝踩過的雷(都已解,記給接續者)

1. **`datamodel_version` 必須對上 iTop 版本**:此映像是 iTop **3.2.2**,datamodel_version 要填 **3.2.1**(看 `datamodels/2.x/version.xml`);填 2.7.0 會編譯失敗。
2. **`selected_modules` 不能只列 extensions**:要含 base 模組(`itop-profiles-itil` 定義 user_rights/groups、`itop-welcome-itil`、`authent-local`、`itop-config`、`itop-structure`、`itop-attachments`),否則 compile 報 `Missing unique tag: groups in /itop_design/user_rights`。
3. **失敗重跑前要清乾淨**:`rm /var/www/html/data/.maintenance` + `DROP DATABASE itop_db; CREATE DATABASE itop_db;`,否則卡在維護模式、install 腳本不輸出。
4. **param XML 的 `type="array"` 標記要保留**(options/selected_modules/selected_extensions),否則空值被當 string → `in_array()` TypeError;`<database>` 要含 `db_tls_enabled`/`db_tls_ca`。

## 下一步:啟用 REST + 寫 sync(到公司做)

1. **啟用 REST API**:給一個 user「**REST Services User**」profile;`conf/production/config-itop.php` 加 `allowed_rest_profiles`(含該 profile)。測試:
   ```bash
   curl -s "http://localhost:8000/webservices/rest.php?version=1.3" \
     --data-urlencode auth_user=admin --data-urlencode auth_pwd=<pwd> \
     --data-urlencode 'json_data={"operation":"list_operations"}'
   ```
2. **寫 `scripts/itop_sync.py`**:讀 itops 的記錄,經 REST `core/create`/`core/update` 推進 iTop。對映:

   | itops 記錄 | iTop class | 關係 |
   |-----------|-----------|------|
   | host CI(VM/宿主) | `Server` / `VirtualMachine` | — |
   | middleware CI(OpenLiberty) | `Middleware`(或 `OtherSoftware`) | runs on Server |
   | software CI(app) | `WebApplication` / `ApplicationSolution` | depends on Middleware |
   | 服務請求 issue(如 #34) | `UserRequest`(工單) | refers to CI |
   | 部署/過版 | `Change`(`NormalChange`/`RoutineChange`) | impacts CI |

   證據鏈:itops 的 `serviceRequest`→iTop ticket ref;digest/簽章→CI 屬性或 attachment。
3. **觸發點**:`itops_ingest.sh` / `deploy_openliberty*.sh` 部署成功後呼叫 `itop_sync.py`(像 cmdb_register 那樣,但目標是真 iTop)。

## 設計要點

- iTop = 真 CMDB/ITSM 系統 of record;itops = git 護欄 + 政策即程式碼。**互補不互斥**:不合規的東西在 itops 的閘門就被擋(根本不會 sync 進 iTop);合規的才登錄到 iTop 當正式組態。
- 這把 itops 的 `cmdb-as-code`(YAML)從「自幹的薄片」升級成「餵真 ITSM 工具」。
