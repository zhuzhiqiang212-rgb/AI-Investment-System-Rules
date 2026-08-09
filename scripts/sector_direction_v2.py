# -*- coding: utf-8 -*-
"""★轮163 A:重写④方向判定(Opus5裁定·根因=旧版用单日单股判反了中期趋势)。
新输入三样:①板块【整体中位】涨跌(非单一代表标的) ②多窗口5/20/60日 ③③层传下方向(★真参与计算不只拼文本)。
新规则(结构化·可复核):
  · 多窗口一致(5/20/60同向) 且 与③方向一致 → 判该方向·『强信号』
  · 多窗口一致 但 与③方向矛盾 → ★『矛盾·须Opus5裁』(不许机器自己选·上层作参照系)
  · 多窗口不一致 → 『方向不明·不判』  · 禁止单窗口/单日判定
依据链机器可核:三窗口中位数值 + ③方向 + ★两者一致布尔。★Code只实现规则+算数·终裁Opus5(G2)。"""
import sys, json, ssl, statistics, urllib.request, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0"}
DEAD = 0.5   # 中位±0.5%内视为中性(避免噪声)

# ★③层传下方向→板块结构化映射(Opus5框架:成长股压力减轻=中性偏多·能源/避险受损)
DIR3 = {
    "AI算力·AI芯片": "中性偏多", "AI半导体设备": "中性偏多", "AI存储": "中性偏多",
    "AI云·数据中心": "中性偏多", "AI应用软件": "中性偏多", "机器人·自动化": "中性偏多",
    "材料(半导体上游)": "中性偏多", "电力·能源(AI耗电)": "受损",   # ③:能源油价跌+增产→受损
}
DIR3_SRC = "③传下:高估值成长股压力减轻(中性偏多·非利好兑现)·能源受损·避险受损(layer3 J3)"
# ★★轮164 A(Opus5裁定):③判断【适用范围】——③支撑=宏观流动性(中东/油价/OPEC)→只作用于【利率敏感型成长股】;行业周期驱动板块(capex/库存·如半导体设备/存储)不适用→不产生矛盾。
BOARD_DRIVER = {
    "AI算力·AI芯片": "利率敏感型成长股", "AI云·数据中心": "利率敏感型成长股",
    "AI应用软件": "利率敏感型成长股", "机器人·自动化": "利率敏感型成长股",
    "AI半导体设备": "行业周期驱动(capex/库存)", "AI存储": "行业周期驱动(capex/库存)",
    "材料(半导体上游)": "行业周期驱动(capex/库存)", "电力·能源(AI耗电)": "能源/公用",
}
DIR3_SCOPE = {"适用": ["利率敏感型成长股"], "排除": ["行业周期驱动(capex/库存)"]}
# 旧④方向(承接节点单日·轮162)→classified板块映射(仅对照)
OLD = {"AI算力·AI芯片": "受益", "AI半导体设备": "受益", "AI存储": "受损",
       "AI云·数据中心": "受损", "AI应用软件": "受益",
       "电力·能源(AI耗电)": "未覆盖", "机器人·自动化": "未覆盖", "材料(半导体上游)": "未覆盖"}


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _latest(pat):
    g = sorted(ROOT.glob(pat)); return g[-1] if g else None


def to_yahoo(code):
    mk, s = code.split(".", 1)
    return s if mk == "US" else (s + ".T" if mk == "JP" else ((s.lstrip("0") or "0").zfill(4) + ".HK" if mk == "HK" else None))


