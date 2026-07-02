# TASK PACKAGE
# TASK-2026-06-11-008

TASK_ID: TASK-2026-06-11-008
任务名称: G02_YESTERDAY_VALIDATION_V1
目标清单项: G-02（昨日验证机制）
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V6（≠ 执行人）
任务类型: 实施类（代码修改）
影响范围: scripts/auto_briefing.py（修改，新增昨日验证逻辑）
APPROVAL_REQUIRED: YES
审批状态: APPROVED（ChatGPT V6，2026-06-11）
是否涉及账户操作: NO
是否修改分析逻辑: NO
是否修改四报表结构: NO
是否新增治理文档: NO
是否影响G-01流程: NO

---

## 任务目标

auto_briefing.py 每次运行时，读取前一日结论，
对比今日实际市场数据，输出一行验证结果。

输出格式（插入三层结论之前）：

```
昨日判断：TRANSITION B级 → 今日实际：SPX -1.62% / VIX 22.22
验证结论：防守方向成立（TRANSITION期间市场下跌，判断有效）
```

若无前日记录（首次运行）：
```
昨日验证：无前日记录，跳过
```

---

## 修改规范

### 修改1：新增 get_yesterday_validation() 函数

```python
def get_yesterday_validation(today_results: dict) -> str:
    """
    读取 auto_briefing_log.json 中前一日结论，
    对比今日实际数据，返回验证结论字符串。
    """
    if not BRIEFING_LOG_PATH.exists():
        return "昨日验证：无前日记录，跳过"

    try:
        logs = json.loads(BRIEFING_LOG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return "昨日验证：日志读取失败，跳过"

    if len(logs) < 1:
        return "昨日验证：无前日记录，跳过"

    # 取最新一条（今日运行前的最后记录）
    yesterday_log = logs[-1]
    y_cycle  = yesterday_log.get("cycle", "UNKNOWN")
    y_conf   = yesterday_log.get("confidence", "?")
    y_layer0 = yesterday_log.get("layer0", "")
    y_date   = yesterday_log.get("data_date", "?")

    # 今日实际数据
    spx = today_results["spx"]["value"]
    vix = today_results["vix"]["value"]

    spx_str = f"SPX {spx:+.2f}%" if spx is not None else "SPX DATA_GAP"
    vix_str = f"VIX {vix:.2f}" if vix is not None else "VIX DATA_GAP"

    # 简单验证逻辑
    verdict = _validate(y_cycle, spx)

    return (
        f"昨日判断（{y_date}）：{y_cycle} {y_conf}级 — {y_layer0}\n"
        f"今日实际：{spx_str} / {vix_str}\n"
        f"验证结论：{verdict}"
    )


def _validate(cycle: str, spx) -> str:
    """简单验证：周期判断与市场方向是否一致"""
    if spx is None:
        return "SPX数据缺失，无法验证"
    if cycle in ("BEAR", "TRANSITION", "UNKNOWN"):
        if spx < 0:
            return "防守方向成立（市场下跌，判断有效）"
        elif spx > 1.0:
            return "防守判断偏保守（市场上涨，可复盘）"
        else:
            return "市场震荡，判断中性"
    elif cycle in ("BULL_MID", "BULL_EARLY"):
        if spx > 0:
            return "进攻方向成立（市场上涨，判断有效）"
        elif spx < -1.0:
            return "进攻判断偏激进（市场下跌，需复盘）"
        else:
            return "市场震荡，判断中性"
    elif cycle == "BULL_LATE":
        return f"BULL_LATE期间，SPX {spx:+.2f}%，建议人工复盘"
    return "无法自动验证，建议人工复盘"
```

### 修改2：在 main() 中，数据获取完成后调用验证函数

在 `display_data_status(results)` 之后，生成结论之前，插入：

```python
    # 昨日验证
    yesterday_validation = get_yesterday_validation(results)
```

### 修改3：在简报输出区插入验证行

在 `============` 分隔线之后、`第0层` 之前插入：

```python
    print(yesterday_validation)
    print("-" * 60)
```

### 修改4：将验证结果写入 write_latest_cards() 和 write_briefing_log()

在 write_latest_cards() 的日报内容中，三层结论之前加入验证行。
在 write_briefing_log() 的 entry 中新增字段：
```python
"yesterday_validation": yesterday_validation,
```

---

## ACCEPTANCE_CRITERIA

1. auto_briefing.py 修改完成
2. governance_runtime.py 前置检查通过
3. get_yesterday_validation() 函数存在
4. dry-run 测试：昨日验证行出现在输出中
   - 有前日记录时：显示昨日判断 + 今日实际 + 验证结论
   - 无前日记录时：显示"无前日记录，跳过"
5. 验证结果写入 latest_daily_report.md
6. 验证结果写入 auto_briefing_log.json 的 yesterday_validation 字段
7. G-01 自动写入闭环不受影响
8. 验收包 12 项字段完整
9. ChatGPT V6 明确输出 PASS

---

## CLOSE_CONDITION

1. 昨日验证行出现在 dry-run 输出 ✓
2. latest_daily_report.md 含验证行 ✓
3. auto_briefing_log.json 含 yesterday_validation 字段 ✓
4. G-01 流程不受影响 ✓
5. 验收包 12 项字段完整 ✓
6. ChatGPT V6 输出 PASS ✓

---

## CODEX_EXECUTION

步骤0：governance_runtime.py 前置检查
  python scripts/governance_runtime.py \
    --task-id "TASK-2026-06-11-008" \
    --stage "implementation" \
    --approved "true" \
    --executor "Codex" \
    --acceptor "ChatGPT" \
    --thread "AI投研总控台 + 正式日报生产" \
    --task-type "governance" \
    --affects-account "false"

步骤1：读取现有 auto_briefing.py，记录修改前大小

步骤2：按修改规范新增四处代码
  - get_yesterday_validation() 函数
  - _validate() 辅助函数
  - main() 中调用验证函数
  - 输出区插入验证行
  - write_latest_cards() 和 write_briefing_log() 写入验证结果

步骤3：dry-run 验证
  python scripts/auto_briefing.py --dry-run
  记录：昨日验证行是否出现 / 内容

步骤4：生成验收包
  路径：reports/validation/task-2026-06-11-008_validation_package.md

---

## 禁止事项

禁止修改分析逻辑（step1_cycle/step3_signal等）
禁止修改 G-01 已通过的写入流程
禁止扩大为复杂归因系统
禁止修改 skill_gate.py / governance_runtime.py
禁止连接券商接口
禁止自动下单
禁止自行最终验收
