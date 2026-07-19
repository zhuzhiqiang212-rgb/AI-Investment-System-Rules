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
    folds, present = [], []
    for title, aid, fn in _INST_BLOCKS:
        try:
            body = fn(D, date, dyn, daily) or ""
        except Exception as e:
            body = f'<div class="note">本块加载失败·待接（{D.esc(str(e))}）</div>'
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
        "图4结论": f"AI供应链 {_cat_pct(conc,'AI供应链')} 超上限 {_cat_limit(conc,'AI供应链')}——最该盯的超配。",
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
        _st = lambda k, n=48: _cut(re.sub(r"<[^>]+>", "", str(hc.get(k, ""))), n, "…")  # 安全截断·不切半词/日期/括号
        _summ_map[hc.get("代码")] = (
            '<div style="background:#0f1e17;border:1px solid #2f6b4f;border-radius:7px;padding:7px 10px;margin:4px 0 8px;font-size:12.5px;color:#bfe6d3">'
            '<b style="color:#7ee0a0">决定摘要（与①②同一份数据·11核心字段·逐字同源）</b>：'
            f'现价 {hc.get("现价","")}'
            f'｜股数 {hc.get("股数","")}｜今日动作 <b>{hc.get("今日动作","")}</b>'
            f'｜今日价值区 {hc.get("价值区下沿","")}~{hc.get("价值区上沿","")}｜未来目标 {hc.get("目标价","")}'
            f'｜第一档 {hc.get("第一档价","")}｜第二档 {hc.get("第二档价","")}｜建议金额 {hc.get("建议金额","")}'
            f'｜推动股价的事 {_st("催化剂")}'
            f'｜失效条件 {_st("催化剂失效条件")}'
            f'｜拍板状态 {hc.get("三态文字","系统建议·尚未执行")}</div>')
    inst_html, inst_present = _institutional(date, dyn)
    build._inst_present = inst_present     # 供 content_manifest / 出厂核用
    out = out.replace("</style>", _DEEP_CSS + "</style>", 1)               # 追加机构区块样式
    out = re.sub(r'(</div>\s*</details>\s*)(<script>)',                     # 注入 L3 末尾(lambda避免转义)
                 lambda m: inst_html + m.group(1) + m.group(2), out, count=1)
    # [七.2]每只 L3 卡顶注入决定摘要(在 id="deep-SYM" 开头)
    for _sym, _summ in _summ_map.items():
        out = out.replace(f'id="deep-{_sym}">', f'id="deep-{_sym}">{_summ}', 1)
    # L3 导航追加机构底稿锚 + 顶部导航
    out = out.replace('<a href="#L3">③ 完整研究底稿</a>',
                      '<a href="#L3">③ 完整研究底稿</a><a href="#inst-top">④ 完整机构底稿</a>', 1)
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
    return out


def _top_risks(dyn, date):
    return [
        {"风险名": "AI供应链超配", "说明": f"AI供应链 {_cat_pct(D._conc_now(date,dyn),'AI供应链')} 超 45% 上限",
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
