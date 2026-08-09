# -*- coding: utf-8 -*-
"""完整产品·左右栏合一（D1）· Opus 5 2026-08-08 写
用法：python scripts/full_product_lr.py --date 20260808

七层，每层左右并排：
  左栏＝今天的判断与数据（动态·读当日 data/*.json）
  右栏＝该层完整底子/尺（静态·原文并入 00_请先看这里/右栏_*.html 等）

铁律：
  ★右栏原文并入·不摘要·不改写（那是尺）
  ★左栏缺件如实标「未填/未产出·原因」·不静默省略·不占位
  ★元数据(date/岗位/签发/交付时刻/data_date/_说明)不作章节标题
  ★不截断任何判断正文
"""
import sys, os, json, re, argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
ZHENG = ROOT / "00_请先看这里"

# 元数据键：不作章节标题（董事长两次指出）
META_KEYS = {"date", "data_date", "岗位", "签发", "交付时刻", "version", "立于", "维护人"}


def rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def extract_body(path):
    """抽 <body> 内正文，去掉该文件自己的 head/style/script/页头横幅。失败→None。"""
    p = Path(path)
    if not p.exists():
        return None
    try:
        raw = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    m = re.search(r"<body[^>]*>(.*)</body>", raw, re.S | re.I)
    body = m.group(1) if m else raw
    body = re.sub(r"<script.*?</script>", "", body, flags=re.S | re.I)
    body = re.sub(r"<style.*?</style>", "", body, flags=re.S | re.I)
    # 去掉源文件自己的 <h1>（避免与本产品层标题打架），保留 h2/h3
    body = re.sub(r"<h1[^>]*>.*?</h1>", "", body, flags=re.S | re.I)
    return body.strip()


def right_col(sources):
    """右栏：逐个源文件原文并入。缺失→如实标，不留空、不用别层顶替。"""
    out = []
    for label, rel in sources:
        b = extract_body(ZHENG / rel)
        if b is None:
            out.append('<div class="miss">★本块底子缺失·源文件未找到：<code>%s</code>'
                       '（不留空、不用别层内容顶替）</div>' % esc(rel))
            continue
        out.append('<details open><summary>%s　<span class="src">源：%s</span></summary>'
                   '<div class="rbody">%s</div></details>' % (esc(label), esc(rel), b))
    return "\n".join(out) if out else '<div class="miss">★本层无右栏源文件登记</div>'


def render_val(v, depth=0):
    """把 JSON 判断内容渲染成正文。★不截断。★元数据键不作标题。"""
    if v is None:
        return '<div class="miss">★未填</div>'
    if isinstance(v, str):
        return "<p>%s</p>" % esc(v)
    if isinstance(v, (int, float, bool)):
        return "<p>%s</p>" % esc(v)
    if isinstance(v, list):
        return "<ul>" + "".join("<li>%s</li>" % render_val(x, depth + 1) for x in v) + "</ul>"
    if isinstance(v, dict):
        parts = []
        for k, val in v.items():
            ks = str(k)
            if ks.startswith("_") or ks in META_KEYS:
                continue                      # ★元数据不作标题
            tag = "h4" if depth == 0 else "b"
            if tag == "h4":
                parts.append("<h4>%s</h4>%s" % (esc(ks), render_val(val, depth + 1)))
            else:
                parts.append('<div class="kv"><b>%s</b>：%s</div>' % (esc(ks), render_val(val, depth + 1)))
        return "".join(parts) if parts else '<div class="miss">★本节无可显示内容</div>'
    return "<p>%s</p>" % esc(v)


def sec(title, body):
    return '<div class="lsec"><div class="lsec-t">%s</div>%s</div>' % (esc(title), body)


def miss(what, why):
    return '<div class="miss">★%s·未产出<br><span class="why">原因：%s</span></div>' % (esc(what), esc(why))


