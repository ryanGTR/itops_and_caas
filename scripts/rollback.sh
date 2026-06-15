#!/usr/bin/env bash
# GitOps 回退(rollback)— TASK-F4
#
# 把某環境某 app 的部署檔回退到「上一個已知良好」digest:對最近一次過版 commit
# 做 git revert。GitOps 的回退不是「手動改回去」,而是**前向新增一個 revert commit**——
# 歷史只進不退,revert commit 本身就是可稽核的回退軌跡(誰、何時、從哪個 digest 退到哪個)。
# 回退後重新部署,會再次經過 policy-promote / D5 驗章閘門,確保退回去的也是已驗章產物。
#
# 預設 dry-run(只看不做);確認後加 --apply 才真的 revert。
#
# 對應治理控制項:ISO 20000 變更管理(回退);ISO 27001 A.5.3 SoD(回退也走 PR+核准)。
#
# 用法:
#   rollback.sh --app <app> --env <env> [--commit <sha>] [--apply]
#   --commit 省略時 = 最近一次動到該部署檔的 commit(通常即過版 commit)。
set -euo pipefail

APP=""; ENV=""; COMMIT=""; APPLY=0
usage() {
  echo "用法:rollback.sh --app <app> --env <env> [--commit <sha>] [--apply]" >&2
  exit 2
}
while [ $# -gt 0 ]; do
  case "$1" in
    --app) APP="${2:-}"; shift 2 ;;
    --env) ENV="${2:-}"; shift 2 ;;
    --commit) COMMIT="${2:-}"; shift 2 ;;
    --apply) APPLY=1; shift ;;
    -h|--help) usage ;;
    *) echo "未知參數:$1" >&2; usage ;;
  esac
done
[ -n "$APP" ] && [ -n "$ENV" ] || usage

FILE="deployments/${ENV}/${APP}.yaml"
[ -f "$FILE" ] || { echo "✗ 找不到部署檔:$FILE" >&2; exit 2; }

digest_of() { grep -E 'digest:' | head -1 | sed -E 's/.*(sha256:[0-9a-f]{64}).*/\1/'; }

# 欲回退的 commit:預設取最近一次動過該檔的 commit
[ -n "$COMMIT" ] || COMMIT="$(git log -n1 --format=%H -- "$FILE")"
[ -n "$COMMIT" ] || { echo "✗ 找不到動過 $FILE 的 commit" >&2; exit 2; }

cur_digest="$(digest_of < "$FILE")"
prev_digest="$(git show "${COMMIT}^:${FILE}" 2>/dev/null | digest_of || true)"

echo "🔁 GitOps 回退 — ${APP} @ ${ENV}"
echo "  目標檔        :$FILE"
echo "  欲回退 commit :$COMMIT"
git show -s --format='  變更內容      :(%ci) %s' "$COMMIT"
echo "  目前 digest   :${cur_digest:-<無>}"
echo "  回退後 digest :${prev_digest:-<無>}(上一個已知良好)"

if [ -z "$prev_digest" ]; then
  echo "✗ 取不到上一版 digest——該 commit 可能是首次建立此檔,無前一版可退。" >&2
  exit 1
fi

if [ "$APPLY" != 1 ]; then
  echo
  echo "（dry-run:未變更。確認無誤後加 --apply 執行,會新增一個 revert commit 作為回退軌跡。）"
  exit 0
fi

echo
echo "▶ git revert --no-edit $COMMIT   @ $(date -u +%FT%TZ)"
git revert --no-edit "$COMMIT"
new_digest="$(digest_of < "$FILE")"
echo "✅ 已回退:$FILE digest 現為 ${new_digest}"
echo "  回退軌跡 = 新增的 revert commit:$(git log -n1 --format=%H)"
echo "  下一步:重新部署(scripts/deploy_openliberty.sh)→ 重新驗章閘門再次把關回退後的 digest。"
