#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate3_v2 同款框架·扩到现有持仓20只（派工单H1·2026-07-22）。只读OpenD·不下单。
持仓20只(19上市+SpaceX未上市)跑双时间尺度框架:驱动分流(trailing PE机械判)+挂当日真新闻+技术背景·归因/预测栏留白给架构师(Code不代写不编造)。
数据源:PE_ttm/现价/52周高=OpenD实时;净利同比=change_score(有则取·6只不在第2关池标null待接);相对大盘=candidates_v2;新闻=data/news/daily_{date}.json。
SpaceX未上市无PE→纯未来预期驱动(标注)。带时间戳+倒推自检+json.load自检。
用法：python scripts/gate3_v2_holdings.py --date 20260722 --fin-date 20260721"""
import argparse, json, socket, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "data" / "screen"
sys.path.insert(0, str(ROOT / "scripts"))
from driver_classify import classify  # J1:标的类型优先分流(软银控股→未来/资产价值·非单一PE)
JST = timezone(timedelta(hours=9))
SPACEX_COST = 138.0


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
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="20260722")
    ap.add_argument("--fin-date", default="20260721")
    a = ap.parse_args()
    d, fd = a.date, a.fin_date
    sys.stdout.reconfigure(encoding="utf-8")
    gen = now()

    hold = json.loads((ROOT / "data/accounts/holdings_true_20260720.json").read_text(encoding="utf-8"))["holdings"]
    listed = [h for h in hold if not h["symbol"].startswith("CC.")]  # 19上市
    codes = [h["symbol"] for h in listed]
    cs = json.loads((S / f"change_score_{fd}.json").read_text(encoding="utf-8"))["scores"]
    v2 = json.loads((S / f"candidates_v2_{fd}.json").read_text(encoding="utf-8"))["cards"]
    q = json.loads((S / f"quadrant_{fd}.json").read_text(encoding="utf-8"))["cards"]
    newsf = ROOT / "data" / "news" / f"daily_{d}.json"
    news = {}; news_time = None
    if newsf.exists():
        nd = json.loads(newsf.read_text(encoding="utf-8"))
        news = nd.get("cards", {}); news_time = nd.get("generated_at")

    if not port_open():
        doc = {"date": d, "generated_at": gen, "FATAL": "OpenD未连·未生产·不顶充"}
        (S / f"gate3_v2_holdings_{d}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("OpenD未连·如实记未生产"); return 1

    import futu as ft
    ctx = ft.OpenQuoteContext("127.0.0.1", 11111)
    snap = {}
    try:
        for i in range(0, len(codes), 50):
            ret, df = ctx.get_market_snapshot(codes[i:i + 50])
            if ret == ft.RET_OK:
                for _, r in df.iterrows():
                    c = str(r["code"])
                    snap[c] = {
                        "现价": (float(r["last_price"]) if r.get("last_price") not in (None, "") else None),
                        "PE_ttm": (float(r["pe_ttm_ratio"]) if r.get("pe_ttm_ratio") not in (None, "", 0) else None),
                        "PB": (float(r["pb_ratio"]) if r.get("pb_ratio") not in (None, "") else None),
                        "距52周高%": (round((float(r["last_price"]) / float(r["highest52weeks_price"]) - 1) * 100, 1)
                                    if r.get("highest52weeks_price") not in (None, "", 0) else None),
                    }
            time.sleep(2)
    finally:
        ctx.close()

    after_news = (news_time is not None and gen > news_time)
    rows = {}
    # 19上市 + SpaceX
    all_items = [(h["symbol"], h.get("name")) for h in listed] + [("US.SPCX", "SpaceX")]
    for c, name in all_items:
        sp = snap.get(c, {})
        pe = sp.get("PE_ttm"); price = sp.get("现价"); hi52 = sp.get("距52周高%")
        g_net = cs.get(c, {}).get("指标", {}).get("利润同比%")
        in_gate2 = c in cs
        rel = ((v2.get(c, {}).get("市场先行层", {}).get("指标", {}) or {}).get("相对大盘1/3/6月%")) or {}
        ind = q.get(c, {}).get("名称行业")

        # 驱动分流(J1:标的类型优先·非单一PE)
        if c == "US.SPCX":
            price = SPACEX_COST
        cls = classify(c, pe, g_net)
        disable_trailing = cls["禁trailing判贵"]
        driver = cls["驱动"]
        driver_why = cls["依据"]
        # 成长股但PE缺失(亏损)·非特殊类→标存疑
        if cls["标的类型"] == "成长股" and pe is None and c != "US.SPCX":
            disable_trailing = True
            driver = "未来预期驱动(存疑)"
            driver_why = "成长股但OpenD无PE_ttm(亏损/缺失)·暂归未来·须架构师核"

        ncard = news.get(c, {})
        top_news = [{"标题": it.get("标题"), "链接": it.get("链接"), "发布日期": it.get("发布日期"),
                     "来源": it.get("来源"), "近3日内": it.get("近3日内")} for it in (ncard.get("新闻", []) or [])[:3]]

        block = {
            "code": c, "名称": name, "行业(参考)": ind, "现价": price,
            "在第2关财务扫描池": in_gate2,
            "驱动分流": {"结论": driver, "标的类型(Code判·须核)": cls["标的类型"], "依据": driver_why,
                     "禁trailing判贵": disable_trailing, "估值口径": cls["估值口径"], "trailing_PE": pe,
                     "净利同比%": (round(g_net, 1) if g_net is not None else None),
                     "净利同比来源": ("change_score(第2关)" if g_net is not None else "★不在第2关池或缺·待接")},
            "短期走势": {
                "①归因_挂当日真新闻": {
                    "当日新闻(真·Google News RSS)": (top_news or "当日无新闻·未编造"),
                    "技术背景(真)": {"距52周高%": hi52, "相对大盘1/3/6月%": (rel or "★不在第2关池·待接")},
                    "★归因结论": "★待架构师据上新闻+技术背景写归因·Code不代写因果",
                },
                "②预判_架构师空槽(★入库三铁律+大白话)": {
                    "方向(押·禁五五开)": "★待架构师填·概率须>55%或<45%·落45~55=五五开→拒绝入库(押方向或标『不锁』)",
                    "概率": "★待(禁45~55·铁律①)", "见分晓/PDCA核对日": "★待",
                    "★不含买卖价(铁律②)": "只判方向·买卖价/加减仓挪资金行动层",
                    "大白话四步(Q3·必填·无术语)": {"①事实": "★待", "②为什么": "★待", "③对你影响": "★待", "④怎么办/我押的": "★待"},
                    "版本链(铁律③)": "v1;更新→追加v2·原始SHA不可改·带时间戳+触发原因",
                },
            },
        }
        if disable_trailing:
            block["未来/资产驱动_估值(★trailing_PE判贵已禁用)"] = {
                "★禁用说明": f"驱动={driver}·按董事长令禁用trailing判贵·改用[{cls['估值口径']}]+未来五要素",
                "估值口径": cls["估值口径"],
                "①未来目标价": "★待架构师填(预测·Code不编造)",
                "②依据的未来事件": {"架构师填": "★待", "新闻线索(真·供参考)": [n["标题"] for n in top_news] or "当日无新闻"},
                "③兑现概率": "★待架构师填", "④见分晓时间": "★待架构师填",
                "⑤现价相对目标价位置": {"现价": price, "算法": "目标价给出后=现价/目标价-1", "现状": "待①目标价"},
            }
            block["结论"] = {"处置": f"{driver}·不以trailing PE判贵·待架构师给[目标价+未来事件+概率+见分晓时间]",
                          "★禁光秃秃": "结论须架构师补齐五要素·Code不出光秃话"}
        else:
            block["过去驱动_估值(trailing参考)"] = {"PE_ttm": pe, "PB": sp.get("PB"), "估值口径": cls["估值口径"],
                                          "说明": "稳态价值·过去基本面驱动·trailing PE有效·但持仓不出买卖建议(只标框架)·具体贵贱判定+回调价=架构师"}
            block["结论"] = {"处置": "过去基本面驱动·trailing有效", "★等到什么价/预判": "★待架构师填·凡『等』附[价+依据+多久]·不许光秃话"}

        block["注"] = "持仓(非候选)·本表只跑框架+挂真新闻+留白·不出买卖建议·预测归架构师"
        rows[c] = block

    fut = [c for c, _ in all_items if rows[c]["驱动分流"]["禁trailing判贵"] is True]
    past = [c for c, _ in all_items if rows[c]["驱动分流"]["禁trailing判贵"] is False]

    doc = {
        "_说明": "gate3_v2同款框架·扩到持仓20只(H1)。★预测(目标价/事件/概率/时间/预判/归因因果)=架构师职责·Code只机械分流+挂真新闻+留白·不编造。持仓不出买卖建议。",
        "date": d, "generated_at": gen, "★财务(增速)数据源日": fd, "★现价/PE数据源": "OpenD实时(当日)",
        "对象": "持仓20只(19上市+SpaceX未上市)·排除CC.BTC/ETH",
        "★倒推自检_晚于news": {"news": news_time, "本表": gen, "顺序正确": after_news,
                          "结论": ("通过·晚于news" if after_news else "★失败·倒推")},
        "驱动分流(J1·标的类型优先)": "先看类型:控股(软银→NAV)/加密代理(MSTR/COIN/CRCL→mNAV)/未上市/周期→禁trailing判贵;稳态价值→trailing有效;成长→PE>40判未来。类型归类见driver_classify.py·须架构师核",
        "分流结果": {"禁trailing判贵(未来/资产/周期)": fut, "过去基本面驱动(trailing有效)": past,
                 "逐只驱动": {c: rows[c]["驱动分流"]["结论"] for c, _ in all_items}},
        "6只不在第2关池(净利同比/相对大盘待接)": [c for c, _ in all_items if c not in cs and c != "US.SPCX"] + ["US.SPCX(未上市)"],
        "新闻源": f"data/news/daily_{d}.json(G2/H2·独立留档·真新闻)",
        "★预测入库三铁律+大白话(Q2/Q3·prediction_lint.py硬校验·不过不锁)": {
            "①禁五五开": "概率45~55%=骑墙→拒绝入库", "②禁买卖价/加减仓": "预测层只判方向·买卖挪资金行动层",
            "③版本链": "v1→v2追加·原始SHA不可改·带触发原因", "Q3大白话四步": "每条必含事实/为什么/对你影响/怎么办",
            "执行点": "架构师填→lock_predictions.py调prediction_lint·过才入记分卡"},
        "逐只(20)": rows,
    }
    p = S / f"gate3_v2_holdings_{d}.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    raw = p.read_bytes()
    try:
        json.load(open(p, encoding="utf-8")); jl = True
    except Exception as e:
        jl = False; print("★json.load失败", e)
    print("wrote", p.name, len(raw), "字节·EFBFBD=", raw.count(b"\xef\xbf\xbd"), "·json.load通过=", jl)
    print("generated_at:", gen, "·晚于news:", after_news, "·持仓", len(all_items), "只")
    print("未来预期驱动:", fut)
    print("过去基本面驱动:", past)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
