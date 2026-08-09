# -*- coding: utf-8 -*-
"""★轮156 B:Yahoo Finance 财务摘要(港股护城河数据·港交所无keyless XBRL→Yahoo补)。
quoteSummary(cookie+crumb keyless)→ financialData(grossMargins毛利率/returnOnEquity ROE/operatingMargins/revenueGrowth·TTM口径)
+ incomeStatementHistory(近4年totalRevenue→营收增速稳定性·研发费若有)。
★口径=TTM(margins/ROE)·非近3年逐年(与EDGAR/EDINET不同口径)·源显式标Yahoo。★取不到NK4不估算。机器只取数·打分留Opus5(G2)。"""
import sys, json, ssl, statistics, http.cookiejar, urllib.request
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
_OP = None
_CRUMB = None


def _init():
    global _OP, _CRUMB
    if _OP is not None:
        return
    cj = http.cookiejar.CookieJar()
    _OP = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj), urllib.request.HTTPSHandler(context=CTX))
    try:
        _OP.open(urllib.request.Request("https://fc.yahoo.com", headers=UA), timeout=15)
    except Exception:
        pass
    try:
        _CRUMB = _OP.open(urllib.request.Request("https://query1.finance.yahoo.com/v1/test/getcrumb", headers=UA), timeout=15).read().decode()
    except Exception:
        _CRUMB = None


def _qs(sym, mods):
    _init()
    if not _CRUMB:
        return None
    try:
        url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{sym}?modules={mods}&crumb={_CRUMB}"
        r = _OP.open(urllib.request.Request(url, headers=UA), timeout=15).read()
        return json.loads(r)["quoteSummary"]["result"][0]
    except Exception:
        return None


def _raw(node, k):
    v = node.get(k)
    if isinstance(v, dict):
        return v.get("raw")
    return v


def to_yahoo(code):
    mk, sym = code.split(".", 1)
    if mk == "HK":
        return (sym.lstrip("0") or "0").zfill(4) + ".HK"
    if mk == "US":
        return sym
    if mk == "JP":
        return sym + ".T"
    return None


def get_financials(code):
    """返回4项(毛利率/ROE/研发率/营收增速稳定性)·Yahoo口径。取不到→NK4。"""
    sym = to_yahoo(code)
    d = _qs(sym, "financialData,incomeStatementHistory,defaultKeyStatistics") if sym else None
    if not d:
        return {"源": "Yahoo", "★状态": "NK4(Yahoo quoteSummary取不到)"}
    fd = d.get("financialData", {}) or {}
    gm = _raw(fd, "grossMargins"); roe = _raw(fd, "returnOnEquity")
    opm = _raw(fd, "operatingMargins"); rg = _raw(fd, "revenueGrowth")
    ish = (d.get("incomeStatementHistory", {}) or {}).get("incomeStatementHistory", []) or []
    revs = []
    rd_rate = None
    for s in ish:
        tr = _raw(s, "totalRevenue")
        if tr:
            revs.append((s.get("endDate", {}).get("fmt", "?"), tr))
        rd = _raw(s, "researchDevelopment")
        if rd and tr and rd_rate is None:
            rd_rate = round(rd / tr, 4)
    revs = list(reversed(revs))  # 旧→新
    growths = [(revs[i][1] - revs[i - 1][1]) / revs[i - 1][1] for i in range(1, len(revs)) if revs[i - 1][1]]
    rev_std = round(statistics.pstdev(growths), 4) if len(growths) >= 2 else None
    return {
        "源": "Yahoo", "口径": "TTM(margins/ROE)·营收近4年(增速std)",
        "毛利率TTM": round(gm, 4) if isinstance(gm, (int, float)) else "NK4",
        "ROE_TTM": round(roe, 4) if isinstance(roe, (int, float)) else "NK4",
        "营业利润率TTM": round(opm, 4) if isinstance(opm, (int, float)) else "NK4",
        "营收增速TTM": round(rg, 4) if isinstance(rg, (int, float)) else "NK4",
        "研发费用率": rd_rate if rd_rate is not None else "NK4(Yahoo无研发分项)",
        "营收增速稳定性(增速标准差)": rev_std if rev_std is not None else "NK4(年数不足)",
        "营收近年": {y: v for y, v in revs},
        "★状态": "Yahoo取到",
    }


def get_consensus(code):
    """★轮160 A:市场预期consensus(Yahoo keyless)。最新季EPS actual vs est+surprise·前瞻consensus。取不到→NK4。"""
    sym = to_yahoo(code)
    d = _qs(sym, "earningsHistory,earningsTrend") if sym else None
    if not d:
        return {"源": "Yahoo", "★状态": "NK4(Yahoo consensus取不到)"}
    eh = (d.get("earningsHistory", {}) or {}).get("history", []) or []
    latest = eh[-1] if eh else {}
    et = (d.get("earningsTrend", {}) or {}).get("trend", []) or []
    fwd = {}
    for t in et:
        p = t.get("period")
        if p in ("0q", "+1q", "0y", "+1y"):
            fwd[p] = {"EPS_consensus": _raw(t.get("earningsEstimate", {}) or {}, "avg"),
                      "营收_consensus": _raw(t.get("revenueEstimate", {}) or {}, "avg")}
    return {
        "源": "Yahoo(keyless·非付费源)",
        "最新季": (latest.get("quarter", {}) or {}).get("fmt"),
        "EPS_actual": _raw(latest, "epsActual"), "EPS_consensus": _raw(latest, "epsEstimate"),
        "★EPS_surprise%": (round(_raw(latest, "surprisePercent") * 100, 1) if isinstance(_raw(latest, "surprisePercent"), (int, float)) else "NK4"),
        "前瞻consensus": fwd or "NK4",
        "★状态": "Yahoo取到",
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for code in ["HK.00700", "HK.09698", "HK.00981"]:
        print(code, json.dumps(get_financials(code), ensure_ascii=False)[:200])
    for code in ["US.AMKR", "US.RBLX"]:
        print(code, json.dumps(get_consensus(code), ensure_ascii=False)[:200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
