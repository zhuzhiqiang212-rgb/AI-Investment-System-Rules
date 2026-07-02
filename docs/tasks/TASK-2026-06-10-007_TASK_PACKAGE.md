# TASK PACKAGE
# TASK-2026-06-10-007

TASK_ID: TASK-2026-06-10-007
任务名称: TAKE_PROFIT_SYSTEM_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Claude（策略设计）/ Codex（写入 Drive）
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 策略类
影响范围: docs/take_profit_system_v1.md（新建）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO
关联文件:
  docs/buy_trigger_engine_v1.md（TASK-2026-06-10-005）
  docs/position_sizing_engine_v1.md（TASK-2026-06-10-006）

---

## 任务目标

为四账户设计止盈目标系统，解决当前缺口：
日报有买入触发和仓位计算，但没有"涨到哪里该卖"。

与已完成模块的联动：
  买入触发器 → 进场条件
  仓位计算   → 进场规模
  止盈系统   → 出场目标（本任务）
  三者合并构成完整的单笔交易决策闭环。

---

## 交付内容

take_profit_system_v1.md 必须包含：

1. 止盈设计原则
   - 止盈与 A/B/C 信号等级的联动
   - 分批止盈 vs 一次性止盈的适用场景
   - 止盈目标与 40% 年化目标的关系
   - 禁止事项（禁止追涨移动止盈上限等）
   - 用户人工确认边界（系统只输出建议，不自动下单）

2. 四账户各自止盈模板
   每个模板必须包含：
   - 第一止盈目标（部分兑现）
   - 第二止盈目标（主仓兑现）
   - 尾仓处理规则（剩余仓位如何处理）
   - 移动止盈规则（何时上移止损保护浮盈）
   - 强制止盈条件（即使未到目标价也必须卖出的情形）
   - 与止损/失效条件的联动

3. 与买入触发器和仓位引擎的衔接格式
   三模块联动：进场条件 → 进场规模 → 出场目标

4. 真实示例四个：美股/日股/A股/加密各一个
   每个示例须展示：买入价、第一止盈、第二止盈、
   尾仓处理、移动止盈触发点的完整计算

5. 日报 V2 第一屏止盈字段格式

---

## ACCEPTANCE_CRITERIA

1. take_profit_system_v1.md 已写入 docs/
2. 分批止盈结构（第一/第二/尾仓）在四账户模板中均定义
3. 移动止盈规则在四账户模板中均定义
4. 强制止盈条件在四账户模板中均定义
5. 与 A/B/C 信号等级联动规则明确
6. 用户人工确认边界明确声明
7. 示例覆盖美股/日股/A股/加密各一个，含完整计算
8. 三模块衔接格式已定义
9. 验收包 12 项字段完整
10. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. take_profit_system_v1.md 已写入 Drive docs/ ✓
2. 四账户模板完整，六要素齐备 ✓
3. 三模块衔接格式已定义 ✓
4. 四个示例完整 ✓
5. 验收包 12 项字段完整 ✓
6. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

Claude 完成策略设计后，Codex 执行：
将 Claude 输出的 take_profit_system_v1.md 内容
写入 Drive：
  路径：G:\我的云端硬盘\AI_Investment_System\docs\take_profit_system_v1.md
确认文件大小和修改时间，写入验收包：
  路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
        task-2026-06-10-007_validation_package.md
