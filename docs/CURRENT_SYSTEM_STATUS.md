# CURRENT_SYSTEM_STATUS

# 当前系统状态

## 当前阶段

质量目标任务阶段。

## 工程体系状态

GitHub / Skill 已建立，本地 Git 已初始化。

说明：Git 已安装在标准路径，当前终端可能需要重启或刷新 PATH 后才能直接输入 `git`。本地 `.git` 已创建；未设置 remote；未推送 GitHub。

## 当前质量任务

Q0-004 短线价格指导质量 V2，待 ChatGPT 验收。

## 已通过质量任务

- Q0-001 用户日报总判断质量
- Q0-002 四账户执行卡质量
- Q0-003 标的分层质量

## 暂停事项

- 最终收口暂停
- Q0-004 后续执行暂停，除非用户明确要求继续

## 用户当前要求

先验证 GitHub / Skill 是否能承接上下文和右侧 Codex 对话框。

## 下一步

等待 ChatGPT 验收本承接测试。

## 当前用户主入口

START_HERE.html → reports/daily/user_readable_daily_report.html

## 当前禁止事项

- 不允许最终收口
- 不允许自动下单
- 不允许延迟行情直接交易
- 不允许未通过质量目标就进入日常使用模式
- 不允许自动标绿 Q0-004

## Claude / Cursor / Codex 接手说明

任何新 AI 或新工具接手前，必须先读取：

1. README.md
2. docs/CURRENT_SYSTEM_STATUS.md
3. docs/ROLE_SEPARATION_RULES.md
4. skills/quality_review_skill.md
5. system/quality_goal_task_status.json
6. START_HERE.html
7. reports/daily/user_readable_daily_report.html
