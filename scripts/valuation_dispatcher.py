#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Dynamic valuation model dispatcher.

TASK-2026-07-02-059 update:
- reads holdings_true_YYYYMMDD.json instead of legacy unified holdings
- reads chain opportunities
- classifies by business model and dynamic metadata
- does not fetch prices, calculate valuation numbers, trade, or publish
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


JST = timezone(timedelta(hours=9))
QMARK = chr(63)
REPL = chr(0xFFFD)


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




MODEL_INPUTS: dict[str, list[str]] = {
    "成长情景PE": ["前瞻EPS", "收入或利润增速", "毛利率趋势", "资本开支压力", "熊/基准/牛PE假设"],
    "NAV折价": ["每股NAV", "核心资产估值", "现金与负债", "LTV", "历史折价带"],
    "周期PE": ["前瞻EPS", "周期位置", "订单与资本开支趋势", "正常化PE", "峰值盈利警示"],
    "医药管线DCF": ["核心管线", "峰值销售", "成功率", "现金流", "专利期", "折现率"],
    "保险内含价值EV": ["EV", "新业务价值", "PEV倍数", "承保利润", "投资收益", "利率敏感度"],
    "加密mNAV": ["持币量或净资产", "币价", "mNAV倍数", "交易收入", "融资与稀释风险", "监管状态"],
    "非战略简易估值": ["商业模式类型", "同业基础倍数", "盈利或净资产口径", "股息或回购", "非战略持仓去留触发线"],
}

MODEL_ALIASES = {
    "成长情景PE": "growth_scenario_pe",
    "NAV折价": "nav_discount",
    "周期PE": "cyclical_pe",
    "医药管线DCF": "pharma_pipeline_dcf",
    "保险内含价值EV": "insurance_ev",
    "加密mNAV": "crypto_mnav",
    "非战略简易估值": "non_strategic_simple_valuation",
}


def collect_holdings(date_text: str) -> tuple[list[dict[str, Any]], dict[str, Any], Path]:
    path = ROOT / "data" / "accounts" / f"holdings_true_{date_text}.json"
    data = read_json(path)
    items = []
    for row in data.get("holdings", []):
        code = row.get("symbol")
        if not code:
            continue
        items.append({
            "code": code,
            "name": row.get("name") or code,
            "source": "holding_true",
            "holding": row,
            "candidate": None,
        })
    return items, data.get("fingerprint", {}), path


def collect_candidates(date_text: str) -> tuple[list[dict[str, Any]], dict[str, Any], Path]:
    path = ROOT / "data" / "opportunities" / f"chain_opportunities_{date_text}.json"
    data = read_json(path, {})
    items = []
    for row in data.get("candidates", []):
        code = row.get("code") or row.get("ticker") or row.get("symbol")
        if not code:
            continue
        items.append({
            "code": code,
            "name": row.get("name") or code,
            "source": "chain_opportunity",
            "holding": None,
            "candidate": row,
        })
    return items, data.get("fingerprint", {}), path


def merge_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in items:
        key = normalize_code(item["code"])
        if key not in merged:
            merged[key] = {
                "code": item["code"],
                "name": item.get("name") or item["code"],
                "sources": [],
                "holding": None,
                "candidate": None,
            }
        merged[key]["sources"].append(item["source"])
        if item.get("holding") is not None:
            merged[key]["holding"] = item["holding"]
            merged[key]["name"] = item.get("name") or merged[key]["name"]
        if item.get("candidate") is not None:
            merged[key]["candidate"] = item["candidate"]
            merged[key]["name"] = item.get("name") or merged[key]["name"]
    return list(merged.values())


def text_blob(item: dict[str, Any]) -> str:
    parts = [str(item.get("code", "")), str(item.get("name", ""))]
    for obj in [item.get("holding") or {}, item.get("candidate") or {}]:
        for key in ("sector", "industry", "theme", "plate_name", "node_class", "name", "symbol"):
            if obj.get(key):
                parts.append(str(obj[key]))
    return " ".join(parts).lower()


def contains_any(blob: str, words: list[str]) -> bool:
    return any(word.lower() in blob for word in words)


