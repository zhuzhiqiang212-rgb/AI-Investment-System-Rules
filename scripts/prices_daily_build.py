#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P0-1 20日价格序列 · data/prices/daily_{code}.json 生成器

派工单_数据接入并行开工_20260720 · P0-1(最高优先·直接卡加仓闸):
  加仓闸「便宜 且(有推动事件 或 近20交易日不再创新低)」——括号后半条要价格序列才能跑。

本脚本(只读·连 OpenD request_history_kline K_DAY QFQ,不下单/不动交易):
  为每只标的产 data/prices/daily_{code}.json:
    - series: 近60交易日 [date, open, high, low, close, volume]
    - 派生①最低价+发生日期 ②最近一次创新低日期 ③近20交易日是否不再创新低(是/否)
      ④MA20/50/200 ⑤现价相对各均线% ⑥现价在近20日区间中的位置
  取不到→该只 status=FAIL + reason,价/派生全 null。严禁估算/相邻日/旧值顶充。
  加密(CC.*)不支持 K_DAY → 如实标 unsupported,不编。

窗口口径(可审):
  - series 存最近 60 根;
  - ①②③的"创新低"以拉到的全窗(≤250根)running-min 为基准,new_low=当日 low ≤ 此前所有 low 的最小值;
    "最近创新低日期"=最后一次刷新窗内最低的交易日;该日距今 ≥20 交易日 → ③=是(近20日不再创新低)。
  - ⑥ low20/high20 取最近 20 根的 low/high。

用法: python scripts/prices_daily_build.py [--date YYYYMMDD]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRICES_DIR = ROOT / "data" / "prices"
JST = timezone(timedelta(hours=9))

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from realtime_price import (  # noqa: E402
    classify_failure,
    connect_quote_context,
    get_realtime_price,
    records_from_frame,
)

SERIES_LEN = 60      # 存最近60交易日
KLINE_PULL = 250     # 拉250根:够算MA200+稳健判创新低
NEWLOW_RECENT = 20   # 近20交易日不再创新低


def now_jst() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")
    reread = path.read_text(encoding="utf-8")
    if reread != text:
        raise RuntimeError(f"UTF-8 write/read mismatch: {path}")
    if "�" in reread:
        raise RuntimeError(f"U+FFFD garble after write: {path}")


def to_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def universe(date: str) -> list[dict[str, Any]]:
    """从 holdings_review_{date} 取标的宇宙;缺则回退最近一份。"""
    hp = ROOT / "data" / "holdings" / f"holdings_review_{date}.json"
    if not hp.exists():
        cands = sorted((ROOT / "data" / "holdings").glob("holdings_review_*.json"))
        if not cands:
            raise FileNotFoundError("找不到 holdings_review_*.json 取标的宇宙")
        hp = cands[-1]
    doc = read_json(hp)
    out, seen = [], set()
    for r in doc.get("reviews", []):
        s = r.get("symbol")
        if s and s not in seen:
            seen.add(s)
            out.append({"symbol": s, "name": r.get("name")})
    return out, hp.name


def pull_klines(ctx: Any, symbol: str) -> tuple[list[dict[str, Any]], str | None]:
    """拉 K_DAY QFQ 日线,返回按时间升序的 [ {date,open,high,low,close,volume} ]。"""
    from futu import AuType, KLType, RET_OK

    try:
        ret, data, page_key = ctx.request_history_kline(
            symbol, ktype=KLType.K_DAY, autype=AuType.QFQ, max_count=1000,
        )
    except Exception as exc:
        return [], str(exc)
    if ret != RET_OK:
        return [], str(data)
    rows = records_from_frame(data)
    while page_key is not None and len(rows) < KLINE_PULL:
        try:
            ret, data, page_key = ctx.request_history_kline(
                symbol, ktype=KLType.K_DAY, autype=AuType.QFQ, max_count=1000, page_req_key=page_key,
            )
        except Exception as exc:
            return [], str(exc)
        if ret != RET_OK:
            return [], str(data)
        rows.extend(records_from_frame(data))

    bars = []
    for r in rows:
        tk = r.get("time_key") or r.get("data_date") or ""
        date = str(tk).split(" ")[0].split("T")[0]
        o, h, l, c = to_float(r.get("open")), to_float(r.get("high")), to_float(r.get("low")), to_float(r.get("close"))
        v = to_float(r.get("volume"))
        if c is None:
            continue
        bars.append({"date": date, "open": o, "high": h, "low": l, "close": c, "volume": v})
    return bars, None


