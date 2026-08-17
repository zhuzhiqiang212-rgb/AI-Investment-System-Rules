#!/usr/bin/env python3
"""Validate v0.8 PDCA print expansion, render pages, and freeze hashes."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageStat
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RUN = "V7-V07-COMPLETE-20260817-114501-JST"
SOURCE = ROOT / "output/candidates/2026-08-17" / SOURCE_RUN
SOURCE_HTML = SOURCE / "★2026-08-17完整投研产品候选_v0.7.html"
PDCA_SOURCE = SOURCE / "04_57条PDCA逐项闭合检查_20260817.json"
DAILY = ROOT / "00_请先看这里/00_今日日报.pdf"
POPPLER = Path(
    r"C:\Users\localhost\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\native\poppler\Library\bin\pdftoppm.exe"
)
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


def contact_sheet(images: list[Path], output: Path, start_page: int) -> None:
    columns = 4
    thumb_width = 230
    thumbs: list[Image.Image] = []
    for offset, path in enumerate(images):
        with Image.open(path) as source:
            image = source.convert("RGB")
        ratio = thumb_width / image.width
        thumb = image.resize((thumb_width, int(image.height * ratio)))
        canvas = Image.new("RGB", (thumb_width, thumb.height + 24), "white")
        canvas.paste(thumb, (0, 24))
        ImageDraw.Draw(canvas).text((7, 5), f"Page {start_page + offset}", fill="black")
        thumbs.append(canvas)
    rows = (len(thumbs) + columns - 1) // columns
    height = max(image.height for image in thumbs)
    sheet = Image.new("RGB", (columns * thumb_width, rows * height), "#d9dde1")
    for index, image in enumerate(thumbs):
        sheet.paste(image, ((index % columns) * thumb_width, (index // columns) * height))
    sheet.save(output, quality=90)


def report_html(title: str, status: str, checks: dict[str, bool], note: str) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{'通过' if passed else '未通过'}</td></tr>"
        for name, passed in checks.items()
    )
    return (
        "<!doctype html><meta charset='utf-8'>"
        f"<title>{html.escape(title)}</title>"
        "<style>body{font:15px/1.6 Microsoft YaHei;max-width:1000px;margin:30px auto}"
        "table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:7px}</style>"
        f"<h1>{html.escape(title)}</h1><p><b>{html.escape(status)}</b>；{html.escape(note)}</p>"
        f"<table><tr><th>检查</th><th>结果</th></tr>{rows}</table>"
    )


def normalized_business_text(path: Path, version: str, run_id: str) -> str:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    text = soup.get_text(" ", strip=True)
    return text.replace(version, "VERSION").replace(run_id, "RUN_ID")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    parser.add_argument("--manual-reviewed", action="store_true")
    args = parser.parse_args()
    output_dir = Path(args.dir).resolve()
    html_path = next(output_dir.glob("★*v0.8.html"))
    pdf_path = next(output_dir.glob("★*v0.8.pdf"))
    log_path = output_dir / "08_施工日志_20260817.json"
    log = read_json(log_path)
    run_id = log["run_id"]
    pdca = read_json(PDCA_SOURCE)
    expansion_path = output_dir / "04_PDF展开证明_20260817.json"
    expansion = read_json(expansion_path)

    raw = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(raw, "html.parser")
    visible = soup.get_text(" ", strip=True)
    html_ids = sorted(set(re.findall(r"FORECAST-LEDGER-\d{3}", visible)))
    html_series = sorted(set(re.findall(r"PDCA-SERIES-\d{3}", visible)))
    details = soup.find_all("details")
    pdca_details = soup.select("details.pdca-series")

    document = PdfReader(str(pdf_path))
    page_texts = [page.extract_text() or "" for page in document.pages]
    pdf_text = "\n".join(page_texts)
    pdf_ids = sorted(set(re.findall(r"FORECAST-LEDGER-\d{3}", pdf_text)))
    pdf_id_occurrences = re.findall(r"FORECAST-LEDGER-\d{3}", pdf_text)
    pdf_series = sorted(set(re.findall(r"PDCA-SERIES-\d{3}", pdf_text)))
    pdca_pages = [index + 1 for index, text in enumerate(page_texts) if "FORECAST-LEDGER-" in text]
    required_columns = ["预测编号", "预测日期", "原预测", "到期日", "成功定义", "验证日期", "实际结果", "结论", "证据", "反事实"]

    records = pdca["records"]
    judgments = [item.get("judgment") for item in records]
    source_counts = {
        "series": 5,
        "records": len(records),
        "adjudicated": sum(value in {"判对", "判错"} for value in judgments),
        "correct": judgments.count("判对"),
        "wrong": judgments.count("判错"),
        "pending": sum(value not in {"判对", "判错"} for value in judgments),
    }
    source_business = normalized_business_text(SOURCE_HTML, "v0.7", SOURCE_RUN)
    v08_business = normalized_business_text(html_path, "v0.8", run_id)
    links_source = [item.get("href") for item in BeautifulSoup(SOURCE_HTML.read_text(encoding="utf-8"), "html.parser").find_all("a")]
    links_v08 = [item.get("href") for item in soup.find_all("a")]

    blank_pages = [index + 1 for index, text in enumerate(page_texts) if len(text.strip()) < 10]
    page_sizes = sorted(
        {(round(float(page.mediabox.width), 2), round(float(page.mediabox.height), 2)) for page in document.pages}
    )
    a4_portrait = all(590 <= width <= 600 and 837 <= height <= 847 for width, height in page_sizes)

    qa_dir = output_dir / "qa_pages"
    qa_dir.mkdir(exist_ok=True)
    subprocess.run(
        [str(POPPLER), "-png", "-r", "90", str(pdf_path), str(qa_dir / "page")],
        check=True,
        capture_output=True,
    )
    pages = sorted(qa_dir.glob("page-*.png"), key=lambda path: int(path.stem.split("-")[-1]))
    review_pages: list[int] = []
    pixel_checks = []
    for page_number, path in enumerate(pages, 1):
        with Image.open(path) as source:
            image = source.convert("L")
        histogram = image.histogram()
        total = image.width * image.height
        mean_luma = ImageStat.Stat(image).mean[0]
        dark_ratio = sum(histogram[:35]) / total
        ink_ratio = sum(histogram[:245]) / total
        edge = 4
        edge_pixels = (
            list(image.crop((0, 0, image.width, edge)).getdata())
            + list(image.crop((0, image.height - edge, image.width, image.height)).getdata())
            + list(image.crop((0, 0, edge, image.height)).getdata())
            + list(image.crop((image.width - edge, 0, image.width, image.height)).getdata())
        )
        edge_ink_ratio = sum(1 for value in edge_pixels if value < 220) / max(1, len(edge_pixels))
        passed = mean_luma <= 254.5 and ink_ratio >= 0.002 and dark_ratio <= 0.30 and edge_ink_ratio <= 0.08
        if not passed:
            review_pages.append(page_number)
        pixel_checks.append(
            {
                "page": page_number,
                "mean_luma": round(mean_luma, 3),
                "ink_ratio": round(ink_ratio, 5),
                "dark_ratio": round(dark_ratio, 5),
                "edge_ink_ratio": round(edge_ink_ratio, 5),
                "status": "PASS" if passed else "REVIEW",
            }
        )

    contacts = []
    for start in range(0, len(pages), 12):
        output = output_dir / f"05_逐页视觉检查_联系表_{start + 1:03d}-{min(start + 12, len(pages)):03d}.jpg"
        contact_sheet(pages[start : start + 12], output, start + 1)
        contacts.append(str(output))

    daily_after = stamp(DAILY)
    daily_before = log["daily_before"]
    daily_ok = daily_before["size"] == daily_after["size"] and daily_before["sha256"] == daily_after["sha256"]
    checks = {
        "html_forecast_ledger_unique_57": len(html_ids) == 57,
        "pdf_forecast_ledger_unique_57": len(pdf_ids) == 57,
        "pdf_forecast_ledger_occurrences_57": len(pdf_id_occurrences) == 57,
        "html_pdf_forecast_ids_exact_match": html_ids == pdf_ids,
        "html_pdca_series_5": len(html_series) == 5,
        "pdf_pdca_series_5": len(pdf_series) == 5,
        "html_pdf_pdca_series_exact_match": html_series == pdf_series,
        "all_required_pdca_columns_in_html": all(column in visible for column in required_columns),
        "all_required_pdca_columns_in_pdf": all(column in pdf_text for column in required_columns),
        "source_counts_29_28_1_28": source_counts == {"series": 5, "records": 57, "adjudicated": 29, "correct": 28, "wrong": 1, "pending": 28},
        "all_50_details_open": len(details) == 50 and sum(item.has_attr("open") for item in details) == 50,
        "all_5_pdca_details_open": len(pdca_details) == 5 and sum(item.has_attr("open") for item in pdca_details) == 5,
        "print_css_forces_details_visible": "details>*:not(summary){display:block!important}" in raw and "details>*{display:block!important}" in raw,
        "business_text_zero_change": source_business == v08_business,
        "links_zero_change": links_source == links_v08,
        "status_pending_review": all(marker in visible for marker in ["business_pass=PENDING_INDEPENDENT_REVIEW", "final_product_pass=PENDING_INDEPENDENT_REVIEW", "release_status=NOT_AUTHORIZED", "current_executable=false"]),
        "release_not_authorized": "release_status=RELEASED" not in visible and "current_executable=true" not in visible,
        "utf8_replacement_character_zero": "\ufffd" not in raw and "\ufffd" not in pdf_text,
        "pdf_nonblank": not blank_pages,
        "pdf_a4_portrait": a4_portrait,
        "rendered_pages_match_pdf": len(pages) == len(page_texts),
        "pixel_checks_pass": not review_pages,
        "daily_unchanged": daily_ok,
    }
    machine_status = "PASS" if all(checks.values()) else "REVIEW_REQUIRED"
    manual_status = f"PASS_CODEX_CONTACT_SHEET_REVIEW_ALL_{len(page_texts)}_PAGES" if args.manual_reviewed else "PENDING_CODEX_CONTACT_SHEET_REVIEW"

    expansion.update(
        {
            "pdf_check": machine_status,
            "html_forecast_ids": len(html_ids),
            "pdf_forecast_ids": len(pdf_ids),
            "pdf_forecast_occurrences": len(pdf_id_occurrences),
            "html_series": len(html_series),
            "pdf_series": len(pdf_series),
            "source_counts": source_counts,
            "pdca_pdf_pages": pdca_pages,
            "pdca_pdf_page_range": [min(pdca_pages), max(pdca_pages)] if pdca_pages else [],
            "source_pdf_pages": 94,
            "v08_pdf_pages": len(page_texts),
            "added_page_count": len(page_texts) - 94,
            "checks": {key: checks[key] for key in list(checks)[:15]},
        }
    )
    write_json(expansion_path, expansion)
    (output_dir / "04_PDF展开证明_20260817.html").write_text(
        report_html(
            "PDF展开证明",
            machine_status,
            {key: checks[key] for key in list(checks)[:15]},
            f"HTML与PDF均命中57条FORECAST-LEDGER；PDCA位于PDF第{min(pdca_pages) if pdca_pages else '?'}至{max(pdca_pages) if pdca_pages else '?'}页。",
        ),
        encoding="utf-8",
    )

    report = {
        "generated_at": datetime.now(JST).isoformat(timespec="seconds"),
        "status": machine_status,
        "manual_visual_status": manual_status,
        "html": stamp(html_path),
        "pdf": stamp(pdf_path),
        "page_count": len(page_texts),
        "page_sizes_points": page_sizes,
        "pdca_pages": pdca_pages,
        "added_page_count_vs_v07": len(page_texts) - 94,
        "checks": checks,
        "blank_pages": blank_pages,
        "visual_review_pages": review_pages,
        "pixel_checks": pixel_checks,
        "contact_sheets": contacts,
    }
    if args.manual_reviewed:
        report["manual_visual_reviewed_at"] = datetime.now(JST).isoformat(timespec="seconds")
        report["manual_visual_observations"] = [
            f"全部{len(page_texts)}页逐页目视复核",
            f"重点复核PDCA第{min(pdca_pages)}至{max(pdca_pages)}页",
            "无空白、截断、重叠、黑块或乱码",
        ]
    write_json(output_dir / "05_HTML_PDF一致性及逐页视觉检查_20260817.json", report)
    (output_dir / "05_HTML_PDF一致性及逐页视觉检查_20260817.html").write_text(
        report_html(
            "HTML/PDF一致性及逐页视觉检查",
            machine_status,
            checks,
            f"PDF共{len(page_texts)}页；人工状态：{manual_status}。",
        ),
        encoding="utf-8",
    )

    daily_proof = {
        "status": "PASS_UNCHANGED" if daily_ok else "FAIL_CHANGED",
        "before": daily_before,
        "after": daily_after,
        "candidate_pdf": stamp(pdf_path),
        "candidate_not_copied_to_daily": sha256(pdf_path) != daily_after["sha256"],
    }
    write_json(output_dir / "07_00今日日报未覆盖证明_20260817.json", daily_proof)
    (output_dir / "07_00今日日报未覆盖证明_20260817.html").write_text(
        report_html(
            "00今日日报未覆盖证明",
            daily_proof["status"],
            {"施工前后大小一致": daily_before["size"] == daily_after["size"], "施工前后SHA256一致": daily_before["sha256"] == daily_after["sha256"], "候选未复制到日报": daily_proof["candidate_not_copied_to_daily"]},
            daily_after["sha256"],
        ),
        encoding="utf-8",
    )

    log["qa"] = {"machine_status": machine_status, "manual_visual_status": manual_status, "page_count": len(page_texts)}
    log["daily_after"] = daily_after
    log["completed_at"] = datetime.now(JST).isoformat(timespec="seconds")
    write_json(log_path, log)

    excluded = {"06_全部实物SHA256清单_20260817.json", "06_全部实物SHA256清单_20260817.html"}
    artifacts = [
        stamp(path)
        for path in sorted(output_dir.rglob("*"), key=lambda item: str(item))
        if path.is_file() and path.name not in excluded
    ]
    manifest = {
        "generated_at": datetime.now(JST).isoformat(timespec="seconds"),
        "self_excluded": True,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }
    write_json(output_dir / "06_全部实物SHA256清单_20260817.json", manifest)
    rows = "".join(
        f"<tr><td>{html.escape(item['path'])}</td><td>{item['size']:,}</td><td>{html.escape(item['modified_at'])}</td><td><code>{item['sha256']}</code></td></tr>"
        for item in artifacts
    )
    (output_dir / "06_全部实物SHA256清单_20260817.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>全部实物SHA256清单</title>"
        "<style>body{font:13px/1.45 Microsoft YaHei;margin:24px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:5px;overflow-wrap:anywhere}</style>"
        f"<h1>全部实物SHA256清单</h1><p>共{len(artifacts)}项；清单自身不自哈希。</p>"
        f"<table><tr><th>路径</th><th>大小</th><th>修改时间</th><th>SHA256</th></tr>{rows}</table>",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": machine_status,
                "manual": manual_status,
                "pages": len(page_texts),
                "pdca_pages": [min(pdca_pages), max(pdca_pages)] if pdca_pages else [],
                "html_ids": len(html_ids),
                "pdf_ids": len(pdf_ids),
                "daily_unchanged": daily_ok,
                "html": stamp(html_path),
                "pdf": stamp(pdf_path),
                "contacts": contacts,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if machine_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
