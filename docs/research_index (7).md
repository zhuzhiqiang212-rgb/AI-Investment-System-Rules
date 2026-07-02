# research_index.md
# V6研报索引 | 最后更新: 2026-06-16 JST
# RESEARCH体系第一阶段完成（ChatGPT V6裁决）

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
| RESEARCH-004 | 事件总控 | FOMC事件总控专题 | **Published(Beta-1)** | research_drafts/RESEARCH-004.md | FOMC声明发布后自动失效（预计2026-06-18）| B75CA3C5... |

## 当前固定入口

01_最新研报.pdf = RESEARCH-004《FOMC事件总控专题》
  路径: 桌面\股票分析与研究\01_最新研报.pdf
  大小: 239,291 bytes（234KB）
  SHA256: B75CA3C5287D21E486AD89B1AB7F8AC08E4FED778D9B53BFD00D6AB08EDD0993

## 日报引用规范（ChatGPT V6裁决，2026-06-16）

日报引用RESEARCH-004时，只能写：
  "见RESEARCH-004《FOMC事件总控专题》，有效期至FOMC声明发布；
   所有动作为候选框架，执行前需实时价格、账户确认、用户最终确认。"

禁止：将候选动作写成执行指令
禁止：日报直接列出止损/加仓数量作为当日动作

## FOMC后必须执行《RESEARCH-004事件验证复盘》

FOMC声明发布后，必须复盘：
  实际情景：偏鸽/中性/偏鹰
  RESEARCH-004判断是否命中
  A级/B级/防守模式是否正确
  MSTR、软银、NVDA、东京海上动作框架是否有效
  是否需要更新RESEARCH-002/003状态

## P1治理债务（Open，不影响主线）

| BUG | 描述 | 状态 |
|-----|------|------|
| BUG-005 | GitHub RESEARCH_ENGINE_STANDARD仍是V1.1 | Open |
| BUG-006 | GitHub research_index仍是旧版单状态体系 | Open |
| BUG-016 | 实时价格刷新机制缺失（已部分修复：加入距当前时间字段）| Open/P1 |

## RESEARCH体系第一阶段完成状态

RESEARCH-001: Closed（Expired）
RESEARCH-002: Published(Beta-1)（有效）
RESEARCH-003: Published(Beta-1)（有效）
RESEARCH-004: Published(Beta-1)（有效，FOMC后自动失效）

下一步：等待FOMC结果→《RESEARCH-004事件验证复盘》
禁止启动RESEARCH-005（FOMC前）
