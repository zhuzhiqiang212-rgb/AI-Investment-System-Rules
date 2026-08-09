#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★轮335 甲:只读校验 Opus5 填的 judgment_slots_{date}.json。★只校验·不改字。
甲1 JSON合法(不吞异常·指行号)·甲2 结构校验(三件齐/枚举非null/已填不空/引用ID存在)·甲3 字节乱码。
★⑦交易动作按链条=0笔·正当空·不当欠件校(董事长2026-08-09)。
用法: python scripts/judgment_slots_validate.py --date 20260810
"""
import sys, json, argparse, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THREE = ["本层判断", "依据", "证伪信号"]
ENUM = ["★依据右栏哪把尺(①~⑥·E8必填)", "★与尺是否矛盾(E8枚举·必填)", "★属于哪个闭环(E10枚举·必填)"]
CHECK_LAYERS = ["②国家战略", "③资金流动", "④板块轮动", "⑤机会池", "⑥持仓比较"]  # ⑦=链条0笔·正当空


def _is_empty(v):
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() in ("", "None", "null", "[]", "{}")
    if isinstance(v, (list, dict)):
        return len(v) == 0
    return False


def _as_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v.replace("'", '"'))
        except Exception:
            return [x.strip() for x in re.findall(r"E\d+", v)]
    return []


def validate(date):
    p = ROOT / "data" / "pipeline" / f"judgment_slots_{date}.json"
    res = {"file": p.name, "甲1_JSON合法": None, "甲2_结构问题": [], "甲3_乱码EF_BF_BD": None,
           "★整体": None}
    # 甲1 JSON合法(不吞异常·指行号)
    raw = p.read_bytes()
    res["甲3_乱码EF_BF_BD"] = raw.count(b"\xef\xbf\xbd")
    try:
        d = json.loads(raw.decode("utf-8"))
        res["甲1_JSON合法"] = "合法"
    except json.JSONDecodeError as e:
        res["甲1_JSON合法"] = f"★坏:第{e.lineno}行第{e.colno}列·{e.msg}"
        res["★整体"] = "FAIL(JSON坏·后续不校)"
        return res, None
    # 台账证据ID
    ev = d.get("①层证据台账(带ID·供引用)", []) or []
    valid_ids = {str(e.get("id")) for e in ev if isinstance(e, dict) and e.get("id")}
    res["①层台账证据ID数"] = len(valid_ids)
    sl = d.get("②~⑦层工单", {}) or {}
    fails = []
    for L in CHECK_LAYERS:
        v = sl.get(L)
        if not v:
            fails.append(f"[{L}] 该层整个缺失")
            continue
        s = v.get("槽位", {}) or {}
        st = str(s.get("_状态") or v.get("★待Opus5填(20260810)") or "")
        filled_claim = "已填" in str(v.get("★待Opus5填(20260810)", "")) or "已填" in st
        # 甲2① 三件齐
        for f in THREE:
            if _is_empty(s.get(f)):
                fails.append(f"[{L}·槽位.{f}] 三件之一为空")
        # 甲2② 枚举必填非null
        for f in ENUM:
            if _is_empty(s.get(f)):
                fails.append(f"[{L}·槽位.{f}] 必填枚举为空/null")
        # 适用范围(dict·子项非空)
        ar = s.get("★本判断的适用范围(B1·必填)")
        if _is_empty(ar) or (isinstance(ar, dict) and _is_empty(ar.get("适用驱动类型/板块"))):
            fails.append(f"[{L}·槽位.适用范围.适用驱动类型/板块] 空")
        # 甲2③ 标已填却空
        if filled_claim and _is_empty(s.get("本层判断")):
            fails.append(f"[{L}] 标『已填』但本层判断为空")
        # 甲2④ 引用证据ID须存在于①层台账
        for i in _as_list(s.get("★引用证据ID(NV2-4·必填·不许凭空)")):
            if str(i) not in valid_ids:
                fails.append(f"[{L}·引用证据ID] {i} 不在①层台账(共{len(valid_ids)}条·引用不存在的ID)")
    res["甲2_结构问题"] = fails
    res["★整体"] = "PASS(五层结构全过)" if (not fails and res["甲3_乱码EF_BF_BD"] == 0) else f"FAIL({len(fails)}处结构问题·乱码{res['甲3_乱码EF_BF_BD']})"
    return res, d


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="20260810")
    a = ap.parse_args()
    res, _ = validate(a.date)
    print(f"[甲1] JSON: {res['甲1_JSON合法']}")
    print(f"[甲3] 乱码 EF BF BD = {res['甲3_乱码EF_BF_BD']}")
    print(f"[甲2] ①层台账证据ID {res.get('①层台账证据ID数')} 条 · 结构问题 {len(res['甲2_结构问题'])} 处:")
    for f in res["甲2_结构问题"]:
        print("   ✗", f)
    if not res["甲2_结构问题"]:
        print("   ★②③④⑤⑥五层:三件齐/枚举非null/已填不空/引用ID都在台账 —— 全过")
    print(f"[★整体] {res['★整体']}")
    return 0 if res["★整体"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
