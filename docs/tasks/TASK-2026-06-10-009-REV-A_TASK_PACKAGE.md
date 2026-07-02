# TASK PACKAGE
# TASK-2026-06-10-009 REV-A

TASK_ID: TASK-2026-06-10-009 REV-A
任务名称: ASSET_ALLOCATION_ENGINE_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Claude（策略设计）/ Codex（写入 Drive）
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 策略类
影响范围: docs/asset_allocation_engine_v1.md（新建）
APPROVAL_REQUIRED: YES
审批状态: PENDING（REV-A，等待 ChatGPT 重新审批）
旧版本状态: TASK-2026-06-10-009 原始版自动作废
是否涉及账户操作: NO
是否涉及规则变更: NO
关联文件:
  docs/buy_trigger_engine_v1.md（TASK-2026-06-10-005）
  docs/position_sizing_engine_v1.md（TASK-2026-06-10-006）
  docs/take_profit_system_v1.md（TASK-2026-06-10-007）
  docs/cycle_positioning_engine_v1.md（TASK-2026-06-10-008）

---

## 审批变更项（已合并，共4项）

1. 资产配置上限规则
   任何单一资产类别不得因周期信号无限扩张。
   必须定义每类资产的硬上限（占总资产固定比例上限）。

2. 黑天鹅模式（EMERGENCY MODE）
   战争/金融危机/流动性冻结/系统性风险触发时，
   周期标签自动降级，配置进入 EMERGENCY MODE。
   必须定义现金比例下限。

3. 年化40%目标边界
   允许落后目标时提高风险敞口，
   但必须定义提高上限，禁止无限加杠杆或无限提仓。

4. 配置建议有效期
   每次配置矩阵输出须明确有效期
   （7天 / 30天 / 直到周期失效），
   用户知道何时需要重新计算配置。

---

## 交付内容

asset_allocation_engine_v1.md 必须包含：

1. 资产配置设计原则
   - 配置目标：服务于年化 40%+ 最高目标
   - 资产配置上限规则（变更项1）：四类资产各自硬上限
   - 黑天鹅模式定义（变更项2）：触发条件 + EMERGENCY MODE
   - 年化40%目标边界（变更项3）：提高风险敞口上限
   - 配置建议有效期规则（变更项4）
   - 配置调整触发条件
   - 与周期定位引擎的联动规则
   - 禁止事项
   - 用户人工确认边界

2. 资产配置硬上限表（变更项1）
   定义四类资产的硬上限（任何周期下不可突破）：
   - 美股（IBKR）硬上限：总资产 X%
   - 日股（SBI）硬上限：总资产 X%
   - A股（富途）硬上限：总资产 X%
   - 加密（BF）硬上限：总资产 X%
   - 现金/避险资产硬下限：总资产 X%（最低必须保留）
   硬上限在任何周期信号下不可突破，
   包括 A级置信度 BULL_MID 阶段。

3. 七个周期状态下的基准配置矩阵
   对应周期定位引擎六状态 + 新增 EMERGENCY MODE：
   BULL_EARLY / BULL_MID / BULL_LATE /
   BEAR / TRANSITION / UNKNOWN / EMERGENCY
   每个状态须定义：
   - 四账户建议配置比例区间（不超过硬上限）
   - 现金/避险资产建议比例
   - 配置建议有效期（变更项4）
   - 再平衡触发阈值
   - 该状态下的年化目标敞口调整规则（变更项3）

4. EMERGENCY MODE 完整定义（变更项2）
   触发条件（满足任意一条即触发）：
   - 全球主要股指单日跌幅 > 5%
   - 信用利差单日扩张 > 50bps
   - VIX 单日跳升 > 30%
   - 用户手动宣布 EMERGENCY
   EMERGENCY MODE 规则：
   - 周期标签自动降级至 BEAR
   - 所有买入触发器暂停
   - 仓位压缩至各账户最低安全水位
   - 现金比例强制提升至总资产 X%（硬下限）
   - 解除条件：连续5个交易日无新增触发信号
     且用户手动确认解除

5. 年化目标边界规则（变更项3）
   当本月/本季度收益落后目标时：
   - 允许提高风险敞口的条件
   - 提高幅度上限（不超过基准配置的 X 个百分点）
   - 绝对禁止：使用杠杆超过账户净值 / 突破资产硬上限
   - 绝对禁止：TRANSITION / UNKNOWN 期间提高风险敞口
   - 绝对禁止：EMERGENCY MODE 期间提高任何风险敞口

6. 配置建议有效期规则（变更项4）
   每次输出配置建议时，同时输出有效期：
   - BULL_MID A级置信度：30天，或直到周期失效
   - BULL_MID B/C级置信度：7天，或直到置信度变化
   - TRANSITION / UNKNOWN：7天，或直到下次周期判断
   - EMERGENCY MODE：每日重新评估
   有效期到期或周期失效条件触发时，
   用户须重新运行周期定位引擎并更新配置。

7. 动态调整规则
   - 子周期与总周期冲突时的配置调整
   - 置信度降级时的配置收缩规则
   - 单账户触及最大回撤时的跨账户调配规则

8. 配置再平衡规则
   - 漂移阈值触发条件
   - 再平衡执行步骤与优先级
   - 税务与摩擦成本提示

9. 与已完成四模块的衔接格式
   周期标签 + 置信度 → 配置矩阵查表
   → 输出四账户比例建议 + 有效期
   → 各账户在比例内独立执行触发器/仓位/止盈

10. 真实示例两个
    示例1：BULL_MID B级置信度，含年化目标落后场景
    示例2：TRANSITION 状态突发 EMERGENCY MODE
    每个示例须展示：
    硬上限检查 / 有效期标注 / 完整查表计算

11. 日报 V2 配置状态字段格式
    须同时显示：
    - 当前周期标签 + 置信度
    - 配置建议有效期（剩余天数）
    - 四账户当前实际比例 vs 目标比例
    - 偏离程度 / 是否需要再平衡
    - EMERGENCY MODE 状态（若触发）

---

## ACCEPTANCE_CRITERIA

1. asset_allocation_engine_v1.md 已写入 docs/
2. 四类资产硬上限表完整（变更项1）
3. EMERGENCY MODE 完整定义，含触发条件/规则/解除条件（变更项2）
4. 年化目标边界规则完整，含提高上限和三条绝对禁止（变更项3）
5. 七个状态下配置建议有效期均已定义（变更项4）
6. 七状态基准配置矩阵完整（含 EMERGENCY）
7. 动态调整规则含置信度降级/子周期冲突/跨账户调配
8. 两个真实示例含硬上限检查和有效期标注
9. 日报 V2 字段含有效期剩余天数和 EMERGENCY 状态
10. 用户人工确认边界明确声明
11. 验收包 12 项字段完整
12. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. asset_allocation_engine_v1.md 已写入 Drive docs/ ✓
2. 四项审批变更全部合并 ✓
3. 七状态配置矩阵完整（含 EMERGENCY）✓
4. 硬上限表完整 ✓
5. EMERGENCY MODE 完整 ✓
6. 年化目标边界三条绝对禁止存在 ✓
7. 两个示例完整 ✓
8. 验收包 12 项字段完整 ✓
9. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

Claude 完成策略设计后，Codex 执行：
将 Claude 输出的 asset_allocation_engine_v1.md 内容
写入 Drive：
  路径：G:\我的云端硬盘\AI_Investment_System\docs\asset_allocation_engine_v1.md
确认文件大小和修改时间，写入验收包：
  路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
        task-2026-06-10-009_validation_package.md
