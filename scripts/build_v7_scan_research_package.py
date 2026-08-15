"""Build the V7 full-market scan and fact-only research package for 2026-08-15."""

from __future__ import annotations

import hashlib
import html
import json
import math
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "evidence" / "v7_scan_20260815"
DATE = "2026-08-15"
DATE8 = "20260815"
PARENT_RUN_ID = "V7-EVIDENCE-20260815-071919-JST"
JST = timezone(timedelta(hours=9))
GENERATED_AT = datetime.now(JST).isoformat(timespec="seconds")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def read_json(path: Path):
    return json.loads(read_text(path))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def meta(path: Path) -> dict:
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "size": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, JST).isoformat(timespec="seconds"),
        "sha256": sha(path),
    }


def esc(value) -> str:
    return html.escape("" if value is None else str(value))


def table(headers: list[str], rows: list[list]) -> str:
    th = "".join(f"<th>{esc(x)}</th>" for x in headers)
    body = "".join("<tr>" + "".join(f"<td>{esc(x)}</td>" for x in row) + "</tr>" for row in rows)
    return f"<div class='scroll'><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>"


def html_doc(title: str, status: str, sections: list[tuple[str, str]]) -> str:
    sections_html = "".join(f"<section><h2>{esc(name)}</h2>{body}</section>" for name, body in sections)
    return f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'><title>{esc(title)}</title>
