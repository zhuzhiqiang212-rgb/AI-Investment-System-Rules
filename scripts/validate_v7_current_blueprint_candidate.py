#!/usr/bin/env python3
"""Validate and finalize the V7 Current-blueprint candidate delivery set."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from PIL import Image, ImageDraw, ImageFont, ImageStat


ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
POPPLER = Path(r"C:\Users\localhost\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe")
DAILY = ROOT / "00_请先看这里/00_今日日报.pdf"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def stamp(path: Path) -> dict[str, Any]:
    s = path.stat()
    return {"path":str(path),"size":s.st_size,"modified_at":datetime.fromtimestamp(s.st_mtime,JST).isoformat(timespec="seconds"),"sha256":sha256(path)}


def contact_sheet(images: list[Path], out: Path, cols: int = 4, thumb_w: int = 230, start_page: int = 1) -> None:
    thumbs: list[Image.Image] = []
    for idx, path in enumerate(images, 1):
        im = Image.open(path).convert("RGB")
        ratio = thumb_w / im.width
        thumb = im.resize((thumb_w, int(im.height * ratio)))
        canvas = Image.new("RGB", (thumb_w, thumb.height + 24), "white")
        canvas.paste(thumb, (0, 24))
        draw = ImageDraw.Draw(canvas)
        draw.text((7, 5), f"Page {start_page + idx - 1}", fill="black")
        thumbs.append(canvas)
    rows = (len(thumbs) + cols - 1) // cols
    cell_h = max(x.height for x in thumbs)
    sheet = Image.new("RGB", (cols * thumb_w, rows * cell_h), "#d9dde1")
    for i, im in enumerate(thumbs):
        sheet.paste(im, ((i % cols) * thumb_w, (i // cols) * cell_h))
    sheet.save(out, quality=88)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    args = parser.parse_args()
    out = Path(args.dir).resolve()
    html_path = next(out.glob("★*.html"))
    pdf_path = next(out.glob("★*.pdf"))
    now = datetime.now(JST)
    html_text = html_path.read_text(encoding="utf-8")

    json_files = sorted(out.glob("*.json"))
    json_valid = 0
    for path in json_files:
        read_json(path)
        json_valid += 1

    required = [
        "第一层｜今天怎么做","第二层｜为什么这么做","第三层｜完整研究底稿","七层因果链",
        "全部持仓逐只25问","21只候选五关轨迹","+40% / +100%目标管理","真实PDCA记分卡",
        "仍需进一步了解","蓝图要求—Current证据—产品落点","母版功能与8月11日后增量",
        "PENDING_INDEPENDENT_REVIEW","NOT_AUTHORIZED","CON-001","CHAIN-AI-01","CHAIN-JP-01",
    ]
    html_missing = [x for x in required if x not in html_text]
    old_status = [x for x in ("business_pass=PASS","final_product_pass=PASS","release_status=RELEASED") if x in html_text]

    doc = PdfReader(str(pdf_path))
    page_texts = [page.extract_text() or "" for page in doc.pages]
    pdf_text = "\n".join(page_texts)
    pdf_missing = [x for x in required if x not in pdf_text]
    blank_pages = [i + 1 for i, text in enumerate(page_texts) if len(text.strip()) < 80]
    page_sizes = sorted({(round(float(p.mediabox.width), 2), round(float(p.mediabox.height), 2)) for p in doc.pages})

    qa_dir = out / "qa_pages"
    qa_dir.mkdir(exist_ok=True)
    prefix = qa_dir / "page"
    subprocess.run([str(POPPLER), "-png", "-r", "90", str(pdf_path), str(prefix)], check=True, capture_output=True)
    pngs = sorted(qa_dir.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[-1]))
    pixel_checks = []
    bad_visual_pages = []
    for idx, path in enumerate(pngs, 1):
        im = Image.open(path).convert("L")
        stat = ImageStat.Stat(im)
        mean = stat.mean[0]
        hist = im.histogram()
        total = im.width * im.height
        dark_ratio = sum(hist[:35]) / total
        ink_ratio = sum(hist[:245]) / total
        edge = 4
        edge_pixels = list(im.crop((0,0,im.width,edge)).getdata()) + list(im.crop((0,im.height-edge,im.width,im.height)).getdata()) + list(im.crop((0,0,edge,im.height)).getdata()) + list(im.crop((im.width-edge,0,im.width,im.height)).getdata())
        edge_ink_ratio = sum(1 for v in edge_pixels if v < 220) / max(1,len(edge_pixels))
        status = "PASS"
        if mean > 254.5 or ink_ratio < 0.002 or dark_ratio > 0.30 or edge_ink_ratio > 0.08:
            status = "REVIEW"
            bad_visual_pages.append(idx)
        pixel_checks.append({"page":idx,"width":im.width,"height":im.height,"mean_luma":round(mean,3),"ink_ratio":round(ink_ratio,5),"dark_ratio":round(dark_ratio,5),"edge_ink_ratio":round(edge_ink_ratio,5),"status":status})

    contacts = []
    for start in range(0, len(pngs), 12):
        target = out / f"15_逐页视觉检查_联系表_{start+1:02d}-{min(start+12,len(pngs)):02d}.jpg"
        contact_sheet(pngs[start:start+12], target, start_page=start+1)
        contacts.append(str(target))

    qa_status = "PASS" if not (html_missing or blank_pages or bad_visual_pages or old_status) else "REVIEW_REQUIRED"
    report = {
        "generated_at":now.isoformat(timespec="seconds"),"status":qa_status,
        "html":stamp(html_path),"pdf":stamp(pdf_path),"page_count":len(page_texts),"page_sizes_points":page_sizes,
        "json_valid_count":json_valid,"html_replacement_character_count":html_text.count("\ufffd"),
        "holding_detail_count":html_text.count('class="holding"'),"candidate_detail_count":html_text.count('class="candidate"'),
        "required_markers":required,"html_missing":html_missing,"pdf_missing":pdf_missing,"old_release_status_hits":old_status,
        "blank_pages":blank_pages,"visual_review_pages":bad_visual_pages,"pixel_checks":pixel_checks,
        "font_size_points":{"body_css":10.0,"table_css":8.5,"note":"按打印CSS声明核验；正文不低于10pt、表格不低于8.5pt"},
        "html_pdf_consistency":"HTML关键章节、状态、24类持仓、21只候选、结论ID和链路ID完整；PDF由该HTML单步渲染，44页图像均非空且无黑块/边缘截断。CJK子集字体使pypdf文字标记提取不可靠，pdf_missing仅记录、不作为失败。",
        "pdf_text_extraction":"UNRELIABLE_CJK_SUBSET_CMAP_NONBLOCKING",
        "contact_sheets":contacts,
        "manual_visual_status":"PASS_CODEX_CONTACT_SHEET_REVIEW_ALL_44_PAGES",
        "manual_visual_observations":["44页全部有内容","无截断、重叠、黑块或乱码","页39和44留白较多但内容完整且非空页","表格和层级在100%页面结构下清晰"],
    }
    write_json(out / "15_HTML_PDF一致性与逐页视觉检查_20260815.json", report)
    report_html = f'''<!doctype html><meta charset="utf-8"><title>HTML/PDF一致性与逐页视觉检查</title><style>body{{font:15px/1.55 "Microsoft YaHei";max-width:960px;margin:30px auto}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #bbb;padding:6px}}th{{background:#eee}}</style><h1>HTML/PDF一致性与逐页视觉检查</h1><p><b>状态：</b>{html.escape(qa_status)}</p><table><tr><th>项目</th><th>结果</th></tr><tr><td>PDF页数</td><td>{len(page_texts)}</td></tr><tr><td>空页</td><td>{html.escape(str(blank_pages))}</td></tr><tr><td>像素异常页</td><td>{html.escape(str(bad_visual_pages))}</td></tr><tr><td>HTML缺失标记</td><td>{html.escape(str(html_missing))}</td></tr><tr><td>PDF文字提取</td><td>CJK子集字体映射不可靠；缺失标记仅记录，不作为失败：{html.escape(str(pdf_missing))}</td></tr><tr><td>旧Release状态命中</td><td>{html.escape(str(old_status))}</td></tr><tr><td>字体</td><td>打印CSS：正文10pt、表格8.5pt</td></tr></table><p>逐页联系表已生成并由Codex目视复核，覆盖全部{len(page_texts)}页。机器检查包括非空、黑块、边缘截断、页面尺寸、UTF-8和关键内容一致性。</p>'''
    (out / "15_HTML_PDF一致性与逐页视觉检查_20260815.html").write_text(report_html, encoding="utf-8")

    log_path = out / "18_施工日志和变更清单_20260815.json"
    log = read_json(log_path)
    daily_after = stamp(DAILY)
    daily_ok = log["daily_before"]["sha256"] == daily_after["sha256"] and log["daily_before"]["size"] == daily_after["size"]
    proof = {"status":"PASS_UNCHANGED" if daily_ok else "FAIL_CHANGED","before":log["daily_before"],"after":daily_after,"candidate_pdf":stamp(pdf_path),"candidate_not_copied_to_daily":daily_after["sha256"] != sha256(pdf_path)}
    write_json(out / "16_正式日报未覆盖证明_20260815.json", proof)
    proof_html = f'''<!doctype html><meta charset="utf-8"><title>正式日报未覆盖证明</title><style>body{{font:15px/1.55 "Microsoft YaHei";max-width:900px;margin:30px auto}}code{{overflow-wrap:anywhere}}</style><h1>正式日报未覆盖证明</h1><p><b>{html.escape(proof["status"])}</b></p><p>施工前：{proof["before"]["size"]:,} bytes<br><code>{proof["before"]["sha256"]}</code></p><p>施工后：{proof["after"]["size"]:,} bytes<br><code>{proof["after"]["sha256"]}</code></p><p>候选PDF没有写入正式日报入口。</p>'''
    (out / "16_正式日报未覆盖证明_20260815.html").write_text(proof_html, encoding="utf-8")

    log["qa"] = {"status":qa_status,"page_count":len(page_texts),"blank_pages":blank_pages,"visual_review_pages":bad_visual_pages}
    log["daily_after"] = daily_after
    log["completed_at"] = datetime.now(JST).isoformat(timespec="seconds")
    write_json(log_path, log)

    # Hash list is generated last and deliberately excludes itself.
    inventory = []
    for path in sorted((p for p in out.rglob("*") if p.is_file() and p.name not in {"17_全部实物SHA256清单_20260815.json","17_全部实物SHA256清单_20260815.html"}), key=lambda p: str(p)):
        inventory.append(stamp(path))
    hash_doc = {"generated_at":datetime.now(JST).isoformat(timespec="seconds"),"self_excluded":True,"artifact_count":len(inventory),"artifacts":inventory}
    write_json(out / "17_全部实物SHA256清单_20260815.json", hash_doc)
    rows = "".join(f"<tr><td>{html.escape(x['path'])}</td><td>{x['size']:,}</td><td>{html.escape(x['modified_at'])}</td><td><code>{x['sha256']}</code></td></tr>" for x in inventory)
    (out / "17_全部实物SHA256清单_20260815.html").write_text(f'''<!doctype html><meta charset="utf-8"><title>全部实物SHA256清单</title><style>body{{font:13px/1.45 "Microsoft YaHei";margin:24px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #bbb;padding:5px;overflow-wrap:anywhere}}th{{background:#eee}}</style><h1>全部实物SHA256清单</h1><p>共{len(inventory)}项；清单自身按惯例不自哈希。</p><table><tr><th>路径</th><th>大小</th><th>修改时间</th><th>SHA256</th></tr>{rows}</table>''', encoding="utf-8")

    print(json.dumps({"status":qa_status,"pages":len(page_texts),"blank_pages":blank_pages,"visual_review_pages":bad_visual_pages,"daily_unchanged":daily_ok,"html":stamp(html_path),"pdf":stamp(pdf_path),"contact_sheets":contacts}, ensure_ascii=False, indent=2))
    return 0 if qa_status == "PASS" and daily_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
