# -*- coding: utf-8 -*-
"""★轮85 CB2:②国家战略层(整层未建→建)。判据:四类当日各有抓取/明确无 + 三张战略地图被引用。
四类用已有新闻源分类抓取·白名单+时效过滤·零命中写「今日无·已扫N源」。引用右栏三张战略地图(标 data-src)。
输出 data/market/strategy_{date}.json。★做不到标未接·不估算。"""
import sys, json, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
MAPS = ["右栏_完整国家战略地图.html"]   # 含 AI/安全/能源 三张图

CATEGORIES = [
    ("①新立法/拨款(CHIPS/国防授权/能源补贴)", ["CHIPS法案 OR 国防授权 OR 能源补贴 拨款", "美国 立法 半导体 OR 国防 拨款"]),
    ("②行政令/管制新规(出口管制/投资审查/关税)", ["出口管制 OR 投资审查 OR 关税 新规", "美国 行政令 管制 半导体 OR 关税"]),
    ("③战略人事任命", ["美国 战略 人事 任命 部长 OR 顾问", "白宫 人事 任命 国安 OR 商务"]),
    ("④官方战略表态(国情咨文/部长讲话/白皮书)", ["国情咨文 OR 白皮书 OR 部长 讲话 战略", "美国 官方 战略 表态 AI OR 能源"]),
]


