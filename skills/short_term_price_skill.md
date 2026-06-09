# Short Term Price Skill

## Skill名称

Short Term Price Skill

## 角色定位

负责生成短线价格参考区间、价格来源、适用条件、失效条件和账户边界。

## 读取哪些文件

- reports/trading/short_term_price_quality_table.md
- reports/trading/technical_level_generator.md
- reports/validation/technical_price_data_gap_list.md
- data/market/latest_market_validation.md
- reports/accounts/account_position_execution_matrix.md

## 不能做什么

- 不能自动下单。
- 不能修改账户持仓数据。
- 不能把公开延迟行情当作券商实时行情。
- 不能在缺数据时输出确定交易动作。
- 不能自行最终标绿或最终收口。

## 输出格式

- 强参考 / 弱参考 / 暂不出价三层价格卡
- 技术位缺口清单
- 价格逻辑验收包

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
