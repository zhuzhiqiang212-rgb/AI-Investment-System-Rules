#!/usr/bin/env python3
"""
daily_startup_run.py
TASK-2026-07-02-027

Read-only daily startup orchestrator.
- Runs automatic steps in order.
- Stops at unmet human dependencies.
- No order, no publish.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(r"G:\我的云端硬盘\AI_Investment_System")
JST = timezone(timedelta(hours=9))


def date_text(value: str | None) -> str:
    if value:
        return value
    return datetime.now(JST).strftime("%Y%m%d")


def run_step(label: str, cmd: list[str]) -> int:
    print(f"RUN {label}: {' '.join(cmd)}")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True, encoding="utf-8", errors="replace", env=env)
    if proc.stdout:
        print(proc.stdout.strip())
    if proc.stderr:
        print(proc.stderr.strip())
    return proc.returncode


def require_file(path: Path, step: str, message: str) -> bool:
    if path.exists():
        return True
    print(f"需人工完成{step}: {message}")
    return False


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Read-only daily startup runner.")
    parser.add_argument("--date", default=None)
    args = parser.parse_args()
    today = date_text(args.date)

    review_code = run_step("⓪复盘昨天", ["python", str(ROOT / "scripts" / "daily_review.py"), "--date", today])
    if review_code != 0:
        print("需人工完成第⓪步: 复盘脚本返回异常")
        return review_code

    evidence = ROOT / "data" / "evidence_chain" / f"daily_{today}.json"
    if not require_file(evidence, "第②步", f"填当日求证表 {evidence}"):
        return 2

    # ①持仓真表：A8 自动建(股数沿用最近confirmed + 今日OpenD现价)。
    # 已存在则不覆盖——保护董事长报交易后手工更正的当日真表。
    holdings_true = ROOT / "data" / "accounts" / f"holdings_true_{today}.json"
    if not holdings_true.exists():
        code = run_step("①持仓真表(A8·股数沿用+今日OpenD价)",
                        ["python", str(ROOT / "scripts" / "holdings_true_autobuild.py"), "--date", today])
        if code != 0:
            print("需人工完成第①步: holdings_true 自动生成未通过(A8)")
            return code
    else:
        print(f"①持仓真表已存在(跳过·不覆盖): {holdings_true.name}")

    for label, script in [
        ("③机会发现", "opportunity_chain_driven.py"),
        ("④日报上半截", "daily_upper_from_chain.py"),
        ("⑤审持仓", "holdings_review_against_chain.py"),
    ]:
        code = run_step(label, ["python", str(ROOT / "scripts" / script), "--date", today])
        if code != 0:
            print(f"需人工完成{label}: 自动脚本未通过")
            return code

    holdings = ROOT / "data" / "accounts" / "unified_holdings_latest.json"
    opportunity_pool = ROOT / "data" / "opportunities" / f"chain_opportunities_{today}.json"
    if not require_file(opportunity_pool, "第⑤b步", f"机会池产物 {opportunity_pool}"):
        return 2
    if not require_file(holdings, "第⑤b步", f"统一持仓库 {holdings}"):
        return 2

    code = run_step("⑤b估值分派", ["python", str(ROOT / "scripts" / "valuation_dispatcher.py"), "--date", today])
    if code != 0:
        print("需人工完成第⑤b步: 估值分派未通过")
        return code

    valuation_dispatch = ROOT / "data" / "valuation" / f"valuation_dispatch_{today}.json"
    dual_channel = ROOT / "data" / "opportunities" / f"dual_channel_{today}.json"
    if not require_file(opportunity_pool, "第⑤c步", f"机会池产物 {opportunity_pool}"):
        return 2
    if not require_file(holdings, "第⑤c步", f"统一持仓库 {holdings}"):
        return 2
    if not require_file(valuation_dispatch, "第⑤c步", f"估值分派产物 {valuation_dispatch}"):
        return 2
    if not require_file(dual_channel, "第⑤c步", f"双通道产物 {dual_channel}"):
        return 2

    code = run_step("⑤c催化维", ["python", str(ROOT / "scripts" / "catalyst_dimension_build.py"), "--date", today])
    if code != 0:
        print("需人工完成第⑤c步: 催化维未通过")
        return code

    report = ROOT / "00_请先看这里" / f"日报_{today[:4]}-{today[4:6]}-{today[6:]}_完整经线版.html"
    if not require_file(report, "第⑧步", f"组装日报 {report}"):
        return 2

    code = run_step("⑦四闸门", [
        "python",
        str(ROOT / "scripts" / "quality_chain_check.py"),
        "--report",
        str(report),
        "--holdings",
        str(holdings),
        "--json",
    ])
    if code != 0:
        print("需人工完成第⑦步: 四闸门打回")
        return code

    code = run_step("⑧复盘打分", ["python", str(ROOT / "scripts" / "pdca_scorecard.py"), "--date", today])
    if code != 0:
        print("需人工完成第⑧步: PDCA记分卡未通过")
        return code

    print("自动开机流程完成，等待第⑨步董事长签字")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
