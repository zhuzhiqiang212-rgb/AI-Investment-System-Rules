# -*- coding: utf-8 -*-
"""★轮148 E10(阶段E最后一项/看板G21要素四):【大闭环套小闭环】——四个不同周期的闭环 + ★周期纪律硬闸。
四闭环:
  【小·执行闭环】⑥判断→⑦动作→结果→回⑥      周期 日/周   rank 1
  【中·板块闭环】③资金流→④板块→板块表现→回③  周期 周/月   rank 2
  【中·候选闭环】④激活→⑤候选→候选表现→回④    周期 月/季   rank 3
  【大·格局闭环】①世界观→全链→累计结果→回①    周期 季/年   rank 4
★A-3 核心纪律(硬闸):某闭环的判断【只能被同周期或更长周期(rank≥)的证据推翻·不能被更短周期(rank<)的推翻】。
   · 反例:把『一天走势(rank1)』当趋势去推翻『长期估值判断(rank4)』→ 1<4 → FAIL(短推长·禁)。
   · ★反向同样禁:因为一天涨了(rank1)就推翻长期估值(rank4)→ 同样 1<4 → FAIL。
★A-4 到期检测:各闭环到周期末→提醒『该复盘本闭环』→接进今日提醒清单。
★Code 只搭闭环机制+周期比较硬闸·不做投资判断(G2)。周期rank是结构化数值·判定不靠文本(§5.4)。"""
import sys, json, argparse
from datetime import date as _date
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "data/pdca/closed_loops_state.json"

# ★四闭环定义(结构化·rank=周期长短序·数值可比较)
LOOPS = {
    "执行闭环": {"名": "小·执行闭环", "链": "⑥判断→⑦动作→结果→回⑥", "周期": "日/周", "rank": 1, "period_days": 7,  "源层": ["⑥", "⑦"]},
    "板块闭环": {"名": "中·板块闭环", "链": "③资金流→④板块→板块表现→回③", "周期": "周/月", "rank": 2, "period_days": 30, "源层": ["③", "④"]},
    "候选闭环": {"名": "中·候选闭环", "链": "④激活→⑤候选→候选表现→回④", "周期": "月/季", "rank": 3, "period_days": 90, "源层": ["④", "⑤"]},
    "格局闭环": {"名": "大·格局闭环", "链": "①世界观→全链→累计结果→回①", "周期": "季/年", "rank": 4, "period_days": 180, "源层": ["①", "②①", "②"]},
}
# ★层→闭环映射(B-1:E9逆向归因喂给对应闭环)
LAYER_TO_LOOP = {"⑦": "执行闭环", "⑥": "执行闭环", "⑤": "候选闭环", "④": "板块闭环", "③": "板块闭环",
                 "②": "格局闭环", "①": "格局闭环", "②①": "格局闭环"}


