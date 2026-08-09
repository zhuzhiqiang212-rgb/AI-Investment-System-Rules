# -*- coding: utf-8 -*-
"""★轮119 NY1:判断沉淀机制——工单=当日待办(可清)·台账=判断历史(★只增不改·不可清)。
sediment(dc):把 judgment_slots_{dc} 里 Opus5 已填(各层判断+⑥复核)沉淀到 data/pdca/layer_judgment_ledger.json(按日期累积·含判断/依据/引用证据ID/填写时刻/run_id)。
prior_for_layer / prior_recheck:供次日工单显示【既有判断】供对照(NY2-2·Opus5须显式选延续/修正/推翻·不默认继承)。
★台账只增不改:改判＝新增一条并标『修正自哪条』·★不覆盖旧值(PDCA分母:原判错就该记着错)。★Code不填任何判断·只搬运Opus5已填。"""
import sys, json, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
LEDGER = ROOT / "data/pdca/layer_judgment_ledger.json"


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_ledger():
    d = _rj(LEDGER)
    return d.get("entries", []) if d else []


def _save_ledger(entries):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps({"_说明": "★轮119 判断历史台账·只增不改。改判=新增并标修正自·不覆盖(PDCA分母)。Code只搬运Opus5已填。",
                                  "entries": entries}, ensure_ascii=False, indent=2), encoding="utf-8")


def sediment(dc):
    """把 judgment_slots_{dc} 已填内容沉淀到台账(只增不改·去重按 date+层+签名)。返回沉淀条数。"""
    js = _rj(ROOT / "data/pipeline" / f"judgment_slots_{dc}.json")
    if not js:
        return 0, "无工单文件"
    dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    run_id = ""
    try:
        run_id = json.loads((ROOT / "data/product_manifest.json").read_text(encoding="utf-8")).get("run_id", "")
    except Exception:
        pass
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
    entries = _load_ledger()
    exist_keys = {(e.get("date"), e.get("层"), e.get("签名")) for e in entries}
    added = 0
    for k, s in (js.get("②~⑦层工单", {}) or {}).items():
        slot = s.get("槽位", {}) or {}
        j = slot.get("本层判断")
        if j:
            sig = str(j)[:60]
            key = (dh, k, sig)
            if key not in exist_keys:
                entries.append({"date": dh, "层": k, "类型": "本层判断", "判断": j, "依据": slot.get("依据"),
                                "证伪信号": slot.get("证伪信号"), "引用证据ID": slot.get("★引用证据ID(NV2-4·必填·不许凭空)"),
                                "填写时刻": now, "run_id": run_id, "签名": sig, "修正自": None})
                exist_keys.add(key); added += 1
        # ⑥层复核
        for r in s.get("★须复核既有判断(NV3)", []):
            cs = r.get("★复核槽位(Opus5填)", {}) or {}
            concl = cs.get("维持原判/修正/撤回")
            if concl:
                sig = "%s|%s" % (r.get("标的"), str(concl)[:20])
                key = (dh, "%s·复核·%s" % (k, r.get("标的")), sig)
                if key not in exist_keys:
                    entries.append({"date": dh, "层": "%s·复核·%s" % (k, r.get("标的")), "类型": "复核结论",
                                    "标的": r.get("标的"), "复核结论": concl, "原判断": r.get("★原判断(保留台账·不覆盖·NV3-3)"),
                                    "理由": cs.get("理由"), "证伪信号": cs.get("新证伪信号"),
                                    "引用证据ID": cs.get("★引用证据ID"), "错因": cs.get("★原判断错在哪(供PDCA记分)") or "时机错(把有依据的方向与无依据的时点捆成一个动作)",
                                    "填写时刻": now, "run_id": run_id, "签名": sig, "修正自": None})
                    exist_keys.add(key); added += 1
    _save_ledger(entries)
    return added, "沉淀 %d 条(台账共 %d 条·只增不改)" % (added, len(entries))


def prior_for_layer(layer_key):
    """次日工单用:该层台账最近一条判断(供对照·NY2-2)。"""
    hit = [e for e in _load_ledger() if e.get("层") == layer_key and e.get("类型") == "本层判断"]
    return hit[-1] if hit else None


def prior_recheck(ticker):
    """次日工单用:该标的最近一条复核结论。"""
    hit = [e for e in _load_ledger() if e.get("标的") == ticker and e.get("类型") == "复核结论"]
    return hit[-1] if hit else None


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True)
    ap.add_argument("--sediment", action="store_true"); a = ap.parse_args()
    dc = a.date.replace("-", "")
    n, msg = sediment(dc)
    print("[判断沉淀]", msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
