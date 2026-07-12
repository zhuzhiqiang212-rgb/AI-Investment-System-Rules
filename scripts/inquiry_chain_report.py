from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find_link(evidence: dict[str, Any], keywords: list[str]) -> dict[str, Any]:
    for link in evidence.get("links", []):
        node = str(link.get("node", ""))
        if any(keyword in node for keyword in keywords):
            return {
                "node": node,
                "evidence": link.get("evidence", "该环待填"),
                "strength": link.get("strength", "该环待填"),
                "direction": link.get("direction", "该环待填"),
            }
    return {
        "node": "该环待填",
        "evidence": "该环待填",
        "strength": "该环待填",
        "direction": "该环待填",
    }


def format_money(value: Any, currency: str | None) -> str:
    if value is None:
        return "待补"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    suffix = f" {currency}" if currency else ""
    return f"{number:,.2f}{suffix}"


def decide_action(review: dict[str, Any]) -> str:
    verdict = str(review.get("verdict", "待补"))
    quote_status = str(review.get("quote_status", ""))
    quantity_status = str(review.get("quantity_status", ""))
    if quote_status == "FAIL" or "待补" in quantity_status:
        return "等"
    if verdict == "符合":
        return "守"
    if verdict == "不符合":
        return "等"
    return "等"


def price_line(review: dict[str, Any]) -> str:
    price = format_money(review.get("realtime_price"), review.get("currency_hint"))
    used_field = review.get("used_field") or "字段待补"
    time_bits = [str(review.get("data_date") or ""), str(review.get("data_time") or "")]
    stamp = " ".join(bit for bit in time_bits if bit).strip() or "时间待补"
    return f"现价={price}，字段={used_field}，时间={stamp}"


def build_chain(review: dict[str, Any], links: dict[str, dict[str, Any]]) -> dict[str, Any]:
    action = decide_action(review)
    verdict = review.get("verdict", "待补")
    nodes = review.get("matched_node_classes") or []
    node_text = "、".join(nodes) if nodes else "未匹配今日激活节点"

    flow = links["flow"]
    strategy = links["strategy"]
    fed = links["fed"]
    world = links["world"]

    return {
        "symbol": review.get("symbol"),
        "name": review.get("name"),
        "action": action,
        "verdict": verdict,
        "price": review.get("realtime_price"),
        "price_field": review.get("used_field"),
        "data_time": " ".join(
            bit for bit in [str(review.get("data_date") or ""), str(review.get("data_time") or "")] if bit
        ),
        "steps": [
            {
                "step_no": 1,
                "step_name": "该怎么办",
                "source": "holdings_review",
                "text": f"持仓判定={verdict}，匹配节点={node_text}，{price_line(review)}，动作={action}。",
            },
            {
                "step_no": 2,
                "step_name": "为什么",
                "source": flow["node"],
                "text": f"{flow['node']}：力度={flow['strength']}，方向={flow['direction']}，证据={flow['evidence']}。",
            },
            {
                "step_no": 3,
                "step_name": "再为什么",
                "source": strategy["node"],
                "text": f"{strategy['node']}：力度={strategy['strength']}，方向={strategy['direction']}，证据={strategy['evidence']}。",
            },
            {
                "step_no": 4,
                "step_name": "再为什么",
                "source": fed["node"],
                "text": f"{fed['node']}：力度={fed['strength']}，方向={fed['direction']}，证据={fed['evidence']}。",
            },
            {
                "step_no": 5,
                "step_name": "追到头",
                "source": world["node"],
                "text": f"{world['node']}：力度={world['strength']}，方向={world['direction']}，证据={world['evidence']}。",
            },
            {
                "step_no": 6,
                "step_name": "闭环",
                "source": "worldview_to_holding",
                "text": (
                    f"世界观方向={world['direction']}，总闸方向={fed['direction']}，战略方向={strategy['direction']}，"
                    f"持仓判定={verdict}，回到动作={action}。"
                ),
            },
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build inquiry chain from daily evidence and holdings review")
    parser.add_argument("--date", default="20260702")
    parser.add_argument("--symbols", nargs="*", default=["US.NVDA", "JP.6857"])
    args = parser.parse_args()

    evidence_path = ROOT / "data" / "evidence_chain" / f"daily_{args.date}.json"
    holdings_path = ROOT / "data" / "holdings" / f"holdings_review_{args.date}.json"
    output_path = ROOT / "data" / "reports" / f"inquiry_chain_{args.date}.json"

    if not evidence_path.exists():
        print(f"需先填当日求证表: {evidence_path}")
        return 2
    if not holdings_path.exists():
        print(f"需先生成持仓审查: {holdings_path}")
        return 2

    evidence = read_json(evidence_path)
    holdings = read_json(holdings_path)
    reviews = holdings.get("reviews", [])

    links = {
        "world": find_link(evidence, ["总命题", "世界"]),
        "fed": find_link(evidence, ["总闸", "美联储"]),
        "strategy": find_link(evidence, ["战略指向"]),
        "flow": find_link(evidence, ["资金轮动"]),
    }

    by_symbol = {item.get("symbol"): item for item in reviews}
    chains = []
    missing = []
    for symbol in args.symbols:
        review = by_symbol.get(symbol)
        if not review:
            missing.append(symbol)
            continue
        chains.append(build_chain(review, links))

    output = {
        "task_id": "TASK-2026-07-02-063",
        "mode": "formal",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fingerprint": {
            "date": args.date,
            "evidence_source": str(evidence_path),
            "holdings_source": str(holdings_path),
            "target_symbols": args.symbols,
            "framework_fixed": True,
            "answers_from_daily_inputs": True,
            "fixed_answer_written": False,
        },
        "source_links": links,
        "missing_symbols": missing,
        "chains": chains,
    }
    write_json(output_path, output)
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
