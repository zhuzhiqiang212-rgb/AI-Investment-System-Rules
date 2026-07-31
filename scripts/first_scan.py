#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""首轮扫描：美日全量扫描 ＋ 韩股定向两只（派工单_首轮扫描_美日全量加韩股定向_20260720）

铁律遵循：
  · 只读 OpenD 行情与财务，不下单、不动交易。
  · 不产生任何买卖清单；筛选结论只四选一：入围/落选/无法判定/研究基准 + 原因代码。
  · 参数全部用第三节批准的暂行值，Code 不自行优化。
  · 取不到即 null 写原因，严禁估算/相邻日/旧值顶充。
  · 港股/新加坡/欧洲本轮不做；韩股是"定向查2只"，不是"扫描韩国市场"。
  · 数据源只有 OpenD：市值/成交额可取；财务(现金流/净负债)覆盖未验证，取不到如实标缺失；
    行业增长/市场份额 Code 拿不到第三方源，如实大面积标缺失，由架构师人工补。

产出（data/screen/ 下，全部 _20260720）：
  account_perm / universe / gate / industry / leader / ktype / valuation / candidates / coverage_alert / _run
用法： python scripts/first_scan.py [--date 20260720] [--kline-cap N]
"""
from __future__ import annotations
import argparse, json, hashlib, socket, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data" / "screen"
JST = timezone(timedelta(hours=9))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

# ── 第三节 批准参数（暂行值·Code 不得改）──────────────────────
PARAMS = {
    "1_最低市值_美元": 10_000_000_000,
    "2_最低日均成交额_美元": 100_000_000,
    "3_净负债倍数": 4.0,
    "3_净负债_公用事业基建": "行业中位数±1倍",
    "4_财务考察期": "最近4个季度",
    "5_行业强度权重": {"需求增速": 30, "供需紧张": 25, "盈利趋势": 20, "政策资本": 15, "相对大盘": 10},
    "6_K型向下排除阈值": 3,
    "7_行业强度强分数线": 70,
    "7_说明": "首轮试跑值·不得声称已验证有效",
    "8_驱动重叠度": "定性三档·不设数字线",
    "9_行情价格时限_交易日": 2,
    "10_财务数据时限_自然日": 120,
    "11_一致预期时限_自然日": 60,
    "12_行业报告时限_自然日": 365,
    "13_账户权限时限_自然日": 7,
    "_11到13说明": "无外部依据·架构师提出·首轮跑完须回看调整",
}
# 汇率：JP 市值/成交额以 JPY 计价，须换算成美元门槛比较。取不到实时 FX → 用假设值并在 _run 标注待确认。
FX_ASSUMED_USDJPY = 155.0   # 假设值·首轮·须架构师确认（OpenD 无直接 forex 源时用此换算 JP 门槛）

KLINE_CAP_DEFAULT = 120     # 逐日线扫描的安全上限（K型/相对强弱）；超出按成交额排序取前 N，其余如实标 pending

REASON = {
    "MKTCAP": "落选·市值 < 100亿美元（门槛1）",
    "TURNOVER": "落选·日均成交额 < 1亿美元（门槛2·当日成交额近似·见说明）",
    "NETDEBT": "落选·净负债 > 4倍（门槛3）",
    "KTYPE": "落选·K型向下信号 ≥3项（门槛6）",
    "NODATA_TURNOVER": "无法判定·成交额数据未接（OpenD 未返回·不估算）",
    "PASS": "入围·过全部可核门槛（行业强度/龙头/预测由架构师在机器候选之上补）",
    "UNDECIDED_FIN": "无法判定·净负债所需财务未接（OpenD 未返回·不估算）",
    "OTC_NONEXEC": "非可执行范围·OTC/Pink粉单市场（OpenD 不提供OTC行情·非主板上市·与港新欧同类:本轮不可执行·不计入缺失率）",
}
PRIMARY_EXCH = {"US_NYSE", "US_NASDAQ", "US_AMEX", "JP_TSE"}   # 主板;US_PINK=OTC粉单→不可执行范围


def now_jst():
    return datetime.now(JST).isoformat(timespec="seconds")


def ext_time():
    try:
        import forecast_lock as FL
        return FL.external_time()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": f"external_time 调用失败: {e}"}


def sha256_file(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def write_json(name: str, obj) -> dict:
    SCREEN.mkdir(parents=True, exist_ok=True)
    p = SCREEN / f"{name}"
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    raw = p.read_bytes()
    return {"file": str(p.relative_to(ROOT)).replace("\\", "/"), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "written_at_local": now_jst(),
            "mojibake_EFBFBD": raw.count(b"\xef\xbf\xbd")}


def port_open(host="127.0.0.1", port=11111, t=2.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(t)
    try:
        s.connect((host, port)); return True
    except Exception:
        return False
    finally:
        s.close()


# ── Step 0：账户权限（真实交易权限；只读记录·不动交易接口）───────
def step0_account_perm(date):
    # OpenD 交易权限须开交易上下文查询；本轮铁律"不动交易功能"→不开交易上下文。
    # 按已知事实记录权限矩阵，来源标注为"人工已知/开工必读"，并留 OpenD_trade_ctx_queried=false 诚实标注。
    perm = {
        "_说明": "本轮不动 OpenD 交易功能，故未开交易上下文查询实时权限；下列为开工必读/已知事实，来源人工。",
        "OpenD_trade_ctx_queried": False,
        "accounts": {
            "富途(Futu)": {"markets": ["US", "JP", "HK"], "KR": False, "note": "行情+交易权限含美日港；不含韩"},
            "SBI": {"markets": ["JP"], "note": "日股为主（软银进攻仓在此）"},
            "IBKR": {"markets": ["US", "多国"], "KR": "未确认", "note": "美股+多市场；韩股可交易性未经董事长确认"},
        },
        "韩股可交易性": "未获董事长确认（SBI/IBKR 是否可交易韩股）→ 韩股只进研究基准池，不进买卖清单",
        "权限时限_自然日": PARAMS["13_账户权限时限_自然日"],
    }
    return perm


# ── Step 0.5：韩股两只可取性验证 ─────────────────────────────
def step05_kr(ctx, ft):
    kr = ["KR.005930", "KR.000660"]
    res = {"targets": {"KR.005930": "三星电子", "KR.000660": "SK海力士"},
           "market_KR_supported": bool(getattr(ft.Market, "KR", None))}
    try:
        ret, df = ctx.get_market_snapshot(kr)
        res["snapshot_ret_ok"] = (ret == ft.RET_OK)
        res["snapshot_detail"] = (df.to_dict("records") if ret == ft.RET_OK else str(df))
    except Exception as e:  # noqa: BLE001
        res["snapshot_ret_ok"] = False
        res["snapshot_detail"] = f"{type(e).__name__}: {e}"
    res["结论"] = ("OpenD 不支持韩股行情（KR.* 代码被拒·Market 无 KR）·数据未接·不估算"
                 if not res.get("snapshot_ret_ok") else "OpenD 可取韩股·按研究基准池正常计算")
    # 替代观察工具（须标"替代工具·非原股"）
    alt = {}
    for orig, probe in [("KR.000660 SK海力士", "US.SKHY"), ("KR.005930 三星电子", "US.SSNLF")]:
        try:
            ret, df = ctx.get_market_snapshot([probe])
            if ret == ft.RET_OK:
                r = df.iloc[0]
                alt[orig] = {"替代工具": probe, "name": str(r.get("code")), "last_price": float(r.get("last_price")),
                             "性质": "替代工具·非原股·价格受汇率与流动性影响·仅供观察·不得据此买卖"}
            else:
                alt[orig] = {"替代工具": probe, "取到": False, "detail": str(df)[:60]}
        except Exception as e:  # noqa: BLE001
            alt[orig] = {"替代工具": probe, "取到": False, "detail": f"{type(e).__name__}"}
        time.sleep(1.5)
    res["替代观察工具"] = alt
    res["池归属"] = "研究基准池（可作行业对照/判断闪迪与东京电子相对强弱）·不得进买卖清单·不分配金额·不给第一二档执行价"
    return res


# ── Step 1：universe（美日全集）──────────────────────────────
def step1_universe(ctx, ft):
    uni = {"markets_scanned": ["US", "JP"], "markets_not_done": ["HK", "SG(新加坡)", "EU(欧洲)"],
           "not_done_说明": "本轮不做·董事长定『以后再说』·不计入缺失率（与『做了但缺』分开）",
           "korea": "定向查询2只·未做全市场扫描", "counts": {}, "codes": {}, "method": {}}
    for nm, mk in [("US", ft.Market.US), ("JP", ft.Market.JP)]:
        df = None
        for attempt in range(3):                       # basicinfo 响应大·重试3次
            ret, d = ctx.get_stock_basicinfo(mk, ft.SecurityType.STOCK)
            if ret == ft.RET_OK:
                df = d; break
            time.sleep(6)
        if df is not None:
            df2 = df[df.get("delisting") != True] if "delisting" in df.columns else df  # noqa: E712
            codes, primary, otc = [], set(), set()
            exch_dist = {}
            for _, r in df2.iterrows():
                ex = str(r.get("exchange_type", ""))
                exch_dist[ex] = exch_dist.get(ex, 0) + 1
                codes.append({"code": r["code"], "name": r.get("name", ""), "exch": ex})
                (primary if ex in PRIMARY_EXCH else otc).add(r["code"])
            uni["counts"][nm] = {"total_basicinfo": len(df), "excl_delisted": len(df2),
                                 "primary_listed": len(primary), "otc_nonexec": len(otc),
                                 "exchange_dist": exch_dist}
            uni["codes"][nm] = codes
            uni.setdefault("primary_codes", {})[nm] = sorted(primary)
            uni.setdefault("otc_codes", {})[nm] = sorted(otc)
            uni["method"][nm] = "get_stock_basicinfo(全集·含代码清单+交易所归类)"
        else:
            # basicinfo 超时→回退:用 server-filter(市值≥1)数『有市值数据的股票数』作分母·如实标口径
            sf = ft.SimpleFilter(); sf.stock_field = ft.StockField.MARKET_VAL
            sf.filter_min = 1; sf.is_no_filter = False
            cnt = None
            try:
                ret, ls = ctx.get_stock_filter(market=mk, filter_list=[sf], begin=0, num=10)
                if ret == ft.RET_OK:
                    cnt = ls[1]
            except Exception:
                pass
            uni["counts"][nm] = {"total_basicinfo": None, "excl_delisted": cnt,
                                 "note": "get_stock_basicinfo 超时(响应过大)→分母改用 server-filter『有市值数据的股票数』·非严格全部挂牌数·如实标"}
            uni["codes"][nm] = []                       # 无完整代码清单→点名核对改用逐只 snapshot 存在性
            uni["method"][nm] = "fallback: get_stock_filter(market_val>=1) all_count（basicinfo 超时）"
        time.sleep(3)
    return uni


# ── Step 2：门槛（市值 server-filter + 成交额 snapshot + 净负债 best-effort）──
def _filter_mktcap(ctx, ft, market, min_val):
    """server 端市值过滤·分页取全·返回 {code: market_val}。"""
    sf = ft.SimpleFilter(); sf.stock_field = ft.StockField.MARKET_VAL
    sf.filter_min = min_val; sf.is_no_filter = False
    got = {}; begin = 0
    while True:
        ret, ls = ctx.get_stock_filter(market=market, filter_list=[sf], begin=begin, num=200)
        if ret != ft.RET_OK:
            return got, str(ls)
        last, cnt, lst = ls
        for s in lst:
            got[s.stock_code] = float(getattr(s, "market_val", 0) or 0)
        begin += len(lst)
        if last or not lst or begin >= cnt:
            break
        time.sleep(3.5)
    return got, None


def _num(r, k):
    v = r.get(k)
    try:
        return float(v) if v not in (None, "", "N/A") else None
    except Exception:
        return None


def _snapshots(ctx, ft, codes, chunk=100):
    """批量 snapshot(只喂主板码·已排除OTC) → {code:{turnover,pe,price,pb}}。
    仍有个别码使整块报错时(如个别非常规证券)→拆成单只重试·把坏码单独丢弃·不牵连整块。"""
    out = {}
    def pull(part):
        ret, df = ctx.get_market_snapshot(part)
        if ret == ft.RET_OK:
            for _, r in df.iterrows():
                out[str(r.get("code"))] = {"turnover": _num(r, "turnover"), "pe_ttm": _num(r, "pe_ttm_ratio"),
                                           "last_price": _num(r, "last_price"), "pb": _num(r, "pb_ratio")}
            return True
        return False
    for i in range(0, len(codes), chunk):
        part = codes[i:i + chunk]
        ok = False
        try:
            ok = pull(part)
        except Exception:
            ok = False
        if not ok:                       # 整块失败→逐只，坏码单独丢
            for c in part:
                try:
                    pull([c])
                except Exception:
                    pass
                time.sleep(0.6)
        time.sleep(3)
    return out


def step2_gate(ctx, ft, uni, fx):
    min_mkt_usd = PARAMS["1_最低市值_美元"]
    min_tv_usd = PARAMS["2_最低日均成交额_美元"]
    # 市值门槛：US 用美元阈值；JP 用 JPY 阈值(=美元阈值×FX)
    a_us, err_us = _filter_mktcap(ctx, ft, ft.Market.US, min_mkt_usd); time.sleep(3)
    a_jp, err_jp = _filter_mktcap(ctx, ft, ft.Market.JP, min_mkt_usd * fx); time.sleep(3)
    passes_mktcap = {**a_us, **a_jp}   # code -> market_val(本币)
    # 主板 vs OTC:server-filter 的市值池含 US_PINK(OTC粉单)·OpenD不供OTC行情且会污染整块snapshot→先剔出，标不可执行范围
    primary_all = set(uni.get("primary_codes", {}).get("US", [])) | set(uni.get("primary_codes", {}).get("JP", []))
    have_listlist = bool(primary_all)
    mktcap_primary = {c: mv for c, mv in passes_mktcap.items() if (c in primary_all or not have_listlist)}
    mktcap_otc = [c for c in passes_mktcap if c not in mktcap_primary]
    # 成交额：只对主板码 snapshot（当日成交额近似日均·首轮·如实说明）；JP turnover 是 JPY→换成美元比较
    snaps = _snapshots(ctx, ft, list(mktcap_primary))
    per = {}
    poolB = []      # 过市值(主板)+成交额
    for code, mv in passes_mktcap.items():
        is_jp = code.startswith("JP.")
        if code in mktcap_otc:
            per[code] = {"code": code, "market_val_native": mv, "market_val_usd_approx": (mv / fx if is_jp else mv),
                         "pass_mktcap": True, "listing": "OTC/Pink(非主板)",
                         "pass_turnover": False, "gate_result": "非可执行范围", "reason_code": "OTC_NONEXEC"}
            continue
        sp = snaps.get(code, {})
        tv = sp.get("turnover")
        tv_usd = (tv / fx) if (tv is not None and is_jp) else tv
        rec = {"code": code, "market_val_native": mv, "listing": "主板",
               "market_val_usd_approx": (mv / fx if is_jp else mv),
               "turnover_native": tv, "turnover_usd_approx": tv_usd,
               "pe_ttm": sp.get("pe_ttm"), "pb": sp.get("pb"), "last_price": sp.get("last_price"),
               "pass_mktcap": True}
        if tv_usd is None:
            rec["pass_turnover"] = None; rec["gate_result"] = "无法判定"; rec["reason_code"] = "NODATA_TURNOVER"
        elif tv_usd < min_tv_usd:
            rec["pass_turnover"] = False; rec["gate_result"] = "落选"; rec["reason_code"] = "TURNOVER"
        else:
            rec["pass_turnover"] = True; rec["gate_result"] = "过门槛(待净负债/K型)"; rec["reason_code"] = None
            poolB.append(code)
        per[code] = rec
    n_primary_mktcap = {"US": sum(1 for c in mktcap_primary if c.startswith("US.")),
                        "JP": sum(1 for c in mktcap_primary if c.startswith("JP."))}
    gate = {
        "params": {"最低市值_美元": min_mkt_usd, "最低日均成交额_美元": min_tv_usd, "FX_USDJPY_assumed": fx},
        "成交额口径说明": "OpenD get_stock_filter 不支持成交额过滤字段→改用 get_market_snapshot 当日成交额近似日均，首轮如实标；JP 成交额按假设FX换算美元。",
        "主板口径说明": "OpenD 不提供美股 OTC(粉单/US_PINK) 行情，且含OTC码会使整块snapshot报错→已按 exchange_type 只保留主板(NYSE/NASDAQ/AMEX/TSE)。"
                    "OTC 与港新欧同类:本轮不可执行·单列不计入缺失率。",
        "净负债说明": "净负债倍数(门槛3)所需经营性财务，OpenD 快照未直接提供；本轮标 UNDECIDED_FIN(未接·不估算)，覆盖程度见八已知不足。",
        "counts": {
            "universe_total": {k: uni["counts"][k].get("excl_delisted") for k in ("US", "JP")},
            "pass_mktcap_all(含OTC)": {"US": len(a_us), "JP": len(a_jp)},
            "pass_mktcap_primary(主板)": n_primary_mktcap,
            "excluded_OTC_nonexec": len(mktcap_otc),
            "pass_mktcap_and_turnover": len(poolB),
            "undecided_turnover_nodata": sum(1 for r in per.values() if r["reason_code"] == "NODATA_TURNOVER"),
        },
        "filter_errors": {"US": err_us, "JP": err_jp},
        "per_stock": per, "poolB_codes": poolB,
    }
    return gate, poolB, snaps


# ── Step 3：行业强度（tag 可取·五指标多为人工补）─────────────
def step3_industry(ctx, ft, poolB):
    tags = {}
    for i in range(0, len(poolB), 200):
        part = poolB[i:i + 200]
        try:
            ret, df = ctx.get_owner_plate(part)
            if ret == ft.RET_OK:
                for _, r in df.iterrows():
                    tags.setdefault(str(r.get("code")), []).append(str(r.get("plate_name")))
        except Exception:
            pass
        time.sleep(2.5)
    industries = sorted({p for ps in tags.values() for p in ps})
    return {
        "_说明": "行业 tag 取自 OpenD get_owner_plate(所属板块)。行业强度五指标(需求增速/供需紧张/盈利趋势/政策资本/相对大盘)"
               "中，需求增速/供需/政策资本 依赖第三方行业报告，Code 拿不到 → 本轮大面积标『缺失·人工补』(见八已知不足)；"
               "相对大盘 可由指数对比机器算(step6)。故本表只给行业归类与成员，强度分数待人工补齐后由架构师定。",
        "stock_plates": tags,
        "industries_seen": industries,
        "五指标状态": {k: ("机器可算(step6)" if k == "相对大盘" else "缺失·需人工补第三方行业报告")
                   for k in PARAMS["5_行业强度权重"]},
        "行业强度分数": "本轮不机器编造(缺三方源)→留空待人工补·不得声称已评分",
    }


# ── Step 5：K型六信号（逐日线·对 poolB·有上限）────────────────
def _kline(ctx, ft, code, num=120):
    try:
        ret, df, _ = ctx.request_history_kline(code, ktype=ft.KLType.K_DAY, autype=ft.AuType.QFQ,
                                               max_count=num)
        if ret == ft.RET_OK and len(df):
            return df
    except Exception:
        return None
    return None


def _ktype_signals(df):
    """K型向下六信号（机器可判的价量结构·首轮口径）。返回(触发数, 明细)。"""
    import statistics as st
    closes = [float(x) for x in df["close"].tolist()]
    highs = [float(x) for x in df["high"].tolist()]
    lows = [float(x) for x in df["low"].tolist()]
    vols = [float(x) for x in df["volume"].tolist()]
    n = len(closes)
    sig = {}
    if n >= 60:
        ma20 = sum(closes[-20:]) / 20; ma50 = sum(closes[-50:]) / 50
        sig["①收盘跌破MA20"] = closes[-1] < ma20
        sig["②MA20下穿MA50"] = ma20 < ma50
        sig["③高点走低(近20<前20)"] = max(highs[-20:]) < max(highs[-40:-20])
        sig["④低点走低(近20<前20)"] = min(lows[-20:]) < min(lows[-40:-20])
        sig["⑤跌破近60低+放量"] = (closes[-1] <= min(lows[-60:]) * 1.02) and (vols[-1] > (sum(vols[-20:]) / 20))
        peak = max(closes[-60:]); sig["⑥距60日高回撤>15%"] = (peak - closes[-1]) / peak > 0.15 if peak else False
    else:
        return None, {"缺": f"K线不足60根(仅{n})→无法判K型·不估算"}
    down = sum(1 for v in sig.values() if v)
    return down, {k: bool(v) for k, v in sig.items()}


def step5_ktype(ctx, ft, poolB, gate_per, cap):
    order = sorted(poolB, key=lambda c: (gate_per.get(c, {}).get("turnover_usd_approx") or 0), reverse=True)
    scanned, pending = {}, []
    for i, code in enumerate(order):
        if i >= cap:
            pending.append(code); continue
        df = _kline(ctx, ft, code, 120)
        if df is None:
            scanned[code] = {"status": "NODATA", "reason": "OpenD 未返回日线·不估算"}
        else:
            down, detail = _ktype_signals(df)
            scanned[code] = {"status": "OK", "down_signals": down,
                             "excluded_by_ktype": (down is not None and down >= PARAMS["6_K型向下排除阈值"]),
                             "detail": detail}
        time.sleep(1.2)
    return {
        "_说明": f"K型六信号机器判(价量结构)·仅对过市值+成交额的 poolB·按成交额降序·上限 {cap} 只。"
               f"超上限 {len(pending)} 只如实标 pending(未跑日线·不估算)·下轮补。向下≥{PARAMS['6_K型向下排除阈值']}项→排除。",
        "cap": cap, "scanned_count": len(scanned), "pending_count": len(pending),
        "scanned": scanned, "pending_codes": pending,
    }


# ── Step 7：候选池（四选一 + 原因代码）────────────────────────
def step7_candidates(gate, ktype):
    per = gate["per_stock"]; kt = ktype["scanned"]
    cands = []
    for code, r in per.items():
        rc = r.get("reason_code")
        if rc == "OTC_NONEXEC":
            concl, reason = "落选", REASON["OTC_NONEXEC"]
        elif rc == "TURNOVER":
            concl, reason = "落选", REASON["TURNOVER"]
        elif rc == "NODATA_TURNOVER":
            concl, reason = "无法判定", REASON["NODATA_TURNOVER"]
        else:
            k = kt.get(code)
            if k and k.get("status") == "OK" and k.get("excluded_by_ktype"):
                concl, reason = "落选", REASON["KTYPE"]
            elif k and k.get("status") == "OK":
                # 过市值+成交额+K型；净负债未接→无法判定(不谎称入围)
                concl, reason = "无法判定", REASON["UNDECIDED_FIN"]
            elif k and k.get("status") == "NODATA":
                concl, reason = "无法判定", "无法判定·K型日线未接（不估算）"
            else:  # pending 未跑K线
                concl, reason = "无法判定", "无法判定·K型待跑(poolB超上限·下轮补)"
        cands.append({"code": code, "name": "", "market": code.split(".")[0],
                      "conclusion": concl, "reason_code": rc or ("KTYPE" if concl == "落选" and "K型" in reason else "UNDECIDED"),
                      "reason": reason,
                      "market_val_usd_approx": r.get("market_val_usd_approx"),
                      "turnover_usd_approx": r.get("turnover_usd_approx"),
                      "pe_ttm": r.get("pe_ttm"), "pb": r.get("pb")})
    order = {"入围": 0, "无法判定": 1, "研究基准": 2, "落选": 3}
    cands.sort(key=lambda x: (order.get(x["conclusion"], 9), -(x["turnover_usd_approx"] or 0)))
    summary = {}
    for c in cands:
        summary[c["conclusion"]] = summary.get(c["conclusion"], 0) + 1
    return {"_四选一说明": "本轮筛选结论只四选一:入围/落选/无法判定/研究基准+原因代码。"
                       "不出任何行动字段(可小额试买/到价再买等)——那须资金出口五项全通过·另存 actionable_·本轮不生成。"
                       "★净负债(门槛3)财务未接→凡仅缺净负债者一律『无法判定』·不谎称入围。",
            "summary": summary, "total": len(cands), "candidates": cands}


# ── Step 8：四项漏筛检查 ─────────────────────────────────────
def step8_coverage(uni, gate, industry, cands_doc, kr, exist_map=None):
    exist_map = exist_map or {}
    alerts = []
    cands = cands_doc["candidates"]
    # 1 逐只落选原因完整性
    no_reason = [c["code"] for c in cands if c["conclusion"] == "落选" and not c.get("reason")]
    chk1 = {"检查": "逐只落选原因完整性", "落选无原因数": len(no_reason),
            "结果": ("无警报" if not no_reason else "不合格"), "样本": no_reason[:10]}
    # 注：门槛市值未过的 universe 其余股，统一原因=MKTCAP（见下 chk 记明）
    # 2 整行业被同一规则筛掉
    plates = industry.get("stock_plates", {})
    by_plate = {}
    for c in cands:
        for p in plates.get(c["code"], ["(未归类)"]):
            by_plate.setdefault(p, []).append(c)
    ind_alerts = []
    for p, members in by_plate.items():
        if p == "(未归类)":
            continue                       # 未归类不是一个行业·跳过(OTC等无板块)
        reasons = {m["reason_code"] for m in members}
        # 只对『真门槛规则』报警;OTC_NONEXEC/NODATA 不算"规则筛掉整行业"
        if len(members) >= 3 and len(reasons) == 1 and next(iter(reasons)) in ("TURNOVER", "KTYPE"):
            ind_alerts.append({"行业": p, "只数": len(members), "同一规则": next(iter(reasons))})
    chk2 = {"检查": "整行业被同一规则筛掉", "结果": ("无警报" if not ind_alerts else "报警"), "明细": ind_alerts[:20]}
    # 3 强势行业未覆盖：本轮行业强度未评分(缺三方源)→无法判定该检查
    chk3 = {"检查": "强势行业未覆盖", "结果": "无法执行(行业强度未评分·缺第三方行业报告·见八)",
            "说明": "无『强』行业名单→本检查待人工补行业强度后重跑"}
    # 4 点名核对清单
    watch = ["JP.7011", "US.GEV", "JP.6501", "US.CEG", "US.BWXT", "JP.8035", "US.VST", "US.NRG"]
    uni_codes = {x["code"] for m in uni.get("codes", {}).values() for x in m}
    uni_have_list = {mk for mk, lst in uni.get("codes", {}).items() if lst}   # 哪些市场有完整代码清单
    cand_codes = {c["code"] for c in cands}
    roll = []
    for w in watch:
        mk = w.split(".")[0]
        if w in cand_codes:
            cc = next(c for c in cands if c["code"] == w)
            st = f"在扫描结果中·结论={cc['conclusion']}·{cc['reason']}"
        elif w in gate.get("per_stock", {}):
            st = "过市值门槛·未进 poolB(成交额未过/无数据)"
        elif mk in uni_have_list:
            st = ("不在全集(未被 basicinfo 返回或非普通股)" if w not in uni_codes
                  else "在全集但市值未过100亿门槛→落选·市值(门槛1)")
        elif exist_map.get(w) is True:
            st = "存在于该市场(snapshot证实)但市值未过100亿门槛→落选·市值(门槛1)"
        elif exist_map.get(w) is False:
            st = "snapshot 未证实存在(可能非普通股/代码变更)"
        else:
            st = "该市场全集代码清单缺失(basicinfo超时)·未能逐只核·如实标未核"
        roll.append({"code": w, "状态": st})
    n_missing = sum(1 for x in roll if "不在全集" in x["状态"] or "未核" in x["状态"])
    chk4 = {"检查": "点名核对清单", "结果": ("无警报·8只全部在扫描结果中已分类" if n_missing == 0 else f"{n_missing}只未能定位"),
            "说明": "只用于事后核对·未作扫描输入·三星/SK海力士属定向查询不列入本清单", "逐只": roll}
    return {"checks": [chk1, chk2, chk3, chk4],
            "四项均已输出": True,
            "备注": "即使无警报也输出『无警报』。检查3因行业强度未评分标『无法执行』·非跳过。"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="20260720")
    ap.add_argument("--kline-cap", type=int, default=KLINE_CAP_DEFAULT)
    a = ap.parse_args()
    date = a.date
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    SCREEN.mkdir(parents=True, exist_ok=True)
    et = ext_time()
    manifest = {"派工单": "首轮扫描_美日全量加韩股定向_20260720", "date": date,
                "本轮范围": "美日全量扫描 + 韩股定向两只(首轮)·港新欧不做·非全球",
                "started_local": now_jst(), "external_server_time": et, "params": PARAMS,
                "FX_USDJPY_assumed": FX_ASSUMED_USDJPY, "outputs": {}}

    if not port_open():
        manifest["FATAL"] = "OpenD(11111) 未开→本轮未生产·不顶充"
        info = write_json(f"_run_{date}.json", manifest)
        print("OpenD 未开·已如实记录未生产:", info); return 1

    import futu as ft
    ctx = ft.OpenQuoteContext(host="127.0.0.1", port=11111)
    try:
        perm = step0_account_perm(date)
        manifest["outputs"]["account_perm"] = write_json(f"account_perm_{date}.json", perm)
        print("step0 账户权限 ✓")

        kr = step05_kr(ctx, ft)
        manifest["outputs"]["kr_verify"] = write_json(f"kr_targets_{date}.json", kr)
        print("step0.5 韩股两只可取性 ✓ →", kr["结论"][:40])

        uni = step1_universe(ctx, ft)
        manifest["outputs"]["universe"] = write_json(f"universe_{date}.json", uni)
        print("step1 universe ✓ US=%s JP=%s" % (uni["counts"].get("US"), uni["counts"].get("JP")))

        gate, poolB, snaps = step2_gate(ctx, ft, uni, FX_ASSUMED_USDJPY)
        manifest["outputs"]["gate"] = write_json(f"gate_{date}.json", gate)
        print("step2 gate ✓ poolB(过市值+成交额)=%d" % len(poolB))

        industry = step3_industry(ctx, ft, poolB)
        manifest["outputs"]["industry"] = write_json(f"industry_{date}.json", industry)
        print("step3 industry ✓ 行业数=%d" % len(industry["industries_seen"]))

        # step4 leader：市场份额无法自动→缺失清单；财务未接→标缺失
        leader = {"_说明": "龙头四维(市场份额/技术成本/客户/财务)。市场份额+技术成本+客户依赖第三方/年报文本·无法全自动→"
                         "全部标『龙头地位未证实』并列入份额缺失清单(八已知不足)·由架构师人工补并标半自动。财务(净负债等)OpenD快照未直接给→缺失。",
                  "市场份额缺失清单": poolB, "四维状态": {"市场份额": "缺失·人工补", "技术成本": "缺失·人工补",
                                                  "客户结构": "缺失·人工补", "财务": "部分(PE/PB可取·净负债未接)"}}
        manifest["outputs"]["leader"] = write_json(f"leader_{date}.json", leader)
        print("step4 leader ✓ (份额缺失清单=%d·如实标半自动待补)" % len(poolB))

        ktype = step5_ktype(ctx, ft, poolB, gate["per_stock"], a.kline_cap)
        manifest["outputs"]["ktype"] = write_json(f"ktype_{date}.json", ktype)
        print("step5 K型 ✓ 已扫=%d pending=%d" % (ktype["scanned_count"], ktype["pending_count"]))

        # step6 valuation：PE/PB 已在 gate.per_stock；相对大盘强弱 = poolB vs 指数(简版:留待与K线合算)
        valuation = {"_说明": "估值(PE_TTM/PB)取自 snapshot·已随 gate.per_stock 落盘。相对大盘强弱须个股与指数区间对比·"
                            "与K型同源日线·本轮对已跑K线的池给相对强弱、未跑的标 pending。★不因相关性删任何标的·只标驱动重叠度(定性三档·不设数字线)。",
                     "驱动重叠度口径": PARAMS["8_驱动重叠度"],
                     "pe_pb_source": "gate_%s.json.per_stock" % date,
                     "相对大盘": "已跑K线者可算(step5日线)·未跑者 pending·不估算"}
        manifest["outputs"]["valuation"] = write_json(f"valuation_{date}.json", valuation)
        print("step6 valuation ✓")

        cands_doc = step7_candidates(gate, ktype)
        manifest["outputs"]["candidates"] = write_json(f"candidates_{date}.json", cands_doc)
        print("step7 candidates ✓ 四选一:", cands_doc["summary"])

        # 点名核对清单的存在性(basicinfo 超时时用 snapshot 逐只证实)
        watch = ["JP.7011", "US.GEV", "JP.6501", "US.CEG", "US.BWXT", "JP.8035", "US.VST", "US.NRG"]
        exist_map = {}
        try:
            ret, wdf = ctx.get_market_snapshot(watch)
            if ret == ft.RET_OK:
                got = {str(r.get("code")) for _, r in wdf.iterrows() if r.get("last_price") not in (None, "")}
                exist_map = {w: (w in got) for w in watch}
        except Exception:
            exist_map = {}
        cov = step8_coverage(uni, gate, industry, cands_doc, kr, exist_map)
        manifest["outputs"]["coverage_alert"] = write_json(f"coverage_alert_{date}.json", cov)
        print("step8 漏筛四检查 ✓")

    finally:
        ctx.close()

    # 覆盖率(只美日)·分母=主板股(OTC/粉单与港新欧同类单列·不计入缺失率)
    def cov_rate(mk):
        uc = uni["counts"].get(mk) or {}
        tot = uc.get("excl_delisted") or 0
        primary = uc.get("primary_listed")
        otc = uc.get("otc_nonexec")
        pm = [c for c, r in gate["per_stock"].items() if c.startswith(mk + ".") and r["reason_code"] != "OTC_NONEXEC"]
        nod = sum(1 for c in pm if gate["per_stock"][c]["reason_code"] == "NODATA_TURNOVER")
        readok = len(pm)   # 主板·过市值·已snapshot尝试
        got = readok - nod
        return {"总股票数": tot, "主板上市数": primary, "OTC粉单(不可执行·不计缺失率)": otc,
                "主板中过市值门槛": readok, "其中成交额成功读取": got, "成交额缺失(NODATA)": nod,
                "缺失率_成交额_基于主板过市值池_pct": (round(nod / readok * 100, 2) if readok else None)}
    manifest["覆盖率_美日各自"] = {"US": cov_rate("US"), "JP": cov_rate("JP"),
                            "口径说明": "全集=get_stock_basicinfo；分母取『主板上市(NYSE/NASDAQ/AMEX/TSE)』；"
                                    "OTC粉单(US_PINK) OpenD不供行情→与港新欧同类单列·不计入缺失率(『本轮不可执行』≠『做了但缺』)；"
                                    "市值门槛由 server-filter；成交额来自 snapshot。缺失率>20% 不得称『已完成全量筛选』。"
                                    "韩国:定向查2只·未做全市场扫描。"}
    manifest["脚本指纹"] = {"first_scan.py": sha256_file(ROOT / "scripts" / "first_scan.py"),
                        "forecast_lock.py": sha256_file(ROOT / "scripts" / "forecast_lock.py")}
    manifest["finished_local"] = now_jst()
    info = write_json(f"_run_{date}.json", manifest)
    print("\n_run 证据 ✓", info["file"], info["bytes"], "字节")
    print("覆盖率 US:", manifest["覆盖率_美日各自"]["US"])
    print("覆盖率 JP:", manifest["覆盖率_美日各自"]["JP"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
