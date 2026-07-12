from __future__ import annotations

"""A8 真建 · holdings_true 自动生成器（股数沿用 + 今日OpenD现价·不伪造）

总则 A8：3 个非富途账户（SBI/IBKR/bitFlyer）无交易则股数不变，只在董事长报交易时更新；
每天变的只是价格（今日 OpenD 实时刷新）。本脚本：
  1) 从最近一份 confirmed 的 holdings_true 沿用股数/账户拆分（A8·无交易不变）。
  2) 连 OpenD 抓今日实时价嵌进去；某标的抓不到→价 null + 如实标 quote_status，绝不伪造。
  3) 写 data/accounts/holdings_true_{date}.json，指纹写清股数来源(A8沿用)与价来源(今日OpenD)。

下游 holdings_review_against_chain 仍会用 OpenD 再刷一次做权威价；本表的嵌入价是"今日真价快照"。
只读不下单。
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ACCOUNTS_DIR = ROOT / "data" / "accounts"
JST = timezone(timedelta(hours=9))

sys.path.insert(0, str(ROOT / "scripts"))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")
    if "�" in path.read_text(encoding="utf-8"):
        raise RuntimeError(f"garble marker (EF BF BD) found after write: {path}")


def find_latest_confirmed_base(before_date: str) -> Path | None:
    """取 before_date 之前(含更早)最近一份含 confirmed 股数的 holdings_true。"""
    cands = []
    for p in ACCOUNTS_DIR.glob("holdings_true_*.json"):
        stem = p.stem.replace("holdings_true_", "")
        if not stem.isdigit():
            continue
        if stem >= before_date:  # 只沿用更早的 confirmed，不回读当天/未来
            continue
        try:
            data = _read_json(p)
        except Exception:
            continue
        if any(h.get("quantity_status") == "confirmed" for h in data.get("holdings", [])):
            cands.append((stem, p))
    if not cands:
        return None
    cands.sort()
    return cands[-1][1]


def fetch_today_prices(symbols: list[str]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """连一次 OpenD，逐标的取今日实时价。抓不到→价 null + 状态，不伪造。"""
    from realtime_price import connect_quote_context, get_realtime_price

    ctx, attempts = connect_quote_context(max_retries=2, wait_seconds=2)
    price_map: dict[str, dict[str, Any]] = {}
    if ctx is None:
        for s in symbols:
            price_map[s] = {"price": None, "status": "FAIL", "reason": "OpenD 连接失败·待刷新", "data_date": None}
        return price_map, attempts
    try:
        for s in symbols:
            q = get_realtime_price(s, ctx=ctx)
            price_map[s] = {
                "price": q.get("price"),
                "status": q.get("status"),
                "reason": q.get("reason"),
                "data_date": q.get("data_date"),
                "market_state": q.get("market_state"),
                "used_field": q.get("used_field"),
            }
    finally:
        try:
            ctx.close()
        except Exception:
            pass
    return price_map, attempts


def build(date: str) -> dict[str, Any]:
    base_path = find_latest_confirmed_base(date)
    if base_path is None:
        raise FileNotFoundError(f"找不到可沿用的 confirmed holdings_true 基表(早于 {date})")
    base = _read_json(base_path)
    base_date = base_path.stem.replace("holdings_true_", "")
    base_holdings = base.get("holdings", [])

    symbols = [str(h.get("symbol")) for h in base_holdings if h.get("symbol")]
    price_map, attempts = fetch_today_prices(symbols)

    ok = sum(1 for s in symbols if price_map.get(s, {}).get("status") == "OK")
    holdings_out = []
    for h in base_holdings:
        sym = str(h.get("symbol"))
        q = price_map.get(sym, {})
        row = {
            "symbol": h.get("symbol"),
            "name": h.get("name"),
            "total_quantity": h.get("total_quantity"),
            "quantity_status": h.get("quantity_status"),   # A8：沿用，不变
            "accounts": h.get("accounts"),
            "currency_hint": h.get("currency_hint"),
        }
        if q.get("status") == "OK" and q.get("price") is not None:
            row["realtime_price"] = q["price"]
            row["price_data_date"] = q.get("data_date")
            row["price_market_state"] = q.get("market_state")
            row["quote_status"] = "OK"
            row["price_source"] = "OpenD realtime (holdings_true_autobuild)"
        else:
            row["realtime_price"] = None
            row["quote_status"] = q.get("status") or "FAIL"
            row["price_note"] = (q.get("reason") or "今日价待刷新") + "·下游 holdings_review 会再刷 OpenD"
        holdings_out.append(row)

    return {
        "task_id": f"AUTO-{date}-holdings_true_A8",
        "mode": "TRUE_HOLDINGS_BASE_TABLE",
        "date": date,
        "generated_at": datetime.now(JST).isoformat(),
        "fingerprint": {
            "share_count_source": f"A8·股数沿用最近 confirmed 基表 {base_path.name}（非富途账户无交易则不变，未报新交易→沿用）",
            "quote_source": f"今日 OpenD 实时价(realtime_price)·{ok}/{len(symbols)} 取到；未取到者价=null 如实标、不伪造",
            "built_by": "holdings_true_autobuild.py（机器自动·股数沿用+今日OpenD现价）",
            "no_trade": True,
            "no_publish": True,
            "a8_note": "总则A8：3个非富途账户(SBI/IBKR/bitFlyer)无交易则股数不变；每天变的只是价格。有交易请补截图更正股数。",
            "verify_note": "非伪造：股数=confirmed沿用可回溯到基表；价=今日OpenD可回溯到 data_date。",
        },
        "merge_check": base.get("merge_check", {}),
        "price_connection_attempts": attempts,
        "holdings": holdings_out,
        "safety": {"read_only": True, "place_order_called": False, "openD_called": True, "published": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="A8真建·holdings_true自动生成(股数沿用+今日OpenD现价)")
    parser.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d"))
    args = parser.parse_args()

    result = build(args.date)
    out_path = ACCOUNTS_DIR / f"holdings_true_{args.date}.json"
    _write_json(out_path, result)
    fp = result["fingerprint"]
    print(f"[OK] 写出 {out_path}")
    print("股数来源:", fp["share_count_source"])
    print("价来源:", fp["quote_source"])
    ok = sum(1 for h in result["holdings"] if h.get("quote_status") == "OK")
    print(f"持仓 {len(result['holdings'])} 项；今日价 OK {ok} 项")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
