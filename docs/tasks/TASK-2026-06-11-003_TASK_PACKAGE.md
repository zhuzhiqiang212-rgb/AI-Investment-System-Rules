# TASK PACKAGE
# TASK-2026-06-11-003

TASK_ID: TASK-2026-06-11-003
任务名称: AUTO_DECISION_BRIEFING_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 实施类（代码）
影响范围: scripts/auto_briefing.py（新建）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO
是否生成交易指令: NO
是否修改账户数据: NO
前置条件: AUTO_READY: YES（TASK-2026-06-11-002 已验证）

---

## 任务目标

把以下三步合并为一条命令：

  现在（三步）:
    1. python scripts/daily_data_fetch.py --dry-run
    2. 用户确认数据
    3. 打开 daily_briefing_template_v1.md 查表

  目标（一步）:
    python scripts/auto_briefing.py
    → 自动获取数据
    → 自动查表（周期/配置/信号）
    → 输出第0/1/2行结论
    → 用户确认后写入模板

从"脚本+确认+查表 约2分钟"
升级为"一条命令+确认 约30秒"。

---

## 交付内容

### scripts/auto_briefing.py（新建）

功能：
  1. 调用 daily_data_fetch 获取数据（复用现有函数）
  2. 根据数据自动查表六步
  3. 输出第0/1/2行结论
  4. 用户输入 Y 确认后写入 daily_briefing_template_v1.md

自动查表逻辑：

  步骤1 周期定位：
    VIX<20 + 美债<4.5% → BULL_MID  置信度A
    VIX<20 + 美债≥4.5% → BULL_MID  置信度B
    VIX 20-25           → TRANSITION 置信度B
    VIX>25              → BEAR       置信度B
    任一数据DATA_GAP    → UNKNOWN    置信度C

  步骤2 配置偏离：
    加密仓位>10%        → 偏离 YES（需再平衡）
    加密仓位≤10%        → 偏离 NO

  步骤3 信号等级（基于SPX/BTC涨跌）：
    SPX>+0.5%           → 美股信号 B
    SPX<-1%             → 美股信号 无（防守）
    BTC OK且>+1%        → 加密信号 B
    BTC DATA_GAP        → 加密信号 C（降级）

  步骤4-6：基于步骤1-3结果，
    输出建议仓位 / 止损状态（占位，用户确认）/ 预警（无）

  第0行结论生成规则：
    BULL_MID A级  → "允许分批布局AI核心"
    BULL_MID B级  → "谨慎布局，控制仓位"
    TRANSITION    → "今天进入观察期"
    BEAR          → "进入防守，持有现金"
    UNKNOWN       → "证据不足，仅观察"

  第1行唯一动作：
    有B级以上信号且置信度≥B → 分批建仓（账户+标的占位）
    无信号或置信度C         → 观察

  第2行最不能做：
    VIX>20              → 禁止加杠杆
    SPX单日<-1%         → 禁止抄底
    加密>8%             → 禁止加仓加密
    默认                → 禁止追高

用户确认：
  输出第0/1/2行预览后，用户输入 Y 确认写入模板。
  禁止未确认自动写入。
  不生成交易指令，不自动下单。

---

## ACCEPTANCE_CRITERIA

1. auto_briefing.py 已写入 scripts/
2. governance_runtime.py 前置检查通过
3. Codex dry-run：脚本在45秒内完成
4. 第0/1/2行结论基于真实数据输出（非硬编码）
5. 用户确认步骤存在（Y/N，不可跳过）
6. 不生成交易指令 / 不修改账户数据 / 不自动下单
7. 用户本地运行：第0/1/2行结论出现
8. 验收包 12 项字段完整
9. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. auto_briefing.py 写入 scripts/ ✓
2. 第0/1/2行结论基于真实数据生成 ✓
3. 用户本地运行 ≤45秒完成 ✓
4. 用户确认步骤存在 ✓
5. 验收包 12 项字段完整 ✓
6. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

步骤0：governance_runtime.py 前置检查

步骤1：生成 auto_briefing.py，写入 scripts/
  复用 daily_data_fetch.py 中的 fetch 函数
  实现六步自动查表和第0/1/2行生成逻辑

步骤2：Codex dry-run 测试
  python scripts/auto_briefing.py --dry-run
  记录：第0/1/2行内容 / 耗时 / 退出码

步骤3：生成验收包
  路径：reports/validation/task-2026-06-11-003_validation_package.md

---

## 禁止事项

禁止生成交易指令
禁止修改账户数据
禁止自动下单
禁止修改 daily_data_fetch.py
禁止修改 skill_gate.py / governance_runtime.py
禁止修改 dashboard.html
禁止生成日报
禁止自行最终验收
