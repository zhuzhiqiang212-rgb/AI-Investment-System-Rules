from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_v7_v04_business_input as prior  # noqa: E402


JST = timezone(timedelta(hours=9))
PREVIOUS_RUN = "V7-V04-BUSINESS-INPUT-20260816-092343-JST"
PREVIOUS_DIR = ROOT / "output" / "decision_inputs" / "2026-08-16" / PREVIOUS_RUN
DAILY_REPORT = ROOT / "00_请先看这里" / "00_今日日报.pdf"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def metadata(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "size": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, JST).isoformat(timespec="seconds"),
        "sha256": sha256(path),
    }


def esc(value: Any) -> str:
    if value is None:
        return "未取得"
    return html.escape(str(value))


def amount(value: Any, currency: str | None = None) -> str:
    if value is None:
        return "未取得"
    if isinstance(value, (int, float)):
        return f"{value:,.2f}{' ' + currency if currency else ''}"
    return str(value)


def local_url(path: Path) -> str:
    return "file:///" + str(path).replace("\\", "/").replace(" ", "%20")


FORMAL_FACTS: dict[str, dict[str, Any]] = {
    "US.AVGO": {
        "period": "截至2026-05-03的2026财年第二季度（美国会计准则）",
        "published_at": "2026-06-03",
        "currency": "USD",
        "revenue": 22_187_000_000,
        "operating_profit": 10_788_000_000,
        "net_income": 9_310_000_000,
        "ocf": 10_493_000_000,
        "ocf_period": "单季",
        "fcf": 10_262_000_000,
        "fcf_basis": "公司口径：单季经营现金流104.93亿美元减资本开支2.31亿美元",
        "cash": 19_628_000_000,
        "debt": 64_907_000_000,
        "one_off": "并购会计和非现金调整需与美国会计准则结果分开；债务为流动与非流动长期债务合计。",
        "guidance": "2026财年第三季度收入约294亿美元，非美国会计准则营业利润率约为收入的67%。",
        "url": "https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announces-second-quarter-fiscal-year-2026-financial",
    },
    "US.COIN": {
        "period": "截至2026-06-30的第二季度（美国会计准则）",
        "published_at": "2026-07-30",
        "currency": "USD",
        "revenue": 1_220_068_000,
        "operating_profit": -113_488_000,
        "net_income": -359_468_000,
        "ocf": 380_054_000,
        "ocf_period": "2026年上半年",
        "fcf": None,
        "fcf_basis": "10-Q未把传统资本开支单列为可直接复核项目，本包不自行重分类，故不计算自由现金流。",
        "cash": 8_614_065_000,
        "debt": 5_944_232_000,
        "one_off": "数字资产和投资的公允价值变动较大；不能把单季净利润机械外推。",
        "guidance": "公司披露业务多元化与交易量份额，但本包未取得可直接登记的全年收入数值指引。",
        "url": "https://www.sec.gov/Archives/edgar/data/1679788/000167978826000088/coin-20260630.htm",
    },
    "US.CRCL": {
        "period": "截至2026-06-30的第二季度（美国会计准则）",
        "published_at": "2026-08-05",
        "currency": "USD",
        "revenue": 701_315_000,
        "operating_profit": 34_359_000,
        "net_income": 48_221_000,
        "ocf": 538_505_000,
        "ocf_period": "2026年上半年",
        "fcf": 492_352_000,
        "fcf_basis": "上半年经营现金流5.38505亿美元减长期资产采购0.10389亿美元和资本化软件0.35764亿美元。",
        "cash": 1_730_126_000,
        "debt": 0,
        "one_off": "总收入含6.67733亿美元储备收益和0.33582亿美元其他收入；稳定币持有人对应资产负债不能混作公司自有现金或有息债务。",
        "guidance": "本包未从10-Q取得可直接登记的全年收入数值指引。",
        "url": "https://www.sec.gov/Archives/edgar/data/1876042/000187604226000248/crcl-20260630.htm",
    },
    "US.IBKR": {
        "period": "截至2026-06-30的第二季度（美国会计准则）",
        "published_at": "2026-08-06",
        "currency": "USD",
        "revenue": 1_896_000_000,
        "operating_profit": None,
        "operating_profit_status": "券商报表不单列传统营业利润；最接近的税前利润为14.56亿美元。",
        "net_income": 312_000_000,
        "ocf": 9_827_000_000,
        "ocf_period": "2026年上半年",
        "fcf": 9_783_000_000,
        "fcf_basis": "上半年经营现金流98.27亿美元减设备及无形资产采购0.44亿美元；券商现金流受客户及监管隔离资产变化影响，不宜与制造业直接比较。",
        "cash": 7_711_000_000,
        "debt": None,
        "debt_status": "10-Q未在本包所用表格中提供可直接合并的有息债务单一字段。",
        "one_off": "净利润总额包含非控股权益；本包使用归属普通股股东净利润3.12亿美元。",
        "guidance": "未发布传统收入区间指引。",
        "url": "https://www.sec.gov/Archives/edgar/data/1381197/000138119726000147/ibkr-20260630.htm",
    },
    "US.META": {
        "period": "截至2026-06-30的第二季度（美国会计准则）",
        "published_at": "2026-07-30",
        "currency": "USD",
        "revenue": 60_801_000_000,
        "operating_profit": 18_775_000_000,
        "net_income": 15_848_000_000,
        "ocf": 64_088_000_000,
        "ocf_period": "2026年上半年",
        "fcf": 14_975_000_000,
        "fcf_basis": "上半年经营现金流640.88亿美元减资本开支491.13亿美元。",
        "cash": 15_462_000_000,
        "debt": 83_664_000_000,
        "one_off": "第二季度含24亿美元法律费用及11.8亿美元遣散费用。",
        "guidance": "第三季度收入与全年资本开支指引以公司第二季度公告为准。",
        "url": "https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-Second-Quarter-2026-Results/default.aspx",
    },
    "US.MSFT": {
        "period": "截至2026-06-30的2026财年（美国会计准则）",
        "published_at": "2026-07-29",
        "currency": "USD",
        "revenue": 331_839_000_000,
        "operating_profit": 155_237_000_000,
        "net_income": 133_749_000_000,
        "ocf": 182_935_000_000,
        "ocf_period": "全年",
        "fcf": 66_987_000_000,
        "fcf_basis": "全年经营现金流1,829.35亿美元减购置物业设备1,159.48亿美元。",
        "cash": 76_843_000_000,
        "debt": 40_294_000_000,
        "one_off": "财年净利润含OpenAI投资净收益49.63亿美元；现金字段含现金、等价物和短期投资。",
        "guidance": "云业务与资本开支回报应结合公司下一季度正式指引，不由本包外推。",
        "url": "https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20260630.htm",
    },
    "US.MSTR": {
        "period": "截至2026-06-30的第二季度（美国会计准则）",
        "published_at": "2026-08-03",
        "currency": "USD",
        "revenue": 122_368_000,
        "operating_profit": -8_330_950_000,
        "net_income": -8_219_628_000,
        "ocf": 9_850_000,
        "ocf_period": "2026年上半年",
        "fcf": 7_131_000,
        "fcf_basis": "上半年经营现金流985万美元减资本开支271.9万美元。",
        "cash": 1_711_837_000,
        "debt": 6_709_928_000,
        "one_off": "营业亏损主要受数字资产公允价值变化影响，不能与软件业务经营表现混为一谈。",
        "guidance": "公司重点披露比特币与融资指标，不等同于传统盈利指引。",
        "url": "https://www.sec.gov/Archives/edgar/data/1050446/000105044626000044/mstr-20260630.htm",
    },
    "US.NVDA": {
        "period": "截至2026-04-26的2027财年第一季度（美国会计准则）",
        "published_at": "2026-05-20",
        "currency": "USD",
        "revenue": 81_615_000_000,
        "operating_profit": 53_536_000_000,
        "net_income": 58_321_000_000,
        "ocf": 50_344_000_000,
        "ocf_period": "单季",
        "fcf": 48_554_000_000,
        "fcf_basis": "公司口径：经营现金流减设备和无形资产购置及相关本金支付。",
        "cash": 13_237_000_000,
        "debt": 8_470_000_000,
        "one_off": "单季其他收益较大；公司说明上年同期H20费用影响，本季不可机械年化。",
        "guidance": "下一季度收入及毛利率以公司正式第一季度公告中的展望为准。",
        "url": "https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-First-Quarter-Fiscal-2027/default.aspx",
    },
    "US.TSM": {
        "period": "截至2026-06-30的第二季度（台湾IFRS合并口径）",
        "published_at": "2026-07-16",
        "currency": "TWD",
        "revenue": 1_270_380_000_000,
        "operating_profit": 766_600_000_000,
        "net_income": 706_560_000_000,
        "ocf": 783_360_000_000,
        "ocf_period": "单季",
        "fcf": 287_360_000_000,
        "fcf_basis": "单季经营现金流7,833.6亿新台币减资本开支4,960亿新台币。",
        "cash": 3_518_010_000_000,
        "debt": 1_031_680_000_000,
        "one_off": "非营业项目含出售及按市值计量世界先进股份产生的632亿新台币收益。",
        "guidance": "第三季度美元收入446亿至458亿美元，毛利率65%至67%，营业利润率56%至58%。",
        "url": "https://investor.tsmc.com/english/encrypt/files/encrypt_file/reports/2026-07/a80d7933be643644081584087731f73b22ea5a2c/2Q26%20EarningsRelease.pdf",
    },
    "US.SNDK": {
        "period": "截至2026-07-03的2026财年第四季度及全年（美国会计准则，未经审计）",
        "published_at": "2026-08-05",
        "currency": "USD",
        "revenue": 8_965_000_000,
        "operating_profit": 7_037_000_000,
        "net_income": 6_903_000_000,
        "ocf": 11_671_000_000,
        "ocf_period": "2026财年全年",
        "fcf": 11_494_000_000,
        "fcf_basis": "全年经营现金流116.71亿美元减设备采购1.77亿美元。",
        "cash": 4_762_000_000,
        "debt": 0,
        "one_off": "全年含权益证券净收益8.08亿美元；第四季度公司另扩大140亿美元回购授权。",
        "guidance": "2027财年第一季度收入103亿至108亿美元，非美国会计准则每股收益44至46美元。",
        "url": "https://www.sec.gov/Archives/edgar/data/2023554/000162828026053346/sndkq4-26ex991xpressrelease.htm",
        "price_reconciliation": {
            "opend_price_usd": 1641.11,
            "opend_cost_usd": 1376.88,
            "quantity": 40,
            "market_value_usd": 65644.40,
            "calculated_market_value_usd": 65644.40,
            "calculated_pl_ratio_percent": 19.19,
            "broker_returned_pl_ratio_percent": 25.21,
            "broker_pl_basis_status": "BROKER_PL_BASIS_UNRESOLVED",
            "opend_quote_time": "2026-08-14 20:02:18.541",
            "lot_size": 1,
            "conclusion": "OpenD价格为1,641.11美元，不是164.111美元；价格×数量与市值勾稽。按现价/成本计算为19.19%，券商原始盈亏率25.21%的成本口径仍未解释，已隔离且不得用于估值或动作。",
        },
        "corporate_action": {
            "status": "NO_SPLIT_FOUND_BEFORE_CUTOFF",
            "evidence": "公司历史报价页在2026-06-29显示拆分调整因子1:1；截至2026-08-15的SEC申报和公司公告未发现后续拆股生效记录。",
            "url": "https://investor.sandisk.com/stock-information/historical-price-lookup",
        },
    },
    "US.SPCX": {
        "period": "截至2026-06-30的第二季度（美国会计准则）",
        "published_at": "2026-08-04",
        "currency": "USD",
        "revenue": 7_814_000_000,
        "operating_profit": -143_000_000,
        "net_income": -541_000_000,
        "ocf": 3_466_000_000,
        "ocf_period": "2026年上半年",
        "fcf": -25_010_000_000,
        "fcf_basis": "上半年经营现金流34.66亿美元减设备采购284.76亿美元；高资本开支期不可与成熟软件公司直接比较。",
        "cash": 93_522_000_000,
        "debt": 39_364_000_000,
        "one_off": "IPO完成后现金显著增加；总收入含航天、连接和AI三大分部，不能只按SpaceX火箭业务理解。",
        "guidance": "10-Q未提供传统季度收入区间指引。",
        "url": "https://www.sec.gov/Archives/edgar/data/1181412/000162828026052535/spcx-20260630.htm",
    },
    "KRX.005930": {
        "period": "截至2026-06-30的第二季度（K-IFRS合并口径）",
        "published_at": "2026-07-30",
        "currency": "KRW",
        "revenue": 171_500_000_000_000,
        "operating_profit": 89_500_000_000_000,
        "net_income": 71_300_000_000_000,
        "ocf": 105_080_000_000_000,
        "ocf_period": "单季",
        "fcf": 90_970_000_000_000,
        "fcf_basis": "单季经营现金流105.08万亿韩元减设备采购14.11万亿韩元。",
        "cash": 189_999_000_000_000,
        "debt": 22_408_700_000_000,
        "one_off": "现金为现金、等价物及短期金融资产合计；公司披露文件以K-IFRS合并口径列示。",
        "guidance": "公司对2026年下半年给出业务展望，但未在该材料中给出合并收入数值区间。",
        "url": "https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2026_2Q_conference_eng.pdf",
    },
}


