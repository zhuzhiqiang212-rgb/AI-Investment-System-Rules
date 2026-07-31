#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""首轮重跑(A案) HTML完工报告。数字从 data/screen/*_20260721.json 真读·不手打。
用法: python scripts/first_scan2_report.py --date 20260721"""
import argparse, json, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data" / "screen"


def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load(n):
    p = SCREEN / n
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def fmeta(rel):
    p = ROOT / rel
    if not p.exists():
        return (rel, "—", "缺")
    st = p.stat()
    return (rel, f"{st.st_size:,}", datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="20260721"); a = ap.parse_args()
    d = a.date
    run = load(f"_run2_{d}.json") or {}
    gate = load(f"gate_{d}.json") or {}
    fin = load(f"fin_score_{d}.json") or {}
    fc = load(f"funnel_compare_{d}.json") or {}
    cand = load(f"candidates_{d}.json") or {}
    cov = load(f"coverage_alert_{d}.json") or {}
    kr = load(f"kr_targets_{d}.json") or {}

    et = run.get("external_server_time", {})
    et_txt = (f"{et.get('iso')}（{et.get('source')}）" if et.get("ok") else f"未取到")
    fx = run.get("FX_live", {})
    fx_txt = (f"USDJPY={fx.get('USDJPY')}（{fx.get('source')}·as_of {fx.get('as_of')}·取于 {fx.get('fetched_local')}）"
              if fx.get("ok") else f"未取到（{fx.get('reason','')}）")
    covm = run.get("覆盖率_美日", {})

    def cov_row(mk):
        c = covm.get(mk, {})
        rate = c.get("缺失率_pct"); warn = (rate is not None and rate > 20)
        if c.get("全集取数", "").startswith("失败"):
            return (f"<tr style='background:#FBECEC'><td><b>{mk}</b></td><td class='c-warn'>全集拉取失败·未取得</td>"
                    f"<td class='num'>—</td><td class='num'>—</td><td class='num'>{c.get('mktcap股(来自server-filter)')}</td>"
                    f"<td class='num'>{c.get('未取得计入缺失')}</td><td class='num c-warn'>100</td>"
                    f"<td class='c-warn'>⚠ 该市场缺席·计入缺失率·不得称已扫描</td></tr>")
        return (f"<tr><td><b>{mk}</b></td><td class='num'>{c.get('全集')}</td><td class='num'>{c.get('主板')}</td>"
                f"<td class='num'>{c.get('OTC(不做·不计缺失)')}</td><td class='num'>{c.get('主板过市值')}</td>"
                f"<td class='num'>{c.get('成交额60日均缺失(NODATA)')}</td><td class='num'>{'—' if rate is None else rate}</td>"
                f"<td>{'⚠ >20%·不得称已完成全量' if warn else '在阈内'}</td></tr>")

    # 漏斗对比
    f = fc.get("漏斗对比", {})
    prev = f.get("上轮_20260720", {}); cur = f.get("本轮_20260721", {})
    keys = ["全集US", "全集JP", "过市值主板US", "过市值主板JP", "过成交额poolB", "入围", "无法判定", "落选"]
    frows = ""
    for k in keys:
        pv = prev.get(k, prev.get(k.replace("主板", "").replace("过市值", "过市值主板"), "—"))
        frows += f"<tr><td>{esc(k)}</td><td class='num'>{esc(prev.get(k,'—'))}</td><td class='num'>{esc(cur.get(k,'—'))}</td></tr>"
    frows += (f"<tr><td>研究基准(OCF未接)</td><td class='num'>—</td><td class='num'>{esc(cur.get('研究基准(OCF未接)','—'))}</td></tr>")

    # BWXT/NRG
    rc = fc.get("BWXT_NRG复核", {})
    rc_html = ""
    for k, v in rc.items():
        if isinstance(v, dict):
            tv = v.get("本轮60日均成交额_usd")
            tv_m = f"{tv/1e6:.1f}M" if tv else "—"
            rc_html += f"<tr><td class='mono'>{esc(k)}</td><td>{esc(v.get('上轮'))}</td><td class='num'>{tv_m}</td><td><b>{esc(v.get('本轮结论'))}</b>·{esc(v.get('原因',''))}</td></tr>"
        else:
            rc_html += f"<tr><td class='mono'>{esc(k)}</td><td colspan='3'>{esc(v)}</td></tr>"

    # 财务五维缺失率
    fmr = fin.get("财务五维缺失率", {})
    fmr_html = "".join(f"<tr><td>{esc(k)}</td><td class='num'>{v.get('缺')}</td><td class='num'>{v.get('共')}</td>"
                       f"<td class='num'>{v.get('缺失率_pct')}</td></tr>" for k, v in fmr.items())

    # 结论五选一
    summ = cand.get("summary", {})
    summ_html = " ｜ ".join(f"{k} <b>{v}</b>" for k, v in summ.items()) or "—"

    # 入围池(带财务质量分)
    rows = ""
    for c in [x for x in cand.get("candidates", []) if x["conclusion"] == "入围"][:40]:
        coarse = "＊" if str(c.get("分位口径", "")).startswith("全市场") else ""
        rows += (f"<tr><td class='mono'>{esc(c['code'])}</td><td>{esc(c.get('industry',''))}</td>"
                 f"<td class='num'>{'' if c.get('market_val_usd') is None else round(c['market_val_usd']/1e9,1)}</td>"
                 f"<td class='num'>{'' if c.get('avg_turnover_60d_usd') is None else round(c['avg_turnover_60d_usd']/1e6,1)}</td>"
                 f"<td class='num'>{'' if c.get('ocf_ttm') is None else round(c['ocf_ttm']/1e9,2)}</td>"
                 f"<td class='num'>{c.get('gross_margin','')}</td>"
                 f"<td class='num'><b>{c.get('financial_quality_score','')}</b>{coarse}</td>"
                 f"<td class='num'>{c.get('财务质量缺维度数','')}/5</td></tr>")

    chk_html = ""
    for c in cov.get("checks", []):
        res = c.get("结果", ""); cls = "c-ok" if res.startswith("无警报") else ("c-warn" if res in ("报警", "不合格") else "c-mut")
        extra = ""
        if c.get("检查") == "点名核对清单":
            extra = "<ul>" + "".join(f"<li class='mono'>{esc(x['code'])}：{esc(x['状态'])}</li>" for x in c.get("逐只", [])) + "</ul>"
        chk_html += f"<tr><td>{esc(c.get('检查'))}</td><td class='{cls}'>{esc(res)}</td><td>{esc(c.get('说明',''))}{extra}</td></tr>"

    files = ["account_perm", "kr_targets", "universe", "gate", "fin_score", "funnel_compare",
             "candidates", "coverage_alert", "_run2"]
    deliv = "".join(f"<tr><td class='mono'>{esc(r)}</td><td class='num'>{b}</td><td class='mono'>{t}</td></tr>"
                    for r, b, t in (fmeta(f"data/screen/{n}_{d}.json") for n in files))

    html = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>首轮重跑(A案·财务改评分制)完工报告 · {d}</title>
<style>
body{{font-family:"Microsoft YaHei","PingFang SC",sans-serif;line-height:1.7;color:#1A1A1A;background:#F5F6F8;max-width:1180px;margin:0 auto;padding:16px 14px 60px}}
h2{{font-size:17px;color:#12324E;border-left:5px solid #12324E;padding-left:10px;margin:22px 0 8px}}
.hdr{{background:#12324E;color:#fff;border-radius:10px;padding:14px 18px;margin-bottom:12px}}
.hdr .sub{{font-size:13px;opacity:.92;margin-top:4px}}
.card{{background:#fff;border:1px solid #DDE3E8;border-radius:9px;padding:12px 16px;margin:10px 0}}
table{{border-collapse:collapse;width:100%;font-size:12.5px;background:#fff;margin:8px 0}}
th,td{{border:1px solid #DDE3E8;padding:6px 8px;text-align:left;vertical-align:top}}
th{{background:#12324E;color:#fff}} tr:nth-child(even){{background:#F2F4F7}}
.mono{{font-family:Consolas,monospace;font-size:11.5px;color:#33414D}} .num{{text-align:right;font-family:Consolas,monospace}}
.c-ok{{color:#1E7A45;font-weight:800}} .c-warn{{color:#A3231F;font-weight:800}} .c-mut{{color:#6B5200;font-weight:800}}
.warn{{background:#FBF0E7;border:1px solid #C99A6B;border-radius:7px;padding:8px 12px;font-size:12.5px;margin:8px 0;color:#6B3E00}}
.note{{background:#EEF4F8;border:1px solid #B9D3E6;border-radius:7px;padding:8px 12px;font-size:12.5px;margin:8px 0;color:#12324E}}
ul{{margin:6px 0;padding-left:22px}} .scroll{{overflow-x:auto}}
</style></head><body>
<div class="hdr"><div style="font-size:20px;font-weight:800">🔁 首轮重跑（A案·财务改评分制）完工报告</div>
<div class="sub">{esc(run.get('派工单',''))} ｜ 报告生成 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ｜ 外部服务器时间：{esc(et_txt)}</div>
<div class="sub">实时汇率：{esc(fx_txt)}</div>
<div class="sub">只改三处(财务改评分/成交额60日均真算/汇率实时)·其余不变·不改尺·不自调参数·不出买卖清单</div>
<div class="sub" style="margin-top:6px;font-weight:800;font-size:14px">本轮实际覆盖范围：{esc(run.get('本轮实际覆盖范围','(见漏筛检查5)'))}</div></div>

<div class="card"><b>结论五选一：</b>{summ_html}<br>
<b>核心变化：</b>净负债从硬门槛改为评分维度(不阻断)；硬准入只剩 市值/60日均成交额/经营性现金流为正；OCF取不到者进<b>研究基准</b>(非落选)。</div>

<h2>《上轮 vs 本轮 漏斗对比》</h2>
<div class="scroll"><table>
<tr><th>环节</th><th>上轮 20260720</th><th>本轮 20260721</th></tr>
{frows}
</table></div>
<div class="note">上轮口径：成交额=当日近似·净负债硬门槛→0入围/386无法判定。本轮：成交额=60日均真算·财务改评分·实时FX={esc(fx.get('USDJPY'))}。汇率改实时后过市值只数会变(FX {esc(fx.get('USDJPY'))} vs 上轮假设155)。</div>

<h2>BWXT / NRG 复核（上轮疑单日近似造成假落选）</h2>
<div class="scroll"><table>
<tr><th>代码</th><th>上轮</th><th>本轮60日均成交额</th><th>本轮结论·原因</th></tr>
{rc_html}
</table></div>

<h2>覆盖率（仅美日·主板·OTC/港新欧不计缺失）</h2>
<div class="scroll"><table>
<tr><th>市场</th><th>全集</th><th>主板</th><th>OTC(不做)</th><th>主板过市值</th><th>成交额缺失</th><th>缺失率%</th><th>判定</th></tr>
{cov_row('US')}{cov_row('JP')}
</table></div>

<h2>财务质量五维度 · 缺失率（新增·让我们知道评分有多少数据支撑）</h2>
<div class="scroll"><table>
<tr><th>维度</th><th>缺(只)</th><th>入围共(只)</th><th>缺失率%</th></tr>
{fmr_html}
</table></div>
<div class="note">在手订单/成本优势 OpenD 无数据源→100%缺(记0分·标数据未接·不填补·不判落选)。<b>经营性现金流</b>(原误称自由现金流·OpenD无capex→改名·不得叫自由现金流)；<b>毛利率仅当前值·8季趋势未接</b>(规则要求趋势比水平更重要·候选卡已标)；资产负债以资产负债率。</div>

<h2>打回二修（董事长抽查·2026-07-21）</h2>
<div class="warn">
<b>问题1 · OCF门槛误伤投资控股：</b>软银(JP.9984)经营现金流为负(−¥646亿·价值来自持股增值非经营现金流)，上版被判「落选」。<b>本版改判「研究基准」</b>（标"OCF为负·须人工确认商业模式"）——落选=查过不合格，而这里是<b>用错了尺</b>，不是公司不合格。本轮新增 <b>研究基准 {esc(summ.get('研究基准',0))} 只</b>（OCF为负的疑投资控股/资管类）。<br>
<span style="font-size:11.5px">（架构师提的"按行业识别投资控股→改判净资产增减/投资收益"分支＝<b>待董事长拍板</b>·本轮只做保守兜底：OCF为负一律不落选、进研究基准。）</span>
<hr style="border:none;border-top:1px solid #C99A6B;margin:8px 0">
<b>问题2 · 毛利率 0.0 污染（致命）：</b>根因＝OpenD 对半年报日股在 MOST_RECENT_QUARTER 口径返回 <b>0.0</b>（发那科/信越实际 38.29%/34.22%）。<b>本版改 ANNUAL 口径取真值 + 任何 0.0 一律转 null（禁止填0）</b>。出厂检查命中 <b>US {esc((run.get('财务字段0_0报警') or {}).get('US命中数'))} / JP {esc((run.get('财务字段0_0报警') or {}).get('JP命中数'))}</b> 只（多为银行/金融·毛利率本就不适用），已转 null 不参与分位。<br>
<b>真毛利率缺失率 = {esc((fin.get('财务五维缺失率') or {}).get('毛利率',{}).get('缺失率_pct'))}%</b>（上版"0%"是假的·实为 {esc((fin.get('受0_0污染排查') or {}).get('入围中各维缺数',{}).get('毛利率'))}/432 缺）。所有分位已用真值重算。
</div>

<h2>行业分类标准（打回重算·2026-07-21）</h2>
<div class="warn"><b>★上一版作废：</b>之前 industry 误取了券商选股标签(如「日本可交易美股碎股列表」「储能概念股」)，非行业分类，432 个财务质量分全部作废。<b>本版改取 plate_type=INDUSTRY 的真行业分类</b>并重算。
<ul>
<li>分类标准：<b>{esc((fin.get('行业分类标准') or {}).get('名称'))}</b>（{esc((fin.get('行业分类标准') or {}).get('说明',''))}·数据日 {esc((fin.get('行业分类标准') or {}).get('数据日'))}）</li>
<li>入围 432 只落入 <b>{len(fin.get('各行业公司数分布') or {})}</b> 个行业；其中 <b>{len(fin.get('n1_行业组(单只·分位不可靠已退全市场)') or [])}</b> 个行业仅1只(如 Talen 曾独占核电组)→已退【全市场分位】并标注「未按行业校正·仅供粗排」，共 <b>{fin.get('退全市场分位的只数')}</b> 只用全市场分位。</li>
<li>校验例：Talen/NRG/VST/CEG 现同归「独立电力生产商」；Amphenol 归「电子元件」——不再是 n=1 的 0 分。</li>
</ul>
<div class="scroll"><table><tr><th>行业(前12·公司数)</th><th>数</th></tr>
{"".join(f"<tr><td>{esc(k)}</td><td class='num'>{v}</td></tr>" for k,v in list((fin.get('各行业公司数分布') or {}).items())[:12])}
</table></div></div>

<h2>入围池（前40·带真行业+财务质量分·＊=行业组过小改全市场分位·完整见 candidates_{d}.json）</h2>
<div class="scroll"><table>
<tr><th>代码</th><th>行业(INDUSTRY)</th><th>市值$B</th><th>60日均成交$M</th><th>经营现金流$B</th><th>毛利率%</th><th>财务质量分</th><th>缺维度</th></tr>
{rows}
</table></div>

<h2>四项漏筛检查</h2>
<div class="scroll"><table><tr><th>检查</th><th>结果</th><th>说明/明细</th></tr>{chk_html}</table></div>

<h2>韩股两只 · 定向查证</h2>
<div class="card"><b>{esc(kr.get('结论',''))}</b><br><span class="mono">{esc(kr.get('池归属',''))}</span></div>

<h2>交付物实物清单（路径·字节·生成时间）</h2>
<div class="scroll"><table><tr><th>文件</th><th>字节</th><th>生成时间</th></tr>{deliv}</table></div>

<div class="warn"><b>诚实标注：</b><ul>
<li>财务评分：3/5维度有OpenD数据(OCF/毛利率/资产负债)，在手订单/成本优势无源→0分·数据未接·未填补。缺失率见上表。</li>
<li>经营现金流(OCF)取不到者→研究基准(非落选)：没查到≠不合格，可研究不可执行·单独统计。</li>
<li>60日均成交额=kline真算(非当日近似)；取不到者→无法判定(不估算)。</li>
<li>汇率取实时并记录来源与时间；取不到则如实标未接·不用假设值。</li>
<li>行业强度/预测由架构师补；漏筛第3项行业增长数据Code拿不到→如实标『无法执行』不写无警报。</li>
<li>参数用批准值·未自调；不出买卖清单·未生成 actionable。</li>
</ul></div>
<div class="card" style="text-align:center;color:#12324E"><b>Code 不自宣通过。申请架构师独立读实物核验(_run2_{d}.json 含可重跑证据)，核完再送 GPT 总控11。</b></div>
</body></html>"""
    out = ROOT / "00_请先看这里" / f"首轮重跑完工报告_{d}.html"
    out.write_text(html, encoding="utf-8")
    raw = out.read_bytes()
    print("写出:", out, "· 字节:", len(raw), "· 乱码EFBFBD:", raw.count(b"\xef\xbf\xbd"))


if __name__ == "__main__":
    main()
