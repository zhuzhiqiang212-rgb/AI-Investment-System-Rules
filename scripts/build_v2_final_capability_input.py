from __future__ import annotations

import hashlib
import html
import json
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
PYTHON = "bundled workspace Python"
SOURCE_PACKAGE = ROOT / "00_任务中心" / "V7_v2.0_GPT总控唯一业务判断输入包_Current.json"
VALUATION_DECISION = (
    ROOT
    / "output"
    / "decision_inputs"
    / "2026-08-19"
    / "V7-V151-VALUATION-INPUT-CLOSE-20260819-154226-JST"
    / "V7_v1.5_GPT总控最终估值裁定_20260819.json"
)
PRIOR_GATES = (
    ROOT
    / "output"
    / "candidates"
    / "2026-08-20"
    / "V7-COMPLETEHTML-CLOSE-20260821-013257-JST"
    / "04_18只研究观察正式五关_20260820.json"
)
TASK_FILE = ROOT / "00_任务中心" / "阶段C完整HTML全文内容闸复核结论及最终能力闭合令_20260821.html"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def pct(value: float) -> float:
    return round(value * 100.0, 6)


def money(value: float) -> float:
    return round(value, 2)


GUIDANCE = {
    "BTC": {
        "status": "ASSET_NOT_APPLICABLE",
        "plain_status": "非企业资产，不适用公司业绩指引",
        "period": "不适用",
        "facts": ["不套用企业收入、利润或每股收益指引。"],
        "source_title": "Bitcoin: A Peer-to-Peer Electronic Cash System",
        "publisher": "Satoshi Nakamoto",
        "published_at": "2008-10-31",
        "url": "https://bitcoin.org/bitcoin.pdf",
        "locator": "协议定义；不能证明当前价格、流动性或收益前景",
    },
    "ETH": {
        "status": "ASSET_NOT_APPLICABLE",
        "plain_status": "非企业资产，不适用公司业绩指引",
        "period": "不适用",
        "facts": ["不套用企业收入、利润或每股收益指引。"],
        "source_title": "Ethereum Whitepaper",
        "publisher": "Ethereum.org",
        "published_at": "持续维护",
        "url": "https://ethereum.org/en/whitepaper/",
        "locator": "协议与运行规则；不能证明当前价格、流动性或收益前景",
    },
    "JP.4063": {
        "status": "NUMERIC_GUIDANCE_EXTRACTED",
        "plain_status": "公司已给出可核对的全年指引",
        "period": "截至2027年3月的财年",
        "facts": ["销售额2.70万亿日元", "营业利润7,000亿日元", "归母净利润5,250亿日元", "每股收益286日元", "全年股息116日元"],
        "source_title": "Consolidated Financial Results for the First Quarter Ended June 30, 2026",
        "publisher": "Shin-Etsu Chemical",
        "published_at": "2026-07-24",
        "url": "https://www.shinetsu.co.jp/wp-content/uploads/2026/07/20260724E1-1.pdf",
        "locator": "FY2027 consolidated forecast table",
    },
    "JP.4568": {
        "status": "NUMERIC_GUIDANCE_EXTRACTED",
        "plain_status": "公司已给出修订后的全年指引",
        "period": "截至2027年3月的财年",
        "facts": ["核心营业利润3,600亿日元", "营业利润3,200亿日元", "归母净利润2,510亿日元", "每股收益137.94日元"],
        "source_title": "FY2026 Q1 Financial Results Presentation",
        "publisher": "Daiichi Sankyo",
        "published_at": "2026-07-31",
        "url": "https://www.daiichisankyo.com/files/investors/library/quarterly_result/2026/FY2026Q1_Financial_Results_Presentation_E.pdf",
        "locator": "Revised FY2026 forecast table",
    },
    "JP.6758": {
        "status": "NUMERIC_GUIDANCE_EXTRACTED",
        "plain_status": "公司已更新全年预测，需按持续经营口径阅读",
        "period": "截至2027年3月的财年",
        "facts": ["税前利润1.71万亿日元", "归母净利润1.21万亿日元", "经营现金流约1.50万亿日元", "音乐分部销售预测2.19万亿日元、营业利润5,400亿日元"],
        "source_title": "FY2026 Q1 Earnings Presentation",
        "publisher": "Sony Group",
        "published_at": "2026-07-31",
        "url": "https://www.sony.com/en/SonyInfo/IR/library/presen/er/pdf/26q1_sonypre.pdf",
        "locator": "FY2026 forecast summary and segment forecast pages",
    },
    "JP.6857": {
        "status": "NUMERIC_GUIDANCE_EXTRACTED",
        "plain_status": "公司已上调全年指引",
        "period": "截至2027年3月的财年",
        "facts": ["销售额1.714万亿日元", "营业利润8,460亿日元", "净利润6,600亿日元", "每股收益911.64日元"],
        "source_title": "FY2026 Earnings Forecast",
        "publisher": "Advantest",
        "published_at": "2026-07-29",
        "url": "https://www.advantest.com/en/investors/financial-highlights/forecast/",
        "locator": "FY2026 forecast table dated July 29, 2026",
    },
    "JP.6954": {
        "status": "NUMERIC_GUIDANCE_EXTRACTED",
        "plain_status": "公司已更新全年指引",
        "period": "截至2027年3月的财年",
        "facts": ["销售额9,481亿日元", "营业利润2,180亿日元", "归母净利润1,980亿日元", "美元兑日元假设150"],
        "source_title": "Financial Results for the Three Months Ended June 30, 2026",
        "publisher": "FANUC",
        "published_at": "2026-07-31",
        "url": "https://www.fanuc.co.jp/en/ir/announce/pdf/2026/reference202606_e.pdf",
        "locator": "Consolidated Financial Forecast, page 12",
    },
    "JP.7203": {
        "status": "NUMERIC_GUIDANCE_EXTRACTED",
        "plain_status": "公司已给出全年合并预测",
        "period": "截至2027年3月的财年",
        "facts": ["销售收入54.0万亿日元", "营业利润3.40万亿日元", "归母净利润3.25万亿日元", "每股收益272.17日元"],
        "source_title": "FY2027 First Quarter Financial Summary",
        "publisher": "Toyota Motor",
        "published_at": "2026-08-04",
        "url": "https://global.toyota/pages/global_toyota/ir/financial-results/2027_1q_summary_en.pdf",
        "locator": "Page 1, Forecast of Consolidated Results for FY2027",
    },
    "JP.7974": {
        "status": "NUMERIC_GUIDANCE_EXTRACTED",
        "plain_status": "公司已给出全年合并预测",
        "period": "截至2027年3月的财年",
        "facts": ["销售额2.05万亿日元", "营业利润3,700亿日元", "归母净利润3,100亿日元", "每股收益268.90日元"],
        "source_title": "Consolidated Financial Results for the Year Ended March 31, 2026",
        "publisher": "Nintendo",
        "published_at": "2026-05-08",
        "url": "https://www.nintendo.co.jp/ir/pdf/2026/260508e.pdf",
        "locator": "Forecast for year ending March 31, 2027",
    },
    "JP.8001": {
        "status": "NUMERIC_GUIDANCE_EXTRACTED",
        "plain_status": "公司已给出管理计划",
        "period": "截至2027年3月的财年",
        "facts": ["归母净利润9,500亿日元", "税前利润1.24万亿日元", "最低全年股息44日元", "计划回购至少3,000亿日元"],
        "source_title": "FY2025 Business Results and FY2026 Management Plan",
        "publisher": "ITOCHU",
        "published_at": "2026-05-01",
        "url": "https://www.itochu.co.jp/en/ir/financial_statements/2026/__icsFiles/afieldfile/2026/05/01/26_ended_01_e.pdf",
        "locator": "Outlook for fiscal year ending March 31, 2027",
    },
    "JP.8766": {
        "status": "NUMERIC_GUIDANCE_EXTRACTED",
        "plain_status": "公司已给出调整后利润和资本回报指引",
        "period": "截至2027年3月的财年",
        "facts": ["调整后净利润9,500亿日元", "调整后ROE 13.0%", "每股股息245日元"],
        "source_title": "FY2026 Group Business Strategy and Projections",
        "publisher": "Tokio Marine Holdings",
        "published_at": "2026-05-26",
        "url": "https://www.tokiomarinehd.com/en/ir/event/presentation/2026/f5hrqd0000004pev-att/IR_conference_FY2026_e.pdf",
        "locator": "FY2026 projections and shareholder returns",
    },
    "JP.9984": {
        "status": "ALTERNATIVE_GUIDANCE_EXTRACTED",
        "plain_status": "投资控股公司，以NAV和LTV管理，不使用传统收入指引",
        "period": "2026年6月30日",
        "facts": ["NAV 72.30万亿日元", "持股价值83.11万亿日元", "净债务10.81万亿日元", "LTV 13.0%"],
        "source_title": "Net Asset Value per Share",
        "publisher": "SoftBank Group",
        "published_at": "2026-07",
        "url": "https://group.softbank/en/ir/stock/sotp",
        "locator": "NAV and LTV calculation as of June 30, 2026",
    },
    "KRX.005930": {
        "status": "QUALITATIVE_OUTLOOK_EXTRACTED",
        "plain_status": "公司未给出可直接用于全年估值的统一数值区间",
        "period": "2026年第二季度结果",
        "facts": ["只保留HBM、存储价格、出货和半导体利润率的验证条件；不把单季高点外推为全年。"],
        "source_title": "Samsung Electronics Second Quarter 2026 Results",
        "publisher": "Samsung Electronics",
        "published_at": "2026-07",
        "url": "https://news.samsung.com/global/samsung-electronics-announces-second-quarter-2026-results",
        "locator": "Second-quarter consolidated results and second-half business outlook",
    },
    "US.AVGO": {
        "status": "NUMERIC_GUIDANCE_EXTRACTED",
        "plain_status": "公司已给出下一季度数值指引",
        "period": "2026财年第三季度",
        "facts": ["收入约294亿美元", "非GAAP营业利润率约67%", "AI半导体收入预计约160亿美元"],
        "source_title": "Broadcom Announces Second Quarter Fiscal Year 2026 Results",
        "publisher": "Broadcom",
        "published_at": "2026-06-03",
        "url": "https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announces-second-quarter-fiscal-year-2026-financial",
        "locator": "Third quarter fiscal 2026 guidance",
    },
    "US.COIN": {
        "status": "PARTIAL_GUIDANCE_EXTRACTED",
        "plain_status": "公司只给出部分费用和经营口径，不提供稳定的全年收入区间",
        "period": "2026财年",
        "facts": ["调整后费用区间下调并收窄", "无形资产摊销预计1.40亿至1.50亿美元", "交易量和USDC收入仍高度受市场影响"],
        "source_title": "Coinbase Q2 2026 Earnings",
        "publisher": "Coinbase",
        "published_at": "2026-07-30",
        "url": "https://investor.coinbase.com/news/news-details/2026/Coinbase-Q2-Earnings-Everything-Exchange-Drives-3rd-Consecutive-Quarter-of-Record-Crypto-Trading-Volume-Market-Share-Revenue-Diversification-and-Resilience/default.aspx",
        "locator": "Q2 highlights and FY2026 adjusted expense commentary",
    },
    "US.CRCL": {
        "status": "OFFICIAL_SOURCE_REVIEWED_NO_NUMERIC_RANGE",
        "plain_status": "已取得正式结果，但未取得可独立支持价格区间的全年指引",
        "period": "2026年第二季度",
        "facts": ["后续判断只跟踪USDC流通量、储备收益、利率敏感性和监管地位。"],
        "source_title": "Circle Reports Second Quarter 2026 Results",
        "publisher": "Circle Internet Group",
        "published_at": "2026-08-05",
        "url": "https://investor.circle.com/events-and-presentations/event-details/2026/Circle-Reports-Second-Quarter-2026-Results-2026-1bDJXovkaS/default.aspx",
        "locator": "Official Q2 results; no numeric valuation range inferred",
    },
    "US.IBKR": {
        "status": "NO_TRADITIONAL_GUIDANCE",
        "plain_status": "券商不提供传统工业公司式全年指引",
        "period": "最新正式季度",
        "facts": ["改用客户账户、客户资产、净利息收入、资本充足和监管指标。"],
        "source_title": "Interactive Brokers Investor Relations Financial Releases",
        "publisher": "Interactive Brokers Group",
        "published_at": "2026",
        "url": "https://investors.interactivebrokers.com/",
        "locator": "Official financial releases and operating metrics",
    },
    "US.META": {
        "status": "NUMERIC_GUIDANCE_EXTRACTED",
        "plain_status": "公司已给出季度收入、全年费用和资本开支指引",
        "period": "2026年第三季度及全年",
        "facts": ["第三季度收入610亿至640亿美元", "全年费用1,650亿至1,690亿美元", "全年资本开支1,300亿至1,450亿美元", "全年营业利润预计高于2025年"],
        "source_title": "Meta Reports Second Quarter 2026 Results",
        "publisher": "Meta Platforms",
        "published_at": "2026-07-29",
        "url": "https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-Second-Quarter-2026-Results/default.aspx",
        "locator": "CFO Outlook Commentary",
    },
    "US.MSFT": {
        "status": "QUALITATIVE_AND_SEGMENT_GUIDANCE_EXTRACTED",
        "plain_status": "公司已披露云业务和资本开支方向，但本包不倒推全年每股收益",
        "period": "2026财年第四季度电话会及2026日历年",
        "facts": ["Azure需求继续超过供给", "预计2026日历年资本开支约1,900亿美元", "容量约束预计至少持续至2026年末"],
        "source_title": "Microsoft Fiscal Year 2026 Fourth Quarter Earnings Conference Call",
        "publisher": "Microsoft",
        "published_at": "2026-07-29",
        "url": "https://www.microsoft.com/en-us/investor/events/fy-2026/earnings-fy-2026-q4",
        "locator": "Management outlook commentary; no EPS reverse engineering",
    },
    "US.MSTR": {
        "status": "ALTERNATIVE_GUIDANCE_EXTRACTED",
        "plain_status": "比特币财库公司，使用每股比特币、债务和优先义务，而非传统盈利指引",
        "period": "截至2026年5月25日",
        "facts": ["持有843,738枚BTC", "可转债本金67亿美元", "优先股名义金额155亿美元", "美元储备8.71亿美元"],
        "source_title": "Strategy Completes $1.5 Billion Debt Repurchase",
        "publisher": "Strategy",
        "published_at": "2026-05-26",
        "url": "https://www.strategy.com/press/strategy-completes-1-5-billion-debt-repurchase-and-achieves-btc-yield-of-13-3-ytd-now-holds-843738-btc_05-26-2026",
        "locator": "Capital structure update",
    },
    "US.NVDA": {
        "status": "NUMERIC_GUIDANCE_EXTRACTED",
        "plain_status": "公司已给出下一季度数值指引",
        "period": "2027财年第二季度",
        "facts": ["收入910亿美元，上下浮动2%", "GAAP毛利率74.9%，非GAAP毛利率75.0%，上下浮动0.5个百分点", "未计入中国数据中心计算收入"],
        "source_title": "NVIDIA Announces Financial Results for First Quarter Fiscal 2027",
        "publisher": "NVIDIA",
        "published_at": "2026-05-20",
        "url": "https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-First-Quarter-Fiscal-2027/default.aspx",
        "locator": "Outlook for second quarter fiscal 2027",
    },
    "US.SNDK": {
        "status": "NUMERIC_GUIDANCE_EXTRACTED_ACTION_ISOLATED",
        "plain_status": "公司指引已取得，但券商价格、成本口径仍与动作隔离",
        "period": "2027财年第一季度",
        "facts": ["收入指引103亿至108亿美元", "非GAAP毛利率83.0%至85.0%", "非GAAP每股收益44至46美元", "券商收益率口径未解释，故不提供目标贡献概率"],
        "source_title": "Sandisk Reports Fiscal Fourth Quarter 2026 Financial Results",
        "publisher": "SanDisk",
        "published_at": "2026",
        "url": "https://investor.sandisk.com/news-releases/news-release-details/sandisk-reports-fiscal-fourth-quarter-2026-financial-results",
        "locator": "Business Outlook for Fiscal First Quarter of 2027",
    },
    "US.SPCX": {
        "status": "NO_TRADITIONAL_GUIDANCE",
        "plain_status": "现有披露不足以形成传统盈利指引和数值估值",
        "period": "最新公开披露",
        "facts": ["只跟踪发射频率、Starlink经营现金流、融资能力和公开市场流动性。"],
        "source_title": "Space Exploration Technologies SEC filing",
        "publisher": "SEC / SpaceX",
        "published_at": "2026",
        "url": "https://www.sec.gov/Archives/edgar/data/1181412/000162828026042466/spaceexplorationtechnologi.htm",
        "locator": "Public filing; no unsupported 90/125/165 dollar range",
    },
    "US.TSM": {
        "status": "NUMERIC_GUIDANCE_EXTRACTED",
        "plain_status": "公司已给出下一季度数值指引",
        "period": "2026年第三季度",
        "facts": ["收入446亿至458亿美元", "毛利率65%至67%", "营业利润率56%至58%"],
        "source_title": "TSMC Second Quarter 2026 Results and Third Quarter Outlook",
        "publisher": "TSMC",
        "published_at": "2026-07",
        "url": "https://investor.tsmc.com/english/quarterly-results/2026/q2",
        "locator": "Third quarter 2026 outlook",
    },
}


