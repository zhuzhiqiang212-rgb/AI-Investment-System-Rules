# -*- coding: utf-8 -*-
"""★轮133 A:防御仓15%下限(分账户·看板)。
★★★轮224 董事长裁定《防御仓定义统一》:作废旧【Opus5静态名单】·改由 defensive_def 单一判据现算。
判据(三条缺一不可)=①行业属性(医药/保险/公用/电信/必需消费) ②现金流稳定 ③低AI关联。★全系统只留一个防御定义。
分账户算防御仓占比·对照15%下限·报破没破。现金/债不在本判据(只分类股票)。"""
import sys, json, argparse, glob
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import defensive_def   # ★★★单一防御判据(唯一真相源)

LOWER_LIMIT = 15.0   # 看板:防御仓15%下限


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def per_account(dc):
    tg = _rj(ROOT / "data/target" / f"target_gap_{dc}.json")
    fx = (tg.get("富途", {}) or {}).get("fx_used")   # USDJPY
    res = {}
    # 富途:futu_positions·US=USD/JP=JPY÷FX 归一
    fpos = _rj(ROOT / "data/accounts" / f"futu_positions_{dc}.json").get("futu_positions", [])
    if fx and fpos:
        tot = 0.0; deff = []
        for h in fpos:
            s = str(h.get("symbol") or ""); mv = h.get("broker_market_val"); nm = h.get("name") or ""
            if not isinstance(mv, (int, float)):
                continue
            usd = mv if s.startswith("US.") else (mv / fx if s.startswith("JP.") else mv)
            tot += usd
            if defensive_def.is_defensive(s, name=nm):        # ★单一判据
                deff.append((s, usd, nm))
        dv = sum(v for _, v, _ in deff)
        res["富途"] = _pack(tot, deff, dv)
    # SBI:sbi_sleeve·JPY 同币种
    sbf = sorted(glob.glob(str(ROOT / "data/accounts/sbi_sleeve_*.json")))
    if sbf:
        sh = _rj(sbf[-1]).get("holdings", [])
        tot = sum(h.get("market_value_jpy", 0) for h in sh)
        deff = [("JP." + str(h.get("code")), h.get("market_value_jpy", 0), h.get("name") or "")
                for h in sh if defensive_def.is_defensive("JP." + str(h.get("code")), name=h.get("name") or "")]
        dv = sum(v for _, v, _ in deff)
        if tot:
            res["SBI"] = _pack(tot, deff, dv)
    return res


def _pack(tot, deff, dv):
    tot = tot or 1
    pct = dv / tot * 100
    def _det(s, v, nm):
        _, ind, why = defensive_def.classify(s, name=nm)
        return {"symbol": s, "名称": nm, "行业": ind, "判据": why, "占比pct": round(v / tot * 100, 1)}
    return {
        "防御仓占比pct": round(pct, 1), "对照下限pct": LOWER_LIMIT,
        "★破15%下限": pct < LOWER_LIMIT, "达标": pct >= LOWER_LIMIT,
        "防御明细": [_det(s, v, nm) for s, v, nm in deff],
    }


def concentration_delta(dc, decisions):
    """★轮134 C-2:换仓后【单只集中度】变化(币种归一·富途口径)。decisions=[{标的,方向,股数}]。
    ★机器算·非判断。空/无有效换仓→返回 None(待决策清单)。返回 {前最大单只pct,后最大单只pct,delta,明细}。"""
    if not decisions:
        return None
    tg = _rj(ROOT / "data/target" / f"target_gap_{dc}.json")
    fx = (tg.get("富途", {}) or {}).get("fx_used")
    fpos = _rj(ROOT / "data/accounts" / f"futu_positions_{dc}.json").get("futu_positions", [])
    if not (fx and fpos):
        return {"★NK4": "缺 富途持仓/FX·集中度变化不算(不估算)"}
    val = {}   # symbol → USD市值
    pps = {}   # symbol → 每股USD
    for h in fpos:
        s = str(h.get("symbol") or ""); mv = h.get("broker_market_val"); q = h.get("quantity") or 0
        if not isinstance(mv, (int, float)):
            continue
        usd = mv if s.startswith("US.") else (mv / fx if s.startswith("JP.") else mv)
        val[s] = val.get(s, 0) + usd
        if q:
            pps[s] = (mv / q) if s.startswith("US.") else ((mv / q) / fx if s.startswith("JP.") else mv / q)
    before_tot = sum(val.values()) or 1
    before_max = max(val.values()) / before_tot * 100 if val else 0
    after = dict(val)
    for d in decisions:
        s = d.get("标的"); q = d.get("股数"); dirn = str(d.get("方向") or "")
        p = pps.get(s)
        if not (s and isinstance(q, (int, float)) and p):
            continue
        if "卖" in dirn or "换出" in dirn:
            after[s] = max(0, after.get(s, 0) - q * p)
        elif "买" in dirn or "换入" in dirn:
            after[s] = after.get(s, 0) + q * p
    after_tot = sum(after.values()) or 1
    after_max = max(after.values()) / after_tot * 100 if after else 0
    return {"前_最大单只pct": round(before_max, 1), "后_最大单只pct": round(after_max, 1),
            "delta_pp": round(after_max - before_max, 1), "对照看板单只20%": "破" if after_max > 20 else "未破",
            "_口径": "富途·币种归一·仅算单只上限变化(驱动/防御变化同法可扩)"}


def build(dc):
    out = {
        "_说明": "★轮133/224 防御仓15%下限(分账户)。★★★轮224董事长裁定《防御仓定义统一》:作废旧静态名单·由 defensive_def 单一判据现算(全系统唯一防御定义)。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "★统一判据(defensive_def·三条缺一不可)": "①行业属性∈{医药/制药/保险/公用事业/电信/必需消费} ②现金流稳定 ③低AI关联(不属AI供应链)。只满足③=分散非防御。",
        "★防御行业集": sorted(defensive_def.DEFENSIVE_INDUSTRIES),
        "分账户": per_account(dc),
    }
    (ROOT / "data/risk" / f"defensive_ratio_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    for acc, r in o["分账户"].items():
        print("%s 防御仓 %.1f%% vs 15%%下限 → %s ｜明细:%s" % (
            acc, r["防御仓占比pct"], "★破下限(不足)" if r["★破15%下限"] else "达标",
            "·".join("%s[%s]%.1f%%" % (d["名称"], d["行业"], d["占比pct"]) for d in r["防御明细"]) or "(无防御持仓)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
