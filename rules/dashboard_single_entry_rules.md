# dashboard 唯一入口规则

更新时间：2026-06-06 12:25:50 +09:00

## 1. 用户每日入口顺序

用户每天只需要按顺序打开：

1. START_HERE.html
2. reports/daily/readable_dashboard.html
3. reports/daily/latest_official_daily_report_panel.html

其他文件只能作为详情或历史，不得作为主入口。

## 2. latest 优先规则

所有按钮必须优先指向 latest 文件：

- latest_official_daily_report_panel.html
- readable_dashboard.html
- latest_evidence_chain.md
- latest_pdca_checklist.md
- latest_four_account_action_cards.md
- MASTER_TASK_DASHBOARD.html
- EVIDENCE_CHAIN_DASHBOARD.html

旧报告只能放在历史入口。

## 3. 禁止事项

禁止：

- dashboard 指向旧日期日报
- START_HERE 出现多个互相冲突的入口
- next_task 显示 NONE 但系统未收口
- 页面状态和 JSON 状态不一致
- 按钮存在但路径打不开
- 手机端入口太深
- 用户需要自己判断哪个文件最新

## 4. 失败阻断规则

如果出现以下任一情况：

- START_HERE 打不开
- readable_dashboard 打不开
- latest_official_daily_report_panel 打不开
- 任一主按钮路径不存在
- dashboard 指向历史报告
- 状态 JSON 与页面不一致
- next_task 错误
- Drive 同步路径缺失

则：

1. dashboard 状态显示红色
2. 任务推进暂停
3. 生成 validation 报告
4. 不允许继续下一任务
