#!/usr/bin/env bash
# setup_branch_protection.sh — 以程式碼套用 main 分支保護([TASK-05])
#
# 目的:讓「改政策的人」與「用政策的人」分離具有「強制力」。
#       CODEOWNERS 只指定 owner;真正的強制來自 branch protection 開啟
#       「Require review from Code Owners」+ 禁止直接 push + enforce admins。
#
# 對應治理控制項:
#   - ISO 27001 A.5.3 職責分離(核心)
#   - ISO 27001 A.8.4 原始碼存取控制
#
# 為何需要這支腳本:branch protection 是 GitHub repo 設定,無法用本機 git 完成。
#       把它寫成可重複執行、可版控、可審核的腳本(policy as code),
#       而非靠人在 UI 上手點(不可稽核、會漏)。
#
# 前置:已安裝並登入 gh CLI(gh auth login),且對該 repo 有 admin 權限。
# 用法:
#   REPO="<org>/<repo>" BRANCH="main" ./scripts/setup_branch_protection.sh
#
# 注意:此操作會變更線上 repo 設定,請由平台 + 資安群組確認後執行。

set -euo pipefail

REPO="${REPO:?請設定 REPO=<org>/<repo>}"
BRANCH="${BRANCH:-main}"

echo "套用分支保護:${REPO} @ ${BRANCH}"

# 透過 GitHub REST API 設定分支保護。重點欄位:
#   - required_pull_request_reviews.require_code_owner_reviews=true
#       → 動到 CODEOWNERS 涵蓋的政策路徑時,必須由對應 owner(平台+資安)核准。
#         這就是「改護欄需更嚴格審核」的強制點。
#   - required_approving_review_count=1(政策路徑因 code owner 規則而更嚴格)
#   - enforce_admins=true → 連 admin 也不能繞過(SoD 不留後門)
#   - required_status_checks → 兩道護欄必須通過才可合併
#   - allow_force_pushes/allow_deletions=false → 保護歷史可追溯性
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "/repos/${REPO}/branches/${BRANCH}/protection" \
  -f "required_status_checks[strict]=true" \
  -f "required_status_checks[contexts][]=policy-secrets" \
  -f "required_status_checks[contexts][]=policy-structure" \
  -F "enforce_admins=true" \
  -F "required_pull_request_reviews[require_code_owner_reviews]=true" \
  -F "required_pull_request_reviews[required_approving_review_count]=1" \
  -F "required_pull_request_reviews[dismiss_stale_reviews]=true" \
  -F "restrictions=null" \
  -F "allow_force_pushes=false" \
  -F "allow_deletions=false" \
  -F "required_linear_history=true"

echo "完成。請以下列指令確認:"
echo "  gh api /repos/${REPO}/branches/${BRANCH}/protection | jq ."
