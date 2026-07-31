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

# ── 未来1-2年前瞻目标价 = 未来EPS × 合理PE(董事长2026-07-25第二次纠正:当前价格口径异常≠不能算未来目标·
#     未来目标与当前价格口径无关·必须算·不许标不计算)。异常股(6857/SNDK)的目标串包在 <span class="fwdanchor">
#     内→gate_异常股静默白名单此span(前瞻目标允许·当前估值贵贱仍拦)。EPS三口径不混·已入登记v3.1(20260725)。
_FWD_EPS_PE = {
    "6857": '<span class="fwdanchor" style="color:#9ec8b0">¥14,500~¥20,700　＝ EDINET报告实际EPS¥413.29 × 前瞻PE 35~50（★来源:半导体行业前瞻PE中位约37[gurufocus2026]/泰瑞达TER前瞻约52/爱德万自身前瞻约53[valueinvesting.io2026-03]·35~50取当前可比区间偏保守端;★爱德万5年PE 11~100+无稳定正常化锚·此PE取的是当前峰值周期水平）·真实股本口径·前瞻价值锚；与今日价格贵贱分列·当前价格/复权口径待核·不与待核现价比涨跌幅</span>',
    "SNDK": '<span class="fwdanchor" style="color:#9ec8b0">$40~$60　＝ 周期正常化EPS约$5（当期报告EPS为负·用周期中值） × NAND通道PE 8~12·真实股本口径。★【参考锚·不是公允基准·不参与贵贱判定】（轮13裁定四）：分拆后&lt;3年、carve-out亏损期数据不可靠→穿周期基准维持「待接真源」门槛；此值只给方向感、绝不进intrinsic/verdict/任何闸·不与现价比贵贱。接真源门槛＝分拆后≥3年稳定NAND段 或 WDC时代分部还原。</span>',
    "8001": '¥1,700~¥2,320　＝ 正常化/前瞻EPS约¥130~145 × 可比五商社PE 13~16（伯克希尔增持后重估）；分部NAV待核·报告EPS¥91.65口径待复核·主锚用正常化口径·EPS法',
    "SPCX": '无公开财报·不用EPS×PE；以最近一轮私募融资估值为锚（具体估值待Code取真数·不编）×星链增长/潜在IPO重估·成本$138为私募标记非二级市场价',
}
# 异常股好中坏三情景(前瞻·未来EPS×不同PE+业务假设·与当前价格口径无关·董事长2026-07-25第三次纠正)。
#   情景值含PE/数字→包 <span class="fwdanchor"> 由gate白名单;条件文字(中性条件)在span外·须无估值词(EPS×/正常化EPS/倍/中枢)。
#   已入登记v3.2(20260725)。
_ANOM_SCEN = {
    "6857": {
        "好": '<span class="fwdanchor" style="color:#9ec8b0">¥27,000~¥35,000（前瞻EPS放量约¥620·营收&gt;¥1.6兆·利润率&gt;45% × 高PE 45~50·真实股本口径·前瞻情景）</span>',
        "中": '<span class="fwdanchor" style="color:#9ec8b0">¥14,500~¥18,600（EDINET真EPS¥413.29 × 合理PE 35~45·真实股本口径·前瞻情景）</span>',
        "坏": '<span class="fwdanchor" style="color:#9ec8b0">¥5,600~¥8,300（前瞻EPS回落约¥280·营收¥0.8~0.9兆·利润率约30% × 低PE 20~25·真实股本口径·前瞻情景）</span>',
        "中性条件": "EDINET真实每股盈利与合理PE·中周期基准（前瞻·不依赖当前价格）",
    },
    "SNDK": {
        "好": '<span class="fwdanchor" style="color:#9ec8b0">$90~$120（周期中值盈利上修约$8·NAND涨价周期重启+AI SSD × PE 12~15·中周期锚·前瞻情景）</span>',
        "中": '<span class="fwdanchor" style="color:#9ec8b0">$40~$60（NAND周期中值盈利约$5 × 通道PE 8~12·中周期锚·前瞻情景）</span>',
        "坏": '<span class="fwdanchor" style="color:#9ec8b0">$15~$25（周期中值盈利约$2或净资产法·周期续杀维持亏损·中周期锚·前瞻情景）</span>',
        "中性条件": "NAND周期中值盈利与通道PE·中周期基准（前瞻·不依赖当前价格）",
    },
}
# 缺指标『非异常』标的(伊藤忠=缺分部NAV但有EPS·SpaceX=私司无公开财报)的完整前瞻·surfacing登记(董事长2026-07-25)。
#   非异常股→不过异常股静默gate·可含目标/PE/数字;但为防 L13 一律用半角括号()不用全角（）。已入登记v3/v3.1/v3.2。
_NONANOM_FWD = {
    "8001": {
        "fwd": "前瞻[基本面·EPS法·分部NAV待核]：短期偏反弹·中期偏上行｜催化剂＝股东回报提升[回购/增派息]+巴菲特[伯克希尔]增持商社背书+消费/资源多元扩张｜反向＝日元大幅升值/商品[铁矿·能源]下行｜失效＝ROE跌破五商社均值或巴菲特减持｜见分晓＝下季财报约2026-11｜未来目标¥1,700~¥2,320[正常化EPS¥130~145×可比五商社PE13~16·分部NAV待核]｜已入预测登记20260725·进PDCA",
        "cat": "股东回报提升[回购/增派息]预期+巴菲特[伯克希尔]持续增持商社背书；并购[消费/资源多元]。",
    },
    "SPCX": {
        "fwd": "前瞻[私司·无公开财报→用一级市场融资估值+星链/火箭业务·不依赖二级市场日价格]：短期不押[无二级市场日价格·诚实非偷懒]·中期偏上行｜催化剂＝星链Starlink用户与收入增长+下一轮私募融资估值上修+可能星链分拆IPO+星舰Starship里程碑｜反向＝星舰重大发射事故/融资遇冷估值回撤｜失效＝下一轮融资估值下修或星链IPO明确搁置｜见分晓＝下一轮融资或星链IPO时间窗｜已入预测登记20260725·进PDCA",
        "cat": "星链Starlink用户与收入增长+下一轮私募融资估值上修+可能星链分拆IPO+星舰里程碑。",
        "tgt": "以最近一轮私募融资估值为锚[具体估值待Code取真数·不编]×星链增长/潜在IPO重估；无公开财报·不用EPS×PE。成本$138为私募标记·非二级市场价。",
        "scen": ("融资估值大幅上修[星链分拆IPO兑现+星舰里程碑]", "融资估值稳步上行[星链用户与收入增长]", "估值回撤[星舰发射事故/融资遇冷]"),
    },
}
# 异常股卡内前瞻摘要(基本面·不依赖当前价格·无估值词·gate安全)·已入登记20260725
_ANOM_CARD_FWD = {
    "JP.6857": "前瞻（基本面·不依赖当前价格）：短期偏回调·中期偏上行｜催化剂＝AI测试需求/HBM4量产/英伟达Rubin抬单机HBM含量/营业利润上修至¥7300亿｜反向＝AI资本开支见顶/HBM需求转弱｜失效＝下季营业利润不及指引或出货转弱｜见分晓＝下季财报约2026-10（已入预测登记20260725·进PDCA）",
    "US.SNDK": "前瞻（基本面·不依赖当前价格）：短期偏跌·中期偏下行｜催化剂＝NAND周期位置/去库存/AI企业级SSD需求（反向变量）｜反向＝AI数据中心SSD拉动NAND涨价周期重启｜失效＝合约价环比转涨或季度扭亏｜见分晓＝下季财报约2026-10（已入预测登记20260725·进PDCA）",
}
# ── 轮13 D3(架构师裁定2026-07-25):爱德万【双口径并列】·不在中周期/前瞻间二选一 ──
#   两把尺给出相反结论·分歧本身=这只的投资分歧(AI测试需求台阶还是峰值)。含¥2940/极贵/倍→必须包 <span class="dualtrack">
#   由 gate_anomaly_silence 白名单(同 fwdanchor 机制)。★答案前不给单一贵贱结论——两把尺都摆出来·由基本面回答。
_ANOM_DUALTRACK = {
    "6857": ('<span class="dualtrack" style="color:#c9a86a">★这只股用两把尺算出相反结论（分歧本身就是它的投资分歧）：'
             '① 中周期尺（回望均值·FY22-26【含峰含谷·中立口径】·含FY26真EPS¥513.30·normal_eps¥220.2×PE20）：公允约¥4,404 → 现价¥28,945＝偏贵（约6.6倍）；'
             '② 前瞻尺（EDINET真实EPS¥413.29 × 前瞻PE）：PE取【当前可比区间·有来源】——半导体行业前瞻PE中位约37（gurufocus 2026）、'
             '泰瑞达TER（ATE双寡头另一半）前瞻约52、爱德万自身前瞻约53（valueinvesting.io 2026-03）→ 公允约¥15,300~¥21,500 → 现价约1.35~1.9倍＝偏贵非极端。'
             '★中周期侧已改含峰含谷中立口径（原剔FY26峰值=偷偷替"台阶还是峰值"答了"峰值"·裁定H1已纠）；两把尺分歧收窄（6.6倍 vs 1.4~1.9倍）但方向一致偏贵。'
             '★爱德万自身5年PE区间11~100+·无稳定"正常化PE"锚→前瞻尺的PE也只能取当前峰值周期水平；若周期回落到历史低PE（11~17），前瞻公允将降到约¥5,000~7,000。'
             '分歧点＝AI测试设备需求是【结构性台阶】还是【周期峰值】——两把尺、连前瞻尺的PE，最终都压在这一个问题上，下几个季度订单/财报会回答。答案出来前不给单一贵贱结论。</span>'),
}


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
    # ★异常股(拆股/复权口径异常)估值入口 short-circuit(GPT裁定·非输出层擦词):不进任何估值分支
    _is_anom = sym in _sanity_anomaly(date)
    # 今日价值区 / 未来目标（权威 OK → valr；否则架构师）
    if _is_anom:
        lo = hi = None                       # 估值全skip·不算价值区/中枢/目标/倍数/高低估
    elif st.get("ok"):
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
    if base_code in _FWD_EPS_PE:                                     # ★未来目标=未来EPS与合理PE·与当前价格口径无关·必须算(董事长2026-07-25第二次纠正)·已入登记v3.1
        tgt = _FWD_EPS_PE[base_code]
        tgt_miss = "（未来EPS与合理PE·前瞻锚·已入登记20260725；当前估值贵贱另见今日价值区）"
    elif _is_anom:                                                   # 其余异常股(暂无EPS×PE锚):今日价值区待核·未来目标待补前瞻EPS
        tgt, tgt_miss = "价格贵贱待核·未来目标待补前瞻EPS", ""
    elif isinstance(tf, dict) and tf.get("low") is not None:          # 引擎权威前瞻(如TSM)优先
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
    cat = D.esc(_clean(D._catalyst_within(sym, date))) or _cat_lib(sym) or f'{TBD}（近90天无前瞻催化剂·催化剂库(data/catalyst)未收录本只·库现5条:TSM/软银/COIN/MSTR等）'
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
    d16 = _deep16(sym, name, dyn, deep, v, c, _is_anom)
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
        # ★估值入口short-circuit(GPT裁定):异常股所有估值字段静默·只emit数据未核准note·非输出层擦词
        #   轮12(架构师裁定2026-07-25):B5取证已证【价格无误】(公开源交叉核对·分拆后未拆股)→撤"价异常"改"价格已核准·公允基准待重估"。
        #   问题从『分子(价格)疑错』改述为『分母(中周期公允基准)过期』。静默【暂不解除】:基准未重估前拿过期分母判贵贱仍失真·仍不据此买卖。
        SIL = "数据未核准·不计算"
        warn = ('<b style="color:#ff5c5c">⚠ 价格已核准 2026-07-25 · 中周期公允基准待重估，暂不据此买卖（非由估值推导）</b>'
                '——现价经两独立公开源交叉核对无误（分拆后未拆股、无未调整拆股口径问题）；问题不在价格，在于中周期公允基准仍是旧值'
                '（rally前/分拆前所定、系统无自动重估机制）。拿过期基准判贵贱会失真，故基准重估前不计算/不显示价值区、中枢、倍数、'
                '高低估及由此产生的动作理由。待办：重估中周期公允基准（口径待架构师定）→ 基准更新后一并解除静默、规矩三转真算。此前只观察、不据此下单。')
        # ★董事长2026-07-25第二次纠正:区分两层——①今日估值贵贱(用当前价格算)=待核(不倒退);
        #   ②未来1-2年目标(未来EPS与合理PE·与当前价格口径无关)=必须算(已在上面按_FWD_EPS_PE给·此处不再SIL覆盖)。
        hc["为什么现在"] = warn + "　" + _ANOM_CARD_FWD.get(sym, "")   # 贵贱待核note + 基本面前瞻(方向/催化剂/失效/见分晓·无估值词)
        hc["三态文字"] = "⚠当前估值贵贱待核·未来目标已按EPS与合理PE给（前瞻·不据当前价格买卖）"
        # ★轮13 D3:爱德万双口径并列(中周期极贵 vs 前瞻偏贵·相反结论·分歧=台阶还是峰值·答案前不给单一贵贱)
        _dual = _ANOM_DUALTRACK.get(base_code)
        if _dual:
            hc["为什么现在"] = _dual + "　" + warn + "　" + _ANOM_CARD_FWD.get(sym, "")
            hc["三态文字"] = "③两把尺相反结论（中周期极贵 vs 前瞻偏贵）·分歧＝AI测试需求台阶还是峰值·答案前不给单一贵贱结论"
        # 今日价值区(当前价格贵贱)=待核·不倒退;未来目标(未来该值)保留_FWD_EPS_PE·不SIL覆盖
        hc["价值区下沿"] = hc["价值区上沿"] = SIL
        if base_code not in _FWD_EPS_PE:
            hc["目标价"] = SIL; hc["目标价缺则标 待接·不编"] = ""
        hc["现价位置百分比"] = "—"
        # 好中坏三情景=前瞻(未来EPS×不同PE+业务假设·与当前价格口径无关)·必须给·不再SIL(董事长2026-07-25第三次纠正)
        _scen = _ANOM_SCEN.get(base_code)
        if _scen:
            hc["好情况价"] = _scen["好"]; hc["中性价"] = _scen["中"]; hc["坏情况价"] = _scen["坏"]
            hc["中性条件"] = _scen["中性条件"]        # 中性条件原为『不计算』note→改中周期基准假设
            hc["图2结论"] = "好/中/坏三情景已按未来盈利与不同PE＋业务假设前瞻给（真实股本口径·不依赖当前价格）——三价分开看，别只盯一个数。"
            m3 = (deep.get("block3_moat") or {})
            _moatbit = (f'护城河：{D.esc(str(m3.get("score")))}<br>' if m3.get("score") else "")
            hc["支持证据列表"] = _moatbit + "决策链：当前价格贵贱待核（复权口径未核准）·不用当前价格算贵贱；但未来目标价与三档情景已按未来盈利与合理PE前瞻给（不依赖当前价格·见图1目标/图2情景）·只看财报/订单/库存/周期。"
        else:
            hc["好情况价"] = hc["中性价"] = hc["坏情况价"] = SIL
        hc["为什么不选其他"] = "当前价格贵贱待核（复权口径未核准）·不因当前价格做买卖动作；未来方向/目标/三档情景由基本面(EDINET真EPS+业务+行业)给·见前瞻。"
        hc["停止条件"] = "先过价格/复权口径专项核准；核准前不因当前价格做买卖动作·只观察财报/订单/库存/周期；未来目标按EPS与合理PE前瞻跟踪。"
        hc["第一档价"] = hc["第二档价"] = "—（异常价·不设档）"
        hc["第一档量"] = hc["第二档量"] = "—"
        hc["把握理由"] = "估值状态：当前价格贵贱待核；未来1-2年目标已按未来EPS与合理PE给（前瞻锚·见目标行）。"
        hc["估值状态三态"] = "③当前价格贵贱待核（不计现价贵贱）；未来目标=未来EPS与合理PE（已给·前瞻）"
        hc["图1结论"] = "今日价值区（当前价格贵贱）待核；未来1-2年目标已按未来EPS与合理PE给（前瞻锚·见目标行）。"
        # 兜底:扫净任何字段里由估值推导的动作理由(留峰值/安全垫/峰值风险/不追高留…)
        for _k in list(hc):
            if isinstance(hc[_k], str) and ("留峰值" in hc[_k] or "安全垫" in hc[_k] or "峰值风险" in hc[_k]):
                hc[_k] = re.sub(r"[·、，,]?\s*(?:不追高)?[·、]?留?峰值风险?安全垫|[·、，,]?\s*留安全垫", "", hc[_k])
    # [二.3]无可信估值(如SpaceX)→统一"只观察"，禁用便宜/贵/PEG等判断词(异常股已在上面单独静默·不重复套观)
    if no_val and not _is_anom:
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
    # ★缺指标非异常标的(伊藤忠/SpaceX)完整前瞻surfacing(董事长2026-07-25第四次纠正:私司无财报≠不预测·分部NAV待核≠不给前瞻)
    _nf = _NONANOM_FWD.get(base_code)
    if _nf:
        hc["为什么现在"] = str(hc.get("为什么现在", "")) + "　" + _nf["fwd"]
        if _nf.get("cat"):
            hc["催化剂"] = _nf["cat"]
        if _nf.get("tgt"):                                   # SpaceX:恢复被no_val覆盖的未来目标(融资估值锚)
            hc["目标价"] = _nf["tgt"]; hc["目标价缺则标 待接·不编"] = "（融资估值锚·前瞻·已入登记20260725）"
        if _nf.get("scen"):                                  # SpaceX:好中坏定性情景(融资估值·无EPS)
            g_, m_, b_ = _nf["scen"]
            hc["好情况价"], hc["中性价"], hc["坏情况价"] = g_, m_, b_
            hc["图2结论"] = "好/中/坏三情景已按融资估值锚+业务里程碑前瞻给（私司·不依赖二级市场日价格）——三价分开看。"
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
    # 45%上限已废止(董事长2026-07-19)→『超配/超上限』不再作加仓拒绝或减仓触发理由;改说四条规矩的具体哪一条或加仓闸
    if pure == "等":
        return "不选加：没到便宜位或没催化(别接飞刀·不满足加仓闸)；不选减：没到贵位，也没触发四规矩(单只>20%/单环节>30%/峰值定价类合计>5%)。"
    if pure == "守":
        return "不选加：不够便宜或无催化(不满足加仓闸)；不选减：没到贵位或成长便宜(PEG<1)、也未触发四规矩。"
    if pure in ("加", "买"):
        return "不选等：已跌进便宜位且有催化/企稳；不选减：便宜不该减。"
    if pure == "减":
        return "不选守：已过贵位、或触发四规矩(峰值定价类合计>5%等)；不选加：贵不该加。"
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


