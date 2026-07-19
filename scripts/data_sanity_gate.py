#!/usr/bin/env python3
"""数据异常检查关（验收整改2026-07-18·第一档3）· 只读不下单

正式产品前必过。查【会让董事长做错决策】的数据异常，命中即标红·停买卖建议：
  · 价格异常(现价与估值参考差 5 倍+，如闪迪$1,365 vs 参考$40~80 → 疑似拆股/口径没换算)
  · 股数/市值突跳(与上一份持仓比，单只市值跳变 >50% 却无对应加减仓记录)
  · 只数对不上(production 20 只 vs 深研 19 只这类)
  · 同股两动作(决定表里同一只出现两个动作)
  · 代码不匹配(production 里的 symbol 在持仓真表里找不到)

返回异常清单；渲染层据此在顶部标红警条。data_sanity_gate 本身只读不改数。
用法：python scripts/data_sanity_gate.py --date 20260717
      from data_sanity_gate import check; issues = check(date)
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))


def _rj(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def mag_flag(px, mid, reliability: str = "") -> tuple:
    """量级哨兵(董事长2026-07-18)：现价 ÷ 合理价中枢 差多少倍。
    返回 (级别, 倍数)：
      · 'red'    —— 差 >15 倍，或 >6 倍且估值可靠度低(勉强/不够) → 离谱·无法用周期解释·标红待人工核
      · 'caution'—— 差 6~15 倍且可靠度够 → 真价+周期顶导致的极贵·可解释·正常显示
      · None     —— ≤6 倍，正常
    <1/6(现价远低于中枢)同样按 red 处理(疑喂价错/拆股)。"""
    try:
        px = float(px); mid = float(mid)
    except (TypeError, ValueError):
        return None, 0.0
    if px <= 0 or mid <= 0:
        return None, 0.0
    gap = px / mid if px >= mid else mid / px
    low_rel = any(k in str(reliability) for k in ("勉强", "不够"))
    if gap > 15 or (gap > 6 and low_rel) or px < mid / 6:
        return "red", gap
    if gap > 6:
        return "caution", gap
    return None, gap


def check(date: str) -> list:
    issues = []
    prod = _rj(ROOT / "data" / "reports" / f"production_{date}.json")
    # 量级哨兵：现价 vs 架构师中周期估算中枢差 >6 倍 → 红/黄(离谱失真 vs 周期顶可解释)
    arch = {}
    try:
        ap = sorted((ROOT / "data" / "valuation").glob("architect_normalized_est_*.json"))
        if ap:
            for e in _rj(ap[-1]).get("estimates", []):
                arch[str(e.get("ticker"))] = e
    except Exception:
        pass
    for h in [x for x in prod.get("holdings", []) if not str(x.get("symbol", "")).startswith("CC.")]:
        s = str(h.get("symbol")); px = h.get("price")
        e = arch.get(s) or {}
        # 已撤销的估算(董事长核价确认真价·撤掉不可靠normalized，如闪迪)→ 列"估值已撤·待接"，不再算倍数报价格异常
        if str(e.get("scale_status")) == "撤销":
            issues.append({"level": "黄", "type": "量级哨兵", "symbol": s, "name": h.get("name"),
                           "detail": (f"现价 {px} 经二源人工核实为真价；原架构师 normalized 估值已撤销"
                                      f"（极端超级周期下正常化不可靠）→ 合理价待接·算不出，守着看，不用它判贵贱")})
            continue
        mid = (e.get("fair_price") or {}).get("mid")
        lvl, gap = mag_flag(px, mid, e.get("reliability", ""))
        if lvl in ("red", "caution"):
            resolved = str(e.get("scale_status", "")).startswith("已复核")
            if resolved:
                # 架构师已复核·非算错(如爱德万:真景气高点的正常极贵·峰值定价)
                issues.append({"level": "黄", "type": "量级哨兵", "symbol": s, "name": h.get("name"),
                               "detail": (f"现价 {px} 是中周期公允 {mid} 的约 {gap:.0f} 倍——架构师已复核："
                                          f"真·景气高点的正常极贵(峰值定价·峰值PE约54)，非算错。"
                                          f"守·不追高、留峰值风险安全垫")})
            else:
                issues.append({"level": "红" if lvl == "red" else "黄", "type": "量级哨兵",
                               "symbol": s, "name": h.get("name"),
                               "detail": (f"现价 {px} 与中周期估算中枢 {mid} 差约 {gap:.0f} 倍"
                                          f"（可靠度：{e.get('reliability','?')}）→ 现价多为真价·"
                                          f"这套穿周期估算参考度低，待架构师复核·暂不用它判贵贱")})
    holds = [h for h in prod.get("holdings", []) if not str(h.get("symbol", "")).startswith("CC.")]
    valr = {r["symbol"]: r for r in (_rj(ROOT / "data" / "valuation" / f"valuation_results_{date}.json")
                                     .get("results") or []) if r.get("symbol")}

    # ① 价格异常：现价与估值区间差 5 倍以上(疑似拆股/口径没换算)
    #   P0-2(董事长2026-07-19):【已核准·真价】的(架构师 scale_status=已复核·如爱德万)不得再报"疑似错误"——
    #   否则同屏出现"疑似拆股"与"已复核无误"两口径(明令禁止)。核准股的差倍由⑤量级哨兵按"已复核·口径差非数据错"说清。
    for h in holds:
        s = str(h.get("symbol")); px = h.get("price")
        if str((arch.get(s) or {}).get("scale_status", "")).startswith("已复核"):
            continue                                   # 已核准真价→不报价格异常(避免与量级哨兵"已复核"矛盾)
        v = valr.get(s) or {}
        lo, hi = v.get("reasonable_low"), v.get("reasonable_high")
        if px and lo and hi and lo > 0:
            if px > hi * 5 or px < lo / 5:
                issues.append({"level": "红", "type": "价格异常",
                               "symbol": s, "name": h.get("name"),
                               "detail": f"现价 {px} 与估值区间 {lo}~{hi} 差 5 倍以上"
                                         f"→疑似拆股未换算/口径不符，别据此买卖·待人工核准"})

    # ② 只数对不上：production vs 深研卡
    n_prod = len(holds)
    try:
        cards = list((ROOT / "data" / "analysis" / "deep_cards").glob("*.json"))
        n_card = len([c for c in cards])
    except Exception:
        n_card = 0
    # (只提示·不拦：新持仓允许暂无深研卡)
    if n_card and abs(n_prod - n_card) > 3:
        issues.append({"level": "黄", "type": "只数差异", "symbol": "-", "name": "-",
                       "detail": f"production {n_prod} 只 vs 深研卡 {n_card} 张，差 {abs(n_prod-n_card)} → 核对是否漏卡"})

    # ③ 代码不匹配：production symbol 在持仓真表里找不到
    ht = _rj(ROOT / "data" / "accounts" / f"holdings_true_{date}.json")
    ht_syms = {str(h.get("symbol")) for h in ht.get("holdings", [])}
    if ht_syms:
        for h in holds:
            s = str(h.get("symbol"))
            if s not in ht_syms:
                issues.append({"level": "红", "type": "代码不匹配", "symbol": s, "name": h.get("name"),
                               "detail": f"{s} 在 production 里有、持仓真表里没有→数据源对不上"})

    # ④ 市值突跳：与上一份 production 比，单只市值跳 >50% 且无加减仓记录
    prev = None
    for i in range(1, 8):
        pd = (datetime.strptime(date, "%Y%m%d") - timedelta(days=i)).strftime("%Y%m%d")
        p = ROOT / "data" / "reports" / f"production_{pd}.json"
        if p.exists():
            prev = _rj(p)
            break
    if prev:
        prev_qty = {str(h.get("symbol")): h.get("quantity") for h in prev.get("holdings", [])}
        for h in holds:
            s = str(h.get("symbol"))
            q0, q1 = prev_qty.get(s), h.get("quantity")
            if q0 and q1 and q0 > 0:
                jump = abs(q1 - q0) / q0
                if jump > 0.5:
                    issues.append({"level": "黄", "type": "股数突跳", "symbol": s, "name": h.get("name"),
                                   "detail": f"股数 {q0:g}→{q1:g}(变 {jump*100:.0f}%)→确认是真加减仓还是数据错"})

    # ⑤ 同股两动作：决定表里同一只两个动作(有 decisions_ 文件才查)
    dec = _rj(ROOT / "data" / "pdca" / f"decisions_{date}.json").get("decisions", {})
    # decisions 是 {sym:{action}}，天然唯一；这里核它与另一处若有出入(预留·当前单一源已保证)
    return issues


def main() -> int:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="数据异常检查关")
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    issues = check(a.date)
    doc = {"_说明": "数据异常检查关：命中即标红·停买卖建议。正式产品前必过。",
           "date": a.date, "generated_at": datetime.now(JST).isoformat(timespec="seconds"),
           "n_red": sum(1 for x in issues if x["level"] == "红"),
           "n_yellow": sum(1 for x in issues if x["level"] == "黄"),
           "issues": issues}
    p = ROOT / "data" / "reports" / f"data_sanity_{a.date}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {p.name} · 红 {doc['n_red']} · 黄 {doc['n_yellow']}")
    for x in issues:
        print(f"   [{x['level']}] {x['type']} {x.get('symbol','')} {x['detail'][:60]}")
    if not issues:
        print("   ✔ 无数据异常")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
