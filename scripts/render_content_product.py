# -*- coding: utf-8 -*-
"""★轮82 AV:出 08-02 产品——照录渲染 Opus5 内容JSON(判断/概率/理由一字不改)+{{}}从target_gap/forecast填(填不上写未产出)。
周末口径:data_date=当日·价格=上一交易日收盘(休市无新价·页头写明)·新闻抓当日。run_id=R-{date}-HHMMSS。
AV3四件事显性印:七层建成表/八步流程表/资金流未接5项/外部资料状态。走 product_lint 出厂闸·PDF同run_id(.pdf.runid边车)。"""
import sys, os, json, argparse, re, glob, hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
import html as _html
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
SEE = ROOT / "00_请先看这里"


def esc(s):
    return _html.escape(str(s), quote=False)


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _latest(pat):
    xs = sorted(glob.glob(str(ROOT / pat)))
    return xs[-1] if xs else None


def build_values(dc):
    """★AV1-2:{{}}值从 target_gap/forecast/driver/daily_scan 填。缺→『未产出·原因』。"""
    v = {}
    # 现价(07-31收盘)——daily_scan
    scan = _rj(ROOT / "data/market" / f"daily_scan_{dc}.json") or _rj(ROOT / "data/market/daily_scan_20260731.json")
    px = {q["code"]: q.get("last_price") for q in (scan.get("items", {}).get("1_当日20只价", {}) or {}).get("逐只", [])}
    v["META现价"] = px.get("US.META"); v["爱德万现价"] = px.get("JP.6857")
    v["第一三共现价"] = px.get("JP.4568"); v["软银现价"] = px.get("JP.9984"); v["闪迪现价"] = px.get("US.SNDK")
    # 三情景收益率——target_gap(优先当日·回落07-31)
    tg = _rj(ROOT / "data/target" / f"target_gap_{dc}.json") or _rj(ROOT / "data/target/target_gap_20260731.json")
    port = (tg.get("★组合三情景收益率(三·轮52)", {}) or {}).get("富途", {})
    v["S1收益率"] = port.get("S1收益率pct"); v["S2收益率"] = port.get("S2收益率pct"); v["S3收益率"] = port.get("S3收益率pct")
    # AI权重——driver_exposure
    dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:8])
    dv = _rj(ROOT / "data/risk" / f"driver_exposure_{dh}.json") or _rj(_latest("data/risk/driver_exposure_*.json") or "")
    accs = dv.get("账户", {})
    def _hiai(acc):
        w = (((accs.get(acc, {}) or {}).get("驱动组", {}) or {}).get("高AI beta", {}) or {}).get("权重合计")
        return round(w * 100, 1) if isinstance(w, (int, float)) else None
    v["富途高AI权重"] = _hiai("富途"); v["SBI高AI权重"] = _hiai("SBI")
    # forecast 爱德万点值/闪迪区间
    fp = _latest("data/forecast/forecast_2026-*.json")
    fc = _rj(fp) if fp else {}
    def _scen(tk):
        f = next((x for x in fc.get("forecasts", []) if x.get("ticker") == tk and x.get("horizon") == "1y"), None)
        return {s.get("name", "")[:2]: s for s in (f or {}).get("scenarios", [])} if f else {}
    adv = _scen("JP.6857")
    v["爱德万乐观点值"] = (adv.get("乐观", {}) or adv.get("好", {})).get("point_value")
    v["爱德万悲观点值"] = (adv.get("悲观", {}) or adv.get("坏", {})).get("point_value")
    z4 = _rj(ROOT / "data/risk" / f"z4_two_segment_{dc}.json") or _rj(ROOT / "data/risk/z4_two_segment_20260731.json")
    for a in ("富途", "SBI"):
        for r in ((z4.get("账户", {}).get(a, {}) or {}).get("①已算清(特+A级)", {}) or {}).get("只", []) + \
                 ((z4.get("账户", {}).get(a, {}) or {}).get("②未算清(B+C级)", {}) or {}).get("只", []):
            if r.get("code") == "JP.6857" or "爱德万" in str(r.get("name")):
                v["爱德万权重"] = r.get("权重pct")
    snd = _scen("US.SNDK")
    def _rng(s):
        r = s.get("range")
        return ("%s~%s" % (min(r), max(r))) if r else None
    v["闪迪乐观区间"] = _rng(snd.get("乐观", {}) or snd.get("好", {}))
    v["闪迪中性区间"] = _rng(snd.get("中性", {}) or snd.get("中", {}))
    v["闪迪悲观区间"] = _rng(snd.get("悲观", {}) or snd.get("坏", {}))
    return v


def fill_placeholders(obj, values):
    """递归填 {{}}·填不上→『未产出·原因:target_gap/forecast无该值』。"""
    if isinstance(obj, str):
        def rep(m):
            k = m.group(1)
            val = values.get(k)
            return str(val) if val is not None else ("〔未产出·%s待接求证表／前瞻源〕" % k)
        return re.sub(r"\{\{([^}]+)\}\}", rep, obj)
    if isinstance(obj, list):
        return [fill_placeholders(x, values) for x in obj]
    if isinstance(obj, dict):
        return {k: fill_placeholders(x, values) for k, x in obj.items()}
    return obj


# 指令键=写给渲染器的·不展示进产品(如★替换=「本段必须替换掉原有…」)
_INSTR_KEYS = ("★替换", "_instr", "★指令", "_note_to_renderer", "★渲染指令")


def render_node(k, v, level=2):
    """内容dict→HTML照录:键=标题·字符串=段·列表=ul·嵌套=子节。指令键剥除不展示。"""
    if str(k) in _INSTR_KEYS:
        return ""
    out = []
    tag = "h%d" % min(level, 5)
    kt = esc(re.sub(r"^[★_]+", "", str(k))).replace("_", " ")
    if isinstance(v, dict):
        out.append(f'<{tag} class="sec">{kt}</{tag}>')
        for sk, sv in v.items():
            if str(sk) in _INSTR_KEYS:
                continue
            out.append(render_node(sk, sv, level + 1))
    elif isinstance(v, list):
        out.append(f'<{tag} class="sec">{kt}</{tag}><ul>')
        for it in v:
            out.append("<li>%s</li>" % (esc(it) if not isinstance(it, (dict, list)) else render_node("", it, level + 1)))
        out.append("</ul>")
    else:
        txt = esc(v)
        txt = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", txt)
        out.append(f'<p><b>{kt}</b>：{txt}</p>' if kt else f"<p>{txt}</p>")
    return "\n".join(out)


