# research_index.md
# V6研报索引 | 最后更新: 2026-06-16 JST
# SSOT: GitHub knowledge/research_index.md（BUG-006 Open，GitHub落后，不影响使用）

## 状态定义（六状态体系，V1.3）

| 状态 | 含义 | 日报可引用？|
|------|------|-----------|
| Draft | 草稿中 | 否 |
| Review | 待ChatGPT V6审阅 | 否 |
| Published Failed | 发布流程失败 | 否 |
| Published(Beta-1) | WPS验收通过+ChatGPT V6批准 | 是 |
| Expired | 已过有效期 | 否，禁止引用 |
| Archived | 已归档 | 否 |

## 研报索引

| 编号 | 类型 | 主题 | 状态 | GitHub草稿 | 有效期 | PDF SHA256 |
|------|------|------|------|-----------|--------|-----------|
| RESEARCH-001 | 事件专题 | BOJ议息专题_2026-06-16 | **Expired/Closed** | research_drafts/RESEARCH-001.md | BOJ结果公布后已失效 | B8BEA75E... |
| RESEARCH-002 | 个股深度 | MSTR风险处置专题 | **Published(Beta-1)** | research_drafts/RESEARCH-002.md | BTC突破$110K或跌破$90K | CCA3F7BF... |
| RESEARCH-003 | 个股深度 | 软银9984止盈与再配置专题 | **Published(Beta-1)** | research_drafts/RESEARCH-003.md | 用户完成止盈或软银跌破成本价 | FB525C22... |
| RESEARCH-004 | 事件专题 | FOMC专题 | Draft | — | FOMC结果公布后失效 | — |

## 当前固定入口

01_最新研报.pdf = RESEARCH-003《软银9984止盈与再配置专题》
  路径: 桌面\股票分析与研究\01_最新研报.pdf
  大小: 251,249 bytes
  SHA256: FB525C2293C98A45680CEBE04DEAEC70C1D72A6F9085C2B7F50AD695962DCE93

## P1治理债务（Open，不影响主线）

| BUG | 描述 | 状态 |
|-----|------|------|
| BUG-005 | GitHub RESEARCH_ENGINE_STANDARD仍是V1.1 | Open |
| BUG-006 | GitHub research_index仍是旧版单状态体系 | Open |

禁止要求用户手动修改GitHub，后续KNOWLEDGE-GOVERNANCE统一处理。

## BUG-014 Closed

建立research_drafts/目录，RESEARCH-003已完整验证新流程：
GitHub Raw → Codex fetch → PDF（未访问Drive私有文件）
