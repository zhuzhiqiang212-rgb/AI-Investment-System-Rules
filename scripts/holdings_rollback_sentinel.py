#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P0-2 防回滚哨兵 · holdings 股数回滚检测(不静默覆盖)

派工单_数据接入并行开工_20260720 · P0-2:
  「沿用值与最近人工确认值不一致时报警并停用沿用,不许静默覆盖」

分工:
  - 沿用类账户(SBI/IBKR/bitFlyer): 股数走"无交易则沿用旧基表"。若沿用值 != 锚(最近人工确认),
    = 回滚/漂移 → 报警 + 停用沿用(改用锚值) + needs_owner_confirm。
  - 富途账户: 股数走 OpenD 实时,合法随交易变动,不设锚值;若较上一份 confirmed 基表变化,
    flag-only 标『疑似交易/数据异常·需董事长确认』,不改值。

只读+纯计算,不下单、不连 OpenD。锚文件 confirmed_shares_anchor.json 只由人工更新。

用法:
  python scripts/holdings_rollback_sentinel.py --date 20260720          # 检一份 holdings_true
  python scripts/holdings_rollback_sentinel.py --all                    # 全量历史扫描
  from holdings_rollback_sentinel import apply_anchor_guard             # autobuild 内调用
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ACCOUNTS_DIR = ROOT / "data" / "accounts"
ANCHOR_PATH = ACCOUNTS_DIR / "confirmed_shares_anchor.json"
ALARM_LOG = ACCOUNTS_DIR / "rollback_sentinel_log.jsonl"  # 只追加,不改旧记录
JST = timezone(timedelta(hours=9))

FUTU_ALIASES = ("富通", "富途", "Futu", "FUTU", "moomoo")
NON_FUTU_ACCOUNTS = ("SBI", "IBKR", "bitFlyer")


def now_jst() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_anchor() -> dict[str, dict[str, Any]]:
    """返回 {(symbol, account): anchor_row}。"""
    if not ANCHOR_PATH.exists():
        return {}
    doc = _read_json(ANCHOR_PATH)
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for row in doc.get("anchors", []):
        out[(str(row.get("symbol")), str(row.get("account")))] = row
    return out


def _is_futu(account: str) -> bool:
    return str(account) in FUTU_ALIASES