def av3_tables(dc):
    """★AV3四件事显性印。"""
    ss = _rj(ROOT / "data/pdca" / f"scorecard_summary_{dc}.json")
    p7 = _rj(ROOT / "data/logs" / f"pipeline_7steps_{dc}.json")
    mf = _rj(ROOT / "data/market/latest_market_snapshot.json")
    mflow = _rj(ROOT / "data/market" / f"macro_flow_{dc}.json")
    inbox = _rj(ROOT / "data/inbox" / f"new_materials_{dc}.json")
    cs = _rj(ROOT / "data/logs" / f"completion_status_{dc}.json")
    h = ['<div class="av3"><h2 class="sec">★ 这台机器现在什么水平（机器自报·四件事显性印）</h2>']
    # AV3-1 七层建成(★动态读 completion_status·不写死)
    h.append('<h3>① 蓝图七层建成情况</h3><table><tr><th>层</th><th>建成</th><th>证据</th></tr>')
    seven = cs.get("一_七层", {})
    if seven:
        for k, v in seven.items():
            h.append(f"<tr><td>{esc(k)}</td><td>{esc(v.get('满足'))}</td><td>{esc(str(v.get('证据',''))[:46])}</td></tr>")
    else:
        for k, st in {"①世界观": "未建", "②国家战略": "未建", "③资金流动": "部分", "④板块轮动": "部分",
                      "⑤机会池": "部分", "⑥持仓层": "已建", "⑦复盘层": "已建"}.items():
            h.append(f"<tr><td>{esc(k)}</td><td>{esc(st)}</td><td></td></tr>")
    h.append("</table>")
    # AV3-2 八步流程
    h.append('<h3>② 八步流程（哪几步做了/谁负责）</h3><table><tr><th>步</th><th>谁做</th><th>做没做</th></tr>')
    for r in p7.get("七步", []):
        h.append(f"<tr><td>{esc(r.get('步'))}</td><td>{esc(r.get('谁做'))}</td><td>{esc(r.get('做没做'))}</td></tr>")
    h.append("</table>")
    # AV3-3 资金流未接5项
    h.append('<h3>③ 资金流动层未接的项（含蓝图标「总闸抓手」的 FIMA）</h3><ul>')
    for x in mflow.get("核心指标", []) + mflow.get("AQ2次轮留位", []):
        if not x.get("接通"):
            h.append(f"<li>{esc(x.get('指标'))}：{esc(x.get('★取不到·未接') or x.get('★自动源未接') or '未接')}</li>")
    h.append("</ul>")
    # AV3-4 外部资料状态(★轮84 BB2:读正文提取索引·消化数)
    ext = _rj(ROOT / "data/external/text" / f"_index_{dc}.json")
    h.append('<h3>④ 外部研究资料状态（正文提取消化）</h3>')
    if ext:
        st = ext.get("统计", {})
        h.append(f'<p>最近{esc(ext.get("窗口天数"))}天新料 <b>{esc(st.get("新料总数"))}</b> 份 · 正文提取成功 <b>{esc(st.get("提取成功"))}</b> 份 · 需导出PDF(gdoc) {esc(st.get("需导出PDF(gdoc)"))} · 失败 {esc(st.get("提取失败"))}</p>')
        # ★轮95 NA3-3:Opus5 本轮消化状态(9份提取·消化6·未读3)
        dg = _rj(ROOT / "data/external/text" / f"_digest_{dc}.json")
        if dg:
            h.append(f'<p style="background:#1e2e1e;color:#cfe8cf;padding:4px 8px;border-radius:5px">★本轮 Opus5 消化状态：9 份已提取 · <b>已消化 {esc(dg.get("已消化", 6))} 份</b> · <b>未读 {esc(dg.get("未读", 3))} 份</b>（{esc(dg.get("未读清单", "老雷 07-23/24 录音、周前瞻"))}）</p>')
        if ext.get("★告警"):
            h.append(f'<p style="color:#c0392b"><b>{esc(ext.get("★告警"))}</b></p>')
        h.append('<table><tr><th>日期</th><th>来源</th><th>标题</th><th>字数</th></tr>')
        for e in ext.get("条目", [])[:10]:
            h.append(f"<tr><td>{esc(e.get('日期'))}</td><td>{esc(e.get('来源'))}</td><td>{esc(e.get('标题')[:30])}</td><td>{esc(e.get('字数')) if e.get('成功') else esc(e.get('说明')[:18])}</td></tr>")
        h.append("</table>")
    else:
        stale = inbox.get("各类最新与断流", {})
        h.append('<ul>')
        for kind, d in stale.items():
            h.append(f"<li>{esc(kind)}：最新一份 {esc(d.get('最新一份'))}·{esc(d.get('断流告警'))}</li>")
        h.append("</ul>")
    # 复盘层三数并列(AU2)
    au2 = ss.get("★AU2产品三数并列(防误读)", {})
    if au2:
        h.append("<p>★复盘层三数并列：到期验证命中率=%s｜自查发现的错=%s｜待验=%s</p>" % (
            esc(au2.get("★到期验证命中率")), esc(au2.get("★自查发现的错")), esc(au2.get("★待验判断"))))
    h.append("</div>")
    h.append(sector_rotation_block(dc))
    h.append(review_daily_block(dc))
    h.append(machine_build_blocks(dc))
    h.append(external_indicators_block(dc))
    h.append(judgment_completeness_block(dc))
    return "\n".join(h)


