# TASK PACKAGE
# TASK-2026-06-10-005 REV-A

TASK_ID: TASK-2026-06-10-005 REV-A
任务名称: BUY_TRIGGER_ENGINE_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Claude（策略设计）/ Codex（写入 Drive）
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 策略类
影响范围: docs/buy_trigger_engine_v1.md（新建）
APPROVAL_REQUIRED: YES
审批状态: APPROVED WITH CHANGES（ChatGPT，2026-06-10）
旧版本状态: 自动作废
是否涉及账户操作: NO
是否涉及规则变更: NO

---

## 审批变更项（已合并）

1. 增加"不买入条件"（每个账户触发器必须包含）
2. 增加"A/B/C 信号等级"（触发器三段分级）
3. 增加"A股真实示例"（示例须覆盖美股/日股/A股/加密各一个）

---

## 交付内容

buy_trigger_engine_v1.md 必须包含：

1. 触发器设计原则
2. A/B/C 信号等级定义
3. 四账户各自触发条件模板
   每个模板必须包含：
   - 买入触发条件
   - 不买入条件
   - 仓位上限
   - 失效条件
4. 触发器与日报 Delta 卡衔接格式
5. 真实示例四个：美股/日股/A股/加密各一个

---

## ACCEPTANCE_CRITERIA

1. buy_trigger_engine_v1.md 已写入 docs/
2. A/B/C 信号等级有明确定义
3. 四账户各有独立模板，含买入触发/不买入/仓位上限/失效条件
4. 示例覆盖美股/日股/A股/加密各一个
5. 格式可直接嵌入日报 V2 第一屏
6. 验收包 12 项字段完整
7. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. buy_trigger_engine_v1.md 已写入 Drive docs/ ✓
2. A/B/C 信号等级完整 ✓
3. 不买入条件在四账户模板中均存在 ✓
4. 示例四个均完整 ✓
5. 验收包 12 项字段完整 ✓
6. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

Claude 完成策略设计后，Codex 执行：
将 Claude 输出的 buy_trigger_engine_v1.md 内容
写入 Drive：
  路径：G:\我的云端硬盘\AI_Investment_System\docs\buy_trigger_engine_v1.md
确认文件大小和修改时间，写入验收包。
验收包写入路径：
  G:\我的云端硬盘\AI_Investment_System\reports\validation\task-2026-06-10-005_validation_package.md
