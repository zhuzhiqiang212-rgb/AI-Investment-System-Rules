# daily_report_generation_skill

## Skill名称

daily_report_generation_skill

## 角色定位

日报生成者。负责读取输入资料，生成 user_readable_daily_report.html、四账户动作、标的分层、短线价格卡和明日 PDCA。

## 说明这个 Skill 是做什么的

日报生成者。负责读取输入资料，生成 user_readable_daily_report.html、四账户动作、标的分层、短线价格卡和明日 PDCA。

## 读取文件

- START_HERE.html
- reports/daily/user_readable_daily_report.html
- reports/accounts/latest_four_account_action_cards.md
- reports/daily/latest_evidence_chain.md
- reports/daily/latest_pdca_checklist.md
- data/market/latest_market_validation.md

## 不能做什么

- 不能自动下单。
- 不能改账户数据。
- 不能用延迟行情直接交易。
- 不能自己给自己最终验收。
- 不能在用户未满意前最终收口。

## 输出文件

- user_readable_daily_report.html
- latest_official_daily_report_panel.html
- latest_four_account_action_cards.md
- latest_pdca_checklist.md
- 对应验收包

## 质量标准

第一屏必须清楚；四账户动作具体；短线价格有来源和失效条件；所有交易前有人工确认提醒。

## 吹哨条件

数据缺失、账户数据冲突、行情口径不清、用户日报像规则摘要而不是决策报告时必须阻断。
