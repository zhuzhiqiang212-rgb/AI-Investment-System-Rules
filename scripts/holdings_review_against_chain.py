#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Review true holdings against the daily evidence-chain activated nodes.

TASK-2026-07-02-058.
Read-only:
- reads the daily evidence chain
- reads data/accounts/holdings_true_YYYYMMDD.json
- uses scripts/realtime_price.py::get_realtime_price for fresh quotes
- uses Futu quote-side plate APIs to judge active-node membership
- creates no trade context, sends no order, publishes nothing
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from realtime_price import connect_quote_context, get_realtime_price  # noqa: E402


EVIDENCE_DIR = ROOT / "data" / "evidence_chain"
ACCOUNTS_DIR = ROOT / "data" / "accounts"
OUTPUT_DIR = ROOT / "data" / "holdings"
HOST = "127.0.0.1"
PORT = 11111
JST = timezone(timedelta(hours=9))
MAX_PLATE_RETRIES = 3
RETRY_WAIT_SECONDS = 5
PRICE_STATE_CALLS_PER_WINDOW = 9
PRICE_STATE_WINDOW_SLEEP = 31
QMARK = chr(63)
REPL = chr(0xFFFD)


S = {
    "task": "TASK-2026-07-02-058",
    "strong": "\u5f3a",
    "medium": "\u4e2d",
    "weak": "\u5f31",
    "falsified": "\u8bc1\u4f2a",
    "total_gate": "\u603b\u95f8",
    "strategy_node": "\u6218\u7565\u6307\u5411",
    "security": "\u5b89\u5168",
    "energy": "\u80fd\u6e90",
    "compute": "\u7b97\u529b",
    "semi_equipment": "\u534a\u5bfc\u4f53\u8bbe\u5907",
    "memory": "\u5b58\u50a8",
    "foundry": "\u4ee3\u5de5",
    "ai_software": "AI\u5e94\u7528\u8f6f\u4ef6",
    "power": "\u7535\u529b",
    "ally_chain": "\u76df\u53cb\u94fe",
    "match": "\u7b26\u5408",
    "not_match": "\u4e0d\u7b26\u5408",
    "pending": "\u5f85\u8865",
    "confirmed": "\u8463\u4e8b\u957f\u786e\u8ba4",
}