# ───────────── 左栏各层 ─────────────
def L_world(dc, dh, content, slots):
    out = []
    wv = rj(ROOT / "data/market" / f"worldview_{dc}.json")
    out.append(sec("今日判断", render_val((content or {}).get("一_今天发生了什么"))
                   if content else miss("当日正文", "opus5_content 未交")))
    if wv:
        out.append(sec("机器观测", render_val(wv)))
    else:
        out.append(miss("世界观层数据", f"worldview_{dc}.json 不存在"))
    ev = (slots or {}).get("①层证据台账(带ID·供引用)")
    if ev:
        out.append(sec("今日证据（带来源与新鲜度）", render_val(ev)))
    return "".join(out)


def L_strategy(dc, dh, content, slots):
    st = rj(ROOT / "data/market" / f"strategy_{dc}.json")
    s2 = ((slots or {}).get("②~⑦层判断工单") or {}).get("②国家战略") or (slots or {}).get("②国家战略")
    out = [sec("今日判断", render_val(s2) if s2 else miss("②层判断", "judgment_slots 未填"))]
    out.append(sec("机器观测", render_val(st)) if st else miss("战略层数据", f"strategy_{dc}.json 不存在"))
    return "".join(out)


def L_flow(dc, dh, content, slots):
    out = []
    s3 = ((slots or {}).get("②~⑦层判断工单") or {}).get("③资金流动") or (slots or {}).get("③资金流动")
    out.append(sec("今日判断", render_val(s3) if s3 else miss("③层判断", "judgment_slots 未填")))
    if content and content.get("★一之二_资金流动层"):
        out.append(sec("正文·资金流动层", render_val(content["★一之二_资金流动层"])))
    mf = rj(ROOT / "data/market" / f"macro_flow_{dc}.json")
    out.append(sec("机器观测", render_val(mf)) if mf else miss("宏观数据", f"macro_flow_{dc}.json 不存在"))
    return "".join(out)


def L_sector(dc, dh, content, slots):
    out = []
    ss = rj(ROOT / "data/market" / f"sector_strength_{dh}.json")
    if ss and ss.get("produced"):
        rows = ss.get("18格强度(按5日相对强度降序)") or []
        t = ['<table><tr><th>格</th><th>5日相对</th><th>20日相对</th><th>60日相对</th>'
             '<th>轮动5-20</th><th>成分股</th><th>状态</th></tr>']
        for r in rows:
            def f(x):
                if x is None:
                    return '<span class="na">无数据</span>'
                c = "pos" if x > 0 else ("neg" if x < 0 else "")
                return '<span class="%s">%+.2f</span>' % (c, x)
            t.append("<tr><td>%s %s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
                     "<td>%s</td><td>%s</td></tr>" % (
                         esc(r.get("格号") if r.get("格号") is not None else "—"),
                         esc(r.get("格名")), f(r.get("5日相对强度")), f(r.get("20日相对强度")),
                         f(r.get("60日相对强度")), f(r.get("轮动方向(5-20·短期获\\失动能)")),
                         esc(r.get("成分股数")), esc(r.get("当前激活状态"))))
        t.append("</table>")
        out.append(sec("18格强度全表（相对强度＝该格涨跌−大盘涨跌；美股比^GSPC·日股比^N225）", "".join(t)))
        out.append(sec("计算口径", render_val(ss.get("★计算元数据(R3·GPT必核)"))))
    else:
        out.append(miss("板块强度", (ss or {}).get("reason", f"sector_strength_{dh}.json 不存在或未产出")))
    s4 = ((slots or {}).get("②~⑦层判断工单") or {}).get("④板块轮动") or (slots or {}).get("④板块轮动")
    if s4:
        out.append(sec("今日判断", render_val(s4)))
    return "".join(out)


