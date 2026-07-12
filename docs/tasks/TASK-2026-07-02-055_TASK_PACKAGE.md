# TASK-2026-07-02-055 根治数据降级：建统一分时段实时取价函数

【总则对照】
第一条：数据服务证据链，不从持仓反推。
第六条：取价按市场与时段现算，返回价格、时间戳、市场状态和使用字段；取不到则FAIL，不降级不臆造。

## 目标
新建 scripts/realtime_price.py，提供 get_realtime_price(code)统一取价函数和命令行测试。

## 安全边界
只读 OpenD 行情；不创建交易上下文；不下单；不发布；不改其它生产脚本。

## 验收
- US.NVDA、US.MSFT能根据美股市场状态选择 pre_price / last_price / after_price / overnight_price。
- JP.6857、JP.9984取 last_price。
- CC.BTCUSD、CC.ETHUSD取 last_price。
- 每条返回 code、price、data_date、data_time、market_state、used_field、status。
- 写完重读 UTF-8，问号计数为0，替换字符计数为0。