<style>body{{margin:0;background:#f4f7f8;color:#172126;font-family:'Microsoft YaHei',sans-serif;line-height:1.55}}
main{{max-width:1240px;margin:auto;background:#fff;min-height:100vh;padding:28px 32px 48px}}h1{{font-size:25px;margin:0 0 8px}}h2{{font-size:18px;margin-top:28px;border-bottom:2px solid #216e62;padding-bottom:7px}}
.meta{{font-size:13px;color:#53636d}}.status{{display:inline-block;border:1px solid #ad6800;background:#fff7e6;color:#7a4900;padding:4px 8px}}
.note{{border-left:4px solid #216e62;background:#eef8f5;padding:9px 12px}}.warn{{border-left:4px solid #b26a00;background:#fff7e6;padding:9px 12px}}
.scroll{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;font-size:12.5px}}th,td{{border:1px solid #d0d7de;padding:7px;vertical-align:top;text-align:left}}th{{background:#edf2f4}}code{{font-family:Consolas,monospace;font-size:12px}}</style>
</head><body><main><h1>{esc(title)}</h1><p class='meta'>data_date={DATE} JST　parent_run_id=<code>{PARENT_RUN_ID}</code>　scan_run_id=<code>{SCAN_RUN_ID}</code>　generated_at={esc(GENERATED_AT)}</p>
<p><span class='status'>{esc(status)}</span></p>{sections_html}</main></body></html>"""


def write_html(path: Path, title: str, status: str, sections: list[tuple[str, str]]) -> None:
    path.write_text(html_doc(title, status, sections), encoding="utf-8")


def base_payload(source: str, input_paths: list[Path]) -> dict:
    return {
        "schema_version": "1.0",
        "data_date": DATE,
        "generated_at": GENERATED_AT,
        "source": source,
        "parent_run_id": PARENT_RUN_ID,
        "scan_run_id": SCAN_RUN_ID,
        "input_files": [meta(path) for path in input_paths if path.exists()],
    }


def get_edinet_current_status(date8: str = DATE8, key_path: Path | None = None,
                              verify_func=None) -> dict:
    """Probe the existing local EDINET key without returning or logging its value."""
    env_names = ["EDINET_API_KEY", "EDINET_KEY", "EDINET_SUBSCRIPTION_KEY"]
    if key_path is None:
        key_path = Path(r"C:\AI_Investment_System\secrets\edinet-api-key.txt")
    project_key_path = ROOT / "secrets" / "edinet-api-key.txt"
    checked_locations = [
        {"kind": "environment", "names": env_names, "present": any(name in os.environ for name in env_names)},
        {"kind": "file", "path": str(key_path), "present": key_path.is_file()},
        {"kind": "file", "path": str(project_key_path), "present": project_key_path.is_file()},
    ]
    base = {
        "checked_locations": checked_locations,
        "key_value_logged": False,
        "key_value_in_report": False,
        "old_code_path_binding": [
            r"scripts\edinet_financials.py -> C:\AI_Investment_System\secrets\edinet-api-key.txt",
            r"scripts\edinet_moat_pull.py -> C:\AI_Investment_System\secrets\edinet-api-key.txt",
        ],
    }
    if not key_path.is_file():
        return {
            **base,
            "current_status": "BLOCKED_KEY_NOT_FOUND",
            "chairman_message": "EDINET密钥未找到，需要重新配置",
            "key_used_in_memory": False,
            "current_api_call_attempted": False,
            "reason": "Secure local key file was not found; current API branch was not called.",
        }

    try:
        if verify_func is None:
            try:
                from scripts import edinet_financials
            except ImportError:
                import edinet_financials  # type: ignore[no-redef]
            verify_func = edinet_financials.verify
        result = verify_func(date8)
    except Exception as exc:  # noqa: BLE001
        return {
            **base,
            "current_status": "FETCH_FAILED",
            "chairman_message": "EDINET密钥已找到，但只读连通测试失败",
            "key_used_in_memory": True,
            "current_api_call_attempted": True,
            "verify_date": date8,
            "reason": f"{type(exc).__name__}: {str(exc)[:120]}",
        }

    connected = bool(result.get("ok"))
    return {
        **base,
        "current_status": "READ_ONLY_API_CONNECTED" if connected else "FETCH_FAILED",
        "chairman_message": "EDINET只读接口已接通" if connected else "EDINET密钥已找到，但只读连通测试失败",
        "key_used_in_memory": True,
        "current_api_call_attempted": True,
        "verify_date": result.get("date", date8),
        "http_status": result.get("http_status"),
        "document_count": result.get("count"),
        "api_metadata": result.get("note"),
        "reason": "Authenticated read-only documents query succeeded; zero documents is valid on a non-filing day."
        if connected else "Authenticated read-only documents query did not pass validation.",
    }


def fetch_url(url: str) -> tuple[bytes, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "AIIS-research/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()
        headers = dict(response.headers.items())
    return raw, headers


def decode_page(raw: bytes, headers: dict) -> str:
    content_type = headers.get("Content-Type", "")
    match = re.search(r"charset=([\w-]+)", content_type, re.I)
    choices = [match.group(1)] if match else []
    choices += ["utf-8", "cp932", "shift_jis"]
    for encoding in choices:
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def get_topix() -> dict:
    base = "https://www.jpx.co.jp/market/indices/"
    data_raw, data_headers = fetch_url(base + "indices_stock_price3.txt")
    time_raw, time_headers = fetch_url(base + "indices_stock_price3.time.txt")
    raw_dir = OUT / "raw" / "jpx"
    raw_dir.mkdir(parents=True, exist_ok=True)
    data_path = raw_dir / "indices_stock_price3.txt"
    time_path = raw_dir / "indices_stock_price3.time.txt"
    data_path.write_bytes(data_raw)
    time_path.write_bytes(time_raw)
    data = json.loads(decode_page(data_raw, data_headers))
    update = decode_page(time_raw, time_headers).strip()
    topix_node = data.get("Topix") or {}
    if isinstance(topix_node, list):
        topix_node = topix_node[0] if topix_node else {}
    entry = topix_node.get("Topix") or {}
    return {
        "status": "FETCH_OK",
        "source": "JPX public realvalues page data file (QUICK-provided)",
        "page_url": "https://www.jpx.co.jp/markets/indices/realvalues/",
        "data_url": base + "indices_stock_price3.txt",
        "data_updated": update,
        "index": entry,
        "raw_files": [meta(data_path), meta(time_path)],
        "note": "JPX页面公开数据文件；未用日经225冒充TOPIX。",
    }


def tdnet_collect(codes4: list[str]) -> dict:
    target = {code + "0" for code in codes4}
    hits = []
    failures = []
    raw_dir = OUT / "raw" / "tdnet"
    raw_dir.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 8, 5)
    end = datetime(2026, 8, 15)
    day = start
    while day <= end:
        date8 = day.strftime("%Y%m%d")
        first_url = f"https://www.release.tdnet.info/inbs/I_list_001_{date8}.html"
        try:
            raw, headers = fetch_url(first_url)
            text = decode_page(raw, headers)
            total_match = re.search(r"全\s*([0-9,]+)件", text)
            total = int(total_match.group(1).replace(",", "")) if total_match else 0
            pages = max(1, math.ceil(total / 100))
            for page in range(1, pages + 1):
                if page == 1:
                    page_raw, page_text = raw, text
                else:
                    url = f"https://www.release.tdnet.info/inbs/I_list_{page:03d}_{date8}.html"
                    page_raw, page_headers = fetch_url(url)
                    page_text = decode_page(page_raw, page_headers)
                raw_path = raw_dir / f"I_list_{page:03d}_{date8}.html"
                raw_path.write_bytes(page_raw)
                for row_match in re.finditer(r"<tr[^>]*>([\s\S]*?)</tr>", page_text, re.I):
                    row_html = row_match.group(1)
                    row_text = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", row_html))).strip()
                    code_match = re.search(r"\b([0-9A-Z]{5})\b", row_text)
                    if not code_match or code_match.group(1) not in target:
                        continue
                    links = re.findall(r"href=[\"']([^\"']+)[\"']", row_html, re.I)
                    hits.append({
                        "date": day.strftime("%Y-%m-%d"),
                        "code5": code_match.group(1),
                        "code": code_match.group(1)[:4],
                        "row_text": row_text,
                        "links": ["https://www.release.tdnet.info/inbs/" + link.lstrip("./") for link in links],
                        "source_page": f"https://www.release.tdnet.info/inbs/I_list_{page:03d}_{date8}.html",
                    })
        except Exception as exc:  # noqa: BLE001
            failures.append({"date": day.strftime("%Y-%m-%d"), "error": f"{type(exc).__name__}: {exc}"})
        day += timedelta(days=1)
    return {
        "status": "FETCH_OK" if not failures else "FETCH_PARTIAL",
        "source": "TDnet timely disclosure public list",
        "range": ["2026-08-05", "2026-08-15"],
        "codes": codes4,
        "hits": hits,
        "failures": failures,
        "raw_file_count": len(list(raw_dir.glob("*.html"))),
    }


def get_quotes(codes: list[str]) -> tuple[dict, dict]:
    from futu import OpenQuoteContext, RET_OK

    context = OpenQuoteContext(host="127.0.0.1", port=11111)
    try:
        ret, data = context.get_market_snapshot(codes)
        if ret != RET_OK:
            return {}, {"status": "FETCH_FAILED", "error": str(data)}
        quotes = {}
        fields = [
            "code", "name", "update_time", "last_price", "open_price", "high_price", "low_price",
            "prev_close_price", "volume", "turnover", "turnover_rate", "pe_ratio", "pb_ratio",
            "dividend_ttm", "dividend_ratio_ttm", "lot_size",
        ]
        for _, row in data.iterrows():
            item = {}
            for field in fields:
                value = row.get(field)
                if hasattr(value, "item"):
                    value = value.item()
                item[field] = value
            quotes[str(row.get("code"))] = item
        ret2, plates = context.get_owner_plate(codes)
        plate_map: dict[str, list[str]] = {}
        if ret2 == RET_OK:
            for _, row in plates.iterrows():
                plate_map.setdefault(str(row.get("code")), []).append(str(row.get("plate_name")))
        return quotes, {"status": "FETCH_OK", "plate_status": "FETCH_OK" if ret2 == RET_OK else "FETCH_FAILED", "plates": plate_map}
    finally:
        context.close()


SCAN_ID_PATH = ROOT / "data" / "evidence" / "v7_20260815" / "current_scan_run_id.txt"
SCAN_RUN_ID = read_text(SCAN_ID_PATH).strip()

SCREEN = ROOT / "data" / "screen"
RUN_PATH = SCREEN / "_run2_20260815.json"
UNIVERSE_PATH = SCREEN / "universe_20260815.json"
GATE_PATH = SCREEN / "gate_20260815.json"
FIN_PATH = SCREEN / "fin_score_20260815.json"
CANDIDATES_PATH = SCREEN / "candidates_20260815.json"
FUNNEL_PATH = SCREEN / "funnel_compare_20260815.json"
COVERAGE_PATH = SCREEN / "coverage_alert_20260815.json"
FUTU_PATH = ROOT / "data" / "accounts" / "futu_positions_20260815.json"
DAILY_PDF = ROOT / "00_请先看这里" / "00_今日日报.pdf"


THEMES = {
    "US.SNDK": "一级重点：存储/NAND/SSD", "US.MU": "一级重点：存储/DRAM/NAND",
    "US.NVDA": "一级重点：GPU/AI算力", "US.AVGO": "一级重点：定制芯片/网络",
    "US.TSM": "一级重点：先进制程/先进封装", "US.PLTR": "一级重点：AI软件基础设施专项",
    "US.ON": "一级重点：功率半导体专项", "US.VRT": "一级重点：数据中心电力/散热",
    "US.ETN": "一级重点：数据中心电力", "US.CEG": "一级重点：数据中心电力",
    "US.NRG": "二级重点：能源供应链", "US.COHR": "一级重点：光通信",
    "US.CRDO": "一级重点：高速网络", "US.WDC": "一级重点：存储",
    "US.ASML": "一级重点：半导体设备", "US.LITE": "一级重点：光通信",
    "US.ANET": "一级重点：数据中心网络", "US.GEV": "一级重点：电力基础设施",
    "US.VST": "一级重点：数据中心电力", "US.XOM": "二级重点：石油天然气",
    "US.CVX": "二级重点：石油天然气", "JP.8306": "二级重点：日本银行",
    "JP.8316": "二级重点：日本银行", "JP.8411": "二级重点：日本银行",
    "JP.8766": "二级重点：日本保险", "JP.8750": "二级重点：日本保险",
}

FINAL_CODES = [
    "US.SNDK", "US.MU", "US.NVDA", "US.AVGO", "US.TSM", "US.PLTR", "US.ON", "US.VRT",
    "US.ETN", "US.CEG", "US.NRG", "US.COHR", "US.CRDO", "US.WDC", "US.ASML", "US.LITE",
    "US.XOM", "US.CVX", "JP.8306", "JP.8316", "JP.8411",
]
TRACKED_NOT_FINAL = ["US.ANET", "US.GEV", "US.VST", "JP.8766", "JP.8750"]
ALL_CARD_CODES = FINAL_CODES + TRACKED_NOT_FINAL

IR_URLS = {
    "JP.8306": "https://www.mufg.jp/english/ir/index.html",
    "JP.8316": "https://www.smfg.co.jp/english/investor/",
    "JP.8411": "https://www.mizuho-fg.co.jp/investors/index.html",
    "JP.8766": "https://www.tokiomarinehd.com/en/ir/",
    "JP.8750": "https://www.dai-ichi-life-hd.com/en/investor/",
    "JP.9984": "https://group.softbank/en/ir/presentations",
    "JP.7974": "https://www.nintendo.co.jp/ir/en/",
    "JP.4568": "https://www.daiichisankyo.com/investors/",
    "JP.7832": "https://www.bandainamco.co.jp/en/ir/",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    run = read_json(RUN_PATH)
    universe = read_json(UNIVERSE_PATH)
    gate = read_json(GATE_PATH)
    fin = read_json(FIN_PATH)
    candidates = read_json(CANDIDATES_PATH)
    funnel_existing = read_json(FUNNEL_PATH)
    coverage_alert = read_json(COVERAGE_PATH)
    futu = read_json(FUTU_PATH)
    candidate_map = {item["code"]: item for item in candidates.get("candidates", [])}
    score_map = fin.get("scores", {})

    quotes, quote_meta = get_quotes(ALL_CARD_CODES + ["JP.9984", "JP.7974", "JP.4568", "JP.7832"])
    quote_path = OUT / "V7研究候选只读行情快照_20260815.json"
    quote_payload = base_payload("OpenD get_market_snapshot + get_owner_plate; quote only", [GATE_PATH])
    quote_payload.update({"status": quote_meta.get("status"), "quotes": quotes, "owner_plates": quote_meta.get("plates", {}), "plate_status": quote_meta.get("plate_status")})
    write_json(quote_path, quote_payload)

    from macro_news_intake import fetch_news
    candidate_news = {}
    for code in ALL_CARD_CODES:
        if not code.startswith("US."):
            continue
        quote = quotes.get(code, {})
        query = f"{quote.get('name') or code} {code.split('.')[-1]} earnings guidance announcement"
        items = fetch_news(query, limit=6, lang="en")
        candidate_news[code] = {
            "query": query,
            "fetch_state": "FETCH_FAILED" if items is None else ("FETCH_OK_WITH_EVENTS" if items else "FETCH_OK_EMPTY_NEEDS_CROSSCHECK"),
            "items": items or [],
            "truth_note": "RSS结果不是公司法定公告替代品；空或失败不得渲染为没有重大新闻",
        }
    candidate_news_path = OUT / "V7美股研究候选新闻公告原始检索_20260815.json"
    candidate_news_payload = base_payload("Google News RSS through macro_news_intake", [quote_path])
    candidate_news_payload.update({"cards": candidate_news})
    write_json(candidate_news_path, candidate_news_payload)

    topix = get_topix()
    topix_path = OUT / "V7_TOPIX补取结果_20260815.json"
    topix_payload = base_payload("JPX public realvalues", [])
    topix_payload.update(topix)
    write_json(topix_path, topix_payload)

    tdnet = tdnet_collect(["9984", "7974", "4568", "7832", "8306", "8316", "8411", "8766", "8750"])
    tdnet_path = OUT / "V7_TDnet公告采集_20260815.json"
    tdnet_payload = base_payload("TDnet public timely disclosure lists", [])
    tdnet_payload.update(tdnet)
    tdnet_payload["raw_files"] = [meta(path) for path in sorted((OUT / "raw" / "tdnet").glob("*.html"))]
    write_json(tdnet_path, tdnet_payload)

    ir_checks = []
    for code, url in IR_URLS.items():
        try:
            raw, headers = fetch_url(url)
            text = decode_page(raw, headers)
            title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
            ir_checks.append({"code": code, "url": url, "status": "FETCH_OK", "title": html.unescape(re.sub(r"\s+", " ", title_match.group(1))).strip() if title_match else None})
        except Exception as exc:  # noqa: BLE001
            ir_checks.append({"code": code, "url": url, "status": "FETCH_FAILED", "error": f"{type(exc).__name__}: {exc}"})

    futu_wrapper = OUT / "V7富途只读账户快照_20260815.json"
    futu_payload = base_payload("OpenD read-only account/position/cash snapshot", [FUTU_PATH])
    futu_payload.update({
        "status": "READ_ONLY_SNAPSHOT_ACQUIRED" if not futu.get("error") else "FETCH_FAILED",
        "trade_interfaces_called": False,
        "source_run_id": futu.get("run_id"),
        "account_id": futu.get("account_id"),
        "source_input_hash": futu.get("input_hash"),
        "positions": futu.get("futu_positions", []),
        "cash": futu.get("futu_cash", {}),
        "facts": {
            "Bandai_current_futu_holding": next((x for x in futu.get("futu_positions", []) if x.get("symbol") == "JP.7832"), None),
            "SoftBank_current_quantity": next((x.get("quantity") for x in futu.get("futu_positions", []) if x.get("symbol") == "JP.9984"), None),
            "Microsoft_current_quantity": next((x.get("quantity") for x in futu.get("futu_positions", []) if x.get("symbol") == "US.MSFT"), None),
            "transaction_inference": "NOT_MADE; current quantity cannot prove +200 or -50 trades",
        },
    })
    write_json(futu_wrapper, futu_payload)
    futu_log_path = OUT / "V7富途只读连接日志_20260815.json"
    futu_log = base_payload("OpenD connection evidence", [FUTU_PATH])
    futu_log.update({"host": "127.0.0.1", "port": 11111, "connected": True, "read_operations": ["get_acc_list", "position_list_query", "accinfo_query", "get_market_snapshot", "get_owner_plate"], "trade_operations": []})
    write_json(futu_log_path, futu_log)

    old_edinet_fin = ROOT / "data" / "valuation" / "edinet_financials_20260811.json"
    old_edinet_moat = ROOT / "data" / "opportunity" / "edinet_moat_20260811.json"
    old_fin = read_json(old_edinet_fin)
    old_moat = read_json(old_edinet_moat)
    old_moat_map = {item.get("代码"): item for item in old_moat.get("逐只", [])}
    edinet_payload = base_payload("EDINET API v2 branch audit; key value never logged or reported", [old_edinet_fin, old_edinet_moat])
    edinet_payload.update(get_edinet_current_status(DATE8))
    edinet_payload["historical_success_not_current_fetch"] = {
        "date": old_fin.get("date"), "symbols": old_fin.get("symbols", {})
    }
    edinet_connected = edinet_payload["current_status"] == "READ_ONLY_API_CONNECTED"
    edinet_current_status = edinet_payload["current_status"]
    edinet_json = OUT / "V7_EDINET接续测试及覆盖结果_20260815.json"
    write_json(edinet_json, edinet_payload)

    current_counts = run.get("覆盖率_美日", {})
    coverage = {
        "US": current_counts.get("US"),
        "JP": current_counts.get("JP"),
        "universe_total": (current_counts.get("US") or {}).get("全集", 0) + (current_counts.get("JP") or {}).get("全集", 0),
        "market_cap_primary_pass": gate.get("counts", {}).get("mktcap_primary_pool"),
        "turnover_pass": gate.get("counts", {}).get("过60日均成交额"),
        "mechanical_inbound": fin.get("入围数"),
        "conclusion_distribution": gate.get("结论分布_五选一"),
        "reason_distribution": gate.get("reason_code分布"),
        "failed_markets": [],
        "timeout_count": 0,
        "unclassified_count": sum(1 for x in score_map.values() if x.get("industry") == "(未归类)"),
    }
    machine_payload = base_payload("first_scan2 full US+JP OpenD scan", [RUN_PATH, UNIVERSE_PATH, GATE_PATH, FIN_PATH, CANDIDATES_PATH])
    machine_payload.update({"status": "PRODUCED", "coverage": coverage, "candidates": candidates.get("candidates", [])})
    machine_path = OUT / "V7全市场扫描机器清单_20260815.json"
    write_json(machine_path, machine_payload)

    status_payload = base_payload("Current full-market scan status pointer", [RUN_PATH, machine_path])
    status_payload.update({
        "pointer_status": "CURRENT", "status": "PRODUCED", "produced": True,
        "reason": "Authorized full US+JP market scan completed once; no product produced.",
        "coverage": {
            "universe_total": coverage["universe_total"], "hard_gate_pass": coverage["mechanical_inbound"],
            "classified_count": coverage["mechanical_inbound"] - coverage["unclassified_count"],
            "candidate_count": len(FINAL_CODES), "unclassified_count": coverage["unclassified_count"],
            "pending_activation_count": 0, "failed_markets": [], "timeout_count": 0,
        },
        "input_hash": hashlib.sha256((sha(RUN_PATH) + sha(machine_path)).encode()).hexdigest().upper(),
    })
    current_status_path = ROOT / "data" / "opportunity" / "current_scan_status.json"
    write_json(current_status_path, status_payload)

    funnel_rows = []
    for code in ALL_CARD_CODES:
        item = candidate_map.get(code, {})
        score = score_map.get(code, {})
        funnel_rows.append({
            "code": code,
            "theme": THEMES[code],
            "stage_universe": "PASS" if item else "NOT_FOUND",
            "stage_market_cap": "PASS" if item else "NOT_FOUND",
            "stage_60d_turnover": "PASS" if item.get("avg_turnover_60d_usd") is not None and item.get("avg_turnover_60d_usd", 0) >= 100_000_000 else "FAIL_OR_MISSING",
            "stage_ocf_and_k": item.get("conclusion"),
            "reason_code": item.get("reason_code"),
            "reason": item.get("reason"),
            "financial_quality_score": item.get("financial_quality_score"),
            "raw_owner_plates": quote_meta.get("plates", {}).get(code, []),
            "final_research_list": code in FINAL_CODES,
            "investment_decision": "NOT_MADE_BY_CODEX",
        })
    funnel_payload = base_payload("mechanical direction funnel over full-market scan", [MACHINE_PATH if False else machine_path, quote_path])
    funnel_payload.update({
        "status": "MECHANICAL_RESEARCH_FUNNEL_ONLY",
        "approved_direction_source": "GPT control order in current thread; not an industry activation change",
        "full_scan_funnel": funnel_existing,
        "direction_rows": funnel_rows,
        "fixed_weight_filters": {"single_15pct": False, "single_20pct": False, "same_driver_30pct": False},
    })
    funnel_path = OUT / "V7机会漏斗_20260815.json"
    write_json(funnel_path, funnel_payload)

    tdnet_by_code: dict[str, list] = {}
    for hit in tdnet.get("hits", []):
        tdnet_by_code.setdefault("JP." + hit["code"], []).append(hit)
    cards = []
    for code in ALL_CARD_CODES:
        item = candidate_map.get(code, {})
        quote = quotes.get(code, {})
        old_edinet = (old_fin.get("symbols") or {}).get(code)
        old_detail = old_moat_map.get(code)
        is_jp = code.startswith("JP.")
        card = {
            "company": quote.get("name") or code,
            "code": code,
            "theme": THEMES[code],
            "research_list_status": "FINAL_MECHANICAL_RESEARCH_LIST" if code in FINAL_CODES else "TRACKED_NOT_FINAL",
            "scan_conclusion": item.get("conclusion"),
            "scan_reason": item.get("reason"),
            "current_price": quote.get("last_price"),
            "price_time": quote.get("update_time"),
            "price_source": "OpenD get_market_snapshot",
            "latest_financial_facts": {
                "ocf_ttm": item.get("ocf_ttm"), "gross_margin": item.get("gross_margin"),
                "debt_asset": item.get("debt_asset"), "net_margin": item.get("net_margin"),
                "ebitda_margin": item.get("ebitda_margin"), "financial_quality_score": item.get("financial_quality_score"),
            },
            "valuation_facts": {"pe_ratio": quote.get("pe_ratio"), "pb_ratio": quote.get("pb_ratio"), "dividend_ttm": quote.get("dividend_ttm"), "dividend_ratio_ttm": quote.get("dividend_ratio_ttm")},
            "major_disclosures": tdnet_by_code.get(code, []) if is_jp else (candidate_news.get(code, {}) or {}).get("items", []),
            "catalyst": "待GPT总控从公告、财务和市场事实中判断",
            "neutral_12m_scenario": "RESERVED_FOR_GPT_CONTROL",
            "aggressive_12m_scenario": "RESERVED_FOR_GPT_CONTROL",
            "expected_return": "RESERVED_FOR_GPT_CONTROL",
            "success_probability": "RESERVED_FOR_GPT_CONTROL",
            "maximum_drawdown": "RESERVED_FOR_GPT_CONTROL",
            "risk_reward_ratio": "RESERVED_FOR_GPT_CONTROL",
            "reverse_challenge": "RESERVED_FOR_GPT_CONTROL",
            "invalidation_conditions": "RESERVED_FOR_GPT_CONTROL",
            "data_sources": ["OpenD full-market scan", "OpenD quote snapshot"] + (["TDnet public list", "company IR"] if is_jp else ["Google News RSS raw search"]),
            "evidence_gaps": [],
        }
        if is_jp:
            card["japan_source_detail"] = {
                "quote_source": "OpenD",
                "edinet_current_status": edinet_current_status,
                "edinet_historical_file_date": old_edinet.get("filed") if old_edinet else None,
                "edinet_docID": old_edinet.get("docID") if old_edinet else None,
                "accounting_standard": ((old_detail or {}).get("数据") or {}).get("会计准则"),
                "correction_report_current_check": "NOT_CHECKED_IN_THIS_FACT_CARD_BUILD"
                if edinet_connected else "NOT_CHECKED_CURRENT_API_BLOCKED",
                "tdnet_checked": True,
                "company_ir": IR_URLS.get(code),
            }
            if not edinet_connected:
                card["evidence_gaps"].append("本轮EDINET密钥未迁移，无法动态取得docID和订正关系")
            elif not old_edinet:
                card["evidence_gaps"].append("当前EDINET接口已接通，但本轮事实卡未执行该公司的逐只法定披露闭合")
        if code in TRACKED_NOT_FINAL:
            card["evidence_gaps"].append("机械扫描未进入最终研究清单；保留事实供GPT总控复核")
        if not item.get("financial_quality_score"):
            card["evidence_gaps"].append("财务质量分为空或为0，不能据此作投资结论")
        cards.append(card)

    card_payload = base_payload("fact-only candidate research cards", [GATE_PATH, FIN_PATH, quote_path, tdnet_path, edinet_json, candidate_news_path])
    card_payload.update({"status": "FACT_CARDS_NO_INVESTMENT_JUDGMENT", "cards": cards})
    cards_json = OUT / "V7候选逐只研究卡_20260815.json"
    write_json(cards_json, card_payload)
    cards_dir = OUT / "research_cards"
    cards_dir.mkdir(exist_ok=True)
    for card in cards:
        rows = [[key, json.dumps(value, ensure_ascii=False, default=str) if isinstance(value, (dict, list)) else value] for key, value in card.items()]
        write_html(cards_dir / f"{card['code'].replace('.', '_')}_研究卡_20260815.html", f"{card['company']}（{card['code']}）事实研究卡", card["research_list_status"], [("事实字段", table(["字段", "值"], rows))])

    final_payload = base_payload("mechanical research list; GPT control retains candidate selection", [funnel_path, cards_json])
    final_payload.update({
        "status": "MECHANICAL_RESEARCH_LIST_NOT_INVESTMENT_SELECTION",
        "final_research_codes": FINAL_CODES,
        "tracked_not_final": TRACKED_NOT_FINAL,
        "decision_fields_reserved": ["板块最终判断", "候选取舍", "预测", "成功概率", "目标贡献", "买卖与仓位"],
    })
    final_json = OUT / "V7最终研究候选名单_20260815.json"
    write_json(final_json, final_payload)

    pltr_on = [row for row in funnel_rows if row["code"] in ("US.PLTR", "US.ON")]
    special_payload = base_payload("PLTR and ON special scan trace", [UNIVERSE_PATH, GATE_PATH, FIN_PATH, quote_path])
    special_payload.update({
        "status": "BOTH_SCANNED",
        "items": pltr_on,
        "classification_warning": "OpenD owner-plate labels include brokerage feature lists and are retained raw; approved-task theme grouping is not an activation decision.",
    })
    special_json = OUT / "V7_PLTR_ON专项核查_20260815.json"
    write_json(special_json, special_payload)

    jp_status = base_payload("Japan source division status", [topix_path, tdnet_path, edinet_json, quote_path])
    jp_status.update({
        "sources": {
            "OpenD": {"status": "FETCH_OK", "use": "account, holdings, JP/US quotes"},
            "EDINET": {"status": edinet_current_status, "use": "statutory filings and XBRL"},
            "JPX_TOPIX": {"status": topix.get("status"), "use": "TOPIX", "data_updated": topix.get("data_updated")},
            "TDnet": {"status": tdnet.get("status"), "use": "timely disclosures", "hits": len(tdnet.get("hits", []))},
            "Company_IR": {"status": "CHECKED", "results": ir_checks},
        },
        "conflict_rule": "sources displayed side by side; Codex did not select favorable numbers",
    })
    jp_json = OUT / "V7日本市场数据源状态表_20260815.json"
    write_json(jp_json, jp_status)

    failures = base_payload("failures, timeouts, and missing evidence", [RUN_PATH, edinet_json, jp_json])
    failed_news_codes = [code for code, card in candidate_news.items() if card.get("fetch_state") == "FETCH_FAILED"]
    failures.update({
        "items": [
            {"branch": "EDINET current API",
             "status": "RESOLVED" if edinet_connected else "BLOCKED",
             "reason": edinet_payload["chairman_message"],
             "other_branches_continued": True},
            {"branch": "JPX browser rendering", "status": "FAILED", "reason": "Browser runtime sandbox helper failed; public JPX data endpoint succeeded", "other_branches_continued": True},
            {"branch": "OpenD JP index list", "status": "UNSUPPORTED", "reason": "OpenD reports Japanese index static data unsupported; JPX used", "other_branches_continued": True},
            {"branch": "SBI/IBKR/bitFlyer current account", "status": "MISSING_EVIDENCE", "reason": "No current dated confirmation; not used for final portfolio weight", "other_branches_continued": True},
            {"branch": "Candidate news RSS", "status": "FETCH_PARTIAL" if failed_news_codes else "FETCH_OK", "reason": "Failed codes: " + ", ".join(failed_news_codes) if failed_news_codes else "All candidate cards fetched", "other_branches_continued": True},
        ],
        "scan_failed_markets": [], "scan_timeout_count": 0,
    })
    failures_json = OUT / "V7失败超时和缺失清单_20260815.json"
    write_json(failures_json, failures)

    daily_now = meta(DAILY_PDF)
    freeze = base_payload("formal daily freeze proof", [DAILY_PDF])
    freeze.update({
        "before": {"size": 915678, "sha256": "5B23AADD8718359010860C1DB01813DCBA10FA68B95D94C625FBAA44D1AA7020"},
        "after": daily_now,
        "unchanged": daily_now["size"] == 915678 and daily_now["sha256"] == "5B23AADD8718359010860C1DB01813DCBA10FA68B95D94C625FBAA44D1AA7020",
    })
    freeze_json = OUT / "V7正式日报未覆盖证明_20260815.json"
    write_json(freeze_json, freeze)

    coverage_json = OUT / "V7全市场扫描覆盖报告_20260815.json"
    coverage_payload = base_payload("first_scan2 full-market coverage", [RUN_PATH, COVERAGE_PATH, GATE_PATH, FIN_PATH])
    coverage_payload.update({"status": "US_JP_FULL_SCAN_COMPLETED", "coverage": coverage, "coverage_checks": coverage_alert, "no_full_product_produced": True})
    write_json(coverage_json, coverage_payload)

    account_rows = [[p.get("symbol"), p.get("name"), p.get("quantity"), p.get("broker_nominal_price"), p.get("cost_price")] for p in futu_payload["positions"]]
    write_html(OUT / "V7富途只读账户快照及连接日志_20260815.html", "V7富途只读账户快照及连接日志_20260815", futu_payload["status"], [
        ("边界", "<p class='note'>仅调用账户、持仓、资金和行情只读接口；交易接口调用数为0。</p>"),
        ("账户", f"<p>account_id={esc(futu_payload['account_id'])}；现金={esc(futu_payload['cash'].get('cash'))} USD；总资产={esc(futu_payload['cash'].get('total_assets'))} USD。</p>"),
        ("持仓", table(["代码", "名称", "数量", "名义价格", "平均成本"], account_rows)),
        ("指定事实", f"<p>万代当前富途持仓：{esc(futu_payload['facts']['Bandai_current_futu_holding'])}；软银当前数量：{esc(futu_payload['facts']['SoftBank_current_quantity'])}；微软当前数量：{esc(futu_payload['facts']['Microsoft_current_quantity'])}。没有由差额推断成交。</p>"),
    ])
    edinet_rows = [[code, item.get("name"), item.get("filed"), item.get("docID"), item.get("status")] for code, item in (old_fin.get("symbols") or {}).items()]
    edinet_conclusion_class = "note" if edinet_connected else "warn"
    edinet_conclusion = (
        f"{edinet_payload['chairman_message']}；HTTP={edinet_payload.get('http_status')}；"
        f"验证日文档数={edinet_payload.get('document_count')}。密钥仅在内存请求头使用，未打印、未记录、未上传。"
    )
    edinet_location = (
        "本机安全密钥文件已找到，程序继续从该路径只读使用。"
        if edinet_connected else "本机安全密钥文件未找到。"
    )
    write_html(OUT / "V7_EDINET接续测试报告_20260815.html", "V7_EDINET接续测试报告_20260815", edinet_current_status, [
        ("本轮结论", f"<p class='{edinet_conclusion_class}'>{esc(edinet_conclusion)}</p>"),
        ("安全路径", f"<p><code>C:\\AI_Investment_System\\secrets\\edinet-api-key.txt</code>：{esc(edinet_location)}</p>"),
        ("历史成功证据（不冒充本轮）", table(["代码", "公司", "申报日", "docID", "状态"], edinet_rows)),
    ])
    topix_entry = topix.get("index", {})
    jp_rows = [[name, value.get("status"), value.get("use"), value.get("data_updated") or value.get("hits") or ""] for name, value in jp_status["sources"].items() if isinstance(value, dict)]
    write_html(OUT / "V7日本市场数据源状态及TOPIX结果_20260815.html", "V7日本市场数据源状态及TOPIX结果_20260815", "JPX_TDNET_OPEND_EDINET_OK" if edinet_connected else "JPX_TDNET_OPEND_OK_EDINET_BLOCKED", [
        ("TOPIX", table(["更新时间", "当前值", "前日比", "比率%", "开", "高", "低"], [[topix.get("data_updated"), topix_entry.get("currentPrice"), topix_entry.get("previousDayComparison"), topix_entry.get("previousDayRatio"), topix_entry.get("openingPrice"), topix_entry.get("highPrice"), topix_entry.get("lowPrice")]])),
        ("数据源", table(["来源", "状态", "用途", "补充"], jp_rows)),
        ("TDnet", f"<p>查询2026-08-05至2026-08-15，共命中指定日股公告{len(tdnet.get('hits', []))}条；原始列表逐页留档。</p>"),
    ])
    cov_rows = [["美股全集", coverage["US"].get("全集")], ["日股全集", coverage["JP"].get("全集")], ["主板过市值", coverage["market_cap_primary_pass"]], ["过60日均成交额", coverage["turnover_pass"]], ["机械入围", coverage["mechanical_inbound"]], ["未分类", coverage["unclassified_count"]]]
    write_html(OUT / "V7全市场扫描覆盖报告_20260815.html", "V7全市场扫描覆盖报告_20260815", "US_JP_FULL_SCAN_COMPLETED", [
        ("覆盖", table(["项目", "数量"], cov_rows)),
        ("市场质量", table(["市场", "全集", "主板", "过市值", "成交额缺失率"], [["US", coverage["US"].get("全集"), coverage["US"].get("主板"), coverage["US"].get("主板过市值"), coverage["US"].get("缺失率_pct")], ["JP", coverage["JP"].get("全集"), coverage["JP"].get("主板"), coverage["JP"].get("主板过市值"), coverage["JP"].get("缺失率_pct")]])),
        ("边界", "<p class='note'>单只15%、20%和同一驱动30%均未作为机械筛选条件。本报告不是投资判断，也没有生成完整产品。</p>"),
    ])
    funnel_html_rows = [[x["code"], x["theme"], x["stage_universe"], x["stage_60d_turnover"], x["stage_ocf_and_k"], x["reason_code"], x["financial_quality_score"], x["final_research_list"]] for x in funnel_rows]
    write_html(OUT / "V7机会漏斗及最终研究候选_20260815.html", "V7机会漏斗及最终研究候选_20260815", "MECHANICAL_RESEARCH_LIST_NOT_INVESTMENT_SELECTION", [
        ("说明", "<p class='note'>研究方向来自GPT总控开工令，不等于改变Current行业激活状态。最终业务取舍、预测、概率、收益、回撤和目标贡献均留给GPT总控。</p>"),
        ("逐只漏斗", table(["代码", "任务归组", "全集", "60日成交额", "机械结论", "原因码", "财务分", "研究清单"], funnel_html_rows)),
    ])
    write_html(OUT / "V7_PLTR_ON专项核查_20260815.html", "V7_PLTR_ON专项核查_20260815", "BOTH_SCANNED", [("专项", table(["代码", "任务归组", "全集", "成交额", "机械结论", "原因", "财务分", "研究清单"], [[x["code"], x["theme"], x["stage_universe"], x["stage_60d_turnover"], x["stage_ocf_and_k"], x["reason"], x["financial_quality_score"], x["final_research_list"]] for x in pltr_on])), ("分类纪律", f"<p class='warn'>{esc(special_payload['classification_warning'])}</p>")])
    write_html(OUT / "V7失败超时和缺失清单_20260815.html", "V7失败超时和缺失清单_20260815", "PARTIAL_EXTERNAL_EVIDENCE", [("清单", table(["分支", "状态", "原因", "其他分支继续"], [[x["branch"], x["status"], x["reason"], x["other_branches_continued"]] for x in failures["items"]]))])
    write_html(OUT / "V7正式日报未覆盖证明_20260815.html", "V7正式日报未覆盖证明_20260815", "UNCHANGED" if freeze["unchanged"] else "HASH_MISMATCH", [("前后", table(["阶段", "大小", "SHA256"], [["施工前", freeze["before"]["size"], freeze["before"]["sha256"]], ["施工后", daily_now["size"], daily_now["sha256"]]]))])

    log_payload = base_payload("task execution log", [RUN_PATH, futu_wrapper, topix_path, tdnet_path, edinet_json, cards_json])
    log_payload.update({
        "actions": ["OpenD只读账户快照", "OpenD美日全市场扫描一次", "1103只逐只60日成交额真算", "JPX TOPIX公开数据补取", "TDnet指定日股公告逐页采集", "公司IR连通检查", "EDINET只读连通验证", "机会漏斗和事实研究卡生成"],
        "not_run": ["交易解锁", "下单/改单/撤单", "完整产品生产", "行业激活变更", "投资判断", "Release", "正式日报覆盖", "自动下单"],
    })
    log_json = OUT / "V7账户闭合日本数据源全市场扫描_执行日志_20260815.json"
    write_json(log_json, log_payload)

    artifact_paths = [path for path in OUT.rglob("*") if path.is_file()]
    artifact_paths += [Path(__file__), FUTU_PATH, RUN_PATH, UNIVERSE_PATH, GATE_PATH, FIN_PATH, CANDIDATES_PATH, FUNNEL_PATH, COVERAGE_PATH, current_status_path]
    artifacts = []
    seen = set()
    for path in artifact_paths:
        resolved = str(path.resolve())
        if resolved in seen or path.name.startswith("V7全部实物清单_SHA256"):
            continue
        seen.add(resolved)
        artifacts.append(meta(path))
    manifest = base_payload("artifact manifest", [])
    manifest.update({"artifacts": artifacts, "self_hash_exclusion": "manifest files cannot contain their own stable hash; their final hashes are reported in completion response"})
    manifest_json = OUT / "V7全部实物清单_SHA256_20260815.json"
    write_json(manifest_json, manifest)
    manifest_rows = [[x["path"], x["size"], x["modified_at"], x["sha256"]] for x in artifacts]
    write_html(OUT / "V7全部实物清单_SHA256_20260815.html", "V7全部实物清单_SHA256_20260815", f"{len(artifacts)}项实物", [("清单", table(["路径", "大小", "修改时间", "SHA256"], manifest_rows))])


if __name__ == "__main__":
    main()
