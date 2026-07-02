# TASK PACKAGE
# TASK-2026-06-11-006

TASK_ID: TASK-2026-06-11-006
任务名称: SYSTEM_FINAL_COMPLETENESS_CHECK_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Claude（检查）/ Codex（写入验收包）
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 验证类
影响范围: reports/validation/（写入验收包）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO
是否新增功能: NO

---

## 任务目标

确认所有已批准模块均已部署到 docs/ 和 scripts/，
用户可以从 SYSTEM_INDEX.md 找到并使用所有文件。

验证清单（P0 + P1 + P2 全部）：

P0:
  docs/SYSTEM_INDEX.md
  docs/daily_briefing_template_v1.md
  docs/trade_record_log_v1.md

P1:
  docs/cycle_positioning_engine_v1.md
  docs/asset_allocation_engine_v1.md
  docs/buy_trigger_engine_v1.md
  docs/position_sizing_engine_v1.md
  docs/take_profit_system_v1.md

P2:
  docs/strategy_attribution_system_v1.md
  docs/daily_decision_briefing_v1.md

Scripts:
  scripts/daily_data_fetch.py
  scripts/auto_briefing.py
  scripts/skill_gate.py
  scripts/governance_runtime.py

---

## ACCEPTANCE_CRITERIA

1. 上述16份文件全部存在于正确路径
2. SYSTEM_INDEX.md P2 状态已更新为已部署
3. 验收包含每份文件的存在确认
4. 验收包 12 项字段完整
5. ChatGPT 明确输出 PASS

---

## CODEX_EXECUTION

步骤0: governance_runtime.py 前置检查

步骤1: 逐一确认16份文件存在
  记录：文件名 / 存在YES/NO / 文件大小

步骤2: 更新 SYSTEM_INDEX.md P2 状态为已部署

步骤3: 生成验收包
  路径: reports/validation/
        task-2026-06-11-006_validation_package.md

---

## 禁止事项

禁止修改任何文件内容
禁止修改代码
禁止生成日报
禁止涉及账户操作
禁止自行最终验收
