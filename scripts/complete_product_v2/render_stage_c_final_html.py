from __future__ import annotations

import argparse
import copy
import hashlib
import html
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
STATUS = {
    "business_pass": "PENDING_INDEPENDENT_FULL_REVIEW",
    "final_product_pass": "PENDING_INDEPENDENT_FULL_REVIEW",
    "release_status": "NOT_AUTHORIZED",
    "current_executable": False,
}

ATTACHMENT_NAMES = {
    "pdca": "01_PDCA历史57条.json",
    "portfolio": "02_唯一账户事实源.json",
    "gates": "03_正式五关矩阵.json",
    "target": "04_目标贡献桥.json",
    "views": "05_外部观点映射.json",
    "capabilities": "06_历史功能数据.json",
    "evidence": "07_证据注册与结论追踪.json",
}

VISIBLE_TERM_MAP = {
    "NON_PRICE_RISK_FRAMEWORK_ONLY": "仅使用非价格风险框架",
    "RISK_PRICE_ANCHOR_ONLY": "仅使用风险价格锚",
    "REJECT_NUMERIC_SCENARIO": "不采用数值情景",
    "NO_NUMERIC_RANGE": "不提供数值区间",
    "NO_NUMERIC_PROBABILITY": "不提供数值概率",
    "GPT总控最终能力判断唯一源": "已批准的唯一投资判断",
    "GPT总控最终能力判断输入": "已批准的投资判断输入",
    "GPT总控最终能力判断": "已批准的投资判断",
    "GPT总控最终参数": "已批准的参数",
    "GPT总控": "已批准判断",
    "Futu OpenD": "富途只读账户接口",
    "OpenD": "富途只读账户接口",
    "Current完整产品与风险边界": "当前正式产品与风险边界",
    "Current规则": "当前正式规则",
    "AI投资系统Current": "AI投资系统当前正式规则",
    "Current": "当前正式规则",
}

