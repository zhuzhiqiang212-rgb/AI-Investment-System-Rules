#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主池39·行业分布 + 按市场确认状态切行业（派工单F-13·2026-07-21）。
★正式主池定义(F-13):主池 = ①四项象限一致(分歧false) 且 ②该象限为①(强者加速) = 39只。
  「分歧false」只说明四项落同一象限·没说哪个象限;四项一致地恶化(④)也是false→不得只报89。
★只算不筛选·不出买卖清单·不改尺·不合并总分·不锚死名单(名单每日现算)。
读 quadrant/pool_state。输出 pool39_industry。用法：python scripts/pool39_industry.py --date 20260721"""
import argparse, json, sys
from pathlib import Path
from collections import Counter, defaultdict
ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "data" / "screen"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="20260721"); a = ap.parse_args()
    d = a.date
    sys.stdout.reconfigure(encoding="utf-8")
    q = json.loads((S / f"quadrant_{d}.json").read_text(encoding="utf-8"))
    ps = json.loads((S / f"pool_state_{d}.json").read_text(encoding="utf-8"))
    cq = q["cards"]; cs = ps["cards"]

    # 分歧false总数 + 拆解(堵漏·不得只报89)
    nd = [c for c, r in cq.items() if not r["象限分歧"]]
    breakdown = Counter(cq[c]["主象限(利润)"] for c in nd)
    # 正式主池39 = 分歧false 且 象限①
    pool39 = [c for c in nd if cq[c]["主象限(利润)"] == "①"]
    ind_of = {c: (cq[c].get("名称行业") or "(未分类)") for c in cq}
    ind432 = Counter(ind_of[c] for c in cq)

    # 39只名单(代码+行业+象限+状态+得分)
    roster = []
    for c in pool39:
        st = cs.get(c, {})
        roster.append({"code": c, "行业": ind_of[c], "象限": "①强者加速",
                       "市场确认状态": st.get("市场确认状态"), "变化证据得分": st.get("变化证据得分")})
    roster.sort(key=lambda x: -(x["变化证据得分"] or -1))

    # 行业分布(按加速占比排序)
    by_ind = defaultdict(list)
    for c in pool39:
        by_ind[ind_of[c]].append(c)
    ind_rows = []
    for ind, members in by_ind.items():
        tot = ind432[ind]
        ind_rows.append({"行业": ind, "进主池39": len(members), "该行业432总数": tot,
                         "行业内加速占比%": round(len(members) / tot * 100, 1) if tot else None,
                         "成员": sorted(members)})
    ind_rows.sort(key=lambda r: (-(r["行业内加速占比%"] or 0), -r["进主池39"]))
    top3_all = ind_rows[:3]
    top3_ge3 = [r for r in ind_rows if r["该行业432总数"] >= 3][:3]

    # 按市场确认状态切行业
    state_ind = {}
    state_codes = defaultdict(list)
    for c in pool39:
        state_codes[cs.get(c, {}).get("市场确认状态")].append(c)
    for st, codes in state_codes.items():
        cc = Counter(ind_of[c] for c in codes)
        state_ind[st] = {"只数": len(codes),
                         "行业分布": [{"行业": k, "只数": v, "成员": sorted([c for c in codes if ind_of[c] == k])}
                                  for k, v in cc.most_common()]}
    # 正在确认集中度
    zconf = state_codes.get("正在确认", [])
    zc = Counter(ind_of[c] for c in zconf)
    z_top = zc.most_common(5)

    doc = {
        "_F13定义": "★主池 = 分歧false 且 象限①(强者加速) = 39只。分歧false只说明四项同象限·未说哪象限;四项一致恶化(④)也false。不得只报89。",
        "分歧false总数": len(nd),
        "分歧false拆解": {"①强者加速(真主池)": breakdown["①"], "②强者减速": breakdown["②"],
                     "④持续恶化(四项一致地恶化·也是false)": breakdown["④"], "—无法判定象限(数据不足)": breakdown["—"]},
        "主池39名单": roster,
        "行业数": len(by_ind),
        "行业分布(按加速占比降序)": ind_rows,
        "加速占比最高三(全部·含小样本)": [{k: v for k, v in r.items() if k != "成员"} for r in top3_all],
        "加速占比最高三(行业≥3只·更代表趋势)": [{k: v for k, v in r.items() if k != "成员"} for r in top3_ge3],
        "小样本提示": "n≤2 的100%占比是噪声·看行业趋势以≥3只版为准",
        "按市场确认状态的行业分布": state_ind,
        "正在确认集中度top": [{"行业": k, "只数": v} for k, v in z_top],
    }
    p = S / f"pool39_industry_{d}.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("wrote", p.name, p.stat().st_size, "字节 · EFBFBD=", p.read_bytes().count(b"\xef\xbf\xbd"))
    print("分歧false", len(nd), "拆解:", dict(breakdown), "→ 主池39")
    print("答①: 39只落", len(by_ind), "个行业·加速占比top3(≥3只):", [(r["行业"], r["行业内加速占比%"], f'{r["进主池39"]}/{r["该行业432总数"]}') for r in top3_ge3])
    print("答②: 正在确认", len(zconf), "只·集中行业top:", z_top[:5], "· 最集中一个:", z_top[0] if z_top else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
