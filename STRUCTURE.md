# Repo 結構定義(STRUCTURE.md)

本檔定義 Phase 1 的標準 repo 結構。Claude Code 執行 [TASK-01] 時依此建立。

```
pe-idp-platform/
├── README.md                        # 平台說明、如何使用範本
├── PROJECT_PLAN.md                  # 主工作計畫
├── COMPLIANCE_MAP.md                # ISO 對照表
├── GOVERNANCE_BRIEF.md              # 給稽核/主管的提案
├── CLAUDE.md                        # 給 Claude Code 的脈絡
├── STRUCTURE.md                     # 本檔
├── .gitignore
├── LICENSE
├── CODEOWNERS                       # 職責分離核心:誰能改什麼
│
├── .github/
│   ├── pull_request_template.md     # PR 範本(變更目的/風險/回退)
│   └── workflows/
│       ├── policy-secrets.yml       # [TASK-03] 機敏掃描守門員
│       └── policy-structure.yml     # [TASK-04] 結構規範守門員
│
├── policies/                        # 政策即程式碼(受 SoD 保護)
│   ├── README.md                    # 政策清單與對應 ISO 編號
│   └── rules/                       # 各條規則定義
│
├── scaffold/                        # [TASK-02] 自助範本內容
│   ├── README.md                    # 範本說明:替開發者省掉什麼
│   ├── project-template/            # 標準專案骨架
│   │   ├── README.template.md
│   │   ├── .gitignore
│   │   └── .github/workflows/       # 範本內建的 CI 骨架
│   └── docs/
│
└── scripts/
    ├── check_structure.py           # [TASK-04] 結構檢查
    └── generate_audit_report.py     # [TASK-07] 稽核證據產出
```

## 關鍵設計說明

- **`CODEOWNERS`** 是 SoD 的技術實現核心。`.github/workflows/` 與 `policies/`
  指定給平台+資安群組;`scaffold/` 一般開發者可貢獻。
- **`policies/`** 與 `scaffold/` 分離,呼應「改護欄」與「用護欄」的權限分離。
- **`scripts/`** 放可被 CI 呼叫、也可手動執行產出稽核證據的工具。