def L_pool(dc, dh, content, slots):
    out = []
    cp = rj(ROOT / "data/opportunity" / f"candidate_pool_{dh}.json") or \
         rj(ROOT / "data/opportunities" / f"opportunity_gated_{dc}.json")
    n = len(((cp or {}).get("candidates")) or [])
    if n == 0:
        out.append('<div class="zero">今日股票类候选 ＝ <b>0</b><br>'
                   '<span class="why">★按尺要求，候选为 0 必须写明卡在第几关、为什么——见下方判断</span></div>')
    else:
        out.append(sec("候选逐只", render_val((cp or {}).get("candidates"))))
    s5 = ((slots or {}).get("②~⑦层判断工单") or {}).get("⑤机会池") or (slots or {}).get("⑤机会池")
    out.append(sec("今日判断（卡在哪一关）", render_val(s5) if s5 else miss("⑤层判断", "judgment_slots 未填")))
    if content and content.get("四_今天做什么"):
        out.append(sec("正文·今天做什么", render_val(content["四_今天做什么"])))
    return "".join(out)


def L_hold(dc, dh, content, slots):
    out = []
    tg = rj(ROOT / "data/target" / f"target_gap_{dc}.json")
    if tg:
        for acct in ("富途", "SBI"):
            a = tg.get(acct)
            if not isinstance(a, dict):
                continue
            hd = ['<div class="acct">%s　总资产 $%s　｜　股票 $%s　｜　现金 $%s</div>' % (
                esc(acct), esc(round(a.get("当日总资产A_USD") or 0, 2)),
                esc(round(a.get("股票市值_USD") or 0, 2)), esc(round(a.get("现金_USD") or 0, 2)))]
            hd.append('<table><tr><th>代码</th><th>名称</th><th>股数</th><th>现价</th>'
                      '<th>市值USD</th><th>权重</th><th>预测上行</th><th>贡献pp</th><th>盲区</th></tr>')
            for h in a.get("逐只(按贡献pp降序)", []):
                up = h.get("E上行_pct_新口径")
                cb = h.get("贡献pp_新口径")
                cls = "neg" if (cb is not None and cb < 0) else ("pos" if cb else "")
                hd.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>"
                          "<td>%s</td><td>%s</td><td class='%s'>%s</td><td>%s</td></tr>" % (
                              esc(h.get("code")), esc(h.get("name")), esc(h.get("qty")),
                              esc(h.get("price_local_0730") or h.get("price_local")),
                              esc(round(h.get("market_value_usd") or 0, 2)),
                              esc("%.2f%%" % ((h.get("权重_新口径") or 0) * 100)),
                              esc("%.2f%%" % up if up is not None else "—"),
                              cls, esc(cb if cb is not None else "—"),
                              "★是" if h.get("blind") else ""))
            hd.append("</table>")
            sc = (tg.get("★组合三情景收益率(三·轮52)") or {}).get(acct)
            if sc:
                hd.append('<div class="scen">最好 %s%%　｜　概率加权期望 <b>%s%%</b>　｜　最坏 %s%%　'
                          '｜　距 +40%% 还差 <b>%s</b></div>' % (
                              esc(sc.get("S1收益率pct")), esc(sc.get("概率加权合计pct")),
                              esc(sc.get("S3收益率pct")), esc(sc.get("③概率加权期望·距+40%"))))
            out.append(sec("账户 · %s" % acct, "".join(hd)))
    else:
        out.append(miss("持仓与目标缺口", f"target_gap_{dc}.json 不存在"))
    dr = rj(ROOT / "data/risk" / f"defensive_ratio_{dh}.json")
    out.append(sec("防御仓", render_val(dr)) if dr else
               miss("防御仓占比", f"defensive_ratio_{dh}.json 未生成（不用旧数冒充今天）"))
    if content and content.get("三_逐只判断"):
        out.append(sec("正文·逐只判断", render_val(content["三_逐只判断"])))
    return "".join(out)


