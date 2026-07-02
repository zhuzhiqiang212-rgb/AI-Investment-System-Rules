# TASK PACKAGE
# TASK-2026-06-10-013

TASK_ID: TASK-2026-06-10-013
任务名称: ALL_ENGINES_DRIVE_DEPLOYMENT_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 实施类
影响范围: docs/（写入10份文件）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO

---

## 任务目标

将所有已批准的策略设计文档和工具模板
一次性写入 Drive docs/ 正确路径。

解决当前核心缺口：
所有策略设计停在 TASK_PACKAGE 批准阶段，
docs/ 目录下没有任何可供用户查表的文件。
本任务完成后，用户第一次可以打开 Drive
找到真实可用的工具文件。

---

## 待写入文件清单（10份）

Codex 须从对应 TASK_PACKAGE 中读取内容，
生成以下文件并写入 docs/：

文件1: buy_trigger_engine_v1.md
  内容来源: TASK-2026-06-10-005 REV-A
  Drive路径: docs/buy_trigger_engine_v1.md

文件2: position_sizing_engine_v1.md
  内容来源: TASK-2026-06-10-006 REV-A
  Drive路径: docs/position_sizing_engine_v1.md

文件3: take_profit_system_v1.md
  内容来源: TASK-2026-06-10-007 REV-A
  Drive路径: docs/take_profit_system_v1.md

文件4: cycle_positioning_engine_v1.md
  内容来源: TASK-2026-06-10-008 REV-A
  Drive路径: docs/cycle_positioning_engine_v1.md

文件5: asset_allocation_engine_v1.md
  内容来源: TASK-2026-06-10-009 REV-A
  Drive路径: docs/asset_allocation_engine_v1.md

文件6: strategy_attribution_system_v1.md
  内容来源: TASK-2026-06-10-010 REV-A
  Drive路径: docs/strategy_attribution_system_v1.md

文件7: daily_decision_briefing_v1.md
  内容来源: TASK-2026-06-10-011 REV-A
  Drive路径: docs/daily_decision_briefing_v1.md

文件8: daily_briefing_template_v1.md
  内容来源: TASK-2026-06-10-012 REV-A（模板格式规范）
  Drive路径: docs/daily_briefing_template_v1.md
  特别说明: 按 REV-A 中定义的完整模板格式生成，
            包含唯一入口声明/必填选填字段/查表区/
            输出区/样例页/7日摘要区

文件9: trade_record_log_v1.md
  内容来源: TASK-2026-06-10-012 REV-A（记录日志格式规范）
  Drive路径: docs/trade_record_log_v1.md
  特别说明: 按 REV-A 中定义的完整日志格式生成，
            包含填写时机关系图/已执行交易表/
            未交易事件四类表/月度归因汇总区

文件10: SYSTEM_INDEX.md
  内容: 所有引擎文件的索引和阅读顺序
  Drive路径: docs/SYSTEM_INDEX.md
  格式:
    系统入口（每日先读）: daily_briefing_template_v1.md
    引擎文档（按需查表）:
      1. cycle_positioning_engine_v1.md
      2. asset_allocation_engine_v1.md
      3. buy_trigger_engine_v1.md
      4. position_sizing_engine_v1.md
      5. take_profit_system_v1.md
      6. strategy_attribution_system_v1.md
      7. daily_decision_briefing_v1.md（格式规范）
    记录工具:
      trade_record_log_v1.md
    治理制度:
      AI_PROJECT_GOVERNANCE_V2.md

---

## ACCEPTANCE_CRITERIA

1. docs/ 目录下存在10份文件，路径全部正确
2. buy_trigger_engine_v1.md 含四账户模板和A/B/C等级
3. daily_briefing_template_v1.md 含唯一入口声明/≤8必填/样例页
4. trade_record_log_v1.md 含填写时机关系图和三类表格
5. SYSTEM_INDEX.md 含正确阅读顺序
6. 验收包含每份文件的实际大小和修改时间
7. 验收包 12 项字段完整
8. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. 10份文件全部写入 Drive docs/ ✓
2. 验收包含全部10份文件的大小和时间记录 ✓
3. daily_briefing_template_v1.md 含样例页 ✓
4. SYSTEM_INDEX.md 存在且阅读顺序正确 ✓
5. 验收包 12 项字段完整 ✓
6. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

步骤1：读取所有来源 TASK_PACKAGE 文件
  路径：G:\我的云端硬盘\AI_Investment_System\docs\tasks\

步骤2：按文件清单逐一生成并写入 docs/
  根路径：G:\我的云端硬盘\AI_Investment_System\docs\
  逐一确认每份文件写入成功，记录文件大小和修改时间

步骤3：生成验收包
  路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
        task-2026-06-10-013_validation_package.md
  验收包 section 1：10份文件写入结果表
    文件名 | 路径 | 大小(bytes) | 修改时间 | 状态
  验收包 section 2：关键内容确认
    daily_briefing_template_v1.md 含唯一入口声明：YES/NO
    daily_briefing_template_v1.md 必填字段数量：____
    daily_briefing_template_v1.md 含样例页：YES/NO
    trade_record_log_v1.md 含填写时机关系图：YES/NO
    SYSTEM_INDEX.md 系统入口指向正确文件：YES/NO
  验收包 section 3：12项验收字段

---

## 禁止事项

禁止修改任何已批准的策略内容
禁止修改 skill_gate.py
禁止修改 dashboard.html
禁止生成日报
禁止涉及账户操作
禁止自行验收
禁止跳过任何文件（10份必须全部写入）
禁止在验收包中将任何未写入的文件标注为 PASS
