# TASK-2026-07-02-029｜估值第二道关·在链驱动池上筛

## 授权
- 董事长已授权。
- 本任务只读链驱动机会池并做估值第二道关分类，不下单，不发布。

## 范围
- 新建 `scripts/opportunity_valuation_gate.py`。
- 读取 `data/opportunities/chain_opportunities_YYYYMMDD.json`。
- 输出 `data/opportunities/opportunity_gated_YYYYMMDD.json`。

## 总则第六条落实
- 读当日链驱动池，每日现算。
- 源池缺失即退出，不臆造。
- 不写死候选名单，只筛源池候选。
- 输出头部继承源池总闸档、激活节点与当日指纹。

## 铁律
- 只读只筛只分类，不深度估值。
- 财务字段取不到则标待补。
- 不下单，不发布，不动 V0、账户、持仓、宪法、总则。
- UTF-8 写入，写完重读无乱码。
