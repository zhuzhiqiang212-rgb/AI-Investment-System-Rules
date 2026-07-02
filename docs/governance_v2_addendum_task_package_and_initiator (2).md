# AI_PROJECT_GOVERNANCE_V2 ADDENDUM
# 补充制度：任务包输出标准 + 下一任务发起规则 + 验收包交付规则 + 审批提交标准

版本: V2-ADDENDUM-003
生效时间: 2026-06-10 JST
制度层级: AI_PROJECT_GOVERNANCE_V2 补充条款（与主制度同等效力）
关联主制度: AI_Investment_System/docs/AI_PROJECT_GOVERNANCE_V2.md
文件路径: AI_Investment_System/docs/governance_v2_addendum_task_package_and_initiator.md
变更说明: V2-ADDENDUM-002 → V2-ADDENDUM-003，新增第四部分 APPROVAL_SUBMISSION_STANDARD_V1

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
禁止执行对话          : 【维护对话】AI系统维护
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

### 2.1 核心规则

```
NEXT_TASK_INITIATOR = CLAUDE
```

### 2.2 固定流程（强制六阶段）

```
PROPOSAL（Claude 发起）
    ↓
APPROVAL（ChatGPT 审批：APPROVED / REJECTED）
    ↓
IMPLEMENTATION（Codex 执行，依据 TASK_PACKAGE.md）
    ↓
PRE_ACCEPTANCE（Claude 预检，含验收包全文 + APPROVAL_LEVEL 判断）
    ↓
FINAL_ACCEPTANCE（ChatGPT 最终验收，输出 PASS / FAIL）
    ↓
TASK_CLOSED（ChatGPT 输出 TASK_CLOSED）
    ↓
NEXT_PROPOSAL（Claude 发起下一任务，循环）
```

### 2.3 各角色发起权限

| 角色 | 可发起 NEXT_PROPOSAL | 可直接给 Codex 新任务 |
|------|---------------------|----------------------|
| Claude | YES（唯一合法发起方） | NO（须经 ChatGPT APPROVAL） |
| ChatGPT | NO（提出需求由 Claude 转化） | NO |
| Codex | NO | NO |
| 用户 | YES（通过 Claude 转化） | NO |

### 2.4 违规处理

| 违规场景 | Skill Gate 输出 |
|---------|----------------|
| Codex 自行发起新任务 | PROCESS_VIOLATION PV-001 |
| ChatGPT 直接给 Codex 新任务 | PROCESS_VIOLATION PV-003 |
| 跳过 PRE_ACCEPTANCE | PROCESS_VIOLATION PV-009 |

---

## 第三部分：VALIDATION_PACKAGE_DELIVERY_RULE_V1

### 3.1 制度目的

禁止 Claude PRE_ACCEPTANCE 只说"文件已生成"。
必须交付验收包 7 项内容，否则 PRE_ACCEPTANCE = INCOMPLETE。

### 3.2 Claude PRE_ACCEPTANCE 必须输出的 7 项内容

```
1. 文件名
2. 文件路径
3. 文件大小
4. 最后修改时间
5. 验收包摘要（100字以内）
6. 验收包全文 或 Drive viewUrl
7. 预检结论：PASS / INCOMPLETE / FAIL
```

### 3.3 违规判定

| 场景 | 状态 |
|------|------|
| 只输出"文件已生成" | INCOMPLETE |
| 有文件名/路径但无全文 | INCOMPLETE |
| 7项全部输出且预检结论明确 | 合规 |

---

## 第四部分：APPROVAL_SUBMISSION_STANDARD_V1

### 4.1 制度目的

禁止用户自行判断向 ChatGPT 提交什么内容。
Claude 在 PRE_ACCEPTANCE 自动判断 APPROVAL_LEVEL 并输出标准提交块。

### 4.2 APPROVAL_LEVEL 判断规则（Claude 自动判断）

| APPROVAL_LEVEL | 任务类型 | 典型例子 |
|---------------|---------|---------|
| LEVEL-1 | 治理制度类 | Governance / Task Package / GitHub Rule / Skill Gate / Addendum |
| LEVEL-2 | 策略类 | 资产配置 / 仓位引擎 / 买入触发器 / 止盈系统 / 日报结构 |
| LEVEL-3 | 代码类 | skill_gate.py / dashboard.html / 任何脚本修改 |

