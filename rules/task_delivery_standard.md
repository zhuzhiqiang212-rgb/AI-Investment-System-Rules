# 任务交付统一标准

## 目标

统一 ChatGPT、Claude、Codex、Cursor、Skills 的任务交付格式，防止任务完成后缺少验收包、下一步不清楚、发给谁不清楚、唯一动作不清楚。

## 所有任务结束必须输出

【状态】
PASS / PARTIAL / FAIL

【执行人】
Codex / Cursor / Claude / Skill / 其他

【预检人】
右侧 Codex / Claude / 无

【最终验收人】
ChatGPT / AI投研总控台 V4 / 用户

【发给谁】
例如：发给 ChatGPT 验收；发给 Codex 修复；发给用户视觉确认。

【验收包】
必须写明验收包路径。若本任务是只读预检，必须写明“使用原始验收包，不新建预检包”。

【下一步】
写清楚下一步做什么。

【唯一动作】
只能有一个优先动作，避免多个 AI 同时执行不同方向。

【可直接执行指令】
给出用户可以复制给下一位 Worker 的明确指令。

## 强制规则

- 没有验收包 = 任务未完成。
- 没有发给谁 = 任务未完成。
- 没有唯一动作 = 任务未完成。
- 没有可直接执行指令 = 任务未完成。
- 未经 ChatGPT / 用户确认，不得标绿。
- 预检 PASS 不是最终验收 PASS。
- 生成者不能自己最终放行。

## 推荐完成回复模板

```text
【状态】PASS / PARTIAL / FAIL
【执行人】Codex
【预检人】右侧Codex / Claude / 无
【最终验收人】ChatGPT / AI投研总控台 V4
【发给谁】ChatGPT
【验收包】G:\我的云端硬盘\AI_Investment_System\reports\validation\xxx.md
【下一步】上传验收包给ChatGPT最终验收
【唯一动作】等待ChatGPT验收
【可直接执行指令】请验收：xxx.md，并判断是否可以标绿。
```