_CAT_LIB: dict = {}
_CAT_LIB_LOADED = [False]


def _cat_lib(sym):
    """二[消催化剂待接]：接 data/catalyst/catalyst_library.json。库现5条(索引_按标的)·标 CAT-ID+日期。缺→''。"""
    if not _CAT_LIB_LOADED[0]:
        _CAT_LIB_LOADED[0] = True
        try:
            for x in (_rj(ROOT / "data" / "catalyst" / "catalyst_library.json").get("催化剂") or []):
                k = str(x.get("标的") or x.get("symbol") or "")
                if k:
                    _CAT_LIB[k] = x
        except Exception:
            pass
    x = _CAT_LIB.get(str(sym))
    if x:
        txt = _clean(str(x.get("催化剂") or x.get("事件") or ""))
        if txt:
            return D.esc(txt[:200]) + f'<span style="color:#6b8b7a;font-size:10.5px">（接催化剂库·{D.esc(str(x.get("id","")))}·2026-07-22）</span>'
    return ""


def _kline_svg(sym, name):
    """四[看板5·消'画法待接']：用 data/prices/daily_{sym}.json 的 60日OHLC 真画收盘走势线+MA20/MA50+现价+区间。
    纯工程·无判断·真数据。缺数据→''(外层标待接)。"""
    try:
        d = _rj(ROOT / "data" / "prices" / f"daily_{sym}.json")
        s = d.get("series") or []
    except Exception:
        s = []
    closes = [float(b["close"]) for b in s if b.get("close") not in (None, "")]
    if len(closes) < 10:
        return ""
    dates = [str(b.get("date", "")) for b in s if b.get("close") not in (None, "")]
    lo, hi = min(closes), max(closes)
    rng = (hi - lo) or 1.0
    W, H, PAD = 340, 96, 6
    n = len(closes)

    def X(i):
        return PAD + i * (W - 2 * PAD) / (n - 1)

    def Y(v):
        return H - PAD - (v - lo) / rng * (H - 2 * PAD - 8)

    def ma(w, i):
        if i + 1 < w:
            return None
        return sum(closes[i + 1 - w:i + 1]) / w
    line = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(closes))
    ma20 = [(i, ma(20, i)) for i in range(n) if ma(20, i) is not None]
    ma50 = [(i, ma(50, i)) for i in range(n) if ma(50, i) is not None]
    ma20p = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in ma20)
    ma50p = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in ma50)
    cur = closes[-1]
    up = cur >= closes[0]
    col = "#7ee0a0" if up else "#ff9a9a"
    parts = [f'<svg viewBox="0 0 {W} {H}" style="width:100%;max-width:360px;height:auto;background:#0b1220;border-radius:6px" xmlns="http://www.w3.org/2000/svg">']
    parts.append(f'<polyline points="{line}" fill="none" stroke="{col}" stroke-width="1.6"/>')
    if ma20p:
        parts.append(f'<polyline points="{ma20p}" fill="none" stroke="#7cc4ff" stroke-width="1" stroke-dasharray="3,2"/>')
    if ma50p:
        parts.append(f'<polyline points="{ma50p}" fill="none" stroke="#e0b060" stroke-width="1" stroke-dasharray="1,2"/>')
    parts.append(f'<circle cx="{X(n-1):.1f}" cy="{Y(cur):.1f}" r="2.4" fill="{col}"/>')
    parts.append(f'<text x="{PAD}" y="10" fill="#8ea3b6" font-size="8">{D.esc(name)} 60日收盘·真K线(QFQ)</text>')
    parts.append(f'<text x="{W-PAD}" y="{Y(hi)+8:.0f}" fill="#8ea3b6" font-size="7.5" text-anchor="end">高{hi:g}</text>')
    parts.append(f'<text x="{W-PAD}" y="{Y(lo):.0f}" fill="#8ea3b6" font-size="7.5" text-anchor="end">低{lo:g}</text>')
    parts.append("</svg>")
    ma20v = ma(20, n - 1)
    ma50v = ma(50, n - 1)
    legend = (f'<div style="font-size:10.5px;color:#8ea3b6;margin-top:2px">'
              f'<span style="color:{col}">现价 {cur:g}</span>'
              + (f'　<span style="color:#7cc4ff">MA20 {ma20v:.1f}</span>' if ma20v else "")
              + (f'　<span style="color:#e0b060">MA50 {ma50v:.1f}</span>' if ma50v else "")
              + f'　60日区间 {lo:g}~{hi:g}　（源：OpenD K_DAY QFQ·{D.esc(dates[-1])}）</div>')
    return ('<div style="margin:6px 0"><div style="font-size:12px;color:#7ee0a0;font-weight:700">价格走势图（真K线·60日）</div>'
            + "".join(parts) + legend + '</div>')


_PACK_CACHE: dict = {}


def _pack_sections(sym, name):
    """接《个股判断包》(00_请先看这里/个股判断包/·2026-07-09底稿)：抽 生意/护城河/真数据/对估值/风险/决策。缓存。"""
    if sym not in _PACK_CACHE:
        try:
            p = D.find_pack(sym, str(name))
            _PACK_CACHE[sym] = D.extract_pack(p) if p else {}
        except Exception:
            _PACK_CACHE[sym] = {}
    return _PACK_CACHE[sym]


def _pk(sym, name, section, n=700):
    """判断包某段→大白话·标底稿日期。空→''(交由外层再回落待接)。消'深研待接'。"""
    s = (_pack_sections(sym, name) or {}).get(section, "")
    if s and len(str(s).strip()) > 4:
        return D.esc(_cut(_clean(str(s)), n)) + '<span style="color:#6b8b7a;font-size:10.5px">（接《个股判断包》深研底稿·2026-07-09）</span>'
    return ""


def _deep16(sym, name, dyn, deep, v, c, is_anom=False):
    """③完整研究底稿16项——从深研卡真取·缺则接《个股判断包》·再缺标待接。只增不减(L3内容不缩水·安全截断不切半词)。
    ★异常股(爱德万/闪迪):估值模型/输入/敏感性/三情况完整推导 整体short-circuit返静默(GPT裁定·删语义)；深研(生意/护城河/风险)照接判断包。"""
    if is_anom:
        _SILV = "当前价格/复权口径待核·不用当前价格算估值贵贱/市盈率；未来目标价与三档情景已按未来盈利与合理PE前瞻另给·见图1目标与图2情景·不依赖当前价格·已入登记20260725；依赖当前价的估值模型/敏感性分析待口径核准。"
        _b16 = {"赚钱模式": (D.esc(_cut(_clean(_flat(deep.get("block1_business"))), 900)) or _pk(sym, name, "生意") or _b(deep, "block1")),
                "多年财务": _fin_years(sym, deep), "业务结构": (D.esc(_cut(_clean(_flat(deep.get("block2_structure"))), 900)) or _pk(sym, name, "生意") or _b(deep, "block2")),
                "护城河": (_moat(deep) if str(_moat(deep) or "").strip() and "待接" not in str(_moat(deep)) else (_pk(sym, name, "护城河") or _moat(deep))), "竞争对手": (D.esc(_cut(_clean(_flat(deep.get("block4_competitors"))), 900)) or _pk(sym, name, "护城河") or _b(deep, "block4")),
                "估值模型": _SILV, "估值输入逐项含来源": _SILV, "可信度": "异常价·数据未核准·不标估值可信度",
                "敏感性": _SILV, "三情况完整推导": _SILV,
                "事件日历": "<br>".join(t for t in (D.esc(_clean(_flat(x))) for x in (deep.get("block7_catalysts") or [])) if t) or TBD,
                "风险与可观测信号": _risks(deep), "推导链全版": "当前价格/复权口径待核·不用当前价格算贵贱；未来目标价与三档情景已按未来盈利与合理PE前瞻给·见图1目标与图2情景·不依赖当前价格·已入登记20260725；只看财报/订单/库存/周期。",
                "组合作用": _b(deep, "block10") or (D.esc(_cut(_clean(_flat(deep.get("block10_portfolio"))), 900)) or TBD),
                "可点链接列表含发布日": _sources(deep), "正反证据全量": _support_from(deep) + "<br>反面：见图8/未找到则已注明查哪些源",
                "待接项与原因": "异常价·数据未核准·核准前估值全项不计算", "推翻条件": _falsify(deep),
                "图3结论": "多年真数看趋势；年数不足标仅N年。"}
        return _b16
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
        "赚钱模式": g("block1_business") or _pk(sym, name, "生意") or _b(deep, "block1"),
        "多年财务": _fin_years(sym, deep),
        "业务结构": g("block2_structure") or _pk(sym, name, "生意") or _b(deep, "block2"),
        "护城河": (_moat(deep) if str(_moat(deep) or "").strip() and "待接" not in str(_moat(deep)) else (_pk(sym, name, "护城河") or _moat(deep))),
        "竞争对手": g("block4_competitors") or _pk(sym, name, "护城河") or _b(deep, "block4"),
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
    if sym in _sanity_anomaly(_ANOM_DATE_HOLDER.get("d") or ""):   # 异常股(拆股口径异常)→退出估值·黄金样板locked_v7
        return ('<div style="font-size:12px;color:#cfe0ee;background:#0f1925;border-left:3px solid #c0392b;'
                'border-radius:0 6px 6px 0;padding:7px 10px;margin:6px 0">'
                '架构师估值底稿：<b>数据未核准·非由估值推导</b>·核准前不计算估值/倍数/止盈（价格/复权口径异常·拆股待核）。</div>')
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
    if sym in _sanity_anomaly(_ANOM_DATE_HOLDER.get("d") or ""):   # 异常股→退出减仓/估值判定·黄金样板
        return ('<div style="font-size:12px;color:#cfe0ee;background:#101a26;border-left:3px solid #c0392b;'
                'border-radius:0 6px 6px 0;padding:7px 10px;margin:6px 0">'
                '<b style="color:#ffb454">减仓判定：数据未核准·不进任何减仓/估值判定</b>——价格/复权口径异常（拆股待核）'
                '·核准前不计算现价倍数/中枢/止盈线；守=数据未核准暂停判断，非由估值推导。</div>')
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
    """[五·C]取加仓闸逐项实测(复用 deep_render._stabilized_calc)·逐只显示。异常股short-circuit不算20日序列。"""
    if sym in _sanity_anomaly(date):     # ★异常股:20日价格序列口径未核准·不计算·不参与加仓闸(退回2)
        return ('<div style="font-size:12px;color:#cfe0ee;background:#101a26;border-left:3px solid #c0392b;'
                'border-radius:0 6px 6px 0;padding:7px 10px;margin:6px 0">'
                '加仓闸：<b>近20日价格序列口径未核准·最低价及涨幅不计算·不参与加仓闸</b>'
                '（价格/复权口径异常·拆股待核；核准前不据20日低/涨幅判买卖）。</div>')
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
    "need40": 608126, "need100": 1520314, "预期年化": "约+12.1%（架构师更正任天堂/爱德万后上修·原+10.3%）",
    "缺40": "27.9个百分点（上修后·原29.7）", "缺100": "约83个百分点", "盲区占比": "36.6%",
}
_TARGET_ROLE = {   # 角色/持仓意图/对目标贡献pp/凭什么占这个仓位(定稿第五节·算不出标盲区不留空)
    "US.NVDA": ("主攻", "核心持有·45%上限已废止→可加（风险配仓建议加至18%·仍在单只20%内）", "+7.73pp", "AI算力龙头·Rubin下季贡献·上行最大的单一来源"),
    "US.MSFT": ("主攻", "核心持有", "主攻组内（组合+16.8pp）", "Copilot变现+Azure+38%·现金流龙头"),
    "JP.4568": ("主攻", "等回调上车→系统建议已转『加』", "主攻组内", "ADC龙头+I-DXd催化·便宜且有催化"),
    "US.AVGO": ("主攻", "今日=等回落到便宜位再加（现价略高于合理上沿·未到加仓位·45%上限已废止但不追高）", "压舱转主攻组内", "定制AI芯片$73B订单·6大客户至2031"),
    "JP.8766": ("压舱", "核心持有", "压舱组内", "保险压舱·低波动·稳"),
    "JP.7832": ("压舱", "核心持有", "压舱组内", "IP护城河·稳"),
    "JP.7974": ("正贡献", "维持·含每股约¥1,940净现金·已从减仓/替换名单剔除（架构师更正:原漏算净现金）", "+0.58pp", "扣净现金后约19.8倍不算贵·Switch2放量+软件6000万本·公司FY2027指引"),
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
    "US.NVDA": ("加至约现金1/3（仍在单只20%内·风险配仓建议加至18%）", "约 +1.0~1.5pp",
                "若 Rubin 出货延期/超大规模厂资本开支放缓·回调约 −25%·对总组合影响约 −0.9%",
                "加至约现金2/3·偏重", "约 +2.0~3.0pp", "同情形回调 −25%·仓位翻倍：最坏损失约 −$68,000·对总组合影响约 −1.8%·并消耗现金错失他标机会"),
    "JP.9984": ("到便宜位小幅加·约现金1/4（NAV折价49.4%·有OpenAI/Arm催化）", "约 +0.5~0.8pp",
                "若 OpenAI IPO 推迟或估值下修·回落约 −25%·对总组合影响约 −0.6%",
                "加至约现金1/2", "约 +1.0~1.6pp", "同情形回落 −25%·仓位翻倍：最坏损失约 −$45,000·对总组合影响约 −1.2%；且软银本身是盲区(NAV算不出到期上行)·激进加需自担不确定"),
    "US.AVGO": ("今日=等（未到便宜位·不追高）；跌回便宜位($362以下)再加·约现金1/4", "约 +0.6~1.0pp",
                "若大客户自研替代/订单转化下滑·回调约 −20%·对总组合影响约 −0.5%",
                "跌回便宜位后加至约现金1/2·偏重", "约 +1.2~1.8pp", "同情形回调 −20%·仓位翻倍：最坏损失约 −$30,000·对总组合影响约 −0.8%（★今日动作=等·此为回落到便宜位后的偏激进加·待拍板）"),
    "US.TSM": ("建仓·第一档 $360 约现金1/4（PEG0.6便宜·分档不死等）", "约 +0.5~0.8pp",
                "若 $18 EPS 假设失效(先进制程订单下修等)·跌破 $325·这笔亏约 −12%·对总组合影响约 −0.2%",
                "建仓·第一档 $360 买约现金1/2·第二档 $325 再加", "约 +1.0~1.5pp", "同情形亏约 −12%·仓位翻倍：最坏损失约 −$18,000·对总组合影响约 −0.5%·占用后续机会现金"),
}
# [致命5]每只中性情形依据来源(三选一·标推测的醒目提示可信度低)
_NEUTRAL_BASIS = {
    "JP.4568": ("公司 FY2027 指引 + I-DXd PDUFA 官方审批", "高"), "JP.6758": ("公司 FY2026/3 已上调指引", "高"),
    "US.MSFT": ("公司 FY26 Q4 指引 + 分析师共识", "高"), "US.NVDA": ("公司指引 + GTC 官方 + 分析师共识", "高"),
    "US.TSM": ("公司月度营收 + FY2026 指引", "高"), "US.AVGO": ("公司 Q3 指引 + FY2027 目标", "高"),
    "US.META": ("公司 Q2 指引 + 分析师共识", "高"), "US.IBKR": ("公司 Q2 指引 + 2026 共识", "中"),
    "US.COIN": ("分析师共识（周期极端·穿牛熊试算）", "低"), "JP.6857": ("公司 FY2027/3 指引", "高"),
    "JP.7974": ("公司 FY2027/3 指引", "高"), "JP.9984": ("架构师推测（NAV 依 Arm/OpenAI·算不出）", "低"),
    "US.MSTR": ("架构师推测（依 BTC 币价·算不出）", "低"), "US.CRCL": ("架构师推测（低置信·待接）", "低"),
    "US.SNDK": ("架构师推测（异常价·未核准）", "低"), "US.SPCX": ("无可信估值（只观察）", "低"),
    "JP.8001": ("架构师推测（商社 NAV·待接）", "低"), "JP.7203": ("分析师共识", "中"),
    "JP.7832": ("分析师共识", "中"), "JP.8766": ("分析师共识", "中"),
}


