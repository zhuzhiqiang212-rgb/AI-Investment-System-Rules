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
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

ITEM_TIMEOUT = 8


def _fetch_with_hard_timeout(url: str, timeout: int = ITEM_TIMEOUT) -> bytes:
    import concurrent.futures
    import urllib.request

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(
            lambda: urllib.request.urlopen(
                urllib.request.Request(
                    url, headers={"User-Agent": BROWSER_UA}),
                timeout=timeout
            ).read()
        )
        try:
            return future.result(timeout=timeout + 1)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"HARD_TIMEOUT: {url}")

# ─────────────────────────────────────────────
# 数据获取函数（变更项1：含来源和更新时间）
# ─────────────────────────────────────────────

def fetch_vix() -> dict:
    """获取 VIX 当日值。返回 {value, source, updated_at, status}"""
    try:
        import urllib.request
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?interval=1d&range=1d"
        req = urllib.request.Request(
            url, headers={"User-Agent": BROWSER_UA})
        with urllib.request.urlopen(req, timeout=8) as r:
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
        req = urllib.request.Request(
            url, headers={"User-Agent": BROWSER_UA})
        with urllib.request.urlopen(req, timeout=8) as r:
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
        req = urllib.request.Request(
            url, headers={"User-Agent": BROWSER_UA})
        with urllib.request.urlopen(req, timeout=8) as r:
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
    """获取 BTC 日涨跌幅，含备用数据源"""

    # 主源：Yahoo Finance
    urls = [
        "https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?interval=1d&range=2d",
        "https://query2.finance.yahoo.com/v8/finance/chart/BTC-USD?interval=1d&range=2d",
    ]

    for url in urls:
        try:
            time.sleep(2)
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
            print(f"[BTC] 尝试失败: {e}")
            continue

    # 备用源：Binance 公开API（免费，无需Key）
    try:
        binance_url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
        raw = _fetch_with_hard_timeout(binance_url, timeout=ITEM_TIMEOUT)
        data = json.loads(raw)
        change = round(float(data["priceChangePercent"]), 2)
        return {
            "value": change,
            "source": "Binance API (BTCUSDT)",
            "updated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
            "status": "OK"
        }
    except Exception as e:
        print(f"[BTC] Binance失败: {e}")
        return {
            "value": None,
            "source": "Yahoo Finance BTC-USD / Binance",
            "updated_at": "获取失败",
            "status": "DATA_GAP",
            "error": str(e)
        }


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
    print("[MAIN_START] daily_data_fetch 启动")
    parser = argparse.ArgumentParser(description="每日简报数据自动获取")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅显示数据，不写入模板")
    args = parser.parse_args(sys.argv[1:])
    print(f"[ARGS_PARSED] dry_run={args.dry_run}")

    today_str = datetime.now(JST).strftime("%Y-%m-%d")
    TOTAL_TIMEOUT = 45
    t_start = time.time()
    print(f"[TIMER_START] 总超时 {TOTAL_TIMEOUT}秒 已启动")

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
