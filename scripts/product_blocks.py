# -*- coding: utf-8 -*-
"""★★★轮312 共用产品区块（管道版与五册共用·通用扫描·不写死文件名）。
今日成果各归各册:前瞻区/降级清单→册1;爱德万等个股重估→册2持仓;同业对照→册3机会板块。
★董事长明日写微软/软银判断,同名规则(*_opus5_judgment_v*_{dc}.json / peer_*_{dc}.json)自动接,无需改代码。"""
import html as _h
import glob as _g
import re as _re
from pathlib import Path

UNFILLED = '<span style="color:#c0392b">（本项未填·下游不产出）</span>'


def esc(x):
    return _h.escape(str("" if x is None else x))


# ★轮331 丙:四来源标签(GPT新立·全系统适用)。UNVERIFIED_RELAY 必须显眼·不得单独支撑激活/候选/交易。
SOURCE_LABEL_META = {
    "MACHINE_OBSERVATION": ("机器实算", "#0f7b3f", "#e9f7ef"),
    "EXTERNAL_VERIFIED":   ("外部已核实", "#12324e", "#eef3f8"),
    "OPUS_JUDGMENT":       ("Opus5判断", "#6a4c93", "#f4eefb"),
    "UNVERIFIED_RELAY":    ("★转述未核", "#c0392b", "#fdecea"),
}


def source_badge(kind, extra=""):
    """来源标签徽章。kind∈四类。UNVERIFIED_RELAY 用红显眼(丙C2)。extra=URL/文件路径(EXTERNAL_VERIFIED须带)。"""
    label, fg, bg = SOURCE_LABEL_META.get(kind, ("待标来源", "#888", "#f2f2f2"))
    ex = f'<span style="color:#777;font-size:9.5px">·{esc(extra)}</span>' if extra else ""
    return (f'<span data-source-label="{esc(kind)}" style="display:inline-block;font-size:9.5px;font-weight:700;'
            f'color:{fg};background:{bg};border:1px solid {fg};border-radius:3px;padding:0 4px;margin-left:4px">'
            f'{label}</span>{ex}')


def _rv(v):
    """递归可读渲染·★绝不 str(dict)·不截断·空→未填。"""
    if v is None or v == "" or v == [] or v == {}:
        return UNFILLED
    if isinstance(v, dict):
        return "<div style='margin:2px 0 2px 10px'>" + "".join(
            f'<div style="margin:2px 0"><b>{esc(str(k))}</b>：{_rv(x)}</div>' for k, x in v.items()) + "</div>"
    if isinstance(v, list):
        return "<br>".join("・" + _rv(x) for x in v)
    return esc(str(v))


def opus_sections(root, relpath, title, border="#7B241C"):
    """渲 Opus 判断 JSON 全节·键=内容小节标题(元数据 _ 开头跳过·不当标题)·值递归可读。"""
    import json as _j
    p = root / relpath
    if not p.exists():
        return f'<h2>{esc(title)}</h2><p style="color:#c0392b">（{esc(relpath)} 不存在·本层未填·下游不产出）</p>'
    try:
        d = _j.loads(p.read_text(encoding="utf-8"))
    except Exception as _e:
        return f'<h2>{esc(title)}</h2><p style="color:#c0392b">（读取失败:{esc(str(_e)[:60])}）</p>'
    body = ""
    for k, v in d.items():
        if str(k).startswith("_"):
            continue
        body += (f'<div style="border-left:3px solid {border};padding-left:10px;margin:8px 0">'
                 f'<h3 style="margin:4px 0;font-size:14px;color:{border}">{esc(str(k))}</h3>{_rv(v)}</div>')
    return f'<h2 style="color:{border};border-left:5px solid {border};padding-left:8px">{esc(title)}</h2>{body}'


def degrade_html(dc):
    """★结论降级七类 + 临时合规状态声明(GPT V7§19)·置于第一屏·不得只放文末。"""
    items = [
        "①单只是否破20%上限 → <b>不可执行</b>（分母打架·19.1% vs 22.22% 结论相反）",
        "②「全部资产」口径的比例 → <b>口径不完整</b>（缺 IBKR/BitFlyer/BTC/ETH）",
        "③「今日无机会标的」→ <b>未完成筛选·非结论</b>",
        "④美股市值/权重/缺口 → <b>盘中价·近似值</b>",
        "⑤「今日不操作」→ <b>正式交易结论无效</b>；★安全执行状态仍为【暂缓交易】",
        "⑥加密资产口径 → <b>资产缺失·不可用</b>",
        "⑦「云盘料已处理」→ <b>仅扫描·未消化</b>（湖水4份自07-31未消化）",
        "⑧「组合期望回报／距+40%缺口」→ <b>预测陈旧·不可用于决策</b>（富途两版贡献度差 8.6pp·MSFT/NVDA/TSM/AVGO 五只主力锁于07-22~30·此后未重估·组合期望=★我不知道）",
    ]
    lis = "".join(f'<li style="margin:3px 0">{x}</li>' for x in items)
    dd = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:8])
    comp = ('<div style="margin-top:8px;font-size:12.5px">★临时合规状态声明（GPT V7 裁定第十九节）：'
            '本产品当日合规见 <b>output/compliance/完整产品当日合规报告_%s_人工版.html</b>·'
            'Release Gate 状态以页头标注为准（轮297 裁定：仅标注不拦停）。</div>' % dd)
    return ('<div style="background:#fdecea;border:3px solid #c0392b;border-radius:8px;padding:12px 16px;margin:8px 0 14px">'
            '<div style="font-size:16px;font-weight:900;color:#c0392b">🚩 今日结论降级清单（七类·第一屏置顶·不得只放文末）</div>'
            f'<ul style="margin:6px 0 0;padding-left:22px">{lis}</ul>{comp}</div>')