def _num(v: Any) -> float | None:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def check_holdings(holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """比对 holdings 各(symbol,account)与锚。返回报警列表(不修改入参)。"""
    anchor = load_anchor()
    alarms: list[dict[str, Any]] = []
    for h in holdings:
        sym = str(h.get("symbol"))
        for a in h.get("accounts", []) or []:
            acct = str(a.get("account"))
            if _is_futu(acct):
                continue  # 富途走实时,由 futu_change_watch/上层比对,不在锚范围
            key = (sym, acct)
            arow = anchor.get(key)
            if arow is None:
                continue
            anchor_qty = _num(arow.get("confirmed_qty"))
            cur_qty = _num(a.get("quantity"))
            if anchor_qty is None:
                continue  # 锚未定值(如待补持仓量)→不判
            if cur_qty is None or abs(cur_qty - anchor_qty) > 1e-9:
                alarms.append({
                    "symbol": sym,
                    "name": h.get("name"),
                    "account": acct,
                    "inherited_qty": cur_qty,
                    "anchor_qty": anchor_qty,
                    "anchor_source": arow.get("source"),
                    "anchor_confirm_date": arow.get("confirm_date"),
                    "severity": "ROLLBACK_BLOCKED",
                    "action": "停用沿用·改用锚值·needs_owner_confirm",
                })
    return alarms


def apply_anchor_guard(holdings: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """autobuild 内调用:就地修正沿用类账户回滚。
    返回 (修正后的 holdings, 报警列表)。有报警时:该账户 quantity 改回锚值,
    标 qty_source/needs_owner_confirm,并重算 total_quantity。绝不静默沿用旧值。
    """
    anchor = load_anchor()
    alarms: list[dict[str, Any]] = []
    for h in holdings:
        sym = str(h.get("symbol"))
        changed = False
        for a in h.get("accounts", []) or []:
            acct = str(a.get("account"))
            if _is_futu(acct):
                continue
            arow = anchor.get((sym, acct))
            if arow is None:
                continue
            anchor_qty = _num(arow.get("confirmed_qty"))
            cur_qty = _num(a.get("quantity"))
            if anchor_qty is None:
                continue
            if cur_qty is None or abs(cur_qty - anchor_qty) > 1e-9:
                alarms.append({
                    "symbol": sym, "name": h.get("name"), "account": acct,
                    "inherited_qty": cur_qty, "anchor_qty": anchor_qty,
                    "anchor_source": arow.get("source"),
                    "anchor_confirm_date": arow.get("confirm_date"),
                    "severity": "ROLLBACK_BLOCKED",
                    "action": "已停用沿用·改用锚值",
                })
                a["quantity"] = anchor_qty
                a["qty_source"] = f"防回滚哨兵:沿用值({cur_qty})≠人工确认锚({anchor_qty})→已停用沿用,改用锚值。锚源:{arow.get('source')}"
                a["needs_owner_confirm"] = True
                changed = True
        if changed:
            h["total_quantity"] = sum(_num(a.get("quantity")) or 0 for a in h.get("accounts", []) or [])
            h["quantity_status"] = str(h.get("quantity_status", "")) + "·⚠防回滚已介入"
    return holdings, alarms


def append_log(entry: dict[str, Any]) -> None:
    ALARM_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ALARM_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def compute_merge_check(holdings: list[dict[str, Any]]) -> dict[str, str]:
    """从真实 accounts 现算 merge_check(不再沿用 stale 字符串)。仅多账户/需核对的列出。"""
    out: dict[str, str] = {}
    for h in holdings:
        accs = [a for a in (h.get("accounts") or []) if _num(a.get("quantity")) is not None]
        if len(accs) < 2:
            continue
        parts = "+".join(str(int(_num(a["quantity"]))) if float(_num(a["quantity"])).is_integer()
                          else str(_num(a["quantity"])) for a in accs)
        tot = sum(_num(a.get("quantity")) or 0 for a in accs)
        tot_s = str(int(tot)) if float(tot).is_integer() else str(tot)
        out[str(h.get("name"))] = f"{parts}={tot_s}"
    return out


def check_one_file(date: str) -> dict[str, Any]:
    path = ACCOUNTS_DIR / f"holdings_true_{date}.json"
    doc = _read_json(path)
    holdings = doc.get("holdings", [])
    alarms = check_holdings(holdings)
    fresh_merge = compute_merge_check(holdings)
    stale_merge = doc.get("merge_check", {})
    merge_stale = {k: {"stored": stale_merge.get(k), "computed": v}
                   for k, v in fresh_merge.items() if stale_merge.get(k) != v}
    return {"date": date, "file": str(path), "alarms": alarms,
            "merge_check_stale": merge_stale}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="P0-2 防回滚哨兵")
    ap.add_argument("--date")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--log", action="store_true", help="把报警追加进 rollback_sentinel_log.jsonl")
    args = ap.parse_args()

    if args.all:
        files = sorted(glob.glob(str(ACCOUNTS_DIR / "holdings_true_*.json")))
        dates = [os.path.basename(f).replace("holdings_true_", "").replace(".json", "") for f in files]
        dates = [d for d in dates if d.isdigit()]
    elif args.date:
        dates = [args.date]
    else:
        dates = [datetime.now(JST).strftime("%Y%m%d")]

    total_alarms = 0
    for d in dates:
        res = check_one_file(d)
        total_alarms += len(res["alarms"])
        print(f"[{d}] 回滚报警 {len(res['alarms'])} 条; merge_check stale {len(res['merge_check_stale'])} 项")
        for al in res["alarms"]:
            print(f"   ⚠ {al['name']} {al['symbol']}[{al['account']}] 沿用={al['inherited_qty']} 锚={al['anchor_qty']} :: {al['action']}")
        for k, v in res["merge_check_stale"].items():
            print(f"   merge_check[{k}] stored={v['stored']} 应为 {v['computed']}")
        if args.log and (res["alarms"] or res["merge_check_stale"]):
            append_log({"checked_at": now_jst(), **res})
    print(f"总计报警 {total_alarms} 条,共查 {len(dates)} 份。")
    return 1 if total_alarms else 0


if __name__ == "__main__":
    raise SystemExit(main())
