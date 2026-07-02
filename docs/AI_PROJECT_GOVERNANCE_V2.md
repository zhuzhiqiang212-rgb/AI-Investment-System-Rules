# AI_PROJECT_GOVERNANCE_V2
# AI投研体系 最高治理制度

版本：V2.0
生效时间：2026-06-10 JST
制度层级：最高制度（优先于所有 Skill、规则、角色指令）
适用范围：Claude / Codex / ChatGPT / 所有执行角色
文件路径：AI_Investment_System/docs/AI_PROJECT_GOVERNANCE_V2.md
制度状态：ACTIVE

---

## 第一章 最高原则

### 1.1 制度目的

本制度确保 AI投研体系的所有任务——无论由 Claude、Codex 还是 ChatGPT 发起或执行——都经过完整的五阶段流程，防止未经批准的操作进入生产系统，保护用户资产和决策质量。

### 1.2 制度优先级

```
AI_PROJECT_GOVERNANCE_V2（本制度）
    ↓ 优先于
Skill Gate（skill_gate.py）
    ↓ 优先于
所有 rules/ 规则文件
    ↓ 优先于
角色指令（Claude Skill / Codex 指令 / ChatGPT 提示）
    ↓ 优先于
单次对话指令
```

任何单次对话指令、用户临时要求、角色自行判断，均不得绕过本制度。

### 1.3 不可豁免事项

以下任何理由均不构成绕过五阶段流程的合法理由：

- "紧急情况"
- "用户已在对话中口头批准"
- "上次任务已经做过类似的事"
- "这只是一个小改动"
- "ChatGPT / Claude / Codex 认为可以直接执行"

---

## 第二章 五阶段任务流程

### 强制流程图

```
PROPOSAL（提案）
    ↓
    [Skill Gate 检查：提案格式合规？]
    ├─ FAIL → PROCESS_VIOLATION → 阻断，退回提案方
    └─ PASS ↓
APPROVAL（批准）
    ↓
    [必须有明确批准人签字，且批准人 ≠ 提案人]
    ├─ 未批准 → 任何执行请求 → PROCESS_VIOLATION
    └─ 已批准 ↓
IMPLEMENTATION（实施）
    ↓
    [Skill Gate 检查：实施产物合规？]
    ├─ FAIL → PROCESS_VIOLATION → 阻断，写入失败日志
    └─ PASS ↓
ACCEPTANCE（验收）
    ↓
    [验收人 ≠ 执行人；必须输出标准验收包]
    ├─ 未验收 → 任务不得 CLOSE
    └─ 已验收 ↓
CLOSE（关闭）
    ↓
    [验收包归档至 reports/validation/]
    [任务状态更新为 CLOSED]
```

### 2.1 PROPOSAL（提案阶段）

**触发条件**：任何角色发起新任务时，必须先提交提案。

**提案必填字段**（缺一不允许进入 APPROVAL）：

```
任务名称：[明确的任务标识]
执行对话：[AI投研总控台 + 正式日报生产 / AI系统维护]
提案人：[Claude / Codex / ChatGPT / 用户]
预期执行人：[角色名]
预期验收人：[角色名，必须 ≠ 执行人]
任务类型：[日报生产 / 系统维护 / 治理 / 分析 / 其他]
影响范围：[dashboard / Drive文件 / 规则 / 代码 / 仅输出]
是否涉及账户操作：[YES / NO]
是否涉及规则变更：[YES / NO]
预计输出文件：[文件名列表]
```

**Skill Gate 在 PROPOSAL 阶段检查**：
- 执行对话标识是否存在
- 验收人是否与执行人不同
- 是否涉及账户操作（YES → 自动升级为用户确认必填项）

### 2.2 APPROVAL（批准阶段）

**批准人规则**：

| 任务类型 | 批准人 |
|---------|--------|
| 日报生产 | ChatGPT / AI投研总控台 V4 |
| 规则变更 | ChatGPT / AI投研总控台 V4 |
| 系统维护 | 用户 或 ChatGPT |
| 账户相关操作 | 用户（必须） |
| 治理制度变更 | 用户（必须） |

**APPROVAL 格式**（批准人必须明确输出）：

```
APPROVED
任务名称：[与提案一致]
批准人：[角色名]
批准时间：[时间戳]
批准条件：[无 / 须满足以下条件才可执行：...]
```

**未经 APPROVAL，任何角色不得进入 IMPLEMENTATION。**
违反者：Skill Gate 输出 `PROCESS_VIOLATION`，阻断所有后续任务，直至用户手动解除。

### 2.3 IMPLEMENTATION（实施阶段）

**执行人职责**：
- 只能由被批准的执行人执行
- 执行前必须再次调用 Skill Gate 确认产物合规
- 不得超出 APPROVAL 批准的影响范围
- 不得在 AI系统维护 线程中执行正式日报生产任务（反之亦然）

**Skill Gate 在 IMPLEMENTATION 阶段强制检查**：
- 实施产物（文件/代码/报告）是否通过现有质量规则
- 是否涉及未经批准的账户操作
- 文件写入路径是否在批准范围内

