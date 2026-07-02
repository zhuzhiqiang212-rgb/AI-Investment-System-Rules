# TASK PACKAGE
# TASK-2026-06-10-013 REV-A

TASK_ID: TASK-2026-06-10-013 REV-A
任务名称: ALL_ENGINES_DRIVE_DEPLOYMENT_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 实施类
影响范围: docs/（写入11份文件，分P0/P1/P2优先级）
APPROVAL_REQUIRED: YES
审批状态: PENDING（REV-A，等待 ChatGPT 重新审批）
旧版本状态: TASK-2026-06-10-013 原始版自动作废
是否涉及账户操作: NO
是否涉及规则变更: NO

---

## 审批变更项（已合并，共5项）

1. 实施优先级 P0/P1/P2
   优先保证用户每天实际会打开的文件，不一次性全量部署。

2. 唯一入口明确声明
   SYSTEM_INDEX.md 须明确唯一入口文件名和路径，禁止多个入口。

3. 用户侧验收标准
   不是"文件生成成功"，而是"用户打开唯一入口，
   能否在3分钟内完成决策前判断"。

4. 文件依赖关系图
   明确 daily_briefing_template_v1.md /
   trade_record_log_v1.md / SYSTEM_INDEX.md
   各自依赖哪些引擎。

5. 最低可运行版本（MVP）
   定义最小可运行集合，P0文件失败时的降级路径。

---

## 实施优先级定义（变更项1）

### P0：最低可运行版本（MVP）
用户今天就能使用的最小集合。
P0必须全部成功，否则整个部署视为失败。

  文件1: SYSTEM_INDEX.md
    唯一入口索引，用户打开Drive的第一个文件
    Drive路径: docs/SYSTEM_INDEX.md

  文件2: daily_briefing_template_v1.md
    唯一入口，每日决策前判断工具
    Drive路径: docs/daily_briefing_template_v1.md

  文件3: trade_record_log_v1.md
    交易记录日志，归因数据积累起点
    Drive路径: docs/trade_record_log_v1.md

### P1：核心引擎（P0可用后立即部署）
用户查表时需要的引擎文档。
P1失败不影响P0可用性，但用户需要手动记忆规则。

  文件4: cycle_positioning_engine_v1.md
    周期定位（简报步骤1依赖）
  文件5: asset_allocation_engine_v1.md
    资产配置（简报步骤2依赖）
  文件6: buy_trigger_engine_v1.md
    买入触发器（简报步骤3依赖）
  文件7: position_sizing_engine_v1.md
    仓位计算（简报步骤4依赖）
  文件8: take_profit_system_v1.md
    止盈系统（简报步骤5依赖）

### P2：完整系统（P1完成后部署）
归因和格式规范文档。

  文件9:  strategy_attribution_system_v1.md
    归因系统（trade_record_log依赖）
  文件10: daily_decision_briefing_v1.md
    简报格式规范（参考文档，非操作文件）

---

## 唯一入口声明（变更项2）

唯一入口：
  文件名: daily_briefing_template_v1.md
  Drive路径: AI_Investment_System/docs/daily_briefing_template_v1.md
  用户每日第一个打开的文件，且仅此一个。

SYSTEM_INDEX.md 须包含以下声明：
  UNIQUE_ENTRY_POINT: daily_briefing_template_v1.md
  UNIQUE_ENTRY_PATH: AI_Investment_System/docs/daily_briefing_template_v1.md
  禁止多个入口：其他所有文件均为按需展开，不是入口。

---

## 文件依赖关系图（变更项4）

daily_briefing_template_v1.md（唯一入口）
  ├─ 步骤1查表 → cycle_positioning_engine_v1.md
  ├─ 步骤2查表 → asset_allocation_engine_v1.md
  ├─ 步骤3查表 → buy_trigger_engine_v1.md
  ├─ 步骤4查表 → position_sizing_engine_v1.md
  ├─ 步骤5查表 → take_profit_system_v1.md
  └─ 步骤6查表 → strategy_attribution_system_v1.md（预警）

trade_record_log_v1.md
  ├─ 记录格式依赖 → strategy_attribution_system_v1.md
  ├─ 信号等级字段 → buy_trigger_engine_v1.md
  └─ 归因结论字段 → strategy_attribution_system_v1.md

SYSTEM_INDEX.md
  ├─ 指向唯一入口 → daily_briefing_template_v1.md
  ├─ 列出P1引擎    → 五份引擎文档
  └─ 列出记录工具  → trade_record_log_v1.md

MVP可运行条件（P0）：
  daily_briefing_template_v1.md + SYSTEM_INDEX.md
  用户可填写第0/1/2行，查表区标注"引擎待部署"
  不影响结论输出，只影响查表细节

---

## 最低可运行版本 MVP（变更项5）

P0三份文件全部成功 = MVP 达成。
MVP 状态下用户可以：
  ✓ 打开 SYSTEM_INDEX.md 找到唯一入口
  ✓ 打开 daily_briefing_template_v1.md 填写8项必填字段
  ✓ 根据已知规则手动完成查表（引擎在脑中而非文档）
  ✓ 输出第0/1/2行结论
  ✓ 开始用 trade_record_log_v1.md 记录交易

