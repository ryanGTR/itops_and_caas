# itops_and_caas — 一頁總覽(先讀這頁)

> **一句話**:一個把「合規從牆上的政策,變成系統裡不可繞過的事實」做出來、且想透的可動 PoC +
> 完整論述。給面試官 / 主管 / 未來的我 30 秒看懂這是什麼、證明了什麼、為何重要。

## 這是什麼
一個銀行內部開發者平台(IDP)的治理 PoC:把 ISMS / ISO 27001 / ISO 20000 / ITIL 的控制,
用 **policy-as-code + fail-closed 閘門 + 自動物證** 落地成「會跑的系統」,不是投影片。
核心理念:**護欄而非閘門、合規 by construction、鬆綁審核不鬆綁技術閘門**。

## 它證明了什麼(三個能力,都是真的可動)
1. **會動的治理系統**:服務請求 → 變更 → 供應鏈簽章/掃描 → **部署前驗章(fail-closed)** →
   build-once 多環境晉級 → CMDB-as-code → 漂移對帳 → 例外/補單治理。真 cosign / 真 podman /
   真 OpenLiberty / 真 QEMU VM 跑過,抓修過十幾個真 bug。
2. **把抽象變具體的閘門 demo**:**翻一個資料分級標籤 internal→confidential,系統當場擋下並列出缺的高階控制**
   (`policies/classification-matrix.yaml` + `scripts/validate_classification_controls.py`)——
   ISMS 風險為本從「貼標籤」變「系統強制」。這是對決「只交報告」的最有力證據。
3. **想透的論述**:從現況誠實自評 → 系統解法 → 整體平台藍圖 → 簡報 → 管理方向(見下方文件地圖)。

## 怎麼讀(依你是誰)
| 你是 | 先看 |
|---|---|
| 想 30 秒懂 | 本頁 + [`docs/case-study.md`](docs/case-study.md) |
| 稽核 / 資安 | [`docs/framework-conformance-assessment.md`](docs/framework-conformance-assessment.md)(名目 vs 真 + 逐項系統解法) |
| 想看會動的東西 | `docs/governance-console.html`(治理後台)、跑 `bash scripts/tests/classification/selftest.sh`(翻標籤 demo) |
| 主管 / 要提案 | [`docs/exec-pitch-outline.md`](docs/exec-pitch-outline.md) + [`docs/governance-pitch-deck.html`](docs/governance-pitch-deck.html) |
| 想懂治理思路 | [`docs/greenfield-governance-platform.md`](docs/greenfield-governance-platform.md)、[`docs/management-direction-doctrine.md`](docs/management-direction-doctrine.md) |
| 工程接續 | [`README.md`](README.md) + [`TODO.md`](TODO.md) + [`docs/session-handoff.md`](docs/session-handoff.md) |

## 誠實邊界(這也是它的價值)
這是 PoC,不假裝全綠:SoD/CAB 是單人模擬、部分血統是範例值、只覆蓋 ITSM 建置面(未碰 SLA/事件/問題)。
**能誠實指出「哪裡是名目、怎麼補成真」本身就是能力證明**——詳見
[`docs/framework-conformance-assessment.md`](docs/framework-conformance-assessment.md) 與
[`docs/retrospective.md`](docs/retrospective.md)。

## 它「為了什麼」
不是為了被某家公司採用,是當一個**無可否認、誠實、連貫的資產**——
證明作者能把治理框架翻譯成系統事實、且看得懂兩邊(工程 ↔ 公文/監理)的語言。
完整論述見 [`docs/retrospective.md`](docs/retrospective.md)。
