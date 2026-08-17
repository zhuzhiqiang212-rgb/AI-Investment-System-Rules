from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
V05_DIR = ROOT / "output/candidates/2026-08-17/V7-V05-COMPLETE-20260817-080933-JST"
HOLDINGS_V05 = V05_DIR / "04_更新后的24类持仓矩阵_20260817.json"
CANDIDATES_V05 = V05_DIR / "05_更新后的21只五关轨迹_20260817.json"
CRITICAL_DIR = ROOT / "output/decision_inputs/2026-08-17/V7-V04-CRITICAL-EVIDENCE-20260817-003853-JST"
HOLDINGS_SOURCE = CRITICAL_DIR / "02_24类持仓业务判断输入_20260817.json"
CANDIDATES_SOURCE = CRITICAL_DIR / "03_21只候选五关输入_20260817.json"
VAL_INPUTS = ROOT / "data/valuation/val_inputs.json"
SCAN_GATE = ROOT / "data/screen/gate_20260811.json"
DAILY = ROOT / "00_请先看这里/00_今日日报.pdf"

V05_HTML_SHA = "6521DDEE6F6885F8799A6E4F135ED3AA9A375CB4970D2406027091225BEB7D29"
V05_PDF_SHA = "E6B467B8E24588389A0F98E923D44366CA127C5D510945C1169D80C87055D898"
DAILY_SHA = "12C8CB2CF5879C37F2876FEEF8CB6144A3AED6A5D48D89A06A140F2A234DB7FA"

SAMSUNG_Q2_URL = "https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2026_2Q_conference_eng.pdf"
SAMSUNG_FY_URL = "https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2025_4Q_conference_eng.pdf"
SAMSUNG_FY_NEWS = "https://news.samsung.com/nl/samsung-electronics-announces-fourth-quarter-and-fy-2025-results"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def esc(value) -> str:
    if value is None:
        return "未取得"
    return html.escape(str(value))


def num(value, digits=2) -> str:
    if value is None:
        return "未取得"
    return f"{value:,.{digits}f}"


def link(url: str | None, label="正式原文") -> str:
    return f'<a href="{esc(url)}">{esc(label)}</a>' if url else "未取得"


def extract_ratio(text: str, label: str) -> float | None:
    match = re.search(rf"{re.escape(label)}=([-\d.]+)", text or "")
    return float(match.group(1)) if match else None


def holding_price(item: dict) -> tuple[float | None, str | None, str | None]:
    facts = item.get("account_coverage") or []
    if not facts:
        return None, None, None
    facts = sorted(facts, key=lambda x: (bool(x.get("production_day_data")), x.get("data_date") or ""), reverse=True)
    fact = facts[0]
    return fact.get("latest_price"), fact.get("data_date"), fact.get("currency")


HOLDING_SCENARIOS = {
    "US.NVDA": ("EPS", 8.50, (20, 26, 32), "FY27非GAAP EPS历史锁定输入；须在下一次财报后更新"),
    "US.MSFT": ("EPS", 19.09, (18, 22, 26), "FY27 EPS历史锁定输入；2026财年结果后需复核"),
    "JP.4568": ("EPS", 165.0, (18, 20, 24), "前瞻EPS历史锁定输入；管线兑现决定倍数"),
    "JP.9984": ("NAV", 7026.0, (0.60, 0.80, 1.00), "2026-03-31保守NAV/股；倍数表示NAV兑现比例"),
    "JP.6857": ("中周期EPS", 220.2, (16, 20, 24), "FY22-FY26含峰含谷平均EPS；周期台阶仍待总控判断"),
    "US.TSM": ("ADR前瞻EPS", 18.0, (18, 23.5, 27), "FY26E ADR EPS历史锁定输入；不是公司正式指引"),
    "JP.8766": ("BVPS", 4303.0, (1.4, 1.7, 2.0), "IFRS每股净资产历史输入；保险公司用P/B和ROE交叉"),
    "US.AVGO": ("非GAAP EPS", 11.62, (25, 32, 40), "FY2026非GAAP共识历史输入；须与最新财报更新"),
    "US.META": ("规范化EPS", 28.0, (18, 23, 28), "剔除一次性税项后的历史规范化输入"),
    "JP.6758": ("前瞻EPS", 207.0, (16, 20, 24), "次年共识历史输入；持续经营与拆分口径必须并列"),
    "JP.7974": ("指引隐含EPS", 271.0, (16, 20, 24), "FY2027公司指引隐含EPS历史输入"),
    "JP.7203": ("中周期EPS", 300.0, (8, 10, 12), "FY22-FY25完整均值输入；含汇率高低年"),
    "US.IBKR": ("正常化EPS", 2.50, (18, 22, 26), "四季度GAAP EPS合成的历史正常化输入"),
    "US.MSTR": ("每股BTC净值", 93.0, (0.8, 1.0, 1.2), "2026-07-15历史mNAV输入；BTC价格与融资结构变化后失效"),
    "US.COIN": ("中周期EPS", 3.39, (15, 22, 30), "FY2021-FY2025简单均值；周期极端，仅供总控比较"),
}


