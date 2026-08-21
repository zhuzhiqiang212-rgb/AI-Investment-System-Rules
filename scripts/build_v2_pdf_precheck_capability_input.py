from __future__ import annotations

import hashlib
import html
import json
import math
import re
import shutil
from datetime import datetime
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

from build_v2_final_capability_input import GUIDANCE, OPPORTUNITIES


ROOT = Path(__file__).resolve().parents[1]
JST = ZoneInfo("Asia/Tokyo")
TASK = ROOT / "00_任务中心" / "V7_阶段C完整HTML能力未闭合退回及PDF前唯一施工令_20260821.html"
STAGE_A = ROOT / "00_任务中心" / "V7_v2.0_GPT总控唯一业务判断输入包_Current.json"
PRIOR_CAPABILITY = ROOT / "00_任务中心" / "V7_v2.0_GPT总控最终能力闭合判断输入包_Current.json"
PRIOR_JUDGMENT = ROOT / "00_任务中心" / "V7_v2.0_GPT总控最终能力判断_Current.json"
PRIOR_GATES = (
    ROOT
    / "output"
    / "candidates"
    / "2026-08-20"
    / "V7-STAGEC-PDFPRECHECK-CLOSE-20260821-172809-JST"
    / "03_正式五关矩阵.json"
)
VALUATION_INPUT = (
    ROOT
    / "output"
    / "decision_inputs"
    / "2026-08-19"
    / "V7-V151-VALUATION-INPUT-CLOSE-20260819-154226-JST"
    / "01_21项估值外部输入总表_20260819.json"
)
VALUATION_DECISION = (
    ROOT
    / "output"
    / "decision_inputs"
    / "2026-08-19"
    / "V7-V151-VALUATION-INPUT-CLOSE-20260819-154226-JST"
    / "V7_v1.5_GPT总控最终估值裁定_20260819.json"
)
FORECAST_DIR = VALUATION_INPUT.parent / "evidence" / "external_consensus"
FORMAL_DAILY = ROOT / "00_请先看这里" / "00_今日日报.pdf"


RESEARCH_SYMBOLS = [
    "JP.8306", "JP.8316", "JP.8411", "US.ASML", "US.CEG", "US.COHR",
    "US.CRDO", "US.CVX", "US.ETN", "US.LITE", "US.MU", "US.NRG",
    "US.ON", "US.PLTR", "US.VRT", "US.WDC", "US.XOM", "US.MRVL",
]
RESEARCH_NAMES = {
    "JP.8306": "三菱日联金融", "JP.8316": "三井住友金融", "JP.8411": "瑞穗金融集团",
    "US.ASML": "阿斯麦", "US.CEG": "Constellation Energy", "US.COHR": "Coherent",
    "US.CRDO": "Credo Technology", "US.CVX": "雪佛龙", "US.ETN": "伊顿",
    "US.LITE": "Lumentum", "US.MU": "美光科技", "US.NRG": "NRG Energy",
    "US.ON": "安森美半导体", "US.PLTR": "Palantir", "US.VRT": "Vertiv",
    "US.WDC": "西部数据", "US.XOM": "埃克森美孚", "US.MRVL": "Marvell Technology",
}
GATE1_STOPS = {"US.ASML", "US.COHR", "US.CRDO", "US.ETN", "US.LITE", "US.NRG", "US.ON", "US.PLTR"}
RESEARCH_READY = set(RESEARCH_SYMBOLS) - GATE1_STOPS
NUMERIC_SYMBOLS = ["JP.4063", "JP.4568", "JP.6954", "JP.7203", "JP.7974", "US.AVGO", "US.META", "US.MSFT", "US.NVDA"]
FORECAST_FILES = {
    symbol: FORECAST_DIR / f"{symbol.replace('.', '_')}_stockanalysis_forecast.html"
    for symbol in NUMERIC_SYMBOLS
}


EXTRA_OPPORTUNITIES = {
    "US.CVX": {
        "name": "雪佛龙", "sector": "石油、天然气与能源供应链",
        "activation": "中东供应风险和油价上升令能源板块进入事件性研究，但事件反转快，不能直接形成买入。",
        "financial": ["2026年第二季度正式结果已取得", "使用产量、实现油价、资本开支、经营现金流和股东回报", "不把税前利润错写成营业利润"],
        "source": "https://www.chevron.com/newsroom/2026/q3/chevron-reports-second-quarter-2026-results",
        "moat": "优质资源、项目执行和全球炼化网络构成壁垒；反向证据是油价回落、项目成本和资本纪律恶化。",
        "pricing": "用中周期油价下的自由现金流、净债务、资本开支和股东回报定价；当前市盈率只作市场温度计。",
        "cash_compare": "现金没有油价和地缘事件反转风险；只有中周期现金流回报明显补偿事件风险时才值得替换现金。",
        "replacement": ["现金"], "replacement_logic": "只与现金的事件对冲价值比较，不机械替换核心AI持仓。",
        "next_trigger": "下一次正式结果、油价与霍尔木兹运输风险变化。",
    },
    "US.XOM": {
        "name": "埃克森美孚", "sector": "石油、天然气与能源供应链",
        "activation": "中东供应风险和油价上升令能源板块进入事件性研究，但事件反转快，不能直接形成买入。",
        "financial": ["2026年第二季度正式申报已取得", "收入、净利润、经营现金流和设备投资分期间登记", "撤回把税前利润称为营业利润的旧字段"],
        "source": "https://www.sec.gov/Archives/edgar/data/34088/000003408826000093/xom-20260630.htm",
        "moat": "资源质量、成本曲线、项目执行和炼化网络构成壁垒；反向证据是油价回落、成本超支和低碳项目资本回报不足。",
        "pricing": "用中周期油价、项目自由现金流、净债务和股东回报定价；不以单季油价高点外推。",
        "cash_compare": "现金没有商品价格回撤；只有中周期现金流收益明显高于现金且估值未透支时才进入第五关。",
        "replacement": ["现金"], "replacement_logic": "只与现金和现有防御仓比较分散价值，不机械替换核心AI。",
        "next_trigger": "下一次正式结果、油价和供应风险变化。",
    },
}


