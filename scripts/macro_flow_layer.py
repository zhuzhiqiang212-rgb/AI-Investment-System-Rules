# -*- coding: utf-8 -*-
"""★轮77建/轮78多源重写:第③层资金流动(总闸)最小可用集。5核心(10Y/VIX/DXY/FOMC/CPI-PCE)+收益率曲线。
★轮78根因:FRED的Akamai CDN对fredgraph.csv请求特异性阻断(TCP通·HTTP read超时)·非防火墙/DNS/代理。
备用源(优先级·接通哪个用哪个·每指标记实际源·AR3-1):
  10Y/2Y:① 美国财政部官方日收益率曲线CSV(无密钥) ② Yahoo ^TNX(10Y)/^IRX;
  VIX:Yahoo ^VIX(CBOE同源) ; DXY:Yahoo DX-Y.NYB。
★接通=机器自动取到当日值(AR4-1);取不到一律标未接·严禁估算/代理冒充。输出 data/market/macro_flow_{date}.json。"""
import sys, json, argparse, urllib.request
from datetime import datetime, timezone, timedelta, date as _date
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0"}
TO = 12


def _get(url, to=TO):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=to).read().decode("utf-8", "replace")


def yahoo(sym):
    """Yahoo Finance chart → {value,prev,date,源}。失败→(None,err)。"""
    try:
        j = json.loads(_get("https://query1.finance.yahoo.com/v8/finance/chart/%s?range=5d&interval=1d" % sym))
        m = j["chart"]["result"][0]["meta"]
        val = m.get("regularMarketPrice"); prev = m.get("chartPreviousClose")
        ts = m.get("regularMarketTime")
        dstr = datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d") if ts else None
        if val is None:
            return None, "Yahoo无regularMarketPrice"
        return {"value": val, "prev": prev, "date": dstr, "源": "Yahoo Finance %s" % sym}, None
    except Exception as e:
        return None, "Yahoo %s:%s" % (sym, type(e).__name__)


def treasury_curve():
    """美国财政部官方日收益率曲线CSV(2026)→取最新一行的 2Yr/10Yr。无密钥。失败→(None,err)。"""
    url = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all"
           "?type=daily_treasury_yield_curve&field_tdr_date_value=2026&page&_format=csv")
    try:
        txt = _get(url, 15)
        lines = [l for l in txt.strip().splitlines() if l]
        hdr = [h.strip().strip('"') for h in lines[0].split(",")]
        i2 = hdr.index("2 Yr"); i10 = hdr.index("10 Yr")
        rows = []
        for l in lines[1:]:
            c = [x.strip().strip('"') for x in l.split(",")]
            if len(c) > max(i2, i10):
                try:
                    d = datetime.strptime(c[0], "%m/%d/%Y").date()
                    rows.append((d, float(c[i2]), float(c[i10])))
                except Exception:
                    pass
        if not rows:
            return None, "Treasury CSV无有效行"
        rows.sort()
        d, y2, y10 = rows[-1]
        return {"date": d.strftime("%Y-%m-%d"), "y2": y2, "y10": y10, "源": "美国财政部官方日收益率曲线CSV"}, None
    except Exception as e:
        return None, "Treasury:%s" % type(e).__name__


def fred(series):
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s" % series
    try:
        txt = _get(url, 8)
    except Exception as e:
        return None, "FRED %s 超时/阻断(Akamai对fredgraph特异阻断·TCP通HTTP不回·%s)" % (series, type(e).__name__)
    vals = []
    for r in txt.strip().splitlines()[1:]:
        d, _, v = r.partition(","); v = v.strip()
        if v and v != ".":
            try:
                vals.append((d.strip(), float(v)))
            except ValueError:
                pass
    if not vals:
        return None, "FRED返回空"
    return {"value": vals[-1][1], "prev": (vals[-2][1] if len(vals) >= 2 else None), "date": vals[-1][0], "源": "FRED %s" % series}, None


