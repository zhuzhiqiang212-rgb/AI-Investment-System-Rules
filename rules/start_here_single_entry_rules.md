# START_HERE 唯一入口稳定性规则

更新时间：2026-06-06 13:27:47 +09:00

1. START_HERE.html 是用户每天第一入口。
2. START_HERE 必须优先指向：

   - reports/daily/readable_dashboard.html
   - reports/daily/latest_official_daily_report_panel.html
   - system/MASTER_TASK_DASHBOARD.html
   - system/EVIDENCE_CHAIN_DASHBOARD.html
   - reports/daily/latest_evidence_chain.md
   - reports/daily/latest_pdca_checklist.md
   - reports/accounts/latest_four_account_action_cards.md

3. START_HERE 不得指向旧日期日报作为今日主入口。
4. START_HERE 不得出现多个互相冲突的 next_task。
5. START_HERE 显示的任务状态必须与 master_task_status.json、evidence_chain_status.json、MASTER_TASK_DASHBOARD.html、EVIDENCE_CHAIN_DASHBOARD.html 保持一致。
6. 如果 START_HERE 与 JSON 状态冲突，必须红色阻断，不允许继续任务。
7. 如果桌面快捷方式或浏览器缓存打开旧版 START_HERE，必须提示刷新或重新打开最新路径。
8. START_HERE 第一屏必须显示当前系统状态、当前下一步唯一任务、当前是否有冲突、今日主入口按钮、readable_dashboard 按钮、最新日报按钮、四账户动作卡入口、任务总清单入口。