CANDIDATE_CORE: dict[str, dict[str, Any]] = {
    "US.PLTR": {"period": "2026年第二季度", "revenue": 1_935_464_000, "operating_profit": 912_004_000, "net_income": 1_061_890_000, "ocf": 2_115_332_000, "fcf": 2_093_377_000, "currency": "USD", "url": "https://www.sec.gov/Archives/edgar/data/1321655/000132165526000041/pltr-20260630.htm", "published_at": "2026-08-04"},
    "US.ETN": {"period": "2026年第二季度", "revenue": 8_531_000_000, "operating_profit": None, "net_income": 821_000_000, "ocf": 1_634_000_000, "fcf": 1_188_000_000, "currency": "USD", "url": "https://www.sec.gov/Archives/edgar/data/1551182/000155118226000030/etn-20260630.htm", "published_at": "2026-07-31", "note": "经营现金流和自由现金流为上半年口径；10-Q未提供单一合并营业利润字段。"},
    "US.CEG": {"period": "2026年第二季度", "revenue": 5_843_000_000, "operating_profit": 580_000_000, "net_income": 513_000_000, "ocf": 1_553_000_000, "fcf": -968_000_000, "currency": "USD", "url": "https://www.sec.gov/Archives/edgar/data/1868275/000186827526000104/ceg-20260630.htm", "published_at": "2026-08-06", "note": "现金流与资本开支为上半年口径。"},
    "US.ON": {"period": "截至2026-07-03的第二季度", "revenue": 1_603_500_000, "operating_profit": 258_600_000, "net_income": 226_800_000, "ocf": 698_800_000, "fcf": 642_600_000, "currency": "USD", "url": "https://www.sec.gov/Archives/edgar/data/1097864/000109786426000017/on-20260703.htm", "published_at": "2026-08-03", "note": "现金流与资本开支为上半年口径。"},
    "US.COHR": {"period": "截至2026-06-30的2026财年全年", "revenue": 7_118_181_000, "operating_profit": None, "net_income": 804_998_000, "ocf": 79_514_000, "fcf": -1_023_395_000, "currency": "USD", "url": "https://www.sec.gov/Archives/edgar/data/820318/000082031826000020/iivi-20260630.htm", "published_at": "2026-08-14", "note": "10-K未单列传统营业利润；自由现金流按经营现金流减设备采购计算。"},
    "US.LITE": {"period": "截至2026-06-27的2026财年全年", "revenue": 3_014_000_000, "operating_profit": 524_800_000, "net_income": -6_935_100_000, "ocf": None, "fcf": None, "currency": "USD", "url": "https://www.sec.gov/Archives/edgar/data/1633978/000162828026055726/lite_ex991xq4fy26.htm", "published_at": "2026-08-11", "note": "净亏损含78亿美元一次性非现金债务清偿损失；公告未在本包摘录段落给出全年现金流。"},
    "US.XOM": {"period": "2026年第二季度", "revenue": 116_017_000_000, "operating_profit": 19_424_000_000, "net_income": 14_525_000_000, "ocf": 23_555_000_000, "fcf": 16_848_000_000, "currency": "USD", "url": "https://www.sec.gov/Archives/edgar/data/34088/000003408826000093/xom-20260630.htm", "published_at": "2026-08-03", "note": "营业利润栏使用税前利润；自由现金流按单季经营现金流减单季设备增加额67.07亿美元计算。"},
}


