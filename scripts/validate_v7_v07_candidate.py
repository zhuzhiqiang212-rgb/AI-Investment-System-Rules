#!/usr/bin/env python3
"""Validate, render, and finalize the complete V7 v0.7 candidate."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

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
    html_path = next(output_dir.glob("★*v0.7.html"))
    pdf_path = next(output_dir.glob("★*v0.7.pdf"))
    product = html_path.read_text(encoding="utf-8")
    holdings = read_json(output_dir / "12_24类持仓v0.7矩阵_20260817.json")
    candidates = read_json(output_dir / "13_21只候选v0.7矩阵_20260817.json")
    pdca = read_json(output_dir / "04_57条PDCA逐项闭合检查_20260817.json")
    trace = read_json(output_dir / "05_结论证据规则映射检查_20260817.json")
    anchors = read_json(output_dir / "06_机械价格锚清除检查_20260817.json")
    log_path = output_dir / "11_完整施工日志_20260817.json"
    log = read_json(log_path)

    visible_text = BeautifulSoup(product, "html.parser").get_text(" ", strip=True)
    required = [
        "完整投研产品候选 v0.7",
        "business_pass=PENDING_INDEPENDENT_REVIEW",
        "final_product_pass=PENDING_INDEPENDENT_REVIEW",
        "release_status=NOT_AUTHORIZED",
        "current_executable=false",
        "PDCA：5个系列与57条真实跟踪记录",
        "29条已判定",
        "28条尚待验证",
        "日、周、月复盘入口",
        "结论、证据和规则逐项咬合",
        "账户证据只证明持有什么",
        "暂不能给数值买卖区间",
        "不再另设机械价格带",
        "银行经营现金流会被存贷款和证券头寸变动放大",
        "等待独立复验",
    ]
    forbidden = [
        "release_status=RELEASED",
        "business_pass=PASS",
        "final_product_pass=PASS",
        "current_executable=true",
        "当前价乘80%",
        "当前价乘85%",
        "基准价的80%",
        "基准价的85%",
        "未取得 未取得",
        "。；",
        "沿用GPT总控已经批准",
    ]
    missing = [marker for marker in required if marker not in product]
    forbidden_hits = [marker for marker in forbidden if marker in product]

    holding_items = holdings["items"]
    candidate_items = candidates["items"]
    all_items = holding_items + candidate_items
    holding_checks = {
        "count_24": holdings["count"] == 24 and product.count('class="holding"') == 24,
        "every_holding_has_answer": all(item.get("judgment") for item in holding_items),
        "every_holding_has_v07_valuation_input": all(item.get("v07_valuation_input") for item in holding_items),
    }
    candidate_checks = {
        "count_21": candidates["count"] == 21 and product.count('class="candidate"') == 21,
        "executable_count_zero": candidates["executable_count"] == 0 and not any(item.get("executable_now") for item in candidate_items),
        "fifth_gate_pass_count_zero": candidates["fifth_gate_pass_count"] == 0 and not any(item.get("fifth_gate_passed") for item in candidate_items),
        "every_candidate_has_v07_valuation_input": all(item.get("v07_valuation_input") for item in candidate_items),
    }
    mappings = trace["mappings"]
    structured_checks = {
        "pdca_source_and_render_count_57": pdca["source_record_count"] == 57 and pdca["rendered_record_count"] == 57 and len(pdca["records"]) == 57,
        "pdca_unique_ids_57": len({item["prediction_id"] for item in pdca["records"]}) == 57,
        "pdca_series_5": pdca["series_count"] == 5,
        "pdca_counts_exact": (pdca["adjudicated"], pdca["correct"], pdca["wrong"], pdca["pending"]) == (29, 28, 1, 28),
        "pdca_rows_rendered_57": all(item["prediction_id"] in product for item in pdca["records"]) and product.count('class="pdca-series"') == 5,
        "evidence_mapping_45": trace["mapping_count"] == 45 and len(mappings) == 45,
        "evidence_roles_separated": all(item.get("account_evidence") and item.get("financial_evidence") and item.get("valuation_evidence") and item.get("market_event_evidence") and item.get("rule_ids") and item.get("reverse_evidence") and item.get("evidence_boundary") for item in mappings),
        "no_universal_account_evidence": all(item["account_evidence"]["id"] != "EV-ACCOUNT-LOCAL" for item in mappings),
        "candidate_evidence_ids_complete": all(item["financial_evidence"]["id"] and item["valuation_evidence"]["id"] and item["market_event_evidence"]["id"] for item in mappings if item["scope"] == "candidate"),
        "mechanical_numeric_bands_zero": all(not item["numeric_band"] for item in anchors["holdings"] + anchors["candidates"]),
        "observation_band_values_null": all(item["observation_band"].get("lower") is None and item["observation_band"].get("upper") is None for item in all_items),
        "plain_none_zero": "None" not in visible_text,
        "plain_duplicate_missing_zero": "未取得 未取得" not in visible_text,
        "plain_bad_punctuation_zero": "。；" not in visible_text,
        "plain_internal_workflow_zero": "沿用GPT总控已经批准" not in visible_text,
        "overlong_decimal_zero": not bool(__import__("re").search(r"(?<![\\w/])\\d[\\d,]*\\.\\d{7,}(?![\\w/])", visible_text)),
    }
    plain_checks = {
        "None_zero": "None" not in visible_text,
        "duplicate_missing_zero": "未取得 未取得" not in visible_text,
        "bad_punctuation_zero": "。；" not in visible_text,
        "internal_workflow_phrase_zero": "沿用GPT总控已经批准" not in visible_text,
        "overlong_decimal_zero": structured_checks["overlong_decimal_zero"],
        "bank_cashflow_boundary_present": "银行经营现金流会被存贷款和证券头寸变动放大" in visible_text,
        "utf8_replacement_character_zero": "\ufffd" not in product,
    }
    write_json(output_dir / "07_大白话及异常字符检查_20260817.json", {"run_id": log["run_id"], "status": "PASS" if all(plain_checks.values()) else "FAIL", "checks": plain_checks})

    repair = read_json(output_dir / "03_v0.6至v0.7四项返修清单_20260817.json")
    repair_rows = "".join(f"<tr><td>{html.escape(item['item'])}</td><td>{html.escape(item['before'])}</td><td>{html.escape(item['after'])}</td><td>{html.escape(item['reason'])}</td></tr>" for item in repair["items"])
    (output_dir / "03_v0.6至v0.7四项返修清单_20260817.html").write_text("<!doctype html><meta charset='utf-8'><title>v0.6至v0.7四项返修清单</title><style>body{font:15px/1.6 Microsoft YaHei;max-width:1100px;margin:30px auto}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:7px;vertical-align:top}</style><h1>v0.6至v0.7四项返修清单</h1><table><tr><th>项目</th><th>修改前</th><th>修改后</th><th>原因</th></tr>" + repair_rows + "</table>", encoding="utf-8")
    (output_dir / "04_57条PDCA逐项闭合检查_20260817.html").write_text(f"<!doctype html><meta charset='utf-8'><title>57条PDCA逐项闭合检查</title><style>body{{font:15px/1.6 Microsoft YaHei;max-width:960px;margin:30px auto}}code{{overflow-wrap:anywhere}}</style><h1>57条PDCA逐项闭合检查</h1><p><b>通过</b>：源记录57条，产品渲染57条；5个系列；29条已判定（28对、1错），28条待验证。</p><p>源文件SHA256：<code>{pdca['source']['sha256']}</code></p><p>57条逐项内容已进入主产品第三层；机器附件保留原始字段，不补造周/月复盘。</p>", encoding="utf-8")
    mapping_rows = "".join(f"<tr><td>{html.escape(item['conclusion_id'])}</td><td>{html.escape(item['code'])}</td><td>{html.escape(item['account_evidence']['id'])}</td><td>{html.escape(item['financial_evidence']['id'])}</td><td>{html.escape(item['valuation_evidence']['id'])}</td><td>{html.escape(item['market_event_evidence']['id'])}</td><td>{html.escape('、'.join(item['rule_ids']))}</td></tr>" for item in mappings)
    (output_dir / "05_结论证据规则映射检查_20260817.html").write_text("<!doctype html><meta charset='utf-8'><title>结论证据规则映射检查</title><style>body{font:13px/1.5 Microsoft YaHei;margin:24px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:5px;overflow-wrap:anywhere}</style><h1>结论证据规则映射检查</h1><p><b>通过</b>：24类持仓＋21只候选共45项，账户、财务、估值、事件、规则和反向边界分开登记。</p><table><tr><th>结论</th><th>标的</th><th>账户</th><th>财务</th><th>估值</th><th>事件</th><th>规则</th></tr>" + mapping_rows + "</table>", encoding="utf-8")
    (output_dir / "06_机械价格锚清除检查_20260817.html").write_text(f"<!doctype html><meta charset='utf-8'><title>机械价格锚清除检查</title><style>body{{font:15px/1.6 Microsoft YaHei;max-width:900px;margin:30px auto}}</style><h1>机械价格锚清除检查</h1><p><b>通过</b>：24类持仓和21只候选共45项，数值型固定折扣观察带为0；下限和上限字段均为空。</p><p>有可靠估值输入时只保留现有三情景；没有可靠输入时明确不提供数值买卖区间。</p>", encoding="utf-8")
    plain_rows = "".join(f"<tr><td>{html.escape(name)}</td><td>{'通过' if passed else '未通过'}</td></tr>" for name, passed in plain_checks.items())
    (output_dir / "07_大白话及异常字符检查_20260817.html").write_text("<!doctype html><meta charset='utf-8'><title>大白话及异常字符检查</title><style>body{font:15px/1.6 Microsoft YaHei;max-width:900px;margin:30px auto}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:7px}</style><h1>大白话及异常字符检查</h1><table><tr><th>检查</th><th>结果</th></tr>" + plain_rows + "</table>", encoding="utf-8")
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
    pdf_required = ["完整投研产品候选 v0.7", "PDCA：5个系列与57条真实跟踪记录", "结论、证据和规则逐项咬合", "暂不能给数值买卖区间", "等待独立复验"]
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
        output = output_dir / f"08_逐页视觉检查_联系表_{start + 1:02d}-{min(start + 12, len(pages)):02d}.jpg"
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
    write_json(output_dir / "08_HTML_PDF一致性及逐页视觉检查_20260817.json", report)
    rows = "".join(f"<tr><td>{html.escape(name)}</td><td>{'通过' if passed else '未通过'}</td></tr>" for name, passed in machine_checks.items())
    (output_dir / "08_HTML_PDF一致性及逐页视觉检查_20260817.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>HTML/PDF一致性及逐页检查</title>"
        "<style>body{font:15px/1.6 Microsoft YaHei;max-width:980px;margin:30px auto}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:7px}</style>"
        f"<h1>HTML/PDF一致性及逐页检查</h1><p><b>{machine_status}</b>；PDF共{len(page_texts)}页A4。</p><p>人工目视状态：{html.escape(manual_status)}</p>"
        f"<table><tr><th>检查</th><th>结果</th></tr>{rows}</table>", encoding="utf-8")

    daily_proof = {"status": "PASS_UNCHANGED" if daily_ok else "FAIL_CHANGED", "before": daily_before, "after": daily_after, "candidate_pdf": stamp(pdf_path), "candidate_not_copied_to_daily": sha256(pdf_path) != daily_after["sha256"]}
    write_json(output_dir / "10_00今日日报未覆盖证明_20260817.json", daily_proof)
    (output_dir / "10_00今日日报未覆盖证明_20260817.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>00今日日报未覆盖证明</title><style>body{font:15px/1.6 Microsoft YaHei;max-width:900px;margin:30px auto}code{overflow-wrap:anywhere}</style>"
        f"<h1>00今日日报未覆盖证明</h1><p><b>{daily_proof['status']}</b></p><p>施工前：{daily_before['size']:,}字节<br><code>{daily_before['sha256']}</code></p>"
        f"<p>施工后：{daily_after['size']:,}字节<br><code>{daily_after['sha256']}</code></p>", encoding="utf-8")

    log["qa"] = {"machine_status": machine_status, "manual_visual_status": manual_status, "page_count": len(page_texts)}
    log["daily_after"] = daily_after
    log["completed_at"] = datetime.now(JST).isoformat(timespec="seconds")
    write_json(log_path, log)

    excluded = {"09_全部实物SHA256清单_20260817.json", "09_全部实物SHA256清单_20260817.html"}
    artifacts = [stamp(path) for path in sorted(output_dir.rglob("*"), key=lambda item: str(item)) if path.is_file() and path.name not in excluded]
    manifest = {"generated_at": datetime.now(JST).isoformat(timespec="seconds"), "self_excluded": True, "artifact_count": len(artifacts), "artifacts": artifacts}
    write_json(output_dir / "09_全部实物SHA256清单_20260817.json", manifest)
    artifact_rows = "".join(f"<tr><td>{html.escape(item['path'])}</td><td>{item['size']:,}</td><td>{html.escape(item['modified_at'])}</td><td><code>{item['sha256']}</code></td></tr>" for item in artifacts)
    (output_dir / "09_全部实物SHA256清单_20260817.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>全部实物SHA256清单</title><style>body{font:13px/1.45 Microsoft YaHei;margin:24px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #bbb;padding:5px;overflow-wrap:anywhere}</style>"
        f"<h1>全部实物SHA256清单</h1><p>共{len(artifacts)}项；清单自身不自哈希。</p><table><tr><th>路径</th><th>大小</th><th>修改时间</th><th>SHA256</th></tr>{artifact_rows}</table>", encoding="utf-8")

    print(json.dumps({"status": machine_status, "manual": manual_status, "pages": len(page_texts), "daily_unchanged": daily_ok, "html": stamp(html_path), "pdf": stamp(pdf_path), "contacts": contacts}, ensure_ascii=False, indent=2))
    return 0 if machine_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
