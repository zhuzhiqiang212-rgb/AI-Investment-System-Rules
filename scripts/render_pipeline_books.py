# -*- coding: utf-8 -*-
"""★轮127 D6/PG1:七册接【管道版output】(替代旧 render_3layer)。每册内容来自管道七层+exec_params+PDCA台账+右栏6尺·
★每册显 provenance(来自哪几层·引用证据ID)·统一 run_id·★未填层如实标状态(不留白装满·PG1-4/PG2)。
★守 PG2:⑥未填→照出但标「★⑦无动作·因⑥未填」·★不用旧内容填充(不造壳)。★Code不填判断·只搬管道output。"""
import sys, os, json, argparse, time, re, html as _h
from datetime import datetime, timezone, timedelta
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import product_blocks as pb   # ★轮312:共用产品区块(前瞻/降级/深度重估·通用扫描)
OUT = ROOT / "00_请先看这里"


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def esc(x):
    return _h.escape(str(x)) if x is not None else ""


CSS = ("""<style>body{font-family:"Microsoft YaHei",sans-serif;max-width:1080px;margin:0 auto;padding:14px;color:#1a1a1a;line-height:1.7;background:#f5f6f8}
.banner{background:#12324e;color:#fff;border-radius:10px;padding:12px 16px;margin-bottom:8px}
.prov{background:#eaf2fb;border-left:5px solid #2c6e9a;border-radius:6px;padding:8px 12px;margin:8px 0;font-size:12px;color:#234}
.warn{background:#7B241C;color:#fff;border-radius:8px;padding:10px 14px;margin:8px 0}
table{border-collapse:collapse;width:100%;margin:8px 0}th,td{border:1px solid #bbb;padding:6px 9px;font-size:12.5px;text-align:left;vertical-align:top}th{background:#eef3f8}
h2{color:#12324e;border-left:5px solid #2c6e9a;padding-left:8px}.tag{display:inline-block;background:#12324e;color:#fff;border-radius:4px;padding:1px 7px;font-size:11px}</style>""")


_HEAD_INTRADAY = ""   # ★★★轮227:盘中生产横幅(build()按 daily_scan 日股时点设置·空则不显)


def _jp_intraday_banner(dc):
    """★★★轮227:若日股取的是【盘中价】(时点含「盘中」)→超大横幅标明『日股盘中价·未收盘』(2.6铁律:标清不冒充收盘)。"""
    d = _rj(ROOT / "data/market" / f"daily_scan_{dc}.json")
    rows = ((d.get("items", {}) or {}).get("1_当日20只价", {}) or {}).get("逐只") or d.get("逐只") or []
    jp_intraday = any("盘中" in str(r.get("时点") or "") for r in rows if str(r.get("code", "")).startswith("JP."))
    if not jp_intraday:
        return ""
    dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:8])
    return (f'<div style="background:#fff3cd;border:3px solid #d24b4b;border-radius:6px;padding:9px 13px;margin:6px 0;'
            f'font-size:15px;font-weight:900;color:#7B241C">⚠ 日股＝{dh} <u>盘中价（未收盘·数字会变）</u> · 美股＝最近完整交易日收盘价'
            f'<br><span style="font-size:11.5px;font-weight:400">★盘中生产：日股取当刻最新真价·非正式收盘·收盘后可能变动（2.6铁律：标清不冒充收盘）</span></div>')


def _wd_mkt(date):
    """★轮297 B3:从 YYYY-MM-DD 算真实星期几+休市判定+周末价格日·★时间感知(不写死·不假称收盘)。
    ★关键:周末的美股「最近交易日」是周五,但周五美股 05:00 JST(周六)才收盘——若现在<该时刻,美股仍盘中,不许标收盘。"""
    try:
        _JST = timezone(timedelta(hours=9))
        _now = datetime.now(_JST)
        _d = datetime.strptime(date.replace("-", ""), "%Y%m%d")
        _wd = _d.weekday(); _we = _wd >= 5
        _cn = "周一 周二 周三 周四 周五 周六 周日".split()[_wd]
        # 最近交易日(周末回退到周五);日期字符串
        _pdd = (_d - timedelta(days=(_wd - 4))) if _we else _d
        _pd = _pdd.strftime("%Y-%m-%d")
        # 该交易日的美股收盘时刻 = 交易日+1 的 05:00 JST
        _us_close = (_pdd + timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0, tzinfo=_JST)
        _us_closed = _now >= _us_close
        if _we:
            if _us_closed:
                note = f"（{_cn}·休市）｜价格＝{_pd} 收盘（日股东证收盘／美股 {_pd} 收盘）·★无盘中价"
            else:
                note = (f"（{_cn}·休市）｜日股＝{_pd} 收盘 ·【★美股 {_pd} 未收盘·收盘 05:00 JST·当前美股价为盘中价·非完整收盘·完整版待收盘后重跑】")
        else:
            note = f"（{_cn}·交易日）"
        return note
    except Exception:
        return ""

def _head(title, date, run_id, scan):
    _wm = _wd_mkt(date)
    return (f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>{esc(title)}·{esc(date)}</title>{CSS}</head><body>'
            f'<div class="banner"><div style="font-size:19px;font-weight:800">★ {esc(title)} · 数据日 {esc(date)}{esc(_wm)}</div>'
            f'<div style="font-size:12px;margin-top:4px">run_id <b>{esc(run_id)}</b> · 数据日 {esc(date)} · 生成 {esc(scan)} · ★数据源＝七层真管道output(唯一)</div></div>'
            # ★★★轮312 B1(董事长令):两条渲染线并存·页头互指防打开错文件。册1指向管道版。
            f'<div style="background:#fff3cd;border:2px solid #d9a400;border-radius:6px;padding:8px 12px;margin:6px 0;font-size:13px;font-weight:700;color:#8a6d00">'
            f'★本册为【册1·总览闭环】，五册之一（含前瞻研究区/结论降级清单·个股重估见册2·同业对照见册3）。七层管道版见 '
            f'<b>★每日产品_管道版_{esc(date)}.html</b></div>'
            + _HEAD_INTRADAY)


def _prov(层, ids, note=""):
    idtxt = ("·引用证据ID " + esc(ids)) if ids else ""
    return f'<div class="prov">★本册 provenance：内容来自 <b>{esc(层)}</b>{idtxt}{("·"+esc(note)) if note else ""}</div>'


def _foot():
    return '<p style="font-size:11px;color:#888">★管道版七册·Code只搬管道output不填判断·未填层如实标状态(不造壳)。</p></body></html>'


def _latest(pat):
    import glob as _g
    fs = sorted(_g.glob(str(ROOT / pat)))
    return fs[-1] if fs else None


def _pathb_html(dc):
    """★轮171 C:路径B异动原因(板块性/个股特有+公告线索)→册3。"""
    o = _rj(ROOT / "data/universe" / f"path_b_reason_{dc}.json")
    if not o:
        p = _latest("data/universe/path_b_reason_*.json"); o = _rj(p) if p else {}
    rows = o.get("逐只", []) or []
    if not rows:
        return ""
    ann = _rj(ROOT / "data/universe" / f"announcements_{dc}.json") or (_rj(_latest("data/universe/announcements_*.json")) if _latest("data/universe/announcements_*.json") else {})
    annm = ann.get("逐只公告", {}) or {}
    trs = ""
    for r in rows[:25]:
        a = annm.get(r["标的"], {})
        anns = "；".join("%s %s" % (h.get("日期"), h.get("类型")) for h in (a.get("公告", []) or [])[:2]) or "原因未知"
        cls = r.get("★原因状态", "")
        col = "#c0392b" if "个股特有" in cls else "#1e7a3c"
        trs += f'<tr><td>{esc(r["标的"])}</td><td>{esc(r.get("5日%"))}%</td><td style="color:{col}">{esc(str(r.get("★板块性/个股特有"))[:22])}</td><td style="font-size:11px">{esc(anns)}</td></tr>'
    return ('<h2>路径B异动·原因线索（轮157/158·板块性vs个股特有 + 公告）</h2>'
            '<div style="font-size:11.5px;color:#666">★机器算同板块同向比例区分板块性/个股特有·公告=SEC/EDINET窗口内(可能原因·不判因果)·★原因未知者不可据此行动(第一三共教训)。</div>'
            f'<div style="overflow-x:auto"><table style="font-size:12.5px"><tr><th>标的</th><th>5日%</th><th>板块性/个股特有</th><th>公告线索</th></tr>{trs}</table></div>')


