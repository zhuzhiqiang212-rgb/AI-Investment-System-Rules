#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补锁5条修正版（派工单·2026-07-22）。holdings文件已改5条(原55%被拒)→重跑forecast_lock补锁·并入locked_baseline。
CRCL长/SNDK长/丰田长→押明确方向(58/57/57%)→进长期分母;万代短/任天堂短→不锁(诚实)→记录不进短期分母。
holdings原SHA不删·修正版新SHA·留演变链。重算短期/长期分母。
用法：python scripts/patch_lock_5.py --date 20260722"""
import argparse, json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
FDIR = ROOT / "data" / "forecast"
PDCA = ROOT / "data" / "pdca"
JST = timezone(timedelta(hours=9))
sys.path.insert(0, str(ROOT / "scripts"))
from prediction_lint import lint_file, _blk, SHORT_KEYS, LONG_KEYS
from forecast_lock import lock, external_time

# 5条修正(code, 尺度)
FIXED = [("US.CRCL", "长期"), ("US.SNDK", "长期"), ("JP.7203", "长期"), ("JP.7832", "短期"), ("JP.7974", "短期")]


def now():
    return datetime.now(JST).isoformat(timespec="seconds")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="20260722"); a = ap.parse_args()
    d = a.date
    sys.stdout.reconfigure(encoding="utf-8")
    fp = FDIR / f"arch_pred_holdings_{d}.json"
    j = json.loads(fp.read_text(encoding="utf-8"))

    # 1) 校验holdings改后必过(否则不锁)
    lint = lint_file(str(fp))
    print("holdings改后三铁律校验· 通过:", lint["passed"], "· 违规:", lint["违规数"])
    for v in lint["全部违规"]:
        print("   ✗", v.get("铁律"), v.get("标的"), v.get("尺度"), v.get("命中"))
    if not lint["passed"]:
        print("★holdings仍有违规·拒绝补锁"); return 2

    # 2) 重锁holdings修正版 → 新SHA
    et = external_time()
    lk = lock(j, d, label="baseline_持仓_修正5条")
    if not lk.get("ok"):
        print("★锁定失败:", lk); return 1
    new_sha = lk["sha256"]

    # 3) 读记分卡+baseline
    regp = PDCA / "locked_predictions_registry.json"
    reg = json.loads(regp.read_text(encoding="utf-8"))
    bp = FDIR / f"locked_baseline_{d}.json"
    baseline = json.loads(bp.read_text(encoding="utf-8"))
    old_sha = baseline.get("锁定哈希(3源)", {}).get("持仓18", {}).get("sha256", "?")

    key = lambda e: (e["标的"], e["尺度"], e["锁定日"], e.get("版本"))
    exist = {key(e) for e in reg["已登记预测"]}

    # 4) 登记5条修正(版本=baseline_持仓_修正·带新SHA)
    added = []
    for code, scale in FIXED:
        pred = next((p for p in j["预测"] if code in p["标的"]), None)
        if not pred:
            print("★找不到:", code); continue
        blk = _blk(pred, LONG_KEYS if scale == "长期" else SHORT_KEYS)[0]
        direction = str(blk.get("方向", ""))
        not_lock = "不锁" in direction
        in_denom = (scale == "长期" and not not_lock)  # 3条长期进分母·2条不锁短期不进
        status = ("不锁·判不出(诚实)·不进短期分母" if not_lock else "已锁定待评(修正版·押方向)")
        entry = {"标的": pred["标的"], "尺度": scale, "锁定日": d, "版本": "baseline_持仓_修正",
                 "方向": blk.get("方向"), "概率": blk.get("概率"),
                 "PDCA核对日": (str(blk.get("PDCA核对日"))[:10] if str(blk.get("PDCA核对日", ""))[:2].isdigit() else blk.get("PDCA核对日")),
                 "PDCA判据": ("事件兑现日比 实际方向 vs 押的方向·对=命中" if scale == "长期" else "押方向vs实际"),
                 "锁定sha256": new_sha, "链hash": lk["chain_hash"], "时间认证": lk["time_status"],
                 "前身": "原55%被校验拒(见locked_baseline拒绝入库)", "大白话四步": pred.get("大白话四步", {}),
                 "状态": status, "进胜率分母": in_denom}
        if key(entry) in exist:
            print("  已存在跳过:", code, scale); continue
        reg["已登记预测"].append(entry); exist.add(key(entry)); added.append(entry)

    # 5) 演变链 holdings原→修正
    reg.setdefault("演变链", []).append({
        "文件": "arch_pred_holdings", "from_sha": old_sha, "to_sha": new_sha,
        "触发原因": "原5条55%五五开被prediction_lint拒→架构师改押方向(CRCL偏下58/SNDK偏下57/丰田偏上57)+2条改不锁(万代/任天堂)",
        "时间(外部)": et.get("iso"), "原文件处置": "不删·write-once快照保留"})
    reg["更新"] = now()

    # 6) 重算分母(全登记)
    active = [e for e in reg["已登记预测"] if e.get("进胜率分母", True) and e.get("状态", "").startswith("已锁定")]
    short_denom = [e for e in active if e["尺度"] == "短期"]
    long_denom = [e for e in active if e["尺度"] == "长期"]

    # 7) 更新baseline(追加补锁段)
    baseline["补锁5条修正_" + d] = {
        "generated_at": now(), "holdings修正版SHA": new_sha, "holdings原SHA": old_sha,
        "外部时间": et.get("iso"), "演变链": "原→修正(原不删)",
        "进长期分母3条": [e["标的"] for e in added if e["进胜率分母"]],
        "不锁不进短期分母2条": [e["标的"] for e in added if not e["进胜率分母"]],
        "补锁后_短期分母": len(short_denom), "补锁后_长期分母": len(long_denom)}
    baseline.setdefault("锁定哈希(3源)", {})["持仓18_修正版"] = {"sha256": new_sha, "说明": "5条改后重锁·原SHA见持仓18·演变链留档"}

    bp.write_text(json.dumps(baseline, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    regp.write_text(json.dumps(reg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    ok = True
    for p in (bp, regp):
        raw = p.read_bytes()
        try:
            json.load(open(p, encoding="utf-8")); jl = True
        except Exception as e:
            jl = False; ok = False; print("★json.load失败", p.name, e)
        print("wrote", p.name, len(raw), "字节·EFBFBD=", raw.count(b"\xef\xbf\xbd"), "·json.load通过=", jl)
    print("holdings修正版SHA:", new_sha)
    print("补锁登记:", len(added), "条 → 进长期分母3:", [e["标的"].split()[0] for e in added if e["进胜率分母"]],
          "· 不锁不进短期分母2:", [e["标的"].split()[0] for e in added if not e["进胜率分母"]])
    print("★补锁后 短期分母:", len(short_denom), "· 长期分母:", len(long_denom))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
