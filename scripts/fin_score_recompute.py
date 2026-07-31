#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""财务质量分·重算(打回·董事长2026-07-21)：
问题1 industry 之前误取券商选股标签(OTHER/CONCEPT)→改取 plate_type=INDUSTRY 的真行业分类。
问题2 分组错致分位全错→432分作废·重算·并输出各行业公司数分布(查n=1组)。行业组过小(n<3)→改全市场分位并标注。
问题3 自由现金流实为经营性现金流(缺capex)→改名『经营性现金流』。
问题4 毛利率缺8季趋势→标注『仅当前值·趋势未接』。
门槛(市值/60日均成交额/OCF>0·432入围)不变·不重跑;财务值复用 gate_{date}.json;只补行业分类。
用法：python scripts/fin_score_recompute.py --date 20260721"""
import argparse, json, time, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data" / "screen"
W = {"经营性现金流": 25, "毛利率": 25, "资产负债": 20, "在手订单": 20, "成本优势": 10}   # 自由现金流→经营性现金流(缺capex)
MIN_IND = 3   # 行业组≥3只才用行业内分位;否则退全市场分位并标注


def pct_rank(val, arr):
    xs = sorted(x for x in arr if x is not None)
    if not xs or val is None:
        return None
    return round(sum(1 for x in xs if x < val) / len(xs) * 100, 1)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="20260721"); a = ap.parse_args()
    d = a.date
    sys.stdout.reconfigure(encoding="utf-8")
    gate = json.loads((SCREEN / f"gate_{d}.json").read_text(encoding="utf-8"))
    per = gate["per_stock"]
    inbound = [c for c, r in per.items() if r["conclusion"] == "入围"]
    print("入围", len(inbound))

    import futu as ft
    ctx = ft.OpenQuoteContext("127.0.0.1", 11111)
    industry, raw_plates = {}, {}
    try:
        for i in range(0, len(inbound), 200):
            part = inbound[i:i + 200]
            try:
                ret, df = ctx.get_owner_plate(part)
                if ret == ft.RET_OK:
                    for _, r in df.iterrows():
                        c = str(r.get("code"))
                        if str(r.get("plate_type")) == "INDUSTRY":
                            # 同只可能多个INDUSTRY→取第一个(稳定:按plate_name)
                            industry.setdefault(c, str(r.get("plate_name")))
                        raw_plates.setdefault(c, []).append(f"{r.get('plate_name')}[{r.get('plate_type')}]")
            except Exception as e:
                print("owner_plate err", e)
            time.sleep(2.5)
    finally:
        ctx.close()
    n_no_ind = sum(1 for c in inbound if c not in industry)
    for c in inbound:
        industry.setdefault(c, "行业未分类(无INDUSTRY板块)")

    # 各行业公司数分布(查 n=1 组)
    from collections import Counter
    ind_dist = Counter(industry[c] for c in inbound)
    n1 = [k for k, v in ind_dist.items() if v == 1]

    # 维度取值(复用 gate 财务·经营性现金流=OCF·资产负债=100-负债率越低越好)
    dim_val = {c: {
        "经营性现金流": per[c].get("ocf_ttm"),
        "毛利率": per[c].get("gross_margin"),
        "资产负债": (100 - per[c]["debt_asset"]) if per[c].get("debt_asset") is not None else None,
        "在手订单": None,     # OpenD无源
        "成本优势": None,     # OpenD无源
    } for c in inbound}

    by_ind = {}
    for c in inbound:
        by_ind.setdefault(industry[c], []).append(c)

    scores = {}
    miss = {k: 0 for k in W}
    fallback_cnt = 0
    for c in inbound:
        ind = industry[c]; peers = by_ind[ind]
        dims = {}; tot = 0.0; wsum = 0.0; miss_here = 0; used_全市场 = False
        for dim, w in W.items():
            v = dim_val[c][dim]
            if v is None:
                dims[dim] = {"score": 0, "status": "数据未接", "pct": None}
                miss_here += 1; miss[dim] += 1
                continue
            if len(peers) >= MIN_IND:
                arr = [dim_val[p][dim] for p in peers]; basis = f"行业内(n={len(peers)})"
            else:
                arr = [dim_val[p][dim] for p in inbound]; basis = f"全市场(行业组n={len(peers)}<{MIN_IND}·未按行业校正)"
                used_全市场 = True
            pr = pct_rank(v, arr)
            dims[dim] = {"score": pr if pr is not None else 0, "status": "OK", "pct": pr, "raw": v, "basis": basis}
            if pr is not None:
                tot += pr * w; wsum += w
        if used_全市场:
            fallback_cnt += 1
        scores[c] = {"industry": ind, "financial_quality_score": round(tot / wsum, 1) if wsum else 0.0,
                     "分位口径": ("全市场分位(行业组过小·未按行业校正·仅供粗排)" if used_全市场 else "行业内分位"),
                     "缺维度数": miss_here, "维度": dims}

    fin_miss_rate = {k: {"缺": miss[k], "共": len(inbound),
                         "缺失率_pct": round(miss[k] / len(inbound) * 100, 1) if inbound else None} for k in W}

    # 受 0.0 污染排查(董事长2026-07-21问题2):读 _run2 的 0.0 报警 + 本次入围中各维 null 数
    zero_report = {}
    try:
        rr = json.loads((SCREEN / f"_run2_{d}.json").read_text(encoding="utf-8"))
        zero_report = rr.get("财务字段0_0报警", {})
    except Exception:
        pass
    null_by_dim = {dim: [c for c in inbound if dim_val[c][dim] is None] for dim in W}
    affected = {"_说明": "毛利率等利润率字段 OpenD 曾对部分日股(半年报)返回 0.0→已改 ANNUAL口径取真值·且0.0一律转null不当真值参与分位",
                "0_0命中(已转null·来自_run2)": zero_report,
                "入围中各维缺数": {dim: len(null_by_dim[dim]) for dim in W},
                "入围毛利率缺失清单(前20)": null_by_dim["毛利率"][:20]}

    doc = {
        "_说明": "财务质量五维·行业内分位加权。★重算(打回2026-07-21):行业改取 plate_type=INDUSTRY 真分类;"
               "行业组<3只退全市场分位并标注;自由现金流→经营性现金流(缺capex);毛利率ANNUAL口径真值·0.0转null;毛利率仅当前值(趋势未接)。",
        "受0_0污染排查": affected,
        "行业分类标准": {"名称": "Futu OpenD 行业板块 get_owner_plate(plate_type=INDUSTRY)",
                   "说明": "券商/数据商行业分类(US 约145行业·粒度近GICS子行业;JP 近东证业种)·非官方GICS/东证授权数据·如实标",
                   "版本": "OpenD 实时板块", "数据日": d, "取数方式": "get_owner_plate 逐只取所属INDUSTRY板块"},
        "字段更名": {"自由现金流→经营性现金流": "OpenD无capex→无法算真自由现金流·改用经营性现金流TTM·不得叫自由现金流(会误导)"},
        "毛利率口径": "仅当前值(最近季)·8季趋势未接(OpenD filter只给最近季)·规则要求趋势比水平更重要→候选卡须标『毛利率仅当前值·趋势未接』",
        "入围数": len(inbound),
        "行业无分类数(无INDUSTRY板块)": n_no_ind,
        "各行业公司数分布": dict(sorted(ind_dist.items(), key=lambda x: -x[1])),
        "n1_行业组(单只·分位不可靠已退全市场)": n1,
        "退全市场分位的只数": fallback_cnt,
        "财务五维缺失率": fin_miss_rate,
        "scores": scores,
    }
    p = SCREEN / f"fin_score_{d}.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("wrote", p.name, p.stat().st_size, "bytes · EFBFBD=", p.read_bytes().count(b"\xef\xbf\xbd"))
    print("行业数:", len(ind_dist), "· n=1组:", len(n1), "· 无分类:", n_no_ind, "· 退全市场:", fallback_cnt)

    # 回填 candidates 的 financial_quality_score + industry
    cp = SCREEN / f"candidates_{d}.json"
    cd = json.loads(cp.read_text(encoding="utf-8"))
    for c in cd["candidates"]:
        s = scores.get(c["code"])
        if s:
            c["financial_quality_score"] = s["financial_quality_score"]
            c["industry"] = s["industry"]
            c["分位口径"] = s["分位口径"]
    cp.write_text(json.dumps(cd, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("回填 candidates ✓")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
