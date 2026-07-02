# TASK PACKAGE
# TASK-2026-06-11-009

TASK_ID: TASK-2026-06-11-009
任务名称: G03_FOUR_CARD_DEDUP_V1
目标清单项: G-03（四报表去重）
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V6（≠ 执行人）
任务类型: 实施类（代码修改）
影响范围: scripts/auto_briefing.py（修改 write_latest_cards() 函数）
APPROVAL_REQUIRED: YES
审批状态: APPROVED（ChatGPT V6，2026-06-11）
是否涉及账户操作: NO
是否修改分析逻辑: NO
是否改变文件路径: NO
是否改变文件命名: NO
是否影响G-01流程: NO
是否影响G-02验证行: NO

---

## 任务目标

修改 write_latest_cards() 函数，
使四份 latest_*.md 各自只回答一个核心问题，
消除大段重复的三层结论内容。

四份文件各自边界：

  latest_daily_report.md
    回答：今天市场发生了什么，以及为什么重要
    内容：昨日验证结果 + 今日新变量（VIX/美债/SPX/BTC变化）
          + 今日结论 + 置信度变化原因

  latest_direction_card.md
    回答：当前资金主线和母方向是否变化
    内容：周期标签 + 置信度 + 方向维持/改变
          + 失效条件（何时判断需要重来）

  latest_risk_card.md
    回答：当前最大风险是什么，风险等级如何
    内容：TOP1风险 + 触发阈值 + 最不能做（1-3条）
          + 数据源状态（OK/DATA_GAP）

  latest_execution_card.md
    回答：今天应该买、卖、观察、回避什么
    内容：唯一动作 + 四账户边界
          + 执行前必须确认的事项

---

## 修改规范

### 修改：重写 write_latest_cards() 函数

```python
def write_latest_cards(conclusions: dict, results: dict,
                        today_str: str, next_steps: dict,
                        yesterday_validation: str = "") -> None:
    """写入四份差异化 latest_*.md 文件，各自只回答一个核心问题"""

    vix = results["vix"]["value"]
    tnx = results["tnx"]["value"]
    spx = results["spx"]["value"]
    btc = results["btc"]["value"]
    cycle  = conclusions["cycle"]
    conf   = conclusions["confidence"]
    layer0 = conclusions["layer0"]
    layer1 = conclusions["layer1"]
    layer2 = " / ".join(conclusions["layer2"])

    vix_str = f"{vix}" if vix is not None else "DATA_GAP"
    tnx_str = f"{tnx}%" if tnx is not None else "DATA_GAP"
    spx_str = f"{spx:+.2f}%" if spx is not None else "DATA_GAP"
    btc_str = f"{btc:+.2f}%" if btc is not None else "DATA_GAP"

    # 失效条件（基于周期）
    invalidation_map = {
        "BULL_MID":    "VIX突破25 / SPX单日跌幅超3% / ETF Flow连续转负",
        "TRANSITION":  "VIX突破30 / 关键支撑位跌破 / 数据冲突持续3日以上",
        "BEAR":        "VIX回落至20以下且SPX连续3日上涨",
        "BULL_EARLY":  "VIX重新上穿22 / 资金流转负",
        "BULL_LATE":   "拥挤度缓解 / 高Beta开始分化",
        "UNKNOWN":     "关键数据补齐后重新判断",
    }
    invalidation = invalidation_map.get(cycle, "请人工判断失效条件")

    # ── 文件1：日报 ── 回答"今天发生了什么"
    DAILY_REPORT_PATH.write_text(f"""# 今日日报 — {today_str}
生成时间：{today_str} JST　　来源：auto_briefing.py

{yesterday_validation}

## 今日市场变量
VIX：{vix_str}　10Y美债：{tnx_str}　SPX：{spx_str}　BTC：{btc_str}

## 今日结论
{layer0}
周期：{cycle}　置信度：{conf}

⚠️ 禁止自动下单。执行前人工确认。
""", encoding="utf-8")

    # ── 文件2：方向卡 ── 回答"主线方向是否变化"
    DIRECTION_CARD_PATH.write_text(f"""# 方向卡 — {today_str}
生成时间：{today_str} JST

## 当前方向
周期：{cycle}　置信度：{conf}
方向：{layer0}

## 失效条件
{invalidation}

## 方向小结
置信度{conf}级——{"方向明确，可按此执行" if conf in ("A","B") else "证据不足，仅观察，不执行"}

⚠️ 禁止自动下单。
""", encoding="utf-8")

    # ── 文件3：风险卡 ── 回答"最大风险是什么"
    RISK_CARD_PATH.write_text(f"""# 风险卡 — {today_str}
生成时间：{today_str} JST

## 最大风险
{layer2}

## 风险触发阈值
VIX当前：{vix_str}（警戒：>25）
SPX当前：{spx_str}（警戒：单日<-2%）
BTC当前：{btc_str}

## 数据源状态
VIX：{results['vix']['status']}　10Y：{results['tnx']['status']}
SPX：{results['spx']['status']}　BTC：{results['btc']['status']}

⚠️ 禁止自动下单。
""", encoding="utf-8")

    # ── 文件4：执行卡 ── 回答"今天该做什么"
    EXECUTION_CARD_PATH.write_text(f"""# 执行卡 — {today_str}
生成时间：{today_str} JST

## 唯一动作
{layer1}

## 四账户边界
富途：{layer1}
IBKR：{layer1}
SBI ：{layer1}
BF  ：{layer1}{"（BTC DATA_GAP，不操作）" if btc is None else ""}

## 执行前必须确认
□ 券商实时行情
□ 当前持仓和成本
□ 可用现金
□ 未成交挂单

NEXT_OWNER  : {next_steps['NEXT_OWNER']}
NEXT_ACTION : {next_steps['NEXT_ACTION']}

⚠️ 禁止自动下单。禁止修改账户文件。
""", encoding="utf-8")

    print(f"✓ 四份差异化 latest_*.md 已写入 [{today_str}]")
```

