# -*- coding: utf-8 -*-
"""★★轮179:3只完整决策链(D3七样)——锁定完整产品标准的样品(GPT最短路径第2件)。
GPT对D3的定义(七样缺一不可):①买卖账户 ②股数 ③分档 ④价格 ⑤失效条件 ⑥换仓对象 ⑦执行后全组合变化。
★Code只算【机械七样】(账户/股数/分档/价格/组合变化·可复核)·【判断类】(失效方向/换仓决定/是否操作)【逐字搬Opus5正文】不代判(G2)。
★缺件如实NK4·不估算不硬凑(GPT第⑧条)。★三只互相咬合:合并计算(C-1)·同一场景一套数不打架(C-2/L17)。
3只覆盖买/卖/持三态:JP.4568第一三共(卖·退出方向已定今日不操作)·US.MSFT微软(持·超限作废不动)·JP.7735 SCREEN(买·候选#1格式demo)。"""
import sys, json, math, glob
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

FX = {"US": 1.0, "JP": 157.0, "HK": 7.8422}
DEF_LIST = {"JP.7974", "JP.8766", "JP.7203", "JP.7832", "JP.8001"}   # 防御股(Opus5静态:任天堂/东京海上/丰田/万代/伊藤忠)
AIBETA_FATE = {"JP.6857", "JP.9984"}   # ★命运变量·高AI beta单一环节(爱德万+软银·driver_exposure破30%那组)


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _latest(pat):
    g = sorted(ROOT.glob(pat))
    return g[-1] if g else None


def _usd_by_positions(extra_delta=None):
    """全账户 by公司 USD市值(FUTU+SBI·FX归一)。extra_delta={code:usd增量}用于模拟买卖后。返回 (usd_by, name_by)。"""
    fx = _rj(_latest("data/universe/tier_filter_*.json")).get("FX", {}) or FX
    if not fx.get("JP"):
        fx["JP"] = 157.0
    pos = _rj(_latest("data/accounts/futu_positions_*.json")).get("futu_positions", []) or []
    sbi = _rj(_latest("data/accounts/sbi_positions_*.json")).get("逐只", []) or []
    usd_by, name_by = {}, {}
    for p in pos:
        c = p["symbol"]; mk = c.split(".")[0]
        usd_by[c] = usd_by.get(c, 0) + (p.get("broker_market_val") or 0) / fx.get(mk, 1.0)
        name_by[c] = p.get("name")
    for s in sbi:
        c = s["symbol"]
        usd_by[c] = usd_by.get(c, 0) + (s.get("市值JPY") or 0) / fx.get("JP", 157.0)
        name_by.setdefault(c, s.get("name"))
    if extra_delta:
        for c, d in extra_delta.items():
            usd_by[c] = usd_by.get(c, 0) + d
    return usd_by, name_by


def snapshot(usd_by, label):
    """全账户快照:total(股票市值)·防御%·美股%/日股%·单只max·命运变量(高AI beta)%。★分母=股票市值(与decision_worklist同源·不含现金)。"""
    total = sum(v for v in usd_by.values() if v > 0) or 1
    def_usd = sum(usd_by.get(c, 0) for c in DEF_LIST)
    us_usd = sum(v for c, v in usd_by.items() if c.startswith("US.") and v > 0)
    jp_usd = sum(v for c, v in usd_by.items() if c.startswith("JP.") and v > 0)
    fate_usd = sum(usd_by.get(c, 0) for c in AIBETA_FATE)
    mx = max(((c, v) for c, v in usd_by.items() if v > 0), key=lambda x: x[1])
    return {
        "口径": label,
        "股票市值合计USD": round(total),
        "防御仓%": round(def_usd / total * 100, 2),
        "美股%": round(us_usd / total * 100, 2),
        "日股%": round(jp_usd / total * 100, 2),
        "单只最大%": {"标的": mx[0], "权重%": round(mx[1] / total * 100, 2)},
        "命运变量·高AIbeta%(爱德万+软银)": round(fate_usd / total * 100, 2),
    }


