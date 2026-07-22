#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配仓体检重算（派工单任务A·2026-07-22）：四账户现金已找齐(勿再报无源)+实时股票市值→三比率。
现金(董事长核给·逐账户标新鲜度)：富途JPY2,132,074+USD204.75(今日)·SBI JPY17,895,950(7-18)·IBKR USD4,508(7-02)·bitFlyer JPY295,363(7-02)。
FX=162.47(董事长指定)。①几成仓=股票/(股票+现金) ②日股占比=日股/总资产(≤30%) ③各单只(≤20%)。
只读OpenD·不下单。加 json.load 自检(教训:字节干净≠JSON有效)。
用法：python scripts/portfolio_check.py"""
import json, socket, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
FXV = 162.47  # 董事长指定实时值

# 未上市持仓(无OpenD实时价·按成本计入)·SpaceX在0720台账缺失·据0719台账+董事长核给
UNLISTED = [{"symbol": "US.SPCX", "name": "SpaceX", "market": "US", "quantity": 10.0, "cost_per_share": 138.0,
             "reason": "未上市·OpenD无实时价·按成本$138×10股=$1,380计入(源:0719台账富途average_cost A级+董事长核)"}]

CASH = {
    "富途": {"JPY": 2132074, "USD": 204.75, "新鲜度": "今日2026-07-22(董事长现报)"},
    "SBI": {"JPY": 17895950, "新鲜度": "2026-07-18(源:sbi_sleeve_2026-07-18.json)"},
    "IBKR": {"USD": 4508, "新鲜度": "2026-07-02(源:四账户现金补充_2026-07-02.md)"},
    "bitFlyer": {"JPY": 295363, "新鲜度": "2026-07-02(同上)"},
}


def now():
    return datetime.now(JST).isoformat(timespec="seconds")


def port_open(t=2.0):
    s = socket.socket(); s.settimeout(t)
    try:
        s.connect(("127.0.0.1", 11111)); return True
    except Exception:
        return False
    finally:
        s.close()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    hold = json.loads((ROOT / "data/accounts/holdings_true_20260720.json").read_text(encoding="utf-8"))["holdings"]
    stocks = [h for h in hold if h.get("total_quantity") and not h["symbol"].startswith("CC.")]
    out = {"date": "20260722", "generated_at": now(), "FX_USDJPY": FXV, "FX来源": "董事长指定实时值162.47",
           "现金_逐账户": CASH, "现金新鲜度说明": "富途今日/SBI 7-18/IBKR·bitFlyer 7-02(董事长核给·G盘已找齐·不再报无源)"}

    if not port_open():
        out["FATAL"] = "OpenD未连·未生产·不顶充"
        p = ROOT / "data/accounts/portfolio_check_20260722.json"
        p.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("OpenD未连·如实记未生产"); return 1

    import futu as ft
    ctx = ft.OpenQuoteContext("127.0.0.1", 11111)
    px = {}
    try:
        codes = [h["symbol"] for h in stocks]
        for i in range(0, len(codes), 50):
            ret, df = ctx.get_market_snapshot(codes[i:i + 50])
            if ret == ft.RET_OK:
                for _, r in df.iterrows():
                    px[str(r["code"])] = (float(r["last_price"]) if r.get("last_price") not in (None, "") else None)
            time.sleep(2)
    finally:
        ctx.close()

    rows = []; miss = []
    for h in stocks:
        c = h["symbol"]; q = float(h["total_quantity"]); p = px.get(c)
        if p is None:
            miss.append(c)
            rows.append({"symbol": c, "name": h.get("name"), "quantity": q, "price": None,
                         "market_value_usd": None, "reason": "OpenD未返回实时价·未取到"})
            continue
        is_jp = c.startswith("JP.")
        mv_local = p * q
        mv_usd = (mv_local / FXV if is_jp else mv_local)
        rows.append({"symbol": c, "name": h.get("name"), "market": ("JP" if is_jp else "US"),
                     "quantity": q, "price": p, "currency": ("JPY" if is_jp else "USD"),
                     "market_value_local": round(mv_local, 2), "market_value_usd": round(mv_usd, 2)})
    # 注入未上市持仓(按成本·列入"未取到实时价")
    for u in UNLISTED:
        mv = u["cost_per_share"] * u["quantity"]
        rows.append({"symbol": u["symbol"], "name": u["name"], "market": u["market"], "quantity": u["quantity"],
                     "price": None, "currency": "USD", "计价方式": "成本(未上市·无实时价)",
                     "cost_per_share": u["cost_per_share"], "market_value_local": round(mv, 2),
                     "market_value_usd": round(mv, 2), "reason": u["reason"]})
        miss.append(u["symbol"])
    stock_usd = sum(r["market_value_usd"] for r in rows if r.get("market_value_usd") is not None)
    jp_usd = sum(r["market_value_usd"] for r in rows if r.get("market") == "JP" and r.get("market_value_usd") is not None)

    cash_usd = 0.0
    for k, v in CASH.items():
        cash_usd += v.get("USD", 0) + (v.get("JPY", 0) / FXV)
    total_usd = stock_usd + cash_usd

    per_stock = sorted([{"symbol": r["symbol"], "name": r["name"],
                         "占总资产%": round(r["market_value_usd"] / total_usd * 100, 2),
                         "market_value_usd": r["market_value_usd"]}
                        for r in rows if r.get("market_value_usd") is not None], key=lambda x: -x["占总资产%"])
    over20 = [x for x in per_stock if x["占总资产%"] > 20]

    out.update({
        "持仓逐只": rows, "持仓只数": len(rows),
        "未取到实时价": [{"symbol": r["symbol"], "name": r["name"], "计价": r.get("计价方式", "缺价·未计入"),
                     "market_value_usd": r.get("market_value_usd"), "原因": r.get("reason")}
                    for r in rows if r["symbol"] in miss],
        "汇总_USD": {"股票市值": round(stock_usd, 2), "现金合计": round(cash_usd, 2), "总资产": round(total_usd, 2),
                   "日股市值": round(jp_usd, 2)},
        "①几成仓": {"股票市值/总资产%": round(stock_usd / total_usd * 100, 1),
                 "防御仓(现金)占比%": round(cash_usd / total_usd * 100, 1),
                 "防御仓线": "现金应≥20%", "防御仓是否达标": (cash_usd / total_usd >= 0.20),
                 "口径": "几成仓=股票/(股票+现金)"},
        "②日股占比_vs单一驱动30%": {"日股市值USD": round(jp_usd, 2), "占总资产%": round(jp_usd / total_usd * 100, 1),
                             "风控线": "单一驱动(日元)≤30%", "是否超线": (jp_usd / total_usd > 0.30)},
        "③各单只占比_vs20%": {"逐只降序": per_stock, "超20%的": over20, "风控线": "单只≤20%"},
    })
    p = ROOT / "data/accounts/portfolio_check_20260722.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    raw = p.read_bytes()
    # 自检:字节 + json.load
    try:
        json.load(open(p, encoding="utf-8")); jl = True
    except Exception as e:
        jl = False; print("★json.load失败", e)
    print("wrote", p.name, len(raw), "字节·EFBFBD=", raw.count(b"\xef\xbf\xbd"), "·json.load通过=", jl, "·未取价", len(miss))
    print("①几成仓:", out["①几成仓"]["股票市值/总资产%"], "%·防御仓(现金):", out["①几成仓"]["防御仓(现金)占比%"], "%(线20·达标=", out["①几成仓"]["防御仓是否达标"], ")")
    print("②日股占比:", out["②日股占比_vs单一驱动30%"]["占总资产%"], "%(线30·超线=", out["②日股占比_vs单一驱动30%"]["是否超线"], ")")
    print("③单只超20%:", [(x["symbol"], x["占总资产%"]) for x in over20] or "无")
    print("总资产USD:", round(total_usd, 0), "股票", round(stock_usd, 0), "现金", round(cash_usd, 0), "日股", round(jp_usd, 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
