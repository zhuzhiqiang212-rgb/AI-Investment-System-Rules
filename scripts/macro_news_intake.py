from __future__ import annotations

"""第二块 · 宏观事件 + 主题新闻源（让"待第二块"三环也机器自动评）

机器自动抓当日宏观事件真值(经济日历)与主题新闻，喂进规则引擎，把 evidence_autobuild
里现在标"待第二块"的三环（世界观级 / 战略产业面 / 手段层）变成机器自动评。

诚实边界（总则第九条四、第十三条二）：机器【抓不到】真源 → 如实标"待接真源"、读上一
状态、绝不编造。先接一个能用的源跑通一环，再逐环加。

可用真源（机器侧·无需密钥）：
- 主题新闻：Google News RSS（keyless）→ 战略产业面 / 手段层 / 世界观级
- 经济日历：FRED fredgraph.csv（keyless）→ 总闸(非农/CPI/Fed 真值)；本网络下超时则标"待接真源"

用法：
  python scripts/macro_news_intake.py --date 20260711        # 独立跑：读回 daily_ 写回三环
  evidence_autobuild.py --with-macro-news                      # 由第一块调用 enrich_links()
"""

import argparse
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "Mozilla/5.0 (compatible; macro_news_intake/1.0)"}
TIMEOUT = 12

# ══ 新闻层整改(董事局工单 2026-07-16)：源白名单 + 时效 + 中文源 + 加权研判 ══
# ① 源白名单：只取权威财经/官方。名单外一律剔除(大学活动页/内容农场/智库博客/零售App博客)
SOURCE_WHITELIST = {
    # 国际权威
    "reuters": "路透", "路透": "路透", "路透社": "路透",
    "bloomberg": "彭博", "彭博": "彭博", "彭博社": "彭博",
    "cnbc": "CNBC",
    "wall street journal": "WSJ", "wsj": "WSJ", "华尔街日报": "WSJ",
    "financial times": "FT", "ft中文网": "FT", "金融时报": "FT",
    # 官方
    "federal reserve": "美联储官方", "美联储": "美联储官方", "sec": "SEC官方",
    "u.s. department of the treasury": "美财政部官方", "white house": "白宫官方",
    "nvidia": "公司官方", "官方": "官方",
    # 中文主流财经(2026-07-16 放宽：原名单过窄→把登真新闻的大站全挡了·假报"今日无重大新闻")
    "caixin": "财新", "财新": "财新", "财新网": "财新",
    "华尔街见闻": "华尔街见闻", "wallstreetcn": "华尔街见闻",
    "第一财经": "第一财经", "yicai": "第一财经",
    "证券时报": "证券时报", "stcn": "证券时报",
    "新浪财经": "新浪财经", "sina": "新浪财经",
    "东方财富": "东方财富", "eastmoney": "东方财富",
    "澎湃": "澎湃新闻", "thepaper": "澎湃新闻",
    "界面": "界面新闻", "jiemian": "界面新闻",
    "21财经": "21财经", "21世纪经济报道": "21财经",
    # 乙3：世界观级(地缘/秩序/大国政治)的真新闻不登财经站，登国际新闻通讯社。
    # 原白名单只有财经媒体→世界观层天天0条、假报"今日无重大地缘新闻"。
    "rfi": "RFI法广", "法广": "RFI法广",
    "美国之音": "美国之音", "voa": "美国之音",
    "bbc": "BBC", "德国之声": "德国之声", "dw": "德国之声",
    "associated press": "美联社", "ap news": "美联社", "美联社": "美联社",
    "agence france": "法新社", "法新社": "法新社", "afp": "法新社",
    "nikkei": "日经", "日经": "日经", "共同社": "共同社", "kyodo": "共同社",
    "新华社": "新华社", "xinhua": "新华社", "中新社": "中新社", "环球时报": "环球时报",
}
# 明确剔除模式(大学活动页/智库博客/内容农场/零售App博客/论坛)——只挡这些，不挡大站
SOURCE_BLOCK_PAT = re.compile(
    r"(university|college|\.edu|speaker series|think ?change|\bodi\b|institute|智库|"
    r"eciks|pluang|medium\.com|substack|wiki|forum|reddit|论坛|贴吧)", re.I)