def forward_html(root, dc):
    """前瞻研究区·读 data/forward/forward_{dc}.json·★★★replace_low_efficiency_holdings 单独成块置顶·空→未填。"""
    import json as _j
    p = root / "data" / "forward" / f"forward_{dc}.json"
    if not p.exists():
        return f'<h2>前瞻研究区</h2><p>{UNFILLED}（forward_{dc}.json 不存在）</p>'
    try:
        f = _j.loads(p.read_text(encoding="utf-8"))
    except Exception as _e:
        return f'<h2>前瞻研究区</h2><p>{UNFILLED}（读取失败:{esc(str(_e)[:60])}）</p>'

    def _get(o, *names):
        for n in names:
            if n in o:
                return o[n]
        for k in o:
            for n in names:
                if str(k).lstrip("★ ") == str(n).lstrip("★ "):
                    return o[k]
        return None
    orr = f.get("opportunity_rotation", {}) or {}
    repl = _get(orr, "replace_low_efficiency_holdings", "★★★replace_low_efficiency_holdings")
    repl_block = ('<div style="border:3px solid #7B241C;border-radius:8px;padding:12px 15px;margin:6px 0 14px;background:#fdf0ee">'
                  '<div style="font-size:16px;font-weight:900;color:#7B241C">🔺 今日最实质结论：低效持仓是否替换（微软／爱德万）</div>'
                  f'<div style="margin-top:6px;font-size:13px">{_rv(repl) if repl not in (None, "", {}) else UNFILLED}</div></div>')
    fe = f.get("future_events", {}) or {}
    fe_rows = ""
    for hz, lbl in [("horizon_3d", "3日内"), ("horizon_30d", "30日内"), ("horizon_quarter", "本季度")]:
        lst = fe.get(hz) or []
        body = UNFILLED if not lst else "<br>".join(
            f'・<b>{esc(e.get("date"))}</b> {esc(e.get("type"))}｜{esc(e.get("subject"))}｜影响持仓：{_rv(e.get("affected_holdings"))}｜预期：{esc(e.get("expected_impact"))}' for e in lst)
        fe_rows += f'<tr><td><b>{lbl}</b></td><td>{body}</td></tr>'
    trends = f.get("trends") or []
    tr_rows = UNFILLED if not trends else "".join(
        f'<tr><td><b>{esc(t.get("trend_id"))}</b><br>{esc(t.get("name"))}</td><td>阶段：{esc(t.get("stage"))}</td>'
        f'<td><b>失效条件</b>：{_rv(t.get("invalidation_condition"))}<br><b>下一观察点</b>：{_rv(t.get("next_observation_point"))}</td></tr>' for t in trends)
    tr_html = UNFILLED if not trends else f'<table><tr><th>趋势</th><th>阶段</th><th>失效条件 / 下一观察点</th></tr>{tr_rows}</table>'
    SK = ["trigger", "evidence", "probability_or_confidence", "sector_impact", "holding_impact", "impact_on_40pct_path", "impact_on_100pct_path", "action", "invalidation_condition"]
    LBL = {"impact_on_40pct_path": "对+40%路径", "impact_on_100pct_path": "对+100%路径", "trigger": "触发", "evidence": "证据", "probability_or_confidence": "概率/置信", "sector_impact": "板块影响", "holding_impact": "持仓影响", "action": "动作", "invalidation_condition": "失效条件"}
    sc = f.get("scenarios", {}) or {}

    def _scell(o):
        if not o or all(o.get(k) in (None, "", [], {}) for k in SK):
            return UNFILLED
        return "".join(f'<div><b>{esc(LBL.get(k, k))}</b>：{_rv(o.get(k))}</div>' for k in SK if o.get(k) not in (None, "", [], {}))
    sc_rows = "".join(f'<tr><td><b>{lbl}</b></td><td>{_scell(sc.get(k, {}) or {})}</td></tr>' for k, lbl in [("base", "基准"), ("bull", "乐观"), ("bear", "悲观")])
    OR = ["strongest_trend_now", "likely_next_rotation", "sectors_in_expectation_forming", "sectors_crowded_or_realized", "watchlist", "why_not_buying_yet", "upgrade_trigger"]
    or_body = "".join(f'<div style="margin:3px 0"><b>{esc(k)}</b>：{_rv(orr.get(k))}</div>' for k in OR if k in orr) or UNFILLED
    _html = (f'<h2>前瞻研究区（未来事件／趋势／情景／机会轮动）{source_badge("OPUS_JUDGMENT", "Opus5前瞻研究")}</h2>'
             f'<p style="font-size:11px;color:#888">★数据源 forward_{dc}.json·空字段=Opus5未产出(如实标·不占位)。'
             f'★★★带 {SOURCE_LABEL_META["UNVERIFIED_RELAY"][0]} 标的＝Opus5自己写的未核项·不因是Opus5写就默认可信(丙·轮333)。</p>'
             f'{repl_block}'
             f'<h3 style="font-size:14px">未来事件（3日／30日／季度）</h3><table><tr><th>时窗</th><th>事件</th></tr>{fe_rows}</table>'
             f'<h3 style="font-size:14px">趋势（带失效条件与下一观察点）</h3>{tr_html}'
             f'<h3 style="font-size:14px">情景（base／bull／bear·各含对+40%/+100%路径）</h3><table><tr><th>情景</th><th>要素</th></tr>{sc_rows}</table>'
             f'<h3 style="font-size:14px">机会轮动</h3>{or_body}')
    # ★乙1/丙(轮333):Opus5自己写的未核项(待核/未查证/答不出/日期待核…)→标 UNVERIFIED_RELAY·不因是Opus5写就默认可信。
    _badge = source_badge("UNVERIFIED_RELAY")
    _html = _re.sub(r"(待核实|待查证|待核|未查证到|未查证|答不出|日期待核|存疑|无法确认|未核实)(?!</span>)",
                    lambda m: m.group(1) + _badge, _html)
    return fill_sector_tokens(root, dc, _html)   # ★甲(轮333):判断文字用{SS.格号.字段}占位符·渲染填当日实算值·查不到FAIL(取代轮332正则改写)


def fill_sector_tokens(root, dc, html):
    """★甲(轮333·根治轮332正则改写的越界):判断层文字用占位符 {SS.<格号>.<字段>} 写机器数·
    渲染时按 sector_strength 填【当日实算值】。★彻底取代 _sync_sector_readings 的正则改写(那是渲染层改判断文字·越界·§5.4禁的自由文本方式)。
    字段:r5/r20/r60(相对强度·带正负号两位小数)·n5/n20/n60(有效样本数·整数)。
    ★甲3:token 查不到值(格号缺/字段非法/文件缺)→ raise ValueError(渲染FAIL·宁可不出品不出陈旧数)。
       value=None(样本不足)→填「N/A」(合法·非陈旧)。无token→原样返回(no-op)。"""
    import json as _j
    if not _re.search(r"\{SS\.\d+\.(?:r5|r20|r60|n5|n20|n60)\}", html):
        return html                                     # 无token→不动(no-op)
    dh = dc if "-" in dc else "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    p = root / "data" / "market" / f"sector_strength_{dh}.json"
    try:
        ss = _j.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"[SS-token] 前瞻含板块强度token但 sector_strength_{dh}.json 读不到({type(e).__name__})→渲染FAIL·不出陈旧数")
    rows = {r.get("格号"): r for r in ss.get("18格强度(按5日相对强度降序)", [])}
    FIELD = {"r5": ("5日相对强度", "rs"), "r20": ("20日相对强度", "rs"), "r60": ("60日相对强度", "rs"),
             "n5": ("5日", "n"), "n20": ("20日", "n"), "n60": ("60日", "n")}

    def _sub(m):
        gno, fld = int(m.group(1)), m.group(2)
        r = rows.get(gno)
        if r is None:
            raise ValueError(f"[SS-token] {{SS.{gno}.{fld}}} 的格{gno}不在 sector_strength→渲染FAIL(不静默跳过)")
        key, kind = FIELD[fld]
        v = (r.get("有效样本数", {}) or {}).get(key) if kind == "n" else r.get(key)
        if v is None:
            return "N/A"
        return f"{v:+.2f}" if kind == "rs" else f"{int(v)}"
    return _re.sub(r"\{SS\.(\d+)\.(r5|r20|r60|n5|n20|n60)\}", _sub, html)