def classify_item(item: dict[str, Any]) -> tuple[str, str | None, str]:
    code = normalize_code(item.get("code", ""))
    tail = code_tail(code)
    blob = text_blob(item)
    candidate = item.get("candidate") or {}
    node_class = str(candidate.get("node_class") or "")

    if tail in {"NVDA", "MSFT", "AVGO", "TSM", "META"}:
        return "成长科技", "成长情景PE", "美股AI核心或半导体节点代码锚命中"
    if tail in {"SNDK"}:
        return "周期硬件", "周期PE", "存储硬件周期属性代码锚命中"

    if code.startswith("CC.") or contains_any(blob, ["btc", "eth", "bitcoin", "ethereum", "crypto", "加密", "coinbase", "circle", "mstr", "strategy"]):
        return "加密相关", "加密mNAV", "加密或持币商业模式锚命中"
    if tail == "8766" or contains_any(blob, ["保险", "insurance", "tokio marine", "东京海上"]):
        return "保险", "保险内含价值EV", "保险商业模式锚命中"
    if tail == "4568" or contains_any(blob, ["医药", "pharma", "biotech", "三共", "daiichi"]):
        return "医药", "医药管线DCF", "医药管线商业模式锚命中"
    if tail == "9984" or contains_any(blob, ["控股", "投资公司", "holding", "nav", "软银", "softbank"]):
        return "控股投资公司", "NAV折价", "控股投资商业模式锚命中"
    if tail == "6857" or node_class == "半导体设备" or contains_any(blob, ["设备", "equipment", "semiconductor equipment", "爱德万", "advantest", "amat", "asml", "lam research", "kla"]):
        return "周期设备", "周期PE", "设备与资本开支周期锚命中"
    if node_class in {"算力", "代工", "AI应用软件"} or contains_any(blob, ["ai", "cloud", "software", "gpu", "芯片", "半导体", "算力", "代工", "microsoft", "nvidia", "meta", "tsmc", "broadcom"]):
        return "成长科技", "成长情景PE", "成长科技或AI节点锚命中"

    non_strategy = "非AI战略主线，简易估值即可，不做深度模型，可迭代升级"
    if tail == "7203" or contains_any(blob, ["toyota", "丰田", "汽车", "auto"]):
        return "非战略周期", "非战略简易估值", non_strategy + "；汽车周期商业模式锚命中"
    if tail in {"7974", "7832"} or contains_any(blob, ["nintendo", "bandai", "任天堂", "万代", "娱乐", "玩具", "游戏", "ip"]):
        return "非战略简易PE", "非战略简易估值", non_strategy + "；消费娱乐IP商业模式锚命中"
    if tail == "6758" or contains_any(blob, ["sony", "索尼", "综合电子", "electronics"]):
        return "非战略分部", "非战略简易估值", non_strategy + "；综合电子分部商业模式锚命中"
    if tail == "8001" or contains_any(blob, ["itochu", "伊藤忠", "商社", "trading company"]):
        return "非战略PB股息", "非战略简易估值", non_strategy + "；综合商社商业模式锚命中"
    if tail == "IBKR" or contains_any(blob, ["ibkr", "interactive brokers", "broker", "券商", "经纪"]):
        return "非战略PE", "非战略简易估值", non_strategy + "；券商商业模式锚命中"
    return "待人工归类", None, "行业或商业模式锚不足，未硬套模型"


def load_model_instance_index() -> dict[str, Path]:
    index: dict[str, Path] = {}
    instance_dir = ROOT / "data" / "valuation" / "model_instances"
    if not instance_dir.exists():
        return index
    for path in instance_dir.glob("*.json"):
        try:
            payload = read_json(path)
        except Exception:
            continue
        symbol = normalize_code(payload.get("symbol", ""))
        name = str(payload.get("name", "")).strip().lower()
        if symbol:
            index[symbol] = path
            index[code_tail(symbol)] = path
        if name:
            index[name] = path
    return index


def instance_path_for(item: dict[str, Any], model_type: str | None, instance_index: dict[str, Path]) -> str | None:
    if model_type is None:
        return None
    keys = [normalize_code(item.get("code", "")), code_tail(item.get("code", "")), str(item.get("name", "")).strip().lower()]
    for key in keys:
        path = instance_index.get(key)
        if path:
            return str(path.relative_to(ROOT)).replace("\\", "/")
    return None


