# -*- coding: utf-8 -*-
"""★轮106 NL2:三只样板执行参数【全部机器算·无拍脑袋】(US.MSFT/JP.6857/JP.4568)。
从 OpenD K_DAY(QFQ) 取真 K线→算 MA20/60/120·ADV60(60日日均成交量)·ATR14·60日日波动分位。
据此推:到价三档(目标/低吸/止损)·分笔数(卖出股数÷ADV参与率)·每档价(均线档位)·跳空阈值(ATR%)。
★每个参数带【算法+输入数据+as_of】;算不出→NK4不输出标『因缺X』·不拍数。★只读·不下单。"""
import sys, json, math, argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
sys.path.insert(0, str(ROOT / "scripts"))
from realtime_price import connect_quote_context, get_realtime_price, records_from_frame

TARGETS = [("US.MSFT", "微软"), ("JP.6857", "爱德万"), ("JP.4568", "第一三共")]


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def fetch_bars(ctx, symbol):
    """取 K_DAY(QFQ) 全 bar:close/high/low/volume。返回 bars(时间升序)。"""
    from futu import AuType, KLType, RET_OK
    rows = []
    try:
        ret, data, pk = ctx.request_history_kline(symbol, ktype=KLType.K_DAY, autype=AuType.QFQ, max_count=1000)
        if ret != RET_OK:
            return [], str(data)
        rows = records_from_frame(data)
        while pk is not None and len(rows) < 300:
            ret, data, pk = ctx.request_history_kline(symbol, ktype=KLType.K_DAY, autype=AuType.QFQ, max_count=1000, page_req_key=pk)
            if ret != RET_OK:
                break
            rows.extend(records_from_frame(data))
    except Exception as e:
        return [], str(e)
    bars = []
    for r in rows:
        try:
            bars.append({"close": float(r.get("close")), "high": float(r.get("high")),
                         "low": float(r.get("low")), "volume": float(r.get("volume") or 0),
                         "time": r.get("time_key") or r.get("time")})
        except (TypeError, ValueError):
            continue
    return bars, None


def _ma(closes, n):
    return round(sum(closes[-n:]) / n, 4) if len(closes) >= n else None