def L_pdca(dc, dh, content, slots):
    out = []
    sc = rj(ROOT / "data/pdca" / f"scorecard_summary_{dc}.json")
    out.append(sec("记分卡", render_val(sc)) if sc else miss("记分卡", f"scorecard_summary_{dc}.json 不存在"))
    rv = rj(ROOT / "data/pdca" / f"pdca_review_{dc}.json")
    if rv:
        out.append(sec("复盘", render_val(rv)))
    if content and content.get("五_这台机器今天的状态"):
        out.append(sec("正文·今日错误与更正", render_val(content["五_这台机器今天的状态"])))
    return "".join(out)


def L_base(dc, dh, content, slots):
    """底层地基·佐证输入（云盘料）——★《生产流程规范》第6节步骤①「刷数据(…云盘料)」要求的一环。
    ★★此前 full_product 未含本层，导致老雷/湖水/TXT 的更新在产品里看不到。"""
    out = []
    nm = rj(ROOT / "data/inbox" / f"new_materials_{dc}.json")
    if nm:
        rows = ['<table><tr><th>来源</th><th>最新一份</th><th>距今</th><th>断流</th></tr>']
        for k, v in (nm.get("各类最新与断流") or {}).items():
            days = v.get("距今天数")
            cls = "neg" if v.get("★断流") else ("warn" if (days or 0) >= 10 else "pos")
            rows.append("<tr><td><b>%s</b></td><td>%s</td><td class='%s'>%s 天</td><td>%s</td></tr>"
                        % (esc(k), esc(v.get("最新一份")), cls, esc(days), esc(v.get("断流告警"))))
        rows.append("</table>")
        rows.append('<div class="kv">扫描路径：%s</div>' % esc("　｜　".join(nm.get("扫描路径") or [])))
        rows.append('<div class="kv">文件总数：<b>%s</b>　｜　扫描时刻：%s</div>'
                    % (esc(nm.get("文件总数")), esc(nm.get("as_of"))))
        out.append(sec("云盘料·更新与断流（老雷／湖水／inbox）", "".join(rows)))
        lst = nm.get("清单") or []
        if lst:
            recent = lst[:15]
            ul = "<ul>" + "".join(
                "<li>%s　<b>%s</b>　%s　<span class='src'>%s</span></li>"
                % (esc(x.get("日期")), esc(x.get("类别")), esc(x.get("文件")), esc(x.get("可读性")))
                for x in recent) + "</ul>"
            out.append(sec("最近入库（前 15 份·共 %d 份）" % len(lst), ul))
    else:
        out.append(miss("云盘料扫描", f"data/inbox/new_materials_{dc}.json 不存在"))

    # ★未消化＝提取成功但未被任何判断引用（机器每天在报·此前只印在提醒里）
    ds = rj(ROOT / "data/external" / f"digest_status_{dc}.json") or \
         rj(ROOT / "data/external" / f"digest_status_{(int(dc)-1)}.json")
    if ds:
        out.append(sec("★外部资料消化状态（提取成功但未被任何判断引用＝我没读）", render_val(ds)))
    idx = rj(ROOT / "data/external/text" / f"_index_{dc}.json")
    if idx:
        out.append(sec("已提取文本索引", render_val(idx)))
    if not ds and not idx:
        out.append(miss("外部资料消化状态", "digest_status / text 索引均未找到"))
    return "".join(out)


