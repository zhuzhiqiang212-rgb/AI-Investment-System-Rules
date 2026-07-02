# V6 Knowledge Governance Architecture v1.0
# AI投研总控台 V6 知识治理架构

生成时间: 2026-06-14 JST
制定人: Claude / ChatGPT V6
审计依据: Phase 0A/0B/0C + 五份核心文件全文内容

---

# PHASE 0A：文件内容审计

## 00_SYSTEM_MANUAL.md

文件目标: 定义系统定位、模块职责、运行原则、统一规范
目录结构: 系统定位 / 模块职责（6层）/ 运行原则（5条）/ 统一规范 / 新模块继承规则
关键规则摘要:
  - 系统定位：有边界的决策辅助，不自动执行
  - 6层模块：数据层/分析层/决策层/输出层/治理层/归因层
  - 新模块继承规则：5条强制继承
来源资产: AI_PROJECT_GOVERNANCE_V2 + 各引擎文档 + auto_briefing.py逻辑

资产属性:
  Long-term Knowledge: YES（系统定位不随市场变化）
  Governance: YES（治理层描述）
  Workflow: YES（每日使用流程）
  Adaptation: NO
  Runtime: NO

审计结论:
  重复: 与03_TASK_STANDARD存在角色职责重叠（两份文件都定义了Claude/GPT/Codex边界）
  冲突: 无
  需要拆分: 建议将"模块职责"拆出为独立的ARCHITECTURE文档，避免MANUAL过重
  需要重构: NO，但需补充"研究框架"和"Prompt Templates"章节（当前缺失）

---

## 01_INVESTMENT_RULES.md

文件目标: 投资明鉴规则库，仓位/风险/买卖纪律/周期/归因
目录结构: 仓位管理 / 风险管理 / 买卖纪律 / 周期分析规则 / 归因原则
关键规则摘要:
  - 硬上限：美股50% / 日股30% / A股30% / 加密10% / 现金最低10%
  - 止损：单笔最大亏损账户净值3%
  - 4维周期判断：VIX/10Y美债/SPX/BTC
  - 最低样本：触发器10次 / 周期8次 / 单账户5笔
来源资产: buy_trigger_engine + position_sizing_engine + asset_allocation_engine + strategy_attribution_system

资产属性:
  Long-term Knowledge: YES（核心投资规则）
  Governance: YES（硬上限属于治理规则）
  Workflow: NO
  Adaptation: NO
  Runtime: NO

审计结论:
  重复: 归因原则（六模块）与04_TRADE_RECORD_STANDARD重复定义
  冲突: 无
  需要拆分: 建议将"周期分析规则"单独成文（CYCLE_ANALYSIS_RULES.md），因其可独立演进
  需要重构: 建议增加"研究方法论"章节（当前缺失）

---

## 02_REPORT_STANDARD.md

文件目标: 日报/周报/月报统一模板
目录结构: 日报标准（4份latest_*.md格式）/ 周报标准 / 月报标准
关键规则摘要:
  - 日报质量标准：4条（不矛盾/TRANSITION→观察/layer2两条/当日日期）
  - 周报：手动，每周五
  - 月报：monthly_return_tracking_v1.md
来源资产: auto_briefing.py + G-03/G-03B逻辑修复

资产属性:
  Long-term Knowledge: YES（报表结构）
  Governance: NO
  Workflow: YES（生成流程）
  Adaptation: YES（格式可随需求变化）
  Runtime: NO

审计结论:
  重复: 日报格式与auto_briefing.py代码中write_latest_cards()函数重复定义（规则在文档，实现在代码）
  冲突: 无
  需要拆分: NO
  需要重构: 建议增加"研究报告"标准（当前只有投资操作报表，缺乏研究成果报告模板）

---

## 03_TASK_STANDARD.md

文件目标: 任务包格式/验收标准/线程交接/角色边界
目录结构: 任务包格式 / 六阶段流程 / 准入规则 / 验收标准 / 三元组 / 接管自检 / 角色职责 / 线程定义
关键规则摘要:
  - 六阶段：PROPOSAL→APPROVAL→IMPLEMENTATION→PRE_ACCEPTANCE→FINAL_ACCEPTANCE→TASK_CLOSED
  - 准入5条：GOVERNANCE_SYNC + 自检 + TASK_PACKAGE + APPROVAL + governance_runtime
  - 角色边界：Claude/ChatGPT/Codex/用户各自职责和禁止
