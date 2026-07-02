# TASK PACKAGE
# TASK-2026-06-10-015

TASK_ID: TASK-2026-06-10-015
任务名称: SKILL_GATE_RUNTIME_INTEGRATION_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 实施类（代码）
影响范围: scripts/skill_gate.py（已有，新增调用层）
          scripts/governance_runtime.py（新建）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO
关联文件:
  scripts/skill_gate.py（现有，含 process_gate + emit_process_violation）
  docs/AI_PROJECT_GOVERNANCE_V2.md
  docs/governance_v2_addendum_task_package_and_initiator.md

---

## 任务目标

让 Skill Gate 从规则文档升级为真正的执行守门人。

当前问题：
  process_gate() 和 emit_process_violation() 函数存在于
  skill_gate.py 中，但没有任何地方调用它们。
  Claude / Codex / ChatGPT 违规时，没有任何机制自动吹哨。

本任务目标：
  1. 证明 PROCESS_VIOLATION 能够自动拦截违规
  2. 证明三个角色任一违规时，Skill Gate 会自动吹哨
  3. 建立每次任务执行前的 Gate Check 标准流程

---

## 交付内容

### 文件1：scripts/governance_runtime.py（新建）

Skill Gate 运行时调用层。
在每次 Codex 执行任务前，必须先调用本模块的
run_governance_check()，通过后方可继续执行。

必须包含：

1. run_governance_check(task_context: dict) -> bool
   调用 process_gate()，若 FAIL 则：
   - 调用 emit_process_violation() 输出标准违规记录
   - 写入失败日志
   - 返回 False，阻断后续所有任务
   - 输出明确的 BLOCKED 状态

2. validate_task_package(task_package_path: str) -> bool
   验证 TASK_PACKAGE.md 的13个必填字段是否完整：
   - 读取 Drive 中的 TASK_PACKAGE 文件
   - 检查每个必填字段是否存在且非空
   - 缺失字段触发 PV-002

3. check_thread_compliance(thread: str, task_type: str) -> bool
   验证执行对话线程是否合规：
   - 维护线程执行正式任务 → PV-006
   - 主线程执行临时测试 → PV-007
   - 缺少执行对话标识 → 拒绝执行

4. check_approver_executor_split(approver: str, executor: str) -> bool
   验证审批人与执行人是否分离：
   - 同一角色同时审批和执行 → PV-004

5. 标准调用模板（Codex 每次任务开始前复制使用）：
   ```python
   from governance_runtime import run_governance_check

   task_context = {
       "stage": "implementation",
       "approved": True,
       "executor": "Codex",
       "acceptor": "ChatGPT",
       "thread": "AI投研总控台 + 正式日报生产",
       "task_type": "governance",
       "affects_account": False,
       "user_confirmed": False,
       "acceptance_package_path": "",
       "task_id": "TASK-XXXX-XX-XX-XXX",
   }

   if not run_governance_check(task_context):
       print("BLOCKED: Skill Gate 未通过，任务中止。")
       exit(1)

   # 通过后继续执行任务
   ```

### 文件2：三项自动拦截测试（写入验收包）

测试必须证明三个角色违规时 Skill Gate 均能自动吹哨：

测试1：Codex 违规——未获 APPROVAL 直接执行（PV-003）
  task_context["approved"] = False
  预期：run_governance_check() 返回 False
        emit_process_violation() 被调用
        日志中出现 PROCESS_VIOLATION + PV-003
        输出 BLOCKED

测试2：Claude 违规——执行人 = 验收人（PV-004，自验）
  task_context["executor"] = "Claude"
  task_context["acceptor"] = "Claude"
  预期：run_governance_check() 返回 False
        日志中出现 PROCESS_VIOLATION + PV-004
        输出 BLOCKED

测试3：ChatGPT 违规——在维护线程执行正式日报生产（PV-006）
  task_context["thread"] = "AI系统维护"
  task_context["task_type"] = "daily_report"
  预期：run_governance_check() 返回 False
        日志中出现 PROCESS_VIOLATION + PV-006
        输出 BLOCKED

测试4（合规基准）：标准合规场景
  approved=True / executor≠acceptor / 正确线程
  预期：run_governance_check() 返回 True
        无 PROCESS_VIOLATION 输出
        任务继续执行

---

## ACCEPTANCE_CRITERIA

1. governance_runtime.py 已写入 scripts/
2. run_governance_check() 函数存在且可调用
3. 测试1：PV-003 自动触发，日志中出现 PROCESS_VIOLATION + PV-003
4. 测试2：PV-004 自动触发，日志中出现 PROCESS_VIOLATION + PV-004
5. 测试3：PV-006 自动触发，日志中出现 PROCESS_VIOLATION + PV-006
6. 测试4：合规场景返回 True，无违规输出
7. 所有四项测试的 assert 全部通过
8. 失败日志 skill_gate_failure_log.md 有三条新的 PROCESS_VIOLATION 记录
9. 标准调用模板已在 governance_runtime.py 中注释说明
10. 验收包 12 项字段完整
11. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. governance_runtime.py 已写入 scripts/ ✓
2. 四项测试全部 assert 通过 ✓
3. 三条 PROCESS_VIOLATION 日志记录存在 ✓
4. 验收包 12 项字段完整 ✓
5. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

步骤1：确认 skill_gate.py 中 process_gate() 和
       emit_process_violation() 函数已存在
       路径：G:\我的云端硬盘\AI_Investment_System\scripts\skill_gate.py

步骤2：生成 governance_runtime.py
       写入：G:\我的云端硬盘\AI_Investment_System\scripts\governance_runtime.py
       必须包含上方定义的5个函数和标准调用模板

步骤3：运行四项测试
       记录每项测试的实际输出和 assert 结果

步骤4：读取 skill_gate_failure_log.md
       确认三条新 PROCESS_VIOLATION 记录已写入

步骤5：生成验收包
       路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
             task-2026-06-10-015_validation_package.md
       必须包含：
         section 1：governance_runtime.py 写入确认（大小/时间）
         section 2：四项测试实际输出和 assert 结果
         section 3：日志中 PROCESS_VIOLATION 出现次数确认
         section 4：12项验收字段

---

## 禁止事项

禁止修改 skill_gate.py 现有函数
禁止修改 dashboard.html
禁止生成日报
禁止涉及账户操作
禁止自行最终验收
禁止在任意 assert 失败时填写状态 PASS
禁止在测试未全部通过时宣布 Skill Gate 已接入
