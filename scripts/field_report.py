#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""field_id 映射+十项核验+10只样本 → HTML报告。用法: python scripts/field_report.py"""
import json, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "data" / "screen"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def r1(v):
    return round(v, 1) if isinstance(v, (int, float)) else v


def main():
    fm = json.loads((S / "field_map_20260721.json").read_text(encoding="utf-8"))
    fv = json.loads((S / "field_verify_20260721.json").read_text(encoding="utf-8"))
    fs = json.loads((S / "field_sample_20260721.json").read_text(encoding="utf-8"))["samples"]

    def maptbl(d):
        return "".join(f"<tr><td class='mono'>{esc(k)}</td><td>{esc(v['科目'])}</td><td>{esc(v['单位'])}</td>"
                       f"<td>{esc(v['来源'])}</td><td class='mono' style='font-size:10.5px'>{esc(v['依据'])}</td></tr>"
                       for k, v in d.items())
    inc8 = maptbl(fm["利润表_8xxx_US_GAAP"]); cf8 = maptbl(fm["现金流量表_8xxx_US_GAAP"])
    inc11 = maptbl(fm["利润表_11xxx_JGAAP"]); cf11 = maptbl(fm["现金流量表_11xxx_JGAAP"])

    vrows = "".join(f"<tr><td><b>{esc(k)}</b></td><td>{esc(v)}</td></tr>" for k, v in fv.items() if not k.startswith("_"))

    srows = ""
    for c, d in fs.items():
        if d.get("error"):
            srows += f"<tr><td class='mono'>{esc(c)}</td><td colspan='9'>{esc(d['error'])}</td></tr>"; continue
        flag = d["常识核对"][0]
        fc = "c-ok" if flag.startswith("通过") else "c-no"
        srows += (f"<tr><td class='mono'>{esc(c)}</td><td>{esc(d['名称'])}</td>"
                  f"<td class='mono' style='font-size:10px'>{esc(d.get('字段方案',''))[:5]}</td>"
                  f"<td class='num'>{r1(d.get('营收同比%(yoy)'))}</td>"
                  f"<td class='num'>{d.get('毛利率%')}</td>"
                  f"<td class='num'>{d.get('毛利率同比(pp·两年FY算)')}</td>"
                  f"<td class='num'>{r1(d.get('净利同比%(yoy)'))}</td>"
                  f"<td class='num'>{r1(d.get('经营现金流同比%(yoy)'))}</td>"
                  f"<td class='num'>—</td>"
                  f"<td class='{fc}'>{esc(flag[:16])}</td></tr>")

    html = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>field_id映射+十项核验+样本 · 2026-07-21</title>
