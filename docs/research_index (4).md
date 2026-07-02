# research_index.md
# V6研报索引
# 用途: 记录所有已生成研报的编号/名称/时间/状态/路径
# 生成者: Claude（每次生成研报时同步更新）
# SSOT: GitHub knowledge/research_index.md
# 注意: 本文件只存索引，不存研报正文
# 最后更新: 2026-06-16 JST（RESEARCH-001正式发布 Published(Beta-1)）

---

## 状态定义（五状态体系，V1.2生效）

| 状态 | 含义 | 日报可引用？|
|------|------|-----------|
| Draft | 草稿，Claude正在生成或修订中 | 否 |
| Review | 已提交ChatGPT V6审阅 | 否 |
| Published Failed | 发布流程失败（文件损坏/不可读）| 否 |
| Published (Beta-1) | 通过用户WPS可读验收 + ChatGPT V6批准 | 是 |
| Expired | 已过有效期，事件/时效已过 | 否，禁止引用 |
| Archived | 已归档，超期不再参考 | 否 |

---

## 研报索引

| 编号 | 类型 | 主题 | 生成时间 | 有效期 | 状态 | Markdown草稿Drive ID | 触发条件 | 结论写回日报 |
|------|------|------|---------|--------|------|---------------------|---------|------------|
| RESEARCH-001 | 事件专题 | BOJ议息专题_2026-06-16 | 2026-06-15 JST | BOJ结果公布后失效（预计2026-06-16）| **Published (Beta-1)** | 1w-ppc1TBS-ibeDwBCnkGSRk-npkzz_bT | 事件日历★★★★，未来3日内 | 允许写回日报，BOJ后按情景执行，价格须实时确认 |
| RESEARCH-002 | 个股深度 | MSTR风险处置专题 | 待生成 | 待定 | Draft | — | 持仓浮亏<-30% | 待生成后执行 |
| RESEARCH-003 | 个股深度 | 9984软银止盈与再配置专题 | 待生成 | 待定 | Draft | — | 持仓浮盈>+50% | 待生成后执行 |
| RESEARCH-004 | 事件专题 | FOMC专题 | 待生成 | FOMC结果公布后失效 | Draft | — | 事件日历★★★★★ | 待生成后执行 |

---

## RESEARCH-001 发布说明

发布状态: **Published (Beta-1)**
发布时间: 2026-06-16 JST
审批人: ChatGPT V6
用户验收: PASS（WPS打开，中文正常，有效期可见，价格过期标识可见）

验收通过项:
  ✅ 有效期机制（BUG-003）：第一页有效期表格可见
  ✅ 数据时间戳（BUG-001/BUG-007）：2026-06-15 01:23 JST标注可见
  ✅ 价格过期标识：6,472日元【价格已过期】可见
  ✅ 用户价格差异说明：7,139日元差异已写入
  ✅ WPS中文正常显示：PASS
  ✅ PDF大小：193KB（步骤3.5 PASS）

候选结论（已允许写回日报SBI账户动作区）:
  BOJ前：全部持有，不操作
  BOJ后偏鹰：东京海上候选加仓约10%，软银候选减仓约10%
  BOJ后温和：全部持有，等FOMC
  ⚠️ 所有价格须以实时行情为准，研报价格已过期

遗留问题:
  BUG-013：实时价格刷新缺失（P2，下阶段优化）
  BUG-013说明：当前已知价格过期，但系统无法自动拉取最新持仓快照在发布前刷新

---

## 待修复漏洞清单（简版）

| BUG | 描述 | 优先级 | 阶段 |
|-----|------|--------|------|
| BUG-002 | 01_最新研报.pdf固定入口缺失 | P1 | 明日优先 |
| BUG-004 | 日报引用研报须含有效期 | P1 | RESEARCH-002前 |
| BUG-005 | GitHub RESEARCH_ENGINE_STANDARD未同步V1.2 | P1 | 待解决 |
| BUG-006 | GitHub research_index未同步五状态版 | P1 | 待解决 |
| BUG-008 | 研报引用自动失效机制 | P1 | RESEARCH-002前 |
| BUG-009 | Drive重复制度文件（已部分清理）| P1 | 观察 |
| BUG-013 | 实时价格刷新缺失 | P2 | 后续优化 |

---

## GitHub同步说明

本文件SSOT在GitHub（当前待同步，GitHub仍为旧版）:
https://raw.githubusercontent.com/zhuzhiqiang212-rgb/AI-Investment-System-Rules/main/knowledge/research_index.md

GitHub同步问题（BUG-005/006）正在处理中，不影响已发布研报的使用。