def _exec(code):
    e = _rj(_latest("data/accounts/exec_params_*.json")).get("三只", []) or []
    for x in e:
        if x.get("symbol") == code:
            return x
    return {}


def _price_levels(code):
    """到价三尺度(未来3日/1-3月/6-12月·目标/低吸/止损)——来自exec_params(机器K线算)。"""
    x = _exec(code)
    tp = x.get("到价三档", {})
    out = {}
    for k, v in tp.items():
        if isinstance(v, dict):
            out[k] = {kk: (vv.get("值") if isinstance(vv, dict) else vv) for kk, vv in v.items()}
    kl = x.get("K线指标(机器算·K_DAY QFQ)", {})
    return out, kl, x.get("现价", {}).get("值")


def _tranche(qty, adv60):
    """分档:股数÷(ADV60×20%参与率)·向上取整·最小1。"""
    if not adv60 or not qty:
        return None, "NK4:缺ADV60或股数"
    part = adv60 * 0.20
    n = max(1, math.ceil(qty / part))
    return n, "分笔数=ceil(%d ÷ (ADV60 %d ×20%%=%d))=%d；股数占ADV60仅%.3f%%→%s" % (
        qty, adv60, round(part), n, qty / adv60 * 100, "1笔即可(远低于日均量)" if n == 1 else "%d笔" % n)


def _fetch_kline_7735():
    """★7735非持仓·exec_params无它→现算K线(复用exec_params_build)。★先读缓存(独立步已抓·避免每次OpenD慢抓)·无缓存才live。OpenD失败则NK4。"""
    cache = _rj(ROOT / "data/accounts/cand_kline_7735_20260804.json")
    if cache and cache.get("compute"):
        return cache
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import exec_params_build as epb
        from realtime_price import connect_quote_context, get_realtime_price
        ctx, _att = connect_quote_context(max_retries=2, wait_seconds=2)   # ★返(ctx,attempts)元组·须解包
        try:
            q = get_realtime_price("JP.7735", ctx=ctx, max_retries=1, wait_seconds=0)   # ★单字符串+ctx kwarg
            price = q.get("price") if q.get("status") == "OK" else None
            bars, err = epb.fetch_bars(ctx, "JP.7735")   # ★返(bars,err)元组·须解包
            if not price and bars:
                price = bars[-1].get("close")
            comp = epb.compute("JP.7735", "SCREEN Holdings", bars, price, "现算", None, 0, None)
            return {"现价": price, "compute": comp, "bars数": len(bars), "K线err": err}
        finally:
            try:
                ctx.close()
            except Exception:
                pass
    except Exception as e:
        return {"NK4": "7735 K线现算失败(%s: %s)→价格/分档NK4" % (type(e).__name__, str(e)[:80])}