<style>
body{{font-family:"Microsoft YaHei","PingFang SC",sans-serif;line-height:1.7;color:#1A1A1A;background:#F5F6F8;max-width:1200px;margin:0 auto;padding:16px 14px 60px}}
h2{{font-size:16px;color:#12324E;border-left:5px solid #12324E;padding-left:10px;margin:20px 0 8px}}
.hdr{{background:#12324E;color:#fff;border-radius:10px;padding:14px 18px;margin-bottom:12px}}
.hdr .sub{{font-size:13px;opacity:.92;margin-top:4px}}
table{{border-collapse:collapse;width:100%;font-size:12px;background:#fff;margin:8px 0}}
th,td{{border:1px solid #DDE3E8;padding:5px 7px;text-align:left;vertical-align:top}}
th{{background:#12324E;color:#fff}} .mono{{font-family:Consolas,monospace;font-size:11px;color:#33414D}} .num{{text-align:right;font-family:Consolas,monospace}}
.c-ok{{color:#1E7A45;font-weight:700}} .c-no{{color:#A3231F;font-weight:700}}
.warn{{background:#FBF0E7;border:1px solid #C99A6B;border-radius:8px;padding:10px 14px;margin:8px 0;color:#6B3E00;font-size:13px}}
.big{{background:#EEF4F8;border:1px solid #B9D3E6;border-radius:8px;padding:12px 16px;margin:8px 0;color:#12324E;font-size:14px;font-weight:700}}
.scroll{{overflow-x:auto}}
</style></head><body>
<div class="hdr"><div style="font-size:20px;font-weight:800">🔑 field_id 映射 ＋ 十项核验 ＋ 10只样本实算</div>
<div class="sub">2026-07-21 ｜ ★只解字段与核验·不筛选·不排序·不出名单·不给买卖建议·不改尺</div>
<div class="sub">映射全部为【反推】(AAPL+丰田 交叉验证 8xxx；东京电子+日立 交叉验证 11xxx)·非富途官方字段表(本OpenD版 display_name 返回空)</div></div>

<div class="big">一句话：变化驱动从【1根柱子(利润同比)】→【4根(营收/毛利率/净利/OCF 同比)】；<br>
其中【0根】可直接用于严格无未来信息回测（须联结真实发布日 earnings_price_move + 不能排除财报重述）；修正后可做【带发布日滞后的准回测】。</div>

<div class="warn"><b>★两套字段方案(易串号)：</b>US_GAAP/IFRS 用 <b>8xxx</b>；日股本土 JGAAP(NonUS_GAAP·东京电子/日立/三菱重工) 用 <b>11xxx</b>，同一含义 field_id 不同。丰田虽日股但报 US_GAAP 故走 8xxx。混用会串号——这是本轮关键发现之一。</div>

<h2>① 映射表 · 8xxx（US_GAAP/IFRS）</h2>
<div class="scroll"><table><tr><th>field_id</th><th>科目(反推)</th><th>单位</th><th>来源</th><th>交叉验证依据</th></tr>
<tr><td colspan='5' style='background:#F2F4F7'><b>利润表(statement_type=1)</b></td></tr>{inc8}
<tr><td colspan='5' style='background:#F2F4F7'><b>现金流量表(statement_type=3)</b></td></tr>{cf8}</table></div>

<h2>① 映射表 · 11xxx（JGAAP·NonUS_GAAP）</h2>
<div class="scroll"><table><tr><th>field_id</th><th>科目(反推)</th><th>单位</th><th>来源</th><th>交叉验证依据</th></tr>
<tr><td colspan='5' style='background:#F2F4F7'><b>利润表</b></td></tr>{inc11}
<tr><td colspan='5' style='background:#F2F4F7'><b>现金流量表</b></td></tr>{cf11}</table></div>
<div class="warn"><b>capex/真自由现金流：</b>{esc(fm['capex_资本开支']['状态'])}</div>

<h2>② 十项核验（GPT总控11 要求·第4/5/6项是回测可用性关键）</h2>
<div class="scroll"><table><tr><th>项</th><th>结论</th></tr>{vrows}</table></div>

<h2>③ 10只样本实算（供架构师核对合理性·已做常识核对·防"取到但值假")</h2>
<div class="scroll"><table>
<tr><th>代码</th><th>名称</th><th>方案</th><th>营收同比%</th><th>毛利率%</th><th>毛利率同比pp</th><th>净利同比%</th><th>OCF同比%</th><th>真FCF</th><th>常识核对</th></tr>
{srows}
</table></div>
<div class="warn">常识核对：龙头公司毛利率均在合理区间(礼来83%/英伟达71%/东京电子45%/戴尔20%·联合健康18%保险低毛利)·无"毛利率=0.0"假值(已避开信越/发那科同类陷阱)。真FCF列全为"—"：capex未确认·不采信。</div>

<h2>④⑤ 覆盖率 ＋ 明确回答</h2>
<div class="big">解开映射后 A组"变化驱动"在10只中的可得率：营收同比 <b>10/10</b>·毛利率同比 <b>9/10</b>(美光仅1个FY期)·经营现金流同比 <b>10/10</b>·净利同比 10/10·真自由现金流 <b>0/10</b>(capex待查)。<br><br>
「变化驱动从<b>一根柱子变成四根</b>（营收/毛利率/净利/OCF 同比）；其中<b>可用于严格无未来信息回测的是 0 根</b>——因 statements 返回的是当前(可能被重述)值、且期末日≠发布日；<b>联结 earnings_price_move 的真实发布日、并接受不能排除重述之后，这四根可做"带发布日滞后的准回测"。</b>capex 未确认，真自由现金流本轮不可用。」</div>

<div class="hdr" style="text-align:center;background:#fff;color:#12324E;border:1px solid #DDE3E8"><b>本轮只解字段与核验·未筛选未出名单。映射均为反推·请架构师抽样复核后再据此设计标准→送GPT→拍板。</b><br>
<span class="mono">实物：data/screen/field_map / field_verify / field_sample _20260721.json</span></div>
</body></html>"""
    out = ROOT / "00_请先看这里" / "字段映射与核验报告_20260721.html"
    out.write_text(html, encoding="utf-8")
    raw = out.read_bytes()
    print("wrote", out.name, len(raw), "字节 · EFBFBD=", raw.count(b"\xef\xbf\xbd"))


if __name__ == "__main__":
    main()