def _scan_judgments(root, dc):
    """通用扫描个股重估·按标的取最高版本(不 sorted[-1])。返回 [(tkr, ver, relpath)]。"""
    vdir = root / "data" / "valuation"
    jfiles = _g.glob(str(vdir / f"*_opus5_judgment_v*_{dc}.json")) + _g.glob(str(vdir / f"*_opus5_judgment_{dc}.json"))
    by = {}
    for fp in jfiles:
        base = _re.sub(r".*[\\/]", "", fp)
        tkr = _re.sub(r"_opus5_judgment.*", "", base)
        mv = _re.search(r"_v(\d+)_", base)
        ver = int(mv.group(1)) if mv else 1
        if tkr not in by or ver > by[tkr][0]:
            by[tkr] = (ver, str(Path(fp).relative_to(root)).replace("\\", "/"))
    return [(t, v[0], v[1]) for t, v in sorted(by.items())]


def deepdive_judgments(root, dc):
    """★个股深度重估(持仓层)→册2。通用扫描·空→本日无个股重估。"""
    js = _scan_judgments(root, dc)
    if not js:
        return '<h2>持仓层 · 深度重估</h2><p style="color:#888">本日无个股深度重估产出。</p>'
    out = '<h2 style="color:#7B241C;border-left:5px solid #7B241C;padding-left:8px">持仓层 · 深度重估（★通用扫描·按标的取最高版本）</h2>'
    for tkr, ver, rel in js:
        out += ('<div style="border:2px solid #7B241C;border-radius:8px;padding:8px 12px;margin:8px 0;background:#fdf7f5">'
                + opus_sections(root, rel, f"{tkr} 重估（v{ver}·最新版）", "#7B241C") + '</div>')
    return out


def deepdive_peers(root, dc):
    """★同业对照(板块层)→册3。通用扫描 peer_*_{dc}.json·空→本日无同业对照。"""
    pfiles = sorted(_g.glob(str(root / "data" / "valuation" / f"peer_*_{dc}.json")))
    if not pfiles:
        return '<h2>板块层 · 同业对照</h2><p style="color:#888">本日无同业对照产出。</p>'
    out = '<h2 style="color:#12324e;border-left:5px solid #12324e;padding-left:8px">板块层 · 同业对照（★通用扫描·★口径差异注·不作精确比较）</h2>'
    for fp in pfiles:
        rel = str(Path(fp).relative_to(root)).replace("\\", "/")
        nm = _re.sub(r"\.json$", "", _re.sub(r".*[\\/]peer_", "", fp)).replace("_" + dc, "")
        out += ('<div style="border:2px solid #12324e;border-radius:8px;padding:8px 12px;margin:8px 0;background:#f4f8fc">'
                + opus_sections(root, rel, f"同业对照 {nm}", "#12324e") + '</div>')
    return out


def overdue_verdict_html(root, dc):
    """★轮341乙3:见分晓日已过却未记分→册1第一屏红条『★有N条预测到期未记分·记分卡当前不可信』。
    读 overdue_verdict_{dc}.json(overdue_verdict_gate产出)·0条→不出(静默)。"""
    import json as _json
    try:
        d = _json.loads((root / "data" / "pdca" / f"overdue_verdict_{dc}.json").read_text(encoding="utf-8"))
    except Exception:
        return ""
    ov = d.get("逐条", []) or []
    if not ov:
        return ""
    rows = "".join(f'<li>{esc(o.get("标的"))} {esc(o.get("horizon"))}·见分晓 {esc(o.get("见分晓日"))}·逾期 <b>{esc(o.get("逾期天数"))}</b> 天</li>' for o in ov)
    return ('<div style="border:3px solid #c0392b;background:#fdecea;border-radius:8px;padding:11px 15px;margin:10px 0">'
            f'<div style="font-size:17px;font-weight:900;color:#c0392b">★有 {len(ov)} 条预测到期未记分，记分卡当前不可信</div>'
            '<div style="font-size:12px;color:#7B241C;margin-top:3px">这些预测的见分晓日已过、却还没记分——记分卡的对错统计里缺了它们，'
            '现在看到的胜率不完整。★记分是 Opus5 的活（料已备在 overdue_scoring_prep）。</div>'
            f'<ul style="margin:6px 0 0 18px;font-size:12.5px;color:#233">{rows}</ul></div>')


def scoring_disclosure_html(root, dc):
    """★轮342乙2:Opus5补记逾期预测后·第一屏印一句(一字不改·不折叠)。读 opus5_scoring_{dc}.json 的『★我要求把这句印进产品』。无文件→不出(静默)。"""
    import json as _json
    try:
        d = _json.loads((root / "data" / "pdca" / f"opus5_scoring_{dc}.json").read_text(encoding="utf-8"))
    except Exception:
        return ""
    sent = ((d.get("★记完之后的诚实结论", {}) or {}).get("★我要求把这句印进产品")
            or (d.get("★记完之后的诚实结论", {}) or {}).get("对记分卡的影响"))
    if not sent:
        return ""
    return ('<div style="border:3px solid #8e44ad;background:#f6effa;border-radius:8px;padding:12px 16px;margin:10px 0">'
            '<div style="font-size:13px;font-weight:900;color:#6c3483;margin-bottom:4px">★记分卡诚实披露（Opus5 补记后·一字不改）</div>'
            f'<div style="font-size:15px;font-weight:800;color:#4a235a;line-height:1.55">{esc(sent)}</div>'
            '<div style="font-size:11.5px;color:#7d6a8a;margin-top:5px">★记分卡变难看，正是它开始可信的标志。</div></div>')


