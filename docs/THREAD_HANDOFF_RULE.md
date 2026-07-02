# THREAD_HANDOFF_RULE V1.0
# 线程移交规则

生效时间: 2026-06-11 JST
制度层级: AI_PROJECT_GOVERNANCE_V2 执行规则
来源文件:
  docs/AI_PROJECT_GOVERNANCE_V2.md
  docs/governance_v2_addendum_task_package_and_initiator.md（第二部分）

---

## 第一部分：线程定义

### 主线程
标识: 【执行对话】AI投研总控台 + 正式日报生产
用途:
  - 日报生产 / Dashboard / 投资分析
  - 系统治理 / Skill / GitHub
  - 验收 / PROPOSAL / APPROVAL

### 维护线程
标识: 【执行对话】AI系统维护
用途:
  - 路径错误 / 脚本报错 / 文件修复
  - 权限问题 / 临时系统维修

### 线程禁止事项
禁止在维护线程执行正式日报生产 → PV-006
禁止在主线程做无关临时测试 → PV-007
禁止缺少执行对话标识时执行任务（Codex 必须拒绝）

---

## 第二部分：TASK_CLOSED 三元组（强制输出）

每次 TASK_CLOSED 后必须输出，不可省略：

```
NEXT_OWNER  : [角色名：Claude / ChatGPT / Codex / 用户]
NEXT_ACTION : [具体动作，一句话]
NEXT_THREAD : [线程名称]
```

PRECHECK_FAIL 后标准三元组：
```
NEXT_OWNER  : Claude
NEXT_ACTION : 发起修复 PROPOSAL，等待 ChatGPT 审批
NEXT_THREAD : AI投研总控台 + 正式日报生产
```

违反（未输出三元组）：
  PRE_ACCEPTANCE = INCOMPLETE → 任务不得进入 FINAL_ACCEPTANCE

---

## 第三部分：新线程移交 SOP

新线程（V5 或其他）接管总控前，必须按顺序完成：

步骤1: 读取 docs/SYSTEM_GOVERNANCE_MANUAL.md
步骤2: 读取 docs/SKILL_GUARD_RULE.md
步骤3: 读取本文件（docs/THREAD_HANDOFF_RULE.md）
步骤4: 输出接管自检四项
步骤5: 确认 GOVERNANCE_SYNC: COMPLETE
步骤6: 方可进入总控

任意步骤未完成 → 禁止接管 / 禁止审批 / 禁止生成 Codex 指令

---

## 第四部分：六阶段完整流程（含线程标识）

```
PROPOSAL（Claude 发起，主线程）
    ↓
APPROVAL（ChatGPT 审批，主线程）
    ↓
IMPLEMENTATION（Codex 执行，主线程或维护线程，按任务类型）
    ↓
PRE_ACCEPTANCE（Claude 预检，含 NEXT 三元组，主线程）
    ↓
FINAL_ACCEPTANCE（ChatGPT 验收，主线程）
    ↓
TASK_CLOSED（输出 NEXT_OWNER / NEXT_ACTION / NEXT_THREAD）
    ↓
NEXT_PROPOSAL（Claude 发起，循环）
```

---

## 第五部分：READY_FOR_IMPLEMENTATION 准入规则

以下五条全部满足才允许进入：

1. GOVERNANCE_SYNC: COMPLETE
2. 接管自检四项全部 YES
3. TASK_PACKAGE 已写入 docs/tasks/
4. ChatGPT APPROVAL 已明确输出
5. governance_runtime.py 前置检查返回 0

任意条件不满足 → 禁止 READY_FOR_IMPLEMENTATION
