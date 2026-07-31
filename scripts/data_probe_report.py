#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据能力探针 · HTML报告(指标×10只矩阵+样例值+覆盖率+A组vsB组结论)。
用法：python scripts/data_probe_report.py"""
import json, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def cls(v):
    v = str(v)
    if v.startswith("能"):
        return "c-ok"
    if v.startswith("部分"):
        return "c-mid"
    return "c-no"


def main():
    d = json.loads((ROOT / "data" / "screen" / "data_probe_20260721.json").read_text(encoding="utf-8"))
    sample = d["样本"]; codes = list(sample.keys())
    matrix = d["能力矩阵_指标x10只"]
    metrics = list(matrix[codes[0]].keys())
    ex = d["实际样例值"]

    # 矩阵表
    head = "<tr><th>指标</th>" + "".join(f"<th>{esc(sample[c])}<br><span class='mono'>{esc(c)}</span></th>" for c in codes) + "</tr>"
    body = ""
    for m in metrics:
        row = f"<tr><td><b>{esc(m)}</b></td>"
        for c in codes:
            v = matrix[c][m]
            row += f"<td class='{cls(v)}'>{esc(v)}</td>"
        body += row + "</tr>"

    # 样例值(挑关键项)
    sx = ""
    for c in codes:
        g = ex[c].get("A2_利润同比", {})
        rel = ex[c].get("B6_相对大盘超额%", {})
        er = ex[c].get("A5B10_财报价格反应", {})
        sx += (f"<tr><td class='mono'>{esc(c)}</td><td>{esc(sample[c])}</td>"
               f"<td class='num'>{g.get('净利润(归母)同比')}</td>"
               f"<td class='num'>{g.get('营业利润同比')}</td>"
               f"<td class='num'>{ex[c].get('B8_距52周高%')}</td>"
               f"<td class='num'>{ex[c].get('B9_上涨量比下跌量')}</td>"
               f"<td class='num'>{(rel or {}).get('3月')}</td>"
               f"<td class='num'>{(er or {}).get('财报次数')}</td>"
               f"<td class='mono'>{esc((er or {}).get('最近财报发布日',''))}</td>"
               f"<td class='num'>{(er or {}).get('财报后首日跳空%')}</td></tr>")

    # 覆盖率
    cov = d["覆盖率"]
    cr = "".join(f"<tr><td>{esc(k)}</td><td class='num'>{v['能']}</td><td class='num'>{v['部分']}</td>"
                 f"<td class='num'>{v['不能']}</td><td class='num'>{v['可得率%']}</td></tr>" for k, v in cov.items())

    cgroup = d["C组_可信度"]
    crows = "".join(f"<tr><td><b>{esc(k)}</b></td><td>{esc(v)}</td></tr>" for k, v in cgroup.items())
    concl = d["A组vsB组结论"]["判断"]
    a_sum = esc("；".join(f"{k}={v['可得率%']}%" for k, v in d["A组vsB组结论"]["A组(基本面变化)"].items()))
    b_sum = esc("；".join(f"{k}={v['可得率%']}%" for k, v in d["A组vsB组结论"]["B组(市场变化)"].items()))

    html = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>数据能力探针报告 · 2026-07-21</title>
<style>
body{{font-family:"Microsoft YaHei","PingFang SC",sans-serif;line-height:1.7;color:#1A1A1A;background:#F5F6F8;max-width:1240px;margin:0 auto;padding:16px 14px 60px}}
h2{{font-size:17px;color:#12324E;border-left:5px solid #12324E;padding-left:10px;margin:22px 0 8px}}
.hdr{{background:#12324E;color:#fff;border-radius:10px;padding:14px 18px;margin-bottom:12px}}
.hdr .sub{{font-size:13px;opacity:.92;margin-top:4px}}
table{{border-collapse:collapse;width:100%;font-size:11.8px;background:#fff;margin:8px 0}}
th,td{{border:1px solid #DDE3E8;padding:5px 7px;text-align:left;vertical-align:top}}
th{{background:#12324E;color:#fff}} .mono{{font-family:Consolas,monospace;font-size:11px;color:#33414D}} .num{{text-align:right;font-family:Consolas,monospace}}
.c-ok{{background:#E4F3EA;color:#1E7A45;font-weight:700}} .c-mid{{background:#FBF3E3;color:#6B5200;font-weight:700}} .c-no{{background:#FBECEC;color:#A3231F;font-weight:700}}
.note{{background:#EEF4F8;border:1px solid #B9D3E6;border-radius:7px;padding:8px 12px;font-size:12.5px;margin:8px 0;color:#12324E}}
.big{{background:#FBF0E7;border:1px solid #C99A6B;border-radius:8px;padding:12px 16px;margin:10px 0;color:#6B3E00;font-size:13.5px}}
.scroll{{overflow-x:auto}}
</style></head><body>
<div class="hdr"><div style="font-size:20px;font-weight:800">🔬 数据能力探针报告（先探针·再冻结标准）</div>
<div class="sub">2026-07-21 ｜ 生成 {esc(d.get('生成时间'))} ｜ ★只探数据能力·不筛选·不排序·不出名单·不给买卖建议·不改尺·不自调参数</div>
<div class="sub">样本10只(美日·含点名5只盈利主力)：{esc('、'.join(f'{v}{k}' for k,v in sample.items()))}</div></div>

<div class="note">目的：在冻结新筛选标准前，先摸清每个指标到底能不能算——避免第三次"先设计标准、跑完才发现数据不支持"。大盘基准 US=SPY、JP=1329ETF（{esc(d.get('index_可得'))}）。</div>

<h2>① 能力矩阵：指标 × 10只 × 能/部分/不能</h2>
<div class="scroll"><table>{head}{body}</table></div>
<div class="note">绿=能取到真值 · 黄=部分/需自算 · 红=不能。"不能"原因写在指标名括号内。</div>

<h2>③ 实际样例值（供架构师核对合理性·防"取到了但值是假的"）</h2>
<div class="scroll"><table>
<tr><th>代码</th><th>名称</th><th>净利同比%</th><th>营业利润同比%</th><th>距52周高%</th><th>涨量/跌量</th><th>相对大盘3月%</th><th>财报次数</th><th>最近财报日</th><th>财报后跳空%</th></tr>
{sx}
</table></div>

<h2>④ 覆盖率（各指标在10只中的可得率）</h2>
<div class="scroll"><table>
<tr><th>指标</th><th>能</th><th>部分</th><th>不能</th><th>可得率%</th></tr>
{cr}
</table></div>

<h2>C组 · 数据可信度（17项中的12–17）</h2>
<div class="scroll"><table><tr><th>项</th><th>结论</th></tr>{crows}</table></div>

<h2>⑤ 结论：A组大面积不可得时，B组能撑起多少"变化驱动"</h2>
<div class="big">{esc(concl)}</div>
<div class="note">A组(基本面变化)：{a_sum}<br>
B组(市场变化)：{b_sum}</div>

<div class="hdr" style="text-align:center;background:#fff;color:#12324E;border:1px solid #DDE3E8"><b>本轮只探能力·未筛选未出名单。请架构师据此重新设计标准→送GPT→拍板→再扫描。</b><br>
<span class="mono">实物：data/screen/data_probe_20260721.json（含全部样例值与逐项判定）</span></div>
</body></html>"""
    out = ROOT / "00_请先看这里" / "数据能力探针报告_20260721.html"
    out.write_text(html, encoding="utf-8")
    raw = out.read_bytes()
    print("wrote", out.name, len(raw), "bytes · EFBFBD=", raw.count(b"\xef\xbf\xbd"))


if __name__ == "__main__":
    main()
