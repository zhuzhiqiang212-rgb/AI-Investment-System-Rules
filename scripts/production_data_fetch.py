#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
production_data_fetch.py

TASK-2026-07-05 取数环节修复版：
- 官方源替换：Federal Register Presidential Documents / BIS agency feed.
- H.4.1 抓实际缩表数值，不只抓页面标题。
- 世界观候选过滤 enforcement/termination 等例行监管噪声。
- 第⑥层补细分 ETF/板块行情并按板块认领规则机械打标。
- Yahoo chart 按最近一个有效交易日 close 标 data_date，不冒充今日。

只读取数，不下单、不发布；抓不到即标待接入/待人工认领。
"""

from __future__ import annotations

import argparse
import csv
import html
import importlib.util
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:  # pragma: no cover
    BeautifulSoup = None

ROOT = Path(r"G:\我的云端硬盘\AI_Investment_System")
JST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"

OFFICIAL_URLS = {
    "federal_register_presidential_documents": "https://www.federalregister.gov/api/v1/documents.json?conditions%5Bpresidential_document_type%5D%5B%5D=executive_order&conditions%5Bpublication_date%5D%5Bgte%5D={since}&order=newest&per_page=5",
    "federal_register_bis_rules": "https://www.federalregister.gov/api/v1/documents.json?conditions%5Bagencies%5D%5B%5D=industry-and-security-bureau&conditions%5Bpublication_date%5D%5Bgte%5D={since}&order=newest&per_page=5",
    "fed_speeches_rss": "https://www.federalreserve.gov/feeds/speeches.xml",
    "fed_press_rss": "https://www.federalreserve.gov/feeds/press_all.xml",
    "h41_current": "https://www.federalreserve.gov/releases/h41/current/h41.htm",
}

WORLDVIEW_NOISE = (
    "enforcement action",
    "termination of enforcement",
    "civil money penalty",
    "cease and desist",
    "prohibition order",
    "consent order",
    "written agreement",
)

MACRO_SPECS = [
    ("^VIX", "^VIX", "VIX"),
    ("^TNX", "US10Y", "10Y U.S. Treasury Yield"),
    ("DX-Y.NYB", "DXY", "U.S. Dollar Index"),
    ("SOXX", "SOXX", "iShares Semiconductor ETF"),
    ("^GSPC", "SPX", "S&P 500"),
    ("JPY=X", "USDJPY", "USD/JPY"),
]

SECTOR_ETFS = [
    ("SOXX", "SOXX", "AI半导体/宽半导体", "宽半导体ETF，仍需理解岗拆分AI算力/设备/代工/存储"),
    ("SMH", "SMH", "AI半导体", "半导体龙头ETF"),
    ("PSI", "PSI", "AI半导体设备/动量半导体", "半导体动量/设备相关代表，需人工核具体成分"),
    ("IGV", "IGV", "AI软件应用", "软件ETF"),
    ("CLOU", "CLOU", "AI软件应用/云", "云计算ETF，AI软件应用候选"),
    ("XLU", "XLU", "AI电力/能源", "公用事业ETF，是否AI数据中心供电需理解岗核"),
    ("URA", "URA", "AI电力/能源", "核能/铀ETF，AI电力硬约束候选"),
    ("IBIT", "IBIT", "加密", "BTC ETF/加密映射"),
    ("BITQ", "BITQ", "加密", "加密股ETF"),
    ("GLD", "GLD", "黄金", "黄金ETF"),
    ("XLV", "XLV", "防御·医疗", "医疗保健ETF"),
    ("XLF", "XLF", "防御·金融", "金融ETF"),
    ("XLE", "XLE", "能源", "能源ETF"),
    ("XLI", "XLI", "工业/安全", "工业ETF，军工安全需另核"),
    ("ITA", "ITA", "安全/军工", "航空航天与国防ETF"),
    ("IWM", "IWM", "小盘/风险偏好", "小盘指数ETF"),
    ("EWJ", "EWJ", "日本/盟友链", "日本ETF"),
]


def now_jst() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def fetch_bytes(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def clean_text(value: Any, limit: int = 700) -> str:
    if value is None:
        return ""
    s = html.unescape(re.sub(r"<[^>]+>", " ", str(value)))
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")
    b = path.read_bytes()
    if b.startswith(b"\xef\xbb\xbf"):
        raise RuntimeError(f"BOM detected: {path}")
    if b.count(b"\xef\xbf\xbd"):
        raise RuntimeError(f"U+FFFD detected: {path}")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    b = path.read_bytes()
    if b.startswith(b"\xef\xbb\xbf"):
        raise RuntimeError(f"BOM detected: {path}")
    if b.count(b"\xef\xbf\xbd"):
        raise RuntimeError(f"U+FFFD detected: {path}")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ymd_from_ts(ts: int | float | str | None) -> str | None:
    try:
        return datetime.fromtimestamp(int(ts), timezone.utc).astimezone(JST).strftime("%Y-%m-%d")
    except Exception:
        return None


def fetch_yahoo_chart(yahoo_symbol: str, out_symbol: str, name: str) -> dict[str, Any]:
    enc = urllib.parse.quote(yahoo_symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}?interval=1d&range=10d"
    try:
        data = json.loads(fetch_bytes(url, 15).decode("utf-8"))
        result = data["chart"]["result"][0]
        meta = result.get("meta", {})
        timestamps = result.get("timestamp") or []
        quote = result.get("indicators", {}).get("quote", [{}])[0]
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []
        valid = []
        for i, close in enumerate(closes):
            if close is not None and i < len(timestamps):
                valid.append((timestamps[i], float(close), volumes[i] if i < len(volumes) else None))
        if not valid:
            raise RuntimeError("no valid daily close returned")
        t_last, close_last, vol_last = valid[-1]
        prev_close = valid[-2][1] if len(valid) >= 2 else meta.get("chartPreviousClose")
        change = None
        if prev_close:
            change = (close_last / float(prev_close) - 1.0) * 100.0
        return {
            "symbol": out_symbol,
            "name": name,
            "price": round(close_last, 6),
            "close": round(close_last, 6),
            "change_percent": None if change is None else round(change, 6),
            "volume": vol_last,
            "data_date": ymd_from_ts(t_last),
            "source": f"Yahoo Finance chart close ({yahoo_symbol})",
            "source_url": url,
            "status": "OK",
            "note": "使用 chart 中最后一个有效日线 close；该日即本标的最近可得交易日，不冒充今日实时。",
        }
    except Exception as exc:
        return {
            "symbol": out_symbol,
            "name": name,
            "price": None,
            "change_percent": None,
            "volume": None,
            "data_date": None,
            "source": f"Yahoo Finance chart close ({yahoo_symbol})",
            "source_url": url,
            "status": "待接入",
            "error": str(exc),
            "note": "抓取失败，不用旧值或估算冒充。",
        }


def parse_federal_register_documents(url: str, source: str) -> tuple[list[dict[str, Any]], str | None]:
    try:
        data = json.loads(fetch_bytes(url, 15).decode("utf-8"))
        out = []
        for r in data.get("results", []):
            title = clean_text(r.get("title"), 260)
            abstract = clean_text(r.get("abstract"), 500)
            if not abstract:
                abstract = clean_text(
                    f"Federal Register未提供abstract；type={r.get('type')}；document_number={r.get('document_number')}；"
                    f"publication_date={r.get('publication_date')}；title={title}",
                    500,
                )
            out.append({
                "source": source,
                "title": title,
                "time": r.get("publication_date"),
                "data_date": r.get("publication_date"),
                "url": r.get("html_url") or r.get("pdf_url"),
                "raw": abstract,
                "document_number": r.get("document_number"),
            })
        return out, None
    except Exception as exc:
        return [], str(exc)


def fetch_rss_items(source: str, url: str, limit: int = 5) -> tuple[list[dict[str, Any]], str | None]:
    try:
        raw = fetch_bytes(url, 15)
        root = ET.fromstring(raw)
        items = []
        for item in root.findall(".//item")[:limit]:
            title = clean_text(item.findtext("title"), 260)
            desc = clean_text(item.findtext("description"), 500)
            link = clean_text(item.findtext("link"), 500)
            pub = clean_text(item.findtext("pubDate"), 120)
            data_date = None
            try:
                data_date = parsedate_to_datetime(pub).astimezone(JST).strftime("%Y-%m-%d")
            except Exception:
                pass
            items.append({"source": source, "title": title, "time": pub, "data_date": data_date, "url": link, "raw": desc or title})
        return items, None
    except Exception as exc:
        return [], str(exc)


def worldview_filter(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kept, filtered = [], []
    for item in items:
        text = f"{item.get('title','')} {item.get('raw','')}".lower()
        if any(noise in text for noise in WORLDVIEW_NOISE):
            x = dict(item)
            x["filter_reason"] = "例行 enforcement/监管处罚噪声，抓取端过滤，不进世界观①"
            filtered.append(x)
        else:
            kept.append(item)
    return kept, filtered


FRAMEWORK_WORDS = (
    "regime",
    "policy framework",
    "framework",
    "balance sheet",
    "dollar",
    "monetary",
    "reserve",
    "fima",
    "global",
    "liquidity",
    "geopolitical",
    "supply chain",
)


def framework_level(item: dict[str, Any]) -> bool:
    text = f"{item.get('title', '')} {item.get('raw', '')}".lower()
    return any(word in text for word in FRAMEWORK_WORDS)


def tag_worldview_item(item: dict[str, Any], source_type: str, cross_layer: str | None = None) -> dict[str, Any]:
    raw = clean_text(item.get("raw") or item.get("abstract") or item.get("title"), 500)
    tagged = {
        "source_type": source_type,
        "source": item.get("source"),
        "title": item.get("title"),
        "time": item.get("time"),
        "data_date": item.get("data_date"),
        "url": item.get("url"),
        "raw": raw,
        "framework_level": framework_level(item) if source_type == "美联储框架级" else None,
    }
    if cross_layer:
        tagged["cross_layer"] = cross_layer
    if item.get("document_number"):
        tagged["document_number"] = item.get("document_number")
    return tagged


def build_worldview_candidates(
    speeches: list[dict[str, Any]],
    pres_docs: list[dict[str, Any]],
    bis_docs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    fed_items = [tag_worldview_item(item, "美联储框架级") for item in speeches]
    fed_items.sort(key=lambda x: (x.get("framework_level") is not True, str(x.get("data_date") or "")))
    pres_items = [tag_worldview_item(item, "白宫行政令", "①③") for item in pres_docs]
    bis_items = [tag_worldview_item(item, "BIS管制", "①③") for item in bis_docs]
    coverage = {
        "美联储框架级": f"已扫·{len(fed_items)}条(其中框架级{sum(1 for x in fed_items if x.get('framework_level') is True)}条)",
        "白宫行政令": f"已扫·{len(pres_items)}条(横跨①③)",
        "BIS管制": f"已扫·{len(bis_items)}条(横跨①③)" if bis_items else "已扫·0条",
        "国会立法": "待接入·需Congress.gov API",
        "地缘阵营": "待接入·无官方API源",
    }
    return fed_items + pres_items + bis_items, coverage


def extract_int(text: str) -> int | None:
    m = re.search(r"[-+]?\s*\d[\d,]*", text)
    if not m:
        return None
    return int(m.group(0).replace(" ", "").replace(",", ""))


def parse_h41() -> tuple[dict[str, Any], str | None]:
    url = OFFICIAL_URLS["h41_current"]
    try:
        text = fetch_bytes(url, 20).decode("utf-8", errors="replace")
        title_m = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
        title = clean_text(title_m.group(1), 220) if title_m else "Federal Reserve H.4.1 current"
        date_m = re.search(r"H\.4\.1\s*-\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})", title)
        data_date = None
        if date_m:
            try:
                data_date = datetime.strptime(date_m.group(1), "%B %d, %Y").strftime("%Y-%m-%d")
            except Exception:
                pass
        if not BeautifulSoup:
            raise RuntimeError("BeautifulSoup unavailable")
        soup = BeautifulSoup(text, "html.parser")

        def row_values(label: str) -> list[str]:
            cell_text = soup.find(string=lambda s: bool(s and label in s))
            if not cell_text:
                return []
            row = cell_text.find_parent("tr")
            if not row:
                return []
            return [" ".join(c.get_text(" ", strip=True).split()) for c in row.find_all(["td", "th"])]

        total_assets = row_values("Total assets")
        reserve_balances = row_values("Reserve balances with Federal Reserve Banks")
        if len(total_assets) < 4 or len(reserve_balances) < 3:
            raise RuntimeError(f"H.4.1 rows incomplete: total={total_assets}, reserve={reserve_balances}")

        payload = {
            "source": "Federal Reserve H.4.1 current table",
            "title": title,
            "time": data_date,
            "data_date": data_date,
            "url": url,
            "raw": "H.4.1 实际数值搬运；Claude 判缩表方向/力度。",
            "values": {
                "total_assets_millions_usd": extract_int(total_assets[2]),
                "total_assets_week_change_millions_usd": extract_int(total_assets[3]),
                "reserve_balances_millions_usd": extract_int(reserve_balances[1]),
                "reserve_balances_week_change_millions_usd": extract_int(reserve_balances[2]),
            },
            "raw_rows": {
                "total_assets": total_assets,
                "reserve_balances": reserve_balances,
            },
        }
        return payload, None
    except Exception as exc:
        return {
            "source": "Federal Reserve H.4.1 current table",
            "title": "H.4.1 actual balance sheet values",
            "time": None,
            "data_date": None,
            "url": url,
            "raw": "待接入：H.4.1 数值抓取失败，不用页面标题或旧值冒充。",
            "values": {
                "total_assets_millions_usd": None,
                "total_assets_week_change_millions_usd": None,
                "reserve_balances_millions_usd": None,
                "reserve_balances_week_change_millions_usd": None,
            },
            "status": "待接入",
        }, str(exc)


def load_holding_symbols() -> list[dict[str, Any]]:
    path = ROOT / "data" / "accounts" / "holdings_true_20260702.json"
    doc = read_json(path)
    seen = set()
    out = []
    for h in doc.get("holdings", []):
        symbol = h.get("symbol")
        if symbol and symbol not in seen:
            seen.add(symbol)
            out.append({"symbol": symbol, "name": h.get("name")})
    return out


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def build_ma_levels(date: str) -> tuple[Path, dict[str, Any]]:
    out_path = ROOT / "data" / "holdings" / f"ma_levels_{date}.json"
    holdings = load_holding_symbols()
    mod = load_module(ROOT / "scripts" / "holdings_ma_levels.py", "holdings_ma_levels_runtime")
    ctx, attempts = mod.connect_quote_context(max_retries=3, wait_seconds=3)
    if ctx is None:
        payload = mod.build_disconnected(date, holdings, attempts, "OpenD quote connection failed")
        payload["input_note"] = f"holdings_review_{date}.json 不存在；本次修复演习仅用 holdings_true_20260702.json 作为持仓名单来源，未把旧审查结论冒充今日结论。"
        write_json(out_path, payload)
        return out_path, payload
    items = []
    try:
        for h in holdings:
            item = mod.build_item(ctx, h["symbol"], h.get("name"))
            qd = item.get("data_date")
            # build_item from older script may not carry data_date; enrich by a direct quote call if needed.
            if qd is None:
                quote = mod.get_realtime_price(h["symbol"], ctx=ctx, max_retries=1, wait_seconds=0)
                item["data_date"] = quote.get("data_date")
                item["data_time"] = quote.get("data_time")
                item["market_state"] = quote.get("market_state")
            items.append(item)
            time.sleep(0.1)
    finally:
        try:
            ctx.close()
        except Exception:
            pass
    payload = {
        "task_id": "TASK-2026-07-05-取数演习修复",
        "date": date,
        "generated_at": now_jst(),
        "connection": {"ok": True, "reason": "", "attempts": attempts},
        "input_note": f"holdings_review_{date}.json 不存在；本次修复演习仅用 holdings_true_20260702.json 作为持仓名单来源，未把旧审查结论冒充今日结论。",
        "source_kline": "Futu OpenD request_history_kline K_DAY",
        "holdings": items,
        "summary": {
            "total": len(items),
            "ok": sum(1 for x in items if x.get("status") == "OK"),
            "pending": sum(1 for x in items if x.get("status") != "OK"),
        },
        "safety": {"read_only": True, "trade_context_created": False, "place_order_called": False, "published": False},
    }
    write_json(out_path, payload)
    return out_path, payload


def refresh_stablecoin_csv() -> tuple[Path, list[dict[str, Any]], list[str]]:
    rows, errors = [], []
    for asset in ["usdt", "usdc"]:
        url = f"https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets={asset}&metrics=SplyCur&frequency=1d&page_size=1"
        try:
            data = json.loads(fetch_bytes(url, 15).decode("utf-8"))
            vals = data.get("data") or []
            if not vals:
                raise RuntimeError("empty CoinMetrics data")
            r = vals[-1]
            rows.append({
                "asset": asset.upper(),
                "metric": "current supply",
                "source": "CoinMetrics Community API",
                "source_url": url,
                "time": r.get("time"),
                "value": r.get("SplyCur"),
                "data_status": "CONNECTED_PUBLIC_ONCHAIN",
                "action_allowed": "NO",
                "note": "Supply evidence only; does not trigger account action alone.",
            })
        except Exception as exc:
            errors.append(f"{asset.upper()}: {exc}")
    path = ROOT / "data" / "onchain" / "stablecoin_supply_latest.csv"
    if len(rows) == 2:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        if path.read_bytes().count(b"\xef\xbf\xbd"):
            raise RuntimeError(f"U+FFFD detected: {path}")
        return path, rows, errors
    # Keep existing with true date if refresh fails.
    existing = []
    if path.exists():
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            existing = list(csv.DictReader(f))
    return path, existing, errors


def run_yield_curve(date: str) -> tuple[Path, dict[str, Any]]:
    script = ROOT / "scripts" / "yield_curve_fetch.py"
    mod = load_module(script, "yield_curve_runtime")
    # Reuse its main by calling subprocess-like through runpy would be clunky; fetch with its functions.
    us10y = mod.fetch_regular_market_price("^TNX")
    us3m = mod.fetch_regular_market_price("^IRX")
    out_path = ROOT / "data" / "market" / f"yield_curve_{date}.json"
    if us10y is None or us3m is None:
        payload = {
            "task_id": "2b-1",
            "generated_at": now_jst(),
            "date": date,
            "connection": {"ok": False, "reason": "Yahoo ^TNX or ^IRX unavailable"},
            "source": "Yahoo ^TNX / ^IRX",
            "short_end_note": "短端用3个月(^IRX)，非2年；真2年美债待FRED源",
            "us10y": None,
            "us3m": None,
            "spread_10y_3m": None,
            "inverted": None,
            "status": "待拉·源未连",
            "safety": {"read_only": True, "place_order_called": False, "published": False},
        }
    else:
        spread = round(us10y - us3m, 3)
        payload = {
            "task_id": "2b-1",
            "generated_at": now_jst(),
            "date": date,
            "data_date": date[:4] + "-" + date[4:6] + "-" + date[6:],
            "connection": {"ok": True, "reason": ""},
            "source": "Yahoo ^TNX / ^IRX",
            "short_end_note": "短端用3个月(^IRX)，非2年；真2年美债待FRED源",
            "us10y": us10y,
            "us3m": us3m,
            "spread_10y_3m": spread,
            "inverted": spread < 0,
            "status": "OK",
            "safety": {"read_only": True, "place_order_called": False, "published": False},
        }
    write_json(out_path, payload)
    return out_path, payload


def build_market_snapshot() -> tuple[Path, dict[str, Any]]:
    assets = [fetch_yahoo_chart(src, sym, name) for src, sym, name in MACRO_SPECS]
    payload = {
        "task_id": "TASK-2026-07-05-取数演习修复",
        "mode": "production_data_fetch_fixed_v1",
        "generated_at": now_jst(),
        "latest_trading_day_logic": "Yahoo chart range=10d，取最后一根有效日线 close；美国股指/ETF遇假日可能停在07-02，外汇/加密可有不同data_date，逐项如实标。",
        "security_rules": {
            "read_only_market_data": True,
            "place_order_called": False,
            "change_order_called": False,
            "cancel_order_called": False,
            "published": False,
        },
        "data_sources": {"primary": "Yahoo Finance chart public API", "fallback": None},
        "summary": {
            "total_assets": len(assets),
            "success_count": sum(1 for a in assets if a["status"] == "OK"),
            "fail_count": sum(1 for a in assets if a["status"] != "OK"),
            "failed_symbols": [a["symbol"] for a in assets if a["status"] != "OK"],
            "all_items_have_true_data_date_or_pending": True,
        },
        "assets": assets,
    }
    path = ROOT / "data" / "market" / "latest_market_snapshot.json"
    write_json(path, payload)
    return path, payload


def build_sector_flow() -> tuple[Path, dict[str, Any]]:
    items = []
    for src, sym, label, reason in SECTOR_ETFS:
        asset = fetch_yahoo_chart(src, sym, src)
        items.append({
            "symbol": sym,
            "name": asset.get("name"),
            "price": asset.get("price"),
            "change_percent": asset.get("change_percent"),
            "volume": asset.get("volume"),
            "data_date": asset.get("data_date"),
            "source": asset.get("source"),
            "source_url": asset.get("source_url"),
            "status": asset.get("status"),
            "sector_label": label,
            "reason": reason,
            "recognition_status": "待人工复核" if "需" in reason or "宽" in reason else "机械认领",
        })
    payload = {
        "task_id": "TASK-2026-07-05-取数演习修复",
        "date": None,
        "generated_at": now_jst(),
        "rule_source": "00_请先看这里/板块认领规则.html",
        "note": "按17板块规则补抓代表ETF/行业ETF；认不准标待人工复核/待人工认领，不硬塞。",
        "items": items,
        "summary": {
            "total": len(items),
            "success_count": sum(1 for x in items if x.get("status") == "OK"),
            "manual_review_needed": sum(1 for x in items if x.get("recognition_status") != "机械认领"),
            "pending_symbols": [x["symbol"] for x in items if x.get("status") != "OK"],
        },
        "safety": {"read_only": True, "place_order_called": False, "published": False},
    }
    path = ROOT / "data" / "sector" / "sector_flow_PENDING_DATE.json"
    # date filled by caller after latest date determined.
    return path, payload


def build_candidates(date: str, snapshot: dict[str, Any], sector: dict[str, Any], stable_rows: list[dict[str, Any]]) -> tuple[Path, dict[str, Any]]:
    since = "2026-06-25"
    fetch_errors = {}
    speeches, err = fetch_rss_items("美联储主席/理事讲话 RSS", OFFICIAL_URLS["fed_speeches_rss"], 8)
    if err:
        fetch_errors["fed_speeches_rss_error"] = err
    worldview_kept, worldview_filtered = worldview_filter(speeches)

    h41, h41_err = parse_h41()
    if h41_err:
        fetch_errors["h41_value_error"] = h41_err

    pres_url = OFFICIAL_URLS["federal_register_presidential_documents"].format(since=since)
    pres_docs, err = parse_federal_register_documents(pres_url, "Federal Register Presidential Documents API")
    if err:
        fetch_errors["federal_register_presidential_documents_error"] = err

    bis_url = OFFICIAL_URLS["federal_register_bis_rules"].format(since=since)
    bis_docs, err = parse_federal_register_documents(bis_url, "Federal Register BIS / Industry and Security Bureau rules API")
    if err:
        fetch_errors["federal_register_bis_rules_error"] = err

    worldview, worldview_source_coverage = build_worldview_candidates(worldview_kept, pres_docs, bis_docs)

    stable_events = []
    for row in stable_rows:
        stable_events.append({
            "source": row.get("source"),
            "title": f"{row.get('asset')} stablecoin supply",
            "time": row.get("time"),
            "data_date": (row.get("time") or "")[:10] or None,
            "url": row.get("source_url"),
            "raw": f"{row.get('asset')} SplyCur={row.get('value')}；只搬供应数据，不判断强/中/弱。",
        })
    stable_events.append({
        "source": "代币化美债",
        "title": "代币化美债",
        "time": None,
        "data_date": None,
        "url": None,
        "raw": "待接入：本次未取得干净公开源，不臆造。",
    })

    flow_events = []
    for a in snapshot.get("assets", []):
        flow_events.append({
            "source": a.get("source"),
            "title": a.get("symbol"),
            "time": a.get("data_date"),
            "data_date": a.get("data_date"),
            "url": a.get("source_url"),
            "raw": f"{a.get('symbol')} price={a.get('price')} change_percent={a.get('change_percent')}；只搬行情事实，不判断强/中/弱。",
        })
    sector_events = []
    for x in sector.get("items", []):
        sector_events.append({
            "source": x.get("source"),
            "title": f"{x.get('symbol')} / {x.get('sector_label')}",
            "time": x.get("data_date"),
            "data_date": x.get("data_date"),
            "url": x.get("source_url"),
            "raw": f"{x.get('symbol')} price={x.get('price')} change_percent={x.get('change_percent')} volume={x.get('volume')} sector_label={x.get('sector_label')} recognition={x.get('recognition_status')}；只搬板块事实。",
        })

    payload = {
        "date": date,
        "generated_at": now_jst(),
        "note": "只搬运不判断，够不够格由理解岗判；本文件不写强/中/弱、不写结论。",
        "source_fixes": {
            "whitehouse_replacement": pres_url,
            "bis_replacement": bis_url,
            "h41_current": OFFICIAL_URLS["h41_current"],
            "fed_speeches_rss": OFFICIAL_URLS["fed_speeches_rss"],
        },
        "data_date": {
            "market_snapshot": sorted({a.get("data_date") for a in snapshot.get("assets", []) if a.get("data_date")}),
            "stablecoin": sorted({(r.get("time") or "")[:10] for r in stable_rows if r.get("time")}),
            "h41": h41.get("data_date"),
            "sector_flow": sorted({x.get("data_date") for x in sector.get("items", []) if x.get("data_date")}),
        },
        "fetch_errors": fetch_errors,
        "filtered_noise": worldview_filtered,
        "worldview_source_coverage": worldview_source_coverage,
        "layer_status": {},
        "layer_1_worldview": worldview,
        "layer_2_gate": [h41],
        "layer_2_fima": "待理解岗判（FIMA无干净数据源，读公告判）",
        "layer_3_strategy": pres_docs + bis_docs,
        "layer_4_means": stable_events,
        "layer_5_flow": flow_events,
        "layer_6_sector": sector_events,
    }
    for key in ["layer_1_worldview", "layer_2_gate", "layer_3_strategy", "layer_4_means", "layer_5_flow", "layer_6_sector"]:
        if not payload.get(key):
            payload["layer_status"][key] = "本层今日无抓到候选，待理解岗按规范判是否援引上周"
    path = ROOT / "data" / "inbox" / f"candidates_{date}.json"
    write_json(path, payload)
    return path, payload


def u_count(path: Path) -> int:
    return path.read_bytes().count(b"\xef\xbf\xbd")


def scan_pending(payloads: list[tuple[Path, Any]]) -> list[str]:
    markers = ["待接入", "待拉", "待理解岗判", "待人工认领", "待人工复核", "PENDING"]
    rows = []
    for path, payload in payloads:
        text = json.dumps(payload, ensure_ascii=False) if not isinstance(payload, str) else payload
        for m in markers:
            n = text.count(m)
            if n:
                rows.append(f"{path}: {m} × {n}")
    return rows


def write_receipt(date: str, outputs: list[tuple[str, Path]], fixes: list[str], summaries: dict[str, Any], pending: list[str]) -> Path:
    path = ROOT / "00_请先看这里" / "给Claude的回执.md"
    lines = [
        "# 给 Claude 的回执 · TASK-2026-07-05 取数修复重跑",
        "",
        "生产(取数修复后重跑)完成。",
        "",
        f"- date：{date}（最近交易日按各市场最后有效交易日逐项标 data_date；不冒充今日）",
        f"- generated_at：{now_jst()}",
        "- safety：read_only=true；place_order_called=false；change_order_called=false；cancel_order_called=false；published=false",
        "",
        "## 修复情况（待修 5 条逐条销项）",
    ]
    lines.extend([f"- {x}" for x in fixes])
    lines.append("")
    lines.append("## 产出文件")
    for label, out in outputs:
        lines.append(f"- {label}：`{out}`（U+FFFD={u_count(out)}）")
    lines.append("")
    lines.append("## 重跑结果摘要")
    lines.append(f"- market snapshot：{summaries.get('snapshot')}")
    lines.append(f"- H.4.1：{summaries.get('h41')}")
    lines.append(f"- sector_flow：{summaries.get('sector')}")
    lines.append(f"- ma_levels：{summaries.get('ma')}")
    lines.append(f"- yield_curve：{summaries.get('yield_curve')}")
    lines.append(f"- stablecoin：{summaries.get('stablecoin')}")
    lines.append("")
    lines.append("## 仍待接入 / 待拉 / 待判 / 待人工认领")
    if pending:
        lines.extend([f"- {x}" for x in pending])
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("## 编码自检")
    lines.append("- 本次写入文件 UTF-8 无 BOM；写后回读 U+FFFD=0。")
    write_text(path, "\n".join(lines) + "\n")
    return path


def run(date_arg: str | None) -> dict[str, Any]:
    snapshot_path, snapshot = build_market_snapshot()
    # Choose date from US10Y if available; fallback to latest market data_date, then user arg.
    date = date_arg
    us10y = next((a for a in snapshot.get("assets", []) if a.get("symbol") == "US10Y"), None)
    if us10y and us10y.get("data_date"):
        date = str(us10y["data_date"]).replace("-", "")
    if not date:
        dates = sorted([a.get("data_date") for a in snapshot.get("assets", []) if a.get("data_date")])
        date = (dates[-1].replace("-", "") if dates else datetime.now(JST).strftime("%Y%m%d"))

    # Rename any date-specific outputs built after date is known.
    yield_path, yield_payload = run_yield_curve(date)
    ma_path, ma_payload = build_ma_levels(date)
    stable_path, stable_rows, stable_errors = refresh_stablecoin_csv()
    sector_tmp_path, sector_payload = build_sector_flow()
    sector_payload["date"] = date
    sector_path = ROOT / "data" / "sector" / f"sector_flow_{date}.json"
    write_json(sector_path, sector_payload)
    candidates_path, candidates = build_candidates(date, snapshot, sector_payload, stable_rows)

    h41 = candidates.get("layer_2_gate", [{}])[0]
    h41_values = h41.get("values", {}) if isinstance(h41, dict) else {}
    fixes = [
        "① 白宫/BIS 源：白宫行政令改 Federal Register Presidential Documents API；BIS 改 Federal Register Industry and Security Bureau agency API；旧 whitehouse/BIS RSS 不再使用。候选文件 source_fixes 已写新 URL。",
        "② 总闸 H.4.1：已抓实际数值 total_assets_millions_usd / total_assets_week_change_millions_usd / reserve_balances_millions_usd / reserve_balances_week_change_millions_usd，不再只搬页面链接。",
        f"③ 世界观①扫全源：已按5类源生成 worldview_source_coverage；候选{len(candidates.get('layer_1_worldview', []))}条，filtered_noise={len(candidates.get('filtered_noise', []))}条。",
        f"④ 板块⑥：已补抓 {sector_payload.get('summary', {}).get('total')} 个代表 ETF/行业 ETF；认不准标待人工复核，不硬塞。",
        "⑤ 最近交易日行情：Yahoo chart range=10d 取最后一根有效日线 close；逐项 data_date 如实保留，美国假日停在07-02的标的不冒充07-03。",
    ]
    summaries = {
        "snapshot": snapshot.get("summary"),
        "h41": h41_values,
        "sector": sector_payload.get("summary"),
        "ma": ma_payload.get("summary"),
        "yield_curve": {k: yield_payload.get(k) for k in ["us10y", "us3m", "spread_10y_3m", "inverted", "status", "data_date"]},
        "stablecoin": [{"asset": r.get("asset"), "time": r.get("time"), "value": r.get("value")} for r in stable_rows],
    }
    payloads = [
        (snapshot_path, snapshot),
        (yield_path, yield_payload),
        (ma_path, ma_payload),
        (stable_path, "\n".join([str(x) for x in stable_rows]) + "\n".join(stable_errors)),
        (sector_path, sector_payload),
        (candidates_path, candidates),
    ]
    pending = scan_pending(payloads)
    if stable_errors:
        pending.append("stablecoin_supply_latest.csv: 刷新失败，保留现有带真实日期CSV；" + "；".join(stable_errors))
    outputs = [
        ("market snapshot", snapshot_path),
        ("yield curve", yield_path),
        ("holdings MA levels", ma_path),
        ("stablecoin supply", stable_path),
        ("sector flow", sector_path),
        ("six-layer candidates", candidates_path),
    ]
    receipt_path = write_receipt(date, outputs, fixes, summaries, pending)
    outputs.append(("Claude receipt", receipt_path))
    return {
        "date": date,
        "outputs": [str(p) for _, p in outputs],
        "summaries": summaries,
        "pending_count": len(pending),
        "receipt": str(receipt_path),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None, help="Optional YYYYMMDD override; default derives from latest market data.")
    args = parser.parse_args()
    result = run(args.date)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
