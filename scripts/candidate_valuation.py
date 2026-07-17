#!/usr/bin/env python3
"""机会池候选估值 + 一句话研究（董事局工单2026-07-17）· 只读不下单

治「机会池候选满屏 估值待接/护城河待接/未入判断包」。给每只有真代码的候选补：
  ① 估值：EDGAR 取真·多年 EPS → 中周期正常化(穿周期均值)× 板块中枢PE → 便宜/中枢/贵位，与现价比
     (方法同持仓：周期股用中周期正常化盈利、不锚景气高点。缺权威源→待接·不编)
  ② 一句话研究：干嘛的、有没有护城河、为什么进这个池(哪个承接节点)
  ③ 架构师若给了候选中周期估算(architect_candidate_est_*.json)→并列渲染(标非权威·可靠度)

⚠边界(CLAUDE.md §1)：本模块【机械】取真历史EPS + 用透明规则(穿周期均值×板块PE)算【候选级】区间，
  标"候选估值·机械算·非精调"。它够拿来比"该不该换"，但不是精调结论；
  精调(哪几年正常/该给几倍)属分析判断，架构师产出后覆盖。缺真源、架构师也没给→老实标待接+原因。

产物：data/valuation/candidate_valuation_{date}.json
用法：python scripts/candidate_valuation.py --date 20260717
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))

# 每只候选的一句话研究(干嘛的+护城河+为什么在池里)——机械知识、非当日判断
RESEARCH = {
    "US.AMD": ("CPU/GPU 设计商，MI 系列是英伟达在 AI 加速卡上的主要挑战者",
               "有 x86 生态 + 先进制程绑定台积电，但 AI 软件生态(CUDA)落后英伟达 → 护城河中",
               "算力节点"),
    "US.MRVL": ("数据中心定制芯片(ASIC)+光/网络互连，AI 基建的‘卖铲子’",
                "定制芯片设计门槛高、客户粘性强 → 护城河中偏宽", "算力节点"),
    "US.UMC": ("台湾成熟制程晶圆代工(非先进制程)", "成熟制程壁垒低于台积电、偏周期 → 护城河窄", "算力/代工节点"),
    "US.ASML": ("光刻机独家垄断(EUV 全球唯一)", "EUV 独此一家、不可替代 → 护城河极宽", "半导体设备节点"),
    "US.AMAT": ("半导体设备龙头(沉积/刻蚀等全线)", "设备种类全、与晶圆厂深度绑定 → 护城河宽", "半导体设备节点"),
    "US.LRCX": ("刻蚀/沉积设备龙头(存储厂关键供应商)", "刻蚀细分领先、存储资本开支直接受益 → 护城河宽", "半导体设备节点"),
    "US.KLAC": ("量检测设备近乎垄断", "量测环节壁垒极高、几无对手 → 护城河极宽", "半导体设备节点"),
    "US.MU": ("DRAM/NAND 存储三巨头之一", "存储是重资产强周期、HBM 是 AI 亮点但商品属性强 → 护城河窄→中", "存储节点"),
    "US.GFS": ("格芯·成熟/特色制程代工", "特色工艺有一定粘性、但非先进制程 → 护城河窄→中", "代工节点"),
    "US.VST": ("美国独立发电商(含核电/燃气)", "电力资产 + AI 数据中心用电爆发 → 护城河中(受管制)", "电力核电节点"),
    "US.CEG": ("美国最大核电运营商", "核电牌照壁垒极高、AI 数据中心长约受益 → 护城河宽", "电力核电节点"),
    "US.GEV": ("GE 电力设备(燃气轮机/电网)", "电网设备 + 电力资本开支周期 → 护城河中偏宽", "电力核电节点"),
    "US.CCJ": ("全球最大铀矿商之一", "铀矿资源禀赋 + 核电复兴需求 → 护城河中偏宽", "电力核电节点"),
    "JP.8035": ("东京电子·涂胶显影/刻蚀设备龙头", "日系设备龙头、与台积电深度绑定 → 护城河宽", "半导体设备节点"),
    "JP.285A": ("铠侠·NAND 存储原厂", "存储强周期、AI 缺货尖峰不可持续 → 护城河窄", "存储节点"),
    "HK.00981": ("中芯国际·中国大陆代工龙头", "受出口管制约束、政策扶持 vs 技术代差 → 护城河窄→中", "代工节点"),
    "JP.7735": ("斯库林·涂胶清洗设备", "细分设备有位置、规模小于东电 → 护城河中", "半导体设备节点"),
    "JP.6590": ("芝浦机电·半导体/FPD 设备", "细分设备商 → 护城河窄→中", "半导体设备节点"),
    "JP.6951": ("日本电子·电子显微镜/分析仪器", "科学仪器细分龙头 → 护城河中", "半导体设备节点"),
}
# 板块中枢PE(穿周期·保守·不锚景气高点)——机械参数、可迭代
SECTOR_PE = {"算力": 22, "半导体设备": 20, "代工": 15, "存储": 12, "电力核电": 18}


def _edgar():
    try:
        import edgar_financials as E
        return E
    except Exception:
        return None


def _prices(codes: list) -> dict:
    try:
        from futu import OpenQuoteContext, RET_OK
    except Exception:
        return {}
    out = {}
    try:
        q = OpenQuoteContext(host="127.0.0.1", port=11111)
        for b in [codes[i:i + 20] for i in range(0, len(codes), 20)]:
            r, d = q.get_market_snapshot(b)
            if r != RET_OK:
                continue
            for _i, x in d.iterrows():
                out[str(x["code"])] = {"price": x.get("last_price"), "pe_ttm": x.get("pe_ttm_ratio"),
                                       "pb": x.get("pb_ratio")}
        q.close()
    except Exception:
        pass
    return out


def _node_of(tk: str, uni: dict) -> str:
    for node, cs in (uni.get("nodes", {}) or {}).items():
        for c in cs or []:
            if str(c.get("ticker")) == tk:
                return node
    return ""


def _pe_key(node: str) -> str:
    for k in SECTOR_PE:
        if k in node:
            return k
    return "算力"


def build(date: str) -> dict:
    uni = {}
    try:
        uni = json.loads((ROOT / "data" / "valuation" / "candidate_universe.json").read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": f"candidate_universe.json 缺：{e}", "candidates": {}}
    cands = {}
    for node, cs in (uni.get("nodes", {}) or {}).items():
        for c in cs or []:
            tk = str(c.get("ticker") or "")
            if tk and tk not in cands and tk not in ("待接", "TBD", "-") and "待接" not in tk:
                cands[tk] = {"name": c.get("name"), "node": node}
    # 架构师候选估算(若有)
    arch = {}
    try:
        ap = sorted((ROOT / "data" / "valuation").glob("architect_candidate_est_*.json"))
        if ap:
            for e in json.loads(ap[-1].read_text(encoding="utf-8")).get("estimates", []):
                arch[str(e.get("ticker"))] = e
    except Exception:
        pass
    prices = _prices(list(cands))
    E = _edgar()
    cikmap = E.cik_map() if E else {}
    out = {}
    for tk, meta in cands.items():
        node = meta["node"]
        rz = RESEARCH.get(tk)
        research = (f"{rz[0]}。{rz[1]}。进池因【{rz[2]}】激活。" if rz else "候选研究待补·不编")
        px = (prices.get(tk) or {}).get("price")
        rec = {"name": meta["name"], "node": node, "research": research,
               "price": px, "pe_ttm": (prices.get(tk) or {}).get("pe_ttm")}
        # ① 架构师估算优先(非权威·标可靠度)
        if tk in arch:
            rec["valuation"] = {"source": "架构师估算", "authoritative": False, **arch[tk]}
            out[tk] = rec
            continue
        # ② 美股 → EDGAR 真历史EPS 算中周期候选区间
        base = tk.split(".")[-1]
        cik = cikmap.get(base.upper())
        if E and cik:
            ser, tag = E.annual_eps(cik)
            eps = [r["eps"] for r in ser if isinstance(r.get("eps"), (int, float))]
            if len(eps) >= 3 and px is not None:
                win = eps[-7:] if len(eps) >= 7 else eps[-5:] if len(eps) >= 5 else eps[-3:]
                norm = sum(win) / len(win)
                pe = SECTOR_PE[_pe_key(node)]
                if norm > 0:
                    mid = norm * pe
                    lo, hi = mid * 0.75, mid * 1.3
                    gap = (px - mid) / mid * 100
                    # ⚠现价远高于机械中枢(>3倍)：多是【高成长股·市场按未来爆发定价】，
                    #   中周期正常化这套会显得"极贵"但那不冤枉——如实标，并提示这类需架构师精调、别只看这个数。
                    #   若低于中枢1/5(可能是ADR折股/货币口径)→老实待接不编。
                    # 交叉核：机械估值说"偏便宜"，但 OpenD 的当前 PE_ttm 却很高(>35) → 两把尺打架，
                    #   多是 EPS 口径/ADR 折股/货币对不上 → 不敢说便宜，老实待接(治联电/科磊那种)。
                    pe_ttm = (prices.get(tk) or {}).get("pe_ttm")
                    # PE_ttm>25 就不可能"便宜"(便宜位对应的是低估)→与机械"偏便宜"矛盾=口径对不上
                    cheap_but_highpe = (px < lo) and isinstance(pe_ttm, (int, float)) and pe_ttm > 25
                    if px < mid / 5 or cheap_but_highpe:
                        rec["valuation"] = {"source": "候选估值", "authoritative": True, "status": "待接",
                                            "reason": (f"机械算说'便宜'但当前市盈率却达 {pe_ttm:.0f} 倍→两把尺打架，"
                                                       f"多是EPS口径/ADR折股/货币对不上·不敢下结论·待架构师核·不编"
                                                       if cheap_but_highpe else
                                                       f"现价{px}远低于机械中枢{mid:.0f}→口径/货币可能对不上·不编")}
                        out[tk] = rec
                        continue
                    verdict = ("偏便宜" if px < lo else "偏贵" if px > hi else "大致合理")
                    over_note = ""
                    if px > mid * 3:
                        verdict = "极贵(按正常化盈利)"
                        over_note = ("·⚠现价是正常化盈利的 %.0f 倍——这类多是市场按【高成长/未来爆发】定价，"
                                     "中周期正常化这把尺会显得极贵；要不要换它、别只看这个数，等架构师中周期精调") % (px / norm)
                    rec["valuation"] = {
                        "source": f"候选估值·机械算(中周期正常化EPS×板块PE)·EDGAR {tag}",
                        "authoritative": True, "reliability": "候选级(机械·非精调)",
                        "normalized_eps": round(norm, 2), "pe_mid": pe,
                        "fair": {"cheap": round(lo, 1), "mid": round(mid, 1), "rich": round(hi, 1)},
                        "verdict": verdict, "gap_mid_pct": round(gap, 1),
                        "note": f"穿 {len(win)} 年正常化EPS≈{norm:.2f}×板块中枢PE {pe}倍；现价{px}对中枢{gap:+.0f}%" + over_note,
                        "history_years": len(eps)}
                else:
                    rec["valuation"] = {"source": "候选估值", "authoritative": True, "status": "待接",
                                        "reason": f"穿周期均值EPS为负({norm:.2f})→周期底部亏损、正常化不可靠·不编"}
            else:
                rec["valuation"] = {"source": "候选估值", "authoritative": True, "status": "待接",
                                    "reason": ("EDGAR 历史EPS<3年(上市太短)·不编" if px is not None
                                               else "取不到现价·不编")}
        else:
            # ③ 非美股 → EDGAR 取不到
            mkt = tk.split(".")[0]
            rec["valuation"] = {"source": "候选估值", "authoritative": True, "status": "待接",
                                "reason": f"{mkt}股不在 SEC EDGAR(需 EDINET/公司IR 或架构师估算)·本单未接·不编"}
        out[tk] = rec
    return {"error": "", "candidates": out, "arch_count": len(arch)}


def main() -> int:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="机会池候选估值+研究")
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    r = build(a.date)
    doc = {"_说明": "机会池候选的估值(中周期机械算·或架构师估算)+一句话研究。够拿来比'该不该换'。"
                   "缺真源、架构师也没给→标待接+原因，不编。",
           "date": a.date, "generated_at": datetime.now(JST).isoformat(timespec="seconds"),
           "error": r.get("error", ""), "candidates": r.get("candidates", {})}
    p = ROOT / "data" / "valuation" / f"candidate_valuation_{a.date}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if doc["error"]:
        print(f"[候选估值 失败] {doc['error']}", file=sys.stderr)
        return 3
    cs = doc["candidates"]
    ok = [k for k, v in cs.items() if (v.get("valuation") or {}).get("verdict")]
    wait = [k for k, v in cs.items() if (v.get("valuation") or {}).get("status") == "待接"]
    print(f"wrote {p.name} · 候选 {len(cs)} 只 · 有估值 {len(ok)} · 仍待接 {len(wait)}")
    for k, v in cs.items():
        val = v.get("valuation") or {}
        if val.get("verdict"):
            f = val["fair"]
            print(f"   ✔ {k:10s} {v['name'][:8]:10s} 现价{v.get('price')} · 合理{f['cheap']}~{f['rich']}(中枢{f['mid']}) → {val['verdict']}")
        else:
            print(f"   △ {k:10s} {v['name'][:8]:10s} 待接：{val.get('reason','')[:50]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
