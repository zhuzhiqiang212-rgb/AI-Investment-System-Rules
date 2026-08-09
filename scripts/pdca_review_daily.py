# -*- coding: utf-8 -*-
"""★轮84 BA1:⑦复盘层·日复盘补两项 + 决策质量分。三件产出:
 BA1-1 action_review_{date}.json —— 昨日动作今天看对没对(对/错/未到验证时点·判错标错在哪)
 BA1-2 event_vs_macro_{date}.json —— 今日新事件对当前regime=支持/中性/证伪(证伪→产品显性告警)
 BA1-3 decision_quality_{date}.json —— 每个动作质量分=Σ(把握分×依据系数)/依赖判断数·<2.0标低把握
系数 A=1.0 / B=0.6 / C=0.3。判定尽量机械(关键词规则+价格比对)·不做投资判断·不确定默认『未到/中性』。"""
import sys, json, argparse, re, glob
from datetime import datetime, timezone, timedelta, date as _date
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
COEF = {"A": 1.0, "B": 0.6, "C": 0.3}


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _prev_trading(dc):
    """上一交易日(跳周末)。08-02周日→07-31。"""
    d = _date(int(dc[:4]), int(dc[4:6]), int(dc[6:8]))
    for _ in range(1, 6):
        d -= timedelta(days=1)
        if d.weekday() < 5:
            return d.strftime("%Y%m%d")
    return dc


def _px_map(dc):
    scan = _rj(ROOT / "data/market" / f"daily_scan_{dc}.json")
    out = {}
    for q in ((scan.get("items", {}).get("1_当日20只价", {}) or {}).get("逐只", []) or []):
        out[q.get("code")] = q.get("last_price")
    return out


# ── BA1-1 昨日动作今天看对没对 ──
def action_review(dc):
    prev = _prev_trading(dc)
    y_dec = _rj(ROOT / "data/pdca" / f"decisions_{prev}.json").get("decisions", {})
    px_now = _px_map(dc); px_prev = _px_map(prev)
    weekend = (px_now == px_prev) or all(px_now.get(k) == px_prev.get(k) for k in y_dec if k in px_now)
    rows = []
    for sym, d in y_dec.items():
        act = (d or {}).get("action", ""); nm = (d or {}).get("name", sym)
        pn, pp = px_now.get(sym), px_prev.get(sym)
        chg = None
        if isinstance(pn, (int, float)) and isinstance(pp, (int, float)) and pp:
            chg = (pn - pp) / pp * 100
        # 机械判定:无价变(周末/休市)→未到验证时点;有价变→按动作方向核
        verdict, err = "未到验证时点", ""
        if chg is not None and abs(chg) >= 0.01:
            # 守/观=不动作·价小动仍算未到;减后跌=对·减后涨=时机错;加后涨=对·加后跌=时机错
            if act in ("减", "卖", "清") and chg < -1:
                verdict = "对"
            elif act in ("减", "卖", "清") and chg > 2:
                verdict, err = "错", "时机错"
            elif act in ("加", "买") and chg > 1:
                verdict = "对"
            elif act in ("加", "买") and chg < -2:
                verdict, err = "错", "时机错"
            else:
                verdict = "未到验证时点"
        rows.append({"标的": nm, "代码": sym, "昨日动作": act,
                     "昨价": pp, "今价": pn, "涨跌pct": (round(chg, 2) if chg is not None else None),
                     "判定": verdict, "错在哪": err})
    n_right = sum(1 for r in rows if r["判定"] == "对")
    n_wrong = sum(1 for r in rows if r["判定"] == "错")
    n_pend = sum(1 for r in rows if r["判定"] == "未到验证时点")
    return {"_说明": "★BA1-1 昨日(上一交易日)动作今天看对没对。无价变(周末休市)→未到验证时点·非命中。判错标错在哪。",
            "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]), "对照昨日": "%s-%s-%s" % (prev[:4], prev[4:6], prev[6:]),
            "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
            "休市无价变": bool(weekend), "计数": {"对": n_right, "错": n_wrong, "未到验证时点": n_pend},
            "逐只": rows}


# ── BA1-2 今日新事件对宏观regime=支持/中性/证伪 ──
_REGIME_RULES = [
    # (关键词, 涉及regime分量, 命中方向)  证伪=与当前regime相反的强信号
    (r"降息|宽松|放水|流动性宽|QE", "高利率", "证伪"),
    (r"加息|收紧|鹰派|利率上调|通胀超预期|CPI.*超", "高利率", "支持"),
    (r"暴跌|崩盘|恐慌|VIX.*飙|risk.?off|避险", "低恐慌", "证伪"),
    (r"新高|风险偏好|risk.?on|反弹", "低恐慌", "支持"),
    (r"衰退|裁员潮|失业.*升|硬着陆|recession", "无衰退定价", "证伪"),
    (r"美元走强|美元反弹|DXY.*升|dollar.*strong", "美元转弱", "证伪"),
    (r"美元走弱|美元贬|DXY.*跌", "美元转弱", "支持"),
]


