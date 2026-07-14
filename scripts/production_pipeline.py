from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# 护城河沿用超过该天数 → 产品出"建议重评"提示（常量可调·总则第五/十二条：慢变可沿用但不能永不重评）
MOAT_REEVAL_DAYS = 10

NODE_ALIASES = {
    "算力": ["算力"],
    "半导体设备": ["半导体设备", "设备"],
    "代工": ["代工"],
    "电力": ["电力"],
    "存储": ["存储"],
    "AI应用软件": ["AI应用软件", "软件"],
    "盟友链": ["盟友链", "日韩链", "盟友"],
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def money_number(value: Any):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value).replace(",", "")
    token = ""
    started = False
    dot_seen = False
    for ch in raw:
        if ch.isdigit():
            token += ch
            started = True
        elif ch == "." and started and not dot_seen:
            token += ch
            dot_seen = True
        elif ch == "-" and not started and not token:
            token += ch
        elif started:
            break
    if token in ("", "-", "."):
        return None
    try:
        return float(token)
    except ValueError:
        return None


def extract_active_nodes(evidence: dict[str, Any]) -> list[str]:
    derived = evidence.get("derived", {})
    derived_text = " ".join(str(derived.get(k, "")) for k in ("today_direction", "opportunity_scope", "decision_constraint"))
    active = []
    for node, aliases in NODE_ALIASES.items():
        if any(alias in derived_text for alias in aliases):
            if node == "AI应用软件" and "不纳入" in derived_text and "软件" in derived_text:
                continue
            if node == "存储" and "不纳入" in derived_text and "存储" in derived_text:
                continue
            if node == "盟友链" and "不纳入" in derived_text and ("盟友" in derived_text or "日韩" in derived_text):
                continue
            active.append(node)
    return active


def find_link(evidence: dict[str, Any], keyword: str) -> dict[str, Any]:
    for link in evidence.get("links", []):
        if keyword in str(link.get("node", "")):
            return link
    return {}


def technical_label(value: dict[str, Any] | None) -> dict[str, Any]:
    if not value:
        return {"status": "待补", "label": "技术待补", "reason": "无技术维数据"}
    cur = money_number(value.get("current_price"))
    ma200 = money_number(value.get("ma200"))
    high60 = money_number(value.get("high60"))
    low60 = money_number(value.get("low60"))
    if cur is None:
        return {"status": "待补", "label": "技术待补", "reason": "现价待补"}
    reasons = []
    if ma200:
        reasons.append(f"现价/MA200={cur / ma200:.2f}")
    if high60:
        reasons.append(f"现价/60高={cur / high60:.2f}")
    if low60:
        reasons.append(f"现价/60低={cur / low60:.2f}")
    if ma200 and cur <= ma200 * 1.10:
        label = "位置好"
    elif high60 and cur >= high60 * 0.95:
        label = "位置偏高"
    elif ma200 and cur >= ma200 * 1.35:
        label = "位置偏高"
    else:
        label = "位置中性"
    return {"status": "OK", "label": label, "reason": "；".join(reasons) or "技术位可用"}


