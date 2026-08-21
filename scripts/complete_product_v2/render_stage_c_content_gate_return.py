from __future__ import annotations

import argparse
import copy
import html
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.complete_product_v2 import render_stage_c_capability_closed_html as previous
JST = timezone(timedelta(hours=9))

ACCOUNT_SOURCE: dict[str, Any] = {}
FUTU_SNAPSHOT: dict[str, Any] = {}
MARKET_FACTS: dict[str, Any] = {}
REFRESHED_ACCOUNT: dict[str, Any] = {}

CURRENT_MARKET_NAMES = (
    "S&P 500", "Nasdaq Composite", "Nikkei 225", "USD/JPY",
    "US 10Y yield", "US 30Y yield", "WTI crude", "Brent crude",
)
STALE_CURRENT_MARKET_TERMS = (
    "4.65%", "5.19%", "84.58", "91.93",
    "65,952.94", "-3.45%", "-0.52%", "-0.97%",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def market_record(asset_id: str) -> dict[str, Any] | None:
    return next((row for row in MARKET_FACTS["records"] if row.get("asset_id") == asset_id), None)


def quote_value(asset_id: str) -> tuple[float, str, str]:
    row = market_record(asset_id)
    if not row:
        raise RuntimeError(f"missing refreshed quote: {asset_id}")
    if row.get("last_price") is not None:
        price = float(row["last_price"])
        raw_time = str(row.get("update_time") or MARKET_FACTS["evidence_cutoff_jst"])
        zone = "JST" if asset_id.startswith("JP.") else "ET（富途市场时间）"
        return price, f"{raw_time} {zone}", str(row["source"])
    return float(row["price"]), str(row["market_time_jst"]), str(row["source"])


def current_market_snapshot() -> dict[str, Any]:
    by_name = {row["name"]: row for row in MARKET_FACTS["macro_records"]}
    missing = [name for name in CURRENT_MARKET_NAMES if name not in by_name]
    if missing:
        raise RuntimeError(f"missing current market indicators: {missing}")
    rows = []
    for name in CURRENT_MARKET_NAMES:
        source = by_name[name]
        rows.append({
            "indicator": name,
            "value": float(source["price"]),
            "previous_close": float(source["previous_close"]),
            "change_pct": float(source["change_pct"]),
            "market_time_jst": str(source["market_time_jst"]),
            "source": str(source["source"]),
            "source_url": str(source["source_url"]),
            "raw_sha256": str(source["raw_sha256"]),
            "market_status": "日本市场收盘" if name == "Nikkei 225" else "证据截止前最后可得行情",
            "role": "本批次当前行情",
        })
    row_map = {row["indicator"]: row for row in rows}
    fact = (
        f"标普500为{row_map['S&P 500']['value']:,.2f}、较前收盘{row_map['S&P 500']['change_pct']:.2f}%"
        f"（{row_map['S&P 500']['market_time_jst']}）；"
        f"纳指为{row_map['Nasdaq Composite']['value']:,.2f}、较前收盘{row_map['Nasdaq Composite']['change_pct']:.2f}%"
        f"（{row_map['Nasdaq Composite']['market_time_jst']}）；"
        f"日经225为{row_map['Nikkei 225']['value']:,.2f}、较前收盘{row_map['Nikkei 225']['change_pct']:.2f}%"
        f"（{row_map['Nikkei 225']['market_time_jst']}）；"
        f"美国10年期国债收益率为{row_map['US 10Y yield']['value']:.2f}%"
        f"（{row_map['US 10Y yield']['market_time_jst']}），30年期为{row_map['US 30Y yield']['value']:.2f}%"
        f"（{row_map['US 30Y yield']['market_time_jst']}）；"
        f"WTI为{row_map['WTI crude']['value']:.2f}美元"
        f"（{row_map['WTI crude']['market_time_jst']}），布伦特为{row_map['Brent crude']['value']:.2f}美元"
        f"（{row_map['Brent crude']['market_time_jst']}）；"
        f"USD/JPY为{row_map['USD/JPY']['value']:.2f}"
        f"（{row_map['USD/JPY']['market_time_jst']}）。"
    )
    return {
        "evidence_cutoff_jst": str(MARKET_FACTS["evidence_cutoff_jst"]),
        "role": "本批次当前行情",
        "records": rows,
        "fact": fact,
    }


def remove_legacy_current_market_facts(model: dict[str, Any]) -> list[dict[str, Any]]:
    removed: list[dict[str, Any]] = []
    for layer in model["layers"]:
        retained = []
        for fact in layer.get("facts", []):
            serialized = json.dumps(fact, ensure_ascii=False)
            if any(term in serialized for term in STALE_CURRENT_MARKET_TERMS):
                removed.append({"layer": layer["layer"], "title": fact.get("title"), "status": "已从本批次当前事实中删除"})
            else:
                retained.append(fact)
        layer["facts"] = retained
    return removed


def rebuild_account_source() -> dict[str, Any]:
    source = copy.deepcopy(ACCOUNT_SOURCE)
    usd_jpy, usd_jpy_time, usd_source = quote_value("USDJPY")
    krw_jpy, krw_jpy_time, krw_source = quote_value("KRWJPY")
    futu_map = {row["symbol"]: row for row in FUTU_SNAPSHOT["futu_positions"]}
    rows: list[dict[str, Any]] = []
    for old in source["positions"]:
        row = copy.deepcopy(old)
        symbol = row["asset_id"]
        price, price_time, price_source = quote_value(symbol)
        if row["account"] == "FUTU":
            position = futu_map[symbol]
            row["quantity"] = float(position["quantity"])
            row["quantity_evidence_date"] = "2026-08-21"
            row["quantity_evidence_status"] = "8月21日OpenD只读接口实测"
            row["source"] = "Futu OpenD只读持仓接口；未调用交易解锁或订单功能"
        row["price"] = price
        row["price_time_jst"] = price_time
        row["price_source"] = price_source
        if row["currency"] == "JPY":
            value = row["quantity"] * price
        elif row["currency"] == "USD":
            value = row["quantity"] * price * usd_jpy
        elif row["currency"] == "KRW":
            value = row["quantity"] * price * krw_jpy
        else:
            raise RuntimeError(f"unsupported currency: {row['currency']}")
        row["market_value_jpy"] = round(value, 2)
        row["fx_used"] = (
            {"pair": "USD/JPY", "value": usd_jpy, "time": usd_jpy_time, "source": usd_source}
            if row["currency"] == "USD" else
            {"pair": "KRW/JPY", "value": krw_jpy, "time": krw_jpy_time, "source": krw_source}
            if row["currency"] == "KRW" else
            {"pair": "不需要换汇", "value": 1.0, "time": price_time, "source": "日元原币计价"}
        )
        rows.append(row)

    futu_total_jpy = float(FUTU_SNAPSHOT["futu_cash"]["total_assets"]) * usd_jpy
    futu_positions_jpy = sum(row["market_value_jpy"] for row in rows if row["account"] == "FUTU")
    futu_cash_and_other_jpy = futu_total_jpy - futu_positions_jpy
    broker = FUTU_SNAPSHOT["futu_cash"]
    cash_rows = copy.deepcopy(source["cash_and_unknown_fields"])
    futu_cash = next(row for row in cash_rows if row["account"] == "FUTU")
    futu_cash.update({
        "name": "现金及尚未拆分的其他净资产",
        "market_value_jpy": round(futu_cash_and_other_jpy, 2),
        "data_date": "2026-08-21",
        "status": "8月21日OpenD实测；账户总额已闭合，内部构成仍有未拆分项",
        "components": {
            "cash_usd": broker["cash"],
            "account_market_value_usd": broker["market_val"],
            "total_assets_usd": broker["total_assets"],
            "other_net_assets_usd": round(broker["total_assets"] - broker["market_val"] - broker["cash"], 4),
            "usd_jpy": usd_jpy,
            "usd_jpy_time_jst": usd_jpy_time,
        },
    })
    ibkr_cash = next(row for row in cash_rows if row["account"] == "IBKR")
    ibkr_cash["market_value_jpy"] = round(2056.28 * usd_jpy, 2)
    ibkr_cash["status"] = "8月4日最后确认现金，董事长8月19日确认其后无交易；按8月21日汇率重估，利息和费用变化仍未知"

    account_totals: defaultdict[str, float] = defaultdict(float)
    for row in rows:
        account_totals[row["account"]] += row["market_value_jpy"]
    for row in cash_rows:
        account_totals[row["account"]] += float(row["market_value_jpy"])
    account_totals["FUTU"] = round(futu_total_jpy, 2)
    known_total = round(sum(account_totals.values()), 2)

    combined: defaultdict[str, dict[str, Any]] = defaultdict(
        lambda: {"quantity_by_account": {}, "market_value_jpy": 0.0, "name": ""}
    )
    for row in rows:
        item = combined[row["asset_id"]]
        item["asset_id"] = row["asset_id"]
        item["name"] = row["name"]
        item["quantity_by_account"][row["account"]] = row["quantity"]
        item["market_value_jpy"] += row["market_value_jpy"]
    combined_rows = sorted(
        ({**value, "market_value_jpy": round(value["market_value_jpy"], 2)} for value in combined.values()),
        key=lambda row: row["market_value_jpy"], reverse=True,
    )
    combined_map = {row["asset_id"]: row for row in combined_rows}

    def risk(symbols: set[str]) -> dict[str, Any]:
        value = sum(combined_map[symbol]["market_value_jpy"] for symbol in symbols if symbol in combined_map)
        return {
            "symbols": sorted(symbols), "market_value_jpy": round(value, 2),
            "known_total_ratio_pct": round(value / known_total * 100.0, 6),
            "denominator": "8月21日已知资产观察总额；手工账户仍保留各自证据日期",
        }

    ai_direct = {"US.AVGO", "US.MSFT", "US.NVDA", "US.SNDK", "US.TSM"}
    crypto_direct = {"BTC", "ETH"}
    source.update({
        "known_assets_total_jpy": known_total,
        "account_known_values_jpy": {key: round(value, 2) for key, value in account_totals.items()},
        "unknowns": [
            "SBI个人与公司账户归属未闭合；2026-08-19 18:50 JST交易后截图已读取，数量按8月21日价格重估。",
            "SBI买付余力不等同于完整现金、融资及应计利息拆分。",
            "IBKR使用2026-08-04最后截图；董事长于8月19日确认其后无交易，利息、费用、负现金和融资仍不是生产日实物。",
            "bitFlyer使用2026-08-11最后截图；董事长于8月19日确认其后无交易。",
            "不同账户证据日期不同，已知资产合计不是四账户同日完整净值。",
        ],
        "positions": rows,
        "combined_positions": combined_rows,
        "cash_and_unknown_fields": cash_rows,
        "risk": {
            "ai_direct": risk(ai_direct),
            "ai_broad_with_softbank_proxy": risk(ai_direct | {"JP.9984"}),
            "crypto_direct": risk(crypto_direct),
            "crypto_broad_with_related_equities": risk(crypto_direct | {"US.MSTR", "US.COIN", "US.CRCL"}),
        },
        "forward_observation_baselines": {
            "FUTU": {"baseline_jpy": account_totals["FUTU"], "plus_40_target_jpy": round(account_totals["FUTU"] * 1.4, 2), "plus_100_target_jpy": round(account_totals["FUTU"] * 2.0, 2), "boundary": "8月21日OpenD当日实测前瞻观察基线，不是1月1日年度收益基线。"},
            "SBI账户归属尚未确认": {"baseline_jpy": account_totals["SBI账户归属尚未确认"], "plus_40_target_jpy": round(account_totals["SBI账户归属尚未确认"] * 1.4, 2), "plus_100_target_jpy": round(account_totals["SBI账户归属尚未确认"] * 2.0, 2), "boundary": "8月19日交易后数量按8月21日收盘价重估；账户归属仍未闭合。"},
        },
        "annual_performance_boundary": "缺少2026年1月1日完整净值及全年净入出金，不能计算年度实际累计收益或精确目标差额。",
        "refresh_audit": {
            "futu_snapshot_run_id": FUTU_SNAPSHOT["run_id"],
            "futu_collected_at_jst": FUTU_SNAPSHOT["generated_at"],
            "market_cutoff_jst": MARKET_FACTS["evidence_cutoff_jst"],
            "usd_jpy": usd_jpy, "usd_jpy_time_jst": usd_jpy_time,
            "topix_status": "自动行情源失败，未写成没有TOPIX行情",
        },
    })
    return source


def refresh_capability(capability: dict[str, Any]) -> None:
    global REFRESHED_ACCOUNT
    if not REFRESHED_ACCOUNT:
        REFRESHED_ACCOUNT = rebuild_account_source()
    combined = {row["asset_id"]: row for row in REFRESHED_ACCOUNT["combined_positions"]}
    total = REFRESHED_ACCOUNT["known_assets_total_jpy"]
    for cap in capability["holdings_24"]:
        symbol = cap["symbol"]
        combined_row = combined[symbol]
        price, price_time, source = quote_value(symbol)
        cap["market_value_jpy"] = combined_row["market_value_jpy"]
        cap["known_asset_weight_pct"] = round(combined_row["market_value_jpy"] / total * 100.0, 6)
        cap["quantity_by_account"] = combined_row["quantity_by_account"]
        cap["current_price"] = {"value": price, "time": price_time, "source": source}
    research_quotes = {}
    for item in capability["research_18"]:
        price, price_time, source = quote_value(item["asset_id"])
        old = market_record(item["asset_id"]) or {}
        item["current_quote"] = {
            "last_price": price, "update_time": price_time, "source": source,
            "pe_ratio": old.get("pe_ratio"), "pb_ratio": old.get("pb_ratio"),
        }
        research_quotes[item["asset_id"]] = item["current_quote"]
    capability["quote_refresh"] = {
        "records": [{"code": key, **value} for key, value in research_quotes.items()],
        "log": {"status": "FETCH_OK", "started_at_jst": MARKET_FACTS["started_at_jst"], "finished_at_jst": MARKET_FACTS["finished_at_jst"], "api": "OpenD只读行情及公开行情补足", "trade_calls": 0, "requested": 18, "received": 18},
    }
    capability["evidence_cutoff_jst"] = MARKET_FACTS["evidence_cutoff_jst"]


def weighted_scenario(decision: dict[str, Any], current: float) -> dict[str, float]:
    values = decision["scenario_values"]
    probs = decision["scenario_probability_pct"]
    weighted = sum(float(values[key]) * float(probs[key]) / 100.0 for key in ("bear", "base", "bull"))
    expected = (weighted / current - 1.0) * 100.0
    return {"weighted_value": weighted, "expected_return_pct": expected}


REAL_HOLDING_EVENTS = {
    "US.AVGO": {
        "role": "公司或行业事件", "status": "已取得本批次独立公司事件",
        "title": "Broadcom据报洽谈超过600亿美元AI芯片融资", "publisher": "Reuters报道；可读取转载页交叉核验",
        "published_at": "2026-08-20", "period": "本批次统一事实截止前",
        "locator": "报道正文：融资规模、潜在参与方及未置评边界",
        "url": "https://www.boursorama.com/bourse/actualites-amp/broadcom-cherche-a-lever-plus-de-60000-millions-pour-accord-de-puces-ia-rapporte-bloomberg-news-ece3781d853613b3798258ad1a917d60",
        "supports": "AI需求融资规模仍大，但债务融资、对手方和客户集中风险同步上升。",
        "cannot_prove": "报道不能证明融资已经完成，也不能当作Broadcom已确认收入、负债或现金流。",
    },
    "US.NVDA": {
        "role": "公司或行业事件", "status": "已取得本批次独立公司事件",
        "title": "NVIDIA否认中国专用LPU已在路线图中", "publisher": "Reuters报道；NVIDIA发言人回应",
        "published_at": "2026-08-20", "period": "本批次统一事实截止前",
        "locator": "报道正文：NVIDIA发言人对中国专用LPU传闻的否认",
        "url": "https://www.boursorama.com/bourse/actualites/nvidia-dement-les-informations-selon-lesquelles-elle-s-appreterait-a-lancer-une-puce-d-ia-en-chine-d-ici-la-fin-de-l-annee-71e3f8cec411a06e3c88bc2f4bfa83d2",
        "supports": "撤回把未确认LPU传闻当作中国业务增量的依据。",
        "cannot_prove": "公司否认只针对LPU传闻，不能证明全部中国业务或出口限制已经解决。",
    },
}


def normalize_holding_event_roles(rows: list[dict[str, Any]]) -> None:
    missing = {
        "role": "公司或行业事件", "status": "截止时间内未取得独立公司事件",
        "title": "截止时间内未取得独立公司事件", "publisher": "本批次公司事件检索",
        "published_at": "截至统一事实截止时间", "period": "本批次统一事实截止前",
        "locator": "未取得可独立使用的公司事件原文；没有用财报或监管文件占位", "url": None,
        "supports": "只说明本批次限定检索范围内未取得独立公司事件，不代表市场上没有发生事件。",
        "cannot_prove": "不能支持当期事件判断、估值变化或交易动作。",
    }
    for item in rows:
        roles = item.get("precise_evidence_roles", [])
        idx = next((i for i, role in enumerate(roles) if role.get("role") == "公司或行业事件"), None)
        replacement = copy.deepcopy(REAL_HOLDING_EVENTS.get(item["asset_id"], missing))
        if idx is None:
            roles.append(replacement)
        else:
            roles[idx] = replacement


def sync_research_market_facts(capability: dict[str, Any]) -> None:
    for item in capability["research_18"]:
        quote = item["current_quote"]
        gate = item["gates"][2]
        fact = gate.get("fact") if isinstance(gate.get("fact"), dict) else {}
        fact.update({
            "current_price": quote["last_price"], "price_time": quote["update_time"],
            "pe_ratio_market_snapshot": quote.get("pe_ratio"), "pb_ratio_market_snapshot": quote.get("pb_ratio"),
            "boundary": "当前市盈率和市净率只作市场温度计；不能独立证明内在价值。",
        })
        gate["fact"] = fact
        gate["source"] = {"title": "统一事实截止前最后可得行情", "publisher": quote["source"], "published_at": quote["update_time"], "url": None}


def pdca_probability_basis(prediction_id: str) -> str:
    return {
        "P-20260821-01": "采用较高档70%：正式政策仍未确认单向宽松，但通胀和沟通可能变化，保留明确反向风险。该档位尚无足够历史样本校准。",
        "P-20260821-03": "采用较高档70%：正式财报支持AI需求，同时出口限制和客户自研芯片构成可核反向证据。该档位尚无足够历史样本校准。",
        "P-20260821-04": "采用较高档70%：估值安全边际、稀释透明和项目兑现必须同时闭合，当前至少一项仍缺。该档位尚无足够历史样本校准。",
        "P-20260821-05": "采用较高档70%：长期电力需求和合同可见，但资本开支与自由现金流仍是实质约束。该档位尚无足够历史样本校准。",
        "P-20260821-06": "采用较高档70%：18只对象当前均不可执行，预测只要求至少15只继续未触发，并保留最多3只可能通过的反向空间。该档位尚无足够历史样本校准。",
        "P-20260821-02": "这是产品流程检查，采用很高档90%表示必须遵守正式决定边界；不进入投资预测概率校准。",
    }[prediction_id]


def rebuild_pdca_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    verified = correct = wrong = 0
    for row in records:
        actual = str(row.get("actual_result") or "")
        success = str(row.get("success_definition") or "")
        match = re.search(r"变动([+-]\d+(?:\.\d+)?)%", actual)
        result = None
        if match and "SOXX" in success and "不低于-10%" in success:
            result, series = float(match.group(1)) >= -10.0, "半导体五日跌幅阈值"
            lesson = "本条只证明该滚动窗口内SOXX没有跌破-10%，不等于AI长期逻辑已经正确；以后同时记录相对大盘表现和正式盈利证据。"
        elif match and "SOXX" in success and "低于5%" in success:
            result, series = float(match.group(1)) < 5.0, "半导体五日强反弹阈值"
            lesson = "本条正确识别了该窗口没有出现5%以上强反弹；以后同时锁定反弹持续时间，避免把短窗结果外推成周期判断。"
        elif match and "SPY" in success and "不低于-5%" in success:
            result, series = float(match.group(1)) >= -5.0, "标普五日避险阈值"
            lesson = "本条只证明该滚动窗口内SPY没有跌破-5%，不等于市场风险已经消失；以后同时记录长端利率、美元和波动率。"
        else:
            series = "市场环境描述" if "翻转级事件" in str(row.get("prediction")) else "政策状态描述"
            lesson = f"{row.get('prediction_date')}这条记录没有列出可核事件清单、阈值和来源，无法复核。今后必须在形成预测时锁定对象、阈值、截止日和外部证据。"
        row["tracking_series"] = series
        if result is not None:
            verified += 1; correct += int(result); wrong += int(not result)
            row.update({
                "verification_class": "已有阈值与外部行情结果", "verdict": "判对" if result else "判错",
                "external_evidence": "富途只读行情接口复权日K；标的、区间起止和涨跌幅已保存在本条实际结果中。没有网页链接不等于没有外部市场数据。",
                "error_or_learning_category": "账户或行情数据与阈值复核",
                "specific_change": "滚动窗口结果与长期投资逻辑分开统计；不再把跟踪点一致率称为胜率。",
            })
        else:
            row.update({
                "verification_class": "原定义不足，无法验证", "verdict": "无法独立验证",
                "actual_result": "原记录没有可外部核验的事件清单或数值阈值，本期不倒填结果，退出统计分母。",
                "external_evidence": "原记录缺少与成功定义一一对应的外部证据。",
                "error_or_learning_category": "因果推理定义不足" if series == "市场环境描述" else "新闻源与政策定义不足",
                "specific_change": "新预测必须预先登记成功标准、反事实、验证日和证据角色。",
            })
        row["lesson"] = lesson
    return {
        "historical_record_count": len(records), "verifiable_tracking_points": verified,
        "correct_tracking_points": correct, "wrong_tracking_points": wrong,
        "not_independently_verifiable": len(records) - verified,
        "independent_prediction_series": len({row["tracking_series"] for row in records}),
        "statistics_boundary": "可核验跟踪点存在滚动窗口重叠，不等于独立投资预测；一致率不得称为胜率。",
    }

def apply_holdings(old_holdings: list[dict[str, Any]], capability: dict[str, Any], final: dict[str, Any]) -> list[dict[str, Any]]:
    refresh_capability(capability)
    rows = ORIGINAL_APPLY_HOLDINGS(old_holdings, capability, final)
    decision_map = {row["asset_id"]: row for row in final["holdings_judgments"]}
    cap_map = {row["symbol"]: row for row in capability["holdings_24"]}
    for item in rows:
        decision = decision_map[item["asset_id"]]
        if decision["target_contribution_included"]:
            current = float(cap_map[item["asset_id"]]["current_price"]["value"])
            calc = weighted_scenario(decision, current)
            weight = float(cap_map[item["asset_id"]]["known_asset_weight_pct"])
            contribution = weight * calc["expected_return_pct"] / 100.0
            item["scenario_decision"]["expected_return_pct"] = round(calc["expected_return_pct"], 6)
            item["scenario_decision"]["target_contribution_pp"] = round(contribution, 6)
            item["scenario_decision"]["current_price_used"] = current
            item["scenario_decision"]["current_price_time"] = cap_map[item["asset_id"]]["current_price"]["time"]
            item["scenario_decision"]["weighted_scenario_value"] = round(calc["weighted_value"], 6)
            item["action"]["target_contribution"] = f"按8月21日账户权重机械复算：{contribution:+.4f}个百分点。"
    normalize_holding_event_roles(rows)
    return rows


def apply_research(old_research: list[dict[str, Any]], capability: dict[str, Any], final: dict[str, Any]) -> list[dict[str, Any]]:
    refresh_capability(capability)
    sync_research_market_facts(capability)
    rows = ORIGINAL_APPLY_RESEARCH(old_research, capability, final)
    for item in rows:
        quote = item["current_quote"]
        gate3 = item["gates"][2]
        pe = quote.get("pe_ratio")
        pb = quote.get("pb_ratio")
        item["valuation_or_risk_pricing"] = (
            f"统一当前价{quote['last_price']:,.4f}，时间{quote['update_time']}；"
            f"市盈率{pe:,.2f}倍，市净率{pb:,.2f}倍。"
            "这些行情指标只作市场温度计，不能独立证明内在价值。"
        )
        reason = str(item["final_opportunity_judgment"].get("reason") or "研究尚未闭合")
        reason = re.sub(r"当前\d+(?:\.\d+)?倍市盈率", f"当前{pe:.1f}倍市盈率", reason)
        reason = re.sub(r"\d+(?:\.\d+)?倍市净率", f"{pb:.1f}倍市净率", reason)
        item["final_opportunity_judgment"]["reason"] = reason
        item["retain_or_drop"] = reason
        gate5 = item["gates"][4]
        decision = item["final_opportunity_judgment"]
        gate5["fact"] = (
            f"第五关结论：{decision['gate5']}。原因：{reason}。"
            f"与现金或持仓比较：{decision.get('replacement_object') or '没有形成替换对象'}。"
            f"催化剂：{decision.get('catalyst') or '尚未取得'}。"
            f"重新判断时间：{decision.get('decision_time') or '下一次正式披露'}。"
        )
        if isinstance(gate3.get("fact"), dict):
            gate3["fact"].update({
                "current_price": quote["last_price"], "price_time": quote["update_time"],
                "pe_ratio_market_snapshot": pe, "pb_ratio_market_snapshot": pb,
            })
    return rows


def build_target_bridge(capability: dict[str, Any], final: dict[str, Any]) -> dict[str, Any]:
    refresh_capability(capability)
    cap_map = {row["symbol"]: row for row in capability["holdings_24"]}
    decision_map = {row["asset_id"]: row for row in final["holdings_judgments"]}
    rows = []
    contribution = 0.0
    quantified_weight = 0.0
    scenario_totals = {"bear": 0.0, "base": 0.0, "bull": 0.0}
    usd_jpy, usd_jpy_time, _ = quote_value("USDJPY")
    for symbol, cap in cap_map.items():
        decision = decision_map[symbol]
        current = float(cap["current_price"]["value"])
        row = {
            "asset_id": symbol, "name": cap["name"],
            "known_weight_pct": float(cap["known_asset_weight_pct"]),
            "current_price": current, "current_price_time": cap["current_price"]["time"],
            "current_price_source": cap["current_price"]["source"],
            "fx_value": usd_jpy if symbol.startswith("US.") else 1.0,
            "fx_time": usd_jpy_time if symbol.startswith("US.") else cap["current_price"]["time"],
            "fx_pair": "USD/JPY" if symbol.startswith("US.") else "原币为日元或本期不需要换汇",
            "target_contribution_included": decision["target_contribution_included"],
            "unique_action": decision["unique_action"],
            "scenario_values": decision.get("scenario_values"),
            "scenario_probability_pct": decision.get("scenario_probability_pct"),
            "probability_band": "悲观{bear}%／基准{base}%／乐观{bull}%".format(**decision["scenario_probability_pct"]) if decision.get("scenario_probability_pct") else "本期没有数值概率",
        }
        if decision["target_contribution_included"]:
            calc = weighted_scenario(decision, current)
            row.update(calc)
            row["target_contribution_pp"] = row["known_weight_pct"] * calc["expected_return_pct"] / 100.0
            row["formula"] = "概率加权价值=悲观值×悲观概率+基准值×基准概率+乐观值×乐观概率；预期收益=概率加权价值÷当前价−1；组合贡献=账户权重×预期收益"
            if symbol == "JP.4568":
                row["zero_explanation"] = "上一版恰好为0，是因为当时概率加权价值2,867.50日元与当时当前价2,867.50日元完全相同；8月21日价格刷新后按新价重新计算，不再强行保留0。"
            contribution += row["target_contribution_pp"]
            quantified_weight += row["known_weight_pct"]
            for key in scenario_totals:
                scenario_return = (float(decision["scenario_values"][key]) / current - 1.0) * 100.0
                scenario_totals[key] += row["known_weight_pct"] * scenario_return / 100.0
        else:
            row.update({"weighted_value": None, "expected_return_pct": None, "target_contribution_pp": None, "formula": "本期没有可靠数值情景，不按0计入目标桥。"})
        rows.append(row)
    unquantified = 100.0 - quantified_weight
    residual_40 = (40.0 - contribution) / (unquantified / 100.0)
    residual_100 = (100.0 - contribution) / (unquantified / 100.0)
    total = REFRESHED_ACCOUNT["known_assets_total_jpy"]
    portfolio = final["portfolio_target_judgment"]
    return {
        "boundary": "这是8月21日已知资产前瞻观察桥，不是2026年1月1日起的实际年度收益；手工账户仍保留各自证据日期。",
        "known_assets_jpy": total, "plus_40_observation_target_jpy": round(total * 1.4, 2),
        "plus_100_observation_target_jpy": round(total * 2.0, 2),
        "quantified_asset_count": 9, "quantified_weight_pct": round(quantified_weight, 6),
        "unquantified_weight_pct": round(unquantified, 6),
        "probability_weighted_contribution_pp": round(contribution, 6),
        "scenario_contribution_pp": {**{key: round(value, 6) for key, value in scenario_totals.items()}, "probability_weighted": round(contribution, 6)},
        "plus_40_status": "NOT_PROVEN", "plus_100_status": "NOT_FEASIBLE_UNDER_CURRENT_EVIDENCE",
        "plain_language_reason": f"9项数值情景按8月21日当前价、账户权重和汇率重算后，概率加权贡献约{contribution:+.2f}个百分点。其余资产和现金没有被当成0，但缺少可复算收益输入，因此当前仍不能证明＋40%路径成立，＋100%也没有可信可执行路径。",
        "residual_required_average_return_pct": {"for_plus_40": round(residual_40, 6), "for_plus_100": round(residual_100, 6)},
        "required_monthly_compound_pct": portfolio["required_monthly_compound_from_august_18_pct"],
        "cash_role": portfolio["cash_opportunity_cost"], "fallback_route": portfolio["fallback_route"],
        "monthly_milestones": portfolio["monthly_milestones"], "next_review": portfolio["next_full_review_jst"],
        "asset_rows": rows, "unquantified_is_zero": False,
        "fx": {"USD/JPY": usd_jpy, "time_jst": usd_jpy_time},
    }


def apply_pdca(model: dict[str, Any], final: dict[str, Any]) -> dict[str, Any]:
    audit = previous.legacy.rebuild_pdca_quality(model)
    history_audit = rebuild_pdca_records(model["pdca"]["plain_records"])
    for row in final["pdca_new_predictions"]:
        row["probability_basis"] = pdca_probability_basis(row["prediction_id"])
        row["probability_label"] = "很高" if row["probability_pct"] == 90 else "较高"
    all_new = copy.deepcopy(final["pdca_new_predictions"])
    process_qa = [row for row in all_new if row["prediction_id"] == "P-20260821-02"]
    investment = [row for row in all_new if row["prediction_id"] != "P-20260821-02"]
    summary = model["pdca"]["body_summary"]
    summary.update({
        "new_predictions": all_new, "investment_predictions": investment,
        "process_quality_checks": process_qa, "new_quality_baseline_count": len(investment),
        "probability_policy": copy.deepcopy(final["probability_policy"]),
        "historical_verification": history_audit,
        "verdict_counts": {"判对": history_audit["correct_tracking_points"], "判错": history_audit["wrong_tracking_points"], "无法独立验证": history_audit["not_independently_verifiable"]},
        "externally_verifiable": history_audit["verifiable_tracking_points"],
        "not_independently_verifiable": history_audit["not_independently_verifiable"],
        "forbidden_claim": "29条是可核验滚动跟踪点，不是29个独立预测，也不能称为投资胜率。",
        "system_changes": [
            "已有明确阈值和富途复权日K结果的29条记录恢复真实判定；没有网页链接不再被误判为没有外部市场数据。",
            "28条缺少事件清单或数值阈值的记录继续列为无法验证，不倒填结果。",
            "错误归因分为新闻源、行情数据、规则、估值和因果推理；每条同时登记本期具体修改。",
            "5条投资预测与1条产品流程QA分开；70%是固定“较高”档评分值，不是由旧跟踪点一致率反推。",
        ],
    })
    audit.update(history_audit)
    audit.update({"investment_prediction_count": len(investment), "process_qa_count": len(process_qa), "all_records": all_new})
    layer7 = next(row for row in model["layers"] if row["layer"] == 7)
    layer7.update({
        "final_judgment": "57条历史记录中，29条有预先阈值和富途复权日K结果，按原标准均判对；其余28条因原定义不足仍无法验证。29条是重叠滚动跟踪点，不是投资胜率。",
        "portfolio_transmission": "历史记录用于识别数据、规则和推理缺陷；5条新投资预测另按固定概率档位做未来校准，产品流程QA不进入投资统计。",
        "reversal": "若复核发现行情区间、复权口径或原成功标准登记错误，立即撤回对应判定并重算分母。",
        "facts": [
            {"title": "历史PDCA真实复核", "publisher": "本产品第三层PDCA正文", "fact": "57条中29条具有明确阈值与行情结果，29条判对、0条判错；28条原定义不足，继续退出分母。", "supports": "支持区分可核跟踪点和真正无法验证记录。", "cannot_prove": "滚动窗口高度重叠，不能称为29个独立预测或投资胜率。", "url": "#pdca"},
            {"title": "新预测概率依据", "publisher": "本产品第三层PDCA正文", "fact": "5条投资预测使用固定较高档70%，每条分别登记支持证据、反向风险和选择理由；另1条90%为流程QA。", "supports": "支持未来使用Brier分数校准概率。", "cannot_prove": "样本尚未到期，不能提前证明70%已经校准准确。", "url": "#pdca"},
        ],
    })
    return audit

def build_news(model: dict[str, Any]) -> None:
    old_records = [row for row in model["news"].get("records", []) if row.get("event_id") not in {"NEWS-20260820-MARKET-SNAPSHOT"}]
    macro = {row["name"]: row for row in MARKET_FACTS["macro_records"]}
    cutoff = MARKET_FACTS["evidence_cutoff_jst"]
    snapshot = current_market_snapshot()
    retrieval_finished = datetime.now(JST).isoformat(timespec="seconds")
    records = old_records + [
        {
            "event_id": "NEWS-20260821-GLOBAL-MARKETS", "title": "8月21日全球股市、长债、油价和美元出现相互拉扯",
            "publisher": "Reuters报道的可读取转载页；AP交叉核验；行情由公开图表接口复核",
            "published_at": "2026-08-21", "data_date": "2026-08-21；每项实际时间见行情明细", "retrieved_at_jst": retrieval_finished,
            "url": "https://ae.marketscreener.com/news/global-stocks-set-for-biggest-weekly-fall-since-mid-july-dollar-on-the-defensive-ce7858dadb89ff26",
            "independent_url": "https://apnews.com/article/96ef9586e1288e50843b4d2b1ccebc32",
            "fact": snapshot["fact"],
            "market_snapshot": copy.deepcopy(snapshot["records"]),
            "market_role": snapshot["role"],
            "evidence_cutoff_jst": snapshot["evidence_cutoff_jst"],
            "portfolio_impact": "增长资产下跌而长端收益率与油价走高，说明增长担忧和融资压力可同时存在。能源股短期受油价支持，高估值科技受折现率压制，现金选择权上升。",
            "boundary": "美股仍在盘中，不冒充收盘；Reuters原站无法由当前执行环境直接打开，事实由可读取转载页、AP和独立行情交叉核验。",
        },
        {
            "event_id": "NEWS-20260820-AVGO-AI-DEBT", "title": "Broadcom据报洽谈超过600亿美元AI芯片融资",
            "publisher": "Reuters报道，原始信息援引Bloomberg；可读取Reuters转载页", "published_at": "2026-08-20", "data_date": "2026-08-20", "retrieved_at_jst": retrieval_finished,
            "url": "https://jackfmfargo.com/2026/08/20/broadcom-seeks-more-than-60-billion-in-latest-ai-debt-deal-bloomberg-news-reports/",
            "independent_url": "https://www.boursorama.com/bourse/actualites-amp/broadcom-cherche-a-lever-plus-de-60000-millions-pour-accord-de-puces-ia-rapporte-bloomberg-news-ece3781d853613b3798258ad1a917d60",
            "fact": "报道指Broadcom正与贷款方讨论为AI芯片安排筹集超过600亿美元债务，受益方包括Anthropic等；这是洽谈和报道，不是Broadcom已经完成融资或已经发生现金支出。",
            "portfolio_impact": "需求融资规模支持AI基础设施需求仍强，但把客户需求与大额债务绑定，会提高融资链、对手方和集中度风险。AVGO继续持有但不新增，AI同一驱动不扩大。",
            "boundary": "Broadcom、Apollo和Blackstone未就报道向Reuters置评；不能把报道金额当成公司已确认收入、负债或现金流。",
        },
        {
            "event_id": "NEWS-20260820-NVDA-CHINA-LPU-DENIAL", "title": "NVIDIA否认中国专用LPU已在路线图中",
            "publisher": "Reuters报道的可读取转载页；NVIDIA发言人回应", "published_at": "2026-08-20", "data_date": "2026-08-20", "retrieved_at_jst": retrieval_finished,
            "url": "https://www.boursorama.com/bourse/actualites/nvidia-dement-les-informations-selon-lesquelles-elle-s-appreterait-a-lancer-une-puce-d-ia-en-chine-d-ici-la-fin-de-l-annee-71e3f8cec411a06e3c88bc2f4bfa83d2",
            "independent_url": "https://jackfmfargo.com/2026/08/20/nvidia-to-ship-ai-chip-for-china-by-year-end-the-information-reports/",
            "fact": "NVIDIA发言人否认将于年内推出面向中国客户的专用LPU，并称当前没有在中国销售LPU，路线图中也没有中国专用LPU。",
            "portfolio_impact": "这撤回了把未确认LPU传闻当作中国业务增量的依据；但没有消除出口限制、产品准入和本地竞争风险。NVDA核心持有、财报前不追价的动作不变。",
            "boundary": "公司否认只针对LPU报道，不能外推为NVIDIA全部中国业务或出口限制已经解决。",
        },
    ]
    model["news"] = {
        "run_id": model["run_id"], "search_started_at_jst": MARKET_FACTS["started_at_jst"],
        "search_finished_at_jst": retrieval_finished, "evidence_cutoff_jst": cutoff,
        "search_scope": ["全球市场", "全球债券与美元", "油价与霍尔木兹", "AI融资", "NVDA中国业务", "24类持仓与18只观察股"],
        "queries": ["2026-08-21 global markets bonds oil dollar", "Broadcom more than 60 billion AI debt", "NVIDIA China LPU denial", "8月21日持仓与观察股公司公告增量"],
        "records": records,
        "current_market_snapshot": snapshot,
        "failed_sources": ["Reuters原站三个指定页面均无法由当前执行环境直接打开；使用可读取Reuters转载页、AP与独立行情交叉核验。", "TOPIX自动行情源返回空结果；未写成没有TOPIX行情。"],
        "excluded": ["截止时间之后发布的事实", "只有标题且无可核内容的线索", "不能影响七层、账户、持仓或动作的低影响消息"],
    }


def inject_content(model: dict[str, Any]) -> dict[str, Any]:
    model["single_portfolio_source"] = copy.deepcopy(REFRESHED_ACCOUNT)
    model["evidence_cutoff_jst"] = MARKET_FACTS["evidence_cutoff_jst"]
    model["judgment_formed_at_jst"] = datetime.now(JST).isoformat(timespec="seconds")
    build_news(model)
    snapshot = model["news"]["current_market_snapshot"]
    removed_market_facts = remove_legacy_current_market_facts(model)
    model["market_snapshot_uniqueness"] = {
        "evidence_cutoff_jst": snapshot["evidence_cutoff_jst"],
        "role": snapshot["role"],
        "records": copy.deepcopy(snapshot["records"]),
        "removed_legacy_current_facts": removed_market_facts,
    }
    market_by_name = {row["indicator"]: row for row in snapshot["records"]}
    risk = REFRESHED_ACCOUNT["risk"]
    total = REFRESHED_ACCOUNT["known_assets_total_jpy"]
    layer_map = {row["layer"]: row for row in model["layers"]}
    layer_map[1].update({"final_judgment": f"截至统一截止，标普500为{market_by_name['S&P 500']['value']:,.2f}、纳指为{market_by_name['Nasdaq Composite']['value']:,.2f}，美国长债收益率与油价同时偏高；AI基础设施长期需求仍在，但不是无条件宽松环境。", "direction": "长期支持AI基础设施，短期压制高估值和高融资依赖资产", "strength": "中等偏强", "confidence": "中高", "transmission": "提高自由现金流、融资结构和估值安全边际要求；能源只作事件性研究。", "reversal": "油价、通胀和长端收益率持续回落，或AI资本开支被正式下调。"})
    layer_map[3].update({"final_judgment": f"截至统一截止，美国10年期国债收益率{market_by_name['US 10Y yield']['value']:.2f}%、30年期{market_by_name['US 30Y yield']['value']:.2f}%，WTI {market_by_name['WTI crude']['value']:.2f}美元、布伦特{market_by_name['Brent crude']['value']:.2f}美元；美股走弱、美元偏软，但资金并未转为单向宽松。", "direction": "中性偏紧", "strength": "中等偏强", "confidence": "中高", "transmission": "高估值科技不追价；现金保留选择权；能源价格受益不能直接等于能源股通过第五关。", "reversal": "股债同时企稳、油价回落且通胀预期连续下降。"})
    layer_map[4].update({"final_judgment": f"日经225较前收盘{market_by_name['Nikkei 225']['change_pct']:.2f}%，标普500为{market_by_name['S&P 500']['change_pct']:.2f}%，纳指为{market_by_name['Nasdaq Composite']['change_pct']:.2f}%；油价上涨短期支持能源价格因素，长端利率偏高压制高估值科技。Broadcom融资与NVIDIA中国业务消息没有让观察股通过第五关。", "direction": "AI基础设施仍活跃但受融资与折现率约束；能源短期偏强", "strength": "中等", "confidence": "中高", "transmission": "AVGO、NVDA维持原持有边界但不新增；XOM、CVX只保留事件性观察；18只观察对象没有因此自动通过第五关。", "reversal": "油价和长端利率持续回落，或融资安排、需求及NVIDIA产品路线出现新的正式事实。"})
    layer_map[5]["final_judgment"] = "18只研究观察对象继续按唯一五关源管理；本轮新增新闻没有使任何对象形成可执行机会。"
    layer_map[5]["transmission"] = "研究卡、五关表、影子组合和行动栏全部从证券代码唯一源生成；当前可执行机会仍为0。"
    layer_map[6].update({"final_judgment": f"8月21日已知资产观察总额约{total:,.0f}日元；AI直接暴露{risk['ai_direct']['known_total_ratio_pct']:.2f}%，含软银代理后{risk['ai_broad_with_softbank_proxy']['known_total_ratio_pct']:.2f}%；广义加密暴露{risk['crypto_broad_with_related_equities']['known_total_ratio_pct']:.2f}%。", "transmission": "富途使用8月21日OpenD实测；SBI、IBKR、bitFlyer保留各自证据日。比例只用于风险观察，不是机械交易线。", "reversal": "取得手工账户更新现金、融资和应计字段后，重新计算已知分母和风险比例。"})
    layer6_facts = {fact.get("title"): fact for fact in layer_map[6].get("facts", [])}
    layer6_facts["唯一账户口径"] = {
        "title": "唯一账户口径", "publisher": "8月21日唯一账户事实源",
        "published_at": REFRESHED_ACCOUNT["refresh_audit"]["futu_collected_at_jst"], "url": None,
        "fact": f"已知资产观察总额为{total:,.2f}日元；富途为8月21日OpenD实测，手工账户保留各自证据日。",
        "supports": "支持已知口径风险观察，不等于四账户同日完整净值。",
        "cannot_prove": "不能证明未知现金、融资、应计项目或SBI账户归属。",
    }
    layer6_facts["AI同一驱动"] = {
        "title": "AI同一驱动", "publisher": "8月21日唯一账户事实源",
        "published_at": REFRESHED_ACCOUNT["refresh_audit"]["futu_collected_at_jst"], "url": None,
        "fact": f"以{total:,.2f}日元已知资产为分母，AI直接暴露{risk['ai_direct']['known_total_ratio_pct']:.2f}%，含软银代理后为{risk['ai_broad_with_softbank_proxy']['known_total_ratio_pct']:.2f}%。",
        "supports": "支持暂停扩大AI同一驱动风险。", "cannot_prove": "不是四账户同日完整比例，也不是自动交易硬线。",
    }
    layer6_facts["加密同一驱动"] = {
        "title": "加密同一驱动", "publisher": "8月21日唯一账户事实源",
        "published_at": REFRESHED_ACCOUNT["refresh_audit"]["futu_collected_at_jst"], "url": None,
        "fact": f"以{total:,.2f}日元已知资产为分母，广义加密暴露{risk['crypto_broad_with_related_equities']['known_total_ratio_pct']:.2f}%。",
        "supports": "支持不新增加密相关风险并保留条件性削减顺序。", "cannot_prove": "未知账户字段可能改变比例，不自动触发交易。",
    }
    ordered_titles = ["唯一账户口径", "AI同一驱动", "加密同一驱动"]
    remaining_facts = [fact for fact in layer_map[6].get("facts", []) if fact.get("title") not in ordered_titles]
    layer_map[6]["facts"] = [layer6_facts[title] for title in ordered_titles] + remaining_facts
    layer_map[7].update({"final_judgment": "本期建立5条投资预测基线，另有1条产品流程QA；两者分开统计。57条历史记录逐条展示其可验证性、结果、归因和改进。", "transmission": "只有投资预测进入未来概率校准；流程QA用于检查产品有没有把媒体预期写成正式决定。", "reversal": "到验证日没有独立外部证据时，记录退出统计分母，不追溯补造。"})
    news_map = {row["event_id"]: row for row in model["news"]["records"]}
    current_event_ids = {"NEWS-20260821-GLOBAL-MARKETS", "NEWS-20260820-AVGO-AI-DEBT", "NEWS-20260820-NVDA-CHINA-LPU-DENIAL"}
    for layer in layer_map.values():
        layer["facts"] = [fact for fact in layer.get("facts", []) if fact.get("event_id") not in current_event_ids]
    for number, event_ids in {1: ["NEWS-20260821-GLOBAL-MARKETS"], 3: ["NEWS-20260821-GLOBAL-MARKETS"], 4: ["NEWS-20260821-GLOBAL-MARKETS", "NEWS-20260820-AVGO-AI-DEBT", "NEWS-20260820-NVDA-CHINA-LPU-DENIAL"], 5: ["NEWS-20260820-AVGO-AI-DEBT"], 6: ["NEWS-20260821-GLOBAL-MARKETS"]}.items():
        layer_map[number].setdefault("facts", []).extend({
            **copy.deepcopy(news_map[event_id]),
            "supports": news_map[event_id]["portfolio_impact"],
            "cannot_prove": news_map[event_id]["boundary"],
        } for event_id in event_ids)
    research_map = {row["asset_id"]: row for row in model["research_gates"]}
    model["capabilities"]["shadow_portfolio"] = [{
        "asset_id": symbol, "name": item["name"], "capital_allocated": 0,
        "identity": "影子观察，不是真实持仓", "current_gate_stop": item["formal_gate_stop"],
        "comparison": item["replacement_target"], "trigger": item["executable_condition"],
        "next_review": item["next_review"],
    } for symbol, item in research_map.items()]
    for issue in model["capabilities"].get("issue_ledger", []):
        issue["owner"] = "数据证据由系统更新；投资判断由投研主脑统一裁定"
        if "全产品HTML必须恢复" in issue.get("issue", ""):
            issue["issue"] = "完整产品必须持续保留三层导航、证据追踪、替换比较、风险穿透、影子观察和问题台账。"
            issue["owner"] = "产品生成与内容闸复核"
    return {"status": "UPDATED_TO_2026-08-21_CUTOFF", "cutoff": model["evidence_cutoff_jst"]}


def apply_first_layer(model: dict[str, Any], final: dict[str, Any]) -> None:
    ORIGINAL_APPLY_FIRST_LAYER(model, final)
    action = model["judgment"]["today_action"]
    action["headline"] = "今天不强行新增仓位；先管理AI融资和长端利率风险，18只研究对象继续等待第五关真实触发。"
    action["priority"] = [
        "8月21日富途账户已通过OpenD只读刷新；手工账户继续显著保留原证据日期，不拼成同日净值。",
        "全球股市盘中偏弱、长债收益率和油价偏高，现金选择权上升；能源受益与科技折现压力同时存在。",
        "Broadcom大额AI融资报道既验证需求也提高融资链风险；AVGO持有、不新增。",
        "NVIDIA否认中国专用LPU，相关传闻不再作为增量依据；NVDA持有、财报前不追价。",
        "9项条件情景按8月21日价格、权重和汇率重算；＋40%路径仍未证明，＋100%仍无可信可执行路径。",
    ]


def render_target_bridge(target: dict[str, Any], base: Any) -> str:
    rows = []
    for row in target["asset_rows"]:
        if row["target_contribution_included"]:
            values = row["scenario_values"]
            probs = row["scenario_probability_pct"]
            calc = (
                f"当前价{row['current_price']:,.2f}（{row['current_price_time']}） → "
                f"概率加权价值{row['weighted_value']:,.2f} → 预期收益{row['expected_return_pct']:+.2f}% → "
                f"已知资产权重{row['known_weight_pct']:.2f}% → 组合贡献{row['target_contribution_pp']:+.4f}个百分点"
            )
            scenario = f"悲观{values['bear']:,.2f}×{probs['bear']}%＋基准{values['base']:,.2f}×{probs['base']}%＋乐观{values['bull']:,.2f}×{probs['bull']}%"
            note = row.get("zero_explanation") or ""
        else:
            calc = "没有可靠数值情景，不按0计入目标贡献，也不支持精确动作。"
            scenario = "使用非价格风险框架"
            note = ""
        rows.append(f"<tr data-target-row='{base.esc(row['asset_id'])}'><td>{base.esc(row['asset_id'])}<br>{base.esc(row['name'])}</td><td>{base.esc(scenario)}</td><td>{base.esc(calc)}<br><span class='muted'>汇率：{base.esc(row['fx_pair'])} {row['fx_value']:.4f}；{base.esc(row['fx_time'])}</span>{('<br><span class=\"boundary\">'+base.esc(note)+'</span>') if note else ''}</td><td>{base.esc(row['unique_action'])}</td></tr>")
    checkpoints = "".join(f"<tr><td>{base.esc(row['check_date'])}</td><td>{base.esc(row['check'])}</td></tr>" for row in target["monthly_milestones"])
    return f"""
    <div class="target-bars"><div><b>8月21日已知资产观察总额</b><span>¥{base.fmt_num(target['known_assets_jpy'])}</span><i style="width:50%"></i></div>
    <div><b>＋40%前瞻观察目标</b><span>¥{base.fmt_num(target['plus_40_observation_target_jpy'])}</span><i style="width:70%"></i></div>
    <div><b>＋100%压力目标</b><span>¥{base.fmt_num(target['plus_100_observation_target_jpy'])}</span><i style="width:100%"></i></div></div>
    <p class="boundary">{base.esc(target['boundary'])}</p>
    <div class="metric-grid"><article class="metric"><b>数值情景覆盖</b><strong>{target['quantified_weight_pct']:.2f}%</strong><small>9项条件情景</small></article>
    <article class="metric"><b>概率加权贡献</b><strong>{target['probability_weighted_contribution_pp']:+.2f}个百分点</strong><small>按8月21日价格和权重重算</small></article>
    <article class="metric"><b>＋40%路径</b><strong>尚未证明</strong><small>未量化部分平均仍需{target['residual_required_average_return_pct']['for_plus_40']:.2f}%</small></article>
    <article class="metric"><b>＋100%路径</b><strong>当前不可行</strong><small>未量化部分平均仍需{target['residual_required_average_return_pct']['for_plus_100']:.2f}%</small></article></div>
    <p>{base.esc(target['plain_language_reason'])}</p><p><b>现金机会成本：</b>{base.esc(target['cash_role'])}</p><p><b>替代路线：</b>{base.esc(target['fallback_route'])}</p>
    {base.details('24类资产可见计算桥', '<table><thead><tr><th>资产</th><th>情景输入</th><th>当前价到组合贡献</th><th>唯一动作</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table>', attrs="data-visible-target-bridge='1'")}
    <h4>复核里程碑</h4><table><thead><tr><th>日期</th><th>检查内容</th></tr></thead><tbody>{checkpoints}</tbody></table><p><b>下一次全量复核：</b>{base.esc(target['next_review'])}</p>
    """


def render_pdca(pdca: dict[str, Any], base: Any) -> str:
    summary = pdca["body_summary"]
    audit = summary["historical_verification"]
    investment = summary["investment_predictions"]
    process = summary["process_quality_checks"]
    investment_rows = "".join(
        f"<tr data-investment-prediction='1'><td>{index}</td><td>{base.esc(row['statement'])}</td>"
        f"<td>{base.esc(row['probability_label'])}（{row['probability_pct']}%固定评分值）<br><span class='muted'>{base.esc(row['probability_basis'])}</span></td>"
        f"<td>{base.esc(row['success_definition'])}</td><td>{base.esc(row['counterfactual'])}</td><td>{base.esc(row['verification_date'])}</td></tr>"
        for index, row in enumerate(investment, 1)
    )
    process_rows = "".join(
        f"<tr data-process-qa='1'><td>{base.esc(row['statement'])}</td><td>{base.esc(row['probability_basis'])}</td>"
        f"<td>{base.esc(row['success_definition'])}</td><td>{base.esc(row['verification_date'])}</td></tr>" for row in process
    )
    history_rows = []
    for row in pdca["plain_records"]:
        history_rows.append(
            f"<tr data-pdca-history='1'><td>{row['record_number']}</td><td>{base.esc(row.get('prediction_date'))}<br>{base.esc(row.get('prediction'))}</td>"
            f"<td>{base.esc(row.get('success_definition'))}</td><td>{base.esc(row.get('actual_result'))}<br>{base.esc(row.get('external_evidence'))}</td>"
            f"<td>{base.esc(row.get('verdict'))}<br><span class='muted'>{base.esc(row.get('verification_class'))}</span></td>"
            f"<td><b>归因：</b>{base.esc(row.get('error_or_learning_category'))}<br><b>教训：</b>{base.esc(row.get('lesson'))}"
            f"<br><b>本期修改：</b>{base.esc(row.get('specific_change'))}<br><b>相反选择：</b>{base.esc(row.get('counterfactual'))}</td></tr>"
        )
    changes = "".join(f"<li>{base.esc(value)}</li>" for value in summary.get("system_changes", []))
    return f"""
    <div class="metric-grid"><article class="metric"><b>历史记录</b><strong>57条</strong><small>原始记录全部保留</small></article>
    <article class="metric"><b>可核验跟踪点</b><strong>{audit['verifiable_tracking_points']}条</strong><small>{audit['correct_tracking_points']}条判对，{audit['wrong_tracking_points']}条判错</small></article>
    <article class="metric"><b>无法独立验证</b><strong>{audit['not_independently_verifiable']}条</strong><small>原定义不足，不倒填</small></article>
    <article class="metric"><b>独立序列</b><strong>{audit['independent_prediction_series']}组</strong><small>滚动跟踪点不等于独立预测</small></article></div>
    <p class="boundary">{base.esc(audit['statistics_boundary'])}</p>
    <p><b>投资预测：</b>本期5条，只有这些记录进入未来概率校准。70%是总控批准的“较高”固定评分档，不是由旧跟踪点一致率反推。<b>产品流程QA：</b>1条，不计入投资预测。</p>
    <table><thead><tr><th>序号</th><th>投资预测</th><th>概率档及依据</th><th>成功标准</th><th>相反结果</th><th>验证时间</th></tr></thead><tbody>{investment_rows}</tbody></table>
    <h4>产品流程QA</h4><table><thead><tr><th>检查内容</th><th>采用概率档的原因</th><th>通过标准</th><th>检查时间</th></tr></thead><tbody>{process_rows}</tbody></table>
    <h4>本期从历史记录中改变了什么</h4><ul>{changes}</ul>
    {base.details('57条历史记录：预测、实际、判定、归因和改进', '<table><thead><tr><th>编号</th><th>当时预测</th><th>成功标准</th><th>实际与证据</th><th>判定</th><th>归因、教训与修改</th></tr></thead><tbody>'+''.join(history_rows)+'</tbody></table>', attrs="data-pdca-ledger='57'")}
    """

def semantic_qa(model: dict[str, Any], html_text: str, capability: dict[str, Any], final: dict[str, Any], output_dir: Path, attachment_rows: list[dict[str, Any]], decision_hash: str) -> dict[str, Any]:
    visible = previous.visible_text(html_text)
    research = {row["asset_id"]: row for row in model["research_gates"]}
    shadow = {row["asset_id"]: row for row in model["capabilities"]["shadow_portfolio"]}
    gate_conflicts = [symbol for symbol in research if shadow.get(symbol, {}).get("current_gate_stop") != research[symbol]["formal_gate_stop"]]
    target_errors = []
    for row in model["target_bridge"]["asset_rows"]:
        if row["target_contribution_included"]:
            decision = next(item for item in final["holdings_judgments"] if item["asset_id"] == row["asset_id"])
            calc = weighted_scenario(decision, row["current_price"])
            expected_contribution = row["known_weight_pct"] * calc["expected_return_pct"] / 100.0
            if abs(expected_contribution - row["target_contribution_pp"]) > 1e-6 or not row["current_price_time"] or not row["fx_time"]:
                target_errors.append(row["asset_id"])
    forbidden = {term: visible.count(term) for term in ["Codex取证", "Codex施工", "全产品HTML必须恢复", "本期判断判断", "详见机器附件", "等待GPT总控", "总控必须决定"] if visible.count(term)}
    futu_rows = [row for row in model["single_portfolio_source"]["positions"] if row["account"] == "FUTU"]
    account_dates = {row["account"]: row["quantity_evidence_date"] for row in model["single_portfolio_source"]["positions"] if row["account"] != "FUTU"}
    news_ids = {row["event_id"] for row in model["news"]["records"]}
    new_news_ids = {"NEWS-20260821-GLOBAL-MARKETS", "NEWS-20260820-AVGO-AI-DEBT", "NEWS-20260820-NVDA-CHINA-LPU-DENIAL"}
    new_layer_facts = [fact for layer in model["layers"] for fact in layer.get("facts", []) if fact.get("event_id") in new_news_ids]
    new_layer_facts_complete = bool(new_layer_facts) and all(fact.get("supports") and fact.get("cannot_prove") for fact in new_layer_facts)
    news_window_ok = model["news"]["search_started_at_jst"] < model["news"]["evidence_cutoff_jst"] <= model["news"]["search_finished_at_jst"] and model["news"]["evidence_cutoff_jst"] == model["evidence_cutoff_jst"]
    html_counts = {
        "holdings": len(re.findall(r"data-holding=['\"]", html_text)),
        "research": len(re.findall(r"data-research=['\"]", html_text)),
        "gates": len(re.findall(r"data-gate-row=['\"]1['\"]", html_text)),
        "target": len(re.findall(r"data-target-row=['\"]", html_text)),
        "investment_predictions": len(re.findall(r"data-investment-prediction=['\"]1['\"]", html_text)),
        "process_qa": len(re.findall(r"data-process-qa=['\"]1['\"]", html_text)),
        "pdca_history": len(re.findall(r"data-pdca-history=['\"]1['\"]", html_text)),
    }
    expected_risk = model["single_portfolio_source"]["risk"]
    layer6 = next(row for row in model["layers"] if row["layer"] == 6)
    layer6_by_title = {row.get("title"): row for row in layer6.get("facts", [])}
    stale_account_terms = ["312,884,485.80", "33.42%", "47.02%", "13.36%"]
    stale_account_hits = {term: visible.count(term) for term in stale_account_terms if visible.count(term)}
    account_fact_values_ok = (
        f"{model['single_portfolio_source']['known_assets_total_jpy']:,.2f}" in str(layer6_by_title.get("唯一账户口径"))
        and f"{expected_risk['ai_direct']['known_total_ratio_pct']:.2f}%" in str(layer6_by_title.get("AI同一驱动"))
        and f"{expected_risk['ai_broad_with_softbank_proxy']['known_total_ratio_pct']:.2f}%" in str(layer6_by_title.get("AI同一驱动"))
        and f"{expected_risk['crypto_broad_with_related_equities']['known_total_ratio_pct']:.2f}%" in str(layer6_by_title.get("加密同一驱动"))
    )
    price_conflicts = []
    for symbol, item in research.items():
        quote = item["current_quote"]
        gate_fact = item["gates"][2].get("fact") if isinstance(item["gates"][2].get("fact"), dict) else {}
        if isinstance(item["gates"][2].get("fact"), dict) and (
            gate_fact.get("current_price") != quote.get("last_price")
            or gate_fact.get("price_time") != quote.get("update_time")
            or gate_fact.get("pe_ratio_market_snapshot") != quote.get("pe_ratio")
            or gate_fact.get("pb_ratio_market_snapshot") != quote.get("pb_ratio")
        ):
            price_conflicts.append({"asset_id": symbol, "quote": quote, "gate3": gate_fact})
    price_checked = sum(isinstance(item["gates"][2].get("fact"), dict) for item in research.values())
    required_price_symbols = {"US.CEG", "US.CVX", "US.MU", "US.VRT", "US.WDC", "US.XOM", "US.MRVL"}
    required_price_symbols_checked = all(symbol in research and isinstance(research[symbol]["gates"][2].get("fact"), dict) for symbol in required_price_symbols)
    event_rows = []
    event_contradictions = []
    for item in model["holdings"]:
        role = next((row for row in item.get("precise_evidence_roles", []) if row.get("role") == "公司或行业事件"), None)
        event_rows.append({"asset_id": item["asset_id"], "role": role})
        if not role:
            event_contradictions.append({"asset_id": item["asset_id"], "reason": "缺少公司事件角色"})
        elif role.get("status") == "已取得本批次独立公司事件":
            if not all(role.get(key) for key in ("title", "publisher", "published_at", "locator", "url", "supports")):
                event_contradictions.append({"asset_id": item["asset_id"], "reason": "已取得但定位不完整"})
        elif role.get("status") == "截止时间内未取得独立公司事件":
            if role.get("url") is not None or "未取得" not in str(role.get("title")):
                event_contradictions.append({"asset_id": item["asset_id"], "reason": "未取得状态仍有占位链接或错误标题"})
        else:
            event_contradictions.append({"asset_id": item["asset_id"], "reason": "未知事件状态"})
    event_obtained = [row["asset_id"] for row in event_rows if row["role"] and row["role"].get("status") == "已取得本批次独立公司事件"]
    event_missing = [row["asset_id"] for row in event_rows if row["role"] and row["role"].get("status") == "截止时间内未取得独立公司事件"]
    history = model["pdca"]["plain_records"]
    historical = model["pdca"]["body_summary"]["historical_verification"]
    investment_basis = [row.get("probability_basis") for row in model["pdca"]["body_summary"]["investment_predictions"]]
    current_snapshot = model["news"]["current_market_snapshot"]
    snapshot_records = current_snapshot["records"]
    snapshot_by_name = {row["indicator"]: row for row in snapshot_records}
    cutoff_time = datetime.fromisoformat(current_snapshot["evidence_cutoff_jst"])
    snapshot_fields_complete = (
        len(snapshot_records) == len(CURRENT_MARKET_NAMES)
        and set(snapshot_by_name) == set(CURRENT_MARKET_NAMES)
        and all(
            row.get("role") == "本批次当前行情"
            and row.get("source") and row.get("source_url") and row.get("raw_sha256")
            and datetime.fromisoformat(row["market_time_jst"]) <= cutoff_time
            for row in snapshot_records
        )
    )
    global_market_event = next(row for row in model["news"]["records"] if row.get("event_id") == "NEWS-20260821-GLOBAL-MARKETS")
    required_market_layers = (1, 3, 4, 6)
    layer_market_matches = {
        number: [fact for fact in next(row for row in model["layers"] if row["layer"] == number).get("facts", []) if fact.get("event_id") == "NEWS-20260821-GLOBAL-MARKETS"]
        for number in required_market_layers
    }
    layer_market_unique = all(
        len(matches) == 1
        and matches[0].get("fact") == global_market_event["fact"]
        and matches[0].get("market_snapshot") == snapshot_records
        and matches[0].get("market_role") == "本批次当前行情"
        for matches in layer_market_matches.values()
    )
    market_trace_details = [
        evidence
        for trace in model["traceability"]
        for evidence in trace.get("evidence_details", [])
        if evidence.get("title") == global_market_event["title"]
    ]
    trace_market_unique = bool(market_trace_details) and all(
        evidence.get("fact") == global_market_event["fact"]
        and evidence.get("market_snapshot") == snapshot_records
        and evidence.get("market_role") == "本批次当前行情"
        and evidence.get("evidence_cutoff_jst") == current_snapshot["evidence_cutoff_jst"]
        for evidence in market_trace_details
    )
    stale_market_phrases = (
        "美国10年期收益率快照约4.65%，30年期约5.19%",
        "日经225盘中约65,952.94，较上一可比值-3.45%",
        "WTI约84.58美元、布伦特约91.93美元",
    )
    stale_market_hits = {term: visible.count(term) for term in stale_market_phrases if visible.count(term)}
    holdings_by_id = {row["asset_id"]: row for row in model["holdings"]}
    market_action_consistent = (
        "持有" in holdings_by_id["US.AVGO"]["action"]["unique_action"]
        and "不追价" in holdings_by_id["US.AVGO"]["action"]["unique_action"]
        and "持有" in holdings_by_id["US.NVDA"]["action"]["unique_action"]
        and "不追价" in holdings_by_id["US.NVDA"]["action"]["unique_action"]
        and research["US.XOM"]["final_opportunity_judgment"]["gate5"] != "第五关通过"
        and research["US.CVX"]["final_opportunity_judgment"]["gate5"] != "第五关通过"
        and all(term in next(row for row in model["layers"] if row["layer"] == 4)["transmission"] for term in ("AVGO", "NVDA", "XOM", "CVX"))
    )
    checks = {
        "Q01新闻窗口与增量事件": {"pass": news_window_ok and new_news_ids.issubset(news_ids) and new_layer_facts_complete, "detail": {"window_ok": news_window_ok, "new_event_count": len(news_ids & new_news_ids), "layer_transmission_complete": new_layer_facts_complete}},
        "Q02富途8月21日账户实测": {"pass": len(futu_rows) == 12 and all(row["quantity_evidence_date"] == "2026-08-21" for row in futu_rows) and model["single_portfolio_source"]["refresh_audit"]["futu_snapshot_run_id"].startswith("FUTU-RO-20260821"), "detail": {"positions": len(futu_rows), "snapshot": model["single_portfolio_source"]["refresh_audit"]}},
        "Q03手工账户日期边界": {"pass": account_dates.get("SBI账户归属尚未确认") == "2026-08-19 18:50 JST" and account_dates.get("IBKR") == "2026-08-04" and account_dates.get("bitFlyer") == "2026-08-11" and all(term in visible for term in ["2026-08-19 18:50 JST", "2026-08-04最后截图", "2026-08-11最后截图"]), "detail": account_dates},
        "Q04跨章节五关唯一": {"pass": len(research) == 18 and len(shadow) == 18 and not gate_conflicts, "detail": {"research": len(research), "shadow": len(shadow), "conflicts": gate_conflicts}},
        "Q05目标贡献可见复算": {"pass": len([row for row in model["target_bridge"]["asset_rows"] if row["target_contribution_included"]]) == 9 and not target_errors and "上一版恰好为0" in visible and html_counts["target"] == 24, "detail": {"errors": target_errors, "html_rows": html_counts["target"]}},
        "Q06PDCA分类与全文": {"pass": len(model["pdca"]["plain_records"]) == 57 and len(model["pdca"]["body_summary"]["investment_predictions"]) == 5 and len(model["pdca"]["body_summary"]["process_quality_checks"]) == 1 and html_counts["pdca_history"] == 57 and html_counts["investment_predictions"] == 5 and html_counts["process_qa"] == 1 and "三条新质量基线" not in visible and "新建3条预测基线" not in visible, "detail": html_counts},
        "Q07完整HTML自足": {"pass": all(term in visible for term in ["8月21日富途账户已通过富途只读账户接口只读刷新", "可见计算桥", "57条历史记录", "产品流程QA"]) and "详见机器附件" not in visible, "detail": {"required_visible": True}},
        "Q08内部施工语言": {"pass": not forbidden, "detail": forbidden},
        "Q09结构与冻结边界": {"pass": html_counts["holdings"] == 24 and html_counts["research"] == 18 and html_counts["gates"] == 90 and not list(output_dir.glob("*.pdf")) and model["status"] == previous.STATUS, "detail": html_counts},
        "Q10UTF8与本地路径": {"pass": b"\xef\xbf\xbd" not in html_text.encode("utf-8") and not re.search(r"(?i)(?:[A-Z]:\\|file://)", visible), "detail": {"replacement": html_text.encode("utf-8").count(b"\xef\xbf\xbd")}},
        "Q11全账户唯一风险口径": {"pass": account_fact_values_ok and not stale_account_hits, "detail": {"known_assets_jpy": model["single_portfolio_source"]["known_assets_total_jpy"], "risk": expected_risk, "layer6_facts_match": account_fact_values_ok, "stale_hits": stale_account_hits}},
        "Q12研究行情单一来源": {"pass": len(research) == 18 and price_checked >= 7 and required_price_symbols_checked and not price_conflicts, "detail": {"research_count": len(research), "third_gate_price_checked": price_checked, "required_symbols_checked": required_price_symbols_checked, "conflicts": price_conflicts}},
        "Q13公司事件证据状态": {"pass": len(event_rows) == 24 and len(event_obtained) == 2 and len(event_missing) == 22 and not event_contradictions and set(event_obtained) == {"US.AVGO", "US.NVDA"}, "detail": {"checked": len(event_rows), "obtained": event_obtained, "missing_count": len(event_missing), "contradictions": event_contradictions}},
        "Q14PDCA真实闭环": {"pass": len(history) == 57 and historical["verifiable_tracking_points"] == 29 and historical["correct_tracking_points"] == 29 and historical["wrong_tracking_points"] == 0 and historical["not_independently_verifiable"] == 28 and all(row.get("error_or_learning_category") and row.get("specific_change") for row in history) and len(investment_basis) == 5 and all(investment_basis) and len(set(investment_basis)) == 5, "detail": {"historical": historical, "attribution_missing": [row["record_number"] for row in history if not row.get("error_or_learning_category") or not row.get("specific_change")], "investment_probability_basis_count": len(investment_basis), "unique_probability_basis_count": len(set(investment_basis))}},
        "Q15跨章节市场指标唯一": {
            "pass": snapshot_fields_complete and global_market_event.get("market_snapshot") == snapshot_records and global_market_event.get("fact") == current_snapshot["fact"] and layer_market_unique and trace_market_unique and market_action_consistent and not stale_market_hits,
            "detail": {
                "evidence_cutoff_jst": current_snapshot["evidence_cutoff_jst"],
                "indicator_count": len(snapshot_records),
                "indicator_times": {row["indicator"]: row["market_time_jst"] for row in snapshot_records},
                "layer_current_event_counts": {str(number): len(matches) for number, matches in layer_market_matches.items()},
                "trace_current_event_count": len(market_trace_details),
                "removed_legacy_current_facts": model["market_snapshot_uniqueness"]["removed_legacy_current_facts"],
                "stale_current_phrase_hits": stale_market_hits,
                "market_action_consistent": market_action_consistent,
            },
        },
    }
    failures = [key for key, result in checks.items() if not result["pass"]]
    return {"schema_version": "V7-STAGEC-RETURN-SEMANTIC-QA-4.0", "run_id": model["run_id"], "checked_at_jst": datetime.now(JST).isoformat(timespec="seconds"), "checks": checks, "pass_count": len(checks) - len(failures), "check_count": len(checks), "failures": failures, "status": "INTERNAL_QA_PASS_WAITING_GPT_FULL_HTML_CONTENT_GATE" if not failures else "FAIL", "self_declared_content_gate_pass": False, "pdf_render_authorized": False}


def rebuild_traceability(model: dict[str, Any]) -> list[dict[str, Any]]:
    rows = ORIGINAL_REBUILD_TRACEABILITY(model)
    by_conclusion = {row.get("conclusion"): row for row in rows}
    for item in model["holdings"]:
        key = f"{item['asset_id']}｜{item['name']}唯一动作"
        target = by_conclusion.get(key)
        event = next((row for row in item.get("precise_evidence_roles", []) if row.get("role") == "公司或行业事件"), None)
        if target is not None and event is not None:
            target.setdefault("evidence_details", []).append({
                "title": event.get("title"), "publisher": event.get("publisher"),
                "published_at": event.get("published_at"), "url": event.get("url"),
                "supports": event.get("supports"), "cannot_prove": event.get("cannot_prove"),
                "status": event.get("status"), "locator": event.get("locator"),
            })
    market_event = next(row for row in model["news"]["records"] if row.get("event_id") == "NEWS-20260821-GLOBAL-MARKETS")
    for trace in rows:
        for evidence in trace.get("evidence_details", []):
            if evidence.get("title") == market_event["title"]:
                evidence.update({
                    "fact": market_event["fact"],
                    "data_date": market_event["data_date"],
                    "retrieved_at_jst": market_event["retrieved_at_jst"],
                    "evidence_cutoff_jst": market_event["evidence_cutoff_jst"],
                    "market_role": market_event["market_role"],
                    "market_snapshot": copy.deepcopy(market_event["market_snapshot"]),
                })
    return rows

ORIGINAL_APPLY_HOLDINGS = previous.apply_holdings
ORIGINAL_APPLY_RESEARCH = previous.apply_research
ORIGINAL_APPLY_FIRST_LAYER = previous.apply_first_layer
ORIGINAL_INJECT = previous.legacy.inject_market_reversal
ORIGINAL_WRITE_ATTACHMENT = previous.write_attachment
ORIGINAL_REBUILD_TRACEABILITY = previous.rebuild_traceability


def write_attachment(path: Path, value: Any, purpose: str) -> dict[str, Any]:
    if path.name == "01_PDCA历史57条及新预测.json":
        purpose = "57条历史记录的真实复核、5条投资预测与1条产品流程QA"
    elif path.name == "12_PDCA概率校准规则.json":
        purpose = "固定概率档位、逐条概率依据、5条投资预测与1条产品流程QA"
    elif path.name == "13_能力闭合修改前后清单.json":
        value["content_gate_return_fixes"] = [
            {"item": "全账户风险口径", "before": "七层仍保留旧总额和旧暴露比例", "after": "驾驶舱、七层和证据附件统一使用8月21日唯一账户源"},
            {"item": "七只研究股行情", "before": "当前行情与第三关来自两个快照", "after": "当前价、时间、市盈率、市净率及第五关理由从证券代码唯一行情源生成"},
            {"item": "持仓公司事件", "before": "22张卡以财报链接占位并误称已取得事件", "after": "22张诚实登记未取得独立公司事件；AVGO和NVDA保留实际事件原文"},
            {"item": "PDCA", "before": "57条全部因无网页链接被判无法验证", "after": "29条按原阈值和富途复权日K恢复判定，28条定义不足继续退出；新预测补齐逐条概率依据"},
            {"item": "市场指标唯一性", "before": "七层残留阶段A旧利率、油价和股指并与8月21日快照并列", "after": "七层、新闻、证据追踪、板块与动作统一使用截至2026-08-21 22:49:18 JST的逐项带时间快照"},
        ]
        purpose = "本轮已闭合四项与市场指标唯一性返修前后及冻结章节说明"
    return ORIGINAL_WRITE_ATTACHMENT(path, value, purpose)


def main() -> int:
    global ACCOUNT_SOURCE, FUTU_SNAPSHOT, MARKET_FACTS
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-renderer", required=True, type=Path)
    parser.add_argument("--base-model", required=True, type=Path)
    parser.add_argument("--capability-input", required=True, type=Path)
    parser.add_argument("--final-judgment", required=True, type=Path)
    parser.add_argument("--previous-account-source", required=True, type=Path)
    parser.add_argument("--futu-snapshot", required=True, type=Path)
    parser.add_argument("--market-facts", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--daily-report", required=True, type=Path)
    args = parser.parse_args()
    ACCOUNT_SOURCE = load_json(args.previous_account_source)["data"]
    FUTU_SNAPSHOT = load_json(args.futu_snapshot)
    MARKET_FACTS = load_json(args.market_facts)
    previous.apply_holdings = apply_holdings
    previous.apply_research = apply_research
    previous.build_target_bridge = build_target_bridge
    previous.apply_pdca = apply_pdca
    previous.apply_first_layer = apply_first_layer
    previous.render_target_bridge = render_target_bridge
    previous.render_pdca = render_pdca
    previous.semantic_qa = semantic_qa
    previous.write_attachment = write_attachment
    previous.rebuild_traceability = rebuild_traceability
    previous.legacy.inject_market_reversal = inject_content
    previous.legacy.VISIBLE_TERM_MAP.update({
        "Codex取证，本期判断判断": "数据证据由系统更新，投资判断由投研主脑统一裁定",
        "Codex施工，本期判断全读验收": "产品生成后由总控执行全文内容闸",
        "全产品HTML必须恢复": "完整产品必须持续保留",
        "未由Codex取得原文": "本批次未直接取得原文",
    })
    sys.argv = [
        sys.argv[0], "--base-renderer", str(args.base_renderer), "--base-model", str(args.base_model),
        "--capability-input", str(args.capability_input), "--final-judgment", str(args.final_judgment),
        "--output-dir", str(args.output_dir), "--run-id", args.run_id,
        "--daily-report", str(args.daily_report),
    ]
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
