# SYSTEM_GOVERNANCE_MANUAL V1.0
# 治理手册总索引

生效时间: 2026-06-11 JST
制度层级: 参考索引（指向各主制度，不覆盖主制度）
文件路径: AI_Investment_System/docs/SYSTEM_GOVERNANCE_MANUAL.md

---

## 第一部分：治理制度层级

```
AI_PROJECT_GOVERNANCE_V2.md（最高制度）
    ↓
governance_v2_addendum_task_package_and_initiator.md（补充制度 V2-ADDENDUM-003）
    ↓
SKILL_GUARD_RULE.md（守门规则）
THREAD_HANDOFF_RULE.md（线程移交规则）
    ↓
approval_submission_standard_v1.md（审批提交标准）
```

冲突时以上层制度为准。

---

## 第二部分：引用完整性检查清单

以下文件必须全部存在，否则 GOVERNANCE_SYNC: INCOMPLETE：

| # | 文件 | 类型 | 状态 |
|---|------|------|------|
| 1 | docs/AI_PROJECT_GOVERNANCE_V2.md | 最高制度 | 须存在 |
| 2 | docs/governance_v2_addendum_task_package_and_initiator.md | 补充制度 | 须存在 |
| 3 | docs/approval_submission_standard_v1.md | 审批标准 | 须存在 |
| 4 | docs/SKILL_GUARD_RULE.md | 守门规则 | 须存在 |
| 5 | docs/THREAD_HANDOFF_RULE.md | 线程规则 | 须存在 |
| 6 | docs/SYSTEM_GOVERNANCE_MANUAL.md | 本文件 | 须存在 |
| 7 | scripts/skill_gate.py | 运行时执行 | 须存在 |
| 8 | scripts/governance_runtime.py | 强制入口 | 须存在 |

全部存在 → GOVERNANCE_SYNC: COMPLETE
任意缺失 → GOVERNANCE_SYNC: INCOMPLETE → 禁止 READY_FOR_IMPLEMENTATION

---

## 第三部分：新线程接管 SOP

任何新线程（V5 或其他）接管总控前，必须按顺序执行：

步骤1: 读取本文件（SYSTEM_GOVERNANCE_MANUAL.md）
步骤2: 读取 SKILL_GUARD_RULE.md
步骤3: 读取 THREAD_HANDOFF_RULE.md
步骤4: 逐项确认引用完整性清单（第二部分）
步骤5: 输出接管自检四项：

  ```
  ROLE_UNDERSTOOD          : YES
  NO_DIRECT_CODEX_COMMAND  : YES
  NEXT_ACTION_REQUIRED     : YES
  TASK_HANDOFF_REQUIRED    : YES
  ```

步骤6: 输出 GOVERNANCE_SYNC 状态
步骤7: 仅当全部 YES 且 GOVERNANCE_SYNC: COMPLETE 时，方可接管

---

## 第四部分：READY_FOR_IMPLEMENTATION 准入规则

以下五条全部满足才允许进入 READY_FOR_IMPLEMENTATION：

1. GOVERNANCE_SYNC: COMPLETE（8项文件全部存在）
2. 接管自检四项全部 YES
3. TASK_PACKAGE 已写入 docs/tasks/
4. ChatGPT APPROVAL 已明确输出
5. governance_runtime.py 前置检查返回 0（$LASTEXITCODE=0）

---

## 第五部分：TASK_CLOSED 标准格式

每次 TASK_CLOSED 后必须输出：

```
NEXT_OWNER  : [Claude / ChatGPT / Codex / 用户]
NEXT_ACTION : [具体动作]
NEXT_THREAD : [AI投研总控台 + 正式日报生产 / AI系统维护]
```

PRECHECK_FAIL 时标准输出：
```
NEXT_OWNER  : Claude
NEXT_ACTION : 发起修复 PROPOSAL，等待 ChatGPT 审批
NEXT_THREAD : AI投研总控台 + 正式日报生产
```

---

## 第六部分：角色职责速查

| 角色 | 职责 | 禁止 |
|------|------|------|
| Claude | PROPOSAL / 预检 / 文件设计 | 直接写入生产 / 最终验收 |
| ChatGPT | APPROVAL / 最终验收 / TASK_CLOSED | 直接指挥 Codex |
| Codex | IMPLEMENTATION / 文件写入 | 自行发起任务 / 自验 |
| 用户 | 账户操作确认 / 制度变更批准 | 不可被任何角色代替 |