来源资产: AI_PROJECT_GOVERNANCE_V2 + SKILL_GUARD_RULE + THREAD_HANDOFF_RULE

资产属性:
  Long-term Knowledge: YES（协作流程是长期知识）
  Governance: YES（核心治理规则）
  Workflow: YES（六阶段流程即Workflow）
  Adaptation: NO
  Runtime: NO

审计结论:
  重复: 角色职责与00_SYSTEM_MANUAL中的模块职责存在重叠
        接管自检与SKILL_GUARD_RULE存在重叠
  冲突: 无
  需要拆分: 建议将"接管自检"和"线程定义"合并到SKILL_GUARD_RULE/THREAD_HANDOFF_RULE，避免三处定义同一内容
  需要重构: NO

---

## 04_TRADE_RECORD_STANDARD.md

文件目标: 交易记录/月度归因/收益跟踪规范
目录结构: 交易记录规范（16字段+4类未交易）/ 月度归因规范 / 收益跟踪规范 / 收益归因层级
关键规则摘要:
  - 16字段：进场填1-10，出场填11-16，月末填16
  - 六模块归因：方向/仓位/标的/执行/风险/现金
  - 触发G-10：连续3个月<2% / 任一月亏损>-5%
来源资产: strategy_attribution_system_v1.md + monthly_return_tracking_v1.md

资产属性:
  Long-term Knowledge: YES（记录格式）
  Governance: YES（样本规则是治理规则）
  Workflow: YES（填写时机是Workflow）
  Adaptation: NO
  Runtime: NO

审计结论:
  重复: 六模块归因与01_INVESTMENT_RULES归因原则重复
        样本规则与01_INVESTMENT_RULES最低样本规则重复
  冲突: 01_INVESTMENT_RULES归因六类 vs 04_TRADE_RECORD六模块：名称略有差异
        01: 周期定位/资产配置/买入触发/仓位计算/止盈规则/用户执行偏离
        04: 市场方向判断/仓位配置/标的选择/交易执行/风险控制/现金管理
        → 两套命名指向同一模块，存在轻微冲突
  需要拆分: NO
  需要重构: 建议统一归因模块命名（选一套，更新两处）

---

# PHASE 0B：迁移完整性审计

## 已迁移资产
| 资产 | 来源 | 状态 |
|------|------|------|
| 系统定位和边界原则 | 历次对话 + Governance V2 | ✅ 00_SYSTEM_MANUAL |
| 仓位/风险/买卖规则 | 策略引擎文档 | ✅ 01_INVESTMENT_RULES |
| 日报/周报/月报模板 | auto_briefing.py + 对话 | ✅ 02_REPORT_STANDARD |
| 任务包/治理流程 | Governance V2 + Addendum | ✅ 03_TASK_STANDARD |
| 交易记录/归因规范 | strategy_attribution + 对话 | ✅ 04_TRADE_RECORD_STANDARD |
| 策略引擎文档（7份） | docs/ | ✅ 保留，已在Drive |
| 治理制度文档（5份） | docs/ | ✅ 保留，已在Drive |
| 自动化脚本（4份） | scripts/ | ✅ 保留，GitHub同步 |

## 未迁移资产（缺口）
| 资产 | 来源 | 缺失原因 | 建议 |
|------|------|---------|------|
| Claude Skills定义 | 无 | 从未建立 | 需新建 |
| Prompt Templates | 无 | 从未定义 | 需新建 |
| Research Framework | 无 | 从未建立 | 需新建 |
| Research Methodology | 无 | 从未定义 | 需新建 |
| Agent Memory Schema | 无 | 从未定义 | 需新建 |
| Historical Research Assets | V4数据文件 | 废弃为V4旧版 | 需重建 |
| Codex Assets（完整规范） | governance_runtime.py | 仅有运行时，无完整规范 | 需补充 |
| MCP Workflow | 无 | 系统未接MCP | 暂缓 |
| Tool Registry | 无 | 系统未建立 | 暂缓 |
| Cursor Rules | 无 | 系统不用Cursor | 暂缓 |
| Gemini Instructions | 无 | 系统不用Gemini | 暂缓 |
| ChatGPT V6 Instructions | 无 | 未正式写入 | 需新建（本次任务输出） |
| Custom GPT配置 | 无 | 未建立 | 需新建 |

