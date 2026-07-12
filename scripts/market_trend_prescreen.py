#!/usr/bin/env python3
"""
market_trend_prescreen.py
TASK-2026-07-02-018

Read-only whole-market trend prescreen via Futu OpenD get_stock_filter.
- Only quote-side get_stock_filter is called.
- No trade context, no order, no publish.
- Unsupported or permission-limited markets are recorded honestly.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(r"G:\我的云端硬盘\AI_Investment_System")
CAPABILITY_PATH = ROOT / "data" / "market" / "market_scan_capability_20260702.json"
OPPORTUNITY_DIR = ROOT / "data" / "opportunities"
HOST = "127.0.0.1"
PORT = 11111
JST = timezone(timedelta(hours=9))
QUERY_TIMEOUT_SEC = 45


MARKET_CONFIGS = {
    "US": {
        "label": "美股",
        "futu_markets": ["US"],
        "price_min": 5,
        "avg_turnover_20d_min": 20_000_000,
        "change_20d_min": 2,
        "change_20d_max": 30,
    },
    "HK": {
        "label": "港股",
        "futu_markets": ["HK"],
        "price_min": 1,
        "avg_turnover_20d_min": 20_000_000,
        "change_20d_min": 2,
        "change_20d_max": 35,
    },
    "A": {
        "label": "A股",
        "futu_markets": ["SH", "SZ"],
        "price_min": 3,
        "avg_turnover_20d_min": 50_000_000,
        "change_20d_min": 2,
        "change_20d_max": 35,
    },
    "JP": {
        "label": "日股",
        "futu_markets": ["JP"],
        "price_min": 500,
        "avg_turnover_20d_min": 2_000_000_000,
        "change_20d_min": 2,
        "change_20d_max": 30,
    },
}


def now_jst() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return str(value)


def write_json_utf8(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8", newline="\n")
    reread = path.read_text(encoding="utf-8")
    if reread != text:
        raise RuntimeError(f"UTF-8 reread mismatch: {path}")
    if chr(0xFFFD) in reread or chr(63) in reread:
        raise RuntimeError(f"Garble marker found: {path}")


def classify_error(message: str) -> str:
    lower = message.lower()
    if any(token in lower for token in ["not support", "unsupported"]) or "不支持" in message:
        return "不支持"
    if any(token in lower for token in ["permission", "quota", "subscribe", "subscription", "权限", "额度", "订阅"]):
        return "受限"
    return "受限"


def build_filters(cfg: dict[str, Any]):
    from futu import (
        AccumulateFilter,
        CustomIndicatorFilter,
        KLType,
        RelativePosition,
        SimpleFilter,
        SortDir,
        StockField,
    )

    filters = []

    price = SimpleFilter()
    price.stock_field = StockField.CUR_PRICE
    price.filter_min = cfg["price_min"]
    price.is_no_filter = False
    filters.append(price)

    turnover = AccumulateFilter()
    turnover.stock_field = StockField.TURNOVER
    turnover.days = 20
    turnover.filter_min = cfg["avg_turnover_20d_min"] * 20
    turnover.is_no_filter = False
    filters.append(turnover)

    change = AccumulateFilter()
    change.stock_field = StockField.CHANGE_RATE
    change.days = 20
    change.filter_min = cfg["change_20d_min"]
    change.filter_max = cfg["change_20d_max"]
    change.sort = SortDir.DESCEND
    change.is_no_filter = False
    filters.append(change)

    for ma_days in (20, 50, 200):
        ma_filter = CustomIndicatorFilter()
        ma_filter.stock_field1 = StockField.PRICE
        ma_filter.stock_field2 = StockField.MA
        ma_filter.stock_field2_para = [ma_days]
        ma_filter.relative_position = RelativePosition.MORE
        ma_filter.ktype = KLType.K_DAY
        ma_filter.is_no_filter = False
        filters.append(ma_filter)

    return filters


def get_attr(obj: Any, attr: Any) -> Any:
    if isinstance(obj, dict):
        return obj.get(attr)
    if hasattr(obj, attr) if isinstance(attr, str) else False:
        return getattr(obj, attr)
    if hasattr(obj, "__dict__"):
        return obj.__dict__.get(attr)
    return None


def record_from_item(item: Any, market_key: str, sub_market: str, timestamp: str) -> dict[str, Any]:
    raw = dict(getattr(item, "__dict__", {}))
    stock_code = json_safe(raw.get("stock_code"))
    stock_name = json_safe(raw.get("stock_name"))
    cur_price = json_safe(raw.get("cur_price"))
    change_20d = json_safe(raw.get(("change_rate", 20)))
    turnover_20d = json_safe(raw.get(("turnover", 20)))
    ma20 = json_safe(raw.get(("ma", "20", "k_day")) or raw.get(("ma20", "k_day")))
    ma50 = json_safe(raw.get(("ma", "50", "k_day")))
    ma200 = json_safe(raw.get(("ma", "200", "k_day")))

    def gt(a: Any, b: Any) -> bool | None:
        try:
            return float(a) > float(b)
        except Exception:
            return None

    avg_turnover = None
    try:
        avg_turnover = float(turnover_20d) / 20 if turnover_20d is not None else None
    except Exception:
        avg_turnover = None

    ma20_ok = gt(cur_price, ma20)
    ma50_ok = gt(cur_price, ma50)
    ma200_ok = gt(cur_price, ma200)
    return {
        "code": stock_code,
        "name": stock_name,
        "market": market_key,
        "futu_market": sub_market,
        "latest_price": cur_price,
        "change_20d_pct": change_20d,
        "turnover_20d": turnover_20d,
        "avg_turnover_20d": avg_turnover,
        "above_ma20": ma20_ok,
        "above_ma50": ma50_ok,
        "above_ma200": ma200_ok,
        "ma20": ma20,
        "ma50": ma50,
        "ma200": ma200,
        "hit_reason": "价格过市场下限；近20日成交额过流动性门槛；价格站上MA20/MA50/MA200；近20日涨跌幅处于合理强势区间",
        "timestamp": timestamp,
    }


def capability_probe(market_key: str, sub_market: str, cfg: dict[str, Any], limit: int) -> dict[str, Any]:
    from futu import Market, OpenQuoteContext, RET_OK

    ctx = OpenQuoteContext(host=HOST, port=PORT)
    try:
        market_value = getattr(Market, sub_market)
        filters = build_filters(cfg)
        ret, data = ctx.get_stock_filter(market_value, filter_list=filters, begin=0, num=limit)
        if ret != RET_OK:
            message = str(data)
            return {
                "market": market_key,
                "futu_market": sub_market,
                "status": classify_error(message),
                "supported": False,
                "limited": classify_error(message) == "受限",
                "reason": message,
                "returned_count": 0,
                "fields": [],
                "records": [],
            }

        page_done = None
        all_count = None
        if isinstance(data, tuple) and len(data) >= 3:
            page_done = json_safe(data[0])
            all_count = json_safe(data[1])
            items = data[2]
        elif isinstance(data, tuple) and len(data) >= 2:
            all_count = json_safe(data[0])
            items = data[1]
        else:
            items = data
        items = list(items or [])
        timestamp = now_jst()
        records = [record_from_item(item, market_key, sub_market, timestamp) for item in items]
        field_names = sorted({str(k) for item in items for k in getattr(item, "__dict__", {}).keys()})
        return {
            "market": market_key,
            "futu_market": sub_market,
            "status": "支持",
            "supported": True,
            "limited": False,
            "reason": "",
            "returned_count": len(records),
            "all_count": all_count,
            "page_done": page_done,
            "fields": field_names,
            "records": records,
        }
    except Exception as exc:
        return {
            "market": market_key,
            "futu_market": sub_market,
            "status": classify_error(str(exc)),
            "supported": False,
            "limited": classify_error(str(exc)) == "受限",
            "reason": str(exc),
            "returned_count": 0,
            "fields": [],
            "records": [],
        }
    finally:
        try:
            ctx.close()
        except Exception:
            pass


def worker(market_key: str, sub_market: str, cfg: dict[str, Any], limit: int, queue: mp.Queue) -> None:
    try:
        queue.put(capability_probe(market_key, sub_market, cfg, limit))
    except Exception as exc:
        queue.put({
            "market": market_key,
            "futu_market": sub_market,
            "status": "受限",
            "supported": False,
            "limited": True,
            "reason": str(exc),
            "returned_count": 0,
            "fields": [],
            "records": [],
        })


def run_probe_with_timeout(market_key: str, sub_market: str, cfg: dict[str, Any], limit: int) -> dict[str, Any]:
    queue: mp.Queue = mp.Queue()
    proc = mp.Process(target=worker, args=(market_key, sub_market, cfg, limit, queue))
    proc.start()
    proc.join(QUERY_TIMEOUT_SEC)
    if proc.is_alive():
        proc.terminate()
        proc.join(2)
        return {
            "market": market_key,
            "futu_market": sub_market,
            "status": "受限",
            "supported": False,
            "limited": True,
            "reason": f"get_stock_filter timeout after {QUERY_TIMEOUT_SEC}s",
            "returned_count": 0,
            "fields": [],
            "records": [],
        }
    if queue.empty():
        return {
            "market": market_key,
            "futu_market": sub_market,
            "status": "受限",
            "supported": False,
            "limited": True,
            "reason": "worker returned no result",
            "returned_count": 0,
            "fields": [],
            "records": [],
        }
    return queue.get()


def build_outputs(limit_per_market: int) -> tuple[dict[str, Any], dict[str, Any]]:
    generated_at = now_jst()
    capability: dict[str, Any] = {
        "task_id": "TASK-2026-07-02-018",
        "mode": "READ_ONLY_QUOTE_ONLY_NO_ORDER_NO_PUBLISH",
        "generated_at": generated_at,
        "host": HOST,
        "port": PORT,
        "method": "OpenQuoteContext.get_stock_filter",
        "markets": {},
        "safety": {
            "trade_context_created": False,
            "place_order_called": False,
            "change_order_called": False,
            "cancel_order_called": False,
            "published": False,
        },
    }
    opportunities: dict[str, Any] = {
        "task_id": "TASK-2026-07-02-018",
        "mode": "READ_ONLY_PRESCREEN_ONLY",
        "generated_at": generated_at,
        "criteria": {
            "liquidity": "价格高于市场下限，近20日累计成交额高于日均门槛乘以20",
            "trend": "价格站上MA20、MA50、MA200，且近20日涨跌幅处于合理强势区间",
            "limit": f"每市场最多 Top {limit_per_market}",
        },
        "markets": {},
        "all_candidates": [],
    }

    for market_key, cfg in MARKET_CONFIGS.items():
        sub_results = [
            run_probe_with_timeout(market_key, sub_market, cfg, limit_per_market)
            for sub_market in cfg["futu_markets"]
        ]
        supported_results = [r for r in sub_results if r.get("supported")]
        if supported_results:
            status = "支持"
            reason = ""
        else:
            status_values = {r.get("status") for r in sub_results}
            status = "不支持" if status_values == {"不支持"} else "受限"
            reason = "；".join(f"{r.get('futu_market')}:{r.get('reason')}" for r in sub_results)

        fields = sorted({field for r in sub_results for field in r.get("fields", [])})
        records = [rec for r in supported_results for rec in r.get("records", [])]
        records.sort(key=lambda x: (x.get("change_20d_pct") is None, -(float(x.get("change_20d_pct") or 0))))
        records = records[:limit_per_market]

        capability["markets"][market_key] = {
            "label": cfg["label"],
            "status": status,
            "supported": bool(supported_results),
            "reason": reason,
            "submarkets": sub_results,
            "fields": fields,
            "limits_or_permissions": reason,
            "thresholds": {
                "price_min": cfg["price_min"],
                "avg_turnover_20d_min": cfg["avg_turnover_20d_min"],
                "change_20d_min": cfg["change_20d_min"],
                "change_20d_max": cfg["change_20d_max"],
            },
        }
        opportunities["markets"][market_key] = {
            "label": cfg["label"],
            "status": status,
            "reason": reason,
            "candidate_count": len(records),
            "candidates": records,
        }
        opportunities["all_candidates"].extend(records)

    return capability, opportunities


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Read-only Futu get_stock_filter market trend prescreen.")
    parser.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d"), help="output date suffix YYYYMMDD")
    parser.add_argument("--limit", type=int, default=30, help="max candidates per market")
    args = parser.parse_args()

    capability, opportunities = build_outputs(args.limit)
    output_path = OPPORTUNITY_DIR / f"trend_candidates_{args.date}.json"
    write_json_utf8(CAPABILITY_PATH, capability)
    write_json_utf8(output_path, opportunities)

    print(f"CAPABILITY_PATH={CAPABILITY_PATH}")
    print(f"OUTPUT_PATH={output_path}")
    for key, info in opportunities["markets"].items():
        print(f"{key} {info['status']} candidates={info['candidate_count']} reason={info.get('reason') or ''}")
        for item in info["candidates"][:5]:
            print(
                f"  {item.get('code')} {item.get('name')} "
                f"chg20={item.get('change_20d_pct')} "
                f"turnover20={item.get('turnover_20d')} "
                f"MA20/50/200={item.get('above_ma20')}/{item.get('above_ma50')}/{item.get('above_ma200')}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
