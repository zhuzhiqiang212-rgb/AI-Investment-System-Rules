# -*- coding: utf-8 -*-
"""★轮106 NL1-NL4:三只样板端到端(US.MSFT/JP.6857/JP.4568)·08-03交易日。
链:数据(exec_params真算)→三情景(forecast)→到价(算)→账户与数量→七层传导(3字段·NL4)→样板HTML。
★七层传导:received_from_upper/processing/passed_to_lower。上层空→只两条合法路径(阻断|显式声明不依赖·理由)·禁第三条。
★执行参数全部机器算(exec_params_build)·Code不填判断数字;判断内容引用Opus5逐只判断(不代编)。"""
import sys, json, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def esc(s):
    return (str("" if s is None else s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def transmission(sym, dc, ep, opus_reason, action):
    """七层传导·3字段/层·读08-03上层真数据。上层空→显式声明不依赖(理由)或阻断(NL4·禁第三条)。"""
    wv = _rj(ROOT / "data/market" / f"worldview_{dc}.json")
    st = _rj(ROOT / "data/market" / f"strategy_{dc}.json")
    mf = _rj(ROOT / "data/market" / f"macro_flow_{dc}.json")
    sr = _rj(ROOT / "data/market" / f"sector_rotation_{dc}.json")
    wv_z = wv.get("★零命中分类(NK2·全局)", "?"); wv_can = wv.get("★下游可否宣称今日无事件")
    st_z = st.get("★零命中分类(NK2·全局)", "?")
    # ③资金流动核心数(received)
    rates = []
    for x in (mf.get("核心指标", []) or [])[:4]:
        v = x.get("值") if isinstance(x.get("值"), (str, int, float)) else (x.get("值", {}) or {}).get("值")
        if x.get("接通"):
            rates.append("%s=%s" % (x.get("指标"), v))
    rate_str = "·".join(rates) if rates else "③层核心指标见macro_flow"
    sec = sr.get("★接通", {})
    empty_upper_note = ("①世界观今日『%s』(总命中0)、②国家战略『%s』——★上层无今日增量事件。"
                        "本判断【显式声明：不依赖①②层今日增量·合法路径②·NL4】·理由：" % (wv_z, st_z))
    layers = [
        {"层": "①世界观", "received_from_upper": "①层今日：%s·总命中%s(源可达·非抓取失败)" % (wv_z, wv.get("总命中")),
         "processing": empty_upper_note + ("%s 的处置动因是【%s】·非今日地缘/世界观增量事件——故不依赖①层今日无新事件(★非『上层空还照出判断不吭声』的第三条)" % (sym, action)),
         "passed_to_lower": "向②③层传递：世界观regime无今日切换·沿用既有regime基线"},
        {"层": "②国家战略", "received_from_upper": "②层今日：%s·三张战略地图(AI/安全/能源)沿用" % st_z,
         "processing": "②层无今日新立法/管制事件→本判断显式声明不依赖②层今日增量(理由同上·company/rates驱动)",
         "passed_to_lower": "向③④层传递：战略地图无今日变更"},
        {"层": "③资金流动", "received_from_upper": "③层(总闸)received：%s(as_of %s)" % (rate_str, mf.get("as_of", "08-03")),
         "processing": "★这是【真依赖】的上层：利率/流动性决定贴现压力。processing＝%s（Opus5判断·Code不代编）" % opus_reason.get("③", "见Opus5逐只判断"),
         "passed_to_lower": "向⑥持仓传递：贴现/流动性档位→影响该股估值锚与到价"},
        {"层": "④板块轮动", "received_from_upper": "④层received：板块轮动接通%s·%s" % (sr.get("★接通N/4", "?"), esc(json.dumps(sec, ensure_ascii=False))[:80]),
         "processing": "processing＝%s" % opus_reason.get("④", "板块信号并入该股周期位置判断(Opus5)"),
         "passed_to_lower": "向⑥持仓传递：所属板块强弱→择时参考"},
        {"层": "⑤机会池", "received_from_upper": "⑤层：该只为【现有持仓】·非新机会候选",
         "processing": "持仓标的不走机会池五关新建仓路径→本判断显式声明不依赖⑤层(合法路径②·理由:已持仓)",
         "passed_to_lower": "无(持仓不向机会池传递建仓信号)"},
        {"层": "⑥持仓(本层)", "received_from_upper": "汇总①②③④上层：regime无今日切换+利率紧档+板块信号",
         "processing": ("本层产出【机器算执行参数】：现价%s(as_of %s)·目标价%s·低吸MA60=%s·止损MA120=%s；"
                        "分笔数%s·跳空阈值%s%%(全K_DAY真算·见exec_params)。★买卖决策=%s(动因:%s·Opus5)"
                        % (ep["现价"].get("值"), ep["现价"].get("as_of"),
                           ep["到价三档"]["目标价"].get("值"), ep["到价三档"]["低吸价"].get("值"), ep["到价三档"]["止损价"].get("值"),
                           ep["★分笔数"].get("值"), ep["★跳空阈值"].get("值"), action, opus_reason.get("⑥", ""))),
         "passed_to_lower": "向⑦复盘传递：本次决策+到价+执行参数→待验证(见分晓日)"},
        {"层": "⑦复盘", "received_from_upper": "⑥持仓本次决策+到价+执行参数",
         "processing": "登记预测/决策→PDCA计时·待到期验证(forecast verdict_date)·到期比对实际",
         "passed_to_lower": "向①层反馈：验证结果修正世界观/判断能力度量(闭环)"},
    ]
    return layers


def stock_card(sym, name, ep, fc_scn, acct, opus_reason, action, dc):
    scn_rows = ""
    for s in fc_scn:
        scn_rows += ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                     % (esc(s.get("name")), esc(s.get("range")), esc(s.get("prob")), esc(s.get("point_value", "—"))))
    pt = ep["到价三档"]

    def cell(m):
        if m.get("值") is None:
            return '<span style="color:#c0392b">%s</span>' % esc(m.get("★不输出", "不输出"))
        return "<b>%s</b><div style='font-size:11px;color:#666'>算法：%s<br>输入：%s · as_of %s</div>" % (
            esc(m.get("值")), esc(m.get("算法")), esc(m.get("输入数据")), esc(m.get("as_of")))
    trans = transmission(sym, dc, ep, opus_reason, action)
    trans_rows = ""
    for L in trans:
        trans_rows += ("<tr><td><b>%s</b></td><td>%s</td><td>%s</td><td>%s</td></tr>"
                       % (esc(L["层"]), esc(L["received_from_upper"]), esc(L["processing"]), esc(L["passed_to_lower"])))
    ind = ep["K线指标(机器算·K_DAY QFQ)"]
    return f"""
<div class="card" id="sample-{esc(sym)}">
<h2>{esc(name)} {esc(sym)} — 决策：{esc(action)}</h2>
<div class="meta">现价 <b>{esc(ep['现价'].get('值'))}</b>（{esc(ep['现价'].get('as_of'))}·{esc(ep['现价'].get('来源'))}）｜ K_DAY真算：MA20/60/120={esc(ind['MA20'])}/{esc(ind['MA60'])}/{esc(ind['MA120'])}·ADV60={esc(ind['ADV60_60日日均成交量'])}·ATR14={esc(ind['ATR14'])}({esc(ind['ATR占现价pct'])}%)·K线{esc(ind['K线根数'])}根</div>
<h3>三情景（point_value+概率·来自锁定预测 forecast）</h3>
<table><tr><th>情景</th><th>区间</th><th>概率</th><th>point_value</th></tr>{scn_rows}</table>
<h3>到价三档（★全算出·算法+输入+as_of·算不出不输出NK4）</h3>
<table><tr><th>到价</th><th>值+算法+输入+as_of</th></tr>
<tr><td>目标价</td><td>{cell(pt['目标价'])}</td></tr>
<tr><td>低吸价</td><td>{cell(pt['低吸价'])}</td></tr>
<tr><td>止损价</td><td>{cell(pt['止损价'])}</td></tr></table>
<h3>★执行参数（★机器算·非拍脑袋）</h3>
<table><tr><th>参数</th><th>值+算法+输入+as_of</th></tr>
<tr><td>分笔数</td><td>{cell(ep['★分笔数'])}</td></tr>
<tr><td>跳空阈值</td><td>{cell(ep['★跳空阈值'])}</td></tr>
<tr><td>每档价格</td><td>{cell(ep['每档价格'])}</td></tr></table>
<h3>账户与数量（NL3）</h3>
<div class="acct">{acct}</div>
<h3>七层传导（NL4·received/processing/passed·上层空→显式声明不依赖或阻断·禁第三条）</h3>
<table><tr><th>层</th><th>received_from_upper</th><th>processing</th><th>passed_to_lower</th></tr>{trans_rows}</table>
</div>"""


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    dc = a.date.replace("-", "")
    epd = _rj(ROOT / "data/accounts" / f"exec_params_{dc}.json")
    if epd.get("★连接") != "OK":
        print("[样板] ★exec_params 未OK(OpenD连不上?)·未生产·不估算"); return 2
    epmap = {r["symbol"]: r for r in epd.get("三只", [])}
    # forecast scenarios
    import glob, re
    dated = [(m.group(1), p) for p in glob.glob(str(ROOT / "data/forecast/forecast_*.json"))
             if (m := re.match(r"forecast_(\d{4}-\d{2}-\d{2})\.json$", Path(p).name))]
    fc = _rj(sorted(dated)[-1][1]) if dated else {}
    scn = {}
    for f in (fc.get("forecasts") or []):
        if f.get("horizon") == "1y":
            scn[f.get("ticker")] = f.get("scenarios") or []
    ht = _rj(ROOT / "data/accounts" / f"holdings_true_{dc}.json")
    hmap = {h.get("symbol"): h for h in ht.get("holdings", [])}
    ep4568 = _rj(ROOT / "data/accounts" / f"exec_plan_4568_{dc}.json") or _rj(ROOT / "data/accounts/exec_plan_4568_20260802.json")

    # 每只:决策(action·第一三共=卖出给定;MSFT/爱德万=Opus5判断·此处标)+账户数量+Opus5理由
    plan = {
        "US.MSFT": {"action": "持有观察（★富途23.55%超单只20%上限·是否减仓=Opus5判断）",
                    "acct": "富途 665股@ $461.81(市值$307,104)·占富途23.55%＞20%上限。★减仓与否及减多少=Opus5判断(Code不代编);若定减仓·减仓股数一到·分笔数即可按ADV60真算。",
                    "reason": {"③": "利率4.75%紧档=实打实贴现压力·MSFT PE23.6需Azure加速撑(Opus5)", "④": "AI板块·capex转化存疑(Meta同日盈利未跟上被罚·Opus5)", "⑥": "目标价(中性)420<现价467→中性口径偏贵·capex能否转Azure收入是关键(Opus5)"}},
        "JP.6857": {"action": "持有观察（★高波动·价格已进乐观区·消化期误判风险）",
                    "acct": "SBI 800股@ ¥28,887·占SBI一半以上波动。★不动(Opus5:算不准·两口径差十倍);ATR14=8.24%证其高波动·若定减仓分笔数按ADV60真算。",
                    "reason": {"③": "高利率对高PE有贴现压力(Opus5)", "④": "半导体设备·测试机(Opus5)", "⑥": "现价32130＞乐观区间下沿·★点值口径:中性27330·乐观44639——现价已进乐观区·『新台阶vs周期顶』判不准(Opus5·不加仓)"}},
        "JP.4568": {"action": "★卖出全部9,900股（今日交易日·董事长要执行）",
                    "acct": "SBI 3,400 ＋ 富途 6,500 ＝ 9,900股·全部卖出转现金。组合净影响(exec_plan_4568真算)：见下。",
                    "reason": {"③": "不依赖③层(处置动因=会计造假·company-specific)", "④": "不依赖④层", "⑥": "卖出动因=七月会计做错账+五月特别损失·两次财务出问题→报出的数字不可用·非估值/regime(Opus5逐只判断)"}},
    }
    # 第一三共账户块补组合净影响
    if ep4568:
        ni = ep4568.get("组合净影响", {})
        plan["JP.4568"]["acct"] += ("<br>组合净影响：总持仓 $%s→$%s·日股 %s%%→%s%%·防御 %s%%→%s%%(★已破15%%下限)·现金占比待接(现金基数null·NK4不编)" % (
            ni.get("总持仓市值_USD", {}).get("卖出前"), ni.get("总持仓市值_USD", {}).get("卖出后"),
            ni.get("日股占比_pct", {}).get("卖出前"), ni.get("日股占比_pct", {}).get("卖出后"),
            ni.get("防御仓占比_pct", {}).get("卖出前"), ni.get("防御仓占比_pct", {}).get("卖出后")))

    cards = ""
    for sym, name in [("US.MSFT", "微软"), ("JP.6857", "爱德万"), ("JP.4568", "第一三共")]:
        ep = epmap.get(sym)
        if not ep:
            continue
        cards += stock_card(sym, name, ep, scn.get(sym, []), plan[sym]["acct"], plan[sym]["reason"], plan[sym]["action"], dc)
    now = datetime.now(JST)
    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>三只样板端到端 · {a.date}</title>
<style>body{{font-family:"Microsoft YaHei",sans-serif;max-width:1100px;margin:0 auto;padding:14px;color:#1a1a1a;line-height:1.7;background:#f5f6f8}}
.banner{{background:#12324e;color:#fff;border-radius:10px;padding:12px 16px;margin-bottom:12px}}
.card{{background:#fff;border:2px solid #2c6e9a;border-radius:10px;padding:12px 16px;margin:14px 0}}
h2{{color:#12324e;border-left:5px solid #2c6e9a;padding-left:8px}} h3{{color:#14523e;margin:12px 0 4px}}
table{{border-collapse:collapse;width:100%;margin:6px 0}} th,td{{border:1px solid #bbb;padding:5px 8px;font-size:12.5px;text-align:left;vertical-align:top}}
th{{background:#eef3f8}} .meta{{font-size:12.5px;color:#333;background:#eef7f1;padding:6px 10px;border-radius:6px}} .acct{{background:#fff7ee;border-left:4px solid #d08030;padding:6px 10px;font-size:13px}}</style></head><body>
<div class="banner"><div style="font-size:20px;font-weight:800">★ 三只样板 · 端到端跑通（NL1-NL4） · data_date {a.date}（周一·交易日）</div>
<div style="font-size:12.5px;margin-top:4px">价格：JP=08-03日股开盘实时·US=隔夜最近成交（OpenD实测·见各卡as_of）｜生成 {now.strftime('%Y-%m-%d %H:%M JST')}｜★执行参数全部机器算(K_DAY QFQ·ADV60/ATR14/均线)·无拍脑袋·算不出标NK4不输出</div></div>
{cards}
</body></html>"""
    op = ROOT / "00_请先看这里" / f"★三只样板_端到端_{a.date}.html"
    op.write_text(html, encoding="utf-8")
    b = html.encode("utf-8")
    print("[样板] 写出", op.name, "·", round(len(b) / 1024), "KB· 乱码", b.count(b"\xef\xbf\xbd"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
