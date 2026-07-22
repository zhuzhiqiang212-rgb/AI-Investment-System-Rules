#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build catalyst dimension data.

TASK-2026-07-02-059 update:
- reads holdings_true_YYYYMMDD.json
- peer-comparison current prices use realtime_price.py
- no stale model-instance current_price fallback when realtime quote fails
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



MODEL_TYPE_FALLBACK = {
    "US.MSFT": "成长情景PE",
    "US.NVDA": "成长情景PE",
    "JP.9984": "NAV折价",
    "JP.6857": "周期PE",
    "JP.4568": "医药管线DCF",
    "JP.8766": "保险内含价值EV",
    "US.MSTR": "加密mNAV",
}


def collect_holdings(date_text: str) -> tuple[list[dict[str, Any]], Path]:
    path = ROOT / "data" / "accounts" / f"holdings_true_{date_text}.json"
    data = read_json(path)
    rows = [{"code": row.get("symbol"), "name": row.get("name") or row.get("symbol"), "source": "holding_true", "raw": row} for row in data.get("holdings", []) if row.get("symbol")]
    return rows, path


def collect_candidates(date_text: str) -> tuple[list[dict[str, Any]], dict[str, Any], Path]:
    path = ROOT / "data" / "opportunities" / f"chain_opportunities_{date_text}.json"
    data = read_json(path, {})
    rows = [{"code": row.get("code"), "name": row.get("name") or row.get("code"), "source": "chain_opportunity", "raw": row} for row in data.get("candidates", []) if row.get("code")]
    return rows, data.get("fingerprint", {}), path


def collect_dispatch(date_text: str) -> tuple[dict[str, dict[str, Any]], Path]:
    path = ROOT / "data" / "valuation" / f"valuation_dispatch_{date_text}.json"
    data = read_json(path, {})
    index: dict[str, dict[str, Any]] = {}
    for row in data.get("records", []):
        code = row.get("code")
        if not code:
            continue
        index[normalize_code(code)] = row
        index[code_tail(code)] = row
    return index, path


def merge_universe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in items:
        key = normalize_code(item["code"])
        if key not in merged:
            merged[key] = {"code": item["code"], "name": item.get("name") or item["code"], "sources": [], "raw_by_source": {}}
        merged[key]["sources"].append(item["source"])
        merged[key]["raw_by_source"][item["source"]] = item.get("raw", {})
        if item.get("name"):
            merged[key]["name"] = item["name"]
    return list(merged.values())


def model_type_for(code: str, name: str, dispatch_index: dict[str, dict[str, Any]], instance_payload: dict[str, Any] | None = None) -> str:
    dispatch = dispatch_index.get(normalize_code(code)) or dispatch_index.get(code_tail(code)) or {}
    if dispatch.get("所属模型"):
        return dispatch["所属模型"]
    if instance_payload and instance_payload.get("model_type"):
        return instance_payload["model_type"]
    return MODEL_TYPE_FALLBACK.get(normalize_code(code)) or MODEL_TYPE_FALLBACK.get(code_tail(code)) or "待估值分派"


