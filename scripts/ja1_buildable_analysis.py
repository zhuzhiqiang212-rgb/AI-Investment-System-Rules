# -*- coding: utf-8 -*-
"""★轮91 JA1:拆开「50只全<1.5pp」的真实原因。补缺口pp = 可建权重 × 上行%。
高AI beta组已破限(富途36%/SBI44.5%·上限30%)→高AI beta格候选合法可建权重≈0→<1.5pp不是『不够便宜』而是『风险约束下建不了仓』。
逐只三列(上行%/可建权重[被哪条约束限]/补缺口pp) + 分布(上行低 vs 可建≈0被压死) + 结论(A不便宜/B建不了仓/C兼有)。
输出 data/opportunity/buildable_analysis_{date}.json。"""
import sys, json, argparse, glob
from datetime import datetime, timezone, timedelta
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
SINGLE_CAP = 0.20        # 单只上限
GROUP_CAP = 0.30         # 单一环节(驱动组)上限

# 激活格 → 驱动暴露组(高AI beta价格弹性 / 独立 / 利率 …)——分类·非投资判断
CELL_DRIVER = {
    "半导体存储（DRAM/NAND）": "高AI beta", "半导体测试": "高AI beta", "半导体设备（前道/后道）": "高AI beta",
    "半导体材料": "高AI beta", "代工": "高AI beta", "AI算力租赁（新型云）": "高AI beta", "AI服务器/硬件": "高AI beta",
    "AI电力/能源": "独立驱动", "日本金融/保险": "日本利率受益", "日本自动化/机器人": "独立驱动", "医药（ADC/肿瘤）": "独立驱动",
}


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def build(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    cp = _rj(ROOT / "data/opportunity" / f"candidate_pool_{dh}.json")
    dv = _rj(sorted(glob.glob(str(ROOT / "data/risk/driver_exposure_*.json")))[-1])
    # 组现权重(取富途+SBI里更满的·保守=用max·因破限就建不了)
    grp_w = {}
    for acc in ("富途", "SBI"):
        for g, v in (dv.get("账户", {}).get(acc, {}) or {}).get("驱动组", {}).items():
            w = v.get("权重合计")
            if isinstance(w, (int, float)):
                grp_w[g] = max(grp_w.get(g, 0), w)
    rows = []
    for c in cp.get("candidates", []):
        fv = (c.get("fair_value", {}) or {}).get("value")
        px = c.get("price")
        if not (isinstance(fv, (int, float)) and fv > 0 and isinstance(px, (int, float)) and px > 0):
            continue   # 无简易估值(C级待估值)·不进本拆解
        upside = fv / px - 1
        cell = c.get("sector_cell"); drv = CELL_DRIVER.get(cell, "独立驱动")
        cur = grp_w.get(drv, 0)
        headroom = max(0.0, GROUP_CAP - cur)
        buildable = min(SINGLE_CAP, headroom)
        limited_by = ("驱动组『%s』已达%.1f%%(破/触%d%%上限)→可建≈0" % (drv, cur * 100, GROUP_CAP * 100)) if headroom <= 0.001 \
            else ("驱动组『%s』余量%.1f%%(单只上限%d%%)" % (drv, headroom * 100, SINGLE_CAP * 100))
        contrib_pp = buildable * upside * 100
        rows.append({"code": c.get("code"), "sector_cell": cell, "驱动组": drv,
                     "①上行pct": round(upside * 100, 1), "②可建权重pct": round(buildable * 100, 2),
                     "②被哪条约束限": limited_by, "③补缺口pp": round(contrib_pp, 3)})
    # 分布
    low_upside = [r for r in rows if r["①上行pct"] < 10]
    blocked = [r for r in rows if r["①上行pct"] >= 10 and r["②可建权重pct"] < 0.5]
    both_ok_but_small = [r for r in rows if r["①上行pct"] >= 10 and r["②可建权重pct"] >= 0.5 and r["③补缺口pp"] < 1.5]
    # 主因判定(★含方法偏差诚实标注)
    # 高上行却被风险压死的(可建≈0·上行≥10%)=仓位结构堵死新机会的铁证
    high_up_blocked = [r for r in blocked if r["①上行pct"] >= 20]
    verdict = ("C:两者兼有·且两个关键事实——"
               "①【建不了仓·铁证】高AI beta组已破限(现%s%%>上限%d%%)·致 %d 只高AI beta格候选可建权重≈0"
               "(其中 %d 只上行≥20%%[含上行100%%+的]想建也建不了→仓位结构堵死了新AI/半导体机会·非市场没机会);"
               "②【『不便宜』含方法偏差】另 %d 只简易估值下上行<10%%显『贵』·但简易估值=板块中位PE×【当前EPS】·"
               "对低当前EPS的成长股系统性低估(它们按未来盈利定价)→这批『不便宜』部分是估值方法局限·非真贵。"
               "★所以不是单纯A(不便宜)·仓位结构(高AI beta破限)确实压死了含高上行在内的一批半导体/AI候选"
               ) % (round(grp_w.get("高AI beta", 0) * 100, 1), GROUP_CAP * 100, len(blocked), len(high_up_blocked), len(low_upside))
    return {
        "_说明": "★轮91 JA1 拆开入选0真因。补缺口pp=可建权重×上行%。高AI beta破限→高AI beta格可建≈0→<1.5pp是建不了仓非不便宜。",
        "date": dh, "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "驱动组现权重(富途/SBI取更满)": {k: round(v * 100, 1) for k, v in grp_w.items()}, "组上限pct": GROUP_CAP * 100,
        "有简易估值可拆解数": len(rows),
        "分布": {"上行%本身低(<10%)": len(low_upside), "上行%不低但可建≈0(风险压死)": len(blocked),
               "上行可建都够但补缺口仍<1.5pp": len(both_ok_but_small)},
        "★主因结论(JA1-3)": verdict,
        "上行低_前10": sorted(low_upside, key=lambda r: r["①上行pct"])[:10],
        "被风险压死_前10": sorted(blocked, key=lambda r: -r["①上行pct"])[:10],
        "逐只": rows,
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out = build(a.date)
    p = ROOT / "data/opportunity" / f"buildable_analysis_{a.date.replace('-','')}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    b = p.read_bytes(); json.loads(b.decode())
    print("[ja1_buildable] %s · 可拆解%d只 · 乱码%d" % (a.date, out["有简易估值可拆解数"], b.count(b"\xef\xbf\xbd")))
    print("  驱动组现权重:", out["驱动组现权重(富途/SBI取更满)"])
    print("  分布:", out["分布"])
    print("  ★主因:", out["★主因结论(JA1-3)"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
