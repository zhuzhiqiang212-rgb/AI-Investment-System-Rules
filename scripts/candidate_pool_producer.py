# -*- coding: utf-8 -*-
"""D2③(尺v1.1)·候选池生产者。按当日第1关激活板块·逐格取龙头/承接节点→data/opportunity/candidate_pool_{date}.json。
含 ticker/name/sector_cell/driver_group/估值引擎入参。★严禁全市场自下而上凑名单;上游(激活清单当日)未就绪→据实报未产出·不先凑池子。
Code只按激活格取候选骨架·不点公允值(fair_value由估值引擎当日跑)。"""
import json, argparse, pathlib, glob
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9)); ROOT = pathlib.Path(__file__).resolve().parent.parent
def build(date):
    dd = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    # ★轮87 EA2:排除TEMPLATE(模板永不当实际清单)·取 data_date 最新且≤当日的一份(非 sorted(glob)[-1])。
    _cands_f = []
    for f in glob.glob(str(ROOT / "data" / "market" / "sector_activation_*.json")):
        if "TEMPLATE" in pathlib.Path(f).name.upper():
            continue
        try:
            _fj = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
        except Exception:
            _fj = {}
        if _fj.get("★可用于生产") is not True:   # ★★★收尾:跳过未终验清单(可用于生产!=true)
            continue
        _dt = _fj.get("data_date", "")
        if _dt and _dt <= dd:
            _cands_f.append((_dt, f))
    _cands_f.sort()
    if not _cands_f:
        return {"date": dd, "produced": False, "reason": "无有效激活清单文件(排除TEMPLATE后)"}
    actfile = _cands_f[-1][1]
    if "TEMPLATE" in pathlib.Path(actfile).name.upper():   # EA2-2 断言
        raise RuntimeError("EA2:候选池选中TEMPLATE·禁止把模板当实际清单")
    aj = json.loads(pathlib.Path(actfile).read_text(encoding="utf-8"))
    # ★轮87 EA3:作废只看结构化字段(作废/有效期至)·非当日≠作废(周末/off-cycle接受最近有效清单·不据自由文本关键词)。
    if (aj.get("作废") is True) or (aj.get("有效期至") and str(dd) > str(aj.get("有效期至"))):
        return {"date": dd, "produced": False,
                "reason": "★激活清单显式结构化字段判失效(作废=true 或 过有效期)·不用" ,
                "activation_file": actfile, "candidates": []}
    # 当日激活清单就绪:逐格取龙头/承接节点骨架(fair_value留空·由估值引擎当日跑·此处不点)
    cands = []
    for b in aj.get("板块", []):
        if b.get("激活") is True:
            for role in ("龙头", "承接节点"):
                cands.append({"sector_cell": (b.get("格名") or b.get("板块")), "role": role, "driver_group": b.get("驱动类型"),  # ★P0-3:兼容格名(A稿)/板块(旧清单)
                              "driver_basis": b.get("激活依据", "")[:60], "ticker": "", "name": "",
                              "fair_value": {"value": 0, "method": "", "as_of": "", "confidence": "C", "hardcoded": False},
                              "price": None, "note": "★待第2关财务扫描填龙头ticker+估值引擎当日跑fair_value"})
    return {"date": dd, "produced": True, "activation_file": actfile, "candidates": cands,
            "note": "候选骨架按激活格产出·ticker与fair_value待第2~3关(财务扫描/估值引擎)当日填·未自下而上"}
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d")); a = ap.parse_args()
    r = build(a.date)
    out = ROOT / "data" / "opportunity" / f"candidate_pool_{r['date']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    print("候选池生产者 %s → %s · produced=%s" % (a.date, out.name, r["produced"]))
    if not r["produced"]:
        print(" ", r["reason"][:100])
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
