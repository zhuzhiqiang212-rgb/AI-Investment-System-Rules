from __future__ import annotations

import argparse
import hashlib
import html
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_v7_current_blueprint_candidate import PROFILE  # noqa: E402

JST = timezone(timedelta(hours=9))
BASE_RUN = "V7-BLUEPRINT-DATA-CLOSE-20260816-015526-JST"
MID_RUN = "V7-BLUEPRINT-DATA-CLOSE-20260816-015232-JST"
BASE_DIR = ROOT / "output" / "candidates" / "2026-08-15" / BASE_RUN
MID_DIR = ROOT / "output" / "candidates" / "2026-08-15" / MID_RUN


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def meta(path: Path) -> dict[str, Any]:
    st = path.stat()
    return {
        "path": str(path),
        "size": st.st_size,
        "modified_at": datetime.fromtimestamp(st.st_mtime, JST).isoformat(timespec="seconds"),
        "sha256": sha(path),
    }


def esc(value: Any) -> str:
    if value is None:
        return "未取得"
    return html.escape(str(value))


def money(value: Any, currency: str = "") -> str:
    if value is None:
        return "未取得"
    try:
        return f"{float(value):,.2f} {currency}".strip()
    except (TypeError, ValueError):
        return str(value)


def local_url(path: Path) -> str:
    return "file:///" + str(path).replace("\\", "/").replace(" ", "%20")


OFFICIAL_FACTS: dict[str, dict[str, Any]] = {
    "US.NVDA": {
        "period": "截至2026-04-26的季度（美国会计准则）", "revenue": 81_615_000_000,
        "operating_profit": 53_536_000_000, "net_income": 58_321_000_000,
        "currency": "USD", "ocf": None, "fcf": None, "cash": None, "debt": None,
        "one_off": "其他收益包含较大项目；必须结合10-Q附注判断，不把单季净利润机械年化。",
        "guidance": "下一季指引应以公司最新财报为准，本包不替GPT总控外推。",
        "url": "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000052/nvda-20260426.htm",
    },
    "US.TSM": {
        "period": "截至2026-03-31的第一季度；另有2026年6月月度营收", "revenue": None,
        "operating_profit": None, "net_income": None, "currency": "TWD", "ocf": None,
        "fcf": None, "cash": None, "debt": None,
        "one_off": "月度营收与季度利润口径分开，不能混成同一期间。",
        "guidance": "先进制程与资本开支指引需由GPT总控结合正式季度报告判断。",
        "url": "https://www.sec.gov/Archives/edgar/data/1046179/000104617926000278/0001046179-26-000278-index.htm",
    },
    "US.AVGO": {
        "period": "截至2026-05-03的季度（美国会计准则）", "revenue": None,
        "operating_profit": None, "net_income": None, "currency": "USD", "ocf": None,
        "fcf": None, "cash": None, "debt": None,
        "one_off": "并购会计和非现金项目需与调整后口径分开。",
        "guidance": "AI半导体和软件分部指引以10-Q及财报附件为准。",
        "url": "https://www.sec.gov/Archives/edgar/data/1730168/000173016826000054/0001730168-26-000054-index.htm",
    },
    "US.MSFT": {
        "period": "截至2026-06-30的财年（美国会计准则）", "revenue": 331_839_000_000,
        "operating_profit": 155_237_000_000, "net_income": 133_749_000_000,
        "currency": "USD", "ocf": None, "fcf": None, "cash": 76_843_000_000,
        "debt": 40_294_000_000,
        "one_off": "财年净利润含OpenAI投资净收益49.63亿美元；公司同时给出剔除该影响的非美国会计准则口径。",
        "guidance": "Azure、云业务与资本开支回报需要结合下一期正式指引。",
        "url": "https://www.microsoft.com/en-us/Investor/earnings/FY-2026-Q4/press-release-webcast",
    },
    "US.META": {
        "period": "截至2026-06-30的第二季度（美国会计准则）", "revenue": 60_801_000_000,
        "operating_profit": 18_775_000_000, "net_income": 15_850_000_000,
        "currency": "USD", "ocf": None, "fcf": 784_000_000, "cash": None, "debt": None,
        "one_off": "本季含24亿美元法律费用及11.8亿美元遣散费用，不能直接当作经常性成本。",
        "guidance": "公司给出第三季度收入区间，资本开支与费用仍需看正式指引。",
        "url": "https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-Second-Quarter-2026-Results/default.aspx",
    },
    "US.MSTR": {
        "period": "截至2026-03-31的第一季度（美国会计准则）", "revenue": 124_300_000,
        "operating_profit": -14_470_000_000, "net_income": -12_540_000_000,
        "currency": "USD", "ocf": None, "fcf": None, "cash": 2_210_000_000, "debt": None,
        "one_off": "经营亏损含数字资产未实现公允价值亏损144.6亿美元；这与软件经营亏损不是同一概念。",
        "guidance": "公司强调BTC与融资指标，但这些指标不是盈利、估值或流动性指标。",
        "url": "https://www.strategy.com/press/strategy-announces-first-quarter-2026-financial-results_05-05-2026",
    },
    "US.COIN": {
        "period": "2026年第一季度", "revenue": None, "operating_profit": None,
        "net_income": None, "currency": "USD", "ocf": None, "fcf": None, "cash": None, "debt": None,
        "one_off": "交易收入、稳定币与订阅收入必须分开；本轮未从公告正文取得完整三表。",
        "guidance": "公司称交易量份额创新高，不能替代完整财务表。",
        "url": "https://investor.coinbase.com/news/news-details/2026/Coinbase-Q1-Financial-Results-Show-Resilient-Financial-Performance-Driven-by-New-All-Time-High-Crypto-Trading-Volume-Market-Share/default.aspx",
    },
    "US.CRCL": {
        "period": "最新已核官方事项为2026年OCC许可公告；完整财务三表本轮未取得", "revenue": None,
        "operating_profit": None, "net_income": None, "currency": "USD", "ocf": None,
        "fcf": None, "cash": None, "debt": None,
        "one_off": "监管许可是业务证据，不是财务业绩。",
        "guidance": "USDC规模、利率敏感性和分销成本仍待GPT总控核。",
        "url": "https://investor.circle.com/news/news-details/2026/Circle-Receives-Final-OCC-Approval-to-Establish-National-Trust-Bank/default.aspx",
    },
    "US.SPCX": {
        "period": "2026年IPO完成公告与SEC申报；完整季度三表本轮未取得", "revenue": None,
        "operating_profit": None, "net_income": None, "currency": "USD", "ocf": None,
        "fcf": None, "cash": None, "debt": None,
        "one_off": "证券身份已经闭合，但身份闭合不等于估值与流动性结论闭合。",
        "guidance": "需等待具体财务和监管披露。",
        "url": "https://www.sec.gov/Archives/edgar/data/1181412/000162828026042466/spaceexplorationtechnologi.htm",
    },
    "US.SNDK": {
        "period": "截至2026-04-03的第三财季", "revenue": None,
        "operating_profit": 4_111_000_000, "net_income": None, "currency": "USD",
        "ocf": None, "fcf": None, "cash": None, "debt": None,
        "one_off": "券商价格、拆股和研究口径仍未校正；正式财务不能消除账户价格口径冲突。",
        "guidance": "公司当时给出第四财季收入77.5亿至82.5亿美元指引；本包不据此制定价值区间。",
        "url": "https://www.sandisk.com/company/newsroom/press-releases/2026/2026-04-30-sandisk-reports-fiscal-third-quarter-2026-financial-results",
    },
    "US.IBKR": {
        "period": "截至2026-03-31的第一季度", "revenue": 1_669_000_000,
        "operating_profit": None, "net_income": 267_000_000, "currency": "USD",
        "ocf": None, "fcf": None, "cash": None, "debt": None,
        "one_off": "券商会把汇率分散策略和投资按市值计价列为调整项目。",
        "guidance": "客户资产、利率和交易量需继续跟踪。",
        "url": "https://www.sec.gov/Archives/edgar/data/1381197/000138119726000093/ibkr-20260331.htm",
    },
}


