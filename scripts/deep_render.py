#!/usr/bin/env python3
"""深度完整产品·实时自动渲染器（架构升级 2026-07-15）· 只读不下单

目标：每次跑用【实时数据】现生成完整深度版，达手工样板(完整产品_{date}_深度版.html)的深度与结构。
手工样板仅作目标样板·非数据源。输出写机器名 完整产品_{date}_机器版.html，永不覆盖手工 _深度版.html。

数据源（缺不编·缺哪只标待接/待建判断包）：
  · 深研  ← 00_请先看这里/个股判断包/个股判断包_*.html（按 symbol 映射抽:一句话结论/生意/护城河/真数据/对估值/风险/决策）
  · 右栏6块尺 ← 右栏_*.html body（第六部分折叠）
  · 动态 ← production_{date}.json(价/落哪区/动作/质量关) + daily_{date}.json(五层/VIX/利率/板块) + 集中度
  · 档案 ← holdings_true(股数/成本·四账户·缺不编) + ma_levels(20/50/200均线·仅趋势参考不作买卖线)
价位只看估值(便宜位/偏贵位)；均线只作趋势参考(总则)。
"""
from __future__ import annotations
import argparse, glob, html, json, re
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "00_请先看这里" / "个股判断包"

def esc(v: Any) -> str: return html.escape("" if v is None else str(v))
def rj(p: Path) -> dict:
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return {}

# ── symbol → 个股判断包文件（按 ticker token 匹配文件名·不锚死名单：glob+含token） ──
def _token(sym: str) -> str:
    return sym.split(".")[-1].upper()   # US.NVDA→NVDA, JP.4568→4568

def find_pack(sym: str, name: str) -> Path | None:
    tok = _token(sym)
    for p in sorted(PACK_DIR.glob("个股判断包_*.html")):
        stem = p.stem.upper()
        if tok in stem or (name and name in p.stem):
            return p
    return None

# ── 判断包抽取器：清标签→按小标题切段 ──
def _plain(htmltext: str) -> str:
    t = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', htmltext, flags=re.S)
    t = re.sub(r'<[^>]+>', '\n', t)
    for a, b in [('&lt;','<'),('&gt;','>'),('&amp;','&'),('&quot;','"'),('&#39;',"'"),('&nbsp;',' ')]:
        t = t.replace(a, b)
    return re.sub(r'[ \t]+', ' ', t)

def extract_pack(path: Path) -> dict[str, str]:
    """从判断包抽:一句话结论/生意/护城河/真数据/对估值/风险/决策综合。缺段→''。"""
    raw = _plain(path.read_text(encoding="utf-8"))
    text = "\n".join(ln.strip() for ln in raw.splitlines() if ln.strip())
    def grab(start_kw, stop_kws, frm=0):
        i = text.find(start_kw, frm)
        if i < 0: return ""
        j = len(text)
        for s in stop_kws:
            k = text.find(s, i + len(start_kw))
            if k > -1: j = min(j, k)
        return re.sub(r'\s*\n\s*', ' ', text[i + len(start_kw):j].strip(" ：:·\n")).strip()
    # 各段限定在其父区块内(避免顶部'护城河 8·宽'表头行/校正说明被误抓)
    deep_i = text.find("底层深挖")       # 生意/护城河/真数据 只在此之后抓
    upper_i = text.find("上层对比")
    moat_i = text.find("护城河", deep_i if deep_i > -1 else 0)  # 真数据数据段在护城河之后(跳过表头'底层深挖+真数据'里的'真数据')
    # R5：跨字段标签切除(治MSTR/伊藤忠串字段)——任一段遇到别的字段标签词即截断，不串
    _OTHER = ["一句话结论", "底层深挖", "上层对比", "对世界观", "对估值", "对组合",
              "决策合理性", "决策把关", "综合：", "缺口", "来源（", "来源：", "拍板人"]
    def _cut(s: str) -> str:
        if not s:
            return s
        # WebSearch 来源括注:闭合的删括注(保留前后正文·治第一三共'（WebSearch·很新）'被误吞)；未闭合的删到尾(治微软'财务（WebSearch'截断)
        s = re.sub(r'（WebSearch[^）]*）', '', s)
        s = re.sub(r'（?WebSearch[^）]*$', '', s)
        cut = len(s)
        for lb in _OTHER:
            k = s.find(lb)
            if k > 0:
                cut = min(cut, k)
        s = s[:cut].strip(" ：:·、，。\n")
        # R5：去尾部半截残词(切点前若留下句末标点后的短残词，如'…客户。财务'→'…客户。')
        s = re.sub(r'([。！？；])[^。！？；]{1,6}$', r'\1', s)
        return s.strip(" ：:·、，\n")

    # R5 风险(退出条件)：段头锚定——只认专门"风险（…)"或独占一行"风险"，排除"风险最高/经营分散风险"词内命中
    def _risk_section() -> str:
        m = re.search(r'风险（[^）]*）', text) or re.search(r'(?:^|\n)风险(?=\n)', text)
        if not m:
            return ""     # 无专门风险段 → 退出条件缺(交由 render 标未完成)
        start = m.end()
        j = len(text)
        for s in ("决策合理性", "决策把关", "组合维度", "缺口", "来源", "→ 综合", "拍板人"):
            k = text.find(s, start)
            if k > -1:
                j = min(j, k)
        return re.sub(r'\s*\n\s*', ' ', text[start:j].strip(" ：:·\n")).strip()

    return {
        "一句话结论": _cut(grab("一句话结论", ["底层深挖", "上层对比"])),
        "生意": _cut(grab("生意", ["护城河", "真数据", "上层对比"], frm=deep_i if deep_i > -1 else 0)),
        "护城河": _cut(grab("护城河", ["真数据", "上层对比", "风险"], frm=deep_i if deep_i > -1 else 0)),
        "真数据": _cut(grab("真数据", ["上层对比", "风险", "决策", "缺口", "来源"], frm=moat_i if moat_i > -1 else 0)),
        "对估值": _cut(grab("对估值", ["对组合", "风险", "决策"], frm=upper_i if upper_i > -1 else 0)),
        "风险": _cut(_risk_section()),
        "决策": _cut(grab("综合", ["缺口", "来源"]) or grab("决策合理性把关", ["缺口", "来源"])),
    }

# ── 动态数据 ──
# ── 件一：逐股价格"数据真实时点"标签（不许一个 data_date 盖全部市场） ──
_MKT_NAME = {"US": "美股", "JP": "日股", "HK": "港股", "CN": "A股", "CC": "加密"}
_STATE_TXT = {"PRE_MARKET_BEGIN": "盘前", "PRE_MARKET_END": "盘前", "MORNING": "盘中", "AFTERNOON": "盘中",
              "CLOSED": "收盘", "AFTER_HOURS_BEGIN": "盘后", "AFTER_HOURS_END": "盘后",
              "NIGHT_OPEN": "夜盘", "REST": "午休", "OVERNIGHT": "夜盘",
              # 甲1：WAITING_OPEN 是机器话，漏到过页头 → 给人话
              "WAITING_OPEN": "开盘前", "SUSPENSION": "停牌", "STOP_TRADING": "停牌"}
_FIELD_TXT = {"last_price": "收盘", "pre_price": "盘前", "after_price": "盘后", "overnight_price": "夜盘"}

def price_stamp(sym: str, date: str) -> str:
    """返回该只现价的真实时点标签，如「美股·07-15盘前」「日股·07-16收盘」。缺→标待接不编。"""
    mkt = _MKT_NAME.get(str(sym).split(".")[0], str(sym).split(".")[0])
    dd = st = fld = None
    try:
        for h in (rj(ROOT / "data" / "accounts" / f"holdings_true_{date}.json").get("holdings") or []):
            if h.get("symbol") == sym:
                dd = h.get("price_data_date"); st = h.get("price_market_state"); break
    except Exception:
        pass
    try:
        for x in (rj(ROOT / "data" / "holdings" / f"holdings_review_{date}.json").get("reviews") or []):
            if x.get("symbol") == sym:
                fld = x.get("used_field")
                dd = dd or x.get("data_date")
                break
    except Exception:
        pass
    if not dd:
        return f"{mkt}·价时点待接（未取到行情数据日·不编）"
    tag = _STATE_TXT.get(str(st), "") or _FIELD_TXT.get(str(fld), "") or "最近可得"
    d = str(dd)
    dshort = f"{d[5:7]}-{d[8:10]}" if len(d) >= 10 and "-" in d else d
    same = (d.replace("-", "") == date)
    note = "" if same else "·非当日"
    return f"{mkt}·{dshort}{tag}{note}"

# ── 件二：佐证层（总则第九条三·系统证据链为主·湖水/老雷/TXT研报只作印证或挑战·严禁反客为主） ──
_CORRO_CACHE = {}
def _corro() -> dict:
    if "d" not in _CORRO_CACHE:
        try:
            _CORRO_CACHE["d"] = rj(ROOT / "data" / "analysis" / "corroboration.json")
        except Exception:
            _CORRO_CACHE["d"] = {}
    return _CORRO_CACHE["d"]

_VERDICT_COLOR = {"印证": "#7ee0a0", "挑战": "#ffb454", "佐证料待接": "#c9a86a"}


def _corro_age(date: str) -> tuple[int, str]:
    """甲5：佐证料距当日多少天——每日现算·不写死。返回(最旧料天数, 最新料as_of)。"""
    c = _corro()
    srcs = c.get("sources") or []
    try:
        today = datetime.strptime(date, "%Y%m%d").date()
    except Exception:
        return 0, ""
    ages = []
    for s in srcs:
        try:
            d = datetime.strptime(str(s.get("as_of", ""))[:10], "%Y-%m-%d").date()
            ages.append(((today - d).days, str(s.get("as_of"))))
        except Exception:
            continue
    if not ages:
        return 0, ""
    ages.sort(reverse=True)
    return ages[0][0], min(a[1] for a in ages)


def corro_staleness_banner(date: str) -> str:
    """甲5：佐证料过期→醒目警条(不是小字脚注)。天数现算·超30天转橙色告警。"""
    days, oldest = _corro_age(date)
    if not days:
        return ""
    hot = days > 30
    bg, bd, col = ("#3a2410", "#c47a1e", "#ffb454") if hot else ("#12261f", "#4f9e7f", "#7ee0a0")
    return (f'<div class="card" style="background:{bg};border-color:{bd};border-width:2px">'
            f'<div style="font-size:15px;font-weight:700;color:{col}">'
            f'{"⚠ 佐证料已放了 " + str(days) + " 天（不是今天的料）" if hot else "佐证料 " + str(days) + " 天内·较新"}</div>'
            f'<div style="font-size:13px;margin-top:4px;color:#e6eef5">'
            f'下面每处「佐证」栏里的<b>湖水／老雷</b>观点，最早一份是 <b>{esc(oldest)}</b> 整理的、'
            f'距今天 <b>{days}</b> 天。'
            f'{"这么旧的料<b>只能当方向性参考</b>，不能当今天的证据——" if hot else ""}'
            f'今天的结论一律以左栏<b>系统证据链</b>（当日实时行情+当日新闻）为准。'
            f'佐证只用来「印证」或「挑战」系统判断，<b>永远不盖过系统判断</b>（总则第九条三）。</div></div>')

def corro_box(key: str, kind: str = "layer") -> str:
    """给一条系统判断挂佐证栏。kind=layer→by_layer(模糊匹配节点名)；kind=symbol→by_symbol。
    有料→印证/挑战+来源；无料→佐证料待接·从接入起用（不编不凑）。佐证绝不盖过系统判断。"""
    c = _corro()
    if not c:
        return ('<div class="meta" style="color:#c9a86a;font-size:11.5px;margin-top:3px">'
                '佐证（第九条三）：<b>佐证料待接</b>（corroboration.json 缺·不编）</div>')
    e = None
    if kind == "symbol":
        e = (c.get("by_symbol") or {}).get(key)
    else:
        for k, v in (c.get("by_layer") or {}).items():
            if k in str(key) or str(key) in k or any(w and w in str(key) for w in k.split("·")):
                e = v
                break
    if not e:
        # uncovered_note 自带完整括号("佐证料待接·从接入起用（现有料[…]未覆盖该标的·不编不凑）")，
        # 外面【不许】再套一层"（…）"——否则括号不闭合、"佐证料待接"还重复两遍。
        _note = str(c.get("uncovered_note", "现有料未覆盖·不编不凑"))
        _note = re.sub(r"^佐证料待接·从接入起用\s*", "", _note)   # 去掉与前半句重复的那截
        return ('<div class="meta" style="color:#c9a86a;font-size:11.5px;margin-top:3px">'
                f'佐证（第九条三·只作印证/挑战·不盖系统判断）：<b>佐证料待接·从接入起用</b>'
                f'——{esc(_note)}</div>')
    vd = str(e.get("verdict", "佐证料待接"))
    col = _VERDICT_COLOR.get(vd, "#c9a86a")
    bits = []
    if e.get("hushui"):
        bits.append(f'<b>湖水</b>：{esc(str(e["hushui"]))}')
    if e.get("laolei"):
        bits.append(f'<b>老雷</b>：{esc(str(e["laolei"]))}')
    tail = []
    if e.get("consistency"):
        tail.append(f'一致度：{esc(str(e["consistency"]))}')
    if e.get("closer"):
        tail.append(f'谁更接近：{esc(str(e["closer"]))}')
    if e.get("watch"):
        tail.append(f'观察指标：{esc(str(e["watch"]))}')
    if e.get("note"):
        tail.append(esc(str(e["note"])))
    return ('<div class="meta" style="font-size:11.5px;margin-top:3px;color:#9db0c2;border-left:3px solid ' + col + ';padding-left:7px">'
            f'佐证（第九条三·只作印证/挑战·<b>不盖系统判断</b>）：<b style="color:{col}">{esc(vd)}</b>'
            + ('｜' + '　'.join(bits) if bits else '')
            + ('<br>' + '｜'.join(tail) if tail else '')
            # 甲4：这句"料已N天旧"全册只在①册顶部的警条里说一次，别层层卡卡重复(治刷屏)
            + f'<br><span style="color:#8ea3b6">来源：{esc(str(e.get("source", "待接")))}'
            + '（非当日料·当日结论以左栏系统证据链为准）</span></div>')


# 甲5：当日现算的佐证料天数(build 起手写入·供每条佐证栏尾注引用·不写死)
_CORRO_AGE: dict = {}

# ── 甲6：财报日历驱动·出报日该只卡顶强制横幅(earnings_calendar.json 现算·不写死名单) ──
_ECAL_CACHE: dict = {}


def _ecal(date: str) -> dict:
    """symbol → 当日财报事件(只认日历里 report_date==当日的)。"""
    if date in _ECAL_CACHE:
        return _ECAL_CACHE[date]
    d = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    out = {}
    try:
        cal = rj(ROOT / "data" / "valuation" / "earnings_calendar.json")
        for e in cal.get("events", []) or []:
            if str(e.get("report_date", ""))[:10] == d:
                out[str(e.get("symbol"))] = e
    except Exception:
        out = {}
    _ECAL_CACHE[date] = out
    return out


def earnings_banner(sym: str, date: str, dyn: dict) -> str:
    """出报日→该只卡顶部强制横幅。已接到新财报数→报"已更新"；没接到→老实说"数据更新中·②表和估值还是上一季的"。"""
    e = _ecal(date).get(sym)
    if not e:
        return ""
    fiscal = esc(str(e.get("fiscal", "本季")))
    sess = esc(str(e.get("session", "")))
    reported = e.get("reported_on")
    # 该只的②财报表最新一行覆盖到哪个期(现算·判断新数到没到)
    got = False
    try:
        dc = _load_deep_card(sym)
        rows = ((dc or {}).get("block2_financials", {}) or {}).get("rows", []) or []
        last = " ".join(str(rows[-1].get(k, "")) for k in ("fy", "period", "as_of")) if rows else ""
        got = str(e.get("fiscal", "")).replace("2026Q2", "Q2 2026") in last or "Q2 2026" in last or "2Q26" in last
    except Exception:
        got = False
    val = (dyn.get("valr", {}) or {}).get(sym, {})
    val_wait = str(val.get("status", "")) == "待接真源"
    if reported and got:
        return ('<div class="card" style="background:#12261f;border:2px solid #4f9e7f;margin-bottom:6px">'
                f'<div style="font-size:16px;font-weight:700;color:#7ee0a0">📣 今日出财报（{fiscal}·{sess}）·新数已接入</div>'
                '<div style="font-size:13px;margin-top:3px">下面②多年财报表与⑤估值都<b>已按今天这份新财报重算</b>。</div></div>')
    return ('<div class="card" style="background:#3a2410;border:2px solid #c47a1e;margin-bottom:6px">'
            f'<div style="font-size:16px;font-weight:700;color:#ffb454">📣 今天出财报（{fiscal}{"·" + sess if sess else ""}）·数据更新中</div>'
            '<div style="font-size:13px;margin-top:4px;color:#e6eef5">'
            f'这只<b>今天（{esc(date[:4])}-{esc(date[4:6])}-{esc(date[6:])}）刚出{fiscal}财报</b>，但新数字<b>还没接进本卡</b>——'
            f'下面②多年财报表最新只到<b>上一季</b>、⑤估值{"也还是<b>待接</b>" if val_wait else "也还是<b>按上一季的数算的</b>"}。'
            '<br><b style="color:#ffb454">所以：本卡今天的估值结论请先别当准。</b>'
            '等新财报数字接进来（需要把真实的季度财务数录进估值输入表）后会自动重算——'
            '缺真源就不编数，这是规矩。</div></div>')

# ══ 分册架构(董事局工单)：5册·同源页眉·跨册相对路径锚·闭环图。纯移搬·一字不删 ══
# ══ 乙1：统一前缀+日期，让5册在G盘按名排序时【连续相邻】且置顶醒目 ══
# ★前缀→排到目录最前；「每日产品_日期_序号_」→同日5册必定挨在一起、序号即阅读顺序。
VOL_PREFIX = "★每日产品"


def _dd(date: str) -> str:
    return f"{date[:4]}-{date[4:6]}-{date[6:]}"


def VOL(date: str, n: int) -> str:
    return {1: f"{VOL_PREFIX}_{_dd(date)}_1_总览闭环.html",
            2: f"{VOL_PREFIX}_{_dd(date)}_2_持仓深研.html",
            3: f"{VOL_PREFIX}_{_dd(date)}_3_机会池.html",
            4: f"{VOL_PREFIX}_{_dd(date)}_4_记分卡.html",
            5: f"{VOL_PREFIX}_{_dd(date)}_5_右栏6尺.html"}[n]

# ②持仓深研册按逻辑拆子册(每册<300KB·绝不删内容·按组合角色分组)
VOL2_SUBS = [("2a", "AI主线仓", ["US.NVDA", "US.MSFT", "US.AVGO", "US.TSM", "JP.6857", "JP.9984", "US.META", "US.SNDK"]),
             ("2b", "防御分散仓", ["JP.4568", "JP.8766", "JP.6758", "JP.7203", "JP.8001", "JP.7832", "JP.7974"]),
             ("2c", "加密簇与金融仓", ["US.MSTR", "US.COIN", "US.CRCL", "US.IBKR"])]

def VOL2(date: str, sub: str) -> str:
    # 2a/2b/2c 排在 "_2_" 与 "_3_" 之间 → 与其余4册连续相邻
    return f"{VOL_PREFIX}_{_dd(date)}_2{sub[-1]}_持仓深研_{dict((s, n) for s, n, _ in VOL2_SUBS)[sub]}.html"

def _sub_of(sym: str) -> str:
    for s, _n, syms in VOL2_SUBS:
        if sym in syms:
            return s
    return "2a"

_LAYER_SLUG = {"总命题": "world", "总闸": "fedgate", "战略": "strategy",
               "手段": "means", "资金轮动": "capital", "板块": "sector"}
def layer_slug(node: str) -> str:
    for k, v in _LAYER_SLUG.items():
        if k in str(node):
            return v
    return "layer"

def L1(date: str, anchor: str = "") -> str:
    return VOL(date, 1) + (("#" + anchor) if anchor else "")
def L2(date: str, anchor: str = "") -> str:
    """持仓深研链：按 symbol 定位到它所在的子册(2a/2b/2c)，锚点不跨册断。"""
    if anchor.startswith("stock-"):
        return VOL2(date, _sub_of(anchor[6:])) + "#" + anchor
    return VOL2(date, "2a") + (("#" + anchor) if anchor else "")
def L5(date: str, anchor: str = "") -> str:
    return VOL(date, 5) + (("#" + anchor) if anchor else "")

def _a(href: str, text: str, color: str = "#8fd6ff") -> str:
    return f'<a href="{href}" style="color:{color};text-decoration:underline dotted">{text}</a>'

def _mkt_oneline(date: str) -> str:
    """甲1：页头那一行小字——各市场的价到底是"今天的"还是"昨晚收盘"。按真数据现算·不写死。"""
    try:
        hts = rj(ROOT / "data" / "accounts" / f"holdings_true_{date}.json").get("holdings") or []
    except Exception:
        return "各市场价格时点：待接（缺当日持仓真值·不编）"
    agg = {}
    for h in hts:
        sym = str(h.get("symbol") or "")
        mkt = _MKT_NAME.get(sym.split(".")[0], sym.split(".")[0])
        dd = str(h.get("price_data_date") or "")
        st = _STATE_TXT.get(str(h.get("price_market_state")), "")
        if dd:
            agg.setdefault(mkt, (dd, st))
    if not agg:
        return "各市场价格时点：待接（无行情数据日·不编）"
    bits = []
    for mkt, (dd, st) in sorted(agg.items()):
        if dd.replace("-", "") == date:
            bits.append(f"<b>{esc(mkt)}＝今天的价</b>（{esc(dd)}{esc(st)}）")
        else:
            # 只陈述事实"价停在哪天的哪个时点"，不替市场编"开没开盘"(会说错·如日股此刻正开着)
            bits.append(f"<b>{esc(mkt)}＝{esc(dd)}{esc(st) or '收盘'}的价</b>（不是今天的）")
    return "　｜　".join(bits) + "　<span style='color:#8ea3b6'>（每只价旁都标了它自己的时点）</span>"


def _price_asof_note(date: str) -> str:
    """头部总说明：按市场汇总各自价格真实时点（不许一个 data_date 盖全部市场）。"""
    try:
        hts = rj(ROOT / "data" / "accounts" / f"holdings_true_{date}.json").get("holdings") or []
    except Exception:
        return ('<div style="font-size:12px;color:#ffb454;font-weight:400">价格时点说明：待接（holdings_true 缺·不编）</div>')
    agg = {}
    for h in hts:
        sym = str(h.get("symbol") or "")
        mkt = _MKT_NAME.get(sym.split(".")[0], sym.split(".")[0])
        dd = str(h.get("price_data_date") or "")
        st = _STATE_TXT.get(str(h.get("price_market_state")), str(h.get("price_market_state") or ""))
        if not dd:
            continue
        agg.setdefault((mkt, dd, st), 0)
        agg[(mkt, dd, st)] += 1
    if not agg:
        return '<div style="font-size:12px;color:#ffb454;font-weight:400">价格时点说明：待接（无行情数据日·不编）</div>'
    parts = []
    for (mkt, dd, st), n in sorted(agg.items()):
        same = (dd.replace("-", "") == date)
        parts.append(f'<b>{esc(mkt)}</b> {esc(dd)}{esc(st)}（{n}只{"·当日" if same else "·非当日"}）')
    return ('<div style="font-size:12px;color:#ffb454;font-weight:400;margin-top:4px">'
            '⚠ 各市场价格真实时点（<b>data_date 只是本产品的生产日、不代表每只价都是当日</b>）：'
            + "；".join(parts)
            + '。<b>美股为最近美股交易日的盘前/收盘价</b>——JST 晚间美股尚未开盘（22:30 开），次日实时价以当日 OpenD 扫描为准；'
            '日股/港股/A股同理按各自市场时点标注。每只现价旁均有［市场·日期时点］标签，缺则标待接不编。</div>')

def load_dynamic(date: str) -> dict:
    prod = rj(ROOT / "data" / "reports" / f"production_{date}.json")
    daily = rj(ROOT / "data" / "evidence_chain" / f"daily_{date}.json")
    ma = {x["symbol"]: x for x in (rj(ROOT / "data" / "holdings" / f"ma_levels_{date}.json").get("holdings") or [])}
    ht = {h["symbol"]: h for h in (rj(ROOT / "data" / "accounts" / f"holdings_true_{date}.json").get("holdings") or [])}
    # 估值单一源(valuation_results·分类型精算·R1 final.valuation 只从这里取)
    valr = {r["symbol"]: r for r in (rj(ROOT / "data" / "valuation" / f"valuation_results_{date}.json").get("results") or []) if r.get("symbol")}
    return {"prod": prod, "daily": daily, "ma": ma, "ht": ht, "valr": valr, "date": date}


# ── R1 决策对象唯一化：每标的一个 final(quality/valuation/action/confidence/reason/invalidation) ──
# 标题·正文·摘要·闭环·PDCA 一律只引用 final；判断包只供定性深研素材，其估值/动作结论一概不渲染(治B3内部冲突)。
def _clean_placeholder(s: str) -> str:
    # 去判断包里未解析的现算占位符(B3②)，避免把"(见左栏仓位集中度摘要现算)"印进正文
    return re.sub(r'[（(]\s*见左栏[^）)]*[现算摘要][^）)]*[）)]', '（AI敞口见第三部分集中度现算）', s or "")

