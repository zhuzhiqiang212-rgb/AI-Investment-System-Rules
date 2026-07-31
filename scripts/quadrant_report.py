#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""四象限分池 HTML报告·F-11。用法: python scripts/quadrant_report.py --date 20260721"""
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
    q = json.loads((S / f"quadrant_{d}.json").read_text(encoding="utf-8"))
    cards = q["cards"]; dist = q["象限分布"]

    def rowset(codes, limit=25):
        h = ""
        for c in codes[:limit]:
            r = cards[c]
            fq = r["四项象限"]
            div = "⚠分歧" if r["象限分歧"] else ""
            fl = r["常识核对"][0] if r.get("常识核对") else ""
            fc = "c-no" if (fl and not str(fl).startswith("通过")) else ""
            h += (f"<tr><td class='mono'>{esc(c)}</td><td>{esc(r.get('名称行业') or '')[:10]}</td>"
                  f"<td class='num'><b>{r1(r['变化证据得分'])}</b></td><td class='num'>{r1(r['数据覆盖率'])}</td><td>{esc(r['结论可信度'])[:4]}</td>"
                  f"<td class='num'>{r1(r['利润同比%'])}/{r1(r['利润加速度pp'])}</td>"
                  f"<td class='mono'>利{fq['利润']}营{fq['营收']}现{fq['OCF']}毛{fq['毛利率']}</td>"
                  f"<td class='{fc}'>{esc(div)}{esc(str(fl)[:10]) if fc else ''}</td></tr>")
        return h

    order = q["各象限内排序"]
    main20 = rowset(q["主池①前20"], 20)
    q2 = rowset(order.get("②", []), 20)
    q3 = rowset(order.get("③", []), 20)

    html = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>变化驱动·四象限分池 · {d}</title>