def load_technical_map(dual: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for item in dual.get("channel_2_trade_price", {}).get("instruments", []):
        code = item.get("code") or item.get("ticker")
        tech = item.get("six_dimensions", {}).get("技术维", {})
        if code:
            result[code] = {
                "kind": item.get("kind"),
                "node_class": item.get("node_class"),
                "technical": technical_label(tech.get("value")),
                "technical_raw": tech.get("value"),
                "funds": item.get("six_dimensions", {}).get("资金维", {}),
            }
    return result


def parse_valuation_instances(inst_dir: Path) -> dict[str, dict[str, Any]]:
    instances = {}
    for path in sorted(inst_dir.glob("*.json")):
        data = read_json(path)
        symbol = data.get("symbol")
        if not symbol:
            continue
        bands = data.get("valuation_bands", {})
        base = money_number(bands.get("base"))
        cheap = money_number(bands.get("cheap") or bands.get("low_buy"))
        expensive = money_number(
            bands.get("expensive") or bands.get("expensive_or_reduce") or bands.get("偏贵可减")
        )
        instances[symbol] = {
            "name": data.get("name"),
            "model_type": data.get("model_type") or data.get("模型类型"),
            "base": base,
            "cheap_threshold": cheap,
            "expensive_threshold": expensive,
            "bands": bands,
            "conclusion": data.get("conclusion", ""),
            "source_file": path.name,
        }
    return instances


def valuation_label(instance: dict[str, Any] | None, current_price: Any) -> dict[str, Any]:
    if not instance:
        return {"status": "待补", "label": "估值待补", "reason": "无模型实例"}
    price = money_number(current_price)
    if price is None:
        return {"status": "待补", "label": "估值待补", "reason": "现价待补", "model_type": instance.get("model_type")}
    base = instance.get("base")
    cheap = instance.get("cheap_threshold")
    expensive = instance.get("expensive_threshold")
    if cheap and price < cheap:
        label = "便宜"
    elif expensive and price > expensive:
        label = "贵"
    elif base and price <= base:
        label = "合理偏便宜"
    elif base and price <= base * 1.10:
        label = "合理"
    elif base:
        label = "贵"
    else:
        label = "估值待判"
    reason_bits = []
    if base:
        reason_bits.append(f"现价/基准={price / base:.2f}")
    if cheap:
        reason_bits.append(f"便宜线={cheap:g}")
    if expensive:
        reason_bits.append(f"偏贵线={expensive:g}")
    return {
        "status": "OK",
        "label": label,
        "reason": "；".join(reason_bits) or "模型实例存在",
        "model_type": instance.get("model_type"),
        "source_file": instance.get("source_file"),
    }


def _moat_evaluated_count(data: dict[str, Any]) -> int:
    """已评项数：moat_grade 非空且非'待补/待理解岗打分'。"""
    n = 0
    for it in data.get("items", []):
        g = str(it.get("moat_grade") or "")
        if g and "待补" not in g and g != "待理解岗打分":
            n += 1
    return n


def resolve_moat_source(date: str) -> tuple[dict[str, Any], str, bool]:
    """护城河跨天沿用（慢变·像A8股数沿用）。

    当日 moat_analysis_{date}.json 不存在或未评→沿用"最近一版已评"的 moat_analysis。
    返回 (data, used_date, carried)。carried=True 表示沿用自另一天。
    """
    exact = ROOT / "data" / "moat" / f"moat_analysis_{date}.json"
    if exact.exists():
        data = read_json(exact)
        if _moat_evaluated_count(data) > 0:
            return data, date, False  # 当日已评·用当日

    # 沿用：在已评的历史版本里取"不晚于 date 的最近一版"；无则取整体最近一版
    evaluated: list[tuple[str, dict[str, Any]]] = []
    for p in (ROOT / "data" / "moat").glob("moat_analysis_*.json"):
        stem = p.stem.replace("moat_analysis_", "")
        if not stem.isdigit():
            continue
        try:
            data = read_json(p)
        except Exception:
            continue
        if _moat_evaluated_count(data) > 0:
            evaluated.append((stem, data))
    if not evaluated:
        return {}, "", False
    evaluated.sort(key=lambda x: x[0])
    not_future = [e for e in evaluated if e[0] <= date]
    used_stem, used_data = (not_future or evaluated)[-1]
    return used_data, used_stem, used_stem != date


def load_moat_map(date: str) -> tuple[dict[str, dict[str, Any]], str, bool]:
    data, used_date, carried = resolve_moat_source(date)
    moat_map = {str(item.get("symbol")): item for item in data.get("items", []) if item.get("symbol")}
    return moat_map, used_date, carried


def moat_staleness(date: str, used_date: str) -> tuple[int | None, bool, str | None]:
    """算护城河沿用天数=当日−已评日期；> MOAT_REEVAL_DAYS → 出重评提示(只提示不改评级)。"""
    if not used_date or not date.isdigit() or not used_date.isdigit():
        return None, False, None
    try:
        d0 = datetime.strptime(date, "%Y%m%d")
        d1 = datetime.strptime(used_date, "%Y%m%d")
    except ValueError:
        return None, False, None
    days = (d0 - d1).days
    if days > MOAT_REEVAL_DAYS:
        return days, True, f"护城河已沿用 {days} 天(自 {used_date})·超 {MOAT_REEVAL_DAYS} 天阈值·建议理解岗重评（提示不自动改评级）"
    return days, False, None


def moat_label(item: dict[str, Any] | None) -> dict[str, Any]:
    if not item:
        return {
            "status": "待理解岗打分",
            "moat_grade": "待补护城河",
            "total_score": None,
            "confidence": "待补",
            "basis": "无护城河实例",
        }
    return {
        "status": item.get("status", "待理解岗打分"),
        "moat_grade": item.get("moat_grade", "待补护城河"),
        "total_score": item.get("total_score"),
        "confidence": item.get("confidence", "待补"),
        "basis": item.get("basis", ""),
        "source_file": item.get("source_file"),
        "dimensions": item.get("dimensions", {}),
    }


def decide_action(pipeline_verdict: str, soft: str, valuation: str, moat: str) -> tuple[str, str]:
    if pipeline_verdict != "符合":
        return "等", f"硬性={pipeline_verdict}→受检，不做主动动作；护城河={moat}"
    if valuation in ("贵",) or soft == "位置偏高":
        return "守", f"硬性=符合方向+软性={soft}+估值={valuation}+护城河={moat}→守不追"
    if moat == "宽护城河" and valuation in ("便宜", "合理偏便宜") and soft in ("位置好", "位置中性"):
        return "守", f"硬性=符合方向+软性={soft}+估值={valuation}+护城河={moat}→优质，重点"
    if valuation in ("便宜", "合理偏便宜") and soft in ("位置好", "位置中性"):
        return "守", f"硬性=符合方向+软性={soft}+估值={valuation}+护城河={moat}→守"
    return "守", f"硬性=符合方向+软性={soft}+估值={valuation}+护城河={moat}→守"


def build(date: str) -> dict[str, Any]:
    evidence_path = ROOT / "data" / "evidence_chain" / f"daily_{date}.json"
    holdings_path = ROOT / "data" / "holdings" / f"holdings_review_{date}.json"
    dual_path = ROOT / "data" / "opportunities" / f"dual_channel_{date}.json"
    if not evidence_path.exists():
        raise FileNotFoundError(f"缺求证表: {evidence_path}")
    if not holdings_path.exists():
        raise FileNotFoundError(f"缺持仓审查: {holdings_path}")
    if not dual_path.exists():
        raise FileNotFoundError(f"缺双通道: {dual_path}")

    evidence = read_json(evidence_path)
    holdings = read_json(holdings_path)
    dual = read_json(dual_path)
    active_nodes = extract_active_nodes(evidence)
    tech_map = load_technical_map(dual)
    valuations = parse_valuation_instances(ROOT / "data" / "valuation" / "model_instances")
    moats, moat_used_date, moat_carried = load_moat_map(date)
    moat_staleness_days, moat_reeval_needed, moat_reeval_msg = moat_staleness(date, moat_used_date)
    today_direction = evidence.get("derived", {}).get("today_direction", "待填")
    today_direction_short = evidence.get("derived", {}).get("today_direction_short", "")

    holding_results = []
    counts = {"符合": 0, "受检": 0, "待补": 0}
    for review in holdings.get("reviews", []):
        symbol = review.get("symbol")
        matched = review.get("matched_node_classes") or []
        effective_matched = [node for node in matched if node in active_nodes]
        if effective_matched:
            pipeline_verdict = "符合"
        elif review.get("verdict") == "符合" and not active_nodes:
            pipeline_verdict = "待补"
        else:
            pipeline_verdict = "受检"
        counts[pipeline_verdict] = counts.get(pipeline_verdict, 0) + 1
        soft = tech_map.get(symbol, {}).get("technical", {"status": "待补", "label": "技术待补", "reason": "双通道无该标的"})
        val = valuation_label(valuations.get(symbol), review.get("realtime_price"))
        moat = moat_label(moats.get(symbol))
        action, reason = decide_action(pipeline_verdict, soft.get("label", "技术待补"), val.get("label", "估值待补"), moat.get("moat_grade", "待补护城河"))
        holding_results.append({
            "symbol": symbol,
            "name": review.get("name"),
            "quantity": review.get("total_quantity"),
            "price": review.get("realtime_price"),
            "market_value": review.get("market_value"),
            "raw_holding_verdict": review.get("verdict"),
            "matched_node_classes_raw": matched,
            "matched_node_classes_effective": effective_matched,
            "hard_filter": pipeline_verdict,
            "soft_filter": soft,
            "valuation": val,
            "moat": moat,
            "action": action,
            "one_line_reason": reason,
        })
    # 基本面质量关(试行·尺=基本面质量关框架.html)：放硬性闸之后·三档判定·防误杀三条·缺数待接不编(总则:不锚死名单)
    try:
        from quality_gate import grade_holdings as _grade_quality
        _quality_map = _grade_quality(holding_results)
        for _h in holding_results:
            _h["quality_gate"] = _quality_map.get(str(_h.get("symbol")), {"tier": "②", "tier_label": "趋势观察·不杀", "why": "待接"})
    except Exception as _qe:                     # 质量关消费方缺失时不破坏既有产出(试行·可降级)
        for _h in holding_results:
            _h.setdefault("quality_gate", {"tier": "待接", "tier_label": "质量关待接", "why": f"质量关模块不可用({_qe})"})

    opportunities = []
    for item in dual.get("channel_2_trade_price", {}).get("instruments", []):
        if item.get("kind") != "A类候选":
            continue
        node = item.get("node_class")
        hard = "符合激活节点" if node in active_nodes else "不在当日激活节点"
        tech = tech_map.get(item.get("code"), {}).get("technical", {"status": "待补", "label": "技术待补"})
        opportunities.append({
            "channel": "通道②新机会",
            "code": item.get("code"),
            "name": item.get("name"),
            "node_class": node,
            "hard_filter": hard,
            "soft_filter": tech,
            "moat": moat_label(moats.get(item.get("code"))),
        })

    channel1 = []
    for item in dual.get("channel_1_best_holding", {}).get("comparisons", []):
        node = item.get("同节点")
        current = item.get("现持仓标的", {})
        candidate = item.get("候选标的", {})
        channel1.append({
            "channel": "通道①换仓对比",
            "current_holding": current,
            "candidate": candidate,
            "node_class": node,
            "hard_filter": "符合激活节点" if node in active_nodes else "不在当日激活节点",
            "candidate_soft_filter": tech_map.get(candidate.get("code"), {}).get("technical", {"status": "待补", "label": "技术待补"}),
            "current_soft_filter": tech_map.get(current.get("code"), {}).get("technical", {"status": "待补", "label": "技术待补"}),
            "candidate_moat": moat_label(moats.get(candidate.get("code"))),
            "current_moat": moat_label(moats.get(current.get("code"))),
            "decision": item.get("建议", "待理解岗判断"),
        })

    return {
        "task_id": "TASK-2026-07-02-064",
        "mode": "formal",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fingerprint": {
            "date": date,
            "framework_fixed": True,
            "answers_from_daily": True,
            "evidence_source": str(evidence_path),
            "holdings_source": str(holdings_path),
            "dual_channel_source": str(dual_path),
            "valuation_instances_dir": str(ROOT / "data" / "valuation" / "model_instances"),
            "moat_analysis_source": str(
                ROOT / "data" / "moat" / f"moat_analysis_{moat_used_date or date}.json"
            ),
            "moat_carry_note": (
                f"护城河沿用自 {moat_used_date}·待重评则更新（慢变跨天persist，不回待补）"
                if moat_carried else
                (f"护城河=当日已评 {moat_used_date}" if moat_used_date else "护城河=无任何已评版本·待理解岗打分")
            ),
            "moat_used_date": moat_used_date,
            "moat_staleness_days": moat_staleness_days,
            "moat_reeval_days_threshold": MOAT_REEVAL_DAYS,
            "moat_reeval_needed": moat_reeval_needed,
            "moat_reeval_msg": moat_reeval_msg,
        },
        "today_direction": today_direction,
        "today_direction_short": today_direction_short,
        "activated_nodes": active_nodes,
        "evidence_summary": {
            "world": find_link(evidence, "总命题"),
            "fed_gate": find_link(evidence, "总闸"),
            "strategy": find_link(evidence, "战略指向"),
            "flow": find_link(evidence, "资金轮动"),
        },
        "holding_summary": counts,
        "holdings": holding_results,
        "opportunity_pool": {
            "channel_1_swap_comparisons": channel1,
            "channel_2_new_opportunities": opportunities,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run evidence-driven production pipeline")
    parser.add_argument("--date", default="20260702")
    args = parser.parse_args()
    output = build(args.date)
    output_path = ROOT / "data" / "reports" / f"production_{args.date}.json"
    write_json(output_path, output)
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
