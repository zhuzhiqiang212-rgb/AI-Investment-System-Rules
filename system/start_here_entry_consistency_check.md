# START_HERE入口一致性检查

更新时间：2026-06-06 13:27:47 +09:00

| 检查项 | 结果 | 说明 | 是否阻断 |
|---|---|---|---|
| START_HERE.html 是否存在 | YES | 文件存在 | NO |
| START_HERE.html 是否非空 | YES | 文件非空 | NO |
| START_HERE 是否显示当前 next_task | YES | 当前任务为P1-024 | NO |
| START_HERE 的 next_task 是否与 master_task_status.json 一致 | YES | next_task 同步为 P1-024 | NO |
| START_HERE 的 next_task 是否与 evidence_chain_status.json 一致 | YES | next_task 同步为 P1-024 | NO |
| START_HERE 是否显示 P1-024 为当前任务 | YES | P1-024可见 | NO |
| START_HERE 是否不存在旧的 P1-023 待验收状态 | YES | P1-023已通过，不再待验收 | NO |
| START_HERE 是否不显示 next_task NONE | YES | 未发现NONE | NO |
| START_HERE 是否优先指向 latest 文件 | YES | latest日报/证据链/PDCA/四账户入口存在 | NO |
| START_HERE 是否不把旧报告作为今日主入口 | YES | 旧报告仅历史入口 | NO |
| START_HERE 是否有 readable_dashboard 入口 | YES | 入口存在 | NO |
| START_HERE 是否有 latest_official_daily_report_panel 入口 | YES | 入口存在 | NO |
| START_HERE 是否有 MASTER_TASK_DASHBOARD 入口 | YES | 入口存在 | NO |
| START_HERE 是否有四账户动作入口 | YES | 入口存在 | NO |
| START_HERE 是否手机端第一屏可读 | YES | 移动端首屏摘要存在 | NO |
| 是否存在 OneDrive 残留主入口 | NO | 仅缓存提示中禁止OneDrive；无主入口残留 | NO |
| 是否存在浏览器缓存提示 | YES | 已写入Ctrl+F5与重新打开提示 | NO |
| 是否存在桌面快捷方式提示 | YES | 已写入快捷方式目标检查结果 | NO |