OPPORTUNITIES = {
    "US.MU": {
        "name": "Micron",
        "sector": "AI半导体、存储和HBM",
        "activation": "AI数据中心建设带动HBM与存储需求；属于已激活研究板块，但受AI同一驱动暴露约束。",
        "financial": ["第四季度收入指引500亿美元，上下浮动10亿美元", "毛利率约86%", "GAAP每股收益30.73美元，上下浮动1美元"],
        "source": "https://investors.micron.com/node/50671",
        "moat": "HBM认证、先进制程和规模供给能力构成进入壁垒；反向证据是存储扩产可能令价格周期反转。",
        "pricing": "必须使用中周期盈利和存储价格敏感性，不能用单季高点利润直接外推。",
        "cash_compare": "现金保留回撤选择权；MU只有在中周期盈利、估值和HBM兑现同时优于现金时才值得进入第五关。",
        "replacement": ["US.SNDK"],
        "replacement_logic": "与现有SNDK属于相近存储驱动，应比较周期盈利、现金流、口径可靠性和回撤，而不是叠加同一风险。",
        "next_trigger": "下一份正式财报同时核对HBM收入、毛利率、供给扩张和价格。",
    },
    "US.WDC": {
        "name": "Western Digital",
        "sector": "数据中心存储与硬盘",
        "activation": "云数据中心容量增长支持近线硬盘需求，但必须与NAND和SSD周期分开。",
        "financial": ["第四季度收入37.5亿美元", "非GAAP毛利率54.4%", "自由现金流12.8亿美元", "下一季度收入同比增长指引42%至49%"],
        "source": "https://investor.wdc.com/node/28586",
        "moat": "大容量硬盘技术、客户认证和规模制造构成壁垒；反向证据是云客户采购节奏和价格同时转弱。",
        "pricing": "采用分拆后独立财务、自由现金流和硬盘周期中枢，不沿用分拆前混合口径。",
        "cash_compare": "现金没有硬盘周期回撤；WDC需证明自由现金流持续和数据中心订单能补偿周期风险。",
        "replacement": ["US.SNDK"],
        "replacement_logic": "与SNDK比较不同存储子周期、财务口径可靠性及现金流，不允许只因同属存储而叠加。",
        "next_trigger": "下一季度正式结果核对订单、价格、自由现金流及分拆后口径。",
    },
    "US.VRT": {
        "name": "Vertiv",
        "sector": "数据中心电力、散热与基础设施",
        "activation": "AI机房电力密度和散热需求增长，属于已激活研究板块。",
        "financial": ["全年收入指引138亿至142亿美元", "全年调整后营业利润32.85亿至33.65亿美元", "全年调整后自由现金流24亿至26亿美元"],
        "source": "https://investors.vertiv.com/news/news-details/2026/Vertiv-Reports-Strong-Second-Quarter-2026-with-Diluted-EPS-Growth-of-53-Adjusted-Diluted-EPS-Growth-of-60-Raises-Full-Year-2026-Guidance-Across-All-Key-Metrics/default.aspx",
        "moat": "电力和热管理产品、服务网络与客户认证构成壁垒；反向证据是积压转化、产能和利润率不及指引。",
        "pricing": "以公司全年指引、自由现金流和订单兑现为基础；不得仅因AI主题给高倍数。",
        "cash_compare": "现金收益低但无项目交付风险；VRT需在增长兑现后仍有足够风险补偿。",
        "replacement": ["JP.9984", "US.SNDK"],
        "replacement_logic": "与现有广义AI代理和存储持仓比较，只有驱动更直接且风险收益更好才有替换意义。",
        "next_trigger": "下一季度核对积压转收入、产能、营业利润率和自由现金流。",
    },
    "US.CEG": {
        "name": "Constellation Energy",
        "sector": "AI数据中心电力与核电",
        "activation": "长期电力合同和数据中心负荷增长支持研究，同时具备分散AI芯片风险的潜力。",
        "financial": ["第二季度调整后每股营业收益2.55美元", "全年调整后每股收益指引上调至11.50至12.50美元", "披露920MW长期购电协议"],
        "source": "https://www-stage.constellationenergy.com/news/2026/08/constellation-reports-second-quarter-2026-results.html",
        "moat": "核电资产、许可和长期合同构成稀缺性；反向证据是资本开支、负自由现金流和监管风险。",
        "pricing": "采用正常化每股收益、合同期限、资本开支和负债，不把电力需求主题直接当估值。",
        "cash_compare": "现金没有监管和核电运营风险；CEG需证明合同收益覆盖资本开支和融资成本。",
        "replacement": ["JP.8766", "JP.9984"],
        "replacement_logic": "与防御型保险和广义AI代理比较分散价值、现金流稳定性及回撤。",
        "next_trigger": "长期合同落地、核电利用率、资本开支和自由现金流更新时复核。",
    },
    "JP.8306": {
        "name": "三菱日联金融集团",
        "sector": "日本银行与利率正常化",
        "activation": "板块条件激活；BOJ正式政策、净息差和信贷成本仍是必要条件。",
        "financial": ["第一季度归母利润8,094.27亿日元", "全年归母利润目标2.70万亿日元", "净营业利润目标2.90万亿日元", "ROE目标约12%", "全年股息96日元"],
        "source": "https://www.mufg.jp/dam/ir/fs/2026/pdf/summary2606_en.pdf",
        "moat": "存款基础、客户关系和资本实力构成壁垒；反向证据是加息推迟、信用成本上升和海外风险。",
        "pricing": "采用BVPS、ROE、资本充足和股东回报框架，不使用工业企业现金流倍数。",
        "cash_compare": "日元现金保留政策不确定期的选择权；银行需证明净息差扩张足以覆盖信用成本。",
        "replacement": ["JP.8766"],
        "replacement_logic": "与现有东京海上比较利率受益、资本回报、防御性和灾损/信用风险。",
        "next_trigger": "BOJ正式决定、下一季度净息差和信贷成本披露。",
    },
    "JP.8316": {
        "name": "三井住友金融集团",
        "sector": "日本银行与利率正常化",
        "activation": "板块条件激活；政策预期不能替代正式决定和财报兑现。",
        "financial": ["第一季度归母利润5,013.72亿日元", "全年归母利润目标1.70万亿日元", "净业务利润目标2.40万亿日元", "信用成本计划3,400亿日元"],
        "source": "https://www.smfg.co.jp/english/investor/financial/latest_statement/2027_3/2027_1q_e01.pdf",
        "moat": "客户基础、资本和综合金融能力构成壁垒；反向证据是信用成本、海外风险和政策推迟。",
        "pricing": "采用BVPS、ROE、资本充足和股东回报框架。",
        "cash_compare": "现金不承担信用周期风险；需证明净息差与股东回报能补偿风险。",
        "replacement": ["JP.8766"],
        "replacement_logic": "与东京海上比较资本回报和利率敏感度，不把金融板块当作无差别替代。",
        "next_trigger": "BOJ正式决定及下一季度净息差、信用成本和资本回报。",
    },
    "JP.8411": {
        "name": "瑞穗金融集团",
        "sector": "日本银行与利率正常化",
        "activation": "板块条件激活；政策和盈利兑现尚未同时闭合。",
        "financial": ["第一季度归母利润4,229亿日元", "全年归母利润目标1.40万亿日元", "净业务利润目标1.75万亿日元", "全年股息150日元"],
        "source": "https://library.mizuhogroup.com/asset/9ff487db-e8c6-49e3-84e7-c94408d171ec/fg-data26_1q_2.pdf",
        "moat": "企业客户和资本市场能力构成壁垒；反向证据是信用成本、政策推迟和资本效率不及同业。",
        "pricing": "采用BVPS、ROE、资本充足和股东回报框架。",
        "cash_compare": "日元现金保留政策选择权；只有盈利兑现和相对估值同时占优才值得替换。",
        "replacement": ["JP.8766"],
        "replacement_logic": "与东京海上及另外两家银行比较ROE、信用成本和股东回报。",
        "next_trigger": "BOJ正式决定及下一季度净息差、信用成本、资本回报。",
    },
    "US.MRVL": {
        "name": "Marvell Technology",
        "sector": "定制AI芯片与高速互连",
        "activation": "Google定制芯片协议和AI网络需求证明板块活跃，但也加剧AVGO/NVDA竞争。",
        "financial": ["第二季度收入指引27亿美元，上下浮动5%", "非GAAP毛利率58.25%至59.25%", "非GAAP每股收益0.93美元，上下浮动0.05美元"],
        "source": "https://investor.marvell.com/news-events/press-releases/detail/1023/marvell-technology-inc-reports-first-quarter-of-fiscal-year-2027-financial-results",
        "moat": "定制芯片和高速互连设计能力构成壁垒；反向证据是客户集中、认股权证稀释和竞争加剧。",
        "pricing": "采用公司季度指引、客户集中、摊薄和自由现金流；不能把122亿美元认股权证上限当现金收入。",
        "cash_compare": "现金无客户集中和稀释风险；MRVL必须证明订单兑现和风险补偿。",
        "replacement": ["US.AVGO", "US.NVDA"],
        "replacement_logic": "与现有AVGO和NVDA直接比较定制芯片增长、客户集中、估值和同一驱动暴露。",
        "next_trigger": "Google项目里程碑、下一季度收入/毛利率和摊薄披露。",
    },
}