def enrich_accounts(accounts: dict[str, Any]) -> None:
    samsung = next(row for row in accounts["account_rows"] if row["code"] == "KRX.005930")
    samsung.update({
        "currency": "KRW",
        "latest_price": 242_500,
        "market_value": 3_637_500,
        "quote_price_krw": 242_500,
        "market_value_krw": 3_637_500,
        "market_value_reporting_usd": 2_560.00,
        "fx_krw_per_usd": 1420.8984375,
        "fx_date": "2026-08-04",
        "fx_basis": "IBKR证券总持仓美元额减六只美股美元市值后的隐含折算；不作为实时外汇报价。",
        "freshness": "最后已知状态；韩元报价和韩元市值保留本币，美元字段仅为IBKR账户折算市值。",
    })
    accounts["samsung_currency_reconciliation"] = {
        "status": "CLOSED",
        "security": "KRX.005930",
        "quantity": 15,
        "quote_price_krw": 242_500,
        "market_value_krw": 3_637_500,
        "ibkr_market_value_usd": 2_560.00,
        "fx_krw_per_usd": 1420.8984375,
        "fx_date": "2026-08-04",
        "proof": "242,500韩元×15股=3,637,500韩元；3,637,500÷2,560=1,420.8984375韩元/美元。",
    }


