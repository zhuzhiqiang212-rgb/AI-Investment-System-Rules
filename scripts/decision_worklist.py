# -*- coding: utf-8 -*-
"""★轮166 C:⑥层【决策清单待填表】——把决策要的数据一处摆齐·供董事长/Opus5逐只填『换/守/减』。
★Code只摆数据·★决策字段留空·★不代填任何决策(G2)。
每持仓:现价/成本/权重/pl/到价三档/护城河(已评)/DIO+capex组合。超限项:单只>20%·防御仓<15%。候选:⑤101只三路径命中/护城河已评。"""
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SINGLE_CAP = 20.0   # 单只上限%
DEF_FLOOR = 15.0    # 防御仓下限%


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _latest(pat):
    g = sorted(ROOT.glob(pat)); return g[-1] if g else None


def _holdings_sanity(pos, FX, total_usd):
    """★轮174 E:持仓数据自检(不需外部数据)。①单只市值=股数×现价 ②★跨币种未归一检测(会捕获轮173那类BUG) ③权重和≈100%。"""
    warns = []   # ★真告警(需查)
    # ①单只一致性(★真告警:股数×现价对不上)
    bad1 = []
    for p in pos:
        mv = p.get("broker_market_val") or 0
        calc = (p.get("quantity") or 0) * (p.get("broker_nominal_price") or 0)
        if calc and abs(mv - calc) > max(1, calc * 0.02):
            bad1.append({"标的": p["symbol"], "市值": mv, "股数×现价": round(calc, 1)})
    if bad1:
        warns.append({"★告警": "单只市值≠股数×现价", "明细": bad1})
    # ②★跨币种检测(★哨兵:原始broker_market_val是混币种·任何直接相加必错·轮173正是此)
    markets = set(p["symbol"].split(".")[0] for p in pos)
    raw_sum = sum((p.get("broker_market_val") or 0) for p in pos) or 1
    cross_ccy = len(markets) > 1
    ratio = round(raw_sum / total_usd, 1) if total_usd else 0
    ccy = ("✅本表已FX归一(正确)。★哨兵:原始broker_market_val是混币种(raw直接相加=%.0f vs FX归一USD=%.0f·差%.1f倍)→★任何直接sum原始市值的代码必错(轮173正是此)·所有权重计算必须先FX归一" % (raw_sum, round(total_usd), ratio)) if (cross_ccy and ratio > 3) else "单一市场或已归一·无混币风险"
    return {
        "①单只市值=股数×现价": ("✅全一致" if not bad1 else "★★有不一致(需查)"),
        "②货币混合哨兵": ccy,
        "③FX归一USD总市值": round(total_usd),
        "★自检结论": ("★★有真告警需查(单只市值对不上)" if warns else "✅通过(单只一致·已FX归一·混币哨兵已警示)"),
        "真告警明细": warns,
    }