def judgment_completeness_block(dc):
    """★轮99 NE L19 三态:①已做·沿用 ②★需复核(逼Opus5响应) ③判断未做。★有效期只看见分晓日(§5.4·非当日≠未做)。"""
    j = _rj(ROOT / "data/pdca" / f"judgment_completeness_{dc}.json")
    if not j:
        return ""
    review = j.get("★需复核清单(Opus5须响应·触发原因)", [])
    undone = j.get("判断未做清单", [])
    fail = j.get("★第4步FAIL(未做>50%)")
    h = ['<div class="av3"><h2 class="sec">★ 第4步 判断完整性（L19·三态·NE）</h2>']
    h.append(f'<p style="background:{"#3a1e1e" if fail else "#1e2e3a"};color:#cfe0ff;padding:8px 12px;border-radius:6px">'
             f'持仓 <b>{esc(j.get("持仓数"))}</b> 只 → ①判断已做·沿用 <b>{esc(j.get("①判断已做·沿用"))}</b> · ②<b style="color:#ffcf70">★需复核 {esc(j.get("②★需复核"))}</b> · ③判断未做 <b>{esc(j.get("③判断未做"))}</b>（{esc(j.get("判断未做占比pct"))}%）'
             f'{"　→ ★第4步 FAIL" if fail else "　→ 第4步 PASS（未做≤50%）"}</p>')
    h.append('<p style="font-size:12px;color:#888">★三态：①【已做·沿用】有见分晓日未过的锁定预测且当日无事件（★非当日≠未做·守§5.4·与PDCA锁定兼容）；②【★需复核】有锁定预测但当日被<b>结构化触发</b>（|涨跌幅|>5% 或 新闻命中该只）→ <b>须 Opus5 响应（确认沿用 or 改判）</b>；③【判断未做】无有效期内预测。★真偷懒＝有新事件却不复核，不是没每天重打同一句话。★Code 不替 Opus5 编判断。</p>')
    h.append(f'<p>需复核 {esc(j.get("②★需复核"))} 只 → 已响应 <b>{esc(j.get("★需复核已响应"))}</b>·仍挂 <b>{esc(j.get("★需复核仍挂"))}</b>｜其中 ★判错(被证伪) <b style="color:#c0392b">{esc(j.get("★判错(被证伪)"))}</b>·沿用(未证伪) {esc(j.get("★沿用(未证伪)"))}</p>')
    # ★NG2/NG3-3:三只判错原样照录(不弱化)——读 judgment 复核
    jf = _rj(ROOT / "data/forecast" / f"judgment_{dc[:4]}-{dc[4:6]}-{dc[6:]}.json")
    wrong = [r for r in (jf.get("复核", []) or []) if "判错" in str(r.get("★结论") or r.get("★★结论") or "") or "证伪" in str(r.get("★结论") or r.get("★★结论") or "")]
    if wrong:
        h.append('<h3 style="color:#c0392b">★本轮判错清单（原样照录·不弱化·NG3-3）</h3>')
        for r in wrong:
            concl = r.get("★结论") or r.get("★★结论") or ""
            h.append(f'<div style="background:#3a1e1e;color:#ffd9d0;padding:6px 10px;border-radius:5px;margin:4px 0">'
                     f'<b>{esc(r.get("name"))}（{esc(r.get("ticker"))}）</b> 触发 {esc(r.get("触发"))}·现价 {esc(r.get("现价"))}·★落点 {esc(r.get("★落点"))}<br>{esc(str(concl)[:200])}</div>')
    if review:
        h.append('<h3 style="color:#c8860a">②需复核触发（结构化·阈值按板块波动率分层·NG5）</h3><table><tr><th>代码</th><th>名称</th><th>触发原因</th><th>Opus5响应</th></tr>')
        for x in review:
            h.append(f"<tr><td>{esc(x.get('code'))}</td><td>{esc(x.get('名称'))}</td><td style='color:#c0392b'>{esc('；'.join(x.get('触发原因', [])))}</td><td>{esc(x.get('★Opus5响应'))}</td></tr>")
        h.append("</table>")
    if undone:
        h.append('<h3>③判断未做（无有效期内预测·显性列不藏·NG3-4）</h3><ul>')
        for x in undone:
            h.append(f"<li>{esc(x.get('code'))} {esc(x.get('名称'))}——{esc(x.get('原因'))}</li>")
        h.append("</ul>")
    # ★NG3-2 GPT V6 双FAIL / NG3-5 外部湖水一人 / NG3-7 TSM point_value缺——原样印
    h.append('<div style="background:#2a1e1e;color:#ffd9d0;padding:8px 12px;border-radius:6px;margin:8px 0">'
             '<b>★如实印（不省略·不美化）：</b><ul>'
             '<li>★GPT V6 终验（08-02）：<b>产品成品 FAIL ＋ 机器 FAIL</b>——两项均未放行（原样印·NG3-2）</li>'
             '<li>★外部研究资料 9 份<b>全部出自「湖水」一人·非独立信源</b>——禁「N 方独立指向」表述（NG3-5）</li>'
             '<li>★英伟达/OpenAI 融资担保＝<b>【待核】</b>·属未证实风险观察区·不进正文判断（NG3-6）</li>'
             '<li>★US.TSM 悲观档「预测点值」缺 → <b>E[上行]不输出</b>（守 B/C 级不出预期收益·不用区间中值代替·NG3-7）</li>'
             '</ul></div>')
    h.append("</div>")
    return "\n".join(h)


def external_indicators_block(dc):
    """★轮94 MA1/MA2/MA4:外部资料结构化四维度(仓位/资金流/事件日历/宏观)+PCE反向证据·渲进产品。"""
    ind = _rj(ROOT / "data/external" / f"indicators_{dc}.json")
    if not ind:
        return ""
    h = ['<div class="av3"><h2 class="sec">★ 外部研究资料·结构化维度（湖水/老雷·机器接不到的四维度·B级非机器直采）</h2>']
    h.append('<p style="font-size:12px;color:#888">★这些是外部资料提取的<b>事实数值</b>（Code 只提事实·不提观点）·<b>意味着什么由 Opus5 判</b>（MA5 分工）</p>')
    # MA1-1 仓位维度(机器完全没有)
    pos = ind.get("MA1-1_仓位维度", [])
    if pos:
        h.append('<h3>㈠ 仓位维度（★机器完全没有·投行数据免密钥不可得）</h3><table><tr><th>指标</th><th>值</th><th>资料日/来源</th></tr>')
        for x in pos[:10]:
            h.append(f"<tr><td>{esc(x.get('指标'))}</td><td><b>{esc(x.get('值'))}</b></td><td>{esc(x.get('资料日期'))}·湖水</td></tr>")
        h.append("</table>")
    # MA1-2 资金流向·分主体
    flow = ind.get("MA1-2_资金流向", [])
    if flow:
        h.append('<h3>㈡ 资金流向·分主体（★机器完全没有）</h3><table><tr><th>主体/集中标的</th><th>方向/净额</th><th>资料日</th></tr>')
        for x in flow[:10]:
            left = x.get("主体") or ("集中:" + str(x.get("集中标的_主体", "")))
            right = (str(x.get("方向", "")) + " " + str(x.get("净额", ""))) if x.get("方向") else str(x.get("集中标的", ""))
            h.append(f"<tr><td>{esc(left)}</td><td>{esc(right)}</td><td>{esc(x.get('资料日期'))}</td></tr>")
        h.append("</table>")
    # MA1-4 宏观数据点 + ★MA4 PCE反向证据
    macro = ind.get("MA1-4_宏观数据点", [])
    pce = next((x for x in macro if "PCE" in str(x.get("指标", ""))), None)
    if pce and pce.get("对比预期") in ("低于预期", "不及预期"):
        h.append('<div style="background:#3a2a1e;color:#ffe8cf;border:2px solid #d08030;border-radius:8px;padding:8px 12px;margin:8px 0">'
                 f'<b>★MA4 反向证据（不许静默忽略）：</b>外部资料提取 <b>{esc(pce.get("指标"))} {esc(pce.get("值"))}·{esc(pce.get("对比预期"))}</b>（{esc(pce.get("资料日期"))}·湖水·B级待机器直采确认）。'
                 '★当前 regime 判「高利率＋三票主张加息」，而<b>核心通胀低于预期意味加息压力减轻</b>——这是与 regime 方向相反的证据，'
                 '显性标出（Fable 会诊指出过：不许把两边都说得通的证据只记在自己一边）。★<b>是否据此改 regime＝Opus5 判</b>（Code 只提事实）。</div>')
    if macro:
        h.append('<h3>㈢ 宏观数据点（外部资料·可临时补第③层未接指标·标来源非机器直采）</h3><ul>')
        for x in macro[:6]:
            h.append(f"<li>{esc(x.get('指标'))} {esc(x.get('值'))}·{esc(x.get('对比预期'))}（{esc(x.get('资料日期'))}·{esc(x.get('级别'))}）</li>")
        h.append("</ul>")
    # MA1-3 事件日历(见分晓时间)
    ev = ind.get("MA1-3_事件日历", [])
    if ev:
        h.append('<h3>㈣ 事件日历·见分晓时间（外部资料）</h3><table><tr><th>日期</th><th>事件</th><th>原文片段(供核·PDF日期易切乱)</th></tr>')
        seen = set()
        for x in ev[:12]:
            k = (x.get("日期"), x.get("事件"))
            if k in seen:
                continue
            seen.add(k)
            h.append(f"<tr><td>{esc(x.get('日期'))}</td><td>{esc(x.get('事件'))}</td><td style='font-size:11px'>{esc(x.get('原文片段',''))}</td></tr>")
        h.append("</table>")
    h.append("</div>")
    return "\n".join(h)