## 待确认资产
- GitHub仓库与Drive的同步策略（脚本已在Drive，是否同步到GitHub？）
- Claude Project知识库配置

## 无法迁移资产
- 聊天历史记录（仅保留规则和知识，不迁移对话）
- 实时市场数据快照（每日生成，不归档）

---

# PHASE 0C：知识缺口分析

## 五大标准完整性评估

| 标准 | 存在 | 完整性 | 缺失项 |
|------|------|-------|-------|
| SYSTEM_MANUAL | ✅ | 80% | 研究框架 / Prompt模板 / Architecture图 |
| INVESTMENT_RULES | ✅ | 85% | 研究方法论 / 宏观分析框架 |
| REPORT_STANDARD | ✅ | 70% | 研究报告模板 / 周报模板需完善 |
| TASK_STANDARD | ✅ | 90% | Codex完整规范 / Agent协同规范 |
| TRADE_RECORD_STANDARD | ✅ | 85% | 归因模块命名冲突需统一 |

## 缺失项（V6知识库缺口）
1. Claude Skills正式定义
2. Prompt Templates库
3. Research Framework（研究框架）
4. Research Methodology（研究方法论）
5. ChatGPT V6 Instructions
6. Agent Memory Schema
7. 归因模块命名统一

## 薄弱项
1. 02_REPORT_STANDARD缺乏研究报告模板
2. 00_SYSTEM_MANUAL缺乏系统架构图文字描述
3. 01_INVESTMENT_RULES缺乏宏观分析维度

## 重复项（需处理）
1. 归因六模块：01 vs 04（命名不一致）
2. 角色职责：00 vs 03（重复定义）
3. 接管自检：03 vs SKILL_GUARD_RULE（重复定义）
4. 样本规则：01 vs 04（重复定义）

## 冲突项（需裁定）
1. 归因模块命名冲突（裁定见下方）

---

# PHASE 1：20个核心问题裁定

1. Knowledge是否唯一SSOT: YES
   00-04五份文件是唯一权威来源，代码和指令均从此派生。

2. Governance是否共享: YES
   跨Claude/ChatGPT/Codex共享，不因模型不同而改变。

3. Workflow是否共享: YES
   六阶段流程适用于所有模型协作，不因模型不同而改变。

4. Skills是否只是Governance+Workflow实现形式: YES
   Claude Skills是Governance规则+Workflow步骤在Claude平台的适配产物。

5. Instructions是否属于Adaptation Layer: YES
   ChatGPT Instructions / Custom GPT Instructions都是L4适配层产物。

6. Codex Rules是否属于Adaptation Layer: YES
   Codex执行规范是L3 Workflow在Codex平台的适配实现。

7. Cursor Rules是否属于Adaptation Layer: YES（当前系统不使用，但架构上属于L4）

8. Gemini Instructions是否属于Adaptation Layer: YES（当前系统不使用，但架构上属于L4）

9. Skills与Instructions是否派生产物: YES
   均由L2 Governance + L3 Workflow派生，不独立维护。

10. 是否由Governance自动派生Rules: YES（目标）
    当前为手动同步，目标是建立自动派生链路。

11. 是否建立单向派生体系: YES
    Knowledge → Governance → Workflow → Adaptation → Runtime
    禁止反向修改。

12. 是否禁止双向维护: YES
    适配层（Skills/Instructions/Codex Rules）不得反向修改上层知识。

13. 新模型是否复用Governance与Workflow: YES
    新模型只需编写L4适配层，L1-L3完全复用。

14. Skills是否共享: NO（Skills是模型特定的适配产物，不跨模型共享）
    但Skills背后的Knowledge和Governance是共享的。

15. Governance是否共享: YES

16. Workflow是否共享: YES

17. Knowledge是否共享: YES

