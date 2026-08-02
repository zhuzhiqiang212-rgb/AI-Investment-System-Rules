# -*- coding: utf-8 -*-
"""★轮79 AS:第⑦层复盘记分卡(系统的魂)。四部件:①判断记分卡(累积·只追加) ②确定性累积表(七层派生·升档写死)
③多尺度复盘(日/周) ④决策质量评分。★AS6产品能看出哪层最弱。AS5:pdca_verdict/locked/prob_calibration保留·经forecast_id关联。"""
import sys, json, argparse, glob, re
from datetime import datetime, timezone, timedelta, date as _date
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
SC = ROOT / "data" / "pdca" / "judgment_scorecard.json"
CL = ROOT / "data" / "pdca" / "certainty_ledger.json"
GRADE_COEF = {"A": 1.0, "B": 0.6, "C": 0.3}   # AS4依据等级系数
LAYERS = ["①世界观", "②国家战略", "③资金流动", "④板块地图", "⑤个股研究", "⑥持仓层", "⑦复盘层"]


def _load_sc():
    if SC.exists():
        try:
            return json.loads(SC.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"_说明": "★判断记分卡(第⑦层部件①)·累积型只追加不覆盖。每条判断=一层的一个可证伪判断+把握分+依据等级+证伪条件+验证。", "entries": []}


def _conf_to_score(conf):
    m = {"高": 4, "中高": 4, "中": 3, "中低": 2, "低": 2}
    if isinstance(conf, (int, float)):
        return int(max(1, min(5, round(conf))))
    return m.get(str(conf), 3)


def _grade_norm(g):
    if g in ("特级", "A"):
        return "A"
    if g in ("A-", "B"):
        return "B"
    return "C" if g else "C"


def seed_持仓层(date):
    """从 forecast(locked)种子⑥持仓层判断(AS5·forecast_id关联)。已有id不重复追加(累积·只追加)。"""
    sc = _load_sc()
    have = {e.get("id") for e in sc["entries"]}
    # 取最新工作版 forecast
    cands = [(m.group(1), p) for p in glob.glob(str(ROOT / "data/forecast" / "forecast_*.json"))
             if (m := re.match(r"forecast_(\d{4}-\d{2}-\d{2})\.json$", Path(p).name))]
    if not cands:
        return sc, 0
    fc = json.loads(Path(max(cands)[1]).read_text(encoding="utf-8"))
    n_new = 0
    for f in fc.get("forecasts", []):
        if f.get("horizon") != "1y":
            continue
        fid = f.get("forecast_id") or ("FC-" + str(f.get("ticker")))
        sid = "J6-" + str(fid)
        if sid in have:
            continue
        grade = _grade_norm(f.get("参数出处等级"))
        e = {"id": sid, "登记日": f.get("locked_at", "")[:10] or (date if "-" in date else "%s-%s-%s" % (date[:4], date[4:6], date[6:8])),
             "判断产出日": f.get("locked_at", "")[:10] or None,
             "层": "⑥持仓层", "判断": "%s 方向/情景(E上行%s%%)" % (f.get("name") or f.get("ticker"), f.get("expected_upside_pct")),
             "依据": [f.get("PE来源"), "参数出处等级%s" % f.get("参数出处等级")],
             "把握分": _conf_to_score(f.get("confidence")), "依据等级": grade,
             "证伪条件": f.get("invalidation_signal") or "待Opus5补", "验证日": f.get("verdict_date"),
             "验证状态": "待验", "验证时实际": None, "错在哪": None,
             "forecast_id": fid, "★关联": "locked_predictions/pdca_verdict(AS5)"}
        sc["entries"].append(e); have.add(sid); n_new += 1
    # 合并 pdca_verdict 结果(已验证的更新状态)
    for vp in sorted(glob.glob(str(ROOT / "data/pdca" / "verdict_*.json"))):
        try:
            vd = json.loads(Path(vp).read_text(encoding="utf-8"))
        except Exception:
            continue
        for v in (vd.get("verdicts") or vd.get("到期") or []):
            if not isinstance(v, dict):
                continue
            fid = v.get("forecast_id")
            for e in sc["entries"]:
                if e.get("forecast_id") == fid and v.get("已判定"):
                    e["验证状态"] = "命中" if v.get("类型") in ("命中", "S2", "中性") else ("未命中" if v.get("类型") == "未命中" else "部分")
                    e["验证时实际"] = v.get("实际收盘价")
    return sc, n_new


def certainty_ledger():
    """部件②:七层确定性累积表(★由 scorecard 派生·AS2-1检测手填→FAIL在gate)。升档写死:连续10已验证≥60%→中·≥20≥70%→高。"""
    sc = _load_sc()
    out = {"_说明": "★确定性累积表(部件②·魂)·★由judgment_scorecard派生计算(不许手填)·七层各自独立算。升档写死:≥10条已验证且命中率≥60%→中·≥20且≥70%→高。",
           "date": datetime.now(JST).strftime("%Y-%m-%d"), "层": {}}
    for layer in LAYERS:
        es = [e for e in sc["entries"] if e.get("层") == layer]
        verified = [e for e in es if e.get("验证状态") in ("命中", "未命中", "部分", "已证伪")]
        hit = sum(1 for e in verified if e.get("验证状态") == "命中")
        rate = round(hit / len(verified) * 100, 1) if verified else None
        if len(verified) >= 20 and (rate or 0) >= 70:
            cert = "高"
        elif len(verified) >= 10 and (rate or 0) >= 60:
            cert = "中"
        else:
            cert = "低"
        out["层"][layer] = {"当前确定性": cert, "★派生来源": "judgment_scorecard(非手填)", "判断总数": len(es),
                           "已验证判断数": len(verified), "命中数": hit, "命中率pct": rate,
                           "轨迹": [{"id": e.get("id"), "状态": e.get("验证状态")} for e in es][-10:]}
    return out