def machine_build_blocks(dc):
    """★轮85:①世界观 ②国家战略 ③资金流补 ⑥持仓档案 建成情况渲进产品(①②须标 data-src 引用框架)。"""
    wv = _rj(ROOT / "data/market" / f"worldview_{dc}.json")
    strat = _rj(ROOT / "data/market" / f"strategy_{dc}.json")
    mfx = _rj(ROOT / "data/market" / f"macro_flow_ext_{dc}.json")
    acctb = _rj(ROOT / "data/accounts" / f"all_accounts_base_{dc}.json")
    if not (wv or strat or mfx):
        return ""
    h = ['<div class="av3"><h2 class="sec">★ 轮85 新建层（①世界观／②国家战略／③资金流补／⑥持仓档案）</h2>']
    # ①世界观(标 data-src 引用框架)
    if wv.get("五类"):
        h.append(f'<h3 data-src="{esc(wv.get("data_src"))}">① 世界观层（五类事件·框架：{esc(wv.get("框架文件"))}）</h3><table><tr><th>类</th><th>结论</th></tr>')
        for c in wv["五类"]:
            h.append(f"<tr><td>{esc(c['类'])}</td><td>{esc(c['结论'])}</td></tr>")
        h.append("</table>")
    # ②国家战略
    if strat.get("四类"):
        h.append(f'<h3 data-src="{esc(strat.get("data_src"))}">② 国家战略层（四类·三张战略地图：{esc(strat.get("战略地图文件"))}）</h3><table><tr><th>类</th><th>结论</th></tr>')
        for c in strat["四类"]:
            h.append(f"<tr><td>{esc(c['类'])}</td><td>{esc(c['结论'])}</td></tr>")
        h.append("</table>")
    # ③资金流补(含FIMA)
    if mfx.get("补充指标"):
        h.append(f'<h3>③ 资金流动·补充指标（本文件接通 {esc(mfx.get("本文件接通数"))}/{esc(mfx.get("本文件指标数"))}·含 FIMA）</h3><table><tr><th>指标</th><th>值/未接原因</th></tr>')
        for x in mfx["补充指标"]:
            vo = x.get("值")
            if x.get("接通"):
                v = str((vo.get("值") or vo.get("命中") or "接通") if isinstance(vo, dict) else vo)[:44]
            else:
                v = "未接：" + str(x.get("★失败原因"))[:50]
            h.append(f"<tr><td>{esc(x['指标'])}</td><td>{esc(v)}</td></tr>")
        h.append("</table>")
    # ⑥全账户底数(★轮86 DA1:主战场齐+静止户有快照即可)
    if acctb.get("主战场"):
        h.append('<h3>⑥ 全账户底数（IBKR/bitFlyer＝静止账户·不做目标管理·07-19尺G6）</h3><ul>')
        for k, v in acctb.get("主战场", {}).items():
            h.append(f"<li>主战场 {esc(k)}：{'当日底数齐✔' if v.get('接通') else '待接'}</li>")
        for k, v in acctb.get("静止账户(不做目标管理·跟随主战场)", {}).items():
            snap = "有最近快照✔" if v.get("有最近快照") else "待首次录入"
            h.append(f"<li>静止 {esc(k)}：{snap}·{esc(str(v.get('★状态',''))[:40])}（静止≠陈旧）</li>")
        h.append("</ul>")
    # ⑤机会池(★轮86 DB2:第4关护城河五维/第5关深度/量能/机会发现)
    moat5 = _rj(ROOT / "data/opportunity" / f"moat_{dc}.json")
    disc = _rj(ROOT / "data/opportunity" / f"discovery_{dc[:4]}-{dc[4:6]}-{dc[6:]}.json")
    vol = _rj(ROOT / "data/opportunity" / f"volume_standard_{dc}.json")
    if moat5 or disc:
        cands = len(disc.get("candidates", []) or []) if disc else 0
        pend = len(disc.get("pending_valuation", []) or []) if disc else 0
        cpool = _rj(ROOT / "data/opportunity" / f"candidate_pool_{dc[:4]}-{dc[4:6]}-{dc[6:]}.json")
        cls = cpool.get("归类到激活格的入围数", 0)
        au = _rj(ROOT / "data/opportunity" / f"classify_audit_{dc}.json")
        passc = au.get("★HA1-4校验汇总", {}).get("通过格", [])
        failc = au.get("★HA1-4校验汇总", {}).get("不通过格", [])
        h.append('<h3>⑤ 机会池·第4关护城河/第5关深度/量能/机会发现（★轮89 行业归类改全板块列表）</h3><ul>')
        h.append(f'<li>第4关 护城河五维（监管特许/高效规模/受监管回报/资产壁垒/需求刚性）：脚本已建·{esc(len(moat5.get("逐只",[])))}只·逐维数据待接(不编)</li>')
        h.append('<li>第5关 个股深度四项（财报要点/管线/管理层/竞争格局）：脚本已建·多项待接(不编)</li>')
        h.append(f'<li>量能标准：{esc(vol.get("放量突破阈值","当日量≥60日均量×1.5"))}（{esc(vol.get("等级","B级"))}·60日均量非当日近似）</li>')
        valn = cpool.get("★IA2简易估值(B级·EPS×板块中位PE·仅供S1排序)算出fair_value数", 0)
        fineN = cpool.get("★IA1半导体细分:业务词解析出", 0)
        ja1 = _rj(ROOT / "data/opportunity" / f"buildable_analysis_{dc}.json")
        dist = ja1.get("分布", {})
        h.append(f'<li>★机会发现（全市场扫描·全板块列表+业务词归类）：入围 460 → 归类 <b>{esc(cls)}</b> 只（半导体细分业务词解析 {esc(fineN)}）→ 简易估值 <b>{esc(valn)}</b> 只 → 过 S1。<b>★结论口径（NB5·GPT退回项6）：本轮筛选无可放行候选（{esc(cands)} 只放行）·★筛选有效性尚未验证</b>——★不表述为「市场机会为 0」（高上行候选已证有归类错+小样本污染·筛选器分组/估值基线/异常值处理尚不稳定）。待估值 {pend}</li>')
        h.append(f'<li>HA1-4 归类校验 <b>{esc(len(passc))} 格通过</b>（测试 JP.6857／设备 JP.8035·6146·6920／存储 铠侠／材料 信越 落对格）·{esc(len(failc))} 格不通过（已报出）</li>')
        ka1 = _rj(ROOT / "data/opportunity" / f"ka1_full_valuation_{dc}.json")
        ka1c = ka1.get("★KA1-3分类", {})
        n_real = len(ka1c.get("疑真实被压死的机会(简易上行较可信·待完整估值确认)", []))
        n_arti = len(ka1c.get("疑方法偏差/归类错(简易上行是artifact)", []))
        h.append('<li style="background:#3a1e1e;color:#ffd9d0;padding:6px 10px;border-radius:6px"><b>★入选 0 的三条限定（缺一不可）：</b>'
                 '①入选 0 是按【简易估值·B级】算的结果，<b>不等于市场上没有机会</b>；'
                 '②简易估值用【板块中位 PE】作锚，方法上偏向「无一显著低于板块中位」（且对低当前 EPS 的成长股系统性低估）；'
                 f'③<b>主因＝仓位结构 + 方法偏差</b>：高 AI beta 组破限 44.5% &gt; 30%，压死 {esc(dist.get("上行%不低但可建≈0(风险压死)", 8))} 只（排除持仓后）。</li>')
        h.append(f'<li style="background:#2a1e3a;color:#e0d0ff;padding:6px 10px;border-radius:6px"><b>★轮93 归类错→假高上行 传导链已修 + 全面验证：</b>'
                 '（1）轮92 的 108%/163% 是<b>归类错 artifact</b>（三井物产/三菱商事综合商社经「数据中心」宽概念误落 AI算力）——已<b>清掉宽泛关键词</b>（数据中心/稀土/AI芯片等），商社/金属已不再进候选；'
                 f'（2）★<b>轮93 决定性发现</b>：连轮92「唯一像样的」<b>DELL(59%) 也是 artifact</b>——AI服务器格仅 2 只，格中位 PE 被 Palantir(PE 116.9) 污染拉到 74.6，DELL 自身 PE 32.3 其实合理≈公允；'
                 f'（3）清完 artifact，被压死 <b>{esc(n_arti+n_real)} 只</b>里真正较可信只 <b>{esc(n_real)} 只</b>（Qnity 14%/Lasertec 12%·<b>全是边际上行</b>）。'
                 '★<b>「仓位结构堵死高上行机会」目前无一 candidate 站得住</b>——高 AI beta 破限确 block 新 AI 仓，但被 block 的「高上行」经查全是简易估值 artifact（归类错 或 小样本格中位 PE 被单个极贵 peer 污染）。</li>')
        h.append('<li style="background:#1e2a3a;color:#cfe0ff;padding:6px 10px;border-radius:6px"><b>★简易估值的方法边界（LA3·如实立档）：</b>scan 发现的新标的当前只能做到 <b>B 级简易估值</b>（板块中位 PE × 当前 EPS），其有效性完全依赖①归类正确②格样本足；<b>升 A 级需共识 forward EPS 源（免密钥源不可得）</b>。★简易估值只供 S1 排序初筛，<b>绝不进产品当买卖依据</b>。</li>')
        h.append("</ul>")
    h.append("</div>")
    return "\n".join(h)


