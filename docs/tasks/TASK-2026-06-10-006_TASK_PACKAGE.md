# TASK PACKAGE
# TASK-2026-06-10-006

TASK_ID: TASK-2026-06-10-006
任务名称: POSITION_SIZING_ENGINE_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Claude（策略设计）/ Codex（写入 Drive）
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 策略类
影响范围: docs/position_sizing_engine_v1.md（新建）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO

---

## 任务目标

为四账户设计仓位大小计算框架。

解决当前缺口：
买入触发器（TASK-2026-06-10-005）已完成"何时买"，
本任务解决"买多少"——基于信号等级、账户规模、
当前回撤、波动率，计算每次买入的具体仓位大小。

---

## 交付内容

position_sizing_engine_v1.md 必须包含：

1. 仓位计算设计原则
   - 与 A/B/C 信号等级的联动规则
   - 账户回撤对仓位的动态压缩规则
   - 总仓位上限控制

2. 四账户各自仓位计算模板
   每个模板必须包含：
   - 基础仓位公式（基于信号等级）
   - 回撤压缩系数（账户亏损时自动缩仓）
   - 波动率调整（高波动标的自动减仓）
   - 单标的集中度上限
   - 加仓规则（何时允许加仓，加多少）

3. 与买入触发器的衔接格式
   触发器输出信号等级 → 仓位引擎输出具体仓位百分比

4. 真实示例四个：美股/日股/A股/加密各一个
   每个示例须展示完整计算过程

5. 日报 V2 第一屏仓位字段格式

---

## ACCEPTANCE_CRITERIA

1. position_sizing_engine_v1.md 已写入 docs/
2. 四账户各有独立仓位计算模板
3. 每个模板含：基础仓位/回撤压缩/波动率调整/集中度上限/加仓规则
4. 与 A/B/C 信号等级联动规则明确
5. 示例覆盖美股/日股/A股/加密各一个，含完整计算过程
6. 日报 V2 第一屏仓位字段格式已定义
7. 验收包 12 项字段完整
8. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. position_sizing_engine_v1.md 已写入 Drive docs/ ✓
2. 四账户模板完整，五要素齐备 ✓
3. 信号等级联动规则明确 ✓
4. 四个示例完整 ✓
5. 验收包 12 项字段完整 ✓
6. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

Claude 完成策略设计后，Codex 执行：
将 Claude 输出的 position_sizing_engine_v1.md 内容
写入 Drive：
  路径：G:\我的云端硬盘\AI_Investment_System\docs\position_sizing_engine_v1.md
确认文件大小和修改时间，写入验收包：
  路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
        task-2026-06-10-006_validation_package.md