def guidance_for(symbol: str) -> dict:
    if symbol not in GUIDANCE:
        raise KeyError(f"Missing guidance for {symbol}")
    return GUIDANCE[symbol]


def quote_map(package: dict) -> dict:
    return {row.get("asset_id") or row.get("code"): row for row in package["asset_quotes"]["records"]}


def valuation_map(decision: dict) -> dict:
    return {row["symbol"]: row for row in decision["items"]}


def current_price(symbol: str, package: dict, holding: dict) -> tuple[float | None, str | None, str | None]:
    record = quote_map(package).get(symbol)
    if record and record.get("last_price") is not None:
        return float(record["last_price"]), record.get("update_time"), record.get("source")
    raw = holding.get("current_price") or {}
    value = raw.get("value") or raw.get("last_price") or raw.get("price")
    return (float(value), raw.get("time") or raw.get("update_time"), raw.get("source")) if value is not None else (None, None, None)


def scenario_values(row: dict) -> tuple[dict, str]:
    values = row.get("scenario_values") or {}
    if not values:
        return {}, ""
    currency = "JPY" if any(key.endswith("_jpy") for key in values) else "USD"
    normalized = {}
    for key, value in values.items():
        name = key.split("_")[0]
        normalized[name] = float(value)
    return normalized, currency


