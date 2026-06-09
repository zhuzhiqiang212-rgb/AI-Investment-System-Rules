# Role Gap Closure Design V1

状态：PASS
执行人：Codex
预检人：Claude
最终验收人：ChatGPT / AI投研总控台 V4
发给谁：ChatGPT / AI投研总控台 V4

## 设计原则

1. 最小补位原则：只补当前系统中真实存在的职责空白，不新增无关 Worker，不扩大任何角色权限。
2. 生成者不能自验原则：任何由 Claude / Codex / Cursor 生成的内容，最终验收必须交给 ChatGPT / AI投研总控台 V4 或用户确认。
3. 用户满意前不得收口原则：结构检查通过不等于用户体验通过。
4. Drive 与 GitHub 分层原则：Google Drive 保存日报、验收包、历史报告、账户资料和输入资料；GitHub 保存规则、Skills、脚本、模板和工程结构。
5. 交易边界不可突破原则：所有账户动作、短线价格、风险提示均为投研参考。
6. 缺口可见原则：无法读取、无法 OCR、无法结构化、无法验证的数据，必须显示为缺口。

## 空白1-5 的完整设计

### 空白1：用户版日报内容质量最终责任人
主责：ChatGPT / AI投研总控台 V4。
为什么：用户版日报最终质量不能由生成者自验。
触发：生成或重写用户版日报正文、更新 dashboard 用户入口、用户反馈日报不好读或不能决策。
验收：Delta 卡、四账户唯一动作、五段证据结构、完整 Direction/Risk/Execution/Evidence Chain/PDCA、无后台验收语言挤占用户阅读。

### 空白2：Skill 运行时执行责任人
主责：Codex。
为什么：Skill 文件是静态规则，必须由执行脚本在关键写入点调用。
触发：任何脚本准备写入 dashboard.html 或用户版日报主入口。
验收：skill_gate.py 存在；FAIL 时阻断 dashboard 写入；失败日志生成；dashboard 修改时间不变。

### 空白3：OCR 与内容读取工程责任人
主责：Cursor。
为什么：OCR、PDF、PPT、截图、视频转文字和结构化提取属于工程工具链任务。
触发：文件层可见但内容层不可读；账户截图无法提取持仓、成本、市值、现金、挂单。
验收：可提取 OCR 文本；区分 OCR 文本与结构化数据；仍需人工确认的字段明确标注。

### 空白4：规则源版本责任人
主责：GitHub / Codex 工程执行；ChatGPT 最终验收。
为什么：Google Drive 是资料和报告仓库，GitHub 应承担规则、Skills、脚本、模板和工程结构的版本追踪。
触发：新增或修改 rules / skills / scripts / templates。
验收：README / docs / rules / skills / scripts 纳入 Git 候选；reports/daily、reports/validation、账户截图、输入资料被排除；未 push 前不得声称 GitHub 是唯一规则源。

### 空白5：任务交付闭环责任人
主责：Codex 执行；Claude 预检；ChatGPT 最终验收。
为什么：多 Worker 协作必须统一验收包、发给谁、下一步和唯一动作。
触发：任意正式任务完成。
验收：有验收包路径、真实存在、文件大小、最后修改时间、状态、执行人、预检人、最终验收人、发给谁、下一步唯一动作、可直接执行指令。

## 空白6-10 的最小补位

6. 数据缺口升级仲裁：主责 ChatGPT / AI投研总控台 V4。
7. 账户快照变化确认：主责 用户。
8. 短线价格参考价质量仲裁：主责 ChatGPT / 用户。
9. Dashboard 视觉体验最终确认：主责 用户。
10. 最终收口批准：主责 用户 + ChatGPT。

## 补位方案总表

| 空白编号 | 空白名称 | 主责 | 当前方案 |
|---:|---|---|---|
| 1 | 用户版日报内容质量最终责任人 | ChatGPT / AI投研总控台 V4 | 内容质量最终验收 |
| 2 | Skill 运行时执行责任人 | Codex | skill_gate.py 前置阻断 |
| 3 | OCR 与内容读取工程责任人 | Cursor | OCR 与结构化管线 |
| 4 | 规则源版本责任人 | GitHub + Codex | 本地 Git 到 GitHub 规则源演进 |
| 5 | 任务交付闭环责任人 | Codex / Claude / Cursor | 统一验收包字段与唯一动作 |
| 6 | 数据缺口升级仲裁 | ChatGPT | 按缺口规则仲裁 |
| 7 | 账户快照变化确认 | 用户 | 人工确认账户变化 |
| 8 | 短线价格参考价质量仲裁 | ChatGPT / 用户 | 区分强参考/弱参考/不出价 |
| 9 | Dashboard 视觉体验最终确认 | 用户 | 用户视觉验收优先 |
| 10 | 最终收口批准 | 用户 + ChatGPT | 明确指令后才收口 |

ROLE_GAP_CLOSURE_READY: YES