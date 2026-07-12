from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RULE_SOURCE = "00_请先看这里/PDCA记分规则准绳.html"

RINGS = [
    {"id": "worldview", "name": "世界观", "keywords": ["总命题", "世界"]},
    {"id": "fed_gate", "name": "总闸", "keywords": ["总闸", "美联储"]},
    {"id": "strategy", "name": "战略", "keywords": ["战略指向"]},
    {"id": "capital_flow", "name": "资金轮动", "keywords": ["资金轮动"]},
    {"id": "sector_rotation", "name": "板块轮动", "keywords": ["板块轮动"]},
]

STRENGTH_RANK = {"证伪": 0, "弱": 1, "中": 2, "强": 3, "高": 3}
CERTAINTY_UP = {"证伪": "弱", "弱": "中", "中": "高", "高": "高"}
CERTAINTY_DOWN = {"高": "中", "中": "弱", "弱": "证伪", "证伪": "证伪"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def previous_date(date: str) -> str:
    from datetime import datetime, timedelta

    dt = datetime.strptime(date, "%Y%m%d")
    return (dt - timedelta(days=1)).strftime("%Y%m%d")


def find_ring_link(daily: dict[str, Any], ring: dict[str, Any]) -> dict[str, Any]:
    for link in daily.get("links", []):
        node = str(link.get("node", ""))
        if any(keyword in node for keyword in ring["keywords"]):
            return link
    return {
        "node": ring["name"],
        "evidence": "该环待填",
        "strength": "弱",
        "direction": "待填",
    }


def strength_rank(value: Any) -> int:
    return STRENGTH_RANK.get(str(value), 1)


def direction_reversed(prev: dict[str, Any] | None, cur: dict[str, Any]) -> bool:
    if str(cur.get("strength")) == "证伪":
        return True
    if not prev:
        return False
    prev_direction = str(prev.get("direction", ""))
    cur_direction = str(cur.get("direction", ""))
    if prev_direction and cur_direction and prev_direction != cur_direction:
        return True
    return False


def score_ring(prev: dict[str, Any] | None, cur: dict[str, Any]) -> tuple[int, str]:
    if not prev:
        return 0, "建立首日，先记基准"
    if direction_reversed(prev, cur):
        return -1, "方向反转或证伪"
    prev_rank = strength_rank(prev.get("strength"))
    cur_rank = strength_rank(cur.get("strength"))
    if cur_rank < prev_rank:
        return -1, "力度转弱"
    same_evidence = str(prev.get("evidence", "")) == str(cur.get("evidence", ""))
    same_strength = str(prev.get("strength", "")) == str(cur.get("strength", ""))
    same_direction = str(prev.get("direction", "")) == str(cur.get("direction", ""))
    if same_evidence and same_strength and same_direction:
        return 0, "无实质变化"
    if cur_rank >= prev_rank and same_direction:
        return 1, "维持或增强且方向一致"
    return 0, "中性"


def apply_certainty(card: dict[str, Any], score: int) -> tuple[str, str]:
    before = str(card.get("current_certainty") or card.get("initial_strength") or "弱")
    if score > 0:
        card["support_streak"] = int(card.get("support_streak", 0)) + 1
        card["hit_streak"] = 0
        after = CERTAINTY_UP.get(before, before)
        event = f"支持，确定性 {before}→{after}"
    elif score < 0:
        card["hit_streak"] = int(card.get("hit_streak", 0)) + 1
        card["support_streak"] = 0
        after = CERTAINTY_DOWN.get(before, before)
        event = f"打脸，确定性 {before}→{after}"
    else:
        card["support_streak"] = 0
        card["hit_streak"] = 0
        after = before
        event = f"中性，确定性维持 {after}"
    card["current_certainty"] = after
    return after, event


def decision_quality(cards: list[dict[str, Any]]) -> dict[str, str]:
    certs = [str(card.get("current_certainty", "弱")) for card in cards]
    by_id = {str(card.get("ring_id")): str(card.get("current_certainty", "弱")) for card in cards}
    gate_certainty = by_id.get("fed_gate", "弱")
    if gate_certainty in {"弱", "证伪"}:
        return {"level": "低", "reason": "总闸确定性降为弱或证伪，机会池必须收口径"}
    if "证伪" in certs or certs.count("弱") >= 2:
        return {"level": "低", "reason": "关键环节确定性弱或证伪，机会池应收口径"}
    if certs.count("高") >= 3 and "弱" not in certs:
        return {"level": "高", "reason": "多数关键环节高确定性，可按纪律放大口径"}
    return {"level": "中", "reason": "关键环节未证伪但确定性未全高，维持谨慎口径"}


def build(date: str) -> dict[str, Any]:
    daily_path = ROOT / "data" / "evidence_chain" / f"daily_{date}.json"
    prev_path = ROOT / "data" / "evidence_chain" / f"daily_{previous_date(date)}.json"
    scorecards_path = ROOT / "data" / "pdca" / "scorecards.json"
    if not daily_path.exists():
        print(f"需先填当日求证表: {daily_path}")
        raise SystemExit(2)

    daily = read_json(daily_path)
    prev_daily = read_json(prev_path) if prev_path.exists() else None
    scorecards = read_json(scorecards_path) if scorecards_path.exists() else {"cards": {}, "history": []}
    existing_history = None
    for record in scorecards.get("history", []):
        if record.get("date") == date:
            existing_history = record
            break
    existing_scores = existing_history.get("scores", {}) if existing_history else {}

    today_cards = []
    for ring in RINGS:
        cur = find_ring_link(daily, ring)
        prev = find_ring_link(prev_daily, ring) if prev_daily else None
        card = scorecards.setdefault("cards", {}).get(ring["id"], {})
        if not card:
            card = {
                "ring_id": ring["id"],
                "ring_name": ring["name"],
                "judgment": cur.get("direction", "待填"),
                "created_at": date,
                "initial_strength": cur.get("strength", "弱"),
                "cumulative_score": 0,
                "current_certainty": cur.get("strength", "弱"),
                "support_streak": 0,
                "hit_streak": 0,
            }
        score, reason = score_ring(prev, cur)
        before_certainty = card.get("current_certainty", "弱")
        card["judgment"] = cur.get("direction", card.get("judgment", "待填"))
        card["last_strength"] = cur.get("strength", "弱")
        card["last_evidence"] = cur.get("evidence", "")
        previous_same_day_score = int(existing_scores.get(ring["id"], 0))
        card["cumulative_score"] = int(card.get("cumulative_score", 0)) - previous_same_day_score + score
        after_certainty, event = apply_certainty(card, score)
        scorecards["cards"][ring["id"]] = card
        today_cards.append({
            "ring_id": ring["id"],
            "ring_name": ring["name"],
            "node": cur.get("node", ring["name"]),
            "judgment": cur.get("direction", "待填"),
            "evidence": cur.get("evidence", "该环待填"),
            "strength": cur.get("strength", "弱"),
            "previous_strength": prev.get("strength") if prev else None,
            "previous_direction": prev.get("direction") if prev else None,
            "daily_score": score,
            "score_reason": reason,
            "cumulative_score": card["cumulative_score"],
            "certainty_before": before_certainty,
            "current_certainty": after_certainty,
            "certainty_event": event,
        })

    quality = decision_quality(today_cards)
    daily_output = {
        "task_id": "TASK-2026-07-03-068",
        "mode": "formal",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fingerprint": {
            "date": date,
            "framework_fixed": True,
            "answers_from_daily": True,
            "rule_source": RULE_SOURCE,
            "daily_source": str(daily_path),
            "previous_daily_source": str(prev_path) if prev_path.exists() else None,
            "scorecards_source": str(scorecards_path),
        },
        "rings": today_cards,
        "decision_quality": quality,
    }
    scorecards["updated_at"] = datetime.now(timezone.utc).isoformat()
    scorecards["rule_source"] = RULE_SOURCE
    scorecards["history"] = [record for record in scorecards.get("history", []) if record.get("date") != date]
    scorecards.setdefault("history", []).append({
        "date": date,
        "decision_quality": quality,
        "scores": {card["ring_id"]: card["daily_score"] for card in today_cards},
    })
    write_json(scorecards_path, scorecards)
    write_json(ROOT / "data" / "pdca" / f"pdca_daily_{date}.json", daily_output)
    return daily_output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build daily PDCA scorecard from evidence chain")
    parser.add_argument("--date", default=None)
    args = parser.parse_args()
    date = args.date or datetime.now().strftime("%Y%m%d")
    output = build(date)
    print(json.dumps({
        "date": date,
        "decision_quality": output["decision_quality"],
        "ring_scores": {ring["ring_name"]: ring["daily_score"] for ring in output["rings"]},
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