def build_holding_table(package: dict, decision: dict) -> tuple[list[dict], dict]:
    total = float(package["accounts_and_risk"]["known_assets_total_jpy"])
    combined = {row["asset_id"]: row for row in package["accounts_and_risk"]["combined_positions"]}
    decisions = valuation_map(decision)
    rows = []
    for holding in package["holding_inputs"]["items"]:
        symbol = holding["symbol"]
        position = combined[symbol]
        price, price_time, price_source = current_price(symbol, package, holding)
        value_jpy = float(position["market_value_jpy"])
        weight = value_jpy / total
        valuation = decisions.get(symbol)
        scenarios, currency = scenario_values(valuation or {})
        scenario_returns = {}
        scenario_contribution_pp = {}
        if price and scenarios:
            for label, value in scenarios.items():
                scenario_returns[label] = round(value / price - 1.0, 8)
                scenario_contribution_pp[label] = round(weight * (value / price - 1.0) * 100.0, 6)
        classification = (valuation or {}).get("decision_class", "NO_APPROVED_NUMERIC_SCENARIO")
        numeric_ready = classification == "NUMERIC_VALUATION_APPROVED" and bool(scenario_returns)
        rows.append(
            {
                "symbol": symbol,
                "name": holding["name"],
                "market_value_jpy": money(value_jpy),
                "known_asset_weight_pct": pct(weight),
                "quantity_by_account": position.get("quantity_by_account", {}),
                "current_price": {"value": price, "time": price_time, "source": price_source},
                "latest_formal_financial": holding.get("financial_fact"),
                "company_guidance": guidance_for(symbol),
                "valuation_or_risk_pricing": {
                    "classification": classification,
                    "numeric_scenario_ready": numeric_ready,
                    "method": (valuation or {}).get("formula") or holding.get("valuation_input", {}).get("method"),
                    "input": (valuation or {}).get("input"),
                    "parameters": (valuation or {}).get("parameters"),
                    "scenario_values": scenarios,
                    "currency": currency or None,
                    "scenario_returns": scenario_returns,
                    "scenario_contribution_pp": scenario_contribution_pp,
                    "boundary": "数值仅为已批准条件情景的机械复算；概率和最终动作由GPT总控一次性裁定。" if numeric_ready else "不进入数值目标贡献；仅保留风险定价与验证条件。",
                },
                "probability_input": {
                    "value": None,
                    "status": "GPT_CONTROL_REQUIRED",
                    "derivation_required": ["正式指引兑现度", "财务质量", "估值或风险定价", "反向证据", "组合同一驱动与替换价值"],
                    "template_probability_removed": True,
                },
                "reverse_evidence": holding.get("reverse_evidence"),
                "company_or_industry_event": holding.get("company_or_industry_event"),
                "update_condition": holding.get("update_condition"),
                "action_boundary": "本包不作买卖、仓位或概率判断；现有保守状态不构成订单。",
                "gpt_control_fields": ["bear/base/bull情景是否采用", "各情景概率", "是否纳入目标贡献", "持有/等待/条件降风险", "替换对象与条件"],
            }
        )
    numeric_rows = [row for row in rows if row["valuation_or_risk_pricing"]["numeric_scenario_ready"]]
    coverage_value = sum(row["market_value_jpy"] for row in numeric_rows)
    summary = {
        "holding_count": len(rows),
        "guidance_reviewed_count": sum(1 for row in rows if row["company_guidance"]["status"]),
        "guidance_coverage_pct": pct(sum(1 for row in rows if row["company_guidance"]["status"]) / len(rows)),
        "numeric_scenario_count": len(numeric_rows),
        "numeric_scenario_market_value_jpy": money(coverage_value),
        "numeric_scenario_coverage_pct": pct(coverage_value / total),
        "unquantified_market_value_jpy": money(total - coverage_value),
        "unquantified_weight_pct": pct(1.0 - coverage_value / total),
        "probability_values_assigned_by_codex": 0,
    }
    return rows, summary


