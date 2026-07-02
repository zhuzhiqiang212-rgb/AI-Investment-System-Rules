# AI_PROJECT_GOVERNANCE_V2 ADDENDUM
# 补充制度：任务包输出标准 + 下一任务发起规则

版本: V2-ADDENDUM-001
生效时间: 2026-06-10 JST
制度层级: AI_PROJECT_GOVERNANCE_V2 补充条款（与主制度同等效力）
关联主制度: AI_Investment_System/docs/AI_PROJECT_GOVERNANCE_V2.md
文件路径: AI_Investment_System/docs/governance_v2_addendum_task_package_and_initiator.md

---

## 第一部分：TASK_PACKAGE_OUTPUT_STANDARD_V1

### 1.1 制度目的

禁止以聊天长文本作为任务执行依据。
所有需要 APPROVAL 的任务，必须生成标准 TASK_PACKAGE.md 文件，
写入 Drive，作为 Codex 执行的唯一合法依据。

### 1.2 触发条件

以下任意情况触发本标准：
- 任务需要 APPROVAL_REQUIRED: YES
- 任务影响 Drive 文件、代码、规则、dashboard
- 任务由 Claude / Codex / ChatGPT 任何角色发起

### 1.3 TASK_PACKAGE.md 固定字段（缺一不合规）

```
TASK_ID              : [唯一任务编号，格式 TASK-YYYY-MM-DD-NNN]
任务名称              : [明确任务标识]
执行对话              : [线程标识]
提案人                : [角色名]
执行人                : [角色名]
验收人                : [角色名，≠ 执行人]
任务类型              : [日报生产/系统维护/治理/分析]
影响范围              : [具体路径或模块]
APPROVAL_REQUIRED    : YES / NO
审批状态              : PENDING / APPROVED / REJECTED
CODEX_EXECUTION      : [Codex 可直接执行的完整指令，或"本任务无需Codex执行代码"]
ACCEPTANCE_CRITERIA  : [验收标准列表]
CLOSE_CONDITION      : [CLOSE 条件列表]
```

### 1.4 文件写入规则

- 写入路径：`AI_Investment_System/docs/tasks/`
- 文件命名：`{TASK_ID}_TASK_PACKAGE.md`
- 写入时机：PROPOSAL 完成后、APPROVAL 前
- Codex 只能依据 Drive 中的 TASK_PACKAGE.md 执行，不依据聊天文本

### 1.5 统一输出字段（验收包必含）

```
文件名:
文件路径:
文件大小:
最后修改时间:
状态: PASS / PARTIAL / FAIL
发给谁:
下一步唯一动作:
是否成功生成: YES / NO
```

### 1.6 禁止事项

- 禁止要求用户从聊天窗口复制执行指令发给 Codex
- 禁止以聊天文本作为 Codex 执行依据
- 禁止 TASK_PACKAGE.md 缺少任何固定字段
- 禁止在未写入 Drive 前宣布 APPROVED

---

## 第二部分：NEXT_TASK_INITIATOR_RULE_V1

### 2.1 制度目的

明确任务链中每个角色的发起权限，防止任务在未经正式流程的情况下被 Codex 或 ChatGPT 直接延续。

### 2.2 核心规则

```
NEXT_TASK_INITIATOR = CLAUDE
```

TASK_CLOSED 后，下一任务的发起权归属 Claude，且仅归属 Claude。

### 2.3 固定流程（强制，不可跳过任何阶段）

```
PROPOSAL（Claude 发起）
    ↓
APPROVAL（ChatGPT 审批：APPROVED / REJECTED）
    ↓
IMPLEMENTATION（Codex 执行，依据 TASK_PACKAGE.md）
    ↓
PRE_ACCEPTANCE（Claude 预检，输出预检报告）
    ↓
FINAL_ACCEPTANCE（ChatGPT 最终验收，输出 PASS / FAIL）
    ↓
TASK_CLOSED（ChatGPT 输出 TASK_CLOSED）
    ↓
NEXT_PROPOSAL（Claude 发起下一任务，循环）
```

