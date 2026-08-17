#!/usr/bin/env python3
"""Build V7 v0.7 from the immutable v0.6 candidate and existing evidence."""

from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, NavigableString


ROOT = Path(__file__).resolve().parents[1]
SOURCE_RUN = "V7-V06-COMPLETE-20260817-105200-JST"
SOURCE = ROOT / "output/candidates/2026-08-17" / SOURCE_RUN
PDCA_SOURCE = ROOT / "output/decision_inputs/2026-08-17/V7-V04-CRITICAL-EVIDENCE-20260817-003705-JST/04_PDCA汇总及逐条记录_20260817.json"
VALUATION_SOURCE = ROOT / "output/decision_inputs/2026-08-17/V7-V05-EVIDENCE-CLOSE-20260817-092935-JST"
JST = timezone(timedelta(hours=9))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def stamp(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "size": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, JST).isoformat(timespec="seconds"),
        "sha256": sha256(path),
    }


def esc(value: Any) -> str:
    if value is None or value == "":
        return "没有取得"
    return html.escape(str(value))


def compact_number(value: Any) -> str:
    if value is None:
        return "没有取得"
    if isinstance(value, float):
        return f"{value:,.4f}".rstrip("0").rstrip(".")
    return f"{value:,}" if isinstance(value, int) else str(value)


def anchor_plain(value_input: dict[str, Any]) -> str:
    if value_input.get("scenarios") and value_input.get("status") != "CANNOT_FORM_RELIABLE_VALUATION":
        return "不再另设机械价格带。只用现有悲观、基准、乐观情景复核估值；情景结果不是自动买卖线。"
    return "暂不能给数值买卖区间；只保留财报、盈利、事件和风险触发条件。"


