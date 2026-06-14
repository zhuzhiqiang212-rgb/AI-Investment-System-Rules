# 03_TASK_STANDARD
# 任务包/验收/线程交接标准 V6

版本: V6.0
生效时间: 2026-06-14 JST

---

## 一、任务包标准格式

每个任务包必须包含以下字段：

```
TASK_ID: TASK-YYYY-MM-DD-XXX
任务名称: [任务名]
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V6（≠ 执行人）
任务类型: [策略类/实施类/验证类/治理类]
影响范围: [具体文件]
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO
```

---

## 二、六阶段流程（强制执行）

```
PROPOSAL（Claude发起）
    ↓
APPROVAL（ChatGPT V6审批）
    ↓
IMPLEMENTATION（Codex执行）
    ↓
PRE_ACCEPTANCE（Claude预检）
    ↓
FINAL_ACCEPTANCE（ChatGPT V6验收）
    ↓
TASK_CLOSED（输出三元组）
```

禁止跳过任何阶段。
禁止同一角色同时担任执行人和验收人。

---

## 三、READY_FOR_IMPLEMENTATION 准入规则

以下五条全部满足才允许进入：
1. GOVERNANCE_SYNC: COMPLETE（8项文件全部存在）
2. 接管自检四项全部YES
3. TASK_PACKAGE已写入docs/tasks/
4. ChatGPT V6 APPROVAL已明确输出
5. governance_runtime.py前置检查返回0

---

## 四、验收标准

### 技术验收（Codex完成后）
- 文件已写入正确路径
- 文件大小合理
- 修改时间为当日

### 质量验收（ChatGPT V6）
- 验收以决策价值为核心，不以文件数量为核心
- 以下理由不得通过验收：
  - "文件已生成"
  - "脚本运行成功"
  - "没有报错"

---

## 五、TASK_CLOSED三元组（强制输出）

每次TASK_CLOSED后必须输出，不可省略：

```
NEXT_OWNER  : [Claude/ChatGPT/Codex/用户]
NEXT_ACTION : [具体动作，一句话]
NEXT_THREAD : [AI投研总控台 + 正式日报生产]
```

PRECHECK_FAIL时标准三元组：
```
NEXT_OWNER  : Claude
NEXT_ACTION : 发起修复PROPOSAL，等待ChatGPT V6审批
NEXT_THREAD : AI投研总控台 + 正式日报生产
```

---

## 六、新线程接管自检

任何新线程接管前必须输出：
```
ROLE_UNDERSTOOD          : YES
NO_DIRECT_CODEX_COMMAND  : YES
NEXT_ACTION_REQUIRED     : YES
TASK_HANDOFF_REQUIRED    : YES
```

任意项为NO → 禁止接管/禁止审批/禁止生成Codex指令

---

## 七、角色职责边界

| 角色 | 职责 | 禁止 |
|------|------|------|
| Claude | PROPOSAL/预检/设计 | 直接写入生产/最终验收 |
| ChatGPT V6 | APPROVAL/最终验收 | 直接指挥Codex |
| Codex | IMPLEMENTATION/写入 | 自行发起/自验 |
| 用户 | 账户操作/制度批准 | 不可被代替 |

---

## 八、线程定义

主线程: 【执行对话】AI投研总控台 + 正式日报生产
  用途: 日报/分析/治理/验收/Skill

维护线程: 【执行对话】AI系统维护
  用途: 路径错误/脚本修复/临时维修

禁止在维护线程执行正式日报生产 → PV-006
