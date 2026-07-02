# TASK PACKAGE
# TASK-2026-06-10-016

TASK_ID: TASK-2026-06-10-016
任务名称: SKILL_GATE_LIVE_VIOLATION_TEST_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 实施类（实战验证）
影响范围: reports/validation/（验收包，只读写日志和验收包）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO
关联文件:
  scripts/governance_runtime.py（TASK-2026-06-10-015 REV-A）
  reports/validation/skill_gate_failure_log.md

---

## 任务目标

在真实任务流程中验证 governance_runtime.py 能自动拦截违规。

本任务是刻意构造的违规场景测试，不是生产任务。
目的：证明 Skill Gate 在真实 Codex 执行流程中（而非单元测试中）
能够自动吹哨，输出 PROCESS_VIOLATION 并阻断后续步骤。

验证问题：
  "如果 Codex 收到一个未经批准的任务，
   governance_runtime.py 是否真的会拦截它？"

---

## 执行规范

### 阶段一：故意违规执行（approved=false）

Codex 在执行本任务主体前，先运行以下命令：

```powershell
python scripts/governance_runtime.py `
  --task-id      "TASK-2026-06-10-016-VIOLATION-TEST" `
  --stage        "implementation" `
  --approved     "false" `
  --executor     "Codex" `
  --acceptor     "ChatGPT" `
  --thread       "AI投研总控台 + 正式日报生产" `
  --task-type    "governance" `
  --affects-account "false"

if ($LASTEXITCODE -ne 0) {
    Write-Host "BLOCKED: Skill Gate 自动拦截成功。"
    Write-Host "记录拦截结果，继续进入阶段二。"
    # 注意：本任务的阶段一目的就是被拦截，这是预期行为
}
```

预期结果：
- governance_runtime.py 返回 1（BLOCKED）
- 输出 PROCESS_VIOLATION + PV-003
- 输出 BLOCKED 文本
- 日志写入一条新的 PROCESS_VIOLATION 记录
- $LASTEXITCODE = 1

记录实际输出（完整截图或文本），写入验收包 section 1。

### 阶段二：合规执行（本任务实际内容）

阶段一验证完成后，使用正确参数（approved=true）
运行 governance_runtime.py，通过后执行本任务实际内容：

```powershell
python scripts/governance_runtime.py `
  --task-id      "TASK-2026-06-10-016" `
  --stage        "implementation" `
  --approved     "true" `
  --executor     "Codex" `
  --acceptor     "ChatGPT" `
  --thread       "AI投研总控台 + 正式日报生产" `
  --task-type    "governance" `
  --affects-account "false"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: 合规场景不应触发阻断，请检查参数。"
    exit 1
}
```

预期结果：
- governance_runtime.py 返回 0（PASS）
- 输出 Gate Check 通过
- $LASTEXITCODE = 0

### 阶段三：生成验收包

生成 task-2026-06-10-016_validation_package.md，写入结果。

---

## ACCEPTANCE_CRITERIA

1. 阶段一：故意违规命令（approved=false）触发 PV-003
2. 阶段一：输出包含 PROCESS_VIOLATION + BLOCKED
3. 阶段一：$LASTEXITCODE = 1
4. 阶段一：skill_gate_failure_log.md 新增一条记录
5. 阶段二：合规命令（approved=true）返回 0，正常放行
6. 阶段一和阶段二的完整命令输出已写入验收包 section 1 和 section 2
7. 验收包明确结论：Skill Gate 在真实执行流程中已证明能自动拦截
8. 验收包 12 项字段完整
9. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. 阶段一拦截成功，PV-003 触发，$LASTEXITCODE=1 ✓
2. 阶段二合规通过，$LASTEXITCODE=0 ✓
3. 日志新增一条 PROCESS_VIOLATION 记录 ✓
4. 验收包完整，含两阶段完整输出 ✓
5. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

步骤1：运行阶段一违规命令（approved=false）
  记录完整输出和 $LASTEXITCODE

步骤2：确认 skill_gate_failure_log.md 新增记录
  记录测试前后 PROCESS_VIOLATION 总数

步骤3：运行阶段二合规命令（approved=true）
  记录完整输出和 $LASTEXITCODE

步骤4：生成验收包
  路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
        task-2026-06-10-016_validation_package.md
  须含：
    section 1：阶段一完整命令输出（含 PROCESS_VIOLATION 文本）
    section 2：阶段二完整命令输出（含 Gate Check 通过文本）
    section 3：日志变化（测试前后 PROCESS_VIOLATION 总数）
    section 4：实战验证结论
      - Skill Gate 在真实执行流程中是否自动拦截：YES/NO
      - PROCESS_VIOLATION 是否在任务流程中（非单元测试）触发：YES/NO
      - 合规场景是否正常放行：YES/NO
    section 5：12项标准验收字段

---

## 禁止事项

禁止修改 skill_gate.py 或 governance_runtime.py
禁止修改 dashboard.html
禁止生成日报
禁止涉及账户操作
禁止自行最终验收
禁止在阶段一未触发 BLOCKED 时将拦截结果填写为 YES
禁止跳过阶段一直接进入阶段二