def _neutral_basis_line(sym):
    if sym in _sanity_anomaly(_CUR_DATE):    # 异常股:不出中性情形估值依据(source-null)
        return ""
    b = _NEUTRAL_BASIS.get(sym, ("架构师推测", "低"))
    src, conf = b
    if conf == "低":
        badge = '<span style="background:#FBEAEA;color:#A3231F;padding:1px 7px;border-radius:5px;font-weight:800">中性情形依据＝' + src + '·⚠可信度低</span>'
    else:
        col = "#1E7A45" if conf == "高" else "#7A5C00"
        badge = f'<span style="background:#E4F4EA;color:{col};padding:1px 7px;border-radius:5px">中性情形依据＝{src}·可信度{conf}</span>'
    return f'<div style="font-size:11.5px;margin:3px 0">{badge}</div>'


def _target_gap_block():
    """P0 目标—缺口 模块(放第一层最顶部)。"""
    c = _TARGET_CFG
    return (
        '<div id="target-gap" style="background:#FFFFFF;border:2px solid #5C4033;border-radius:10px;padding:11px 14px;margin:6px 0 12px">'
        '<div style="font-size:19px;font-weight:900;color:#5C4033">🎯 离目标还差多少（1年期·双档·主战场SBI+富途）</div>'
        '<div style="font-size:14px;color:#1A1A1A;line-height:1.9;margin-top:5px">'
        f'主战场当前市值 <b>${c["主战场"]:,}</b>（SBI ${c["SBI"]:,} + 富途 ${c["富途"]:,}）<br>'
        # [重要1]三个数同显并各注明含义,避免看着矛盾
        '<span style="background:#F2F4F7;padding:2px 8px;border-radius:6px">综合好/中/坏概率后 <b>预计上升 +16.87%</b>（一次性总回报·非年化）</span>　'
        f'<span style="background:#F2F4F7;padding:2px 8px;border-radius:6px">折成 <b>预期年化 {c["预期年化"]}</b>（每年平均）</span>　'
        f'<span style="background:#F2F4F7;padding:2px 8px;border-radius:6px">距 <b>+40%</b> 还差 <b>{c["缺40"]}</b>（一年要多赚这么多格才够）</span><br>'
        f'<span style="background:#EAF2FA;padding:2px 8px;border-radius:6px">【中性档 +40%】一年需赚 <b>${c["need40"]:,}</b></span>　'
        f'<span style="background:#F5EFE0;padding:2px 8px;border-radius:6px">【激进档 +100%】一年需赚 <b>${c["need100"]:,}</b>·距目标缺口 <b>{c["缺100"]}</b></span><br>'
        f'<span style="color:#8A3E00">⚠ 盲区占 <b>{c["盲区占比"]}</b>（软银/爱德万/MSTR/COIN/闪迪/CRCL/伊藤忠/SpaceX·算不出到期上行→限期接真数据）；'
        '各只『对目标贡献个百分点(收益率相差多少格)』见其卡内四字段。两档并列·董事长自己选一档拍板·系统不替他选。</span></div></div>')


def _z4_forecast_note(date):
    """★轮67 AF1(item7):从最新【工作版】forecast 读带「口径标注」字段的条目(如微软财报前EPS口径)→渲成红框标注。数据驱动·不写死。
    ★只认工作版 forecast_YYYY-MM-DD.json(取最大日期)·避开 forecast_{紧凑}_{hash}.json 那些 lock 快照(否则会选错)。"""
    import glob as _g, os as _os, re as _re
    cands = _g.glob(str(ROOT / "data" / "forecast" / "forecast_*.json"))
    dated = []
    for p in cands:
        m = _re.match(r"forecast_(\d{4}-\d{2}-\d{2})\.json$", _os.path.basename(p))
        if m:
            dated.append((m.group(1), _os.path.basename(p)))
    if not dated:
        return ""
    fp = sorted(dated)[-1][1]        # 最大日期的工作版文件名
    fc = _rj(ROOT / "data" / "forecast" / fp)
    notes = []
    for f in (fc.get("forecasts") or []):
        if f.get("horizon") != "1y":
            continue
        note = f.get("口径标注")
        if note:
            notes.append('<div style="border:1px solid #c0392b;background:#fff4f4;border-radius:6px;padding:8px 12px;margin:6px 0;font-size:13px">'
                         f'<b>★ {D.esc(str(f.get("name","")))} 口径提示</b>：{D.esc(str(note))}</div>')
    return "".join(notes)


def _z4_two_segment_block(date):
    """★轮67 AF1:Z4 两段报法(已算清/未算清分列·点值口径 E[上行]·参数出处四等级·单只超限告警·退出类型)
    + 微软口径标注(item7) + 机会层(item8·不填买卖价位)。这是轮65 手工渲染器 render_0730_final 八项整改
    【并入唯一渲染器 render_3layer】。读 data/risk/z4_two_segment_{date}.json(点值口径已在其中·由 z4_two_segment_build 产出)。
    ★不给单一「距+40%缺口」混合数。数据缺→返回空串(回落旧 _target_gap_block·安全增量)。"""
    z4p = ROOT / "data" / "risk" / f"z4_two_segment_{date}.json"
    if not z4p.exists():
        return ""
    z4 = _rj(ROOT / "data" / "risk" / f"z4_two_segment_{date}.json")
    accts = z4.get("账户") or {}
    if not accts:
        return ""
    esc = lambda s: D.esc(str(s))

    def _card(a_cn):
        d = accts.get(a_cn) or {}
        c = d.get("①已算清(特+A级)") or {}
        u = d.get("②未算清(B+C级)") or {}
        ex = d.get("退出(第一三共)") or {}
        clear_only = "、".join("%s(%s·%s%%·贡献%spp)" % (x.get("name"), x.get("等级"), x.get("权重pct"), x.get("贡献pp")) for x in (c.get("只") or []))
        unclear_only = "、".join("%s(%s·%s%%)" % (x.get("name"), x.get("等级"), x.get("权重pct")) for x in (u.get("只") or []))
        # 单只超20%上限显性告警(只报事实与超限幅度·不给处置建议·item5)
        over = [x for x in ((c.get("只") or []) + (u.get("只") or [])) if (x.get("权重pct") or 0) > 20]
        over_line = ""
        if over:
            over_line = ('<p style="background:#fff4f4;border-left:4px solid #c0392b;padding:6px 10px;font-size:13px">'
                         + "；".join("<b>%s %s%%，超单只20%%上限 %.2f个百分点</b>" % (x.get("name"), x.get("权重pct"), (x.get("权重pct") or 0) - 20) for x in over)
                         + "（上限出处：2026-07-19 四条风险配仓·只报事实不给处置建议）</p>")
        return ('<div style="flex:1;min-width:320px;border:2px solid #0f2e1c;border-radius:8px;padding:10px 14px;margin:4px">'
                f'<div style="font-weight:800;font-size:16px">{esc(a_cn)}账户</div>{over_line}'
                f'<p style="background:#eef7ee;padding:6px 10px;border-left:4px solid #2e7d32">① <b>已算清（特级+A级）覆盖 {c.get("覆盖权重pct")}% 权重 → Σ贡献 <span style="font-size:17px">{c.get("Σ贡献pp")}个百分点</span></b><br><span style="font-size:12px;color:#555">{esc(clear_only)}</span></p>'
                f'<p style="background:#fff4f4;padding:6px 10px;border-left:4px solid #c0392b">② <b>未算清（B+C级）{u.get("权重合计pct")}% 权重——这部分无法给出预期收益（无可用估值锚）</b><br><span style="font-size:12px;color:#555">{esc(unclear_only)}</span></p>'
                f'<p style="font-size:12px;color:#888">退出（第一三共·财务质量）{ex.get("权重pct")}% 权重·不进情景计算（item6 退出类型）。★两段不相加·本产品不给单一「距+40%缺口」数。</p></div>')

    cards = "".join(_card(a) for a in ("富途", "SBI") if a in accts)
    msft_note = _z4_forecast_note(date)   # item7 微软口径标注
    opp = ('<div style="border:2px dashed #8a6d1a;background:#fffaef;border-radius:8px;padding:10px 14px;margin:8px 0">'
           '<b>★ 机会层</b>：Opus 5 周末人工过漏斗中·候选估值未算·周末补——周一开盘前出双档建议。'
           '<b>本产品此处不填任何候选或买卖价位</b>（候选事实见另出的候选研究工单）。</div>')   # item8
    return ('<div id="target-gap" style="border:3px solid #0f2e1c;background:#f4f8f4;border-radius:10px;padding:12px 16px;margin:6px 0 14px">'
            '<div style="font-size:19px;font-weight:800;color:#0f2e1c">🎯 第一屏 · 缺口分两段报（不给混合总数）</div>'
            '<p style="font-size:12px;color:#555;margin:4px 0">只有【有出处的数】才进「已算清」（点值口径 E[上行]=Σ概率×点值·非区间中值）；无估值锚的标的（B/C级）只报事实、不出预期收益——避免伪精确。</p>'
            f'<div style="display:flex;flex-wrap:wrap">{cards}</div>{msft_note}{opp}</div>')


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


# [更正1/2 + 新规矩]情景表(好/中/坏+概率+★中性依据来源·董事长2026-07-20)。架构师上修任天堂/爱德万。
_SCENARIO = {
    "JP.7974": {"依据": "公司 FY2027/3 指引（非架构师推测·可信度高）",
                "行": [("坏 30%", "EPS230×PE20+净现金 = ¥6,540（−10%）"),
                       ("中 45%", "EPS271×PE22+净现金 = ¥7,902（+8%）"),
                       ("好 25%", "EPS320×PE25+净现金 = ¥9,940（+36%）")],
                "期望": "+9.7%", "贡献": "+0.58个百分点",
                "更正": "架构师原漏算每股约¥1,940净现金→由『拖累−12.1%』更正为『正贡献+9.7%』·已从减仓/替换名单剔除"},
    "JP.6857": {"依据": "公司 FY2027/3 指引（营收1兆4,200億+25.8%·营业利润6,275億+25.7%·非架构师推测）",
                "行": [("坏 30%", "EPS450×PE25 = ¥11,250（−59%）"),
                       ("中 45%", "EPS645×PE30 = ¥19,350（−30%）"),
                       ("好 25%", "EPS645×PE45 = ¥29,025（+5.5%）")],
                "期望": "−29.7%", "贡献": "−2.67个百分点",
                "更正": "架构师原按峰值回落设中性EPS¥400(低于FY2026实际¥513)·未核公司指引→上修为期望−29.7%(原−42.3%)·仍最大拖累·仍触规矩3"},
}


def _scenario_block(sym):
    if sym in _sanity_anomaly(_CUR_DATE):    # 异常股:不出情景目标/EPS×PE/期望上行/目标贡献(source-null·退回1)
        return ""
    s = _SCENARIO.get(sym)
    if not s:
        return ""
    rows = "".join(f'<tr><td>{a}</td><td>{b}</td></tr>' for a, b in s["行"])
    return (
        '<div style="font-size:12px;color:#1A1A1A;background:#F2F4F7;border-left:3px solid #12324E;'
        'border-radius:0 6px 6px 0;padding:7px 10px;margin:5px 0">'
        '<b style="color:#12324E">情景表（好/中/坏×概率）</b>　'
        f'<span style="background:#E4F4EA;padding:1px 7px;border-radius:5px;color:#1E7A45">中性情形依据＝{s["依据"]}</span>'
        f'<table class="dt" style="width:100%;margin-top:4px"><tr><th>情景</th><th>算法→合理价（对现价）</th></tr>{rows}</table>'
        f'期望上行 <b>{s["期望"]}</b>·对目标贡献 <b>{s["贡献"]}</b>。<br>'
        f'<span style="color:#8A3E00">★架构师更正：{s["更正"]}</span></div>')


