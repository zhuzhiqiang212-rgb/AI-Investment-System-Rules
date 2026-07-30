#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
driver_exposure.py —— Q2(轮53):单一驱动暴露度(组合同向性)。
按 ★NEXT_TASK §一驱动归组·每个账户算:各驱动组权重合计 + 每组对 S1−S3 跨度的贡献
  (组内 Σ权重×(S1中值涨幅 − S3中值涨幅))·并对照 07-19 尺「单一环节上限30%」标破限。
★Q2-4 只给暴露度事实·不给操作建议。输出 data/risk/driver_exposure_{date}.json。
用法: python scripts/driver_exposure.py --date 2026-07-30
"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

# ★NEXT_TASK §一驱动归组(ticker → 组)
GROUP = {
    "US.NVDA": "高AI beta", "JP.6857": "高AI beta", "US.AVGO": "高AI beta",
    "US.TSM": "高AI beta", "US.SNDK": "高AI beta", "JP.9984": "高AI beta",  # 软银Arm占权益39.7%
    "US.MSFT": "中AI beta",
    "US.MSTR": "加密beta", "US.COIN": "加密beta", "US.CRCL": "加密beta",
    "JP.8766": "日本利率受益",
    "JP.7203": "日元/全球需求", "JP.8001": "日元/全球需求",
    "JP.4568": "独立驱动", "JP.7974": "独立驱动", "JP.6758": "独立驱动", "JP.7832": "独立驱动",
    "US.SPCX": "非上市",
}
LIMIT = 0.30  # 07-19尺:单一环节上限30%


def build(date_h):
    dc = date_h.replace("-", "")
    tg = json.loads((ROOT / "data/target" / f"target_gap_{dc}.json").read_text(encoding="utf-8"))
    fc = json.loads((ROOT / "data/forecast" / f"forecast_{date_h}.json").read_text(encoding="utf-8"))
    acc_map = {"FUTU": "富途", "SBI": "SBI"}
    f1y = {(acc_map.get(f.get("account"), f.get("account")), f.get("ticker")): f
           for f in fc.get("forecasts", []) if f.get("horizon") == "1y"}

    out = {"_说明": "单一驱动暴露度(Q2·轮53)。★只给暴露度事实·不给操作建议(Q2-4)。"
                    "跨度贡献=组内Σ权重×(S1中值涨幅−S3中值涨幅)·对照07-19尺单一环节上限30%。",
           "date": date_h, "单一环节上限": LIMIT, "账户": {}}
    for a_cn in ("富途", "SBI"):
        A = tg[a_cn].get("当日总资产A_USD") or 0
        groups = {}
        total_span = 0.0
        for r in tg[a_cn].get("逐只(按贡献pp降序)", []):
            code = r.get("code"); g = GROUP.get(code)
            f = f1y.get((a_cn, code))
            px = r.get("price_local_0730", r.get("price_local"))
            if not (g and f and px and A):
                continue
            w = (r.get("market_value_usd") or 0) / A
            scen = f.get("scenarios", [])
            s1_mid = sum(scen[0].get("range", [0, 0])) / 2
            s3_mid = sum(scen[2].get("range", [0, 0])) / 2
            span_contrib = w * ((s1_mid / px - 1) - (s3_mid / px - 1))  # 权重×(S1涨幅−S3涨幅)
            gg = groups.setdefault(g, {"权重合计": 0.0, "跨度贡献": 0.0, "成分": []})
            gg["权重合计"] += w
            gg["跨度贡献"] += span_contrib
            gg["成分"].append(code)
            total_span += span_contrib
        # 占比 + 破限
        for g, gg in groups.items():
            gg["权重合计"] = round(gg["权重合计"], 4)
            gg["跨度贡献pp"] = round(gg["跨度贡献"] * 100, 2)
            gg["跨度贡献占比pct"] = round(gg["跨度贡献"] / total_span * 100, 1) if total_span else None
            gg["★破单一环节30%"] = (gg["权重合计"] > LIMIT)
            gg["破限幅度pp"] = round((gg["权重合计"] - LIMIT) * 100, 2) if gg["权重合计"] > LIMIT else 0
            del gg["跨度贡献"]
        # 命运变量:跨度贡献占比最大的组
        top = max(groups.items(), key=lambda kv: kv[1]["跨度贡献占比pct"] or 0) if groups else (None, {})
        out["账户"][a_cn] = {
            "A_USD": A, "S1_S3总跨度pp": round(total_span * 100, 2), "驱动组": groups,
            "★命运变量": {"驱动组": top[0], "权重合计pct": round((top[1].get("权重合计") or 0) * 100, 1),
                        "占S1_S3跨度pct": top[1].get("跨度贡献占比pct")} if top[0] else None,
            "破单一环节30%的组": [g for g, gg in groups.items() if gg["★破单一环节30%"]],
        }
    p = ROOT / "data/risk" / f"driver_exposure_{date_h}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out, p


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out, p = build(a.date)
    print(f"[driver_exposure] → {p.name}")
    for a_cn in ("富途", "SBI"):
        d = out["账户"][a_cn]
        print(f"--- {a_cn} S1−S3总跨度 {d['S1_S3总跨度pp']}pp · 破30%组: {d['破单一环节30%的组']} ---")
        for g, gg in sorted(d["驱动组"].items(), key=lambda kv: -(kv[1]['跨度贡献占比pct'] or 0)):
            flag = "★破30%" if gg["★破单一环节30%"] else ""
            print(f"    {g:12s} 权重{gg['权重合计']*100:5.1f}% 跨度贡献{gg['跨度贡献pp']:6.2f}pp 占跨度{gg['跨度贡献占比pct']}% {flag}")
        c = d["★命运变量"]
        print(f"    ★命运变量: {c['驱动组']} 占权重{c['权重合计pct']}%·贡献S1−S3跨度{c['占S1_S3跨度pct']}%")


if __name__ == "__main__":
    raise SystemExit(main())