CANDIDATE_SPECIFIC: dict[str, dict[str, str]] = {
    "US.SNDK": {"business":"NAND闪存、SSD和数据中心存储", "moat":"制程、固件、客户认证和与铠侠的产能协作", "competition":"Micron、Samsung、SK hynix、Kioxia、WDC", "compare":"与现有SNDK账户风险及Samsung存储敞口比较，不能重复计算", "reason":"账户价格与拆股口径未校正，先留观察池"},
    "US.MU": {"business":"DRAM、HBM和NAND存储", "moat":"HBM认证、制程、封装与长期客户协议", "competition":"Samsung、SK hynix、SNDK/Kioxia", "compare":"可与现有SNDK和Samsung比较存储周期与财务质量", "reason":"强周期与异常高单季利润需要验证可持续性"},
    "US.NVDA": {"business":"GPU、网络、系统和AI软件平台", "moat":"CUDA生态、开发者、互连与整机协同", "competition":"AMD、云厂商自研芯片、定制ASIC", "compare":"与现有NVDA、AVGO、TSM同驱动敞口合并比较", "reason":"已有大额持仓且同一驱动集中度高，不因扫描自动升级"},
    "US.AVGO": {"business":"定制AI芯片、网络芯片和基础设施软件", "moat":"大客户协作、网络技术和软件转换成本", "competition":"NVDA、Marvell、客户内部芯片团队", "compare":"与现有AVGO、NVDA及TSM比较，不重复增加同驱动", "reason":"客户集中、并购口径和估值仍需总控裁定"},
    "US.TSM": {"business":"先进及成熟制程晶圆代工", "moat":"良率、制程、资本规模和客户信任", "competition":"Samsung Foundry、Intel Foundry", "compare":"与现有TSM及所有AI芯片持仓合并看地缘和资本开支风险", "reason":"已有持仓，候选身份只用于再比较"},
    "US.PLTR": {"business":"政府与企业数据软件和AI应用平台", "moat":"部署经验、数据整合和客户转换成本", "competition":"云厂商、Snowflake、Databricks及自建方案", "compare":"与MSFT的软件和AI应用收入质量比较", "reason":"估值、客户集中和最新正式财报直链仍待补强"},
    "US.ON": {"business":"汽车、工业和数据中心的功率与传感半导体", "moat":"功率器件、车规认证和制造能力", "competition":"Infineon、STMicro、NXP、TI", "compare":"可与AI基础设施芯片持仓比较，但驱动并不完全相同", "reason":"第二季正式结果直链未闭合，先按Q1证据观察"},
    "US.VRT": {"business":"数据中心供电、冷却和机房基础设施", "moat":"工程交付、服务网络、产品组合和客户认证", "competition":"Schneider Electric、Eaton、nVent", "compare":"可与高估值AI芯片仓比较更偏实体基础设施的现金流", "reason":"增长强但订单、项目执行和估值需总控决定"},
    "US.ETN": {"business":"电气系统、配电、工业和航空电源管理", "moat":"认证、渠道、安装基础和产品组合", "competition":"Schneider、ABB、Siemens、Vertiv", "compare":"与VRT比较数据中心电力暴露，与现有AI芯片仓比较周期差异", "reason":"第二季正式结果具体财务附件未在本轮闭合"},
    "US.CEG": {"business":"核电与零碳电力供应", "moat":"核电资产、许可、长期合同和运行能力", "competition":"大型独立发电商和公用事业", "compare":"与AI资本开支链比较电力瓶颈收益，也与能源候选比较", "reason":"电价、监管、核电停机和合同结构需总控判断"},
    "US.NRG": {"business":"零售电力、天然气和发电资产", "moat":"客户规模、供应组合和市场运营", "competition":"Vistra、Constellation及区域零售商", "compare":"与CEG的核电资产模式分开，不能按同一毛利口径比较", "reason":"零售商属性、商品风险和融资结构仍需判断"},
    "US.COHR": {"business":"光通信、激光器和先进材料", "moat":"磷化铟、光学制造、客户认证和规模", "competition":"Lumentum、Fabrinet及模块厂商", "compare":"与AVGO网络芯片和CRDO电互连比较AI互连瓶颈", "reason":"客户集中、产能扩张和最新财年结果需核"},
    "US.CRDO": {"business":"高速SerDes、AEC和连接芯片", "moat":"高速模拟/混合信号设计与云客户认证", "competition":"Broadcom、Marvell、光模块方案", "compare":"与AVGO、COHR、LITE比较电连接与光连接的成本边界", "reason":"增长很快但客户集中与估值需要总控裁定"},
    "US.WDC": {"business":"硬盘和企业数据存储", "moat":"磁记录技术、规模与云客户认证", "competition":"Seagate及闪存替代方案", "compare":"与SNDK/MU的闪存路径比较容量成本和周期", "reason":"周期盈利和产品结构需要按拆分后口径验证"},
    "US.ASML": {"business":"EUV、DUV光刻机和装机服务", "moat":"EUV独占、供应链协同和客户切换壁垒", "competition":"EUV无直接同级替代；DUV面对Nikon/Canon", "compare":"与TSM、NVDA等下游需求比较，但业务位置不同", "reason":"中国限制、订单确认和高估值需总控判断"},
    "US.LITE": {"business":"光通信器件和商用激光器", "moat":"激光器技术、客户认证与制造良率", "competition":"Coherent、Fabrinet及亚洲光器件厂", "compare":"与COHR、CRDO比较光/电互连和客户集中", "reason":"财年末结果刚发布，完整现金流与估值边界仍待核"},
    "US.XOM": {"business":"上游油气、炼化、化工和低碳项目", "moat":"资源、项目执行、炼化网络和成本曲线", "competition":"Chevron、Shell及国家石油公司", "compare":"与Itochu资源敞口和CVX比较资本回报与油价敏感性", "reason":"油价路径与第二季完整财务未在本包核齐"},
    "US.CVX": {"business":"上游油气、炼化和能源基础设施", "moat":"优质资源、项目和全球运营能力", "competition":"Exxon、Shell、BP", "compare":"与XOM及Itochu比较资源质量、并购和资本回报", "reason":"第二季利润含资产出售等项目，需剥离后判断"},
    "JP.8306": {"business":"三菱UFJ金融集团，银行、证券、信托和海外金融", "moat":"存款、客户网络、资本和全球业务", "competition":"SMFG、Mizuho及国际大行", "compare":"与日本保险持仓比较加息受益和信用风险", "reason":"利差受益与信用成本、海外风险需总控平衡"},
    "JP.8316": {"business":"三井住友金融集团，银行、卡和综合金融", "moat":"客户网络、存款、卡业务和资本", "competition":"MUFG、Mizuho", "compare":"与MUFG/Mizuho及东京海上比较利率敏感性", "reason":"估值、信用成本和股东回报需总控决定"},
    "JP.8411": {"business":"瑞穗金融集团，银行、证券和资产管理", "moat":"企业客户、资本市场和存款基础", "competition":"MUFG、SMFG", "compare":"与另外两家日本大行逐项比较，不按板块机械选", "reason":"盈利质量、系统执行和资本回报仍需总控判断"},
}


