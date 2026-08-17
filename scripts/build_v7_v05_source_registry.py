from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    args = parser.parse_args()
    out = Path(args.dir).resolve()
    if ROOT not in out.parents:
        raise SystemExit("Output directory must remain under project root")
    audit = json.loads((out / "02_45项财务异常复扫矩阵_20260817.json").read_text(encoding="utf-8"))
    now = datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds")
    samsung_urls = {
        "https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2026_2Q_conference_eng.pdf",
        "https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2025_4Q_conference_eng.pdf",
        "https://news.samsung.com/nl/samsung-electronics-announces-fourth-quarter-and-fy-2025-results",
    }
    remote_urls = sorted({x.get("source_url") for x in audit["items"] if x.get("source_url")} | samsung_urls)
    local_paths = [
        ROOT / "output/candidates/2026-08-17/V7-V05-COMPLETE-20260817-080933-JST/04_更新后的24类持仓矩阵_20260817.json",
        ROOT / "output/candidates/2026-08-17/V7-V05-COMPLETE-20260817-080933-JST/05_更新后的21只五关轨迹_20260817.json",
        ROOT / "output/decision_inputs/2026-08-17/V7-V04-CRITICAL-EVIDENCE-20260817-003853-JST/02_24类持仓业务判断输入_20260817.json",
        ROOT / "output/decision_inputs/2026-08-17/V7-V04-CRITICAL-EVIDENCE-20260817-003853-JST/03_21只候选五关输入_20260817.json",
        ROOT / "data/valuation/val_inputs.json",
        ROOT / "data/screen/gate_20260811.json",
        ROOT / "data/accounts/futu_positions_20260817.json",
    ]
    registry = {
        "generated_at": now,
        "remote_formal_sources": [
            {
                "url": url,
                "local_copy": False,
                "size": None,
                "sha256": None,
                "hash_boundary": "本包登记直接原文链接；未下载的远程页面不伪造本地大小或SHA256。",
            }
            for url in remote_urls
        ],
        "local_input_artifacts": [
            {
                "path": str(path),
                "size": path.stat().st_size,
                "modified_at": datetime.fromtimestamp(path.stat().st_mtime, ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds"),
                "sha256": sha256(path),
            }
            for path in local_paths
        ],
    }
    target = out / "06_正式来源及本地输入注册表_20260817.json"
    target.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"remote_sources": len(remote_urls), "local_inputs": len(local_paths), "path": str(target)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
