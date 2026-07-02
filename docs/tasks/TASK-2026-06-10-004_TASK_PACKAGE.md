# TASK PACKAGE
# TASK-2026-06-10-004

TASK_ID: TASK-2026-06-10-004
任务名称: APPROVAL_SUBMISSION_STANDARD_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: ChatGPT / AI投研总控台 V4
执行人: Claude（制度文件生成）
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 系统治理 / 制度文件
影响范围: docs/approval_submission_standard_v1.md / docs/governance_v2_addendum_task_package_and_initiator.md（更新）
APPROVAL_REQUIRED: YES
审批状态: APPROVED（ChatGPT，随任务给出）
是否涉及账户操作: NO
是否涉及规则变更: YES

---

## CODEX_EXECUTION

本任务无需 Codex 执行代码。
Claude 生成制度文件，直接写入 Drive。

---

## ACCEPTANCE_CRITERIA

1. approval_submission_standard_v1.md 已写入 docs/
2. governance_v2_addendum 已更新，包含第四部分 APPROVAL_SUBMISSION_STANDARD_V1
3. 验收包 12 项字段完整
4. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. 两份文件全部写入 Drive ✓
2. Addendum 版本升级为 V2-ADDENDUM-003 ✓
3. 验收包 12 项字段完整 ✓
4. ChatGPT 输出 PASS ✓
