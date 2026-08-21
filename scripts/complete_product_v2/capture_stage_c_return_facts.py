from __future__ import annotations

import argparse
import hashlib
import json
import ssl
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from futu import OpenQuoteContext, RET_OK


JST = timezone(timedelta(hours=9))

OPEND_SYMBOLS = [
    "JP.4063", "JP.4568", "JP.6758", "JP.6857", "JP.6954", "JP.7203",
    "JP.7974", "JP.8001", "JP.8306", "JP.8316", "JP.8411", "JP.8766",
    "JP.9984", "US.ASML", "US.AVGO", "US.CEG", "US.COHR", "US.COIN",
    "US.CRCL", "US.CRDO", "US.CVX", "US.ETN", "US.IBKR", "US.LITE",
    "US.META", "US.MSFT", "US.MSTR", "US.MU", "US.NRG", "US.NVDA",
    "US.ON", "US.PLTR", "US.SNDK", "US.SPCX", "US.TSM", "US.VRT",
    "US.WDC", "US.XOM", "US.MRVL",
]

EXTERNAL_SYMBOLS = {
    "BTC": "BTC-JPY", "ETH": "ETH-JPY", "KRX.005930": "005930.KS",
    "USDJPY": "JPY=X", "KRWJPY": "KRWJPY=X",
}

MACRO_SYMBOLS = {
    "S&P 500": "^GSPC", "Nasdaq Composite": "^IXIC", "Dow Jones": "^DJI",
    "Nikkei 225": "^N225", "TOPIX": "^TOPX", "USD/JPY": "JPY=X",
    "US 10Y yield": "^TNX", "US 30Y yield": "^TYX", "WTI crude": "CL=F",
    "Brent crude": "BZ=F", "Gold": "GC=F",
}


def now_jst() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def safe(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if isinstance(value, float) and value != value:
        return None
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def fetch_chart(symbol: str) -> dict[str, Any]:
    now = datetime.now(JST)
    query = urllib.parse.urlencode({
        "period1": int((now - timedelta(days=7)).timestamp()),
        "period2": int((now + timedelta(minutes=5)).timestamp()),
        "interval": "5m", "events": "history",
    })
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(symbol, safe="") + "?" + query
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=20, context=ssl.create_default_context()) as response:
        raw = response.read()
    result = json.loads(raw.decode("utf-8"))["chart"]["result"][0]
    timestamps = result.get("timestamp") or []
    closes = result.get("indicators", {}).get("quote", [{}])[0].get("close") or []
    pairs = [(timestamp, close) for timestamp, close in zip(timestamps, closes) if close is not None]
    if not pairs:
        raise RuntimeError("公开行情返回中没有可用价格")
    timestamp, close = pairs[-1]
    meta = result.get("meta", {})
    previous_close = meta.get("chartPreviousClose") or meta.get("previousClose")
    return {
        "source_url": url, "source": "Yahoo Finance chart public endpoint",
        "symbol": symbol, "price": float(close),
        "previous_close": float(previous_close) if previous_close is not None else None,
        "currency": meta.get("currency"), "exchange_name": meta.get("exchangeName"),
        "market_time_jst": datetime.fromtimestamp(timestamp, JST).isoformat(),
        "raw_sha256": hashlib.sha256(raw).hexdigest().upper(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"output exists: {args.output}")
    started = now_jst()
    records: list[dict[str, Any]] = []
    macro: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    context = None
    try:
        context = OpenQuoteContext(host="127.0.0.1", port=11111)
        ret, data = context.get_market_snapshot(OPEND_SYMBOLS)
        if ret == RET_OK:
            records.extend({
                **{str(key): safe(value) for key, value in row.items()},
                "asset_id": str(row.get("code")), "source": "Futu OpenD get_market_snapshot read-only",
                "status": "FETCH_OK",
            } for row in data.to_dict(orient="records"))
        else:
            failures.append({"source": "Futu OpenD get_market_snapshot read-only", "status": "FETCH_FAILED", "error": str(data)})
    finally:
        if context is not None:
            context.close()
    for asset_id, symbol in EXTERNAL_SYMBOLS.items():
        try:
            records.append({**fetch_chart(symbol), "asset_id": asset_id, "status": "FETCH_OK"})
        except Exception as exc:
            failures.append({"asset_id": asset_id, "symbol": symbol, "status": "FETCH_FAILED", "error_type": type(exc).__name__, "error": str(exc)})
    for name, symbol in MACRO_SYMBOLS.items():
        try:
            row = fetch_chart(symbol)
            previous = row.get("previous_close")
            row["change_pct"] = (row["price"] / previous - 1.0) * 100.0 if previous not in (None, 0) else None
            macro.append({"name": name, **row, "status": "FETCH_OK"})
        except Exception as exc:
            failures.append({"name": name, "symbol": symbol, "status": "FETCH_FAILED", "error_type": type(exc).__name__, "error": str(exc)})
    finished = now_jst()
    result = {
        "schema_version": "V7-STAGEC-RETURN-MARKET-1.0", "run_id": args.run_id,
        "started_at_jst": started, "finished_at_jst": finished, "evidence_cutoff_jst": finished,
        "read_only": True, "trade_operations": False, "records": records,
        "macro_records": macro, "failures": failures,
        "success_count": len(records) + len(macro), "failure_count": len(failures),
        "boundary": "行情按各自最后可得市场时间登记；未收盘市场不冒充收盘数据。抓取失败只登记失败。",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "success": result["success_count"], "failed": result["failure_count"], "cutoff": finished}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
