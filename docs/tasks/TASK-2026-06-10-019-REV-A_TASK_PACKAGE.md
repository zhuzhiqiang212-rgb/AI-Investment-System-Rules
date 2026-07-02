# TASK PACKAGE
# TASK-2026-06-10-019 REV-A

TASK_ID: TASK-2026-06-10-019 REV-A
任务名称: DAILY_DATA_AUTO_FETCH_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 实施类（代码）
影响范围:
  scripts/daily_data_fetch.py（新建）
  docs/daily_briefing_template_v1.md（P1/P2改进）
  data/daily_fetch_log.json（新建，确认日志）
APPROVAL_REQUIRED: YES
审批状态: PENDING（REV-A，等待 ChatGPT 重新审批）
旧版本状态: TASK-2026-06-10-019 原始版自动作废
是否涉及账户操作: NO
是否涉及规则变更: NO
是否生成交易指令: NO
是否修改账户数据: NO

---

## 审批变更项（已合并，共5项）

1. 数据源状态显示
   写入模板前必须显示每项数据的来源和更新时间。

2. 数据获取失败降级规则
   单项失败标记 DATA_GAP，允许用户手动填写，不阻断整体。

3. 用户确认日志
   用户输入 Y 后，记录确认时间和数据摘要，用于归因。

4. 禁止覆盖历史记录
   每天只写入当日区域，不覆盖历史 Daily Briefing。

5. 验收指标：实际计时验证从3分钟缩短到1分钟以内。

---

## 交付内容

### 文件1：scripts/daily_data_fetch.py（新建）

完整代码规范：