CANDIDATE_MULTIPLES = {
    "US.MU": ("P/E", (14, 20, 26), (0.80, 1.00, 1.20)),
    "US.NVDA": ("P/E", (25, 35, 45), (0.85, 1.00, 1.15)),
    "US.AVGO": ("P/E", (22, 30, 38), (0.85, 1.00, 1.15)),
    "US.TSM": ("P/E", (18, 23, 28), (0.85, 1.00, 1.15)),
    "US.PLTR": ("P/E", (35, 50, 70), (0.75, 1.00, 1.25)),
    "US.ON": ("P/E", (12, 18, 24), (0.75, 1.00, 1.25)),
    "US.VRT": ("P/E", (24, 32, 40), (0.80, 1.00, 1.20)),
    "US.ETN": ("P/E", (20, 26, 32), (0.85, 1.00, 1.15)),
    "US.CEG": ("P/E", (16, 22, 28), (0.80, 1.00, 1.20)),
    "US.NRG": ("P/E", (12, 17, 22), (0.80, 1.00, 1.20)),
    "US.COHR": ("P/E", (16, 23, 30), (0.75, 1.00, 1.25)),
    "US.CRDO": ("P/E", (28, 42, 56), (0.75, 1.00, 1.25)),
    "US.WDC": ("P/E", (12, 18, 24), (0.75, 1.00, 1.25)),
    "US.ASML": ("P/E", (24, 34, 44), (0.85, 1.00, 1.15)),
    "US.XOM": ("P/E", (10, 14, 18), (0.80, 1.00, 1.20)),
    "US.CVX": ("P/E", (10, 14, 18), (0.80, 1.00, 1.20)),
    "JP.8306": ("P/B", (1.0, 1.3, 1.6), (0.95, 1.00, 1.05)),
    "JP.8316": ("P/B", (0.9, 1.2, 1.5), (0.95, 1.00, 1.05)),
    "JP.8411": ("P/B", (0.9, 1.2, 1.5), (0.95, 1.00, 1.05)),
}


MANUAL_FLAGS = {
    "KRX.005930": ["两套期间必须并列：2026Q2与2025FY均为K-IFRS合并，不能相互替换", "归母利润71.3万亿与合并净利润71.6万亿必须分列"],
    "US.SNDK": ["营业利润率、净利率和经营现金流率极高，虽有SEC直链仍须复核期间及一次性项目；估值继续阻断"],
    "US.PLTR": ["收入和利润为季度，经营现金流和自由现金流可能为累计口径；不得直接算单季现金流率"],
    "US.ON": ["收入和利润为季度，现金流为上半年；期间已标注但不可直接求单季现金流率"],
    "US.ETN": ["收入和利润为季度，现金流为上半年；营业利润未取得"],
    "US.CEG": ["收入和利润为季度，现金流为上半年"],
    "US.COHR": ["10-K未单列传统营业利润；自由现金流为机械计算且为负"],
    "US.LITE": ["巨额一次性非现金债务清偿损失导致净亏损；现金流未取得，估值阻断"],
    "US.XOM": ["原卡将税前利润放入营业利润栏，字段标签错误，必须撤回该营业利润值"],
    "JP.8306": ["银行经营现金流不适合作为普通工业公司的自由现金流估值输入"],
    "JP.8316": ["银行经营现金流不适合作为普通工业公司的自由现金流估值输入"],
    "JP.8411": ["经营现金流0.0按项目纪律视为缺失；银行也不以普通FCF口径估值"],
    "JP.6758": ["归母净利润受持续经营/终止经营与拆分会计影响，必须与持续经营利润并列"],
    "US.MSTR": ["公允价值变化使营业利润和净利润不能用于传统P/E估值"],
    "US.SPCX": ["IPO及融资可能使现金余额与经营规模失去可比性"],
}


