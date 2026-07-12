#!/usr/bin/env python3
"""
daily_upper_from_chain.py
TASK-2026-07-02-025

Mechanical mapping from daily evidence chain to daily report layers 1-7.
- Reads evidence chain first.
- Copies evidence fields only, no invented prose.
- No order, no publish.
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
OUTPUT_DIR = ROOT / "data" / "reports"
JST = timezone(timedelta(hours=9))

NODE_DEFINITIONS = {
    "算力": {"strategy": ["AI"], "gate_scope": ["强", "中"]},
    "半导体设备": {"strategy": ["AI"], "gate_scope": ["强", "中"]},
    "存储": {"strategy": ["AI"], "gate_scope": ["强"]},
    "代工": {"strategy": ["AI"], "gate_scope": ["强", "中"]},
    "AI应用软件": {"strategy": ["AI"], "gate_scope": ["强"]},
    "电力": {"strategy": ["AI", "能源"], "gate_scope": ["强", "中"]},
    "盟友链": {"strategy": ["AI"], "gate_scope": ["强"]},
}


def now_jst() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


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
                {"node": "总命题·世界是否真变", "evidence": "DEMO流程验证", "strength": "中", "direction": "变"},
                {"node": "总闸·美联储是否美国优先", "evidence": "DEMO流程验证", "strength": "中", "direction": "是"},
                {"node": "战略指向·AI/安全/能源", "evidence": "DEMO流程验证", "strength": "中", "direction": "AI"},
                {"node": "手段层·FIMA/稳定币/加密", "evidence": "DEMO流程验证", "strength": "中", "direction": "通"},
                {"node": "资金轮动", "evidence": "DEMO流程验证", "strength": "中", "direction": "AI"},
                {"node": "板块轮动", "evidence": "DEMO流程验证", "strength": "中", "direction": "半导体设备/算力/代工/电力"},
            ],
            "derived": {
                "today_direction": "DEMO流程验证，战略指向AI",
                "opportunity_scope": "总闸中，收口径，只跑核心节点",
                "decision_constraint": "DEMO非正式日报上半截，不用于下单",
            },
        }, "DEMO_IN_MEMORY"
    path = EVIDENCE_DIR / f"daily_{date_text}.json"
    if not path.exists():
        raise FileNotFoundError(f"需先填当日求证表: {path}")
    return json.loads(path.read_text(encoding="utf-8")), str(path)


def find_link(evidence: dict[str, Any], keyword: str) -> dict[str, Any] | None:
    for link in evidence.get("links", []):
        if keyword in str(link.get("node", "")):
            return link
    return None


def normalize_link(link: dict[str, Any] | None, source_name: str) -> dict[str, str]:
    if not link:
        return {
            "source_link": source_name,
            "evidence": "该环待填",
            "strength": "该环待填",
            "direction": "该环待填",
        }
    return {
        "source_link": str(link.get("node") or source_name),
        "evidence": str(link.get("evidence") or "该环待填"),
        "strength": str(link.get("strength") or "该环待填"),
        "direction": str(link.get("direction") or "该环待填"),
    }


def combine_links(parts: list[dict[str, str]], source_name: str) -> dict[str, str]:
    return {
        "source_link": source_name,
        "evidence": "；".join(part["evidence"] for part in parts) if parts else "该环待填",
        "strength": " / ".join(part["strength"] for part in parts) if parts else "该环待填",
        "direction": " / ".join(part["direction"] for part in parts) if parts else "该环待填",
    }


def extract_chain_state(evidence: dict[str, Any]) -> tuple[str, list[str]]:
    total_gate = "该环待填"
    strategies: list[str] = []
    gate = find_link(evidence, "总闸")
    if gate and str(gate.get("strength", "")) in ["强", "中", "弱", "证伪"]:
        total_gate = str(gate.get("strength"))
    strategy = find_link(evidence, "战略指向")
    if strategy:
        direction = str(strategy.get("direction", ""))
        for item in ["AI", "安全", "能源"]:
            if item in direction:
                strategies.append(item)
    return total_gate, strategies


def active_nodes(total_gate: str, strategies: list[str]) -> list[str]:
    if total_gate in ["弱", "证伪", "该环待填"]:
        return []
    result = []
    for node, cfg in NODE_DEFINITIONS.items():
        if total_gate not in cfg["gate_scope"]:
            continue
        if any(strategy in strategies for strategy in cfg["strategy"]):
            result.append(node)
    return result


def layer(no: int, name: str, mapped: dict[str, str], downstream: str) -> dict[str, Any]:
    return {
        "layer_no": no,
        "layer_name": name,
        "source_link": mapped["source_link"],
        "evidence": mapped["evidence"],
        "strength": mapped["strength"],
        "direction": mapped["direction"],
        "downstream": downstream,
    }


def build_layers(evidence: dict[str, Any], active_node_list: list[str]) -> list[dict[str, Any]]:
    total = normalize_link(find_link(evidence, "总命题"), "总命题·世界是否真变")
    gate = normalize_link(find_link(evidence, "总闸"), "总闸·美联储是否美国优先")
    strategy = normalize_link(find_link(evidence, "战略指向"), "战略指向·AI/安全/能源")
    tool = normalize_link(find_link(evidence, "手段层"), "手段层·FIMA/稳定币/加密")
    flow = normalize_link(find_link(evidence, "资金轮动"), "资金轮动")
    sector = normalize_link(find_link(evidence, "板块轮动"), "板块轮动")
    industry = {
        "source_link": "激活节点类",
        "evidence": "、".join(active_node_list) if active_node_list else "该环待填",
        "strength": gate["strength"],
        "direction": "、".join(active_node_list) if active_node_list else "该环待填",
    }
    return [
        layer(1, "今天世界发生了什么", combine_links([total, gate], "总命题+总闸"), "固定模板：由总命题与总闸决定世界观读数。"),
        layer(2, "宏观", combine_links([gate, tool], "总闸+手段层"), "固定模板：由总闸与手段层决定宏观约束。"),
        layer(3, "战略", strategy, "固定模板：由战略指向决定今日战略主线。"),
        layer(4, "流动性", combine_links([tool, gate], "手段层+总闸"), "固定模板：由手段层与总闸决定流动性口径。"),
        layer(5, "资金轮动", flow, "固定模板：由资金轮动环决定资金方向。"),
        layer(6, "板块轮动", sector, "固定模板：由板块轮动环决定承接板块。"),
        layer(7, "行业", industry, "固定模板：由激活节点类列出行业节点。"),
    ]


def build_output(evidence: dict[str, Any], source: str, date_text: str, demo: bool) -> dict[str, Any]:
    total_gate, strategies = extract_chain_state(evidence)
    nodes = active_nodes(total_gate, strategies)
    return {
        "task_id": "TASK-2026-07-02-025",
        "mode": "DEMO_NOT_FORMAL_DAILY_UPPER" if demo else "FORMAL_DAILY_UPPER_FROM_CHAIN",
        "generated_at": now_jst(),
        "fingerprint": {
            "evidence_source": source,
            "total_gate": total_gate,
            "strategic_directions": strategies,
            "activated_node_classes": nodes,
            "generated_at": now_jst(),
            "mode": "DEMO_NOT_FORMAL_DAILY_UPPER" if demo else "FORMAL_DAILY_UPPER_FROM_CHAIN",
        },
        "safety": {
            "read_only": True,
            "place_order_called": False,
            "published": False,
            "invented_evidence": False,
        },
        "layers": build_layers(evidence, nodes),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Generate daily report upper 7 layers from evidence chain.")
    parser.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d"))
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    try:
        evidence, source = load_evidence(args.date, args.demo)
    except FileNotFoundError as exc:
        print(str(exc))
        return 2

    output = build_output(evidence, source, args.date, args.demo)
    suffix = f"{args.date}_DEMO" if args.demo else args.date
    output_path = OUTPUT_DIR / f"daily_upper_{suffix}.json"
    write_json_utf8(output_path, output)

    print(f"OUTPUT_PATH={output_path}")
    print(f"MODE={output['mode']}")
    print(f"TOTAL_GATE={output['fingerprint']['total_gate']}")
    print(f"STRATEGIC_DIRECTIONS={','.join(output['fingerprint']['strategic_directions'])}")
    print(f"ACTIVE_NODES={','.join(output['fingerprint']['activated_node_classes'])}")
    for item in output["layers"]:
        print(
            f"LAYER={item['layer_no']} {item['layer_name']} "
            f"SOURCE={item['source_link']} STRENGTH={item['strength']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