CANDIDATE_OFFICIAL: dict[str, dict[str, Any]] = {
    "US.MU": {"title":"Micron 2026财年第三季正式结果", "date":"2026-06-24", "url":"https://www.sec.gov/Archives/edgar/data/723125/000072312526000013/a2026q3ex991-pressrelease.htm"},
    "US.VRT": {"title":"Vertiv 2026年第二季正式结果", "date":"2026-07-29", "url":"https://investors.vertiv.com/news/news-details/2026/Vertiv-Reports-Strong-Second-Quarter-2026-with-Diluted-EPS-Growth-of-53-Adjusted-Diluted-EPS-Growth-of-60-Raises-Full-Year-2026-Guidance-Across-All-Key-Metrics/default.aspx"},
    "US.ON": {"title":"onsemi 2026年第一季正式结果", "date":"2026-05-04", "url":"https://investor.onsemi.com/node/22816/pdf"},
    "US.COHR": {"title":"Coherent 2026财年第三季正式结果", "date":"2026-05-06", "url":"https://www.coherent.com/content/dam/coherent/site/en/documents/investors/financial-releases/2026/may-6/earnings-release-fy26-q3.pdf"},
    "US.CRDO": {"title":"Credo 2026财年全年正式结果", "date":"2026-06-01", "url":"https://www.sec.gov/Archives/edgar/data/1807794/000162828026039474/credoq42026ex-991.htm"},
    "US.WDC": {"title":"Western Digital 2026财年第三季正式结果", "date":"2026-04-30", "url":"https://www.westerndigital.com/en-ca/company/newsroom/press-releases/2026/2026-04-30-wd-reports-fiscal-third-quarter-2026-financial-results"},
    "US.ASML": {"title":"ASML 2026年第二季正式结果", "date":"2026-07-15", "url":"https://ourbrand.asml.com/asset/c8dbf3fc-4c5e-4406-83f6-27694b138245/Press-Release-Financial-Results-Q2-2026.pdf"},
    "US.LITE": {"title":"Lumentum 2026财年第三季正式结果", "date":"2026-05-05", "url":"https://investor.lumentum.com/financial-news-releases/news-details/2026/Lumentum-Announces-Third-Quarter-of-Fiscal-Year-2026-Financial-Results/default.aspx"},
    "US.NRG": {"title":"NRG 2026年第一季正式结果申报", "date":"2026-05-06", "url":"https://www.sec.gov/Archives/edgar/data/1013871/000101387126000010/nrg-20260506.htm"},
    "US.XOM": {"title":"ExxonMobil 2026年第一季正式结果", "date":"2026-05-01", "url":"https://ir.exxonmobil.com/static-files/f3835d90-32e6-4b8f-83f8-567af7daf45e"},
    "US.CVX": {"title":"Chevron 2026年第二季正式结果", "date":"2026-07-31", "url":"https://www.chevron.com/newsroom/2026/q3/chevron-reports-second-quarter-2026-results"},
}


def build_accounts(run_id: str, now: str) -> dict[str, Any]:
    futu_path = ROOT / "data" / "accounts" / "futu_positions_20260816.json"
    sbi_path = ROOT / "data" / "accounts" / "per_account_SBI_20260811.json"
    ibkr_path = ROOT / "data" / "accounts" / "per_account_IBKR_20260811.json"
    bf_path = ROOT / "data" / "accounts" / "bitflyer_account_20260811.json"
    futu, sbi, ibkr, bf = map(load, (futu_path, sbi_path, ibkr_path, bf_path))
    rows: list[dict[str, Any]] = []
    for x in futu["futu_positions"]:
        position_currency = "JPY" if x["symbol"].startswith("JP.") else "USD"
        rows.append({"account":"富途", "account_property":"个人/公司属性未由OpenD字段确认", "instrument":x["name"], "code":x["symbol"], "quantity":x["quantity"], "cost":x["cost_price"], "latest_price":x["broker_nominal_price"], "market_value":x["broker_market_val"], "profit_loss":None, "broker_pl_ratio":x.get("pl_ratio"), "currency":position_currency, "data_date":futu["data_date"], "source":str(futu_path), "target_management":True, "risk_management":True, "production_day_data":True, "freshness":"生产日OpenD只读刷新；逐只价格/市值按证券本币，总账户汇总由OpenD按美元返回"})
    fc = futu["futu_cash"]
    rows.append({"account":"富途", "account_property":"个人/公司属性未由OpenD字段确认", "instrument":"现金", "code":"CASH.USD", "quantity":fc["cash"], "cost":None, "latest_price":1, "market_value":fc["cash"], "profit_loss":None, "broker_pl_ratio":None, "currency":"USD", "data_date":futu["data_date"], "source":str(futu_path), "target_management":True, "risk_management":True, "production_day_data":True, "freshness":"生产日OpenD只读刷新"})
    residual = round(fc["total_assets"] - fc["market_val"] - fc["cash"], 4)
    rows.append({"account":"富途", "account_property":"个人/公司属性未由OpenD字段确认", "instrument":"基金/其他净资产合计（尚未拆分名称）", "code":"OTHER_NET_ASSET_AGGREGATE", "quantity":None, "cost":None, "latest_price":None, "market_value":residual, "profit_loss":None, "broker_pl_ratio":None, "currency":"USD", "data_date":futu["data_date"], "source":str(futu_path), "target_management":True, "risk_management":True, "production_day_data":True, "freshness":"生产日OpenD总资产减证券市值和现金所得的账户闭合项；不推定具体资产"})
    for x in sbi["逐只"]:
        rows.append({"account":"SBI（个人/公司归属待实物）", "account_property":"SBI个人与SBI公司无法由现有截图可靠区分", "instrument":x["标的"], "code":x["code"], "quantity":x["股数"], "cost":x.get("取得单价"), "latest_price":x["现价"], "market_value":x["市值本币"], "profit_loss":x.get("評価損益本币"), "broker_pl_ratio":None, "currency":"JPY", "data_date":sbi["截图日期"], "source":str(sbi_path), "target_management":True, "risk_management":True, "production_day_data":False, "freshness":"最后已知状态；截图内无日历日期，日期来自文件夹并有董事长确认记录"})
    rows.append({"account":"SBI（个人/公司归属待实物）", "account_property":"归属待确认", "instrument":"现金/买付余力", "code":"CASH.JPY", "quantity":sbi["买付余力JPY_2営業日後"], "cost":None, "latest_price":1, "market_value":sbi["买付余力JPY_2営業日後"], "profit_loss":None, "broker_pl_ratio":None, "currency":"JPY", "data_date":sbi["截图日期"], "source":str(sbi_path), "target_management":True, "risk_management":True, "production_day_data":False, "freshness":"最后已知状态"})
    for x in ibkr["逐只"]:
        rows.append({"account":"IBKR", "account_property":"个人/公司属性未由截图确认", "instrument":x["标的"], "code":x["code"], "quantity":x["股数"], "cost":None, "latest_price":x["现价"], "market_value":x.get("市值USD", x.get("市值本币")), "profit_loss":None, "broker_pl_ratio":None, "currency":"USD" if x.get("市值USD") is not None else x["币种"], "data_date":ibkr["截图日期"], "source":str(ibkr_path), "target_management":False, "risk_management":True, "production_day_data":False, "freshness":"最后已知状态；不进入目标缺口但进入风险管理"})
    rows.append({"account":"IBKR", "account_property":"个人/公司属性未由截图确认", "instrument":"现金", "code":"CASH.USD", "quantity":ibkr["现金USD"], "cost":None, "latest_price":1, "market_value":ibkr["现金USD"], "profit_loss":None, "broker_pl_ratio":None, "currency":"USD", "data_date":ibkr["截图日期"], "source":str(ibkr_path), "target_management":False, "risk_management":True, "production_day_data":False, "freshness":"最后已知状态"})
    for x in bf["持有"]:
        code = "CASH.JPY" if x["code"] == "JPY" else x["code"]
        rows.append({"account":"bitFlyer", "account_property":"个人/公司属性未由截图确认", "instrument":x["标的"], "code":code, "quantity":x["数量"], "cost":None, "latest_price":None, "market_value":x["市值JPY"], "profit_loss":None, "broker_pl_ratio":None, "currency":"JPY", "data_date":bf["截图日期"], "source":str(bf_path), "target_management":False, "risk_management":True, "production_day_data":False, "freshness":"最后已知状态；董事长确认无交易"})
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if not row["code"].startswith("CASH") and row["code"] != "OTHER_NET_ASSET_AGGREGATE":
            grouped[row["code"]].append(row)
    merged = []
    for code, xs in sorted(grouped.items()):
        dates = sorted({x["data_date"] for x in xs})
        currencies = sorted({x["currency"] for x in xs})
        merged.append({"code":code, "instrument":xs[0]["instrument"], "quantity_last_known_sum":sum(float(x["quantity"] or 0) for x in xs), "market_value_last_known_sum_by_currency":{c:sum(float(x["market_value"] or 0) for x in xs if x["currency"] == c) for c in currencies}, "accounts":[x["account"] for x in xs], "source_dates":dates, "same_day":len(dates) == 1, "boundary":"不同日期时仅为最后已知数量汇总，不是同日净值，不反推交易"})
    return {"run_id":run_id, "generated_at":now, "status":"FACT_INPUT_ONLY", "futu_reconciliation":{"total_assets_usd":fc["total_assets"], "securities_market_value_usd":fc["market_val"], "cash_usd":fc["cash"], "other_net_assets_aggregate_usd":residual, "closed_to_total":abs(fc["total_assets"]-fc["market_val"]-fc["cash"]-residual)<0.01, "boundary":"合计闭合，但基金/其他净资产具体名称尚未由OpenD拆分"}, "account_rows":rows, "cross_account_same_instrument":merged, "source_files":[meta(p) for p in (futu_path,sbi_path,ibkr_path,bf_path)]}