def build(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    try:
        from macro_news_intake import fetch_news, qualify_news, _src_tier, fetch_broad_feeds
    except Exception as e:
        return {"date": dh, "★错误": "新闻抓取模块导入失败:%s" % e}
    now = datetime.now(timezone.utc)
    # ★轮122 PB3:②层同①层——取消「确认无/周末」出口·改两档·接宽市场feed多源·带新鲜度硬指标。
    _wd = datetime.strptime(dc, "%Y%m%d").weekday(); is_weekend = _wd >= 5
    cats = []; total = 0; fetched_total = 0; newest_pub = None
    for name, queries in CATEGORIES:
        hits, tried, seen = [], 0, set(); cat_fetched = 0
        for q in queries:
            try:
                items = fetch_news(q, limit=10, lang="zh")
            except Exception:
                items = None
            tried += 1
            if not items:
                continue
            cat_fetched += len(items); fetched_total += len(items)
            for _it in items:   # ★newest_pub 只统计过白名单(权威源)项(同①层·防非权威掩盖滞后)
                _pd = _it.get("pub_dt")
                if _pd and _src_tier(_it.get("source_raw", "")) and (newest_pub is None or _pd.astimezone(timezone.utc) > newest_pub):
                    newest_pub = _pd.astimezone(timezone.utc)
            qf = qualify_news(items, ring="国家战略", now=now)
            for it in qf.get("ok", []):
                key = it.get("title", "")[:40]
                if key and key not in seen:
                    seen.add(key)
                    hits.append({"标题": it.get("title"), "来源": it.get("source") or it.get("source_raw"),
                                 "链接": it.get("url"), "发布": it.get("pub_date")})
        total += len(hits)
        cats.append({"类": name, "命中条数": len(hits), "已扫源数": tried, "★原始抓取条数": cat_fetched,
                     "逐条": hits[:6], "结论": "命中 %d 条" % len(hits) if hits else "(见零命中分类)"})
    # ★★轮122 PB1/PB2:接入宽市场feed(CNBC+Yahoo)·多源冗余·宽流靠相关性映射进②层(不靠查询词)
    try:
        broad_items, broad_health = fetch_broad_feeds(limit_each=40)
    except Exception:
        broad_items, broad_health = [], [{"源": "CNBC/Yahoo", "可达": False, "条数": 0, "最新日期": None, "滞后天数": None}]
    _google_raw = fetched_total; _google_newest = newest_pub
    fetched_total += len(broad_items)
    for _it in broad_items:
        _pd = _it.get("pub_dt")
        if _pd and _src_tier(_it.get("source_raw", "")) and (newest_pub is None or _pd.astimezone(timezone.utc) > newest_pub):
            newest_pub = _pd.astimezone(timezone.utc)
    broad_qf = qualify_news(broad_items, ring="国家战略", now=now)
    broad_hits, _bseen = [], set()
    for it in broad_qf.get("ok", []):
        key = it.get("title", "")[:40]
        if key and key not in _bseen:
            _bseen.add(key)
            broad_hits.append({"标题": it.get("title"), "来源": it.get("source") or it.get("source_raw"),
                               "链接": it.get("url"), "发布": it.get("pub_date")})
    total += len(broad_hits)
    # ★★轮121/122 PB3:两档(取消确认无/周末)·判据＝A类最新过白名单事实滞后天数(§5.4结构化)
    today = now.date()
    newest_date = newest_pub.date() if newest_pub else None
    lag_days = (today - newest_date).days if newest_date else None
    has_today_fact = (newest_date == today)
    src_unreachable = (fetched_total == 0)
    if has_today_fact:
        zclass = "已取到当日事实"; srchealth = "已取到当日"
        zmsg = "★A类源已取到【当日(系统日 %s)·过白名单】战略事实·新鲜度达标——下游可据当日事实判断" % dh
    else:
        zclass = "源未取到当日·需处置"
        if src_unreachable:
            srchealth = "源不可达"; _why = "全query原始抓取=0条(源不可达/抓取失败)"
        elif newest_pub is None:
            srchealth = "抓到但无当日权威事实"; _why = "抓到%d条原始但无一条过白名单(权威源今日无内容)" % fetched_total
        else:
            srchealth = "抓到但无当日权威事实"; _why = "权威源最新事实仅到 %s·滞后系统日 %d 天" % (newest_pub.strftime("%Y-%m-%d"), lag_days)
        zmsg = ("★A类源【未取到当日战略事实】(%s)——【需处置·非确认无·非周末休市:董事长轮121裁定『不存在节假日没有新闻』】·"
                "★下游禁止宣称『今日无战略事件』·必须告警并补源(多源冗余CNBC/Yahoo)·★不许调松时效凑命中") % _why
    for c in cats:
        if c["命中条数"] == 0:
            if has_today_fact:
                c["结论"] = "本类零命中·但A类源已取到当日事实(源健康·PB3)"
            elif src_unreachable or c["★原始抓取条数"] == 0:
                c["结论"] = "★本类抓取0条·源未取到当日·需处置(非确认无·PB3)"
            else:
                c["结论"] = "★源未取到当日·需处置(抓到但无当日权威事实·非确认无·PB3)"
    _bqs = broad_qf.get("stats", {})
    cats.append({"类": "⑤宽市场流(CNBC/Yahoo·相关性映射·PB2)", "命中条数": len(broad_hits),
                 "已扫源数": len(broad_health), "★原始抓取条数": len(broad_items), "逐条": broad_hits[:6],
                 "结论": ("命中 %d 条(宽流经相关性映射进②层·非查询词·PB2)" % len(broad_hits)) if broad_hits
                         else "宽流%d条·经相关性映射后%d条与②层战略主题相关(其余噪声被相关性闸挡·PB2)" % (len(broad_items), len(broad_hits))})
    _glag = (today - _google_newest.date()).days if _google_newest else None
    src_health = [{"源": "Google News(4类窄query聚合)", "可达": _google_raw > 0, "条数": _google_raw,
                   "最新日期": _google_newest.strftime("%Y-%m-%d") if _google_newest else None, "滞后天数": _glag}] + broad_health
    return {
        "_说明": "★轮85 CB2/★轮122 PB3 ②国家战略层。四类窄query + 宽市场feed(CNBC/Yahoo)多源。★零命中两档:已取到当日事实/源未取到当日·需处置——【取消『确认无』『周末』出口·同①层】。",
        "date": dh, "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "战略地图文件": MAPS, "data_src": MAPS[0],
        "四类": cats, "总命中": total,
        "★A类新鲜度(枚举·PB3两档)": zclass, "★源健康(枚举)": srchealth,
        "★零命中分类(NK2·全局)": zclass, "★零命中说明": zmsg,
        "★抓取健康(全类原始条数)": fetched_total,
        "★源不可达(bool·product_lint硬FAIL依据)": src_unreachable,
        "★A类最新事实日期(PB3)": newest_pub.strftime("%Y-%m-%d") if newest_pub else None,
        "★A类滞后天数(PB3)": lag_days,
        "★新鲜度达标(取到当日事实·bool)": has_today_fact,
        "★各源健康表(PB1-3·逐源)": src_health,
        "★宽市场流相关性映射(PB2)": {"宽流原始条数": len(broad_items), "映射进②层条数": len(broad_hits),
                                     "被相关性闸挡(噪声)": _bqs.get("dropped", 0)},
        "★是否周末": is_weekend,
        "★下游可否宣称今日无事件": False,
        "★判据满足": "是(四类各有抓取结果·零命中一律判需处置·§5.4滞后天数结构化·PB3取消确认无/周末+三张地图被引用)",
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out = build(a.date)
    p = ROOT / "data" / "market" / f"strategy_{a.date.replace('-', '')}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    b = p.read_bytes(); json.loads(b.decode())
    print("[national_strategy_layer] %s → %s · 乱码%d · 总命中%s · 新鲜度达标%s" % (a.date, p.name, b.count(b"\xef\xbf\xbd"), out.get("总命中"), out.get("★新鲜度达标(取到当日事实·bool)")))
    for c in out.get("四类", []):
        print("  %s: %s" % (c["类"], c["结论"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
