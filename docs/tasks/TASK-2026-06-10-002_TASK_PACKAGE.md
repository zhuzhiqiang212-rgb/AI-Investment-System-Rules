# TASK PACKAGE
# TASK-2026-06-10-002

TASK_ID: TASK-2026-06-10-002
任务名称: TASK_PACKAGE_OUTPUT_STANDARD_V1 + NEXT_TASK_INITIATOR_RULE_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
提案人: ChatGPT / AI投研总控台 V4
执行人: Claude（制度文件生成）/ Codex（写入 Drive）
验收人: ChatGPT / AI投研总控台 V4
任务类型: 系统治理 / 制度文件
影响范围: docs/tasks/ / docs/ / reports/validation/
APPROVAL_REQUIRED: YES
审批状态: APPROVED（提案人 = ChatGPT，随任务给出）

---

## CODEX_EXECUTION

Codex 无需执行代码。
本任务由 Claude 生成制度文件，Codex 确认文件已写入 Drive 后输出验收包。

写入文件清单：
1. docs/tasks/TASK-2026-06-10-002_TASK_PACKAGE.md（本文件）
2. docs/governance_v2_addendum_task_package_and_initiator.md
3. reports/validation/task-2026-06-10-002_validation_package.md

---

## ACCEPTANCE_CRITERIA

1. 三份文件均已写入 Drive 正确路径
2. governance_v2_addendum 包含 TASK_PACKAGE_OUTPUT_STANDARD_V1 完整规则
3. governance_v2_addendum 包含 NEXT_TASK_INITIATOR_RULE_V1 完整规则
4. 固定流程图完整：PROPOSAL→APPROVAL→IMPLEMENTATION→PRE_ACCEPTANCE→FINAL_ACCEPTANCE→TASK_CLOSED→NEXT_PROPOSAL
5. 验收包 12 项字段完整

---

## CLOSE_CONDITION

ChatGPT 输出 TASK_CLOSED 须满足：
1. 三份文件全部写入 Drive ✓
2. Addendum 制度内容完整 ✓
3. 验收包 12 项字段完整 ✓
4. ChatGPT 明确输出 PASS ✓
