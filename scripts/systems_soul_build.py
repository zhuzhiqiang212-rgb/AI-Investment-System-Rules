#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""系统之魂构建器（总则第十四条·⑦记分卡三件魂之数据层）。

不另起炉灶：pillar_score.json 完全源自 data/pdca/scorecards.json（pdca_scorecard 产物·
cumulative_score/current_certainty/history）；shadow_nav.json 源自 production_{date}
（持仓市值+动作），逐日追加。缺历史→标"待接·从今日起累积"，不编。

产出：
  data/pdca/pillar_score.json —— 支柱确定性累积表（各环 当前档+累计分+近N日走势）
  data/pdca/shadow_nav.json   —— 影子组合反事实净值（系统建议执行 vs 实际不动 + 差值，逐日追加）
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CERT_LADDER = ["证伪", "弱", "中", "高"]   # 从"中"往"高"攒


def rj(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def wj(p: Path, data: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    p.write_text(text, encoding="utf-8")
    if "�" in p.read_text(encoding="utf-8"):
        raise RuntimeError(f"U+FFFD detected: {p}")


# ── 魂①：支柱确定性累积表（源自 scorecards.json·不另起炉灶） ──
def build_pillar_score(date: str) -> dict:
    sc = rj(ROOT / "data" / "pdca" / "scorecards.json")
    cards = sc.get("cards", {}) or {}
    history = sc.get("history", []) or []
    hist_sorted = sorted(history, key=lambda r: str(r.get("date", "")))
    order = ["worldview", "fed_gate", "strategy", "capital_flow", "sector_rotation"]
    name_by = {rid: (cards.get(rid, {}) or {}).get("ring_name", rid) for rid in order}
    pillars = []
    for rid in order:
        card = cards.get(rid, {}) or {}
        # 近N日走势：从 history 逐日取该环 daily score + 滚动累积
        trend = []
        cum = 0
        for rec in hist_sorted:
            s = int((rec.get("scores", {}) or {}).get(rid, 0) or 0)
            cum += s
            trend.append({"date": rec.get("date"), "score": s, "cum": cum})
        recent = trend[-7:]
        # 走势箭头（近3日累积方向）
        arrow = "→"
        if len(trend) >= 2:
            d = trend[-1]["cum"] - trend[max(0, len(trend) - 4)]["cum"]
            arrow = "↑" if d > 0 else ("↓" if d < 0 else "→")
        pillars.append({
            "ring_id": rid,
            "ring_name": name_by.get(rid, rid),
            "current_certainty": card.get("current_certainty", "待接"),
            "cumulative_score": card.get("cumulative_score", (trend[-1]["cum"] if trend else 0)),
            "trend": recent,
            "trend_arrow": arrow,
            "days_tracked": len(trend),
        })
    return {
        "as_of": date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "data/pdca/scorecards.json（pdca_scorecard 产物·不另起炉灶）",
        "certainty_ladder": CERT_LADDER,
        "rule_source": "右栏①世界观尺·支持/证伪判定表（+1/0/-1 每环每日）",
        "pillars": pillars,
        "note": "确定性从'中'往'高'攒：判对+1、无变0、证伪-1，滚动累积。缺更长历史的走势→随日累积。",
    }


# ── 魂③：影子组合反事实记分（system=按当日守/减/加执行 vs actual=实际不动） ──
_ACTION_MULT = {"守": 1.0, "等": 1.0, "加": 1.30, "减": 0.60, "初判": 1.0}


def _action_mult(action: str) -> float:
    a = str(action or "")
    for k, v in _ACTION_MULT.items():
        if a.startswith(k) or k in a[:2]:
            return v
    return 1.0


def _usdjpy() -> float:
    try:
        import full_product_render as fpr
        r, _ = fpr.resolve_usdjpy()
        return float(r)
    except Exception:
        return 162.5


def _mv_usd(h: dict, usdjpy: float):
    sym = str(h.get("symbol") or "")
    mv = h.get("market_value")
    if mv is None:
        return None
    try:
        mv = float(mv)
    except (TypeError, ValueError):
        return None
    if sym.startswith("JP."):
        return mv / usdjpy if usdjpy else None
    return mv


def build_shadow_nav(date: str) -> dict:
    path = ROOT / "data" / "pdca" / "shadow_nav.json"
    prod = rj(ROOT / "data" / "reports" / f"production_{date}.json")
    holds = [h for h in prod.get("holdings", []) if not str(h.get("symbol", "")).startswith("CC.")]
    usdjpy = _usdjpy()
    # 当日快照：每只 现价 + 实际权重(市值折美元) + 系统权重(动作乘子后归一)
    mv = {}
    price = {}
    action = {}
    for h in holds:
        sym = str(h.get("symbol"))
        m = _mv_usd(h, usdjpy)
        p = h.get("price")
        if m is None or p is None:
            continue
        mv[sym] = m
        price[sym] = float(p)
        action[sym] = h.get("action", "")
    tot = sum(mv.values())
    if tot <= 0:
        actual_w, system_w = {}, {}
    else:
        actual_w = {s: mv[s] / tot for s in mv}
        sysmv = {s: mv[s] * _action_mult(action[s]) for s in mv}
        stot = sum(sysmv.values()) or 1.0
        system_w = {s: sysmv[s] / stot for s in sysmv}

    prev = rj(path) if path.exists() else None
    snap = {"date": date, "price": price, "actual_w": actual_w, "system_w": system_w,
            "action": action, "usdjpy": usdjpy}

    if not prev or not prev.get("series"):
        # 第一天：基准=0，只存快照供次日算收益
        series = [{"date": date, "system_nav": 0.0, "actual_nav": 0.0, "diff": 0.0,
                   "system_ret": None, "actual_ret": None,
                   "note": "基准日·从今日起累积（第一天基准=0·缺历史不编）"}]
        return {"as_of": date, "generated_at": datetime.now(timezone.utc).isoformat(),
                "baseline_date": date,
                "source": "production_{date}.json（持仓市值+动作）·逐日追加",
                "method": "system=按当日守/减/加(乘子 守/等1.0·加1.30·减0.60)调权后净值；actual=实际持仓不动净值；diff=system−actual=系统建议真含金量",
                "series": series, "last_snapshot": snap,
                "note": "缺历史→待接·从今日起累积；次日起用上一快照现价算日收益、复利成净值。"}

    # 基准日同日重跑：保持基准语义(0/0/0)、只刷快照(不把同日当"次日"算收益)
    if date == prev.get("baseline_date"):
        prev["series"] = [r for r in prev["series"] if r.get("date") != date]
        prev["series"].append({"date": date, "system_nav": 0.0, "actual_nav": 0.0, "diff": 0.0,
                               "system_ret": None, "actual_ret": None,
                               "note": "基准日·从今日起累积（第一天基准=0·缺历史不编）"})
        prev["as_of"] = date
        prev["generated_at"] = datetime.now(timezone.utc).isoformat()
        prev["last_snapshot"] = snap
        return prev
    # 次日+：用上一快照现价算各只日收益，按各自权重加权成组合日收益
    psnap = prev.get("last_snapshot", {})
    pprice = psnap.get("price", {})
    pact_w = psnap.get("actual_w", {})
    psys_w = psnap.get("system_w", {})

    def port_ret(weights):
        acc = 0.0
        wsum = 0.0
        for s, w in weights.items():
            if s in price and s in pprice and pprice[s]:
                acc += w * (price[s] / pprice[s] - 1.0)
                wsum += w
        return acc if wsum > 0 else 0.0

    aret = port_ret(pact_w)     # 昨日实际权重 × 今日/昨日收益
    sret = port_ret(psys_w)     # 昨日系统权重 × 今日/昨日收益
    last = prev["series"][-1]
    a_nav = (1 + last["actual_nav"] / 100.0) * (1 + aret) * 100.0 - 100.0
    s_nav = (1 + last["system_nav"] / 100.0) * (1 + sret) * 100.0 - 100.0
    prev["series"] = [r for r in prev["series"] if r.get("date") != date]
    prev["series"].append({
        "date": date, "system_nav": round(s_nav, 3), "actual_nav": round(a_nav, 3),
        "diff": round(s_nav - a_nav, 3),
        "system_ret": round(sret * 100, 3), "actual_ret": round(aret * 100, 3),
        "note": "净值=基准100起、以昨权重×今收益复利（单位:%相对基准）"})
    prev["as_of"] = date
    prev["generated_at"] = datetime.now(timezone.utc).isoformat()
    prev["last_snapshot"] = snap
    return prev


# ── 拍板收件箱：阈值触发→结构化待拍板事项（依据链可回溯·拍板记录留存→次日PDCA验证） ──
def build_pending_decisions(date: str) -> dict:
    path = ROOT / "data" / "pdca" / "pending_decisions.json"
    prev = rj(path) if path.exists() else {"items": []}
    old = {i.get("id"): i for i in (prev.get("items") or [])}
    import full_product_render as fpr
    prod = rj(ROOT / "data" / "reports" / f"production_{date}.json")
    cost = rj(ROOT / "data" / "accounts" / "unified_holdings_latest.json")
    conc = fpr.portfolio_concentration(prod.get("holdings", []),
                                       (cost.get("summary", {}) or {}).get("known_cash_usd"), {})
    cats = conc.get("categories", {}) or {}
    items = []
    for cat, v in cats.items():
        pct, lim = v.get("pct"), v.get("limit")
        if v.get("over"):
            pid = f"PD-{cat}-超上限"
            items.append({
                "id": pid, "date": date, "status": "待拍板",
                "proposal": f"{cat}集中度 {pct:.1f}% 超 {lim}% 上限 → 是否减仓降敞口？",
                "evidence_chain": [f"第三部分·集中度现算：{cat} {pct:.1f}% vs 上限 {lim}%（当日production市值折美元）",
                                   "第三部分附·风险因子穿透：该类成分股与合计敞口",
                                   "第四部分附·6b替换引擎：同额置换后集中度换前→换后现算",
                                   "个股卡⑩组合视角：簇内质量相对弱者优先减"],
                "options": ["A. 减至限内", "B. 维持不动（只换不加·不砍核心）", "C. 部分减（减半）"],
                "default_if_expired": "无拍板→默认 B 维持（只换不加·不砍核心），次日重新提请",
                "decision": old.get(pid, {}).get("decision", "待董事长填"),
                "decided_at": old.get(pid, {}).get("decided_at"),
            })
        if v.get("short"):
            pid = f"PD-{cat}-低于下限"
            items.append({
                "id": pid, "date": date, "status": "待拍板",
                "proposal": f"{cat}集中度 {pct:.1f}% 低于 {lim}% 下限 → 是否加仓补到下限？",
                "evidence_chain": [f"第三部分·集中度现算：{cat} {pct:.1f}% vs 下限 {lim}%",
                                   "个股卡⑤估值：该类中是否有对中枢有折让者",
                                   "个股卡⑩组合视角：该类分散AI风险的角色"],
                "options": ["A. 加该类中估值有折让者补到下限", "B. 维持（等更好点位）", "C. 分批加"],
                "default_if_expired": "无拍板→默认 B 维持（等更好点位），次日重新提请",
                "decision": old.get(pid, {}).get("decision", "待董事长填"),
                "decided_at": old.get(pid, {}).get("decided_at"),
            })
    return {"as_of": date, "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "阈值由 第三部分集中度现算 触发·依据链可回溯到层；拍板记录(decision)由董事长填→次日PDCA验证",
            "pending_count": sum(1 for i in items if i.get("decision") in (None, "", "待董事长填")),
            "items": items,
            "note": "到期默认处理=无拍板则按default_if_expired执行并次日重新提请；已拍板项(decision非待填)次日进PDCA验证。"}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="系统之魂构建器（pillar_score + shadow_nav + pending_decisions）")
    ap.add_argument("--date", required=True)
    args = ap.parse_args()
    date = args.date
    if str(ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))
    pillar = build_pillar_score(date)
    wj(ROOT / "data" / "pdca" / "pillar_score.json", pillar)
    shadow = build_shadow_nav(date)
    wj(ROOT / "data" / "pdca" / "shadow_nav.json", shadow)
    pend = build_pending_decisions(date)
    wj(ROOT / "data" / "pdca" / "pending_decisions.json", pend)
    print(json.dumps({
        "pillar_pillars": len(pillar["pillars"]),
        "pillar_days": pillar["pillars"][0]["days_tracked"] if pillar["pillars"] else 0,
        "shadow_days": len(shadow["series"]),
        "pending_count": pend["pending_count"],
        "pending_ids": [i["id"] for i in pend["items"]],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
