# TASK PACKAGE
# TASK-2026-06-11-001

TASK_ID: TASK-2026-06-11-001
任务名称: AUTO_READY_VALIDATION_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: 用户（本地运行）/ Codex（记录结果）
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 验证类
影响范围: reports/validation/（写入验收包）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO
是否生成交易指令: NO
是否修改账户数据: NO
前置条件: TASK-2026-06-10-021 REV-A 已完成（硬超时修复）

---

## 任务目标

验证 TASK-021 REV-A 硬超时修复后，
用户本地 dry-run 是否能在 45 秒内完成，
并成功返回 VIX / 10Y / SPX / BTC 四项数据。

判断 AUTO_READY：YES / NO。

---

## 用户操作（一条命令）

在本地 Windows 终端执行：

  cd G:\我的云端硬盘\AI_Investment_System
  python scripts/daily_data_fetch.py --dry-run

观察并记录：
  1. [FETCH_START] 日志是否逐项出现
  2. 脚本是否在 45 秒内退出（不卡死）
  3. 四项数据各自状态：

     VIX    : OK / DATA_GAP / HARD_TIMEOUT   值：____
     10Y美债: OK / DATA_GAP / HARD_TIMEOUT   值：____
     SPX    : OK / DATA_GAP / HARD_TIMEOUT   值：____
     BTC    : OK / DATA_GAP / HARD_TIMEOUT   值：____

  4. 总耗时：____秒

将以上结果发回 Claude / Codex。

---

## Codex 操作

接收用户结果，生成验收包：
  路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
        task-2026-06-11-001_auto_ready_validation_package.md

---

## AUTO_READY 判定规则

OK 项数量 ≥ 3  →  AUTO_READY: YES
OK 项数量 < 3  →  AUTO_READY: NO
脚本仍卡死      →  AUTO_READY: NO + 需进一步诊断

---

## ACCEPTANCE_CRITERIA

1. 用户本地 dry-run 已执行
2. 脚本在 45 秒内退出（不卡死）：YES / NO
3. [FETCH_START] 日志出现：YES / NO
4. 四项数据状态已记录（OK / DATA_GAP / HARD_TIMEOUT）
5. OK 项数量已统计
6. AUTO_READY: YES / NO 已明确输出
7. 验收包 12 项字段完整
8. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. 用户本地结果已记录 ✓
2. 脚本不卡死已确认 ✓
3. AUTO_READY 判定已输出 ✓
4. 验收包 12 项字段完整 ✓
5. ChatGPT 输出 PASS ✓

若 AUTO_READY: YES → 进入 AUTO_DECISION_BRIEFING_V1
若 AUTO_READY: NO  → 诊断新原因，不进入 TASK-022

---

## CODEX_EXECUTION

等待用户提供本地运行结果后：

生成验收包：
  task-2026-06-11-001_auto_ready_validation_package.md

必须包含：
  section 1：用户本地运行结果
    [FETCH_START] 日志：YES/NO
    脚本45秒内退出：YES/NO
    VIX / 10Y / SPX / BTC 各自状态和值
    总耗时
  section 2：OK 项数量 / DATA_GAP / HARD_TIMEOUT 统计
  section 3：AUTO_READY 判定
    OK≥3：YES/NO
    AUTO_READY：YES/NO
    若 NO：新原因说明
  section 4：12项标准验收字段

---

## 禁止事项

禁止用 Codex 环境结果替代用户本地结果
禁止生成日报
禁止涉及账户操作
禁止自动下单
禁止自行最终验收
禁止进入 TASK-022
禁止启动 AUTO_DECISION_BRIEFING_V1（须等 AUTO_READY: YES 确认后）