def _atr(bars, n=14):
    if len(bars) < n + 1:
        return None
    trs = []
    for i in range(len(bars) - n, len(bars)):
        h, l, pc = bars[i]["high"], bars[i]["low"], bars[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return round(sum(trs) / n, 4)


def _daily_range_pctile(bars, n=60, q=0.5):
    """60日 日内(high-low)/close 分布的分位数(默认中位数)——供跳空阈值参考。"""
    if len(bars) < n:
        return None
    rs = sorted((b["high"] - b["low"]) / b["close"] for b in bars[-n:] if b["close"])
    idx = min(len(rs) - 1, int(q * len(rs)))
    return round(rs[idx] * 100, 2)  # pct


def compute(symbol, name, bars, price, price_asof, cost, qty, forecast_scn):
    closes = [b["close"] for b in bars]
    ma20, ma60, ma120 = _ma(closes, 20), _ma(closes, 60), _ma(closes, 120)
    adv60 = round(sum(b["volume"] for b in bars[-60:]) / 60, 0) if len(bars) >= 60 else None
    atr14 = _atr(bars, 14)
    atr_pct = round(atr14 / price * 100, 2) if (atr14 and price) else None
    rng_med = _daily_range_pctile(bars, 60, 0.5)
    asof_k = bars[-1]["time"] if bars else None

    def mark(val, algo, inputs, ok=True):
        if not ok or val is None:
            return {"值": None, "★不输出": "因缺输入·本项不输出(NK4·不拍数)", "算法": algo, "输入数据": inputs, "as_of": asof_k}
        return {"值": val, "算法": algo, "输入数据": inputs, "as_of": asof_k}

    # ── 三情景 point_value/区间(长期·来自锁定预测) ──
    mid_pt, opt_pt, bear_lo = None, None, None
    for s in (forecast_scn or []):
        nm = str(s.get("name", "")); rg = s.get("range") if isinstance(s.get("range"), list) else None
        pv = s.get("point_value") or (round(sum(rg) / 2, 2) if rg else None)
        if "中性" in nm:
            mid_pt = pv
        elif "乐观" in nm:
            opt_pt = pv
        elif "悲观" in nm and rg:
            bear_lo = rg[0]

    # ── 到价·★三时间尺度(NM2·不混用)：3日=技术swing／1-3月=趋势均线／6-12月=基本面情景 ──
    _a = atr14
    price_targets = {
        "未来3日(短·技术swing·MA20+ATR)": {
            "目标价": mark(round(price + _a, 2) if (price and _a) else None, "现价+1×ATR14(短期波动上沿·swing)", "现价+ATR14", ok=bool(price and _a)),
            "低吸价": mark(round(price - _a, 2) if (price and _a) else None, "现价−1×ATR14(短期波动下沿)·参照MA20=%s" % ma20, "现价+ATR14+MA20", ok=bool(price and _a)),
            "止损价": mark(round(price - 1.5 * _a, 2) if (price and _a) else None, "现价−1.5×ATR14(短期止损)", "现价+ATR14", ok=bool(price and _a)),
        },
        "未来1-3月(中·趋势·均线位)": {
            "目标价": mark(ma20, "MA20(短中期均线·趋势回归位)", "K_DAY QFQ 20根收盘均值", ok=ma20 is not None),
            "低吸价": mark(ma60, "回踩MA60(60日均线)", "K_DAY QFQ 60根收盘均值", ok=ma60 is not None),
            "止损价": mark(ma120, "跌破MA120(120日中期趋势线)", "K_DAY QFQ 120根收盘均值", ok=ma120 is not None),
        },
        "未来6-12月(长·基本面·三情景)": {
            "目标价": mark(mid_pt, "三情景中性(S2) point_value(锁定预测)", "forecast 该只中性point_value", ok=mid_pt is not None),
            "低吸价": mark(bear_lo, "悲观(S3)区间下沿(便宜位)", "forecast 悲观range下界", ok=bear_lo is not None),
            "止损价": mark(bear_lo, "跌破悲观(S3)下沿=基本面假设失效位", "forecast 悲观range下界", ok=bear_lo is not None),
            "乐观(S1)point": opt_pt,
        },
    }

    # ── 分笔数=卖出股数 ÷ (ADV60 × 单笔参与率20%)·向上取整·最小1 ──
    part_rate = 0.20  # 单笔不超过日均量20%(限市场冲击·标准执行参与率)
    tranches = None; tranche_algo = None
    if qty and adv60:
        cap = adv60 * part_rate
        tranches = max(1, math.ceil(qty / cap))
        tranche_algo = ("分笔数=ceil(卖出股数 %d ÷ (ADV60 %d × 参与率20%%=%d))=%d；"
                        "★股数占ADV60仅 %.2f%%——%s" % (
                            qty, adv60, int(cap), tranches, qty / adv60 * 100,
                            "远小于单笔上限·无需拆分·1笔即可" if tranches == 1 else "需拆分以控冲击"))
    tranche = mark(tranches, tranche_algo or "分笔数=卖出股数÷(ADV60×20%)", "卖出股数 + ADV60(60日日均成交量)", ok=tranches is not None)

    # ── 跳空阈值=1×ATR%(低开在1个ATR内=常态波动照卖;1-2 ATR分批;>2 ATR暂停) ──
    gap = mark(atr_pct, "跳空阈值=ATR14/现价(1×ATR=常态日波动)。低开≤1×ATR照卖·1~2×ATR分批·>2×ATR暂停(超常态波动·等确认)",
               "ATR14(14日真实波幅均值) + 现价 + 60日日内波幅中位%s" % (("=%.2f%%" % rng_med) if rng_med else ""), ok=atr_pct is not None)

    # ── 每档价格=按均线/现价档位(卖出:现价→MA20→更高;分笔时逐档) ──
    ladder = None
    if price and tranches and atr14:
        # 卖出分笔:以现价为锚·每档间隔0.5×ATR(盘口档位近似)·tranches档
        ladder = [round(price - i * 0.5 * atr14, 2) for i in range(tranches)] if tranches > 1 else [round(price, 2)]
    ladder_mark = mark(ladder, "每档价=现价 − i×0.5×ATR14(逐档让价0.5个ATR·近似盘口档位)·i=0..笔数-1",
                       "现价 + ATR14 + 分笔数", ok=ladder is not None)

    return {
        "symbol": symbol, "name": name,
        "现价": {"值": price, "as_of": price_asof, "来源": "OpenD get_realtime_price"},
        "成本": cost,
        "K线指标(机器算·K_DAY QFQ)": {
            "MA20": ma20, "MA60": ma60, "MA120": ma120,
            "ADV60_60日日均成交量": adv60, "ATR14": atr14, "ATR占现价pct": atr_pct,
            "60日日内波幅中位pct": rng_med, "K线根数": len(bars), "as_of": asof_k},
        "到价三档": price_targets,
        "★分笔数": tranche,
        "★跳空阈值": gap,
        "每档价格": ladder_mark,
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    dc = a.date.replace("-", "")
    # ★NM1:全量20只(不只3只)。标的来源=production holdings(权威20只)。
    prod = _rj(ROOT / "data/reports" / f"production_{dc}.json")
    targets = [(h.get("symbol"), h.get("name")) for h in prod.get("holdings", []) if h.get("symbol")]
    if not targets:
        targets = TARGETS
    # 成本/股数 来源
    ht = _rj(ROOT / "data/accounts" / f"holdings_true_{dc}.json")
    hmap = {h.get("symbol"): h for h in ht.get("holdings", [])}
    # forecast 三情景(来自锁定预测)。★守§5.4:按 forecast_YYYY-MM-DD.json 日期选最新·不用 sorted(glob)[-1](会选中hash后缀空文件)。
    import glob, re
    dated = []
    for p in glob.glob(str(ROOT / "data/forecast/forecast_*.json")):
        m = re.match(r"forecast_(\d{4}-\d{2}-\d{2})\.json$", Path(p).name)
        if m:
            dated.append((m.group(1), p))
    fc = _rj(sorted(dated)[-1][1]) if dated else {}
    scnmap = {}
    for f in (fc.get("forecasts") or []):
        if f.get("horizon") == "1y":
            scnmap[f.get("ticker")] = f.get("scenarios") or []

    ctx, attempts = connect_quote_context(max_retries=3, wait_seconds=3)
    if ctx is None:
        out = {"date": a.date, "★连接": "FAIL", "★如实报": "OpenD连不上·未生产·不用旧价顶充", "attempts": attempts}
        (ROOT / "data/accounts" / f"exec_params_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[exec_params] ★OpenD连不上·未生产(如实报·不估算)"); return 2
    results = []
    try:
        for sym, nm in targets:
            q = get_realtime_price(sym, ctx=ctx, max_retries=1, wait_seconds=0)
            price = q.get("price") if q.get("status") == "OK" else None
            price_asof = "%s(%s·%s)" % (q.get("used_field"), q.get("status"), datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"))
            bars, err = fetch_bars(ctx, sym)
            h = hmap.get(sym, {})
            cost = None
            for acc in (h.get("accounts") or []):
                if acc.get("cost"):
                    cost = acc.get("cost"); break
            qty = h.get("total_quantity")
            r = compute(sym, nm, bars, price, price_asof, cost, qty, scnmap.get(sym))
            if err:
                r["★K线错误"] = err
            results.append(r)
    finally:
        try: ctx.close()
        except Exception: pass
    out = {"_说明": "★轮106 NL2 三只样板执行参数·全机器算·每参数标算法+输入+as_of·算不出不输出(NK4)。",
           "date": a.date, "生成时刻": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
           "★连接": "OK", "三只": results}
    (ROOT / "data/accounts" / f"exec_params_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for r in results:
        ind = r["K线指标(机器算·K_DAY QFQ)"]
        print("%s %s 现价%s ADV60=%s ATR14=%s(%s%%) MA20/60/120=%s/%s/%s" % (
            r["symbol"], r["name"], r["现价"]["值"], ind["ADV60_60日日均成交量"], ind["ATR14"], ind["ATR占现价pct"],
            ind["MA20"], ind["MA60"], ind["MA120"]))
        if r["symbol"] == "JP.4568":
            print("  ★第一三共 分笔数:", r["★分笔数"].get("算法"))
            print("  ★第一三共 跳空阈值:", r["★跳空阈值"].get("值"), "% —", r["★跳空阈值"].get("算法")[:60])
    print("[exec_params] 写出 exec_params_%s.json" % dc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
