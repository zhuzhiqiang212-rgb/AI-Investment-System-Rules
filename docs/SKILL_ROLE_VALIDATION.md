# Skill 职能验证表

| Skill | 职能 | 输入文件 | 输出文件 | 不能做什么 | 何时需要ChatGPT验收 |
| ----- | -- | ---- | ---- | ----- | ------------- |
| daily_report_generation_skill | 生成用户版日报、四账户动作、标的分层、短线价格卡、明日PDCA | START_HERE.html；reports/daily/user_readable_daily_report.html；reports/accounts/latest_four_account_action_cards.md；reports/daily/latest_evidence_chain.md；reports/daily/latest_pdca_checklist.md；data/market/latest_market_validation.md | user_readable_daily_report.html；latest_official_daily_report_panel.html；四账户动作卡；PDCA；验收包 | 不能自动下单；不能改账户数据；不能自己最终验收；不能用延迟行情直接交易 | 生成或重构日报、动作卡、PDCA 后必须给 ChatGPT 验收 |
| quality_review_skill | 检查用户日报是否达质量目标，判断是否通过/返工/阻断 | rules/user_report_quality_master_goals.md；system/quality_goal_task_status.json；reports/validation/*validation_package*.md；用户日报 | 质量检查结论；问题清单；green/yellow/red 建议；下一步修复指令 | 不能替代用户最终确认；不能直接改账户数据；不能自动下单 | 任何质量任务标绿前必须验收 |
| final_closure_skill | 最终收口前检查所有任务、入口、用户满意度和阻断项 | system/master_task_status.json；system/quality_goal_task_status.json；START_HERE.html；最终收口验收包 | 最终收口验收包；收口阻断原因；是否允许 daily_use_mode 建议 | 不能在用户未满意、任务未全绿、存在红黄阻断时收口 | 最终收口前必须由 ChatGPT 和用户共同确认 |
| account_execution_quality_skill | 检查四账户执行卡是否逐标、具体、可复核 | latest_account_snapshot.md；account_position_execution_matrix.md；latest_four_account_action_cards.md；ticker_layering_decision_table.md | 账户执行质量检查；逐标矩阵；账户动作验收包 | 不能编造持仓、成本、现金、挂单；不能输出确定交易动作 | 四账户动作卡更新或账户执行质量任务完成后 |
| short_term_price_quality_skill | 检查短线价格参考、技术位、强弱参考、暂不出价和缺口 | short_term_price_quality_table.md；technical_level_generator.md；technical_price_data_gap_list.md；latest_market_validation.md；account_position_execution_matrix.md | 短线价格质量检查表；技术位缺口清单；短线价格验收包 | 不能把延迟行情当实时；不能把百分比回撤伪装成技术支撑；不能直接下单 | 短线价格卡或 Q0-004 更新后必须验收 |
