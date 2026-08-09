#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★轮338 乙:全库闸自查——每个 gate/lint/check 脚本，判定它读【结构化字段】还是【自由文本关键词】(§5.4)。
★只查、不改(乙3:不一致先如实标·改法董事长定·有些该改的是填写方不是闸)。
★启发式·会有误判——本器只挑【候选】给人复核·不当定论。★闸自称与实际不一致=重点。
输出 data/governance/gate_audit_{date}.json。用法: python scripts/gate_audit.py --date 20260810
"""
import sys, re, json, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
NAME_PAT = re.compile(r"(gate|lint|check|verify|conformance|preverify|regression|_闸)", re.I)

# ★自由文本关键词匹配的可疑形态(读自由文本字段后做 in/startswith 关键词)
FREETEXT_FIELDS = ("说明", "_说明", "note", "reason", "detail", "描述", "上一版处置", "备注", "文案")
SUS_PATTERNS = [
    (r'["\'](?:[^"\']*(?:说明|note|reason|detail|描述|备注))["\']\s*\)?\s*(?:or\b|\.get)', "读自由文本字段(说明/note/reason…)"),
    (r'\bany\(\s*\w+\s+in\s+str\(', "any(kw in str(…)) 关键词包含匹配"),
    (r'\bin\s+str\(', "in str(…) 文本包含"),
    (r'\.startswith\(\s*\w+\[:\d+\]', "startswith 前缀猜(c[:n])"),
    (r'if\s+["\'][^"\']{2,}["\']\s+in\s+\w+(?![\w\[])', "if '关键词' in 变量"),
]
# ★结构化判定的好形态
STRUCT_PATTERNS = [
    (r'\.get\([^)]+\)\s*(?:==|!=|is\b|>=|<=|>|<)', "字段值 比较(==/is/大小)"),
    (r'\bin\s+[A-Z_]{3,}\b', "in 枚举常量集合(ENUM)"),
    (r'==\s*True\b|is\s+True\b|is\s+None\b|== *False', "布尔/None 判定"),
    (r'data_date|有效期至|"作废"|effective_from|end.*sorted', "日期/作废字段"),
]
CLAIM_PAT = re.compile(r"结构化|§5\.4|布尔|枚举|非文本|非关键词|structured")


def audit_one(fp):
    try:
        src = fp.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    sus = []
    for pat, desc in SUS_PATTERNS:
        n = len(re.findall(pat, src))
        # 排除掉在 FREETEXT_FIELDS 判空/日志里的良性用法很难·此处只计数
        if n:
            sus.append({"形态": desc, "命中数": n})
    struct = []
    for pat, desc in STRUCT_PATTERNS:
        n = len(re.findall(pat, src))
        if n:
            struct.append({"形态": desc, "命中数": n})
    claims_struct = bool(CLAIM_PAT.search(src))
    n_sus = sum(x["命中数"] for x in sus)
    n_struct = sum(x["命中数"] for x in struct)
    # 判定:自由文本命中显著 且 结构化少 → 疑"实际读文本";若还自称结构化 → 重点不一致
    reads_freetext = n_sus >= 2 and n_sus >= n_struct
    inconsistent = claims_struct and reads_freetext
    verdict = ("★不一致(自称结构化·实际疑读文本)" if inconsistent else
               ("疑读自由文本(未自称结构化·仍建议复核)" if reads_freetext else
                "结构化为主(疑似OK)" if n_struct else "无明显判定逻辑(可能非闸/纯渲染)"))
    return {"闸": fp.name, "自称结构化": claims_struct, "自由文本可疑命中": n_sus,
            "结构化命中": n_struct, "★判定": verdict,
            "自由文本形态": sus[:4], "结构化形态": struct[:3]}


def build(date):
    files = sorted(p for p in SCRIPTS.glob("*.py") if NAME_PAT.search(p.name))
    rows = [r for r in (audit_one(p) for p in files) if r]
    incons = [r for r in rows if r["★判定"].startswith("★不一致")]
    sus = [r for r in rows if "疑读自由文本" in r["★判定"]]
    return {
        "_说明": ("★全库闸自查(§5.4)·启发式挑候选·非定论。★不一致(自称结构化·实际疑读文本)=重点复核。"
                   "★轮338 只查不改·改法董事长定(有些该改的是填写方不是闸·如right_left_gate轮337教训)。"),
        "date": date, "扫描脚本数": len(rows),
        "★不一致数(自称结构化实际疑文本)": len(incons),
        "疑读自由文本数": len(sus),
        "★重点复核(不一致)": incons,
        "疑读自由文本(建议复核)": [{"闸": r["闸"], "★判定": r["★判定"], "自由文本命中": r["自由文本可疑命中"]} for r in sus],
        "逐脚本明细": rows,
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="20260810")
    a = ap.parse_args()
    obj = build(a.date)
    outp = ROOT / "data/governance" / f"gate_audit_{a.date}.json"
    outp.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(obj, ensure_ascii=False, indent=2)
    json.loads(txt); outp.write_text(txt, encoding="utf-8")
    print(f"[gate_audit] 写出 {outp}")
    print(f"[gate_audit] 扫{obj['扫描脚本数']}个闸 · ★不一致{obj['★不一致数(自称结构化实际疑文本)']}个 · 疑读文本{obj['疑读自由文本数']}个")
    for r in obj["★重点复核(不一致)"]:
        print(f"   ★不一致 {r['闸']}: 自由文本命中{r['自由文本可疑命中']}/结构化{r['结构化命中']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