def _rj(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def _today(dc):
    return _date(int(dc[:4]), int(dc[4:6]), int(dc[6:8]))


def loop_of_layer(layer):
    """B-1:某层归属哪个闭环。"""
    return LAYER_TO_LOOP.get(layer)


def overturn_gate(judgment_loop, evidence_loop):
    """★★A-3 核心硬闸:judgment_loop 的判断能否被 evidence_loop 的证据推翻。
    规则:evidence.rank >= judgment.rank → 允许(同周期或更长);evidence.rank < judgment.rank → FAIL(短推长·禁)。
    ★判定靠结构化数值 rank·非文本(§5.4)。"""
    jr = LOOPS.get(judgment_loop, {}).get("rank")
    er = LOOPS.get(evidence_loop, {}).get("rank")
    if jr is None or er is None:
        return {"结果": "无法判定", "原因": "闭环名未知", "judgment_loop": judgment_loop, "evidence_loop": evidence_loop}
    ok = er >= jr
    return {
        "结果": "PASS(允许推翻)" if ok else "★FAIL(短周期证据不许推翻长周期判断)",
        "judgment_loop": judgment_loop, "judgment_rank": jr,
        "evidence_loop": evidence_loop, "evidence_rank": er,
        "判据": "evidence_rank(%d) %s judgment_rank(%d)" % (er, ">=" if ok else "<", jr),
        "允许推翻": ok,
    }


# ★A-3 测试案例(数据来自董事长指出的今日犯错·Code只跑周期比较不编投资判断)
GATE_TESTS = [
    {"名": "爱德万:把一天走势当趋势外推去推翻长期估值",
     "judgment_loop": "格局闭环", "judgment_desc": "长期估值/格局判断(rank4)",
     "evidence_loop": "执行闭环", "evidence_desc": "一天走势(rank1·日频)",
     "应为": False, "对应董事长": "★短周期证据不许推翻长周期判断"},
    {"名": "微软:一天走势外推",
     "judgment_loop": "格局闭环", "judgment_desc": "长期格局判断(rank4)",
     "evidence_loop": "执行闭环", "evidence_desc": "一天走势(rank1)",
     "应为": False, "对应董事长": "★同上·短推长禁"},
    {"名": "★反向:因为一天涨了就推翻长期估值判断",
     "judgment_loop": "格局闭环", "judgment_desc": "长期估值判断(rank4)",
     "evidence_loop": "执行闭环", "evidence_desc": "一天涨(rank1)",
     "应为": False, "对应董事长": "★反向同样禁"},
    {"名": "对照:季度基本面(同为长周期)修正长期估值",
     "judgment_loop": "格局闭环", "judgment_desc": "长期估值判断(rank4)",
     "evidence_loop": "候选闭环", "evidence_desc": "月/季证据(rank3)",
     "应为": False, "对应董事长": "rank3<rank4·仍不足(需同或更长)"},
    {"名": "对照:同周期证据修正执行判断(允许)",
     "judgment_loop": "执行闭环", "judgment_desc": "⑥执行判断(rank1)",
     "evidence_loop": "执行闭环", "evidence_desc": "日/周结果(rank1)",
     "应为": True, "对应董事长": "同周期·允许"},
    {"名": "对照:长周期格局证据修正执行判断(允许)",
     "judgment_loop": "执行闭环", "judgment_desc": "⑥执行判断(rank1)",
     "evidence_loop": "格局闭环", "evidence_desc": "格局级证据(rank4)",
     "应为": True, "对应董事长": "更长周期·允许(rank4>=rank1)"},
]


def run_gate_tests():
    rows = []
    all_ok = True
    for t in GATE_TESTS:
        g = overturn_gate(t["judgment_loop"], t["evidence_loop"])
        correct = (g["允许推翻"] == t["应为"])
        all_ok = all_ok and correct
        rows.append({**t, "★闸判": g["结果"], "判据": g["判据"], "★与预期一致": correct})
    return {"全部正确": all_ok, "用例": rows}


def expiry_check(dc):
    """★A-4:各闭环到周期末→提醒复盘。读 state(各闭环上次复盘日)·距今≥period_days→到期。"""
    st = _rj(STATE, {})
    loops_state = st.get("loops", {}) if isinstance(st, dict) else {}
    today = _today(dc)
    due, near = [], []
    for lid, meta in LOOPS.items():
        last = loops_state.get(lid, {}).get("上次复盘日")
        pd = meta["period_days"]
        if not last:
            due.append({"闭环": meta["名"], "周期": meta["周期"], "上次复盘": None,
                        "★状态": "从未复盘·建议建立首次复盘基线", "distance": None})
            continue
        try:
            ld = _date(int(last[:4]), int(last[5:7]), int(last[8:10]))
            days = (today - ld).days
        except Exception:
            days = None
        if days is None:
            continue
        remain = pd - days
        row = {"闭环": meta["名"], "周期": meta["周期"], "上次复盘": last, "已过天数": days, "周期天数": pd, "距到期": remain}
        if days >= pd:
            due.append({**row, "★状态": "★到期·该复盘本闭环"})
        elif remain <= max(2, pd // 10):
            near.append({**row, "★状态": "临近到期(≤%d天)" % max(2, pd // 10)})
    return {"到期": due, "临近": near}


def wire_sources(dc):
    """把已有机制并入四闭环体系(B-1/B-2/B-3)——★只归类·不改原数据。"""
    wired = {}
    # B-1:E9逆向归因→对应闭环
    att = _rj(ROOT / "data/pdca" / f"backward_attribution_{dc}.json", {})
    e9 = []
    for name, r in (att.get("★两案例归因", {}) or {}).items():
        layer = (r.get("★机制归因", {}) or {}).get("★错在哪层")
        e9.append({"案例": name, "错层": layer, "★归入闭环": loop_of_layer(layer), "维度": (r.get("★机制归因", {}) or {}).get("★维度")})
    wired["B1_E9归因归入闭环"] = e9
    # B-2:forecast见分晓→按核对日周期归入闭环
    reg = _rj(ROOT / "data/pdca/locked_predictions_registry.json", {})
    preds = reg.get("已登记预测") or reg.get("predictions") or reg.get("entries") or (reg if isinstance(reg, list) else [])
    b2 = []
    for p in (preds if isinstance(preds, list) else []):
        if not isinstance(p, dict):
            continue
        due = p.get("PDCA核对日") or p.get("见分晓") or p.get("核对日")
        horizon = str(p.get("尺度") or p.get("时间尺度") or p.get("horizon") or "")
        # 短→执行闭环·长→格局闭环(按尺度文本粗归·★仅归类不判投资G2)
        loop = "格局闭环" if ("长" in horizon or "long" in horizon.lower()) else "执行闭环"
        b2.append({"标的": p.get("标的") or p.get("code"), "尺度": horizon, "核对日": due, "★归入闭环": loop})
    wired["B2_见分晓预测归入闭环"] = b2[:50]
    wired["B2_预测数"] = len(b2)
    wired["B2_按闭环计数"] = {"执行闭环": sum(1 for x in b2 if x["★归入闭环"] == "执行闭环"),
                        "格局闭环": sum(1 for x in b2 if x["★归入闭环"] == "格局闭环")}
    # B-3:候选池重跑触发(G22四条)→候选闭环
    cp = _rj(ROOT / "data/opportunity/candidate_pool.json", {})
    trg = cp.get("★重跑触发(4条·G22)") or cp.get("★重跑触发(G22四条)") or cp.get("重跑触发") or {}
    wired["B3_候选池触发归入闭环"] = {"★归入闭环": "候选闭环", "触发状态": trg}
    return wired


def build(dc):
    gate = run_gate_tests()
    expiry = expiry_check(dc)
    wired = wire_sources(dc)
    out = {
        "_说明": "★轮148 E10 大闭环套小闭环。四闭环(执行/板块/候选/格局·各自周期)+★A-3周期纪律硬闸(短周期证据不许推翻长周期判断·反向亦禁)。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "★四闭环": {k: {"名": v["名"], "链": v["链"], "周期": v["周期"], "rank": v["rank"], "复盘周期天": v["period_days"]} for k, v in LOOPS.items()},
        "★A3周期纪律硬闸": {"规则": "evidence_rank >= judgment_rank 才允许推翻·否则FAIL(短推长禁·反向同禁)", **gate},
        "★A4到期检测(接今日提醒清单)": expiry,
        "★B接合已有机制": wired,
    }
    (ROOT / "data/pdca" / f"closed_loops_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def alerts_rows(dc):
    """★A-4:供 daily_alerts / render 调用——返回闭环到期提醒行(接今日提醒清单)。"""
    ex = expiry_check(dc)
    return ex["到期"] + ex["临近"]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    g = o["★A3周期纪律硬闸"]
    print("[E10 四闭环]", " | ".join("%s(rank%d·%s)" % (v["名"], v["rank"], v["周期"]) for v in o["★四闭环"].values()))
    print("[A-3 周期纪律硬闸] 全部用例正确:", g["全部正确"])
    for r in g["用例"]:
        print("  %s → %s [%s] 与预期一致=%s" % (r["名"][:28], r["★闸判"], r["判据"], r["★与预期一致"]))
    ex = o["★A4到期检测(接今日提醒清单)"]
    print("[A-4 到期检测] 到期%d · 临近%d" % (len(ex["到期"]), len(ex["临近"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
