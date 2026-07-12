# TASK-2026-07-02-025｜14层经线上半截改由每日求证表生成 T4

## 授权
- 董事长已授权。
- 本任务只建设日报上半截链驱动生成脚本，只读，不下单，不发布。

## 范围
- 新建 `scripts/daily_upper_from_chain.py`。
- 读取 `data/evidence_chain/daily_YYYYMMDD.json`。
- 机械映射第1-7层，输出 `data/reports/daily_upper_YYYYMMDD.json`。
- 支持 `--demo` 输出 `data/reports/daily_upper_YYYYMMDD_DEMO.json`，标注 DEMO/非正式。

## 总则第四/六条落实
- 每日现算：每次读取当日求证表生成。
- 随链变：总闸、战略指向、节点类随求证表变化。
- 只搬证据：证据照搬求证表，空环节标“该环待填”。
- 带当日指纹：输出 evidence_source、total_gate、strategic_directions、generated_at、mode。

## 铁律
- UTF-8 写入，写完重读无乱码。
- 不生成新中文散文，不编造证据。
- 不下单，不发布。
- 不动 V0、账户、持仓、宪法、总则。
