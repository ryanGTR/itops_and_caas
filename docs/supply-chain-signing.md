---
title: 供應鏈建置與簽章（Build → SBOM → Scan → Sign）
type: howto
created: 2026-06-14
updated: 2026-06-14
tags: [supply-chain, sbom, sca, cosign, signing, isms, iso27001]
---

# 供應鏈建置與簽章

> 對應 `PROJECT_PLAN.md` [TASK-D4]。把要部署的 Java 應用建成**可驗證來源**的容器映像:
> build → SBOM → SCA 掃描 → cosign 簽章。並補上 `supply-chain` 專案的 **L4 cosign 簽章缺口**。

## 角色分工(呼應權責邊界)

- **itops(平台)**:提供「鋪好的路」——可重用簽章 pipeline(`.github/workflows/supply-chain-sign.yml`)
  + 簽章信任根(`trust/cosign.pub`)+ 簽章政策。**定義**鏈長什麼樣。
- **supply-chain(被治理的 app)**:`github/app/backend`(Java/Maven)是部署標的;
  在它自己的 repo **呼叫** itops 的可重用 pipeline 來 build/sign。**執行**這條鏈。

> 為什麼這樣分:app 原始碼屬於 app repo;平台只負責「定義鏈 + 持有信任根 + 部署前驗章」。
> 詳見 `docs/tooling-roles-and-real-world-mapping.md`。

## 這條鏈(每一步的治理意義)

```
build ──▶ SBOM(syft) ──▶ SCA 掃描(grype) ──▶ cosign 簽章 ──▶ 輸出 digest
  │          │                │                   │              │
不可變映像   軟體物料清單      已知漏洞高風險即擋    來源可驗證      回填 DeploymentRequest
            (A.8.28)         (A.8.8 弱點管理)     (A.8.28 完整性)  (spec.source.digest)
```

- **以 digest 簽,不簽 tag**:tag 可被覆蓋,digest 不可變——簽 digest 才有完整性保證。
- **SBOM 以 attestation 綁上映像**:之後可追溯這個映像由哪些元件組成。
- **驗章在部署前**(TASK-D5):用 `trust/cosign.pub` 驗,未簽/驗不過 → fail-closed 拒絕部署。

## 呼叫方式(app repo 端)

在 `supply-chain` 的 app repo 加一個 workflow 呼叫 itops 的可重用 pipeline:

```yaml
jobs:
  sign:
    uses: ryanGTR/itops_and_caas/.github/workflows/supply-chain-sign.yml@main
    with:
      image_name: ghcr.io/ryangtr/supply-chain-backend
      context: ./github/app/backend
      dockerfile: ./github/app/backend/Dockerfile
    secrets:
      registry_username: ${{ github.actor }}
      registry_password: ${{ secrets.GITHUB_TOKEN }}
      cosign_private_key: ${{ secrets.COSIGN_PRIVATE_KEY }}   # 對應 trust/cosign.pub
      cosign_password:    ${{ secrets.COSIGN_PASSWORD }}
```

> 私鑰以 GitHub Secret `COSIGN_PRIVATE_KEY` 注入(對應 `trust/cosign.pub`);**絕不進版控**。
> 正式環境改 KMS/HSM(見 `docs/adr/0002`)。

## 驗證狀態(誠實標註)

- ✅ 信任根:`trust/cosign.pub` 已產(cosign key-pair;私鑰本地、`*.key` 已 gitignore)。
- ✅ pipeline-as-code:可重用簽章 workflow 已定義。
- ⏳ **真實 build/sign/掃描**(需 app + secrets + 安裝 cosign/syft/grype on runner)留到「實跑場」。
  TASK-D4 驗收的「產出帶 SBOM+掃描+簽章的映像」於實跑時完成;本次先把鏈與信任根就位。

## 對應治理控制項

| 控制項 | 體現 |
|---|---|
| ISO 27001 A.8.28 安全開發 / 供應鏈完整性 | 簽章 + 以 digest 簽 |
| ISO 27001 A.8.8 弱點管理 | SCA 掃描高風險即擋 |
| ISO 27001 A.8.25 安全開發生命週期 | build→SBOM→scan→sign 一條鏈 |
| 補 supply-chain L4 缺口 | cosign 簽章落地 |

## See Also
- `.github/workflows/supply-chain-sign.yml`（可重用簽章 pipeline）
- `trust/README.md`（信任根）
- `docs/golden-path-request-to-deploy.md`（部署黃金路徑全貌，階段③）
- `deployments/README.md`（digest 回填 DeploymentRequest）