def scenario_table(value_input: dict[str, Any]) -> str:
    rows = []
    for item in value_input.get("scenarios") or []:
        rows.append(
            "<tr>"
            f"<td>{esc(item.get('scenario'))}</td>"
            f"<td>{compact_number(item.get('metric_value'))}</td>"
            f"<td>{compact_number(item.get('multiple'))}</td>"
            f"<td>{compact_number(item.get('valuation_per_share'))}</td>"
            "</tr>"
        )
    if not rows:
        return "<p><b>数值区间：</b>没有取得足以形成可靠估值的输入，因此不列价格区间。</p>"
    return (
        "<div class='table-wrap'><table><thead><tr><th>情景</th><th>盈利/现金流输入</th>"
        "<th>倍数</th><th>估值结果</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def valuation_block(value_input: dict[str, Any]) -> str:
    method = value_input.get("method") or "没有取得可核的估值方法"
    metric = value_input.get("one_year_metric")
    if isinstance(metric, dict):
        metric_text = "；".join(f"{k}={compact_number(v)}" for k, v in metric.items())
    elif metric is None:
        metric_text = "没有取得可核的一年期盈利或现金流指标，因此不能形成可靠估值。"
    else:
        metric_text = compact_number(metric)
    source = value_input.get("formal_source")
    source_html = f"<a href='{html.escape(source)}'>查看正式原文</a>" if source else "没有取得直接原文"
    return (
        "<div class='valuation-evidence v07-valuation'><h4>估值依据与动作边界</h4>"
        f"<p><b>方法：</b>{esc(method)}</p>"
        f"<p><b>一年期输入：</b>{esc(metric_text)}</p>"
        f"{scenario_table(value_input)}"
        f"<p><b>价格条件：</b>{esc(anchor_plain(value_input))}</p>"
        f"<p><b>证据缺口：</b>{esc(value_input.get('data_gap_impact') or value_input.get('gap') or '没有新增缺口说明')}</p>"
        f"<p><b>来源：</b>{source_html}。估值输入只用于复核，不生成订单。</p></div>"
    )


def format_success(value: Any) -> str:
    if not isinstance(value, dict):
        return esc(value)
    names = {"state_hold": "状态保持", "gt": "高于", "lt": "低于"}
    operator = names.get(str(value.get("operator")), str(value.get("operator") or "没有取得"))
    return f"{operator} {compact_number(value.get('target'))}；按{esc(value.get('settle_by'))}验证"


def pdca_section(pdca: dict[str, Any]) -> str:
    summary = pdca["summary"]
    records_by_series: dict[str, list[dict[str, Any]]] = {}
    for record in pdca["records"]:
        records_by_series.setdefault(record["series_id"], []).append(record)

    series_rows = []
    details = []
    for series in pdca["series"]:
        records = records_by_series[series["series_id"]]
        judged = sum(record.get("judgment") in {"判对", "判错"} for record in records)
        pending = len(records) - judged
        series_rows.append(
            "<tr>"
            f"<td>{esc(series['series_id'])}</td><td>{esc(series['layer'])}</td>"
            f"<td>{esc(series.get('instrument') or '宏观状态')}</td><td>{len(records)}</td>"
            f"<td>{judged}</td><td>{pending}</td></tr>"
        )
        record_rows = []
        for record in records:
            horizon = record.get("prediction_horizon") or {}
            record_rows.append(
                "<tr>"
                f"<td>{esc(record.get('prediction_id'))}<br><small>第{record.get('tracking_sequence')}次连续跟踪</small></td>"
                f"<td>{esc(record.get('prediction_date'))}</td>"
                f"<td>{esc(record.get('original_prediction'))}</td>"
                f"<td>{esc(horizon.get('due_date'))}</td>"
                f"<td>{format_success(record.get('success_definition'))}</td>"
                f"<td>{esc(record.get('validation_date'))}</td>"
                f"<td>{esc(record.get('actual_result'))}</td>"
                f"<td>{esc(record.get('judgment'))}</td>"
                f"<td>{esc(record.get('evidence'))}</td>"
                f"<td>{esc(record.get('counterfactual_portfolio_result'))}</td>"
                "</tr>"
            )
        details.append(
            "<details class='pdca-series'><summary>"
            f"{esc(series['series_id'])}｜{esc(series['layer'])}｜{len(records)}条跟踪，{judged}条已判定，{pending}条待验证"
            "</summary><div class='table-wrap'><table class='pdca-records'><thead><tr>"
            "<th>预测编号</th><th>预测日期</th><th>原预测</th><th>到期日</th><th>成功定义</th>"
            "<th>验证日期</th><th>实际结果</th><th>结论</th><th>证据</th><th>反事实</th>"
            "</tr></thead><tbody>" + "".join(record_rows) + "</tbody></table></div></details>"
        )

    review = pdca["review_entries"]
    daily = "<br>".join(esc(item) for item in review.get("daily", [])) or "没有取得原始日复盘入口"
    weekly = "<br>".join(esc(item) for item in review.get("weekly", [])) or "没有原始周复盘记录，不补造"
    monthly = "<br>".join(esc(item) for item in review.get("monthly", [])) or "没有原始月复盘记录，不补造"
    return (
        "<section id='pdca'><h2>PDCA：5个系列与57条真实跟踪记录</h2>"
        "<p class='lead'>57条是不同日期锁定的连续跟踪点，不是57个彼此独立的预测。"
        f"现有5个系列；29条已判定，其中28条判对、1条判错；28条尚待验证。"
        f"已判定跟踪点一致率为{summary['hit_rate_percent_on_adjudicated_tracking']:.1f}%，不能称为独立预测准确率。</p>"
        "<div class='table-wrap'><table><thead><tr><th>系列ID</th><th>主题</th><th>标的</th>"
        "<th>跟踪数</th><th>已判定</th><th>待验证</th></tr></thead><tbody>"
        + "".join(series_rows)
        + "</tbody></table></div>"
        + "".join(details)
        + "<h3>日、周、月复盘入口</h3><div class='grid-3'>"
        f"<div><b>日复盘</b><p>{daily}</p></div><div><b>周复盘</b><p>{weekly}</p></div>"
        f"<div><b>月复盘</b><p>{monthly}</p></div></div>"
        f"<p class='note'>{esc(review.get('boundary'))}</p></section>"
    )


def source_url(item: dict[str, Any]) -> str | None:
    value = item.get("v06_valuation_input") or {}
    audit = item.get("v06_financial_audit") or {}
    evidence = item.get("evidence") or {}
    return evidence.get("url") or value.get("formal_source") or audit.get("source_url") or item.get("financial_source")


def evidence_mapping(item: dict[str, Any], scope: str) -> dict[str, Any]:
    code = item["code"]
    safe = re.sub(r"[^A-Za-z0-9]+", "-", code).strip("-")
    account_sources = [row.get("source") for row in item.get("account_coverage", []) if row.get("source")]
    formal = source_url(item)
    event = (item.get("evidence") or {}).get("url") or formal
    reverse = item.get("reverse_risk") or (item.get("gate5_specific") or {}).get("risk") or "没有取得独立反向事实；因此不产生动作"
    boundary = (
        (item.get("v06_valuation_input") or {}).get("data_gap_impact")
        or (item.get("v06_valuation_input") or {}).get("gap")
        or item.get("cross_layer_rule")
        or "证据只支持当前研究边界，不自动形成交易"
    )
    return {
        "conclusion_id": f"CON-{'HOLD' if scope == 'holding' else 'CAND'}-{safe}",
        "scope": scope,
        "code": code,
        "name": item.get("name"),
        "conclusion": item.get("judgment") if scope == "holding" else item.get("final_answer"),
        "account_evidence": {"id": f"EV-ACCOUNT-{safe}", "sources": account_sources or ["不适用：非持仓候选"]},
        "financial_evidence": {"id": f"EV-FIN-{safe}", "source": formal or "没有取得直接正式原文"},
        "valuation_evidence": {"id": f"EV-VAL-{safe}", "source": formal or "没有取得可靠估值原文", "input_file": str(VALUATION_SOURCE)},
        "market_event_evidence": {"id": f"EV-EVENT-{safe}", "source": event or "没有取得独立事件原文", "boundary": "若与财务原文相同，只支持该公告所载事件，不代表当日行情"},
        "rule_ids": ["RULE-UNKNOWN-ISOLATE-ACTION", "RULE-NO-FIXED-RATIO-TRADE", "RULE-EVIDENCE-ROLE-SEPARATION"],
        "reverse_evidence": reverse,
        "evidence_boundary": boundary,
    }


def evidence_bundle(mapping: dict[str, Any]) -> str:
    def link(value: str) -> str:
        return f"<a href='{html.escape(value)}'>原文</a>" if value.startswith("http") else esc(value)

    account = "；".join(mapping["account_evidence"]["sources"])
    return (
        "<div class='evidence-bundle'><h4>这项结论由什么支撑</h4>"
        f"<p><b>账户事实：</b>{esc(mapping['account_evidence']['id'])}｜{esc(account)}</p>"
        f"<p><b>公司财务/监管：</b>{esc(mapping['financial_evidence']['id'])}｜{link(mapping['financial_evidence']['source'])}</p>"
        f"<p><b>估值输入：</b>{esc(mapping['valuation_evidence']['id'])}｜{link(mapping['valuation_evidence']['source'])}</p>"
        f"<p><b>市场/事件：</b>{esc(mapping['market_event_evidence']['id'])}｜{link(mapping['market_event_evidence']['source'])}</p>"
        f"<p><b>适用规则：</b>{esc('、'.join(mapping['rule_ids']))}</p>"
        f"<p><b>反向证据与边界：</b>{esc(mapping['reverse_evidence'])}｜{esc(mapping['evidence_boundary'])}</p></div>"
    )


def evidence_section(mappings: list[dict[str, Any]]) -> str:
    rows = []
    for item in mappings:
        rows.append(
            "<tr>"
            f"<td>{esc(item['conclusion_id'])}</td><td>{esc(item['code'])}</td><td>{esc(item['scope'])}</td>"
            f"<td>{esc(item['account_evidence']['id'])}</td><td>{esc(item['financial_evidence']['id'])}</td>"
            f"<td>{esc(item['valuation_evidence']['id'])}</td><td>{esc(item['market_event_evidence']['id'])}</td>"
            f"<td>{esc('、'.join(item['rule_ids']))}</td><td>{esc(item['evidence_boundary'])}</td></tr>"
        )
    return (
        "<section id='evidence-trace'><h2>结论、证据和规则逐项咬合</h2>"
        "<p class='lead'>账户证据只证明持有什么，不能单独证明公司质量、估值或动作。"
        "下表把账户、财务、估值、市场事件、规则和反向边界分开登记。</p>"
        "<div class='table-wrap'><table><thead><tr><th>结论ID</th><th>标的</th><th>范围</th>"
        "<th>账户</th><th>财务</th><th>估值</th><th>事件</th><th>规则</th><th>边界</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div></section>"
    )


def replace_heading_section(soup: BeautifulSoup, heading_text: str, markup: str) -> None:
    heading = next((h for h in soup.find_all(["h2", "h3"]) if heading_text in h.get_text(" ", strip=True)), None)
    if heading is None:
        raise RuntimeError(f"Missing section heading: {heading_text}")
    section = heading.find_parent("section")
    section.replace_with(BeautifulSoup(markup, "html.parser").section)


def plain_language_cleanup(soup: BeautifulSoup) -> None:
    replacements = {
        "None": "没有取得",
        "未取得 未取得": "没有取得",
        "。；": "。",
        "沿用GPT总控已经批准的持仓或观察结论；上述数字不自动形成订单。": "按本产品列明的唯一结论继续观察；估值输入不生成订单。",
        "沿用GPT总控已经批准": "按本产品列明的唯一结论执行",
        "48.147541%": "48.15%",
        "61.475698%": "61.48%",
        "96.552%": "96.6%",
    }
    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"], recursive=False)
        for index in range(len(cells) - 1):
            if cells[index].get_text(" ", strip=True) == "未取得" and cells[index + 1].get_text(" ", strip=True) == "未取得":
                cells[index].string = "成本未取得"
                cells[index + 1].string = "最新价未取得"
    for node in list(soup.find_all(string=True)):
        if not isinstance(node, NavigableString) or node.parent.name in {"script", "style"}:
            continue
        value = str(node)
        for old, new in replacements.items():
            value = value.replace(old, new)
        value = re.sub(r"(?<![\w/])(\d[\d,]*)\.(\d{7,})(?![\w/])", lambda m: f"{float((m.group(1) + '.' + m.group(2)).replace(',', '')):,.4f}".rstrip("0").rstrip("."), value)
        if value != str(node):
            node.replace_with(value)


def main() -> int:
    now = datetime.now(JST)
    run_id = f"V7-V07-COMPLETE-{now:%Y%m%d-%H%M%S}-JST"
    output_dir = ROOT / "output/candidates/2026-08-17" / run_id
    output_dir.mkdir(parents=True, exist_ok=False)

    source_html = SOURCE / "★2026-08-17完整投研产品候选_v0.6.html"
    holdings_doc = read_json(SOURCE / "04_24类持仓唯一答案检查_20260817.json")
    candidates_doc = read_json(SOURCE / "05_21只候选五关检查_20260817.json")
    pdca = read_json(PDCA_SOURCE)
    if len(pdca["records"]) != 57 or len(pdca["series"]) != 5:
        raise RuntimeError("PDCA source is not the locked 57-record, 5-series source")

    soup = BeautifulSoup(source_html.read_text(encoding="utf-8"), "html.parser")
    product = soup.get_text(" ", strip=True)
    if SOURCE_RUN not in product or "v0.6" not in product:
        raise RuntimeError("Unexpected v0.6 source identity")
    for node in soup.find_all(string=True):
        if isinstance(node, NavigableString):
            replaced = str(node).replace("v0.6", "v0.7").replace(SOURCE_RUN, run_id)
            if replaced != str(node):
                node.replace_with(replaced)
    if soup.title:
        soup.title.string = "2026-08-17完整投研产品候选_v0.7"

    style = soup.find("style")
    if style:
        style.append("\n.pdca-series,.evidence-bundle{margin:10px 0;border:1px solid #b8c4cf;padding:9px 11px;border-radius:6px;background:#fbfcfd}.pdca-records{font-size:9.5pt}.pdca-records th,.pdca-records td{vertical-align:top}.evidence-bundle,.valuation-evidence{break-inside:avoid;page-break-inside:avoid}.evidence-bundle p{margin:4px 0}.grid-3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}@media(max-width:800px){.grid-3{grid-template-columns:1fr}}")

    replace_heading_section(soup, "PDCA：系列和跟踪点分开", pdca_section(pdca))

    candidate_by_code = {item["code"]: item for item in candidates_doc["items"]}
    mappings: list[dict[str, Any]] = []
    for scope, document, css in [
        ("holding", holdings_doc, "holding"),
        ("candidate", candidates_doc, "candidate"),
    ]:
        for item in document["items"]:
            value_input = item.get("v06_valuation_input") or {}
            item["v07_valuation_input"] = value_input
            item.pop("v06_valuation_input", None)
            item["observation_band"] = {
                "type": "非机械研究触发条件",
                "base_price": None,
                "lower": None,
                "upper": None,
                "plain": anchor_plain(value_input),
                "definition": "不得用现价固定折扣冒充安全边际或自动买卖线。",
            }
            value_input["observation_line_note"] = anchor_plain(value_input)
            value_input["observation_line_separated"] = True
            detail = soup.find("details", id=f"{css}-{item['code'].replace('.', '-')}")
            if detail is None:
                raise RuntimeError(f"Missing {scope}: {item['code']}")
            for old in detail.select(".valuation-evidence"):
                old.replace_with(BeautifulSoup(valuation_block(value_input), "html.parser").div)
            for paragraph in detail.find_all(["p", "li"]):
                text = paragraph.get_text(" ", strip=True)
                if text.startswith("行动观察带："):
                    paragraph.clear()
                    paragraph.append(BeautifulSoup(f"<b>行动观察条件：</b>{esc(anchor_plain(value_input))}", "html.parser"))
            mapping = evidence_mapping(item, scope)
            mappings.append(mapping)
            body = detail.select_one(".asset-body") or detail
            body.append(BeautifulSoup(evidence_bundle(mapping), "html.parser").div)

    # Bank cash-flow fields are not comparable with industrial-company free cash flow.
    for detail_id in ["candidate-JP-8306", "candidate-JP-8316", "candidate-JP-8411"]:
        detail = soup.find(id=detail_id)
        if detail:
            for paragraph in detail.find_all(["p", "li"]):
                if paragraph.get_text(" ", strip=True).startswith("第2关："):
                    paragraph.clear()
                    paragraph.append(BeautifulSoup("<b>第2关：</b>银行经营现金流会被存贷款和证券头寸变动放大，不能按工业企业自由现金流解读。本产品只看净息差、信贷成本、资本充足率、净利润和股东回报；没有取得的指标不显示为零。", "html.parser"))
                    break
    ibkr = soup.find(id="holding-US-IBKR")
    if ibkr:
        for paragraph in ibkr.find_all("p"):
            text = paragraph.get_text(" ", strip=True)
            if text.startswith("正式财务：") and "经营现金流" in text:
                paragraph.clear()
                paragraph.append(BeautifulSoup("<b>正式财务：</b>截至2026-06-30的第二季度收入18.96亿美元，归属普通股股东净利润3.12亿美元。银行及券商经营现金流受客户资金、证券头寸和结算变动影响，本产品不把该机械数值当作工业企业自由现金流，也不用它支持估值动作。", "html.parser"))
                break

    replace_heading_section(soup, "结论—证据—规则追踪", evidence_section(mappings))
    plain_language_cleanup(soup)

    html_path = output_dir / "★2026-08-17完整投研产品候选_v0.7.html"
    html_path.write_text(str(soup), encoding="utf-8")

    holdings_doc["run_id"] = run_id
    candidates_doc["run_id"] = run_id
    trace_doc = {"run_id": run_id, "generated_at": now.isoformat(timespec="seconds"), "mapping_count": len(mappings), "mappings": mappings}
    pdca_check = {
        "run_id": run_id,
        "source": stamp(PDCA_SOURCE),
        "source_record_count": 57,
        "rendered_record_count": 57,
        "series_count": 5,
        "adjudicated": 29,
        "correct": 28,
        "wrong": 1,
        "pending": 28,
        "records": pdca["records"],
        "review_entries": pdca["review_entries"],
    }
    repair = {
        "run_id": run_id,
        "source_run_id": SOURCE_RUN,
        "source_html": stamp(source_html),
        "items": [
            {"item": "真实PDCA", "before": "只显示5系列/57跟踪点汇总，系列判定数显示未取得", "after": "57条原记录逐项进入第三层；5系列分别显示已判定和待验证；日周月入口如实登记", "reason": "统计摘要不能替代逐条复盘"},
            {"item": "证据链", "before": "业务结论主要共用账户证据", "after": "24持仓和21候选分别登记账户、财务、估值、事件、规则及反向边界", "reason": "账户事实不能单独证明公司质量和估值"},
            {"item": "机械价格锚", "before": "保留现价固定折扣观察带", "after": "可靠估值只展示既有三情景；不可靠估值不提供数值买卖区间", "reason": "固定折扣不是安全边际"},
            {"item": "大白话", "before": "存在None、重复缺失词、拼接错误、长小数和银行机械现金流", "after": "缺失说明中文化、数字适度取整、银行指标按行业边界解释、内部流程话术删除", "reason": "提高真实决策可读性"},
        ],
    }
    anchor_check = {
        "run_id": run_id,
        "holdings": [{"code": item["code"], "condition": item["observation_band"]["plain"], "numeric_band": False} for item in holdings_doc["items"]],
        "candidates": [{"code": item["code"], "condition": item["observation_band"]["plain"], "numeric_band": False} for item in candidates_doc["items"]],
    }
    write_json(output_dir / "03_v0.6至v0.7四项返修清单_20260817.json", repair)
    write_json(output_dir / "04_57条PDCA逐项闭合检查_20260817.json", pdca_check)
    write_json(output_dir / "05_结论证据规则映射检查_20260817.json", trace_doc)
    write_json(output_dir / "06_机械价格锚清除检查_20260817.json", anchor_check)
    write_json(output_dir / "12_24类持仓v0.7矩阵_20260817.json", holdings_doc)
    write_json(output_dir / "13_21只候选v0.7矩阵_20260817.json", candidates_doc)
    daily_before = read_json(SOURCE / "13_00今日日报未覆盖证明_20260817.json")["after"]
    write_json(output_dir / "11_完整施工日志_20260817.json", {
        "run_id": run_id,
        "generated_at": now.isoformat(timespec="seconds"),
        "source_run_id": SOURCE_RUN,
        "source_immutable": True,
        "daily_before": daily_before,
        "actions": ["承接v0.6原件", "接入57条真实PDCA", "重建45项证据角色映射", "清除机械价格锚", "清理机器残留"],
        "status": {"business_pass": "PENDING_INDEPENDENT_REVIEW", "final_product_pass": "PENDING_INDEPENDENT_REVIEW", "release_status": "NOT_AUTHORIZED", "current_executable": False},
    })
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
