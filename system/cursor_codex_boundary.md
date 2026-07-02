# Cursor 与 Codex 边界

## Cursor 负责

- OCR流程
- PDF处理
- 自动化脚本
- Dashboard开发
- GitHub工程维护
- 本地代码开发
- 文件处理工具开发

## Cursor 禁止

- 修改账户数据
- 修改投资结论
- 最终验收
- Q0任务标绿
- 自动下单
- 修改方向卡结论
- 修改风险卡结论

## Codex 负责

- Drive文件读取
- 报告生成
- 日报生成
- Direction Card
- Risk Card
- Execution Card
- Dashboard调用
- 验收包生成
- 系统任务执行

## Codex 禁止

- 最终验收
- 自动下单
- 未经确认修改账户数据
- 未经确认修改投资结论
- 自行标绿Q0任务

## 协作规则

| 场景 | Cursor | Codex | 验收 |
|---|---|---|---|
| OCR/PDF工具坏了 | 修脚本和工具 | 生成修复验收包 | ChatGPT / 用户 |
| 日报内容要重构 | 不直接改结论 | 生成用户日报和验收包 | ChatGPT / 用户 |
| Dashboard版面问题 | 可开发组件 | 写入Drive页面并生成验收包 | ChatGPT / 用户 |
| GitHub工程维护 | 维护代码结构 | 同步说明和验收包 | ChatGPT / 用户 |
| 账户数据变化 | 不改 | 只按用户确认资料写入 | 用户最终确认 |

## 红线

Cursor 与 Codex 都不能自动下单、不能最终收口、不能未验收标绿、不能编造账户数据。
