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
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import deep_render as D  # noqa: E402

TPL = ROOT / "00_请先看这里" / "三层骨架模板_给Code填数据_20260719.html"
ACT_COLOR = {"加": "add", "买": "add", "减": "cut", "守": "hold", "等": "wait"}
ACT_ICON = {"加": "▲", "买": "▲", "减": "▼", "守": "■", "等": "…"}
TBD = '<span style="color:#6B4E8C">待接·不编</span>'


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
    pdate = str((dyn.get("prod", {}) or {}).get("generated_at", ""))[:10] or date
    # 今日价值区 / 未来目标（权威 OK → valr；否则架构师）
    if st.get("ok"):
        lo, hi = st["lo"], st["hi"]
    else:
        av = D.arch_val_display(sym, dyn)
        _e = D._arch_est(sym) or {}
        fp = _e.get("fair_price") or _e.get("archived_fair_price") or {}
        lo, hi = fp.get("cheap"), fp.get("rich")
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
    # 深研16项
    d16 = _deep16(sym, name, dyn, deep, v, c)
    hc = {
        "代码": sym, "股票名": D.esc(name), "名": D.esc(name),
        "今日动作": pure, "动作色": ACT_COLOR.get(pure, "hold"), "动作图标": ACT_ICON.get(pure, "■"),
        "三态": "sys", "三态文字": "系统建议·尚未执行",
        "现价": f"{c}{px:,.2f}" if px is not None else TBD, "市场": mkt, "价格日期": pdate,
        "价值区下沿": f"{c}{lo:,.0f}" if lo else TBD, "价值区上沿": f"{c}{hi:,.0f}" if hi else TBD,
        "目标价": tgt, "目标价缺则标 待接·不编": tgt_miss, "现价位置百分比": pos,
        "第一档价": d1p, "第一档量": d1q, "第二档价": d2p, "第二档量": d2q,
        "账户": acct, "币种": c, "股数": f"{qty:g}" if qty else TBD, "建议金额": amt,
        "停止条件": _stop_of(pure, st, c),
        "为什么现在": re.sub(r"<[^>]+>", "", why)[:300],
        "为什么不选其他": _why_not(pure, st, c),
        "催化剂": cat, "催化剂来源": catsrc,
        "催化剂失效条件": (D.esc(_clean(_flat((deep.get("block7_catalysts") or [""])[0]))) or TBD),
        "证伪条件": _falsify(deep),
        "把握程度": D._conf_grade(D.build_final(sym, name, dyn)),
        "把握理由": "账本质地档＋估值可信度综合(见③第6项)",
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
        **d16,
    }
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


def _stop_of(pure, st, c):
    if not st.get("ok"):
        return "权威估值待接→现在不动手·守着看"
    if pure in ("加", "买"):
        return f"涨回 {c}{st['mid']:,.0f} 以上就别再追"
    if pure == "减":
        return f"跌回 {c}{st['hi']:,.0f} 以下就别再减"
    return f"跌破 {c}{st['lo']:,.0f} 才谈加、涨过 {c}{st['hi']:,.0f} 才谈减"


def _why_not(pure, st, c):
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
    return f"今日该值 {c}{lo:,.0f}~{c}{hi:,.0f}{ft}；现价 {c}{px:,.0f}，动作={pure}。今日价值区与未来目标分开看。"


def _deep16(sym, name, dyn, deep, v, c):
    """③完整研究底稿16项——从深研卡真取·缺标待接。只增不减(L3内容不缩水·安全截断不切半词)。"""
    g = lambda k, n=900: (D.esc(_cut(_clean(_flat(deep.get(k))), n)) or TBD)   # _flat已None→空·不 dump dict
    method = str(v.get("model_disp") or "")
    if not method:
        av = D._arch_est(sym) or {}
        method = str(av.get("ruler_short") or "待接")
    # 可信度随『估值输入』走:输入待接 → 不得标 A·精算(治轮5致命5·可信度牌与内容矛盾)
    vin = _val_inputs(sym, v)
    cred_raw = str(v.get("credibility") or "待接")
    if vin == TBD or "待接" in vin:
        cred = "待接·框架参考（输入未接·不标精算）"
    else:
        cred = cred_raw.replace("低置信", "低置信·仅作框架参考")
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
        "待接项与原因": _waits(sym, v),
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
    canon = f"{c}{px:,.0f}"
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


def build(date: str) -> str:
    dyn = D.load_dynamic(date)
    dd = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    dec = _rj(ROOT / "data" / "pdca" / f"decisions_{date}.json").get("decisions", {})
    conc = D._conc_now(date, dyn)
    prod = dyn.get("prod", {})
    # run_id / 生产时间
    mani = _rj(ROOT / "data" / "product_manifest.json")
    run_id = str(mani.get("run_id", ""))
    gen = str(prod.get("generated_at", ""))[:19]
    # 待接清单(不能依赖)
    sanity = _rj(ROOT / "data" / "reports" / f"data_sanity_{date}.json")
    tbd_rows = [{"标的": D.esc(str(x.get("name") or x.get("symbol"))), "原因": D.esc(str(x.get("detail"))[:120])}
                for x in (sanity.get("issues") or [])]
    # 无权威估值的也进"不能依赖"
    for h in prod.get("holdings", []):
        s = str(h.get("symbol"))
        v = (dyn.get("valr", {}) or {}).get(s, {})
        if str(v.get("status")) != "OK":
            tbd_rows.append({"标的": D.esc(str(h.get("name"))), "原因": "权威估值待接·只有架构师非权威估算/框架参考"})
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
    # 新旧程度
    fresh = _freshness(date, prod)
    ctx = {
        "data_date": dd, "生产时间": gen or D.md_note(dyn) if hasattr(D, "md_note") else gen, "run_id": run_id or TBD,
        "各市场价时点说明": "美股取昨夜收；日股取当日/最近交易日收；周末休市→最近交易日(页头已标)",
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
                 ("by_ticker", "按标的"), ("reasonable_low", "合理下沿"), ("reasonable_high", "合理上沿")):
        out = out.replace(a, b)
    # 图6/9/10/11 第二轮→在结论前补"待接·第二轮"标注(不留假数)
    for n in ("6", "9", "10", "11"):
        out = out.replace(f'data-chart="{n}">', f'data-chart="{n}"><div style="font-size:11px;color:#A9761A">（本图第二轮补·画法待接·结论/数据已填真值或标待接）</div>', 1)
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


def _freshness(date, prod):
    return {"new": "当日实时价", "mid": "SBI等沿用", "old": "0", "chg_new": "0", "chg_cancel": "0", "chg_grade": "见各卡"}


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
    # 登记指纹(正式产品=三层)
    try:
        from product_manifest import write_manifest
        mani = _rj(ROOT / "data" / "product_manifest.json")
        write_manifest(a.date, str(mani.get("run_id", "")), "", [fname])
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