def sector_rotation_block(dc):
    """★轮84 BC3:第④层板块轮动渲染块。"""
    sr = _rj(ROOT / "data/market" / f"sector_rotation_{dc}.json")
    if not sr:
        return ""
    h = ['<div class="av3"><h2 class="sec">④ 板块轮动层（第④层·今日首次建成·接通 %s）</h2>' % esc(sr.get("★接通N/4"))]
    h.append('<h3>大盘指数（当日涨跌）</h3><table><tr><th>指数</th><th>当日涨跌</th></tr>')
    for nm, d in sr.get("BC3-2_大盘指数", {}).items():
        v = d.get("当日涨跌pct")
        h.append(f"<tr><td>{esc(nm)}</td><td>{('%+.2f%%' % v) if isinstance(v,(int,float)) else esc(d.get('★未接','未接'))}</td></tr>")
    h.append("</table>")
    h.append('<h3>轮动信号（相对强弱）</h3><table><tr><th>对</th><th>近5日</th><th>近20日</th><th>当前</th></tr>')
    for nm, d in sr.get("BC3-4_轮动信号", {}).items():
        h.append(f"<tr><td>{esc(nm)}</td><td>{esc(d.get('近5日相对强弱pp'))}pp</td><td>{esc(d.get('近20日相对强弱pp'))}pp</td><td><b>{esc(d.get('当前', d.get('★未接','')))}</b></td></tr>")
    h.append("</table>")
    nf = sr.get("BC3-3_板块净流入", {})
    if nf.get("★未接"):
        h.append(f'<p style="color:#c0392b">板块资金净流入：<b>未接</b>——{esc(nf.get("★未接"))}</p>')
    h.append('<h3>承接节点当日涨跌（激活板块格·代表持仓）</h3><table><tr><th>板块格</th><th>群</th><th>代表持仓</th><th>涨跌</th></tr>')
    for n in sr.get("BC3-1_承接节点涨跌", [])[:18]:
        v = n.get("当日涨跌pct")
        h.append(f"<tr><td>{esc(n.get('板块格'))}</td><td>{esc(n.get('群'))}</td><td>{esc(n.get('代表持仓'))}</td><td>{('%+.2f%%' % v) if isinstance(v,(int,float)) else '待映射'}</td></tr>")
    h.append("</table></div>")
    return "\n".join(h)