注意：函数签名新增 `yesterday_validation` 参数（默认空字符串），
main() 中调用时传入该参数。

---

## ACCEPTANCE_CRITERIA

1. auto_briefing.py 修改完成
2. governance_runtime.py 前置检查通过
3. dry-run 测试：四份文件内容边界清晰
   - latest_daily_report.md 含昨日验证行和今日变量
   - latest_direction_card.md 含失效条件，不含执行动作
   - latest_risk_card.md 含风险阈值，不含完整三层结论
   - latest_execution_card.md 含唯一动作和四账户边界
4. 四份文件不再大段重复同一段三层结论
5. G-01 自动写入闭环不受影响
6. G-02 昨日验证行正确传入日报
7. START_HERE.html 入口不受影响
8. 验收包 12 项字段完整
9. ChatGPT V6 明确输出 PASS

---

## CLOSE_CONDITION

1. write_latest_cards() 重写完成 ✓
2. dry-run 四份文件内容各自独立 ✓
3. G-01/G-02 流程不受影响 ✓
4. 验收包 12 项字段完整 ✓
5. ChatGPT V6 输出 PASS ✓

---

## CODEX_EXECUTION

步骤0：governance_runtime.py 前置检查
  python scripts/governance_runtime.py \
    --task-id "TASK-2026-06-11-009" \
    --stage "implementation" \
    --approved "true" \
    --executor "Codex" \
    --acceptor "ChatGPT" \
    --thread "AI投研总控台 + 正式日报生产" \
    --task-type "governance" \
    --affects-account "false"

步骤1：读取现有 auto_briefing.py，记录修改前大小

步骤2：重写 write_latest_cards() 函数
  按修改规范替换现有函数体
  main() 调用时传入 yesterday_validation 参数

步骤3：dry-run 验证
  python scripts/auto_briefing.py --dry-run
  记录四份文件内容摘要（各自第一行和关键字段）

步骤4：生成验收包
  路径：reports/validation/task-2026-06-11-009_validation_package.md

---

## 禁止事项

禁止修改分析逻辑（step1_cycle/step3_signal等）
禁止改变文件路径或文件名
禁止影响G-01/G-02已通过流程
禁止修改 skill_gate.py / governance_runtime.py
禁止连接券商接口
禁止自动下单
禁止自行最终验收
