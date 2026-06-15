#!/usr/bin/env bash
# setup_branch_protection.sh — 以程式碼套用 main 分支保護([TASK-05] / [TASK-06])
#
# 目的:讓「改政策的人」與「用政策的人」分離具有「強制力」,且讓每個變更都
#       必須走可追溯的 PR 流程。CODEOWNERS 只指定 owner;真正的強制來自
#       branch protection:Require code owner review + 禁直接 push + enforce admins。
#
# 對應治理控制項:
#   - ISO 27001 A.5.3 職責分離(核心)      [TASK-05]
#   - ISO 27001 A.8.4 原始碼存取控制         [TASK-05]
#   - ISO 27001 A.8.32 / ISO 20000 變更管理  [TASK-06](禁直接 push、必過政策檢查)
#
# 為何需要這支腳本:branch protection 是 GitHub repo 設定,無法用本機 git 完成。
#       把它寫成可重複執行、可版控、可審核的腳本(policy as code),
#       而非靠人在 UI 上手點(不可稽核、會漏)。
#
# 前置:gh CLI 已可用,且持有對該 repo 的 admin 權限。
#       建議用含 "Administration: Read and write" 的 fine-grained token:
#         GH_TOKEN="github_pat_xxx" REPO="<org>/<repo>" ./scripts/setup_branch_protection.sh
#
# 模式:
#   預設        = 嚴格 SoD:需 code owner 核准 1 人(多人 / org 環境)。
#   SOLO=1      = 單人模式:不需他人核准(個人 repo 無法核准自己的 PR),
#                 但仍保留「禁直接 push + 必過政策檢查 + enforce admins」。
#
# 注意:此操作會變更線上 repo 設定,請由平台 + 資安群組確認後執行。

set -euo pipefail

REPO="${REPO:?請設定 REPO=<org>/<repo>}"
BRANCH="${BRANCH:-main}"
SOLO="${SOLO:-0}"

if [[ "$SOLO" == "1" ]]; then
  echo "模式:SOLO(單人)— 不要求他人核准,但保留禁直接 push + 必過檢查 + enforce admins"
  REQUIRE_CODEOWNER="false"
  REVIEW_COUNT=0
else
  echo "模式:嚴格 SoD — 需 code owner 核准(適合多人 / organization)"
  REQUIRE_CODEOWNER="true"
  REVIEW_COUNT=1
fi

echo "套用分支保護:${REPO} @ ${BRANCH}"

# 透過 GitHub REST API 設定分支保護。重點欄位:
#   - required_pull_request_reviews.require_code_owner_reviews:動到 CODEOWNERS
#       涵蓋的政策路徑時,必須由對應 owner(平台+資安)核准 → 「改護欄需更嚴格審核」。
#   - enforce_admins=true:連 admin 也不能繞過(SoD 不留後門)。
#   - required_status_checks:六道護欄必須通過才可合併(變更管理 / A.8.32)。
#       policy-secrets / policy-structure(Phase 1)+ policy-iac(Phase 2 IaC 閘門)
#       + cmdb-validate(Phase D 組態基線閘門,TASK-D7:防 CMDB 與真相漂移)
#       + deploy-gate-selftest(Phase D 部署前驗章閘門 self-test,TASK-D5)
#       + change-class(Phase E 變更分類閘門,TASK-E1:例外受控、護欄不鬆綁)。
#       原則:會跑的護欄就該強制——「不合規根本合不了」不留漏網。
#   - restrictions=null:不額外限制可推送者(交由 PR + review 控管)。
#   - allow_force_pushes / allow_deletions=false:保護歷史可追溯性。
#
# 巢狀 JSON body 以 --input 餵入(較 -f/-F 的 bracket 寫法穩定可靠)。
read -r -d '' BODY <<JSON || true
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["policy-secrets", "policy-structure", "policy-iac", "cmdb-validate", "deploy-gate-selftest", "change-class"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "require_code_owner_reviews": ${REQUIRE_CODEOWNER},
    "required_approving_review_count": ${REVIEW_COUNT},
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_linear_history": true
}
JSON

printf '%s' "$BODY" | gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "/repos/${REPO}/branches/${BRANCH}/protection" \
  --input -

echo "完成。請以下列指令確認:"
echo "  gh api /repos/${REPO}/branches/${BRANCH}/protection | jq ."
