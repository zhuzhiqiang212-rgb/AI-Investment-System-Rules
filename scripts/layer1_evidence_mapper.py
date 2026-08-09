# -*- coding: utf-8 -*-
"""★轮114 NU1:①层重构＝【每日证据→右栏6尺 的映射器】。★不限定输入源内容方向·只固定处理方式(锚定义不锚内容·守总则六)。
四类输入(只定义渠道·不定义内容)走【同一条链】：A公开新闻/公告/宏观 B当日价格行为 C持仓与候选当日表现 D★Drive任意文件。
链：证据→①识别说了什么(从资料本身)→②映射到右栏①~⑥哪把尺(印证/★动摇/无关)→③映射下游层/维度→④标注(来源/独立性/依据等级/as_of)。
两路输出：路1对6尺持续验证(★动摇置顶)·路2对下游维度依据。★B/C恒有→①层output恒非空·★『今日无事件』从此不出现。
NU2 映射不上→标『候选新维度』(PDCA入口)。NU5 Drive自动检测·不按内容分流·标来源人与独立性(9份全湖水一人·非独立)。"""
import sys, json, glob, os, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
RULERS = {"①": "世界观", "②": "国家战略", "③": "资金流动", "④": "板块地图", "⑤": "过滤五关", "⑥": "持仓档案"}


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _ev(证据, 尺, 印证动摇, 强度, 下游层, 维度, 方向, 来源, 独立, 依据级, as_of, prov=""):
    return {"证据": 证据, "对应尺": 尺, "印证动摇": 印证动摇, "强度": 强度,
            "下游层": 下游层, "维度": 维度, "方向": 方向,
            "来源": 来源, "是否独立信源": 独立, "依据等级": 依据级, "as_of": as_of, "provenance": prov}