def build_target_bridge(package: dict, holdings: list[dict], summary: dict) -> dict:
    baseline = float(package["accounts_and_risk"]["known_assets_total_jpy"])
    contribution = {"bear": 0.0, "base": 0.0, "bull": 0.0}
    for row in holdings:
        for label, value in row["valuation_or_risk_pricing"]["scenario_contribution_pp"].items():
            contribution[label] += value
    contribution = {key: round(value, 6) for key, value in contribution.items()}
    start = datetime(2026, 8, 20, tzinfo=ZoneInfo("Asia/Tokyo"))
    end = datetime(2026, 12, 31, tzinfo=ZoneInfo("Asia/Tokyo"))
    checkpoints = [datetime(2026, month, day, tzinfo=ZoneInfo("Asia/Tokyo")) for month, day in [(9, 30), (10, 31), (11, 30), (12, 31)]]
    days = (end - start).days
    milestones = []
    for point in checkpoints:
        elapsed = (point - start).days
        milestones.append(
            {
                "date": point.date().isoformat(),
                "plus_40_path_jpy": money(baseline * (1.4 ** (elapsed / days))),
                "plus_100_path_jpy": money(baseline * (2.0 ** (elapsed / days))),
                "boundary": "平滑复利观察路径，不是收益承诺，也不是2026年实际完成度。",
            }
        )
    remaining_months = days / 30.4375
    return {
        "baseline": {
            "known_assets_jpy": money(baseline),
            "date": "2026-08-20",
            "status": "FORWARD_OBSERVATION_BASELINE_ONLY",
            "cannot_prove": "不能倒推2026年1月1日至8月19日实际收益，也不是完整四账户同日净资产。",
        },
        "targets": {
            "plus_40_end_value_jpy": money(baseline * 1.4),
            "plus_100_end_value_jpy": money(baseline * 2.0),
            "remaining_calendar_days": days,
            "smooth_monthly_return_required_plus_40_pct": round(((1.4 ** (1.0 / remaining_months)) - 1.0) * 100.0, 4),
            "smooth_monthly_return_required_plus_100_pct": round(((2.0 ** (1.0 / remaining_months)) - 1.0) * 100.0, 4),
            "monthly_milestones": milestones,
        },
        "mechanically_quantified_holdings": {
            "count": summary["numeric_scenario_count"],
            "coverage_pct": summary["numeric_scenario_coverage_pct"],
            "scenario_contribution_pp": contribution,
            "formula": "单项组合贡献百分点 = 已知资产权重 × (情景价格 ÷ 当前价格 - 1) × 100",
            "probability_weighted_result": None,
            "probability_status": "GPT_CONTROL_REQUIRED",
        },
        "risk_only_holdings": {
            "count": 24 - summary["numeric_scenario_count"],
            "weight_pct": summary["unquantified_weight_pct"],
            "treatment": "不填伪精确概率，不进入数值贡献合计；由GPT总控决定是否采用非价格情景。",
        },
        "mechanical_gap_after_quantified_scenarios_pp": {
            label: {
                "to_plus_40": round(40.0 - value, 6),
                "to_plus_100": round(100.0 - value, 6),
            }
            for label, value in contribution.items()
        },
        "required_new_opportunity_contribution": {
            "status": "GPT_CONTROL_REQUIRED",
            "formula": "目标差额 = 目标收益率 - 总控采用的现有持仓概率加权贡献 - 现金及其他资产贡献",
            "required_decisions": ["9项条件情景概率", "15项风险框架是否纳入", "现金收益假设", "新机会排序、成功概率和最大允许权重"],
            "boundary": "Codex不选择概率、仓位或机会；本表只把缺口变成可填写字段。",
        },
    }


