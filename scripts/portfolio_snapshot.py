#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""账户全量快照（派工单B1·2026-07-22）：20只实时市值+现金→几成仓/日股占比/单只占比·对照风控。
★只读OpenD·不下单。连不上如实报"连不上·未生产"·不拿旧数据顶充。
现金:富途=董事长现报(213万JPY+205USD);SBI/IBKR/bitFlyer无实时源(Google Docs当前无法OCR)→用07-02核报值·显眼标"非今日·当前未取到"。
用法:python scripts/portfolio_snapshot.py"""
import json, socket, sys, time, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
JP_DRIVER = {"JP.4568", "JP.9984", "JP.8766", "JP.6758", "JP.6857", "JP.7203", "JP.8001", "JP.7832", "JP.7974"}


def now():
    return datetime.now(JST).isoformat(timespec="seconds")


def live_fx():
    for url in ["https://open.er-api.com/v6/latest/USD"]:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "x"}), timeout=8) as r:
                j = json.loads(r.read().decode())
                if j.get("rates", {}).get("JPY"):
                    return {"USDJPY": float(j["rates"]["JPY"]), "source": "open.er-api", "as_of": j.get("time_last_update_utc"), "fetched": now()}
        except Exception:
            pass
    return {"USDJPY": None, "err": "实时FX未取到"}


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
    fx = live_fx(); FXV = fx.get("USDJPY")
    snap = {"date": "20260722", "generated_at": now(), "FX": fx,
            "现金_口径说明": "富途=董事长2026-07-22现报;SBI/IBKR/bitFlyer=2026-07-02核报值·当前无实时源(Google Docs无法OCR)·★非今日·标缺"}

    if not port_open():
        snap["FATAL"] = "OpenD(11111)连不上·未生产·不拿旧数据顶充"
        (ROOT / "data/accounts/portfolio_snapshot_20260722.json").write_text(json.dumps(snap, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("OpenD连不上·已如实记录未生产"); return 1

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

    # 逐只市值(本币)+折USD
    rows = []; miss = []
    for h in stocks:
        c = h["symbol"]; q = float(h["total_quantity"]); p = px.get(c)
        if p is None:
            miss.append(c); rows.append({"symbol": c, "name": h.get("name"), "quantity": q, "price": None,
                                          "market_value_local": None, "market_value_usd": None, "reason": "OpenD未返回实时价·未取到"})
            continue
        is_jp = c.startswith("JP.")
        mv_local = p * q
        mv_usd = (mv_local / FXV if (is_jp and FXV) else mv_local)
        rows.append({"symbol": c, "name": h.get("name"), "market": ("JP" if is_jp else "US"), "quantity": q,
                     "price": p, "currency": ("JPY" if is_jp else "USD"),
                     "market_value_local": round(mv_local, 2), "market_value_usd": round(mv_usd, 2),
                     "是否日元驱动": c in JP_DRIVER})
    stock_usd = sum(r["market_value_usd"] for r in rows if r.get("market_value_usd") is not None)

    # 现金(USD)
    cash = {
        "富途_2026-07-22董事长现报": {"JPY": 2130000, "USD": 205, "_来源": "董事长口头核报·当日"},
        "SBI_2026-07-02核报": {"JPY": 19520910, "_来源": "四账户现金补充_2026-07-02·★当前无实时源·非今日"},
        "IBKR_2026-07-02核报": {"USD": 4508, "_来源": "同上·★非今日"},
        "bitFlyer_2026-07-02核报": {"JPY": 295363, "_来源": "同上·★非今日"},
        "★当前实时缺": "SBI/IBKR/bitFlyer 现金无实时源(Google Docs当前环境无法导出/OCR)·上列为07-02核报值·董事长须核当前值",
    }
    cash_usd = 0.0
    for k, v in cash.items():
        if isinstance(v, dict):
            cash_usd += v.get("USD", 0) + (v.get("JPY", 0) / FXV if FXV else 0)
    total_usd = stock_usd + cash_usd

    # 三个数
    jp_usd = sum(r["market_value_usd"] for r in rows if r.get("market") == "JP" and r.get("market_value_usd") is not None)
    per_stock = sorted([{"symbol": r["symbol"], "name": r["name"], "占总资产%": round(r["market_value_usd"] / total_usd * 100, 2),
                         "market_value_usd": r["market_value_usd"]} for r in rows if r.get("market_value_usd") is not None],
                       key=lambda x: -x["占总资产%"])
    over20 = [x for x in per_stock if x["占总资产%"] > 20]

    snap.update({
        "持仓逐只": rows, "未取到实时价": miss,
        "现金": cash,
        "汇总_USD": {"股票市值": round(stock_usd, 2), "现金合计": round(cash_usd, 2), "总资产": round(total_usd, 2)},
        "①几成仓_对照防御仓20%": {"股票市值/总资产%": round(stock_usd / total_usd * 100, 1),
                            "防御仓(现金)占比%": round(cash_usd / total_usd * 100, 1),
                            "防御仓线": "防御仓(现金)应≥20%", "防御仓是否达标": (cash_usd / total_usd >= 0.20),
                            "口径": "几成仓=股票市值/(股票+现金)·防御仓=现金/总资产"},
        "②日股占比_vs风控30%": {"日股市值USD": round(jp_usd, 2), "占总资产%": round(jp_usd / total_usd * 100, 1),
                          "风控线": "单一驱动(日元跨9只)≤30%", "是否超线": jp_usd / total_usd > 0.30,
                          "日元驱动9只": sorted(JP_DRIVER)},
        "③各单只占比_vs风控20%": {"逐只": per_stock, "超20%的": over20, "风控线": "单只≤20%"},
        "★数据完整性警示": ("SBI/IBKR/bitFlyer现金为07-02核报(非今日)·影响分母·三比率为含此前提的估算" if FXV else "无FX·比率不可算"),
    })
    p = ROOT / "data/accounts/portfolio_snapshot_20260722.json"
    p.write_text(json.dumps(snap, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    raw = p.read_bytes()
    print("wrote", p.name, len(raw), "字节·EFBFBD=", raw.count(b"\xef\xbf\xbd"), "·未取价", len(miss))
    print("①几成仓:", snap["①几成仓_对照防御仓20%"]["股票市值/总资产%"], "%·防御仓(现金):", snap["①几成仓_对照防御仓20%"]["防御仓(现金)占比%"], "%(线20%·达标=", snap["①几成仓_对照防御仓20%"]["防御仓是否达标"], ")")
    print("②日股占比:", snap["②日股占比_vs风控30%"]["占总资产%"], "% (线30%·超线=", snap["②日股占比_vs风控30%"]["是否超线"], ")")
    print("③单只超20%:", [(x["symbol"], x["占总资产%"]) for x in over20] or "无")
    print("总资产USD:", round(total_usd, 0), "股票", round(stock_usd, 0), "现金", round(cash_usd, 0), "FX", FXV)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
