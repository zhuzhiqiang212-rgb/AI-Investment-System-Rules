# TASK PACKAGE
# TASK-2026-06-11-012

TASK_ID: TASK-2026-06-11-012
任务名称: G06_BTC_SIGNAL_FIX_V1
目标清单项: G-06（BTC信号修复）
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V6（≠ 执行人）
任务类型: 实施类（代码修复）
影响范围: scripts/daily_data_fetch.py（修复 fetch_btc_change()）
APPROVAL_REQUIRED: YES
审批状态: APPROVED（ChatGPT V6，2026-06-11）
是否涉及账户操作: NO
是否影响既有流程: NO

---

## 问题根因

BTC-USD 长期 DATA_GAP 导致：
1. 4维周期判断缺失第4个维度
2. 置信度无法达到 A 级
3. 加密信号长期降 C 级

诊断方向：
  Yahoo Finance BTC-USD 可能需要不同的 endpoint
  或响应格式与其他标的不同导致解析失败。

---

## 修复规范

### 修复1：fetch_btc_change() 增加备用数据源

```python
def fetch_btc_change() -> dict:
    """获取 BTC 日涨跌幅，含备用数据源"""

    # 主源：Yahoo Finance
    urls = [
        "https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?interval=1d&range=2d",
        "https://query2.finance.yahoo.com/v8/finance/chart/BTC-USD?interval=1d&range=2d",
    ]

    for url in urls:
        try:
            raw = _fetch_with_hard_timeout(url, timeout=ITEM_TIMEOUT)
            data = json.loads(raw)
            result = data["chart"]["result"]
            if not result:
                continue
            closes = result[0]["indicators"]["quote"][0]["close"]
            closes = [c for c in closes if c is not None]
            if len(closes) < 2:
                continue
            change = round((closes[-1] / closes[-2] - 1) * 100, 2)
            return {
                "value": change,
                "source": url,
                "updated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
                "status": "OK"
            }
        except Exception as e:
            continue

    # 备用源：CoinGecko 公开API（无需key）
    try:
        cg_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        raw = _fetch_with_hard_timeout(cg_url, timeout=ITEM_TIMEOUT)
        data = json.loads(raw)
        change = round(data["bitcoin"]["usd_24h_change"], 2)
        return {
            "value": change,
            "source": "CoinGecko API",
            "updated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
            "status": "OK"
        }
    except Exception as e:
        return {
            "value": None,
            "source": "Yahoo Finance BTC-USD / CoinGecko",
            "updated_at": "获取失败",
            "status": "DATA_GAP",
            "error": str(e)
        }
```

---

## ACCEPTANCE_CRITERIA

1. daily_data_fetch.py 修复完成
2. governance_runtime.py 前置检查通过
3. Codex dry-run：BTC 返回 OK（有效值）
4. 用户本地 dry-run：BTC 返回 OK
5. auto_briefing.py --dry-run：4维全部有效
6. 验收包 12 项字段完整
7. ChatGPT V6 明确输出 PASS

---

## CLOSE_CONDITION

1. fetch_btc_change() 修复完成，含备用源 ✓
2. 用户本地 BTC : OK ✓
3. 4维周期判断维度数量达到4 ✓
4. 验收包完整 ✓
5. ChatGPT V6 输出 PASS ✓

---

## CODEX_EXECUTION

步骤0：governance_runtime.py 前置检查

步骤1：重写 fetch_btc_change()
  主源：Yahoo Finance query1 + query2 双端点
  备用源：CoinGecko 公开API

步骤2：Codex dry-run
  python scripts/daily_data_fetch.py --dry-run
  记录：BTC 状态 / 值 / 使用哪个数据源

步骤3：auto_briefing dry-run
  python scripts/auto_briefing.py --dry-run
  记录：有效维度数量是否达到4

步骤4：生成验收包
  路径：reports/validation/task-2026-06-11-012_validation_package.md

---

## 禁止事项

禁止修改其他 fetch 函数
禁止影响既有 G-01 至 G-05 流程
禁止修改 skill_gate.py / governance_runtime.py
禁止连接券商接口
禁止自动下单
禁止自行最终验收
