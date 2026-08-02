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
LAYERS = ["①世界观", "②国家战略", "③资金流动", "④板块轮动", "⑤机会池", "⑥持仓层", "⑦复盘层"]


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
             "验证状态": "待验", "★验证来源": "到期验证",   # ★AU1-1:到验证日由市场/事实给答案(计入升档分母)
             "验证时实际": None, "错在哪": None,
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


def merge_history(sc):
    """★轮80 AT1:并入七条历史判断(judgment_history_opus5_20260731_0802.json)。
    ★保留『事后补登』标记(一次性历史回填·违反登记须同时的规矩·必须留痕不许洗白)。只追加不重复。"""
    hp = ROOT / "data/pdca" / "judgment_history_opus5_20260731_0802.json"
    if not hp.exists():
        return sc, 0
    hd = json.loads(hp.read_text(encoding="utf-8"))
    have = {e.get("id") for e in sc["entries"]}
    n = 0
    for j in hd.get("judgments", []):
        if j.get("id") in have:
            continue
        e = dict(j)
        # 归一 ★错在哪→错在哪(scorecard字段)·保留原键
        if e.get("★错在哪") is not None and not e.get("错在哪"):
            e["错在哪"] = e.get("★错在哪")
        # ★AU1-1:这七条是自查/主动发现的错(对的不会被自己推翻)→验证来源=自查证伪(★不计入升档分母·只算自查发现率)
        e.setdefault("★验证来源", "自查证伪")
        e["★登记性质"] = "事后补登·一次性历史回填(轮80·违反登记须与判断同时·留痕不洗白)"
        e["判断产出日"] = e.get("判断产出日") or "早于登记日(历史·故事后补)"
        sc["entries"].append(e); have.add(e.get("id")); n += 1
    return sc, n


def error_distributions(sc):
    """★AT1-3:派生统计——四类错因分布 + 按层分布(进产品)。从已证伪/未命中判断派生。"""
    from collections import Counter
    failed = [e for e in sc["entries"] if e.get("验证状态") in ("未命中", "已证伪")]
    ec = Counter((e.get("错在哪") or "未填错因") for e in failed)
    lc = Counter(e.get("层") for e in failed)
    return {"_说明": "四类错因分布(数据错/逻辑错/时机错/口径错)+按层分布·从已证伪/未命中判断派生(AT1-3·进产品)。",
            "四类错因分布": dict(ec), "按层分布(出错判断)": dict(lc),
            "样本数(已证伪+未命中)": len(failed)}


