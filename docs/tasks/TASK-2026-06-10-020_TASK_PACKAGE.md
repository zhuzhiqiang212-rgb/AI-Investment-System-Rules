# TASK PACKAGE
# TASK-2026-06-10-020

TASK_ID: TASK-2026-06-10-020
任务名称: USER_ENV_DATA_FETCH_VALIDATION_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: 用户（在本地 Windows 环境运行脚本）
         Codex（记录结果并写入验收包）
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 验证类
影响范围: reports/validation/（写入验收包）
          data/daily_fetch_log.json（用户确认后写入）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO
是否生成交易指令: NO
是否修改账户数据: NO

---

## 任务目标

在用户真实 Windows 环境中运行一次
daily_data_fetch.py，验证数据获取是否正常。

背景：
  所有测试均在 Codex 执行环境中完成，
  该环境无法访问 Yahoo Finance，导致全部 DATA_GAP。
  用户本地环境能否成功获取数据至今未验证。
  本任务是进入 AUTO_DECISION_BRIEFING_V1 的前提条件。

验证问题：
  "daily_data_fetch.py 在用户本地环境中
   能否成功获取 VIX / 美债 / SPX / BTC 数据？"

---

## 执行规范

### 用户操作（约5分钟）

步骤1：在本地 Windows 终端运行

  cd G:\我的云端硬盘\AI_Investment_System
  python scripts/daily_data_fetch.py --dry-run

步骤2：观察输出并记录每项数据状态
  - VIX：OK 还是 DATA_GAP？值是多少？
  - 10Y美债：OK 还是 DATA_GAP？值是多少？
  - SPX日涨跌：OK 还是 DATA_GAP？值是多少？
  - BTC日涨跌：OK 还是 DATA_GAP？值是多少？
  - 总耗时：____秒

步骤3：将以上结果发给 Codex

### Codex 操作

接收用户结果，写入验收包：
  路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
        task-2026-06-10-020_validation_package.md

---

## ACCEPTANCE_CRITERIA

1. 用户已在本地环境运行 --dry-run
2. 四项数据获取结果已记录（OK/DATA_GAP及值）
3. 总耗时已记录
4. 验收包已写入
5. 验收包含明确结论：
   - OK项数量：____
   - DATA_GAP项数量：____
   - 是否满足进入 AUTO_DECISION_BRIEFING 条件
     （OK≥3项 = 满足 / OK<3项 = 需先修复数据源）
6. 验收包 12 项字段完整
7. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. 用户本地运行结果已记录 ✓
2. 四项数据状态明确 ✓
3. AUTO_DECISION_BRIEFING 进入条件判断已输出 ✓
4. 验收包 12 项字段完整 ✓
5. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

等待用户提供本地运行结果后：

步骤1：整理用户提供的数据获取结果

步骤2：生成验收包
  路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
        task-2026-06-10-020_validation_package.md
  须含：
    section 1：用户本地环境运行结果
      VIX：OK/DATA_GAP / 值
      10Y美债：OK/DATA_GAP / 值
      SPX日涨跌：OK/DATA_GAP / 值
      BTC日涨跌：OK/DATA_GAP / 值
      总耗时
    section 2：AUTO_DECISION_BRIEFING 条件判断
      OK项数量 / 条件满足：YES/NO / 下一步建议
    section 3：12项标准验收字段

---

## 禁止事项

禁止用 Codex 执行环境的 DATA_GAP 结果替代用户本地结果
禁止生成日报
禁止涉及账户操作
禁止自动下单
禁止自行最终验收
