#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""市场确认·状态标记 HTML报告(F-12·不淘汰)。用法: python scripts/pool_state_report.py --date 20260721"""
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
    ps = json.loads((S / f"pool_state_{d}.json").read_text(encoding="utf-8"))
    cards = ps["cards"]; order = ps["各状态内排序"]
    dist = ps["三状态数量_全89"]; dist39 = ps["三状态数量_真主池39(①同向加速)"]

    def tbl(codes, limit=60):
        h = ""
        for c in codes[:limit]:
            r = cards[c]; acc = r["四项加速"]; rel = r["相对大盘1/3/6月%"]
            susp = "⚠基数" if r.get("基数效应嫌疑") else ""
            anom = "⚠异常" if r.get("异常字段") else ""
            h += (f"<tr><td class='mono'>{esc(c)}</td><td class='mono' style='font-size:10px'>{esc(r['共同象限'])}</td><td>{esc(r.get('行业') or '')[:8]}</td>"
                  f"<td class='num'><b>{r1(r['变化证据得分'])}</b></td>"
                  f"<td class='num'>{r1(acc.get('利润加速pp'))}/{r1(acc.get('营收加速pp'))}/{r1(acc.get('OCF加速pp'))}/{r1(acc.get('毛利率加速pp'))}</td>"
                  f"<td class='num'>{r1(rel.get('1月'))}/{r1(rel.get('3月'))}/{r1(rel.get('6月'))}</td>"
                  f"<td class='num'>{r1(r.get('距52周高%'))}</td><td class='num'>{r1(r.get('量能比(涨/跌)'))}</td>"
                  f"<td class='num'>{r1(r.get('财报后跳空%'))}/{r1(r.get('20日守住%'))}</td>"
                  f"<td class='c-no'>{esc(susp)}{esc(anom)}</td></tr>")
        return h
    cols = "<tr><th>代码</th><th>象限</th><th>行业</th><th>变化得分</th><th>四项加速(利/营/现/毛)pp</th><th>相对大盘1/3/6月%</th><th>距52高%</th><th>量能</th><th>跳空/20守%</th><th>标注</th></tr>"

    html = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>市场确认·状态标记(不淘汰) · {d}</title>
