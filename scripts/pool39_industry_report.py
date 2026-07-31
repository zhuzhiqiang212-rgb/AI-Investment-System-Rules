#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主池39·行业分布 HTML报告(F-13)。用法: python scripts/pool39_industry_report.py --date 20260721"""
import argparse, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "data" / "screen"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def r1(v):
    return round(v, 1) if isinstance(v, (int, float)) else ("" if v is None else v)


ST = {"已确认": "s1", "正在确认": "s2", "未确认": "s3", None: "s0", "状态数据不足": "s0"}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="20260721"); a = ap.parse_args()
    d = a.date
    j = json.loads((S / f"pool39_industry_{d}.json").read_text(encoding="utf-8"))
    bd = j["分歧false拆解"]; ind_rows = j["行业分布(按加速占比降序)"]; roster = j["主池39名单"]
    state_ind = j["按市场确认状态的行业分布"]; ztop = j["正在确认集中度top"]
    top3 = j["加速占比最高三(行业≥3只·更代表趋势)"]

    irows = "".join(f"<tr><td>{esc(r['行业'])}</td><td class='num'>{r['进主池39']}</td><td class='num'>{r['该行业432总数']}</td>"
                    f"<td class='num'><b>{r['行业内加速占比%']}</b></td><td class='mono'>{esc('、'.join(r['成员']))}</td></tr>"
                    for r in ind_rows)
    rrows = "".join(f"<tr><td class='mono'>{esc(x['code'])}</td><td>{esc(x['行业'])[:12]}</td>"
                    f"<td class='{ST.get(x['市场确认状态'],'s0')}'>{esc(x['市场确认状态'])}</td><td class='num'>{r1(x['变化证据得分'])}</td></tr>"
                    for x in roster)

    def state_block(st):
        blk = state_ind.get(st)
        if not blk:
            return f"<div class='sbox'><b>{esc(st)}（0只）</b></div>"
        rows = "".join(f"<tr><td>{esc(r['行业'])}</td><td class='num'>{r['只数']}</td><td class='mono'>{esc('、'.join(r['成员']))}</td></tr>" for r in blk["行业分布"])
        return (f"<div class='sbox'><b>{esc(st)}（{blk['只数']}只）· 行业分布</b>"
                f"<table><tr><th>行业</th><th>只数</th><th>成员</th></tr>{rows}</table></div>")

    html = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>主池39·行业分布 · {d}</title>