18. Prompt是否共享: 部分共享
    Prompt Templates属于L1 Knowledge，共享。
    系统Prompt属于L4 Adaptation，不跨模型共享。

19. Codex Rules是否共享: NO（Codex Rules是Codex特定适配）

20. Cursor Rules是否共享: NO（Cursor Rules是Cursor特定适配）

结论：
共享的是: Knowledge（L1）/ Governance（L2）/ Workflow（L3）
不共享的是: Skills/Instructions/Codex Rules/Cursor Rules（均为L4适配层产物）

---

# PHASE 2：企业级五层模型

```
L1 Core Knowledge（核心知识层）
  ├── SYSTEM_MANUAL（系统定位+原则）
  ├── INVESTMENT_RULES（投资明鉴规则）
  ├── REPORT_STANDARD（报表标准）
  ├── TASK_STANDARD（任务标准）
  ├── TRADE_RECORD_STANDARD（交易记录标准）
  ├── Research Framework（待建）
  ├── Research Methodology（待建）
  └── Prompt Templates（待建）

L2 Governance（治理层）
  ├── AI_PROJECT_GOVERNANCE_V2.md（最高制度）
  ├── governance_v2_addendum_*.md（补充制度）
  ├── SKILL_GUARD_RULE.md（守门规则）
  ├── THREAD_HANDOFF_RULE.md（线程移交）
  ├── SYSTEM_GOVERNANCE_MANUAL.md（治理索引）
  ├── Audit Rules（审计规则）
  └── Risk Control Rules（风险控制规则）

L3 Workflow（工作流层）
  ├── Agent Workflow（六阶段流程）
  ├── SOP（每日使用SOP）
  ├── Task Pipeline（PROPOSAL→TASK_CLOSED）
  ├── Tool Routing（数据获取→分析→输出）
  └── Agent Memory Schema（待建）

L4 Adaptation（适配层）
  ├── Claude Skills（Claude平台适配）
  ├── ChatGPT V6 Instructions（ChatGPT适配）
  ├── Codex Instructions（Codex适配）
  ├── Custom GPT配置（待建）
  └── [未来: Cursor Rules / Gemini Instructions]

L5 Runtime（运行时层）
  ├── governance_runtime.py（Skill Gate强制入口）
  ├── skill_gate.py（违规拦截）
  ├── daily_data_fetch.py（数据获取）
  ├── auto_briefing.py（核心引擎）
  ├── user_config.json（用户配置）
  └── auto_briefing_log.json（运行日志）
```

---

# PHASE 3：各平台职责边界设计

| 平台 | 层级 | 职责 | 禁止 |
|------|------|------|------|
| GitHub | L1+L3+L5 | 代码版本控制，脚本SSOT | 存储账户数据/密码 |
| Google Drive | L1+L2+L3+输出 | 知识文档/日报/记录 | 执行代码 |
| Claude Project | L1+L4 | 知识库+Skills适配 | 直接写入生产文件 |
| Claude Skills | L4 | Governance+Workflow的Claude实现 | 绕过Governance |
| ChatGPT V6 Instructions | L4 | APPROVAL+验收的行为规范 | 直接指挥Codex |
| Custom GPT | L4 | 特定用途的GPT适配 | 独立维护规则 |
| Codex | L4+L5 | IMPLEMENTATION执行 | 自行发起/自验 |
| MCP | L5 | 工具集成（待接入） | 绕过Governance |
| Tool Registry | L5 | 工具注册表（待建） | N/A |
| Agent Memory | L3+L5 | 记忆模式（待建） | N/A |

---

# PHASE 4：V6目录映射

```
L1 Knowledge → Google Drive docs/（00-04 + 策略引擎7份）
                Claude Project知识库
                GitHub docs/

L2 Governance → Google Drive docs/（治理制度5份）
                Claude Skills（守门规则实现）
                GitHub governance/

L3 Workflow   → Google Drive docs/（SYSTEM_INDEX + 工具文件）
                03_TASK_STANDARD.md
                GitHub workflow/

L4 Adaptation → Claude Project（Skills）
                ChatGPT V6 Instructions（本文档派生）
                Codex Instructions（governance_runtime.py体现）

L5 Runtime    → Google Drive scripts/（4份脚本）
                Google Drive data/（user_config.json）
                GitHub scripts/
```