def build_dispatch(date_text: str, symbols: list[str] | None) -> dict[str, Any]:
    holdings, holdings_fingerprint, holdings_path = collect_holdings(date_text)
    candidates, opportunity_fingerprint, opportunities_path = collect_candidates(date_text)
    combined = merge_items([*holdings, *candidates])
    if symbols:
        allowed = {normalize_code(s) for s in symbols} | {code_tail(s) for s in symbols}
        combined = [item for item in combined if normalize_code(item["code"]) in allowed or code_tail(item["code"]) in allowed]

    instance_index = load_model_instance_index()
    records = []
    for item in combined:
        classification, model_type, reason = classify_item(item)
        inst_path = instance_path_for(item, model_type, instance_index)
        if model_type is None:
            status = "待人工归类"
            inputs = []
            alias = None
        elif inst_path:
            status = "已建模实例"
            inputs = MODEL_INPUTS[model_type]
            alias = MODEL_ALIASES[model_type]
        else:
            status = "待补输入"
            inputs = MODEL_INPUTS[model_type]
            alias = MODEL_ALIASES[model_type]
        records.append({
            "code": item["code"],
            "name": item["name"],
            "sources": sorted(set(item["sources"])),
            "判定类型": classification,
            "所属模型": model_type or "待人工归类",
            "model_alias": alias,
            "所需输入清单": inputs,
            "状态": status,
            "判定理由": reason,
            "model_instance_path": inst_path,
        })

    dist = Counter(row["所属模型"] for row in records)
    status_dist = Counter(row["状态"] for row in records)
    unknown = [row for row in records if row["状态"] == "待人工归类"]
    generated_at = now_jst()
    return {
        "task_id": "TASK-2026-07-02-059",
        "date": date_text,
        "generated_at": generated_at,
        "fingerprint": {
            "date": date_text,
            "generated_at": generated_at,
            "mode": "FORMAL_VALUATION_DISPATCH_READ_ONLY",
            "source_holdings_file": str(holdings_path.relative_to(ROOT)).replace("\\", "/"),
            "source_holdings_type": "holdings_true",
            "source_holdings_fingerprint": holdings_fingerprint,
            "source_opportunity_file": str(opportunities_path.relative_to(ROOT)).replace("\\", "/"),
            "source_opportunity_fingerprint": opportunity_fingerprint,
            "symbol_source_counts": {
                "holdings_true": len(holdings),
                "chain_opportunities": len(candidates),
                "combined_unique": len(combined),
            },
            "dispatch_rule_version": "VALUATION_MODEL_LIBRARY_V1",
            "fixed_stock_answer_written": False,
            "model_instance_index_source": "data/valuation/model_instances/*.json",
            "model_instance_index_count": len({str(p) for p in instance_index.values()}),
            "read_only": True,
        },
        "safety": {
            "read_only": True,
            "trade_context_created": False,
            "quote_context_created": False,
            "place_order_called": False,
            "published": False,
            "valuation_number_calculated": False,
            "fixed_target_list_used": False,
            "unknowns_are_forced_into_model": False,
        },
        "summary": {
            "model_distribution": dict(sorted(dist.items())),
            "status_distribution": dict(sorted(status_dist.items())),
            "unknown_count": len(unknown),
            "unknown_codes": [f"{r['code']} {r['name']}" for r in unknown],
        },
        "records": records,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Dispatch symbols to valuation model types without price or valuation calculation.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--symbols", default="")
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()] or None
    payload = build_dispatch(args.date, symbols)
    out_path = Path(args.out) if args.out else ROOT / "data" / "valuation" / f"valuation_dispatch_{args.date}.json"
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    write_json_utf8(out_path, payload)
    print(json.dumps({
        "output": str(out_path),
        "holdings_source": payload["fingerprint"]["source_holdings_file"],
        "model_distribution": payload["summary"]["model_distribution"],
        "status_distribution": payload["summary"]["status_distribution"],
        "unknown_codes": payload["summary"]["unknown_codes"],
        "fingerprint": payload["fingerprint"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
