#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOLDINGS = ROOT / "data/accounts/unified_holdings_latest.json"
DEFAULT_RESEARCH = ROOT / "data/research/candidates_20260702.json"
DEFAULT_OUT_DIR = ROOT / "data/decisions"
TRUE_VALUATION = {"NVDA", "MSFT", "9984"}
AI_CORE = {"NVDA", "MSFT", "9984", "AVGO", "TSM", "6857"}
CRYPTO_HIGH_BETA = {"MSTR", "COIN", "CRCL", "BTC", "ETH"}


def safe_text(value: Any) -> str:
    return str(value).replace("\ufffd", "").replace(chr(63), "？")


def fmt_money(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"${value:,.0f}"
    return "待补"


def accounts_distribution(row: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for acct in row.get("accounts", []):
        out.append({
            "account": safe_text(acct.get("account", "待补")),
            "ticker": safe_text(acct.get("ticker", row.get("ticker", "待补"))),
            "quantity": acct.get("quantity"),
            "market_value_usd": acct.get("market_value_usd"),
        })
    return out


def cost_pnl(row: dict[str, Any]) -> dict[str, Any]:
    basis = row.get("known_cost_basis_usd")
    pnl_pct = row.get("known_unrealized_pnl_pct")
    status = row.get("cost_coverage_status") or "待补"
    return {
        "coverage_status": safe_text(status),
        "cost_basis_usd": basis if basis is not None else "待补",
        "unrealized_pnl_pct": pnl_pct if pnl_pct is not None else "待补",
        "note": "有则填；无则待补，不用零或现价冒充",
    }


def data_grade(row: dict[str, Any]) -> str:
    grades = []
    for acct in row.get("accounts", []):
        if acct.get("cost_grade"):
            grades.append(str(acct.get("cost_grade")))
    return safe_text(" / ".join(sorted(set(grades))) if grades else "待补")


def valuation(ticker: str) -> dict[str, str]:
    base = ticker.split(".")[0]
    if base in TRUE_VALUATION:
        return {"status": "真估值", "note": "已在日报估值区列示，仍非自动下单"}
    return {"status": "占位", "note": "不可下单，待补真估值"}


def today_action(ticker: str) -> str:
    base = ticker.split(".")[0]
    if base in AI_CORE:
        return "持有"
    if base in CRYPTO_HIGH_BETA:
        return "不追"
    return "复核"


def research_link(ticker: str, research: dict[str, Any]) -> str:
    blob = json.dumps(research, ensure_ascii=False)
    base = ticker.split(".")[0]
    if base and base in blob:
        return "引用今日研究候选，待 Claude 理解岗确认"
    return "无新研究"


def build_cards(holdings_path: Path, research_path: Path, out_dir: Path, run_date: str) -> dict[str, Any]:
    data = json.loads(holdings_path.read_text(encoding="utf-8"))
    research = {}
    if research_path.exists():
        research = json.loads(research_path.read_text(encoding="utf-8"))
    cards = []
    for row in data.get("aggregate_by_ticker", []):
        ticker = safe_text(row.get("ticker", "待补"))
        card = {
            "标的": ticker,
            "账户分布": accounts_distribution(row),
            "市值": fmt_money(row.get("market_value_usd")),
            "成本_盈亏": cost_pnl(row),
            "数据等级": data_grade(row),
            "估值": valuation(ticker),
            "今日动作": today_action(ticker),
            "因为→所以": "",
            "🔴反过来想+翻盘信号": "",
            "触发线": "待 Claude 填",
            "研究理解关联": research_link(ticker, research),
        }
        cards.append(card)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"decision_cards_{run_date}.json"
    result = {
        "task_id": "TASK-2026-07-02-015",
        "mode": "skeleton_only_no_order_no_publish",
        "run_date": run_date,
        "card_count": len(cards),
        "true_valuation_count": sum(1 for c in cards if c["估值"]["status"] == "真估值"),
        "placeholder_valuation_count": sum(1 for c in cards if c["估值"]["status"] == "占位"),
        "cost_pending_count": sum(1 for c in cards if c["成本_盈亏"]["coverage_status"] == "PENDING"),
        "cards": cards,
    }
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    reread = out.read_text(encoding="utf-8")
    if "\ufffd" in reread or chr(63) in reread:
        raise SystemExit("bad char detected in decision cards")
    result["output_path"] = str(out)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Build ticker decision card skeletons.")
    parser.add_argument("--holdings", default=str(DEFAULT_HOLDINGS))
    parser.add_argument("--research", default=str(DEFAULT_RESEARCH))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--run-date", default="20260702")
    args = parser.parse_args()
    result = build_cards(Path(args.holdings), Path(args.research), Path(args.out_dir), args.run_date)
    print(json.dumps({
        "output_path": result["output_path"],
        "card_count": result["card_count"],
        "true_valuation_count": result["true_valuation_count"],
        "placeholder_valuation_count": result["placeholder_valuation_count"],
        "cost_pending_count": result["cost_pending_count"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
