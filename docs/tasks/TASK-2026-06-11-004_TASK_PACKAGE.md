# TASK PACKAGE
# TASK-2026-06-11-004

TASK_ID: TASK-2026-06-11-004
任务名称: P2_DOCS_DEPLOYMENT_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 实施类
影响范围: docs/（写入2份P2文件）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO
是否新增功能: NO

---

## 任务目标

部署 P2 两份规范文档到 docs/，完成全系统文档闭环。

待写入文件：

文件1: strategy_attribution_system_v1.md
  内容来源: TASK-2026-06-10-010 REV-A
  目标路径: docs/strategy_attribution_system_v1.md

文件2: daily_decision_briefing_v1.md
  内容来源: TASK-2026-06-10-011 REV-A
  目标路径: docs/daily_decision_briefing_v1.md

---

## 执行前置条件

步骤0: governance_runtime.py 前置检查
  python scripts/governance_runtime.py \
    --task-id "TASK-2026-06-11-004" \
    --stage "implementation" \
    --approved "true" \
    --executor "Codex" \
    --acceptor "ChatGPT" \
    --thread "AI投研总控台 + 正式日报生产" \
    --task-type "governance" \
    --affects-account "false"

---

## ACCEPTANCE_CRITERIA

1. strategy_attribution_system_v1.md 写入 docs/
2. daily_decision_briefing_v1.md 写入 docs/
3. SYSTEM_INDEX.md P2 状态更新为已部署
4. governance_runtime.py 前置检查通过
5. 验收包 12 项字段完整
6. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. 两份文件写入 docs/ ✓
2. SYSTEM_INDEX.md 已更新 ✓
3. 验收包 12 项字段完整 ✓
4. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

步骤0: governance_runtime.py 前置检查
步骤1: 读取来源 TASK_PACKAGE，生成两份文件写入 docs/
步骤2: 更新 SYSTEM_INDEX.md P2 状态
步骤3: 生成验收包
  路径: reports/validation/task-2026-06-11-004_validation_package.md

---

## 禁止事项

禁止修改任何策略内容
禁止修改 skill_gate.py / governance_runtime.py
禁止修改 dashboard.html
禁止生成日报
禁止涉及账户操作
禁止自行最终验收