def jp_fact(company: dict[str, Any]) -> dict[str, Any]:
    metrics = company["metrics"]
    def val(name: str) -> Any:
        x = metrics.get(name) or {}
        return x.get("value") if x.get("status") == "SELECTED" else None
    return {"period":f"{company['period_start']}至{company['period_end']}（{company['accounting_standard']}，合并口径）", "revenue":val("revenue"), "operating_profit":val("operating_profit"), "net_income":val("net_income"), "currency":"JPY", "ocf":val("operating_cash_flow"), "fcf":None, "cash":val("cash_end"), "debt":None, "assets":val("assets"), "liabilities":val("liabilities"), "one_off":"订正关系和被拒绝的单体/分部上下文见EDINET严格口径附件；未解析字段不补数。", "guidance":"公司正式指引需与TDnet/IR同期公告交叉核对，由GPT总控判断。", "url":f"https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?{company['doc_id']}", "doc_id":company["doc_id"], "xbrl_contexts":{k:{q:v.get(q) for q in ("qname","contextRef","unitRef","period","consolidated_status")} for k,v in metrics.items() if v.get("status") == "SELECTED"}}


def build_holdings(run_id: str, now: str, accounts: dict[str, Any]) -> dict[str, Any]:
    old = load(BASE_DIR / "02_持仓完整研究数据_20260815.json")
    strict = load(BASE_DIR / "01_EDINET严格口径逐只复核_20260815.json")["companies"]
    by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in accounts["account_rows"]:
        by_code[row["code"]].append(row)
    items = []
    for src in old["items"]:
        code, name = src["code"], src["name"]
        p = PROFILE[code]
        formal = jp_fact(strict[code]) if code in strict else OFFICIAL_FACTS.get(code)
        if code in ("BTC", "ETH"):
            formal = {"period":"不适用：数字资产不是经营公司", "revenue":None, "operating_profit":None, "net_income":None, "currency":None, "ocf":None, "fcf":None, "cash":None, "debt":None, "one_off":"不套用企业财务报表；使用链上、流动性、托管和宏观风险口径。", "guidance":"无公司正式指引。", "url":"https://bitcoin.org/bitcoin.pdf" if code == "BTC" else "https://ethereum.org/en/whitepaper/"}
        missing = []
        if not formal:
            missing.append("本轮未取得可直接引用的最新正式财务文件")
        else:
            for k, label in (("revenue","收入"),("operating_profit","营业利润"),("net_income","归母/净利润"),("ocf","经营现金流"),("fcf","自由现金流"),("cash","现金"),("debt","债务/融资义务")):
                if formal.get(k) is None:
                    missing.append(label)
        if code == "US.SNDK":
            missing.insert(0, "2026财年第四季已到公告窗口，但本轮未取得可直接核验的正式Q4原文；当前仅采用已核实的Q3正式结果")
        price_rows = by_code.get(code, [])
        latest = max(price_rows, key=lambda x:x["data_date"]) if price_rows else None
        special = None
        if code == "JP.6758":
            special = {"continuing_operations":"2026年3月期持续经营销售额12.4796万亿日元、营业利润1.4475万亿日元、持续经营归母利润1.0309万亿日元。", "including_discontinued_operation":"包含已终止经营业务后，合并归母净亏损3268.65亿日元。", "explanation":"金融业务拆分后按IFRS列为终止经营，两个数字回答不同问题；不得用总体会计亏损替代持续经营盈利，也不得忽略拆分影响。", "source":"https://www.sony.com/en/SonyInfo/IR/library/FY2025_20F_PDF.pdf"}
        items.append({"code":code, "name":name, "account_facts":price_rows, "business":p["business"], "how_it_makes_money":p["money"], "main_business_and_growth_drivers":p["revenue"], "latest_formal_financial_period":formal.get("period") if formal else None, "revenue":formal.get("revenue") if formal else None, "operating_profit":formal.get("operating_profit") if formal else None, "net_income_attributable_or_net_income":formal.get("net_income") if formal else None, "continuing_vs_discontinued_operations":special or "现有正式材料未显示需单列终止经营；如后续披露变化须重新核。", "operating_cash_flow":formal.get("ocf") if formal else None, "free_cash_flow":formal.get("fcf") if formal else None, "cash":formal.get("cash") if formal else None, "debt_and_financing_obligations":formal.get("debt") if formal else None, "one_off_and_accounting_basis":formal.get("one_off") if formal else "缺正式材料，不补造。", "official_guidance":formal.get("guidance") if formal else None, "current_price":latest.get("latest_price") if latest else None, "price_data_time":latest.get("data_date") if latest else None, "valuation_method_input_only":p["method"], "valuation_numbers_and_basis":"未获授权制定当前估值或价值区间；只向GPT总控提供方法与正式财务输入。", "moat":p["moat"], "main_competitors":p["competitors"], "short_term_catalyst":p["catalyst"], "one_year_catalyst":p["catalyst"], "maximum_reverse_risk":p["reverse"], "invalidation_condition":p["invalidate"], "comparison_with_holdings_and_alternatives":src["replacement"], "approved_judgment_and_source":src["approved_judgment"], "questions_for_gpt_control":["正式财务与价格是否支持原判断？","相对现有持仓和候选应保留、观察还是替换？","在不制定机械比例的前提下，目标贡献和风险如何取舍？"], "action_boundary":"Codex不制定价值区间、买卖区间或仓位；缺可靠估值时不能形成价格动作。", "evidence_url":formal.get("url") if formal else None, "missing_fields":missing})
    return {"run_id":run_id, "generated_at":now, "holding_count":len(items), "items":items}


