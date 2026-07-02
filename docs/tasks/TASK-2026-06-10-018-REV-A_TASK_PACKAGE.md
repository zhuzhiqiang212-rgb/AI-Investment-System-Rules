# TASK PACKAGE
# TASK-2026-06-10-018 REV-A

TASK_ID: TASK-2026-06-10-018 REV-A
任务名称: USER_SIDE_MVP_WALKTHROUGH_TEST_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Codex（正式执行人）
体验者: 用户（体验者 / 验收观察者，非正式执行人）
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 验证类
影响范围: reports/validation/（写入两份报告文件）
APPROVAL_REQUIRED: YES
审批状态: PENDING（REV-A，等待 ChatGPT 重新审批）
旧版本状态: TASK-2026-06-10-018 原始版自动作废
是否涉及账户操作: NO
是否涉及规则变更: NO
是否生成交易指令: NO
是否修改账户数据: NO
是否自动下单: NO

---

## 审批变更项（已合并，共5项）

1. 执行人修正
   正式执行人：Codex
   用户角色：体验者 / 验收观察者（非正式执行人）

2. 测试目标修正
   不要求用户填满全部字段。
   测试目标是验证路径是否能跑通：
   SYSTEM_INDEX → daily_briefing_template → 第0/1/2行结论

3. 失败也算有效结果
   无法3分钟完成时，不判定任务失败。
   必须记录卡点，输出 USABILITY_GAP_LIST。

4. 测试输出文件
   生成 user_side_mvp_walkthrough_test_v1.md，
   含入口耗时/填写耗时/是否得到结论/卡点/改进建议。

5. 明确不生成交易指令/不修改账户/不自动下单

---

## 测试目标

验证以下路径是否能在真实使用中跑通：

  SYSTEM_INDEX.md
      ↓
  daily_briefing_template_v1.md（唯一入口）
      ↓
  填写必填字段 + 查表区
      ↓
  第0/1/2行结论输出

核心问题：
  路径是否畅通？
  哪里会卡住？
  需要改什么？

不要求：
  填满全部字段
  3分钟必须完成
  所有步骤零卡点

---

## 执行规范

### 前置检查（Codex 执行）

  python scripts/governance_runtime.py \
    --task-id      "TASK-2026-06-10-018" \
    --stage        "implementation" \
    --approved     "true" \
    --executor     "Codex" \
    --acceptor     "ChatGPT" \
    --thread       "AI投研总控台 + 正式日报生产" \
    --task-type    "governance" \
    --affects-account "false"

  返回 0 才继续。返回 1 则中止。

### 阶段一：入口路径测试（Codex 模拟用户操作，计时）

  操作1：打开 SYSTEM_INDEX.md，计时到找到唯一入口文件名
    目标：≤30秒
    记录：实际耗时____秒 / 是否找到：YES/NO

  操作2：从唯一入口路径打开 daily_briefing_template_v1.md
    记录：文件是否正常打开：YES/NO
    记录：第一行是否看到唯一入口声明：YES/NO
    记录：首次使用说明是否清晰：YES/NO

### 阶段二：路径连通测试（核心）

目标：验证 SYSTEM_INDEX → 模板 → 结论 这条路径能跑通。
不强制填满所有字段，最小填写路径即可。

  最小填写路径（只需以下4项即可得出结论）：
    VIX：____（使用当日真实值或合理估计值）
    10Y美债：____%
    SPX日涨跌：____%
    加密仓位：____%

  查表步骤（按模板顺序）：
    步骤1：根据VIX+美债 → 周期标签 → 打开 cycle_positioning_engine_v1.md
           记录：是否找到查表规则：YES/NO / 耗时：____秒
    步骤2：配置偏离检查
           记录：是否找到查表规则：YES/NO / 耗时：____秒
    步骤3：信号等级判断
           记录：是否找到查表规则：YES/NO / 耗时：____秒
    步骤4-6：若步骤1-3通过则继续，否则记录卡点并跳过

  输出区：
    第0行：尝试填写一句话结论 + 置信度
    第1行：尝试选择唯一动作
    第2行：尝试填写最不能做

  记录：
    是否成功输出第0行：YES/NO
    是否成功输出第1行：YES/NO
    是否成功输出第2行：YES/NO

