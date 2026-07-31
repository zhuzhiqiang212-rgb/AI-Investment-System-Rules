#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""变化驱动层(4根柱子) HTML报告·F-07双轴。用法: python scripts/change_driver_report.py --date 20260721"""
import argparse, json, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def r1(v):
    return round(v, 1) if isinstance(v, (int, float)) else ("" if v is None else v)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="20260721"); a = ap.parse_args()
    d = a.date
    doc = json.loads((ROOT / "data" / "screen" / f"change_driver_{d}.json").read_text(encoding="utf-8"))
    cards = doc["cards"]
    tiers = doc["分档明细"]

    def card_rows(codes, limit=30):
        rows = ""
        for c in codes[:limit]:
            v = cards[c]; m = v.get("指标", {})
            flag = v["常识核对"][0]
            fc = "c-ok" if flag.startswith("通过") else "c-no"
            rows += (f"<tr><td class='mono'>{esc(c)}</td><td class='mono' style='font-size:10px'>{esc(v.get('数据方案') or '')}</td>"
                     f"<td class='num'><b>{r1(v.get('变化证据得分'))}</b></td>"
                     f"<td class='num'>{r1(v.get('数据覆盖率'))}</td><td>{esc(v.get('结论可信度'))}</td>"
                     f"<td class='num'>{r1(m.get('利润同比%'))}/{r1(m.get('利润加速度(pp)'))}</td>"
                     f"<td class='num'>{r1(m.get('营收同比%'))}/{r1(m.get('营收加速度(pp)'))}</td>"
                     f"<td class='num'>{r1(m.get('毛利率同比(pp)'))}·{esc(m.get('毛利率趋势') or '')}</td>"
                     f"<td class='num'>{r1(m.get('OCF同比%'))}/{r1(m.get('OCF加速度(pp)'))}</td>"
                     f"<td>{'是' if m.get('由亏转盈') else ''}</td>"
                     f"<td class='{fc}'>{esc(flag[:14])}</td></tr>")
        return rows

    high = card_rows(sorted(tiers["高(≥0.75)"], key=lambda c: -(cards[c].get("变化证据得分") or 0)))
    mid = card_rows(sorted(tiers["中(0.5-0.75)"], key=lambda c: -(cards[c].get("变化证据得分") or 0)), 15)

    html = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>变化驱动层·4根柱子 · {d}</title>
<style>
body{{font-family:"Microsoft YaHei","PingFang SC",sans-serif;line-height:1.7;color:#1A1A1A;background:#F5F6F8;max-width:1220px;margin:0 auto;padding:16px 14px 60px}}
h2{{font-size:16px;color:#12324E;border-left:5px solid #12324E;padding-left:10px;margin:20px 0 8px}}
.hdr{{background:#12324E;color:#fff;border-radius:10px;padding:14px 18px;margin-bottom:12px}}
.hdr .sub{{font-size:13px;opacity:.92;margin-top:4px}}
table{{border-collapse:collapse;width:100%;font-size:11.6px;background:#fff;margin:8px 0}}
th,td{{border:1px solid #DDE3E8;padding:5px 6px;text-align:left;vertical-align:top}}
th{{background:#12324E;color:#fff}} .mono{{font-family:Consolas,monospace;font-size:11px;color:#33414D}} .num{{text-align:right;font-family:Consolas,monospace}}
.c-ok{{color:#1E7A45;font-weight:700}} .c-no{{color:#A3231F;font-weight:700}}
.warn{{background:#FBF0E7;border:1px solid #C99A6B;border-radius:8px;padding:10px 14px;margin:8px 0;color:#6B3E00;font-size:12.5px}}
.note{{background:#EEF4F8;border:1px solid #B9D3E6;border-radius:7px;padding:8px 12px;font-size:12.5px;margin:8px 0;color:#12324E}}
.scroll{{overflow-x:auto}}
</style></head><body>
<div class="hdr"><div style="font-size:20px;font-weight:800">📊 变化驱动层：1根柱子 → 4根</div>
<div class="sub">{d} ｜ ★只算不筛选·不出名单·不给买卖建议·不改尺 ｜ 入围 {doc['入围只数']}只·有PIT数据 {doc['有PIT数据']}只</div>
<div class="sub">4根柱子(各含 同比+加速度)：利润 / 营收 / 毛利率(pp+趋势) / 经营现金流 ＋ 由亏转盈 ｜ 数据源：当日PIT存档(8xxx/11xxx原样)</div></div>

<div class="warn"><b>★F-07 双轴五铁律(已落地)：</b>①缺失不计0分(不入分母) ②缺失权重不静默转市场确认 ③不同覆盖率不直接排名(下方按档分列) ④覆盖率&lt;0.5→"无法充分判定/观察池" ⑤禁"得分×覆盖率"合并。每卡三项：<b>变化证据得分 / 数据覆盖率 / 结论可信度</b>。<br>
<b>★F-08 分层：</b>本表仅【基本面变化层】(利润/营收/毛利率/OCF加速度+由亏转盈)·不与市场确认/先行/扩散层重复计分。<b>真自由现金流：待查(capex未解出·不采信)。</b></div>

<div class="note">按覆盖率分档(不跨档排名)：高(≥0.75) <b>{doc['按覆盖率分档(不跨档排名)']['高(≥0.75)']}</b>只 · 中(0.5-0.75) <b>{doc['按覆盖率分档(不跨档排名)']['中(0.5-0.75)']}</b>只 · 低/无法充分判定 <b>{doc['按覆盖率分档(不跨档排名)']['低/无法充分判定(<0.5)']}</b>只 ｜ 常识核对待查 {len(doc['常识核对待查'])}只</div>

<h2>高覆盖率档(≥0.75·前30·按变化证据得分)</h2>
<div class="scroll"><table>
<tr><th>代码</th><th>方案</th><th>变化证据得分</th><th>覆盖率</th><th>可信度</th><th>利润同比/加速</th><th>营收同比/加速</th><th>毛利率pp·趋势</th><th>OCF同比/加速</th><th>由亏转盈</th><th>常识</th></tr>
{high}
</table></div>

<h2>中覆盖率档(0.5-0.75·前15·不与高档同列排名)</h2>
<div class="scroll"><table>
<tr><th>代码</th><th>方案</th><th>变化证据得分</th><th>覆盖率</th><th>可信度</th><th>利润同比/加速</th><th>营收同比/加速</th><th>毛利率pp·趋势</th><th>OCF同比/加速</th><th>由亏转盈</th><th>常识</th></tr>
{mid}
</table></div>
{'<div class="warn"><b>常识核对待查：</b>' + esc('、'.join(doc['常识核对待查'][:30])) + '</div>' if doc['常识核对待查'] else '<div class="note">常识核对：无明显异常值(无龙头毛利率=0之类)。</div>'}

<div class="hdr" style="text-align:center;background:#fff;color:#12324E;border:1px solid #DDE3E8"><b>本轮只把变化驱动扩到4根并按F-07/F-08输出·未筛选未出名单。请架构师核对合理性后再据此设计标准。</b><br>
<span class="mono">实物：data/screen/change_driver_{d}.json</span></div>
</body></html>"""
    out = ROOT / "00_请先看这里" / f"变化驱动层4根柱子_{d}.html"
    out.write_text(html, encoding="utf-8")
    raw = out.read_bytes()
    print("wrote", out.name, len(raw), "字节 · EFBFBD=", raw.count(b"\xef\xbf\xbd"))


if __name__ == "__main__":
    main()
