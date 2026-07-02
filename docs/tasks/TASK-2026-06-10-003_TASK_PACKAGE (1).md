# TASK PACKAGE
# TASK-2026-06-10-003 · REV-B（合规版）

TASK_ID: TASK-2026-06-10-003
任务名称: ADDENDUM_SYNC_TO_GITHUB_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护（禁止在此对话执行本任务）
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 系统治理 / GitHub 同步
影响范围: rules/（本地 Git）/ GitHub remote（若已设置）
APPROVAL_REQUIRED: YES
审批状态: APPROVED（ChatGPT，2026-06-10）
是否涉及账户操作: NO
是否涉及规则变更: YES

---

## CODEX_EXECUTION

步骤1：确认本地 Git 状态
  cd "G:\我的云端硬盘\AI_Investment_System"
  git status
  git log --oneline -3
  git remote -v
  记录：branch / 最近3条hash / remote状态

步骤2：复制两份制度文件到 rules/
  源1：docs\governance_v2_addendum_task_package_and_initiator.md
  目标1：rules\governance_v2_addendum_task_package_and_initiator.md

  源2：docs\AI_PROJECT_GOVERNANCE_V2.md
  目标2：rules\AI_PROJECT_GOVERNANCE_V2.md

  PowerShell：
    $root = "G:\我的云端硬盘\AI_Investment_System"
    Copy-Item "$root\docs\governance_v2_addendum_task_package_and_initiator.md" "$root\rules\" -Force
    Copy-Item "$root\docs\AI_PROJECT_GOVERNANCE_V2.md" "$root\rules\" -Force
    Get-Item "$root\rules\governance_v2_addendum_task_package_and_initiator.md" | Select-Object Name, Length, LastWriteTime
    Get-Item "$root\rules\AI_PROJECT_GOVERNANCE_V2.md" | Select-Object Name, Length, LastWriteTime

步骤3：git add + git commit
  git add rules/governance_v2_addendum_task_package_and_initiator.md
  git add rules/AI_PROJECT_GOVERNANCE_V2.md
  git commit -m "feat(rules): sync governance V2 + addendum V2-ADDENDUM-002 [TASK-2026-06-10-003]"
  git log --oneline -1
  记录：新 commit hash（完整40位）

步骤4：git push（条件执行）
  若 remote 已设置：git push origin main → 记录输出 → PUSH_STATUS: PUSH_DONE
  若 remote 未设置：不执行 → PUSH_STATUS: PUSH_PENDING（记录原因）

步骤5：生成验收包
  文件名：task-2026-06-10-003_validation_package.md
  写入路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
  必须包含：Git状态 / 文件复制结果 / commit hash / push状态 / 12项验收字段

---

## ACCEPTANCE_CRITERIA

1. governance_v2_addendum_task_package_and_initiator.md 已进入 rules/
2. AI_PROJECT_GOVERNANCE_V2.md 已进入 rules/
3. git commit 已完成，hash 已记录
4. PUSH_STATUS 已明确（PUSH_DONE 或 PUSH_PENDING + 原因）
5. 验收包 12 项字段完整
6. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

以下全部满足，ChatGPT 方可输出 TASK_CLOSED：
1. 两份制度文件已复制到 rules/ ✓
2. git commit 已完成，hash 已记录 ✓
3. PUSH_STATUS 已明确 ✓
4. 验收包 12 项字段完整 ✓
5. ChatGPT 输出 PASS ✓

---

## 禁止事项

禁止修改 skill_gate.py 任何现有函数
禁止修改 dashboard.html
禁止生成日报
禁止涉及账户操作
禁止删除 rules/ 现有文件
禁止自行验收（验收包最终验收人不得填写 Codex）
禁止在 commit 中包含 reports/ 目录内容
禁止 push 未完成时将 PUSH_STATUS 填写为 PUSH_DONE
禁止在【维护对话】AI系统维护中执行本任务