```python
#!/usr/bin/env python3
"""
daily_data_fetch.py
每日简报数据自动获取脚本
TASK-2026-06-10-019 REV-A

功能：
  自动获取6项必填数据，显示数据源状态，
  经用户确认后写入 daily_briefing_template_v1.md 当日区域。
  禁止覆盖历史记录。
  所有确认记录写入 data/daily_fetch_log.json。

标准运行命令：
  python scripts/daily_data_fetch.py
  python scripts/daily_data_fetch.py --dry-run  （仅显示，不写入）
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"G:\我的云端硬盘\AI_Investment_System")
TEMPLATE_PATH = ROOT / "docs" / "daily_briefing_template_v1.md"
FETCH_LOG_PATH = ROOT / "data" / "daily_fetch_log.json"
JST = timezone(timedelta(hours=9))

# ─────────────────────────────────────────────
# 数据获取函数（变更项1：含来源和更新时间）
# ─────────────────────────────────────────────

def fetch_vix() -> dict:
    """获取 VIX 当日值。返回 {value, source, updated_at, status}"""
    try:
        import urllib.request
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?interval=1d&range=1d"
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        return {
            "value": round(price, 2),
            "source": "Yahoo Finance (^VIX)",
            "updated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
            "status": "OK"
        }
    except Exception as e:
        return {"value": None, "source": "Yahoo Finance (^VIX)",
                "updated_at": "获取失败", "status": "DATA_GAP", "error": str(e)}


def fetch_tnx() -> dict:
    """获取 10Y 美债收益率。"""
    try:
        import urllib.request
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ETNX?interval=1d&range=1d"
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        return {
            "value": round(price, 3),
            "source": "Yahoo Finance (^TNX)",
            "updated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
            "status": "OK"
        }
    except Exception as e:
        return {"value": None, "source": "Yahoo Finance (^TNX)",
                "updated_at": "获取失败", "status": "DATA_GAP", "error": str(e)}


def fetch_spx_change() -> dict:
    """获取 SPX 日涨跌幅（%）。"""
    try:
        import urllib.request
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?interval=1d&range=2d"
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        change = round((closes[-1] / closes[-2] - 1) * 100, 2) if len(closes) >= 2 else None
        return {
            "value": change,
            "source": "Yahoo Finance (^GSPC)",
            "updated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
            "status": "OK" if change is not None else "DATA_GAP"
        }
    except Exception as e:
        return {"value": None, "source": "Yahoo Finance (^GSPC)",
                "updated_at": "获取失败", "status": "DATA_GAP", "error": str(e)}


def fetch_btc_change() -> dict:
    """获取 BTC 日涨跌幅（%）。"""
    try:
        import urllib.request
        url = "https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?interval=1d&range=2d"
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        change = round((closes[-1] / closes[-2] - 1) * 100, 2) if len(closes) >= 2 else None
        return {
            "value": change,
            "source": "Yahoo Finance (BTC-USD)",
            "updated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
            "status": "OK" if change is not None else "DATA_GAP"
        }
    except Exception as e:
        return {"value": None, "source": "Yahoo Finance (BTC-USD)",
                "updated_at": "获取失败", "status": "DATA_GAP", "error": str(e)}


def fetch_user_config() -> dict:
    """读取用户本地配置（加密仓位占比、本月收益率）。"""
    config_path = ROOT / "data" / "user_config.json"
    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)
        return {
            "crypto_position_pct": cfg.get("crypto_position_pct", None),
            "monthly_return_pct":  cfg.get("monthly_return_pct", None),
            "source": str(config_path),
            "status": "OK"
        }
    except FileNotFoundError:
        return {
            "crypto_position_pct": None,
            "monthly_return_pct": None,
            "source": str(config_path),
            "status": "DATA_GAP",
            "error": "user_config.json 不存在，请手动填写"
        }


# ─────────────────────────────────────────────
# 数据源状态显示（变更项1）
# ─────────────────────────────────────────────

def display_data_status(results: dict) -> None:
    """显示所有字段的数据源、值、更新时间、状态。"""
    print("\n" + "=" * 60)
    print("DAILY DATA FETCH — 数据源状态")
    print("=" * 60)

    fields = [
        ("VIX",        results["vix"]),
        ("10Y美债",    results["tnx"]),
        ("SPX日涨跌",  results["spx"]),
        ("BTC日涨跌",  results["btc"]),
        ("加密仓位%",  {"value": results["config"]["crypto_position_pct"],
                        "source": results["config"]["source"],
                        "updated_at": "用户配置",
                        "status": results["config"]["status"]}),
        ("本月收益%",  {"value": results["config"]["monthly_return_pct"],
                        "source": "trade_record_log / user_config",
                        "updated_at": "用户记录",
                        "status": results["config"]["status"]}),
    ]

    gap_count = 0
    for name, r in fields:
        status_tag = "✓" if r["status"] == "OK" else "⚠ DATA_GAP"
        val_str = str(r["value"]) if r["value"] is not None else "— 获取失败，请手动填写"
        if r["status"] != "OK":
            gap_count += 1
        print(f"  {name:<12} {val_str:<15} "
              f"来源: {r.get('source','—'):<35} "
              f"更新: {r.get('updated_at','—'):<22} {status_tag}")

    print("=" * 60)
    if gap_count > 0:
        print(f"  ⚠ {gap_count} 项数据获取失败（DATA_GAP），"
              "请写入模板后手动补填。")
        print("  置信度提示：必填字段缺失≥3项时，整体置信度降C级。")
    else:
        print("  ✓ 全部数据获取成功。")
    print()


# ─────────────────────────────────────────────
# 模板写入（变更项4：禁止覆盖历史）
# ─────────────────────────────────────────────

def write_to_template(results: dict, today_str: str, dry_run: bool) -> bool:
    """
    将数据写入 daily_briefing_template_v1.md 当日区域。
    禁止覆盖已存在的当日或历史记录。
    """
    template = TEMPLATE_PATH.read_text(encoding="utf-8", errors="ignore")

    # 检查当日记录是否已存在（变更项4）
    date_marker = f"日期: {today_str}"
    if date_marker in template:
        print(f"⚠ 当日记录 [{today_str}] 已存在，禁止覆盖。")
        print("  若需更新，请手动修改模板中对应区域。")
        return False

    def fmt(r: dict, suffix: str = "") -> str:
        if r["value"] is not None:
            return f"{r['value']}{suffix}"
        return "DATA_GAP（请手动填写）"

    # 构建当日填写区块
    new_block = f"""
────────────────────────────────────────
当日填写区 [{today_str}]（由 daily_data_fetch.py 自动写入）
────────────────────────────────────────
日期                  : {today_str}
VIX当日值             : {fmt(results['vix'])}
  来源: {results['vix']['source']} | 更新: {results['vix']['updated_at']}
10Y美债收益率          : {fmt(results['tnx'], '%')}
  来源: {results['tnx']['source']} | 更新: {results['tnx']['updated_at']}
SPX日涨跌             : {fmt(results['spx'], '%')}
  来源: {results['spx']['source']} | 更新: {results['spx']['updated_at']}
BTC日涨跌             : {fmt(results['btc'], '%')}
  来源: {results['btc']['source']} | 更新: {results['btc']['updated_at']}
加密仓位占总资产        : {results['config']['crypto_position_pct'] or 'DATA_GAP（请手动填写）'}
本月已实现收益率        : {results['config']['monthly_return_pct'] or 'DATA_GAP（请手动填写）'}
最大持仓浮亏           : DATA_GAP（请手动填写）

"""

    if dry_run:
        print("[DRY RUN] 以下内容将写入模板（未实际写入）：")
        print(new_block)
        return True

    # 写入模板末尾（追加，不覆盖）
    with open(TEMPLATE_PATH, "a", encoding="utf-8") as f:
        f.write(new_block)
    print(f"✓ 当日数据已写入模板 [{today_str}]")
    return True


# ─────────────────────────────────────────────
# 用户确认日志（变更项3）
# ─────────────────────────────────────────────

def write_confirmation_log(results: dict, today_str: str) -> None:
    """用户确认后，写入确认时间和数据摘要。"""
    FETCH_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    existing = []
    if FETCH_LOG_PATH.exists():
        try:
            existing = json.loads(
                FETCH_LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            existing = []

    entry = {
        "date": today_str,
        "confirmed_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "data_summary": {
            "vix":   results["vix"]["value"],
            "tnx":   results["tnx"]["value"],
            "spx":   results["spx"]["value"],
            "btc":   results["btc"]["value"],
            "crypto_pct": results["config"]["crypto_position_pct"],
            "monthly_return": results["config"]["monthly_return_pct"],
        },
        "gap_fields": [
            k for k, v in {
                "vix": results["vix"], "tnx": results["tnx"],
                "spx": results["spx"], "btc": results["btc"],
            }.items() if v["status"] != "OK"
        ]
    }

    existing.append(entry)
    FETCH_LOG_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"✓ 确认日志已写入：{FETCH_LOG_PATH}")


# ─────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="每日简报数据自动获取")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅显示数据，不写入模板")
    args = parser.parse_args()

    today_str = datetime.now(JST).strftime("%Y-%m-%d")
    t_start = time.time()

    print(f"\n[daily_data_fetch] 开始获取数据 — {today_str}")

    # 获取数据
    results = {
        "vix":    fetch_vix(),
        "tnx":    fetch_tnx(),
        "spx":    fetch_spx_change(),
        "btc":    fetch_btc_change(),
        "config": fetch_user_config(),
    }

    # 显示数据源状态（变更项1）
    display_data_status(results)

    t_fetch = time.time() - t_start
    print(f"数据获取耗时：{t_fetch:.2f} 秒\n")

    if args.dry_run:
        write_to_template(results, today_str, dry_run=True)
        print("[DRY RUN] 完成，未写入任何文件。")
        sys.exit(0)

    # 用户确认（变更项3，不可跳过）
    print("请确认以上数据后输入 Y 写入模板，或输入 N 取消：")
    answer = input("  > ").strip().upper()

    if answer != "Y":
        print("已取消。模板未被修改。")
        sys.exit(0)

    t_confirm = time.time() - t_start

    # 写入模板（变更项4：禁止覆盖历史）
    success = write_to_template(results, today_str, dry_run=False)

    if success:
        # 写入确认日志（变更项3）
        write_confirmation_log(results, today_str)

    t_total = time.time() - t_start
    print(f"\n总耗时：{t_total:.2f} 秒（目标 ≤60 秒）")
    if t_total <= 60:
        print("✓ 1分钟目标达成")
    else:
        print(f"⚠ 超过1分钟目标（实际 {t_total:.1f} 秒），请检查网络")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
```

