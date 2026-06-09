# Role Matrix Audit V1

状态：PASS
执行人：Codex
预检人：Claude
最终验收人：ChatGPT / AI投研总控台 V4
发给谁：ChatGPT / AI投研总控台 V4

## 角色矩阵审计结论

当前 AI 投研系统涉及 Claude、Codex、Cursor、ChatGPT、Skills、GitHub、Google Drive、用户。系统必须防止重复执行、互相覆盖、职责混乱和生成者自验。

## 角色职责矩阵

| 角色 | 主责 | 权限 | 禁止事项 |
|---|---|---|---|
| ChatGPT / AI投研总控台 V4 | 最终验收、质量判定、是否标绿/收口 | 审核验收包、输出 PASS/PARTIAL/FAIL、给下一步唯一动作 | 不得跳过用户满意度；不得用结构检查替代最终质量判断 |
| Claude | 指令设计、长文分析、预检、质量建议 | 输出设计、审计、预检结论和可执行指令 | 不写回 Drive；不最终验收；不改账户数据；不改投资结论 |
| Codex | 文件写入、脚本执行、日报生成、验收包生成 | 读写 Google Drive 项目文件、运行本地脚本、生成验证包 | 不最终验收；不自动下单；不未经确认改账户/投资结论；不自行标绿质量任务 |
| Cursor | OCR、PDF处理、自动化脚本、Dashboard开发、本地代码开发 | 开发工具和工程化流程 | 不改账户数据；不改投资结论；不最终验收；不标绿 Q0/Q1 质量任务 |
| Skills | 固化岗位手册和规则 | 定义规则、质量门槛、流程边界 | Skills 不直接执行操作；不得替代验收包 |
| GitHub | 规则/脚本/Skill 版本保险柜 | 保存 README、docs、rules、skills、scripts、templates | 不保存日报、验收包、账户截图、输入资料、隐私文件 |
| Google Drive | 资料、日报、验收包、历史归档仓库 | 保存 reports、accounts、inputs、validation | 不作为唯一代码版本保险柜 |
| 用户 | 最终满意确认和账户变化确认 | 确认账户是否变化、确认视觉体验、批准最终收口 | 不需要手动判断后台技术状态是否达标，系统应自检 |

## 关键风险

1. 生成者自验。
2. Claude/Codex/Cursor 职责重叠。
3. GitHub 未成为唯一规则源却被误称已启用。
4. Google Drive 文件存在但内容不可读。
5. 验收包路径、发给谁、下一步唯一动作不统一。
6. 用户日报被后台验收语言污染。
7. Dashboard 更新绕过 Skill Gate。
8. 账户快照和市场价格时效混淆。
9. C级代理或缺失数据冒充 A/B 证据。
10. 用户未满意前最终收口。

## 审计结论

Role Matrix Audit V1 要求所有正式任务必须明确：执行人、预检人、最终验收人、发给谁、验收包路径、下一步唯一动作、可直接执行指令。任何角色不得越权修改账户数据、投资结论或自行最终验收。

ROLE_MATRIX_AUDIT_READY: YES