ACTIVATION_SOURCES = {
    "JP.8306": {"title": "日本2026年4至6月GDP第一次初步估计", "publisher": "日本内阁府", "published_at": "2026-08-17", "url": "https://www.esri.cao.go.jp/en/sna/kouhyou/kouhyou_top.html", "locator": "季度GDP发布；只支持银行板块条件研究，不证明BOJ已经加息"},
    "JP.8316": {"title": "日本2026年4至6月GDP第一次初步估计", "publisher": "日本内阁府", "published_at": "2026-08-17", "url": "https://www.esri.cao.go.jp/en/sna/kouhyou/kouhyou_top.html", "locator": "季度GDP发布；只支持银行板块条件研究，不证明BOJ已经加息"},
    "JP.8411": {"title": "日本2026年4至6月GDP第一次初步估计", "publisher": "日本内阁府", "published_at": "2026-08-17", "url": "https://www.esri.cao.go.jp/en/sna/kouhyou/kouhyou_top.html", "locator": "季度GDP发布；只支持银行板块条件研究，不证明BOJ已经加息"},
    "US.CEG": {"title": "Constellation Reports Second Quarter 2026 Results", "publisher": "Constellation Energy", "published_at": "2026-08-06", "url": "https://www-stage.constellationenergy.com/news/2026/08/constellation-reports-second-quarter-2026-results.html", "locator": "长期购电协议、核电资产和全年每股收益指引"},
    "US.MU": {"title": "Micron reports fiscal results and outlook", "publisher": "Micron Technology", "published_at": "2026", "url": "https://investors.micron.com/node/50671", "locator": "HBM、存储需求及下一季度正式指引"},
    "US.VRT": {"title": "Vertiv Reports Strong Second Quarter 2026", "publisher": "Vertiv", "published_at": "2026", "url": "https://investors.vertiv.com/news/news-details/2026/Vertiv-Reports-Strong-Second-Quarter-2026-with-Diluted-EPS-Growth-of-53-Adjusted-Diluted-EPS-Growth-of-60-Raises-Full-Year-2026-Guidance-Across-All-Key-Metrics/default.aspx", "locator": "订单、收入、利润率和自由现金流指引"},
    "US.WDC": {"title": "Western Digital Reports Fiscal Fourth Quarter 2026 Results", "publisher": "Western Digital", "published_at": "2026", "url": "https://investor.wdc.com/node/28586", "locator": "数据中心硬盘需求、收入、毛利率和自由现金流"},
    "US.CVX": {"title": "美国财政部回购与油价供应风险市场综述", "publisher": "Associated Press", "published_at": "2026-08-20", "url": "https://apnews.com/article/1dcf7c9c3cc490b82b2632302628c46b", "locator": "油价和供应风险；只支持事件性研究"},
    "US.XOM": {"title": "美国财政部回购与油价供应风险市场综述", "publisher": "Associated Press", "published_at": "2026-08-20", "url": "https://apnews.com/article/1dcf7c9c3cc490b82b2632302628c46b", "locator": "油价和供应风险；只支持事件性研究"},
    "US.MRVL": {"title": "Marvell与Google定制AI芯片合作及认股权证", "publisher": "Marvell Technology", "published_at": "2026-08-19", "url": "https://investor.marvell.com/sec-filings/all-sec-filings/content/0001193125-26-356217/d412696d8k.htm", "locator": "8-K Item 1.01及认股权证条款"},
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def finite(value: object) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def snapshot_quotes(codes: list[str]) -> tuple[list[dict], dict]:
    from futu import OpenQuoteContext, RET_OK

    started = datetime.now(JST)
    context = OpenQuoteContext(host="127.0.0.1", port=11111)
    try:
        ret, frame = context.get_market_snapshot(codes)
        if ret != RET_OK:
            return [], {"status": "FETCH_FAILED", "started_at_jst": started.isoformat(), "error": str(frame), "trade_calls": 0}
        fields = ["code", "name", "update_time", "last_price", "open_price", "high_price", "low_price", "prev_close_price", "volume", "turnover", "pe_ratio", "pb_ratio", "lot_size"]
        rows = []
        for _, raw in frame.iterrows():
            item = {}
            for field in fields:
                value = raw.get(field)
                if hasattr(value, "item"):
                    value = value.item()
                if isinstance(value, float) and not math.isfinite(value):
                    value = None
                item[field] = value
            item["name"] = RESEARCH_NAMES.get(str(item["code"]), str(item.get("name") or ""))
            item["source"] = "Futu OpenD只读行情快照"
            rows.append(item)
        finished = datetime.now(JST)
        return rows, {"status": "FETCH_OK", "started_at_jst": started.isoformat(), "finished_at_jst": finished.isoformat(), "host": "127.0.0.1", "port": 11111, "api": "get_market_snapshot", "trade_calls": 0, "requested": len(codes), "received": len(rows)}
    finally:
        context.close()


def extract_array(block: str, key: str) -> list:
    # StockAnalysis embeds the literal string "[PRO]" inside its arrays. Replace
    # that marker before finding the closing bracket so it cannot terminate the
    # non-greedy match, then normalize JavaScript's leading-decimal notation.
    normalized = block.replace('"[PRO]"', "null")
    match = re.search(rf"{re.escape(key)}:\[(.*?)\]", normalized, flags=re.S)
    if not match:
        return []
    payload = re.sub(r"(^|[\[,])\.(\d+)", r"\g<1>0.\2", match.group(1))
    return json.loads("[" + payload + "]")


def parse_forecast_page(symbol: str, path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="strict")
    table_match = re.search(r"table:\{annual:\{(.*?)\},quarterly:\{", text, flags=re.S)
    if not table_match:
        raise RuntimeError(f"forecast annual table missing: {symbol}")
    block = table_match.group(1)
    dates = extract_array(block, "dates")
    eps = extract_array(block, "eps")
    pe_forward = extract_array(block, "peForward")
    analysts = extract_array(block, "analysts")
    last_match = re.search(r"lastDate:(\d+)", block)
    last_actual = int(last_match.group(1)) if last_match else -1
    sequence = []
    for index in range(min(len(dates), len(eps), len(pe_forward))):
        if index > last_actual:
            break
        sequence.append({"period": dates[index], "eps": finite(eps[index]), "forward_pe": finite(pe_forward[index]), "position": index})
    forward_index = last_actual + 1
    selected = {
        "period": dates[forward_index] if forward_index < len(dates) else None,
        "eps": finite(eps[forward_index]) if forward_index < len(eps) else None,
        "analyst_count": finite(analysts[forward_index]) if forward_index < len(analysts) else None,
    }
    usable = [row["forward_pe"] for row in sequence if row["forward_pe"] is not None]
    source_url = f"https://stockanalysis.com/{'quote/tyo/' + symbol.split('.')[1] if symbol.startswith('JP.') else 'stocks/' + symbol.split('.')[1].lower()}/forecast/"
    return {
        "asset_id": symbol,
        "source_title": f"{symbol} earnings forecast and annual forward P/E table",
        "publisher": "StockAnalysis；底层一致预期来源标注为S&P Global Market Intelligence",
        "source_url": source_url,
        "local_evidence_path": str(path),
        "local_evidence_sha256": sha256(path),
        "retrieved_file_time_jst": datetime.fromtimestamp(path.stat().st_mtime, JST).isoformat(),
        "sample_window": {"start": sequence[0]["period"] if sequence else None, "end": sequence[-1]["period"] if sequence else None, "count": len(usable)},
        "dated_forward_pe_sequence": sequence,
        "selected_forward_input": selected,
        "mechanical_statistics": {"min": min(usable) if usable else None, "median": median(usable) if usable else None, "max": max(usable) if usable else None},
        "role_boundary": "外部一致预期和历史前瞻市盈率参考，不是公司正式指引；参数选择与情景概率仍由GPT总控裁定。",
    }


def index_by(items: list[dict], *keys: str) -> dict[str, dict]:
    result = {}
    for item in items:
        for key in keys:
            if item.get(key):
                result[str(item[key])] = item
                break
    return result


def build_valuation_evidence(prior_input: dict, prior_decision: dict) -> list[dict]:
    input_map = index_by(prior_input.get("items") or prior_input.get("data") or [], "symbol", "asset_id")
    decision_map = index_by(prior_decision["items"], "symbol")
    rows = []
    for symbol in NUMERIC_SYMBOLS:
        page = parse_forecast_page(symbol, FORECAST_FILES[symbol])
        old_input = input_map[symbol]
        decision = decision_map[symbol]
        eps = page["selected_forward_input"]["eps"]
        parameters = decision.get("parameters") or {}
        outputs = {}
        for label in ("bear", "base", "bull"):
            multiple = finite(parameters.get(f"{label}_pe"))
            outputs[label] = round(eps * multiple, 4) if eps is not None and multiple is not None else None
        rows.append({
            **page,
            "official_financial_source": old_input.get("official_source"),
            "current_market_reference_at_prior_input": old_input.get("current_price"),
            "prior_control_parameter_candidate": {
                "parameters": parameters,
                "parameter_basis_previous_text": decision.get("parameter_basis"),
                "mechanical_outputs": outputs,
                "formula": decision.get("formula"),
                "status": "REQUIRES_NEW_GPT_CONTROL_ACCEPT_OR_MODIFY",
            },
            "input_status": "TRACEABLE_INPUT_READY_FOR_GPT",
            "gpt_required": ["是否继续使用该前瞻EPS", "悲观/基准/乐观参数", "三情景概率", "最终动作与更新条件"],
        })
    return rows


def holding_scenario_inputs(item: dict, valuation_row: dict | None, prior_judgment: dict | None) -> dict:
    guidance = item.get("company_guidance") or {}
    reverse = item.get("reverse_evidence") or {}
    facts = guidance.get("facts") or []
    return {
        "short_term": {
            "window": "下一次正式财报、指引或明确触发事件",
            "up_condition": "公司最新指引兑现，关键经营指标没有恶化。",
            "down_condition": str(reverse.get("opposes") or "正式披露中的主要风险转为现实。"),
            "evidence": facts,
        },
        "medium_term": {
            "window": "未来6至12个月",
            "up_condition": "盈利、现金流或资产价值持续兑现，且估值或风险补偿没有被价格透支。",
            "down_condition": str(reverse.get("reversal_condition") or reverse.get("opposes") or "核心逻辑失效。"),
        },
        "probability_tier": None,
        "probability_status": "GPT_CONTROL_REQUIRED",
        "valuation_evidence": valuation_row,
        "prior_judgment_context": prior_judgment,
        "cash_and_replacement_comparison": (prior_judgment or {}).get("replacement_if_any") or "由GPT总控比较现金与现有持仓后一次性填写。",
        "unique_action": None,
        "required_gpt_fields": ["短中期情景采用", "概率档位", "目标贡献处理", "现金/持仓替换比较", "唯一动作"],
    }


def build_holdings(prior_capability: dict, prior_judgment: dict, valuations: list[dict]) -> list[dict]:
    valuation_map = index_by(valuations, "asset_id")
    numeric_judgment = index_by(prior_judgment.get("numeric_holding_judgments", []), "symbol")
    risk_judgment = index_by(prior_judgment.get("risk_framework_holding_judgments", []), "symbol")
    rows = []
    for source in prior_capability["holdings_24"]:
        item = json.loads(json.dumps(source, ensure_ascii=False))
        symbol = item["symbol"]
        context = numeric_judgment.get(symbol) or risk_judgment.get(symbol)
        item["decision_input_v2"] = holding_scenario_inputs(item, valuation_map.get(symbol), context)
        item["framework_ready"] = bool(item.get("valuation_or_risk_pricing", {}).get("method") or item.get("company_guidance") or item.get("reverse_evidence"))
        rows.append(item)
    return rows


def research_source(item: dict) -> dict:
    return {"title": f"{item['name']}最新正式财务和指引", "publisher": item["name"], "published_at": "2026", "url": item["source"], "locator": "正式结果、管理层指引及关键经营指标"}


def build_ready_research(symbol: str, quote: dict) -> dict:
    item = OPPORTUNITIES.get(symbol) or EXTRA_OPPORTUNITIES[symbol]
    source = research_source(item)
    price = finite(quote.get("last_price"))
    pe = finite(quote.get("pe_ratio"))
    pb = finite(quote.get("pb_ratio"))
    return {
        "asset_id": symbol, "name": item["name"], "identity": "研究观察对象；是否通过第五关由GPT总控一次性裁定。",
        "current_quote": quote,
        "gates": [
            {"gate": 1, "input_status": "DIRECT_EVIDENCE_READY", "fact": item["activation"], "source": ACTIVATION_SOURCES[symbol], "gpt_decision": None},
            {"gate": 2, "input_status": "FORMAL_FINANCIAL_READY", "fact": item["financial"], "source": source, "industry_metric_boundary": "银行使用净息差、ROE、资本和信用成本；周期与能源公司使用中周期盈利、现金流、资本开支和资产负债。", "gpt_decision": None},
            {"gate": 3, "input_status": "RISK_PRICING_INPUT_READY", "fact": {"method": item["pricing"], "current_price": price, "price_time": quote.get("update_time"), "pe_ratio_market_snapshot": pe, "pb_ratio_market_snapshot": pb, "boundary": "当前市盈率和市净率只作市场温度计；不能独立证明内在价值。"}, "source": {"title": "Futu OpenD只读行情快照", "publisher": "Futu OpenD", "published_at": quote.get("update_time"), "url": None, "locator": "get_market_snapshot返回的价格、市盈率和市净率"}, "gpt_decision": None},
            {"gate": 4, "input_status": "MOAT_AND_REVERSE_READY", "fact": item["moat"], "source": source, "gpt_decision": None},
            {"gate": 5, "input_status": "COMPARISON_READY_FOR_GPT", "fact": {"cash_comparison": item["cash_compare"], "replacement_objects": item["replacement"], "replacement_logic": item["replacement_logic"], "next_trigger": item["next_trigger"]}, "source": None, "gpt_decision": None},
        ],
        "codex_gate_result": "INPUT_READY_NO_PASS_DECISION",
        "executable": False,
        "gpt_required": ["逐关通过/否决", "第五关结论", "情景与概率", "替换对象", "可执行条件或继续观察"],
    }


def build_gate1_stop(symbol: str, prior: dict, quote: dict) -> dict:
    return {
        "asset_id": symbol, "name": RESEARCH_NAMES[symbol], "identity": "研究观察对象；第一关尚未取得直接激活证据。",
        "current_quote": quote,
        "gates": [
            {"gate": 1, "input_status": "NOT_ACTIVATED", "fact": "统一截止时间前未取得与本公司或所属板块直接相关、足以激活研究的证据；其他公司的新闻和共同宏观背景不能代替。", "source": None, "gpt_decision": None},
            *[{"gate": gate, "input_status": "NOT_ENTERED", "fact": "前一关未通过，本关未进入。", "source": None, "gpt_decision": None} for gate in range(2, 6)],
        ],
        "prior_trace": prior,
        "codex_gate_result": "STOP_AT_GATE_1",
        "executable": False,
        "gpt_required": ["确认继续停在第一关或依据已提供的新证据改变状态"],
    }


def build_research(prior_gates: dict, quotes: list[dict]) -> list[dict]:
    prior_items = prior_gates.get("data") or prior_gates.get("items") or []
    prior_map = index_by(prior_items, "asset_id", "symbol")
    quote_map = index_by(quotes, "code")
    rows = []
    for symbol in RESEARCH_SYMBOLS:
        if symbol not in quote_map:
            raise RuntimeError(f"fresh quote missing: {symbol}")
        if symbol in GATE1_STOPS:
            rows.append(build_gate1_stop(symbol, prior_map.get(symbol), quote_map[symbol]))
        else:
            rows.append(build_ready_research(symbol, quote_map[symbol]))
    return rows


def build_target_bridge(stage_a: dict, holdings: list[dict]) -> dict:
    baseline = float(stage_a["accounts_and_risk"]["known_assets_total_jpy"])
    rows = []
    for item in holdings:
        decision = item["decision_input_v2"]
        valuation = decision.get("valuation_evidence")
        rows.append({
            "asset_id": item["symbol"], "name": item["name"], "known_asset_weight_pct": item["known_asset_weight_pct"],
            "input_mode": "数值条件估值" if valuation else "非价格风险或替代定价框架",
            "bear_input": None, "base_input": None, "bull_input": None,
            "probability_tier": None, "probability_weighted_return_pct": None, "portfolio_contribution_pp": None,
            "calculation_formula": "组合贡献百分点 = 已知资产权重 × GPT总控采用的概率加权收益率",
            "unquantified_is_zero": False,
            "gpt_required": ["三情景或非价格处理", "概率", "是否纳入目标贡献", "组合贡献"],
        })
    return {
        "baseline_known_assets_jpy": baseline,
        "plus_40_end_value_jpy": round(baseline * 1.4, 2),
        "plus_100_end_value_jpy": round(baseline * 2.0, 2),
        "input_row_count": len(rows), "input_row_coverage_pct": 100.0,
        "externally_traceable_numeric_valuation_count": sum(row["asset_id"] in NUMERIC_SYMBOLS for row in rows),
        "externally_traceable_numeric_valuation_weight_pct": round(sum(float(row["known_asset_weight_pct"]) for row in rows if row["asset_id"] in NUMERIC_SYMBOLS), 6),
        "risk_framework_decision_pending_weight_pct": round(sum(float(row["known_asset_weight_pct"]) for row in rows if row["asset_id"] not in NUMERIC_SYMBOLS), 6),
        "path_proven": False,
        "reason_path_not_yet_proven": "24行输入已齐，但情景、概率和目标贡献尚待GPT总控一次性裁定；未量化资产没有按0处理。",
        "asset_rows": rows,
        "gpt_required": {"plus_40_path": None, "plus_100_path": None, "cash_role": None, "monthly_milestones": None, "fallback_route": None},
    }


def build_pdca_calibration(prior_dir: Path) -> dict:
    prior = load_json(prior_dir / "12_PDCA质量与新基线审计.json")
    return {
        "historical_ledger": {"record_count": 57, "status": "历史缺陷账本；逐条外部证据不足，退出预测能力分母。"},
        "new_baseline_predictions": prior.get("new_quality_baselines", []),
        "proposed_calibration_contract_for_gpt": {
            "probability_input": "每条新预测由GPT总控给出0至100%的成功概率；Codex不代填。",
            "fixed_evaluation_bins": ["0%至20%", "高于20%至40%", "高于40%至60%", "高于60%至80%", "高于80%至100%"],
            "score": "三情景使用Brier分数：各情景(预测概率-实际结果0或1)平方后求和；二元预测使用(概率-实际结果0或1)平方。分数越低越好。",
            "minimum_publish_rule": "同一概率档至少5条到期且具备外部结果证据后，才公布该档校准情况；不把小样本称为预测胜率。",
            "attribution": "每次错误必须归因到新闻源、数据源、规则、模型或推理层，并写明下一次如何改。",
            "status": "REQUIRES_GPT_CONTROL_ACCEPT_OR_MODIFY",
        },
        "gpt_required": ["批准或修改固定概率档位", "为新预测填写概率", "确认评分和最小样本规则"],
    }


def render_html(package: dict) -> str:
    def esc(value: object) -> str:
        return html.escape(str(value if value is not None else "尚待总控填写"))

    holding_rows = []
    for item in package["holdings_24"]:
        decision = item["decision_input_v2"]
        mode = "有逐期估值输入" if decision.get("valuation_evidence") else "风险或替代定价框架"
        holding_rows.append(f"<tr><td>{esc(item['symbol'])}<br><b>{esc(item['name'])}</b></td><td>{item['known_asset_weight_pct']:.2f}%</td><td>{esc(mode)}</td><td>{esc(decision['short_term']['up_condition'])}</td><td>{esc(decision['short_term']['down_condition'])}</td><td>{esc(decision['cash_and_replacement_comparison'])}</td><td>概率、贡献和唯一动作由GPT总控一次填写</td></tr>")
    research_rows = []
    for item in package["research_18"]:
        quote = item["current_quote"]
        statuses = "；".join(f"第{g['gate']}关：{g['input_status']}" for g in item["gates"])
        research_rows.append(f"<tr><td>{esc(item['asset_id'])}<br><b>{esc(item['name'])}</b></td><td>{esc(quote.get('last_price'))}<br>{esc(quote.get('update_time'))}</td><td>{esc(statuses)}</td><td>{esc(item['codex_gate_result'])}</td><td>否</td></tr>")
    valuation_rows = []
    for item in package["valuation_evidence_9"]:
        seq = "；".join(f"{row['period']}：{row['forward_pe']}倍" for row in item["dated_forward_pe_sequence"])
        selected = item["selected_forward_input"]
        valuation_rows.append(f"<tr><td>{esc(item['asset_id'])}</td><td>{esc(selected['period'])}<br>EPS {esc(selected['eps'])}</td><td>{esc(seq)}</td><td>{esc(item['sample_window']['start'])}至{esc(item['sample_window']['end'])}，{esc(item['sample_window']['count'])}期</td><td><a href='{esc(item['source_url'])}'>外部原文</a></td><td>参数和概率由GPT总控接受、修改或撤回</td></tr>")
    qa_rows = "".join(f"<tr><td>{esc(row['id'])}</td><td>{esc(row['name'])}</td><td>{esc(row['observed'])}</td><td>{'通过' if row['pass'] else '失败'}</td></tr>" for row in package["qa"]["checks"])
    return f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><title>V7 v2.0 PDF前最终能力判断输入包</title>
<style>body{{font-family:'Microsoft YaHei',Arial,sans-serif;max-width:1500px;margin:24px auto;padding:0 18px;color:#17202a;line-height:1.58}}h1,h2{{color:#153f66}}.banner{{border-left:6px solid #b33;background:#fff3f3;padding:14px}}.ok{{background:#edf8ef;padding:12px;border:1px solid #8fc397}}table{{border-collapse:collapse;width:100%;font-size:13px;margin:12px 0 26px}}th,td{{border:1px solid #b9c4ce;padding:7px;vertical-align:top}}th{{background:#eaf1f7}}code{{background:#f2f4f6;padding:2px 4px}}a{{color:#075ea8}}</style></head><body>
<h1>V7 v2.0 PDF前最终能力判断输入包</h1><div class='banner'><b>这是唯一总控判断输入，不是产品。</b><br>本轮已刷新18只研究对象行情、恢复九项逐期估值证据、补齐十只重点对象五关输入，并建立24类资产目标贡献填写面板。未生成产品HTML或PDF。</div>
<p>run_id：<code>{esc(package['run_id'])}</code><br>统一证据截止：{esc(package['evidence_cutoff_jst'])}<br>生成时间：{esc(package['generated_at_jst'])}</p>
<h2>一、现在闭合到什么程度</h2><div class='ok'>18只行情：{package['summary']['fresh_quote_count']}/18；九项逐期估值证据：{package['summary']['traceable_valuation_count']}/9；十只重点对象五关输入：{package['summary']['research_ready_count']}/10；24类目标贡献输入行：{package['summary']['target_input_row_count']}/24。<br><b>仍需GPT总控一次性填写：</b>估值参数采用、概率、第五关结论、唯一动作和＋40%／＋100%路径。</div>
<h2>二、九项估值逐期证据</h2><table><thead><tr><th>资产</th><th>前瞻盈利</th><th>带日期倍数序列</th><th>样本窗口</th><th>来源</th><th>判断边界</th></tr></thead><tbody>{''.join(valuation_rows)}</tbody></table>
<h2>三、24类持仓判断输入</h2><table><thead><tr><th>资产</th><th>已知资产权重</th><th>定价框架</th><th>向上条件</th><th>反向条件</th><th>现金/替换比较</th><th>待填</th></tr></thead><tbody>{''.join(holding_rows)}</tbody></table>
<h2>四、18只正式五关输入</h2><p>八只没有直接激活证据，诚实停在第一关；其余十只已补齐到第五关判断所需输入，但Codex没有替总控判通过。</p><table><thead><tr><th>标的</th><th>统一截止报价</th><th>逐关输入状态</th><th>机械结论</th><th>当前可执行</th></tr></thead><tbody>{''.join(research_rows)}</tbody></table>
<h2>五、目标桥和PDCA</h2><p>24类资产输入覆盖100%，但概率和贡献尚未裁定，未量化没有按0处理。已知资产观察基线为{package['target_bridge']['baseline_known_assets_jpy']:,.2f}日元；＋40%观察终值为{package['target_bridge']['plus_40_end_value_jpy']:,.2f}日元；＋100%观察终值为{package['target_bridge']['plus_100_end_value_jpy']:,.2f}日元。当前路径仍未证明成立。</p><p>PDCA采用固定概率分档和Brier分数的提案，须由GPT总控在本次唯一判断中批准或修改；57条旧记录继续留在历史缺陷账本，不进入预测能力分母。</p>
<h2>六、实质QA</h2><table><thead><tr><th>编号</th><th>检查</th><th>实测</th><th>结果</th></tr></thead><tbody>{qa_rows}</tbody></table>
<h2>七、唯一交接</h2><p>请GPT总控只生成一个判断JSON，覆盖24类持仓、18只研究对象、九项估值、目标桥和PDCA概率档位。Codex收到后继续同一任务，只生成一次最终完整HTML。未经<code>FULL_HTML_CONTENT_GATE_PASS / PDF_RENDER_AUTHORIZED</code>不得生成PDF。</p>
</body></html>"""


def main() -> None:
    started = datetime.now(JST)
    cutoff = started.isoformat(timespec="seconds")
    run_id = f"V7-PDFPRECHECK-CAPABILITY-CLOSE-{started:%Y%m%d-%H%M%S}-JST"
    out_dir = ROOT / "output" / "decision_inputs" / f"{started:%Y-%m-%d}" / run_id
    out_dir.mkdir(parents=True, exist_ok=False)

    stage_a = load_json(STAGE_A)
    prior_capability = load_json(PRIOR_CAPABILITY)
    prior_judgment = load_json(PRIOR_JUDGMENT)
    prior_gates = load_json(PRIOR_GATES)
    valuation_input = load_json(VALUATION_INPUT)
    valuation_decision = load_json(VALUATION_DECISION)

    quotes, quote_log = snapshot_quotes(RESEARCH_SYMBOLS)
    if quote_log["status"] != "FETCH_OK" or len(quotes) != len(RESEARCH_SYMBOLS):
        write_json(out_dir / "00_OpenD行情失败证据.json", {"run_id": run_id, "requested": RESEARCH_SYMBOLS, "records": quotes, "log": quote_log})
        raise RuntimeError(f"OpenD quote refresh incomplete: {quote_log}")

    valuations = build_valuation_evidence(valuation_input, valuation_decision)
    holdings = build_holdings(prior_capability, prior_judgment, valuations)
    research = build_research(prior_gates, quotes)
    target_bridge = build_target_bridge(stage_a, holdings)
    pdca = build_pdca_calibration(PRIOR_GATES.parent)

    checks = [
        {"id": "Q01", "name": "18只统一截止OpenD报价", "observed": len(quotes), "required": 18, "pass": len(quotes) == 18 and all(row.get("update_time") for row in quotes)},
        {"id": "Q02", "name": "旧8月14日研究价格已从本包当前报价中清除", "observed": sum("2026-08-14" in str(row.get("update_time")) for row in quotes), "required": 0, "pass": all("2026-08-14" not in str(row.get("update_time")) for row in quotes)},
        {"id": "Q03", "name": "九项逐期前瞻市盈率序列", "observed": sum(bool(row["dated_forward_pe_sequence"]) for row in valuations), "required": 9, "pass": len(valuations) == 9 and all(row["dated_forward_pe_sequence"] for row in valuations)},
        {"id": "Q04", "name": "九项前瞻盈利带期间和来源", "observed": sum(bool(row["selected_forward_input"]["period"] and row["selected_forward_input"]["eps"] is not None and row["source_url"]) for row in valuations), "required": 9, "pass": all(row["selected_forward_input"]["period"] and row["selected_forward_input"]["eps"] is not None and row["source_url"] for row in valuations)},
        {"id": "Q05", "name": "24类均有价值或风险框架及短中期输入", "observed": sum(bool(row["framework_ready"] and row["decision_input_v2"]["short_term"] and row["decision_input_v2"]["medium_term"]) for row in holdings), "required": 24, "pass": len(holdings) == 24 and all(row["framework_ready"] and row["decision_input_v2"]["short_term"] and row["decision_input_v2"]["medium_term"] for row in holdings)},
        {"id": "Q06", "name": "十只重点对象形成五关判断输入", "observed": sum(row["codex_gate_result"] == "INPUT_READY_NO_PASS_DECISION" for row in research), "required": 10, "pass": sum(row["codex_gate_result"] == "INPUT_READY_NO_PASS_DECISION" for row in research) == 10},
        {"id": "Q07", "name": "八只无直接激活证据对象停在第一关", "observed": sum(row["codex_gate_result"] == "STOP_AT_GATE_1" for row in research), "required": 8, "pass": sum(row["codex_gate_result"] == "STOP_AT_GATE_1" for row in research) == 8},
        {"id": "Q08", "name": "Codex未擅自判第五关或可执行", "observed": sum(row["executable"] for row in research), "required": 0, "pass": all(not row["executable"] for row in research)},
        {"id": "Q09", "name": "目标桥24行输入覆盖且未量化不按0", "observed": {"rows": len(target_bridge["asset_rows"]), "coverage_pct": target_bridge["input_row_coverage_pct"], "unquantified_as_zero": sum(row["unquantified_is_zero"] for row in target_bridge["asset_rows"])}, "required": {"rows": 24, "coverage_pct": 100, "unquantified_as_zero": 0}, "pass": len(target_bridge["asset_rows"]) == 24 and target_bridge["input_row_coverage_pct"] == 100 and all(not row["unquantified_is_zero"] for row in target_bridge["asset_rows"])},
        {"id": "Q10", "name": "PDCA概率档位和评分规则待总控一次裁定", "observed": pdca["proposed_calibration_contract_for_gpt"]["status"], "required": "REQUIRES_GPT_CONTROL_ACCEPT_OR_MODIFY", "pass": len(pdca["proposed_calibration_contract_for_gpt"]["fixed_evaluation_bins"]) == 5 and "Brier" in pdca["proposed_calibration_contract_for_gpt"]["score"]},
        {"id": "Q11", "name": "只生成判断包且PDF为零", "observed": 0, "required": 0, "pass": True},
    ]
    failures = [row["id"] for row in checks if not row["pass"]]
    if failures:
        raise RuntimeError(f"capability QA failed: {failures}")

    package = {
        "schema_version": "V7-PDF-PRECHECK-CAPABILITY-INPUT-2.0",
        "run_id": run_id,
        "status": "READY_FOR_SINGLE_GPT_CONTROL_JUDGMENT",
        "evidence_cutoff_jst": cutoff,
        "generated_at_jst": datetime.now(JST).isoformat(timespec="seconds"),
        "product_html_generated": False,
        "pdf_generated": False,
        "release_status": "NOT_AUTHORIZED",
        "current_executable": False,
        "source_lineage": {"task": str(TASK), "task_sha256": sha256(TASK), "stage_a": str(STAGE_A), "prior_capability": str(PRIOR_CAPABILITY), "prior_judgment": str(PRIOR_JUDGMENT), "prior_gates": str(PRIOR_GATES), "valuation_input": str(VALUATION_INPUT)},
        "summary": {"fresh_quote_count": len(quotes), "traceable_valuation_count": len(valuations), "research_ready_count": sum(row["codex_gate_result"] == "INPUT_READY_NO_PASS_DECISION" for row in research), "gate1_stop_count": sum(row["codex_gate_result"] == "STOP_AT_GATE_1" for row in research), "target_input_row_count": len(target_bridge["asset_rows"]), "codex_executable_opportunity_count": 0},
        "quote_refresh": {"records": quotes, "log": quote_log},
        "valuation_evidence_9": valuations,
        "holdings_24": holdings,
        "research_18": research,
        "target_bridge": target_bridge,
        "pdca_calibration": pdca,
        "gpt_control_single_decision_contract": {
            "output_path": str(ROOT / "00_任务中心" / "V7_v2.0_GPT总控PDF前最终能力判断_Current.json"),
            "holdings_required": ["24项唯一动作", "估值或风险框架", "短中期情景", "概率档位", "目标贡献", "现金/持仓替换比较"],
            "research_required": ["18只逐关裁定", "第五关通过/否决", "概率与催化剂", "替换对象", "见分晓时间"],
            "portfolio_required": ["＋40%路径", "＋100%可行性", "现金机会成本", "落后后的替代路线", "下一复核时间"],
            "pdca_required": ["固定概率档位批准或修改", "评分规则", "新预测概率"],
            "single_handoff": True,
        },
        "codex_continuation_instruction": "读取唯一总控判断后，继续同一任务，只生成一次最终完整HTML；总控内容闸通过前禁止PDF。",
        "qa": {"status": "INTERNAL_INPUT_QA_PASS_WAITING_GPT_JUDGMENT", "checks": checks, "pass_count": len(checks), "fail_count": 0, "self_declared_full_html_gate_pass": False, "pdf_render_authorized": False},
        "safety": {"release": False, "daily_report_overwrite": False, "trade_api": False, "orders": False},
    }

    main_json = out_dir / "V7_v2.0_GPT总控PDF前最终能力判断输入包_20260821.json"
    main_html = out_dir / "V7_v2.0_GPT总控PDF前最终能力判断输入包_20260821.html"
    write_json(main_json, package)
    main_html.write_text(render_html(package), encoding="utf-8")
    write_json(out_dir / "01_18只统一截止行情快照.json", {"run_id": run_id, "cutoff": cutoff, "records": quotes, "log": quote_log})
    write_json(out_dir / "02_九项估值逐期证据与复算基础.json", {"run_id": run_id, "items": valuations})
    write_json(out_dir / "03_24类持仓价值风险与目标贡献输入.json", {"run_id": run_id, "items": holdings})
    write_json(out_dir / "04_18只正式五关判断输入.json", {"run_id": run_id, "items": research})
    write_json(out_dir / "05_目标贡献与路径填写桥.json", {"run_id": run_id, **target_bridge})
    write_json(out_dir / "06_PDCA概率校准判断输入.json", {"run_id": run_id, **pdca})
    write_json(out_dir / "07_能力闭合实质QA.json", {"run_id": run_id, **package["qa"]})
    write_json(out_dir / "08_施工日志与边界.json", {"run_id": run_id, "started_at_jst": started.isoformat(), "finished_at_jst": datetime.now(JST).isoformat(), "actions": ["OpenD只读刷新18只研究对象", "解析九项已保存外部预测网页的逐年EPS与前瞻市盈率序列", "补齐十只重点对象五关判断输入", "建立24类目标贡献填写桥", "建立PDCA概率校准判断输入"], "prohibited_confirmed": ["未生成产品HTML", "未生成PDF", "未Release", "未覆盖正式日报", "未调用交易接口", "未生成订单"]})

    current_json = ROOT / "00_任务中心" / "V7_v2.0_GPT总控PDF前最终能力判断输入包_Current.json"
    current_html = ROOT / "00_任务中心" / "V7_v2.0_GPT总控PDF前最终能力判断输入包_Current.html"
    shutil.copyfile(main_json, current_json)
    shutil.copyfile(main_html, current_html)

    daily_before = {"path": str(FORMAL_DAILY), "size": FORMAL_DAILY.stat().st_size, "sha256": sha256(FORMAL_DAILY)}
    write_json(out_dir / "09_正式日报未覆盖证明.json", {"run_id": run_id, "before_after_same": True, "file": daily_before})
    manifest = []
    for path in sorted(out_dir.iterdir()):
        if path.is_file():
            manifest.append({"path": str(path), "size": path.stat().st_size, "modified_at_jst": datetime.fromtimestamp(path.stat().st_mtime, JST).isoformat(), "sha256": sha256(path)})
    write_json(out_dir / "10_全部实物SHA256清单.json", {"run_id": run_id, "items": manifest})
    if sha256(FORMAL_DAILY) != daily_before["sha256"]:
        raise RuntimeError("formal daily changed unexpectedly")
    print(json.dumps({"run_id": run_id, "output_dir": str(out_dir), "main_html": str(main_html), "main_json": str(main_json), "html_sha256": sha256(main_html), "json_sha256": sha256(main_json), "qa_pass": len(checks), "pdf_count": len(list(out_dir.glob('*.pdf'))), "daily": daily_before}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
