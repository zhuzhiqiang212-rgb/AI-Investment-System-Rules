#!/usr/bin/env python3
"""分类型估值引擎 · 按类型【自动选模型】（尺=右栏_估值方法学.html）· 只读不下单

董事长定：估值模型由【标的类型自动定】，不手工每只指定。本引擎：
  1) 用 security_classifier 把每只持仓/候选按生意模式自动归类(成长股/控股/周期/保险/综合商社/券商/资产)
  2) 按尺的"类型→模型"表自动映射估值模型并算精算价：
     成长股→两段式EPS-DCF | 控股→NAV净资产 | 周期→中周期盈利(不用峰值) | 保险→PB/内含价值
     综合商社→NAV/PB(按主业) | 券商→正常化PE | 资产(BTC/ETH)→不做企业估值
  3) 每只记录：类型+为何这么归类+用了哪个模型+关键假设+可信度(A·精算/待接真源)

输入：data/valuation/val_inputs.json —— 理解岗只填【真财务输入】(不再填 method；模型由类型自动定)。
      data/valuation/security_types.json —— 行业事实底表(可迭代)，分类器据此归类。
输出：data/valuation/valuation_results_{date}.json —— render 的持仓卡「贵不贵/买卖价」与机会池直接吃。
缺真输入 → status='待接真源'，不硬编假值(红线)。每日现算不写死；乱码自核。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))

sys.path.insert(0, str(ROOT / "scripts"))
from dcf_valuation import two_stage_dcf              # 复用成长股两段式 DCF 原语
from security_classifier import classify, TYPE_MODEL, MODEL_INPUTS  # 类型自动分类+类型→模型(尺)


def _f(v):
    """转 float；None/空/非数 → None(不硬编)。"""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _pack(sym, name, cur, cls, intrinsic, target, assumptions, extra_note=""):
    """内在价值→合理区(±10%)统一封装·带类型/模型/可信度。"""
    return {
        "symbol": sym, "name": name, "currency": cur, "status": "OK",
        "type": cls["type"], "type_reason": cls["type_reason"], "type_source": cls["source"],
        "model": cls["model"], "model_disp": cls["model_disp"], "method_disp": cls["model_disp"],
        "intrinsic": round(intrinsic, 2),
        "reasonable_low": round(target * 0.90, 2),
        "reasonable_high": round(target * 1.10, 2),
        "target": round(target, 2),
        "confidence": "A·" + cls["model"], "credibility": "A·精算",
        "assumptions": assumptions,
        "note": extra_note,
    }


def _pending(sym, name, cls, missing):
    model = cls["model"]; disp = cls["model_disp"]
    reason = f"缺真输入：{('、'.join(missing))}（该用 {disp}·{MODEL_INPUTS.get(model, '')}）·不硬编"
    return {"symbol": sym, "name": name, "status": "待接真源",
            "type": cls["type"], "type_reason": cls["type_reason"], "type_source": cls["source"],
            "model": model, "model_disp": disp, "method_disp": disp,
            "credibility": "待接真源", "reason": reason}


def _asset(sym, name, cls):
    return {"symbol": sym, "name": name, "status": "资产口径",
            "type": cls["type"], "type_reason": cls["type_reason"], "type_source": cls["source"],
            "model": cls["model"], "model_disp": cls["model_disp"], "method_disp": cls["model_disp"],
            "credibility": "不适用", "reason": "无财报的资产·不做企业估值·只按仓位纪律(≤12%)+币价管"}


# ── 各模型（真输入→精算价）。缺输入返回待接·不硬编 ──

def m_growth_dcf(sym, name, cur, cls, it):
    need = {"eps0": _f(it.get("eps0")), "g_stage1": _f(it.get("g_stage1")),
            "years": it.get("years"), "terminal_g": _f(it.get("terminal_g")), "wacc": _f(it.get("wacc"))}
    missing = [k for k, v in need.items() if v is None]
    if missing:
        return _pending(sym, name, cls, missing)
    try:
        iv = two_stage_dcf(need["eps0"], need["g_stage1"], int(need["years"]), need["terminal_g"], need["wacc"])
    except ValueError as exc:
        return _pending(sym, name, cls, [f"假设不合法({exc})"])
    return _pack(sym, name, cur, cls, iv, iv, {**need, "note": it.get("note", "")})


def m_nav(sym, name, cur, cls, it):
    assets = it.get("assets") or []
    vals = [_f(a.get("value")) for a in assets] if isinstance(assets, list) else []
    net_debt = _f(it.get("net_debt")); shares = _f(it.get("shares"))
    missing = []
    if not vals or any(v is None for v in vals):
        missing.append("assets[各资产估值]")
    if net_debt is None:
        missing.append("net_debt(净负债)")
    if shares is None or shares == 0:
        missing.append("shares(总股本)")
    if missing:
        return _pending(sym, name, cls, missing)
    gross = sum(vals)
    nav_ps = (gross - net_debt) / shares
    if nav_ps <= 0:
        return _pending(sym, name, cls, ["资产减净负债后为负·核对输入"])
    disc = _f(it.get("holding_discount"))
    target = nav_ps * (1 - disc) if disc is not None else nav_ps
    return _pack(sym, name, cur, cls, nav_ps, target,
                 {"资产合计": round(gross, 2), "净负债": net_debt, "总股本": shares,
                  "每股NAV": round(nav_ps, 2), "控股折价": disc,
                  "资产明细": [{a.get("name"): _f(a.get("value"))} for a in assets], "note": it.get("note", "")},
                 extra_note=("合理中枢已按控股折价" + (f"{disc:.0%}" if disc is not None else "0%") + "折"))


def m_mid_cycle(sym, name, cur, cls, it):
    normal_eps = _f(it.get("normal_eps")); pe_mid = _f(it.get("pe_mid"))
    if normal_eps is not None and pe_mid is not None:
        iv = normal_eps * pe_mid
        return _pack(sym, name, cur, cls, iv, iv,
                     {"法": "正常年景EPS×中周期PE", "normal_eps": normal_eps, "pe_mid": pe_mid, "note": it.get("note", "")})
    ebitda = _f(it.get("ebitda_normal")); mult = _f(it.get("ev_ebitda"))
    net_debt = _f(it.get("net_debt")); shares = _f(it.get("shares"))
    if None not in (ebitda, mult, net_debt, shares) and shares != 0:
        ev = ebitda * mult; per_share = (ev - net_debt) / shares
        if per_share <= 0:
            return _pending(sym, name, cls, ["EV减净负债后为负·核对输入"])
        return _pack(sym, name, cur, cls, per_share, per_share,
                     {"法": "中周期EV/EBITDA", "ebitda_normal": ebitda, "ev_ebitda": mult,
                      "净负债": net_debt, "总股本": shares, "EV": round(ev, 2), "note": it.get("note", "")})
    return _pending(sym, name, cls, ["normal_eps+pe_mid 或 ebitda_normal+ev_ebitda+net_debt+shares(任一整套)"])


def m_pbv(sym, name, cur, cls, it):
    bvps = _f(it.get("bvps")); target_pb = _f(it.get("target_pb"))
    if bvps is not None and target_pb is not None:
        iv = bvps * target_pb
        return _pack(sym, name, cur, cls, iv, iv,
                     {"法": "每股净资产×目标PB", "bvps": bvps, "target_pb": target_pb, "note": it.get("note", "")})
    evps = _f(it.get("ev_per_share")); evm = _f(it.get("ev_multiple"))
    if evps is not None and evm is not None:
        iv = evps * evm
        return _pack(sym, name, cur, cls, iv, iv,
                     {"法": "内含价值/股×倍数", "ev_per_share": evps, "ev_multiple": evm, "note": it.get("note", "")})
    return _pending(sym, name, cls, ["bvps+target_pb 或 ev_per_share+ev_multiple(任一套)"])


def m_normalized_pe(sym, name, cur, cls, it):
    eps = _f(it.get("normalized_eps")); pe = _f(it.get("pe_normal"))
    if eps is not None and pe is not None:
        iv = eps * pe
        return _pack(sym, name, cur, cls, iv, iv,
                     {"法": "正常化EPS×正常化PE", "normalized_eps": eps, "pe_normal": pe, "note": it.get("note", "")})
    return _pending(sym, name, cls, ["normalized_eps+pe_normal"])


MODEL_FN = {"growth_dcf": m_growth_dcf, "nav": m_nav, "mid_cycle": m_mid_cycle,
            "pbv": m_pbv, "normalized_pe": m_normalized_pe}


def _apply_credibility(result, it):
    """新2(董事长2026-07-19):可信度标签必须与 note 自述一致·不许挂虚高A牌。
    val_inputs 有 credibility 字段→用它覆盖(如爱德万→中高·COIN→中);没有→保持默认。"""
    cr = (it or {}).get("credibility")
    if cr and isinstance(result, dict) and result.get("status") == "OK":
        result["credibility"] = str(cr)
        result["confidence"] = str(cr)
    return result


def value_one(sym, it):
    """按类型自动选模型给一只标的估值(持仓或候选皆可)。it=真财务输入(可空)。"""
    it = it or {}
    name = it.get("name", "")
    cur = it.get("currency", "$")
    # 架构师锁定价值区(董事长提案·如台积电P/E+PEG今日价值区)→ 直填精算·不走中周期(避免误判成长股)
    fl = it.get("fair_locked") or {}
    if fl.get("low") is not None and fl.get("high") is not None and fl.get("mid") is not None:
        clsf = classify(sym, name)
        r = _pack(sym, name, cur, clsf, float(fl["mid"]), float(fl["mid"]),
                  {"法": str(it.get("ruler_disp") or "P/E+PEG(架构师锁定·前瞻)"),
                   "forward_eps": it.get("forward_eps"), "forward_pe": it.get("forward_pe"),
                   "peg": it.get("peg"), "note": it.get("note", "")})
        r["reasonable_low"] = float(fl["low"]); r["reasonable_high"] = float(fl["high"])
        r["target"] = float(fl["mid"])
        r["model_disp"] = str(it.get("ruler_disp") or "P/E+PEG(架构师锁定)")
        r["method_disp"] = r["model_disp"]
        r["target_future"] = it.get("target_future")   # 未来1~2年目标价(三段式④)
        r["forward_eps"] = it.get("forward_eps"); r["forward_pe"] = it.get("forward_pe"); r["peg"] = it.get("peg")
        r["source"] = it.get("source", "")
        return _apply_credibility(r, it)
    cls = classify(sym, name)                     # 类型自动分类→模型(尺)
    if cls["model"] == "asset_none":
        return _asset(sym, name, cls)
    fn = MODEL_FN.get(cls["model"])
    if fn is None:                                # 理论不至·防御
        return _pending(sym, name, cls, [f"模型 {cls['model']} 未实现"])
    return _apply_credibility(fn(sym, name, cur, cls, it), it)


def compute(inputs: dict) -> dict:
    holdings = inputs.get("holdings", {})
    items = holdings.items() if isinstance(holdings, dict) else [(h.get("symbol"), h) for h in holdings]
    rows = [value_one(sym, it) for sym, it in items]
    return {"generated_at": datetime.now(JST).isoformat(),
            "engine": "分类型估值引擎 v2·按类型自动选模型",
            "ruler": "00_请先看这里/右栏_估值方法学.html",
            "type_model_map": {k: v["model_disp"] for k, v in TYPE_MODEL.items()},
            "results": rows}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="分类型估值引擎·按类型自动选模型·只读不下单")
    ap.add_argument("--date", default=None)
    args = ap.parse_args()
    date = args.date or datetime.now(JST).strftime("%Y%m%d")
    inp = ROOT / "data" / "valuation" / "val_inputs.json"
    if not inp.exists():
        print(f"[待接真源] 缺输入位 {inp}，不编造。")
        return 2
    out = compute(json.loads(inp.read_text(encoding="utf-8")))
    out_path = ROOT / "data" / "valuation" / f"valuation_results_{date}.json"
    text = json.dumps(out, ensure_ascii=False, indent=2)
    out_path.write_text(text, encoding="utf-8")
    if out_path.read_bytes().count(b"\xef\xbf\xbd") > 0:
        print("[WARN] 输出疑似乱码 EF BF BD>0")
    ok = sum(1 for r in out["results"] if r.get("status") == "OK")
    asset = sum(1 for r in out["results"] if r.get("status") == "资产口径")
    pend = len(out["results"]) - ok - asset
    print(f"wrote {out_path} · 精算 {ok} 只(可信度A)、资产口径 {asset} 只、待接 {pend} 只")
    for r in out["results"]:
        st = r.get("status")
        if st == "OK":
            print(f"  [A] {str(r['symbol']):11} 归类={r['type']:5}→{r['model_disp']:16} 中枢={r['currency']}{r['target']} 合理区 {r['currency']}{r['reasonable_low']}~{r['currency']}{r['reasonable_high']} ({r['type_source']})")
        elif st == "资产口径":
            print(f"  [资产] {str(r['symbol']):11} 归类={r['type']}·不做企业估值")
        else:
            print(f"  [待接] {str(r['symbol']):11} 归类={r['type']:5}→{r['model_disp']}: {r.get('reason', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
