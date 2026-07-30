# -*- coding: utf-8 -*-
"""A(38号)·目标—缺口模块。富途/SBI各自独立算·1年双档+40%/+100%。算法照38号A·公允算不出标盲区不填0。
富途走OpenD当日实测(daily_scan);SBI未接OpenD(数据57天前)→盲区·缺口无法计算。IBKR/bitFlyer不做目标。
★换仓测算:对贡献pp最低三只算『卖它换成最高贡献只补多少pp』(答07-19尺P6:换任天堂补多少)。Code只算不改判断。"""
import json, pathlib, argparse
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9))
ROOT = pathlib.Path(__file__).resolve().parent.parent

# 公允值/目标价(每股·取自round33 L1-3表+35号冻结正文·Code不自造)。None=盲区(算不出·标原因·不填0)
FAIR = {
    "US.NVDA": (240.51, None), "US.MSFT": (433.41, None), "JP.4568": (3287, None), "JP.6758": (4113, None),
    "JP.7203": (3000, None), "JP.8766": (7315, None), "JP.7832": (4202, None), "US.AVGO": (328.79, None),
    "US.TSM": (487.5, "目标区$475-500取中"), "US.META": (578.91, None), "JP.7974": (5384, None),
    "US.MSTR": (93.34, None), "US.COIN": (74.58, None), "US.IBKR": (55.0, None),
    # 盲区(公允算不出·写明为什么)
    "JP.9984": (None, "家底价值两个差距悬殊口径(3月NAV¥7,026 vs 6月¥13,000)·无单一答案"),
    "JP.8001": (None, "商社净资产价值待接(EDINET)·当前无实数"),
    "US.CRCL": (None, "偏空·靠利息生意·无公允目标价(缺流通量/久期/分成)"),
    "US.SNDK": (None, "分拆后历史不足3年·引擎normal_eps=null·无可用估值基准"),
    "JP.6857": (None, "双口径不给单一结论·且定价基准452天未复核"),
    "US.SPCX": (None, "非上市股权·无公开财报·估值=接受一级市场轮次报价"),
}
IS_JP = lambda c: c.startswith("JP.")

def load(date):
    scan = json.loads((ROOT / "data" / "market" / f"daily_scan_{date}.json").read_text(encoding="utf-8"))
    px = {q["code"]: q["last_price"] for q in scan["items"]["1_当日20只价"]["逐只"]}
    usdjpy = scan["items"]["5_USDJPY"]["值"]
    hold = json.loads((ROOT / "data" / "accounts" / f"holdings_true_{date}.json").read_text(encoding="utf-8"))["holdings"]
    return px, usdjpy, hold

def acct_positions(hold, acct_names):
    """取某账户(名列表)下各只 (code,name,qty)。富途账户名可能是 富通/富途。"""
    out = []
    for h in hold:
        for a in h.get("accounts", []):
            if a.get("account") in acct_names:
                out.append({"code": h["symbol"], "name": h.get("name", ""), "qty": float(a.get("quantity", 0))})
    return out

def price_usd(code, px, usdjpy):
    p = px.get(code)
    if not isinstance(p, (int, float)): return None
    return p / usdjpy if IS_JP(code) else p

def compute_account(name, positions, px, usdjpy, cash_usd, cash_note):
    """按38号A算:A/目标/每只贡献pp/缺口/盲区%/换仓测算。"""
    rows = []
    stock_val = 0.0
    for pos in positions:
        pu = price_usd(pos["code"], px, usdjpy)
        mv = pu * pos["qty"] if pu is not None else None
        if mv: stock_val += mv
        rows.append({**pos, "price_local": px.get(pos["code"]), "price_usd": pu, "market_value_usd": mv})
    A = stock_val + (cash_usd or 0)
    # 每只 上行%/贡献pp
    for r in rows:
        fair, blind = FAIR.get(r["code"], (None, "未登记公允"))
        if fair is None or r["price_local"] is None or not r["price_local"]:
            r["fair"] = None; r["upside_pct"] = None; r["contribution_pp"] = None
            r["blind"] = True; r["blind_reason"] = blind or "公允算不出"
        else:
            up = (fair - r["price_local"]) / r["price_local"]
            r["fair"] = fair
            r["upside_pct"] = round(up * 100, 2)
            r["contribution_pp"] = round((r["market_value_usd"] / A) * up * 100, 3) if A else None
            r["blind"] = False; r["blind_reason"] = None
    total_contrib = round(sum(r["contribution_pp"] for r in rows if r["contribution_pp"] is not None), 3)
    blind_mv = sum(r["market_value_usd"] for r in rows if r["blind"] and r["market_value_usd"])
    rows_sorted = sorted(rows, key=lambda r: (r["contribution_pp"] is None, -(r["contribution_pp"] or -999)))
    # 换仓测算:最高贡献只 + 贡献最低三只 → 卖低换高补多少pp
    valid = [r for r in rows if r["contribution_pp"] is not None]
    swap = []
    if valid:
        top = max(valid, key=lambda r: r["contribution_pp"])
        low3 = sorted(valid, key=lambda r: r["contribution_pp"])[:3]
        for r in low3:
            if r["code"] == top["code"]: continue
            add_pp = round((r["market_value_usd"] / A) * ((top["upside_pct"] - r["upside_pct"]) / 100) * 100, 3) if A else None
            swap.append({"卖": r["name"], "卖_code": r["code"], "换成": top["name"], "换成_code": top["code"],
                         "能补pp": add_pp, "说明": "卖%s换%s·补%.2f个百分点" % (r["name"], top["name"], add_pp or 0)})
    return {
        "账户": name, "当日总资产A_USD": round(A, 2) if A else None, "股票市值_USD": round(stock_val, 2),
        "现金_USD": cash_usd, "现金说明": cash_note,
        "目标": {"+40%需赚_USD": round(A * 0.40, 2) if A else None, "+100%需赚_USD": round(A * 1.00, 2) if A else None},
        "账户预期贡献合计pp(盲区不计)": total_contrib,
        "距+40%缺口pp": round(40 - total_contrib, 3), "距+100%缺口pp": round(100 - total_contrib, 3),
        "盲区占比%": round(blind_mv / A * 100, 2) if A else None,
        "逐只(按贡献pp降序)": rows_sorted,
        "换仓测算(卖低贡献三只换最高贡献只)": swap,
    }

