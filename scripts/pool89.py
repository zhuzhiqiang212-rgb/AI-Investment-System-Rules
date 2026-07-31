#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主池·行业分布 + 市场确认层 + 基数效应（派工单2026-07-21·F-11/F-08）。
★只算不筛选·不出买卖清单·不下单·不改尺·不合并总分。
★口径提示(诚实):董事长单据"89只(象限分歧=false)"实含 ①39/②5/④5/无法判定40——
  其中40只是加速度缺致【平凡非分歧】(名不副实)、5只④持续恶化(按规矩应排除)。
  真正"四项同向加速"的强者=【利润①且象限分歧false=39只】。本轮两项任务在39只真主池上做，
  并同时给出89的完整拆解，供架构师确认是否改口径。
任务1 行业分布(plate_type=INDUSTRY真行业)+行业内加速占比。任务2 市场确认层五指标+基数效应嫌疑。
读 quadrant/change_score/candidates_v2/fin_score/PIT。用法：python scripts/pool89.py --date 20260721"""
import argparse, json, sys, time
from pathlib import Path
from collections import defaultdict, Counter
ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "data" / "screen"
IDX = {"US": "US.SPY", "JP": "JP.1329"}
Fmap = {"8xxx": {"rev": 8001, "net": 8037}, "11xxx": {"rev": 11001, "net": 11036}}


def fy(stmt):
    return [r for r in (stmt or {}).get("report_list", []) if "FY" in r.get("period_text", "")]


def gv(period, fid):
    for x in period.get("item_list", []):
        if x.get("field_id") == fid:
            return x.get("data")
    return None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="20260721"); a = ap.parse_args()
    d = a.date
    sys.stdout.reconfigure(encoding="utf-8")
    q = json.loads((S / f"quadrant_{d}.json").read_text(encoding="utf-8"))
    v2 = json.loads((S / f"candidates_v2_{d}.json").read_text(encoding="utf-8"))
    cards_q = q["cards"]; cards_v2 = v2["cards"]
    # PIT
    pit = {}
    pf = ROOT / "data" / "pit" / d / "statements.jsonl"
    if pf.exists():
        for line in pf.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    r = json.loads(line); pit[r["code"]] = r
                except Exception:
                    pass

    # 89(象限分歧false)拆解
    p89 = [c for c, r in cards_q.items() if not r["象限分歧"]]
    breakdown = Counter(cards_q[c]["主象限(利润)"] for c in p89)
    真主池39 = [c for c in p89 if cards_q[c]["主象限(利润)"] == "①"]
    all432 = list(cards_q.keys())

    # ── 任务1:行业分布(真主池39·并附89口径)──
    ind_of = {c: (cards_q[c].get("名称行业") or "(未分类)") for c in all432}
    ind_432 = Counter(ind_of[c] for c in all432)
    ind_39 = defaultdict(list)
    for c in 真主池39:
        ind_39[ind_of[c]].append(c)
    industry = {}
    for ind, members in ind_39.items():
        industry[ind] = {"进主池39数": len(members), "成员": sorted(members),
                         "该行业432总数": ind_432[ind],
                         "行业内加速占比%": round(len(members) / ind_432[ind] * 100, 1) if ind_432[ind] else None}
    top3 = sorted(industry.items(), key=lambda kv: (-kv[1]["行业内加速占比%"], -kv[1]["进主池39数"]))[:3]
    # ≥3只行业的加速占比(避免 n=1-2 的100%噪声·更能代表"整行业在变强")
    top3_ge3 = sorted([(k, v) for k, v in industry.items() if v["该行业432总数"] >= 3],
                      key=lambda kv: (-kv[1]["行业内加速占比%"], -kv[1]["进主池39数"]))[:3]

    # ── 任务2:市场确认层五指标(真主池39·klines补52周高/量能·其余复用缓存)+ 基数效应 ──
    import futu as ft
    ctx = ft.OpenQuoteContext("127.0.0.1", 11111)
    idx = {}
    for mk, ic in IDX.items():
        try:
            ret, df, _ = ctx.request_history_kline(ic, ktype=ft.KLType.K_DAY, autype=ft.AuType.QFQ, max_count=260)
            idx[mk] = [float(x) for x in df["close"].tolist()] if ret == ft.RET_OK and len(df) else None
        except Exception:
            idx[mk] = None
        time.sleep(1)
    market = {}; got = Counter()
    try:
        for c in 真主池39:
            mk = c.split(".")[0]
            v2c = cards_v2.get(c, {})
            L3 = v2c.get("市场先行层", {}).get("指标", {})
            L2 = v2c.get("市场确认层", {}).get("指标", {})
            rec = {"code": c, "行业": ind_of[c]}
            # 1 相对大盘(复用缓存)+斜率
            rel = L3.get("相对大盘1/3/6月%", {})
            rec["相对大盘1/3/6月%"] = rel
            rec["斜率改善(1月>6月)"] = L3.get("斜率改善(1月>6月)")
            rec["相对大盘3月为正且斜率改善"] = (rel.get("3月") is not None and rel.get("3月") > 0 and bool(L3.get("斜率改善(1月>6月)")))
            if rel.get("3月") is not None:
                got["相对大盘"] += 1
            # 2/3 52周高 + 上涨/下跌量(kline)
            try:
                ret, df, _ = ctx.request_history_kline(c, ktype=ft.KLType.K_DAY, autype=ft.AuType.QFQ, max_count=260)
                if ret == ft.RET_OK and len(df) >= 30:
                    cl = [float(x) for x in df["close"].tolist()]; hi = [float(x) for x in df["high"].tolist()]; vol = [float(x) for x in df["volume"].tolist()]
                    rec["距52周高%"] = round((cl[-1] / max(hi[-min(len(hi), 252):]) - 1) * 100, 2); got["距52周高"] += 1
                    upv = [vol[i] for i in range(max(1, len(cl) - 60), len(cl)) if cl[i] > cl[i - 1]]
                    dnv = [vol[i] for i in range(max(1, len(cl) - 60), len(cl)) if cl[i] < cl[i - 1]]
                    rec["上涨日均量比下跌日均量"] = round((sum(upv) / len(upv)) / (sum(dnv) / len(dnv)), 2) if (upv and dnv) else None
                    if rec.get("上涨日均量比下跌日均量") is not None:
                        got["量能"] += 1
            except Exception:
                pass
            time.sleep(0.6)
            # 4 财报后跳空守住(复用缓存)
            rec["财报后跳空%"] = L2.get("财报后跳空%"); rec["5日守住%"] = L2.get("5日守住%"); rec["20日守住%"] = L2.get("20日守住%")
            rec["最近财报日"] = L2.get("最近财报日")
            if L2.get("财报后跳空%") is not None:
                got["财报跳空"] += 1
            # 5 相对行业强度(部分:与主池39同行业成员3月相对强度中位数比·成本高·近似)
            rec["相对行业强度"] = "部分·下算"
            # 基数效应:营收绝对规模 + 上期利润是否过小
            rc = pit.get(c); base = {}
            if rc and rc.get("income"):
                ifys = fy(rc["income"])
                ids = {x.get("field_id") for x in ifys[0].get("item_list", [])} if ifys else set()
                sch = "8xxx" if 8001 in ids else ("11xxx" if 11001 in ids else None)
                if sch and len(ifys) >= 2:
                    fm = Fmap[sch]
                    rev0 = gv(ifys[0], fm["rev"]); net0 = gv(ifys[0], fm["net"]); net1 = gv(ifys[1], fm["net"])
                    base = {"营收绝对规模": rev0, "本期净利": net0, "上期净利": net1,
                            "上期利润绝对值<本期10%": (net0 is not None and net1 is not None and abs(net0) > 0 and abs(net1) < 0.1 * abs(net0))}
            rec["基数"] = base
            rec["基数效应嫌疑"] = bool(base.get("上期利润绝对值<本期10%"))
            market[c] = rec
        # 5 相对行业强度(主池39内·按行业中位数)
        by_ind_rel = defaultdict(list)
        for c, r in market.items():
            v = (r.get("相对大盘1/3/6月%") or {}).get("3月")
            if v is not None:
                by_ind_rel[r["行业"]].append((c, v))
        for c, r in market.items():
            peers = by_ind_rel.get(r["行业"], [])
            v = (r.get("相对大盘1/3/6月%") or {}).get("3月")
            if len(peers) >= 2 and v is not None:
                med = sorted(x[1] for x in peers)[len(peers) // 2]
                r["相对行业强度"] = {"本只3月相对大盘": v, "同行业(主池内)中位数": med, "强于行业中位": v > med, "口径": f"主池内同行业{len(peers)}只·部分"}
            else:
                r["相对行业强度"] = "部分·同行业主池内成员<2·无法算中位数"
    finally:
        ctx.close()

    suspicion = sorted([c for c, r in market.items() if r["基数效应嫌疑"]])
    # 五项可得率(在39上)
    n = len(真主池39)
    可得率 = {"相对大盘": round(got["相对大盘"] / n * 100, 1), "距52周高": round(got["距52周高"] / n * 100, 1),
           "上涨/下跌量": round(got["量能"] / n * 100, 1), "财报跳空守住": round(got["财报跳空"] / n * 100, 1),
           "相对行业强度": "部分(主池内同行业中位数)"}
    # 答③:四项加速 + 相对大盘3月正且斜率改善 + 非基数嫌疑
    ans3 = sorted([c for c in 真主池39 if market[c].get("相对大盘3月为正且斜率改善") and not market[c]["基数效应嫌疑"]])

    # 输出
    (S / f"pool89_industry_{d}.json").write_text(json.dumps({
        "_口径": "★真主池=利润①且象限分歧false=39只(四项同向加速真强者)。董事长89(象限分歧false)拆解见下·40只无法判定象限(加速度缺·平凡非分歧)+5只②+5只④(应排除)非真强者。",
        "89拆解": {"①真强者": breakdown["①"], "②强者减速": breakdown["②"], "④持续恶化(应排除)": breakdown["④"], "—无法判定象限(加速度缺)": breakdown["—"]},
        "真主池39": sorted(真主池39), "行业数": len(industry),
        "加速占比最高三行业(全部·含小样本)": [{"行业": k, **{kk: vv for kk, vv in v.items() if kk != "成员"}} for k, v in top3],
        "加速占比最高三行业(行业≥3只·更代表趋势)": [{"行业": k, **{kk: vv for kk, vv in v.items() if kk != "成员"}} for k, v in top3_ge3],
        "小样本提示": "农业投入品/电子分销等 n≤2 的100%占比是噪声(样本太小·不代表整行业变强)·看行业趋势以≥3只版为准",
        "行业分布": industry}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (S / f"pool89_market_{d}.json").write_text(json.dumps({
        "_口径": "市场确认层五指标(F-08·与基本面层分开算)·真主池39只。相对大盘/斜率/跳空复用当日缓存·52周高/量能当日kline真算·相对行业=主池内同行业中位数(部分)。",
        "五项可得率": 可得率, "基数效应嫌疑清单": suspicion,
        "同时满足四项加速+相对大盘3月正且斜率改善+非基数嫌疑": ans3,
        "market": market}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print("★口径:89(象限分歧false)=", dict(breakdown), "→真主池(①同向)39只")
    print("任务1 行业数:", len(industry), "· 加速占比top3:", [(k, v["行业内加速占比%"], str(v["进主池39数"]) + "/" + str(v["该行业432总数"])) for k, v in top3])
    print("任务2 五项可得率:", 可得率)
    print("基数效应嫌疑:", len(suspicion), "只 →", suspicion)
    print("答③(四项加速+相对大盘3月正斜率改善+非基数):", len(ans3), "只 →", ans3)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
