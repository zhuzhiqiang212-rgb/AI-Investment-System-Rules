# -*- coding: utf-8 -*-
"""★轮77 AQ:第③层资金流动(总闸)最小可用集。5核心指标(10Y/VIX/DXY/FOMC/CPI-PCE)+收益率曲线。
源:FRED fredgraph.csv(keyless·本网络下超时则如实标「取不到·未接」)。★严禁估算或代理值冒充(轮73 IEF代理不合格·必须真收益率)。
输出 data/market/macro_flow_{date}.json。AQ2(FIMA/非农/避险/稳定币)本轮留位标未接(FIMA显性=总闸抓手·不许静默省略)。"""
import sys, json, argparse, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 8   # 短超时·FRED不可达则快失败标未接(不干等)


def fred(series_id):
    """FRED keyless CSV → {date,value,prev} 或 None(超时/失败)。"""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    try:
        text = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=TIMEOUT).read().decode("utf-8")
    except Exception as e:
        return None, "%s:%s" % (type(e).__name__, str(e)[:40])
    vals = []
    for r in text.strip().splitlines()[1:]:
        d, _, v = r.partition(",")
        v = v.strip()
        if v and v != ".":
            try:
                vals.append((d.strip(), float(v)))
            except ValueError:
                pass
    if not vals:
        return None, "FRED返回空/无有效值"
    return {"date": vals[-1][0], "value": vals[-1][1], "prev": (vals[-2][1] if len(vals) >= 2 else None)}, None


def _ind(name, series, blueprint_level):
    got, err = fred(series)
    if got:
        return {"指标": name, "源": "FRED %s" % series, "蓝图": blueprint_level, "接通": True,
                "当日值": got["value"], "数据日": got["date"], "前值": got["prev"]}
    return {"指标": name, "源": "FRED %s" % series, "蓝图": blueprint_level, "接通": False,
            "★取不到·未接": "FRED网络超时/不可达(本网络已知·%s)→严禁代理/估算冒充·待接真源" % (err or "")}


def build(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:8])
    dgs10 = _ind("10年期美债收益率", "DGS10", "核心")
    dgs2 = _ind("2年期美债收益率", "DGS2", "供收益率曲线")
    vix = _ind("VIX恐慌指数", "VIXCLS", "核心")
    dxy = _ind("DXY美元指数(贸易加权广义)", "DTWEXBGS", "重要")
    cpi = _ind("CPI", "CPIAUCSL", "核心")
    pce = _ind("PCE", "PCEPI", "核心")
    # 收益率曲线(AQ1-6):10Y−2Y
    if dgs10["接通"] and dgs2["接通"]:
        spread = round(dgs10["当日值"] - dgs2["当日值"], 3)
        curve = {"指标": "美债收益率曲线(10Y−2Y)", "接通": True, "利差pct": spread,
                 "是否倒挂": spread < 0, "判读": ("倒挂(10Y<2Y·衰退信号)" if spread < 0 else "正常(10Y>2Y)")}
    else:
        curve = {"指标": "美债收益率曲线(10Y−2Y)", "接通": False, "★取不到·未接": "依赖 DGS10/DGS2·其一未接→曲线不成立"}
    # FOMC(AQ1-4):自动日历待接·录已知事实(源=声明·非估算)
    fomc = {"指标": "FOMC决议", "蓝图": "核心", "接通": False,
            "★自动源未接": "美联储官网FOMC日历/声明自动抓取未接(待接)",
            "已知事实(源=FOMC声明·董事长/GPT转·非估算)": {
                "上次决议": "2026-07-29 维持利率(未加息)", "票型": "9人中3票主张加息(异议3票)",
                "点阵图": "有", "前瞻指引状态": "★现已取消(不再给明确路径指引)", "下次会议日期": "待接自动日历"}}
    core = [dgs10, dgs2, vix, dxy, cpi, pce, curve, fomc]
    # AQ2 留位(标未接·FIMA显性=总闸抓手不许静默省略)
    aq2 = [
        {"指标": "非农就业", "源": "FRED PAYEMS", "接通": False, "★取不到·未接": "本轮先留位·次轮接(FRED超时)"},
        {"指标": "★FIMA回购动向", "蓝图": "★核心·总闸抓手", "源": "美联储H.4.1周报", "接通": False,
         "★取不到·未接": "★蓝图标『总闸抓手』·本轮未接·必须在产品显性标出(不许静默省略·AQ2)·源在H.4.1周报·待接"},
        {"指标": "避险资金流(黄金/瑞郎)", "接通": False, "★取不到·未接": "本轮留位·次轮接"},
        {"指标": "稳定币市值", "接通": False, "★取不到·未接": "本轮留位·次轮接"},
    ]
    n_core_connected = sum(1 for x in core if x.get("接通"))
    n_total = len(core) + len(aq2)   # 8核心相关 + 4次轮 = 12? 用"核心5+曲线+FOMC"计,统一报 N/10
    connected = sum(1 for x in (core + aq2) if x.get("接通"))
    total_slots = 10   # 蓝图最小可用集口径:10个指标位
    not_connected_core = [x["指标"] for x in core if not x.get("接通")]
    out = {"_说明": "★轮77 第③层资金流动(总闸)最小可用集。源=FRED keyless·取不到一律标未接(严禁代理/估算冒充·轮73 IEF代理不合格)。",
           "date": dh, "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
           "核心指标": core, "AQ2次轮留位": aq2,
           "★接通统计": {"核心接通数": n_core_connected, "核心总数": len(core), "接通N/10": "%d/10" % connected,
                       "未接核心": not_connected_core},
           "★资金流层完备性(供 macro_flow_gate)": {
               "核心5指标(10Y/VIX/DXY/FOMC/CPI-PCE)取不到数": sum(1 for x in [dgs10, vix, dxy, fomc, cpi] if not x.get("接通")),
               "★≥2取不到则本层判断不成立·禁下游宣激活": True},
           }
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
        v = x.get("当日值", x.get("利差pct", "—")) if x.get("接通") else "取不到·未接"
        print("  %-24s %s" % (x["指标"], v))
    print("  ★接通:", out["★接通统计"]["接通N/10"], "· 未接核心:", out["★接通统计"]["未接核心"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
