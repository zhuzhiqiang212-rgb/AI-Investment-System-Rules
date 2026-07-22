#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第3关·v2·双时间尺度预判（派工单G1·2026-07-22·董事长已核方向）。对真主池15只。
★分工铁律:预测(目标价/未来事件/兑现概率/见分晓时间/短期预判/见顶到什么位多久)=架构师职责·记分卡记的是『架构师预测胜率』(见G3)。
  Code只:①据真数据机械分流驱动②挂真当日新闻做短期归因(防编造)③给架构师预测的结构化空槽④目标价给出后机械算相对位置。
  ★Code绝不编造目标价/事件/概率/预判——空槽标『待架构师填』。
每只输出:
 - 驱动分流:过去基本面 or 未来预期驱动(据trailing PE水平机械判)
 - 未来驱动的:禁用trailing PE判贵·给①目标价②未来事件③兑现概率④见分晓时间⑤现价相对目标价位置(空槽+新闻线索)
 - 短期走势:①归因(挂当日真新闻)②预判(架构师空槽)
 - 结论:禁止光秃秃『贵/等回调』·凡『等』必附[等到什么价+依据+多久](future=架构师补;past=trailing数据可给)
带时间戳+倒推自检(晚于gate3&news)+json.load自检。
用法：python scripts/gate3_v2.py --date 20260722 --fin-date 20260721"""
import argparse, json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "data" / "screen"
sys.path.insert(0, str(ROOT / "scripts"))
from driver_classify import classify  # J1:标的类型优先分流(别再单一PE阈值)
JST = timezone(timedelta(hours=9))


def now():
    return datetime.now(JST).isoformat(timespec="seconds")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="20260722")
    ap.add_argument("--fin-date", default="20260721")
    a = ap.parse_args()
    d, fd = a.date, a.fin_date
    sys.stdout.reconfigure(encoding="utf-8")
    gen = now()

    g3 = json.loads((S / f"gate3_valuation_{d}.json").read_text(encoding="utf-8"))
    g3_time = g3.get("generated_at")
    g3rows = g3["逐只(15)"]
    cs = json.loads((S / f"change_score_{fd}.json").read_text(encoding="utf-8"))["scores"]
    v2 = json.loads((S / f"candidates_v2_{fd}.json").read_text(encoding="utf-8"))["cards"]
    newsf = ROOT / "data" / "news" / f"daily_{d}.json"
    news = {}
    news_time = None
    if newsf.exists():
        nd = json.loads(newsf.read_text(encoding="utf-8"))
        news = nd.get("cards", {}); news_time = nd.get("generated_at")
    after_g3 = (g3_time is not None and gen > g3_time)
    after_news = (news_time is not None and gen > news_time)

    POOL15 = list(g3rows.keys())
    rows = {}
    for c in POOL15:
        g3c = g3rows[c]
        v3 = g3c.get("第3关估值", {})
        typ = g3c.get("标的类型(Code判·须核)")
        pe = (v3.get("关键值", {}) or {}).get("PE_ttm")
        price = v3.get("现价")
        g_net = cs.get(c, {}).get("指标", {}).get("利润同比%")
        rel = ((v2.get(c, {}).get("市场先行层", {}).get("指标", {}) or {}).get("相对大盘1/3/6月%")) or {}
        hi52 = v3.get("距52周高%")

        # ── 驱动分流(J1:标的类型优先·非单一PE)──
        cls = classify(c, pe, g_net)
        disable_trailing = cls["禁trailing判贵"]
        driver = cls["驱动"]
        driver_why = cls["依据"]

        # ── 短期新闻(真·挂链接)──
        ncard = news.get(c, {})
        top_news = []
        for it in (ncard.get("新闻", []) or [])[:3]:
            top_news.append({"标题": it.get("标题"), "链接": it.get("链接"), "发布日期": it.get("发布日期"),
                             "来源": it.get("来源"), "近3日内": it.get("近3日内")})

        block = {
            "code": c, "名称": g3c.get("名称"), "标的类型(Code判·须核)": typ, "现价": price,
            "驱动分流": {"结论": driver, "标的类型(Code判·须核)": cls["标的类型"], "依据": driver_why,
                     "禁trailing判贵": disable_trailing, "估值口径": cls["估值口径"],
                     "trailing_PE": pe, "净利同比%": (round(g_net, 1) if g_net is not None else None)},
            "短期走势": {
                "①归因_挂当日真新闻": {
                    "当日新闻(真·Google News RSS)": (top_news or "当日无新闻·未编造"),
                    "技术背景(真)": {"距52周高%": hi52, "相对大盘1/3/6月%": rel},
                    "★归因结论": "★待架构师据上新闻+技术背景写归因(为何今日这样走)·Code不代写因果",
                },
                "②预判_架构师空槽(★入库三铁律+大白话)": {
                    "方向(押·禁五五开)": "★待架构师填:偏反弹/偏回调/偏上行… 概率须>55%或<45%·落45~55=五五开→拒绝入库(要么押方向要么标『不锁』)",
                    "概率": "★待(禁45~55·铁律①)",
                    "见分晓/PDCA核对日": "★待",
                    "★不含买卖价(铁律②)": "只判方向·具体买卖价/加减仓挪到资金行动层·预测层不出",
                    "大白话四步(Q3·必填·无术语)": {"①事实": "★待", "②为什么": "★待", "③对你影响": "★待", "④怎么办/我押的": "★待"},
                    "版本链(铁律③)": "v1;更新→追加v2·原始SHA不可改·带时间戳+触发原因",
                },
            },
        }

        if disable_trailing:
            block["未来/资产驱动_估值(★trailing_PE判贵已禁用)"] = {
                "★禁用说明": f"驱动={driver}·按董事长令禁用trailing PE判『贵』·改用[{cls['估值口径']}]+未来五要素",
                "估值口径": cls["估值口径"],
                "①未来目标价": "★待架构师填(预测·Code不编造)",
                "②依据的未来事件": {"架构师填": "★待",
                                "新闻线索(真·供架构师参考·非结论)": [n["标题"] for n in top_news] or "当日无新闻"},
                "③兑现概率": "★待架构师填",
                "④见分晓时间": "★待架构师填",
                "⑤现价相对目标价位置": {"现价": price, "算法": "目标价给出后=现价/目标价-1", "现状": "待①目标价"},
            }
            block["结论"] = {"处置": "未来驱动·不以trailing PE判贵·待架构师给[目标价+未来事件+概率+见分晓时间]",
                          "★禁光秃秃": "本只结论必须由架构师补齐五要素·Code不出『贵/等回调』光秃话"}
        else:
            # 过去基本面驱动:trailing估值有效·可给数据结论·但『等』仍需附价+依据+多久
            tv = v3.get("结论")
            block["过去驱动_估值(trailing有效)"] = {
                "trailing估值结论": tv, "依据": v3.get("依据"), "PE_ttm": pe, "估值模型": v3.get("估值模型"),
            }
            if tv and ("贵" in str(tv)):
                block["结论"] = {"处置": "等回调", "★等到什么价": "★待架构师给回调目标价(trailing偏贵·但具体等到多少=预测)",
                              "依据": v3.get("依据"), "★多久": "★待架构师填", "★禁光秃秃": "『等』已附依据·价与时限待架构师补"}
            else:
                block["结论"] = {"处置": "过(便宜/合理·trailing支撑)", "依据": v3.get("依据"),
                              "说明": "过去基本面驱动+trailing便宜/合理→进第4关(非光秃话·附trailing依据)"}

        block["逐关轨迹"] = {
            "第1关": g3c.get("逐关轨迹", {}).get("第1关_激活板块"),
            "第2关_象限": g3c.get("逐关轨迹", {}).get("第2关_象限"),
            "第2关_市场确认": g3c.get("逐关轨迹", {}).get("第2关_市场确认"),
            "第3关_驱动": driver,
        }
        rows[c] = block

    fut = [c for c in POOL15 if rows[c]["驱动分流"]["禁trailing判贵"] is True]
    past = [c for c in POOL15 if rows[c]["驱动分流"]["禁trailing判贵"] is False]

    doc = {
        "_说明": "第3关v2·双时间尺度预判。★预测(目标价/事件/概率/时间/预判)=架构师职责(记分卡记其胜率·见G3)·Code只机械分流+挂真新闻+给空槽+算相对位置·不编造预测。",
        "date": d, "generated_at": gen, "★财务(增速)数据源日": fd,
        "★倒推自检": {"晚于gate3": {"gate3": g3_time, "gate3_v2": gen, "顺序正确": after_g3},
                  "晚于news": {"news": news_time, "gate3_v2": gen, "顺序正确": after_news},
                  "结论": ("通过·晚于gate3与news" if (after_g3 and after_news) else "★失败·倒推")},
        "驱动分流(J1·标的类型优先)": "先看类型:控股/加密代理/未上市/周期→禁trailing判贵;稳态价值→trailing有效;成长→PE>40判未来。类型归类见driver_classify.py·须架构师核",
        "分流结果": {"禁trailing判贵(未来/资产/周期)": fut, "过去基本面驱动(trailing有效)": past,
                 "逐只驱动": {c: rows[c]["驱动分流"]["结论"] for c in POOL15}},
        "★交给架构师填的空槽清单": {
            "未来驱动每只(共%d只)" % len(fut): ["①未来目标价", "②依据的未来事件", "③兑现概率", "④见分晓时间"],
            "每只短期": ["短期归因结论(据挂好的真新闻)", "短期预判(回调/主升/见顶+位+时)"],
            "过去驱动偏贵的": ["回调等到什么价", "多久"],
        },
        "新闻源": "data/news/daily_%s.json(G2·Google News RSS真新闻)" % d,
        "★预测入库三铁律+大白话(Q2/Q3·prediction_lint.py硬校验·不过不锁)": {
            "①禁五五开": "概率落45~55%=骑墙→拒绝入库(押方向或标『不锁』)",
            "②禁买卖价/加减仓": "预测层只判方向·具体买卖价与加减仓挪到资金行动层",
            "③版本链": "v1→v2追加·原始SHA不可改·更新带时间戳+触发原因",
            "Q3大白话四步": "每条必含 事实/为什么/对你影响/怎么办(无术语)",
            "执行点": "架构师填→lock_predictions.py调prediction_lint校验→过才forecast_lock入记分卡",
        },
        "逐只(15)": rows,
    }
    p = S / f"gate3_v2_{d}.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    raw = p.read_bytes()
    try:
        json.load(open(p, encoding="utf-8")); jl = True
    except Exception as e:
        jl = False; print("★json.load失败", e)
    print("wrote", p.name, len(raw), "字节·EFBFBD=", raw.count(b"\xef\xbf\xbd"), "·json.load通过=", jl)
    print("generated_at:", gen, "·晚于gate3:", after_g3, "·晚于news:", after_news)
    print("未来预期驱动(禁trailing判贵):", fut)
    print("过去基本面驱动(trailing有效):", past)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