def build(date):
    dc = date.replace("-", "")
    evid = []      # 全部证据(走同一条链)
    unmapped = []  # NU2 映射不上→候选新维度
    ep = _rj(ROOT / "data/accounts" / f"exec_params_{dc}.json")
    # ★W-2:对比基准 production 改为【动态选最近可用的一版(data_date < 当日)】·不写死 20260802
    import re as _re
    _prevs = []
    for _p in glob.glob(str(ROOT / "data/reports" / "production_*.json")):
        _m = _re.search(r"production_(\d{8})\.json$", os.path.basename(_p))
        if _m and _m.group(1) < dc:
            _prevs.append((_m.group(1), _p))
    _prevs.sort()
    _prev_date = _prevs[-1][0] if _prevs else ""
    prev = _rj(_prevs[-1][1]) if _prevs else {}
    pmap = {h["symbol"]: h.get("price") for h in prev.get("holdings", [])}
    JP_DEF = {"JP.8766", "JP.6758", "JP.7203", "JP.8001", "JP.7832", "JP.7974", "JP.4568"}

    # ── B 当日价格行为(恒有)──
    jp, us = [], []
    for r in ep.get("三只", []):
        s, cur = r["symbol"], r["现价"].get("值"); pv = pmap.get(s)
        if not (cur and pv):
            continue
        chg = (cur - pv) / pv * 100
        (jp if s.startswith("JP.") else us).append((s, r["name"], chg))
    # ★W-1:as_of 改为从实际数据时间戳读取·不写死「08-03」
    _cur_asof = ""
    for _r in ep.get("三只", []):
        _a = (_r.get("现价") or {}).get("as_of")
        if _a:
            _cur_asof = str(_a); break
    _pdh = ("%s-%s-%s" % (_prev_date[:4], _prev_date[4:6], _prev_date[6:])) if _prev_date else "无历史基准"
    asof_px = "当日价格·%s（OpenD实测·exec_params）｜对比基准 production_%s" % (_cur_asof or "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]), _pdh)
    if jp:
        jp_avg = sum(c for _, _, c in jp) / len(jp)
        dirn = "普跌" if jp_avg < -0.5 else ("普涨" if jp_avg > 0.5 else "涨跌互现")
        evid.append(_ev("日股开盘：%d 只均 %+.2f%%·%s（%s）" % (len(jp), jp_avg, dirn, "·".join("%s%+.1f%%" % (n, c) for _, n, c in sorted(jp, key=lambda x: x[2])[:4])),
                        "④板块地图", "动摇" if dirn == "普跌" else "印证", "中",
                        "④板块轮动", "日股板块强弱", dirn, "OpenD价格·机器直采", "是(市场客观价)", "A", asof_px, "B类价格行为"))
        # ★NU6-2 第一三共 vs SBI/日股普跌——直接检验『该卖』判断
        d4568 = next((c for s, _, c in jp if s == "JP.4568"), None)
        others = [c for s, _, c in jp if s != "JP.4568"]
        if d4568 is not None and others:
            oavg = sum(others) / len(others)
            rel = d4568 - oavg
            evid.append(_ev("★第一三共 %+.2f%% vs 其余日股均 %+.2f%%（相对 %+.1fpp·%s）——直接检验『该卖第一三共』判断" % (
                            d4568, oavg, rel, "相对抗跌" if rel > 1 else "同步"),
                            "⑥持仓档案", "★动摇" if rel > 1 else "无关", "高" if rel > 2 else "中",
                            "⑥持仓比较", "第一三共处置(卖/守)", "抗跌→质疑卖出理由（会计造假是基本面·价格抗跌是市场分歧·须Opus5复核卖出前提）",
                            "OpenD价格·机器直采", "是(市场客观价)", "A", asof_px, "B类·NU6-2直接检验"))
    if us:
        us_avg = sum(c for _, _, c in us) / len(us)
        dirn = "普涨" if us_avg > 0.5 else ("普跌" if us_avg < -0.5 else "涨跌互现")
        evid.append(_ev("美股隔夜：%d 只均 %+.2f%%·%s（%s）" % (len(us), us_avg, dirn, "·".join("%s%+.1f%%" % (n, c) for _, n, c in sorted(us, key=lambda x: -x[2])[:4])),
                        "③资金流动", "印证" if dirn == "普涨" else "动摇", "中",
                        "③资金流动", "风险偏好/资金流向", "美股风险偏好回升" if dirn == "普涨" else "美股承压", "OpenD价格·机器直采", "是(市场客观价)", "A", asof_px, "B类价格行为"))

    # ── C 持仓与候选当日表现(恒有) ──
    if jp or us:
        allc = jp + us
        up = [(n, c) for _, n, c in allc if c > 0]; dn = [(n, c) for _, n, c in allc if c < 0]
        evid.append(_ev("全持仓当日：涨 %d 跌 %d（最强 %s·最弱 %s）" % (
                        len(up), len(dn), max(allc, key=lambda x: x[2])[1], min(allc, key=lambda x: x[2])[1]),
                        "⑥持仓档案", "印证", "低", "⑥持仓比较", "持仓当日表现", "分化(美涨日跌)",
                        "OpenD价格·机器直采", "是", "A", asof_px, "C类持仓表现"))

    # ── A 公开新闻/宏观:★轮123 PC1——用①②层当日真实事实【逐条】进证据台账(不再只写源健康一行) ──
    wv = _rj(ROOT / "data/market" / f"worldview_{dc}.json")
    st = _rj(ROOT / "data/market" / f"strategy_{dc}.json")
    _fresh = wv.get("★新鲜度达标(取到当日事实·bool)")
    _newest = wv.get("★A类最新事实日期(PA3)") or wv.get("★源最新新闻日期")
    _srch = wv.get("★源健康(枚举·PA3)")
    # A-1 源健康(新鲜度)——达标→印证数据质量;不达标→★动摇(须处置)。★源健康=元证据·非市场方向·由Opus5看
    evid.append(_ev("公开新闻源状态：新鲜度%s·A类最新事实 %s·源健康『%s』(多源:Google/CNBC/Yahoo·任一当日即达标)" % ("达标" if _fresh else "未达标", _newest, _srch),
                    "①世界观", "印证" if _fresh else "★动摇", "低",
                    "①世界观", "新闻源健康/新鲜度", "源已取到当日事实" if _fresh else "源未取到当日·需处置",
                    "worldview多源扫描", "是(多源冗余)" if _fresh else "否", "B", wv.get("as_of"), "A类·源健康(PC1)"))
    # A-2 逐条新闻事实→尺(★Code只做机械路由:内容关键词→触及哪把尺;印证/动摇方向由Opus5判·Code不断)
    _REGIME = ["降温", "缓和", "升级", "反转", "逆转", "突破", "破裂", "开战", "停火", "增产", "减产",
               "暴跌", "暴涨", "崩", "危机", "制裁", "加征", "escalat", "ceasefire", "surge", "plunge",
               "crash", "reversal", "breakthrough", "tension", "ebb", "opec"]

    def _news_rulers(t):
        t = t or ""; tl = t.lower(); out = []
        if any(k in t for k in ("地缘", "中东", "伊朗", "以色列", "俄", "乌克兰", "台海", "朝鲜", "战争", "冲突", "停火", "制裁", "核")) \
           or any(k in tl for k in ("geopolit", "iran", "israel", "russia", "ukraine", "war", "conflict", "ceasefire", "sanction", "middle east", "nuclear")):
            out.append(("①世界观", "①世界观", "地缘/秩序"))
        if any(k in t for k in ("关税", "出口管制", "立法", "拨款", "行政令", "管制")) \
           or any(k in tl for k in ("tariff", "export control", "legislation", "policy shift")):
            out.append(("②国家战略", "②国家战略", "政策/管制"))
        if any(k in t for k in ("油价", "原油", "能源", "利率", "收益率", "美元", "通胀", "降息", "加息", "增产", "减产")) \
           or any(k in tl for k in ("oil", "crude", "opec", "energy", "yield", " rate", "dollar", "inflation", "fed")):
            out.append(("③资金流动", "③资金流动", "资金/能源价格"))
        if any(k in t for k in ("半导体", "芯片", "科技", "板块")) \
           or any(k in tl for k in ("semiconductor", "chip", "sector")):
            out.append(("④板块地图", "④板块轮动", "板块/产业"))
        return out or [("①世界观", "①世界观", "宏观事实(待细分)")]

    _raw_news = []
    for c in wv.get("五类", []):
        for h in c.get("逐条", []):
            _raw_news.append((h.get("标题"), h.get("来源"), h.get("发布")))
    for c in st.get("四类", []):
        for h in c.get("逐条", []):
            _raw_news.append((h.get("标题"), h.get("来源"), h.get("发布")))
    _seen_t = set(); news_ct = 0
    for title, nsrc, pub in _raw_news:
        if not title:
            continue
        kk = title[:40]
        if kk in _seen_t:
            continue
        _seen_t.add(kk); news_ct += 1
        if news_ct > 16:
            break
        is_regime = any((w in title) or (w in title.lower()) for w in _REGIME)
        for 尺, 层, 维 in _news_rulers(title):
            evid.append(_ev("新闻事实：%s" % title[:70], 尺,
                            "★可能动摇(待Opus5判印证/动摇)" if is_regime else "触及(待Opus5判)",
                            "中" if is_regime else "低",
                            层, 维, "见标题·方向待Opus5判(Code不断)", nsrc or "多源RSS",
                            "是(权威媒体·多源)", "B", pub or (date + " 当日"), "A类·当日新闻(PC1)"))

    # ── D Drive 外部资料目录(★自动检测·不按内容分流·同一条链·NU5) ──
    ext_txt = sorted(glob.glob(str(ROOT / "data/external/text/*.txt")))
    ext_json = sorted(glob.glob(str(ROOT / "data/external/*.json")))
    dfiles = [os.path.basename(p) for p in ext_txt]
    mapped_d, unmap_d = 0, 0
    for fn in dfiles:
        low = fn.lower()
        # 从文件名/内容识别它说了什么(不预设分类)·映射到尺
        if any(k in fn for k in ("资金流", "仓位", "去仓位")):
            尺, 层, 维 = "③资金流动", "③资金流动", "机构仓位/资金流"
        elif any(k in fn for k in ("DUV", "半导体", "AI硬件")):
            尺, 层, 维 = "④板块地图", "④板块轮动", "半导体/AI硬件"
        elif any(k in fn for k in ("节奏", "前瞻", "策略")):
            尺, 层, 维 = "①世界观", "①世界观", "市场节奏/regime"
        else:
            尺 = 层 = 维 = None
        if 尺:
            mapped_d += 1
        else:
            unmap_d += 1
            unmapped.append({"资料": fn, "★未能映射": "现有6尺无对应维度", "★候选新维度": "待Opus5/董事长判(从文件内容定)"})
        evid.append(_ev("Drive外部资料：%s" % fn, 尺 or "★未能映射·候选新维度", "印证" if 尺 else "候选新维度", "低",
                        层 or "待定", 维 or "★候选新维度", "见资料", "湖水（Drive目录）", "否(9份全湖水一人·非独立·GPT裁定)", "B", fn[:11], "D类·NU5"))

    # ── NU2:同类反复映射不上≥3次→建议改尺 ──
    sugg = []
    if unmap_d >= 3:
        sugg.append("★建议新增/修订尺：Drive类反复映射不上 %d 次→现有6尺覆盖不到·交 Opus5 与董事长判" % unmap_d)

    # ★轮123 PC1-3:给每条证据分配【插入序ID】E1..EN(★稳定·不随动摇置顶排序变——台账引用E1/E2/E4须恒指同一条)
    for _i, _e in enumerate(evid, 1):
        _e["id"] = "E%d" % _i

    # ── 两路输出(NU3) ──
    路1 = sorted([e for e in evid if e["对应尺"] and "无关" not in e["印证动摇"]],
                key=lambda e: (0 if "动摇" in e["印证动摇"] else 1))  # ★动摇置顶(★id已固定·排序不改id)
    路2 = [{"id": e["id"], "证据": e["证据"][:60], "下游层": e["下游层"], "维度": e["维度"], "方向": e["方向"], "依据等级": e["依据等级"]} for e in evid]

    out = {
        "_说明": "★轮114 NU ①层=每日证据→6尺映射器。四类(A新闻/B价格/C持仓/D Drive任意文件)走同一条链·不限定内容方向只固定处理方式。★output恒非空·『无事件』类结论不出现。",
        "date": date, "生成时刻": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "证据总数": len(evid), "★output恒非空": len(evid) > 0,
        "★证据ID区间": ("%s~%s" % (evid[0]["id"], evid[-1]["id"])) if evid else "无",
        "★全证据台账(带ID·插入序稳定)": [{"id": e["id"], "证据": e["证据"][:70], "对应尺": e["对应尺"],
                                          "印证动摇": e["印证动摇"], "下游层": e["下游层"], "来源": e["来源"], "as_of": e["as_of"]} for e in evid],
        "★A类当日新闻条数(PC1)": news_ct,
        "路1_对6尺持续验证(★动摇置顶)": 路1,
        "路2_对下游维度依据": 路2,
        "★动摇/可能动摇的尺(PDCA入口·置顶)": [{"id": e["id"], "尺": e["对应尺"], "印证动摇": e["印证动摇"], "证据": e["证据"][:50]}
                                             for e in 路1 if "动摇" in e["印证动摇"]],
        "★动摇的尺(PDCA入口·置顶)": [e["对应尺"] for e in 路1 if "动摇" in e["印证动摇"]],
        "NU2_映射不上_候选新维度": unmapped,
        "NU2_建议改尺": sugg,
        "NU5_Drive扫描": {"新件数(text)": len(ext_txt), "json件": len(ext_json), "已映射": mapped_d, "★映射不上": unmap_d, "★来源": "全出自湖水一人·非独立信源(GPT裁定·禁N方独立)"},
        "★禁用语核": "本output不含被禁的『无事件』类结论(NU4)·恒以证据呈现",
    }
    (ROOT / "data/market" / f"evidence_map_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date)
    print("证据总数 %d · output恒非空=%s" % (o["证据总数"], o["★output恒非空"]))
    print("★动摇的尺:", o["★动摇的尺(PDCA入口·置顶)"] or "无")
    print("路1(尺验证·动摇置顶):")
    for e in o["路1_对6尺持续验证(★动摇置顶)"][:6]:
        print("  [%s] %s · %s · %s" % (e["印证动摇"], e["对应尺"], e["强度"], e["证据"][:54]))
    print("NU5 Drive:", o["NU5_Drive扫描"])
    print("映射不上(候选新维度):", len(o["NU2_映射不上_候选新维度"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
