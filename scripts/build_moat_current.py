# -*- coding: utf-8 -*-
"""★★★轮192 P0-1:合并三份护城河评分为【唯一 Current 源】data/moat/moat_current.json。
根治GPT二次FAIL根因(正文13只 vs 机器表7只·同一承重事实两个答案·第五次同族错:上游做完下游没接)。
源:①moat_analysis_20260728(07-28旧·20只·items·total_score) ②moat_opus5_full_20260805(批次1·7只·★★逐只评分·总分) ③moat_opus5_batch2(批次2·6只)。
★合并规则(严格按GPT):同标的多份→取最新日期(08-05>07-28)·沿用旧的标 source_date+★沿用未重评:true·不静默覆盖(每只可查哪天评)·新旧不同保留 previous_score。"""
import sys, json, re, hashlib, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _code(s):
    m = re.search(r"([A-Z]{2}\.[0-9A-Z]+)", str(s))
    return m.group(1) if m else None


def build():
    old = _rj(ROOT / "data/moat/moat_analysis_20260728.json")
    b1 = _rj(ROOT / "data/opportunity/moat_opus5_full_20260805.json").get("★★逐只评分", {}) or {}
    b2 = _rj(ROOT / "data/opportunity/moat_opus5_batch2_20260805.json").get("★★逐只评分", {}) or {}
    # ★轮194:批次3(9只·键名"★★逐只"·含SPCX NK4未上市)
    _b3raw = _rj(ROOT / "data/opportunity/moat_opus5_batch3_20260805.json")
    b3 = _b3raw.get("★★逐只评分") or _b3raw.get("★★逐只") or {}
    # 07-28旧(20只)
    old_by = {}
    for it in old.get("items", []):
        c = it.get("symbol")
        if c:
            old_by[c] = {"score": it.get("total_score"), "grade": it.get("moat_grade"), "confidence": it.get("confidence"), "dimensions": it.get("dimensions")}
    # 08-05新(批次1+2·13只)
    new_by = {}
    for src in (b1, b2, b3):
        for k, v in src.items():
            c = _code(k)
            if c and isinstance(v, dict):
                sc = v.get("总分")
                if sc is None and ("NK4" in json.dumps(v, ensure_ascii=False) or "未上市" in json.dumps(v, ensure_ascii=False)):
                    sc = "NK4·未上市无法评分"   # ★SPCX:标NK4非"未评"(不凭印象硬评)
                new_by[c] = {"score": sc, "grade": v.get("结论"), "dims": {kk: (vv.get("分") if isinstance(vv, dict) else vv) for kk, vv in v.items() if kk in ("品牌", "网络效应", "成本优势", "转换成本", "无形资产")}}
    # 合并:union·08-05优先
    merged = {}
    for c in set(list(old_by) + list(new_by)):
        if c in new_by:
            rec = {"代码": c, "score": new_by[c]["score"], "grade": new_by[c]["grade"], "source_date": "2026-08-05", "★沿用未重评": False}
            if c in old_by and old_by[c]["score"] != new_by[c]["score"]:
                rec["previous_score"] = old_by[c]["score"]; rec["previous_source_date"] = "2026-07-28"
        else:
            rec = {"代码": c, "score": old_by[c]["score"], "grade": old_by[c]["grade"], "source_date": "2026-07-28", "★沿用未重评": True}
        merged[c] = rec
    # ★★★轮193 A:应用 Opus5 自我复核修正(moat_review_newold·撤回微软9→7等)·★保留previous_score+修正记录·不静默改。
    rev = _rj(ROOT / "data/moat/moat_review_newold_20260805.json").get("★★★四、修正后的评分（★以此为准）", {}) or {}
    for c, fx in rev.items():
        if c in merged and isinstance(fx, dict) and fx.get("分") is not None:
            r = merged[c]
            if r.get("score") != fx["分"]:
                r["★修正前score"] = r.get("score")
                r["★修正记录"] = "Opus5自我复核撤回·%s" % str(fx.get("★变更", "")).replace("★", "")
                r["score"] = fx["分"]
                r["grade"] = fx.get("结论", r.get("grade"))
                r["source_date"] = "2026-08-05"
    rows = sorted(merged.values(), key=lambda r: r["代码"])
    evaluated = [r for r in rows if r["score"] is not None]
    n_0805 = sum(1 for r in rows if r["source_date"] == "2026-08-05")
    n_0728 = sum(1 for r in rows if r["source_date"] == "2026-07-28")
    # ★source_hash:count + 各只(代码,score,source_date)排序哈希→供一致性闸比对(§5.4结构化)
    basis = json.dumps([(r["代码"], r["score"], r["source_date"]) for r in rows], ensure_ascii=False, sort_keys=True)
    shash = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
    out = {
        "_说明": "★★★轮192 P0-1 唯一Current护城河源(合并07-28旧20+08-05批次1/2共13·取最新·沿用标记·previous_score保留)。★正文/机器表/统计/动作层四处必须全从本文件读(P0-2)·一致性闸比对count+source_hash(P0-3)。",
        "date": "2026-08-05", "★唯一源": True,
        "★已评数量": len(evaluated), "★总条数": len(rows),
        "★08-05重评数": n_0805, "★07-28沿用未重评数": n_0728,
        "★source_hash(count+逐只code/score/date)": shash,
        "★一致性闸比对键": {"count": len(evaluated), "source_hash": shash},
        "逐只": rows,
    }
    (ROOT / "data/moat/moat_current.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def load():
    """P0-2:四处渲染统一从这里读护城河。返回 {code: {score,grade,source_date,沿用}}。"""
    o = _rj(ROOT / "data/moat/moat_current.json")
    return {r["代码"]: r for r in o.get("逐只", [])}, o.get("★一致性闸比对键", {})


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    argparse.ArgumentParser().parse_args()
    o = build()
    print("[moat_current] 总%d只 · 已评%d · 08-05重评%d · 07-28沿用%d · source_hash=%s" % (
        o["★总条数"], o["★已评数量"], o["★08-05重评数"], o["★07-28沿用未重评数"], o["★source_hash(count+逐只code/score/date)"]))
    for r in o["逐只"]:
        tag = "沿用07-28" if r["★沿用未重评"] else "08-05评"
        prev = "(previous%s)" % r.get("previous_score") if "previous_score" in r else ""
        print("  %-9s 分%-4s %s %s" % (r["代码"], r["score"], tag, prev))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
