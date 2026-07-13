#!/usr/bin/env python3
"""第三块 · 全自动定时编排器（一条命令跑完当日全链出产品）

每天到点自动把当日全链跑完，出 00_请先看这里/完整产品_{当日}.html，无人值守。
缺一步即停·如实写日志 data/logs/auto_daily_{当日}.log·不伪造不硬推。

自检告警（治"悄无声息偷懒"）：
  - 一进 main 立刻写启动日志(时间戳)并即时落盘——跑了就有痕迹。
  - 跑完自检当日产品是否生成且 EF BF BD=0；没有→写显眼告警文件
    00_请先看这里/⚠自动运行告警_{date}.html（写清哪步失败/OpenD/退出码）。

链序：
  0 预检 OpenD（未开→如实报错停·A8今日价靠OpenD·不伪造）
  1 holdings_true（股数沿用最近confirmed + 今日OpenD价·A8；已存在则不覆盖）
  2 evidence_autobuild --with-macro-news（求证表：行情+宏观+新闻自评）
  3 opportunity_chain_driven → opportunity_valuation_gate（机会闸）
  4 opportunity_dual_channel（双通道·production 必需）
  5 holdings_review_against_chain（审持仓·OpenD刷价）
  6 pdca_scorecard → pdca_review（记分/复盘）
  7 production_pipeline（三关+护城河沿用+重评提示）
  8 full_product_render（出 完整产品_{当日}.html）

只读不下单。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
LOG_PATH: Path | None = None


def date_text(value: str | None) -> str:
    return value if value else datetime.now(JST).strftime("%Y%m%d")


def _init_log(date: str) -> None:
    """一进 main 就建日志、立刻落盘——保证跑了就有痕迹(即便随后崩)。"""
    global LOG_PATH
    LOG_PATH = ROOT / "data" / "logs" / f"auto_daily_{date}.log"
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("w", encoding="utf-8") as f:
        f.write(f"[START] auto_daily_run {date} @ {datetime.now(JST).isoformat()}\n"
                f"[ENV] cwd={os.getcwd()} python={sys.executable}\n"
                f"[ENV] ROOT={ROOT} exists={ROOT.exists()}\n")


def log(line: str) -> None:
    try:
        print(line)
    except UnicodeEncodeError:  # GBK 控制台(计划任务环境)遇⚠/中文不崩·如实落盘为准
        try:
            sys.stdout.buffer.write((line + "\n").encode("utf-8", "replace"))
        except Exception:
            pass
    if LOG_PATH is not None:
        with LOG_PATH.open("a", encoding="utf-8") as f:  # 每行即时落盘
            f.write(line + "\n")


def write_alarm(date: str, failed_step: str, code: int | None, opend_ok: bool | None, extra: str = "") -> Path:
    """写显眼告警 HTML：董事长一眼看到今天没出/为什么。UTF-8·自核乱码。"""
    ts = datetime.now(JST).isoformat()
    opend_txt = "未知" if opend_ok is None else ("已连接" if opend_ok else "未开/连不上")
    html = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>⚠ 自动运行告警 {date}</title>
<style>body{{margin:0;background:#2a1010;color:#ffe;font-family:"Microsoft YaHei",Arial,sans-serif;line-height:1.8;}}
.wrap{{max-width:820px;margin:0 auto;padding:26px 20px;}}
.box{{background:#3a1616;border:2px solid #b03a3a;border-radius:14px;padding:20px 22px;}}
h1{{color:#ff9a9a;font-size:22px;margin:0 0 10px;}} b{{color:#fff;}} code{{background:#1a0c0c;padding:1px 6px;border-radius:4px;color:#ffd0d0;}}
li{{margin:6px 0;}}</style></head><body><div class="wrap"><div class="box">
<h1>⚠ 今天({date})自动运行没出完整产品</h1>
<p><b>事实</b>：自动编排器跑了但没成功出当日产品，已在此如实告警（不悄无声息）。</p>
<ul>
<li><b>卡在哪步</b>：{failed_step}</li>
<li><b>退出码</b>：<code>{code}</code></li>
<li><b>OpenD 状态</b>：{opend_txt}</li>
<li><b>时间</b>：{ts}</li>
{f'<li><b>补充</b>：{extra}</li>' if extra else ''}
</ul>
<p><b>怎么办</b>：①确认 OpenD 已开、Google Drive(G:) 已挂载；②手动补跑 <code>python scripts\\auto_daily_run.py --date {date}</code>；③详情看日志 <code>data\\logs\\auto_daily_{date}.log</code>。</p>
<p style="color:#c99;font-size:12.5px;">本文件由 auto_daily_run.py 自检生成·只读不下单。</p>
</div></div></body></html>
"""
    path = ROOT / "00_请先看这里" / f"⚠自动运行告警_{date}.html"
    path.write_text(html, encoding="utf-8")
    if "�".encode("utf-8") in path.read_bytes():
        log(f"[WARN] 告警文件疑似乱码: {path}")
    log(f"[ALARM] 已写告警文件: {path}")
    return path