def _load_ruler_valuations(date):
    """⑤(41号):引用 data/valuation 的尺A/尺B脚本结果·覆盖FAIR。爱德万公允由尺A算出(非硬编码)。"""
    import glob as _g
    val = ROOT / "data" / "valuation"
    for p in _g.glob(str(val / f"ruler_a_*_{date}.json")):
        try:
            r = json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
            code = r["标的"]; fair = r["采用档"]["公允值"]
            FAIR[code] = (fair, None)  # 采用档公允·来自尺A脚本计算
        except Exception:
            pass

def build_futu_authoritative(date):
    """D1(46号)分母核平:富途A统一到单一权威源 futu_positions_{date}.json(OpenD accinfo·07:30·同一时点)。
    A=total_assets·cash=futu_cash.cash·每股市值/价=broker_market_val/broker_nominal_price(同07:30时点·不用daily_scan盘中价·不取平均)。"""
    fp = json.loads((ROOT / "data" / "accounts" / f"futu_positions_{date}.json").read_text(encoding="utf-8"))
    fc = fp["futu_cash"]; A = fc["total_assets"]; cash = fc["cash"]; mval = fc["market_val"]
    tstamp = fp.get("generated_at", "")
    # 隐含FX(OpenD口径):market_val = ΣUS_mv + ΣJP_mv/FX
    us = sum(p["broker_market_val"] for p in fp["futu_positions"] if p["symbol"].startswith("US."))
    jp_local = sum(p["broker_market_val"] for p in fp["futu_positions"] if p["symbol"].startswith("JP."))
    fx = round(jp_local / (mval - us), 3) if (mval - us) else None
    rows = []
    for p in fp["futu_positions"]:
        code = p["symbol"]; px_local = p.get("broker_nominal_price"); mv_local = p.get("broker_market_val")
        mv_usd = mv_local if code.startswith("US.") else (mv_local / fx if fx else None)
        fair, blind = FAIR.get(code, (None, "未登记公允"))
        if fair is None or not px_local:
            up = None; contrib = None; bl = True; br = blind or "公允算不出"
        else:
            up = (fair - px_local) / px_local; contrib = round(mv_usd / A * up * 100, 3); bl = False; br = None
        rows.append({"code": code, "name": next((h.get("name") for h in json.loads((ROOT / "data" / "accounts" / f"holdings_true_{date}.json").read_text(encoding="utf-8"))["holdings"] if h["symbol"] == code), ""),
                     "qty": p["quantity"], "price_local_0730": px_local, "market_value_usd": round(mv_usd, 2) if mv_usd else None,
                     "fair": fair, "upside_pct": round(up * 100, 2) if up is not None else None,
                     "contribution_pp": contrib, "blind": bl, "blind_reason": br})
    total_contrib = round(sum(r["contribution_pp"] for r in rows if r["contribution_pp"] is not None), 3)
    blind_mv = sum(r["market_value_usd"] for r in rows if r["blind"] and r["market_value_usd"])
    rows.sort(key=lambda r: (r["contribution_pp"] is None, -(r["contribution_pp"] or -999)))
    valid = [r for r in rows if r["contribution_pp"] is not None]
    swap = []
    if valid:
        top = max(valid, key=lambda r: r["contribution_pp"])
        for r in sorted(valid, key=lambda r: r["contribution_pp"])[:3]:
            if r["code"] == top["code"]: continue
            add = round(r["market_value_usd"] / A * ((top["upside_pct"] - r["upside_pct"]) / 100) * 100, 3)
            swap.append({"卖": r["name"], "换成": top["name"], "能补pp": add, "说明": "卖%s换%s·补%.2fpp" % (r["name"], top["name"], add)})
    return {"账户": "富途", "当日总资产A_USD": round(A, 2), "股票市值_USD": round(mval, 2), "现金_USD": cash,
            "★单一权威源": "futu_positions_%s.json · OpenD accinfo_query(REAL·USD) · 取数时刻 %s" % (date, tstamp),
            "★口径说明": "A/现金/每股市值均取OpenD 07:30同一快照·同一时点;JP按OpenD隐含FX≈%s换USD;不用daily_scan盘中价·不取平均·不挑顺眼值。轮39差$18,731来源已查实=价格时点(07:30快照 vs daily_scan 12:03盘中)+FX(162.536沿用 vs OpenD 07:30≈%s)双重差·本轮统一到07:30单一源消除" % (fx, fx),
            "现金说明": "OpenD accinfo实测 $%.2f(07:30·非沿用)" % cash,
            "目标": {"+40%需赚_USD": round(A * 0.40, 2), "+100%需赚_USD": round(A * 1.00, 2)},
            "账户预期贡献合计pp(盲区不计)": total_contrib, "距+40%缺口pp": round(40 - total_contrib, 3), "距+100%缺口pp": round(100 - total_contrib, 3),
            "盲区占比%": round(blind_mv / A * 100, 2), "逐只(按贡献pp降序)": rows, "换仓测算(卖低贡献三只换最高贡献只)": swap}

