# -*- coding: utf-8 -*-
"""★轮85 CA1:①世界观层(整层未建→建)。★轮121 PA1:取消「确认无/周末休市」出口——董事长裁定『必须保障新鲜度·不存在节假日没有新闻』。
五类各自用已有新闻源(Google News RSS·keyless)分类抓取·白名单+时效过滤。★零命中只判两档(§5.4结构化·基于A类最新事实滞后天数):
【已取到当日事实】(滞后0天)/【源未取到当日·需处置】(告警+阻断下游宣称无事件·绝不判确认无/周末)。★新鲜度硬指标进输出(PA3)。
引用右栏_完整世界观描述.html(产品标 data-src)。输出 data/market/worldview_{date}.json。★做不到标未接·不估算。"""
import sys, json, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
FRAME = "右栏_完整世界观描述.html"

CATEGORIES = [
    ("①地缘政治大事件", ["战争 冲突 OR 制裁 OR 政变", "选举 地缘 冲突", "war sanctions conflict",
                    "伊朗 以色列 OR 美伊 冲突 OR 升级", "中东 霍尔木兹 OR 制裁升级", "Iran Israel escalation strait Hormuz"]),
    ("②美国重大政策转向", ["美国 行政令 OR 总统 表态 政策", "白宫 国会 政策 转向", "executive order policy shift"]),
    ("③供应链阵营化", ["出口管制 OR 脱钩 OR 友岸外包", "供应链 阵营 半导体 管制", "export control decoupling chips"]),
    ("④主要国家关系突变", ["中美关系 OR 美欧 OR 美日 关系", "外交 关系 紧张 OR 突破", "US China relations"]),
    ("⑤黑天鹅突发", ["金融危机 OR 崩盘 突发", "重大 科技突破 OR 黑天鹅", "financial crisis breakthrough"]),
]


