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
def load_dynamic(date: str) -> dict:
    prod = rj(ROOT / "data" / "reports" / f"production_{date}.json")
    daily = rj(ROOT / "data" / "evidence_chain" / f"daily_{date}.json")
    ma = {x["symbol"]: x for x in (rj(ROOT / "data" / "holdings" / f"ma_levels_{date}.json").get("holdings") or [])}
    ht = {h["symbol"]: h for h in (rj(ROOT / "data" / "accounts" / f"holdings_true_{date}.json").get("holdings") or [])}
    # 估值单一源(valuation_results·分类型精算·R1 final.valuation 只从这里取)
    valr = {r["symbol"]: r for r in (rj(ROOT / "data" / "valuation" / f"valuation_results_{date}.json").get("results") or []) if r.get("symbol")}
    return {"prod": prod, "daily": daily, "ma": ma, "ht": ht, "valr": valr}


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

def _load_deep_card(sym: str):
    p = DEEP_DIR / f"{sym}.json"
    if not p.exists():
        return None
    try:
        return rj(p)
    except Exception:
        return None

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
                rows = []
                for lbl, at, dd in [("资产涨：持有资产(Arm/OpenAI等) +10%", tot * 1.1, disc),
                                    ("资产跌：持有资产 -10%", tot * 0.9, disc),
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
    out.append('<div class="blk">⑤ 它到底值多少钱（算法+过程+区间+"如果变了"）</div>'
               f'<div class="plain"><b>怎么算</b>：{_nd(v5.get("method_plain",""))}</div>'
               '<table class="dt"><tr><th>要填的输入</th><th>大白话</th></tr>' + inrows + '</table>' + inval
               + f'<p style="font-size:13px"><span class="k">算出来</span>{rng}（与决策条同一源·R1）。{_nd(v5.get("note",""))}</p>'
               + senstbl)
    # ⑥ 牛/基/熊三情景
    sc = deep.get("block6_scenarios", {})
    scrows = "".join(f'<tr><td class="{r.get("cls","base")}">{_nd(r.get("case",""))}</td><td>{_nd(r.get("assume",""))}</td><td>{_nd(r.get("value",""))}</td><td>{_nd(r.get("prob",""))}</td></tr>' for r in sc.get("rows", []))
    out.append('<div class="blk">⑥ 好、中、坏三种情况分别值多少</div>'
               '<table class="dt"><tr><th>情况</th><th>假设(人话)</th><th>值多少</th><th>大概几成可能</th></tr>' + scrows + '</table>'
               f'<p style="font-size:13px"><span class="k">这告诉你</span>{_nd(sc.get("readout",""))}</p>')
    # ⑦ 催化剂日历
    cats = "".join(f'<li>{_nd(x)}</li>' for x in deep.get("block7_catalysts", []))
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
    _deepcard = _load_deep_card(sym)
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
    cost_s = f"{c}{fnum(cost)}（四账户均价·{ht.get('cost_grade','')}级）" if cost is not None else "待接·四账户无成本记录（不编）"
    ma20, ma50, ma200 = ma.get("ma20"), ma.get("ma50"), ma.get("ma200")
    ma_s = (f"20日{c}{fnum(ma20)}/50日{c}{fnum(ma50)}/200日{c}{fnum(ma200)}（均线位·仅趋势参考·不作买卖线）"
            if ma200 is not None else "待接·均线不足（不编）")
    dossier = (f'<div class="dossier"><span class="k">档案</span><b>持仓</b>{esc(qty_s)} ｜ <b>成本</b>{esc(cost_s)} '
               f'｜ <b>现价</b>{esc(c)}{esc(fnum(price)) if price is not None else "待接"} ｜ <b>均线</b>{esc(ma_s)}</div>')
    # 标题 + 决策条（全部引 final·单一源）
    hd = (f'<div class="hd"><b>{esc(name)}</b> <span class="sym">{esc(sym)}</span> '
          f'<span class="conf">动作：{f["action"]}</span> '
          f'<span class="q">账本：{f["quality"]}</span> <span class="v">估值：{f["valuation_short"]}（{f["valuation_grade"]}）</span></div>')
    conf_grade = _conf_grade(f)   # R10②:账本档→高/中/低把握(显式)
    final_row = (f'<div class="dossier" style="background:#12203a;border-radius:6px;padding:6px 8px">'
                 f'<span class="k">决策(单一源)</span>'
                 f'<b>动作</b>{f["action"]} ｜ <b>估值</b>{f["valuation"]} ｜ <b>账本</b>{f["quality"]} '
                 f'｜ <b>把握</b><span style="color:#ffd479;font-weight:700">{esc(conf_grade)}</span>（{f["confidence"]}）</div>')
    return (f'<div class="card">{hd}{final_row}{deep}{dossier}'
            f'<div class="you"><span class="k">今天对你(单一源)</span>{f["reason"]}</div></div>'), pack_status

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
    names = "、".join(esc(name_by[s]) for s in members) or "—"
    expo = (sum(mv.get(s, 0.0) for s in members) / total * 100.0) if total > 0 else 0.0
    return ('<div class="you" style="margin-top:5px;font-weight:400;color:#9ed8ff">'
            f'<b style="color:#5cc8ff">对你·落点持仓（哪几只受影响）</b>：{names}'
            f'<span style="color:#8ea3b6">（同属风险因子「{esc(fac)}」·合计敞口 {expo:.1f}%·见第三部分附）</span></div>')

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

def part1_layers(daily: dict, dyn: dict) -> str:
    links = daily.get("links") or []
    rows = []
    for l in links:
        node = l.get("node", ""); strg = l.get("strength", ""); dr = l.get("direction", "")
        plain = l.get("plain") or l.get("today_plain") or ""
        evidence = str(l.get("evidence") or "")
        events = l.get("today_events") or []
        fact = esc(str(dr)) + ((" ｜ " + esc(str(events[0]))) if events else "")
        why = esc(evidence) if evidence else "为什么这么判：待接（daily 无 evidence·不编）"
        flip = _match(node, _LAYER_FLIP, "出现与当前方向相反的持续证据")
        ruler = _match(node, _LAYER_RULER, "第六部分·右栏底子")
        rows.append(
            f'<div class="card"><div class="hd"><b>{esc(node)}</b> '
            f'<span class="conf">力度 {esc(strg)} · 方向 {esc(dr)}</span></div>'
            f'<div style="font-size:13px"><span class="k">① 事实(今天怎么了)</span>{fact}</div>'
            f'<div style="font-size:13px;margin-top:3px"><span class="k">② 为什么(这么判的依据)</span>{why}</div>'
            + _layer_impact(node, dyn).replace("对你·落点持仓", "③ 对你·落点持仓")
            + f'<div style="font-size:13px;margin-top:3px"><span class="k">④ 什么情况改看法(证伪)</span>{esc(flip)}</div>'
            f'<div class="meta" style="color:#8ea3b6;font-size:11.5px;margin-top:3px">大白话：{esc(plain) if plain else "待接"}｜对应尺：{esc(ruler)}</div>'
            '</div>')
    if not rows:
        rows.append('<div class="card">五层数据待接（daily_{date}.json 无 links·不编）</div>')
    return ('<h2>第一部分 · 大环境今天怎么了（五层·每层 事实→为什么→对你落点→什么情况改看法·接右栏6尺）</h2>'
            + "".join(rows))

# ── 第一部分附·宏观判定表（尺模板+当日读数） ──
def part1_macro_table(daily: dict) -> str:
    der = daily.get("derived", {}) or {}
    td = esc(str(der.get("today_direction", "待接")))
    return ('<h2>第一部分附 · 宏观指标"强/中/弱/证伪"判定标准表（尺）</h2>'
            '<div class="card"><table border="1" cellpadding="5" style="border-collapse:collapse;font-size:13px">'
            '<tr><th>档</th><th>含义（尺）</th></tr>'
            '<tr><td>强</td><td>方向明确成立、证据充分</td></tr>'
            '<tr><td>中</td><td>方向成立但力度一般/证据部分</td></tr>'
            '<tr><td>弱</td><td>方向存疑/证据转软</td></tr>'
            '<tr><td>证伪</td><td>反向证据出现、判断被推翻</td></tr></table>'
            f'<div class="you" style="margin-top:6px">当日读数：{td}</div></div>')

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
    rows = []
    for f in order:
        members = [s for s, fs in by_sym.items() if f in fs and s in name_by]
        expo = sum(mv.get(s, 0.0) for s in members)
        pct = expo / total * 100.0
        mem_txt = "、".join(f"{esc(name_by[s])}" + ("" if s in mv else "(市值缺·未计敞口)") for s in members) or "—"
        rows.append(f'<tr><td style="padding:5px 8px;border-bottom:1px solid #24384c;font-weight:700;color:#ffd479">{esc(f)}</td>'
                    f'<td style="padding:5px 8px;border-bottom:1px solid #24384c">{mem_txt}</td>'
                    f'<td style="padding:5px 8px;border-bottom:1px solid #24384c;text-align:right;color:#7ee0a0">{pct:.1f}%</td></tr>')
    tbl = ('<table style="width:100%;border-collapse:collapse;font-size:13px">'
           '<tr style="color:#8ea3b6"><th style="text-align:left;padding:5px 8px">共同风险因子</th>'
           '<th style="text-align:left;padding:5px 8px">挂着哪几只持仓</th>'
           '<th style="text-align:right;padding:5px 8px">合计敞口%</th></tr>' + "".join(rows) + '</table>')
    note = ('<div class="meta" style="color:#8ea3b6;font-size:12px;margin-top:6px">'
            '敞口%=该因子成分股当日折美元市值合计÷全持仓合计（现算·非写死）；一只可挂多因子故各因子敞口相加可>100%。'
            '归属映射见 data/valuation/risk_factors.json（可迭代·改一只因子归属→本表成分股与敞口数字联动变）。</div>')
    return ('<h3 style="margin-top:14px">第三部分附 · 共同风险因子穿透（同一冲击会同时打到哪几只）</h3>'
            '<div class="card">' + tbl + note + '</div>')

def part3_concentration(date: str, dyn: dict) -> str:
    try:
        import full_product_render as fpr
        cost = rj(ROOT / "data" / "accounts" / "unified_holdings_latest.json")
        conc = fpr.portfolio_concentration(dyn["prod"].get("holdings", []),
                                           (cost.get("summary", {}) or {}).get("known_cash_usd"), {})
        rows = []
        for k, v in (conc.get("categories", {}) or {}).items():
            pct = v.get("pct"); lim = v.get("limit"); over = v.get("over"); short = v.get("short")
            flag = "⚠超上限" if over else ("⚠低于下限" if short else "在限内")
            rows.append(f'<div>· <b>{esc(k)}</b>：{pct:.1f}%（限 {lim}%）· {flag}</div>')
        conc_html = '<h2>第三部分 · 仓位集中度（哪一类押太多了）</h2><div class="card">' + "".join(rows) + '</div>'
    except Exception as e:
        conc_html = f'<h2>第三部分 · 仓位集中度</h2><div class="card">集中度现算失败·待接（{esc(e)}）</div>'
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
    head = (f'<h2>第四部分 · 机会池：该不该换、换谁（现算候选 {in_pool}/{len(wl)} 进池·证据驱动·6a）</h2>'
            f'<div class="card">当日激活承接节点(证据源)：{esc("、".join(active) or "待接")}｜机会口径：{scope}'
            '<div class="meta" style="color:#8ea3b6;font-size:12px">候选是否进池由「节点是否在当日激活承接节点」现算·改当日证据→候选集变（6b替换引擎=P2）</div></div>')
    return head + "".join(rows)

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
            moat_a = esc(str((next((h for h in holds if h.get("symbol") == asym), {}) or {}).get("moat", "") or "待接"))[:40]
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

def part4_funnel(date: str, daily: dict, dyn: dict) -> str:
    active = _active_nodes(daily)
    try:
        uni = rj(ROOT / "data" / "valuation" / "candidate_universe.json").get("nodes", {}) or {}
    except Exception as e:
        return f'<h2>第四部分附 · 机会池全扫</h2><div class="card">候选宇宙待接（candidate_universe.json 缺：{esc(e)}）</div>'
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
    seen = set()
    for node, cands in uni.items():
        for c in (cands or []):
            nm = c.get("name", ""); tk = str(c.get("ticker") or "")
            key = (node, nm)
            if key in seen:
                continue
            seen.add(key)
            g1 = _node_active(node, active)                       # ①硬性:节点激活
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
    # 过关分布统计
    n_total = len(all_rows); n_g1 = sum(1 for r in all_rows if r["g1"])
    n_g2 = sum(1 for r in all_rows if r["g1"] and "过·站上" in r["g2"])
    # 池一:值得看候选池
    wrows = ""
    for r in worth:
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
        wrows = '<div class="card">今日无候选过硬性关（激活节点内候选均待接均线数据·不编）</div>'
    # 池二:用户挑战池(结构·待董事长指定)
    pool2 = ('<div class="blk">池② 用户挑战池（董事长想挑战/加看的标的·跑同样五关给结论）</div>'
             '<div class="card"><span class="need">待董事长指定</span>——结构已留：董事长点名任一标的，即按同一五关漏斗(①硬性②软性③估值④护城河⑤个股)现算给"过到第几关/卡在哪关+结论"。（缺指定→不编）</div>')
    # 池三:等好价标的池(好公司但贵·记便宜位到价提醒)
    pool3 = ('<div class="blk">池③ 等好价标的池（好公司但估值贵·记下便宜位·到价提醒）</div>'
             '<div class="card">结构已留：好公司但当前估值贵者入此池、记"便宜买入位"、到价提醒。'
             '当前候选宇宙外部标的估值多为<span class="need">待接·候选估值未接</span>；持仓中估值偏贵者(如IBKR现价约37倍前瞻>正常化中枢$52.8)已在其个股卡⑤标注等更好点位。外部候选到价提醒待接入候选估值后启用。</div>')
    scope = esc(str((daily.get("derived", {}) or {}).get("opportunity_scope", "待接")))
    head = ('<h2>第四部分附 · ⑤机会池·全市场五关漏斗（候选宇宙→五关现算→三个池·总则第十四条）</h2>'
            f'<div class="card">当日激活承接节点：<b>{esc("、".join(active) or "待接")}</b>｜候选宇宙 {n_total} 只(按节点·candidate_universe.json可迭代)｜'
            f'过①硬性关(节点激活) <b>{n_g1}</b> 只｜过②软性关(站上均线) <b>{n_g2}</b> 只。'
            f'<div class="meta" style="color:#8ea3b6;font-size:12px">五关=①硬性(节点激活)②软性(均线)③估值④护城河⑤个股；过关进"值得看候选池"。改当日激活节点→候选集变(守第六条动态)。gate②均线复用当日 chain_opportunities 真扫描·③④⑤缺真源标待接不编。｜机会口径：{scope}</div></div>')
    return (head + f'<div class="blk">池① 值得看候选池（过①硬性关 {n_g1} 只·带节点+当日证据+多维对比）</div>'
            + wrows + pool2 + pool3)

def part5_closeloop(daily: dict) -> str:
    der = daily.get("derived", {}) or {}
    close = esc(str(der.get("today_direction_short") or der.get("today_direction", "待接")))
    return '<h2>第五部分 · 整条逻辑怎么闭环</h2>' + f'<div class="card">{close}</div>'

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
        ("右栏② 国家战略地图 · 完整底子", "右栏_完整国家战略地图.html", False),
        ("右栏②补 · 安全线／能源线（战略地图·同源）", "右栏_完整国家战略地图.html", False),
        ("右栏③ 资金流动完整机制", "右栏_资金流动完整机制.html", False),
        ("右栏④ 板块地图", "右栏_板块地图.html", False),
        ("右栏⑤ 过滤标准／筛选规则", "右栏_过滤标准筛选规则.html", False),
        ("右栏⑥ 持仓完整档案", "右栏_持仓完整档案.html", False),
    ]
    folds = []
    for title, fname, opened in RULERS:
        body = _ruler_body(fname)
        folds.append(f'<details class="ruler-embed"{" open" if opened else ""}>'
                     f'<summary>{esc(title)}</summary>'
                     f'<div style="background:#f6f2e8;color:#2a2a2a;padding:10px;border-radius:6px">{body}</div></details>')
    return '<h2>第六部分 · 右栏底子（6把尺 · 判断依据）</h2>' + "".join(folds)


