# -*- coding: utf-8 -*-
"""Z4·缺口分两段(轮62口径·轮67接进管线)。已算清=特+A级Σ贡献pp+权重;未算清=B+C级权重(无可用估值锚);退出=★退出标的。
★点值口径:E[上行]=compute_expected_upside(用 point_value·非区间中值)。输出 data/risk/z4_two_segment_{date}.json 供 render_3layer 第一屏。
用法: python scripts/z4_two_segment_build.py --date 20260731 [--forecast-date 20260730]
  --date        : 生产日(紧凑)·读 daily_scan_{date}/target_gap_{date}
  --forecast-date: forecast 日(紧凑)·跨市场收盘日复用前一交易日 forecast;缺省=自动取最新工作版 forecast_YYYY-MM-DD。
"""
import json, sys, argparse, glob, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from target_gap import compute_expected_upside
FX = 163.425


def _resolve_forecast_date(pipeline_date):
    cands = glob.glob(str(ROOT / "data" / "forecast" / "forecast_*.json"))
    dates = [m.group(1) for p in cands
             if (m := re.match(r"forecast_(\d{4}-\d{2}-\d{2})\.json$", Path(p).name))]
    return max(dates).replace("-", "") if dates else pipeline_date


def build(date, fdate):
    fdh = f"{fdate[:4]}-{fdate[4:6]}-{fdate[6:]}"
    tg = json.loads((ROOT / "data/target" / f"target_gap_{date}.json").read_text(encoding="utf-8"))
    fc = json.loads((ROOT / "data/forecast" / f"forecast_{fdh}.json").read_text(encoding="utf-8"))
    acc_map = {"FUTU": "富途", "SBI": "SBI"}
    f1y = {(acc_map.get(f.get("account"), f.get("account")), f.get("ticker")): f
           for f in fc["forecasts"] if f.get("horizon") == "1y"}
    out = {"_说明": "缺口分两段(Z4·轮62口径·轮67进管线)。★不给混合总数·不出现单一距+40%缺口。"
                    "已算清=特+A级Σ贡献(点值口径);未算清=B+C级权重(无可用估值锚);退出=★退出标的。"
                    "取价/市值/等级均取自 target_gap_{date}(管线必产·单一真相源)·点值口径 E[上行]=compute_expected_upside(用forecast scenarios)。",
           "date": f"{date[:4]}-{date[4:6]}-{date[6:]}", "forecast_date": fdh, "账户": {}}
    for a_cn in ("富途", "SBI"):
        cash = tg.get(a_cn, {}).get("现金_USD") or 0
        holds, total_mv = [], 0.0
        for r in tg.get(a_cn, {}).get("逐只(按贡献pp降序)", []):
            code = r["code"]
            px = r.get("当日价(E上行分母)")           # ★轮67:取自 target_gap(管线必产)·非 daily_scan 非标准段
            mv = r.get("market_value_usd")            # target_gap 已折 USD
            if px is None or mv is None:
                continue
            total_mv += mv
            holds.append((code, r.get("name"), px, mv, r.get("参数出处等级")))
        A = total_mv + cash
        clear = {"贡献pp": 0.0, "权重": 0.0, "只": []}
        unclear = {"权重": 0.0, "只": []}
        exit_ = {"权重": 0.0, "只": []}
        for code, name, px, mv, grade_tg in holds:
            w = mv / A if A else 0
            f = f1y.get((a_cn, code)); grade = grade_tg or (f or {}).get("参数出处等级")
            if f and f.get("★退出"):
                exit_["权重"] += w
                exit_["只"].append({"code": code, "name": name, "权重pct": round(w * 100, 2)})
            elif grade in ("特级", "A", "A-") and f:
                _, eu = compute_expected_upside(f["scenarios"], px)
                c = round(w * eu, 3); clear["贡献pp"] += c; clear["权重"] += w
                clear["只"].append({"code": code, "name": name, "等级": grade, "权重pct": round(w * 100, 2),
                                    "E上行pct": eu, "贡献pp": c})
            else:
                unclear["权重"] += w
                unclear["只"].append({"code": code, "name": name, "等级": grade, "权重pct": round(w * 100, 2),
                                      "PE来源": (f or {}).get("PE来源"), "★不出收益": "无可用估值锚"})
        out["账户"][a_cn] = {
            "A_USD": round(A, 2),
            "①已算清(特+A级)": {"覆盖权重pct": round(clear["权重"] * 100, 2), "Σ贡献pp": round(clear["贡献pp"], 2),
                             "只": sorted(clear["只"], key=lambda x: -x["贡献pp"])},
            "②未算清(B+C级)": {"权重合计pct": round(unclear["权重"] * 100, 2), "说明": "这部分无法给出预期收益(无可用估值锚)", "只": unclear["只"]},
            "退出(第一三共)": {"权重pct": round(exit_["权重"] * 100, 2), "只": exit_["只"]},
            "★缺口口径": "已算清 %.1f%% 权重贡献 %.2f pp;未算清 %.1f%% 权重尚无可用估值锚(★不相加·不出单一缺口数)" % (
                clear["权重"] * 100, clear["贡献pp"], unclear["权重"] * 100),
        }
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--forecast-date", default=None)
    a = ap.parse_args()
    fdate = a.forecast_date or _resolve_forecast_date(a.date)
    out = build(a.date, fdate)
    p = ROOT / "data" / "risk" / f"z4_two_segment_{a.date}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    b = p.read_bytes(); json.loads(b.decode())
    print("[z4_two_segment] %s (forecast %s) → %s · 乱码%d" % (a.date, fdate, p.name, b.count(b"\xef\xbf\xbd")))
    for a_cn in ("富途", "SBI"):
        d = out["账户"].get(a_cn, {})
        print("  %s:" % a_cn, d.get("★缺口口径", "(无)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