### 2.4 各角色发起权限

| 角色 | 可发起 NEXT_PROPOSAL | 可直接给 Codex 新任务 |
|------|---------------------|----------------------|
| Claude | YES（唯一合法发起方） | NO（须经 ChatGPT APPROVAL） |
| ChatGPT | NO（不得直接发起，可提出需求由 Claude 转化为 PROPOSAL） | NO |
| Codex | NO | NO |
| 用户 | YES（通过 Claude 转化为 PROPOSAL） | NO（须经完整流程） |

### 2.5 违规处理

| 违规场景 | Skill Gate 输出 |
|---------|----------------|
| Codex TASK_CLOSED 后自行发起新任务 | PROCESS_VIOLATION PV-001 |
| ChatGPT 直接给 Codex 新任务（绕过 Claude PROPOSAL） | PROCESS_VIOLATION PV-003 |
| Claude 未输出 NEXT_PROPOSAL 直接跳到 IMPLEMENTATION | PROCESS_VIOLATION PV-001 |
| 跳过 PRE_ACCEPTANCE 直接 FINAL_ACCEPTANCE | PROCESS_VIOLATION PV-009 |

### 2.6 ChatGPT 提出需求的合法路径

ChatGPT 可以提出新任务需求，但必须通过以下路径：

```
ChatGPT 提出需求（自然语言）
    ↓
Claude 将需求转化为标准 PROPOSAL + TASK_PACKAGE.md
    ↓
ChatGPT 审批（APPROVED / REJECTED）
    ↓
后续正常流程
```

ChatGPT 提出需求 ≠ PROPOSAL，不可直接触发 IMPLEMENTATION。

---

## 第三部分：与 AI_PROJECT_GOVERNANCE_V2 主制度的关系

| 主制度条款 | 本 Addendum 补充内容 |
|-----------|---------------------|
| 第二章 五阶段流程 | 新增 PRE_ACCEPTANCE 阶段（Claude 预检），细化为六阶段 |
| 第三章 Skill Gate 违规检测 | 新增 NEXT_TASK_INITIATOR 违规场景映射 |
| 第四章 角色职责边界 | 明确 NEXT_TASK_INITIATOR = CLAUDE |
| 新增 | TASK_PACKAGE_OUTPUT_STANDARD_V1（禁止聊天长文本作为执行依据） |

本 Addendum 与主制度同等效力，冲突时以本 Addendum 为准（后制定原则）。

---

## 快速参考卡

```
┌──────────────────────────────────────────────────┐
│  GOVERNANCE V2 ADDENDUM 快速参考                  │
├──────────────────────────────────────────────────┤
│  任务包规则                                        │
│  ▸ 所有 APPROVAL 任务 → 必须生成 TASK_PACKAGE.md  │
│  ▸ 写入 docs/tasks/{TASK_ID}_TASK_PACKAGE.md     │
│  ▸ Codex 只依据 Drive 文件执行，不依据聊天文本     │
│  ▸ 固定字段 13 项，缺一不合规                      │
├──────────────────────────────────────────────────┤
│  发起规则                                          │
│  ▸ NEXT_TASK_INITIATOR = CLAUDE（唯一）           │
│  ▸ TASK_CLOSED → Claude 发起 NEXT_PROPOSAL       │
│  ▸ ChatGPT 提需求 → Claude 转化 → ChatGPT 审批   │
│  ▸ Codex 不得自行发起任何新任务                    │
├──────────────────────────────────────────────────┤
│  完整六阶段流程                                    │
│  PROPOSAL → APPROVAL → IMPLEMENTATION            │
│  → PRE_ACCEPTANCE → FINAL_ACCEPTANCE             │
│  → TASK_CLOSED → NEXT_PROPOSAL                   │
└──────────────────────────────────────────────────┘
```