### 2.4 ACCEPTANCE（验收阶段）

**验收人规则**：
- 验收人必须 ≠ 执行人（生成者不能自验）
- 验收人不能是 Skill Gate 自动通过（自动检查 ≠ 人工验收）

**标准验收包必填字段**（12项，缺一不算完成验收）：

```
文件名：
文件路径：
文件大小：
最后修改时间：
状态：[PASS / PARTIAL / FAIL]
执行人：
预检人：
最终验收人：
发给谁：
下一步唯一动作：
可直接执行指令：
是否成功生成：[YES / NO]
```

### 2.5 CLOSE（关闭阶段）

**关闭条件**（全部满足才可 CLOSE）：
- 验收包已生成并归档至 `reports/validation/`
- 验收人已明确输出 PASS
- 所有产出文件已写入正确路径
- 任务状态更新为 CLOSED

**CLOSE 格式**：
```
TASK_CLOSED
任务名称：[任务名]
关闭时间：[时间戳]
验收包路径：[路径]
关闭人：[ChatGPT / 用户]
```

---

## 第三章 Skill Gate 流程违规检测

### 3.1 PROCESS_VIOLATION 触发条件

Skill Gate 在检测到以下任一情况时，必须立即输出 `PROCESS_VIOLATION` 并阻断后续任务：

| 违规类型 | 触发场景 |
|---------|---------|
| `PV-001` | 未提交 PROPOSAL 直接要求 IMPLEMENTATION |
| `PV-002` | PROPOSAL 必填字段缺失 |
| `PV-003` | 未获得 APPROVAL 直接执行任务 |
| `PV-004` | 执行人 = 验收人（自验违规） |
| `PV-005` | 执行超出 APPROVAL 批准的影响范围 |
| `PV-006` | 在 AI系统维护 线程中执行正式日报生产任务 |
| `PV-007` | 在 AI投研总控台 线程中执行无关临时测试 |
| `PV-008` | 任务未经验收即宣布 CLOSE |
| `PV-009` | 验收包缺少必填字段 |
| `PV-010` | 账户操作未经用户确认 |

### 3.2 PROCESS_VIOLATION 输出格式

```
PROCESS_VIOLATION
违规代码：[PV-XXX]
违规角色：[Claude / Codex / ChatGPT]
违规描述：[具体说明]
当前阶段：[PROPOSAL / APPROVAL / IMPLEMENTATION / ACCEPTANCE / CLOSE]
阻断效果：后续所有任务已暂停，等待用户手动解除
解除方式：用户明确输出 RESUME_AFTER_VIOLATION 并说明原因
```

### 3.3 违规后阻断范围

`PROCESS_VIOLATION` 发出后，以下操作全部暂停，直至用户手动解除：

- 日报生成
- dashboard.html 更新
- Drive 文件写入
- Direction / Risk / Execution Card 生成
- 任何新任务的 IMPLEMENTATION

---

## 第四章 角色职责边界

### 4.1 Claude

- 职责：提案设计、指令规范、长文档分析、预检（PROPOSAL + 预检）
- 禁止：直接写入 Drive（除验收包）、最终验收、自行进入 IMPLEMENTATION
- 违规触发：PV-001 / PV-003 / PV-004

### 4.2 Codex

- 职责：文件写入、脚本执行、日报生成（IMPLEMENTATION）
- 禁止：最终验收、自行发起 PROPOSAL、在无 APPROVAL 情况下执行任务
- 违规触发：PV-003 / PV-004 / PV-006 / PV-007

### 4.3 ChatGPT / AI投研总控台 V4

- 职责：APPROVAL 批准、最终验收（ACCEPTANCE + CLOSE）
- 禁止：同时作为执行人和验收人、绕过 Skill Gate 自行标绿
- 违规触发：PV-004 / PV-008

### 4.4 用户

- 职责：账户操作最终确认、治理制度变更批准、PROCESS_VIOLATION 手动解除
- 任何涉及账户资金、仓位变更的操作，用户是唯一合法确认人

---

## 第五章 执行对话线程规则

### 5.1 主线程

```
【执行对话】AI投研总控台 + 正式日报生产
```

用途：日报生产 / Dashboard / 投资分析 / 治理 / Skill / GitHub / 验收

### 5.2 维护线程

```
【执行对话】AI系统维护
```

用途：路径错误 / 脚本报错 / 文件修复 / 权限问题 / 临时维修

### 5.3 线程违规

- 在维护线程执行正式日报生产 → PV-006
- 在主线程做无关临时测试 → PV-007
- 缺少执行对话标识 → Codex 必须拒绝执行，提示补写

---

## 第六章 Skill Gate V2 升级要求

在现有 skill_gate.py（V1，已支持日报质量检查 + GitHub primary/local fallback）基础上，Codex 须新增以下检查模块：

### 新增：流程合规检查（process_gate）

