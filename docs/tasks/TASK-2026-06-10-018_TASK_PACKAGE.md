# TASK PACKAGE
# TASK-2026-06-10-018

TASK_ID: TASK-2026-06-10-018
任务名称: USER_SIDE_MVP_WALKTHROUGH_TEST_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: 用户（主导）+ Codex（记录结果）
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 验证类
影响范围: reports/validation/（写入Walkthrough结果报告）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO
关联文件:
  docs/SYSTEM_INDEX.md
  docs/daily_briefing_template_v1.md
  docs/cycle_positioning_engine_v1.md
  docs/asset_allocation_engine_v1.md
  docs/buy_trigger_engine_v1.md
  docs/position_sizing_engine_v1.md
  docs/take_profit_system_v1.md
  docs/trade_record_log_v1.md

---

## 任务目标

验证用户能否从 SYSTEM_INDEX.md 进入唯一入口，
并完整走完一次真实决策前判断流程。

不是模拟测试，而是用真实当日数据（2026-06-10）
完整填写一份 daily_briefing_template_v1.md，
得出真实的第0/1/2行结论。

验证问题：
  "系统设计是否符合真实使用？
   3分钟目标是否成立？
   哪个步骤卡住了用户？"

---

## Walkthrough 流程（用户主导，Codex 计时记录）

### 阶段一：入口测试（目标30秒）

用户操作：
  1. 打开 Drive → 进入 docs/ 目录
  2. 打开 SYSTEM_INDEX.md
  3. 找到唯一入口文件名

记录：
  耗时：____秒
  是否在5秒内找到唯一入口：YES/NO
  SYSTEM_INDEX.md 唯一入口声明是否清晰：YES/NO

### 阶段二：模板填写（目标3分钟）

用户操作：
  1. 打开 daily_briefing_template_v1.md
  2. 阅读首次使用说明（首次使用者）
  3. 填写必填8项（使用当日真实数据）
  4. 填写选填字段（有数据就填，无数据跳过）
  5. 完成查表区6步
  6. 输出第0/1/2行结论

记录（逐步计时）：
  首次使用说明阅读耗时：____秒
  必填8项填写耗时：____秒
  选填字段填写耗时：____秒
  查表区6步耗时：____秒
  第0/1/2行输出耗时：____秒
  总耗时：____秒（目标≤180秒）

### 阶段三：结论记录

填写当日真实数据并输出：
  日期：2026-06-10

  必填字段填写结果：
    VIX：____
    10Y美债：____%
    SPX日涨跌：____%
    BTC日涨跌：____%
    加密仓位：____%
    本月收益率：____%
    最大持仓浮亏：____%

  选填字段填写情况：
    北向资金：有/无（值：____）
    美元兑日元：有/无（值：____）
    ETF资金流：有/无
    Positioning：有/无
    Onchain：有/无
    纳指：有/无

  查表区结果：
    步骤1 周期标签：____  置信度：____
    步骤2 配置偏离：YES/NO
    步骤3 四账户信号：美股____ 日股____ A股____ 加密____
    步骤4 建议仓位：____%
    步骤5 触发止损：YES/NO
    步骤6 失效预警：有/无

  输出结果：
    第0行结论：________________________  置信度：____
    第1行唯一动作：____________________
    第2行最不能做：
      1. ____________________
      2. ____________________（若有）

### 阶段四：问题记录

记录用户在Walkthrough中遇到的所有卡点：

  卡点1：____________________（发生在哪步/耗时/原因）
  卡点2：____________________（若有）
  卡点3：____________________（若有）

  总体评估：
    3分钟目标是否达成：YES/NO
    哪个步骤最耗时：____
    哪个步骤最难理解：____
    哪个引擎文档查表最困难：____
    用户是否能独立完成全流程：YES/NO（需要辅助的步骤：____）

---

## ACCEPTANCE_CRITERIA

1. Walkthrough 结果报告已写入 reports/validation/
2. 阶段一：用户能否找到唯一入口（结果记录）
3. 阶段二：总耗时已记录（是否达成3分钟目标）
4. 阶段三：真实当日数据填写结果和第0/1/2行输出已记录
5. 阶段四：卡点和改进建议已记录
6. 验收包含以下结论判断：
   - 3分钟目标：YES/NO
   - 用户能独立完成：YES/NO
   - 需要立即修复的卡点数量：____
7. 验收包 12 项字段完整
8. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. Walkthrough 结果报告写入 reports/validation/ ✓
2. 真实第0/1/2行结论已产生 ✓
3. 卡点和改进建议已记录 ✓
4. 3分钟目标是否达成有明确结论 ✓
5. 验收包 12 项字段完整 ✓
6. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

本任务执行人是用户（主导Walkthrough），
Codex 负责：
  1. 运行 governance_runtime.py 前置检查
  2. 协助用户计时记录各阶段耗时
  3. 将用户Walkthrough结果整理写入验收报告：
     路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
           task-2026-06-10-018_walkthrough_report.md
  4. 生成标准验收包：
     路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
           task-2026-06-10-018_validation_package.md

执行前置检查命令：
  python scripts/governance_runtime.py \
    --task-id      "TASK-2026-06-10-018" \
    --stage        "implementation" \
    --approved     "true" \
    --executor     "Codex" \
    --acceptor     "ChatGPT" \
    --thread       "AI投研总控台 + 正式日报生产" \
    --task-type    "governance" \
    --affects-account "false"

---

## 禁止事项

禁止用模拟数据替代真实当日数据
禁止跳过任何Walkthrough阶段
禁止在3分钟目标未达成时填写 YES
禁止修改任何策略文件或代码
禁止自行最终验收
禁止生成日报
禁止涉及账户操作
