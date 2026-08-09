# -*- coding: utf-8 -*-
"""★轮158 B:标的身份核验(防「看代码凭印象认错」——JP.7735被误当发那科的教训)。
每只补【公司全名 + 主营(行业)】。源:Yahoo assetProfile(longName/industry/sector)·富途basicinfo兜底。
覆盖:20持仓 + Top30候选 + 25异动(评分/产品/异动清单都要带名·不许只显代码)。★取不到标『身份待核』不编。"""
import sys, json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import yahoo_financials as YF

HOLDINGS = ["JP.4568", "US.NVDA", "US.MSFT", "US.MSTR", "US.COIN", "JP.9984", "JP.8766", "JP.6758",
            "JP.6857", "JP.7203", "JP.8001", "JP.7832", "JP.7974", "US.AVGO", "US.CRCL", "US.SNDK",
            "US.TSM", "US.META", "US.IBKR", "US.SPCX"]
# 已知全名(私司/无Yahoo兜底·不编)
KNOWN = {"US.SPCX": {"全名": "Space Exploration Technologies Corp. (SpaceX)", "行业": "Aerospace (private)", "板块": "Industrials"}}


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _latest(pat):
    g = sorted(ROOT.glob(pat)); return g[-1] if g else None


def resolve(code):
    if code in KNOWN:
        return {**KNOWN[code], "源": "已知(不编)"}
    sym = YF.to_yahoo(code)
    if not sym:
        return {"全名": "身份待核", "行业": None, "板块": None, "源": "NK"}
    d = YF._qs(sym, "assetProfile,price")
    if not d:
        return {"全名": "身份待核(Yahoo取不到)", "行业": None, "板块": None, "源": "NK"}
    ap = d.get("assetProfile", {}) or {}; pr = d.get("price", {}) or {}
    name = pr.get("longName") or pr.get("shortName") or "身份待核"
    return {"全名": name, "行业": ap.get("industry"), "板块": ap.get("sector"), "源": "Yahoo"}


def build(dc):
    prio = _rj(_latest("data/opportunity/candidate_priority_*.json"))
    top = [r["标的"] for r in (prio.get("★Top30_板块非受损(个股层面优先)", []) + prio.get("★★Top30_板块受损(便宜可能是板块问题·单独分组·须Opus5辨)", []))][:30]
    tg = _rj(_latest("data/universe/type_gate3_*.json"))
    anom = [a["code"] for a in tg.get("★C异动明细", [])]
    codes = []
    for c in HOLDINGS + top + anom:
        if c not in codes:
            codes.append(c)
    idmap = {}
    for c in codes:
        idmap[c] = resolve(c)
        time.sleep(0.2)
    out = {
        "_说明": "★轮158 标的身份(全名+主营行业)。防看代码认错(JP.7735≠发那科教训)。源Yahoo assetProfile·取不到标身份待核不编。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "覆盖数": len(idmap),
        "身份": idmap,
    }
    (ROOT / f"data/opportunity/identity_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("身份覆盖", o["覆盖数"], "只")
    for c in ["JP.7735", "JP.6857", "US.CTSH", "US.AMKR"]:
        i = o["身份"].get(c, {})
        print("  %-9s %s · %s" % (c, i.get("全名"), i.get("行业")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