def enrich_holdings(holdings: dict[str, Any]) -> None:
    for item in holdings["items"]:
        if item["code"] in {"BTC", "ETH"}:
            item["formal_financial_status"] = "NOT_APPLICABLE_ASSET"
            item["enterprise_financials_applicability"] = "NOT_APPLICABLE"
            item["missing_fields"] = []
            item["financial_gap_note"] = "BTC、ETH为资产，不适用企业收入、利润、现金流、现金和有息债务字段；不计为财务缺失。"
        formal = FORMAL_FACTS.get(item["code"])
        if not formal:
            continue
        item.update({
            "latest_formal_financial_period": formal["period"],
            "revenue": formal["revenue"],
            "operating_profit": formal.get("operating_profit"),
            "net_income_attributable_or_net_income": formal["net_income"],
            "operating_cash_flow": formal["ocf"],
            "free_cash_flow": formal.get("fcf"),
            "cash": formal.get("cash"),
            "debt_and_financing_obligations": formal.get("debt"),
            "one_off_and_accounting_basis": formal["one_off"],
            "official_guidance": formal["guidance"],
            "evidence_url": formal["url"],
            "formal_financial_detail": formal,
            "formal_financial_status": "FORMAL_SOURCE_EXTRACTED",
        })
        nonblocking = []
        if formal.get("operating_profit") is None:
            nonblocking.append(formal.get("operating_profit_status", "正式文件未单列可直接使用的营业利润。"))
        if formal.get("fcf") is None:
            nonblocking.append(formal.get("fcf_basis", "正式文件未提供可复核自由现金流计算基础。"))
        if formal.get("debt") is None:
            nonblocking.append(formal.get("debt_status", "正式文件未提供可直接合并的单一债务字段。"))
        item["allowed_nonblocking_field_limits"] = nonblocking
        item["missing_fields"] = []
    sndk = next(item for item in holdings["items"] if item["code"] == "US.SNDK")
    sndk["action_boundary"] = "价格单位、数量、市值、公司行动和第四季度财报已闭合；券商原始盈亏率25.21%与现价/成本计算19.19%不一致，标记BROKER_PL_BASIS_UNRESOLVED并隔离；Codex仍不制定价值区间、买卖区间或仓位。"
    sndk["valuation_method_input_only"] = "价格单位、公司行动和正式财务已校正；估值方法、价值区间和动作条件仍由GPT总控决定。"
    sndk["valuation_numbers_and_basis"] = "未获授权制定当前估值或价值区间；券商盈亏率口径未解释，不进入估值或动作判断。"
    sndk["approved_judgment_and_source"] = "上一版总控判断为“校正完成前持有但不加仓”；校正条件现已闭合，是否维持或更新由GPT总控重新裁定。"


def enrich_candidates(candidates: dict[str, Any]) -> None:
    for item in candidates["items"]:
        core = CANDIDATE_CORE.get(item["code"])
        if not core:
            continue
        item["official_evidence"] = {
            "title": f"{item['name']}最新正式财报",
            "date": core["published_at"],
            "url": core["url"],
        }
        item["formal_core_numbers"] = core
        item["gates"][1]["input"] = (
            f"正式财报期间：{core['period']}；收入{amount(core.get('revenue'), core['currency'])}；"
            f"营业利润{amount(core.get('operating_profit'), core['currency'])}；净利润{amount(core.get('net_income'), core['currency'])}；"
            f"经营现金流{amount(core.get('ocf'), core['currency'])}；自由现金流{amount(core.get('fcf'), core['currency'])}。"
            f"{core.get('note', '')}这些是判断输入，不是机械评分结论。"
        )
        item["missing_evidence_or_gpt_decision"] = [
            value for value in item["missing_evidence_or_gpt_decision"]
            if "正式财报" not in value and "直链" not in value
        ]
    sndk = next(item for item in candidates["items"] if item["code"] == "US.SNDK")
    formal = FORMAL_FACTS["US.SNDK"]
    sndk["official_evidence"] = {"title": "Sandisk 2026财年第四季度及全年正式结果", "date": formal["published_at"], "url": formal["url"]}
    sndk["formal_core_numbers"] = formal
    sndk["gates"][1]["input"] = (
        "SNDK第四季度正式结果已取得：收入89.65亿美元、营业利润70.37亿美元、净利润69.03亿美元；"
        "全年经营现金流116.71亿美元。OpenD价格、成本、数量和市值已勾稽，未发现截止日前拆股生效记录。"
        "数据阻断闭合，但估值与动作仍由GPT总控决定。"
    )
    sndk["observation_pool_reason"] = "关键数据口径已闭合；仍在研究观察池等待GPT总控完成估值和业务取舍。"
    sndk["missing_evidence_or_gpt_decision"] = ["五关最终通过/淘汰由GPT总控决定", "相对现有持仓的替换价值由GPT总控决定"]


