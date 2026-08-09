# -*- coding: utf-8 -*-
"""★轮104 NK1:全账户闭合汇总【接通·非删除】(GPT明令)。读全部账户底数文件聚合·每个数字标【分母+来源文件+as_of】。
★接不通的项(08-02当日现金/BTC-ETH数量)如实标『未接·原因·预计』·不因此删整块(NK1-4)。
★NK4 前置检查:缺【全账户分母/价格日期/估值锚】→ 该项比例与到价【不输出】·标『因缺X本项不输出』·不用估算填充。
持仓市值/AI敞口/币种敞口=当日可算(用production+portfolio_concentration);现金/总资产=混合口径(富途07-22·SBI07-18·IBKR/bitFlyer07-02)显式标。"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from full_product_render import portfolio_concentration, resolve_usdjpy, _mv_usd


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def build(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    prod = _rj(ROOT / "data/reports" / f"production_{dc}.json")
    holds = prod.get("holdings", [])
    usdjpy, fx_src = resolve_usdjpy()
    import re as _re
    fx_src = _re.sub(r"[\w-]+\.json", "统一持仓快照", str(fx_src)).replace("fx.USDJPY", "USDJPY").strip("·. ")

    # ── 当日可算(持仓口径·NK1-2) ──
    conc = portfolio_concentration(holds)
    total_mv = conc.get("total_usd")
    ai = ((conc.get("categories", {}) or {}).get("AI供应链") or {})
    ai_pct = ai.get("pct")
    jp_usd = sum((_mv_usd(h, usdjpy)[0] or 0) for h in holds if str(h.get("symbol", "")).startswith("JP."))
    us_usd = sum((_mv_usd(h, usdjpy)[0] or 0) for h in holds if str(h.get("symbol", "")).startswith("US."))

    # ── 各账户底数(接通·标 as_of·来源) ──
    cov = _rj(ROOT / "data/accounts/全账户覆盖_20260722.json")
    cov_map = {r.get("账户", ""): r for r in cov.get("账户覆盖", [])}
    futu = cov_map.get("FUTU(富途)", {})
    sbi = _rj(ROOT / "data/accounts/sbi_sleeve_2026-07-18.json")
    bf = _rj(ROOT / "data/accounts/bitflyer_account_2026-07-02.json")
    sbi_snap = sbi.get("snapshot", {}) or {}

    accounts = [
        {"账户": "富途 FUTU", "接入": "OpenD实时", "现金_USD": futu.get("现金USD"), "总资产_USD": futu.get("总资产USD"),
         "市值_USD": futu.get("市值USD"), "as_of": futu.get("数据日", "2026-07-22"), "来源文件": "全账户覆盖_20260722.json←futu_positions accinfo_query(REAL·USD)",
         "机器直采": True, "★状态": "现金/总资产 as_of=07-22(董事长现报)·非08-02·持仓市值可用08-02重算"},
        {"账户": "SBI(独立进攻仓sleeve)", "接入": "手工截图·未接OpenD", "as_of": sbi_snap.get("data_date", "2026-07-18"),
         "来源文件": "sbi_sleeve_2026-07-18.json(董事长SBI App截图)", "机器直采": False,
         "★状态": "★sleeve独立核算·不并入主组合集中度(sleeve_rules)·as_of=07-18·未接OpenD·待董事长手工确认08-02"},
        {"账户": "IBKR", "接入": "OCR快照·未接OpenD", "as_of": "2026-07-02", "来源文件": "四账户OCR汇总_2026-07-02(嵌production IBKR腿)",
         "机器直采": False, "★状态": "★静止账户(07-19尺·不做目标管理)·as_of=07-02·无交易则沿用·非陈旧但非08-02"},
        {"账户": "bitFlyer(加密)", "接入": "OCR快照·未接OpenD", "总资产_JPY": bf.get("总资产_JPY"), "as_of": bf.get("截图日期", "2026-07-02"),
         "来源文件": "bitflyer_account_2026-07-02.json(截图)", "机器直采": False,
         "★状态": "★静止账户·总资产¥%s(07-02)·BTC/ETH数量明细【未接】·as_of=07-02" % bf.get("总资产_JPY")},
    ]

    # ── NK4 前置检查:缺分母/价格日期/估值锚 → 该项比例不输出 ──
    fresh_cash_ok = False  # 08-02 当日现金:不存在(最新富途07-22)
    price_date_ok = True   # 价格对应交易日 07-31 明确
    checks = {
        "全账户现金分母_08-02当日": {"齐": fresh_cash_ok, "实情": "最新现金 富途07-22/SBI07-18/IBKR·bitFlyer07-02·无08-02当日现金"},
        "价格对应交易日": {"齐": price_date_ok, "实情": "07-31 周五收盘(两市周末休市·明确)"},
        "BTC/ETH数量": {"齐": False, "实情": "bitFlyer 币种数量明细未接(仅总资产JPY)"},
    }

    def gated(name, value, needs_fresh_cash=False, needs_price=False):
        """NK4:依赖项分母缺则不输出该比例·标因缺X本项不输出。"""
        if needs_fresh_cash and not fresh_cash_ok:
            return "★因缺【08-02当日全账户现金分母】·本项不输出(NK4·不用估算填充)"
        if needs_price and not price_date_ok:
            return "★因缺【价格对应交易日】·本项不输出(NK4)"
        return value

    out = {
        "_说明": "★轮104 NK1 全账户闭合汇总(接通非删除)。每数字标分母+来源+as_of。NK4:缺分母项不输出比例·标因缺X。",
        "date": dh, "生成时刻": "见回报", "FX_USDJPY": usdjpy, "FX来源": fx_src,
        "一_各账户底数(接通·标as_of)": accounts,
        "二_当日可算(持仓口径·分母=已扫持仓市值合计·as_of=08-02价07-31)": {
            "已扫持仓市值合计_USD": round(total_mv, 0) if total_mv else None,
            "分母": "已扫持仓市值合计(含富途+SBI实时腿+IBKR/bitFlyer静态)·非现金融资全账户闭合",
            "来源": "production_%s.json holdings × portfolio_concentration(同产品规矩4)" % dc, "as_of": "%s(价07-31)" % dh,
            "AI同一驱动集中度_真实占比": {"值_pct": round(ai_pct, 2) if ai_pct is not None else None,
                "分母": "已扫持仓市值合计(非估算·NK1-2)", "口径": "AI供应链category·真实持仓算·非估算"},
            "币种敞口": {"日元_USD": round(jp_usd, 0), "美元_USD": round(us_usd, 0),
                "日元占比_pct": round(jp_usd / total_mv * 100, 2) if total_mv else None,
                "美元占比_pct": round(us_usd / total_mv * 100, 2) if total_mv else None,
                "分母": "已扫持仓市值合计", "as_of": "08-02价07-31"},
        },
        "三_全账户闭合(混合口径·NK4部分不输出)": {
            "★口径警示": "★现金数据截至日 富途07-22/SBI07-18/IBKR·bitFlyer07-02·持仓数据截至日 08-02(价07-31)——【非同一时点闭合】",
            "整体总资产_USD": gated("整体总资产", "★混合口径·不给单一精确数(现金非08-02)——分账户见『一』各标as_of", needs_fresh_cash=True),
            "总现金与融资净额": gated("现金融资净额", None, needs_fresh_cash=True),
            "距+40%目标进度": gated("距+40%进度", None, needs_fresh_cash=True),
            "距+100%目标进度": gated("距+100%进度", None, needs_fresh_cash=True),
        },
        "四_接不通项(如实标·原因·预计·NK1-4·不删整块)": [
            {"项": "08-02当日全账户现金/总资产", "原因": "SBI/IBKR/bitFlyer未接OpenD·富途现金董事长07-22后未再报", "预计": "董事长手工报当日现金 or SBI/IBKR接入后自动"},
            {"项": "BTC/ETH币种数量明细", "原因": "bitFlyer仅入库总资产JPY·币种截图IMG_3278~3280未逐张读", "预计": "续读加密截图后接"},
            {"项": "SBI公司账户", "原因": "07-02 OCR·未接OpenD", "预计": "董事长手工确认"},
        ],
        "五_NK4前置检查结果": checks,
        "★NK4声明": "缺【08-02当日现金分母】→ 整体总资产/现金融资净额/目标进度【不输出精确比例】·标因缺X(不用估算填充·防D3精确地产生错误答案)。持仓市值/AI敞口/币种敞口=当日可算·照出。",
    }
    op = ROOT / "data/accounts" / f"all_accounts_closure_{dc}.json"
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[全账户闭合] 写出", op.name)
    print("  当日可算: 持仓市值 $%s · AI敞口 %s%% · 日元占比 %.1f%% · 美元占比 %.1f%%" % (
        round(total_mv), round(ai_pct, 1), jp_usd / total_mv * 100, us_usd / total_mv * 100))
    print("  各账户as_of: 富途07-22 / SBI07-18 / IBKR07-02 / bitFlyer07-02")
    print("  ★NK4: 08-02当日现金分母缺 → 整体总资产/现金净额/目标进度【不输出】(标因缺X·不估算)")
    print("  接不通项: 3 条(如实标·未删整块)")
    return 0


if __name__ == "__main__":
    import argparse
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    raise SystemExit(build(a.date))
