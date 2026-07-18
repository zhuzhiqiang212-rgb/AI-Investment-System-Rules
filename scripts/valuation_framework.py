#!/usr/bin/env python3
"""估值五层框架·按行业换尺（老雷法·董事长2026-07-18 拍板改尺）

替掉"一把尺(穿周期正常化)套所有"的错方法。原则：
  1 估值是最后一层：前四层(宏观/行业/公司/财务)先筛"好生意"；估值只回答"贵不贵"。
  2 按行业换尺；有盈利有增速的【一律先算 PEG=市盈率÷净利增速%】(PEG<1 便宜·0.8~1.2 合理·>1.5 偏贵)。
  3 用相对倍数(现价倍数 vs 行业合理区间)判贵贱，不追一个 DCF 死数。
  4 缺关键输入→标"该尺待接·缺X·不编"，绝不改套别的尺凑数。

每只：行业标签 → 选对应模型 → 取输入(SEC EDGAR / 公司IR / 架构师vetted值) → 关键倍数 + 现价vs合理区间 → 便宜/合理/贵 + 可靠度。
低置信也【必显数值】；真缺输入才"待接·缺X·不编"。

本模块只读不产出文件；deep_render/candidate_valuation import 它。
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ── 行业分类：每只归一类(董事长表) ──────────────────────────────
INDUSTRY = {
    # 芯片·成熟盈利
    "US.AVGO": "芯片·成熟盈利", "US.TSM": "芯片·成熟盈利",
    # 芯片·高增长
    "US.NVDA": "芯片·高增长", "US.AMD": "芯片·高增长", "US.MRVL": "芯片·高增长",
    # 半导体·设备/存储·强周期
    "JP.6857": "半导体·强周期", "US.SNDK": "半导体·强周期", "US.MU": "半导体·强周期",
    "JP.8035": "半导体·强周期", "US.ASML": "半导体·强周期", "US.AMAT": "半导体·强周期",
    "US.LRCX": "半导体·强周期", "US.KLAC": "半导体·强周期", "JP.285A": "半导体·强周期",
    "US.UMC": "半导体·强周期", "US.GFS": "半导体·强周期", "HK.00981": "半导体·强周期",
    # 电力/能源
    "US.VST": "电力/能源", "US.CEG": "电力/能源", "US.GEV": "电力/能源", "US.CCJ": "电力/能源",
    # 消费/IP
    "JP.7974": "消费/IP", "JP.7832": "消费/IP", "JP.6758": "消费/IP",
    # 医疗/药
    "JP.4568": "医疗/药",
    # 商社 / 控股
    "JP.8001": "商社", "JP.9984": "控股/科技投资",
    # 金融/保险
    "JP.8766": "金融/保险",
    # 汽车/制造
    "JP.7203": "汽车/制造",
    # 软件/SaaS
    "US.VEEV": "软件/SaaS", "US.NOW": "软件/SaaS", "US.PLTR": "软件/SaaS",
    "US.MSFT": "软件/SaaS", "US.META": "软件/SaaS",
    # 加密/金融
    "US.MSTR": "加密/金融", "US.COIN": "加密/金融", "US.CRCL": "加密/金融", "US.IBKR": "加密/金融",
    # 未上市·无财报
    "US.SPCX": "未上市·无财报",
}

# ── 每行业用哪把尺(ruler)+合理区间说明 ──────────────────────────
MODEL = {
    "芯片·成熟盈利": {"ruler": "P/E + PEG + FCF收益率", "peg": True,
                 "range": "龙头合理 P/E 约 20~30；PEG 0.8~1.2 合理"},
    "芯片·高增长": {"ruler": "PEG + EV/Sales（增速快则高 P/E 可合理）", "peg": True,
                "range": "PEG<1 便宜；EV/Sales 看增速匹配"},
    "半导体·强周期": {"ruler": "中周期正常化 EPS × 中周期 PE（不用峰值）", "peg": False,
                 "range": "现价按峰值定→标『贵·别把峰值当常态』"},
    "电力/能源": {"ruler": "EV/EBITDA + FCF收益率(>5~6%=现金牛) + NAV", "peg": False,
              "range": "一体化 5~7×；电力 AI 运营商 8~12×"},
    "消费/IP": {"ruler": "P/E + PEG + 股息率（净现金多先扣净现金）", "peg": True,
             "range": "P/E 看增速；PEG 0.8~1.2 合理"},
    "医疗/药": {"ruler": "P/E + PEG（利润率是命门；创新药管线用 rNPV）", "peg": True,
            "range": "PEG 0.8~1.2 合理"},
    "商社": {"ruler": "NAV/PB(拆分资产 SOTP) + 正常化 P/E 交叉验证", "peg": False,
           "range": "P/B 对净资产；充分定价≈P/B 接近 1"},
    "控股/科技投资": {"ruler": "NAV(持仓净值 SOTP·扣控股折价) + P/B 交叉验证", "peg": False,
                "range": "看持仓净值折价率；软银按 Vision Fund+ARM 等分项加总"},
    "金融/保险": {"ruler": "P/E + PEG + P/B + 股息率", "peg": True,
              "range": "保险看 P/B 与 ROE；P/E 约 10~15"},
    "汽车/制造": {"ruler": "P/E + PEG + 股息率", "peg": True,
              "range": "周期制造 P/E 约 8~12；PEG 0.8~1.2 合理"},
    "软件/SaaS": {"ruler": "EV/Sales + Rule of 40(增速%+FCF利润率%≥40) + forward P/E", "peg": False,
               "range": "Rule of 40 达标→高 EV/Sales 可合理"},
    "加密/金融": {"ruler": "MSTR=mNAV；COIN/CRCL=穿牛熊/中性利率正常化·低置信；IBKR=P/E+PEG", "peg": False,
              "range": "加密低置信·框架参考"},
    "未上市·无财报": {"ruler": "无公开财报→无估值基础", "peg": False, "range": "守着看"},
}

# 龙头合理 P/E 上沿（成熟盈利·消费·医疗·IBKR）——判"P/E 绝对值高不高"的锚，仅辅助 PEG
PE_ANCHOR = {"芯片·成熟盈利": (20, 30), "消费/IP": (15, 25), "医疗/药": (14, 22), "加密/金融": (15, 25)}


def industry_of(sym: str) -> str:
    return INDUSTRY.get(sym, "未分类")


def ruler_of(sym: str) -> str:
    return MODEL.get(industry_of(sym), {}).get("ruler", "待归类")


def _rj(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def peg_verdict(peg: float) -> str:
    if peg < 0.8:
        return "便宜"
    if peg <= 1.2:
        return "合理"
    if peg <= 1.5:
        return "偏贵"
    return "贵"


def compute_peg(price, eps_ttm, growth_pct):
    """PEG = (现价/每股盈利) / 净利增速% 。返回 (pe, peg) 或 None(缺输入/不适用)。"""
    try:
        price = float(price); eps = float(eps_ttm); g = float(growth_pct)
    except (TypeError, ValueError):
        return None
    if eps <= 0 or g <= 0:
        return None
    pe = price / eps
    return round(pe, 1), round(pe / g, 2)


def evaluate(sym: str, dyn: dict | None = None, price=None, arch: dict | None = None) -> dict:
    """按行业选尺、算倍数、判贵贱。返回：
    {industry, ruler, peg_applicable, metrics{pe?,peg?,growth?,...}, verdict, reliability, missing[], source, note}
    有 vetted 输入(架构师/EDGAR)→给数；缺→missing 标明缺什么、verdict='待接'。"""
    ind = industry_of(sym)
    m = MODEL.get(ind, {})
    out = {"symbol": sym, "industry": ind, "ruler": m.get("ruler", "待归类"),
           "peg_applicable": bool(m.get("peg")), "range": m.get("range", ""),
           "metrics": {}, "verdict": "", "reliability": "", "missing": [], "source": "", "note": ""}

    if ind == "未上市·无财报":
        out.update(verdict="无估值基础", reliability="—",
                   note="未上市·无公开财报，没有可估值的基础(不是没算·是没法算)。守着看。")
        return out

    # 架构师 vetted 值优先（6只中周期估算 + 候选 forward 判定）——这些是分析岗按行业口径给的
    if arch is None:
        arch = _arch_entry(sym)
    if arch:
        fp = arch.get("fair_price") or arch.get("archived_fair_price") or {}
        lo, mid, hi = fp.get("cheap"), fp.get("mid"), fp.get("rich")
        rel = str(arch.get("reliability") or "")
        vd = str(arch.get("verdict") or "")
        ruler_short = str(arch.get("ruler_short") or m.get("ruler", ""))
        if mid is not None:
            out["metrics"]["架构师中枢"] = mid
            out["metrics"]["区间"] = f"{lo}~{hi}"
            out.update(verdict=vd or "见架构师估算", reliability=rel or "架构师",
                       source=f"架构师估算·{ruler_short}",
                       note=str(arch.get("resolved_note") or arch.get("retract_note") or arch.get("method") or ""))
            # 有盈利有增速→补算 PEG（成熟/成长/消费/医疗类）
            if m.get("peg"):
                g = _growth_hint(arch)
                pe_peg = compute_peg(price, mid and _eps_hint(arch), g) if g else None
                if pe_peg:
                    out["metrics"]["PEG"] = pe_peg[1]
                    out["metrics"]["PE"] = pe_peg[0]
                elif g is None:
                    out["missing"].append("前瞻净利增速(算PEG)")
            return out

    # 无架构师值 → 按行业尺尝试算；缺输入→待接·缺X
    out["reliability"] = "低置信"
    if m.get("peg"):
        out["missing"].append("前瞻净利增速+穿周期EPS(算P/E+PEG)")
        out.update(verdict="待接",
                   note=f"该用『{m.get('ruler')}』：需前瞻净利增速+每股盈利(架构师/分析岗vetted)才算 PEG，本单未接·不编。")
    elif ind == "电力/能源":
        out["missing"].append("EBITDA+净负债+FCF(算EV/EBITDA·FCF收益率)")
        out.update(verdict="待接",
                   note="该用『EV/EBITDA+FCF收益率』：需 EBITDA/净负债/自由现金流(公司IR)，本单未接·不编。")
    elif ind == "软件/SaaS":
        out["missing"].append("营收增速+FCF利润率(算EV/Sales+Rule of 40)")
        out.update(verdict="待接",
                   note="该用『EV/Sales+Rule of 40』：需营收增速+FCF利润率，本单未接·不编。")
    elif ind == "加密/金融":
        if sym == "US.MSTR":
            out["missing"].append("比特币持仓净值+市值(算mNAV)")
            out.update(verdict="待接", note="该用『mNAV』：需比特币持仓净值 vs 市值，本单未接·不编。")
        else:
            out["missing"].append("穿牛熊正常化EPS/中性利率净利(架构师·低置信)")
            out.update(verdict="待接", note="该用『穿牛熊/中性利率正常化』(低置信)，本单架构师未给·不编。")
    else:
        out["missing"].append("该行业模型的关键输入")
        out.update(verdict="待接", note=f"该用『{m.get('ruler')}』，缺关键输入·不编。")
    return out


_AC = {}


def _arch_entry(sym: str) -> dict | None:
    if "d" not in _AC:
        try:
            p = sorted((ROOT / "data" / "valuation").glob("architect_normalized_est_*.json"))[-1]
            _AC["d"] = {str(e.get("ticker")): e for e in (_rj(p).get("estimates") or [])}
        except Exception:
            _AC["d"] = {}
    return (_AC["d"] or {}).get(sym)


def _growth_hint(arch: dict) -> float | None:
    """从架构师条目里找净利增速%(若给了)。没有→None(→PEG待接·缺增速)。"""
    for k in ("growth_pct", "net_income_growth_pct", "eps_growth_pct"):
        v = arch.get(k)
        if isinstance(v, (int, float)) and v > 0:
            return float(v)
    return None


def _eps_hint(arch: dict):
    for k in ("forward_eps", "normalized_eps"):
        v = arch.get(k)
        if isinstance(v, (int, float)):
            return v
    return None


def all_holdings_eval(date: str) -> list:
    prod = _rj(ROOT / "data" / "reports" / f"production_{date}.json")
    price = {str(h.get("symbol")): h.get("price") for h in prod.get("holdings", [])}
    out = []
    for h in prod.get("holdings", []):
        s = str(h.get("symbol"))
        if s.startswith("CC."):
            continue
        out.append(evaluate(s, price=price.get(s)))
    return out


if __name__ == "__main__":
    import sys, argparse
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="20260718")
    a = ap.parse_args()
    print("持仓·行业标签+用哪把尺+结论：")
    for r in all_holdings_eval(a.date):
        met = "·".join(f"{k}={v}" for k, v in r["metrics"].items()) or "—"
        miss = ("·缺:" + "/".join(r["missing"])) if r["missing"] else ""
        print(f"  {r['symbol']:<9}[{r['industry']:<9}] 尺={r['ruler'][:20]:<20} {r['verdict']:<8}"
              f"({r['reliability']}) {met}{miss}")
