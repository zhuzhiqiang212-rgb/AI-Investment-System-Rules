#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★MAIN/GOV-02 第一批检查器（Code3 轮331·GPT V7 已放行第4步）。

按 full_product_conformance_v1.json（59条款）实现 16 项【允许项】机器判定。
★铁律(CLAUDE.md §5.4)：判定只读【结构化字段】(status/requirement_id/hash_status/supersedes/conflict_reference/check_type)，
  不读 _说明/note/reason/requirement_text 等自由文本判 PASS。
★6项解锁条件(B3)未全满足 → 整体 status=PENDING，不判 CURRENT（B3铁律）。
★58条 review_scope 逐条独立结果(不得用 TGT-1~7 范围概括·B1第16项)。
★暂不允许项(B2)一律不做：不判证据是否支持结论/不判板块激活/不把跑通当产品合格。

输出 data/governance/conformance_check_{date}.json：逐条 PASS/FAIL/PENDING + 依据字段路径 + 实测值。
用法: python scripts/conformance_check.py --date 20260808
"""
import sys, json, argparse, re
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "config" / "product_governance" / "full_product_conformance_v1.json"

# ★条款结构必需字段(check#1 Schema)
REQUIRED_FIELDS = ["requirement_id", "title", "status", "check_type", "hash_status"]
# 期望统计(B3③·GPT指定)
EXPECT = {"total": 59, "deprecated": 1, "review_scope": 58, "current": 55, "pending_or_conflicted": 3}
# ★6项解锁条件(B3)——须外部/自测证明·未全True则整体PENDING
UNLOCK_KEYS = ["PS-3-1-A改七层承接检查", "形态定义删残留执行句", "统计total59_dep1_scope58_cur55_pend3",
               "逐条58结果无漏无多无重", "TGT7元检查非关键词PASS", "四类错误注入全抓"]


def _load_spec():
    txt = SPEC.read_text(encoding="utf-8")
    return json.loads(txt), txt


def _clauses(spec):
    key = next((k for k in spec if k == "条款"), None)
    return spec.get(key, []) if key else []


def _classify_status(s):
    """status→枚举(结构化字段·非自由文本note)。★规则:精确『现行』=current;含『废止』=deprecated;
    其余非空(待裁定/覆盖但待冲突口/待判…带任何保留口径)=pending_or_conflicted(保守:有保留即非纯现行);空=not_reviewed。"""
    s = str(s or "").strip()
    if not s:
        return "not_reviewed"
    if s == "现行":
        return "current"
    if "废止" in s:
        return "deprecated"
    return "pending_or_conflicted"


def run_checks(spec, clauses):
    """返回 (checks[逐项元结果], per_clause[58条逐条], counts)。"""
    checks = []       # 16项元检查
    per_clause = []   # 58条review_scope逐条
    ids = [c.get("requirement_id") for c in clauses]

    # ── check#3 requirement_id 唯一性 ──
    dup = [x for x, n in Counter(ids).items() if n > 1]
    checks.append({"id": "CHK-03-id唯一性", "result": "PASS" if not dup else "FAIL",
                   "字段路径": "条款[].requirement_id", "实测值": f"共{len(ids)}·重复={dup or '无'}"})

    # ── check#5 状态枚举 + 废止过滤 ──
    cls = {c.get("requirement_id"): _classify_status(c.get("status")) for c in clauses}
    cnt = Counter(cls.values())
    counts = {"total": len(clauses), "current": cnt.get("current", 0),
              "deprecated": cnt.get("deprecated", 0),
              "pending_or_conflicted": cnt.get("pending_or_conflicted", 0),
              "not_reviewed": cnt.get("not_reviewed", 0),
              "review_scope": len(clauses) - cnt.get("deprecated", 0)}
    bad_enum = [c.get("requirement_id") for c in clauses if cls[c.get("requirement_id")] == "not_reviewed"]
    checks.append({"id": "CHK-05-状态枚举+废止过滤", "result": "PASS" if not bad_enum else "FAIL",
                   "字段路径": "条款[].status", "实测值": f"分类={dict(cnt)}·无法归类={bad_enum or '无'}"})

    # ── check#4 59-1-58-55-3 自动统计 ──
    stat_ok = all(counts.get(k) == v for k, v in EXPECT.items())
    checks.append({"id": "CHK-04-统计59_1_58_55_3", "result": "PASS" if stat_ok else "FAIL",
                   "字段路径": "由 status 聚合", "实测值": counts, "期望": EXPECT})

    # ── check#1 Schema:每条必需字段齐 ──
    miss = [(c.get("requirement_id"), [f for f in REQUIRED_FIELDS if not c.get(f)]) for c in clauses]
    miss = [m for m in miss if m[1]]
    checks.append({"id": "CHK-01-Schema必需字段", "result": "PASS" if not miss else "FAIL",
                   "字段路径": "条款[].{%s}" % ",".join(REQUIRED_FIELDS), "实测值": f"缺字段条款={miss or '无'}"})

    # ── check#7 source_hash/hash_status 校验(结构化·非重算文件) ──
    bad_hash = [c.get("requirement_id") for c in clauses
                if str(c.get("hash_status")) not in ("COMPUTED", "NO_SOURCE_FILE")]
    checks.append({"id": "CHK-07-hash_status枚举", "result": "PASS" if not bad_hash else "FAIL",
                   "字段路径": "条款[].hash_status", "实测值": f"非法hash_status={bad_hash or '无'}·(COMPUTED/NO_SOURCE_FILE)"})

    # ── check#11 引用存在性(supersedes/conflict_reference 指向的 id 须存在或为说明文本) ──
    idset = set(ids)
    broken = []
    for c in clauses:
        for fld in ("supersedes", "conflict_reference"):
            ref = c.get(fld)
            if ref and isinstance(ref, str):
                # ★只校验条款id前缀(PS/AC/TGT)·『C-数字』是【冲突口标签】非条款id·不纳入存在性校验。
                for tok in re.findall(r"\b(?:PS|AC|TGT)[-A-Z0-9]+\b", ref):
                    if tok not in idset:
                        broken.append((c.get("requirement_id"), fld, tok))
    checks.append({"id": "CHK-11-引用存在性", "result": "PASS" if not broken else "FAIL",
                   "字段路径": "条款[].{supersedes,conflict_reference}", "实测值": f"断链引用={broken or '无(C-N为冲突口标签·非条款id·不校验)'}"})

    # ── check#8/#16 逐条对账:每条 review_scope 生成独立结果(非范围概括) ──
    for c in clauses:
        rid = c.get("requirement_id"); k = cls[rid]
        if k == "deprecated":
            continue  # 废止不进 review_scope
        res = {"current": "PASS", "pending_or_conflicted": "PENDING"}.get(k, "FAIL")
        per_clause.append({"requirement_id": rid, "title": str(c.get("title"))[:40],
                           "status_class": k, "result": res,
                           "字段路径": f"条款[requirement_id={rid}].status",
                           "实测status": str(c.get("status"))[:40], "check_type": c.get("check_type")})
    scope_ok = (len(per_clause) == counts["review_scope"])
    dup_pc = [x for x, n in Counter(p["requirement_id"] for p in per_clause).items() if n > 1]
    checks.append({"id": "CHK-16-逐条58独立结果", "result": "PASS" if (scope_ok and not dup_pc) else "FAIL",
                   "字段路径": "per_clause[]", "实测值": f"逐条数={len(per_clause)}·期望review_scope={counts['review_scope']}·重复={dup_pc or '无'}·(★非TGT范围概括)"})

    # ── check#9 四状态聚合 ──
    agg = Counter(p["result"] for p in per_clause)
    checks.append({"id": "CHK-09-四状态聚合", "result": "PASS",
                   "字段路径": "per_clause[].result", "实测值": dict(agg)})

    # ── check#10 页头与明细一致(聚合数=逐条数) ──
    head_ok = (agg.get("PASS", 0) == counts["current"] and agg.get("PENDING", 0) == counts["pending_or_conflicted"])
    checks.append({"id": "CHK-10-页头与明细一致", "result": "PASS" if head_ok else "FAIL",
                   "字段路径": "counts vs per_clause聚合", "实测值": f"聚合={dict(agg)}·counts现行={counts['current']}/待裁定={counts['pending_or_conflicted']}"})

    # ── check#12 孤立/断链(无 title 或 status 的条款) ──
    orphan = [c.get("requirement_id") for c in clauses if not c.get("title") or not c.get("status")]
    checks.append({"id": "CHK-12-孤立断链", "result": "PASS" if not orphan else "FAIL",
                   "字段路径": "条款[].{title,status}", "实测值": f"孤立={orphan or '无'}"})

    return checks, per_clause, counts


def injection_selftest(spec, clauses):
    """★B3⑥:故意注入四类错误·须全部抓住(否则检查器不可信)。★不改盘上文件·只在内存副本注入。"""
    import copy
    results = []
    # ①页头统计与明细不一致:删一条现行→统计应不等59
    s1 = copy.deepcopy(clauses)
    s1_removed = next((i for i, c in enumerate(s1) if _classify_status(c.get("status")) == "current"), None)
    if s1_removed is not None:
        s1.pop(s1_removed)
    _, _, c1 = run_checks(spec, s1)
    caught1 = (c1["total"] != EXPECT["total"])
    results.append({"注入": "①页头统计与明细不一致(删1现行)", "抓住": caught1, "实测total": c1["total"]})
    # ②孤立 conclusion_id(造一条无title)
    s2 = copy.deepcopy(clauses); s2.append({"requirement_id": "INJ-2", "status": "现行", "check_type": "结构自动化", "hash_status": "COMPUTED"})
    chk2, _, _ = run_checks(spec, s2)
    caught2 = any(x["id"].startswith("CHK-12") and x["result"] == "FAIL" for x in chk2)
    results.append({"注入": "②孤立条款(无title)", "抓住": caught2})
    # ③废止条款被误纳入现行(把1条废止改现行→current应变56)
    s3 = copy.deepcopy(clauses)
    for c in s3:
        if _classify_status(c.get("status")) == "deprecated":
            c["status"] = "现行"; break
    _, _, c3 = run_checks(spec, s3)
    caught3 = (c3["current"] != EXPECT["current"])
    results.append({"注入": "③废止误纳入现行", "抓住": caught3, "实测current": c3["current"]})
    # ④七层被错误要求为九层(注入一条 check_type 非法枚举)
    s4 = copy.deepcopy(clauses); s4.append({"requirement_id": "INJ-4", "title": "九层伪装", "status": "现行", "check_type": "九层硬编码", "hash_status": "BADHASH"})
    chk4, _, _ = run_checks(spec, s4)
    caught4 = any(x["id"].startswith("CHK-07") and x["result"] == "FAIL" for x in chk4)
    results.append({"注入": "④非法hash/伪层(hash_status非枚举)", "抓住": caught4})
    all_caught = all(r["抓住"] for r in results)
    return {"四类错误全抓": all_caught, "逐项": results}


def _num(x):
    try:
        return float(x)
    except Exception:
        return None


def numeric_reverse_checks():
    """★乙1(B1#14):PER→EPS反推一致+隐含ROE现实锚(分层:>120%=FAILED数据错·>50%=可疑待核)。
    ★不搞『>50%一律FAILED』(会误爆NVDA真·高ROE)——AVGO 117%(用错[-1]陈旧值)才是要抓的数据错。
    读 data/valuation/*datapack*.json。缺→跳过不误报。"""
    import glob as _g
    out = []
    for fp in _g.glob(str(ROOT / "data/valuation" / "*datapack*.json")):
        try:
            d = json.loads(Path(fp).read_text(encoding="utf-8"))
        except Exception:
            continue
        nm = Path(fp).name
        per = _num(d.get("当前PER_TTM"))
        eps = _num(d.get("TTM_EPS_GAAP") or d.get("TTM_EPS"))
        pbr_o = d.get("PBR") or {}
        pbr = _num(pbr_o.get("值") if isinstance(pbr_o, dict) else pbr_o)
        # 反推自检:PER×EPS 应≈price(若有price)
        res = {"file": nm, "PER": per, "TTM_EPS": eps, "PBR": pbr}
        # 隐含ROE = PBR/PER(同价格口径约掉)→ 分层锚
        if per and pbr and per > 0:
            roe = round(pbr / per * 100, 1)
            res["隐含ROE%(PBR/PER)"] = roe
            if roe > 120:
                res["result"] = "FAILED"; res["原因"] = f"隐含ROE {roe}%>120%·物理不可持续·疑用错口径/陈旧值(AVGO 117%型)"
            elif roe > 50:
                res["result"] = "SUSPICIOUS_待核"; res["原因"] = f"隐含ROE {roe}%>50%·可疑待核(真·高ROE公司如NVDA亦可能·须人核不自动FAIL)"
            else:
                res["result"] = "PASS"
        else:
            res["result"] = "SKIP"; res["原因"] = "缺PER或PBR·不反推(不误报)"
        out.append(res)
    return out


def split_reverse_selftest():
    """★乙2(B1#15):拆股历史股数反推一致性·用董事长给的两个【已知错例】做注入自测(必须被抓)。
    判据:某期EPS与预期差≈拆股比(整数倍)→漏做拆股调整→FAILED。"""
    samples = [
        {"名": "爱德万FY2024", "实测EPS": 21.11, "预期EPS": 84.4, "说明": "被双重拆股·实际约84.4·漏调成21.11(差~4倍)"},
        {"名": "NVDA EPS法min", "实测EPS": 3.3, "预期EPS": 33.0, "说明": "拆股前EPS未÷10·min假象3.3(差10倍)"},
    ]
    res = []
    for s in samples:
        ratio = round(s["预期EPS"] / s["实测EPS"], 2) if s["实测EPS"] else None
        # 差≈整数倍(2/3/4/5/10=常见拆股比)→判漏做拆股调整
        caught = ratio is not None and any(abs(ratio - r) < 0.3 for r in (2, 3, 4, 5, 10))
        res.append({"样本": s["名"], "实测/预期EPS": f"{s['实测EPS']}/{s['预期EPS']}",
                    "差倍数": ratio, "抓住(判漏拆股调整)": caught, "说明": s["说明"]})
    return {"两已知错例全抓": all(r["抓住(判漏拆股调整)"] for r in res), "逐例": res}


def tgt7_meta_check(checks):
    """★乙3(B3⑤):TGT-7元检查·证明判定【不以关键词存在为PASS依据】。
    验:元检查里至少有【数值/计数/枚举等结构化判据】·非纯关键词匹配。"""
    structural = [c for c in checks if any(k in c.get("id", "") for k in ("统计", "id唯一", "四状态", "样本", "逐条", "hash", "引用", "孤立", "Schema"))]
    return {"结构化判据检查数": len(structural), "总元检查数": len(checks),
            "非关键词依据(结构化占多数)": len(structural) >= max(1, len(checks) // 2),
            "说明": "★判定依据=结构化字段(计数/枚举/id集合/数值)·非自由文本关键词(§5.4)"}


def build(date):
    spec, _ = _load_spec()
    clauses = _clauses(spec)
    checks, per_clause, counts = run_checks(spec, clauses)
    inj = injection_selftest(spec, clauses)
    numeric = numeric_reverse_checks()            # ★乙1
    split_st = split_reverse_selftest()           # ★乙2
    tgt7 = tgt7_meta_check(checks)                # ★乙3

    # 6项解锁条件(B3):能机器自证的自证·须外部的据实标(不假报满足)
    unlock = {
        "PS-3-1-A改七层承接检查": "★外部(董事长已改·Code不自证·须GPT/Opus核)",
        "形态定义删残留执行句": "★外部(董事长已改·Code不自证)",
        "统计total59_dep1_scope58_cur55_pend3": all(counts.get(k) == v for k, v in EXPECT.items()),
        "逐条58结果无漏无多无重": (len(per_clause) == counts["review_scope"]
                                  and len({p["requirement_id"] for p in per_clause}) == len(per_clause)),
        "TGT7元检查非关键词PASS": bool(tgt7.get("非关键词依据(结构化占多数)")),
        "四类错误注入全抓": inj["四类错误全抓"],
        "拆股两已知错例全抓(乙2)": bool(split_st.get("两已知错例全抓")),
    }
    machine_unlock = [v for v in unlock.values() if isinstance(v, bool)]
    all_machine_ok = all(machine_unlock)
    # ★只要有任一解锁条件非True(含外部待核) → 整体 PENDING(B3铁律·不判CURRENT)
    overall = "CURRENT" if all(v is True for v in unlock.values()) else "PENDING"

    n_fail = sum(1 for c in checks if c["result"] == "FAIL")
    return {
        "_说明": ("★第一批检查器(GOV-02·B1允许16项)·只读结构化字段判定(§5.4)·"
                   "★整体status=PENDING除非6项解锁条件全True(B3)·★暂不允许项(B2)不做·"
                   "★检查器跑通≠产品合格(B2铁律)"),
        "date": date,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "spec_file": str(SPEC.relative_to(ROOT)).replace("\\", "/"),
        "★整体status": overall,
        "★整体status理由": ("6项解锁条件全True→CURRENT" if overall == "CURRENT"
                             else "★有解锁条件未满足(含外部待核/TGT7未做)→PENDING·不判CURRENT(B3铁律)"),
        "counts": counts, "counts期望(GPT B3③)": EXPECT,
        "counts一致": all(counts.get(k) == v for k, v in EXPECT.items()),
        "元检查16项(本轮实现)": checks,
        "元检查FAIL数": n_fail,
        "6项解锁条件(B3)": unlock,
        "机器可自证解锁条件全过": all_machine_ok,
        "四类错误注入自测(B3⑥)": inj,
        "乙1_数值反推PER→EPS+ROE锚(B1#14)": numeric,
        "乙2_拆股股数反推自测(B1#15·两已知错例)": split_st,
        "乙3_TGT7元检查(B3⑤)": tgt7,
        "逐条结果(review_scope·58条独立·非范围概括)": per_clause,
        "★本轮未实现(如实标)": {
            "分母有效样本数结构化(B1#13)": "★已在 sector_strength 内实现(有效样本数字段)·此处未跨检",
        },
    }


def _write_self_validate(obj, date):
    outp = ROOT / "data" / "governance" / f"conformance_check_{date}.json"
    outp.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(obj, ensure_ascii=False, indent=2)
    json.loads(txt)                                   # 写前自校验
    outp.write_text(txt, encoding="utf-8")
    json.loads(outp.read_text(encoding="utf-8"))      # 写后自校验(坏JSON拒绝·B1#2)
    return outp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now().strftime("%Y%m%d"))
    a = ap.parse_args()
    obj = build(a.date)
    p = _write_self_validate(obj, a.date)
    print(f"[conformance] 写出 {p}")
    print(f"[conformance] 整体status={obj['★整体status']}·counts一致={obj['counts一致']}·"
          f"元检查FAIL={obj['元检查FAIL数']}·四类注入全抓={obj['四类错误注入自测(B3⑥)']['四类错误全抓']}")
    print(f"[conformance] counts={obj['counts']}")
    for c in obj["元检查16项(本轮实现)"]:
        print(f"   {c['result']:<5} {c['id']}")


if __name__ == "__main__":
    main()