def build(date):
    _load_ruler_valuations(date)
    px, usdjpy, hold = load(date)
    # D1(46号)分母核平:富途改用单一权威源 futu_positions(OpenD 07:30·现金实测$34,279.21·非沿用)
    futu = build_futu_authoritative(date)
    # SBI(38号续①②):盲区已解——股数取07-18权威截图(12天未交易·稳定)·价取当日实测·余力¥17,895,950(07-18沿用)
    #   ★07-18权威股数(SBI持仓(私)/IMG_3519.PNG):第一三共3400/索尼1000/爱德万800/丰田800/伊藤忠900/东京海上1000/软银2800
    SBI_SHARES_0718 = {"JP.4568": 3400, "JP.6758": 1000, "JP.6857": 800, "JP.7203": 800,
                       "JP.8001": 900, "JP.8766": 1000, "JP.9984": 2800}
    nm_map = {h["symbol"]: h.get("name", "") for h in hold}
    sbi_pos = [{"code": c, "name": nm_map.get(c, ""), "qty": float(q)} for c, q in SBI_SHARES_0718.items()]
    sbi_cash_jpy = 17895950
    sbi = compute_account("SBI", sbi_pos, px, usdjpy, cash_usd=sbi_cash_jpy / usdjpy,
                          cash_note="买付余力 ¥17,895,950(07-18·12天前·沿用)→ $%.0f@%.3f" % (sbi_cash_jpy / usdjpy, usdjpy))
    sbi["数据来源说明"] = "★股数=07-18截图(SBI持仓(私)/IMG_3519.PNG·12天未交易稳定) · 价=daily_scan当日实测 · 余力=¥17,895,950(07-18沿用·12天前)"
    sbi["盲区"] = False
    return {
        "_说明": "目标—缺口·2026-07-30·依据正式尺 目标倒推框架_定稿_1年双档_20260719·Code照算法实现未改投资判断",
        "date": date, "生成": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"),
        "口径": "富途/SBI各自独立算不合并·IBKR/bitFlyer不做目标管理(07-19尺:跟随主战场)·期限1年·双档+40%(中性提醒)/+100%(激进执行)",
        "富途": futu, "SBI": sbi,
        "IBKR_bitFlyer": "不做目标管理(07-19尺+07-30确认)·仅附录·被清算/强制处置时提醒",
    }

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out = ROOT / "data" / "target" / f"target_gap_{a.date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    res = build(a.date)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    f = res["富途"]
    print("target_gap %s → %s" % (a.date, out.name))
    print("富途 A=$%.0f · 预期贡献合计 %.2fpp · 距+40%%缺口 %.2fpp · 距+100%%缺口 %.2fpp · 盲区占比 %.1f%%"
          % (f["当日总资产A_USD"], f["账户预期贡献合计pp(盲区不计)"], f["距+40%缺口pp"], f["距+100%缺口pp"], f["盲区占比%"]))
    print("富途贡献pp降序前5:", [(r["name"], r["contribution_pp"]) for r in f["逐只(按贡献pp降序)"][:5]])
    print("★换仓测算(答P6):")
    for s in f["换仓测算(卖低贡献三只换最高贡献只)"]:
        print("   ", s["说明"])
    sb = res["SBI"]
    print("SBI A=$%.0f · 预期贡献合计 %.2fpp · 距+40%%缺口 %.2fpp · 盲区占比 %.1f%%(股数07-18/价当日实测/余力07-18沿用)"
          % (sb["当日总资产A_USD"], sb["账户预期贡献合计pp(盲区不计)"], sb["距+40%缺口pp"], sb["盲区占比%"]))
    print("SBI贡献pp降序:", [(r["name"], r["contribution_pp"]) for r in sb["逐只(按贡献pp降序)"]])
    print("SBI换仓测算:", [s["说明"] for s in sb["换仓测算(卖低贡献三只换最高贡献只)"]])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
