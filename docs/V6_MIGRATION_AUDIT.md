# V6_MIGRATION_AUDIT
# AI投研总控台 V6 知识库迁移审计

生成时间: 2026-06-14 JST
审计人: Claude
目标: 提取长期有效知识资产，迁移至 V6 共享知识库

---

## 一、保留（必须迁移到V6）

### 策略引擎文档（docs/）
| 文件 | 价值 | 迁移优先级 |
|------|------|-----------|
| cycle_positioning_engine_v1.md | 周期定位核心规则 | P0 |
| asset_allocation_engine_v1.md | 资产配置矩阵+硬上限 | P0 |
| buy_trigger_engine_v1.md | 四账户买入触发规则 | P0 |
| position_sizing_engine_v1.md | 仓位计算+回撤压缩 | P0 |
| take_profit_system_v1.md | 分批止盈+不止盈条件 | P0 |
| strategy_attribution_system_v1.md | 归因框架+模块责任 | P0 |
| daily_decision_briefing_v1.md | 简报格式规范 | P0 |

### 治理制度文档（docs/）
| 文件 | 价值 | 迁移优先级 |
|------|------|-----------|
| SKILL_GUARD_RULE.md | 角色边界+拦截规则 | P0 |
| THREAD_HANDOFF_RULE.md | 线程移交+三元组规则 | P0 |
| SYSTEM_GOVERNANCE_MANUAL.md | 治理总索引 | P0 |
| AI_PROJECT_GOVERNANCE_V2.md | 最高制度 | P0 |
| governance_v2_addendum_*.md | 补充制度 V2-ADDENDUM-003 | P0 |

### 工具文件（docs/）
| 文件 | 价值 | 迁移优先级 |
|------|------|-----------|
| SYSTEM_INDEX.md | 唯一入口索引 | P0 |
| daily_briefing_template_v1.md | 每日填写模板 | P0 |
| trade_record_log_v1.md | 交易记录日志 | P0 |
| monthly_return_tracking_v1.md | 月度收益追踪 | P0 |
| MASTER_GOAL_LIST_V1.md | 目标清单 | P1 |

### 自动化脚本（scripts/）
| 文件 | 价值 | 迁移优先级 |
|------|------|-----------|
| auto_briefing.py | 核心日报生成引擎 | P0 |
| daily_data_fetch.py | 数据获取+Binance BTC | P0 |
| governance_runtime.py | Skill Gate强制入口 | P0 |
| skill_gate.py | 违规拦截+日志 | P0 |

---

## 二、合并（存在重复内容需合并）

| 重复内容 | 现有文件 | 合并方案 |
|---------|---------|---------|
| 四报表模板 | latest_*.md×4 + daily_briefing_template | 以daily_briefing_template为主，latest_*为输出 |
| 周期判断规则 | cycle_positioning_engine + step1_cycle()代码 | 规则文档为权威，代码为实现 |
| 验收包格式 | 20+个task_validation_package | 合并为03_TASK_STANDARD.md |
| 用户确认边界 | 散落在各引擎文档中 | 统一收录到01_INVESTMENT_RULES.md |

---

## 三、废弃（已过期或无价值）

| 文件/类别 | 废弃原因 |
|---------|---------|
| task-*_validation_package.md（20+份） | 历史执行记录，非知识资产 |
| V4_*系列文件 | V4旧版本，已被V6体系替代 |
| P1/P2/P3_IMPLEMENTATION_ACCEPTANCE.md | 历史验收记录 |
| skill_gate_failure_log.md | 运行日志，非规则 |
| user_side_mvp_walkthrough_test_v1.md | 一次性测试记录 |
| latest_onchain_structure_v4.md等v4数据文件 | 旧版本数据快照 |
| G06_BTC_SIGNAL_BLOCKED_NOTE.md | 临时诊断记录 |
