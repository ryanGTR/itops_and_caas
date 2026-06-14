# trust/ — 簽章信任根(cosign)

> 這個目錄放這條黃金路徑的**簽章信任根**:用來驗證「部署的映像確實由本平台簽過」。

## 內容

| 檔案 | 是什麼 | 進版控? |
|---|---|---|
| `cosign.pub` | **公鑰**(信任根),部署前驗章(TASK-D5)用它驗 | ✅ 是(公開無妨) |
| `cosign.key` | **私鑰**,簽章用 | ❌ **絕不進版控**(被 `.gitignore` 的 `*.key` 忽略) |

## 信任模式(PoC vs 正式環境)

| | PoC(本專案) | 銀行正式環境 |
|---|---|---|
| 金鑰 | cosign **key-pair**(本地產) | **KMS / HSM-backed**(金鑰不落地) |
| 私鑰保管 | 本地檔案,gitignore + 機敏掃描雙重防進版控 | KMS/HSM,簽章經 API,人拿不到金鑰 |
| 決策 | 見 `docs/adr/0002` | 同上 |

> 為什麼私鑰絕不進版控:一旦外洩,攻擊者可偽造「本平台已簽」的惡意映像。
> 這正是 TASK-03 機敏掃描護欄要擋的——`*.key` 想進版控會被 gitleaks 攔下。

## 怎麼用

- **簽章(在 app repo)**:`.github/workflows/supply-chain-sign.yml` 用私鑰(以 secret `COSIGN_PRIVATE_KEY` 注入)簽映像 digest。
- **驗章(部署前,TASK-D5)**:用本目錄的 `cosign.pub` 驗:
  ```bash
  cosign verify --key trust/cosign.pub <image>@<digest>
  ```
- **重產金鑰(如需)**:
  ```bash
  cd trust && COSIGN_PASSWORD="<密碼>" cosign generate-key-pair
  # cosign.key 會被 gitignore;只 commit cosign.pub
  ```

## See Also
- `docs/supply-chain-signing.md`(簽章/驗章完整模型)
- `docs/adr/0002-openliberty-runtime-and-deploy.md`(金鑰選型決策)
- `.github/workflows/supply-chain-sign.yml`(可重用簽章 pipeline)