---

# PHASE 5：文件级分类

| 文件 | 层级 | SSOT位置 | 属性 |
|------|------|---------|------|
| 00_SYSTEM_MANUAL.md | L1 | Drive | Long-term Knowledge |
| 01_INVESTMENT_RULES.md | L1+L2 | Drive | Long-term Knowledge + Governance |
| 02_REPORT_STANDARD.md | L1+L3 | Drive | Long-term Knowledge + Workflow |
| 03_TASK_STANDARD.md | L2+L3 | Drive | Governance + Workflow |
| 04_TRADE_RECORD_STANDARD.md | L1+L3 | Drive | Long-term Knowledge + Workflow |
| AI_PROJECT_GOVERNANCE_V2.md | L2 | Drive | Governance（最高制度） |
| SKILL_GUARD_RULE.md | L2 | Drive | Governance |
| THREAD_HANDOFF_RULE.md | L2+L3 | Drive | Governance + Workflow |
| cycle_positioning_engine_v1.md | L1 | Drive | Long-term Knowledge |
| asset_allocation_engine_v1.md | L1 | Drive | Long-term Knowledge |
| buy_trigger_engine_v1.md | L1 | Drive | Long-term Knowledge |
| position_sizing_engine_v1.md | L1 | Drive | Long-term Knowledge |
| take_profit_system_v1.md | L1 | Drive | Long-term Knowledge |
| strategy_attribution_system_v1.md | L1 | Drive | Long-term Knowledge |
| auto_briefing.py | L5 | Drive+GitHub | Runtime |
| daily_data_fetch.py | L5 | Drive+GitHub | Runtime |
| governance_runtime.py | L2+L5 | Drive+GitHub | Governance + Runtime |
| skill_gate.py | L2+L5 | Drive+GitHub | Governance + Runtime |
| user_config.json | L5 | Drive（本地） | Runtime（用户数据） |
| latest_*.md | 输出 | Drive | Runtime Output（非知识资产） |

---

# PHASE 6：协同架构

```
用户
 ↓ 确认/下单
Claude（L1知识 + L2治理 + L4适配）
 ↓ PROPOSAL
ChatGPT V6（L2治理验收 + L4适配）
 ↓ APPROVAL
Codex（L4适配 + L5运行）
 ↓ IMPLEMENTATION
governance_runtime.py（L5门控）
 ↓ 通过
auto_briefing.py（L5核心引擎）
 ↓ 输出
Google Drive reports/（日报输出）
 ↓ 更新
START_HERE.html（用户唯一入口）
```

跨模型共享层（L1-L3）：
  Claude / ChatGPT V6 / Codex 均遵守同一套
  Knowledge / Governance / Workflow

模型特定层（L4）：
  Claude：Skills（守门规则在Claude平台的实现）
  ChatGPT V6：Instructions（APPROVAL行为规范）
  Codex：执行边界规范（不自发起/不自验/governance_runtime前置）

---

# PHASE 7：最终治理结论

## SSOT设计
Knowledge SSOT: Google Drive docs/（00-04 + 策略引擎7份）
Governance SSOT: Google Drive docs/（治理制度5份）
Workflow SSOT: Google Drive docs/（工具文件 + 03_TASK_STANDARD）
Runtime SSOT: Google Drive scripts/ + GitHub（代码版本控制）
Output: Google Drive reports/（非SSOT，每日生成覆盖）

## Governance设计
- Governance跨模型共享（Claude/ChatGPT/Codex均遵守）
- 最高制度：AI_PROJECT_GOVERNANCE_V2.md
- 运行时执行：governance_runtime.py（不可绕过）
- 违规拦截：PV-003/PV-004/PV-006

## Workflow设计
- 六阶段流程跨模型共享（PROPOSAL→TASK_CLOSED）
- 每日SOP：auto_briefing.py → Y → 四报表更新
- 线程定义：主线程/维护线程，禁止混用

## Skills定位
- Skills是L4适配层产物
- Skills = L2 Governance规则在Claude平台的实现形式
- Skills不独立维护，由Governance派生
- Skills变更必须追溯到Governance变更

