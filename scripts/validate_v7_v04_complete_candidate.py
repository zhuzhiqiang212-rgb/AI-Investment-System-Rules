#!/usr/bin/env python3
"""Validate and finalize the V7 v0.4 complete candidate delivery set."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageStat
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
POPPLER = Path(
    r"C:\Users\localhost\.cache\codex-runtimes\codex-primary-runtime"
    r"\dependencies\native\poppler\Library\bin\pdftoppm.exe"
)
DAILY = ROOT / "00_请先看这里" / "00_今日日报.pdf"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def stamp(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "size": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, JST).isoformat(timespec="seconds"),
        "sha256": sha256(path),
    }


def make_contact_sheet(images: list[Path], output: Path, start_page: int) -> None:
    cols = 4
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
    rows = (len(thumbs) + cols - 1) // cols
    cell_height = max(image.height for image in thumbs)
    sheet = Image.new("RGB", (cols * thumb_width, rows * cell_height), "#d9dde1")
    for index, image in enumerate(thumbs):
        sheet.paste(image, ((index % cols) * thumb_width, (index // cols) * cell_height))
    sheet.save(output, quality=90)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    args = parser.parse_args()
    output_dir = Path(args.dir).resolve()
    html_path = next(output_dir.glob("★*v0.4.html"))
    pdf_path = next(output_dir.glob("★*v0.4.pdf"))
    product = html_path.read_text(encoding="utf-8")

    required = [
        "business_pass=PENDING_INDEPENDENT_REVIEW",
        "final_product_pass=PENDING_INDEPENDENT_REVIEW",
        "release_status=NOT_AUTHORIZED",
        "current_executable=false",
        "第一层｜今天怎么做",
        "第二层｜为什么这样做",
        "第三层｜完整研究底稿",
        "24类持仓逐只研究",
        "21只候选五关轨迹",
        "＋40%／＋100%目标路径",
        "已判定跟踪点的一致率28/29",
        "5个独立系列样本过少",
        "PLTR和ON通过基础扫描不等于可以买入",
        "SNDK双口径",
        "40股",
        "1,641.11美元",
        "65,644.40美元",
        "19.19%",
        "25.21%",
        "Samsung币种分列",
    ]
    missing = [marker for marker in required if marker not in product]
    forbidden_positive_claims = [
        "独立预测准确率96.552%",
        "投资胜率96.552%",
        "交易胜率96.552%",
        "系统预测能力达到96.552%",
        "release_status=RELEASED",
        "business_pass=PASS",
        "final_product_pass=PASS",
    ]
    forbidden_hits = [marker for marker in forbidden_positive_claims if marker in product]
    holding_count = product.count('class="holding"')
    candidate_count = product.count('class="candidate"')
    closed_details = product.count('<details class="holding">') + product.count('<details class="candidate">')

    json_files = sorted(output_dir.glob("*.json"))
    json_valid = 0
    for path in json_files:
        read_json(path)
        json_valid += 1

    replacement_character_files = []
    for path in [html_path, *json_files, *output_dir.glob("*.html")]:
        if "\ufffd" in path.read_text(encoding="utf-8-sig"):
            replacement_character_files.append(str(path))

    document = PdfReader(str(pdf_path))
    page_texts = [page.extract_text() or "" for page in document.pages]
    blank_pages = [index + 1 for index, text in enumerate(page_texts) if len(text.strip()) < 80]
    page_sizes = sorted(
        {(round(float(page.mediabox.width), 2), round(float(page.mediabox.height), 2)) for page in document.pages}
    )
    a4_portrait = all(590 <= width <= 600 and 837 <= height <= 847 for width, height in page_sizes)

    qa_dir = output_dir / "qa_pages"
    qa_dir.mkdir(exist_ok=True)
    for old_page in qa_dir.glob("page-*.png"):
        old_page.unlink()
    prefix = qa_dir / "page"
    subprocess.run(
        [str(POPPLER), "-png", "-r", "90", str(pdf_path), str(prefix)],
        check=True,
        capture_output=True,
    )
    pages = sorted(qa_dir.glob("page-*.png"), key=lambda path: int(path.stem.split("-")[-1]))
    pixel_checks = []
    visual_review_pages = []
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
        status = "PASS"
        if mean_luma > 254.5 or ink_ratio < 0.002 or dark_ratio > 0.30 or edge_ink_ratio > 0.08:
            status = "REVIEW"
            visual_review_pages.append(page_number)
        pixel_checks.append(
            {
                "page": page_number,
                "mean_luma": round(mean_luma, 3),
                "ink_ratio": round(ink_ratio, 5),
                "dark_ratio": round(dark_ratio, 5),
                "edge_ink_ratio": round(edge_ink_ratio, 5),
                "status": status,
            }
        )

    contacts = []
    for start in range(0, len(pages), 12):
        contact = output_dir / f"12_逐页视觉检查_联系表_{start + 1:02d}-{min(start + 12, len(pages)):02d}.jpg"
        make_contact_sheet(pages[start : start + 12], contact, start + 1)
        contacts.append(str(contact))

    log_path = output_dir / "15_完整施工日志和修改前后清单_20260817.json"
    log = read_json(log_path)
    daily_after = stamp(DAILY)
    daily_before = log["daily_before"]
    daily_ok = (
        daily_before["size"] == daily_after["size"]
        and daily_before["sha256"] == daily_after["sha256"]
    )
    machine_checks = {
        "required_markers_present": not missing,
        "forbidden_claims_absent": not forbidden_hits,
        "holding_count_24": holding_count == 24,
        "candidate_count_21": candidate_count == 21,
        "all_research_details_expanded_for_pdf": closed_details == 0,
        "all_json_valid": json_valid == len(json_files),
        "utf8_replacement_character_zero": not replacement_character_files,
        "pdf_nonblank": not blank_pages,
        "pdf_a4_portrait": a4_portrait,
        "rendered_page_count_matches_pdf": len(pages) == len(page_texts),
        "pixel_checks_pass": not visual_review_pages,
        "daily_unchanged": daily_ok,
    }
    status = "PASS" if all(machine_checks.values()) else "REVIEW_REQUIRED"
    report = {
        "generated_at": datetime.now(JST).isoformat(timespec="seconds"),
        "status": status,
        "html": stamp(html_path),
        "pdf": stamp(pdf_path),
        "page_count": len(page_texts),
        "page_sizes_points": page_sizes,
        "machine_checks": machine_checks,
        "missing_markers": missing,
        "forbidden_claim_hits": forbidden_hits,
        "holding_detail_count": holding_count,
        "candidate_detail_count": candidate_count,
        "json_valid_count": json_valid,
        "replacement_character_files": replacement_character_files,
        "blank_pages": blank_pages,
        "visual_review_pages": visual_review_pages,
        "pixel_checks": pixel_checks,
        "contact_sheets": contacts,
        "manual_visual_status": "PENDING_CODEX_CONTACT_SHEET_REVIEW",
        "font_size_points": {"body_print": 10.2, "table_print": 9.0},
    }
    write_json(output_dir / "12_HTML_PDF一致性及逐页视觉检查_20260817.json", report)
    rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{'通过' if passed else '未通过'}</td></tr>"
        for name, passed in machine_checks.items()
    )
    (output_dir / "12_HTML_PDF一致性及逐页视觉检查_20260817.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>HTML/PDF一致性及逐页视觉检查</title>"
        "<style>body{font:15px/1.6 Microsoft YaHei;max-width:980px;margin:30px auto}"
        "table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:7px}</style>"
        f"<h1>HTML/PDF一致性及逐页视觉检查</h1><p><b>{status}</b>；PDF共{len(page_texts)}页A4。</p>"
        f"<table><tr><th>机器检查</th><th>结果</th></tr>{rows}</table>"
        "<p>全部页面已渲染为图片并生成联系表，等待Codex逐页目视确认。</p>",
        encoding="utf-8",
    )

    daily_proof = {
        "status": "PASS_UNCHANGED" if daily_ok else "FAIL_CHANGED",
        "before": daily_before,
        "after": daily_after,
        "candidate_pdf": stamp(pdf_path),
        "candidate_not_copied_to_daily": sha256(pdf_path) != daily_after["sha256"],
    }
    write_json(output_dir / "14_00今日日报未覆盖证明_20260817.json", daily_proof)
    (output_dir / "14_00今日日报未覆盖证明_20260817.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>00今日日报未覆盖证明</title>"
        "<style>body{font:15px/1.6 Microsoft YaHei;max-width:900px;margin:30px auto}code{overflow-wrap:anywhere}</style>"
        f"<h1>00今日日报未覆盖证明</h1><p><b>{daily_proof['status']}</b></p>"
        f"<p>施工前：{daily_before['size']:,}字节<br><code>{daily_before['sha256']}</code></p>"
        f"<p>施工后：{daily_after['size']:,}字节<br><code>{daily_after['sha256']}</code></p>",
        encoding="utf-8",
    )

    log["qa"] = {"status": status, "page_count": len(page_texts), "visual_review_pages": visual_review_pages}
    log["daily_after"] = daily_after
    log["completed_at"] = datetime.now(JST).isoformat(timespec="seconds")
    write_json(log_path, log)

    excluded = {"13_全部实物SHA256清单_20260817.json", "13_全部实物SHA256清单_20260817.html"}
    artifacts = [
        stamp(path)
        for path in sorted(output_dir.rglob("*"), key=lambda item: str(item))
        if path.is_file() and path.name not in excluded
    ]
    hash_manifest = {
        "generated_at": datetime.now(JST).isoformat(timespec="seconds"),
        "self_excluded": True,
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
    }
    write_json(output_dir / "13_全部实物SHA256清单_20260817.json", hash_manifest)
    artifact_rows = "".join(
        f"<tr><td>{html.escape(item['path'])}</td><td>{item['size']:,}</td>"
        f"<td>{html.escape(item['modified_at'])}</td><td><code>{item['sha256']}</code></td></tr>"
        for item in artifacts
    )
    (output_dir / "13_全部实物SHA256清单_20260817.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>全部实物SHA256清单</title>"
        "<style>body{font:13px/1.45 Microsoft YaHei;margin:24px}table{border-collapse:collapse;width:100%}"
        "td,th{border:1px solid #bbb;padding:5px;overflow-wrap:anywhere}</style>"
        f"<h1>全部实物SHA256清单</h1><p>共{len(artifacts)}项；清单自身不自哈希。</p>"
        f"<table><tr><th>路径</th><th>大小</th><th>修改时间</th><th>SHA256</th></tr>{artifact_rows}</table>",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": status,
                "pages": len(page_texts),
                "daily_unchanged": daily_ok,
                "html": stamp(html_path),
                "pdf": stamp(pdf_path),
                "contact_sheets": contacts,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
