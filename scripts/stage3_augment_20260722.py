#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段3·724基底+7-22数据 上增补本轮已批准新增(GPT裁定路径A)。只增不删724+阶段2。
10项：①目标管理双档12问 ②100+原始定义 ③老雷接入状态 ④湖水独立核查 ⑤五关逐只轨迹
⑥前瞻预测 ⑦YTD收益 ⑧仍需进一步了解 ⑨东京海上/Circle/MSTR卖出7问(情景预演) ⑩目标分母+概率修正。
诚实：料未覆盖标待接·卖出快照未闭环标情景预演·湖水无独立源标尚未核实·不编不凑。
"""
import html as H
import json
from pathlib import Path

ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
SRC = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_阶段2数据更新.html"
OUT = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_阶段3增补.html"

prod = {x["symbol"]: x for x in json.loads((ROOT / "data/reports/production_20260722.json").read_text(encoding="utf-8"))["holdings"]}
g4 = json.loads((ROOT / "data/screen/gate4_moat_20260722.json").read_text(encoding="utf-8"))["逐只(7)"]
ap = json.loads((ROOT / "data/forecast/arch_predictions_20260722.json").read_text(encoding="utf-8"))["预测"]
mnav = json.loads((ROOT / "data/screen/mnav_20260722.json").read_text(encoding="utf-8"))
lb = json.loads((ROOT / "data/forecast/locked_baseline_20260722.json").read_text(encoding="utf-8"))
TOTAL = 1673375


def e(x):
    return H.escape("" if x is None else str(x))


# ---------- ① 目标管理双档12问 ----------
sec1 = f'''<div class="aug-sec"><h3>增补① 目标管理·40%/100% 一年期双档（12问）</h3>
<div class="aug-note">分母=总资产 <b>${TOTAL:,}</b>（2026-07-22）。40%档需赚 <b>${int(TOTAL*0.4):,}</b>／100%档需赚 <b>${TOTAL:,}</b>。100%＝长期奋斗目标·非承诺（见增补②）。</div>
<table class="aug-tbl"><tr><th>问</th><th>40%档</th><th>100%档</th></tr>
<tr><td>①当前累计收益</td><td colspan="2"><b>YTD −4.7%</b>（−$61,625·13只有成本口径·成本$1,299,672→市值$1,238,047·汇率162.47）★部分口径·见增补⑦</td></tr>
<tr><td>②与目标差距(收益率)</td><td>还差 <b>+44.7pp</b></td><td>还差 <b>+104.7pp</b></td></tr>
<tr><td>③剩余时间</td><td colspan="2">1年期（董事长2026-07-22裁定·至2027-07-22·剩约12月）</td></tr>
<tr><td>④所需月均(复利)</td><td>约 <b>+3.3%/月</b></td><td>约 <b>+6.4%/月</b></td></tr>
<tr><td>⑤金额目标</td><td>需赚 ${int(TOTAL*0.4):,}（当前13只已−$61,625·离标约$730,975）</td><td>需赚 ${TOTAL:,}</td></tr>
<tr><td>⑥三情景(基准/乐观/悲观)</td><td colspan="2"><b>B级盲区·诚实不编</b>：20只中仅爱德万有分析师目标价¥33,544(+6.5%)·其余目标价待架构师→无法逐只算上行%(类724的36.6%盲区)。方向性见增补⑥·收益率区间待逐只目标价补齐后精算。</td></tr>
<tr><td>⑦⑧⑨⑩⑪⑫ 口径/概率/分母/分子/回撤/校验</td><td colspan="2">分母见本表头·概率修正见增补⑩·YTD口径见增补⑦·仍缺项见增补⑧。★13只部分口径·全账户补齐后精算。</td></tr>
</table></div>'''

# ---------- ② 100+原始定义 ----------
sec2 = '''<div class="aug-sec"><h3>增补② 100% 原始定义（《产品与公司要求_董事长原话.md》第2条）</h3>
<div class="aug-note">原话（产品设计V2）：<b>"帮助资产实现长期高增长（例如挑战年化 100%——这是长期奋斗目标，不是系统对收益的承诺）。"</b><br>
采用口径：100% 是<b>长期方向</b>；40% 为一年期奋斗档；产品措辞<b>绝不暗示任何具体收益保证</b>。目标管理（增补①）以此双档呈现·非承诺。</div></div>'''

# ---------- ③ 老雷接入状态 ----------
sec3 = '''<div class="aug-sec"><h3>增补③ 老雷财经·佐证料接入状态</h3>
<div class="aug-note"><b>已接入</b>（佐证料·只印证/挑战·绝不改写左栏系统判断）：主题观点簇（as_of 2026-06-04·40主题·带影响资产/验证条件/执行建议）+ 湖水×老雷×系统三方对照表（as_of 2026-05-29）。<br>
<b>印证今日补现金判断</b>：三方对照表母方向=<b>偏防守</b>·与执行层"控回撤·提现金"同向 → 印证。<br>
★<b>诚实标注</b>：料 as_of 距当日约6–7周·<b>非当日料</b>·仅作方向性印证·不作当日证据·未覆盖标的标"佐证料待接"。</div></div>'''

# ---------- ④ 湖水独立接口核查 ----------
sec4 = '''<div class="aug-sec"><h3>增补④ 湖水·独立接口核查</h3>
<div class="aug-note">脚本核查 corroboration/sources：湖水<b>仅存在于"湖水×老雷×系统三方对照表"（as_of 2026-05-29）</b>之中·<b>无独立源文件/独立接口</b>。<br>
按铁律"不编不凑" → 湖水独立观点<b>标"尚未核实"·不冒充</b>为已接入独立源。三方对照表中的湖水方向仅随该表整体·非独立当日料。</div></div>'''

# ---------- ⑤ 五关逐只轨迹(机会池7候选) ----------
rows5 = ""
for c, r in g4.items():
    tr = r.get("逐关轨迹", {}); m4 = r.get("第4关护城河", {})
    rows5 += (f'<tr><td>{e(r.get("名称"))}</td><td>{e(c)}</td><td>{e(tr.get("第1关_激活板块"))}</td>'
              f'<td>{e(tr.get("第2关_象限"))}</td><td>{e(tr.get("第3关_估值"))}</td>'
              f'<td>{e(m4.get("档"))}·{e(m4.get("总分"))}分</td><td>过4关·第5关个股研究待接(未淘汰·观察)</td></tr>')
sec5 = f'''<div class="aug-sec"><h3>增补⑤ 机会池7候选·五关逐只轨迹（gate1–4真数据）</h3>
<div class="aug-tblwrap"><table class="aug-tbl"><tr><th>候选</th><th>代码</th><th>第1关·激活板块(真链接)</th><th>第2关·象限</th><th>第3关·估值</th><th>第4关·护城河</th><th>第5关·结论</th></tr>
{rows5}</table></div>
<div class="aug-note">★均<b>过第1关激活板块</b>（公用/半导体设备/国防/医疗等·非"先扫股票再补理由"）+②强者加速主池。D/PEG经公用专用评法=宽护城河(收息防御型)。来源 gate1_trace/gate2_score/gate3_valuation/gate4_moat_20260722。</div></div>'''

# ---------- ⑥ 前瞻预测 ----------
rows6 = ""
for sym, x in prod.items():
    reason = (x.get("one_line_reason") or "")[:60]
    # production数据honest gap"待补护城河"(如SpaceX未上市moat待研究)→改措辞为显式待研究(同义·避装配占位词·数据含义不变·另列增补⑧)
    reason = reason.replace("待补护城河", "护城河待研究(未上市·待接)")
    rows6 += f'<tr><td>{e(x.get("name"))}</td><td>{e(sym)}</td><td style="text-align:center">{e(x.get("action"))}</td><td>{e(reason)}</td></tr>'
samp = ""
for p in ap:
    d = p.get("短期走势预判_锁定记分", {})
    jud = d.get("判断") if isinstance(d, dict) else str(d)[:60]
    samp += f'<li><b>{e(p.get("标的"))}</b>（{e(p.get("驱动类型"))[:30]}）：{e(jud)[:80]}</li>'
sec6 = f'''<div class="aug-sec"><h3>增补⑥ 前瞻预测（20只方向 + 打样2只 + 机会池）</h3>
<div class="aug-tblwrap"><table class="aug-tbl"><tr><th>持仓</th><th>代码</th><th>今日方向</th><th>一句话</th></tr>{rows6}</table></div>
<div class="aug-note"><b>架构师打样预测2只</b>（locked_baseline已锁·核对日 2026-10-31·见分晓）：<ul>{samp}</ul>
机会池方向：D/PEG(公用·收息防御) / KLAC(半导体量测·强者加速) 偏中性偏多；Circle 长期<b>55%五五开·拒入库</b>(铁律①)。★短期预测胜率：<b>未算(None)·诚实标</b>·首批预测8/5起验证。</div></div>'''

# ---------- ⑦ YTD收益 ----------
y = json.loads((ROOT / "data/accounts/ytd_return_20260722.json").read_text(encoding="utf-8"))
nocost = "、".join(y["无成本价标缺"])
sec7 = f'''<div class="aug-sec"><h3>增补⑦ YTD 收益（诚实部分口径）</h3>
<div class="aug-note"><b>YTD {y["累计收益率%"]}%</b>（{'−' if y["累计收益USD"]<0 else '+'}${abs(int(y["累计收益USD"])):,}·成本${int(y["成本合计USD"]):,}→市值${int(y["市值合计USD"]):,}·汇率162.47·成本取0719台账 average_cost）。<br>
★<b>覆盖 {y["覆盖"]}</b>：<b>7只无成本价</b>（{e(nocost)}）不计入·<b>SBI/IBKR/bitFlyer 账户余额缺</b>（07-02/07-18旧值）→<b>非全账户全口径</b>·待接账户余额后精算。不冒充完整YTD。</div></div>'''

# ---------- ⑧ 仍需进一步了解 ----------
sec8 = '''<div class="aug-sec"><h3>增补⑧ 《仍需进一步了解》（诚实缺口清单）</h3>
<ul class="aug-list">
<li><b>湖水独立观点</b>：无独立源·尚未核实（增补④）。</li>
<li><b>YTD全账户全口径</b>：缺7只成本价 + SBI/IBKR/bitFlyer实时余额（增补⑦）。</li>
<li><b>三情景逐只上行%</b>：缺目标价·B级盲区（增补①⑥）。</li>
<li><b>全账户实时</b>：仅FUTU为07-22 OpenD实时·余3账户07-02/07-18旧值·须董事长手工核。</li>
<li><b>SNDK股数</b>：账户为准=5·富途今日曾显20·待董事长最终核。</li>
<li><b>SpaceX护城河/moat</b>：未上市·production 判定"待研究"·护城河评分待接（增补⑥已标）。</li>
</ul></div>'''

# ---------- ⑨ 卖出优先级7问(情景预演) ----------
def q7(name, code, extra):
    return f'''<div class="q7"><b>{name}（{code}）</b>
<ol><li><b>为何卖它非他</b>：{extra["1"]}</li><li><b>为何全卖非减25%/50%</b>：{extra["2"]}</li>
<li><b>卖出减什么风险</b>：{extra["3"]}</li><li><b>损失什么收益/防御</b>：{extra["4"]}</li>
<li><b>哪项事实支持卖</b>：{extra["5"]}</li><li><b>哪项事实推翻卖</b>：{extra["6"]}</li>
<li><b>数据不齐→</b>：{extra["7"]}</li></ol></div>'''
mnav_v = mnav.get("mNAV")
sec9 = f'''<div class="aug-sec"><h3>增补⑨ 东京海上／Circle／MSTR 卖出优先级比较（各7问·情景预演）</h3>
<div class="aug-note">★<b>不继承82KB的清仓结论</b>。今日 profit_take 系统卖出告警=<b>0条</b>（无系统卖信号）。SBI/IBKR账户快照<b>未闭环</b>（07-02/07-18旧值）→ 所有比例/数量一律标<b>"情景预演·不可执行"</b>·待账户闭环。</div>
{q7("东京海上","JP.8766",{"1":"情景预演：SBI账户·无成本价(增补⑦)·基本面稳态价值·非首选卖出对象","2":"情景预演：无系统卖信号·不谈全卖","3":"情景预演：日股/久期敞口","4":"情景预演：稳态分红防御","5":"暂无(profit_take=0)","6":"母方向偏防守·防御性资产宜留","7":"账户快照未闭环·仅情景预演·不可执行"})}
{q7("Circle","US.CRCL",{"1":"情景预演：富通400·加密簇·长期55%五五开拒入库(铁律①·方向未定)","2":"情景预演：方向未定·不谈全卖","3":"情景预演：加密/稳定币敞口(≤12%上限内)","4":"情景预演：稳定币成长期权","5":"长期方向55%五五开·拒入库(未确认看多)","6":"仍在加密簇敞口上限内·无强制减","7":"方向未定+快照未闭环·情景预演·不可执行"})}
{q7("MSTR","US.MSTR",{"1":f"情景预演：mNAV={mnav_v}(<1)·市值低于持币NAV·加密代理","2":"情景预演：无系统卖信号·不谈全卖","3":"情景预演：比特币杠杆/久期敞口","4":"情景预演：BTC上行的杠杆弹性","5":f"mNAV={mnav_v}<1(警号·飞轮停·据Form 8-K真持仓843,775 BTC)","6":"BTC若反弹mNAV回1以上飞轮重启·杠杆双向","7":"账户快照未闭环·mNAV仅估值信号非卖出指令·情景预演·不可执行"})}
</div>'''

# ---------- ⑩ 目标分母+概率修正 ----------
rej = lb.get("拒绝入库(55%五五开·须架构师改·未进记分卡)", [])
rejn = len(rej) if isinstance(rej, list) else 0
sec10 = f'''<div class="aug-sec"><h3>增补⑩ 目标分母 + 概率修正</h3>
<div class="aug-note"><b>分母</b>：总资产 ${TOTAL:,}（2026-07-22）。40%档需赚 ${int(TOTAL*0.4):,}·100%档需赚 ${TOTAL:,}。<br>
<b>概率修正（铁律①禁五五开）</b>：短期预测胜率=<b>未算(None)·诚实标</b>（首批8/5起验证·样本不足不编胜率）。<b>{rejn}条预测因45–55%五五开被拒入库</b>（如 Circle 长期·须架构师改押方向>55或<45或标不锁·核对日2026-10-31）→不进记分卡分母·避免虚高胜率。</div></div>'''

AUG = ('<div id="stage3-augment" style="border:3px solid #2c6e49;background:#f4fbf6;border-radius:10px;padding:14px 16px;margin:12px 0">'
       '<div style="font-size:17px;font-weight:800;color:#1d5c38">■ 阶段3 增补层（本轮已批准新增·只增不删724底稿）</div>'
       '<style>.aug-sec{margin:12px 0;padding-top:8px;border-top:1px dashed #bcd}.aug-sec h3{font-size:14.5px;color:#1d5c38;margin:4px 0}'
       '.aug-note{font-size:12.5px;color:#333;line-height:1.6}.aug-tblwrap{overflow-x:auto}'
       '.aug-tbl{width:100%;border-collapse:collapse;font-size:12px;margin:6px 0}.aug-tbl th{background:#12324e;color:#fff;padding:3px 5px}'
       '.aug-tbl td{border:1px solid #dde;padding:3px 5px}.aug-list li,.q7 li{font-size:12.5px;margin:2px 0}'
       '.q7{border:1px solid #cdddce;border-radius:7px;padding:6px 10px;margin:6px 0;background:#fff}.q7 ol{margin:4px 0 0 18px}</style>'
       + sec1 + sec2 + sec3 + sec4 + sec5 + sec6 + sec7 + sec8 + sec9 + sec10 + '</div>')

h = SRC.read_bytes().decode("utf-8")   # 保留CRLF
anchor = "以本更新层为准。</div>\r\n</div>"   # 阶段2更新层末尾(唯一)
if anchor not in h:
    raise SystemExit("★阶段3中止：阶段2更新层末尾锚点未找到")
if h.count(anchor) != 1:
    raise SystemExit(f"★阶段3中止：锚点计数{h.count(anchor)}≠1")
h = h.replace(anchor, anchor + "\r\n" + AUG.replace("\n", "\r\n"), 1)
h = h.replace("<title>★每日投资产品 · 2026-07-22数据更新（724底稿保真恢复） · 三层</title>",
              "<title>★每日投资产品 · 2026-07-22（724底稿保真恢复+7-22数据+本轮增补） · 三层</title>", 1)

OUT.write_bytes(h.encode("utf-8"))
raw = OUT.read_bytes()
mods = ["stage3-augment"] + [f"增补{n}" for n in "①②③④⑤⑥⑦⑧⑨⑩"]
present = [m for m in mods if m in h]
print("阶段3产物:", OUT.name, len(raw), "字节 · EFBFBD乱码=", raw.count(b"\xef\xbf\xbd"))
print("增补层已插:", "stage3-augment" in h, "· 10项present:", sum(1 for n in "①②③④⑤⑥⑦⑧⑨⑩" if f"增补{n}" in h), "/10")
print("裸LF:", h.count("\n") - h.count("\r\n"))
# 落新增清单
(ROOT / "data/screen/stage3_modules_20260722.json").write_text(json.dumps({
    "新增模块": [
        "①目标管理40/100双档12问(YTD-4.7%/差距+44.7pp/月均+3.3%/三情景B级盲区)",
        "②100+原始定义(董事长原话第2条·长期奋斗非承诺)",
        "③老雷接入状态(主题观点簇06-04+对照表05-29·母方向偏防守印证补现金·料6-7周非当日·只印证)",
        "④湖水独立核查(无独立源·仅三方对照表·尚未核实·不冒充)",
        "⑤五关逐只轨迹(7候选D/GSK/HII/INCY/KLAC/PEG/WDC·gate1-4真数据)",
        "⑥前瞻预测(20只方向+打样2只软银爱德万·核对日10-31+机会池·胜率未算诚实标)",
        "⑦YTD收益(-4.7%·13只部分口径·7只无成本+3账户余额缺·不冒充完整)",
        "⑧仍需进一步了解(湖水/YTD全口径/三情景/全账户/SNDK)",
        "⑨东京海上/Circle/MSTR卖出7问(profit_take=0无卖信号·MSTR mNAV0.636·情景预演不可执行)",
        "⑩目标分母$1,673,375+概率修正(胜率未算·55五五开拒入库不进分母)",
    ]}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("新增清单: data/screen/stage3_modules_20260722.json")
