# TASK-2026-07-02-030 机会池改双通道六维定价

## 授权
- 董事长已授权。
- 本任务只读机会池、持仓库与行情，生成双通道六维定价骨架，不下单，不发布。

## 范围
- 新建 scripts/opportunity_dual_channel.py。
- 读取 data/opportunities/opportunity_gated_YYYYMMDD.json 的 A 类机会。
- 读取 data/accounts/unified_holdings_latest.json。
- 输出 data/opportunities/dual_channel_YYYYMMDD.json。

## 总则第六条落地
- 每日现算：读取当日估值关与持仓库。
- 随链变：继承源池总闸与激活节点。
- 带指纹：记录源池、总闸、节点、六维状态。
- 动态占位：估值维与基本面催化维写 source、refresh、status、value=null。

## 铁律
- 只读只算，不替人下换仓结论。
- 不下单，不发布。
- 不动 V0、账户、持仓、宪法、总则。
- UTF-8 写入，写完重读无乱码。
