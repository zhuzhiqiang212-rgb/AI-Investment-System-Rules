#!/usr/bin/env python3
"""佐证料接入：Drive 研报 PDF（董事局工单2026-07-17·甲）· 只读不下单

问题：佐证料停在 2026-05-29，因为董事长 Drive 里那批研报 PDF（湖水/Tech Daily/周前瞻/盘前/
      北美资金流等，已更新到 07-11）从来没被读进来。
做法：解析 PDF 正文 → 建结构化语料（日期/来源文件/作者/标题/正文），按日期取最近若干份。
      渲染层据此出佐证：标来源文件名+日期、料不反客（总则第九条三）；研报没提的地方
      如实标"研报未覆盖·不编"。

⚠边界（CLAUDE.md §1 不设计不决策）：本模块只做【机械抽取】——把研报原话摘出来、按主题归位。
  "印证/挑战"的最终定性属分析判断；这里只做可机械判定的方向标注，判不了的标"方向待理解岗判"，
  绝不替湖水/老雷编他们没说过的话。

产物：data/analysis/research_corpus.json
用法：python scripts/research_corpus_ingest.py --src "G:/我的云端硬盘/湖水资讯" --days 14
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
DEFAULT_SRC = Path("G:/我的云端硬盘/湖水资讯")

# 文件名日期：26-07-11-1 xxx.pdf → 2026-07-11
_FN_DATE = re.compile(r"^(\d{2})-(\d{1,2})-(\d{1,2})")
# 正文里的英文日期（更权威，作者自己写的）：Friday, July 10, 2026
_BODY_DATE = re.compile(r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,\s+([A-Z][a-z]+)\s+(\d{1,2}),\s+(\d{4})")
_MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}

# 主题归位（机械关键词匹配·把研报原话挂到系统的层/标的上）
TOPIC_KEYS = {
    "世界观": ["地缘", "美伊", "伊朗", "关税", "制裁", "战争", "北约", "秩序", "特朗普", "大国"],
    "总闸": ["FOMC", "美联储", "fed", "利率", "降息", "加息", "CPI", "PPI", "非农", "点阵图"],
    "战略指向": ["AI", "算力", "半导体", "GPU", "英伟达", "NVDA", "TSM", "台积电", "CPO", "HBM", "ASML"],
    "手段层": ["稳定币", "加密", "比特币", "BTC", "crypto", "stablecoin", "代币"],
    "资金轮动": ["资金流", "hedge fund", "net leverage", "CTA", "vol control", "仓位", "Bulls & Bears",
                 "北美资金", "北亚资金", "ETF流入", "ETF流出"],
    "板块轮动": ["板块", "轮动", "科技股", "NDX", "纳指", "SOX", "半导体指数"],
    "机会池": ["买入", "加仓", "低吸", "建仓", "机会"],
}
SYMBOL_KEYS = {
    "US.NVDA": ["英伟达", "NVDA", "Nvidia"], "US.TSM": ["台积电", "TSM", "TSMC"],
    "US.MSFT": ["微软", "MSFT", "Microsoft"], "US.AVGO": ["博通", "AVGO", "Broadcom"],
    "US.META": ["META", "Meta", "脸书"], "US.SNDK": ["闪迪", "SNDK", "SanDisk"],
    "JP.9984": ["软银", "SoftBank", "9984"], "JP.6857": ["爱德万", "Advantest", "6857"],
    "US.MSTR": ["MSTR", "MicroStrategy", "Strategy"], "US.COIN": ["Coinbase", "COIN"],
    "US.CRCL": ["Circle", "CRCL"], "JP.7974": ["任天堂", "Nintendo", "7974"],
    "JP.6758": ["索尼", "Sony", "6758"], "JP.7203": ["丰田", "Toyota", "7203"],
    "JP.4568": ["第一三共", "Daiichi", "4568"], "JP.8766": ["东京海上", "8766"],
    "JP.8001": ["伊藤忠", "8001"], "JP.7832": ["万代", "7832"], "US.IBKR": ["IBKR", "盈透"],
    "US.SPCX": ["SpaceX", "SPCX"],
}


# ⚠这批 PDF 里大量汉字被排版成【康熙部首/兼容区】变体：湖⽔(⽔≠水)、7⽉(⽉≠月)、⼏(≠几)…
#   不折回正常汉字，关键词匹配会大面积落空(实测"湖水"匹配不到、作者识别全成"待接")。
_CJK_COMPAT = {
    "⽔": "水", "⽉": "月", "⼏": "几", "⽇": "日", "⼀": "一", "⼆": "二", "⼈": "人",
    "⼤": "大", "⼩": "小", "⼭": "山", "⼒": "力", "⼊": "入", "⼯": "工", "⼠": "士",
    "⼦": "子", "⼿": "手", "⽂": "文", "⽅": "方", "⽕": "火", "⽯": "石", "⽥": "田",
    "⽩": "白", "⽬": "目", "⾦": "金", "⻓": "长", "⻔": "门", "⻜": "飞", "⻢": "马",
    "⻄": "西", "⾔": "言", "⾜": "足", "⻋": "车", "⾬": "雨", "⾼": "高", "⿊": "黑",
    "⽣": "生", "⽤": "用", "⽐": "比", "⽒": "氏", "⽊": "木", "⽜": "牛", "⽝": "犬",
    "⾏": "行", "⾯": "面", "⾷": "食", "⾻": "骨", "⿃": "鸟", "⼼": "心", "⽗": "父",
}


def _norm(s: str) -> str:
    """PDF 抽出来的中文常夹全角空格/断行/康熙部首变体；归一化好做关键词匹配与展示。"""
    s = s.replace("⁠", "").replace("﻿", "")
    for a, b in _CJK_COMPAT.items():
        s = s.replace(a, b)
    s = re.sub(r"[ \t　]+", " ", s)
    s = re.sub(r"\n{2,}", "\n", s)
    return s.strip()


def _file_date(name: str) -> str | None:
    m = _FN_DATE.match(name)
    if not m:
        m2 = re.search(r"(20\d{2})(\d{2})(\d{2})", name)     # G09_完整投研报表_20260617_V2
        return f"{m2.group(1)}-{m2.group(2)}-{m2.group(3)}" if m2 else None
    y, mo, d = m.groups()
    return f"20{y}-{int(mo):02d}-{int(d):02d}"


def _body_date(text: str) -> str | None:
    m = _BODY_DATE.search(text)
    if not m:
        return None
    mo = _MONTHS.get(m.group(1))
    return f"{m.group(3)}-{mo:02d}-{int(m.group(2)):02d}" if mo else None


def parse_pdf(p: Path) -> dict | None:
    try:
        from pypdf import PdfReader
    except Exception:
        return None
    try:
        import logging
        logging.getLogger("pypdf").setLevel(logging.ERROR)
        r = PdfReader(str(p))
        text = _norm("\n".join((pg.extract_text() or "") for pg in r.pages))
    except Exception as e:
        return {"file": p.name, "error": f"解析失败：{type(e).__name__}", "text": "", "pages": 0}
    if not text:
        return {"file": p.name, "error": "PDF 无可抽取文本（可能是扫描件）→ 不编", "text": "", "pages": 0}
    bd, fd = _body_date(text), _file_date(p.name)
    # 作者自己写的日期比文件名可靠；两者都没有→不编日期
    date = bd or fd
    # 作者：按研报里自己写的「作者：X」实取，取不到才标待接(不猜)
    ma = re.search(r"作者[：:]\s*([^\s\n，,。]{1,12})", text[:600])
    author = ma.group(1).strip() if ma else "待接"
    title = re.sub(r"^\d{2}-\d{1,2}-\d{1,2}-?\d*[\s.、]*", "", p.stem).strip() or p.stem
    return {"file": p.name, "date": date, "date_from": ("正文" if bd else ("文件名" if fd else "无")),
            "author": author, "title": title, "pages": len(r.pages), "chars": len(text),
            "text": text, "error": ""}


def _hits(text: str, keys: list) -> list:
    return [k for k in keys if k.lower() in text.lower()]


def _excerpt(text: str, keys: list, width: int = 150) -> str:
    """摘研报【原话】(不改写·不解读)：取第一处命中周围的一句。"""
    for k in keys:
        i = text.lower().find(k.lower())
        if i < 0:
            continue
        a = max(0, i - width // 2)
        seg = text[a: a + width]
        seg = re.sub(r"^\S*\s", "", seg)          # 掐头不完整词
        return seg.strip().rstrip("，,。;；") + "…"
    return ""


def build(src: Path, days: int, today: str) -> dict:
    pdfs = sorted(src.glob("*.pdf"))
    docs, errs = [], []
    for p in pdfs:
        d = parse_pdf(p)
        if d is None:
            return {"error": "pypdf 不可用 → 无法解析研报 PDF", "docs": []}
        (errs if d.get("error") else docs).append(d)
    docs = [d for d in docs if d.get("date")]
    docs.sort(key=lambda d: d["date"], reverse=True)
    latest = docs[0]["date"] if docs else None
    # 近 N 天的料(按最新研报日往前数·不是按今天·否则周末/假期会误判成"没料")
    recent = []
    if latest:
        cut = (datetime.strptime(latest, "%Y-%m-%d") - timedelta(days=days)).strftime("%Y-%m-%d")
        recent = [d for d in docs if d["date"] >= cut]
    by_topic, by_symbol = {}, {}
    for topic, keys in TOPIC_KEYS.items():
        for d in recent:                                   # recent 已按日期倒序 → 第一个命中的就是最近一份
            h = _hits(d["text"], keys)
            if h:
                by_topic[topic] = {"file": d["file"], "date": d["date"], "author": d["author"],
                                   "title": d["title"], "hit_keys": h[:4],
                                   "excerpt": _excerpt(d["text"], h)}
                break
    for sym, keys in SYMBOL_KEYS.items():
        for d in recent:
            h = _hits(d["text"], keys)
            if h:
                by_symbol[sym] = {"file": d["file"], "date": d["date"], "author": d["author"],
                                  "title": d["title"], "hit_keys": h[:4],
                                  "excerpt": _excerpt(d["text"], h)}
                break
    return {"error": "", "latest_date": latest, "docs": docs, "recent": recent,
            "by_topic": by_topic, "by_symbol": by_symbol, "parse_errors": errs}


def main() -> int:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="佐证料接入(Drive研报PDF)")
    ap.add_argument("--src", default=str(DEFAULT_SRC))
    ap.add_argument("--days", type=int, default=14, help="取最新研报日往前 N 天的料")
    ap.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d"))
    a = ap.parse_args()
    src = Path(a.src)
    if not src.exists():
        print(f"[佐证接入 失败] 研报文件夹不存在：{src}", file=sys.stderr)
        return 3
    r = build(src, a.days, a.date)
    if r.get("error"):
        print(f"[佐证接入 失败] {r['error']}", file=sys.stderr)
        return 3
    doc = {
        "_说明": "佐证料语料库：解析董事长 Drive 研报 PDF 正文而来。渲染层据此出佐证——"
                 "标来源文件名+日期、只摘研报原话、料不反客(总则第九条三)；研报没提的地方标"
                 "「研报未覆盖·不编」。本模块只做机械抽取，不替作者编他没说过的话。",
        "_边界": "「印证/挑战」的最终定性属分析判断(CLAUDE.md §1 不设计不决策)；"
                 "本文件只提供【研报原话+来源+日期】，由渲染层原样摆出来给董事长自己看。",
        "src_folder": str(src),
        "date": a.date,
        "generated_at": datetime.now(JST).isoformat(timespec="seconds"),
        "latest_report_date": r["latest_date"],
        "window_days": a.days,
        "n_pdf_total": len(r["docs"]) + len(r["parse_errors"]),
        "n_parsed": len(r["docs"]),
        "n_recent": len(r["recent"]),
        "recent_files": [{"file": d["file"], "date": d["date"], "title": d["title"],
                          "author": d["author"], "pages": d["pages"], "chars": d["chars"],
                          "date_from": d["date_from"]} for d in r["recent"]],
        "by_topic": r["by_topic"],
        "by_symbol": r["by_symbol"],
        "parse_errors": [{"file": e["file"], "error": e["error"]} for e in r["parse_errors"]],
    }
    p = ROOT / "data" / "analysis" / "research_corpus.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {p.name} · PDF {doc['n_pdf_total']} 份 · 解析成功 {doc['n_parsed']} · "
          f"最新研报日 {doc['latest_report_date']} · 近{a.days}天 {doc['n_recent']} 份")
    print(f"   主题覆盖 {len(doc['by_topic'])}/{len(TOPIC_KEYS)} · 标的覆盖 {len(doc['by_symbol'])}/{len(SYMBOL_KEYS)}")
    for e in doc["parse_errors"]:
        print(f"   ⚠ {e['file']}：{e['error']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