def core_numbers(item: dict) -> dict:
    if "formal_core_numbers" in item:
        x = item.get("formal_core_numbers") or {}
        return {
            "period": x.get("period"), "revenue": x.get("revenue"),
            "operating_profit": x.get("operating_profit"), "net_income": x.get("net_income"),
            "ocf": x.get("ocf"), "fcf": x.get("fcf"), "currency": x.get("currency"),
            "source": x.get("url") or (item.get("official_evidence") or {}).get("url"),
        }
    return {
        "period": item.get("latest_formal_financial_period"), "revenue": item.get("revenue"),
        "operating_profit": item.get("operating_profit"),
        "net_income": item.get("net_income_attributable_or_net_income"),
        "ocf": item.get("operating_cash_flow"), "fcf": item.get("free_cash_flow"),
        "currency": (item.get("formal_financial_detail") or {}).get("currency"),
        "source": item.get("evidence_url") or (item.get("official_evidence") or {}).get("url"),
    }


def financial_audit_row(scope: str, item: dict) -> dict:
    n = core_numbers(item)
    revenue = n.get("revenue")
    op = n.get("operating_profit")
    net = n.get("net_income")
    ocf = n.get("ocf")
    flags = list(MANUAL_FLAGS.get(item["code"], []))
    if revenue and op is not None and abs(op / revenue) > 0.60:
        flags.append(f"营业利润/收入={op / revenue:.1%}，超过60%异常复核阈值")
    if revenue and net is not None and abs(net / revenue) > 0.60:
        flags.append(f"净利润/收入={net / revenue:.1%}，超过60%异常复核阈值")
    if revenue and ocf is not None and abs(ocf / revenue) > 1.0:
        flags.append(f"经营现金流/收入={ocf / revenue:.1%}，需核对累计期间或一次性资金流")
    if ocf == 0:
        flags.append("经营现金流为0.0，按项目纪律转为缺失")
    source = n.get("source")
    direct = bool(source and ("sec.gov/Archives" in source or "edinet-fsa.go.jp/WZEK0040" in source or "samsung.com" in source or "investor" in source or "investors" in source or "ourbrand.asml.com" in source or "chevron.com/newsroom" in source or "westerndigital.com" in source))
    if item["code"] in {"BTC", "ETH"}:
        status = "NOT_APPLICABLE_ASSET"
    elif item["code"] in {"US.SNDK", "US.LITE", "US.XOM"}:
        status = "REQUIRES_FIELD_OR_PERIOD_REPAIR"
    elif flags:
        status = "VERIFIED_WITH_EXPLICIT_LIMITS"
    else:
        status = "MECHANICAL_CHECK_PASS" if direct else "SOURCE_REVIEW_REQUIRED"
    return {
        "scope": scope, "code": item["code"], "name": item.get("name"), "period": n.get("period"),
        "consolidation": "按来源登记；日股/三星明确为合并，SEC项目依申报主体",
        "currency": n.get("currency"), "revenue": revenue, "operating_profit": op,
        "net_income": net, "operating_cash_flow": ocf, "free_cash_flow": n.get("fcf"),
        "source_url": source, "direct_formal_source": direct, "flags": flags, "status": status,
        "mechanical_only": True,
    }


def scenario_values(metric_value: float, multiples, factors=(1.0, 1.0, 1.0)) -> list[dict]:
    labels = ("悲观", "基准", "乐观")
    result = []
    for label, multiple, factor in zip(labels, multiples, factors):
        adjusted = metric_value * factor
        result.append({
            "scenario": label, "metric_value": round(adjusted, 6), "multiple": multiple,
            "valuation_per_share": round(adjusted * multiple, 2),
        })
    return result