---

### 文件2：docs/daily_briefing_template_v1.md 改进（P1+P2）

P1改进：唯一入口声明移至文件第一行
  第一行固定为：
  "DAILY DECISION BRIEFING — 唯一入口"

P2改进：查表步骤1-5增加引擎文件醒目标识
  步骤1 [周期定位] 查表文件: cycle_positioning_engine_v1.md
  步骤2 [资产配置] 查表文件: asset_allocation_engine_v1.md
  步骤3 [买入触发] 查表文件: buy_trigger_engine_v1.md
  步骤4 [仓位计算] 查表文件: position_sizing_engine_v1.md
  步骤5 [止盈检查] 查表文件: take_profit_system_v1.md

---

## ACCEPTANCE_CRITERIA

1. scripts/daily_data_fetch.py 已写入 scripts/
2. 数据源状态显示含来源+更新时间（变更项1）
3. 单项失败标记 DATA_GAP，不阻断整体（变更项2）
4. 用户确认日志写入 data/daily_fetch_log.json（变更项3）
5. 禁止覆盖历史记录，当日已有记录时拒绝写入（变更项4）
6. 实际计时验证总耗时 ≤60秒（变更项5）
7. P1改进：唯一入口声明在 daily_briefing_template 第一行
8. P2改进：步骤1-5旁有引擎文件标识
9. governance_runtime.py 前置检查通过
10. dry-run 测试成功运行并记录实际输出
11. 验收包 12 项字段完整
12. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. daily_data_fetch.py 已写入 scripts/ ✓
2. dry-run 测试实际运行并输出数据源状态 ✓
3. 变更项1-5全部实现 ✓
4. P1/P2改进已实施于 daily_briefing_template_v1.md ✓
5. 实际计时 ≤60秒 ✓
6. 验收包 12 项字段完整 ✓
7. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

