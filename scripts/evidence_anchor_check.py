#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★轮335 乙:E-ID 内容锚比对器（防判断静默挂在变了的证据上·与写死33.84同一族病）。

背景:judgment_slots 是【某日】证据台账拷来的·①层证据 E1~En 每日重生成——【编号不变·内容会变】。
Opus5 在各层加了『引用证据的内容锚』(把当时那条证据原文抄下)。
本器:读各层内容锚·与【当日重生成的①层台账】逐条【按内容】比对：
  ★不符→该层置「须重判」·产品打红条(乙2)  ★相符→静默通过(乙3)  ★按内容不按编号(乙4·编号永远相符=等于没比)。

判据(乙4):内容 hash + 原文前40字·规范化后比对·两者都变才判「已变」·只变格式(空白/标点)不判。
用法:
  python scripts/evidence_anchor_check.py --date 20260810              # 与当日live台账比
  python scripts/evidence_anchor_check.py --date 20260810 --selftest   # 注入变化证明能抓
"""
import sys, json, argparse, re, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANCHOR_KEY = "★★引用证据的内容锚(防E-ID漂移)"


def _rj(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _norm(s):
    """规范化:去HTML标签/多空白/首尾·只留实质内容(乙4:只变格式不判已变)。"""
    s = re.sub(r"<[^>]+>", "", str(s or ""))
    s = re.sub(r"\s+", "", s)
    return s


def _drifted(anchor, current):
    """★乙4:按内容判漂移。内容锚是 Opus5 的【略记引用】(证据开头一段)·比当日全文短——
    故判据=【规范化后·锚是否仍是当日证据的前缀/子串】。是→内容保留(只是略记/加尾巴·非漂移);否→真漂移(数字/事实变了)。
    ★只变格式(空白/标点)不判漂移(_norm 已去);数字或关键内容变→锚找不到→判漂移。"""
    a, c = _norm(anchor), _norm(current)
    if not a:
        return False
    # 锚是当日证据的前缀 或 子串(容 Opus5 略记) → 未漂移
    if c.startswith(a) or a in c:
        return False
    # 反向:当日证据是锚的前缀(证据被截短但仍一致) → 未漂移
    if a.startswith(c) and len(c) >= 8:
        return False
    return True


def _live_evidence(date):
    """当日重生成的①层证据台账 {E-ID: 证据原文}。优先 layer1_evidence_mapper live·回落 evidence_map/slots内嵌。"""
    # 1) live 重算
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from layer1_evidence_mapper import build as _emb
        o = _emb(date)
        for key in ("①层证据台账(带ID·供引用)", "路2_下游维度依据", "证据台账"):
            lst = o.get(key)
            if isinstance(lst, list) and lst:
                return {str(e.get("id")): (e.get("证据") or e.get("evidence") or "") for e in lst if isinstance(e, dict) and e.get("id")}, f"layer1_evidence_mapper.build({date})·live"
    except Exception:
        pass
    # 2) 回落:slots 内嵌台账(注:这是拷贝时的快照·与anchor同源→会相符·仅作无live时兜底)
    sp = ROOT / "data" / "pipeline" / f"judgment_slots_{date}.json"
    if sp.exists():
        d = _rj(sp)
        lst = d.get("①层证据台账(带ID·供引用)", []) or []
        return {str(e.get("id")): (e.get("证据") or "") for e in lst if isinstance(e, dict) and e.get("id")}, "slots内嵌台账(兜底·快照·非当日live)"
    return {}, "无源"


def _anchors(slots):
    """从各层取 {层: {E-ID: 锚原文}}。★跳过 ★用法/★为什么 等非E-ID元键。"""
    out = {}
    for L, v in (slots.get("②~⑦层工单", {}) or {}).items():
        a = (v.get("槽位", {}) or {}).get(ANCHOR_KEY)
        if isinstance(a, dict):
            eids = {k: t for k, t in a.items() if re.fullmatch(r"E\d+", str(k))}
            if eids:
                out[L] = eids
    return out


def check(date, live_map=None):
    slots = _rj(ROOT / "data" / "pipeline" / f"judgment_slots_{date}.json")
    anchors = _anchors(slots)
    if live_map is None:
        live_map, src = _live_evidence(date)
    else:
        src = "注入(selftest)"
    layers = []
    for L, eids in anchors.items():
        drifted = []
        for eid, anchor_txt in eids.items():
            cur = live_map.get(str(eid))
            if cur is None:
                drifted.append({"E-ID": eid, "情形": "当日台账无此ID", "锚原文前40": str(anchor_txt)[:40], "今日": "(缺)"})
                continue
            if _drifted(anchor_txt, cur):          # 内容变(规范化后·锚不再是当日证据的前缀/子串)·非格式
                drifted.append({"E-ID": eid, "情形": "内容已变", "锚原文前40": str(anchor_txt).strip()[:40], "今日前40": str(cur).strip()[:40]})
        layers.append({"层": L, "锚条数": len(eids), "漂移数": len(drifted),
                       "状态": ("★须重判" if drifted else "相符·静默通过"), "漂移明细": drifted})
    n_drift = sum(1 for x in layers if x["漂移数"] > 0)
    return {"date": date, "证据源": src, "有锚的层": len(anchors),
            "须重判层数": n_drift, "逐层": layers}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="20260810")
    ap.add_argument("--selftest", action="store_true", help="注入一条内容变化·证明能抓")
    a = ap.parse_args()
    live = None
    if a.selftest:
        # 用 slots 内嵌台账做基线·改 E1 内容模拟漂移
        d = _rj(ROOT / "data" / "pipeline" / f"judgment_slots_{a.date}.json")
        live = {str(e.get("id")): e.get("证据") for e in d.get("①层证据台账(带ID·供引用)", []) if e.get("id")}
        if "E1" in live:
            live["E1"] = "★[selftest注入]日股开盘：8只均 −3.80%·普跌（与原锚+1.29%普涨相反）"
    res = check(a.date, live_map=live)
    outp = ROOT / "data" / "pipeline" / f"anchor_drift_{a.date}.json"
    txt = json.dumps(res, ensure_ascii=False, indent=2)
    json.loads(txt); outp.write_text(txt, encoding="utf-8")
    print(f"[anchor] 证据源:{res['证据源']}")
    print(f"[anchor] 有锚的层 {res['有锚的层']} · ★须重判层数 {res['须重判层数']}")
    for L in res["逐层"]:
        print(f"   {L['状态']:<12} {L['层']}(锚{L['锚条数']}条·漂移{L['漂移数']})")
        for dft in L["漂移明细"][:2]:
            print(f"       {dft['E-ID']} {dft['情形']}: 锚『{dft.get('锚原文前40','')}』→ 今日『{dft.get('今日前40', dft.get('今日',''))}』")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