# 重要性按【内容】判(不光按域名)：命中即属重大，白名单外的大站也不许剔到0
IMPORTANT_PAT = re.compile(
    r"(法案|参议院|众议院|国会|监管|新规|加息|降息|议息|美联储|央行|关税|制裁|出口管制|"
    r"财报|业绩|指引|营收|净利|并购|收购|上市|IPO|代币化|稳定币|禁令|裁决|判决|"
    r"act\b|senate|congress|regulat|tariff|sanction|earnings|guidance|merger|acquisition|"
    r"rate (cut|hike)|fed\b|sec\b|ruling|ban\b|tokeniz)", re.I)

# ② 时效：只取最近 N 小时内发布的新闻(旧闻不许挂"今天怎么了")
MAX_AGE_HOURS = 36

# ③ 中文源优先：用中文查询+zh-CN feed → 标题原生中文(结构性解决"全英文没翻")
QUERIES = {
    "strategy": "英伟达 台积电 AI 芯片 财报 需求 指引",
    "means": "稳定币 加密 监管 银行",
    # 乙3：世界一天不可能"无事件"——世界观级本就该覆盖 地缘/秩序/大国政治/央行/战争/制裁/选举/贸易。
    # ⚠必须用 OR：Google News 空格=AND，堆9个词会 AND 到 0 条(实测)→反而假报"无事件"。
    "world": "地缘 OR 关税 OR 制裁 OR 战争 OR 央行 OR 选举 OR 贸易战 OR 国际秩序 OR 峰会",
}
QUERIES_EN_FALLBACK = {
    "strategy": "AI semiconductor earnings guidance Nvidia TSMC demand",
    "means": "stablecoin regulation crypto bank",
    "world": "geopolitics OR tariff OR sanctions OR war OR \"central bank\" OR election OR summit",
}

# ④ 加权研判信号表(带否定词处理·非机械计数；每条命中须过相关性闸)
STRAT_BULL = ["创纪录", "超预期", "上修", "强劲", "大涨", "订单激增", "产能吃紧", "上调指引",
              "record", "beat", "raise", "robust", "strong", "surge", "upgrade", "boom"]
STRAT_BEAR = ["不及预期", "下修", "疲软", "抛售", "砍单", "过剩", "降价", "下调指引", "减产",
              "miss", "cut", "slowdown", "selloff", "downgrade", "glut", "oversupply", "warn", "weak"]
MEANS_POS = ["获批", "落地", "扩张", "牌照", "合作", "发行", "纳入", "approval", "approved",
             "license", "launch", "adopt", "partnership", "expand"]
MEANS_NEG = ["禁", "打击", "收紧", "推迟", "驳回", "诉讼", "罚", "ban", "crackdown", "restrict",
             "delay", "reject", "lawsuit", "fraud"]
WORLD_REGIME = ["战争", "入侵", "制裁", "关税", "联盟", "脱钩", "核", "政变", "禁运",
                "war", "invasion", "sanction", "tariff", "alliance", "decoupl", "embargo", "coup"]
# 否定/弱化词：命中则该条方向信号降权(治"标题有词就算数")
NEGATORS = ["否认", "辟谣", "未", "不会", "暂缓", "传闻", "无关", "denies", "denied", "no plan",
            "rumor", "unlikely", "not "]
