#!/usr/bin/env python3
"""富途持仓实时同步（董事局工单2026-07-17·甲P0）· 只读不下单

问题：系统一直用 2026-07-02 的四账户 OCR 快照 → 董事长在富途的加减仓没反映，
      集中度/闲钱/加谁减谁 全部可能算错。
做法：富途账户直接从 OpenD 交易接口拉【当前实时持仓 + 券商成本均价】(只读 position_list_query)；
      SBI / IBKR / bitFlyer 不在 OpenD 里 → 明确标"需董事长手工确认"，绝不拿旧数顶充。

⚠成本口径：OpenD 的 cost_price 对拆股/多次买入的标的可能返回负值(如台积电 -23352)，
  那是券商的"摊薄成本"字段异常 → 一律优先用 average_cost(平均成本)，负值不采用。

产物：data/accounts/futu_positions_{date}.json（含与上次快照的变化清单）
用法：python scripts/futu_positions_sync.py --date 20260717
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
# OpenD 拉不到的券商(非富途)——只能靠董事长确认，不许拿旧数当今天的
NON_OPEND = ("SBI", "IBKR", "bitFlyer")


def pull() -> dict:
    """从 OpenD 拉富途真实持仓+成本+现金。返回 {"error":..., "positions":[...], "cash":{...}}"""
    try:
        from futu import (OpenSecTradeContext, TrdMarket, SecurityFirm, TrdEnv,
                          Currency, RET_OK)
    except Exception as e:
        return {"error": f"futu SDK 不可用：{e}", "positions": [], "cash": {}}
    t = None
    try:
        t = OpenSecTradeContext(filter_trdmarket=TrdMarket.US, host="127.0.0.1", port=11111,
                                security_firm=SecurityFirm.FUTUSECURITIES)
        r, accs = t.get_acc_list()
        if r != RET_OK:
            return {"error": f"取账户列表失败：{accs}", "positions": [], "cash": {}}
        real = [a for _i, a in accs.iterrows() if str(a.get("trd_env")) == "REAL"]
        if not real:
            return {"error": "OpenD 里没有 REAL 账户（只有模拟盘）→ 拉不到真实持仓", "positions": [], "cash": {}}
        acc_id = int(real[0]["acc_id"])
        r, d = t.position_list_query(acc_id=acc_id, trd_env=TrdEnv.REAL)
        if r != RET_OK:
            return {"error": f"取持仓失败：{d}", "positions": [], "cash": {}}
        pos = []
        for _i, x in d.iterrows():
            # 成本：优先 average_cost；cost_price 出现负值(券商摊薄字段异常)→不采用
            cp, ac = x.get("cost_price"), x.get("average_cost")
            cost, src = None, ""
            if ac is not None and float(ac) > 0:
                cost, src = float(ac), "OpenD average_cost(券商平均成本·A级)"
            elif cp is not None and float(cp) > 0:
                cost, src = float(cp), "OpenD cost_price(券商成本·A级)"
            else:
                src = f"待接·券商成本字段异常(cost_price={cp}/average_cost={ac})→不编"
            pos.append({"symbol": str(x["code"]), "name": str(x.get("stock_name") or ""),
                        "account": "富途", "quantity": float(x["qty"]),
                        "cost_price": cost, "cost_source": src,
                        "cost_grade": "A" if cost else "待接",
                        "broker_market_val": float(x["market_val"]) if x.get("market_val") is not None else None,
                        "broker_nominal_price": float(x["nominal_price"]) if x.get("nominal_price") is not None else None,
                        "pl_ratio": (float(x["pl_ratio"]) if x.get("pl_ratio") is not None else None)})
        cash = {}
        r2, a = t.accinfo_query(acc_id=acc_id, trd_env=TrdEnv.REAL, currency=Currency.USD)
        if r2 == RET_OK and len(a):
            x = a.iloc[0]
            cash = {"currency": "USD",
                    "cash": float(x["cash"]) if x.get("cash") is not None else None,
                    "avl_withdrawal_cash": (float(x["avl_withdrawal_cash"])
                                            if x.get("avl_withdrawal_cash") is not None else None),
                    "total_assets": float(x["total_assets"]) if x.get("total_assets") is not None else None,
                    "market_val": float(x["market_val"]) if x.get("market_val") is not None else None,
                    "source": "OpenD accinfo_query(REAL·USD)"}
        return {"error": "", "acc_id": acc_id, "positions": pos, "cash": cash}
    except Exception as e:
        return {"error": f"OpenD 交易接口异常：{type(e).__name__}: {e}", "positions": [], "cash": {}}
    finally:
        if t is not None:
            try:
                t.close()
            except Exception:
                pass


FUTU_ALIASES = ("富通", "富途", "Futu", "FUTU", "moomoo")


def _old_futu(date: str) -> dict:
    """变化清单的比对基线 = 系统【实际在用】的上一份 holdings_true 里富途那部分的股数。
    ⚠不能用 unified_holdings_latest(07-02 OCR)：它缺闪迪等条目，会把"5→20 加仓"误报成"新增"。
    ⚠账户名在数据里写作「富通」。"""
    base = None
    for p in sorted((ROOT / "data" / "accounts").glob("holdings_true_*.json"), reverse=True):
        stem = p.stem.replace("holdings_true_", "")
        if stem.isdigit() and stem < date:
            base = p
            break
    if base is None:
        return {}
    try:
        u = json.loads(base.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for v in u.get("holdings", []) or []:
        for a in v.get("accounts", []) or []:
            if str(a.get("account")) in FUTU_ALIASES:
                out[str(v.get("symbol"))] = {"qty": a.get("quantity"), "name": v.get("name"),
                                             "base_file": base.name}
    return out


def diff(pos: list, date: str) -> list:
    old = _old_futu(date)
    now = {p["symbol"]: p for p in pos}
    rows = []
    for k in sorted(set(old) | set(now)):
        o, n = old.get(k), now.get(k)
        oq = (o or {}).get("qty")
        nq = (n or {}).get("quantity")
        if oq == nq:
            continue
        if (oq or 0) == 0 and (nq or 0) == 0:
            continue    # 基线里就是0、现在也没有 → 不是变化(如东京海上富途早已清空)
        if oq is None:
            rows.append({"ticker": k, "name": n["name"], "change": "新增", "old_qty": 0, "new_qty": nq,
                         "cost_price": n.get("cost_price"),
                         "note": "上一份基线里富途没有这只 → 这几天新买的"})
        elif nq is None:
            rows.append({"ticker": k, "name": (o or {}).get("name") or k, "change": "清空", "old_qty": oq, "new_qty": 0,
                         "cost_price": None, "note": "上次快照富途有、现在 OpenD 里没有 → 已全部卖出"})
        else:
            rows.append({"ticker": k, "name": n["name"],
                         "change": ("加仓" if nq > oq else "减仓"), "old_qty": oq, "new_qty": nq,
                         "cost_price": n.get("cost_price"),
                         "note": f"股数 {oq:g} → {nq:g}（{'+' if nq > oq else ''}{nq-oq:g}）"})
    return rows


def main() -> int:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="富途持仓实时同步(OpenD·只读)")
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    r = pull()
    doc = {
        "_说明": "富途账户的【当前实时持仓+券商成本均价】，直接取自 OpenD 交易接口(只读 position_list_query)，"
                 "不再用 2026-07-02 的 OCR 快照。SBI/IBKR/bitFlyer 不在 OpenD 里 → 见 non_opend_accounts，"
                 "那几个账户的持仓需董事长手工确认，系统不拿旧数顶充。",
        "date": a.date,
        "generated_at": datetime.now(JST).isoformat(timespec="seconds"),
        "source": "OpenD OpenSecTradeContext.position_list_query(REAL) + accinfo_query",
        "error": r.get("error", ""),
        "acc_id": r.get("acc_id"),
        "futu_positions": r.get("positions", []),
        "futu_cash": r.get("cash", {}),
        "changes_vs_last_snapshot": diff(r.get("positions", []), a.date),
        "non_opend_accounts": {
            "accounts": list(NON_OPEND),
            "status": "需董事长手工确认",
            "note": "这几家券商不接 OpenD，系统拉不到它们的实时持仓。"
                    "产品里凡用到它们的股数，都是 2026-07-02 的 OCR 快照 → 已在册内标明"
                    "「该账户持仓需董事长手工确认」，不冒充当日实时。",
        },
    }
    p = ROOT / "data" / "accounts" / f"futu_positions_{a.date}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if doc["error"]:
        print(f"[富途同步 失败] {doc['error']}", file=sys.stderr)
        return 3
    print(f"wrote {p.name} · 富途 {len(doc['futu_positions'])} 只 · 变化 {len(doc['changes_vs_last_snapshot'])} 项")
    for c in doc["changes_vs_last_snapshot"]:
        cp = f"成本 {c['cost_price']:.2f}" if c.get("cost_price") else "成本待接"
        print(f"   ⚡ {c['change']} {c['name']}({c['ticker']}) {c['old_qty']:g}→{c['new_qty']:g} · {cp}")
    cash = doc["futu_cash"]
    if cash:
        print(f"   富途现金 ${cash.get('cash'):,.2f} · 可提 ${cash.get('avl_withdrawal_cash'):,.2f} "
              f"· 总资产 ${cash.get('total_assets'):,.2f}")
    n_wait = sum(1 for x in doc["futu_positions"] if not x.get("cost_price"))
    if n_wait:
        print(f"   ⚠ {n_wait} 只券商成本字段异常→标待接不编")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
