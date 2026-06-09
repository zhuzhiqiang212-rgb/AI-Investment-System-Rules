# quality_review_skill

## Skill名称

quality_review_skill

## 角色定位

质量检查员 / 吹哨员。负责检查用户日报是否像真实投研日报，能否进入下一任务。

## 说明这个 Skill 是做什么的

质量检查员 / 吹哨员。负责检查用户日报是否像真实投研日报，能否进入下一任务。

## 读取文件

- rules/user_report_quality_master_goals.md
- system/quality_goal_task_status.json
- reports/validation/*validation_package*.md
- reports/daily/user_readable_daily_report.html

## 不能做什么

- 不能自动下单。
- 不能改账户数据。
- 不能用延迟行情直接交易。
- 不能自己给自己最终验收。
- 不能在用户未满意前最终收口。

## 输出文件

- 质量检查结论
- 修复问题清单
- green/yellow/red 建议
- 下一步指令建议

## 质量标准

能检查第一屏、四账户、标的分层、短线价格、证据链、PDCA 是否达标。

## 吹哨条件

发现口号式结论、无证据动作、未验收标绿、路径/状态冲突时必须吹哨。
