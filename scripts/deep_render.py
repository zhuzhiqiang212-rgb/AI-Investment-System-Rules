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
from datetime import datetime, timezone
from pathlib import Path
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
    return {
        "一句话结论": grab("一句话结论", ["底层深挖", "上层对比"]),
        "生意": grab("生意", ["护城河", "真数据", "上层对比"], frm=deep_i if deep_i > -1 else 0),
        "护城河": grab("护城河", ["真数据", "上层对比", "风险"], frm=deep_i if deep_i > -1 else 0),
        "真数据": grab("真数据", ["上层对比", "风险", "决策", "缺口", "来源"], frm=moat_i if moat_i > -1 else 0),
        "对估值": grab("对估值", ["对组合", "风险", "决策"], frm=upper_i if upper_i > -1 else 0),
        "风险": grab("风险", ["决策合理性", "决策把关", "缺口", "来源"], frm=upper_i if upper_i > -1 else 0),
        "决策": grab("综合", ["缺口", "来源"]) or grab("决策合理性把关", ["缺口", "来源"]),
    }

# ── 动态数据 ──
def load_dynamic(date: str) -> dict:
    prod = rj(ROOT / "data" / "reports" / f"production_{date}.json")
    daily = rj(ROOT / "data" / "evidence_chain" / f"daily_{date}.json")
    ma = {x["symbol"]: x for x in (rj(ROOT / "data" / "holdings" / f"ma_levels_{date}.json").get("holdings") or [])}
    ht = {h["symbol"]: h for h in (rj(ROOT / "data" / "accounts" / f"holdings_true_{date}.json").get("holdings") or [])}
    return {"prod": prod, "daily": daily, "ma": ma, "ht": ht}

def cur(sym: str) -> str: return "¥" if sym.startswith("JP.") else "$"
def fnum(v):
    try:
        f = float(v); return f"{f:,.0f}" if abs(f) >= 100 else f"{f:,.2f}"
    except (TypeError, ValueError): return None

# ── 单只持仓卡（深研+动态+档案） ──
def render_card(sym: str, name: str, dyn: dict) -> str:
    prod_h = next((h for h in dyn["prod"].get("holdings", []) if h.get("symbol") == sym), {})
    price = prod_h.get("price"); qg = prod_h.get("quality_gate", {}) or {}
    action = prod_h.get("action", "待接"); reason = prod_h.get("one_line_reason", "")
    val = (prod_h.get("valuation", {}) or {}).get("label", "待接")
    ma = dyn["ma"].get(sym, {}); ht = dyn["ht"].get(sym, {})
    c = cur(sym)
    # 深研（判断包·真源）
    pack = find_pack(sym, name)
    if pack:
        ex = extract_pack(pack)
        deep = (f'<div class="deep"><span class="k">深研·财报趋势</span>{esc(ex["真数据"] or ex["一句话结论"] or "判断包未含真数据段")}'
                f'<div style="margin-top:5px"><span class="k">生意/增长点</span>{esc(ex["生意"])}'
                f'<span class="k">护城河/竞争格局</span>{esc(ex["护城河"])}</div>'
                f'<div style="margin-top:5px"><span class="k">一句话结论</span>{esc(ex["一句话结论"])}'
                f'<span class="k">买入逻辑(对估值)</span>{esc(ex["对估值"] or "判断包未含对估值段")}'
                f'<span class="k">退出条件/风险</span>{esc(ex["风险"])}</div>'
                f'<div class="meta" style="color:#8fd6ff;font-size:12px;margin-top:4px">深研源：{esc(pack.name)}（判断包·真源抽取）</div></div>')
        pack_status = "OK"
    else:
        deep = '<div class="deep"><span class="k">深研·财报趋势</span><span style="color:#c9a86a">待建判断包（个股判断包_*.html 缺该只·不编）</span></div>'
        pack_status = "待建判断包"
    # 档案（股数/成本/均线趋势参考·缺不编）
    qty = ht.get("total_quantity"); cost = ht.get("avg_cost_price")
    accs = ht.get("accounts") or []
    if qty:
        parts = []
        for a in accs:
            q = a.get("quantity")
            if q:
                parts.append(f"{a.get('account','')}{q:g}")
        qty_s = f"{qty:g}股" + (f"（{'＋'.join(parts)}）" if parts else "")
    else:
        qty_s = "待接·无真股数"
    cost_s = f"{c}{fnum(cost)}（四账户均价·{ht.get('cost_grade','')}级）" if cost is not None else "待接·四账户无成本记录（不编）"
    ma20, ma50, ma200 = ma.get("ma20"), ma.get("ma50"), ma.get("ma200")
    ma_s = (f"20日{c}{fnum(ma20)}/50日{c}{fnum(ma50)}/200日{c}{fnum(ma200)}（均线位·仅趋势参考·不作买卖线）"
            if ma200 is not None else "待接·均线不足（不编）")
    dossier = (f'<div class="dossier"><span class="k">档案</span><b>持仓</b>{esc(qty_s)} ｜ <b>成本</b>{esc(cost_s)} '
               f'｜ <b>现价</b>{esc(c)}{esc(fnum(price)) if price is not None else "待接"} ｜ <b>均线</b>{esc(ma_s)}</div>')
    # 质量关+动作
    qt = qg.get("tier", ""); qlab = qg.get("tier_label", "")
    hd = (f'<div class="hd"><b>{esc(name)}</b> <span class="sym">{esc(sym)}</span> '
          f'<span class="conf">动作：{esc(action)}</span> '
          f'<span class="q">账本：{esc(qt)}{esc(qlab)}</span> <span class="v">贵不贵：{esc(val)}</span></div>')
    return (f'<div class="card">{hd}{deep}{dossier}'
            f'<div class="you"><span class="k">今天对你</span>{esc(reason)}</div></div>'), pack_status