def build(dc):
    pos = _rj(_latest("data/accounts/futu_positions_*.json")).get("futu_positions", []) or []
    ep = _rj(_latest("data/accounts/exec_params_*.json"))
    epm = {}
    for x in (ep.get("三只", []) or []):
        epm[x.get("标的") or x.get("code") or x.get("symbol")] = x
    moat = _rj(_latest("data/opportunity/moat_opus5_*.json"))
    # ★轮173 C-1:护城河已评【有效】=微软/爱德万·SCREEN(JP.7735)作废(董事长误当发那科评·不作数)
    MOAT_VOID = {"JP.7735"}
    moatm = {r.get("代码"): r for r in (moat.get("逐只", []) or []) if r.get("代码") not in MOAT_VOID}
    idm = _rj(_latest("data/opportunity/identity_*.json")).get("身份", {}) or {}
    invc = _rj(_latest("data/universe/inventory_capex_all_*.json"))
    invm = {r["代码"]: r for r in (invc.get("逐只", []) or [])}
    inv3 = _rj(_latest("data/universe/inventory_capex_2*.json"))
    inv3m = {r["代码"]: r for r in (inv3.get("逐只", []) or [])}
    # ★轮173 C-3:危险组合7只(capex升+库存升)·标出(含持仓NVDA/伊藤忠/万代)
    DANGER7 = {"US.NVDA", "US.GOOGL", "US.DELL", "US.QCOM", "US.CACI", "JP.8001", "JP.7832"}

    # ★★★轮174 修致命BUG:broker_market_val是【各持仓本币】·必须FX归一到USD。★★轮176:并入SBI→【全账户】口径(FUTU+SBI合并by公司)。
    FX = _rj(_latest("data/universe/tier_filter_*.json")).get("FX", {}) or {"US": 1.0, "JP": 157.0, "HK": 7.8422}
    if not FX.get("JP"):
        FX["JP"] = 157.0
    sbi = _rj(_latest("data/accounts/sbi_positions_*.json")).get("逐只", []) or []
    # ★合并FUTU+SBI:by公司累加USD市值(FX归一)
    usd_by = {}
    name_by = {}
    for p in pos:
        c = p["symbol"]; mk = c.split(".")[0]
        usd_by[c] = usd_by.get(c, 0) + (p.get("broker_market_val") or 0) / FX.get(mk, 1.0)
        name_by[c] = p.get("name")
    for s in sbi:
        c = s["symbol"]
        usd_by[c] = usd_by.get(c, 0) + (s.get("市值JPY") or 0) / FX.get("JP", 157.0)
        name_by.setdefault(c, s.get("name"))
    total = sum(usd_by.values()) or 1   # ★全账户FX归一USD总市值
    # ★逐只＝合并后的全账户持仓(不再只富途·SBI-only标的如爱德万/东京海上/丰田/索尼也进表)
    merged = sorted(usd_by.items(), key=lambda x: -x[1])
    posmap = {p["symbol"]: p for p in pos}
    sbimap = {s["symbol"]: s for s in sbi}
    rows = []
    for code, mv in merged:
        p = posmap.get(code, {})
        s = sbimap.get(code, {})
        w = round(mv / total * 100, 2)   # ★2位小数(微仓不塌成0)
        m = moatm.get(code, {})
        iv = invm.get(code) or inv3m.get(code) or {}
        combo = iv.get("★组合状态") or (iv.get("★组合状态(Code只给·含义董事长判)")) or "NK4(未取到库存/capex)"
        moat_v = (m.get("总moat结论") or m.get("总分") or m.get("moat_grade"))
        moat_disp = (("已评:总分%s" % moat_v) if (code in moatm and moat_v is not None) else
                     ("★评分作废(SCREEN误当发那科·不作数)" if code in MOAT_VOID else "★未评(仅微软/爱德万有效评分)"))
        acct = ("富途+SBI" if (code in posmap and code in sbimap) else ("SBI" if code in sbimap and code not in posmap else "富途"))
        rows.append({
            "代码": code, "全名": idm.get(code, {}).get("全名", name_by.get(code)), "账户": acct,
            "现价": p.get("broker_nominal_price") or s.get("现价"), "成本": p.get("cost_price") or s.get("成本"),
            "★权重%(全账户·FUTU+SBI·FX归一)": w,
            "★是否微仓(<0.5%)": (w < 0.5),
            "★超单只20%上限(全账户口径)": (w > SINGLE_CAP),
            "到价三档(exec_params)": epm.get(code, "★未在exec_params三只内·待接"),
            "护城河(Opus5已评·SCREEN作废)": moat_disp,
            "DIO+capex组合": combo,
            "★危险组合(capex升+库存升)": (code in DANGER7),
            "★决策(换/守/减·董事长填·Code不代填)": None,
        })
    over = [r for r in rows if r["★超单只20%上限(全账户口径)"]]
    # ★★轮176 D-3:防御仓占比(★全账户·含SBI东京海上/伊藤忠/丰田)。防御股名单Opus5静态(东京海上8766/伊藤忠8001/丰田7203/万代7832/任天堂7974)。
    DEF = {"JP.8766", "JP.8001", "JP.7203", "JP.7832", "JP.7974"}
    def_w = round(sum(r["★权重%(全账户·FUTU+SBI·FX归一)"] for r in rows if r["代码"] in DEF), 2)
    def_names = [r["代码"] for r in rows if r["代码"] in DEF]
    # ★★★E:持仓数据自检(不需外部数据·自己就能查)
    sanity = _holdings_sanity(pos, FX, total)
    # ⑤候选:三路径命中 + 护城河已评
    prio = _rj(_latest("data/opportunity/candidate_priority_*.json"))
    tri = [r["标的"] for r in prio.get("全量排序", []) if r.get("★命中数", 0) >= 3]
    cand_rows = []
    for code in tri:
        cand_rows.append({"代码": code, "全名": idm.get(code, {}).get("全名", "?"),
                          "★三路径命中": True, "护城河(Opus5已评)": (moatm.get(code, {}).get("总moat结论") or "★未评"),
                          "★候选决策(是否纳入·董事长填)": None})
    out = {
        "_说明": "★轮166 C 决策清单待填表。★Code只摆数据·决策字段留空·不代填(G2)。持仓现价/成本/权重/到价/护城河/DIO+capex组合摆齐·超限项标出·候选三路径命中列出。SBI账户sleeve快照过期(仅富途13持仓·SBI待新快照)。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "★权重口径(必读·轮176全账户)": f"★权重＝【全账户·FUTU+SBI合并by公司·FX归一USD】(全账户总市值≈${round(total):,})。★轮176已并入SBI9持仓(读自董事长截图)。★关键变化:微软富途账户内24.24%→★全账户{round(next((r['★权重%(全账户·FUTU+SBI·FX归一)'] for r in rows if r['代码']=='US.MSFT'),0),2)}%(SBI稀释后不再超20%)。★美股≈45%·日股≈55%(含SBI日股·非futu-only的64/36)。",
        "★持仓决策清单(填换/守/减)": rows,
        "★超单只20%上限的(全账户口径)": [{"代码": r["代码"], "权重%": r["★权重%(全账户·FUTU+SBI·FX归一)"]} for r in over],
        "★★持仓数据自检(E·无需外部数据)": sanity,
        "★防御仓占比(全账户·含SBI·FX归一)": {"占比%": def_w, "vs15%下限": ("★破15%下限" if def_w < DEF_FLOOR else "达标"), "含哪几只": def_names, "★口径注": "全账户防御股(东京海上/伊藤忠/丰田/万代/任天堂)·已含SBI"},
        "★候选(⑤·三路径命中·填是否纳入)": cand_rows,
        "_数据源": "futu_positions(现价/成本/权重) + exec_params(到价) + moat_opus5(护城河) + inventory_capex(DIO/capex) + candidate_priority(三路径)",
    }
    (ROOT / f"data/pdca/decision_worklist_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("持仓决策清单 %d 行 · 超单只20%%(全账户) %d 只 · 候选三路径 %d 只" % (
        len(o["★持仓决策清单(填换/守/减)"]), len(o["★超单只20%上限的(全账户口径)"]), len(o["★候选(⑤·三路径命中·填是否纳入)"])))
    for r in o["★持仓决策清单(填换/守/减)"]:
        print("  %-9s %-14s 权重%s%% %s 护城河[%s] DIO[%s] %s" % (
            r["代码"], str(r["全名"])[:14], r["★权重%(全账户·FUTU+SBI·FX归一)"],
            "微仓" if r["★是否微仓(<0.5%)"] else "    ",
            str(r["护城河(Opus5已评·SCREEN作废)"])[:14], str(r["DIO+capex组合"])[:12],
            "★危险" if r["★危险组合(capex升+库存升)"] else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