def first_screen_decisions_html(root, dc):
    """★轮342丙3:册1第一屏三段(整块·不折叠·不缩小)——数字全从 four_account_current_{dc}.json 现取(不写死)。
    ①今日0笔的理由 ②破线(防御<15%·日股>30%·请裁定) ③跨账户占股票市值%(四账户独立看会被拆两半)。文件缺→段内如实标『数据缺·未取到』。"""
    import json as _json
    fa = {}
    try:
        fa = _json.loads((root / "data" / "accounts" / f"four_account_current_{dc}.json").read_text(encoding="utf-8"))
    except Exception:
        fa = {}
    dfn = fa.get("★防御仓(机器可识别=保险·当前源)", {}) or {}
    jp = fa.get("★日股占比(甲3③)", {}) or {}
    cx = fa.get("★跨账户占股票总值(71.2%类比·重算)", {}) or {}
    ai = fa.get("★AI资本开支集中度(甲3②)", {}) or {}
    def _num(v):
        return v if isinstance(v, (int, float)) else "（数据缺·未取到）"
    def_pct = _num(dfn.get("占四账户股票%")); jp_pct = _num(jp.get("占四账户股票%"))
    cx_pct = _num(cx.get("占比%")); cx_n = cx.get("跨账户标的数", "（缺）")
    ai_pct = _num(ai.get("占比%")); ai_legs = ai.get("命中腿", []) or []
    ai_accts = len({str(x).split("@")[-1].split("(")[0] for x in ai_legs}) if ai_legs else "（缺）"
    def_break = dfn.get("★是否破线(<15%)"); jp_break = jp.get("★是否破线(>30%)")
    ai_break = isinstance(ai_pct, (int, float)) and ai_pct > 30   # AI同源 vs 单一驱动30%上限
    seg1 = ('<li style="margin:6px 0"><b>今日 0 笔的理由</b>：重估未完成，我没有资格动手——'
            '<b>不是</b>看过了、决定拿着。（0 笔≠已审阅通过，是"还没到能动手的程度"。）</li>')
    seg2 = ('<li style="margin:6px 0"><b>★三条线同时破，而今天 0 笔——请董事长裁定</b>：'
            f'①防御仓 <b>{esc(def_pct)}%</b> {"＜ 15% 下限 ✗" if def_break else "（未破）"}'
            f'（机器只认保险=东京海上·完整防御分类归 Opus5）；'
            f'②日股 <b>{esc(jp_pct)}%</b> {"＞ 30% 上限 ✗" if jp_break else "（未破）"}；'
            f'③AI 同源 <b>{esc(ai_pct)}%</b> {"＞ 30% 单一驱动上限 ✗" if ai_break else "（未破）"}。'
            '请裁定：补防御/降日股/降 AI 同源，还是改尺放宽。</li>')
    seg3 = (f'<li style="margin:6px 0"><b>同源风险（今天才第一次被算出来）</b>：AI 资本开支组占股票市值 '
            f'<b>{esc(ai_pct)}%</b>，横跨 <b>{esc(ai_accts)}</b> 个账户（{esc(len(ai_legs))} 条腿）。'
            f'★四账户各自独立看时，这个数<b>不出现在任何一张表上</b>——不是被算错，是根本没被算过。</li>')
    seg4 = (f'<li style="margin:6px 0"><b>跨账户集中</b>：<b>{esc(cx_n)}</b> 只标的横跨多账户，'
            f'占股票市值 <b>{esc(cx_pct)}%</b>——四账户独立看会被拆成两半各看一段。'
            f'{("（07-02 全快照曾＝71.2%/7只；本轮当前源＝" + str(cx_pct) + "%/" + str(cx_n) + "只·富途已清仓东京海上退出集合。）") if isinstance(cx_pct, (int, float)) else ""}</li>')
    return ('<div style="border:3px solid #b9770e;background:#fff8ec;border-radius:8px;padding:13px 17px;margin:12px 0">'
            '<div style="font-size:16px;font-weight:900;color:#8a5a00;margin-bottom:6px">★今日必须知情/裁定（不折叠·数字现取）</div>'
            f'<ul style="margin:4px 0 0 6px;font-size:13.5px;color:#3a2e12;list-style:none;padding-left:0">{seg1}{seg2}{seg3}{seg4}</ul>'
            '<div style="font-size:11px;color:#9a7b3a;margin-top:6px">★数字从 four_account_current 现取（源日:富途08-08/SBI08-05/IBKR07-02）·非写死。四件推论+记分卡披露见正文第四/五节。裁定=董事长/Opus5。</div></div>')


def four_account_tables_html(root, dc):
    """★轮342甲2/丙1:四账户各自独立表(占本账户%·标账户名·各账户源日不同逐处标)。读 four_account_current_{dc}.json。
    ★董事长08-09拍板:四账户各自独立·不做总资产表。crypto单独列不进股票分母。文件缺→不出(静默)。"""
    import json as _json
    try:
        fa = _json.loads((root / "data" / "accounts" / f"four_account_current_{dc}.json").read_text(encoding="utf-8"))
    except Exception:
        return ""
    tabs = fa.get("四账户独立表", {}) or {}
    order = ["富途", "SBI", "IBKR"]
    blocks = ""
    for name in order:
        t = tabs.get(name) or {}
        rows = t.get("逐只", []) or []
        if not rows:
            continue
        tr = "".join(
            f'<tr><td><b>{esc(r.get("标的"))}</b>{("·" + esc(r.get("name"))) if r.get("name") else ""}</td>'
            f'<td style="text-align:right">{esc(r.get("股数"))}</td>'
            f'<td style="text-align:right">${esc(int(r.get("市值USD", 0)))}</td>'
            f'<td style="text-align:right"><b>{esc(r.get("占本账户%"))}%</b></td></tr>' for r in rows)
        blocks += (
            f'<div style="margin:10px 0;border:1px solid #bcd;border-radius:7px;overflow:hidden">'
            f'<div style="background:#eaf2fb;padding:7px 12px;font-size:13.5px;font-weight:800;color:#12324e">'
            f'账户【{esc(name)}】· 源日 {esc(t.get("源日"))} · {esc(t.get("新鲜度"))} · 账户股票 ${esc(int(t.get("账户股票市值USD", 0)))}</div>'
            f'<table style="width:100%;border-collapse:collapse;font-size:12.5px">'
            f'<tr style="background:#f6f9fc"><th style="text-align:left;padding:3px 8px">标的</th><th style="text-align:right;padding:3px 8px">股数</th>'
            f'<th style="text-align:right;padding:3px 8px">市值USD</th><th style="text-align:right;padding:3px 8px">占本账户%</th></tr>{tr}</table></div>')
    # bitFlyer crypto(单独·不进股票分母)
    bf = (tabs.get("bitFlyer(crypto·不进股票分母)") or {}).get("逐只", []) or []
    bf_html = ""
    if bf:
        br = "".join(f'<li>{esc(c.get("币种"))} {esc(c.get("数量"))} · ${esc(int(c.get("市值USD_0702", 0)))}（07-02快照）</li>' for c in bf)
        bf_html = (f'<div style="margin:8px 0;padding:8px 12px;background:#fef8ee;border:1px dashed #c9a24b;border-radius:6px;font-size:12.5px">'
                   f'<b>bitFlyer（加密·单独列·不进股票分母）</b><ul style="margin:4px 0 0 16px">{br}</ul></div>')
    return ('<div style="border:2px solid #2c6e9a;border-radius:8px;padding:11px 14px;margin:12px 0;background:#fbfdff">'
            '<div style="font-size:15px;font-weight:900;color:#12324e">四账户各自独立表（占本账户%·非总资产·董事长08-09拍板）</div>'
            '<div style="font-size:11.5px;color:#567;margin:3px 0 6px">★每账户源日不同已逐处标：富途08-08实时 / SBI08-05快照 / IBKR07-02静止。四账户独立看·全局只看两个跨账户数(见第一屏/册1)。</div>'
            f'{blocks}{bf_html}</div>')


