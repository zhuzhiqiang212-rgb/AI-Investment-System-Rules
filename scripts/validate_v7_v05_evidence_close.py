from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
V05_DIR = ROOT / "output/candidates/2026-08-17/V7-V05-COMPLETE-20260817-080933-JST"
V05_HTML = V05_DIR / "★2026-08-17完整投研产品候选_v0.5.html"
V05_PDF = V05_DIR / "★2026-08-17完整投研产品候选_v0.5.pdf"
DAILY = ROOT / "00_请先看这里/00_今日日报.pdf"
V05_HTML_SHA = "6521DDEE6F6885F8799A6E4F135ED3AA9A375CB4970D2406027091225BEB7D29"
V05_PDF_SHA = "E6B467B8E24588389A0F98E923D44366CA127C5D510945C1169D80C87055D898"
DAILY_SHA = "12C8CB2CF5879C37F2876FEEF8CB6144A3AED6A5D48D89A06A140F2A234DB7FA"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    args = parser.parse_args()
    out = Path(args.dir).resolve()
    if ROOT not in out.parents:
        raise SystemExit("Output directory must remain under project root")

    samsung = read_json(out / "01_三星财务字段纠错报告_20260817.json")
    audit = read_json(out / "02_45项财务异常复扫矩阵_20260817.json")
    holdings = read_json(out / "03_24类持仓估值判断输入表_20260817.json")
    candidates = read_json(out / "04_21只候选第五关估值输入表_20260817.json")
    ai = read_json(out / "05_AI暴露口径校验表_20260817.json")
    html_path = out / "V7_v0.5财务真实性纠错及估值判断输入闭合_20260817.html"
    text = html_path.read_text(encoding="utf-8")

    q2 = samsung["periods"]["2026Q2"]["fields"]
    fy = samsung["periods"]["2025FY"]["fields"]
    checks = {
        "v05_html_unchanged": sha256(V05_HTML) == V05_HTML_SHA,
        "v05_pdf_unchanged": sha256(V05_PDF) == V05_PDF_SHA,
        "daily_unchanged": sha256(DAILY) == DAILY_SHA,
        "samsung_q2_revenue": q2["revenue"]["converted_krw"] == 171_500_000_000_000,
        "samsung_q2_operating_profit": q2["operating_profit"]["converted_krw"] == 89_500_000_000_000,
        "samsung_q2_net_vs_parent_separate": q2["net_profit"]["converted_krw"] == 71_600_000_000_000 and q2["profit_attributable_to_owners"]["converted_krw"] == 71_300_000_000_000,
        "samsung_fy_revenue": fy["revenue"]["converted_krw"] == 333_600_000_000_000,
        "samsung_fy_operating_profit": fy["operating_profit"]["converted_krw"] == 43_600_000_000_000,
        "audit_count_45": audit.get("count") == 45 and len(audit.get("items", [])) == 45,
        "holding_count_24": holdings.get("count") == 24 and len(holdings.get("items", [])) == 24,
        "candidate_count_21": candidates.get("count") == 21 and len(candidates.get("items", [])) == 21,
        "candidate_gate_not_passed": all(x.get("fifth_gate_decision") == "FIFTH_GATE_INPUT_ONLY_NOT_PASSED" for x in candidates["items"]),
        "observation_lines_separated_holdings": all(x.get("observation_line_separated") is True for x in holdings["items"]),
        "observation_lines_separated_candidates": all(x.get("observation_line_separated") is True for x in candidates["items"]),
        "ai_direct_exact": ai.get("direct_pct") == 48.147541,
        "ai_broad_exact": ai.get("broad_pct") == 61.475698,
        "ai_futu_denominator_named": "富途总资产" in ai.get("denominator", ""),
        "ai_not_all_accounts": "不是四账户同日暴露" in ai.get("boundary", ""),
        "html_boundary_no_release": "不Release" in text and "不生成订单" in text,
        "html_utf8_replacement_zero": "\ufffd" not in text and b"\xef\xbf\xbd" not in html_path.read_bytes(),
        "samsung_source_direct": "2026_2Q_conference_eng.pdf" in samsung["periods"]["2026Q2"]["source_url"],
        "formal_sources_present": all(x.get("source_url") or x.get("status") == "NOT_APPLICABLE_ASSET" for x in audit["items"]),
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise SystemExit("Validation failed: " + ", ".join(failed))

    json_files = sorted(out.glob("*.json"))
    for path in json_files:
        read_json(path)
        if b"\xef\xbf\xbd" in path.read_bytes():
            raise SystemExit(f"UTF-8 replacement bytes found: {path.name}")

    now = datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds")
    qa = {
        "status": "PASS", "checked_at": now, "checks": checks,
        "json_count": len(json_files), "utf8_replacement_count": 0,
        "v05_hashes": {"html": sha256(V05_HTML), "pdf": sha256(V05_PDF)},
        "daily_hash": sha256(DAILY),
    }
    write_json(out / "07_测试及UTF8检查记录_20260817.json", qa)

    files = sorted(x for x in out.iterdir() if x.is_file() and not x.name.startswith("08_全部实物"))
    manifest = {
        "generated_at": now, "self_hash_excluded": True,
        "items": [{
            "path": str(path), "size": path.stat().st_size,
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime, ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds"),
            "sha256": sha256(path),
        } for path in files],
        "source_v05": [
            {"path": str(V05_HTML), "size": V05_HTML.stat().st_size, "sha256": sha256(V05_HTML)},
            {"path": str(V05_PDF), "size": V05_PDF.stat().st_size, "sha256": sha256(V05_PDF)},
        ],
        "daily": {"path": str(DAILY), "size": DAILY.stat().st_size, "sha256": sha256(DAILY)},
    }
    write_json(out / "08_全部实物路径大小时间SHA256_20260817.json", manifest)

    rows = "".join(
        f"<tr><td>{item['path']}</td><td>{item['size']}</td><td>{item['modified_at']}</td><td><code>{item['sha256']}</code></td></tr>"
        for item in manifest["items"]
    )
    (out / "08_全部实物路径大小时间SHA256_20260817.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>全部实物SHA256</title><style>body{font-family:Microsoft YaHei,Arial;padding:24px}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border:1px solid #bbb;padding:7px;text-align:left;word-break:break-all}th{background:#eee}</style>"
        "<h1>全部实物路径、大小、时间及SHA256</h1><p>清单自身哈希不递归登记。</p><table><tr><th>路径</th><th>大小</th><th>修改时间</th><th>SHA256</th></tr>" + rows + "</table>",
        encoding="utf-8",
    )
    print(json.dumps({"status": "PASS", "checks": len(checks), "files": len(manifest["items"]), "output_dir": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
