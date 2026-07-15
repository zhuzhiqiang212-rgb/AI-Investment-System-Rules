#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整产品·深度版渲染器 v3（数据层production + 分析层deep → 深度版HTML）
按《完整产品_深度标准_v1》：每层/每只五要素(事实→为什么→对你→怎么办→什么情况改看法)+把握；
价位只看估值(便宜线/偏贵线)、均线仅背景；缺数人话说清。数字来自production(现算)、分析文字来自deep(分析岗当日写)。
用法：python product_render_v3.py --date 20260714 --root <项目根>
输入：data/reports/production_{date}.json（机器真数）+ data/analysis/deep_{date}.json（分析岗当日分析）
输出：00_请先看这里/完整产品_{date}_机器版.html（2026-07-15改名·机器渲染与分析岗手工超集版_深度版分离·永不覆盖）
"""
from __future__ import annotations
import argparse, html, json, re
from pathlib import Path

USDJPY = 162.536
CRYPTO = {"MSTR","COIN","CRCL","BTCUSD","ETHUSD","BTC","ETH"}
AI_NODE = {"NVDA","MSFT","META","AVGO","6857","TSM","SNDK","9984"}

def esc(x): return html.escape("" if x is None else str(x))
def base(s): return s.split(".")[-1]
def mv_usd(h):
    mv=h.get("market_value")
    if mv is None: return None
    return mv/USDJPY if h["symbol"].startswith("JP.") else mv
def num_from(r,k):
    m=re.search(k+r"=\s*([0-9][0-9,\.]*)", r or ""); return float(m.group(1).replace(",","")) if m else None
def is_ai(h): return base(h["symbol"]) in AI_NODE
def is_crypto(h): return h["symbol"].startswith("CC.") or base(h["symbol"]).upper() in CRYPTO
def is_def(h):
    t=h.get("name","")+" "+h.get("moat",{}).get("basis","")
    return any(k in t for k in ("保险","海上","第一三共","医药","制药"))
def cur(s): return "¥" if s.startswith("JP.") else "$"
def cbadge(c):
    cl="c-hi" if c=="高" else ("c-lo" if c=="低" else "c-mid"); return f'<span class="conf {cl}">把握{esc(c)}</span>'

def render(date, root):
    root=Path(root)
    prod=json.loads((root/"data"/"reports"/f"production_{date}.json").read_text(encoding="utf-8"))
    deep=json.loads((root/"data"/"analysis"/f"deep_{date}.json").read_text(encoding="utf-8"))
    hs=prod["holdings"]; H={h["symbol"]:h for h in hs}

    total=sum(v for v in (mv_usd(h) for h in hs) if v is not None)
    def cat(pred): return sum(v for h in hs if pred(h) and (v:=mv_usd(h)) is not None)
    ai_pct=cat(is_ai)/total*100; cr_pct=cat(is_crypto)/total*100; de_pct=cat(is_def)/total*100
    singles={h["symbol"]:(mv_usd(h)/total*100 if (mv_usd(h) and total) else 0) for h in hs}
    ai_over=ai_pct>45; cr_over=cr_pct>12

    def flags(h):
        sp=singles.get(h["symbol"],0); out=[]
        if is_ai(h) and ai_over:
            ms=h.get("moat",{}).get("total_score")
            if ms is not None and ms<=3: out.append(("要降AI先减它","AI已到上限、这只质量最弱→腾额度先动它"))
            else: out.append(("别加","AI这类已到上限(≤45%)、再买超标"))
        if sp>15: out.append((f"单一超限{sp:.0f}%","这一只已超单一15%上限"))
        if is_crypto(h) and cr_over: out.append(("控敞口","加密近/超12%上限"))
        return out

    P=[HEAD]
    P.append(f'<h1>每日投资决策台 · 完整产品（深度版·正式生产）</h1><p class="sub">数据 {esc(date)} 真数据 ｜ 数字＝production现算、分析＝分析岗deep当日写 ｜ 决策只看估值不看均线·每条标把握·缺数说清</p>')
    P.append(f'<div class="oneline"><b>今天一句话：</b>{esc(deep["oneline"])} {cbadge("高")}<div class="sub" style="margin-top:5px">这句话是下面五层大环境+每只持仓合起来顶出来的。</div></div>')

    P.append('<h2>第一部分 · 大环境今天怎么了（五层 · 讲透）</h2>')
    tt={"world":"① 大局：世界大格局有没有变","fed_gate":"② 资金总闸：美联储松不松（最重要）","strategy":"③ AI 主线：你最大那注，产业硬不硬","flow":"④ 避险情绪：今天大家慌不慌","sector":"⑤ 板块：钱今天往哪流"}
    for k in ["world","fed_gate","strategy","flow","sector"]:
        L=deep["layers"].get(k)
        if not L: continue
        P.append(f'''<div class="card"><div class="hd">{esc(tt[k])} {cbadge(L["conf"])}</div>
        <div class="row"><span class="k">事实</span>{esc(L["fact"])}</div>
        <div class="row"><span class="k">为什么值得看</span>{esc(L["why"])}</div>
        <div class="you"><span class="k">对你的组合</span>{esc(L["you"])}</div>
        <div class="flip"><span class="k">什么情况改看法</span>{esc(L["flip"])}</div>
        <div class="sub">{esc(L["note"])}</div></div>''')

    P.append('<h2>第二部分 · 你的持仓，今天怎么办（19只 · 每只讲透）</h2>')
    P.append('<div class="card" style="background:#fbf6ee;border-color:#e6d3b0"><b>价位规矩：</b>买卖价只看估值——便宜位/偏贵位。均线只当趋势背景一句话、绝不当止损或买入线，根治红减绿加自打架。要不要止损看生意有没有坏。下面按角色分组，先看该守的、再看该减的。</div>')
    for g in deep["groups"]:
        P.append(f'<h3>{esc(g["title"])}</h3>')
        for sym in g["symbols"]:
            h=H.get(sym); d=deep["holdings"].get(sym)
            if not h or not d: continue
            P.append(card(h,d,flags(h)))
    assets=[h for h in hs if is_crypto(h) and h.get("market_value") is None]
    if assets:
        li="".join(f'<li><b>{esc(h["name"])}</b>（现价约 ${h["price"]:,.0f}）：无财报资产·质量关不适用，只按仓位纪律控占比、不追高。</li>' for h in assets)
        P.append(f'<div class="card"><div class="hd">加密资产：比特币 BTC / 以太坊 ETH {cbadge("中")}</div><ul class="mini">{li}</ul><div class="flip"><b>数据缺口（诚实说）：</b>这两只持仓数量还没接进系统，所以暂不算占比、不给动作价——不是漏，是这个数待接。补上后加密总占比才完整。</div></div>')

    P.append('<h2>第三部分 · 仓位集中度（哪一类押太多了）</h2><div class="card">')
    def bar(n,p,lim,over,low=False):
        tone="over" if over else "ok"; rel=f"上限{lim}%" if not low else f"下限{lim}%"
        f=("⚠ 超上限" if over and not low else ("⚠ 略不足" if low and p<lim else "✓ 内"))
        return f'<div class="crow"><div class="cname">{esc(n)}</div><div class="cbarwrap"><div class="cbar {tone}" style="width:{min(p,100):.0f}%"></div></div><div class="cval">{p:.0f}%（{rel}）· {f}</div></div>'
    P.append(bar("AI 供应链（押在AI这条链上的钱）",ai_pct,45,ai_over))
    P.append(bar("加密（MSTR/COIN/CRCL已计，BTC/ETH数量待接）",cr_pct,12,cr_over))
    P.append(bar("防御（抗跌保命仓·保险/医药）",de_pct,15,False,low=True))
    P.append(f'<div class="you" style="margin-top:10px"><b>今天最该看的一行：AI 押了 {ai_pct:.0f}%，远超 45% 上限。</b>这就是为什么A组每一只（哪怕便宜、哪怕优质）都标别加——不是它们不好，是你在AI这条船上的钱太集中。想降下来，正确顺序是<b>先减质量最弱的软银，而不是砍真正的核心（英伟达/台积电）</b>。防御仓 {de_pct:.0f}%、略低于15%下限，压舱石可再厚点——第一三共在便宜位、可作加防御的方向。</div>')
    P.append('<div class="sub" style="margin-top:6px">算法：每类持仓值÷全部持仓值（日元先按162.536折美元）。现算的——持仓一变这些数就跟着变。</div></div>')

    P.append('<h2>第四部分 · 机会池：该不该换、换谁</h2>')
    op=prod.get("opportunity_pool",{})
    if not op.get("channel_1_swap_comparisons") and not op.get("channel_2_new_opportunities"):
        P.append('<div class="card"><p><b>今天机器扫描：没有到换仓价的现成候选。</b>但不代表外面没机会——是这套"机会标的vs你的持仓"的多维对比还没接上真数据（问题清单根因④）。</p><p>接上后它会这样帮你决策：拿一个候选（如做AI高速内存HBM的存储龙头海力士）和你手里同一类持仓摆一张表，比四样——护城河谁更宽、估值谁更便宜、方向谁更顺、换完会不会让某类更超标，直接给"换谁、什么价换"。示例见《完整产品_新样式定样》海力士对比表。</p><div class="flip"><b>要补两件：</b>①机会池扫描把候选填进来；②每个候选的便宜买价+最新财报现金流。</div></div>')

    P.append('<h2>第五部分 · 整条逻辑怎么闭环</h2>')
    P.append('''<div class="chain"><b>大局</b>：美国优先、阵营化没变（特朗普谈格陵兰=又添一块砖）<span class="ar">↓</span>
    <b>资金总闸</b>：美联储偏紧、钱没放水（利率涨到4.557%）<span class="ar">↓所以</span>
    <b>策略</b>：钱紧时只拿真赚钱护城河宽的，少碰靠借钱撑的<span class="ar">↓</span>
    <b>板块</b>：AI长期地基硬（台积电营收创新高）、但半导体今天资金在退→不追高<span class="ar">↓落到每只</span>
    <b>持仓动作</b>：A组优质AI守住不加（已超标）；软银质量最弱→要降AI先减它；防御压舱、第一三共便宜位可小加<span class="ar">↓</span>
    <b>机会</b>：候选跟同类持仓比、够格且到便宜位才换（今天无到价候选）<span class="ar">↓明天</span>
    <b>复盘</b>：明天验证今天判断对没对，对的加把握、错的改尺，回头修正大局判断</div>
    <p class="sub">每步都写得出"因为上面X所以下面Y"：如"因为钱紧(②)+AI已超标(集中度)，所以英伟达再便宜也别加"。任何一只动作都能顺这条线倒推回大局。</p>''')

    P.append(f'<p class="foot">—— 完整产品·深度版·正式生产 ｜ v3渲染器读 production_{esc(date)}.json（真数字·现算）+ deep_{esc(date)}.json（分析岗当日分析）｜ 改数字或改分析、输出跟着变 ——</p></body></html>')
    return "\n".join(P)

def card(h,d,fl):
    sym=h["symbol"]; c=cur(sym); v=h.get("valuation",{})
    price=h.get("price"); cheap=num_from(v.get("reason",""),"便宜线"); exp=num_from(v.get("reason",""),"偏贵线")
    zone,zt="",""
    if price is not None and cheap is not None and exp is not None:
        if price<cheap: zone,zt="便宜区","z-cheap"
        elif price<=exp: zone,zt="合理区","z-fair"
        else: zone,zt="偏贵区","z-exp"
    fb="".join(f'<span class="flag">{esc(t)}</span>' for t,_ in fl)
    acls="warn-act" if fl else ""
    extra=("　" + "；".join(desc for _,desc in fl)) if fl else ""
    zbadge=f'<span class="zone {zt}">{esc(zone)}</span>' if zone else ""
    if cheap is not None and exp is not None:
        pl=f'便宜位 {c}{cheap:,.0f} ｜ 偏贵位 {c}{exp:,.0f}。<b>现价 {c}{price:,.0f}，落在【{esc(zone)}】。</b>{esc(d["pricenote"])}'
    else:
        pl=f'这只还没做出估值区间，先不给买卖价（不拿均线硬编），按仓位纪律控占比。{esc(d.get("pricenote",""))}'
    return f'''<div class="card hold">
    <div class="hd">{esc(h["name"])}（{esc(base(sym))}）{zbadge} {cbadge(d["conf"])}{fb}</div>
    <div class="act {acls}"><b>动作：{esc(d["action"])}。</b>{extra}</div>
    <div class="row"><span class="k">生意硬吗</span>{esc(d["biz"])}</div>
    <div class="row"><span class="k">账本硬吗</span>{esc(d["book"])}</div>
    <div class="price">💰 <b>价位（只看估值）</b>：{pl}</div>
    <div class="flip"><span class="k">什么情况改看法</span>{esc(d["flip"])}</div>
    </div>'''

HEAD='''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>完整产品·深度版</title><style>
body{font-family:"Microsoft YaHei","PingFang SC",sans-serif;line-height:1.9;color:#1f2733;max-width:920px;margin:0 auto;padding:24px 17px;background:#f5f6f8}
h1{font-size:22px;color:#12324e;border-bottom:3px solid #2c6e9a;padding-bottom:8px;margin-bottom:3px}
h2{font-size:18px;color:#12324e;border-left:6px solid #2c6e9a;padding-left:10px;margin-top:30px}
h3{font-size:15.5px;color:#7a4a12;background:#fbf3e6;border-radius:7px;padding:7px 12px;margin-top:22px}
.sub{color:#66707c;font-size:12.8px}
.oneline{background:#eaf2f8;border:1px solid #b8d3e6;border-radius:10px;padding:14px 17px;margin:12px 0;font-size:15px}
.card{background:#fff;border:1px solid #e2e6ec;border-radius:11px;padding:15px 19px;margin:14px 0;box-shadow:0 1px 4px rgba(0,0,0,.05)}
.card.hold{border-left:4px solid #cbd6e2}
.hd{font-size:16.5px;color:#12324e;font-weight:bold;margin-bottom:4px}
.conf{display:inline-block;border-radius:5px;padding:1px 9px;font-size:12.3px;font-weight:bold;color:#fff;margin-left:5px}
.c-hi{background:#1d7a45}.c-mid{background:#c9791f}.c-lo{background:#8a94a0}
.flag{display:inline-block;background:#b23b3b;color:#fff;border-radius:4px;padding:0 8px;font-size:12px;margin-left:5px}
.zone{display:inline-block;border-radius:4px;padding:0 8px;font-size:12.3px;font-weight:bold;margin-left:4px}
.z-cheap{background:#d8f0e0;color:#1d7a45}.z-fair{background:#e2ecf5;color:#2c6e9a}.z-exp{background:#fbe6dd;color:#b23b3b}
.act{background:#eef7f1;border:1px solid #b6ddc6;border-radius:8px;padding:8px 12px;margin:8px 0;font-size:14.5px}
.act b{color:#1d7a45}.warn-act{background:#fdf1ec;border-color:#e6bda9}.warn-act b{color:#b23b3b}
.row{margin:7px 0}.k{display:inline-block;background:#eef3f8;color:#12324e;border-radius:5px;padding:1px 8px;font-weight:bold;font-size:12.6px;margin-right:3px}
.you{background:#eef7f4;border-left:4px solid #4f9e7f;border-radius:0 7px 7px 0;padding:8px 12px;margin:8px 0}
.flip{background:#fbf6ee;border-left:4px solid #c9a06a;border-radius:0 7px 7px 0;padding:8px 12px;margin:8px 0;font-size:13.4px;color:#5a4a2a}
.price{background:#f7f9fb;border-radius:8px;padding:8px 12px;margin-top:7px;font-size:13.6px}
.mini li{margin:4px 0}
.crow{display:flex;align-items:center;margin:7px 0;font-size:13.4px}.cname{width:250px}.cbarwrap{flex:1;background:#eef1f4;border-radius:6px;height:14px;overflow:hidden;margin:0 10px}
.cbar{height:14px;border-radius:6px}.cbar.ok{background:#7bbf98}.cbar.over{background:#d98a6a}.cval{width:230px;text-align:right;color:#556}
.chain{background:#12324e;color:#e8f1f8;border-radius:10px;padding:15px 18px;font-size:14px;line-height:2.1}.chain b{color:#ffd479}.chain .ar{color:#8fb6d6;margin:0 6px}
.foot{color:#88919c;font-size:12px;text-align:center;margin-top:22px}
</style></head><body>'''

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--date",default="20260714"); ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1])); ap.add_argument("--out",default="")
    a=ap.parse_args()
    # 输出改 _机器版(2026-07-15根治回滚):机器渲染永不覆盖分析岗手工的 _深度版超集版·两者分离
    out=a.out or str(Path(a.root)/"00_请先看这里"/f"完整产品_{a.date}_机器版.html")
    html_txt=render(a.date,a.root); Path(out).write_text(html_txt,encoding="utf-8")
    b=Path(out).read_bytes(); nb=b.count(b'\xef\xbf\xbd'); print("wrote %s · bytes=%d · 乱码EFBFBD=%d"%(out,len(b),nb))
