# 历史报告归档规则

更新时间：2026-06-06 16:05:14 +09:00

## 1. latest 文件规则

以下文件永远代表当前最新版本，不移动，不改名：

* reports\daily\latest_official_daily_report_panel.html
* reports\daily\readable_dashboard.html
* reports\daily\dashboard.html
* reports\daily\latest_evidence_chain.md
* reports\daily\latest_pdca_checklist.md
* reports\accounts\latest_four_account_action_cards.md
* system\master_task_status.json
* system\evidence_chain_status.json
* START_HERE.html

## 2. 历史归档目录规则

历史文件统一归档到：

G:\我的云端硬盘\AI_Investment_System\reports\history\YYYY-MM-DD\

每个日期目录下可分：

* daily_reports
* dashboards
* evidence_chain
* pdca
* account_cards
* validation_packages
* inputs_snapshot
* system_status

## 3. 验收包归档规则

所有验收包主目录仍保留在：

G:\我的云端硬盘\AI_Investment_System\reports\validation\

但必须建立索引：

G:\我的云端硬盘\AI_Investment_System\reports\validation\validation_index.md

如果一个任务有多个版本：

* v1 不通过
* v2 通过

索引必须写明最终通过版本。

## 4. 旧报告降级规则

旧日期日报、旧 dashboard、旧卡片只能作为历史参考。

禁止：

* 旧报告作为今日主入口
* 旧 dashboard 覆盖 latest
* 旧快照进入当前价主表
* 历史验收包误当待验收文件

## 5. 历史入口规则

START_HERE 和 readable_dashboard 必须有“历史报告入口”，但位置不能高于今日入口。

用户优先级：

1. 今日入口
2. 当前任务
3. 最新日报
4. 历史报告入口
