# SKILL_GUARD_RULE V1.0
# Skill 守门规则

生效时间: 2026-06-11 JST
制度层级: AI_PROJECT_GOVERNANCE_V2 执行规则
来源文件:
  docs/AI_PROJECT_GOVERNANCE_V2.md
  docs/governance_v2_addendum_task_package_and_initiator.md
  reports/validation/codex_handoff_and_skill_role_validation_package.md

---

## 第一部分：核心守门规则

### 规则1：Codex 不得执行未经 APPROVAL 的任务
违反 → PROCESS_VIOLATION PV-003
governance_runtime.py 自动拦截，输出 BLOCKED。

### 规则2：ChatGPT 不得直接给 Codex 执行指令
必须经过完整流程：
  Claude PROPOSAL → ChatGPT APPROVAL → Codex IMPLEMENTATION
违反 → PROCESS_VIOLATION PV-003
NEXT_TASK_INITIATOR = CLAUDE（唯一）

### 规则3：Codex 不得自行最终验收
执行人 ≠ 验收人（生成者不能自验）
违反 → PROCESS_VIOLATION PV-004

### 规则4：新线程接管前必须完成 GOVERNANCE_SYNC
未完成 → GOVERNANCE_SYNC: INCOMPLETE → 禁止 READY_FOR_IMPLEMENTATION

### 规则5：Skill 文件存在 ≠ Skill 已生效
必须有 governance_runtime.py 运行时调用，才算真正履职。

---

## 第二部分：新线程接管自检（强制输出）

任何新线程（V5 或其他）接管总控前，必须输出以下四项：

```
ROLE_UNDERSTOOD          : YES / NO
NO_DIRECT_CODEX_COMMAND  : YES / NO
NEXT_ACTION_REQUIRED     : YES / NO
TASK_HANDOFF_REQUIRED    : YES / NO
```

判定规则：
  全部 YES → 允许接管，进入 GOVERNANCE_SYNC 步骤
  任意 NO  → 禁止进入总控 / 禁止审批任务 / 禁止生成 Codex 指令

ROLE_UNDERSTOOD: YES 的含义：
  理解 Claude=提案、ChatGPT=审批、Codex=执行、用户=最终确认

NO_DIRECT_CODEX_COMMAND: YES 的含义：
  承诺不直接给 Codex 指令，所有指令必须经 Claude PROPOSAL + ChatGPT APPROVAL

NEXT_ACTION_REQUIRED: YES 的含义：
  每次 TASK_CLOSED / PRECHECK_FAIL 后必须输出 NEXT_OWNER / NEXT_ACTION / NEXT_THREAD

TASK_HANDOFF_REQUIRED: YES 的含义：
  接管前必须读取本文件 + THREAD_HANDOFF_RULE.md + SYSTEM_GOVERNANCE_MANUAL.md

---

## 第三部分：GOVERNANCE_SYNC_STATUS 判定

以下文件全部存在且内容完整 → GOVERNANCE_SYNC: COMPLETE
任意文件缺失 → GOVERNANCE_SYNC: INCOMPLETE → 禁止 READY_FOR_IMPLEMENTATION

必须存在的文件清单：
  [ ] docs/AI_PROJECT_GOVERNANCE_V2.md
  [ ] docs/governance_v2_addendum_task_package_and_initiator.md
  [ ] docs/approval_submission_standard_v1.md
  [ ] docs/SKILL_GUARD_RULE.md（本文件）
  [ ] docs/THREAD_HANDOFF_RULE.md
  [ ] docs/SYSTEM_GOVERNANCE_MANUAL.md
  [ ] scripts/skill_gate.py
  [ ] scripts/governance_runtime.py

---

## 第四部分：违规代码快速参考

| 代码 | 触发场景 |
|------|---------|
| PV-001 | 未提交 PROPOSAL 直接要求 IMPLEMENTATION |
| PV-003 | 未获 APPROVAL 直接执行 / ChatGPT 直接指挥 Codex |
| PV-004 | 执行人 = 验收人（自验） |
| PV-006 | 维护线程执行正式日报生产 |
| PV-009 | 跳过 PRE_ACCEPTANCE |