def windows(code):
    sym = to_yahoo(code)
    if not sym:
        return None
    try:
        j = json.loads(urllib.request.urlopen(urllib.request.Request(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=6mo&interval=1d", headers=UA), timeout=15, context=CTX).read())
        adj = j["chart"]["result"][0]["indicators"].get("adjclose", [{}])[0].get("adjclose")
        cl = [c for c in (adj or []) if c is not None]
        if len(cl) < 61:
            return None
        return {5: (cl[-1] - cl[-6]) / cl[-6] * 100, 20: (cl[-1] - cl[-21]) / cl[-21] * 100, 60: (cl[-1] - cl[-61]) / cl[-61] * 100}
    except Exception:
        return None


def _sign(x):
    return "受益" if x > DEAD else ("受损" if x < -DEAD else "中性")


def decide(m5, m20, m60, dir3, board_driver=None):
    """新规则(★轮164:先查③适用范围·范围外不产生矛盾)。返回(结论方向, 状态, 一致布尔)。"""
    s5, s20, s60 = _sign(m5), _sign(m20), _sign(m60)
    multi_consistent = (s5 == s20 == s60) and s5 != "中性"
    if not multi_consistent:
        return "方向不明", "多窗口不一致(5/20/60非同向)→不判", None
    board_dir = s5  # 受益/受损
    # ★★轮164:③判断是否适用于本板块(适用范围·Opus5裁定)
    if board_driver in DIR3_SCOPE["排除"]:
        return board_dir, "多窗口一致[%s]·★③判断不适用于本板块(%s·③是宏观流动性→只作用利率敏感型成长股)·不产生矛盾" % (board_dir, board_driver), None
    d3 = dir3 or "未明"
    # ③方向与板块方向是否一致(结构化)——★仅对③适用范围内的板块
    if d3 in ("中性偏多", "中性", "未明"):
        if board_dir == "受益":
            return board_dir, "强信号(多窗口一致且③中性偏多一致·板块在③适用范围内)", True
        else:
            return board_dir, "★矛盾(③适用范围内·多窗口=受损但③=中性偏多)→须Opus5裁", False
    d3_dir = "受益" if "偏多" in d3 or d3 == "受益" else ("受损" if "受损" in d3 or "偏空" in d3 else "中性")
    if d3_dir == board_dir:
        return board_dir, "强信号(多窗口一致且与③方向一致)", True
    if d3_dir == "中性":
        return board_dir, "多窗口一致·③中性未加强", True
    return board_dir, "★矛盾(③适用范围内·多窗口一致但与③方向相反)→须Opus5裁", False


def build(dc):
    cls = _rj(_latest("data/universe/classified_*.json"))
    ff = _rj(_latest("data/universe/funnel_full_*.json"))
    bigmid = set(c for c, v in (ff.get("snap", {}) or {}).items() if v.get("tier") in ("大盘", "中盘"))
    rows = []
    changed = 0
    for b in DIR3:
        codes = [c for c in (cls.get("★各板块归出", {}) or {}).get(b, {}).get("全量code(供分层筛选·不进产品)", []) if c in bigmid][:70]
        w5, w20, w60 = [], [], []
        for c in codes:
            w = windows(c); time.sleep(0.15)
            if w:
                w5.append(w[5]); w20.append(w[20]); w60.append(w[60])
        if len(w5) < 4:
            rows.append({"板块": b, "样本": len(w5), "结论方向": "样本不足·不判"}); continue
        m5, m20, m60 = round(statistics.median(w5), 2), round(statistics.median(w20), 2), round(statistics.median(w60), 2)
        d3 = DIR3.get(b)
        drv = BOARD_DRIVER.get(b)
        new_dir, status, agree = decide(m5, m20, m60, d3, drv)
        old = OLD.get(b, "未覆盖")
        flip = (old not in ("未覆盖",) and new_dir != old)
        if flip:
            changed += 1
        rows.append({
            "板块": b, "样本": len(w5),
            "★新方向": new_dir, "状态": status,
            "旧方向(单日)": old, "★是否变化": ("★变了(%s→%s)" % (old, new_dir)) if flip else ("未覆盖→" + new_dir if old == "未覆盖" else "未变"),
            "依据链(机器可核)": {"5日中位": m5, "20日中位": m20, "60日中位": m60,
                          "③传下方向": d3, "本板块驱动类型": drv, "★③适用于本板块": (drv not in DIR3_SCOPE["排除"]),
                          "★③与板块方向一致": agree, "多窗口同向": (_sign(m5) == _sign(m20) == _sign(m60))},
        })
    out = {
        "_说明": "★轮163 ④方向重写(Opus5裁定)。输入=板块整体中位(5/20/60)+③传下方向(真参与计算)。规则:多窗口一致且③一致=强信号;多窗口一致但③矛盾=须Opus5裁;多窗口不一致=方向不明。★Code实现规则不终裁(G2)。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "③方向来源": DIR3_SRC,
        "★变化板块数(vs旧单日方向)": changed,
        "矛盾须Opus5裁": [r["板块"] for r in rows if "须Opus5裁" in str(r.get("状态", ""))],   # ★轮164:改精确匹配·不误捕『不产生矛盾』
        "③不适用板块(适用范围外·不产生矛盾)": [r["板块"] for r in rows if "不适用于本板块" in str(r.get("状态", ""))],
        "逐板块": rows,
    }
    (ROOT / f"data/market/sector_direction_v2_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("★变化板块数:", o["★变化板块数(vs旧单日方向)"], "· 矛盾须裁:", o["矛盾须Opus5裁"])
    for r in o["逐板块"]:
        if "★新方向" in r:
            dl = r["依据链(机器可核)"]
            print("  %-16s 新[%s] 旧[%s] %s | 5/20/60=%s/%s/%s ③=%s 一致=%s | %s" % (
                r["板块"], r["★新方向"], r["旧方向(单日)"], r["★是否变化"],
                dl["5日中位"], dl["20日中位"], dl["60日中位"], dl["③传下方向"], dl["★③与板块方向一致"], r["状态"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