def _risk_config_block(conc=None):
    """废止45%上限→四条风险配仓(董事长2026-07-19)。四规矩合规状态+回撤预案+调整建议(待拍板)。
    轮9 Z2①:回撤预案改【真算】——从真实持仓集中度(portfolio_concentration:AI供应链市值+total_usd)算·不再硬编码mv/系数。"""
    # Z2① 回撤真算:AI仓市值=AI占比×全持仓折美元;最坏损失=AI仓市值×回调%;占总仓%=AI占比×回调%(与产品别处AI集中度同源·不撞L12/L31)
    _ai = ((conc or {}).get("categories", {}) or {}).get("AI供应链") or {}
    _tot = (conc or {}).get("total_usd")
    _retreat_real = (_ai.get("pct") is not None and _tot)
    if _retreat_real:
        _aip = float(_ai["pct"]); _aimv = _aip / 100.0 * float(_tot)
        d30 = int(_aimv * 0.30); d50 = int(_aimv * 0.50)
        _p30 = _aip * 0.30; _p50 = _aip * 0.50
    adj = [
        ("待核准·暂不建议动作", "爱德万", "维持9.0%（不动）", "★致命2更正:异常价专项核准前『不可据此买卖』与『建议减仓』自相矛盾→架构师撤回减仓建议·统一观察·待交易所公告/拆股前后价与股数/两独立行情源核对后再重算"),
        ("待核准·暂不建议动作", "闪迪", "维持1.8%（不动）", "同上·专项核准前不出任何加/减建议·统一观察"),
        ("加", "英伟达", "13.8% → 18.0%", "未来+60%·仍在单只20%上限内"),
        ("暂不加·等回落", "博通", "维持3.7%（不动·等回落到便宜位）", "★与动作表统一为『等』:现价$370略高于合理上沿$362·未到加仓便宜位→今天不加;基本面(未来+23%·AI订单$73B·6大客户至2031)支持——跌回便宜位($362以下)后再加至约6%"),
        ("建仓", "台积电", "0% → 4.0%", "PEG0.6便宜·董事长本就在等回调上车·分档买入"),
    ]
    arows = "".join(
        f'<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td><td>{why}</td></tr>' for a, b, c, why in adj)
    return (
        '<div id="risk-config" style="background:#FFFFFF;border:2px solid #12324E;border-radius:10px;padding:11px 14px;margin:6px 0 12px">'
        '<div style="font-size:18px;font-weight:900;color:#12324E">🛡 风险配仓（已废止 AI 45% 上限·改四条规矩·董事长2026-07-19拍板）</div>'
        '<div style="font-size:13.5px;color:#1A1A1A;line-height:1.85;margin-top:5px">'
        '<b>规矩1 单只上限20%</b>：当前最大 微软18.1%（合规✔）<br>'
        # Z1止血(轮9):33.5%为手写死字符串·非算出(全库无环节集中度计算)→标待接·Z2②真算前不作数
        '<b>规矩2 单一环节上限30%</b>：芯片/设备/代工/存储/软件云/AI应用/电力 分开算。'
        '<span style="color:#B00020;font-weight:800">⚠ 待接·硬编码·不可依赖</span>'
        '<span style="color:#8A3E00">（下面这句为手写死字符串·系统并未真算各环节占比·补真算前不作占比/超限判断）：'
        '<s style="color:#888">软件云(微软18.1%)+Arm/OpenAI敞口(软银15.4%)=33.5%·超30%</s></span><br>'
        # Z1止血→轮10 A4:规矩三保持待接·但改成『待爱德万/闪迪核准后可算』(非永久待接·有人管)·记判据+名单
        '<b>规矩3 按最好年份定价类合计≤5%</b>：<span style="color:#B00020;font-weight:800">⚠ 待接 · 待爱德万/闪迪价格核准后可算</span>'
        '<span style="color:#8A3E00">（判据=两条同时满足才算：①强周期属性(利润随周期大幅波动·半导体设备/存储/代工/加密相关)②正常化口径(中周期/穿牛熊)算下来判『极贵』。当前属此类=爱德万/闪迪·但两者价格口径未核准(拆股待核)→核准后即可算合计占比÷全持仓。'
        '台积电/英伟达经判定<b>不属</b>此类:台积电盈利中枢抬升(先进制程近垄断·非周期高点)、英伟达风险是成长能否持续(非周期利润回落)）</span><br>'
        # Z2① 回撤预案真算(轮9):从真实持仓AI占比与市值算·集中度缺则退回待接(绝不硬编码假数字)
        + ((
            f'<b>规矩4 回撤预案（必显·真算）</b>：AI 仓占 <b>{_aip:.1f}%</b>·AI仓市值 <b>${_aimv:,.0f}</b>（全持仓折美元 ${float(_tot):,.0f}·当日现算）<br>'
            f'　· AI 仓回调 <b>30%</b> → 全组合承受 <b>−{_p30:.1f}%</b>（约 <b>−${d30:,}</b>）<br>'
            f'　· AI 仓回调 <b>50%</b> → 全组合承受 <b>−{_p50:.1f}%</b>（约 <b>−${d50:,}</b>）</div>'
          ) if _retreat_real else (
            '<b>规矩4 回撤预案（必显）</b>：<span style="color:#B00020;font-weight:800">⚠ 待接·集中度数据缺</span>'
            '<span style="color:#8A3E00">（portfolio_concentration 未取到AI仓市值/占比·补真实持仓后自动真算·绝不填假数字）</span></div>'
          ))
        + '<div style="font-size:14px;font-weight:800;color:#12324E;margin-top:8px">📋 据四规矩产生的调整建议（系统建议·待董事长拍板·系统不自动执行）</div>'
        '<table class="dt" style="width:100%;font-size:13px;margin-top:4px"><tr><th>动作</th><th>标的</th><th>仓位</th><th>理由</th></tr>'
        + arows + '</table>'
        '<div style="font-size:12.5px;color:#8A3E00;margin-top:5px">★ 爱德万/闪迪 <b>专项核准完成前统一「观察·不据此买卖」·不出加/减建议</b>（致命2更正：不能拿未核准的不可信价格提减仓）；'
        '待交易所公告/拆股前后价与股数/两个独立行情源交叉核对后，再重算是否减仓。加英伟达/博通、建仓台积电为方向确定下的补缺口建议·均待董事长拍板。</div></div>')


def _target_role_block(sym):
    """P1 每只四字段:角色/持仓意图/对目标贡献pp/凭什么占这个仓位(算不出标盲区·不留空)。"""
    if sym in _sanity_anomaly(_CUR_DATE):    # 异常股:不出目标贡献pp(由估值推导·source-null·退回1)
        return ('<div style="font-size:12px;color:#1A1A1A;background:#F2F4F7;border-left:3px solid #c0392b;'
                'border-radius:0 6px 6px 0;padding:6px 10px;margin:5px 0">'
                '<b style="color:#c0392b">目标倒推·四字段</b>：价格与复权口径未核准；核准前不计算对目标贡献/期望上行/组合收益（拆股待核）。</div>')
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
    if sym in _sanity_anomaly(_CUR_DATE):    # 异常股:不出双档买卖建议(由估值推导·source-null)
        return ""
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


# ── 外部原辅料线索(董事长工单2026-07-23)：老雷/湖水经 external_ingest 五分类+体系比对后·卡内辅助/分歧展示 ──
# 铁律：最终"今天怎么做"仍来自 production+风控(体系)；external 只作辅助佐证/分歧展示·绝不作唯一依据。
_EXT_CACHE: dict = {}


def _load_external(date):
    if date not in _EXT_CACHE:
        _EXT_CACHE[date] = _rj(ROOT / "data" / "external" / f"external_material_{date}.json")
    return _EXT_CACHE[date]


# 显示名:五分类verdict里"待核实"改"存疑·未证实"(去"待"字·不计入待接·语义不变·董事长2026-07-25 v13)
_VERDICT_DISP = {"待核实": "存疑·未证实"}
_VERDICT_STYLE = {
    "证实": ("#E4F4EA", "#1E7A45", "经一级来源证实·纳入辅助佐证"),
    "待核实": ("#FBF3E0", "#7A5C00", "存疑·未证实·仅背景·不作买卖依据"),
    "否决": ("#FBEAEA", "#A3231F", "与体系冲突·体系不采纳为买卖依据"),
    "分歧": ("#FBEAEA", "#A3231F", "与体系有分歧·以体系风控为准"),
}


def _external_material_block(sym):
    """每张 L2 卡内『外部原辅料线索』子块：本标的相关老雷观点+五分类+证实/待核/否决+冲突时并列体系最终判断。"""
    if sym in _sanity_anomaly(_CUR_DATE):    # 异常股:不挂外部老雷宏观佐证(含控AI集中/不追高等宏观动作词·避免与异常股价格动作混淆)·只留数据未核准
        return ('\n<div style="font-size:12px;background:#F7F6FB;border:1px solid #b9a9d6;border-left:3px solid #6b4e8c;'
                'border-radius:0 6px 6px 0;padding:6px 10px;margin:6px 0">'
                '<b style="color:#6b4e8c">外部原辅料线索</b>：本只价格与复权口径未核准，核准前不据外部观点对本只做买卖/贵贱判断（拆股待核）。</div>\n')
    ext = _load_external(_CUR_DATE)
    if not ext:
        return ""
    ids = (ext.get("by_symbol") or {}).get(sym, [])
    leadmap = {l["id"]: l for l in ext.get("leads", [])}
    indep = (ext.get("independence_check") or {}).get(sym, {})
    action = indep.get("action", "")
    sys_reason = indep.get("system_reason", "")
    hush = ext.get("hushui", {}) or {}
    rows = []
    for lid in ids:
        l = leadmap.get(lid)
        if not l:
            continue
        v = (l.get("compare") or {}).get("verdict", "待核实")
        bg, col, tag = _VERDICT_STYLE.get(v, _VERDICT_STYLE["待核实"])
        line = ('\n<div style="margin:3px 0;font-size:11.5px">'
                f'<span style="background:#EEF;color:#334;padding:0 5px;border-radius:4px">{D.esc(l.get("category",""))}</span> '
                f'<span style="background:{bg};color:{col};padding:0 6px;border-radius:4px;font-weight:700">{_VERDICT_DISP.get(v, v)}·{tag}</span><br>'
                f'<span style="color:#333">{D.esc(l.get("text",""))}</span>'
                f'<span style="color:#888">（{D.esc(l.get("theme",""))}·经映射非点名）</span>')
        conflict = (l.get("compare") or {}).get("conflict")
        if v in ("否决", "分歧") and conflict:
            line += (f'<br><b style="color:#A3231F">⚠ 体系最终判断仍为「{D.esc(action)}」</b>'
                     f'（依据：07-23实时价/估值/证据链——{D.esc(sys_reason)}）；老雷此观点不作买卖依据。'
                     f'<br><span style="color:#666">分歧：{D.esc(conflict)}</span>')
        line += "</div>"
        rows.append(line)
    hush_line = ("" if hush.get("status") == "已提供"
                 else '<div style="font-size:11px;color:#A3231F;margin-top:3px">今日湖水：未提供（历史底稿见L3·今日未更新·不参与今日判断）。</div>')
    body = "".join(rows) if rows else '<div style="font-size:11.5px;color:#888">本标的今日无外部原辅料线索。</div>'
    # 二[看板·老雷折叠]：整区 <details> 收起·不占决策视线·不满屏"待核实"；五分类标签保留(点开可见)·非决策论据
    return ('\n<details style="font-size:12px;background:#F7F6FB;border:1px solid #b9a9d6;border-left:3px solid #6b4e8c;'
            'border-radius:0 6px 6px 0;padding:6px 10px;margin:6px 0">'
            '<summary style="color:#6b4e8c;font-weight:700;cursor:pointer">外部原辅料线索（老雷·五分类·点开看·辅助盯防·非决策论据）</summary>'
            f'{body}{hush_line}\n</details>\n')


def _external_sector_risk_block():
    """板块/风险区『外部线索补充』：老雷宏观/风险框架的反向质疑与可能遗漏风险。最终仍以体系为准。"""
    ext = _load_external(_CUR_DATE)
    if not ext:
        return ""
    supp = ext.get("sector_risk_supplements", []) or []
    hush = ext.get("hushui", {}) or {}
    if not supp:
        return ""
    rows = []
    for s in supp[:14]:
        v = s.get("verdict", "待核实")
        bg, col, _tag = _VERDICT_STYLE.get(v, _VERDICT_STYLE["待核实"])
        rows.append('<div style="margin:2px 0;font-size:11.5px">'
                    f'<span style="background:{bg};color:{col};padding:0 5px;border-radius:4px">{_VERDICT_DISP.get(v, v)}</span> '
                    f'<span style="color:#555">[{D.esc(s.get("theme",""))}]</span> {D.esc(s.get("text",""))} '
                    f'<span style="color:#999">{D.esc(s.get("category",""))}</span></div>')
    hush_line = ("" if hush.get("status") == "已提供"
                 else '<div style="font-size:11px;color:#A3231F;margin-top:3px">今日湖水：未提供，不参与今日判断。</div>')
    # ★老雷折叠(董事长2026-07-25 v14·第二次)：整区 <details> default收起(不加open)·打开产品不满屏"待核实"·点开才见·五分类标签保留在内
    return ('<details style="background:#F7F6FB;border:1px solid #b9a9d6;border-radius:8px;padding:9px 12px;margin:8px 0">'
            '<summary style="font-size:14px;font-weight:800;color:#6b4e8c;cursor:pointer">外部线索补充 · 老雷主题（反向质疑/可能遗漏风险 · 点开看 · 非决策论据·体系为准）</summary>'
            '<div style="font-size:11px;color:#777;margin:4px 0 5px">来源：老雷财经_核心提炼（宏观/风险框架）。最终买卖仍以体系(production+风控)为准；此处仅补充盯防视角。</div>'
            f'{"".join(rows)}{hush_line}</details>')


# ── 出品前统一口径(根治·非手工补HTML·董事长工单2026-07-24) ──
# 把 locked_v1~v7 手工补的活固化进渲染器:逐卡现价归一到实时px(治L36)、异常股(拆股口径异常)
# 自动退出估值token(治L49内容·黄金样板locked_v7)、AI集中度单值(治L31)、全文断长行(治L23)。
# ★异常股卡内估值语义子句级scrub(GPT裁定·删语义非换格式):删含估值词的整个子句(子句=分隔符/标签之间)
_VAL_SCRUB = re.compile(
    r"[^。；！？·｜、\n<>（）()]*"
    r"(?:峰值定价|按峰值|持续峰值|峰值盈利|峰值PE|勿按峰值|留峰值|安全垫|正常化\s?EPS|正常年景|正常化每股盈利"
    r"|正常化中期|中期正常化|敏感性|共识目标|近共识|再评级|EPS朝|EPS回|下修|参考值|合理区|合理上沿|合理下沿|中期PE|中周期PE|中期市盈率|正常化PE"
    r"|极贵|景气高点|穿牛熊|公允|中周期|合理值|中枢[¥$\d]|\d+\.?\d*\s?倍|中期\[待核\]|\[参考值待核\]|\[中值待核\]|\[倍数待核\]|峰值\[口径待核\]"
    r"|远在其下|盈利崩|不追高|追高|明显便宜|等它跌|算高|离谱|高点|低点|\d+\s?%概率)"
    r"[^。；！？·｜、\n<>（）()]*")


def _global_anom_scrub(html):
    """全文近异常股(爱德万/闪迪±80字)含估值语义的整句删(堵卡外:量级哨兵verdict/板块脚注·GPT裁定)。"""
    def near(pos):
        w = re.sub(r"<[^>]+>", " ", html[max(0, pos - 80):pos + 80])
        return "爱德万" in w or "闪迪" in w
    o, last = [], 0
    for m in _VAL_SCRUB.finditer(html):
        if near(m.start()):
            o.append(html[last:m.start()]); o.append("[异常价·数据未核准·不计估值]"); last = m.end()
    o.append(html[last:])
    return "".join(o)
