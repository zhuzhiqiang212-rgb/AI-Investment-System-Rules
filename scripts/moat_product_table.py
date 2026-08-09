# -*- coding: utf-8 -*-
"""★轮155 A:护城河客观数据→产品表(册2a/2b持仓深研·董事长与Opus5可见)。
每项标 值/年份/准则(IFRS或JP-GAAP)/数据源/NK4。
★A-3 两条会误导的数带注:①任天堂毛利率0.39带『Switch2发售年·常态~61%(FY2025)』②东京海上ROE双口径并列。
★A-4 负ROIC(MSTR/闪迪)如实显示不隐藏。★Code只排版真数·质性归Opus5(G2)。"""
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _latest(pat):
    g = sorted(ROOT.glob(pat)); return g[-1] if g else None


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _last(d):
    """dict{year:val}→(最新年,值);非dict→(None,None)。"""
    if isinstance(d, dict) and d:
        y = sorted(d.keys())[-1]
        return y, d[y]
    return None, None


def _fmt_pct(d, nk_label="NK4"):
    y, v = _last(d)
    if v is None:
        return f'<span style="color:#999">{nk_label}</span>', None
    return f'{v*100:.1f}% <span style="color:#888;font-size:11px">(FY{y})</span>', v


def rows_data(dc):
    ed = _rj(_latest("data/opportunity/moat_data_*.json"))
    jp = _rj(_latest("data/opportunity/edinet_moat_*.json"))
    roic = _rj(_latest("data/opportunity/roic_*.json"))
    fw = _rj(_latest("data/opportunity/moat_framework_*.json"))
    roic_m = {r["代码"]: r["ROIC结果"] for r in roic.get("逐只", [])}
    us = {r["代码"]: r for r in ed.get("逐只", [])}
    jpm = {r["代码"]: r for r in jp.get("逐只", [])}
    out = []
    for h in fw.get("逐只(20持仓·通用五维结构+客观托底)", []):
        code = h["代码"]; name = h["名称"]
        rec = {"代码": code, "名称": name, "准则": None, "源": None,
               "毛利率": None, "ROE": None, "研发费用率": None, "营收增速稳定性": None, "ROIC": None, "注": []}
        if code in us and "四项数据(近3年·对应通用五维)" in us[code]:
            d = us[code]["四项数据(近3年·对应通用五维)"]; rec["源"] = "EDGAR(SEC)"; rec["准则"] = "US-GAAP/IFRS"
            rec["毛利率"] = d.get("毛利率近3年"); rec["ROE"] = d.get("ROE近3年")
            rec["研发费用率"] = d.get("研发费用率近3年"); rec["营收增速稳定性"] = d.get("营收增速稳定性(增速标准差)")
        elif code in jpm:
            d = jpm[code]["数据"]; rec["源"] = "EDINET(FSA)"; rec["准则"] = d.get("会计准则")
            if d.get("★保险专用(毛利率对保险不适用)"):
                rec["保险"] = True
                rec["ROE"] = {"IFRS": d.get("ROE_IFRS口径(归母·近年)"), "JPGAAP": d.get("ROE_JPGAAP口径(自己資本利益率·近年)")}
                rec["注"].append("保险公司·毛利率不适用·ROE双口径并列(IFRS/JP-GAAP不混)")
            else:
                rec["毛利率"] = d.get("毛利率近年"); rec["ROE"] = d.get("ROE近年(自算=归母净利/归母权益)")
                rec["研发费用率"] = d.get("研发费用率近年"); rec["营收增速稳定性"] = d.get("营收增速稳定性(增速标准差)")
        else:
            rec["源"] = "NK4"
        rr = roic_m.get(code, {})
        rec["ROIC"] = rr.get("ROIC") if isinstance(rr.get("ROIC"), (int, float)) else None
        rec["ROIC_FY"] = rr.get("FY")
        # ★A-3 误导数带注
        if code == "JP.7974":
            rec["注"].append("★毛利率0.39=Switch2发售年(硬件占比高)·常态~61%(FY2025)·非口径错")
        if code == "JP.8766":
            pass  # 保险注已加
        out.append(rec)
    return out


