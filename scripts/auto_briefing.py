#!/usr/bin/env python3
"""
auto_briefing.py
自动决策简报 V1
TASK-2026-06-11-003 REV-A

功能：
  1. 调用 daily_data_fetch 获取数据
  2. 自动六步查表
  3. 输出第0/1/2层结论 + NEXT_OWNER/ACTION/THREAD
  4. 用户 Y 确认后写入 daily_briefing_template_v1.md
  5. 生成 briefing 记录（TASK_ID + 生成时间 + 数据时间）

禁止：
  自动下单 / 自动生成交易指令 /
  修改账户文件 / 写入执行卡

运行命令：
  python scripts/auto_briefing.py
  python scripts/auto_briefing.py --dry-run
"""

import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"G:\我的云端硬盘\AI_Investment_System")
JST  = timezone(timedelta(hours=9))
BRIEFING_LOG_PATH = ROOT / "data" / "auto_briefing_log.json"
TEMPLATE_PATH     = ROOT / "docs" / "daily_briefing_template_v1.md"
DAILY_REPORT_PATH   = ROOT / "reports" / "daily" / "latest_daily_report.md"
DIRECTION_CARD_PATH = ROOT / "reports" / "daily" / "latest_direction_card.md"
RISK_CARD_PATH      = ROOT / "reports" / "daily" / "latest_risk_card.md"
EXECUTION_CARD_PATH = ROOT / "reports" / "daily" / "latest_execution_card.md"
START_HERE_PATH     = ROOT / "START_HERE.html"


POSITION_SNAPSHOT_PATH = ROOT / "data" / "position_snapshot.json"


def load_position_snapshot() -> dict:
    """读取 Futu OpenD 只读持仓快照；不存在时返回空结构。"""
    if not POSITION_SNAPSHOT_PATH.exists():
        return {
            "mode": "READ_ONLY",
            "summary": {"position_count": 0, "has_real_position_data": False},
            "markets": [],
            "missing": True,
        }
    try:
        return json.loads(POSITION_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "mode": "READ_ONLY",
            "summary": {"position_count": 0, "has_real_position_data": False},
            "markets": [],
            "error": str(exc),
        }


def format_position_snapshot(snapshot: dict) -> str:
    """将只读持仓快照格式化到执行卡。"""
    generated_at = snapshot.get("generated_at", "未生成")
    summary = snapshot.get("summary", {})
    count = summary.get("position_count", 0)
    lines = [
        f"快照时间：{generated_at}",
        f"模式：{snapshot.get('mode', 'READ_ONLY')}（账户数据仅供结构参考，禁止直接下单）",
        f"持仓记录数：{count}",
    ]
    if snapshot.get("missing"):
        lines.append("状态：未找到 data/position_snapshot.json，请先运行 scripts/futu_position_fetch.py")
        return "\n".join(lines)
    if snapshot.get("error"):
        lines.append(f"读取错误：{snapshot['error']}")
        return "\n".join(lines)

    rows = []
    for market in snapshot.get("markets", []):
        market_name = market.get("market", "UNKNOWN")
        pos_query = market.get("position_query", {})
        records = pos_query.get("records", [])
        if not records:
            err = pos_query.get("error", "")
            rows.append(f"- {market_name}: 无持仓记录" + (f"（{err}）" if err else ""))
            continue
        rows.append(f"- {market_name}: {len(records)} 条")
        for rec in records[:20]:
            code = rec.get("code") or rec.get("stock_code") or rec.get("证券代码") or "UNKNOWN"
            name = rec.get("stock_name") or rec.get("name") or rec.get("证券名称") or ""
            qty = rec.get("qty") or rec.get("can_sell_qty") or rec.get("quantity") or rec.get("持仓数量") or "?"
            cost = rec.get("cost_price") or rec.get("average_cost") or rec.get("成本价") or "?"
            mv = rec.get("market_val") or rec.get("market_value") or rec.get("市值") or "?"
            rows.append(f"  - {code} {name} | 数量:{qty} | 成本:{cost} | 市值:{mv}")
        if len(records) > 20:
            rows.append(f"  - ... 其余 {len(records) - 20} 条见 data/position_snapshot.json")
    lines.extend(rows)
    return "\n".join(lines)

# 复用 daily_data_fetch 的 fetch 函数
sys.path.insert(0, str(Path(__file__).parent))
from daily_data_fetch import (
    fetch_vix, fetch_tnx, fetch_spx_change,
    fetch_btc_change, fetch_user_config,
    display_data_status,
)

# ─────────────────────────────────────────────
# 六步自动查表
# ─────────────────────────────────────────────

def step1_cycle(vix, tnx, spx=None, btc=None) -> tuple[str, str]:
    """
    步骤1：周期定位 → (周期标签, 置信度)
    4维判断：VIX / 美债 / SPX / BTC
    """
    # 维度不足时降级
    available = sum([
        vix is not None,
        tnx is not None,
        spx is not None,
        btc is not None,
    ])
    if available < 2:
        return "UNKNOWN", "C"

    signals = []

    # 维度1：VIX
    if vix is not None:
        if vix < 18:
            signals.append("BULL")
        elif vix < 23:
            signals.append("TRANSITION")
        else:
            signals.append("BEAR")

    # 维度2：10Y美债
    if tnx is not None:
        if tnx < 4.0:
            signals.append("BULL")
        elif tnx < 4.7:
            signals.append("TRANSITION")
        else:
            signals.append("BEAR")

    # 维度3：SPX日涨跌
    if spx is not None:
        if spx > 0.5:
            signals.append("BULL")
        elif spx < -1.0:
            signals.append("BEAR")
        else:
            signals.append("TRANSITION")

    # 维度4：BTC日涨跌（风险偏好辅助）
    if btc is not None:
        if btc > 1.0:
            signals.append("BULL")
        elif btc < -2.0:
            signals.append("BEAR")
        else:
            signals.append("TRANSITION")

    bull_count  = signals.count("BULL")
    bear_count  = signals.count("BEAR")
    trans_count = signals.count("TRANSITION")
    total       = len(signals)

    # 周期判断
    if bull_count >= total * 0.75:
        cycle = "BULL_MID"
    elif bear_count >= total * 0.75:
        cycle = "BEAR"
    elif bull_count > bear_count and bull_count >= total * 0.5:
        cycle = "BULL_MID"
    elif bear_count > bull_count and bear_count >= total * 0.5:
        cycle = "BEAR"
    else:
        cycle = "TRANSITION"

    # 置信度（基于一致性）
    max_count = max(bull_count, bear_count, trans_count)
    if max_count == total:
        confidence = "A"       # 全部一致
    elif max_count >= total * 0.75:
        confidence = "A"       # 75%以上一致
    elif max_count >= total * 0.5:
        confidence = "B"       # 50%以上一致
    else:
        confidence = "C"       # 严重分歧

    # 数据不足时置信度降级
    if available < 3:
        if confidence == "A":
            confidence = "B"
        elif confidence == "B":
            confidence = "C"

    return cycle, confidence


