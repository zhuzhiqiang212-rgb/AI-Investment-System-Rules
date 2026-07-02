# TASK PACKAGE
# TASK-2026-06-10-017

TASK_ID: TASK-2026-06-10-017
任务名称: P1_ENGINES_DEPLOYMENT_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 实施类
影响范围: docs/（写入5份P1引擎文档）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO
内容来源（已批准 TASK_PACKAGE）:
  TASK-2026-06-10-005 REV-A → buy_trigger_engine_v1.md
  TASK-2026-06-10-006 REV-A → position_sizing_engine_v1.md
  TASK-2026-06-10-007 REV-A → take_profit_system_v1.md
  TASK-2026-06-10-008 REV-A → cycle_positioning_engine_v1.md
  TASK-2026-06-10-009 REV-A → asset_allocation_engine_v1.md

---

## 任务目标

部署 P1 五份引擎文档到 Drive docs/ 目录。
不新增任何设计内容，完全按已批准 TASK_PACKAGE 内容执行。

解决当前直接缺口：
用户打开 daily_briefing_template_v1.md 查表区时，
步骤1-5全部标注"引擎文档待部署"。
本任务完成后，用户第一次能够完整走完六步查表流程。

---

## 待写入文件（5份，严格按此顺序）

文件1: cycle_positioning_engine_v1.md（步骤1）
  内容来源: TASK-2026-06-10-008 REV-A
  Drive路径: docs/cycle_positioning_engine_v1.md
  优先原因: 步骤1，整个查表流程的起点

文件2: asset_allocation_engine_v1.md（步骤2）
  内容来源: TASK-2026-06-10-009 REV-A
  Drive路径: docs/asset_allocation_engine_v1.md

文件3: buy_trigger_engine_v1.md（步骤3）
  内容来源: TASK-2026-06-10-005 REV-A
  Drive路径: docs/buy_trigger_engine_v1.md

文件4: position_sizing_engine_v1.md（步骤4）
  内容来源: TASK-2026-06-10-006 REV-A
  Drive路径: docs/position_sizing_engine_v1.md

文件5: take_profit_system_v1.md（步骤5）
  内容来源: TASK-2026-06-10-007 REV-A
  Drive路径: docs/take_profit_system_v1.md

---

## 执行前置条件

Codex 在执行本任务前必须先运行 governance_runtime.py：

  python scripts/governance_runtime.py \
    --task-id      "TASK-2026-06-10-017" \
    --stage        "implementation" \
    --approved     "true" \
    --executor     "Codex" \
    --acceptor     "ChatGPT" \
    --thread       "AI投研总控台 + 正式日报生产" \
    --task-type    "governance" \
    --affects-account "false"

返回 0 才允许继续。返回 1 则中止。

---

## 部署完成后：更新 SYSTEM_INDEX.md

五份文件部署完成后，更新 SYSTEM_INDEX.md 中
P1文件清单的状态和最后更新时间。

---

## ACCEPTANCE_CRITERIA

1. 五份文件全部写入 docs/ 正确路径
2. governance_runtime.py 前置检查返回 0（已记录）
3. 各文件包含对应引擎的核心内容
   - cycle_positioning_engine_v1.md 含六个周期状态定义
   - asset_allocation_engine_v1.md 含七状态配置矩阵和硬上限
   - buy_trigger_engine_v1.md 含四账户模板和A/B/C等级
   - position_sizing_engine_v1.md 含回撤压缩和满仓禁止规则
   - take_profit_system_v1.md 含分批止盈和不止盈条件
4. SYSTEM_INDEX.md P1状态更新
5. 用户侧验收：打开 daily_briefing_template_v1.md
   查表区步骤1-5不再显示"引擎文档待部署"
6. 验收包含五份文件实际大小和修改时间
7. 验收包 12 项字段完整
8. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. 五份文件全部写入 docs/ ✓
2. governance_runtime.py 前置检查通过（$LASTEXITCODE=0）✓
3. SYSTEM_INDEX.md P1状态已更新 ✓
4. 用户侧验收：查表区可用 ✓
5. 验收包 12 项字段完整 ✓
6. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

步骤0：运行 governance_runtime.py 前置检查
  返回 0 → 继续执行
  返回 1 → 中止，报告 BLOCKED

步骤1-5：按顺序读取对应 TASK_PACKAGE REV-A，
  生成并写入五份引擎文档到 docs/
  每份文件写入后记录实际大小和修改时间

步骤6：更新 SYSTEM_INDEX.md
  P1文件清单状态改为已部署，填入更新时间

步骤7：生成验收包
  路径: G:\我的云端硬盘\AI_Investment_System\reports\validation\
        task-2026-06-10-017_validation_package.md
  须含:
    section 1：governance_runtime 前置检查结果
    section 2：五份文件写入结果（文件名/大小/修改时间/状态）
    section 3：各文件关键内容确认（含核心字段检查）
    section 4：SYSTEM_INDEX.md 更新确认
    section 5：用户侧验收（查表区步骤1-5是否可用）
    section 6：12项验收字段

---

## 禁止事项

禁止修改任何已批准的策略内容
禁止修改 skill_gate.py 或 governance_runtime.py
禁止修改 dashboard.html
禁止生成日报
禁止涉及账户操作
禁止自行最终验收
禁止在 governance_runtime.py 返回 1 时继续执行
禁止跳过前置检查步骤
禁止在未写入的文件旁标注 PASS