def build(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:8])
    tries = []
    tc, tc_err = treasury_curve()   # 官方10Y/2Y优先

    def indicator(name, level, fetchers, manual_baseline=None):
        """按优先级试 fetchers=[(源名,可调用)]·接通用第一个成功的·记实际源。"""
        for src_desc, fn in fetchers:
            got, err = fn()
            tries.append("%s←%s:%s" % (name, src_desc, "OK" if got else err))
            if got:
                r = {"指标": name, "蓝图": level, "接通": True, "★机器自动接通": True,
                     "当日值": got.get("value"), "前值": got.get("prev"), "数据日": got.get("date"),
                     "实际用源": got.get("源")}
                if manual_baseline is not None:
                    r["Opus5手工基线(交叉核·AR1)"] = manual_baseline
                    r["★与手工基线一致性"] = "机器%s vs 手工%s" % (got.get("value"), manual_baseline)
                return r
        r = {"指标": name, "蓝图": level, "接通": False, "★机器自动接通": False,
             "★取不到·未接": "所有源均失败(FRED阻断/其余无该指标)·严禁代理估算冒充·待接"}
        if manual_baseline is not None:
            r["Opus5手工基线(临时·AR1·非机器接入)"] = "%s·★临时基线·待机器自动接入后替换·不算已接通" % manual_baseline
        return r

    dgs10 = indicator("10年期美债收益率", "核心",
                      [("Treasury官方", lambda: (({"value": tc["y10"], "prev": None, "date": tc["date"], "源": tc["源"]}, None) if tc else (None, tc_err))),
                       ("Yahoo ^TNX", lambda: yahoo("%5ETNX")),
                       ("FRED DGS10", lambda: fred("DGS10"))], manual_baseline="4.74%")
    dgs2 = indicator("2年期美债收益率", "供收益率曲线",
                     [("Treasury官方", lambda: (({"value": tc["y2"], "prev": None, "date": tc["date"], "源": tc["源"]}, None) if tc else (None, tc_err))),
                      ("FRED DGS2", lambda: fred("DGS2"))])
    vix = indicator("VIX恐慌指数", "核心",
                    [("Yahoo ^VIX(CBOE同源)", lambda: yahoo("%5EVIX")), ("FRED VIXCLS", lambda: fred("VIXCLS"))], manual_baseline="16.81")
    dxy = indicator("DXY美元指数", "重要",
                    [("Yahoo DX-Y.NYB", lambda: yahoo("DX-Y.NYB")), ("FRED DTWEXBGS", lambda: fred("DTWEXBGS"))], manual_baseline="99.864")
    cpi = indicator("CPI", "核心", [("FRED CPIAUCSL", lambda: fred("CPIAUCSL"))])
    pce = indicator("PCE", "核心", [("FRED PCEPI", lambda: fred("PCEPI"))])
    # 收益率曲线(10Y−2Y)
    if dgs10["接通"] and dgs2["接通"]:
        sp = round(dgs10["当日值"] - dgs2["当日值"], 3)
        curve = {"指标": "美债收益率曲线(10Y−2Y)", "接通": True, "★机器自动接通": True, "利差pct": sp,
                 "是否倒挂": sp < 0, "判读": ("倒挂(衰退信号)" if sp < 0 else "正常(10Y>2Y)"), "实际用源": (tc or {}).get("源", "Treasury/Yahoo")}
    else:
        curve = {"指标": "美债收益率曲线(10Y−2Y)", "接通": False, "★机器自动接通": False, "★取不到·未接": "依赖10Y/2Y·其一未接"}
    fomc = {"指标": "FOMC决议", "蓝图": "核心", "接通": False, "★机器自动接通": False,
            "★自动源未接": "美联储官网FOMC日历/声明自动抓取未接·待接",
            "已知事实(源=FOMC声明·非估算)": {"上次决议": "2026-07-29维持利率", "票型": "9人3票主张加息",
                                        "点阵图": "有", "前瞻指引状态": "★现已取消", "下次会议日期": "待接自动日历"}}
    core = [dgs10, dgs2, vix, dxy, cpi, pce, curve, fomc]
    aq2 = [
        {"指标": "非农就业", "源": "FRED PAYEMS/BLS", "接通": False, "★机器自动接通": False, "★取不到·未接": "次轮接(FRED阻断)"},
        {"指标": "★FIMA回购动向", "蓝图": "★核心·总闸抓手", "源": "美联储H.4.1周报", "接通": False, "★机器自动接通": False,
         "★取不到·未接": "★蓝图标总闸抓手·未接·产品须显性标出不许静默省略(AQ2)·源H.4.1待接"},
        {"指标": "避险资金流(黄金/瑞郎)", "接通": False, "★机器自动接通": False, "★取不到·未接": "次轮接"},
        {"指标": "稳定币市值", "接通": False, "★机器自动接通": False, "★取不到·未接": "次轮接"},
    ]
    # ★AR4:机器自动接通计数(核心5=10Y/VIX/DXY/FOMC/CPI)
    core5 = [dgs10, vix, dxy, fomc, cpi]
    auto_core5 = sum(1 for x in core5 if x.get("★机器自动接通"))
    auto_total = sum(1 for x in (core + aq2) if x.get("★机器自动接通"))
    out = {"_说明": "★第③层资金流动(总闸)最小可用集。★轮78多源:FRED的Akamai对fredgraph特异阻断→改Treasury官方/Yahoo接通10Y/VIX/DXY/2Y·每指标记实际源。取不到标未接·严禁代理估算。",
           "date": dh, "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
           "核心指标": core, "AQ2次轮留位": aq2,
           "★接通统计": {"机器自动接通(核心5)": "%d/5" % auto_core5, "机器自动接通(全部)N/10": "%d/10" % auto_total,
                       "未接核心": [x["指标"] for x in core if not x.get("接通")]},
           "★AR4完备性(供macro_flow_gate)": {"机器自动接通核心5数": auto_core5, "★<3则标手工基线/未自动接通": auto_core5 < 3},
           "源尝试轨迹(AR3-1)": tries}
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out = build(a.date)
    p = ROOT / "data" / "market" / f"macro_flow_{a.date.replace('-', '')}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    b = p.read_bytes(); json.loads(b.decode())
    print("[macro_flow_layer] %s → %s · 乱码%d" % (a.date, p.name, b.count(b"\xef\xbf\xbd")))
    for x in out["核心指标"]:
        if x.get("接通"):
            print("  ✔ %-22s %s (源:%s)" % (x["指标"], x.get("当日值", x.get("利差pct")), x.get("实际用源")))
        else:
            print("  ✗ %-22s 取不到·未接" % x["指标"])
    print("  ★机器自动接通核心5:", out["★接通统计"]["机器自动接通(核心5)"], "· 全部:", out["★接通统计"]["机器自动接通(全部)N/10"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
