#!/usr/bin/env python3
"""每日自动生产（董事局工单2026-07-17·甲）· 只读不下单

董事长指出：不该靠他每天提醒才扫。本脚本由 Windows 任务计划每交易日定时自动跑完，
出当天五册（页头标"今天的"、run_id/data_date=当天），全程无需人点。

链路（缺一环即如实记、不拿旧版顶充）：
  ① 富途实时持仓(OpenD)  ② 持仓真表  ③ 审持仓  ④ production(当日实时价)
  ⑤ 均线  ⑥ 估值  ⑦ 当日涨跌  ⑧ 当日新闻+证据链  ⑨ 研报佐证(湖水资讯)
  ⑩ 三件魂  ⑪ 渲五册(内含出厂lint硬闸·FAIL不覆盖旧版)  ⑫ 归档非当天的册

铁律（CLAUDE.md §2.6）：
  · OpenD 连不上 / 任一关键环失败 → 如实记「当天未生产·原因」到主控日志，**不留旧版冒充今天**。
  · 出厂 lint FAIL → 不覆盖旧册、记错因。

怎么改跑的时间：见 CLAUDE.md §7「每日自动生产」，或直接
  schtasks /Change /TN "AI投资系统_每日自动生产" /ST 07:30
用法：
  python scripts/daily_auto_produce.py                 # 自动用今天(JST)
  python scripts/daily_auto_produce.py --date 20260717
  python scripts/daily_auto_produce.py --install       # 注册 Windows 任务计划
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
LOG_DIR = ROOT / "data" / "logs"
RUNLOG = LOG_DIR / "auto_produce_runs.json"
TASK_NAME = "AI投资系统_每日自动生产"
DEFAULT_TIME = "07:30"          # 每交易日 07:30 JST：日股开盘前、美股昨夜已收 → 董事长早上就能看到当天的

# (标签, 脚本, 是否关键环)  关键环失败=当天不出品(不许拿旧版顶充)
STEPS = [
    ("① 富途实时持仓(OpenD)", "futu_positions_sync.py", True),
    ("② 持仓真表", "holdings_true_autobuild.py", True),
    ("③ 审持仓+权威价", "holdings_review_against_chain.py", True),
    ("④ production(当日实时价)", "production_pipeline.py", True),
    ("⑤ 均线(趋势参考)", "holdings_ma_levels.py", False),
    ("⑥ 估值分派", "valuation_dispatcher.py", False),
    ("⑦ 当日涨跌", "day_change_scan.py", False),
    ("⑦b 数据异常检查关", "data_sanity_gate.py", False),
    ("⑧ 当日新闻+证据链", "evidence_autobuild.py", True, ["--with-macro-news"]),
    ("⑨ 研报佐证(湖水资讯)", "research_corpus_ingest.py", False),
    ("⑨b 财报官方数(SEC EDGAR)", "edgar_financials.py", False),
    ("⑨c 机会池候选估值+研究", "candidate_valuation.py", False),
    ("⑩ 记分卡", "pdca_scorecard.py", False),
    ("⑪ 复盘", "pdca_review.py", False),
    ("⑫ 三件魂", "systems_soul_build.py", False),
    ("⑫b 预测记分(下预测+结算到期)", "forecast_ledger.py", False),
]


def _now() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def run_step(label: str, script: str, date: str, extra: list | None = None) -> tuple[int, str]:
    cmd = [sys.executable, str(ROOT / "scripts" / script), "--date", date] + (extra or [])
    # 甲3：光在父进程 encoding="utf-8" 解不够——【子进程】默认按系统 GBK 编码写 stdout，
    #   于是中文进日志就成了乱码("持仓20项"→"�ֲ� 20 ��")。必须让子进程也用 UTF-8 输出。
    import os
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    try:
        p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=900, env=env)
        tail = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()
        return p.returncode, (tail[-1][:200] if tail else "")
    except subprocess.TimeoutExpired:
        return 124, "超时(>15分钟)"
    except Exception as e:
        return 1, f"{type(e).__name__}: {e}"


def archive_old(date: str) -> list:
    """乙：生产成功后，把非当天的 ★每日产品_* 移进 _历史归档（移不是删·删要签字）。"""
    d = ROOT / "00_请先看这里"
    arc = d / "_历史归档" / "每日产品"
    arc.mkdir(parents=True, exist_ok=True)
    dd = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    keep = f"★每日产品_{dd}.html"        # 甲[A方案]：合并后每天只留【这一个】文件
    moved = []
    for p in d.glob("★每日产品_*.html"):
        if p.name == keep:
            continue                      # 旧的分册(★每日产品_日期_1_总览闭环.html 等)照样归档
        try:
            tgt = arc / p.name
            if tgt.exists():
                tgt.unlink()
            p.rename(tgt)
            moved.append(p.name)
        except Exception:
            pass
    return moved


def _log(rec: dict) -> None:
    """台账【追加】不覆盖(机器加固2026-07-18·4)：每次运行都新增一行、保留多日历史，
    这样才能证明"连续N个交易日准时/用当天数据/失败也留痕"。同日多次跑(失败后补跑)各留一行，
    不再按日 dedup 顶掉前一次。保留最近 400 行(约一年·含同日重试)。"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    hist = []
    if RUNLOG.exists():
        try:
            hist = json.loads(RUNLOG.read_text(encoding="utf-8")).get("runs", [])
        except Exception:
            hist = []
    # 幂等保护：同一次运行(同 date+同 finished_at)不重复追加；否则一律追加
    stamp = (rec.get("date"), rec.get("finished_at"))
    if not any((h.get("date"), h.get("finished_at")) == stamp for h in hist):
        hist.append(rec)
    hist.sort(key=lambda h: (str(h.get("date")), str(h.get("finished_at") or "")))
    # 每日一览：按日取该日最后一条的状态，方便"连续N交易日"核查
    by_day = {}
    for h in hist:
        by_day[str(h.get("date"))] = h.get("status")
    RUNLOG.write_text(json.dumps(
        {"_说明": "每日自动生产的运行台账·【追加不覆盖】。每次运行(含同日补跑)各留一行；"
                  "某天未生产→记「未生产+原因」，产品目录【不留】旧版冒充今天(实时铁律 CLAUDE.md §2.6)。",
         "task_name": TASK_NAME,
         "n_runs": len(hist), "n_days": len(by_day),
         "每日状态一览": dict(sorted(by_day.items())),
         "runs": hist[-400:]},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sync_master_log(rec: dict) -> None:
    """把「当天生产成功/未生产+原因」回写进主控，董事长一眼看到。"""
    m = ROOT / "00_请先看这里" / "★开工必读_主控文件.html"
    if not m.exists():
        return
    import re
    s = m.read_text(encoding="utf-8")
    ok = rec["status"] == "OK"
    bg, bd, col = ("#0f2e1c", "#4fbf87", "#1c6b45") if ok else ("#3a1414", "#d24b4b", "#a11")
    body = (f'<!--AUTO_RUN_LOG_START-->\n'
            f'<div style="background:{bg};border:2px solid {bd};border-radius:8px;padding:10px 14px;margin:8px 0">'
            f'<div style="font-size:16px;font-weight:800;color:{col}">'
            f'每日自动生产（{TASK_NAME}）：{rec["date"]} — {"✔ 已出当天五册" if ok else "✗ 当天未生产"}</div>'
            f'<div style="font-size:13px;margin-top:3px">跑于 {rec["finished_at"]}'
            + (f'　｜　run_id <b>{rec.get("run_id","")}</b>' if ok else f'　｜　<b>原因：{rec.get("reason","")}</b>')
            + '</div>'
            + (f'<div style="font-size:12px;color:#a11;margin-top:3px">'
               f'<b>产品目录里没有留旧版冒充今天</b>（实时铁律）。修好后重跑即可。</div>' if not ok else '')
            + f'<div style="font-size:11.5px;color:#666;margin-top:3px">'
              f'本块由 daily_auto_produce.py 每次自动回写。改跑的时间：'
              f'<code>schtasks /Change /TN "{TASK_NAME}" /ST 08:00</code></div></div>\n'
            f'<!--AUTO_RUN_LOG_END-->')
    if "<!--AUTO_RUN_LOG_START-->" in s:
        s = re.sub(r"<!--AUTO_RUN_LOG_START-->.*?<!--AUTO_RUN_LOG_END-->", body, s, flags=re.S)
    else:
        s = re.sub(r"(<!--PRODUCT_STATUS_END-->)", r"\1\n" + body, s, count=1)
    m.write_text(s, encoding="utf-8")


def install_task(time_str: str) -> int:
    """注册 Windows 任务计划：每天 time_str 跑一次(周末/假期市场没数→那天会如实记未生产)。"""
    cmd = ["schtasks", "/Create", "/TN", TASK_NAME, "/TR",
           f'"{sys.executable}" "{ROOT / "scripts" / "daily_auto_produce.py"}"',
           "/SC", "DAILY", "/ST", time_str, "/F"]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print((p.stdout or "") + (p.stderr or ""))
    return p.returncode


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="每日自动生产(无需人点)")
    ap.add_argument("--date", default=None)
    ap.add_argument("--install", action="store_true", help="注册 Windows 任务计划")
    ap.add_argument("--time", default=DEFAULT_TIME, help=f"任务计划时间(默认 {DEFAULT_TIME} JST)")
    a = ap.parse_args()
    if a.install:
        return install_task(a.time)

    date = a.date or datetime.now(JST).strftime("%Y%m%d")
    started = _now()
    print(f"═══ 每日自动生产 · {date} · 开始 {started} ═══")
    done, failed = [], None
    for st in STEPS:
        label, script, critical = st[0], st[1], st[2]
        extra = st[3] if len(st) > 3 else None
        rc, tail = run_step(label, script, date, extra)
        mark = "✔" if rc == 0 else ("✗" if critical else "△")
        print(f"  {mark} {label} rc={rc} {tail[:90]}")
        done.append({"step": label, "rc": rc, "tail": tail[:200], "critical": critical})
        if rc != 0 and critical:
            failed = f"{label} 失败(rc={rc})：{tail[:120]}"
            break
    if failed:
        rec = {"date": date, "status": "FAIL", "started_at": started, "finished_at": _now(),
               "reason": failed, "steps": done, "note": "关键环失败 → 当天未生产；未拿旧版顶充"}
        _log(rec)
        _sync_master_log(rec)
        print(f"\n[当天未生产] {failed}")
        print("  → 已记入 data/logs/auto_produce_runs.json 与主控；产品目录未留旧版冒充今天。")
        return 3
    # ⑬ 渲五册（出厂 lint 硬闸在渲染器内部：FAIL 即不落盘、不覆盖旧册）
    snap = ROOT / "data" / "evidence_chain" / "last_run_snapshot.json"
    if snap.exists():
        try:
            snap.unlink()
        except Exception:
            pass
    rc, tail = run_step("⑬ 渲五册(含出厂lint硬闸)", "deep_render.py", date)
    if rc != 0:
        rec = {"date": date, "status": "FAIL", "started_at": started, "finished_at": _now(),
               "reason": f"渲染/出厂lint 未通过(rc={rc})：{tail[:150]}", "steps": done,
               "note": "出厂lint FAIL → 旧册未被覆盖；错因见此"}
        _log(rec)
        _sync_master_log(rec)
        print(f"\n[当天未出品] 出厂lint/渲染未过：{tail[:150]}")
        return 5
    print(f"  ✔ ⑬ 渲五册 rc=0 {tail[:90]}")
    run_id = ""
    try:
        run_id = json.loads((ROOT / "data" / "product_manifest.json").read_text(encoding="utf-8")).get("run_id", "")
    except Exception:
        pass
    moved = archive_old(date)          # 乙：归档非当天的册
    rec = {"date": date, "status": "OK", "started_at": started, "finished_at": _now(),
           "run_id": run_id, "steps": done, "archived": moved}
    _log(rec)
    _sync_master_log(rec)
    print(f"\n[当天已出品] run_id={run_id} · 归档 {len(moved)} 份旧册 → 00_请先看这里/_历史归档/每日产品/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
