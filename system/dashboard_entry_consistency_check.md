# dashboard入口一致性检查

更新时间：2026-06-06 12:25:50 +09:00

| 检查项 | 结果 | 说明 | 是否阻断 |
|---|---|---|---|
| START_HERE 是否存在 | YES | 主入口文件存在 | NO |
| readable_dashboard 是否存在 | YES | 第二入口存在 | NO |
| latest_official_daily_report_panel 是否存在 | YES | 正式日报 latest panel 存在 | NO |
| dashboard.html 是否存在且不为空 | YES | dashboard.html 存在且非空 | NO |
| 所有主按钮路径是否存在 | YES | 10个主按钮目标均存在 | NO |
| 是否所有主入口都指向 latest | YES | 主入口指向 latest/readable/任务仪表盘；旧报告仅历史 | NO |
| 是否存在旧日期报告作为主入口 | NO | 未在五个入口发现 26-05-30 作为主入口 | NO |
| master_task_status 与 evidence_chain_status 是否一致 | YES | next_task 均为 P1-023 | NO |
| START_HERE 显示的 next_task 是否与 JSON 一致 | YES | 显示 P1-023 | NO |
| MASTER_TASK_DASHBOARD 显示的 next_task 是否与 JSON 一致 | YES | 显示 P1-023 | NO |
| EVIDENCE_CHAIN_DASHBOARD 显示的 next_task 是否与 JSON 一致 | YES | 显示 P1-023 | NO |
| 是否存在 next_task = NONE 异常 | NO | 系统建设中，next_task 不为 NONE | NO |
| Drive 路径是否仍在 AI_Investment_System 下 | YES | G:\我的云端硬盘\AI_Investment_System | NO |
| 是否存在 OneDrive 残留主入口 | NO | 未发现 OneDrive / New project 2 主入口残留 | NO |
| 手机端是否能在第一屏看到入口 | YES | 三个日常入口与两个系统页均保留手机首屏按钮 | NO |