# 相关性闸：该环主题词，标题/摘要须至少命中一个才算"与本环相关"
RELEVANCE = {
    "strategy": ["ai", "人工智能", "芯片", "半导体", "英伟达", "台积电", "nvidia", "tsmc",
                 "gpu", "算力", "数据中心", "hbm", "存储", "晶圆"],
    "means": ["稳定币", "加密", "比特币", "usdc", "usdt", "stablecoin", "crypto", "bitcoin",
              "数字资产", "fima", "央行"],
    # 乙3：世界观相关性放宽——地缘/秩序/大国政治/央行/战争/制裁/选举/贸易 都算世界观相关。
    # 原名单只有8个地缘词→把"美联储议息/中美贸易/大选/北约"这类真·世界观新闻全挡在门外，
    # 结果天天假报"今日无重大地缘新闻"、董事长看到就不往下验收了。
    "world": ["关税", "制裁", "地缘", "联盟", "脱钩", "贸易战", "贸易", "出口管制", "禁运",
              "战争", "军事", "冲突", "停火", "核", "导弹", "政变",
              "大选", "选举", "总统", "首相", "议会", "参议院", "众议院", "国会",
              "央行", "美联储", "加息", "降息", "议息", "利率决议", "欧洲央行", "日本央行",
              "秩序", "峰会", "条约", "协定", "北约", "联合国", "g7", "g20", "金砖",
              "中美", "美中", "俄乌", "俄罗斯", "乌克兰", "中东", "以色列", "伊朗", "台海", "朝鲜",
              "tariff", "sanction", "geopolit", "alliance", "war", "conflict", "ceasefire",
              "trade", "export control", "embargo", "election", "senate", "congress", "parliament",
              "central bank", "fed ", "federal reserve", "rate cut", "rate hike", "ecb", "boj",
              "summit", "treaty", "nato", "united nations", "diploma", "nuclear"],
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ── 真源抓取（抓不到→返回 None，由调用方标"待接真源"）────────────────────────

def _src_tier(src: str) -> str | None:
    """源白名单判定：命中→返回规范中文源名；剔除模式或名单外→None。"""
    s = (src or "").strip().lower()
    if not s:
        return None
    if SOURCE_BLOCK_PAT.search(s):
        return None
    for key, disp in SOURCE_WHITELIST.items():
        if key in s:
            return disp
    return None


def _pub_dt(it) -> "datetime | None":
    raw = (it.findtext("pubDate") or "").strip()
    if not raw:
        return None
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(raw)
    except Exception:
        return None


def fetch_news(query: str, limit: int = 12, lang: str = "zh") -> list[dict[str, Any]] | None:
    """Google News RSS（keyless）。中文源优先(zh-CN)→标题原生中文。
    每条带 pub_dt/pub_date(真实发布日) + source(白名单规范名)；网络失败→None。
    不在此过滤，过滤交 qualify_news(源白名单+时效)，以便如实报"抓到N条/合格M条"。"""
    if lang == "zh":
        suffix = "&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    else:
        suffix = "&hl=en-US&gl=US&ceid=US:en"
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(query) + suffix
    try:
        req = urllib.request.Request(url, headers=UA)
        raw = urllib.request.urlopen(req, timeout=TIMEOUT).read()
        root = ET.fromstring(raw)
    except Exception:
        return None
    items = []
    for it in root.findall(".//item")[:limit]:
        title = html.unescape((it.findtext("title") or "").strip())
        src = ""
        src_el = it.find("source")
        if src_el is not None and src_el.text:
            src = html.unescape(src_el.text.strip())
        link = html.unescape((it.findtext("link") or "").strip())
        desc = it.findtext("description") or ""
        summary = re.sub(r"<[^>]+>", " ", html.unescape(desc))
        summary = re.sub(r"\s+", " ", summary).strip()[:400]
        dt = _pub_dt(it)
        if title:
            items.append({"title": title, "source_raw": src, "url": link, "summary": summary,
                          "pub_dt": dt,
                          "pub_date": dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if dt else "发布日待接",
                          "lang": "en" if _looks_english(title) else "zh"})
    return items or None


def _looks_english(s: str) -> bool:
    zh = sum(1 for c in s if "一" <= c <= "鿿")
    return zh == 0 and bool(re.search(r"[A-Za-z]{4,}", s or ""))


def qualify_news(items: list[dict[str, Any]] | None, ring: str,
                 now: "datetime | None" = None) -> dict[str, Any]:
    """源白名单 + 时效(MAX_AGE_HOURS) + 相关性闸 三重过滤。
    返回 {ok:[合格条], dropped:[(标题,原因)], stats:{...}}。合格0条→上层标"今日无重大新闻·维持基线"。"""
    now = now or datetime.now(timezone.utc)
    ok, dropped, weak = [], [], []

    def _drop(n, reason, near=False):
        """乙3：剔除条也保完整标题+来源+日期+链接(原来 title[:40] 硬切→半截标题)。
        near=True 表示"今天真读到了、只是判为弱相关"→要列给董事长自己看，不许直接劝退。"""
        src_raw = str(n.get("source_raw", "") or "")
        rec = {"title": n.get("title", ""), "reason": reason,
               "source": (src_raw.split(" - ")[-1].strip() or src_raw or "来源不详"),
               "url": n.get("url", ""), "pub_date": n.get("pub_date", "")}
        dropped.append(rec)
        if near:
            weak.append(rec)

    for n in (items or []):
        tier = _src_tier(n.get("source_raw", ""))
        blob0 = (n.get("title", "") + " " + n.get("summary", ""))
        rel_hit = any(w.lower() in blob0.lower() for w in RELEVANCE.get(ring, []))
        if not tier:
            # 重要性按内容判(不光按域名)：明确重大新闻(法案/监管/议息/财报/关税…)且非剔除类源→救回
            src_raw = n.get("source_raw", "")
            if IMPORTANT_PAT.search(blob0) and not SOURCE_BLOCK_PAT.search(src_raw.lower()):
                tier = (src_raw or "其他媒体").split(" - ")[0].strip()[:12]
            else:
                # 源不够权威但【主题确实相关】→算"弱相关·今天读到了"，列出来给董事长自己看
                _drop(n, f"源不在权威名单、内容也够不上重大：{src_raw}", near=rel_hit)
                continue
        dt = n.get("pub_dt")
        if dt is None:
            _drop(n, "没有发布日期(pubDate缺)→不采信", near=rel_hit)
            continue
        age_h = (now - dt.astimezone(timezone.utc)).total_seconds() / 3600.0
        if age_h > MAX_AGE_HOURS:
            _drop(n, f"旧闻(发布于{dt.astimezone(timezone.utc):%Y-%m-%d}·距今{age_h:.0f}小时>{MAX_AGE_HOURS}小时)",
                  near=rel_hit)
            continue
        blob = (n.get("title", "") + " " + n.get("summary", "")).lower()
        if not rel_hit:
            _drop(n, "与本环主题不相关(未过相关性闸)", near=False)
            continue
        n2 = dict(n)
        n2["source"] = tier
        n2["age_h"] = round(age_h, 1)
        ok.append(n2)
    return {"ok": ok, "dropped": dropped, "weak": weak,
            "stats": {"fetched": len(items or []), "qualified": len(ok), "dropped": len(dropped),
                      "weak": len(weak)}}


def _dir_signal(n: dict[str, Any], pos_words: list[str], neg_words: list[str]) -> tuple[float, str]:
    """单条新闻的方向研判(非机械计数)：判断实质方向+否定词降权+按新鲜度加权。
    返回 (带权分, 研判理由)。"""
    blob = (n.get("title", "") + " " + n.get("summary", "")).lower()
    hit_pos = [w for w in pos_words if w.lower() in blob]
    hit_neg = [w for w in neg_words if w.lower() in blob]
    negated = any(w.lower() in blob for w in NEGATORS)
    if not hit_pos and not hit_neg:
        return 0.0, "无明确方向(仅相关背景)"
    raw = (1.0 if hit_pos else 0.0) - (1.0 if hit_neg else 0.0)
    if hit_pos and hit_neg:
        raw = 0.0
    w_fresh = 1.0 if n.get("age_h", 99) <= 12 else 0.6      # 越新权重越高
    w_neg = 0.35 if negated else 1.0                         # 否定/辟谣→大幅降权
    score = raw * w_fresh * w_neg
    why = []
    if hit_pos: why.append("利多依据:" + "/".join(hit_pos[:2]))
    if hit_neg: why.append("利空依据:" + "/".join(hit_neg[:2]))
    if negated: why.append("含否定/辟谣→降权")
    why.append(f"新鲜度{n.get('age_h','?')}h")
    return score, "·".join(why)


def fetch_fred_latest(series_id: str) -> dict[str, Any] | None:
    """FRED fredgraph.csv（keyless）。返回 {date, value, prev}；失败/超时→None。"""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    try:
        req = urllib.request.Request(url, headers=UA)
        text = urllib.request.urlopen(req, timeout=TIMEOUT).read().decode("utf-8")
    except Exception:
        return None
    rows = [r for r in text.strip().splitlines()[1:] if "," in r]
    vals = []
    for r in rows:
        d, _, v = r.partition(",")
        v = v.strip()
        if v and v != ".":
            try:
                vals.append((d.strip(), float(v)))
            except ValueError:
                pass
    if not vals:
        return None
    last = vals[-1]
    prev = vals[-2] if len(vals) >= 2 else (None, None)
    return {"series": series_id, "date": last[0], "value": last[1], "prev": prev[1]}


# ── 关键词规则：真新闻→力度（写死·可审计）────────────────────────────────────

def _judge(q: dict[str, Any], pos_words: list[str], neg_words: list[str]) -> dict[str, Any]:
    """对【合格新闻】做加权方向研判(逐条给理由)，非机械计数。返回带权净分与逐条研判。"""
    per = []
    net = 0.0
    for n in q["ok"]:
        sc, why = _dir_signal(n, pos_words, neg_words)
        net += sc
        per.append({"title": n["title"], "source": n["source"], "pub_date": n["pub_date"],
                    "url": n.get("url", ""), "lang": n.get("lang", "zh"),
                    "signal": round(sc, 2), "why": why})
    return {"net": round(net, 2), "per_item": per, "n_ok": len(q["ok"]),
            "dropped": q["dropped"], "stats": q["stats"]}


NO_NEWS = "今日无重大新闻·维持基线"


def judge_strategy(q: dict[str, Any]) -> dict[str, Any]:
    j = _judge(q, STRAT_BULL, STRAT_BEAR)
    if j["n_ok"] == 0:
        return {**j, "strength": "中", "state": NO_NEWS, "direction": f"AI({NO_NEWS})", "no_news": True}
    net = j["net"]
    if net >= 1.5:
        strength, state = "强", "AI产业面走强"
    elif net <= -1.5:
        strength, state = "弱", "AI产业面转弱"
    else:
        strength, state = "中", "AI产业面中性"
    return {**j, "strength": strength, "state": state, "direction": f"AI({state})", "no_news": False}


def judge_means(q: dict[str, Any]) -> dict[str, Any]:
    j = _judge(q, MEANS_POS, MEANS_NEG)
    if j["n_ok"] == 0:
        return {**j, "strength": "中", "state": NO_NEWS, "direction": NO_NEWS, "no_news": True}
    net = j["net"]
    if net >= 1.5:
        strength, state = "中", "稳定币/加密通道活跃(偏松)"
    elif net <= -1.5:
        strength, state = "弱", "稳定币/加密通道受限(偏紧)"
    else:
        strength, state = "中", "手段层有动作·中性"
    return {**j, "strength": strength, "state": state, "direction": state, "no_news": False}


def judge_world(q: dict[str, Any]) -> dict[str, Any]:
    """世界观级 regime 反转是高门槛：只有权威源当日实质地缘事件才算数，且仍不凭新闻就翻面(诚实)。"""
    j = _judge(q, WORLD_REGIME, [])
    # 甲4：本层问的是"世界是否真变"→ direction 必须【回答】这个问题，不许答"变"却又说"维持"(自打架)。
    if j["n_ok"] == 0:
        return {**j, "strength": "中", "state": "三支柱维持·今日无重大地缘新闻",
                "direction": "没变(三支柱维持·今日无重大地缘新闻)", "no_news": True}
    strong = [p for p in j["per_item"] if p["signal"] > 0]
    if len(strong) >= 2:
        state = "地缘/秩序信号增多·需盯(未到regime反转)"
        direction = f"没变·但要盯({state})"
    else:
        state = "三支柱维持·无regime反转"
        direction = f"没变({state})"
    return {**j, "strength": "中", "state": state, "direction": direction, "no_news": False}


# ── 组装：把真评写回对应 link（覆盖"待第二块"占位，带 source 指纹）──────────────

def _find(links: list[dict], keyword: str) -> dict | None:
    for L in links:
        if keyword in str(L.get("node", "")):
            return L
    return None


PLAIN = {
    "strategy": {"强": "今天 AI 产业的权威新闻里好消息明显多于坏消息，产业面在走强 → 对你：AI 主线基本面还硬，核心仓可以守、别追高。",
                 "弱": "今天 AI 产业的权威新闻里坏消息偏多、产业面转弱 → 对你：AI 主线要盯着点、别急着加仓。",
                 "中": "今天 AI 产业好坏消息参半、没大变 → 对你：AI 主线守着看，不追高也不慌。",
                 "无": "今天没有够格(权威源+当日)的 AI 产业新闻 → 维持基线：AI 主线沿用上次判断，核心仓照守、不因没新闻就动。"},
    "means": {"活跃": "稳定币/加密这条「钱进美元」的管道今天利好偏多、在变活 → 对你：长期利多美元资产，加密簇按纪律控敞口。",
              "受限": "稳定币这条管道今天遇到监管收紧 → 对你：短期情绪偏谨慎，加密簇别追。",
              "中": "稳定币/加密通道今天没明显动作 → 对你：不影响今天动作。",
              "无": "今天没有够格(权威源+当日)的稳定币/加密新闻 → 维持基线：不影响今天动作。"},
    "world": {"增多": "地缘/秩序上的紧张信号今天多了一些，但还没到掀翻大格局的程度 → 对你：投资大方向暂时不变，多留个心眼、盯着点。",
              "维持": "今天没有会掀翻世界大格局的地缘大事，三支柱（美国优先·阵营化·集中砸AI）延续 → 对你：投资大方向不变，照现有框架走。",
              "无": "今天没有够格(权威源+当日)的地缘新闻 → 维持基线：三支柱延续，大方向不变。"},
}


def _fetch_qualified(ring: str) -> dict[str, Any]:
    """中文源优先(标题原生中文)；合格不足→英文源兜底(仍走白名单+时效)。"""
    zh = fetch_news(QUERIES[ring], lang="zh") or []
    q = qualify_news(zh, ring)
    used = "中文源(zh-CN)"
    if q["stats"]["qualified"] == 0:
        en = fetch_news(QUERIES_EN_FALLBACK[ring], lang="en") or []
        q2 = qualify_news(en, ring)
        if q2["stats"]["qualified"] > 0:
            q2["stats"]["fetched"] += q["stats"]["fetched"]
            q2["dropped"] = q["dropped"] + q2["dropped"]
            q = q2
            used = "中文源0合格→英文权威源兜底"
    q["feed_used"] = used
    return q


def smart_trim(s: str, limit: int = 44) -> str:
    """第四轮：标题只在词/句边界截断+加…，绝不从中间硬切。日期/来源一律不截。"""
    s = (s or "").strip()
    # 去掉 Google News 惯例的" - 来源"尾巴(来源另有字段·不重复)
    s = re.sub(r"\s+-\s+[^\-]{1,20}$", "", s).strip()
    if len(s) <= limit:
        return s
    cut = s[:limit]
    # 优先在中文句读/英文词边界断开
    for sep in ("！", "？", "。", "；", "，", "、", "!", "?", ";", ",", " "):
        p = cut.rfind(sep)
        if p >= limit * 0.5:
            return cut[:p].rstrip(" ，、;,") + "…"
    return cut.rstrip() + "…"


def _write_ring(node: dict, ring: str, jd: dict, q: dict) -> None:
    """把研判写回环：evidence 讲清「几条抓到/几条合格/为什么剔除/逐条研判」，非关键词计数。"""
    st = q["stats"]
    drop_txt = "；".join(f"{smart_trim(d['title'])}→{d['reason']}" for d in q["dropped"][:3]) or "无"
    weak = q.get("weak") or []
    if jd.get("no_news"):
        # 乙3：合格0条【绝不】直接"无事件·维持基线"劝退——今天读到的、判为弱相关的也要摆出来给董事长自己看。
        node["evidence"] = (f"【新闻研判】{ring}：抓{st['fetched']}条 → 过源白名单+时效({MAX_AGE_HOURS}h)+相关性闸后"
                            f"合格 0 条 → 判「{jd['state']}」(不拿旧闻/杂源凑·不编)。"
                            f"今天读到但判为弱相关的有 {len(weak)} 条(见下·董事长可自己看)。剔除示例：{drop_txt}")
        if weak:
            node["today_events"] = [f"今天没有够格的{ring}新闻（抓{st['fetched']}条·合格0条）；"
                                    f"但今天确实读到了这 {len(weak)} 条弱相关的，摆出来你自己判："]
        else:
            node["today_events"] = [f"今日无够格新闻·维持基线（抓{st['fetched']}条·合格0条）"]
        node["news_items"] = []
        # 弱相关条单列一个字段：渲染层照样出完整标题/来源/日期/可点链接，只是标明"弱相关·未采信"
        node["weak_items"] = [{"title": d["title"], "source": d["source"], "url": d["url"],
                               "pub_date": d["pub_date"], "judge": d["reason"]} for d in weak[:3]]
        node["background"] = [f"源白名单=路透/彭博/CNBC/WSJ/FT/官方+财新/华尔街见闻/第一财经/证券时报；时效≤{MAX_AGE_HOURS}h；已剔除大学页/智库博客/内容农场"]
    else:
        per = jd["per_item"]
        # 标题只在词/句边界截+…；来源与日期【完整不截】
        node["evidence"] = (f"【新闻研判】{ring}：抓{st['fetched']}条→合格{st['qualified']}条(权威源+{MAX_AGE_HOURS}h内+过相关性闸)，"
                            f"逐条方向研判加权净分={jd['net']} → 判「{jd['state']}·{jd['strength']}」(非关键词计数)。"
                            + "样本：" + "；".join(f"{smart_trim(p['title'])}（{p['source']}·{p['pub_date']}·{p['why']}）"
                                                for p in per[:3]))
        node["today_events"] = [f"{p['source']}·{p['pub_date']}：{smart_trim(p['title'], 60)}" for p in per[:3]]
        node["news_items"] = [{"title": p["title"], "source": p["source"], "url": p["url"],
                               "pub_date": p["pub_date"], "lang": p["lang"],
                               "judge": p["why"], "signal": p["signal"]} for p in per[:5]]
        node["weak_items"] = []
        node["background"] = [f"加权研判净分={jd['net']}(逐条:新鲜度加权·否定/辟谣降权·须过相关性闸)",
                              f"合格{st['qualified']}/抓{st['fetched']}·剔除{st['dropped']}条(源不合格/旧闻/不相关)"]
    node["strength"] = jd["strength"]
    node["direction"] = jd["direction"]
    node["_state"] = jd["state"]
    node["source"] = f"Google News RSS·{q.get('feed_used','')}·合格{st['qualified']}/抓{st['fetched']}条·源白名单+≤{MAX_AGE_HOURS}h"
    node["news_dropped"] = [dict(d) for d in q["dropped"][:6]]   # 乙3:完整标题+来源+日期+链接(不再半截)


def enrich_links(links: list[dict[str, Any]], date: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """三环新闻→加权研判写回。整改后：源白名单+时效+中文源+逐条研判(非关键词计数)。"""
    report: dict[str, Any] = {"source": "Google News RSS(zh-CN优先·keyless) + FRED(keyless)",
                              "news_rules": {"whitelist": sorted(set(SOURCE_WHITELIST.values())),
                                             "blocked": "大学活动页/智库博客(ODI等)/内容农场(eciks等)/零售App博客/论坛",
                                             "max_age_hours": MAX_AGE_HOURS,
                                             "judge": "逐条方向研判(相关性闸+新鲜度加权+否定词降权)·非关键词命中计数"},
                              "auto_nodes": [], "pending_source_nodes": [], "fetched": {}}

    for ring, keyword, judger, label in (
            ("strategy", "战略指向", judge_strategy, "战略产业面"),
            ("means", "手段层", judge_means, "手段层"),
            ("world", "总命题", judge_world, "世界观级")):
        node = _find(links, keyword) or (_find(links, "世界") if ring == "world" else None)
        if node is None:
            continue
        q = _fetch_qualified(ring)
        if q["stats"]["fetched"] == 0:
            node["evidence"] = f"【待接真源】{label}新闻源今日抓取失败(网络) → 读上一状态，不编造。"
            node["direction"] = "待接真源·读上一状态"
            node["plain"] = f"今天没抓到{label}的新闻，沿用上次判断 → 对你：不因抓不到就动。"
            node["source"] = "Google News RSS 抓取失败·待接真源"
            report["pending_source_nodes"].append(label)
            continue
        jd = judger(q)
        _write_ring(node, label, jd, q)
        # 大白话
        if ring == "strategy":
            node["plain"] = PLAIN["strategy"]["无" if jd.get("no_news") else jd["strength"]]
        elif ring == "means":
            k = "无" if jd.get("no_news") else ("活跃" if "活跃" in jd["state"] else ("受限" if "受限" in jd["state"] else "中"))
            node["plain"] = PLAIN["means"][k]
        else:
            k = "无" if jd.get("no_news") else ("增多" if "增多" in jd["state"] else "维持")
            node["plain"] = PLAIN["world"][k]
        report["auto_nodes"].append(label)
        report["fetched"][ring] = {"fetched": q["stats"]["fetched"], "qualified": q["stats"]["qualified"],
                                   "dropped": q["stats"]["dropped"], "feed": q.get("feed_used"),
                                   "net": jd.get("net"), "state": jd["state"], "no_news": jd.get("no_news", False),
                                   "items": [{"title": p["title"], "source": p["source"], "pub_date": p["pub_date"],
                                              "lang": p["lang"], "signal": p["signal"], "why": p["why"]}
                                             for p in jd.get("per_item", [])[:5]],
                                   "dropped_examples": [dict(d) for d in q["dropped"][:5]]}

    # —— 总闸 enrich：经济日历真值(非农/CPI/Fed)。本网络下 FRED 超时→待接真源 ——
    fed_node = _find(links, "总闸")
    macro = {}
    for key, sid in (("非农PAYEMS", "PAYEMS"), ("CPI", "CPIAUCSL"), ("FedFunds", "FEDFUNDS")):
        got = fetch_fred_latest(sid)
        if got:
            macro[key] = got
    if fed_node is not None:
        if macro:
            bits = []
            for k, v in macro.items():
                trend = ""
                if v.get("prev") is not None:
                    trend = "升" if v["value"] > v["prev"] else ("降" if v["value"] < v["prev"] else "平")
                bits.append(f"{k}={v['value']}({v['date']}·较前值{trend})")
            fed_node.setdefault("today_events", []).append("经济日历真值：" + "；".join(bits))
            fed_node["source"] = str(fed_node.get("source", "")) + " + FRED经济日历"
            report["fetched"]["macro_calendar"] = macro
            report["auto_nodes"].append("总闸·经济日历enrich")
        else:
            fed_node.setdefault("background", []).append("经济日历源(FRED非农/CPI/Fed)本次超时→待接真源，总闸仍按行情边际")
            report["pending_source_nodes"].append("总闸·经济日历(FRED超时)")

    return links, report


def apply_to_file(date: str) -> dict[str, Any]:
    """独立跑：读回 daily_{date}.json，enrich 三环，写回。"""
    path = ROOT / "data" / "evidence_chain" / f"daily_{date}.json"
    if not path.exists():
        raise FileNotFoundError(f"need 第一块求证表 first: {path}")
    data = _read_json(path)
    links, report = enrich_links(data.get("links", []), date)
    data["links"] = [{k: v for k, v in L.items() if not k.startswith("_")} for L in links]
    data.setdefault("rule_engine", {})["macro_news"] = report
    data["data_date_note"] = str(data.get("data_date_note", "")) + " ｜已接第二块(宏观新闻源)覆写三环。"
    _write_json(path, data)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="第二块·宏观事件+主题新闻源")
    parser.add_argument("--date", default="20260711")
    args = parser.parse_args()
    report = apply_to_file(args.date)
    print(f"[OK] 第二块已写回 daily_{args.date}.json")
    print("自动评环:", "、".join(report["auto_nodes"]) or "无")
    print("待接真源环:", "、".join(report["pending_source_nodes"]) or "无")
    print("report:", json.dumps(report, ensure_ascii=False)[:400])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