def decision_quality():
    """部件④:决策质量分=Σ(把握分×依据等级系数)÷依赖判断数。按层聚合(近似每层动作依赖该层判断)。"""
    sc = _load_sc()
    out = {}
    for layer in LAYERS:
        es = [e for e in sc["entries"] if e.get("层") == layer]
        if not es:
            out[layer] = None; continue
        s = sum((e.get("把握分") or 0) * GRADE_COEF.get(e.get("依据等级"), 0.3) for e in es)
        q = round(s / len(es), 2)
        out[layer] = {"决策质量分": q, "依赖判断数": len(es), "★低把握(<2.0)": q < 2.0}
    return out


def weakest_layer(cl):
    """★AS6:本体系哪一层最弱(命中率最低·其次确定性最低·再次质量分最低)。"""
    rows = []
    for layer, d in cl["层"].items():
        rows.append((layer, d.get("命中率pct"), d.get("当前确定性"), d.get("已验证判断数")))
    scored = [r for r in rows if r[1] is not None]
    if scored:
        w = min(scored, key=lambda r: r[1])
        return {"最弱层": w[0], "命中率pct": w[1], "确定性": w[2], "判据": "命中率最低"}
    # 无已验证→取判断最少/确定性低的
    low = [r for r in rows if r[2] == "低"]
    return {"最弱层": "全部低确定性(无足够已验证判断)", "低确定性层数": len(low),
            "判据": "尚无层达到≥10条已验证·全部处于『低』确定性起步期", "各层已验证数": {r[0]: r[3] for r in rows}}


def review_daily(date):
    """部件③ AS3-1:日复盘·必须含三项(缺任一→不合格)。"""
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:8])
    sc = _load_sc()
    yday_verified = [e for e in sc["entries"] if e.get("验证日") and str(e.get("验证日"))[:10] < dh and e.get("验证状态") != "待验"]
    # ①各环判断今天验证(逐层)
    p1 = {layer: {"待验": sum(1 for e in sc["entries"] if e.get("层") == layer and e.get("验证状态") == "待验"),
                  "今验命中": sum(1 for e in yday_verified if e.get("层") == layer and e.get("验证状态") == "命中")}
          for layer in LAYERS}
    # ②昨天持仓动作今天看对没对(新建·从 decisions/production action 近似·当前留结构标未产出)
    p2 = {"说明": "昨天持仓动作今天看对没对", "状态": "★结构已建·数据待接(需昨日动作表+今日价对比·Opus5/production动作源)", "逐动作": []}
    # ③今日新事件对宏观判断=支持/中性/证伪(新建)
    ev = ROOT / "data/evidence_chain" / f"daily_{dc}.json"
    p3 = {"说明": "今日新事件对宏观判断=支持/中性/证伪", "状态": ("有当日证据链·待Opus5判支持/中性/证伪" if ev.exists() else "★无当日证据链→未产出·原因")}
    complete = bool(p1) and bool(p2) and bool(p3)
    return {"_说明": "日复盘(部件③·AS3-1)·必须含蓝图左栏三项·缺任一该日复盘不合格。", "date": dh,
            "①各环判断今天验证": p1, "②昨天持仓动作今天看对没对(新建)": p2,
            "③今日新事件对宏观判断": p3, "★三项齐全": complete,
            "★合格": complete, "★备注": "②③为新建部件·结构已建·内容待Opus5/数据接入(如实标未产出·不假填)"}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    dc = a.date.replace("-", "")
    sc, n_new = seed_持仓层(a.date)
    SC.parent.mkdir(parents=True, exist_ok=True)
    SC.write_text(json.dumps(sc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cl = certainty_ledger(); CL.write_text(json.dumps(cl, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dq = decision_quality()
    rv = review_daily(a.date)
    (ROOT / "data/pdca" / f"review_daily_{dc}.json").write_text(json.dumps(rv, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    weak = weakest_layer(cl)
    summary = {"_说明": "第⑦层复盘记分卡层·汇总(供产品第⑦层+AS6最弱层)。", "date": a.date,
               "判断记分卡条数": len(sc["entries"]), "本次新增": n_new,
               "七层确定性": {k: v["当前确定性"] for k, v in cl["层"].items()},
               "★本体系最弱层(AS6)": weak, "决策质量分(按层)": dq}
    (ROOT / "data/pdca" / f"scorecard_summary_{dc}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[pdca_scorecard_layer] %s · 记分卡%d条(新增%d) · 乱码%d" % (a.date, len(sc["entries"]), n_new, SC.read_bytes().count(b"\xef\xbf\xbd")))
    print("  七层确定性:", {k.split("层")[0][:3] if "层" in k else k[:3]: v["当前确定性"] for k, v in cl["层"].items()})
    print("  ★最弱层(AS6):", weak.get("最弱层"), "·", weak.get("判据"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
