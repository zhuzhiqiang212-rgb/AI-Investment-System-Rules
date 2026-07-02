# TASK PACKAGE
# TASK-2026-06-10-012

TASK_ID: TASK-2026-06-10-012
任务名称: DAILY_BRIEFING_TEMPLATE_IMPLEMENTATION_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 策略类 + 实施类
影响范围:
  docs/daily_briefing_template_v1.md（新建，每日可填写的实体模板）
  docs/trade_record_log_v1.md（新建，交易记录存储文件）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO
关联文件:
  docs/daily_decision_briefing_v1.md（格式规范，本任务的输入）
  docs/buy_trigger_engine_v1.md
  docs/position_sizing_engine_v1.md
  docs/take_profit_system_v1.md
  docs/cycle_positioning_engine_v1.md
  docs/asset_allocation_engine_v1.md
  docs/strategy_attribution_system_v1.md

---

## 任务目标

把七个已完成的策略设计文档转化为
用户每天实际可以使用的工具文件。

解决当前核心缺口：
七个引擎是七份规则文档，没有任何一份
是用户每天打开填写的工作文件。
本任务生成两份实体工具文件：

文件1：每日简报填写模板
  用户每天填入当日数据 → 自动查表 →
  输出第0/1/2行结论 + 五区块状态

文件2：交易记录日志
  用户每笔交易和未交易事件的记录载体
  归因系统的数据积累起点

---

## 交付内容

### 文件1：daily_briefing_template_v1.md

每日简报填写模板，包含：

1. 数据填充区（用户每日手动填入）
   必填字段（15项）：
   - 日期
   - VIX当日值
   - 10年期美债收益率
   - SPX日涨跌幅
   - 纳指日涨跌幅
   - BTC日涨跌幅
   - 北向资金净流入（亿人民币）
   - 美元兑日元汇率
   - 富途账户总市值
   - IBKR账户总市值
   - SBI账户总市值
   - BF账户总市值
   - 加密仓位占总资产比例
   - 本月已实现收益率
   - 近期最大回撤

2. 自动查表区（基于填入数据）
   用户填完数据后按引擎逐步查表：
   步骤1查表：周期定位引擎 → 周期标签 + 置信度
   步骤2查表：资产配置引擎 → 配置偏离状态
   步骤3查表：买入触发器   → 各账户信号等级
   步骤4查表：仓位计算     → 建议仓位（若有信号）
   步骤5查表：止盈系统     → 持仓止盈止损状态
   步骤6查表：归因系统     → 失效预警（若有）

3. 输出区（基于查表结果生成）
   第0行：今日一句话结论 + 置信度等级
   第1行：今日唯一动作（四选一）
   第2行：今日最不能做（1-3条）
   区块A-E：五个状态区块

4. 历史填写记录区
   保留最近7天的简报摘要
   供用户快速对比趋势

### 文件2：trade_record_log_v1.md

交易记录日志，包含：

1. 已执行交易记录表
   按 strategy_attribution_system_v1.md
   的12字段标准格式，提供空白填写表格
   初始提供30行空白记录位置

2. 未交易事件记录表
   按四类未交易事件格式，提供空白填写表格
   类型A：触发未买入
   类型B：应减未减
   类型C：违规买入
   类型D：应止未止

3. 月度归因汇总区
   每月末填写：
   - 总交易次数 / 胜率 / 盈亏比
   - 各模块责任归因统计
   - 人工干预偏离次数

---

## ACCEPTANCE_CRITERIA

1. daily_briefing_template_v1.md 已写入 docs/
2. 模板含 15 项数据填充字段
3. 六步查表流程对应所有引擎
4. 输出区含第0/1/2行 + 五区块完整格式
5. trade_record_log_v1.md 已写入 docs/
6. 交易记录表含 12 字段标准格式
7. 未交易四类记录表格完整
8. 月度归因汇总区完整
9. 验收包 12 项字段完整
10. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. daily_briefing_template_v1.md 已写入 Drive docs/ ✓
2. trade_record_log_v1.md 已写入 Drive docs/ ✓
3. 15项数据填充字段完整 ✓
4. 六步查表流程完整 ✓
5. 交易记录和未交易记录表格完整 ✓
6. 验收包 12 项字段完整 ✓
7. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

步骤1：读取以下文件作为输入：
  G:\我的云端硬盘\AI_Investment_System\docs\daily_decision_briefing_v1.md
  G:\我的云端硬盘\AI_Investment_System\docs\strategy_attribution_system_v1.md

步骤2：生成 daily_briefing_template_v1.md
写入路径：
  G:\我的云端硬盘\AI_Investment_System\docs\daily_briefing_template_v1.md

步骤3：生成 trade_record_log_v1.md
写入路径：
  G:\我的云端硬盘\AI_Investment_System\docs\trade_record_log_v1.md

步骤4：确认两份文件大小和修改时间，写入验收包：
  G:\我的云端硬盘\AI_Investment_System\reports\validation\
  task-2026-06-10-012_validation_package.md
