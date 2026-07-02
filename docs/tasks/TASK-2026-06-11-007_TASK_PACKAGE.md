# TASK PACKAGE
# TASK-2026-06-11-007

TASK_ID: TASK-2026-06-11-007
任务名称: G01_SOP_AUTO_PIPELINE_V1
目标清单项: G-01（SOP自动化串联）
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V6（≠ 执行人）
任务类型: 实施类（代码修改）
影响范围: scripts/auto_briefing.py（修改，新增写入逻辑）
APPROVAL_REQUIRED: YES
审批状态: APPROVED（ChatGPT V6，2026-06-11）
是否涉及账户操作: NO
是否修改分析逻辑: NO
是否修改四报表结构: NO
是否新增治理文档: NO

---

## 任务目标

用户输入 Y 确认后，auto_briefing.py 自动完成：
1. 写入 latest_daily_report.md
2. 写入 latest_direction_card.md
3. 写入 latest_risk_card.md
4. 写入 latest_execution_card.md
5. 更新 START_HERE.html 中的日期和四报表内容

无需用户额外操作。

---

## 修改规范

### 修改1：新增四路径常量（文件顶部）

```python
DAILY_REPORT_PATH   = ROOT / "reports" / "daily" / "latest_daily_report.md"
DIRECTION_CARD_PATH = ROOT / "reports" / "daily" / "latest_direction_card.md"
RISK_CARD_PATH      = ROOT / "reports" / "daily" / "latest_risk_card.md"
EXECUTION_CARD_PATH = ROOT / "reports" / "daily" / "latest_execution_card.md"
START_HERE_PATH     = ROOT / "START_HERE.html"
```

### 修改2：新增 write_latest_cards() 函数

```python
def write_latest_cards(conclusions: dict, results: dict,
                        today_str: str, next_steps: dict) -> None:
    """写入四份 latest_*.md 文件"""

    vix_val = results["vix"]["value"]
    tnx_val = results["tnx"]["value"]
    spx_val = results["spx"]["value"]
    cycle   = conclusions["cycle"]
    conf    = conclusions["confidence"]
    layer0  = conclusions["layer0"]
    layer1  = conclusions["layer1"]
    layer2  = " / ".join(conclusions["layer2"])

    # latest_daily_report.md
    DAILY_REPORT_PATH.write_text(f"""# AUTO DECISION BRIEFING — 今日日报
生成时间：{today_str} JST
来源：auto_briefing.py（TASK-2026-06-11-003 REV-A）

## 今日结论
周期：{cycle}　置信度：{conf}

第0层 今日结论：{layer0}
第1层 唯一动作：{layer1}
第2层 最不能做：{layer2}

## 数据源状态
VIX    ：{results['vix']['status']}（{vix_val}）
10Y美债：{results['tnx']['status']}（{tnx_val}%）
SPX    ：{results['spx']['status']}（{spx_val}%）
BTC    ：{results['btc']['status']}

## NEXT
NEXT_OWNER  : {next_steps['NEXT_OWNER']}
NEXT_ACTION : {next_steps['NEXT_ACTION']}
NEXT_THREAD : {next_steps['NEXT_THREAD']}

⚠️ 禁止自动下单。执行前必须用户人工确认。
""", encoding="utf-8")

    # latest_direction_card.md
    DIRECTION_CARD_PATH.write_text(f"""# Direction Card — {today_str}
生成时间：{today_str} JST

## 方向结论
周期：{cycle}　置信度：{conf}
第0层：{layer0}

## 唯一动作：{layer1}

⚠️ 禁止自动下单。
""", encoding="utf-8")

    # latest_risk_card.md
    RISK_CARD_PATH.write_text(f"""# Risk Card — {today_str}
生成时间：{today_str} JST

## 最不能做
{layer2}

## 数据风险
VIX {vix_val} / 美债 {tnx_val}% / SPX {spx_val}%
BTC：{results['btc']['status']}

⚠️ 禁止自动下单。
""", encoding="utf-8")

    # latest_execution_card.md
    EXECUTION_CARD_PATH.write_text(f"""# Execution Card — {today_str}
生成时间：{today_str} JST

## 执行结论
唯一动作：{layer1}
置信度：{conf}

## 四账户边界
全账户：{layer1}，禁止自动下单
执行前人工确认：券商实时行情 / 持仓 / 现金 / 成本 / 挂单

⚠️ 禁止自动下单。禁止修改账户文件。
""", encoding="utf-8")

    print(f"✓ 四份 latest_*.md 已写入 [{today_str}]")
```