```python
def process_gate(task_context: dict) -> tuple[bool, list[str]]:
    """
    检查任务是否经过合法的五阶段流程。
    task_context 字段：
      - stage: 当前阶段（proposal/approval/implementation/acceptance/close）
      - proposer: 提案人
      - approver: 批准人（approval 阶段必填）
      - executor: 执行人
      - acceptor: 验收人
      - approved: bool，是否已获批准
      - thread: 执行对话线程标识
      - affects_account: bool，是否涉及账户操作
    """
    violations = []

    if task_context.get("stage") == "implementation":
        if not task_context.get("approved"):
            violations.append("PV-003: 未获得 APPROVAL，禁止 IMPLEMENTATION")
        if task_context.get("executor") == task_context.get("acceptor"):
            violations.append("PV-004: 执行人 = 验收人，自验违规")
        thread = task_context.get("thread", "")
        if "系统维护" in thread and task_context.get("task_type") == "daily_report":
            violations.append("PV-006: 维护线程禁止执行正式日报生产")

    if task_context.get("stage") == "close":
        if not task_context.get("acceptance_package_path"):
            violations.append("PV-008: 任务未经验收，禁止 CLOSE")

    if task_context.get("affects_account") and not task_context.get("user_confirmed"):
        violations.append("PV-010: 账户操作未经用户确认")

    return len(violations) == 0, violations


def emit_process_violation(violations: list[str], role: str, stage: str):
    """输出标准 PROCESS_VIOLATION 并写入日志。"""
    print("PROCESS_VIOLATION")
    for v in violations:
        print(f"  {v}")
    print(f"违规角色：{role}")
    print(f"当前阶段：{stage}")
    print("阻断效果：后续所有任务已暂停，等待用户手动输出 RESUME_AFTER_VIOLATION 解除")
```

### 升级说明

- 现有 `skill_gate()` 函数保持不变（日报质量检查）
- 新增 `process_gate()` 函数（流程合规检查）
- 两者均须通过，日报生产才允许进行
- `emit_process_violation()` 输出标准格式，并写入 `skill_gate_failure_log.md`

---

## 第七章 制度变更规则

### 7.1 变更条件

本制度（AI_PROJECT_GOVERNANCE_V2）的任何修改，须满足：

- 用户明确书面批准
- ChatGPT 审核变更内容
- 变更记录写入 `docs/governance_change_log.md`
- 变更后的制度文件 push 到 GitHub rules/ 目录

### 7.2 禁止自行修改

任何角色（Claude / Codex / ChatGPT）均不得在未经用户批准的情况下修改本制度。
违反者：Skill Gate 输出 `PROCESS_VIOLATION PV-010`。

---

## 第八章 快速参考卡

```
┌─────────────────────────────────────────────────────────┐
│  AI_PROJECT_GOVERNANCE_V2  快速参考                      │
├─────────────────────────────────────────────────────────┤
│  五阶段：PROPOSAL → APPROVAL → IMPLEMENTATION            │
│          → ACCEPTANCE → CLOSE                            │
├─────────────────────────────────────────────────────────┤
│  铁律1：未 APPROVAL，禁止 IMPLEMENTATION                  │
│  铁律2：生成者不能自验（执行人 ≠ 验收人）                  │
│  铁律3：账户操作必须用户确认                               │
│  铁律4：验收包12字段缺一不算完成                           │
│  铁律5：PROCESS_VIOLATION 后所有任务暂停                   │
├─────────────────────────────────────────────────────────┤
│  违规解除：用户输出 RESUME_AFTER_VIOLATION + 原因          │
│  制度变更：用户书面批准 + ChatGPT审核 + GitHub push        │
└─────────────────────────────────────────────────────────┘
```

---

## 附录A：PROCESS_VIOLATION 代码速查

| 代码 | 违规场景 |
|------|---------|
| PV-001 | 未提交 PROPOSAL 直接要求 IMPLEMENTATION |
| PV-002 | PROPOSAL 必填字段缺失 |
| PV-003 | 未获得 APPROVAL 直接执行任务 |
| PV-004 | 执行人 = 验收人（自验） |
| PV-005 | 执行超出 APPROVAL 批准范围 |
| PV-006 | 维护线程执行正式日报生产 |
| PV-007 | 主线程做无关临时测试 |
| PV-008 | 未验收即宣布 CLOSE |
| PV-009 | 验收包缺少必填字段 |
| PV-010 | 账户操作未经用户确认 |

---

## 附录B：本制度与现有文件的关系

| 现有文件 | 与本制度的关系 |
|---------|--------------|
| skill_gate.py | 本制度的技术执行层；须新增 process_gate() 模块 |
| validation_workflow.rule | 本制度 ACCEPTANCE 阶段的具体规则 |
| codex_execution_thread_rule | 本制度第五章的具体实现 |
| role_separation_rules.md | 本制度第四章的具体展开 |
| user_report_quality_gate.skill | 本制度 IMPLEMENTATION 阶段的质量检查 |

本制度 > 所有上述文件。冲突时以本制度为准。