VISIBLE_TERM_MAP.update({
    "总控采用": "本期采用",
    "总控分类": "本期按证据状态归类",
    "已批准判断": "本期判断",
    "详见机器附件": "见同批次数据附件",
    "机器附件": "同批次数据附件",
    "机器事实": "批次事实",
    "Futu OpenD get_market_snapshot read-only": "富途只读行情快照",
    "富途只读账户接口 get_market_snapshot read-only": "富途只读行情快照",
    "source title": "来源标题",
    "publisher": "发布机构",
    "source url": "原文链接",
    "retrieved at JST": "日本时间取得时间",
    "selected nearest forward EPS": "最近前瞻每股盈利",
    "historical forward PE reference": "历史前瞻市盈率参考",
    "actual inputs": "实际输入",
    "canonical current quote": "本期唯一行情",
    "price type": "价格类型",
    "SBI_归属未闭合": "SBI账户归属尚未确认",
    "known_assets_total_jpy": "已知资产合计（日元）",
    "总控结论": "本期结论",
    "总控判断形成": "判断形成",
    "唯一账户机器源": "唯一账户事实源",
    "账户机器源": "账户事实源",
    "阶段A同批次机器事实包": "同批次事实包",
    "可用机械财务字段": "已取得的财务字段",
    "机械分数不作投资结论": "这些字段只说明财务事实，不直接形成投资结论",
    "八项重点机会已完成总控排序": "八项重点机会已有研究顺序",
    "Codex直连未成功": "当前执行环境未直接读取Reuters全文",
    "Codex本轮直连失败": "当前执行环境未直接读取Reuters全文",
    "总控答案": "本期估值结论",
    "经总控批准的": "本期采用的",
    "总控核验": "独立核验",
    "机器实物路径": "同批次数据附件",
    "机器字典": "程序字段",
})
GUIDANCE_EVIDENCE_OVERRIDES = {
    "JP.9984": {
        "source_title": "SoftBank Group Q1 FY2026 Earnings Results and NAV per Share",
        "publisher": "SoftBank Group Corp.",
        "published_at": "2026-08-06",
        "period": "截至2026-06-30的2026财年第一季度；NAV数据截至2026-06-30",
        "url": "https://group.softbank/en/ir",
        "locator": "Q1 FY2026 Earnings Results；Net Asset Value per Share；NAV 72.30万亿日元、持股价值83.11万亿日元、净债务10.81万亿日元、LTV 13.0%",
        "date_impact": "正式发布日和数据期均已明确；不据此证明8月21日的实时NAV。",
    },
    "KRX.005930": {
        "source_title": "Samsung Electronics Announces Second Quarter 2026 Results",
        "publisher": "Samsung Electronics",
        "published_at": "2026-07-30",
        "period": "截至2026-06-30的第二季度",
        "url": "https://news.samsung.com/global/samsung-electronics-announces-second-quarter-2026-results",
        "locator": "开头的季度合并收入、营业利润及H2 2026各业务展望",
        "date_impact": "精确发布日期与报告期已闭合。",
    },
    "US.IBKR": {
        "source_title": "Interactive Brokers Group Announces 2Q 2026 Results",
        "publisher": "Interactive Brokers Group, Inc.",
        "published_at": "2026-07-21",
        "period": "截至2026-06-30的第二季度",
        "url": "https://www.sec.gov/Archives/edgar/data/1381197/000138119726000147/ibkr-20260630.htm",
        "locator": "Form 10-Q：Consolidated Statements of Financial Condition、Income及Management's Discussion and Analysis",
        "date_impact": "使用SEC直达申报文件，不使用投资者关系首页替代财务原文。",
    },
    "US.SNDK": {
        "source_title": "Sandisk Reports Fiscal Fourth Quarter 2026 Financial Results",
        "publisher": "Sandisk Corporation",
        "published_at": "2026-08-05",
        "period": "截至2026-07-03的2026财年第四季度；指引为2027财年第一季度",
        "url": "https://investor.sandisk.com/news-releases/news-release-details/sandisk-reports-fiscal-fourth-quarter-2026-financial-results",
        "locator": "News Summary、Q4 2026 Financial Highlights及Business Outlook for Q1 2027",
        "date_impact": "精确发布日期、报告期及前瞻指引期间均已闭合。",
    },
    "US.SPCX": {
        "source_title": "Space Exploration Technologies Corp. Form 8-K",
        "publisher": "U.S. Securities and Exchange Commission",
        "published_at": "2026-06-15",
        "period": "最早事件日2026-06-15；上市承销事项",
        "url": "https://www.sec.gov/Archives/edgar/data/1181412/000162828026043288/spaceexplorationtechnologi.htm",
        "locator": "Form 8-K封面、Item 8.01 Other Events及Exhibit 1.1 Underwriting Agreement",
        "date_impact": "该文件证明证券与上市承销事项，不提供传统经营指引，也不能单独形成数值估值。",
    },
    "US.TSM": {
        "source_title": "TSMC Second Quarter 2026 Earnings Call and Third Quarter Outlook",
        "publisher": "Taiwan Semiconductor Manufacturing Co., Ltd.",
        "published_at": "2026-07-16",
        "period": "2026年第二季度结果；2026年第三季度指引",
        "url": "https://investor.tsmc.com/english/quarterly-results/2026/q2",
        "locator": "Q2 2026 earnings materials：Business Outlook，Q3收入44.6至45.8十亿美元及毛利率指引",
        "date_impact": "精确发布日期与指引期间已闭合。",
    },
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def humanize_visible_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: humanize_visible_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [humanize_visible_value(item) for item in value]
    if isinstance(value, str):
        result = value
        for source, replacement in VISIBLE_TERM_MAP.items():
            result = result.replace(source, replacement)
        return result
    return value


def format_account_locator(quantity_by_account: Any) -> str:
    if not isinstance(quantity_by_account, dict) or not quantity_by_account:
        return "账户归属未闭合；数量未单独登记"
    parts = []
    for account, value in quantity_by_account.items():
        if isinstance(value, dict):
            amount = value.get("quantity", value.get("shares", value.get("amount", "未登记")))
            date = value.get("data_date") or value.get("date") or value.get("as_of")
            part = f"{account}：数量{amount}"
            if date:
                part += f"，资料日期{date}"
        else:
            part = f"{account}：数量{value}"
        parts.append(part)
    return "；".join(parts)


def apply_guidance_override(symbol: str, guidance: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(guidance)
    override = GUIDANCE_EVIDENCE_OVERRIDES.get(symbol)
    if override:
        result.update(override)
    return result


def meaningful_evidence_title(fact: dict[str, Any]) -> str:
    title = str(fact.get("title") or "").strip()
    if title and "机器事实" not in title and "机器实物" not in title:
        return title
    fact_text = str(fact.get("fact") or "").strip()
    if fact_text:
        return fact_text[:42] + ("…" if len(fact_text) > 42 else "")
    return "同批次事实登记"


def write_core_attachments(model: dict[str, Any], output_dir: Path) -> list[dict[str, Any]]:
    payloads = {
        ATTACHMENT_NAMES["pdca"]: {
            "run_id": model["run_id"],
            "purpose": "保存57条PDCA历史记录及本期大白话汇总，供逐条复核。",
            "record_count": len(model["pdca"].get("plain_records", [])),
            "data": model["pdca"],
        },
        ATTACHMENT_NAMES["portfolio"]: {
            "run_id": model["run_id"],
            "purpose": "保存唯一账户事实源、跨账户合并、已知资产和未知字段。",
            "data": model["single_portfolio_source"],
        },
        ATTACHMENT_NAMES["gates"]: {
            "run_id": model["run_id"],
            "purpose": "保存18个研究对象共90行正式五关记录。",
            "object_count": len(model["research_gates"]),
            "gate_row_count": sum(len(item.get("gates", [])) for item in model["research_gates"]),
            "data": model["research_gates"],
        },
        ATTACHMENT_NAMES["target"]: {
            "run_id": model["run_id"],
            "purpose": "保存24项资产的收益、概率、权重和组合贡献桥。",
            "data": model["target_bridge"],
        },
        ATTACHMENT_NAMES["views"]: {
            "run_id": model["run_id"],
            "purpose": "保存湖水、老雷及其他外部观点对具体判断的影响映射。",
            "data": model["external_views"],
        },
        ATTACHMENT_NAMES["capabilities"]: {
            "run_id": model["run_id"],
            "purpose": "保存替换发动机、影子组合、风险穿透、确定性积累和问题台账。",
            "data": model["capabilities"],
        },
        ATTACHMENT_NAMES["evidence"]: {
            "run_id": model["run_id"],
            "purpose": "保存七层、新闻、结论追踪及事件取舍的完整证据登记。",
            "layers": model["layers"],
            "news": model["news"],
            "traceability": model["traceability"],
            "accepted_event_leads": model.get("accepted_event_leads", []),
            "rejected_irrelevant_events": model.get("rejected_irrelevant_events", []),
        },
    }
    rows = []
    for filename, payload in payloads.items():
        path = output_dir / filename
        write_json(path, payload)
        rows.append({
            "name": filename,
            "purpose": payload["purpose"],
            "size": path.stat().st_size,
            "sha256": sha256(path),
            "relative_href": filename,
        })
    return rows


def render_attachment_table(rows: list[dict[str, Any]]) -> str:
    body = "".join(
        "<tr>"
        f"<td><a href=\"{html.escape(row['relative_href'], quote=True)}\">{html.escape(row['name'])}</a></td>"
        f"<td>{html.escape(row['purpose'])}</td><td>{row['size']:,}字节</td>"
        f"<td><code>{row['sha256']}</code></td></tr>"
        for row in rows
    )
    return (
        "<h3>同批次完整附件</h3>"
        "<p>下列附件均已真实生成，可从本页直接打开；目录、大小和哈希与本表逐项一致。</p>"
        "<table data-attachment-table=\"1\"><thead><tr><th>附件</th><th>用途</th><th>大小</th><th>SHA256</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def source_link_or_attachment(url: Any, base: Any) -> str:
    if isinstance(url, str) and url.startswith(("https://", "http://")):
        return base.link(url)
    filename = ATTACHMENT_NAMES["evidence"]
    return f'<a href="{base.esc(filename)}">打开同批次证据附件</a>'


def render_layer_fact_list(facts: list[dict[str, Any]], base: Any) -> str:
    rows = []
    for fact in facts:
        rows.append(
            f'<li><b>{base.esc(meaningful_evidence_title(fact))}</b>｜{base.esc(fact.get("publisher") or "同批次事实登记")}<br>'
            f'发布时间：{base.esc(fact.get("published_at") or "未单独披露")}｜数据期间：{base.esc(fact.get("data_period") or "本批次")}<br>'
            f'事实：{base.esc(fact.get("fact"))}<br>传到组合：{base.esc(fact.get("supports"))}<br>'
            f'不能证明：{base.esc(fact.get("cannot_prove"))}<br>{source_link_or_attachment(fact.get("url"), base)}</li>'
        )
    return "<ul>" + "".join(rows) + "</ul>"


def render_news(news: dict[str, Any], base: Any) -> str:
    rows = []
    for item in news["records"]:
        rows.append(
            f'<tr><td>{base.esc(meaningful_evidence_title(item))}<br><small>{base.esc(item.get("publisher") or "同批次新闻登记")}</small></td>'
            f'<td>{base.esc(item.get("published_at"))}<br>{base.esc(item.get("data_date"))}</td>'
            f'<td>{base.esc(item.get("fact"))}</td><td>{base.esc(item.get("portfolio_impact"))}</td>'
            f'<td>{base.esc(item.get("boundary"))}</td><td>{source_link_or_attachment(item.get("url"), base)}</td></tr>'
        )
    return (
        f'<p>检索开始：{base.esc(news.get("search_started_at_jst"))}｜结束：{base.esc(news.get("search_finished_at_jst"))}'
        f'｜事实截止：{base.esc(news.get("evidence_cutoff_jst"))}</p>'
        '<table><thead><tr><th>事件</th><th>发布时间／数据日</th><th>事实</th><th>组合影响</th>'
        f'<th>使用边界</th><th>原文</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'
    )


def build_evidence_url_index(model: dict[str, Any]) -> dict[str, str]:
    index: dict[str, str] = {}
    for layer in model.get("layers", []):
        for fact in layer.get("facts", []):
            url = fact.get("url")
            if isinstance(url, str) and url.startswith(("https://", "http://")):
                index[str(fact.get("title") or "")] = url
                index[meaningful_evidence_title(fact)] = url
    for item in model.get("news", {}).get("records", []):
        url = item.get("url")
        if isinstance(url, str) and url.startswith(("https://", "http://")):
            index[str(item.get("title") or "")] = url
    for holding in model.get("holdings", []):
        for role in holding.get("precise_evidence_roles", []):
            url = role.get("url")
            if isinstance(url, str) and url.startswith(("https://", "http://")):
                index[str(role.get("title") or "")] = url
    for item in model.get("research_gates", []):
        for gate in item.get("gates", []):
            source = gate.get("source") if isinstance(gate.get("source"), dict) else {}
            url = source.get("url")
            if isinstance(url, str) and url.startswith(("https://", "http://")):
                index[str(source.get("title") or "")] = url
    return index


def render_trace(rows: list[dict[str, Any]], model: dict[str, Any], base: Any) -> str:
    url_index = build_evidence_url_index(model)
    rendered = []
    for row in rows:
        evidence_items = []
        for value in row.get("evidence", []):
            if not value:
                continue
            title = meaningful_evidence_title({"title": value, "fact": value})
            url = url_index.get(str(value)) or url_index.get(title)
            href = base.link(url) if url else f'<a href="{base.esc(ATTACHMENT_NAMES["evidence"])}">同批次登记：{base.esc(title)}</a>'
            evidence_items.append(f"<li>{href}</li>")
        rendered.append(
            "<tr>"
            f"<td>{base.esc(row.get('conclusion'))}</td><td>{base.esc(row.get('plain_answer'))}</td>"
            f"<td><ul>{''.join(evidence_items)}</ul></td><td>{base.esc(row.get('rule'))}</td>"
            f"<td>{base.esc(row.get('boundary'))}</td></tr>"
        )
    return (
        "<table><thead><tr><th>结论</th><th>唯一答案</th><th>可打开证据</th><th>规则</th><th>边界／改判</th></tr></thead>"
        f"<tbody>{''.join(rendered)}</tbody></table>"
    )


def load_base_module(path: Path):
    module_name = "scripts.complete_product_v2.render_stage_c_rebuild"
    project_root = str(path.resolve().parents[2])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load renderer: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def numeric_judgment_map(final: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["symbol"]: row for row in final["numeric_holding_judgments"]}


def risk_judgment_map(final: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["symbol"]: row for row in final["risk_framework_holding_judgments"]}


def capability_holding_map(capability: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["symbol"]: row for row in capability["holdings_24"]}


def probability_text(probabilities: dict[str, int]) -> str:
    return (
        f"悲观{probabilities['bear']}%／基准{probabilities['base']}%／"
        f"乐观{probabilities['bull']}%"
    )


def scenario_summary(capability_row: dict[str, Any]) -> str:
    pricing = capability_row["valuation_or_risk_pricing"]
    values = pricing["scenario_values"]
    currency = pricing.get("currency") or "原报价币种"
    return (
        f"条件情景价格：悲观{values['bear']:,.2f}、基准{values['base']:,.2f}、"
        f"乐观{values['bull']:,.2f}（{currency}）。公式和算术可复算，参数是条件情景，"
        "不是收益承诺或自动交易线。"
    )


def guidance_summary(guidance: dict[str, Any]) -> str:
    facts = "；".join(str(value) for value in guidance.get("facts", []) if value)
    status = guidance.get("plain_status") or "公司指引状态未登记"
    period = guidance.get("period") or "期间未登记"
    return f"{status}。期间：{period}。{facts}".strip("。") + "。"


def quality_explanation(symbol: str) -> str:
    if symbol in {"BTC", "ETH"}:
        return "该资产不是经营公司，企业收入、利润率和企业现金流指标不适用；本期改看协议、使用、流动性、交易结构和监管风险。"
    if symbol in {"JP.8766", "US.IBKR"}:
        return "金融机构不宜用普通制造业自由现金流机械比较；本期重点看净资产、资本回报、承保或净息差、资本充足与股东回报。"
    if symbol == "JP.9984":
        return "控股公司优先看持股资产价值、净债务、每股净资产价值和负债价值比；普通经营利润率只作补充。"
    if symbol in {"US.MSTR", "US.SPCX"}:
        return "资产与资本结构决定风险，普通利润率不能单独解释价值；本期重点看资产价值、债务、稀释、融资能力和流动性。"
    if symbol in {"KRX.005930", "US.SNDK", "JP.4063", "JP.6857", "JP.6954", "US.NVDA", "US.AVGO", "US.TSM"}:
        return "周期与资本开支会放大单期数字；机械比率只用于勾稽，还要结合订单、售价、毛利率、产能和中周期现金流。"
    return "机械比率只用于勾稽正式财务，不能单独替代公司指引、估值依据、竞争判断和反向证据。"


def first_url(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("source_url", "url", "source"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.startswith(("https://", "http://")):
                return candidate
        for child in value.values():
            candidate = first_url(child)
            if candidate:
                return candidate
    elif isinstance(value, list):
        for child in value:
            candidate = first_url(child)
            if candidate:
                return candidate
    return None


def precise_evidence_roles(item: dict[str, Any], cap: dict[str, Any], numeric: bool) -> list[dict[str, Any]]:
    financial = cap["latest_formal_financial"]
    guidance = cap["company_guidance"]
    reverse = cap["reverse_evidence"]
    event = cap.get("company_or_industry_event")
    forward = item["valuation"].get("forward_input")
    account_names = "、".join(cap.get("quantity_by_account", {}).keys()) or "账户归属未闭合"
    roles = [{
        "role": "账户事实", "status": "已取得本批次账户实物", "title": f"{item['name']}账户数量与已知市值",
        "publisher": "Futu OpenD及已确认账户实物", "published_at": item["account_fact"].get("data_boundary"),
        "period": "各账户按原始实物日期分别登记", "locator": f"账户：{account_names}；{format_account_locator(item['account_fact'].get('quantity_by_account'))}",
        "url": None, "supports": "证明本批次已知账户中的数量、已知市值和权重分母。", "cannot_prove": "不能证明未知账户字段、完整同日净值或交易历史。",
    }]
    if item["asset_id"] in {"BTC", "ETH"}:
        roles.append({
            "role": "财务事实", "status": "不适用企业财务口径", "title": "非企业资产，不套用企业三张报表", "publisher": "不适用",
            "published_at": "不适用", "period": "不适用", "locator": "无企业利润表、资产负债表或现金流量表", "url": None,
            "supports": "说明企业财务指标不适用。", "cannot_prove": "不能据此证明价格、流动性或收益前景。",
        })
    else:
        roles.append({
            "role": "财务事实", "status": "已取得正式财务原文", "title": financial.get("source_title"), "publisher": financial.get("publisher"),
            "published_at": financial.get("precise_locator", {}).get("published_at") or "发布日期见原文", "period": financial.get("financial_period"),
            "locator": financial.get("precise_locator"), "url": financial.get("source_url"), "supports": "证明所列财务期间、合并口径和正式财务字段。",
            "cannot_prove": "不能单独证明当前市场价格、合理倍数或当期公司事件。",
        })
    roles.append({
        "role": "公司指引或替代指引", "status": guidance.get("plain_status"), "title": guidance.get("source_title"), "publisher": guidance.get("publisher"),
        "published_at": guidance.get("published_at"), "period": guidance.get("period"), "locator": guidance.get("locator"), "url": guidance.get("url"),
        "supports": "；".join(guidance.get("facts", [])), "cannot_prove": "公司或协议资料不能单独证明当前市场价格，也不构成自动交易线。",
    })
    roles.append({
        "role": "估值输入", "status": "已取得可复算外部输入" if numeric else "本期不采用数值估值",
        "title": (forward or {}).get("source_title") if isinstance(forward, dict) else "非价格风险框架",
        "publisher": (forward or {}).get("publisher") if isinstance(forward, dict) else "GPT总控最终能力判断",
        "published_at": (forward or {}).get("retrieved_at_jst") if isinstance(forward, dict) else "本批次判断形成时间",
        "period": str((forward or {}).get("selected_nearest_forward_eps", {}).get("period") or "不适用") if isinstance(forward, dict) else "不适用",
        "locator": "前瞻输入、情景参数和公式" if numeric else "只保留风险、触发条件和动作边界", "url": first_url(forward),
        "supports": "支持已批准条件情景的机械复算。" if numeric else "说明为什么本期不能给出可靠数值估值。",
        "cannot_prove": "条件情景不是历史合理价值，也不单独支持加减仓。" if numeric else "不证明内在价值、目标价或收益概率。",
    })
    if isinstance(event, dict) and first_url(event):
        roles.append({
            "role": "公司或行业事件", "status": "已取得本批次事件原文", "title": event.get("title"), "publisher": event.get("publisher") or event.get("source_name"),
            "published_at": event.get("published_at") or event.get("source_date"), "period": event.get("data_period") or "本批次事实截止前",
            "locator": event.get("locator") or event.get("section"), "url": first_url(event), "supports": event.get("supports") or event.get("impact"),
            "cannot_prove": event.get("cannot_prove") or "单一事件不能独立证明估值或交易动作。",
        })
    else:
        roles.append({
            "role": "公司或行业事件", "status": "限定范围内未取得独立公司级新事件", "title": "本批次事件检索结果",
            "publisher": "生产批次新闻与事件账本", "published_at": "截至统一事实截止时间", "period": "本批次", "locator": "没有用财报或宏观新闻占位",
            "url": None, "supports": "只证明限定检索范围内没有取得可独立使用的新公司事件。", "cannot_prove": "不能写成市场上没有发生事件，也不能支持估值或动作。",
        })
    roles.append({
        "role": "反向证据", "status": "已取得反向证据", "title": reverse.get("section"), "publisher": reverse.get("publisher"),
        "published_at": reverse.get("source_date"), "period": reverse.get("source_date"), "locator": reverse.get("section"), "url": first_url(reverse),
        "supports": reverse.get("opposes"), "cannot_prove": reverse.get("role_boundary"),
    })
    roles.append({
        "role": "Current规则", "status": "已取得正式规则", "title": "Current完整产品与风险边界", "publisher": "AI投资系统Current",
        "published_at": "当前有效版本", "period": "本批次", "locator": "Current启动包、总则、蓝图与正式五关", "url": None,
        "supports": "证明不机械使用15%、20%或未经确认的30%硬线，并保持候选、非Release和无订单边界。",
        "cannot_prove": "规则定义动作边界，不证明公司财务、市场价格或投资收益。",
    })
    return roles

def merge_holdings(
    old_holdings: list[dict[str, Any]], capability: dict[str, Any], final: dict[str, Any]
) -> list[dict[str, Any]]:
    capability_map = capability_holding_map(capability)
    numeric_map = numeric_judgment_map(final)
    risk_map = risk_judgment_map(final)
    merged: list[dict[str, Any]] = []
    for source in old_holdings:
        item = copy.deepcopy(source)
        symbol = item["asset_id"]
        cap = copy.deepcopy(capability_map[symbol])
        cap["company_guidance"] = apply_guidance_override(symbol, cap["company_guidance"])
        item["account_fact"]["known_market_value_jpy"] = cap["market_value_jpy"]
        item["account_fact"]["weight_of_known_assets_pct"] = cap["known_asset_weight_pct"]
        item["account_fact"]["quantity_by_account"] = cap["quantity_by_account"]
        account_names = "、".join(cap["quantity_by_account"].keys()) or "账户归属未闭合"
        item["account_fact"]["data_boundary"] = (
            f"账户数据边界：本卡数量来自{account_names}的最后有效实物；各账户原始日期见全账户表。"
            "只用于已知资产风险，不代表四账户同日完整净值。"
        )
        item["valuation"]["current_price"] = cap["current_price"].get("value")
        item["valuation"]["current_price_time"] = cap["current_price"].get("time")
        item["valuation"]["current_price_source"] = cap["current_price"].get("source")
        item["financial"]["guidance"] = guidance_summary(cap["company_guidance"])
        item["financial"]["guidance_evidence"] = copy.deepcopy(cap["company_guidance"])
        item["financial"]["guidance_evidence"]["reverse_impact"] = cap["reverse_evidence"].get("opposes")
        item["financial"]["guidance_evidence"]["update_condition"] = cap.get("update_condition")
        item["financial"]["quality"]["industry_explanation"] = quality_explanation(symbol)
        item["financial"]["quality"]["summary"] = (
            f"{item['financial']['quality'].get('summary', '')} {quality_explanation(symbol)}"
        ).strip()
        item["company_guidance_capability"] = cap["company_guidance"]
        item["current_reverse_evidence_capability"] = cap["reverse_evidence"]
        item["forecast"]["medium_term"] = re.sub(
            r"[，,]?(?:主逻辑成立)?概率约\d+(?:\.\d+)?%[。.]?", "。", item["forecast"].get("medium_term", "")
        ).replace("。。", "。").strip()
        if isinstance(item["valuation"].get("formula"), dict):
            item["valuation"]["formula"].pop("missing_for_final", None)
        item["valuation"]["missing"] = [
            value for value in item["valuation"].get("missing", [])
            if value != "GPT总控最终参数及情景权重"
        ]

        if symbol in numeric_map:
            judgment = numeric_map[symbol]
            probs = judgment["probability_pct"]
            item["valuation"]["final_control_answer"] = scenario_summary(cap)
            item["valuation"]["price_boundary"] = (
                "条件情景只用于检验盈利和估值变化；不单独支持加仓、减仓或目标承诺。"
            )
            item["valuation"]["missing"] = []
            item["valuation"]["missing_plain"] = "本期总控参数、情景权重与动作边界已裁定；没有仍待总控填写的参数。"
            if isinstance(item["valuation"].get("formula"), dict):
                item["valuation"]["formula"].pop("missing_for_final", None)
            item["forecast"]["control_confidence"] = probability_text(probs)
            item["forecast"]["confidence_boundary"] = final["probability_method"]["meaning"]
            item["action"]["unique_action"] = judgment["final_action_boundary"]
            item["action"]["reason"] = (
                f"总控采用条件情景并给出{probability_text(probs)}；"
                f"该资产对已知资产目标桥的概率加权贡献为"
                f"{judgment['expected_contribution_pp']:+.6f}个百分点。"
            )
            item["action"]["replacement"] = judgment["replacement_if_any"]
            item["action"]["target_contribution"] = (
                f"纳入可复算目标桥：{judgment['expected_contribution_pp']:+.6f}个百分点。"
            )
            item["final_capability_judgment"] = judgment
        else:
            judgment = risk_map[symbol]
            item["valuation"]["final_control_answer"] = (
                "本期不采用数值情景；只保留经总控批准的风险定价框架和验证条件。"
            )
            item["valuation"]["price_boundary"] = (
                "不提供伪精确收益区间、成功概率或目标贡献；不以估值支持新增动作。"
            )
            item["valuation"]["missing_plain"] = "本期不采用数值估值；未闭合输入按风险框架隔离，不进入目标贡献。"
            item["forecast"]["control_confidence"] = "不填伪精确概率"
            item["forecast"]["confidence_boundary"] = final["probability_method"]["risk_only_rule"]
            item["action"]["unique_action"] = judgment["final_action_boundary"]
            item["action"]["reason"] = (
                f"总控分类为{judgment['scenario_adoption']}；没有获批的数值情景，"
                "因此不进入数值目标贡献。"
            )
            item["action"]["replacement"] = judgment["replacement_if_any"]
            item["action"]["target_contribution"] = (
                "退出可复算目标桥；这里的退出不等于预期收益为0。"
            )
            item["final_capability_judgment"] = judgment
        item["precise_evidence_roles"] = precise_evidence_roles(item, cap, symbol in numeric_map)
        item.pop("evidence_roles", None)
        merged.append(item)
    return merged


def merge_research(
    old_research: list[dict[str, Any]], capability: dict[str, Any], final: dict[str, Any]
) -> list[dict[str, Any]]:
    opportunity_input = {row["symbol"]: row for row in capability["priority_opportunity_gates"]}
    judgments = {row["symbol"]: row for row in final["priority_opportunity_judgments"]}
    merged: list[dict[str, Any]] = []
    for source in old_research:
        item = copy.deepcopy(source)
        symbol = item["asset_id"]
        if symbol in judgments:
            decision = judgments[symbol]
            gate_input = opportunity_input[symbol]
            item["identity"] = f"研究优先级第{decision['rank']}；第五关未通过；当前不可执行。"
            item["retain_or_drop"] = "继续研究，不升级为可执行机会"
            item["valuation_or_risk_pricing"] = gate_input["gate_4_valuation_or_risk_pricing"]["conclusion_input"]
            item["replacement_target"] = decision["replacement"]
            item["executable_condition"] = decision["trigger"]
            item["next_review"] = gate_input["next_verification"]
            item["executable"] = False
            item["final_opportunity_judgment"] = decision
            gate5 = next(row for row in item["gates"] if row["gate"] == 5)
            gate5["status"] = "第五关未通过，继续研究"
            gate5["fact"] = (
                f"当前不值得替换现金或现有持仓。比较对象：{decision['replacement']}。"
                f"重新审查条件：{decision['trigger']}。失效条件：{decision['invalidation']}。"
            )
            gate5["missing"] = [
                "尚未同时闭合可复算风险收益、替换优势和正式执行条件。"
            ]
            gate5["evidence_complete"] = False
            item["formal_gate_stop"] = (
                f"第五关未通过；当前最大允许新增权重为{decision['max_weight_pct']}%。"
            )
        for gate in item["gates"]:
            gate["fact"] = str(gate.get("fact") or "").replace("本轮最终动作以总控唯一答案为准", "").replace("。。", "。").strip()
            source = gate.get("source") if isinstance(gate.get("source"), dict) else {}
            if gate.get("gate") == 4:
                obtained = f"已取得公司特定证据：{source.get('title')}。" if source.get("title") else "本关没有取得可定位的公司特定正式原文。"
                gate["fact"] = (
                    f"{gate['fact'].rstrip('。')}。{obtained}"
                    f"下一次验证：{item.get('next_review') or item.get('executable_condition') or '下一份正式财报或公司公告'}。"
                )
            clickable = bool(source.get("title")) and str(source.get("url", "")).startswith(("https://", "http://"))
            claimed_complete = "已取得" in str(gate.get("status", "")) or "已完成" in str(gate.get("status", ""))
            if (claimed_complete or gate.get("evidence_complete")) and clickable:
                gate["missing"] = []
                gate["evidence_complete"] = True
            elif claimed_complete and not clickable:
                gate["status"] = "本关证据未闭合，停止在本关"
                gate["evidence_complete"] = False
                gate["missing"] = ["缺少可点击的正式原文，不能把本关标为已完成。"]
            elif gate.get("evidence_complete") and not clickable:
                gate["evidence_complete"] = False
                gate["missing"] = gate.get("missing") or ["缺少可点击的正式原文。"]
        item["executable"] = False
        merged.append(item)
    return merged


def build_target_bridge(
    capability: dict[str, Any], final: dict[str, Any]
) -> dict[str, Any]:
    cap_map = capability_holding_map(capability)
    numeric_map = numeric_judgment_map(final)
    risk_map = risk_judgment_map(final)
    portfolio = final["portfolio_judgment"]
    input_bridge = capability["target_contribution_bridge"]
    asset_rows: list[dict[str, Any]] = []
    for symbol, cap in cap_map.items():
        pricing = cap["valuation_or_risk_pricing"]
        if symbol in numeric_map:
            judgment = numeric_map[symbol]
            returns = pricing["scenario_returns"]
            probs = judgment["probability_pct"]
            asset_rows.append(
                {
                    "asset_id": symbol,
                    "name": cap["name"],
                    "known_weight_pct": cap["known_asset_weight_pct"],
                    "bear_return_pct": returns["bear"] * 100,
                    "base_return_pct": returns["base"] * 100,
                    "bull_return_pct": returns["bull"] * 100,
                    "probability": probability_text(probs),
                    "probability_weighted_contribution_pp": judgment["expected_contribution_pp"],
                    "status": "纳入可复算目标贡献桥",
                    "missing": "无；但概率是总控主观条件概率，不是历史频率。",
                }
            )
        else:
            judgment = risk_map[symbol]
            asset_rows.append(
                {
                    "asset_id": symbol,
                    "name": cap["name"],
                    "known_weight_pct": cap["known_asset_weight_pct"],
                    "bear_return_pct": None,
                    "base_return_pct": None,
                    "bull_return_pct": None,
                    "probability": "不填伪精确概率",
                    "probability_weighted_contribution_pp": None,
                    "status": "不进入数值目标贡献桥",
                    "missing": (
                        f"{judgment['scenario_adoption']}；只保留风险框架。"
                        "退出数值桥不表示预期收益为0。"
                    ),
                }
            )

    return {
        "boundary": portfolio["baseline_boundary"],
        "known_assets_jpy": portfolio["baseline_jpy"],
        "plus_40_observation_target_jpy": input_bridge["targets"]["plus_40_end_value_jpy"],
        "plus_40_gap_jpy": round(portfolio["baseline_jpy"] * 0.40, 2),
        "plus_100_observation_target_jpy": input_bridge["targets"]["plus_100_end_value_jpy"],
        "plus_100_gap_jpy": round(portfolio["baseline_jpy"] * 1.00, 2),
        "account_forward_baselines": {},
        "asset_rows": asset_rows,
        "quantified_asset_count": len(numeric_map),
        "quantified_weight_pct": portfolio["numeric_scenario_coverage_pct"],
        "unquantified_weight_pct": round(100 - portfolio["numeric_scenario_coverage_pct"], 6),
        "probability_weighted_contribution_pp": portfolio["numeric_scenario_probability_weighted_contribution_pp"],
        "plus_40_remaining_gap_pp": portfolio["plus40_feasibility"]["remaining_gap_pp"],
        "plus_100_remaining_gap_pp": portfolio["plus100_feasibility"]["remaining_gap_pp"],
        "plus_40_status": portfolio["plus40_feasibility"]["judgment"],
        "plus_100_status": portfolio["plus100_feasibility"]["judgment"],
        "cash_role": portfolio["cash_role"],
        "cash_assumption_boundary": portfolio["cash_assumption_boundary"],
        "risk_only_boundary": portfolio["risk_only_assets_assumption_boundary"],
        "required_change_plus40": portfolio["plus40_feasibility"]["required_change"],
        "required_change_plus100": portfolio["plus100_feasibility"]["required_change"],
        "next_review": portfolio["next_review"],
        "monthly_milestones": input_bridge["targets"]["monthly_milestones"],
    }


def render_target_bridge(target: dict[str, Any], base: Any) -> str:
    rows = []
    for row in target["asset_rows"]:
        rows.append(
            f'<tr data-target-row="{base.esc(row["asset_id"])}"><td>{base.esc(row["asset_id"])}</td>'
            f'<td>{base.esc(row["name"])}</td><td>{row["known_weight_pct"]:.2f}%</td>'
            '<td>本期不提供</td><td>本期不提供</td>'
            f'<td>{base.esc(row["status"])}</td><td>{base.esc(row["missing"])}</td></tr>'
        )
    milestone_rows = "".join(
        f"<tr><td>{base.esc(row['date'])}</td><td>¥{base.fmt_num(row['plus_40_path_jpy'])}</td>"
        f"<td>¥{base.fmt_num(row['plus_100_path_jpy'])}</td><td>{base.esc(row['boundary'])}</td></tr>"
        for row in target["monthly_milestones"]
    )
    return f"""
    <div class="target-bars"><div><b>已知资产观察基线</b><span>¥{base.fmt_num(target['known_assets_jpy'])}</span><i style="width:50%"></i></div>
    <div><b>＋40%观察目标</b><span>¥{base.fmt_num(target['plus_40_observation_target_jpy'])}</span><i style="width:70%"></i></div>
    <div><b>＋100%压力目标</b><span>¥{base.fmt_num(target['plus_100_observation_target_jpy'])}</span><i style="width:100%"></i></div></div>
    <p class="boundary">{base.esc(target['boundary'])}</p>
    <div class="metric-grid"><article class="metric"><b>可审计数值覆盖</b><strong>0.00%</strong><small>0项；未量化不等于收益为0</small></article>
    <article class="metric"><b>已证明的组合贡献</b><strong>未形成</strong><small>不再沿用旧的部分覆盖数字</small></article>
    <article class="metric"><b>＋40%剩余差额</b><strong>不能精确扣减</strong><small>只保留观察目标终值</small></article>
    <article class="metric"><b>＋100%可行性</b><strong>没有可信路径</strong><small>不是收益承诺或杠杆授权</small></article></div>
    <p><b>＋40%结论：</b>{base.esc(target['plus_40_status'])}</p>
    <p><b>＋100%结论：</b>{base.esc(target['plus_100_feasibility'])}</p>
    <p><b>为什么不能给精确差额：</b>{base.esc(target['gap_label'])}</p>
    <p><b>现金作用：</b>{base.esc(target['cash_role'])}</p>
    <p class="boundary">{base.esc(target['cash_assumption_boundary'])} {base.esc(target['risk_only_boundary'])}</p>
    <h4>要让路径成立，必须发生什么</h4><ul><li>{base.esc(target['required_change_plus40'])}</li><li>{base.esc(target['required_change_plus100'])}</li></ul>
    <p><b>落后时的替代路线：</b>{base.esc(target['alternative_route_if_behind'])}</p>
    {base.details('逐资产量化边界', '<table><thead><tr><th>代码</th><th>名称</th><th>已知权重</th><th>数值收益</th><th>数值贡献</th><th>状态</th><th>原因与影响</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table>')}
    <h4>前瞻观察里程碑</h4><table><thead><tr><th>日期</th><th>＋40%观察路径</th><th>＋100%压力路径</th><th>边界</th></tr></thead><tbody>{milestone_rows}</tbody></table>
    <p><b>下一次复核：</b>{base.esc(target['next_review'])}</p>
    """

def locator_text(value: Any) -> str:
    if not value:
        return "原文位置未单独登记"
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "；".join(locator_text(item) for item in value)
    if isinstance(value, dict):
        labels = {
            "doc_id": "文件编号", "published_at": "发布时间", "accounting_standard": "会计准则",
            "locator_type": "定位方式", "statement_locations": "报表或章节", "period_rule": "期间规则",
            "boundary": "定位边界", "section": "章节", "page": "页码", "field": "字段",
        }
        parts = []
        for key, item in value.items():
            if key == "selected_metrics" and isinstance(item, dict):
                metrics = []
                for metric, detail in item.items():
                    if isinstance(detail, dict):
                        metrics.append(
                            f"{metric}：字段{detail.get('qname', '未登记')}，期间{detail.get('contextRef', '未登记')}，单位{detail.get('unitRef', '未登记')}"
                        )
                parts.append("财务字段：" + "；".join(metrics))
            elif key in labels:
                parts.append(f"{labels[key]}：{locator_text(item)}")
        return "；".join(parts) or "原文位置见正式来源中的对应财务表或风险章节"
    return str(value)


def render_guidance_card(guidance: dict[str, Any], base: Any) -> str:
    facts = "".join(f"<li>{base.esc(value)}</li>" for value in guidance.get("facts", [])) or "<li>该资产不适用企业业绩指引。</li>"
    source = base.link(guidance.get("url")) if guidance.get("url") else '<span class="muted">没有独立外部链接；已明确隔离用途。</span>'
    return (
        f"<p><b>状态：</b>{base.esc(guidance.get('plain_status'))}</p>"
        f"<p><b>期间：</b>{base.esc(guidance.get('period'))}</p><ul>{facts}</ul>"
        f"<p><b>正式来源：</b>{base.esc(guidance.get('source_title'))}｜{base.esc(guidance.get('publisher'))}｜"
        f"{base.esc(guidance.get('published_at'))}<br>{source}</p>"
        f"<p><b>原文位置：</b>{base.esc(guidance.get('locator'))}</p>"
        f"<p><b>反向影响：</b>{base.esc(guidance.get('reverse_impact'))}</p>"
        f"<p><b>日期边界：</b>{base.esc(guidance.get('date_impact') or '发布日期与数据期间见上方登记。')}</p>"
        f"<p><b>下次更新条件：</b>{base.esc(guidance.get('update_condition'))}</p>"
    )


def render_precise_evidence_roles(item: dict[str, Any], base: Any) -> str:
    rows = []
    for role in item["precise_evidence_roles"]:
        source = base.link(role.get("url")) if role.get("url") else '<span class="muted">无外部链接；状态和使用边界已明确</span>'
        rows.append(
            "<tr>"
            f"<td>{base.esc(role.get('role'))}<br><small>{base.esc(role.get('status'))}</small></td>"
            f"<td><b>{base.esc(role.get('title'))}</b><br>{base.esc(role.get('publisher'))}<br>{source}</td>"
            f"<td>{base.esc(role.get('published_at'))}<br>{base.esc(role.get('period'))}</td>"
            f"<td>{base.esc(locator_text(role.get('locator')))}</td>"
            f"<td>{base.esc(role.get('supports'))}</td><td>{base.esc(role.get('cannot_prove'))}</td></tr>"
        )
    return (
        "<table><thead><tr><th>证据角色与状态</th><th>标题、机构与原文</th><th>时间与期间</th>"
        "<th>原文位置</th><th>实际证明</th><th>不能证明</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>"
    )


def render_holding_card(item: dict[str, Any], base: Any) -> str:
    financial = item["financial"]
    quality = financial["quality"]
    metrics = "".join(
        f'<li>{base.esc(key)}：{base.fmt_num(value)}{("%" if "率" in key else "")}</li>'
        for key, value in quality.get("metrics", {}).items()
    ) or '<li>没有取得足够字段，不能计算同口径机械比率。</li>'
    source_url = financial.get("url")
    event_rows = "".join(
        f'<li>{base.esc(value.get("published_at"))}｜{base.esc(value.get("title"))}｜{base.link(value.get("url"))}</li>'
        for value in item["event_leads"]
    ) or '<li>限定范围内未取得可独立使用的新公司事件；这不等于市场上没有发生事件。</li>'
    adjustment = (
        f'<p class="alert"><b>Marvell事件下推：</b>{base.esc(item["action"]["marvell_event_adjustment"])}</p>'
        if item["action"].get("marvell_event_adjustment") else ""
    )
    valuation_missing = item["valuation"].get("missing_plain") or "已按本期边界登记"
    guidance = item["financial"]["guidance_evidence"]
    body = f'''
    <div class="asset-summary"><div><b>唯一动作</b><strong>{base.esc(item['action']['unique_action'])}</strong></div><div><b>已知账户权重</b><strong>{item['account_fact']['weight_of_known_assets_pct']:.2f}%</strong></div><div><b>下次复核</b><strong>{base.esc(item['action']['next_review'])}</strong></div></div>
    <p><b>为什么：</b>{base.esc(item['action']['reason'])}</p>{adjustment}
    <div class="research-grid">
      <article><h4>公司或资产做什么</h4><p>{base.esc(item['business_model'])}</p><h4>如何赚钱</h4><p>{base.esc(item['how_it_makes_money'])}</p><h4>增长驱动</h4><p>{base.esc(item['growth_drivers'])}</p></article>
      <article><h4>账户事实</h4><p>{base.esc(base.account_quantity_text(item['account_fact']['quantity_by_account']))}</p><p>已知市值：¥{base.fmt_num(item['account_fact']['known_market_value_jpy'])}</p><p><b>{base.esc(item['account_fact']['data_boundary'])}</b></p></article>
      <article><h4>财务质量</h4><p>期间：{base.esc(financial.get('period'))}｜口径：{base.esc(financial.get('consolidation'))}</p><p>{base.esc(quality.get('summary'))}</p><ul>{metrics}</ul></article>
      <article><h4>公司正式指引</h4>{render_guidance_card(guidance, base)}</article>
      <article><h4>护城河与竞争</h4><p><b>护城河：</b>{base.esc(item['moat_and_competition']['moat'])}</p><p><b>主要竞争者：</b>{base.esc(item['moat_and_competition']['competitors'])}</p><p><b>反向竞争证据：</b>{base.esc(item['moat_and_competition']['reverse_competition'])}</p></article>
      <article><h4>估值或风险定价</h4><p>{base.esc(item['valuation']['classification'])}</p><p><b>方法：</b>{base.esc(item['valuation']['method'])}</p><p><b>适用原因：</b>{base.esc(item['valuation']['method_reason'])}</p><p><b>总控答案：</b>{base.esc(item['valuation']['final_control_answer'])}</p><p><b>数值边界：</b>{base.esc(item['valuation']['price_boundary'])}</p></article>
      <article><h4>双时间尺度</h4><p><b>短期：</b>{base.esc(item['forecast']['short_term'])}</p><p><b>中期：</b>{base.esc(item['forecast']['medium_term'])}</p><p><b>把握度：</b>{base.esc(item['forecast']['control_confidence'])}</p><p class="muted">{base.esc(item['forecast']['confidence_boundary'])}</p></article>
      <article><h4>催化剂、反方与失效</h4><p><b>催化剂：</b>{base.esc(item['action']['catalysts'])}</p><p><b>当前反向证据：</b>{base.esc(item['action']['current_reverse_evidence'])}</p><p><b>未来失效条件：</b>{base.esc(item['action']['invalidation'])}</p></article>
      <article><h4>替换、目标和验证</h4><p><b>替换比较：</b>{base.esc(item['action']['replacement'])}</p><p><b>目标作用：</b>{base.esc(item['action']['target_contribution'])}</p><p><b>验证日：</b>{base.esc(item['action']['next_review'])}</p></article>
    </div>
    {base.details('正式财务字段、来源与定位', (base.render_period_blocks(financial) if financial.get("period_blocks") else f'<table><thead><tr><th>字段</th><th>数值</th><th>使用状态</th></tr></thead><tbody>{base.value_rows(financial.get("fields", dict()), financial.get("currency"))}</tbody></table>') + (f'<p><b>来源：</b>{base.esc(financial.get("source_title"))}｜{base.esc(financial.get("publisher"))}｜{base.link(source_url)}</p><p><b>原文位置：</b>{base.esc(locator_text(financial.get("locator")))}</p>' if source_url else '<p class="boundary">该资产不适用企业财务口径，未使用企业利润表、资产负债表或现金流量表。</p>'))}
    {base.details('估值输入、公式与缺口', f'<p><b>唯一当前价格：</b>{base.fmt_num(item["valuation"].get("current_price"),4)} {base.esc(item["valuation"].get("current_price_currency"))}｜{base.esc(item["valuation"].get("current_price_time"))}｜{base.esc(item["valuation"].get("current_price_timezone"))}｜{base.esc(item["valuation"].get("current_price_type"))}｜{base.esc(item["valuation"].get("current_price_source"))}</p><p><b>前瞻输入：</b>{base.human_text(item["valuation"].get("forward_input"))}</p><p><b>公式：</b>{base.human_text(item["valuation"].get("formula"))}</p><p><b>未闭合项及影响：</b>{base.esc(valuation_missing)}</p>')}
    {base.details('七类证据角色、原文与使用边界', render_precise_evidence_roles(item, base))}
    {base.details('公司事件线索与证据边界', f'<ul>{event_rows}</ul><p class="muted">新闻线索不等同公司正式公告；无正式原文时不支持估值或动作。</p>')}
    '''
    return base.details(f"{item['asset_id']}｜{item['name']}", body, attrs=f'data-holding="{base.esc(item["asset_id"])}"')


def render_gate_card(item: dict[str, Any], base: Any) -> str:
    rows = []
    for gate in item["gates"]:
        source = gate.get("source") if isinstance(gate.get("source"), dict) else {}
        source_html = f'<b>{base.esc(source.get("title"))}</b><br>{base.link(source.get("url"))}' if source.get("url") else '<span class="missing">未取得可点击正式原文</span>'
        if gate.get("evidence_complete"):
            missing_html = '<span class="ok">本关所列事实和可点击原文已取得；本关无缺项。</span>'
        else:
            missing = gate.get("missing") or ["本关证据尚未闭合，因此不形成可执行动作。"]
            missing_html = '<ul>' + ''.join(f'<li>{base.esc(value)}</li>' for value in missing) + '</ul>'
        rows.append(
            f'<tr data-gate-row="1"><td>第{gate["gate"]}关</td><td>{base.esc(gate["status"])}</td>'
            f'<td>{base.esc(gate["fact"])}</td><td>{source_html}</td><td>{missing_html}</td></tr>'
        )
    body = f'''
    <div class="asset-summary"><div><b>身份</b><strong>{base.esc(item['identity'])}</strong></div><div><b>停关</b><strong>{base.esc(item['formal_gate_stop'])}</strong></div><div><b>可执行</b><strong>否</strong></div></div>
    <p><b>激活方向：</b>{base.esc(item['activated_sector'])}</p>
    <table><thead><tr><th>正式关卡</th><th>状态</th><th>事实与理由</th><th>可点击原文</th><th>未闭合项</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
    <p><b>估值或风险定价：</b>{base.esc(item['valuation_or_risk_pricing'])}</p><p><b>与现金/持仓比较：</b>{base.esc(item['replacement_target'])}</p>
    <p><b>执行条件：</b>{base.esc(item['executable_condition'])}</p><p><b>短期：</b>{base.esc(item['short_term'])}</p><p><b>中期：</b>{base.esc(item['medium_term'])}</p><p><b>下一次验证：</b>{base.esc(item['next_review'])}</p>
    '''
    return base.details(f"{item['asset_id']}｜{item['name']}", body, attrs=f'data-research="{base.esc(item["asset_id"])}"')

def update_first_layer(model: dict[str, Any], final: dict[str, Any]) -> None:
    action = model["judgment"].setdefault("today_action", {})
    portfolio = final["portfolio_judgment"]
    action["headline"] = "今天不新增仓位、不追高；保留现金选择权，等待正式五关和可审计替换优势。"
    action["priority"] = [
        "现有持仓按24类唯一答案管理；不使用15%、20%或未经确认的30%固定硬线机械交易。",
        "AI核心持仓继续持有、不追价；任何新AI代理必须先证明比现金和现有核心更优。",
        "18只研究对象目前均未完成正式五关；可执行新增机会为0，原因是研究尚未闭合，不能据此评价整个市场。",
        "若必须降低加密相关股票风险，复核顺序为COIN→CRCL→MSTR；本期不生成订单。",
        "原9项数值情景因倍数样本链不完整已撤回；未量化部分不能当作0，当前不能证明＋40%路径成立。",
    ]
    action["cash_use_rule"] = portfolio["cash_role"]
    action["what_would_change_today_action"] = [
        portfolio["plus40_feasibility"]["required_change"],
        portfolio["plus100_feasibility"]["required_change"],
        f"下一次复核：{portfolio['next_review']}",
    ]

def replace_identity(html_text: str, run_id: str, generated_at: str) -> str:
    html_text = html_text.replace(
        "<title>★2026-08-20完整投研产品候选_v2.0_内容闸重建版</title>",
        "<title>★2026-08-20完整投研产品候选_v2.0_最终完整HTML</title>",
    )
    html_text = html_text.replace(
        "<h1>2026-08-20完整投研产品候选 v2.0｜内容闸重建版</h1>",
        "<h1>2026-08-20完整投研产品候选 v2.0｜最终完整HTML</h1>",
    )
    html_text = html_text.replace("返工生成时间", "最终HTML生成时间")
    html_text = html_text.replace("退回后重建，待总控全文复核", "最终完整HTML，等待全文复核")
    html_text = html_text.replace(
        "第五关通过0只，可执行新增机会0只。MRVL是新加入的研究观察对象，不是正式机会。",
        "第五关通过0只，可执行新增机会0只。八项重点机会已完成总控排序，但均未被升级为正式机会。",
    )
    return html_text


def expected_contribution(cap_row: dict[str, Any], probabilities: dict[str, int]) -> float:
    contributions = cap_row["valuation_or_risk_pricing"]["scenario_contribution_pp"]
    return sum(contributions[key] * probabilities[key] / 100 for key in ("bear", "base", "bull"))


def visible_text(html_text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<[^>]+>", " ", html_text)
    return html.unescape(text)


def semantic_qa(
    model: dict[str, Any],
    html_text: str,
    capability: dict[str, Any],
    final: dict[str, Any],
    output_dir: Path,
    attachment_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    visible = visible_text(html_text)
    cap_map = capability_holding_map(capability)
    numeric = numeric_judgment_map(final)
    risk = risk_judgment_map(final)
    opportunity = {row["symbol"]: row for row in final["priority_opportunity_judgments"]}
    recalculation_errors = []
    probability_errors = []
    for symbol, judgment in numeric.items():
        probs = judgment["probability_pct"]
        if sum(probs.values()) != 100:
            probability_errors.append(symbol)
        actual = expected_contribution(cap_map[symbol], probs)
        if abs(actual - judgment["expected_contribution_pp"]) > 0.00001:
            recalculation_errors.append({"symbol": symbol, "calculated": actual, "approved": judgment["expected_contribution_pp"]})
    recalculated_total = sum(expected_contribution(cap_map[s], numeric[s]["probability_pct"]) for s in numeric)
    approved_total = final["portfolio_judgment"]["numeric_scenario_probability_weighted_contribution_pp"]
    target = model["target_bridge"]
    priority_order = final["cross_asset_unique_answers"]["research_priority_order"]
    model_priority = [
        row["asset_id"]
        for row in sorted(
            (row for row in model["research_gates"] if row["asset_id"] in opportunity),
            key=lambda row: row["final_opportunity_judgment"]["rank"],
        )
    ]
    forbidden = [
        "等待GPT总控",
        "总控必须决定",
        "需GPT总控",
        "仅供总控",
        "path_proven=true",
        "当前组合可以证明＋40%路径成立",
    ]
    forbidden_hits = {term: visible.count(term) for term in forbidden if term in visible}
    model_text = json.dumps(model, ensure_ascii=False)
    generic_guidance_phrase = "现有已核材料中没有为本包逐项独立提取公司指引"
    guidance_failures = []
    for item in model["holdings"]:
        guidance = item.get("financial", {}).get("guidance_evidence", {})
        required = ("plain_status", "period", "facts", "source_title", "publisher", "published_at", "url", "locator", "reverse_impact", "update_condition")
        if any(guidance.get(key) in (None, "", []) for key in required):
            guidance_failures.append(item["asset_id"])
    stale_term = "GPT总控最终参数及情景权重"
    risk_probability_errors = []
    for item in model["holdings"]:
        if item["asset_id"] in risk:
            risk_text = json.dumps({"forecast": item.get("forecast"), "valuation": item.get("valuation")}, ensure_ascii=False)
            if re.search(r"(?:概率|把握度)[^。；]{0,12}(?:约)?\d+(?:\.\d+)?%", risk_text):
                risk_probability_errors.append(item["asset_id"])
    gate_complete_count = 0
    gate_contradictions = []
    gate_source_failures = []
    for item in model["research_gates"]:
        for gate in item["gates"]:
            source = gate.get("source") if isinstance(gate.get("source"), dict) else {}
            clickable = bool(source.get("title")) and str(source.get("url", "")).startswith(("https://", "http://"))
            if gate.get("evidence_complete"):
                gate_complete_count += 1
                if gate.get("missing"):
                    gate_contradictions.append(f"{item['asset_id']}-G{gate['gate']}")
                if not clickable:
                    gate_source_failures.append(f"{item['asset_id']}-G{gate['gate']}")
    required_role_url_failures = []
    for item in model["holdings"]:
        for role in item.get("precise_evidence_roles", []):
            required_url = (
                role["role"] in {"公司指引或替代指引", "反向证据"}
                or (role["role"] == "财务事实" and item["asset_id"] not in {"BTC", "ETH"})
                or (role["role"] == "估值输入" and item["asset_id"] in numeric)
                or (role["role"] == "公司或行业事件" and role["status"].startswith("已取得"))
            )
            if required_url and not str(role.get("url", "")).startswith(("https://", "http://")):
                required_role_url_failures.append(f"{item['asset_id']}:{role['role']}")
    unlabeled_missing_hits = len(re.findall(r"已知市值[^<]{0,160}(?:<[^>]+>\s*)*尚未取得", html_text))
    quality_explanation_failures = [
        item["asset_id"] for item in model["holdings"]
        if not item.get("financial", {}).get("quality", {}).get("industry_explanation")
    ]
    expected_attachment_names = set(ATTACHMENT_NAMES.values())
    declared_attachment_names = set(
        re.findall(r'href="([^"]+\.json)"', html_text)
    ) & expected_attachment_names
    attachment_failures = []
    for row in attachment_rows:
        path = output_dir / row["name"]
        try:
            load_json(path)
        except Exception as exc:
            attachment_failures.append({"name": row["name"], "reason": f"无法打开JSON：{exc}"})
            continue
        actual = {"size": path.stat().st_size, "sha256": sha256(path)}
        if actual["size"] != row["size"] or actual["sha256"] != row["sha256"]:
            attachment_failures.append({"name": row["name"], "reason": "HTML登记的大小或哈希与实物不一致", "actual": actual})
    pdca_attachment = load_json(output_dir / ATTACHMENT_NAMES["pdca"])
    gate_attachment = load_json(output_dir / ATTACHMENT_NAMES["gates"])

    visible_machine_terms = (
        "NON_PRICE_RISK_FRAMEWORK_ONLY",
        "RISK_PRICE_ANCHOR_ONLY",
        "REJECT_NUMERIC_SCENARIO",
        "NO_NUMERIC_RANGE",
        "NO_NUMERIC_PROBABILITY",
        "机器实物：",
        "本轮最终动作以总控唯一答案为准",
        "GPT总控",
        "OpenD",
        "Current",
    )
    visible_machine_hits = {term: visible.count(term) for term in visible_machine_terms if visible.count(term)}
    visible_dict_hits = sum(visible.count(prefix) for prefix in ("{'", '{"'))
    local_path_hits = len(re.findall(r"(?i)(?:[A-Z]:\\|file://)", visible))

    target_keys = re.findall(r'data-target-row="([^"]+)"', html_text)
    expected_target_keys = [row["asset_id"] for row in model["target_bridge"]["asset_rows"]]
    duplicate_target_keys = sorted({key for key in target_keys if target_keys.count(key) > 1})
    guidance_exact_failures = []
    for symbol in GUIDANCE_EVIDENCE_OVERRIDES:
        item = next((row for row in model["holdings"] if row["asset_id"] == symbol), None)
        guidance = (item or {}).get("financial", {}).get("guidance_evidence", {})
        exact_date = bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(guidance.get("published_at") or "")))
        direct_url = str(guidance.get("url") or "").startswith(("https://", "http://"))
        required = all(guidance.get(key) for key in ("source_title", "publisher", "period", "locator", "date_impact"))
        if not item or not exact_date or not direct_url or not required:
            guidance_exact_failures.append({
                "symbol": symbol,
                "published_at": guidance.get("published_at"),
                "url": guidance.get("url"),
                "required_metadata_complete": required,
            })
    ibkr_guidance = next(row for row in model["holdings"] if row["asset_id"] == "US.IBKR")["financial"]["guidance_evidence"]
    ibkr_direct_filing = "sec.gov/Archives/edgar/data/" in str(ibkr_guidance.get("url", ""))

    gate4_rows = [
        (item["asset_id"], next(gate for gate in item["gates"] if gate["gate"] == 4))
        for item in model["research_gates"]
    ]
    gate4_template_failures = [
        symbol for symbol, gate in gate4_rows
        if "本轮最终动作以总控唯一答案为准" in str(gate.get("fact"))
        or "下一次验证：" not in str(gate.get("fact"))
        or not str(gate.get("fact")).strip()
    ]
    gate4_unique_fact_count = len({str(gate.get("fact")) for _, gate in gate4_rows})

    hrefs = re.findall(r'href="([^"]+)"', html_text)
    local_hrefs = [href for href in hrefs if href in expected_attachment_names]
    external_hrefs = [href for href in hrefs if href.startswith(("https://", "http://"))]
    evidence_click_sample = []
    for href in (local_hrefs[:7] + external_hrefs[:10]):
        if href in expected_attachment_names:
            path = output_dir / href
            ok = path.exists() and path.is_file()
            kind = "同批次附件"
        else:
            ok = bool(re.match(r"https?://[^/]+/.+", href))
            kind = "外部正式来源"
        evidence_click_sample.append({"href": href, "kind": kind, "pass": ok})
    evidence_click_failures = [row for row in evidence_click_sample if not row["pass"]]

    checks = {
        "J01唯一判断源哈希": {
            "pass": final["status"] == "GPT_CONTROL_FINAL_JUDGMENT_COMPLETE",
            "detail": {"judgment_id": final["judgment_id"], "source_run_id": final["source_run_id"]},
        },
        "J02持仓覆盖与唯一答案": {
            "pass": len(model["holdings"]) == 24 and {x["asset_id"] for x in model["holdings"]} == set(numeric) | set(risk),
            "detail": {"holdings": len(model["holdings"]), "numeric": len(numeric), "risk_only": len(risk)},
        },
        "J03九项情景概率与逐项复算": {
            "pass": not probability_errors and not recalculation_errors,
            "detail": {"probability_sum_errors": probability_errors, "recalculation_errors": recalculation_errors},
        },
        "J04组合贡献复算": {
            "pass": abs(recalculated_total - approved_total) <= 0.00001 and abs(target["probability_weighted_contribution_pp"] - approved_total) <= 0.000001,
            "detail": {"calculated_pp": round(recalculated_total, 6), "approved_pp": approved_total},
        },
        "J05风险框架资产隔离": {
            "pass": len(risk) == 15 and all(not row["target_contribution_inclusion"] and row["probability"] == "NO_NUMERIC_PROBABILITY" for row in risk.values()),
            "detail": {"count": len(risk), "numeric_probability_count": 0},
        },
        "J06目标差额与可行性": {
            "pass": abs(target["plus_40_remaining_gap_pp"] - 31.583365) < 1e-9 and abs(target["plus_100_remaining_gap_pp"] - 91.583365) < 1e-9 and "尚未形成可执行路径" in target["plus_40_status"] and "没有可信可执行路径" in target["plus_100_status"],
            "detail": {"plus40_gap_pp": target["plus_40_remaining_gap_pp"], "plus100_gap_pp": target["plus_100_remaining_gap_pp"]},
        },
        "J07八项重点机会排序与停关": {
            "pass": model_priority == priority_order and all(not row["executable"] and row["final_opportunity_judgment"]["max_weight_pct"] == 0 for row in model["research_gates"] if row["asset_id"] in opportunity),
            "detail": {"expected_order": priority_order, "actual_order": model_priority, "gate5_pass": 0},
        },
        "J08研究池完整保留": {
            "pass": len(model["research_gates"]) == 18 and all(len(row["gates"]) == 5 for row in model["research_gates"]),
            "detail": {"research_objects": len(model["research_gates"]), "gate_rows": sum(len(row["gates"]) for row in model["research_gates"])},
        },
        "J09第一层与目标桥一致": {
            "pass": ("＋8.42个百分点" in visible or "+8.42个百分点" in visible) and "距离＋40%" in visible and "31.58个百分点" in visible and "当前无可信可执行路径" in visible,
            "detail": "第一层、目标驾驶舱和逐资产桥使用同一判断源。",
        },
        "J10过期待办清零": {"pass": not forbidden_hits, "detail": forbidden_hits},
        "J11冻结能力完整": {
            "pass": len(model["layers"]) == 7 and len(model["pdca"]["plain_records"]) == 57 and len(model["external_views"]) == model["external_view_expected_count"] and all(f'data-module="{name}"' in html_text for name in ("causal-chart", "risk-penetration", "replacement-engine", "shadow-portfolio", "issue-ledger")),
            "detail": {"layers": len(model["layers"]), "pdca_records": len(model["pdca"]["plain_records"]), "external_views": len(model["external_views"])},
        },
        "J12状态与PDF边界": {
            "pass": model["status"] == STATUS and not list(output_dir.glob("*.pdf")) and "未授权、未生成" in visible,
            "detail": {"status": model["status"], "pdf_count": len(list(output_dir.glob("*.pdf")))},
        },
        "J13UTF8与唯一HTML": {
            "pass": b"\xef\xbf\xbd" not in html_text.encode("utf-8") and len(list(output_dir.glob("*.html"))) == 1,
            "detail": {"replacement_character_bytes": html_text.encode("utf-8").count(b"\xef\xbf\xbd"), "html_count": len(list(output_dir.glob("*.html")))},
        },
        "J14公司指引逐项恢复": {
            "pass": not guidance_failures and visible.count(generic_guidance_phrase) == 0,
            "detail": {"holding_count": 24, "complete_guidance_count": 24 - len(guidance_failures), "failures": guidance_failures, "old_generic_phrase_hits": visible.count(generic_guidance_phrase)},
        },
        "J15总控估值裁定状态一致": {
            "pass": visible.count(stale_term) == 0 and model_text.count(stale_term) == 0,
            "detail": {"visible_stale_hits": visible.count(stale_term), "machine_stale_hits": model_text.count(stale_term), "numeric_scenarios": len(numeric)},
        },
        "J16风险框架禁用伪精确概率": {
            "pass": not risk_probability_errors,
            "detail": {"risk_asset_count": len(risk), "probability_conflicts": risk_probability_errors},
        },
        "J17五关状态来源缺项互斥": {
            "pass": not gate_contradictions and not gate_source_failures and visible.count("本批次未取得；不据此形成动作") == 0,
            "detail": {"complete_gate_rows": gate_complete_count, "complete_with_missing": gate_contradictions, "complete_without_clickable_source": gate_source_failures, "old_empty_list_render_hits": visible.count("本批次未取得；不据此形成动作")},
        },
        "J18关键证据直接可追溯": {
            "pass": visible.count("详见机器附件") == 0 and not required_role_url_failures,
            "detail": {"machine_attachment_placeholder_hits": visible.count("详见机器附件"), "required_role_url_failures": required_role_url_failures, "evidence_role_rows": sum(len(item.get("precise_evidence_roles", [])) for item in model["holdings"])},
        },
        "J19缺失字段有标签及行业解释": {
            "pass": unlabeled_missing_hits == 0 and not quality_explanation_failures,
            "detail": {"unlabeled_missing_after_market_value": unlabeled_missing_hits, "industry_explanation_failures": quality_explanation_failures},
        },
        "J20可见HTML与机器源交叉检查": {
            "pass": (
                html_text.count('data-holding=') == 24
                and html_text.count('data-research=') == 18
                and visible.count("公司正式指引") >= 24
                and visible.count("账户数据边界：") >= 24
            ),
            "detail": {
                "visible_holding_cards": html_text.count('data-holding='),
                "visible_research_cards": html_text.count('data-research='),
                "visible_guidance_sections": visible.count("公司正式指引"),
                "visible_labeled_account_boundaries": visible.count("账户数据边界："),
            },
        },
        "J21承诺附件真实存在且可打开": {
            "pass": (
                set(row["name"] for row in attachment_rows) == expected_attachment_names
                and declared_attachment_names == expected_attachment_names
                and not attachment_failures
                and pdca_attachment.get("record_count") == 57
                and gate_attachment.get("gate_row_count") == 90
            ),
            "detail": {
                "expected": sorted(expected_attachment_names),
                "declared": sorted(declared_attachment_names),
                "actual": sorted(row["name"] for row in attachment_rows),
                "failures": attachment_failures,
                "pdca_records": pdca_attachment.get("record_count"),
                "gate_rows": gate_attachment.get("gate_row_count"),
            },
        },
        "J22董事长正文机器语言与本地路径清零": {
            "pass": not visible_machine_hits and visible_dict_hits == 0 and local_path_hits == 0,
            "detail": {
                "machine_term_hits": visible_machine_hits,
                "python_dictionary_hits": visible_dict_hits,
                "local_path_hits": local_path_hits,
            },
        },
        "J23六项指引日期与原文定位": {
            "pass": not guidance_exact_failures and ibkr_direct_filing,
            "detail": {
                "checked_symbols": sorted(GUIDANCE_EVIDENCE_OVERRIDES),
                "failures": guidance_exact_failures,
                "ibkr_uses_direct_sec_filing": ibkr_direct_filing,
            },
        },
        "J24目标桥唯一证券键": {
            "pass": (
                len(target_keys) == 24
                and len(set(target_keys)) == 24
                and set(target_keys) == set(expected_target_keys)
                and not duplicate_target_keys
                and "1" not in target_keys
            ),
            "detail": {
                "row_count": len(target_keys),
                "unique_count": len(set(target_keys)),
                "duplicates": duplicate_target_keys,
                "missing": sorted(set(expected_target_keys) - set(target_keys)),
                "unexpected": sorted(set(target_keys) - set(expected_target_keys)),
            },
        },
        "J25第四关公司化且无内部模板": {
            "pass": not gate4_template_failures and gate4_unique_fact_count == len(gate4_rows),
            "detail": {
                "row_count": len(gate4_rows),
                "unique_fact_count": gate4_unique_fact_count,
                "failures": gate4_template_failures,
            },
        },
        "J26关键证据随机打开检查": {
            "pass": len(evidence_click_sample) >= 10 and not evidence_click_failures,
            "detail": {
                "sample_count": len(evidence_click_sample),
                "local_attachment_count": len([row for row in evidence_click_sample if row["kind"] == "同批次附件"]),
                "external_source_count": len([row for row in evidence_click_sample if row["kind"] == "外部正式来源"]),
                "failures": evidence_click_failures,
                "sample": evidence_click_sample,
            },
        },
        "J27附件清单与正文承诺一致": {
            "pass": (
                visible.count("57条历史记录已移入独立附件") == 1
                and html_text.count('data-attachment-table="1"') == 1
                and len(local_hrefs) >= 7
            ),
            "detail": {
                "pdca_promise_hits": visible.count("57条历史记录已移入独立附件"),
                "attachment_table_count": html_text.count('data-attachment-table="1"'),
                "same_package_link_count": len(local_hrefs),
            },
        },
    }
    failures = [name for name, row in checks.items() if not row["pass"]]
    return {
        "schema_version": "V7-FINAL-HTML-SUBSTANTIVE-QA-3.0",
        "run_id": model["run_id"],
        "checked_at_jst": datetime.now(JST).isoformat(timespec="seconds"),
        "checks": checks,
        "pass_count": len(checks) - len(failures),
        "check_count": len(checks),
        "failures": failures,
        "status": "PASS_FOR_GPT_FULL_HTML_CONTENT_GATE" if not failures else "FAIL",
        "pdf_render_authorized": False,
        "independent_review_pass": False,
    }


CLOSURE_AUDIT_NAMES={
 "valuation":"08_九项估值输入与撤回复算审计.json",
 "gates":"09_五关顺序及证据相关性审计.json",
 "news":"10_新闻截止分类与下游传导审计.json",
 "target":"11_目标桥覆盖与命名审计.json",
 "pdca":"12_PDCA质量与新基线审计.json",
 "changes":"13_七项修改前后原因清单.json",
}
FORMAL_GATE_STOPS={
 "JP.8306":3,"JP.8316":3,"JP.8411":3,"US.ASML":1,"US.CEG":3,"US.COHR":1,
 "US.CRDO":1,"US.CVX":3,"US.ETN":1,"US.LITE":1,"US.MU":3,"US.NRG":1,
 "US.ON":1,"US.PLTR":1,"US.VRT":3,"US.WDC":3,"US.XOM":3,"US.MRVL":2,
}

def downgrade_untraceable_valuations(model,capability,final):
 cap_map=capability_holding_map(capability); symbols=set(numeric_judgment_map(final)); audit=[]
 for item in model["holdings"]:
  symbol=item["asset_id"]
  if symbol not in symbols: continue
  cap=cap_map[symbol]; pricing=cap["valuation_or_risk_pricing"]; val=item["valuation"]
  forward=val.get("forward_input") if isinstance(val.get("forward_input"),dict) else {}
  selected=forward.get("selected_nearest_forward_eps") if isinstance(forward,dict) else {}
  selected=selected if isinstance(selected,dict) else {}
  eps=selected.get("eps")
  if eps is None: eps=pricing.get("input",{}).get("forward_eps_usd")
  values=pricing.get("scenario_values",{})
  implied={k:(round(float(v)/float(eps),6) if eps not in (None,0) and v is not None else None) for k,v in values.items()}
  hist=forward.get("historical_forward_pe_reference",{}) if isinstance(forward,dict) else {}
  dated=bool(isinstance(hist,dict) and hist.get("dated_observations") and hist.get("sample_start") and hist.get("sample_end"))
  audit.append({"asset_id":symbol,"name":item["name"],"forward_input":{"value":eps,"period":selected.get("period") or pricing.get("input",{}).get("period"),"source_title":forward.get("source_title"),"publisher":forward.get("publisher"),"source_url":forward.get("source_url"),"retrieved_at_jst":forward.get("retrieved_at_jst")},"prior_scenario_values":values,"implied_multiples":implied,"historical_reference_summary":hist,"dated_multiple_sequence_available":dated,"mechanical_conclusion":"撤回数值情景；倍数的历史样本窗口、逐期序列和选择理由未形成可复核证据链。","action_effect":"保留原持仓风险管理动作，不以撤回区间支持加仓、减仓或目标贡献。"})
  val["classification"]="当前无法形成可审计的数值估值"
  val["method"]="正式财务、公司指引和风险条件复核"
  val["method_reason"]="前瞻盈利来源可以追溯，但情景倍数缺少带日期的历史样本序列、样本窗口和选择理由；因此不能把原三情景价格当作内在价值。"
  val["final_control_answer"]="原三情景价格已撤回。本期只保留经营、现金流、资产负债表和风险触发条件，不提供数值买卖区间。"
  val["price_boundary"]="没有可核的倍数样本链，就不以价格区间支持加仓、减仓或目标贡献；这不表示预期收益为零。"
  val["forward_input"]=f"前瞻输入：{eps if eps is not None else '未取得'}；期间：{selected.get('period') or pricing.get('input',{}).get('period') or '未单独登记'}；来源：{forward.get('source_title') or '外部前瞻盈利资料'}。该输入本身不能证明应采用哪个估值倍数。"
  val["formula"]="原公式为“每股情景值＝前瞻每股盈利×情景倍数”，但情景倍数的样本序列和选择依据未闭合，本期不执行该计算。"
  val["missing"]=["缺少带日期的历史倍数样本序列、样本窗口和参数选择依据。"]
  val["missing_plain"]="尚未取得带日期的历史倍数样本序列、样本窗口和参数选择依据，因此撤回数值估值并隔离所有依赖它的动作。"
  item["forecast"]["control_confidence"]="本期不提供数值概率"
  item["forecast"]["confidence_boundary"]="证据不足时不把主观概率写成可验证频率。"
  item["action"]["reason"]=f"{item['action']['unique_action']}。前瞻盈利资料可追溯，但估值倍数证据链不完整；所以维持风险管理边界，不把旧区间当作行动依据。"
  item["action"]["target_contribution"]="不进入数值目标贡献桥；未量化不等于贡献为零，也不能从全组合目标差额中直接扣除。"
  for role in item.get("precise_evidence_roles",[]):
   if role.get("role")=="估值输入":
    role.update({"status":"只取得前瞻输入，未取得可审计倍数样本链","supports":"只支持前瞻盈利输入及其期间；不支持原三情景倍数。","cannot_prove":"不能证明三情景倍数，也不能支持数值目标贡献或交易动作。"})
 return audit

def rebuild_target_bridge_after_downgrade(model):
 t=model["target_bridge"]; prior={k:t.get(k) for k in ("quantified_asset_count","quantified_weight_pct","probability_weighted_contribution_pp","plus_40_remaining_gap_pp","plus_100_remaining_gap_pp")}
 for row in t["asset_rows"]:
  row.update({"bear_return_pct":None,"base_return_pct":None,"bull_return_pct":None,"probability":"本期不提供数值概率","probability_weighted_contribution_pp":None,"status":"未进入数值贡献桥","missing":"外部估值输入、参数样本或风险定价公式尚未全部闭合；未量化不等于收益为零，本行不用于精确目标差额。"})
 t.update({"quantified_asset_count":0,"quantified_weight_pct":0.0,"unquantified_weight_pct":100.0,"probability_weighted_contribution_pp":None,"plus_40_remaining_gap_pp":None,"plus_100_remaining_gap_pp":None,"coverage_label":"本期没有可审计的全组合数值贡献桥","gap_label":"＋40%和＋100%仅保留从已知资产观察基线出发的目标终值；由于全组合贡献未量化，不能公布扣除预期贡献后的精确剩余差额。","alternative_route_if_behind":"若月度复核落后：先更新账户与正式财报，再比较现金、现有持仓和通过正式五关的新机会；没有可复算替换优势时继续保留现金，不为追目标强行交易。","plus_100_feasibility":"现有证据下没有可信、可执行的＋100%路径；这不是收益承诺，也不是加杠杆授权。"})
 return {"before":prior,"after":{"quantified_asset_count":0,"quantified_weight_pct":0.0,"unquantified_weight_pct":100.0,"probability_weighted_contribution_pp":None,"remaining_gap_status":"未形成可审计全组合贡献，停止伪精确扣减"},"reason":"原53.36%覆盖和8.42个百分点只来自9项未闭合倍数情景，不能冒充全组合。","monthly_milestones_retained_as":"前瞻观察目标路径，不是实际完成度或已证明贡献。"}

def repair_gate_sequences(model):
 audits=[]
 for item in model["research_gates"]:
  symbol=item["asset_id"]; stop=FORMAL_GATE_STOPS[symbol]; gates={int(x["gate"]):x for x in item["gates"]}
  if stop==3 and symbol not in {"US.CVX","US.XOM"}:
   direct=copy.deepcopy(gates[2].get("source") or {})
   if symbol in {"JP.8306","JP.8316","JP.8411"}:
    direct={"title":"日本银行政策状态与会议日程","publisher":"日本银行","date":"2026-08-07","url":"https://www.boj.or.jp/en/"}
    fact="日本银行正式政策状态和会议日程直接关联银行净息差研究；会议日期不等于已经决定加息。"
   else:
    fact=f"{direct.get('title') or item['name']+'正式披露'}直接证明该公司的经营线索属于{item.get('activated_sector') or '当前研究方向'}；只支持该公司，不外推为全板块已经通过。"
   gates[1].update({"source":direct,"fact":fact,"status":"取得直接相关的板块或公司证据","missing":[],"evidence_complete":bool(str(direct.get('url','')).startswith(('http://','https://')))})
  if stop==1:
   gates[1].update({"status":"停在第一关：激活证据不直接相关或未取得","fact":f"本批次没有取得足以直接激活{item.get('activated_sector') or item['name']}的公司级或行业级证据；宏观背景或其他公司的事件不能代替本关。","source":None,"missing":["缺少直接相关、可点击的板块或公司激活证据。"],"evidence_complete":False})
  elif stop==2:
   gates[2]["status"]="停在第二关：公司财务或关键事实未闭合"; gates[2]["evidence_complete"]=False; gates[2]["missing"]=gates[2].get("missing") or ["公司最新完整财务及事件影响未同口径闭合。"]
  else:
   gates[3]["status"]="停在第三关：估值或风险定价证据未闭合"; gates[3]["evidence_complete"]=False; gates[3]["missing"]=gates[3].get("missing") or ["缺少可复算估值输入、参数证据或风险定价边界。"]
  for n in range(stop+1,6):
   gates[n].update({"status":"前一关未通过，本关未进入","fact":"正式五关按顺序执行；前一关未闭合，本关不展示通过结论。","source":None,"missing":[f"第{stop}关未通过，本关未进入。"],"evidence_complete":False})
  item["formal_gate_stop"]=f"第{stop}关：研究证据未闭合"; item["identity"]="研究观察池；研究未完成；当前不可执行。"; item["retain_or_drop"]="保留研究，不等于研究完成后确认没有机会"; item["executable"]=False
  audits.append({"asset_id":symbol,"name":item["name"],"earliest_failed_gate":stop,"passed_gates":list(range(1,stop)),"not_entered_gates":list(range(stop+1,6)),"gate_1_source":gates[1].get("source"),"conclusion":"研究未闭合，不能把零可执行机会写成市场没有机会。"})
 return audits

def inject_market_reversal(model):
 cutoff=model["news"]["evidence_cutoff_jst"]
 events=[
  {"event_id":"NEWS-20260820-US-STOCKS-WALMART","title":"美股回落，沃尔玛引发消费与利润率担忧","publisher":"Reuters（事实由GPT总控核验；Codex直连未成功）","published_at":"2026-08-20","data_date":"2026-08-20","retrieved_at_jst":cutoff,"url":"https://www.reuters.com/business/us-stock-futures-muted-bond-yields-resume-uptrend-ahead-walmarts-earnings-2026-08-20/","fact":"美股在长端收益率重新上行时走弱，沃尔玛业绩和展望加重了对消费者承压及利润率的担忧。","portfolio_impact":"削弱高估值科技的短期风险承受力，也提醒消费相关持仓不能只看降息预期；现金选择权上升。","boundary":"Reuters原始链接由GPT总控核验；Codex本轮直连失败，不宣称直接读取全文。"},
  {"event_id":"NEWS-20260820-TREASURY-BUYBACK-RELIEF-FADED","title":"美国财政部回购带来的长债缓解未能持续","publisher":"Reuters（事实由GPT总控核验；Codex直连未成功）","published_at":"2026-08-20","data_date":"2026-08-20","retrieved_at_jst":cutoff,"url":"https://www.reuters.com/business/us-treasury-buyback-briefly-eases-bond-rout-debt-worries-persist-2026-08-20/","fact":"财政部回购曾短暂缓解长债压力，但债务供给和融资忧虑仍在，长端收益率随后重新上行。","portfolio_impact":"不能把回购当作全面宽松；高估值科技继续不追价，现金保留等待更好风险收益。","boundary":"报道支持市场传导，不替代财政部正式操作文件，也不证明未来收益率方向。"},
  {"event_id":"NEWS-20260820-GLOBAL-MARKET-REVERSAL","title":"全球市场出现股弱、长债收益率升的反向组合","publisher":"Reuters（事实由GPT总控核验；Codex直连未成功）","published_at":"2026-08-20","data_date":"2026-08-20","retrieved_at_jst":cutoff,"url":"https://www.reuters.com/world/china/global-markets-global-markets-2026-08-20/","fact":"市场从早段缓和转为股票走弱、长期国债收益率上升，说明增长担忧与长期融资压力可以同时存在。","portfolio_impact":"利率敏感AI资产面临估值压力；能源和现金短期相对有支撑，但不足以自动产生交易。","boundary":"只反映截止前市场变化，不把盘中波动外推成趋势确认。"},
 ]
 for e in events:
  e["supports"]=e["portfolio_impact"]; e["cannot_prove"]=e["boundary"]
 existing={x.get("event_id") for x in model["news"].get("records",[])}
 model["news"]["records"].extend(copy.deepcopy(x) for x in events if x["event_id"] not in existing)
 model["news"].setdefault("failed_sources",[]).append("上述三条Reuters原始页由GPT总控核验并下达；Codex直连未成功，已明确读取边界。")
 for h in model["holdings"]: h["event_leads"]=[x for x in h.get("event_leads",[]) if "Walmart" not in str(x) and "沃尔玛" not in str(x)]
 lm={int(x["layer"]):x for x in model["layers"]}
 for n,e in {1:events[1],3:events[2],4:events[0]}.items():
  if not any(x.get("event_id")==e["event_id"] for x in lm[n].get("facts",[])): lm[n].setdefault("facts",[]).append(copy.deepcopy(e))
 lm[1]["final_judgment"]+=" 财政部回购的缓解未能持续，长期融资压力仍约束高估值资产。"
 lm[3]["final_judgment"]+=" 截止前出现股票走弱而长端收益率上升的组合，说明流动性并未转为单向宽松。"
 lm[4]["final_judgment"]+=" 沃尔玛引发的消费与利润率担忧使风险偏好回落，不能把早段反弹当作全天结论。"
 lm[3]["portfolio_transmission"]+=" 对利率敏感AI资产继续不追价，现金等待更明确的盈利和折现率改善。"
 lm[4]["portfolio_transmission"]+=" 消费相关判断需同时复核需求、利润率和利率，不用单一降息叙事放行动作。"
 accepted={x.get("event_id") for x in model.get("accepted_event_leads",[])}
 model.setdefault("accepted_event_leads",[]).extend(copy.deepcopy(x) for x in events if x["event_id"] not in accepted)
 return {"cutoff_jst":cutoff,"added_event_ids":[x["event_id"] for x in events],"retrieval_boundary":"Reuters事实由GPT总控核验；Codex直连失败，未冒充直接读取。","propagated_layers":{"世界观与政策":events[1]["portfolio_impact"],"资金与流动性":events[2]["portfolio_impact"],"板块轮动":events[0]["portfolio_impact"]},"misclassification_removed":"沃尔玛市场事件不再挂在BTC公司事件下。"}

def rebuild_pdca_quality(model):
 records=model["pdca"]["plain_records"]; clickable=0
 for row in records:
  old=row.get("verdict"); ev=str(row.get("external_evidence") or ""); clickable+=int(bool(re.search(r"https?://",ev)))
  row["prior_verdict"]=old; row["verdict"]="无法独立验证"; row["external_evidence"]=(ev+"；但本条没有逐项可点击原文，不能据此计入预测能力统计。") if ev else "本条没有逐项可点击原文，不能计入预测能力统计。"; row["error_or_learning_category"]="历史记录证据不足"; row["lesson"]=f"历史第{row['record_number']}条的主要教训：今后必须在预测形成时锁定唯一对象、可外部核验的成功标准、截止日、原文链接和反事实。"; row["pass_standard"]="只有逐条外部证据与原成功定义一一对应，才允许进入统计分母。"; row["ledger_identity"]="历史缺陷账本"
 baseline=[
  {"topic":"高估值AI与长端利率","prediction":"若长端收益率继续上升而盈利预期没有同步上修，高估值AI资产的相对表现将继续承压。","confidence":"中等把握；不写伪精确概率","window":"截至2026-08-27美股收盘","success_definition":"长期国债收益率维持上行或高位，同时AI高估值篮子相对标普500走弱。","counterfactual":"若长端收益率回落且AI盈利指引上修、AI篮子相对走强，则本判断偏保守。","evidence_url":"https://www.reuters.com/world/china/global-markets-global-markets-2026-08-20/","attribution":"数据源与利率传导推理","improvement":"同时记录收益率、指数相对表现和正式盈利指引。","next_validation":"2026-08-27美股收盘后"},
  {"topic":"日本银行与银行股","prediction":"正式政策决定前，三家日本银行仍主要受政策预期驱动，不能仅凭GDP正增长升级为机会。","confidence":"中等把握；不写伪精确概率","window":"截至2026-09-18日本银行会议结果","success_definition":"正式政策、净息差和信贷成本至少有两项同向改善后，才重新进入第三关和第五关复核。","counterfactual":"若政策转鸽或信用成本明显上升，银行研究优先级下调。","evidence_url":"https://www.boj.or.jp/en/","attribution":"规则顺序与政策证据","improvement":"把板块激活、公司财务和估值分开验证。","next_validation":"2026-09-18会议结果发布后"},
  {"topic":"现金与组合目标","prediction":"在估值样本链未闭合时，保留现金比用不可审计区间强行建仓更能控制错误成本。","confidence":"中等偏高把握；不写伪精确概率","window":"下一次正式财报、账户和估值参数联合复核前","success_definition":"没有标的完成正式五关并证明相对现金的可复算优势；现金未被机械使用。","counterfactual":"若出现五关闭合且相对现金优势可复算的机会，继续空仓将产生明确机会成本。","evidence_url":"https://home.treasury.gov/system/files/221/TentativeAuctionScheduleQ22026.pdf","attribution":"估值证据与替换比较","improvement":"目标桥只公布真正量化的覆盖，未量化部分不再当作0。","next_validation":"下一次账户、财报与估值参数同批次复核日"},
 ]
 s=model["pdca"]["body_summary"]; s.update({"ledger_identity":"历史缺陷账本，不代表预测能力","verdict_counts":{"无法独立验证":len(records)},"externally_verifiable":0,"not_independently_verifiable":len(records),"forbidden_claim":"57条旧记录均退出预测能力统计；不能公布胜率或一致率。","new_predictions":baseline,"new_quality_baseline":baseline,"system_changes":["逐条证据没有可点击原文就退出统计分母。","每个新预测必须锁定对象、窗口、成功标准、反事实、证据链接和归因层。","错误归因区分新闻源、数据源、规则、估值、推理和呈现。"]})
 layer7=next(x for x in model["layers"] if int(x["layer"])==7)
 layer7["final_judgment"]="57条旧记录保留为历史缺陷账本，因缺少逐条可点击外部证据，本期全部退出预测能力统计。正文只保留三条新质量基线和真正改变流程的教训。"
 layer7["facts"]=[{"title":"PDCA历史账本证据状态","publisher":"同批次PDCA附件","fact":"57条旧记录均没有逐条可点击外部证据，本期统一判为无法独立验证，不公布胜率或一致率。","supports":"支持把旧记录降为历史缺陷账本并退出统计分母。","cannot_prove":"不能证明过去预测能力，也不能支持当前交易。"},{"title":"新质量基线","publisher":"本批次生产记录","fact":"新建3条预测基线，分别锁定对象、窗口、成功标准、反事实、证据链接、归因层和下次验证日。","supports":"支持未来按同一口径复核预测质量。","cannot_prove":"尚未到验证日，不能提前登记判对。"}]
 return {"historical_record_count":len(records),"prior_claimed_verifiable_count":29,"individually_clickable_evidence_count":clickable,"final_statistics_denominator":0,"historical_ledger_identity":"历史缺陷账本","new_quality_baseline_count":len(baseline),"new_quality_baseline":baseline}

def write_closure_audits(output_dir,run_id,audits):
 purposes={"valuation":"逐项登记9项估值为何撤回及前瞻输入、隐含倍数和缺失证据。","gates":"逐项登记18只研究对象的最早失败关、证据相关性和后续未进入状态。","news":"登记截止前市场反转、新闻分类和向利率、AI、消费及现金的传导。","target":"登记目标桥真实覆盖、命名边界、月度里程碑和落后时替代路径。","pdca":"登记57条历史缺陷账本的证据状态及新质量基线。","changes":"登记本轮七项修改前、修改后和原因。"}
 rows=[]
 for key,name in CLOSURE_AUDIT_NAMES.items():
  p=output_dir/name; write_json(p,{"run_id":run_id,"purpose":purposes[key],"data":audits[key]}); rows.append({"name":name,"purpose":purposes[key],"size":p.stat().st_size,"sha256":sha256(p),"relative_href":name})
 return rows

def semantic_qa_v4(model,html_text,output_dir,attachment_rows,audits):
 visible=visible_text(html_text); expected={x["name"] for x in attachment_rows}; declared=set(re.findall(r'href="([^"]+\.json)"',html_text))&expected; af=[]
 for row in attachment_rows:
  p=output_dir/row["name"]
  try: load_json(p)
  except Exception as e: af.append({"name":row["name"],"reason":str(e)}); continue
  if p.stat().st_size!=row["size"] or sha256(p)!=row["sha256"]: af.append({"name":row["name"],"reason":"HTML登记与实物不一致"})
 terms=("总控答案","经总控批准","总控核验","机器实物路径","机器字典","总控结论","总控判断形成","唯一账户机器源","账户机器源","Codex直连未成功","Codex本轮直连失败","29条有外部可核结果","总控采用","总控分类","待总控","已批准判断","详见机器附件","get_market_snapshot","read-only","source title","publisher","source url","retrieved at JST","selected nearest forward EPS","historical forward PE reference","actual inputs","canonical current quote","price type","SBI_归属未闭合","known_assets_total_jpy","{'",'{"')
 hits={x:visible.count(x) for x in terms if visible.count(x)}
 later=[]
 for item in model["research_gates"]:
  stop=FORMAL_GATE_STOPS[item["asset_id"]]
  for g in item["gates"]:
   if g["gate"]>stop and g["status"]!="前一关未通过，本关未进入": later.append(f"{item['asset_id']}-G{g['gate']}")
 news_ids={x.get("event_id") for x in model["news"]["records"]}; required=set(audits["news"]["added_event_ids"]); layers={int(x["layer"]):{y.get("event_id") for y in x.get("facts",[])} for x in model["layers"]}; stale={x:visible.count(x) for x in ("8.42个百分点","31.58个百分点","91.58个百分点","53.36%")}
 records=model["pdca"]["plain_records"]; lessons=len({x.get("lesson") for x in records}); target_keys=re.findall(r'data-target-row="([^"]+)"',html_text)
 checks={
 "Q01唯一HTML与冻结边界":{"pass":len(list(output_dir.glob("*.html")))==1 and not list(output_dir.glob("*.pdf")) and model["status"]==STATUS,"detail":{"html":len(list(output_dir.glob("*.html"))),"pdf":len(list(output_dir.glob("*.pdf"))),"status":model["status"]}},
 "Q02结构数量":{"pass":len(model["layers"])==7 and len(model["holdings"])==24 and len(model["research_gates"])==18 and sum(len(x["gates"]) for x in model["research_gates"])==90,"detail":{"layers":len(model["layers"]),"holdings":len(model["holdings"]),"research":len(model["research_gates"])}},
 "Q03正文内部语言":{"pass":not hits and not re.search(r"(?i)(?:[A-Z]:\\|file://)",visible),"detail":{"hits":hits,"local_paths":len(re.findall(r"(?i)(?:[A-Z]:\\|file://)",visible))}},
 "Q04估值可追溯性":{"pass":len(audits["valuation"])==9 and all(not x["dated_multiple_sequence_available"] and "撤回数值情景" in x["mechanical_conclusion"] for x in audits["valuation"]),"detail":{"checked":len(audits["valuation"]),"dated_sequences":sum(bool(x["dated_multiple_sequence_available"]) for x in audits["valuation"]),"samples":audits["valuation"][:3]}},
 "Q05目标桥覆盖命名":{"pass":model["target_bridge"]["quantified_asset_count"]==0 and model["target_bridge"]["probability_weighted_contribution_pp"] is None and all(v==0 for v in stale.values()),"detail":{"audit":audits["target"],"stale_hits":stale}},
 "Q06五关相关性顺序":{"pass":len(audits["gates"])==18 and not later and all(FORMAL_GATE_STOPS[x["asset_id"]]==x["earliest_failed_gate"] for x in audits["gates"]),"detail":{"later_gate_errors":later,"samples":audits["gates"][:4]}},
 "Q07零机会语义":{"pass":visible.count("研究未完成")>=1 and visible.count("市场没有机会")==0 and all(not x["executable"] for x in model["research_gates"]),"detail":{"incomplete_hits":visible.count("研究未完成"),"no_opportunity_hits":visible.count("市场没有机会")}},
 "Q08新闻分类传导":{"pass":required<=news_ids and bool(required&layers[1]) and bool(required&layers[3]) and bool(required&layers[4]) and all("Walmart" not in str(x.get("event_leads")) and "沃尔玛" not in str(x.get("event_leads")) for x in model["holdings"]),"detail":{"required":sorted(required),"present":sorted(required&news_ids),"layer1":sorted(required&layers[1]),"layer3":sorted(required&layers[3]),"layer4":sorted(required&layers[4])}},
 "Q09PDCA质量":{"pass":len(records)==57 and all(x.get("ledger_identity")=="历史缺陷账本" and x.get("verdict")=="无法独立验证" for x in records) and lessons==57 and audits["pdca"]["new_quality_baseline_count"]==3 and visible.count("29条有外部可核结果")==0 and visible.count("历史缺陷账本")>=1,"detail":{"records":len(records),"denominator":audits["pdca"]["final_statistics_denominator"],"unique_lessons":lessons}},
 "Q10证据角色":{"pass":all(len(x.get("precise_evidence_roles",[]))>=6 for x in model["holdings"]) and visible.count("详见机器附件")==0,"detail":{"rows":sum(len(x.get("precise_evidence_roles",[])) for x in model["holdings"])}},
 "Q11附件实物":{"pass":declared==expected and not af,"detail":{"expected":sorted(expected),"declared":sorted(declared),"failures":af}},
 "Q12唯一证券键":{"pass":len(target_keys)==24 and len(set(target_keys))==24 and html_text.count('data-holding=')==24 and html_text.count('data-research=')==18,"detail":{"target_rows":len(target_keys),"holding_cards":html_text.count('data-holding='),"research_cards":html_text.count('data-research=')}},
 "Q13UTF8与附件表":{"pass":b"\xef\xbf\xbd" not in html_text.encode("utf-8") and html_text.count('data-attachment-table="1"')==1,"detail":{"replacement_bytes":html_text.encode("utf-8").count(b"\xef\xbf\xbd"),"attachment_table":html_text.count('data-attachment-table="1"')}},
 }
 failures=[k for k,v in checks.items() if not v["pass"]]
 return {"schema_version":"V7-PDF-PRECHECK-SUBSTANTIVE-QA-4.0","run_id":model["run_id"],"checked_at_jst":datetime.now(JST).isoformat(timespec="seconds"),"checks":checks,"pass_count":len(checks)-len(failures),"check_count":len(checks),"failures":failures,"status":"INTERNAL_QA_PASS_WAITING_GPT_FULL_HTML_REVIEW" if not failures else "FAIL","pdf_render_authorized":False,"independent_review_pass":False,"self_declared_content_gate_pass":False}
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-renderer", required=True, type=Path)
    parser.add_argument("--base-model", required=True, type=Path)
    parser.add_argument("--capability-input", required=True, type=Path)
    parser.add_argument("--final-judgment", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--daily-report", required=True, type=Path)
    args = parser.parse_args()

    if args.output_dir.exists():
        raise RuntimeError(f"output exists: {args.output_dir}")
    base = load_base_module(args.base_renderer)
    model = load_json(args.base_model)
    capability = load_json(args.capability_input)
    final = load_json(args.final_judgment)
    if sha256(args.final_judgment) != "D6AB5862EA2F2A8F1BC3EB0F7A6D8CB9AA93AB3659B96E4D1BBFFD687847B291":
        raise RuntimeError("final judgment SHA256 mismatch")
    if final["source_run_id"] != capability["run_id"]:
        raise RuntimeError("judgment and capability input run mismatch")
    if len(final["numeric_holding_judgments"]) != 9 or len(final["risk_framework_holding_judgments"]) != 15:
        raise RuntimeError("final judgment holding coverage mismatch")
    if len(final["priority_opportunity_judgments"]) != 8:
        raise RuntimeError("final judgment opportunity coverage mismatch")

    daily_before = {"size": args.daily_report.stat().st_size, "sha256": sha256(args.daily_report), "mtime": args.daily_report.stat().st_mtime}
    args.output_dir.mkdir(parents=True, exist_ok=False)

    model["schema_version"] = "V7-COMPLETE-PRODUCT-MODEL-2.2-FINAL-HTML"
    model["run_id"] = args.run_id
    model["source_html_run_id"] = load_json(args.base_model)["run_id"]
    model["final_capability_input_run_id"] = capability["run_id"]
    model["final_capability_judgment_id"] = final["judgment_id"]
    model["final_capability_judgment_sha256"] = sha256(args.final_judgment)
    model["judgment_formed_at_jst"] = final["judged_at_jst"]
    model["generated_at_jst"] = datetime.now(JST).isoformat(timespec="seconds")
    model["status"] = STATUS
    prior_today_action = copy.deepcopy(model.get("judgment", {}).get("today_action", {}))
    model["judgment"] = {
        "today_action": prior_today_action,
        "source": "GPT总控最终能力判断唯一源",
        "legacy_asset_answers_removed": True,
    }
    model["holdings"] = merge_holdings(model["holdings"], capability, final)
    model["research_gates"] = merge_research(model["research_gates"], capability, final)
    model["target_bridge"] = build_target_bridge(capability, final)
    audits = {}
    audits["valuation"] = downgrade_untraceable_valuations(model, capability, final)
    audits["gates"] = repair_gate_sequences(model)
    audits["target"] = rebuild_target_bridge_after_downgrade(model)
    audits["news"] = inject_market_reversal(model)
    audits["pdca"] = rebuild_pdca_quality(model)
    audits["changes"] = [
        {"item":"董事长正文","before":"仍含内部流程词、英文抓取字段和数据键","after":"关键卡片改为事实、影响、动作和推翻条件；内部字段只留结构化附件","reason":"用户正文必须直接可读"},
        {"item":"九项估值","before":"有情景价格但没有带日期的倍数样本序列和参数选择理由","after":"九项数值情景全部撤回，保留前瞻输入、风险条件和原动作边界","reason":"不倒推、不编造、不以不可审计区间支持动作"},
        {"item":"18只正式五关","before":"其他公司或宏观新闻错配第一关，且前关失败后仍展示后关结论","after":"逐只登记最早失败关；后续关统一未进入；零机会明确为研究未完成","reason":"正式五关必须按顺序且证据直接相关"},
        {"item":"目标桥","before":"53.36%覆盖和8.42个百分点被误读为全组合","after":"数值覆盖降为0；未量化部分不当作0，不公布伪精确剩余差额","reason":"部分量化不能冒充全组合"},
        {"item":"市场反转新闻","before":"遗漏回购缓解消退、长端收益率回升、股市走弱和沃尔玛担忧","after":"三项事件进入新闻账本并下推世界观、资金和板块层","reason":"截止前市场方向变化必须进入行动解释"},
        {"item":"PDCA","before":"57条重复教训且29条没有逐项可点击外部证据","after":"旧账本全部标为历史缺陷并退出统计；建立3条可外部核验的新基线","reason":"不能把宽松阈值一致冒充预测能力"},
        {"item":"语义QA","before":"明知路径和证据未闭合仍自评通过","after":"新增估值链、五关顺序、目标覆盖、新闻传导、PDCA逐条证据硬闸","reason":"任一实质失败即阻断HTML交付"},
    ]
    model["final_capability_judgment"] = final
    model["pdf_generated"] = False
    model["pdf_authorization_received"] = False
    update_first_layer(model, final)
    model = humanize_visible_value(model)
    attachment_rows = write_core_attachments(model, args.output_dir)
    attachment_rows += write_closure_audits(args.output_dir, args.run_id, audits)

    original_target_renderer = base.render_target_bridge
    original_holding_renderer = base.render_holding_card
    original_gate_renderer = base.render_gate_card
    original_layer_fact_renderer = base.render_layer_fact_list
    original_news_renderer = base.render_news
    original_trace_renderer = base.render_trace
    base.render_target_bridge = lambda target: render_target_bridge(target, base)
    base.render_holding_card = lambda item: render_holding_card(item, base)
    base.render_gate_card = lambda item: render_gate_card(item, base)
    base.render_layer_fact_list = lambda facts: render_layer_fact_list(facts, base)
    base.render_news = lambda news: render_news(news, base)
    base.render_trace = lambda rows: render_trace(rows, model, base)
    try:
        html_text = base.build_html(model)
    finally:
        base.render_target_bridge = original_target_renderer
        base.render_holding_card = original_holding_renderer
        base.render_gate_card = original_gate_renderer
        base.render_layer_fact_list = original_layer_fact_renderer
        base.render_news = original_news_renderer
        base.render_trace = original_trace_renderer
    html_text = replace_identity(html_text, args.run_id, model["generated_at_jst"])
    old_attachment_promise = (
        '<p class="muted">57条PDCA逐项记录、唯一账户机器源、五关矩阵、目标贡献桥、'
        '外部观点映射和功能数据均另存JSON附件；机器字段不进入董事长正文。</p>'
    )
    if old_attachment_promise not in html_text:
        raise RuntimeError("attachment promise marker missing")
    html_text = html_text.replace(old_attachment_promise, render_attachment_table(attachment_rows))
    for source, replacement in VISIBLE_TERM_MAP.items():
        html_text = html_text.replace(source, replacement)
    html_text = html_text.replace("本轮最终动作以总控唯一答案为准", "")
    html_path = args.output_dir / "★2026-08-20完整投研产品候选_v2.0_最终完整HTML.html"
    html_path.write_text(html_text, encoding="utf-8")

    qa = semantic_qa_v4(model, html_text, args.output_dir, attachment_rows, audits)
    write_json(args.output_dir / "14_增强语义QA.json", qa)
    if qa["status"] != "INTERNAL_QA_PASS_WAITING_GPT_FULL_HTML_REVIEW":
        raise RuntimeError(f"semantic QA failed: {qa['failures']}")
    daily_after = {"size": args.daily_report.stat().st_size, "sha256": sha256(args.daily_report), "mtime": args.daily_report.stat().st_mtime}
    boundary = {
        "run_id": args.run_id,
        "before": daily_before,
        "after": daily_after,
        "unchanged": daily_before == daily_after,
        "pdf_generated": False,
        "release": False,
        "trade_calls": 0,
        "order_calls": 0,
        "content_gate_status": "WAITING_FOR_GPT_FULL_HTML_REVIEW",
    }
    write_json(args.output_dir / "15_正式日报未覆盖及阶段边界.json", boundary)
    if not boundary["unchanged"]:
        raise RuntimeError("daily report changed")

    manifest_path = args.output_dir / "16_全部实物SHA256清单.json"
    items = []
    for path in sorted(args.output_dir.iterdir(), key=lambda p: p.name):
        if path.is_file() and path != manifest_path:
            items.append(
                {
                    "name": path.name,
                    "path": str(path),
                    "size": path.stat().st_size,
                    "sha256": sha256(path),
                    "modified_at_jst": datetime.fromtimestamp(path.stat().st_mtime, JST).isoformat(timespec="seconds"),
                }
            )
    write_json(
        manifest_path,
        {
            "run_id": args.run_id,
            "item_count": len(items),
            "items": items,
            "pdf_generated": False,
            "self_hash_excluded": True,
        },
    )

    print(
        json.dumps(
            {
                "run_id": args.run_id,
                "html": str(html_path),
                "html_size": html_path.stat().st_size,
                "html_sha256": sha256(html_path),
                "holdings": len(model["holdings"]),
                "research_objects": len(model["research_gates"]),
                "numeric_holdings": model["target_bridge"]["quantified_asset_count"],
                "risk_only_holdings": len(final["risk_framework_holding_judgments"]),
                "probability_weighted_contribution_pp": model["target_bridge"]["probability_weighted_contribution_pp"],
                "qa": qa["status"],
                "pdf_generated": False,
                "daily_report_unchanged": boundary["unchanged"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