P1失败时的降级处理：
  查表区对应步骤标注："[引擎文档待部署，参考已知规则]"
  不阻断简报输出，置信度不因P1缺失而自动降级

P2失败时的降级处理：
  归因系统暂缓，trade_record_log 仍可记录（归因结论留空）
  daily_decision_briefing_v1.md 作为参考文档缺失，不影响模板使用

---

## 用户侧验收标准（变更项3）

技术验收（Codex 执行后）：
  ✓ P0三份文件存在于 docs/ 目录
  ✓ P1五份文件存在于 docs/ 目录
  ✓ P2两份文件存在于 docs/ 目录

用户侧验收（ChatGPT 最终验收时确认）：
  用户打开 SYSTEM_INDEX.md：
    → 能否在5秒内找到唯一入口文件名？YES/NO
  用户打开 daily_briefing_template_v1.md：
    → 是否在第一行看到唯一入口声明？YES/NO
    → 必填字段是否≤8项？YES/NO
    → 是否包含样例页（2026-06-10完整示例）？YES/NO
  用户填写必填8项（模拟）：
    → 能否在2分钟内完成必填区？YES/NO
    → 能否在1分钟内完成查表区？YES/NO
    → 能否得出第0/1/2行输出？YES/NO
  3分钟完成目标：YES/NO

用户侧验收全部 YES = 生产级可用。
任意 NO = 任务状态 PARTIAL，需指明具体失败项。

---

## CODEX_EXECUTION

执行顺序严格按 P0 → P1 → P2：

Phase P0（必须全部成功才能继续）：

  步骤1：生成 SYSTEM_INDEX.md
  内容须包含：
    UNIQUE_ENTRY_POINT: daily_briefing_template_v1.md
    UNIQUE_ENTRY_PATH: AI_Investment_System/docs/daily_briefing_template_v1.md
    文件依赖关系图（上方完整版）
    P0/P1/P2文件清单及状态
  写入：G:\我的云端硬盘\AI_Investment_System\docs\SYSTEM_INDEX.md

  步骤2：生成 daily_briefing_template_v1.md
  按 TASK-2026-06-10-012 REV-A 定义的完整格式生成：
    唯一入口声明 / ≤8必填字段 / ≤6选填字段 /
    降级规则 / 查表区6步 / 输出区第0/1/2行 /
    区块A-E / 7日摘要区 / 样例页（2026-06-10完整示例）
  写入：G:\我的云端硬盘\AI_Investment_System\docs\daily_briefing_template_v1.md

  步骤3：生成 trade_record_log_v1.md
  按 TASK-2026-06-10-012 REV-A 定义的完整格式生成：
    填写时机关系图 / 已执行交易12字段表（30行）/
    未交易四类事件表 / 月度归因汇总区
  写入：G:\我的云端硬盘\AI_Investment_System\docs\trade_record_log_v1.md

  P0确认：三份文件全部写入成功 → 继续 P1
          任意失败 → 停止，在验收包标注 PARTIAL

Phase P1（P0成功后执行）：
  逐一生成并写入：
    cycle_positioning_engine_v1.md
    asset_allocation_engine_v1.md
    buy_trigger_engine_v1.md
    position_sizing_engine_v1.md
    take_profit_system_v1.md
  内容来源：对应 TASK_PACKAGE REV-A 文件中的策略内容

Phase P2（P1成功后执行）：
  逐一生成并写入：
    strategy_attribution_system_v1.md
    daily_decision_briefing_v1.md

生成验收包：
  路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
        task-2026-06-10-013_validation_package.md
  须包含：
    section 1：P0/P1/P2 文件写入结果表
    section 2：依赖关系图确认
    section 3：用户侧验收标准逐项确认
    section 4：12项验收字段

---

## ACCEPTANCE_CRITERIA

1. P0三份文件（SYSTEM_INDEX / 简报模板 / 记录日志）全部写入 ✓
2. SYSTEM_INDEX.md 含唯一入口声明和依赖关系图（变更项2/4）✓
3. daily_briefing_template_v1.md 含唯一入口声明/≤8必填/样例页（变更项1/3）✓
4. P1五份引擎文档全部写入 ✓
5. P2两份文档全部写入 ✓
6. 用户侧验收七项全部 YES（变更项3）✓
7. 文件依赖关系图在 SYSTEM_INDEX.md 中完整（变更项4）✓
8. MVP降级路径在 SYSTEM_INDEX.md 中说明（变更项5）✓
9. 验收包 12 项字段完整 ✓
10. ChatGPT 明确输出 PASS ✓

---

## CLOSE_CONDITION

1. P0全部成功 ✓
2. P1全部成功 ✓
3. P2全部成功 ✓
4. 用户侧验收七项全部 YES ✓
5. 验收包 12 项字段完整 ✓
6. ChatGPT 输出 PASS ✓

若P1/P2部分失败：状态 PARTIAL，ChatGPT 决定是否 CLOSE。
若P0失败：状态 FAIL，任务重新执行。

---

## 禁止事项

禁止修改任何已批准的策略内容
禁止修改 skill_gate.py
禁止修改 dashboard.html
禁止生成日报
禁止涉及账户操作
禁止自行验收
禁止在未写入的文件旁标注 PASS
禁止在P0失败时继续执行P1/P2
禁止跳过用户侧验收七项检查
