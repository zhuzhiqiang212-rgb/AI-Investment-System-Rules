# -*- coding: utf-8 -*-
"""★MAIN-04 决策卡五格（Code3 轮建·2026-08-09·董事长乙B1/B2）。

每只持仓一张卡·五格缺一格＝没做完：
  ①为什么   ②怎么动(守/减/加/换)  ③什么价(买点/止盈)  ④多少量(占比+股数+上限对照)  ⑤钱从哪来/影响

★分工(董事长乙B2·丁铁律)：Code【只建结构+可自动填的】(现价/股数/动作机器初值/估值标签/护城河)，
★①为什么真理由、③价目标、④占比目标 = 投资判断 → 归Opus5 → 留空标『待Opus5填』·★Code不替填。
★B3:今日动作＝0笔也出卡(『0笔』是结论·不是不需要卡)。

★数据诚实(铁律)：④权重%须【货币归一(USD)】——production 的 market_value 是【混货(日股¥·美股$)】·
  直接算权重会串(软银¥大值 vs NVDA$小值)。08-08 无新鲜USD归一 per-holding 源(统一表 unified_holdings 陈旧于07-02·
  同MAIN-03货币折算未接)→ ★权重%标『待接·混货未折算』·不输出错数。股数是原生值·可信·照填。
★Code不填判断·只搬机器可得字段+留判断槽。
"""
import json, glob, html as _h
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
SINGLE_CAP_PCT = 20.0   # 单只上限(memory four-risk-config-gates:董事长07-19四条·单只20%)


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def esc(x):
    return _h.escape(str(x)) if x is not None else ""


def _sb(kind, extra=""):
    """★轮331 丙:来源标签徽章(复用 product_blocks.source_badge·取不到则退化为文字)。"""
    try:
        import sys as _s
        _s.path.insert(0, str(ROOT / "scripts"))
        import product_blocks as _pb
        return _pb.source_badge(kind, extra)
    except Exception:
        return f'<span style="font-size:9px;color:#888">[{esc(kind)}]</span>'


def _latest_production(date):
    p = ROOT / "data" / "reports" / f"production_{date}.json"
    if not p.exists():
        cands = sorted(glob.glob(str(ROOT / "data" / "reports" / "production_*.json")))
        if not cands:
            return {}, None
        p = Path(cands[-1])
    return _rj(p), p.name


def _pending(label):
    """判断槽占位：待Opus5填(红字·不造壳·不替填)。"""
    return f'<span style="color:#a00">★待Opus5填（{esc(label)}）</span>'


def _grid5(h, company_news_by_sym):
    sym = str(h.get("symbol", "")); name = str(h.get("name") or sym)
    price = h.get("price"); qty = h.get("quantity")
    action = str(h.get("action") or "守")          # 机器初值(production算)·机制/为什么归Opus5
    val = h.get("valuation") or {}; val_lab = val.get("label") or val.get("status") or "待接"
    moat = h.get("moat") or {}; moat_g = moat.get("moat_grade") or "待评"
    one_line = str(h.get("one_line_reason") or "")  # 机器五关一句·作①参考·非最终理由
    # 今日公司事件(来自 company_news feed·作①今日事件锚·意义仍待Opus5)
    cn = (company_news_by_sym or {}).get(sym) or {}
    evs = cn.get("events") or []
    ev_html = ""
    if evs:
        lis = "".join(f'<li><a href="{esc(e.get("url"))}">{esc(str(e.get("title"))[:52])}</a>'
                      f'<span style="color:#888;font-size:10px">（{esc(e.get("source"))}·{esc(e.get("pub_date"))}）</span>{_sb("UNVERIFIED_RELAY")}</li>'
                      for e in evs[:3])
        ev_html = (f'<div style="font-size:10px;color:#c0392b">★今日公司事件＝转述未核·仅供Opus5判·不得单独支撑加减仓</div>'
                   f'<ul style="margin:2px 0 2px 16px;font-size:11px;color:#245">{lis}</ul>')
    elif cn:
        ev_html = '<div style="font-size:10.5px;color:#999">（今日无够格公司事件·客观空·不硬凑）</div>'

    action_color = {"加": "#0f7b3f", "减": "#c0392b", "守": "#42607a", "换": "#b8860b", "等": "#8a6d00"}.get(action, "#42607a")

    def row(no, tit, body):
        return (f'<div style="display:flex;gap:8px;padding:5px 0;border-top:1px dashed #d5dbe2">'
                f'<div style="flex:0 0 84px;font-weight:700;color:#12324e;font-size:12px">{no} {tit}</div>'
                f'<div style="flex:1;font-size:12px;color:#233">{body}</div></div>')

    g1 = f'{ev_html}<div style="color:#556;font-size:11px">机器五关一句(参考·非最终)：{esc(one_line)}</div>' \
         f'<div style="margin-top:2px">真理由/关键假设：{_pending("①为什么·真理由+与实际持仓关系")}</div>'
    g2 = f'当前机器动作：<b style="color:{action_color}">{esc(action)}</b>（机器初值）　机制/为什么这么动：{_pending("②守/减/加/换的机制")}'
    g3 = f'现价：<b>{esc(price)}</b>（机器·当日）{_sb("MACHINE_OBSERVATION")}　买点(合理区下沿)/止盈线：{_pending("③什么价")}　估值标签：{esc(val_lab)}'
    g4 = (f'持仓股数：<b>{esc(qty)}</b>（机器·原生·可信）{_sb("MACHINE_OBSERVATION")}　'
          f'当前权重：<span style="color:#a00">待接·混货未折算（须USD归一·同MAIN-03·不输出错数）</span>　'
          f'单只上限：{SINGLE_CAP_PCT:.0f}%（超过=强制减仓线）　'
          f'目标占比：{_pending("④多少量·目标占比")}')
    g5 = f'{_pending("⑤钱从哪来/影响：减能腾出多少·换掉的是谁·对组合的影响")}'

    return (f'<div style="border:1px solid #c3ccd6;border-left:6px solid {action_color};border-radius:9px;'
            f'background:#fbfcfe;padding:10px 13px;margin:9px 0">'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline">'
            f'<div style="font-size:15px;font-weight:800;color:#12324e">{esc(name)} '
            f'<span style="color:#7a8b9a;font-size:11px">{esc(sym)}</span></div>'
            f'<div style="font-size:11px;color:#7a8b9a">护城河：{esc(moat_g)}</div></div>'
            + row("①", "为什么", g1) + row("②", "怎么动", g2) + row("③", "什么价", g3)
            + row("④", "多少量", g4) + row("⑤", "钱从哪来", g5)
            + f'<div style="font-size:10px;color:#9aa;margin-top:4px">provenance：production_{esc(h.get("_dc",""))}·五格结构Code建·判断槽待Opus5</div>'
            + '</div>')


