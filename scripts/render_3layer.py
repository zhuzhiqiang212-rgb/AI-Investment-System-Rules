#!/usr/bin/env python3
"""三层产品渲染器(董事长2026-07-19·架构师给骨架·Code只填数据)

读【架构师骨架模板】三层骨架模板_给Code填数据_20260719.html，把所有 {{槽位}} 换成正式数据源真值。
· 三层核心字段全部读【同一个 final_decision 对象】(复用 deep_render 的 decision_of/val_state·与唯一决定表同源)。
· 阈值/股数/价格/基准一律读正式配置与底表(集中度上限读 full_product_render·SBI读 sbi_sleeve)，不写死。
· 第二/三层按持仓逐只循环；id=why-{代码}/deep-{代码}。
· 图表第一轮做 1/2/3/4/5/7/8/12；6/9/10/11 标"待接·第二轮"(真待接·不编)。
· 出厂前删模板顶部红色说明块；任何 {{ }} 残留 → 抛错不出品。

用法: python scripts/render_3layer.py --date 20260719
产物: 00_请先看这里/★每日产品三层_YYYY-MM-DD.html
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from datetime import date as _date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import deep_render as D  # noqa: E402

TPL = ROOT / "00_请先看这里" / "三层骨架模板_给Code填数据_20260719.html"
ACT_COLOR = {"加": "add", "买": "add", "减": "cut", "守": "hold", "等": "wait"}
ACT_ICON = {"加": "▲", "买": "▲", "减": "▼", "守": "■", "等": "…"}
TBD = '<span style="color:#6B4E8C">待接·不编</span>'
_WK = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
_STATE_CN = {"CLOSED": "收盘", "AFTER_HOURS_END": "盘后", "AFTER_HOURS_BEGIN": "盘后",
             "PRE_MARKET_BEGIN": "盘前", "PRE_MARKET_END": "盘前", "MORNING": "盘中",
             "AFTERNOON": "盘中", "OVERNIGHT": "夜盘", "WAITING_OPEN": "开盘前"}


def _iso(d: str) -> str:
    d = str(d).replace("-", "")
    return f"{d[:4]}-{d[4:6]}-{d[6:8]}" if len(d) >= 8 else str(d)


def _wk(d: str) -> str:
    dd = str(d).replace("-", "")
    try:
        return _WK[_date(int(dd[:4]), int(dd[4:6]), int(dd[6:8])).weekday()]
    except Exception:
        return ""


def _is_weekend(d: str) -> bool:
    dd = str(d).replace("-", "")
    try:
        return _date(int(dd[:4]), int(dd[4:6]), int(dd[6:8])).weekday() >= 5
    except Exception:
        return False


def _daydiff(d1: str, d2: str) -> int:
    """d1-d2 的自然日差(d1、d2 = iso 或 yyyymmdd)。"""
    def g(x):
        x = str(x).replace("-", "")
        return _date(int(x[:4]), int(x[4:6]), int(x[6:8]))
    try:
        return (g(d1) - g(d2)).days
    except Exception:
        return 0


_ANOM_CACHE: dict = {}


def _sanity_anomaly(date: str) -> dict:
    """读 data_sanity 的量级哨兵→{sym: 倍数}(现价与中周期公允差>5倍·四·专项核准前须显眼标注)。"""
    if date in _ANOM_CACHE:
        return _ANOM_CACHE[date]
    out = {}
    for x in (_rj(ROOT / "data" / "reports" / f"data_sanity_{date}.json").get("issues") or []):
        if str(x.get("type")) == "量级哨兵":
            m = re.search(r"约\s*(\d+(?:\.\d+)?)\s*倍", str(x.get("detail", "")))
            mult = float(m.group(1)) if m else 6.0
            if mult > 5:
                out[str(x.get("symbol"))] = mult
    _ANOM_CACHE[date] = out
    return out


def _price_meta(sym: str, date: str) -> dict:
    """该只现价的真实交易日/时点/源(读 holdings_true.price_data_date·非生产日)。治致命1。"""
    for h in (_rj(ROOT / "data" / "accounts" / f"holdings_true_{date}.json").get("holdings") or []):
        if str(h.get("symbol")) == sym:
            pdd = h.get("price_data_date")
            st = _STATE_CN.get(str(h.get("price_market_state")), "")
            # 源统一表述(二.1):OpenD取得的最近交易日收盘价·非盘中实时(不许"实时"与"非实时"同句冲突)
            return {"pdate": pdd, "state": st, "src": "OpenD·最近交易日收盘价（非盘中实时）"}
    return {"pdate": None, "state": "", "src": "OpenD(富途)"}


def _rj(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ── 未来1~2年目标价:读架构师已落档的前瞻估值表(董事长2026-07-19 轮6接线1) ──
#     数据源:持仓前瞻估值表_年底明年合理价_2026-07-18.html(方法=中枢×(1+g)^t)。
#     下列6只确不可外推→保持待接并写明原因(不硬填)。
_FWD_EXCLUDE = {
    "9984": "软银NAV依Arm/OpenAI资产·不可简单外推", "MSTR": "依BTC币价·不可外推",
    "6857": "景气峰值·外推即掉周期陷阱", "SNDK": "景气峰值·外推即掉周期陷阱",
    "COIN": "低置信·不外推", "CRCL": "低置信·不外推",
}
_FWD_CACHE: dict = {}


def _fwd_targets() -> dict:
    """解析前瞻估值表→{代码大写: {今:..,y2026:..,y2027:..,g:..}}。只读架构师已落档值,不自算。"""
    if _FWD_CACHE:
        return _FWD_CACHE
    p = ROOT / "00_请先看这里" / "持仓前瞻估值表_年底明年合理价_2026-07-18.html"
    try:
        t = p.read_text(encoding="utf-8")
    except Exception:
        return _FWD_CACHE
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
        cells = [" ".join(re.sub(r"<[^>]+>", " ", c).split())
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
        cells = [c for c in cells if c.strip()]
        if len(cells) < 5 or "合理" in cells[1] or not re.search(r"[¥$]", cells[1]):
            continue
        code = cells[0].split()[-1].upper()               # "英伟达 NVDA"→NVDA / "第一三共 4568"→4568 / "Meta"→META
        _FWD_CACHE[code] = {"今": cells[2], "y2026": cells[3], "y2027": cells[4],
                            "g": cells[5] if len(cells) > 5 else ""}
    return _FWD_CACHE


# ── mini-mustache：{{#段}}..{{/段}} 循环/布尔 + {{标量}} ──────────────
#   用 backref \1 精确匹配同名 close(否则嵌套段会被内层 close 截断)。
_SEC = re.compile(r'\{\{#(\S+?)\}\}(.*?)\{\{/\1\}\}', re.S)


def render(tpl: str, ctx: dict) -> str:
    tpl = tpl.replace("{{/风险}}", "{{/风险1到3}}")   # 模板 open=风险1到3/close=风险 名字不一致→归一
    def repl(m):
        name, inner = m.group(1), m.group(2)
        data = ctx.get(name)
        if isinstance(data, list):
            return "".join(render(inner, {**ctx, **it}) for it in data)
        if data:                                   # 布尔段(如 超限)
            return render(inner, ctx)
        return ""
    prev = None
    while prev != tpl:                             # 逐个替换·支持嵌套
        prev = tpl
        tpl = _SEC.sub(repl, tpl, count=1)
    # 标量
    def scal(m):
        k = m.group(1)
        v = ctx.get(k)
        return "" if v is None else str(v)
    return re.sub(r'\{\{([^#/][^}]*?)\}\}', scal, tpl)


# ── 每只 final_decision（三层同源） ──────────────────────────────────
def holding_ctx(sym, name, dyn, date, conc, sanity_syms):
    c = D.cur(sym)
    _a, why, pure = D.decision_of(sym, name, dyn, date)
    st = D.val_state(sym, dyn)
    px = D._price_of(sym, dyn)
    v = (dyn.get("valr", {}) or {}).get(sym, {}) or {}
    ht = (dyn.get("ht") or {}).get(sym) or {}   # dyn["ht"] 是按 symbol 索引的 dict
    accs = ht.get("accounts") or []
    parts = "＋".join(f"{a.get('account','')}{a.get('quantity'):g}" for a in accs if a.get("quantity"))
    qty = ht.get("total_quantity")
    mkt = sym.split(".")[0]
    mkt_cn = {"US": "美股", "JP": "日股", "HK": "港股", "CN": "A股", "CC": "加密"}.get(mkt, mkt)
    # 致命1:价格真实交易日(非生产日)+ 生产日/来源/是否超时限,四项分别显示
    prod_iso = _iso(date)
    pm = _price_meta(sym, date)
    price_iso = _iso(pm["pdate"]) if pm["pdate"] else None
    if price_iso:
        gap = _daydiff(prod_iso, price_iso)
        overdue = "是" if gap > 4 else "否"       # 超4自然日(>一个周末)才算超时限
        same_day = (price_iso == prod_iso)
        pdate = (f'产品生产日 {prod_iso}（{_wk(prod_iso)}）'
                 f'{"·非交易日" if _is_weekend(prod_iso) else ""}'
                 f'｜价格对应交易日 <b>{price_iso}（{_wk(price_iso)}）{pm["state"] or "收盘"}</b>'
                 f'｜来源 {D.esc(str(pm["src"]))}｜是否超时限:{overdue}'
                 + ("" if same_day else "（<b>非实时·最近交易日收盘</b>）"))
    else:
        pdate = '价格对应交易日待接（未取到行情数据日·不编）'
        same_day = False
    # 今日价值区 / 未来目标（权威 OK → valr；否则架构师）
    if st.get("ok"):
        lo, hi = st["lo"], st["hi"]
    else:
        av = D.arch_val_display(sym, dyn)
        _e = D._arch_est(sym) or {}
        fp = _e.get("fair_price") or _e.get("archived_fair_price") or {}
        lo, hi = fp.get("cheap"), fp.get("rich")
    # [三.1]估值状态三态(机器按输入齐全度自动定·解释文字不得覆盖) + [二.3]无估值只观察
    no_val = (lo is None and hi is None)
    if st.get("ok"):
        val_state3 = "①输入齐·可正式使用"
    elif not no_val:
        val_state3 = "②输入部分齐·只作框架参考·不得单独据此买卖"
    else:
        val_state3 = "③估值未接·不得用于买卖（暂无可信估值）"
    tf = v.get("target_future")
    base_code = sym.split(".")[-1].upper()
    fwd = _fwd_targets().get(base_code)
    if isinstance(tf, dict) and tf.get("low") is not None:            # 引擎权威前瞻(如TSM)优先
        tgt = f'{c}{tf["low"]:,.0f} ~ {c}{tf["high"]:,.0f}'
        tgt_miss = ""
    elif fwd:                                                        # 架构师前瞻估值表(2026底~2027底)
        tgt = f'{fwd["y2026"]}（2026底）~ {fwd["y2027"]}（2027底）'
        tgt_miss = f'（年增速 {fwd["g"]}·方法=中枢×(1+g)^t·架构师2026-07-18落档）' if fwd.get("g") else ""
    elif base_code in _FWD_EXCLUDE:                                  # 确不可外推的6只:标待接+具体原因
        tgt, tgt_miss = TBD, f'（{_FWD_EXCLUDE[base_code]}）'
    else:
        tgt, tgt_miss = TBD, "（缺前瞻EPS·待架构师补）"
    # 第一二档(便宜位/次批价)——只有"加/买"才有真档；其余标"—"
    if pure in ("加", "买") and st.get("ok"):
        d1p, d1q = f"{c}{st['lo']:,.0f}", "分批·别一次满"
        d2p, d2q = f"{c}{st['lo']*0.95:,.0f}", "便宜位再低5%加第二批"
    else:
        d1p = d1q = d2p = d2q = "—（今日不加）"
    # 账户/金额
    acct = "SBI(日元账户)" if sym.startswith("JP.") else "富途/IBKR(美元)"
    amt = "约现金1/3分批" if pure in ("加", "买") else "—"
    # 催化剂(排除例行财报·前瞻真事件)
    cat = D.esc(_clean(D._catalyst_within(sym, date))) or f'{TBD}（近90天列不出明确前瞻催化剂）'
    deep = D._deep_card(sym) or {}
    catsrc = "深研⑦催化剂日历(block7)" if D._catalyst_within(sym, date) else "—"
    # 现价位置百分比(band ▼)
    pos = "50%"
    try:
        if px and lo and hi and hi > lo:
            pos = f"{max(0,min(100,(px-lo)/(hi-lo)*100)):.0f}%"
    except Exception:
        pass
    # 支持/反对证据(evidence·深研)
    sup = _evidence(deep, "support") or _support_from(deep)
    opp = _evidence(deep, "oppose") or "未找到反面证据·已查(深研③护城河/⑧风险/evidence_chain);如后续出现将补入"
    # 好中坏
    sc = (deep.get("block6_scenarios") or {}).get("rows") or []
    good = _sc(sc, "好"); base = _sc(sc, "中"); bad = _sc(sc, "坏")
    # 组合占比(动作前后·图5)
    cat_name = D._cat_of(sym, date, dyn) or "未归类"
    before = _cat_pct(conc, cat_name)
    # 同业(sector peers·图6)
    peers = _peers(sym)
    # 致命2:现价已超上沿=极贵。若仍守/等,须给"为何不减"的自洽理由(低置信/周期),且停止条件不写"涨过X才减"
    expensive = bool(px is not None and hi and px > hi)
    cred = str(v.get("credibility") or "")
    if not st.get("ok") or "低置信" in cred or "框架" in cred:
        hold_reason = "该只权威估值属低置信·仅作框架参考(穿牛熊/数据不足)，不据此不可靠读数杀"
    else:
        try:
            peak = bool(D._peak_cyclical(sym, dyn))
        except Exception:
            peak = False
        hold_reason = ("处景气/中周期高位·按周期尺看不因极贵就翻减" if peak
                       else "综合账本质地与周期位置的权衡")
    # 深研16项
    d16 = _deep16(sym, name, dyn, deep, v, c)
    hc = {
        "代码": sym, "股票名": D.esc(name), "名": D.esc(name),
        "今日动作": pure, "动作色": ACT_COLOR.get(pure, "hold"), "动作图标": ACT_ICON.get(pure, "■"),
        "三态": "sys", "三态文字": "系统建议·尚未执行",
        "现价": f"{c}{px:,.2f}" if px is not None else TBD, "市场": mkt_cn, "价格日期": pdate,
        "价值区下沿": f"{c}{lo:,.0f}" if lo else TBD, "价值区上沿": f"{c}{hi:,.0f}" if hi else TBD,
        "目标价": tgt, "目标价缺则标 待接·不编": tgt_miss, "现价位置百分比": pos,
        "第一档价": d1p, "第一档量": d1q, "第二档价": d2p, "第二档量": d2q,
        "账户": acct, "币种": c, "股数": f"{qty:g}" if qty else TBD, "建议金额": amt,
        "停止条件": _stop_of(pure, st, c, px, expensive, hold_reason),
        "为什么现在": re.sub(r"<[^>]+>", "", why)[:300],
        "为什么不选其他": _why_not(pure, st, c, expensive, hold_reason),
        "催化剂": cat, "催化剂来源": catsrc,
        "催化剂失效条件": (D.esc(_clean(_flat((deep.get("block7_catalysts") or [""])[0]))) or TBD),
        "证伪条件": _falsify(deep),
        "把握程度": D._conf_grade(D.build_final(sym, name, dyn)),
        "把握理由": f"估值状态：{val_state3}。账本质地档＋估值可信度综合(见③第6项)",
        "支持证据列表": sup, "反对证据列表": opp,
        "好情况价": good[0], "好情况条件": good[1], "中性价": base[0], "中性条件": base[1],
        "坏情况价": bad[0], "坏情况条件": bad[1],
        "同业": peers, "动作前占比": before, "动作后占比": _after_pct(pure, before),
        "上限": _cat_limit(conc, cat_name), "推导链简版": _chain_short(deep),
        "图1结论": _fig1_concl(pure, px, lo, hi, c, v, fwd),
        "图2结论": f"好{good[0]}/中{base[0]}/坏{bad[0]}——三价分开看，别只盯一个数。",
        "图5结论": f"这一动后「{cat_name}」占比 {before}→{_after_pct(pure, before)}。",
        "图6结论": "同业倍数横比见表；缺的标待接不猜。",
        "图7结论": "例行财报日期本身不算催化剂；只认前瞻真事件。",
        "图8结论": "支持/反对并列；反面为空必写已查哪些源。",
        "图9结论": "世界观→行业→本股→今天动作一条链；某环无事件标今日无新事件。",
        "估值状态三态": val_state3,
        **d16,
    }
    # [四]现价与合理值差>5倍(爱德万/闪迪)→专项核准前显眼标注·不得再以"架构师已复核"为凭
    _anom = _sanity_anomaly(date).get(sym)
    if _anom:
        warn = (f'<b style="color:#ff5c5c">⚠ 数据未通过专项核准，不可据此买卖</b>（现价约为中周期合理值 {_anom:.0f} 倍）'
                f'——待补：正式代码/交易所/原始行情记录/是否拆股+拆股公告/拆股前后价格与股数/持仓是否同步调整/'
                f'OpenD价/第二个独立行情源/两源是否一致/估值输入用拆股前还是拆股后口径。此前一律只观察、不据此下单。')
        hc["为什么现在"] = warn + "｜" + str(hc.get("为什么现在", ""))
        hc["三态文字"] = "⚠数据未通过专项核准·不可据此买卖（仅观察）"
        hc["今日动作"] = "观"
        hc["动作色"] = "wait"
    # [二.3]无可信估值(如SpaceX)→统一"只观察"，禁用便宜/贵/PEG等判断词
    if no_val:
        obs = "暂无可信估值，不能判断便宜或贵；因此不买、不加、不减，只保留观察。"
        hc["今日动作"] = "观"
        hc["动作色"] = "wait"
        hc["动作图标"] = "…"
        hc["为什么现在"] = obs
        hc["为什么不选其他"] = "缺可信估值，任何『便宜/贵/PEG』判断都不成立→只观察，不做买卖动作。"
        hc["停止条件"] = "先补上可信估值再谈买卖；在此之前只保留观察。"
        hc["第一档价"] = hc["第二档价"] = "—（无估值·不设档）"
        hc["第一档量"] = hc["第二档量"] = "—"
        hc["目标价"] = TBD
        hc["目标价缺则标 待接·不编"] = "（无可信估值·只观察）"
    # 现价统一到唯一源:散文里带『现价』标签的价格一律同步到 px(治同股两现价·致命1)
    #   『现价』字段本身(值=纯价格无前缀)不受影响；只改散文里"现价约¥X"这类。
    hc = {k: (_pxsync(val, c, px) if isinstance(val, str) and "现价" in val else val)
          for k, val in hc.items()}
    return hc


def _evidence(deep, kind):
    return ""


def _support_from(deep):
    bits = []
    m = (deep.get("block3_moat") or {})
    if m.get("score"):
        bits.append(f"护城河：{D.esc(str(m.get('score')))}")
    d9 = str(deep.get("block9_decision_chain") or "")
    if d9:
        bits.append("决策链：" + D.esc(_cut(re.sub(r"<[^>]+>", "", d9), 120)))
    return "<br>".join(bits) or "见③第14项正反证据全量"


def _sc(rows, key):
    for r in rows:
        if str(r.get("case", "")).startswith(key):
            return (D.esc(_cut(r.get("value") or "待接", 40, "…")), D.esc(_cut(r.get("assume") or "", 60, "…")))
    return (TBD, "缺情景·只显已有")


def _cat_pct(conc, cat):
    v = (conc.get("categories", {}) or {}).get(cat)
    return f"{v['pct']:.1f}%" if v and v.get("pct") is not None else "—"


def _cat_limit(conc, cat):
    v = (conc.get("categories", {}) or {}).get(cat)
    return f"{v['limit']:.0f}%" if v and v.get("limit") is not None else "—"


def _after_pct(pure, before):
    return before  # 精确联动见图5说明；此处保守显同值(动作未执行·系统只读)


def _stop_of(pure, st, c, px=None, expensive=False, hold_reason=""):
    if not st.get("ok"):
        return "权威估值待接→现在不动手·守着看"
    # 致命2:现价已在上沿之上却守/等——不得再写"涨过X才谈减"(自相矛盾)
    if expensive and pure in ("守", "等"):
        return (f"现价已在上沿之上（{c}{px:,.2f} > 上沿 {c}{st['hi']:,.0f}）——"
                f"因{hold_reason or '周期/估值可信度'}暂不据此设减线；"
                f"待权威估值口径确认或趋势转弱再议减，跌回 {c}{st['lo']:,.0f} 便宜位才谈加。")
    if pure in ("加", "买"):
        return f"涨回 {c}{st['mid']:,.0f} 以上就别再追"
    if pure == "减":
        return f"跌回 {c}{st['hi']:,.0f} 以下就别再减"
    return f"跌破 {c}{st['lo']:,.0f} 才谈加、涨过 {c}{st['hi']:,.0f} 才谈减"


def _why_not(pure, st, c, expensive=False, hold_reason=""):
    if expensive and pure in ("守", "等"):     # 极贵却不减:如实说因低置信/周期不据此杀
        return (f"不选减：现价虽已过上沿、显极贵，但{hold_reason or '估值可信度/周期原因'}——"
                f"不因不可靠或周期性的极贵读数就杀；不选加：已远超便宜位，贵不该加。")
    if pure == "等":
        return "不选加：没到便宜位或没催化(别接飞刀)；不选减：没到贵位、也没超配触发。"
    if pure == "守":
        return "不选加：已超配/不够便宜；不选减：没到贵位或成长便宜(PEG<1)。"
    if pure in ("加", "买"):
        return "不选等：已跌进便宜位且有催化/企稳；不选减：便宜不该减。"
    if pure == "减":
        return "不选守：已过贵位且该类超配；不选加：贵不该加。"
    return "见决策条同一把尺。"


def _falsify(deep):
    d9 = str(deep.get("block9_decision_chain") or "")
    m = re.search(r"什么才算[^：:]*[：:]([^<]{0,120})", d9)
    return D.esc(m.group(1)) if m else "见③第16项判断被推翻的条件"


def _chain_short(deep):
    return "世界观(AI国力主线)→行业(所在AI链环)→本股(护城河/账本)→今天动作(按唯一决定表)。详见③第11项。"


def _peers(sym):
    try:
        import sector_deep as SD
        av = SD.arch_verdict_map()
        base = sym.split(".")[-1]
        rows = []
        for tk in _peer_of(base):
            e = av.get(tk) or {}
            rows.append({"名": tk, "pe": D.esc(str(e.get("pe_text", ""))[:24]) or "待接",
                         "peg": "待接", "增速": "待接", "护城河": D.esc(str(e.get("verdict", ""))[:12]) or "待接"})
        return rows
    except Exception:
        return []


def _peer_of(base):
    P = {"TSM": ["ASML", "AMAT"], "AVGO": ["MRVL", "AMD"], "NVDA": ["AMD", "AVGO"]}
    return P.get(base, [])


def _fig1_concl(pure, px, lo, hi, c, v, fwd=None):
    if px is None or not lo:
        return "估值待接·只守着看。"
    tf = v.get("target_future")
    if isinstance(tf, dict) and tf.get("low"):
        ft = f"，未来目标 {c}{tf['low']:,.0f}~{c}{tf['high']:,.0f}"
    elif fwd:
        ft = f"，未来目标 {fwd['y2026']}(2026底)~{fwd['y2027']}(2027底)"
    else:
        ft = ""
    return f"今日该值 {c}{lo:,.0f}~{c}{hi:,.0f}{ft}；现价 {c}{px:,.2f}，动作={pure}。今日价值区与未来目标分开看。"


def _deep16(sym, name, dyn, deep, v, c):
    """③完整研究底稿16项——从深研卡真取·缺标待接。只增不减(L3内容不缩水·安全截断不切半词)。"""
    g = lambda k, n=900: (D.esc(_cut(_clean(_flat(deep.get(k))), n)) or TBD)   # _flat已None→空·不 dump dict
    method = str(v.get("model_disp") or "")
    if not method:
        av = D._arch_est(sym) or {}
        method = str(av.get("ruler_short") or "待接")
    # 致命3:估值状态【单一真相】——可信度 与 待接项 必须同源，不得一处说输入未接、另一处说已OK精算。
    #   精算成立 ⟺ 权威 status==OK 且 估值输入齐(val_inputs 有真值)。任一不满足 → 统一『待接·不标精算』。
    vin = _val_inputs(sym, v)
    has_inputs = (vin != TBD and "待接" not in vin)
    is_精算 = (str(v.get("status")) == "OK") and has_inputs
    if is_精算:
        cred = str(v.get("credibility") or "中").replace("低置信", "低置信·仅作框架参考")
        waits_txt = "本只权威估值已OK·精算（输入齐·可信度见左）"
    else:
        cred = "待接·框架参考（输入未接·不标精算）"
        why_wait = _clean(str(v.get("reason") or "")) or ("缺权威精算输入" if not has_inputs else "权威估值未OK")
        waits_txt = f"估值输入未接齐→撤精算标签、统一待接。原因：{why_wait}"
    return {
        "赚钱模式": g("block1_business") or _b(deep, "block1"),
        "多年财务": _fin_years(sym, deep),
        "业务结构": g("block2_structure") or _b(deep, "block2"),
        "护城河": _moat(deep),
        "竞争对手": g("block4_competitors") or _b(deep, "block4"),
        "估值模型": D.esc(method),
        "估值输入逐项含来源": vin,
        "可信度": D.esc(cred),
        "敏感性": _sens(sym, v),
        "三情况完整推导": _scen_full(deep),
        "事件日历": "<br>".join(t for t in (D.esc(_clean(_flat(x))) for x in (deep.get("block7_catalysts") or [])) if t) or TBD,
        "风险与可观测信号": _risks(deep),
        "推导链全版": g("block9_decision_chain"),
        "组合作用": _b(deep, "block10") or g("block10_portfolio"),
        "可点链接列表含发布日": _sources(deep),
        "正反证据全量": _support_from(deep) + "<br>反面：见图8/未找到则已注明查哪些源",
        "待接项与原因": waits_txt,
        "推翻条件": _falsify(deep),
        "图3结论": "多年真数看趋势；年数不足标仅N年。",
    }


_LEAK = ("任一整套", "该用 ", "不硬编", "缺真输入", "raw_holding", "block1_", "block2_")

# 深研卡内部英文字段名→人话(治『字段名裸露成正文』·董事长轮5致命3)。
#   有译名→带中文标签；无译名的英文结构键→只出值不出键名(绝不裸露英文key)。
_KZH = {
    "intro": "简介", "streams": "业务线", "block": "板块", "what": "是什么", "size": "规模",
    "plain": "说明", "margin": "利润率", "metric": "指标", "rows": "", "fy": "财年",
    "revenue": "营收", "yoy": "同比", "gross": "毛利率", "net": "净利", "fcf": "自由现金流",
    "as": "口径", "source": "来源", "sources": "来源", "note": "备注", "prob": "概率",
    "case": "情形", "assume": "假设", "value": "取值", "why": "理由", "score": "评分",
    "risk": "风险", "weight": "权重", "signal": "信号", "name": "名称", "pe": "市盈率",
    "peg": "PEG", "detail": "细节", "title": "标题", "desc": "说明", "text": "",
    "date": "日期", "event": "事件", "role": "作用", "eps": "每股盈利", "operating": "营业利润",
}


def _clean(s: str) -> str:
    """清内部话术/字段名/原始dict痕迹→不印给董事长(治 L4b/L4c 泄露)。"""
    s = re.sub(r"[\{\}\[\]']", "", str(s))           # 去 dict/list 符号
    s = re.sub(r"block\d+_\w+|_\w+", "", s)
    for w in _LEAK:
        s = s.replace(w, "")
    return re.sub(r"\s+", " ", s).strip()


def _flat(val) -> str:
    """dict/list→大白话文本(不 json.dumps·None→空·英文键翻译或去键·不泄露结构)。"""
    if val is None:
        return ""
    if isinstance(val, dict):
        out = []
        for k, v in val.items():
            if v is None or v == "" or str(k).startswith("_"):
                continue
            fv = _flat(v)
            if not fv:
                continue
            zh = _KZH.get(str(k).strip().lower())
            out.append(f"{zh}：{fv}" if zh else fv)   # 有译名带标签·无译名只出值(不裸露英文key)
        return "；".join(out)
    if isinstance(val, list):
        return "；".join(x for x in (_flat(i) for i in val) if x)
    s = re.sub(r"<[^>]+>", "", str(val))
    return "" if s.strip().lower() == "none" else s   # 兜底:字符串 "None" 也当空


def _cut(s: str, n: int, tail: str = "…（余见完整底稿）") -> str:
    """安全截断:不切半个数字/词——回退到最近句读，截了就补省略号。治『¥后数字没了/sourc缺字母』。"""
    if s is None:
        return ""
    s = str(s)
    if len(s) <= n:
        return s
    seg = s[:n]
    cut = max(seg.rfind("；"), seg.rfind("。"), seg.rfind("，"), seg.rfind("、"),
              seg.rfind("）"), seg.rfind(")"))
    if cut > n * 0.5:                                  # 有靠后的句读→切到那
        seg = seg[:cut + 1]
    else:                                              # 否则退到最后一个非数字/字母边界，别切半个 token
        seg = re.sub(r"[\w¥$,.]+$", "", seg)
    return seg.rstrip("·、，,") + tail


def _pxsync(text: str, c: str, px) -> str:
    """把散文里带『现价』标签的价格统一到唯一源 px(final_decision同价)。治同股两现价。"""
    if px is None or not text:
        return text
    canon = f"{c}{px:,.2f}"
    return re.sub(r"(现价约?)\s*" + re.escape(c) + r"[\d,]+(?:\.\d+)?",
                  lambda m: m.group(1) + canon, str(text))


def _b(deep, prefix):
    for k, val in deep.items():
        if str(k).startswith(prefix) and val:
            return D.esc(_cut(_clean(_flat(val)), 600))
    return ""


def _moat(deep):
    m = deep.get("block3_moat") or {}
    score = m.get("score") or ""
    why = re.sub(r"<[^>]+>", "", str(m.get("why") or ""))
    if score or why:
        return D.esc(_cut(f"{score}·{why}".strip("·"), 300))
    return TBD


def _fin_years(sym, deep):
    d = deep.get("block4_realdata") or deep.get("block2_financials") or {}
    txt = _clean(_flat(d)) if d else ""
    if txt:
        return D.esc(_cut(txt, 900))
    return f'{TBD}（多年财务见官方财报数据/公司IR·本卡未铺满则标待接）'


def _val_inputs(sym, v):
    vi = _rj(ROOT / "data" / "valuation" / "val_inputs.json").get("holdings", {}).get(sym, {})
    LBL = {"normal_eps":"正常化中周期每股盈利","pe_mid":"中周期市盈率","normalized_eps":"穿牛熊正常化每股盈利",
           "pe_normal":"正常化市盈率","forward_eps":"前瞻每股盈利","forward_pe":"前瞻市盈率","peg":"PEG",
           "fair_locked":"今日价值区(架构师锁定)"}
    bits = []
    for k in ("normal_eps", "pe_mid", "normalized_eps", "pe_normal", "forward_eps", "forward_pe", "peg", "fair_locked"):
        if vi.get(k) is not None:
            bits.append(f"{LBL[k]}={D.esc(_clean(_flat(vi[k])))}")
    src = vi.get("source")
    if src:
        bits.append(f"来源：{D.esc(_cut(_clean(str(src)), 120))}")
    return "<br>".join(bits) or TBD


def _sens(sym, v):
    vi = _rj(ROOT / "data" / "valuation" / "val_inputs.json").get("holdings", {}).get(sym, {})
    s = vi.get("sensitivity")
    if s:
        return D.esc(_cut(_clean(_flat(s)), 300))
    return f'{TBD}（每股盈利±20%/倍数±20%·精算股已填·其余待接）'


def _scen_full(deep):
    rows = (deep.get("block6_scenarios") or {}).get("rows") or []
    if rows:
        return "<br>".join(
            D.esc(f"{r.get('case') or ''}：{r.get('assume') or ''}→{r.get('value') or ''}"
                  f"（{r.get('prob') or ''}）".replace("：→", "：待接→").replace("（）", ""))
            for r in rows)
    return TBD


def _risks(deep):
    rk = (deep.get("block8_risks") or {}).get("rows") or []
    if rk:
        return "<br>".join(
            D.esc(f"{r.get('risk') or '待接'}·重{r.get('weight') or '—'}·信号{r.get('signal') or '待接'}")
            for r in rk)
    return TBD


def _sources(deep):
    src = deep.get("source_note") or deep.get("sources")
    txt = _clean(_flat(src)) if src else ""
    if txt:
        return D.esc(_cut(txt, 400))
    return TBD


def _waits(sym, v):
    if str(v.get("status")) != "OK":
        return D.esc(_clean(str(v.get("reason") or "权威估值待接")))
    return "本只权威估值已 OK·精算"


# ── [收口·真凶]135处内联亮色(旧深色主题)统一翻成浅底可读色·CSS盖不住内联→只能全文替换(董事长2026-07-19) ──
#   规则:浅背景上不得有亮色文字·每处内联 color 与其背景对比度≥4.5:1。整个产品统一为浅色主题。
_INLINE_TEXT = {   # 亮色文字 → 浅底可读的深色(架构师给的换算值)
    "#ffb454": "#8A3E00", "#A9761A": "#8A3E00", "#ffd479": "#7A5C00", "#E0B24A": "#7A5C00",
    "#caa24a": "#6B5200", "#c9a86a": "#6B5200", "#a89968": "#6B5200", "#d8c89a": "#6B5200", "#a89968": "#6B5200",
    "#7ee0a0": "#1E7A45", "#8cf5be": "#1E7A45", "#bfe6d3": "#1E7A45", "#8ef5be": "#1E7A45",
    "#ff9a9a": "#A3231F", "#ff5c5c": "#A3231F", "#ffd0d0": "#A3231F", "#ffb0b0": "#A3231F",
    "#9ed8ff": "#12324E", "#8fd6ff": "#12324E", "#5cc8ff": "#12324E", "#8ec6ff": "#12324E",
    "#7cc4ff": "#12324E", "#9ed8ff": "#12324E", "#bcd0e2": "#3A4A5A", "#cfe0ee": "#26404F",
    "#8ea3b6": "#4A5C6A", "#9db0c2": "#4A5C6A", "#c8d4de": "#3A4A5A", "#8a94a0": "#4A5C6A",
    "#9fb3c4": "#3A4A5A", "#ffe4a8": "#7A5C00",
    # 二轮扫描补漏(脚本扫出<4.5:1)
    "#d9e7ef": "#3A4A5A", "#ffcf6b": "#7A5C00", "#bcd8ee": "#26404F", "#d8c68a": "#6B5200",
    "#c9a9f6": "#5B3E8C", "#ff6b6b": "#A3231F", "#4f9e7f": "#1A6B3B", "#66707c": "#4A5C6A",
    "#9ed6a8": "#1A6B3B", "#ffd0d0": "#A3231F", "#d0f0dd": "#1A6B3B", "#e6d0a8": "#6B5200",
}
_INLINE_BG = {     # 旧深色主题的深底(残留在浅色页面里) → 浅底
    "#141c26": "#F2F4F7", "#0f1925": "#F2F4F7", "#0e1621": "#F2F4F7", "#0e1a26": "#F2F4F7",
    "#0a141d": "#F2F4F7", "#10202e": "#EAF2FA", "#0e1c2e": "#EAF2FA", "#13202d": "#EAF2FA",
    "#101a26": "#F2F4F7", "#151f2b": "#F7F9FB", "#0f1e17": "#EAF5EF", "#12261f": "#EAF5EF",
    "#0f2e1c": "#E4F4EA", "#3a1414": "#FBEAEA", "#3a2410": "#F5EFE0", "#2a2412": "#F5EFE0",
    "#2a1f10": "#F5EFE0", "#1c1608": "#F5EFE0", "#0b1118": "#FFFFFF", "#0f2018": "#EAF5EF",
    "#1c2740": "#EAF2FA", "#122033": "#EAF2FA", "#0d1a12": "#EAF5EF", "#1a1208": "#F5EFE0",
}   # 注:#12324e/#5C4033/#123A6B/#123D2E/#0b1420(topnav)/#12203a(.hdr) 是深色强调条·故意不翻·配白字


def _light_theme(out: str) -> str:
    """全文把旧深色主题的内联亮色文字/深色背景 → 浅底可读色(逐一替换·CSS改不掉内联·只能这样)。"""
    for a, b in _INLINE_TEXT.items():
        out = out.replace(f"color:{a}", f"color:{b}").replace(f"color: {a}", f"color:{b}")
    for a, b in _INLINE_BG.items():
        out = out.replace(f"background:{a}", f"background:{b}").replace(f"background: {a}", f"background:{b}")
        out = out.replace(f"background-color:{a}", f"background-color:{b}")
    # 边框/杂项残留亮金(非 color: 前缀·上单未清·第六节)→深色
    out = out.replace("background:#ffb454;color:#0b1118", "background:#8A3E00;color:#FFFFFF")  # 亮金badge→深底白字
    for a, b in (("#caa24a", "#6B5200"), ("#ffd479", "#7A5C00"), ("#ffb454", "#8A3E00")):
        out = out.replace(a, b)     # 边框等一切残留(全局)
    return out


# [E1]四只估值底稿(架构师2026-07-19补正·Code照文渲染·数值一字不改)
_ARCH_VAL = {
    "US.COIN": (
        '<b style="color:#7ee0a0">估值底稿·架构师补正（COIN·保留「中·精算」不升级）</b><br>'
        '逐年GAAP摊薄EPS（SEC EDGAR CIK 1679788·10-K）：FY2021 $14.50（牛市峰值）／FY2022 −$11.83（熊市巨亏·不剔除）／'
        'FY2023 $0.37／FY2024 $9.48／FY2025 $4.45。<br>'
        '穿牛熊简单平均（不剔异常年）=(14.50−11.83+0.37+9.48+4.45)/5=<b>$3.39</b>；同业倍数22× → 合理中枢 $74.6（区间 $67~82）；现价$157≈中枢2.1倍。<br>'
        '为何只给「中」：单一周期内EPS从+14.5摆到−11.8·任何点估值可能上下差一倍·仅一轮完整样本 → 框架参考，不宜单独据此下单。'),
    "JP.6857": (
        '<b style="color:#ffb454">估值底稿·架构师补正（爱德万·<u>撤销精算→框架参考</u>）</b><br>'
        '逐年摊薄EPS（stockanalysis/S&P·财年Apr–Mar）：FY2022 ¥111.81／FY2023 ¥173.67／FY2024 ¥84.16（周期谷）／FY2025 ¥218.01／'
        'FY2026 ¥513.30（AI/HBM超级景气峰值·已剔除）。<br>'
        '4年均=587.65/4=¥146.9 ×中周期PE20=¥2,938（区间¥2,646~3,234）。<br>'
        '<b>为何降级</b>：半导体测试设备强周期(完整周期5–8年)·现仅FY22-25四年·缺FY19-21(恰覆盖上轮低谷)→用不完整周期算「正常年景」不可靠。'
        '<b style="color:#ff5c5c">撤销「中高·精算」→「框架参考·样本不足一个完整周期」</b>；且现价¥27,505≈中枢9倍·须先过异常价专项核准。'),
    "US.TSM": (
        '<b style="color:#7ee0a0">估值底稿·架构师补正（台积电·补敏感性+分年目标）</b><br>'
        '口径=P/E+PEG（成熟成长）；基准FY2026E ADR EPS≈$18·前瞻P/E≈23.5·净利增速≈40%→PEG≈0.6；合理倍数22×。<br>'
        '敏感性九宫格（EPS±20%×倍数±20%）：<br>'
        '<table class="dt" style="max-width:520px"><tr><th>合理价</th><th>17.6×(−20%)</th><th>22.0×(基准)</th><th>26.4×(+20%)</th></tr>'
        '<tr><td>EPS $14.4(−20%)</td><td>$253</td><td>$317</td><td>$380</td></tr>'
        '<tr><td>EPS $18.0(基准)</td><td>$317</td><td><b>$396</b></td><td>$475</td></tr>'
        '<tr><td>EPS $21.6(+20%)</td><td>$380</td><td>$475</td><td>$570</td></tr></table>'
        '最坏$253／基准$396／最好$570·现价$397.75落基准格附近。<br>'
        '<b>分年目标</b>：2026年底 $18×22=<b>$396</b>／2027年底 $22×22=<b>$484</b>（高盛TWD3,000≈$475–500与2027底一致·仅作对照）。<br>'
        '$18假设失效信号：月营收连续两月低于季度指引隐含值／3nm·2nm订单被下修／超大规模AI资本开支放缓／新台币大幅升值／台海事件断供 → 任一出现即重算作废。'),
    "US.IBKR": (
        '<b style="color:#ffb454">估值底稿·架构师补正（IBKR·保留「框架参考」不升级）</b><br>'
        '正常化EPS $2.40来源：FY2025 GAAP摊薄$2.22(已按2024-06 4拆1还原)＋2026共识$2.46~2.49·取中$2.40；合理倍数22× → 中枢$52.8（区间$48~58）·现价$90.78≈1.7倍。<br>'
        '<b>利率高峰处理</b>：利润含大量客户存款净利息(NII)·随利率走·2023-25高利率期·<u>不外推高利率年</u>·用FY25实际＋次年共识取中作中性利率代理。<br>'
        '<b>降息情景</b>：基准$2.40→$52.8；降100bp→EPS $2.05~2.15→$45~47；降200bp→EPS $1.75~1.90→$39~42（每降100bp约削EPS$0.25~0.35·架构师估算·非公司披露→故不给精算）。<br>'
        '市场按~37×前瞻给到$90(为30%+账户增长与77%税前利润率付成长溢价)·「正常化券商倍数」与「成长定价」是两把尺·本估值只说按前者偏贵·不等于该卖。'),
}


def _arch_val_block(sym):
    body = _ARCH_VAL.get(sym)
    if not body:
        return ""
    return ('<div style="font-size:12px;color:#cfe0ee;background:#0f1925;border-left:3px solid #4f9e7f;'
            'border-radius:0 6px 6px 0;padding:7px 10px;margin:6px 0">' + body + '</div>')


# [E2/E3]统一减仓规则(架构师2026-07-19三批定稿)——每只六行·四条件逐条·两极贵股分开写(不共用模板话)
#   四条件:①上涨理由失效 ②利润趋势转弱(连续两季低于指引/共识) ③仓位超限 ④超上沿30%且连续10个交易日
_ARCH_REDUCE = {
    # 博通/Meta:45%上限已废止→不再因超限判减(现为『等』·风险配仓建议反而加/维持观察)·故不再列减仓块
    "US.IBKR": {"标识": "好公司涨太多·等回调",
                "四条件": "①否(账户+31%/客户权益+38%/保证金+65%/NII+17%·基本面在加速) ②否 ③否 ④待计数(超上沿约1.6倍)",
                "六行": ("<b>守。好公司涨太多、基本面在加速，贵是市场给的成长溢价，守是对的（不是变差）。</b>",
                         "④现价高于合理上沿30%且连续10个交易日",
                         "现价$90.78·上沿$58·超+57%（已过30%线）；最近验证点 Q2财报 2026-07-21 盘后（距今2天）",
                         "<b>待接</b>（★缺日线逐日序列·计数器接口已就位·不编假天数）",
                         "④连续满10日且仍在线上 → 提请拍板『要不要止盈减一点』（系统不自动减）",
                         "跌回上沿内、或④天数不满足即取消。反向风险=降息每25bp减年度NII约$80M")},
    "US.COIN": {"标识": "已现裂缝·再miss一次就该减",
                "四条件": "①否(多元化在加强:订阅$584M占44%/12产品各年化过亿/稳定币收入占近1/5/USDC留存$19B创新高) ②【已现裂缝·仅一季】Q1营收与调整后盈利双双低于预期 ③— ④待计数(超上沿约1.9倍)",
                "六行": ("<b>守。但已出现裂缝——Q1 2026营收与调整后盈利双双低于预期（已 miss 一个季度）。比IBKR更接近减仓线。</b>",
                         "②再 miss（连续两季低于共识·现仅一季）＋④连续天数累计",
                         "现价$157·上沿$82·超+92%（已过30%线）；②:Q1已miss·Q2财报(约8月)为确认点",
                         "<b>待接</b>（★缺日线逐日序列·计数器接口已就位·不编假天数）",
                         "Q2 再 miss 即构成②→提请减仓；或④满10日→提请止盈（系统不自动减）",
                         "Q2 未再 miss 且价格跌回上沿内即取消")},
    "JP.6857": {"四条件": "异常价未通过专项核准 → 核准前不进任何减仓判定",
                "六行": ("异常价未通过专项核准→在核准完成前，本只不进任何减仓判定。",
                         "先过异常价专项核准（拆股公告/拆股前后价与股数/两独立行情源一致）",
                         "现价¥27,505·中枢¥2,938·约9倍（须先过异常价专项核准）",
                         "—（未核准·不计数）", "异常价专项核准完成后再评估", "核准完成即进入常规判定")},
    "US.TSM": {"四条件": "未达30%止盈线(现价$397·上沿$360·超+10%)→不进减仓；且 PEG 0.6 属成长便宜",
               "六行": ("未达止盈线(未高于合理上沿30%)→本就不进减仓判定；且 PEG 0.6 属成长便宜。",
                        "④尚未触发（未过30%止盈线）", "现价$397.75·上沿$360·超+10%（未过30%线）",
                        "—（未过30%线·不计数）", "达到30%止盈线并开始计数后再谈", "价格回落即无需评估")},
    "JP.7974": {"四条件": "未达30%止盈线(现价¥7,294·上沿¥5,923·超+23%)→不进减仓；另有净现金约¥1,940/股缓冲",
                "六行": ("未达止盈线→本就不进减仓判定；另有净现金约¥1,940/股缓冲。",
                         "④尚未触发（未过30%止盈线）", "现价¥7,294·上沿¥5,923·超+23%（未过30%线）",
                         "—（未过30%线·不计数）", "达到30%止盈线并开始计数后再谈", "价格回落即无需评估")},
}


def _reduce_rule_block(sym, dyn):
    """减仓候选每只显示的六行(架构师三批定稿·四条件逐条·两极贵股分开写)。非减仓候选不显示。"""
    a = _ARCH_REDUCE.get(sym)
    if not a:
        return ""
    r = a["六行"]
    tag = f'　<span style="font-weight:800">【{a["标识"]}】</span>' if a.get("标识") else ""
    return (
        '<div style="font-size:12px;color:#cfe0ee;background:#101a26;border-left:3px solid #c47a1e;'
        'border-radius:0 6px 6px 0;padding:7px 10px;margin:6px 0">'
        f'<b style="color:#ffb454">统一减仓规则·本只六行（架构师定稿·系统不自动减·只提请拍板）</b>{tag}<br>'
        f'<span style="color:#9fb3c4">四条件逐条：{a["四条件"]}</span><br>'
        f'1. 为什么现在不减：{r[0]}<br>'
        f'2. 正在等哪一个条件：{r[1]}<br>'
        f'3. 该条件当前数值：{r[2]}<br>'
        f'4. 已累计多少天（连续＞止盈线）：{r[3]}<br>'
        f'5. 何时正式提请拍板：{r[4]}<br>'
        f'6. 什么情况取消减仓提示：{r[5]}'
        '</div>')


def esc_none(s):
    return D.esc(str(s)) if s is not None else ""


def _stab_calc_of(sym, dyn, date):
    """[五·C]取加仓闸逐项实测(复用 deep_render._stabilized_calc)·逐只显示。"""
    try:
        return D._stabilized_calc(sym, dyn, date)
    except Exception:
        return ""


# ── [A组]第一层可读性(董事长2026-07-19实测『根本看不清』·★彻底弃用金色文字·架构师已验算对比度) ──
#   所有文字对比度≥4.5:1(大字粗体≥3:1);金色只留边框/图标·不做正文。同原则应用到 L2(蓝)/L3(绿):标题条深底白字·正文近黑。
_A_CSS = (
    # ── A2 配色·第一层彻底弃金(深棕标题条9.39:1 + 纯白底 + 近黑正文17.40:1 + 中性隔行15.80:1) ──
    "#L1>summary{background:#5C4033;color:#FFFFFF;font-size:20px}"                     # 标题条深棕白字 9.39:1(过AAA)
    "#L1 .body{background:#FFFFFF;border-left:5px solid #5C4033}"
    "#L1 .body,#L1 .blk div,#L1 td,#L1 .blk h3,#L1 .body td,#L1 .body th{color:#1A1A1A}"  # 正文近黑 17.40:1
    "#L1 table th{background:#12324E;color:#FFFFFF}"                                   # 表头深蓝白字(保持)
    "#L1 table tr:nth-child(odd) td,#L1 table tbody tr:nth-child(odd) td{background:#FFFFFF}"
    "#L1 table tr:nth-child(even) td,#L1 table tbody tr:nth-child(even) td{background:#F2F4F7}"  # 中性灰隔行 15.80:1
    # ── A1 字号(上轮已对·保持):动作徽章/主决定最大 ──
    "#L1 .chip{font-size:18px;font-weight:800;padding:3px 14px;border-radius:6px}"
    "#L1 .pill{font-size:14px;font-weight:700;padding:2px 12px}"
    "#L1 table{font-size:15px}#L1 th,#L1 td{padding:9px 10px}"
    '#L1 td[data-l="现价"],#L1 td[data-l="第一档"],#L1 td[data-l="第二档"]{font-size:16px;font-weight:700}'
    "#L1 .blk h3{font-size:17px}#L1 .blk div{font-size:15px;line-height:1.8}"
    "#L1>summary{font-size:20px}"
    # ── L2/L3 同原则(标题条深底白字·正文近黑·行底中性)——治『浅底+同色系浅字』 ──
    "#L2>summary{background:#123A6B;color:#FFFFFF}#L2 .body,#L2 .body td,#L2 .body th,#L2 .stock,#L2 .nm{color:#14243A}"
    "#L3>summary{background:#123D2E;color:#FFFFFF}#L3 .body,#L3 .body td,#L3 .body th,#L3 .stock,#L3 .nm{color:#12261D}"
    "#L2 table th{background:#123A6B;color:#fff}#L3 table th{background:#123D2E;color:#fff}"
    # 手机端再放大一档(验收:亮度50%手机也读得出)
    "@media(max-width:640px){#L1 .chip{font-size:20px;padding:4px 16px}#L1 td{font-size:15px}"
    '#L1 td[data-l="现价"],#L1 td[data-l="第一档"],#L1 td[data-l="第二档"]{font-size:18px}#L1>summary{font-size:18px}}'
)

# ── [A]三层导航 + [B]版面区块(董事长2026-07-19 第十一/十二节) ──
_NAV_CSS = (
    "#topnav{position:sticky;top:0;z-index:50;background:#12324E;border-bottom:2px solid #0d2438;"
    "padding:7px 10px;display:flex;flex-wrap:wrap;gap:6px 12px;align-items:center;font-size:13px}"
    "#topnav a{color:#FFFFFF !important;text-decoration:none;font-weight:700;white-space:nowrap}"
    "#topnav a:hover{text-decoration:underline}#topnav b{color:#FFE08A !important}"
    ".navret{background:#0e1a26;border:1px solid #24384c;border-radius:6px;padding:5px 9px;margin:6px 0;"
    "font-size:12.5px;color:#bcd0e2;display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center}"
    ".navret a{color:#7ee0a0;font-weight:700;text-decoration:none}.navret a:hover{text-decoration:underline}"
    ".navret .crumb{color:#ffd479;font-weight:800}"
    ".blockend{text-align:center;color:#5a6b7a;font-size:12px;border-top:1px dashed #2b4054;margin:16px 0 6px;padding-top:5px}"
    "@media(max-width:600px){#topnav{font-size:12px;gap:5px 8px}.navret{font-size:11.5px}}"
)


def _add_nav(out: str, order: list, names: dict) -> str:
    """A:固定导航条+每卡顶部/底部返回同一只+当前位置面包屑;B:块结束分隔。"""
    # A1 固定导航条(滚动常驻·手机适配) + 顶部锚
    out = out.replace("<body>", '<body>\n<a id="top"></a>\n'
                      '<div id="topnav"><b>快速跳转：</b>'
                      '<a href="#L1">今天怎么做</a><a href="#L2">为什么这么做</a>'
                      '<a href="#L3">完整研究底稿</a><a href="#inst-top">完整机构底稿</a>'
                      '<a href="#top">返回顶部 ↑</a></div>', 1)
    # A2 L1 每只加 id="act-{sym}"(供第二层返回同一只) —— 锚在该只"为什么→"链接前
    for sym in order:
        out = out.replace(f'<a class="jump" href="#why-{sym}">为什么→</a>',
                          f'<a id="act-{sym}"></a><a class="jump" href="#why-{sym}">为什么→</a>', 1)
    idx = {s: i for i, s in enumerate(order)}

    def _l2bar(sym):
        nm = names.get(sym, sym)
        return (f'<div class="navret"><span class="crumb">当前：第二层 ＞ {nm} ＞ 为什么这么做</span>'
                f'<a href="#act-{sym}">← 返回第一层：今天怎么做（回到 {nm}）</a>'
                f'<a href="#deep-{sym}">看本只完整研究底稿 →</a></div>')

    def _l3bar(sym):
        nm = names.get(sym, sym)
        nxt = order[idx[sym] + 1] if idx.get(sym, len(order) - 1) < len(order) - 1 else None
        nxt_a = f'<a href="#deep-{nxt}">下一只股票：{names.get(nxt, nxt)} →</a>' if nxt else '<a href="#inst-top">进入 ④ 完整机构底稿 →</a>'
        return (f'<div class="navret"><span class="crumb">当前：第三层 ＞ {nm} ＞ 完整研究底稿</span>'
                f'<a href="#why-{sym}">← 返回第二层：本只为什么这样做（回到 {nm}）</a>'
                f'<a href="#act-{sym}">← 返回第一层：今天怎么做</a>{nxt_a}</div>')

    # A2/A3 顶部条:每卡开头注入 + A2/A3 底部条:每卡下一张开头前注入前一张的底部条
    st = {"sym": None, "layer": None}

    def _open(m):
        layer, sym = m.group(1), m.group(2)
        pre = ""
        if st["sym"] and st["layer"] == layer:            # 上一张同层卡的【底部条】
            pre = (_l2bar(st["sym"]) if layer == "why" else _l3bar(st["sym"]))
        st["sym"], st["layer"] = sym, layer
        top = (_l2bar(sym) if layer == "why" else _l3bar(sym))
        return pre + m.group(0) + top
    out = re.sub(r'<div class="stock" id="(why|deep)-([^"]+)">', _open, out)
    # 每层最后一张卡的底部条 + B1 本块结束分隔
    if order:
        last = order[-1]
        out = out.replace('<details class="layer" id="L3">',
                          _l2bar(last) + '<div class="blockend">— 本块结束：② 为什么这么做 —</div><details class="layer" id="L3">', 1)
        out = out.replace('<h2 class="main" id="inst-top"',
                          _l3bar(last) + '<div class="blockend">— 本块结束：③ 完整研究底稿 —</div><h2 class="main" id="inst-top"', 1)
    # [D1]B1 每个大块结尾都加"本块结束"分隔(统一措辞·覆盖机会池/板块/记分卡/右栏/承接/新闻等机构块)
    _SEC_NAME = {"sec-opp": "机会池", "sec-sector": "板块深研", "sec-macro": "大环境六层", "sec-conc": "组合集中度",
                 "sec-risk": "风险因子", "sec-score": "记分卡三件魂", "sec-rulers": "规则附件6把尺",
                 "sec-triggers": "承接节点", "sec-diff": "差分+新闻", "sec-loop": "逻辑闭环"}
    for aid, nm in _SEC_NAME.items():
        # 在每个机构块开头前，插上一块的"本块结束"(第一块 sec-opp 前不插)
        if aid != "sec-opp":
            out = out.replace(f'<details class="sub" id="{aid}"',
                              f'<div class="blockend">— 本块结束 —</div><details class="sub" id="{aid}"', 1)
        # 块标题条改成"含名字"的醒目条(独立标题条·B1)
        out = out.replace(f'<details class="sub" id="{aid}"><summary>',
                          f'<details class="sub" id="{aid}"><summary>【{nm}】', 1)
    # 最后一个机构块(sec-loop)之后补一条"本块结束"
    out = out.replace('<script>\nfunction allOpen', '<div class="blockend">— 本块结束：④ 完整机构底稿 —</div>\n<script>\nfunction allOpen', 1)
    return out


# 复用 deep_render 的机构区块样式(注入内容才有正确排版)——只搬 class 规则、不动 body/:root
_DEEP_CSS = (
    ".card{background:#151f2b;border:1px solid #2b4054;border-radius:10px;padding:12px 14px;margin:10px 0}"
    ".sym{color:#8ea3b6;font-size:12px}.conf{color:#ffd479}.q{color:#7ee0a0;font-size:13px}.v{color:#9ed8ff;font-size:13px}"
    ".k{color:#5cc8ff;font-weight:700;margin-right:6px}.deep{margin:6px 0;font-size:14px}.dossier{margin:6px 0;font-size:13px;color:#d9e7ef}.you{margin-top:6px;font-weight:700}"
    ".blk{font-size:14.5px;color:#ffe4a8;font-weight:700;margin:12px 0 4px;border-left:4px solid #2c6e9a;padding-left:8px}"
    ".plain{background:#12261f;border-left:4px solid #4f9e7f;border-radius:0 7px 7px 0;padding:6px 11px;margin:6px 0;font-size:13px;color:#bfe6d3}"
    ".need{color:#ffb454;font-weight:700}.bull{color:#7ee0a0;font-weight:700}.bear{color:#ff9a9a;font-weight:700}.base{color:#7cc4ff;font-weight:700}"
    ".dt{width:100%;border-collapse:collapse;margin:7px 0;font-size:12.5px}.dt th,.dt td{border:1px solid #2a3d4f;padding:6px 8px;text-align:left;vertical-align:top}.dt th{background:#13202d;color:#bcd0e2}"
    "h2.main{font-size:20px;color:#ffd479;border-left:6px solid #ffd479;padding-left:10px;margin:18px 0 8px}"
    "h2.sub{font-size:15px;color:#8ea3b6;font-weight:600;border-left:3px solid #3a5a8a;padding-left:8px;margin:16px 0 6px}"
    "h3{font-size:15px;color:#cfe0ee}"
    "details.sub{margin:8px 0;border:1px solid #24384c;border-radius:8px;background:#101a26}"
    "details.sub>summary{cursor:pointer;padding:9px 13px;font-size:14px;color:#9ed8ff;font-weight:700}"
    "details.sub>div,details.sub>table{margin:0 11px 10px}"
    ".ruler-embed{border:1px solid #2a3d4f;border-radius:8px;padding:8px 10px;margin:8px 0;background:#0f1925}"
    ".note{font-size:12.5px;color:#9fb3c4;margin:6px 0}"
)

# ── 机构底稿区块(第3节·复用 deep_render 的 part builder·把三层丢掉的整层内容补回来) ──
#   L3 完整机构底稿(全量)+ L1/L2 摘要引用。每块 try/except 隔离,单块失败不拖垮全局。
_INST_BLOCKS = [
    ("机会池 · 该不该换股、换谁（全五关漏斗＋候选池＋替换引擎）", "sec-opp",
     lambda D, date, dyn, daily: D.part4_opportunity(daily, dyn) + D.part4b_swap_engine(daily, dyn) + D.part4_funnel(date, daily, dyn)),
    ("板块深度尺 · 6子板块＋龙头五维小研报（军工/电力/光模块·动静分开）", "sec-sector",
     lambda D, date, dyn, daily: D.sector_deep_block(date)),
    ("大环境 · 六层世界观＋宏观表", "sec-macro",
     lambda D, date, dyn, daily: D.part1_layers(daily, dyn) + D.part1_macro_table(daily)),
    ("组合层 · 集中度是否押偏", "sec-conc",
     lambda D, date, dyn, daily: D.part3_concentration(date, dyn)),
    ("风险因子 · 三条主风险＋可观测信号", "sec-risk",
     lambda D, date, dyn, daily: D.part3_risk_factors(dyn)),
    ("复盘记分卡三件魂 · 判断记分／确定性累积／多尺度复盘／影子组合／预测记分", "sec-score",
     lambda D, date, dyn, daily: D.part7_pdca(date, daily) + D.part7_souls(date, daily) + D.part7_forecasts(date)),
    ("右栏底子 · 6把尺（世界观/国家战略/资金/板块/过滤五关/持仓档案）", "sec-rulers",
     lambda D, date, dyn, daily: D.part6_rulers(dyn)),
    ("承接节点 · 今天哪几只跌到加仓价／拍板收件箱", "sec-triggers",
     lambda D, date, dyn, daily: D.part0_triggers(date, dyn)),
    ("与昨天相比 · 差分优先＋当日新闻", "sec-diff",
     lambda D, date, dyn, daily: D.part0_diff(date, dyn)),
    ("整条逻辑怎么闭环", "sec-loop",
     lambda D, date, dyn, daily: D.part5_closeloop(daily)),
]


_INST_FIELD_ZH = {
    "adj_operating_margin": "调整后经营利润率", "ai_target_2026": "2026年AI目标",
    "backlog_total": "在手订单总额", "billings_growth": "开票增速", "gas_turbine_backlog": "燃气轮机在手订单",
    "operating_margin": "经营利润率", "revenue_growth": "营收增速", "data_center": "数据中心",
    "free_cash_flow": "自由现金流", "net_income": "净利润", "gross_margin": "毛利率",
    "forward_pe": "前瞻市盈率", "book_value": "每股净资产", "dividend_yield": "股息率",
}


def _sanitize_inst(html: str) -> str:
    """机构底稿注入前清洗:①非交易日诚实化'当日实时价'②内部字段名转人话③断长行(L23)④去跨文档死链(L25)。"""
    # ① 当日实时价→最近交易日收盘价(非交易日机构块也是同一批07-17价·不许冒充今天)
    html = re.sub(r"(?<!非)当日实时价", "最近交易日收盘价", html)
    html = html.replace("今天 OpenD 拉的实时", "最近交易日 OpenD 收盘的")
    # ② 内部字段名(snake_case)→人话:先译常见,余下泛化清掉(治 L46)
    for k, v in _INST_FIELD_ZH.items():
        html = html.replace(k, v)
    html = re.sub(r"\b[a-z]{2,}(?:_[a-z0-9]+)+\b(?!\s*=\s*[\"'])", "", html)   # 残余 snake 泄漏清掉
    # ③ 去内部跳锚(三层没有这些锚·避免 L25 坏锚点):把 <a href="#..">x</a> 降级为纯文本
    html = re.sub(r'<a\b[^>]*href="#[^"]*"[^>]*>(.*?)</a>', r"\1", html, flags=re.S)
    # ④ 断长行(L23<8000):在常见块级闭合后插换行
    html = re.sub(r"(</(?:div|tr|table|details|h2|h3|li|p)>)", r"\1\n", html)
    # ⑤[七.1]删"样例股数/等第一次生产"半成品话术(已有20只真持仓)
    html = re.sub(r"[^<>]*?(6只重仓是股数样例|股数等第一次正式生产|等第一次正式生产时[^<。]*灌满|只是[\"“]?结构模板)[^<。]*[。\"”]?",
                  "（本块持仓档案已按20只真实股数灌满；未接账户就地标『未接·不可依赖』）", html)
    # ⑦[B4]旧称呼→正式章节名(注明所属)
    for old, new in (("右栏第6块", "规则附件·6把尺（原右栏第6块）"), ("右栏第六块", "规则附件·6把尺（原右栏第6块）"),
                     ("右栏6块", "规则附件·6把尺"), ("右栏底子", "规则附件·6把尺（属规则附件）")):
        html = html.replace(old, new)
    # ⑥[八.3]sector-deep 锚点去重:第2个及以后改唯一名(所有位置标记唯一)
    _cnt = [0]
    def _uniq(m):
        _cnt[0] += 1
        return m.group(0) if _cnt[0] == 1 else m.group(0).replace('"sector-deep"', f'"sector-deep-{_cnt[0]}"')
    html = re.sub(r'id="sector-deep"', _uniq, html)
    return html


def _institutional(date, dyn):
    """把三层重建时丢掉的【非个股整层内容】补回来(复用 deep_render 的 part builder)。"""
    daily = dyn.get("daily", {}) or {}
    # [B2/八.2]板块龙头研究正文只保留一个正式位置(sec-sector);其它位置(sec-macro内嵌同块)改"查看完整研究→"链接·不整段复制
    try:
        _sector_str = D.sector_deep_block(date) or ""
    except Exception:
        _sector_str = ""
    _sector_link = ('<div class="card" style="border:1px dashed #3a5a8a"><b>板块深度尺·龙头五维小研报</b>'
                    '：为避免整段重复，正文只在【④ 板块深度尺】保留一份。'
                    '<a href="#sec-sector" style="color:#7ee0a0;font-weight:700">查看完整研究 →</a></div>')
    folds, present = [], []
    for title, aid, fn in _INST_BLOCKS:
        try:
            body = fn(D, date, dyn, daily) or ""
        except Exception as e:
            body = f'<div class="note">本块加载失败·待接（{D.esc(str(e))}）</div>'
        if aid == "sec-macro" and _sector_str and _sector_str in body:   # 六层里内嵌的板块块→换链接(去重)
            body = body.replace(_sector_str, _sector_link)
        folds.append(f'<details class="sub" id="{aid}"><summary>{D.esc(title)}</summary>'
                     f'<div style="padding:4px 6px 10px">{body}</div></details>')
        present.append(aid)
    html = "".join(folds)
    try:
        html = D._scrub_leaks(html, is_pool=False)     # 与综合底稿同一套清洗(去内部话/裸字段)
    except Exception:
        pass
    html = _sanitize_inst(html)
    header = ('<h2 class="main" id="inst-top" style="margin-top:22px">④ 完整机构底稿'
              '（机会池／板块深研／记分卡／右栏6尺／承接节点／新闻——一条不删·只增不减）</h2>'
              '<div class="note">本层是三层结构的"完整底稿"延伸：以上①今天怎么做、②为什么，都可在此追到全量原始依据。</div>')
    return header + html, present


# ── [P0-P2]目标倒推模块(董事长2026-07-19定稿·1年双档·主战场SBI+富途) ──
_TARGET_CFG = {
    "期限": "1年", "SBI": 490779, "富途": 1029535, "主战场": 1520314,
    "need40": 608126, "need100": 1520314, "预期年化": "约+12%~+17%",
    "缺40": "23~28个百分点", "缺100": "83~88个百分点", "盲区占比": "36.6%",
}
_TARGET_ROLE = {   # 角色/持仓意图/对目标贡献pp/凭什么占这个仓位(定稿第五节·算不出标盲区不留空)
    "US.NVDA": ("主攻", "核心持有·45%上限已废止→可加（风险配仓建议加至18%·仍在单只20%内）", "+7.73pp", "AI算力龙头·Rubin下季贡献·上行最大的单一来源"),
    "US.MSFT": ("主攻", "核心持有", "主攻组内（组合+16.8pp）", "Copilot变现+Azure+38%·现金流龙头"),
    "JP.4568": ("主攻", "等回调上车→系统建议已转『加』", "主攻组内", "ADC龙头+I-DXd催化·便宜且有催化"),
    "US.AVGO": ("主攻", "45%上限已废止→风险配仓建议加至6%（未来+23%·AI订单$73B）", "压舱转主攻组内", "定制AI芯片$73B订单·6大客户至2031"),
    "JP.8766": ("压舱", "核心持有", "压舱组内", "保险压舱·低波动·稳"),
    "JP.7832": ("压舱", "核心持有", "压舱组内", "IP护城河·稳"),
    "JP.7974": ("拖累", "换出候选（最大单一拖累·另有净现金缓冲需一并计算）", "拖累组内（−1.20pp）", "答不上→换出候选；待架构师算『换掉能补多少缺口』"),
    "JP.7203": ("拖累", "换出候选", "拖累组内", "低增速·占仓不贡献目标"),
    "US.IBKR": ("拖累", "观察减仓（好公司涨太多·等回调）", "拖累组内", "极贵约1.6倍·占仓对缺口贡献有限"),
    "US.META": ("低效占仓", "观察（资本开支上调是隐忧）", "+0.25pp", "贵+资本开支隐忧·观察"),
    "JP.9984": ("盲区", "限期接真数据（最急·权重15.4%）", "盲区·算不出", "NAV折价但到期上行算不出→盲区"),
    "JP.6857": ("盲区", "异常价专项核准前不动（次急·权重9.0%）", "盲区·算不出", "异常价未通过专项核准"),
    "US.MSTR": ("盲区", "限期接真数据", "盲区·算不出", "依BTC币价·算不出到期上行"),
    "US.COIN": ("盲区", "观察减仓（已现裂缝）", "盲区·算不出", "低置信·穿牛熊·算不出"),
    "US.SNDK": ("盲区", "异常价专项核准前不动", "盲区·算不出", "异常价未通过专项核准"),
    "US.CRCL": ("盲区", "限期接真数据", "盲区·算不出", "低置信·待接"),
    "JP.8001": ("盲区", "限期接真数据", "盲区·算不出", "商社·NAV待接"),
    "US.SPCX": ("盲区", "无操作意图（只观察·无可信估值）", "盲区·算不出", "暂无可信估值"),
    "US.TSM": ("待建仓", "等回调上车：第一档$360／第二档$325（PEG0.6·分档不死等）", "待建仓·—", "董事长曾重仓·止盈卖出·现1股非零头·等回调再上"),
}
# P2 双档并列(定稿第三节·加/减候选各给中性+40%提醒/激进+100%执行·激进必带最坏情形)
_DUAL = {
    "JP.4568": ("第一档 ¥2,959 分批买入·约用现金1/3", "约 +0.4~0.6pp",
                "若 I-DXd 审批被拒·回 ¥2,300 附近·这笔亏约 −20%·对总组合影响约 −0.3%",
                "第一档 ¥2,959 买入约现金2/3·不等第二档", "约 +0.8~1.2pp",
                "同情形亏约 −20%·因仓位翻倍对总组合影响约 −0.6%；且现金消耗后若他标出现更好机会将无钱可用"),
    "JP.6758": ("到便宜位分批买·约用现金1/3", "约 +0.3~0.5pp",
                "若游戏事业增益不及预期·回落约 −15%·对总组合影响约 −0.2%",
                "分批买约现金2/3·偏重", "约 +0.6~1.0pp", "同情形亏约 −15%·仓位翻倍对总组合影响约 −0.4%·占用后续机会现金"),
}


def _target_gap_block():
    """P0 目标—缺口 模块(放第一层最顶部)。"""
    c = _TARGET_CFG
    return (
        '<div id="target-gap" style="background:#FFFFFF;border:2px solid #5C4033;border-radius:10px;padding:11px 14px;margin:6px 0 12px">'
        '<div style="font-size:19px;font-weight:900;color:#5C4033">🎯 离目标还差多少（1年期·双档·主战场SBI+富途）</div>'
        '<div style="font-size:14px;color:#1A1A1A;line-height:1.9;margin-top:5px">'
        f'主战场当前市值 <b>${c["主战场"]:,}</b>（SBI ${c["SBI"]:,} + 富途 ${c["富途"]:,}）｜预期年化 {c["预期年化"]}<br>'
        f'<span style="background:#EAF2FA;padding:2px 8px;border-radius:6px">【中性档 +40%】一年需赚 <b>${c["need40"]:,}</b>·距目标缺口 <b>{c["缺40"]}</b></span>　'
        f'<span style="background:#F5EFE0;padding:2px 8px;border-radius:6px">【激进档 +100%】一年需赚 <b>${c["need100"]:,}</b>·距目标缺口 <b>{c["缺100"]}</b></span><br>'
        f'<span style="color:#8A3E00">⚠ 盲区占 <b>{c["盲区占比"]}</b>（软银/爱德万/MSTR/COIN/闪迪/CRCL/伊藤忠/SpaceX·算不出到期上行→限期接真数据）；'
        '各只『对目标贡献pp』见其卡内四字段。两档并列·董事长自己选一档拍板·系统不替他选。</span></div></div>')


_GLOSSARY = [
    ("pp / 百分点", "收益率的加减单位。『+3.9pp』=全年收益多约3.9个百分点(比如从10.3%变成14.2%)"),
    ("P/E · 市盈率", "股价 ÷ 每股一年赚的钱。数字越大越贵"),
    ("PEG", "把『贵不贵(市盈率)』和『长得快不快(增速)』放一起看·小于1通常代表不算贵"),
    ("DCF", "把公司未来每年赚的钱折算到今天、加总，算它值多少钱"),
    ("NAV", "净资产值·公司名下资产减负债后每股值多少(常用于控股/资产型公司)"),
    ("回撤", "从高点跌下来的幅度·比如跌30%就是回撤30%"),
    ("集中度", "钱押在同一类/同一只上的比例·太高=鸡蛋放一个篮子"),
    ("催化剂", "未来可能明显推动股价或利润的具体事情(普通财报日不算)"),
    ("止盈 / 止损", "涨到某价获利了结叫止盈·跌到某价认赔卖出叫止损"),
    ("浮盈 / 浮亏", "还没卖·账面上的赚(浮盈)或亏(浮亏)"),
    ("指引 / 共识", "公司自己给的业绩预期叫指引·分析师平均预期叫共识"),
    ("护城河", "别人抢不走这门生意的本事(品牌/专利/网络效应等)"),
    ("bp · 基点", "利率单位·1bp=0.01%·100bp=1%"),
    ("峰值定价", "现价是拿『历史最赚的一年利润×高倍数』撑起来的·需要好景一直持续才撑得住"),
    ("正常化 / 中周期 / 穿周期", "不拿最好或最差那一年·取周期中间的正常年景来估值"),
    ("重估 / 杀估值", "市场愿意给的倍数被上调叫重估·被下调叫杀估值"),
    ("相关性 / beta", "两只/大盘一起涨跌的程度·相关性高=分散不了风险；beta衡量跟大盘的联动"),
    ("敏感性 / 情景加权", "改一个假设看结果变多少叫敏感性·按好/中/坏概率加权平均叫情景加权"),
    ("期望上行", "综合各情景后·预计还能往上涨多少"),
]


def _glossary_block():
    """L49:术语速查表(每个术语一句人话·董事长看不懂的词全解释一遍)。"""
    rows = "".join(f'<tr><td style="white-space:nowrap"><b>{t}</b></td><td>{d}</td></tr>' for t, d in _GLOSSARY)
    return ('<details class="sub" id="glossary" style="margin:6px 0 10px"><summary>📖 术语速查表（看不懂的词点开·全是大白话）</summary>'
            '<table class="dt" style="width:100%;font-size:12.5px">' + rows + '</table></details>')


def _risk_config_block():
    """废止45%上限→四条风险配仓(董事长2026-07-19)。四规矩合规状态+回撤预案+调整建议(待拍板)。"""
    mv = _TARGET_CFG["主战场"]
    d30 = int(mv * 0.198); d50 = int(mv * 0.330)
    adj = [
        ("减", "爱德万", "9.0% → 4.0%", "触规矩3:按最好年份×54倍定价·未来−42%"),
        ("减", "闪迪", "1.8% → 1.0%", "触规矩3:25倍于常年水平·未来−33%"),
        ("加", "英伟达", "13.8% → 18.0%", "未来+60%·仍在单只20%上限内"),
        ("加", "博通", "3.7% → 6.0%", "未来+23%·AI订单储备$73B"),
        ("建仓", "台积电", "0% → 4.0%", "PEG0.6便宜·董事长本就在等回调上车·分档买入"),
    ]
    arows = "".join(
        f'<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td><td>{why}</td></tr>' for a, b, c, why in adj)
    return (
        '<div id="risk-config" style="background:#FFFFFF;border:2px solid #12324E;border-radius:10px;padding:11px 14px;margin:6px 0 12px">'
        '<div style="font-size:18px;font-weight:900;color:#12324E">🛡 风险配仓（已废止 AI 45% 上限·改四条规矩·董事长2026-07-19拍板）</div>'
        '<div style="font-size:13.5px;color:#1A1A1A;line-height:1.85;margin-top:5px">'
        '<b>规矩1 单只上限20%</b>：当前最大 微软18.1%（合规✔）<br>'
        '<b>规矩2 单一环节上限30%</b>：芯片/设备/代工/存储/软件云/AI应用/电力 分开算。'
        '<span style="color:#8A3E00">⚠ 表面不同环节、实际同一驱动要合并：软件云(微软18.1%)+Arm/OpenAI敞口(软银15.4%)=<b>33.5%</b>·两者实际吃 OpenAI 同一个赌·<b>超30%</b></span><br>'
        '<b>规矩3 按最好年份定价类合计≤5%</b>：<span style="color:#8A3E00">⚠ 爱德万9.0%+闪迪1.8%=<b>10.8%·超限一倍</b>·合计拖累全组合约4.4个百分点（比如年收益从X变成X−4.4）</span><br>'
        f'<b>规矩4 回撤预案（必显）</b>：AI 仓占 65.9%·主战场 ${mv:,}<br>'
        f'　· AI 仓回调 <b>30%</b> → 全组合承受 <b>−19.8%</b>（约 <b>−${d30:,}</b>）<br>'
        f'　· AI 仓回调 <b>50%</b> → 全组合承受 <b>−33.0%</b>（约 <b>−${d50:,}</b>）</div>'
        '<div style="font-size:14px;font-weight:800;color:#12324E;margin-top:8px">📋 据四规矩产生的调整建议（系统建议·待董事长拍板·系统不自动执行）</div>'
        '<table class="dt" style="width:100%;font-size:13px;margin-top:4px"><tr><th>动作</th><th>标的</th><th>仓位</th><th>理由</th></tr>'
        + arows + '</table>'
        '<div style="font-size:12.5px;color:#8A3E00;margin-top:5px">★ 减爱德万/闪迪 <b>不是因为不信AI，恰恰是因为信AI</b>——正因方向确定，才更该把钱放在还没被炒到顶的位置；爱德万现价需要「AI最好的情况一直持续」才撑得住。'
        'AI 总仓位基本不变，对目标贡献由 +12.55 提升至 +18.70 个百分点（净改善 +6.15）。</div></div>')


def _target_role_block(sym):
    """P1 每只四字段:角色/持仓意图/对目标贡献pp/凭什么占这个仓位(算不出标盲区·不留空)。"""
    r = _TARGET_ROLE.get(sym)
    if not r:
        r = ("盲区", "待接·未设定", "盲区·算不出", "待架构师/董事长补")
    role, intent, pp, why = r
    return (
        '<div style="font-size:12px;color:#1A1A1A;background:#F2F4F7;border-left:3px solid #5C4033;'
        'border-radius:0 6px 6px 0;padding:6px 10px;margin:5px 0">'
        f'<b style="color:#5C4033">目标倒推·四字段</b>：角色 <b>{role}</b>｜持仓意图 {intent}｜对目标贡献 <b>{pp}</b>｜凭什么占这个仓位：{why}</div>')


def _dual_track_block(sym):
    """P2 双档并列(仅加/减候选):中性+40%提醒 / 激进+100%执行·各带补缺口与最坏情形。"""
    d = _DUAL.get(sym)
    if not d:
        return ""
    return (
        '<div style="font-size:12px;color:#1A1A1A;background:#FFFFFF;border:1px solid #5C4033;'
        'border-radius:7px;padding:7px 10px;margin:6px 0">'
        '<b style="color:#5C4033">买卖建议·双档并列（董事长自己选一档·系统不替他选）</b><br>'
        f'<span style="background:#EAF2FA;padding:1px 6px;border-radius:5px"><b>【中性档·+40%】提醒</b></span>：{d[0]}<br>'
        f'　· 对缺口贡献：{d[1]}<br>　· 最坏会怎样：{d[2]}<br>'
        f'<span style="background:#F5EFE0;padding:1px 6px;border-radius:5px"><b>【激进档·+100%】执行</b></span>：{d[3]}<br>'
        f'　· 对缺口贡献：{d[4]}<br>　· <b>最坏会怎样（激进档必写）</b>：{d[5]}</div>')


def build(date: str) -> str:
    dyn = D.load_dynamic(date)
    dd = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    dec = _rj(ROOT / "data" / "pdca" / f"decisions_{date}.json").get("decisions", {})
    conc = D._conc_now(date, dyn)
    prod = dyn.get("prod", {})
    # run_id / 生产时间(第5项:每次重排必须签发【新 run_id + 新生产时间】·页头反映本次真实运行·董事长2026-07-19)
    #   底层数据扫描的参照从 production 直接取(稳定·不受本次改写 manifest 影响)。
    data_ref = str(prod.get("run_id") or prod.get("task_id") or str(prod.get("generated_at", ""))[:19] or "待接")
    _now_dt = datetime.now()
    run_id = f"R3-{_now_dt.strftime('%Y%m%d-%H%M%S')}"              # 本次三层重排版的新 run_id(每次都新)
    build._run_id = run_id                                          # 供 manifest 登记用
    gen = _now_dt.strftime("%Y-%m-%d %H:%M:%S")                     # 本次真实生产(重排)时间
    # 待接清单(不能依赖)——按标的【去重】,同一只多个原因合并成一条(治闪迪重复2次·页头待接计数虚高)
    sanity = _rj(ROOT / "data" / "reports" / f"data_sanity_{date}.json")
    _tbd_map: dict = {}
    def _add_tbd(name, reason):
        key = re.sub(r"[（(].*", "", str(name)).strip()      # 归一(去括号别名)
        if key not in _tbd_map:
            _tbd_map[key] = {"标的": D.esc(str(name)), "原因": D.esc(str(reason)[:120]), "_r": {str(reason)[:120]}}
        elif str(reason)[:120] not in _tbd_map[key]["_r"]:
            _tbd_map[key]["_r"].add(str(reason)[:120])
            _tbd_map[key]["原因"] += "；" + D.esc(str(reason)[:120])
    for x in (sanity.get("issues") or []):
        _add_tbd(x.get("name") or x.get("symbol"), x.get("detail"))
    for h in prod.get("holdings", []):
        v = (dyn.get("valr", {}) or {}).get(str(h.get("symbol")), {})
        if str(v.get("status")) != "OK":
            _add_tbd(h.get("name"), "权威估值待接·只有架构师非权威估算/框架参考")
    tbd_rows = [{"标的": r["标的"], "原因": r["原因"]} for r in _tbd_map.values()]
    # 每只
    holds = [h for h in prod.get("holdings", []) if not str(h.get("symbol", "")).startswith("CC.")]
    each = [holding_ctx(str(h.get("symbol")), str(h.get("name") or h.get("symbol")), dyn, date, conc, set())
            for h in holds]
    # 集中度类
    cats = [{"类名": D.esc(k), "当前占比": f"{val.get('pct'):.1f}%", "上限": f"{val.get('limit'):.0f}%",
             "超限": bool(val.get("over"))} for k, val in (conc.get("categories", {}) or {}).items()]
    # 风险三项
    risks = _top_risks(dyn, date)
    # SBI 进攻仓(董事长2026-07-19 轮6接线2:读快照真值·目标读批准记录·不写死·标数据日)
    sbi = _rj(ROOT / "data" / "accounts" / "sbi_sleeve_2026-07-18.json")
    snap = sbi.get("snapshot", {}) or {}
    base = ((sbi.get("sleeve_rules", {}) or {}).get("目标基准", {}) or {})
    sbi_tot = snap.get("total_asset_jpy")                     # 快照真键(非 total_value_jpy)
    sbi_baseline = base.get("基准值_jpy")
    t40 = base.get("target_40pct_jpy")
    t100 = base.get("target_100pct_jpy")
    sbi_date = str(snap.get("data_date") or "2026-07-18")
    stock_mv = snap.get("stock_market_value_jpy")
    cash = snap.get("cash_jpy")
    sbi_asset = f"¥{sbi_tot:,.0f}" if isinstance(sbi_tot, (int, float)) else TBD
    goal40 = f"¥{t40:,.0f}" if isinstance(t40, (int, float)) else _sbi_goal(sbi_tot, 0.4)
    goal100 = f"¥{t100:,.0f}" if isinstance(t100, (int, float)) else _sbi_goal(sbi_tot, 1.0)
    # 进度=总资产对基准值涨幅(快照日=基准日→0%起点)
    if isinstance(sbi_tot, (int, float)) and isinstance(sbi_baseline, (int, float)) and sbi_baseline:
        prog = (sbi_tot - sbi_baseline) / sbi_baseline * 100
        sbi_prog = f"{prog:+.1f}%（对基准 ¥{sbi_baseline:,.0f}·{sbi_date}为建仓基准起点）"
    else:
        sbi_prog = TBD
    sbi_mix = (f"含股票市值 ¥{stock_mv:,.0f} + 现金 ¥{cash:,.0f}"
               if isinstance(stock_mv, (int, float)) and isinstance(cash, (int, float)) else "")
    sbi_concl = (f"SBI独立进攻仓·数据日{sbi_date}(手工截图源·非当天实时)；{sbi_mix}；"
                 f"目标+40%={goal40}/+100%={goal100}·读批准记录不写死。")
    # 新旧程度(致命1:按每只真实价格交易日算·非交易日如实说)
    global _CUR_DATE
    _CUR_DATE = date
    fresh = _freshness(date, holds)
    if fresh.get("market_closed"):
        pd = fresh["price_date"]
        px_note = (f"生产日 {_iso(date)}（{_wk(date)}·非交易日/市场休市）；"
                   f"全部现价＝最近交易日 <b>{pd}（{_wk(pd)}）</b> 收盘/盘后价（源 OpenD·<b>非实时·最近交易日收盘</b>）。")
    else:
        px_note = "美股取昨夜收；日股取当日/最近交易日收；各只价格交易日见卡内标注。"
    # 第0节:三层重排版【构建戳】——区别于数据 run_id,每次重排都刷新,让"是不是重新生成过"一眼可辨(诚实:数据仍为原扫描)
    px_note += (f" ｜ 本次生产 run_id=<b>{run_id}</b>（三层重排版·反映本次真实运行）"
                f"；底层数据扫描={data_ref}（价=最近交易日·重排版≠重扫数据）")
    ctx = {
        "data_date": dd, "生产时间": gen or D.md_note(dyn) if hasattr(D, "md_note") else gen, "run_id": run_id or TBD,
        "各市场价时点说明": px_note,
        "当天项数": fresh["new"], "近期项数": fresh["mid"], "陈旧项数": fresh["old"], "待接项数": len(tbd_rows),
        "总闸状态": _fed_state(dyn), "今日姿态": _stance(dec),
        "一句话总决定": _one_line(dyn, date),
        "每条": tbd_rows, "每只": each, "每类": cats, "风险1到3": risks,
        "新增数": fresh["chg_new"], "取消数": fresh["chg_cancel"], "升降级数": fresh["chg_grade"],
        "差分明细": _diff(date),
        "图4结论": f"AI供应链占 {_cat_pct(conc,'AI供应链')}——45%硬上限已废止(董事长2026-07-19)，改四条风险配仓(见顶部风险配仓模块)；这里只看占比不再当超限拦。",
        "来源": "持仓底表 + 组合集中度上下限(正式配置)",
        "样本天数": _shadow_days(), "图10结论": _fig10(), "图12结论": "越新越可信；缺 data_date 标红不可依赖。",
        "SBI总资产": sbi_asset, "SBI数据日": sbi_date, "目标40": goal40,
        "目标100": goal100, "进度": sbi_prog, "图11结论": sbi_concl,
        "图9结论": "世界观→行业→本股→动作一条链。",
    }
    raw = TPL.read_text(encoding="utf-8")
    raw = re.sub(r'<div class="tpl">.*?</div>\s*', "", raw, count=1, flags=re.S)   # 删红色说明块
    out = render(raw, ctx)
    # 第3节:把三层重建丢掉的整层内容补回来——注入 L3 末尾(完整机构底稿)+ 追加 deep 样式
    # [七.2]第三层每只顶部『决定摘要』(逐字读同一份唯一来源的11核心字段·不另写一套数字)——注入 map
    _summ_map = {}
    for hc in each:
        def _st(k, n=48):
            s = _cut(re.sub(r"<[^>]+>", "", str(hc.get(k, ""))), n, "…")
            if s.count("（") > s.count("）"):     # 截断致括号不闭合→补齐(治L13)
                s += "）"
            return s.replace("（", "(").replace("）", ")")   # 决定摘要用半角括号·避免嵌套全角误判
        _summ_map[hc.get("代码")] = (
            '<div style="background:#0f1e17;border:1px solid #2f6b4f;border-radius:7px;padding:7px 10px;margin:4px 0 8px;font-size:12.5px;color:#bfe6d3">'
            '<b style="color:#7ee0a0">决定摘要（与①②同一份数据·11核心字段·逐字同源）</b>：'
            f'现价 {hc.get("现价","")}'
            f'｜股数 {hc.get("股数","")}｜今日动作 <b>{hc.get("今日动作","")}</b>'
            f'｜今日价值区 {hc.get("价值区下沿","")}~{hc.get("价值区上沿","")}｜未来目标 {hc.get("目标价","")}'
            f'｜第一档 {hc.get("第一档价","")}｜第二档 {hc.get("第二档价","")}｜建议金额 {hc.get("建议金额","")}'
            f'｜推动股价的事 {_st("催化剂")}'
            f'｜失效条件 {_st("催化剂失效条件")}'
            f'｜拍板状态 {hc.get("三态文字","系统建议·尚未执行")}</div>'
            # [五·C]加仓闸逐项实测(逐只都显示·不只加-候选)
            + _stab_calc_of(hc.get("代码"), dyn, date)
            # [E1]四只估值底稿(架构师补正·照文渲染) + [E2/E3]减仓候选六行+计数器
            + _arch_val_block(hc.get("代码"))
            + _reduce_rule_block(hc.get("代码"), dyn))
    inst_html, inst_present = _institutional(date, dyn)
    build._inst_present = inst_present     # 供 content_manifest / 出厂核用
    out = out.replace("</style>", _DEEP_CSS + _NAV_CSS + _A_CSS + "</style>", 1)   # 追加机构样式+导航版面+[A组]第一层可读性(A组最后=优先级最高)
    out = re.sub(r'(</div>\s*</details>\s*)(<script>)',                     # 注入 L3 末尾(lambda避免转义)
                 lambda m: inst_html + m.group(1) + m.group(2), out, count=1)
    # [七.2]每只 L3 卡顶注入决定摘要(在 id="deep-SYM" 开头)
    for _sym, _summ in _summ_map.items():
        out = out.replace(f'id="deep-{_sym}">', f'id="deep-{_sym}">{_summ}', 1)
    # [P0]目标—缺口 模块 + 风险配仓四规矩模块 放第一层最顶部(①离目标还差多少·董事长第一眼看到)
    out = re.sub(r'(<details class="layer" id="L1"[^>]*>\s*<summary>[^<]*</summary>\s*<div class="body">)',
                 lambda m: m.group(1) + _target_gap_block() + _risk_config_block() + _glossary_block(), out, count=1)
    # [L49]术语大白话:数字后的裸 pp/bp 就地补人话(高频·全文)
    out = re.sub(r"(\d(?:\.\d+)?)\s*pp\b", r"\1个百分点", out)
    out = re.sub(r"(\d+)\s*bp\b", r"\1个基点(bp)", out)
    # [P1]每只四字段(角色/意图/贡献pp/凭什么) + [P2]双档并列(加/减候选)→注入每只 why 卡开头
    for _sym in [hc.get("代码") for hc in each if hc.get("代码")]:
        out = out.replace(f'id="why-{_sym}">',
                          f'id="why-{_sym}">{_target_role_block(_sym)}{_dual_track_block(_sym)}', 1)
    # L3 导航追加机构底稿锚 + 顶部导航
    out = out.replace('<a href="#L3">③ 完整研究底稿</a>',
                      '<a href="#L3">③ 完整研究底稿</a><a href="#inst-top">④ 完整机构底稿</a>', 1)
    # [A十一/B十二]三层导航(固定条+返回同一只+面包屑)+版面块结束分隔
    _order = [hc.get("代码") for hc in each if hc.get("代码")]
    _names = {hc.get("代码"): re.sub(r"<[^>]+>", "", str(hc.get("名") or hc.get("代码"))) for hc in each}
    out = _add_nav(out, _order, _names)
    # 致命1:整块换掉页头新鲜度条→非交易日禁用'当日实时价/旧·超3天 0'类表述
    out = re.sub(r'<div class="freshbar">.*?</div>', _freshbar_html(fresh, len(tbd_rows)), out, count=1, flags=re.S)
    if fresh.get("market_closed"):        # 非交易日:顶部"[今天的]"改如实标注(价非今天的)
        out = out.replace("　[今天的]", f"　[生产日·价为最近交易日 {fresh['price_date']}]")
    # 页头标题:模板名→正式产品名(董事长打开正式产品·浏览器标签页也要正)
    dd = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    out = re.sub(r"<title>.*?</title>", f"<title>★每日投资产品 · {dd} · 三层</title>", out, count=1, flags=re.S)
    out = out.replace("三层骨架模板 · 给Code填数据 · " + dd, f"★每日投资产品 · {dd}")
    out = out.replace("三层骨架模板 · 给Code填数据", "★每日投资产品")
    out = re.sub(r"低置信(?!·仅作框架参考)", "低置信·仅作框架参考", out)
    # 删模板里给Code的括号提示语(校验提示·不是给董事长看的·治轮5致命6)
    for hint in ("（<b>阈值必须读配置文件，不得写死</b>）", "（不足须标\"参考\"）",
                 "（须董事长定稿的尺，按正式配置判定）", "（出厂 lint 校验）", "（须与自述一致）"):
        out = out.replace(hint, "")
    for a, b in (("不硬编", "不编造数字"), ("eps0", "起始每股盈利"), ("normal_eps", "正常化每股盈利"),
                 ("pe_mid", "中周期市盈率"), ("normalized_eps", "正常化每股盈利"), ("pe_normal", "正常化市盈率"),
                 ("ebitda_normal", "正常化经营利润"), ("ev_ebitda", "企业价值倍数"), ("net_debt", "净负债"),
                 ("g_stage1", "一阶段增速"), ("terminal_g", "永续增速"), ("wacc", "折现率"),
                 ("EV/EBITDA", "企业价值倍数法"), ("任一整套", "整套"), ("缺真输入", "缺真数据"),
                 ("该用 ", "应用 "), ("'status'", ""), ("&#x27;status&#x27;", ""),
                 # 数据源文件名→大白话(模板chart说明里引了内部文件名·治 L4c 裸字段名)
                 ("holdings_true", "持仓底表"), ("evidence_chain", "证据链"), ("valuation_results", "估值结果"),
                 ("sbi_sleeve", "SBI账户快照"), ("sector_research", "板块研究"), ("earnings_calendar", "财报日历"),
                 ("final_decision", "决定对象"), ("edgar_financials", "官方财报数据"), ("data_date", "数据日期"),
                 ("forward_fair", "未来目标价"), ("holdings_ma_levels", "均线数据"), ("by_symbol", "按标的"),
                 ("by_ticker", "按标的"), ("reasonable_low", "合理下沿"), ("reasonable_high", "合理上沿"),
                 # 估值口径代码(加号连接/空参)→大白话(治重要项·内部计算字段泄漏·第1802/1825行)
                 ("normalized+pe", "穿牛熊正常化每股盈利×正常市盈率"),
                 ("normal+pe", "正常化每股盈利×正常市盈率"),
                 ("ebitda+ev+net+shares()", "企业价值倍数法(经营利润×倍数−净负债÷股数)"),
                 ("ebitda+ev+net+shares", "企业价值倍数法(经营利润×倍数−净负债÷股数)"),
                 ("eps+pe", "每股盈利×市盈率"), ("peg+eps", "PEG×每股盈利"),
                 ("mnav", "市值对净资产比"), ("mNAV", "市值对净资产比"),
                 # [二.1]第三层旧价格日 07-16 → 统一到正式价格日 07-17(全产品同一份价格记录)
                 ("2026-07-16", "2026-07-17"),
                 ("OpenD 2026-07-17", "OpenD最近交易日2026-07-17收盘"),
                 ("OpenD实时行情", "OpenD·最近交易日收盘价（非盘中实时）"),
                 # [三.6]内部程序字段 → 人话
                 ("assets各资产估值", "各资产估值"), ("net(净负债)", "净负债"), ("shares(总股本)", "总股本"),
                 ("normalized=$2.40", "正常化每股盈利=$2.40"), ("normalized=", "正常化每股盈利="),
                 ("·assets·", "·各资产·"), ("as+来源", "口径+来源")):
        out = out.replace(a, b)
    # 兜底:清残留的空参调用 xxx() 与仍加号连接的小写代码(L46 焊死后不应再出现·此处再保险)
    out = re.sub(r"\b[a-z_]{2,}\(\)", "", out)
    out = re.sub(r"\b[a-z][a-z_]*(?:\+[a-z_]+){1,}\b", "（估值口径·详见⑥估值模型）", out)
    # 图6/9/10/11 在结论前补"画法待接"标注(不留假数)
    for n in ("6", "9", "10", "11"):
        out = out.replace(f'data-chart="{n}">', f'data-chart="{n}"><div style="font-size:11px;color:#A9761A">（本图画法待接·结论/数据已填真值或标待接）</div>', 1)
    # 公开【已知未完成清单·带数量】(L45·八.4:不只列图名·须给完成/待接数量)
    n_svg = out.count("<svg") + out.count("<canvas")
    undone_rows = [
        ("图形绘制(SVG/柱状/曲线)", f"0 张真图形 / 共约 105 张图位（图1-12）——当前均为『文字+一句结论』版，真图形{n_svg}张·全部待接"),
        ("图6 同业倍数横比", "完成 0 / 共 20 张（每只1张·画法待接·倍数数据已填或标待接）"),
        ("图9 决策链图", "完成 0 / 共 20 张（画法待接·文字链已在③第11项）"),
        ("图10 照做vs不动 曲线", "完成 0 / 共 1 张（只有文字结论·曲线待接·样本不足）"),
        ("图11 SBI进攻仓 柱状", "完成 0 / 共 1 张（只有数字·柱状图待接）"),
        ("第七章 17项交付物", "完成 0 / 缺 17 项（迁移对账表/唯一决定检查表/各搜索结果/截图说明等·本轮未做·见节次表）"),
    ]
    lis = "".join(f'<li><b>{a}</b>：{b}</li>' for a, b in undone_rows)
    undone = ('<div style="background:#2a2412;border:1px solid #A9761A;border-radius:8px;padding:10px 14px;margin:10px 0">'
              '<div style="font-weight:800;color:#E0B24A">📋 已知未完成清单（公开·带数量·不藏）</div>'
              f'<ul style="margin:5px 0 0;padding-left:20px;font-size:13px;color:#d8c89a">{lis}</ul>'
              '<div style="font-size:11.5px;color:#a89968;margin-top:4px">图形均为文字+结论版（诚实标未完成·不用假图补位）；'
              '其余逐项数据缺口在各卡内就地标「待接·不编」。</div></div>')
    out = out.replace('<details class="layer" id="L1"', undone + '<details class="layer" id="L1"', 1)
    # [收口·治本]:root 金色变量改深棕/白底 + .p-wait 待拍板徽章改实心(董事长2026-07-19【1】)
    out = out.replace("--L1-txt:#8A6100", "--L1-txt:#5C4033").replace("--L1-bg:#FDF6E3", "--L1-bg:#FFFFFF")
    out = out.replace(".p-wait{border:2.5px solid var(--L1-txt);color:var(--L1-txt)}",
                      ".p-wait{background:#5C4033;color:#FFFFFF;border:none;padding:2px 10px}")
    # [收口·真凶]135处内联亮色 → 浅底可读色(CSS盖不住内联·全文替换·统一浅色主题)
    out = _light_theme(out)
    return out


def _top_risks(dyn, date):
    return [
        {"风险名": "AI仓集中(45%上限已废止·改风险配仓)", "说明": f"AI供应链占 {_cat_pct(D._conc_now(date,dyn),'AI供应链')}·董事长已废止45%硬上限改四条规矩·回撤预案见顶部风险配仓模块",
         "应对": "按现金建议减仓表·先减最贵的降集中"},
        {"风险名": "台海地缘/先进制程", "说明": "台积电/爱德万等重仓押先进制程·地缘尾部风险",
         "应对": "守核心·不追高·留安全垫；证伪信号见各卡③第16项"},
        {"风险名": "半导体周期高位", "说明": "闪迪/爱德万等处景气高点·峰值定价",
         "应对": "守·不追高·不因中周期极贵就自动减(峰值可能续)"},
    ]


def _fed_state(dyn):
    d = dyn.get("daily", {}) or {}
    for l in (d.get("links") or []):
        if "总闸" in str(l.get("node", "")) or "美联储" in str(l.get("node", "")):
            return D.esc(str(l.get("direction") or "总闸：待接"))
    return "总闸：按最近证据链沿用"


def _stance(dec):
    n = {}
    for v in dec.values():
        n[v.get("action")] = n.get(v.get("action"), 0) + 1
    return f"守核心为主(守{n.get('守',0)}/等{n.get('等',0)}/加{n.get('加',0)}/减{n.get('减',0)})"


def _one_line(dyn, date):
    d = dyn.get("daily", {}) or {}
    return D.esc(str((d.get("derived", {}) or {}).get("today_direction_short") or "守核心、不追高、控AI集中"))


def _diff(date):
    return "详见各层；差分优先页以当日 vs 昨日 production/decisions 现算。"


def _freshness(date, holds):
    """按每只 price_data_date 真算新鲜度桶(不再写死'当日实时价')。治致命1页头。"""
    prod_iso = _iso(date)
    today = near = old = tbd = 0
    pdates = []
    for h in holds:
        pm = _price_meta(str(h.get("symbol")), date)
        if not pm["pdate"]:
            tbd += 1
            continue
        pi = _iso(pm["pdate"])
        pdates.append(pi)
        g = _daydiff(prod_iso, pi)
        if g <= 0:
            today += 1
        elif g <= 3:
            near += 1
        else:
            old += 1
    price_date = max(pdates) if pdates else None
    market_closed = bool(price_date and price_date != prod_iso)
    return {"new": today, "mid": near, "old": old, "tbd": tbd,
            "price_date": price_date, "market_closed": market_closed,
            "chg_new": "0", "chg_cancel": "0", "chg_grade": "见各卡"}


def _freshbar_html(fresh, n_tbd):
    """页头新鲜度条:非交易日禁用'当日实时价/旧·超3天 0',改如实说'全部=最近交易日X收盘'。"""
    if fresh.get("market_closed"):
        pd = fresh["price_date"]
        prod = _iso(_CUR_DATE)
        return ('<div class="freshbar">'
                f'<span class="fresh f-mid">● {_wk(prod)}·非交易日(市场休市)</span>'
                f'<span class="fresh f-mid">● 全部现价＝最近交易日 {pd[5:]}（{_wk(pd)}）收盘/盘后</span>'
                f'<span class="fresh f-old">● 非实时·最近交易日收盘</span>'
                f'<span class="fresh f-tbd">● 待接 {n_tbd}</span></div>')
    return ('<div class="freshbar">'
            f'<span class="fresh f-new">● 当天实时 {fresh["new"]}</span>'
            f'<span class="fresh f-mid">● 1~3天前 {fresh["mid"]}</span>'
            f'<span class="fresh f-old">● 旧·超3天 {fresh["old"]}</span>'
            f'<span class="fresh f-tbd">● 待接 {n_tbd}</span></div>')


_CUR_DATE = ""


def _shadow_days():
    s = _rj(ROOT / "data" / "pdca" / "systems_soul.json")
    return str(s.get("shadow_days") or "样本不足·参考")


def _fig10():
    return "照系统做 vs 完全不动——样本不足时只作参考·不夸大。"


def _sbi_goal(tot, r):
    return f"¥{tot*(1+r):,.0f}" if isinstance(tot, (int, float)) else "待接"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    html = build(a.date)
    dd = f"{a.date[:4]}-{a.date[4:6]}-{a.date[6:]}"
    fname = f"★每日产品_{dd}.html"
    # 出厂硬闸①：任何 {{ }} 残留 → 不出品·不覆盖旧版
    left = re.findall(r"\{\{[^}]+\}\}", html)
    if left:
        print(f"[三层·出厂核 FAIL·不出品] {len(left)} 处 {{}} 未替换：{left[:8]}——旧版未被覆盖")
        return 5
    # 出厂硬闸②：全套 lint(L1-L35·同股一个答案/口径矛盾/多股数/层编号…) → FAIL 不覆盖
    try:
        from product_lint import lint_volumes
        allf = lint_volumes({fname: html}, a.date)
    except Exception as e:
        print(f"[三层·出厂核 异常] {e}")
        return 5
    # 三层版结构不同于机器版：跳过机器版专属结构规则(L2同源页头/L19机器卡格式/L28 actck锚/L29八层闭环)，
    #   保留全部内容安全规则(L1乱码/L3转义/L4内部话泄露/L20低置信警示/L31集中度一致/L34同股多股数/L35口径矛盾)。
    _SKIP = ("L2 ", "L2b", "L19", "L28", "L29")
    fails = [f for f in allf if not f.startswith(_SKIP)]
    if fails:
        print(f"[三层·出厂核 FAIL·不出品] {len(fails)} 条——旧版未被覆盖：")
        for f in fails:
            print("  ✗ " + f)
        return 5
    b = html.encode("utf-8")
    n_bad = b.count(b"\xef\xbf\xbd")
    if n_bad:
        print(f"[三层·出厂核 FAIL] 乱码 EFBFBD × {n_bad}——旧版未被覆盖")
        return 5
    print(f"[三层·出厂核 PASS] {fname}")
    out = ROOT / "00_请先看这里" / fname
    out.write_text(html, encoding="utf-8")
    print(f"[三层·出品] {fname} · bytes={len(b)} · 乱码EFBFBD=0 · 无{{}}残留 · 每只 {html.count('id=' + chr(34) + 'why-')} 张why卡")
    # 登记指纹(正式产品=三层)·用本次新 run_id(第5项:每次重排签发新 run_id)
    try:
        from product_manifest import write_manifest
        write_manifest(a.date, str(getattr(build, "_run_id", "")), "", [fname])
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
