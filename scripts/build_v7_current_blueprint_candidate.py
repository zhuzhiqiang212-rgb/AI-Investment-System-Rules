#!/usr/bin/env python3
"""Build the 2026-08-15 V7 Current-blueprint full-product candidate.

The script only consumes existing evidence and GPT-control judgments. It does not
call broker APIs, modify governance, register a Release, or touch the daily PDF.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
DATA_DATE = "2026-08-15"
OLD_V03 = ROOT / "output/candidates/2026-08-15/V7-SCAN-20260815-103023-JST/v0.3"
EVIDENCE = ROOT / "data/evidence/v7_20260815"
SCAN = ROOT / "data/evidence/v7_scan_20260815"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_html(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def stamp(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "size": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, JST).isoformat(timespec="seconds"),
        "sha256": sha256(path),
    }


def e(value: Any) -> str:
    return html.escape(str(value if value is not None else "未取得"), quote=True)


def fmt_num(value: Any, digits: int = 2) -> str:
    if value is None:
        return "未取得"
    return f"{float(value):,.{digits}f}"


def table(headers: list[str], rows: list[list[Any]], cls: str = "") -> str:
    th = "".join(f"<th>{e(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{v if isinstance(v, Raw) else e(v)}</td>" for v in row) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table class="{e(cls)}"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


class Raw(str):
    pass


PROFILE: dict[str, dict[str, str]] = {
    "US.TSM": {"business":"全球领先晶圆代工，生产先进与成熟制程芯片。","money":"按晶圆和制造服务收费，先进制程贡献主要增量。","revenue":"高性能计算、智能手机、汽车与物联网；利润依赖先进节点利用率。","moat":"先进制程、良率、资本规模与客户信任。","competitors":"三星电子、Intel Foundry。","method":"市盈率、自由现金流和资本开支周期并看。","thesis":"AI算力需求支撑先进制程，但地缘和资本强度不能忽略。","short":"跟踪AI链订单和地缘溢价，不把单日价格当趋势。","catalyst":"先进制程放量、AI客户订单与毛利率兑现。","reverse":"高估值、地缘风险和客户自研会压低回报。","invalidate":"先进制程利用率或毛利率持续低于指引。","timing":"下一次月度营收和季度财报。"},
    "US.SPCX": {"business":"Space Exploration Technologies Corp. Class A普通股，业务覆盖发射、卫星互联网与航天基础设施。","money":"发射服务、Starlink订阅及相关政府和商业合同。","revenue":"订阅和发射合同；细分利润仍需正式披露补强。","moat":"可复用火箭、发射频率、卫星网络和工程规模。","competitors":"ULA、Blue Origin、卫星通信运营商。","method":"分部收入、现金流与可比公司；当前资料不足以给出可靠区间。","thesis":"证券身份已核实，但目标贡献数值情景尚未获批准。","short":"仅做身份和流动性跟踪，不新增。","catalyst":"Starlink增长、发射频率和新业务进展。","reverse":"资本开支、监管、事故与披露不足。","invalidate":"官方披露无法支持增长或流动性明显恶化。","timing":"下一份正式财务或监管披露。"},
    "US.SNDK": {"business":"提供NAND闪存、SSD及存储产品。","money":"向数据中心、终端和渠道销售存储器与解决方案。","revenue":"NAND价格、出货位元与企业级SSD；利润高度周期化。","moat":"存储技术、供应链、客户验证与规模。","competitors":"Micron、Samsung、SK hynix、Kioxia、WDC。","method":"周期中段盈利、自由现金流和每位元经济性；当前价格/拆股/财务口径待校正。","thesis":"券商市值可进入账户风险，未校正研究假设不得进入目标贡献。","short":"数据校正前持有但不加仓。","catalyst":"AI存储合同、NAND价格与企业SSD需求。","reverse":"周期见顶、供给扩张及数据口径异常。","invalidate":"校正后官方数据不支持当前盈利或价格逻辑。","timing":"数据校正完成日及下一次正式财报。"},
    "US.NVDA": {"business":"设计GPU、加速计算平台、网络与AI软件。","money":"销售数据中心芯片、系统和软件生态。","revenue":"数据中心为核心，游戏和专业可视化补充；利润依赖高端芯片和软件溢价。","moat":"CUDA生态、软硬件协同、开发者网络和产品迭代。","competitors":"AMD、定制ASIC、云厂商自研芯片。","method":"远期盈利、自由现金流与增长持续期。","thesis":"核心持有；不因比例机械减仓，同驱动压力测试前不追高。","short":"订单与官方指引未转弱前主线仍在，但高集中放大波动。","catalyst":"Blackwell/Rubin放量、网络和系统收入。","reverse":"融资循环、出口限制和客户自研加速。","invalidate":"数据中心指引下修或毛利率持续恶化。","timing":"下一次财报与主要云厂商资本开支更新。"},
    "US.MSTR": {"business":"Strategy，以资本结构放大的比特币敞口为主。","money":"软件收入叠加BTC持有与融资操作，普通股对BTC高度敏感。","revenue":"软件收入有限，权益价值主要受BTC和融资条件驱动。","moat":"资本市场执行能力，不等于经营护城河。","competitors":"BTC现货、ETF及其他数字资产载体。","method":"每股BTC净敞口、债务和优先证券义务、相对BTC溢价。","thesis":"第一条件减持/替换对象；停止补仓摊低成本。","short":"BTC和融资条件主导，资本结构放大下行。","catalyst":"BTC上涨及融资继续支持每股BTC敞口。","reverse":"BTC下跌、溢价收缩和资本成本上升。","invalidate":"BTC逻辑转弱且更优替代机会形成。","timing":"BTC趋势、融资公告和季度资产披露。"},
    "US.MSFT": {"business":"云计算、企业软件、生产力工具和AI平台。","money":"订阅、云资源、软件许可、广告与游戏。","revenue":"Azure、Microsoft 365等经常性收入；利润由云与软件规模驱动。","moat":"企业分发、云规模、生态与转换成本。","competitors":"AWS、Google Cloud、Oracle及开源软件。","method":"自由现金流、云增长、资本开支回报与远期市盈率。","thesis":"核心持有；收益质量高，但需比较对+40%目标的贡献。","short":"高质量但资本开支和估值会影响短期弹性。","catalyst":"Azure/AI收入与利润率兑现。","reverse":"AI资本开支回报慢、竞争和监管。","invalidate":"云增长与自由现金流同时持续低于预期。","timing":"下一次财报及云业务指引。"},
    "US.CRCL": {"business":"Circle，发行USDC并提供稳定币支付基础设施。","money":"储备资产利息、支付和基础设施服务。","revenue":"储备收益高度受利率和USDC规模影响。","moat":"合规许可、分发网络和机构集成。","competitors":"Tether、银行代币及其他稳定币。","method":"USDC规模、储备收益、分销成本和监管许可。","thesis":"加密三者第二保留；小仓观察，暂不加仓。","short":"许可进展支持逻辑，但利率和份额敏感。","catalyst":"USDC扩张与国家信托银行落地。","reverse":"降息、份额流失和分销成本上升。","invalidate":"USDC份额或关键许可明显受损。","timing":"月度流通数据、利率变化和季度财报。"},
    "US.COIN": {"business":"加密资产交易、托管、稳定币和衍生品平台。","money":"交易费、订阅服务、稳定币分成和托管。","revenue":"交易与非交易收入较MSTR更多元。","moat":"合规牌照、流动性、托管与品牌。","competitors":"Binance、Kraken、Robinhood及链上交易平台。","method":"周期中段EBITDA、交易量和非交易收入占比。","thesis":"加密三者中优先保留；不追高加仓。","short":"仍受加密周期影响，但收入来源相对多元。","catalyst":"交易量、稳定币、衍生品与订阅增长。","reverse":"币价和交易活跃度下滑、监管冲击。","invalidate":"交易与非交易收入同时恶化且EBITDA持续转负。","timing":"月度交易量与下一次财报。"},
    "US.AVGO": {"business":"半导体、定制AI芯片、网络芯片和基础设施软件。","money":"芯片销售、长期软件订阅与维护。","revenue":"AI半导体增速高，软件提供现金流；客户集中需监控。","moat":"定制芯片、网络技术、客户协同和软件转换成本。","competitors":"NVDA、Marvell、内部ASIC团队。","method":"分部增长、自由现金流和远期市盈率。","thesis":"继续持有；增长成立但估值较高，不追价。","short":"当日大跌显示预期敏感，需看订单而非价格单点。","catalyst":"AI定制芯片和网络收入。","reverse":"客户集中、估值和资本开支放缓。","invalidate":"AI收入指引连续下修或大客户流失。","timing":"下一次财报和客户资本开支更新。"},
    "JP.9984": {"business":"软银集团，以投资控股、Arm及AI资产净值为核心。","money":"资产升值、分红、处置和融资。","revenue":"合并业务收入与投资收益并存；股东回报受资产净值折价影响。","moat":"资本配置网络与Arm等稀缺资产。","competitors":"大型科技投资控股和私募资本。","method":"NAV资产净值、折价、杠杆和核心资产情景。","thesis":"继续持有；广义AI代理敞口，暂停新增。","short":"AI资产与日元/利率共同驱动，波动高。","catalyst":"Arm及AI资产兑现、NAV折价收敛。","reverse":"杠杆、资产集中和折价扩大。","invalidate":"核心AI资产持续下跌且融资成本明显上升。","timing":"季度NAV披露和主要被投企业财报。"},
    "JP.7974": {"business":"游戏硬件、软件及马力欧等IP运营。","money":"硬件、第一方软件、数字内容和授权。","revenue":"平台周期与高毛利软件销量决定利润。","moat":"自有IP、硬件软件一体化和用户生态。","competitors":"Sony、Microsoft、移动游戏平台。","method":"平台周期归一化利润、净现金与IP价值。","thesis":"继续持有；跟踪硬件周期、软件销量及利润兑现。","short":"新品周期有上行也有预期透支风险。","catalyst":"硬件装机、第一方软件与电影/授权。","reverse":"硬件热度透支、软件附着率不足。","invalidate":"装机、软件销量和利润连续低于指引。","timing":"月度销售数据和下一次财报。"},
    "JP.4568": {"business":"创新制药，核心为肿瘤等药物管线。","money":"药品销售、合作里程碑和授权收入。","revenue":"核心产品商业化与管线成功决定利润。","moat":"研发平台、临床数据、专利和商业化能力。","competitors":"全球大型药企与同靶点生物科技公司。","method":"风险调整管线净现值、现有产品现金流。","thesis":"继续持有、暂停加仓；复核管线兑现。","short":"临床和监管事件带来非线性波动。","catalyst":"临床、审批和商业化里程碑。","reverse":"试验失败、审批延迟或安全性问题。","invalidate":"关键管线失败或销售持续低于预期。","timing":"下一次临床/监管公告和财报。"},
    "JP.4063": {"business":"信越化学，半导体硅片、PVC和功能材料。","money":"销售材料，利润来自规模、成本和高规格产品。","revenue":"半导体材料与化学品周期共同驱动。","moat":"工艺、规模、客户认证和成本优势。","competitors":"SUMCO、环球晶及全球化工企业。","method":"周期中段利润、自由现金流与分部估值。","thesis":"截至SBI截图日的最后已知持仓；本轮未获新动作裁定。","short":"观察半导体材料需求和化工周期。","catalyst":"硅片需求复苏与高端材料放量。","reverse":"晶圆库存、化工价格与日元变化。","invalidate":"订单和利润率持续恶化。","timing":"下一次财报和行业库存更新。"},
    "JP.6758": {"business":"Sony，游戏、音乐、影像传感器和娱乐内容。","money":"平台、内容、硬件和传感器销售。","revenue":"游戏网络、音乐影视与传感器多元贡献。","moat":"内容IP、平台、传感器技术和品牌。","competitors":"Nintendo、Microsoft、Samsung及内容平台。","method":"分部加总、自由现金流和周期归一化。","thesis":"截至SBI截图日的最后已知持仓；进入风险观察。","short":"多元业务可分散，但游戏与传感器周期仍敏感。","catalyst":"游戏内容、订阅和传感器需求。","reverse":"硬件周期、内容成本和智能手机需求。","invalidate":"核心分部利润同时下修。","timing":"下一次分部财报。"},
    "JP.6857": {"business":"Advantest，半导体自动测试设备。","money":"销售测试系统、服务和耗材。","revenue":"高端芯片测试需求与设备周期驱动。","moat":"测试技术、客户认证和安装基础。","competitors":"Teradyne及专业测试设备商。","method":"订单、周期中段利润和远期市盈率。","thesis":"截至SBI截图日的最后已知持仓；高AI同驱动风险需合并观察。","short":"AI测试需求强，但估值和周期回撤大。","catalyst":"先进芯片测试复杂度和订单。","reverse":"客户资本开支放缓与估值压缩。","invalidate":"订单/积压和利润率持续下修。","timing":"下一次订单与财报。"},
    "JP.6954": {"business":"FANUC，工业机器人、数控系统和工厂自动化。","money":"设备销售、维护和备件。","revenue":"全球制造业资本开支和自动化渗透率。","moat":"可靠性、安装基础、控制技术与服务网络。","competitors":"Yaskawa、ABB、Siemens等。","method":"周期中段利润、净现金和订单。","thesis":"截至SBI截图日的最后已知持仓；本轮未获新动作裁定。","short":"受制造业周期和中国需求影响。","catalyst":"自动化订单复苏和高端制造投资。","reverse":"全球制造业放缓、价格竞争。","invalidate":"订单和利润率连续恶化。","timing":"季度订单与财报。"},
    "JP.7203": {"business":"Toyota，汽车、金融服务与移动出行。","money":"整车、零部件、金融和售后。","revenue":"混动和全球规模支撑现金流，汇率影响明显。","moat":"制造体系、品牌、渠道与规模。","competitors":"全球车企及中国新能源车企。","method":"周期中段利润、资产负债与市净率。","thesis":"截至SBI截图日的最后已知持仓；观察电动化竞争。","short":"估值提供支撑，但关税、汇率和中国竞争是变量。","catalyst":"混动需求、成本改善和新车型。","reverse":"电动化落后、关税与日元升值。","invalidate":"销量、利润率和竞争地位持续恶化。","timing":"月度销量和下一次财报。"},
    "JP.8001": {"business":"Itochu，综合商社，覆盖消费、食品、纺织、机械和资源。","money":"贸易利润、投资收益和分红。","revenue":"非资源业务占比较高，资源价格仍有影响。","moat":"网络、资本配置和长期合作关系。","competitors":"三菱商事、三井物产等。","method":"分部加总、现金流和NAV折价。","thesis":"截至SBI截图日的最后已知持仓；作为异质收益来源观察。","short":"相对AI低相关，但日元和商品周期影响回报。","catalyst":"资本回报、并购和非资源增长。","reverse":"商品周期、投资减值和日元升值。","invalidate":"现金流和资本回报持续恶化。","timing":"下一次财报与资本政策。"},
    "JP.8766": {"business":"Tokio Marine，财产险、寿险与海外保险。","money":"保费、承保利润和投资收益。","revenue":"承保与投资两端驱动，巨灾损失影响波动。","moat":"品牌、定价数据、渠道和全球业务。","competitors":"MS&AD、Sompo及全球保险集团。","method":"市净率、ROE、综合成本率和资本回报。","thesis":"SBI截图仍显示1000股；历史是否卖出不从差额推断。","short":"潜在加息利好投资收益，但巨灾和汇率是反向风险。","catalyst":"利率、承保改善和回购。","reverse":"巨灾损失、准备金和资本市场回撤。","invalidate":"综合成本率和资本回报持续恶化。","timing":"季度财报、巨灾披露和资本政策。"},
    "US.META": {"business":"社交平台、数字广告与AI基础设施。","money":"广告为主，辅以设备和服务。","revenue":"广告量价和参与度驱动，AI资本开支影响自由现金流。","moat":"用户网络、广告数据和分发。","competitors":"Google、TikTok、Amazon广告。","method":"广告增长、自由现金流和资本开支回报。","thesis":"IBKR最后已知持仓；不进入目标缺口，但进入风险管理。","short":"广告现金流强，AI开支和监管是风险。","catalyst":"广告效率与AI推荐改善。","reverse":"监管、竞争与资本开支失控。","invalidate":"广告增长和自由现金流同时持续恶化。","timing":"下一次财报与监管进展。"},
    "US.IBKR": {"business":"Interactive Brokers，电子券商和交易基础设施。","money":"净利息、佣金和账户服务。","revenue":"客户资产、交易量和利率共同驱动。","moat":"低成本、全球市场接入和技术平台。","competitors":"Schwab、Robinhood及全球券商。","method":"客户资产增长、净利息和市盈率。","thesis":"IBKR最后已知小仓；仅风险观察。","short":"利率与交易活跃度混合影响。","catalyst":"账户增长和国际扩张。","reverse":"降息、交易低迷和系统风险。","invalidate":"客户资产和盈利持续转弱。","timing":"月度运营数据与财报。"},
    "KRX.005930": {"business":"Samsung Electronics，存储、晶圆制造、手机和消费电子。","money":"芯片、手机、显示与电子产品销售。","revenue":"存储周期与手机业务是主要波动源。","moat":"规模、垂直整合、制造和品牌。","competitors":"SK hynix、Micron、TSM、Apple等。","method":"分部估值、存储周期和净现金。","thesis":"IBKR最后已知15股；进入存储同驱动风险。","short":"存储改善支持，但先进制程竞争和周期仍是风险。","catalyst":"HBM/存储价格与良率改善。","reverse":"技术落后、供给扩张和手机疲弱。","invalidate":"存储利润和先进制程进展持续落后。","timing":"季度财报与存储价格。"},
    "BTC": {"business":"比特币是去中心化数字资产，不是经营公司。","money":"无经营收入；回报来自价格变化。","revenue":"不适用；需用链上、流动性和宏观条件评估。","moat":"网络效应、稀缺规则和全球流动性。","competitors":"法币、黄金、其他加密资产。","method":"不使用公司估值；观察流动性、采用度和周期。","thesis":"bitFlyer最后已知持仓；仅风险管理，不作为当日确认。","short":"高波动且与MSTR/COIN/CRCL形成同驱动。","catalyst":"流动性、机构采用和监管清晰度。","reverse":"监管、流动性收紧和杠杆清算。","invalidate":"采用度和流动性结构持续恶化。","timing":"每日风险监控、月度账户截图。"},
    "ETH": {"business":"以太坊是智能合约网络原生资产，不是经营公司。","money":"无公司收入；持有人回报来自价格和网络使用。","revenue":"链上费用、质押与应用活跃度是网络指标。","moat":"开发者生态、应用和网络效应。","competitors":"Solana等智能合约网络。","method":"网络活跃、费用、质押和流动性，不套用市盈率。","thesis":"bitFlyer最后已知持仓；仅风险管理。","short":"高波动，受网络使用、监管和加密周期影响。","catalyst":"应用增长、扩容和机构采用。","reverse":"竞争链分流、监管和技术风险。","invalidate":"开发者/用户活跃和费用结构持续恶化。","timing":"每日风险监控、月度账户截图。"},
}


GENERIC_CANDIDATE_MOAT = {
    "存储": "制造规模、技术迭代和客户认证",
    "AI": "技术、客户验证、生态或基础设施交付能力",
    "银行": "存款、客户关系、资本和牌照",
    "保险": "定价数据、渠道和资本",
    "能源": "资源、基础设施和成本曲线",
}


def profile_for(code: str, name: str) -> dict[str, str]:
    if code in PROFILE:
        return PROFILE[code]
    return {
        "business": f"{name}的业务事实以本轮候选研究卡和正式披露为准。",
        "money": "收入来源需按最新正式财报分部核对。",
        "revenue": "现有机械研究卡提供财务字段，但不能代替分部利润分析。",
        "moat": "护城河需要在第五关深度研究中确认。",
        "competitors": "竞争对手需要按业务分部补齐。",
        "method": "使用正式财报、现金流、可比估值与周期位置交叉判断。",
        "thesis": "保留在研究范围，不代表买入或替换结论。",
        "short": "等待业务主脑结合当日证据裁定。",
        "catalyst": "见候选研究卡中的公告和行业驱动。",
        "reverse": "数据不完整、估值和行业驱动反转。",
        "invalidate": "正式披露不能支持研究假设。",
        "timing": "下一次正式财报或关键催化剂。",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id")
    args = parser.parse_args()
    now = datetime.now(JST)
    run_id = args.run_id or f"V7-BLUEPRINT-20260815-{now:%H%M%S}-JST"
    out = ROOT / "output/candidates/2026-08-15" / run_id
    out.mkdir(parents=True, exist_ok=False)

    daily = ROOT / "00_请先看这里/00_今日日报.pdf"
    daily_before = stamp(daily)

    futu = read_json(ROOT / "data/accounts/futu_positions_20260815.json")
    sbi = read_json(ROOT / "data/accounts/per_account_SBI_20260811.json")
    ibkr = read_json(ROOT / "data/accounts/per_account_IBKR_20260811.json")
    bitflyer = read_json(ROOT / "data/accounts/bitflyer_account_20260811.json")
    market = read_json(EVIDENCE / "V7当日市场结构化行情_20260815.json")
    seven_input = read_json(EVIDENCE / "V7七层业务判断输入包_20260815.json")
    cards_doc = read_json(SCAN / "V7候选逐只研究卡_20260815.json")
    final_doc = read_json(SCAN / "V7最终研究候选名单_20260815.json")
    funnel = read_json(SCAN / "V7机会漏斗_20260815.json")
    edinet = read_json(SCAN / "V7_EDINET接续测试及覆盖结果_20260815.json")
    judgments_doc = read_json(OLD_V03 / "GPT总控判断落地矩阵_20260815_v0.3.json")
    account_close = read_json(OLD_V03 / "富途账户金额与盈亏口径闭合_20260815_v0.3.json")
    target_old = read_json(OLD_V03 / "年度目标贡献与进度边界_20260815_v0.3.json")
    news_old = read_json(OLD_V03 / "重大新闻证据清单_20260815_v0.3.json")
    ai_stress = read_json(OLD_V03 / "AI同一驱动敞口压力测试_20260815_v0.3.json")
    forecast_ledger = read_json(ROOT / "data/pdca/forecast_ledger.json")

    quotes = {q.get("symbol"): q for q in market.get("quotes", [])}
    usd_jpy = quotes.get("JPY=X", {}).get("close", 159.304993)
    judgments = judgments_doc["judgments"]
    scenarios = judgments_doc["scenarios"]
    final_codes = final_doc["final_research_codes"]
    cards = {c["code"]: c for c in cards_doc["cards"]}

    account_status = [
        {"account":"富途","basis":"OpenD（富途本地只读数据服务）刷新","date":futu["generated_at"],"target":True,"risk":True,"blind":"基金资产仅有汇总字段；无逐项名称"},
        {"account":"SBI（归属未闭合）","basis":"Drive最近实物/手动截图","date":sbi["截图日期"],"target":True,"risk":True,"blind":"个人/公司归属未能从实物独立区分；未发现SBI公司独立实物"},
        {"account":"IBKR","basis":"Drive最近实物/手动截图","date":ibkr["截图日期"],"target":False,"risk":True,"blind":"不是生产日事实；META不进入目标完成度"},
        {"account":"bitFlyer","basis":"Drive最近实物/手动截图","date":bitflyer["截图日期"],"target":False,"risk":True,"blind":"不是生产日事实；加密总敞口可能已变化"},
    ]

    account_assets: list[dict[str, Any]] = []
    merged: dict[str, dict[str, Any]] = defaultdict(lambda: {"quantity":0.0,"usd_value":0.0,"accounts":[],"dates":set(),"names":set()})

    def add_asset(account: str, code: str, name: str, asset_type: str, qty: float, currency: str,
                  local_value: float, usd_value: float, date: str, target: bool, source: str) -> None:
        row = {"account":account,"code":code,"name":name,"asset_type":asset_type,"quantity":qty,
               "currency":currency,"local_value":local_value,"usd_value":usd_value,"data_date":date,
               "target_management":target,"risk_management":True,"source":source}
        account_assets.append(row)
        if asset_type in {"股票","加密资产"}:
            m = merged[code]
            m["quantity"] += float(qty)
            m["usd_value"] += float(usd_value)
            m["accounts"].append(account)
            m["dates"].add(date)
            m["names"].add(name)

    for p in futu["futu_positions"]:
        cur = "JPY" if p["symbol"].startswith("JP.") else "USD"
        local = float(p["broker_market_val"])
        usd = local / usd_jpy if cur == "JPY" else local
        add_asset("富途", p["symbol"], p["name"], "股票", p["quantity"], cur, local, usd,
                  futu["generated_at"], True, "OpenD只读刷新")
    add_asset("富途", "CASH.USD", "现金", "现金", futu["futu_cash"]["cash"], "USD",
              futu["futu_cash"]["cash"], futu["futu_cash"]["cash"], futu["generated_at"], True, "OpenD accinfo_query")
    add_asset("富途", "FUND.AGG", "基金资产（仅汇总）", "基金", 1, "USD",
              account_close["account_amounts"]["fund_assets_usd"], account_close["account_amounts"]["fund_assets_usd"],
              futu["generated_at"], True, "OpenD fund_assets汇总")
    for p in sbi["逐只"]:
        add_asset("SBI", p["code"], p["标的"], "股票", p["股数"], "JPY", p["市值本币"],
                  p["市值本币"] / usd_jpy, sbi["截图日期"], True, sbi["截图来源"])
    add_asset("SBI", "CASH.JPY", "买付余力", "现金", sbi["买付余力JPY_2営業日後"], "JPY",
              sbi["买付余力JPY_2営業日後"], sbi["买付余力JPY_2営業日後"] / usd_jpy, sbi["截图日期"], True, sbi["截图来源"])
    for p in ibkr["逐只"]:
        add_asset("IBKR", p["code"], p["标的"], "股票", p["股数"], p["币种"], p["市值本币"],
                  p.get("市值USD", p["市值本币"]), ibkr["截图日期"], False, ibkr["截图来源"])
    add_asset("IBKR", "CASH.USD", "现金", "现金", ibkr["现金USD"], "USD", ibkr["现金USD"], ibkr["现金USD"], ibkr["截图日期"], False, ibkr["截图来源"])
    for p in bitflyer["持有"]:
        typ = "现金" if p["code"] == "JPY" else "加密资产"
        add_asset("bitFlyer", p["code"], p["标的"], typ, p["数量"], "JPY", p["市值JPY"],
                  p["市值JPY"] / usd_jpy, bitflyer["截图日期"], False, bitflyer["截图来源"])

    merged_rows = []
    for code, item in sorted(merged.items()):
        merged_rows.append({
            "code": code,
            "name": " / ".join(sorted(item["names"])),
            "quantity": round(item["quantity"], 6),
            "usd_value_mixed_date": round(item["usd_value"], 2),
            "accounts": item["accounts"],
            "data_dates": sorted(item["dates"]),
            "warning": "跨日期估算，仅用于风险视图，不代表2026-08-15同日净值" if len(item["dates"]) > 1 or next(iter(item["dates"])) != futu["generated_at"] else "当日富途只读刷新",
        })

    holding_codes = [r["code"] for r in merged_rows]
    questions = [
        "公司做什么","如何赚钱","收入和利润来自哪里","财务质量","资产负债及现金流","护城河","竞争对手","当前投资逻辑",
        "当前估值方法","当前估值","便宜、合理、偏贵区间","可考虑买入区间","可考虑减持或替换区间","未来数日/数周预测",
        "未来一年预测","中性、乐观、悲观情景","成功概率","最大可能回撤","催化剂","反向质疑","失效条件","什么时候见分晓",
        "对+40%/+100%目标的作用","与其他持仓相比应留谁、减谁、换谁","下一次PDCA验证时间"
    ]
    holding_research = []
    for merged_row in merged_rows:
        code, name = merged_row["code"], merged_row["name"]
        p = profile_for(code, name)
        card = cards.get(code, {})
        fin = card.get("latest_financial_facts", {})
        val = card.get("valuation_facts", {})
        scenario = scenarios.get(code)
        judgment = judgments.get(code, p["thesis"])
        if scenario:
            one_year = f"中性{scenario[0]}；激进{scenario[1]}"
            scenarios_text = f"中性{scenario[0]}；乐观/激进{scenario[1]}；压力情景{scenario[3]}%"
            probability = f"GPT总控批准值 {scenario[2]}%"
            drawdown = f"压力回撤 {scenario[3]}%"
        else:
            one_year = "未获2026-08-15数值情景批准；不自行补数"
            scenarios_text = "中性/乐观/悲观数值待业务主脑批准；本版只保留事实和风险"
            probability = "未批准数值；不得由机械评分替代"
            drawdown = "未批准数值；仍进入账户风险与组合压力审查"
        valuation_now = (f"PE={val.get('pe_ratio','未取得')}，PB={val.get('pb_ratio','未取得')}；"
                         "机械字段只作证据，不直接形成买卖结论") if val else "缺少同口径最新正式估值；列入进一步了解"
        fin_text = (f"OCF TTM={fin.get('ocf_ttm','未取得')}，毛利率={fin.get('gross_margin','未取得')}%，"
                    f"净利率={fin.get('net_margin','未取得')}%，质量分={fin.get('financial_quality_score','未取得')}；需与正式财报口径核对") if fin else "本轮没有同口径结构化财务卡；使用账户事实并等待正式披露补齐"
        answers = [
            p["business"], p["money"], p["revenue"], fin_text,
            "按最新正式财报核对净现金/净负债、自由现金流和融资义务；无可靠字段时不估算放行。",
            p["moat"], p["competitors"], judgment, p["method"], valuation_now,
            "未获批准的价格区间不自行编造；以正式估值更新后分档。",
            "本轮不生成订单；没有批准买入价。",
            "本轮不生成订单；按已批准条件、替代价值和失效条件复核，不用固定15%/20%/30%机械线。",
            p["short"], one_year, scenarios_text, probability, drawdown, p["catalyst"], p["reverse"], p["invalidate"], p["timing"],
            ("SNDK目标贡献已隔离；只计账户风险。" if code == "US.SNDK" else
             "IBKR/bitFlyer资产只进入风险管理，不进入目标完成度。" if any(a in {"IBKR","bitFlyer"} for a in merged_row["accounts"]) else
             "进入目标管理，但跨账户不同日期使精确贡献只能作为条件范围。"),
            ("COIN优先保留、CRCL第二、MSTR第一条件替换；其余比较需以已批准判断和替代证据为准。" if code in {"US.COIN","US.CRCL","US.MSTR"} else
             "先与现有AI/加密同驱动集中度和VRT、TSM、CRDO等替代机会比较；未获批准不新增动作。"),
            p["timing"],
        ]
        holding_research.append({
            "code":code,"name":name,"accounts":merged_row["accounts"],"data_dates":merged_row["data_dates"],
            "judgment":judgment,"questions":[{"no":i+1,"question":q,"answer":answers[i]} for i,q in enumerate(questions)]
        })

    candidate_tracks = []
    for code in final_codes:
        card = cards[code]
        fin = card.get("latest_financial_facts", {})
        val = card.get("valuation_facts", {})
        p = profile_for(code, card["company"])
        quality = fin.get("financial_quality_score")
        gate2 = "REVIEW_REQUIRED" if quality in (None, 0, 0.0) else "PASS_TO_VALUATION"
        gate3 = "VALUATION_REVIEW_REQUIRED" if val.get("pe_ratio") in (None, 0, 0.0) else "PASS_TO_MOAT_REVIEW"
        priority = "已达到优先比较条件" if code in {"US.VRT","US.TSM","US.CRDO"} else "尚未达到替换现有持仓条件"
        candidate_tracks.append({
            "code":code,"company":card["company"],"theme":card["theme"],
            "activation_evidence":"GPT总控批准扫描方向 + 当日扫描实际进入研究范围；不等于正式行业激活或买入",
            "gate1":{"conclusion":"PASS_RESEARCH_SCOPE","evidence":card["scan_reason"],"failure":"无"},
            "gate2":{"conclusion":gate2,"evidence":fin,"failure":"财务质量分缺失/为0需校正" if gate2=="REVIEW_REQUIRED" else "无"},
            "gate3":{"conclusion":gate3,"evidence":val,"failure":"估值字段不足" if gate3.startswith("VALUATION") else "无"},
            "gate4":{"conclusion":"DEEP_REVIEW","evidence":p["moat"],"failure":"护城河尚需正式披露与竞争对手交叉验证"},
            "gate5":{"conclusion":"RETAINED_FOR_GPT_RESEARCH","evidence":judgments.get(code,"本轮保留研究，未获业务取舍"),"failure":"不得把机械评分当投资判断"},
            "final_status":"保留研究","replacement_condition":priority,
            "gap":"除VRT/TSM/CRDO外，缺少已批准的替代排序；数据缺口见研究卡",
        })

    evidence_trace = [
        {"conclusion_id":"CON-001","conclusion":"今日不生成交易订单；先处理同驱动集中和数据缺口。","evidence_id":["EVD-FUTU-20260815","EVD-AI-STRESS","EVD-ACCOUNT-MIXED"],"rule_id":["RULE-SHAPE","RULE-13-2"],"reasoning":"账户日期不一致且AI广义暴露高，先看风险和替代价值。","counter":"现金和异质资产可缓冲部分波动。","action":"保持候选状态，无自动交易。"},
        {"conclusion_id":"CON-002","conclusion":"加密驱动优先保留COIN，其次CRCL，MSTR为第一条件替换对象。","evidence_id":["EVD-COIN-OFFICIAL","EVD-CRCL-OFFICIAL","EVD-MSTR-OFFICIAL","EVD-BITFLYER-LASTKNOWN"],"rule_id":["RULE-DEPTH","RULE-NO-FIXED-WEIGHT"],"reasoning":"收入多元性、许可进展和资本结构风险不同。","counter":"三者仍受同一加密周期影响，bitFlyer不是当日数据。","action":"业务处置优先级，不是订单。"},
        {"conclusion_id":"CON-003","conclusion":"AI直接敞口48.148%，广义敞口61.476%；新增AI前先做替换比较。","evidence_id":["EVD-AI-STRESS","EVD-FUTU-20260815","EVD-NVDA-FINANCE"],"rule_id":["RULE-DEPTH","RULE-NO-FIXED-WEIGHT"],"reasoning":"多只资产由同一AI资本开支驱动，名义分散不等于风险分散。","counter":"不同公司商业模式和现金流质量不同。","action":"展示20%/35%压力，不用30%机械线。"},
        {"conclusion_id":"CON-004","conclusion":"SNDK市值进入风险，但退出年度目标贡献。","evidence_id":["EVD-FUTU-20260815","EVD-SNDK-CORRECTION"],"rule_id":["RULE-DEPTH","RULE-EVIDENCE-TRUTH"],"reasoning":"券商持仓市值是账户事实，研究价格/拆股/财务口径尚未校正。","counter":"湖水8/15材料支持长期存储需求，但不能修复口径。","action":"校正前持有不加仓，贡献标记排除。"},
        {"conclusion_id":"CON-005","conclusion":"+40%有条件可能，+100%不能据现有证据宣称可达。","evidence_id":["EVD-TARGET-BOUNDARY","EVD-ACCOUNT-MIXED","EVD-PDCA"],"rule_id":["RULE-GOAL","RULE-PDCA"],"reasoning":"已批准情景的机械贡献为18.497个百分点，但这不是实际进度且账户非同日。","counter":"若高弹性候选兑现，贡献可能提高，同时回撤也显著扩大。","action":"先补基准和证据，用条件公式管理差距。"},
    ]

    layers = [
        {"layer":1,"name":"世界观","date":"2026-08-14/15","facts":["美股主要指数小幅回落，Russell 2000上涨0.51%","美国7月零售销售环比下降0.6%，控制组下降0.4%","老雷8/3-8/5观点：市场由流动性驱动转向基本面兑现"],"conclusion":"主题仍在，但收益更依赖盈利、现金流和兑现。","next":"进入宏观利率与资本成本。","block":"无；老雷仅作外部观点，不冒充当日新闻"},
        {"layer":2,"name":"国家与宏观战略","date":"2026-07-29至2026-08-15","facts":["美联储7月会议维持3.50%-3.75%","Reuters消息人士称BOJ考虑最早9月加息，尚非正式决定","USD/JPY 159.30"],"conclusion":"美国增长偏弱与折现率可能下降形成混合影响；日本利率与日元是日股关键变量。","next":"传给资金流和日股压力测试。","block":"BOJ不是正式决定，不能写成已加息"},
        {"layer":3,"name":"资金流","date":"2026-08-14/15","facts":["TLT -0.67%，VIX 14.25","湖水8/15材料称GS净杠杆截至8/12约79%，80%附近、82%预警","韩国外资净买入约21.5亿美元并加速买入Samsung/SK hynix"],"conclusion":"风险偏好尚可但拥挤和杠杆使AI链对坏消息敏感。","next":"传给板块轮动与压力测试。","block":"湖水为外部观点/资金流材料，需与官方和价格事实并列"},
        {"layer":4,"name":"板块轮动","date":"2026-08-14/15","facts":["SOXX -0.06%，SNDK +7.39%，AVGO -5.94%，NVDA -0.06%","AI融资安排潜在规模超5000亿美元，不等于NVDA已支出","存储、AI基础设施、日本金融为扫描重点"],"conclusion":"AI基础设施和存储仍是研究主线，但分化与融资风险上升。","next":"传给21只机会池。","block":"不由Codex改变正式激活状态"},
        {"layer":5,"name":"机会池","date":"2026-08-15","facts":["全市场扫描16,815只，21只进入最终机械研究名单","VRT第一、TSM第二、CRDO第三为已批准新机会排序","PLTR和ON均实际进入扫描记录"],"conclusion":"候选必须逐只过五关；指定核查不等于入选。","next":"与现有持仓的质量、回撤和同驱动比较。","block":"机械评分不是投资判断"},
        {"layer":6,"name":"持仓与替代","date":"富途2026-08-15；其他账户最后已知日期","facts":["富途12只实时刷新；SBI/IBKR/bitFlyer使用最后已知实物","AI广义暴露61.476%，含SNDK风险但目标贡献排除","加密排序COIN→CRCL→MSTR"],"conclusion":"不机械按比例交易；先解释风险、替代价值和证据盲区。","next":"传给今日行动与目标管理。","block":"跨账户不是同日净值"},
        {"layer":7,"name":"复盘和PDCA","date":"历史统计至2026-08-10；新基线2026-08-15","facts":["历史短期已评4条、命中1条、累计25%","长期已评0条，不能宣称准确率","本产品建立可验证的新基线，不回写历史结论"],"conclusion":"当前准确率不足以放大风险；预测必须按锁定日期复核。","next":"形成下次检查日和失效条件。","block":"部分旧预测缺锁定价，不能严格评分"},
    ]

    chains = [
        {"chain_id":"CHAIN-AI-01","path":"美国消费偏弱与折现率混合 → AI融资支持需求但杠杆上升 → NVDA/TSM/AVGO/VRT/CRDO → 现有AI广义暴露61.476% → 新增前先比较替换价值，不生成订单"},
        {"chain_id":"CHAIN-JP-01","path":"BOJ加息可能性（报道，非决定） → 日元/收益率可能上升 → 日本银行保险受益而高久期/出口资产承压 → 软银/任天堂/东京海上等 → 纳入日股压力测试，等待官方决定"},
    ]

    goal_paths = {
        "actual_progress":"无法精确计算：缺经确认年初统一基准，且SBI/IBKR/bitFlyer不是生产日快照。",
        "confirmed_component":"GPT总控已批准数值情景的机械中性贡献18.497个百分点；SNDK贡献1.412个百分点已剔除。该数不是年内实际收益。",
        "gap_to_40_component":round(40-target_old["neutral_midpoint_contribution_pp_from_quantified_holdings"],3),
        "gap_to_100_component":round(100-target_old["neutral_midpoint_contribution_pp_from_quantified_holdings"],3),
        "remaining_days":(datetime(2026,12,31).date()-datetime(2026,8,15).date()).days,
        "conditional_required_returns":[
            {"assumed_ytd_pct":r,"required_to_40_pct":round(((1.4/(1+r/100))-1)*100,2),"required_to_100_pct":round(((2.0/(1+r/100))-1)*100,2)}
            for r in (-10,0,10,20)
        ],
        "assessment":"+40%在盈利兑现、候选替代和回撤受控同时成立时有条件可能；+100%需要极高弹性与风险暴露，现有证据不足以宣称可达。",
        "drivers":["NVDA/MSFT/AVGO/软银等核心AI兑现","VRT/TSM/CRDO替代机会","存储周期在口径校正后兑现"],
        "drags":["MSTR资本结构放大BTC风险","SNDK数据未校正","跨账户日期与年初基准缺口","AI同驱动集中"],
        "today_action":"先做证据和替代比较，不用固定比例机械交易。",
        "inaction":"若不处理集中度和MSTR替代条件，AI或加密同向回撤会放大；若过度降波动，也可能伤害+40%弹性。",
        "prohibited":"杠杆追涨、补仓摊低成本、自动下单、用旧截图冒充当日、为+100%强行提高风险。",
        "next_check":"2026-08-19及下一次正式财报/账户新实物。",
    }

    historical_accuracy = {"short_reviewed":4,"short_hits":1,"short_accuracy_pct":25,"long_reviewed":0,"long_hits":0,"long_accuracy":"无可评分样本"}
    pdca = {
        "source_summary":historical_accuracy,
        "source_file":"data/pdca/forecast_ledger.json",
        "truth_note":"本日为Current蓝图重做基线建立日；历史台账有记录，但可严格评分样本有限，不用未来观察冒充已完成PDCA。",
        "new_baselines":[
            {"prediction_id":"PRED-20260815-AI-CAPEX","source":"GPT总控已批准判断","prediction":"AI基础设施需求逻辑继续，但融资杠杆使同驱动回撤风险上升。","success_definition":"下一轮NVDA/TSM/AVGO/VRT/CRDO官方指引未整体下修，且融资风险被正式披露跟踪。","today_evidence":"NVDA相关融资安排与公司财务；当前仅建立基线","status":"尚不能判断","counterfactual":"若完全忽略集中度，AI广义跌20%时组合压力约12.295%","next_check":"下一次核心公司财报/2026-08-31"},
            {"prediction_id":"PRED-20260815-CRYPTO-ORDER","source":"GPT总控返修令","prediction":"COIN业务韧性优于CRCL，MSTR资本结构风险最高。","success_definition":"在同一加密压力窗口中，经营披露与回撤表现继续支持COIN→CRCL→MSTR排序。","today_evidence":"三家公司官方披露与账户风险；当前仅建立基线","status":"尚不能判断","counterfactual":"若继续给MSTR补仓，BTC下跌时普通股回撤和融资风险会被放大","next_check":"2026-08-31或三者下一份正式披露"},
            {"prediction_id":"PRED-20260815-SNDK-CORRECTION","source":"GPT总控v0.3返修令","prediction":"SNDK校正完成前，研究收益假设不具备进入目标贡献的资格。","success_definition":"价格、拆股、财务口径被正式证据闭合后再决定是否恢复贡献。","today_evidence":"券商市值65,644.40美元可核；研究口径未闭合","status":"尚不能判断","counterfactual":"若未校正就计入，机械贡献会虚增1.412个百分点","next_check":"数据校正完成即复核"},
        ],
        "review_entries":{"daily":"下一交易日检查价格/新闻/账户异常","weekly":"2026-08-21复核因果链、候选和压力","monthly":"2026-08-31复核预测、胜率和目标路径"},
    }

    external = {
        "edinet":{"status":"EDINET_CURRENT_KEY_UNAVAILABLE","meaning":"新电脑未找到EDINET密钥；当日API分支未调用","security":"未打印、未写日志、未上传密钥","historical":"2026-08-11历史EDINET实物覆盖9只日股，docID保留；当日使用TDnet、公司IR和历史EDINET并降级证据等级","source":str(SCAN / "V7_EDINET接续测试及覆盖结果_20260815.json")},
        "laolei":[
            {"date":"2026-08-05","file":"26-08-5-6老雷录音文本.txt","drive_id":"1yDjC9Y_EtGvKKyDfzTplW9I47alqK1eh","read":True,"support":"市场从流动性驱动转向基本面，支持重视毛利率和自由现金流。","challenge":"AI长期逻辑仍在，但高杠杆和拥挤会制造压力。","use":"作为中期外部观点，不冒充当日新闻。"},
            {"date":"2026-08-04","file":"26-08-4-6老雷录音文本.txt","drive_id":"1UT5gBLRCT8OV-pq8fHH3OnZ2QrrYuX4h","read":True,"support":"关注实际盈利兑现。","challenge":"主题上涨不能替代公司现金流。","use":"用于反向质疑。"},
            {"date":"2026-08-03","file":"26-08-3-2老雷录音文本.txt","drive_id":"1O1bZrkE-9128SRCzD4WS_LUxdW0GzIC7","read":True,"support":"AI中长期需求仍有支撑。","challenge":"拥挤和估值会放大回撤。","use":"与官方财务并列。"},
        ],
        "hushui":[
            {"date":"2026-08-15","file":"26-08-15-1 Tech Daily sell-side opinions & headlines .pdf","drive_id":"1ug-99ga2NZQlqHSZ84nuYGHCvZWNDbSa","read":True,"support":"SNDK长期存储合同、NVDA/VRT等AI基础设施需求线索。","challenge":"卖方目标价和融资叙事不能替代数据校正与公司现金流。","use":"候选研究支持/反向证据。"},
            {"date":"2026-08-15","file":"26-08-15-2 减仓窗口后移...pdf","drive_id":"1mbj_3CRVGAN22E3KF0wXU_nzo9AlHdj_","read":True,"support":"资金杠杆和潜在去风险窗口。","challenge":"时间窗是外部观点，不是确定事件。","use":"进入资金流与压力测试。"},
            {"date":"2026-08-15","file":"26-08-15-3韩国资金流周五继续改善.pdf","drive_id":"1aKa1Fla-GUH35sFswhv41wOO55TiHxxZ","read":True,"support":"韩国外资净买入和存储链资金改善。","challenge":"单日资金流不能证明周期持续。","use":"支持Samsung/存储观察。"},
        ],
    }

    further = [
        {"id":"OPEN-001","unknown":"EDINET新电脑安全密钥未找到","importance":"日股法定披露、订正关系和XBRL当日核验受限","missing":"本机安全配置","impact":"日股证据等级","method":"由本机安全配置恢复，不在聊天发送密钥","owner":"董事长/本机配置","eta":"配置后立即","allowed":"继续用TDnet/IR/历史EDINET并降级","forbidden":"声称当日EDINET已接通"},
        {"id":"OPEN-002","unknown":"SNDK价格、拆股与财务口径","importance":"影响估值和年度贡献","missing":"同口径正式数据","impact":"SNDK新增与目标贡献","method":"官方披露、券商公司行动记录交叉核对","owner":"数据链/业务主脑","eta":"校正完成日","allowed":"券商市值进入风险","forbidden":"加仓或计入目标贡献"},
        {"id":"OPEN-003","unknown":"SBI个人/公司归属及SBI公司独立实物","importance":"影响账户边界","missing":"身份明确的配置或截图","impact":"账户归属和目标管理","method":"继续从实物识别，不反复要求无交易确认","owner":"账户资料链","eta":"出现新实物时","allowed":"按SBI合并最后已知状态展示","forbidden":"猜测账户归属"},
        {"id":"OPEN-004","unknown":"富途基金资产28,873.30美元逐项身份","importance":"总资产已闭合但资产类别明细不足","missing":"基金逐项接口字段","impact":"类现金/风险分类","method":"后续只读接口补字段","owner":"OpenD数据链","eta":"下次接口扩展","allowed":"作为基金汇总进入资产","forbidden":"伪造基金名称"},
        {"id":"OPEN-005","unknown":"四账户同日净值和年初统一基准","importance":"决定+40%/+100%实际进度","missing":"统一口径年初基准和同日账户值","impact":"目标完成度","method":"沿用最近实物并在新资料出现时更新","owner":"账户/目标管理","eta":"证据齐备时","allowed":"展示条件公式和已确认部分","forbidden":"伪造精确进度"},
        {"id":"OPEN-006","unknown":"TSM券商累计盈亏口径","importance":"摊薄成本为负且券商累计盈亏率返回0","missing":"券商口径解释","impact":"盈亏展示","method":"保留原字段并只用平均成本未实现收益","owner":"OpenD数据链","eta":"下次券商字段核验","allowed":"展示现价/平均成本","forbidden":"用于投资判断或年度进度"},
        {"id":"OPEN-007","unknown":"ON、ETN、ASML个股新闻抓取失败项","importance":"可能漏掉公司级事件","missing":"替代来源交叉核验","impact":"候选第五关","method":"官方IR/SEC/新闻源补取","owner":"新闻链","eta":"下一轮采集","allowed":"保留研究并显著披露失败","forbidden":"写成没有重大新闻"},
        {"id":"OPEN-008","unknown":"东京海上、万代、软银、微软历史成交原因","importance":"影响复盘但不改变当前实物持仓","missing":"成交单或日志","impact":"历史归因","method":"有实物时补入；不从数量差推断","owner":"账户档案","eta":"实物出现时","allowed":"展示当前/最后已知数量","forbidden":"猜测成交"},
    ]

    blueprint_matrix = [
        {"requirement":"三层结构","current_evidence":"完整产品形态定义v1/三套结构映射表","product_location":"第一层今日怎么做、第二层为什么、第三层完整研究底稿","status":"PASS"},
        {"requirement":"七层因果链","current_evidence":"体系建设总则/三套结构映射表","product_location":"STR-005-04及两条贯通链","status":"PASS"},
        {"requirement":"账户来源与目标管理分离","current_evidence":"正式尺_总则第十三条之二","product_location":"STR-005-08全账户表","status":"PASS"},
        {"requirement":"全持仓25问","current_evidence":"完整产品深度标准","product_location":"STR-005-06，24类持仓×25问","status":"PASS"},
        {"requirement":"21只候选五关","current_evidence":"右栏过滤标准/扫描实物","product_location":"STR-005-07逐只轨迹","status":"PASS"},
        {"requirement":"目标管理","current_evidence":"正式总则/目标配置","product_location":"STR-005-09条件公式与边界","status":"PASS_WITH_EVIDENCE_GAP"},
        {"requirement":"真实PDCA","current_evidence":"PDCA记分规则准绳/历史台账","product_location":"STR-005-12历史准确率+新基线","status":"PASS"},
        {"requirement":"新闻真实性","current_evidence":"质量纪律看板第16条","product_location":"STR-005-04三类重大新闻和失败披露","status":"PASS"},
        {"requirement":"结论-证据-规则","current_evidence":"完整产品验收标准","product_location":"STR-005-13追踪表","status":"PASS"},
        {"requirement":"仍需进一步了解","current_evidence":"完整产品深度标准","product_location":"STR-005-15八项清单","status":"PASS"},
        {"requirement":"候选边界","current_evidence":"本次GPT总控开工令","product_location":"封面、尾页和状态字段","status":"PASS"},
    ]

    mother_matrix = [
        {"feature":"封面、数据日、run_id和状态","preserved":True,"location":"STR-005-00/01","update":"加入三层跳转与大白话状态","reason":"Current形态定义","deleted":"无"},
        {"feature":"今日行动摘要","preserved":True,"location":"STR-005-02/03","update":"使用8/15已批准判断，不沿用8/11旧动作","reason":"账户和业务判断已更新","deleted":"旧日期动作"},
        {"feature":"七层链路","preserved":True,"location":"STR-005-04","update":"加入老雷/湖水、BOJ报道、融资风险","reason":"8/11后证据增量","deleted":"无"},
        {"feature":"研究底稿","preserved":True,"location":"STR-005-05","update":"完整账户、持仓、候选和证据链","reason":"完整产品退回要求","deleted":"无"},
        {"feature":"全部持仓逐只研究","preserved":True,"location":"STR-005-06","update":"24类持仓×25问；旧截图显式标日期","reason":"总则13.2和深度标准","deleted":"无"},
        {"feature":"机会池和五关","preserved":True,"location":"STR-005-07","update":"21只逐只五关，不用16,815概数替代","reason":"本次退回原文","deleted":"无"},
        {"feature":"账户与集中度","preserved":True,"location":"STR-005-08/11","update":"富途刷新，其他账户最后已知；AI广义暴露与SNDK隔离","reason":"8/15批准增量","deleted":"固定15/20/30机械线"},
        {"feature":"+40%/+100%目标","preserved":True,"location":"STR-005-09","update":"条件公式和已确认贡献，不以NOT_CALCULABLE停止","reason":"本次开工令","deleted":"伪精确进度"},
        {"feature":"预测和PDCA","preserved":True,"location":"STR-005-10/12","update":"历史准确率与新锁定基线分开","reason":"PDCA准绳","deleted":"把未来观察冒充已评分"},
        {"feature":"反向质疑/压力测试","preserved":True,"location":"STR-005-11","update":"AI含/不含SNDK、加密和日元利率风险","reason":"v0.3批准内容","deleted":"无"},
        {"feature":"证据和问题台账","preserved":True,"location":"STR-005-13/14/15","update":"加入ID追踪、EDINET阻断和外部研究资料","reason":"Current验收标准","deleted":"无"},
    ]

    gaps = [
        {"priority":"P1","item":"EDINET当日API","status":"EDINET_CURRENT_KEY_UNAVAILABLE","effect":"日股法定披露当日自动核验降级；TDnet/IR/历史EDINET继续"},
        {"priority":"P1","item":"SNDK研究口径","status":"DATA_CORRECTION_REQUIRED","effect":"市值计风险，目标贡献排除"},
        {"priority":"P1","item":"年度实际进度","status":"RANGE_ONLY","effect":"无统一年初基准和四账户同日净值"},
        {"priority":"P2","item":"SBI账户归属","status":"OWNERSHIP_UNRESOLVED","effect":"按SBI合并展示；SBI公司实物未找到"},
        {"priority":"P2","item":"富途基金明细","status":"AGGREGATE_ONLY","effect":"总资产已闭合，基金名称未知"},
        {"priority":"P2","item":"TSM券商盈亏口径","status":"BROKER_PL_BASIS_UNRESOLVED","effect":"原字段保留但不用于判断"},
        {"priority":"P2","item":"ON/ETN/ASML公司新闻","status":"FETCH_FAILED","effect":"显著披露，不写成无重大新闻"},
    ]

    # Structured artifacts are written before the HTML so the product can link to them.
    artifacts: dict[str, Any] = {
        "03_三层结构检查报告_20260815.json":{"run_id":run_id,"layers":[{"layer":1,"status":"PASS"},{"layer":2,"status":"PASS"},{"layer":3,"status":"PASS"}],"html_controls":["全部展开","全部折叠","层间跳转"],"pdf_all_content_visible":True},
        "04_七层因果链检查报告_20260815.json":{"run_id":run_id,"layers":layers,"complete_chains":chains,"status":"PASS"},
        "05_结论证据规则追踪清单_20260815.json":{"run_id":run_id,"items":evidence_trace,"id_zero_count":0,"status":"PASS"},
        "06_全账户及全部资产清单_20260815.json":{"run_id":run_id,"usd_jpy":usd_jpy,"account_status":account_status,"assets":account_assets,"merged_positions":merged_rows,"mixed_date_warning":True},
        "07_每只持仓完整研究清单_20260815.json":{"run_id":run_id,"holding_count":len(holding_research),"questions_per_holding":25,"items":holding_research},
        "08_每只候选五关轨迹_20260815.json":{"run_id":run_id,"candidate_count":len(candidate_tracks),"items":candidate_tracks,"boundary":"机械轨迹不是投资判断"},
        "09_年度40_100目标路径_20260815.json":{"run_id":run_id,**goal_paths},
        "10_PDCA记分卡_20260815.json":{"run_id":run_id,**pdca},
        "11_老雷湖水EDINET接入与使用报告_20260815.json":{"run_id":run_id,**external},
        "12_仍需进一步了解清单_20260815.json":{"run_id":run_id,"items":further},
        "13_母版功能及新增成果对照_20260815.json":{"run_id":run_id,"items":mother_matrix,"post_20260811_increments":["四账户口径更新","富途18:35只读刷新","AI广义暴露与SNDK隔离","三项重大新闻","17只批准情景","MSTR/CRCL/COIN排序","SPCX身份核实","全市场16,815只扫描与21只研究名单"]},
        "14_数据缺口和失败项清单_20260815.json":{"run_id":run_id,"items":gaps,"missing_is_not_closed":True},
        "蓝图要求_Current证据_产品落点矩阵_20260815.json":{"run_id":run_id,"items":blueprint_matrix},
        "富途只读账户快照_本产品批次_20260815.json":{"run_id":run_id,"source_run_id":futu["run_id"],"source_generated_at":futu["generated_at"],"account_id":futu["account_id"],"input_hash":futu["input_hash"],"positions":futu["futu_positions"],"cash":futu["futu_cash"],"trading_calls":False},
    }
    for name, value in artifacts.items():
        write_json(out / name, value)

    account_rows = [[a["account"],a["basis"],a["date"],"是" if a["target"] else "否","是" if a["risk"] else "否",a["blind"]] for a in account_status]
    asset_rows = [[a["account"],a["code"],a["name"],a["asset_type"],fmt_num(a["quantity"],4),a["currency"],fmt_num(a["local_value"]),fmt_num(a["usd_value"]),a["data_date"],"目标+风险" if a["target_management"] else "仅风险"] for a in account_assets]
    merged_html_rows = [[m["code"],m["name"],fmt_num(m["quantity"],4),fmt_num(m["usd_value_mixed_date"]),", ".join(m["accounts"]),", ".join(m["data_dates"]),m["warning"]] for m in merged_rows]
    layer_rows = [[x["layer"],x["name"],x["date"],Raw("<ul>"+"".join(f"<li>{e(v)}</li>" for v in x["facts"])+"</ul>"),x["conclusion"],x["next"],x["block"]] for x in layers]
    evidence_rows = [[x["conclusion_id"],x["conclusion"],", ".join(x["evidence_id"]),", ".join(x["rule_id"]),x["reasoning"],x["counter"],x["action"]] for x in evidence_trace]
    candidate_rows = [[c["code"],c["company"],c["theme"],c["gate1"]["conclusion"],c["gate2"]["conclusion"],c["gate3"]["conclusion"],c["gate4"]["conclusion"],c["gate5"]["conclusion"],c["replacement_condition"]] for c in candidate_tracks]

    holding_sections = []
    for h in holding_research:
        qrows = [[q["no"],q["question"],q["answer"]] for q in h["questions"]]
        holding_sections.append(f'<details open class="holding" id="holding-{e(h["code"].replace(".","-"))}"><summary>{e(h["code"])} {e(h["name"])}｜{e(h["judgment"])}</summary><p class="muted">账户：{e(", ".join(h["accounts"]))}；证据日期：{e(", ".join(h["data_dates"]))}</p>{table(["#","问题","回答"],qrows,"research")}</details>')

    candidate_sections = []
    for c in candidate_tracks:
        rows = []
        for idx in range(1,6):
            g = c[f"gate{idx}"]
            rows.append([f"第{idx}关",g["conclusion"],json.dumps(g["evidence"],ensure_ascii=False),g["failure"]])
        candidate_sections.append(f'<details open class="candidate" id="candidate-{e(c["code"].replace(".","-"))}"><summary>{e(c["code"])} {e(c["company"])}｜{e(c["theme"])}</summary>{table(["关卡","结论","证据","失败/缺口"],rows,"research")}<p><b>最终状态：</b>{e(c["final_status"])}；<b>替换条件：</b>{e(c["replacement_condition"])}；<b>差距：</b>{e(c["gap"])}</p></details>')

    news_rows = [
        ["美国7月零售销售","2026-08-14","环比-0.6%，九个月首次下降；控制组-0.4%。不能据单月确认衰退。","盈利预期偏负面、折现率偏正面","同比仍约+5%，退款、油价和Prime Day可能扰动","Reuters"],
        ["日本央行9月加息可能性","2026-08-14","来源报道/尚非日本央行正式决定；消息人士称最早或在9月17-18日会议。","银行保险潜在受益；软银/任天堂等面临利率和汇率压力","经济增长可能制约，加息可能推迟","Reuters"],
        ["NVIDIA相关AI基础设施融资","2026-08-14","潜在安排超5000亿美元，NVDA潜在支持最高约1250亿美元；不等于已发生现金支出。","支持AI需求逻辑，同时提高同驱动和信用风险","杠杆、对手方和利用率不达预期","Reuters"],
    ]

    html_doc = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>★2026-08-15完整投研产品候选 Current蓝图重做版</title>
<style>
:root{{--ink:#17202a;--muted:#5d6875;--line:#c9d2dc;--paper:#fff;--band:#eef3f6;--green:#126b50;--red:#a12c2c;--amber:#8a5b00;--blue:#225c9b}}
*{{box-sizing:border-box}} html{{scroll-behavior:smooth}} body{{margin:0;background:#e9edf0;color:var(--ink);font:10.6pt/1.56 "Yu Gothic","Microsoft YaHei",Arial,sans-serif;letter-spacing:0}}
.page{{max-width:1180px;margin:0 auto;background:var(--paper);min-height:100vh;box-shadow:0 0 24px #0002}} header{{padding:28px 36px 22px;border-bottom:4px solid var(--ink);background:#fff}}
h1{{font-size:25pt;line-height:1.15;margin:0 0 10px}} h2{{font-size:17pt;border-bottom:2px solid var(--ink);padding-bottom:5px;margin:30px 0 12px}} h3{{font-size:13pt;margin:22px 0 8px}} h4{{font-size:11.5pt;margin:16px 0 6px}}
p,li{{max-width:98ch}} .meta{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;font-size:9.5pt}} .status{{padding:6px 8px;border:1px solid var(--line);background:var(--band)}}
.warn{{color:var(--amber);font-weight:700}} .bad{{color:var(--red);font-weight:700}} .good{{color:var(--green);font-weight:700}} nav{{position:sticky;top:0;z-index:5;background:#17202a;color:white;padding:8px 20px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}} nav a,nav button{{color:white;background:transparent;border:1px solid #ffffff66;padding:5px 9px;border-radius:4px;text-decoration:none;font:inherit;cursor:pointer}}
main{{padding:0 36px 46px}} .screen{{min-height:72vh;padding-top:8px}} .callout{{border-left:5px solid var(--blue);padding:10px 14px;background:#f4f7f9;margin:10px 0}} .risk{{border-left-color:var(--red);background:#fff5f4}} .action{{border-left-color:var(--green);background:#f2f8f5}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}} .panel{{border:1px solid var(--line);padding:12px;background:#fff}} .panel h3{{margin-top:0}} .table-wrap{{overflow-x:auto;margin:8px 0 16px}} table{{width:100%;border-collapse:collapse;table-layout:auto}} th,td{{border:1px solid var(--line);padding:6px 7px;vertical-align:top;text-align:left;font-size:8.8pt;overflow-wrap:anywhere}} th{{background:#e7edf1;font-weight:700}} tr:nth-child(even) td{{background:#fafbfc}} ul{{margin:5px 0;padding-left:20px}}
details{{border:1px solid var(--line);margin:10px 0;background:white}} summary{{font-weight:700;padding:9px 11px;background:#edf2f5;cursor:pointer}} details>p,details>.table-wrap{{margin-left:11px;margin-right:11px}} .muted{{color:var(--muted)}} code{{font-family:Consolas,monospace;font-size:.92em;overflow-wrap:anywhere}} .pill{{display:inline-block;border:1px solid var(--line);padding:2px 6px;border-radius:4px;margin:2px;background:#fff}} .toc ol{{columns:2}} .page-break{{break-before:page}} .avoid{{break-inside:avoid}}
@media(max-width:760px){{header,main{{padding-left:18px;padding-right:18px}} .meta,.grid{{grid-template-columns:1fr}} .toc ol{{columns:1}} h1{{font-size:20pt}}}}
@page{{size:A4 portrait;margin:13mm 11mm 15mm}} @media print{{body{{background:#fff;font-size:10pt}} .page{{box-shadow:none;max-width:none}} nav{{display:none}} header,main{{padding-left:0;padding-right:0}} details{{break-inside:auto}} details>summary{{break-after:avoid}} .screen{{min-height:0}} th,td{{font-size:8.5pt;padding:4px 5px}} a{{color:#000;text-decoration:none}}}}
</style></head><body><div class="page"><header id="STR-005-00"><h1>★2026-08-15 完整投研产品候选<br>Current蓝图重做版</h1><p>生产日：2026-08-15 JST｜生成时间：{e(now.isoformat(timespec="seconds"))}｜run_id：<code>{e(run_id)}</code></p><div class="meta"><div class="status"><b>business_pass</b><br><span class="warn">PENDING_INDEPENDENT_REVIEW</span></div><div class="status"><b>final_product_pass</b><br><span class="warn">PENDING_INDEPENDENT_REVIEW</span></div><div class="status"><b>release_status</b><br><span class="bad">NOT_AUTHORIZED</span></div></div><p class="muted">候选，不是正式产品；不构成订单或自动下单授权。正式日报仍为《当前暂无合格正式产品》说明。</p></header>
<nav><a href="#layer1">第一层 今天怎么做</a><a href="#layer2">第二层 为什么</a><a href="#layer3">第三层 研究底稿</a><a href="#accounts">账户</a><a href="#holdings">持仓25问</a><a href="#candidates">候选五关</a><a href="#target">目标</a><a href="#pdca">PDCA</a><button onclick="document.querySelectorAll('details').forEach(x=>x.open=true)">全部展开</button><button onclick="document.querySelectorAll('details').forEach(x=>x.open=false)">全部折叠</button></nav><main>
<section id="STR-005-01"><h2>临时合规状态与大白话说明</h2><p><b>pp</b>是百分点；<b>NAV</b>是资产净值；<b>OpenD</b>是富途本地只读数据服务；<b>FETCH_FAILED</b>是数据抓取失败；<b>PENDING_INDEPENDENT_REVIEW</b>是等待独立复验；<b>NOT_AUTHORIZED</b>是尚未授权发布。</p><p>本产品把缺失写成缺失：EDINET当日密钥未找到、SNDK研究口径未校正、四账户不是同一数据日。它们不会被写成已经闭合。</p></section>
<section id="layer1" class="screen"><h2>第一层｜今天怎么做</h2><div class="callout action"><h3>最重要的五个结论</h3><ol><li><b>核心不是追涨，而是先看同一驱动：</b>AI直接敞口48.148%，加入软银代理敞口后约61.476%。新增AI之前，先比较是否替换较弱持仓。</li><li><b>加密排序已明确：</b>COIN优先保留，CRCL第二小仓观察，MSTR是第一条件减持/替换对象；这不是交易订单。</li><li><b>SNDK先校正再谈贡献：</b>65,644.40美元券商市值继续计入风险，但退出年度目标贡献，校正前不加仓。</li><li><b>新机会研究顺序：</b>VRT第一、TSM第二、CRDO第三；仍需与现有持仓比较后才可能形成动作。</li><li><b>账户口径诚实分层：</b>富途已于{e(futu["generated_at"])}只读刷新；SBI、IBKR、bitFlyer使用各自最近截图的最后已知状态。</li></ol></div>
<div class="grid"><div class="panel"><h3>当前持仓怎么分</h3><p><b>核心持有：</b><a href="#holding-US-NVDA">NVDA</a>、<a href="#holding-US-MSFT">MSFT</a>；<b>继续持有/暂停新增：</b><a href="#holding-JP-9984">软银</a>、<a href="#holding-JP-7974">任天堂</a>、<a href="#holding-JP-4568">第一三共</a>、<a href="#holding-US-AVGO">AVGO</a>；<b>校正前不加仓：</b><a href="#holding-US-SNDK">SNDK</a>；<b>条件替换优先：</b><a href="#holding-US-MSTR">MSTR</a>；<b>最后已知账户风险观察：</b>SBI、IBKR、bitFlyer其余持仓。</p></div><div class="panel"><h3>今日不行动会怎样</h3><p>不处理集中度并不等于马上出事，但AI或加密同向下跌时，组合回撤会被放大。含SNDK口径下，AI广义资产整体跌20%对应组合压力约12.295%，跌35%约21.516%。</p></div><div class="panel"><h3>+40% / +100%</h3><p>已批准数值情景的机械中性贡献为18.497个百分点，不是实际年内进度。+40%有条件可能；+100%不能据现有证据宣称可达，更不能靠杠杆或追涨强行实现。</p></div><div class="panel"><h3>今天禁止做什么</h3><p>不自动下单、不恢复Release、不覆盖正式日报、不用15%/20%/30%固定线机械交易、不用旧截图冒充当天、不用SNDK未校正假设贡献目标。</p></div></div>
<div class="callout risk"><b>最可能推翻当前判断的新证据：</b>核心AI公司指引整体下修；BOJ正式政策与报道相反；SNDK校正后财务不支持存储逻辑；COIN/CRCL经营数据恶化；MSTR资本结构或BTC逻辑显著变化；新账户实物显示集中度与当前最后已知状态明显不同。</div>
<h3>账户是否完整</h3>{table(["账户","口径","实际日期","目标管理","风险管理","盲区及影响"],account_rows)}</section>
<section id="STR-005-02"><h2>今日决策摘要</h2><p>事实是什么：美国消费数据转弱、BOJ加息仍只是报道、AI融资支持需求同时增加杠杆；富途已刷新，其他账户是最后已知状态。为什么重要：组合同时暴露于AI、加密、日元和利率。对持仓的影响：收益弹性仍在，但同向回撤和数据盲区限制了精确目标管理。现在怎么办：优先做替换比较、SNDK校正和证据闭合，不生成订单。推翻条件：见上方清单。</p></section>
<section id="STR-005-03"><h2>行动明细（无订单）</h2>{table(["优先级","事项","现在做什么","不做什么","验证点"],[[1,"账户和口径","保留富途刷新与三账户最后已知日期","不伪造同日净值","新账户实物/年初基准"],[2,"AI集中","看含/不含SNDK压力并比较替代价值","不用30%机械线","核心公司指引与同向回撤"],[3,"加密排序","COIN→CRCL→MSTR执行研究优先级","不按账面亏损机械卖出","经营披露、BTC和融资条件"],[4,"SNDK","账户风险继续计算，目标贡献排除","校正前不加仓","拆股/价格/财务口径"],[5,"候选","VRT→TSM→CRDO优先深研","不把扫描分当买入","五关证据与持仓比较"]])}</section>
<section id="layer2" class="page-break"><h2>第二层｜为什么这么做</h2><h3 id="STR-005-04">七层因果链</h3>{table(["层","名称","证据日期","实际事实","本层结论","传给下一层","阻断/边界"],layer_rows,"layers")}<h3>两条完整贯通链</h3>{table(["链ID","宏观事实 → 行业驱动 → 候选 → 持仓比较 → 今日行动"],[[c["chain_id"],c["path"]] for c in chains])}
<h3>当日市场、宏观与重大新闻</h3>{table(["事件","日期","事实","组合影响","反向风险","来源"],news_rows)}<p class="muted">新闻真实性检查：市场级重大新闻不由ON、ETN、ASML个股抓取失败替代；抓取失败显著披露，不写成“没有重大新闻”。</p>
<h3>外部观点如何使用</h3>{table(["来源","日期","实际读取","支持","反对/风险","处理"],[["老雷",x["date"],"是",x["support"],x["challenge"],x["use"]] for x in external["laolei"]]+[["湖水",x["date"],"是",x["support"],x["challenge"],x["use"]] for x in external["hushui"]])}</section>
<section id="layer3" class="page-break"><h2>第三层｜完整研究底稿</h2><div class="toc"><h3>目录</h3><ol><li>完整研究基座</li><li>全账户及资产</li><li>24类持仓25问</li><li>21只候选五关</li><li>+40%/+100%目标路径</li><li>预测与PDCA</li><li>反向质疑和压力测试</li><li>证据链</li><li>指标、冲突和仍需了解</li><li>母版与增量对照</li></ol></div>
<section id="STR-005-05"><h2>完整研究基座</h2><p>扫描覆盖16,815只（美股13,062、日股3,753），21只进入最终机械研究名单。研究卡包含行情、财务、估值、公告、催化剂、反向质疑和缺口；机械入围只说明“值得研究”，不等于买入或行业激活。</p>{table(["项目","数量/状态","解释"],[["全市场扫描","16,815","覆盖报告中的实际扫描总数"],["60日成交额池","788","不能用单日成交额替代"],["最终研究名单",len(candidate_tracks),"逐只五关在后文"],["固定比例筛除","未使用","15%/20%/30%不是机械筛除线"],["PLTR/ON","均有实际轨迹","指定核查不保证入选"]])}</section>
<section id="accounts" class="page-break"><h2 id="STR-005-08">全账户、资产和集中度</h2><p><b>统一换算：</b>USD/JPY={fmt_num(usd_jpy,4)}，时间为2026-08-14最后完成日线。不同账户日期不能拼成“8月15日同日净值”，下面美元数只用于风险视图。</p>{table(["账户","代码","名称","类别","数量","币种","本币市值","美元估算","数据日期","用途"],asset_rows,"assets")}<h3>跨账户同标的合并视图</h3>{table(["代码","名称","合计数量","美元估算","账户","证据日期","警告"],merged_html_rows,"merged")}
<h3>富途金额闭合</h3>{table(["项目","美元","说明"],[["总资产",fmt_num(futu["futu_cash"]["total_assets"]),"OpenD账户汇总"],["市场市值",fmt_num(futu["futu_cash"]["market_val"]),"OpenD账户汇总"],["现金",fmt_num(futu["futu_cash"]["cash"]),"含币种汇总"],["基金资产",fmt_num(account_close["account_amounts"]["fund_assets_usd"]),"只有汇总字段"],["负现金/融资/应计利息","0 / 0 / 0","本次OpenD返回字段"],["闭合状态","CLOSED_TO_OPEND_TOTAL_ASSETS","原2.48%差额由基金资产、换算和舍入解释"]])}</section>
<section id="holdings" class="page-break"><h2 id="STR-005-06">全部持仓逐只25问</h2><p>共{len(holding_research)}类持仓，覆盖富途、SBI、IBKR、bitFlyer。每只均回答25项；没有业务主脑批准的数值不会由机械评分补造。</p>{''.join(holding_sections)}</section>
<section id="candidates" class="page-break"><h2 id="STR-005-07">21只候选五关轨迹</h2><p>以下是机械研究轨迹，不是Codex投资判断。第一关研究范围、第二关财务质量、第三关估值、第四关护城河、第五关业务主脑研究状态均逐只展示。</p>{table(["代码","公司","板块","第一关","第二关","第三关","第四关","第五关","替换条件"],candidate_rows,"candidates")}{''.join(candidate_sections)}</section>
<section id="target" class="page-break"><h2 id="STR-005-09">+40% / +100%目标管理</h2><div class="callout"><b>真实进度：</b>{e(goal_paths["actual_progress"])}<br><b>已确认部分：</b>{e(goal_paths["confirmed_component"])}<br><b>判断：</b>{e(goal_paths["assessment"])}</div>{table(["假设当前年内收益","从现在到+40%仍需","从现在到+100%仍需"],[[f'{x["assumed_ytd_pct"]}%',f'{x["required_to_40_pct"]}%',f'{x["required_to_100_pct"]}%'] for x in goal_paths["conditional_required_returns"]])}<h3>三情景（条件管理，不伪装精确预测）</h3>{table(["情景","条件","目标影响","风险"],[["悲观","AI/加密同向回撤、SNDK校正不支持、日元/利率不利","+40%明显受阻，先保全可恢复性","不能用补仓摊低或杠杆追回"],["基准","核心盈利兑现、替代机会谨慎落地、回撤可控","+40%有条件可能；已批准机械贡献18.497pp仍不足以单独证明","账户与基准缺口"],["乐观","AI基础设施、存储和高弹性候选同时兑现","可能显著缩小+40%差距；+100%仍需更多证据","同驱动集中和估值同步回撤"]])}<h3>贡献与瓶颈</h3><p><b>主要贡献：</b>{e('；'.join(goal_paths['drivers']))}。<b>最大拖累：</b>{e('；'.join(goal_paths['drags']))}。<b>今日行动：</b>{e(goal_paths['today_action'])}。<b>不行动：</b>{e(goal_paths['inaction'])}。<b>禁止：</b>{e(goal_paths['prohibited'])}。</p></section>
<section id="STR-005-10"><h2>预测、情景和概率</h2><p>17只获GPT总控数值情景；SNDK条件值不进入目标贡献，SPCX和其他未批准标的不补造数值。各持仓的中性、激进、概率和回撤已在25问中逐只展示。</p></section>
<section id="STR-005-11"><h2>反向质疑、压力测试和失效条件</h2>{table(["口径","AI直接敞口","AI广义敞口","直接跌20%","直接跌35%","广义跌20%","广义跌35%"],[["含SNDK券商市值","48.148%","61.476%","9.630%","16.852%","12.295%","21.516%"],["不含SNDK敏感性","42.500%","55.828%","8.500%","14.875%","11.166%","19.540%"]])}<div class="grid"><div class="panel"><h3>AI资本开支放缓</h3><p>NVDA、MSFT、AVGO、软银及VRT/CRDO可能同时受订单、预算和估值下修。</p></div><div class="panel"><h3>出口限制/客户自研</h3><p>芯片收入和先进制程结构变化，不能把公司名分散当风险分散。</p></div><div class="panel"><h3>加密回撤</h3><p>MSTR、COIN、CRCL和bitFlyer同向；MSTR资本结构进一步放大。</p></div><div class="panel"><h3>BOJ与日元</h3><p>正式政策若超预期，银行保险与高久期/出口资产可能出现相反方向变化。</p></div></div><p>这些是压力刻度，不是30%硬线，不自动触发交易。</p></section>
<section id="pdca" class="page-break"><h2 id="STR-005-12">真实PDCA记分卡</h2><p>{e(pdca['truth_note'])}</p>{table(["指标","结果","解释"],[["历史短期已评","4","来自旧台账"],["短期命中","1","累计25%"],["长期已评","0","不能宣称准确率"],["严格评分限制","存在","部分旧预测缺锁定价"]])}{table(["预测编号","上一次/本次锁定内容","成功定义","今日证据","状态","反事实","下次验证"],[[x["prediction_id"],x["prediction"],x["success_definition"],x["today_evidence"],x["status"],x["counterfactual"],x["next_check"]] for x in pdca["new_baselines"]])}<p><b>复盘入口：</b>日：{e(pdca['review_entries']['daily'])}；周：{e(pdca['review_entries']['weekly'])}；月：{e(pdca['review_entries']['monthly'])}。</p></section>
<section id="STR-005-13" class="page-break"><h2>数据来源与结论—证据—规则追踪</h2>{table(["结论ID","结论","证据ID","规则ID","为什么足够/不足","反向证据","最终动作"],evidence_rows,"evidence")}<h3>主要证据实物</h3>{table(["证据ID","实物/来源","日期","状态"],[["EVD-FUTU-20260815","data/accounts/futu_positions_20260815.json",futu["generated_at"],"只读刷新成功"],["EVD-ACCOUNT-MIXED","SBI/IBKR/bitFlyer最后已知截图派生JSON","2026-08-05/04/11","显式跨日期"],["EVD-MARKET","V7当日市场结构化行情_20260815.json","2026-08-14/15","事实包"],["EVD-SCAN","V7全市场扫描机器清单_20260815.json","2026-08-15","16,815只"],["EVD-EDINET","V7_EDINET接续测试及覆盖结果_20260815.json","2026-08-15","当日密钥缺失；历史证据保留"],["EVD-LAOL","Drive老雷文本3份","2026-08-03至05","实际读取"],["EVD-HUSHUI","Drive湖水PDF 3份","2026-08-15","实际读取"]])}</section>
<section id="STR-005-14"><h2>指标、冲突和失败项</h2>{table(["级别","项目","状态","影响"],[[g["priority"],g["item"],g["status"],g["effect"]] for g in gaps])}</section>
<section id="STR-005-15" class="page-break"><h2>仍需进一步了解</h2>{table(["ID","还不知道什么","为什么重要","缺少证据","可能改变","验证方法","负责人/来源","预计时间","未闭合允许","未闭合禁止"],[[x["id"],x["unknown"],x["importance"],x["missing"],x["impact"],x["method"],x["owner"],x["eta"],x["allowed"],x["forbidden"]] for x in further],"open-items")}</section>
<section class="page-break"><h2>蓝图要求—Current证据—产品落点</h2>{table(["蓝图要求","Current证据","产品落点","状态"],[[x["requirement"],x["current_evidence"],x["product_location"],x["status"]] for x in blueprint_matrix])}<h2>母版功能与8月11日后增量</h2>{table(["原母版功能","保留","位置","更新","原因","删除"],[[x["feature"],"是" if x["preserved"] else "否",x["location"],x["update"],x["reason"],x["deleted"]] for x in mother_matrix])}</section>
<section><h2>候选边界与停止状态</h2><ul><li><code>business_pass=PENDING_INDEPENDENT_REVIEW</code></li><li><code>final_product_pass=PENDING_INDEPENDENT_REVIEW</code></li><li><code>release_status=NOT_AUTHORIZED</code></li><li>未登记Release，未覆盖<code>00_今日日报.pdf</code>，未调用交易接口，未生成或执行订单。</li><li>完成后交GPT总控和原GPT终验线程全量终验。</li></ul></section>
</section></main></div><script>document.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',()=>{{const x=document.querySelector(a.getAttribute('href'));if(x&&x.tagName==='DETAILS')x.open=true}}));</script></body></html>'''

    product_html = out / "★2026-08-15完整投研产品候选_Current蓝图重做版.html"
    write_html(product_html, html_doc)

    construction = {
        "run_id":run_id,"data_date":DATA_DATE,"generated_at":now.isoformat(timespec="seconds"),
        "scope":"Current蓝图完整候选组装；无Release、无交易、无正式日报覆盖",
        "inputs":[str(ROOT / "data/accounts/futu_positions_20260815.json"),str(SCAN / "V7候选逐只研究卡_20260815.json"),str(OLD_V03 / "GPT总控判断落地矩阵_20260815_v0.3.json")],
        "changes":["保留已批准v0.3业务判断","扩展为三层/七层/24持仓25问/21候选五关","接入四账户最后已知口径","接入老雷、湖水和EDINET状态","建立目标条件路径和真实PDCA"],
        "prohibited_actions_confirmed":["未登记Release","未改正式日报","未调用交易接口","未生成订单","未修改制度"],
        "daily_before":daily_before,
    }
    write_json(out / "18_施工日志和变更清单_20260815.json", construction)
    print(json.dumps({"run_id":run_id,"output_dir":str(out),"html":str(product_html),"daily_before":daily_before},ensure_ascii=False,indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
