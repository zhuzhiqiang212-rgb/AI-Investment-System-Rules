# -*- coding: utf-8 -*-
"""★轮79 AS1/AS2:判断记分卡闸。
AS1-1:每条判断须有 scorecard 条目(种子自 forecast·缺则该步FAIL)。
AS1-2:验证状态=未命中 而『错在哪』为空 → FAIL。
AS1-3:登记日 ≠ 判断产出日 → 告警(不许事后补登记)。
AS2-1:certainty_ledger 的『当前确定性』必须与 scorecard 派生一致·手填(不一致)→ FAIL。"""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
SC = ROOT / "data" / "pdca" / "judgment_scorecard.json"
CL = ROOT / "data" / "pdca" / "certainty_ledger.json"
LAYERS = ["①世界观", "②国家战略", "③资金流动", "④板块轮动", "⑤机会池", "⑥持仓层", "⑦复盘层"]


def _derive_cert(entries, layer):
    es = [e for e in entries if e.get("层") == layer]
    # ★轮81:升档只看『到期验证』类(与 certainty_ledger 一致·自查证伪不计入)
    verified = [e for e in es if e.get("★验证来源") == "到期验证" and e.get("验证状态") in ("命中", "未命中", "部分", "已证伪")]
    hit = sum(1 for e in verified if e.get("验证状态") == "命中")
    rate = (hit / len(verified) * 100) if verified else 0
    if len(verified) >= 20 and rate >= 70:
        return "高"
    if len(verified) >= 10 and rate >= 60:
        return "中"
    return "低"


def check():
    fails = []; warns = []
    if not SC.exists():
        return ["judgment_scorecard.json 不存在→复盘层部件①未产出"], []
    sc = json.loads(SC.read_text(encoding="utf-8"))
    entries = sc.get("entries", [])
    import re as _re
    for e in entries:
        # AS1-2:未命中/已证伪而错在哪空→FAIL
        if e.get("验证状态") in ("未命中", "已证伪") and not e.get("错在哪"):
            fails.append("AS1-2 记分卡 %s 验证=%s 但『错在哪』为空(必填:数据错/逻辑错/时机错/口径错)→FAIL" % (e.get("id"), e.get("验证状态")))
        # ★AT2-1(轮80):C级来源不得输出精确数——依据等级=C 的判断文本含小数点后≥2位精确值→FAIL
        if e.get("依据等级") == "C":
            txt = str(e.get("判断") or "") + " " + " ".join(str(x) for x in (e.get("依据") or []))
            m = _re.search(r"\d+\.\d{2,}", txt)
            if m:
                fails.append("AT2-1 记分卡 %s 依据等级=C(二手/拍的)却输出精确数『%s』→C级不得输出小数点后≥2位·应改『大部分/约』等模糊表述→FAIL" % (e.get("id"), m.group(0)))
        # AS1-3:登记日≠判断产出日→告警(不许事后补)
        rd, pd = str(e.get("登记日") or ""), str(e.get("判断产出日") or "")
        if rd and pd and rd != pd:
            warns.append("AS1-3 记分卡 %s 登记日%s≠判断产出日%s(疑事后补登记·登记须与出判断同时)" % (e.get("id"), rd, pd))
    # AS2-1:certainty_ledger 当前确定性 必须=scorecard派生(手填→FAIL)
    if CL.exists():
        cl = json.loads(CL.read_text(encoding="utf-8"))
        for layer in LAYERS:
            declared = (cl.get("层", {}).get(layer, {}) or {}).get("当前确定性")
            derived = _derive_cert(entries, layer)
            if declared is not None and declared != derived:
                fails.append("AS2-1 确定性累积表『%s』当前确定性=%s ≠ 由scorecard派生的%s→疑手填(必须派生·不许手填)→FAIL" % (layer, declared, derived))
    return fails, warns


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    fails, warns = check()
    for w in warns:
        print("  ⚠", w)
    if fails:
        print("[judgment_scorecard_gate FAIL] %d 条" % len(fails))
        for f in fails:
            print("  ✗", f)
        return 6
    print("[judgment_scorecard_gate PASS] 每条判断有条目·无未命中缺错因·确定性派生一致(告警%d)" % len(warns))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
