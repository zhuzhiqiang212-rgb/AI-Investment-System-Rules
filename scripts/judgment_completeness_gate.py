# -*- coding: utf-8 -*-
"""★轮98建/轮99 NE 重写 L19 判断完整性闸——★三态判定(守 CLAUDE.md §5.4)。
★NE1修:『非当日』≠『未做』(第五次同型故障已纠)——有效期只看【见分晓日期数值比较】·不看是否当日;与PDCA锁定机制兼容(07-22锁定见分晓在2027仍有效)。
三态(NE2):
 ①【判断已做·沿用】该只有【见分晓日未过】的锁定预测·且当日无结构化触发 → 已做(标沿用+见分晓日)
 ②【★需复核】有锁定预测·但当日该只被【结构化触发】(|涨跌幅|>阈值 或 新闻命中该ticker) → 逼Opus5响应(确认沿用or改判)
 ③【判断未做】无任何见分晓日未过的锁定预测 → 未做
★真偷懒=有新事件却不复核预测·不是没每天重打同一句话。★触发条件全结构化·不靠自由文本关键词(§5.4)。
★Code不替Opus5编判断——『需复核』的响应是判断岗的活。未做>50%→第4步FAIL。"""
import sys, json, argparse
from datetime import date as _date
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
# ★轮100 NG5:触发阈值按板块波动率分层(存储/AI硬件±8%·其余±5%)——高波动标的±5%几乎天天触发·真信号被噪声淹没。
CHG_TH_DEFAULT = 5.0
CHG_TH_HIVOL = 8.0
HIVOL_TICKERS = {"US.SNDK", "JP.6857", "US.NVDA", "US.AVGO", "US.TSM", "US.MSTR", "US.COIN"}  # 存储/AI硬件/半导体/加密(高波动)


def _chg_threshold(tk):
    return CHG_TH_HIVOL if tk in HIVOL_TICKERS else CHG_TH_DEFAULT


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _valid_locked(dh):
    """锁定预测登记表→{ticker: [见分晓日未过的条目]}。★有效期只看 verdict_date 数值比较·非当日(NE1·§5.4)。"""
    reg = _rj(ROOT / "data/forecast/locked_predictions_registry.json")
    recs = reg.get("已登记预测", []) or []
    today = _date(*[int(x) for x in dh.split("-")])
    out = {}
    for x in recs:
        tk = x.get("ticker") or x.get("code")
        vd = x.get("verdict_date") or x.get("见分晓日")
        if not (tk and vd):
            continue
        try:
            vdd = _date(*[int(y) for y in str(vd).split("-")])
        except Exception:
            continue
        if vdd >= today:   # 见分晓日未过=在有效期(★数值比较·不看是否当日)
            out.setdefault(tk, []).append({"horizon": x.get("horizon"), "verdict_date": vd, "locked_at": x.get("locked_at")})
    return out


def _triggers(dc, dh):
    """当日【结构化触发】:①|涨跌幅|>阈值(daily_scan数值) ②新闻命中该ticker(evidence_chain links含名/代码)。★不靠自由文本关键词。"""
    scan = _rj(ROOT / "data/market" / f"daily_scan_{dc}.json")
    chg = {}
    for q in ((scan.get("items", {}).get("1_当日20只价", {}) or {}).get("逐只", []) or []):
        c = q.get("chg_pct")
        if isinstance(c, (int, float)):
            chg[q.get("code")] = (c, q.get("name"))
    daily = _rj(ROOT / "data/evidence_chain" / f"daily_{dc}.json")
    links_txt = json.dumps(daily.get("links", []), ensure_ascii=False)
    return chg, links_txt


