# Codex 右侧对话框承接说明

## 1. 你现在接手的系统是什么

- AI_Investment_System 是用户的 AI 投研闭环系统。
- 目标不是自动交易，也不是替代用户下单。
- 目标是生成用户每天能读懂、能执行、能复盘的投研日报。
- 用户主入口是 `START_HERE.html`。
- 用户主报表是 `reports\daily\user_readable_daily_report.html`。

## 2. 当前系统状态

- 基础系统任务已经完成。
- GitHub / Skill 工程体系已通过。
- 本地 Git 已初始化，但当前终端可能需要重启后才能直接识别 `git` PATH。
- 当前仍处于“质量目标任务阶段”。
- 当前质量任务停在 `Q0-004 短线价格指导质量 V2`。
- `Q0-001 / Q0-002 / Q0-003` 已通过。
- `Q0-004` 不得自动标绿。
- 最终收口暂停。

## 3. 你的角色

Codex 是：

- 工程执行者
- 文件生成者
- 结构修复者
- 验收包生成者

Codex 不是：

- 最终验收者
- 自动交易执行者
- 账户数据编造者
- 最终收口放行者

## 4. ChatGPT 的角色

ChatGPT 是：

- 总设计
- 指令生成
- 质量验收
- 吹哨
- 是否通过 / 是否标绿的判定者

## 5. 用户的角色

用户是：

- 最终确认者
- 体验验收者
- 真实账户操作人
- 可以随时否决收口的人

## 6. GitHub / Google Drive 分工

Google Drive 保存：

- 日报
- 验收包
- 历史报告
- 截图
- 输入资料
- 账户快照
- validation 文件

GitHub 保存：

- README
- docs
- rules
- skills
- scripts
- templates
- 系统结构说明

禁止把以下内容放进 Git：

- 账户截图
- 持仓截图
- reports/daily
- reports/validation
- inbox
- inputs
- PDF / 图片 / 视频 / 音频
- `.env`

## 7. 如何使用 Skill

- `daily_report_generation_skill`：生成用户版日报、账户动作、标的分层、短线价格卡和明日 PDCA。
- `quality_review_skill`：检查日报是否达到质量目标，是否能标绿或进入下一步。
- `final_closure_skill`：最终收口前检查；只有所有质量任务通过且用户满意，才可建议收口。
- `account_execution_quality_skill`：检查四账户执行卡是否下钻到逐标、数量、成本、动作、失效条件。
- `short_term_price_quality_skill`：检查短线价格、技术位、强弱参考、暂不出价、数据缺口。

执行任何任务前，先判断该任务属于哪个 Skill。
如果不确定，优先使用 `quality_review_skill` 做检查。

## 8. 当前禁止事项

- 不执行最终收口。
- 不自动下单。
- 不改账户数据。
- 不编造持仓 / 成本 / 现金 / 挂单。
- 不把延迟行情当实时价格。
- 不把百分比回撤当技术支撑。
- 不把后台验收包当用户日报。
- 不跳过 Q0 质量任务。
- 不自动标绿 Q0-004。

## 9. 当前下一步

当前下一步不是继续生成日报，也不是最终收口。

当前下一步是：

等待 ChatGPT 验收或按用户指令重新生成：

`G:\我的云端硬盘\AI_Investment_System\reports\validation\q0_004_short_term_price_validation_package_v2.md`

在用户指示前，不主动执行 Q0-004。
