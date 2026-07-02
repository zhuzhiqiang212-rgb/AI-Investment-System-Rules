# TASK PACKAGE
# TASK-2026-06-10-009

TASK_ID: TASK-2026-06-10-009
任务名称: ASSET_ALLOCATION_ENGINE_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Claude（策略设计）/ Codex（写入 Drive）
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 策略类
影响范围: docs/asset_allocation_engine_v1.md（新建）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO
关联文件:
  docs/buy_trigger_engine_v1.md（TASK-2026-06-10-005）
  docs/position_sizing_engine_v1.md（TASK-2026-06-10-006）
  docs/take_profit_system_v1.md（TASK-2026-06-10-007）
  docs/cycle_positioning_engine_v1.md（TASK-2026-06-10-008）

---

## 任务目标

为四账户设计资产配置引擎，解决当前缺口：
周期定位引擎输出了"现在处于什么周期"，
但没有规则告诉用户"该把多少钱放在哪里"。

与已完成模块的联动：
  周期定位引擎 → 输出周期阶段 + 置信度
      ↓
  资产配置引擎 → 输出四账户资金比例建议
      ↓
  买入触发器   → 在配置比例内寻找进场机会
  仓位计算     → 在配置比例内计算单笔规模
  止盈系统     → 出场后资金回归配置比例

五模块合并构成完整的"定位→配置→进场→规模→出场"体系。

---

## 交付内容

asset_allocation_engine_v1.md 必须包含：

1. 资产配置设计原则
   - 配置目标：服务于年化 40%+ 的最高目标
   - 配置调整触发条件（何时重新配置）
   - 与周期定位引擎的联动规则
   - 配置置信度与周期置信度的传导关系
   - 禁止事项（禁止频繁再平衡等）
   - 用户人工确认边界

2. 六个周期状态下的基准配置矩阵
   对应周期定位引擎的六个状态：
   BULL_EARLY / BULL_MID / BULL_LATE /
   BEAR / TRANSITION / UNKNOWN
   每个状态须定义四账户的建议配置比例区间：
   - 美股（IBKR）建议比例
   - 日股（SBI）建议比例
   - A股（富途）建议比例
   - 加密（BF）建议比例
   - 现金/避险资产建议比例
   - 再平衡触发条件

3. 动态调整规则
   - 子周期与总周期冲突时的配置调整
   - 置信度降级时的配置收缩规则
   - 单账户触及最大回撤时的跨账户调配规则
   - 年化目标进度对配置的影响
     （落后目标时是否允许提高风险资产比例）

4. 配置再平衡规则
   - 何时触发再平衡（漂移阈值）
   - 再平衡执行步骤
   - 再平衡优先级（先减谁，后加谁）
   - 税务与摩擦成本提示

5. 与四个已完成模块的衔接格式
   周期标签 → 配置矩阵查表 → 输出四账户比例建议
   → 各账户在比例内独立执行触发器/仓位/止盈

6. 真实示例两个
   当前市场配置建议（BULL_MID + B级置信度）
   以及 TRANSITION 状态下的保守配置
   每个示例须展示完整的查表和计算过程

7. 日报 V2 配置状态字段格式
   须同时显示：
   - 当前周期标签（来自周期引擎）
   - 四账户当前实际比例
   - 四账户建议目标比例
   - 偏离程度（是否需要再平衡）

---

## ACCEPTANCE_CRITERIA

1. asset_allocation_engine_v1.md 已写入 docs/
2. 六个周期状态下的基准配置矩阵完整
3. 动态调整规则含子周期冲突/置信度降级/回撤跨账户调配
4. 年化目标进度对配置的影响规则已定义
5. 再平衡规则完整（触发条件/步骤/优先级/税务提示）
6. 与已完成四模块的衔接格式已定义
7. 两个真实示例含完整查表和计算过程
8. 日报 V2 配置字段格式已定义
9. 用户人工确认边界明确声明
10. 验收包 12 项字段完整
11. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. asset_allocation_engine_v1.md 已写入 Drive docs/ ✓
2. 六状态配置矩阵完整 ✓
3. 动态调整规则完整 ✓
4. 再平衡规则完整 ✓
5. 两个真实示例完整 ✓
6. 验收包 12 项字段完整 ✓
7. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

Claude 完成策略设计后，Codex 执行：
将 Claude 输出的 asset_allocation_engine_v1.md 内容
写入 Drive：
  路径：G:\我的云端硬盘\AI_Investment_System\docs\asset_allocation_engine_v1.md
确认文件大小和修改时间，写入验收包：
  路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
        task-2026-06-10-009_validation_package.md
