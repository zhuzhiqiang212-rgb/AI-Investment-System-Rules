#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""锁定第一批架构师预测（派工单J-lock·2026-07-22）。
读 data/forecast/arch_predictions_{date}.json → forecast_lock(SHA256+Google HTTP Date外部时间戳+哈希链) →
① 断言锁定外部时间戳 晚于本文件mtime、晚于新闻源mtime(防事后编)
② 抽4条预测(软银短/长·爱德万短/长)+各自PDCA核对日 → 进记分卡登记
③ 到核对日自动提醒(--check-due)·累计架构师短期/长期预测胜率
输出 data/forecast/locked_{date}.json + 记分卡登记 data/pdca/locked_predictions_registry.json。
用法：python scripts/lock_predictions.py --date 20260722
      python scripts/lock_predictions.py --date 20260722 --check-due   # 列到期待核对的预测"""
import argparse, json, os, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
FDIR = ROOT / "data" / "forecast"
PDCA = ROOT / "data" / "pdca"
sys.path.insert(0, str(ROOT / "scripts"))


def now():
    return datetime.now(JST).isoformat(timespec="seconds")


def load_registry():
    p = PDCA / "locked_predictions_registry.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"_说明": "已锁定预测登记(记分卡)·append不覆盖·到核对日PDCA评判后累计架构师胜率。",
            "架构师胜率累计": {"短期": {"命中": 0, "已评": 0}, "长期": {"命中": 0, "已评": 0}},
            "已登记预测": []}


