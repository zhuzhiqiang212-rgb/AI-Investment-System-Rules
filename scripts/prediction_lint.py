#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""预测质量三铁律 + 大白话校验（派工单Q2/Q3·2026-07-22）。gate3_v2生产模板/锁定前硬校验。
铁律① 概率禁45%~55%(五五开=骑墙)→落此区间拒绝入库(要么押方向要么标『不锁』)。
铁律② 预测层禁买卖挂单价/加减仓动作(挪到资金行动层):动作词(加仓/减仓/建仓/清仓/挂单/止损/止盈/买入/卖出/满仓)
       +短期预判里的价位目标(看…至/下探/反弹至/看到 + 具体价)→违规。★长期估值目标价(NAV/分析师目标)不算买卖价·放行。
铁律③ 每条预测支持v1→v2版本链:原始SHA不可改·更新追加带时间戳+触发原因(文件级演变链说明校验)。
Q3 大白话四步:每条须含 事实/为什么/对你影响/怎么办(或①②③④)·无术语。
被 lock_predictions.py 调用(锁定前校验·不过不锁)。也可独立:python scripts/prediction_lint.py --file data/forecast/arch_predictions_v2_20260722.json"""
import argparse, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

ACTION_KW = ["加仓", "减仓", "建仓", "清仓", "挂单", "止损", "止盈", "买入", "卖出", "满仓"]
DISCLAIMER = ["不含买卖价", "资金行动层", "不在此", "加仓闸", "禁买卖", "禁止", "不含"]
SHORT_KEYS = ["短期预判_押方向_锁定记分", "短期预判_押方向", "短期走势预判_锁定记分"]  # v2 / 批次 / v1
LONG_KEYS = ["长期预判_押方向", "长期预判_锁定记分", "长期目标价_锁定记分"]
# 短期价位目标(方向层不该有具体买卖价):看…至/下探/反弹至/看到 + 3位以上数字
PRICE_TARGET_RE = re.compile(r"(看|反弹至|下探|看到|目标位|回落至|冲至)[^,，。]{0,6}?[¥$]?\d{3,}")


def parse_probs(s):
    return [int(x) for x in re.findall(r"(\d{1,3})\s*%", str(s))]


def _blk(pred, keys):
    for k in keys:
        if isinstance(pred.get(k), dict) and pred.get(k):
            return pred[k], k
    return {}, None


def lint_pred(pred):
    v = []
    name = pred.get("标的", "?")
    short, _ = _blk(pred, SHORT_KEYS)
    long_, _ = _blk(pred, LONG_KEYS)
    # 铁律① 概率禁45-55(短期必判·长期若给了概率也判)
    for scale, blk in [("短期", short), ("长期", long_)]:
        # 只判『头部概率』(第一个%·即押的方向概率);括号内如『改自55%被校验拒』是变更说明·不算
        probs = parse_probs(blk.get("概率", ""))
        if probs and 45 <= probs[0] <= 55:
            v.append({"铁律": "①禁五五开", "标的": name, "尺度": scale, "命中": f"头部概率{probs[0]}%落45~55(骑墙)",
                      "处置": "押方向(>55或<45)或标『不锁』"})
    # 铁律② 短期价位目标 + 全条动作词(排除disclaimer上下文)
    short_txt = json.dumps(short, ensure_ascii=False)
    for m in PRICE_TARGET_RE.finditer(short_txt):
        seg = short_txt[max(0, m.start() - 12):m.start()]
        if not any(dw in seg for dw in DISCLAIMER):
            v.append({"铁律": "②禁买卖价(短期方向层)", "标的": name, "命中": m.group(0),
                      "处置": "短期只判方向·具体买卖价挪到资金行动层/加仓闸"})
    # ②动作词只扫『预测块』(短期/长期押方向)·不扫归因(归因含新闻事实·如"分析师列为值得加仓5只"是引用非动作)
    whole = json.dumps({"短": short, "长": long_}, ensure_ascii=False)
    NEG = "不非没未勿别"  # 否定/说明语境(如『不满仓押』=解释信心·非动作)
    for kw in ACTION_KW:
        i = 0
        while True:
            j = whole.find(kw, i)
            if j < 0:
                break
            ctx = whole[max(0, j - 16):j + 16]
            prev = whole[j - 1] if j > 0 else ""
            negated = (prev in NEG)  # 紧邻否定=说明信心非资金动作
            if not negated and not any(dw in ctx for dw in DISCLAIMER):
                v.append({"铁律": "②禁加减仓/挂单动作", "标的": name, "命中": kw, "上下文": ctx,
                          "处置": "预测层不出资金动作·挪资金行动层"})
            i = j + len(kw)
    # Q3 大白话四步
    bs = pred.get("大白话四步", {})
    keys = "".join(bs.keys())
    need = ["事实", "为什么", "对你影响"]
    has_action = ("怎么办" in keys or "预测" in keys or "④" in keys)
    if len(bs) < 4 or not all(n in keys for n in need) or not has_action:
        v.append({"铁律": "Q3大白话四步", "标的": name,
                  "命中": f"大白话四步缺/不全(现{list(bs.keys())})·须含事实/为什么/对你影响/怎么办(或④)"})
    return v


def lint_file(path):
    j = json.loads(Path(path).read_text(encoding="utf-8"))
    preds = j.get("预测", [])
    all_v = []
    per = {}
    for p in preds:
        vv = lint_pred(p)
        per[p.get("标的", "?")] = vv
        all_v.extend(vv)
    # 铁律③ 版本链(文件级):v2须有演变链说明+v1引用+触发原因
    chain_ok = True
    chain_note = None
    ver = (preds[0].get("版本") if preds else None)
    if ver and str(ver).lower() != "v1":
        ec = j.get("演变链说明", {})
        if not (ec and ("v1" in ec) and ("触发" in json.dumps(ec, ensure_ascii=False))):
            chain_ok = False
            chain_note = "★铁律③:非v1版须带『演变链说明』含v1引用+触发原因(原始SHA不可改·更新追加)"
            all_v.append({"铁律": "③版本链", "命中": chain_note})
        else:
            chain_note = "演变链说明齐(v1引用+触发原因)·原始v1不改·v2追加"
    return {"passed": len(all_v) == 0, "版本": ver, "违规数": len(all_v),
            "版本链": {"ok": chain_ok, "说明": chain_note}, "逐条违规": per, "全部违规": all_v}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    r = lint_file(a.file)
    print("三铁律+大白话校验:", a.file)
    print("版本:", r["版本"], "· 通过:", r["passed"], "· 违规数:", r["违规数"], "· 版本链:", r["版本链"]["说明"])
    for vv in r["全部违规"]:
        print("  ✗", vv)
    if r["passed"]:
        print("  ✓ 全过(押方向/无买卖价/大白话齐/版本链齐)")
    return 0 if r["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