def anchor_drift_html(root, dc):
    """★轮335 乙2:E-ID内容锚漂移→产品红条。读 anchor_drift_{dc}.json(evidence_anchor_check 产出)。
    某层引用的证据当日已变→大字红条『本层判断引用的证据已变·须重判·不得沿用』(附原文/今日对照)。无漂移→不出(静默·乙3)。"""
    import json as _json
    try:
        d = _json.loads((root / "data" / "pipeline" / f"anchor_drift_{dc}.json").read_text(encoding="utf-8"))
    except Exception:
        return ""                                    # 无比对结果→不出(不误报)
    drift_layers = [L for L in d.get("逐层", []) if L.get("漂移数", 0) > 0]
    if not drift_layers:
        return ""                                    # 全相符→静默(乙3·不打扰)
    rows = ""
    for L in drift_layers:
        for dft in L.get("漂移明细", []):
            rows += (f'<li><b>{esc(L["层"])}</b>·{esc(dft.get("E-ID"))} {esc(dft.get("情形"))}：'
                     f'锚原文『{esc(dft.get("锚原文前40"))}』→ 今日『{esc(dft.get("今日前40") or dft.get("今日", ""))}』</li>')
    return ('<div style="border:3px solid #c0392b;background:#fdecea;border-radius:8px;padding:11px 15px;margin:10px 0">'
            '<div style="font-size:17px;font-weight:900;color:#c0392b">★本层判断引用的证据已变，判断须重判，不得沿用</div>'
            f'<div style="font-size:12px;color:#7B241C;margin-top:3px">{len(drift_layers)} 个层的引用证据在当日重生成后内容已变（编号不变·内容变）——'
            '这些层的判断挂在旧证据上，★不得直接沿用，须 Opus5 按当日证据重判。</div>'
            f'<ul style="margin:6px 0 0 18px;font-size:12px;color:#233">{rows}</ul></div>')


def sector_split_html(root, dc):
    """★轮330 甲A4:拆格(格18国防军工/格19网络安全)板块强度→册3机会板块。
    ★格19不得从每日产品消失(GPT V7 指定):至少显示 enabled/activated 两态 + GPT 固定文案。
    ★读 sector_strength_{date}.json(核心口径·邻接单列不参与)·空→标未产出(不编)。"""
    import json as _json
    dh = dc if "-" in dc else "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    p = root / "data" / "market" / f"sector_strength_{dh}.json"
    try:
        d = _json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return ('<h2 style="color:#12324e;border-left:5px solid #12324e;padding-left:8px">板块层 · 拆格强度（国防军工/网络安全）</h2>'
                '<p style="color:#888">本日无拆格强度产出（sector_strength 未产出·如实标·不编）。</p>')
    rows = {r.get("格号"): r for r in d.get("18格强度(按5日相对强度降序)", [])}
    f19 = d.get("★格19两字段(A3)", {}) or {}

    def _rs(v):   # 相对强度值·缺失→N/A(不渲成None/空)
        return esc(v) if isinstance(v, (int, float)) else "N/A"

    def _pct(v):  # 涨跌%·缺失(如SPCX上市不足60日)→N/A(不渲成空紧跟%)·甲3
        return (f"{esc(v)}%" if isinstance(v, (int, float)) else "N/A（历史不足）")

    def _n(v):    # 样本数
        return esc(v) if v is not None else "—"

    def _cn_bool(v, yes, no):  # bool→中文(甲2:不把Python True/False印给董事长)
        return yes if v is True else (no if v is False else "待接")

    def _cell_html(no, title, color):
        r = rows.get(no)
        if not r:
            return f'<div style="color:#888;margin:6px 0">{esc(title)}：本日无产出</div>'
        vs = r.get("有效样本数", {})
        adj = r.get("★邻接(不参与)", [])
        adj_perf = r.get("★邻接单列表现(A2·不进核心平均)", []) or []
        body = (f'<div style="font-size:13px;color:#233"><b>核心篮子</b> {esc(r.get("成分股数"))} 只（只核心参与强度·邻接不参与）</div>'
                f'<div style="font-size:13px;margin-top:3px">相对强度：'
                f'5日 <b>{_rs(r.get("5日相对强度"))}</b> ／ 20日 <b>{_rs(r.get("20日相对强度"))}</b> ／ '
                f'60日 <b>{_rs(r.get("60日相对强度"))}</b>（60日=近三个月·非长期）{source_badge("MACHINE_OBSERVATION")}</div>'
                f'<div style="font-size:12px;color:#556;margin-top:2px">有效样本数：5日 {_n(vs.get("5日"))} ／ 20日 {_n(vs.get("20日"))} ／ 60日 {_n(vs.get("60日"))}（&lt;3只则该周期不出数）</div>')
        if adj:
            perf = "".join(f'<li>{esc(a.get("symbol"))}：5日 {_pct(a.get("5日%"))} ／ 20日 {_pct(a.get("20日%"))} ／ 60日 {_pct(a.get("60日%"))}（单列·不进核心平均）</li>'
                           for a in adj_perf if a.get("symbol"))
            body += (f'<div style="font-size:12px;color:#7a5a00;margin-top:3px"><b>邻接观察池</b>（不参与强度/候选·单列）：{esc("、".join(adj))}</div>'
                     + (f'<ul style="margin:2px 0 2px 16px;font-size:11.5px;color:#555">{perf}</ul>' if perf else ""))
        return (f'<div style="border:1px solid {color};border-left:6px solid {color};border-radius:8px;'
                f'background:#fbfcfe;padding:9px 12px;margin:8px 0">'
                f'<div style="font-size:14.5px;font-weight:800;color:{color}">{esc(title)}</div>{body}</div>')

    g19_status = (f'<div style="font-size:12px;color:#12324e;margin-top:3px">'
                  f'格19状态：{_cn_bool(f19.get("cell19_enabled"), "已启用", "未启用")}·'
                  f'{_cn_bool(f19.get("cell19_activated"), "已激活", "未激活（强趋势观察·驱动待核）")}'
                  f'（★不因价格自动升激活）{source_badge("MACHINE_OBSERVATION", "60日强度=当日实算")}</div>'
                  f'<div style="font-size:12.5px;color:#7B241C;margin-top:3px;padding:5px 8px;background:#fdf5f5;border-radius:6px">'
                  f'{esc(f19.get("★A4固定文案") or "网络安全：60日强度为强趋势观察方向；因 ARR、RPO、订阅增长等驱动证据尚未完成，不自动升级为正式候选。")}'
                  f'{source_badge("OPUS_JUDGMENT", "激活判定归Opus5·驱动证据")}</div>')
    return ('<h2 style="color:#12324e;border-left:5px solid #12324e;padding-left:8px">板块层 · 拆格强度（国防军工格18 / 网络安全格19）</h2>'
            '<div style="font-size:11.5px;color:#888;margin-bottom:4px">★口径：只核心篮子参与强度·邻接单列不参与（GPT V7 拆格裁定 v3 落入 Current）。★是否激活须驱动证据·强度不构成激活依据。</div>'
            + _cell_html(18, "格18 · 国防军工/太空（核心11只·SPCX降邻接单列）", "#2f6b4f")
            + _cell_html(19, "格19 · 网络安全（核心5只·GPT V7 已批准启用）", "#3a6ea5")
            + g19_status)