def _priority_html(dc):
    """★轮171 C:候选优先级(多路径命中Top)→册3。"""
    o = _rj(ROOT / "data/opportunity" / f"candidate_priority_{dc}.json")
    if not o:
        p = _latest("data/opportunity/candidate_priority_*.json"); o = _rj(p) if p else {}
    top = (o.get("★Top30_板块非受损(个股层面优先)", []) or []) + (o.get("★★Top30_板块受损(便宜可能是板块问题·单独分组·须Opus5辨)", []) or [])
    if not top:
        return ""
    trs = ""
    for r in top[:15]:
        trs += f'<tr><td>#{esc(r.get("排名"))}</td><td>{esc(r.get("标的"))}</td><td>{esc("".join(r.get("命中路径", [])))}</td><td>{esc(r.get("★命中数"))}</td><td>{"√" if r.get("过第3关") else "×"}</td><td>{esc(r.get("路径B_5日异动%"))}</td><td>{"★板块受损" if r.get("★板块受损") else ""}</td></tr>'
    combo = o.get("★多路径命中组合分布", {})
    return ('<h2>候选优先级排序（轮151·结构化·供护城河评估先后·Code不判哪只更好）</h2>'
            f'<div style="font-size:11.5px;color:#666">多路径命中(≥2条)组合：{esc(json.dumps(combo, ensure_ascii=False))}·排序＝命中数↓→过第3关→异动跌幅↑→PE分位↑→大盘优先。</div>'
            f'<div style="overflow-x:auto"><table style="font-size:12px"><tr><th>#</th><th>标的</th><th>路径</th><th>命中</th><th>过3关</th><th>5日异动%</th><th></th></tr>{trs}</table></div>')


def _danger_html(dc):
    """★轮171 C:危险组合(库存增速vs营收增速)→册2a。"""
    o = _rj(ROOT / "data/universe" / f"danger_deepdive_{dc}.json")
    if not o:
        p = _latest("data/universe/danger_deepdive_*.json"); o = _rj(p) if p else {}
    rows = o.get("逐只", []) or []
    if not rows:
        return ""
    trs = ""
    for r in rows:
        d = r.get("深查", {})
        iy, ry = d.get("库存YoY%"), d.get("营收YoY%")
        v = d.get("★库存vs营收增速(董事长判据·Code只标)", d.get("口径", ""))
        col = "#c0392b" if "积压" in str(v) else "#888"
        trs += f'<tr><td>{esc(r["代码"])}</td><td>{esc(r.get("全名"))[:18] if isinstance(r.get("全名"), str) else "?"}</td><td>{esc(iy)}%</td><td>{esc(ry)}%</td><td style="color:{col};font-size:11px">{esc(str(v)[:30])}</td></tr>'
    return ('<h2>🔻 危险组合深查（轮167·capex升+库存升·库存增速vs营收增速）</h2>'
            '<div style="font-size:11.5px;color:#666">★营收增速>库存增速=备货(健康)·库存增速>营收增速=积压(危险)·★Code只算标·备货还是积压由Opus5/董事长判。</div>'
            f'<div style="overflow-x:auto"><table style="font-size:12px"><tr><th>代码</th><th>全名</th><th>库存YoY</th><th>营收YoY</th><th>机器标</th></tr>{trs}</table></div>')


def _defensive_html(dc):
    """★轮133 A-3:防御仓15%下限(分账户)+判据+哪几只算防御为什么(Opus5静态名单)。"""
    try:
        import defensive_gate as _dg
        o = _dg.build(dc)
    except Exception:
        return ""
    rows = ""
    for acc, r in (o.get("分账户", {}) or {}).items():
        det = "·".join("%s[%s] %s%%" % (d.get("名称") or d.get("symbol"), d.get("行业") or d.get("类") or "", d.get("占比pct")) for d in r.get("防御明细", [])) or "(无防御持仓)"
        col = "#c0392b" if r.get("★破15%下限") else "#0f7b3f"
        rows += (f'<tr><td>{esc(acc)}</td><td><b style="color:{col}">{esc(r.get("防御仓占比pct"))}%</b></td>'
                 f'<td>{"★破15%下限(防御不足)" if r.get("★破15%下限") else "达标(≥15%)"}</td><td style="font-size:11px">{esc(det)}</td></tr>')
    return (f'<h3 style="font-size:14px">逐账户·防御仓（★看板15%下限·防御股名单＝Opus5静态给定·Code不自行归类）</h3>'
            f'<table><tr><th>账户</th><th>防御仓占比</th><th>vs 15%</th><th>算作防御的(及为什么)</th></tr>{rows}</table>'
            f'<p style="font-size:11px;color:#666">★判据(Opus5给)：①非AI驱动·现金流稳定(保险/公用/必需消费/商社) ②不在AI承接节点·两者同时满足。★边界股(丰田=汇率敏感/万代·任天堂=消费非必需)由Opus5显式标·Code不自行判。现金/债不在本判据(只分类股票)。</p>')