def _scrub_pack_prices(s: str) -> str:
    """R4返修：只抹【当前交易价】类字段(现价/股价/买入价/卖出价/止损价/低吸价 + 币种数字)——价位只从production。
    绝不动财报数字(营收/EPS/FCF/利润/关税额·$B/亿/万亿)和分析师目标价叙述(历史研究·带as_of)。
    治原抹除器把财报量级(营收/利润)误抹的回归；防呆:植入'现价约$99999'仍被抹(现价标签+数字)。"""
    if not s:
        return s
    # 仅带【当前交易价标签】+ 币种数字 才抹(移除原过宽的目标价/合理区/公允值/约$N回溯逻辑)
    return re.sub(r'(现价|股价|买入价|卖出价|止损价|低吸价)[^，。；、\s]{0,3}[约≈=]?\s*[¥$]\s*[\d,]+\.?\d*\s*[kK万亿]?',
                  '（现价以本卡档案·当日production为准）', s)


def _scrub_valuation_stance(s: str) -> str:
    """R1补：深研只留定性素材，把估值定性词剥离(估值只在'决策条(单一源)'出现)——治软银深研'偏贵/高于公允值三成'与决策条打架。"""
    if not s:
        return s
    # 多字估值短语(安全·优先)
    s = re.sub(r'(现价)?[^，。；、]{0,6}(高于|低于)公允值[^，。；、]{0,8}', '（估值以决策条为准）', s)
    for w in ("合理偏便宜", "偏贵", "偏便宜", "公允值", "估值偏高", "估值偏低"):
        s = s.replace(w, "（估值见决策条）")
    # 独立估值判断字'贵'/'便宜'(仅估值语境·避开 宝贵/昂贵/贵州/贵金属 等)
    s = re.sub(r'(现价|价位|估值|它|该股)([^，。；、]{0,5})(贵|便宜)(?![州族重金])', r'\1\2（估值见决策条）', s)
    s = re.sub(r'[（(]\s*(偏?贵|便宜|偏便宜)\s*[）)]', '（估值见决策条）', s)            # （贵）（便宜）（偏贵）
    s = re.sub(r'(不|很|太|够|偏|更|挺|溢价[^，。；、]{0,8})(贵|便宜)(?![州族重金])', r'\1（估值见决策条）', s)  # 不便宜/很贵/溢价…贵
    s = re.sub(r'(比|较)[^，。；、]{0,24}?(贵|便宜)(一大截|一截)?', '\\1（估值见决策条）', s)   # 比"净币值"贵一大截
    s = s.replace("便宜有便宜的道理", "（估值见决策条）")
    return s

def _audit_financials(data: str, sym: str) -> str:
    """R8 财务数字口径审计：标注疑量级/单位错(缺真源不硬改·待核)。日本大盘股年营收多为万亿级，
    若'营收 ¥N,NNN亿'(N≥1000)标'亿'→疑数字实为十亿円(差一量级)。附审计标注。"""
    notes = []
    for m in re.finditer(r'营收.{0,15}?[¥到]\s*[¥]?\s*([\d,]+(?:\.\d+)?)\s*亿', data):
        try:
            val = float(m.group(1).replace(",", ""))
        except ValueError:
            continue
        if sym.startswith("JP.") and val >= 1000:   # 万亿级公司却标'¥1000+亿'→疑单位/量级
            notes.append(f'⚠财务审计：营收「¥{m.group(1)}亿」疑单位/量级错（该司年营收多为万亿级；数字疑为十亿円→约¥{val/1000:.2f}万亿）·缺官方财报源不硬改·待理解岗核订正')
    return ('<div class="meta" style="color:#ffb454;font-size:12px;margin-top:3px">'
            + " ｜ ".join(esc(n) for n in notes) + "</div>") if notes else ""


def build_final(sym: str, name: str, dyn: dict) -> dict:
    prod_h = next((h for h in dyn["prod"].get("holdings", []) if h.get("symbol") == sym), {})
    qg = prod_h.get("quality_gate", {}) or {}
    v = dyn.get("valr", {}).get(sym, {})
    c = cur(sym)
    # 估值(单一源=valuation_results)：OK→区间+中枢+法+可信度；待接→标待接；退回production label仅作辅助词
    if v.get("status") == "OK":
        valuation_text = (f'{esc(v.get("model_disp","精算"))}·合理区 {c}{fnum(v.get("reasonable_low"))}~{c}{fnum(v.get("reasonable_high"))}'
                          f'·中枢 {c}{fnum(v.get("target"))}（可信度A）')
        valuation_short = f'合理区 {c}{fnum(v.get("reasonable_low"))}~{c}{fnum(v.get("reasonable_high"))}·中枢{c}{fnum(v.get("target"))}'
        valuation_grade = "A·精算"
    else:
        _reason = esc(v.get("reason") or "待接真源")
        valuation_text = f'{esc(v.get("model_disp","按类型"))}·待接（{_reason}）'
        valuation_short = "待接真源"
        valuation_grade = "待接"
    return {
        "symbol": sym, "name": name,
        "quality": f'{esc(qg.get("tier",""))}{esc(qg.get("tier_label","待接"))}',
        "quality_why": _clean_placeholder(esc(qg.get("why", ""))),
        "valuation": valuation_text, "valuation_short": valuation_short, "valuation_grade": valuation_grade,
        "valuation_model": esc(v.get("model_disp", "")), "valuation_type": esc(v.get("type", "")),
        "action": esc(prod_h.get("action", "待接")),
        "confidence": esc(qg.get("tier", "") + "档" if qg.get("tier") else "待接"),
        "reason": _clean_placeholder(esc(prod_h.get("one_line_reason", ""))),
        "price": prod_h.get("price"),
    }

def cur(sym: str) -> str: return "¥" if sym.startswith("JP.") else "$"
def fnum(v):
    try:
        f = float(v); return f"{f:,.0f}" if abs(f) >= 100 else f"{f:,.2f}"
    except (TypeError, ValueError): return None

# ── 单只持仓卡（R1:决策全引 final·深研只留定性素材） ──
# R10③：深研英文样本(过程artifact/普通词)译中或去掉；专有名词/术语缩写(公司/产品/试验/法案/技术)保留不失真
_EN_COMMON = [(r'WebSearch', ''), (r'[Cc]ap[Ee]x', '资本开支'), (r'record', '创纪录'),
              (r'YTD', '年初至今'), (r'App', '应用'), (r'record-high', '创历史新高')]
def _zh_common(s: str) -> str:
    if not s:
        return s
    for tok, zh in _EN_COMMON:
        s = re.sub(r'(?<![A-Za-z])' + tok + r'(?![A-Za-z])', zh, s)
    s = re.sub(r'\s{2,}', ' ', s)
    return s

# R10②：账本①/②/③档 → 高/中/低把握(显式)
def _conf_grade(f: dict) -> str:
    q = str(f.get("quality", "")); c = str(f.get("confidence", ""))
    if "①" in q or "①" in c: return "高把握"
    if "③" in q or "③" in c: return "低把握"
    if "②" in q or "②" in c: return "中把握"
    return "把握待接"

# ══════════ 成品级深度10块渲染(对齐董事长认可样卡)：定性块来自判断包/认可样卡·②财报Code接真源·⑤估值引擎+敏感性 ══════════
DEEP_DIR = ROOT / "data" / "analysis" / "deep_cards"

def _load_deep_card(sym: str, dyn: dict | None = None):
    p = DEEP_DIR / f"{sym}.json"
    if not p.exists():
        return None
    try:
        d = rj(p)
    except Exception:
        return None
    if dyn is not None:
        # 甲2：整卡一次性同步现价(所有块·含②⑤⑥⑨与source_note)→全卡现价唯一
        try:
            d = json.loads(_sync_card_prices(sym, json.dumps(d, ensure_ascii=False), dyn))
        except Exception:
            pass
    return d

# ══ 甲2[P0]：现价全卡唯一 —— 深度卡正文里【写死】的旧价/旧PE/旧贵贱，一律按今日实时价现算 ══
# 根因：deep_cards/*.json 的分析正文里把当时的价写进了句子(如 META"现价约$631、前瞻PE约17~20倍(偏便宜)")，
# 而档案四行与决策条走 production 实时价($687·系统现算"偏贵19%") → 同一张卡两个价、两个相反结论。
# 治法：现价=production 单一真源；由价推出的前瞻PE用引擎的 eps0 现算；由旧价推出的贵/便宜结论
# 一律收敛为"指向本卡⑤估值区间与决策条"(R1单一源·判断口径不变·不删肉)。
_PRICE_RE = re.compile(r"(现价[约]?\s*)([\$¥])\s*([\d,]+(?:\.\d+)?)")
# 乙7：⑤"真实市场参照"里还有两种不带"现价"二字的第三方旧价写法，也得治：
#   ①"TSM收盘$419.48(2026-07-15)"  ②"AVGO约$394(stockanalysis 2026-07)"
# 处理原则(按工单)：要么统一到今日实时价，要么【明确另标它自己的日期+来源】、不许与"现价"混淆。
_3RD_DATED_RE = re.compile(
    r"([A-Z]{2,5})\s*(?:收盘|股价|市价)\s*([\$¥])\s*([\d,]+(?:\.\d+)?)\s*[（(]\s*(\d{4}-\d{2}(?:-\d{2})?)\s*[）)]")
_3RD_SRC_RE = re.compile(
    r"([A-Z]{2,5})\s*约\s*([\$¥])\s*([\d,]+(?:\.\d+)?)\s*[（(]\s*([a-zA-Z]+)\s+(\d{4}-\d{2}(?:-\d{2})?)\s*[）)]")
_FWD_PE_RE = re.compile(r"(?:前瞻PE|前瞻市盈率)\s*约?\s*([\d\.]+)(?:\s*[~～-]\s*([\d\.]+))?\s*倍|约\s*([\d\.]+)\s*倍前瞻")
_CHEAP_RE = re.compile(r"[（(][^（）()]{0,12}(?:偏便宜|偏贵|很便宜|很贵)[^（）()]{0,12}[）)]")


def _price_of(sym: str, dyn: dict):
    for h in (dyn.get("prod", {}) or {}).get("holdings", []) or []:
        if h.get("symbol") == sym:
            return h.get("price")
    return None


def _sync_card_prices(sym: str, blob: str, dyn: dict) -> str:
    """把一张深度卡正文里所有写死的现价→今日实时价(单一源)；前瞻PE→现算；旧贵贱结论→指向单一源。"""
    live = _price_of(sym, dyn)
    if live is None:
        return blob
    c = cur(sym)
    live_s = f"{live:,.2f}".rstrip("0").rstrip(".") if isinstance(live, (int, float)) else str(live)
    stale: list[str] = []

    def _rep_price(m):
        old = m.group(3)
        try:
            if abs(float(old.replace(",", "")) - float(live)) / float(live) > 0.01:
                stale.append(old)
        except Exception:
            pass
        return f"{m.group(1)}{c}{live_s}"

    blob = _PRICE_RE.sub(_rep_price, blob)

    # 乙7：第三方旧价(带日期/带来源) → 换成今日实时价；若与今日价差>1%，把旧价降级成"交叉参考"
    #      并【明确另标它自己的日期+来源】，绝不与"现价"混淆。
    def _rep_dated(m):
        sym_t, cy, old, d = m.group(1), m.group(2), m.group(3), m.group(4)
        try:
            diff = abs(float(old.replace(",", "")) - float(live)) / float(live) > 0.01
        except Exception:
            diff = True
        if not diff:
            return f"{sym_t} 现价{c}{live_s}（今日实时）"
        stale.append(old)
        return (f"{sym_t} 现价{c}{live_s}（今日实时·与档案行同一源）"
                f"；另：{d} 的收盘价是{cy}{old}（<b>那是{d}的旧价·不是现价</b>·仅作交叉参考）")

    def _rep_src(m):
        sym_t, cy, old, src, d = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        try:
            diff = abs(float(old.replace(",", "")) - float(live)) / float(live) > 0.01
        except Exception:
            diff = True
        if not diff:
            return f"{sym_t} 现价{c}{live_s}（今日实时）"
        stale.append(old)
        return (f"{sym_t} 现价{c}{live_s}（今日实时·与档案行同一源）"
                f"；另：第三方{src}在{d}记的是{cy}{old}（<b>那是{d}的旧价·不是现价</b>·仅作交叉参考）")

    blob = _3RD_DATED_RE.sub(_rep_dated, blob)
    blob = _3RD_SRC_RE.sub(_rep_src, blob)

    # 甲5：卡里写"某日收盘价待接"是【写卡当时】没取到价留的坑；今天实时价已经有了→就地填上，
    # 别让同一张卡一边说"待接"、一边在档案行展示 ¥5,961(软银)。
    blob = re.sub(r"[；;、,]?\s*\d{4}-\d{2}-\d{2}\s*收盘价待接",
                  f"；今日实时价{c}{live_s}（见本卡档案行·同一实时源）", blob)
    if not stale:
        return blob
    # 这张卡的正文确实拿旧价说过话 → 前瞻PE按今日价+引擎eps0现算(拿不到eps0就不编、只标)
    eps0 = None
    v = (dyn.get("valr", {}) or {}).get(sym, {}) or {}
    a = v.get("assumptions", {}) or {}
    for k in ("eps0", "normalized_eps", "normal_eps"):
        if isinstance(a.get(k), (int, float)):
            eps0 = a[k]
            break
    if eps0:
        pe_now = float(live) / float(eps0)
        blob = _FWD_PE_RE.sub(f"前瞻PE约{pe_now:.0f}倍（按今天{c}{live_s}现算）", blob)
    else:
        blob = _FWD_PE_RE.sub("前瞻PE（今日现算见本卡⑤估值行）", blob)
    # 旧价推出来的"(偏便宜)/(偏贵)"括注 → 收敛到单一源(判断口径不变:结论本就以⑤/决策条为准)
    blob = _CHEAP_RE.sub("（贵还是便宜以本卡⑤估值区间与顶部决策条为准·那是今天现算的）", blob)
    return blob


# ══ 乙5/乙6：估值数轴（纯HTML/CSS·不引外部库·深浅色都清楚） ══
# 「便宜─合理─贵」三段 + 现价 ▼ 落点。数字全部来自估值引擎单一源(R1)，本组件只负责【画】，不改口径。
HORIZON_NOTE = "这是按公司未来约 1~2 年该值多少算出来的合理价，不是猜下个月的股价"


def _val_axis(sym: str, dyn: dict, mini: bool = False) -> str:
    """返回估值数轴HTML；估值待接→返回空串(由调用方写人话原因·不画假轴)。"""
    v = (dyn.get("valr", {}) or {}).get(sym, {}) or {}
    if str(v.get("status")) != "OK":
        return ""
    lo, mid, hi = v.get("reasonable_low"), v.get("intrinsic"), v.get("reasonable_high")
    px = _price_of(sym, dyn)
    if lo is None or hi is None or mid is None or px is None or hi <= lo:
        return ""
    c = cur(sym)
    # 轴的显示范围：把区间左右各放宽30%，保证现价在轴上看得见
    span = hi - lo
    a0, a1 = lo - span * 0.6, hi + span * 0.6
    if px < a0:
        a0 = px - span * 0.15
    if px > a1:
        a1 = px + span * 0.15
    W = max(a1 - a0, 1e-9)

    def pos(x):
        return max(0.0, min(100.0, (x - a0) / W * 100.0))

    p_lo, p_hi, p_px, p_mid = pos(lo), pos(hi), pos(px), pos(mid)
    # 贵/便宜=与中枢比(与决策条同一口径·只是换个画法)
    gap = (px - mid) / mid * 100.0
    if px < lo:
        verd, col = f"偏便宜（比中间值低 {abs(gap):.0f}%）", "#2f9e5f"
    elif px > hi:
        verd, col = f"偏贵（比中间值高 {gap:+.0f}%）".replace("+", ""), "#d24b4b"
    else:
        verd, col = f"大致合理（比中间值{'高' if gap >= 0 else '低'} {abs(gap):.0f}%）", "#c9922b"
    h = 8 if mini else 16
    fs = 10.5 if mini else 12.5
    bar = (f'<div style="position:relative;height:{h}px;border-radius:{h//2}px;overflow:hidden;'
           f'background:#8a8f96;margin:{2 if mini else 8}px 0 {"9" if mini else "16"}px">'
           f'<div style="position:absolute;left:0;width:{p_lo:.2f}%;height:100%;background:#2f9e5f"></div>'
           f'<div style="position:absolute;left:{p_lo:.2f}%;width:{max(p_hi-p_lo,0.5):.2f}%;height:100%;background:#c9922b"></div>'
           f'<div style="position:absolute;left:{p_hi:.2f}%;right:0;height:100%;background:#d24b4b"></div>'
           # 中枢刻度
           f'<div style="position:absolute;left:{p_mid:.2f}%;top:0;width:2px;height:100%;background:#0b1118;opacity:.75"></div>'
           f'</div>'
           # 现价 ▼（放在条上方·深浅色都靠自带描边看得见）
           f'<div style="position:absolute;left:{p_px:.2f}%;top:-{2 if mini else 4}px;transform:translateX(-50%);'
           f'font-size:{fs+1:.0f}px;color:#ffffff;text-shadow:0 0 3px #000,0 0 3px #000;line-height:1">▼</div>')
    wrap = (f'<div style="position:relative;padding-top:{10 if mini else 14}px">{bar}</div>')
    if mini:
        return (wrap + f'<div style="font-size:10.5px;color:{col};font-weight:700;margin-top:-4px">{esc(verd)}</div>')
    labels = (f'<div style="display:flex;justify-content:space-between;font-size:12px;color:#c8d4de;margin-top:-10px">'
              f'<span>便宜　<b>{c}{lo:,.0f}</b></span>'
              f'<span>中间值　<b>{c}{mid:,.0f}</b></span>'
              f'<span>贵　<b>{c}{hi:,.0f}</b></span></div>')
    return ('<div style="background:#101a26;border:1px solid #2b4054;border-radius:8px;padding:10px 14px 8px;margin:8px 0">'
            f'<div style="font-size:13px;color:#9ed8ff;font-weight:700;margin-bottom:2px">这只现在贵不贵（一眼看）</div>'
            + wrap + labels
            + f'<div style="margin-top:7px;font-size:13.5px">现价 <b style="font-size:15px">{c}{px:,.2f}</b>'
              f'　<b style="color:{col};font-size:14px">{esc(verd)}</b></div>'
            + f'<div style="font-size:11.5px;color:#8ea3b6;margin-top:3px">▼＝今天的价。绿=便宜 / 黄=合理 / 红=贵。'
              f'<b>{esc(HORIZON_NOTE)}</b>。</div></div>')


def _val_wait_reason(sym: str, dyn: dict) -> str:
    """估值待接的6只：不画轴、写人话原因(缺不编)。"""
    v = (dyn.get("valr", {}) or {}).get(sym, {}) or {}
    t = str(v.get("type") or "")
    why = {"周期股": "它是周期股——现在正处在景气高点，拿眼下的盈利去乘倍数会把价算得虚高；"
                    "得用“穿越一轮周期的正常年景盈利”，而这个数还没有权威来源可接",
           "控股公司": "它是控股公司——得把手里每块资产分别估值再相加减负债；这套分项真估值还没接进来",
           "商社": "它是综合商社——得把各块业务分别估值再相加；这套分项真估值还没接进来"}.get(t, "")
    if not why:
        why = "这类生意还没有可信的估值输入（缺真源），硬算出来的数会误导你"
    return ('<div style="background:#2a1f10;border:1px solid #7a5a20;border-radius:8px;padding:9px 13px;margin:8px 0">'
            '<div style="font-size:13px;color:#ffb454;font-weight:700">这只算不出该值多少钱——所以不画贵便宜轴</div>'
            f'<div style="font-size:12.5px;color:#e6eef5;margin-top:3px">{esc(why)}。'
            '<b>缺真源就不编数</b>，这是规矩。所以今天对它只能“守着看”，不主动加减。</div></div>')


# ══ 乙7/乙8：横条形图（纯HTML/CSS·深浅色都清楚·带上限/下限红虚线） ══
def _bar_row(label: str, pct: float, limit=None, floor=None, note: str = "", scale: float = 100.0) -> str:
    w = max(0.0, min(100.0, pct / scale * 100.0))
    over = limit is not None and pct > limit
    short = floor is not None and pct < floor
    col = "#d24b4b" if over else ("#c9922b" if short else "#3f8fd0")
    flag = ("<b style='color:#ff9a9a'>⚠ 超上限</b>" if over
            else ("<b style='color:#ffd479'>⚠ 不足下限</b>" if short else "<span style='color:#8ea3b6'>在限内</span>"))
    marks = ""
    for lim, cl, txt in ((limit, "#ff5c5c", "上限"), (floor, "#ffd479", "下限")):
        if lim is None:
            continue
        lp = max(0.0, min(100.0, lim / scale * 100.0))
        marks += (f'<div style="position:absolute;left:{lp:.2f}%;top:-3px;bottom:-3px;width:0;'
                  f'border-left:2px dashed {cl}"></div>'
                  f'<div style="position:absolute;left:{lp:.2f}%;top:-15px;transform:translateX(-50%);'
                  f'font-size:10px;color:{cl};white-space:nowrap">{txt}{lim:.0f}%</div>')
    return (f'<div style="margin:16px 0 10px">'
            f'<div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:3px">'
            f'<b>{esc(label)}</b><span><b style="font-size:14px">{pct:.1f}%</b>　{flag}</span></div>'
            f'<div style="position:relative;height:15px;background:#3a4551;border-radius:4px">'
            f'<div style="width:{w:.2f}%;height:100%;background:{col};border-radius:4px"></div>{marks}</div>'
            + (f'<div style="font-size:11.5px;color:#8ea3b6;margin-top:3px">{note}</div>' if note else "")
            + '</div>')


def _nd(s) -> str:
    """待接标橙(不编)。内容为已核准/已接真源的可信HTML片段·原样渲染。"""
    return str(s).replace("待接", '<span class="need">待接</span>')