NODE_DEFINITIONS = {
    S["compute"]: {
        "strategy": ["AI"],
        "gate_scope": [S["strong"], S["medium"]],
        "markets": ["US"],
        "plate_anchors": ["AI\u82af\u7247GPU", "\u534a\u5bfc\u4f53", "\u82af\u7247", "\u4eba\u5de5\u667a\u80fd"],
    },
    S["semi_equipment"]: {
        "strategy": ["AI"],
        "gate_scope": [S["strong"], S["medium"]],
        "markets": ["US", "JP"],
        "plate_anchors": ["\u534a\u5bfc\u4f53\u8bbe\u5907", "\u534a\u5bfc\u4f53", "\u8bbe\u5907"],
    },
    S["memory"]: {
        "strategy": ["AI"],
        "gate_scope": [S["strong"]],
        "markets": ["US", "HK", "JP"],
        "plate_anchors": ["\u5b58\u50a8\u82af\u7247", "\u5b58\u50a8", "\u8bb0\u5fc6\u4f53", "\u534a\u5bfc\u4f53"],
    },
    S["foundry"]: {
        "strategy": ["AI"],
        "gate_scope": [S["strong"], S["medium"]],
        "markets": ["US", "HK"],
        "plate_anchors": ["\u6676\u5706\u4ee3\u5de5", "\u4ee3\u5de5", "\u534a\u5bfc\u4f53"],
    },
    S["ai_software"]: {
        "strategy": ["AI"],
        "gate_scope": [S["strong"]],
        "markets": ["US"],
        "plate_anchors": ["AI\u8f6f\u4ef6\u5e94\u7528", "\u8f6f\u4ef6", "\u4e92\u8054\u7f51\u5185\u5bb9\u4e0e\u4fe1\u606f", "\u4eba\u5de5\u667a\u80fd"],
    },
    S["power"]: {
        "strategy": ["AI", S["energy"]],
        "gate_scope": [S["strong"], S["medium"]],
        "markets": ["US", "JP", "HK"],
        "plate_anchors": ["\u7535\u529b\u6838\u7535", "\u7535\u529b", "\u6838\u7535", "\u516c\u7528\u4e8b\u4e1a"],
    },
    S["ally_chain"]: {
        "strategy": ["AI"],
        "gate_scope": [S["strong"]],
        "markets": ["JP"],
        "plate_anchors": ["\u65e5\u80a1\u534a\u5bfc\u4f53\u94fe", "\u534a\u5bfc\u4f53", "\u7535\u5b50", "\u8bbe\u5907"],
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


def sanitize_tree(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace(QMARK, "[question_mark]").replace(REPL, "[replacement_char]")
    if isinstance(value, list):
        return [sanitize_tree(item) for item in value]
    if isinstance(value, dict):
        return {str(key): sanitize_tree(item) for key, item in value.items()}
    return value


def records_from_frame(obj: Any) -> list[dict[str, Any]]:
    if obj is None:
        return []
    if hasattr(obj, "to_dict"):
        return [{str(k): json_safe(v) for k, v in row.items()} for row in obj.to_dict(orient="records")]
    if isinstance(obj, list):
        out = []
        for row in obj:
            if isinstance(row, dict):
                out.append({str(k): json_safe(v) for k, v in row.items()})
            else:
                out.append({"raw": json_safe(row)})
        return out
    if isinstance(obj, dict):
        return [{str(k): json_safe(v) for k, v in obj.items()}]
    return [{"raw": json_safe(obj)}]


def write_json_utf8(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    clean_payload = sanitize_tree(payload)
    text = json.dumps(clean_payload, ensure_ascii=False, indent=2) + "\n"
    if QMARK in text or REPL in text:
        raise RuntimeError(f"garble marker found before write: {path}")
    path.write_text(text, encoding="utf-8", newline="\n")
    reread = path.read_text(encoding="utf-8")
    if reread != text:
        raise RuntimeError(f"UTF-8 reread mismatch: {path}")
    if QMARK in reread or REPL in reread:
        raise RuntimeError(f"garble marker found after write: {path}")


def load_evidence(date_text: str) -> tuple[dict[str, Any], str]:
    path = EVIDENCE_DIR / f"daily_{date_text}.json"
    if not path.exists():
        raise FileNotFoundError(f"need daily evidence chain first: {path}")
    return json.loads(path.read_text(encoding="utf-8")), str(path)


def extract_chain_state(evidence: dict[str, Any]) -> tuple[str, list[str]]:
    total_gate = S["pending"]
    strategies: list[str] = []
    for link in evidence.get("links", []):
        node = str(link.get("node", ""))
        strength = str(link.get("strength", ""))
        direction = str(link.get("direction", ""))
        if S["total_gate"] in node and strength in [S["strong"], S["medium"], S["weak"], S["falsified"]]:
            total_gate = strength
        if S["strategy_node"] in node:
            for item in ["AI", S["security"], S["energy"]]:
                if item in direction and item not in strategies:
                    strategies.append(item)
    return total_gate, strategies


def active_nodes(total_gate: str, strategies: list[str]) -> list[str]:
    if total_gate in [S["weak"], S["falsified"], S["pending"]]:
        return []
    nodes: list[str] = []
    for node, cfg in NODE_DEFINITIONS.items():
        if total_gate not in cfg["gate_scope"]:
            continue
        if any(strategy in strategies for strategy in cfg["strategy"]):
            nodes.append(node)
    return nodes


def load_true_holdings(date_text: str) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    path = ACCOUNTS_DIR / f"holdings_true_{date_text}.json"
    if not path.exists():
        raise FileNotFoundError(f"need true holdings base table first: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("holdings", []), str(path), payload.get("fingerprint", {})


def market_enum(name: str):
    from futu import Market

    return getattr(Market, name)


def find_matching_plates(ctx: Any, market: str, anchors: list[str]) -> tuple[list[dict[str, Any]], str, int, list[str]]:
    from futu import Plate, RET_OK

    retry_count = 0
    retry_events: list[str] = []
    last_error = ""
    for attempt in range(1, MAX_PLATE_RETRIES + 1):
        ret, data = ctx.get_plate_list(market_enum(market), Plate.ALL)
        if ret == RET_OK:
            plates = records_from_frame(data)
            matched = []
            for plate in plates:
                name = str(plate.get("plate_name", ""))
                if any(anchor.lower() in name.lower() for anchor in anchors):
                    matched.append(plate)
            return matched[:3], "", retry_count, retry_events
        last_error = str(data)
        if attempt < MAX_PLATE_RETRIES:
            retry_count += 1
            retry_events.append(f"get_plate_list/{market} attempt {attempt} failed; wait {RETRY_WAIT_SECONDS}s; {last_error}")
            time.sleep(RETRY_WAIT_SECONDS)
    return [], last_error, retry_count, retry_events


def build_active_members(active_node_list: list[str]) -> tuple[dict[str, list[dict[str, str]]], list[str], int, list[str]]:
    from futu import OpenQuoteContext, RET_OK

    members: dict[str, list[dict[str, str]]] = {}
    errors: list[str] = []
    retry_total = 0
    retry_events: list[str] = []
    plate_cache: dict[str, list[dict[str, Any]]] = {}
    if not active_node_list:
        return members, errors, retry_total, retry_events

    ctx = OpenQuoteContext(host=HOST, port=PORT)
    try:
        for node in active_node_list:
            cfg = NODE_DEFINITIONS[node]
            node_members: list[dict[str, str]] = []
            for market in cfg["markets"]:
                plates, plate_error, retries, events = find_matching_plates(ctx, market, cfg["plate_anchors"])
                retry_total += retries
                retry_events.extend(events)
                if plate_error:
                    errors.append(f"{node}/{market}: {plate_error}")
                    continue
                for plate in plates[:2]:
                    code = str(plate.get("code", ""))
                    if code not in plate_cache:
                        last_error = ""
                        for attempt in range(1, MAX_PLATE_RETRIES + 1):
                            ret, data = ctx.get_plate_stock(code)
                            if ret == RET_OK:
                                plate_cache[code] = records_from_frame(data)
                                break
                            last_error = str(data)
                            if attempt < MAX_PLATE_RETRIES:
                                retry_total += 1
                                retry_events.append(f"get_plate_stock/{code} attempt {attempt} failed; wait {RETRY_WAIT_SECONDS}s; {last_error}")
                                time.sleep(RETRY_WAIT_SECONDS)
                        else:
                            errors.append(f"{node}/{code}: {last_error}")
                            plate_cache[code] = []
                        time.sleep(3.2)
                    for row in plate_cache.get(code, []):
                        stock_code = str(row.get("code") or row.get("stock_code") or "")
                        stock_name = str(row.get("stock_name") or row.get("name") or "")
                        node_members.append({
                            "code": stock_code,
                            "base": base_code(stock_code),
                            "name": stock_name,
                            "node_class": node,
                            "plate_code": code,
                            "plate_name": str(plate.get("plate_name", "")),
                        })
            members[node] = node_members
    finally:
        ctx.close()
    return members, errors, retry_total, retry_events


def base_code(code: str) -> str:
    value = str(code or "").strip()
    if "." in value:
        value = value.split(".")[-1]
    if value.endswith(".T"):
        value = value[:-2]
    return value.upper()


def holding_aliases(row: dict[str, Any]) -> set[str]:
    symbol = str(row.get("symbol") or row.get("code") or "").strip()
    aliases = set()
    if symbol:
        aliases.add(symbol.upper())
        aliases.add(base_code(symbol))
    return aliases


def refresh_prices(holdings: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    price_map: dict[str, dict[str, Any]] = {}
    ctx, attempts = connect_quote_context(max_retries=3, wait_seconds=3)
    if ctx is None:
        for row in holdings:
            symbol = str(row.get("symbol", ""))
            price_map[symbol] = {
                "code": symbol,
                "status": "FAIL",
                "price": None,
                "reason": "OpenD quote connection failed",
                "connection_attempts": attempts,
            }
        return price_map, attempts
    try:
        for index, row in enumerate(holdings):
            if index and index % PRICE_STATE_CALLS_PER_WINDOW == 0:
                time.sleep(PRICE_STATE_WINDOW_SLEEP)
            symbol = str(row.get("symbol", ""))
            price_map[symbol] = get_realtime_price(symbol, ctx=ctx)
    finally:
        ctx.close()
    return price_map, attempts


def calc_market_value(price: Any, quantity: Any) -> float | None:
    if price is None or quantity is None:
        return None
    return round(float(price) * float(quantity), 4)


def review_holding(
    holding: dict[str, Any],
    quote: dict[str, Any],
    active_members: dict[str, list[dict[str, str]]],
    data_gaps: list[str],
) -> dict[str, Any]:
    aliases = holding_aliases(holding)
    matched = []
    for _node, members in active_members.items():
        for member in members:
            member_aliases = {str(member.get("code", "")).upper(), str(member.get("base", "")).upper()}
            if aliases & member_aliases:
                matched.append(member)

    if quote.get("status") != "OK":
        verdict = S["pending"]
        reason = "\u5b9e\u65f6\u53d6\u4ef7FAIL\uff0c\u4e0d\u7528\u65e7\u4ef7\u964d\u7ea7"
    elif matched:
        verdict = S["match"]
        reason = "\u843d\u5728\u4eca\u65e5\u6fc0\u6d3b\u8282\u70b9\u677f\u5757\u6210\u5206\u4e2d\uff0c\u5728\u4eca\u65e5\u6218\u7565\u65b9\u5411\u4e0a"
    else:
        verdict = S["not_match"]
        if data_gaps:
            reason = "\u672a\u5339\u914d\u4eca\u65e5\u6fc0\u6d3b\u8282\u70b9\uff1b\u677f\u5757\u6570\u636e\u5b58\u5728\u90e8\u5206\u7f3a\u53e3\uff0c\u9700\u590d\u6838"
        else:
            reason = "\u672a\u843d\u5728\u4efb\u4f55\u4eca\u65e5\u6fc0\u6d3b\u8282\u70b9\u677f\u5757"

    total_quantity = holding.get("total_quantity")
    price = quote.get("price")
    account_rows = []
    for item in holding.get("accounts", []):
        quantity = item.get("quantity")
        account_rows.append({
            **item,
            "market_value": calc_market_value(price, quantity),
        })

    return {
        "symbol": holding.get("symbol"),
        "name": holding.get("name"),
        "total_quantity": total_quantity,
        "quantity_status": holding.get("quantity_status"),
        "accounts": account_rows,
        "realtime_price": price,
        "used_field": quote.get("used_field"),
        "market_state": quote.get("market_state"),
        "data_date": quote.get("data_date"),
        "data_time": quote.get("data_time"),
        "quote_status": quote.get("status"),
        "quote_reason": quote.get("reason"),
        "market_value": calc_market_value(price, total_quantity),
        "currency_hint": holding.get("currency_hint"),
        "verdict": verdict,
        "reason": reason,
        "matched_node_classes": sorted({item["node_class"] for item in matched}),
        "matched_plate_examples": matched[:5],
    }


def summarize(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        S["match"]: sum(1 for row in reviews if row.get("verdict") == S["match"]),
        S["not_match"]: sum(1 for row in reviews if row.get("verdict") == S["not_match"]),
        S["pending"]: sum(1 for row in reviews if row.get("verdict") == S["pending"]),
        "price_FAIL": sum(1 for row in reviews if row.get("quote_status") != "OK"),
        "total": len(reviews),
    }


def data_source_status(errors: list[str], retry_total: int, reviews: list[dict[str, Any]]) -> tuple[str, list[str]]:
    all_pending_due_to_plate_gap = bool(errors) and bool(reviews) and all(row.get("verdict") == S["pending"] for row in reviews)
    if all_pending_due_to_plate_gap:
        status = "\u677f\u5757\u6570\u636e\u83b7\u53d6\u5931\u8d25\uff0c\u6301\u4ed3\u5ba1\u67e5\u964d\u7ea7\u4e3a\u5168\u5f85\u8865\uff0c\u9700\u68c0\u67e5OpenD\u8fde\u63a5"
    elif errors:
        status = "\u677f\u5757\u6570\u636e\u90e8\u5206\u5931\u8d25\uff0c\u5df2\u4fdd\u7559\u544a\u8b66\uff0c\u672a\u9759\u9ed8\u964d\u7ea7"
    elif retry_total:
        status = "\u677f\u5757\u6570\u636e\u53ef\u7528\uff0c\u66fe\u9047\u5230\u77ac\u65f6\u5931\u8d25\u5e76\u5df2\u91cd\u8bd5\u6062\u590d"
    else:
        status = "\u677f\u5757\u6570\u636e\u53ef\u7528"
    warnings = [status] if (errors or retry_total or all_pending_due_to_plate_gap) else []
    return status, warnings


def build_output(date_text: str) -> dict[str, Any]:
    evidence, evidence_source = load_evidence(date_text)
    total_gate, strategies = extract_chain_state(evidence)
    nodes = active_nodes(total_gate, strategies)
    holdings, holdings_source, holdings_fingerprint = load_true_holdings(date_text)
    price_map, price_connection_attempts = refresh_prices(holdings)
    active_members, errors, retry_total, retry_events = build_active_members(nodes)
    reviews = [
        review_holding(holding, price_map.get(str(holding.get("symbol")), {}), active_members, errors)
        for holding in holdings
    ]
    summary = summarize(reviews)
    status, warnings = data_source_status(errors, retry_total, reviews)
    return {
        "task_id": S["task"],
        "mode": "FORMAL_TRUE_HOLDINGS_REVIEW_AGAINST_CHAIN",
        "generated_at": now_jst(),
        "fingerprint": {
            "evidence_source": evidence_source,
            "holdings_source": holdings_source,
            "holdings_source_type": "holdings_true",
            "share_count_source": "\u8463\u4e8b\u957f\u622a\u56fe\u786e\u8ba42026-07-02",
            "price_source": "OpenD realtime via scripts/realtime_price.py::get_realtime_price",
            "cross_account_merged": True,
            "total_gate": total_gate,
            "strategic_directions": strategies,
            "activated_node_classes": nodes,
            "generated_at": now_jst(),
            "mode": "FORMAL_TRUE_HOLDINGS_REVIEW_AGAINST_CHAIN",
            "source_holdings_fingerprint": holdings_fingerprint,
        },
        "safety": {
            "read_only": True,
            "quote_context_only": True,
            "trade_context_created": False,
            "place_order_called": False,
            "published": False,
            "specific_trade_advice": False,
            "no_price_downgrade_on_fail": True,
        },
        "price_connection_attempts": price_connection_attempts,
        "data_source_status": status,
        "data_source_retry_count": retry_total,
        "data_source_retry_events": retry_events,
        "warnings": warnings,
        "data_gaps": errors,
        "summary": summary,
        "reviews": reviews,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Review true holdings against daily chain activated nodes.")
    parser.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d"))
    args = parser.parse_args()

    try:
        output = build_output(args.date)
    except FileNotFoundError as exc:
        print(str(exc))
        return 2

    output_path = OUTPUT_DIR / f"holdings_review_{args.date}.json"
    write_json_utf8(output_path, output)

    print(f"OUTPUT_PATH={output_path}")
    print(f"MODE={output['mode']}")
    print(f"TOTAL_GATE={output['fingerprint']['total_gate']}")
    print(f"ACTIVE_NODES={','.join(output['fingerprint']['activated_node_classes'])}")
    print(f"DATA_SOURCE_STATUS={output.get('data_source_status', '')}")
    print(f"RETRY_COUNT={output.get('data_source_retry_count', 0)}")
    print(f"SUMMARY={json.dumps(output['summary'], ensure_ascii=False)}")
    for item in output["reviews"][:8]:
        print(
            f"SAMPLE={item.get('symbol')} {item.get('name')} "
            f"QTY={item.get('total_quantity')} PRICE={item.get('realtime_price')} "
            f"FIELD={item.get('used_field')} VERDICT={item.get('verdict')} "
            f"NODES={','.join(item.get('matched_node_classes', []))}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
