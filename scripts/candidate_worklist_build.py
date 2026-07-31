#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Y2(轮61):候选研究工单(周末人工过漏斗用)。16只·只给事实与路径·★不给判断/区间/建议。
★取不到一律标『取不到·未接』·严禁估算/近似(Y2-1)。市值降序(Y2-2)。驱动组按★NEXT_TASK §一。
用法: python scripts/candidate_worklist_build.py"""
import json, futu, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-07-31"

# 16只(名称·OpenD码·驱动组按§一·市场时点)。韩股OpenD不支持→标待接
CANDS = [
    ("三星电子", "KR.005930", None, "高AI beta(存储NAND/HBM)", "07-31待接(韩股)"),
    ("SK海力士", "KR.000660", None, "高AI beta(存储NAND/HBM)", "07-31待接(韩股)"),
    ("信越化学", "JP.4063", "JP.4063", "高AI beta(半导体材料)", "07-31盘中"),
    ("ファナック", "JP.6954", "JP.6954", "高AI beta(自动化/半导体设备)", "07-31盘中"),
    ("ディスコ", "JP.6146", "JP.6146", "高AI beta(半导体设备)", "07-31盘中"),
    ("レーザーテック", "JP.6920", "JP.6920", "高AI beta(半导体设备/检测)", "07-31盘中"),
    ("東京エレクトロン", "JP.8035", "JP.8035", "高AI beta(半导体设备)", "07-31盘中"),
    ("戴尔 DELL", "US.DELL", "US.DELL", "高AI beta(AI服务器)", "07-30收盘"),
    ("台积电 TSM", "US.TSM", "US.TSM", "高AI beta(先进制程)", "07-30收盘"),
    ("Nebius NBIS", "US.NBIS", "US.NBIS", "高AI beta(AI云)", "07-30收盘"),
    ("CoreWeave CRWV", "US.CRWV", "US.CRWV", "高AI beta(AI云)", "07-30收盘"),
    ("CleanSpark CLSK", "US.CLSK", "US.CLSK", "加密beta(比特币矿)", "07-30收盘"),
    ("Riot RIOT", "US.RIOT", "US.RIOT", "加密beta(比特币矿)", "07-30收盘"),
    ("Marathon MARA", "US.MARA", "US.MARA", "加密beta(比特币矿)", "07-30收盘"),
    ("Cipher CIFR", "US.CIFR", "US.CIFR", "加密beta(比特币矿)", "07-30收盘"),
    ("IREN", "US.IREN", "US.IREN", "加密beta(比特币矿)", "07-30收盘"),
]
NA = "取不到·未接(严禁估算)"

ec = {e.get("symbol"): e for e in json.loads((ROOT / "data/valuation/earnings_calendar.json").read_text(encoding="utf-8")).get("events", [])}

q = futu.OpenQuoteContext(host="127.0.0.1", port=11111)
codes = [c[2] for c in CANDS if c[2]]
snap = {}
ret, d = q.get_market_snapshot(codes)
if ret == 0:
    for _, r in d.iterrows():
        snap[r["code"]] = {"last": r.get("last_price"), "prev": r.get("prev_close_price"),
                           "mktcap": (r.get("total_market_val") if "total_market_val" in d.columns else None)}
kl = {}
for c in codes:
    try:
        ret, k, _ = q.request_history_kline(c, start="2026-05-01", end="2026-07-31", ktype="K_DAY", max_count=70)
        if ret == 0 and len(k):
            last = k.iloc[-1]["close"]; d5 = k.iloc[-6]["close"] if len(k) >= 6 else None
            jul = k[k["time_key"] >= "2026-07-01"]
            mdd = round((jul["low"].min() / jul["high"].max() - 1) * 100, 1) if len(jul) else None
            turns = [rr["turnover"] for _, rr in k.tail(60).iterrows() if rr.get("turnover")]
            adv60 = round(sum(turns) / len(turns)) if turns else None
            kl[c] = {"chg5d": round((last / d5 - 1) * 100, 1) if d5 else None, "7月区间回撤pct": mdd, "adv60_成交额": adv60}
    except Exception:
        kl[c] = {}
q.close()

rows = []
for name, disp, code, grp, vintage in CANDS:
    s = snap.get(code, {}) if code else {}
    k = kl.get(code, {}) if code else {}
    last = s.get("last"); prev = s.get("prev")
    rows.append({
        "名称": name, "code": disp, "驱动组(§一)": grp,
        "当日价": last if last is not None else NA, "price_vintage": vintage,
        "当日涨跌pct": (round((last / prev - 1) * 100, 2) if (last and prev) else NA),
        "近5日涨跌pct": k.get("chg5d", NA) if code else NA,
        "★7月最大回撤pct": k.get("7月区间回撤pct", NA) if code else NA,
        "市值": s.get("mktcap") if s.get("mktcap") else NA,
        "60日均成交额(不用当日近似)": k.get("adv60_成交额", NA) if code else NA,
        "下一财报日": (ec.get(code, {}).get("report_date") if code and ec.get(code) else NA),
        "基本面(营收/净利同比·毛利率)": NA + "(非持仓·无机器源·须理解岗/外部接入)",
        "★可交易性_富途": NA + "(须确认)", "★可交易性_SBI": NA + "(须确认·韩股尤其)",
    })
# 市值降序(取不到置后)
rows.sort(key=lambda r: -(r["市值"] if isinstance(r["市值"], (int, float)) else -1))

out = {"_说明": "候选研究工单(Y2·轮61)。★只给事实与路径·不给判断/区间/建议(那是Opus5的活)。取不到一律标待接·严禁估算。",
       "date": DATE, "生成": DATE + " " + datetime.datetime.now().strftime("%H:%M:%S"),
       "候选数": len(rows), "数据取不到只数": sum(1 for r in rows if r["当日价"] == NA),
       "取不到清单": [r["名称"] for r in rows if r["当日价"] == NA],
       "工单(市值降序)": rows}
jp = ROOT / "data/opportunity/candidate_worklist_2026-07-31.json"
jp.parent.mkdir(parents=True, exist_ok=True)
jp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

import html as _h
def esc(x): return _h.escape(str(x))
trs = ""
for r in rows:
    trs += ("<tr><td>%s</td><td>%s</td><td>%s</td><td style='text-align:right'>%s</td><td>%s</td>"  # html-ok
            "<td style='text-align:right'>%s</td><td style='text-align:right'>%s</td><td style='text-align:right;color:#c0392b'>%s</td>"  # html-ok
            "<td style='text-align:right'>%s</td><td style='text-align:right'>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>") % (  # html-ok
        esc(r["名称"]), esc(r["code"]), esc(r["驱动组(§一)"]), esc(r["当日价"]), esc(r["price_vintage"]),
        esc(r["当日涨跌pct"]), esc(r["近5日涨跌pct"]), esc(r["★7月最大回撤pct"]), esc(r["市值"]),
        esc(r["60日均成交额(不用当日近似)"]), esc(r["下一财报日"]), esc(r["★可交易性_富途"]), esc(r["★可交易性_SBI"]))
page = ("<!doctype html><meta charset='utf-8'><title>候选研究工单 2026-07-31</title>"  # html-ok
        "<style>body{font-family:'Microsoft YaHei',sans-serif;max-width:1500px;margin:0 auto;padding:20px}"  # html-ok
        "table{border-collapse:collapse;width:100%;font-size:12px}th,td{border:1px solid #bbb;padding:4px 6px}th{background:#2c3e50;color:#fff}</style>"  # html-ok
        "<h2>候选研究工单 · 2026-07-31 · 16 只（市值降序）</h2>"  # html-ok
        "<p style='color:#c0392b'>★ 只给事实与路径·不含判断/区间/建议。取不到一律标待接·严禁估算。</p>"  # html-ok
        "<table><tr><th>名称</th><th>code</th><th>驱动组(§一)</th><th>当日价</th><th>vintage</th><th>当日涨跌%</th><th>近5日%</th>"  # html-ok
        "<th>★7月最大回撤%</th><th>市值</th><th>60日均成交额</th><th>下一财报日</th><th>可交易_富途</th><th>可交易_SBI</th></tr>" + trs + "</table>")  # html-ok
hp = ROOT / "data/opportunity/candidate_worklist_2026-07-31.html"
hp.write_text(page, encoding="utf-8")
for p in (jp, hp):
    b = p.read_bytes(); (json.loads(b.decode()) if p.suffix == ".json" else None)
    print("写", p.name, "字节", len(b), "乱码", b.count(b"\xef\xbf\xbd"))
print("候选", len(rows), "· 取不到", out["数据取不到只数"], "只:", out["取不到清单"])