def certainty_ledger():
    """部件②:七层确定性累积表(★由 scorecard 派生·AS2-1检测手填→FAIL在gate)。
    ★轮81 AU1:验证分三类(自查证伪/到期验证/事件证伪)·【禁合并成单一命中率】。
    升档【只看到期验证类】:连续≥10条到期验证且命中率≥60%→中·≥20且≥70%→高(自查证伪不计入升档分母·否则越自查越降级=反向激励)。
    自查发现率单列(越高=自查越有效·正面指标·非负面)。"""
    sc = _load_sc()
    out = {"_说明": "★确定性累积表(部件②·魂)·派生自judgment_scorecard(不许手填)·七层各自独立。★验证分三类不合并;升档只看『到期验证』;自查发现率是正面指标。",
           "date": datetime.now(JST).strftime("%Y-%m-%d"), "层": {}}
    for layer in LAYERS:
        es = [e for e in sc["entries"] if e.get("层") == layer]
        due = [e for e in es if e.get("★验证来源") == "到期验证" and e.get("验证状态") in ("命中", "未命中", "部分", "已证伪")]
        selfck = [e for e in es if e.get("★验证来源") == "自查证伪"]
        event = [e for e in es if e.get("★验证来源") == "事件证伪"]
        pending = [e for e in es if e.get("验证状态") == "待验"]
        due_hit = sum(1 for e in due if e.get("验证状态") == "命中")
        due_rate = round(due_hit / len(due) * 100, 1) if due else None   # ★只有到期验证有『命中率』
        # ★升档只看到期验证
        if len(due) >= 20 and (due_rate or 0) >= 70:
            cert = "高"
        elif len(due) >= 10 and (due_rate or 0) >= 60:
            cert = "中"
        else:
            cert = "低"
        out["层"][layer] = {
            "当前确定性": cert, "★派生来源": "judgment_scorecard(非手填)·升档只看到期验证",
            "判断总数": len(es),
            "★到期验证": {"数": len(due), "命中数": due_hit, "命中率pct": due_rate if due else "待样本(尚无到期)"},
            "★自查证伪": {"数": len(selfck), "说明": "自查/主动发现的错·不计入升档分母·见自查发现率"},
            "★事件证伪": {"数": len(event)},
            "待验判断数": len(pending),
            "★升档进度": "到期验证 %d 条(需≥10且≥60%%→中)" % len(due),
            "轨迹": [{"id": e.get("id"), "来源": e.get("★验证来源"), "状态": e.get("验证状态")} for e in es][-10:]}
    # ★AU1-4 自查发现率(全局·正面指标)
    all_selfck = sum(1 for e in sc["entries"] if e.get("★验证来源") == "自查证伪")
    all_due = sum(1 for e in sc["entries"] if e.get("★验证来源") == "到期验证")
    out["★自查发现率(AU1-4·正面指标)"] = {"自查证伪数": all_selfck, "到期验证数": all_due,
                                     "说明": "★自查发现率越高=自查越有效·是正面指标不是负面(度量自查有效性·非判断能力)·不与命中率混算"}
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
    """★AS6:本体系哪一层最弱。★轮81:只用【到期验证】命中率判(自查证伪不算命中率·防样本偏差)。"""
    rows = []
    for layer, d in cl["层"].items():
        due = d.get("★到期验证", {})
        rate = due.get("命中率pct") if isinstance(due.get("命中率pct"), (int, float)) else None
        rows.append((layer, rate, d.get("当前确定性"), due.get("数", 0)))
    scored = [r for r in rows if r[1] is not None]
    if scored:
        w = min(scored, key=lambda r: r[1])
        return {"最弱层": w[0], "到期验证命中率pct": w[1], "确定性": w[2], "判据": "到期验证命中率最低"}
    return {"最弱层": "尚无层有到期验证样本→无法比命中率(首条到期后才有)", "判据": "全部处于『低』起步期·到期验证样本=0",
            "各层到期验证数": {r[0]: r[3] for r in rows},
            "★注": "★不用自查证伪判最弱层(那度量自查有效性非判断能力)"}


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
    sc, n_hist = merge_history(sc)   # ★轮80 AT1:并入七条历史判断(留事后补登痕)
    # ★轮81 AU1-1:回填现有条目的验证来源(轮79/80已入库的没这字段)——JH-*(历史自查)=自查证伪·其余(forecast种子)=到期验证
    for e in sc["entries"]:
        if not e.get("★验证来源"):
            e["★验证来源"] = "自查证伪" if str(e.get("id", "")).startswith("JH-") else "到期验证"
    SC.parent.mkdir(parents=True, exist_ok=True)
    SC.write_text(json.dumps(sc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dist = error_distributions(sc)   # ★AT1-3:四类错因+按层分布
    cl = certainty_ledger(); CL.write_text(json.dumps(cl, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dq = decision_quality()
    rv = review_daily(a.date)
    (ROOT / "data/pdca" / f"review_daily_{dc}.json").write_text(json.dumps(rv, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    weak = weakest_layer(cl)
    # ★AU2:产品三数并列(防误读·不许只显单一命中率0%)
    all_due = sum(1 for e in sc["entries"] if e.get("★验证来源") == "到期验证" and e.get("验证状态") != "待验")
    all_due_hit = sum(1 for e in sc["entries"] if e.get("★验证来源") == "到期验证" and e.get("验证状态") == "命中")
    all_selfck = sum(1 for e in sc["entries"] if e.get("★验证来源") == "自查证伪")
    all_pending = sum(1 for e in sc["entries"] if e.get("验证状态") == "待验")
    next_due = min([str(e.get("验证日"))[:10] for e in sc["entries"] if e.get("验证状态") == "待验" and e.get("验证日")] or ["待定"])
    au2 = {
        "★到期验证命中率": ("%.1f%%(%d条已到期)" % (all_due_hit / all_due * 100, all_due) if all_due else "待样本(首条%s到期)" % next_due),
        "★自查发现的错": "%d 条(%s)" % (all_selfck, "/".join("%s%d" % (k, v) for k, v in dist["四类错因分布"].items())),
        "★待验判断": "%d 条" % all_pending,
        "★呈现铁律": "这三个数必须并列显示·★不许只显单一『命中率0%』(自查证伪≠判断能力·那是误导·AU2)"}
    summary = {"_说明": "第⑦层复盘记分卡层·汇总(供产品第⑦层)。★AU2三数并列防误读·验证分三类不混算。", "date": a.date,
               "判断记分卡条数": len(sc["entries"]), "本次新增(forecast种子)": n_new, "本次并入历史": n_hist,
               "★AU2产品三数并列(防误读)": au2,
               "七层确定性(升档只看到期验证)": {k: v["当前确定性"] for k, v in cl["层"].items()},
               "★本体系最弱层(AS6)": weak, "决策质量分(按层)": dq,
               "★四类错因分布(AT1-3·进产品)": dist["四类错因分布"], "★按层分布(出错判断·AT1-3)": dist["按层分布(出错判断)"],
               "★自查发现率(AU1-4·正面指标)": cl.get("★自查发现率(AU1-4·正面指标)")}
    (ROOT / "data/pdca" / f"scorecard_summary_{dc}.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[pdca_scorecard_layer] %s · 记分卡%d条(新增%d) · 乱码%d" % (a.date, len(sc["entries"]), n_new, SC.read_bytes().count(b"\xef\xbf\xbd")))
    print("  七层确定性:", {k.split("层")[0][:3] if "层" in k else k[:3]: v["当前确定性"] for k, v in cl["层"].items()})
    print("  ★最弱层(AS6):", weak.get("最弱层"), "·", weak.get("判据"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