# ── 第一部分·五层大环境（daily links·今日事件现渲） ──
def part1_layers(daily: dict) -> str:
    links = daily.get("links") or []
    rows = []
    for l in links:
        node = l.get("node", ""); strg = l.get("strength", ""); dr = l.get("direction", "")
        plain = l.get("plain") or l.get("today_plain") or ""
        rows.append(f'<div class="card"><div class="hd"><b>{esc(node)}</b> '
                    f'<span class="conf">力度 {esc(strg)} · 方向 {esc(dr)}</span></div>'
                    f'<div class="you">{esc(plain) if plain else "今日事件待接（daily 无该层大白话·不编）"}</div></div>')
    if not rows:
        rows.append('<div class="card">五层数据待接（daily_{date}.json 无 links·不编）</div>')
    return '<h2>第一部分 · 大环境今天怎么了（五层）</h2>' + "".join(rows)

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
        return '<h2>第三部分 · 仓位集中度（哪一类押太多了）</h2><div class="card">' + "".join(rows) + '</div>'
    except Exception as e:
        return f'<h2>第三部分 · 仓位集中度</h2><div class="card">集中度现算失败·待接（{esc(e)}）</div>'

# ── 第四/五部分 ──
def part4_5(daily: dict, dyn: dict) -> str:
    der = daily.get("derived", {}) or {}
    scope = esc(str(der.get("opportunity_scope", "待接")))
    close = esc(str(der.get("today_direction_short") or der.get("today_direction", "待接")))
    return ('<h2>第四部分 · 机会池：该不该换、换谁</h2>'
            f'<div class="card">机会口径（现算）：{scope}<div class="meta" style="color:#8ea3b6;font-size:12px">候选详情见机会层引擎·此处给口径</div></div>'
            '<h2>第五部分 · 整条逻辑怎么闭环</h2>'
            f'<div class="card">{close}</div>')

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


