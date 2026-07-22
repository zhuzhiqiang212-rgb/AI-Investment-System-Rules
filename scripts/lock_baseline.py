#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""锁定35只预测基线（派工单·2026-07-22）。forecast_lock候选7+持仓18两文件·纳入v2(软银/爱德万542d742)同一基线。
每条走三铁律校验(prediction_lint):
 - 55%五五开(违反铁律①)→拒绝入记分卡(锁文件留审计·但不进胜率分母·须架构师改押方向)
 - HII短期『不锁·判不出』/ SpaceX短期『不适用·未上市』→记录·不进短期胜率分母
进记分卡:各短/长条目带PDCA核对日+判据(押方向vs实际)。锁定时间戳须晚于batch_frame(15:15)与填写。
输出 data/forecast/locked_baseline_20260722.json。
用法：python scripts/lock_baseline.py --date 20260722"""
import argparse, json, os, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
FDIR = ROOT / "data" / "forecast"
PDCA = ROOT / "data" / "pdca"
JST = timezone(timedelta(hours=9))
sys.path.insert(0, str(ROOT / "scripts"))
from prediction_lint import lint_file, _blk, SHORT_KEYS, LONG_KEYS
from forecast_lock import lock, external_time

FILES = [("候选", "arch_pred_candidates_20260722.json"), ("持仓", "arch_pred_holdings_20260722.json")]


def now():
    return datetime.now(JST).isoformat(timespec="seconds")


def classify_entry(direction, viol_set, tgt, scale):
    dir_s = str(direction or "")
    if "不锁" in dir_s:
        return "不锁·判不出(诚实)", False
    if "不适用" in dir_s:
        return "不适用·未上市(无股价可核)", False
    if (tgt, scale) in viol_set:
        return "拒绝入库·55%五五开(违反铁律①)·须架构师改押方向(>55或<45)或标不锁", False
    return "已锁定待评", True


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="20260722"); a = ap.parse_args()
    d = a.date
    sys.stdout.reconfigure(encoding="utf-8")
    et = external_time()
    ext_iso = et.get("iso")

    def to_ts(iso):
        try:
            return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
        except Exception:
            return None
    ext_ts = to_ts(ext_iso)
    # batch_frame最新时间戳
    bfs = sorted(FDIR.glob(f"batch_frame_{d}_*.json"))
    bf_mtime = os.path.getmtime(bfs[-1]) if bfs else None

    # 载记分卡登记
    regp = PDCA / "locked_predictions_registry.json"
    reg = json.loads(regp.read_text(encoding="utf-8")) if regp.exists() else \
        {"架构师胜率累计": {"短期": {"命中": 0, "已评": 0}, "长期": {"命中": 0, "已评": 0}}, "已登记预测": []}
    key = lambda e: (e["标的"], e["尺度"], e["锁定日"], e.get("版本"))
    exist = {key(e) for e in reg["已登记预测"]}

    locks = []
    all_new = []
    rejected = []
    excluded = []
    per_file_time_ok = True
    for batch, fn in FILES:
        fp = FDIR / fn
        if not fp.exists():
            print("★缺文件·不编造:", fn); return 1
        j = json.loads(fp.read_text(encoding="utf-8"))
        lint = lint_file(str(fp))
        viol_set = {(v.get("标的"), v.get("尺度")) for v in lint["全部违规"] if str(v.get("铁律", "")).startswith("①")}
        f_mtime = os.path.getmtime(fp)
        lk = lock(j, d, label=f"baseline_{batch}")
        later_bf = (ext_ts is not None and bf_mtime is not None and ext_ts > bf_mtime)
        later_file = (ext_ts is not None and ext_ts > f_mtime)
        per_file_time_ok = per_file_time_ok and later_bf and later_file
        locks.append({"批次": batch, "文件": fn, "sha256": lk["sha256"], "链hash": lk["chain_hash"],
                      "时间认证": lk["time_status"], "外部时间": ext_iso,
                      "晚于batch_frame": later_bf, "晚于本文件": later_file,
                      "lint通过": lint["passed"], "违规数": lint["违规数"]})
        for p in j.get("预测", []):
            tgt = p.get("标的")
            short, _ = _blk(p, SHORT_KEYS)
            long_, _ = _blk(p, LONG_KEYS)
            for scale, blk in [("短期", short), ("长期", long_)]:
                if not blk:
                    continue
                status, in_denom = classify_entry(blk.get("方向"), viol_set, tgt, scale)
                cd = blk.get("PDCA核对日")
                entry = {"标的": tgt, "尺度": scale, "锁定日": d, "版本": f"baseline_{batch}",
                         "方向": blk.get("方向"), "概率": blk.get("概率"),
                         "PDCA核对日": (str(cd)[:10] if cd and str(cd)[:2].isdigit() else cd),
                         "PDCA判据": ("押方向 vs 实际:方向对=命中" if scale == "短期"
                                    else "事件兑现日比 实际方向/目标 vs 押的方向·对=命中"),
                         "锁定sha256": lk["sha256"], "链hash": lk["chain_hash"], "时间认证": lk["time_status"],
                         "大白话四步": p.get("大白话四步", {}), "状态": status, "进胜率分母": in_denom}
                if key(entry) in exist:
                    continue
                if status.startswith("拒绝入库"):
                    rejected.append({"标的": tgt, "尺度": scale, "原因": status, "核对日": entry["PDCA核对日"]})
                    continue  # 拒绝入库:不进记分卡(锁文件已留审计)
                if not in_denom:
                    excluded.append({"标的": tgt, "尺度": scale, "状态": status})
                reg["已登记预测"].append(entry)
                exist.add(key(entry))
                all_new.append(entry)

    reg["更新"] = now()
    reg.setdefault("基线批次", []).append({"日期": d, "批次": ["候选", "持仓", "v2(软银/爱德万·542d742已锁)"],
                                       "锁定时间(外部)": ext_iso, "新登记": len(all_new)})

    # 统计(含既有v2)
    active = [e for e in reg["已登记预测"] if e.get("进胜率分母", True) and e.get("状态", "").startswith("已锁定")]
    short_denom = [e for e in active if e["尺度"] == "短期"]
    long_denom = [e for e in active if e["尺度"] == "长期"]
    v2_entries = [e for e in reg["已登记预测"] if str(e.get("版本", "")).lower() == "v2"]

    hit = reg["架构师胜率累计"]

    def rate(k):
        n = hit[k]["已评"]
        return (round(hit[k]["命中"] / n * 100, 1) if n else None)

    baseline = {
        "_说明": "35只预测基线锁定。候选7+持仓18两文件forecast_lock+v2(软银/爱德万542d742)纳入同一基线。三铁律校验:55%五五开拒绝入库·HII不锁/SpaceX不适用不进短期分母。",
        "date": d, "generated_at": now(), "外部权威时间(Google HTTP Date)": ext_iso, "时间源": et.get("source"),
        "★时间顺序断言": {"锁定外部时间": ext_iso,
                     "最新batch_frame": (datetime.fromtimestamp(bf_mtime, JST).isoformat(timespec="seconds") if bf_mtime else None),
                     "晚于batch_frame(15:15)": (ext_ts > bf_mtime if (ext_ts and bf_mtime) else None),
                     "晚于填写(各文件)": per_file_time_ok,
                     "结论": ("通过·锁定晚于batch_frame与填写" if per_file_time_ok else "★失败·时间顺序")},
        "锁定哈希(3源)": {"候选7": locks[0], "持仓18": locks[1],
                     "v2软银爱德万": {"sha256": (v2_entries[0]["锁定sha256"] if v2_entries else "542d742fc697..."), "说明": "第十轮已锁·纳入同一基线"}},
        "★注_持仓文件条数": "文件含18条(20持仓−软银−爱德万·后两者在v2)·派工单写16为口径差·如实以文件18为准",
        "进记分卡条数": {"本次新登记(候选+持仓compliant)": len(all_new),
                    "含v2共登记": len(reg["已登记预测"]),
                    "短期(进胜率分母·已锁定待评)": len(short_denom),
                    "长期(进胜率分母·已锁定待评)": len(long_denom)},
        "拒绝入库(55%五五开·须架构师改·未进记分卡)": rejected,
        "不进短期分母(记录但不算胜率)": excluded,
        "架构师短期预测胜率%": rate("短期"), "架构师长期预测胜率%": rate("长期"),
        "胜率说明": "分子=核对日已评命中·分母=进分母的已锁定条目。当前0已评→待核对日。拒绝入库/不锁/不适用 均不进分母。",
        "PDCA核对日总览": sorted({e["PDCA核对日"] for e in active if e.get("PDCA核对日")}, key=str),
    }
    FDIR.mkdir(parents=True, exist_ok=True)
    p1 = FDIR / f"locked_baseline_{d}.json"
    p1.write_text(json.dumps(baseline, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    regp.write_text(json.dumps(reg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    ok = True
    for p in (p1, regp):
        raw = p.read_bytes()
        try:
            json.load(open(p, encoding="utf-8")); jl = True
        except Exception as e:
            jl = False; ok = False; print("★json.load失败", p.name, e)
        print("wrote", p.name, len(raw), "字节·EFBFBD=", raw.count(b"\xef\xbf\xbd"), "·json.load通过=", jl)
    for lk in locks:
        print(f"锁定 {lk['批次']}: sha {lk['sha256'][:16]} · lint通过 {lk['lint通过']} · 违规 {lk['违规数']} · 晚于batch_frame {lk['晚于batch_frame']}")
    print("进记分卡新登记:", len(all_new), "· 短期分母", len(short_denom), "· 长期分母", len(long_denom))
    print("拒绝入库(55%):", [(r["标的"].split()[0], r["尺度"]) for r in rejected])
    print("不进短期分母:", [(e["标的"].split()[0], e["尺度"], e["状态"][:8]) for e in excluded])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
