#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path("G:\\\u6211\u7684\u4e91\u7aef\u786c\u76d8\\AI_Investment_System")
OUT_DIR = ROOT / "00_\u8bf7\u5148\u770b\u8fd9\u91cc"
JST = timezone(timedelta(hours=9))

LABELS = {
    "title": "\u65e5\u62a5_20260702_\u5b8c\u6574\u7248",
    "top": "\u5f53\u65e5\u8bc1\u636e\u94fe\u6307\u7eb9",
    "risk": "\u98ce\u9669\u58f0\u660e\uff1a\u672c\u62a5\u544a\u975e\u5b9e\u65f6\u3001\u975e\u4e0b\u5355\u6307\u4ee4\uff1b\u6700\u7ec8\u51b3\u7b56\u5728\u8463\u4e8b\u957f\uff1bClaude\u975e\u6301\u724c\u6295\u987e\u3002",
    "gate": "\u603b\u95f8",
    "nodes": "\u6fc0\u6d3b\u8282\u70b9",
    "scope": "\u673a\u4f1a\u6c60\u53e3\u5f84",
    "source": "\u4f9d\u636e",
    "generated": "\u751f\u6210\u65f6\u95f4",
    "layer": "\u7b2c{n}\u5c42 {name}",
    "source_link": "\u6765\u6e90\u73af\u8282",
    "evidence": "\u4eca\u65e5\u8bc1\u636e",
    "strength": "\u529b\u5ea6",
    "direction": "\u65b9\u5411",
    "downstream": "\u4e0b\u6e38\u63a8\u5bfc",
    "company": "\u516c\u53f8",
    "code": "\u4ee3\u7801",
    "name": "\u540d\u79f0",
    "account": "\u8d26\u6237",
    "market_value": "\u5e02\u503cUSD",
    "verdict": "\u53d7\u68c0\u7ed3\u679c",
    "matched_nodes": "\u6240\u5c5e\u8282\u70b9",
    "decision_placeholder": "\u3010\u5f85\u7406\u89e3\u5c97\u586b\u56e0\u4e3a\u6240\u4ee5/\u53cd\u8fc7\u6765\u60f3\u3011",
    "valuation_placeholder": "\u3010\u5f85\u7406\u89e3\u5c97\u586b,\u4ec5\u5fae\u8f6f\u6a21\u677f\u5b8c\u6210,\u4f59\u5f85\u8865\u3011",
    "risk_placeholder": "\u3010\u5f85\u7406\u89e3\u5c97\u586b\u6df1\u5ea6\u3011",
    "review_placeholder": "\u3010\u5f85\u7406\u89e3\u5c97\u586b+\u590d\u76d8\u9776\u5b50\u3011",
    "opportunity": "\u673a\u4f1a",
    "channel1": "\u901a\u9053\u2460 \u6362\u4ed3\u5bf9\u6bd4",
    "channel2": "\u901a\u9053\u2461 \u516d\u7ef4\u4e70\u5356\u4ef7\u683c\u5e26",
    "current": "\u73b0\u6301\u4ed3",
    "candidate": "\u5019\u9009",
    "same_node": "\u540c\u8282\u70b9",
    "price_position": "\u4ef7\u683c\u4f4d",
    "suggestion": "\u5efa\u8bae",
    "kind": "\u7c7b\u578b",
    "tech": "\u6280\u672f\u7ef4",
    "cost": "\u6210\u672c\u7ef4",
    "funds": "\u8d44\u91d1\u7ef4",
    "valuation": "\u4f30\u503c\u7ef4",
    "catalyst": "\u57fa\u672c\u9762\u50ac\u5316\u7ef4",
    "summary": "\u6458\u8981",
    "portfolio": "\u7ec4\u5408",
    "today_action": "\u4eca\u65e5\u52a8\u4f5c",
    "today_direction": "today_direction",
    "opportunity_scope": "opportunity_scope",
    "decision_constraint": "decision_constraint",
}


