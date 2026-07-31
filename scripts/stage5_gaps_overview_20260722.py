#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段5·治理144待补/待接(GPT四类A/B/C/D·结构化缺口)+全账户总览(GPT裁定2026-07-23)。
只增不删724。增补⑬数据缺口结构化登记(按类型覆盖724自陈~144实质缺口·每项:类/缺失内容/原因/现有数据日期/影响/责任方/下一处理/可执行性)。
增补⑭全账户总览(724持仓完整档案账户拆分merge→按账户+快照日期·标日期不称实时)。
★不伪造真值·不借"诚实缺口"留空模板:C类给完整结构化字段;A类填真值;B类保留旧值+标来源日期;D类(裸待补)=0(724无)。
"""
import html as H
import json
import re
from pathlib import Path

ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
SRC = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_阶段4动作统一.html"
OUT = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_阶段5缺口账户.html"
SPLIT = {"JP.4568": "富通6500＋SBI3400", "US.NVDA": "富通830＋IBKR190", "US.MSFT": "富通550＋IBKR140",
         "US.MSTR": "富通700＋IBKR158", "US.COIN": "富通200＋IBKR45", "JP.9984": "富通4100＋SBI2800",
         "JP.8766": "SBI1000", "JP.6758": "SBI1000", "JP.6857": "SBI800", "JP.7203": "SBI800",
         "JP.8001": "SBI900", "JP.7832": "富通500", "JP.7974": "富通2000", "US.AVGO": "富通150",
         "US.CRCL": "富通400", "US.SNDK": "富通5", "US.TSM": "富通1", "US.META": "IBKR95",
         "US.IBKR": "IBKR14", "US.SPCX": "富途10"}
prod = {x["symbol"]: x for x in json.loads((ROOT / "data/reports/production_20260722.json").read_text(encoding="utf-8"))["holdings"]}
NAME = {s: prod[s]["name"] for s in prod}


def e(x):
    return H.escape("" if x is None else str(x))


# ---------- 增补⑬ 数据缺口结构化登记(治理~144·GPT四类) ----------
# 每项: 类, 类型, 处数, 缺失内容, 原因, 现有数据日期, 影响, 责任方, 下一处理, 可执行性
GAPS = [
    ("A", "20只现价/持仓/账户拆分", "~60", "—已填真值", "—", "2026-07-22 OpenD", "已解决", "—", "已就地填7-22实时", "已用"),
    ("A", "YTD收益(13只口径)", "1", "—已填真值−4.7%", "—", "2026-07-22", "已解决", "—", "增补①/⑦已填", "已用"),
    ("A", "7-22统一动作(20只)", "~40", "—已填架构师deep", "—", "2026-07-22", "已解决", "—", "增补⑪+就地chip已统一", "守/等非交易量"),
    ("B", "无成本价(7只:东京海上/索尼/爱德万/丰田/伊藤忠/META/IBKR)", "7", "台账无average_cost", "台账无", "—(0719台账缺)", "YTD仅13只口径·非全口径", "董事长/台账岗", "补7只买入成本价", "涉盈亏计算·不直接执行"),
    ("B", "SBI/IBKR/bitFlyer账户余额", "3", "无OpenD·仅旧值", "该3账户无OpenD接口", "SBI个人07-18·SBI公司/IBKR/bitFlyer 07-02", "全账户分母含旧值前提·三比率为估算", "董事长手工", "手工核当前余额", "涉分母·标旧值不称实时"),
    ("B", "SNDK股数(富途今日20 vs 账户5)", "1", "两源冲突", "富途今日显20·账户台账5", "2026-07-22", "已取账户5·原20留痕", "董事长", "最终核实富途持仓", "已用5"),
    ("C", "权威估值真源(6-13只)", "13", "权威估值(架构师估值真源)", "未接权威估值源·仅系统PE代理", "无", "估值判断只有PE代理·非权威", "架构师", "接权威估值源", "不涉交易量"),
    ("C", "图表渲染/画法(倍数横比0/20·决策链0/20·曲线·柱状)", "34", "图形渲染", "chart渲染未接·文字/数字链已在", "文字链2026-07-22已有", "视觉图缺·结论文字已完整", "工程/Code", "接chart渲染管线", "不涉交易"),
    ("C", "护城河/moat评分(部分标的·如SpaceX未上市)", "6", "部分标的护城河维度", "未上市/moat未研究", "无", "护城河维度空·已标待研究", "分析岗", "补moat研究", "不涉交易"),
    ("C", "分部精确数(如丰田TFS金融)", "5", "分部营收/利润精确数", "分部数据未接", "无", "分部占比为粗估", "分析岗", "接分部财务数据", "不涉交易"),
    ("C", "催化剂库真源(8只)", "8", "8只催化剂三要素真源", "催化剂库未接全", "部分07-22", "催化剂方向部分空·可信度标传闻不单独支撑", "分析岗", "建全催化剂库", "不涉交易"),
    ("C", "BTC/ETH持仓数量", "3", "加密持仓数量", "未接进系统·bitFlyer无OpenD", "无", "加密敞口占比不算·不给动作价", "董事长", "手工核报数量", "涉持仓·不可直接执行"),
    ("C", "机会池第5关个股研究(7候选)", "7", "7候选个股深度研究", "第5关未做", "gate1-4已2026-07-22", "候选留观察·未成今日正式候选", "分析岗", "做第5关研究", "不涉交易(未推荐)"),
    ("C", "佐证料未覆盖标的", "~10", "老雷/湖水料未覆盖标的的佐证", "料as_of 05-29/06-04·未覆盖全部", "05-29/06-04", "该标的佐证空·标佐证料待接", "分析岗", "扩佐证料覆盖", "不涉交易"),
    ("C", "新持仓判断包(需理解岗建·如SpaceX)", "3", "新买入标的的完整判断包", "董事长新买入·理由未文档化", "无", "买入逻辑/替换条件空·已标待补原因", "理解岗", "建判断包", "不涉交易(不改现有动作)"),
    ("D", "裸待补(无原因/日期/影响)", "0", "—", "—", "—", "—", "—", "724无裸待补·全部带原因(归C/B)", "—"),
]
grows = ""
CLSBG = {"A": "#0f2e1c", "B": "#3a2a0a", "C": "#2a1a1a", "D": "#333"}
CLSFG = {"A": "#bfe9cf", "B": "#f0d9a0", "C": "#f5c6c6", "D": "#ccc"}
for g in GAPS:
    cls = g[0]
    grows += (f'<tr style="background:{CLSBG[cls]};color:{CLSFG[cls]}"><td><b>{cls}</b></td><td>{e(g[1])}</td><td style="text-align:center">{e(g[2])}</td>'
              f'<td>{e(g[3])}</td><td>{e(g[4])}</td><td>{e(g[5])}</td><td>{e(g[6])}</td><td>{e(g[7])}</td><td>{e(g[8])}</td><td>{e(g[9])}</td></tr>')
sec13 = (f'<div id="gap-registry-0722" style="border:3px solid #6b2020;background:#fdf5f5;border-radius:10px;padding:14px 16px;margin:12px 0">'
         f'<div style="font-size:17px;font-weight:800;color:#6b2020">■ 增补⑬ 数据缺口结构化登记（治理724自陈约144处待接/待补·GPT四类·2026-07-23）</div>'
         f'<div style="font-size:12.5px;color:#555;margin:4px 0 8px">A=已有真值已填·B=有旧值无7-22同日(保留+标来源日期)·C=确实未接(结构化缺口)·D=裸待补(724无·全部带原因归C/B)。'
         f'★不伪造真值·不借"诚实缺口"留空模板;涉交易量项均标"不可直接执行"。</div>'
         f'<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:11px">'
         f'<tr style="background:#12324e;color:#fff"><th>类</th><th>类型</th><th>处</th><th>缺失内容</th><th>原因</th><th>现有数据日期</th><th>影响</th><th>责任方</th><th>下一处理</th><th>可执行性</th></tr>'
         f'{grows}</table></div></div>')

# ---------- 增补⑭ 全账户总览(持仓账户拆分merge+快照日期) ----------
# 解析SPLIT→按账户聚合
acct_hold = {"富通/富途(FUTU)": [], "SBI": [], "IBKR": []}
for sym, sp in SPLIT.items():
    for part in re.split(r"＋", sp):
        m = re.match(r"(富通|富途|SBI|IBKR)(\d+)", part)
        if not m:
            continue
        who, q = m.group(1), m.group(2)
        key = "富通/富途(FUTU)" if who in ("富通", "富途") else who
        acct_hold[key].append(f"{NAME[sym]}{q}")
CASH = [
    ("FUTU(富途)", "✅ OpenD实时", "2026-07-22(今日)", "$41,103.99", "全账户覆盖·OpenD", True),
    ("SBI个人", "❌ 非今日", "2026-07-18(sbi_sleeve)", "余额缺", "旧快照·须董事长核", False),
    ("SBI公司", "❌ 非今日", "2026-07-02(OCR)", "¥19,520,910(合计SBI)", "portfolio_snapshot·07-02核报", False),
    ("IBKR", "❌ 非今日", "2026-07-02(OCR)", "$4,508", "portfolio_snapshot·07-02核报", False),
    ("bitFlyer", "❌ 非今日", "2026-07-02(OCR)", "¥295,363", "portfolio_snapshot·07-02核报", False),
    ("BTC/ETH(加密)", "⚠ 数量待接", "—", "数量未接", "未接进系统·待董事长", False),
]
h_rows = ""
for acct, holds in acct_hold.items():
    h_rows += f'<tr><td><b>{e(acct)}</b></td><td>{e("、".join(holds))}</td></tr>'
c_rows = ""
for acct, st, dt, amt, src, live in CASH:
    bg = "#0f2e1c" if live else "#3a1414"; fg = "#bfe9cf" if live else "#ffb3b3"
    c_rows += f'<tr style="background:{bg};color:{fg}"><td>{e(acct)}</td><td>{e(st)}</td><td>{e(dt)}</td><td style="text-align:right">{e(amt)}</td><td>{e(src)}</td></tr>'
sec14 = (f'<div id="account-overview-0722" style="border:3px solid #12324e;background:#f2f6fb;border-radius:10px;padding:14px 16px;margin:12px 0">'
         f'<div style="font-size:17px;font-weight:800;color:#12324e">■ 增补⑭ 全账户总览（724持仓完整档案账户拆分merge + 快照日期）</div>'
         f'<div style="font-size:12.5px;color:#555;margin:4px 0 8px">★仅FUTU为2026-07-22 OpenD实时;SBI/IBKR/bitFlyer为07-02/07-18旧快照·<b>标日期·不称实时</b>。</div>'
         f'<b style="font-size:13px">① 持仓按账户(股数·来自724完整档案拆分)</b>'
         f'<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:11.5px;margin:6px 0 10px"><tr style="background:#12324e;color:#fff"><th>账户</th><th>持仓(名称+股数)</th></tr>{h_rows}</table></div>'
         f'<b style="font-size:13px">② 账户现金/接入 + 快照日期(红=非今日)</b>'
         f'<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:11.5px;margin-top:6px"><tr style="background:#12324e;color:#fff"><th>账户</th><th>接入</th><th>快照日期</th><th>现金</th><th>来源</th></tr>{c_rows}</table></div></div>')

h = SRC.read_bytes().decode("utf-8")
anchor_ins = '<div id="stage3-augment"'
h = h.replace(anchor_ins, sec14 + sec13 + anchor_ins, 1)

OUT.write_bytes(h.encode("utf-8"))
raw = OUT.read_bytes()
print("阶段5产物:", OUT.name, len(raw), "字节·EFBFBD乱码=", raw.count(b"\xef\xbf\xbd"), "·裸LF=", raw.count(b"\n") - raw.count(b"\r\n"))
print("缺口登记/全账户总览已插:", "gap-registry-0722" in h, "/", "account-overview-0722" in h)
from collections import Counter
cc = Counter(g[0] for g in GAPS)
print("GAP分类: A=%d B=%d C=%d D=%d 类型行=%d" % (cc["A"], cc["B"], cc["C"], cc["D"], len(GAPS)))
(ROOT / "data/screen/stage5_gaps_20260722.json").write_text(json.dumps({
    "gap_registry": [{"类": g[0], "类型": g[1], "处数": g[2], "缺失内容": g[3], "原因": g[4], "现有数据日期": g[5],
                      "影响": g[6], "责任方": g[7], "下一处理": g[8], "可执行性": g[9]} for g in GAPS],
    "分类计数": dict(cc), "D类裸待补": 0, "account_holdings_by_account": acct_hold,
    "account_cash_snapshot": [{"账户": c[0], "接入": c[1], "快照日期": c[2], "现金": c[3], "来源": c[4]} for c in CASH],
}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("落: data/screen/stage5_gaps_20260722.json")