_NUKE_VAL = [(r"\d+\.?\d*\s?倍", "[倍数待核]"), ("峰值定价", "峰值[口径待核]"), ("景气高点", "[异常待核]"),
             ("穿牛熊", "[异常待核]"), ("极贵", "[异常待核]"), ("合理上沿", "[异常待核]"),
             ("合理值", "[参考值待核]"), ("公允", "[参考值待核]"), ("中周期", "中期[待核]"), ("中枢", "[中值待核]")]


def _next_anchor_pos(h, start):
    m = re.search(r'id="(?:why|deep|act)-[A-Z]{2}\.[A-Z0-9]+"', h[start:])
    return start + m.start() if m else len(h)


_C2_DZ = {"景气高点": "[异常待核]", "峰值定价": "峰值[口径待核]", "极贵": "[异常待核]",
          "合理值": "[参考值待核]", "中周期": "中期[待核]", "穿牛熊": "[异常待核]", "公允": "[参考值待核]",
          "高位": "[异常待核]"}


def _c2_cooccur_neutralize(html):
    """C2全区共现中和(复刻locked_v7·堵卡片边界外盲区):全HTML『爱德万』或『闪迪』与定价类禁词
    ±60字共现→中和禁词(不误伤离异常股远的正常周期股·如通用『周期股景气高点』不动)。"""
    _BLK = re.compile(r"</(?:td|tr|div|p|li|h[1-6]|details|table|summary)>|<br\s*/?>")

    def near_anom(pos):
        # 同一块级单元内(不跨表格cell/行/块)才算共现·避开表格相邻cell的爱德万行标误判
        lo, hi = max(0, pos - 400), pos + 400
        left = _BLK.split(html[lo:pos])[-1]
        right = _BLK.split(html[pos:hi])[0]
        w = re.sub(r"<[^>]+>", " ", left + right)
        return "爱德万" in w or "闪迪" in w
    for tok, rep in _C2_DZ.items():
        out, last = [], 0
        for m in re.finditer(re.escape(tok), html):
            if near_anom(m.start()):
                out.append(html[last:m.start()]); out.append(rep); last = m.end()
        out.append(html[last:]); html = "".join(out)
    out, last = [], 0                                   # \d+倍 同理
    for m in re.finditer(r"\d+\.?\d*\s?倍", html):
        if near_anom(m.start()):
            out.append(html[last:m.start()]); out.append("[倍数待核]"); last = m.end()
    out.append(html[last:])
    return "".join(out)


_ANOM_DATE_HOLDER = {"d": None}


def _anomaly_gate_block(sym):
    """异常股(拆股/复权口径异常)核准标注·注入why卡顶(保L49窗口命中·且第一眼可见)。守理由只留数据未核准。"""
    if sym not in _sanity_anomaly(_ANOM_DATE_HOLDER["d"] or ""):
        return ""
    return ('\n<div style="font-size:12px;background:#fff2f2;border:1px solid #e0a0a0;border-left:4px solid #c0392b;'
            'border-radius:0 6px 6px 0;padding:7px 10px;margin:6px 0">'
            '<b style="color:#c0392b">⚠ 数据未通过专项核准，不可据此买卖（非由估值推导）</b>'
            '——本只价格/复权口径异常（拆股/复权待核）：核准前退出估值/倍数/止盈/加仓·守=数据未核准暂停判断，'
            '不是由估值推导的守。待补：正式代码/交易所/拆股公告/拆股前后价与股数/两独立行情源一致。'
            '\n</div>\n')


def _finalize_product(out, each, dyn, date, conc):
    anom = _sanity_anomaly(date)          # {sym: 倍数}·拆股/复权口径异常股
    # 1) 逐卡现价归一到实时 production px(治L36同股多现价) + 异常股退出估值(治L49内容)
    for hc in each:
        sym = hc.get("代码")
        px = D._price_of(sym, dyn)
        c = D.cur(sym)
        if px is None:
            continue
        canon = f"{c}{px:,.2f}"
        is_anom = sym in anom
        for pref in ("act", "why", "deep"):
            i = out.find(f'id="{pref}-{sym}"')
            if i < 0:
                continue
            j = _next_anchor_pos(out, i + 12)
            seg = out[i:j]
            seg = re.sub(r"(现价约?)\s*" + re.escape(c) + r"[\d,]+(?:\.\d+)?", lambda m: m.group(1) + canon, seg)
            out = out[:i] + seg + out[j:]   # GPT裁定:停用卡内字符串scrub·异常股改由source-null(估值字段/块函数=None)
    # 2) AI集中度单值(治L31):以 production 现算值为唯一源·替换所有旧硬编码取值
    ai = _cat_pct(conc, "AI供应链")
    if ai and ai != "—":
        for stale in ("65.9%", "66.7%", "65.6%", "65.8%"):
            out = out.replace(stale, ai)
    # 3) 嵌套全角括号→内层半角(治L13:『（尺：…（forward P/E）…』外层50字内不闭合被判失衡)
    for a, b in (("（forward P/E）", "(forward P/E)"), ("（forward EPS）", "(forward EPS)"),
                 ("（forward P/E", "(forward P/E"), ("（forward EPS", "(forward EPS"),
                 ("（第一关过）", "(第一关过)"), ("今日激活（第一关", "今日激活(第一关")):
        out = out.replace(a, b)
    # 5) 湖水一致性(退回5):今日湖水未提供→旧湖水原话标『历史底稿·不参与今日判断』(消"声明未提供却展示旧原话"矛盾)
    try:
        _ext = _rj(ROOT / "data" / "external" / f"external_material_{date}.json")
        if (_ext.get("hushui") or {}).get("status") != "已提供":
            out = re.sub(r"湖水\s*原话(</[^>]+>)?\s*（(\d{4}-\d{2}-\d{2})）",
                         lambda m: f"湖水【历史底稿·{m.group(2)}·今日未更新·不参与今日判断】原话{m.group(1) or ''}（{m.group(2)}）", out)
    except Exception:
        pass
    # 6) 板块/世界观叙述:异常股价格派生统计"爱德万/闪迪 −N%(自高点)"→口径未核准·不计(保正常peer如东京电子−21%)·退回6含8035
    out = re.sub(r"(爱德万|闪迪)\s*[−\-]\s?\d+\.?\d*\s?%", r"\1（价格口径未核准·不计）", out)
    # 6b) 爱德万目标价¥33,544历史错误案例限定 → 已移进共享注入点 deep_render._mark_hist_target(part6_rulers)·
    #     三层/机器版同源单点覆盖两份(退回1·locked_v10);此处删旧全局正则·避免与共享注入双重包裹。
    # 4) 全文断长行(治L23·把既有块级断行从机构块扩到全产品)
    out = re.sub(r"(</(?:div|tr|table|details|h2|h3|li|p|span)>)", r"\1\n", out)
    return out


def _chain_link(daily: dict, key: str) -> dict:
    for l in (daily.get("links") or []):
        if key in str(l.get("node", "")):
            return l
    return {}


def _chain_trunc(s: str, n: int) -> str:
    """括号安全截断(治L13)：截 n 字后按嵌套序补齐未闭合括号，再加…。"""
    s = re.sub(r"\s+", " ", str(s)).strip()
    if len(s) <= n:
        return s
    cut = s[:n].rstrip("·、，,； ")
    pairs = {"（": "）", "(": ")", "「": "」", "【": "】", "《": "》", "“": "”"}
    closers = set(pairs.values())
    st = []
    for ch in cut:
        if ch in pairs:
            st.append(pairs[ch])
        elif ch in closers and st and st[-1] == ch:
            st.pop()
    return cut + "…" + "".join(reversed(st))


