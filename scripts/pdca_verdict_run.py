#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
pdca_verdict_run.py —— N2(轮50):概率预测到期记分(尺§五·看板G0)。
到期日取该只【实际收盘价】→ 落在哪个情景区间 → 判命中/未命中/部分:
  · 落在某情景区间内 = 该情景命中(记 scenario + 标称概率)
  · 落在所有区间之外 = ★「区间划错」(不是概率错)——必须与「概率错」分开记
输出 data/pdca/verdict_{date}.json + 回写 locked_predictions_registry 该条结果。
★N2-3 取价来源必须写明(daily_scan.last_price);取不到 → 报「取不到·未记分」·严禁近似价假判。
用法: python scripts/pdca_verdict_run.py --asof 2026-07-31
"""
import argparse, json, sys, glob
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def _actual_close(code, dc):
    """从 daily_scan_{dc}.json 取实际收盘价·返回 (price, source) 或 (None, 取不到原因)。★不近似。"""
    p = ROOT / "data/market" / f"daily_scan_{dc}.json"
    if not p.exists():
        return None, f"取不到·daily_scan_{dc}.json 不存在(该日未扫描)·未记分"
    d = json.loads(p.read_text(encoding="utf-8"))
    for it in d.get("items", []):
        if it.get("code") == code or it.get("symbol") == code:
            lp = it.get("last_price")
            if lp is not None:
                return lp, f"daily_scan_{dc}.json.items[{code}].last_price"
            return None, f"取不到·daily_scan 有 {code} 但 last_price 为空·未记分"
    return None, f"取不到·daily_scan_{dc}.json 无 {code}·未记分"


def _forecasts_by_id():
    out = {}
    for fp in glob.glob(str(ROOT / "data/forecast/forecast_*.json")):
        for f in json.loads(Path(fp).read_text(encoding="utf-8")).get("forecasts", []):
            if f.get("forecast_id"):
                out[f["forecast_id"]] = f
    return out


def run(asof):
    reg_p = ROOT / "data/forecast/locked_predictions_registry.json"
    reg = json.loads(reg_p.read_text(encoding="utf-8"))
    fcs = _forecasts_by_id()
    verdicts = []
    for e in reg.get("已登记预测", []):
        vd = (e.get("verdict_date") or "")[:10]
        if not vd or vd > asof:
            continue  # 未到期
        if e.get("结果") and e.get("结果", {}).get("已判定"):
            continue  # 已判过
        f = fcs.get(e.get("forecast_id"), {})
        code = f.get("ticker") or e.get("ticker")
        price, src = _actual_close(code, vd.replace("-", ""))
        if price is None:
            v = {"forecast_id": e.get("forecast_id"), "ticker": code, "verdict_date": vd,
                 "已判定": False, "结果": "取不到实际价·未记分", "取价来源": src}
            verdicts.append(v); e["结果"] = v
            continue
        # 落在哪个情景区间
        hit = None
        for s in f.get("scenarios", []):
            rng = s.get("range", [None, None])
            if rng[0] is not None and rng[0] <= price <= rng[1]:
                hit = s; break
        if hit:
            outcome = {"类型": "情景命中", "命中情景": hit.get("name"), "命中标称概率": hit.get("prob")}
        else:
            # 落在所有区间外 = 区间划错(★与概率错分开)
            outcome = {"类型": "区间划错", "命中情景": None, "命中标称概率": None,
                       "说明": "实际价落在所有情景区间之外——是区间划错·非概率错(尺§五·N2-1)"}
        v = {"forecast_id": e.get("forecast_id"), "ticker": code, "verdict_date": vd,
             "已判定": True, "实际收盘价": price, "取价来源": src,
             "各情景区间": [{"名": s.get("name"), "区间": s.get("range"), "概率": s.get("prob")} for s in f.get("scenarios", [])],
             **outcome}
        verdicts.append(v); e["结果"] = v

    # 回写 registry + 出 verdict 文件
    reg["verdict更新"] = f"asof {asof} · 判定 {sum(1 for v in verdicts if v.get('已判定'))} 条 · 取不到 {sum(1 for v in verdicts if not v.get('已判定'))} 条"
    reg_p.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    vp = ROOT / "data/pdca" / f"verdict_{asof}.json"
    vp.parent.mkdir(parents=True, exist_ok=True)
    vp.write_text(json.dumps({"asof": asof, "verdicts": verdicts}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # N2-2 概率校准:按情景命中 vs 标称概率累计(★样本<10只记录不下结论)
    judged = [v for v in verdicts if v.get("已判定")]
    bands = {}
    for v in judged:
        if v.get("类型") == "情景命中":
            b = str(v.get("命中标称概率"))
            bands.setdefault(b, {"命中该档情景数": 0}); bands[b]["命中该档情景数"] += 1
    calib = {"asof": asof, "已判定样本数": len(judged), "区间划错数": sum(1 for v in judged if v.get("类型") == "区间划错"),
             "按标称概率档(情景命中计数)": bands,
             "★结论": "样本 <10·只记录不下结论(小样本不下结论·CLAUDE.md数据坑位)" if len(judged) < 10 else "样本≥10·可校准",
             "_说明": "命中率用于校准概率(尺§五):标X%那批实际命中率显著<X%→该档整体下调。区间划错单列(非概率错)。"}
    (ROOT / "data/pdca/prob_calibration.json").write_text(json.dumps(calib, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return verdicts, vp


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--asof", required=True); a = ap.parse_args()
    verdicts, vp = run(a.asof)
    print(f"[pdca_verdict] asof {a.asof} · 到期 {len(verdicts)} 条 → {vp.name}")
    for v in verdicts:
        if v.get("已判定"):
            print(f"  {v['ticker']} 实际 {v['实际收盘价']} → {v.get('类型')}({v.get('命中情景')}·标称{v.get('命中标称概率')}) · 源 {v['取价来源']}")
        else:
            print(f"  {v['ticker']} → {v['结果']}（{v['取价来源']}）")


if __name__ == "__main__":
    raise SystemExit(main())