def build_opportunity_gates(prior: dict) -> list[dict]:
    prior_items = prior.get("items") or prior.get("research_pool") or prior.get("opportunities") or []
    prior_map = {item.get("symbol") or item.get("asset_id"): item for item in prior_items}
    rows = []
    for symbol, item in OPPORTUNITIES.items():
        rows.append(
            {
                "symbol": symbol,
                "name": item["name"],
                "prior_trace": prior_map.get(symbol),
                "gate_1_sector_activation": {"status": "EVIDENCE_READY", "conclusion_input": item["activation"], "sector": item["sector"]},
                "gate_2_company_and_financial": {"status": "EVIDENCE_READY", "formal_guidance": item["financial"], "official_source": item["source"]},
                "gate_3_moat_and_competition": {"status": "EVIDENCE_READY", "conclusion_input": item["moat"]},
                "gate_4_valuation_or_risk_pricing": {"status": "METHOD_READY_PARAMETER_DECISION_PENDING", "conclusion_input": item["pricing"], "numeric_range": None},
                "gate_5_cash_and_replacement": {
                    "status": "INPUT_READY_FOR_GPT_DECISION",
                    "cash_comparison": item["cash_compare"],
                    "explicit_replacement_holdings": item["replacement"],
                    "replacement_logic": item["replacement_logic"],
                },
                "next_verification": item["next_trigger"],
                "current_identity": "研究观察池",
                "executable_now": False,
                "gpt_control_required": ["第五关通过或淘汰", "概率与情景", "相对排序", "替换对象", "最大允许权重", "触发条件"],
                "boundary": "证据输入闭合不等于第五关通过；Codex不升级为可执行机会。",
            }
        )
    return rows