LAYERS = [
    ("⓪", "底层地基 · 佐证输入（云盘料）", "老雷／湖水／TXT 有没有更新·有没有被读进判断", L_base,
     [("蓝图·底层地基两类文件", "蓝图内容总清单_V1.html"),
      ("生产流程规范（步骤①含『云盘料』）", "生产流程规范_主控_生产二字触发.html")]),
    ("①", "世界观层", "世界底层变没变", L_world,
     [("完整世界观描述", "右栏_完整世界观描述.html")]),
    ("②", "国家战略层", "钱往 AI / 安全 / 能源 哪个方向", L_strategy,
     [("完整国家战略地图", "右栏_完整国家战略地图.html")]),
    ("③", "资金流动层", "钱怎么流 · 总闸美联储", L_flow,
     [("资金流动完整机制", "右栏_资金流动完整机制.html"),
      ("判定标准表 v1", "正式尺_资金流动层判定标准表_v1_20260802.html")]),
    ("④", "板块轮动层", "钱落到哪些板块", L_sector,
     [("板块地图", "右栏_板块地图.html")]),
    ("⑤", "机会池 / 筛选层", "筛出什么值得看", L_pool,
     [("过滤标准筛选规则（第1~5关）", "右栏_过滤标准筛选规则.html"),
      ("护城河分析框架（第4关）", "护城河分析框架.html"),
      ("估值方法学（第3关）", "右栏_估值方法学.html"),
      ("估值方法学·增补两把尺", "右栏_估值方法学_增补_两把尺.html")]),
    ("⑥", "持仓层", "你手里的怎么办", L_hold,
     [("持仓完整档案", "右栏_持仓完整档案.html")]),
    ("⑦", "复盘 / 记分卡层", "PDCA · 确定性累积（系统的魂）", L_pdca,
     [("复盘记分卡层完整设计", "⑦复盘记分卡层_完整设计.html"),
      ("正式尺·复盘记分卡层设计 v1", "正式尺_复盘记分卡层设计_v1_20260802.html"),
      ("PDCA 记分规则准绳", "PDCA记分规则准绳.html")]),
]

CSS = """
body{font-family:"Microsoft YaHei","PingFang SC",sans-serif;margin:0;padding:18px;background:#f2f4f7;color:#1a1a1a;line-height:1.85;font-size:16px}
.wrap{max-width:1680px;margin:0 auto}
.banner{background:#12324e;color:#fff;border-radius:10px;padding:18px 22px;margin-bottom:14px}
.banner .big{font-size:27px;font-weight:800}
.banner .sub{font-size:14px;margin-top:6px;opacity:.93}
.redbar{background:#7B241C;color:#fff;border-radius:8px;padding:12px 18px;margin:10px 0;font-size:15px}
.nav{background:#fff;border:1px solid #ccd;border-radius:8px;padding:10px 16px;margin:10px 0;font-size:14px}
.nav a{margin-right:14px;color:#12324e;text-decoration:none;font-weight:700}
.layer{background:#fff;border:1px solid #c9d2dc;border-radius:10px;margin:18px 0;overflow:hidden}
.lhead{background:#12324e;color:#fff;padding:11px 18px}
.lhead .n{font-size:21px;font-weight:800}
.lhead .d{font-size:13px;opacity:.9}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:0}
@media(max-width:1100px){.cols{grid-template-columns:1fr}}
.cl,.cr{padding:14px 18px}
.cl{border-right:2px solid #dde3ea}
.ct{font-weight:800;font-size:15px;padding:6px 10px;border-radius:5px;margin-bottom:10px;display:inline-block}
.ct-l{background:#e3f0ff;color:#12324e}
.ct-r{background:#fdf2dd;color:#7a5a00}
.lsec{margin:12px 0;border-left:4px solid #4a7ba7;padding-left:12px}
.lsec-t{font-weight:800;color:#12324e;margin-bottom:5px}
h4{margin:10px 0 4px;color:#12324e;font-size:15.5px}
.kv{margin:4px 0}
table{border-collapse:collapse;width:100%;margin:8px 0;font-size:13.5px;background:#fff}
th{background:#12324e;color:#fff;padding:7px 6px;text-align:left}
td{border-bottom:1px solid #e0e0e0;padding:6px}
.pos{color:#1a7a3a;font-weight:700}.neg{color:#a02020;font-weight:700}.na{color:#999}
.warn{color:#a67c00;font-weight:700}
.miss{background:#fdecea;border-left:4px solid #c0392b;padding:8px 12px;margin:8px 0;border-radius:4px;font-size:14px}
.why{color:#7a2020;font-size:13px}
.zero{background:#fff3cd;border:2px solid #e6a700;border-radius:6px;padding:10px 14px;margin:8px 0}
.acct{font-weight:800;color:#12324e;margin:6px 0}
.scen{background:#eef7ff;border:1px solid #2c6e9a;border-radius:6px;padding:8px 12px;margin:6px 0;font-size:14px}
details{background:#fffdf7;border:1px solid #e3d5aa;border-radius:6px;padding:8px 12px;margin:8px 0}
summary{cursor:pointer;font-weight:800;color:#7a5a00}
.src{font-weight:400;font-size:12px;color:#998}
.rbody{margin-top:8px;font-size:14px;max-height:none}
.rbody h2{font-size:16px;color:#7a5a00;border-left:4px solid #c9a227;padding-left:8px}
.rbody h3{font-size:15px;color:#7a5a00}
.rbody table{font-size:12.5px}
"""


