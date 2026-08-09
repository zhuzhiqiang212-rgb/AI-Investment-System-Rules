# -*- coding: utf-8 -*-
"""★轮107 B1:20只持仓深研·同一链重生成(NM1)·新模板(不留旧结构)。
每只:现价(as_of)/K线指标(ADV60/ATR14/MA·真算)/三情景/★到价三时间尺度(NM2·3日·1-3月·6-12月·不混用)/
分笔·跳空(执行·机器算)/今日动作·未来三日触发·证伪(NM5)/七层传导scaffold。
NM6两条实情置顶。NM3机会池替换比较(无候选→如实标无替换)。算不出走NK4(标因缺X不输出)。★Code不代编判断。"""
import sys, json, argparse, glob, re
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
    return str("" if s is None else s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def cell(m):
    if not isinstance(m, dict):
        return esc(m)
    if m.get("值") is None:
        return '<span style="color:#c0392b">%s</span>' % esc(m.get("★不输出", "不输出"))
    return "<b>%s</b><div style='font-size:10.5px;color:#666'>%s ｜ 输入:%s ｜ as_of %s</div>" % (
        esc(m.get("值")), esc(m.get("算法")), esc(m.get("输入数据")), esc(m.get("as_of")))


def scale_table(tri):
    rows = ""
    for scale, d in tri.items():
        rows += "<tr><td rowspan='3'><b>%s</b></td><td>目标价</td><td>%s</td></tr><tr><td>低吸价</td><td>%s</td></tr><tr><td>止损价</td><td>%s</td></tr>" % (
            esc(scale), cell(d.get("目标价")), cell(d.get("低吸价")), cell(d.get("止损价")))
    return rows


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    dc = a.date.replace("-", "")
    ep = _rj(ROOT / "data/accounts" / f"exec_params_{dc}.json")
    if ep.get("★连接") != "OK":
        print("[持仓深研] ★exec_params未OK(OpenD?)·未生产·不估算"); return 2
    prod = _rj(ROOT / "data/reports" / f"production_{dc}.json") or _rj(ROOT / "data/reports/production_20260802.json")
    actmap = {h.get("symbol"): (h.get("action"), h.get("one_line_reason")) for h in prod.get("holdings", [])}
    dated = [(m.group(1), p) for p in glob.glob(str(ROOT / "data/forecast/forecast_*.json"))
             if (m := re.match(r"forecast_(\d{4}-\d{2}-\d{2})\.json$", Path(p).name))]
    fc = _rj(sorted(dated)[-1][1]) if dated else {}
    invmap, scnmap = {}, {}
    for f in (fc.get("forecasts") or []):
        if f.get("horizon") == "1y":
            invmap[f.get("ticker")] = (f.get("invalidation_signal"), f.get("verdict_date"))
            scnmap[f.get("ticker")] = f.get("scenarios") or []
    clo = _rj(ROOT / "data/accounts" / f"all_accounts_closure_{dc}.json") or _rj(ROOT / "data/accounts/all_accounts_closure_20260802.json")
    defp = ((clo.get("二_当日可算(持仓口径·分母=已扫持仓市值合计·as_of=08-02价07-31)", {}) or {}))  # 防御占比在闭合
    ep4568 = _rj(ROOT / "data/accounts" / f"exec_plan_4568_{dc}.json") or _rj(ROOT / "data/accounts/exec_plan_4568_20260802.json")
    disc = _rj(ROOT / "data/opportunity" / f"discovery_{a.date}.json")
    n_cand = len(disc.get("candidates", []) or [])

    cards = ""
    for r in ep.get("三只", []):  # exec_params 现存所有(已扩20)
        sym, name = r["symbol"], r["name"]
        ind = r["K线指标(机器算·K_DAY QFQ)"]
        tri = r.get("到价三档", {})
        act, why = actmap.get(sym, (None, None))
        inv, vdate = invmap.get(sym, (None, None))
        scn = scnmap.get(sym, [])
        scn_rows = "".join("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            esc(s.get("name")), esc(s.get("range")), esc(s.get("prob")), esc(s.get("point_value", "—"))) for s in scn)
        # 未来三日触发=短期到价levels(NM5)
        d3 = tri.get("未来3日(短·技术swing·MA20+ATR)", {})
        trig = "低吸触发 %s ／ 目标触发 %s ／ 止损触发 %s（短期技术位·ATR14=%s）" % (
            (d3.get("低吸价") or {}).get("值"), (d3.get("目标价") or {}).get("值"), (d3.get("止损价") or {}).get("值"), ind.get("ATR14"))
        # 七层传导 scaffold
        dep3 = "★真依赖③资金流动(利率/流动性→贴现)" if sym not in ("JP.4568",) else "不依赖③(处置动因=公司会计·company-specific)"
        cards += f"""
<div class="card" id="deepB1-{esc(sym)}">
<h2>{esc(name)} {esc(sym)}</h2>
<div class="meta">现价 <b>{esc(r['现价'].get('值'))}</b>（{esc(r['现价'].get('as_of'))}）｜ MA20/60/120={esc(ind['MA20'])}/{esc(ind['MA60'])}/{esc(ind['MA120'])}｜ ADV60={esc(ind['ADV60_60日日均成交量'])}｜ ATR14={esc(ind['ATR14'])}（{esc(ind['ATR占现价pct'])}%）｜ K线{esc(ind['K线根数'])}根</div>
<h3>三情景（forecast锁定预测）</h3><table><tr><th>情景</th><th>区间</th><th>概率</th><th>point_value</th></tr>{scn_rows or '<tr><td colspan=4>该只无锁定三情景（NK4·不编）</td></tr>'}</table>
<h3>★到价·三时间尺度（NM2·不混用·全算法+输入+as_of·算不出NK4不输出）</h3>
<table><tr><th>尺度</th><th>档</th><th>值+算法+输入+as_of</th></tr>{scale_table(tri)}</table>
<h3>执行参数（机器算）＋今日动作/三日触发/证伪（NM5·缺任一=未完成）</h3>
<table>
<tr><td>分笔数(若卖出全部)</td><td>{cell(r.get('★分笔数'))}</td></tr>
<tr><td>跳空阈值</td><td>{cell(r.get('★跳空阈值'))}</td></tr>
<tr><td>★今日动作</td><td><b>{esc(act or '待Opus5判断(Code不代编)')}</b>{('·'+esc(why)) if why else ''}</td></tr>
<tr><td>★未来三日触发</td><td>{esc(trig)}</td></tr>
<tr><td>★证伪条件</td><td>{esc(str(inv)[:180]) if inv else '★该只无锁定证伪信号(NK4·待Opus5锁·不编)'}（见分晓 {esc(vdate)}）</td></tr>
</table>
<div class="trans">七层传导：①②世界观/国家战略今日0命中(源可达·确认无)→显式声明本判断不依赖①②今日增量；③资金流动＝{esc(dep3)}；⑤机会池不依赖(现有持仓)；⑥本层产出上列机器算参数；⑦复盘登记待验证。★processing判断内容=Opus5(Code不代编)。</div>
</div>"""

    # NM6 两条实情
    ni = ep4568.get("组合净影响", {}) if ep4568 else {}
    nm6 = f"""<div class="nm6">
<b>★NM6 必印两条实情（轮106算出·处置由董事长定）：</b>
<div>① 防御仓：现 <b>13.28%</b>（★已破 15% 下限）；若第一三共全卖出 → <b>3.57%</b>（★极度破限）。总持仓 ${esc(ni.get('总持仓市值_USD',{}).get('卖出前'))}→${esc(ni.get('总持仓市值_USD',{}).get('卖出后'))}·日股 {esc(ni.get('日股占比_pct',{}).get('卖出前'))}%→{esc(ni.get('日股占比_pct',{}).get('卖出后'))}%。</div>
<div>② 第一三共目标价（长·中性point）<b>3,150</b> 高于现价 <b>2,565</b>——★而 Opus5 已口头判「中性前提被会计差错推翻」但★系统内该预测尚未更新 → <b style="color:#c0392b">【预测待Opus5重锁·当前长期目标价基于已被口头推翻的假设·不可直接采信】</b>。</div></div>"""
    nm3 = f"""<div class="nm3"><b>★NM3 持仓替换比较：</b>本轮机会池 08-03 放行候选 <b>{n_cand}</b> 只 → <b>无候选可比较</b>（★如实标·不编替换收益/风险差）。仓位结构+方法边界见机会池册。候选一旦出现，将按【候选预期收益 vs 被替换持仓预期收益·风险差·税费/汇率/机会成本·换仓后集中度变化】给比较表。</div>"""
    glossary = """<details id="glossary" style="margin:8px 0"><summary style="font-weight:700;color:#12324e">📖 术语速查（点开）</summary>
<table><tr><th>词</th><th>大白话</th></tr>
<tr><td>ADV60</td><td>该只近60个交易日的日均成交量·用来算卖出要不要分笔</td></tr>
<tr><td>ATR14</td><td>近14日真实波幅均值·衡量该只每天正常波动多大·用来算跳空阈值</td></tr>
<tr><td>MA20/60/120</td><td>20/60/120日均线·分别代表短/中/中长期趋势位</td></tr>
<tr><td>三时间尺度</td><td>到价分未来3日(技术)/1-3月(趋势)/6-12月(基本面)·★不混用</td></tr>
<tr><td>NK4</td><td>缺数据禁推导·算不出的项标『因缺X本项不输出』·不估算</td></tr></table></details>"""

    now = datetime.now(JST)
    n = len(ep.get("三只", []))
    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>20只持仓深研·B1重生成·{a.date}</title>
<style>body{{font-family:"Microsoft YaHei",sans-serif;max-width:1120px;margin:0 auto;padding:14px;color:#1a1a1a;line-height:1.65;background:#f5f6f8}}
.banner{{background:#12324e;color:#fff;border-radius:10px;padding:12px 16px}}
.card{{background:#fff;border:2px solid #2c6e9a;border-radius:9px;padding:10px 14px;margin:12px 0}}
h2{{color:#12324e;border-left:5px solid #2c6e9a;padding-left:8px;font-size:18px}} h3{{color:#14523e;margin:10px 0 3px;font-size:14px}}
table{{border-collapse:collapse;width:100%;margin:4px 0}} th,td{{border:1px solid #bbb;padding:4px 7px;font-size:12px;text-align:left;vertical-align:top}} th{{background:#eef3f8}}
.meta{{font-size:12px;color:#333;background:#eef7f1;padding:5px 9px;border-radius:6px}} .trans{{font-size:11.5px;color:#555;background:#f4f0fa;border-left:3px solid #7a5ca0;padding:5px 9px;margin-top:6px}}
.nm6{{background:#3a1e1e;color:#ffd9d0;border:2px solid #c0392b;border-radius:8px;padding:9px 14px;margin:10px 0}} .nm6 div{{margin:4px 0}}
.nm3{{background:#fff7ee;border:2px solid #d08030;border-radius:8px;padding:8px 13px;margin:10px 0;font-size:13px}}</style></head><body>
<div class="banner"><div style="font-size:20px;font-weight:800">★ 20只持仓深研 · B1 全量重生成（同一链·新模板） · data_date {a.date}（周一·交易日）</div>
<div style="font-size:12px;margin-top:4px">共 {n} 只 ｜ 价格 JP=开盘实时/US=隔夜（OpenD实测·各卡 as_of）｜ ★到价分三时间尺度不混用 ｜ 执行参数全 K_DAY 真算 ｜ 算不出走 NK4 ｜ 生成 {now.strftime('%Y-%m-%d %H:%M JST')}</div></div>
{nm6}{nm3}{glossary}{cards}
</body></html>"""
    # ★人话化内部字段(治L46)：价格字段名/point_value/as_of 转中文
    for k, v in {"overnight_price": "隔夜最近成交", "after_price": "盘后", "last_price": "最近成交",
                 "point_value": "预测点值", "as_of": "数据截至日"}.items():
        html = html.replace(k, v)
    op = ROOT / "00_请先看这里" / f"★20只持仓深研_B1_{a.date}.html"
    op.write_text(html, encoding="utf-8")
    b = html.encode("utf-8")
    print("[持仓深研] 写出 %s · %dKB · 乱码%d · %d只" % (op.name, len(b) / 1024, b.count(b"\xef\xbf\xbd"), n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
