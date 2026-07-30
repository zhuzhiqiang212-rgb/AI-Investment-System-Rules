#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
prob_calibration_build.py —— 预测优先口径·概率分布版 PDCA 闭环(正式尺§五·看板 G0·2026-07-30)
(与旧 forecast_pdca.py=里程碑2双尺度版并存·此为新概率分布版)
J3-2 到见分晓日自动核对:命中/未命中/部分命中 + ★记录是哪一条依据错了。
J3-3 概率校准表:按置信度/概率档统计实际命中率 → data/pdca/prob_calibration.json
     ★命中率是用来校准概率的(若"70%"那批实际只中40%→整体下调),不是自夸。
用法: python scripts/prob_calibration_build.py --asof 2026-07-30
     价格源未接时,due 预测标『待接实际价·无法自动判定』(不假判命中)。
"""
import argparse, json, sys, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_registry():
    p = ROOT / "data/forecast/locked_predictions_registry.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"已登记预测": []}


def _load_forecasts():
    out = {}
    for fp in glob.glob(str(ROOT / "data/forecast/forecast_*.json")):
        try:
            d = json.loads(Path(fp).read_text(encoding="utf-8"))
        except Exception:
            continue
        for f in (d.get("forecasts", []) or []):
            if f.get("forecast_id"):
                out[f["forecast_id"]] = f
    return out


def run(asof: str):
    reg = _load_registry()
    fcs = _load_forecasts()
    entries = reg.get("已登记预测", []) or []

    due, pending = [], []
    for e in entries:
        vd = (e.get("verdict_date") or "")[:10]
        (due if vd and vd <= asof else pending).append(e)

    # J3-2 核对(due):价格源未接 → 标待接·不假判(★不假报命中)
    verdicts = []
    for e in due:
        f = fcs.get(e.get("forecast_id"), {})
        verdicts.append({
            "forecast_id": e.get("forecast_id"), "ticker": e.get("ticker"),
            "verdict_date": e.get("verdict_date"), "confidence": f.get("confidence"),
            "结果": "待接实际价·无法自动判定(命中/未命中/部分)",
            "错因依据": None,   # 判定后写:是哪一条 scenario.basis 错了(J3-2)
        })

    # J3-3 概率校准表:按置信度档聚合·命中率=命中数/已判定数
    bands = {}
    for e in entries:
        f = fcs.get(e.get("forecast_id"), {})
        conf = f.get("confidence") or "?"
        b = bands.setdefault(conf, {"总数": 0, "已判定": 0, "命中": 0, "命中率": None})
        b["总数"] += 1
    calib = {
        "_说明": "按置信度档统计实际命中率·用于校准(尺§五)。★命中率<标称→该档整体下调。价格源接上、有 due 预测判定后此表才有非零命中率。",
        "asof": asof, "已登记总数": len(entries), "到期待判定(due)": len(due),
        "未到期(pending)": len(pending), "按置信度档": bands, "待判定明细": verdicts,
        "★状态": "接线跑通·当前无到期预测(样例 verdict_date=2027)→命中率暂空·待到期后填",
    }
    outp = ROOT / "data/pdca/prob_calibration.json"
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(calib, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"due": len(due), "pending": len(pending), "verdicts": verdicts, "calib_path": str(outp)}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="预测概率分布版 PDCA 核对与概率校准(尺§五)")
    ap.add_argument("--asof", required=True, help="形如 2026-07-30")
    a = ap.parse_args()
    r = run(a.asof)
    print(f"[prob_calibration] due={r['due']} pending={r['pending']} → 写 {Path(r['calib_path']).name}")
    for v in r["verdicts"]:
        print("  待判定:", v["forecast_id"], v["ticker"], v["verdict_date"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
