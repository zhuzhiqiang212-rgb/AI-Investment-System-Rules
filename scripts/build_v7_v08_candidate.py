#!/usr/bin/env python3
"""Build V7 v0.8 by expanding every details element for PDF printing."""

from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, NavigableString


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RUN = "V7-V07-COMPLETE-20260817-114501-JST"
SOURCE = ROOT / "output/candidates/2026-08-17" / SOURCE_RUN
SOURCE_HTML = SOURCE / "★2026-08-17完整投研产品候选_v0.7.html"
SOURCE_PDF = SOURCE / "★2026-08-17完整投研产品候选_v0.7.pdf"
PDCA_SOURCE = SOURCE / "04_57条PDCA逐项闭合检查_20260817.json"
DAILY_PROOF = SOURCE / "10_00今日日报未覆盖证明_20260817.json"
JST = timezone(timedelta(hours=9))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def stamp(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "size": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, JST).isoformat(timespec="seconds"),
        "sha256": sha256(path),
    }


def report_html(title: str, rows: list[tuple[str, str]]) -> str:
    body = "".join(
        f"<tr><th>{html.escape(label)}</th><td>{html.escape(value)}</td></tr>"
        for label, value in rows
    )
    return (
        "<!doctype html><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>body{font:15px/1.6 Microsoft YaHei;max-width:980px;margin:30px auto}"
        "table{border-collapse:collapse;width:100%}th,td{border:1px solid #bbb;padding:8px;vertical-align:top}"
        "th{width:210px;text-align:left;background:#eef2f4}code{overflow-wrap:anywhere}</style>"
        f"<h1>{html.escape(title)}</h1><table>{body}</table>"
    )


def main() -> int:
    now = datetime.now(JST)
    run_id = f"V7-V08-PDCA-PRINT-{now:%Y%m%d-%H%M%S}-JST"
    output_dir = ROOT / "output/candidates/2026-08-17" / run_id
    output_dir.mkdir(parents=True, exist_ok=False)

    source = SOURCE_HTML.read_text(encoding="utf-8")
    soup = BeautifulSoup(source, "html.parser")
    source_text = soup.get_text(" ", strip=True)
    source_ids = sorted(set(re.findall(r"FORECAST-LEDGER-\d{3}", source_text)))
    details = soup.find_all("details")
    pdca_details = soup.select("details.pdca-series")
    if len(source_ids) != 57 or len(pdca_details) != 5 or len(details) != 50:
        raise RuntimeError("v0.7 source identity or PDCA structure mismatch")

    for node in list(soup.find_all(string=True)):
        if not isinstance(node, NavigableString) or node.parent.name in {"style", "script"}:
            continue
        value = str(node).replace("v0.7", "v0.8").replace(SOURCE_RUN, run_id)
        if value != str(node):
            node.replace_with(value)
    if soup.title:
        soup.title.string = "2026-08-17完整投研产品候选_v0.8"

    for detail in details:
        detail["open"] = ""

    style = soup.find("style")
    if style is None:
        raise RuntimeError("Missing product stylesheet")
    style.append(
        "\n/* v0.8 print-only closure: every nested disclosure is printable. */"
        "details{display:block!important}"
        "details>summary{display:block!important}"
        "details>*:not(summary){display:block!important}"
        "@media print{details,details[open],details:not([open]){display:block!important}"
        "details>summary{display:block!important}details>*{display:block!important}}"
    )

    html_path = output_dir / "★2026-08-17完整投研产品候选_v0.8.html"
    html_path.write_text(str(soup), encoding="utf-8")

    pdca = read_json(PDCA_SOURCE)
    daily_before = read_json(DAILY_PROOF)["after"]
    change = {
        "run_id": run_id,
        "source_run_id": SOURCE_RUN,
        "scope": "PDF_PRINT_EXPANSION_ONLY",
        "source_html": stamp(SOURCE_HTML),
        "source_pdf": stamp(SOURCE_PDF),
        "changes": [
            {
                "item": "候选版本身份",
                "before": "v0.7",
                "after": "v0.8",
                "reason": "保留v0.7审批来源，不覆盖原件",
            },
            {
                "item": "details展开状态",
                "before": "50个details中45个展开，5个PDCA系列折叠",
                "after": "50个details全部静态open",
                "reason": "确保57条PDCA进入PDF",
            },
            {
                "item": "打印CSS",
                "before": "依赖浏览器原生details展开状态",
                "after": "打印时强制details及全部子内容display:block",
                "reason": "防止渲染器忽略折叠内容",
            },
        ],
        "business_content_changed": False,
        "account_data_changed": False,
        "valuation_changed": False,
        "evidence_changed": False,
    }
    expansion = {
        "run_id": run_id,
        "source_html_forecast_ids": len(source_ids),
        "v08_html_forecast_ids": len(set(re.findall(r"FORECAST-LEDGER-\d{3}", soup.get_text(" ", strip=True)))),
        "details_total": len(details),
        "details_open": sum(item.has_attr("open") for item in details),
        "pdca_series_total": len(pdca_details),
        "pdca_series_open": sum(item.has_attr("open") for item in pdca_details),
        "source_pdca_sha256": sha256(PDCA_SOURCE),
        "expected": {
            "series": 5,
            "records": 57,
            "adjudicated": 29,
            "correct": 28,
            "wrong": 1,
            "pending": 28,
        },
        "pdf_check": "PENDING_RENDER",
    }
    log = {
        "run_id": run_id,
        "generated_at": now.isoformat(timespec="seconds"),
        "source_run_id": SOURCE_RUN,
        "daily_before": daily_before,
        "status": {
            "business_pass": "PENDING_INDEPENDENT_REVIEW",
            "final_product_pass": "PENDING_INDEPENDENT_REVIEW",
            "release_status": "NOT_AUTHORIZED",
            "current_executable": False,
        },
        "actions": ["复制v0.7为新批次", "静态展开50个details", "增加打印CSS兜底"],
    }
    write_json(output_dir / "03_v0.7至v0.8变更清单_20260817.json", change)
    write_json(output_dir / "04_PDF展开证明_20260817.json", expansion)
    write_json(output_dir / "08_施工日志_20260817.json", log)
    (output_dir / "03_v0.7至v0.8变更清单_20260817.html").write_text(
        report_html(
            "v0.7至v0.8变更清单",
            [
                ("施工范围", "只修复PDF漏印57条PDCA明细"),
                ("业务正文", "零改写"),
                ("账户、估值、证据", "零改写"),
                ("details", "50个全部静态展开"),
                ("打印CSS", "强制显示details全部子内容"),
            ],
        ),
        encoding="utf-8",
    )
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