<style>
body{{font-family:"Microsoft YaHei","PingFang SC",sans-serif;line-height:1.7;color:#1A1A1A;background:#F5F6F8;max-width:1240px;margin:0 auto;padding:16px 14px 60px}}
h2{{font-size:16px;color:#12324E;border-left:5px solid #12324E;padding-left:10px;margin:20px 0 8px}}
.hdr{{background:#12324E;color:#fff;border-radius:10px;padding:14px 18px;margin-bottom:12px}}
.hdr .sub{{font-size:13px;opacity:.92;margin-top:4px}}
table{{border-collapse:collapse;width:100%;font-size:11.4px;background:#fff;margin:8px 0}}
th,td{{border:1px solid #DDE3E8;padding:5px 6px;text-align:center;vertical-align:middle}}
th{{background:#12324E;color:#fff}} .mono{{font-family:Consolas,monospace;font-size:10.5px;color:#33414D}} .num{{text-align:right;font-family:Consolas,monospace}}
.c-no{{color:#A3231F;font-weight:700}}
.states{{display:flex;gap:10px;flex-wrap:wrap;margin:8px 0}}
.sb{{flex:1;min-width:180px;border-radius:9px;padding:12px 14px;color:#fff}} .sb .n{{font-size:26px;font-weight:800}}
.s1{{background:#1E7A45}} .s2{{background:#12324E}} .s3{{background:#8A2A26}} .s0{{background:#5A6673}}
.warn{{background:#FBF0E7;border:1px solid #C99A6B;border-radius:8px;padding:10px 14px;margin:8px 0;color:#6B3E00;font-size:12.5px}}
.big{{background:#EEF4F8;border:1px solid #B9D3E6;border-radius:8px;padding:12px 16px;margin:8px 0;color:#12324E;font-size:14px;font-weight:700}}
.focus{{background:#EAF5EF;border:2px solid #1E7A45;border-radius:9px;padding:8px 12px;margin:8px 0}}
.scroll{{overflow-x:auto}}
</style></head><body>
<div class="hdr"><div style="font-size:20px;font-weight:800">📍 市场确认 · 状态标记（不再淘汰·F-12）</div>
<div class="sub">{d} ｜ ★市场确认不淘汰任何标的·改为每只打三选一状态·全保留分开显示·天天现算不锚死名单(总则六) ｜ 只算不筛选·不出买卖建议·不改尺·不合并总分</div></div>

<div class="states">
<div class="sb s1"><div>已确认（3月已跑赢）</div><div class="n">{dist['已确认']}</div></div>
<div class="sb s2"><div>正在确认（3月仍跑输·但在改善）</div><div class="n">{dist['正在确认']}</div></div>
<div class="sb s3"><div>未确认（3月跑输·未见好转）</div><div class="n">{dist['未确认']}</div></div>
<div class="sb s0"><div>状态数据不足</div><div class="n">{dist['状态数据不足']}</div></div>
</div>
<div class="big">回答：主池89只(象限分歧false)市场确认三状态 —— <b>已确认 {dist['已确认']} · 正在确认 {dist['正在确认']} · 未确认 {dist['未确认']}</b>（另 状态数据不足 {dist['状态数据不足']}）。<br>
其中真主池39(四项同向加速真强者)：正在确认 {dist39.get('正在确认',0)} · 已确认 {dist39.get('已确认',0)} · 未确认 {dist39.get('未确认',0)}。<br>
<span style="font-size:11.5px;font-weight:400">"近期好于前期"口径=1月相对强度 &gt; 6月(或3月)相对强度(相对强度在改善)。校验：Palantir 与 Amphenol 均落【正在确认】(上一版被当门槛淘汰的·现保留)。三状态互不淘汰。</span></div>

<div class="focus"><b style="color:#1E7A45;font-size:15px">★ 正在确认（单独成栏·不埋末尾）：{dist['正在确认']}只</b> — 生意在变好而市场未充分反应·空间通常比"已确认"大。
<div class="scroll"><table>{cols}{tbl(order.get('正在确认', []))}</table></div></div>

<h2>已确认（3月已跑赢大盘·市场已认可·{dist['已确认']}只）</h2>
<div class="scroll"><table>{cols}{tbl(order.get('已确认', []))}</table></div>

<h2>未确认（3月跑输且近期未见好转·{dist['未确认']}只·保留不淘汰）</h2>
<div class="scroll"><table>{cols}{tbl(order.get('未确认', []))}</table></div>

<div class="warn"><b>★口径提示(承上轮):</b>本表主池=象限分歧false共89只(含 ①真强者39/②5/④5/无法判定40·逐只已标"象限"列)。真正"四项同向加速"的是39只。三状态判据只定义·具体哪只落哪档由每日数据现算·天天会变(总则六·不锚死名单)。保持不变:四象限F-11/四柱算法/8xxx-11xxx/F-07五条/基数标注/毛利率结构NA。</div>

<div class="hdr" style="text-align:center;background:#fff;color:#12324E;border:1px solid #DDE3E8"><b>本轮把市场确认从"淘汰门槛"改为"状态标记"·三状态全保留·未淘汰任何标的·未出固定名单·未合并总分。请架构师核对后再设计标准。</b><br>
<span class="mono">实物：data/screen/pool_state_{d}.json</span></div>
</body></html>"""
    out = ROOT / "00_请先看这里" / f"市场确认状态标记_{d}.html"
    out.write_text(html, encoding="utf-8")
    raw = out.read_bytes()
    print("wrote", out.name, len(raw), "字节 · EFBFBD=", raw.count(b"\xef\xbf\xbd"))


if __name__ == "__main__":
    main()
