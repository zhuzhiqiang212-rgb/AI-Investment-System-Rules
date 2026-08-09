# -*- coding: utf-8 -*-
"""★★★轮195 C · 漏筛基础率记录（★只记录·不判定·GPT V7 限定五项之一）。
★★20%阈值已撤回·合格线待基础率跑出后再定——★本模块【绝不判定合格与否】·只搭记录框架。

C-1 事前固定可投资池:富途/SBI可交易 + ADV60≥$50M + 非并购停牌/非退市
    ★排除并单列:并购套利 / 逼空行情 / 突发事件驱动(不混入基础率)
C-2 只计"大涨前已进池":该标的进池时间戳 < 大涨起始日(★事后进池不算命中)
C-3 分层统计:涨幅前50中·各有几只曾进 L1/L2/L3/L4
C-4 每只漏标断点归因:在哪关淘汰 / 理由 / 现在看是否成立
C-5 ★只记录·不判定
"""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def build_framework(date):
    """搭【记录框架】(schema+可投资池定义)·★不判定。实际大涨样本/进池时间戳由后续喂入。"""
    dc = date.replace("-", "")
    audit = _rj(ROOT / "data/universe" / f"p4_candidate_audit_{dc}.json")
    # C-1 事前固定可投资池(可得性:ADV60≥$50M 从审计g1流动性直接得·停牌/退市源缺→字段留占位不补造)
    rows = audit.get("逐只", []) or []
    pool = []
    for r in rows:
        num = r.get("原始数值", {}) or {}
        adv = num.get("avg60成交额USD")
        pool.append({
            "代码": r.get("代码"),
            "ADV60_USD": adv, "ADV60达标(≥$50M)": bool(r.get("g1流动性")),
            "富途SBI可交易": "NK4(交易权限源待接·不臆断)",
            "非并购停牌": "NK4(停牌源待接)", "非退市": "NK4(退市源待接)",
            "进池时间戳": None,  # ★C-2:待接入进池日志(事后进池不算命中)
        })
    投资池 = [p for p in pool if p["ADV60达标(≥$50M)"]]
    out = {
        "date": date,
        "_说明": "★★★C·漏筛基础率【记录框架】·只记录不判定·20%阈值已撤回·合格线待基础率跑出再定。本文件仅搭结构:可投资池+分层统计骨架+断点归因骨架·不含任何合格判定。",
        "C1_事前固定可投资池": {
            "口径": "富途/SBI可交易 + ADV60≥$50M + 非并购停牌/非退市",
            "★排除并单列(不混入基础率)": ["并购套利", "逼空行情", "突发事件驱动"],
            "ADV60达标数": len(投资池), "宇宙总数": len(pool),
            "★可交易/停牌/退市源": "NK4·待接入(不臆断·不补造)",
            "逐只(骨架)": pool,
        },
        "C2_只计大涨前已进池": {
            "规则": "该标的【进池时间戳】< 【大涨起始日】才算命中·事后进池不算",
            "★进池时间戳源": "待接入进池日志(现为None·不假填)",
        },
        "C3_分层统计(涨幅前50·骨架)": {
            "★口径": "涨幅前50中·各有几只【曾进】L1/L2/L3/L4",
            "曾进L1": None, "曾进L2": None, "曾进L3": None, "曾进L4": None,
            "★待喂入": "大涨样本(涨幅前50)+各只历史进层记录",
        },
        "C4_断点归因(骨架)": {
            "★每只漏标记": ["代码", "在哪关淘汰", "淘汰理由", "现在看是否成立"],
            "逐只": [],  # ★待大涨样本喂入后回填(用p4_audit的『到哪层』+『原始理由』可自动归因)
        },
        "C5_只记录不判定": "★★本框架不含20%阈值·不判合格·合格线待基础率样本累积后由董事长/Opus5定。Code只记录。",
    }
    (ROOT / "data/funnel").mkdir(parents=True, exist_ok=True)
    (ROOT / "data/funnel" / f"miss_base_rate_framework_{dc}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def attribute_missed(date, missed_codes):
    """C-4:给定漏标代码·用审计的『到哪层』+『原始理由』自动断点归因(★只归因不判对错)。"""
    dc = date.replace("-", "")
    audit = _rj(ROOT / "data/universe" / f"p4_candidate_audit_{dc}.json")
    by = {r.get("代码"): r for r in audit.get("逐只", [])}
    out = []
    for c in missed_codes:
        r = by.get(c)
        if r:
            out.append({"代码": c, "在哪关淘汰": r.get("★到哪层"), "淘汰理由": r.get("★原始理由(非综合评分不足)"),
                        "结果": r.get("★结果"), "现在看是否成立": "★待人工/Opus5核(Code只列事实)"})
        else:
            out.append({"代码": c, "在哪关淘汰": "NK4(不在可审计宇宙)", "淘汰理由": "NK4", "现在看是否成立": "NK4"})
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-08-05")
    a = ap.parse_args()
    o = build_framework(a.date)
    _n = o["C1_事前固定可投资池"]["ADV60达标数"]; _t = o["C1_事前固定可投资池"]["宇宙总数"]
    print(f"[base_rate] 记录框架已建(只记录不判定)·可投资池ADV60达标{_n}/{_t} · C3/C4骨架待大涨样本喂入 · ★无20%阈值无合格判定")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
