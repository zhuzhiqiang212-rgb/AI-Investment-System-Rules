# research_index.md
# V6研报索引
# 用途: 记录所有已生成研报的编号/名称/时间/状态/路径
# 生成者: Claude（每次生成研报时同步更新）
# SSOT: GitHub knowledge/research_index.md
# 注意: 本文件只存索引，不存研报正文
# 最后更新: 2026-06-15 JST（RESEARCH-001正式发布）

---

## 状态定义（四状态体系）

| 状态 | 含义 |
|------|------|
| Draft | 草稿，尚未提交验收 |
| Review | 已提交，等待ChatGPT V6验收 |
| Published | 正式发布，结论可写回日报 |
| Archived | 已归档，信息超期不再参考 |

**附加标注（Beta/Stable）：**
- Published (Beta-1)：正式可用，但模板仍在优化中
- Published (Stable)：模板已定稿，可作为标准模板

---

## 研报索引

| 编号 | 类型 | 主题 | 生成时间 | 状态 | Drive文件ID | 触发条件 | 结论写回日报 |
|------|------|------|---------|------|-----------|---------|------------|
| RESEARCH-001 | 事件专题 | BOJ议息专题_2026-06-16 | 2026-06-15 JST | **Published (Beta-1)** | 1vh4N-dxQhl8Ccytv7uW1NsyY-E1-MpXi | 事件日历★★★★，未来3日内 | 允许写回，BOJ后按情景执行 |
| RESEARCH-002 | 个股深度 | MSTR风险处置专题 | 待生成 | Draft | — | 持仓浮亏<-30%（-36.9%） | 待生成后执行 |
| RESEARCH-003 | 个股深度 | 9984软银止盈与再配置专题 | 待生成 | Draft | — | 持仓浮盈>+50%（+79.4%） | 待生成后执行 |
| RESEARCH-004 | 事件专题 | FOMC专题_2026-06-17 | 待生成 | Draft | — | 事件日历★★★★★，未来3日内 | 待生成后执行 |

---

## RESEARCH-001 发布说明

发布状态: Published (Beta-1)
发布时间: 2026-06-15 JST
审批人: ChatGPT V6
模板说明:
  本研报作为RESEARCH_ENGINE_V1第一份正式研报
  模板状态Beta-1：正式可用，继续优化
  三部分结构（风险/机会/行动）已验证可行
  事实标注体系（已核实/待核实/情景假设）已验证可行

结论摘要:
  BOJ前: SBI全部持有，不操作
  BOJ后偏鹰: 东京海上候选加仓~60股，软银候选减仓~410股
  BOJ后温和: 全部持有，等FOMC
  所有操作执行前: 实时行情+账户确认+用户最终确认

---

## RESEARCH-002 规划说明

主题: MSTR风险处置专题
触发原因: 富途持仓MSTR浮亏-36.9%（600股），属于高Beta深度亏损
核心问题:
  MSTR与BTC的相关性是否仍然成立
  $110止损位的依据是否充分
  是否应该止损/减仓/继续持有
  若BTC未能突破关键位，MSTR的出场计划
优先级: P0（账户最大单一风险）

---

## GitHub同步说明

本文件SSOT在GitHub:
https://raw.githubusercontent.com/zhuzhiqiang212-rgb/AI-Investment-System-Rules/main/knowledge/research_index.md

每次新研报生成后:
1. 更新本文件索引行
2. 同步至GitHub（由Codex执行）
3. ChatGPT V6通过Raw链接确认
