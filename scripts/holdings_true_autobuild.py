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


# ⚠账户名在本系统数据里写作「富通」(不是"富途")——写错就匹配不到、会把富途仓当"新持仓"重复加一遍。
FUTU_ALIASES = ("富通", "富途", "Futu", "FUTU", "moomoo")
NON_OPEND_ACCOUNTS = ("SBI", "IBKR", "bitFlyer")


def _apply_futu_live(base_holdings: list, date: str) -> list:
    """甲[P0]：用 OpenD 实时持仓覆盖【富途】那部分股数+成本；其余账户沿用并标"需董事长确认"。"""
    p = ACCOUNTS_DIR / f"futu_positions_{date}.json"
    if not p.exists():
        return base_holdings
    try:
        fp = _read_json(p)
    except Exception:
        return base_holdings
    if fp.get("error"):
        return base_holdings
    live = {str(x["symbol"]): x for x in (fp.get("futu_positions") or [])}
    out, seen = [], set()
    for h in base_holdings:
        sym = str(h.get("symbol"))
        accs = list(h.get("accounts") or [])
        new_accs, changed = [], False
        for a in accs:
            an = str(a.get("account"))
            if an in FUTU_ALIASES:
                lv = live.get(sym)
                if lv is None:      # 富途已清空这只 → 该账户份额归0(真事实·不保留旧数)
                    changed = True
                    continue
                a2 = dict(a)
                a2["quantity"] = lv["quantity"]
                a2["cost_price"] = lv.get("cost_price")
                a2["cost_source"] = lv.get("cost_source")
                a2["cost_grade"] = lv.get("cost_grade")
                a2["qty_source"] = "OpenD 实时持仓(当日·A级)"
                new_accs.append(a2)
                changed = True
                seen.add(sym)
            else:
                a2 = dict(a)
                a2["qty_source"] = f"{an} 不接 OpenD → 沿用 2026-07-02 快照·需董事长手工确认"
                a2["needs_owner_confirm"] = True
                new_accs.append(a2)
        if not new_accs or sum(float(a.get("quantity") or 0) for a in new_accs) <= 0:
            continue                # 四个账户都没有它了(或都归0) → 整只出局
        row = dict(h)
        row["accounts"] = new_accs
        tq = sum(float(a.get("quantity") or 0) for a in new_accs)
        row["total_quantity"] = tq
        row["quantity_status"] = ("confirmed·富途实时+其它账户待确认"
                                  if any(str(a.get("account")) in FUTU_ALIASES for a in new_accs) and
                                  any(a.get("needs_owner_confirm") for a in new_accs)
                                  else ("confirmed·富途实时" if changed else "沿用快照·需董事长手工确认"))
        out.append(row)
    # 富途新买、但系统里还没有的标的 → 如实加进来(不许漏)
    for sym, lv in live.items():
        if sym in seen:
            continue
        out.append({"symbol": sym, "name": lv.get("name") or sym,
                    "total_quantity": lv["quantity"],
                    "quantity_status": "confirmed·富途实时(新持仓·系统此前没有这只)",
                    "accounts": [{"account": "富途", "quantity": lv["quantity"],
                                  "cost_price": lv.get("cost_price"), "cost_source": lv.get("cost_source"),
                                  "cost_grade": lv.get("cost_grade"),
                                  "qty_source": "OpenD 实时持仓(当日·A级)"}],
                    "currency_hint": ("JPY" if sym.startswith("JP.") else "USD"),
                    "_new_from_futu": True})
    return out


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
    # ══ 甲[P0·董事局工单2026-07-17]：富途那部分的股数改用 OpenD 当前实时持仓，不再沿用旧快照 ══
    #   根因：本函数原来只"沿用上一份 confirmed 股数 + 今日刷价"，股数从来没更新过 →
    #   董事长在富途的加减仓系统看不见 → 集中度/闲钱/加谁减谁全可能算错。
    #   SBI/IBKR/bitFlyer 不在 OpenD 里 → 保持沿用并标 needs_owner_confirm，不冒充实时。
    base_holdings = _apply_futu_live(base_holdings, date)

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
