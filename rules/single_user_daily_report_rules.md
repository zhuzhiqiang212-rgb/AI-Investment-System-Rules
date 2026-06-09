# 用户唯一总日报规则

## 1. 用户主入口

用户每天只需要打开：

G:\我的云端硬盘\AI_Investment_System\START_HERE.html

START_HERE 第一屏只显示一个主按钮：

打开今日用户总日报

该按钮指向：

G:\我的云端硬盘\AI_Investment_System\reports\daily\user_readable_daily_report.html

## 2. 用户总日报定位

user_readable_daily_report.html 是用户每天真正看的唯一主报表。

它必须包含：

* 今日一句话结论
* 今天该进攻 / 观望 / 防守
* 四账户动作
* 今天不能做什么
* 当前最大风险
* 数据缺口
* 明日PDCA
* 短线价格指导
* 业务趋势
* 资金流
* 宏观逻辑
* 财报三指标
* 护城河评分
* 后台检查入口

## 3. 其他页面定位

以下页面不再作为用户第一入口：

* readable_dashboard.html
* latest_official_daily_report_panel.html
* MASTER_TASK_DASHBOARD.html
* EVIDENCE_CHAIN_DASHBOARD.html
* reports\validation\
* 各种 validation_package.md

它们只能放在：

后台检查区 / 备用入口 / 详情入口

## 4. 禁止事项

禁止：

* 第一屏同时放3个平级主入口，让用户自己判断
* 把验收包放在用户主阅读区域
* 把任务状态检查放在用户主阅读区域
* 把YES/NO后台表放在用户主阅读区域
* 让用户每天打开多个HTML判断哪个是最新
* 用户主报表只有摘要，没有动作和原因