def _extract_body(root, relpath):
    """★轮318 D1:抽 <body> 内正文·去 head/style/script/首个h1·★原文不摘要不截断。缺失返回None。"""
    p = root / "00_请先看这里" / relpath
    if not p.exists():
        return None
    raw = p.read_text(encoding="utf-8", errors="replace")
    m = _re.search(r"<body[^>]*>(.*?)</body>", raw, _re.S | _re.I)
    inner = m.group(1) if m else raw
    inner = _re.sub(r"<script.*?</script>", "", inner, flags=_re.S | _re.I)
    inner = _re.sub(r"<style.*?</style>", "", inner, flags=_re.S | _re.I)
    inner = _re.sub(r"<h1[^>]*>.*?</h1>", "", inner, count=1, flags=_re.S | _re.I)   # 去首个大标题(横幅)
    return inner


# ★轮337 甲:层号→右栏尺文件(与 right_column_html 的 layers 同源·左→右锚取条文摘录用)。
_LAYER_RULER_FILES = {
    "①": ["右栏_完整世界观描述.html"],
    "②": ["右栏_完整国家战略地图.html"],
    "③": ["右栏_资金流动完整机制.html", "正式尺_资金流动层判定标准表_v1_20260802.html"],
    "④": ["右栏_板块地图.html"],
    "⑤": ["右栏_过滤标准筛选规则.html", "护城河分析框架.html", "右栏_估值方法学.html"],
    "⑥": ["右栏_持仓完整档案.html"],
    "⑦": ["⑦复盘记分卡层_完整设计.html", "PDCA记分规则准绳.html"],
}


def _ruler_excerpt(root, num, limit=80):
    """★轮337 甲1③:从该层右栏尺文件抽【关键条文原文摘录】(30~80字·非尺名)·供册1原地对照。缺→标未取到。"""
    for fn in _LAYER_RULER_FILES.get(num, []):
        body = _extract_body(root, fn)
        if not body:
            continue
        txt = _re.sub(r"<[^>]+>", "", body)
        txt = _re.sub(r"\s+", "", txt)
        # 跳过纯标题/日期开头·取第一段有实质内容(含标点)的
        m = _re.search(r"[^。；\n]{20,%d}[。；]" % limit, txt)
        seg = (m.group(0) if m else txt[:limit]).strip()
        if len(seg) >= 12:
            return seg[:limit], fn
    return "", ""


def _layer_judgment_map(root, dc):
    """★轮336 甲2/轮337 甲1:读 judgment_slots_{dc}·抽每层{层号:{判断,依据尺,与尺是否矛盾}}·供左右咬合(双向)。
    ★用 Opus5 已填的『依据右栏哪把尺』『与尺是否矛盾』字段做连接点(不另起炉灶)。缺/未填→该层无咬合。"""
    import json as _json
    out = {}
    try:
        d = _json.loads((root / "data" / "pipeline" / f"judgment_slots_{dc}.json").read_text(encoding="utf-8"))
    except Exception:
        return out
    for L, v in (d.get("②~⑦层工单", {}) or {}).items():
        s = (v.get("槽位", {}) or {})
        num = L[0] if L and L[0] in "①②③④⑤⑥⑦" else None
        jd = s.get("本层判断")
        ruler = s.get("★依据右栏哪把尺(①~⑥·E8必填)")
        conflict = s.get("★与尺是否矛盾(E8枚举·必填)")
        jtxt = _fmt_judgment(jd)   # ★轮344:六格dict→拼可读文本·跳过None子格(治str(dict)把 None 字面量印进产品)
        if num and jtxt and jtxt not in ("", "None"):
            out[num] = {"判断": jtxt, "依据尺": str(ruler or "").strip(),
                        "与尺是否矛盾": str(conflict or "").strip()}
    return out


def _fmt_judgment(jd):
    """★轮344:本层判断可能是字符串(如②)或六格dict(如③·C-3)。dict→拼非空子格值·跳过None与下划线键·
    ★绝不 str(dict) 直接印(会把未填子格的 Python None 字面量印给董事长·违红线『不许印None』)。"""
    if jd is None:
        return ""
    if isinstance(jd, str):
        return jd.strip()
    if isinstance(jd, dict):
        parts = []
        for k, val in jd.items():
            if str(k).startswith("_"):
                continue
            if val is None or str(val).strip() in ("", "None"):
                continue
            parts.append(str(val).strip())
        return " · ".join(parts)
    return str(jd)


def layer_ruler_anchor_html(root, dc, num):
    """★轮337 甲1:册1每层判断【旁边】的右栏锚——依据哪把尺+与尺是否矛盾(矛盾/空→红条)+该尺关键条文摘录+看册5指引。
    ★左→右咬合(董事长在册1原地就能对照·不必翻册5)。该层无判断→返回空(不硬凑)。"""
    jmap = _layer_judgment_map(root, dc)
    j = jmap.get(num)
    if not j:
        return ""
    ruler = j.get("依据尺", "")
    conflict = j.get("与尺是否矛盾", "")
    judged = j.get("判断", "")
    excerpt, fn = _ruler_excerpt(root, num)
    # 甲2:与尺是否矛盾=矛盾/空→红条
    is_bad = (not conflict) or ("矛盾" in conflict and "不矛盾" not in conflict)
    conflict_html = (f'<div style="border:2px solid #c0392b;background:#fdecea;border-radius:5px;padding:4px 8px;margin-top:3px;'
                     f'font-size:12px;font-weight:800;color:#c0392b">★本层判断与右栏尺不一致／未声明，须裁定（与尺是否矛盾＝{esc(conflict or "空")}）</div>'
                     if is_bad else
                     f'<span style="font-size:11px;color:#0f7b3f">与尺：{esc(conflict)}</span>')
    return (f'<div style="border-left:3px solid #12324e;background:#f4f8fc;border-radius:5px;padding:6px 9px;margin-top:4px;font-size:11.5px">'
            + (f'<div style="color:#12324e;margin-bottom:3px"><b>本层判断(Opus5)</b>：{esc(str(judged)[:140])}…</div>' if judged else "")
            + f'<b style="color:#12324e">▶ 依据的右栏尺</b>：{esc(ruler) or "★未声明依据尺"}　{conflict_html}'
            + (f'<div style="margin-top:3px;color:#334"><b>关键条文摘录</b>：「{esc(excerpt)}」<span style="color:#888">（{esc(fn)}）</span></div>' if excerpt else
               '<div style="margin-top:3px;color:#c0392b">★该尺关键条文未取到（尺文件缺/空）</div>')
            + '<div style="font-size:10.5px;color:#888;margin-top:2px">看完整尺 → 册5·规则附件（对应层）</div></div>')