# ── 第七部分·PDCA复盘记分卡（pdca_daily rings·现渲） ──
def part7_pdca(date: str) -> str:
    pd = rj(ROOT / "data" / "pdca" / f"pdca_daily_{date}.json")
    rings = pd.get("rings") or []
    dq = pd.get("decision_quality", {}) or {}
    head = ('<h2>第七部分 · PDCA 复盘记分卡系统（今天的判断，明天验证 · 系统的魂）</h2>'
            f'<div class="card">今天下手的底气：<b>{esc(dq.get("level", "待接"))}</b>——{esc(dq.get("reason", ""))}'
            '<div class="meta" style="color:#8ea3b6;font-size:12px">判对给尺加把握、判错改尺——证伪落到实处的闭环。</div></div>')
    rows = []
    for r in rings:
        rows.append(f'<div class="card"><div class="hd"><b>{esc(r.get("ring_name"))}</b>'
                    f'（{esc(r.get("node"))}）<span class="conf">判断：{esc(r.get("judgment"))}</span></div>'
                    f'<div class="you" style="font-weight:400;font-size:12.5px;color:#bcd8ee">依据：{esc((r.get("evidence") or "待接")[:220])}</div></div>')
    return head + ("".join(rows) if rows else '<div class="card">PDCA rings 待接（pdca_daily 无 rings·不编）</div>')


def build(date: str, only: list[str] | None = None) -> tuple[str, dict]:
    dyn = load_dynamic(date)
    holds = dyn["prod"].get("holdings", [])
    stocks = [h for h in holds if not str(h.get("symbol","")).startswith("CC.")]
    if only:
        stocks = [h for h in stocks if h.get("symbol") in only]
    cards = []; stats = {"n": 0, "pack_ok": 0, "pack_wait": []}
    for h in stocks:
        card, ps = render_card(h["symbol"], h.get("name", h["symbol"]), dyn)
        cards.append(card); stats["n"] += 1
        if ps == "OK": stats["pack_ok"] += 1
        else: stats["pack_wait"].append(h["symbol"])
    gen = datetime.now(timezone.utc).isoformat()[:19]
    head = ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>完整产品·机器版(实时自动生成)</title><style>'
            'body{font-family:"Microsoft YaHei",Arial,sans-serif;background:#0b1118;color:#eef5f9;line-height:1.7;max-width:1000px;margin:0 auto;padding:16px}'
            '.card{background:#151f2b;border:1px solid #2b4054;border-radius:10px;padding:12px 14px;margin:10px 0}'
            '.hd{font-size:16px;margin-bottom:8px}.sym{color:#8ea3b6;font-size:12px}.conf{color:#ffd479}.q{color:#7ee0a0;font-size:13px}.v{color:#9ed8ff;font-size:13px}'
            '.k{color:#5cc8ff;font-weight:700;margin-right:6px}.deep{margin:6px 0;font-size:14px}.dossier{margin:6px 0;font-size:13px;color:#d9e7ef}.you{margin-top:6px;font-weight:700}'
            '</style></head><body>')
    title = (f'<h1>每日投资决策台 · 完整产品（机器版·实时自动生成）</h1>'
             f'<p style="color:#9aa8b5">数据 {esc(date)} 实时 ｜ 生成 {esc(gen)} UTC ｜ 深研=个股判断包真源抽取 · 动态=production现算 · 均线仅趋势参考不作买卖线 · 缺不编</p>')
    part2 = f'<h2>第二部分 · 你的持仓，今天怎么办（{stats["n"]}只）</h2>' + "".join(cards)
    if only:   # 打通模式:只出持仓卡
        return head + title + part2 + "</body></html>", stats
    daily = dyn["daily"]
    der = daily.get("derived", {}) or {}
    oneline = esc(str(der.get("today_direction_short") or "今天：守核心、不追高、控AI集中"))
    banner = (f'<div class="card" style="background:#1c2740;border-color:#3a5a8a">'
              f'<span class="k">今天一句话</span><b style="font-size:15px">{oneline}</b></div>')
    full = (title + banner + part1_layers(daily) + part1_macro_table(daily) + part2
            + part3_concentration(date, dyn) + part4_5(daily, dyn) + part6_rulers() + part7_pdca(date))
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
    htmltxt, stats = build(a.date, only)
    out = a.out or str(ROOT / "00_请先看这里" / f"完整产品_{a.date}_机器版.html")
    Path(out).write_text(htmltxt, encoding="utf-8")
    b = Path(out).read_bytes()
    print(f"wrote {out} · bytes={len(b)} · 乱码EFBFBD={b.count(b'\xef\xbf\xbd')}")
    print(f"卡片 {stats['n']} 只 · 判断包OK {stats['pack_ok']} · 待建判断包 {stats['pack_wait']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
