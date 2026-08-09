# -*- coding: utf-8 -*-
"""★轮112 NS1:产品改由【管道 output】消费——layer_pipeline 的 ①~⑦ output 成为产品唯一数据源。
NS1-2 切断产品侧旧并排取数:不再各层分别读 worldview/strategy/macro_flow/sector·⑤不读discovery全市场·⑦不读opus5『今天做什么』+production.action。
NS1-3 旧源只作管道①层原始入口·其余层一律走 pipeline output。
NS2:①层08-03总命中0→②~⑦无输入→★产品产不出任何确定性动作·呈现「输入不完整·今日决策暂停更新」+每层上游空→不产出+provenance。
★NS4:opus5_content 不再是⑦动作来源;各层 process(判断)由Opus5挂对应层·动作只能⑦从⑥推出。"""
import sys, json, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
sys.path.insert(0, str(ROOT / "scripts"))
import product_blocks as pb   # ★轮318 D1:右栏六块底子并入
from layer_pipeline import run as pipeline_run


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def esc(s):
    return str("" if s is None else s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _forward_html(dc):
    """★轮300 前瞻研究区渲染:读 data/forward/forward_{dc}.json·空字段一律显「本项未填·Opus5 未产出」·不留白·不占位。★只渲染结构·内容由Opus5填。"""
    import json as _j
    p = ROOT / "data" / "forward" / f"forward_{dc}.json"
    UNFILLED = '<span style="color:#c0392b">本项未填·Opus5 未产出</span>'
    if not p.exists():
        return ('<h2>前瞻研究区（未来事件／趋势／情景／机会轮动）</h2>'
                f'<p>{UNFILLED}（forward_{dc}.json 不存在）</p>')
    try:
        f = _j.loads(p.read_text(encoding="utf-8"))
    except Exception as _e:
        return f'<h2>前瞻研究区</h2><p>{UNFILLED}（读取失败:{esc(str(_e)[:60])}）</p>'
    # ★轮301:递归可读渲染(★绝不 str(dict)·守D2)。dict→键：值·list→逐条·空→未填。
    def _rv(v):
        if v is None or v == "" or v == [] or v == {}:
            return UNFILLED
        if isinstance(v, dict):
            return "<div style='margin:2px 0 2px 8px'>" + "".join(
                f'<div><b>{esc(k)}</b>：{_rv(x)}</div>' for k, x in v.items()) + "</div>"
        if isinstance(v, list):
            return "<br>".join("・" + _rv(x) for x in v)
        return esc(str(v))
    def _get(o, *names):  # 兼容董事长可能带★前缀的键名
        for n in names:
            if n in o:
                return o[n]
        for k in o:
            for n in names:
                if str(k).lstrip("★ ") == str(n).lstrip("★ "):
                    return o[k]
        return None
    st = f.get("_status", "")
    orr = f.get("opportunity_rotation", {}) or {}
    # ★★★A3:replace_low_efficiency_holdings 单独成块置顶(今日最实质结论:该不该换微软/爱德万)
    repl = _get(orr, "replace_low_efficiency_holdings", "★★★replace_low_efficiency_holdings")
    repl_block = (f'<div style="border:3px solid #7B241C;border-radius:8px;padding:12px 15px;margin:6px 0 14px;background:#fdf0ee">'
                  f'<div style="font-size:16px;font-weight:900;color:#7B241C">🔺 今日最实质结论：低效持仓是否替换（微软／爱德万）</div>'
                  f'<div style="margin-top:6px;font-size:13px">{_rv(repl) if repl not in (None, "", {}) else UNFILLED}</div></div>')
    # 未来事件
    fe = f.get("future_events", {}) or {}
    fe_rows = ""
    for hz, lbl in [("horizon_3d", "3日内"), ("horizon_30d", "30日内"), ("horizon_quarter", "本季度")]:
        lst = fe.get(hz) or []
        body = UNFILLED if not lst else "<br>".join(
            f'・<b>{esc(e.get("date"))}</b> {esc(e.get("type"))}｜{esc(e.get("subject"))}｜影响持仓：{_rv(e.get("affected_holdings"))}｜预期：{esc(e.get("expected_impact"))}' for e in lst)
        fe_rows += f'<tr><td><b>{lbl}</b></td><td>{body}</td></tr>'
    # 趋势(★A3:显失效条件+下一观察点)
    trends = f.get("trends") or []
    tr_rows = UNFILLED if not trends else "".join(
        f'<tr><td><b>{esc(t.get("trend_id"))}</b><br>{esc(t.get("name"))}</td><td>阶段：{esc(t.get("stage"))}</td>'
        f'<td><b>失效条件</b>：{_rv(t.get("invalidation_condition"))}<br><b>下一观察点</b>：{_rv(t.get("next_observation_point"))}</td></tr>' for t in trends)
    tr_html = (UNFILLED if not trends else
               f'<table><tr><th>趋势</th><th>阶段</th><th>失效条件 / 下一观察点（★A3）</th></tr>{tr_rows}</table>')
    # 情景(★A3:各显40%/100%路径)
    SK = ["trigger", "evidence", "probability_or_confidence", "sector_impact", "holding_impact", "impact_on_40pct_path", "impact_on_100pct_path", "action", "invalidation_condition"]
    LBL = {"impact_on_40pct_path": "对+40%路径", "impact_on_100pct_path": "对+100%路径", "trigger": "触发", "evidence": "证据", "probability_or_confidence": "概率/置信", "sector_impact": "板块影响", "holding_impact": "持仓影响", "action": "动作", "invalidation_condition": "失效条件"}
    sc = f.get("scenarios", {}) or {}
    def _scell(o):
        if not o or all(o.get(k) in (None, "", [], {}) for k in SK):
            return UNFILLED
        return "".join(f'<div><b>{esc(LBL.get(k, k))}</b>：{_rv(o.get(k))}</div>' for k in SK if o.get(k) not in (None, "", [], {}))
    sc_rows = "".join(f'<tr><td><b>{lbl}</b></td><td>{_scell(sc.get(k, {}) or {})}</td></tr>' for k, lbl in [("base", "基准"), ("bull", "乐观"), ("bear", "悲观")])
    # 机会轮动(replace已置顶·此处显其余)
    OR = ["strongest_trend_now", "likely_next_rotation", "sectors_in_expectation_forming", "sectors_crowded_or_realized", "watchlist", "why_not_buying_yet", "upgrade_trigger"]
    or_body = "".join(f'<div style="margin:3px 0"><b>{esc(k)}</b>：{_rv(orr.get(k))}</div>' for k in OR if k in orr) or UNFILLED
    cl = f.get("china_lens", {}) or {}
    cl_html = _rv(cl) if cl else UNFILLED
    return (f'<h2>前瞻研究区（未来事件／趋势／情景／机会轮动）</h2>'
            f'<p style="font-size:11px;color:#888">★数据源 forward_{dc}.json·状态：{esc(st)}·空字段=Opus5未产出(如实标·不占位)。位置：七层之后·交易动作之前。</p>'
            f'{repl_block}'
            f'<h3 style="font-size:14px">未来事件（3日／30日／季度）</h3><table><tr><th>时窗</th><th>事件</th></tr>{fe_rows}</table>'
            f'<h3 style="font-size:14px">趋势（4条·带失效条件与下一观察点）</h3>{tr_html}'
            f'<h3 style="font-size:14px">情景（base／bull／bear·各含对+40%/+100%路径）</h3><table><tr><th>情景</th><th>要素</th></tr>{sc_rows}</table>'
            f'<h3 style="font-size:14px">机会轮动</h3>{or_body}'
            f'<h3 style="font-size:14px">中国镜头（china_lens）</h3>{cl_html}')


def _rv_generic(v):
    """★轮309:递归可读渲染Opus富文本·绝不str(dict)·不截断·空→未填。"""
    if v is None or v == "" or v == [] or v == {}:
        return '<span style="color:#c0392b">（本项未填·下游不产出）</span>'
    if isinstance(v, dict):
        return "<div style='margin:2px 0 2px 10px'>" + "".join(
            f'<div style="margin:2px 0"><b>{esc(str(k))}</b>：{_rv_generic(x)}</div>' for k, x in v.items()) + "</div>"
    if isinstance(v, list):
        return "<br>".join("・" + _rv_generic(x) for x in v)
    return esc(str(v))


def _opus_sections(relpath, title, border="#7B241C"):
    """★轮309:渲Opus判断JSON全节·键=内容小节标题(元数据_开头跳过·不当标题)·值递归可读。"""
    import json as _j
    p = ROOT / relpath
    if not p.exists():
        return f'<h2>{esc(title)}</h2><p style="color:#c0392b">（{esc(relpath)} 不存在·本层未填·下游不产出）</p>'
    try:
        d = _j.loads(p.read_text(encoding="utf-8"))
    except Exception as _e:
        return f'<h2>{esc(title)}</h2><p style="color:#c0392b">（读取失败:{esc(str(_e)[:60])}）</p>'
    body = ""
    for k, v in d.items():
        if str(k).startswith("_"):   # 元数据(_说明/_数据源等)不当章节标题
            continue
        body += (f'<div style="border-left:3px solid {border};padding-left:10px;margin:8px 0">'
                 f'<h3 style="margin:4px 0;font-size:14px;color:{border}">{esc(str(k))}</h3>{_rv_generic(v)}</div>')
    return f'<h2 style="color:{border};border-left:5px solid {border};padding-left:8px">{esc(title)}</h2>{body}'


def _degrade_html(dc):
    """★★★轮309 B4/B5:第一页置顶·今日结论降级清单(七类·董事长提供)+临时合规状态声明(GPT V7§19)。"""
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
    comp = ('<div style="margin-top:8px;font-size:12.5px">★临时合规状态声明（GPT V7 裁定第十九节）：'
            '本产品当日合规见 <b>output/compliance/完整产品当日合规报告_2026-08-08_人工版.html</b>·'
            'Release Gate 状态以页头标注为准（轮297 裁定：仅标注不拦停）。</div>')
    return ('<div style="background:#fdecea;border:3px solid #c0392b;border-radius:8px;padding:12px 16px;margin:8px 0 14px">'
            '<div style="font-size:16px;font-weight:900;color:#c0392b">🚩 今日结论降级清单（七类·置顶·不得只放文末）</div>'
            f'<ul style="margin:6px 0 0;padding-left:22px">{lis}</ul>{comp}</div>')


def _deepdive_html(dc):
    """★★★轮310 缺口A:通用扫描 data/valuation/ 深度重估产出·【不写死文件名】。
    *_opus5_judgment_v*_{dc}.json → 持仓层(按标的·取最高版本);peer_*_{dc}.json → 板块层。空→本日无深度重估产出。
    ★董事长明日写微软/别的标的判断·同名规则自动接·无需再改代码。"""
    import glob as _g, re as _re
    vdir = ROOT / "data" / "valuation"
    jfiles = _g.glob(str(vdir / f"*_opus5_judgment_v*_{dc}.json")) + _g.glob(str(vdir / f"*_opus5_judgment_{dc}.json"))
    by_tkr = {}
    for fp in jfiles:
        base = _re.sub(r".*[\\/]", "", fp)
        tkr = _re.sub(r"_opus5_judgment.*", "", base)              # 标的键(如 advantest_6857)
        mv = _re.search(r"_v(\d+)_", base)
        ver = int(mv.group(1)) if mv else 1
        if tkr not in by_tkr or ver > by_tkr[tkr][0]:              # 同标的取最高版本(不 sorted[-1])
            by_tkr[tkr] = (ver, fp)
    pfiles = sorted(_g.glob(str(vdir / f"peer_*_{dc}.json")))
    if not by_tkr and not pfiles:
        return '<h2>深度重估区</h2><p style="color:#888">本日无深度重估产出。</p>'
    out = '<h2 style="color:#7B241C;border-left:5px solid #7B241C;padding-left:8px">深度重估区（持仓层个股 + 板块层同业·★通用扫描·非写死）</h2>'
    for tkr, (ver, fp) in sorted(by_tkr.items()):
        rel = str(Path(fp).relative_to(ROOT)).replace("\\", "/")
        out += ('<div style="border:2px solid #7B241C;border-radius:8px;padding:8px 12px;margin:8px 0;background:#fdf7f5">'
                + _opus_sections(rel, f"持仓层 · {tkr} 重估（v{ver}·最新版）", "#7B241C") + '</div>')
    for fp in pfiles:
        rel = str(Path(fp).relative_to(ROOT)).replace("\\", "/")
        nm = _re.sub(r"\.json$", "", _re.sub(r".*[\\/]peer_", "", fp)).replace("_" + dc, "")
        out += ('<div style="border:2px solid #12324e;border-radius:8px;padding:8px 12px;margin:8px 0;background:#f4f8fc">'
                + _opus_sections(rel, f"板块/公司层 · 同业对照 {nm}（★口径差异注·不作精确比较）", "#12324e") + '</div>')
    return out


def build(date):
    dc = date.replace("-", "")
    date = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:8])   # ★轮118:文件名统一连字符(daily传YYYYMMDD/手工传连字符都归一·不生成两份)
    pipe = pipeline_run(dc)              # ★唯一数据源:管道output(内部只读管道·不旁路)
    layers = pipe["七层"]
    trade = pipe["★最终交易动作"]
    has_action = isinstance(trade, list) and len(trade) > 0
    归因 = pipe.get("★⑦无动作的真实归因(PE3-1·非首空层标签)") or "已产出动作"   # ★轮125 PE3-1:不再用『通到第X层』
    now = datetime.now(JST)

    # 顶部判据:①层(证据映射器)恒非空→列证据+动摇置顶;②~⑦待Opus5加工→不自动出动作(NU3/NU4)
    l1 = layers[0]
    em = _rj(ROOT / "data/market" / f"evidence_map_{dc}.json")
    动摇尺 = em.get("★动摇的尺(PDCA入口·置顶)", [])
    if not has_action:
        # ★动摇证据置顶
        shake = [e for e in em.get("路1_对6尺持续验证(★动摇置顶)", []) if "动摇" in str(e.get("印证动摇"))]
        shake_html = "".join(f'<li>【{esc(e.get("印证动摇"))}·{esc(e.get("对应尺"))}】{esc(e.get("证据"))}（强度{esc(e.get("强度"))}·{esc(e.get("来源"))}·{esc(e.get("as_of"))}）</li>' for e in shake)
        verdict = ('<div style="background:#7B241C;color:#fff;border-radius:10px;padding:14px 18px;margin:10px 0">'
                   f'<div style="font-size:20px;font-weight:900">★ ①层证据已到位（{esc(l1["output数"])}条）· 下游②~⑦待 Opus5 加工 · 今日不自动出确定性动作</div>'
                   '<div style="font-size:12.5px;margin-top:5px">★①层＝每日证据→6尺映射器（恒非空·『无事件』类结论不再出现）；★证据≠动作——动作只能⑦层由 Opus5 从⑥推出，本日 Opus5 未加工当日证据故<b>不自动出价格/股数/分笔/跳空</b>。</div>'
                   f'<div style="background:#3a1e1e;border:2px solid #ff6b6b;border-radius:8px;padding:8px 12px;margin:8px 0"><b style="color:#ffcf70">★被现实动摇的尺（PDCA入口·置顶·尺被挑战才知要不要改尺）：{esc("·".join(动摇尺)) or "无"}</b><ul>{shake_html}</ul></div>'
                   '<div style="font-size:12px;color:#ffd9d0">★参考上一轮判断请查 08-02·<b>那是 08-02 的判断·今日未更新</b>·不可直接执行。</div></div>')
    else:
        rows = "".join(f'<li>{esc(a.get("账户"))}·{esc(a.get("股数"))}股·{esc(a.get("价格"))}·{esc(a.get("条件"))}（{esc(a.get("provenance"))}）</li>' for a in trade)
        verdict = ('<div style="background:#0f2e1c;color:#dff5e6;border-radius:10px;padding:14px 18px;margin:10px 0">'
                   f'<div style="font-size:20px;font-weight:900">★ 今日交易动作（⑦层·从⑥推出·唯一来源）</div><ul>{rows}</ul></div>')

    # 七层管道视图(NS2:每层 input→output→空原因+provenance)
    lrows = ""
    for L in layers:
        st = "产出 %d 条" % L["output数"] if L["output数"] else "★无产出"
        # ★轮125 PE3-2:显示逐层真实状态(已填传下/未填阻断/客观空延续)
        真实状态 = L.get("★真实状态")
        detail = ("<b style='color:#12324e'>真实状态：%s</b><br>" % esc(真实状态)) if 真实状态 else ""
        if L["output"]:
            # ★显示可核机器数值(③指标+数值+判档·④板块+涨跌+方向·NW1-2/NW2-2) + ★③传给④三方向(PE1-3)
            bits = []
            for o in L["output"][:6]:
                if "★数值(机器)" in o:
                    bits.append("%s=<b>%s</b>(%s)" % (esc(o.get("指标")), esc(o.get("★数值(机器)")), esc(o.get("判档(机器)"))))
                elif o.get("id") == "J3":   # ③判断(解释框架)
                    bits.append("★③判断：<b>%s</b>｜传给④方向：%s" % (esc(str(o.get("本层判断"))[:28]), esc(str(o.get("★传给④层的输出(三方向)"))[:60])))
                elif "★当日涨跌pct(机器观测)" in o:
                    bits.append("%s <b>%+.2f%%</b>→%s ×③[%s]" % (esc(o.get("板块")), o.get("★当日涨跌pct(机器观测)"), esc(o.get("方向(机器初判枚举)")), esc(str(o.get("★③传下的方向(解释框架)"))[:18])))
                elif "证据" in o:
                    bits.append(esc(str(o.get("证据"))[:34]))
                else:
                    bits.append(esc(str(o.get("候选") or o.get("换或不换") or o.get("延续说明") or o.get("provenance", ""))[:30]))
            detail += "<br>".join(bits)
        # ★丁5(轮332):空层醒目占位——因Opus5判断工单未填而空的层·大字红条一眼可见"缺此层"(不藏灰字)。
        _empty_reason = str(L.get("空原因") or "")
        _state = str(真实状态 or "")
        _need_opus = any(k in (_empty_reason + _state) for k in ("待Opus5", "待 Opus5", "未填", "该填没填", "阻断", "待判断"))
        _banner = ('<div style="border:2px solid #c0392b;background:#fdecea;border-radius:6px;padding:6px 10px;margin:3px 0;'
                   'font-size:13px;font-weight:800;color:#c0392b">★本层今日无判断（等 Opus 5 填写）——产品不完整，缺此层。</div>') if (_empty_reason and _need_opus) else ""
        _cell = (_banner + "<b style='color:#c0392b'>" + st + "</b>·" + esc(L["空原因"])) if L["空原因"] else ("<b>" + st + "</b><br>" + detail)
        lrows += (f'<tr><td><b>{esc(L["层"])}</b></td><td>{esc(L["input来源"])}</td>'
                  f'<td style="font-size:11px">{esc(L["process"])}</td>'
                  f'<td>{_cell}</td></tr>')

    # ★轮116 NW1-4:②~⑥层判断(工单·Opus5填/待判断) + ★第一三共复核(NW2·原判断与修正并列·不覆盖)
    js = _rj(ROOT / "data/pipeline" / f"judgment_slots_{dc}.json")
    jrows = ""
    for k, s in (js.get("②~⑦层工单", {}) or {}).items():
        slot = s.get("槽位", {}) or {}
        j = slot.get("本层判断")
        ref = slot.get("★引用证据ID(NV2-4·必填·不许凭空)") or []
        # ★★★轮297 D2/B4(董事长令):渲染层绝不许把内部数据结构 str() 当正文。
        #   空模板 dict {'①事实':None,...} 是 truthy → 旧 `if j` 走 str() 分支把 dict 印进正文(产品级事故)。
        #   规矩:本层判断=字符串才是正文;dict=内部结构·值全空→「本层未填·下游不产出」;dict部分填→按子字段可读拼接(不 str(dict))。
        _txt = None
        if isinstance(j, str):
            _txt = j.strip() or None
        elif isinstance(j, dict):
            _parts = [f"{esc(str(_k))}：{esc(str(_v).strip())}" for _k, _v in j.items()
                      if _v is not None and str(_v).strip() != ""]
            _txt = "；".join(_parts) if _parts else None   # 全空模板→None→判未填(绝不 str(dict))
        elif j not in (None, "", [], {}):
            _txt = esc(str(j).strip())
        # ★轮297 C2/D3(董事长令):判断正文【不许截断】——去掉旧 [:120] 定长截断(断在半句如「未破20%上限但逼」)。
        cell = (f'<b style="color:#2a7a4a">{esc(_txt) if isinstance(j, str) else _txt}</b>（引用证据 {esc(ref)}）' if _txt
                else '<span style="color:#c0392b">★本层未填·下游不产出（Opus5 未填·NW1-2/D2）</span>')
        jrows += f'<tr><td><b>{esc(k)}</b></td><td>收到证据 {len(s.get("收到证据ID",[]))} 条</td><td>{cell}</td></tr>'
    judg_html = (f'<h2>②~⑥ 层判断（Opus5 按层填工单·provenance 追溯证据ID）</h2>'
                 f'<table><tr><th>层</th><th>收到证据</th><th>本层判断 / 状态</th></tr>{jrows}</table>')
    # ★第一三共复核(NW2)
    rc = ((js.get("②~⑦层工单", {}) or {}).get("⑥持仓比较", {}) or {}).get("★须复核既有判断(NV3)", [])
    for r in rc:
        cs = r.get("★复核槽位(Opus5填)", {}) or {}
        concl = cs.get("维持原判/修正/撤回")
        if concl:
            judg_html += (
                '<h2 style="color:#c0392b">★ 第一三共（JP.4568）复核 — 原判断与复核结论并列·不覆盖（NW2）</h2>'
                '<table><tr><th>项</th><th>内容</th></tr>'
                f'<tr><td>★原判断（保留·未覆盖·NW2-1）</td><td>{esc(r.get("★原判断(保留台账·不覆盖·NV3-3)"))}</td></tr>'
                f'<tr><td>★复核结论</td><td><b style="color:#c0392b">{esc(concl)}</b></td></tr>'
                f'<tr><td>理由</td><td>{esc(cs.get("理由"))}</td></tr>'
                f'<tr><td>★时点判断（NW2-2）</td><td><b style="color:#c0392b">「周一开盘立即卖出」时点已撤回·Opus5 明确无时点依据（价格/均线/量能未算）·时点须⑦层从⑥推·本轮不给新时点</b></td></tr>'
                f'<tr><td>★新证伪信号（NW2-3·看财务披露不看股价）</td><td>{esc(cs.get("新证伪信号"))}</td></tr>'
                f'<tr><td>引用证据ID</td><td>{esc(cs.get("★引用证据ID"))}</td></tr>'
                f'<tr><td>★错因（供PDCA记分）</td><td>{esc(r.get("★复核槽位(Opus5填)", {}).get("★原判断错在哪(供PDCA记分)") or "时机错:把有依据的方向与无依据的时点捆成一个动作")}</td></tr>'
                '</table>')

    # ★★★轮297 B3(董事长令):星期几不许写死。此前 banner 硬编码「周一·交易日」→ 08-07(周五)/08-08(周六)全印周一交易日。
    #   动态算真实星期几+休市判定;周末价格＝最近交易日收盘(不许标「盘中价」·2.6铁律)。
    _d = datetime.strptime(dc, "%Y%m%d")
    _wd = _d.weekday()                       # 0=周一 … 5=周六 6=周日
    _wd_cn = "周一 周二 周三 周四 周五 周六 周日".split()[_wd]
    _is_weekend = _wd >= 5
    _mkt = "休市" if _is_weekend else "交易日"
    _px_d = _d - timedelta(days=(_wd - 4)) if _is_weekend else _d   # 周末回退到最近周五
    _px_date = _px_d.strftime("%Y-%m-%d")
    # ★★★时间感知:该交易日美股收盘=交易日+1 的 05:00 JST。现在<该时刻→美股仍盘中,不许假称收盘(2.6铁律)。
    _us_close = (_px_d + timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
    _us_closed = now.replace(tzinfo=None) >= _us_close if _is_weekend else True
    if _is_weekend and not _us_closed:
        _px_note = (f"日股＝{_px_date} 收盘 ·【★美股 {_px_date} 未收盘·收盘 05:00 JST·当前美股价＝盘中价·非完整收盘·完整版待收盘后重跑】")
    elif _is_weekend:
        _px_note = f"价格＝{_px_date} 收盘（日股东证收盘／美股 {_px_date} 收盘）"
    else:
        _px_note = f"价格对应交易日 {date}（依③z闸须已收盘·非盘中）"
    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>每日产品·管道版·{date}</title>
<style>body{{font-family:"Microsoft YaHei",sans-serif;max-width:1080px;margin:0 auto;padding:14px;color:#1a1a1a;line-height:1.7;background:#f5f6f8}}
.banner{{background:#12324e;color:#fff;border-radius:10px;padding:12px 16px}}
table{{border-collapse:collapse;width:100%;margin:8px 0}} th,td{{border:1px solid #bbb;padding:6px 9px;font-size:12.5px;text-align:left;vertical-align:top}} th{{background:#eef3f8}}
h2{{color:#12324e;border-left:5px solid #2c6e9a;padding-left:8px}}</style></head><body>
<div class="banner"><div style="font-size:20px;font-weight:800">★ 每日投资产品 · 管道版（七层真管道·产品唯一数据源） · 数据日 {date}（{_wd_cn}·{_mkt}）</div>
<div style="font-size:13px;margin-top:4px;font-weight:700;color:#ffe08a">📅 {_px_note}{'　★周六休市·无盘中价' if _is_weekend else ''}</div>
<div style="font-size:12px;margin-top:4px">★数据源＝layer_pipeline ①~⑦ output（唯一）·已切断产品侧旧并排取数（各层直读worldview/strategy/macro_flow/sector、⑤读discovery全市场、⑦读opus5+production 一律不再直连）·旧源仅作管道①层原始入口。生成 {now.strftime('%Y-%m-%d %H:%M JST')}</div></div>
<div style="background:#fff3cd;border:2px solid #d9a400;border-radius:6px;padding:8px 12px;margin:6px 0;font-size:13px;font-weight:700;color:#8a6d00">★本册为【七层管道版】。五册版（册1总览/册2持仓/册3机会板块…）见 <b>★每日产品_{date}.html</b>（册1）</div>
{pb.ledger_html(ROOT, dc)}
{pb.contribution_two_way_html(ROOT, dc)}
{_degrade_html(dc)}
{verdict}
{judg_html}
<h2>七层管道（input→process→output·上游空则结构性阻断·NS2）</h2>
<table><tr><th>层</th><th>input（唯一来源）</th><th>process</th><th>output / 空原因·provenance</th></tr>{lrows}</table>
<div style="border:2px solid #6a4c93;border-radius:8px;padding:10px 14px;margin:12px 0;background:#faf7ff">{pb.fill_sector_tokens(ROOT, dc, _forward_html(dc))}</div>
{_deepdive_html(dc)}
<div style="border:2px solid #12324e;border-radius:8px;padding:10px 14px;margin:12px 0;background:#f4f8fc">{pb.sector_split_html(ROOT, dc)}</div>
<div style="border:2px solid #12324e;border-radius:8px;padding:10px 14px;margin:14px 0;background:#fbfcfe">{pb.right_column_html(ROOT, dc)}</div>
<p style="font-size:12px;color:#666">★NS4：opus5_content 不再是⑦层动作来源；各层 process 的判断内容由 Opus5 提供并挂对应层·★动作只能是⑦层从⑥推出——Opus5 不得越级直接给动作。</p>
</body></html>"""
    op = ROOT / "00_请先看这里" / f"★每日产品_管道版_{date}.html"
    op.write_text(html, encoding="utf-8")
    b = html.encode("utf-8")
    print("[管道版产品] 写出 %s · %dKB · 乱码%d · 有交易动作=%s · ⑦归因=%s" % (
        op.name, len(b) / 1024, b.count(b"\xef\xbf\xbd"), has_action, 归因))
    return 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    return build(a.date)


if __name__ == "__main__":
    raise SystemExit(main())