def _f2(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def _val_sensitivity(sym: str):
    """估值敏感性(现算·变一项其余不变→中枢怎么变)。
    成长股(growth_dcf)：增长±10pp、折现±2pp(复用two_stage_dcf)。
    周期股(mid_cycle)：正常盈利±10%、中周期PE±2(中枢=正常EPS×中周期PE)。
    缺真输入/不支持→None。"""
    try:
        vi = rj(ROOT / "data" / "valuation" / "val_inputs.json").get("holdings", {}).get(sym, {})
        cur_sym = cur(sym)
        # 成长股两段式DCF
        e, g, y = vi.get("eps0"), vi.get("g_stage1"), vi.get("years")
        tg, w = vi.get("terminal_g"), vi.get("wacc")
        if None not in (e, g, y, tg, w):
            from dcf_valuation import two_stage_dcf
            y = int(y); base = two_stage_dcf(e, g, y, tg, w)
            rows = []
            for lbl, gg, ww in [(f"更猛：增速 {g:.0%}→{g+0.10:.0%}", g + 0.10, w),
                                (f"降温：增速 {g:.0%}→{g-0.10:.0%}", g - 0.10, w),
                                (f"利率再涨：折现 {w:.0%}→{w+0.02:.0%}", g, w + 0.02),
                                (f"利率回落：折现 {w:.0%}→{w-0.02:.0%}", g, w - 0.02)]:
                v = two_stage_dcf(e, gg, y, tg, ww)
                rows.append((lbl, f"{cur_sym}{v:.0f}", f"{(v-base)/base*100:+.0f}%"))
            return {"model": "growth_dcf", "base": base, "rows": rows,
                    "inputs": {"eps0": e, "g": g, "years": y, "tg": tg, "wacc": w}}
        # 控股/商社NAV法(如软银):变总资产±10%、控股折价±10pp
        assets = vi.get("assets")
        if assets:
            tot = sum(_f2(a.get("value")) for a in assets if _f2(a.get("value")) is not None)
            nd = _f2(vi.get("net_debt")) or 0.0
            sh = _f2(vi.get("shares"))
            disc = _f2(vi.get("holding_discount")) or 0.0
            if sh and sh > 0:
                base_nav = (tot - nd) / sh * (1 - disc)
                # 甲3[factual]：资产名【按本只现取】，不许写死软银的"(Arm/OpenAI等)"。
                # 原写法让所有走NAV法的标的都贴软银资产名 → MSTR(持的是比特币)敏感性表串成软银模板。
                _names = [str(a.get("name", "")) for a in assets if a.get("name")]
                _short = []
                for _n in _names[:2]:
                    _short.append(re.split(r"[（(]| ", _n)[0][:14])
                _an = "／".join(x for x in _short if x) or "持有资产"
                rows = []
                for lbl, at, dd in [(f"资产涨：{_an} +10%", tot * 1.1, disc),
                                    (f"资产跌：{_an} -10%", tot * 0.9, disc),
                                    ("若市场给控股折价 20%(NAV/股打八折)", tot, 0.20),
                                    ("若市场给控股折价 40%(NAV/股打六折)", tot, 0.40)]:
                    v = (at - nd) / sh * (1 - dd)
                    rows.append((lbl, f"{cur_sym}{v:,.0f}", f"{(v-base_nav)/base_nav*100:+.0f}%"))
                return {"model": "nav", "base": base_nav, "rows": rows,
                        "inputs": {"assets_total": tot, "net_debt": nd, "shares": sh, "discount": disc}}
        # 保险PB/内含价值法(如东京海上):变每股净资产±10%、目标PB±0.2
        bv, tpb = _f2(vi.get("bvps")), _f2(vi.get("target_pb"))
        if bv is not None and tpb is not None:
            base = bv * tpb
            rows = []
            for lbl, b2, p2 in [(f"净资产更厚：每股净资产 +10%", bv * 1.1, tpb),
                                (f"净资产变薄：每股净资产 -10%", bv * 0.9, tpb),
                                (f"给估值更高：目标PB {tpb:g}→{tpb+0.2:g}倍", bv, tpb + 0.2),
                                (f"给估值更低：目标PB {tpb:g}→{max(0.1,tpb-0.2):g}倍", bv, max(0.1, tpb - 0.2))]:
                v = b2 * p2
                rows.append((lbl, f"{cur_sym}{v:,.0f}", f"{(v-base)/base*100:+.0f}%"))
            return {"model": "pbv", "base": base, "rows": rows,
                    "inputs": {"bvps": bv, "target_pb": tpb}}
        # 周期股中周期盈利法
        ne, pe = vi.get("normal_eps"), vi.get("pe_mid")
        if ne is not None and pe is not None:
            base = ne * pe
            rows = []
            for lbl, nn, pp in [(f"景气更旺：正常盈利 {cur_sym}{ne:g}→{cur_sym}{ne*1.1:g}", ne * 1.1, pe),
                                (f"景气转弱：正常盈利 {cur_sym}{ne:g}→{cur_sym}{ne*0.9:g}", ne * 0.9, pe),
                                (f"给估值更高：中周期PE {pe:g}→{pe+2:g}倍", ne, pe + 2),
                                (f"给估值更低：中周期PE {pe:g}→{pe-2:g}倍", ne, pe - 2)]:
                v = nn * pp
                rows.append((lbl, f"{cur_sym}{v:.0f}", f"{(v-base)/base*100:+.0f}%"))
            return {"model": "mid_cycle", "base": base, "rows": rows,
                    "inputs": {"normal_eps": ne, "pe_mid": pe}}
        # 券商正常化PE法(如IBKR/COIN/CRCL):变正常化EPS±10%、正常化PE±2
        nze, nzp = _f2(vi.get("normalized_eps")), _f2(vi.get("pe_normal"))
        if nze is not None and nzp is not None:
            base = nze * nzp
            rows = []
            for lbl, ee, pp in [(f"盈利更旺：正常化EPS {cur_sym}{nze:g}→{cur_sym}{nze*1.1:g}", nze * 1.1, nzp),
                                (f"盈利转弱：正常化EPS {cur_sym}{nze:g}→{cur_sym}{nze*0.9:g}", nze * 0.9, nzp),
                                (f"给估值更高：正常化PE {nzp:g}→{nzp+2:g}倍", nze, nzp + 2),
                                (f"给估值更低：正常化PE {nzp:g}→{max(1,nzp-2):g}倍", nze, max(1, nzp - 2))]:
                v = ee * pp
                rows.append((lbl, f"{cur_sym}{v:.0f}", f"{(v-base)/base*100:+.0f}%"))
            return {"model": "normalized_pe", "base": base, "rows": rows,
                    "inputs": {"normalized_eps": nze, "pe_normal": nzp}}
        return None
    except Exception:
        return None

def render_deep_blocks(sym: str, name: str, dyn: dict, deep: dict, f: dict) -> str:
    out = []
    esc_note = esc(str(deep.get("source_note", "")))
    out.append(f'<div class="meta" style="color:#8ea3b6;font-size:11.5px;margin:4px 0">深度素材来源：{esc_note}</div>')
    # ① 生意引擎
    b = deep.get("block1_business", {})
    rows = "".join(f'<tr><td><b>{_nd(r.get("block",""))}</b></td><td>{_nd(r.get("what",""))}</td><td>{_nd(r.get("size",""))}</td></tr>' for r in b.get("streams", []))
    out.append('<div class="blk">① 它靠什么赚钱、往哪长（生意的根）</div>'
               f'<p style="font-size:13px">{_nd(b.get("intro",""))}</p>'
               '<table class="dt"><tr><th>赚钱的块</th><th>是什么（人话）</th><th>多大/趋势</th></tr>' + rows + '</table>'
               f'<div class="plain"><b>未来新钱从哪来</b>：{_nd(b.get("future_growth",""))}</div>')
    # ② 多年财报表(Code接真源·带as_of/来源)。控股公司(mode=nav)用NAV历史表；其余用收入表·利润率/关键占比两列表头可配置
    fin = deep.get("block2_financials", {})
    if fin.get("mode") == "nav":
        nrows = "".join('<tr><td><b>{pe}</b></td><td>{nav}</td><td>{ltv}</td><td>{nps}</td><td>{disc}</td><td style="color:#8ea3b6;font-size:11px">{aso}<br>{src}</td></tr>'.format(
            pe=_nd(r.get("period","")), nav=_nd(r.get("nav","")), ltv=_nd(r.get("ltv","")), nps=_nd(r.get("nav_ps","")),
            disc=_nd(r.get("discount","")), aso=esc(r.get("as_of","")), src=esc(r.get("source",""))) for r in (fin.get("rows") or []))
        out.append('<div class="blk">② 这几年的账（控股公司看 NAV 净资产·不是看利润）</div>'
                   f'<div class="plain">{_nd(fin.get("plain",""))}</div>'
                   '<table class="dt"><tr><th>期末</th><th>NAV(净资产)</th><th>LTV(负债率)</th><th>NAV/股</th><th>折价</th><th>as_of/来源</th></tr>' + nrows + '</table>'
                   f'<div class="plain"><b>这张表说明</b>：{_nd(fin.get("readout",""))}</div>')
    else:
        margin_label = esc(fin.get("margin_label", "毛利率(GAAP)"))
        metric_label = esc(fin.get("metric_label", "数据中心占比"))
        frows = "".join('<tr><td><b>{fy}</b></td><td>{rev}</td><td>{yoy}</td><td>{gm}</td><td>{ni}</td><td>{fcf}</td><td>{dc}</td><td style="color:#8ea3b6;font-size:11px">{aso}<br>{src}</td></tr>'.format(
            fy=_nd(r.get("fy","")), rev=_nd(r.get("revenue","")), yoy=_nd(r.get("yoy","")), gm=_nd(r.get("gross_margin","")),
            ni=_nd(r.get("net_income","")), fcf=_nd(r.get("fcf","")), dc=_nd(r.get("metric") or r.get("dc_share","")),
            aso=esc(r.get("as_of","")), src=esc(r.get("source",""))) for r in (fin.get("rows") or []))
        out.append('<div class="blk">② 这几年赚钱的账（营收·利润·现金一路怎么走）</div>'
                   f'<div class="plain">{_nd(fin.get("plain",""))}</div>'
                   f'<table class="dt"><tr><th>财年(截止)</th><th>营收</th><th>比去年</th><th>{margin_label}</th><th>净利</th><th>自由现金流</th><th>{metric_label}</th><th>as_of/来源</th></tr>' + frows + '</table>'
                   f'<div class="plain"><b>这张表说明</b>：{_nd(fin.get("readout",""))}</div>')
    # ③ 护城河五维逐维
    mo = deep.get("block3_moat", {})
    mrows = "".join(f'<tr><td>{_nd(r.get("dim",""))}</td><td><b>{_nd(r.get("width",""))}</b></td><td>{_nd(r.get("why",""))}</td></tr>' for r in mo.get("rows", []))
    out.append('<div class="blk">③ 护城河：为什么对手抢不走（五个方面逐个看）</div>'
               '<table class="dt"><tr><th>护城河的一面</th><th>宽/窄</th><th>为什么（人话）</th></tr>' + mrows + '</table>'
               f'<p style="font-size:13px"><span class="k">综合</span>{_nd(mo.get("score",""))}</p>')
    # ④ 对手逐个
    rv = deep.get("block4_rivals", {})
    rrows = "".join(f'<tr><td>{_nd(r.get("rival",""))}</td><td>{_nd(r.get("how",""))}</td><td><b>{_nd(r.get("threat",""))}</b></td><td>{_nd(r.get("why_safe",""))}</td></tr>' for r in rv.get("rows", []))
    out.append('<div class="blk">④ 对手都有谁、能抢走多少</div>'
               '<table class="dt"><tr><th>对手</th><th>怎么打</th><th>威胁</th><th>为什么暂时抢不动</th></tr>' + rrows + '</table>'
               f'<p style="font-size:13px"><span class="k">一句话</span>{_nd(rv.get("oneliner",""))}</p>')
    # ⑤ 估值模型+敏感性(引擎单一源+现算)
    v5 = deep.get("block5_valuation", {})
    valr = dyn.get("valr", {}).get(sym, {})
    low, high, mid = valr.get("reasonable_low"), valr.get("reasonable_high"), valr.get("target")
    ccy = valr.get("currency", cur(sym))
    sens = _val_sensitivity(sym)
    inrows = "".join(f'<tr><td>{_nd(i.get("input",""))}</td><td>{_nd(i.get("plain",""))}</td></tr>' for i in v5.get("inputs", []))
    if sens:
        ip = sens["inputs"]; m = sens.get("model")
        if m == "growth_dcf":
            inval = (f'<div class="plain">本次引擎真输入：明年EPS <b>{ccy}{ip["eps0"]}</b>·头几年增速 <b>{ip["g"]:.0%}</b>·快增 <b>{ip["years"]}年</b>·永续 <b>{ip["tg"]:.0%}</b>·折现 <b>{ip["wacc"]:.0%}</b></div>')
        elif m == "mid_cycle":
            inval = (f'<div class="plain">本次引擎真输入(中周期盈利法)：正常化EPS <b>{ccy}{ip["normal_eps"]:g}</b>·中周期PE <b>{ip["pe_mid"]:g}倍</b></div>')
        elif m == "nav":
            inval = (f'<div class="plain">本次引擎真输入(NAV净资产法)：持有资产合计 <b>{ip["assets_total"]:,.0f}</b>·净负债 <b>{ip["net_debt"]:,.0f}</b>·股本 <b>{ip["shares"]:g}</b>·控股折价 <b>{ip["discount"]:.0%}</b>（单位见判断包·如十亿円/十亿股）</div>')
        elif m == "pbv":
            inval = (f'<div class="plain">本次引擎真输入(保险PB法)：每股净资产 <b>{ccy}{ip["bvps"]:g}</b>·目标PB <b>{ip["target_pb"]:g}倍</b></div>')
        elif m == "normalized_pe":
            inval = (f'<div class="plain">本次引擎真输入(正常化PE法)：正常化EPS <b>{ccy}{ip["normalized_eps"]:g}</b>·正常化PE <b>{ip["pe_normal"]:g}倍</b></div>')
        else:
            inval = ''
        srows = "".join(f'<tr><td>{esc(lbl)}</td><td><b>{esc(mm)}</b></td><td>{esc(dd)}</td></tr>' for lbl, mm, dd in sens["rows"])
        senstbl = ('<div class="plain"><b>如果输入变了会怎样（敏感性·现算）</b>——因为没人能算准，得知道算错了偏多少：</div>'
                   '<table class="dt"><tr><th>如果…</th><th>合理价中枢变成</th><th>较基准</th></tr>' + srows + '</table>')
    else:
        inval = ''; senstbl = '<div class="plain"><span class="need">敏感性待接</span>（缺真输入·如周期股无权威正常化EPS源·不硬编）</div>'
    rng = (f'合理区 <b>{esc(ccy)}{esc(fnum(low))} ~ {esc(ccy)}{esc(fnum(high))}</b>，中枢 <b>{esc(ccy)}{esc(fnum(mid))}</b>'
           if low is not None and mid is not None else '<span class="need">合理区/中枢待接</span>（估值引擎缺真输入·不硬编）')
    # 乙6：大估值数轴顶在⑤块最前——替代"四个数挤一句话"；待接的不画轴、写人话原因(丙10:轴上标时间跨度)
    _axis = _val_axis(sym, dyn) or _val_wait_reason(sym, dyn)
    out.append('<div class="blk">⑤ 它到底值多少钱（算法+过程+区间+"如果变了"）</div>'
               + _axis
               + f'<div class="plain"><b>怎么算</b>：{_nd(v5.get("method_plain",""))}</div>'
               '<table class="dt"><tr><th>要填的输入</th><th>大白话</th></tr>' + inrows + '</table>' + inval
               + f'<p style="font-size:13px"><span class="k">算出来</span>{rng}（与决策条同一源·R1）。'
               + (f'<span style="color:#8ea3b6">（{esc(HORIZON_NOTE)}）</span>' if low is not None else '')
               + f'{_nd(v5.get("note",""))}</p>'
               + senstbl)
    # ⑥ 牛/基/熊三情景
    sc = deep.get("block6_scenarios", {})
    scrows = "".join(f'<tr><td class="{r.get("cls","base")}">{_nd(r.get("case",""))}</td><td>{_nd(r.get("assume",""))}</td><td>{_nd(r.get("value",""))}</td><td>{_nd(r.get("prob",""))}</td></tr>' for r in sc.get("rows", []))
    out.append('<div class="blk">⑥ 好、中、坏三种情况分别值多少</div>'
               '<table class="dt"><tr><th>情况</th><th>假设(人话)</th><th>值多少</th><th>大概几成可能</th></tr>' + scrows + '</table>'
               f'<p style="font-size:13px"><span class="k">这告诉你</span>{_nd(sc.get("readout",""))}</p>')
    # ⑦ 催化剂日历（甲6：当日已出报的那条不许再当"未来要盯的"）
    _d = dyn.get("date", "")
    _today_iso = f"{_d[:4]}-{_d[4:6]}-{_d[6:]}" if len(_d) == 8 else ""
    _is_rep_day = bool(_ecal(_d).get(sym))
    cats = ""
    for x in deep.get("block7_catalysts", []):
        li = _nd(x)
        if _is_rep_day and _today_iso and _today_iso in str(x) and "财报" in str(x):
            li = ('<b style="color:#ffb454">［今天已经出了·不是以后的事］</b> ' + li)
        cats += f'<li>{li}</li>'
    out.append('<div class="blk">⑦ 往后要盯的关键时间点（催化剂日历）</div><ul style="font-size:13px">' + cats + '</ul>')
    # ⑧ 风险量化
    rk = deep.get("block8_risks", {})
    krows = "".join(f'<tr><td>{_nd(r.get("risk",""))}</td><td>{_nd(r.get("weight",""))}</td><td>{_nd(r.get("signal",""))}</td></tr>' for r in rk.get("rows", []))
    out.append('<div class="blk">⑧ 风险——不光列出来，还称一称多重</div>'
               '<table class="dt"><tr><th>风险</th><th>有多重(人话)</th><th>出现的信号</th></tr>' + krows + '</table>')
    # ⑨ 决策链
    out.append('<div class="blk">⑨ 从大局怎么一步步推到决策（决策链）</div>'
               f'<p style="font-size:13px">{_nd(deep.get("block9_decision_chain",""))}</p>')
    # ⑩ 组合视角
    pf = deep.get("block10_portfolio", {})
    out.append('<div class="blk">⑩ 它在你整盘里是什么角色（组合视角）</div>'
               f'<p style="font-size:13px"><span class="k">扛哪些共同风险</span>{_nd(pf.get("common_risks",""))}<br>'
               f'<span class="k">占多重</span>{_nd(pf.get("weight",""))}<br>'
               f'<span class="k">和别的持仓什么关系</span>{_nd(pf.get("correlation",""))}<br>'
               f'<span class="k">换不换</span>{_nd(pf.get("swap",""))}</p>')
    return '<div class="deep">' + "".join(out) + '</div>'

# ══ 件一：每只卡收尾「今天你怎么办」四行人话(结论/为什么/什么价该动/什么信号变卦) ══
# 估值算不出的原因(人话·不甩字段名)
_NOVAL_WHY = {
    "JP.6857": "这只是做芯片测试机的，生意大起大落（现在毛利64%是行情最好的时候），拿眼下的好光景去算它值多少钱，一定算高",
    "US.SNDK": "这只做存储芯片，行业价格暴涨暴跌（毛利4个季度从22%冲到78%），拿现在的高点算价一定离谱",
    "US.TSM": "这只是芯片代工，眼下毛利66%是景气最高点，按现在的赚钱速度算价会高估",
    "JP.8001": "这是综合商社（一家公司下面几百个生意），公司不公布每块资产值多少，业内也不这么算",
    "US.COIN": "这只是加密交易所，行情好时暴赚、行情差时巨亏（2022年亏了26亿美元），没有一个'正常年份'可参照",
    "US.CRCL": "这只九成收入靠美元存款利息，美联储一降息收入就掉，利率一变估值就全变",
}
_ACT_LABEL = {"守": "守住核心·别追高别减", "等": "拿着别动·先别加", "加": "可以加一点", "减": "减一点"}

def howto_block(sym: str, name: str, f: dict, dyn: dict, deep: dict | None) -> str:
    valr = dyn.get("valr", {}).get(sym, {})
    ccy = valr.get("currency", cur(sym))
    low, high, mid = valr.get("reasonable_low"), valr.get("reasonable_high"), valr.get("target")
    px = f.get("price")
    act = str(f.get("action") or "")
    base = next((v for k, v in _ACT_LABEL.items() if act.startswith(k)), None)
    qual = str(f.get("quality") or "")
    has_val = (low is not None and mid is not None)
    # 1) 结论一句话(必带半句人话理由)
    if not has_val:
        concl = "算不清·只能守着看"
        why_tail = "——因为算不出它该值多少钱，不知道贵还是便宜，就不主动加减"
    elif base:
        concl = base
        why_tail = ""
    else:
        concl = "拿着别动·先别加"
        why_tail = ""
    reason_bits = []
    if "①" in qual:
        reason_bits.append("公司质地是最好那一档")
    elif "②" in qual:
        reason_bits.append("公司质地还行、但还在观察期")
    if has_val and px is not None:
        try:
            if float(px) < float(low):
                reason_bits.append(f"现价{ccy}{fnum(px)}比算出来的合理价下沿{ccy}{fnum(low)}还低，属于偏便宜")
            elif float(px) > float(high):
                pct = (float(px) / float(mid) - 1) * 100
                reason_bits.append(f"现价{ccy}{fnum(px)}比合理价中间值{ccy}{fnum(mid)}高约{pct:.0f}%，属于偏贵")
            else:
                reason_bits.append(f"现价{ccy}{fnum(px)}落在合理价{ccy}{fnum(low)}~{ccy}{fnum(high)}区间里，不贵不便宜")
        except Exception:
            pass
    line1 = f'<b style="color:#ffd479">{esc(concl)}</b>' + esc(why_tail) + ("（" + esc("；".join(reason_bits)) + "）" if reason_bits else "")
    # 2) 为什么(一句人话)
    # B2/B3/B4治本：不再鹦鹉学舌 production 的旧护城河/估值判词(它与引擎中枢、与深研③块打架)——
    # 护城河只引深研③块的结论，贵贱只认估值引擎的"现价 vs 合理价"，口径全篇唯一。
    raw = str(f.get("reason") or "")
    bits2 = []
    if "符合方向" in raw or "硬性=符合" in raw:
        bits2.append("它正好落在今天钱在流向的那条线上")
    if deep:
        _sc = str((deep.get("block3_moat") or {}).get("score") or "")
        if "宽" in _sc:
            bits2.append("生意有别人抢不走的东西（护城河宽，详见本卡③）")
        elif "窄" in _sc:
            bits2.append("护城河偏窄、靠不住定价权（详见本卡③）")
    if "①" in qual:
        bits2.append("账本记它是最好那一档")
    elif "②" in qual:
        bits2.append("账本记它还在观察期、没到最好那一档")
    if not has_val:
        bits2.append("但算不出它该值多少钱，所以不主动加减")
    elif px is not None:
        try:
            if float(px) < float(low):
                bits2.append("价格现在偏便宜")
            elif float(px) > float(high):
                bits2.append("但价格现在偏贵——所以只守不加")
            else:
                bits2.append("价格不贵不便宜")
        except Exception:
            pass
    # 软银：值双倍却只守——必须一句话解释，别让人误读成该重仓
    if sym == "JP.9984":
        bits2.append("虽然算出来它值得更高，但你押在AI上的钱已经超上限、纪律不许再加；真要降AI敞口，也是先减它")
    line2 = esc("；".join(bits2) + "。") if bits2 else esc(_zh_common(_scrub_valuation_stance(raw))) or "待接"
    # 3) 什么价该动
    if has_val:
        line3 = (f'跌到 <b>{esc(ccy)}{esc(fnum(low))}</b> 以下可以考虑加一点（那是算出来的合理价下沿）；'
                 f'涨过 <b>{esc(ccy)}{esc(fnum(high))}</b> 就偏贵、别追。中间值约 {esc(ccy)}{esc(fnum(mid))}。')
        if px is not None:
            line3 += f'　现在是 {esc(ccy)}{esc(fnum(px))}。'
        # C2：中枢与现价差得离谱时，必须解释为什么，别让董事长以为算错了
        try:
            gap = (float(px) / float(mid) - 1) * 100 if px else 0
        except Exception:
            gap = 0
        _GAP_WHY = {
            "JP.7974": ("这套算法只算“它靠卖游戏能赚多少钱”，<b>没把它手上那一大笔净现金算进去</b>"
                        "（约每股¥1,940、占市值约四分之一）。所以：<b>整体看是偏贵</b>，"
                        "但扣掉手上净现金后没那么夸张——两句话不矛盾，一句是整体、一句是扣现金。"),
            "US.IBKR": ("这里用的是“一家普通券商该值多少倍”的算法（约22倍），"
                        "而市场现在愿意给它约37倍——因为它客户数每年还在涨约30%、利润率高达77%。"
                        "<b>不是算错了，是市场在为高成长多付钱</b>；按普通券商的尺子量，它确实贵。"),
        }
        if abs(gap) >= 25:
            why_gap = _GAP_WHY.get(sym)
            if why_gap:
                line3 += f'<div style="margin-top:4px;color:#ffb454">为什么算出来的价和现价差这么多：{why_gap}</div>'
            else:
                line3 += (f'<div style="margin-top:4px;color:#ffb454">提醒：现价比算出来的中间值差约{gap:+.0f}%，'
                          f'差距不小——这套算法只按“它未来能赚多少钱”折算，未必涵盖它的全部价值，请结合本卡⑤看。</div>')
    else:
        why = _NOVAL_WHY.get(sym, "这只的赚钱方式没法用常规办法算出一个可信的合理价")
        line3 = f'<span style="color:#ffb454">这只算不出该值多少钱</span>——{esc(why)}。所以只能守着看、不主动加减；等它跌到明显便宜或基本面变坏再说。'
    # 4) 什么信号才变卦(董事长盯得住的)
    sig = None
    if deep:
        cats = deep.get("block7_catalysts") or []
        risks = (deep.get("block8_risks") or {}).get("rows") or []
        bits = []
        if cats:
            bits.append(str(cats[0]).split("：")[0].split("(")[0])
        for r in risks[:2]:
            s = str(r.get("signal") or "")
            if s and "待接" not in s:
                bits.append(s)
        if bits:
            sig = "；".join(bits[:2])
    line4 = esc(sig) if sig else "下季财报的营收/利润明显不及预期，或出了直接冲击它主业的大新闻，就要重看。"
    return ('<div class="card" style="background:#12261f;border-color:#4f9e7f;margin-top:8px">'
            '<div class="hd"><b style="color:#7ee0a0">■ 今天你怎么办</b></div>'
            f'<div style="font-size:13.5px;line-height:1.9">'
            f'<div><b>1｜结论：</b>{line1}</div>'
            f'<div><b>2｜为什么：</b>{line2}</div>'
            # 丙10：加减价必须标时间跨度(有估值的才标·待接的第3行本就是人话原因)
            f'<div><b>3｜什么价该动：</b>{line3}'
            + (f'<div style="font-size:11.5px;color:#8ea3b6;margin-top:2px">'
               f'（{esc(HORIZON_NOTE)}；没有到期时间——到价就提醒，不到就一直不动）</div>'
               if _val_axis(sym, dyn) else '')
            + '</div>'
            f'<div><b>4｜什么信号才变卦：</b>{line4}</div>'
            '</div></div>')

def render_card(sym: str, name: str, dyn: dict) -> str:
    f = build_final(sym, name, dyn)                 # ← 唯一决策对象
    _orig_action = f["action"]                       # 存原始动作(深度卡覆盖退出条件时恢复·不误降初判)
    ma = dyn["ma"].get(sym, {}); ht = dyn["ht"].get(sym, {}); c = cur(sym)
    price = f["price"]
    # 深研（判断包·只取定性素材:生意/护城河/财报真数据/退出条件·不渲染其估值/动作结论·治B3）
    pack = find_pack(sym, name)
    if pack:
        ex = extract_pack(pack)
        # R4:只抹当前交易价(财报/研究目标价保留)；R1补:剥离估值定性词；R10③:英文普通词译中
        def _clean(x): return _zh_common(_scrub_valuation_stance(_scrub_pack_prices(_clean_placeholder(esc(x)))))
        biz = _clean(ex["生意"]); moat = _clean(ex["护城河"])
        data = _clean(ex["真数据"] or "判断包未含真数据段")
        # R5：无专门退出条件段 → 标"深研未完成·退出条件待补"，且动作降"初判·待补全"(缺不编)
        exit_incomplete = not (ex.get("风险") or "").strip()
        if exit_incomplete:
            exit_c = '<span style="color:#c9a86a">深研未完成·退出条件待补（判断包无专门退出条件段·不编）</span>'
            f["action"] = f'初判·待补全（退出条件缺）｜原动作 {f["action"]}'
        else:
            exit_c = _clean(ex["风险"])
        _mdate = re.search(r'(20\d{6})', pack.stem)
        as_of = (f"{_mdate.group(1)[:4]}-{_mdate.group(1)[4:6]}-{_mdate.group(1)[6:]}" if _mdate else "判断包未标日期")
        fin_audit = _audit_financials(ex["真数据"] or "", sym)   # R8 财务口径审计标注
        _cy = "¥(日元·当日汇率见行情快照)" if sym.startswith("JP.") else "$(美元)"
        deep = (f'<div class="deep"><span class="k">深研·财报趋势（财报/数据 as_of {esc(as_of)}·计价{esc(_cy)}）</span>{data}{fin_audit}'
                f'<div style="margin-top:5px"><span class="k">生意/增长点</span>{biz}'
                f'<span class="k">护城河/竞争格局</span>{moat}</div>'
                f'<div style="margin-top:5px"><span class="k">退出条件(看生意不看价·非价位)</span>{exit_c}</div>'
                f'<div class="meta" style="color:#8fd6ff;font-size:12px;margin-top:4px">深研=判断包定性素材·as_of {esc(as_of)}（价位一律以本卡档案/决策条·当日production为准·R4）｜源：{esc(pack.name)}</div></div>')
        pack_status = "OK" if not exit_incomplete else "退出条件待补"
    else:
        deep = '<div class="deep"><span class="k">深研·财报趋势</span><span style="color:#c9a86a">待建判断包（个股判断包_*.html 缺该只·不编）</span></div>'
        pack_status = "待建判断包"
    # 成品级深度10块(对齐认可样卡)：有 deep_cards/{sym}.json 则升级为10块+大白话；无则保持4段(其余18只回退·待铺满)
    _deepcard = _load_deep_card(sym, dyn)
    if _deepcard:
        f["action"] = _orig_action   # 深度卡⑧风险量化+⑨"什么才算生意坏了要走"已含退出条件→不降"初判·待补全"
        deep = render_deep_blocks(sym, name, dyn, _deepcard, f)
        pack_status = "深度10块"
    # 档案（股数/成本/均线趋势参考·缺不编）
    qty = ht.get("total_quantity"); cost = ht.get("avg_cost_price"); accs = ht.get("accounts") or []
    if qty:
        parts = [f"{a.get('account','')}{a.get('quantity'):g}" for a in accs if a.get("quantity")]
        qty_s = f"{qty:g}股" + (f"（{'＋'.join(parts)}）" if parts else "")
    else:
        qty_s = "待接·无真股数"
    # 件六①：成本锚真填不了→人话交代原因(四账户持仓截图只有股数、没有买入价)
    # 甲2：这行本来就要带真加粗→自己拼安全HTML(内容各段单独esc)，不再整串过 esc(否则<b>被转义成字面量)
    cost_html = (esc(f"{c}{fnum(cost)}（四账户均价·{ht.get('cost_grade','')}级）") if cost is not None
                 else ("算不出——你四个账户的持仓记录里<b>只有股数、没有买入价</b>，"
                       "所以没法算你这只赚了还是亏了。"
                       "要填上它，需要你把各账户的买入均价给我一次（之后就能天天自动算盈亏）。"))
    ma20, ma50, ma200 = ma.get("ma20"), ma.get("ma50"), ma.get("ma200")
    # 乙4：分隔符用「 ｜ 」不用「/」——"X/X"归一那条兜底正则会把"¥3,420/200日"里的斜杠吃掉，
    # 粘成"50日¥3,4200日¥3,737"(看着像数字错，其实是分隔符没了)。
    ma_s = (f"20日{c}{fnum(ma20)} ｜ 50日{c}{fnum(ma50)} ｜ 200日{c}{fnum(ma200)}（均线位·仅趋势参考·不作买卖线）"
            if ma200 is not None else "待接·均线不足（不编）")
    dossier = (f'<div class="dossier"><span class="k">档案</span><b>持仓</b>{esc(qty_s)} ｜ <b>成本</b>{cost_html} '
               f'｜ <b>现价</b>{esc(c)}{esc(fnum(price)) if price is not None else "待接"}'
               f'<span style="color:#ffb454;font-size:11.5px;margin-left:4px">［{esc(price_stamp(sym, dyn.get("date","")))}］</span>'
               f' ｜ <b>均线</b>{esc(ma_s)}</div>')
    # 标题 + 决策条（全部引 final·单一源）
    hd = (f'<div class="hd"><b>{esc(name)}</b> <span class="sym">{esc(sym)}</span> '
          f'<span class="conf">动作：{f["action"]}</span> '
          f'<span class="q">账本：{f["quality"]}</span> <span class="v">估值：{f["valuation_short"]}（{f["valuation_grade"]}）</span></div>')
    conf_grade = _conf_grade(f)   # R10②:账本档→高/中/低把握(显式)
    final_row = (f'<div class="dossier" style="background:#12203a;border-radius:6px;padding:6px 8px">'
                 f'<span class="k">决策(单一源)</span>'
                 f'<b>动作</b>{f["action"]} ｜ <b>估值</b>{f["valuation"]} ｜ <b>账本</b>{f["quality"]} '
                 f'｜ <b>把握</b><span style="color:#ffd479;font-weight:700">{esc(conf_grade)}</span>（{f["confidence"]}）</div>')
    _dt = dyn.get("date", "")
    # 硬链2：持仓卡"决策链"↔上游对应层(总览册各层锚)
    chain_links = ('<div class="meta" style="font-size:11.5px;margin-top:3px;color:#8ea3b6">'
                   '决策链回溯上游：' + '　'.join(
                       _a(L1(_dt, "layer-" + s), t) for s, t in
                       (("world", "①世界观"), ("strategy", "②国家战略"), ("capital", "③资金流动"),
                        ("sector", "④板块轮动"))) +
                   '　｜　' + _a(VOL(_dt, 3), "⑤机会池册") + '　' + _a(VOL(_dt, 4), "⑦记分卡册")
                   + '　｜　' + _a(L5(_dt, "ruler-6"), "右栏⑥本只静态档案") + '</div>')
    # 甲6：出报日→卡顶强制横幅(日历现算·非出报日不出现)
    _eb = earnings_banner(sym, dyn.get("date", ""), dyn)
    return (f'<div class="card" id="stock-{esc(sym)}">{_eb}{hd}{final_row}{deep}{dossier}'
            + corro_box(sym, "symbol") + chain_links
            # B4治本：这一行原样甩 production 的旧判词("护城河=窄护城河"等)，与本卡③块/四行打架 →
            # 收敛为指路，结论一律以下面「今天你怎么办」四行为准(单一源)
            + '<div class="you"><span class="k">今天对你</span>'
              '见下面「■ 今天你怎么办」四行——那是这只今天的唯一结论。</div>'
            + howto_block(sym, name, f, dyn, _deepcard) + '</div>'), pack_status

# ── 第一部分·五层大环境（daily links·今日事件现渲；R10①每层落点到具体持仓） ──
# R10①：层→风险因子(复用R9映射)→落点持仓(哪几只受影响·敞口现算·非泛泛)
_LAYER_FACTOR = [(("总命题", "世界", "地缘", "台海"), "台海地缘"),
                 (("总闸", "美联储", "利率", "久期"), "高利率久期"),
                 (("战略", "AI/", "AI("), "AI资本开支"),
                 (("手段", "FIMA", "稳定币", "加密"), "加密β"),
                 (("资金轮动",), "加密β"),
                 (("板块", "半导体"), "半导体周期")]
def _layer_factor(node: str) -> str | None:
    for kws, fac in _LAYER_FACTOR:
        if any(k in node for k in kws):
            return fac
    return None

def _layer_impact(node: str, dyn: dict) -> str:
    fac = _layer_factor(node)
    if not fac:
        return '<div class="meta" style="color:#8ea3b6;font-size:12px;margin-top:4px">对你·落点持仓：该层无对应风险因子映射（不编）</div>'
    try:
        rf = rj(ROOT / "data" / "valuation" / "risk_factors.json")
        by_sym = rf.get("by_symbol", {}) or {}
    except Exception:
        return '<div class="meta" style="color:#8ea3b6;font-size:12px;margin-top:4px">对你·落点持仓：因子映射待接</div>'
    holds = dyn["prod"].get("holdings", [])
    name_by = {str(h.get("symbol")): str(h.get("name") or h.get("symbol")) for h in holds}
    try:
        cost = rj(ROOT / "data" / "accounts" / "unified_holdings_latest.json")
        cbt = cost.get("by_ticker") or {}
    except Exception:
        cbt = {}
    mv, total = _mv_usd_by_symbol(holds, cbt)
    members = [s for s in by_sym if fac in by_sym[s] and s in name_by]
    # 硬链2：落点持仓 → 持仓深研册该只锚点(跨文件相对路径+#anchor)
    # 防断链：加密(CC.*)无个股深研卡→只显名不链，不制造死锚
    _dt = dyn.get("date", "")
    names = "、".join(
        (esc(name_by[s]) + '<span style="color:#8ea3b6;font-size:11px">(资产口径·无个股卡)</span>')
        if str(s).startswith("CC.") else _a(L2(_dt, "stock-" + s), esc(name_by[s]))
        for s in members) or "—"
    expo = (sum(mv.get(s, 0.0) for s in members) / total * 100.0) if total > 0 else 0.0
    return ('<div class="you" style="margin-top:5px;font-weight:400;color:#9ed8ff">'
            f'<b style="color:#5cc8ff">对你·落点持仓（哪几只受影响）</b>：{names}'
            f'<span style="color:#8ea3b6">（同属风险因子「{esc(fac)}」·合计敞口 {expo:.1f}%·点名字跳持仓深研册）</span></div>')

# 深宏观:每层接右栏6尺 + "什么情况改看法"(证伪条件·定义级·非编造)
_LAYER_RULER = [(("总命题", "世界"), "第六部分·右栏① 世界观"),
                (("总闸", "美联储"), "第六部分·右栏③ 资金流动完整机制"),
                (("战略", "AI"), "第六部分·右栏② 国家战略地图"),
                (("手段", "FIMA", "稳定币", "加密"), "第六部分·右栏③ 资金流动完整机制"),
                (("资金轮动",), "第六部分·右栏③ 资金流动完整机制"),
                (("板块", "半导体"), "第六部分·右栏④ 板块地图")]
_LAYER_FLIP = [(("总命题", "世界"), "出现 regime 级反转信号(秩序/联盟根本重构)，而非零星地缘噪声"),
               (("总闸", "美联储"), "美联储出现新的加息/降息事件(FEDFUNDS 变动)——按状态机才翻闸，单日利率波动不算"),
               (("战略", "AI"), "AI 产业面多空关键词转为空占优，或大厂集体下修 AI 资本开支"),
               (("手段", "FIMA", "稳定币", "加密"), "稳定币/加密政策与流动性工具明显收紧、FIMA 类支持退潮"),
               (("资金轮动",), "VIX 持续飙升且资金明显撤离风险资产(不再'不避险')"),
               (("板块", "半导体"), "半导体板块资金持续净流出、SOXX 破位下行")]
def _match(node, table, default):
    for kws, val in table:
        if any(k in node for k in kws):
            return val
    return default

# ── 第零部分·差分优先页（今日变化页·只显与昨日不同者·D2/D3闭环入口） ──
def _prev_date(date: str) -> str | None:
    """找昨日(有真数据的最近前一日)：先试 date-1，再向前找 7 天内存在 production 的日子。"""
    try:
        d0 = datetime.strptime(date, "%Y%m%d")
    except Exception:
        return None
    for k in range(1, 8):
        d = (d0 - timedelta(days=k)).strftime("%Y%m%d")
        if (ROOT / "data" / "reports" / f"production_{d}.json").exists():
            return d
    return None

def part0_diff(date: str, dyn: dict) -> str:
    prev = _prev_date(date)
    if not prev:
        return ('<h2 class="main">今日变化 · 只看跟昨天不一样的</h2><div class="card">'
                '<span class="need">待接·无昨日数据</span>（7天内无更早 production·首日无从比·不编）</div>')
    changes = []          # ①结论变了
    # 1) 五层环变化
    try:
        d_prev = rj(ROOT / "data" / "evidence_chain" / f"daily_{prev}.json")
        a = {l.get("node"): l for l in (d_prev.get("links") or [])}
        b = {l.get("node"): l for l in (dyn["daily"].get("links") or [])}
        for n, cur_l in b.items():
            old = a.get(n, {})
            if old and (old.get("strength") != cur_l.get("strength") or old.get("direction") != cur_l.get("direction")):
                changes.append(f'<b>{esc(str(n))}</b>：{esc(str(old.get("strength")))}·{esc(str(old.get("direction")))} '
                               f'<b style="color:#ffd479">→</b> {esc(str(cur_l.get("strength")))}·{esc(str(cur_l.get("direction")))}')
    except Exception:
        changes.append('<span class="need">五层环差分待接</span>（昨日 daily 缺）')
    # 2) 持仓动作变化(引 final 单一源·R1)
    act_ch = []
    try:
        p_prev = {h.get("symbol"): h for h in rj(ROOT / "data" / "reports" / f"production_{prev}.json").get("holdings", [])}
        for h in dyn["prod"].get("holdings", []):
            s = h.get("symbol")
            if str(s).startswith("CC."):
                continue
            o = (p_prev.get(s) or {}).get("action")
            c = h.get("action")
            if o and c and o != c:
                act_ch.append(f'<b>{esc(str(h.get("name")))}</b>：{esc(str(o))} → {esc(str(c))}')
    except Exception:
        act_ch.append('<span class="need">动作差分待接</span>')
    # 3) 触发的阈值
    thr = []
    try:
        import full_product_render as fpr
        cost = rj(ROOT / "data" / "accounts" / "unified_holdings_latest.json")
        conc = fpr.portfolio_concentration(dyn["prod"].get("holdings", []),
                                           (cost.get("summary", {}) or {}).get("known_cash_usd"), {})
        for k, v in (conc.get("categories", {}) or {}).items():
            if v.get("over"):
                thr.append(f'⚠ <b>{esc(k)}</b> {v["pct"]:.1f}% <b>超上限 {v["limit"]}%</b>（触发·见待拍板）')
            elif v.get("short"):
                thr.append(f'⚠ <b>{esc(k)}</b> {v["pct"]:.1f}% <b>低于下限 {v["limit"]}%</b>（触发·见待拍板）')
    except Exception:
        thr.append('<span class="need">阈值现算待接</span>')
    # 4) 今日待拍板
    pend_rows = ""
    n_pend = 0
    try:
        pd_ = rj(ROOT / "data" / "pdca" / "pending_decisions.json")
        n_pend = int(pd_.get("pending_count") or 0)
        for it in pd_.get("items", []):
            chain = "".join(f'<li>{esc(c)}</li>' for c in it.get("evidence_chain", []))
            opts = "　".join(esc(o) for o in it.get("options", []))
            pend_rows += (f'<div class="card" style="background:#1c2740;border-color:#3a5a8a">'
                          f'<div class="hd"><b>[{esc(it.get("id"))}] {esc(it.get("proposal"))}</b> '
                          f'<span class="q">{esc(it.get("status"))}</span></div>'
                          f'<div style="font-size:12.5px"><span class="k">依据链(可回溯到层)</span><ul style="margin:2px 0">{chain}</ul>'
                          f'<span class="k">选项</span>{opts}<br>'
                          f'<span class="k">到期默认处理</span>{esc(it.get("default_if_expired"))}<br>'
                          f'<span class="k">您的拍板</span><b style="color:#ffd479">{esc(it.get("decision"))}</b>'
                          f'　<span style="color:#7ee0a0">→ 回复我 <b>A</b> / <b>B</b> / <b>C</b> 即可</span>'
                          f'（回了之后，明天的记分卡会自动验证这次拍板对不对）</div></div>')
    except Exception:
        pend_rows = '<div class="card"><span class="need">待拍板收件箱待接</span>（pending_decisions.json 缺）</div>'
    # 组装
    concl = ("".join(f'<div>· {c}</div>' for c in changes) if changes else '<div>· 五层环：无变化</div>')
    acts = ("".join(f'<div>· {c}</div>' for c in act_ch) if act_ch else '<div>· 持仓动作：<b>全部未变</b>（19只动作与昨日一致）</div>')
    quiet = (not changes) and (not act_ch)
    head_note = ('<div class="card" style="background:#12261f;border-color:#4f9e7f"><b>今日无重大变化（守·维持）</b>'
                 '——五层环与19只动作均与昨日一致；下方全量7层照旧，但今天不需要你逐张翻。</div>' if quiet else '')
    return ('<h2 class="main">今日变化 · 只看跟昨天不一样的（跟昨天一样的不重复占地方）</h2>'
            f'<div class="card">对比基准：<b>{esc(prev[:4])}-{esc(prev[4:6])}-{esc(prev[6:])}</b> → <b>{esc(date[:4])}-{esc(date[4:6])}-{esc(date[6:])}</b>（真数据现算）'
            f'｜今日待拍板 <b style="color:#ffd479">{n_pend}</b> 件'
            '<div class="meta" style="color:#8ea3b6;font-size:12px">只显变化+触发阈值+待拍板；全量19卡与7层在下方照旧。缺昨日数据→标待接不编。</div></div>'
            + head_note
            + '<div class="blk">① 今天哪些结论变了</div>'
            + f'<div class="card">{concl}{acts}</div>'
            + '<div class="blk">② 触发了哪个阈值</div>'
            + f'<div class="card">{"".join(f"<div>{x}</div>" for x in thr) if thr else "<div>· 无阈值触发</div>"}</div>'
            + f'<div class="blk" id="pending-inbox">③ 今日待拍板事项（{n_pend} 件·拍板收件箱）</div>'
            + (pend_rows or '<div class="card">今日无待拍板事项</div>'))

def _news_list(items: list, weak: bool = False) -> str:
    """新闻逐条渲染的唯一出口(第四轮+乙3)：完整标题/来源/日期一律不截，每条带可点原文链接；
    取不到URL→明标"无直链"。weak=True 标为弱相关·未采信。"""
    out = []
    for n in items:
        u = str(n.get("url") or "")
        link = (f'　<a href="{u}" target="_blank" style="color:#8fd6ff">阅读原文→</a>'
                if u.startswith("http") else
                f'　<span style="color:#8ea3b6">（来源:{esc(str(n.get("source","")) or "不详")}·无直链）</span>')
        tag = ('<span style="color:#c9a86a;font-size:11px">［弱相关·未采信］</span> ' if weak else "")
        jd = str(n.get("judge") or "")
        out.append(f'<div style="margin-top:3px">· {tag}<b>{esc(str(n.get("title","")))}</b>'
                   f'<br><span style="color:#8ea3b6;font-size:11.5px">来源：{esc(str(n.get("source","")))}'
                   f'　发布：{esc(str(n.get("pub_date","")))}'
                   + (f'　系统怎么看：{esc(jd)}' if jd else "")
                   + f'</span>{link}</div>')
    return "".join(out)


def part1_layers(daily: dict, dyn: dict) -> str:
    links = daily.get("links") or []
    rows = []
    for l in links:
        node = l.get("node", ""); strg = l.get("strength", ""); dr = l.get("direction", "")
        plain = l.get("plain") or l.get("today_plain") or ""
        evidence = str(l.get("evidence") or "")
        events = l.get("today_events") or []
        # 第四轮：今天怎么了 = 方向 + 逐条真新闻(完整标题/来源/日期·每条带可点原文链接)
        news = l.get("news_items") or []
        weak = l.get("weak_items") or []
        if news:
            fact = esc(str(dr)) + _news_list(news)
        elif weak:
            # 乙3：今天没有够格新闻→【不许】只甩一句"无事件·维持基线"劝退，
            # 把今天真读到、只是判为弱相关的摆出来，董事长自己看。
            fact = (esc(str(dr))
                    + f'<div style="margin-top:5px;color:#ffb454;font-size:12.5px">'
                      f'今天没有够格的重大新闻（权威源+当日+强相关），所以本层维持原判断。'
                      f'但今天<b>确实读到了下面这 {len(weak)} 条</b>——系统判它们<b>弱相关·没采信</b>，'
                      f'摆出来你自己看，别只信我这一句：</div>'
                    + _news_list(weak, weak=True))
        else:
            fact = esc(str(dr)) + ((" ｜ " + esc(str(events[0]))) if events else "")
        why = esc(evidence) if evidence else "为什么这么判：待接（daily 无 evidence·不编）"
        flip = _match(node, _LAYER_FLIP, "出现与当前方向相反的持续证据")
        ruler = _match(node, _LAYER_RULER, "第六部分·右栏底子")
        _dt = dyn.get("date", "")
        _rnum = {"world": 1, "strategy": 2, "means": 3, "capital": 3, "sector": 4, "fedgate": 3}.get(layer_slug(node), 1)
        # 甲4：每层顶部先给【一句话结论+力度】，细节收进折叠；佐证栏不再层层重复(全册合并到一处)
        _cl = {"强": "#7ee0a0", "中": "#7cc4ff", "弱": "#ffb454"}.get(str(strg).strip(), "#7cc4ff")
        head_line = (f'<div style="display:flex;align-items:baseline;gap:9px;flex-wrap:wrap">'
                     f'<b style="font-size:16px">{esc(node)}</b>'
                     f'<span style="font-size:11.5px;padding:1px 8px;border-radius:9px;'
                     f'background:{_cl};color:#0b1118;font-weight:800">力度 {esc(strg)}</span></div>'
                     f'<div style="font-size:15px;font-weight:700;color:#ffd479;margin-top:3px">'
                     f'一句话：{esc(str(dr))}</div>'
                     f'<div style="font-size:13px;color:#c8d4de;margin-top:2px">{esc(plain) if plain else ""}</div>'
                     # 丙10：这判断预计管多久(事件驱动→以周为单位沿用·现算天数)
                     + _layer_horizon(l, dyn))
        rows.append(
            f'<div class="card" id="layer-{layer_slug(node)}">{head_line}'
            + '<details class="sub" style="margin-top:8px;background:#0e1621">'
              '<summary>细节：今天怎么了 / 为什么这么判 / 落到你哪几只 / 什么情况才改看</summary>'
            + f'<div style="font-size:13px"><span class="k">① 事实(今天怎么了)</span>{fact}</div>'
            + f'<div style="font-size:13px;margin-top:3px"><span class="k">② 为什么(这么判的依据)</span>{why}</div>'
            + _layer_impact(node, dyn).replace("对你·落点持仓", "③ 对你·落点持仓")
            + f'<div style="font-size:13px;margin-top:3px"><span class="k">④ 什么情况改看法(证伪)</span>{esc(flip)}</div>'
            + _corro_brief(node)
            + '</details>'
            + f'<div class="meta" style="color:#8ea3b6;font-size:11.5px;margin-top:4px">'
              f'对应尺：{_a(L5(_dt, "ruler-" + str(_rnum)), esc(ruler))}（点跳右栏6尺册）</div>'
            '</div>')
    if not rows:
        rows.append('<div class="card">五层数据待接（daily_{date}.json 无 links·不编）</div>')
    # E2：标题按实际环数(世界观/总闸/战略/手段/资金/板块=六层)，不再写死"五层"
    _cn = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七"}.get(len(rows), str(len(rows)))
    return ('<details class="sub" open><summary>大环境今天怎么了（{}层·每层一句话结论；想看依据点开各层细节）</summary>'.format(_cn)
            + "".join(rows) + '</details>')


def _layer_horizon(l: dict, dyn: dict) -> str:
    """丙10：这一层的判断【预计管多久】——事件驱动的以周为单位沿用，并现算"已连续第N天"。"""
    node = str(l.get("node") or "")
    news_n = len(l.get("news_items") or [])
    # 已连续多少天同方向(往回数真实历史·不写死)
    days = 1
    try:
        d = dyn.get("date", "")
        seen = d
        for _ in range(30):
            p = _prev_date(seen)
            if not p:
                break
            try:
                pd_ = rj(ROOT / "data" / "evidence_chain" / f"daily_{p}.json")
            except Exception:
                break
            pl = next((x for x in (pd_.get("links") or []) if str(x.get("node")) == node), None)
            if not pl or str(pl.get("direction")) != str(l.get("direction")):
                break
            days += 1
            seen = p
    except Exception:
        pass
    if news_n:
        txt = (f"这判断预计管多久：<b>没出反向大事之前，以「周」为单位沿用</b>——它是被事件推着走的，"
               f"不是每天翻一次。今天有 {news_n} 条够格新闻支持这个判断，已经<b>连续第 {days} 天</b>是这个方向。")
    else:
        txt = (f"这判断预计管多久：<b>没出反向大事之前，以「周」为单位沿用</b>——今天没有够格的新事件，"
               f"所以维持原判断，已经<b>连续第 {days} 天</b>是这个方向。")
    return (f'<div style="font-size:11.5px;color:#9db0c2;margin-top:4px;'
            f'border-left:3px solid #3a5a8a;padding-left:7px">{txt}</div>')


def _corro_brief(node: str) -> str:
    """甲4：层内佐证只留一句结论；"料已N天旧"这句全册只在①册顶部说一次(不再层层重复)。"""
    h = corro_box(node, "layer")
    h = re.sub(r"<b style=\"color:#ffb454\">（这份料已放了 \d+ 天[^<]*）</b>", "", h)
    h = re.sub(r"（料非当日·仅方向性参考）", "", h)
    return h

# ── 第一部分附·宏观判定表（尺模板+当日读数） ──
def part1_macro_table(daily: dict) -> str:
    der = daily.get("derived", {}) or {}
    td = esc(str(der.get("today_direction", "待接")))
    # E2：当日读数按六层逐层列全(原只列4项·缺世界观/手段层)
    rows6 = ""
    for l in (daily.get("links") or []):
        rows6 += (f'<tr><td><b>{esc(str(l.get("node","")))}</b></td>'
                  f'<td>{esc(str(l.get("strength","待接")))}</td>'
                  f'<td>{esc(str(l.get("direction","待接")))}</td></tr>')
    six = ('<table border="1" cellpadding="5" style="border-collapse:collapse;font-size:13px;margin-top:8px">'
           '<tr><th>这一层</th><th>今天几分力</th><th>今天什么方向</th></tr>' + rows6 + '</table>') if rows6 else ""
    return ('<h2 class="sub">附：宏观指标怎么算强/中/弱/证伪（判定标准·尺）</h2>'
            '<div class="card"><table border="1" cellpadding="5" style="border-collapse:collapse;font-size:13px">'
            '<tr><th>档</th><th>含义（尺）</th></tr>'
            '<tr><td>强</td><td>方向明确成立、证据充分</td></tr>'
            '<tr><td>中</td><td>方向成立但力度一般/证据部分</td></tr>'
            '<tr><td>弱</td><td>方向存疑/证据转软</td></tr>'
            '<tr><td>证伪</td><td>反向证据出现、判断被推翻</td></tr></table>'
            + six +
            f'<div class="you" style="margin-top:6px">今天一句话总读数：{td}</div></div>')

# ── 第三部分·集中度%（复用 full_product_render.portfolio_concentration 现算） ──
# ── 第三部分附·R9 共同风险因子穿透（挂哪几只+合计敞口%·敞口由当日production市值现算·映射data驱动可联动） ──
def _mv_usd_by_symbol(holdings: list, cost_by_ticker: dict | None) -> tuple[dict, float]:
    """复用 fpr 折算:每只 market_value→统一美元;返回 {symbol:mv_usd} 与合计(分母)。缺市值不入分母。"""
    import full_product_render as fpr
    usdjpy, _ = fpr.resolve_usdjpy()
    out = {}
    for h in holdings:
        sym = str(h.get("symbol") or "")
        mv_usd, _note = fpr._mv_usd(h, usdjpy)
        if mv_usd is None and fpr._is_crypto(sym):
            mv_usd = fpr._crypto_mv_fallback(sym, cost_by_ticker)
        if mv_usd is not None:
            out[sym] = float(mv_usd)
    return out, sum(out.values())

def part3_risk_factors(dyn: dict) -> str:
    """R9:共同风险因子穿透。每因子列成分股+合计敞口%(敞口=成分股当日折美元市值/全持仓合计)。
    映射读 data/valuation/risk_factors.json(可迭代·改一只归属→本表数字联动变)。"""
    try:
        rf = rj(ROOT / "data" / "valuation" / "risk_factors.json")
    except Exception as e:
        return f'<div class="card">共同风险因子表·待接（映射缺：{esc(e)}）</div>'
    by_sym = rf.get("by_symbol", {}) or {}
    order = rf.get("factor_order") or sorted({f for v in by_sym.values() for f in v})
    try:
        cost = rj(ROOT / "data" / "accounts" / "unified_holdings_latest.json")
        cbt = None
        try:
            import full_product_render as fpr
            cbt = fpr.cost_by_ticker(cost) if hasattr(fpr, "cost_by_ticker") else (cost.get("by_ticker") or {})
        except Exception:
            cbt = cost.get("by_ticker") or {}
    except Exception:
        cbt = {}
    holds = dyn["prod"].get("holdings", [])
    name_by = {str(h.get("symbol")): str(h.get("name") or h.get("symbol")) for h in holds}
    mv, total = _mv_usd_by_symbol(holds, cbt)
    if total <= 0:
        return '<div class="card">共同风险因子表·待接（分母市值合计=0·当日无可折算市值）</div>'
    # 乙8：条形图化——让"一个坏消息砸中好几只"看得见(数字/口径不变·只换画法)
    bars = []
    for f in order:
        members = [s for s, fs in by_sym.items() if f in fs and s in name_by]
        expo = sum(mv.get(s, 0.0) for s in members)
        pct = expo / total * 100.0
        mem_txt = "、".join(f"{esc(name_by[s])}" + ("" if s in mv else "(市值缺·未计敞口)") for s in members) or "—"
        bars.append((pct, _bar_row(f, pct, note=f"砸中：{mem_txt}")))
    bars.sort(key=lambda x: -x[0])          # 占比大的排前面=最该先看
    tbl = "".join(b for _p, b in bars)
    note = ('<div class="meta" style="color:#8ea3b6;font-size:12px;margin-top:8px">'
            '条越长=这个坏消息一旦发生、会同时砸到你越多的钱。'
            '敞口%=该因子成分股当日折美元市值合计÷全持仓合计（按当日实时价现算·非写死）；'
            '一只股票可能同时挂几个因子，所以各条相加会超过100%——这正是"押得重叠"的意思。</div>')
    return ('<h3 style="margin-top:14px">第三部分附 · 共同风险因子穿透（同一个坏消息会同时打到哪几只）</h3>'
            '<div class="card">' + tbl + note + '</div>')

def part3_concentration(date: str, dyn: dict) -> str:
    try:
        import full_product_render as fpr
        cost = rj(ROOT / "data" / "accounts" / "unified_holdings_latest.json")
        conc = fpr.portfolio_concentration(dyn["prod"].get("holdings", []),
                                           (cost.get("summary", {}) or {}).get("known_cash_usd"), {})
        # 乙7：横条形图 + 上限红虚线 / 下限黄虚线 —— 超上限红、不足下限黄(数字口径不变)
        # ⚠必须读上游的 kind：'upper'=这数是上限、'lower'=这数是下限。
        #   上游把阈值一律放在 limit 字段、靠 kind/over/short 区分方向；
        #   我原来不看 kind 直接当上限画 → 防御(kind=lower·15%是"至少要保持")被画成"上限15%·在限内(蓝)"，
        #   与同册头条/待拍板的"低于15%下限·要拍板"打架。同一个15%，图叫上限、头条叫下限。
        rows = []
        for k, v in (conc.get("categories", {}) or {}).items():
            thr = v.get("limit") if v.get("limit") is not None else v.get("floor")
            is_lower = str(v.get("kind")) == "lower" or bool(v.get("short"))
            rows.append(_bar_row(k, float(v.get("pct") or 0),
                                 limit=(None if is_lower else thr),
                                 floor=(thr if is_lower else v.get("floor"))))
        conc_html = ('<h2 class="sub">仓位集中度 · 哪一类押太多了</h2><div class="card">'
                     + "".join(rows)
                     + '<div class="meta" style="color:#8ea3b6;font-size:11.5px;margin-top:8px">'
                       '条越长=押得越多。<span style="color:#ff5c5c">红虚线</span>=上限、'
                       '<span style="color:#ffd479">黄虚线</span>=下限；条变红=超了上限，变黄=不到下限。'
                       '按当日实时价折美元现算。</div></div>')
    except Exception as e:
        conc_html = f'<h2 class="sub">仓位集中度</h2><div class="card">集中度现算失败·待接（{esc(e)}）</div>'
    return conc_html + part3_risk_factors(dyn)

# ── 第四部分·机会池 6a(R6：候选现算+每候选带'节点+当日证据'·证据驱动) ──
def _active_nodes(daily: dict) -> list[str]:
    td = str((daily.get("derived", {}) or {}).get("today_direction", ""))
    m = re.search(r'激活承接节点[：:]\s*([^\n。]+)', td)
    return [x.strip() for x in re.split(r'[、,，]', m.group(1)) if x.strip()] if m else []

def _node_key(node: str) -> str:
    for k in ("算力", "半导体设备", "代工", "存储", "盟友链", "盟友"):
        if k in node or (k == "半导体设备" and "设备" in node):
            return k
    return node

def part4_opportunity(daily: dict, dyn: dict) -> str:
    der = daily.get("derived", {}) or {}
    active = _active_nodes(daily)
    try:
        import full_product_render as fpr
        wl = list(fpr.OPP_WATCHLIST)
    except Exception:
        wl = []
    rows = []; in_pool = 0
    for c in wl:
        name = c.get("name", ""); node = c.get("node", ""); nk = _node_key(node)
        is_active = nk in active
        if is_active:
            in_pool += 1
            evid = f'其节点「{nk}」今日在激活承接节点内（引②战略/⑥板块·当日证据）→ 进池候选（只换不加·AI已超配）'
            badge = "进池·今日激活"
        else:
            evid = f'其节点「{nk}」今日未在激活承接节点内 → 暂不进池（当日证据不足·不编）'
            badge = "暂不进池"
        rows.append(f'<div class="card"><div class="hd"><b>候选 {esc(name)}</b> '
                    f'<span class="conf">节点：{esc(node)}</span> <span class="q">{esc(badge)}</span></div>'
                    f'<div class="you" style="font-weight:400">当日证据：{esc(evid)}</div></div>')
    if not rows:
        rows.append('<div class="card">候选watchlist待接（OPP_WATCHLIST 缺）</div>')
    scope = esc(str(der.get("opportunity_scope", "待接")))
    # 甲3：不再自报"现算候选 3/3 进池"(与五关漏斗的23→19→5并存=两套口径)。
    # 全篇机会数字唯一出处 = funnel_scope_line；本节只是候选宇宙里"已配好换法"的重点几只展开。
    # 甲2：标题原写"（证据驱动·6a）"，术语清洗把内部编号 6a 抹掉后剩"（证据驱动·）"悬空标点→直接不写编号
    head = ('<h2 class="main">机会池：该不该换、换谁</h2>'
            f'<div class="card"><b>今天的机会池全貌（全篇唯一口径）</b>：{funnel_scope_line(dyn["date"], daily, dyn)}'
            f'　→ 逐只五关明细见本册下方「五关漏斗」。'
            f'<div style="margin-top:5px">当日激活承接节点(证据源)：{esc("、".join(active) or "待接")}｜机会口径：{scope}</div>'
            f'<div class="meta" style="color:#8ea3b6;font-size:12px">本节展开的是候选宇宙里已预配「换谁」方案的重点 {len(wl)} 只'
            f'（其中 {in_pool} 只节点今日激活）——它们是上面那{esc(str(n_uni_of(dyn["date"], daily, dyn)))}只的子集、不是另一套池子。'
            '候选是否进池由「节点是否在当日激活承接节点」现算·改当日证据→候选集变（6b替换引擎）</div></div>')
    return head + "".join(rows)


def n_uni_of(date: str, daily: dict | None = None, dyn: dict | None = None) -> int:
    """候选宇宙"按标的唯一"的只数。

    乙6：这里原来自己数一遍(把 ticker='待接' 的节点占位也当标的→22)，而五关漏斗那边已按
    "无真代码非标的"剔除→21，两处又打架。改为【直接问同一个算子】，不许自己数。
    """
    if daily is not None and dyn is not None:
        return funnel_compute(date, daily, dyn)["n_total"]
    try:
        uni = rj(ROOT / "data" / "valuation" / "candidate_universe.json").get("nodes", {}) or {}
        return len({str(c.get("ticker")) for v in uni.values() for c in (v or [])
                    if c.get("ticker") and str(c.get("ticker")) not in ("待接", "TBD", "-")})
    except Exception:
        return 0

# ── 第四部分附·R6-6b 替换引擎（把6a候选升级为"换不换"决策：多维比较+为何不换/什么价换+换后集中度联动） ──
def _resolve_sym(ticker: str, holds: list) -> str | None:
    t = ticker.upper()
    for h in holds:
        s = str(h.get("symbol") or "")
        if s.split(".")[-1].upper() == t:
            return s
    return None

def part4b_swap_engine(daily: dict, dyn: dict) -> str:
    try:
        import full_product_render as fpr
        wl = list(fpr.OPP_WATCHLIST)
    except Exception:
        wl = []
    try:
        rf = rj(ROOT / "data" / "valuation" / "risk_factors.json")
        by_sym = rf.get("by_symbol", {}) or {}; cand_fac = rf.get("candidate_factors", {}) or {}
    except Exception:
        by_sym = {}; cand_fac = {}
    holds = dyn["prod"].get("holdings", [])
    name_by = {str(h.get("symbol")): str(h.get("name") or h.get("symbol")) for h in holds}
    try:
        cost = rj(ROOT / "data" / "accounts" / "unified_holdings_latest.json"); cbt = cost.get("by_ticker") or {}
    except Exception:
        cbt = {}
    mv, total = _mv_usd_by_symbol(holds, cbt)
    active = _active_nodes(daily)
    def _expo(members):
        return (sum(mv.get(s, 0.0) for s in members) / total * 100.0) if total > 0 else 0.0
    cards = []
    for c in wl:
        cname = c.get("name", ""); node = c.get("node", ""); nk = _node_key(node)
        is_active = nk in active
        cfacs = cand_fac.get(cname, [])
        for tk, aname in (c.get("swap") or []):
            asym = _resolve_sym(tk, holds)
            if not asym:
                continue
            fa = build_final(asym, name_by.get(asym, aname), dyn)
            a_mvusd = mv.get(asym, 0.0)
            a_pct = (a_mvusd / total * 100.0) if total > 0 else 0.0
            a_facs = by_sym.get(asym, [])
            # 换后:A的$额平移给候选 → 从A的因子里减掉a_mv、加到候选的因子里(总额不变)
            moved = set(a_facs) | set(cfacs)
            deltas = []
            for f in sorted(moved):
                members = [s for s in by_sym if f in by_sym[s] and s in name_by]
                before = _expo(members)
                after_mv = sum(mv.get(s, 0.0) for s in members)
                if f in a_facs: after_mv -= a_mvusd     # A 退出该因子
                if f in cfacs: after_mv += a_mvusd      # 候选进入该因子(承 A 的$)
                after = (after_mv / total * 100.0) if total > 0 else 0.0
                if abs(after - before) >= 0.05:
                    arrow = "↑" if after > before else "↓"
                    deltas.append(f'{esc(f)} {before:.1f}%→{after:.1f}%{arrow}')
            delta_txt = "；".join(deltas) if deltas else "该配对下各风险因子敞口基本不变（候选与A因子高度重叠）"
            # 多维比较(护城河/估值/方向/集中度)：A有真数据·候选定性(缺估值源不编)
            # 件四①：禁止把 production 的内部字典原样打印进产品(曾泄露 {'status':'待理解岗打分',...})
            _m = (next((h for h in holds if h.get("symbol") == asym), {}) or {}).get("moat")
            if isinstance(_m, dict):
                _g = _m.get("moat_grade") or _m.get("grade") or ""
                moat_a = esc(str(_g)) if _g else "护城河评级待补（见该只持仓卡③护城河五维）"
            elif _m:
                moat_a = esc(str(_m))[:40]
            else:
                moat_a = "护城河评级待补（见该只持仓卡③护城河五维）"
            cmp_tbl = ('<table style="width:100%;border-collapse:collapse;font-size:12.5px;margin:6px 0">'
                       '<tr style="color:#8ea3b6"><th style="text-align:left;padding:4px 6px">维度</th>'
                       f'<th style="text-align:left;padding:4px 6px">持仓A：{esc(name_by.get(asym, aname))}</th>'
                       f'<th style="text-align:left;padding:4px 6px">候选：{esc(cname)}</th></tr>'
                       f'<tr><td style="padding:4px 6px">护城河</td><td style="padding:4px 6px">{moat_a}</td>'
                       f'<td style="padding:4px 6px">同赛道·候选未入判断包（护城河待接·不编）</td></tr>'
                       f'<tr><td style="padding:4px 6px">估值</td><td style="padding:4px 6px">{f_esc(fa["valuation"])}</td>'
                       f'<td style="padding:4px 6px">候选无估值源（待接·不编）</td></tr>'
                       f'<tr><td style="padding:4px 6px">方向</td><td style="padding:4px 6px">{f_esc(fa["action"])}</td>'
                       f'<td style="padding:4px 6px">节点「{esc(nk)}」{"今日激活" if is_active else "今日未激活"}</td></tr>'
                       f'<tr><td style="padding:4px 6px">集中度</td><td style="padding:4px 6px">A当前占比 {a_pct:.1f}%</td>'
                       f'<td style="padding:4px 6px">同额置换后候选承 {a_pct:.1f}%</td></tr></table>')
            # 为什么现在不换/什么价换
            if is_active:
                why = (f'节点「{esc(nk)}」今日激活，方向上候选有承接逻辑；但<b>候选无估值源/未入判断包</b>，'
                       f'不满足「同类更优且更便宜」硬条件 → <b>现在不换</b>（缺证据不编）。')
                trigger = (f'什么价换：候选进入判断包并给出估值区间、且相对A出现明确折价（或A基本面/估值转弱触发退出条件）时，'
                           f'再按「只换不加·同额置换」评估。')
            else:
                why = (f'节点「{esc(nk)}」今日<b>未激活</b>，承接逻辑不成立 → <b>现在不换</b>（当日证据不足·不编）。')
                trigger = (f'什么价换：待其节点进入当日激活承接节点、且候选估值相对A折价成立时再议。')
            cards.append('<div class="card">'
                         f'<div class="hd"><b>替换评估：{esc(cname)} ⇄ {esc(name_by.get(asym, aname))}</b> '
                         f'<span class="q">{"换不换：现在不换" }</span></div>'
                         + cmp_tbl
                         + f'<div class="you" style="font-weight:400">{why}</div>'
                         + f'<div class="you" style="font-weight:400;color:#9ed8ff">{trigger}</div>'
                         + f'<div class="you" style="margin-top:5px"><b style="color:#5cc8ff">换完后集中度/风险因子如何变（同额置换·现算）</b>：{delta_txt}</div>'
                         '</div>')
    if not cards:
        cards.append('<div class="card">替换引擎·待接（OPP_WATCHLIST 无 swap 配对或分母市值缺）</div>')
    head = ('<h3 style="margin-top:14px">第四部分附 · 替换引擎 6b（该不该"换"：候选 vs 同类持仓A 多维比较+换后集中度联动）</h3>'
            '<div class="card" style="color:#8ea3b6;font-size:12px">每条给：①护城河/估值/方向/集中度多维比较；'
            '②为什么现在不换、什么价换；③同额置换后集中度与风险因子敞口「换前→换后」现算（映射见 data/valuation/risk_factors.json·可迭代联动）。只换不加（AI已超配）。</div>')
    return head + "".join(cards)

def f_esc(x):
    return esc(str(x))

# ── 第四部分附·⑤机会池全市场五关漏斗(总则第十四条:候选宇宙→五关现算→三个池) ──
_NODE_ALIAS = {"算力": ["算力"], "半导体设备": ["半导体设备", "设备"], "代工": ["代工"],
               "存储": ["存储"], "盟友链": ["盟友链", "盟友"], "电力核电": ["电力核电", "电力", "核电"]}
def _node_active(node: str, active: list) -> bool:
    keys = _NODE_ALIAS.get(node, [node])
    return any(k in a or a in k for a in active for k in keys)

_FUNNEL_CACHE: dict = {}


def _featured_names() -> list[str]:
    """6a 单独展开的"重点几只"(OPP_WATCHLIST)——五关漏斗的"其余N只"要排除它们，防两处打架。"""
    try:
        import full_product_render as fpr
        return [str(c.get("name", "")) for c in fpr.OPP_WATCHLIST]
    except Exception:
        return []


def _is_featured(name: str, feat: list[str]) -> bool:
    """名字写法不一致(“海力士(SK Hynix)” vs “SK海力士”)→按去括号后的核心词互含判定。"""
    def core(x: str) -> str:
        return re.sub(r"[（(].*?[）)]|·.*$|\s", "", str(x)).strip()
    n = core(name)
    if not n:
        return False
    for f in feat:
        c = core(f)
        if c and (c in n or n in c):
            return True
    return False


def funnel_compute(date: str, daily: dict, dyn: dict) -> dict:
    """甲3：机会池唯一口径的单一算子。6a标题/摘要表/五关漏斗全都只读这里的数字，
    不许各算各的(原来 6a 报'3/3进池'、漏斗报'23→19→5'=两套并存)。"""
    ck = (date, id(daily))
    if ck in _FUNNEL_CACHE:
        return _FUNNEL_CACHE[ck]
    r = _funnel_compute_raw(date, daily, dyn)
    _FUNNEL_CACHE[ck] = r
    return r


def _funnel_compute_raw(date: str, daily: dict, dyn: dict) -> dict:
    active = _active_nodes(daily)
    try:
        uni = rj(ROOT / "data" / "valuation" / "candidate_universe.json").get("nodes", {}) or {}
    except Exception as e:
        return {"err": str(e), "active": active, "rows": [], "worth": [],
                "n_total": 0, "n_g1": 0, "n_g2": 0}
    # gate②数据源:复用当日 chain_opportunities 真均线扫描(过硬性关=站上MA)
    ma_pass = {}
    try:
        ch = rj(ROOT / "data" / "opportunities" / f"chain_opportunities_{date}.json")
        for c in ch.get("candidates", []) or []:
            code = str(c.get("code") or "")
            t = c.get("technical", {}) or {}
            ma_pass[code] = {"price": t.get("latest_price"), "chg20": t.get("change_20d_pct"),
                             "pass": "站上MA" in str(c.get("hit_reason", "")) or "站上" in str(c.get("hit_reason", ""))}
    except Exception:
        ma_pass = {}
    # 逐候选跑五关(现算)
    worth = []      # 值得看候选池(过硬性关·节点激活)
    all_rows = []
    # 甲3：同一只标的可挂多个节点(如联电=算力+代工)→按标的唯一去重、节点合并成一行，不出两张重复卡
    merged: dict[str, dict] = {}
    for node, cands in uni.items():
        for c in (cands or []):
            nm = c.get("name", ""); tk = str(c.get("ticker") or "")
            key = tk or nm
            if key in merged:
                if node not in merged[key]["nodes"]:
                    merged[key]["nodes"].append(node)
            else:
                merged[key] = {"name": nm, "ticker": tk, "nodes": [node], "source": c.get("source", "")}
    for uc in merged.values():
        if True:
            nm = uc["name"]; tk = uc["ticker"]
            # 甲6：候选宇宙里混了"(定义级·盟友供应链)"这种【节点定义占位】(ticker='待接')，
            # 它不是一只标的，不许算进只数(原来 N=14 里有 1 个是它 → 清单实际13只≠称14)。
            # 判据=没有真代码：守第六条"只锚定义不锚死名单"，占位保留在数据里、只是不当标的数。
            if (not tk) or tk in ("待接", "TBD", "-"):
                continue
            node = "／".join(uc["nodes"])                          # 合并后的节点显示(联电=算力／代工)
            c = {"source": uc["source"]}
            g1 = any(_node_active(n, active) for n in uc["nodes"])  # ①硬性:任一挂靠节点激活即过
            mp = ma_pass.get(tk)
            g2 = ("过·站上均线" if (mp and mp.get("pass")) else ("待接·未在当日扫描" if mp is None else "卡·未站上均线"))
            g3 = "待接·候选估值未接"                                  # ③估值(外部候选无估值源)
            g4 = "待接·候选护城河未接"                                # ④护城河
            g5 = "待接·候选未入判断包"                                # ⑤个股
            # 过到第几关
            if not g1:
                stage = "卡在①硬性关（节点今日未激活）"
            elif not (mp and mp.get("pass")):
                stage = ("过①硬性·②起待接（未在当日均线扫描内）" if mp is None else "卡在②软性关（未站上均线）")
            else:
                stage = "过①②·③起待接（估值/护城河/个股需接真源）"
            price_txt = (f"·现价{mp['price']}·20日{mp['chg20']:+.1f}%" if mp and mp.get("price") is not None else "")
            row = {"node": node, "name": nm, "ticker": tk, "g1": g1, "g2": g2, "stage": stage, "price_txt": price_txt,
                   "source": c.get("source", "")}
            all_rows.append(row)
            if g1:
                worth.append(row)
    # 过关分布统计(全篇唯一口径·甲3)
    n_total = len(all_rows); n_g1 = sum(1 for r in all_rows if r["g1"])
    n_g2 = sum(1 for r in all_rows if r["g1"] and "过·站上" in r["g2"])
    return {"err": "", "active": active, "rows": all_rows, "worth": worth,
            "n_total": n_total, "n_g1": n_g1, "n_g2": n_g2}


def funnel_scope_line(date: str, daily: dict, dyn: dict) -> str:
    """机会池唯一口径的一句话·全篇任何地方要报机会数字都引它(甲3双漏斗根治)。"""
    fc = funnel_compute(date, daily, dyn)
    if fc.get("err"):
        return "候选宇宙待接"
    return (f'候选宇宙 <b>{fc["n_total"]}</b> 只（按标的唯一计·一只挂多节点只算一次）'
            f' → 过①硬性关(节点激活) <b>{fc["n_g1"]}</b> 只'
            f' → 过②软性关(站上均线) <b>{fc["n_g2"]}</b> 只')


def part4_funnel(date: str, daily: dict, dyn: dict) -> str:
    fc = funnel_compute(date, daily, dyn)
    if fc.get("err"):
        return ('<h2 class="sub">附：机会池全扫</h2>'
                f'<div class="card">候选宇宙待接（candidate_universe.json 缺：{esc(fc["err"])}）</div>')
    active = fc["active"]; all_rows = fc["rows"]; worth = fc["worth"]
    n_total, n_g1, n_g2 = fc["n_total"], fc["n_g1"], fc["n_g2"]
    # 池一:值得看候选池
    # 件六②去重：把"护城河待接/估值待接/节点X今日激活/AI簇已超配只换不加"这类逐字重复的话
    # 归纳成一句总述，只对【有实质区别的】(过了均线关·有真价数据)逐只展开。
    distinct = [r for r in worth if "过·站上" in r["g2"]]
    # 甲6：上面 6a 已经把"重点几只"(已预配换法的)单独展开过了 → 这里【排除】它们，
    # 否则同一只(东京电子/美光/SK海力士)在 6a 说"进池·今日激活"、在这里又被归进"没扫到价·都不动"，
    # 两处说法相反、且被数了两遍。
    _feat = _featured_names()
    same = [r for r in worth if "过·站上" not in r["g2"] and not _is_featured(r["name"], _feat)]
    _same_feat = [r for r in worth if "过·站上" not in r["g2"] and _is_featured(r["name"], _feat)]
    wrows = ""
    if same:
        by_node = {}
        for r in same:
            by_node.setdefault(r["node"], []).append(r["name"])
        lines = "；".join(f'<b>{esc(k)}</b>：{esc("、".join(v))}' for k, v in by_node.items())
        wrows += ('<div class="card"><div class="hd"><b>其余 %d 只候选（情况完全相同·合并成一条说）</b></div>'
                  '<div style="font-size:13px">%s</div>'
                  '<div class="plain">这%d只今天的情况<b>一模一样</b>，所以不逐张重复：'
                  '它们的节点今天是热的（过了第一关），但<b>今天的全市场扫描没扫到它们的价格/均线</b>，'
                  '所以第二关往后没法判；而且它们都还没做过估值和护城河研究（不在你持仓里）。'
                  '结论也一样：<b>今天都不动</b>——AI这块你已经超配，只换不加。'
                  '真要动，先等它们进到下面这几只“有真实价格数据”的行列里再说。'
                  '%s</div></div>'
                  % (len(same), lines, len(same),
                     ('（本册开头单独展开的 <b>' + esc("、".join(r["name"] for r in _same_feat))
                      + '</b> 情况其实和这几只一样——节点热、但今天没扫到价，'
                        '所以也都不动；那几只单列只是因为已经先想好了"要换的话拿谁换"。）')
                     if _same_feat else ""))
    for r in distinct:
        cmp_tbl = ('<table class="dt" style="margin:4px 0"><tr style="color:#8ea3b6"><th>维度</th><th>候选</th></tr>'
                   f'<tr><td>护城河</td><td>{esc(r["g4"] if "g4" in r else "待接·候选未入判断包")}</td></tr>'
                   f'<tr><td>估值</td><td>待接·候选估值未接</td></tr>'
                   f'<tr><td>方向</td><td>节点「{esc(r["node"])}」今日激活（gate①过）</td></tr>'
                   f'<tr><td>换进来集中度变化</td><td>若换入→加到「{esc(r["node"])}」相关风险因子敞口(见第三部分附);AI簇已超配·只换不加</td></tr></table>')
        wrows += (f'<div class="card"><div class="hd"><b>{esc(r["name"])}</b> <span class="sym">{esc(r["ticker"])}</span> '
                  f'<span class="conf">节点：{esc(r["node"])}</span> <span class="q">{esc(r["stage"])}</span></div>'
                  f'<div class="you" style="font-weight:400;font-size:12.5px">当日证据：节点「{esc(r["node"])}」在今日激活承接节点内{esc(r["price_txt"])}｜{esc(r["g2"])}｜来源：{esc(r["source"])}</div>'
                  + cmp_tbl + '</div>')
    if not wrows:
        wrows = '<div class="card">今天没有候选过第一关（激活节点里的候选都还没有价格/均线数据·不编）</div>'
    # 池二:用户挑战池(结构·待董事长指定)
    pool2 = ('<div class="blk">池② 用户挑战池（董事长想挑战/加看的标的·跑同样五关给结论）</div>'
             '<div class="card"><span class="need">待董事长指定</span>——结构已留：董事长点名任一标的，即按同一五关漏斗(①硬性②软性③估值④护城河⑤个股)现算给"过到第几关/卡在哪关+结论"。（缺指定→不编）</div>')
    # 池三:等好价标的池(好公司但贵·记便宜位到价提醒)
    pool3 = ('<div class="blk">池③ 等好价标的池（好公司但估值贵·记下便宜位·到价提醒）</div>'
             # 丙10：等好价必须标时间跨度+没有到期时间
             '<div class="plain"><b>这里说的"便宜位"是什么时间跨度</b>：也是<b>按公司未来约 1~2 年该值多少</b>算出来的，'
             '不是猜下个月的股价。<b>它没有到期时间</b>——不是"多久之内必须买"，而是<b>便宜了就提醒你</b>，'
             '一直没便宜就一直不动。</div>'
             '<div class="card">结构已留：好公司但当前估值贵者入此池、记"便宜买入位"、到价提醒。'
             '当前候选宇宙外部标的估值多为<span class="need">待接·候选估值未接</span>；持仓中估值偏贵者(如IBKR现价约37倍前瞻>正常化中枢$52.8)已在其个股卡⑤标注等更好点位。外部候选到价提醒待接入候选估值后启用。</div>')
    scope = esc(str((daily.get("derived", {}) or {}).get("opportunity_scope", "待接")))
    head = ('<h2 class="sub">附：全市场五关漏斗（候选宇宙→五关现算→三个池）</h2>'
            f'<div class="card">当日激活承接节点：<b>{esc("、".join(active) or "待接")}</b>｜候选宇宙 {n_total} 只(按节点·candidate_universe.json可迭代)｜'
            f'过①硬性关(节点激活) <b>{n_g1}</b> 只｜过②软性关(站上均线) <b>{n_g2}</b> 只。'
            f'<div class="meta" style="color:#8ea3b6;font-size:12px">五关=①硬性(节点激活)②软性(均线)③估值④护城河⑤个股；过关进"值得看候选池"。改当日激活节点→候选集变(守第六条动态)。gate②均线复用当日 chain_opportunities 真扫描·③④⑤缺真源标待接不编。｜机会口径：{scope}</div></div>')
    return (head + corro_box("机会池", "layer")
            + f'<div class="blk">池① 值得看候选池（过①硬性关 {n_g1} 只·带节点+当日证据+多维对比）</div>'
            + wrows + pool2 + pool3)

def part5_closeloop(daily: dict) -> str:
    der = daily.get("derived", {}) or {}
    close = esc(str(der.get("today_direction_short") or der.get("today_direction", "待接")))
    return '<h2 class="sub">整条逻辑怎么闭环</h2>' + f'<div class="card">{close}</div>'

# ── 第六部分·6把尺 embed（读右栏_*.html body·浅色皮折叠·7块含②补） ──
def _ruler_body(fname: str) -> str:
    p = ROOT / "00_请先看这里" / fname
    if not p.exists():
        return f'<span style="color:#c9a86a">待接·缺 {esc(fname)}</span>'
    raw = p.read_text(encoding="utf-8")
    m = re.search(r'<body[^>]*>(.*?)</body>', raw, flags=re.S)
    inner = m.group(1) if m else raw
    inner = re.sub(r'<script[^>]*>.*?</script>', '', inner, flags=re.S)
    return inner

def part6_rulers() -> str:
    RULERS = [
        ("右栏① 世界观 · 完整底子", "右栏_完整世界观描述.html", True),
        # 去重:②与②补原嵌同一文件→整块重复两份；安全/能源线已并入②文件内、只留一条(内容各留一份)
        ("右栏② 国家战略地图 · 完整底子（含安全线／能源线完整地图）", "右栏_完整国家战略地图.html", False),
        ("右栏③ 资金流动完整机制", "右栏_资金流动完整机制.html", False),
        ("右栏④ 板块地图", "右栏_板块地图.html", False),
        ("右栏⑤ 过滤标准／筛选规则", "右栏_过滤标准筛选规则.html", False),
        ("右栏⑥ 持仓完整档案", "右栏_持仓完整档案.html", False),
    ]
    folds = []
    for i, (title, fname, opened) in enumerate(RULERS, start=1):
        body = _ruler_body(fname)
        # 硬链2：左栏各层"对应尺"→本册 #ruler-{i}
        folds.append(f'<details class="ruler-embed" id="ruler-{i}"{" open" if opened else ""}>'
                     f'<summary>{esc(title)}</summary>'
                     f'<div style="background:#f6f2e8;color:#2a2a2a;padding:10px;border-radius:6px">{body}</div></details>')
    return '<h2 class="main">右栏底子 · 6把尺（判断依据）</h2>' + "".join(folds)


# ── 第七部分·PDCA接真记分(R7：昨判今验+累计+预测字段·底气与总闸final同源) ──
def track_days(date: str) -> tuple[int, str]:
    """全册唯一的"追踪了几天"。

    甲1：必须【不晚于本次数据日】才算数——history 里混进过 20260717(比数据日20260716还新、
    且在文件里排在16前面)，导致这里数出 10 天、而复盘段按真实序列说"这9天里" → 打架。
    与 pillars_now 用同一截断口径 → 记分卡内天数全册一致。
    """
    dates = set()
    try:
        for r in (rj(ROOT / "data" / "pdca" / "scorecards.json").get("history") or []):
            if r.get("date"):
                dates.add(str(r["date"]))
    except Exception:
        pass
    try:
        # 两个记录源日期不完全一致(记分卡历史曾漏记 07-03)→取并集为真实追踪日，全册统一
        for t in (rj(ROOT / "data" / "pdca" / f"pdca_review_{date}.json").get("certainty_trajectories") or []):
            for s in (t.get("daily_score_series") or []):
                if s.get("date"):
                    dates.add(str(s["date"]))
    except Exception:
        pass
    ds = sorted(d for d in dates if d <= date)      # ← 不许把"未来日"数进今天的追踪天数
    return (len(ds), ds[0]) if ds else (0, "?")


def part7_pdca(date: str, daily: dict | None = None) -> str:
    pd = rj(ROOT / "data" / "pdca" / f"pdca_daily_{date}.json")
    rv = rj(ROOT / "data" / "pdca" / f"pdca_review_{date}.json")
    rings = pd.get("rings") or []
    traj = {t.get("ring_id"): t for t in (rv.get("certainty_trajectories") or [])}
    # R7 底气与总闸 final 同源(治B3③)：读第一部分总闸(R2状态机)而非旧 decision_quality
    fed_dir = fed_str = "待接"
    if daily:
        fed = next((l for l in (daily.get("links") or []) if "总闸" in str(l.get("node"))), {})
        fed_dir, fed_str = fed.get("direction", "待接"), fed.get("strength", "待接")
    # 件四④：样本太少→加人话兜底，不裸露 0/9 吓人
    _days, _start = track_days(date)
    _caveat = (f'<div class="card" style="background:#12261f;border-color:#4f9e7f">'
               f'<b style="color:#7ee0a0">先看这句：</b>这套记分系统<b>从 {esc(_start[:4])}-{esc(_start[4:6])}-{esc(_start[6:])} 起、'
               f'到今天一共只追踪了 {_days} 天</b>，样本太少，'
               f'下面的“判对率”数字<b>现在别当真</b>——攒够几个月历史再看才有意义。'
               f'现在它的用处是：把每天的判断记下来、以后能回头查，而不是拿来评价系统准不准。</div>') if _days < 30 else ""
    head = ('<h2 class="main">复盘记分卡（昨天判的、今天验）</h2>'
            + _caveat +
            f'<div class="card">今天下手的底气（与第一部分总闸同一判断）：<b>{esc(fed_str)}·{esc(fed_dir)}</b>'
            # 甲4：机会口径只许引 derived 的唯一取值(记分卡不再自造"应收口径")
            + (f'<div style="margin-top:4px">今天的机会口径（与①③册同一取值）：'
               f'{esc(str((daily.get("derived", {}) or {}).get("opportunity_scope", "待接")))}</div>' if daily else "")
            + '<div class="meta" style="color:#8ea3b6;font-size:12px">判对了就给这把尺加把握、判错了就改尺。每环记：昨天怎么判的／今天验得怎样／累计几分。</div></div>')
    # 甲1[P0·魂]：分环卡的分数/天数与魂①表、①册摘要【同一算子】pillars_now 现算
    _pn = pillars_now(date)
    _pby = {p["ring_id"]: p for p in _pn["pillars"]}
    rows = []
    for r in rings:
        rid = r.get("ring_id")
        _p = _pby.get(rid, {})
        # 判对率分母 = 同一截断历史(不数未来日)，与"追踪N天"同源
        series = _p.get("trend") or []
        pos = sum(1 for s in series if (s.get("score") or 0) > 0)
        tot = len(series)
        acc = (f"{pos}/{tot} 天判对（{round(pos/tot*100):d}%）" if tot else "首日·待累计")
        # B3③：总闸环今判/置信对齐 R2 状态机 final(与第一部分/底气同源·不再用pdca旧US10Y噪声判)
        _judg, _cert = r.get("judgment"), r.get("current_certainty", "待接")
        if "总闸" in str(r.get("ring_name")) and fed_dir != "待接":
            _judg, _cert = f"{fed_dir}（对齐R2状态机·与第一部分同源）", fed_str
        # 硬链2：记分卡每条 ↔ 它所评的那个判断(判断ID=layer slug·跳总览册该层锚)
        _jid = layer_slug(str(r.get("node") or r.get("ring_name")))
        rows.append(
            f'<div class="card" id="judge-{esc(_jid)}"><div class="hd"><b>{esc(r.get("ring_name"))}</b>（{esc(r.get("node"))}）'
            f'<span class="conf">今判：{esc(_judg)}</span> <span class="q">置信：{esc(_cert)}</span>'
            f' <span style="font-size:11.5px">{_a(L1(date, "layer-" + _jid), "↩它所评的判断(判断ID:" + esc(_jid) + ")")}</span></div>'
            f'<div class="you" style="font-weight:400;font-size:12.5px;color:#bcd8ee">'
            f'· 昨判(预测)：{esc(str(r.get("previous_strength",""))+str(r.get("previous_direction","") or "首日无昨判"))}'
            # 甲1：今日记分/累计分一律取 pillars_now(与魂①表、①册摘要同一取值)
            f'　· 今日验证/自动记分：{esc(str(_p.get("today_score", 0)))}分（{esc(r.get("score_reason","待接"))}）'
            f'　· 累计分：{esc(str(_p.get("cumulative_score", 0)))}'
            f'　· 判对率(自 {esc((series[0].get("date") if series else "?"))})：{esc(acc)}'
            f'　· 成败标准：确定性{esc(r.get("certainty_before","?"))}→{esc(r.get("current_certainty","?"))}（{esc(r.get("certainty_event","维持"))}）</div></div>')
    if not rows:
        rows.append('<div class="card">PDCA rings 待接（pdca_daily 无 rings·不编）</div>')
    return head + "".join(rows) + part7_souls(date, daily)


# ── 第七部分·系统三件魂（总则第十四条：确定性累积表+多尺度复盘+影子组合反事实） ──
def _spark(trend: list) -> str:
    """件六③：把方块字符"图"改成一句人话（董事长看不懂 ▁▃▅▇）。"""
    if not trend:
        return "（还没有历史·从今日起攒）"
    cums = [t.get("cum", 0) for t in trend]
    first, last = cums[0], cums[-1]
    up = sum(1 for t in trend if (t.get("score") or 0) > 0)
    down = sum(1 for t in trend if (t.get("score") or 0) < 0)
    flat = len(trend) - up - down
    if last > first:
        trend_txt = "在往上攒"
    elif last < first:
        trend_txt = "在往下掉"
    else:
        trend_txt = "原地踏步"
    return (f'有记录的这 {len(trend)} 天里：判对 {up} 天、判错 {down} 天、没变化 {flat} 天；'
            f'累计分从 {first} 变成 {last}，{trend_txt}')

_RIDS = ["worldview", "fed_gate", "strategy", "capital_flow", "sector_rotation"]
_RNAME = {"worldview": "世界观", "fed_gate": "总闸", "strategy": "战略",
          "capital_flow": "资金", "sector_rotation": "板块"}


def pillars_now(date: str) -> dict:
    """甲1[P0·魂]：记分卡的【唯一】算子——所有分数/天数一律从 scorecards.json 现算。

    根因：pillar_score.json 是"接scorecards"的派生快照，但没人在渲染时刷新它 →
    它停在 2026-07-16T15:11(总闸0/战略4)，而 scorecards 已经是(总闸1/战略1) →
    分环卡/魂①表/①册摘要三处报三个数。治法=不再读那个快照，全部从 scorecards 现算，
    pillar_score.json 降级为导出物(谁都不许拿它当源)。
    """
    sc = rj(ROOT / "data" / "pdca" / "scorecards.json")
    hist = sorted(sc.get("history", []) or [], key=lambda r: str(r.get("date", "")))
    # ⚠只认【不晚于本次数据日】的记录：history 里混进过 20260717(比数据日还新·且排在16前面)
    # → 造成"追踪10天"与"这9天里"并存。按数据日截断=天数全册唯一。
    hist = [h for h in hist if str(h.get("date", "")) <= date]
    cards = sc.get("cards", {}) or {}
    out = []
    for rid in _RIDS:
        ser = [{"date": h.get("date"), "score": int((h.get("scores", {}) or {}).get(rid, 0) or 0)} for h in hist]
        cum = 0
        trend = []
        for s in ser:
            cum += s["score"]
            trend.append({"date": s["date"], "score": s["score"], "cum": cum})
        c = cards.get(rid, {}) or {}
        first, last = (trend[0]["cum"], trend[-1]["cum"]) if trend else (0, 0)
        out.append({"ring_id": rid, "ring_name": _RNAME[rid],
                    "current_certainty": c.get("current_certainty", "待接"),
                    "cumulative_score": cum,                       # ← 现算·不读快照
                    "today_score": ser[-1]["score"] if ser else 0,  # ← 当日各环记分·与分环卡同一取值
                    "trend_arrow": "↑" if last > first else ("↓" if last < first else "→"),
                    "trend": trend, "days_tracked": len(trend)})
    return {"pillars": out, "history": hist, "days": len(hist),
            "start": hist[0].get("date") if hist else "", "cards": cards}


def part7_souls(date: str, daily: dict | None = None) -> str:
    out = ['<h3 style="margin-top:16px">第七部分·魂 —— 系统之魂三件（总则第十四条：确定性累积表 + 多尺度复盘 + 影子组合反事实记分）</h3>']
    # 魂① 支柱确定性累积表（甲1：与分环卡/①册摘要同一算子 pillars_now·不再读陈旧快照）
    try:
        pn = pillars_now(date)
        ladder = "＜".join(["证伪", "弱", "中", "高"])
        prows = ""
        for pl in pn["pillars"]:
            prows += (f'<tr><td><b>{esc(pl["ring_name"])}</b></td>'
                      f'<td style="color:#ffd479">{esc(pl["current_certainty"])}</td>'
                      f'<td style="text-align:right">{esc(str(pl["cumulative_score"]))}</td>'
                      f'<td style="text-align:right">{esc(str(pl["today_score"]))}</td>'
                      f'<td>{esc(pl["trend_arrow"])}</td>'
                      f'<td style="font-size:12px">{esc(_spark(pl["trend"]))}</td>'
                      f'<td style="color:#8ea3b6">{esc(str(pl["days_tracked"]))}日</td></tr>')
        out.append('<div class="blk">魂① 支柱确定性累积表（三支柱从"中"往"高"攒）</div>'
                   f'<div class="plain">确定性阶梯：{esc(ladder)}；每环每日按尺(支持+1/无变0/证伪-1)滚动累积——判对攒把握、判错减分。'
                   f'本表的分数与天数与上面分环卡、①册摘要<b>同一个算子现算</b>（都数 scorecards 的真实历史），不会各报各的。</div>'
                   '<table class="dt"><tr><th>支柱环</th><th>当前档</th><th>累计分</th><th>今日记分</th><th>走势</th><th>这些天怎么走的</th><th>追踪</th></tr>'
                   + prows + '</table>')
    except Exception as e:
        out.append(f'<div class="card">魂①支柱确定性累积表·待接（scorecards.json 缺：{esc(e)}）</div>')
    # 魂② 多尺度复盘 日/周/月/季/年
    try:
        sc = rj(ROOT / "data" / "pdca" / "scorecards.json")
        hist = sorted(sc.get("history", []) or [], key=lambda r: str(r.get("date", "")))
        rids = ["worldview", "fed_gate", "strategy", "capital_flow", "sector_rotation"]
        rname = {"worldview": "世界观", "fed_gate": "总闸", "strategy": "战略", "capital_flow": "资金", "sector_rotation": "板块"}
        def agg(recs):
            net = {r: sum(int((rec.get("scores", {}) or {}).get(r, 0) or 0) for rec in recs) for r in rids}
            tot = sum(1 for rec in recs for r in rids)
            pos = sum(1 for rec in recs for r in rids if int((rec.get("scores", {}) or {}).get(r, 0) or 0) > 0)
            return net, (f"{pos}/{tot}（{round(pos/tot*100)}%）" if tot else "待接")
        last = hist[-1] if hist else {}
        dq = (last.get("decision_quality", {}) or {})
        n_days = len(hist)
        # 日
        dnet, dhit = agg(hist[-1:])
        out.append('<div class="blk">魂② 多尺度复盘（日→周→月→季→年）</div>')
        out.append('<div class="card"><b>日</b>（验昨天各环+持仓动作）：今日各环记分 '
                   + "、".join(f'{rname[r]}{("+" if dnet[r]>0 else "")}{dnet[r]}' for r in rids)
                   + f'；决策质量：<b>{esc(dq.get("level","待接"))}</b>（{esc(dq.get("reason","待接"))}）。'
                   '<div class="plain">复盘什么：昨判今验各环；该改什么：按今日证伪环调当日口径（见第一部分五层④证伪条件）。</div></div>')
        # 周（近5日）
        wnet, whit = agg(hist[-5:])
        out.append(f'<div class="card"><b>周</b>（确认了才改板块地图"现在"格）：近{min(5,n_days)}日各环净分 '
                   + "、".join(f'{rname[r]}{("+" if wnet[r]>0 else "")}{wnet[r]}' for r in rids)
                   + f'；判对率 {esc(whit)}。'
                   '<div class="plain">复盘什么：一周内各环是否被反复确认；该改什么：某环连续确认→才动"板块地图·现在"格(不因单日噪声改)。</div></div>')
        # 月（现有历史≈半月·partial）
        mnet, mhit = agg(hist)
        out.append(f'<div class="card"><b>月</b>（确定性趋势+判对率）：自 {esc(hist[0].get("date") if hist else "?")} 累计各环净分 '
                   + "、".join(f'{rname[r]}{("+" if mnet[r]>0 else "")}{mnet[r]}' for r in rids)
                   + f'；累计判对率 {esc(mhit)}。'
                   # ⚠这里原来只关了 plain、没关外层 card → 整册 <div> 少一个闭合(L16 抓到)
                   + f'<div class="plain">复盘什么：确定性趋势与判对率；该改什么：判对率高的环升档、低的环重估尺。'
                     f'当前仅 {n_days} 日(不足1月)·满月口径随日累积。</div></div>')
        # 季 / 年（历史不足→待接）
        out.append('<div class="card"><b>季</b>（改"未来"判断）：<span class="need">待接·从今日起累积</span>（现有约2周历史·不足一季·满季后据季度确定性趋势改未来判断·不编）。'
                   '<div class="plain">复盘什么：季度级方向是否成立；该改什么：改"未来"判断与战略地图。</div></div>')
        out.append('<div class="card"><b>年</b>（世界观三支柱重审）：<span class="need">待接·从今日起累积</span>（不足一年·满年后重审世界观三支柱·不编）。'
                   '<div class="plain">复盘什么：世界观三支柱是否需重写；该改什么：年度重审右栏①世界观尺。</div></div>')
    except Exception as e:
        out.append(f'<div class="card">魂②多尺度复盘·待接（scorecards.json 缺：{esc(e)}）</div>')
    # 魂③ 影子组合反事实记分
    try:
        sn = rj(ROOT / "data" / "pdca" / "shadow_nav.json")
        ser = sn.get("series", []) or []
        srows = ""
        for s in ser[-10:]:
            srows += (f'<tr><td>{esc(s.get("date"))}</td>'
                      f'<td style="text-align:right">{esc(str(s.get("system_nav")))}</td>'
                      f'<td style="text-align:right">{esc(str(s.get("actual_nav")))}</td>'
                      f'<td style="text-align:right;color:{"#7ee0a0" if (s.get("diff") or 0)>=0 else "#ff9a9a"}">{esc(str(s.get("diff")))}</td></tr>')
        last = ser[-1] if ser else {}
        out.append('<div class="blk">魂③ 影子组合反事实记分（系统建议执行 vs 实际不动 → 差值=系统真含金量）</div>'
                   f'<div class="plain">{esc(sn.get("method",""))}。基准日 {esc(sn.get("baseline_date","?"))}·净值单位=%相对基准100。源：shadow_nav.json(逐日追加)。</div>'
                   '<table class="dt"><tr><th>日期</th><th>系统建议组合净值%</th><th>实际不动净值%</th><th>差值(系统−实际)</th></tr>' + srows + '</table>'
                   + (f'<div class="plain">当前差值 <b>{esc(str(last.get("diff")))}</b>%。{esc(last.get("note",""))}——差值为正说明"按系统守/减/加建议执行"跑赢"持仓不动"、即系统建议的真含金量；今日为基准日、从今日起逐日累积。</div>'))
    except Exception as e:
        out.append(f'<div class="card">魂③影子组合·待接（shadow_nav.json 缺：{esc(e)}）</div>')
    return "".join(out)


class StaleSnapshotError(Exception):
    """R3：本次 production 快照早于上次已生成的快照→拒绝生成(治'新生成用旧快照'B1)。"""


def _snapshot_guard(date: str, dyn: dict, only) -> None:
    """R3 单调性闸：后运行须用不早于前次的快照，否则拒绝。only(打通)模式跳过。"""
    if only:
        return
    cur_ts = str(dyn["prod"].get("generated_at") or "")
    if not cur_ts:
        return
    rec_p = ROOT / "data" / "evidence_chain" / "last_run_snapshot.json"
    prev = rj(rec_p) if rec_p.exists() else {}
    prev_ts = str(prev.get("scan_ts") or "")
    if prev_ts and cur_ts < prev_ts:
        raise StaleSnapshotError(f"本次 production 快照 {cur_ts} 早于上次 {prev_ts}（run_id={prev.get('run_id')}）→ 拒绝生成，防旧快照顶充。")
    try:
        rec_p.write_text(json.dumps({"date": date, "scan_ts": cur_ts,
                                     "run_id": "R-" + cur_ts.replace("-", "").replace("T", "-").replace(":", "")[:15]},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def build(date: str, only: list[str] | None = None) -> tuple[str, dict]:
    dyn = load_dynamic(date)
    _CORRO_AGE["d"] = _corro_age(date)[0]      # 甲5：佐证料天数当日现算·供各佐证栏尾注引用
    _snapshot_guard(date, dyn, only)   # R3 快照单调性闸
    holds = dyn["prod"].get("holdings", [])
    stocks = [h for h in holds if not str(h.get("symbol","")).startswith("CC.")]
    if only:
        stocks = [h for h in stocks if h.get("symbol") in only]
    cards = []; card_by = {}; stats = {"n": 0, "pack_ok": 0, "pack_wait": [], "exit_todo": [], "_order": stocks}
    for h in stocks:
        card, ps = render_card(h["symbol"], h.get("name", h["symbol"]), dyn)
        cards.append(card); card_by[h["symbol"]] = card; stats["n"] += 1
        if ps in ("OK", "深度10块"): stats["pack_ok"] += 1
        elif ps == "退出条件待补": stats["pack_ok"] += 1; stats["exit_todo"].append(h["symbol"])   # 有包·仅退出条件缺
        else: stats["pack_wait"].append(h["symbol"])                                              # 无判断包
        if ps == "深度10块": stats.setdefault("deep10", []).append(h["symbol"])
    # R3 运行唯一性：run_id + 扫描快照时间戳(锚定 production·稳定→同快照重跑字节一致)
    scan_raw = str(dyn["prod"].get("generated_at") or "")
    scan_ts = scan_raw[:19]   # production 扫描时间戳(本次实时扫描·UTC)
    try:
        _dt = datetime.fromisoformat(scan_raw.replace("Z", "+00:00"))
        scan_jst = _dt.astimezone(JST).strftime("%Y-%m-%d %H:%M:%S JST")
        run_id = "R-" + _dt.astimezone(JST).strftime("%Y%m%d-%H%M%S")
    except Exception:
        scan_jst = "待接"; run_id = "R-" + date + "-nots"
    md_note = str((dyn["daily"].get("rule_engine", {}) or {}).get("inputs_used", {}).get("snapshot_data_date", ""))[:19]
    head = ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>完整产品·机器版(实时自动生成)</title><style>'
            'body{font-family:"Microsoft YaHei",Arial,sans-serif;background:#0b1118;color:#eef5f9;line-height:1.7;max-width:1000px;margin:0 auto;padding:16px}'
            '.card{background:#151f2b;border:1px solid #2b4054;border-radius:10px;padding:12px 14px;margin:10px 0}'
            '.hd{font-size:16px;margin-bottom:8px}.sym{color:#8ea3b6;font-size:12px}.conf{color:#ffd479}.q{color:#7ee0a0;font-size:13px}.v{color:#9ed8ff;font-size:13px}'
            '.k{color:#5cc8ff;font-weight:700;margin-right:6px}.deep{margin:6px 0;font-size:14px}.dossier{margin:6px 0;font-size:13px;color:#d9e7ef}.you{margin-top:6px;font-weight:700}'
            # 深度10块·大白话样式(对齐董事长认可的成品样卡)
            '.blk{font-size:14.5px;color:#ffe4a8;font-weight:700;margin:12px 0 4px;border-left:4px solid #2c6e9a;padding-left:8px}'
            '.plain{background:#12261f;border-left:4px solid #4f9e7f;border-radius:0 7px 7px 0;padding:6px 11px;margin:6px 0;font-size:13px;color:#bfe6d3}'
            '.need{color:#ffb454;font-weight:700}.bull{color:#7ee0a0;font-weight:700}.bear{color:#ff9a9a;font-weight:700}.base{color:#7cc4ff;font-weight:700}'
            '.dt{width:100%;border-collapse:collapse;margin:7px 0;font-size:12.5px}.dt th,.dt td{border:1px solid #2a3d4f;padding:6px 8px;text-align:left;vertical-align:top}.dt th{background:#13202d;color:#bcd0e2}'
            # 甲3：分主次——主(今日变化/待拍板/持仓一眼看全)大而亮；次(大环境/机会池/记分卡/右栏尺)弱化可折叠
            'h2.main{font-size:23px;color:#ffd479;border-left:6px solid #ffd479;padding-left:10px;margin:22px 0 8px}'
            'details.sub{margin:10px 0;border:1px solid #24384c;border-radius:8px;background:#101a26}'
            'details.sub>summary{cursor:pointer;padding:9px 13px;font-size:14px;color:#9ed8ff;font-weight:700;list-style:none}'
            'details.sub>summary::marker{content:""}details.sub>summary::before{content:"▸ ";color:#5cc8ff}'
            'details.sub[open]>summary::before{content:"▾ "}details.sub>div,details.sub>table{margin:0 11px 10px}'
            'h2.sub{font-size:15px;color:#8ea3b6;font-weight:600;border-left:3px solid #3a5a8a;padding-left:8px;margin:16px 0 6px}'
            '</style></head><body>')
    # ══ 乙2：页头最顶端超大横幅——一眼知道是不是今天的、是新是旧 ══
    _dd = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    try:
        _age_d = (datetime.now(JST).date() - datetime.strptime(date, "%Y%m%d").date()).days
    except Exception:
        _age_d = 0
    _fresh = _age_d <= 0
    _bg, _bd, _fg = (("#0f2e1c", "#4fbf87", "#8cf5be") if _fresh else ("#3a2410", "#c47a1e", "#ffb454"))
    _tag = "今天的" if _fresh else (f"{_age_d} 天前的·不是今天" if _age_d > 0 else "")
    # 甲1：页头只留【一句大字 + 一行小字】。run_id/UTC/快照戳这些机器话收进折叠，别一打开就糊脸。
    big = (f'<div style="background:{_bg};border:3px solid {_bd};border-radius:12px;'
           f'padding:12px 18px;margin:0 0 8px">'
           f'<div style="font-size:29px;font-weight:900;color:{_fg};line-height:1.25;letter-spacing:1px">'
           f'★ 每日投资产品 · {esc(_dd)}　<span style="font-size:19px">［{esc(_tag)}］</span></div>'
           # _mkt_oneline 返回的是已转义好的安全HTML(内含<b>)→不能再 esc 一次(否则标签变字面量)
           f'<div style="font-size:12.5px;color:#c8d4de;margin-top:5px">'
           f'{_mkt_oneline(date)}</div>'
           # 机器话折叠(要查再展开)
           f'<details style="margin-top:5px"><summary style="font-size:11.5px;color:#8ea3b6;cursor:pointer">'
           f'编号 / 生产时间 / 数据来源（点开看·核对用）</summary>'
           f'<div style="font-size:11.5px;color:#9aa8b5;margin-top:5px;line-height:1.75">'
           f'· 数据日 data_date=<b>{esc(_dd)}</b>（这些数字取自哪一天）<br>'
           f'· 生产于 <b>{esc(scan_jst)}</b>（UTC {esc(scan_ts)}）——这份文件什么时候跑出来的<br>'
           f'· 编号 run_id=<b>{esc(run_id)}</b>——这一次运行的号；五册必须完全一样，不一样就是有一册是旧的<br>'
           + (f'· 行情快照日：{esc(md_note)}<br>' if md_note else '')
           + f'· 深研=个股判断包真源抽取 · 动态=production现算 · 均线仅趋势参考不作买卖线 · 缺不编'
           + _price_asof_note(date)
           + '</div></details></div>')
    title = big
    part2 = f'<h2 class="main">你的持仓，今天怎么办（{stats["n"]}只）</h2>' + "".join(cards)
    if only:   # 打通模式:只出持仓卡
        return head + title + part2 + "</body></html>", stats
    daily = dyn["daily"]
    der = daily.get("derived", {}) or {}
    oneline = esc(str(der.get("today_direction_short") or "今天：守核心、不追高、控AI集中"))
    banner = _top3_card(date, dyn, daily, stats, oneline)
    # ══ 分册：同一份同源数据 → 5册(纯移搬·一字不删) ══
    v1_nav = _vol_nav(date, 1) ; v2_nav = _vol_nav(date, 2)
    v3_nav = _vol_nav(date, 3) ; v4_nav = _vol_nav(date, 4) ; v5_nav = _vol_nav(date, 5)
    p_diff = part0_diff(date, dyn)
    p_layers = part1_layers(daily, dyn)
    p_macro = part1_macro_table(daily)
    p_conc = part3_concentration(date, dyn)
    p_6a = part4_opportunity(daily, dyn)
    p_6b = part4b_swap_engine(daily, dyn)
    p_funnel = part4_funnel(date, daily, dyn)
    p_close = part5_closeloop(daily)
    p_rulers = part6_rulers()
    p_pdca = part7_pdca(date, daily)

    vol1 = (head + title + v1_nav + banner + corro_staleness_banner(date)   # 甲5：佐证过期→醒目警条
            + p_diff + _loop_map(date) + _summary_tables(date, dyn, stats)
            + p_layers + p_macro + p_conc + p_close + "</body></html>")
    vol3 = (head + title + v3_nav + p_6a + p_6b + p_funnel + "</body></html>")
    vol4 = (head + title + v4_nav + p_pdca + "</body></html>")
    vol5 = (head + title + v5_nav + p_rulers + "</body></html>")
    stats["ruler_embed"] = vol5.count('class="ruler-embed"')
    volumes = {VOL(date, 1): vol1, VOL(date, 3): vol3, VOL(date, 4): vol4, VOL(date, 5): vol5}
    # ②持仓深研：按角色拆3子册(不删内容·每册<300KB)；card_by 保序原样搬
    deep_total = 0
    for sub, subname, syms in VOL2_SUBS:
        picked = [card_by[s] for s in [h.get("symbol") for h in stats["_order"]] if s in syms and s in card_by]
        body = (f'<h2 class="main">你的持仓，今天怎么办（{subname}·{len(picked)}只／全19只）</h2>'
                + _sub_nav(date, sub) + "".join(picked))
        volumes[VOL2(date, sub)] = head + title + _vol_nav(date, 2) + body + "</body></html>"
        deep_total += len(picked)
    stats["deep_blocks"] = deep_total
    # 件四①/件二/件五：全册统一清洗(内部结构泄露/裸字段名/内部话/草稿语)——只改措辞·判断口径不变
    # 甲1：候选专用措辞只许在③机会池册生效(持仓册走持仓版·不套候选模板)
    volumes = {k: _scrub_leaks(v, is_pool=(k == VOL(date, 3))) for k, v in volumes.items()}
    stats["volumes"] = volumes
    stats["run_id"] = run_id          # 丙2/丙3：出厂后登记指纹+回写主控要用
    stats["scan_jst"] = scan_jst
    return volumes[VOL(date, 1)], stats


def _sub_nav(date: str, cur: str) -> str:
    bits = []
    for s, n, syms in VOL2_SUBS:
        lbl = f"{n}({len(syms)}只)"
        bits.append(f'<b style="color:#ffd479">{esc(lbl)}·本子册</b>' if s == cur else _a(VOL2(date, s), esc(lbl)))
    return ('<div class="card" style="background:#101c2c;padding:7px 12px"><span class="k">持仓深研子册</span>'
            + '　｜　'.join(bits)
            + '<div class="meta" style="color:#8ea3b6;font-size:11.5px">19只×10块按组合角色分3子册(每册<300KB·内容一字未删)；'
            '各册同一 run_id/data_date/快照戳；上游"落点持仓"按只直链到所属子册锚点。</div></div>')


# 件四①：产品内不许出现程序内部结构/裸字段名(渲染后统一清洗·治信任击穿)
_FIELD_ZH = {"normal_eps": "正常年景每股盈利", "pe_mid": "穿越周期的合理倍数",
             "normalized_eps": "正常化每股盈利", "pe_normal": "正常化倍数",
             "eps0": "明年每股盈利", "g_stage1": "头几年增速", "terminal_g": "之后的慢增速",
             "wacc": "打折率", "bvps": "每股净资产", "target_pb": "目标市净率",
             "ev_per_share": "每股内含价值", "ev_multiple": "内含价值倍数",
             "holding_discount": "控股折价", "net_debt": "净负债", "shares": "股本",
             "assets": "各资产估值", "ebitda_normal": "正常年景EBITDA", "ev_ebitda": "EV/EBITDA倍数"}
_LEAK_PATS = [
    # 程序内部字典原样打印(曾泄露 {'status':'待理解岗打分',...})
    (re.compile(r"\{&#x27;[^}<]{0,200}?\}|\{&#x27;status&#x27;[^<]{0,160}|\{'[a-z_]+':[^}<]{0,200}\}"),
     "评级待补（见该只持仓卡③护城河五维）"),
    # 引擎"缺真输入：字段名+字段名(任一整套)（该用…）·不硬编"整串→人话。
    # ⚠必须吃到结尾标记"·不硬编"为止：原写法 [^（(<]{0,120} 遇到半角括号(如 shares(任一整套))就停，
    # 把 "(任一整套)（该用 …EV/EBITDA）" 这截内部话原样漏给董事长看(台积电/爱德万/闪迪/伊藤忠/COIN/CRCL 六只)。
    (re.compile(r"缺真输入[：:].{0,240}?(?:·不硬编|・不硬编)"),
     "算不出该值多少钱的原因见本卡「今天你怎么办」第3行"),
    (re.compile(r"缺真输入[：:][^<]{0,240}"), "算不出该值多少钱的原因见本卡「今天你怎么办」第3行"),
    # 残留的"缺真输入/不硬编"内部话→人话(判断口径不变·只改措辞)
    (re.compile(r"（估值引擎缺真输入·不硬编）"), "（算不出可信的合理价·原因见本卡「今天你怎么办」第3行）"),
    (re.compile(r"缺真输入"), "缺可信的估值输入"),
    (re.compile(r"·不硬编|・不硬编|不硬编"), "·不瞎编"),
]
def _scrub_fields(s: str) -> str:
    """裸字段名→中文人话(括号里的字段名也去掉)。"""
    for k, v in sorted(_FIELD_ZH.items(), key=lambda x: -len(x[0])):
        s = re.sub(r"\(" + k + r"\)|（" + k + r"）", "", s)   # 人话标签后的(eps0)括号→删
        s = re.sub(r"(?<![A-Za-z_])" + k + r"(?![A-Za-z_])", v, s)
    return s
# ══ 第二轮打回·A：裸指标/内部名/调试日志 → 人话或删（只改措辞·判断口径不变） ══
_JARGON_RE = [
    # A1 裸指标 → 人话(带"这意味着什么")
    (r"US10Y\s*=\s*([\d.]+)、较昨([+\-][\d.]+)%", r"美国十年期国债利率\1%，比昨天\2%（只是小动，不足以翻转大判断）"),
    (r"US10Y\s*=\s*([\d.]+)", r"美国十年期国债利率\1%"),
    (r"US10Y\s*/\s*Real Yield", "美国十年期国债利率（含剔除通胀后的真实利率）"),
    (r"\bUS10Y\b", "美国十年期国债利率"),
    (r"\bUS3M\b", "美国三个月国债利率"),
    (r"10Y-3M\s*=\s*([\d.]+)", r"十年期国债利率比三个月的高\1个百分点（长短端没有倒挂，属正常）"),
    (r"\bFEDFUNDS\b|\bFedFunds\b", "美联储基准利率"),
    (r"\bSOXX\b", "费城半导体指数（一篮子半导体股）"),
    (r"加权净分\s*=\s*([\-\d.]+)", r"综合研判得分\1（正数偏利多、负数偏利空）"),
    (r"\bregime\s*反转|regime反转", "世界大格局翻转"),
    (r"\bregime\b", "大格局"),
    (r"\bFIMA\b", "美联储给外国央行的美元窗口"),
    (r"\bVIX\b", "市场恐慌指数VIX（越低越安心）"),
    (r"\bDXY\b", "美元指数"),
    # A2 调试日志感 → 删/人话
    (r"过源白名单\+时效\(\d+h\)\+相关性闸后", "按“只认权威媒体+只要当天的”筛过后"),
    (r"·过相关性闸|（未过相关性闸）|未过相关性闸", "·与本层主题相关"),
    (r"相关性闸", "主题相关性"),
    (r"meta字段", "该资料的摘要栏"),
    (r"·非白名单大站", ""),
    (r"（权威源\+\d+h内[^）]*）", "（权威媒体+当天发布）"),
    # 只清"调试日志里裸露的域名"，不动 href/URL 里的(否则原文链接被打坏)
    (r"(?<![/\.\w\"'=])[a-z0-9\-]{2,}\.com(?![/\w])", "该网站"),
    # A3 内部文件名/变量 → 人话
    (r"data/[a-z_]+/[a-z_]+\.json|[a-z_]+\.json", "系统内部记录"),
    (r"（映射见 系统内部记录[^）]*）|（源：系统内部记录[^）]*）|（接系统内部记录[^）]*）", ""),
    (r"chain_opportunities[^·、）\s]*", "当日全市场扫描"),
    (r"\bR1\b|\bR2\b|\bR3\b|\bR4\b|\bR5\b|\bR6\b|\bR7\b|\bR8\b|\bR9\b|\bR10\b", ""),
    (r"（[^）]{0,6}·R\d+）|·R\d+(?=[）。；])|\(R\d+\)", ""),
    (r"gate①|gate②|gate③|gate④|gate⑤", "第一关"),
    (r"判断ID[:：]\s*[a-z_]+", "这条判断"),
    (r"\bEV/EBITDA\b", "企业价值倍数（衡量贵不贵的一种算法）"),
    (r"\bEBITDA\b", "息税折旧前利润（大致等于主营赚的现金）"),
    # ⚠只清【独立出现】的内部编号 6a/6b——原写法 6a\b 会命中 CSS 色值 "#c9a86a" 里的 6a，
    #   把它吃成 "#c9a8"(非法色值)→佐证栏颜色坏掉。故前面必须不是十六进制字符/井号。
    (r"(?<![#0-9A-Fa-f])6[ab]\b", ""),
    # A4 10块残留术语 → 加大白话
    (r"\bmNAV\b", "持币净值倍数（股价相对它手上比特币净值的倍数）"),
    (r"\bSOTP\b", "分部估值（把各块生意分开算再加总）"),
    (r"正常化EPS[·×xX]?正常化PE", "正常年景每股盈利 × 穿越周期的合理倍数"),
    (r"正常化EPS", "正常年景每股盈利"),
    (r"正常化PE", "穿越周期的合理倍数"),
    (r"前瞻PE", "按明年预计盈利算的市盈率"),
    (r"\bbeta\b", "波动性（相对大盘的涨跌幅度）"),
    (r"book-to-bill", "新接订单÷已交货（大于1说明订单在增加）"),
    (r"\bESR\b", "偿付能力充足率（保险公司家底够不够厚）"),
    (r"IFRS\+?ICS|IFRS", "国际会计准则"),
    (r"J-GAAP", "日本会计准则"),
    (r"DXd\s*ADC|DXd/ADC|\bADC\b", "抗体偶联药（把化疗药精准送到癌细胞的技术）"),
    (r"\bDXd\b", "第一三共自研的抗癌药平台"),
    (r"\bILD\b", "间质性肺病（这类药的主要副作用）"),
    (r"GENIUS Act|GENIUS法案", "美国稳定币监管法案"),
    (r"\bUSDC\b", "USDC（Circle发行的美元稳定币）"),
    (r"\bUSDT\b", "USDT（泰达发行的美元稳定币，规模最大）"),
    (r"\bHBM\b", "高带宽内存（AI芯片专用的高速存储）"),
    (r"\bCoWoS\b", "先进封装（把芯片和内存叠在一起的工艺）"),
    (r"\bNAND\b", "闪存芯片"),
    # 甲4：整组先吃掉——原来 XPU 与 ASIC 各替一次，"(XPU/ASIC)"就成了"(定制AI芯片/定制AI芯片)"
    (r"[（(]\s*XPU\s*[／/]\s*(?:定制)?ASIC\s*[）)]", "（定制AI芯片）"),
    (r"[（(]\s*(?:定制)?ASIC\s*[／/]\s*XPU\s*[）)]", "（定制AI芯片）"),
    (r"\bXPU\s*[／/]\s*(?:定制)?ASIC\b|\b(?:定制)?ASIC\s*[／/]\s*XPU\b", "定制AI芯片"),
    (r"\bXPU\b|定制ASIC|\bASIC\b", "定制AI芯片"),
    (r"\bLTV\b", "负债率"),
    (r"\bPPA\b", "长期购电协议"),
    (r"\bSMR\b", "小型模块化核反应堆"),
    (r"\bNBM\b", "新商业模式（多年锁量合约）"),
]
_JARGON_COMPILED = [(re.compile(p), r) for p, r in _JARGON_RE]

def _scrub_jargon(s: str) -> str:
    for pat, rep in _JARGON_COMPILED:
        s = pat.sub(rep, s)
    # 收口：上一轮被HTML标签/词序打断而漏网的(逐个按真身补)
    for a, b in (("mNAV", "持币净值倍数"), ("SOTP", "分部估值"), ("ESR", "偿付能力充足率"),
                 ("FIMA", "美联储给外国央行的美元窗口"), ("regime级大事件", "掀翻大格局的大事"),
                 ("regime", "大格局"), ("高beta", "高波动"), ("beta", "波动性"),
                 ("判断ID回链", "点判断可跳回它所评的那一层"), ("判断ID", "这条判断"),
                 ("bet</", "押注</"), ("加密周期bet", "押注加密周期"),
                 ("接着起草右栏第4块", "右栏第4块"), ("下一步回去组装完整产品", "随后组装完整产品"),
                 ("；接着起草右栏最后一块", "；右栏最后一块"), ("接着起草右栏", "右栏"), ("起草右栏", "右栏"),
                 # B1：任天堂全卡"贵/便宜"口径统一(不许再单独出现"比表面便宜/更便宜")
                 ("·除现金经营业务更便宜", "·整体偏贵、扣掉每股约¥1,940净现金后没那么夸张"),
                 ("除现金经营业务更便宜", "整体偏贵、扣净现金后没那么夸张"),
                 ("除现金外的经营业务比表面PE更便宜", "整体偏贵、扣净现金后没那么夸张"),
                 ("比表面PE更便宜", "整体偏贵、扣净现金后没那么夸张"), ("比表面便宜", "整体偏贵、扣净现金后没那么夸张"),
                 ("；下一步", "；随后"), ("下一步", "随后")):
        s = s.replace(a, b)
    # E1 叠字/重复
    for a, b in (("共同共同风险", "共同风险"), ("共同风险风险", "共同风险"),
                 ("（）", ""), ("()", ""), ("（·", "（"), ("··", "·"), ("；；", "；"),
                 ("（，", "（"), ("(，", "("), (" ｜ ｜ ", " ｜ ")):
        s = s.replace(a, b)
    s = re.sub(r"（\s*）|\(\s*\)", "", s)
    # 甲4 兜底：术语替换后可能把"(A/B)"两侧替成同一个词→"(定制AI芯片/定制AI芯片)"这类重复渣，一律归一。
    # ⚠只吃"同一个词被斜杠隔开重复"这一种,且词里必须【不含数字】——
    #   原写法把"¥3,420/200日¥3,737"这类正当的数字分隔也当重复吃掉了(索尼均线粘连)。
    #   ⚠再加一道护栏：【绝不碰 HTML 标签】——"</div></div>" 里的 div> / div> 会被当成
    #   "同一个词被斜杠隔开重复"吃掉一个 → 迷你数轴每格少一个闭合标签(19只全中)。
    #   故只在纯文本片段上做归一：先把标签挖出来占位，替换完再放回去。
    _tags: list[str] = []

    def _hide(m):
        _tags.append(m.group(0))
        return f"\x00{len(_tags)-1}\x00"

    s = re.sub(r"<[^>]+>", _hide, s)
    s = re.sub(r"[（(]\s*([^\W\d_][^（）()／/\d]{1,13})\s*[／/]\s*\1\s*[）)]", r"（\1）", s)
    s = re.sub(r"(?<![\d,])([^\W\d_][^（）()／/、，\d]{1,13})\s*[／/]\s*\1(?![^（）]*[／/])(?![\d,])", r"\1", s)
    s = re.sub(r"\x00(\d+)\x00", lambda m: _tags[int(m.group(1))], s)
    return s


# ══ 甲7[大白话]：通篇未解释的术语 → 每册【首次出现】就地加括号解释，之后不再啰嗦 ══
# 董事长看不懂 = 这句话白写。不删肉：术语保留，只在第一次出现时把人话补进去。
_GLOSS = [
    (r"(?<![A-Za-z])OI(?![A-Za-z])", "OI（营业利润）"),
    (r"(?<![A-Za-z])DARTs?(?![A-Za-z])", "DARTs（客户日均交易笔数·衡量交易活跃度）"),
    (r"(?<![A-Za-z])PFOF(?![A-Za-z])", "PFOF（把客户订单卖给做市商换回扣的做法·美国有争议）"),
    (r"(?<![A-Za-z])DAR(?![A-Za-z])", "DAR（每个抗体平均挂几个药物分子·抗体药的关键工艺指标）"),
    (r"(?<![A-Za-z])IRA(?![A-Za-z])", "IRA（美国《通胀削减法案》·内含药价管制）"),
    (r"(?<![A-Za-z])CMO(?![A-Za-z])", "CMO（代工生产药品的厂商）"),
    (r"拓扑异构酶(?:抑制剂)?载荷", "拓扑异构酶载荷（抗体上挂的那个杀癌细胞的药物弹头）"),
    (r"ASU\s*2023-08", "ASU2023-08（美国新会计准则·允许把比特币按市价计入利润表）"),
    (r"(?<![A-Za-z])senior(?:\s+notes?)?(?![A-Za-z])", "senior notes（优先级较高的公司债·还钱顺位排在股票前面）"),
    (r"(?<![A-Za-z])ATM(?![A-Za-z])", "ATM（随行就市增发·公司按市价一点点卖新股融资）"),
    (r"(?<![A-Za-z])LTV(?![A-Za-z])", "LTV（借款占资产的比例·衡量杠杆有多重）"),
    (r"(?<![A-Za-z])DER(?![A-Za-z])", "DER（净负债÷净资产·衡量借了多少钱）"),
    (r"Up-C\s*结构", "Up-C结构（上市公司只占运营实体一部分·财报净利与你能分到的不是一回事）"),
    (r"(?<![A-Za-z])SerDes(?![A-Za-z])", "SerDes（芯片间高速收发电路）"),
    (r"(?<![A-Za-z])HBM(?![A-Za-z])", "HBM（高带宽存储·AI芯片旁边那种贵内存）"),
    (r"(?<![A-Za-z])NBM(?![A-Za-z])", "NBM（NAND闪存的高带宽新形态·对标HBM）"),
    (r"(?<![A-Za-z])FCF(?![A-Za-z])", "FCF（自由现金流·真正能拿走的现金）"),
    (r"(?<![A-Za-z])ROI(?![A-Za-z])", "ROI（投入产出比·花的钱赚没赚回来）"),
    (r"(?<![A-Za-z])mNAV(?![A-Za-z])", "mNAV（市值÷持币净值·大于1=市场给溢价）"),
    # 丙8（本轮补）
    # bp 永远跟在数字后("-66bp"/"100bp")→前面【必须】允许数字，只挡字母(避免 bps/bpm 误伤)
    (r"(?<![A-Za-z])bp(?![A-Za-z])", "bp（基点·1个基点=0.01个百分点）"),
    (r"调整\s*EBITDA", "调整EBITDA（公司自己调整过的经营利润口径·非官方会计准则）"),
    (r"(?<![A-Za-z])ILD(?![A-Za-z])", "ILD（间质性肺病·这类抗体药最要盯的副作用）"),
    (r"(?<![A-Za-z])ASCA(?![A-Za-z])", "ASCA（第一三共与阿斯利康的共同开发/分成合作）"),
    (r"(?<![A-Za-z])CoWoS(?![A-Za-z])", "CoWoS（台积电的先进封装·把芯片和高带宽存储叠在一起·AI芯片的产能瓶颈）"),
]


def _gloss_first(h: str) -> str:
    """每册首次出现的术语就地解释一次(之后同术语不再加·免刷屏)。只加字·不删原文。"""
    for pat, rep in _GLOSS:
        rx = re.compile(pat)
        m = rx.search(h)
        if not m:
            continue
        # 已经紧跟【真解释】的就别再叠。⚠不能只看"后面有没有括号"——
        #   "调整EBITDA(非GAAP)" 的括号是限定语不是解释，那样会把该补的解释跳掉。
        #   判据：括号里得有中文说明字(而不只是 GAAP/US/Q1 这类标签)。
        tail = h[m.end(): m.end() + 40]
        mb = re.match(r"\s*[（(]([^）)]{0,36})[）)]", tail)
        if mb and len(re.findall(r"[一-鿿]", mb.group(1))) >= 4:
            continue
        h = h[:m.start()] + rep + h[m.end():]
    return h


def _scrub_leaks(html_txt: str, is_pool: bool = False) -> str:
    """is_pool=True 仅机会池册：候选卡没有「今天你怎么办」四行→指路话要换成候选版。
    持仓册【绝不】走这条(持仓卡有四行·指路正确)——甲1根因就是这里原来不分册全局替换。"""
    for pat, rep in _LEAK_PATS:
        html_txt = pat.sub(rep, html_txt)
    html_txt = _scrub_fields(html_txt)
    html_txt = _scrub_jargon(html_txt)
    # 甲7：世界观"没变·但要盯(…需盯(…))"双盯嵌套 → 拆成一句人话
    html_txt = re.sub(r"没变·但要盯\([^()]*?需盯\(未到世界大格局翻转\)\)",
                      "没变（大格局还是原样），但地缘/秩序上的紧张信号今天多了，要盯着点", html_txt)
    html_txt = re.sub(r"没变·但要盯\(([^()]{0,40})\)", r"没变，但要盯着点（\1）", html_txt)
    html_txt = re.sub(r"没变\(三支柱维持·([^()]{0,30})\)", r"没变（三支柱延续·\1）", html_txt)
    # 甲7：VIX那句三层括号 → 拆短句
    html_txt = re.sub(r"（VIX\s*较昨([+\-][\d.]+)%、曲线未倒挂\(10Y-3M=([\d.]+)·2年待接\)）",
                      r"：市场恐慌指数较昨天\1%，长短期利率没有倒挂，属正常", html_txt)
    html_txt = _gloss_first(html_txt)          # 术语首次出现就地解释
    # 件二/件五：内部话与草稿语→人话/删(判断口径不变·只改措辞)
    for a, b in (("【状态机·事件驱动】", "【判断依据】"), ("状态机", "判断规则"), ("事件驱动", "按事件才改"),
                 ("对齐R2状态机·与第一部分同源", "与第一部分总闸同一判断"), ("(治B2)", ""), ("治B2", ""),
                 ("翻闸", "翻转总判断"), ("边际注脚(仅参考·不翻闸)", "只作参考、不足以翻转大判断"),
                 ("边际注脚", "参考项"), ("·基线)", "·维持原判断)"), ("无新Fed事件·沿用第", "美联储没出新动作·已连续第"),
                 ("(事件日)", "（美联储今天有动作）"), ("敞口", "占比"),
                 ("共同风险因子", "共同风险"), ("风险因子", "共同风险"),
                 ("请你审这块", ""), ("请你审这版（改进版），回我", ""), ("请你审", ""), ("，回我", ""), ("回我", ""),
                 ("待董事长审", ""), ("(待审)", ""), ("（待审）", "")):
        html_txt = html_txt.replace(a, b)
    # D：右栏尺里残留的草稿征询语(下一步:起草…/认可→定稿/要加改吗/对吗)——只删措辞·不删内容
    html_txt = re.sub(r"下一步[：:]\s*起草[^<。；]{0,30}[。；]?", "", html_txt)
    html_txt = re.sub(r"起草依据", "依据", html_txt)
    html_txt = re.sub(r"认可\s*→\s*定稿|认可后定稿", "", html_txt)
    html_txt = re.sub(r"要加\s*/\s*改吗[？?]?|对吗[？?]", "", html_txt)
    html_txt = re.sub(r"下一步[：:]", "", html_txt)
    # E3/甲1：候选卡无「今天你怎么办」四行→只在机会池册换成候选版措辞；持仓册保持指路(那行真实存在)
    if is_pool:
        # 甲3：替换文本【不许自带括号】——它常被塞进外层"（…）"里(如"待接（<此处>）")，
        # 内层再来一对就成了"（A（B）"少一个右括号、句子也断在半截。
        html_txt = html_txt.replace(
            "算不出该值多少钱的原因见本卡「今天你怎么办」第3行",
            "这只候选还没做估值——它不在你持仓里，没跑估值模型")
        html_txt = html_txt.replace(
            "算不出可信的合理价·原因见本卡「今天你怎么办」第3行",
            "还没做估值——它不在你持仓里，没跑估值模型")
    # 甲1：去掉三层套括号(（（x）））
    for _ in range(3):
        html_txt = re.sub(r"（（+", "（", html_txt)
        html_txt = re.sub(r"）+）", "）", html_txt)
        html_txt = re.sub(r"（([^（）]{0,60})（([^（）]{0,60})））", r"（\1\2）", html_txt)
    # E：空标题清掉
    html_txt = re.sub(r"<h([23])>\s*(?:。|”。|“过滤标准”。|\"过滤标准\"。)?\s*</h\1>", "", html_txt)
    return html_txt


def _vol_nav(date: str, cur: int) -> str:
    """五册互跳导航条(每册同源页眉下方·防散架)。"""
    names = {1: "① 总览/闭环", 3: "③ 机会池", 4: "④ 记分卡/复盘", 5: "⑤ 右栏6尺"}
    bits = []
    for n in (1, 2, 3, 4, 5):
        if n == 2:
            # ②已拆3子册：导航直给子册入口
            sub = " / ".join(_a(VOL2(date, s), esc(f"②{s[-1]} {nm}")) for s, nm, _ in VOL2_SUBS)
            bits.append(("<b style='color:#ffd479'>② 持仓深研·本册</b>（" + sub + "）") if cur == 2
                        else ("② 持仓深研（" + sub + "）"))
        elif n == cur:
            bits.append(f'<b style="color:#ffd479">{esc(names[n])}·本册</b>')
        else:
            bits.append(_a(VOL(date, n), esc(names[n])))
    return ('<div class="card" style="background:#101c2c;border-color:#2b4054;padding:8px 12px">'
            '<span class="k">分册导航</span>' + '　｜　'.join(bits)
            + '<div class="meta" style="color:#8ea3b6;font-size:11.5px">五册同一 run_id / data_date / 快照戳·一次数据同源生成；'
            '跨册锚点相对路径可跳（落点持仓→持仓卡；持仓决策链→上游层；对应尺→6尺册；记分条→所评判断）。</div></div>')


def _loop_map(date: str) -> str:
    """硬链3：七层逻辑闭环图(每节点点进对应册/锚点)。"""
    nodes = [("①世界观", L1(date, "layer-world")), ("②国家战略", L1(date, "layer-strategy")),
             ("③资金流动", L1(date, "layer-capital")), ("④板块轮动", L1(date, "layer-sector")),
             ("⑤机会池", VOL(date, 3)), ("⑥持仓", VOL2(date, "2a")), ("⑦复盘记分卡", VOL(date, 4))]
    chain = ' <span style="color:#ffd479">→</span> '.join(
        f'<a href="{h}" style="display:inline-block;background:#12203a;border:1px solid #3a5a8a;'
        f'border-radius:8px;padding:6px 10px;color:#8fd6ff;text-decoration:none;margin:3px 0">{esc(t)}</a>'
        for t, h in nodes)
    return ('<h2 class="sub">七层逻辑闭环图（点节点进对应册/锚点）</h2><div class="card">'
            + chain +
            '<div class="meta" style="color:#8ea3b6;font-size:12px;margin-top:6px">'
            '证据链自上而下：世界观定大势 → 国家战略定钱往哪条线 → 资金流动定松紧 → 板块轮动定哪个群热 → '
            '机会池按五关筛候选 → 持仓按单一源决策 → 复盘记分卡回评每层判断（判断ID回链）。'
            '<b>闭环</b>：⑦记分卡的判对/判错 → 明日回改①-④的确定性档位（见④册魂①支柱累积表）。</div></div>')


def _top3_card(date: str, dyn: dict, daily: dict, stats: dict, oneline: str) -> str:
    """甲2：「今天先看这3件」置顶卡——给明确阅读顺序，治"无从下手"。
    三件都只【引用】既有单一源(derived / pending_decisions / final)，不新造判断。"""
    # ② 今天要拍板几件
    try:
        pd_ = rj(ROOT / "data" / "pdca" / "pending_decisions.json")
        n_pend = int(pd_.get("pending_count") or 0)
        # 3收尾：原来 [:26] 硬切 proposal → 悬着"…低于15.0%下限 → …"半句。
        # 改：整句不截(proposal 本来就短)，句尾的"→ 是否…？"是完整问句、别切掉。
        pend_txt = "；".join(str(i.get("proposal", "")).strip() for i in (pd_.get("items") or [])[:2])
    except Exception:
        n_pend, pend_txt = 0, ""
    # ③ 持仓今天要不要动(动作按 final 单一源统计)
    acts = {}
    for h in dyn["prod"].get("holdings", []):
        s = str(h.get("symbol"))
        if s.startswith("CC."):
            continue
        f = build_final(s, h.get("name", s), dyn)
        a = re.sub(r"<[^>]+>", "", str(f["action"])).strip()
        acts[a] = acts.get(a, 0) + 1
    n_all = sum(acts.values())
    act_txt = "、".join(f"{k} {v} 只" for k, v in sorted(acts.items(), key=lambda x: -x[1]))
    move = n_all - acts.get("守", 0) - acts.get("等", 0)
    act_line = (f"<b style='color:#7ee0a0'>今天不用动手</b>——{n_all} 只全是「守／等」" if move == 0
                else f"<b style='color:#ffd479'>有 {move} 只不是「守／等」</b>，要看一下")

    def item(n, title, body, link):
        return (f'<div style="display:flex;gap:11px;padding:9px 0;border-top:1px solid #2b4054">'
                f'<div style="flex:0 0 26px;height:26px;border-radius:50%;background:#2c6e9a;color:#fff;'
                f'font-weight:900;font-size:14px;display:flex;align-items:center;justify-content:center">{n}</div>'
                f'<div style="flex:1"><div style="font-size:13.5px;color:#9ed8ff;font-weight:700">{title}</div>'
                f'<div style="font-size:14px;margin-top:2px">{body}</div>'
                f'<div style="font-size:11.5px;margin-top:2px">{link}</div></div></div>')

    return ('<div class="card" style="background:#152238;border:2px solid #4a7fb5;border-radius:10px">'
            '<div style="font-size:19px;font-weight:900;color:#ffd479;letter-spacing:.5px">今天先看这 3 件</div>'
            '<div style="font-size:11.5px;color:#8ea3b6;margin-bottom:2px">按这个顺序看就行；下面的大环境/机会池/记分卡是想深究时才翻的底料。</div>'
            + item(1, "大方向：今天整体怎么走",
                   f'<b>{oneline}</b>',
                   _a(L1(date, "layer-world"), "→ 想知道为什么这么判：看下面「大环境六层」"))
            + item(2, "今天要你拍板的事",
                   (f'<b style="color:#ffd479">{n_pend} 件</b>' + (f'<br>{esc(pend_txt)}' if pend_txt else '')
                    if n_pend else '<b style="color:#7ee0a0">0 件</b>——今天没有需要你拍板的事'),
                   (_a(L1(date, "pending-inbox"), "→ 去拍板收件箱") if n_pend else ""))
            + item(3, "你的持仓今天要不要动",
                   f'{act_line}<div style="font-size:12.5px;color:#c8d4de;margin-top:2px">明细：{esc(act_txt)}</div>',
                   _a(L1(date, "hold-table"), "→ 看下面「持仓一眼看全」表（带现价和贵便宜轴）"))
            + '</div>')


def _summary_tables(date: str, dyn: dict, stats: dict) -> str:
    """总览册摘要表：持仓/机会/记分 每行链进对应深册锚点。
    乙5：升级为「一眼看全」对比表——股票｜今天怎么办｜现价｜合理价(未来1~2年)｜贵便宜迷你数轴。"""
    rows = []
    for h in dyn["prod"].get("holdings", []):
        s = str(h.get("symbol"))
        if s.startswith("CC."):
            continue
        f = build_final(s, h.get("name", s), dyn)
        c = cur(s)
        px = _price_of(s, dyn)
        v = (dyn.get("valr", {}) or {}).get(s, {}) or {}
        ok = str(v.get("status")) == "OK" and v.get("intrinsic") is not None
        if ok:
            fair = (f'{c}{v["reasonable_low"]:,.0f} ~ {c}{v["reasonable_high"]:,.0f}'
                    f'<br><span style="color:#8ea3b6;font-size:11px">中间值 {c}{v["intrinsic"]:,.0f}</span>')
            axis = _val_axis(s, dyn, mini=True)
        else:
            # 算不出估值的：这一格写人话原因(不留白·不编数)
            t = str(v.get("type") or "")
            why = {"周期股": "周期股·景气高点算不准", "控股公司": "控股公司·要分项估值",
                   "商社": "综合商社·要分项估值"}.get(t, "缺可信估值输入")
            fair = f'<span style="color:#ffb454">算不出该值多少</span><br><span style="color:#8ea3b6;font-size:11px">{esc(why)}</span>'
            axis = '<span style="color:#8ea3b6;font-size:11px">不画轴——算不出就不编</span>'
        rows.append(f'<tr><td>{_a(L2(date, "stock-" + s), esc(str(h.get("name"))))}'
                    f'<br><span style="color:#8ea3b6;font-size:11px">{esc(s)}</span></td>'
                    f'<td><b style="font-size:14px">{f["action"]}</b>'
                    f'<br><span style="color:#8ea3b6;font-size:11px">{esc(_conf_grade(f))}</span></td>'
                    f'<td style="text-align:right;white-space:nowrap"><b>{esc(c)}{px:,.2f}</b></td>'
                    f'<td style="white-space:nowrap">{fair}</td>'
                    f'<td style="min-width:150px">{axis}</td></tr>')
    hold_tbl = ('<table class="dt"><tr><th>股票</th><th>今天怎么办</th><th style="text-align:right">现价</th>'
                '<th>合理价<br><span style="font-weight:400;font-size:10.5px;color:#8ea3b6">未来1~2年该值多少</span></th>'
                '<th>便宜 ─ 合理 ─ 贵（▼=今天的价）</th></tr>'
                + "".join(rows) + '</table>'
                + f'<div class="meta" style="color:#8ea3b6;font-size:11.5px">'
                  f'「合理价」是<b>{esc(HORIZON_NOTE)}</b>。绿=便宜 / 黄=合理 / 红=贵；▼是今天的价落在哪。'
                  f'点股票名进该只的10块深卡。</div>')
    try:
        pd_ = rj(ROOT / "data" / "pdca" / "pending_decisions.json")
        n_pend = int(pd_.get("pending_count") or 0)
    except Exception:
        n_pend = 0
    try:
        # 甲1：①册摘要也走同一算子(原来读陈旧的 pillar_score.json → 与④册报不同的数)
        pil = "、".join(f'{p["ring_name"]}{p["current_certainty"]}({p["cumulative_score"]:+d}{p["trend_arrow"]})'
                       for p in pillars_now(date)["pillars"])
    except Exception:
        pil = "待接"
    # 甲3 分主次：持仓「一眼看全」是【主】(大标题·置顶)；机会/记分是【次】(可折叠·想深究再翻)
    return ('<h2 class="main" id="hold-table">持仓 · 一眼看全（{}只）</h2>'.format(stats["n"])
            + f'<div class="card">{hold_tbl}</div>'
            + '<details class="sub"><summary>机会 / 记分 摘要（点开看·想深究时才用）</summary>'
            + f'<div class="card" style="margin-top:6px">{funnel_scope_line(date, dyn["daily"], dyn)}'
              f'（与③机会池册同一口径·同一算子）；详见 {_a(VOL(date, 3), "③机会池册")}。'
              f'今日待拍板 <b style="color:#ffd479">{n_pend}</b> 件（见本册上方拍板收件箱）。</div>'
            + f'<div class="card">支柱确定性累积：{esc(pil)}；三件魂详见 {_a(VOL(date, 4), "④记分卡/复盘册")}。</div>'
            + '</details>')

def _pretty(h: str) -> str:
    """丙4：单行超长HTML→按块级标签换行(体积几乎不变·便于董事长核验与 git diff)。
    只在标签【之间】插换行，绝不动标签内部与文本内容 → 渲染结果一字不变。"""
    # 收尾标签后换行(块级)
    h = re.sub(r"(</(?:div|h1|h2|h3|table|tr|ul|ol|li|details|p|style|head|body|html)>)(?=<)", r"\1\n", h)
    # 开头标签前换行(块级·且前面不是换行)
    h = re.sub(r"(?<!\n)(<(?:div|h1|h2|h3|table|tr|ul|ol|li|details|p)\b)", r"\n\1", h)
    h = re.sub(r"\n{3,}", "\n\n", h)
    return h


def main() -> int:
    import sys
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="深度完整产品·实时自动渲染器")
    ap.add_argument("--date", required=True)
    ap.add_argument("--only", default="", help="逗号分隔symbol·仅渲这些(打通用)")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    only = [s.strip() for s in a.only.split(",") if s.strip()] or None
    try:
        htmltxt, stats = build(a.date, only)
    except StaleSnapshotError as e:
        print(f"[拒绝生成·R3] {e}", file=sys.stderr)
        return 4
    vols = stats.get("volumes") or {}
    if vols and not only:
        # ── 丙4：单行超长HTML→按块加换行(体积几乎不变·便于核验与diff) ──
        vols = {k: _pretty(v) for k, v in vols.items()}
        # ── 丙1：出厂机械核 —— FAIL 即【不出品】(不落盘·不覆盖旧册) ──
        try:
            from product_lint import lint_volumes
            fails = lint_volumes(vols, a.date)
        except Exception as e:
            print(f"[出厂核 异常] {e}", file=sys.stderr)
            return 5
        if fails:
            print(f"[出厂核 FAIL·不出品] {len(fails)} 条 —— 旧册未被覆盖：", file=sys.stderr)
            for f in fails:
                print("  ✗ " + f, file=sys.stderr)
            return 5
        print(f"[出厂核 PASS] {len(vols)} 册 · L1乱码/L2同源/L3转义/L4错模板/L5数字/L6状态词/L7半截/L8链接 全过")
        total = 0
        for fname, txt in vols.items():
            p = ROOT / "00_请先看这里" / fname
            p.write_text(txt, encoding="utf-8")
            b = p.read_bytes()
            total += len(b)
            print(f"wrote {fname} · bytes={len(b)} · 乱码EFBFBD={b.count(b'\xef\xbf\xbd')}")
        print(f"五册合计 bytes={total}")
        # ── 丙2/丙3：登记实物指纹(防回滚哨兵) + 回写主控进度块 ──
        try:
            from product_manifest import write_manifest, sync_master
            rid = stats.get("run_id", ""); sj = stats.get("scan_jst", "")
            write_manifest(a.date, rid, sj, list(vols.keys()))
            print(f"[哨兵] 已登记 {len(vols)} 册指纹 → data/product_manifest.json")
            print(sync_master(a.date, rid, sj, list(vols.keys())))
        except Exception as e:
            print(f"[哨兵/回写 失败] {e}", file=sys.stderr)
    else:
        out = a.out or str(ROOT / "00_请先看这里" / f"完整产品_{a.date}_机器版.html")
        Path(out).write_text(htmltxt, encoding="utf-8")
        b = Path(out).read_bytes()
        print(f"wrote {out} · bytes={len(b)} · 乱码EFBFBD={b.count(b'\xef\xbf\xbd')}")
    print(f"卡片 {stats['n']} 只 · 判断包命中 {stats['pack_ok']} · 深度10块 {stats.get('deep10', [])} · 无判断包 {stats['pack_wait']} · 退出条件待补(动作降初判) {stats['exit_todo']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