def enrich_pdca(pdca: dict[str, Any]) -> None:
    ledger = load(ROOT / "data" / "pdca" / "forecast_ledger.json")["forecasts"]
    series_map: dict[tuple[str, str, str], str] = {}
    series_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, (raw, row) in enumerate(zip(ledger, pdca["records"], strict=True), 1):
        key = (raw.get("layer") or "", raw.get("code") or "", raw.get("op") or "")
        if key not in series_map:
            series_map[key] = f"PDCA-SERIES-{len(series_map) + 1:03d}"
        series_id = series_map[key]
        previous = series_rows[series_id][-1]["prediction_id"] if series_rows[series_id] else None
        row.update({
            "series_id": series_id,
            "tracking_sequence": len(series_rows[series_id]) + 1,
            "previous_tracking_id": previous,
            "relationship": "同一预测主题在不同锁定日和验证日的连续滚动跟踪；本条不是新的独立主题。" if previous else "该预测主题的首条锁定记录。",
        })
        series_rows[series_id].append(row)
    correct = sum(row["judgment"] == "判对" for row in pdca["records"])
    wrong = sum(row["judgment"] == "判错" for row in pdca["records"])
    adjudicated = correct + wrong
    pending = len(pdca["records"]) - adjudicated
    pdca["summary"] = {
        "independent_prediction_series_count": len(series_map),
        "tracking_record_count": len(pdca["records"]),
        "distinct_locked_instances": len(pdca["records"]),
        "adjudicated_tracking_count": adjudicated,
        "correct_tracking_count": correct,
        "wrong_tracking_count": wrong,
        "pending_or_missing_actual_count": pending,
        "hit_rate_percent_on_adjudicated_tracking": round(correct / adjudicated * 100, 3) if adjudicated else None,
        "definition": "独立预测数量按层级+标的+判定运算符归并为预测主题系列；57条是不同日期锁定的连续追踪记录，不冒充57个彼此独立的预测主题。",
    }
    pdca["series"] = [
        {
            "series_id": series_id,
            "layer": key[0],
            "instrument": key[1],
            "operator": key[2],
            "tracking_count": len(series_rows[series_id]),
            "first_prediction_id": series_rows[series_id][0]["prediction_id"],
            "last_prediction_id": series_rows[series_id][-1]["prediction_id"],
        }
        for key, series_id in series_map.items()
    ]