步骤0：governance_runtime.py 前置检查
  python scripts/governance_runtime.py \
    --task-id "TASK-2026-06-10-019" \
    --stage "implementation" \
    --approved "true" \
    --executor "Codex" \
    --acceptor "ChatGPT" \
    --thread "AI投研总控台 + 正式日报生产" \
    --task-type "governance" \
    --affects-account "false"

步骤1：生成 daily_data_fetch.py，写入 scripts/
  按本 TASK_PACKAGE 代码规范完整生成

步骤2：运行 dry-run 测试
  python scripts/daily_data_fetch.py --dry-run
  记录：实际获取数据结果 / DATA_GAP字段 / 总耗时

步骤3：实施 P1/P2 改进
  修改 daily_briefing_template_v1.md：
  - 唯一入口声明移至第一行
  - 步骤1-5增加引擎文件标识

步骤4：生成验收包
  路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
        task-2026-06-10-019_validation_package.md
  须含：
    section 1：governance_runtime 前置检查结果
    section 2：daily_data_fetch.py 写入确认
    section 3：dry-run 实际输出（含耗时）
    section 4：变更项1-5逐项确认
    section 5：P1/P2改进确认
    section 6：12项标准验收字段

---

## 禁止事项

禁止修改 skill_gate.py / governance_runtime.py
禁止修改 dashboard.html
禁止生成日报
禁止涉及账户操作
禁止自动下单
禁止跳过用户确认步骤直接写入模板
禁止在已有当日记录时覆盖
禁止自行最终验收
禁止在 governance_runtime.py 返回1时继续执行