def build_holding_valuations(v05_items: list[dict], source_items: list[dict], val_inputs: dict, market: dict) -> list[dict]:
    source_map = {x["code"]: x for x in source_items}
    val_map = val_inputs.get("holdings") or {}
    rows = []
    for item in v05_items:
        code = item["code"]
        source = source_map.get(code, {})
        price, price_date, currency = holding_price(item)
        detail = source.get("formal_financial_detail") or {}
        cash = source.get("cash")
        debt = source.get("debt_and_financing_obligations")
        market_cap = (market.get(code) or {}).get("market_val_native")
        row = {
            "code": code, "name": item.get("name"), "current_price": price, "price_date": price_date,
            "currency": currency, "market_cap": market_cap,
            "cash": cash, "debt": debt, "net_cash_or_debt": (cash - debt) if cash is not None and debt is not None else None,
            "formal_source": source.get("evidence_url") or item.get("financial_source"),
            "financial_period": source.get("latest_formal_financial_period") or item.get("financial_period"),
            "observation_line_separated": True,
            "observation_line_note": "v0.5现价乘80%/85%只作风险观察触发线，不是内在价值。",
            "final_judgment_by_gpt_control": True,
        }
        spec = HOLDING_SCENARIOS.get(code)
        if spec:
            metric_name, metric_value, multiples, basis = spec
            row.update({
                "status": "VALUATION_INPUT_AVAILABLE_WITH_LIMITS",
                "method": metric_name + "×倍数情景",
                "one_year_metric": {"name": metric_name, "value": metric_value, "basis": basis},
                "multiple_options_for_gpt": list(multiples),
                "scenarios": scenario_values(metric_value, multiples),
                "data_gap_impact": "输入有历史锁定日或共识口径；总控必须决定是否更新及采用哪个倍数。",
                "legacy_input_path": str(VAL_INPUTS),
                "legacy_input_excerpt": val_map.get(code),
            })
        else:
            row.update({
                "status": "CANNOT_FORM_RELIABLE_VALUATION",
                "method": item.get("valuation_method"), "one_year_metric": None,
                "multiple_options_for_gpt": None, "scenarios": [],
                "data_gap_impact": "缺可核远期每股盈利、净值、股本或统一口径；不得用现价折扣冒充内在价值。",
            })
        if code in {"KRX.005930", "US.SNDK", "US.SPCX", "BTC", "ETH", "US.CRCL"}:
            row["status"] = "CANNOT_FORM_RELIABLE_VALUATION"
            row["scenarios"] = []
            row["multiple_options_for_gpt"] = None
        rows.append(row)
    return rows


def build_candidate_valuations(v05_items: list[dict], source_items: list[dict], market: dict) -> list[dict]:
    source_map = {x["code"]: x for x in source_items}
    rows = []
    blocked = {"US.SNDK", "US.LITE"}
    for item in v05_items:
        code = item["code"]
        price = (item.get("price_and_time") or {}).get("price")
        price_time = (item.get("price_and_time") or {}).get("time")
        gate3 = next((x.get("input", "") for x in item.get("five_gates", []) if x.get("gate") == 3), "")
        pe = extract_ratio(gate3, "市盈率")
        pb = extract_ratio(gate3, "市净率")
        source = source_map.get(code, {})
        core = source.get("formal_core_numbers") or {}
        spec = CANDIDATE_MULTIPLES.get(code)
        row = {
            "code": code, "name": item.get("name"), "current_price": price, "price_time": price_time,
            "market_cap": (market.get(code) or {}).get("market_val_native"),
            "formal_source": core.get("url") or (source.get("official_evidence") or {}).get("url") or (item.get("evidence") or {}).get("url"),
            "financial_period": core.get("period"), "current_pe": pe, "current_pb": pb,
            "observation_line_separated": True,
            "fifth_gate_decision": "FIFTH_GATE_INPUT_ONLY_NOT_PASSED",
            "final_judgment_by_gpt_control": True,
        }
        if code in blocked or not spec or not price:
            row.update({
                "status": "CANNOT_FORM_RELIABLE_VALUATION",
                "method": None, "one_year_metric": None, "multiple_options_for_gpt": None,
                "scenarios": [], "gap": "正式远期指标或财务口径不足；第五关证据不足，不能通过。",
            })
        else:
            method, multiples, factors = spec
            denominator = pe if method == "P/E" else pb
            if denominator is None or denominator <= 0:
                row.update({
                    "status": "CANNOT_FORM_RELIABLE_VALUATION", "method": method,
                    "one_year_metric": None, "multiple_options_for_gpt": list(multiples), "scenarios": [],
                    "gap": "扫描时点倍数无效，无法反推出可比较的每股指标。",
                })
            else:
                implied = price / denominator
                row.update({
                    "status": "ILLUSTRATIVE_INPUT_FOR_GPT_NOT_VALUE_JUDGMENT",
                    "method": method,
                    "one_year_metric": {
                        "name": "市场隐含TTM EPS" if method == "P/E" else "市场隐含BVPS",
                        "value": round(implied, 6),
                        "basis": f"扫描价格÷扫描时点{method}；不是公司指引或正式远期共识",
                    },
                    "scenario_metric_factors": list(factors),
                    "multiple_options_for_gpt": list(multiples),
                    "scenarios": scenario_values(implied, multiples, factors),
                    "gap": "缺公司正式远期每股指标；三情景仅供总控选择和反算，不构成第五关通过。",
                })
        if code == "US.XOM":
            row["gap"] += " 原卡把税前利润标成营业利润，须先撤回该字段。"
        rows.append(row)
    return rows


