#!/usr/bin/env python
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from skill_gate import ceo_design_gate, constitution_gate, is_constitution_task_package, write_failure_log


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_html(text: str) -> str:
    text = re.sub(r"<script[^>]*>[\s\S]*</script>", " ", text, flags=re.I)
    text = re.sub(r"<style[^>]*>[\s\S]*</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(re.sub(r"\s+", " ", text))


def item(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"item": name, "ok": bool(ok), "detail": detail}


def has_any(text: str, needles: list[str]) -> bool:
    return any(n in text for n in needles)


def status(checks: list[dict[str, Any]], guardrail: bool = False) -> str:
    if all(c["ok"] for c in checks):
        return "PASS_WITH_GUARDRAIL" if guardrail else "PASS"
    return "RETURN"


def gate0_constitution(report_path: Path) -> dict[str, Any]:
    # 第0闸只硬卡 docs/tasks/TASK-* 任务包。日报等最终产品在此豁免，
    # 其总则合规由生产任务包声明和 Claude/董事长语义质检承担。
    is_task_package = is_constitution_task_package(report_path)
    passed, failures = constitution_gate(report_path)
    if not passed:
        write_failure_log(report_path, failures)
    detail = "; ".join(failures)
    if passed and not is_task_package:
        detail = "最终产品豁免任务包总则对照形式检查；产品合规由生产任务担保"
    checks = [item("constitution_alignment_statement_present_or_product_exempt", passed, detail)]
    return {"gate": "G0_CONSTITUTION_GATE", "status": "PASS" if passed else "FAIL", "checks": checks}


def gate05_ceo_self_discipline(report_path: Path) -> dict[str, Any]:
    # 第0.5闸守 CEO 设计与第二质检产出。它只检查是否写了依据声明与质检清单，
    # 不判断语义对错，语义由 Claude 第二质检与董事长终审抽查。
    passed, failures = ceo_design_gate(report_path)
    if not passed:
        write_failure_log(report_path, failures)
    detail = "; ".join(failures)
    checks = [item("ceo_basis_and_qa_checklist_present", passed, detail)]
    return {"gate": "G0_5_CEO_SELF_DISCIPLINE_GATE", "status": "PASS" if passed else "FAIL", "checks": checks}


def load(report_path: Path, holdings_path: Path) -> tuple[str, str, dict[str, Any]]:
    report_html = read_text(report_path)
    return report_html, strip_html(report_html), json.loads(read_text(holdings_path))


def gate1(report_text: str, holdings: dict[str, Any]) -> dict[str, Any]:
    entries = holdings.get("entries") or []
    summary = holdings.get("summary") or {}
    required = ["account", "ticker", "quantity", "price", "currency", "market_value_usd"]
    missing_rows: list[str] = []
    bad_value_rows: list[str] = []
    price_allowed: list[str] = []
    for idx, entry in enumerate(entries, 1):
        missing = [f for f in required if f not in entry]
        if missing:
            missing_rows.append(f"row {idx} {entry.get('ticker', '<NO_TICKER>')}: missing {','.join(missing)}")
        for f in ["quantity", "price", "market_value_usd"]:
            v = entry.get(f)
            if v is None or v == "":
                if f == "price" and entry.get("market_value_usd") and entry.get("quantity") and entry.get("source"):
                    price_allowed.append(f"{entry.get('ticker', '<NO_TICKER>')}: price empty, market value/source present")
                else:
                    bad_value_rows.append(f"row {idx} {entry.get('ticker', '<NO_TICKER>')}: {f} empty")
            elif f in ["quantity", "market_value_usd"] and isinstance(v, (int, float)) and v <= 0:
                bad_value_rows.append(f"row {idx} {entry.get('ticker', '<NO_TICKER>')}: {f} <= 0")
    grades = {str(e.get("data_grade", "")) for e in entries}
    checks = [
        item("entries_non_empty", bool(entries), f"entries={len(entries)}"),
        item("summary_core_fields", all(k in summary for k in ["holdings_total_usd", "known_cash_usd", "known_assets_total_usd"]),
             f"summary_keys={','.join(sorted(summary.keys()))}"),
        item("entry_required_fields", not missing_rows, "; ".join(missing_rows[:8])),
        item("quantity_and_market_value_valid_price_gap_marked", not bad_value_rows,
             "; ".join(bad_value_rows[:8]) or ("allowed: " + "; ".join(price_allowed[:8]))),
        item("data_grade_traceable", bool(grades) and (("A" in grades) or ("B+" in grades)), f"data_grades={','.join(sorted(grades))}"),
        item("futu_cash_pending_removed", "富途现金待补" not in report_text and "富途现金待补" not in json.dumps(summary, ensure_ascii=False),
             "no futu cash pending marker found"),
    ]
    return {"gate": "G1_DATA_TO_VALUATION", "status": status(checks), "checks": checks}


def gate2(report_text: str, holdings: dict[str, Any]) -> dict[str, Any]:
    merged = holdings.get("aggregate_by_ticker") or []
    if isinstance(merged, list):
        unique = [str(x.get("ticker")) for x in merged if isinstance(x, dict) and x.get("ticker")]
    else:
        unique = []
    if not unique:
        unique = sorted({str(e.get("ticker")) for e in holdings.get("entries", []) if e.get("ticker")})
    true_target_aliases = {
        "NVDA": ["NVDA", "英伟达"],
        "MSFT": ["MSFT", "微软"],
        "9984": ["9984", "软银"],
    }
    true_hits = [
        target
        for target, aliases in true_target_aliases.items()
        if any(alias in report_text for alias in aliases)
    ]
    placeholder_count = max(len(unique) - len(true_hits), 0)
    guardrail_ok = has_any(report_text, ["占位", "不可下单", "不可自动下单", "待补真估值", "均不可自动下单"])
    bad_cost = []
    for entry in holdings.get("entries", []):
        if (entry.get("cost_price") == 0 or entry.get("cost_basis") == 0) and "待补" in str(entry.get("cost_grade", "")):
            bad_cost.append(str(entry.get("ticker")))
    checks = [
        item("valuation_section_present", has_any(report_text, ["机会与买卖计划", "真估值", "估值"]), "valuation words found"),
        item("true_valuation_hits", len(true_hits) >= 3, f"hits={','.join(true_hits)}"),
        item("placeholder_has_no_order_guardrail", guardrail_ok, f"placeholder_count={placeholder_count}"),
        item("no_zero_fake_cost", not bad_cost, ",".join(bad_cost[:10])),
    ]
    guardrail = placeholder_count > 0 and guardrail_ok and all(c["ok"] for c in checks)
    return {
        "gate": "G2_VALUATION_TO_RISK",
        "status": status(checks, guardrail=guardrail),
        "checks": checks,
        "guardrail": "NO_ORDER_GUARDRAIL_RELEASE" if guardrail else "",
        "placeholder_valuation_count": placeholder_count,
        "true_valuation_hits": true_hits,
    }


def gate3(report_text: str) -> dict[str, Any]:
    checks = [
        item("today_trade_decision_clear", has_any(report_text, ["不主动交易", "0 件交易", "今天动不动"]), "today action found"),
        item("risk_section_present", has_any(report_text, ["今天最大的风险", "风险"]), "risk section found"),
        item("forbidden_action_present", has_any(report_text, ["不能做", "禁止", "不追", "不自动下单"]), "forbidden action found"),
        item("exposure_linked_to_risk", has_any(report_text, ["AI 集中", "加密", "高 Beta", "半导体", "集中"]), "exposure terms found"),
        item("manual_check_for_low_grade_data", has_any(report_text, ["人工核对", "下单前", "OCR", "截图"]), "manual check terms found"),
    ]
    return {"gate": "G3_RISK_TO_TODAY_ACTION", "status": status(checks), "checks": checks}


def gate4(report_html: str, report_text: str) -> dict[str, Any]:
    h2_count = len(re.findall(r"<h2", report_html, flags=re.I))
    flip_count = report_text.count("反过来想")
    checks = [
        item("first_screen_action_visible", has_any(report_text[:2500], ["今天动不动", "不主动交易", "0 件交易"]), "front section checked"),
        item("reverse_thesis_present", flip_count >= 5, f"reverse_count={flip_count}"),
        item("core_sections_present", all(has_any(report_text, [x]) for x in ["风险", "机会", "账户", "现金", "缺口"]), "risk/opportunity/account/cash/gaps"),
        item("source_and_placeholder_marked", all(has_any(report_text, [x]) for x in ["OCR", "占位", "不可下单"]), "OCR/placeholder/no-order"),
        item("not_order_and_chairman_final", has_any(report_text, ["非下单指令", "最终决策在董事长"]), "disclaimer found"),
        item("report_structure_complete", h2_count >= 9, f"h2_count={h2_count}"),
    ]
    return {"gate": "G4_TODAY_ACTION_TO_DAILY_REPORT", "status": status(checks), "checks": checks}


def run(report: Path, holdings: Path) -> dict[str, Any]:
    gate0 = gate0_constitution(report)
    if gate0["status"] != "PASS":
        return {
            "tool": "quality_chain_check.py",
            "mode": "read_only_no_order_no_publish",
            "report": str(report),
            "holdings": str(holdings),
            "overall": "FAIL",
            "gates": [gate0],
        }
    gate05 = gate05_ceo_self_discipline(report)
    if gate05["status"] != "PASS":
        return {
            "tool": "quality_chain_check.py",
            "mode": "read_only_no_order_no_publish",
            "report": str(report),
            "holdings": str(holdings),
            "overall": "FAIL",
            "gates": [gate0, gate05],
        }
    report_html, report_text, data = load(report, holdings)
    gates = [gate0, gate05, gate1(report_text, data), gate2(report_text, data), gate3(report_text), gate4(report_html, report_text)]
    overall = "PASS" if all(g["status"] in {"PASS", "PASS_WITH_GUARDRAIL"} for g in gates) else "RETURN"
    return {
        "tool": "quality_chain_check.py",
        "mode": "read_only_no_order_no_publish",
        "report": str(report),
        "holdings": str(holdings),
        "overall": overall,
        "gates": gates,
    }


def print_text(result: dict[str, Any]) -> None:
    print(f"QUALITY_CHAIN_CHECK overall={result['overall']}")
    print(f"report={result['report']}")
    print(f"holdings={result['holdings']}")
    if result.get("overall") == "FAIL" and any(g.get("gate") == "G0_CONSTITUTION_GATE" and g.get("status") != "PASS" for g in result.get("gates", [])):
        print("第0闸·总则合规未过")
    if result.get("overall") == "FAIL" and any(g.get("gate") == "G0_5_CEO_SELF_DISCIPLINE_GATE" and g.get("status") != "PASS" for g in result.get("gates", [])):
        print("第0.5闸·CEO自律未过")
    for gate in result["gates"]:
        suffix = f" ({gate.get('guardrail')})" if gate.get("guardrail") else ""
        print(f"\n{gate['gate']}: {gate['status']}{suffix}")
        if "placeholder_valuation_count" in gate:
            print(f"  placeholder_valuation_count={gate['placeholder_valuation_count']}")
            print(f"  true_valuation_hits={','.join(gate.get('true_valuation_hits', []))}")
        for check in gate["checks"]:
            mark = "PASS" if check["ok"] else "RETURN"
            detail = f" -- {check['detail']}" if check.get("detail") else ""
            print(f"  [{mark}] {check['item']}{detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only four-gate quality chain check.")
    parser.add_argument("--report", required=True, help="daily report html path")
    parser.add_argument("--holdings", required=True, help="unified holdings json path")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = parser.parse_args()
    result = run(Path(args.report), Path(args.holdings))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_text(result)
    return 0 if result["overall"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