def render_html(package: dict) -> str:
    def h(value: object) -> str:
        return html.escape(str(value))

    hs = package["holding_summary"]
    tb = package["target_contribution_bridge"]
    rows = []
    for item in package["holdings_24"]:
        guide = item["company_guidance"]
        rows.append(
            "<tr>"
            f"<td>{h(item['symbol'])}<br><b>{h(item['name'])}</b></td>"
            f"<td>{item['known_asset_weight_pct']:.2f}%</td>"
            f"<td>{h(guide['plain_status'])}<br>{h('；'.join(guide['facts']))}</td>"
            f"<td>{h(item['valuation_or_risk_pricing']['classification'])}<br>{h(item['valuation_or_risk_pricing']['boundary'])}</td>"
            f"<td>{h(guide['source_title'])}<br><a href=\"{h(guide['url'])}\">原文</a></td>"
            "</tr>"
        )
    gate_rows = []
    for item in package["priority_opportunity_gates"]:
        gate_rows.append(
            "<tr>"
            f"<td>{h(item['symbol'])}<br><b>{h(item['name'])}</b></td>"
            f"<td>{h(item['gate_1_sector_activation']['conclusion_input'])}</td>"
            f"<td>{h('；'.join(item['gate_2_company_and_financial']['formal_guidance']))}<br><a href=\"{h(item['gate_2_company_and_financial']['official_source'])}\">正式来源</a></td>"
            f"<td>{h(item['gate_3_moat_and_competition']['conclusion_input'])}</td>"
            f"<td>{h(item['gate_4_valuation_or_risk_pricing']['conclusion_input'])}</td>"
            f"<td>{h(item['gate_5_cash_and_replacement']['cash_comparison'])}<br>替换比较：{h('、'.join(item['gate_5_cash_and_replacement']['explicit_replacement_holdings']))}</td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><title>V7 v2.0最终能力闭合业务判断输入包</title>
<style>body{{font-family:'Microsoft YaHei',Arial,sans-serif;max-width:1500px;margin:24px auto;padding:0 18px;color:#17202a;line-height:1.55}}h1,h2{{color:#123b5d}}.banner{{border-left:6px solid #b33;padding:12px 16px;background:#fff4f4}}.ok{{color:#116530;font-weight:700}}.warn{{color:#9a5700;font-weight:700}}table{{width:100%;border-collapse:collapse;margin:14px 0 28px;font-size:13px}}th,td{{border:1px solid #b8c2cc;padding:8px;vertical-align:top}}th{{background:#eaf1f7}}code{{background:#f1f3f5;padding:2px 4px}}a{{color:#075ea8}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}}.metric{{border:1px solid #c7d0d9;padding:10px;background:#fafcfe}}</style></head>
<body><h1>V7 v2.0最终能力闭合业务判断输入包</h1>
<div class=\"banner\"><b>这不是产品，也不是投资结论。</b><br>本包只把24类持仓、8项重点机会和目标贡献桥交给GPT总控一次性裁定。未生成候选产品HTML或PDF，未Release，未覆盖日报，未调用交易功能。</div>
<p>run_id：<code>{h(package['run_id'])}</code>　生成时间：{h(package['generated_at_jst'])}</p>
<h2>能力闸结果</h2><div class=\"grid\">
<div class=\"metric\">24类持仓指引核对：<b>{hs['guidance_reviewed_count']}/24</b></div>
<div class=\"metric\">可机械复算情景：<b>{hs['numeric_scenario_count']}/24</b></div>
<div class=\"metric\">数值情景覆盖已知资产：<b>{hs['numeric_scenario_coverage_pct']:.2f}%</b></div>
<div class=\"metric\">重点机会第五关输入：<b>{len(package['priority_opportunity_gates'])}/8</b></div></div>
<p class=\"ok\">结论：{h(package['capability_qa']['overall_status'])}</p>
<p>“能力闭合”只表示总控可以一次性裁定，不表示24项都能数值估值，也不表示8项机会已经通过第五关。</p>
<h2>目标贡献桥</h2>
<p>已知资产观察基线：{tb['baseline']['known_assets_jpy']:,.2f}日元；＋40%观察终值：{tb['targets']['plus_40_end_value_jpy']:,.2f}日元；＋100%观察终值：{tb['targets']['plus_100_end_value_jpy']:,.2f}日元。</p>
<p>9项条件情景的机械贡献：悲观 {tb['mechanically_quantified_holdings']['scenario_contribution_pp']['bear']:.3f}个百分点；基准 {tb['mechanically_quantified_holdings']['scenario_contribution_pp']['base']:.3f}个百分点；乐观 {tb['mechanically_quantified_holdings']['scenario_contribution_pp']['bull']:.3f}个百分点。概率尚未由Codex填写。</p>
<p class=\"warn\">2026年度实际收益仍不可计算；这里是8月20日起的前瞻观察路径，不能冒充年初至今完成度。</p>
<h2>24类持仓业务判断输入</h2><table><thead><tr><th>资产</th><th>已知资产权重</th><th>公司最新指引</th><th>估值/风险定价</th><th>正式来源</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>8项重点机会正式五关输入</h2><p>全部仍是研究观察池；表内“输入齐全”不等于通过第五关。</p>
<table><thead><tr><th>标的</th><th>第一关</th><th>第二关</th><th>第三关</th><th>第四关</th><th>第五关比较</th></tr></thead><tbody>{''.join(gate_rows)}</tbody></table>
<h2>总控唯一交接</h2><p>请GPT总控在同一轮中填写：24项情景/概率/目标贡献采用与否；8项第五关通过或淘汰、排序、替换对象、最大允许权重及触发条件；＋40%/＋100%路径是否可行和需要的新机会贡献。Codex收到唯一判断文件后，才生成一次最终完整HTML。</p>
</body></html>"""


def main() -> None:
    now = datetime.now(ZoneInfo("Asia/Tokyo"))
    run_id = f"V7-FINAL-CAPABILITY-CLOSE-{now:%Y%m%d-%H%M%S}-JST"
    out_dir = ROOT / "output" / "decision_inputs" / f"{now:%Y-%m-%d}" / run_id
    out_dir.mkdir(parents=True, exist_ok=False)
    source = read_json(SOURCE_PACKAGE)
    valuation = read_json(VALUATION_DECISION)
    prior = read_json(PRIOR_GATES)
    holdings, holding_summary = build_holding_table(source, valuation)
    target_bridge = build_target_bridge(source, holdings, holding_summary)
    gates = build_opportunity_gates(prior)
    sources = []
    for symbol, item in GUIDANCE.items():
        sources.append({"asset_id": symbol, "role": "公司指引或适用性", **{key: item[key] for key in ("source_title", "publisher", "published_at", "period", "url", "locator")}})
    for symbol, item in OPPORTUNITIES.items():
        sources.append({"asset_id": symbol, "role": "机会五关正式财务与指引", "source_title": f"{item['name']} official financial results", "publisher": item["name"], "published_at": "2026", "period": "最新正式期间", "url": item["source"], "locator": "Financial results and guidance"})
    checks = [
        {"id": "QA-01", "name": "24项公司指引逐项核对", "observed": len(holdings), "required": 24, "pass": len(holdings) == 24},
        {"id": "QA-02", "name": "公司指引不再使用统一未提取占位", "observed": sum(row["company_guidance"]["status"] == "NOT_SEPARATELY_EXTRACTED" for row in holdings), "required": 0, "pass": all(row["company_guidance"]["status"] != "NOT_SEPARATELY_EXTRACTED" for row in holdings)},
        {"id": "QA-03", "name": "Codex未填模板概率", "observed": sum(row["probability_input"]["value"] is not None for row in holdings), "required": 0, "pass": all(row["probability_input"]["value"] is None for row in holdings)},
        {"id": "QA-03B", "name": "24项均列明概率推导所需事实", "observed": sum(bool(row["probability_input"]["derivation_required"]) for row in holdings), "required": 24, "pass": all(row["probability_input"]["derivation_required"] for row in holdings)},
        {"id": "QA-04", "name": "可复算情景资产覆盖率为实数且非零", "observed": holding_summary["numeric_scenario_coverage_pct"], "required": ">0", "pass": holding_summary["numeric_scenario_coverage_pct"] > 0},
        {"id": "QA-05", "name": "目标桥已给出基线、公式、情景贡献和月度里程碑", "observed": len(target_bridge["targets"]["monthly_milestones"]), "required": 4, "pass": len(target_bridge["targets"]["monthly_milestones"]) == 4},
        {"id": "QA-06", "name": "8项重点机会逐项形成第五关输入", "observed": len(gates), "required": 8, "pass": len(gates) == 8},
        {"id": "QA-06B", "name": "第五关输入闭合率与实际通过率分开登记", "observed": {"input_ready": len(gates), "passed_by_codex": sum(row["executable_now"] for row in gates)}, "required": {"input_ready": 8, "passed_by_codex": 0}, "pass": len(gates) == 8 and all(not row["executable_now"] for row in gates)},
        {"id": "QA-07", "name": "8项均与现金比较", "observed": sum(bool(row["gate_5_cash_and_replacement"]["cash_comparison"]) for row in gates), "required": 8, "pass": all(row["gate_5_cash_and_replacement"]["cash_comparison"] for row in gates)},
        {"id": "QA-08", "name": "8项均列明具体替换持仓", "observed": sum(bool(row["gate_5_cash_and_replacement"]["explicit_replacement_holdings"]) for row in gates), "required": 8, "pass": all(row["gate_5_cash_and_replacement"]["explicit_replacement_holdings"] for row in gates)},
        {"id": "QA-09", "name": "观察池未被Codex升级为可执行机会", "observed": sum(row["executable_now"] for row in gates), "required": 0, "pass": all(not row["executable_now"] for row in gates)},
        {"id": "QA-10", "name": "未生成产品或PDF", "observed": {"product_html": 0, "pdf": 0}, "required": {"product_html": 0, "pdf": 0}, "pass": True},
    ]
    overall = "CAPABILITY_CLOSED_FOR_GPT_JUDGMENT" if all(row["pass"] for row in checks) else "DISCLOSED_BUT_INCOMPLETE"
    package = {
        "schema_version": "v2.0-final-capability-input-1.0",
        "run_id": run_id,
        "status": "GPT_CONTROL_SINGLE_HANDOFF_READY" if overall.startswith("CAPABILITY_CLOSED") else "RETURNED_FOR_INPUT_COMPLETION",
        "generated_at_jst": now.isoformat(),
        "product_generated": False,
        "pdf_generated": False,
        "release_status": "NOT_AUTHORIZED",
        "current_executable": False,
        "source_lineage": {
            "stage_a_package": str(SOURCE_PACKAGE),
            "valuation_decision": str(VALUATION_DECISION),
            "prior_gate_trace": str(PRIOR_GATES),
            "task_file": str(TASK_FILE),
            "task_sha256": sha256(TASK_FILE),
        },
        "holding_summary": holding_summary,
        "holdings_24": holdings,
        "priority_opportunity_gates": gates,
        "target_contribution_bridge": target_bridge,
        "source_registry": sources,
        "capability_qa": {
            "overall_status": overall,
            "definition": {
                "DISCLOSED_BUT_INCOMPLETE": "只披露了缺口，尚不足以交总控统一裁定。",
                "CAPABILITY_CLOSED_FOR_GPT_JUDGMENT": "事实、计算和比较输入足够总控一次性裁定；不等于投资判断或产品通过。",
            },
            "checks": checks,
            "pass_count": sum(row["pass"] for row in checks),
            "fail_count": sum(not row["pass"] for row in checks),
        },
        "gpt_control_single_decision_contract": {
            "output_path": str(ROOT / "00_任务中心" / "V7_v2.0_GPT总控最终能力判断_Current.json"),
            "holdings_required": ["scenario_adoption", "bear_base_bull_probability", "target_contribution_inclusion", "final_action_boundary", "replacement_if_any"],
            "opportunities_required": ["gate5_pass_or_reject", "rank", "expected_return_or_no_range", "success_probability_or_no_probability", "replacement", "max_weight", "trigger", "invalidation"],
            "portfolio_required": ["plus40_feasibility", "plus100_feasibility", "cash_role", "required_new_opportunity_contribution", "next_review"],
            "single_handoff": True,
        },
        "codex_continuation_instruction": "读取GPT总控唯一判断文件后，只生成一次最终完整HTML；总控全文内容闸通过前禁止PDF。",
        "safety": {"release": False, "daily_report_overwrite": False, "trade_api": False, "orders": False},
    }
    main_json = out_dir / "V7_v2.0_GPT总控最终能力闭合判断输入包_20260821.json"
    main_html = out_dir / "V7_v2.0_GPT总控最终能力闭合判断输入包_20260821.html"
    write_json(main_json, package)
    main_html.write_text(render_html(package), encoding="utf-8")
    write_json(out_dir / "01_24类持仓指引估值与目标贡献输入_20260821.json", {"run_id": run_id, "summary": holding_summary, "items": holdings})
    write_json(out_dir / "02_8项重点机会正式五关输入_20260821.json", {"run_id": run_id, "items": gates})
    write_json(out_dir / "03_前瞻目标贡献与目标差额桥_20260821.json", {"run_id": run_id, **target_bridge})
    write_json(out_dir / "04_最终能力闭合语义QA_20260821.json", {"run_id": run_id, **package["capability_qa"]})
    write_json(out_dir / "05_正式来源注册表_20260821.json", {"run_id": run_id, "items": sources})
    write_json(out_dir / "06_执行日志与边界_20260821.json", {"run_id": run_id, "generated_at_jst": now.isoformat(), "python": PYTHON, "actions": ["读取既有账户、行情、财务、估值和五关实物", "逐项补齐24项公司指引状态", "机械复算9项条件情景贡献", "闭合8项重点机会现金及替换比较", "生成唯一总控判断输入包"], "prohibited_actions_confirmed": ["未生成产品HTML", "未生成PDF", "未Release", "未覆盖00_今日日报.pdf", "未调用交易功能", "未生成订单"]})
    current_json = ROOT / "00_任务中心" / "V7_v2.0_GPT总控最终能力闭合判断输入包_Current.json"
    current_html = ROOT / "00_任务中心" / "V7_v2.0_GPT总控最终能力闭合判断输入包_Current.html"
    current_json.write_bytes(main_json.read_bytes())
    current_html.write_bytes(main_html.read_bytes())
    manifest_items = []
    for path in sorted(out_dir.iterdir()):
        if path.is_file():
            manifest_items.append({"path": str(path), "size": path.stat().st_size, "modified_at": datetime.fromtimestamp(path.stat().st_mtime, ZoneInfo("Asia/Tokyo")).isoformat(), "sha256": sha256(path)})
    for path in (current_json, current_html):
        manifest_items.append({"path": str(path), "size": path.stat().st_size, "modified_at": datetime.fromtimestamp(path.stat().st_mtime, ZoneInfo("Asia/Tokyo")).isoformat(), "sha256": sha256(path)})
    write_json(out_dir / "07_全部实物SHA256清单_20260821.json", {"run_id": run_id, "items": manifest_items})
    print(json.dumps({"run_id": run_id, "output_dir": str(out_dir), "status": overall, "current_json": str(current_json), "current_html": str(current_html)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
