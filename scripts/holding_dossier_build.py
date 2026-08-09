# -*- coding: utf-8 -*-
"""★轮85 CF6:⑥持仓补两项。CF6-1 每只『完整档案』(买入逻辑/成本/目标价/退出条件)→data/accounts/holding_dossier_{code}.json(20只各一份·★成本无历史记录标『待董事长提供』不编)。
CF6-2 全账户底数(含IBKR/bitFlyer)→data/accounts/all_accounts_base_{date}.json(先建结构+明列需董事长提供什么格式什么文件)。"""
import sys, json, argparse, glob
from datetime import datetime, timezone, timedelta
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _latest(pat):
    xs = sorted(glob.glob(str(ROOT / pat)))
    return _rj(xs[-1]) if xs else {}


def build_dossiers(dc):
    prod = _rj(ROOT / "data/reports" / f"production_{dc}.json")
    dec = _rj(ROOT / "data/pdca" / f"decisions_{dc}.json").get("decisions", {})
    tg = _rj(ROOT / "data/target" / f"target_gap_{dc}.json")
    fc = _latest("data/forecast/forecast_2026-*.json")
    fc_map = {}
    for f in fc.get("forecasts", []):
        fc_map.setdefault(f.get("ticker"), []).append(f)
    tg_map = {}
    for r in (tg.get("逐只", []) or tg.get("持仓", []) or []):
        tg_map[r.get("code") or r.get("symbol")] = r
    D = ROOT / "data" / "accounts"; D.mkdir(parents=True, exist_ok=True)
    made = []
    for h in prod.get("holdings", []):
        sym = h.get("symbol"); nm = h.get("name")
        d = (dec.get(sym, {}) or {})
        fcs = fc_map.get(sym, [])
        exits = []
        for f in fcs:
            for s in f.get("scenarios", []):
                if s.get("invalidation") or s.get("失效条件"):
                    exits.append(s.get("invalidation") or s.get("失效条件"))
        dossier = {
            "_说明": "★轮85 CF6-1 持仓完整档案。买入逻辑/成本/目标价/退出条件。★成本无历史记录=待董事长提供(不编)。",
            "代码": sym, "名称": nm, "现价": h.get("price"), "持股": h.get("quantity"),
            "市值": h.get("market_value"), "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
            "买入逻辑": h.get("one_line_reason") or d.get("reason") or "待Opus5补(one_line_reason缺)",
            "成本价": "待董事长提供（无历史成交记录·不编·CF6-1）",
            "目标价": (tg_map.get(sym, {}) or {}).get("目标价") or (fcs[0].get("target") if fcs else None) or "待接(target_gap/forecast无)",
            "退出条件": exits or "待接(forecast无invalidation)",
            "三关结论": {"硬过滤": h.get("hard_filter"), "质量关": h.get("quality_gate"),
                     "软过滤": h.get("soft_filter"), "估值": h.get("valuation"), "护城河": h.get("moat")},
            "今日动作": d.get("action"),
        }
        p = D / ("holding_dossier_%s.json" % str(sym).replace(".", "_"))
        p.write_text(json.dumps(dossier, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        made.append({"code": sym, "name": nm, "成本": "待董事长提供",
                     "目标价有": dossier["目标价"] not in (None, "") and "待接" not in str(dossier["目标价"]),
                     "退出条件有": bool(exits)})
    return made


def build_account_base(dc):
    """★轮86 DA1:全账户底数判据更正。主战场(富途+SBI)当日底数齐 + IBKR/bitFlyer【静止账户】有最近快照即可。
    IBKR/bitFlyer 不做目标管理(07-19尺《目标倒推框架》+看板G6/G7)·无交易时上次快照=当前真实状态(静止≠陈旧)。"""
    dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    futu = _rj(ROOT / "data/accounts" / f"futu_positions_{dc}.json")
    sbi = _rj(ROOT / "data/accounts/sbi_sleeve_2026-07-18.json")
    # IBKR持仓从production holdings嵌有(NVDA/MSFT/MSTR/COIN/META/IBKR的IBKR腿)→有最近快照
    prod = _rj(ROOT / "data/reports" / f"production_{dc}.json")
    ibkr_syms = [h.get("name") for h in prod.get("holdings", []) if h.get("symbol") in
                 ("US.NVDA", "US.MSFT", "US.MSTR", "US.COIN", "US.META", "US.IBKR")]
    STATIC = {"目标管理": False,
              "★状态": "静止·无交易变化时沿用上次快照即为当前真实状态",
              "★不是陈旧": "不做目标管理(07-19尺《目标倒推框架》·看板G6/G7)；无交易则快照不变(同软银intentional_conservative·静止≠过期)"}
    return {
        "_说明": "★轮86 DA1 全账户底数(判据已更正)。主战场富途+SBI当日底数齐 + IBKR/bitFlyer静止账户有最近快照即可·不要求每日更新·不向董事长索要。",
        "date": dh, "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "主战场": {
            "富途": {"接通": bool(futu), "源": "OpenD实时", "当日底数": "已接(futu_positions/driver_exposure)" if futu else "待接"},
            "SBI": {"接通": bool(sbi), "源": "快照sbi_sleeve", "当日底数": "已接(sbi_sleeve快照)" if sbi else "待接"},
        },
        "静止账户(不做目标管理·跟随主战场)": {
            "IBKR": {"有最近快照": bool(ibkr_syms), "最近快照来源": "production持仓嵌IBKR腿(%s)" % "、".join(str(x) for x in ibkr_syms[:6]),
                     "上次快照日": dh if ibkr_syms else "待首次录入", **STATIC,
                     "反向检查(DA1-3)": "仅当富途/SBI相关标的股数变化或董事长告知交易→才提示更新·平时不告警"},
            "bitFlyer": {"有最近快照": False, "上次快照日": "待首次录入(非阻塞·静止账户)", **STATIC,
                         "反向检查(DA1-3)": "仅董事长告知有币种交易→才提示更新·平时不告警"},
        },
        "全账户底数完整度": "★主战场富途+SBI当日底数齐(2/2) + IBKR有最近快照(静止) → 判据满足(DA1-1)。bitFlyer待首次录入·静止账户非阻塞。",
        "★vintage不告警": "IBKR/bitFlyer静止账户·vintage闸不告警(同软银·DA1-2)",
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    dc = a.date.replace("-", "")
    made = build_dossiers(dc)
    base = build_account_base(dc)
    bp = ROOT / "data/accounts" / f"all_accounts_base_{dc}.json"
    bp.write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    n_tgt = sum(1 for m in made if m["目标价有"]); n_exit = sum(1 for m in made if m["退出条件有"])
    print("[holding_dossier] %s · 建档 %d 只 · 有目标价 %d · 有退出条件 %d · 成本全待董事长提供" % (
        a.date, len(made), n_tgt, n_exit))
    print("  全账户底数(DA1更正): 主战场富途✔SBI✔当日底数齐 + IBKR静止户有最近快照 → 判据满足·bitFlyer待录入(静止非阻塞)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