def check_due(reg, today):
    due = []
    for e in reg.get("已登记预测", []):
        cd = str(e.get("PDCA核对日", ""))[:10]
        try:
            dd = datetime.strptime(cd, "%Y-%m-%d").replace(tzinfo=JST)
            if dd <= today and e.get("状态") == "已锁定待评":
                due.append(e)
        except Exception:
            pass
    return due


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="20260722")
    ap.add_argument("--file", default=None, help="预测文件(默认arch_predictions_{date}.json;v2传v2文件)")
    ap.add_argument("--prev-sha", default=None, help="前身版本SHA(v2→标v1)")
    ap.add_argument("--check-due", action="store_true")
    ap.add_argument("--force", action="store_true", help="三铁律FAIL仍强锁(仅调试·正常不用)")
    a = ap.parse_args()
    d = a.date
    sys.stdout.reconfigure(encoding="utf-8")
    today = datetime.strptime(d, "%Y%m%d").replace(tzinfo=JST)

    reg = load_registry()
    if a.check_due:
        due = check_due(reg, datetime.now(JST))
        print("到期待核对预测:", len(due))
        for e in due:
            print("  ", e["标的"], e["尺度"], "核对日", e["PDCA核对日"])
        return 0

    predf = (Path(a.file) if a.file else (FDIR / f"arch_predictions_{d}.json"))
    if not predf.is_absolute():
        predf = (ROOT / predf)
    if not predf.exists():
        print("★架构师预测文件不存在·无法锁定(不编造):", predf); return 1
    arch = json.loads(predf.read_text(encoding="utf-8"))
    file_mtime = os.path.getmtime(predf)
    newsf = ROOT / "data" / "news" / f"daily_{d}.json"
    news_mtime = os.path.getmtime(newsf) if newsf.exists() else None
    version = (arch.get("预测", [{}])[0].get("版本") or "v1")

    # ── Q2/Q3 三铁律+大白话 硬校验(锁定前·不过不锁)──
    from prediction_lint import lint_file
    lint = lint_file(str(predf))
    print("三铁律校验:", predf.name, "· 版本", version, "· 通过", lint["passed"], "· 违规", lint["违规数"])
    for vv in lint["全部违规"][:10]:
        print("   ✗", vv.get("铁律"), vv.get("标的", ""), vv.get("命中"))
    if not lint["passed"] and not a.force:
        print("★三铁律未过·拒绝入库(要么押方向/剥买卖价/补大白话·要么标『不锁』)·未锁定"); return 2

    from forecast_lock import lock, external_time
    et = external_time()
    ext_iso = et.get("iso")
    lk = lock(arch, d, label=f"arch_pred_{version}_软银_爱德万")
    if not lk.get("ok"):
        print("★锁定失败:", lk); return 1
    ver_tag = ("含缺陷初版·保留" if str(version).lower() == "v1" else "修正版·押方向")

    # 时间顺序断言(锁定外部时间 晚于 本文件 & 新闻源)
    def to_ts(iso):
        try:
            return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
        except Exception:
            return None
    ext_ts = to_ts(ext_iso) if ext_iso else None
    later_than_file = (ext_ts is not None and ext_ts > file_mtime)
    later_than_news = (ext_ts is not None and news_mtime is not None and ext_ts > news_mtime)

    # 抽预测 + 核对日 → 登记(兼容v1/v2 schema)
    def pick(p, keys):
        for k in keys:
            if isinstance(p.get(k), dict) and p.get(k):
                return p[k]
        return {}
    SHORT = ["短期预判_押方向_锁定记分", "短期走势预判_锁定记分"]
    LONG = ["长期预判_锁定记分", "长期目标价_锁定记分"]
    registered = []
    for p in arch.get("预测", []):
        tgt = p.get("标的")
        st = pick(p, SHORT); lt = pick(p, LONG)
        bs = p.get("大白话四步", {})
        common = {"版本": version, "标注": ver_tag, "前身版本SHA": a.prev_sha,
                  "锁定sha256": lk["sha256"], "链hash": lk["chain_hash"], "时间认证": lk["time_status"],
                  "大白话四步": bs, "状态": "已锁定待评"}
        if st:
            registered.append({"标的": tgt, "尺度": "短期", "锁定日": d, "现价": p.get("现价"),
                               "方向": st.get("方向"), "预判": st.get("判断"), "具体": st.get("具体"),
                               "概率": st.get("概率"), "见分晓": st.get("见分晓"),
                               "PDCA核对日": str(st.get("PDCA核对日", ""))[:10] or st.get("PDCA核对日"),
                               "PDCA判据": st.get("PDCA判据", "核对日比 实际方向 vs 押的方向·对=命中"),
                               **common})
        if lt:
            registered.append({"标的": tgt, "尺度": "长期", "锁定日": d, "现价": p.get("现价"),
                               "方向": lt.get("方向"), "依据未来事件": lt.get("依据未来事件", lt.get("依据的未来事件(非过去财报)")),
                               "目标价": lt.get("目标价", lt.get("目标价框架")), "概率": lt.get("概率"),
                               "见分晓": lt.get("见分晓"), "PDCA核对日": lt.get("PDCA核对日"),
                               "PDCA判据": "事件兑现日比 实际 vs 目标价+事件是否发生·命中=事件发生且到目标价",
                               **common})

    # 若锁v2:先给已登记的v1条目打标『含缺陷初版·保留』(不删·不改其SHA/内容·仅加注解)
    if str(version).lower() != "v1":
        for e in reg["已登记预测"]:
            if not e.get("版本"):  # 第9轮锁的v1无版本标记
                e["版本"] = "v1"
                e["标注"] = "含缺陷初版·保留(不删)"
                e["缺陷"] = ["短期五五开(违反铁律①)", "软银短期混入买卖价6300-6600/5500(违反铁律②)", "无大白话四步"]
        # 演变链留档
        reg.setdefault("演变链", []).append({
            "from": "v1", "from_sha": a.prev_sha, "to": version, "to_sha": lk["sha256"],
            "触发原因": (arch.get("演变链说明", {}) or {}).get("v2触发原因", "三铁律重出"),
            "时间(外部认证)": ext_iso, "原始v1处置": "不删·保留记分(对照『含缺陷初版』)"})

    # 进记分卡登记(append·去重按标的+尺度+锁定日+版本)
    key = lambda e: (e["标的"], e["尺度"], e["锁定日"], e.get("版本"))
    exist = {key(e) for e in reg["已登记预测"]}
    added = [e for e in registered if key(e) not in exist]
    reg["已登记预测"].extend(added)
    reg["更新"] = now()
    hit = reg["架构师胜率累计"]

    def rate(k):
        n = hit[k]["已评"]
        return (round(hit[k]["命中"] / n * 100, 1) if n else None)

    # 到期提醒
    due = check_due(reg, today)
    upcoming = sorted([e["PDCA核对日"] for e in reg["已登记预测"] if e.get("状态") == "已锁定待评"],
                      key=lambda x: str(x)[:10])

    locked_doc = {
        "_说明": f"架构师预测 {version} 已forecast_lock正式锁定(J-lock)。SHA256+Google HTTP Date外部时间戳+哈希链·不可事后改。",
        "date": d, "generated_at": now(), "版本": version, "版本标注": ver_tag, "前身版本SHA": a.prev_sha,
        "三铁律校验": {"通过": lint["passed"], "违规数": lint["违规数"], "版本链": lint["版本链"]["说明"],
                   "校验项": "①禁五五开概率45-55 ②禁买卖挂单价/加减仓 ③版本链v1→v2 +Q3大白话四步"},
        "演变链v1到v2": (reg.get("演变链", [])[-1] if str(version).lower() != "v1" and reg.get("演变链") else "本次为v1·无前身"),
        "锁定对象": str(predf.relative_to(ROOT)).replace("\\", "/"),
        "锁定结果": {"sha256": lk["sha256"], "chain_hash": lk["chain_hash"], "snapshot": lk["snapshot"],
                 "时间认证": lk["time_status"], "外部权威时间(Google HTTP Date)": ext_iso, "时间源": et.get("source")},
        "★防事后编_时间顺序断言": {
            "锁定外部时间": ext_iso,
            "本文件mtime": datetime.fromtimestamp(file_mtime, JST).isoformat(timespec="seconds"),
            "新闻源mtime": (datetime.fromtimestamp(news_mtime, JST).isoformat(timespec="seconds") if news_mtime else None),
            "锁定晚于本文件": later_than_file, "锁定晚于新闻源": later_than_news,
            "结论": ("通过·锁定时间晚于预测文件与新闻(防事后编)" if (later_than_file and later_than_news) else "★失败·时间顺序不成立")},
        "登记4条预测": registered,
        "记分卡登记": {"本次新登记": len(added), "登记表": "data/pdca/locked_predictions_registry.json",
                   "架构师短期胜率%": rate("短期"), "架构师长期胜率%": rate("长期"),
                   "胜率说明": "分子=核对日已评命中·分母=已评总。当前0已评→待到核对日。"},
        "PDCA核对日总览": [{"标的": e["标的"], "尺度": e["尺度"], "核对日": e["PDCA核对日"], "状态": e["状态"]} for e in registered],
        "到期提醒": {"今日": d, "到期待核对": len(due), "最近核对日": (upcoming[0] if upcoming else None),
                 "提醒机制": "跑 python scripts/lock_predictions.py --check-due 列到期项;到核对日评判后 命中/未命中 累加进胜率"},
    }
    FDIR.mkdir(parents=True, exist_ok=True)
    p1 = FDIR / f"locked_{d}.json"
    p1.write_text(json.dumps(locked_doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    PDCA.mkdir(parents=True, exist_ok=True)
    p2 = PDCA / "locked_predictions_registry.json"
    p2.write_text(json.dumps(reg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    ok = True
    for p in (p1, p2):
        raw = p.read_bytes()
        try:
            json.load(open(p, encoding="utf-8")); jl = True
        except Exception as e:
            jl = False; ok = False; print("★json.load失败", p.name, e)
        print("wrote", p.name, len(raw), "字节·EFBFBD=", raw.count(b"\xef\xbf\xbd"), "·json.load通过=", jl)
    print("锁定SHA256:", lk["sha256"])
    print("链hash:", lk["chain_hash"], "·时间认证:", lk["time_status"])
    print("外部时间:", ext_iso, "·晚于本文件:", later_than_file, "·晚于新闻:", later_than_news)
    print("登记预测", len(registered), "条·新登记", len(added), "·核对日:",
          [(e["标的"].split()[0], e["尺度"], e["PDCA核对日"]) for e in registered])
    print("架构师短期胜率%:", rate("短期"), "·长期胜率%:", rate("长期"), "(0已评→待积累)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