def samsung_report(now: str, run_id: str) -> dict:
    return {
        "run_id": run_id, "generated_at": now, "status": "PERIOD_COMPARISON_CLARIFIED_WITH_FIELD_LABEL_FIX",
        "conclusion": "171.5万亿收入和89.5万亿营业利润来自2026年第二季度K-IFRS合并实际业绩，不是2025全年。v0.5期间标签本身为2026Q2；总控以2025全年333.6/43.6直接替换Q2数字会造成另一种期间错配。必须并列两期。",
        "source_trace": [
            {"value": "171.5万亿韩元", "origin": "2026Q2合并Sales", "page": 12, "unit": "KRW trillion", "status": "SOURCE_CONFIRMED"},
            {"value": "89.5万亿韩元", "origin": "2026Q2合并Operating profit", "page": 12, "unit": "KRW trillion", "status": "SOURCE_CONFIRMED"},
            {"value": "71.3万亿韩元", "origin": "2026Q2 Profit attributable to owners of the parent", "page": 12, "unit": "KRW trillion", "status": "LABEL_AS_ATTRIBUTABLE_PROFIT"},
        ],
        "periods": {
            "2026Q2": {
                "period": "2026-04-01至2026-06-30", "basis": "K-IFRS合并", "source_url": SAMSUNG_Q2_URL,
                "fields": {
                    "revenue": {"k_ifrs_label": "Sales", "raw": 171.5, "unit": "KRW trillion", "converted_krw": 171_500_000_000_000},
                    "operating_profit": {"k_ifrs_label": "Operating profit", "raw": 89.5, "unit": "KRW trillion", "converted_krw": 89_500_000_000_000},
                    "net_profit": {"k_ifrs_label": "Net profit", "raw": 71.6, "unit": "KRW trillion", "converted_krw": 71_600_000_000_000},
                    "profit_attributable_to_owners": {"k_ifrs_label": "Profit attributable to owners of the parent", "raw": 71.3, "unit": "KRW trillion", "converted_krw": 71_300_000_000_000},
                    "operating_cash_flow": {"k_ifrs_label": "Cash flows from operating activities", "raw": 105.08, "unit": "KRW trillion", "converted_krw": 105_080_000_000_000},
                    "pp_and_e_purchase": {"k_ifrs_label": "Purchase of PP&E", "raw": 14.11, "unit": "KRW trillion", "converted_krw": 14_110_000_000_000},
                    "mechanical_fcf": {"formula": "OCF - Purchase of PP&E", "raw": 90.97, "unit": "KRW trillion", "converted_krw": 90_970_000_000_000},
                    "cash_definition": {"k_ifrs_label": "Cash (end of period), including short-term financial instruments/assets", "raw": 190.00, "unit": "KRW trillion", "converted_krw": 190_000_000_000_000},
                    "debts": {"k_ifrs_label": "Debts", "raw": 22.4087, "unit": "KRW trillion", "converted_krw": 22_408_700_000_000},
                    "net_cash": {"k_ifrs_label": "Net Cash", "raw": 167.59, "unit": "KRW trillion", "converted_krw": 167_590_000_000_000},
                },
            },
            "2025FY": {
                "period": "2025-01-01至2025-12-31", "basis": "K-IFRS合并", "source_url": SAMSUNG_FY_URL,
                "news_url": SAMSUNG_FY_NEWS,
                "fields": {
                    "revenue": {"k_ifrs_label": "Sales", "raw": 333.6, "unit": "KRW trillion", "converted_krw": 333_600_000_000_000},
                    "operating_profit": {"k_ifrs_label": "Operating profit", "raw": 43.6, "unit": "KRW trillion", "converted_krw": 43_600_000_000_000},
                    "net_profit": {"k_ifrs_label": "Net profit", "raw": 45.2, "unit": "KRW trillion", "converted_krw": 45_200_000_000_000},
                    "operating_cash_flow": {"k_ifrs_label": "Cash flows from operating activities", "raw": 85.32, "unit": "KRW trillion", "converted_krw": 85_320_000_000_000},
                    "pp_and_e_purchase": {"k_ifrs_label": "Purchase of PP&E", "raw": 47.52, "unit": "KRW trillion", "converted_krw": 47_520_000_000_000},
                    "mechanical_fcf": {"formula": "OCF - Purchase of PP&E", "raw": 37.80, "unit": "KRW trillion", "converted_krw": 37_800_000_000_000},
                    "cash_definition": {"k_ifrs_label": "Cash (end of period), including short-term financial instruments/assets", "raw": 125.85, "unit": "KRW trillion", "converted_krw": 125_850_000_000_000},
                    "debts": {"k_ifrs_label": "Debts", "raw": 25.2391, "unit": "KRW trillion", "converted_krw": 25_239_100_000_000},
                    "net_cash": {"k_ifrs_label": "Net Cash", "raw": 100.61, "unit": "KRW trillion", "converted_krw": 100_610_000_000_000},
                },
            },
        },
        "required_product_fix_for_next_version": [
            "并列2026Q2与2025FY，禁止用一个期间替换另一个期间",
            "71.6写合并净利润，71.3写归母利润，不得都写成净利润",
            "现金190.00/125.85为公司演示口径Cash，包含短期金融工具等，不等同仅现金及等价物",
            "自由现金流90.97/37.80为OCF减PP&E采购的机械计算，必须注明公式",
        ],
    }


