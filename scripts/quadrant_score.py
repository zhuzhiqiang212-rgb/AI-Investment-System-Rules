#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""变化驱动·四象限分池（派工单丙案·2026-07-21·尺总册F-11）。
★只算不筛选·不出买卖清单·不下单·不改尺·不自调参数·四象限分开排序不合并总分。
象限(以利润为主判据·同比×加速度)：
  ①强者加速(同比+/加速度+·主池) ②强者减速(同比+/加速度-·英伟达在此·副池)
  ③困境反转(同比-/加速度+·副池) ④持续恶化(同比-/加速度-·排除)
同时输出 营收/OCF/毛利率 各自象限;四项不一致→标"象限分歧"+明细。
读 change_score_{date}.json(利润/营收/OCF/毛利率 各同比+加速度)。
用法：python scripts/quadrant_score.py --date 20260721
"""
import argparse, json, sys
from pathlib import Path
from collections import Counter, defaultdict
ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data" / "screen"
QNAME = {"①": "强者加速", "②": "强者减速", "③": "困境反转", "④": "持续恶化", "—": "无法判定象限"}


def quad(yoy, accel):
    if yoy is None or accel is None:
        return "—"    # 缺同比或加速度→无法判定象限(F-07:不硬塞)
    if yoy >= 0 and accel >= 0:
        return "①"
    if yoy >= 0 and accel < 0:
        return "②"
    if yoy < 0 and accel >= 0:
        return "③"
    return "④"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="20260721"); a = ap.parse_args()
    d = a.date
    sys.stdout.reconfigure(encoding="utf-8")
    cs = json.loads((SCREEN / f"change_score_{d}.json").read_text(encoding="utf-8"))
    v2 = json.loads((SCREEN / f"candidates_v2_{d}.json").read_text(encoding="utf-8"))
    scores = cs["scores"]; cards = v2["cards"]

    rows = {}
    for c, s in scores.items():
        ind = s.get("指标", {})
        q_profit = quad(ind.get("利润同比%"), ind.get("利润加速度pp"))
        q_rev = quad(ind.get("营收同比%"), ind.get("营收加速度pp"))
        q_ocf = quad(ind.get("OCF同比%"), ind.get("OCF加速度pp"))
        q_gm = quad(ind.get("毛利率同比pp"), ind.get("毛利率加速度pp"))
        qs = {"利润": q_profit, "营收": q_rev, "OCF": q_ocf, "毛利率": q_gm}
        placed = [v for v in qs.values() if v != "—"]
        divergence = (len(set(placed)) > 1)
        rows[c] = {
            "code": c, "名称行业": cards.get(c, {}).get("行业"),
            "主象限(利润)": q_profit, "主象限名": QNAME[q_profit],
            "四项象限": qs, "象限分歧": divergence,
            "变化证据得分": s.get("得分"), "数据覆盖率": s.get("数据覆盖率"),
            "结论可信度": s.get("结论可信度"), "有加速度数": s.get("有加速度数"),
            "利润同比%": ind.get("利润同比%"), "利润加速度pp": ind.get("利润加速度pp"),
            "营收同比/加速": [ind.get("营收同比%"), ind.get("营收加速度pp")],
            "OCF同比/加速": [ind.get("OCF同比%"), ind.get("OCF加速度pp")],
            "毛利率同比pp/加速": [ind.get("毛利率同比pp"), ind.get("毛利率加速度pp")],
            "异常字段": s.get("异常字段", {}), "常识核对": cards.get(c, {}).get("常识核对", []),
        }

    # 各象限分开·象限内按变化证据得分排序(★不合并·不同象限不比)
    by_q = defaultdict(list)
    for c, r in rows.items():
        by_q[r["主象限(利润)"]].append(c)
    for q in by_q:
        by_q[q].sort(key=lambda c: -(rows[c]["变化证据得分"] or -1))
    dist = {q: len(by_q.get(q, [])) for q in ["①", "②", "③", "④", "—"]}
    divergent = [c for c, r in rows.items() if r["象限分歧"]]

    doc = {
        "_说明": "变化驱动四象限分池(F-11丙案)·以利润为主判据(同比×加速度)。★四象限分开排序·不合并总分·不同象限不可比。"
               "主池=象限①;②③为副池(可单独看/给小仓位·不进主排名);④排除。保持:同比/加速度/8xxx11xxx/毛利率结构NA/F-07五条/异常标注 不变。",
        "象限定义": {"①强者加速": "同比+ 加速度+ (主池)", "②强者减速": "同比+ 加速度- (英伟达在此·副池)",
                 "③困境反转": "同比- 加速度+ (副池)", "④持续恶化": "同比- 加速度- (排除)", "—": "缺同比或加速度·无法判定象限"},
        "使用规矩": ["①四象限分开排序不合并总分", "②主池=①·②③副池不进主排名", "③④直接排除", "④每只标象限并显示在卡上"],
        "date": d, "入围": len(rows),
        "象限分布": dist, "象限分布(名)": {QNAME[q]: n for q, n in dist.items()},
        "象限分歧数": len(divergent), "象限分歧清单": sorted(divergent),
        "各象限内排序": {q: by_q.get(q, []) for q in ["①", "②", "③", "④", "—"]},
        "主池①前20": by_q.get("①", [])[:20],
        "cards": rows,
    }
    p = SCREEN / f"quadrant_{d}.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    raw = p.read_bytes()
    print("wrote", p.name, len(raw), "字节 · EFBFBD=", raw.count(b"\xef\xbf\xbd"))
    print("象限分布:", {QNAME[q]: n for q, n in dist.items()})
    print("象限分歧:", len(divergent), "只")
    print("主池①前20:", [(c, rows[c]["变化证据得分"]) for c in by_q.get("①", [])[:20]])
    # 抽验英伟达/特斯拉
    for chk in ["US.NVDA", "US.TSLA"]:
        if chk in rows:
            r = rows[chk]
            print(f"  {chk}: 主象限{r['主象限(利润)']}({r['主象限名']}) 利润{r['利润同比%'] and round(r['利润同比%'],1)}/{r['利润加速度pp']} 四项{r['四项象限']} 分歧{r['象限分歧']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
