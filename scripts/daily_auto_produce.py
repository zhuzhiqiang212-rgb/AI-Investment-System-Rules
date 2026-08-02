#!/usr/bin/env python3
"""每日自动生产（董事局工单2026-07-17·甲）· 只读不下单

董事长指出：不该靠他每天提醒才扫。本脚本由 Windows 任务计划每交易日定时自动跑完，
出当天五册（页头标"今天的"、run_id/data_date=当天），全程无需人点。

链路（缺一环即如实记、不拿旧版顶充）：
  ⓪ G盘可用性自检(写临时文件验可写·只读挂载也算不可用·不过则当天不生产)
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
_TRIGGER = "SCHEDULED"  # A3(36号):SCHEDULED(计划任务) / MANUAL(人工--trigger MANUAL)。台账区分·防人工补产混入自动全链
DEFAULT_TIME = "07:30"          # 每交易日 07:30 JST：日股开盘前、美股昨夜已收 → 董事长早上就能看到当天的

# (标签, 脚本, 是否关键环)  关键环失败=当天不出品(不许拿旧版顶充)
STEPS = [
    # ⓪ A1(36号):扫当日数据硬前置·critical。1当日20只价 2涨跌>5%榜 3当日新闻 4Drive新增(按修改时间)5USDJPY;任一缺→整轮停·不进渲染。
    ("⓪ 扫当日数据(硬前置·A1)", "daily_scan.py", True),
    # ★轮75 AN2:inbox外部资料扫描(此前流程完全没有这一步)——扫inbox+老雷+湖水源·出新增/断流·非关键(断流只告警)。
    ("①a inbox外部资料扫描(新增/断流)", "inbox_scan.py", False),
    ("① 富途实时持仓(OpenD)", "futu_positions_sync.py", True),
    ("② 持仓真表", "holdings_true_autobuild.py", True),
    # ★轮17 H4修+轮22 M1修:production④需【求证表+机会池链(双通道)】·且③审持仓也需【求证表】·原求证表在⑧才建(晚于④/③)→新日期必失败。
    #   依赖真序(clone测试查实):②持仓真表 → 求证表(evidence·不依赖③) → ③审持仓(依赖求证表+持仓真表) → 机会池链(dual依赖③holdings_review) → ④production。
    #   ★求证表必须在③【之前】(轮17误放③后·M1 clone测试暴露)。这几步critical:下游依赖它们。
    ("②a 当日新闻+证据链(求证表)", "evidence_autobuild.py", True, ["--with-macro-news"]),
    ("③ 审持仓+权威价", "holdings_review_against_chain.py", True),
    ("③b 机会池链·链驱动扫描", "opportunity_chain_driven.py", True),
    ("③c 机会池链·估值闸", "opportunity_valuation_gate.py", True),
    ("③d 机会池链·双通道现价", "opportunity_dual_channel.py", True),
    # ★轮66 AE2 数据层闸:扫描日期一致(文件名日期=内容时点·日股同日/美股允许前一日收盘滞后)。CRITICAL(AE2-1)。
    ("③z 扫描日期一致闸(文件名=内容时点)", "scan_date_consistency_gate.py", True, [], {}),
    ("④ production(当日实时价)", "production_pipeline.py", True),
    ("⑤ 均线(趋势参考)", "holdings_ma_levels.py", False),
    ("⑤b 20日价格序列(加仓闸后半条)", "prices_daily_build.py", False),  # W1(架构师裁定2026-07-25):嫁接回本地⑤b·产出『近20交易日不创新低』序列·治deep_render企稳判据【待接】/L44(轮17 H4:deep_render已接入·企稳可判)
    ("⑥ 估值分派", "valuation_dispatcher.py", False),
    ("⑥c 基准vintage过期告警闸", "vintage_gate.py", False),  # 轮13 D1(裁定2026-07-25):基准>90天未复核/vintage未记录/财报晚于复核→告警·补(A)类机制陈旧的根·非关键不阻断生产
    # 41号两把尺:尺A(利润指引≥15%变动重估·当日新闻/财报后自动检测重算)·尺B(控股型净资产·对normal_eps=null或双口径差>30%套用)·结果→data/valuation·供target_gap引用
    ("⑥d 尺A·利润指引大幅变动重估(41号)", "valuation_ruler_guidance_revision.py", False),
    ("⑥e 尺B·控股型净资产估值(41号)", "valuation_ruler_holdco.py", False),
    # 46号D2③候选池生产者(按当日激活板块逐格取龙头·上游未就绪据实报未产出)→ 43号C2机会发现·估值后渲染前·非关键(失败只告警不停链)
    ("⑥e1 估值重估触发巡检(49号E2·估值后·发现摆清单不改fair)", "valuation_review_trigger_gate.py", False),
    ("⑥e2 候选池生产者(激活板块·46号)", "candidate_pool_producer.py", False),
    ("⑥f 机会发现(从缺口出发·43号)", "opportunity_discovery.py", False),
    # ══ ★轮66 AE2 预测层 → 目标层 → 风险层(今天轮39~65 整改主干接入) ══
    #   预测层:forecast_gate 七闸(预测优先口径§七)+point_value 落区间(AB1-4)。CRITICAL(AE2-1)。
    #   ★日期:预测/风险层读 forecast_{YYYY-MM-DD}(横杠)·src=forecast(取最新 forecast 日·跨市场收盘日复用前一交易日)。
    ("⑥g forecast_gate(七闸+point落区间)", "forecast_gate.py", True, [], {"fmt": "hyphen", "src": "forecast"}),
    #   目标层:target_gap 缺口(生产日·读当日 scan/持仓/futu) + 两把闸(分母核平=CRITICAL·vintage同源=告警)。
    ("⑥h target_gap(缺口·目标层)", "target_gap.py", False, [], {}),
    ("⑥i gap分母核平闸(A vs 快照total≤0.5%)", "gap_denominator_gate.py", True, [], {}),
    ("⑥j gap vintage同源闸(>30天告警)", "gap_vintage_gate.py", False, [], {}),
    # ★轮67 AF1:Z4两段缺口(点值口径·已算清/未算清·四等级)→ 产 data/risk/z4_two_segment_{date}.json 供 render_3layer 第一屏。
    #   取价/市值/等级取自 target_gap_{date}(单一真相源)·forecast 日自动解析。非关键(渲染器缺它回落旧缺口块)。
    # ★轮72 AK4:改 CRITICAL——两段全0(数据没接上)即整轮停·不出空产品(六闸全PASS却产空产品的根因)。
    ("⑥k z4两段缺口(点值口径·供第一屏·全0则FAIL)", "z4_two_segment_build.py", True, [], {}),
    #   风险层:单一驱动暴露/跨账户合并暴露/减仓测算——★只给暴露事实·不给操作建议(读 forecast 日)。
    ("⑧a driver_exposure(单一驱动暴露·事实)", "driver_exposure.py", False, [], {"fmt": "hyphen", "src": "forecast"}),
    ("⑧b cross_account(跨账户合并暴露·事实)", "cross_account_exposure.py", False, [], {"fmt": "hyphen", "src": "forecast"}),
    ("⑧c reduction_calc(减仓测算·事实)", "exposure_reduction_calc.py", False, [], {"fmt": "hyphen", "src": "forecast"}),
    ("⑦ 当日涨跌", "day_change_scan.py", False),
    ("⑦b 数据异常检查关", "data_sanity_gate.py", False),
    ("⑦c 数据层文案禁夹带HTML闸", "data_html_leak_gate.py", False),  # 轮20 J4(裁定2026-07-27):数据层不带样式(强调用「」)·防先不翻类HTML漏进esc渲染·非关键只告警
    ("⑦d 激活清单作废告警闸", "regime_activation_gate.py", False),  # 轮23 N1④(裁定2026-07-27):最新sector_activation早于最近regime事件(FOMC)→告警清单可能作废尚未重出·把该不该重出从靠人记变机器提醒
    # ★轮73 AL2:宏观层数据源(SOXX/国债ETF/USDJPY真值·US10Y真收益率/FOMC/日银/日债如实标未接)+宏观完备性闸(不闭合→不宣激活·AL2-6)
    ("⑦e 宏观层快照(SOXX/国债/USDJPY·未接标未接)", "market_macro_snapshot.py", False),
    ("⑦f 宏观完备性闸(未闭合→不宣激活·AL2-6)", "macro_completeness_gate.py", False),
    # ★轮77 AQ:第③层资金流动(总闸)最小可用集(10Y/VIX/DXY/FOMC/CPI-PCE·FRED·取不到标未接)+完备性闸(≥2取不到→本层不成立·禁下游宣激活)
    ("⑦g 资金流层第③层(10Y/VIX/DXY/FOMC/CPI·未接标未接)", "macro_flow_layer.py", False),
    ("⑦h 资金流层完备性闸(≥2取不到→不成立·禁宣激活·AQ3-2)", "macro_flow_gate.py", False),

    ("⑨ 研报佐证(湖水资讯)", "research_corpus_ingest.py", False),
    ("⑨b 财报官方数(SEC EDGAR)", "edgar_financials.py", False),
    ("⑨c 机会池候选估值+研究", "candidate_valuation.py", False),
    ("⑩ 记分卡", "pdca_scorecard.py", False),
    ("⑪ 复盘", "pdca_review.py", False),
    # ★轮66 AE2 复盘层:到期预测记分(取当日收盘价结算·区间划错vs概率错分开)。用 --asof(横杠·forecast 日)。
    ("⑪a pdca_verdict(到期预测记分)", "pdca_verdict_run.py", False, [], {"fmt": "hyphen", "src": "forecast", "argname": "--asof"}),
    # ★轮79 AS:第⑦层复盘记分卡(系统的魂)——判断记分卡(累积)+确定性累积表(七层派生)+多尺度复盘+决策质量·产品能看出哪层最弱。
    ("⑪b 复盘记分卡层(第⑦层·四部件·最弱层)", "pdca_scorecard_layer.py", False),
    ("⑪c 判断记分卡闸(未命中缺错因/确定性手填/C级精确数→FAIL·AS1/AT2-1)", "judgment_scorecard_gate.py", False),
    ("⑪d 未读源码不得判机器行为闸(告警·拦Opus5·AT2-2)", "unread_source_gate.py", False),
    ("⑫ 三件魂", "systems_soul_build.py", False),
    ("⑫b 预测记分(下预测+结算到期)", "forecast_ledger.py", False),
    # ★轮75 AN1:七步流程固化——生成七步表(谁做/做没做/产出物)+第3步拦截(无当日Opus5正文→退出7→整轮停·不许上一日/模板顶替渲染)。CRITICAL。
    ("⑫c 七步流程核+第3步正文拦截(AN1)", "pipeline_7steps.py", True),
]

# ★轮66 AE2:今天(轮39~65整改)接入主干的模块集(用于 dry-run 对照表统计『被真正调用几个』)。
#   product_manifest --check 是渲染后的收尾闸(不在 STEPS 循环里·单列)。
NEW_WIRED_SCRIPTS = {
    "scan_date_consistency_gate.py",   # 数据层闸(CRITICAL)
    "forecast_gate.py",                # 预测层闸(CRITICAL·七闸+point落区间)
    "target_gap.py",                   # 目标层(缺口)
    "gap_denominator_gate.py",         # 目标层闸(CRITICAL·分母核平)
    "gap_vintage_gate.py",             # 目标层闸(告警·vintage同源)
    "driver_exposure.py",              # 风险层(单一驱动暴露)
    "cross_account_exposure.py",       # 风险层(跨账户合并暴露)
    "exposure_reduction_calc.py",      # 风险层(减仓测算)
    "pdca_verdict_run.py",             # 复盘层(到期预测记分)
    "z4_two_segment_build.py",         # ★轮67:目标层(Z4两段缺口·供 render_3layer 第一屏八项整改)
}

# 丙(GPT V6 裁定 2026-07-29·失败关闭硬闸)：关键步 rc==0 但【输出缺失/过小/JSON不可解析/必填字段不足】
#   同样判整轮 FAILED，防「后续渲染掩盖上游失败」。路径由 2026-07-29 真跑输出核实。
#   (脚本 → (相对路径模板{d}=YYYYMMDD, 最小字节, 必填JSON字段或None))
CRITICAL_OUTPUTS = {
    "futu_positions_sync.py":          ("data/accounts/futu_positions_{d}.json", 50, None),
    "holdings_true_autobuild.py":      ("data/accounts/holdings_true_{d}.json", 200, ["holdings"]),
    "evidence_autobuild.py":           ("data/evidence_chain/daily_{d}.json", 100, None),
    "holdings_review_against_chain.py": ("data/holdings/holdings_review_{d}.json", 50, None),
    "opportunity_chain_driven.py":     ("data/opportunities/chain_opportunities_{d}.json", 20, None),
    "opportunity_valuation_gate.py":   ("data/opportunities/opportunity_gated_{d}.json", 20, None),
    "opportunity_dual_channel.py":     ("data/opportunities/dual_channel_{d}.json", 20, None),
    "production_pipeline.py":          ("data/reports/production_{d}.json", 200, None),
}


def verify_output(date: str, script: str) -> tuple[bool, str]:
    """关键步产物校验：存在/大小/JSON可解析/必填字段。无登记输出的步→只靠 rc(返回 True)。"""
    spec = CRITICAL_OUTPUTS.get(script)
    if not spec:
        return True, ""
    rel, min_bytes, jf = spec
    p = ROOT / rel.format(d=date)
    if not p.exists():
        return False, f"输出文件缺失: {rel.format(d=date)}"
    sz = p.stat().st_size
    if sz < min_bytes:
        return False, f"输出文件过小({sz}<{min_bytes}B): {rel.format(d=date)}"
    if p.suffix == ".json":
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            return False, f"JSON不可解析: {rel.format(d=date)} · {type(e).__name__}: {e}"
        if jf:
            missing = [f for f in jf if not (isinstance(obj, dict) and obj.get(f))]
            if missing:
                return False, f"必填字段不足: {rel.format(d=date)} 缺 {missing}"
        # ★轮66 AE3:新闻硬闸(从 daily_scan ⓪ 挪到这·抓完后判)。evidence_autobuild 抓完宏观新闻后，
        #   evidence_chain 必须【真的有新闻】(macro_news 或 links 非空)；抓不到→整轮停·如实报「新闻源连不上·未生产」
        #   (AE3-2:闸未降级；AE3-3:抓不到就停不硬跑)。
        if script == "evidence_autobuild.py":
            n = _count_news(obj)
            if n <= 0:
                return False, ("新闻硬闸FAIL:evidence_chain 无任何新闻(macro_news/links 全空)"
                               "→ 新闻源连不上·当天未生产(不拿旧闻顶充·AE3)")
    return True, ""


def _count_news(obj: dict) -> int:
    """轮66 AE3:数 evidence_chain 里的新闻条数(macro_news + links)。与 daily_scan 的计数口径一致。"""
    n = 0
    try:
        mn = obj.get("rule_engine", {}).get("macro_news")
        if isinstance(mn, list):
            n += len(mn)
        elif isinstance(mn, dict):
            n += sum(len(v) if isinstance(v, (list, dict)) else 1 for v in mn.values())
        lk = obj.get("links")
        if isinstance(lk, list):
            n += len(lk)
    except Exception:
        pass
    return n


def critical_step_failed(date: str, script: str, critical: bool, rc: int) -> str | None:
    """整轮 FAILED 判定(GPT V6 §三)：关键步 超时/非零 或 输出校验未过 → 返回失败原因；否则 None。"""
    if not critical:
        return None
    if rc != 0:
        return f"rc={rc}(超时=124/非零)"
    ok, why = verify_output(date, script)
    return None if ok else why


def _now() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


# 本地兜底日志(在 C 盘·G盘挂了也写得进):留一条"当天G盘不可用·未生产"的痕迹。
_LOCAL_FALLBACK = Path.home() / ".ai_invest_gdrive_fail.log"


def _fallback_log(line: str) -> None:
    try:
        with _LOCAL_FALLBACK.open("a", encoding="utf-8") as f:
            f.write(line.rstrip() + "\n")
    except Exception:
        pass


def gdrive_check() -> tuple[bool, str]:
    """第0步·G盘可用性自检(董事长2026-07-19)：整套数据/产品都住 G 盘，
    Drive 没起来/只读挂载/半挂 → 当天生产会中途诡异失败(如7-19卡在③)。
    与其半路挂留半成品，不如开工第一步就明确报『G盘不可用』。
    检查：①目录在否 ②真能写(写临时文件→读回→删) —— 只读挂载也算不可用。"""
    import os
    if not ROOT.exists():
        return False, f"G盘目录不存在({ROOT}) —— Google Drive 未运行或未挂载"
    probe = ROOT / f"._gdrive_probe_{os.getpid()}.tmp"
    token = f"probe-{datetime.now(JST).strftime('%Y%m%d%H%M%S')}-{os.getpid()}"
    try:
        probe.write_text(token, encoding="utf-8")
        back = probe.read_text(encoding="utf-8")
        if back != token:
            return False, f"G盘写入校验不符(写={token[:20]}… 读={back[:20]}…) —— 挂载异常"
    except Exception as e:
        return False, f"G盘不可写({type(e).__name__}: {e}) —— 疑似只读挂载或 Drive 半挂"
    finally:
        try:
            if probe.exists():
                probe.unlink()
        except Exception:
            pass
    return True, "G盘可读写"


def _resolve_forecast_date(pipeline_date: str) -> str:
    """轮66:预测层/风险层脚本读 forecast_{YYYY-MM-DD}.json+target_gap_{YYYYMMDD}.json。
    正常日 forecast 与生产日同日；但跨市场收盘日(美股前一日收/日股当日收)Opus5 会复用前一交易日 forecast
    (如 07-31 生产复用 forecast_2026-07-30)。这里解析【最新一份 forecast_*.json 的日期】(紧凑 YYYYMMDD)供预测/风险层用。
    找不到→回落生产日。★这是 datesrc='forecast' 的取值来源；scan/目标层仍用生产日。"""
    import glob as _g, os as _os
    cands = _g.glob(str(ROOT / "data" / "forecast" / "forecast_*.json"))
    best = None
    for p in cands:
        stem = _os.path.basename(p)[len("forecast_"):-len(".json")]  # 2026-07-30
        dc = stem.replace("-", "")
        if len(dc) == 8 and dc.isdigit():
            if best is None or dc > best:
                best = dc
    return best or pipeline_date


def build_date_args(pipeline_date: str, forecast_date: str, opts: dict | None) -> list:
    """轮66:按 step 的 opts 造日期参数。opts 键:
       fmt   : 'compact'(默认·YYYYMMDD) | 'hyphen'(YYYY-MM-DD)
       argname: '--date'(默认) | '--asof' | None(无日期参数·如 --check)
       src   : 'pipeline'(默认·生产日) | 'forecast'(最新 forecast 日)
       fixed : 固定附加参数(如 ['--check'])——与 argname=None 搭配"""
    opts = opts or {}
    fixed = list(opts.get("fixed", []))
    argname = opts.get("argname", "--date")
    if argname is None:
        return fixed
    base = forecast_date if opts.get("src") == "forecast" else pipeline_date  # 均为紧凑 YYYYMMDD
    val = f"{base[:4]}-{base[4:6]}-{base[6:]}" if opts.get("fmt") == "hyphen" else base
    return [argname, val] + fixed


def run_step(label: str, script: str, date: str, extra: list | None = None, timeout: int = 900,
             date_args: list | None = None) -> tuple[int, str]:
    da = date_args if date_args is not None else ["--date", date]
    cmd = [sys.executable, str(ROOT / "scripts" / script)] + da + (extra or [])
    # 甲3：光在父进程 encoding="utf-8" 解不够——【子进程】默认按系统 GBK 编码写 stdout，
    #   于是中文进日志就成了乱码("持仓20项"→"�ֲ� 20 ��")。必须让子进程也用 UTF-8 输出。
    # 甲4（2026-07-29 修·三件魂步 72h 死挂根治）：不用 capture_output=True（管道）。
    #   若某步子进程卡在【不可中断 I/O】（如 G 盘 Google Drive 文件流停滞），PIPE 会让父进程
    #   在 communicate() 上永久阻塞，subprocess.run 的 timeout 也解不开（07-29 三件魂步实测卡到
    #   72h 任务超时才退、State 一直 Running 挡住次日触发）。改为：
    #   【输出重定向到文件 + Popen 显式 wait(timeout) + 超时杀进程树 + 10s 宽限即走 + stdin=DEVNULL】。
    #   任何一步的挂起最多 15 分钟即被放弃、整轮继续或干净收尾，不再静默死挂；不可中断的孤儿进程
    #   会残留（需重启清），但不再阻塞父进程与调度器。stdin=DEVNULL 防子/孙进程（如 claude）等 stdin。
    import os, tempfile
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    tmp = tempfile.NamedTemporaryFile("w+", suffix=".steplog", delete=False, encoding="utf-8")
    tmp.close()

    def _tail() -> str:
        try:
            lines = open(tmp.name, encoding="utf-8", errors="replace").read().strip().splitlines()
            return lines[-1][:200] if lines else ""
        except Exception:
            return ""

    _NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # Windows:子进程不弹控制台黑窗(GPT V6 2026-07-29)

    def _kill_tree(pid: int) -> None:
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           capture_output=True, timeout=30, creationflags=_NOWIN)
        except Exception:
            pass

    proc = None
    try:
        fh = open(tmp.name, "w", encoding="utf-8", errors="replace")
        proc = subprocess.Popen(cmd, cwd=str(ROOT), stdin=subprocess.DEVNULL,
                                stdout=fh, stderr=subprocess.STDOUT, env=env,
                                creationflags=_NOWIN)
        try:
            rc = proc.wait(timeout=timeout)
            fh.close()
            return rc, _tail()
        except subprocess.TimeoutExpired:
            fh.close()
            _kill_tree(proc.pid)
            try:
                proc.wait(timeout=10)   # 宽限；不可中断进程则放弃等待、整轮继续
            except subprocess.TimeoutExpired:
                pass
            return 124, f"超时(>{timeout}s·已杀进程树·不可中断则留孤儿·整轮继续)"
    except Exception as e:
        if proc is not None:
            _kill_tree(proc.pid)
        return 1, f"{type(e).__name__}: {e}"
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


def archive_old(date: str) -> list:
    """乙：生产成功后，把非当天的 ★每日产品_* 移进 _历史归档（移不是删·删要签字）。"""
    d = ROOT / "00_请先看这里"
    arc = d / "_历史归档" / "每日产品"
    arc.mkdir(parents=True, exist_ok=True)
    dd = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    keep = f"★每日产品_{dd}.html"        # 甲[A方案]：合并后每天只留【这一个】文件
    moved = []
    # 归档非当天的分册 + 【新1·董事长2026-07-19】旧渲染器的 legacy 完整产品_{date}.html(文件唯一性·每天只留一份正式版)
    globs = list(d.glob("★每日产品_*.html")) + list(d.glob(f"完整产品_{date}.html")) + list(d.glob(f"完整产品_{date}_v*.html"))
    for p in globs:
        if p.name == keep:
            continue                      # 旧的分册(★每日产品_日期_1_总览闭环.html 等)照样归档
        try:
            tgt = arc / (p.name if not p.name.startswith("完整产品") else p.stem + "_legacy归档.html")
            if tgt.exists():
                tgt.unlink()
            p.rename(tgt)
            moved.append(p.name)
        except Exception:
            pass
    return moved


def _moat_needs_rebuild(date: str) -> bool:
    """CODE-13修·护城河自动前置判据：当日 moat_analysis_{date}.json 不存在，或最新 moat 距当日 >16 天 → 需重评。
    render_3layer 出厂闸优先读 moat_analysis_{date}.json；产出当日重评文件即可使其通过(否则超期 FAIL 不出品)。"""
    import datetime as _dt, glob as _g, pathlib as _pl
    today = ROOT / "data" / "moat" / f"moat_analysis_{date}.json"
    if today.exists():
        return False
    cands = sorted(_g.glob(str(ROOT / "data" / "moat" / "moat_analysis_*.json")))
    if not cands:
        return True
    try:
        as_of = _pl.Path(cands[-1]).stem.split("_")[-1]
        ao = _dt.date(int(as_of[:4]), int(as_of[4:6]), int(as_of[6:8]))
        prod_d = _dt.date(int(date[:4]), int(date[4:6]), int(date[6:8]))
        return (prod_d - ao).days > 16
    except Exception:
        return True


def _finalize_render(rc2: int, prod_exists: bool) -> tuple:
    """CODE-13修·⑬b(三层产品=董事长唯一要看的册)后决策：返回 (status, archive_allowed, reason)。
    ★只有 ⑬b 成功(rc==0)且当天产品文件存在，才允许归档、才记 OK；否则 FAILED_NO_PRODUCT 且【不归档】。"""
    if rc2 != 0 or not prod_exists:
        reason = f"⑬b 三层产品(董事长唯一要看的册)未生成：rc={rc2}" + ("" if prod_exists else "·当天产品文件不存在")
        return "FAILED_NO_PRODUCT", False, reason
    return "OK", True, ""


def _log(rec: dict) -> None:
    """台账【追加】不覆盖(机器加固2026-07-18·4)：每次运行都新增一行、保留多日历史，
    这样才能证明"连续N个交易日准时/用当天数据/失败也留痕"。同日多次跑(失败后补跑)各留一行，
    不再按日 dedup 顶掉前一次。保留最近 400 行(约一年·含同日重试)。"""
    # A3(36号):每条记录都带 trigger(SCHEDULED/MANUAL) 与 pipeline(FULL=第0步到出品全跑通 / PARTIAL=中途或人工补产)
    rec.setdefault("trigger", _TRIGGER)
    rec.setdefault("pipeline", "FULL" if rec.get("status") == "OK" else "PARTIAL")
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
    # ⚠ re.sub 的替换串会解释 \A \1 等转义 → body 里若含 Windows 路径(如 \AI_Investment_System)会 bad escape 崩。
    #   用 lambda 返回 body(替换串不被转义解释)·修真bug。
    if "<!--AUTO_RUN_LOG_START-->" in s:
        s = re.sub(r"<!--AUTO_RUN_LOG_START-->.*?<!--AUTO_RUN_LOG_END-->", lambda _m: body, s, flags=re.S)
    else:
        s = re.sub(r"(<!--PRODUCT_STATUS_END-->)", lambda _m: _m.group(1) + "\n" + body, s, count=1)
    m.write_text(s, encoding="utf-8")


def install_task(time_str: str) -> int:
    """注册 Windows 任务计划：每天 time_str 跑一次(周末/假期市场没数→那天会如实记未生产)。"""
    cmd = ["schtasks", "/Create", "/TN", TASK_NAME, "/TR",
           f'"{sys.executable}" "{ROOT / "scripts" / "daily_auto_produce.py"}"',
           "/SC", "DAILY", "/ST", time_str, "/F"]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print((p.stdout or "") + (p.stderr or ""))
    return p.returncode


def _dry_run_report(date: str, fdate: str, started: str, done: list, failed: str | None) -> int:
    """★轮66 AE4-2:空跑对照表——每个管线步骤是否被调用到、rc、是否闸、闸角色。
    ★不出品(不渲染/不归档/不回写主控)·只落 data/logs/dry_run_{date}.json + 控制台打印。"""
    gates = [d for d in done if d.get("is_gate")]
    n_new = sum(1 for d in done if d["script"] in NEW_WIRED_SCRIPTS)
    rpt = {"_说明": "轮66 AE4 空跑验证·管线步骤×闸调用对照。★证明每个今天接入的模块都在管线里被真正调用。"
                    "本次不出品(不渲染/不归档/不回写主控)。",
           "date": date, "forecast_date": fdate, "started_at": started, "finished_at": _now(),
           "步骤总数": len(done), "闸调用数": len(gates),
           "今日接入模块被调用数": f"{n_new}/{len(NEW_WIRED_SCRIPTS)}",
           "中断于": failed, "步骤×闸": [
               {"步骤": d["step"], "脚本": d["script"], "rc": d["rc"], "critical": d["critical"],
                "是否闸": d.get("is_gate", False), "闸角色": d.get("gate_role"),
                "日期参数": d.get("date_args"), "今日接入": d["script"] in NEW_WIRED_SCRIPTS,
                "tail": d.get("tail", "")[:120]} for d in done]}
    p = LOG_DIR / f"dry_run_{date}.json"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rpt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\n════════ ★DRY-RUN 管线步骤 × 闸调用 对照表(AE4-2) ════════")
    print(" %-3s %-40s rc  %-4s %s" % ("#", "步骤", "闸?", "今日接入"))
    for i, d in enumerate(done, 1):
        g = "闸" if d.get("is_gate") else " "
        new = "★新接" if d["script"] in NEW_WIRED_SCRIPTS else ""
        print(" %-3d %-40s %-3s %-4s %s" % (i, d["step"][:40], d["rc"], g, new))
    print("  ——————")
    print(f"  步骤总数 {len(done)} · 闸调用 {len(gates)} · 今日接入模块被调用 {n_new}/{len(NEW_WIRED_SCRIPTS)}")
    if failed:
        print(f"  ⚠ 中断于关键闸: {failed[:120]}")
    print(f"  对照表已落 {p}")
    print("  ★DRY-RUN 结束:未渲染·未出品·未归档·未回写主控(AE4-3)。")
    return 0 if not failed else 3


def main() -> int:
    # 丁(GPT V6 2026-07-29·黑窗口根治)：计划任务改用 pythonw.exe 后台隐藏运行(不弹控制台黑窗)。
    #   pythonw 下 sys.stdout 可能为 None → 直接 print 会崩；统一把 stdout/stderr 重定向到日志文件
    #   (既隐藏窗口，又留生产日志作证据)。交互式(python.exe·有控制台)则保留控制台输出。
    if sys.stdout is None or sys.executable.lower().replace("\\", "/").endswith("pythonw.exe"):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        _stdout_log = open(LOG_DIR / f"daily_stdout_{datetime.now(JST).strftime('%Y%m%d')}.log", "a", encoding="utf-8")
        sys.stdout = _stdout_log
        sys.stderr = _stdout_log
    elif hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="每日自动生产(无需人点)")
    ap.add_argument("--date", default=None)
    ap.add_argument("--install", action="store_true", help="注册 Windows 任务计划")
    ap.add_argument("--time", default=DEFAULT_TIME, help=f"任务计划时间(默认 {DEFAULT_TIME} JST)")
    ap.add_argument("--trigger", default="SCHEDULED", choices=["SCHEDULED", "MANUAL"],
                    help="A3:计划任务拉起=SCHEDULED;人工跑=MANUAL(台账据此区分·防人工补产混入自动全链)")
    ap.add_argument("--simulate-gdrive-fail", action="store_true",
                    help="演练:强制G盘自检失败(证明能正确拦停并记台账)·不真跑生产")
    ap.add_argument("--dry-run", action="store_true",
                    help="★轮66 AE4:空跑验证——跑完整数据+闸链但【不渲染/不出品/不归档/不回写主控】，"
                         "末尾打印『管线步骤×闸调用』对照表，证明每个模块都被真正调用。")
    ap.add_argument("--forecast-date", default=None,
                    help="轮66:预测/风险层用的 forecast 日(紧凑 YYYYMMDD)。缺省=自动取最新一份 forecast_*.json。")
    a = ap.parse_args()
    globals()["_TRIGGER"] = a.trigger
    if a.install:
        return install_task(a.time)

    date = a.date or datetime.now(JST).strftime("%Y%m%d")
    fdate = a.forecast_date or _resolve_forecast_date(date)   # 紧凑 YYYYMMDD
    started = _now()
    _dry = a.dry_run
    print(f"═══ 每日自动生产 · {date} · 开始 {started}{' · ★DRY-RUN(空跑验证·不出品)' if _dry else ''} ═══")
    if _dry:
        print(f"  预测/风险层 forecast 日 = {fdate}（scan/目标层用生产日 {date}）")

    # ── 第0步·G盘可用性自检(缺它则前几轮那种"卡在半路"会留半成品) ──
    if a.simulate_gdrive_fail:
        g_ok, g_reason = False, "【演练】强制G盘不可用(--simulate-gdrive-fail)"
    else:
        g_ok, g_reason = gdrive_check()
    print(f"  {'✔' if g_ok else '✗'} ⓪ G盘可用性自检 — {g_reason}")
    if not g_ok:
        rec = {"date": date, "status": "FAIL", "started_at": started, "finished_at": _now(),
               "reason": f"G盘不可用(Drive未运行或未挂载)：{g_reason}", "steps": [],
               "note": "第0步G盘自检未过 → 当天未生产；未拿旧版顶充今天(实时铁律 §2.6)"}
        # 台账在G盘：G盘真挂了可能写不进 → 先本地兜底留痕，再尽力写G盘台账/主控
        _fallback_log(f"[{_now()}] 当天未生产·date={date}·原因={rec['reason']}")
        try:
            _log(rec)
            if not a.simulate_gdrive_fail:     # 演练不改董事长看的主控状态(避免把真产品状态刷成未生产)
                _sync_master_log(rec)
        except Exception as e:
            print(f"  （G盘台账/主控也写不进：{e}；已写本地兜底 {_LOCAL_FALLBACK}）")
        print(f"\n[当天未生产] {rec['reason']}")
        print(f"  → 已记本地兜底日志 {_LOCAL_FALLBACK}（G盘可用时并记入台账/主控）；产品目录未留旧版冒充今天。")
        return 3
    done, failed = [], None
    # 轮66:哪些脚本是"闸"(用于 AE4-2 步骤×闸调用对照)。名字含 gate 或功能=校验/记分。
    GATE_SCRIPTS = {"scan_date_consistency_gate.py": "扫描日期一致闸(CRITICAL)",
                    "forecast_gate.py": "预测七闸+point落区间(CRITICAL)",
                    "gap_denominator_gate.py": "缺口分母核平闸(CRITICAL)",
                    "gap_vintage_gate.py": "缺口vintage同源闸(告警)",
                    "valuation_review_trigger_gate.py": "估值重估触发巡检",
                    "vintage_gate.py": "基准vintage过期告警闸",
                    "data_sanity_gate.py": "数据异常检查闸",
                    "data_html_leak_gate.py": "数据层禁夹带HTML闸",
                    "regime_activation_gate.py": "激活清单作废告警闸",
                    "pdca_verdict_run.py": "到期预测记分(复盘闸)"}
    for st in STEPS:
        label, script, critical = st[0], st[1], st[2]
        extra = st[3] if len(st) > 3 else None
        opts = st[4] if len(st) > 4 else None
        date_args = build_date_args(date, fdate, opts)
        # ★AE4:空跑用快超时(90s)——只需证明每步被调用到;数据步若需 OpenD 而连不上,90s 足以快速记「调用·失败」再继续,
        #   不必在 900s 墙上干等(真实跑仍用 900s)。
        step_to = 90 if _dry else 900
        rc, tail = run_step(label, script, date, extra, timeout=step_to, date_args=date_args)
        mark = "✔" if rc == 0 else ("✗" if critical else "△")
        gate_tag = ("  ⟦闸:" + GATE_SCRIPTS[script] + "⟧") if script in GATE_SCRIPTS else ""
        print(f"  {mark} {label} rc={rc}{gate_tag} {tail[:80]}")
        done.append({"step": label, "rc": rc, "tail": tail[:200], "critical": critical,
                     "script": script, "date_args": date_args,
                     "is_gate": script in GATE_SCRIPTS, "gate_role": GATE_SCRIPTS.get(script)})
        fail_reason = critical_step_failed(date, script, critical, rc)
        if fail_reason:
            done[-1]["fail_reason"] = fail_reason
            if _dry:
                # ★AE4:空跑【不中断】——继续跑完全链，好让对照表证明每个模块都被调用到(真实跑仍会在下方 break)。
                if failed is None:
                    failed = f"{label} 关键步失败：{fail_reason}｜{tail[:100]}"
                continue
            failed = f"{label} 关键步失败：{fail_reason}｜{tail[:100]}"
            break
    # ── ★轮66 AE4/轮67 AF2:DRY-RUN——不出品/不归档/不回写主控。轮67 增:调用渲染器【dry-run】渲到临时路径+八项自查(证明渲染器已含八项·不写正式产品目录) ──
    if _dry:
        _tmp_render = LOG_DIR / f"dryrender_{date}.html"
        rcr, tailr = run_step("⑬d render_3layer(DRY·八项自查·不出品)", "render_3layer.py", date,
                              extra=["--dry-run", "--out", str(_tmp_render)], timeout=300)
        done.append({"step": "⑬d render_3layer(DRY·八项自查·不出品)", "rc": rcr, "critical": False,
                     "script": "render_3layer.py", "is_gate": False, "gate_role": None, "tail": tailr[:200]})
        print(f"  {'✔' if rcr == 0 else '△'} ⑬d render_3layer DRY rc={rcr} {tailr[:80]}")
        try:
            if _tmp_render.exists():
                _tmp_render.unlink()      # 清临时渲染物(不留)
        except Exception:
            pass
        return _dry_run_report(date, fdate, started, done, failed)
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
    dd = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    # 【CODE-13修·新增·护城河超期自动前置】render_3layer 出厂闸会因护城河超期(as_of>16天)FAIL 不出品。
    #   07-28 那次是手工绕过、没接进自动链，所以今天(07-30)复发。这里在 ⑬b 之前自动跑护城河重评，
    #   产出 moat_analysis_{date}.json 供出厂闸读取(moat_analysis.py=render_3layer 提示的"护城河重评脚本")。
    if _moat_needs_rebuild(date):
        rcm, tailm = run_step("⑬a 护城河自动重评(moat_analysis)", "moat_analysis.py", date)
        done.append({"step": "⑬a 护城河自动重评(moat_analysis)", "rc": rcm, "critical": True, "tail": tailm[:200]})
        print(f"  {'✔' if rcm == 0 else '✗'} ⑬a 护城河自动重评 rc={rcm} {tailm[:90]}")
    # ⑬b 三层产品(=董事长每天唯一要看的册)——【CODE-13修:改为【关键】】失败必须让总状态失败·不出品·不归档
    rc2, tail2 = run_step("⑬b 三层产品(骨架填数据)", "render_3layer.py", date)
    prod_file = ROOT / "00_请先看这里" / f"★每日产品_{dd}.html"
    prod_exists = prod_file.exists()
    done.append({"step": "⑬b 三层产品(骨架填数据)", "rc": rc2, "critical": True, "tail": tail2[:200]})
    status, archive_allowed, gate_reason = _finalize_render(rc2, prod_exists)
    if status != "OK":
        # 【CODE-13修·核心】⑬b 失败→当天无正式产品→【不归档】(旧产品原样留在目录·绝不清场冒充)
        done[-1]["fail_reason"] = gate_reason
        rec = {"date": date, "status": status, "started_at": started, "finished_at": _now(),
               "reason": gate_reason + f"｜{tail2[:120]}", "steps": done,
               "note": "⑬b(董事长唯一要看的册)失败→当天无正式产品→【未归档·昨天的产品原样保留】·不拿旧版冒充今天"}
        _log(rec)
        _sync_master_log(rec)
        print(f"\n[当天未出品·未归档] status={status}：{gate_reason}")
        print("  → 昨天的产品原样保留在 00_请先看这里/(未被清场)；台账/主控已记失败原因。")
        return 5
    print(f"  ✔ ⑬b 三层产品 rc=0 {tail2[:90]}")
    # ★轮66 AE2 出厂层收尾闸:product_manifest --check(防回滚哨兵·比对G盘实物指纹)。渲染器已登记指纹→此处复核。
    #   非关键(告警):对不上=疑似被旧版覆盖·记台账不阻断本次(本次刚渲的就是新的)。
    rcpm, tailpm = run_step("⑬c product_manifest --check(防回滚哨兵)", "product_manifest.py", date,
                            date_args=["--check"])
    done.append({"step": "⑬c product_manifest --check(防回滚哨兵)", "rc": rcpm, "critical": False,
                 "script": "product_manifest.py", "is_gate": True, "gate_role": "防回滚哨兵(出厂层)", "tail": tailpm[:200]})
    print(f"  {'✔' if rcpm == 0 else '△'} ⑬c product_manifest --check rc={rcpm} {tailpm[:80]}")
    run_id = ""
    try:
        run_id = json.loads((ROOT / "data" / "product_manifest.json").read_text(encoding="utf-8")).get("run_id", "")
    except Exception:
        pass
    # 【CODE-13修·归档前置条件】只有 ⑬b 成功且当天产品文件已生成(archive_allowed=True)才允许归档、清场
    moved = archive_old(date) if archive_allowed else []
    rec = {"date": date, "status": "OK", "started_at": started, "finished_at": _now(),
           "run_id": run_id, "steps": done, "archived": moved}
    _log(rec)
    _sync_master_log(rec)
    print(f"\n[当天已出品] run_id={run_id} · 归档 {len(moved)} 份旧册 → 00_请先看这里/_历史归档/每日产品/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
