# TODO / Backlog — itops_and_caas

> 這份是「斷 session 也能接續」的單一真相。任何新 session(或斷線後)從這裡 + 記憶接手。
> 動工慣例:逐項做 → 開分支 → PR → 7 道必過檢查綠 → squash 合併;護欄變更(動 policies/、
> .github/workflows/、scripts/ 閘門)PR 標「需資安審核(SoD)」。

## 🔄 如何接續(斷 session / 換 session 都適用)

1. **讀 repo 內的接續狀態**:[`docs/session-handoff.md`](docs/session-handoff.md)——現在到哪、活著的東西、關鍵決策、踩過的雷、操作慣例。**這份在 repo 裡,不依賴任何外部記憶**(光靠 git repo 就能接續)。(Claude 的跨 session 記憶 `~/.claude/.../memory/` 是補充,但 repo 自己已自足。)
2. **看真實進度,別只信文件**:`git log --oneline -20`、本檔的勾選狀態、`docs/*-evidence.html` / `governance-console.html` / `cmdb-topology.html`。
3. **驗證當前狀態可跑**:
   ```bash
   cd ~/Documents/itops_and_caas
   python3 scripts/cmdb_validate.py            # CMDB 15 CI 應全過
   bash scripts/tests/deploy-gate/selftest.sh  # 7/7
   bash scripts/tests/promote-gate/selftest.sh # 7/7
   git status                                  # 工作區是否乾淨
   ```
4. **環境前置**(若要真跑 VM/部署):libvirt(qemu:///system,default NAT)、tofu、sshpass、cdrtools;
   Debian cloud image 在 `~/itops-vm/images/`(不入版控)。詳見 `iac/environments/vm-openliberty/README.md`。
5. **主線計畫**:itops × supply-chain 整合計畫在 `~/Documents/supply-chain/itops-l4-integration-plan.md`。

## ✅ 已完成(本波,2026-06-15~16,見 git log PR#28~#39)

- 測試 gate(兩層 fail-closed)、真 live 端到端(雙環境→四環境同 digest)、修 7+ 個真 live bug
- 收口:COMPLIANCE_MAP 補 D/E/F、portfolio case-study、as-code 全歷程、關 drift #21
- **真整合**:supply-chain → itops handoff(itops 當活的部署治理中樞)
- **可視化**:治理後台 console、單據追溯 ticket-trace、CMDB 拓樸圖
- **真 VM 部署目標**:OpenTofu 開 QEMU/libvirt VM 跑 OpenLiberty(`deploy_openliberty_vm.sh`)
- **CMDB 多層拓樸**:host → middleware → software(15 CI、圖完整性)

## 📋 待辦(依優先序)

### ✅ 0 — itops × iTop(Combodo)真整合(2026-06-16 完成,PR 待合)
> Ryan 一路說的「itop」其實是 **iTop 產品**(真 ITSM/CMDB)。詳見 `integration/itop/README.md`。
- [x] iTop 3.2.2 本機 Docker 站起 + **完整 ITIL 模型**(220 表;修掉舊安裝只裝出最小模型的雷)
- [x] **啟用 REST API**:給 admin「REST Services User」profile;建 least-privilege 服務帳號 `svc_itops_sync`
      (註:3.2.x 的閘門是 `secure_rest_services`+`HasProfile`,舊筆記的 `allowed_rest_profiles` 無效)
- [x] 寫 `scripts/itop_sync.py`:host→Server、middleware→WebServer、app→WebApplication(原生影響圖)
      + 服務請求→UserRequest + 部署→RoutineChange;冪等;五環境 15 CI 跑通
- [x] 接 trigger:`integration/itops_ingest.sh` 部署成功後 opt-in(`ITOP_SYNC=1`)呼叫 itop_sync(軟失敗,不擋部署)
- [x] 一鍵重現腳本 `integration/itop/setup-itop.sh`(容器→安裝→修權限→啟 REST→建帳號;密碼走 `.itop-secrets`)
> ⚠️ 接續者:iTop 容器若關了,跑 `bash integration/itop/setup-itop.sh` 即可重站(真的 ~3 分鐘,已腳本化驗過)。
> 深化(非阻塞):同步狀態回寫治理後台、工單帶 CAB 欄位、改用 iTop Synchro Data Source 自動 reconcile。

### A — 收口 / 可見性(低成本、對履歷回報高)
- [ ] 把 CMDB 拓樸圖 + 單據追溯掛進治理後台 / README 文件導覽
- [ ] 治理後台加「single-ticket 連結」與「拓樸連結」入口

### B — itops × supply-chain 真整合深化(主線;計畫見 supply-chain/itops-l4-integration-plan.md)
- [ ] **Tier 1**:檔案型 L4 部署驗章(jar/war verify-blob)接進 supply-chain;先 github demo 跑通
- [ ] **Tier 2**:cosign 金鑰後端換 Vault transit — 先 standup `~/Documents/vault-research`(實作 0%,todo 全沒勾)→ enable transit → `--key hashivault://`
- [ ] 自動化:supply-chain CI `repository_dispatch` 觸發 itops ingest(self-hosted runner)

### C — 補強清單(深度;誠實未竟)
- [ ] 真 SBOM/SCA L4:syft/grype 實跑(目前是設計稿,syft/grype 未裝)
- [ ] uat/prod 真容器/VM 全跑(機制已備,只差起資源)
- [ ] workflow 真 fire:`promote.yml` / `emergency-pir.yml` / `supply-chain-sign.yml` 從未真執行
- [ ] **CMDB 再深化成真企業 CMDB**:加網路/DB/服務依賴 CI、接 discovery 自動發現(目前只有 host→middleware→software 主軸)
- [ ] SoD:單人模擬 → 多人核准(或文件化對映,現 SOLO 模式 approver=0)

### D — 清理(隨手)
- [ ] 收 VM:`tofu -chdir=iac/environments/vm-openliberty destroy -auto-approve`
- [ ] 收殘留 podman 容器(若有):各 env `tofu destroy`

## 🤖 若要「自動接續」(可選)
本檔 + 記憶已足以讓任何新 session 手動接續。若要**無人值守自動推進**,可用排程雲端代理:
`/schedule`(cron 雲端 agent,逐 TODO 執行)或 `/loop`。注意會計費且自動跑,建議只在你確認過項目後用。