def _opus5_zhengwen_html(dc):
    """★★轮178 CODE修:把 Opus5 当日正文(opus5_content_{date}.json)渲染进册1顶部。
    ★根因:主路七册此前【完全不读 opus5_content】(只渲机器管道层)→Opus5的C1-C7判断一句不进产品·
      即『正文已交付≠正文进产品』(比AN1-3深一层:AN1-3只查正文文件在不在·没查有没有被主路渲染)。
    ★Code只【逐字搬】Opus5正文·不改一字判断·不代编(G2)。缺件如实标不造壳(PG2)。"""
    o = _rj(ROOT / "data/content" / f"opus5_content_{dc}.json")
    if not o:
        return ('<div class="warn">★当日无 Opus5 正文交付件(opus5_content_%s.json)——'
                '正文未进产品(如实标·不造壳·PG2)。</div>' % dc)
    # ★★★轮230:全账户合计市值【动态实算】(治线193硬编码$1,415,867 stale·GPT发现册1/册4总资产矛盾)。
    #   分母=portfolio_concentration 全组合持仓(与单只20%口径同源·不再写死数)。
    _denom_txt = "全账户合计市值（★实算不可得·标NK4·不写死数）"
    try:
        import full_product_render as _fpr
        _prod = _rj(ROOT / "data/reports" / f"production_{dc}.json")
        _pc = _fpr.portfolio_concentration(_prod.get("holdings", []))
        _tv = _pc.get("total_mv") or _pc.get("total_usd")
        if _tv:
            _denom_txt = "全账户合计市值 ＄%s（FX归一USD·全组合持仓·portfolio_concentration 实算·与单只上限口径同一全组合分母）" % format(int(round(_tv)), ",")
    except Exception:
        pass

    def _render(v):
        if isinstance(v, str):
            return '<p style="margin:3px 0">%s</p>' % esc(v)
        if isinstance(v, list):
            return '<ul style="margin:3px 0 3px 4px">' + "".join('<li>%s</li>' % _render(x) for x in v) + '</ul>'
        if isinstance(v, dict):
            out = ""
            for k, val in v.items():
                if str(k).startswith("_"):
                    continue
                out += '<div style="margin:4px 0"><b>%s</b>：%s</div>' % (esc(k), _render(val))
            return out
        return esc(str(v))

    SECTIONS = ["第一屏_五句", "一_今天发生了什么", "二_对你的钱有什么影响", "三_逐只判断",
                "★三之二_我与外部研究的分歧（★不掩盖）", "四_今天做什么",
                "五_这台机器今天的状态", "六_边界（★我不知道的）"]
    # ★★★轮297 C1(董事长令·第二次点名):元数据字段一律不作章节标题(此前 date/岗位/交付时刻/version 被当 <h3> 印出)。
    #   元数据 denylist(要显示放页头一行·不进正文小节)。
    _META = {"_说明", "data_date", "价格口径", "签发", "签发时刻", "★与08-03的关系",
             "date", "岗位", "交付时刻", "version", "run_id", "scan", "生成", "生成时刻",
             "model", "模型", "作者", "id", "type", "source", "priced_at", "as_of"}
    skip = set(SECTIONS) | _META
    body = ""
    for sec in SECTIONS:
        if sec in o:
            body += ('<div style="border-left:3px solid #2c6e9a;padding-left:10px;margin:9px 0">'
                     '<h3 style="margin:4px 0;color:#12324e;font-size:15px">%s</h3>%s</div>' % (esc(sec), _render(o[sec])))
    # ★未在固定清单里的正文段也渲染(future-proof·不漏Opus5新增段)——★轮297 C1:仅渲染【内容小节】。
    #   判别:真正文小节键都含「_」(一_今天/第一屏_五句/★三之二_…);元数据键(date/岗位/交付时刻/version)都不含「_」。
    #   故 future-proof 只对含「_」且非 skip 的键生效→元数据永不冒充章节标题。
    for k, v in o.items():
        if k not in skip and not str(k).startswith("_") and "_" in str(k):
            body += ('<div style="border-left:3px solid #2c6e9a;padding-left:10px;margin:9px 0">'
                     '<h3 style="margin:4px 0;color:#12324e;font-size:15px">%s</h3>%s</div>' % (esc(k), _render(v)))
    # ★轮178 CODE修:本册口径 + 已知缺项(交付判据⑬c3④⑤要显式写口径与缺项·数据来自正文价格口径/六_边界)
    _bd = None
    for _bk in o:
        if str(_bk).startswith("六_边界") or "边界" in str(_bk):
            _bd = o[_bk]; break
    _gapitems = ("".join("<li>%s</li>" % esc(x) for x in _bd) if isinstance(_bd, list) else ("<li>%s</li>" % esc(str(_bd)) if _bd else "<li>正文未列缺项</li>"))
    koujing = ('<div style="background:#fbf7ee;border:1px solid #d9c48a;border-radius:6px;padding:9px 12px;margin:9px 0;font-size:12.5px">'
               '<b>★本册口径（写明后才可当正式产品交付·⑬c3④）</b>：数据日 <b>%s</b> · <b>价格对应交易日</b> %s · '
               '<b>分母</b>＝%s · '
               '<b>依据等级</b>：持仓现价/权重＝机器实测（特级）；前瞻/概率＝Opus5判断（B级·须复核项见今日提醒）。'
               '<div style="margin-top:6px"><b>★本册已知缺项（缺什么／为什么／何时补·Opus5「六_边界」原话）</b>：<ul style="margin:3px 0">%s</ul></div>'
               '</div>' % (esc(o.get("data_date", "")), esc(o.get("价格口径", "")), esc(_denom_txt), _gapitems))
    body += koujing
    return ('<div style="background:#f6faff;border:2px solid #2c6e9a;border-radius:8px;padding:12px 16px;margin:10px 0">'
            '<div style="font-size:17px;font-weight:800;color:#12324e">★董事长正文（Opus5 %s·数据日 %s）</div>'
            '<div style="font-size:11px;color:#468;margin:3px 0 8px">★投资判断的内容源·Code逐字搬Opus5正文·不改判断(G2)。价格口径：%s</div>'
            '%s</div>' % (esc(o.get("签发", "")), esc(o.get("data_date", "")), esc(o.get("价格口径", "")), body))


def _moat_current_html(dc):
    """★★★轮192 P0-2:护城河【评分表】从【唯一源 moat_current.json】读(根治正文13 vs 机器表7·同源渲染)。
    22只全上·13只08-05重评·9只07-28沿用(标source_date+★沿用未重评)·新旧不同显previous_score。"""
    o = _rj(ROOT / "data/moat/moat_current.json")
    rows = o.get("逐只", []) or []
    if not rows:
        return ""
    tr = ""
    def _sk(x):   # ★轮194:score可为int或"NK4·未上市"字符串(SPCX)·非数值排末尾
        s = x.get("score")
        return -s if isinstance(s, (int, float)) else 99
    for r in sorted(rows, key=_sk):
        prev = ("（previous %s·07-28）" % r.get("previous_score")) if "previous_score" in r else ""
        sd = r.get("source_date"); tag = ("<b style='color:#e6a700'>沿用07-28未重评</b>" if r.get("★沿用未重评") else "08-05重评")
        tr += ("<tr><td>%s</td><td><b>%s</b></td><td>%s</td><td style='font-size:11px'>%s·%s%s</td></tr>"
               % (esc(r.get("代码")), esc(r.get("score")), esc(str(r.get("grade"))[:16]), esc(sd), tag, esc(prev)))
    kv = o.get("★一致性闸比对键", {})
    return ('<h2>护城河评分表（★唯一源 moat_current·%d只·13重评+9沿用07-28·同源渲染防正文机器表打架）</h2>'
            '<div class="prov">★本表与正文/统计/动作层同读 moat_current.json(source_hash=%s·count=%s)·一致性闸硬核·§5.4。</div>'
            '<table><tr><th>标的</th><th>总分</th><th>结论</th><th>评分来源(source_date)</th></tr>%s</table>'
            % (len(rows), esc(kv.get("source_hash")), esc(kv.get("count")), tr))


_JP_NAMES = {"4568": "第一三共", "6758": "索尼", "6857": "爱德万", "7203": "丰田",
             "7832": "万代", "7974": "任天堂", "8001": "伊藤忠", "8766": "东京海上", "9984": "软银"}


def _jp_a_gate_html(dc):
    """★★★轮223:日股決算短信 A 档扫描结果(jp_A_gate_{date}.json)渲进册2a。
    ★根因修:此前【渲染层完全未读 jp_A_gate】→日股A档证据一句不进产品(GPT V7『不得延误真实日股数据进入产品』)。"""
    d = _rj(ROOT / "data/funnel" / f"jp_A_gate_{dc}.json")
    if not d:
        return '<div style="font-size:12px;color:#888;margin:8px 0">★今日无日股決算短信A档扫描件(jp_A_gate_%s.json)</div>' % dc
    结果 = d.get("结果", {}) or {}
    汇总 = d.get("汇总", {}) or {}
    a_rows, miss_rows = "", ""
    for code, r in 结果.items():
        nm = _JP_NAMES.get(code, code)
        if r.get("A档开放"):
            w = r.get("五元组", {}) or {}
            幅 = w.get("幅度")
            幅s = ("%+.1f%%" % (幅 * 100)) if isinstance(幅, (int, float)) else esc(幅)
            原文 = r.get("证据原文") or r.get("表格原文行") or ""
            a_rows += (f'<tr style="background:#eafaf1"><td><b>{esc(nm)}</b> {esc(code)}</td>'
                       f'<td><b style="color:#1e8449">A档开出</b></td>'
                       f'<td>{esc(w.get("指标"))} 同比 <b>{幅s}</b>·{esc(w.get("方向"))}</td>'
                       f'<td style="font-size:11px">证据原文（決算短信）：「{esc(原文)}」<br>路径={esc(r.get("_事实路径"))}</td></tr>')
        else:
            断点 = r.get("断点") or r.get("状态") or ""
            miss_rows += (f'<tr><td>{esc(nm)} {esc(code)}</td><td style="color:#888">未开A档</td>'
                          f'<td colspan="2" style="font-size:11px;color:#888">{esc(str(断点)[:80])}</td></tr>')
    return ('<h2>🇯🇵 日股決算短信 A 档（J-Quants·当日真实公告·verifier 六项核）</h2>'
            '<div style="font-size:11.5px;color:#666">★A档＝证据合格（六项对齐＋证券代码身份＋证据原文可核）·<b>非买入信号</b>。开放范围限決算短信标准摘要表/散文路径（GPT V7 轮217 批准）。</div>'
            f'<div style="font-size:12px;margin:4px 0">扫描 {esc(汇总.get("扫描数"))} 只 · A档开出 <b>{esc(汇总.get("A档开出"))}</b> · 连接 {esc(汇总.get("连接"))}</div>'
            f'<div style="overflow-x:auto"><table style="font-size:12px"><tr><th>标的</th><th>A档</th><th>营收(同比)</th><th>证据原文/断点</th></tr>{a_rows}{miss_rows}</table></div>')


