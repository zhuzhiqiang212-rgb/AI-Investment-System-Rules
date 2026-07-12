#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dual-channel opportunity pricing.

TASK-2026-07-02-059 update:
- current price uses scripts/realtime_price.py::get_realtime_price
- holdings source is holdings_true_YYYYMMDD.json
- no stale price fallback on quote FAIL
- K-line is still read-only and used only for MA, range, and volume context
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from realtime_price import connect_quote_context, get_realtime_price


JST = timezone(timedelta(hours=9))
QMARK = chr(63)
REPL = chr(0xFFFD)
BATCH_SIZE = 10
BATCH_SLEEP_SECONDS = 31


def now_jst() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def sanitize_tree(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace(QMARK, "[question_mark]").replace(REPL, "[replacement_char]")
    if isinstance(value, list):
        return [sanitize_tree(item) for item in value]
    if isinstance(value, dict):
        return {str(key): sanitize_tree(item) for key, item in value.items()}
    return value


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_utf8(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    clean_payload = sanitize_tree(payload)
    text = json.dumps(clean_payload, ensure_ascii=False, indent=2) + "\n"
    if QMARK in text or REPL in text:
        raise RuntimeError(f"garble marker before write: {path}")
    path.write_text(text, encoding="utf-8", newline="\n")
    reread = path.read_text(encoding="utf-8")
    if reread != text:
        raise RuntimeError(f"roundtrip mismatch: {path}")
    if QMARK in reread or REPL in reread:
        raise RuntimeError(f"garble marker after write: {path}")


def normalize_code(raw: Any) -> str:
    return str(raw or "").strip().upper()


def code_tail(code: Any) -> str:
    return normalize_code(code).split(".")[-1]


def parse_money(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value)
    match = re.search(r"[-+][0-9][0-9,]*\.[0-9]+|[-+][0-9][0-9,]*|[0-9][0-9,]*\.[0-9]+|[0-9][0-9,]*", text)
    if not match:
        return None
    return float(match.group(0).replace(",", ""))


def realtime_batch(codes: list[str]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    unique_codes: list[str] = []
    seen: set[str] = set()
    for code in codes:
        if not code or code in seen:
            continue
        seen.add(code)
        unique_codes.append(code)

    ctx, attempts = connect_quote_context(max_retries=3, wait_seconds=3)
    out: dict[str, dict[str, Any]] = {}
    if ctx is None:
        for code in unique_codes:
            out[code] = {"code": code, "status": "FAIL", "price": None, "reason": "OpenD quote connection failed"}
        return out, attempts

    try:
        for index, code in enumerate(unique_codes):
            if index and index % BATCH_SIZE == 0:
                time.sleep(BATCH_SLEEP_SECONDS)
            out[code] = get_realtime_price(code, ctx=ctx)
    finally:
        try:
            ctx.close()
        except Exception:
            pass
    return out, attempts


def calc_market_value(price: Any, quantity: Any) -> float | None:
    if price is None or quantity is None:
        return None
    return round(float(price) * float(quantity), 4)


OPPORTUNITY_DIR = ROOT / "data" / "opportunities"
ACCOUNTS_DIR = ROOT / "data" / "accounts"
HOLDINGS_REVIEW_DIR = ROOT / "data" / "holdings"
HOST = "127.0.0.1"
PORT = 11111
A_KEY = "A类趋势加估值合理"
PENDING = "待补"
NOT_APPLICABLE = "非持仓不适用"
DAILY = "每日"
TECH_DIM = "技术维"
COST_DIM = "成本维"
FUNDS_DIM = "资金维"
VALUATION_DIM = "估值维"
CATALYST_DIM = "基本面催化维"


def load_valuation_gate(date_text: str) -> tuple[dict[str, Any], Path]:
    path = OPPORTUNITY_DIR / f"opportunity_gated_{date_text}.json"
    if not path.exists():
        raise FileNotFoundError("need opportunity valuation gate first: " + str(path))
    return read_json(path), path


def load_holdings_true(date_text: str) -> tuple[list[dict[str, Any]], Path]:
    path = ACCOUNTS_DIR / f"holdings_true_{date_text}.json"
    data = read_json(path)
    return data.get("holdings", []), path


def load_holding_nodes(date_text: str) -> dict[str, list[str]]:
    path = HOLDINGS_REVIEW_DIR / f"holdings_review_{date_text}.json"
    if not path.exists():
        return {}
    data = read_json(path, {})
    out: dict[str, list[str]] = {}
    for row in data.get("reviews", []):
        code = str(row.get("symbol") or row.get("code") or row.get("ticker") or "")
        nodes = row.get("matched_node_classes") or []
        out[normalize_code(code)] = list(nodes)
        out[code_tail(code)] = list(nodes)
    return out


def normalized_candidate(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": row.get("code"),
        "ticker": row.get("code"),
        "name": row.get("name") or row.get("code"),
        "node_class": row.get("node_class"),
    }


def safe_number(value: Any) -> float | None:
    try:
        if value is None or value == "" or value == "N/A":
            return None
        return float(value)
    except Exception:
        return None


def records_from_frame(obj: Any) -> list[dict[str, Any]]:
    if hasattr(obj, "to_dict"):
        return [{str(k): v.item() if hasattr(v, "item") else v for k, v in row.items()} for row in obj.to_dict(orient="records")]
    return []


def pending_metrics(code: str | None, reason: str) -> dict[str, Any]:
    return {"status": PENDING, "reason": reason, "code": code, "source": "Futu OpenD request_history_kline", "refresh": DAILY}


def fetch_kline_metrics(ctx: Any, code: str | None, quote_error: str | None = None) -> dict[str, Any]:
    if quote_error:
        return pending_metrics(code, quote_error)
    if not code:
        return pending_metrics(code, "no Futu code")
    try:
        from futu import KLType, RET_OK
        ret, data, _page_req_key = ctx.request_history_kline(code, ktype=KLType.K_DAY, max_count=260)
    except Exception as exc:
        return pending_metrics(code, str(exc))
    if ret != RET_OK:
        return pending_metrics(code, str(data))
    rows = records_from_frame(data)
    if not rows:
        return pending_metrics(code, "empty K-line")
    closes = [safe_number(row.get("close")) for row in rows]
    highs = [safe_number(row.get("high")) for row in rows]
    lows = [safe_number(row.get("low")) for row in rows]
    volumes = [safe_number(row.get("volume")) for row in rows]
    closes = [v for v in closes if v is not None]
    highs = [v for v in highs if v is not None]
    lows = [v for v in lows if v is not None]
    volumes = [v for v in volumes if v is not None]

    def avg(values: list[float], n: int) -> float | None:
        return sum(values[-n:]) / n if len(values) >= n else None

    avg_vol20 = avg(volumes, 20)
    latest_volume = volumes[-1] if volumes else None
    ratio = latest_volume / avg_vol20 if avg_vol20 not in [None, 0] and latest_volume is not None else None
    return {
        "status": "OK",
        "code": code,
        "kline_latest_close": closes[-1] if closes else None,
        "ma20": avg(closes, 20),
        "ma50": avg(closes, 50),
        "ma200": avg(closes, 200),
        "high60": max(highs[-60:]) if len(highs) >= 60 else None,
        "low60": min(lows[-60:]) if len(lows) >= 60 else None,
        "latest_volume": latest_volume,
        "avg_volume_20d": avg_vol20,
        "volume_ratio_to_20d": ratio,
        "source": "Futu OpenD request_history_kline",
        "refresh": DAILY,
    }


def open_quote_context() -> tuple[Any, str | None]:
    try:
        from futu import OpenQuoteContext
        return OpenQuoteContext(host=HOST, port=PORT), None
    except Exception as exc:
        return None, str(exc)


def cost_dimension(holding: dict[str, Any] | None, realtime_quote: dict[str, Any] | None) -> dict[str, Any]:
    if not holding:
        return {"status": NOT_APPLICABLE, "source": "holdings_true_YYYYMMDD.json", "refresh": DAILY, "value": None}
    quantity = holding.get("total_quantity")
    price = (realtime_quote or {}).get("price")
    market_value = calc_market_value(price, quantity)
    possible_cost = holding.get("cost_per_share") or holding.get("average_cost") or holding.get("cost_basis")
    if possible_cost is None:
        return {
            "status": "待补成本",
            "source": "holdings_true_YYYYMMDD.json",
            "refresh": DAILY,
            "value": {
                "total_quantity": quantity,
                "realtime_price": price,
                "market_value": market_value,
                "cost_per_share": None,
                "unrealized_pnl_pct": None,
            },
            "coverage": holding.get("quantity_status"),
        }
    cost = safe_number(possible_cost)
    pnl = None
    if cost not in [None, 0] and price is not None:
        pnl = round((float(price) / float(cost) - 1) * 100, 4)
    return {
        "status": "OK",
        "source": "holdings_true_YYYYMMDD.json",
        "refresh": DAILY,
        "value": {
            "total_quantity": quantity,
            "realtime_price": price,
            "cost_per_share": cost,
            "unrealized_pnl_pct": pnl,
            "market_value": market_value,
        },
    }


def dynamic_valuation_placeholder() -> dict[str, Any]:
    return {"source": "深度估值模型便宜/合理/贵价格带，随财报与价格每日重算", "refresh": "每日+财报后", "status": "动态占位，待模型实例或理解岗补齐", "value": None}


def catalyst_placeholder() -> dict[str, Any]:
    return {"source": "财报日历/事件/竞对比较/持仓横比", "refresh": "事件驱动", "status": "数据源待接", "value": None}


def build_reference(technical: dict[str, Any], cost: dict[str, Any], funds: dict[str, Any]) -> dict[str, Any]:
    if technical.get("status") != "OK":
        return {"status": PENDING, "text": "技术维数据不足，不能给买卖参考"}
    val = technical.get("value") or {}
    return {
        "status": "可给三维参考",
        "current_price": val.get("current_price"),
        "support_zone": {"ma200": val.get("ma200"), "low60": val.get("low60")},
        "pressure_zone": {"high60": val.get("high60"), "ma20": val.get("ma20")},
        "volume_context": {"avg_volume_20d": funds.get("avg_volume_20d"), "volume_ratio_to_20d": funds.get("volume_ratio_to_20d")},
        "cost_context": cost,
    }


def instrument_record(kind: str, item: dict[str, Any], metrics: dict[str, Any], holding: dict[str, Any] | None, quote: dict[str, Any]) -> dict[str, Any]:
    tech_status = "OK" if quote.get("status") == "OK" and metrics.get("status") == "OK" else "FAIL" if quote.get("status") != "OK" else metrics.get("status")
    technical = {
        "source": "realtime_price.py current price + Futu OpenD request_history_kline MA",
        "refresh": DAILY,
        "status": tech_status,
        "value": {
            "current_price": quote.get("price"),
            "used_field": quote.get("used_field"),
            "market_state": quote.get("market_state"),
            "data_date": quote.get("data_date"),
            "data_time": quote.get("data_time"),
            "kline_latest_close": metrics.get("kline_latest_close"),
            "ma20": metrics.get("ma20"),
            "ma50": metrics.get("ma50"),
            "ma200": metrics.get("ma200"),
            "high60": metrics.get("high60"),
            "low60": metrics.get("low60"),
        } if quote.get("status") == "OK" else None,
        "reason": quote.get("reason") or metrics.get("reason"),
    }
    funds = {
        "source": metrics.get("source", "Futu OpenD request_history_kline"),
        "refresh": DAILY,
        "status": metrics.get("status"),
        "avg_volume_20d": metrics.get("avg_volume_20d"),
        "latest_volume": metrics.get("latest_volume"),
        "volume_ratio_to_20d": metrics.get("volume_ratio_to_20d"),
        "reason": metrics.get("reason"),
    }
    cost = cost_dimension(holding if kind == "持仓" else None, quote)
    return {
        "kind": kind,
        "code": item.get("code"),
        "ticker": item.get("ticker"),
        "name": item.get("name"),
        "node_class": item.get("node_class"),
        "realtime_quote": quote,
        "six_dimensions": {
            TECH_DIM: technical,
            COST_DIM: cost,
            FUNDS_DIM: funds,
            VALUATION_DIM: dynamic_valuation_placeholder(),
            CATALYST_DIM: catalyst_placeholder(),
        },
        "current_buy_sell_reference": build_reference(technical, cost, funds),
        "pending_dimension_note": "估值维与基本面催化维为动态接口占位，value=null，不伪造",
    }


def build_output(date_text: str) -> dict[str, Any]:
    gated, gated_path = load_valuation_gate(date_text)
    a_candidates = gated.get("groups", {}).get(A_KEY, [])
    holdings, holdings_path = load_holdings_true(date_text)
    holding_nodes = load_holding_nodes(date_text)
    holding_by_code = {normalize_code(row.get("symbol")): row for row in holdings}
    holding_by_tail = {code_tail(row.get("symbol")): row for row in holdings}

    items: list[tuple[str, dict[str, Any], dict[str, Any] | None]] = []
    for candidate in a_candidates:
        normalized = normalized_candidate(candidate)
        holding = holding_by_code.get(normalize_code(normalized.get("code"))) or holding_by_tail.get(code_tail(normalized.get("code")))
        items.append(("A类候选", normalized, holding))
    for holding in holdings:
        code = holding.get("symbol")
        items.append(("持仓", {
            "code": code,
            "ticker": code,
            "name": holding.get("name"),
            "node_class": holding_nodes.get(normalize_code(code)) or holding_nodes.get(code_tail(code)) or [],
        }, holding))

    codes = [str(item[1].get("code")) for item in items if item[1].get("code")]
    realtime_quotes, price_attempts = realtime_batch(codes)

    metrics_cache: dict[str, dict[str, Any]] = {}
    records = []
    ctx, quote_error = open_quote_context()
    try:
        for kind, item, holding in items:
            code = str(item.get("code") or "")
            if code not in metrics_cache:
                metrics_cache[code] = fetch_kline_metrics(ctx, code, quote_error)
                time.sleep(0.25)
            records.append(instrument_record(kind, item, metrics_cache[code], holding, realtime_quotes.get(code, {"code": code, "status": "FAIL", "price": None, "reason": "not quoted"})))
    finally:
        if ctx is not None:
            ctx.close()

    compare_rows = []
    for candidate in a_candidates:
        normalized = normalized_candidate(candidate)
        node = str(normalized.get("node_class") or "")
        for holding in holdings:
            holding_code = str(holding.get("symbol") or "")
            nodes = holding_nodes.get(normalize_code(holding_code)) or holding_nodes.get(code_tail(holding_code)) or []
            if node and node in nodes:
                cand_metrics = metrics_cache.get(str(normalized.get("code")), {})
                hold_metrics = metrics_cache.get(holding_code, {})
                cand_quote = realtime_quotes.get(str(normalized.get("code")), {})
                hold_quote = realtime_quotes.get(holding_code, {})
                compare_rows.append({
                    "现持仓标的": {"code": holding_code, "name": holding.get("name")},
                    "候选标的": {"code": normalized.get("code"), "name": normalized.get("name")},
                    "同节点": node,
                    "对比维度": {
                        "质地": {"source": "深度估值与基本面质量模型", "refresh": "每日+财报后", "status": "待理解岗补充", "value": None},
                        "当前价格位置": {
                            "候选": {"current_price": cand_quote.get("price"), "used_field": cand_quote.get("used_field"), "ma200": cand_metrics.get("ma200"), "high60": cand_metrics.get("high60"), "low60": cand_metrics.get("low60")},
                            "现持仓": {"current_price": hold_quote.get("price"), "used_field": hold_quote.get("used_field"), "ma200": hold_metrics.get("ma200"), "high60": hold_metrics.get("high60"), "low60": hold_metrics.get("low60")},
                        },
                    },
                    "建议": "【待理解岗判断换或不换】",
                })

    source_fp = gated.get("fingerprint", {})
    generated_at = now_jst()
    return {
        "task_id": "TASK-2026-07-02-059",
        "mode": "FORMAL_DUAL_CHANNEL_READ_ONLY",
        "generated_at": generated_at,
        "fingerprint": {
            "source_gated_file": str(gated_path.relative_to(ROOT)).replace("\\", "/"),
            "source_holdings_file": str(holdings_path.relative_to(ROOT)).replace("\\", "/"),
            "source_holdings_type": "holdings_true",
            "price_source": "scripts/realtime_price.py::get_realtime_price",
            "rate_limit_policy": f"每{BATCH_SIZE}个取价后等待{BATCH_SLEEP_SECONDS}秒",
            "total_gate": source_fp.get("total_gate"),
            "activated_node_classes": source_fp.get("activated_node_classes"),
            "generated_at": generated_at,
            "mode": "FORMAL_DUAL_CHANNEL_READ_ONLY",
            "dimensions_true": [TECH_DIM, COST_DIM, FUNDS_DIM],
            "dimensions_dynamic_placeholder": [VALUATION_DIM, CATALYST_DIM],
        },
        "safety": {"read_only": True, "quote_context_only": True, "trade_context_created": False, "place_order_called": False, "published": False, "swap_decision_made": False, "no_price_downgrade_on_fail": True},
        "price_connection_attempts": price_attempts,
        "channel_1_best_holding": {"description": "长期价值主体通道，只出同节点对比骨架，不下换仓结论", "comparison_count": len(compare_rows), "comparisons": compare_rows},
        "channel_2_trade_price": {"description": "买卖价格通道，当前价来自实时取价函数，均线与量能来自只读K线", "instrument_count": len(records), "instruments": records},
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Dual-channel opportunity pricing with realtime current price.")
    parser.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d"))
    args = parser.parse_args()
    output = build_output(args.date)
    output_path = OPPORTUNITY_DIR / f"dual_channel_{args.date}.json"
    write_json_utf8(output_path, output)
    sample_nvda = next((r for r in output["channel_2_trade_price"]["instruments"] if r.get("code") == "US.NVDA"), None)
    print(json.dumps({
        "output": str(output_path),
        "channel1_comparisons": output["channel_1_best_holding"]["comparison_count"],
        "channel2_instruments": output["channel_2_trade_price"]["instrument_count"],
        "nvda_quote": sample_nvda.get("realtime_quote") if sample_nvda else None,
        "fingerprint": output["fingerprint"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