def step2_allocation(crypto_pct) -> str:
    """步骤2：配置偏离检查"""
    if crypto_pct is None:
        return "DATA_GAP"
    return "YES（需再平衡）" if crypto_pct > 10 else "NO"


def step3_signal(spx, btc) -> dict:
    """步骤3：信号等级"""
    signals = {}
    if spx is None:
        signals["美股"] = "C（数据缺失）"
    elif spx > 0.5:
        signals["美股"] = "B"
    elif spx < -1.0:
        signals["美股"] = "无（防守）"
    else:
        signals["美股"] = "C"

    if btc is None:
        signals["加密"] = "C（DATA_GAP）"
    elif btc > 1.0:
        signals["加密"] = "B"
    else:
        signals["加密"] = "C"

    signals["日股"] = "观察"
    signals["A股"]  = "观察"
    return signals



def generate_conclusions(cycle: str, confidence: str,
                          signals: dict, crypto_pct) -> dict:
    """生成第0/1/2层结论；P1恢复后 layer1 按账户输出。"""
    conclusion_map = {
        ("BULL_MID", "A"): "允许分批布局AI核心，流动性支撑充足",
        ("BULL_MID", "B"): "谨慎布局，控制仓位，等待更强确认信号",
        ("TRANSITION", "B"): "今天进入观察期，数据冲突，暂缓新仓",
        ("BEAR",       "B"): "进入防守模式，持有现金，禁止新增高Beta",
        ("UNKNOWN",    "C"): "证据不足，仅观察，不执行任何操作",
    }
    layer0 = conclusion_map.get((cycle, confidence), f"当前周期 {cycle}，置信度 {confidence}，请手动判断")

    if cycle in ("TRANSITION", "UNKNOWN", "BEAR") or confidence == "C":
        layer1 = {
            "富途": f"持有，不加仓（{cycle}期间）",
            "SBI":  f"持有，不加仓（{cycle}期间）",
            "IBKR": "持有，不加仓",
            "BF":   "持有，观察BTC走势",
        }
    elif confidence == "A" and cycle in ("BULL_MID", "BULL_EARLY"):
        layer1 = {
            "富途": "持有核心AI，事件落地后再评估加仓",
            "SBI":  "持有，等待BOJ结果后判断",
            "IBKR": "持有，若需操作先人工核对账户",
            "BF":   "持有，观察BTC是否确认突破",
        }
    else:
        layer1 = {
            "富途": "持有，等待置信度升A级后再评估核心AI加仓",
            "SBI":  "持有，等待BOJ结果后判断",
            "IBKR": "持有",
            "BF":   "持有，不加仓（B级）",
        }

    forbidden = []
    if cycle in ("TRANSITION", "BEAR", "UNKNOWN"):
        forbidden.append("禁止加杠杆")
    if signals.get("美股", "").startswith("无"):
        forbidden.append("禁止抄底")
    if crypto_pct is not None and crypto_pct > 8:
        forbidden.append("禁止加仓加密（接近上限）")
    if not forbidden:
        forbidden.append("禁止追高")

    crypto_text = "DATA_GAP" if crypto_pct is None else f"{crypto_pct:.2f}%"
    today_data_line = (
        "当日数据："
        f"周期={cycle}；置信度={confidence}；"
        f"美股信号={signals.get('美股', 'DATA_GAP')}；"
        f"加密信号={signals.get('加密', 'DATA_GAP')}；"
        f"加密占比={crypto_text}"
    )
    if len(forbidden) == 1:
        forbidden.append(today_data_line)
    else:
        forbidden.insert(1, today_data_line)

    return {"layer0": layer0, "layer1": layer1, "layer2": forbidden, "cycle": cycle, "confidence": confidence}

