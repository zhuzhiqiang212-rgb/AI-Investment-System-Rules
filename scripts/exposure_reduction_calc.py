#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
exposure_reduction_calc.py —— R2(轮54):降限测算(只给数·不给建议)。
把破限的驱动组(高AI beta)降到 30% 以内:
  ① 各账户需减少多少美元市值(卖股→现金·A不变·组市值降)
  ② 组内每只「减多少/跨度降多少」的机械可能性(按 跨度贡献pp/权重 排序·★不推荐不写"建议减X")
  ③ 若不减仓·改加入与AI不同向新标的稀释到30%·需加入多少市值(=机会发现要找多大体量)
★Q2-4 规矩不变:只列机械算出的可能性·不排序推荐·不写操作建议。
用法: python scripts/exposure_reduction_calc.py --date 2026-07-30
"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from driver_exposure import GROUP, LIMIT

BROKEN_GROUP = "高AI beta"


def build(date_h):
    dc = date_h.replace("-", "")
    tg = json.loads((ROOT / "data/target" / f"target_gap_{dc}.json").read_text(encoding="utf-8"))
    fc = json.loads((ROOT / "data/forecast" / f"forecast_{date_h}.json").read_text(encoding="utf-8"))
    acc_map = {"FUTU": "富途", "SBI": "SBI"}
    f1y = {(acc_map.get(f.get("account"), f.get("account")), f.get("ticker")): f
           for f in fc.get("forecasts", []) if f.get("horizon") == "1y"}

    out = {"_说明": "降限测算(R2·轮54)。★只给机械算出的数·不排序推荐·不写建议(那是Opus5的活)。"
                    "口径:卖股→现金则A不变、组市值降;加新标的稀释需增A(新资金)。",
           "date": date_h, "破限组": BROKEN_GROUP, "单一环节上限": LIMIT, "账户": {}}
    for a_cn in ("富途", "SBI"):
        A = tg[a_cn].get("当日总资产A_USD") or 0
        members = []
        group_mv = 0.0
        for r in tg[a_cn].get("逐只(按贡献pp降序)", []):
            code = r.get("code")
            if GROUP.get(code) != BROKEN_GROUP:
                continue
            f = f1y.get((a_cn, code)); px = r.get("price_local_0730", r.get("price_local"))
            mv = r.get("market_value_usd") or 0
            if not (f and px and A):
                continue
            group_mv += mv
            w = mv / A
            scen = f.get("scenarios", [])
            s1m = sum(scen[0].get("range", [0, 0])) / 2; s3m = sum(scen[2].get("range", [0, 0])) / 2
            span_contrib = w * ((s1m / px - 1) - (s3m / px - 1))  # 该只对S1−S3跨度的贡献(pp小数)
            members.append({"code": code, "name": r.get("name"), "市值_USD": round(mv, 2), "权重pct": round(w * 100, 2),
                            "跨度贡献pp": round(span_contrib * 100, 2),
                            "跨度贡献pp每1%权重": round(span_contrib * 100 / (w * 100), 3) if w else None,
                            "若全减_组市值降_USD": round(mv, 2),
                            "若全减_跨度降pp": round(span_contrib * 100, 2)})
        # 按 跨度贡献pp/权重 排序(机械·非推荐)
        members.sort(key=lambda m: -(m["跨度贡献pp每1%权重"] or 0))
        grp_w = group_mv / A if A else 0
        # ① 卖股降到30%需减市值:X = group_mv − 0.30×A
        reduce_usd = round(group_mv - LIMIT * A, 2) if grp_w > LIMIT else 0
        # ③ 加新标的稀释到30%需加入:Y = group_mv/0.30 − A
        dilute_add_usd = round(group_mv / LIMIT - A, 2) if grp_w > LIMIT else 0
        out["账户"][a_cn] = {
            "A_USD": round(A, 2), "高AI_beta组市值_USD": round(group_mv, 2), "高AI_beta权重pct": round(grp_w * 100, 2),
            "破限": grp_w > LIMIT, "破限幅度pp": round((grp_w - LIMIT) * 100, 2) if grp_w > LIMIT else 0,
            "①卖股降到30%需减市值_USD": reduce_usd,
            "③加AI不同向新标的稀释到30%需加入市值_USD": dilute_add_usd,
            "②组内每只减仓机械可能性(按跨度贡献pp每1%权重排序·非推荐)": members,
            "★口径": "①卖股:A不变·组市值−X→(组市值−X)/A=30%。③加新仓:增资Y·组市值/(A+Y)=30%。★均为机械算·是否动仓是Opus5/董事长裁定。",
        }
    p = ROOT / "data/risk" / f"reduction_calc_{date_h}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out, p


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out, p = build(a.date)
    print(f"[exposure_reduction_calc] → {p.name}")
    for a_cn in ("富途", "SBI"):
        d = out["账户"][a_cn]
        print(f"--- {a_cn} 高AI beta {d['高AI_beta权重pct']}%(破{d['破限幅度pp']}pp) ---")
        print(f"    ① 卖股降到30% 需减市值 ${d['①卖股降到30%需减市值_USD']:,.0f}")
        print(f"    ③ 加AI不同向新标的稀释到30% 需加入 ${d['③加AI不同向新标的稀释到30%需加入市值_USD']:,.0f}")
        for m in d["②组内每只减仓机械可能性(按跨度贡献pp每1%权重排序·非推荐)"]:
            print(f"       {m['name']:8s} 市值${m['市值_USD']:>10,.0f} 权重{m['权重pct']:>5}% 跨度贡献{m['跨度贡献pp']:>5}pp (每1%权重{m['跨度贡献pp每1%权重']})")


if __name__ == "__main__":
    raise SystemExit(main())
