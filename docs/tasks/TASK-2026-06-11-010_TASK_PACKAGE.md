# TASK PACKAGE
# TASK-2026-06-11-010

TASK_ID: TASK-2026-06-11-010
任务名称: G05_CYCLE_MULTIDIM_V1
目标清单项: G-05（周期定位多维化）
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V6（≠ 执行人）
任务类型: 实施类（代码修改）
影响范围: scripts/auto_briefing.py（扩展 step1_cycle() 函数）
APPROVAL_REQUIRED: YES
审批状态: APPROVED（ChatGPT V6，2026-06-11）
是否涉及账户操作: NO
是否改变文件路径: NO
是否影响G-01/G-02/G-03流程: NO

---

## 任务目标

将周期定位从2维（VIX + 美债）升级为4维：
  维度1：VIX（市场恐慌度）
  维度2：10Y美债收益率（流动性）
  维度3：SPX涨跌（价格结构）
  维度4：BTC涨跌（风险偏好）

置信度判断基于4个维度的一致性，而非仅2个。

---

## 修改规范

### 修改：重写 step1_cycle() 函数

```python
def step1_cycle(vix, tnx, spx=None, btc=None) -> tuple[str, str]:
    """
    步骤1：周期定位 → (周期标签, 置信度)
    4维判断：VIX / 美债 / SPX / BTC
    """
    # 维度不足时降级
    available = sum([
        vix is not None,
        tnx is not None,
        spx is not None,
        btc is not None,
    ])
    if available < 2:
        return "UNKNOWN", "C"

    signals = []

    # 维度1：VIX
    if vix is not None:
        if vix < 18:
            signals.append("BULL")
        elif vix < 23:
            signals.append("TRANSITION")
        else:
            signals.append("BEAR")

    # 维度2：10Y美债
    if tnx is not None:
        if tnx < 4.0:
            signals.append("BULL")
        elif tnx < 4.7:
            signals.append("TRANSITION")
        else:
            signals.append("BEAR")

    # 维度3：SPX日涨跌
    if spx is not None:
        if spx > 0.5:
            signals.append("BULL")
        elif spx < -1.0:
            signals.append("BEAR")
        else:
            signals.append("TRANSITION")

    # 维度4：BTC日涨跌（风险偏好辅助）
    if btc is not None:
        if btc > 1.0:
            signals.append("BULL")
        elif btc < -2.0:
            signals.append("BEAR")
        else:
            signals.append("TRANSITION")

    bull_count  = signals.count("BULL")
    bear_count  = signals.count("BEAR")
    trans_count = signals.count("TRANSITION")
    total       = len(signals)

    # 周期判断
    if bull_count >= total * 0.75:
        cycle = "BULL_MID"
    elif bear_count >= total * 0.75:
        cycle = "BEAR"
    elif bull_count > bear_count and bull_count >= total * 0.5:
        cycle = "BULL_MID"
    elif bear_count > bull_count and bear_count >= total * 0.5:
        cycle = "BEAR"
    else:
        cycle = "TRANSITION"

    # 置信度（基于一致性）
    max_count = max(bull_count, bear_count, trans_count)
    if max_count == total:
        confidence = "A"       # 全部一致
    elif max_count >= total * 0.75:
        confidence = "A"       # 75%以上一致
    elif max_count >= total * 0.5:
        confidence = "B"       # 50%以上一致
    else:
        confidence = "C"       # 严重分歧

    # 数据不足时置信度降级
    if available < 3:
        if confidence == "A":
            confidence = "B"
        elif confidence == "B":
            confidence = "C"

    return cycle, confidence
```

### 修改2：main() 中调用 step1_cycle() 时传入 spx 和 btc

将现有：
```python
cycle, confidence = step1_cycle(vix_val, tnx_val)
```

替换为：
```python
cycle, confidence = step1_cycle(vix_val, tnx_val, spx_val, btc_val)
```

---

## ACCEPTANCE_CRITERIA

1. auto_briefing.py 修改完成
2. governance_runtime.py 前置检查通过
3. step1_cycle() 函数签名含4个参数
4. dry-run 测试：周期判断输出合理
   - 4维数据全部OK时：置信度可能升为A级
   - SPX/BTC DATA_GAP时：置信度降级逻辑正确
5. G-01/G-02/G-03 流程不受影响
6. 验收包 12 项字段完整
7. ChatGPT V6 明确输出 PASS

---

## CLOSE_CONDITION

1. step1_cycle() 重写完成，含4维判断 ✓
2. main() 传入 spx_val / btc_val ✓
3. dry-run 通过 ✓
4. G-01/G-02/G-03 不受影响 ✓
5. 验收包完整 ✓
6. ChatGPT V6 输出 PASS ✓

---

## CODEX_EXECUTION

步骤0：governance_runtime.py 前置检查
  python scripts/governance_runtime.py \
    --task-id "TASK-2026-06-11-010" \
    --stage "implementation" \
    --approved "true" \
    --executor "Codex" \
    --acceptor "ChatGPT" \
    --thread "AI投研总控台 + 正式日报生产" \
    --task-type "governance" \
    --affects-account "false"

步骤1：重写 step1_cycle() 函数，修改 main() 调用

步骤2：dry-run 验证
  python scripts/auto_briefing.py --dry-run
  记录：周期标签 / 置信度 / 维度数量

步骤3：生成验收包
  路径：reports/validation/task-2026-06-11-010_validation_package.md

---

## 禁止事项

禁止修改 step3_signal() 等其他分析函数
禁止改变文件路径或文件名
禁止影响G-01/G-02/G-03已通过流程
禁止修改 skill_gate.py / governance_runtime.py
禁止连接券商接口
禁止自动下单
禁止自行最终验收