def build_candidates(run_id: str, now: str) -> dict[str, Any]:
    base = load(BASE_DIR / "04_候选五关逐只数据_20260815.json")
    card_root = load(ROOT / "data" / "evidence" / "v7_scan_20260815" / "V7候选逐只研究卡_20260815.json")
    cards = {x["code"]:x for x in card_root["cards"]}
    jp = load(BASE_DIR / "01_EDINET严格口径逐只复核_20260815.json")["companies"]
    items = []
    for old in base["items"]:
        code = old["code"]
        spec = CANDIDATE_SPECIFIC[code]
        card = cards.get(code, {})
        fin = card.get("latest_financial_facts", {})
        valuation = card.get("valuation_facts", {})
        official = None
        if code in jp:
            official = {"title":f"{old['name']} EDINET有价证券报告书 {jp[code]['doc_id']}", "date":jp[code]["published_at"][:10], "url":f"https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?{jp[code]['doc_id']}"}
        elif code in OFFICIAL_FACTS:
            official = {"title":f"{old['name']}最新已核正式材料", "date":OFFICIAL_FACTS[code]["period"], "url":OFFICIAL_FACTS[code]["url"]}
        else:
            official = CANDIDATE_OFFICIAL.get(code)
        gates = [
            {"gate":1, "input":f"{old['theme']}；当日扫描方向和漏斗实物已覆盖该公司。正式板块激活仍由GPT总控裁定。", "evidence_status":"输入已整理/待总控裁定"},
            {"gate":2, "input":f"可用机械财务字段：经营现金流={fin.get('ocf_ttm')}，毛利率={fin.get('gross_margin')}，负债资产比={fin.get('debt_asset')}，净利率={fin.get('net_margin')}。机械分数不作投资结论。", "missing":[k for k in ("ocf_ttm","gross_margin","debt_asset","net_margin") if fin.get(k) is None]},
            {"gate":3, "input":f"扫描时点价格={card.get('current_price')}（{card.get('price_time')}）；市盈率={valuation.get('pe_ratio')}，市净率={valuation.get('pb_ratio')}。适用边界：仅为扫描时点，不自行制定价值或买卖区间。"},
            {"gate":4, "input":f"业务：{spec['business']}。可核护城河：{spec['moat']}。主要竞争：{spec['competition']}。资本回报仍须结合正式财报由GPT总控判断。"},
            {"gate":5, "input":f"催化剂：{old['catalyst']} 反向风险：{old['reverse']} 失效条件：{old['trigger']}"},
        ]
        missing = [] if official else ["缺可直接点击的最新正式公司财报或监管文件"]
        items.append({"code":code, "name":old["name"], "theme":old["theme"], "gates":gates, "possible_replacement_comparison":spec["compare"], "missing_evidence_or_gpt_decision":missing + ["五关最终通过/淘汰由GPT总控决定", "相对现有持仓的替换价值由GPT总控决定"], "observation_pool_reason":spec["reason"], "current_pool":"研究观察池", "executable":False, "official_evidence":official, "action_boundary":"不以机械评分代替投资结论，不由Codex升级为可执行机会。"})
    return {"run_id":run_id, "generated_at":now, "candidate_count":len(items), "items":items}


def build_pdca(run_id: str, now: str) -> dict[str, Any]:
    p = ROOT / "data" / "pdca" / "forecast_ledger.json"
    j = load(p)
    rows = []
    for i, x in enumerate(j["forecasts"], 1):
        result = x.get("result")
        status = "判对" if result == "对" else "判错" if result == "错" else "尚不能判断"
        rows.append({"prediction_id":f"FORECAST-LEDGER-{i:03d}", "id_note":"本轮按原账本顺序生成的提取编号，不是补造预测", "prediction_date":x.get("date"), "instrument":x.get("code"), "original_prediction":x.get("claim"), "locked_price_or_value":x.get("target"), "prediction_horizon":{"due_date":x.get("due_date"), "layer":x.get("layer")}, "success_definition":{"operator":x.get("op"), "target":x.get("target"), "settle_by":x.get("settle_by")}, "validation_date":x.get("settled_at") or x.get("due_date"), "actual_result":x.get("actual"), "judgment":status, "evidence":x.get("why"), "counterfactual_portfolio_result":"原始账本未提供，不补造", "source":str(p)})
    daily = sorted((ROOT / "data" / "pdca").glob("review_daily_*.json"))
    weekly = sorted((ROOT / "data" / "pdca").glob("*week*.json")) + sorted((ROOT / "data" / "pdca").glob("*周*.json"))
    monthly = sorted((ROOT / "data" / "pdca").glob("*month*.json")) + sorted((ROOT / "data" / "pdca").glob("*月*.json"))
    return {"run_id":run_id, "generated_at":now, "record_count":len(rows), "records":rows, "review_entries":{"daily":[str(x) for x in daily[-5:]], "weekly":[str(x) for x in weekly[-5:]], "monthly":[str(x) for x in monthly[-5:]], "boundary":"没有原始记录的周期入口不补造"}, "source_file":meta(p)}


def build_external_and_further(run_id: str, now: str) -> dict[str, Any]:
    laolei = [
        {"path":r"G:\我的云端硬盘\老雷\26-08-5-6老雷录音文本.gdoc", "date":"2026-08-05", "actually_read":True, "url":"https://docs.google.com/document/d/1yDjC9Y_EtGvKKyDfzTplW9I47alqK1eh/edit", "validity":"观点随市场与财报变化，作为短期外部意见", "supports":"强调AI长期逻辑必须由盈利、利润率和自由现金流支持；反对只看主题。", "challenges":"高利率、拥挤和杠杆会放大高估值科技回撤；‘长期便宜、短期贵’是观点，不是官方事实。", "possible_impact":"可能改变NVDA、AVGO及AI同驱动持仓的风险判断。"},
        {"path":r"G:\我的云端硬盘\老雷\26-08-4老雷录音文本.gdoc", "date":"2026-08-04", "actually_read":True, "url":"https://docs.google.com/document/d/1UT5gBLRCT8OV-pq8fHH3OnZ2QrrYuX4h/edit", "validity":"短中期外部观点", "supports":"AI货币化要回到云收入、自由现金流和资本开支回报。", "challenges":"十年期利率和资金成本可能压低估值，市场会分化到真实现金流。", "possible_impact":"可能改变MSFT、VRT与高估值候选的相对比较。"},
        {"path":r"G:\我的云端硬盘\老雷\26-08-3老雷录音文本.gdoc", "date":"2026-08-03", "actually_read":True, "url":"https://docs.google.com/document/d/1O1bZrkE-9128SRCzD4WS_LUxdW0GzIC7/edit", "validity":"宏观观点需随汇率和利率更新", "supports":"强调美日韩台AI链和基本面分化。", "challenges":"日元套息逆转可能造成全球流动性冲击。", "possible_impact":"可能改变软银、日本持仓和AI广义暴露的压力测试。"},
    ]
    lake = [
        {"path":r"G:\我的云端硬盘\湖水资讯\26-08-15-1 Tech Daily sell-side opinions & headlines  .pdf", "date":"2026-08-14（PDF内页；文件名为08-15）", "actually_read":True, "validity":"卖方观点，不能替代公司正式披露", "supports":"SNDK长期合同、AI推理存储、NVDA基础设施融资等观点支持存储与AI基础设施需求。", "challenges":"利润率和合同价值为卖方估算，需与公司财报/合同逐条核。", "possible_impact":"可能改变SNDK、MU、NVDA候选优先级。"},
        {"path":r"G:\我的云端硬盘\湖水资讯\26-08-15-2 减仓窗口后移（reality checks, mid term, sox)  .pdf", "date":"2026-08-14（PDF内页）", "actually_read":True, "validity":"外部策略意见，不是系统动作", "supports":"记录杠杆水平与韩国交易热度，提示拥挤风险。", "challenges":"材料明确承认缺实时半导体/存储仓位数据，若据此定减仓比例会越权。", "possible_impact":"只影响总控对AI拥挤与时点的判断，不直接形成订单。"},
        {"path":r"G:\我的云端硬盘\湖水资讯\26-08-15-3韩国资金流周五 继续改善 .pdf", "date":"2026-08-14（PDF内页）", "actually_read":True, "validity":"单日资金流，需后续复核", "supports":"韩国外资净买入及Samsung/SK hynix买盘改善。", "challenges":"单日资金流不能证明存储周期长期趋势。", "possible_impact":"可能改变Samsung、MU和SNDK短期证据权重。"},
    ]
    further = [
        {"id":"OPEN-001", "unknown":"SBI各持仓究竟属于个人账户还是公司账户", "importance":"影响账户归属、税务和风险汇总", "possible_action_change":"可能改变跨账户合并和目标管理范围", "needed_evidence":"能显示账户名/账号归属的SBI实物", "next_check":"下次SBI截图或账户确认时"},
        {"id":"OPEN-002", "unknown":"富途28,873.30美元基金/其他净资产的具体构成", "importance":"总资产已闭合，但资产类别和流动性未闭合", "possible_action_change":"可能改变现金缓冲和风险资产比例判断", "needed_evidence":"OpenD可用基金/资产明细或券商资产页", "next_check":"下一次OpenD资产明细可读时"},
        {"id":"OPEN-003", "unknown":"SNDK券商价格、拆股与研究财务的统一口径", "importance":"账户风险可用市值，但不能据异常价格制定价值动作", "possible_action_change":"可能改变SNDK持有/替代判断", "needed_evidence":"券商公司行动记录、拆股调整和公司正式财务", "next_check":"数据校正完成日"},
        {"id":"OPEN-004", "unknown":"IBKR与bitFlyer逐项成本", "importance":"无法计算可靠盈亏和税务成本", "possible_action_change":"可能改变加密同驱动与亏损仓排序", "needed_evidence":"带成本字段的账户导出或截图", "next_check":"下次账户实物更新"},
        {"id":"OPEN-005", "unknown":"统一年初目标基准净值", "importance":"没有它就不能诚实计算+40%/+100%完成度", "possible_action_change":"可能改变目标贡献要求和替换力度", "needed_evidence":"锁定日期、锁定值和纳入账户范围", "next_check":"GPT总控目标管理裁定前"},
        {"id":"OPEN-006", "unknown":"部分美股候选最新正式财报直链与完整现金流", "importance":"机械财务字段不能代替正式申报", "possible_action_change":"可能把候选留在观察池或移出", "needed_evidence":"具体SEC申报或公司财报文件", "next_check":"下一次候选五关裁定前"},
    ]
    return {"run_id":run_id, "generated_at":now, "conflict_rule":"外部观点与官方数据冲突时并列展示，官方事实优先作为事实，观点保留为待验证假设", "laolei":laolei, "hushui":lake, "further_understanding":further}