def get_yesterday_validation(today_results: dict) -> str:
    """
    读取 auto_briefing_log.json 中前一日结论，
    对比今日实际数据，返回验证结论字符串。
    """
    if not BRIEFING_LOG_PATH.exists():
        return "昨日验证：无前日记录，跳过"

    try:
        logs = json.loads(BRIEFING_LOG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return "昨日验证：日志读取失败，跳过"

    if len(logs) < 1:
        return "昨日验证：无前日记录，跳过"

    # 取最新一条（今日运行前的最后记录）
    yesterday_log = logs[-1]
    y_cycle  = yesterday_log.get("cycle", "UNKNOWN")
    y_conf   = yesterday_log.get("confidence", "?")
    y_layer0 = yesterday_log.get("layer0", "")
    y_date   = yesterday_log.get("data_date", "?")

    # 今日实际数据
    spx = today_results["spx"]["value"]
    vix = today_results["vix"]["value"]

    spx_str = f"SPX {spx:+.2f}%" if spx is not None else "SPX DATA_GAP"
    vix_str = f"VIX {vix:.2f}" if vix is not None else "VIX DATA_GAP"

    # 简单验证逻辑
    verdict = _validate(y_cycle, spx)

    return (
        f"昨日判断（{y_date}）：{y_cycle} {y_conf}级 — {y_layer0}\n"
        f"今日实际：{spx_str} / {vix_str}\n"
        f"验证结论：{verdict}"
    )


def _validate(cycle: str, spx) -> str:
    """简单验证：周期判断与市场方向是否一致"""
    if spx is None:
        return "SPX数据缺失，无法验证"
    if cycle in ("BEAR", "TRANSITION", "UNKNOWN"):
        if spx < 0:
            return "防守方向成立（市场下跌，判断有效）"
        elif spx > 1.0:
            return "防守判断偏保守（市场上涨，可复盘）"
        else:
            return "市场震荡，判断中性"
    elif cycle in ("BULL_MID", "BULL_EARLY"):
        if spx > 0:
            return "进攻方向成立（市场上涨，判断有效）"
        elif spx < -1.0:
            return "进攻判断偏激进（市场下跌，需复盘）"
        else:
            return "市场震荡，判断中性"
    elif cycle == "BULL_LATE":
        return f"BULL_LATE期间，SPX {spx:+.2f}%，建议人工复盘"
    return "无法自动验证，建议人工复盘"


# ─────────────────────────────────────────────
# NEXT_OWNER / NEXT_ACTION / NEXT_THREAD（变更项1）
# ─────────────────────────────────────────────

def generate_next_steps(confidence: str, layer1: str) -> dict:
    """根据置信度和唯一动作输出 NEXT 三元组"""
    if confidence == "C":
        return {
            "NEXT_OWNER":  "用户",
            "NEXT_ACTION": "每天运行 auto_briefing.py，\n              月末填写 monthly_return_tracking_v1.md，\n              积累数据后 Claude 自动触发 G-10",
            "NEXT_THREAD": "AI投研总控台 + 正式日报生产",
        }
    if "分批建仓" in layer1:
        return {
            "NEXT_OWNER":  "用户",
            "NEXT_ACTION": "每天运行 auto_briefing.py，\n              月末填写 monthly_return_tracking_v1.md，\n              积累数据后 Claude 自动触发 G-10",
            "NEXT_THREAD": "AI投研总控台 + 正式日报生产",
        }
    return {
        "NEXT_OWNER":  "用户",
        "NEXT_ACTION": "每天运行 auto_briefing.py，\n              月末填写 monthly_return_tracking_v1.md，\n              积累数据后 Claude 自动触发 G-10",
        "NEXT_THREAD": "AI投研总控台 + 正式日报生产",
    }


# ─────────────────────────────────────────────
# Briefing 记录（变更项2）
# ─────────────────────────────────────────────

def write_briefing_log(conclusions: dict, data_results: dict,
                        today_str: str, yesterday_validation: str) -> None:
    """记录 TASK_ID / 生成时间 / 数据时间"""
    BRIEFING_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if BRIEFING_LOG_PATH.exists():
        try:
            existing = json.loads(
                BRIEFING_LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            existing = []

    entry = {
        "task_id":       "TASK-2026-06-11-003-REV-A",
        "generated_at":  datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "data_date":     today_str,
        "data_times": {
            "vix": data_results["vix"].get("updated_at", "—"),
            "tnx": data_results["tnx"].get("updated_at", "—"),
            "spx": data_results["spx"].get("updated_at", "—"),
            "btc": data_results["btc"].get("updated_at", "—"),
        },
        "layer0":     conclusions["layer0"],
        "layer1":     conclusions["layer1"],
        "layer2":     conclusions["layer2"],
        "cycle":      conclusions["cycle"],
        "confidence": conclusions["confidence"],
        "yesterday_validation": yesterday_validation,
    }
    existing.append(entry)
    BRIEFING_LOG_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"[BRIEFING_LOG] 记录已写入：{BRIEFING_LOG_PATH}")



def write_latest_cards(conclusions: dict, results: dict,
                        today_str: str, next_steps: dict,
                        yesterday_validation: str = "") -> None:
    """写入四份差异化 latest_*.md 文件，各自只回答一个核心问题"""

    vix = results["vix"]["value"]
    tnx = results["tnx"]["value"]
    spx = results["spx"]["value"]
    btc = results["btc"]["value"]
    cycle  = conclusions["cycle"]
    conf   = conclusions["confidence"]
    layer0 = conclusions["layer0"]
    layer1 = conclusions["layer1"]
    layer2 = " / ".join(conclusions["layer2"])

    vix_str = f"{vix}" if vix is not None else "DATA_GAP"
    tnx_str = f"{tnx}%" if tnx is not None else "DATA_GAP"
    spx_str = f"{spx:+.2f}%" if spx is not None else "DATA_GAP"
    btc_str = f"{btc:+.2f}%" if btc is not None else "DATA_GAP"

    # 失效条件（基于周期）
    invalidation_map = {
        "BULL_MID":    "VIX突破25 / SPX单日跌幅超3% / ETF Flow连续转负",
        "TRANSITION":  "VIX突破30 / 关键支撑位跌破 / 数据冲突持续3日以上",
        "BEAR":        "VIX回落至20以下且SPX连续3日上涨",
        "BULL_EARLY":  "VIX重新上穿22 / 资金流转负",
        "BULL_LATE":   "拥挤度缓解 / 高Beta开始分化",
        "UNKNOWN":     "关键数据补齐后重新判断",
    }
    invalidation = invalidation_map.get(cycle, "请人工判断失效条件")
    position_snapshot_text = format_position_snapshot(load_position_snapshot())

    # ── 文件1：日报 ── 回答"今天发生了什么"
    DAILY_REPORT_PATH.write_text(f"""# 今日日报 — {today_str}
生成时间：{today_str} JST　　来源：auto_briefing.py

{yesterday_validation}

## 今日市场变量
VIX：{vix_str}　10Y美债：{tnx_str}　SPX：{spx_str}　BTC：{btc_str}

## 今日结论
{layer0}
周期：{cycle}　置信度：{conf}

⚠️ 禁止自动下单。执行前人工确认。
""", encoding="utf-8")

    # ── 文件2：方向卡 ── 回答"主线方向是否变化"
    DIRECTION_CARD_PATH.write_text(f"""# 方向卡 — {today_str}
生成时间：{today_str} JST

## 当前方向
周期：{cycle}　置信度：{conf}
方向：{layer0}

## 失效条件
{invalidation}

## 方向小结
置信度{conf}级——{"方向明确，可按此执行" if conf in ("A","B") else "证据不足，仅观察，不执行"}

⚠️ 禁止自动下单。
""", encoding="utf-8")

    # ── 文件3：风险卡 ── 回答"最大风险是什么"
    RISK_CARD_PATH.write_text(f"""# 风险卡 — {today_str}
生成时间：{today_str} JST

## 最大风险
{layer2}

## 风险触发阈值
VIX当前：{vix_str}（警戒：>25）
SPX当前：{spx_str}（警戒：单日<-2%）
BTC当前：{btc_str}

## 数据源状态
VIX：{results['vix']['status']}　10Y：{results['tnx']['status']}
SPX：{results['spx']['status']}　BTC：{results['btc']['status']}

⚠️ 禁止自动下单。
""", encoding="utf-8")

    # ── 文件4：执行卡 ── 回答"今天该做什么"
    EXECUTION_CARD_PATH.write_text(f"""# 执行卡 — {today_str}
生成时间：{today_str} JST

## 唯一动作
{layer1}

## 富途真实持仓快照（OpenD只读）
{position_snapshot_text}

## 四账户边界
富途：使用 data/position_snapshot.json 只读快照辅助判断；禁止直接下单
IBKR：{layer1}
SBI ：{layer1}
BF  ：{layer1}{"（BTC DATA_GAP，不操作）" if btc is None else ""}

## 执行前必须确认
□ 券商实时行情
□ 当前持仓和成本
□ 可用现金
□ 未成交挂单

NEXT_OWNER  : {next_steps['NEXT_OWNER']}
NEXT_ACTION : {next_steps['NEXT_ACTION']}

⚠️ 禁止自动下单。禁止修改账户文件。
""", encoding="utf-8")

    # TASK-2026-06-15-003: 同步今日四报到 Drive 桌面文件夹；同名文件直接覆盖，避免重复副本。
    import os
    desktop_folder_id = "15M4GeV5vkNjTJtqGs4VVY-Gj5fhRwH9S"
    desktop_override = os.environ.get("AUTO_BRIEFING_DESKTOP_SYNC_DIR")
    desktop_candidates = []
    if desktop_override:
        desktop_candidates.append(Path(desktop_override))
    desktop_candidates.extend([
        Path(r"C:\Users\zhu20\Desktop\股票分析与研究"),
        Path(r"C:\Users\zhu20\OneDrive\桌面\股票分析与研究"),
    ])
    desktop_folder = next((p for p in desktop_candidates if p.exists()), None)
    if desktop_folder is None:
        print(f"⚠ 桌面同步跳过：未找到 Drive 桌面文件夹 ID {desktop_folder_id} 的本地同步路径")
    else:
        desktop_payloads = [
            (f"{today_str}_daily_report.md", DAILY_REPORT_PATH.read_text(encoding="utf-8")),
            (f"{today_str}_direction_card.md", DIRECTION_CARD_PATH.read_text(encoding="utf-8")),
            (f"{today_str}_risk_card.md", RISK_CARD_PATH.read_text(encoding="utf-8")),
            (f"{today_str}_execution_card.md", EXECUTION_CARD_PATH.read_text(encoding="utf-8")),
        ]
        for desktop_name, desktop_content in desktop_payloads:
            desktop_path = desktop_folder / desktop_name
            desktop_existed = desktop_path.exists()
            desktop_path.write_text(desktop_content, encoding="utf-8")
            desktop_action = "覆盖" if desktop_existed else "新建"
            print(f"✓ 桌面同步{desktop_action}: {desktop_path}")
    print(f"✓ 四份差异化 latest_*.md 已写入 [{today_str}]")







def _safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.replace('%', '').replace(',', '').strip()
            if value in ('', 'N/A', 'nan', 'None'):
                return default
        return float(value)
    except Exception:
        return default


def _position_code(position):
    return str(position.get('code') or position.get('ticker') or position.get('symbol') or position.get('stock_code') or '').upper()


def _position_name(position):
    return str(position.get('stock_name') or position.get('name') or _position_code(position) or '未知标的')


def _position_qty(position):
    return _safe_float(position.get('qty', position.get('quantity', position.get('position_qty', 0))))


def _position_pnl_pct(position):
    return _safe_float(
        position.get('pl_ratio',
        position.get('pnl_pct',
        position.get('profit_pct',
        position.get('pl_ratio_avg_cost', 0))))
    )


def _position_price(position):
    return _safe_float(position.get('nominal_price', position.get('price', position.get('last_price', position.get('market_price', 0)))))


def _position_cost(position):
    return _safe_float(position.get('average_cost', position.get('cost_price', position.get('avg_cost', 0))))


def _position_market_value(position):
    return _safe_float(position.get('market_val', position.get('market_value', position.get('marketValue', 0))))


def _manual_confirm_text():
    return '执行前人工确认：账户/持仓/成本/现金/挂单'


def _is_high_beta(code):
    code = (code or '').upper()
    return any(token in code for token in ('MSTR', 'COIN', 'IREN', 'BTC', 'ETH'))


def _is_jp_code(code):
    code = (code or '').upper()
    return code.startswith('JP.') or code.startswith('HK.') or any(token in code for token in ('9984', '7974', '8766', '4568', '7832', '8035', '6857', '4063', '8750'))


def _is_ai_core(code):
    code = (code or '').upper()
    return any(token in code for token in ('NVDA', 'MSFT', 'META', 'GOOGL', 'AVGO', 'TSM'))


def _is_defensive(code):
    code = (code or '').upper()
    return any(token in code for token in ('8766', '8750', '4568'))


def _format_pct(value):
    return f'{_safe_float(value):+.2f}%'


def _clean_layer1_text(layer1):
    if isinstance(layer1, dict):
        parts = []
        for account, action in layer1.items():
            if isinstance(action, dict):
                text = action.get('动作边界') or action.get('今日关注') or str(action)
            else:
                text = str(action)
            parts.append(f'{account}: {text}')
        text = '；'.join(parts)
    else:
        text = str(layer1)
    for token in ('账户待确认', '标的待确认'):
        text = text.replace(token, '人工确认后执行')
    return text


def _load_positions_unique():
    snapshot = load_position_snapshot()
    positions = []
    for market in snapshot.get('markets', []) or []:
        account_hint = market.get('market') or market.get('account_hint') or ''
        records = (market.get('position_query') or {}).get('records', []) or []
        for row in records:
            if not isinstance(row, dict):
                continue
            item = dict(row)
            item.setdefault('account_bucket', account_hint)
            positions.append(item)
    unique = {}
    for pos in positions:
        code = _position_code(pos)
        if not code:
            continue
        current = unique.get(code)
        if current is None or _position_market_value(pos) > _position_market_value(current):
            unique[code] = pos
    return list(unique.values())


def generate_60s_summary(conclusions, positions):
    layer1 = _clean_layer1_text(conclusions.get('layer1', '持有观察'))
    layer2 = conclusions.get('layer2') or ['禁止追高，原因：当前事件窗口内波动可能放大']
    layer2_first = str(layer2[0]) if layer2 else '禁止追高，原因：风险收益比不够清晰'
    events = get_3day_events(datetime.now(JST).strftime('%Y-%m-%d'))
    event = events[0] if events else {'name': '无重大事件', 'date': '未知'}
    if positions:
        best = max(positions, key=_position_pnl_pct)
        high_beta = [p for p in positions if _is_high_beta(_position_code(p))]
        worst = min(high_beta or positions, key=_position_pnl_pct)
        best_line = f'{_position_code(best)} {_format_pct(_position_pnl_pct(best))} → 强势仓位，先持有观察'
        worst_line = f'{_position_code(worst)} {_format_pct(_position_pnl_pct(worst))} → 波动风险最高，优先看止损警戒'
    else:
        best_line = '无持仓数据 → 仅做市场判断'
        worst_line = '无持仓数据 → 不做账户执行判断'
    return [
        f'今天做什么：{layer1}',
        f'今天不能做什么：{layer2_first}',
        f'最大机会：{best_line}',
        f'最大风险：{worst_line}',
        f'今天关注：{event.get("name", "无重大事件")}（{event.get("date", "未知")}）',
    ]


def get_position_risk_level(pnl_pct, code):
    code = (code or '').upper()
    pnl_pct = _safe_float(pnl_pct)
    if pnl_pct >= 0:
        return '🟢', '持有'
    if pnl_pct >= -15:
        return '🟡', '观察止损'
    text = '高危/止损警戒'
    if _is_high_beta(code):
        text = '高Beta+止损警戒'
    return '🔴', text


def get_position_advice(position, cycle='BULL_MID', confidence='B'):
    code = _position_code(position)
    name = _position_name(position)
    pnl = _position_pnl_pct(position)
    manual = _manual_confirm_text()
    if _is_high_beta(code) and pnl < -30:
        if 'MSTR' in code:
            trigger = '若跌破用户历史关键位 MSTR $110'
        else:
            trigger = '若继续下跌并且风险卡仍显示高Beta过热'
        return (f'{code} {name} {pnl:+.2f}% 🔴 高Beta高危\n'
                f'若[BTC无法确认新高且高Beta继续走弱] → 降低波动暴露，{manual}\n'
                f'{trigger} → 执行止损复核，{manual}\n'
                f'若[BTC重新走强且风险降温] → 仅持有观察，不追高')
    if pnl >= 50 and not _is_high_beta(code):
        return (f'{code} {name} {pnl:+.2f}% 🟢 强势仓位\n'
                f'若[周期升级为BULL A级] → 可评估加仓，{manual}\n'
                f'若[周期维持BULL B级] → 持有，等待更强确认，不追高')
    if pnl >= 0:
        return (f'{code} {name} {pnl:+.2f}% 🟢 盈利仓位\n'
                f'若[周期不变] → 持有\n'
                f'若[周期降级] → 注意保护利润，触发条件待专题研报确认')
    if pnl >= -15:
        return (f'{code} {name} {pnl:+.2f}% 🟡 小幅亏损\n'
                f'若[继续下跌超过规则库单笔最大亏损3%] → 执行止损复核，{manual}\n'
                f'若[反弹回正] → 持有观察')
    return (f'{code} {name} {pnl:+.2f}% 🔴 高危/止损警戒\n'
            f'若[亏损继续扩大且基本面无改善] → 降低风险，{manual}\n'
            f'若[事件落地后反弹] → 先观察，不追高')


def get_3day_events(today_str):
    try:
        today = datetime.strptime(today_str, '%Y-%m-%d').date()
    except Exception:
        today = datetime.now(JST).date()
    manual = _manual_confirm_text()
    calendar = [
        {'date': '2026-06-16', 'name': 'BOJ议息', 'impact': 4, 'targets': ['9984软银', '7974任天堂', '日元走势'],
         'scenarios': [
             f'若[USD/JPY走强且日股AI链继续高开] → 已有仓持有，新仓不追，{manual}',
             f'若[日元快速升值压制日股] → 软银/日股AI链降波动复核，{manual}',
         ]},
        {'date': '2026-06-17', 'name': 'FOMC会议', 'impact': 5, 'targets': ['NVDA', 'MSFT', 'SPX'],
         'scenarios': [
             f'若[偏鸽且AI主线确认] → 只评估核心AI，不追高Beta，{manual}',
             f'若[偏鹰且美债上行] → 高Beta优先降波动，{manual}',
         ]},
        {'date': '2026-06-20', 'name': '三巫日（季度期权到期）', 'impact': 3, 'targets': ['MSTR', 'COIN', '高Beta标的'],
         'scenarios': [
             f'若[高Beta冲高但波动放大] → 不追高，必要时降波动，{manual}',
             f'若[波动回落且趋势不破] → 持有观察，等待下一次确认',
         ]},
        {'date': '2026-06-25', 'name': 'PCE数据', 'impact': 3, 'targets': ['降息预期', '美债'],
         'scenarios': [
             f'若[通胀降温] → 观察核心AI是否获资金回流，{manual}',
             f'若[通胀反弹] → 不新增高Beta，保留现金',
         ]},
    ]
    picked = []
    for event in calendar:
        d = datetime.strptime(event['date'], '%Y-%m-%d').date()
        if d >= today:
            event = dict(event)
            weekday = '一二三四五六日'[d.weekday()]
            event['display'] = f"{event['date']}（周{weekday}）{event['name']} {'★' * int(event['impact'])}"
            picked.append(event)
    return picked[:3]


def get_monthly_progress():
    config_path = ROOT / 'data' / 'user_config.json'
    try:
        data = json.loads(config_path.read_text(encoding='utf-8')) if config_path.exists() else {}
        value = _safe_float(data.get('monthly_return_pct', 0.0))
    except Exception:
        value = 0.0
    if value == 0.0:
        return '本月进度待更新（月末填写monthly_return_tracking_v1.md）'
    diff = value - 3.33
    status = '超额' if diff >= 0 else '落后'
    return f'本月目标3.33% / 当前{value:.2f}% / {status}{abs(diff):.2f}%'


def get_research_trigger(positions, events):
    triggers = []
    for event in events:
        if int(event.get('impact', 0)) >= 4:
            triggers.append((3, f"{event.get('name', '事件')}专题"))
    for pos in positions:
        code = _position_code(pos)
        pnl = _position_pnl_pct(pos)
        if pnl < -30:
            triggers.append((2, f'{code}止损复盘'))
        elif pnl > 50:
            triggers.append((1, f'{code}止盈时机研究'))
    if triggers:
        _, topic = sorted(triggers, key=lambda x: x[0], reverse=True)[0]
        return f'研报触发提醒：今日是否需要生成专题研报：是；建议主题：{topic}'
    return '研报触发提醒：今日是否需要生成专题研报：否；建议主题：无'


def get_sub_cycle(positions, results, events):
    spx = _safe_float((results.get('spx') or {}).get('value'), None)
    btc = _safe_float((results.get('btc') or {}).get('value'), None)
    vix = _safe_float((results.get('vix') or {}).get('value'), None)
    ai_positions = [p for p in positions if _is_ai_core(_position_code(p))]
    ai_avg = sum(_position_pnl_pct(p) for p in ai_positions) / len(ai_positions) if ai_positions else 0
    ai = 'BULL_MID' if spx is not None and spx > 0.5 and ai_avg > 30 else 'TRANSITION'
    crypto = 'BEAR' if btc is not None and btc < -3 else 'BULL_MID' if btc is not None and btc > 3 else 'TRANSITION'
    has_boj = any('BOJ' in e.get('name', '') for e in events)
    jp = 'TRANSITION' if has_boj else 'BULL_MID'
    vix_state = '风险低' if vix is not None and vix < 18 else '风险抬升' if vix is not None and vix < 25 else '风险高'
    allocation = '现金保留，核心持有' if crypto == 'TRANSITION' or jp == 'TRANSITION' else '核心资产可观察加仓'
    display = {
        'AI核心子周期': f'{ai}｜NVDA/TSM/MSFT 等核心AI仍是主线，但按事件窗口确认',
        '加密/高Beta子周期': f'{crypto}｜BTC/MSTR/COIN/IREN 不追脉冲',
        '日本/日股子周期': f'{jp}｜BOJ前后看USDJPY和日股AI链波动',
        'A股子周期': 'DATA_GAP｜当前无A股/北向资金数据，不进入执行判断',
        '_raw': {'ai': ai, 'crypto': crypto, 'jp': jp, 'risk': vix_state},
    }
    return display


def get_position_tier(positions, sub_cycles):
    tiers = {'核心仓': [], '高Beta仓': [], '防守仓': [], '观察仓': [], '问题仓': []}
    for pos in positions:
        code = _position_code(pos)
        pnl = _position_pnl_pct(pos)
        label = f'{code} {_format_pct(pnl)}'
        if pnl < -30 or (_is_high_beta(code) and pnl < -15):
            tiers['问题仓'].append(label)
        elif _is_high_beta(code):
            tiers['高Beta仓'].append(label)
        elif _is_defensive(code):
            tiers['防守仓'].append(label)
        elif _is_ai_core(code) or any(token in code for token in ('9984', '8035', '6857', '4063')):
            tiers['核心仓'].append(label)
        else:
            tiers['观察仓'].append(label)
    for key in tiers:
        if not tiers[key]:
            tiers[key].append('暂无')
    return tiers


def get_account_actions(positions, conclusions, events, sub_cycles):
    manual = _manual_confirm_text()
    us = [p for p in positions if not _is_jp_code(_position_code(p))]
    jp = [p for p in positions if _is_jp_code(_position_code(p))]
    def worst(items):
        return min(items, key=_position_pnl_pct) if items else None
    has_fomc = any('FOMC' in e.get('name', '') for e in events)
    has_boj = any('BOJ' in e.get('name', '') for e in events)
    w_us = worst(us)
    w_jp = worst(jp)
    w_us_text = f'{_position_code(w_us)} {_format_pct(_position_pnl_pct(w_us))}' if w_us else '暂无'
    w_jp_text = f'{_position_code(w_jp)} {_format_pct(_position_pnl_pct(w_jp))}' if w_jp else '暂无'
    high_beta_deep = [p for p in us if _is_high_beta(_position_code(p)) and _position_pnl_pct(p) < -30]
    crypto_cycle = sub_cycles.get('_raw', {}).get('crypto', 'TRANSITION') if isinstance(sub_cycles, dict) else 'TRANSITION'
    return {
        '富途': {'今日关注': f'{w_us_text} + {"FOMC会议" if has_fomc else "美股风险"}', '动作边界': '高Beta止损警戒，核心AI持有观察' if high_beta_deep else '核心AI持有观察，高Beta不追', '禁止': 'FOMC前禁止加仓高Beta' if has_fomc else '禁止追高', '执行前人工确认': manual},
        'SBI': {'今日关注': f'{w_jp_text} + {"BOJ/日元" if has_boj else "日股走势"}', '动作边界': 'BOJ结果出来前不新建日股AI仓位' if has_boj else '日股核心持有观察', '禁止': 'BOJ前不新增日股AI链' if has_boj else '禁止追高', '执行前人工确认': manual},
        'IBKR': {'今日关注': '当前持仓与保证金状态', '动作边界': '仅参考，不做执行；若要操作先核对保证金/现金/挂单', '禁止': '未核对保证金前不操作', '执行前人工确认': manual},
        'BF': {'今日关注': f'BTC走势 + 加密子周期{crypto_cycle}', '动作边界': '观察，不加仓' if crypto_cycle == 'TRANSITION' else '按BTC趋势观察', '禁止': 'BTC脉冲上涨时不追', '执行前人工确认': manual},
    }


def get_rotation_signal(results, positions, events, sub_cycles):
    raw = sub_cycles.get('_raw', {}) if isinstance(sub_cycles, dict) else {}
    nvda = next((p for p in positions if 'NVDA' in _position_code(p)), None)
    ai_main = raw.get('ai') == 'BULL_MID' and nvda is not None and _position_pnl_pct(nvda) > 50
    has_boj = any('BOJ' in e.get('name', '') for e in events)
    has_fomc = any('FOMC' in e.get('name', '') for e in events)
    worst = min(positions, key=_position_pnl_pct) if positions else None
    rotation_out = f'{_position_code(worst)}相关高Beta风险' if worst and raw.get('crypto') in ('TRANSITION', 'BEAR') and _is_high_beta(_position_code(worst)) else '暂无明确退潮'
    cash = '维持现金，不追高' if has_boj or has_fomc else '可小幅降低现金观察核心AI'
    return [
        f'当前主线: {"AI硬件/核心AI" if ai_main else "AI核心观察"}',
        f'备选主线: {"日本金融与日股事件窗口" if has_boj else "美股科技" if has_fomc else "暂无"}',
        '观察中: 日本科技 / SaaS观察池 / 高Beta加密',
        f'退潮板块: {rotation_out}',
        f'现金状态: {cash}',
    ]


def quality_check(content_flags):
    checks = [
        ('持仓无重复（每个code唯一）', content_flags.get('unique_positions')),
        ('摘要和layer1无占位符', content_flags.get('summary_layer1_clean')),
        ('未来事件至少两个情景', content_flags.get('events_have_two_scenarios')),
        ('每个情景有具体动作', content_flags.get('scenarios_have_specific_action')),
        ('持仓建议差异化', content_flags.get('advice_differentiated')),
        ('至少一个条件触发逻辑', content_flags.get('has_conditional_logic')),
        ('条件动作含执行前人工确认', content_flags.get('conditional_manual_confirm')),
        ('至少1个红色高危标的含具体触发', content_flags.get('red_holding_trigger')),
        ('包含4项子周期判断', content_flags.get('sub_cycle_four_items')),
        ('第1层按账户输出', content_flags.get('layer1_by_account')),
        ('包含5类持仓分层', content_flags.get('position_tiers_five')),
    ]
    failed = []
    for idx, (name, ok) in enumerate(checks, start=1):
        status = 'PASS' if ok else 'FAIL'
        print(f'[QUALITY_CHECK] {status}: 第{idx}项 {name}')
        if not ok:
            failed.append(f'第{idx}项 {name}')
    if failed:
        print('[质量自检FAIL] ' + '；'.join(failed))
        raise SystemExit(1)
    return checks


def generate_pdf_report(conclusions, results, today_str, *args, yesterday_validation=None):
    from io import BytesIO
    import shutil
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    if args:
        for _arg in args:
            if isinstance(_arg, str) and ("????" in _arg or "????" in _arg):
                yesterday_validation = _arg

    positions = _load_positions_unique()
    events = get_3day_events(today_str)
    sub_cycles = get_sub_cycle(positions, results, events)
    account_actions = get_account_actions(positions, conclusions, events, sub_cycles)
    conclusions['sub_cycles'] = sub_cycles
    if not isinstance(conclusions.get('layer1'), dict):
        conclusions['layer1'] = {k: v.get('动作边界', '') for k, v in account_actions.items()}
    tiers = get_position_tier(positions, sub_cycles)
    rotation = get_rotation_signal(results, positions, events, sub_cycles)
    summary = generate_60s_summary(conclusions, positions)
    advices = [get_position_advice(p, conclusions.get('cycle', 'BULL_MID'), conclusions.get('confidence', 'B')) for p in positions]
    manual = _manual_confirm_text()

    scenario_lines = []
    for event in events:
        scenario_lines.extend(event.get('scenarios', []) or [])
    action_words = ('加仓', '减仓', '止损', '降波动', '执行', '操作', '评估')
    conditional_lines = [line for line in scenario_lines + advices if '若[' in line or line.strip().startswith('若')]
    actionable_conditional = [line for line in conditional_lines if any(word in line for word in action_words)]
    content_flags = {
        'unique_positions': len({_position_code(p) for p in positions}) == len(positions),
        'summary_layer1_clean': all('账户待确认' not in x and '标的待确认' not in x for x in summary) and '账户待确认' not in _clean_layer1_text(conclusions.get('layer1')),
        'events_have_two_scenarios': bool(events) and all(len(e.get('scenarios', []) or []) >= 2 for e in events),
        'scenarios_have_specific_action': bool(scenario_lines) and all('→' in line and not line.endswith('等待确认') for line in scenario_lines),
        'advice_differentiated': len(set(advices)) > 1,
        'has_conditional_logic': bool(conditional_lines),
        'conditional_manual_confirm': all((manual in line) or ('专题研报确认' in line) or ('等待行情数据接入后确认' in line) or ('持有观察' in line) or ('不追高' in line) for line in actionable_conditional),
        'red_holding_trigger': any(('🔴' in advice and ('若[' in advice or '若' in advice)) for advice in advices),
        'sub_cycle_four_items': all(k in sub_cycles for k in ('AI核心子周期', '加密/高Beta子周期', '日本/日股子周期', 'A股子周期')),
        'layer1_by_account': isinstance(conclusions.get('layer1'), dict) and all(k in conclusions['layer1'] for k in ('富途', 'SBI', 'IBKR', 'BF')),
        'position_tiers_five': all(k in tiers for k in ('核心仓', '高Beta仓', '防守仓', '观察仓', '问题仓')),
    }
    quality_check(content_flags)

    desktop_base = Path(r'C:\Users\zhu20\OneDrive\桌面\股票分析与研究')
    desktop_base.mkdir(parents=True, exist_ok=True)
    fixed_pdf = desktop_base / '00_今日日报.pdf'
    archive_pdf = desktop_base / f'AI投研日报_{today_str}.pdf'

    font_name = 'Helvetica'
    for font_path, candidate in [
        (r'C:\Windows\Fonts\msyh.ttc', 'MSYH'),
        (r'C:\Windows\Fonts\simsun.ttc', 'SimSun'),
        (r'C:\Windows\Fonts\simhei.ttf', 'SimHei'),
    ]:
        try:
            if Path(font_path).exists():
                pdfmetrics.registerFont(TTFont(candidate, font_path))
                font_name = candidate
                break
        except Exception:
            continue

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 42
    y = height - 42

    def new_page():
        nonlocal y
        c.showPage()
        c.setFont(font_name, 10)
        y = height - 42

    def draw(text, size=10, leading=15, bold=False):
        nonlocal y
        if y < 56:
            new_page()
        c.setFont(font_name, size)
        max_chars = max(18, int((width - margin * 2) / (size * 0.58)))
        for raw_line in str(text).split('\n'):
            line = raw_line.rstrip()
            while len(line) > max_chars:
                c.drawString(margin, y, line[:max_chars])
                y -= leading
                if y < 56:
                    new_page()
                line = line[max_chars:]
            c.drawString(margin, y, line)
            y -= leading

    def section(title):
        nonlocal y
        if y < 90:
            new_page()
        y -= 4
        draw(f'★ {title}', size=13, leading=19)

    # Page 1
    draw(f'AI投研日报｜{today_str}', size=18, leading=24)
    draw(f'生成时间：{datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")}｜数据来源：daily_data_fetch + position_snapshot 只读快照', size=9, leading=14)
    section('今日决策摘要（60秒版）')
    for item in summary:
        draw(f'• {item}', size=10, leading=15)
    section('今日市场数据')
    for key, label in [('vix', 'VIX'), ('tnx', '10Y美债'), ('spx', 'SPX'), ('btc', 'BTC')]:
        item = results.get(key, {}) if isinstance(results, dict) else {}
        draw(f'{label}: {item.get("value", "DATA_GAP")}｜状态:{item.get("status", "DATA_GAP")}｜来源:{item.get("source", "未知")}', size=10)
    section('今日结论')
    draw(f'周期标签：{conclusions.get("cycle", "UNKNOWN")}｜置信度：{conclusions.get("confidence", "?")}', size=10)
    draw(f'第0层：{conclusions.get("layer0", "无")}', size=10)
    draw('第1层（按账户）：', size=10)
    for account, action in conclusions.get('layer1', {}).items():
        draw(f'- {account}: {action}', size=10)
    draw('第2层：', size=10)
    for item in conclusions.get('layer2', [])[:4]:
        draw(f'- {item}', size=10)
    section('子周期判断（P1恢复）')
    for key in ('AI核心子周期', '加密/高Beta子周期', '日本/日股子周期', 'A股子周期'):
        draw(f'{key}: {sub_cycles.get(key)}', size=10)

    # Page 2
    new_page()
    section('持仓分层（5类）')
    for tier, items in tiers.items():
        draw(f'{tier}: {"；".join(items)}', size=10)
    section('资金轮动主线（5行以内）')
    for line in rotation[:5]:
        draw(f'• {line}', size=10)
    section('四账户动作边界')
    for account, details in account_actions.items():
        draw(f'{account}: 今日关注={details["今日关注"]}；动作边界={details["动作边界"]}；禁止={details["禁止"]}；{details["执行前人工确认"]}', size=9, leading=14)
    section('未来3日条件计划')
    for event in events:
        draw(event.get('display', ''), size=10)
        draw(f'影响: {" / ".join(event.get("targets", []))}', size=9, leading=13)
        for scenario in event.get('scenarios', []):
            draw(f'- {scenario}', size=9, leading=13)

    # Page 3
    new_page()
    section('持仓风险速览与条件触发建议')
    for pos, advice in zip(positions, advices):
        code = _position_code(pos)
        name = _position_name(pos)
        color, risk_text = get_position_risk_level(_position_pnl_pct(pos), code)
        qty = _position_qty(pos)
        cost = _position_cost(pos)
        price = _position_price(pos)
        draw(f'{code} {name}｜数量:{qty:g}｜成本:{cost:.2f}｜现价:{price:.2f}｜{color} {risk_text}', size=9, leading=13)
        for line in advice.split('\n')[1:]:
            draw(f'  {line}', size=8.5, leading=12)
    section('本月目标进度')
    draw(get_monthly_progress(), size=10)
    section('研报触发提醒')
    research_line = get_research_trigger(positions, events)
    draw(research_line, size=10)
    section('今日必做事项')
    draw('1. 打开 00_今日日报.pdf 只读确认。', size=10)
    draw(f'2. 若发生任何账户动作，先执行人工确认：{manual}。', size=10)
    draw('3. 不接券商交易接口，不自动下单，不输出直接交易指令。', size=10)
    section('免责声明')
    draw('本日报仅用于投研与账户结构参考，不构成投资建议；任何交易均需用户人工确认后自行执行。', size=9, leading=13)

    c.save()
    pdf_bytes = buffer.getvalue()
    archive_pdf.write_bytes(pdf_bytes)
    shutil.copyfile(archive_pdf, fixed_pdf)
    print(f'[PDF] 已写入唯一入口: {fixed_pdf}')
    print(f'[PDF] 已写入日期归档: {archive_pdf}')
    return {'fixed_pdf': str(fixed_pdf), 'archive_pdf': str(archive_pdf), 'bytes': len(pdf_bytes), 'pages_estimate': 3, 'research_trigger': research_line}

def update_start_here(today_str: str, conclusions: dict) -> None:
    """更新 START_HERE.html 中的日期字符串"""
    if not START_HERE_PATH.exists():
        print(f"⚠ START_HERE.html 未找到，跳过更新")
        return
    content = START_HERE_PATH.read_text(encoding="utf-8", errors="ignore")
    # 替换日期（格式 YYYY-MM-DD）
    import re
    yesterday = re.findall(r'\d{4}-\d{2}-\d{2}', content)
    if yesterday:
        old_date = yesterday[0]
        if old_date != today_str:
            content = content.replace(old_date, today_str)
            START_HERE_PATH.write_text(content, encoding="utf-8")
            print(f"✓ START_HERE.html 日期已更新 {old_date} → {today_str}")
        else:
            print(f"✓ START_HERE.html 日期已是今日，无需更新")
    else:
        print("⚠ START_HERE.html 中未找到日期字符串，跳过更新")


# ─────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────

def main():
    print("[MAIN_START] auto_briefing 启动")
    import argparse
    parser = argparse.ArgumentParser(description="自动决策简报")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--auto-confirm", action="store_true")
    args = parser.parse_args(sys.argv[1:])
    print(f"[ARGS_PARSED] dry_run={args.dry_run} auto_confirm={args.auto_confirm}")

    today_str = datetime.now(JST).strftime("%Y-%m-%d")
    t_start = time.time()

    # 获取数据
    print("\n[FETCH] 获取市场数据...")
    results = {
        "vix":    fetch_vix(),
        "tnx":    fetch_tnx(),
        "spx":    fetch_spx_change(),
        "btc":    fetch_btc_change(),
        "config": fetch_user_config(),
    }
    display_data_status(results)

    # 昨日验证
    yesterday_validation = get_yesterday_validation(results)

    # 六步查表
    vix_val     = results["vix"]["value"]
    tnx_val     = results["tnx"]["value"]
    spx_val     = results["spx"]["value"]
    btc_val     = results["btc"]["value"]
    crypto_pct  = results["config"]["crypto_position_pct"]

    cycle, confidence = step1_cycle(vix_val, tnx_val, spx_val, btc_val)
    allocation        = step2_allocation(crypto_pct)
    signals           = step3_signal(spx_val, btc_val)
    conclusions       = generate_conclusions(
        cycle, confidence, signals, crypto_pct)
    next_steps        = generate_next_steps(
        confidence, conclusions["layer1"])

    # 输出结论（变更项3：仅输出三层结论）
    print("\n" + "=" * 60)
    print("AUTO DECISION BRIEFING")
    print(f"日期: {today_str}  周期: {cycle}  置信度: {confidence}")
    print("=" * 60)
    print(yesterday_validation)
    print("-" * 60)
    print(f"第0层 今日结论  : {conclusions['layer0']}")
    print(f"第1层 唯一动作  : {conclusions['layer1']}")
    print(f"第2层 最不能做  : {' / '.join(conclusions['layer2'])}")
    print("-" * 60)
    print(f"NEXT_OWNER  : {next_steps['NEXT_OWNER']}")
    print(f"NEXT_ACTION : {next_steps['NEXT_ACTION']}")
    print(f"NEXT_THREAD : {next_steps['NEXT_THREAD']}")
    print("=" * 60)
    print()
    print("⚠️  本输出仅供参考。禁止自动下单。禁止修改账户文件。")
    print("    执行前必须用户人工确认。")

    t_elapsed = time.time() - t_start
    print(f"\n总耗时: {t_elapsed:.2f} 秒")

    if args.dry_run:
        print("[DRY RUN] 完成，未写入任何文件。")
        sys.exit(0)

    # 用户确认：手动运行仍需输入Y；任务计划可用 --auto-confirm 自动确认。
    if args.auto_confirm:
        print("\n[AUTO_CONFIRM] 已启用自动确认，跳过手动输入Y。")
        answer = "Y"
    else:
        print("\n以上结论是否写入 daily_briefing_template_v1.md？")
        print("输入 Y 确认写入，输入 N 取消：")
        answer = input("  > ").strip().upper()
    if answer != "Y":
        print("已取消。")
        sys.exit(0)

    # 写入模板（追加当日区块）
    today_marker = f"日期: {today_str}"
    template_text = TEMPLATE_PATH.read_text(
        encoding="utf-8", errors="ignore")
    if today_marker in template_text:
        print(f"⚠ 当日记录已存在，禁止覆盖。")
        sys.exit(1)

    block = f"""
────────────────────────────────────────
AUTO BRIEFING [{today_str}]（由 auto_briefing.py 自动写入）
────────────────────────────────────────
日期: {today_str}
周期: {cycle}  置信度: {confidence}
第0层 今日结论 : {conclusions['layer0']}
第1层 唯一动作 : {conclusions['layer1']}
第2层 最不能做 : {' / '.join(conclusions['layer2'])}
NEXT_OWNER     : {next_steps['NEXT_OWNER']}
NEXT_ACTION    : {next_steps['NEXT_ACTION']}
NEXT_THREAD    : {next_steps['NEXT_THREAD']}
"""
    with open(TEMPLATE_PATH, "a", encoding="utf-8") as f:
        f.write(block)
    print(f"✓ 结论已写入模板 [{today_str}]")

    # 写入四份 latest_*.md
    write_latest_cards(conclusions, results, today_str, next_steps, yesterday_validation)

    # 生成PDF日报（写入桌面）
    try:
        pdf_file = generate_pdf_report(
            conclusions, results, today_str,
            next_steps, None, yesterday_validation)
        print(f"✓ PDF日报已生成：{pdf_file}")
    except Exception as e:
        print(f"⚠ PDF生成失败，请检查reportlab安装：{e}")

    # 更新 START_HERE.html
    update_start_here(today_str, conclusions)

    # 写入 briefing 记录（变更项2）
    write_briefing_log(conclusions, results, today_str, yesterday_validation)
    print()
    print("─" * 60)
    print("📋 交易记录提示")
    print(f"今日是否有交易？")
    print(f"  有 → 打开 trade_record_log_v1.md 记录")
    print(f"  无 → 无需操作")
    print("─" * 60)

    sys.exit(0)


if __name__ == "__main__":
    main()








