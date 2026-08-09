# -*- coding: utf-8 -*-
"""★★★轮221 补漏:锁定期闸(必填校验·不是验证体系)。堵『锁定预测时不写锁定价→结算基准是活的』的敞口。
★锁定预测时【必填】:标的/尺度/方向/概率/锁定价/PDCA核对日/PDCA判据·缺任一→拒绝锁定(不写registry·报缺哪个)。
★特别:锁定价 必须【数值】·PDCA核对日 必须【日期】(YYYY-MM-DD 或 YYYYMMDD)·不得 null/文字。
★另:--health 对 registry 现存条目跑体检→registry_health_{当日}.json(缺锁定价/核对日非日期)·【只报不改】。"""
import sys, json, time, re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ["标的", "尺度", "方向", "概率", "锁定价", "PDCA核对日", "PDCA判据"]


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _to_date(v):
    if not isinstance(v, str):
        return None
    s = v.strip().replace("/", "-")
    if re.fullmatch(r"\d{8}", s):
        s = "%s-%s-%s" % (s[:4], s[4:6], s[6:8])
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _is_date(v):
    return _to_date(v) is not None


def _is_tradingday(v):
    """★轮222:必须是交易日(排周末·美股/日股同)。节假日先不做(不扩建)。返回 (是交易日, 说明)。"""
    dt = _to_date(v)
    if dt is None:
        return False, "非日期"
    wd = dt.weekday()   # 0=一…5=六 6=日
    if wd == 5:
        return False, "周六(非交易日·锁那刻就无法执行)"
    if wd == 6:
        return False, "周日(非交易日·锁那刻就无法执行)"
    return True, "交易日"


def _lock_price(p):
    """锁定价字段:优先『锁定价』·兼容旧schema『现价』。"""
    return p.get("锁定价") if p.get("锁定价") is not None else p.get("现价")


def validate_lock(pred):
    """校验一条待锁定预测。返回 (通过, 缺失/非法列表)。"""
    errs = []
    for f in REQUIRED:
        v = _lock_price(pred) if f == "锁定价" else pred.get(f)
        if v is None or (isinstance(v, str) and not v.strip()):
            errs.append("缺[%s]" % f)
    lp = _lock_price(pred)
    if lp is not None and not _is_num(lp):
        errs.append("锁定价非数值(=%r)" % lp)
    cd = pred.get("PDCA核对日") or pred.get("verdict_date")
    if cd is not None:
        if not _is_date(cd):
            errs.append("到期日非日期格式(=%r)" % cd)
        else:
            ok_td, why = _is_tradingday(cd)
            if not ok_td:
                errs.append("到期日非交易日:%s(=%r)" % (why, cd))   # ★轮222 COIN那个错
    # ★轮342乙3:见分晓日↔尺度间隔闸(0-30d≥20天·长期≥80天)——源头挡『0~30天判断却设锁后第2天核对』(COIN那类)。
    _hz = pred.get("尺度") or pred.get("horizon")
    _lockday = pred.get("锁定日") or pred.get("locked_at") or date.today().isoformat()
    if cd is not None and _is_date(cd) and _hz:
        try:
            import horizon_verdict_match_gate as _hvm
            _ok, _why = _hvm.check_lock(_hz, _lockday, cd)
            if not _ok:
                errs.append(_why)
        except Exception as _e:
            errs.append("间隔闸未能运行(%s)·请人工核见分晓日与尺度是否匹配" % type(_e).__name__)
    return (len(errs) == 0), errs


def health_check(dd):
    """★轮222 双源体检·只报不改。pdca源查缺锁定价/核对日;forecast源查verdict_date日期+交易日(index无价字段→单列说明)。"""
    import registry_sources as rs
    rows = []
    total = 0
    for e in rs.load_all():
        total += 1
        issues = []
        if e["源"] == "pdca":
            if not _is_num(e.get("锁定价")):
                issues.append("缺锁定价")
        # 到期日日期+交易日(两源都查)
        dv = e.get("到期日")
        if not _is_date(dv):
            issues.append("到期日非日期(=%r)" % dv)
        else:
            ok_td, why = _is_tradingday(dv)
            if not ok_td:
                issues.append("到期日非交易日:%s(=%r)" % (why, dv))
        if issues:
            rows.append({"源": e["源"], "idx": e["idx"], "标的": e["标的"], "尺度": e["尺度"],
                         "状态": e["状态"], "问题": issues})
    def cnt(src, kw):
        return sum(1 for r in rows if r["源"] == src and any(kw in x for x in r["问题"]))
    out = {"_说明": "★轮221/222 双源registry体检(锁定期闸)·【只报不改】·补哪条怎么补是Opus5判断。forecast源index不存锁定价(在detail文件)→本体检不判forecast缺价。",
           "date": "%s-%s-%s" % (dd[:4], dd[4:6], dd[6:8]), "as_of": time.strftime("%Y-%m-%d %H:%M JST"),
           "总条数": total,
           "pdca源": {"缺锁定价": cnt("pdca", "缺锁定价"), "到期日非日期": cnt("pdca", "非日期"), "到期日非交易日": cnt("pdca", "非交易日")},
           "forecast源": {"到期日非日期": cnt("forecast", "非日期"), "到期日非交易日": cnt("forecast", "非交易日")},
           "问题清单": rows}
    (ROOT / "data/pdca").mkdir(parents=True, exist_ok=True)
    (ROOT / "data/pdca" / ("registry_health_%s.json" % dd)).write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    dd = time.strftime("%Y%m%d")
    for i, a in enumerate(sys.argv):
        if a == "--date" and i + 1 < len(sys.argv):
            dd = sys.argv[i + 1].replace("-", "")
    if "--health" in sys.argv:
        o = health_check(dd)
        print("双源体检: 共%d条 · pdca[缺锁定价%d/非日期%d/非交易日%d] · forecast[非日期%d/非交易日%d]"
              % (o["总条数"], o["pdca源"]["缺锁定价"], o["pdca源"]["到期日非日期"], o["pdca源"]["到期日非交易日"],
                 o["forecast源"]["到期日非日期"], o["forecast源"]["到期日非交易日"]))
        for r in o["问题清单"]:
            if any("非交易日" in x or "非日期" in x for x in r["问题"]):
                print("  [%s] %s %s · %s" % (r["源"], r["标的"], r["尺度"], "; ".join(r["问题"])))
    else:
        # 自测:合规PASS·缺锁定价REJECT·核对日文字REJECT·★周六REJECT(COIN那个错)·★轮342间隔REJECT
        # 锁定日显式给定→间隔判定不随运行日漂移(短期0-30d需≥20天;08-19-07-30=20天·合规)
        good = {"标的": "测试X", "尺度": "短期", "方向": "偏上行", "概率": "约60%", "锁定价": 100.0,
                "锁定日": "2026-07-30", "PDCA核对日": "2026-08-19", "PDCA判据": "方向对=命中"}
        bad1 = dict(good); bad1["锁定价"] = None
        bad2 = dict(good); bad2["PDCA核对日"] = "1-2周后"
        bad3 = dict(good); bad3["PDCA核对日"] = "2026-08-01"   # ★2026-08-01是周六
        bad4 = dict(good); bad4["PDCA核对日"] = "2026-08-03"   # ★轮342:短期却锁后第4天核对(第一三共那类)→间隔闸REJECT
        print("合规(短期20天)→", validate_lock(good))
        print("缺锁定价→", validate_lock(bad1))
        print("核对日文字→", validate_lock(bad2))
        print("核对日周六→", validate_lock(bad3))
        print("★短期间隔仅4天→", validate_lock(bad4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
