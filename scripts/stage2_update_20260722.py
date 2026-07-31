#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段2·724基底(保真件)上更新7-22数据(GPT裁定路径A)。只改数据/加更新层·不删724内容。

in-place结构化更新(锚定+计数断言，任一计数不符即抛错停止)：
  ①20只 pxnow现价 → production_20260722(OpenD·22:47JST官方生产管线)
  ②价格日元数据 生产日07-19→07-22 / 价格对应07-17→07-22 / 来源尾诚实标注
  ③全局价格声明 07-17 → 07-22
  ④SNDK持仓头 20股(富通20) → 5股(富通5)  (07-22账户为准·富途今日曾显20待核)
加更新层(只增不删·插入<body>首)：权威07-22持仓表+账户现金(仅FUTU实时·余标旧值来源·铁律3)+3快照留痕+负现金/融资利息标C无数据+预测验证日。
★不做288处正文散价的盲替(风险)：底稿三层保留为07-17价基线分析·顶部更新层为07-22权威·加银禅明。
"""
import html as H
import json
import re
from pathlib import Path

ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
SRC = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_保真测试件.html"   # 724保真件(=724逐字节)
OUT = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_阶段2数据更新.html"

prod = {x["symbol"]: x for x in json.loads((ROOT / "data/reports/production_20260722.json").read_text(encoding="utf-8"))["holdings"]}
# 724已有账户拆分(勘察确认·非待接)
SPLIT = {
    "JP.4568": "富通6500＋SBI3400", "US.NVDA": "富通830＋IBKR190", "US.MSFT": "富通550＋IBKR140",
    "US.MSTR": "富通700＋IBKR158", "US.COIN": "富通200＋IBKR45", "JP.9984": "富通4100＋SBI2800",
    "JP.8766": "SBI1000", "JP.6758": "SBI1000", "JP.6857": "SBI800", "JP.7203": "SBI800",
    "JP.8001": "SBI900", "JP.7832": "富通500", "JP.7974": "富通2000", "US.AVGO": "富通150",
    "US.CRCL": "富通400", "US.SNDK": "富通5", "US.TSM": "富通1", "US.META": "IBKR95",
    "US.IBKR": "IBKR14", "US.SPCX": "富途10",
}
ORDER = ["JP.4568", "US.NVDA", "US.MSFT", "US.MSTR", "US.COIN", "JP.9984", "JP.8766", "JP.6758",
         "JP.6857", "JP.7203", "JP.8001", "JP.7832", "JP.7974", "US.AVGO", "US.CRCL", "US.SNDK",
         "US.TSM", "US.META", "US.IBKR", "US.SPCX"]


def fmt_px(sym, p):
    return (f"¥{p:,.2f}" if sym.startswith("JP.") else f"${p:,.2f}")


def must(cond, msg):
    if not cond:
        raise SystemExit(f"★阶段2中止(计数/锚点不符)：{msg}")


h = SRC.read_bytes().decode("utf-8")   # 字节级读取·保留724的CRLF换行(不静默转LF)·差异只发生在更新处
changes = []          # 逐项变更留痕
abc = {"A": [], "B": [], "C": []}

# ---------- ① 20只 pxnow现价(锚定symbol·各1处) ----------
for sym in ORDER:
    p = prod[sym]
    newpx = fmt_px(sym, p["price"])
    pat = re.compile(r"(" + re.escape(sym) + r"</span></td>\s*<td data-l=\"现价\"><b class=\"pxnow\">)([^<]+)(</b>)")
    m = pat.search(h)
    must(m, f"{sym} pxnow锚点未找到")
    old = m.group(2)
    h2, n = pat.subn(lambda mm: mm.group(1) + newpx + mm.group(3), h, count=1)
    must(n == 1, f"{sym} pxnow替换数={n}≠1")
    h = h2
    changed = (old != newpx)
    changes.append({"项": f"现价 {sym}", "旧": old, "新": newpx, "类": "B", "变": changed})
    abc["B"].append(f"现价 {sym}: {old}→{newpx}")

# ---------- ② 价格日元数据 ----------
r1 = "产品生产日 2026-07-19（周日）·非交易日"
n1 = h.count(r1); must(n1 == 20, f"生产日模板计数{n1}≠20")
h = h.replace(r1, "产品生产日 2026-07-22（周三）·价格更新日")
changes.append({"项": "价格元数据·生产日", "旧": r1, "新": "…07-22（周三）·价格更新日", "计数": n1, "类": "B"})

for old_dl in ["价格对应交易日 <b>2026-07-17（周五）盘后</b>", "价格对应交易日 <b>2026-07-17（周五）收盘</b>"]:
    nc = h.count(old_dl)
    h = h.replace(old_dl, "价格对应 <b>2026-07-22·OpenD快照</b>")
    changes.append({"项": "价格元数据·对应交易日", "旧": old_dl, "新": "价格对应 2026-07-22·OpenD快照", "计数": nc, "类": "B"})
must((h.count("2026-07-17（周五）盘后") + h.count("2026-07-17（周五）收盘")) == 0, "仍残留07-17价格对应交易日标签")

r_tail = "来源 OpenD·最近交易日收盘价（非盘中实时）｜是否超时限:否（<b>非实时·最近交易日收盘</b>）"
nt = h.count(r_tail); must(nt == 20, f"来源尾模板计数{nt}≠20")
h = h.replace(r_tail, "来源 production run 22:47JST(OpenD)｜JP=07-22收盘·US=盘中/最近成交(非确定收盘)｜同日另有08:40·21:49快照·差异见顶部更新层")
changes.append({"项": "价格元数据·来源尾", "旧": r_tail[:24] + "…", "新": "…production run·三快照留痕", "计数": nt, "类": "B"})

# ---------- ③ 全局价格声明 ----------
r_glob = "全部现价＝最近交易日 07-17（周五）收盘/盘后"
ng = h.count(r_glob); must(ng == 1, f"全局价格声明计数{ng}≠1")
h = h.replace(r_glob, "全部现价＝2026-07-22 OpenD快照（JP收盘/US盘中·22:47JST·production run）｜同日另有08:40·21:49快照差异见更新层")
changes.append({"项": "全局价格声明", "旧": r_glob, "新": "…2026-07-22 OpenD快照·三快照留痕", "计数": 1, "类": "B"})

# ---------- ④ SNDK持仓头 20→5 ----------
r_sndk = "20股（富通20）"
ns = h.count(r_sndk); must(ns == 1, f"SNDK头计数{ns}≠1")
h = h.replace(r_sndk, "5股（富通5）")
changes.append({"项": "SNDK持仓头股数", "旧": "20股（富通20）", "新": "5股（富通5）", "计数": 1, "类": "B",
                "注": "07-22账户为准=5·富途今日曾显20待董事长核·原20留痕于更新层"})
abc["B"].append("SNDK股数: 20→5(账户为准·富途今日曾显20待核)")

# 股数A(未变·19只)
for sym in ORDER:
    if sym == "US.SNDK":
        continue
    abc["A"].append(f"股数+账户拆分 {sym}: {int(prod[sym]['quantity'])}股（{SPLIT[sym]}）不变")

# ---------- C: 724确实没有 ----------
abc["C"] = [
    "我方账户·负现金/融资利息: 724无·07-22无数据源(富途保证金账户负现金待董事长核)·标C不编",
    "SBI/IBKR/bitFlyer 07-22实时现金: OpenD拉不到·仅07-02/07-18旧值·标日期来源·不称实时",
    "BTC/ETH 数量: 未接进系统·待董事长手工",
]

# ---------- 加更新层(只增不删) ----------
FX = 162.468102
cash_rows = [
    ("FUTU(富途)", "✅ OpenD实时·2026-07-22今日", "$41,103.99", "全账户覆盖_20260722·OpenD", True),
    ("SBI(个人/公司)", "❌ 非今日·2026-07-02核报", "¥19,520,910", "portfolio_snapshot·07-02核报", False),
    ("IBKR", "❌ 非今日·2026-07-02核报", "$4,508", "portfolio_snapshot·07-02核报", False),
    ("bitFlyer", "❌ 非今日·2026-07-02核报", "¥295,363", "portfolio_snapshot·07-02核报", False),
    ("负现金/融资利息", "C·724无·无07-22数据", "—", "待董事长核富途保证金", False),
    ("BTC/ETH", "⚠ 数量待接", "—", "未接进系统", False),
]
hold_rows = ""
for sym in ORDER:
    p = prod[sym]
    hold_rows += (f'<tr><td>{H.escape(p["name"])}</td><td>{sym}</td><td>{SPLIT[sym]}</td>'
                  f'<td style="text-align:right">{int(p["quantity"])}</td>'
                  f'<td style="text-align:right">{fmt_px(sym, p["price"])}</td>'
                  f'<td style="text-align:right">{p["market_value"]:,.0f}</td>'
                  f'<td style="text-align:center">{H.escape(p.get("action") or "")}</td></tr>')
cash_html = ""
for acct, st, amt, src, live in cash_rows:
    bg = "#0f2e1c" if live else "#3a1414"
    fg = "#bfe9cf" if live else "#ffb3b3"
    cash_html += f'<tr style="background:{bg};color:{fg}"><td>{acct}</td><td>{st}</td><td style="text-align:right">{amt}</td><td>{src}</td></tr>'

LAYER = f'''<div id="update-0722" style="border:3px solid #b8860b;background:#fffdf5;border-radius:10px;padding:14px 16px;margin:12px 0">
<div style="font-size:17px;font-weight:800;color:#7a5c00">■ 07-22 实时数据更新层（724底稿之上·只增不删）</div>
<div style="font-size:12.5px;color:#555;margin:4px 0 10px">价源=production run 2026-07-22 22:47JST（OpenD·官方生产管线）。<b>铁律3诚实标注</b>：仅 FUTU 为07-22 OpenD实时；SBI/IBKR/bitFlyer 现金为07-02核报（非今日·不称"同一快照真值"）。★同日另有08:40(portfolio_snapshot)、21:49(holdings_true)两快照，价格因日内不同时刻略异（NVDA 205.23/207.29）——采用22:47 production·差异留痕待架构师定"以哪一时刻为准"。FX USDJPY={FX:.4f}。</div>
<b style="font-size:13.5px">① 全账户持仓（20只·07-22 OpenD价·账户拆分724已有）</b>
<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px;margin:6px 0 12px">
<tr style="background:#12324e;color:#fff"><th>名称</th><th>代码</th><th>账户拆分</th><th>股数</th><th>07-22价</th><th>市值(本币)</th><th>动作</th></tr>
{hold_rows}</table></div>
<b style="font-size:13.5px">② 账户现金（红=非今日旧值·须董事长核）</b>
<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:12px;margin:6px 0 12px">
<tr style="background:#12324e;color:#fff"><th>账户</th><th>接入/日期</th><th>现金</th><th>来源</th></tr>
{cash_html}</table></div>
<div style="font-size:12px;color:#a11;margin-bottom:8px">★FUTU现金另有"董事长口头核报当日 ¥2,130,000+$205"（≈$13,315）与OpenD $41,103.99 不一致——以OpenD实时为准·口头值待核。</div>
<b style="font-size:13.5px">③ SNDK股数</b>：账户为准 <b>5股</b>（富通5）。富途今日曾显20股 → 原724值20留痕·待董事长最终核。
<div style="margin-top:6px;font-size:12px"><b>④ 负现金/融资利息</b>：724无此项·07-22无数据源·标C不编（富途保证金账户是否负现金待董事长核）。
<b>⑤ 预测验证日</b>：locked_baseline_20260722 核对日示例 2026-10-31 等（08-05近验证）·底稿08-05预测保留。</div>
<div style="font-size:12px;color:#666;margin-top:8px;border-top:1px dashed #ccc;padding-top:6px">⚠ 下方三层底稿的现价字段已刷新为07-22 OpenD快照；<b>底稿分析文字与推导市值/占比为生产时点基线</b>，全账户07-22权威口径以本更新层为准。</div>
</div>
'''

anchor = '<a id="top"></a>'
na = h.count(anchor); must(na == 1, f"插入锚点<a id=top>计数{na}≠1")
h = h.replace(anchor, anchor + "\r\n" + LAYER.replace("\n", "\r\n"), 1)

# 技术字段·标题
h = h.replace("<title>★每日投资产品 · 2026-07-19 · 三层</title>",
              "<title>★每日投资产品 · 2026-07-22数据更新（724底稿保真恢复） · 三层</title>", 1)

OUT.write_bytes(h.encode("utf-8"))
raw = OUT.read_bytes()
print("阶段2产物:", OUT.name, len(raw), "字节 · EFBFBD乱码=", raw.count(b"\xef\xbf\xbd"))
print("变更条目:", len(changes), "· 更新层已插:", "update-0722" in h)
print("残留07-17（周五）盘后/收盘:", h.count("2026-07-17（周五）盘后") + h.count("2026-07-17（周五）收盘"))
# 落变更清单
(ROOT / "data/screen/stage2_changes_20260722.json").write_text(
    json.dumps({"changes": changes, "ABC": abc}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("变更清单: data/screen/stage2_changes_20260722.json")