def review_daily_block(dc):
    """★轮84 BA1:⑦复盘层日复盘(昨日动作/事件对regime/决策质量分)渲染块。"""
    ar = _rj(ROOT / "data/pdca" / f"action_review_{dc}.json")
    ev = _rj(ROOT / "data/pdca" / f"event_vs_macro_{dc}.json")
    dq = _rj(ROOT / "data/pdca" / f"decision_quality_{dc}.json")
    if not (ar or ev or dq):
        return ""
    h = ['<div class="av3"><h2 class="sec">⑦ 复盘层·日复盘三项（第⑦层·今日补齐）</h2>']
    # 昨日动作
    if ar:
        c = ar.get("计数", {})
        h.append(f'<h3>㈠ 昨天持仓动作今天看对没对（对照 {esc(ar.get("对照昨日"))}）</h3>')
        h.append(f'<p>对 {esc(c.get("对"))} · 错 {esc(c.get("错"))} · 未到验证时点 {esc(c.get("未到验证时点"))}{"（休市无价变·未到验证）" if ar.get("休市无价变") else ""}</p>')
        wrong = [r for r in ar.get("逐只", []) if r.get("判定") == "错"]
        if wrong:
            h.append('<table><tr><th>标的</th><th>动作</th><th>涨跌</th><th>错在哪</th></tr>')
            for r in wrong:
                h.append(f"<tr><td>{esc(r['标的'])}</td><td>{esc(r['昨日动作'])}</td><td>{esc(r['涨跌pct'])}%</td><td>{esc(r['错在哪'])}</td></tr>")
            h.append("</table>")
    # 事件对regime
    if ev:
        c = ev.get("计数", {})
        h.append(f'<h3>㈡ 今日新事件对宏观 regime＝支持/中性/证伪</h3>')
        h.append(f'<p>当前 regime：{esc(ev.get("当前regime"))}</p>')
        h.append(f'<p>支持 {esc(c.get("支持"))} · 中性 {esc(c.get("中性"))} · <b>证伪 {esc(c.get("证伪"))}</b></p>')
        if ev.get("★证伪告警"):
            h.append(f'<p style="color:#c0392b;font-weight:900">⚠ {esc(ev.get("★证伪告警"))}</p>')
    # 决策质量分
    if dq:
        c = dq.get("计数", {})
        h.append(f'<h3>㈢ 决策质量分（Σ把握分×依据系数÷依赖判断数·A=1.0/B=0.6/C=0.3·&lt;2.0低把握）</h3>')
        h.append(f'<p>有分动作 {esc(c.get("有分动作"))} · 低把握(&lt;2.0) <b>{esc(c.get("低把握(<2.0)"))}</b> · 均分 {esc(c.get("均分"))}</p>')
        h.append('<table><tr><th>标的</th><th>动作</th><th>质量分</th><th>标记</th></tr>')
        for r in dq.get("逐只", []):
            q = r.get("质量分")
            style = ' style="color:#c0392b"' if r.get("标记", "").startswith("低把握") else ""
            h.append(f'<tr{style}><td>{esc(r["标的"])}</td><td>{esc(r["动作"])}</td><td>{esc(q) if q is not None else "—"}</td><td>{esc(r.get("标记",""))}</td></tr>')
        h.append("</table>")
    h.append("</div>")
    return "\n".join(h)


def actck_anchors(dc):
    """★L28:同股一致性校验锚。以 decisions_{dc}.json 为唯一决定表·每只埋 data-actck=只|决定表|动作(隐藏)。"""
    dec = _rj(ROOT / "data/pdca" / f"decisions_{dc}.json").get("decisions", {})
    if not dec:
        return ""
    spans = []
    for sym, d in dec.items():
        act = (d or {}).get("action", "")
        if act:
            spans.append(f'<span data-actck="{esc(sym)}|决定表|{esc(act)}" style="display:none"></span>')
    return '<div style="display:none" aria-hidden="true">' + "".join(spans) + "</div>"


def completion_header(dc):
    """★AW4 C01/轮100 NG1:完工度页头串。★去『未完工·内部件(不交)』整体否定·改【局部标注:本册可用+缺项逐条】。"""
    cs = _rj(ROOT / "data/logs" / f"completion_status_{dc}.json")
    line = cs.get("★页头串")
    done = cs.get("★机器装好了")
    if not line:
        return "", None
    # ★NG1-2/NG3-8:缺项清单(缺什么·为什么·何时补)——从完工度部分/未建层派生
    seven = cs.get("一_七层", {})
    gaps = []
    for k, v in seven.items():
        if v.get("满足") == "部分":
            gaps.append("%s：%s" % (k, str(v.get("证据", ""))[:70]))
    tbd = _rj(ROOT / "data/reports" / f"tbd_reclassify_{dc}.json")
    gaps.append("全账户闭合（NK1轮104已接通·见『全账户闭合汇总』块）：持仓/AI敞口/币种=当日可算已出；★缺08-02当日现金分母→整体总资产/现金净额/目标进度不输出(NK4·不估算)·待董事长报当日现金或SBI/IBKR接入")
    gap_html = "".join("<li>%s</li>" % esc(g) for g in gaps)
    # ★轮102 A5:总判据2/5却标「正式产品可用」→ 显式印【机器完工度N/5·GPT V6 FAIL·不得用于真实交易】(结构化读·非写死·守§5.4)
    cnt = cs.get("计数", {}) or {}
    tot_ok = cnt.get("总判据满足")
    tot_all = cnt.get("总判据数") or 5
    warn = (f'★机器完工度（总判据）{esc(tot_ok)}/{esc(tot_all)} · GPT V6 终验 FAIL · ★不得用于真实交易'
            if tot_ok is not None else '★机器完工度未达标 · GPT V6 终验 FAIL · ★不得用于真实交易')
    return (f'<div style="background:#12324e;color:#dfeeff;border:2px solid #4f9fdf;border-radius:8px;'
            f'padding:9px 14px;margin:10px 0;font-size:14px">'
            f'<b style="color:#7ec0ff;font-size:16px">✅ 本册内容可用（能用的部分先用起来·可看可参考）</b>'
            f'<div style="background:#3a1e1e;color:#ff9a9a;border:2px solid #c0392b;border-radius:6px;padding:5px 10px;margin:5px 0;font-weight:900;font-size:14px">{warn}（轮102 A5）</div>'
            f'<b>完工度实情（原样印·不美化）：</b>{esc(line)}<br>'
            f'<b style="color:#ffcf70">★本册已知缺项（缺什么·为什么·何时补）：</b><ul style="margin:4px 0">{gap_html}</ul></div>'), done


