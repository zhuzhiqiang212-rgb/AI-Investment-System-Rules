#!/usr/bin/env python3
"""
opportunity_chain_driven.py
TASK-2026-07-02-023

Chain-driven opportunity discovery.
- Reads daily evidence chain first.
- Uses Futu OpenD quote-side plate APIs and stock_filter only.
- No trade context, no order, no publish.
- Plate anchors define categories, not fixed stock answers.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"G:\我的云端硬盘\AI_Investment_System")
EVIDENCE_DIR = ROOT / "data" / "evidence_chain"
OUTPUT_DIR = ROOT / "data" / "opportunities"
HOST = "127.0.0.1"
PORT = 11111
JST = timezone(timedelta(hours=9))

MARKET_CONFIGS = {
    "US": {"price_min": 5, "avg_turnover_20d_min": 20_000_000, "change_20d_min": 2, "change_20d_max": 30},
    "HK": {"price_min": 1, "avg_turnover_20d_min": 20_000_000, "change_20d_min": 2, "change_20d_max": 35},
    "JP": {"price_min": 500, "avg_turnover_20d_min": 2_000_000_000, "change_20d_min": 2, "change_20d_max": 30},
}

NODE_DEFINITIONS = {
    "算力": {
        "strategy": ["AI"],
        "gate_scope": ["强", "中"],
        "markets": ["US"],
        "plate_anchors": ["AI芯片GPU", "半导体", "芯片", "人工智能"],
        "anchor_examples": ["英伟达", "AMD"],
        "logic": "general",
        "scope_note": "算力核心节点",
    },
    "半导体设备": {
        "strategy": ["AI"],
        "gate_scope": ["强", "中"],
        "markets": ["US", "JP"],
        "plate_anchors": ["半导体设备", "半导体", "设备"],
        "anchor_examples": ["爱德万", "东京电子", "AMAT"],
        "logic": "general",
        "scope_note": "设备核心节点",
    },
    "存储": {
        "strategy": ["AI"],
        "gate_scope": ["强"],
        "markets": ["US", "HK", "JP"],
        "plate_anchors": ["存储芯片", "存储", "记忆体", "半导体"],
        "anchor_examples": ["海力士", "三星", "美光"],
        "logic": "general",
        "scope_note": "总闸强时纳入",
    },
    "代工": {
        "strategy": ["AI"],
        "gate_scope": ["强", "中"],
        "markets": ["US", "HK"],
        "plate_anchors": ["晶圆代工", "代工", "半导体"],
        "anchor_examples": ["台积电"],
        "logic": "general",
        "scope_note": "代工核心节点",
    },
    "AI应用软件": {
        "strategy": ["AI"],
        "gate_scope": ["强"],
        "markets": ["US"],
        "plate_anchors": ["AI软件应用", "软件", "互联网内容与信息", "人工智能"],
        "anchor_examples": ["微软", "Meta", "Google"],
        "logic": "general",
        "scope_note": "总闸强时纳入",
    },
    "电力": {
        "strategy": ["AI", "能源"],
        "gate_scope": ["强", "中"],
        "markets": ["US", "JP", "HK"],
        "plate_anchors": ["电力核电", "电力", "核电", "公用事业"],
        "anchor_examples": ["维斯特拉", "Constellation"],
        "logic": "early",
        "scope_note": "电力为AI硬约束，AI或能源为战略指向时均激活，走提前埋伏逻辑（董事长TASK-024确认）",
    },
    "盟友链": {
        "strategy": ["AI"],
        "gate_scope": ["强"],
        "markets": ["JP"],
        "plate_anchors": ["日股半导体链", "半导体", "电子", "设备"],
        "anchor_examples": ["软银", "日韩半导体"],
        "logic": "general",
        "scope_note": "总闸强才纳入",
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


def records_from_frame(obj: Any) -> list[dict[str, Any]]:
    if obj is None:
        return []
    if hasattr(obj, "to_dict"):
        return [{str(k): json_safe(v) for k, v in row.items()} for row in obj.to_dict(orient="records")]
    if isinstance(obj, list):
        result = []
        for row in obj:
            if isinstance(row, dict):
                result.append({str(k): json_safe(v) for k, v in row.items()})
            else:
                result.append({"raw": json_safe(row)})
        return result
    return [{"raw": json_safe(obj)}]


def write_json_utf8(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8", newline="\n")
    reread = path.read_text(encoding="utf-8")
    if reread != text:
        raise RuntimeError(f"UTF-8 reread mismatch: {path}")
    if chr(63) in reread or chr(0xFFFD) in reread:
        raise RuntimeError(f"Garble marker found: {path}")


def load_evidence(date_text: str, demo: bool) -> tuple[dict[str, Any], str]:
    if demo:
        return {
            "date": date_text,
            "demo": True,
            "links": [
                {"node": "总闸·美联储是否美国优先", "evidence": "DEMO流程验证", "strength": "中", "direction": "是"},
                {"node": "战略指向·AI/安全/能源", "evidence": "DEMO流程验证", "strength": "中", "direction": "AI"},
            ],
            "derived": {
                "today_direction": "DEMO流程验证，战略指向AI",
                "opportunity_scope": "总闸中，收口径，只跑核心节点",
                "decision_constraint": "DEMO非正式机会池，不用于下单",
            },
        }, "DEMO_IN_MEMORY"

    path = EVIDENCE_DIR / f"daily_{date_text}.json"
    if not path.exists():
        raise FileNotFoundError(f"需先填当日求证表: {path}")
    return json.loads(path.read_text(encoding="utf-8")), str(path)


def extract_chain_state(evidence: dict[str, Any]) -> tuple[str, list[str]]:
    total_gate = "待填"
    strategies: list[str] = []
    for link in evidence.get("links", []):
        node = str(link.get("node", ""))
        strength = str(link.get("strength", ""))
        direction = str(link.get("direction", ""))
        if "总闸" in node and strength in ["强", "中", "弱", "证伪"]:
            total_gate = strength
        if "战略指向" in node:
            for item in ["AI", "安全", "能源"]:
                if item in direction and item not in strategies:
                    strategies.append(item)
    return total_gate, strategies


def active_nodes(total_gate: str, strategies: list[str]) -> list[str]:
    if total_gate in ["弱", "证伪"]:
        return []
    result = []
    for node, cfg in NODE_DEFINITIONS.items():
        if total_gate not in cfg["gate_scope"]:
            continue
        if any(strategy in strategies for strategy in cfg["strategy"]):
            result.append(node)
    return result


def scope_from_gate(total_gate: str) -> str:
    if total_gate == "强":
        return "节点全成分可进池"
    if total_gate == "中":
        return "收口径，只留核心板块与提前埋伏电力节点"
    if total_gate == "弱":
        return "不新增，只输出守现有核心"
    if total_gate == "证伪":
        return "停用战略供应链口径，切备用逻辑"
    return "待填"


def build_filters(cfg: dict[str, Any], logic: str):
    from futu import AccumulateFilter, CustomIndicatorFilter, KLType, RelativePosition, SimpleFilter, SortDir, StockField

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

    if logic == "general":
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
    else:
        change = AccumulateFilter()
        change.stock_field = StockField.CHANGE_RATE
        change.days = 20
        change.filter_min = -15
        change.filter_max = 20
        change.sort = SortDir.DESCEND
        change.is_no_filter = False
        filters.append(change)

        ma_filter = CustomIndicatorFilter()
        ma_filter.stock_field1 = StockField.PRICE
        ma_filter.stock_field2 = StockField.MA
        ma_filter.stock_field2_para = [200]
        ma_filter.relative_position = RelativePosition.MORE
        ma_filter.ktype = KLType.K_DAY
        ma_filter.is_no_filter = False
        filters.append(ma_filter)

    return filters


def raw_item_record(item: Any, node_class: str, market: str, plate: dict[str, Any], logic: str) -> dict[str, Any]:
    raw = dict(getattr(item, "__dict__", {}))
    cur_price = json_safe(raw.get("cur_price"))
    change_20d = json_safe(raw.get(("change_rate", 20)))
    turnover_20d = json_safe(raw.get(("turnover", 20)))
    ma20 = json_safe(raw.get(("ma", "20", "k_day")) or raw.get(("ma20", "k_day")))
    ma50 = json_safe(raw.get(("ma", "50", "k_day")))
    ma200 = json_safe(raw.get(("ma", "200", "k_day")))

    reason = "一般节点硬性关：价格站上MA20/MA50/MA200，过流动性门槛，20日涨跌幅处于合理强势区间"
    if logic == "early":
        reason = "提前埋伏逻辑：站稳MA200，过流动性门槛，处于底部或回调蓄势区，不要求20日已强势"

    return {
        "code": json_safe(raw.get("stock_code")),
        "name": json_safe(raw.get("stock_name")),
        "node_class": node_class,
        "market": market,
        "plate_code": plate.get("code"),
        "plate_name": plate.get("plate_name"),
        "hit_reason": reason,
        "technical": {
            "latest_price": cur_price,
            "change_20d_pct": change_20d,
            "turnover_20d": turnover_20d,
            "ma20": ma20,
            "ma50": ma50,
            "ma200": ma200,
            "logic": logic,
        },
    }


def market_enum(name: str):
    from futu import Market

    return getattr(Market, name)


def find_matching_plates(ctx: Any, market: str, anchors: list[str]) -> tuple[list[dict[str, Any]], str]:
    from futu import Plate, RET_OK

    ret, data = ctx.get_plate_list(market_enum(market), Plate.ALL)
    if ret != RET_OK:
        return [], str(data)
    plates = records_from_frame(data)
    matched = []
    for plate in plates:
        name = str(plate.get("plate_name", ""))
        if any(anchor.lower() in name.lower() for anchor in anchors):
            matched.append(plate)
    return matched[:3], ""


def filter_plate(ctx: Any, market: str, node_class: str, plate: dict[str, Any], logic: str) -> tuple[list[dict[str, Any]], str, int]:
    from futu import RET_OK

    plate_code = str(plate.get("code", ""))
    member_ret, member_data = ctx.get_plate_stock(plate_code)
    member_count = len(records_from_frame(member_data)) if member_ret == RET_OK else 0

    cfg = MARKET_CONFIGS.get(market)
    if cfg is None:
        return [], "市场参数待补", member_count

    ret, data = ctx.get_stock_filter(market_enum(market), filter_list=build_filters(cfg, logic), plate_code=plate_code, begin=0, num=30)
    if ret != RET_OK:
        return [], str(data), member_count

    if isinstance(data, tuple) and len(data) >= 3:
        items = data[2]
    elif isinstance(data, tuple) and len(data) >= 2:
        items = data[1]
    else:
        items = data
    records = [raw_item_record(item, node_class, market, plate, logic) for item in list(items or [])]
    return records, "", member_count


def run_discovery(evidence: dict[str, Any], evidence_source: str, date_text: str, demo: bool) -> dict[str, Any]:
    from futu import OpenQuoteContext

    total_gate, strategies = extract_chain_state(evidence)
    nodes = active_nodes(total_gate, strategies)
    scope = scope_from_gate(total_gate)

    output: dict[str, Any] = {
        "task_id": "TASK-2026-07-02-023",
        "mode": "DEMO_FLOW_VALIDATION_NOT_FORMAL_POOL" if demo else "FORMAL_READ_ONLY_PRESCREEN",
        "generated_at": now_jst(),
        "date": date_text,
        "evidence_source": evidence_source,
        "fingerprint": {
            "total_gate": total_gate,
            "strategic_directions": strategies,
            "activated_node_classes": nodes,
            "scope": scope,
            "leader_cap_applied": total_gate == "中",
            "per_node_cap": 10 if total_gate == "中" else None,
            "demo": demo,
            "derivation_reason": evidence.get("derived", {}),
        },
        "safety": {
            "quote_context_only": True,
            "trade_context_created": False,
            "place_order_called": False,
            "published": False,
            "fixed_stock_answer_written": False,
        },
        "node_results": {},
        "candidates": [],
        "blocked_reason": "",
    }

    if total_gate == "弱":
        output["blocked_reason"] = "总闸弱，不新增，只输出守现有核心"
        return output
    if total_gate == "证伪":
        output["blocked_reason"] = "总闸证伪，停用战略供应链口径，切备用逻辑"
        return output

    ctx = OpenQuoteContext(host=HOST, port=PORT)
    try:
        for node in nodes:
            cfg = NODE_DEFINITIONS[node]
            node_entry = {
                "node_class": node,
                "logic": cfg["logic"],
                "scope_note": cfg["scope_note"],
                "plate_anchors": cfg["plate_anchors"],
                "anchor_examples_not_candidates": cfg["anchor_examples"],
                "markets": {},
                "hit_count": 0,
            }
            node_candidates: list[dict[str, Any]] = []
            for market in cfg["markets"]:
                plates, plate_error = find_matching_plates(ctx, market, cfg["plate_anchors"])
                market_entry = {
                    "matched_plates": plates,
                    "plate_error": plate_error,
                    "member_counts": {},
                    "errors": [],
                    "candidates": [],
                }
                for plate in plates:
                    records, err, member_count = filter_plate(ctx, market, node, plate, cfg["logic"])
                    market_entry["member_counts"][str(plate.get("code"))] = member_count
                    if err:
                        market_entry["errors"].append({"plate": plate, "error": err})
                    market_entry["candidates"].extend(records)
                node_candidates.extend(market_entry["candidates"])
                node_entry["markets"][market] = market_entry
            node_candidates.sort(
                key=lambda item: float(item.get("technical", {}).get("turnover_20d") or 0),
                reverse=True,
            )
            deduped_candidates = []
            seen_codes = set()
            for item in node_candidates:
                code = str(item.get("code"))
                if code in seen_codes:
                    continue
                seen_codes.add(code)
                deduped_candidates.append(item)
            node_candidates = deduped_candidates
            if total_gate == "中":
                node_candidates = node_candidates[:10]
                kept_codes = {str(item.get("code")) for item in node_candidates}
                for market_entry in node_entry["markets"].values():
                    market_entry["candidates_before_leader_cap"] = len(market_entry["candidates"])
                    market_entry["candidates"] = [
                        item for item in market_entry["candidates"]
                        if str(item.get("code")) in kept_codes
                    ]
            node_entry["hit_count"] = len(node_candidates)
            output["candidates"].extend(node_candidates)
            output["node_results"][node] = node_entry
    finally:
        ctx.close()

    output["fingerprint"]["hit_counts_by_node"] = {
        node: info["hit_count"] for node, info in output["node_results"].items()
    }
    return output


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Chain-driven opportunity discovery, read only.")
    parser.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d"))
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    try:
        evidence, source = load_evidence(args.date, args.demo)
    except FileNotFoundError as exc:
        print(str(exc))
        return 2

    result = run_discovery(evidence, source, args.date, args.demo)
    suffix = f"{args.date}_DEMO" if args.demo else args.date
    output_path = OUTPUT_DIR / f"chain_opportunities_{suffix}.json"
    write_json_utf8(output_path, result)

    print(f"OUTPUT_PATH={output_path}")
    print(f"MODE={result['mode']}")
    print(f"TOTAL_GATE={result['fingerprint']['total_gate']}")
    print(f"ACTIVE_NODES={','.join(result['fingerprint']['activated_node_classes'])}")
    print(f"SCOPE={result['fingerprint']['scope']}")
    print(f"CANDIDATES={len(result['candidates'])}")
    for node, count in result["fingerprint"].get("hit_counts_by_node", {}).items():
        print(f"NODE={node} COUNT={count}")
    for item in result["candidates"][:5]:
        tech = item.get("technical", {})
        print(
            f"SAMPLE={item.get('code')} {item.get('name')} "
            f"NODE={item.get('node_class')} PLATE={item.get('plate_name')} "
            f"PX={tech.get('latest_price')} CHG20={tech.get('change_20d_pct')} "
            f"MA20={tech.get('ma20')} MA50={tech.get('ma50')} MA200={tech.get('ma200')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
