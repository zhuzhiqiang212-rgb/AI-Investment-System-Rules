#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
cross_account_exposure.py —— S1(轮55):跨账户单只合并暴露(从未被计算过的视角)。
现状:集中度检查都按账户或按驱动组·缺「同一只跨账户合并看」。实例:软银富途11.93%+SBI16.31%分开都没破单只20%·合并没人算过。
· 主战场合计 A = 富途A + SBI A(IBKR/bitFlyer 不进目标管理·另列附录一行)
· 每只 跨账户合并市值 ÷ 合计A = 合并权重·降序·对照单只20%上限标破限
· 每只同时给:合并跨度贡献pp / 置信度 / 锚龄天数 / 是否blind(让高收益·高波动·低把握集中在同一只时一眼可见)
★S1-3 只给暴露事实·不给操作建议。输出 data/risk/cross_account_{date}.json。
用法: python scripts/cross_account_exposure.py --date 2026-07-30
"""
import argparse, json, sys, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SINGLE_MAX = 0.20  # 单只上限(07-19尺)


def _age(today, d):
    try:
        return (today - datetime.date(int(d[:4]), int(d[5:7]), int(d[8:10]))).days
    except Exception:
        return None


def build(date_h):
    dc = date_h.replace("-", "")
    today = datetime.date(int(date_h[:4]), int(date_h[5:7]), int(date_h[8:10]))
    tg = json.loads((ROOT / "data/target" / f"target_gap_{dc}.json").read_text(encoding="utf-8"))
    fc = json.loads((ROOT / "data/forecast" / f"forecast_{date_h}.json").read_text(encoding="utf-8"))
    vi = json.loads((ROOT / "data/valuation/val_inputs.json").read_text(encoding="utf-8")).get("holdings", {})
    acc_map = {"FUTU": "富途", "SBI": "SBI"}
    f1y = {(acc_map.get(f.get("account"), f.get("account")), f.get("ticker")): f
           for f in fc.get("forecasts", []) if f.get("horizon") == "1y"}

    A_futu = tg["富途"].get("当日总资产A_USD") or 0
    A_sbi = tg["SBI"].get("当日总资产A_USD") or 0
    A_total = A_futu + A_sbi

    merged = {}
    for a_cn in ("富途", "SBI"):
        for r in tg[a_cn].get("逐只(按贡献pp降序)", []):
            code = r.get("code")
            mv = r.get("market_value_usd") or 0
            f = f1y.get((a_cn, code)); px = r.get("price_local_0730", r.get("price_local"))
            m = merged.setdefault(code, {"code": code, "name": r.get("name"), "合并市值_USD": 0.0,
                                         "账户": [], "blind": False, "跨度贡献_raw": 0.0,
                                         "置信度": None, "锚fair": r.get("fair")})
            m["合并市值_USD"] += mv
            m["账户"].append(a_cn)
            if r.get("blind"):
                m["blind"] = True
            if f and px:
                w = mv / A_total
                scen = f.get("scenarios", [])
                s1m = sum(scen[0].get("range", [0, 0])) / 2; s3m = sum(scen[2].get("range", [0, 0])) / 2
                m["跨度贡献_raw"] += w * ((s1m / px - 1) - (s3m / px - 1))
                m["置信度"] = f.get("confidence")

    # T1-1(轮56):主战场合并总跨度=Σ每只合并跨度贡献(=两账户A加权·数学等价)
    total_span_pp = round(sum(m["跨度贡献_raw"] for m in merged.values()) * 100, 2)
    rows = []
    for code, m in merged.items():
        w = m["合并市值_USD"] / A_total if A_total else 0
        pa = vi.get(code, {}).get("priced_at")
        span_pp = round(m["跨度贡献_raw"] * 100, 2)
        span_share = round(span_pp / total_span_pp * 100, 1) if total_span_pp else None  # T1-2:占全组合总跨度pct
        rows.append({
            "code": code, "name": m["name"], "账户": "+".join(sorted(set(m["账户"]))),
            "合并市值_USD": round(m["合并市值_USD"], 2), "合并权重pct": round(w * 100, 2),
            "破单只20%": w > SINGLE_MAX, "破限幅度pp": round((w - SINGLE_MAX) * 100, 2) if w > SINGLE_MAX else 0,
            "合并跨度贡献pp": span_pp, "合并跨度贡献占全组合总跨度pct": span_share,
            # T1-3:★只算不设闸——25%阈值尚未经董事长拍板·未拍板前不是规矩·任何闸不得因此FAIL
            "若采用25%上限则破限(★尚未拍板·仅标注不设闸)": (span_share is not None and span_share > 25),
            "置信度": m["置信度"], "锚龄天数": _age(today, pa) if pa else None, "blind": m["blind"],
        })
    rows.sort(key=lambda x: -x["合并权重pct"])
    rows_by_span = sorted(rows, key=lambda x: -(x["合并跨度贡献占全组合总跨度pct"] or 0))
    top = rows[0] if rows else {}
    top_span = rows_by_span[0] if rows_by_span else {}

    # IBKR/bitFlyer 附录一行(不进主战场目标管理)
    appendix = tg.get("IBKR_bitFlyer", "不做目标管理(07-19尺+07-30确认)·仅附录·不进主战场合计A")

    out = {"_说明": "跨账户单只合并暴露(S1·轮55)+跨度贡献占比(T1·轮56)。★只给暴露事实·不给操作建议·不设闸(T1-3)。",
           "date": date_h, "主战场合计A_USD": round(A_total, 2),
           "富途A_USD": round(A_futu, 2), "SBI_A_USD": round(A_sbi, 2), "单只上限": SINGLE_MAX,
           "主战场合并总跨度pp": total_span_pp,
           "跨账户合并(按合并权重降序)": rows,
           "跨账户合并(按跨度贡献占比降序)": rows_by_span,
           "最大单一暴露_按市值": {"标的": top.get("name"), "code": top.get("code"), "合并权重pct": top.get("合并权重pct"),
                             "破单只20%": top.get("破单只20%")},
           "最大单一暴露_按波动贡献": {"标的": top_span.get("name"), "code": top_span.get("code"),
                               "占全组合总跨度pct": top_span.get("合并跨度贡献占全组合总跨度pct"),
                               "现行尺未管此维度": True, "若采用25%上限则破限(★尚未拍板)": top_span.get("若采用25%上限则破限(★尚未拍板·仅标注不设闸)")},
           "破单只20%的标的": [r["name"] for r in rows if r["破单只20%"]],
           "★若采用25%跨度上限则破限的标的(★尚未拍板·仅供参考不设闸)": [r["name"] for r in rows if r["若采用25%上限则破限(★尚未拍板·仅标注不设闸)"]],
           "IBKR_bitFlyer附录": appendix,
           "★口径": "两口径:按市值(合并权重·现行单只20%上限管)与按波动贡献(占全组合总跨度·现行尺未管)。25%跨度上限尚未经董事长拍板·未拍前不是规矩·不设闸。是否动仓是Opus5/董事长裁定。"}
    p = ROOT / "data/risk" / f"cross_account_{date_h}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out, p


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out, p = build(a.date)
    print(f"[cross_account_exposure] → {p.name} · 主战场合计A ${out['主战场合计A_USD']:,.0f}")
    print(f"    破单只20%: {out['破单只20%的标的'] or '无'}")
    for r in out["跨账户合并(按合并权重降序)"][:6]:
        print(f"    {r['name']:8s}({r['账户']}) 合并权重{r['合并权重pct']:>5}% 跨度贡献{r['合并跨度贡献pp']:>5}pp 置信度{r['置信度']} 锚龄{r['锚龄天数']} blind={r['blind']} {'★破20%' if r['破单只20%'] else ''}")


if __name__ == "__main__":
    raise SystemExit(main())