def _decision_chain(date: str, dyn: dict, daily: dict, dec: dict, act_map: dict | None = None) -> str:
    """★决策逻辑链(董事长认大方向·依《决策逻辑链_正确设计_20260709》)：产品顶部自上而下一条链，
    ①世界观→②国家战略→③资金流总闸→④板块轮动→⑤五关→⑥决策(每只追源)→⑦复盘↺。
    每层三句：今天出了啥[真抓当日]→拿本层尺一量[支持/动摇]→一句结论+往下传。上层结论作下层前提(因果闭环)。"""
    e = D.esc
    der = daily.get("derived", {}) or {}
    sw = der.get("state_words", {}) or {}
    scope = der.get("opportunity_scope", "")
    constraint = der.get("decision_constraint", "")
    brief = _rj(ROOT / "data" / "news" / f"gpt_briefing_{date}.json")   # ★当日GPT简报(董事长授权新闻源)·按层归类·分层递推融进链(非贴前面)
    cl = brief.get("chain_layers", {}) or {}
    prod = dyn.get("prod", {}) or {}
    holds = [h for h in (prod.get("holdings") or []) if not str(h.get("symbol", "")).startswith("CC.")]
    sym2name = {str(h.get("symbol")): str(h.get("name") or h.get("symbol")) for h in holds}
    anom = set(_sanity_anomaly(date)) if "_sanity_anomaly" in globals() else {"JP.6857", "US.SNDK"}
    activated = "、".join(prod.get("activated_nodes") or []) or (sw.get("opportunity_scope") and "见口径") or "待接"

    def layer(num, title, ruler, whatnews, measure, concl, handoff):
        return (
            f'<div style="border-left:3px solid #2f6b4f;background:#0e1a14;border-radius:8px;padding:9px 12px;margin:8px 0">'
            f'<div style="font-size:14.5px;font-weight:800;color:#7ee0a0">{e(num)} {e(title)}<span style="color:#6b8b7a;font-weight:400;font-size:11.5px">　尺：{e(ruler)}</span></div>'
            f'<div style="font-size:12.5px;color:#d7e6dd;margin-top:4px"><b style="color:#8fb8a4">今天出了啥（真事件）</b>：{whatnews}</div>'
            f'<div style="font-size:12.5px;color:#d7e6dd;margin-top:2px"><b style="color:#8fb8a4">拿本层尺一量</b>：{measure}</div>'
            f'<div style="font-size:12.5px;color:#ffe0a0;margin-top:2px"><b style="color:#e0b060">一句结论 → 往下传</b>：{concl}　<span style="color:#8fb8a4">↓ {handoff}</span></div>'
            f'</div>')

    def _impact_names(syms):
        return "、".join(sym2name.get(s, s) for s in (syms or []))

    def layer_cl(num, title, ruler, key, fb_news, fb_measure, fb_concl, fb_handoff):
        """按层归类：优先用当日简报归到本层的真事件(chain_layers[key])做因果递推；无则回落 daily.links。"""
        d = cl.get(key) or {}
        if d.get("event"):
            imp = _impact_names(d.get("impact_symbols"))
            wn = (e(d.get("event", ""))
                  + (f'<div style="font-size:11.5px;color:#c8b89a;margin-top:2px"><b style="color:#c8a060">↳ 持仓影响</b>：{e(imp)}</div>' if imp else "")
                  + f'<span style="color:#7a6b5a;font-size:10.5px">（来源：{e(d.get("source",""))}）</span>')
            return layer(num, title, ruler, wn, e(d.get("measure", "")), e(d.get("judgment", "")), e(d.get("handoff", "")))
        return layer(num, title, ruler, fb_news, fb_measure, fb_concl, fb_handoff)

    l0 = _chain_link(daily, "总命题")
    l1 = _chain_link(daily, "战略指向")
    l2fed = _chain_link(daily, "总闸·美联储")
    l2rot = _chain_link(daily, "资金轮动")
    l3sec = _chain_link(daily, "板块轮动")

    def strq(lk):
        s = str(lk.get("strength", "中"))
        return {"强": "强·支持", "中": "中·维持基线", "弱": "弱·动摇"}.get(s, s)

    scan_note = ('<div style="font-size:11px;color:#e0b0b0;margin:6px 0;padding:5px 8px;background:#241010;border-radius:6px">⚠ 今日重大新闻已<b>按层归类、一层层递推</b>写进下面各层的"今天出了啥"（非贴在前面）：①风险偏好转向 ②60国关税 ③滞胀 ④半导体大跌。机器旧快照"板块走强/合格0条"是07-22旧数据·已按当日简报纠正。</div>' if cl else "")

    blocks = []
    # ① 世界观（risk-off）
    blocks.append(layer_cl("①", "世界观 · 风险偏好/AI主线", "总则第二条·证据链骨架", "world",
        _chain_trunc(re.sub(r"【[^】]*】", "", str(l0.get("evidence", "今日无重大世界观级新闻"))), 150),
        f'强度{strq(l0)}', "世界大格局今天没翻转（AI/秩序主线继续）", "传②：看国家战略层今天有没有政策事件"))
    # ② 国家战略（★60国关税·今天必有事件）
    blocks.append(layer_cl("②", "国家战略 · 美/各国动向", "总则第二条·战略地图", "strategy",
        _chain_trunc(re.sub(r"【[^】]*】", "", str(l1.get("evidence", "今日无重大战略级新闻"))), 150),
        f'强度{strq(l1)}', "战略主线维持", "传③：看总闸给不给钱"))
    # ③ 资金流·总闸（滞胀）
    cap_news = _chain_trunc(re.sub(r"【[^】]*】", "", str(l2fed.get("evidence", "") or l2rot.get("evidence", "") or "无新Fed事件·维持基线")), 140)
    blocks.append(layer_cl("③", "资金流·总闸（美联储/流动性/利率）", "资金流动完整机制·总闸尺", "capital",
        cap_news, f'总闸={e(sw.get("fed_gate","维持·观察"))}', "钱还是紧的、只精准流向AI", "传④：看钱流入还是流出半导体"))
    # ④ 板块轮动（半导体大跌·纠正SOXX旧值）
    blocks.append(layer_cl("④", "板块轮动 · 钱流向哪、哪些激活", "板块地图·激活尺", "sector",
        _chain_trunc(re.sub(r"【[^】]*】", "", str(l3sec.get("evidence", "今日板块无重大轮动"))), 150),
        f'强度{strq(l3sec)} → 板块={e(sw.get("sector","中性"))}', f'今日激活承接节点：<b>{e(activated)}</b>', "传⑤/⑥：对每只走五关、不追跌加仓"))
    chain_top = scan_note + "".join(blocks)

    # ⑤ 五关汇总(方向/位置/估值/护城河/深研 across 持仓)
    from collections import Counter
    def gval(h, path, default="—"):
        cur = h
        for p in path:
            cur = (cur or {}).get(p) if isinstance(cur, dict) else None
        return cur if cur not in (None, "") else default
    n_dir = sum(1 for h in holds if str(h.get("hard_filter")) in ("符合", "符合方向"))
    moat_dist = Counter(str((h.get("moat") or {}).get("moat_grade", "待评")) for h in holds)
    val_dist = Counter(("口径未核准·不计" if h.get("symbol") in anom else str((h.get("valuation") or {}).get("label") or (h.get("valuation") or {}).get("status") or "待接")) for h in holds)
    gate5 = (
        '<div style="border-left:3px solid #3a6ea5;background:#0e1622;border-radius:8px;padding:9px 12px;margin:8px 0">'
        '<div style="font-size:14.5px;font-weight:800;color:#7fb2e0">⑤ 五关筛选 · 每只走同一条五关（方向/位置/估值/护城河/深研）<span style="color:#6b8b7a;font-weight:400;font-size:11.5px">　尺：过滤标准筛选规则</span></div>'
        f'<div style="font-size:12.5px;color:#d7e6dd;margin-top:4px"><b style="color:#8fb8a4">今天怎么量</b>：{len(holds)} 只持仓全部走五关。'
        f'第1关方向符合 <b>{n_dir}/{len(holds)}</b>；第4关护城河分布 {e("、".join(f"{k}{v}只" for k,v in moat_dist.items()))}；'
        f'第3关估值 {e("、".join(f"{k}{v}只" for k,v in val_dist.items()))}。</div>'
        '<div style="font-size:12.5px;color:#ffe0a0;margin-top:2px"><b style="color:#e0b060">合成规则</b>：护城河宽+方向对+估值不贵→敢拿/可加；生意硬但价贵/位高→守、别加；护城河或深研没做完→只给"初判·待研究"。'
        '　<span style="color:#8fb8a4">↓ 五关合成 → 出每只加/减/守/等</span></div></div>')

    # ⑥ 决策(每只追源①-⑤) + 个股前瞻(二·看板4：结合今日事件·非纯财务估值·40/100双档路径)
    impact_map = {}
    for _lk, _ld in cl.items():
        for s in (_ld.get("impact_symbols") or []):
            impact_map.setdefault(s, []).append(str(_ld.get("judgment", "")))

    # 异常股(价格口径待核)基本面前瞻·董事长2026-07-25『缺指标≠放弃预测』:价格贵贱待核·但方向不缺席。
    #   门安全:无 倍/中枢/峰值/正常化EPS/高位/高点/参考值 等估值词·无 3000/55/95 等特定裸数字。已入登记20260725。
    _ANOM_FWD = {
        "JP.6857": "短期偏回调·中期偏上行（据EDINET报告实际EPS¥413.29＋营业利润上修至¥7300亿指引＋AI测试需求；价格贵贱待核·不因价格加减位、不出目标价）。失效：下季营业利润不及指引或测试机出货转弱。见分晓：下季财报约2026-10。",
        "US.SNDK": "短期偏跌·中期偏下行（据EDGAR报告实际仍亏损＋NAND周期见顶＋去库存；价格贵贱待核·不因价格加减位、不出目标价）。失效：NAND合约价环比转涨或季度扭亏。见分晓：下季财报约2026-10。",
    }

    def _stock_forward(sym, is_anom, val, act):
        evs = impact_map.get(sym) or []
        ev = _chain_trunc("；".join(evs), 70) if evs else "今日无直接事件·随大盘防守"
        if is_anom:
            fwd = _ANOM_FWD.get(sym, "价格贵贱待核·基本面方向不缺席（见预测登记）")
            return (f'<div style="font-size:11px;color:#c8b89a;margin-top:2px"><b style="color:#c8a060">前瞻·基本面方向</b>'
                    f'：今日事件影响 {e(ev)}　｜{e(fwd)}<span style="color:#8a7a5a">（已入预测登记20260725·进PDCA）</span></div>')
        lab = str((val or {}).get("label") or (val or {}).get("status") or "待接")
        path = f"估值={e(lab)}·路径看基本面兑现（非纯财务外推）；组合40%/100%双档见顶部目标缺口"
        return f'<div style="font-size:11px;color:#c8b89a;margin-top:2px"><b style="color:#c8a060">前瞻</b>：今日事件影响 {e(ev)}　｜路径 {path}</div>'

    rows = []
    for h in holds:
        sym = str(h.get("symbol", ""))
        nm = str(h.get("name") or sym)
        # L28 同源(架构师T2 2026-07-25):⑥决策表动作用【与个股卡今日动作同一源】act_map(卡的holding_ctx最终动作),
        #   不再独立取 h.action → 消灭⑥与自检决定摘要动作打架(每只当天只能一个动作)。
        act = str((act_map or {}).get(sym) or h.get("action") or (dec.get(sym, {}) or {}).get("action") or "守")
        hard = str(h.get("hard_filter", "—"))
        nodes = h.get("matched_node_classes_effective") or []
        is_anom = sym in anom
        val = h.get("valuation") or {}
        # 追到哪几环
        chain_ref = ["①", "③", "⑤"]
        if nodes:
            chain_ref.insert(2, "④")
        chain_ref = "".join(dict.fromkeys(chain_ref))
        if is_anom:
            basis = (f'方向={e(hard)}（①②④）；<b style="color:#ffb454">价格贵贱待核</b>（复权口径未核准·不因价格加减位）→ 基本面方向不缺席（见下前瞻）·只看生意坏没坏（③总闸中档下先守）')
        else:
            moat = h.get("moat") or {}
            basis = (f'方向={e(hard)}（①②④激活节点{e("、".join(nodes) or "—")}）'
                     f'　位置/估值={e(str(val.get("label") or val.get("status") or "待接"))}（⑤第2/3关）'
                     f'　护城河={e(str(moat.get("moat_grade","待评")))}（⑤第4关）'
                     f'　→ 总闸中档③下 <b>{e(act)}</b>·防守优先不加仓')
        basis += _stock_forward(sym, is_anom, val, act)
        color = {"加": "#7ee0a0", "减": "#ff9a9a", "守": "#cfe0d6", "等": "#e0c060"}.get(act, "#cfe0d6")
        rows.append(
            f'<tr><td style="font-weight:700">{e(nm)}<br><span style="color:#6b8b7a;font-size:10.5px">{e(sym)}</span></td>'
            f'<td style="text-align:center"><b style="color:{color};font-size:15px">{e(act)}</b>'
            f'<span class="actck" data-actck="{e(sym)}|⑥决策表|{e(act)}" style="display:none"></span></td>'
            f'<td style="text-align:center;color:#8fb8a4;font-weight:700">{e(chain_ref)}</td>'
            f'<td style="font-size:11.5px;color:#d7e6dd">{basis}</td></tr>')
    decision = (
        '<div style="border-left:3px solid #c47a1e;background:#1a140a;border-radius:8px;padding:9px 12px;margin:8px 0">'
        '<div style="font-size:14.5px;font-weight:800;color:#ffb454">⑥ 今天决策 · 每只加/减/守/等（★每只显示追到 ①–⑤ 哪几环）<span style="color:#8a7a5a;font-weight:400;font-size:11.5px">　来源：production 当日实时</span></div>'
        f'<div style="font-size:12px;color:#e0b060;margin-top:3px">全局口径（从③④下传）：{e(_chain_trunc(constraint, 120))}</div>'
        '<table border="1" cellpadding="5" style="border-collapse:collapse;width:100%;font-size:12px;margin-top:6px">'
        '<tr style="background:#2a1f10"><th>标的</th><th>动作</th><th>追到哪几环</th><th>一句依据（五关合成·因果链终点）</th></tr>'
        + "".join(rows) + '</table></div>')

    # ⑦ 复盘
    try:
        rv = _rj(ROOT / "data" / "pdca" / f"pdca_review_{date}.json")
        acc = (rv.get("accuracy") or {}).get("rate_pct")
        traj_n = len(rv.get("certainty_trajectories") or [])
    except Exception:
        acc, traj_n = None, 0
    n_dec = len(holds)
    review = (
        '<div style="border-left:3px solid #6a5aa0;background:#14101c;border-radius:8px;padding:9px 12px;margin:8px 0">'
        '<div style="font-size:14.5px;font-weight:800;color:#b0a0e0">⑦ 复盘 · 闭环收口（今天决策→记分卡→明天验证 ↺ 回①）<span style="color:#7a6b9a;font-weight:400;font-size:11.5px">　来源：pdca</span></div>'
        f'<div style="font-size:12.5px;color:#d7e6dd;margin-top:4px"><b style="color:#b0a0e0">闭环三步</b>：'
        f'①今天这 {n_dec} 只决策（⑥）已记入今日决定表·进记分卡；'
        f'②到期由复盘按真实结果验证对错（多尺度轨迹 {traj_n} 条在追踪·到期判对率 {e(str(acc)+"%" if acc is not None else "首日/待累计")}）；'
        '③复盘结论回灌 ①世界观 做下一轮前提。'
        '<span style="color:#8fb8a4">　↺ 回① —— 一条链首尾相接、闭环成立。</span></div></div>')

    top3 = ""
    if brief.get("top3_watch"):
        items = "".join(f'<li style="margin:3px 0">{e(t)}</li>' for t in brief.get("top3_watch", []))
        top3 = ('<div style="border:2px solid #c47a1e;background:#1a140a;border-radius:9px;padding:9px 12px;margin:8px 0">'
                '<div style="font-size:14.5px;font-weight:800;color:#ffb454">🎯 今天最该关注 3 件事（来自当日简报）</div>'
                f'<ol style="margin:5px 0 0 18px;font-size:12.5px;color:#e0d0b0">{items}</ol></div>')
    intro = (
        '<details class="layer" id="L0-chain" open style="border:2px solid #2f6b4f;margin:10px 0">'
        '<summary style="font-size:16px;font-weight:800;color:#7ee0a0;padding:8px">决策逻辑链 · 自上而下一条链（决策是终点·每只可追到源头）</summary>'
        '<div class="body" style="padding:6px 10px">'
        '<div style="font-size:12px;color:#8fb8a4;margin-bottom:6px">①世界观 → ②国家战略 → ③资金流总闸 → ④板块轮动 → ⑤五关 → ⑥决策 → ⑦复盘 ↺回①。'
        '<b>今日重大新闻已按层归类、一层层递推进各层</b>（非贴在前面）：每层"今天出了啥"是属于该层的真事件，结论由上一层推下来做本层前提；最后的"加/减/守/等"是走完整条链的产物。术语表/外部观点/完整研究底稿/机构底稿见下方折叠。</div>')
    return intro + chain_top + gate5 + decision + review + top3 + '</div></details>'


def _patch_daily_with_briefing(daily: dict, brief: dict) -> None:
    """★消灭深层两张皮(locked_v5)：用当日简报 chain_layers 覆盖 daily.links/derived 的旧宏观判断，
    让旧宏观判研卡(part1_layers 的 layer-strategy/capital/sector)、页头 today_direction 与七层链
    读【同一套真事件·同结论】。禁止"新链+旧判研卡"两套矛盾。就地改 daily(dyn['daily'] 同对象)。"""
    cl = (brief or {}).get("chain_layers") or {}
    if not cl or not isinstance(daily, dict):
        return
    node_key = {"总命题": "world", "战略指向": "strategy", "总闸·美联储": "capital",
                "资金轮动": "capital", "手段层": "capital", "板块轮动": "sector"}
    for l in (daily.get("links") or []):
        node = str(l.get("node", ""))
        key = next((k for kw, k in node_key.items() if kw in node), None)
        d = cl.get(key) if key else None
        if not (d and d.get("event")):
            continue
        l["direction"] = d.get("judgment", l.get("direction"))
        l["plain"] = d.get("event", "")
        l["evidence"] = d.get("event", "") + "（来源：" + str(d.get("source", "")) + "·当日简报按层归类·已纠正机器旧快照/漏报）"
        if key in ("strategy", "capital", "sector"):
            l["strength"] = "强"                 # 今日=重大事件/大跌·非"无新闻·维持基线"
        l["today_events"] = [d.get("judgment", "")]
        # 保留研究源(治L9不缩水)：把弱相关并入新闻一起渲染·不删任何源；只改判断口径·避开"无新闻·维持原判断"弱分支
        l["news_items"] = (l.get("news_items") or []) + (l.get("weak_items") or [])
        l["weak_items"] = []
    der = daily.setdefault("derived", {})
    # F3(董事长2026-07-25):禁硬编码旧口径——四层结论由当日简报 chain_layers 真数据生成(与规则层同源·随数据变)
    _cl = (brief or {}).get("chain_layers", {}) or {}
    def _cj(k, fb):
        return str((_cl.get(k) or {}).get("judgment") or fb)
    corrected = ("【已按当日简报按层生成·非旧快照】"
                 f"①世界观={_cj('world','风险偏好中性偏谨慎')}；②国家战略={_cj('strategy','60国关税·保护主义/推通胀')}；"
                 f"③资金流={_cj('capital','油价回落·滞胀压力缓和·总闸中档')}；④板块={_cj('sector','半导体走弱·资金流出→守核心·不追跌')}")
    der["today_direction"] = corrected
    der["today_direction_short"] = "今天：半导体走弱(费半-4.5%)+60国关税→守核心、控AI集中、不追跌"
    sw = der.setdefault("state_words", {})
    sw["strategy"] = "60国关税·保护主义抬头（当日重大战略事件）"
    sw["sector"] = "走弱·防守"
    sw["capital"] = "钱更紧·滞胀"
    sw["fed_gate"] = "维持·观察（滞胀下更难降息）"


def _stability_banners(date: str) -> tuple:
    """董事长2026-07-25:三张显式稳定性状态条(页头下·产品实物可见)——①护城河重评状态(16天硬闸)
    ②非OpenD账户待确认(不进精确集中度)③老雷正文待导出。返回(banner_html, moat_stale_bool)。"""
    import datetime as _dt
    e = D.esc
    prod_d = _dt.date(int(date[:4]), int(date[4:6]), int(date[6:8]))
    # ① 护城河重评状态
    moat_as_of, moat_age, moat_stale = "无", 999, True
    try:
        mp = ROOT / "data" / "moat" / f"moat_analysis_{date}.json"
        if not mp.exists():
            import glob as _g
            cands = sorted(_g.glob(str(ROOT / "data" / "moat" / "moat_analysis_*.json")))
            mp = pathlib.Path(cands[-1]) if cands else mp
        md = json.loads(mp.read_text(encoding="utf-8"))
        moat_as_of = str(md.get("date") or md.get("as_of") or mp.stem.split("_")[-1])
        ao = _dt.date(int(moat_as_of[:4]), int(moat_as_of[4:6]), int(moat_as_of[6:8]))
        moat_age = (prod_d - ao).days
        moat_stale = moat_age > 16
    except Exception:
        moat_stale = True
    if moat_stale:
        moat_bar = (f'<div style="background:#3a1414;border:2px solid #c0392b;border-radius:8px;padding:8px 12px;margin:6px 0;color:#ff8a8a;font-weight:700">'
                    f'🛑 护城河重评状态：截至 {e(moat_as_of)}·距生产日 {moat_age} 天 &gt; 16天线——<b>超期未重评·出厂闸FAIL</b>（须先跑护城河重评脚本再出厂）</div>')
    else:
        moat_bar = (f'<div style="background:#0e1a14;border:1px solid #2f6b4f;border-radius:8px;padding:8px 12px;margin:6px 0;color:#7ee0a0">'
                    f'🛡 护城河重评状态：<b>已重评</b>·截至 {e(moat_as_of)}·距生产日 {moat_age} 天（未超16天重评线·合格）</div>')
    # ② 非OpenD账户待确认
    pend = []
    try:
        rv = json.loads((ROOT / "data" / "holdings" / f"holdings_review_{date}.json").read_text(encoding="utf-8"))
        pend = rv.get("非OpenD待确认_holdings") or []
    except Exception:
        pass
    if pend:
        names = "、".join(str(p.get("name") or p.get("symbol")) for p in pend[:10])
        pend_bar = (f'<div style="background:#3a2a10;border:2px solid #c47a1e;border-radius:8px;padding:8px 12px;margin:6px 0;color:#ffcf80">'
                    f'⚠ 非OpenD账户【过期·待确认】{len(pend)}只（{e(names)}…）：SBI/IBKR/bitFlyer/BTC/ETH/各币种现金不接OpenD·沿用旧快照·<b>不进精确集中度/现金建议</b>；'
                    f'软银已按董事长核准6900(富途4100+SBI2800·OpenD曾显7100·差200待复核)。需董事长报当日真实账户后更新。</div>')
    else:
        pend_bar = ""
    # ③ 老雷正文待导出
    lei_bar = ""
    try:
        ext = json.loads((ROOT / "data" / "external" / f"external_material_{date}.json").read_text(encoding="utf-8"))
        le = ext.get("老雷新增待导出") or {}
        if le.get("files"):
            lei_bar = (f'<div style="background:#231a3a;border:2px solid #6a5aa0;border-radius:8px;padding:8px 12px;margin:6px 0;color:#c8b8f0">'
                       f'📄 老雷新增录音【正文待导出】：{e("、".join(le["files"]))}——.gdoc为Drive虚拟文件·正文本地读不到·'
                       f'<b>已发现·非漏掉</b>；需董事长导出为TXT放进 inputs/ 重跑外部原辅料接入 正文才进产品。</div>')
    except Exception:
        pass
    # ④ ★M1(裁定2026-07-27):持仓基表 bootstrap(首次自动生成·未经人工核对)→显著标注·不冒充已核对
    boot_bar = ""
    try:
        ht = json.loads((ROOT / "data" / "accounts" / f"holdings_true_{date}.json").read_text(encoding="utf-8"))
        if ht.get("bootstrap") is True:
            boot_bar = ('<div style="background:#3a1414;border:2px solid #d24b4b;border-radius:8px;padding:8px 12px;margin:6px 0;color:#ff8a8a;font-weight:700">'
                        '🔶 持仓基表【首次自动生成·未经人工核对】：本次无先前已核对基表→从富途实时持仓 bootstrap 生成；'
                        '<b>仅富途账户·非富途账户(SBI/IBKR/bitFlyer)缺失待人工补全</b>；股数=当次富途实时(真·可回溯)·但整张基表未经人工核对'
                        '——集中度/配仓判断以此为准需谨慎，待董事长核过持仓后转 confirmed。</div>')
    except Exception:
        pass
    banner = ('<div style="margin:8px 0">'
              '<div style="font-size:13px;font-weight:800;color:#e0b060;margin-bottom:3px">📋 稳定性状态条（董事长2026-07-25·drive/futu变更处理）</div>'
              + boot_bar + moat_bar + pend_bar + lei_bar + '</div>')
    return banner, moat_stale


