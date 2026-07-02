# 每日报告自动写回检查说明

更新时间：2026-06-05 20:42:32 +09:00

可执行脚本：`system/daily_writeback_check.py`

| 检查项 | 检查方法 | 通过条件 | 失败处理 |
|---|---|---|---|
| latest_official_daily_report_panel 是否存在 | 检查路径与非零大小 | 存在且非空 | 标红冲突并暂停推进 |
| readable_dashboard 是否存在 | 检查路径与非零大小 | 存在且非空 | 保留旧版并标红 |
| latest_evidence_chain 是否存在 | 检查路径与非零大小 | 存在且非空 | 标记证据链未写回 |
| latest_pdca_checklist 是否存在 | 检查路径与非零大小 | 存在且非空 | 标记PDCA未写回 |
| four_account_action_cards 是否存在 | 检查路径与非零大小 | 存在且非空 | 账户动作降级 |
| START_HERE 是否指向 latest | 搜索latest_official_daily_report_panel.html | 存在latest入口 | 修复入口并标红 |
| dashboard 是否指向 latest | 搜索latest_official_daily_report_panel.html | 存在latest入口 | 修复入口并标红 |
| 两份status JSON是否一致 | 比较任务状态与next_task | 完全一致 | has_conflict=true |
| next_task 是否正确 | 按优先级重算 | 与状态文件一致且非错误NONE | 阻断推进 |
| 历史归档是否存在 | 检查当日7个归档文件 | 全部存在且非空 | 标记归档失败 |
| validation验收包是否生成 | 检查对应文件 | 存在且非空 | 保持黄色待验收 |
| 旧报告是否误作今日入口 | 检查主入口链接 | 只指向latest | 移到历史入口 |