def build_evidence(run_id: str, now: str, accounts: dict[str, Any], holdings: dict[str, Any], candidates: dict[str, Any], pdca: dict[str, Any], ext: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    items = []
    def add(eid: str, title: str, source: str, published: str | None, data_date: str | None, url: str, boundary: str) -> None:
        items.append({"evidence_id":eid,"title":title,"source":source,"published_at":published,"data_date":data_date,"fetched_at":now,"freshness":"截至本批次取得","url":url,"applicable_boundary":boundary})
    for i, f in enumerate(accounts["source_files"], 1):
        p = Path(f["path"])
        add(f"EV-ACC-{i:03d}", p.name, "账户原始/结构化实物", f["modified_at"], None, local_url(p), "仅支持对应账户和其数据日期，不拼成同日净值")
    strict = load(BASE_DIR / "01_EDINET严格口径逐只复核_20260815.json")["companies"]
    for code, x in strict.items():
        add(f"EV-EDINET-{code.replace('.','-')}", f"{x['name']} 有价证券报告书 {x['doc_id']}", "EDINET", x["published_at"], x["period_end"], f"https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?{x['doc_id']}", "只采用合并、当期、无分部维度的已选上下文")
    add("EV-SONY-20F-2026", "Sony FY2025 Form 20-F", "Sony官方", "2026-06-18", "2026-03-31", "https://www.sony.com/en/SonyInfo/IR/library/FY2025_20F_PDF.pdf", "区分持续经营与包含终止经营的总体损益")
    seen = set()
    for x in holdings["items"]:
        if x["evidence_url"] and x["evidence_url"] not in seen and not x["code"].startswith("JP."):
            seen.add(x["evidence_url"]); add(f"EV-HOLD-{x['code'].replace('.','-')}", f"{x['name']}正式材料", "公司/监管官方", None, x["latest_formal_financial_period"], x["evidence_url"], "只支持材料中明确披露的期间与字段")
    for x in candidates["items"]:
        ev = x["official_evidence"]
        if ev and ev["url"] not in seen and not x["code"].startswith("JP."):
            seen.add(ev["url"]); add(f"EV-CAND-{x['code'].replace('.','-')}", ev["title"], "公司/监管官方", ev.get("date"), ev.get("date"), ev["url"], "作为五关事实输入，不代表通过")
    scan = ROOT / "data" / "evidence" / "v7_scan_20260815" / "V7候选逐只研究卡_20260815.json"
    add("EV-SCAN-CARDS", "全市场扫描候选逐只研究卡", "项目扫描实物", None, "2026-08-15", local_url(scan), "价格和机械财务字段仅代表扫描时点")
    add("EV-PDCA-LEDGER", "预测账本", "项目PDCA日志", pdca["source_file"]["modified_at"], None, local_url(Path(pdca["source_file"]["path"])), "只提取原始记录，不补造反事实")
    for i, x in enumerate(ext["laolei"], 1): add(f"EV-LA0LEI-{i:02d}", Path(x["path"]).name, "老雷外部观点", x["date"], x["date"], x["url"], "外部观点，不替代官方事实")
    for i, x in enumerate(ext["hushui"], 1): add(f"EV-HUSHUI-{i:02d}", Path(x["path"]).name, "湖水资讯/卖方观点", x["date"], x["date"], local_url(Path(x["path"])), "外部观点与单日资金流，不直接形成动作")
    add("EV-REUTERS-RETAIL", "美国7月零售销售", "Reuters", "2026-08-14", "2026-07", "https://www.reuters.com/business/us-retail-sales-unexpectedly-fall-july-2026-08-14/", "宏观单月数据，不能单独确认衰退")
    add("EV-REUTERS-BOJ", "日本央行9月加息可能性报道", "Reuters", "2026-08-14", "2026-08-14", "https://www.reuters.com/world/asia-pacific/boj-eyeing-september-rate-hike-faster-pace-tightening-sources-say-2026-08-14/", "消息人士报道，不是日本央行正式决定")
    add("EV-REUTERS-NVDA-FIN", "NVIDIA相关AI基础设施融资安排", "Reuters", "2026-08-14", "2026-08-14", "https://www.reuters.com/legal/transactional/private-credit-roundup-nvidias-half-trillion-chips-financing-plus-others-2026-08-14/", "融资安排规模不等于NVIDIA已发生现金支出")
    traces = []
    for i, row in enumerate(accounts["account_rows"], 1): traces.append({"conclusion_id":f"CL-ACC-{i:03d}","conclusion":f"{row['account']} {row['code']}为{row['data_date']}最后已知账户事实","evidence_ids":[f"EV-ACC-{1 if row['account']=='富途' else 2 if row['account'].startswith('SBI') else 3 if row['account']=='IBKR' else 4:03d}"],"rule_id":"RULE-ACCOUNT-DATE-BOUNDARY","original_link":local_url(Path(row['source'])),"data_date":row['data_date'],"boundary":row['freshness']})
    ev_ids = {x["evidence_id"] for x in items}
    for x in holdings["items"]:
        eids = []
        if x["code"].startswith("JP.") and f"EV-EDINET-{x['code'].replace('.','-')}" in ev_ids: eids.append(f"EV-EDINET-{x['code'].replace('.','-')}")
        if f"EV-HOLD-{x['code'].replace('.','-')}" in ev_ids: eids.append(f"EV-HOLD-{x['code'].replace('.','-')}")
        traces.append({"conclusion_id":f"CL-HOLD-{x['code'].replace('.','-')}","conclusion":f"{x['name']}业务判断输入已整理，动作仍待GPT总控","evidence_ids":eids,"rule_id":"RULE-NO-CODEX-INVESTMENT-JUDGMENT","original_link":x["evidence_url"],"data_date":x["latest_formal_financial_period"],"boundary":x["action_boundary"]})
    for x in candidates["items"]:
        eid = f"EV-CAND-{x['code'].replace('.','-')}"
        eids = ["EV-SCAN-CARDS"] + ([eid] if eid in ev_ids else [])
        traces.append({"conclusion_id":f"CL-CAND-{x['code'].replace('.','-')}","conclusion":f"{x['name']}五关输入已整理但仍在观察池","evidence_ids":eids,"rule_id":"RULE-FIVE-GATE-BUSINESS-DECISION-RESERVED","original_link":x["official_evidence"]["url"] if x["official_evidence"] else None,"data_date":"2026-08-15","boundary":x["action_boundary"]})
    traces.append({"conclusion_id":"CL-PDCA-LEDGER","conclusion":f"从原账本提取{pdca['record_count']}条预测记录","evidence_ids":["EV-PDCA-LEDGER"],"rule_id":"RULE-NO-BACKFILL-PDCA","original_link":local_url(Path(pdca["source_file"]["path"])),"data_date":None,"boundary":"无原始记录不补造"})
    return ({"run_id":run_id,"generated_at":now,"evidence_count":len(items),"items":items}, {"run_id":run_id,"generated_at":now,"trace_count":len(traces),"items":traces})


def batch_identity() -> dict[str, Any]:
    def files(d: Path) -> dict[str, dict[str, Any]]:
        return {p.name:meta(p) for p in d.iterdir() if p.is_file()} if d.exists() else {}
    base, mid = files(BASE_DIR), files(MID_DIR)
    common = sorted(set(base) & set(mid))
    changed = [n for n in common if base[n]["sha256"] != mid[n]["sha256"]]
    return {"baseline":{"run_id":BASE_RUN,"path":str(BASE_DIR),"exists":BASE_DIR.exists(),"identity_recommendation":"ONLY_BASELINE_FOR_V0.4_INPUT"}, "intermediate":{"run_id":MID_RUN,"path":str(MID_DIR),"exists":MID_DIR.exists(),"identity_recommendation":"INTERMEDIATE_FAILED_NOT_FOR_REVIEW"}, "comparison":{"baseline_file_count":len(base),"intermediate_file_count":len(mid),"common_file_count":len(common),"changed_common_files":changed,"baseline_only":sorted(set(base)-set(mid)),"intermediate_only":sorted(set(mid)-set(base)),"known_difference":"015232存在伊藤忠和软银资产负债勾稽误报；015526修正非控股权益逻辑、可读纠错报告和视觉问题。"}, "handling_recommendation":"不移动、不删除、不覆盖；015232明确登记为中间失败批次，015526继续作为唯一基准候选。"}


def render_html(path: Path, run_id: str, now: str, accounts: dict[str, Any], holdings: dict[str, Any], candidates: dict[str, Any], pdca: dict[str, Any], ext: dict[str, Any], gaps: dict[str, Any], batches: dict[str, Any]) -> None:
    acc_rows = "".join(f"<tr><td>{esc(x['account'])}</td><td>{esc(x['code'])}<br>{esc(x['instrument'])}</td><td>{esc(x['quantity'])}</td><td>{money(x['cost'],x['currency'])}</td><td>{money(x['latest_price'],x['currency'])}</td><td>{money(x['market_value'],x['currency'])}</td><td>{esc(x['data_date'])}</td><td>{esc(x['freshness'])}</td></tr>" for x in accounts["account_rows"])
    hold_rows = "".join(f"<tr><td>{esc(x['code'])}<br>{esc(x['name'])}</td><td>{esc(x['business'])}<br><b>赚钱方式：</b>{esc(x['how_it_makes_money'])}</td><td>{esc(x['latest_formal_financial_period'])}<br>收入 {money(x['revenue'])}<br>营业利润 {money(x['operating_profit'])}<br>净利润 {money(x['net_income_attributable_or_net_income'])}<br>经营现金流 {money(x['operating_cash_flow'])}</td><td>{esc(x['moat'])}<br><b>竞争：</b>{esc(x['main_competitors'])}</td><td>{esc(x['maximum_reverse_risk'])}<br><b>推翻：</b>{esc(x['invalidation_condition'])}</td><td>{esc('；'.join(x['missing_fields']))}</td></tr>" for x in holdings["items"])
    cand_rows = "".join(f"<tr><td>{esc(x['code'])}<br>{esc(x['name'])}</td><td>{esc(x['theme'])}</td><td>{esc(x['gates'][1]['input'])}</td><td>{esc(x['gates'][2]['input'])}</td><td>{esc(x['gates'][3]['input'])}</td><td>{esc(x['gates'][4]['input'])}</td><td>{esc(x['possible_replacement_comparison'])}</td><td>{esc(x['observation_pool_reason'])}</td></tr>" for x in candidates["items"])
    gap_rows = "".join(f"<tr><td>{esc(x['id'])}</td><td>{esc(x['description'])}</td><td>{esc(x['impact'])}</td><td>{esc(x['next_evidence'])}</td></tr>" for x in gaps["items"])
    html_text = f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><title>V7 v0.4业务判断输入包</title><style>
body{{font-family:'Microsoft YaHei',Arial,sans-serif;color:#1f2937;margin:0;background:#f4f6f8;font-size:14px;line-height:1.65}}main{{max-width:1500px;margin:auto;background:white;padding:28px 34px}}h1{{font-size:28px;margin:0 0 8px}}h2{{font-size:20px;border-bottom:2px solid #0f766e;padding-bottom:6px;margin-top:30px}}.banner{{background:#e6f4f1;border-left:5px solid #0f766e;padding:12px 16px;margin:16px 0}}.warn{{background:#fff7ed;border-left:5px solid #ea580c;padding:12px 16px}}table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:13px}}th,td{{border:1px solid #cbd5e1;padding:7px;vertical-align:top;text-align:left}}th{{background:#eef2f7}}.scroll{{overflow-x:auto}}code{{background:#eef2f7;padding:2px 4px}}a{{color:#075985}}small{{color:#475569}}</style></head><body><main>
<h1>V7完整产品v0.4业务判断输入与证据闭合</h1><div class='banner'><b>批次：</b>{esc(run_id)}<br><b>生成：</b>{esc(now)}<br><b>性质：</b>供GPT总控完成投资判断的事实输入包，不是v0.4产品，不包含Codex买卖、估值取舍或仓位决定。</div>
<div class='warn'>基准候选 <code>{BASE_RUN}</code> 和中间批次 <code>{MID_RUN}</code> 均未修改、未移动、未覆盖。本轮未Release、未覆盖正式日报、未调用交易功能、未生成订单。</div>
<h2>一、账户事实</h2><p>富途已在生产日通过OpenD只读刷新。SBI、IBKR和bitFlyer保留各自最后已知日期；不同日期账户不拼成同日净值。</p><p>富途总资产 {money(accounts['futu_reconciliation']['total_assets_usd'],'USD')}，证券市值 {money(accounts['futu_reconciliation']['securities_market_value_usd'],'USD')}，现金 {money(accounts['futu_reconciliation']['cash_usd'],'USD')}，基金/其他净资产合计 {money(accounts['futu_reconciliation']['other_net_assets_aggregate_usd'],'USD')}。金额已闭合，但最后一项具体构成尚未闭合。</p><div class='scroll'><table><thead><tr><th>账户</th><th>标的</th><th>数量</th><th>成本</th><th>最新价</th><th>市值</th><th>数据日</th><th>边界</th></tr></thead><tbody>{acc_rows}</tbody></table></div>
<h2>二、24类持仓判断输入</h2><p>以下只整理事实、财务、护城河、风险和待裁问题。没有可靠估值时明确保持缺失，不形成价格动作。</p><div class='scroll'><table><thead><tr><th>持仓</th><th>业务与赚钱方式</th><th>最新正式财务</th><th>护城河与竞争</th><th>反向风险与失效</th><th>仍缺</th></tr></thead><tbody>{hold_rows}</tbody></table></div>
<h2>三、21只候选五关输入</h2><p>所有标的仍在研究观察池。表内的扫描指标只是输入，正式板块激活、五关通过、候选取舍和替代关系均由GPT总控决定。</p><div class='scroll'><table><thead><tr><th>候选</th><th>第一关</th><th>第二关</th><th>第三关</th><th>第四关</th><th>第五关</th><th>可能比较对象</th><th>观察池原因</th></tr></thead><tbody>{cand_rows}</tbody></table></div>
<h2>四、PDCA实物</h2><p>从原始预测账本逐条提取 {pdca['record_count']} 条。没有锁定价格、反事实组合结果或周/月入口的记录保持缺失，不补造。明细见机器附件。</p>
<h2>五、老雷、湖水与进一步了解</h2><p>实际读取老雷材料 {len(ext['laolei'])} 份、湖水资讯PDF {len(ext['hushui'])} 份。它们均作为外部观点；与官方数据冲突时并列展示，官方材料作为事实，观点保留为待验证假设。</p><ul>{''.join(f"<li><b>{esc(Path(x['path']).name)}</b>：支持 {esc(x['supports'])}；反向 {esc(x['challenges'])}</li>" for x in ext['laolei']+ext['hushui'])}</ul>
<h2>六、缺失与冲突</h2><table><thead><tr><th>编号</th><th>问题</th><th>影响</th><th>所需证据</th></tr></thead><tbody>{gap_rows}</tbody></table>
<h2>七、批次身份</h2><p><code>{MID_RUN}</code>建议登记为 <b>INTERMEDIATE_FAILED_NOT_FOR_REVIEW</b>；<code>{BASE_RUN}</code>继续作为本轮唯一基准。共同文件中有 {len(batches['comparison']['changed_common_files'])} 个哈希不同，具体清单见批次报告。本轮不移动、不删除任何批次。</p>
<h2>八、交付边界</h2><ul><li>未生成v0.4完整产品。</li><li>未自行制定价值区间、买卖区间或仓位。</li><li>未登记Release，未覆盖<code>00_今日日报.pdf</code>。</li><li>未调用交易、解锁、下单、改单或撤单接口。</li><li>账户、持仓、候选、PDCA、外部观点与证据链的完整机器字段见同目录JSON附件。</li></ul>
</main></body></html>"""
    path.write_text(html_text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id")
    args = ap.parse_args()
    dt = datetime.now(JST)
    run_id = args.run_id or f"V7-V04-BUSINESS-INPUT-{dt:%Y%m%d-%H%M%S}-JST"
    now = dt.isoformat(timespec="seconds")
    out = ROOT / "output" / "decision_inputs" / "2026-08-16" / run_id
    out.mkdir(parents=True, exist_ok=False)
    accounts = build_accounts(run_id, now)
    holdings = build_holdings(run_id, now, accounts)
    candidates = build_candidates(run_id, now)
    pdca = build_pdca(run_id, now)
    ext = build_external_and_further(run_id, now)
    evidence, traces = build_evidence(run_id, now, accounts, holdings, candidates, pdca, ext)
    batches = batch_identity()
    gaps = {"run_id":run_id,"generated_at":now,"items":[
        {"id":"GAP-ACCOUNT-001","description":"SBI个人与公司账户归属无法由现有截图区分","impact":"账户归属、税务和风险汇总不完整","next_evidence":"带账户名/账号属性的SBI实物"},
        {"id":"GAP-ACCOUNT-002","description":"富途28,873.30美元基金/其他净资产只有合计","impact":"总额闭合，具体资产类别和流动性仍未知","next_evidence":"OpenD基金或其他资产明细"},
        {"id":"GAP-ACCOUNT-003","description":"SBI、IBKR、bitFlyer与富途数据日不同","impact":"不能形成同日全组合净值和精确权重","next_evidence":"需要时取得同日账户实物"},
        {"id":"GAP-SNDK-001","description":"SNDK券商价格、拆股与研究口径未统一","impact":"可计账户市值风险，不能据此形成价值或买卖动作","next_evidence":"公司行动与券商调整记录"},
        {"id":"GAP-FIN-001","description":"部分美股正式材料未提供完整收入、利润、现金流、现金和债务字段","impact":"对应持仓/候选只能作为事实不完整的判断输入","next_evidence":"具体SEC申报或公司财报附件"},
        {"id":"GAP-PDCA-001","description":"原预测账本未记录反事实组合结果，周/月独立入口不完整","impact":"不能补造反事实收益或完整周期复盘","next_evidence":"未来按锁定规则建立真实记录"},
        {"id":"CLOSED-SONY-001","description":"索尼持续经营与终止经营口径已分开","impact":"纠正把总体会计亏损冒充持续经营利润的风险","next_evidence":"下次正式财报继续沿用同一口径"},
        {"id":"BATCH-IDENTITY-001","description":"015232与015526不能同时作为待送验候选","impact":"版本身份混乱","next_evidence":"按报告建议登记015232为中间失败批次；本轮不移动文件"},
    ]}
    execution = {"run_id":run_id,"generated_at":now,"task":"V7完整产品v0.4业务判断输入与证据闭合","status":"COMPLETED_WITH_DISCLOSED_GAPS","operations":["读取Current基准候选和机器附件","OpenD只读刷新富途账户","整理四账户不同日期事实","整理24类持仓业务判断输入","整理21只候选五关输入","提取PDCA原始记录","读取老雷与湖水材料","建立精确证据和追踪关系","核对015232与015526批次身份"],"prohibitions_verified":{"base_candidate_modified":False,"v04_product_generated":False,"investment_judgment_by_codex":False,"value_or_buy_zone_decided":False,"release_registered":False,"daily_report_overwritten":False,"trading_api_called":False,"order_generated":False},"batch_identity":batches,"base_candidate_hashes":{"html":"DB48379493520CA1D2FE914807BCE0883A58BF496DD7664CAF44427BFA555FB2","pdf":"EF9E8854F0F61348FC3086A26CC5CBCB79485BA8D109759CC1D715819EC33E8E"}}
    execution["daily_report_proof"] = meta(ROOT / "00_请先看这里" / "00_今日日报.pdf")
    named = [
        ("01_全账户资产明细_20260816.json",accounts),("02_24类持仓业务判断输入_20260816.json",holdings),("03_21只候选五关输入_20260816.json",candidates),("04_PDCA逐条记录_20260816.json",pdca),("05_老雷湖水与仍需进一步了解_20260816.json",ext),("06_精确证据注册表_20260816.json",evidence),("07_结论证据规则追踪表_20260816.json",traces),("08_缺失与冲突清单_20260816.json",gaps),("09_执行日志及批次身份核对报告_20260816.json",execution),
    ]
    for name, value in named: dump(out / name, value)
    render_html(out / "V7_v0.4业务判断输入包_20260816.html", run_id, now, accounts, holdings, candidates, pdca, ext, gaps, batches)
    artifacts = [meta(p) for p in sorted(out.iterdir()) if p.is_file()]
    dump(out / "10_全部实物SHA256清单_20260816.json", {"run_id":run_id,"generated_at":datetime.now(JST).isoformat(timespec="seconds"),"artifact_count_excluding_this_manifest":len(artifacts),"self_reference_note":"清单自身无法稳定包含自身哈希；其余全部交付实物均已登记", "artifacts":artifacts})
    print(json.dumps({"run_id":run_id,"output_dir":str(out),"files":len(list(out.iterdir()))},ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
