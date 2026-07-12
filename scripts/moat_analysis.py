from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RULE_SOURCE = "00_请先看这里/护城河分析框架.html"
DIMENSIONS = ["品牌", "网络效应", "成本优势", "转换成本", "专利技术"]
DIMENSION_SCORE = {"宽": 2, "窄": 1, "无": 0}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def moat_grade(total: int | None) -> str:
    if total is None:
        return "待补护城河"
    if total >= 7:
        return "宽护城河"
    if total >= 4:
        return "窄护城河"
    return "无护城河"


def normalize_dimension(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        level = value.get("level") or value.get("档") or value.get("score_label") or value.get("label")
        basis = value.get("basis") or value.get("依据") or value.get("reason") or ""
    else:
        level = value
        basis = ""
    if isinstance(level, (int, float)):
        score = int(level)
        label = "宽" if score >= 2 else "窄" if score == 1 else "无"
    else:
        label = str(level) if level is not None else "待补"
        score = DIMENSION_SCORE.get(label)
    return {"label": label, "score": score, "basis": basis}


def normalize_instance(data: dict[str, Any], source_file: str) -> dict[str, Any]:
    dimensions_raw = data.get("dimensions") or data.get("五维") or {}
    dimensions = {}
    missing = []
    total = 0
    complete = True
    for name in DIMENSIONS:
        dim = normalize_dimension(dimensions_raw.get(name))
        dimensions[name] = dim
        if dim["score"] is None:
            complete = False
            missing.append(name)
        else:
            total += int(dim["score"])
    total_score = total if complete else None
    return {
        "symbol": data.get("symbol") or data.get("code"),
        "name": data.get("name", ""),
        "dimensions": dimensions,
        "total_score": total_score,
        "moat_grade": data.get("moat_grade") or data.get("护城河档") or moat_grade(total_score),
        "confidence": data.get("confidence") or data.get("置信度") or "待补",
        "basis": data.get("basis") or data.get("依据") or "",
        "missing_dimensions": missing,
        "source_file": source_file,
        "status": "OK" if complete else "待理解岗打分",
    }


def load_instances() -> dict[str, dict[str, Any]]:
    inst_dir = ROOT / "data" / "moat" / "moat_instances"
    inst_dir.mkdir(parents=True, exist_ok=True)
    result = {}
    for path in sorted(inst_dir.glob("*.json")):
        data = read_json(path)
        item = normalize_instance(data, path.name)
        symbol = item.get("symbol")
        if symbol:
            result[str(symbol)] = item
    return result


def symbols_from_sources(date: str) -> list[dict[str, str]]:
    seen: dict[str, str] = {}
    holdings_path = ROOT / "data" / "holdings" / f"holdings_review_{date}.json"
    if holdings_path.exists():
        holdings = read_json(holdings_path)
        for item in holdings.get("reviews", []):
            code = item.get("symbol")
            if code:
                seen[str(code)] = item.get("name", "")
    dual_path = ROOT / "data" / "opportunities" / f"dual_channel_{date}.json"
    if dual_path.exists():
        dual = read_json(dual_path)
        for item in dual.get("channel_2_trade_price", {}).get("instruments", []):
            code = item.get("code") or item.get("ticker")
            if code:
                seen.setdefault(str(code), item.get("name", ""))
    return [{"symbol": code, "name": name} for code, name in sorted(seen.items())]


def build(date: str) -> dict[str, Any]:
    instances = load_instances()
    items = []
    for ref in symbols_from_sources(date):
        symbol = ref["symbol"]
        inst = instances.get(symbol)
        if inst:
            items.append(inst)
        else:
            items.append({
                "symbol": symbol,
                "name": ref.get("name", ""),
                "dimensions": {name: {"label": "待补", "score": None, "basis": ""} for name in DIMENSIONS},
                "total_score": None,
                "moat_grade": "待补护城河",
                "confidence": "待补",
                "basis": "待理解岗结合资料按五维打分",
                "missing_dimensions": DIMENSIONS,
                "source_file": None,
                "status": "待理解岗打分",
            })
    output = {
        "task_id": "TASK-2026-07-03-070",
        "mode": "formal",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fingerprint": {
            "date": date,
            "framework_fixed": True,
            "answers_from_instances": True,
            "rule_source": RULE_SOURCE,
            "instances_dir": str(ROOT / "data" / "moat" / "moat_instances"),
        },
        "scoring_rule": {
            "dimensions": DIMENSIONS,
            "dimension_score": {"宽": 2, "窄": 1, "无": 0},
            "grade": {"7-10": "宽护城河", "4-6": "窄护城河", "0-3": "无护城河"},
        },
        "summary": {
            "total_symbols": len(items),
            "rated": sum(1 for item in items if item.get("status") == "OK"),
            "pending": sum(1 for item in items if item.get("status") != "OK"),
        },
        "items": items,
    }
    write_json(ROOT / "data" / "moat" / f"moat_analysis_{date}.json", output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build moat analysis from dynamic moat instances")
    parser.add_argument("--date", default="20260702")
    args = parser.parse_args()
    output = build(args.date)
    print(json.dumps({
        "date": args.date,
        "summary": output["summary"],
        "instances_dir": output["fingerprint"]["instances_dir"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