判断优先级：LEVEL-3 > LEVEL-2 > LEVEL-1

### 4.3 LEVEL-1 提交格式

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APPROVAL_LEVEL   : LEVEL-1
TASK_ID          : [任务编号]
文件名            : [文件名]
文件路径          : [Drive 完整路径]
文件大小          : [字节数]
Drive ID         : [文件 ID]
最后修改时间      : [JST 时间戳]
Claude 预检结果   : PASS / INCOMPLETE / FAIL
发给谁            : ChatGPT / AI投研总控台 V4
下一步唯一动作    : [一句话说明]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[以上内容可直接转发给 ChatGPT]
```

无需复制文件正文。

### 4.4 LEVEL-2 提交格式

LEVEL-1 全部字段，再附加：
```
策略摘要: [100字以内]
策略文件内容: [全文或关键章节]
```

### 4.5 LEVEL-3 提交格式

LEVEL-1 全部字段，再附加：
```
代码变更说明: [修改了什么，为什么]
代码内容: [修改代码全文 / diff / 验收包关键内容]
```

### 4.6 Claude PRE_ACCEPTANCE 输出规范

- 必须自动判断并输出 APPROVAL_LEVEL
- 必须按对应 Level 格式输出完整提交块
- 禁止要求用户自行判断 Level
- LEVEL-1 禁止附加正文

### 4.7 违规判定

| 违规场景 | 结果 |
|---------|------|
| 未输出 APPROVAL_LEVEL | PRE_ACCEPTANCE = INCOMPLETE |
| LEVEL 低报 | PRE_ACCEPTANCE = INCOMPLETE |
| LEVEL-2/3 缺策略/代码内容 | PRE_ACCEPTANCE = INCOMPLETE |

---

## 第五部分：与 AI_PROJECT_GOVERNANCE_V2 主制度的关系

本 Addendum 与主制度同等效力，冲突时以本 Addendum 为准（后制定原则）。

| 主制度条款 | Addendum 补充 |
|-----------|--------------|
| 第二章 五阶段流程 | 细化为六阶段，新增 PRE_ACCEPTANCE 验收包全文要求 |
| 第三章 Skill Gate | 新增 NEXT_TASK_INITIATOR 违规场景 |
| 第四章 角色边界 | 明确 NEXT_TASK_INITIATOR = CLAUDE |
| 新增 | TASK_PACKAGE_OUTPUT_STANDARD_V1 |
| 新增 | NEXT_TASK_INITIATOR_RULE_V1 |
| 新增 | VALIDATION_PACKAGE_DELIVERY_RULE_V1 |
| 新增 | APPROVAL_SUBMISSION_STANDARD_V1 |

---

## 快速参考卡

```
┌──────────────────────────────────────────────────────┐
│  GOVERNANCE V2 ADDENDUM V2-ADDENDUM-003 快速参考      │
├──────────────────────────────────────────────────────┤
│  任务包规则                                            │
│  ▸ APPROVAL 任务 → 必须生成 TASK_PACKAGE.md           │
│  ▸ 写入 docs/tasks/{TASK_ID}_TASK_PACKAGE.md         │
│  ▸ Codex 只依据 Drive 文件执行                        │
├──────────────────────────────────────────────────────┤
│  发起规则                                              │
│  ▸ NEXT_TASK_INITIATOR = CLAUDE（唯一）               │
│  ▸ TASK_CLOSED → Claude 发起 NEXT_PROPOSAL           │
├──────────────────────────────────────────────────────┤
│  验收包交付规则                                        │
│  ▸ PRE_ACCEPTANCE 必须输出 7 项内容                   │
│  ▸ 只说"文件已生成" → INCOMPLETE                      │
├──────────────────────────────────────────────────────┤
│  审批提交规则                                          │
│  ▸ Claude 自动判断 LEVEL-1 / 2 / 3                   │
│  ▸ LEVEL-3 > LEVEL-2 > LEVEL-1（优先级）              │
│  ▸ 禁止用户自行判断 Level                              │
├──────────────────────────────────────────────────────┤
│  完整六阶段流程                                        │
│  PROPOSAL → APPROVAL → IMPLEMENTATION                │
│  → PRE_ACCEPTANCE → FINAL_ACCEPTANCE                 │
│  → TASK_CLOSED → NEXT_PROPOSAL                       │
└──────────────────────────────────────────────────────┘
```
