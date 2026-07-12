#!/usr/bin/env python
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KB = ROOT / "Knowledge_Base"
DEFAULT_HOLDINGS = ROOT / "data/accounts/unified_holdings_latest.json"
DEFAULT_OUT_DIR = ROOT / "data/research"


HIGH_VALUE_TERMS = ["老雷", "深度研究", "laolei", "lei", "deep research"]
V1_SOURCE_TERMS = ["老雷", "湖水", "Drive", "drive", "知识库", "Knowledge_Base"]
TEXT_EXTS = {".md", ".txt", ".csv", ".json"}
EXCLUDE_TITLE_TERMS = ["索引", "主题索引", "总框架", "来源清单", "Index", "index"]


def read_text_lossless(path: Path) -> str:
    data = path.read_bytes()
    for enc in ["utf-8", "utf-8-sig", "gb18030"]:
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def clean_for_json(value: str) -> str:
    return value.replace("\ufffd", "").replace(chr(63), "？")


def sha256_text(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def load_holdings_terms(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    terms: set[str] = set()
    for entry in data.get("entries", []):
        for key in ["ticker", "code", "name"]:
            value = entry.get(key)
            if value:
                text = str(value).strip()
                if text:
                    terms.add(text)
                    if "." in text:
                        terms.add(text.split(".")[0])
    for row in data.get("aggregate_by_ticker", []):
        for key in ["ticker", "name"]:
            value = row.get(key)
            if value:
                text = str(value).strip()
                if text:
                    terms.add(text)
    return sorted(t for t in terms if len(t) >= 2)


def file_date_hit(path: Path, target: dt.date) -> bool:
    try:
        mdate = dt.datetime.fromtimestamp(path.stat().st_mtime).date()
    except OSError:
        return False
    if mdate == target:
        return True
    name = path.name
    patterns = [
        target.strftime("%Y-%m-%d"),
        target.strftime("%Y%m%d"),
        target.strftime("%y-%m-%d"),
        target.strftime("%y%m%d"),
    ]
    return any(p in name for p in patterns)



def is_index_or_framework_file(path: Path, text_head: str) -> bool:
    title = f"{path.stem}\n{text_head[:300]}"
    return any(term in title for term in EXCLUDE_TITLE_TERMS)

def source_label(path: Path, text_head: str) -> str:
    blob = f"{path.name} {text_head}"
    if "老雷" in blob or "laolei" in blob.lower() or "lei" in blob.lower():
        return "老雷"
    if "湖水" in blob:
        return "湖水"
    if "Drive" in str(path) or "drive" in str(path).lower():
        return "Drive"
    return "Knowledge_Base"


def collect_files(roots: list[Path]) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    reasons: list[str] = []
    for root in roots:
        if not root.exists():
            reasons.append(f"root_missing:{root}")
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in TEXT_EXTS:
                files.append(path)
    return files, reasons


def build_candidates(roots: list[Path], holdings_terms: list[str], target: dt.date, limit: int) -> dict[str, Any]:
    files, root_reasons = collect_files(roots)
    seen: set[str] = set()
    candidates: list[dict[str, Any]] = []
    for path in files:
        text = read_text_lossless(path)
        fp = sha256_text(text)
        if fp in seen:
            continue
        seen.add(fp)
        head = text[:2000]
        if is_index_or_framework_file(path, head):
            continue
        hay = f"{path.name}\n{head}"
        matched_terms = [term for term in holdings_terms if term and term in hay]
        today_new = file_date_hit(path, target)
        label = source_label(path, head)
        high_value = any(term.lower() in hay.lower() for term in HIGH_VALUE_TERMS)
        v1_source = any(term.lower() in f"{path} {head}".lower() for term in V1_SOURCE_TERMS)
        reasons: list[str] = []
        if today_new:
            reasons.append("today_new")
        if matched_terms:
            reasons.append("holding_related")
        if high_value:
            reasons.append("high_value_forced")
        if not reasons:
            continue
        if not v1_source and not high_value:
            continue
        try:
            mtime = dt.datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
        except OSError:
            mtime = ""
        candidates.append({
            "source": clean_for_json(label),
            "path": clean_for_json(str(path)),
            "fingerprint_sha256": fp,
            "mtime": mtime,
            "matched_reasons": reasons,
            "matched_terms": [clean_for_json(x) for x in matched_terms[:12]],
            "codex_note": "只做机械预筛，不判断重要性；交 Claude 理解岗七维打标。",
        })
    candidates.sort(key=lambda c: (
        0 if "high_value_forced" in c["matched_reasons"] else 1,
        0 if "today_new" in c["matched_reasons"] else 1,
        0 if "holding_related" in c["matched_reasons"] else 1,
        c["path"],
    ))
    limited = candidates[:limit]
    empty_reason = ""
    if not files:
        empty_reason = "未读到资料文件；输出空清单。"
    elif not limited:
        empty_reason = "未发现今日新增、高价值源或当前持仓高相关资料；输出空清单。"
    return {
        "task_id": "TASK-2026-07-02-013",
        "mode": "read_only_prescreen_no_judgement_no_order_no_publish",
        "target_date": target.isoformat(),
        "input_roots": [clean_for_json(str(r)) for r in roots],
        "holdings_terms_count": len(holdings_terms),
        "scanned_file_count": len(files),
        "deduped_candidate_count_before_limit": len(candidates),
        "candidate_count": len(limited),
        "limit": limit,
        "empty_reason": clean_for_json(empty_reason),
        "root_warnings": [clean_for_json(r) for r in root_reasons],
        "candidates": limited,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Research intake mechanical prescreen.")
    parser.add_argument("--date", default=dt.date.today().isoformat())
    parser.add_argument("--knowledge-base", default=str(DEFAULT_KB))
    parser.add_argument("--drive-dir", action="append", default=[])
    parser.add_argument("--holdings", default=str(DEFAULT_HOLDINGS))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--limit", type=int, default=15)
    args = parser.parse_args()

    target = dt.date.fromisoformat(args.date)
    roots = [Path(args.knowledge_base)] + [Path(p) for p in args.drive_dir]
    holdings_terms = load_holdings_terms(Path(args.holdings))
    result = build_candidates(roots, holdings_terms, target, max(1, args.limit))

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"candidates_{target.strftime('%Y%m%d')}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    reread = out_path.read_text(encoding="utf-8")
    if "\ufffd" in reread or chr(63) in reread:
        raise SystemExit("bad char detected in output")
    print(json.dumps({
        "output": str(out_path),
        "candidate_count": result["candidate_count"],
        "scanned_file_count": result["scanned_file_count"],
        "sources": sorted({c["source"] for c in result["candidates"]}),
        "empty_reason": result["empty_reason"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
