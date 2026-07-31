#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""首轮重跑（A案·董事长2026-07-21）：财务改评分制。派工单_首轮重跑_财务改评分制_20260721。

上一轮没做错——架构师把"净负债"设成硬门槛却没先验证 OpenD 能否给数据。本轮只改三处：
  改1 财务门槛→财务质量评分（不阻断入围）：硬准入只剩 市值/60日均成交额/经营性现金流为正；
      其余财务改五维评分(自由现金流25/毛利率25/资产负债20/在手订单20/成本优势10)·行业内分位0~100·加权。
      取不到的维度记0分并标"数据未接"·不得用行业均值填补·不得因此判落选·卡上标"财务质量数据缺 N/5 项"。
  改2 成交额→真算近60交易日日均（不得再用当日近似）。
  改3 汇率→取实时(记录取值时间与来源)。
经营性现金流是唯一仍有阻断力的财务项：取不到→标"财务数据未接"·进研究基准池(不是落选·落选=查过不合格)。
结论五选一：入围/落选/研究基准/无法判定/本轮不做。
铁律不变：只读不下单·不改尺·不自调参数·不出买卖清单·不生成 actionable·取不到标null写原因不估算。
用法：python scripts/first_scan2.py [--date 20260721] [--prev 20260720]
"""
from __future__ import annotations
import argparse, json, hashlib, socket, sys, time, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data" / "screen"
JST = timezone(timedelta(hours=9))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

PARAMS = {
    "硬准入_1_最低市值_美元": 10_000_000_000,
    "硬准入_2_最低60日均成交额_美元": 100_000_000,
    "硬准入_3_经营性现金流": "TTM 为正（>0）；取不到→研究基准池(非落选)",
    "财务五维权重": {"自由现金流": 25, "毛利率": 25, "资产负债": 20, "在手订单": 20, "成本优势": 10},
    "财务评分口径": "每维按行业内分位打分0~100·加权=财务质量总分；取不到的维度记0分并标『数据未接』·不填补·不判落选",
    "6_K型向下排除阈值": 3,
    "7_行业强度强分数线": 70,
    "9_行情价格时限_交易日": 2,
    "10_财务数据时限_自然日": 120,
    "成交额口径": "近60交易日日均(真算·kline turnover)·不再用当日近似",
    "_不变": "参数用批准值·Code不自调；港新欧/美股OTC本轮不做·不计缺失率",
}
PRIMARY_EXCH = {"US_NYSE", "US_NASDAQ", "US_AMEX", "JP_TSE"}
# 财务字段(FinancialFilter·tuple键)
FIN_FIELDS = {"operating_cash_flow_ttm": "OCF_TTM", "gross_profit_rate": "毛利率",
              "debt_asset_rate": "资产负债率", "net_profit_rate": "净利率", "ebitda_margin": "EBITDA率"}


def now_jst():
    return datetime.now(JST).isoformat(timespec="seconds")


def ext_time():
    try:
        import forecast_lock as FL
        return FL.external_time()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": f"external_time 调用失败: {e}"}


def live_fx():
    """实时 USDJPY(记录时间与来源)。取不到→标未接·不猜。"""
    for name, url in [("open.er-api", "https://open.er-api.com/v6/latest/USD"),
                      ("exchangerate.host", "https://api.exchangerate.host/latest?base=USD&symbols=JPY")]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "scan/1.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                j = json.loads(r.read().decode("utf-8"))
                rate = (j.get("rates") or {}).get("JPY")
                if rate:
                    return {"ok": True, "USDJPY": float(rate), "source": name + "(" + url + ")",
                            "as_of": j.get("time_last_update_utc") or j.get("date"), "fetched_local": now_jst()}
        except Exception:
            continue
    return {"ok": False, "reason": "实时FX源全部连不上·未接·不用假设值", "fetched_local": now_jst()}


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).exists() else None


def write_json(name, obj):
    SCREEN.mkdir(parents=True, exist_ok=True)
    p = SCREEN / name
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    raw = p.read_bytes()
    return {"file": str(p.relative_to(ROOT)).replace("\\", "/"), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(), "written_at_local": now_jst(),
            "mojibake_EFBFBD": raw.count(b"\xef\xbf\xbd")}


def port_open(host="127.0.0.1", port=11111, t=2.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(t)
    try:
        s.connect((host, port)); return True
    except Exception:
        return False
    finally:
        s.close()


def _num(r, k):
    v = r.get(k)
    try:
        return float(v) if v not in (None, "", "N/A") else None
    except Exception:
        return None


def classify_pool(ctx, ft, market, codes, chunk=150):
    """分批(code_list·小响应·避开全集超时)取 exchange_type → (exch映射, 失败批的code)。
    某批重试1次仍不行→该批 code 标未取得并继续·不因一批失败放弃整个市场(董事长2026-07-21 问题3)。"""
    exch, failed, batches = {}, [], {"total": 0, "ok": 0, "fail": 0}
    for i in range(0, len(codes), chunk):
        part = codes[i:i + chunk]; batches["total"] += 1; ok = False
        for _ in range(2):
            try:
                ret, df = ctx.get_stock_basicinfo(market, ft.SecurityType.STOCK, code_list=part)
                if ret == ft.RET_OK:
                    for _, r in df.iterrows():
                        exch[str(r["code"])] = str(r.get("exchange_type"))
                    ok = True; break
            except Exception:
                pass
            time.sleep(5)
        if ok:
            batches["ok"] += 1
        else:
            batches["fail"] += 1; failed += part
        time.sleep(1.2)
    return exch, failed, batches


def fin_val(s, field):
    for k, v in vars(s).items():
        if isinstance(k, tuple) and k[0] == field:
            try:
                return float(v)
            except Exception:
                return None
    return None


# ── universe（含主板/OTC归类）──
def step1_universe(ctx, ft):
    uni = {"markets_scanned": ["US", "JP"], "markets_not_done": ["HK", "SG", "EU", "美股OTC"],
           "not_done_说明": "本轮不做·不计入缺失率", "korea": "定向查2只·未做全市场扫描",
           "counts": {}, "codes": {}, "primary_codes": {}, "otc_codes": {}, "method": {}}
    for nm, mk in [("US", ft.Market.US), ("JP", ft.Market.JP)]:
        df = None
        for _ in range(5):
            ret, d = ctx.get_stock_basicinfo(mk, ft.SecurityType.STOCK)
            if ret == ft.RET_OK:
                df = d; break
            time.sleep(8)
        if df is not None:
            df2 = df[df.get("delisting") != True] if "delisting" in df.columns else df  # noqa: E712
            codes, primary, otc, exch = [], set(), set(), {}
            for _, r in df2.iterrows():
                ex = str(r.get("exchange_type", "")); exch[ex] = exch.get(ex, 0) + 1
                codes.append({"code": r["code"], "name": r.get("name", ""), "exch": ex})
                (primary if ex in PRIMARY_EXCH else otc).add(r["code"])
            uni["counts"][nm] = {"total_basicinfo": len(df), "excl_delisted": len(df2),
                                 "primary_listed": len(primary), "otc_nonexec": len(otc), "exchange_dist": exch}
            uni["codes"][nm] = codes; uni["primary_codes"][nm] = sorted(primary); uni["otc_codes"][nm] = sorted(otc)
            uni["method"][nm] = "get_stock_basicinfo(全集+交易所归类)"
        else:
            uni["counts"][nm] = {"total_basicinfo": None, "error": "basicinfo 超时"}
            uni["codes"][nm] = []
        time.sleep(3)
    return uni


# ── 市值+财务(一次 combo filter 批量取)──
def _filter_fin(ctx, ft, market, min_mktval):
    sf = ft.SimpleFilter(); sf.stock_field = ft.StockField.MARKET_VAL
    sf.filter_min = min_mktval; sf.is_no_filter = False; sf.sort = ft.SortDir.DESCEND

    def ff(fld):
        # ★用 ANNUAL(年报)口径:日股常按半年报·MOST_RECENT_QUARTER 的毛利/净利/EBITDA 常返回 0.0(未填)污染排序;
        #   ANNUAL 有真值(发那科毛利38.29/信越34.22)。TTM字段(OCF)不受季度影响。
        f = ft.FinancialFilter(); f.stock_field = fld; f.is_no_filter = True
        f.quarter = ft.FinancialQuarter.ANNUAL
        return f

    def margin_or_null(s, field):
        # 利润率字段(毛利/净利/EBITDA):取不到或恰为 0.0 → null(数据未接·禁止填0·会污染分位);记入 0.0 报警
        v = fin_val(s, field)
        return (None if (v is None or v == 0.0) else v)

    fils = [sf, ff(ft.StockField.OPERATING_CASH_FLOW_TTM), ff(ft.StockField.GROSS_PROFIT_RATE),
            ff(ft.StockField.DEBT_ASSET_RATE), ff(ft.StockField.NET_PROFIT_RATE), ff(ft.StockField.EBITDA_MARGIN)]
    got = {}; begin = 0; err = None; zero_flag = []
    while True:
        ret, ls = ctx.get_stock_filter(market=market, filter_list=fils, begin=begin, num=200)
        if ret != ft.RET_OK:
            err = str(ls); break
        last, cnt, lst = ls
        for s in lst:
            gm_raw = fin_val(s, "gross_profit_rate")
            if gm_raw == 0.0:                    # 出厂检查:关键财务字段 0.0 → 记录待确认(不当真值)
                zero_flag.append(s.stock_code)
            got[s.stock_code] = {"market_val": float(getattr(s, "market_val", 0) or 0),
                                 "ocf_ttm": fin_val(s, "operating_cash_flow_ttm"),
                                 "gross_margin": margin_or_null(s, "gross_profit_rate"),
                                 "debt_asset": fin_val(s, "debt_asset_rate"),
                                 "net_margin": margin_or_null(s, "net_profit_rate"),
                                 "ebitda_margin": margin_or_null(s, "ebitda_margin"),
                                 "_fin_quarter": "ANNUAL"}
        begin += len(lst)
        if last or not lst or begin >= cnt:
            break
        time.sleep(4)
    return got, err, zero_flag


# ── 60日均成交额 + K型（同一次 kline）──
def _kline60(ctx, ft, code):
    try:
        ret, df, _ = ctx.request_history_kline(code, ktype=ft.KLType.K_DAY, autype=ft.AuType.QFQ, max_count=60)
        if ret == ft.RET_OK and len(df):
            return df
    except Exception:
        return None
    return None


def _turn_and_ktype(df):
    tv = [float(x) for x in df["turnover"].tolist()] if "turnover" in df.columns else []
    closes = [float(x) for x in df["close"].tolist()]
    highs = [float(x) for x in df["high"].tolist()]
    lows = [float(x) for x in df["low"].tolist()]
    vols = [float(x) for x in df["volume"].tolist()]
    n = len(closes)
    avg_tv = (sum(tv) / len(tv)) if tv else None
    kt = None
    if n >= 60:
        ma20 = sum(closes[-20:]) / 20; ma50 = sum(closes[-50:]) / 50
        sig = {"①收盘跌破MA20": closes[-1] < ma20, "②MA20下穿MA50": ma20 < ma50,
               "③高点走低": max(highs[-20:]) < max(highs[-40:-20]),
               "④低点走低": min(lows[-20:]) < min(lows[-40:-20]),
               "⑤破60低+放量": (closes[-1] <= min(lows[-60:]) * 1.02) and (vols[-1] > sum(vols[-20:]) / 20),
               "⑥距60高回撤>15%": (max(closes[-60:]) - closes[-1]) / max(closes[-60:]) > 0.15}
        kt = {"down": sum(1 for v in sig.values() if v), "sig": {k: bool(v) for k, v in sig.items()}}
    return avg_tv, kt, n


def pct_rank(val, arr):
    """val 在 arr(非None) 中的分位0~100(越大越高)。"""
    xs = sorted(x for x in arr if x is not None)
    if not xs or val is None:
        return None
    below = sum(1 for x in xs if x < val)
    return round(below / len(xs) * 100, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="20260721")
    ap.add_argument("--prev", default="20260720")
    a = ap.parse_args()
    date, prev = a.date, a.prev
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    SCREEN.mkdir(parents=True, exist_ok=True)
    et = ext_time(); fx = live_fx()
    man = {"派工单": "首轮重跑_财务改评分制_20260721(A案)", "date": date, "started_local": now_jst(),
           "external_server_time": et, "FX_live": fx, "params": PARAMS, "outputs": {}}
    if not port_open():
        man["FATAL"] = "OpenD 未开→未生产·不顶充"; print(write_json(f"_run2_{date}.json", man)); return 1
    if not fx.get("ok"):
        man["FATAL"] = "实时FX取不到→不用假设值·JP市值门槛无法换算·本轮暂停JP市值口径";
        # 仍继续但JP用标注(不静默)；这里选择继续并在JP标注
    FXV = fx.get("USDJPY")

    import futu as ft
    ctx = ft.OpenQuoteContext(host="127.0.0.1", port=11111)
    try:
        # step0 / 0.5 复用 first_scan 的记录
        import first_scan as FS
        perm = FS.step0_account_perm(date); man["outputs"]["account_perm"] = write_json(f"account_perm_{date}.json", perm)
        kr = FS.step05_kr(ctx, ft); man["outputs"]["kr"] = write_json(f"kr_targets_{date}.json", kr)
        print("step0/0.5 ✓", kr["结论"][:30])

        uni = step1_universe(ctx, ft)
        man["outputs"]["universe"] = write_json(f"universe_{date}.json", uni)
        # 市场级取数是否成功(成功=有主板代码清单)。失败→其mktcap股标 MARKET_FETCH_FAIL(计入缺失·非OTC非本轮不做)
        market_ok = {mk: bool(uni["primary_codes"].get(mk)) for mk in ("US", "JP")}
        man["market_fetch_ok"] = market_ok
        print("step1 universe ✓ US_ok=%s JP_ok=%s" % (market_ok["US"], market_ok["JP"]))

        # step2 市值(全过滤·含无财务者) + 财务(combo·子集) → 合并·不漏股
        import first_scan as FS
        min_mkt = PARAMS["硬准入_1_最低市值_美元"]
        us_mk, _e1 = FS._filter_mktcap(ctx, ft, ft.Market.US, min_mkt); time.sleep(3)
        jp_min = min_mkt * FXV if FXV else 1e99
        jp_mk, _e2 = FS._filter_mktcap(ctx, ft, ft.Market.JP, jp_min); time.sleep(3)
        us_fin, us_err, us_zero = _filter_fin(ctx, ft, ft.Market.US, min_mkt); time.sleep(3)
        jp_fin, jp_err, jp_zero = _filter_fin(ctx, ft, ft.Market.JP, jp_min); time.sleep(2)
        man["财务字段0_0报警"] = {"_说明": "关键财务字段(毛利率)返回0.0→已按数据未接(null)处理·不当真值·待人工确认(董事长2026-07-21出厂检查)",
                          "US命中数": len(us_zero), "JP命中数": len(jp_zero),
                          "样本": (us_zero[:10] + jp_zero[:10])}
        # 合并:市值过滤的全体为准(无财务者财务字段=None·不漏)
        mktcap_fin = {}
        for code, mv in {**us_mk, **jp_mk}.items():
            f = us_fin.get(code) or jp_fin.get(code) or {}
            mktcap_fin[code] = {"market_val": mv, "ocf_ttm": f.get("ocf_ttm"), "gross_margin": f.get("gross_margin"),
                                "debt_asset": f.get("debt_asset"), "net_margin": f.get("net_margin"),
                                "ebitda_margin": f.get("ebitda_margin"),
                                "_no_fin_data": (code not in us_fin and code not in jp_fin)}
        # 分批兜底分类(问题3):某市场全集(basicinfo)未取得→用 code_list 分批取 mktcap股 exchange·可靠避开超时
        fetch_failed = set()
        classify_batches = {}
        for mk in ("US", "JP"):
            if market_ok.get(mk):
                continue
            codes = [c for c in mktcap_fin if c.startswith(mk + ".")]
            MK = ft.Market.US if mk == "US" else ft.Market.JP
            exch, failed, batches = classify_pool(ctx, ft, MK, codes)
            classify_batches[mk] = {**batches, "分批取到分类": len(exch), "该批未取得(计入缺失)": len(failed)}
            prim = uni["primary_codes"].setdefault(mk, []); otcc = uni["otc_codes"].setdefault(mk, [])
            for c, e in exch.items():
                (prim if e in PRIMARY_EXCH else otcc).append(c)
            fetch_failed |= set(failed)
            if exch:
                market_ok[mk] = True         # 分批取到了分类→该市场视为可用(失败批单列缺失)
            uni["method"][mk] = f"分批 code_list basicinfo 兜底(全集超时)·取到分类 {len(exch)}·未取得 {len(failed)}"
        man["classify_batches"] = classify_batches
        man["market_fetch_ok"] = market_ok

        primary = set(uni["primary_codes"].get("US", [])) | set(uni["primary_codes"].get("JP", []))
        pool, otc_pass, fail_pass = [], [], []
        for c in mktcap_fin:
            mk = c.split(".")[0]
            if c in fetch_failed or not market_ok.get(mk):
                fail_pass.append(c)          # 全集/该批未取得→缺失(计入缺失率·非OTC·非本轮不做)
            elif c in primary:
                pool.append(c)
            else:
                otc_pass.append(c)           # 确认OTC(basicinfo的US_PINK)·本轮不做·不计缺失
        print("step2 市值+财务 ✓ 主板过市值=%d (OTC剔除=%d·市场取数失败=%d)" % (len(pool), len(otc_pass), len(fail_pass)))

        # step2b 60日均成交额 + K型（逐只 kline）·可复用上次已算好的(日股不必重拉·董事长2026-07-21)
        cache = {}
        pg = SCREEN / f"gate_{date}.json"
        if pg.exists():
            try:
                pgd = json.loads(pg.read_text(encoding="utf-8"))
                for c, r in pgd.get("per_stock", {}).items():
                    tv = r.get("avg_turnover_60d_usd")
                    if tv is not None:
                        cache[c] = {"tv_usd": tv, "down": r.get("ktype_down"), "bars": r.get("kline_bars")}
            except Exception:
                pass
        kdata = {}; n_cache = n_pull = 0
        for i, code in enumerate(pool):
            is_jp = code.startswith("JP.")
            if code in cache:                       # 复用已算(成交额60日均+K型)·不重拉
                kdata[code] = {"avg_tv_usd": cache[code]["tv_usd"], "down": cache[code]["down"],
                               "bars": cache[code]["bars"], "src": "复用上次kline"}
                n_cache += 1; continue
            df = _kline60(ctx, ft, code)
            if df is None:
                kdata[code] = {"avg_tv_usd": None, "down": None, "bars": 0, "src": "nodata"}
            else:
                avg_tv, kt, n = _turn_and_ktype(df)
                avg_tv_usd = (avg_tv / FXV if (is_jp and FXV and avg_tv is not None) else avg_tv)
                kdata[code] = {"avg_tv_usd": avg_tv_usd, "down": (kt["down"] if kt else None), "bars": n, "src": "kline"}
            n_pull += 1
            if n_pull % 50 == 0:
                print("  kline pull %d (cache %d)" % (n_pull, n_cache))
            time.sleep(0.7)
        print("step2b 60日均成交额+K型 ✓ 复用 %d·新拉 %d (共 %d)" % (n_cache, n_pull, len(pool)))

        # 组装 per-stock
        min_tv = PARAMS["硬准入_2_最低60日均成交额_美元"]
        per = {}
        for code in mktcap_fin:
            is_jp = code.startswith("JP.")
            fin = mktcap_fin[code]
            rec = {"code": code, "market": code.split(".")[0],
                   "market_val_native": fin["market_val"],
                   "market_val_usd": (fin["market_val"] / FXV if (is_jp and FXV) else fin["market_val"]),
                   "ocf_ttm": fin["ocf_ttm"], "gross_margin": fin["gross_margin"],
                   "debt_asset": fin["debt_asset"], "net_margin": fin["net_margin"], "ebitda_margin": fin["ebitda_margin"]}
            if code in fail_pass:
                rec.update({"listing": f"{code.split('.')[0]}全集拉取失败·未取得", "conclusion": "无法判定",
                            "reason_code": "MARKET_FETCH_FAIL",
                            "reason": f"{code.split('.')[0]}全集拉取失败·未取得(计入缺失率·非OTC·非本轮不做)"})
                per[code] = rec; continue
            if code in otc_pass:
                rec.update({"listing": "OTC/非主板", "conclusion": "本轮不做", "reason_code": "OTC_NONEXEC",
                            "reason": "美股OTC(确认粉单US_PINK)本轮不做·不计入缺失率"})
                per[code] = rec; continue
            rec["listing"] = "主板"
            kd = kdata.get(code, {})
            avg_tv_usd = kd.get("avg_tv_usd")
            rec["avg_turnover_60d_usd"] = avg_tv_usd
            rec["kline_bars"] = kd.get("bars")
            down = kd.get("down")
            rec["ktype_down"] = down
            # 硬准入判定
            if avg_tv_usd is None:
                rec.update({"conclusion": "无法判定", "reason_code": "NODATA_TURNOVER",
                            "reason": "60日均成交额数据本身取不到(kline未返回)·不估算"}); per[code] = rec; continue
            if avg_tv_usd < min_tv:
                rec.update({"conclusion": "落选", "reason_code": "TURNOVER",
                            "reason": f"查过不合格·60日均成交额 {avg_tv_usd/1e6:.1f}M < 100M(门槛2)"}); per[code] = rec; continue
            ocf = fin["ocf_ttm"]
            if ocf is None:
                rec.update({"conclusion": "研究基准", "reason_code": "OCF_NODATA",
                            "reason": "经营性现金流数据未接(非落选·没查到≠不合格)→研究基准池·不进可执行候选"}); per[code] = rec; continue
            if ocf <= 0:
                # 董事长2026-07-21:OCF为负不当落选依据(落选=查过不合格·而这里是用错了尺)。
                # 投资控股/资管类价值来自持股增值非经营现金流(如软银)→改判研究基准·标注须人工确认商业模式。
                # (架构师提的"按行业识别投资控股→改判净资产增减/投资收益"分支=待董事长拍板·本轮未实施·仅用保守兜底)
                rec.update({"conclusion": "研究基准", "reason_code": "OCF_NEG_HOLDING_CHECK",
                            "reason": f"OCF为负(OCF_TTM={ocf/1e9:.2f}B≤0)·须人工确认商业模式"
                                      f"(投资控股/资管类价值来自持股增值·非经营现金流·可能用错尺)→研究基准池·非落选"})
                per[code] = rec; continue
            if down is not None and down >= PARAMS["6_K型向下排除阈值"]:
                rec.update({"conclusion": "落选", "reason_code": "KTYPE",
                            "reason": f"查过不合格·K型向下{down}项≥3(门槛6)"}); per[code] = rec; continue
            # 三项硬准入全过 → 入围(财务质量另行评分·即使部分维度缺)
            rec.update({"conclusion": "入围", "reason_code": "PASS",
                        "reason": "三项硬准入全过(市值/60日均成交额/OCF>0)·财务质量见评分·行业强度与预测由架构师补"})
            per[code] = rec
        # 入围池
        inbound = [c for c, r in per.items() if r["conclusion"] == "入围"]

        # step3 财务五维评分(行业分位)
        # 行业 tag
        tags = {}
        for i in range(0, len(inbound), 200):
            part = inbound[i:i + 200]
            try:
                ret, df = ctx.get_owner_plate(part)
                if ret == ft.RET_OK:
                    for _, r in df.iterrows():
                        tags.setdefault(str(r.get("code")), []).append(str(r.get("plate_name")))
            except Exception:
                pass
            time.sleep(2)
        # 每只主行业=第一个板块
        def main_ind(c):
            ps = tags.get(c, [])
            return ps[0] if ps else "(未归类)"
        # 维度取值(入围池)
        dim_val = {c: {
            "自由现金流": (per[c]["ocf_ttm"]),      # 缺capex→以OCF近似(标注)
            "毛利率": per[c]["gross_margin"],
            "资产负债": (100 - per[c]["debt_asset"]) if per[c]["debt_asset"] is not None else None,  # 越低负债越好→反向
            "在手订单": None,                        # OpenD无·数据未接
            "成本优势": None,                        # OpenD无·数据未接
        } for c in inbound}
        # 行业内分位
        by_ind = {}
        for c in inbound:
            by_ind.setdefault(main_ind(c), []).append(c)
        W = PARAMS["财务五维权重"]
        scores = {}
        miss_count = {d: 0 for d in W}
        for c in inbound:
            ind = main_ind(c); peers = by_ind[ind]
            dims = {}; total = 0.0; wsum = 0.0; miss = 0
            for d, w in W.items():
                v = dim_val[c][d]
                if v is None:
                    dims[d] = {"score": 0, "status": "数据未接", "pct": None}
                    miss += 1; miss_count[d] += 1
                else:
                    arr = [dim_val[p][d] for p in peers]
                    pr = pct_rank(v, arr)
                    dims[d] = {"score": pr if pr is not None else 0, "status": "OK", "pct": pr, "raw": v}
                    if pr is not None:
                        total += pr * w; wsum += w
            fq = round(total / wsum, 1) if wsum else 0.0
            scores[c] = {"industry": ind, "financial_quality_score": fq, "缺维度数": miss,
                         "维度": dims, "note": "自由现金流以OCF近似(缺capex);毛利率仅当前值(8季趋势缺·下轮补);在手订单/成本优势 OpenD无→0分未接"}
        fin_miss_rate = {d: {"缺": miss_count[d], "共": len(inbound),
                             "缺失率_pct": (round(miss_count[d] / len(inbound) * 100, 1) if inbound else None)} for d in W}

        # 结论统计(五选一)
        from collections import Counter
        concl = Counter(r["conclusion"] for r in per.values())
        rc = Counter(r["reason_code"] for r in per.values())

        # 漏斗对比(load prev)
        prevrun = SCREEN / f"_run_{prev}.json"; prevgate = SCREEN / f"gate_{prev}.json"; prevc = SCREEN / f"candidates_{prev}.json"
        funnel = {"环节": ["全集US", "全集JP", "过市值(主板)US", "过市值(主板)JP", "过成交额(poolB)", "入围", "无法判定", "落选"],
                  "上轮_20260720": {}, "本轮_20260721": {}}
        try:
            pg = json.loads(prevgate.read_text(encoding="utf-8")); pc = json.loads(prevc.read_text(encoding="utf-8"))
            funnel["上轮_20260720"] = {
                "全集US": pg["counts"]["universe_total"]["US"], "全集JP": pg["counts"]["universe_total"]["JP"],
                "过市值主板US": pg["counts"].get("pass_mktcap_primary(主板)", {}).get("US"),
                "过市值主板JP": pg["counts"].get("pass_mktcap_primary(主板)", {}).get("JP"),
                "过成交额poolB": pg["counts"].get("pass_mktcap_and_turnover"),
                "入围": pc["summary"].get("入围", 0), "无法判定": pc["summary"].get("无法判定", 0),
                "落选": pc["summary"].get("落选", 0), "口径注": "上轮成交额=当日近似·净负债硬门槛致0入围/386无法判定"}
        except Exception as e:
            funnel["上轮_20260720"] = {"error": f"读上轮失败:{e}"}
        us_mk_primary = sum(1 for c in pool if c.startswith("US."))
        jp_mk_primary = sum(1 for c in pool if c.startswith("JP."))
        pass_tv = sum(1 for c, r in per.items() if r.get("avg_turnover_60d_usd") is not None and r["avg_turnover_60d_usd"] >= min_tv and r["listing"] == "主板")
        funnel["本轮_20260721"] = {
            "全集US": uni["counts"]["US"].get("excl_delisted"), "全集JP": uni["counts"]["JP"].get("excl_delisted"),
            "过市值主板US": us_mk_primary, "过市值主板JP": jp_mk_primary, "过成交额poolB": pass_tv,
            "入围": concl.get("入围", 0), "无法判定": concl.get("无法判定", 0), "落选": concl.get("落选", 0),
            "研究基准(OCF未接)": concl.get("研究基准", 0),
            "口径注": f"成交额=60日均(真算)·财务改评分制·FX实时{FXV}"}
        # BWXT/NRG 复核
        recheck = {}
        for w in ["US.BWXT", "US.NRG"]:
            r = per.get(w)
            if r:
                recheck[w] = {"上轮": "落选·日均成交额<1亿(当日近似)",
                              "本轮60日均成交额_usd": r.get("avg_turnover_60d_usd"),
                              "本轮结论": r.get("conclusion"), "原因": r.get("reason")}
            else:
                recheck[w] = "不在本轮市值+财务过滤结果(可能市值未过或无财务数据)"

        # 落盘
        man["outputs"]["gate_fin"] = write_json(f"gate_{date}.json", {
            "params": PARAMS, "FX_live": fx, "counts": {
                "universe": {k: uni["counts"][k].get("excl_delisted") for k in ("US", "JP")},
                "mktcap_fin_all": {"US": len(us_fin), "JP": len(jp_fin)},
                "mktcap_primary_pool": len(pool), "otc_excluded": len(otc_pass),
                "过60日均成交额": pass_tv},
            "结论分布_五选一": dict(concl), "reason_code分布": dict(rc),
            "filter_errors": {"US": us_err, "JP": jp_err}, "per_stock": per})
        man["outputs"]["fin_score"] = write_json(f"fin_score_{date}.json", {
            "_说明": PARAMS["财务评分口径"], "入围数": len(inbound),
            "财务五维缺失率": fin_miss_rate, "scores": scores})
        man["outputs"]["funnel_compare"] = write_json(f"funnel_compare_{date}.json",
                                                      {"漏斗对比": funnel, "BWXT_NRG复核": recheck})
        # candidates(五选一)
        cand = sorted(per.values(), key=lambda x: ({"入围": 0, "研究基准": 1, "无法判定": 2, "落选": 3, "本轮不做": 4}.get(x["conclusion"], 9),
                                                   -(x.get("avg_turnover_60d_usd") or 0)))
        for c in cand:
            if c["code"] in scores:
                c["financial_quality_score"] = scores[c["code"]]["financial_quality_score"]
                c["财务质量缺维度数"] = scores[c["code"]]["缺维度数"]
        man["outputs"]["candidates"] = write_json(f"candidates_{date}.json", {
            "_五选一说明": "入围/落选/研究基准/无法判定/本轮不做。落选=查过不合格;研究基准=没查到(OCF未接)或韩股;无法判定=市值/成交额数据取不到。"
                        "不出任何行动字段·不生成 actionable。", "summary": dict(concl), "total": len(cand), "candidates": cand})

        # 漏筛四检查
        watch = ["JP.7011", "US.GEV", "JP.6501", "US.CEG", "US.BWXT", "JP.8035", "US.VST", "US.NRG"]
        cov = _coverage(uni, per, tags, watch, inbound, by_ind, market_ok)
        man["outputs"]["coverage_alert"] = write_json(f"coverage_alert_{date}.json", cov)
        print("结论五选一:", dict(concl))
    finally:
        ctx.close()

    # 覆盖率(主板·美日)·全集拉取失败的市场→计入缺失率·不得标『不计』
    def covr(mk):
        uc = uni["counts"].get(mk, {})
        stocks = [c for c in per if c.startswith(mk + ".")]
        fail = sum(1 for c in stocks if per[c]["reason_code"] == "MARKET_FETCH_FAIL")
        if not market_ok.get(mk):
            return {"全集取数": "失败·未取得(计入缺失率)", "预期全集参照": 13012 if mk == "US" else 3751,
                    "实际取到全集": None, "mktcap股(来自server-filter)": len(stocks),
                    "未取得计入缺失": fail, "缺失率_pct": 100.0,
                    "注": f"{mk}全集拉取失败→本轮该市场【缺席】·计入缺失率·不得称本市场已扫描"}
        pm = [c for c in stocks if per[c].get("listing") == "主板"]
        nod = sum(1 for c in pm if per[c]["reason_code"] == "NODATA_TURNOVER")
        return {"全集取数": "成功", "全集": uc.get("excl_delisted"), "主板": uc.get("primary_listed"),
                "OTC(不做·不计缺失)": uc.get("otc_nonexec"), "主板过市值": len(pm),
                "成交额60日均缺失(NODATA)": nod,
                "缺失率_pct": (round(nod / len(pm) * 100, 2) if pm else None)}
    actual_cov = "美日全量扫描" if all(market_ok.values()) else (
        "实际覆盖：" + "＋".join([f"{m}全量" for m in ("US", "JP") if market_ok.get(m)] +
                             [f"{m}缺席·未取得" for m in ("US", "JP") if not market_ok.get(m)]))
    man["本轮实际覆盖范围"] = actual_cov
    man["覆盖率_美日"] = {"US": covr("US"), "JP": covr("JP"),
                     "口径": "分母=主板过市值;成交额=60日均(kline真算);OTC/港新欧不计缺失率;"
                           "★全集拉取失败的市场→计入缺失率·不得标『不计』;缺失率>20%不得称已完成全量筛选;"
                           f"本轮实际覆盖=【{actual_cov}】"}
    man["脚本指纹"] = {"first_scan2.py": sha256_file(ROOT / "scripts" / "first_scan2.py"),
                    "first_scan.py": sha256_file(ROOT / "scripts" / "first_scan.py")}
    man["可重跑说明"] = "原始数据快照=universe/gate/fin_score等JSON;真离线replay需另存OpenD原始响应(未实现·如实标)。"
    man["finished_local"] = now_jst()
    print("_run2 ✓", write_json(f"_run2_{date}.json", man))
    print("覆盖率US", man["覆盖率_美日"]["US"]); print("覆盖率JP", man["覆盖率_美日"]["JP"])
    return 0


def _coverage(uni, per, tags, watch, inbound, by_ind, market_ok=None):
    market_ok = market_ok or {}
    cand = list(per.values())
    no_reason = [c["code"] for c in cand if c["conclusion"] == "落选" and not c.get("reason")]
    chk1 = {"检查": "逐只落选原因完整性", "落选无原因数": len(no_reason),
            "结果": ("无警报" if not no_reason else "不合格"), "样本": no_reason[:10]}
    by_plate = {}
    for c in cand:
        for p in tags.get(c["code"], ["(未归类)"]):
            by_plate.setdefault(p, []).append(c)
    ind_alerts = []
    for p, ms in by_plate.items():
        if p == "(未归类)":
            continue
        reasons = {m["reason_code"] for m in ms}
        if len(ms) >= 3 and len(reasons) == 1 and next(iter(reasons)) in ("TURNOVER", "KTYPE", "OCF_NEG"):
            ind_alerts.append({"行业": p, "只数": len(ms), "同一规则": next(iter(reasons))})
    chk2 = {"检查": "整行业被同一规则筛掉", "结果": ("无警报" if not ind_alerts else "报警"), "明细": ind_alerts[:20]}
    chk3 = {"检查": "强势行业未覆盖", "结果": "无法执行(行业强度未评分·缺第三方行业报告)",
            "说明": "依赖第三方行业报告·Code拿不到·由架构师人工补·不写无警报"}
    cset = {c["code"]: c for c in cand}
    roll = []
    for w in watch:
        c = cset.get(w)
        if c:
            roll.append({"code": w, "状态": f"在结果中·结论={c['conclusion']}·{c['reason'][:50]}"})
        else:
            roll.append({"code": w, "状态": "不在市值+财务过滤结果(市值未过或无财务数据)"})
    n_missing = sum(1 for x in roll if "不在" in x["状态"])
    chk4 = {"检查": "点名核对清单", "结果": ("无警报·8只均已定位" if n_missing == 0 else f"{n_missing}只未定位"),
            "说明": "只用于事后核对·三星/SK海力士属定向查询不列入", "逐只": roll}
    # 检查5 市场级缺失警报(新增·董事长2026-07-21)：某市场成功读取=0或缺失率>50%→报警·不得称『美日全量扫描』
    mkt_alerts = []
    for mk in ("US", "JP"):
        stocks = [c for c in per if c.startswith(mk + ".")]
        fail = sum(1 for c in stocks if per[c]["reason_code"] == "MARKET_FETCH_FAIL")
        total = len(stocks)
        rate = round(fail / total * 100, 1) if total else None
        if (not market_ok.get(mk)) or (total > 0 and total == fail) or (rate is not None and rate > 50):
            mkt_alerts.append({"市场": mk, "全集取数成功": market_ok.get(mk), "该市场mktcap股": total,
                               "其中未取得": fail, "缺失率%": rate,
                               "警报": f"{mk}市场整体无数据/缺失>50%·本轮不得称『美日全量扫描』·须改称实际覆盖范围"})
    actual_cov = "美日全量扫描" if not mkt_alerts else (
        "实际覆盖：" + "＋".join([f"{m}全量" for m in ("US", "JP") if market_ok.get(m)] +
                             [f"{m}缺席(未取得)" for m in ("US", "JP") if not market_ok.get(m)]))
    chk5 = {"检查": "市场级缺失警报(新增·第5项)", "结果": ("无警报" if not mkt_alerts else "报警"),
            "明细": mkt_alerts, "本轮实际覆盖范围": actual_cov,
            "说明": "某市场成功读取=0或缺失率>50%→报警·且本轮改称实际覆盖范围(不得称美日全量扫描·把失败说成范围决定)"}
    return {"checks": [chk1, chk2, chk3, chk4, chk5], "五项均已输出": True, "本轮实际覆盖范围": actual_cov}


if __name__ == "__main__":
    raise SystemExit(main())