def load_model_instances(dispatch_index: dict[str, dict[str, Any]], price_map: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    instance_dir = ROOT / "data" / "valuation" / "model_instances"
    instances: list[dict[str, Any]] = []
    index: dict[str, dict[str, Any]] = {}
    if not instance_dir.exists():
        return instances, index
    for path in sorted(instance_dir.glob("*.json")):
        payload = read_json(path, {})
        symbol = payload.get("symbol")
        if not symbol:
            continue
        name = payload.get("name") or symbol
        model_type = model_type_for(symbol, name, dispatch_index, payload)
        bands = payload.get("valuation_bands") or {}
        center = parse_money(bands.get("base") or bands.get("center") or bands.get("reasonable_center"))
        quote = price_map.get(symbol) or price_map.get(normalize_code(symbol))
        current = quote.get("price") if quote and quote.get("status") == "OK" else None
        ratio = round((float(current) / float(center) - 1) * 100, 2) if current is not None and center not in [None, 0] else None
        record = {
            "symbol": symbol,
            "name": name,
            "model_type": model_type,
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "current_price": current,
            "current_price_source": "scripts/realtime_price.py::get_realtime_price",
            "current_quote": quote,
            "center_price": bands.get("base") or bands.get("center") or bands.get("reasonable_center"),
            "current_vs_center_pct": ratio,
            "status": "可横比" if ratio is not None else "实时价或中枢待补",
            "legacy_instance_current_price_ignored": payload.get("inputs", {}).get("current_price"),
        }
        instances.append(record)
        for key in {normalize_code(symbol), code_tail(symbol), str(name).strip().lower()}:
            index[key] = record
    return instances, index


def build_peer_groups(instances: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for inst in instances:
        groups[inst["model_type"]].append(inst)
    out: dict[str, dict[str, Any]] = {}
    for model_type, rows in groups.items():
        comparable = [row for row in rows if row.get("current_vs_center_pct") is not None]
        ordered = sorted(comparable, key=lambda x: x["current_vs_center_pct"])
        out[model_type] = {
            "model_type": model_type,
            "instance_count": len(rows),
            "comparable_count": len(comparable),
            "instances": rows,
            "cheapest_by_current_vs_center": ordered[0] if len(ordered) >= 2 else None,
            "richest_by_current_vs_center": ordered[-1] if len(ordered) >= 2 else None,
            "status": "横比可用" if len(ordered) >= 2 else ("该类仅1个实例，暂不足以横比" if len(rows) == 1 else "实例或实时价不足"),
        }
    return out


def financial_calendar_stub(code: str, name: str) -> dict[str, Any]:
    return {"next_earnings_estimated_date": None, "source": "财报日历", "refresh": "每日", "status": "待人工填入或后续接口接入", "value_basis": "v1先建动态字段结构，不伪造日期", "symbol": code, "name": name}


_CATALYST_LIB_CACHE: dict[str, list] | None = None


def load_catalyst_library() -> dict[str, list]:
    """读催化剂库·按标的index(P1三要素规范v1落地·替换event_driven空壳)。"""
    global _CATALYST_LIB_CACHE
    if _CATALYST_LIB_CACHE is None:
        lib = read_json(ROOT / "data" / "catalyst" / "catalyst_library.json", {}) or {}
        idx: dict[str, list] = {}
        for e in lib.get("催化剂", []):
            idx.setdefault(str(e.get("标的")), []).append(e)
        _CATALYST_LIB_CACHE = idx
    return _CATALYST_LIB_CACHE


def event_driven_from_library(code: str) -> dict[str, Any]:
    """event_driven 维:按三要素结构从催化剂库读(替换 value=None 空壳)。无则标待补·不编造。"""
    idx = load_catalyst_library()
    cats = idx.get(code) or idx.get(normalize_code(code)) or []
    if not cats:
        return {"source": "催化剂库(data/catalyst/catalyst_library.json)", "refresh": "事件驱动",
                "status": "该标的无催化剂入库·待补(不编造)", "催化剂数": 0, "催化剂": []}
    return {"source": "催化剂库(data/catalyst/catalyst_library.json·三要素规范v1)", "refresh": "事件驱动",
            "status": "已接催化剂库", "催化剂数": len(cats),
            "催化剂": [{"id": c.get("id"), "催化剂": c.get("催化剂"), "三要素": c.get("三要素"),
                     "三要素完整": c.get("三要素完整"), "准入状态": c.get("准入状态"),
                     "可单独支撑预测方向": c.get("可单独支撑预测方向")} for c in cats]}


def build(date_text: str) -> dict[str, Any]:
    holdings, holdings_path = collect_holdings(date_text)
    candidates, opportunity_fingerprint, opportunities_path = collect_candidates(date_text)
    dispatch_index, dispatch_path = collect_dispatch(date_text)
    universe = merge_universe([*holdings, *candidates])

    instance_dir = ROOT / "data" / "valuation" / "model_instances"
    instance_codes = []
    if instance_dir.exists():
        for path in sorted(instance_dir.glob("*.json")):
            payload = read_json(path, {})
            if payload.get("symbol"):
                instance_codes.append(payload["symbol"])
    all_codes = [item["code"] for item in universe] + instance_codes
    price_map, attempts = realtime_batch(all_codes)
    instances, instance_index = load_model_instances(dispatch_index, price_map)
    peer_groups = build_peer_groups(instances)

    records = []
    for item in universe:
        code = item["code"]
        name = item["name"]
        model_type = model_type_for(code, name, dispatch_index)
        inst = instance_index.get(normalize_code(code)) or instance_index.get(code_tail(code)) or instance_index.get(str(name).strip().lower())
        group = peer_groups.get(model_type)
        quote = price_map.get(code) or price_map.get(normalize_code(code)) or {}
        if group:
            if group["instance_count"] == 1 and not inst:
                status = "该类仅1个实例，暂不足以横比"
                cheap = None
                rich = None
            elif group["instance_count"] == 1 and inst:
                status = "本标的是该类唯一实例，仅显示自身实时价vs中枢，不外推给同类"
                cheap = inst
                rich = inst
            else:
                status = group["status"]
                cheap = group["cheapest_by_current_vs_center"]
                rich = group["richest_by_current_vs_center"]
            peer = {
                "model_type": model_type,
                "status": status,
                "instance_count": group["instance_count"],
                "comparable_count": group["comparable_count"],
                "current_instance": inst,
                "self_price_participation": {
                    "status": "实时价已读取" if quote.get("status") == "OK" else "实时价FAIL不降级",
                    "price": quote.get("price"),
                    "used_field": quote.get("used_field"),
                    "source": "scripts/realtime_price.py::get_realtime_price",
                },
                "cheapest_by_current_vs_center": cheap,
                "richest_by_current_vs_center": rich,
            }
        else:
            peer = {"model_type": model_type, "status": "该模型暂无实例，待补后横比", "instance_count": 0, "comparable_count": 0, "current_instance": None, "cheapest_by_current_vs_center": None, "richest_by_current_vs_center": None}
        records.append({
            "code": code,
            "name": name,
            "sources": sorted(set(item["sources"])),
            "model_type": model_type,
            "realtime_quote": quote,
            "financial_calendar": financial_calendar_stub(code, name),
            "peer_comparison": peer,
            "event_driven": event_driven_from_library(code),
        })

    generated_at = now_jst()
    return {
        "task_id": "TASK-2026-07-02-059",
        "date": date_text,
        "generated_at": generated_at,
        "fingerprint": {
            "date": date_text,
            "generated_at": generated_at,
            "mode": "FORMAL_CATALYST_DIMENSION_READ_ONLY",
            "source_holdings_file": str(holdings_path.relative_to(ROOT)).replace("\\", "/"),
            "source_holdings_type": "holdings_true",
            "source_opportunity_file": str(opportunities_path.relative_to(ROOT)).replace("\\", "/"),
            "source_valuation_dispatch_file": str(dispatch_path.relative_to(ROOT)).replace("\\", "/"),
            "model_instance_source": "data/valuation/model_instances/*.json",
            "price_source": "scripts/realtime_price.py::get_realtime_price",
            "rate_limit_policy": f"每{BATCH_SIZE}个取价后等待{BATCH_SLEEP_SECONDS}秒",
            "opportunity_fingerprint": opportunity_fingerprint,
            "symbol_source_counts": {"holdings_true": len(holdings), "chain_opportunities": len(candidates), "combined_unique": len(universe), "model_instances": len(instances), "realtime_price_codes": len(set(all_codes))},
            "fixed_stock_answer_written": False,
            "read_only": True,
        },
        "safety": {"read_only": True, "trade_context_created": False, "place_order_called": False, "published": False, "static_answer_written": False, "missing_dates_fabricated": False, "no_price_downgrade_on_fail": True},
        "price_connection_attempts": attempts,
        "dimension_status": {
            "financial_calendar": {"done": True, "status": "结构已建，日期字段待人工或接口填入", "refresh": "每日"},
            "peer_comparison": {"done": True, "status": "读取实时价与模型实例动态横比", "instance_count": len(instances)},
            "event_driven": {"done": True, "status": "已接催化剂库(三要素规范v1·data/catalyst/catalyst_library.json)",
                             "refresh": "事件驱动", "库条数": sum(len(v) for v in load_catalyst_library().values())},
        },
        "peer_groups": peer_groups,
        "records": records,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Build catalyst dimension data with realtime price peer comparison.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    payload = build(args.date)
    out_path = Path(args.out) if args.out else ROOT / "data" / "catalyst" / f"catalyst_{args.date}.json"
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    write_json_utf8(out_path, payload)
    nvda = next((r for r in payload["records"] if r.get("code") == "US.NVDA"), None)
    msft = next((r for r in payload["records"] if r.get("code") == "US.MSFT"), None)
    print(json.dumps({
        "output": str(out_path),
        "fingerprint": payload["fingerprint"],
        "dimension_status": payload["dimension_status"],
        "nvda_peer": nvda.get("peer_comparison") if nvda else None,
        "msft_peer": msft.get("peer_comparison") if msft else None,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
