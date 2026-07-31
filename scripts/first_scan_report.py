#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""首轮扫描 · 给董事长看的 HTML 完工报告(路径+字节+生成时间+外部时间+覆盖率+四选一+四漏筛)。
所有数字从 data/screen/*.json 真实物读·不手打。用法: python scripts/first_scan_report.py --date 20260720"""
import argparse, json, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data" / "screen"


def esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load(name):
    p = SCREEN / name
    return (json.loads(p.read_text(encoding="utf-8")) if p.exists() else None)


def fmeta(rel):
    p = ROOT / rel
    if not p.exists():
        return (rel, "—", "缺")
    st = p.stat()
    return (rel, f"{st.st_size:,}", datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="20260720"); a = ap.parse_args()
    d = a.date
    run = load(f"_run_{d}.json") or {}
    gate = load(f"gate_{d}.json") or {}
    uni = load(f"universe_{d}.json") or {}
    cand = load(f"candidates_{d}.json") or {}
    cov = load(f"coverage_alert_{d}.json") or {}
    kr = load(f"kr_targets_{d}.json") or {}
    kt = load(f"ktype_{d}.json") or {}

    et = run.get("external_server_time", {})
    et_txt = (f"{et.get('iso')}（源：{et.get('source')}）" if et.get("ok") else f"未取到（{et.get('reason','')[:40]}）")
    covm = run.get("覆盖率_美日各自", {})

    def cov_row(mk):
        c = covm.get(mk, {})
        tot = c.get("总股票数"); miss = c.get("成交额缺失(NODATA)")
        rate = c.get("缺失率_成交额_基于主板过市值池_pct")
        warn = (rate is not None and rate > 20)
        return (f"<tr><td><b>{mk}</b></td><td class='num'>{tot}</td><td class='num'>{c.get('主板上市数')}</td>"
                f"<td class='num'>{c.get('OTC粉单(不可执行·不计缺失率)')}</td>"
                f"<td class='num'>{c.get('主板中过市值门槛')}</td><td class='num'>{c.get('其中成交额成功读取')}</td>"
                f"<td class='num'>{miss}</td><td class='num'>{'—' if rate is None else rate}</td>"
                f"<td>{'⚠ 缺失率>20%·不得称已完成全量筛选' if warn else '成交额缺失率 0/阈内'}</td></tr>")

    # 交付物清单
    files = ["account_perm", "kr_targets", "universe", "gate", "industry", "leader", "ktype",
             "valuation", "candidates", "coverage_alert", "_run"]
    deliv = "".join(f"<tr><td class='mono'>{esc(r)}</td><td class='num'>{b}</td><td class='mono'>{t}</td></tr>"
                    for r, b, t in (fmeta(f"data/screen/{n}_{d}.json") for n in files))

    # 四选一
    summ = cand.get("summary", {})
    summ_html = " ｜ ".join(f"{k} <b>{v}</b>" for k, v in summ.items()) or "—"

    # 候选池前若干(过门槛/无法判定)展示
    rows = ""
    for c in (cand.get("candidates") or [])[:40]:
        rows += (f"<tr><td class='mono'>{esc(c['code'])}</td><td>{esc(c['conclusion'])}</td>"
                 f"<td class='num'>{'' if c.get('market_val_usd_approx') is None else round(c['market_val_usd_approx']/1e9,1)}</td>"
                 f"<td class='num'>{'' if c.get('turnover_usd_approx') is None else round(c['turnover_usd_approx']/1e6,1)}</td>"
                 f"<td class='num'>{c.get('pe_ttm') if c.get('pe_ttm') is not None else ''}</td>"
                 f"<td>{esc(c['reason'])}</td></tr>")

    # 四漏筛
    chk_html = ""
    for c in (cov.get("checks") or []):
        res = c.get("结果", "")
        cls = "c-ok" if res == "无警报" else ("c-warn" if res in ("报警", "不合格") else "c-mut")
        extra = ""
        if c.get("检查") == "点名核对清单":
            extra = "<ul>" + "".join(f"<li class='mono'>{esc(x['code'])}：{esc(x['状态'])}</li>" for x in c.get("逐只", [])) + "</ul>"
        elif c.get("明细"):
            extra = "<div class='mono'>" + esc(json.dumps(c["明细"], ensure_ascii=False)[:300]) + "</div>"
        chk_html += f"<tr><td>{esc(c.get('检查'))}</td><td class='{cls}'>{esc(res)}</td><td>{esc(c.get('说明',''))}{extra}</td></tr>"

    # KR
    kr_alt = "".join(f"<li>{esc(o)} → {esc(json.dumps(v, ensure_ascii=False)[:120])}</li>"
                     for o, v in (kr.get("替代观察工具") or {}).items())

    html = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>首轮扫描完工报告 · 美日全量+韩股定向两只 · {d}</title>
<style>
body{{font-family:"Microsoft YaHei","PingFang SC",sans-serif;line-height:1.7;color:#1A1A1A;background:#F5F6F8;max-width:1180px;margin:0 auto;padding:16px 14px 60px}}
h2{{font-size:17px;color:#12324E;border-left:5px solid #12324E;padding-left:10px;margin:22px 0 8px}}
.hdr{{background:#12324E;color:#fff;border-radius:10px;padding:14px 18px;margin-bottom:12px}}
.hdr .sub{{font-size:13px;opacity:.92;margin-top:4px}}
.card{{background:#fff;border:1px solid #DDE3E8;border-radius:9px;padding:12px 16px;margin:10px 0}}
table{{border-collapse:collapse;width:100%;font-size:12.5px;background:#fff;margin:8px 0}}
th,td{{border:1px solid #DDE3E8;padding:6px 8px;text-align:left;vertical-align:top}}
th{{background:#12324E;color:#fff}} tr:nth-child(even){{background:#F2F4F7}}
.mono{{font-family:Consolas,monospace;font-size:11.5px;color:#33414D}}
.num{{text-align:right;font-family:Consolas,monospace}}
.c-ok{{color:#1E7A45;font-weight:800}} .c-warn{{color:#A3231F;font-weight:800}} .c-mut{{color:#6B5200;font-weight:800}}
.warn{{background:#FBF0E7;border:1px solid #C99A6B;border-radius:7px;padding:8px 12px;font-size:12.5px;margin:8px 0;color:#6B3E00}}
.note{{background:#EEF4F8;border:1px solid #B9D3E6;border-radius:7px;padding:8px 12px;font-size:12.5px;margin:8px 0;color:#12324E}}
ul{{margin:6px 0;padding-left:22px}} .scroll{{overflow-x:auto}}
</style></head><body>
<div class="hdr"><div style="font-size:20px;font-weight:800">🔎 首轮扫描完工报告 · 《美日全量扫描 ＋ 韩股定向两只 · 首轮》</div>
<div class="sub">派工单：{esc(run.get('派工单',''))} ｜ 报告生成 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ｜ 外部服务器时间：{esc(et_txt)}</div>
<div class="sub"><b>本轮不是「全球」</b>：港股/新加坡/欧洲本轮不做；韩国＝定向查2只、未做全市场扫描。不出买卖清单·不下单·只读·不改尺。</div></div>

<div class="card"><b>一句话：</b> 美日按全量扫过一遍门槛，韩股两只按定向查证(OpenD不支持→数据未接·SK海力士有US替代观察线)。
筛选只出四选一结论+原因代码：<b>{summ_html}</b>。四项漏筛检查全部输出。净负债(门槛3)所需财务 OpenD 未接→凡仅缺此项者一律「无法判定」，未谎称入围。</div>

<h2>覆盖率（仅美日·港新欧不计入·韩国定向不算全市场）</h2>
<div class="scroll"><table>
<tr><th>市场</th><th>全集总数</th><th>主板上市</th><th>OTC粉单(不可执行·不计缺失)</th><th>主板过市值门槛</th><th>成交额成功读取</th><th>成交额缺失</th><th>缺失率%</th><th>判定</th></tr>
{cov_row('US')}{cov_row('JP')}
</table></div>
<div class="note">口径：全集=get_stock_basicinfo；市值门槛=OpenD server-filter(MARKET_VAL≥100亿美元)；成交额=get_market_snapshot当日成交额近似日均(OpenD不支持成交额过滤字段·首轮如实标)。JP以假设汇率 USDJPY={esc(run.get('FX_USDJPY_assumed'))} 换算美元门槛·<b>待架构师确认</b>。</div>

<h2>候选池 · 四选一结论（前40·完整见 candidates_{d}.json）</h2>
<div class="scroll"><table>
<tr><th>代码</th><th>结论</th><th>市值($B)</th><th>成交额($M)</th><th>PE_TTM</th><th>原因</th></tr>
{rows}
</table></div>

<h2>四项漏筛检查（本轮重点·全部输出）</h2>
<div class="scroll"><table>
<tr><th>检查</th><th>结果</th><th>说明/明细</th></tr>
{chk_html}
</table></div>

<h2>韩股两只 · 定向查证</h2>
<div class="card"><b>{esc(kr.get('结论',''))}</b><br>
<span class="mono">池归属：{esc(kr.get('池归属',''))}</span>
<ul>{kr_alt}</ul></div>

<h2>交付物实物清单（路径 · 字节 · 生成时间）</h2>
<div class="scroll"><table>
<tr><th>文件</th><th>字节</th><th>生成时间</th></tr>
{deliv}
</table></div>

<div class="warn"><b>已知不足（先说清·不算失职·派工单第八节）：</b>
<ul>
<li>数据源只有 OpenD：市值/成交额可取；<b>净负债/经营性现金流未直接提供 → 净负债门槛(3)未接·凡仅缺此项者一律「无法判定」·不估算</b>。</li>
<li>行业强度五指标里 需求增速/供需/政策资本 依赖第三方行业报告，Code 拿不到 → <b>本轮大面积留空·由架构师人工补</b>；相对大盘可机器算(与K线同源)。</li>
<li>市场份额无法全自动 → 全部标「龙头地位未证实」并列入份额缺失清单，架构师人工补并标半自动。</li>
<li>K型六信号：只对过市值+成交额的池、按成交额降序、上限 {esc(kt.get('cap'))} 只机器判；超上限 <b>{esc(kt.get('pending_count'))}</b> 只如实标 pending(未跑日线·不估算)·下轮补。</li>
<li>汇率 USDJPY={esc(run.get('FX_USDJPY_assumed'))} 为假设值(OpenD无直接forex源)·影响JP门槛边界·<b>待董事长/架构师确认</b>。</li>
<li>参数7 分数线≥70、参数11~13 均首轮试跑/无外部依据，跑完须回看调整·Code未自行优化。</li>
</ul></div>

<div class="card" style="text-align:center;color:#12324E"><b>Code 不自宣通过。申请架构师独立读实物核验(可重跑证据在 _run_{d}.json)，核完再送 GPT 总控11。</b></div>
</body></html>"""

    out = ROOT / "00_请先看这里" / f"首轮扫描完工报告_{d}.html"
    out.write_text(html, encoding="utf-8")
    raw = out.read_bytes()
    print("写出:", out, "· 字节:", len(raw), "· 乱码EFBFBD:", raw.count(b"\xef\xbf\xbd"))


if __name__ == "__main__":
    main()