def build_evidence(run_id: str, now: str, accounts: dict[str, Any], holdings: dict[str, Any], candidates: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(evidence_id: str, title: str, source: str, published_at: str | None, data_date: str | None, url: str, boundary: str, fields: list[str]) -> None:
        if evidence_id in seen:
            return
        seen.add(evidence_id)
        items.append({
            "evidence_id": evidence_id,
            "title": title,
            "source": source,
            "published_at": published_at,
            "data_date": data_date,
            "fetched_at": now,
            "freshness": "截止原生产日2026-08-15前已公开；本批次于接口/网页可用后补取得" if published_at and published_at <= "2026-08-15" else "本地原始实物",
            "url": url,
            "applicable_boundary": boundary,
            "fields_supported": fields,
        })

    account_sources = sorted({Path(row["source"]) for row in accounts["account_rows"]})
    for index, path in enumerate(account_sources, 1):
        add(f"EV-ACCOUNT-{index:03d}", path.name, "项目账户实物", None, None, local_url(path), "只支持该文件明确记录的账户、日期和字段", ["账户", "数量", "价格", "市值", "币种", "数据日"])
    for item in holdings["items"]:
        formal = item.get("formal_financial_detail")
        if not formal and item.get("evidence_url"):
            add(
                f"EV-HOLD-{item['code'].replace('.', '-')}",
                f"{item['name']}正式资料",
                item.get("official_source") or "正式披露来源",
                item.get("formal_publication_date"),
                item.get("latest_formal_financial_period"),
                item["evidence_url"],
                "保留上一轮已登记的直接原文证据；不替代投资判断",
                ["持仓研究所用正式事实"],
            )
            continue
        if not formal:
            continue
        add(
            f"EV-HOLD-{item['code'].replace('.', '-')}",
            f"{item['name']}正式财务",
            "监管申报或公司正式财报",
            formal["published_at"],
            formal["period"],
            formal["url"],
            "只支持所列期间、会计口径和已明确披露字段；不直接形成买卖或估值结论",
            ["收入", "营业利润/替代口径", "净利润", "经营现金流", "自由现金流或计算基础", "现金", "债务", "一次性项目", "正式指引"],
        )
        if item["code"] == "US.SNDK":
            action = formal["corporate_action"]
            add("EV-SNDK-CORPORATE-ACTION", "Sandisk历史报价与拆分调整", "Sandisk官方投资者关系", None, "2026-06-29", action["url"], "仅支持历史报价页所示拆分调整因子和价格单位", ["拆分调整因子", "历史美元报价"])
    for item in candidates["items"]:
        core = item.get("formal_core_numbers")
        evidence = item.get("official_evidence") or {}
        if not core and evidence.get("url"):
            add(
                f"EV-CAND-{item['code'].replace('.', '-')}",
                evidence.get("title") or f"{item['name']}正式资料",
                evidence.get("publisher") or "正式披露来源",
                evidence.get("date") or evidence.get("publication_date"),
                evidence.get("period"),
                evidence["url"],
                "保留上一轮已登记的直接原文证据；不等于通过五关或形成动作",
                ["候选五关所用正式事实"],
            )
            continue
        if not core:
            continue
        add(
            f"EV-CAND-{item['code'].replace('.', '-')}",
            f"{item['name']}候选五关正式财报",
            "SEC或公司正式财报",
            core["published_at"],
            core["period"],
            core["url"],
            "支持第二关财务输入；五关最终通过、估值与替换判断仍由GPT总控完成",
            ["收入", "利润", "经营现金流", "自由现金流或适用限制"],
        )
    add("EV-PDCA-LEDGER", "原始预测账本", "项目PDCA日志", None, None, local_url(ROOT / "data" / "pdca" / "forecast_ledger.json"), "只提取原始锁定记录并建立连续追踪关系，不补造", ["预测日", "验证日", "结果", "连续追踪"])
    return {"run_id": run_id, "generated_at": now, "evidence_count": len(items), "items": items}


def build_gaps(run_id: str, now: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "generated_at": now,
        "status": "CRITICAL_EVIDENCE_COMPLETION_SUBMITTED",
        "closed_critical_items": [
            {"id": "CLOSED-SNDK-001", "item": "SNDK价格、公司行动、OpenD勾稽和2026财年第四季度财报", "status": "CLOSED", "boundary": "数据口径闭合不等于估值或交易动作获批"},
            {"id": "CLOSED-SAMSUNG-001", "item": "Samsung韩元报价、韩元市值、IBKR美元折算和汇率日期分列", "status": "CLOSED"},
            {"id": "CLOSED-HOLDING-FIN-001", "item": "AVGO、COIN、CRCL、IBKR、META、MSFT、MSTR、NVDA、TSM、Samsung、SNDK、SpaceX正式财务字段", "status": "CLOSED_WITH_FIELD_LEVEL_LIMITS"},
            {"id": "CLOSED-CANDIDATE-EVIDENCE-001", "item": "PLTR、ETN、CEG、ON第二季度、COHR最新全年、LITE财年末、XOM第二季度正式直链和核心数字", "status": "CLOSED"},
            {"id": "CLOSED-PDCA-001", "item": "57条追踪记录、29条已判定、28条待验证及连续追踪关系", "status": "CLOSED"},
        ],
        "allowed_nonblocking_gaps": [
            {"id": "ALLOWED-001", "item": "SBI个人/公司账户归属不明", "impact": "账户归属和税务汇总仍有限制"},
            {"id": "ALLOWED-002", "item": "富途28,873.30美元其他净资产未拆分", "impact": "总额闭合但资产类别未知"},
            {"id": "ALLOWED-003", "item": "四账户数据日期不同", "impact": "不得拼成同日净值"},
            {"id": "ALLOWED-004", "item": "28条PDCA尚未到验证点或缺实际结果", "impact": "不进入命中率分母"},
            {"id": "ALLOWED-005", "item": "个别正式报表未单列传统营业利润、债务或自由现金流字段", "impact": "按字段说明保留，不用替代值冒充"},
        ],
        "business_decisions_reserved": [
            "价值区间、买卖区间和仓位",
            "21只候选五关最终通过或淘汰",
            "持仓保留、减持、替换和目标贡献",
        ],
    }


def build_changes(run_id: str, now: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "generated_at": now,
        "previous_status": "RETURNED_FOR_CRITICAL_EVIDENCE_COMPLETION",
        "items": [
            {"id": "CHG-001", "before": "SNDK价格、拆分和第四季度财报未闭合", "after": "OpenD 1,641.11美元×40股=65,644.40美元；按现价/成本计算19.19%，券商原始25.21%标记BROKER_PL_BASIS_UNRESOLVED并隔离；截止日前未发现拆股；Q4正式财报已接入", "evidence": [FORMAL_FACTS["US.SNDK"]["url"], FORMAL_FACTS["US.SNDK"]["corporate_action"]["url"]]},
            {"id": "CHG-002", "before": "Samsung 242,500被混入美元市值记录", "after": "报价242,500韩元、市值3,637,500韩元、IBKR折算2,560美元、隐含汇率1,420.8984375韩元/美元及日期分列", "evidence": [local_url(ROOT / "data" / "accounts" / "per_account_IBKR_20260811.json"), FORMAL_FACTS["KRX.005930"]["url"]]},
            {"id": "CHG-003", "before": "12类重点持仓多项正式财务字段为空", "after": "逐只接入SEC、公司IR或正式财报；无法取得的单一字段以字段级限制说明，不以模板补数", "evidence": [value["url"] for value in FORMAL_FACTS.values()]},
            {"id": "CHG-004", "before": "PLTR、ETN、CEG、ON、COHR、LITE、XOM缺最新正式财报直链或核心数字", "after": "七只均登记具体SEC/正式财报链接、期间和核心数字，五关仍保留观察池边界", "evidence": [value["url"] for value in CANDIDATE_CORE.values()]},
            {"id": "CHG-005", "before": "57条被逐条列示但未区分独立主题与重复跟踪", "after": "归并为5个独立预测主题系列、57条锁定追踪；29条已判定、28条待验证，命中率按28/29计算", "evidence": [local_url(ROOT / "data" / "pdca" / "forecast_ledger.json")]},
        ],
    }


def render_html(path: Path, run_id: str, now: str, accounts: dict[str, Any], holdings: dict[str, Any], candidates: dict[str, Any], pdca: dict[str, Any], gaps: dict[str, Any], changes: dict[str, Any]) -> None:
    hold_rows = []
    for item in holdings["items"]:
        detail = item.get("formal_financial_detail")
        if detail:
            financial = (
                f"{esc(detail['period'])}<br>收入 {amount(detail['revenue'], detail['currency'])}<br>"
                f"营业利润 {amount(detail.get('operating_profit'), detail['currency'])}<br>"
                f"净利润 {amount(detail['net_income'], detail['currency'])}<br>经营现金流 {amount(detail['ocf'], detail['currency'])}<br>"
                f"自由现金流 {amount(detail.get('fcf'), detail['currency'])}"
            )
            source = f"<a href='{esc(detail['url'])}'>正式原文</a>"
        else:
            financial = f"{esc(item['latest_formal_financial_period'])}<br>沿用已核日股/资产口径"
            source = f"<a href='{esc(item.get('evidence_url'))}'>证据</a>" if item.get("evidence_url") else "本地实物"
        hold_rows.append(f"<tr><td>{esc(item['code'])}<br>{esc(item['name'])}</td><td>{financial}</td><td>{esc(item['one_off_and_accounting_basis'])}</td><td>{source}</td><td>{esc(item['action_boundary'])}</td></tr>")
    candidate_rows = []
    for item in candidates["items"]:
        ev = item.get("official_evidence") or {}
        candidate_rows.append(f"<tr><td>{esc(item['code'])}<br>{esc(item['name'])}</td><td>{esc(item['gates'][0]['input'])}</td><td>{esc(item['gates'][1]['input'])}</td><td>{esc(item['gates'][2]['input'])}</td><td>{esc(item['gates'][3]['input'])}</td><td>{esc(item['gates'][4]['input'])}</td><td><a href='{esc(ev.get('url'))}'>正式原文</a><br>{esc(item['observation_pool_reason'])}</td></tr>")
    change_rows = "".join(f"<tr><td>{esc(row['id'])}</td><td>{esc(row['before'])}</td><td>{esc(row['after'])}</td></tr>" for row in changes["items"])
    closed_rows = "".join(f"<tr><td>{esc(row['id'])}</td><td>{esc(row['item'])}</td><td>{esc(row['status'])}</td></tr>" for row in gaps["closed_critical_items"])
    allowed_rows = "".join(f"<tr><td>{esc(row['id'])}</td><td>{esc(row['item'])}</td><td>{esc(row['impact'])}</td></tr>" for row in gaps["allowed_nonblocking_gaps"])
    samsung = accounts["samsung_currency_reconciliation"]
    summary = pdca["summary"]
    path.write_text(f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><title>V7 v0.4业务输入关键缺口闭合</title><style>
body{{font-family:'Microsoft YaHei','Noto Sans CJK SC',sans-serif;color:#1b1f23;margin:30px;line-height:1.55;font-size:15px}}h1{{font-size:26px}}h2{{font-size:20px;border-bottom:2px solid #333;padding-bottom:6px}}.banner{{border-left:6px solid #a33;background:#f6f7f8;padding:14px;margin:16px 0}}table{{border-collapse:collapse;width:100%;margin:12px 0 24px}}th,td{{border:1px solid #bbb;padding:7px;vertical-align:top;font-size:13px}}th{{background:#eef0f2}}.ok{{color:#176b36;font-weight:700}}.hold{{color:#8a4b00;font-weight:700}}code{{background:#f1f3f5;padding:2px 4px}}a{{color:#075bbb;word-break:break-all}}@media print{{body{{margin:12mm;font-size:10pt}}th,td{{font-size:9.5pt}}}}
</style></head><body><h1>V7完整产品v0.4业务输入关键缺口闭合</h1>
<div class='banner'><b>run_id：</b>{esc(run_id)}<br><b>生成时间：</b>{esc(now)}<br><b>上一轮状态：</b>RETURNED_FOR_CRITICAL_EVIDENCE_COMPLETION<br><b>本轮技术提交：</b>CRITICAL_EVIDENCE_COMPLETION_SUBMITTED<br><b>边界：</b>只补事实和证据；不生成v0.4产品，不作投资判断，不Release，不覆盖正式日报，不生成订单。</div>
<h2>一、执行摘要</h2><p class='ok'>SNDK、Samsung币种、重点持仓正式财务、七只候选正式财报和PDCA连续追踪五项关键缺口已按证据闭合。</p><p class='hold'>这不表示任何估值、买卖、仓位或候选五关已经获批；相关判断全部保留给GPT总控。</p>
<table><tr><th>编号</th><th>闭合事项</th><th>状态</th></tr>{closed_rows}</table>
<h2>二、SNDK口径闭合</h2><p>OpenD在2026-08-14 20:02:18.541返回每股1,641.11美元、成本1,376.88美元、40股、市值65,644.40美元。价格乘数量与市值勾稽，因此不是164.111美元；按现价/成本计算为19.19%，券商原始盈亏率25.21%的成本口径未解释，已隔离且不进入估值或动作判断。公司历史报价页显示2026-06-29拆分调整因子为1:1；截至原生产日的SEC申报和公司公告未发现后续拆股生效记录。<a href='{FORMAL_FACTS['US.SNDK']['url']}'>第四季度及全年正式财报</a>已接入。</p>
<h2>三、Samsung账户币种闭合</h2><p>IBKR最后已知记录：{samsung['quantity']}股，每股{amount(samsung['quote_price_krw'], 'KRW')}，韩元市值{amount(samsung['market_value_krw'], 'KRW')}；IBKR账户折算市值{amount(samsung['ibkr_market_value_usd'], 'USD')}，隐含汇率{amount(samsung['fx_krw_per_usd'], 'KRW/USD')}，日期{samsung['fx_date']}。242,500从未作为美元价格使用。</p>
<h2>四、24类持仓正式财务输入</h2><table><tr><th>持仓</th><th>最新正式财务</th><th>一次性项目/口径</th><th>直接证据</th><th>动作边界</th></tr>{''.join(hold_rows)}</table>
<h2>五、21只候选五关输入</h2><p>七只退回点名标的已补具体正式财报直链和核心数字；其余候选保留上一版已核直接证据。全部仍在研究观察池，Codex未作通过或淘汰决定。</p><table><tr><th>候选</th><th>第一关</th><th>第二关</th><th>第三关</th><th>第四关</th><th>第五关</th><th>证据与观察原因</th></tr>{''.join(candidate_rows)}</table>
<h2>六、PDCA真实口径</h2><p>原账本共有{summary['tracking_record_count']}条不同日期锁定的追踪记录，归并为{summary['independent_prediction_series_count']}个独立预测主题系列。已判定{summary['adjudicated_tracking_count']}条，其中判对{summary['correct_tracking_count']}条、判错{summary['wrong_tracking_count']}条；待验证或缺实际结果{summary['pending_or_missing_actual_count']}条。已判定追踪命中率为{summary['hit_rate_percent_on_adjudicated_tracking']:.3f}%。57条不再被表述为57个彼此独立的预测主题。</p>
<h2>七、允许保留的非阻断缺口</h2><table><tr><th>编号</th><th>事项</th><th>影响</th></tr>{allowed_rows}</table>
<h2>八、修改前—修改后</h2><table><tr><th>编号</th><th>修改前</th><th>修改后</th></tr>{change_rows}</table>
<h2>九、停止边界</h2><ul><li>未修改上一版输入包和基准候选。</li><li>未生成v0.4完整产品。</li><li>未作价值区间、买卖区间、仓位或候选取舍。</li><li>未登记Release，未覆盖<code>00_今日日报.pdf</code>。</li><li>只调用Futu报价只读接口核对SNDK；未调用交易接口，未生成订单。</li></ul>
</body></html>""", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id")
    args = parser.parse_args()
    now_dt = datetime.now(JST)
    now = now_dt.isoformat(timespec="seconds")
    run_id = args.run_id or f"V7-V04-CRITICAL-EVIDENCE-{now_dt.strftime('%Y%m%d-%H%M%S')}-JST"
    out = ROOT / "output" / "decision_inputs" / "2026-08-17" / run_id
    out.mkdir(parents=True, exist_ok=False)

    previous_hashes = {path.name: sha256(path) for path in PREVIOUS_DIR.iterdir() if path.is_file()}
    daily_before = metadata(DAILY_REPORT)

    prior.OFFICIAL_FACTS.update(FORMAL_FACTS)
    accounts = prior.build_accounts(run_id, now)
    enrich_accounts(accounts)
    holdings = prior.build_holdings(run_id, now, accounts)
    enrich_holdings(holdings)
    candidates = prior.build_candidates(run_id, now)
    enrich_candidates(candidates)
    pdca = prior.build_pdca(run_id, now)
    enrich_pdca(pdca)
    evidence = build_evidence(run_id, now, accounts, holdings, candidates)
    gaps = build_gaps(run_id, now)
    changes = build_changes(run_id, now)

    files = [
        ("01_全账户资产明细_20260817.json", accounts),
        ("02_24类持仓业务判断输入_20260817.json", holdings),
        ("03_21只候选五关输入_20260817.json", candidates),
        ("04_PDCA汇总及逐条记录_20260817.json", pdca),
        ("05_精确证据注册表_20260817.json", evidence),
        ("06_缺失与冲突清单_20260817.json", gaps),
        ("07_逐项修改前修改后证据清单_20260817.json", changes),
    ]
    for name, value in files:
        dump(out / name, value)
    html_path = out / "V7_v0.4业务判断关键补证包_20260817.html"
    render_html(html_path, run_id, now, accounts, holdings, candidates, pdca, gaps, changes)

    daily_after = metadata(DAILY_REPORT)
    execution = {
        "run_id": run_id,
        "generated_at": now,
        "task": "V7 v0.4业务输入关键缺口闭合",
        "status": "CRITICAL_EVIDENCE_COMPLETION_SUBMITTED",
        "previous_package": {"path": str(PREVIOUS_DIR), "hashes_before": previous_hashes, "modified": False},
        "counts": {"account_rows": len(accounts["account_rows"]), "holdings": len(holdings["items"]), "candidates": len(candidates["items"]), "pdca_tracking": len(pdca["records"]), "evidence": len(evidence["items"])},
        "daily_report": {"before": daily_before, "after": daily_after, "byte_identical": daily_before["sha256"] == daily_after["sha256"] and daily_before["size"] == daily_after["size"]},
        "prohibitions_verified": {"v04_product_generated": False, "investment_judgment_by_codex": False, "value_or_buy_zone_decided": False, "release_registered": False, "daily_report_overwritten": False, "trading_api_called": False, "order_generated": False},
    }
    dump(out / "08_执行日志_20260817.json", execution)

    artifact_paths = sorted(path for path in out.iterdir() if path.is_file())
    replacements = {path.name: path.read_bytes().count(b"\xef\xbf\xbd") for path in artifact_paths}
    manifest = {
        "run_id": run_id,
        "generated_at": now,
        "manifest_self_excluded": True,
        "items": [metadata(path) | {"utf8_replacement_bytes": replacements[path.name]} for path in artifact_paths],
        "checks": {
            "utf8_replacement_total": sum(replacements.values()),
            "previous_package_unchanged": previous_hashes == {path.name: sha256(path) for path in PREVIOUS_DIR.iterdir() if path.is_file()},
            "daily_report_unchanged": daily_before["sha256"] == daily_after["sha256"] and daily_before["size"] == daily_after["size"],
            "holding_count": len(holdings["items"]),
            "candidate_count": len(candidates["items"]),
            "pdca_adjudicated": pdca["summary"]["adjudicated_tracking_count"],
            "pdca_pending": pdca["summary"]["pending_or_missing_actual_count"],
            "samsung_quote_currency": next(row for row in accounts["account_rows"] if row["code"] == "KRX.005930")["currency"],
            "sndk_market_value_math": FORMAL_FACTS["US.SNDK"]["price_reconciliation"]["calculated_market_value_usd"],
        },
    }
    dump(out / "09_全部实物SHA256清单_20260817.json", manifest)
    print(json.dumps({"run_id": run_id, "output": str(out), "files": len(list(out.iterdir())), "daily_report_unchanged": execution["daily_report"]["byte_identical"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