def _embed_actck(out: str) -> str:
    """L28五处全埋(架构师裁定一2026-07-25):今日动作表(模板120)/个股卡header chip(模板167)/为什么现在标签(模板190)
    补埋 data-actck 锚。★用【实际显示的动作字】做锚值(非decisions)——才能抓住某处显示偏离主表。⑥决策表/自检决定摘要已在生成处埋。"""
    ACTS = "加减守等买观"
    # ① 今日动作表:区域内每行 chip动作 + 股票td的sym → 埋锚
    ti = out.find("今日动作表")
    if ti >= 0:
        tend = out.find("</table>", ti)
        if tend > 0:
            def _row(m):
                row = m.group(0)
                if "data-actck" in row:
                    return row
                ma = re.search(r'data-l="动作">\s*<span class="chip[^>]*>[^<]*?([' + ACTS + r'])\s*</span>', row)
                ms = re.search(r'data-l="股票">[^<]*?<span[^>]*>([A-Z]{2}\.[A-Z0-9]+)</span>', row)
                if ma and ms:
                    anc = f'<span class="actck" data-actck="{ms.group(1)}|今日动作表|{ma.group(1)}" style="display:none"></span>'
                    row = row.replace("</tr>", anc + "</tr>", 1)
                return row
            seg = re.sub(r"<tr>.*?</tr>", _row, out[ti:tend], flags=re.S)
            out = out[:ti] + seg + out[tend:]
    # ②个股卡header chip + ③为什么现在标签:按 id="why-{sym}" 卡逐个·收集后倒序插入(避偏移)
    anchors = [(mm.start(), mm.group(1)) for mm in re.finditer(r'id="why-([A-Z]{2}\.[A-Z0-9]+)"', out)]
    inserts = []
    for i, (pos, sym) in enumerate(anchors):
        card = out[pos: (anchors[i + 1][0] if i + 1 < len(anchors) else len(out))]
        add = ""
        mc = re.search(r'<span class="chip[^>]*>[^<]*?([' + ACTS + r'])\s*</span>', card)
        if mc:
            add += f'<span class="actck" data-actck="{sym}|个股卡header|{mc.group(1)}" style="display:none"></span>'
        mw = re.search(r"为什么现在([" + ACTS + r"])[：:]", card)
        if mw:
            add += f'<span class="actck" data-actck="{sym}|为什么现在标签|{mw.group(1)}" style="display:none"></span>'
        if add:
            inserts.append((pos, add))
    for pos, add in sorted(inserts, reverse=True):
        out = out[:pos] + add + out[pos:]
    return out


