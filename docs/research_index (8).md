# research_index.md
# V6研报索引 | 最后更新: 2026-06-16 JST
# RESEARCH体系第一阶段完成（ChatGPT V6裁决）
# 新增：BUG-017 + 事件驱动自动触发规则

---

## 状态定义（六状态体系 + 事件管理状态，V1.3）

研报状态：
| 状态 | 含义 | 日报可引用？|
|------|------|-----------|
| Draft | 草稿中 | 否 |
| Review | 待ChatGPT V6审阅 | 否 |
| Published Failed | 发布流程失败 | 否 |
| Published(Beta-1) | WPS验收通过+ChatGPT V6批准 | 是 |
| Expired | 已过有效期 | 否，禁止引用 |
| Archived | 已归档 | 否 |

事件状态（新增）：
| 状态 | 含义 |
|------|------|
| Upcoming | T-3日内，预警已触发，研报待生成 |
| Active | 事件进行中，对应研报有效 |
| Review | FOMC/BOJ后，待事件验证复盘 |
| Expired | 事件已过，研报自动失效 |

---

## 研报索引

| 编号 | 类型 | 主题 | 状态 | 事件状态 | GitHub草稿 | 有效期 | PDF SHA256 |
|------|------|------|------|---------|-----------|--------|-----------|
| RESEARCH-001 | 事件专题 | BOJ议息专题_2026-06-16 | **Expired/Closed** | Expired | research_drafts/RESEARCH-001.md | BOJ后已失效 | B8BEA75E... |
| RESEARCH-002 | 个股深度 | MSTR风险处置专题 | **Published(Beta-1)** | Active | research_drafts/RESEARCH-002.md | BTC突破$110K或跌破$90K | CCA3F7BF... |
| RESEARCH-003 | 个股深度 | 软银9984止盈与再配置专题 | **Published(Beta-1)** | Active | research_drafts/RESEARCH-003.md | 用户完成止盈或软银跌破成本价 | FB525C22... |
| RESEARCH-004 | 事件总控 | FOMC事件总控专题 | **Published(Beta-1)** | **Active→Review（FOMC后）** | research_drafts/RESEARCH-004.md | FOMC声明发布后自动失效 | B75CA3C5... |

---

## 日报引用规范（ChatGPT V6裁决）

引用RESEARCH-004时，日报只能写：
  "见RESEARCH-004《FOMC事件总控专题》，有效期至FOMC声明发布；
   所有动作为候选框架，执行前需实时价格、账户确认、用户最终确认。"

禁止：将候选动作写成执行指令
禁止：日报直接列出止损/加仓数量作为当日动作

---

## FOMC后必须执行《RESEARCH-004事件验证复盘》

FOMC声明发布后（预计2026-06-18），立即触发：
  实际情景：偏鸽/中性/偏鹰
  RESEARCH-004判断命中率
  A级/B级/防守模式是否正确
  MSTR/软银/NVDA/东京海上框架有效性
  是否需要更新RESEARCH-002/003状态
  是否需要生成新研报（RESEARCH-005）

---

## BUG清单（当前Open）

| BUG | 描述 | 优先级 | 状态 |
|-----|------|--------|------|
| BUG-005 | GitHub RESEARCH_ENGINE_STANDARD仍是V1.1 | P1 | Open |
| BUG-006 | GitHub research_index仍是旧版单状态体系 | P1 | Open |
| BUG-016 | 实时价格刷新机制缺失（已部分修复：加入距当前时间字段）| P1 | Open |
| **BUG-017** | **重大事件自动驱动缺失（BOJ由用户提醒，非系统主动驱动）** | **P0** | **Open** |

---

## BUG-017详情（ChatGPT V6登记，2026-06-16）

名称：重大事件自动驱动缺失
优先级：P0
状态：Open

问题：BOJ事件由用户提醒，而非系统主动驱动。以后禁止重大事件靠用户提醒。

事件驱动触发规则（V6永久制度）：

适用事件：
  BOJ / FOMC / CPI / PCE / 非农 / 三巫日
  核心持仓财报 / 重大政策 / 重大地缘事件
  BTC重大事件 / 浮盈>50% / 浮亏<-30%

T-3日：自动预警，日报显示事件名称/日期/影响标的/是否需要研报
T-2至T-1日：事件等级★★★★以上→自动触发专题研报，不等待用户提醒
T日：日报置顶事件总控区，回答今天看什么/偏鸽/中性/偏鹰条件/候选动作
T+1日：自动触发事件验证复盘，检查情景命中/研报有效性/状态更新/研报关闭

修复方案：
  需在auto_briefing.py或日历模块中接入事件日历
  T-3日自动生成事件预警并写入日报事件区
  T-2日★★★★以上事件自动触发Claude生成研报
  T+1日自动触发复盘任务
处理时机：KNOWLEDGE-GOVERNANCE+SKILL-AUDIT统一处理

---

## RESEARCH体系第一阶段完成

RESEARCH-001: Closed（Expired）
RESEARCH-002: Published(Beta-1)（Active）
RESEARCH-003: Published(Beta-1)（Active）
RESEARCH-004: Published(Beta-1)（Active，FOMC后→Review→Expired）

下一步：等待FOMC结果（预计2026-06-18 JST）
→《RESEARCH-004事件验证复盘》
→ 之后：SKILL-AUDIT + KNOWLEDGE-GOVERNANCE

禁止：FOMC前启动RESEARCH-005
禁止：自动交易
禁止：将候选动作写成执行指令