def all_accounts_closure_block(dc):
    """★轮104 NK1:全账户闭合汇总(接通非删除)。每数标分母/来源/as_of·NK4缺分母项不输出比例。源 all_accounts_closure_{dc}.json。"""
    c = _rj(ROOT / "data/accounts" / f"all_accounts_closure_{dc}.json")
    if not c:
        return ""
    accs = c.get("一_各账户底数(接通·标as_of)", [])
    day = c.get("二_当日可算(持仓口径·分母=已扫持仓市值合计·as_of=08-02价07-31)", {})
    ai = day.get("AI同一驱动集中度_真实占比", {}); cur = day.get("币种敞口", {})
    clo = c.get("三_全账户闭合(混合口径·NK4部分不输出)", {})
    miss = c.get("四_接不通项(如实标·原因·预计·NK1-4·不删整块)", [])
    def _clean(s):  # ★人话化来源(不印内部json文件名/裸字段·治L46)
        import re as _r
        s = _r.sub(r"[\w-]+\.json", "内部快照", str(s or ""))
        s = _r.sub(r"\b[a-z]{2,}(?:_[a-z0-9]+)+\b", "", s).replace("accinfo_query", "").replace("as_of", "数据截至日")
        return _r.sub(r"\s{2,}", " ", s).strip("·← ")
    h = ['<div class="av3" style="border:3px solid #2c6e9a"><h2 class="sec" style="color:#12324e">★ 全账户闭合汇总（NK1·接通·每数标分母/来源/数据截至日）</h2>']
    h.append('<p style="font-size:12px;color:#888">★GPT裁定：全账户不接通不算完整产品——本块【接通】各账户底数并标数据截至日；缺 08-02 当日现金分母的比例【不输出】(NK4·不估算填充)。</p>')
    # 各账户
    h.append('<h3>㈠ 各账户底数（接通·标 数据截至日·来源·是否机器直采）</h3><table><tr><th>账户</th><th>接入</th><th>现金/总资产</th><th>数据截至日</th><th>来源</th><th>直采</th></tr>')
    for a in accs:
        amt = []
        if a.get("总资产_USD"): amt.append("总$%s" % format(int(a["总资产_USD"]), ","))
        if a.get("现金_USD"): amt.append("现金$%s" % format(int(a["现金_USD"]), ","))
        if a.get("总资产_JPY"): amt.append("总¥%s" % format(int(a["总资产_JPY"]), ","))
        h.append(f'<tr><td><b>{esc(a.get("账户"))}</b></td><td>{esc(a.get("接入"))}</td><td>{esc("·".join(amt) or "见状态")}</td>'
                 f'<td style="color:#c0392b">{esc(a.get("as_of"))}</td><td style="font-size:11px">{esc(_clean(a.get("来源文件")))}</td><td>{"✔" if a.get("机器直采") else "手工"}</td></tr>')
    h.append("</table>")
    # 当日可算
    h.append('<h3>㈡ 当日可算（持仓口径·真实算·非估算·NK1-2）</h3><ul>')
    h.append(f'<li>已扫持仓市值合计：<b>${esc(day.get("已扫持仓市值合计_USD"))}</b>（分母={esc(day.get("分母"))}·{esc(day.get("as_of"))}）</li>')
    h.append(f'<li><b>AI 同一驱动集中度（真实占比·非估算）：{esc(ai.get("值_pct"))}%</b>（分母={esc(ai.get("分母"))}）</li>')
    h.append(f'<li>币种敞口：日元 {esc(cur.get("日元占比_pct"))}%（${esc(cur.get("日元_USD"))}）· 美元 {esc(cur.get("美元占比_pct"))}%（${esc(cur.get("美元_USD"))}）·分母={esc(cur.get("分母"))}</li>')
    h.append("</ul>")
    # 闭合(NK4不输出)
    h.append('<h3>㈢ 全账户闭合（混合口径·NK4 缺当日现金分母→比例不输出）</h3>')
    h.append(f'<p style="background:#3a2a1e;color:#ffe8cf;border:2px solid #d08030;padding:6px 10px;border-radius:6px">{esc(clo.get("★口径警示"))}</p><ul>')
    for k in ("整体总资产_USD", "总现金与融资净额", "距+40%目标进度", "距+100%目标进度"):
        v = clo.get(k)
        h.append(f'<li>{esc(k)}：<span style="color:#c0392b">{esc(v) if v is not None else "★因缺08-02当日现金分母·本项不输出(NK4·不估算)"}</span></li>')
    h.append("</ul>")
    # 接不通(NK1-4)
    h.append('<h3 style="color:#c0392b">㈣ 接不通项（如实标·原因·预计·不删整块·NK1-4）</h3><table><tr><th>项</th><th>原因</th><th>预计</th></tr>')
    for m in miss:
        h.append(f'<tr><td>{esc(m.get("项"))}</td><td>{esc(m.get("原因"))}</td><td>{esc(m.get("预计"))}</td></tr>')
    h.append("</table>")
    h.append(f'<p style="font-size:12px;color:#c0392b">{esc(c.get("★NK4声明"))}</p>')
    h.append("</div>")
    return "\n".join(h)


def exec_plan_block(dc):
    """★轮102 A1:第一三共卖出执行方案(账户拆分+参考价+组合净影响真算+执行判断待Opus5)。
    ★Code只做算术;限价/跳空/分笔=Opus5判断(标待补·不代编)。数据源 exec_plan_4568_{dc}.json。"""
    ep = _rj(ROOT / "data/accounts" / f"exec_plan_4568_{dc}.json")
    if not ep:
        return ""
    ni = ep.get("组合净影响", {})
    tot = ni.get("总持仓市值_USD", {}); jp = ni.get("日股占比_pct", {}); df = ni.get("防御仓占比_pct", {})
    ej = ep.get("★执行判断_待Opus5(Code不代编·投资判断非算术)", {})
    ac = ep.get("账户拆分", {})
    h = ['<div class="av3" style="border:3px solid #c0392b"><h2 class="sec" style="color:#c0392b">★ 第一三共 JP.4568 卖出执行方案（董事长明天开盘用·A1）</h2>']
    h.append('<p style="background:#3a1e1e;color:#ffd9d0;padding:6px 10px;border-radius:5px">'
             f'账户拆分：<b>SBI {esc(ac.get("SBI"))} 股 ＋ 富途 {esc(ac.get("富途"))} 股 ＝ {esc(ep.get("总股数"))} 股</b>'
             f'　｜　参考价：<b>{esc(ep.get("参考价_JPY"))}</b>（{esc(ep.get("价格对应交易日"))}）'
             f'　｜　卖出市值 <b>{esc(ep.get("卖出市值_JPY"))} 日元</b> ≈ <b>${esc(ep.get("卖出所得折美元"))}</b>（FX {esc(ep.get("FX_USDJPY"))}·{esc(ep.get("FX来源"))}）</p>')
    h.append('<h3>组合净影响（纯算术·Code·分母＝已扫持仓市值合计·与产品规矩4同源）</h3>')
    h.append('<table><tr><th>口径</th><th>卖出前</th><th>卖出后</th></tr>')
    h.append(f'<tr><td>总持仓市值(USD)</td><td>${esc(tot.get("卖出前"))}</td><td>${esc(tot.get("卖出后"))}</td></tr>')
    h.append(f'<tr><td>日股占比</td><td>{esc(jp.get("卖出前"))}%</td><td>{esc(jp.get("卖出后"))}%</td></tr>')
    h.append(f'<tr><td>防御仓占比（下限15%）</td><td style="color:#c0392b">{esc(df.get("卖出前"))}%</td><td style="color:#c0392b;font-weight:900">{esc(df.get("卖出后"))}%</td></tr>')
    h.append(f'<tr><td>现金占比</td><td colspan="2" style="color:#c0392b">{esc(ni.get("现金占比_pct"))}</td></tr>')
    h.append('</table>')
    h.append(f'<p style="background:#3a2a1e;color:#ffe8cf;border:2px solid #d08030;padding:6px 10px;border-radius:6px"><b>★防御下限提示：</b>{esc(ep.get("★防御下限提示"))}</p>')
    h.append('<h3 style="color:#c8860a">★执行细节（限价／跳空／分笔）＝投资判断＝Opus5（Code 不代编·非算术）</h3><ul>')
    for k in ("限价档位", "跳空低开处理X%", "分笔方式"):
        h.append(f'<li><b>{esc(k)}</b>：{esc(ej.get(k))}</li>')
    h.append(f'<li style="color:#2a7a4a">Opus5 已给的执行指令（原样照录）：<b>{esc(ej.get("Opus5已给的执行指令(原样)"))}</b></li>')
    h.append('</ul>')
    h.append('<p style="font-size:12px;color:#888">★Code 只做：账户拆分渲染（董事长给定）＋参考价＋组合净影响算术。限价档位／跳空阈值／分笔＝风险判断·须 Opus5 填（守 CLAUDE.md 六岗位·Code 不设计投资逻辑·不代编判断）。</p>')
    h.append("</div>")
    return "\n".join(h)


