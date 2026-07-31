#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""四层分类得分(candidates_v2) HTML报告·F-07双轴/F-08分层·不合并总分。用法: python scripts/change_score_report.py --date 20260721"""
import argparse, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "data" / "screen"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def r1(v):
    return round(v, 1) if isinstance(v, (int, float)) else ("" if v is None else v)


def cell(layer):
    if not layer or layer.get("得分") is None:
        cov = (layer or {}).get("数据覆盖率", 0)
        return f"<td class='c-no'>—<br><span class='mono'>覆盖{cov}·无法充分判定</span></td>"
    cov = layer.get("数据覆盖率", 0)
    cls = "c-ok" if cov >= 0.75 else ("c-mid" if cov >= 0.5 else "c-no")
    return f"<td class='{cls}'><b>{r1(layer['得分'])}</b><br><span class='mono'>覆盖{cov}·{esc(layer.get('结论可信度',''))[:6]}</span></td>"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="20260721"); a = ap.parse_args()
    d = a.date
    v2 = json.loads((S / f"candidates_v2_{d}.json").read_text(encoding="utf-8"))
    cs = json.loads((S / f"change_score_{d}.json").read_text(encoding="utf-8"))
    cards = v2["cards"]
    cov4 = cs["四项同比可得率%"]
    cova = cs.get("加速度可得率%", {})
    gmx = cs.get("毛利率覆盖分解_结构vs缺失", {})
    from collections import Counter
    cred = Counter(cards[c]["基本面变化层"].get("结论可信度", "")[:1] for c in cards)
    # 按基本面变化层覆盖率≥0.75 且得分排(仅同档内·不跨档)
    hi = [c for c in cards if (cards[c]["基本面变化层"].get("数据覆盖率") or 0) >= 0.75]
    hi.sort(key=lambda c: -(cards[c]["基本面变化层"].get("得分") or 0))
    rows = ""
    for c in hi[:40]:
        v = cards[c]; f = v["基本面变化层"].get("指标", {})
        flag = v["常识核对"][0]
        rows += (f"<tr><td class='mono'>{esc(c)}</td><td class='mono' style='font-size:10px'>{esc(v['基本面变化层'].get('数据方案') or '')}</td>"
                 + cell(v["基本面变化层"]) + cell(v["市场先行层"]) + cell(v["市场确认层"]) + cell(v["行业扩散层"])
                 + f"<td class='num'>{r1(f.get('利润同比%'))}/{r1(f.get('利润加速度pp'))}</td>"
                 f"<td class='num'>{r1(f.get('营收同比%'))}/{r1(f.get('营收加速度pp'))}</td>"
                 f"<td class='num'>{r1(f.get('毛利率同比pp'))}·{esc(f.get('毛利率趋势') or '')}</td>"
                 f"<td class='num'>{r1(f.get('OCF同比%'))}/{r1(f.get('OCF加速度pp'))}</td>"
                 f"<td>{'亏损收窄' if f.get('亏损收窄') else ''}{'由亏转盈' if f.get('由亏转盈') else ''}</td>"
                 f"<td class='{'c-ok' if flag.startswith('通过') else 'c-no'}'>{esc(flag[:12])}</td></tr>")

    html = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>变化驱动·四层分类得分 · {d}</title>
