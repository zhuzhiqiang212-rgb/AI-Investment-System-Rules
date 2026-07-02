# TASK PACKAGE
# TASK-2026-06-10-008

TASK_ID: TASK-2026-06-10-008
任务名称: CYCLE_POSITIONING_ENGINE_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Claude（策略设计）/ Codex（写入 Drive）
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 策略类
影响范围: docs/cycle_positioning_engine_v1.md（新建）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO
关联文件:
  docs/buy_trigger_engine_v1.md（TASK-2026-06-10-005）
  docs/position_sizing_engine_v1.md（TASK-2026-06-10-006）
  docs/take_profit_system_v1.md（TASK-2026-06-10-007）

---

## 任务目标

为四账户设计周期定位引擎，解决当前缺口：
日报告诉用户"今天的信号"，但不告诉用户
"现在处于哪个周期阶段、该用什么仓位策略"。

与已完成模块的联动：
  周期定位引擎 → 输出当前周期阶段标签
      ↓
  买入触发器  → 流动性条件参数调整
  仓位计算    → 基础仓位系数调整
  止盈系统    → 周期止盈五维判断输入
  四模块合并构成完整的市场定位 + 交易决策体系。

---

## 交付内容

cycle_positioning_engine_v1.md 必须包含：

1. 周期定位设计原则
   - 周期阶段定义（至少4个阶段）
   - 每个阶段对应的仓位策略基准
   - 周期判断维度（量化指标清单）
   - 周期误判风险与应对
   - 用户人工确认边界

2. 周期阶段定义与判断矩阵
   至少定义以下四个阶段：
   - 牛市初期（Risk-On 启动）
   - 牛市中期（主升浪）
   - 牛市末期（过热/拥挤）
   - 熊市 / 调整期（Risk-Off）
   每个阶段须包含：
   - 判断指标与阈值
   - 对应仓位策略基准
   - 允许执行的操作
   - 禁止执行的操作
   - 典型持续时间参考

3. 周期判断指标清单
   须覆盖：
   - 宏观流动性指标（美债收益率/M2/美联储资产负债表）
   - 市场情绪指标（VIX/Fear&Greed/AAII情绪）
   - 资金流指标（ETF Flow/北向资金/稳定币供应）
   - 技术结构指标（均线系统/新高新低比/涨跌家数）
   - AI叙事指标（资本开支/研发投入/叙事强度）
   - 加密周期指标（BTC半减期/链上数据/MVRV）

4. 四账户周期联动规则
   每个账户在不同周期阶段的：
   - 仓位基准调整系数
   - 触发器参数调整
   - 止盈目标调整

5. 日报 V2 周期状态字段格式
   周期阶段标签必须出现在日报第一屏

6. 真实示例两个
   当前市场周期判断示例（美股 + 加密）
   展示完整的指标打分 → 阶段判断 → 仓位策略调整过程

---

## ACCEPTANCE_CRITERIA

1. cycle_positioning_engine_v1.md 已写入 docs/
2. 四个周期阶段定义完整，各含判断指标/仓位策略/允许禁止操作
3. 周期判断指标清单覆盖六个维度
4. 四账户周期联动规则均已定义
5. 与买入触发器/仓位引擎/止盈系统的衔接格式已定义
6. 日报 V2 周期状态字段格式已定义
7. 两个真实示例含完整判断过程
8. 用户人工确认边界明确声明
9. 验收包 12 项字段完整
10. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. cycle_positioning_engine_v1.md 已写入 Drive docs/ ✓
2. 四阶段定义完整 ✓
3. 六维指标清单完整 ✓
4. 四账户联动规则完整 ✓
5. 两个真实示例完整 ✓
6. 验收包 12 项字段完整 ✓
7. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

Claude 完成策略设计后，Codex 执行：
将 Claude 输出的 cycle_positioning_engine_v1.md 内容
写入 Drive：
  路径：G:\我的云端硬盘\AI_Investment_System\docs\cycle_positioning_engine_v1.md
确认文件大小和修改时间，写入验收包：
  路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
        task-2026-06-10-008_validation_package.md
