# -*- coding: utf-8 -*-
"""★轮73 AL2:宏观层数据源(latest_market_snapshot 停07-22·根本缺)。当日抓能抓的、取不到的一律标「取不到·未接」(AL2-5)。
接:SOXX(费城半导体·US.SOXX)、10Y国债方向代理(US.IEF 7-10Y国债ETF·价涨=收益率降=边际松)、TLT(20Y)、USDJPY(日元)。
未接(如实标·不沿用旧事件冒充当日·AL2-5):US10Y真收益率(OpenD无TNX)、FOMC/美元流动性事件、日银决议、日债收益率。
输出 data/market/latest_market_snapshot.json(by_symbol + macro_layer 完备性标记)。"""
import sys, json, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent

# 能抓的代理(OpenD)·与未接项
PROXY = {"US.SOXX": "SOXX_费城半导体", "US.IEF": "IEF_7-10Y国债ETF(10Y方向代理)",
         "US.TLT": "TLT_20Y国债ETF", "US.SPY": "SPY_标普500"}
NOT_CONNECTED = {
    "US10Y_真收益率": "OpenD无TNX/^TNX·真10年期收益率待接FRED(DGS10)/美国财政部;当前用 IEF 价格方向代理(价涨=收益率降=边际松)",
    "FOMC_美元_流动性事件": "无当日事件源·待接经济日历(FOMC日程/点阵图/资产负债表)——★不沿用06-01旧事件冒充当日(AL2-5)",
    "日银_决议": "无日银(BOJ)决议/YCC/购债事件源·待接日银公告日历",
    "日债_10Y收益率": "OpenD无日债收益率·待接JGB源",
}


def fetch(codes):
    try:
        from realtime_price import connect_quote_context
        from futu import RET_OK
    except Exception as e:
        return {}, "futu导入失败:%s" % e
    ctx, att = connect_quote_context(max_retries=2, wait_seconds=2)
    if ctx is None:
        return {}, "OpenD连接失败:%s" % att
    out = {}
    try:
        ret, data = ctx.get_market_snapshot(codes)
        if ret == RET_OK:
            for r in data.to_dict("records"):
                lp, pc = r.get("last_price"), r.get("prev_close_price")
                chg = round((lp - pc) / pc * 100, 3) if (isinstance(lp, (int, float)) and isinstance(pc, (int, float)) and pc) else None
                out[r.get("code")] = {"last_price": lp, "prev_close_price": pc, "change_percent": chg,
                                      "update_time": r.get("update_time")}
    finally:
        try: ctx.close()
        except Exception: pass
    return out, None


def build(date):
    px, err = fetch(list(PROXY.keys()))
    # USDJPY 从当日 daily_scan 取(真值·沿用标记)
    usdjpy = None
    try:
        sc = json.loads((ROOT / "data/market" / f"daily_scan_{date}.json").read_text(encoding="utf-8"))
        usdjpy = sc["items"]["5_USDJPY"]
    except Exception:
        pass
    by_symbol = {}
    for code, name in PROXY.items():
        q = px.get(code)
        if q and q.get("last_price") is not None:
            by_symbol[name.split("_")[0]] = {"code": code, "名称": name, **q, "present": True}
    # ★AL2-1:US10Y 无真收益率→用 IEF 方向代理·显式标未接真源
    ief = by_symbol.get("IEF")
    by_symbol["US10Y"] = ({"present": False, "★取不到·未接": NOT_CONNECTED["US10Y_真收益率"],
                           "方向代理_IEF价change": (ief or {}).get("change_percent"),
                           "方向": ("边际松(国债价涨→收益率降)" if (ief and (ief.get("change_percent") or 0) > 0.1)
                                    else ("偏紧(国债价跌→收益率升)" if (ief and (ief.get("change_percent") or 0) < -0.1) else "中性/待接真源"))})
    out = {
        "_说明": "★轮73 AL2 宏观层快照。能抓的抓真值(SOXX/国债ETF/USDJPY)·取不到的一律标『取不到·未接』(AL2-5)·不沿用旧事件冒充当日。",
        "date": date, "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "by_symbol": by_symbol,
        "usdjpy": usdjpy,
        "★未接项(如实·待接真源)": NOT_CONNECTED,
        "fetch_err": err,
        # ★AL2-6 完备性:关键宏观字段是否闭合(供 macro_completeness_gate + 渲染层判"该层能不能宣激活")
        "macro_completeness": {
            "SOXX_present": "SOXX" in by_symbol,
            "US10Y真收益率_present": False,   # 未接
            "FOMC事件_present": False,        # 未接
            "日银_present": False,            # 未接
            "日债_present": False,            # 未接
            "★结论": "宏观层不闭合(US10Y真收益率/FOMC/日银/日债 未接)→ 板块激活证据链不闭合·不许宣布板块激活(AL2-6/GPT第5条)",
        },
    }
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out = build(a.date)
    p = ROOT / "data" / "market" / "latest_market_snapshot.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    b = p.read_bytes(); json.loads(b.decode())
    print("[market_macro_snapshot] %s → %s · 乱码%d" % (a.date, p.name, b.count(b"\xef\xbf\xbd")))
    print("  抓到真值:", [k for k, v in out["by_symbol"].items() if v.get("present")])
    print("  未接(如实标):", list(NOT_CONNECTED.keys()))
    print("  ★宏观完备性:", out["macro_completeness"]["★结论"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