def check(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    prod = _rj(ROOT / "data/reports" / f"production_{dc}.json")
    holds = [(h.get("symbol"), h.get("name")) for h in prod.get("holdings", [])]
    locked = _valid_locked(dh)
    chg, links_txt = _triggers(dc, dh)
    # ★NG2:读第4步判断响应(Opus5)——需复核是否已响应(判错/沿用)。★Code只登记响应状态·不编判断。
    jf = _rj(ROOT / "data/forecast" / f"judgment_{dh}.json")
    responded = {}
    for r in (jf.get("复核", []) or []):
        tk = r.get("ticker") or r.get("code")
        if tk:
            concl = str(r.get("★结论") or r.get("★★结论") or r.get("结论") or "")
            # ★沿用先判(『未证伪』含『证伪』易误判)·再判错
            if "沿用" in concl or "未证伪" in concl:
                responded[tk] = "沿用"
            elif "判错" in concl or "被证伪" in concl or "证伪" in concl:
                responded[tk] = "判错"
            else:
                responded[tk] = "已响应"
    done, review, undone = [], [], []
    for sym, nm in holds:
        lk = locked.get(sym, [])
        if not lk:
            undone.append({"code": sym, "名称": nm, "原因": "无见分晓日未过的锁定预测(NE2-3)"})
            continue
        # 结构化触发判定(★NG5阈值分层)
        trig = []
        th = _chg_threshold(sym)
        c = chg.get(sym)
        if c and abs(c[0]) > th:
            trig.append("当日涨跌幅 %+.2f%%（|>%.0f%%阈值·%s|）" % (c[0], th, "高波动±8%" if sym in HIVOL_TICKERS else "常规±5%"))
        if sym and (sym in links_txt or (nm and str(nm) in links_txt)):
            trig.append("新闻命中该标的(evidence_chain links)")
        vds = "、".join("%s见分晓%s" % (e.get("horizon"), e.get("verdict_date")) for e in lk)
        if trig:
            review.append({"code": sym, "名称": nm, "触发原因": trig, "锁定": vds,
                           "★Opus5响应": responded.get(sym, "★仍挂·未响应")})
        else:
            done.append({"code": sym, "名称": nm, "沿用": "锁定预测在有效期·%s" % vds})
    n = len(holds) or 1
    pct_undone = len(undone) / n * 100
    n_pending = sum(1 for x in review if "仍挂" in str(x.get("★Opus5响应", "")))
    n_wrong = sum(1 for x in review if x.get("★Opus5响应") == "判错")
    n_keep = sum(1 for x in review if x.get("★Opus5响应") == "沿用")
    return {
        "_说明": "★轮99 NE L19 三态判定。①已做·沿用(见分晓未过的锁定预测·无触发) ②★需复核(有锁定但当日结构化触发·逼Opus5响应) ③判断未做(无有效期内预测)。★有效期只看见分晓日(§5.4·非当日≠未做)·触发全结构化·Code不替Opus5编。",
        "date": dh, "持仓数": len(holds),
        "①判断已做·沿用": len(done), "②★需复核": len(review), "③判断未做": len(undone),
        "★需复核已响应": len(review) - n_pending, "★需复核仍挂": n_pending,
        "★判错(被证伪)": n_wrong, "★沿用(未证伪)": n_keep,
        "判断未做占比pct": round(pct_undone, 1),
        "★第4步FAIL(未做>50%)": pct_undone > 50,
        "★需复核清单(Opus5须响应·触发原因)": review,
        "判断未做清单": undone,
        "已做沿用清单": done,
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out = check(a.date)
    p = ROOT / "data" / "pdca" / f"judgment_completeness_{a.date.replace('-', '')}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    b = p.read_bytes(); json.loads(b.decode())
    print("[L19 判断完整性·三态] %s · 持仓%d · ①已做沿用%d · ②★需复核%d · ③判断未做%d(%.0f%%) · 乱码%d" % (
        a.date, out["持仓数"], out["①判断已做·沿用"], out["②★需复核"], out["③判断未做"], out["判断未做占比pct"], b.count(b"\xef\xbf\xbd")))
    for x in out["★需复核清单(Opus5须响应·触发原因)"]:
        print("  ⚠需复核 %s %s ← %s" % (x["code"], x["名称"], "；".join(x["触发原因"])))
    for x in out["判断未做清单"]:
        print("  ✗未做 %s %s（%s）" % (x["code"], x["名称"], x["原因"]))
    if out["★第4步FAIL(未做>50%)"]:
        print("  ★第4步 FAIL:判断未做 %.0f%% >50%%" % out["判断未做占比pct"]); return 6
    print("  第4步判断完整性 PASS(未做≤50%·但★需复核项须Opus5响应)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