def build(date):
    dc = date.replace("-", "")
    dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    content = rj(ROOT / "data/content" / f"opus5_content_{dc}.json")
    slots = rj(ROOT / "data/pipeline" / f"judgment_slots_{dc}.json")
    now = datetime.now(JST)
    wd = "一二三四五六日"[datetime.strptime(dh, "%Y-%m-%d").weekday()]

    miss_list = []
    if not content:
        miss_list.append("当日正文 opus5_content_%s.json 未交 → 各层判断将大面积缺失" % dc)
    if not slots:
        miss_list.append("judgment_slots_%s.json 不存在 → ②~⑦层判断无来源" % dc)

    nav = " ".join('<a href="#L%s">%s%s</a>' % (i, n, nm)
                   for i, (n, nm, _, _, _) in enumerate(LAYERS))

    parts = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">',
             '<title>完整产品·左右栏合一·%s</title><style>%s</style></head><body><div class="wrap">' % (dh, CSS),
             '<div class="banner"><div class="big">完整产品 · 左右栏合一 · %s（周%s）</div>'
             '<div class="sub">左栏＝今天的判断与数据　｜　右栏＝该层完整底子（尺·原文并入·未摘要）</div>'
             '<div class="sub">生成 %s ｜ 七层：世界观 → 国家战略 → 资金流动 → 板块轮动 → 机会池 → 持仓 → 复盘记分卡</div></div>'
             % (dh, wd, now.strftime("%Y-%m-%d %H:%M JST"))]

    if miss_list:
        parts.append('<div class="redbar"><b>★本册缺件（如实列出·不静默省略）</b><ul>' +
                     "".join("<li>%s</li>" % esc(x) for x in miss_list) + "</ul></div>")

    parts.append('<div class="nav">跳转：%s</div>' % nav)

    for i, (n, nm, desc, lf, rsrc) in enumerate(LAYERS):
        try:
            left = lf(dc, dh, content, slots)
        except Exception as e:
            left = miss("本层左栏渲染失败", "%s: %s" % (type(e).__name__, e))
        parts.append(
            '<div class="layer" id="L%s"><div class="lhead"><span class="n">%s %s</span>'
            '<span class="d">　—　%s</span></div><div class="cols">'
            '<div class="cl"><div class="ct ct-l">左栏 · 今天</div>%s</div>'
            '<div class="cr"><div class="ct ct-r">右栏 · 完整底子（尺）</div>%s</div>'
            '</div></div>' % (i, n, esc(nm), esc(desc), left, right_col(rsrc)))

    parts.append('</div></body></html>')
    return "".join(parts)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    dc = a.date.replace("-", "")
    dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    html = build(a.date)
    out = ZHENG / f"★完整产品_{dh}_左右栏合一.html"
    out.write_text(html, encoding="utf-8")
    b = out.read_bytes()
    print("[完整产品·左右栏] %s · %d KB · 乱码%d · → %s" % (
        dh, len(b) // 1024, b.count(b"\xef\xbf\xbd"), out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
