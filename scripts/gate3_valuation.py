#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第3关·估值（贵不贵）·给真主池15只跑（派工单D2·2026-07-22）。只读OpenD·不下单。
按标的类型选模型：成长股→成长PE/PEG；能源公用→股息+现金流(PE低+高股息)；医药→DCF管线(★OpenD无管线预测→用PE/PB代理·标DCF待接)；军工→防务PE中枢。
每只输出：估值模型/关键值/现价/便宜or合理or明显贵。便宜合理→过；明显贵→记下等回调(★不淘汰)。
★阈值均为暂行(教科书口径)·须架构师核。★基数效应护栏(守5.5)：净利同比>60%多为周期/小基数→PEG失真→改看PE绝对+标注。
带每只逐关轨迹(第1关→第2关象限→第3关估值)+generated_at+倒推自检(晚于gate2)。
用法：python scripts/gate3_valuation.py --date 20260722 --fin-date 20260721"""
import argparse, json, socket, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import Counter
ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "data" / "screen"
JST = timezone(timedelta(hours=9))

POOL15 = ["US.CDNS", "US.COHR", "US.CRDO", "US.D", "US.DGX", "US.GSK", "US.HII",
          "US.INCY", "US.KLAC", "US.LITE", "US.P", "US.PEG", "US.PLTR", "US.STX", "US.WDC"]
# 类型归类(据OpenD行业·Code判·须架构师核)
TYPE = {
    "US.CDNS": "成长_科技软件", "US.COHR": "成长_光通信/半导体", "US.CRDO": "成长_半导体",
    "US.KLAC": "成长_半导体设备", "US.LITE": "成长_光通信", "US.P": "成长_科技硬件",
    "US.PLTR": "成长_软件", "US.STX": "成长_存储(周期)", "US.WDC": "成长_存储(周期)",
    "US.D": "能源公用", "US.PEG": "能源公用",
    "US.GSK": "医药", "US.INCY": "医药(生物)", "US.DGX": "医疗诊断服务",
    "US.HII": "军工/国防",
}
GROWTH_BASE_GUARD = 60.0  # 净利同比>此值→PEG失真(基数/周期)·改看PE绝对


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


def judge(code, typ, pe, pb, div, g_net):
    """返回(估值模型, 关键值dict, 结论便宜/合理/明显贵, 依据, 待接标注)。阈值暂行·须架构师核。"""
    note = None
    if pe is None or pe <= 0:
        return "无法估(PE缺失/为负)", {"PE_ttm": pe}, "无法判定", "PE缺失或为负·亏损或数据缺", note
    if typ.startswith("成长") or typ == "医疗诊断服务":
        model = "成长PE/PEG"
        peg = (pe / g_net if (g_net and g_net > 0) else None)
        kv = {"PE_ttm": pe, "PB": pb, "净利同比%": g_net, "PEG(PE/净利同比)": (round(peg, 2) if peg else None)}
        if g_net is not None and g_net > GROWTH_BASE_GUARD:
            # 基数效应/周期·PEG失真·改看PE绝对
            note = f"★净利同比{g_net}%>60%·多为小基数/周期反弹→PEG失真不采信·改看PE绝对+PB(守5.5基数效应)"
            if pe > 80:
                v, why = "明显贵", f"PE_ttm {pe}高(>80)·增速虽高但基数/周期失真·PE绝对偏贵"
            elif pe > 45:
                v, why = "偏贵→合理待核", f"PE_ttm {pe}(45-80)·周期/成长·须架构师核商业模式(如存储周期高点EPS)"
            else:
                v, why = "合理", f"PE_ttm {pe}(<45)·虽基数失真但PE绝对不高"
        elif peg is not None:
            if peg < 1:
                v, why = "便宜", f"PEG {round(peg,2)}<1(PE{pe}/增{g_net}%)"
            elif peg < 1.5:
                v, why = "合理", f"PEG {round(peg,2)}(1-1.5)"
            elif peg < 2:
                v, why = "偏贵", f"PEG {round(peg,2)}(1.5-2)"
            else:
                v, why = "明显贵", f"PEG {round(peg,2)}≥2(PE{pe}/低增{g_net}%)"
        else:
            v, why = ("明显贵" if pe > 50 else "无法判定"), f"净利同比缺/≤0·PEG不可算·PE_ttm {pe}"
        return model, kv, v, why, note
    if typ == "能源公用":
        model = "股息+现金流(公用:低PE+高股息)"
        kv = {"PE_ttm": pe, "股息率%": div, "PB": pb, "净利同比%": g_net}
        note = "★真现金流估值(P/OCF·派息覆盖)待接·此处用PE+股息率代理·公用PE中枢约17"
        if div is not None and div >= 4 and pe <= 18:
            v, why = "便宜", f"股息{div}%≥4且PE{pe}≤18"
        elif (div is not None and div >= 3) and pe <= 21:
            v, why = "合理", f"股息{div}%(≥3)·PE{pe}(≤21)·近公用中枢"
        elif pe > 22:
            v, why = "偏贵", f"PE{pe}>22高于公用中枢"
        else:
            v, why = "合理", f"PE{pe}·股息{div}%·居中"
        return model, kv, v, why, note
    if typ.startswith("医药"):
        model = "DCF管线(★OpenD无管线现金流预测→用PE/PB代理·标DCF待接)"
        kv = {"PE_ttm": pe, "PB": pb, "净利同比%": g_net}
        note = "★DCF管线需分析师现金流/在研管线预测·OpenD不可得→标『DCF待接』·下为PE代理·制药PE中枢约16"
        base = (g_net is not None and g_net > GROWTH_BASE_GUARD)
        if base:
            note += f"；净利同比{g_net}%基数失真·仅看PE绝对"
        if pe < 14:
            v, why = "便宜(PE代理)", f"PE_ttm {pe}<14·低于制药中枢16"
        elif pe <= 20:
            v, why = "合理(PE代理)", f"PE_ttm {pe}(14-20)·近制药中枢"
        elif pe <= 24:
            v, why = "偏贵(PE代理)", f"PE_ttm {pe}(20-24)"
        else:
            v, why = "明显贵(PE代理)", f"PE_ttm {pe}>24"
        return model, kv, v, why, note
    if typ == "军工/国防":
        model = "防务PE中枢(约19·稳定低增)"
        kv = {"PE_ttm": pe, "PB": pb, "股息率%": div, "净利同比%": g_net}
        note = "军工低增稳定·PEG对低增标的偏严·主看PE vs防务中枢19"
        if pe < 17:
            v, why = "便宜", f"PE_ttm {pe}<17·低于防务中枢19"
        elif pe <= 22:
            v, why = "合理", f"PE_ttm {pe}(17-22)·近防务中枢"
        elif pe <= 26:
            v, why = "偏贵", f"PE_ttm {pe}(22-26)"
        else:
            v, why = "明显贵", f"PE_ttm {pe}>26"
        return model, kv, v, why, note
    return "未分类", {"PE_ttm": pe}, "无法判定", "类型未归类", note


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="20260722")
    ap.add_argument("--fin-date", default="20260721")
    a = ap.parse_args()
    d, fd = a.date, a.fin_date
    sys.stdout.reconfigure(encoding="utf-8")
    gen = now()

    g2 = json.loads((S / f"gate2_score_{d}.json").read_text(encoding="utf-8"))
    g2_time = g2.get("generated_at")
    after_g2 = (g2_time is not None and gen > g2_time)
    g2rows = g2["逐只轨迹(216)"]
    cs = json.loads((S / f"change_score_{fd}.json").read_text(encoding="utf-8"))["scores"]

    if not port_open():
        doc = {"date": d, "generated_at": gen, "FATAL": "OpenD 未连·未生产·不顶充"}
        (S / f"gate3_valuation_{d}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("OpenD未连·如实记未生产"); return 1

    import futu as ft
    ctx = ft.OpenQuoteContext("127.0.0.1", 11111)
    snap = {}
    try:
        ret, df = ctx.get_market_snapshot(POOL15)
        if ret == ft.RET_OK:
            for _, r in df.iterrows():
                snap[str(r["code"])] = {
                    "现价": (float(r["last_price"]) if r.get("last_price") not in (None, "") else None),
                    "name": r.get("name"),
                    "PE_ttm": (float(r["pe_ttm_ratio"]) if r.get("pe_ttm_ratio") not in (None, "", 0) else None),
                    "PB": (float(r["pb_ratio"]) if r.get("pb_ratio") not in (None, "") else None),
                    "股息率%": (float(r["dividend_ratio_ttm"]) if r.get("dividend_ratio_ttm") not in (None, "") else None),
                    "EPS": (float(r["earning_per_share"]) if r.get("earning_per_share") not in (None, "") else None),
                    "距52周高%": (round((float(r["last_price"]) / float(r["highest52weeks_price"]) - 1) * 100, 1)
                                if r.get("highest52weeks_price") not in (None, "", 0) else None),
                }
    finally:
        ctx.close()

    rows = {}
    for c in POOL15:
        sp = snap.get(c, {})
        typ = TYPE.get(c, "未分类")
        g_net = cs.get(c, {}).get("指标", {}).get("利润同比%")
        g_net = (round(g_net, 1) if g_net is not None else None)
        model, kv, verdict, why, note = judge(c, typ, sp.get("PE_ttm"), sp.get("PB"), sp.get("股息率%"), g_net)
        g2c = g2rows.get(c, {})
        rows[c] = {
            "code": c, "名称": sp.get("name"), "标的类型(Code判·须核)": typ,
            "逐关轨迹": {
                "第1关_激活板块": g2c.get("第1关", {}).get("结果", "?") + "·" + str(g2c.get("第1关", {}).get("激活板块")),
                "第2关_象限": g2c.get("四象限_F11", {}).get("主象限(利润为主判据)") + str(g2c.get("四象限_F11", {}).get("象限名")),
                "第2关_市场确认": g2c.get("市场确认_F12", {}).get("状态"),
                "第3关_估值": verdict,
            },
            "第3关估值": {
                "估值模型": model, "关键值": kv, "现价": sp.get("现价"), "距52周高%": sp.get("距52周高%"),
                "结论": verdict, "依据": why, "★待接/护栏": note,
                "处置": ("过(便宜/合理→进第4关护城河)" if verdict in ("便宜", "合理", "便宜(PE代理)", "合理(PE代理)")
                       else ("记下等回调(★不淘汰)" if "贵" in verdict else "需架构师核")),
            },
        }

    # 统计
    def band(v):
        if v.startswith("便宜"):
            return "便宜"
        if v.startswith("合理"):
            return "合理"
        if v == "偏贵" or v.startswith("偏贵"):
            return "偏贵"
        if "明显贵" in v:
            return "明显贵"
        return "其他/待核"
    cnt = Counter(band(rows[c]["第3关估值"]["结论"]) for c in POOL15)
    cheap_ok = [c for c in POOL15 if band(rows[c]["第3关估值"]["结论"]) in ("便宜", "合理")]
    expensive = [c for c in POOL15 if band(rows[c]["第3关估值"]["结论"]) in ("偏贵", "明显贵")]

    doc = {
        "_说明": "第3关估值(贵不贵)·真主池15只·按类型选模型·便宜合理→过·明显贵→记下等回调(不淘汰)。",
        "date": d, "generated_at": gen, "★财务(增速)数据源日": fd,
        "★倒推自检_晚于gate2": {"gate2生成时间": g2_time, "gate3生成时间": gen, "晚于gate2(顺序正确)": after_g2,
                          "结论": ("通过·第3关晚于第2关" if after_g2 else "★失败·倒推")},
        "★阈值声明": "PEG/PE中枢阈值均为教科书暂行口径·Code执行·须架构师核；类型归类为Code据OpenD行业判·须核。",
        "★方法诚实边界": ["DCF管线(医药GSK/INCY)真现金流预测OpenD不可得→用PE代理·已标『DCF待接』",
                     "公用(D/PEG)真P/OCF·派息覆盖待接→用PE+股息率代理",
                     f"净利同比>{GROWTH_BASE_GUARD}%(CRDO/INCY/STX/WDC/PLTR/COHR/GSK等)→基数/周期失真·PEG不采信·改看PE绝对(守5.5)",
                     "OpenD无forward_PE·PEG用trailing PE÷trailing净利同比·非前瞻"],
        "统计_15只": {"便宜": cnt.get("便宜", 0), "合理": cnt.get("合理", 0), "偏贵": cnt.get("偏贵", 0),
                   "明显贵": cnt.get("明显贵", 0), "其他/待核": cnt.get("其他/待核", 0)},
        "便宜或合理→过(进第4关)": sorted(cheap_ok),
        "偏贵/明显贵→记下等回调(不淘汰)": sorted(expensive),
        "逐只(15)": rows,
    }
    p = S / f"gate3_valuation_{d}.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    raw = p.read_bytes()
    try:
        json.load(open(p, encoding="utf-8")); jl = True
    except Exception as e:
        jl = False; print("★json.load失败", e)
    print("wrote", p.name, len(raw), "字节·EFBFBD=", raw.count(b"\xef\xbf\xbd"), "·json.load通过=", jl)
    print("generated_at:", gen, "· 晚于gate2:", after_g2)
    print("统计15只:", dict(cnt))
    for c in POOL15:
        r = rows[c]["第3关估值"]
        print(f"  {c.ljust(9)} {rows[c]['标的类型(Code判·须核)'].ljust(14)} 现价{r['现价']} {r['结论']}·{r['依据']}")
    print("便宜/合理→过:", len(cheap_ok), "· 偏贵/明显贵→等回调:", len(expensive))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
