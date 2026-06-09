# 每日报告自动写回规则

更新时间：2026-06-05 20:42:32 +09:00

## 必须同步写回对象

每日正式生成完成后，必须同步检查并写回：

1. `reports/daily/latest_official_daily_report_panel.html`
2. `reports/daily/readable_dashboard.html`
3. `reports/daily/dashboard.html`
4. `reports/daily/latest_evidence_chain.md`
5. `reports/daily/latest_pdca_checklist.md`
6. `reports/accounts/latest_four_account_action_cards.md`
7. `system/evidence_chain_status.json`
8. `system/master_task_status.json`
9. `START_HERE.html`
10. `system/EVIDENCE_CHAIN_DASHBOARD.html`
11. `system/MASTER_TASK_DASHBOARD.html`

## latest 文件规则

- latest 文件永远代表当前最新正式版本，并采用覆盖写入。
- latest 文件不得指向旧日期报告。
- START_HERE 和 dashboard 必须优先指向 latest 文件。
- 旧日期报告只能进入历史入口。

## 历史归档规则

每日正式报告生成后，复制到 `reports/history/YYYY-MM-DD/`：

- `official_daily_report_panel_YYYY-MM-DD.html`
- `readable_dashboard_YYYY-MM-DD.html`
- `latest_evidence_chain_YYYY-MM-DD.md`
- `latest_pdca_checklist_YYYY-MM-DD.md`
- `latest_four_account_action_cards_YYYY-MM-DD.md`
- `evidence_chain_status_YYYY-MM-DD.json`
- `master_task_status_YYYY-MM-DD.json`

归档使用复制，不删除 latest 文件；同日再次运行允许覆盖同日归档。

## 状态同步规则

- 只有 ChatGPT 明确验收通过，任务才允许标绿。
- Codex 不得自动标绿待验收任务。
- `next_task` 不得为 `NONE`，除非全部任务真实完成。
- START_HERE、MASTER_TASK_DASHBOARD、EVIDENCE_CHAIN_DASHBOARD 与两个 JSON 状态必须一致。
- 如果状态冲突，必须在 `daily_writeback_status.json` 标记冲突并暂停后续推进。

## 入口优先级规则

用户每日优先打开：

1. `START_HERE.html`
2. `reports/daily/readable_dashboard.html`
3. `reports/daily/latest_official_daily_report_panel.html`

旧报告不得作为今日主入口。

## 冲突阻断规则

出现任一情况必须阻断推进：

- 两份状态 JSON 的任务状态或 next_task 不一致。
- 存在未完成任务但 next_task 为 NONE。
- START_HERE 或 dashboard 未指向 latest 文件。
- 历史归档失败。
- 验收包未生成。
- ChatGPT 未验收的任务被标绿。

失败时：保留原文件，记录原因，`has_conflict=true`，不得自动推进下一任务。
