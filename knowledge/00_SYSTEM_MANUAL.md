# 00_SYSTEM_MANUAL
# AI投研总控台 V6 系统手册

版本: V6.0
生效时间: 2026-06-14 JST
制定人: Claude / ChatGPT V6

---

## 一、系统定位

AI投研总控台 V6 是一个**有边界的决策辅助系统**。

最终目标: 四账户年化收益率 40%+
交付物: 每天一份决策前判断简报
核心边界:
  - 系统只提供决策辅助，不自动执行
  - 账户下单和出入金只能由用户本人操作
  - 禁止连接券商下单接口
  - 禁止存储账户密码或API密钥

---

## 二、模块职责

### 数据层
职责: 自动获取市场数据
工具: daily_data_fetch.py
数据源: Yahoo Finance（VIX/SPX/10Y）+ Binance（BTC）
输出: 结构化数据字典

### 分析层
职责: 周期定位 + 信号判断 + 置信度评级
工具: auto_briefing.py（step1_cycle / step3_signal）
输入: 市场数据字典
输出: 周期标签 + 置信度 + 信号等级

### 决策层
职责: 生成三层结论
工具: auto_briefing.py（generate_conclusions）
规则:
  - TRANSITION/UNKNOWN/BEAR → 强制"观察"
  - BULL_MID A级 → 允许"分批建仓"
  - layer2至少两条，第二条含当日具体数据
输出: 第0/1/2层结论

### 输出层
职责: 写入四报表和START_HERE.html
工具: auto_briefing.py（write_latest_cards / update_start_here）
输出文件:
  latest_daily_report.md（今天发生了什么）
  latest_direction_card.md（主线方向是否变化）
  latest_risk_card.md（最大风险是什么）
  latest_execution_card.md（今天该做什么）

### 治理层
职责: 运行时门控，防止违规执行
工具: governance_runtime.py + skill_gate.py
拦截: PV-003（未批准）/ PV-004（自验）/ PV-006（错误线程）

### 归因层
职责: 记录交易，积累胜率数据
工具: trade_record_log_v1.md + monthly_return_tracking_v1.md
触发: 每笔交易后手动填写，每月末归因复盘

---

## 三、运行原则

### 原则1：信号质量优先于自动化程度
在信号质量未经3个月实盘验证之前，保留用户确认步骤。
不因追求自动化而跳过人工确认。

### 原则2：置信度决定动作边界
A级: 允许分批建仓（仅BULL_MID）
B级: 允许持有，等待更强确认
C级: 强制观察，不执行任何新仓

### 原则3：每日使用流程固定
早盘前: python scripts/auto_briefing.py → 输入Y
看到结论后人工决策，在券商界面手动操作
交易后: 填写 trade_record_log_v1.md
月末: 填写 monthly_return_tracking_v1.md

### 原则4：四报表职责边界固定
日报: 今天发生了什么，昨日判断是否验证
方向卡: 当前周期方向 + 失效条件
风险卡: TOP1风险 + 触发阈值 + 最不能做
执行卡: 唯一动作 + 四账户边界

### 原则5：治理门控不可绕过
任何新任务必须经过: PROPOSAL→APPROVAL→IMPLEMENTATION
governance_runtime.py 前置检查必须通过
执行人 ≠ 验收人（禁止自验）

---

## 四、统一规范

### 数据缺失处理
单项DATA_GAP → 对应信号降级，不阻断整体
必填字段缺失≥3项 → 整体置信度降C级

### 样本积累规则
触发器各等级：最少10次才能统计胜率
周期标签：最少8次才能统计有效性
样本不足 → 禁止输出"策略有效/失效"结论

### 40%目标追踪
月度目标: 3.33%（40%÷12）
连续3个月低于目标 → 触发G-10策略迭代
月末填写: monthly_return_tracking_v1.md

---

## 五、新模块继承规则

任何新增模块必须：
1. 继承本手册的系统定位和边界原则
2. 运行前执行 governance_runtime.py 前置检查
3. 不新增下单接口
4. 不存储账户密码
5. 输出末尾包含 NEXT_OWNER / NEXT_ACTION / NEXT_THREAD
