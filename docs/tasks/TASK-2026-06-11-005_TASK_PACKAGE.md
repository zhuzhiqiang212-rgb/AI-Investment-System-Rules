# TASK PACKAGE
# TASK-2026-06-11-005

TASK_ID: TASK-2026-06-11-005
任务名称: V5_GOVERNANCE_BOOTSTRAP_FIX_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Claude（文件生成）/ Codex（写入 Drive）
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 治理类
影响范围: docs/（新建三份治理文档）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO
是否新增功能: NO
是否新增引擎: NO
是否修改业务逻辑: NO

---

## 问题根因（V5 接管预检失败）

违规1: V5 直接给 Codex 执行指令
        违反：ChatGPT 不得直接指挥 Codex
        规则来源：NEXT_TASK_INITIATOR_RULE_V1

违规2: PRECHECK_FAIL 后未稳定输出 NEXT_OWNER / NEXT_ACTION / NEXT_THREAD
        违反：TASK_CLOSED 模板必须包含三元组

违规3: V5 未读取并执行 SKILL_GUARD_RULE / THREAD_HANDOFF_RULE
        因为这两份文件根本不存在于 docs/

根本原因：三份治理基础文档未建立。
          任何新线程（V5 或其他）无法完成规则同步。

---

## 任务目标

建立三份治理基础文档，使新线程接管前能完成规则同步，
并输出标准接管自检。

不新增功能，不新增引擎，不修改业务逻辑。
只建立已有规则的独立文件形式。

---

## 交付内容

### 文件1：docs/SKILL_GUARD_RULE.md

内容规范：

# SKILL_GUARD_RULE V1.0
# Skill 守门规则

生效时间: 2026-06-11 JST
来源: AI_PROJECT_GOVERNANCE_V2 + Addendum V2-ADDENDUM-003
      codex_handoff_and_skill_role_validation_package.md

---

## 核心规则

1. Codex 不得执行未经 APPROVAL 的任务
   违反 → PROCESS_VIOLATION PV-003

2. ChatGPT 不得直接给 Codex 执行指令
   必须经过：Claude PROPOSAL → ChatGPT APPROVAL → Codex IMPLEMENTATION
   违反 → PROCESS_VIOLATION PV-003

3. Codex 不得自行最终验收
   执行人 ≠ 验收人
   违反 → PROCESS_VIOLATION PV-004

4. 任何新线程接管前必须完成 GOVERNANCE_SYNC
   未完成 GOVERNANCE_SYNC → 禁止 READY_FOR_IMPLEMENTATION

5. Skill 文件存在 ≠ Skill 已生效
   必须有 governance_runtime.py 运行时调用

---

## 新线程接管自检（必须输出）

接管前任何新线程必须输出：

  ROLE_UNDERSTOOD: YES / NO
  NO_DIRECT_CODEX_COMMAND: YES / NO
  NEXT_ACTION_REQUIRED: YES / NO
  TASK_HANDOFF_REQUIRED: YES / NO

任意项为 NO → 禁止进入总控 / 禁止审批任务 / 禁止生成 Codex 指令

---

## GOVERNANCE_SYNC_STATUS 判定

所有以下文件存在且内容完整 → GOVERNANCE_SYNC: COMPLETE
任意文件缺失 → GOVERNANCE_SYNC: INCOMPLETE → 禁止 READY_FOR_IMPLEMENTATION

必须存在的文件：
  docs/SKILL_GUARD_RULE.md（本文件）
  docs/THREAD_HANDOFF_RULE.md
  docs/SYSTEM_GOVERNANCE_MANUAL.md
  docs/AI_PROJECT_GOVERNANCE_V2.md
  docs/governance_v2_addendum_task_package_and_initiator.md

---

### 文件2：docs/THREAD_HANDOFF_RULE.md

内容规范：

# THREAD_HANDOFF_RULE V1.0
# 线程移交规则

生效时间: 2026-06-11 JST
来源: NEXT_TASK_INITIATOR_RULE_V1
      AI_PROJECT_GOVERNANCE_V2 Addendum V2-ADDENDUM-003

---

## 线程定义

主线程: 【执行对话】AI投研总控台 + 正式日报生产
  用途: 日报生产 / Dashboard / 投资分析 /
        系统治理 / Skill / GitHub / 验收

维护线程: 【执行对话】AI系统维护
  用途: 路径错误 / 脚本报错 / 文件修复 /
        权限问题 / 临时系统维修

---

## 移交规则

1. TASK_CLOSED 后必须输出三元组（不可省略）：
   NEXT_OWNER  : [角色名]
   NEXT_ACTION : [具体动作]
   NEXT_THREAD : [线程名称]

2. 新线程启动前必须完成 GOVERNANCE_SYNC
   步骤：
   a. 读取 docs/SKILL_GUARD_RULE.md
   b. 读取 docs/THREAD_HANDOFF_RULE.md（本文件）
   c. 读取 docs/SYSTEM_GOVERNANCE_MANUAL.md
   d. 输出接管自检四项（见 SKILL_GUARD_RULE.md）

3. 线程禁止事项：
   禁止在维护线程执行正式日报生产 → PV-006
   禁止在主线程做无关临时测试 → PV-007
   禁止缺少执行对话标识时执行任务