def render_html(dc):
    data = rows_data(dc)
    def cell(d):
        h, _ = _fmt_pct(d) if isinstance(d, dict) or d is None else (esc(d), None)
        return h
    trs = []
    for r in data:
        # ROE(保险双口径特判)
        if isinstance(r["ROE"], dict) and "IFRS" in r["ROE"]:
            iy, iv = _last(r["ROE"]["IFRS"]); jy, jv = _last(r["ROE"]["JPGAAP"])
            roe_html = (f'IFRS {iv*100:.1f}% <span style="color:#888;font-size:11px">(FY{iy})</span> / '
                        f'JP {jv*100:.1f}% <span style="color:#888;font-size:11px">(FY{jy})</span>') if (iv is not None and jv is not None) else '<span style="color:#999">NK4</span>'
        else:
            roe_html = cell(r["ROE"])
        gm_html = cell(r["毛利率"]) if not r.get("保险") else '<span style="color:#999">保险N/A</span>'
        rd_html = cell(r["研发费用率"])
        rev_std = r["营收增速稳定性"]
        rev_html = (f'{rev_std:.3f}' if isinstance(rev_std, (int, float)) else '<span style="color:#999">NK4</span>')
        if r["ROIC"] is None:
            roic_html = '<span style="color:#999">NK4</span>'
        else:
            col = "#c0392b" if r["ROIC"] < 0 else ("#1e7a3c" if r["ROIC"] >= 0.2 else "#333")
            roic_html = f'<b style="color:{col}">{r["ROIC"]*100:.1f}%</b> <span style="color:#888;font-size:11px">(FY{r.get("ROIC_FY")})</span>'
        note = ""
        if r["注"]:
            note = '<div style="font-size:11px;color:#b8860b;margin-top:2px">⚠ ' + "；".join(esc(n) for n in r["注"]) + "</div>"
        trs.append(
            f'<tr><td style="text-align:left"><b>{esc(r["名称"])}</b><br><span style="color:#888;font-size:11px">{esc(r["代码"])}·{esc(r["准则"] or "?")}·{esc(r["源"])}</span>{note}</td>'
            f'<td>{gm_html}</td><td>{roe_html}</td><td>{rd_html}</td><td>{rev_html}</td><td>{roic_html}</td></tr>')
    html = (
        '<div style="margin:14px 0"><h2 style="font-size:17px">🏰 护城河客观数据（20持仓·机器取真数·五维打分由Opus5）</h2>'
        '<div style="font-size:12px;color:#666;margin-bottom:6px">数据源：美股 EDGAR(SEC XBRL)·日股 EDINET(FSA XBRL)·准则IFRS/JP-GAAP不混·NK4=取不到(不估算)。'
        '毛利率=成本优势·ROE/ROIC=护城河结果指标·研发率=无形资产/专利·营收增速稳定性(标准差·越小越稳)=转换成本间接。</div>'
        '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:13px;text-align:center" border="1" cellpadding="6">'
        '<tr style="background:#f0f4f8;font-weight:700"><td>持仓</td><td>毛利率</td><td>ROE</td><td>研发费用率</td><td>营收增速稳定性(σ)</td><td>ROIC</td></tr>'
        + "".join(trs) +
        '</table></div>'
        '<div style="font-size:11px;color:#888;margin-top:6px">⚠标注=会误导的数需带上下文读。负ROIC(红)如实显示不隐藏。ROE绿=≥20%。</div></div>')
    return html


def render_dio_html(dc):
    """★轮166 A:DIO/capex表(与护城河表并列·标值/期间/口径/源/NK4·JP年度2点限制显示·组合状态)。"""
    ic = _rj(_latest("data/universe/inventory_capex_2*.json"))   # 3焦点(详细)
    rows = ic.get("逐只", []) or []
    trs = []
    for r in rows:
        dt = r.get("★DIO趋势"); ct = r.get("★capex趋势"); combo = r.get("★组合状态(Code只给·含义董事长判)", "NK4")
        kou = r.get("口径", "?")
        dio_html = (f'{dt["首末"]}天·<b>{esc(dt["总体"])}</b>' if isinstance(dt, dict) else '<span style="color:#999">NK4</span>')
        cap_html = (f'<b>{esc(ct["总体"])}</b>' if isinstance(ct, dict) else '<span style="color:#999">NK4</span>')
        limit = '<span style="color:#c0392b;font-size:11px">⚠年度2点(季度序列需四半期報告)</span>' if "年度" in kou else '<span style="color:#888;font-size:11px">季度8-12季</span>'
        trs.append(f'<tr><td style="text-align:left"><b>{esc(r["全名"])}</b><br><span style="color:#888;font-size:11px">{esc(r["代码"])}·{esc(kou)}·{("EDINET" if r["代码"].startswith("JP") else "EDGAR")}</span></td>'
                   f'<td>{dio_html}</td><td>{cap_html}</td><td><b>{esc(combo)}</b></td><td>{limit}</td></tr>')
    return ('<div style="margin:14px 0"><h2 style="font-size:17px">🔄 行业周期位置（库存周转天数 + capex·机器取数·周期位置由Opus5/董事长判）</h2>'
            '<div style="font-size:12px;color:#666;margin-bottom:6px">DIO=存货÷营业成本×天数（US季度/JP年度）·capex=资本开支趋势·源：US EDGAR / JP EDINET·NK4=取不到。★JP为有報年度2点·非季度序列（已标）。</div>'
            '<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:13px;text-align:center" border="1" cellpadding="6">'
            '<tr style="background:#f0f4f8;font-weight:700"><td>标的</td><td>库存周转天数(DIO)</td><td>capex趋势</td><td>★组合状态</td><td>口径限制</td></tr>'
            + "".join(trs) + '</table></div>'
            '<div style="font-size:11px;color:#888;margin-top:6px">★capex升+库存降/升 等组合＝周期位置线索·是不是升周期/见顶由Opus5/董事长判（Code不判）。</div></div>')


def build(dc):
    html = render_html(dc)
    outp = ROOT / f"data/opportunity/moat_table_{dc}.html"
    outp.write_text(html, encoding="utf-8")
    dio = render_dio_html(dc)
    (ROOT / f"data/opportunity/dio_table_{dc}.html").write_text(dio, encoding="utf-8")
    return html


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    build(a.date.replace("-", ""))
    data = rows_data(a.date.replace("-", ""))
    print("护城河表:", len(data), "只 · 有ROIC:", sum(1 for r in data if r["ROIC"] is not None),
          "· 带注:", sum(1 for r in data if r["注"]))
    for r in data:
        if r["注"]:
            print("  ⚠", r["代码"], r["名称"], "→", "；".join(r["注"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