### 修改3：新增 update_start_here() 函数

```python
def update_start_here(today_str: str, conclusions: dict) -> None:
    """更新 START_HERE.html 中的日期字符串"""
    if not START_HERE_PATH.exists():
        print(f"⚠ START_HERE.html 未找到，跳过更新")
        return
    content = START_HERE_PATH.read_text(encoding="utf-8", errors="ignore")
    # 替换日期（格式 YYYY-MM-DD）
    import re
    yesterday = re.findall(r'\d{4}-\d{2}-\d{2}', content)
    if yesterday:
        old_date = yesterday[0]
        if old_date != today_str:
            content = content.replace(old_date, today_str)
            START_HERE_PATH.write_text(content, encoding="utf-8")
            print(f"✓ START_HERE.html 日期已更新 {old_date} → {today_str}")
        else:
            print(f"✓ START_HERE.html 日期已是今日，无需更新")
    else:
        print("⚠ START_HERE.html 中未找到日期字符串，跳过更新")
```

### 修改4：在 main() 用户确认 Y 之后调用两个新函数

在现有写入模板的代码块之后，追加：

```python
    # 写入四份 latest_*.md
    write_latest_cards(conclusions, results, today_str, next_steps)

    # 更新 START_HERE.html
    update_start_here(today_str, conclusions)
```

---

## ACCEPTANCE_CRITERIA

1. auto_briefing.py 修改完成，新增三处代码
2. governance_runtime.py 前置检查通过
3. Codex dry-run 测试：--dry-run 模式不写入 latest_* 和 START_HERE
4. 实际运行（非dry-run）用户输入 Y 后：
   - latest_daily_report.md 写入成功，日期为当日
   - latest_direction_card.md 写入成功
   - latest_risk_card.md 写入成功
   - latest_execution_card.md 写入成功
   - START_HERE.html 日期更新为当日
5. 验收包含五份文件实际路径和修改时间
6. ChatGPT V6 明确输出 PASS

---

## CLOSE_CONDITION

1. 五项写入全部成功 ✓
2. dry-run 不触发写入 ✓
3. 验收包 12 项字段完整 ✓
4. ChatGPT V6 输出 PASS ✓

---

## CODEX_EXECUTION

步骤0：governance_runtime.py 前置检查
  python scripts/governance_runtime.py \
    --task-id "TASK-2026-06-11-007" \
    --stage "implementation" \
    --approved "true" \
    --executor "Codex" \
    --acceptor "ChatGPT" \
    --thread "AI投研总控台 + 正式日报生产" \
    --task-type "governance" \
    --affects-account "false"

步骤1：读取现有 auto_briefing.py，记录修改前大小

步骤2：按修改规范新增四处代码
  - 常量区新增五个路径常量
  - 新增 write_latest_cards() 函数
  - 新增 update_start_here() 函数
  - main() 中 Y 确认后调用两个新函数

步骤3：dry-run 验证（不写入）
  python scripts/auto_briefing.py --dry-run
  确认 latest_*.md 和 START_HERE.html 未被修改

步骤4：生成验收包
  路径：reports/validation/task-2026-06-11-007_validation_package.md
  须含：
    修改前后文件大小
    dry-run 确认
    五份文件路径
    写入时间（待用户实际运行后补充）
    12项标准验收字段

---

## 禁止事项

禁止修改分析逻辑（step1_cycle/step3_signal等函数）
禁止修改四报表结构定义
禁止修改 skill_gate.py / governance_runtime.py
禁止连接券商接口
禁止自动下单
禁止自行最终验收