def build(date):
    global _HEAD_INTRADAY
    dc = date.replace("-", "")
    _HEAD_INTRADAY = _jp_intraday_banner(dc)   # ★★★轮227:盘中横幅(日股盘中价才显)
    date = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:8])
    pipe = _rj(ROOT / "data/market" / f"layer_pipeline_{dc}.json")
    if not pipe:
        # 现场跑管道
        try:
            from layer_pipeline import run as _run
            pipe = _run(dc)
        except Exception as e:
            return {"错误": "管道output缺失且现场跑失败:%s" % e}
    layers = {L["层"][0]: L for L in pipe.get("七层", [])}
    em = _rj(ROOT / "data/market" / f"evidence_map_{dc}.json")
    ep = _rj(ROOT / "data/accounts" / f"exec_params_{dc}.json")
    now = datetime.now(JST)
    # ★★★轮229:优先读入口统一 run_id(AIIS_RUN_ID)·读不到才自生成(兼容单独调用)——治溯源链断裂。
    run_id = os.environ.get("AIIS_RUN_ID") or ("R-%s-%s" % (dc, now.strftime("%H%M%S")))
    scan = now.strftime("%Y-%m-%d %H:%M:%S JST")
    # ★run_id 边车(真实epoch·跨午夜安全)
    _hp = ROOT / "data/logs" / f"runid_history_{dc}.json"
    _hj = _rj(_hp); _hj.setdefault("run_ids", []).append(run_id)
    _hj.setdefault("epochs", {})[run_id] = int(time.time()); _hj["latest"] = run_id
    _hp.parent.mkdir(parents=True, exist_ok=True); _hp.write_text(json.dumps(_hj, ensure_ascii=False, indent=2), encoding="utf-8")

    # ⑥/⑦ 状态(PG2 核心:⑦有无动作)
    l6, l7 = layers.get("⑥", {}), layers.get("⑦", {})
    has_action = l7.get("output数", 0) > 0
    归因 = pipe.get("★⑦无动作的真实归因(PE3-1·非首空层标签)")
    # ★修正3:0动作分两种——【维持结论】(⑥已判维持·0笔·产品完整)vs【未填故障】(该填没填·草案)。
    #   守铁律:仅当归因是维持结论(非该填没填/阻断)才出结论横幅;真未填→仍出草案横幅。
    _l6_state = str(l6.get("★真实状态") or "")
    _is_hold_conclusion = (not has_action) and ("已填" in _l6_state) and ("该填没填" not in _l6_state) and ("阻断" not in _l6_state)
    if has_action:
        action_banner = (f'<div style="background:#0f2e1c;color:#dff5e6;border-radius:8px;padding:10px 14px;margin:8px 0">★ ⑦已产出 {l7.get("output数")} 条可执行动作（⑥决策清单已填·D3链通）。</div>')
    elif _is_hold_conclusion:
        action_banner = (f'<div style="background:#0f2e1c;color:#dff5e6;border-radius:8px;padding:10px 14px;margin:8px 0">'
                         f'★ ⑦无交易动作 · 因：{esc(归因) or "⑥已判维持持仓·0笔决策"}——'
                         f'★这是【结论】非草案：⑥本层判断已填(维持持仓)·决策清单0笔·产品完整。</div>')
    else:
        action_banner = (f'<div class="warn">★ ⑦无可执行动作 · 因：{esc(归因) or "上游未填"}——'
                         f'本册按管道真实状态出（草案·非可执行成品）·★未用旧内容填充(不造壳·PG2)。</div>')

    files = {}

    # ── 册1 总览闭环 ← 七层状态 + ①动摇置顶 ──
    状态表 = pipe.get("★逐层真实状态(PE3-2·替代通到第X层)", [])
    # ★乙4/丁5(轮333):册1空层醒目占位——因Opus5工单未填而空的层·大字红条一眼可见"缺此层"(★比管道版更醒目·董事长第一眼)。
    def _state_cell(r):
        st = str(r.get("★真实状态") or "")
        _ly = str(r.get("层") or "")
        _num = _ly[0] if _ly and _ly[0] in "①②③④⑤⑥⑦" else None
        # ★轮337 甲1:册1每层判断【旁边】的右栏尺锚(依据哪把尺+与尺是否矛盾红条+关键条文摘录+看册5)·左→右咬合。
        _anchor = pb.layer_ruler_anchor_html(ROOT, dc, _num) if _num else ""
        # ★丙3(轮335):⑦交易0笔是【由⑥推出的结果·非漏填】→显中性绿条·不当"缺此层"红条。
        if "⑦" in _ly and any(k in st for k in ("无动作", "无换仓", "无交易", "维持")) and "未填" not in st and "该填没填" not in st:
            return ('<div style="border:2px solid #2f6b4f;background:#eef7f1;border-radius:6px;padding:7px 10px;'
                    'font-size:13px;font-weight:700;color:#2f6b4f">今日交易 0 笔 —— 这是由⑥推出的结果，不是漏填</div>'
                    f'<div style="font-size:10.5px;color:#888;margin-top:2px">{esc(st)}</div>' + _anchor)
        _out0 = str(r.get("output数") or "0") in ("0", "")
        # ★空/未产出系状态(缺此层·待Opus5)→醒目;排除【已填结论/已产出/维持持仓(有效0动作结论)】。
        _empty_kw = any(k in st for k in ("待Opus5", "待 Opus5", "未填", "该填没填", "阻断", "待判断",
                                          "客观空", "状态延续", "无观测", "无候选", "无动作", "无换仓", "全null"))
        _ok_kw = any(k in st for k in ("已填", "已产出", "维持持仓", "已激活"))
        empty = (_empty_kw or _out0) and not _ok_kw
        if empty:
            return ('<div style="border:2px solid #c0392b;background:#fdecea;border-radius:6px;padding:7px 10px;'
                    'font-size:14px;font-weight:900;color:#c0392b">★本层今日无判断（等 Opus 5 填写）'
                    '<br><span style="font-size:12px">产品不完整·缺此层</span></div>'
                    f'<div style="font-size:10.5px;color:#888;margin-top:2px">{esc(st)}</div>' + _anchor)
        return f'<b>{esc(st)}</b>' + _anchor
    strows = "".join(f'<tr><td><b>{esc(r["层"])}</b></td><td>{esc(r["output数"])}</td><td>{_state_cell(r)}</td><td style="font-size:11px">{esc(r["★上游接入"])}</td></tr>' for r in 状态表)
    shake = [e for e in em.get("路1_对6尺持续验证(★动摇置顶)", []) if "动摇" in str(e.get("印证动摇"))]
    shrows = "".join(f'<li>【{esc(e.get("印证动摇"))}·{esc(e.get("对应尺"))}】{esc(str(e.get("证据"))[:80])}（{esc(e.get("来源"))}·{esc(e.get("as_of"))}）</li>' for e in shake)
    # ★轮130 A/B:今日提醒清单(D4巡检C/D类 + 见分晓到期)进册1顶部
    try:
        import daily_alerts as _al
        alerts = _al.build(dc)
    except Exception:
        alerts = {}
    _al_rows = ""
    for x in (alerts.get("B_见分晓到期", {}) or {}).get("到期未核对", []) + (alerts.get("B_见分晓到期", {}) or {}).get("临近", []):
        _al_rows += f'<li>🔔 <b>见分晓</b>：{esc(x.get("标的"))}·{esc(x.get("尺度"))}·核对日 {esc(x.get("核对日"))}·<b style="color:#c0392b">{esc(x.get("状态"))}</b>——{esc(x.get("★须核对"))}</li>'
    for x in alerts.get("A_D类_触价检测", []):
        _al_rows += f'<li>🎯 <b>触价</b>：{esc(x.get("名称"))}·<b style="color:#c0392b">{esc(x.get("触发"))}</b>·{esc(x.get("算式"))}（{esc(x.get("★提醒"))}）</li>'
    for x in alerts.get("A_B类今昨diff(只报变化事实·不判意义G2)", []):
        _al_rows += f'<li>🔄 <b>{esc(x.get("类"))}</b>：{esc(x.get("项"))}·{esc(x.get("变化"))}（★只报变化事实·意义待Opus5判·G2）</li>'
    for x in alerts.get("A_C类_机器取不到需人工补", []):
        _al_rows += f'<li>🔧 <b>{esc(x.get("类"))}</b>：{esc(x.get("项"))}·缺 {esc(x.get("缺"))}→需人工补：{esc(x.get("需人工补"))}</li>'
    # ★轮148 E10 A-4:四闭环到期提醒(该复盘本闭环)
    for x in alerts.get("E_闭环到期(E10·该复盘本闭环)", []):
        _al_rows += f'<li>🔁 <b>闭环到期</b>：{esc(x.get("闭环"))}·周期 {esc(x.get("周期"))}·<b style="color:#c0392b">{esc(x.get("★状态"))}</b>（上次复盘 {esc(x.get("上次复盘"))}）</li>'
    # ★★轮175 C:外部资料未消化(显要·防08-03答疑类静默漏掉)
    _ed = alerts.get("★F_外部资料未消化(轮175·防静默漏)", {}) or {}
    if _ed.get("未消化数", 0) > 0:
        _al_rows += f'<li>📄 <b style="color:#c0392b">外部资料未消化 {esc(_ed.get("未消化数"))} 份</b>（提取成功但未被任何已填判断引用·须Opus5核是否相关·不阻断出品但不许静默漏）：'
        _al_rows += "；".join(f'{esc(x.get("日期"))} {esc(x.get("来源"))}《{esc(str(x.get("标题"))[:24])}》' for x in (_ed.get("未消化清单", []) or [])[:12]) + '</li>'
    # ★★★轮186 A:见分晓日历(机器从registry算·非Opus5口头)——今日到期 + ★已过期未记分(记分卡空转)
    _vc = alerts.get("★H_见分晓日历(轮186·机器从registry算·非Opus5口头)", {}) or {}
    if _vc.get("今日到期数", 0) > 0:
        _al_rows += f'<li>📅 <b style="color:#c0392b">今日 {esc(_vc.get("今日到期数"))} 条预测到期·须Opus5记分</b>：' + "；".join(f'{esc(x.get("ticker"))}({esc(x.get("horizon"))}·{esc(x.get("verdict_date"))})' for x in (_vc.get("今日到期", []) or [])) + '（★到期由机器从registry读verdict_date算·非口头指定·§5.4）</li>'
    if _vc.get("★已过期未记分数", 0) > 0:
        _al_rows += f'<li>⏰ <b style="color:#c0392b">★已过期但未记分 {esc(_vc.get("★已过期未记分数"))} 条(记分卡空转·须Opus5补记)</b>：' + "；".join(f'{esc(x.get("ticker"))}({esc(x.get("horizon"))}·到期{esc(x.get("verdict_date"))})' for x in (_vc.get("★已过期未记分", []) or [])) + '</li>'
    _sm = alerts.get("汇总", {})
    alerts_html = (f'<div style="background:#fff8e1;border:2px solid #e6a700;border-radius:8px;padding:10px 14px;margin:8px 0">'
                   f'<div style="font-size:15px;font-weight:800;color:#7a5a00">🔔 今日提醒清单（C机器取不到 {_sm.get("C类项",0)} · D触价 {_sm.get("D类触价",0)} · B今昨变化 {_sm.get("B类变化",0)} · 见分晓到期 {_sm.get("到期未核对",0)}/临近 {_sm.get("临近",0)} · 闭环到期 {_sm.get("闭环到期",0)}）</div>'
                   f'<ul style="margin:6px 0">{_al_rows or "<li>今日无提醒</li>"}</ul>'
                   f'<div style="font-size:11px;color:#a80">★触价/到期/闭环到期是机器信号·是否动作/记分/复盘由Opus5判(G2)。</div></div>') if alerts else ""
    # ★轮146 C-2:今日可动清单(候选池内·快层)进册1顶部
    cp = _rj(ROOT / "data/opportunity" / "candidate_pool.json")
    _mv = cp.get("★今日可动清单(池内·快层)", []) or []
    movable_html = ""
    if _mv:
        _rows = "".join(f'<li>🎯 <b>{esc(x.get("标的"))}</b>·{esc(x.get("★可动信号"))}（单日{esc(x.get("单日%"))}%/5日{esc(x.get("5日%"))}%·入口{esc(x.get("★入口"))}·{esc(x.get("★须过关"))}）</li>' for x in _mv[:20])
        movable_html = (f'<div style="background:#eef7ff;border:2px solid #2c6e9a;border-radius:8px;padding:10px 14px;margin:8px 0">'
                        f'<div style="font-size:14px;font-weight:800;color:#12324e">📌 今日可动清单（候选池 {cp.get("★候选池只数",0)} 只·池内快层算·非重扫全市场·{len(_mv)}条可动）</div>'
                        f'<ul style="margin:6px 0">{_rows}</ul>'
                        f'<div style="font-size:11px;color:#468">★候选池持久化(E6)·今日{"触发重跑" if (cp.get("★重跑触发(4条·G22)",{}) or {}).get("任一触发") else "未触发·沿用上版"}·可动仅入口须过第2/3/4关(不免筛)。</div></div>')
    # ★轮129 D2/PI3-1:①层动摇条→图文决策卡(四段+红绿+迷你图·G14大白话)
    try:
        import decision_cards as _dc
        _l1cards = _dc.layer1_cards(dc)
    except Exception as _e:
        _l1cards = []
    cards_html = ('<h2>①层·图文决策卡（今日事件→对照尺→判定→大白话依据·3秒找依据）</h2>' + "".join(_l1cards)) if _l1cards else ""
    # ★★轮178 CODE修:Opus5当日正文置顶(七实情C1-C7的内容源·主路此前不读致一句不进产品)
    _opus5_zw = _opus5_zhengwen_html(dc)
    b1 = (_head("册1·总览闭环", date, run_id, scan) + _prov("★Opus5正文 + ①~⑦全层状态 + ①证据映射器动摇置顶 + 今日提醒", em.get("★证据ID区间"))
          + pb.anchor_drift_html(ROOT, dc)   # ★轮335 乙2:E-ID内容锚漂移→红条置顶(引用证据已变·须重判·不得沿用)
          + pb.degrade_html(dc)   # ★★★轮312 A4:结论降级七类+合规声明→第一屏置顶(action_banner之前)
          + action_banner +
          _opus5_zw +
          movable_html + alerts_html +
          '<h2>七层真实状态（管道逐层·非"通到第X层"标签）</h2>'
          f'<table><tr><th>层</th><th>output</th><th>★真实状态</th><th>上游接入</th></tr>{strows}</table>'
          f'<h2>①层·被现实动摇的尺（PDCA入口·置顶·{len(shake)}条）</h2><ul>{shrows or "<li>今日无动摇尺</li>"}</ul>'
          + cards_html
          + f'<div style="border:2px solid #6a4c93;border-radius:8px;padding:10px 14px;margin:12px 0;background:#faf7ff">{pb.forward_html(ROOT, dc)}</div>'   # ★轮312 A3:前瞻研究区→册1总览
          + _foot())
    files["1_总览闭环"] = b1

    # ── 册2a/2b 持仓深研 ← ⑥ + exec_params ──
    holds = ep.get("三只", [])
    dl = []  # ⑥决策清单
    js = _rj(ROOT / "data/pipeline" / f"judgment_slots_{dc}.json")
    _sl = (js.get("②~⑦层工单", {}) or {}).get("⑥持仓比较", {}) or {}
    dl = [d for d in ((_sl.get("★决策清单(可执行·Opus5填·⑦读此+exec_params组装·空则⑦不产出)", {}) or {}).get("决策") or []) if d.get("标的")]
    dl_by = {d["标的"]: d for d in dl}
    rc = _sl.get("★须复核既有判断(NV3)", [])
    rc_html = ""
    for r in rc:
        cs = r.get("★复核槽位(Opus5填)", {}) or {}
        if cs.get("维持原判/修正/撤回"):
            rc_html += (f'<div class="prov">★{esc(r.get("标的"))} 复核结论=<b>{esc(cs.get("维持原判/修正/撤回"))}</b>·理由：{esc(str(cs.get("理由")))}</div>')  # ★轮297 C2/D3:判断正文不截断(去[:200])

    def _hold_rows(sub):
        rows = ""
        for p in sub:
            sym = p.get("symbol"); px = (p.get("现价") or {}).get("值")
            d = dl_by.get(sym)
            act = (f'<b style="color:#c0392b">{esc(d.get("方向"))}·{esc(d.get("股数"))}股</b>' if d else '<span style="color:#888">⑥未给决策(无动作)</span>')
            jp = p.get("★分笔数", {}); tk = p.get("★跳空阈值", {}); pc = p.get("每档价格", {})
            rows += (f'<tr><td><b>{esc(p.get("name"))}</b><br>{esc(sym)}</td><td>{esc(px)}<br><span style="font-size:10px">{esc((p.get("现价") or {}).get("as_of"))}</span></td>'
                     f'<td>{act}</td><td>分笔{esc(jp.get("值"))}·分档{esc(pc.get("值"))}</td>'
                     f'<td>跳空{esc(tk.get("值"))}%<br><span style="font-size:10px">{esc(str(tk.get("算法"))[:40])}</span></td></tr>')
        return rows
    # ★轮129 D2/PI3-1:持仓判断卡(⑥复核已填→出卡·⑥未填→不出卡·标待判断·不造壳PI1-4)
    try:
        import decision_cards as _dc2
        _hcards, _pending = _dc2.holding_cards(dc)
    except Exception:
        _hcards, _pending = [], []
    _pend_bits = []
    if _pending:
        _pend_bits.append(f'★以下 {len(_pending)} 只持仓 ⑥复核【待Opus5填】→不出卡：{esc("·".join(str(x) for x in _pending[:20]))}')
    if not dl:   # ★PI1-4:⑥换仓决策清单未填→无持仓动作卡·标待判断(不造壳)
        _pend_bits.append("★⑥换仓/处置决策清单【待Opus5填】(0笔)→今日无持仓动作卡·标『待判断』·★未用旧内容造壳(PI1-4)")
    _pend_html = ('<div style="background:#f2f2f2;border-radius:6px;padding:8px 12px;margin:8px 0;font-size:12px;color:#666">'
                  + "<br>".join(_pend_bits) + '</div>') if _pend_bits else ""
    half = (len(holds) + 1) // 2
    # ★轮155 A:护城河客观数据表(EDGAR/EDINET·两误导数带注·负ROIC不隐藏)→册2a
    # ★轮194:唯一源护城河评分表【独立 try】——不可被下方 _mpt 客观数据表异常一起吞掉(一致性闸依赖此表嵌 source_hash·上次FAIL直接原因)
    try:
        _moat_cur_tbl = _moat_current_html(dc)   # ★唯一源moat_current·22只·嵌source_hash+count=NN
    except Exception as _e_cur:
        _moat_cur_tbl = '<div style="color:#c00;font-size:12px">★护城河唯一源表渲染失败:%s</div>' % esc(str(_e_cur))
    try:
        import moat_product_table as _mpt
        _obj_tbl = _mpt.render_html(dc)   # ★客观数据表(EDGAR/EDINET)
        _dio_tbl = _mpt.render_dio_html(dc)   # ★轮166 A:DIO/capex表并列
        _dio_tbl = _dio_tbl + _danger_html(dc)   # ★轮171 C:危险组合(库存vs营收增速)进册2a
    except Exception:
        _obj_tbl = ""; _dio_tbl = ""
    _moat_tbl = _moat_cur_tbl + _obj_tbl   # ★唯一源表在前·客观数据表在后
    for tag, sub, tl, showcards in (("2a_持仓深研上", holds[:half], "册2a·持仓深研（上）", True), ("2b_持仓深研下", holds[half:], "册2b·持仓深研（下）", False)):
        cards_sec = (('<h2>持仓·图文决策卡（⑥判断已填的·四段+红绿+迷你图）</h2>' + "".join(_hcards)) if _hcards else
                     '<div style="font-size:12px;color:#888;margin:8px 0">★今日⑥持仓判断暂无已填卡（见下方待判断）</div>') if showcards else ""
        b = (_head(tl, date, run_id, scan) + _prov("⑥持仓比较 + exec_params(到价/分笔/跳空·机器)", None,
                   "⑥决策清单%d笔" % len(dl)) + action_banner + rc_html + (cards_sec if showcards else "") + ((_jp_a_gate_html(dc) + _moat_tbl + _dio_tbl) if showcards else "") + (_pend_html if showcards else "") +
             '<h2>持仓·执行参数（现价/分笔/分档/跳空来自exec_params机器·方向/股数来自⑥决策清单）</h2>'
             f'<table><tr><th>标的</th><th>现价(as_of)</th><th>⑥决策</th><th>分笔/分档(exec_params)</th><th>跳空规则</th></tr>{_hold_rows(sub)}</table>'
             + (f'<div style="border:2px solid #7B241C;border-radius:8px;padding:10px 14px;margin:12px 0;background:#fdf7f5">{pb.deepdive_judgments(ROOT, dc)}</div>' if tag == "2a_持仓深研上" else "")   # ★轮312 A1:个股深度重估(爱德万v4等)→册2a
             + (pb.drift_holdings_html(ROOT, dc) if tag == "2a_持仓深研上" else "")   # ★轮327 丙C2/C3:漂移三分类+理由三件套状态→册2a
             + _foot())
        files[tag] = b

    # ── 册3 机会板块 ← ④ + ⑤ ──
    l4, l5 = layers.get("④", {}), layers.get("⑤", {})
    s4rows = "".join(f'<tr><td>{esc(o.get("板块"))}</td><td>{esc(o.get("★当日涨跌pct(机器观测)"))}%</td><td>{esc(o.get("方向(机器初判枚举)"))}</td><td style="font-size:11px">{esc(str(o.get("★③传下的方向(解释框架)"))[:60])}</td></tr>' for o in l4.get("output", [])[:12])
    s5rows = "".join(
        (f'<li><b>{esc(o.get("板块"))}</b> → <b style="color:#c0392b">{esc(o.get("symbol"))}</b>'
         f'{"（★宇宙外新标的·可换入候选）" if o.get("★宇宙外新标的") else "（持仓内）"}'
         f'{("·"+esc(o.get("★A-4须过关"))) if o.get("★宇宙外新标的") else ""}</li>')
        if o.get("symbol") else f'<li>{esc(o.get("板块"))}·{esc(o.get("候选标的") or o.get("候选"))}</li>'
        for o in l5.get("output", []))
    b3 = (_head("册3·机会板块", date, run_id, scan) + _prov("④板块轮动 + ⑤机会池", None,
               "④状态：%s；⑤状态：%s" % (l4.get("★真实状态"), l5.get("★真实状态"))) +
          '<h2>④板块（机器涨跌 × ③传下方向）</h2>'
          f'<table><tr><th>板块</th><th>当日涨跌</th><th>机器初判</th><th>③传下方向(解释框架)</th></tr>{s4rows or "<tr><td colspan=4>④无板块数据</td></tr>"}</table>'
          f'<h2>⑤机会池候选</h2>'
          f'<div style="background:#fdecea;border:1px solid #c0392b;border-radius:6px;padding:8px 12px;margin:6px 0;font-size:11.5px;color:#7B241C">'
          f'★候选来源声明：以下承接节点标的＝<b>Opus5 手填</b>(sector_activation 判定人=Opus5·<b>非机器发现</b>·董事长07-31举例经手填入)·总则六「只锚定义不锚死名单」。'
          f'★裁定：标的宇宙将改为【富途可拉全市场+Opus5定归类】(轮135查清:美/日/港/A/新/马可拉·★韩股拉不了·全市场列表需分页)·本清单为过渡·不冒充机器产物。</div>'
          f'<ul>{s5rows or ("<li>★"+esc(l5.get("空原因") or "⑤无候选")+"</li>")}</ul>' + _pathb_html(dc) + _priority_html(dc)
          + f'<div style="border:2px solid #12324e;border-radius:8px;padding:10px 14px;margin:12px 0;background:#f4f8fc">{pb.deepdive_peers(ROOT, dc)}</div>'   # ★轮312 A2:同业对照(Teradyne等)→册3机会板块
          + f'<div style="border:2px solid #12324e;border-radius:8px;padding:10px 14px;margin:12px 0;background:#f4f8fc">{pb.sector_split_html(ROOT, dc)}</div>'   # ★轮330 甲A4:拆格强度(格18国防军工/格19网络安全·格19不得从产品消失)→册3
          + _foot())
    files["3_机会板块"] = b3

    # ── 册4 组合记分 ← ⑦ + PDCA台账 ──
    ledger = _rj(ROOT / "data/pdca/layer_judgment_ledger.json")
    ent = ledger.get("entries", ledger) if isinstance(ledger, dict) else ledger
    ent = ent if isinstance(ent, list) else []
    lrows = "".join(f'<tr><td>{esc(e.get("date"))}</td><td>{esc(e.get("标的"))}</td><td>{esc(e.get("复核结论") or e.get("类型"))}</td><td>{esc(e.get("引用证据ID"))}</td></tr>' for e in ent[:8])
    if has_action:
        a_rows = "".join(f'<tr><td>{esc(a.get("标的"))}</td><td>{esc(a.get("账户"))}</td><td>{esc(a.get("方向"))}·{esc(a.get("股数"))}股</td><td>分档{esc(a.get("分档价格"))}·跳空{esc((a.get("跳空规则") or {}).get("阈值pct"))}%</td></tr>' for a in l7.get("output", []))
        act_sec = f'<h2>⑦交易动作（可执行）</h2><table><tr><th>标的</th><th>账户</th><th>方向股数(⑥)</th><th>执行参数(exec_params)</th></tr>{a_rows}</table>'
    else:
        act_sec = f'<div class="warn">★⑦无动作·因：{esc(归因) or "⑥未填"}——组合记分册今日无可执行动作段（★不造壳·PG2）。</div>'
    # ★★轮130 C:富途/SBI 分账户目标进度(看板G5·不合并)+跨账户同一驱动集中度→册4
    tg = _rj(ROOT / "data/target" / f"target_gap_{dc}.json")
    _acc_rows = ""
    for accn in ("富途", "SBI"):
        a = tg.get(accn, {}) or {}
        A = a.get("当日总资产A_USD"); g = a.get("目标", {}) or {}
        if A:
            _acc_rows += (f'<tr><td><b>{esc(accn)}</b></td><td>${esc("{:,.0f}".format(A))}</td>'
                          f'<td>距+40%还需赚 <b>${esc("{:,.0f}".format(g.get("+40%需赚_USD",0)))}</b></td>'
                          f'<td>距+100%还需赚 <b>${esc("{:,.0f}".format(g.get("+100%需赚_USD",0)))}</b></td></tr>')
        else:
            _acc_rows += f'<tr><td><b>{esc(accn)}</b></td><td colspan=3>★当日总资产缺·目标进度NK4不输出</td></tr>'
    _cl2 = (_rj(ROOT / "data/accounts" / f"all_accounts_closure_{dc}.json").get("二_当日可算(持仓口径·分母=已扫持仓市值合计·as_of=08-02价07-31)", {}) or {})
    _conc = (_cl2.get("AI同一驱动集中度_真实占比", {}) or {}).get("值_pct")
    # ★★轮131 B:逐账户集中度拆分——同一驱动(driver_exposure·标vintage)+30%看板对照·★破限标红
    import glob as _g131, re as _re131
    _def = sorted(_g131.glob(str(ROOT / "data/risk/driver_exposure_*.json")))
    _de = _rj(_def[-1]) if _def else {}
    _de_v = str(_de.get("date") or "")
    _drv_rows = ""
    for accn, av in (_de.get("账户", {}) or {}).items():
        for gn, g in (av.get("驱动组", {}) or {}).items():
            pct = g.get("跨度贡献占比pct")
            if pct is None:
                continue
            broke = g.get("★破单一环节30%")
            _drv_rows += (f'<tr><td>{esc(accn)}</td><td>{esc(gn)}</td><td><b style="color:{"#c0392b" if broke else "#0f7b3f"}">{esc(pct)}%</b></td>'
                          f'<td>{"★破30%上限" if broke else "未破30%"}</td></tr>')
    _drv_html = (f'<h3 style="font-size:14px">逐账户·同一驱动集中度（对照看板 单一驱动30%上限·数据日 {esc(_de_v)}）</h3>'
                 f'<table><tr><th>账户</th><th>驱动组</th><th>占比</th><th>vs 30%上限</th></tr>{_drv_rows}</table>') if _drv_rows else ""
    # ★★轮132 B:币种归一逐只市值→单只上限20%(对照看板)。富途 US.=USD/JP.=JPY÷FX;SBI 同币种(JPY)直接算。
    _fx = (tg.get("富途", {}) or {}).get("fx_used")
    _single = []
    _fpos = _rj(ROOT / "data/accounts" / f"futu_positions_{dc}.json").get("futu_positions", [])
    if _fx and _fpos:
        _vals = []
        for h in _fpos:
            mv = h.get("broker_market_val"); s = str(h.get("symbol") or "")
            if isinstance(mv, (int, float)):
                _vals.append((h.get("name"), mv if s.startswith("US.") else (mv / _fx if s.startswith("JP.") else mv)))
        _tot = sum(v for _, v in _vals) or 1
        _top = max(_vals, key=lambda x: x[1]) if _vals else (None, 0)
        _single.append(("富途", _top[0], _top[1] / _tot * 100))
    import glob as _gsb
    _sbf = sorted(_gsb.glob(str(ROOT / "data/accounts/sbi_sleeve_*.json")))
    if _sbf:
        _sh = _rj(_sbf[-1]).get("holdings", [])
        _st = sum(h.get("market_value_jpy", 0) for h in _sh) or 1
        if _sh:
            _tp = max(_sh, key=lambda x: x.get("market_value_jpy", 0))
            _single.append(("SBI", _tp.get("name"), _tp.get("market_value_jpy", 0) / _st * 100))
    _sng_rows = "".join(f'<tr><td>{esc(a)}</td><td>{esc(nm)}</td><td><b style="color:{"#c0392b" if p>20 else "#0f7b3f"}">{p:.1f}%</b></td><td>{"★破20%上限" if p>20 else "未破20%"}</td></tr>' for a, nm, p in _single)
    _sng_html = (f'<h3 style="font-size:14px">逐账户·单只上限（★币种归一·对照看板 单只20%上限）</h3>'
                 f'<table><tr><th>账户</th><th>最大单只</th><th>占比</th><th>vs 20%</th></tr>{_sng_rows}</table>') if _sng_rows else ""
    c_sec = (f'<h2>分账户目标进度（★看板G5·富途/SBI 各自算·不合并）</h2>'
             f'<table><tr><th>账户</th><th>当日总资产</th><th>距+40%(中性)</th><th>距+100%(激进)</th></tr>{_acc_rows}</table>'
             + _sng_html + _drv_html +
             f'<p style="font-size:11.5px;color:#555">★IBKR/bitFlyer＝静止账户·<b>不做目标管理</b>(看板G6·仅附录/被清算时提醒)。'
             f'★<b>跨账户同一驱动风险</b>：AI供应链同一驱动集中度(全账户合并)＝<b style="color:#c0392b">{esc(_conc)}%</b>——分账户算·但跨账户合并风险仍并表显示(B-2/C-2)。</p>'
             + _defensive_html(dc) +
             f'<p style="font-size:11px;color:#888">口径：{esc(str(tg.get("口径",""))[:60])}·依据07-19尺·Code照算法搬数未改判断(G2)。</p>')
    # ★轮130 B-3:见分晓到期未核对累计→册4(★Code只计数·不代记分·G2)
    _bd = alerts.get("B_见分晓到期", {}) or {}
    _due_rows = "".join(f'<tr><td>{esc(x.get("标的"))}</td><td>{esc(x.get("尺度"))}</td><td>{esc(x.get("核对日"))}</td><td><b style="color:#c0392b">{esc(x.get("状态"))}</b></td></tr>' for x in (_bd.get("到期未核对", []) + _bd.get("临近", [])))
    due_sec = (f'<h2>见分晓到期检测（PDCA闭环·★到期未核对累计 {_bd.get("★到期未核对累计", 0)} 条）</h2>'
               f'<table><tr><th>标的</th><th>尺度</th><th>核对日</th><th>状态</th></tr>{_due_rows or "<tr><td colspan=4>今日无到期/临近</td></tr>"}</table>'
               f'<p style="font-size:11px;color:#a80">★到期须核对结果并记分——★记分是 Opus5 的判断·Code 只检测提醒不代记(G2)。</p>')
    # ★乙2/丁1(轮333):两版贡献度(锁定判断版 vs 现价影子版)→册4·并印背离结论。
    _contrib = pb.contribution_two_way_html(ROOT, dc)
    _contrib_block = (f'<div style="border:2px solid #7B241C;border-radius:8px;padding:10px 14px;margin:12px 0;background:#fdf7f5">'
                      f'{_contrib}'
                      f'<div style="margin-top:8px;padding:7px 10px;background:#fdecea;border-radius:6px;font-size:13px;font-weight:800;color:#c0392b">'
                      f'★两版符号相反（锁定判断版 +3.004pp vs 现价影子版 −5.596pp），说明锁定时的判断与现价已背离；'
                      f'组合期望回报当前为【不知道】（结论降级第⑧类）。</div></div>') if _contrib and "未" not in _contrib[:20] else ""
    b4 = (_head("册4·组合记分", date, run_id, scan) + _prov("⑦交易动作 + 分账户目标 + PDCA台账 + 见分晓到期", None,
               "⑦状态：%s" % l7.get("★真实状态")) + act_sec + c_sec + _contrib_block + due_sec +
          f'<h2>PDCA判断台账（只增不改·近8条）</h2><table><tr><th>日期</th><th>标的</th><th>结论</th><th>引用证据ID</th></tr>{lrows or "<tr><td colspan=4>台账暂无</td></tr>"}</table>' + _foot())
    files["4_组合记分"] = b4

    # ── 册5 规则附件 ← 右栏6尺 ──
    rulers = ["右栏_完整世界观描述.html", "右栏_完整国家战略地图.html", "右栏_板块地图.html",
              "右栏_过滤标准筛选规则.html", "右栏_估值方法学.html", "右栏_持仓完整档案.html"]
    rrows = "".join(f'<li><span class="tag">尺</span> {esc(r)}{"（在库）" if (OUT/r).exists() else "（★缺文件）"}</li>' for r in rulers)
    # ★轮336 甲(MAIN-06):右栏六块底子原文+左右咬合→册5(整个右栏·非只列名)。左=今天哪层判断用到本块尺(依据右栏哪把尺)·右=尺原文。
    b5 = (_head("册5·规则附件", date, run_id, scan) + _prov("右栏6尺(世界观/国家战略/板块/过滤/估值/持仓档案)", None) +
          f'<h2>右栏6尺（管道①~⑥层各自锚定的尺·附件名录）</h2><ul>{rrows}</ul>'
          + f'<div style="border:2px solid #12324e;border-radius:8px;padding:10px 14px;margin:12px 0;background:#fbfcfe">{pb.right_column_html(ROOT, dc)}</div>'
          + _foot())
    files["5_规则附件"] = b5

    # 写盘(★每日产品_日期_序号_册名.html)
    written = []
    for tag, htmlc in files.items():
        fn = OUT / f"★每日产品_{date}_{tag}.html"
        fn.write_text(htmlc, encoding="utf-8")
        b = htmlc.encode("utf-8")
        written.append({"册": fn.name, "KB": round(len(b) / 1024, 1), "乱码": b.count(b"\xef\xbf\xbd")})
    # ★轮156 C:索引册＝【六册合并】(董事长唯一入口PDF渲的就是它·含册2a护城河表)。原只放册1→PDF漏册2a。
    idx = OUT / f"★每日产品_{date}.html"
    _order = ["1_总览闭环", "2a_持仓深研上", "2b_持仓深研下", "3_机会板块", "4_组合记分", "5_规则附件"]
    _head_part = files["1_总览闭环"].split("<body>", 1)[0] + "<body>"
    _bodies = []
    for _i, _k in enumerate(_order):
        _h = files.get(_k, "")
        _m = re.search(r"<body>(.*)</body>", _h, re.S)
        if _m:
            _inner = _m.group(1)
            _bodies.append(_inner if _i == 0 else f'<div style="page-break-before:always"></div>{_inner}')
    idx.write_text(_head_part + "".join(_bodies) + "</body></html>", encoding="utf-8")

    return {"run_id": run_id, "date": date, "has_action": has_action, "归因": 归因,
            "册": written, "index": idx.name}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    r = build(a.date)
    if r.get("错误"):
        print("[七册] 失败:", r["错误"]); return 1
    print("[七册·管道版] run_id=%s · ⑦有动作=%s · 归因=%s" % (r["run_id"], r["has_action"], r.get("归因")))
    for w in r["册"]:
        print("  %s · %sKB · 乱码%d" % (w["册"], w["KB"], w["乱码"]))
    print("  索引:", r["index"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
