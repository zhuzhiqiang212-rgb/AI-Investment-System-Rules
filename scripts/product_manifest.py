#!/usr/bin/env python3
"""防回滚哨兵 + 主控进度回写（丙2/丙3·董事局工单2026-07-17）· 只读不下单

丙2 哨兵：每次生产把「run_id + 各册字节哈希」写进 data/product_manifest.json（随代码推 GitHub 侧）。
        开工脚本比对 G盘实物哈希：不符 → 报"疑似被旧版覆盖"，而不是默默拿旧册当今天的产品。
        (G盘是 Google Drive 同步盘，历史上出过被旧版本回滚覆盖的情况。)
丙3 回写：每次生产由脚本把「当前正式产品=哪五册 / 数据日 / 更新时间」回写进 ★开工必读_主控文件.html
        的进度块——别再停在 07-04/07-14 那种早就过期的日期上。

用法：
  from product_manifest import write_manifest, sync_master   # 渲染器出厂后调用
  python scripts/product_manifest.py --check                 # 开工比对(哨兵)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
MANIFEST = ROOT / "data" / "product_manifest.json"
MASTER = ROOT / "00_请先看这里" / "★开工必读_主控文件.html"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def write_manifest(date: str, run_id: str, scan_jst: str, filenames: list[str]) -> dict:
    """丙2：生产完把各册实物哈希登记下来(随 scripts 一起推 GitHub·成为可回退的真相)。"""
    vols = {}
    for fn in filenames:
        p = ROOT / "00_请先看这里" / fn
        if p.exists():
            b = p.read_bytes()
            vols[fn] = {"bytes": len(b), "sha256_16": _sha(b)}
    m = {"_说明": "五册实物指纹。开工脚本拿它比对G盘实物：对不上=G盘那份被旧版覆盖了(Drive回滚)，"
                  "别拿旧册当今天的产品交验收。",
         "data_date": date, "run_id": run_id, "produced_at_jst": scan_jst,
         "written_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
         "volumes": vols}
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return m


def check_manifest() -> tuple[int, list[str]]:
    """丙2 哨兵：比对 manifest 与 G盘实物。返回 (退出码, 报告行)。"""
    out = []
    if not MANIFEST.exists():
        return 0, ["[哨兵] 还没有 manifest（首次生产后才有）→ 跳过比对"]
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    bad = 0
    for fn, rec in (m.get("volumes") or {}).items():
        p = ROOT / "00_请先看这里" / fn
        if not p.exists():
            out.append(f"  ✗ 缺册：{fn}（manifest 里有登记、G盘上没有）")
            bad += 1
            continue
        b = p.read_bytes()
        if _sha(b) != rec.get("sha256_16"):
            out.append(f"  ✗ 疑似被旧版覆盖：{fn}\n"
                       f"      登记 {rec.get('sha256_16')} / {rec.get('bytes'):,} 字节\n"
                       f"      实物 {_sha(b)} / {len(b):,} 字节")
            bad += 1
    if bad:
        out.insert(0, f"[哨兵 报警] {bad} 册与登记指纹对不上（run_id={m.get('run_id')}·"
                      f"数据日={m.get('data_date')}）→ 疑似被旧版覆盖，别当今天的产品用；重跑生产。")
        return 6, out
    out.insert(0, f"[哨兵 OK] {len(m.get('volumes') or {})} 册指纹与登记一致"
                  f"（run_id={m.get('run_id')}·数据日={m.get('data_date')}·生产于{m.get('produced_at_jst')}）")
    return 0, out


def sync_master(date: str, run_id: str, scan_jst: str, filenames: list[str]) -> str:
    """丙3：把当前正式产品回写进主控文件的进度块(用锚点标记包住·可反复覆盖)。"""
    if not MASTER.exists():
        return "[回写] 主控文件不在 → 跳过"
    s = MASTER.read_text(encoding="utf-8")
    dd = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    lis = "".join(f'<li><a href="{fn}">{fn}</a></li>' for fn in filenames)
    block = (f'<!--PRODUCT_STATUS_START-->\n'
             f'<div style="background:#0f2e1c;border:3px solid #4fbf87;border-radius:10px;padding:12px 16px;margin:10px 0">'
             f'<div style="font-size:22px;font-weight:900;color:#1c6b45">当前正式产品 · 数据日 {dd}</div>'
             f'<div style="font-size:14px;margin-top:4px">生产于 <b>{scan_jst}</b>　｜　run_id <b>{run_id}</b>'
             f'　｜　本块由生产脚本每次自动回写（不是手填·不会过期）</div>'
             f'<ul style="font-size:13px;margin:6px 0 0 18px">{lis}</ul>'
             f'<div style="font-size:12px;color:#555;margin-top:4px">'
             f'五册的数据日/run_id 必须完全一致；不一致或找不到文件 → 跑 '
             f'<code>python scripts/product_manifest.py --check</code> 查是不是被旧版覆盖了。</div></div>\n'
             f'<!--PRODUCT_STATUS_END-->')
    if "<!--PRODUCT_STATUS_START-->" in s:
        s = re.sub(r"<!--PRODUCT_STATUS_START-->.*?<!--PRODUCT_STATUS_END-->", block, s, flags=re.S)
    else:
        s = re.sub(r"(<body[^>]*>)", r"\1\n" + block, s, count=1, flags=re.I)
        if "<!--PRODUCT_STATUS_START-->" not in s:
            s = block + s
    # 页头那句手填的"最后更新 2026-07-04"也是丙3要治的过期日→一并自动回写(它是页头第一眼看到的日期)
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
    s2, n = re.subn(r"最后更新\s*[\d]{4}-[\d]{2}-[\d]{2}(?:\s*[\d:]{4,8}(?:\s*JST)?)?",
                    f"最后更新 {now}", s)
    s = s2
    MASTER.write_text(s, encoding="utf-8")
    return (f"[回写] 主控进度块已更新 → 数据日{dd}·{len(filenames)}册·run_id {run_id}"
            + (f"；页头'最后更新'刷成 {now}（原为手填的过期日）" if n else ""))


def main() -> int:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="防回滚哨兵")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        rc, lines = check_manifest()
        for L in lines:
            print(L)
        return rc
    print("用 --check 跑哨兵比对")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