def build_html(date):
    prod, used = _latest_production(date)
    holds = [x for x in (prod.get("holdings") or []) if not str(x.get("symbol", "")).startswith("CC.")]
    cn_obj = _rj(ROOT / "data" / "news" / f"company_news_{date}.json")
    cn_by = {h.get("symbol"): h for h in (cn_obj.get("holdings") or [])}
    for h in holds:
        h["_dc"] = date
    cards = "".join(_grid5(h, cn_by) for h in holds)
    n_act = sum(1 for h in holds if str(h.get("action") or "守") not in ("守", "等"))
    head = (f'<div style="border:2px solid #12324e;border-radius:9px;background:#eef3f8;padding:9px 13px;margin:8px 0">'
            f'<div style="font-size:16px;font-weight:800;color:#12324e">决策卡 · 五格（每只一张·缺一格＝没做完）</div>'
            f'<div style="font-size:12px;color:#456;margin-top:3px">'
            f'①为什么 ②怎么动 ③什么价 ④多少量 ⑤钱从哪来／影响　·　持仓 {len(holds)} 只·'
            f'今日交易动作 {n_act} 笔（★0 笔也出卡·0笔是结论·非不需要）</div>'
            f'<div style="font-size:11px;color:#a00;margin-top:2px">★①为什么／③价／④占比目标＝投资判断·待Opus5填·Code不替填（丁铁律）</div>'
            f'<div style="font-size:10.5px;color:#888;margin-top:1px">数据：production_{esc(used)}·公司事件：company_news_{esc(date)}.json</div></div>')
    return head + cards


def build_all(date):
    """结构化返回(供 render 或自检)。"""
    prod, used = _latest_production(date)
    holds = [x for x in (prod.get("holdings") or []) if not str(x.get("symbol", "")).startswith("CC.")]
    return {"n_holdings": len(holds), "source": used, "date": date,
            "★判断槽": "①为什么/③价/④占比目标=待Opus5(Code不填)",
            "html_len": len(build_html(date))}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now().strftime("%Y%m%d"))
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    html = build_html(a.date)
    if a.out:
        Path(a.out).write_text(html, encoding="utf-8")
        print(f"[decision_cards_5grid] 写出 {a.out}·{len(html)} 字节")
    info = build_all(a.date)
    print(f"[decision_cards_5grid] 持仓{info['n_holdings']}只·五格HTML {info['html_len']}字节·源{info['source']}")
    print("[decision_cards_5grid] ★①为什么/③价/④占比目标 全标待Opus5填·Code只建结构+机器可填")


if __name__ == "__main__":
    main()
