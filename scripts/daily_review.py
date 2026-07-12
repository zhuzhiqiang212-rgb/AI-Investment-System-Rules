#!/usr/bin/env python3
"""
daily_review.py
TASK-2026-07-02-027

Read-only daily review skeleton.
- Reads yesterday evidence chain and decision cards.
- Pulls quote snapshots only when both archives exist.
- Leaves attribution and Act fields blank for human judgment.
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
DECISION_DIR = ROOT / "data" / "decisions"
REVIEW_DIR = ROOT / "data" / "review"
HOST = "127.0.0.1"
PORT = 11111
JST = timezone(timedelta(hours=9))


def now_jst() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def date_from_arg(value: str | None) -> datetime:
    if value:
        return datetime.strptime(value, "%Y%m%d").replace(tzinfo=JST)
    return datetime.now(JST)


def write_json_utf8(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8", newline="\n")
    reread = path.read_text(encoding="utf-8")
    if reread != text:
        raise RuntimeError(f"UTF-8 reread mismatch: {path}")
    if chr(63) in reread or chr(0xFFFD) in reread:
        raise RuntimeError(f"Garble marker found: {path}")


def load_cards(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cards = data.get("cards", [])
    return cards if isinstance(cards, list) else []


def code_for_snapshot(symbol: str) -> str:
    value = str(symbol or "").strip()
    if not value:
        return value
    if value.startswith(("US.", "HK.", "JP.")):
        return value
    if value.isdigit():
        return "JP." + value
    return "US." + value


def fetch_snapshots(codes: list[str]) -> dict[str, dict[str, Any]]:
    from futu import OpenQuoteContext, RET_OK

    result: dict[str, dict[str, Any]] = {}
    if not codes:
        return result
    ctx = OpenQuoteContext(host=HOST, port=PORT)
    try:
        ret, data = ctx.get_market_snapshot(codes)
        if ret != RET_OK:
            return {code: {"status": "DATA_GAP", "error": str(data)} for code in codes}
        records = data.to_dict(orient="records") if hasattr(data, "to_dict") else []
        for row in records:
            code = str(row.get("code") or row.get("stock_code") or "")
            result[code] = {str(k): safe(v) for k, v in row.items()}
    finally:
        ctx.close()
    return result


def safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return str(value)


def mechanical_verdict(action: str, change_rate: Any) -> str:
    try:
        change = float(change_rate)
    except Exception:
        return "待观察"
    if "不追" in action and change <= 0:
        return "对"
    if "不追" in action and change > 8:
        return "待观察"
    if "持有" in action and change >= -3:
        return "对"
    if "复核" in action:
        return "待观察"
    return "待观察"


def build_review(today: datetime) -> tuple[dict[str, Any] | None, str]:
    yesterday = today - timedelta(days=1)
    today_text = today.strftime("%Y%m%d")
    yesterday_text = yesterday.strftime("%Y%m%d")
    evidence_path = EVIDENCE_DIR / f"daily_{yesterday_text}.json"
    decision_path = DECISION_DIR / f"decision_cards_{yesterday_text}.json"
    if not evidence_path.exists() or not decision_path.exists():
        return None, "无昨日存档,跳过复盘"

    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    cards = load_cards(decision_path)
    codes = [code_for_snapshot(str(card.get("标的", ""))) for card in cards]
    snapshots = fetch_snapshots(codes)
    items = []
    for card in cards:
        symbol = str(card.get("标的", ""))
        code = code_for_snapshot(symbol)
        snap = snapshots.get(code, {})
        action = str(card.get("今日动作", ""))
        change = snap.get("update_time") and (snap.get("change_rate") or snap.get("change_rate_5min"))
        items.append({
            "symbol": symbol,
            "code": code,
            "yesterday_action": action,
            "today_snapshot": snap,
            "verdict": mechanical_verdict(action, change),
            "trend_data": {
                "change_rate": change if change is not False else None,
                "source": "Futu OpenD get_market_snapshot",
            },
            "attribution_to_fill_by_human": "",
            "act_plan_to_fill_by_human": "",
        })
    output = {
        "task_id": "TASK-2026-07-02-027",
        "mode": "READ_ONLY_DAILY_REVIEW_SKELETON",
        "generated_at": now_jst(),
        "fingerprint": {
            "review_date": today_text,
            "review_target_date": yesterday_text,
            "evidence_source": str(evidence_path),
            "decision_source": str(decision_path),
            "generated_at": now_jst(),
        },
        "safety": {
            "read_only": True,
            "trade_context_created": False,
            "place_order_called": False,
            "published": False,
            "human_fields_left_blank": True,
        },
        "evidence_summary": {
            "date": evidence.get("date", yesterday_text),
            "link_count": len(evidence.get("links", [])),
        },
        "items": items,
    }
    output_path = REVIEW_DIR / f"daily_review_{today_text}.json"
    write_json_utf8(output_path, output)
    return output, str(output_path)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Read-only daily PDCA review skeleton.")
    parser.add_argument("--date", default=None)
    args = parser.parse_args()
    output, message = build_review(date_from_arg(args.date))
    if output is None:
        print(message)
        return 0
    print(f"OUTPUT_PATH={message}")
    print(f"ITEMS={len(output['items'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
