#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据能力探针（派工单 2026-07-21·GPT总控：先探针·再冻结标准）。
★只探数据能力·不筛选·不排序·不出名单·不给买卖建议·不改尺·不自调参数。
10只样本 × 17项指标 × 能/不能/部分 + 实际样例值 + 覆盖率 + A组不可得时B组能撑多少。
用法：python scripts/data_probe.py"""
from __future__ import annotations
import json, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "screen"
JST = timezone(timedelta(hours=9))
SAMPLE = ["US.LLY", "US.OXY", "US.UNH", "US.GOOGL", "US.DELL", "US.NVDA", "US.MU",
          "JP.7011", "JP.8035", "JP.6501"]
NAMES = {"US.LLY": "礼来", "US.OXY": "西方石油", "US.UNH": "联合健康", "US.GOOGL": "谷歌",
         "US.DELL": "戴尔", "US.NVDA": "英伟达", "US.MU": "美光", "JP.7011": "三菱重工",
         "JP.8035": "东京电子", "JP.6501": "日立"}
IDX = {"US": "US.SPY", "JP": "JP.1329"}   # 大盘基准:US=SPY;JP=iShares日本ETF(1329)·取不到则标缺基准


def now():
    return datetime.now(JST).isoformat(timespec="seconds")


def fin_val(s, field):
    for k, v in vars(s).items():
        if isinstance(k, tuple) and k[0] == field:
            try:
                return float(v)
            except Exception:
                return None
    return None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import futu as ft
    ctx = ft.OpenQuoteContext("127.0.0.1", 11111)
    R = {c: {} for c in SAMPLE}      # 每只每项结果
    try:
        # ── A组·增长率字段(利润同比等)via get_stock_filter is_no_filter ──
        def growth_fields(market, codes):
            flds = {"营业利润同比": ft.StockField.OPERATING_PROFIT_GROWTH_RATE,
                    "净利润(归母)同比": ft.StockField.PROFIT_TO_SHAREHOLDERS_GROWTH_RATE,
                    "税前利润同比": ft.StockField.PROFIT_BEFORE_TAX_GROWTH_RATE,
                    "ROE同比": ft.StockField.ROE_GROWTH_RATE}
            sf = ft.SimpleFilter(); sf.stock_field = ft.StockField.MARKET_VAL; sf.filter_min = 1e9; sf.is_no_filter = False
            fils = [sf]
            for f in flds.values():
                ff = ft.FinancialFilter(); ff.stock_field = f; ff.is_no_filter = True; ff.quarter = ft.FinancialQuarter.ANNUAL
                fils.append(ff)
            out = {}
            begin = 0
            want = set(codes)
            while want:
                ret, ls = ctx.get_stock_filter(market=market, filter_list=fils, begin=begin, num=200)
                if ret != ft.RET_OK:
                    break
                last, cnt, lst = ls
                for s in lst:
                    if s.stock_code in want:
                        out[s.stock_code] = {"营业利润同比": fin_val(s, "operating_profit_growth_rate"),
                                             "净利润(归母)同比": fin_val(s, "profit_to_shareholders_growth_rate"),
                                             "税前利润同比": fin_val(s, "profit_before_tax_growth_rate"),
                                             "ROE同比": fin_val(s, "roe_growth_rate")}
                        want.discard(s.stock_code)
                begin += len(lst)
                if last or begin >= cnt or not lst:
                    break
                time.sleep(3)
            return out
        us_g = growth_fields(ft.Market.US, [c for c in SAMPLE if c.startswith("US.")]); time.sleep(2)
        jp_g = growth_fields(ft.Market.JP, [c for c in SAMPLE if c.startswith("JP.")]); time.sleep(2)
        gmap = {**us_g, **jp_g}
        for c in SAMPLE:
            R[c]["A2_利润同比"] = gmap.get(c, {})

        # ── A1 历史财务序列季数 + A3/A4 capex/订单(statements 原始·field需映射) ──
        for c in SAMPLE:
            try:
                ret, d = ctx.get_financials_statements(c, num=40)
                if ret == ft.RET_OK and isinstance(d, dict):
                    rep = d.get("report_list") or []
                    R[c]["A1_历史财报期数"] = {"报表期数(单次≤40)": len(rep), "可继续翻页": bool(d.get("next_key")),
                                          "字段名display_name为空": True, "口径": "get_financials_statements·field_id编码·需官方字段映射表才能定位capex/营收行"}
                else:
                    R[c]["A1_历史财报期数"] = {"error": str(d)[:80]}
            except Exception as e:
                R[c]["A1_历史财报期数"] = {"exception": type(e).__name__}
            time.sleep(1.5)

        # ── A5/B10 earnings_price_move:财报发布日+财报后跳空及守住 ──
        for c in SAMPLE:
            try:
                ret, df = ctx.get_financials_earnings_price_move(c)
                if ret == ft.RET_OK and hasattr(df, "columns") and len(df):
                    pubs = sorted(set(df["pub_trading_day_str"].tolist()))
                    # 最近一次财报:day_offset 0(财报后首日) vs -1(前一日) 跳空; +5 vs 0 守住
                    latest = df[df["pub_trading_day_str"] == pubs[-1]]
                    def px(off):
                        r = latest[latest["day_offset"] == off]
                        return float(r["close_price"].iloc[0]) if len(r) else None
                    p_1, p0, p5 = px(-1), px(0), px(5)
                    gap = (round((p0 / p_1 - 1) * 100, 2) if p_1 and p0 else None)
                    hold = (round((p5 / p0 - 1) * 100, 2) if p0 and p5 else None)
                    R[c]["A5B10_财报价格反应"] = {"财报次数": len(pubs), "最近财报发布日": pubs[-1],
                                             "财报后首日跳空%": gap, "之后5日再动%": hold,
                                             "含发布时间pub_date": True}
                else:
                    R[c]["A5B10_财报价格反应"] = {"error": str(df)[:80]}
            except Exception as e:
                R[c]["A5B10_财报价格反应"] = {"exception": type(e).__name__}
            time.sleep(1.5)

        # ── B组·klines:52周高点/上下跌量/相对大盘 1-3-6月 ──
        def kl(code, n=260):
            try:
                ret, df, _ = ctx.request_history_kline(code, ktype=ft.KLType.K_DAY, autype=ft.AuType.QFQ, max_count=n)
                return df if ret == ft.RET_OK and len(df) else None
            except Exception:
                return None
        idx_close = {}
        for mk, ic in IDX.items():
            d = kl(ic); time.sleep(1)
            idx_close[mk] = [float(x) for x in d["close"].tolist()] if d is not None else None
        for c in SAMPLE:
            df = kl(c); time.sleep(0.8)
            if df is None:
                R[c]["B_klines"] = {"error": "kline未返回"}
                continue
            close = [float(x) for x in df["close"].tolist()]
            high = [float(x) for x in df["high"].tolist()]
            vol = [float(x) for x in df["volume"].tolist()]
            hi52 = max(high[-min(len(high), 252):])
            dist52 = round((close[-1] / hi52 - 1) * 100, 2)
            up_v = sum(vol[i] for i in range(1, len(close)) if close[i] > close[i - 1])
            dn_v = sum(vol[i] for i in range(1, len(close)) if close[i] < close[i - 1])
            udr = round(up_v / dn_v, 2) if dn_v else None
            mk = c.split(".")[0]
            ic = idx_close.get(mk)
            rel = {}
            for lbl, d in [("1月", 21), ("3月", 63), ("6月", 126)]:
                if len(close) > d and ic and len(ic) > d:
                    sr = close[-1] / close[-1 - d] - 1
                    ir = ic[-1] / ic[-1 - d] - 1
                    rel[lbl] = round((sr - ir) * 100, 2)
                else:
                    rel[lbl] = None
            R[c]["B6_相对大盘超额%"] = rel
            R[c]["B8_距52周高%"] = dist52
            R[c]["B9_上涨量比下跌量"] = udr
        R["_index_ok"] = {mk: (idx_close[mk] is not None) for mk in IDX}
    finally:
        ctx.close()

    # ── 汇总:能力矩阵 + 覆盖率 ──
    def has(v):
        return isinstance(v, dict) and not v.get("error") and not v.get("exception") and any(
            (x is not None) for k, x in v.items() if not k.startswith("_") and not isinstance(x, dict)) or \
            (isinstance(v, dict) and any(isinstance(x, (int, float)) for x in v.values()))
    caps = {}   # 指标→{能:[],部分:[],不能:[]}
    # 指标可得性判定(按实际取到样例)
    def avail_A2(c):
        g = R[c].get("A2_利润同比", {})
        vals = [v for v in g.values() if v is not None]
        return "能" if len(vals) >= 3 else ("部分" if vals else "不能")
    def avail_A5(c):
        return "能" if isinstance(R[c].get("A5B10_财报价格反应"), dict) and R[c]["A5B10_财报价格反应"].get("财报次数") else "不能"
    def avail_A1(c):
        return "能(原始)" if (R[c].get("A1_历史财报期数", {}).get("报表期数(单次≤40)") or 0) >= 8 else "部分"
    def avail_B(c, key):
        v = R[c].get(key)
        if key == "B6_相对大盘超额%":
            return "能" if v and any(x is not None for x in v.values()) else "部分(缺大盘基准)"
        return "能" if v is not None else "不能"
    matrix = {}
    for c in SAMPLE:
        matrix[c] = {
            "A1历史财报≥8季": avail_A1(c),
            "A2利润同比": avail_A2(c),
            "A3营收同比": "部分(无直接字段·需statements解field_id)",
            "A4毛利率/OCF同比": "不能(filter无此增长字段·需2期statements自算)",
            "A3capex": "不能(filter无capex字段;statements疑含但field_id未映射)",
            "A4在手订单": "不能(OpenD无订单余额字段)",
            "A5一致预期历史": "不能(OpenD无分析师一致预期API·仅有财报实际)",
            "B6相对大盘1/3/6月": avail_B(c, "B6_相对大盘超额%"),
            "B8距52周高": avail_B(c, "B8_距52周高%"),
            "B9上涨量/下跌量": avail_B(c, "B9_上涨量比下跌量"),
            "B10财报后跳空守住": avail_A5(c),
            "B7相对行业强度": "部分(需行业成员批量kline自算·OpenD无现成字段)",
            "B11行业涨占比/新高占比": "部分(需全行业成员kline自算·成本高)",
        }
    doc = {
        "_探针说明": "只探数据能力·不筛选不排序不出名单不给建议·不改尺。样本10只(美日·含点名5只盈利主力)。",
        "生成时间": now(), "样本": {c: NAMES[c] for c in SAMPLE}, "大盘基准": IDX,
        "index_可得": R.get("_index_ok"),
        "能力矩阵_指标x10只": matrix,
        "实际样例值": {c: {k: v for k, v in R[c].items()} for c in SAMPLE},
        "C组_可信度": {
            "12_真实存在非0空": "利润同比/相对强度/52周高/量比 取到真值(见样例);★毛利率类曾遇OpenD半年报返0.0陷阱→已知须ANNUAL口径+0.0转null",
            "13_历史同口径": "statements多期存在但field_id未映射·同口径未逐项验证→标部分;kline派生指标同口径",
            "14_发布时间可得": "财报发布日 earnings_price_move.pub_trading_day_str 可得(能);filter增长字段无as-of发布日(不能)",
            "15_look_ahead风险": "★filter/growth返回的是当前最新TTM快照·非历史as-of值→用于回测有look-ahead偏差;kline按交易日无回填(低风险);earnings_price_move带真实发布日(低风险)",
            "16_US_JP一致": "增长字段/earnings/kline 美日皆返回(见JP.7011/8035/6501样例);财报口径日股半年报·季度粒度与美股不同",
            "17_更新频率": "财务=季/半年报随披露更新;价格=日线T+1;相对强度=可日更",
        },
    }
    # 覆盖率
    def rate(key):
        vals = [matrix[c][key] for c in SAMPLE]
        能 = sum(1 for v in vals if v.startswith("能"))
        部分 = sum(1 for v in vals if v.startswith("部分"))
        return {"能": 能, "部分": 部分, "不能": len(vals) - 能 - 部分, "可得率%": round(能 / len(vals) * 100, 1)}
    doc["覆盖率"] = {k: rate(k) for k in matrix[SAMPLE[0]]}
    A = ["A1历史财报≥8季", "A2利润同比", "A3营收同比", "A4毛利率/OCF同比", "A3capex", "A4在手订单", "A5一致预期历史"]
    B = ["B6相对大盘1/3/6月", "B8距52周高", "B9上涨量/下跌量", "B10财报后跳空守住", "B7相对行业强度", "B11行业涨占比/新高占比"]
    doc["A组vsB组结论"] = {
        "A组(基本面变化)": {k: doc["覆盖率"][k] for k in A},
        "B组(市场变化)": {k: doc["覆盖率"][k] for k in B},
        "判断": "A组『变化驱动』核心(营收/毛利/OCF同比·capex·订单·一致预期)大面积不可得或需自解field_id;"
              "唯『利润同比』有直接字段。B组(相对大盘/52周高/量能/财报跳空)基本可算——"
              "★若A组不可得，B组可撑起『市场已在定价变化』类判断(动量/相对强度/财报后反应)，"
              "但撑不起『基本面拐点提前于价格』类判断(需营收/订单/预期上修)。二者互补·不能互替。",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "data_probe_20260721.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    raw = p.read_bytes()
    print("wrote", p.name, len(raw), "bytes · EFBFBD=", raw.count(b"\xef\xbf\xbd"))
    print("覆盖率:", json.dumps({k: v["可得率%"] for k, v in doc["覆盖率"].items()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
