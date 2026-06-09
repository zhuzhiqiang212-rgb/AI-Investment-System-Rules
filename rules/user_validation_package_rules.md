# 用户验收包机制规则

更新时间：2026-06-06 15:06:03 +09:00

## 1. 每个任务必须生成验收包

每个任务完成后，必须在以下目录生成验收包：

G:\我的云端硬盘\AI_Investment_System\reports\validation\

文件命名规则：

任务ID_英文任务名_validation_package.md

例如：

P1-024：short_term_price_guidance_validation_package.md

P1-027：data_gap_warning_validation_package.md

## 2. 验收包必须包含真实摘录

验收包不能只写 YES/NO。

必须包含：

* 任务结果摘要
* 真实内容摘录
* 路径清单
* HTML入口检查
* 质量检查
* 待ChatGPT验收结论

如果是价格、账户、资金流、证据链、PDCA类任务，必须摘录真实表格或卡片内容。

## 3. 用户上传提示规则

任务完成后，Codex 必须明确告诉用户：

请上传这个文件给 ChatGPT 验收：

G:\我的云端硬盘\AI_Investment_System\reports\validation\xxx_validation_package.md

不能只说“已完成”。

## 4. ChatGPT验收规则

ChatGPT验收后只有两种结果：

### 通过

输出：

* 通过原因
* 可以标绿
* 写回指令

### 不通过

输出：

* 不通过原因
* 不能标绿
* 修正指令
* 要重新上传哪个验收包

## 5. 写回规则

只有 ChatGPT 明确说“通过，可以标绿”后，Codex 才能写回：

status: passed
color: green
progress: 100
chatgpt_validated: true

否则必须保持：

status: pending_validation
color: yellow
chatgpt_validated: false

## 6. 防错规则

禁止：

* 没有验收包就标绿
* 只有摘要没有真实摘录
* 路径转义错误
* 自动跳下一任务
* next_task变成NONE
* 把ChatGPT未验收任务写成passed
* 用户上传错文件时强行验收
