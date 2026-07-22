#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""预测记分卡·双尺度PDCA（派工单G3·2026-07-22）。架构师的双尺度预判→forecast_lock(SHA256+外部时间)→进记分卡·到期PDCA·累计架构师短/长期胜率。
流程:①架构师在gate3_v2填预判(短期预判/未来目标价+事件+概率+见分晓时间)→②本脚本抽出『已填』的锁定(不可篡改)→③记进记分卡带见分晓日→
     ④短期:锁定+N交易日后PDCA(比现价vs预判);长期:事件兑现日PDCA→⑤累计架构师短期胜率/长期胜率。
★只锁『已填』的真预判(不以★待开头);空槽=待架构师填·不锁不计。Code不代填预测。
用法：python scripts/forecast_pdca.py --date 20260722 --short-days 14
      python scripts/forecast_pdca.py --date 20260722 --resolve   # 到期PDEA评判(需现价/事件核实)"""
import argparse, json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "data" / "screen"
PDCA = ROOT / "data" / "pdca"
JST = timezone(timedelta(hours=9))
sys.path.insert(0, str(ROOT / "scripts"))


def now():
    return datetime.now(JST).isoformat(timespec="seconds")


def is_filled(v):
    """真被架构师填了(非空槽)。空槽以★待/待架构师 开头。"""
    if v is None:
        return False
    s = str(v)
    return not (s.startswith("★待") or s.startswith("待架构师") or "待架构师填" in s or s.strip() in ("", "★待"))


def lock_prediction(pred_obj, date, label=""):
    """把一条已填预判 forecast_lock(SHA256+外部时间·不可篡改)→返回sha/chain。"""
    from forecast_lock import lock  # 复用底座:lock(dict, date, label)
    try:
        return lock(pred_obj, date, label)
    except Exception as e:
        return {"ok": False, "err": str(e)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="20260722")
    ap.add_argument("--short-days", type=int, default=14, help="短期预判见分晓天数(≈10交易日)")
    ap.add_argument("--resolve", action="store_true", help="到期PDCA评判模式")
    a = ap.parse_args()
    d = a.date
    sys.stdout.reconfigure(encoding="utf-8")
    lock_day = datetime.strptime(d, "%Y%m%d").replace(tzinfo=JST)
    short_due = (lock_day + timedelta(days=a.short_days)).strftime("%Y-%m-%d")

    g3v2 = json.loads((S / f"gate3_v2_{d}.json").read_text(encoding="utf-8"))
    rows = g3v2["逐只(15)"]

    entries = []
    locked_n = 0
    pending_n = 0
    for c, r in rows.items():
        short_pred = r.get("短期走势", {}).get("②预判_架构师空槽")
        fut = r.get("未来驱动_估值(★trailing_PE判贵已禁用)")
        # 短期预判条目
        st_filled = is_filled(short_pred)
        st = {"code": c, "尺度": "短期", "预判内容": short_pred,
              "锁定日": d, "见分晓日": short_due, "见分晓依据": f"锁定+{a.short_days}日(≈10交易日)",
              "PDCA判据": "到期比 现价 vs 预判方向/目标位·命中=方向对且到位",
              "状态": "待架构师填·未锁定"}
        if st_filled:
            lk = lock_prediction({"code": c, "尺度": "短期", "预判": short_pred, "锁定日": d, "见分晓日": short_due}, d)
            st["状态"] = "已锁定待评"; st["锁定sha256"] = lk.get("sha256"); st["链hash"] = lk.get("chain_hash"); st["时间认证"] = lk.get("time_status")
            locked_n += 1
        else:
            pending_n += 1
        entries.append(st)
        # 长期预判条目(仅未来驱动的有)
        if fut:
            tgt = fut.get("①未来目标价"); ev = fut.get("②依据的未来事件", {}).get("架构师填")
            prob = fut.get("③兑现概率"); due = fut.get("④见分晓时间")
            lt_filled = is_filled(tgt) and is_filled(ev) and is_filled(due)
            lt = {"code": c, "尺度": "长期(事件兑现)", "目标价": tgt, "未来事件": ev, "兑现概率": prob,
                  "见分晓时间": due, "PDCA判据": "事件兑现日比 实际 vs 目标价+事件是否发生·命中=事件发生且到目标价",
                  "状态": "待架构师填·未锁定"}
            if lt_filled:
                lk = lock_prediction({"code": c, "尺度": "长期", "目标价": tgt, "事件": ev, "概率": prob, "见分晓": due, "锁定日": d}, d)
                lt["状态"] = "已锁定待评"; lt["锁定sha256"] = lk.get("sha256"); lt["链hash"] = lk.get("chain_hash")
                locked_n += 1
            else:
                pending_n += 1
            entries.append(lt)

    # 胜率累计(读历史已评条目·本轮无已评→0/0)
    hist = PDCA / "prediction_hitrate.json"
    hit = {"短期": {"命中": 0, "已评": 0}, "长期": {"命中": 0, "已评": 0}}
    if hist.exists():
        try:
            hit = json.loads(hist.read_text(encoding="utf-8")).get("架构师胜率累计", hit)
        except Exception:
            pass

    def rate(k):
        n = hit[k]["已评"]
        return (round(hit[k]["命中"] / n * 100, 1) if n else None)

    doc = {
        "_说明": "预测记分卡·双尺度PDCA(G3)。架构师预判→forecast_lock(不可篡改)→到期PDCA→累计架构师短/长期胜率。★Code只锁已填真预判·空槽待架构师·不代填。",
        "date": d, "generated_at": now(),
        "基线快照(gate3_v2已锁)": {"文件": f"data/forecast/forecast_{d}_8ec4f8587a0f.json", "sha256": "8ec4f8587a0f785810a159a38ef3ed762736d319b667e4fcbe3fe42580a9c700",
                            "说明": "本次gate3_v2结构已forecast_lock·外部时间认证·防事后回改"},
        "本轮统计": {"预判条目总数": len(entries), "已锁定(架构师已填)": locked_n, "待架构师填(空槽·未锁)": pending_n},
        "架构师胜率累计": hit,
        "架构师短期预测胜率%": rate("短期"),
        "架构师长期预测胜率%": rate("长期"),
        "胜率说明": "分子=已评命中·分母=已评总。到期(短期见分晓日/长期事件日)跑 --resolve 评判后累加。当前0已评→胜率待积累。",
        "PDCA流程": ["①架构师在gate3_v2填预判", "②本脚本锁定已填(SHA256+外部时间)", "③记见分晓日",
                   "④到期跑--resolve比实际", "⑤命中率累加进本表"],
        "预判条目": entries,
    }
    PDCA.mkdir(parents=True, exist_ok=True)
    p = PDCA / f"prediction_scorecard_{d}.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    # 胜率累计文件(持久·首建)
    if not hist.exists():
        hist.write_text(json.dumps({"架构师胜率累计": hit, "更新": now()}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    raw = p.read_bytes()
    try:
        json.load(open(p, encoding="utf-8")); jl = True
    except Exception as e:
        jl = False; print("★json.load失败", e)
    print("wrote", p.name, len(raw), "字节·EFBFBD=", raw.count(b"\xef\xbf\xbd"), "·json.load通过=", jl)
    print(f"预判条目{len(entries)}·已锁定(架构师已填){locked_n}·待架构师填{pending_n}")
    print("架构师短期胜率%:", rate("短期"), "·长期胜率%:", rate("长期"), "(0已评→待积累)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