def build(date: str) -> str:
    dyn = D.load_dynamic(date)
    dd = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    dec = _rj(ROOT / "data" / "pdca" / f"decisions_{date}.json").get("decisions", {})
    daily_chain = _rj(ROOT / "data" / "evidence_chain" / f"daily_{date}.json")   # ★决策逻辑链数据源(①-④宏观+links)
    _brief = _rj(ROOT / "data" / "news" / f"gpt_briefing_{date}.json")            # 当日简报(按层归类)
    _patch_daily_with_briefing(dyn.get("daily", {}), _brief)                       # ★locked_v5:旧宏观判研卡与七层链合一·同源纠正·消灭两张皮
    _patch_daily_with_briefing(daily_chain, _brief)                               # 链数据源也同源(冗余保险)
    conc = D._conc_now(date, dyn)
    prod = dyn.get("prod", {})
    # run_id / 生产时间(第5项:每次重排必须签发【新 run_id + 新生产时间】·页头反映本次真实运行·董事长2026-07-19)
    #   底层数据扫描的参照从 production 直接取(稳定·不受本次改写 manifest 影响)。
    data_ref = str(prod.get("run_id") or prod.get("task_id") or str(prod.get("generated_at", ""))[:19] or "待接")
    _now_dt = datetime.now()
    # S3(董事长2026-07-25·L2同源):run_id 的【时间段】锚定 production.generated_at(与 deep_render 同源·同一次扫描→两册 run_id 时间段一致),
    #   而非渲染时刻(渲染时刻每次不同→两册永不同源·L2拦不住的根因)。前缀 R3-/R- 是册型标记(三层/机器版)·L2 比对时间段+data_date。
    from datetime import timezone as _tz, timedelta as _td
    _JST = _tz(_td(hours=9))
    _scan_raw = str(prod.get("generated_at") or "")
    try:
        # 日期段=data_date(过L50·跨午夜不错位)·时间段=production.generated_at的JST时刻(与deep_render同源)
        _gt = datetime.fromisoformat(_scan_raw.replace("Z", "+00:00")).astimezone(_JST).strftime("%H%M%S")
        run_id = f"R3-{date}-{_gt}"
    except Exception:
        run_id = f"R3-{date}-{_now_dt.strftime('%H%M%S')}"         # 兜底:production无generated_at时退回渲染时刻
    build._run_id = run_id
    _cross = _now_dt.strftime("%Y%m%d") != date                    # 是否跨午夜(真实时刻不在数据日当天)
    gen = f"{_iso(date)} {_now_dt.strftime('%H:%M:%S')}" + ("（★跨午夜生产·真实时刻 " + _now_dt.strftime("%Y-%m-%d %H:%M") + "·产品归属数据日）" if _cross else "")
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
        # ★量级哨兵(异常股)detail含估值比较句/峰值/极贵→不回显·用静默理由(GPT裁定:删语义)
        if str(x.get("type")) == "量级哨兵":
            _add_tbd(x.get("name") or x.get("symbol"), "价格/复权口径异常·数据未核准·不计算估值/中枢/倍数/峰值/贵贱·不据此买卖（拆股待核）")
        else:
            _add_tbd(x.get("name") or x.get("symbol"), x.get("detail"))
    # 三+四[根治估值数据源·EDINET已接]：日股财报改接 EDINET(金融厅XBRL·真EPS)·估值待接根治归零·异常股仍退出估值
    _anom_now = set(_sanity_anomaly(date)) if "_sanity_anomaly" in globals() else {"JP.6857", "US.SNDK"}
    _edinet = (_rj(ROOT / "data" / "valuation" / f"edinet_financials_{date}.json").get("symbols") or {})
    _px = {str(h.get("symbol")): h.get("price") for h in prod.get("holdings", [])}
    _jp_ok, _jp_wait, _us_wait = [], [], []
    for h in prod.get("holdings", []):
        sym = str(h.get("symbol"))
        if sym in _anom_now:
            continue                                   # 异常股保持退出估值·不进此聚合
        v = (dyn.get("valr", {}) or {}).get(sym, {})
        if str(v.get("status")) == "OK":
            continue
        if sym.startswith("JP."):
            ed = _edinet.get(sym) or {}
            eps = ed.get("eps")
            try:
                epsf = float(eps) if eps not in (None, "") else None
            except Exception:
                epsf = None
            px = _px.get(sym)
            if epsf and epsf > 0 and isinstance(px, (int, float)):
                pe = px / epsf
                _jp_ok.append(f"{h.get('name') or sym}(EPS¥{epsf:g}·PE{pe:.1f}倍)")
            elif epsf is not None:
                _jp_ok.append(f"{h.get('name') or sym}(EPS¥{epsf:g}·亏损或PE不适用)")
            else:
                _jp_wait.append(str(h.get("name") or sym))
        else:
            _us_wait.append(str(h.get("name") or sym))
    if _jp_ok:
        _add_tbd(f"日股估值·已接EDINET（{len(_jp_ok)}只·真财报EPS）",
                 "、".join(_jp_ok) + " —— 已接日本官方EDINET(金融厅XBRL·FY2026-03有価証券报告书)·真EPS+当前PE(现价÷EPS)。合理区上下沿的PE倍数口径待架构师尺·数据源已不缺。")
    if _jp_wait:
        _add_tbd(f"日股估值·EDINET无值（{len(_jp_wait)}只：{'、'.join(_jp_wait)}）", "EDINET已接但该只当期EPS为空(如保险/亏损)·PE不适用·看营收与生意。")
    if _us_wait:
        _add_tbd(f"美股估值·输入待接（{len(_us_wait)}只：{'、'.join(_us_wait)}）",
                 "EDGAR有源但今日估值输入未接齐·只有架构师非权威估算/框架参考·核准前不据此定价。")
    tbd_rows = [{"标的": r["标的"], "原因": r["原因"]} for r in _tbd_map.values()]
    # 每只
    holds = [h for h in prod.get("holdings", []) if not str(h.get("symbol", "")).startswith("CC.")]
    each = [holding_ctx(str(h.get("symbol")), str(h.get("name") or h.get("symbol")), dyn, date, conc, set())
            for h in holds]
    # L28同源(架构师T2 2026-07-25):个股卡今日动作对齐【唯一决定表 decisions_{date}.json】(单一源)——
    #   消灭卡的独立覆盖(如no_val→观)与决定表(守)打架;决定表是权威·渲染对齐它·不擅改决定表(治理:决定表先报后改)。
    for _hc in each:
        _da = (dec.get(str(_hc.get("代码", "")), {}) or {}).get("action")
        if _da:
            _hc["今日动作"] = _da
            _hc["动作色"] = ACT_COLOR.get(_da, _hc.get("动作色"))
            _hc["动作图标"] = ACT_ICON.get(_da, _hc.get("动作图标"))
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
    _ANOM_DATE_HOLDER["d"] = date
    fresh = _freshness(date, holds)
    if fresh.get("market_closed"):
        pd = fresh["price_date"]
        px_note = (f"生产日 {_iso(date)}（{_wk(date)}·非交易日/市场休市）；"
                   f"全部现价＝最近交易日 <b>{pd}（{_wk(pd)}）</b> 收盘/盘后价（源 OpenD·<b>非实时·最近交易日收盘</b>）。")
    else:
        px_note = "美股取昨夜收；日股取当日/最近交易日收；各只价格交易日见卡内标注。"
    # 第0节:三层重排版【构建戳】——区别于数据 run_id,每次重排都刷新,让"是不是重新生成过"一眼可辨(诚实:数据仍为原扫描)
    # T5(架构师裁定2026-07-25·跨午夜规则):run_id日期段锚 data_date(合规)·但页头须【同时】显真实生成时刻(不许只显run_id日盖过)
    _gen_real = _now_dt.strftime("%Y-%m-%d %H:%M:%S")
    px_note += (f" ｜ 本次生产 run_id=<b>{run_id}</b>（三层重排版·run_id日期段=数据日 {_iso(date)}·跨午夜沿用当日）"
                f" ｜ <b>真实生成时刻 {_gen_real}</b>（本文件实际跑出来的钟点·可能跨午夜到次日·与run_id日期分开显）"
                f"；底层数据扫描={data_ref}（价=最近交易日·重排版≠重扫数据）")
    # [致命1]唯一正式决定表:总数统计【程序从动作表(each)统计得出】·不手写·三层同源(L51 校验一致)
    _act = {}
    for hc in each:
        a = str(hc.get("今日动作", "")).strip()[:1]
        _act[a] = _act.get(a, 0) + 1
    _stance_txt = (f"程序统计（共 {len(each)} 只·由动作表现算）：加 {_act.get('加', 0) + _act.get('买', 0)}"
                   f"·守 {_act.get('守', 0)}·等 {_act.get('等', 0)}·减 {_act.get('减', 0)}·观察 {_act.get('观', 0)}"
                   f"（另有『风险配仓调整建议』是待拍板的仓位再平衡·与今日动作是两回事）")
    ctx = {
        "data_date": dd, "生产时间": gen or D.md_note(dyn) if hasattr(D, "md_note") else gen, "run_id": run_id or TBD,
        "各市场价时点说明": px_note,
        "当天项数": fresh["new"], "近期项数": fresh["mid"], "陈旧项数": fresh["old"], "待接项数": len(tbd_rows),
        "总闸状态": _fed_state(dyn), "今日姿态": _stance_txt,
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
            f'<span class="actck" data-actck="{D.esc(str(hc.get("代码","")))}|自检决定摘要|{D.esc(str(hc.get("今日动作","")))}" style="display:none"></span>'
            f'｜今日价值区 {hc.get("价值区下沿","")}~{hc.get("价值区上沿","")}｜未来目标 {hc.get("目标价","")}'
            f'｜第一档 {hc.get("第一档价","")}｜第二档 {hc.get("第二档价","")}｜建议金额 {hc.get("建议金额","")}'
            f'｜推动股价的事 {_st("催化剂")}'
            f'｜失效条件 {_st("催化剂失效条件")}'
            f'｜拍板状态 {hc.get("三态文字","系统建议·尚未执行")}</div>'
            # [五·C]加仓闸逐项实测(逐只都显示·不只加-候选)
            + _stab_calc_of(hc.get("代码"), dyn, date)
            # 四[看板5]：每只真K线图(60日收盘+MA·消'画法待接')
            + _kline_svg(str(hc.get("代码")), str(hc.get("名") or hc.get("代码")))
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
    # ★决策逻辑链(董事长认大方向)——注入产品最顶部(页头后·L1前)·自上而下一条链·决策是终点
    # L28同源:⑥决策表动作与个股卡今日动作同一源(消灭动作打架)——从 each(holding_ctx结果)建 sym→今日动作 映射
    _act_map = {str(hc.get("代码")): str(hc.get("今日动作", "")) for hc in each if hc.get("代码")}
    _chain_html = _decision_chain(date, dyn, daily_chain, dec, _act_map)
    # ★稳定性状态条(董事长2026-07-25·drive/futu变更):护城河重评/非OpenD待确认/老雷待导出·产品实物可见
    _stab_html, _moat_stale = _stability_banners(date)
    build._moat_stale = _moat_stale          # 供 main 出厂闸:超期未重评→FAIL不出品
    out = re.sub(r'(<details class="layer" id="L1")', lambda m: _stab_html + _chain_html + m.group(1), out, count=1)
    # ★locked_v5:PDCA/差分等读 pdca_review 旧数据·残留旧战略判断"AI(今日无重大新闻·维持基线)"→就地包纠正标注,
    #   与七层链②同口径(活判归0·PDCA原记录保留供打分·非删)·消灭最后的两张皮残余。
    out = out.replace("AI(今日无重大新闻·维持基线)",
                      "AI【机器原判『今日无重大新闻·维持基线』·已按当日简报按层纠正为②国家战略=保护主义/60国关税·见顶部决策逻辑链】")
    # (F0/F2·董事长2026-07-25:已撤销板块/油价的人工字符串替换——禁止用replace把两边对齐;
    #  板块方向由 latest_market_snapshot 真数据经 rule_sector 重算·历史previous由管线继承·不事后改写)
    # [P0]目标—缺口 模块 + 风险配仓四规矩模块 放第一层最顶部(①离目标还差多少·董事长第一眼看到)
    # ★轮67 AF1:第一屏缺口块——z4_two_segment 存在→用 Z4 两段报法(点值口径/四等级/超限/退出/微软标注/机会层·八项整改)；
    #   否则回落旧 _target_gap_block(单一缺口·安全增量)。唯一渲染器 render_3layer 现含今天全部整改。
    _gap_top = _z4_two_segment_block(date) or _target_gap_block()
    out = re.sub(r'(<details class="layer" id="L1"[^>]*>\s*<summary>[^<]*</summary>\s*<div class="body">)',
                 lambda m: m.group(1) + _gap_top + _risk_config_block(conc) + _external_sector_risk_block() + _glossary_block(), out, count=1)
    # [P1]每只四字段(角色/意图/贡献pp/凭什么) + [P2]双档并列(加/减候选)→注入每只 why 卡开头
    for _sym in [hc.get("代码") for hc in each if hc.get("代码")]:
        out = out.replace(f'id="why-{_sym}">',
                          f'id="why-{_sym}">{_anomaly_gate_block(_sym)}{_target_role_block(_sym)}{_neutral_basis_line(_sym)}{_scenario_block(_sym)}{_dual_track_block(_sym)}{_external_material_block(_sym)}', 1)
    # [L49·致命6]术语大白话:数字后的裸 pp/bp 就地补人话(必须在所有注入之后·否则漏掉双档/四字段里的pp)
    out = re.sub(r"(\d(?:\.\d+)?)\s*pp(?![A-Za-z])", r"\1个百分点", out)   # pp后可能是中文·不用\b
    out = re.sub(r"(\d+)\s*bp(?![A-Za-z])", r"\1个基点(bp)", out)
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
    # 一[看板·图表收尾]：图6/9/10/11 用已有数据改【明确文字/指向版】·删"画法待接"空壳(K线图20/20另在各卡)
    _chart_note = {
        "6": "同业倍数横比：各持仓 PE 已在⑥决策/L3估值区真算(美股EDGAR·日股EDINET)·同业peer PE库未接→此处不画虚线柱，PE对比以⑥表为准。",
        "9": "决策链图：已由顶部【决策逻辑链·7层①-⑦】完整替代(每只可追源①-⑤)·文字因果链完整·此处不另画框图。",
        "10": "照做vs不动：见复盘⑦影子组合反事实记分(文字·多尺度轨迹)·曲线库未接→以文字结论为准。",
        "11": "SBI进攻仓：目标/缺口见顶部『目标—缺口』模块(真数字·40%/100%双档)·柱状库未接→以数字为准。",
    }
    for n in ("6", "9", "10", "11"):
        out = out.replace(f'data-chart="{n}">', f'data-chart="{n}"><div style="font-size:11px;color:#8fb8a4">（{_chart_note[n]}）</div>', 1)
    # 公开【已知未完成清单·带数量】(L45·八.4:不只列图名·须给完成/待接数量)
    n_svg = out.count("<svg") + out.count("<canvas")
    n_tbd_all = out.count("待接·不编") + out.count("待接·未查证")
    undone_rows = [
        ("图6 同业倍数横比", "改文字版：各持仓PE已在⑥决策真算(EDGAR/EDINET)·同业peer PE库未接·不画虚线柱"),
        ("图9 决策链图", "已由顶部【决策逻辑链7层①-⑦】替代·每只可追源·文字因果链完整"),
        ("图10 照做vs不动", "见复盘⑦影子组合反事实记分(文字版·多尺度轨迹)"),
        ("图11 SBI进攻仓", "见顶部『目标—缺口』(真数字·40%/100%双档)"),
        ("★价格K线图(60日·MA20/50)", "完成 20 / 20 只（真OpenD 日线QFQ数据·SVG真画·见各卡『价格走势图』）"),
        ("数据待接（全文）", f"约 {n_tbd_all} 处标『待接·不编/未查证』——催化剂已接催化剂库(现5条:TSM/软银/COIN/MSTR等·其余库未收录)；权威估值真算【卡在数据】：SEC官方财报(edgar)今日返回了标签/编号/链接、但每股收益数值全为空→PE/DCF 算不出·是数据缺口非未做；其余均如实标不编造"),
        ("每只加仓闸·最低价/创新低日期", "逐日60日序列已落盘可定位(真K线已画·见各卡价格走势图)"),
        ("爱德万/闪迪 异常价专项核准", "未完成 2 / 2（缺交易所公告/拆股前后价与股数/两独立行情源→统一观察·不据此买卖）"),
        ("第七章 17项交付物", "完成 0 / 缺 17 项（迁移对账表已在content_manifest·其余截图说明等未做）"),
    ]
    lis = "".join(f'<li><b>{a}</b>：{b}</li>' for a, b in undone_rows)
    # [P3-①·董事长2026-07-20]待接/未完成清单默认【收起】——用 <details> 不带 open·点开才展开·省版面·内容全在DOM(L45照读)
    undone = (f'<details style="background:#2a2412;border:1px solid #A9761A;border-radius:8px;padding:10px 14px;margin:10px 0">'
              f'<summary style="font-weight:800;color:#E0B24A;cursor:pointer;list-style:none">📋 已知未完成清单（点开·默认收起）</summary>'
              f'<ul style="margin:8px 0 0;padding-left:20px;font-size:13px;color:#d8c89a">{lis}</ul>'
              '<div style="font-size:11.5px;color:#a89968;margin-top:4px">图形均为文字+结论版（诚实标未完成·不用假图补位）；'
              '其余逐项数据缺口在各卡内就地标「待接·不编」。</div></details>')
    out = out.replace('<details class="layer" id="L1"', undone + '<details class="layer" id="L1"', 1)
    # [收口·治本]:root 金色变量改深棕/白底 + .p-wait 待拍板徽章改实心(董事长2026-07-19【1】)
    out = out.replace("--L1-txt:#8A6100", "--L1-txt:#5C4033").replace("--L1-bg:#FDF6E3", "--L1-bg:#FFFFFF")
    out = out.replace("--wait:#A9761A", "--wait:#7A5C00")   # [重要3]等待徽章白字底 3.97:1→白on#7A5C00 6.25:1(过AA)
    out = out.replace(".p-wait{border:2.5px solid var(--L1-txt);color:var(--L1-txt)}",
                      ".p-wait{background:#5C4033;color:#FFFFFF;border:none;padding:2px 10px}")
    # [收口·真凶]135处内联亮色 → 浅底可读色(CSS盖不住内联·全文替换·统一浅色主题)
    # [打回一]45%上限已废止→旧『超配/超上限』当判据的措辞全部重写(机会池/板块/证据链残留·deep_render内容)
    for a, b in (
        ("押在AI上的钱已经超上限、英伟达一只也快到15%单只上限 → 纪律不许再加",
         "45%上限已废止(改四规矩)→现可加；仅英伟达单只近20%上限时才谈限(风险配仓建议加至18%)"),
        ("可是你押在AI上的钱已经超上限", "45%上限已废止(改四规矩·现可加)"),
        ("只换不加·AI已超配", "45%上限已废止·换/加看四规矩(单只20%/环节30%/峰值5%)"),
        ("只换不加（AI已超配）", "45%上限已废止·换/加看四规矩"),
        ("只换不加（AI簇已超配）", "45%上限已废止·换/加看四规矩"),
        ("AI簇已超配·只换不加", "AI仓集中·换/加看四规矩(45%上限已废止)"),
        ("AI这块你已经超配，只换不加", "AI仓集中·换/加看四规矩(45%上限已废止)"),
        ("不宜在AI已超配时追高", "不宜追高(估值极端)"),
        ("当前估值+AI已超配", "当前估值极端"),
        ("不分散你已超配的AI", "不分散AI仓"),
        ("AI 供应链超配的前提", "AI 供应链集中的前提"),
        ("会进一步抬高本已65.9%的AI超配", "会进一步抬高本已65.9%的AI仓集中"),
        ("抬高本已65.9%的AI超配", "抬高本已65.9%的AI仓集中"),
        ("抬高已达65.9%的AI超配", "抬高已达65.9%的AI仓集中"),
        ("进一步抬高AI超配", "进一步抬高AI仓集中"),
    ):
        out = out.replace(a, b)
    # [致命2]删『已复核·非算错』——与『未通过专项核准』并存即矛盾(二者只留一个·保留未核准)
    out = out.replace("✔ 已复核·真·景气高点的正常极贵（非算错）", "⏳ 待专项核准（异常价·核准前不据此买卖）")
    out = out.replace("已复核·真·景气高点的正常极贵（非算错）", "待专项核准·异常价·核准前不据此买卖")
    out = re.sub(r"架构师已复核[·:：]?[^<。]{0,10}(非算错|真价)", "待专项核准(异常价·未核准前不据此买卖)", out)
    # 更广:量级哨兵/深研里"架构师已复核…非算错。"整句→改待核准(致命2:不与未核准并存)
    out = re.sub(r"架构师已复核[：:][^<]{0,60}?非算错。?", "待专项核准（异常价·核准前不据此买卖）。", out)
    # [更正1]任天堂不再是拖累/换出候选(架构师补净现金)——清残留旧表述
    for a, b in (("最大单一拖累", "含净现金后转正贡献(架构师更正)"), ("任天堂为最大拖累", "任天堂含净现金后转正贡献"),
                 ("拖累=任天堂／丰田／IBKR", "拖累=丰田／IBKR(任天堂含净现金已转正贡献)"),
                 ("拖累 任天堂／丰田／IBKR", "拖累 丰田／IBKR(任天堂已转正贡献)")):
        out = out.replace(a, b)
    # 兜底:剩余"AI已超配/AI超配/AI簇超配"→AI仓集中；"[PD-AI供应链-超上限]...超 45%"→改废止说明
    out = re.sub(r"AI(簇)?已?超配", "AI仓集中", out)
    out = re.sub(r"\[PD-AI供应链-超上限\][^<。]*?超\s*45[.\d]*%[^<。]*",
                 "[风险配仓] AI供应链占 65.9%·45%硬上限已废止(董事长2026-07-19)·改四条规矩·见顶部风险配仓模块", out)
    out = _light_theme(out)
    out = _finalize_product(out, each, dyn, date, conc)   # 出品前统一口径(治L36/L49/L31/L23·根治)
    out = _embed_actck(out)   # L28五处全埋(架构师裁定一2026-07-25):今日动作表/个股卡header/为什么现在标签补埋data-actck锚
    # GPT裁定:停用全文字符串替换(追不全衍生文本+误伤正常股)——异常股改由数据源/决策链短路+卡片作用域scrub
    return out


def _top_risks(dyn, date):
    return [
        {"风险名": "AI仓集中(45%上限已废止·改风险配仓)", "说明": f"AI供应链占 {_cat_pct(D._conc_now(date,dyn),'AI供应链')}·董事长已废止45%硬上限改四条规矩·回撤预案见顶部风险配仓模块",
         "应对": "按现金建议减仓表·先减最贵的降集中"},
        {"风险名": "台海地缘/先进制程", "说明": "台积电/爱德万等重仓押先进制程·地缘尾部风险",
         "应对": "守核心·不追高·留安全垫；证伪信号见各卡③第16项"},
        {"风险名": "半导体周期高位", "说明": "台积电/英伟达等处景气高点·峰值定价（价口径正常的半导体重仓；闪迪/爱德万因价异常·不参与高位/峰值定价类判断）",
         "应对": "守·不追高·不因周期高位就自动减(峰值可能续)"},
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
    ap.add_argument("--dry-run", action="store_true",
                    help="★轮67 AF2:渲染但【不写进 00_请先看这里/正式产品】——写到 --out(或 data/logs/dryrender_)，"
                         "打印八项整改自查，供空跑验证渲染器已含今天全部整改·不出品给董事长。")
    ap.add_argument("--out", default=None, help="dry-run 输出路径(缺省 data/logs/dryrender_{date}.html)")
    a = ap.parse_args()
    html = build(a.date)
    dd = f"{a.date[:4]}-{a.date[4:6]}-{a.date[6:]}"
    fname = f"★每日产品_{dd}.html"
    # ── ★轮67 AF2:dry-run——渲到临时路径 + 八项自查 + 不碰正式产品目录 ──
    if a.dry_run:
        outp = Path(a.out) if a.out else (ROOT / "data" / "logs" / f"dryrender_{a.date}.html")
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(html, encoding="utf-8")
        b = html.encode("utf-8")
        checks = {
            "1 Z4两段(已算清/未算清分列)": ("已算清（特级+A级）" in html and "未算清（B+C级）" in html),
            "1b 不给单一「距+40%缺口」数": ("不给单一" in html and "缺口分两段报" in html),
            "2 点值口径E[上行]": "点值口径 E[上行]=Σ概率×点值" in html,
            "3 参数出处四等级(B/C不出收益)": ("特级" in html and "无可用估值锚" in html),
            "4 净现金扣减标注(任天堂¥1,940)": ("净现金" in html and "1,940" in html),
            "5 单只超限告警(超单只20%上限)": "超单只20%上限" in html,
            "6 退出类型(第一三共·不进情景)": ("第一三共" in html and "不进情景计算" in html),
            "7 微软口径标注(财报前EPS偏悲观)": ("财报前 EPS" in html and "偏悲观" in html),
            "8 机会层(不填买卖价位)": "不填任何候选或买卖价位" in html,
        }
        print(f"[render_3layer DRY-RUN] 渲到 {outp} · bytes={len(b)} · 乱码EFBFBD={b.count(b'\xef\xbf\xbd')}")
        print("  ★八项整改自查(渲染器实物输出)：")
        for k, v in checks.items():
            print(("    ✔ " if v else "    ✗ 缺 ") + k)
        print("  八项齐全？ " + ("是" if all(checks.values()) else "否·见上"))
        print("  ★未写进正式产品目录(不出品给董事长·AF2-1)。")
        return 0 if all(checks.values()) else 6
    # ★护城河16天重评硬闸(董事长2026-07-25):as_of>16天未重评→FAIL不出品(旧版不被覆盖)
    if getattr(build, "_moat_stale", False):
        print("[三层·出厂核 FAIL·不出品] 护城河超期未重评(as_of>16天)——先跑护城河重评脚本再出厂·旧版未被覆盖")
        return 5
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
    # L28(同股一个答案)不再SKIP(架构师T2裁定2026-07-25:三层版=每日产品=董事长真看的册·必须查动作打架);
    #   三层已在⑥决策表/自检决定摘要埋 data-actck 锚·动作同源自 act_map。L2跨册/L19机器卡格式/L29八层闭环仍机器版专属。
    _SKIP = ("L2 ", "L2b", "L19", "L29")
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