def ma(closes: list[float], n: int) -> float | None:
    return round(sum(closes[-n:]) / n, 6) if len(closes) >= n else None


def pct(cur: float | None, base: float | None) -> float | None:
    if cur is None or base is None or base == 0:
        return None
    return round((cur - base) / base * 100, 3)


def derive(bars: list[dict[str, Any]], price: float | None) -> dict[str, Any]:
    """派生①-⑥。bars 按时间升序、含全窗(≤250)。价格优先用实时 price,否则用最后收盘。"""
    closes = [b["close"] for b in bars]
    lows = [b["low"] if b["low"] is not None else b["close"] for b in bars]
    cur = price if price is not None else (closes[-1] if closes else None)

    # ①最低价及发生日期(全存窗=最近60根内的最低;这里以 series 窗判)
    series = bars[-SERIES_LEN:]
    s_lows = [(b["low"] if b["low"] is not None else b["close"], b["date"]) for b in series]
    low_min, low_min_date = (None, None)
    if s_lows:
        low_min, low_min_date = min(s_lows, key=lambda x: x[0])
        low_min = round(low_min, 4)

    # ②最近一次创新低日期(全窗 running-min;new low=刷新此前最低)
    last_new_low_date = None
    new_low_idx = None
    run_min = None
    for i, b in enumerate(bars):
        lv = b["low"] if b["low"] is not None else b["close"]
        if run_min is None or lv < run_min - 1e-12:
            run_min = lv
            last_new_low_date = b["date"]
            new_low_idx = i
    # ③近20交易日是否不再创新低:最近创新低距今 ≥20 根 → 是
    bars_since_new_low = (len(bars) - 1 - new_low_idx) if new_low_idx is not None else None
    no_new_low_20 = (bars_since_new_low is not None and bars_since_new_low >= NEWLOW_RECENT)

    # ④均线
    ma20, ma50, ma200 = ma(closes, 20), ma(closes, 50), ma(closes, 200)

    # ⑥现价在近20日区间位置
    last20 = bars[-20:]
    low20 = min((b["low"] if b["low"] is not None else b["close"]) for b in last20) if last20 else None
    high20 = max((b["high"] if b["high"] is not None else b["close"]) for b in last20) if last20 else None
    pos20 = None
    if cur is not None and low20 is not None and high20 is not None and high20 > low20:
        pos20 = round((cur - low20) / (high20 - low20), 4)

    return {
        "price_used_for_derive": cur,
        "low_min_60d": low_min,
        "low_min_60d_date": low_min_date,
        "last_new_low_date": last_new_low_date,
        "bars_since_last_new_low": bars_since_new_low,
        "no_new_low_recent20": no_new_low_20,          # ③ True/False
        "ma20": ma20, "ma50": ma50, "ma200": ma200,
        "price_vs_ma20_pct": pct(cur, ma20),
        "price_vs_ma50_pct": pct(cur, ma50),
        "price_vs_ma200_pct": pct(cur, ma200),
        "low20": round(low20, 4) if low20 is not None else None,
        "high20": round(high20, 4) if high20 is not None else None,
        "pos_in_20d_range": pos20,                     # ⑥ 0=贴20日低 1=贴20日高
    }