def event_vs_macro(dc):
    daily = _rj(ROOT / "data/evidence_chain" / f"daily_{dc}.json")
    macro = _rj(ROOT / "data/market" / f"macro_flow_{dc}.json")
    content = _rj(ROOT / "data/content" / f"opus5_content_{dc}.json")
    # regime串:优先Opus5八节·否则据macro_flow指标派生
    regime = ""
    z = content.get("★一之二_资金流动层（第③层·今日首次建成）") or content.get("一之二_资金流动层（第③层·今日首次建成）") or {}
    if isinstance(z, dict):
        for v in z.values():
            if isinstance(v, str) and "regime" in v:
                regime = v; break
    if not regime:
        ind = {x.get("指标"): x.get("值") or x.get("当日值") for x in macro.get("核心指标", [])}
        regime = "高利率+低恐慌+无衰退定价(据macro_flow:10Y%s/VIX%s)" % (ind.get("10年期美债收益率"), ind.get("VIX恐慌指数"))
    links = daily.get("links", []) or []
    rows = []
    n_falsify = 0
    for lk in links:
        ev = str(lk.get("evidence") or ""); node = str(lk.get("node") or "")
        # ★防误报:剥除阈值/规则描述文字(如「（阈值 VIX>+5.0%或倒挂→避险）」·非真事件·否则关键词误伤)
        ev_clean = re.sub(r"[（(]阈值[^）)]*[）)]", "", ev)
        ev_clean = re.sub(r"规则判「[^」]*」", "", ev_clean)
        cls, comp = "中性", ""
        # 先信引擎自身结论:判「…中性/需盯/未到regime反转…」→中性(不误判证伪)
        engine_concl = re.search(r"判「([^」]*)」", ev_clean)
        if engine_concl and re.search(r"中性|需盯|未到regime反转|无重大新闻|维持|沿用", engine_concl.group(1)):
            cls, comp = "中性", "引擎判中性/未反转"
        else:
            for pat, c, direction in _REGIME_RULES:
                if re.search(pat, ev_clean):
                    cls, comp = direction, c
                    break
        if cls == "证伪":
            n_falsify += 1
        title = re.sub(r"\s+", " ", ev)[:90]
        rows.append({"节点": node[:24], "新闻摘": title, "对regime": cls, "涉及分量": comp})
    warn = ("★regime判定被今日事件证伪·须重判(命中%d条证伪信号)" % n_falsify) if n_falsify else ""
    return {"_说明": "★BA1-2 今日新事件对当前regime=支持/中性/证伪。机械关键词规则(不做投资判断)·不确定=中性。证伪→产品显性告警。",
            "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]), "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
            "当前regime": regime[:120], "计数": {"支持": sum(1 for r in rows if r["对regime"] == "支持"),
            "中性": sum(1 for r in rows if r["对regime"] == "中性"), "证伪": n_falsify},
            "★证伪告警": warn, "逐条": rows}


# ── BA1-3 决策质量分 ──
def decision_quality(dc):
    dec = _rj(ROOT / "data/pdca" / f"decisions_{dc}.json").get("decisions", {})
    sc = _rj(ROOT / "data/pdca/judgment_scorecard.json").get("entries", [])
    rows = []
    for sym, d in dec.items():
        act = (d or {}).get("action", ""); nm = (d or {}).get("name", sym)
        # 匹配支持该只的judgment(判断文本含股名·或ticker匹配)
        deps = [e for e in sc if (nm and nm in str(e.get("判断", ""))) or
                (e.get("ticker") == sym) or (e.get("symbol") == sym)]
        num, n = 0.0, 0
        for e in deps:
            grade = str(e.get("依据等级", "C")).strip()[:1]
            hold = e.get("把握分")
            if isinstance(hold, (int, float)):
                num += hold * COEF.get(grade, 0.3); n += 1
        q = round(num / n, 2) if n else None
        flag = "低把握动作·依据不足" if (q is not None and q < 2.0) else ("依据不足·无关联判断" if q is None else "")
        rows.append({"标的": nm, "代码": sym, "动作": act, "依赖判断数": n, "质量分": q,
                     "标记": flag, "依据等级分布": [str(e.get("依据等级")) for e in deps]})
    scored = [r for r in rows if r["质量分"] is not None]
    low = [r for r in rows if r["标记"].startswith("低把握")]
    return {"_说明": "★BA1-3 决策质量分=Σ(把握分×依据系数)/依赖判断数。系数A=1.0/B=0.6/C=0.3。<2.0标低把握。每动作带分进产品。",
            "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]), "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
            "系数": COEF, "计数": {"有分动作": len(scored), "低把握(<2.0)": len(low),
            "均分": (round(sum(r["质量分"] for r in scored) / len(scored), 2) if scored else None)},
            "逐只": rows}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    dc = a.date.replace("-", "")
    outs = {"action_review": action_review(dc), "event_vs_macro": event_vs_macro(dc), "decision_quality": decision_quality(dc)}
    D = ROOT / "data" / "pdca"; D.mkdir(parents=True, exist_ok=True)
    for nm, obj in outs.items():
        p = D / f"{nm}_{dc}.json"
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        b = p.read_bytes(); json.loads(b.decode())
        print("[%s] → %s · 乱码%d" % (nm, p.name, b.count(b"\xef\xbf\xbd")))
    ar, ev, dq = outs["action_review"], outs["event_vs_macro"], outs["decision_quality"]
    print("  BA1-1 昨日动作:", ar["计数"], "· 休市无价变" if ar["休市无价变"] else "")
    print("  BA1-2 事件对regime:", ev["计数"], ("· " + ev["★证伪告警"]) if ev["★证伪告警"] else "· 无证伪")
    print("  BA1-3 决策质量分:", dq["计数"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
