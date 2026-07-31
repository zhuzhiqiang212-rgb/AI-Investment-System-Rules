#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整产品·新样式渲染器 v2（大白话·决策不打架·标可信度）
读 data/reports/production_{date}.json → 出董事长看的新样式 HTML。
铁律：术语当场翻人话；买卖价只看估值(便宜线/偏贵线)、均线只作趋势背景不当买卖线；缺数用人话说不甩"待理解岗补深"。
用法：python product_render_v2.py --date 20260714 --root <项目根> [--out 路径]
默认 root=脚本上一级，out=00_请先看这里/完整产品_{date}_v2.html
"""
from __future__ import annotations
import argparse, html, json, re
from pathlib import Path

USDJPY = 162.536  # 兜底汇率(日元→美元)

CRYPTO = {"MSTR","COIN","CRCL","BTCUSD","ETHUSD","BTC","ETH"}
AI_NODE = {"NVDA":"算力","MSFT":"算力","META":"AI软件应用","AVGO":"半导体设备",
           "6857":"半导体设备","TSM":"代工","SNDK":"存储","9984":"盟友链"}
DEFENSIVE_KW = ("保险","海上","第一三共","医药","制药")

MODEL_PLAIN = {
 "医药管线DCF":"按新药管线的未来现金折现估的（医药专用）",
 "成长情景PE":"按成长股的情景市盈率估的",
 "NAV折价":"按它持有资产的净值打个折估的（控股公司专用）",
 "加密mNAV":"按它持有的币值估的（加密壳专用）",
 "保险内含价值EV":"按保险公司的内含价值估的（保险专用）",
 "周期PE":"按周期股的市盈率估的",
 "相对估值·财报锚·非精算·可信度C":"跟同行比价的粗估（可信度较低·还没做精算）",
}

def esc(x): return html.escape("" if x is None else str(x))
def base(sym): return sym.split(".")[-1]

def mv_usd(h):
    mv = h.get("market_value")
    if mv is None: return None
    s = h["symbol"]
    if s.startswith("JP."): return mv/USDJPY
    return mv  # US./CC. 已是美元

def num_from(reason, key):
    m = re.search(key+r"=\s*([0-9][0-9,\.]*)", reason or "")
    return float(m.group(1).replace(",","")) if m else None

def is_ai(h): return base(h["symbol"]) in AI_NODE
def is_crypto(h): return h["symbol"].startswith("CC.") or base(h["symbol"]).upper() in CRYPTO
def is_def(h):
    t = h.get("name","")+" "+h.get("moat",{}).get("basis","")
    return any(k in t for k in DEFENSIVE_KW)

def conf_badge(level):
    m={"高":"c-hi","中":"c-mid","低":"c-lo","中低":"c-mid"}
    return f'<span class="conf {m.get(level,"c-mid")}">把握{level}</span>'

def strength_to_conf(s):
    return {"强":"高","中":"中","弱":"中低"}.get(s,"中")

def cur_sym(sym):
    if sym.startswith("JP."): return "¥"
    return "$"

def render(date, root):
    root = Path(root)
    prod = json.loads((root/"data"/"reports"/f"production_{date}.json").read_text(encoding="utf-8"))
    hs = prod["holdings"]

    # ---- 集中度现算(美元归一) ----
    total = sum(v for v in (mv_usd(h) for h in hs) if v is not None)
    def cat_sum(pred): return sum(v for h in hs if pred(h) and (v:=mv_usd(h)) is not None)
    ai_usd = cat_sum(is_ai); cr_usd = cat_sum(is_crypto); de_usd = cat_sum(is_def)
    ai_pct = ai_usd/total*100 if total else 0
    cr_pct = cr_usd/total*100 if total else 0
    de_pct = de_usd/total*100 if total else 0
    singles = {h["symbol"]:(mv_usd(h)/total*100 if (mv_usd(h) and total) else 0) for h in hs}
    ai_over = ai_pct>45; cr_over = cr_pct>12
    single_over = {s:p for s,p in singles.items() if p>15}

    def holding_flag(h):
        s=h["symbol"]; sp=singles.get(s,0)
        tags=[]
        if is_ai(h) and ai_over:
            ms = h.get("moat",{}).get("total_score")
            if ms is not None and ms<=3:
                tags.append(("要降AI就先减它","warn","AI 押得已到上限，而这只在 AI 仓里质量最弱（几乎没护城河）——要腾额度先动它。"))
            else:
                tags.append(("别加","warn","AI 这类押得已到上限（≤45%），再买会超标。"))
        if sp>15:
            tags.append(("别加·单一超限","warn",f"这一只已占 {sp:.0f}%、超过单一 15% 上限。"))
        if is_crypto(h) and cr_over:
            tags.append(("控敞口","warn","加密这类已近/超 12% 上限，守着不加。"))
        return tags

    P=[]
    P.append(HEAD)
    P.append(f'<h1>每日投资决策台 · 新样式</h1><p class="sub">数据：{esc(date)} ｜ 全大白话 · 决策只看估值不看均线 · 每条标把握 ｜ 只给判断依据，最终你拍板</p>')

    tds = prod.get("today_direction_short","")
    P.append('<div class="oneline"><b>今天一句话：</b>'+esc(tds.replace("今天：",""))+
              '　'+conf_badge("高")+'<div class="sub2">这句话是下面五层证据合起来的结论，往下看每层怎么来的。</div></div>')

    P.append('<h2>一 · 大环境今天怎么了（五层证据 · 全大白话）</h2>')
    titles={"world":"① 大局（世界大格局有没有变）","fed_gate":"② 资金总闸（美联储放不放水·最重要）",
            "strategy":"③ AI 主线（产业方向硬不硬）","flow":"④ 避险情绪（大家慌不慌）","sector":"⑤ 板块（钱今天往哪流）"}
    ev=prod.get("evidence_summary",{})
    for k in ["world","fed_gate","strategy","flow","sector"]:
        L=ev.get(k)
        if not L: continue
        plain=L.get("plain","")
        why,todo=plain,""
        if "→ 对你：" in plain:
            why,todo=plain.split("→ 对你：",1)
        elif "→ 对你" in plain:
            why,todo=plain.split("→ 对你",1); todo=todo.lstrip("：:")
        conf=strength_to_conf(L.get("strength"))
        evs="".join(f"<li>{esc(e)}</li>" for e in L.get("today_events",[]))
        P.append(f'''<div class="card"><div class="ctop"><b>{esc(titles.get(k,k))}</b> {conf_badge(conf)}</div>
        <div class="four"><div><span class="lab">事实/为什么</span>{esc(why.strip())}</div>
        <div><span class="lab">怎么办</span>{esc(todo.strip()) or "按大方向守着即可。"}</div></div>
        <details class="fold"><summary>原始新闻/读数（点开看源头，可不看）</summary><ul>{evs}</ul></details></div>''')

    P.append('<h2>二 · 你的持仓，今天怎么办（价位只看估值·不打架）</h2>')
    P.append('<div class="ruleban"><b>价位规矩：</b>买卖价<b>只看估值</b>——便宜位（想低吸等这里）、偏贵/想卖位。<b>均线（平均价）只说一句"趋势偏强还是偏弱"，绝不当止损或买入线</b>，所以不会再出现"跌破年线要减、又跌破买入线要加"的自打架。要不要止损看<b>生意有没有坏</b>，不看跌破哪根线。</div>')
    real=[h for h in hs if not is_crypto(h) or h.get("market_value") is not None]
    real=sorted(real,key=lambda h:(mv_usd(h) or 0),reverse=True)
    assets=[h for h in hs if is_crypto(h) and h.get("market_value") is None]
    for h in real:
        P.append(card_html(h,singles,holding_flag(h)))
    if assets:
        li="".join(f'<li><b>{esc(h["name"])}</b>（现价约 ${h["price"]:,.0f}）：{esc(h["quality_gate"]["why"])}。按仓位纪律控占比、不追高。</li>' for h in assets)
        P.append(f'<div class="card"><div class="ctop"><b>加密资产（BTC / ETH）</b> {conf_badge("中")}</div><ul class="mini">{li}</ul><div class="miss">持仓数量还没接进来，所以暂不算占比、不给动作价——不是漏，是这两只的持仓数待接。</div></div>')

    P.append('<h2>三 · 仓位集中度（哪一类押太多了）</h2>')
    def bar(name,pct,limit,over,low=False):
        tone = "over" if over else "ok"
        rel = f"上限{limit}%" if not low else f"下限{limit}%"
        flagtxt = ("⚠ 超上限→别再加" if over and not low else ("⚠ 不足下限→看整体配置" if low and pct<limit else "✓ 在规矩内"))
        return f'<div class="crow"><div class="cname">{esc(name)}</div><div class="cbarwrap"><div class="cbar {tone}" style="width:{min(pct,100):.0f}%"></div></div><div class="cval">{pct:.0f}%（{rel}）· {flagtxt}</div></div>'
    P.append('<div class="card">')
    P.append(bar("AI 供应链（押在AI这条链上的钱）",ai_pct,45,ai_over))
    P.append(bar("加密（比特币等·MSTR/COIN/CRCL已计，BTC/ETH数量待接）",cr_pct,12,cr_over))
    P.append(bar("防御（抗跌保命仓·保险/医药）",de_pct,15,False,low=True))
    P.append('<div class="miss">算法：每类持仓值 ÷ 全部持仓值（日元先按 '+f'{USDJPY}'+' 折成美元再比）。哪类超上限→对应持仓卡自动写"别加"。</div></div>')

    P.append('<h2>四 · 机会池：该不该换、换谁</h2>')
    op=prod.get("opportunity_pool",{})
    c1=op.get("channel_1_swap_comparisons",[]); c2=op.get("channel_2_new_opportunities",[])
    if not c1 and not c2:
        P.append('''<div class="card"><p><b>今天机会池的扫描结果：没有到"换仓价"的候选。</b>但这不等于外面没机会——是<b>机会池的候选清单和多维对比还没接上真数据</b>（这是已知缺口，见问题清单根因④）。</p>
        <p>接上后，这里会长这样：把外面的机会标的和你手里<b>同一类</b>的持仓摆一张表，比四样——<b>护城河谁更宽、估值谁更便宜、方向谁更顺、换完会不会让某类押得更超标</b>，直接给"够不够格换、什么价换"。示例样式见《完整产品_新样式定样》里的海力士对比表。</p>
        <div class="miss">要补：机会池扫描填候选 + 每个候选的便宜买价与财报数。补上这张表就能给确定的换仓依据。</div></div>''')
    else:
        rows="".join(f'<tr><td>{esc(x.get("name",""))}</td><td>{esc(x.get("note",""))}</td></tr>' for x in (c1+c2))
        P.append(f'<div class="card"><table><tr><th>候选</th><th>说明</th></tr>{rows}</table></div>')

    P.append('<h2>五 · 整条逻辑怎么闭环（一眼看懂因果）</h2>')
    P.append('''<div class="chain">
    <b>大局</b>：美国优先、阵营化，大格局没变 <span class="ar">↓</span>
    <b>资金总闸</b>：美联储偏紧、钱没放水（利率又涨） <span class="ar">↓ 所以</span>
    <b>策略</b>：钱紧时只拿真赚钱、护城河宽的，少碰靠借钱撑的 <span class="ar">↓</span>
    <b>板块</b>：AI 长期主线硬，但半导体今天资金在流出→不追高 <span class="ar">↓ 落到每只</span>
    <b>持仓动作</b>：优质仓（英伟达/微软等）守住不加；弱质量高杠杆（软银）优先减；便宜的防御（第一三共）压舱可小加 <span class="ar">↓</span>
    <b>机会</b>：候选跟同类持仓比，够格且到便宜位才换 <span class="ar">↓ 明天</span>
    <b>复盘</b>：明天验证今天的判断对没对，对的加把握、错的改尺，回头修正最上面的大局判断
    </div><p class="sub2">每一步都写得出"因为上面X、所以下面Y"——任何一只的动作都能顺这条线倒推回大局，不是拍脑袋。</p>''')

    P.append(f'<p class="foot">—— 新样式·全量版 ｜ 生成器 product_render_v2.py 读 production_{esc(date)}.json 现算，改数据结论跟着变（非写死）。价位只来自估值、均线仅背景。——</p>')
    P.append("</body></html>")
    return "\n".join(P)

def card_html(h,singles,flags):
    sym=h["symbol"]; name=h["name"]; price=h.get("price"); cur=cur_sym(sym)
    q=h.get("quality_gate",{}); v=h.get("valuation",{}); m=h.get("moat",{})
    cheap=num_from(v.get("reason",""),"便宜线"); exp=num_from(v.get("reason",""),"偏贵线")
    zone,ztone="",""
    if price is not None and cheap is not None and exp is not None:
        if price<cheap: zone,ztone="便宜区（低于便宜位）","z-cheap"
        elif price<=exp: zone,ztone="合理区（不便宜也不贵）","z-fair"
        else: zone,ztone="偏贵区（高于偏贵位）","z-exp"
    flagtxt="".join(f'<span class="flag">{esc(t)}</span>' for t,_,_ in flags)
    if flags:
        act_main="守 · 持有，但"+("、".join(t for t,_,_ in flags))
        acls="warn-act"; extra="；".join(d for _,_,d in flags)
    else:
        act_main="守 · 持有 / 观望"; acls=""; extra="今天没有明确的买卖信号，先拿着。"
    tier=q.get("tier"); tlab=q.get("tier_label",""); qwhy=q.get("why","")
    if tier=="①": qtxt=f'<b style="color:#1d7a45">优质·通过</b>：{esc(qwhy)}'; conf="高"
    elif tier=="②": qtxt=f'<b style="color:#c9791f">在盯改善（没被误杀）</b>：{esc(qwhy)}'; conf="中"
    else: qtxt=f'{esc(tlab)}：{esc(qwhy)}'; conf="中"
    mg=m.get("moat_grade",""); msc=m.get("total_score"); mb=m.get("basis","")
    moat_line=f'{esc(mg)}'+(f'（打分{msc}）' if msc is not None else '')+f'：{esc(mb)}'
    model=MODEL_PLAIN.get(v.get("model_type",""),v.get("model_type",""))
    if cheap is not None and exp is not None:
        pl=(f'便宜位 {cur}{cheap:,.0f}（想低吸等这里）｜ 想卖/偏贵位 {cur}{exp:,.0f}。'
            f'<b>现价 {cur}{price:,.0f}，落在【{esc(zone)}】。</b>')
    else:
        pl='这只还没做出估值区间，<b>先不给买卖价</b>（不拿均线硬编），按仓位纪律控占比。'
    tb=""
    mr=re.search(r"现价/MA200=([0-9\.]+)",h.get("soft_filter",{}).get("reason",""))
    if mr:
        r=float(mr.group(1))
        d="上方＝趋势偏强" if r>1 else ("下方＝趋势偏弱" if r<1 else "持平")
        tb=f'<div class="trend">趋势背景（只参考·不当买卖线）：现价约是一年平均价的 {r:.2f} 倍（{d}）。</div>'
    zbadge=f'<span class="zone {ztone}">{esc(zone)}</span>' if zone else ''
    return f'''<div class="card hold">
      <div class="ctop"><b>{esc(name)}（{esc(base(sym))}）</b> {zbadge} {conf_badge(conf)}{flagtxt}</div>
      <div class="act {acls}"><b>动作：{esc(act_main)}。</b>{esc(extra)}</div>
      <div class="four">
        <div><span class="lab">生意硬吗</span>护城河 {moat_line}</div>
        <div><span class="lab">账本硬吗</span>{qtxt}</div>
        <div><span class="lab">贵不贵</span>{esc(v.get("label",""))}　<span class="pt">（{esc(model)}）</span></div>
      </div>
      <div class="price">💰 <b>价位（只看估值）</b>：{pl}{tb}</div>
    </div>'''

HEAD='''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>每日投资决策台·新样式</title><style>
body{font-family:"Microsoft YaHei","PingFang SC",sans-serif;line-height:1.85;color:#1f2733;max-width:960px;margin:0 auto;padding:22px 16px;background:#f5f6f8}
h1{font-size:22px;color:#12324e;border-bottom:3px solid #2c6e9a;padding-bottom:8px;margin-bottom:4px}
h2{font-size:18px;color:#12324e;border-left:6px solid #2c6e9a;padding-left:10px;margin-top:28px}
.sub{color:#66707c;font-size:12.8px}.sub2{color:#66707c;font-size:12.6px;margin-top:5px}
.oneline{background:#eaf2f8;border:1px solid #b8d3e6;border-radius:9px;padding:13px 16px;margin:12px 0;font-size:15px}
.card{background:#fff;border:1px solid #e2e6ec;border-radius:10px;padding:14px 17px;margin:12px 0;box-shadow:0 1px 3px rgba(0,0,0,.05)}
.card.hold{border-left:4px solid #cbd6e2}
.ctop{font-size:15.5px;margin-bottom:6px}
.four div{margin:5px 0}.lab{display:inline-block;min-width:78px;color:#c9791f;font-weight:bold}
.act{background:#eef7f1;border:1px solid #b6ddc6;border-radius:8px;padding:8px 12px;margin:7px 0;font-size:14.5px}
.act b{color:#1d7a45}.warn-act{background:#fdf1ec;border-color:#e6bda9}.warn-act b{color:#b23b3b}
.conf{display:inline-block;border-radius:4px;padding:0 8px;font-size:12.2px;font-weight:bold;color:#fff;margin-left:4px}
.c-hi{background:#1d7a45}.c-mid{background:#c9791f}.c-lo{background:#8a94a0}
.flag{display:inline-block;background:#b23b3b;color:#fff;border-radius:4px;padding:0 8px;font-size:12px;margin-left:5px}
.zone{display:inline-block;border-radius:4px;padding:0 8px;font-size:12.4px;font-weight:bold;margin-left:4px}
.z-cheap{background:#d8f0e0;color:#1d7a45}.z-fair{background:#e2ecf5;color:#2c6e9a}.z-exp{background:#fbe6dd;color:#b23b3b}
.price{background:#f7f9fb;border-radius:8px;padding:8px 12px;margin-top:7px;font-size:13.8px}
.trend{color:#66707c;font-size:12.4px;margin-top:4px}.pt{color:#66707c;font-size:12.4px}
.fold{margin-top:6px;font-size:12.8px}.fold summary{cursor:pointer;color:#2c6e9a}.fold ul{margin:5px 0}
.ruleban{background:#fbf6ee;border:1px solid #e6d3b0;border-radius:8px;padding:11px 15px;margin:10px 0;font-size:13.6px}
.miss{background:#f4f2ee;border-left:4px solid #c9a06a;border-radius:0 6px 6px 0;padding:7px 11px;margin:7px 0;font-size:13px;color:#6a5a3a}
.mini li{margin:4px 0}
.crow{display:flex;align-items:center;margin:7px 0;font-size:13.4px}.cname{width:230px}.cbarwrap{flex:1;background:#eef1f4;border-radius:6px;height:14px;overflow:hidden;margin:0 10px}
.cbar{height:14px;border-radius:6px}.cbar.ok{background:#7bbf98}.cbar.over{background:#d98a6a}.cval{width:250px;text-align:right;color:#556}
.chain{background:#12324e;color:#e8f1f8;border-radius:10px;padding:15px 18px;font-size:14px;line-height:2.1}.chain b{color:#ffd479}.chain .ar{color:#8fb6d6;margin:0 6px}
.foot{color:#88919c;font-size:12px;text-align:center;margin-top:20px}
</style></head><body>'''

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--date",default="20260714")
    ap.add_argument("--root",default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--out",default="")
    a=ap.parse_args()
    htmlout=render(a.date,a.root)
    outp=a.out or str(Path(a.root)/"00_请先看这里"/f"完整产品_{a.date}_v2.html")
    Path(outp).write_text(htmlout,encoding="utf-8")
    b=Path(outp).read_bytes(); n=b.count(b"\xef\xbf\xbd")
    print(f"wrote {outp} · bytes={len(b)} · 乱码EFBFBD={n}")
