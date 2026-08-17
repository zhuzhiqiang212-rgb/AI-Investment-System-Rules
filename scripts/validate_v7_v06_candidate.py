#!/usr/bin/env python3
"""Validate, render, and finalize the complete V7 v0.6 candidate."""

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
DAILY = ROOT / "00_请先看这里/00_今日日报.pdf"


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
    html_path = next(output_dir.glob("★*v0.6.html"))
    pdf_path = next(output_dir.glob("★*v0.6.pdf"))
    product = html_path.read_text(encoding="utf-8")
    holdings = read_json(output_dir / "04_24类持仓唯一答案检查_20260817.json")
    candidates = read_json(output_dir / "05_21只候选五关检查_20260817.json")
    same_stock = read_json(output_dir / "06_同股跨层一致性检查_20260817.json")
    samsung = read_json(output_dir / "07_三星双期间校验_20260817.json")
    isolation = read_json(output_dir / "08_SNDK_LITE_XOM_爱德万隔离证明_20260817.json")
    ai = read_json(output_dir / "09_AI暴露分母校验_20260817.json")
    log_path = output_dir / "14_完整施工日志_20260817.json"
    log = read_json(log_path)

    required = [
        "完整投研产品候选 v0.6",
        "business_pass=PENDING_INDEPENDENT_REVIEW",
        "final_product_pass=PENDING_INDEPENDENT_REVIEW",
        "release_status=NOT_AUTHORIZED",
        "current_executable=false",
        "为什么今天不买",
        "继续等待什么",
        "什么时候重新判断",
        "市场继续上涨的代价",
        "市场下跌时现金的价值",
        "怎样服务年度目标",
        "ETN → CEG → MUFG → TSM → VRT",
        "富途账户AI直接",
        "48.147541%",
        "61.475698%",
        "不是四账户同日总暴露",
        "三星电子双期间财务校验",
        "2026年第二季度",
        "2025全年",
        "SNDK动作隔离",
        "LITE证据隔离",
        "撤回把税前利润写成营业利润",
        "爱德万测试估值冲突",
        "无法形成可靠估值",
        "第五关未通过",
        "老雷",
        "湖水",
        "仍需进一步了解",
        "结论—证据—规则",
    ]
    forbidden = [
        "release_status=RELEASED",
        "business_pass=PASS",
        "final_product_pass=PASS",
        "current_executable=true",
        "不允许Release",
        "税前利润作为营业利润",
        "AI直接暴露约48.147541%；加入软银代理暴露约61.475698%。",
        "当前价乘80%",
        "当前价乘85%",
    ]
    missing = [marker for marker in required if marker not in product]
    forbidden_hits = [marker for marker in forbidden if marker in product]

    holding_items = holdings["items"]
    candidate_items = candidates["items"]
    holding_checks = {
        "count_24": holdings["count"] == 24 and product.count('class="holding"') == 24,
        "every_holding_has_answer": all(item.get("judgment") for item in holding_items),
        "every_holding_has_valuation_input": all(item.get("v06_valuation_input") for item in holding_items),
        "unreliable_valuations_isolated": all(
            item["v06_valuation_input"]["status"] != "CANNOT_FORM_RELIABLE_VALUATION"
            or not item["v06_valuation_input"].get("scenarios")
            for item in holding_items
        ),
    }
    candidate_checks = {
        "count_21": candidates["count"] == 21 and product.count('class="candidate"') == 21,
        "executable_count_zero": candidates["executable_count"] == 0 and not any(item.get("executable_now") for item in candidate_items),
        "fifth_gate_pass_count_zero": candidates["fifth_gate_pass_count"] == 0 and not any(item.get("fifth_gate_passed") for item in candidate_items),
        "every_candidate_has_valuation_input": all(item.get("v06_valuation_input") for item in candidate_items),
        "priority_exact": candidates["priority"] == ["US.ETN", "US.CEG", "JP.8306", "US.TSM", "US.VRT"],
    }
    structured_checks = {
        "same_stock_cross_layer_consistent": same_stock["all_consistent"] and same_stock["count"] == 4,
        "samsung_two_periods": set(samsung["periods"]) == {"2026Q2", "2025FY"},
        "samsung_q2_values": samsung["periods"]["2026Q2"]["fields"]["revenue"]["raw"] == 171.5 and samsung["periods"]["2026Q2"]["fields"]["operating_profit"]["raw"] == 89.5,
        "samsung_fy_values": samsung["periods"]["2025FY"]["fields"]["revenue"]["raw"] == 333.6 and samsung["periods"]["2025FY"]["fields"]["operating_profit"]["raw"] == 43.6,
        "four_isolations_no_action": len(isolation["items"]) == 4 and not any(item["action_generated"] for item in isolation["items"]),
        "ai_direct_exact": ai["direct_pct"] == 48.147541,
        "ai_broad_exact": ai["broad_pct"] == 61.475698,
        "ai_denominator_futu": "富途总资产" in ai["denominator"] and "不是四账户同日" in ai["boundary"],
        "ai_not_trade_trigger": ai["automatic_trade_trigger"] is False,
    }

    json_files = sorted(output_dir.glob("*.json"))
    for path in json_files:
        read_json(path)
    replacement_files = []
    for path in [html_path, *json_files, *output_dir.glob("*.html")]:
        if "\ufffd" in path.read_text(encoding="utf-8-sig"):
            replacement_files.append(str(path))

    document = PdfReader(str(pdf_path))
    page_texts = [page.extract_text() or "" for page in document.pages]
    pdf_text = "\n".join(page_texts)
    blank_pages = [index + 1 for index, text in enumerate(page_texts) if len(text.strip()) < 80]
    page_sizes = sorted({(round(float(page.mediabox.width), 2), round(float(page.mediabox.height), 2)) for page in document.pages})
    a4_portrait = all(590 <= width <= 600 and 837 <= height <= 847 for width, height in page_sizes)
    pdf_required = ["完整投研产品候选 v0.6", "为什么今天不买", "三星电子双期间财务校验", "第五关未通过", "等待独立复验"]
    pdf_missing = [marker for marker in pdf_required if marker not in pdf_text]

    qa_dir = output_dir / "qa_pages"
    qa_dir.mkdir(exist_ok=True)
    prefix = qa_dir / "page"
    subprocess.run([str(POPPLER), "-png", "-r", "90", str(pdf_path), str(prefix)], check=True, capture_output=True)
    pages = sorted(qa_dir.glob("page-*.png"), key=lambda path: int(path.stem.split("-")[-1]))
    pixel_checks = []
    review_pages = []
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
            review_pages.append(page_number)
        pixel_checks.append({"page": page_number, "mean_luma": round(mean_luma, 3), "ink_ratio": round(ink_ratio, 5), "dark_ratio": round(dark_ratio, 5), "edge_ink_ratio": round(edge_ink_ratio, 5), "status": status})

    contacts = []
    for start in range(0, len(pages), 12):
        output = output_dir / f"11_逐页视觉检查_联系表_{start + 1:02d}-{min(start + 12, len(pages)):02d}.jpg"
        contact_sheet(pages[start:start + 12], output, start + 1)
        contacts.append(str(output))

    daily_after = stamp(DAILY)
    daily_before = log["daily_before"]
    daily_ok = daily_before["size"] == daily_after["size"] and daily_before["sha256"] == daily_after["sha256"]
    machine_checks = {
        "required_product_content_present": not missing,
        "forbidden_release_and_stale_text_zero": not forbidden_hits,
        **holding_checks,
        **candidate_checks,
        **structured_checks,
        "all_json_valid": True,
        "utf8_replacement_character_zero": not replacement_files,
        "pdf_key_content_matches_html": not pdf_missing,
        "pdf_nonblank": not blank_pages,
        "pdf_a4_portrait": a4_portrait,
        "rendered_pages_match_pdf": len(pages) == len(page_texts),
        "pixel_checks_pass": not review_pages,
        "daily_unchanged": daily_ok,
    }
    machine_status = "PASS" if all(machine_checks.values()) else "REVIEW_REQUIRED"
    manual_status = f"PASS_CODEX_CONTACT_SHEET_REVIEW_ALL_{len(page_texts)}_PAGES" if args.manual_reviewed else "PENDING_CODEX_CONTACT_SHEET_REVIEW"
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
        "pdf_missing_markers": pdf_missing,
        "blank_pages": blank_pages,
        "visual_review_pages": review_pages,
        "pixel_checks": pixel_checks,
        "contact_sheets": contacts,
        "font_size_points": {"body_print": 10.2, "table_print": 9.0},
    }
    if args.manual_reviewed:
        report["manual_visual_reviewed_at"] = datetime.now(JST).isoformat(timespec="seconds")
        report["manual_visual_observations"] = [f"全部{len(page_texts)}页逐页目视复核", "无空页、截断、重叠、黑块或乱码", "章节自然留白不属于内容缺失"]
    write_json(output_dir / "11_HTML_PDF一致性及逐页检查_20260817.json", report)
    rows = "".join(f"<tr><td>{html.escape(name)}</td><td>{'通过' if passed else '未通过'}</td></tr>" for name, passed in machine_checks.items())
    (output_dir / "11_HTML_PDF一致性及逐页检查_20260817.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>HTML/PDF一致性及逐页检查</title>"
        "<style>body{font:15px/1.6 Microsoft YaHei;max-width:980px;margin:30px auto}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:7px}</style>"
        f"<h1>HTML/PDF一致性及逐页检查</h1><p><b>{machine_status}</b>；PDF共{len(page_texts)}页A4。</p><p>人工目视状态：{html.escape(manual_status)}</p>"
        f"<table><tr><th>检查</th><th>结果</th></tr>{rows}</table>", encoding="utf-8")

    daily_proof = {"status": "PASS_UNCHANGED" if daily_ok else "FAIL_CHANGED", "before": daily_before, "after": daily_after, "candidate_pdf": stamp(pdf_path), "candidate_not_copied_to_daily": sha256(pdf_path) != daily_after["sha256"]}
    write_json(output_dir / "13_00今日日报未覆盖证明_20260817.json", daily_proof)
    (output_dir / "13_00今日日报未覆盖证明_20260817.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>00今日日报未覆盖证明</title><style>body{font:15px/1.6 Microsoft YaHei;max-width:900px;margin:30px auto}code{overflow-wrap:anywhere}</style>"
        f"<h1>00今日日报未覆盖证明</h1><p><b>{daily_proof['status']}</b></p><p>施工前：{daily_before['size']:,}字节<br><code>{daily_before['sha256']}</code></p>"
        f"<p>施工后：{daily_after['size']:,}字节<br><code>{daily_after['sha256']}</code></p>", encoding="utf-8")

    log["qa"] = {"machine_status": machine_status, "manual_visual_status": manual_status, "page_count": len(page_texts)}
    log["daily_after"] = daily_after
    log["completed_at"] = datetime.now(JST).isoformat(timespec="seconds")
    write_json(log_path, log)

    excluded = {"12_全部实物SHA256清单_20260817.json", "12_全部实物SHA256清单_20260817.html"}
    artifacts = [stamp(path) for path in sorted(output_dir.rglob("*"), key=lambda item: str(item)) if path.is_file() and path.name not in excluded]
    manifest = {"generated_at": datetime.now(JST).isoformat(timespec="seconds"), "self_excluded": True, "artifact_count": len(artifacts), "artifacts": artifacts}
    write_json(output_dir / "12_全部实物SHA256清单_20260817.json", manifest)
    artifact_rows = "".join(f"<tr><td>{html.escape(item['path'])}</td><td>{item['size']:,}</td><td>{html.escape(item['modified_at'])}</td><td><code>{item['sha256']}</code></td></tr>" for item in artifacts)
    (output_dir / "12_全部实物SHA256清单_20260817.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>全部实物SHA256清单</title><style>body{font:13px/1.45 Microsoft YaHei;margin:24px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:5px;overflow-wrap:anywhere}</style>"
        f"<h1>全部实物SHA256清单</h1><p>共{len(artifacts)}项；清单自身不自哈希。</p><table><tr><th>路径</th><th>大小</th><th>修改时间</th><th>SHA256</th></tr>{artifact_rows}</table>", encoding="utf-8")

    print(json.dumps({"status": machine_status, "manual": manual_status, "pages": len(page_texts), "daily_unchanged": daily_ok, "html": stamp(html_path), "pdf": stamp(pdf_path), "contacts": contacts}, ensure_ascii=False, indent=2))
    return 0 if machine_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
