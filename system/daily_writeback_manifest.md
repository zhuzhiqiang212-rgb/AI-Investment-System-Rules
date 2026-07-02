# 每日报告自动写回清单

更新时间：2026-06-05 20:42:32 +09:00

| 写回对象 | 路径 | 是否必须写回 | 写回频率 | 写回触发条件 | 成功标记 | 失败处理 | 是否进入验收包 |
|---|---|---|---|---|---|---|---|
| latest_official_daily_report_panel.html | reports/daily/latest_official_daily_report_panel.html | YES | 每次日报 | 正式日报/面板生成完成 | 文件存在且非空 | 标红冲突，暂停推进 | YES |
| readable_dashboard.html | reports/daily/readable_dashboard.html | YES | 每次日报 | 日报或状态变化 | 文件存在且入口有效 | 标红并保留旧版 | YES |
| dashboard.html | reports/daily/dashboard.html | YES | 每次日报 | 日报或状态变化 | 文件存在且指向latest | 标红并修复入口 | YES |
| latest_evidence_chain.md | reports/daily/latest_evidence_chain.md | YES | 每次日报 | 结论/证据变化 | 文件存在且非空 | 标记证据链未写回 | YES |
| latest_pdca_checklist.md | reports/daily/latest_pdca_checklist.md | YES | 每次日报 | 判断/验证变化 | 文件存在且非空 | 标记PDCA未写回 | YES |
| latest_four_account_action_cards.md | reports/accounts/latest_four_account_action_cards.md | YES | 每次日报 | 账户动作或风险变化 | 文件存在且非空 | 降级账户动作并人工复核 | YES |
| evidence_chain_status.json | system/evidence_chain_status.json | YES | 每次任务 | 任务状态变化 | 与master一致 | has_conflict=true | YES |
| master_task_status.json | system/master_task_status.json | YES | 每次任务 | 任务状态变化 | 与evidence一致 | has_conflict=true | YES |
| START_HERE.html | START_HERE.html | YES | 每次日报/任务 | 入口或状态变化 | 指向latest且显示next_task | 标红入口冲突 | YES |
| EVIDENCE_CHAIN_DASHBOARD.html | system/EVIDENCE_CHAIN_DASHBOARD.html | YES | 每次任务 | 状态变化 | 显示一致状态 | 重新渲染 | YES |
| MASTER_TASK_DASHBOARD.html | system/MASTER_TASK_DASHBOARD.html | YES | 每次任务 | 状态变化 | 显示一致状态 | 重新渲染 | YES |
| history/YYYY-MM-DD/ | reports/history/YYYY-MM-DD/ | YES | 每日/每次正式生成 | latest写回完成 | 7个规定归档存在 | 标黄或红并暂停推进 | YES |
| validation验收包目录 | reports/validation/ | YES | 每个任务 | 任务待验收 | 对应验收包存在 | 保持黄色待验收 | YES |
