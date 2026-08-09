# -*- coding: utf-8 -*-
"""★轮175 C(第二层·今天栽的这层):外部资料【消化状态】+ 未消化告警闸。
★『已消化』= ①层已生成证据ID + ★该ID被某层【已填判断】引用过。★仅『文件在系统里/已映射』不算已消化。
★未消化的外部资料 → 出品时必须显式列出(不阻断出品·但产品显要位置标『N份未消化』)——★让Code和董事长都看得见·不再静默漏掉(08-03答疑资料教训)。
★Code只算消化状态+出告警·不判资料是否相关(G2·Opus5判)。"""
import sys, json, re, glob
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _latest(pat):
    g = sorted(glob.glob(str(ROOT / pat))); return g[-1] if g else None


def build(dc):
    idx = _rj(_latest("data/external/text/_index_*.json"))
    items = idx.get("条目", []) or []
    em = _rj(_latest("data/market/evidence_map_*.json"))
    led = em.get("★全证据台账(带ID·插入序稳定)", []) or []
    # txt文件名 → 证据ID(D类)
    txt2id = {}
    for e in led:
        desc = str(e.get("证据") or e.get("desc") or "")
        m = re.search(r"Drive外部资料：(.+?\.txt)", desc)
        if m:
            txt2id[m.group(1).strip()] = e.get("id") or e.get("证据ID")
    # ★被【已填判断】引用的证据ID(仅本层判断非空的槽位·NV2-4引用)
    js = _rj(_latest("data/pipeline/judgment_slots_*.json"))
    referenced = set()
    for k, s in (js.get("②~⑦层工单", {}) or {}).items():
        g = s.get("槽位", {}) or {}
        if g.get("本层判断"):   # ★只算已填判断
            for rid in (g.get("★引用证据ID(NV2-4·必填·不许凭空)", []) or []):
                referenced.add(str(rid))
    rows = []
    for it in items:
        title = it.get("标题"); src = it.get("来源"); dt = it.get("日期")
        txt = it.get("txt") or (it.get("原文件", "").rsplit(".", 1)[0] + ".txt")
        eid = txt2id.get(txt) or txt2id.get((it.get("原文件", "") or "").rsplit(".", 1)[0] + ".txt")
        # 匹配容错:按标题片段找
        if not eid:
            for fn, i in txt2id.items():
                if title and title[:10] in fn:
                    eid = i; break
        has_id = bool(eid)
        digested = has_id and (str(eid) in referenced)
        rows.append({"日期": dt, "来源": src, "标题": title, "提取成功": it.get("成功"),
                     "①层证据ID": eid or "★无(未映射)", "被已填判断引用": digested,
                     "★消化状态": "已消化" if digested else ("★未消化(有证据ID未被判断引用)" if has_id else "★未消化(未映射进①层)")})
    undig = [r for r in rows if r["★消化状态"].startswith("★未消化") and r["提取成功"]]
    out = {
        "_说明": "★轮175 外部资料消化状态。已消化=有①层证据ID且被已填判断引用·仅『文件在系统』不算。★未消化→出品显式列出(不阻断·产品显要标N份)·防静默漏掉(08-03答疑教训)。Code只算不判相关性(G2)。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "外部资料总数": len(rows), "已消化数": sum(1 for r in rows if r["★消化状态"] == "已消化"),
        "★未消化数(提取成功但未进判断)": len(undig),
        "★未消化清单": [{"日期": r["日期"], "来源": r["来源"], "标题": r["标题"], "①层证据ID": r["①层证据ID"], "状态": r["★消化状态"]} for r in undig],
        "★出品告警": ("★%d份外部资料【未消化】(提取成功但未被任何已填判断引用)·须Opus5核是否相关" % len(undig)) if undig else "✅外部资料全部已消化",
        "逐份": rows,
    }
    (ROOT / f"data/external/digest_status_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def alert_line(dc):
    """★供render/daily_alerts调用:未消化告警行(册1显要)。"""
    o = _rj(ROOT / f"data/external/digest_status_{dc}.json") or build(dc)
    return o.get("★出品告警"), o.get("★未消化数(提取成功但未进判断)", 0), o.get("★未消化清单", [])


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("外部资料 %d · 已消化 %d · ★未消化 %d" % (o["外部资料总数"], o["已消化数"], o["★未消化数(提取成功但未进判断)"]))
    print("★出品告警:", o["★出品告警"])
    for r in o["★未消化清单"]:
        print("  ★未消化:", r["日期"], r["来源"], str(r["标题"])[:36], "· 证据ID", r["①层证据ID"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
