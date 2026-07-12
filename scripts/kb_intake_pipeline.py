#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INCOMING = ROOT / "Knowledge_Base/incoming"
DEFAULT_LOG_DIR = ROOT / "data/research"
TEXT_EXTS = {".md", ".txt", ".csv", ".json", ".pdf", ".docx", ".xlsx", ".pptx"}


def safe_text(value: str) -> str:
    return value.replace("\ufffd", "").replace(chr(63), "？")


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def source_name(path: Path) -> str:
    parts = [p for p in path.parts]
    joined = " ".join(parts)
    if "湖水" in joined:
        return "湖水"
    if "老雷" in joined:
        return "老雷"
    if "TXT" in joined or "流水" in joined:
        return "TXT流水账"
    return path.parent.name or "unknown"


def unique_dest(incoming: Path, source: str, path: Path, digest: str) -> Path:
    suffix = path.suffix
    stem = safe_text(path.stem)[:80]
    folder = incoming / safe_text(source)
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{stem}_{digest[:12]}{suffix}"


def scan_roots(roots: list[Path], days: int, incoming: Path, log_dir: Path, run_date: str) -> dict[str, Any]:
    cutoff = datetime.now() - timedelta(days=days)
    scanned_roots = []
    warnings = []
    hits = []
    copied = []
    seen = set()
    for root in roots:
        if not root.exists():
            warnings.append(f"root_missing:{root}")
            continue
        scanned_roots.append(str(root))
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_EXTS:
                continue
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
            except OSError:
                continue
            if mtime < cutoff:
                continue
            digest = file_sha256(path)
            if digest in seen:
                continue
            seen.add(digest)
            source = source_name(path)
            dest = unique_dest(incoming, source, path, digest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            record = {
                "original_path": safe_text(str(path)),
                "incoming_path": safe_text(str(dest)),
                "source": safe_text(source),
                "file_date": mtime.isoformat(timespec="seconds"),
                "fingerprint_sha256": digest,
            }
            hits.append(record)
            copied.append(record)
    log_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "task_id": "TASK-2026-07-02-015",
        "mode": "read_only_copy_no_judgement_no_order_no_publish",
        "run_date": run_date,
        "days": days,
        "scanned_root_count": len(roots),
        "existing_root_count": len(scanned_roots),
        "hit_count": len(hits),
        "copied_count": len(copied),
        "source_distribution": dict(Counter(x["source"] for x in copied)),
        "warnings": [safe_text(x) for x in warnings],
        "records": copied,
    }
    out = log_dir / f"kb_intake_log_{run_date.replace('-', '')}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    reread = out.read_text(encoding="utf-8")
    if "\ufffd" in reread or chr(63) in reread:
        raise SystemExit("bad char detected in log")
    result["log_path"] = str(out)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Mechanical KB intake pipeline.")
    parser.add_argument("--root", action="append", default=[], help="raw research root directory")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--incoming", default=str(DEFAULT_INCOMING))
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    parser.add_argument("--run-date", default=datetime.now().strftime("%Y%m%d"))
    args = parser.parse_args()
    roots = [Path(x) for x in args.root]
    result = scan_roots(roots, args.days, Path(args.incoming), Path(args.log_dir), args.run_date)
    print(json.dumps({
        "scanned_root_count": result["scanned_root_count"],
        "existing_root_count": result["existing_root_count"],
        "hit_count": result["hit_count"],
        "copied_count": result["copied_count"],
        "source_distribution": result["source_distribution"],
        "warnings": result["warnings"],
        "log_path": result["log_path"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
