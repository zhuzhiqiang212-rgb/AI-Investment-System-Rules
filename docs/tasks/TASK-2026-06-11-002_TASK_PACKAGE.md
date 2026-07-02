# TASK PACKAGE
# TASK-2026-06-11-002

TASK_ID: TASK-2026-06-11-002
任务名称: FETCH_SCRIPT_ARGPARSE_FIX_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 实施类（代码修复）
影响范围: scripts/daily_data_fetch.py（修复 main() 启动卡死）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO
是否生成交易指令: NO
是否新增功能: NO

---

## 最终根因

脚本顶层无异常。卡点在 main() 内部、第一个 print 之前。
最可能位置：argparse.parse_args() 在 Windows CMD 环境下
未正确接收 --dry-run 参数，触发交互式等待或阻塞。

---

## 修复规范（仅修改 main() 启动区，不改其他逻辑）

### 修复1：main() 第一行加入 MAIN_START 日志

在 main() 函数体第一行插入：
  print("[MAIN_START] daily_data_fetch 启动")

用于确认 main() 被进入。

### 修复2：argparse 增加 sys.argv 显式传入保护

将：
  args = parser.parse_args()

替换为：
  args = parser.parse_args(sys.argv[1:])

防止 Windows CMD 下 argparse 读取异常输入源。

### 修复3：parse_args 之后立即输出日志

在 args = parser.parse_args(sys.argv[1:]) 之后插入：
  print(f"[ARGS_PARSED] dry_run={args.dry_run}")

用于确认参数解析完成。

### 修复4：总超时定时器启动前加入日志

在 total_timer.start() 之后插入：
  print(f"[TIMER_START] 总超时 {TOTAL_TIMEOUT}秒 已启动")

---

## ACCEPTANCE_CRITERIA

1. governance_runtime.py 前置检查通过
2. [MAIN_START] 日志已加入 main() 第一行
3. parse_args 改为 parse_args(sys.argv[1:])
4. [ARGS_PARSED] 日志已加入
5. [TIMER_START] 日志已加入
6. Codex dry-run 测试：[MAIN_START] 出现在输出中
7. 用户本地 dry-run：脚本在 45 秒内退出，[MAIN_START] 出现
8. 验收包 12 项字段完整
9. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. 四处修复完成 ✓
2. 用户本地脚本不再卡死 ✓
3. [MAIN_START] / [ARGS_PARSED] / [TIMER_START] 均出现 ✓
4. 验收包 12 项字段完整 ✓
5. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

步骤0：governance_runtime.py 前置检查
  python scripts/governance_runtime.py \
    --task-id "TASK-2026-06-11-002" \
    --stage "implementation" \
    --approved "true" \
    --executor "Codex" \
    --acceptor "ChatGPT" \
    --thread "AI投研总控台 + 正式日报生产" \
    --task-type "governance" \
    --affects-account "false"

步骤1：记录修复前文件大小

步骤2：按修复规范修改 daily_data_fetch.py
  - main() 第一行加 [MAIN_START] 日志
  - parse_args() → parse_args(sys.argv[1:])
  - [ARGS_PARSED] 日志
  - [TIMER_START] 日志

步骤3：Codex dry-run 测试
  python scripts/daily_data_fetch.py --dry-run
  记录：[MAIN_START] 是否出现 / 耗时

步骤4：生成验收包
  路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
        task-2026-06-11-002_validation_package.md
  须含：
    section 1：四处修复位置确认
    section 2：修复前后文件大小
    section 3：Codex dry-run 输出（含 [MAIN_START] 确认）
    section 4：用户本地复测指引
    section 5：12项标准验收字段

---

## 禁止事项

禁止修改 fetch 函数业务逻辑
禁止修改数据写入 / 确认 / 历史保护逻辑
禁止修改 skill_gate.py / governance_runtime.py
禁止修改 dashboard.html
禁止生成日报
禁止涉及账户操作
禁止自行最终验收
禁止进入 TASK-022
禁止进入 AUTO_DECISION_BRIEFING
