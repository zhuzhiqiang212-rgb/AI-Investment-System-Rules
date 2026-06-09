# 用户版报表与验收包分离规则

## 1. 验收包用途

validation_package 只用于：

* ChatGPT验收
* Codex自检
* 证明任务是否完成
* 摘录真实内容
* 记录路径、状态、质量检查

验收包可以是 Markdown。
验收包可以包含表格、路径、YES/NO、技术细节。
验收包不作为用户每天主阅读页面。

## 2. 用户版报表用途

用户版报表用于：

* 用户每天打开阅读
* 5秒内看懂今日结论
* 看到四账户动作
* 看到风险和禁止动作
* 看到数据缺口
* 看到明日PDCA
* 看到短线价格指导
* 看到市场结构是否变化

用户版报表必须是 HTML 卡片式。
用户版报表必须手机端可读。
用户版报表不能是黑底小字。
用户版报表不能是长横表。
用户版报表不能只写路径和YES/NO。

## 3. 文件分工

后台验收文件放在：

G:\我的云端硬盘\AI_Investment_System\reports\validation\

用户阅读文件放在：

G:\我的云端硬盘\AI_Investment_System\reports\daily\

用户主要阅读入口：

1. START_HERE.html
2. reports\daily\readable_dashboard.html
3. reports\daily\latest_official_daily_report_panel.html
4. reports\daily\full_single_entry_preview.html

验收包不得作为今日主入口。

## 4. 用户版报表最低标准

每个用户版模块必须包含：

* 一句话结论
* 证据
* 风险
* 当前动作
* 禁止动作
* 等待条件
* 失效条件
* 数据缺口
* 人工确认提醒

禁止：

* 只显示YES/NO
* 只显示文件路径
* 只显示后台检查表
* 黑底小字
* 横向长表挤爆
* 没有结论
* 没有动作
* 没有风险
* 没有失效条件
