# itops × iTop(Combodo)整合

> 把 itops 的 git 版控 CMDB(`cmdb/<env>/*.yaml`)推進**真正的 ITSM/CMDB 產品 iTop**(Combodo),
> 讓 iTop 當系統 of record(真 CMDB 拓樸 + 服務台 / 變更 UI),itops 保留 git 的 fail-closed 護欄。
> 起因:Ryan 一路說的「itop」其實是這個產品;他的「硬體→middleware→軟體」CMDB 心智模型 = iTop 的資料模型。

## 狀態:✅ 已打通(2026-06-16)

- ✅ iTop 3.2.2 本機站起 + **完整 ITIL 資料模型**(220 表;Server/WebServer/WebApplication/UserRequest/Change 齊全)。
- ✅ REST API 啟用 + **least-privilege 服務帳號** `svc_itops_sync`(只給 REST/組態/變更/服務台 profile,非 admin)。
- ✅ `scripts/itop_sync.py`:讀 `cmdb/<env>/*.yaml` → upsert 進 iTop(冪等)。已對五個環境 15 CI 跑通。
- ✅ 觸發點:`integration/itops_ingest.sh` 部署成功後(opt-in `ITOP_SYNC=1`)自動呼叫 sync。

## 一鍵重現(把整套 iTop 站起來)

```bash
bash integration/itop/setup-itop.sh        # 容器→安裝→修權限→啟 REST→建服務帳號
source .itop-secrets                        # 載入產生的密碼(此檔已被 .gitignore)
python3 scripts/itop_sync.py --env vm-openliberty --org Demo
# → http://localhost:8000  (admin / 見 .itop-secrets)
```

`setup-itop.sh` 把以下手動步驟固化成冪等腳本:跑 `vbkunin/itop` 容器 → 無人值守安裝
(`itop-install.xml`)→ 修權限/DB 帳號 → 給 admin「REST Services User」profile → 建服務帳號。
機敏密碼一律走環境變數(未設則自動產生),寫到 `.itop-secrets`,不進版控。

## CI / 工單對映(已用真 API 驗證)

選 `WebServer` 串 OpenLiberty,是為了得到 iTop **原生的影響分析圖** `app → web server → host`
(用真 FK `webserver_id` / `system_id`,而非鬆散的清單)。

| itops CI(`cmdb/<env>/`)         | iTop class       | 關係(FK)                         |
|----------------------------------|------------------|------------------------------------|
| host(libvirt VM / 容器宿主)     | `Server`         | —(見下方「為何不是 VirtualMachine」)|
| middleware(OpenLiberty)         | `WebServer`      | `system_id` → host                 |
| software(已部署 app)           | `WebApplication` | `webserver_id` → middleware        |
| `provenance.serviceRequest`(#34)| `UserRequest`    | `functionalcis_list` → app         |
| 一次部署 / 過版                  | `RoutineChange`  | `functionalcis_list` → app         |

互補不互斥:不合規的東西在 itops 閘門就被擋(根本不會 sync 進 iTop);合規且部署成功的才登錄成正式組態。
**過版用 `RoutineChange`(例行變更)** 呼應「護欄預先授權」——不是每次都走重量級審核。

## 安裝踩過的雷(都已解,記給接續者)

1. **模組清單要填「真實模組名」,不是 `installation.xml` 的 `extension_code`**。
   早期版本把 `itop-config-mgmt-datacenter`、`itop-service-mgmt-enterprise`… 放進 `<selected_extensions>`,
   那些是 installation.xml 的 choice code,**不是模組目錄名**,unattended 安裝會靜默忽略 →
   只編出最小模型(只有 `Person`),`Server`/`UserRequest`/`Change` 全缺。
   ✅ 已改:`<selected_modules>` 直接列真實模組(`itop-datacenter-mgmt`、`itop-request-mgmt-itil`、
   `itop-change-mgmt-itil`…)。**驗收別只看「101 表 / installed」,要實際查類別存不存在**。
2. **`datamodel_version` 要對上版本**:此映像是 iTop **3.2.2**,填 **3.2.1**(看 `datamodels/2.x/version.xml`)。
3. **install 用 root CLI 跑 → 檔案/連線對不上 www-data**:
   - `config-itop.php` 與 `data/`、`log/` 被建成 `root:root` → apache(www-data)讀不到 →
     REST 報 `Could not find configuration file`。修:`chown -R www-data:www-data conf data log env-production`。
   - MariaDB `root` 只能 unix_socket 登入(限 OS root)→ www-data 連 DB 被拒(errno 1698)。
     修:建專用 DB 帳號 `itop`(帶密碼),改 `config-itop.php` 的 `db_user`/`db_pwd`。
4. **REST 閘門是 `secure_rest_services` + 硬編碼 `HasProfile('REST Services User')`**(見 `webservices/rest.php`)。
   舊筆記說的 `allowed_rest_profiles` 對 3.2.x **無效**。正解:給要用 REST 的帳號「REST Services User」profile。
5. **失敗重跑要清乾淨**:`rm data/.maintenance` + `DROP DATABASE itop_db; CREATE DATABASE …`,否則卡維護模式。
6. **runit 容器別用 `apachectl -k graceful`**:它會另起一隻 rogue apache。要讓設定生效就 `podman restart`(由 runit 重起)。

## 安全/治理註記

- `svc_itops_sync` 是 least-privilege 服務帳號:有建立/更新 CI 與工單的權,但**無刪除權**(刪除留給 admin)。
  這呼應 SoD——同步機器人只會「登錄」,不會「抹除」紀錄。
- 本機開發密碼走 `.itop-secrets`(gitignore);正式環境應接 Vault / secret manager,別落地明文。
- 對應治理控制項:ISO 20000 組態/變更管理;ISO 27001 A.8.9 組態管理、A.5.23 雲端服務使用。

## 後續可深化(非阻塞)

- 把同步狀態回寫進治理後台 console(哪些 CI 已進 iTop)。
- 服務請求/變更單帶 caller/team/CAB 欄位,模擬真正的服務台/CAB 流程。
- 用 iTop 的 Synchro Data Source(資料同步來源)取代直接 REST upsert,得到自動 reconcile/孤兒清理。
