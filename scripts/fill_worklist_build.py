#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
fill_worklist_build.py —— N3(轮50):给 Opus5 出「预测填报工单」。
对【尚未填预测的持仓】逐只列客观事实(代码/名称/账户/股数/当日价+vintage/权重/锚+priced_at+锚龄/
review_due命中+类型/blind/证据文件路径/下一事件日)·按权重降序·输出 JSON + 同名 HTML。
★N3-3:表里不许出现任何建议/判断/情景/概率——只给事实与路径(那是 Opus5 的活)。
用法: python scripts/fill_worklist_build.py --date 2026-07-30
"""
import argparse, json, sys, datetime, html
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def _age_days(today, d):
    try:
        return (today - datetime.date(int(d[:4]), int(d[5:7]), int(d[8:10]))).days
    except Exception:
        return None


def build(date_h):
    dc = date_h.replace("-", "")
    today = datetime.date(int(date_h[:4]), int(date_h[5:7]), int(date_h[8:10]))
    tg = json.loads((ROOT / "data/target" / f"target_gap_{dc}.json").read_text(encoding="utf-8"))
    fc = json.loads((ROOT / "data/forecast" / f"forecast_{date_h}.json").read_text(encoding="utf-8"))
    have = {(f.get("account"), f.get("ticker")) for f in fc.get("forecasts", [])}
    _acc = {"FUTU": "富途", "SBI": "SBI"}
    have_cn = {(_acc.get(a, a), t) for a, t in have}

    vi = json.loads((ROOT / "data/valuation/val_inputs.json").read_text(encoding="utf-8")).get("holdings", {})
    rd = {}
    rdp = ROOT / "data/valuation" / f"review_due_{dc}.json"
    if rdp.exists():
        for d in json.loads(rdp.read_text(encoding="utf-8")).get("详情", []):
            rd[d.get("code")] = d
    ec = json.loads((ROOT / "data/valuation/earnings_calendar.json").read_text(encoding="utf-8")).get("events", [])
    next_ev = {}
    for e in ec:
        rdte = e.get("report_date", "")
        if rdte and rdte >= date_h:
            s = e.get("symbol")
            if s not in next_ev or rdte < next_ev[s]["report_date"]:
                next_ev[s] = {"report_date": rdte, "fiscal": e.get("fiscal"), "confirm": e.get("confirm"), "session": e.get("session")}

    def evidence_paths(code):
        paths = []
        for rel in [f"data/evidence_chain/daily_{dc}.json", "data/valuation/val_inputs.json",
                    f"data/valuation/ruler_a_{code.replace('.', '_')}_{dc}.json"]:
            p = ROOT / rel
            if p.exists():
                try:
                    if code in p.read_text(encoding="utf-8") or rel.endswith(f"{code.replace('.', '_')}_{dc}.json"):
                        paths.append(rel)
                except Exception:
                    pass
        # 当日新闻
        for np in (ROOT / "data/news").glob(f"*{dc}*"):
            try:
                if code in np.read_text(encoding="utf-8"):
                    paths.append("data/news/" + np.name)
            except Exception:
                pass
        return paths

    rows = []
    for acc_cn in ("富途", "SBI"):
        A = tg[acc_cn].get("当日总资产A_USD") or 0
        for r in tg[acc_cn].get("逐只(按贡献pp降序)", []):
            code = r.get("code")
            if (acc_cn, code) in have_cn:
                continue  # 已填预测·跳过
            px = r.get("price_local_0730", r.get("price_local"))
            mv = r.get("market_value_usd") or 0
            h = vi.get(code, {})
            pa = h.get("priced_at")
            d = rd.get(code)
            rows.append({
                "代码": code, "名称": r.get("name"), "账户": acc_cn, "股数": r.get("qty"),
                "当日价": px, "price_vintage": ("2026-07-30 东证收盘(daily_scan)" if code.startswith("JP.")
                                              else "2026-07-29 收盘＋盘后"),
                "权重_机器算(市值÷账户A)": round(mv / A, 4) if A else None,
                "市值_USD": round(mv, 2),
                "锚fair": r.get("fair"), "锚priced_at": pa, "锚龄天数": _age_days(today, pa) if pa else None,
                "review_due命中": bool(r.get("review_due")),
                "review_due类型": ([t.get("类型") for t in d.get("触发", [])] if d else []),
                "blind": bool(r.get("blind")), "blind_reason": r.get("blind_reason"),
                "可用证据文件": evidence_paths(code),
                "下一已知事件日": next_ev.get(code),
            })
    rows.sort(key=lambda x: -(x["权重_机器算(市值÷账户A)"] or 0))  # N3-2 权重降序

    out = {"_说明": "预测填报工单(N3·轮50)。★只给客观事实与路径·不含任何建议/判断/情景/概率(那是Opus5的活·N3-3)。"
                    "填报只需给:情景区间/概率/依据/证伪信号/见分晓日期/置信度;E[上行]/权重/贡献pp机器算(M3)。",
           "date": date_h, "生成": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
           "尚未填预测只数": len(rows), "按权重降序": True, "工单": rows}
    jp = ROOT / "data/forecast" / f"fill_worklist_{date_h}.json"
    jp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # HTML(董事长/Opus5 可直接看)
    def esc(x):
        return html.escape(str(x)) if x is not None else "—"
    trs = ""
    for r in rows:
        ev = r["下一已知事件日"]
        evs = f"{ev['report_date']}·{ev.get('fiscal','')}·{ev.get('confirm','')}" if ev else "—"
        trs += ("<tr><td>%s</td><td>%s</td><td>%s</td><td style='text-align:right'>%s</td>"
                "<td style='text-align:right'>%s</td><td>%s</td><td style='text-align:right'>%s</td>"
                "<td style='text-align:right'>%s</td><td>%s</td><td style='text-align:right'>%s</td>"
                "<td>%s</td><td>%s</td><td>%s</td><td style='font-size:11px'>%s</td><td>%s</td></tr>" % (
                    esc(r["代码"]), esc(r["名称"]), esc(r["账户"]), esc(r["股数"]),
                    esc(r["当日价"]), esc(r["price_vintage"]), esc(r["权重_机器算(市值÷账户A)"]),
                    esc(r["市值_USD"]), esc(r["锚fair"]), esc(r["锚龄天数"]),
                    "是" if r["review_due命中"] else "否", esc("／".join(r["review_due类型"]) or "—"),
                    "是" if r["blind"] else "否", esc("<br>".join(r["可用证据文件"]) or "—") if False else "<br>".join(esc(p) for p in r["可用证据文件"]) or "—",
                    evs))
    # O3(轮52):豁免收窄到函数级——只对本函数写 .html 的行加 '# html-ok'(整脚本不再豁免·若往 json 写标签仍会被拦)
    _pg = ("<!doctype html><meta charset='utf-8'><title>预测填报工单 %s</title>"  # html-ok
           "<style>body{font-family:'Microsoft YaHei',sans-serif;max-width:1400px;margin:0 auto;padding:20px}"  # html-ok
           "table{border-collapse:collapse;width:100%%;font-size:13px}th,td{border:1px solid #bbb;padding:5px 7px;text-align:left}"  # html-ok
           "th{background:#2c3e50;color:#fff}h2{color:#2c3e50}</style>"  # html-ok
           "<h2>预测填报工单 · %s · 尚未填预测 %d 只（权重降序）</h2>"  # html-ok
           "<p style='color:#c0392b'>★ 本表只给客观事实与路径·不含建议/判断/情景/概率。填报只需给：情景区间／概率／依据／证伪信号／见分晓日期／置信度；E[上行]／权重／贡献pp 机器算。</p>"  # html-ok
           "<table><tr><th>代码</th><th>名称</th><th>账户</th><th>股数</th><th>当日价</th><th>price_vintage</th>"  # html-ok
           "<th>权重(机器)</th><th>市值$</th><th>锚fair</th><th>锚龄天</th><th>review_due</th><th>命中类型</th>"  # html-ok
           "<th>blind</th><th>可用证据文件</th><th>下一事件日</th></tr>%s</table>")  # html-ok
    page = _pg % (date_h, date_h, len(rows), trs)
    hp = ROOT / "data/forecast" / f"fill_worklist_{date_h}.html"
    hp.write_text(page, encoding="utf-8")
    return jp, hp, len(rows)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    jp, hp, n = build(a.date)
    print(f"[fill_worklist] 尚未填 {n} 只 → {jp.name} + {hp.name}")


if __name__ == "__main__":
    raise SystemExit(main())