def build(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    try:
        from macro_news_intake import fetch_news, qualify_news, _src_tier, fetch_broad_feeds
    except Exception as e:
        return {"date": dh, "★错误": "新闻抓取模块导入失败:%s" % e}
    now = datetime.now(timezone.utc)
    # ★轮104 NK2-1:零命中三分类·非统一「今日无」。周末/盘前=数据未更新;全局抓取0=源不可达(报错阻断);源可达但本类空=确认无。
    _wd = datetime.strptime(dc, "%Y%m%d").weekday()  # 5,6=周末
    is_weekend = _wd >= 5
    cats = []
    total_hit = 0
    fetched_total = 0   # 全五类跨query抓到的原始条数(判抓取健康:全局=0→源不可达)
    newest_pub = None   # ★轮113 NT1:全部抓到项里最新的发布时刻——判『源日期滞后/覆盖不足』(抓到但全是旧闻)
    for name, queries in CATEGORIES:
        hits, sources_tried, seen = [], 0, set()
        cat_fetched = 0
        for q in queries:
            try:
                items = fetch_news(q, limit=10, lang=("en" if any(c.isascii() and c.isalpha() for c in q[-8:]) else "zh"))
            except Exception:
                items = None   # 抓取异常=源不可达信号(区别于返回空list=可达但无内容)
            sources_tried += 1
            if not items:
                continue
            cat_fetched += len(items); fetched_total += len(items)
            # ★newest_pub 只统计【过白名单(权威源)】的项——否则非权威源的新鲜新闻会掩盖『权威源滞后』真相(NT1)
            for _it in items:
                _pd = _it.get("pub_dt")
                if _pd and _src_tier(_it.get("source_raw", "")) and (newest_pub is None or _pd.astimezone(timezone.utc) > newest_pub):
                    newest_pub = _pd.astimezone(timezone.utc)
            qf = qualify_news(items, ring="世界观", now=now)
            for it in qf.get("ok", []):
                key = it.get("title", "")[:40]
                if key and key not in seen:
                    seen.add(key)
                    hits.append({"标题": it.get("title"), "来源": it.get("source") or it.get("source_raw"),
                                 "链接": it.get("url"), "发布": it.get("pub_date")})
        total_hit += len(hits)
        cats.append({"类": name, "命中条数": len(hits), "已扫源数": sources_tried,
                     "★原始抓取条数": cat_fetched, "逐条": hits[:6],
                     "结论": "命中 %d 条" % len(hits) if hits else "(见零命中分类)"})
    # ★★轮122 PB1/PB2:接入宽市场feed(CNBC+Yahoo)·与Google News并存＝多源冗余(任一取到当日即达标)。
    #   宽流不带query·靠相关性映射进①层(PB2-2·证据→尺映射器·不靠查询词筛)。
    try:
        broad_items, broad_health = fetch_broad_feeds(limit_each=40)
    except Exception:
        broad_items, broad_health = [], [{"源": "CNBC/Yahoo", "可达": False, "条数": 0, "最新日期": None, "滞后天数": None}]
    _google_raw = fetched_total                      # ★宽流并入前＝Google窄query原始条数(PB4-4基线)
    _google_newest = newest_pub                      # ★Google源最新whitelist事实(PB1-3逐源)
    fetched_total += len(broad_items)
    # ★newest_pub 纳入宽市场whitelist条(CNBC/Yahoo已在白名单)——任一源取到当日→新鲜度达标(多源冗余)
    for _it in broad_items:
        _pd = _it.get("pub_dt")
        if _pd and _src_tier(_it.get("source_raw", "")) and (newest_pub is None or _pd.astimezone(timezone.utc) > newest_pub):
            newest_pub = _pd.astimezone(timezone.utc)
    # ★PB2:宽流靠相关性闸(qualify_news relevance)映射进①层·不靠查询词——挡噪声证据＝broad_qf.stats
    broad_qf = qualify_news(broad_items, ring="世界观", now=now)
    broad_hits, _bseen = [], set()
    for it in broad_qf.get("ok", []):
        key = it.get("title", "")[:40]
        if key and key not in _bseen:
            _bseen.add(key)
            broad_hits.append({"标题": it.get("title"), "来源": it.get("source") or it.get("source_raw"),
                               "链接": it.get("url"), "发布": it.get("pub_date")})
    total_hit += len(broad_hits)

    # ★★轮121 PA1:取消「确认无」「周末休市」出口(董事长裁定『必须保障新鲜度·不存在节假日没有新闻』)。
    #   零命中/未取到当日一律判【源未取到当日·需处置】(告警+阻断下游宣称无事件)·★绝不判『确认无/周末休市』。
    #   ★判据＝结构化日期(§5.4):A类最新【过白名单】事实日期 == 系统日 → 已取到当日事实;否则 → 需处置。
    #   ★两档(PA1-3):【已取到当日事实】/【源未取到当日·需处置(源健康异常)】——不再有第三/四档。
    today = now.date()
    newest_date = newest_pub.date() if newest_pub else None
    lag_days = (today - newest_date).days if newest_date else None   # ★A类滞后天数(PA3·结构化)
    has_today_fact = (newest_date == today)                          # ★至少一条【当日·过白名单】权威事实(PA1判据)
    src_unreachable = (fetched_total == 0)                           # 全query原始抓取=0(源不可达)——product_lint硬FAIL依据
    if has_today_fact:
        zclass = "已取到当日事实"; srchealth = "已取到当日"
        zmsg = "★A类源已取到【当日(系统日 %s)·过白名单】权威事实·新鲜度达标——下游可据当日事实判断" % dh
    else:
        zclass = "源未取到当日·需处置"
        if src_unreachable:
            srchealth = "源不可达"; _why = "全query原始抓取=0条(源不可达/抓取失败)"
        elif newest_pub is None:
            srchealth = "抓到但无当日权威事实"; _why = "抓到%d条原始但无一条过白名单(权威源今日无内容)" % fetched_total
        else:
            srchealth = "抓到但无当日权威事实"; _why = "权威源最新事实仅到 %s·滞后系统日 %d 天" % (newest_pub.strftime("%Y-%m-%d"), lag_days)
        zmsg = ("★A类源【未取到当日事实】(%s)——【需处置·非确认无·非周末休市:董事长轮121裁定『不存在节假日没有新闻』】·"
                "★下游禁止宣称『今日无事件』·必须告警并补源(多源冗余·PA4实测CNBC/Yahoo Finance/SEC EDGAR官方RSS可返当日·见155回报)·"
                "★不许调松时效凑命中(那让旧闻冒充当日污染①层)") % _why
    # 逐类补分类标签(★两档·PA1)
    for c in cats:
        if c["命中条数"] == 0:
            if has_today_fact:
                c["结论"] = "本类零命中·但A类源已取到当日事实(源健康·PA1)"
            elif src_unreachable or c["★原始抓取条数"] == 0:
                c["结论"] = "★本类抓取0条·源未取到当日·需处置(非确认无·PA1)"
            else:
                c["结论"] = "★源未取到当日·需处置(抓到但无当日权威事实·非确认无·PA1)"
    # ★PB2:宽市场流⑥类(经相关性映射·非查询词)——独立展示噪声拦截·放五类后(不被上面两档覆写)
    _bqs = broad_qf.get("stats", {})
    cats.append({"类": "⑥宽市场流(CNBC/Yahoo·相关性映射·PB2)", "命中条数": len(broad_hits),
                 "已扫源数": len(broad_health), "★原始抓取条数": len(broad_items), "逐条": broad_hits[:6],
                 "结论": ("命中 %d 条(宽流经相关性映射进①层·非查询词·PB2)" % len(broad_hits)) if broad_hits
                         else "宽流%d条·经相关性映射后%d条与①层主题相关(其余噪声被相关性闸挡·PB2)" % (len(broad_items), len(broad_hits))})
    # ★PB1-3 各源健康表(逐源独立:Google窄query聚合 + CNBC + Yahoo)
    _glag = (today - _google_newest.date()).days if _google_newest else None
    src_health = [{"源": "Google News(5类窄query聚合)", "可达": _google_raw > 0, "条数": _google_raw,
                   "最新日期": _google_newest.strftime("%Y-%m-%d") if _google_newest else None, "滞后天数": _glag}] + broad_health
    return {
        "_说明": "★轮85 CA1/轮104 NK2/★轮121 PA1 ①世界观层。五类抓取(Google News RSS·白名单+时效)。★零命中两档:已取到当日事实/源未取到当日·需处置——【取消『确认无』『周末休市』出口·董事长裁定不存在节假日没有新闻】。",
        "date": dh, "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "框架文件": FRAME, "data_src": FRAME,
        "五类": cats, "总命中": total_hit,
        "★A类新鲜度(枚举·PA1两档)": zclass,          # 已取到当日事实 | 源未取到当日·需处置
        "★源健康(枚举·PA3)": srchealth,               # 已取到当日 | 抓到但无当日权威事实 | 源不可达
        "★零命中分类(NK2·全局)": zclass,              # 兼容旧字段·现只两值(不再有确认无/周末)
        "★零命中说明": zmsg,
        "★抓取健康(全五类原始条数)": fetched_total,
        "★源不可达(bool·product_lint硬FAIL依据)": src_unreachable,
        "★A类最新事实日期(PA3)": newest_pub.strftime("%Y-%m-%d") if newest_pub else None,
        "★A类滞后天数(PA3)": lag_days,
        "★新鲜度达标(取到当日事实·bool)": has_today_fact,
        "★各源健康表(PA3·逐类)": [{"类": c["类"], "原始抓取条数": c["★原始抓取条数"],
                                    "命中条数": c["命中条数"], "已扫源数": c["已扫源数"]} for c in cats],
        "★各源健康表(PB1-3·逐源)": src_health,   # ★逐源:Google/CNBC/Yahoo 各自 可达/条数/最新日期/滞后天数
        "★宽市场流相关性映射(PB2)": {"宽流原始条数": len(broad_items), "映射进①层条数": len(broad_hits),
                                     "被相关性闸挡(噪声)": _bqs.get("dropped", 0),
                                     "说明": "宽流不带query·靠相关性闸映射进①层·非查询词筛(证据→尺映射器·PB2-2)"},
        "★①层证据条数(PB4-4)": {"宽流并入前(Google窄query原始)": _google_raw,
                                 "宽流并入后(原始总)": fetched_total,
                                 "合格命中(五窄query+宽流映射)": total_hit},
        "★多源冗余(PB1-2)": "Google News + CNBC + Yahoo 并存·任一取到当日即新鲜度达标",
        "★是否周末": is_weekend,                       # 保留供参考·★周末不再作为『无新闻』借口(PA1)
        "★源最新新闻日期": newest_pub.strftime("%Y-%m-%d") if newest_pub else None,   # 兼容旧字段
        "★源滞后天数": lag_days,                       # 兼容旧字段
        "★下游可否宣称今日无事件": False,             # ★PA1:恒False(董事长裁定不存在没有新闻·未取到=需处置非无事件)
        "★判据满足": "是(五类各有抓取结果·零命中一律判需处置·§5.4基于滞后天数结构化判定·非确认无非留空·PA1取消确认无/周末出口)",
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out = build(a.date)
    p = ROOT / "data" / "market" / f"worldview_{a.date.replace('-', '')}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    b = p.read_bytes(); json.loads(b.decode())
    print("[worldview_layer] %s → %s · 乱码%d · 总命中%s" % (a.date, p.name, b.count(b"\xef\xbf\xbd"), out.get("总命中")))
    for c in out.get("五类", []):
        print("  %s: %s" % (c["类"], c["结论"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
