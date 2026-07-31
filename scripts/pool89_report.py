#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主池·行业分布+市场确认层 HTML报告。用法: python scripts/pool89_report.py --date 20260721"""
import argparse, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "data" / "screen"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def r1(v):
    return round(v, 1) if isinstance(v, (int, float)) else ("" if v is None else v)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="20260721"); a = ap.parse_args()
    d = a.date
    ind = json.loads((S / f"pool89_industry_{d}.json").read_text(encoding="utf-8"))
    mkt = json.loads((S / f"pool89_market_{d}.json").read_text(encoding="utf-8"))
    bd = ind["89拆解"]; market = mkt["market"]
    top3 = ind["加速占比最高三行业(行业≥3只·更代表趋势)"]

    # 行业分布表
    irows = ""
    for k, v in sorted(ind["行业分布"].items(), key=lambda kv: -kv[1]["行业内加速占比%"]):
        irows += (f"<tr><td>{esc(k)}</td><td class='num'>{v['进主池39数']}</td><td class='num'>{v['该行业432总数']}</td>"
                  f"<td class='num'>{v['行业内加速占比%']}</td><td class='mono'>{esc('、'.join(v['成员']))}</td></tr>")
    # 市场确认表(39)
    mrows = ""
    for c, r in sorted(market.items(), key=lambda kv: -((kv[1].get('相对大盘1/3/6月%') or {}).get('3月') or -999)):
        rel = r.get("相对大盘1/3/6月%", {})
        susp = "⚠基数嫌疑" if r.get("基数效应嫌疑") else ""
        ri = r.get("相对行业强度")
        ri_txt = ("强于行业中位" if isinstance(ri, dict) and ri.get("强于行业中位") else ("弱于/平" if isinstance(ri, dict) else "部分"))
        mrows += (f"<tr><td class='mono'>{esc(c)}</td><td>{esc(r.get('行业') or '')[:9]}</td>"
                  f"<td class='num'>{r1(rel.get('1月'))}/{r1(rel.get('3月'))}/{r1(rel.get('6月'))}</td>"
                  f"<td>{'是' if r.get('相对大盘3月为正且斜率改善') else ''}</td>"
                  f"<td class='num'>{r1(r.get('距52周高%'))}</td><td class='num'>{r1(r.get('上涨日均量比下跌日均量'))}</td>"
                  f"<td class='num'>{r1(r.get('财报后跳空%'))}/{r1(r.get('20日守住%'))}</td>"
                  f"<td>{esc(ri_txt)}</td>"
                  f"<td class='num'>{'' if not r.get('基数',{}).get('营收绝对规模') else round(r['基数']['营收绝对规模']/1e9,1)}</td>"
                  f"<td class='c-no'>{esc(susp)}</td></tr>")

    html = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>主池·行业分布+市场确认层 · {d}</title>
