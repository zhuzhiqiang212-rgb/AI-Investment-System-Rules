# TASK PACKAGE
# TASK-2026-06-10-005

TASK_ID: TASK-2026-06-10-005
任务名称: BUY_TRIGGER_ENGINE_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Claude（策略设计）/ Codex（写入 Drive）
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 策略类
影响范围: docs/buy_trigger_engine_v1.md（新建）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO

---

## 任务目标

为四账户（美股IBKR / 日股SBI / A股富途 / 加密BF）
设计统一的买入触发器框架。

解决当前最大决策黑洞：
日报有结论，但没有"今天什么条件触发买入"。

---

## 交付内容

1. buy_trigger_engine_v1.md
   包含：
   - 触发器设计原则（条件句结构）
   - 四账户各自的触发条件模板
   - 触发器与日报 Delta 卡的衔接格式
   - 触发器失效条件（与止损联动）
   - 示例：3个真实标的触发器写法

2. 触发器格式规范（可直接写入日报第一屏）

---

## ACCEPTANCE_CRITERIA

1. buy_trigger_engine_v1.md 已写入 docs/
2. 四账户各有独立触发条件模板
3. 每个触发器包含：触发条件 / 仓位上限 / 失效条件 三要素
4. 示例覆盖美股 / 日股 / 加密至少各一个
5. 格式可直接嵌入日报 V2 第一屏
6. 验收包 12 项字段完整
7. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. buy_trigger_engine_v1.md 已写入 Drive docs/ ✓
2. 四账户模板完整 ✓
3. 示例完整 ✓
4. 验收包 12 项字段完整 ✓
5. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

本任务 Claude 完成策略设计后，Codex 执行：
将 Claude 输出的 buy_trigger_engine_v1.md 内容
写入 Drive：
  路径：G:\我的云端硬盘\AI_Investment_System\docs\buy_trigger_engine_v1.md
确认文件大小和修改时间，写入验收包。
