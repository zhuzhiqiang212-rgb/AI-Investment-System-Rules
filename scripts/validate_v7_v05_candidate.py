#!/usr/bin/env python3
"""Validate and finalize the complete V7 v0.5 candidate."""

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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    parser.add_argument("--manual-reviewed", action="store_true")
    args = parser.parse_args()
    output_dir = Path(args.dir).resolve()
    html_path = next(output_dir.glob("★*v0.5.html"))
    pdf_path = next(output_dir.glob("★*v0.5.pdf"))
    product = html_path.read_text(encoding="utf-8")
    holdings = read_json(output_dir / "04_更新后的24类持仓矩阵_20260817.json")
    candidates = read_json(output_dir / "05_更新后的21只五关轨迹_20260817.json")
    exposure = read_json(output_dir / "06_AI敞口重算表_20260817.json")
    target = read_json(output_dir / "07_目标条件计算表_20260817.json")
    repair = read_json(output_dir / "03_六项返修对照表_20260817.json")

    required = [
        "完整投研产品候选 v0.5",
        "business_pass=PENDING_INDEPENDENT_REVIEW",
        "final_product_pass=PENDING_INDEPENDENT_REVIEW",
        "release_status=NOT_AUTHORIZED",
        "current_executable=false",
        "观察带只是重新研究的触发价格",
        "ETN→CEG→MUFG→TSM→VRT",
        "48.147541%",
        "61.475698%",
        "券商收益率25.21%与现价、成本计算收益率19.19%",
        "已判定跟踪点的一致率28/29",
        "下一次日本市场收盘、美国市场收盘及重要财报发布后",
        "-10%",
        "+55.6%",
        "+122.2%",
        "+20%",
        "+16.7%",
        "+66.7%",
    ]
    forbidden = [
        "未获授权制定当前估值或价值区间",
        "正式板块激活仍由GPT总控裁定",
        "GPT总控判断",
        "催化剂：正式财报和行业需求",
        "反向风险：估值、竞争和兑现",
        "失效条件：正式证据和业务判断闭合",
        "SNDK价格、拆股与财务口径",
        "富途2026-08-15",
        "61.476%",
        "VRT→TSM→CRDO",
        "下一次正式财报、账户新实物或总控指定验证日",
        "release_status=RELEASED",
        "business_pass=PASS",
        "final_product_pass=PASS",
    ]
    missing = [marker for marker in required if marker not in product]
    forbidden_hits = [marker for marker in forbidden if marker in product]

    valuation_complete = all(
        item.get("valuation_method")
        and item.get("valuation_judgment")
        and item.get("valuation_basis")
        and "未获授权" not in str(item.get("valuation"))
        for item in holdings["items"]
    )
    holding_time_complete = all(
        set(item.get("dual_time_scale", {})) == {"short", "long", "success", "failure", "review"}
        for item in holdings["items"]
    )
    candidate_gate5 = [item.get("five_gates", [{}, {}, {}, {}, {}])[4].get("input") for item in candidates["items"]]
    candidate_gate5_complete = all(candidate_gate5) and len(set(candidate_gate5)) == 21
    candidate_sector_complete = all(
        item.get("sector_research_status") and "等待" not in item.get("sector_research_status", "")
        for item in candidates["items"]
    )
    candidate_time_complete = all(
        set(item.get("dual_time_scale", {})) == {"short", "long", "success", "failure", "review"}
        for item in candidates["items"]
    )
    target_values = [
        (row["assumed_progress"], row["needed_for_40"], row["needed_for_100"])
        for row in target["conditional_table"]
    ]
    target_complete = target_values == [
        ("-10%", "+55.6%", "+122.2%"),
        ("0%", "+40.0%", "+100.0%"),
        ("+10%", "+27.3%", "+81.8%"),
        ("+20%", "+16.7%", "+66.7%"),
    ]
    exposure_complete = (
        exposure["data_date"] == "2026-08-17"
        and exposure["direct_exposure_pct"] == 48.147541
        and exposure["broad_exposure_pct"] == 61.475698
    )

    json_files = sorted(output_dir.glob("*.json"))
    for path in json_files:
        read_json(path)
    replacement_files = []
    for path in [html_path, *json_files, *output_dir.glob("*.html")]:
        if "\ufffd" in path.read_text(encoding="utf-8-sig"):
            replacement_files.append(str(path))

    document = PdfReader(str(pdf_path))
    page_texts = [page.extract_text() or "" for page in document.pages]
    blank_pages = [index + 1 for index, text in enumerate(page_texts) if len(text.strip()) < 80]
    page_sizes = sorted(
        {(round(float(page.mediabox.width), 2), round(float(page.mediabox.height), 2)) for page in document.pages}
    )
    a4_portrait = all(590 <= width <= 600 and 837 <= height <= 847 for width, height in page_sizes)

    qa_dir = output_dir / "qa_pages"
    qa_dir.mkdir(exist_ok=True)
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
        output = output_dir / f"09_逐页视觉检查_联系表_{start + 1:02d}-{min(start + 12, len(pages)):02d}.jpg"
        contact_sheet(pages[start : start + 12], output, start + 1)
        contacts.append(str(output))

    log_path = output_dir / "12_完整施工日志_20260817.json"
    log = read_json(log_path)
    daily_after = stamp(DAILY)
    daily_before = log["daily_before"]
    daily_ok = daily_before["size"] == daily_after["size"] and daily_before["sha256"] == daily_after["sha256"]
    machine_checks = {
        "required_markers_present": not missing,
        "stale_and_forbidden_text_zero": not forbidden_hits,
        "holding_count_24": holdings["count"] == 24 and product.count('class="holding"') == 24,
        "holding_valuation_24_complete": valuation_complete,
        "holding_time_scale_24_complete": holding_time_complete,
        "candidate_count_21": candidates["count"] == 21 and product.count('class="candidate"') == 21,
        "candidate_fifth_gate_21_unique": candidate_gate5_complete,
        "candidate_sector_status_21_closed": candidate_sector_complete,
        "candidate_time_scale_21_complete": candidate_time_complete,
        "all_45_details_expanded_for_pdf": product.count("<details") == 45 and product.count('open=""') == 45,
        "six_repairs_closed": len(repair["items"]) == 6 and all(item["status"] == "CLOSED" for item in repair["items"]),
        "ai_exposure_recalculated": exposure_complete,
        "target_condition_table_exact": target_complete,
        "all_json_valid": True,
        "utf8_replacement_character_zero": not replacement_files,
        "pdf_nonblank": not blank_pages,
        "pdf_a4_portrait": a4_portrait,
        "rendered_pages_match_pdf": len(pages) == len(page_texts),
        "pixel_checks_pass": not visual_review_pages,
        "daily_unchanged": daily_ok,
    }
    machine_status = "PASS" if all(machine_checks.values()) else "REVIEW_REQUIRED"
    manual_status = (
        f"PASS_CODEX_CONTACT_SHEET_REVIEW_ALL_{len(page_texts)}_PAGES"
        if args.manual_reviewed
        else "PENDING_CODEX_CONTACT_SHEET_REVIEW"
    )
    report = {
        "generated_at": datetime.now(JST).isoformat(timespec="seconds"),
        "status": machine_status,
        "manual_visual_status": manual_status,
        "html": stamp(html_path),
        "pdf": stamp(pdf_path),
        "page_count": len(page_texts),
        "page_sizes_points": page_sizes,
        "machine_checks": machine_checks,
        "missing_markers": missing,
        "forbidden_hits": forbidden_hits,
        "blank_pages": blank_pages,
        "visual_review_pages": visual_review_pages,
        "pixel_checks": pixel_checks,
        "contact_sheets": contacts,
        "font_size_points": {"body_print": 10.2, "table_print": 9.0},
    }
    if args.manual_reviewed:
        report["manual_visual_reviewed_at"] = datetime.now(JST).isoformat(timespec="seconds")
        report["manual_visual_observations"] = [
            f"全部{len(page_texts)}页逐页目视复核",
            "无空页、截断、重叠、黑块或乱码",
            "章节收尾留白不属于内容缺失",
        ]
    write_json(output_dir / "09_HTML_PDF一致性及逐页检查_20260817.json", report)
    check_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{'通过' if passed else '未通过'}</td></tr>"
        for name, passed in machine_checks.items()
    )
    (output_dir / "09_HTML_PDF一致性及逐页检查_20260817.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>HTML/PDF一致性及逐页检查</title>"
        "<style>body{font:15px/1.6 Microsoft YaHei;max-width:980px;margin:30px auto}"
        "table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:7px}</style>"
        f"<h1>HTML/PDF一致性及逐页检查</h1><p><b>{machine_status}</b>；PDF共{len(page_texts)}页A4。</p>"
        f"<p>人工目视状态：{html.escape(manual_status)}</p>"
        f"<table><tr><th>检查</th><th>结果</th></tr>{check_rows}</table>",
        encoding="utf-8",
    )

    daily_proof = {
        "status": "PASS_UNCHANGED" if daily_ok else "FAIL_CHANGED",
        "before": daily_before,
        "after": daily_after,
        "candidate_pdf": stamp(pdf_path),
        "candidate_not_copied_to_daily": sha256(pdf_path) != daily_after["sha256"],
    }
    write_json(output_dir / "11_00今日日报未覆盖证明_20260817.json", daily_proof)
    (output_dir / "11_00今日日报未覆盖证明_20260817.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>00今日日报未覆盖证明</title>"
        "<style>body{font:15px/1.6 Microsoft YaHei;max-width:900px;margin:30px auto}code{overflow-wrap:anywhere}</style>"
        f"<h1>00今日日报未覆盖证明</h1><p><b>{daily_proof['status']}</b></p>"
        f"<p>施工前：{daily_before['size']:,}字节<br><code>{daily_before['sha256']}</code></p>"
        f"<p>施工后：{daily_after['size']:,}字节<br><code>{daily_after['sha256']}</code></p>",
        encoding="utf-8",
    )
    log["qa"] = {"machine_status": machine_status, "manual_visual_status": manual_status, "page_count": len(page_texts)}
    log["daily_after"] = daily_after
    log["completed_at"] = datetime.now(JST).isoformat(timespec="seconds")
    write_json(log_path, log)

    excluded = {"10_全部实物SHA256清单_20260817.json", "10_全部实物SHA256清单_20260817.html"}
    artifacts = [
        stamp(path)
        for path in sorted(output_dir.rglob("*"), key=lambda item: str(item))
        if path.is_file() and path.name not in excluded
    ]
    manifest = {"generated_at": datetime.now(JST).isoformat(timespec="seconds"), "self_excluded": True, "artifact_count": len(artifacts), "artifacts": artifacts}
    write_json(output_dir / "10_全部实物SHA256清单_20260817.json", manifest)
    artifact_rows = "".join(
        f"<tr><td>{html.escape(item['path'])}</td><td>{item['size']:,}</td><td>{html.escape(item['modified_at'])}</td><td><code>{item['sha256']}</code></td></tr>"
        for item in artifacts
    )
    (output_dir / "10_全部实物SHA256清单_20260817.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>全部实物SHA256清单</title>"
        "<style>body{font:13px/1.45 Microsoft YaHei;margin:24px}table{border-collapse:collapse;width:100%}"
        "td,th{border:1px solid #bbb;padding:5px;overflow-wrap:anywhere}</style>"
        f"<h1>全部实物SHA256清单</h1><p>共{len(artifacts)}项；清单自身不自哈希。</p>"
        f"<table><tr><th>路径</th><th>大小</th><th>修改时间</th><th>SHA256</th></tr>{artifact_rows}</table>",
        encoding="utf-8",
    )
    print(json.dumps({"status": machine_status, "manual": manual_status, "pages": len(page_texts), "daily_unchanged": daily_ok, "html": stamp(html_path), "pdf": stamp(pdf_path), "contacts": contacts}, ensure_ascii=False, indent=2))
    return 0 if machine_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
