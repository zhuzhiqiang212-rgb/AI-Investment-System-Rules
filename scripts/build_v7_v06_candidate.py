#!/usr/bin/env python3
"""Build the complete V7 v0.6 candidate from v0.5 and the closed evidence package."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
SOURCE_RUN = "V7-V05-COMPLETE-20260817-080933-JST"
EVIDENCE_RUN = "V7-V05-EVIDENCE-CLOSE-20260817-092935-JST"
SOURCE = ROOT / "output/candidates/2026-08-17" / SOURCE_RUN
EVIDENCE = ROOT / "output/decision_inputs/2026-08-17" / EVIDENCE_RUN
DAILY = ROOT / "00_请先看这里/00_今日日报.pdf"

OVERLAP_CODES = {"US.NVDA", "US.AVGO", "US.TSM", "US.SNDK"}


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


def fragment(markup: str):
    return BeautifulSoup(markup, "html.parser")


def replace_labelled_paragraph(container, label: str, body: str) -> bool:
    for paragraph in container.find_all("p"):
        bold = paragraph.find("b")
        if bold and bold.get_text(strip=True) == label:
            paragraph.clear()
            new_bold = container.new_tag("b")
            new_bold.string = label
            paragraph.append(new_bold)
            paragraph.append(body)
            return True
    return False


def value_text(value: Any, currency: str | None = None) -> str:
    if value is None:
        return "未取得"
    if isinstance(value, float):
        rendered = f"{value:,.4f}".rstrip("0").rstrip(".")
    else:
        rendered = f"{value:,}" if isinstance(value, int) else str(value)
    return f"{currency or ''} {rendered}".strip()


def scenario_table(item: dict[str, Any]) -> str:
    scenarios = item.get("scenarios") or []
    if not scenarios:
        return "<p><b>三情景：</b>无法形成可靠估值，不以现价折扣冒充内在价值。</p>"
    rows = []
    for row in scenarios:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('scenario', '')))}</td>"
            f"<td>{html.escape(value_text(row.get('metric_value')))}</td>"
            f"<td>{html.escape(value_text(row.get('multiple')))}</td>"
            f"<td>{html.escape(value_text(row.get('valuation_per_share'), item.get('currency')))}</td>"
            "</tr>"
        )
    return (
        "<div class='table-wrap compact'><table><thead><tr><th>情景</th><th>盈利/现金流输入</th>"
        "<th>倍数</th><th>机械估值结果</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def valuation_block(item: dict[str, Any], holding: bool) -> str:
    available = item.get("status") != "CANNOT_FORM_RELIABLE_VALUATION"
    metric = item.get("one_year_metric") or {}
    source = item.get("formal_source")
    source_link = f"<a href='{html.escape(source)}'>正式原文</a>" if source else "未取得直接原文"
    if available:
        plain_status = "已有可供总控选择的估值输入，但仍有适用边界"
    else:
        plain_status = "无法形成可靠估值；隔离价格动作和目标贡献"
    gap = item.get("data_gap_impact") or item.get("gap") or "没有新增说明"
    current_price = item.get("current_price")
    price_date = item.get("price_date") or item.get("price_time") or "未取得"
    body = (
        "<div class='valuation-evidence'><h4>v0.6估值证据与动作边界</h4>"
        f"<p><b>当前状态：</b>{html.escape(plain_status)}。</p>"
        f"<p><b>当前价格：</b>{html.escape(value_text(current_price, item.get('currency')))}；数据时间：{html.escape(str(price_date))}。</p>"
        f"<p><b>方法：</b>{html.escape(str(item.get('method') or '资料不足，未采用估值模型'))}。</p>"
        f"<p><b>一年期输入：</b>{html.escape(str(metric.get('name') or '未取得'))} {html.escape(value_text(metric.get('value')))}；"
        f"基础：{html.escape(str(metric.get('basis') or '未取得正式远期指标'))}。</p>"
        + scenario_table(item)
        + f"<p><b>证据缺口和影响：</b>{html.escape(str(gap))}</p>"
        + f"<p><b>来源：</b>{source_link}。</p>"
        + "<p><b>现在怎么办：</b>沿用GPT总控已经批准的持仓或观察结论；上述数字不自动形成订单。</p>"
        + "</div>"
    )
    if not holding:
        body = body.replace("沿用GPT总控已经批准的持仓或观察结论", "保持研究观察池身份，第五关没有自动通过")
    return body


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timestamp", help="JST timestamp YYYYMMDD-HHMMSS")
    args = parser.parse_args()
    now = datetime.now(JST)
    token = args.timestamp or now.strftime("%Y%m%d-%H%M%S")
    run_id = f"V7-V06-COMPLETE-{token}-JST"
    output_dir = ROOT / "output/candidates/2026-08-17" / run_id
    if output_dir.exists():
        raise RuntimeError(f"Output already exists: {output_dir}")
    output_dir.mkdir(parents=True)

    source_html = SOURCE / "★2026-08-17完整投研产品候选_v0.5.html"
    source_pdf = SOURCE / "★2026-08-17完整投研产品候选_v0.5.pdf"
    holdings = read_json(SOURCE / "04_更新后的24类持仓矩阵_20260817.json")
    candidates = read_json(SOURCE / "05_更新后的21只五关轨迹_20260817.json")
    trace = read_json(SOURCE / "08_结论证据规则追踪表_20260817.json")
    samsung = read_json(EVIDENCE / "01_三星财务字段纠错报告_20260817.json")
    audit = read_json(EVIDENCE / "02_45项财务异常复扫矩阵_20260817.json")
    holding_values = read_json(EVIDENCE / "03_24类持仓估值判断输入表_20260817.json")
    candidate_values = read_json(EVIDENCE / "04_21只候选第五关估值输入表_20260817.json")
    ai = read_json(EVIDENCE / "05_AI暴露口径校验表_20260817.json")
    holding_value_by_code = {item["code"]: item for item in holding_values["items"]}
    candidate_value_by_code = {item["code"]: item for item in candidate_values["items"]}
    audit_by_key = {(item["scope"], item["code"]): item for item in audit["items"]}
    holding_by_code = {item["code"]: item for item in holdings["items"]}

    if len(holdings["items"]) != 24 or len(candidates["items"]) != 21 or len(audit["items"]) != 45:
        raise RuntimeError("Expected 24 holdings, 21 candidates, and 45 audit rows")
    if set(holding_value_by_code) != set(holding_by_code):
        raise RuntimeError("Holding valuation input coverage mismatch")

    soup = BeautifulSoup(source_html.read_text(encoding="utf-8"), "html.parser")
    title = "★2026-08-17完整投研产品候选 v0.6"
    soup.title.string = title
    soup.find("h1").string = title
    header = soup.find("header")
    header_meta = header.find("p")
    header_meta.clear()
    header_meta.append(
        f"产品生成日：2026-08-17 JST｜生成时间：{now.isoformat(timespec='seconds')}｜run_id："
    )
    code_tag = soup.new_tag("code")
    code_tag.string = run_id
    header_meta.append(code_tag)

    style = soup.find("style")
    style.append(
        "\n.decision-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:12px 0}"
        ".decision-grid>div,.valuation-evidence,.correction{border:1px solid #b8c4cf;background:#f8fafc;padding:10px 12px;border-radius:6px}"
        ".valuation-evidence h4,.correction h4{margin:0 0 6px;color:#173b57}.compact{font-size:.95em}"
        ".keep-together{break-inside:avoid;page-break-inside:avoid}"
        "@media(max-width:760px){.decision-grid{grid-template-columns:1fr}}"
    )

    layer1 = soup.find("section", id="layer1")
    final_decision = fragment(
        "<section id='v06-control-decision' class='layer-closure'><h3>总控已经给出的今天答案</h3>"
        "<div class='decision-grid'>"
        "<div><b>为什么今天不买</b><p>现金存在不等于必须建仓。21只候选里没有一只在现有价格、盈利证据和同一驱动风险下达到“现在必须买入”。</p></div>"
        "<div><b>继续等待什么</b><p>等待更好的估值、BOJ正式政策、公司财报或盈利预测确认，以及市场回撤带来的更好风险收益比。</p></div>"
        "<div><b>什么时候重新判断</b><p>下一次日本市场收盘、美国市场收盘、BOJ正式决定或重点公司财报发布后；发生显著回撤也立即重算。</p></div>"
        "<div><b>市场继续上涨的代价</b><p>现金会拖累短期相对收益，也可能错过强势股继续上行；这是等待安全垫必须承担的机会成本。</p></div>"
        "<div><b>市场下跌时现金的价值</b><p>现金能避免被迫卖出，并在盈利逻辑未坏但价格回落时提供替换弱持仓或建立更优机会的能力。</p></div>"
        "<div><b>怎样服务年度目标</b><p>＋40%依赖核心盈利兑现、控制同一驱动回撤并在更好价格加入高质量机会；现有证据无法证明靠追高可以达到＋100%。</p></div>"
        "</div><p><b>研究顺序：</b>ETN → CEG → MUFG → TSM → VRT。它是等待触发的研究顺序，不是买入顺序；当前可执行新机会仍为0。</p>"
        "<p><b>日股现金：</b>一千多万日元继续等待，不因现金存在而强行建仓。</p></section>"
    ).section
    first_closure = soup.find("section", id="first-screen-closure")
    first_closure.insert_before(final_decision)

    # Put the denominator boundary next to every first-screen and second-layer exposure number.
    for node in soup.find_all(string=lambda value: value and "AI直接" in value):
        node.replace_with(
            str(node)
            .replace("AI直接", "富途账户AI直接")
            .replace("含软银广义", "富途账户含软银代理后的广义")
        )
    ai_boundary = fragment(
        "<div class='callout risk'><b>AI比例分母：</b>48.147541%和61.475698%都以2026-08-17富途总资产1,162,265.0739美元为分母。"
        "其他账户日期不同，因此不是四账户同日总暴露；它们是风险观察值，不是15%、20%或30%自动交易硬线。</div>"
    ).div
    layer2 = soup.find("section", id="layer2")
    account_heading = next(h for h in layer2.find_all("h3") if h.get_text(strip=True) == "全账户、现金和同一驱动")
    account_heading.insert_after(ai_boundary)

    samsung_currency_heading = next(h for h in soup.find_all("h3") if h.get_text(strip=True) == "Samsung币种分列")
    samsung_currency_table = samsung_currency_heading.find_next_sibling("div", class_="table-wrap")
    samsung_currency_wrapper = soup.new_tag("div")
    samsung_currency_wrapper["class"] = ["keep-together"]
    samsung_currency_heading.insert_before(samsung_currency_wrapper)
    samsung_currency_wrapper.append(samsung_currency_heading.extract())
    samsung_currency_wrapper.append(samsung_currency_table.extract())

    for holding in holdings["items"]:
        code = holding["code"]
        value_input = holding_value_by_code[code]
        audit_row = audit_by_key[("持仓", code)]
        holding["v06_valuation_input"] = value_input
        holding["v06_financial_audit"] = audit_row
        holding["final_answer_source"] = "v0.5 GPT总控结论；v0.6只接入纠错和估值证据"
        detail = soup.find("details", id=f"holding-{code.replace('.', '-')}")
        if detail is None:
            raise RuntimeError(f"Missing holding detail: {code}")
        body = detail.select_one(".asset-body")
        body.append(fragment(valuation_block(value_input, True)).div)
        if value_input["status"] == "CANNOT_FORM_RELIABLE_VALUATION":
            replace_labelled_paragraph(detail, "便宜/合理/偏贵：", "无法形成可靠估值；不以现价乘80%或85%冒充内在价值，不产生价格动作。")

    # Samsung: two periods must coexist and use precise K-IFRS labels.
    samsung_detail = soup.find("details", id="holding-KRX-005930")
    q2 = samsung["periods"]["2026Q2"]
    fy = samsung["periods"]["2025FY"]
    samsung_html = (
        "<div class='correction'><h4>三星电子双期间财务校验</h4>"
        "<p>两组数字都来自K-IFRS合并口径，但期间不同，不能互相替换。合并净利润、归母利润和机械自由现金流分别展示。</p>"
        "<div class='table-wrap'><table><thead><tr><th>期间</th><th>收入</th><th>营业利润</th><th>合并净利润</th><th>归母利润</th><th>经营现金流</th><th>机械自由现金流</th><th>现金口径</th><th>债务</th></tr></thead><tbody>"
        f"<tr><td>2026年第二季度</td><td>{q2['fields']['revenue']['raw']}万亿韩元</td><td>{q2['fields']['operating_profit']['raw']}万亿韩元</td>"
        f"<td>{q2['fields']['net_profit']['raw']}万亿韩元</td><td>{q2['fields']['profit_attributable_to_owners']['raw']}万亿韩元</td>"
        f"<td>{q2['fields']['operating_cash_flow']['raw']}万亿韩元</td><td>{q2['fields']['mechanical_fcf']['raw']}万亿韩元</td>"
        f"<td>{q2['fields']['cash_definition']['raw']}万亿韩元</td><td>{q2['fields']['debts']['raw']}万亿韩元</td></tr>"
        f"<tr><td>2025全年</td><td>{fy['fields']['revenue']['raw']}万亿韩元</td><td>{fy['fields']['operating_profit']['raw']}万亿韩元</td>"
        f"<td>{fy['fields']['net_profit']['raw']}万亿韩元</td><td>官方摘要未在本表另列</td>"
        f"<td>{fy['fields']['operating_cash_flow']['raw']}万亿韩元</td><td>{fy['fields']['mechanical_fcf']['raw']}万亿韩元</td>"
        f"<td>{fy['fields']['cash_definition']['raw']}万亿韩元</td><td>{fy['fields']['debts']['raw']}万亿韩元</td></tr>"
        "</tbody></table></div>"
        f"<p>来源：<a href='{q2['source_url']}'>2026年第二季度官方文件</a>；<a href='{fy['source_url']}'>2025全年官方文件</a>。</p>"
        "<p><b>现在怎么办：</b>旧账户价格只进入最后已知风险；双期间财务用于研究，不产生当日交易动作。</p></div>"
    )
    samsung_detail.select_one(".asset-body").append(fragment(samsung_html).div)

    # Four required isolations.
    sndk_detail = soup.find("details", id="holding-US-SNDK")
    sndk_detail.select_one(".asset-body").append(fragment(
        "<div class='correction'><h4>SNDK动作隔离</h4><p>券商市值继续进入富途账户风险；正式财务已取得，但财务与估值口径仍不足以形成可靠内在价值。"
        "不进入年度目标贡献或加仓判断。券商收益率25.21%与成本计算19.19%的差异继续隔离。</p></div>"
    ).div)
    holding_by_code["US.SNDK"]["target_contribution"] = "EXCLUDED_PENDING_RELIABLE_VALUATION"
    holding_by_code["US.SNDK"]["valuation_judgment"] = "无法形成可靠估值，不产生加仓或目标贡献。"

    advantest = soup.find("details", id="holding-JP-6857")
    advantest.select_one(".asset-body").append(fragment(
        "<div class='correction'><h4>爱德万测试估值冲突</h4><p>不同估值方法给出的结果存在数量级冲突，不能挑一个数冒充唯一内在价值。"
        "当前只保留持仓审查、订单与利润率验证和失效条件，不由此产生交易动作。</p></div>"
    ).div)

    candidate_by_code = {item["code"]: item for item in candidates["items"]}
    for candidate in candidates["items"]:
        code = candidate["code"]
        value_input = candidate_value_by_code[code]
        audit_row = audit_by_key[("候选", code)]
        candidate["v06_valuation_input"] = value_input
        candidate["v06_financial_audit"] = audit_row
        candidate["executable_now"] = False
        candidate["fifth_gate_passed"] = False
        candidate["fifth_gate_plain"] = "第五关未通过；只在研究观察池，当前不产生买入动作。"
        if code in OVERLAP_CODES:
            candidate["final_answer"] = holding_by_code[code]["judgment"]
            candidate["cross_layer_rule"] = "与持仓层共用唯一答案；候选层不得另给新增动作"
        else:
            candidate["final_answer"] = "继续研究观察，当前不新增。"
        detail = soup.find("details", id=f"candidate-{code.replace('.', '-')}")
        if detail is None:
            raise RuntimeError(f"Missing candidate detail: {code}")
        detail.select_one(".asset-body").append(fragment(valuation_block(value_input, False)).div)
        replace_labelled_paragraph(detail, "现在怎么办：", candidate["final_answer"] + "；第五关未通过，当前可执行新机会为0。")

    lite = soup.find("details", id="candidate-US-LITE")
    lite.select_one(".asset-body").append(fragment(
        "<div class='correction'><h4>LITE证据隔离</h4><p>正式结果包含一次性、非现金的债务清偿损失；现金流资料不足，不能用会计利润变化替代现金创造能力。"
        "第五关证据不足，不能通过，也不产生买入动作。</p></div>"
    ).div)
    candidate_by_code["US.LITE"]["fifth_gate_plain"] = "一次性非现金债务清偿损失与现金流不足尚未闭合，第五关不通过。"

    xom = soup.find("details", id="candidate-US-XOM")
    gate2 = xom.select("ol.gates > li")[1]
    gate2.clear()
    gate2.append(fragment(
        "<b>第2关：</b>撤回把税前利润写成营业利润的旧字段；不使用该字段计算利润率或估值。保留收入、净利润、经营现金流及正式文件能够直接支持的字段。"
    ))
    candidate_by_code["US.XOM"]["five_gates"][1]["input"] = "撤回把税前利润写成营业利润的旧字段；不使用该字段计算利润率或估值。"

    # A visible financial correction summary keeps the product readable without exposing raw machine states.
    correction = fragment(
        "<section class='layer-closure'><h3>本轮财务真实性纠错</h3><div class='table-wrap'><table><thead><tr><th>对象</th><th>事实</th><th>对今天动作的限制</th></tr></thead><tbody>"
        "<tr><td>三星电子</td><td>2026年第二季度与2025全年并列，合并净利润、归母利润和机械自由现金流分开。</td><td>旧账户价格不产生交易动作。</td></tr>"
        "<tr><td>SNDK</td><td>券商市值进入风险；可靠内在价值尚不能形成。</td><td>不进目标贡献，不加仓。</td></tr>"
        "<tr><td>LITE</td><td>存在一次性非现金债务清偿损失，现金流不足。</td><td>第五关不通过。</td></tr>"
        "<tr><td>XOM</td><td>撤回把税前利润当营业利润的字段。</td><td>错误字段不用于利润率或估值。</td></tr>"
        "<tr><td>爱德万测试</td><td>估值方法结果存在数量级冲突。</td><td>不选择单一内在价值，不产生动作。</td></tr>"
        "</tbody></table></div></section>"
    ).section
    soup.find("section", id="layer3").insert(1, correction)

    # Add the new evidence package to the conclusion-evidence-rule trace.
    new_trace = [
        {"conclusion_id": "CON-V06-NO-BUY", "conclusion": "当前21只候选均未达到现在必须买入的条件", "evidence_id": "EV-V05-VALUATION-CLOSE", "rule_id": "RULE-RISK-REWARD-FIRST", "source": str(EVIDENCE / "04_21只候选第五关估值输入表_20260817.json"), "boundary": "研究顺序不是买入顺序"},
        {"conclusion_id": "CON-V06-SAMSUNG", "conclusion": "三星2026Q2与2025全年分期并列", "evidence_id": "EV-SAMSUNG-DUAL-PERIOD", "rule_id": "RULE-PERIOD-CONSOLIDATION-UNIT", "source": q2["source_url"] + " | " + fy["source_url"], "boundary": "不得跨期替换"},
        {"conclusion_id": "CON-V06-AI-DENOM", "conclusion": "AI比例仅为富途账户分母", "evidence_id": "EV-FUTU-EXPOSURE", "rule_id": "RULE-SAME-DENOMINATOR", "source": ai["source"], "boundary": ai["boundary"]},
        {"conclusion_id": "CON-V06-ISOLATION", "conclusion": "SNDK、LITE、XOM和爱德万存在明确动作隔离", "evidence_id": "EV-FINANCIAL-AUDIT-45", "rule_id": "RULE-UNKNOWN-ISOLATE-ACTION", "source": str(EVIDENCE / "02_45项财务异常复扫矩阵_20260817.json"), "boundary": "状态不明不自动产生交易"},
    ]
    trace["run_id"] = run_id
    trace["items"].extend(new_trace)

    # Update identity after all DOM edits.
    product = str(soup)
    replacements = {
        "v0.5": "v0.6",
        SOURCE_RUN: run_id,
        "AI直接暴露约48.147541%；加入软银代理暴露约61.475698%。": "富途账户AI直接暴露约48.147541%；加入软银代理后的广义暴露约61.475698%。其他账户日期不同，这不是四账户同日总比例。",
        "用于风险观察，不是固定硬线。": "以富途总资产为分母，用于风险观察，不是四账户同日比例，也不是固定硬线。",
    }
    for old, new in replacements.items():
        product = product.replace(old, new)
    forbidden = [
        "release_status=RELEASED",
        "business_pass=PASS",
        "final_product_pass=PASS",
        "税前利润作为营业利润",
    ]
    bad_hits = [marker for marker in forbidden if marker in product]
    if bad_hits:
        raise RuntimeError(f"Forbidden output text: {bad_hits}")

    html_path = output_dir / "★2026-08-17完整投研产品候选_v0.6.html"
    html_path.write_text(product, encoding="utf-8")

    change_list = {
        "run_id": run_id,
        "source_run_id": SOURCE_RUN,
        "evidence_run_id": EVIDENCE_RUN,
        "items": [
            {"item": "完整产品身份", "before": "v0.5总控退回", "after": "v0.6候选，等待独立复验", "reason": "承接总控最终判断与最新闭合证据"},
            {"item": "三星财务", "before": "仅2026Q2，容易与2025全年混读", "after": "2026Q2与2025全年并列，净利润口径分开", "reason": "避免跨期间、跨字段替换"},
            {"item": "估值", "before": "观察线容易与内在价值混读", "after": "24持仓及21候选接入估值输入；不足者明确不可可靠估值", "reason": "估值输入与动作隔离"},
            {"item": "候选动作", "before": "研究轨迹存在但需要总控最终归口", "after": "21只全部第五关未通过，当前可执行新机会为0", "reason": "落实总控最终组合判断"},
            {"item": "AI暴露", "before": "部分段落未重复写明分母", "after": "全文统一标为富途账户分母", "reason": "避免误读为四账户同日比例"},
            {"item": "四项隔离", "before": "分散在证据附件", "after": "SNDK、LITE、XOM、爱德万限制进入正文", "reason": "状态不明时安全隔离动作"},
        ],
    }
    same_stock = []
    for code in sorted(OVERLAP_CODES):
        same_stock.append({
            "code": code,
            "holding_answer": holding_by_code[code]["judgment"],
            "candidate_answer": candidate_by_code[code]["final_answer"],
            "consistent": holding_by_code[code]["judgment"] == candidate_by_code[code]["final_answer"],
            "boundary": "候选层不得另给新增动作",
        })
    isolation = {
        "run_id": run_id,
        "items": [
            {"code": "US.SNDK", "status": "券商市值计入风险；估值、目标贡献和加仓隔离", "action_generated": False},
            {"code": "US.LITE", "status": "一次性非现金损失和现金流不足；第五关不通过", "action_generated": False},
            {"code": "US.XOM", "status": "错误营业利润字段已撤回；不用于利润率或估值", "action_generated": False},
            {"code": "JP.6857", "status": "估值方法数量级冲突；不选单一内在价值", "action_generated": False},
        ],
    }
    holding_check = {"run_id": run_id, "count": 24, "all_have_unique_answer": all(item.get("judgment") for item in holdings["items"]), "items": holdings["items"]}
    candidate_check = {"run_id": run_id, "count": 21, "executable_count": 0, "fifth_gate_pass_count": 0, "priority": ["US.ETN", "US.CEG", "JP.8306", "US.TSM", "US.VRT"], "items": candidates["items"]}
    ai_check = {**ai, "run_id": run_id, "plain_label_direct": "以本批次富途总资产为分母的AI直接暴露", "plain_label_broad": "以本批次富途总资产为分母、加入软银代理后的广义暴露", "automatic_trade_trigger": False}
    samsung_check = {**samsung, "run_id": run_id, "product_identity": "双期间并列，未跨期替换"}

    write_json(output_dir / "03_v0.5至v0.6变更清单_20260817.json", change_list)
    write_json(output_dir / "04_24类持仓唯一答案检查_20260817.json", holding_check)
    write_json(output_dir / "05_21只候选五关检查_20260817.json", candidate_check)
    write_json(output_dir / "06_同股跨层一致性检查_20260817.json", {"run_id": run_id, "count": len(same_stock), "all_consistent": all(row["consistent"] for row in same_stock), "items": same_stock})
    write_json(output_dir / "07_三星双期间校验_20260817.json", samsung_check)
    write_json(output_dir / "08_SNDK_LITE_XOM_爱德万隔离证明_20260817.json", isolation)
    write_json(output_dir / "09_AI暴露分母校验_20260817.json", ai_check)
    write_json(output_dir / "10_结论证据规则追踪表_20260817.json", trace)

    log = {
        "run_id": run_id,
        "generated_at": now.isoformat(timespec="seconds"),
        "source_v05_html": stamp(source_html),
        "source_v05_pdf": stamp(source_pdf),
        "evidence_inputs": [stamp(path) for path in sorted(EVIDENCE.glob("0[1-5]_*.json"))],
        "daily_before": stamp(DAILY),
        "status": {"business_pass": "PENDING_INDEPENDENT_REVIEW", "final_product_pass": "PENDING_INDEPENDENT_REVIEW", "release_status": "NOT_AUTHORIZED", "current_executable": False},
        "boundaries": {"release_registered": False, "daily_overwritten": False, "trade_functions_called": False, "orders_generated": False, "current_rules_modified": False, "new_research_project_started": False},
    }
    write_json(output_dir / "14_完整施工日志_20260817.json", log)
    print(json.dumps({"run_id": run_id, "output_dir": str(output_dir), "html": stamp(html_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
