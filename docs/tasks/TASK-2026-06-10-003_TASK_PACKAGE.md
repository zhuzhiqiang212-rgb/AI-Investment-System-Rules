# TASK PACKAGE
# TASK-2026-06-10-003

TASK_ID: TASK-2026-06-10-003
任务名称: ADDENDUM_SYNC_TO_GITHUB_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V4
任务类型: 系统治理 / GitHub 同步
影响范围: GitHub rules/ 目录 / 本地 Git 仓库
APPROVAL_REQUIRED: YES
审批状态: APPROVED（ChatGPT，2026-06-10）
是否涉及账户操作: NO
是否涉及规则变更: YES（将 V2-ADDENDUM-002 同步为 GitHub 规则源）

---

## CODEX_EXECUTION

见正文执行包（本文件下方）。
Codex 依据本文件执行，不依据聊天文本。

---

## ACCEPTANCE_CRITERIA

1. governance_v2_addendum_task_package_and_initiator.md 已复制到本地 Git rules/ 目录
2. AI_PROJECT_GOVERNANCE_V2.md 已复制到本地 Git rules/ 目录
3. git add + git commit 已执行，commit hash 已记录
4. git push 已执行（若 remote 已设置）或输出 PUSH_PENDING（若 remote 尚未设置）
5. 验收包 12 项字段完整
6. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

以下全部满足，ChatGPT 方可输出 TASK_CLOSED：
1. 两份制度文件已复制到本地 Git rules/ 目录 ✓
2. git commit 已完成，hash 已记录 ✓
3. git push 已执行 或 PUSH_PENDING 已说明原因 ✓
4. 验收包 12 项字段完整 ✓
5. ChatGPT 输出 PASS ✓
