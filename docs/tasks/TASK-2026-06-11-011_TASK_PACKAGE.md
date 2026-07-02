# TASK PACKAGE
# TASK-2026-06-11-011

TASK_ID: TASK-2026-06-11-011
任务名称: G03B_OUTPUT_LOGIC_FIX_V1
目标清单项: G-03B（输出逻辑修复）
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V6（≠ 执行人）
任务类型: 实施类（代码修复）
影响范围: scripts/auto_briefing.py（修复 generate_conclusions() 逻辑）
APPROVAL_REQUIRED: YES
审批状态: APPROVED（ChatGPT V6，2026-06-11）
是否涉及账户操作: NO
是否影响G-01/G-02/G-03/G-05流程: NO

---

## 问题根因

今日实际输出发现三处逻辑矛盾：

问题1：第0层"今天进入观察期，暂缓新仓"
        第1层"分批建仓"
        → 自相矛盾，TRANSITION期间不应输出建仓指令

问题2：第1层"账户待确认/标的待确认"是空占位符
        → 用户无法采取任何行动

问题3：第2层最不能做只有一条泛泛的"禁止加杠杆"
        → 信息量过低，未结合当日具体数据

---

## 修改规范

### 修改1：修复 generate_conclusions() 中 layer1 逻辑

```python
# 修复前（有问题）：
if confidence == "C" or cycle in ("UNKNOWN", "BEAR"):
    layer1 = "观察"
elif has_b_signal and confidence in ("A", "B"):
    layer1 = "分批建仓 [账户待确认 / 标的待确认]"
else:
    layer1 = "持有"

# 修复后：
if cycle in ("TRANSITION", "UNKNOWN", "BEAR") or confidence == "C":
    layer1 = "观察"
elif has_b_signal and confidence == "A":
    layer1 = "分批建仓（美股IBKR优先，标的由用户根据执行卡确认）"
elif has_b_signal and confidence == "B":
    layer1 = "持有，等待置信度升至A级后再建仓"
else:
    layer1 = "持有"
```

### 修改2：修复 generate_conclusions() 中 layer2 逻辑

第2层必须输出至少两条，第二条结合当日具体数据：

```python
# 修复后：
forbidden = []

# 第一条：基于周期的核心禁止（必须有）
if cycle in ("TRANSITION", "BEAR", "UNKNOWN"):
    forbidden.append("禁止加杠杆（当前处于" + cycle + "期间）")
elif cycle == "BULL_LATE":
    forbidden.append("禁止追高（BULL_LATE期间注意拥挤度）")
else:
    forbidden.append("禁止无计划追高")

# 第二条：基于当日数据的具体禁止（必须有）
if spx is not None and spx < -1.0:
    forbidden.append(f"禁止追跌抄底（SPX今日已跌{spx:.2f}%，下行动能未止）")
elif spx is not None and spx > 1.5:
    forbidden.append(f"禁止追涨（SPX今日已涨{spx:.2f}%，追高风险高）")
elif crypto_pct is not None and crypto_pct > 8:
    forbidden.append(f"禁止加仓加密（当前仓位{crypto_pct}%，接近10%上限）")
else:
    forbidden.append("禁止在数据不完整时执行任何新仓操作")

# 第三条（可选）：基于置信度
if confidence == "C":
    forbidden.append("禁止在置信度C级时执行任何新仓")
```

---

## ACCEPTANCE_CRITERIA

1. auto_briefing.py 修改完成
2. governance_runtime.py 前置检查通过
3. dry-run 验证：
   - TRANSITION/UNKNOWN/BEAR 时 layer1 = "观察"
   - BULL_MID A级时 layer1 = "分批建仓（美股IBKR优先...）"
   - layer2 至少两条，第二条含当日具体数据
4. 第0层和第1层不再自相矛盾
5. G-01/G-02/G-03/G-05 流程不受影响
6. 验收包 12 项字段完整
7. ChatGPT V6 明确输出 PASS

---

## CLOSE_CONDITION

1. generate_conclusions() 修复完成 ✓
2. dry-run 输出逻辑一致 ✓
3. layer2 至少两条 ✓
4. 既有流程不受影响 ✓
5. ChatGPT V6 输出 PASS ✓

---

## CODEX_EXECUTION

步骤0：governance_runtime.py 前置检查
  python scripts/governance_runtime.py \
    --task-id "TASK-2026-06-11-011" \
    --stage "implementation" \
    --approved "true" \
    --executor "Codex" \
    --acceptor "ChatGPT" \
    --thread "AI投研总控台 + 正式日报生产" \
    --task-type "governance" \
    --affects-account "false"

步骤1：修复 generate_conclusions() 中 layer1 和 layer2 逻辑

步骤2：dry-run 验证
  python scripts/auto_briefing.py --dry-run
  记录：layer1 内容 / layer2 条数和内容

步骤3：生成验收包
  路径：reports/validation/task-2026-06-11-011_validation_package.md

---

## 禁止事项

禁止修改 step1_cycle() / step3_signal() 等其他分析函数
禁止影响G-01/G-02/G-03/G-05已通过流程
禁止修改 skill_gate.py / governance_runtime.py
禁止连接券商接口
禁止自动下单
禁止自行最终验收