def run_step(label: str, script: str, date: str, extra: list[str] | None = None) -> int:
    cmd = [sys.executable, str(ROOT / "scripts" / script), "--date", date] + (extra or [])
    log(f"[RUN] {label}: {' '.join(cmd)}")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True,
                          encoding="utf-8", errors="replace", env=env)
    tail = "\n".join((proc.stdout or "").strip().splitlines()[-4:])
    if tail:
        log(tail)
    if proc.returncode != 0:
        err = "\n".join((proc.stderr or "").strip().splitlines()[-8:])
        if err:
            log("[STDERR] " + err)
    log(f"[RC] {label} = {proc.returncode}")
    return proc.returncode


def preflight_opend() -> bool:
    """A8：今日价靠 OpenD。未开→如实报错、不伪造价。"""
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from realtime_price import connect_quote_context
        ctx, attempts = connect_quote_context(max_retries=2, wait_seconds=2)
    except Exception as exc:  # futu 未装等
        log(f"[预检] OpenD 组件不可用：{exc}")
        return False
    if ctx is None:
        log("[预检] OpenD 未连接（网关未开/未登录）。按 A8：今日价靠 OpenD 刷新，"
            "拿不到真价则如实停、不伪造。请开 OpenD 后重跑。")
        return False
    try:
        ctx.close()
    except Exception:
        pass
    log("[预检] OpenD 已连接·可取今日实时价。")
    return True


def product_ok(date: str) -> tuple[bool, str]:
    """自检：当日产品存在且 EF BF BD=0。"""
    product = ROOT / "00_请先看这里" / f"完整产品_{date}.html"
    if not product.exists():
        return False, f"产品文件未生成: {product}"
    garble = product.read_bytes().count("�".encode("utf-8"))
    if garble > 0:
        return False, f"产品存在但有乱码 EF BF BD={garble}: {product}"
    return True, str(product)


def main() -> int:
    parser = argparse.ArgumentParser(description="第三块·全自动当日全链编排器")
    parser.add_argument("--date", default=None)
    parser.add_argument("--skip-opend-preflight", action="store_true",
                        help="跳过OpenD预检(仅测试用；正常勿加)")
    args = parser.parse_args()
    today = date_text(args.date)

    for stream in (sys.stdout, sys.stderr):  # 计划任务/GBK 控制台下也用 UTF-8·不因编码崩
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    _init_log(today)  # 先落盘启动痕迹
    log(f"===== auto_daily_run {today} @ {datetime.now(JST).isoformat()} =====")

    opend_ok: bool | None = None
    # 0 预检 OpenD（未开→如实停+告警）
    if not args.skip_opend_preflight:
        opend_ok = preflight_opend()
        if not opend_ok:
            log("[STOP] 第0步 OpenD 预检未过 → 停、不伪造。")
            write_alarm(today, "第0步 OpenD 预检（今日价靠OpenD）", 3, opend_ok,
                        "OpenD 未开或连不上，按A8不伪造价格。开OpenD后重跑。")
            return 3

    # 1 holdings_true（已存在则不覆盖·护董事长手工更正的交易日真表）
    holdings_true = ROOT / "data" / "accounts" / f"holdings_true_{today}.json"
    if holdings_true.exists():
        log(f"[SKIP] 1 持仓真表已存在(不覆盖): {holdings_true.name}")
    else:
        if run_step("1 持仓真表(A8·股数沿用+今日OpenD价)", "holdings_true_autobuild.py", today) != 0:
            return _stop(today, "1 持仓真表", opend_ok)

    # 2..8 顺序链；每步 RC≠0 即停+告警
    chain = [
        ("2 求证表(行情+宏观+新闻)", "evidence_autobuild.py", ["--with-macro-news"]),
        ("3a 机会发现", "opportunity_chain_driven.py", None),
        ("3b 机会估值闸", "opportunity_valuation_gate.py", None),
        ("4 双通道", "opportunity_dual_channel.py", None),
        ("5 审持仓(OpenD刷价)", "holdings_review_against_chain.py", None),
        ("6a 记分卡", "pdca_scorecard.py", None),
        ("6b 复盘", "pdca_review.py", None),
        ("7 生产线(三关+护城河沿用)", "production_pipeline.py", None),
        ("7b DCF精算(覆盖能算的成长股·可信度A)", "dcf_valuation.py", None),
        ("7c 机会层候选行情(Yahoo·只读)", "candidate_price_fetch.py", None),
        ("8 出完整产品", "full_product_render.py", None),
    ]
    for label, script, extra in chain:
        if run_step(label, script, today, extra) != 0:
            return _stop(today, label, opend_ok)

    # 自检
    ok, detail = product_ok(today)
    if not ok:
        log(f"[STOP] 自检未过：{detail}")
        write_alarm(today, "8 出完整产品(自检)", 2, opend_ok, detail)
        return 2

    log(f"[OK] 当日完整产品(自检通过·乱码0): {detail}")
    log("[DONE] auto_daily_run 成功。")
    return 0


def _stop(date: str, label: str, opend_ok: bool | None) -> int:
    log(f"[STOP] {label} 失败(RC≠0) → 停、不硬推不伪造。")
    write_alarm(date, label, 1, opend_ok, "某步脚本返回非0，链已停。看日志定位。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