## Instructions定位
- ChatGPT V6 Instructions是L4适配层产物
- Instructions定义ChatGPT V6的APPROVAL行为规范
- Instructions不得与L2 Governance冲突
- Instructions变更须ChatGPT V6 + 用户双重确认

## Codex Rules定位
- Codex Rules是L4适配层产物
- Codex Rules = L3 Workflow在Codex平台的执行规范
- 核心规则：governance_runtime.py前置检查 / 禁止自发起 / 禁止自验

## 单向派生体系（最终裁定）
L1 Knowledge
  ↓（派生）
L2 Governance
  ↓（派生）
L3 Workflow
  ↓（派生）
L4 Adaptation（Skills / Instructions / Codex Rules）
  ↓（派生）
L5 Runtime（脚本 / 配置 / 日志）

禁止：L4/L5反向修改L1-L3
禁止：双向维护（任何层级的变更只能向下传播）

## 自动同步策略
当前：手动同步（Drive → Codex执行）
目标：Drive更新 → 自动触发Codex同步 → governance_runtime验证 → 生效
暂缓：MCP Workflow自动同步（待工具接入后建立）

## 审计策略
频率：每季度执行一次知识审计
触发：G-10策略迭代时同步审计
输出：V6_QUARTERLY_AUDIT.md（格式同V6_MIGRATION_AUDIT）

## 版本控制策略
L1-L3：语义版本号（v1.0 → v1.1 → v2.0）
L4：随L2/L3版本更新
L5：Git提交记录
变更必须：修改SSOT文件 → ChatGPT V6审批 → Codex执行 → 验收

## 新模型接入策略
步骤1: 读取 00_SYSTEM_MANUAL.md（L1）
步骤2: 读取 AI_PROJECT_GOVERNANCE_V2.md（L2）
步骤3: 读取 03_TASK_STANDARD.md（L3）
步骤4: 编写该模型的L4适配（Instructions/Rules）
步骤5: 接管自检四项输出YES
步骤6: ChatGPT V6确认准入

## 推荐方案
推荐: 单向派生体系 + Drive作为L1-L3的SSOT
推荐: Skills和Instructions均从Governance自动派生（目标态）
推荐: 归因模块命名统一（采用01_INVESTMENT_RULES的六分类名称）
推荐: 新建Research Framework和Prompt Templates（下一阶段）

## 不推荐方案
不推荐: Skills和Instructions独立维护（会导致与Governance漂移）
不推荐: 双向维护（L5的执行反馈绕过L1-L3直接修改规则）
不推荐: 多处定义同一规则（如归因六模块在01和04两处不一致定义）

---

# 归因模块命名冲突裁定

当前冲突：
  01_INVESTMENT_RULES: 周期定位错误/资产配置错误/买入触发错误/仓位计算错误/止盈规则错误/用户执行偏离
  04_TRADE_RECORD_STANDARD: 市场方向判断/仓位配置/标的选择/交易执行/风险控制/现金管理

裁定（采用01版本，因为更精确指向具体引擎）：
  统一使用：
  M1: 周期定位错误（对应 cycle_positioning_engine）
  M2: 资产配置错误（对应 asset_allocation_engine）
  M3: 买入触发错误（对应 buy_trigger_engine）
  M4: 仓位计算错误（对应 position_sizing_engine）
  M5: 止盈规则错误（对应 take_profit_system）
  M6: 用户执行偏离（非引擎问题，用户行为）

  04_TRADE_RECORD_STANDARD中的六模块表述需更新为M1-M6。

---

# 最终裁决

Knowledge是否唯一长期资产来源: YES
Governance是否跨模型共享: YES
Workflow是否跨模型共享: YES
Skills是否只是实现形式: YES
Instructions是否只是适配层产物: YES
Codex/Cursor Rules是否由治理层派生: YES
是否建立单向派生体系: YES
是否禁止双向维护: YES
新模型是否复用Governance与Workflow: YES

---

NEXT_OWNER  : ChatGPT V6
NEXT_ACTION : 确认架构裁定，将00-04五份文件+本架构文件
              导入ChatGPT V6知识库，建立Instructions适配层
NEXT_THREAD : AI投研总控台 + 正式日报生产