# ── 第七部分·PDCA接真记分(R7：昨判今验+累计+预测字段·底气与总闸final同源) ──
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
    head = ('<h2>第七部分 · PDCA 复盘记分卡系统（昨判今验 · 累计打分 · 系统的魂）</h2>'
            f'<div class="card">今天下手的底气(与总闸 final 同源)：<b>{esc(fed_str)}·{esc(fed_dir)}</b>'
            '<div class="meta" style="color:#8ea3b6;font-size:12px">判对给尺加把握、判错改尺——每环带 预测/置信/验证指标/成败标准/自动记分；累计分见各环。</div></div>')
    rows = []
    for r in rings:
        rid = r.get("ring_id")
        tj = traj.get(rid, {})
        series = tj.get("daily_score_series") or []
        pos = sum(1 for s in series if (s.get("daily_score") or 0) > 0)
        tot = len(series)
        acc = f"{pos}/{tot}（{round(pos/tot*100):d}%）" if tot else "首日·待累计"
        # B3③：总闸环今判/置信对齐 R2 状态机 final(与第一部分/底气同源·不再用pdca旧US10Y噪声判)
        _judg, _cert = r.get("judgment"), r.get("current_certainty", "待接")
        if "总闸" in str(r.get("ring_name")) and fed_dir != "待接":
            _judg, _cert = f"{fed_dir}（对齐R2状态机·与第一部分同源）", fed_str
        rows.append(
            f'<div class="card"><div class="hd"><b>{esc(r.get("ring_name"))}</b>（{esc(r.get("node"))}）'
            f'<span class="conf">今判：{esc(_judg)}</span> <span class="q">置信：{esc(_cert)}</span></div>'
            f'<div class="you" style="font-weight:400;font-size:12.5px;color:#bcd8ee">'
            f'· 昨判(预测)：{esc(str(r.get("previous_strength",""))+str(r.get("previous_direction","") or "首日无昨判"))}'
            f'　· 今日验证/自动记分：{esc(str(r.get("daily_score","0")))}分（{esc(r.get("score_reason","待接"))}）'
            f'　· 累计分：{esc(str(r.get("cumulative_score","0")))}'
            f'　· 判对率(自 {esc((series[0].get("date") if series else "?"))})：{esc(acc)}'
            f'　· 成败标准：确定性{esc(r.get("certainty_before","?"))}→{esc(r.get("current_certainty","?"))}（{esc(r.get("certainty_event","维持"))}）</div></div>')
    if not rows:
        rows.append('<div class="card">PDCA rings 待接（pdca_daily 无 rings·不编）</div>')
    return head + "".join(rows) + part7_souls(date, daily)


