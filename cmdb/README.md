# cmdb/ — 組態管理資料庫即程式碼（CMDB-as-code）

> 這個目錄是平台的**組態基線**。每個檔案 = 一個 **Configuration Item（CI）**:
> 一個應用在某環境的**已部署實例**,連同它的來源、簽章、實例位置與組態關係。
> 版控史(commit / PR diff)就是天然的**組態基線與變更史**——這正是 ISO 20000
> 組態管理 / ISO 27001 A.8.9 要的東西,而且不必另外架一套 CMDB 工具。

## 為什麼用「版控的 YAML」當 CMDB

| | 傳統 CMDB 工具 | 本專案(CMDB-as-code） |
|---|---|---|
| 變更史 | 工具內稽核日誌 | Git commit / PR(誰改/何時/為何/誰核准) |
| 基線 | 需手動快照 | 任一 commit 即一個基線 |
| 與真相一致 | 靠人工/掃描對帳 | `cmdb_validate.py` 在每個 PR 強制驗一致性 |
| 漂移偵測 | 事後 | CI 閘門事前擋(fail-closed) |

> Java 類比:像把「執行環境的真相」從某個 runtime DB 搬進版控的 `*.yaml`,
> 再用一支驗證器當編譯期檢查——CMDB 與實際部署對不上就「編不過」(PR 被擋)。

## 怎麼產生 / 維護

CI **不手寫**,由部署流程產出,確保 CMDB 反映真實部署:

```bash
# 部署成功後(TASK-D6 產出 last-deploy.json),登錄 / 更新 CI:
python3 scripts/cmdb_register.py \
  --request deployments/openliberty-sandbox/supply-chain-backend.yaml

# 驗證組態基線(CI 閘門 policy-cmdb.yml 會在每個 PR 重跑):
python3 scripts/cmdb_validate.py
```

## CI 結構（schema 草案）

```yaml
apiVersion: cmdb/v1
kind: ConfigurationItem
metadata:   { ciId, type, app, environment }
spec:
  source:        { artifact, version, digest(sha256:…), signature }   # 來源與物證
  runtime:       { type, instance, url, httpPort }                    # 跑在哪
  provenance:    { serviceRequest, requestedBy, deploymentRequest, gate, deployedAt, result }
  dataClassification
  relationships: [ {type, target}, … ]   # CI 之間的依存(deployed-from / signed-by / runs-on)
```

## 受治理（不是放著好看）

`policy-cmdb.yml` 在每個 PR 強制 `cmdb_validate.py` + fail-closed self-test:
CI 結構不整 / 物證缺失 / **digest 與來源 DeploymentRequest 漂移** / 缺組態關係 → **PR 被擋**。

## 目錄慣例

```
cmdb/
└── <環境>/
    └── <應用名>.yaml      # 一個 CI = 一個應用在某環境的已部署實例
```

## 漂移對帳（TASK-E4）：抓出「沒走流程的變更」

CMDB 是「期望態」;真相要靠**對帳**確認。`scripts/reconcile.py` 比對每個 CI 的
`source.digest`(期望)與**線上實際 running image digest**——不符或實例缺漏即漂移
(有人手動改線上 / 塞了來路不明映像 / 把實例移掉 = 補單沒登錄)。

```bash
python3 scripts/reconcile.py                 # 本機:用 podman 實際態對帳
python3 scripts/reconcile.py --open-issue     # 漂移 → 自動開 GitHub issue 留痕
python3 scripts/reconcile.py --observed-file state.json   # 餵入實際態(self-test / 離線 / 正式)
```

| | PoC(本專案) | 銀行正式環境 |
|---|---|---|
| 實際態來源 | `podman inspect`(本機) | registry digest / orchestrator(k8s)/ 監控匯出 |
| 跑在哪 | 本機 / host 排程(podman 在 host,**非 GitHub hosted runner**) | 持續對帳(GitOps controller / 定期 job) |
| 漂移處置 | 開 issue(`--open-issue`) | 告警 + 自動矯正 / 變更工單 |

> 漂移 ≠ 自動修復。依「**補單≠漂白**」:(a) 補登 retroactive 變更 + PIR;(b) root cause 為何繞得過。

## See Also
- `scripts/cmdb_register.py`（部署成功 → 登錄 CI）
- `scripts/cmdb_validate.py`（CMDB 基線驗證,fail-closed）
- `scripts/reconcile.py`（漂移對帳:期望態 vs 線上實際態,TASK-E4）
- `deployments/README.md`（上游:部署請求即程式碼）
- `docs/cmdb-and-evidence-chain.md`（CMDB + 端到端證據鏈,TASK-D7）
- `docs/golden-path-request-to-deploy.md`（全貌,階段⑦）
