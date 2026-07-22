#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量预测生产·实时一次性扫全部35只（派工单R1·2026-07-22）。只读OpenD·不下单·当日实时扫·不用存量。
对象=20持仓(19上市+SpaceX)+15候选=35只。
Code填客观栏(当日实时):驱动分流(按类型)/当日新闻(实时·标题链接日期)/技术背景/现价。
主观栏留白给架构师:归因/押方向预判/大白话四步——走三铁律校验模板(禁五五开/禁买卖价/版本链+大白话)。
一次run内同时抓OpenD价+新闻→一个生成时间戳(不隔夜)。外部时间认证。
输出 data/forecast/batch_frame_{YYYYMMDD_HHMMSS}.json。
用法：python scripts/batch_frame.py --fin-date 20260721"""
import argparse, json, socket, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "data" / "screen"
FDIR = ROOT / "data" / "forecast"
JST = timezone(timedelta(hours=9))
sys.path.insert(0, str(ROOT / "scripts"))
from driver_classify import classify
from macro_news_intake import fetch_news
SPACEX_COST = 138.0

CAND = {"US.CDNS": "Cadence Design", "US.COHR": "Coherent", "US.CRDO": "Credo Technology",
        "US.D": "Dominion Energy", "US.DGX": "Quest Diagnostics", "US.GSK": "GSK",
        "US.HII": "Huntington Ingalls", "US.INCY": "Incyte", "US.KLAC": "KLA Corp",
        "US.LITE": "Lumentum", "US.P": "US.P stock", "US.PEG": "Public Service Enterprise",
        "US.PLTR": "Palantir", "US.STX": "Seagate", "US.WDC": "Western Digital"}
EN = dict(CAND)
EN.update({"US.NVDA": "Nvidia", "US.MSFT": "Microsoft", "US.MSTR": "Strategy MicroStrategy",
           "US.COIN": "Coinbase", "US.AVGO": "Broadcom", "US.CRCL": "Circle stock", "US.SNDK": "SanDisk",
           "US.TSM": "TSMC", "US.META": "Meta Platforms", "US.IBKR": "Interactive Brokers", "US.SPCX": "SpaceX"})

SUBJ_SLOT = {
    "归因_当前为何这样走": "★待架构师填(据下方真新闻+技术背景·事实与推论分开)",
    "短期预判_押方向(★三铁律)": {
        "方向": "★待架构师填:偏反弹/偏回调/偏上行… 禁五五开(概率>55或<45·否则拒入库或标『不锁』)",
        "概率": "★待(禁45~55·铁律①)", "见分晓/PDCA核对日": "★待",
        "★不含买卖价(铁律②)": "只判方向·买卖价/加减仓挪资金行动层",
    },
    "长期预判_押方向(★三铁律)": {"方向": "★待", "依据未来事件": "★待", "见分晓/PDCA核对日": "★待"},
    "大白话四步(Q3·必填·无术语)": {"①事实": "★待", "②为什么": "★待", "③对你影响": "★待", "④怎么办/我押的": "★待"},
    "版本链(铁律③)": "v1;更新→追加v2·原始SHA不可改·带时间戳+触发原因",
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
    ap = argparse.ArgumentParser(); ap.add_argument("--fin-date", default="20260721"); a = ap.parse_args()
    fd = a.fin_date
    sys.stdout.reconfigure(encoding="utf-8")
    gen_dt = datetime.now(JST)
    gen = gen_dt.isoformat(timespec="seconds")
    stamp = gen_dt.strftime("%Y%m%d_%H%M%S")

    hold = json.loads((ROOT / "data/accounts/holdings_true_20260720.json").read_text(encoding="utf-8"))["holdings"]
    listed = [(h["symbol"], h.get("name")) for h in hold if not h["symbol"].startswith("CC.")]
    targets = {}
    for c, nm in listed:
        targets[c] = {"名称": nm, "类别": "持仓"}
    targets["US.SPCX"] = {"名称": "SpaceX", "类别": "持仓(未上市)"}
    for c, nm in CAND.items():
        targets[c] = {"名称": nm, "类别": ("持仓+候选" if c in targets else "候选")}
    codes_listed = [c for c in targets if c != "US.SPCX"]

    cs = json.loads((S / f"change_score_{fd}.json").read_text(encoding="utf-8"))["scores"]
    v2 = json.loads((S / f"candidates_v2_{fd}.json").read_text(encoding="utf-8"))["cards"]
    q = json.loads((S / f"quadrant_{fd}.json").read_text(encoding="utf-8"))["cards"]

    if not port_open():
        (FDIR / f"batch_frame_{stamp}.json").parent.mkdir(parents=True, exist_ok=True)
        (FDIR / f"batch_frame_{stamp}.json").write_text(json.dumps({"FATAL": "OpenD未连·未生产·不顶充", "generated_at": gen}, ensure_ascii=False, indent=1), encoding="utf-8")
        print("OpenD未连·如实记未生产"); return 1

    import futu as ft
    from forecast_lock import external_time
    ctx = ft.OpenQuoteContext("127.0.0.1", 11111)
    snap = {}
    try:
        for i in range(0, len(codes_listed), 50):
            ret, df = ctx.get_market_snapshot(codes_listed[i:i + 50])
            if ret == ft.RET_OK:
                for _, r in df.iterrows():
                    c = str(r["code"])
                    lp = (float(r["last_price"]) if r.get("last_price") not in (None, "") else None)
                    snap[c] = {"现价": lp,
                               "PE_ttm": (float(r["pe_ttm_ratio"]) if r.get("pe_ttm_ratio") not in (None, "", 0) else None),
                               "PB": (float(r["pb_ratio"]) if r.get("pb_ratio") not in (None, "") else None),
                               "距52周高%": (round((lp / float(r["highest52weeks_price"]) - 1) * 100, 1)
                                           if (lp and r.get("highest52weeks_price") not in (None, "", 0)) else None)}
            time.sleep(2)
    finally:
        ctx.close()
    et = external_time()

    rows = {}
    no_news = []
    for c, meta in targets.items():
        sp = snap.get(c, {})
        pe = sp.get("PE_ttm"); price = (SPACEX_COST if c == "US.SPCX" else sp.get("现价"))
        g_net = cs.get(c, {}).get("指标", {}).get("利润同比%")
        rel = ((v2.get(c, {}).get("市场先行层", {}).get("指标", {}) or {}).get("相对大盘1/3/6月%")) or {}
        cls = classify(c, pe, g_net)
        # 当日新闻(实时·本run抓)
        try:
            items = fetch_news(str(EN.get(c) or meta["名称"] or c), limit=3, lang=("en" if c.startswith("US.") else "zh"))
        except Exception:
            items = None
        news = [{"标题": it.get("title"), "链接": it.get("url"), "发布日期": it.get("pub_date"), "来源": it.get("source_raw")}
                for it in (items or [])[:3]]
        if not news:
            no_news.append(c)
        rows[c] = {
            "code": c, "名称": meta["名称"], "类别": meta["类别"],
            "★客观栏(Code填·当日实时)": {
                "驱动分流": {"标的类型(Code判·须核)": cls["标的类型"], "驱动": cls["驱动"],
                          "禁trailing判贵": cls["禁trailing判贵"], "估值口径": cls["估值口径"], "依据": cls["依据"]},
                "当日新闻(实时·标题链接日期)": (news or "当日无新闻·未编造"),
                "技术背景": {"现价": price, "trailing_PE": pe, "PB": sp.get("PB"), "距52周高%": sp.get("距52周高%"),
                          "相对大盘1/3/6月%": (rel or "★不在第2关池·待接"),
                          "净利同比%": (round(g_net, 1) if g_net is not None else None)},
            },
            "★主观栏(架构师填·留白·走三铁律模板)": SUBJ_SLOT,
        }

    doc = {
        "_说明": "全量预测生产·实时一次性扫35只(R1)。Code填客观栏(当日实时:驱动/新闻/技术/现价)·主观栏(归因/押方向/大白话)留白给架构师·走三铁律校验(prediction_lint)。",
        "★生成时间戳": gen, "文件戳": stamp, "外部权威时间(Google HTTP Date)": et.get("iso"), "时间源": et.get("source"),
        "★数据新鲜度": "OpenD价/PE + 新闻 均本run当日实时抓·不用存量·不隔夜",
        "对象": {"总数": len(targets), "持仓": 20, "候选": 15, "上市实扫": len(codes_listed), "未上市": ["US.SPCX(按成本$138)"]},
        "无新闻标的": no_news,
        "三铁律校验就位": {"校验器": "scripts/prediction_lint.py", "锁定闸": "scripts/lock_predictions.py",
                     "① 禁五五开(概率45~55拒入库)": "就位", "② 禁买卖价/加减仓(挪资金行动层)": "就位",
                     "③ 版本链(v1→v2追加·原始SHA不可改)": "就位", "Q3 大白话四步": "就位"},
        "下一步(R2)": "架构师同批次填主观(押方向不五五开/无买卖价/大白话)→Code跑 lock_predictions.py 过校验后一次性forecast_lock整批(v版本链)·全程当日数据不隔夜",
        "逐只(35)": rows,
    }
    FDIR.mkdir(parents=True, exist_ok=True)
    p = FDIR / f"batch_frame_{stamp}.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    raw = p.read_bytes()
    try:
        json.load(open(p, encoding="utf-8")); jl = True
    except Exception as e:
        jl = False; print("★json.load失败", e)
    print("wrote", p.name, len(raw), "字节·EFBFBD=", raw.count(b"\xef\xbf\xbd"), "·json.load通过=", jl)
    print("扫描", len(targets), "只(上市实扫", len(codes_listed), "+SpaceX)·无新闻", len(no_news), no_news)
    print("★生成时间戳:", gen, "·外部认证:", et.get("iso"))
    print("三铁律校验就位: ①禁五五开 ②禁买卖价 ③版本链 +Q3大白话 · 校验器 prediction_lint.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
