# -*- coding: utf-8 -*-
"""★★★轮192 P0-3:护城河一致性闸(GPT V6明确要求·硬拦非告警)——根治正文13 vs 机器表7(同一承重事实两答案)。
判据(§5.4结构化·count+source_hash·不靠文本):
  ★唯一源 moat_current.json 的【已评count + source_hash】= 产品护城河表引用的 = 正文陈述的 —— ★四处必须完全一致。
  不一致 → ★★★禁止送审(硬拦·rc=3)·不是告警。
判定对象:产品HTML里护城河表是否嵌 moat_current 的 source_hash(证明读的是唯一源)+ 表内评分行数是否=count。
  ★若产品护城河表无 moat_current source_hash 或行数≠count(如旧7只表)→硬拦。"""
import sys, json, re, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def check(html_path):
    cur = _rj(ROOT / "data/moat/moat_current.json")
    kv = cur.get("★一致性闸比对键", {})
    src_count = kv.get("count"); src_hash = kv.get("source_hash")
    n_0805 = cur.get("★08-05重评数")
    p = Path(html_path)
    if not p.exists():
        return {"pass": False, "禁止送审": True, "原因": "产品HTML不存在:%s" % html_path}
    html = p.read_text(encoding="utf-8", errors="replace")
    checks = {}
    # ①产品护城河表嵌 moat_current 的 source_hash(证明读唯一源)
    checks["①产品含moat_current_source_hash"] = bool(src_hash) and (str(src_hash) in html)
    # ②产品声明的护城河count == moat_current count(从表头"count=NN"抓·结构化)
    m = re.search(r"count=(\d+)", html)
    prod_count = int(m.group(1)) if m else None
    checks["②产品护城河count==唯一源count"] = (prod_count is not None) and (prod_count == src_count)
    # ③★★★两答案检测:产品里若同时出现"机器表7"式旧数(护城河评分只7/机器表7只)且与唯一源count(=%s)不符→两答案
    #   结构化:抓所有"护城河...N只/N评"数字·任一≠src_count且≠n_0805(13重评)→疑似两答案
    suspicious = []
    for mm in re.finditer(r"护城河[^0-9]{0,12}(\d{1,2})\s*只", html):
        v = int(mm.group(1))
        if v not in (src_count, n_0805) and v < src_count:
            suspicious.append(v)
    checks["③无与唯一源矛盾的护城河只数(防两答案)"] = (len(suspicious) == 0)
    # ④★★★轮194:正文↔机器表【未评声明】冲突(反转版·批次3出分后正文没刷新→正文说N只未评·机器表已评)
    #   结构化:正文里"N 只...未评"的 N，须 ≤ moat_current 里真未评数(score为None或NK4·不含已给分)。否则=正文陈旧·两答案。
    rows = cur.get("逐只", []) or []
    true_unrated = sum(1 for r in rows if r.get("score") is None or ("NK4" in str(r.get("score"))))
    claim_unrated = None
    _op = ROOT / "data/content" / ("opus5_content_%s.json" % str(cur.get("date", "")).replace("-", ""))
    if _op.exists():
        _optxt = _op.read_text(encoding="utf-8", errors="replace")
        _mns = [int(x) for x in re.findall(r"(\d{1,2})\s*只[^。」）)]{0,16}未评", _optxt)]
        if _mns:
            claim_unrated = max(_mns)
    checks["④正文未评声明≤机器表真未评数(防正文陈旧)"] = (claim_unrated is None) or (claim_unrated <= true_unrated)
    all_ok = all(checks.values())
    fails = [k for k, v in checks.items() if not v]
    return {"pass": all_ok, "禁止送审": (not all_ok), "唯一源": {"count": src_count, "source_hash": src_hash, "08-05重评": n_0805},
            "产品count": prod_count, "疑似两答案的只数": suspicious,
            "④正文未评声明": claim_unrated, "④机器表真未评数": true_unrated, "四处一致性检查": checks, "未过": fails,
            "★动作": ("允许送审(护城河四处同源一致)" if all_ok else "★★★禁止送审(护城河不一致·硬拦·非告警)——%s" % fails)}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--html", required=True); a = ap.parse_args()
    r = check(a.html)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r["pass"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