<style>
body{{font-family:"Microsoft YaHei","PingFang SC",sans-serif;line-height:1.7;color:#1A1A1A;background:#F5F6F8;max-width:1200px;margin:0 auto;padding:16px 14px 60px}}
h2{{font-size:16px;color:#12324E;border-left:5px solid #12324E;padding-left:10px;margin:20px 0 8px}}
.hdr{{background:#12324E;color:#fff;border-radius:10px;padding:14px 18px;margin-bottom:12px}} .hdr .sub{{font-size:13px;opacity:.92;margin-top:4px}}
table{{border-collapse:collapse;width:100%;font-size:11.8px;background:#fff;margin:8px 0}}
th,td{{border:1px solid #DDE3E8;padding:5px 7px;text-align:center;vertical-align:middle}}
th{{background:#12324E;color:#fff}} .mono{{font-family:Consolas,monospace;font-size:10.5px;color:#33414D}} .num{{text-align:right;font-family:Consolas,monospace}}
.s1{{color:#1E7A45;font-weight:700}} .s2{{color:#12324E;font-weight:800;background:#EAF5EF}} .s3{{color:#A3231F;font-weight:700}} .s0{{color:#5A6673}}
.warn{{background:#FBF0E7;border:1px solid #C99A6B;border-radius:8px;padding:10px 14px;margin:8px 0;color:#6B3E00;font-size:12.5px}}
.big{{background:#EEF4F8;border:1px solid #B9D3E6;border-radius:8px;padding:12px 16px;margin:8px 0;color:#12324E;font-size:13.5px;font-weight:700}}
.gold{{background:#FBF4E0;border:2px solid #B8860B;border-radius:9px;padding:10px 14px;margin:8px 0;color:#6B5200;font-weight:700}}
.sbox{{background:#fff;border:1px solid #DDE3E8;border-radius:8px;padding:8px 12px;margin:8px 0}}
.scroll{{overflow-x:auto}}
</style></head><body>
<div class="hdr"><div style="font-size:20px;font-weight:800">🏭 主池39 · 行业分布（F-13）</div>
<div class="sub">{d} ｜ ★只算不筛选·不出买卖建议·不改尺·不合并总分·不锚死名单(名单每日现算·总则六)</div></div>

<div class="warn"><b>★F-13 口径堵漏（正式定义）：</b>主池 = <b>分歧false 且 象限①(强者加速)</b>。「分歧false」只说明四项落<u>同一</u>象限·没说哪个象限——四项一致地<b>恶化</b>(④)也是false。
分歧false共 <b>{j['分歧false总数']}</b> 只，拆开＝<b>①真强者 {bd['①强者加速(真主池)']}</b> / ②强者减速 {bd['②强者减速']} / <b>④持续恶化 {bd['④持续恶化(四项一致地恶化·也是false)']}</b>(四项一致在恶化·也false·应排除) / 无法判定 {bd['—无法判定象限(数据不足)']}(数据不足)。<b>只报89会让人以为有89个强者·实际只有 {bd['①强者加速(真主池)']} 个。</b></div>

<div class="big">答①：主池39只落在 <b>{j['行业数']}</b> 个行业。行业内加速占比(进主池÷该行业432总数)最高三个(行业≥3只)：
{esc(' · '.join(f"{x['行业']} {x['行业内加速占比%']}%({x['进主池39']}/{x['该行业432总数']})" for x in top3))}。</div>

<div class="gold">答②：「正在确认」21只集中在——<b>{esc('、'.join(f"{k['行业']}{k['只数']}只" for k in ztop[:5]))}</b>。
最集中的一个是 <b>「{esc(ztop[0]['行业'])}」占 {ztop[0]['只数']} 只</b>（占正在确认的 {round(ztop[0]['只数']/21*100)}%）。<br>
<span style="font-size:12px;font-weight:400">★意义：黄金 在"行业内加速占比"也居首(6/12=50%)，且这 6 只全在"正在确认"——<b>整个黄金板块在基本面加速、而市场尚未充分确认</b>，比 21 家孤立公司有意义得多（正是您说的"整行业刚开始被市场发现"）。</span></div>

<h2>行业分布（按行业内加速占比 从高到低）</h2>
<div class="scroll"><table><tr><th>行业</th><th>进主池39</th><th>该行业432总数</th><th>行业内加速占比%</th><th>成员</th></tr>{irows}</table></div>
<div class="warn">{esc(j.get('小样本提示',''))}（农业投入品2/2、电子分销1/1 等100%是小样本噪声·看趋势以≥3只版为准）。</div>

<h2>按市场确认状态切行业（F-12三状态·正在确认21/已确认15/未确认3）</h2>
{state_block("正在确认")}
{state_block("已确认")}
{state_block("未确认")}

<h2>主池39完整名单（代码+行业+状态+变化证据得分·按得分排序）</h2>
<div class="scroll"><table><tr><th>代码</th><th>行业</th><th>市场确认状态</th><th>变化证据得分</th></tr>{rrows}</table></div>

<div class="hdr" style="text-align:center;background:#fff;color:#12324E;border:1px solid #DDE3E8"><b>本轮只做主池口径堵漏(89→39)+39只行业分布+按状态切行业·未筛选未出固定名单·未合并总分。请架构师核对后再设计标准。</b><br>
<span class="mono">实物：data/screen/pool39_industry_{d}.json</span></div>
</body></html>"""
    out = ROOT / "00_请先看这里" / f"主池39行业分布_{d}.html"
    out.write_text(html, encoding="utf-8")
    raw = out.read_bytes()
    print("wrote", out.name, len(raw), "字节 · EFBFBD=", raw.count(b"\xef\xbf\xbd"))


if __name__ == "__main__":
    main()