4. PRECHECK_FAIL 后必须输出：
   NEXT_OWNER  : Claude
   NEXT_ACTION : 发起修复 PROPOSAL，等待 ChatGPT 审批
   NEXT_THREAD : AI投研总控台 + 正式日报生产

---

### 文件3：docs/SYSTEM_GOVERNANCE_MANUAL.md

内容规范：

# SYSTEM_GOVERNANCE_MANUAL V1.0
# 治理手册总索引

生效时间: 2026-06-11 JST
制度层级: 参考索引（不覆盖主制度，指向主制度）

---

## 治理制度层级

最高制度:
  docs/AI_PROJECT_GOVERNANCE_V2.md

补充制度:
  docs/governance_v2_addendum_task_package_and_initiator.md
  （版本: V2-ADDENDUM-003，含四个补充规则）

守门规则:
  docs/SKILL_GUARD_RULE.md
  docs/THREAD_HANDOFF_RULE.md

批准提交标准:
  docs/approval_submission_standard_v1.md

---

## 引用完整性检查清单

以下文件必须全部存在，否则 GOVERNANCE_SYNC: INCOMPLETE：

  [ ] docs/AI_PROJECT_GOVERNANCE_V2.md
  [ ] docs/governance_v2_addendum_task_package_and_initiator.md
  [ ] docs/approval_submission_standard_v1.md
  [ ] docs/SKILL_GUARD_RULE.md
  [ ] docs/THREAD_HANDOFF_RULE.md
  [ ] docs/SYSTEM_GOVERNANCE_MANUAL.md（本文件）
  [ ] scripts/skill_gate.py
  [ ] scripts/governance_runtime.py

---

## 新线程接管 SOP

步骤1: 读取本文件（SYSTEM_GOVERNANCE_MANUAL.md）
步骤2: 读取 SKILL_GUARD_RULE.md
步骤3: 读取 THREAD_HANDOFF_RULE.md
步骤4: 输出接管自检：
  ROLE_UNDERSTOOD: YES
  NO_DIRECT_CODEX_COMMAND: YES
  NEXT_ACTION_REQUIRED: YES
  TASK_HANDOFF_REQUIRED: YES
步骤5: 任意项为 NO → 停止，输出：
  GOVERNANCE_SYNC: INCOMPLETE
  NEXT_OWNER: Claude
  NEXT_ACTION: 发起 GOVERNANCE_BOOTSTRAP 修复 PROPOSAL
  NEXT_THREAD: AI投研总控台 + 正式日报生产

---

## READY_FOR_IMPLEMENTATION 准入规则

以下条件全部满足才允许进入 READY_FOR_IMPLEMENTATION：
  1. GOVERNANCE_SYNC: COMPLETE
  2. 接管自检四项全部 YES
  3. TASK_PACKAGE 已写入 docs/tasks/
  4. ChatGPT APPROVAL 已明确输出
  5. governance_runtime.py 前置检查返回 0

任意条件不满足 → 禁止 READY_FOR_IMPLEMENTATION

---

## ACCEPTANCE_CRITERIA

1. docs/SKILL_GUARD_RULE.md 写入 docs/
2. docs/THREAD_HANDOFF_RULE.md 写入 docs/
3. docs/SYSTEM_GOVERNANCE_MANUAL.md 写入 docs/
4. SYSTEM_GOVERNANCE_MANUAL 引用链完整（8项文件列表）
5. SKILL_GUARD_RULE 含接管自检四项格式
6. THREAD_HANDOFF_RULE 含 NEXT_OWNER/ACTION/THREAD 三元组规则
7. READY_FOR_IMPLEMENTATION 准入规则完整（5条）
8. 无新增功能 / 无新增引擎 / 无业务逻辑修改
9. 验收包 12 项字段完整
10. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. 三份文件写入 docs/ ✓
2. PRECHECK 重新执行：三份文件均存在 ✓
3. GOVERNANCE_SYNC: COMPLETE ✓
4. 验收包 12 项字段完整 ✓
5. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

步骤0: governance_runtime.py 前置检查
  python scripts/governance_runtime.py \
    --task-id "TASK-2026-06-11-005" \
    --stage "implementation" \
    --approved "true" \
    --executor "Codex" \
    --acceptor "ChatGPT" \
    --thread "AI投研总控台 + 正式日报生产" \
    --task-type "governance" \
    --affects-account "false"

步骤1: 生成并写入三份文件（按上方内容规范）
  docs/SKILL_GUARD_RULE.md
  docs/THREAD_HANDOFF_RULE.md
  docs/SYSTEM_GOVERNANCE_MANUAL.md

步骤2: 生成验收包
  路径: reports/validation/task-2026-06-11-005_validation_package.md
  须含:
    section 1: governance_runtime 前置检查
    section 2: 三份文件写入确认（大小/时间）
    section 3: GOVERNANCE_SYNC 判定
    section 4: 接管自检四项确认
    section 5: READY_FOR_IMPLEMENTATION 准入规则确认
    section 6: 12项标准验收字段

---

## 禁止事项

禁止新增功能
禁止新增引擎
禁止修改业务逻辑
禁止修改 skill_gate.py / governance_runtime.py
禁止修改 dashboard.html
禁止生成日报
禁止涉及账户操作
禁止自行最终验收
