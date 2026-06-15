# research_index.md
# V6研报索引
# 用途: 记录所有已生成研报的编号/名称/时间/状态/路径
# 生成者: Claude（每次生成研报时同步更新）
# SSOT: GitHub knowledge/research_index.md
# 注意: 本文件只存索引，不存研报正文
# 最后更新: 2026-06-15 JST（P0修复：BUG-003有效期 + BUG-006状态同步）

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
| RESEARCH-001 | 事件专题 | BOJ议息专题_2026-06-16 | 2026-06-15 JST | BOJ结果公布后失效（预计2026-06-16）| **Review / 待用户WPS截图确认** | 1w-ppc1TBS-ibeDwBCnkGSRk-npkzz_bT（v2.0 P0修复版）| 事件日历★★★★，未来3日内 | 待用户WPS打开确认后执行 |
| RESEARCH-002 | 个股深度 | MSTR风险处置专题 | 待生成 | 待定 | Draft | — | 持仓浮亏<-30% | 待生成后执行 |
| RESEARCH-003 | 个股深度 | 9984软银止盈与再配置专题 | 待生成 | 待定 | Draft | — | 持仓浮盈>+50% | 待生成后执行 |
| RESEARCH-004 | 事件专题 | FOMC专题 | 待生成 | FOMC结果公布后失效 | Draft | — | 事件日历★★★★★ | 待生成后执行 |

---

## RESEARCH-001 修复历史

| 版本 | 时间 | 状态 | 说明 |
|------|------|------|------|
| v1.0草稿 | 2026-06-15 JST | Published Failed | 初版，base64传输损坏，PDF7.5KB不可读 |
| v2.0 P0修复版 | 2026-06-15 JST | Review / 待用户WPS截图确认 | BUG-001数据时间戳 + BUG-003有效期 已修复；PDF已重发，等待用户WPS打开确认 |

---

## P0发布前检查清单（每次发布前必须确认）

- [ ] BUG-001：所有持仓价格标注数据时间戳，过期价格标【价格已过期】
- [ ] BUG-003：研报首部包含有效期表格（生效/失效/状态）
- [ ] BUG-005：GitHub SSOT已同步最新制度文件（RESEARCH_ENGINE_STANDARD V1.2）
- [ ] BUG-006：research_index已同步至GitHub
- [ ] 步骤3.5：两路径SHA256一致，文件>50KB
- [ ] 用户WPS打开截图确认可读

---

## GitHub同步说明

本文件SSOT在GitHub:
https://raw.githubusercontent.com/zhuzhiqiang212-rgb/AI-Investment-System-Rules/main/knowledge/research_index.md

每次研报状态变更后，Codex必须同步本文件至GitHub。

