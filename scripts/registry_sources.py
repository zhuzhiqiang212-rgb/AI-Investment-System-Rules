# -*- coding: utf-8 -*-
"""★★★轮222:两个 registry 统一【读取口径】(不合并内容·只改读的人·GPT/董事长裁定)。
源①`data/pdca/locked_predictions_registry.json`   (58条·07-22 baseline·押方向·冻结·只允许状态写回)
源②`data/forecast/locked_predictions_registry.json`(26条·概率分布版·verdict_date·今后新锁定只进这里)
★本模块把两源规范化成统一 schema·供 逾期扫描/胜率计数器/体检 共用。★不改任何被读文件。
字段映射:到期日 = pdca『PDCA核对日』/ forecast『verdict_date』;状态 = pdca『状态』/ forecast『无此字段→按 forecast_id 有无记分文件判』。"""
import json, re, glob
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDCA = ROOT / "data/pdca/locked_predictions_registry.json"
FORECAST = ROOT / "data/forecast/locked_predictions_registry.json"
_HZ = {"0-30d": "短期", "1y": "长期", "短期": "短期", "长期": "长期"}


def _ticker(s):
    m = re.search(r"(US|JP)\.[A-Z0-9]+", str(s or ""))
    return m.group(0) if m else str(s or "")


def _lock_price(p):
    return p.get("锁定价") if p.get("锁定价") is not None else p.get("现价")


def _classify(判定):
    t = str(判定 or "")
    if "不可记分" in t:
        return "已评·不可记分"
    if "偏差" in t or "非最高" in t:
        return "已评·未命中"
    if "命中" in t:
        return "已评·命中"
    return None


def scoring_index():
    """{forecast_id: 状态} —— 从 first_real_scoring*.json 抽 forecast源的记分结论(按 forecast_id 关联)。"""
    idx = {}
    for f in glob.glob(str(ROOT / "data/pdca/first_real_scoring*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        def walk(o):
            if isinstance(o, dict):
                fid = o.get("forecast_id")
                if fid:
                    verd = None
                    for k, v in o.items():
                        if isinstance(v, dict) and ("判定" in json.dumps(v, ensure_ascii=False)):
                            for k2, v2 in v.items():
                                if "判定" in str(k2) and isinstance(v2, str):
                                    verd = _classify(v2)
                    if verd:
                        idx[fid] = verd
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for x in o:
                    walk(x)
        walk(d)
    return idx


def load_all():
    """返回规范化条目列表。每条:{源,标的,ticker,尺度,到期日,状态,锁定价,判据,sha,forecast_id,计分,可严格评分,已评}。"""
    out = []
    sidx = scoring_index()
    # 源① pdca
    if PDCA.exists():
        d = json.loads(PDCA.read_text(encoding="utf-8"))
        for i, p in enumerate(d.get("已登记预测") or []):
            状态 = str(p.get("状态") or "")
            out.append({"源": "pdca", "idx": i, "标的": p.get("标的"), "ticker": _ticker(p.get("标的")),
                        "尺度": _HZ.get(str(p.get("尺度")), str(p.get("尺度"))), "到期日": p.get("PDCA核对日"),
                        "状态": 状态, "锁定价": _lock_price(p), "判据": p.get("PDCA判据"),
                        "sha": p.get("锁定sha256"), "forecast_id": p.get("forecast_id"),
                        "计分": p.get("计分"), "可严格评分": p.get("可严格评分"), "已评": ("已评" in 状态)})
    # 源② forecast(状态由 forecast_id 记分索引判)
    if FORECAST.exists():
        d = json.loads(FORECAST.read_text(encoding="utf-8"))
        for i, p in enumerate(d.get("已登记预测") or []):
            fid = p.get("forecast_id")
            状态 = sidx.get(fid)          # None=未评
            out.append({"源": "forecast", "idx": i, "标的": p.get("ticker"), "ticker": p.get("ticker"),
                        "尺度": _HZ.get(str(p.get("horizon")), str(p.get("horizon"))), "到期日": p.get("verdict_date"),
                        "状态": 状态 or "已锁定待评", "锁定价": None, "判据": None,
                        "sha": p.get("sha256"), "forecast_id": fid,
                        "计分": None, "可严格评分": None, "已评": bool(状态)})
    return out