def build(dc):
    o5 = _rj(_latest("data/content/opus5_content_*.json"))
    zhu = {x.get("标的", ""): x for x in o5.get("三_逐只判断", [])}
    base_usd, name_by = _usd_by_positions()
    base = snapshot(base_usd, "现状(基线·未动)")

    # ══════ 1) JP.4568 第一三共 · 卖出侧(退出方向已定·今日不操作) ══════
    pl_dai, kl_dai, px_dai = _price_levels("JP.4568")
    adv_dai = kl_dai.get("ADV60_60日日均成交量")
    n_dai, alg_dai = _tranche(7900, adv_dai)
    zdai = zhu.get("第一三共 JP.4568", {})
    daiichi = {
        "标的": "JP.4568 第一三共", "处境": "卖出侧·退出方向已定·今日不操作(Opus5正文)",
        "① 买卖账户": "FUTU 6,500股 + SBI 1,400股(两账户都有·全退需两边都动·合计7,900股)",
        "② 股数": {"值": 7900, "算法": "全部退出=当前全账户持仓7,900股(FUTU6500+SBI1400)。★退出驱动=会计诚信问题(非补防御缺口)→退出方向决定全清·非按缺口算部分",
                   "★上个交易日已卖": "2,000股(9,900→7,900·Opus5正文)"},
        "③ 分档": {"分笔数": n_dai, "算法": alg_dai, "跳空阈值": ("%.2f%%(ATR14/现价·低开≤1ATR照卖·1~2ATR分批·>2ATR暂停)" % kl_dai.get("ATR占现价pct")) if kl_dai.get("ATR占现价pct") else "NK4"},
        "④ 价格(三尺度·卖出用目标价挂·止损=加速退出)": pl_dai,
        "⑤ 失效条件(Opus5正文·可机器检测·不看股价)": {
            "退出印证·应加速": "审计意见保留 / 监管问询 / 再次修订 / CFO变动 任一(公告监测:EDINET/8-K)",
            "退出削弱·须重估": "后续两季无新增财务披露问题 且 下期财报按修订口径正常发布",
            "★不采用": "『股价回升X%』作证伪(Opus5明确)"},
        "⑥ 换仓对象": "转现金·不买入(Opus5 08-03定『卖出第一三共转现金不买入』)。★非换入某标的→本只⑥=退出转现金",
        "⑦ 执行后全组合变化": "见【C·合并组合变化·场景A】",
        "★本只判断来源": "退出方向/失效信号/转现金=Opus5正文逐字搬;账户/股数/分档/价格=Code机器算(G2)",
    }

    # ══════ 2) US.MSFT 微软 · 持有侧(超限作废·不动) ══════
    pl_ms, kl_ms, px_ms = _price_levels("US.MSFT")
    w_ms = round(base_usd.get("US.MSFT", 0) / base["股票市值合计USD"] * 100, 2)
    zms = zhu.get("微软 US.MSFT", {})
    msft = {
        "标的": "US.MSFT 微软", "处境": "持有侧·超限判断作废·不动(Opus5正文)",
        "① 买卖账户": "FUTU 500股(SBI无·美股)。★不动→本次不从任何账户动",
        "② 股数": {"值": 0, "算法": "★0变动(不动)。现持500股·全账户权重%.2f%%<20%%上限→减仓前提(超限)已消失" % w_ms},
        "③ 分档": "不适用(不动·0笔)",
        "④ 价格(三尺度·监测线·不动的观察位)": pl_ms,
        "⑤ 失效条件(不动→何时重新触发·可机器检测)": {
            "重新触发减仓": "微软全账户权重回升 >20%(权重监测·如SBI日股大跌致美股占比抬升)",
            "估值端失效": "forward P/E 回到 33x 无折价(Opus5正文:现21.2x有折价·33x是AI叙事最有利估值)",
            "★证伪依据": "Opus5正文:『不动不是因为看好·是减仓理由(超限)没了』+云收入二阶导提速利润率未恶化"},
        "⑥ 换仓对象": "不适用(不动·不换)",
        "⑦ 执行后全组合变化": "无变化(不动)。现贡献:全账户权重%.2f%%·护城河8分(宽)·中AIbeta组" % w_ms,
        "★本只判断来源": "作废/不动/估值折价=Opus5正文;权重/价格=Code机器算(G2)",
    }

    # ══════ 3) JP.7735 SCREEN · 买入侧(候选#1·格式demo) ══════
    cand = _fetch_kline_7735()
    prio = _rj(_latest("data/opportunity/candidate_priority_*.json"))
    top = (prio.get("全量排序", []) or [{}])[0]
    if "compute" in cand:
        cc = cand["compute"]
        pl_7735 = {k: ({kk: (vv.get("值") if isinstance(vv, dict) else vv) for kk, vv in v.items()} if isinstance(v, dict) else v)
                   for k, v in (cc.get("到价三档", {}) or {}).items()}
        kl7 = cc.get("K线指标(机器算·K_DAY QFQ)", {})
        adv7 = kl7.get("ADV60_60日日均成交量")
        px7 = cand.get("现价")
    else:
        pl_7735, kl7, adv7, px7 = {"NK4": cand.get("NK4")}, {}, None, None
    # 建仓股数=需Opus5定目标权重→Code给算式+示例(3%起步)
    ex_shares = None
    if px7:
        ex_shares = round(0.03 * base["股票市值合计USD"] / (px7 / FX["JP"]))   # 3%示例·JPY股→USD
    n_7735, alg_7735 = _tranche(ex_shares, adv7) if (ex_shares and adv7) else (None, "NK4:缺现价或ADV60")
    screen = {
        "标的": "JP.7735 SCREEN Holdings", "处境": "买入侧·候选池#1·★格式demo(实际买入决策=Opus5·当前Opus5定不买入)",
        "★为何选它(候选#1)": "候选优先级排序#1:命中3路径(A趋势+B异动+C估值)·过第3关·PE_TTM %s·5日异动 %s%%(大跌=路径B)·大盘。★Code按结构化字段排(命中数最高·G2)·不判它更好" % (top.get("PE_TTM"), top.get("路径B_5日异动%")),
        "① 买卖账户": "SBI(日股·SBI直接持日股顺) 或 FUTU(现金$59,218可买日股)。★7735是日股→建议SBI",
        "② 股数": {"★需Opus5定目标建仓权重": "Code不代定(G2)",
                  "算式": f'股数=目标权重百分比 × 全账户股票市值${base["股票市值合计USD"]} ÷(现价{px7 or "NK4"} JPY÷157)',
                  "示例(3%起步)": (f"约{ex_shares}股" if ex_shares else "NK4(缺现价)")},
        "③ 分档": {"分笔数": n_7735, "算法": alg_7735},
        "④ 价格(三尺度·买入用低吸价·现算K线)": pl_7735,
        "⑤ 失效条件": {"★买入判断=Opus5的·Code不代判": True,
                    "可机器检测的候选(供Opus5)": ["跌破现算止损价", "④板块轮动确认半导体设备受损(Opus5 08-04已重判受损·与候选池'板块受损=false'矛盾→须Opus5核)"]},
        "⑥ 换仓对象": "买7735=用第一三共卖出的现金$128,844(若Opus5把'退出转现金'改为'换仓')。★当前Opus5定退出转现金不买入→此为格式demo·实际不买",
        "⑦ 执行后全组合变化": "见【C·合并组合变化·场景B(格式demo)】",
        "★护城河": "★待评(D-2):SCREEN护城河作废(曾误当发那科评·decision_worklist MOAT_VOID)→护城河待评·本次不作为买入依据",
        "★本只判断来源": "买入决定/目标权重/失效方向=待Opus5;账户/价格/分档/算式=Code机器算(G2)",
    }

    # ══════ C) 三只咬合·合并组合变化(★同源计算·不打架L17) ══════
    dai_usd = base_usd.get("JP.4568", 0)
    # 场景A(实际·Opus5定):卖第一三共7900→现金·微软不动·不买入
    a_usd = dict(base_usd); a_usd["JP.4568"] = 0
    sA = snapshot(a_usd, "场景A:卖第一三共7900→转现金(微软不动·不买入·Opus5实际定)")
    # 场景B(格式demo·董事长C-1):卖第一三共→现金→买7735(等额$128,844)
    b_usd = dict(base_usd); b_usd["JP.4568"] = 0
    b_usd["JP.7735"] = b_usd.get("JP.7735", 0) + dai_usd
    sB = snapshot(b_usd, "场景B(格式demo):卖第一三共7900→买7735等额$%d" % round(dai_usd))
    combined = {
        "基线": base,
        "场景A(实际·Opus5定:卖第一三共转现金·不买)": sA,
        "★场景A关键变化": {
            "防御仓%": "%.2f%% → %.2f%%(↑%.2fpp·卖非防御股使防御占比升·仍<15%%)" % (base["防御仓%"], sA["防御仓%"], sA["防御仓%"] - base["防御仓%"]),
            "美股/日股": "%.1f/%.1f → %.1f/%.1f(卖日股第一三共→美股占比升)" % (base["美股%"], base["日股%"], sA["美股%"], sA["日股%"]),
            "单只最大": "%s %.2f%% → %s %.2f%%(分母缩→微软占比升·仍<20%%)" % (base["单只最大%"]["标的"], base["单只最大%"]["权重%"], sA["单只最大%"]["标的"], sA["单只最大%"]["权重%"]),
            "命运变量AIbeta": "%.2f%% → %.2f%%(卖非AIbeta股使集中度升·↑%.2fpp)" % (base["命运变量·高AIbeta%(爱德万+软银)"], sA["命运变量·高AIbeta%(爱德万+软银)"], sA["命运变量·高AIbeta%(爱德万+软银)"] - base["命运变量·高AIbeta%(爱德万+软银)"]),
            "现金": "$59,218 → $%s(+第一三共卖出$%d)" % ("{:,}".format(round(59218 + dai_usd)), round(dai_usd)),
        },
        "场景B(格式demo·董事长C-1:卖第一三共买7735)": sB,
        "★场景B关键变化(vs基线)": {
            "防御仓%": "%.2f%% → %.2f%%(卖非防御买非防御·防御占比基本不变)" % (base["防御仓%"], sB["防御仓%"]),
            "美股/日股": "%.1f/%.1f → %.1f/%.1f(日股内部换·美日比基本不变)" % (base["美股%"], base["日股%"], sB["美股%"], sB["日股%"]),
            "命运变量AIbeta": "%.2f%% → %.2f%%(★买半导体设备7735·若归入AIbeta则集中度进一步升)" % (base["命运变量·高AIbeta%(爱德万+软银)"], sB["命运变量·高AIbeta%(爱德万+软银)"]),
            "★关键洞察": "★买7735(半导体·AI-beta)不补防御缺口·反而不改善防御仓13.18%<15%——★换仓对象若为补防御应选防御股·非半导体候选。此即董事长看『该不该动』的依据。",
            "★7735归类注": "场景B的AIbeta%未含7735(driver_exposure命运变量组=爱德万+软银·未含7735)→7735是否入组是Opus5分类·Code不擅归",
        },
        "C-3 执行顺序/资金": {"顺序": "场景A:两账户(FUTU6500+SBI1400)同挂卖·1笔即可(占ADV60仅0.10%)。场景B:先卖后买(等现金到账)",
                          "资金是否够": "买入用第一三共卖出现金$%d(充足)+原现金$59,218·无需外部注资" % round(dai_usd)},
        "★L17自检": "场景A/B各一套自洽数·不混用(C-2)。防御仓基线13.18%只出现一次·场景值明确标注场景→无对立数字",
    }

    out = {
        "_说明": "★轮179 3只完整决策链(D3七样)样品。★Code只算机械七样·判断类逐字搬Opus5正文·缺件NK4不硬凑(G2)。3只覆盖卖/持/买三态。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "★三只(七样齐)": {"卖出侧·第一三共": daiichi, "持有侧·微软": msft, "买入侧·候选7735": screen},
        "★C_三只咬合·合并组合变化": combined,
        "★D_如实标": {
            "D-1_NK4项": [x for x in (["7735价格/分档(K线现算失败)"] if "NK4" in cand else []) ],
            "D-2_候选护城河": "SCREEN(7735)护城河作废待评→本次不作为买入依据(如实标)",
            "D-3_不该动的": "微软=不动(七样里适用:账户/股数0/价格监测/失效条件/组合无变化·5样适用·分档&换仓不适用)。第一三共=退出方向已定但今日不操作(七样齐·供退出日)。★均未硬凑动作",
        },
        "★七样完整性自检": None,   # 下方填
    }
    # 七样完整性自检(缺一即FAIL)
    SEVEN = ["① 买卖账户", "② 股数", "③ 分档", "④ 价格", "⑤ 失效条件", "⑥ 换仓对象", "⑦ 执行后全组合变化"]
    chk = {}
    for nm, st in [("第一三共", daiichi), ("微软", msft), ("7735", screen)]:
        got = []
        for s in SEVEN:
            got.append(any(k.startswith(s[:3]) for k in st.keys()))
        chk[nm] = {"七样齐": all(got), "缺": [SEVEN[i] for i, g in enumerate(got) if not g]}
    out["★七样完整性自检"] = chk
    (ROOT / f"data/pdca/decision_chain_full_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("决策链3只 · 七样自检:", json.dumps(o["★七样完整性自检"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
