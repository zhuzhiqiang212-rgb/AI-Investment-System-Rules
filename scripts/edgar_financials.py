#!/usr/bin/env python3
"""财报官方接口：SEC EDGAR 自动取数（董事局工单2026-07-17·丙1）· 只读不下单

治「财报季漏」(台积电Q2式)：不再等人工录，直接连 SEC EDGAR XBRL 官方接口取真财务数。

⚠边界（CLAUDE.md §1 不设计不决策）：
  那 6 只待接估值缺的是【正常年景EPS / 正常化EPS / 分部资产估值】——
  "哪几年算正常年景"、"该给几倍"是**分析判断**，不是机械取数，我不定。
  本模块只做能机械做的：
    · 从 EDGAR 取【真·多年历史 EPS/营收/净利】(带 form/fy/期末日/来源URL)
    · 按几个常见窗口算出【候选】正常化值(3/5/7年均)，标明"候选·待理解岗确认"
  理解岗确认后填进 val_inputs.json，估值引擎自动重算(不换方法)。
  取不到 → 标待接、不编。

产物：data/valuation/edgar_financials_{date}.json
用法：python scripts/edgar_financials.py --date 20260717
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
UA = {"User-Agent": "AI-Investment-System zhuzhiqiang212@gmail.com"}
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
CONCEPT = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/{tx}/{tag}.json"
# 估值待接、且在 SEC 报财报的(日股不在 EDGAR·如爱德万/伊藤忠→标"非美国上市·EDGAR无此数")
US_WAIT = ["TSM", "SNDK", "COIN", "CRCL"]
NON_US = {"JP.6857": "爱德万(日本上市)", "JP.8001": "伊藤忠(日本上市)"}
# 年度稀释EPS 的 XBRL 标签：美国公司报 us-gaap；外国发行人(如台积电 20-F)报 ifrs-full → 两套都试
EPS_TAGS = [("us-gaap", "EarningsPerShareDiluted"), ("us-gaap", "EarningsPerShareBasicAndDiluted"),
            ("us-gaap", "EarningsPerShareBasic"),
            ("us-gaap", "IncomeLossFromContinuingOperationsPerDilutedShare"),
            ("ifrs-full", "DilutedEarningsLossPerShare"), ("ifrs-full", "BasicEarningsLossPerShare")]


def _get(url: str) -> dict | None:
    try:
        return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25).read())
    except Exception:
        return None


def cik_map() -> dict:
    d = _get(TICKERS_URL) or {}
    return {str(v["ticker"]).upper(): int(v["cik_str"]) for v in d.values()}


def annual_eps(cik: int) -> tuple[list, str]:
    """取年度稀释EPS 序列(10-K/20-F)。返回 (序列, 用的标签)。取不到→([], "")"""
    for tx, tag in EPS_TAGS:
        d = _get(CONCEPT.format(cik=cik, tx=tx, tag=tag))
        time.sleep(0.2)                       # 守 SEC 的调用频率礼仪
        if not d:
            continue
        rows = []
        for unit, vals in (d.get("units") or {}).items():
            if "share" not in unit.lower():
                continue
            for x in vals:
                if str(x.get("form")) not in ("10-K", "20-F"):
                    continue
                if x.get("fp") not in (None, "FY"):
                    continue
                # 只要整年期(约365天)，排除季度/半年
                try:
                    s = datetime.fromisoformat(x["start"]).date()
                    e = datetime.fromisoformat(x["end"]).date()
                    if not (330 <= (e - s).days <= 400):
                        continue
                except Exception:
                    continue
                rows.append({"fy": x.get("fy"), "form": x.get("form"), "end": x.get("end"),
                             "eps": x.get("val"), "filed": x.get("filed"), "unit": unit})
        if rows:
            uniq = {}
            for r in rows:                     # 同一 fy 多次申报 → 取最后申报的(修订后)
                k = r["end"]
                if k not in uniq or str(r["filed"]) > str(uniq[k]["filed"]):
                    uniq[k] = r
            out = sorted(uniq.values(), key=lambda r: str(r["end"]))
            return out, f"{tx}:{tag}"
    return [], ""


def build(date: str) -> dict:
    m = cik_map()
    if not m:
        return {"error": "SEC EDGAR ticker→CIK 表取不到（网络/接口）→ 待接、不编", "symbols": {}}
    out = {}
    for tk in US_WAIT:
        cik = m.get(tk)
        if not cik:
            out[tk] = {"status": "待接", "reason": f"EDGAR 里查不到 {tk} 的 CIK"}
            continue
        ser, tag = annual_eps(cik)
        if not ser:
            out[tk] = {"status": "待接", "cik": cik,
                       "reason": "EDGAR 里没取到年度稀释EPS（标签不匹配或未申报）→ 不编"}
            continue
        eps = [r["eps"] for r in ser if isinstance(r.get("eps"), (int, float))]
        cand = {}
        for n in (3, 5, 7):
            if len(eps) >= n:
                cand[f"{n}年均"] = round(sum(eps[-n:]) / n, 4)
        out[tk] = {
            "status": "OK", "cik": cik, "xbrl_tag": tag,
            "source_url": CONCEPT.format(cik=cik, tx=tag.split(":")[0], tag=tag.split(":")[-1]),
            "history": ser[-10:],
            "candidate_normalized_eps": cand,
            "_候选说明": "以上是【按真·历史EPS机械算的候选值】，不是结论。"
                        "「哪几年算正常年景／该给几倍」属分析判断(CLAUDE.md §1 我不定)——"
                        "请理解岗挑一个窗口、确认后填进 val_inputs.json 的 normal_eps/normalized_eps，"
                        "估值引擎会按同一类型模型自动重算(不换方法)。",
        }
    for sym, why in NON_US.items():
        out[sym] = {"status": "待接", "reason": f"{why} → 不在 SEC EDGAR，此接口取不到；"
                                                f"需另接 EDINET(日本)或公司IR，本单未做"}
    return {"error": "", "symbols": out}


def main() -> int:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="SEC EDGAR 财报自动取数")
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    r = build(a.date)
    doc = {"_说明": "SEC EDGAR XBRL 官方接口取的【真·多年财务数】。本模块只取数+算候选正常化值，"
                   "不做'正常年景是哪几年'的判断(那属分析判断)。取不到→标待接、不编。",
           "date": a.date, "generated_at": datetime.now(JST).isoformat(timespec="seconds"),
           "source": "SEC EDGAR XBRL companyconcept (keyless·需 User-Agent)",
           "error": r.get("error", ""), "symbols": r.get("symbols", {})}
    p = ROOT / "data" / "valuation" / f"edgar_financials_{a.date}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if doc["error"]:
        print(f"[EDGAR 失败] {doc['error']}", file=sys.stderr)
        return 3
    ok = [k for k, v in doc["symbols"].items() if v.get("status") == "OK"]
    print(f"wrote {p.name} · 取到 {len(ok)}/{len(doc['symbols'])} 只")
    for k, v in doc["symbols"].items():
        if v.get("status") == "OK":
            h = v["history"]
            print(f"   ✔ {k:6s} CIK={v['cik']} · {len(h)}年历史(最近 {h[-1]['fy']} EPS={h[-1]['eps']}) "
                  f"· 候选正常化EPS {v['candidate_normalized_eps']}")
        else:
            print(f"   △ {k:9s} {v['reason'][:70]}")
    print("   ⚠ 候选值需理解岗确认后填 val_inputs.json 才会进估值（我不替它定'正常年景'）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
