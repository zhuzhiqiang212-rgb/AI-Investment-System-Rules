from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RULE_SOURCE = "00_请先看这里/PDCA记分规则准绳.html"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def daily_files() -> list[Path]:
    return sorted((ROOT / "data" / "pdca").glob("pdca_daily_*.json"))


def date_from_daily(path: Path) -> str:
    return path.stem.replace("pdca_daily_", "")


def load_daily_all() -> list[dict[str, Any]]:
    items = []
    for path in daily_files():
        data = read_json(path)
        data["_date"] = date_from_daily(path)
        items.append(data)
    return items


def scale_window(days: int, daily_all: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    selected = daily_all[-days:]
    if len(selected) < days:
        return selected, f"待累积{days - len(selected)}天"
    return selected, "已具备"


def summarize_window(days: int, daily_all: list[dict[str, Any]]) -> dict[str, Any]:
    selected, status = scale_window(days, daily_all)
    ring_scores: dict[str, int] = {}
    certainty_events: list[dict[str, str]] = []
    for day in selected:
        for ring in day.get("rings", []):
            rid = ring.get("ring_id")
            ring_scores[rid] = ring_scores.get(rid, 0) + int(ring.get("daily_score", 0))
            event = str(ring.get("certainty_event", ""))
            if "→" in event:
                certainty_events.append({
                    "date": day.get("_date", ""),
                    "ring_name": ring.get("ring_name", ""),
                    "event": event,
                })
    solidifying = [rid for rid, score in ring_scores.items() if score > 0]
    shaking = [rid for rid, score in ring_scores.items() if score < 0]
    return {
        "status": status,
        "days_available": len(selected),
        "ring_scores": ring_scores,
        "solidifying": solidifying,
        "shaking": shaking,
        "certainty_events": certainty_events,
    }


def self_reflection_frame(scale: str, status: str) -> dict[str, str]:
    return {
        "scale": scale,
        "status": status,
        "判断方法": "待复盘填写：这一环用哪些指标形成判断，是否抓对关键",
        "打分规则": "待复盘填写：什么算支持或证伪，标准是否合理",
        "确定性阈值": "待复盘填写：升降级阈值是否太松或太紧",
        "规则迭代": "待复盘填写：若改规则，记录为什么改与生效日期",
    }


def build_trajectories(scorecards: dict[str, Any], daily_all: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards = scorecards.get("cards", {})
    result = []
    for ring_id, card in cards.items():
        series = []
        running = 0
        for day in daily_all:
            for ring in day.get("rings", []):
                if ring.get("ring_id") == ring_id:
                    running += int(ring.get("daily_score", 0))
                    series.append({
                        "date": day.get("_date"),
                        "daily_score": ring.get("daily_score"),
                        "running_score": running,
                        "certainty_before": ring.get("certainty_before"),
                        "current_certainty": ring.get("current_certainty"),
                        "certainty_event": ring.get("certainty_event"),
                    })
        result.append({
            "ring_id": ring_id,
            "ring_name": card.get("ring_name", ring_id),
            "judgment": card.get("judgment", "待填"),
            "created_at": card.get("created_at", ""),
            "cumulative_score": card.get("cumulative_score", 0),
            "current_certainty": card.get("current_certainty", "待填"),
            "daily_score_series": series,
            "certainty_path_text": " → ".join(str(item.get("current_certainty")) for item in series) if series else "待累积",
        })
    return result


def build(date: str) -> dict[str, Any]:
    scorecards_path = ROOT / "data" / "pdca" / "scorecards.json"
    if not scorecards_path.exists():
        print(f"需先跑PDCA记分卡: {scorecards_path}")
        raise SystemExit(2)
    scorecards = read_json(scorecards_path)
    daily_all = load_daily_all()
    target_path = ROOT / "data" / "pdca" / f"pdca_daily_{date}.json"
    if not target_path.exists():
        print(f"需先生成当日PDCA: {target_path}")
        raise SystemExit(2)
    target_daily = read_json(target_path)
    target_daily["_date"] = date

    review = {
        "task_id": "TASK-2026-07-03-069",
        "mode": "formal",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fingerprint": {
            "date": date,
            "framework_fixed": True,
            "answers_from_pdca_data": True,
            "rule_source": RULE_SOURCE,
            "scorecards_source": str(scorecards_path),
            "daily_file_count": len(daily_all),
        },
        "today_decision_quality": target_daily.get("decision_quality", {}),
        "certainty_trajectories": build_trajectories(scorecards, daily_all),
        "multi_scale": {
            "daily": {
                "status": "已具备",
                "date": date,
                "rings": target_daily.get("rings", []),
                "decision_quality": target_daily.get("decision_quality", {}),
            },
            "weekly": summarize_window(7, daily_all),
            "monthly": {
                "summary": summarize_window(30, daily_all),
                "second_layer_self_reflection": self_reflection_frame("月", "待累积"),
            },
            "quarterly": {
                "summary": summarize_window(90, daily_all),
                "second_layer_self_reflection": self_reflection_frame("季", "待累积"),
            },
            "yearly": {
                "summary": summarize_window(365, daily_all),
                "second_layer_self_reflection": self_reflection_frame("年", "待累积"),
            },
        },
    }
    output_path = ROOT / "data" / "pdca" / f"pdca_review_{date}.json"
    write_json(output_path, review)
    return review


def main() -> int:
    parser = argparse.ArgumentParser(description="Build PDCA multi scale review")
    parser.add_argument("--date", default=None)
    args = parser.parse_args()
    date = args.date or datetime.now().strftime("%Y%m%d")
    review = build(date)
    print(json.dumps({
        "date": date,
        "decision_quality": review.get("today_decision_quality"),
        "trajectory_count": len(review.get("certainty_trajectories", [])),
        "weekly_status": review.get("multi_scale", {}).get("weekly", {}).get("status"),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