def build_symbol(ctx: Any, sym: str, name: str | None, date: str) -> dict[str, Any]:
    base = {"symbol": sym, "name": name, "date": date, "generated_at": now_jst(),
            "source": "OpenD request_history_kline K_DAY QFQ + realtime_price",
            "safety": {"read_only": True, "place_order_called": False, "history_kline_called": True}}

    if sym.startswith("CC."):
        base.update({"status": "UNSUPPORTED", "reason": "加密代码 OpenD 不支持 K_DAY 均线/序列;不编估算",
                     "series": None})
        return base, "UNSUPPORTED"

    quote = get_realtime_price(sym, ctx=ctx, max_retries=1, wait_seconds=0)
    price = quote.get("price") if quote.get("status") == "OK" else None

    bars, kreason = pull_klines(ctx, sym)
    if kreason or not bars:
        base.update({"status": "FAIL", "reason": kreason or "K线为空",
                     "realtime_price": price, "price_status": quote.get("status"),
                     "series": None})
        return base, "FAIL"

    series = bars[-SERIES_LEN:]
    der = derive(bars, price)
    warn = []
    if der["ma200"] is None:
        warn.append(f"MA200需≥200根,现{len(bars)}根")
    if price is None:
        warn.append(f"实时价FAIL:{quote.get('reason')}(派生用最后收盘)")

    base.update({
        "status": "OK",
        "realtime_price": price,
        "price_status": quote.get("status"),
        "price_data_date": quote.get("data_date"),
        "kline_count_pulled": len(bars),
        "series_len": len(series),
        "series": series,
        "derived": der,
        "warnings": warn or None,
    })
    return base, "OK"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="P0-1 价格序列生成器")
    ap.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d"))
    args = ap.parse_args()

    syms, uni_src = universe(args.date)
    # 快速端口预检:OpenD(11111)未开时,futu 连接会长时间阻塞而非快速失败 → 先探端口,闭则直接如实标未接通
    import socket
    _s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _s.settimeout(3)
    try:
        _s.connect(("127.0.0.1", 11111))
        _port_open = True
    except Exception:
        _port_open = False
    finally:
        _s.close()
    if not _port_open:
        ctx, attempts = None, [{"success": False, "reason": "port 11111 connection refused (OpenD 未运行)", "time": now_jst()}]
    else:
        ctx, attempts = connect_quote_context(max_retries=2, wait_seconds=2)

    report = {"task": "P0-1", "date": args.date, "generated_at": now_jst(),
              "universe_source": uni_src, "connection_ok": ctx is not None,
              "connection_attempts": attempts, "per_symbol": []}

    if ctx is None:
        reason = "OpenD 未连(端口11111 connection refused 或超时)·请开 OpenD 客户端后重跑"
        for it in syms:
            doc = {"symbol": it["symbol"], "name": it["name"], "date": args.date,
                   "generated_at": now_jst(), "status": "FAIL_NO_OPEND", "reason": reason,
                   "series": None,
                   "source": "OpenD request_history_kline K_DAY QFQ + realtime_price",
                   "safety": {"read_only": True, "place_order_called": False}}
            write_json(PRICES_DIR / f"daily_{it['symbol']}.json", doc)
            report["per_symbol"].append({"symbol": it["symbol"], "name": it["name"],
                                         "status": "未接通", "reason": reason})
        write_json(PRICES_DIR / f"_report_{args.date}.json", report)
        print(json.dumps({"connection_ok": False, "reason": reason,
                          "written": len(syms), "dir": str(PRICES_DIR)}, ensure_ascii=False, indent=2))
        return 2

    counts = {"OK": 0, "FAIL": 0, "UNSUPPORTED": 0}
    try:
        for it in syms:
            try:
                doc, st = build_symbol(ctx, it["symbol"], it["name"], args.date)
            except Exception as exc:
                doc = {"symbol": it["symbol"], "name": it["name"], "date": args.date,
                       "generated_at": now_jst(), "status": "FAIL",
                       "reason": f"{classify_failure(str(exc))}: {exc}", "series": None}
                st = "FAIL"
            write_json(PRICES_DIR / f"daily_{it['symbol']}.json", doc)
            counts[st if st in counts else "FAIL"] = counts.get(st, 0) + 1
            d = doc.get("derived") or {}
            report["per_symbol"].append({
                "symbol": it["symbol"], "name": it["name"], "status": st,
                "reason": doc.get("reason"),
                "no_new_low_recent20": d.get("no_new_low_recent20"),
                "last_new_low_date": d.get("last_new_low_date"),
                "ma200_ok": d.get("ma200") is not None if st == "OK" else None,
            })
    finally:
        try:
            ctx.close()
        except Exception:
            pass

    report["summary"] = counts
    write_json(PRICES_DIR / f"_report_{args.date}.json", report)
    print(json.dumps({"connection_ok": True, "summary": counts,
                      "dir": str(PRICES_DIR)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