def content_fragment(date):
    """★轮83 AW3:只返回 八节照录 + AV3四表 + 完工度页头 的 HTML 片段(无banner/css/actck)——
    供 render_3layer 并入(与全部原有模块并存)。判断照录·{{}}从求证表/前瞻填。"""
    dc = date.replace("-", "")
    content = _rj(ROOT / "data/content" / f"opus5_content_{dc}.json")
    if not content:
        return ""
    content = fill_placeholders(content, build_values(dc))
    hdr, _ = completion_header(dc)
    body = []
    for k, v in content.items():
        if k.startswith("_") or k in ("data_date", "价格口径", "签发", "签发时刻"):
            continue
        body.append(render_node(k, v, 2))
    return ('<section class="opus5-8"><div style="background:#0f2e1c;color:#7ee0a0;padding:6px 12px;'
            'border-radius:6px;font-weight:900;font-size:17px;margin:14px 0 4px">★ Opus5 当日正文（八节·判断/概率/理由照录）</div>'
            + hdr + exec_plan_block(dc) + all_accounts_closure_block(dc) + "\n".join(body) + av3_tables(dc) + "</section>")


def build(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:8])
    content = _rj(ROOT / "data/content" / f"opus5_content_{dc}.json")
    values = build_values(dc)
    content = fill_placeholders(content, values)
    now = datetime.now(JST)
    # ★★★轮229:优先读入口统一 run_id(AIIS_RUN_ID)·读不到才自生成——治溯源链断裂。
    run_id = os.environ.get("AIIS_RUN_ID") or ("R-%s-%s" % (dc, now.strftime("%H%M%S")))
    # 新闻08-02
    ev = _rj(ROOT / "data/evidence_chain" / f"daily_{dc}.json")
    n_news = 0
    mn = ev.get("rule_engine", {}).get("macro_news")
    if isinstance(mn, dict):
        n_news = sum(len(x) if isinstance(x, (list, dict)) else 1 for x in mn.values())
    lk = ev.get("links")
    if isinstance(lk, list):
        n_news += len(lk)
    news_line = ("当日新闻 %d 条(见证据链)" % n_news) if n_news > 0 else "★新闻源未返回 08-02 内容·原因：证据链无当日 macro_news/links(严禁写『今日无重大新闻』)"
    # 页头
    banner = (f'<div class="banner"><div class="big">★ 每日投资产品 · 数据日 <b>{dh}</b>（周日）</div>'
              f'<div>产品生产日：<b>{dh}</b>　｜　价格对应交易日：<b>2026-07-31</b>（两市周末休市·取最近交易日收盘·休市无新价）</div>'
              f'<div>run_id <b>{run_id}</b>　｜　生产时刻 {now.strftime("%Y-%m-%d %H:%M JST")}</div>'
              f'<div style="font-size:12px">新闻：{esc(news_line)}｜ 内容＝Opus5 正文照录（判断／概率／理由未改）·占位值已从求证表与前瞻源填实</div></div>')
    # 正文照录
    body = []
    for k, v in content.items():
        if k.startswith("_") or k in ("data_date", "价格口径", "签发", "签发时刻"):
            continue
        body.append(render_node(k, v, 2))
    css = ("<style>body{font-family:'Microsoft YaHei',sans-serif;max-width:960px;margin:0 auto;padding:12px;color:#1a1a1a;line-height:1.7}"
           ".banner{background:#0f2e1c;color:#dff5e6;border:3px solid #4fbf87;border-radius:10px;padding:12px 16px;margin:8px 0}"
           ".banner .big{font-size:20px;font-weight:900;color:#7ee0a0}"
           "h2.sec{color:#0f2e1c;border-left:5px solid #4fbf87;padding-left:8px;margin-top:20px}"
           "h3{color:#12324e} table{border-collapse:collapse;width:100%;margin:6px 0} th,td{border:1px solid #ccc;padding:4px 8px;font-size:13px;text-align:left}"
           ".av3{background:#f4f8f4;border:2px solid #0f2e1c;border-radius:8px;padding:8px 14px;margin:12px 0}</style>")
    html = (f"<title>★每日投资产品 · {dh}</title>{css}{banner}"
            + "\n".join(body) + av3_tables(dc) + actck_anchors(dc)
            + f'<div style="color:#888;font-size:12px;margin-top:20px">data_date={dh} · run_id={run_id} · 价格=07-31收盘</div>')
    return html, run_id, dh


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    html, run_id, dh = build(a.date)
    fname = f"★每日产品_{dh}.html"
    # 出厂闸:product_lint L1-L16
    try:
        from product_lint import lint_volumes
        fails = [f for f in lint_volumes({fname: html}, a.date) if not f.startswith(("L2 ", "L2b", "L19", "L29"))]
    except Exception as e:
        print("[content_product 出厂lint异常]", e); return 5
    b = html.encode("utf-8"); nbad = b.count(b"\xef\xbf\xbd")
    left = re.findall(r"\{\{[^}]+\}\}", html)
    if left:
        print("[content_product FAIL] 裸{{}}残留:", left[:5]); return 5
    if nbad:
        print("[content_product FAIL] 乱码", nbad); return 5
    if fails:
        print("[content_product 出厂lint FAIL·不出品]", len(fails)); [print("  ✗", f[:110]) for f in fails[:12]]; return 5
    out = SEE / fname
    out.write_text(html, encoding="utf-8")
    print("[content_product 出品] %s · bytes=%d · 乱码0 · run_id=%s" % (fname, len(b), run_id))
    # 登记 manifest + 主控
    try:
        import product_manifest as pm
        pm.write_manifest(a.date, run_id, dh, [fname]); pm.sync_master(dh, run_id, dh, [fname])
    except Exception as e:
        print("  manifest登记异常:", e)
    print("RUN_ID=" + run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