def right_column_html(root, dc):
    """★★★轮318 D1(挂17天):右栏六块底子(尺)原文并入·按V7七层因果链归位·grid左右并排(窄屏堆叠)·<details>默认收起·全在同页(不跳链)。
    ★轮336 甲2:左侧改为【左右咬合】——显示今天哪层判断用到了本块尺(依据右栏哪把尺·Opus5已填)·咬不上如实标『本块今日无左栏引用』。"""
    jmap = _layer_judgment_map(root, dc)
    layers = [
        ("①事实层 · 世界观", ["右栏_完整世界观描述.html"]),
        ("②政策层 · 国家战略地图", ["右栏_完整国家战略地图.html"]),
        ("③资金层 · 资金流动机制", ["右栏_资金流动完整机制.html", "正式尺_资金流动层判定标准表_v1_20260802.html"]),
        ("④板块层 · 板块地图", ["右栏_板块地图.html"]),
        ("⑤公司/机会层 · 筛选·护城河·估值", ["右栏_过滤标准筛选规则.html", "护城河分析框架.html", "右栏_估值方法学.html", "右栏_估值方法学_增补_两把尺.html"]),
        ("⑥组合层 · 持仓完整档案", ["右栏_持仓完整档案.html"]),
        ("⑦复盘记分卡层", ["⑦复盘记分卡层_完整设计.html", "正式尺_复盘记分卡层设计_v1_20260802.html", "PDCA记分规则准绳.html"]),
    ]
    css = ('<style>.rcgrid{display:grid;grid-template-columns:minmax(180px,1fr) 2fr;gap:12px;align-items:start}'
           '@media(max-width:760px){.rcgrid{grid-template-columns:1fr}}'
           '.rcbox{border:2px solid #12324e;border-radius:8px;padding:10px 14px;margin:12px 0;background:#fff}'
           '.rcleft{background:#eef3f8;border-radius:6px;padding:8px 10px;font-size:12.5px}'
           '.rcright details{margin:6px 0;border:1px solid #ccc;border-radius:6px;padding:4px 8px}'
           '.rcright summary{cursor:pointer;font-weight:700;color:#12324e}'
           '.rcright details>div{margin-top:8px;font-size:12px;max-height:none;overflow-x:auto}</style>')
    blocks = ""
    ok, fail = 0, 0
    for title, fs in layers:
        right = ""
        for fn in fs:
            body = _extract_body(root, fn)
            if body is None:
                right += f'<p style="color:#c0392b">★本层底子缺失·源文件 <b>{esc(fn)}</b> 未找到</p>'
                fail += 1
            else:
                right += f'<details><summary>📜 {esc(fn)}（点开看完整原文底子）</summary><div>{body}</div></details>'
                ok += 1
        # ★轮336 甲2/甲3:左右咬合——本块(层号)今天被哪层判断用到(依据右栏哪把尺)·咬不上如实标。
        _num = title[0] if title and title[0] in "①②③④⑤⑥⑦" else None
        _jd = jmap.get(_num) if _num else None
        if _jd:
            _sum, _ruler = _jd.get("判断", ""), _jd.get("依据尺", "")
            left = (f'<div style="font-size:12px;font-weight:800;color:#0f7b3f;margin-bottom:3px">✓ 今天左栏用到了本块尺</div>'
                    f'<div style="font-size:12px;color:#233"><b>本层判断</b>：{esc(_sum[:110])}…</div>'
                    + (f'<div style="font-size:11px;color:#556;margin-top:3px"><b>依据右栏哪把尺</b>：{esc(_ruler[:80])}</div>' if _ruler else "")
                    + '<div style="font-size:10.5px;color:#888;margin-top:2px">（连接点＝判断工单「依据右栏哪把尺」·非另起炉灶）</div>')
        else:
            left = ('<div style="font-size:12px;font-weight:700;color:#c0392b">★本块今日无左栏引用</div>'
                    '<div style="font-size:11px;color:#888;margin-top:2px">（该层判断工单未填/客观空·或本块为慢变底子今日未被引用·如实标·不假装咬上）</div>')
        blocks += (f'<div class="rcbox"><div style="font-size:15px;font-weight:800;color:#12324e;margin-bottom:6px">{esc(title)}</div>'
                   f'<div class="rcgrid"><div class="rcleft">{left}</div>'
                   f'<div class="rcright">{right}</div></div></div>')
    return (css + '<h2 style="color:#12324e;border-left:5px solid #12324e;padding-left:8px">右栏六块底子 · 尺（V7七层因果链归位·★原文并入不摘要·同页折叠）</h2>'
            f'<p style="font-size:11px;color:#888">★慢变尺原文·左=今日判断(见七层管道)/右=该层完整底子(details默认收起)。并入 {ok} 份·缺失 {fail} 份。</p>' + blocks)


def ledger_html(root, dc):
    """★★★轮319:任务台账A3摘要(第一屏)+A4锁。挂起天数=今天-created·连续未动=今天-last_touched(自动算)。
    A4:opus5_last_read_date != 今天 → 第一屏红字『Opus5本轮未读任务台账』。"""
    import json as _j
    from datetime import date as _date, datetime as _dt, timezone as _tz, timedelta as _td
    p = root / "data" / "tasks" / "task_ledger.json"
    if not p.exists():
        return '<div style="color:#c0392b">★任务台账 task_ledger.json 未找到</div>'
    d = _j.loads(p.read_text(encoding="utf-8"))
    today = _dt.now(_tz(_td(hours=9))).date()   # ★挂起天数用【真实今天】(JST)·非产品数据日

    def _gap(ds):
        try:
            return (today - _date(int(ds[:4]), int(ds[5:7]), int(ds[8:10]))).days
        except Exception:
            return None
    tasks = d.get("tasks", [])
    unfinished = [t for t in tasks if t.get("status") != "已完成"]
    over7 = [t for t in unfinished if (_gap(t.get("created_date")) or 0) > 7]
    longest = max(unfinished, key=lambda t: (_gap(t.get("created_date")) or 0), default=None)
    ld = _gap(longest.get("created_date")) if longest else 0
    a3 = (f'当前未完成 <b>{len(unfinished)}</b> 项 ｜ 挂超7天 <b>{len(over7)}</b> 项 ｜ '
          f'最久一项：<b>{esc(longest.get("title","")[:30]) if longest else "无"}</b>（已挂 <b>{ld}</b> 天）')
    # A4:Opus5读台账锁
    lr = d.get("opus5_last_read_date")
    dd_h = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:8])
    a4 = ("" if lr == dd_h else
          '<div style="background:#7B241C;color:#fff;padding:6px 12px;border-radius:6px;margin:4px 0;font-weight:800">⚠ Opus5 本轮未读任务台账（opus5_last_read_date≠今天）</div>')
    # 挂超7天明细
    rows = "".join(
        f'<tr><td>{esc(t.get("task_id"))}</td><td>{esc(t.get("title")[:40])}</td><td>{esc(t.get("owner"))}</td>'
        f'<td>{esc(t.get("status"))}</td><td style="color:#c0392b;font-weight:700">{_gap(t.get("created_date"))}天</td><td>{esc(t.get("priority"))}</td></tr>'
        for t in sorted(over7, key=lambda t: -(_gap(t.get("created_date")) or 0)))
    return ('<div style="background:#fff3cd;border:3px solid #d9a400;border-radius:8px;padding:12px 16px;margin:8px 0 14px">'
            '<div style="font-size:15px;font-weight:900;color:#8a6d00">📋 任务台账（防跑偏·第一屏·轮319）</div>'
            f'{a4}<div style="font-size:13.5px;margin:6px 0">{a3}</div>'
            + (f'<details open><summary style="cursor:pointer;font-weight:700">挂超7天明细 {len(over7)} 项</summary>'
               f'<table style="font-size:12px"><tr><th>id</th><th>标题</th><th>owner</th><th>状态</th><th>挂起</th><th>P</th></tr>{rows}</table></details>' if over7 else '')
            + '</div>')