<style>
body{{font-family:"Microsoft YaHei","PingFang SC",sans-serif;line-height:1.7;color:#1A1A1A;background:#F5F6F8;max-width:1240px;margin:0 auto;padding:16px 14px 60px}}
h2{{font-size:16px;color:#12324E;border-left:5px solid #12324E;padding-left:10px;margin:20px 0 8px}}
.hdr{{background:#12324E;color:#fff;border-radius:10px;padding:14px 18px;margin-bottom:12px}}
.hdr .sub{{font-size:13px;opacity:.92;margin-top:4px}}
table{{border-collapse:collapse;width:100%;font-size:11.6px;background:#fff;margin:8px 0}}
th,td{{border:1px solid #DDE3E8;padding:5px 6px;text-align:center;vertical-align:middle}}
th{{background:#12324E;color:#fff}} .mono{{font-family:Consolas,monospace;font-size:10.5px;color:#33414D}} .num{{text-align:right;font-family:Consolas,monospace}}
.c-no{{color:#A3231F;font-weight:700}}
.warn{{background:#FBF0E7;border:1px solid #C99A6B;border-radius:8px;padding:10px 14px;margin:8px 0;color:#6B3E00;font-size:12.5px}}
.big{{background:#EEF4F8;border:1px solid #B9D3E6;border-radius:8px;padding:12px 16px;margin:8px 0;color:#12324E;font-size:13.5px;font-weight:700}}
.scroll{{overflow-x:auto}}
</style></head><body>
<div class="hdr"><div style="font-size:20px;font-weight:800">🎯 主池 · 行业分布 ＋ 市场确认层</div>
<div class="sub">{d} ｜ ★只算不筛选·不出名单·不给买卖建议·不改尺·不合并总分</div></div>

<div class="warn"><b>★口径必读(诚实)：</b>您单据"主池89只(象限分歧=false)"实际拆解为 <b>①真强者 {bd['①真强者']}</b> ／ ②强者减速 {bd['②强者减速']} ／ ④持续恶化 {bd['④持续恶化(应排除)']}(按规矩应排除) ／ <b>无法判定象限 {bd['—无法判定象限(加速度缺)']}</b>(加速度缺→平凡"非分歧"·名不副实)。真正"四项同向加速"的只有 <b>{bd['①真强者']} 只</b>。本轮两项任务在这 {bd['①真强者']} 只【真主池】上做。若您要按全部89(含④与无法判定)做，请示下。</div>

<h2>任务1 · 真主池 {bd['①真强者']}只 的行业分布（真行业 plate_type=INDUSTRY）</h2>
<div class="big">① 落在 <b>{ind['行业数']}</b> 个行业。加速占比最高三行业(行业≥3只·更代表"整行业在变强")：
{esc(' · '.join(f"{x['行业']} {x['行业内加速占比%']}%({x['进主池39数']}/{x['该行业432总数']})" for x in top3))}。<br>
<span style="font-size:11.5px;font-weight:400">（{esc(ind.get('小样本提示',''))}）</span></div>
<div class="scroll"><table><tr><th>行业</th><th>进主池</th><th>该行业432总数</th><th>加速占比%</th><th>成员</th></tr>{irows}</table></div>

<h2>任务2 · 市场确认层五指标（F-08·与基本面层分开算·{bd['①真强者']}只）</h2>
<div class="big">五项可得率：相对大盘 {mkt['五项可得率']['相对大盘']}% · 距52周高 {mkt['五项可得率']['距52周高']}% · 上涨/下跌量 {mkt['五项可得率']['上涨/下跌量']}% · 财报跳空守住 {mkt['五项可得率']['财报跳空守住']}% · 相对行业强度 {esc(mkt['五项可得率']['相对行业强度'])}。<br>
<b>② 基数效应嫌疑（上期利润绝对值&lt;本期10%·暂行）：{len(mkt['基数效应嫌疑清单'])} 只 → {esc('、'.join(mkt['基数效应嫌疑清单']))}</b>。<br>
（注：Credo(CRDO) 利润同比+805% 已被 &gt;±500% 异常标注并截尾；其上期利润≈本期11%·刚好在10%线外·未进本清单·属边界·暂行阈值可调。）</div>
<div class="scroll"><table>
<tr><th>代码</th><th>行业</th><th>相对大盘1/3/6月%</th><th>3月正+斜率改善</th><th>距52周高%</th><th>涨/跌量</th><th>跳空/20日守住%</th><th>相对行业</th><th>营收$B</th><th>基数</th></tr>
{mrows}
</table></div>

<div class="big">③ 同时满足「四项加速」+「相对大盘3月为正且斜率改善」+「非基数效应嫌疑」的：<b>{len(mkt['同时满足四项加速+相对大盘3月正且斜率改善+非基数嫌疑'])} 只 → {esc('、'.join(mkt['同时满足四项加速+相对大盘3月正且斜率改善+非基数嫌疑']))}</b>（价格与基本面同步确认·基数效应可能性低）。</div>

<div class="hdr" style="text-align:center;background:#fff;color:#12324E;border:1px solid #DDE3E8"><b>本轮只做行业分布+市场确认+基数效应标注·未筛选未出名单·未合并总分。请架构师确认口径(89 vs 39)与暂行阈值后再设计标准。</b><br>
<span class="mono">实物：data/screen/pool89_industry_{d}.json · pool89_market_{d}.json</span></div>
</body></html>"""
    out = ROOT / "00_请先看这里" / f"主池行业分布与市场确认_{d}.html"
    out.write_text(html, encoding="utf-8")
    raw = out.read_bytes()
    print("wrote", out.name, len(raw), "字节 · EFBFBD=", raw.count(b"\xef\xbf\xbd"))


if __name__ == "__main__":
    main()
