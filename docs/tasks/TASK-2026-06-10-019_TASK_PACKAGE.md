# TASK PACKAGE
# TASK-2026-06-10-019

TASK_ID: TASK-2026-06-10-019
任务名称: DAILY_DATA_AUTO_FETCH_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 实施类（代码）
影响范围: scripts/daily_data_fetch.py（新建）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO
是否生成交易指令: NO
是否修改账户数据: NO

---

## 任务目标

生成每日简报所需数据的自动获取脚本。

解决当前唯一主线摩擦点：
用户每天需手动查找并填入6项必填数据。
本脚本自动获取这些数据，
写入 daily_briefing_template_v1.md 的必填区，
用户只需确认数据准确后开始查表。

从"手动填4-6项→查表→3分钟"
升级为"运行脚本→确认数据→查表→1分钟"。

---

## 交付内容

### scripts/daily_data_fetch.py

自动获取以下6项数据并写入简报模板：

必填字段（6项）：
  1. VIX当日值
     数据源：Yahoo Finance（^VIX）或等价公开API
  2. 10Y美债收益率
     数据源：Yahoo Finance（^TNX）或等价公开API
  3. SPX日涨跌
     数据源：Yahoo Finance（^GSPC）
  4. BTC日涨跌
     数据源：Yahoo Finance（BTC-USD）或 CoinGecko API
  5. 加密仓位占总资产（用户配置值，非API）
     来源：读取用户本地配置文件 data/user_config.json
           若不存在，使用上次记录值或提示用户手动输入
  6. 本月已实现收益率（用户记录值）
     来源：读取 trade_record_log_v1.md 月度归因汇总
           若无记录，输出 "待填写"

脚本行为：
  1. 获取数据
  2. 输出数据预览（用户确认）
  3. 用户确认后写入 daily_briefing_template_v1.md 必填区
  4. 写入 data/daily_fetch_log.json（每日获取记录）

用户确认步骤（不可跳过）：
  输出预览后，用户输入 Y 确认写入，输入 N 取消。
  禁止未经用户确认直接写入。

数据缺失降级规则（对应简报模板降级规则）：
  VIX获取失败     → 输出"获取失败，请手动填写"，不阻断
  美债获取失败    → 同上
  SPX获取失败     → 同上
  BTC获取失败     → 同上
  任意字段失败    → 置信度降级提示写入模板
  全部失败        → 输出警告，回退到手动填写模式

标准运行命令：
  python scripts/daily_data_fetch.py

---

## 同时完成：两项已接受的改进项

### 改进项P1（Walkthrough发现）
将 daily_briefing_template_v1.md 唯一入口声明
提至文件第一行。

### 改进项P2（Walkthrough发现）
在查表区步骤1-5旁增加醒目的引擎文件标识：
  步骤1 [周期定位] → 查表：cycle_positioning_engine_v1.md
  步骤2 [资产配置] → 查表：asset_allocation_engine_v1.md
  步骤3 [买入触发] → 查表：buy_trigger_engine_v1.md
  步骤4 [仓位计算] → 查表：position_sizing_engine_v1.md
  步骤5 [止盈检查] → 查表：take_profit_system_v1.md

---

## ACCEPTANCE_CRITERIA

1. scripts/daily_data_fetch.py 已写入 scripts/
2. 脚本能成功获取VIX/美债/SPX/BTC四项数据
3. 用户确认步骤存在（Y/N确认后才写入，不可跳过）
4. 数据缺失降级规则已实现（单项失败不阻断整体）
5. daily_briefing_template_v1.md P1改进已实施
   （唯一入口声明在文件第一行）
6. daily_briefing_template_v1.md P2改进已实施
   （步骤1-5旁有引擎文件标识）
7. 运行一次 daily_data_fetch.py 并记录实际输出
8. governance_runtime.py 前置检查通过
9. 验收包 12 项字段完整
10. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. daily_data_fetch.py 已写入 scripts/ ✓
2. 实际运行测试通过（至少获取到2项数据）✓
3. 用户确认步骤存在且不可跳过 ✓
4. P1/P2 改进已实施于 daily_briefing_template_v1.md ✓
5. 验收包 12 项字段完整 ✓
6. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

步骤0：governance_runtime.py 前置检查
  python scripts/governance_runtime.py \
    --task-id "TASK-2026-06-10-019" \
    --stage "implementation" \
    --approved "true" \
    --executor "Codex" \
    --acceptor "ChatGPT" \
    --thread "AI投研总控台 + 正式日报生产" \
    --task-type "governance" \
    --affects-account "false"
  返回 0 才继续。

步骤1：生成 daily_data_fetch.py，写入 scripts/

步骤2：运行测试
  python scripts/daily_data_fetch.py --dry-run
  记录实际获取到的数据和任何失败项

步骤3：实施 P1/P2 改进
  修改 daily_briefing_template_v1.md：
  - 唯一入口声明移至第一行
  - 步骤1-5旁增加引擎文件标识

步骤4：生成验收包
  路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
        task-2026-06-10-019_validation_package.md
  须含：
    section 1：governance_runtime 前置检查结果
    section 2：daily_data_fetch.py 写入确认
    section 3：实际运行测试输出（数据获取结果）
    section 4：P1/P2 改进实施确认
    section 5：12项标准验收字段

---

## 禁止事项

禁止修改 skill_gate.py / governance_runtime.py
禁止修改 dashboard.html
禁止生成日报
禁止涉及账户操作
禁止自动下单
禁止跳过用户确认步骤直接写入模板
禁止自行最终验收
禁止在 governance_runtime.py 返回1时继续执行