### 阶段三：卡点记录（变更项3）

逐步记录每个遇到困难的位置：

  卡点格式：
    位置：[步骤名称]
    现象：[具体卡在什么地方]
    原因分析：[为什么卡——文字不清晰/找不到引擎/数据缺失/逻辑不明/其他]
    严重程度：高（阻断路径）/ 中（明显减速）/ 低（轻微不适）
    修复建议：[一句话说明需要改什么]

---

## 输出文件规范

### 文件1：user_side_mvp_walkthrough_test_v1.md（变更项4）
路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
      user_side_mvp_walkthrough_test_v1.md

必须包含：
  1. 测试日期和执行人
  2. 入口耗时（SYSTEM_INDEX → 找到唯一入口）
  3. 路径连通状态（SYSTEM_INDEX→模板→结论能否跑通：YES/NO/PARTIAL）
  4. 填写耗时（必填4项 + 查表步骤1-3）
  5. 是否得到第0/1/2行结论（各 YES/NO）
  6. USABILITY_GAP_LIST（变更项3）：
       所有卡点的完整列表，含位置/现象/原因/严重程度/修复建议
  7. 用户是否看得懂系统（总体评估：YES/NO/PARTIAL + 说明）
  8. 下一步修复建议（按优先级排序）
  9. 路径连通结论：PASS / PARTIAL / FAIL + 说明

### 文件2：task-2026-06-10-018_validation_package.md（标准验收包）
路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
      task-2026-06-10-018_validation_package.md

---

## USABILITY_GAP_LIST 判定规则

路径连通结论：
  PASS：第0/1/2行全部输出 + 无高严重度卡点
  PARTIAL：第0行已输出 + 有中等卡点但路径可走通
  FAIL：无法输出第0行 + 存在高严重度阻断卡点

无论结论是 PASS / PARTIAL / FAIL：
  均视为有效测试结果
  PARTIAL 和 FAIL 的卡点列表是比 PASS 更有价值的产出
  不得因结果非 PASS 而判定任务失败

---

## ACCEPTANCE_CRITERIA

1. governance_runtime.py 前置检查通过（$LASTEXITCODE=0）
2. user_side_mvp_walkthrough_test_v1.md 已写入 reports/validation/
3. 报告含入口耗时、路径连通状态、填写耗时
4. 报告含第0/1/2行输出结果（各 YES/NO）
5. USABILITY_GAP_LIST 存在（即使零卡点也须明确列出"无卡点"）
6. 路径连通结论已输出（PASS/PARTIAL/FAIL + 说明）
7. 下一步修复建议已输出（即使 PASS 也须列出）
8. 明确确认：不生成交易指令 / 不修改账户数据 / 不自动下单
9. 验收包 12 项字段完整
10. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. user_side_mvp_walkthrough_test_v1.md 写入 ✓
2. USABILITY_GAP_LIST 存在 ✓
3. 路径连通结论明确（PASS/PARTIAL/FAIL）✓
4. 验收包 12 项字段完整 ✓
5. ChatGPT 输出 PASS ✓

注：路径连通结论为 PARTIAL 或 FAIL 时，ChatGPT 仍可输出 PASS
    （任务本身验证成功），但须同时说明下一步修复优先级。

---

## 禁止事项

禁止生成交易指令
禁止修改账户数据
禁止自动下单
禁止修改任何策略文件或代码
禁止修改 skill_gate.py / governance_runtime.py / dashboard.html
禁止生成日报
禁止用模拟数据声称"已完成真实测试"
禁止在路径未跑通时填写路径连通状态为 PASS
禁止自行最终验收
