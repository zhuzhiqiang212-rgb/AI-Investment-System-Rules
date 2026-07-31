#!/usr/bin/env python3
"""预测锁定机制·技术底座（派工单 P1-2·董事长2026-07-20 批准）· 只读不下单

要解决的问题：一条预测一旦下了，事后不能偷偷回改（改内容或改时间来"事后诸葛"）。
本模块提供防篡改的"锁"：把预测定格 → 算 SHA-256 指纹 → 盖【外部服务器时间】戳
→ 记进一份【只能追加、不能修改】的链式日志（另存一处做冗余）。任何回改都能被 verify 查出来。

四个硬要求（逐条对着建）：
  1) data/forecast/ 目录              —— 每条锁定单独存一份快照文件（写一次·不覆盖）
  2) SHA-256 指纹                     —— 快照内容的指纹，进日志；verify 时重算比对
  3) 外部服务器时间(不得用本机时间)   —— 本机时间可被改，不可信；取不到就【如实标"未时间认证"】，
                                         绝不拿本机时间冒充权威时间（铁律：取不到就报，不顶充）
  4) 只能追加不能修改的日志·另存一处  —— JSONL 哈希链(每行含上一行指纹)，改任一旧行都会断链；
                                         同一份链再冗余写到 data/logs/ 一份，互为佐证

外加：Google Drive 版本编号可行性验证（本盘是否 GDrive、能否回溯历史版本）。

用法：
  python scripts/forecast_lock.py --demo            # 自检：锁一条样例→verify过→篡改→verify断链
  python scripts/forecast_lock.py --verify          # 只核链
  python scripts/forecast_lock.py --gdrive          # 只验 GDrive 版本编号可行性
  python scripts/forecast_lock.py --lock-file X.json --date 20260720   # 锁定一个真预测文件
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
FORECAST_DIR = ROOT / "data" / "forecast"
LOG_PRIMARY = FORECAST_DIR / "_append_only_log.jsonl"          # 主：与快照同处
LOG_MIRROR = ROOT / "data" / "logs" / "forecast_lock_audit.jsonl"  # 另存一处：冗余佐证
GENESIS = "0" * 64                                             # 链头


# ── SHA-256 指纹 ──────────────────────────────────────────────
def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _canon(obj) -> bytes:
    """规范化 JSON 字节（排序键·固定分隔符）→ 同内容必得同指纹。"""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


# ── 外部服务器时间(不得用本机时间) ────────────────────────────
def external_time() -> dict:
    """取【外部】权威时间。成功→{ok:True, iso, source}；
    取不到→{ok:False, reason, local_ref}（local_ref 仅作参考·明确标注不可信·绝不当权威时间用）。"""
    import urllib.request

    # 多个外部源，任一成功即可（HTTP Date 头或时间 API）
    sources = [
        ("worldtimeapi", "http://worldtimeapi.org/api/timezone/Asia/Tokyo", "json_datetime"),
        ("google-header", "https://www.google.com/", "http_date_header"),
        ("cloudflare-header", "https://cloudflare.com/cdn-cgi/trace", "http_date_header"),
    ]
    errs = []
    for name, url, mode in sources:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "forecast-lock/1.0"})
            with urllib.request.urlopen(req, timeout=6) as r:
                if mode == "json_datetime":
                    j = json.loads(r.read().decode("utf-8"))
                    iso = j.get("datetime")
                    if iso:
                        return {"ok": True, "iso": iso, "source": f"{name}({url})"}
                # HTTP Date 头（服务器权威时间）
                dh = r.headers.get("Date")
                if dh:
                    dt = datetime.strptime(dh, "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
                    return {"ok": True, "iso": dt.astimezone(JST).isoformat(timespec="seconds"),
                            "source": f"{name}(HTTP Date 头@{url})"}
                errs.append(f"{name}:无Date头")
        except Exception as e:  # noqa: BLE001
            errs.append(f"{name}:{type(e).__name__}")
    # 全失败：如实报，本机时间只作参考、明确不可信
    return {"ok": False,
            "reason": "外部时间源全部连不上（本机离线/无网）：" + "; ".join(errs),
            "local_ref_untrusted": datetime.now(JST).isoformat(timespec="seconds")}


# ── 只能追加不能修改的日志（哈希链）────────────────────────────
def _last_chain_hash(log: Path) -> str:
    if not log.exists():
        return GENESIS
    last = GENESIS
    for line in log.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            last = json.loads(line)["chain_hash"]
        except Exception:
            pass
    return last


def _append(entry: dict) -> dict:
    """把 entry 追加进主日志＋镜像日志（各自独立算链）。返回带 chain_hash 的记录。"""
    LOG_PRIMARY.parent.mkdir(parents=True, exist_ok=True)
    LOG_MIRROR.parent.mkdir(parents=True, exist_ok=True)
    prev = _last_chain_hash(LOG_PRIMARY)
    rec = dict(entry)
    rec["prev_chain_hash"] = prev
    # 本行链指纹 = H(上一行链指纹 + 本行业务内容)；改任一旧行→其后所有链指纹全断
    rec["chain_hash"] = _sha256(prev.encode() + _canon({k: rec[k] for k in sorted(rec) if k != "chain_hash"}))
    line = json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n"
    with LOG_PRIMARY.open("a", encoding="utf-8") as f:
        f.write(line)
    with LOG_MIRROR.open("a", encoding="utf-8") as f:
        f.write(line)
    return rec


def verify_chain() -> dict:
    """核链：①主日志逐行重算 chain_hash 必须自洽（改任一旧行→断链）
    ②每条锁定引用的快照文件仍在、且 SHA-256 与登记值一致（改快照内容→指纹对不上）
    ③镜像日志与主日志逐行一致（有人只改了一份→对不上）。"""
    out = {"log_exists": LOG_PRIMARY.exists(), "entries": 0, "chain_ok": True,
           "snapshots_ok": True, "mirror_ok": True, "broken": []}
    if not LOG_PRIMARY.exists():
        out["note"] = "还没有任何锁定记录"
        return out
    prev = GENESIS
    lines = [l for l in LOG_PRIMARY.read_text(encoding="utf-8").splitlines() if l.strip()]
    out["entries"] = len(lines)
    for i, line in enumerate(lines):
        rec = json.loads(line)
        want = _sha256(prev.encode() + _canon({k: rec[k] for k in sorted(rec)
                                               if k not in ("chain_hash",)}))
        if rec.get("prev_chain_hash") != prev or rec.get("chain_hash") != want:
            out["chain_ok"] = False
            out["broken"].append(f"第{i + 1}行链指纹对不上（此行或之前被改过）")
            prev = rec.get("chain_hash", "")
            continue
        prev = rec["chain_hash"]
        # 校验快照文件指纹
        snap = rec.get("snapshot_file")
        if snap:
            sp = ROOT / snap
            if not sp.exists():
                out["snapshots_ok"] = False
                out["broken"].append(f"第{i + 1}行的快照文件丢失：{snap}")
            elif _sha256(sp.read_bytes()) != rec.get("sha256"):
                out["snapshots_ok"] = False
                out["broken"].append(f"第{i + 1}行快照被改：{snap} 现指纹≠登记指纹")
    # 镜像一致
    if LOG_MIRROR.exists():
        mlines = [l for l in LOG_MIRROR.read_text(encoding="utf-8").splitlines() if l.strip()]
        if mlines != lines:
            out["mirror_ok"] = False
            out["broken"].append("镜像日志与主日志不一致（可能只改了一份）")
    else:
        out["mirror_ok"] = False
        out["broken"].append("镜像日志缺失")
    out["all_ok"] = out["chain_ok"] and out["snapshots_ok"] and out["mirror_ok"]
    return out


# ── 锁定一条预测 ──────────────────────────────────────────────
def lock(forecast_obj: dict, date: str, label: str = "") -> dict:
    """把 forecast_obj 定格：写快照(不覆盖)→算指纹→盖外部时间戳→追加进链式日志。"""
    FORECAST_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"date": date, "label": label, "forecast": forecast_obj}
    body = _canon(payload)
    fp = _sha256(body)
    snap_name = f"forecast_{date}_{fp[:12]}.json"
    snap_path = FORECAST_DIR / snap_name
    # 写一次·不覆盖：若已存在同指纹→幂等；存在不同内容→拒绝（防偷改）
    if snap_path.exists():
        if _sha256(snap_path.read_bytes()) != fp:
            return {"ok": False, "error": f"同名快照已存在但指纹不同，拒绝覆盖：{snap_name}"}
    else:
        snap_path.write_bytes(body)

    et = external_time()
    time_block = ({"authoritative_time": et["iso"], "time_source": et["source"], "time_status": "已外部认证"}
                  if et["ok"] else
                  {"authoritative_time": None, "time_source": None,
                   "time_status": "未时间认证·外部时间取不到（本机时间不可信·不作数）",
                   "time_unavailable_reason": et["reason"],
                   "local_time_ref_untrusted": et["local_ref_untrusted"]})
    entry = {"kind": "forecast_lock", "date": date, "label": label,
             "snapshot_file": str(snap_path.relative_to(ROOT)).replace("\\", "/"),
             "sha256": fp, "logged_at_local_untrusted": datetime.now(JST).isoformat(timespec="seconds"),
             **time_block}
    rec = _append(entry)
    return {"ok": True, "sha256": fp, "snapshot": entry["snapshot_file"],
            "time_status": time_block["time_status"], "chain_hash": rec["chain_hash"]}


# ── Google Drive 版本编号可行性验证 ───────────────────────────
def gdrive_feasibility() -> dict:
    p = str(ROOT).replace("\\", "/")
    on_gdrive = ("我的云端硬盘" in p) or ("My Drive" in p) or ("Google Drive" in p)
    # 探测本机 Google Drive Desktop 挂载点
    mounts = []
    for d in "GHIJKLM":
        base = Path(f"{d}:/我的云端硬盘")
        if base.exists():
            mounts.append(str(base))
    return {
        "root": p,
        "on_google_drive": on_gdrive,
        "detected_mounts": mounts,
        "结论": ("可行——本盘在 Google Drive Desktop 的『我的云端硬盘』下，"
               "每次覆盖写文件，Google Drive 服务端会自动保留【历史版本】，可在 drive.google.com "
               "右键『版本管理/管理版本』按时间回溯，无需我们自己编版本号。"
               if on_gdrive else
               "本盘不在 Google Drive 路径下——若要版本编号需另接方案。"),
        "落地建议": ["锁定快照文件名内嵌 SHA-256 前12位＝内容版本号（本模块已做）",
                 "链式日志只追加，天然带序号(行号)＋链指纹＝防回改版本链",
                 "依赖 Google Drive 服务端版本历史做二次兜底（人工可在网页端回溯）"],
        "注意": "Google Drive 版本历史的保留期/份数由 Google 侧策略决定，不能当唯一防线；"
              "本模块的哈希链是不依赖 Google 的独立防篡改证据。",
    }


def _demo() -> int:
    # 自检隔离在沙盒目录，绝不污染正式 append-only 日志
    global FORECAST_DIR, LOG_PRIMARY, LOG_MIRROR
    FORECAST_DIR = ROOT / "data" / "forecast" / "_selftest"
    LOG_PRIMARY = FORECAST_DIR / "_append_only_log.jsonl"
    LOG_MIRROR = ROOT / "data" / "logs" / "forecast_lock_audit_selftest.jsonl"
    for p in (LOG_PRIMARY, LOG_MIRROR):
        if p.exists():
            p.unlink()
    for s in FORECAST_DIR.glob("forecast_*.json") if FORECAST_DIR.exists() else []:
        s.unlink()
    print("=== P1-2 预测锁定底座 · 自检（沙盒·不动正式日志）===")
    sample = {"claim": "样例：未来5交易日 SOXX 不累计跌破 -10%", "op": "gt", "target": -10.0, "code": "US.SOXX"}
    r = lock(sample, "20260720", label="demo-sample")
    print("① 锁定一条样例预测：", json.dumps(r, ensure_ascii=False))
    v1 = verify_chain()
    print("② 核链（应全过）：", "全过✔" if v1.get("all_ok") else f"有问题✗ {v1['broken']}")
    # 篡改演练：改快照内容 → 指纹对不上
    snaps = sorted(FORECAST_DIR.glob("forecast_20260720_*.json"))
    if snaps:
        victim = snaps[-1]
        orig = victim.read_bytes()
        victim.write_bytes(orig[:-1] + b" ")  # 改 1 字节
        v2 = verify_chain()
        print("③ 篡改快照1字节后核链（应报断链）：",
              "已抓✔ " + str(v2["broken"]) if not v2.get("all_ok") else "没抓到✗")
        victim.write_bytes(orig)  # 恢复
        v3 = verify_chain()
        print("④ 恢复后核链（应重新全过）：", "全过✔" if v3.get("all_ok") else f"仍异常✗ {v3['broken']}")
    print("⑤ 外部时间取用：",
          "已外部认证" if r["time_status"] == "已外部认证"
          else "未认证（离线·如实标注·未用本机时间冒充）—— 符合铁律")
    g = gdrive_feasibility()
    print("⑥ GDrive 版本编号可行性：", g["结论"][:60], "…")
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="预测锁定机制·技术底座")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--gdrive", action="store_true")
    ap.add_argument("--lock-file")
    ap.add_argument("--date")
    ap.add_argument("--label", default="")
    a = ap.parse_args()
    if a.demo:
        return _demo()
    if a.gdrive:
        print(json.dumps(gdrive_feasibility(), ensure_ascii=False, indent=2))
        return 0
    if a.verify:
        print(json.dumps(verify_chain(), ensure_ascii=False, indent=2))
        return 0
    if a.lock_file and a.date:
        obj = json.loads(Path(a.lock_file).read_text(encoding="utf-8"))
        print(json.dumps(lock(obj, a.date, a.label), ensure_ascii=False, indent=2))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