# ── 第七部分·系统三件魂（总则第十四条：确定性累积表+多尺度复盘+影子组合反事实） ──
def _spark(trend: list) -> str:
    """迷你走势：把每日累积分画成 ▁▃▅▇ 高低块（缺则空）。"""
    if not trend:
        return "（待接·从今日起累积）"
    cums = [t.get("cum", 0) for t in trend]
    lo, hi = min(cums), max(cums)
    blocks = "▁▂▃▄▅▆▇█"
    def b(v):
        if hi == lo:
            return "▄"
        return blocks[min(7, max(0, round((v - lo) / (hi - lo) * 7)))]
    spark = "".join(b(c) for c in cums)
    seq = "→".join(f'{("+" if t["score"]>0 else "")}{t["score"]}' for t in trend)
    return f'{spark}　（{seq}）'

def part7_souls(date: str, daily: dict | None = None) -> str:
    out = ['<h3 style="margin-top:16px">第七部分·魂 —— 系统之魂三件（总则第十四条：确定性累积表 + 多尺度复盘 + 影子组合反事实记分）</h3>']
    # 魂① 支柱确定性累积表
    try:
        ps = rj(ROOT / "data" / "pdca" / "pillar_score.json")
        ladder = "＜".join(ps.get("certainty_ladder", ["证伪", "弱", "中", "高"]))
        prows = ""
        for pl in ps.get("pillars", []):
            prows += (f'<tr><td><b>{esc(pl.get("ring_name"))}</b></td>'
                      f'<td style="color:#ffd479">{esc(pl.get("current_certainty"))}</td>'
                      f'<td style="text-align:right">{esc(str(pl.get("cumulative_score")))}</td>'
                      f'<td>{esc(pl.get("trend_arrow"))}</td>'
                      f'<td style="font-family:monospace;font-size:12px">{esc(_spark(pl.get("trend", [])))}</td>'
                      f'<td style="color:#8ea3b6">{esc(str(pl.get("days_tracked")))}日</td></tr>')
        out.append('<div class="blk">魂① 支柱确定性累积表（三支柱从"中"往"高"攒）</div>'
                   f'<div class="plain">确定性阶梯：{esc(ladder)}；每环每日按尺(支持+1/无变0/证伪-1)滚动累积——判对攒把握、判错减分。源：pillar_score.json(接scorecards·不另起炉灶)。</div>'
                   '<table class="dt"><tr><th>支柱环</th><th>当前档</th><th>累计分</th><th>走势</th><th>近N日轨迹(累积/每日)</th><th>追踪</th></tr>' + prows + '</table>')
    except Exception as e:
        out.append(f'<div class="card">魂①支柱确定性累积表·待接（pillar_score.json 缺：{esc(e)}）</div>')
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
                   + (f'<div class="plain">复盘什么：确定性趋势与判对率；该改什么：判对率高的环升档、低的环重估尺。当前仅 {n_days} 日(<1月)·满月口径随日累积。</div>' ))
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
    _snapshot_guard(date, dyn, only)   # R3 快照单调性闸
    holds = dyn["prod"].get("holdings", [])
    stocks = [h for h in holds if not str(h.get("symbol","")).startswith("CC.")]
    if only:
        stocks = [h for h in stocks if h.get("symbol") in only]
    cards = []; stats = {"n": 0, "pack_ok": 0, "pack_wait": [], "exit_todo": []}
    for h in stocks:
        card, ps = render_card(h["symbol"], h.get("name", h["symbol"]), dyn)
        cards.append(card); stats["n"] += 1
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
            '</style></head><body>')
    title = (f'<h1>每日投资决策台 · 完整产品（机器版·实时自动生成）</h1>'
             f'<div style="background:#0e1621;border:1px solid #3a5a8a;border-radius:8px;padding:8px 12px;margin:6px 0;color:#ffd479;font-weight:700">'
             f'🆔 run_id=<b>{esc(run_id)}</b>'
             f' ｜ 📅 data_date=<b>{esc(date[:4])}-{esc(date[4:6])}-{esc(date[6:])}</b>'
             f' ｜ 本次实时扫描(production)：<b>{esc(scan_jst)}</b>（UTC {esc(scan_ts)}）'
             + (f' ｜ 行情快照日：{esc(md_note)}' if md_note else '')
             + '<div style="font-size:12px;color:#9aa8b5;font-weight:400">run_id 锚定 production_' + esc(date) + '.json（generated_at 同源·可回溯）；同一扫描重渲字节一致（R3运行唯一性）</div></div>'
             f'<p style="color:#9aa8b5">深研=个股判断包真源抽取 · 动态=production现算 · 均线仅趋势参考不作买卖线 · 缺不编</p>')
    part2 = f'<h2>第二部分 · 你的持仓，今天怎么办（{stats["n"]}只）</h2>' + "".join(cards)
    if only:   # 打通模式:只出持仓卡
        return head + title + part2 + "</body></html>", stats
    daily = dyn["daily"]
    der = daily.get("derived", {}) or {}
    oneline = esc(str(der.get("today_direction_short") or "今天：守核心、不追高、控AI集中"))
    banner = (f'<div class="card" style="background:#1c2740;border-color:#3a5a8a">'
              f'<span class="k">今天一句话</span><b style="font-size:15px">{oneline}</b></div>')
    full = (title + banner + part1_layers(daily, dyn) + part1_macro_table(daily) + part2
            + part3_concentration(date, dyn) + part4_opportunity(daily, dyn) + part4b_swap_engine(daily, dyn)
            + part4_funnel(date, daily, dyn) + part5_closeloop(daily)
            + part6_rulers() + part7_pdca(date, daily))
    stats["ruler_embed"] = full.count('class="ruler-embed"')
    stats["deep_blocks"] = full.count('class="deep"')
    return head + full + "</body></html>", stats

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
    out = a.out or str(ROOT / "00_请先看这里" / f"完整产品_{a.date}_机器版.html")
    Path(out).write_text(htmltxt, encoding="utf-8")
    b = Path(out).read_bytes()
    print(f"wrote {out} · bytes={len(b)} · 乱码EFBFBD={b.count(b'\xef\xbf\xbd')}")
    print(f"卡片 {stats['n']} 只 · 判断包命中 {stats['pack_ok']} · 深度10块 {stats.get('deep10', [])} · 无判断包 {stats['pack_wait']} · 退出条件待补(动作降初判) {stats['exit_todo']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