def table(headers, rows) -> str:
    head = "".join(f"<th>{esc(x)}</th>" for x in headers)
    body = "".join("<tr>" + "".join(f"<td>{x}</td>" for x in row) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def render_html(run_id: str, now: str, samsung: dict, audit: list[dict], hv: list[dict], cv: list[dict], ai: dict) -> str:
    audit_rows = []
    for x in audit:
        audit_rows.append([esc(x["scope"]), esc(x["code"]), esc(x["name"]), esc(x["period"]), esc(x["status"]), esc("；".join(x["flags"]) or "未触发异常阈值"), link(x["source_url"])])
    hv_rows = []
    for x in hv:
        values = " / ".join(f'{s["scenario"]}:{num(s["valuation_per_share"])}' for s in x["scenarios"]) or "无法形成可靠估值"
        hv_rows.append([esc(x["code"]), esc(x["name"]), esc(x["current_price"]), esc(x["price_date"]), esc(x["status"]), esc(x.get("method")), esc(values), link(x.get("formal_source"))])
    cv_rows = []
    for x in cv:
        values = " / ".join(f'{s["scenario"]}:{num(s["valuation_per_share"])}' for s in x["scenarios"]) or "第五关证据不足"
        cv_rows.append([esc(x["code"]), esc(x["name"]), esc(x["current_price"]), esc(x["price_time"]), esc(x["status"]), esc(x.get("method")), esc(values), link(x.get("formal_source"))])
    q2 = samsung["periods"]["2026Q2"]["fields"]
    fy = samsung["periods"]["2025FY"]["fields"]
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>V7 v0.5财务真实性纠错及估值判断输入闭合</title><style>
body{{margin:0;font-family:"Microsoft YaHei",Arial,sans-serif;color:#17212b;background:#fff;line-height:1.65;font-size:15px}}header{{background:#17324d;color:#fff;padding:28px max(24px,6vw)}}main{{max-width:1280px;margin:auto;padding:22px}}section{{padding:22px 0;border-bottom:1px solid #ccd5dd}}h1{{font-size:28px;margin:0 0 8px}}h2{{font-size:21px;color:#17324d}}h3{{font-size:17px}}.meta{{color:#d7e3ed}}.callout{{border-left:5px solid #26734d;background:#eef7f2;padding:12px 16px;margin:12px 0}}.warn{{border-color:#a45113;background:#fff6e8}}.bad{{border-color:#a82d2d;background:#fff0f0}}.table-wrap{{overflow-x:auto;margin:12px 0}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{border:1px solid #bdc8d2;padding:7px 8px;text-align:left;vertical-align:top}}th{{background:#eaf0f5}}code{{background:#edf1f4;padding:2px 4px}}a{{color:#0b61a4}}ul{{padding-left:22px}}footer{{padding:24px;background:#f0f3f5;color:#47535e}}
</style></head><body><header><h1>V7 v0.5财务真实性纠错及估值判断输入闭合</h1><div class="meta">run_id={esc(run_id)}｜生成时间={esc(now)}｜仅供GPT总控判断｜不修改v0.5｜不Release｜不生成订单</div></header><main>
<section><h2>一、执行结论</h2><div class="callout"><b>三星结论：</b>171.5万亿和89.5万亿是2026年第二季度K-IFRS合并实际数据；333.6万亿和43.6万亿是2025全年数据。两者均有正式原文，但不能跨期间替换。</div><div class="callout warn"><b>估值结论：</b>观察触发线已与内在价值分开。已有锁定输入者只提供悲观/基准/乐观算式供总控选择；缺远期盈利、净值或口径仍异常者明确为“无法形成可靠估值”。所有候选第五关仍是输入状态，不由Codex放行。</div></section>
<section><h2>二、三星财务字段纠错</h2><p>{esc(samsung['conclusion'])}</p>{table(['期间','收入','营业利润','合并净利润','归母利润','经营现金流','机械FCF','Cash口径','债务','来源'],[["2026Q2",num(q2['revenue']['raw'])+'万亿KRW',num(q2['operating_profit']['raw'])+'万亿KRW',num(q2['net_profit']['raw'])+'万亿KRW',num(q2['profit_attributable_to_owners']['raw'])+'万亿KRW',num(q2['operating_cash_flow']['raw'])+'万亿KRW',num(q2['mechanical_fcf']['raw'])+'万亿KRW',num(q2['cash_definition']['raw'])+'万亿KRW',num(q2['debts']['raw'],4)+'万亿KRW',link(SAMSUNG_Q2_URL)],["2025FY",num(fy['revenue']['raw'])+'万亿KRW',num(fy['operating_profit']['raw'])+'万亿KRW',num(fy['net_profit']['raw'])+'万亿KRW','正式摘要未在本包单列',num(fy['operating_cash_flow']['raw'])+'万亿KRW',num(fy['mechanical_fcf']['raw'])+'万亿KRW',num(fy['cash_definition']['raw'])+'万亿KRW',num(fy['debts']['raw'],4)+'万亿KRW',link(SAMSUNG_FY_URL)]])}<ul>{''.join('<li>'+esc(x)+'</li>' for x in samsung['required_product_fix_for_next_version'])}</ul></section>
<section><h2>三、45项财务异常复扫</h2><p>共24类持仓记录和21只候选记录。异常阈值只负责报警，不替代投资判断；银行、加密资产和特殊会计项目按各自口径处理。</p>{table(['范围','代码','名称','期间','状态','异常/限制','正式原文'],audit_rows)}</section>
<section><h2>四、24类持仓估值判断输入</h2><p>三情景结果是“每股指标×供总控选择的倍数”，不是买卖建议。历史锁定输入有日期限制；没有可靠输入的项目不出数。</p>{table(['代码','名称','当前价','价格日','状态','方法','悲观/基准/乐观结果','正式原文'],hv_rows)}</section>
<section><h2>五、21只候选第五关估值输入</h2><p>候选结果使用扫描价格和扫描倍数反推的TTM指标，再做显式情景；它不是正式远期共识。因此全部仍为第五关输入，不能由Codex判定通过。</p>{table(['代码','名称','扫描价','时间','状态','方法','悲观/基准/乐观结果','正式原文'],cv_rows)}</section>
<section><h2>六、AI暴露口径</h2>{table(['指标','数值','分母','边界'],[["AI直接暴露",esc(ai['direct_pct'])+'%',esc(ai['denominator']),esc(ai['boundary'])],["加入软银后的广义暴露",esc(ai['broad_pct'])+'%',esc(ai['denominator']),esc(ai['boundary'])]])}<p>这两个比例不是全账户同日暴露，不属于固定硬线，不自动触发交易。</p></section>
<section><h2>七、停止边界</h2><ul><li>v0.5 HTML/PDF原件未修改。</li><li>本轮未生成v0.6产品。</li><li>未作最终投资判断，未登记Release，未覆盖00_今日日报.pdf。</li><li>未调用交易功能，未生成或执行订单。</li><li>下一岗位：GPT总控完成估值和投资判断后，再签发v0.6完整产品生产任务。</li></ul></section></main><footer>状态：GPT_CONTROL_REVIEW_RETURNED_V05｜本包仅做证据、字段和估值输入闭合。</footer></body></html>'''


def main() -> None:
    now_dt = datetime.now(ZoneInfo("Asia/Tokyo"))
    now = now_dt.isoformat(timespec="seconds")
    run_id = f"V7-V05-EVIDENCE-CLOSE-{now_dt.strftime('%Y%m%d-%H%M%S')}-JST"
    out = ROOT / "output/decision_inputs/2026-08-17" / run_id
    out.mkdir(parents=True, exist_ok=False)

    v05_holdings = read_json(HOLDINGS_V05)["items"]
    v05_candidates = read_json(CANDIDATES_V05)["items"]
    source_holdings = read_json(HOLDINGS_SOURCE)["items"]
    source_candidates = read_json(CANDIDATES_SOURCE)["items"]
    val_inputs = read_json(VAL_INPUTS)
    gate = read_json(SCAN_GATE)
    market = gate.get("per_stock") or {}

    samsung = samsung_report(now, run_id)
    audit = [financial_audit_row("持仓", x) for x in source_holdings]
    audit.extend(financial_audit_row("候选", x) for x in source_candidates)
    holdings_valuation = build_holding_valuations(v05_holdings, source_holdings, val_inputs, market)
    candidates_valuation = build_candidate_valuations(v05_candidates, source_candidates, market)
    ai = {
        "run_id": run_id, "direct_pct": 48.147541, "broad_pct": 61.475698,
        "denominator": "2026-08-17富途总资产1,162,265.0739美元",
        "boundary": "其他账户日期不同，不是四账户同日暴露；不属于固定硬线，不自动触发交易",
        "source": str(ROOT / "data/accounts/futu_positions_20260817.json"),
    }

    write_json(out / "01_三星财务字段纠错报告_20260817.json", samsung)
    write_json(out / "02_45项财务异常复扫矩阵_20260817.json", {"run_id": run_id, "count": len(audit), "items": audit})
    write_json(out / "03_24类持仓估值判断输入表_20260817.json", {"run_id": run_id, "count": len(holdings_valuation), "items": holdings_valuation})
    write_json(out / "04_21只候选第五关估值输入表_20260817.json", {"run_id": run_id, "count": len(candidates_valuation), "items": candidates_valuation})
    write_json(out / "05_AI暴露口径校验表_20260817.json", ai)
    report = render_html(run_id, now, samsung, audit, holdings_valuation, candidates_valuation, ai)
    (out / "V7_v0.5财务真实性纠错及估值判断输入闭合_20260817.html").write_text(report, encoding="utf-8")

    execution = {
        "run_id": run_id, "generated_at": now, "status": "EVIDENCE_INPUT_PACKAGE_COMPLETE_FOR_GPT_CONTROL",
        "source_v05": str(V05_DIR),
        "source_v05_hashes": {"html": V05_HTML_SHA, "pdf": V05_PDF_SHA},
        "daily_before_sha256": sha256(DAILY),
        "actions": ["只读读取v0.5和上游财务卡", "机械复扫45项", "生成24+21估值输入", "未修改v0.5", "未调用交易功能"],
        "important_finding": "三星171.5/89.5属于2026Q2，333.6/43.6属于2025FY；不是同一期间。",
    }
    write_json(out / "06_执行日志_20260817.json", execution)
    print(json.dumps({"run_id": run_id, "output_dir": str(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