def now_jst() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def e(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    return html.escape(str(value), quote=True)


def load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        print(f"\u7f3a{label}\u4ea7\u51fa: {path}")
        raise SystemExit(2)
    return json.loads(path.read_text(encoding="utf-8"))


def write_utf8(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    reread = path.read_text(encoding="utf-8")
    if reread != text:
        raise RuntimeError("UTF-8 reread mismatch")
    if chr(63) in reread or chr(0xFFFD) in reread:
        raise RuntimeError("Garble marker found")


def kv(label: str, value: Any) -> str:
    return f"<div><b>{e(label)}</b><span>{e(value)}</span></div>"


def table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f"<th>{e(h)}</th>" for h in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{e(cell)}</td>" for cell in row) + "</tr>")
    return "<table><thead><tr>" + head + "</tr></thead><tbody>" + "".join(body) + "</tbody></table>"


def render_upper_layer(layer: dict[str, Any]) -> str:
    title = LABELS["layer"].format(n=layer.get("layer_no"), name=layer.get("layer_name"))
    rows = [
        [LABELS["source_link"], layer.get("source_link")],
        [LABELS["evidence"], layer.get("evidence")],
        [LABELS["strength"], layer.get("strength")],
        [LABELS["direction"], layer.get("direction")],
        [LABELS["downstream"], layer.get("downstream")],
    ]
    return f"<section id='layer-{e(layer.get('layer_no'))}'><h2>{e(title)}</h2>{table(['',''], rows)}</section>"


def render_layer8(holdings: dict[str, Any]) -> str:
    rows = []
    for row in holdings.get("reviews", []):
        rows.append([
            row.get("code"),
            row.get("name"),
            row.get("account"),
            row.get("market_value_usd"),
            row.get("verdict"),
            ", ".join(row.get("matched_node_classes") or []),
            LABELS["decision_placeholder"],
        ])
    return "<section id='layer-8'><h2>\u7b2c8\u5c42 \u516c\u53f8</h2>" + table([
        LABELS["code"], LABELS["name"], LABELS["account"], LABELS["market_value"],
        LABELS["verdict"], LABELS["matched_nodes"], "\u51b3\u7b56\u63aa\u8f9e"
    ], rows) + "</section>"


def render_layer11(dual: dict[str, Any]) -> str:
    ch1 = dual.get("channel_1_best_holding", {})
    rows1 = []
    for row in ch1.get("comparisons", []):
        rows1.append([
            row.get("\u73b0\u6301\u4ed3\u6807\u7684"),
            row.get("\u5019\u9009\u6807\u7684"),
            row.get("\u540c\u8282\u70b9"),
            row.get("\u5bf9\u6bd4\u7ef4\u5ea6", {}).get("\u5f53\u524d\u4ef7\u683c\u4f4d\u7f6e"),
            row.get("\u5efa\u8bae"),
        ])
    ch2 = dual.get("channel_2_trade_price", {})
    rows2 = []
    for row in ch2.get("instruments", []):
        dims = row.get("six_dimensions", {})
        rows2.append([
            row.get("kind"),
            row.get("code") or row.get("ticker"),
            row.get("name"),
            row.get("node_class"),
            dims.get("\u6280\u672f\u7ef4"),
            dims.get("\u6210\u672c\u7ef4"),
            dims.get("\u8d44\u91d1\u7ef4"),
            dims.get("\u4f30\u503c\u7ef4"),
            dims.get("\u57fa\u672c\u9762\u50ac\u5316\u7ef4"),
            row.get("current_buy_sell_reference"),
        ])
    html_parts = [
        "<section id='layer-11'><h2>\u7b2c11\u5c42 \u673a\u4f1a</h2>",
        f"<h3>{e(LABELS['channel1'])}</h3>",
        table([LABELS["current"], LABELS["candidate"], LABELS["same_node"], LABELS["price_position"], LABELS["suggestion"]], rows1),
        f"<h3>{e(LABELS['channel2'])}</h3>",
        table([LABELS["kind"], LABELS["code"], LABELS["name"], LABELS["same_node"], LABELS["tech"], LABELS["cost"], LABELS["funds"], LABELS["valuation"], LABELS["catalyst"], LABELS["summary"]], rows2),
        "</section>",
    ]
    return "".join(html_parts)


def render_layer12(holdings: dict[str, Any]) -> str:
    rows = [[k, v] for k, v in (holdings.get("summary") or {}).items()]
    return "<section id='layer-12'><h2>\u7b2c12\u5c42 \u7ec4\u5408</h2>" + table([LABELS["verdict"], "\u6570\u91cf"], rows) + "</section>"


def render_layer13(evidence: dict[str, Any]) -> str:
    derived = evidence.get("derived") or {}
    rows = [
        [LABELS["today_direction"], derived.get("today_direction")],
        [LABELS["opportunity_scope"], derived.get("opportunity_scope")],
        [LABELS["decision_constraint"], derived.get("decision_constraint")],
    ]
    return "<section id='layer-13'><h2>\u7b2c13\u5c42 \u4eca\u65e5\u52a8\u4f5c</h2>" + table(["",""], rows) + "</section>"


def build_html(date_text: str) -> str:
    upper_path = ROOT / "data" / "reports" / f"daily_upper_{date_text}.json"
    holdings_path = ROOT / "data" / "holdings" / f"holdings_review_{date_text}.json"
    dual_path = ROOT / "data" / "opportunities" / f"dual_channel_{date_text}.json"
    evidence_path = ROOT / "data" / "evidence_chain" / f"daily_{date_text}.json"

    upper = load_json(upper_path, "daily_upper")
    holdings = load_json(holdings_path, "holdings_review")
    dual = load_json(dual_path, "dual_channel")
    evidence = load_json(evidence_path, "daily evidence chain")

    fp = upper.get("fingerprint") or {}
    generated_at = now_jst()
    layers = []
    for layer in upper.get("layers", []):
        layers.append(render_upper_layer(layer))
    layers.append(render_layer8(holdings))
    layers.append(f"<section id='layer-9'><h2>\u7b2c9\u5c42 \u4f30\u503c</h2><p>{e(LABELS['valuation_placeholder'])}</p></section>")
    layers.append(f"<section id='layer-10'><h2>\u7b2c10\u5c42 \u98ce\u9669</h2><p>{e(LABELS['risk_placeholder'])}</p></section>")
    layers.append(render_layer11(dual))
    layers.append(render_layer12(holdings))
    layers.append(render_layer13(evidence))
    layers.append(f"<section id='layer-14'><h2>\u7b2c14\u5c42 \u4ea7\u54c1+\u590d\u76d8</h2><p>{e(LABELS['review_placeholder'])}</p></section>")

    top = "".join([
        kv(LABELS["gate"], fp.get("total_gate")),
        kv(LABELS["nodes"], ", ".join(fp.get("activated_node_classes") or [])),
        kv(LABELS["scope"], (evidence.get("derived") or {}).get("opportunity_scope")),
        kv(LABELS["source"], str(evidence_path)),
        kv(LABELS["generated"], generated_at),
    ])
    css = """
body{font-family:Arial,'Microsoft YaHei',sans-serif;margin:0;background:#f6f7f9;color:#1f2933}
main{max-width:1180px;margin:0 auto;padding:28px}
header{background:#102a43;color:white;padding:28px;border-bottom:4px solid #f0b429}
h1{margin:0 0 12px;font-size:28px}
.fingerprint{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin-top:16px}
.fingerprint div{background:rgba(255,255,255,.12);padding:10px;border-radius:6px}
.fingerprint b{display:block;color:#d9e2ec;margin-bottom:4px}
.risk{margin-top:14px;color:#f7d070}
section{background:white;margin:18px 0;padding:18px;border:1px solid #d9e2ec;border-radius:6px}
h2{font-size:20px;margin:0 0 12px;color:#102a43}
h3{font-size:16px;margin:16px 0 8px;color:#334e68}
table{width:100%;border-collapse:collapse;font-size:13px;table-layout:fixed}
th,td{border:1px solid #d9e2ec;padding:8px;vertical-align:top;word-break:break-word}
th{background:#eef2f7;text-align:left}
p{line-height:1.65}
"""
    return "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><title>" + e(LABELS["title"]) + "</title><style>" + css + "</style></head><body><header><h1>" + e(LABELS["title"]) + "</h1><div class='fingerprint'>" + top + "</div><div class='risk'>" + e(LABELS["risk"]) + "</div></header><main>" + "".join(layers) + "</main></body></html>"


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="20260702")
    args = parser.parse_args()
    html_text = build_html(args.date)
    out_path = OUT_DIR / f"\u65e5\u62a5_{args.date}_\u5b8c\u6574\u7248.html"
    write_utf8(out_path, html_text)
    print(f"OUTPUT_PATH={out_path}")
    print("LAYERS=14")
    print("PLACEHOLDERS=\u7b2c8\u5c42\u51b3\u7b56\u63aa\u8f9e,\u7b2c9\u5c42\u4f30\u503c,\u7b2c10\u5c42\u98ce\u9669,\u7b2c14\u5c42\u4ea7\u54c1+\u590d\u76d8")
    print("CHANNEL11=dual_channel_20260702")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
