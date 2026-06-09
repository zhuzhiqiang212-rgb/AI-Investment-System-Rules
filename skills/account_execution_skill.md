# Account Execution Skill

## Skill名称

Account Execution Skill

## 角色定位

负责把四账户持仓、风险、禁止动作、等待条件和人工确认项整理成逐账户、逐标的执行卡。

## 读取哪些文件

- reports/accounts/latest_account_snapshot.md
- reports/accounts/account_position_execution_matrix.md
- reports/accounts/latest_four_account_action_cards.md
- reports/daily/ticker_layering_decision_table.md
- data/market/latest_market_validation.md

## 不能做什么

- 不能自动下单。
- 不能修改账户持仓数据。
- 不能把公开延迟行情当作券商实时行情。
- 不能在缺数据时输出确定交易动作。
- 不能自行最终标绿或最终收口。

## 输出格式

- 四账户动作卡
- 逐标执行矩阵
- 风险升级/缓和条件
- 验收包

## 质量检查

- 是否有结论、证据、风险、动作、等待条件、失效条件。
- 是否标明数据缺口和人工确认项。
- 是否连接四账户、证据链和 PDCA。
- 是否避免口号式表达和只写“观察”。

## 失败时怎么处理

- 明确写失败原因。
- 标注缺失文件或数据缺口。
- 生成待修复验收包。
- 不推进下一任务，不自动标绿。
