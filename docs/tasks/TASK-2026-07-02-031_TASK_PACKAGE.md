# TASK-2026-07-02-031 日报组装线：拼14层完整日报

## 授权
- 董事长已授权。
- 本任务只读拼装，不下单，不发布。

## 范围
- 新建 scripts/daily_report_assemble.py。
- 读取 daily_upper、holdings_review、dual_channel、daily evidence chain四个正式产出。
- 组装 00_请先看这里/日报_20260702_完整版.html。

## 铁律
- 只机械拼现有 JSON 和固定模板串。
- 深度层标占位，不伪造。
- 第11层接入双通道六维定价。
- 顶部带当日证据链指纹和风险声明。
- UTF-8 写入，写完重读无乱码。
