#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""市场确认·状态标记（不再淘汰）（派工单F-12·2026-07-21）。
★市场确认不淘汰任何标的·改为每只打【三选一状态】·全部保留分开显示·天天现算不锚死名单(总则六)。
  已确认  ：相对大盘3月 > 0(三月跑赢)
  正在确认：相对大盘3月 ≤ 0(仍跑输)但 近期好于前期(1月相对强度 > 3月)  ←生意在变好·市场未充分反应·空间常更大·单独成栏
  未确认  ：相对大盘3月 ≤ 0 且 近期未见好转(1月 ≤ 3月)
主池=象限分歧false(董事长口径89·内含①真强者39/②5/④5/无法判定40·逐只标共同象限)。
每只保留:四项加速、相对大盘1/3/6月、距52周高、量能比、财报后反应、基数效应标注。
读 quadrant/change_score/candidates_v2/pool89_market/PIT + kline(52周高/量能)。
用法：python scripts/pool_state.py --date 20260721"""
import argparse, json, sys, time
from pathlib import Path
from collections import Counter, defaultdict
ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "data" / "screen"
Fmap = {"8xxx": {"rev": 8001, "net": 8037}, "11xxx": {"rev": 11001, "net": 11036}}


def fy(stmt):
    return [r for r in (stmt or {}).get("report_list", []) if "FY" in r.get("period_text", "")]


def gv(period, fid):
    for x in period.get("item_list", []):
        if x.get("field_id") == fid:
            return x.get("data")
    return None


def status_of(rel):
    # 近期好于前期 = 相对强度在改善:1月相对 > 6月相对(半年趋势·如Amphenol) 或 1月 > 3月(更近)
    r3 = rel.get("3月"); r1 = rel.get("1月"); r6 = rel.get("6月")
    if r3 is None or r1 is None:
        return "状态数据不足", "缺相对大盘1或3月"
    if r3 > 0:
        return "已确认", "三月跑赢大盘"
    if (r6 is not None and r1 > r6) or (r1 > r3):
        return "正在确认", "三月仍跑输·但近期(1月)相对强度好于前期(6月/3月)·在改善"
    return "未确认", "三月跑输·且近期相对强度未见好转"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="20260721"); a = ap.parse_args()
    d = a.date
    sys.stdout.reconfigure(encoding="utf-8")
    q = json.loads((S / f"quadrant_{d}.json").read_text(encoding="utf-8"))
    v2 = json.loads((S / f"candidates_v2_{d}.json").read_text(encoding="utf-8"))
    cs = json.loads((S / f"change_score_{d}.json").read_text(encoding="utf-8"))
    cards_q = q["cards"]; cards_v2 = v2["cards"]; scores = cs["scores"]
    pm = {}
    pmf = S / f"pool89_market_{d}.json"
    if pmf.exists():
        pm = json.loads(pmf.read_text(encoding="utf-8")).get("market", {})
    pit = {}
    pf = ROOT / "data" / "pit" / d / "statements.jsonl"
    if pf.exists():
        for line in pf.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    r = json.loads(line); pit[r["code"]] = r
                except Exception:
                    pass

    pool = [c for c, r in cards_q.items() if not r["象限分歧"]]   # 89(象限分歧false)
    need_kl = [c for c in pool if c not in pm]                    # 缺52周高/量能的(非39真主池那50只)

    import futu as ft
    ctx = ft.OpenQuoteContext("127.0.0.1", 11111)
    kl = {}
    try:
        for c in need_kl:
            try:
                ret, df, _ = ctx.request_history_kline(c, ktype=ft.KLType.K_DAY, autype=ft.AuType.QFQ, max_count=260)
                if ret == ft.RET_OK and len(df) >= 30:
                    cl = [float(x) for x in df["close"].tolist()]; hi = [float(x) for x in df["high"].tolist()]; vol = [float(x) for x in df["volume"].tolist()]
                    upv = [vol[i] for i in range(max(1, len(cl) - 60), len(cl)) if cl[i] > cl[i - 1]]
                    dnv = [vol[i] for i in range(max(1, len(cl) - 60), len(cl)) if cl[i] < cl[i - 1]]
                    kl[c] = {"距52周高%": round((cl[-1] / max(hi[-min(len(hi), 252):]) - 1) * 100, 2),
                             "上涨日均量比下跌日均量": (round((sum(upv) / len(upv)) / (sum(dnv) / len(dnv)), 2) if (upv and dnv) else None)}
            except Exception:
                pass
            time.sleep(0.6)
    finally:
        ctx.close()

    def base_effect(c):
        rc = pit.get(c)
        if not (rc and rc.get("income")):
            return {}
        ifys = fy(rc["income"])
        if len(ifys) < 2:
            return {}
        ids = {x.get("field_id") for x in ifys[0].get("item_list", [])}
        sch = "8xxx" if 8001 in ids else ("11xxx" if 11001 in ids else None)
        if not sch:
            return {}
        fm = Fmap[sch]
        rev0 = gv(ifys[0], fm["rev"]); net0 = gv(ifys[0], fm["net"]); net1 = gv(ifys[1], fm["net"])
        return {"营收绝对规模": rev0, "本期净利": net0, "上期净利": net1,
                "基数效应嫌疑": (net0 is not None and net1 is not None and abs(net0) > 0 and abs(net1) < 0.1 * abs(net0))}

    rows = {}
    for c in pool:
        v2c = cards_v2.get(c, {}); sc = scores.get(c, {}); ind_ = sc.get("指标", {})
        L3 = v2c.get("市场先行层", {}).get("指标", {}); L2 = v2c.get("市场确认层", {}).get("指标", {})
        rel = L3.get("相对大盘1/3/6月%", {}) or {}
        st, why = status_of(rel)
        mk = pm.get(c, {}); k = kl.get(c, {})
        be = base_effect(c)
        rows[c] = {
            "code": c, "共同象限": cards_q[c]["主象限(利润)"], "行业": cards_q[c].get("名称行业"),
            "市场确认状态": st, "状态依据": why,
            "变化证据得分": sc.get("得分"), "数据覆盖率": sc.get("数据覆盖率"), "可信度": sc.get("结论可信度"),
            "四项加速": {"利润加速pp": ind_.get("利润加速度pp"), "营收加速pp": ind_.get("营收加速度pp"),
                     "OCF加速pp": ind_.get("OCF加速度pp"), "毛利率加速pp": ind_.get("毛利率加速度pp")},
            "相对大盘1/3/6月%": rel, "斜率改善(1月>6月)": L3.get("斜率改善(1月>6月)"),
            "距52周高%": mk.get("距52周高%", k.get("距52周高%")),
            "量能比(涨/跌)": mk.get("上涨日均量比下跌日均量", k.get("上涨日均量比下跌日均量")),
            "财报后跳空%": L2.get("财报后跳空%"), "20日守住%": L2.get("20日守住%"),
            "基数": (mk.get("基数") if mk.get("基数") else be),
            "基数效应嫌疑": (mk.get("基数效应嫌疑") if c in pm else be.get("基数效应嫌疑", False)),
            "异常字段": sc.get("异常字段", {}),
        }
    # 分状态·内按变化证据得分排序
    by_st = defaultdict(list)
    for c, r in rows.items():
        by_st[r["市场确认状态"]].append(c)
    for st in by_st:
        by_st[st].sort(key=lambda c: -(rows[c]["变化证据得分"] or -1))
    dist = {st: len(by_st.get(st, [])) for st in ["已确认", "正在确认", "未确认", "状态数据不足"]}
    # 真主池39内的状态分布(更有意义)
    p39 = [c for c in pool if cards_q[c]["主象限(利润)"] == "①"]
    dist39 = Counter(rows[c]["市场确认状态"] for c in p39)

    doc = {
        "_说明": "市场确认·状态标记(F-12)·★不淘汰·三状态全保留分开显示·天天现算不锚死名单。"
               "已确认=3月跑赢;正在确认=3月跑输但近期好于前期(生意变好市场未充分反应·单独成栏);未确认=3月跑输且近期未好转。",
        "主池口径": f"象限分歧false共{len(pool)}只(董事长89口径·内含①真强者{sum(1 for c in pool if cards_q[c]['主象限(利润)']=='①')}/②{sum(1 for c in pool if cards_q[c]['主象限(利润)']=='②')}/④{sum(1 for c in pool if cards_q[c]['主象限(利润)']=='④')}/无法判定{sum(1 for c in pool if cards_q[c]['主象限(利润)']=='—')})·逐只已标共同象限",
        "三状态数量_全89": dist,
        "三状态数量_真主池39(①同向加速)": dict(dist39),
        "各状态内排序": {st: by_st.get(st, []) for st in ["已确认", "正在确认", "未确认", "状态数据不足"]},
        "★正在确认(单独成栏·空间常更大)": [{"code": c, "变化证据得分": rows[c]["变化证据得分"], "共同象限": rows[c]["共同象限"],
                                 "相对大盘3月": rows[c]["相对大盘1/3/6月%"].get("3月"), "相对大盘1月": rows[c]["相对大盘1/3/6月%"].get("1月"),
                                 "行业": rows[c]["行业"]} for c in by_st.get("正在确认", [])],
        "cards": rows,
    }
    p = S / f"pool_state_{d}.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("wrote", p.name, p.stat().st_size, "字节 · EFBFBD=", p.read_bytes().count(b"\xef\xbf\xbd"))
    print("三状态数量(全89):", dist)
    print("三状态数量(真主池39):", dict(dist39))
    for chk in ["US.PLTR", "US.APH"]:
        if chk in rows:
            print(f"  {chk}: {rows[chk]['市场确认状态']}·{rows[chk]['状态依据']}·相对大盘1/3月={rows[chk]['相对大盘1/3/6月%'].get('1月')}/{rows[chk]['相对大盘1/3/6月%'].get('3月')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