<style>
body{{font-family:"Microsoft YaHei","PingFang SC",sans-serif;line-height:1.7;color:#1A1A1A;background:#F5F6F8;max-width:1180px;margin:0 auto;padding:16px 14px 60px}}
h2{{font-size:16px;color:#12324E;border-left:5px solid #12324E;padding-left:10px;margin:20px 0 8px}}
.hdr{{background:#12324E;color:#fff;border-radius:10px;padding:14px 18px;margin-bottom:12px}}
.hdr .sub{{font-size:13px;opacity:.92;margin-top:4px}}
table{{border-collapse:collapse;width:100%;font-size:11.6px;background:#fff;margin:8px 0}}
th,td{{border:1px solid #DDE3E8;padding:5px 6px;text-align:center;vertical-align:middle}}
th{{background:#12324E;color:#fff}} .mono{{font-family:Consolas,monospace;font-size:11px;color:#33414D}} .num{{text-align:right;font-family:Consolas,monospace}}
.c-no{{color:#A3231F;font-weight:700}}
.quad{{display:flex;gap:10px;flex-wrap:wrap;margin:8px 0}}
.qbox{{flex:1;min-width:220px;border-radius:9px;padding:12px 14px;color:#fff}}
.q1{{background:#1E7A45}} .q2{{background:#12324E}} .q3{{background:#6B5200}} .q4{{background:#8A2A26}} .q0{{background:#5A6673}}
.qbox .n{{font-size:26px;font-weight:800}}
.warn{{background:#FBF0E7;border:1px solid #C99A6B;border-radius:8px;padding:10px 14px;margin:8px 0;color:#6B3E00;font-size:12.5px}}
.big{{background:#EEF4F8;border:1px solid #B9D3E6;border-radius:8px;padding:12px 16px;margin:8px 0;color:#12324E;font-size:14px;font-weight:700}}
.scroll{{overflow-x:auto}}
</style></head><body>
<div class="hdr"><div style="font-size:20px;font-weight:800">🎯 变化驱动 · 四象限分池（F-11丙案）</div>
<div class="sub">{d} ｜ ★只算不筛选·不出名单·不给买卖建议·不改尺·<b>四象限分开排序·不合并总分·不同象限不可比</b> ｜ 入围 {q['入围']}只</div>
<div class="sub">以「利润」为主判据(同比×加速度)。为什么四象限：纯按加速度排会把"从很差变没那么差"排在"从很好变没那么好"前面→推向K型下支·与G-05冲突。</div></div>

<div class="quad">
<div class="qbox q1"><div>① 强者加速（主池）</div><div class="n">{dist['①']}</div><div class="mono">同比+ 加速度+</div></div>
<div class="qbox q2"><div>② 强者减速（副池·英伟达在此）</div><div class="n">{dist['②']}</div><div class="mono">同比+ 加速度-</div></div>
<div class="qbox q3"><div>③ 困境反转（副池）</div><div class="n">{dist['③']}</div><div class="mono">同比- 加速度+</div></div>
<div class="qbox q4"><div>④ 持续恶化（排除）</div><div class="n">{dist['④']}</div><div class="mono">同比- 加速度-</div></div>
<div class="qbox q0"><div>— 无法判定象限</div><div class="n">{dist['—']}</div><div class="mono">缺同比或加速度</div></div>
</div>

<div class="big">明确回答：432只里 <b>象限①(强者加速·主池) {dist['①']}只</b> · ②强者减速 {dist['②']}只 · ③困境反转 {dist['③']}只 · ④持续恶化(排除) {dist['④']}只 · 无法判定 {dist['—']}只。<br>
校验：英伟达→<b>②强者减速</b>(利润+64.75%/加速度−80.15·不进主池)；特斯拉→<b>③困境反转</b>(利润−46.11%/加速度+6.12)。二者<b>分属不同副池·不被放在一起排名</b>——纯加速度排序会把特斯拉排在英伟达前面(推向脆弱端)，四象限避免了这点。</div>

<h2>主池①（强者加速·前20·象限内按变化证据得分排序）</h2>
<div class="scroll"><table>
<tr><th>代码</th><th>行业</th><th>变化得分</th><th>覆盖</th><th>可信</th><th>利润同比/加速</th><th>四项象限(利/营/现/毛)</th><th>标注</th></tr>
{main20}
</table></div>

<h2>副池②（强者减速·前20·仍高速但增速回落·可小仓位·不进主排名）</h2>
<div class="scroll"><table>
<tr><th>代码</th><th>行业</th><th>变化得分</th><th>覆盖</th><th>可信</th><th>利润同比/加速</th><th>四项象限</th><th>标注</th></tr>
{q2}
</table></div>

<h2>副池③（困境反转·前20·同比负但加速度转正·可小仓位·不进主排名）</h2>
<div class="scroll"><table>
<tr><th>代码</th><th>行业</th><th>变化得分</th><th>覆盖</th><th>可信</th><th>利润同比/加速</th><th>四项象限</th><th>标注</th></tr>
{q3}
</table></div>

<div class="warn"><b>象限分歧 {q['象限分歧数']}只：</b>四项指标(利润/营收/OCF/毛利率)落在不同象限的股票（如英伟达 利润②但毛利率④）。已在每张卡"四项象限"列逐只标明·完整清单见 quadrant_{d}.json.象限分歧清单。四象限分开排序不合并·②③副池不进主排名·④{dist['④']}只直接排除。capex/真FCF仍待查·不采信。</div>

<div class="hdr" style="text-align:center;background:#fff;color:#12324E;border:1px solid #DDE3E8"><b>本轮只做四象限分池·未筛选未出名单·未合并总分·②③④按规矩处理。请架构师核对后再设计标准。</b><br>
<span class="mono">实物：data/screen/quadrant_{d}.json（含各象限内排序+象限分歧清单+主池①完整名单）</span></div>
</body></html>"""
    out = ROOT / "00_请先看这里" / f"变化驱动四象限分池_{d}.html"
    out.write_text(html, encoding="utf-8")
    raw = out.read_bytes()
    print("wrote", out.name, len(raw), "字节 · EFBFBD=", raw.count(b"\xef\xbf\xbd"))


if __name__ == "__main__":
    main()
