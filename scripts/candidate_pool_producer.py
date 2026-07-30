# -*- coding: utf-8 -*-
"""D2③(尺v1.1)·候选池生产者。按当日第1关激活板块·逐格取龙头/承接节点→data/opportunity/candidate_pool_{date}.json。
含 ticker/name/sector_cell/driver_group/估值引擎入参。★严禁全市场自下而上凑名单;上游(激活清单当日)未就绪→据实报未产出·不先凑池子。
Code只按激活格取候选骨架·不点公允值(fair_value由估值引擎当日跑)。"""
import json, argparse, pathlib, glob
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9)); ROOT = pathlib.Path(__file__).resolve().parent.parent
def build(date):
    dd = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    sa = sorted(glob.glob(str(ROOT / "data" / "market" / "sector_activation_*.json")))
    if not sa:
        return {"date": dd, "produced": False, "reason": "无激活清单文件"}
    aj = json.loads(pathlib.Path(sa[-1]).read_text(encoding="utf-8"))
    if aj.get("data_date") != dd:
        return {"date": dd, "produced": False,
                "reason": "★未产出:最新激活清单 data_date=%s≠当日%s·且该清单自写FOMC后须重判已作废→上游(第1关激活板块)未就绪·据实报未产出·不自下而上凑名单·不先凑个池子跑通了算" % (aj.get("data_date"), dd),
                "activation_file": sa[-1], "candidates": []}
    # 当日激活清单就绪:逐格取龙头/承接节点骨架(fair_value留空·由估值引擎当日跑·此处不点)
    cands = []
    for b in aj.get("板块", []):
        if b.get("激活") is True:
            for role in ("龙头", "承接节点"):
                cands.append({"sector_cell": b.get("板块"), "role": role, "driver_group": b.get("驱动类型"),
                              "driver_basis": b.get("激活依据", "")[:60], "ticker": "", "name": "",
                              "fair_value": {"value": 0, "method": "", "as_of": "", "confidence": "C", "hardcoded": False},
                              "price": None, "note": "★待第2关财务扫描填龙头ticker+估值引擎当日跑fair_value"})
    return {"date": dd, "produced": True, "activation_file": sa[-1], "candidates": cands,
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