<style>
body{{font-family:"Microsoft YaHei","PingFang SC",sans-serif;line-height:1.7;color:#1A1A1A;background:#F5F6F8;max-width:1280px;margin:0 auto;padding:16px 14px 60px}}
h2{{font-size:16px;color:#12324E;border-left:5px solid #12324E;padding-left:10px;margin:20px 0 8px}}
.hdr{{background:#12324E;color:#fff;border-radius:10px;padding:14px 18px;margin-bottom:12px}}
.hdr .sub{{font-size:13px;opacity:.92;margin-top:4px}}
table{{border-collapse:collapse;width:100%;font-size:11.4px;background:#fff;margin:8px 0}}
th,td{{border:1px solid #DDE3E8;padding:5px 6px;text-align:center;vertical-align:middle}}
th{{background:#12324E;color:#fff}} .mono{{font-family:Consolas,monospace;font-size:10px;color:#33414D}} .num{{text-align:right;font-family:Consolas,monospace}}
.c-ok{{background:#E4F3EA;color:#1E7A45;font-weight:700}} .c-mid{{background:#FBF3E3;color:#6B5200;font-weight:700}} .c-no{{background:#FBECEC;color:#A3231F;font-weight:700}}
.warn{{background:#FBF0E7;border:1px solid #C99A6B;border-radius:8px;padding:10px 14px;margin:8px 0;color:#6B3E00;font-size:12.5px}}
.big{{background:#EEF4F8;border:1px solid #B9D3E6;border-radius:8px;padding:12px 16px;margin:8px 0;color:#12324E;font-size:14px;font-weight:700}}
.scroll{{overflow-x:auto}}
</style></head><body>
<div class="hdr"><div style="font-size:20px;font-weight:800">📊 变化驱动 · 四层分类得分（不合并总分）</div>
<div class="sub">{d} ｜ ★只算不筛选·不出名单·不给买卖建议·不改尺·<b>不合并成单一总分</b> ｜ 入围 {v2['入围']}只</div></div>

<div class="big">一句话：四根柱子<b>全部算出</b>——同比可得率 利润 {cov4['利润']}% · 营收 {cov4['营收']}% · 毛利率同比 {cov4['毛利率同比']}% · OCF {cov4['OCF']}%；<b>加速度可得率</b> 利润 {cova.get('利润加速度')}% · 营收 {cova.get('营收加速度')}% · OCF {cova.get('OCF加速度')}%（PIT 已存16期·≥2个FY→加速度可算·上一版全null的致命已修）。<br>
可信度分布：高 <b>{cred.get('高',0)}</b> / 中 <b>{cred.get('中',0)}</b> / 低 <b>{cred.get('低',0)}</b>（可信度已按 柱子数+加速度数+异常 收紧·非只看覆盖率）。capex/真自由现金流仍<b>待查·不采信</b>；行业扩散层未算(覆盖0)。</div>
<div class="warn"><b>毛利率覆盖分解（答架构师问）：</b>入围 {gmx.get('总入围')} 只中，毛利率同比可得 <b>{gmx.get('毛利率同比可得')}</b>；<b>{gmx.get('结构性无营业成本科目(银行/保险/地产类·非缺失)')}</b> 只是<b>结构性无营业成本科目</b>（银行/保险/地产·8003/8004不存在·<u>该行业没有毛利率概念·非"数据没取到"</u>）；有科目但数据缺失 <b>{gmx.get('有科目但数据缺失(期数不足等)')}</b> 只。两者已分开、不混进同一覆盖率数字。结构性无毛利行业：{esc('、'.join((gmx.get('结构性无毛利的行业') or [])[:8]))}。</div>

<div class="warn"><b>★F-07(五铁律)＋F-08(四层不重复)已落地：</b>①缺失不计0 ②缺失权重不转移 ③不同覆盖率不直接排名(下表仅基本面变化层高覆盖档) ④覆盖不足→无法充分判定 ⑤<b>禁"得分×覆盖率"合并·四层各列不合并</b>。财报后市场反应只放【市场确认层】(不再与变化驱动重复计分)。<b>capex/真FCF待查·不采信。</b></div>

<h2>四层分类得分（基本面变化层高覆盖档·前40·每格：得分/覆盖率/可信度）</h2>
<div class="scroll"><table>
<tr><th>代码</th><th>方案</th><th>基本面变化层</th><th>市场先行层</th><th>市场确认层</th><th>行业扩散层</th><th>利润同比/加速</th><th>营收同比/加速</th><th>毛利率pp·趋势</th><th>OCF同比/加速</th><th>亏损</th><th>常识</th></tr>
{rows}
</table></div>
<div class="warn">行业扩散层全列"—覆盖0"：需全行业成员kline算上涨广度/新高比例·成本高·本轮未算·如实标（不计0分·F-07④）。常识核对待查：{esc('、'.join(v2['常识核对待查'][:20])) if v2['常识核对待查'] else '无明显异常'}。</div>

<h2>四项可得率（432只·同比 vs 加速度）</h2>
<div class="scroll"><table><tr><th>口径</th><th>利润</th><th>营收</th><th>毛利率同比</th><th>OCF</th></tr>
<tr><td>同比可得率%</td><td class='num'>{cov4['利润']}</td><td class='num'>{cov4['营收']}</td><td class='num'>{cov4['毛利率同比']}</td><td class='num'>{cov4['OCF']}</td></tr>
<tr><td>加速度可得率%</td><td class='num'>{cova.get('利润加速度')}</td><td class='num'>{cova.get('营收加速度')}</td><td class='num'>{cova.get('毛利率同比')}</td><td class='num'>{cova.get('OCF加速度')}</td></tr></table></div>

<div class="hdr" style="text-align:center;background:#fff;color:#12324E;border:1px solid #DDE3E8"><b>本轮只把变化驱动扩到4根并按F-07/F-08四层输出·未筛选未出名单·未合并总分。请架构师核对后再设计标准。</b><br>
<span class="mono">实物：data/screen/change_score_{d}.json · candidates_v2_{d}.json</span></div>
</body></html>"""
    out = ROOT / "00_请先看这里" / f"变化驱动四层分类得分_{d}.html"
    out.write_text(html, encoding="utf-8")
    raw = out.read_bytes()
    print("wrote", out.name, len(raw), "字节 · EFBFBD=", raw.count(b"\xef\xbf\xbd"))


if __name__ == "__main__":
    main()