def contribution_two_way_html(root, dc):
    """★★★轮322 A2/A3:账户期望贡献两版并列(锁定时原判断 vs 当前价影子)+差额陈旧度·差>5pp红字·防误读。读target_gap ★轮322块。"""
    import json as _j
    p = root / "data" / "target" / f"target_gap_{dc}.json"
    if not p.exists():
        return ""
    d = _j.loads(p.read_text(encoding="utf-8"))
    tw = d.get("★轮322_两版贡献度与陈旧度")
    if not tw:
        return ""
    lk = tw.get("按锁定时原判断", {}); cu = tw.get("按当前价影子", {}); diff = tw.get("差额(判断陈旧度)", {})
    stale_acc = tw.get("★差>5pp账户_期望不可用于决策", [])
    rows = ""
    for acc in ["富途", "SBI"]:
        dv = diff.get(acc)
        flag = ' <b style="color:#c0392b">⚠期望不可用于决策</b>' if acc in stale_acc else ''
        rows += (f'<tr><td><b>{esc(acc)}</b></td><td>{esc(lk.get(acc))}pp</td><td>{esc(cu.get(acc))}pp</td>'
                 f'<td style="color:#c0392b;font-weight:700">{esc(dv)}pp{flag}</td></tr>')
    warn = ('<div style="background:#7B241C;color:#fff;padding:6px 12px;border-radius:6px;margin:6px 0;font-weight:800">'
            f'★账户 {esc("、".join(stale_acc))} 预测已显著陈旧（差>5pp）·期望回报不可用于决策</div>' if stale_acc else '')
    return ('<div style="background:#fff8f0;border:2px solid #7B241C;border-radius:8px;padding:10px 14px;margin:8px 0">'
            '<div style="font-size:14px;font-weight:800;color:#7B241C">账户期望贡献 · 两版并列（★不替换·各标口径）</div>'
            f'{warn}<table style="font-size:12.5px"><tr><th>账户</th><th>按锁定时原判断<br>(Opus5当初真判断)</th><th>按当前价<br>(价格拉出的算术影子)</th><th>差额(判断陈旧度)</th></tr>{rows}</table>'
            '<p style="font-size:11px;color:#888">★★正确结论：组合期望回报＝【我不知道】·五只主力(MSFT/NVDA/TSM/AVGO)锁于07-22~30此后未重估·重估完前距+40%缺口不构成决策依据。</p></div>')


def drift_holdings_html(root, dc):
    """★★★轮327 丙C2/C3:漂移三分类(CROSSED红/NARROWED黄/WIDENED黄)→册2持仓·每只两行(锁定时/现)+理由三件套状态+顶部醒目提示。"""
    import json as _j
    p = root / "data" / "target" / f"target_gap_{dc}.json"
    if not p.exists(): return ""
    d = _j.loads(p.read_text(encoding="utf-8"))
    reg_p = root / "data" / "forecast" / "locked_predictions_registry.json"
    reg = {}
    if reg_p.exists():
        for x in _j.loads(reg_p.read_text(encoding="utf-8")).get("已登记预测", []):
            reg[x.get("ticker")] = x
    COLOR = {"CROSSED": ("#c0392b", "★判断已失效·须重估"), "NARROWED": ("#8a6d00", "空间收窄·方向仍成立"),
             "WIDENED": ("#8a6d00", "空间扩大·须核基本面是否恶化")}
    rows = ""
    for acc in ["富途", "SBI"]:
        for x in d.get(acc, {}).get("逐只(按贡献pp降序)", []):
            lu = x.get("locked_upside_pct"); cu = x.get("upside_pct")
            dt = x.get("drift_type")
            if not dt and lu is not None and cu is not None:   # ★轮327:内联算(drift_type字段可能丢·从upside反算)
                dt = ("CROSSED" if (lu > 0) != (cu > 0) else ("NARROWED" if abs(cu) < abs(lu) else "WIDENED"))
            if not dt: continue
            col, lbl = COLOR.get(dt, ("#333", dt))
            r = reg.get(x.get("code"), {})
            rs = r.get("rationale_status") or ("有" if r.get("rationale") else "永久缺失")
            rows += (f'<tr><td><b>{esc(x.get("code"))}</b> {esc(x.get("name"))}</td>'
                     f'<td>锁定 {esc(x.get("locked_price"))}→E {esc(x.get("fair"))}→<b>{esc(x.get("locked_upside_pct"))}%</b></td>'
                     f'<td>现 {esc(x.get("price_local") or x.get("当日价(E上行分母)"))}→E {esc(x.get("fair"))}→<b>{esc(x.get("upside_pct"))}%</b></td>'
                     f'<td style="color:#c0392b">{esc(x.get("drift_pp"))}pp</td>'
                     f'<td style="color:{col};font-weight:800">{esc(dt)}<br>{lbl}</td>'
                     f'<td style="font-size:11px">{esc(rs)}</td></tr>')
    if not rows: return ""
    notice = ('<div style="background:#7B241C;color:#fff;padding:8px 12px;border-radius:6px;margin:6px 0;font-size:12.5px;font-weight:700">'
              '★本组合全部已锁定预测均无判断理由记录（锁定时未记录·永久缺失）。PDCA 只能验证对错·无法回溯错因。新锁定闸已于 2026-08-09 启用（理由三件套不全→拒绝锁定）。</div>')
    return ('<div style="border:2px solid #7B241C;border-radius:8px;padding:10px 14px;margin:12px 0;background:#fff8f5">'
            '<h2 style="color:#7B241C;border-left:5px solid #7B241C;padding-left:8px">预测漂移三分类 · 逐只（锁定时 vs 现在）</h2>'
            f'{notice}<table style="font-size:12px"><tr><th>标的</th><th>锁定时</th><th>现在</th><th>漂移</th><th>类型</th><th>理由</th></tr>{rows}</table></div>')
