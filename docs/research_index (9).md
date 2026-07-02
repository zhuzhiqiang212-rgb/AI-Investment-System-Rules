# research_index.md
# V6研报索引 | 最后更新: 2026-06-16 JST
# RESEARCH体系第一阶段：Conditional Pass
# 用户最终验收：Pending（BUG-018 Open）

---

## 状态定义（六状态体系，V1.3）

| 状态 | 含义 | 日报可引用？|
|------|------|-----------|
| Draft | 草稿中 | 否 |
| Review | 待ChatGPT V6审阅 | 否 |
| Published Failed | 发布流程失败 | 否 |
| Published(Beta-1) | WPS验收通过+ChatGPT V6批准 | 是 |
| Expired | 已过有效期 | 否，禁止引用 |
| Archived | 已归档 | 否 |

---

## 研报索引

| 编号 | 类型 | 主题 | 状态 | GitHub草稿 | 有效期 | PDF SHA256 |
|------|------|------|------|-----------|--------|-----------|
| RESEARCH-001 | 事件专题 | BOJ议息专题_2026-06-16 | **Expired/Closed** | research_drafts/RESEARCH-001.md | BOJ后已失效 | B8BEA75E... |
| RESEARCH-002 | 个股深度 | MSTR风险处置专题 | **Published(Beta-1)** | research_drafts/RESEARCH-002.md | BTC突破$110K或跌破$90K | CCA3F7BF... |
| RESEARCH-003 | 个股深度 | 软银9984止盈与再配置专题 | **Published(Beta-1)** | research_drafts/RESEARCH-003.md | 用户完成止盈或软银跌破成本价 | FB525C22... |
| RESEARCH-004 | 事件总控 | FOMC事件总控专题 | **Published(Beta-1)** | research_drafts/RESEARCH-004.md | FOMC声明发布后自动失效 | B75CA3C5... |

---

## 当前固定入口

01_最新研报.pdf = RESEARCH-004《FOMC事件总控专题》
  路径: 桌面\股票分析与研究\01_最新研报.pdf
  大小: 239,291 bytes（234KB）
  SHA256: B75CA3C5287D21E486AD89B1AB7F8AC08E4FED778D9B53BFD00D6AB08EDD0993

---

## RESEARCH体系第一阶段状态

正确表述：
  RESEARCH体系第一阶段主体完成，
  技术链路通过，研报分析通过，发布流程通过，
  但用户决策验收未完全通过（BUG-018 Open），
  进入下一阶段修复BUG-018。

禁止写：最终通过 / 正式关闭

---

## BUG清单（当前Open）

| BUG | 描述 | 优先级 | 状态 |
|-----|------|--------|------|
| BUG-005 | GitHub RESEARCH_ENGINE_STANDARD仍是V1.1 | P1 | Open |
| BUG-006 | GitHub research_index仍是旧版单状态体系 | P1 | Open |
| BUG-016 | 实时价格刷新机制缺失（已部分修复）| P1 | Open |
| BUG-017 | 重大事件自动驱动缺失 | P0 | Open |
| **BUG-018** | **决策清晰度不足：用户看完研报仍不确定今天具体做什么** | **P0** | **Open** |

---

## BUG-018详情

名称：决策清晰度不足
优先级：P0
状态：Open（不关闭，直到用户验收通过）

问题：
  用户看完RESEARCH-004后，仍需自己推导"今天到底做什么"。
  研报提供情景框架，但缺少"今日唯一动作"转译层。
  日报与研报之间没有自动衔接。

修复方案：
  建立00B_今日总控页.pdf（独立入口）
  每天合并日报数据+有效研报状态→输出今日唯一动作
  必须回答：今天做什么 / 今天不能做什么 / 风险第一名 / 机会第一名 / 下一动作

关闭条件：
  00B_今日总控页建立
  用户看完后明确确认"今天该做什么"
  ChatGPT V6验收通过

---

## FOMC后必须执行

FOMC声明发布后（预计2026-06-18），立即触发：
  《RESEARCH-004事件验证复盘》

复盘检查项：
  1. 实际情景：偏鸽/中性/偏鹰
  2. RESEARCH-004命中率
  3. RESEARCH-002（MSTR）框架有效性
  4. RESEARCH-003（软银）框架有效性
  5. NVDA进攻窗口判断是否有效
  6. MSTR路径B/C是否正确
  7. 软银25%止盈框架是否合理

---

## 下一阶段任务优先级

P0（FOMC后立即）：
  1. 《RESEARCH-004事件验证复盘》
  2. 建立00B_今日总控页.pdf（修复BUG-018）

P1（之后）：
  3. RESEARCH-002/003/004结论写回日报（规范引用格式）
  4. SKILL-AUDIT + KNOWLEDGE-GOVERNANCE
     含BUG-005/006/016/017/018统一修复

---

## 补充规则（ChatGPT V6 2026-06-16补充）

以后用户中途提出补充意见：
  必须自动合并到上一条待执行指令
  禁止产生新的平行任务
  必须输出"合并后的完整执行版本"

---

## 禁止事项（持续生效）

禁止：启动RESEARCH-005
禁止：新增研报正文
禁止：扩展研究范围
禁止：把候选动作改成交易指令
禁止：在BUG-018关闭前写"RESEARCH体系第一阶段最终关闭"
