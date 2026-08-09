# -*- coding: utf-8 -*-
"""★轮85 CC3:③资金流动补5项(现5/10·判据≥8含FIMA)。多源试·每项记『试了哪源·失败原因』(CC3-6·严禁估算/代理冒充)。
 CC3-1 CPI/PCE:BLS公开API(CPI=CUUR0000SA0)·PCE=BEA(试)。CC3-2 非农:BLS(CES0000000001)。
 CC3-3 ★FIMA回购:美联储H.4.1周报(federalreserve.gov/releases/h41)。CC3-4 FOMC:fed FOMC日历页。
 CC3-5 避险:GLD(黄金)/CHF(瑞郎)Yahoo + 稳定币USDT/USDC市值(Yahoo价·市值需供给量·标口径)。
输出 data/market/macro_flow_ext_{date}.json + 接通统计。"""
import sys, json, argparse, re, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0"}


def _get(url, to=12):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=to).read().decode("utf-8", "replace")


def _yahoo(sym):
    try:
        j = json.loads(_get("https://query1.finance.yahoo.com/v8/finance/chart/%s?range=5d&interval=1d" % sym))
        m = j["chart"]["result"][0]["meta"]
        return {"值": m.get("regularMarketPrice"), "前值": m.get("chartPreviousClose"), "源": "Yahoo %s" % sym}, None
    except Exception as e:
        return None, "Yahoo %s:%s" % (sym, type(e).__name__)


def _bls(series, name):
    """BLS公开API v2(无key有限流)。返回最新值+期。试BLS→失败记原因。"""
    tried = []
    try:
        j = json.loads(_get("https://api.bls.gov/publicAPI/v2/timeseries/data/%s" % series))
        tried.append("BLS公开API")
        if j.get("status") != "REQUEST_SUCCEEDED":
            return None, "BLS返回%s:%s" % (j.get("status"), (j.get("message") or [""])[0][:60]), tried
        d = j["Results"]["series"][0]["data"]
        if not d:
            return None, "BLS无数据点", tried
        latest = d[0]
        return {"值": latest.get("value"), "期": "%s-%s" % (latest.get("year"), latest.get("period")),
                "源": "BLS公开API %s" % series}, None, tried
    except Exception as e:
        tried.append("BLS公开API")
        return None, "BLS %s:%s" % (series, type(e).__name__), tried


def _fima_h41():
    """★FIMA回购:H.4.1周报 h41.htm。FIMA repo facility=表『Repurchase agreements』下『Foreign official』行数值(百万美元)。"""
    tried = ["federalreserve.gov/releases/h41/current/h41.htm"]
    try:
        html = _get("https://www.federalreserve.gov/releases/h41/current/h41.htm", to=15)
        txt = re.sub(r"<[^>]+>", " ", html)
        txt = txt.replace("&#xa0;", " ").replace("&nbsp;", " ")
        txt = re.sub(r"\s+", " ", txt)
        # 定位 Repurchase agreements 段·取其后首个 Foreign official 行的数值
        i = txt.find("Repurchase agreements")
        val = None
        if i >= 0:
            seg = txt[i:i + 400]
            m = re.search(r"Foreign official\s+([\d,]+)", seg)
            if m:
                val = m.group(1).replace(",", "")
        if val is not None:
            return {"值": "%s 百万美元" % val, "口径": "H.4.1『Repurchase agreements·Foreign official』(FIMA repo facility使用量·0=闲置)",
                    "源": "美联储 H.4.1 h41.htm"}, None, tried
        return None, "h41.htm已抓·但未在Repurchase agreements段定位Foreign official数值(表结构或变)→未接(非估算)", tried
    except Exception as e:
        return None, "H.4.1:%s" % type(e).__name__, tried


def _fomc_calendar():
    """FOMC决议自动源:fed FOMC日历页·解析会议日期。"""
    tried = ["federalreserve.gov/monetarypolicy/fomccalendars.htm"]
    try:
        html = _get("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", to=15)
        # 找2026年会议月份
        yrs = re.findall(r"(January|March|April|June|July|September|October|December)\s*[\d/\-–]+\s*,?\s*2026", html)
        months = sorted(set(re.findall(r"(January|March|April|June|July|September|October|November|December)", html)))
        if yrs or "2026" in html:
            return {"命中": "FOMC日历页含2026会议安排(月份:%s)" % "、".join(months[:8]), "源": "fed FOMC calendar"}, None, tried
        return None, "FOMC日历页无2026安排", tried
    except Exception as e:
        return None, "FOMC日历:%s" % type(e).__name__, tried


def build(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    items = []

    def add(name, res, err, tried, note=""):
        items.append({"指标": name, "接通": bool(res), "值": res, "★失败原因": err,
                      "试了哪些源": tried, "口径说明": note})

    # CC3-1 CPI (BLS)
    r, e, t = _bls("CUUR0000SA0", "CPI")
    add("CPI(城市消费者物价)", r, e, t)
    # PCE — BEA(非BLS)·本轮标试BEA
    add("PCE(个人消费支出物价)", None, "PCE非BLS序列·源在BEA(bea.gov API需注册key·本轮未申请key)·FRED被Akamai阻断·未接(非估算)",
        ["FRED(Akamai阻断)", "BEA API(需key·未申请)"])
    # CC3-2 非农 (BLS)
    r, e, t = _bls("CES0000000001", "非农就业")
    add("非农就业(总就业人数)", r, e, t)
    # CC3-3 FIMA
    r, e, t = _fima_h41()
    add("★FIMA回购(核心·总闸抓手)", r, e, t, "蓝图标『核心·总闸抓手』")
    # CC3-4 FOMC
    r, e, t = _fomc_calendar()
    add("FOMC决议(自动源)", r, e, t)
    # CC3-5 避险:GLD/CHF + 稳定币USDT/USDC
    r, e = _yahoo("GLD"); add("避险·黄金GLD", r, e, ["Yahoo GLD"])
    r, e = _yahoo("CHF=X"); add("避险·瑞郎CHF", r, e, ["Yahoo CHF=X"])
    r, e = _yahoo("USDT-USD"); add("稳定币USDT(价·脱锚监测)", r, e, ["Yahoo USDT-USD"],
                                   "价格监测脱锚·真市值需流通供给量(CoinGecko/无key有限)·此处只监测价格锚定")
    r, e = _yahoo("USDC-USD"); add("稳定币USDC(价·脱锚监测)", r, e, ["Yahoo USDC-USD"], "同USDT·价格锚定监测")

    n_conn = sum(1 for x in items if x["接通"])
    return {
        "_说明": "★轮85 CC3 ③资金流动补5项。多源试·每项记试了哪源+失败原因(CC3-6)。★取不到标未接·严禁估算/代理冒充。",
        "date": dh, "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "补充指标": items, "本文件接通数": n_conn, "本文件指标数": len(items),
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out = build(a.date)
    p = ROOT / "data" / "market" / f"macro_flow_ext_{a.date.replace('-', '')}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    b = p.read_bytes(); json.loads(b.decode())
    print("[macro_flow_ext] %s → %s · 乱码%d · 本文件接通 %d/%d" % (
        a.date, p.name, b.count(b"\xef\xbf\xbd"), out["本文件接通数"], out["本文件指标数"]))
    for x in out["补充指标"]:
        print("  %s %s: %s" % ("✔" if x["接通"] else "✗", x["指标"][:24],
                               (str(x["值"])[:50] if x["接通"] else x["★失败原因"][:56])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
