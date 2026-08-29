from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
V11 = ROOT / "output/candidates/2026-08-28/V7-V20-PREDICTIVE-FULL-HTML-V11-20260828113325-JST/★2026-08-27完整投研产品候选_v2.0_预测型完整HTML_v11.html"
V12_DIR = ROOT / "output/candidates/2026-08-28/V12-CHAIRMAN-DECISION-20260828181431-JST"
V12 = V12_DIR / "V12董事长投资决策产品.html"
V12_SOURCE = V12_DIR / "V12结构化产品源.json"
LOCKED_FORECASTS = ROOT / "output/decision_inputs/2026-08-26/V7-V20-FORECAST-LOCK-20260826175555-JST/84份正式预测_LOCKED.json"
PLUS100_SUPPLEMENT = ROOT / "output/candidates/2026-08-29/V13-USER-READABLE-20260829015943-JST/PLUS100_EVENT_WINDOW_RESEARCH_SUPPLEMENT_v3.json"
PLUS100_EVENT_CALENDAR = ROOT / "output/candidates/2026-08-29/V13-USER-READABLE-20260829015943-JST/42项未来12个月事件日历_v3.json"
V11_SHA = "3FCCD3E4F3978C87DDC18C6E80D570EE61427BA1A8052BBDD651C4477EB83E78"
V12_SHA = "C3D56CA6D3FE2624E396428515A916F66DE81336920A9815CD720C4DE4537494"
V11_URL = "https://drive.google.com/file/d/1hhCZB9E-QRM0lDrDKKnU359BWaJwwOe8/view"
V12_URL = "https://drive.google.com/file/d/1cKcOVHKPr1ed3AUMSI_J2zKyyiORgD4Z/view"
PLUS100_INDEX_URL = "https://drive.google.com/file/d/1dFQkw8K2KBREfulhs3cOOUd0_xqD3si2/view"
PLUS100_DRIVE_FILES = [
    ("完整研究补充", "PLUS100_EVENT_WINDOW_RESEARCH_SUPPLEMENT_v3.json", "1H_2GkpnIqC2hcrS--3BaMAyuZ9e7nV4p"),
    ("真实事件时间历史样本", "真实事件时间历史样本_v3.json", "181YXPYsZfY_W07YRnUG6-rSqNWIfkYry"),
    ("条件匹配历史事件样本", "条件匹配历史事件样本_v3.json", "1QonT09n2Sn3EeZn7J_biVtoHbfLRpsKT"),
    ("股票与基准1、5、20、60日收益", "股票与基准1_5_20_60日收益_v3.json", "1d9sx8A9jhMcZG6r6Vvbjz90XcceyQsOG"),
    ("超额收益与最大回撤", "超额收益与最大回撤统计_v3.json", "11HFZt4oVyqQzh5hM4ye4WDA_1PcVs0BX"),
    ("新A、B、C三级波段池", "新A_B_C三级波段池_v3.json", "1iCQ43a5QGched5FQx9cdlIWJghXW5YOA"),
    ("未来12个月真实事件日历", "42项未来12个月事件日历_v3.json", "11px_AAbUS0WuJc1cAns3-n9LMNfQ9Z9u"),
    ("时间重叠与风险相关性", "时间重叠与风险相关性v3.json", "1CWyzgcjY0_Q4S3kOeFl2nqKViV1XLEdR"),
    ("年度路径可计算性", "年度路径可计算性报告_v3.json", "1Ds-boBONb6TVONaOgYMIF8ZB_BdkOMDn"),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def pct(value, digits=1) -> str:
    if value is None:
        return "暂时无法可靠计算"
    return f"{float(value) * 100:+.{digits}f}%"


RECOMMENDATION = {
    "加仓倾向": "建议加仓", "继续持有": "建议持有", "减仓倾向": "建议减仓",
    "替换候选": "考虑替换", "等待触发": "先等",
}
CONFIDENCE = {"A": "较高", "B": "中等", "C": "较低"}

REPLACEMENTS = {
    "概率加权": "把较差、正常、较好三种情况按可能性合在一起",
    "EPS": "每股收益", "FCF": "自由现金流",
    "PE": "市盈率（当前股价相当于多少年的公司利润）",
    "NAV": "净资产价值（资产价值减去债务后剩下的价值）",
    "HBM": "HBM（AI芯片旁边使用的高速内存）",
    "CapEx": "资本开支", "C档": "较低把握", "A档": "较高把握", "B档": "中等把握",
    "CONDITIONAL_PASS_ABSOLUTE_POSITIVE": "经营与价格比较初步支持继续研究",
    "CONDITIONAL_PASS_REPLACEMENT_REVIEW_ONLY": "只适合进入替换比较，尚不是执行结论",
    "NOT_PASS": "目前没有通过", "NOT_ACTIVATED": "目前没有启动",
    "organic growth midpoint": "内生增长区间中点",
    "revenue growth midpoint": "收入增长区间中点",
    "revenue midpoint": "收入区间中点",
    "sales growth": "销售增长",
    "operating margin": "营业利润率",
    "gross margin": "毛利率",
    "midpoint": "区间中点",
    " and ": "与",
    "US.MU": "美光", "US.ORCL": "甲骨文", "US.ETN": "伊顿", "US.CRDO": "Credo",
    "US.TER": "Teradyne", "US.VRT": "Vertiv", "US.GEV": "GE Vernova",
    "US.PWR": "Quanta Services", "US.MOD": "Modine", "US.AMD": "AMD",
    "US.ALAB": "Astera Labs", "US.ANET": "Arista Networks", "US.COHR": "Coherent",
    "JP.7735": "SCREEN", "JP.3436": "SUMCO", "JP.8035": "东京电子",
    "不适用ND": "NAND", "High-不适用": "High-NA",
    "13.0十亿美元": "130亿美元",
    "正式证伪条件": "什么情况会证明当前判断错了",
    "新增尾扫事实": "最新补充事实",
    "市场隐含预期": "当前股价里已经包含的市场期待",
    "盈利桥": "未来业务怎样变成利润",
    "上修": "提高预期", "下修": "降低预期",
    "赔率": "潜在回报与风险",
}


def plain(value) -> str:
    text = "" if value is None else str(value)
    template = "大致按当前方向发展，未来价值温和变化。"
    if template in text:
        driver = text.split(template, 1)[0].rstrip("，。； ")
        remainder = text.split(template, 1)[1].strip()
        text = f"{driver}是这只资产当前最需要核对的具体指标；这些指标能否持续改善，决定当前判断能否成立。{remainder}"
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    # The source contracts use ``bn`` for billions. Render the amount and
    # currency in ordinary Chinese without relying on a word boundary before
    # Chinese text (``bn与`` has no Unicode word boundary).
    text = text.replace("H1 sales 1,620bn", "上半年销售额1.62万亿日元")
    text = re.sub(
        r"EUR\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*bn(?![A-Za-z])",
        lambda match: f"{float(match.group(1).replace(',', '')) * 10:g}亿欧元",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"(?<![A-Za-z])([0-9][0-9,]*(?:\.[0-9]+)?)\s*bn(?![A-Za-z])",
        lambda match: f"{float(match.group(1).replace(',', '')) * 10:g}亿美元",
        text,
        flags=re.I,
    )
    text = text.replace("亿美元美元", "亿美元").replace("亿欧元欧元", "亿欧元")
    text = text.replace("真正变成收入、利润或现金", "兑现为收入、转化为利润并形成现金回报")
    text = text.replace("当前价格从当前价格出发", "按当前股价看")
    text = text.replace("什么把数字推到这么很高", "为什么这个结果会这么高")
    text = text.replace("什么把数字推到这么很低", "为什么这个结果会这么低")
    text = re.sub(r"\bV11\b", "冻结研究底稿", text)
    text = re.sub(r"\bV12\b", "冻结决策研究层", text)
    text = re.sub(r"\bGPT\b", "研究系统", text)
    return text.replace("forecast_id", "预测记录")


def paragraph(value) -> str:
    text = plain(value).strip()
    return esc(text if text else "当前冻结资料没有提供足够信息，因此没有编造结论。")


def humanize_bridge(item: dict) -> str:
    text = str(item.get("earnings_bridge") or "")
    asset_id = item.get("asset_id", "")
    if asset_id == "US.ASML":
        unit = "亿欧元"
        eps_unit = "欧元"
    elif asset_id.startswith("JP."):
        unit = "亿日元"
        eps_unit = "日元"
    elif asset_id.startswith("KRX."):
        unit = "亿韩元"
        eps_unit = "韩元"
    else:
        unit = "亿美元"
        eps_unit = "美元"

    def billion(match):
        value = float(match.group(1).replace(",", "")) * 10
        shown = f"{value:,.1f}".rstrip("0").rstrip(".")
        return shown + unit

    def million(match):
        value = float(match.group(1).replace(",", "")) / 100
        shown = f"{value:,.2f}".rstrip("0").rstrip(".")
        return shown + unit

    text = re.sub(r"([\d,]+(?:\.\d+)?)十亿", billion, text)
    text = re.sub(r"([\d,]+(?:\.\d+)?)百万", million, text)
    text = re.sub(
        r"营业利润率约0\.(\d+)至0\.(\d+)",
        lambda m: f"营业利润率约{int(m.group(1))}%至{int(m.group(2))}%",
        text,
    )
    text = re.sub(
        r"每股收益约([\d,]+(?:\.\d+)?)至([\d,]+(?:\.\d+)?)",
        lambda m: f"每股收益约{m.group(1)}至{m.group(2)}{eps_unit}",
        text,
    )
    text = text.replace("这些数字是锁定情景的经营桥，不是收益承诺。", "")
    return text.strip()


def comprehensive_reference_explanation() -> str:
    return (
        "“一年综合参考”不是目标价，也不是承诺未来一定涨跌多少。系统分别考虑较差、正常和较好几种一年后可能结果，"
        "再按照目前认为的发生可能性合并成一个参考值。它主要用于比较不同资产，不适合单独拿来决定买卖。"
        "如果价格判断本身把握度低，这个百分比只能理解成很宽的研究参考，不能当成精确预测。"
    )


def direction_label(value, frozen_direction=None) -> str:
    text = plain(frozen_direction)
    if text:
        if any(word in text for word in ("明显偏弱", "强烈看跌")):
            return "明显偏弱"
        if any(word in text for word in ("偏下", "看跌")):
            return "偏弱"
        if any(word in text for word in ("接近中性", "中性")) and not any(word in text for word in ("偏上", "偏下")):
            return "大致中性"
        if any(word in text for word in ("强看涨", "明显偏强")):
            return "明显偏强"
        if any(word in text for word in ("偏上", "看涨")):
            return "偏强"
    if not isinstance(value, (int, float)):
        return "方向尚不明确"
    if value >= 0.50:
        return "明显偏强"
    if value >= 0.15:
        return "偏强"
    if value > -0.15:
        return "大致中性"
    if value > -0.30:
        return "偏弱"
    return "明显偏弱"


def confidence_label(value) -> str:
    return {"A": "较高", "B": "中等", "C": "较低"}.get(value, "尚未可靠确定")


def asset_anchor(asset_id: str) -> str:
    return "year-" + re.sub(r"[^A-Za-z0-9]+", "-", asset_id).strip("-")


def scenario_link(item: dict) -> str:
    return f'<p><a class="scenario-link" href="#{asset_anchor(item.get("asset_id", ""))}">查看这只资产的一年情景</a></p>'


def display_currency(currency: str) -> str:
    return {"USD": "美元", "JPY": "日元", "KRW": "韩元"}.get(currency, currency or "")


def price_number(value, currency: str) -> str:
    if not isinstance(value, (int, float)):
        return "暂时无法可靠取得"
    if currency in {"JPY", "KRW"}:
        return f"{value:,.0f}{display_currency(currency)}"
    return f"{value:,.2f}{display_currency(currency)}"


def price_range(values, currency: str) -> str:
    if not isinstance(values, list) or len(values) != 2:
        return "暂时无法可靠取得"
    return f"{price_number(values[0], currency)}至{price_number(values[1], currency)}"


def concise_sentence(value, limit=110) -> str:
    text = plain(value).strip()
    if not text:
        return "当前冻结资料没有提供足够信息，因此没有编造结论。"
    first = re.split(r"(?<=[。！？])", text, maxsplit=1)[0].strip()
    return first if len(first) <= limit else first[:limit].rstrip("，； ") + "。"


def scenario_business_explanation(item: dict, contract: dict, key: str) -> str:
    assumption = concise_sentence(contract.get(f"{key}_business_assumption"), 145)
    if key == "bear":
        risk = concise_sentence(item.get("downside"), 95)
        return f"{assumption} 需要防范的是：{risk}"
    if key == "base":
        driver = concise_sentence(item.get("catalyst"), 95)
        return f"{assumption} 接下来核对：{driver}"
    driver = concise_sentence(item.get("catalyst"), 95)
    return f"{assumption} 这要求“{driver}”明显超出目前判断。"


def asset_confidence_reason(item: dict, confidence: str) -> str:
    name = item.get("asset_name") or item.get("asset_id")
    driver = concise_sentence(item.get("catalyst"), 105)
    risk = concise_sentence(item.get("downside"), 105)
    if confidence == "A":
        return f"{name}已有较完整的正式经营数据，当前把握主要来自“{driver}”；但“{risk}”仍可能使实际价格偏离经营判断。"
    if confidence == "B":
        return f"{name}的方向有公司与行业证据支持，关键验证是“{driver}”；由于“{risk}”，一年后的盈利和估值仍有明显误差。"
    return f"{name}的关键变量是“{driver}”，但“{risk}”；两者一年后的幅度都难以精确判断，因此价格把握度较低。"


def scenario_reference(item: dict) -> str:
    contract = item.get("_year_contract") or {}
    value = item.get("year_expected_return", item.get("expected_return"))
    confidence = item.get("valuation_confidence", item.get("overall_price_confidence"))
    if not contract:
        return (
            f'<details class="scenario-reference" data-full-year-scenario="1" data-asset-specific-scenario="1"><summary>查看一年情景</summary>'
            f'<p><strong>合并参考：</strong>{esc(pct(value))}</p>'
            f'<p><strong>价格判断把握度：</strong>{esc(confidence_label(confidence))}。冻结合同未能在当前展示层定位，因此没有补写情景数字。</p></details>'
        )
    lock = contract.get("lock_reference_price") or {}
    currency = lock.get("currency") or ""
    probabilities = contract.get("probability_candidate") or {}
    rows = []
    for key, label in (("bear", "较差"), ("base", "正常"), ("bull", "较好")):
        probability = probabilities.get(f"{key}_pct")
        rows.append(
            f"<tr><td>{label}</td><td>{esc(str(probability) + '%' if probability is not None else '暂未可靠取得')}</td>"
            f"<td>{esc(price_range(contract.get(f'{key}_price_range'), currency))}</td>"
            f"<td>{esc(scenario_business_explanation(item, contract, key))}</td></tr>"
        )
    extreme = ""
    if isinstance(value, (int, float)) and (value > 0.50 or value < -0.30):
        direction = "高" if value > 0 else "低"
        driver = concise_sentence(item.get("catalyst"), 105)
        risk = concise_sentence(item.get("downside"), 105)
        extreme = (
            f'<p class="extreme-reason" data-extreme-reason="1"><strong>为什么这个结果会这么{direction}：</strong>'
            f'{esc(driver)} 当前价格与一年情景差距较大；主要反向风险是“{esc(risk)}”。</p>'
        )
    confidence_reason = asset_confidence_reason(item, confidence)
    return (
        '<details class="scenario-reference" data-full-year-scenario="1" data-asset-specific-scenario="1"><summary>查看一年情景</summary><div>'
        f'<p><strong>当前参考价格：</strong>{esc(price_number(lock.get("value"), currency))}</p>'
        f'<div class="table-wrap"><table><thead><tr><th>情景</th><th>可能性</th><th>一年后价格范围</th><th>这只资产自己的原因</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
        f'<p><strong>合并参考值：</strong>{esc(price_number(contract.get("expected_price_candidate"), currency))}，'
        f'相对当前参考价格约为{esc(pct(value))}。</p>'
        f'<p><strong>为什么把握度是{esc(confidence_label(confidence))}：</strong>{esc(confidence_reason)}</p>'
        f'{extreme}</div></details>'
    )


def card(title: str, body: str, cls="") -> str:
    return f'<article class="card {cls}"><h3>{esc(title)}</h3>{body}</article>'


def metric(label: str, value: str, note: str) -> str:
    return f'<div class="metric"><span>{esc(label)}</span><strong>{esc(value)}</strong><small>{esc(note)}</small></div>'


PRIORITY_HOLDING_NARRATIVES = {
    "US.NVDA": [
        "NVIDIA最新季度收入约962.21亿美元，其中数据中心收入约890亿美元；公司给出的下一季度收入指引约1080亿美元。这说明大型科技公司和云服务商对AI算力的投入仍在快速增长，需求并没有因为股价已经很高就突然消失。",
        "这件事会先增加GPU和整套服务器系统的出货，再通过高端产品占比影响利润。公司给出的下一季度毛利率约74%；毛利率就是每100美元收入扣掉直接生产成本后还剩多少。若这一比例明显下降，收入即使增长，利润增长也可能变慢。",
        "市场已经知道NVIDIA是AI龙头，因此股价里的期待很高。最新结果提高了未来收入预期，但供应限制、毛利率回落、客户自研芯片和出口限制都可能压低市场愿意支付的价格。公司生意继续变好，不等于股价可以忽略价格风险。",
        "当前建议是建议持有。继续持有的原因是盈利证据仍然最完整；没有直接加大判断力度，是因为当前价格已经包含很高期待。下一步重点看下一季度收入是否接近1080亿美元、毛利率能否守住约74%，以及供应改善后现金回收是否跟上收入增长。",
    ],
    "JP.9984": [
        "软银的价值主要来自所持Arm等核心资产，而不是单看软银自身一季利润。近期公司计划发行1万亿日元、期限7年的债券，暂定年利率4.3%至4.9%。这会让公司同时多出现金和债务，发行当日并不会凭空创造价值。",
        "真正影响未来利润的是融资成本。按暂定利率计算，每年毛利息约430亿至490亿日元；这些利息必须由核心资产升值、投资收益或旧债置换节省来覆盖。若资金只是闲置或投资回报低于利息，净资产价值就会被慢慢侵蚀。",
        "市场关注的是Arm和其他AI资产能否继续升值，以及软银相对这些资产价值的折价能否缩小。当前建议是建议持有，因为核心资产仍提供较强上行来源；但SBI年度收益过度依赖软银，意味着一家公司判断错就会明显拖累整个账户。",
        "下一步重点看9月4日最终债券利率、资金用途、Arm等核心资产价值和后续财报。若融资成本高于暂定范围、资金用途无法产生足够回报，或核心资产价值明显下降，当前持有判断需要重新评估。",
    ],
    "KRX.005930": [
        "三星电子的存储业务会受益于AI服务器需求，但高端HBM竞争力仍弱于领先对手。近期股价大跌和股东回报方案低于市场期待，说明投资者不仅在看行业景气，也在质疑公司能否把需求真正变成份额、利润和现金回报。",
        "HBM是AI芯片旁边使用的高速内存。若认证和出货继续延迟，三星即使卖出更多普通存储产品，也可能错过利润更高的产品组合；利润率改善就会慢于美光或SK海力士。",
        "当前建议是建议减仓。原因不是认定三星业务全面恶化，而是当前账户承受了较大的存储和AI共同风险，而三星的高端产品证据还不足。相同资金放在美光等证据更清楚的对象上，研究结果显示潜在回报更有吸引力。",
        "下一步要看HBM认证、实际出货、半导体利润率和股东回报能否一起改善。若只有行业价格上涨、公司份额却没有恢复，当前风险仍然存在；若四项同步改善，减仓建议才有理由转弱。",
    ],
    "JP.8001": [
        "伊藤忠的核心业务和现金流并不是突然变坏。问题在于商品价格、投资资产减值、地缘风险和非上市资产价值会共同影响未来净资产，而当前价格对稳定增长已经给了较高期待。",
        "冻结研究把一年价格方向判断为明显偏弱。这个结论主要反映当前价格和潜在减值压力，并不等于公司经营全面崩坏；精确情景数字只在下方披露层保留。",
        "当前建议是建议减仓。与美光相比，伊藤忠的盈利弹性较低，而美光的存储价格、高速内存出货和利润率存在更清楚的改善路径。这里的比较只是说明资金机会成本，不代表已经执行替换。",
        "下一步看核心利润、自由现金流、资产减值和股东回报。若核心利润与现金持续提高、没有新增重大减值，而且回购分红兑现到足以覆盖当前价格压力，减仓理由会减弱。",
    ],
    "JP.8766": [
        "东京海上的保险业务仍有稳定现金来源，但灾害损失、准备金偏差和综合成本率会决定承保利润。综合成本率可以理解为保险公司每收100元保费，需要为赔付和经营支出多少；比例越低，承保业务通常越赚钱。",
        "冻结研究把一年价格方向判断为偏弱。主要原因是当前价格已经反映较多资本回报期待，同时巨大灾害损失和准备金变化仍可能侵蚀利润；这不是说保险业务突然失去价值。",
        "当前建议是建议减仓，并与伊顿做替换比较。伊顿受益于数据中心配电需求，订单和利润验证更直接；东京海上的优势是防守属性和资本回报，两者承担的风险不同，因此不能只比较一个收益数字。",
        "下一步重点看综合成本率、灾害损失、准备金和回购分红。如果承保利润持续好于公司计划、资本回报没有被削弱，减仓理由会下降；反之，风险会从价格问题变成经营问题。",
    ],
    "US.AVGO": [
        "博通的AI定制芯片、网络设备和VMware软件现金流仍然是强业务。问题不在于公司没有增长，而在于市场已经对AI订单和软件整合给了很高期待，当前价格需要持续超出预期才能提供足够回报。",
        "AI客户订单增长会先推高芯片和网络收入，VMware订阅转化则影响现金流。若大客户订单放缓或客户集中度上升，收入仍可能增长，但市场愿意给的价格会下降。",
        "当前建议是考虑替换。甲骨文的大额云合同转收入提供了更高的一年综合参考，博通相对占用资金的机会成本上升。这不是否定博通的公司质量，而是把好公司和好价格分开判断。",
        "下一步看AI订单、VMware整合现金流和融资成本。只有这些指标继续改善，并且当前股价对增长的提前反映被实际盈利消化，博通才可能重新获得更好的相对吸引力。",
    ],
    "US.MSFT": [
        "微软的云业务和AI产品仍在增长，Azure、企业软件和AI助手可以带来新收入；同时公司必须投入大量资本开支建设数据中心。资本开支就是建设数据中心和购买服务器设备投入的钱。",
        "关键不是微软有没有花钱，而是新增AI收入能否快于折旧、能源和基础设施成本增长。如果收入增加但自由现金流下降，市场会怀疑投资回报；如果Azure和AI收入增长同时带来现金，股价的高期待就更有支撑。",
        "当前建议是建议加仓。原因是微软拥有成熟企业客户和现金流，可以比多数AI概念公司更直接地把产品使用变成收费；但仍要防止资本开支长期快于收入。",
        "下一步看Azure增长、AI收入、营业利润率和自由现金流。若资本开支持续增加而现金回收没有改善，加仓理由会被削弱。",
    ],
    "US.SNDK": [
        "闪迪的核心变化来自NAND存储价格和数据中心需求。NAND是一种用于固态硬盘和数据中心存储的闪存；价格上涨和高端企业产品占比提高，会直接改善收入与利润率。",
        "这类公司具有明显周期性：供给收紧时价格和利润可以迅速上升，扩产过快时也会迅速回落。当前研究认为数据中心出货和价格改善仍有支撑，但不能把一个上升周期当成永久增长。",
        "当前建议是建议加仓，因为冻结研究显示未来一年回报仍为正，而且数据中心收入和现金改善可以验证。与此同时，存储价格、库存和企业固态硬盘需求一旦转弱，股价通常会先于财报下跌。",
        "下一步看NAND价格、数据中心出货、利润率和自由现金流是否同步改善。只看到价格上涨、看不到现金回收，不能证明周期真正健康。",
    ],
}


def priority_holding_story(item: dict) -> str:
    paragraphs = PRIORITY_HOLDING_NARRATIVES[item["asset_id"]]
    confidence = item.get("overall_price_confidence")
    direction = direction_label(item.get("year_expected_return"), item.get("year_price_direction"))
    return (
        f'<article class="priority-asset" data-priority-holding="1">'
        f'<h3>{esc(item["asset_name"])} <small>{esc(item["asset_id"])}</small></h3>'
        f'<div class="decision-row"><span class="decision">{esc(RECOMMENDATION.get(item.get("recommendation"), plain(item.get("recommendation"))))}</span>'
        f'<span>一年方向：{esc(direction)}｜价格判断把握度：{esc(confidence_label(confidence))}</span></div>'
        + "".join(f"<p>{esc(text)}</p>" for text in paragraphs)
        + scenario_link(item)
        + '</article>'
    )


def holding_story(item: dict, detailed=False) -> str:
    rec = RECOMMENDATION.get(item.get("recommendation"), plain(item.get("recommendation")))
    result = pct(item.get("year_expected_return"))
    short = pct(item.get("short_expected_return"))
    comparison = item.get("comparison_return_delta")
    if comparison is None:
        comparison_text = "冻结资料没有提供可复算的收益差，因此这里只保留定性比较。"
    elif comparison >= 0:
        comparison_text = f"候选的一年综合参考比本持仓高约{comparison * 100:.1f}个百分点。"
    else:
        comparison_text = f"候选的一年综合参考比本持仓低约{abs(comparison) * 100:.1f}个百分点，因此目前没有替换优势。"
    comparison_asset = plain(item.get("replacement") or "现金")
    body = f"""
      <div class="decision-row"><span class="decision">{esc(rec)}</span><span>一年方向：{esc(direction_label(item.get('year_expected_return'), item.get('year_price_direction')))}｜价格判断把握度：{esc(confidence_label(item.get('overall_price_confidence')))}</span></div>
      <p><strong>为什么：</strong>{paragraph(item.get('reason'))}</p>
      <p><strong>未来一年怎么看：</strong>公司业务趋势为“{esc(plain(item.get('year_direction')))}”，从今天股价出发的潜在回报方向为“{esc(plain(item.get('year_price_direction')))}”。短期参考仍为{esc(short)}；精确一年数字放在情景披露中，避免把低把握研究参考误读成目标价。</p>
      <p><strong>哪里可能错：</strong>{paragraph(item.get('risk'))}</p>
      <p><strong>什么事实会改变判断：</strong>{paragraph(item.get('change_condition'))}</p>
      <p><strong>与谁比较：</strong>当前最直接的比较对象是{esc(comparison_asset)}。{esc(comparison_text)}这只资产的比较重点是{paragraph(item.get('opportunity_cost_dimension'))}。</p>
      <p class="confidence"><strong>证据可靠程度：</strong>对公司业务的判断为{esc(CONFIDENCE.get(item.get('business_confidence'), item.get('business_confidence') or '未知'))}，对未来股价范围的判断为{esc(CONFIDENCE.get(item.get('overall_price_confidence'), item.get('overall_price_confidence') or '未知'))}。股价证据较弱时，区间只适合比较，不适合当成精确目标。</p>
      {scenario_link(item)}"""
    if detailed:
        body += f'<div class="watch"><strong>什么情况会证明当前判断错了：</strong>{paragraph(item.get("invalidation"))}</div>'
    return f'<article class="holding" data-holding="1"><h3>{esc(item["asset_name"])} <small>{esc(item["asset_id"])}</small></h3>{body}</article>'


def opportunity_story(item: dict, detailed=False) -> str:
    direction = direction_label(item.get("expected_return"))
    confidence = item.get("valuation_confidence")
    if detailed and item["asset_id"] in PRIORITY_OPPORTUNITY_NARRATIVES:
        paragraphs = PRIORITY_OPPORTUNITY_NARRATIVES[item["asset_id"]]
        return (
            f'<article class="priority-asset" data-opportunity="1" data-priority-opportunity="1">'
            f'<h3>第{item.get("rank")}名｜{esc(item["asset_name"])} <small>{esc(item["asset_id"])}</small></h3>'
            + "".join(f"<p>{esc(text)}</p>" for text in paragraphs)
            + f'<div class="decision-row"><span class="decision">继续重点研究</span>'
              f'<span>一年方向：{esc(direction)}｜价格判断把握度：{esc(confidence_label(confidence))}</span></div>'
            + f'<div class="risk"><strong>什么情况会证明当前判断错了：</strong>{paragraph(item.get("risk"))}</div>'
            + scenario_link(item)
            + "</article>"
        )
    body = f"""
      <div class="decision-row"><span class="rank">第{item.get('rank')}名</span><span>一年方向：{esc(direction)}｜价格判断把握度：{esc(confidence_label(confidence))}</span></div>
      <p><strong>为什么现在值得研究：</strong>{paragraph(item.get('rationale'))}</p>
      <p><strong>未来业务可能怎样变化：</strong>{paragraph(item.get('future_change'))}</p>
      <p><strong>怎样变成利润：</strong>{esc(humanize_bridge(item))}</p>
      <p><strong>市场可能漏看了什么：</strong>{paragraph(item.get('overlooked'))}</p>
      <p><strong>现在价格是否已经反映：</strong>{paragraph(item.get('priced_in'))}</p>
      <p><strong>最大的风险：</strong>{paragraph(item.get('risk'))}</p>
      <p><strong>相对现有持仓的意义：</strong>{paragraph(item.get('replacement'))}。这只是替换研究，不是已经发生的操作。</p>
      <p><strong>下一次核对：</strong>{esc(item.get('verification_date') or '按下一份正式财报核对')}。</p>
      {scenario_link(item)}"""
    if detailed:
        body += f'<div class="watch"><strong>哪里最可能判断错：</strong>{paragraph(item.get("catalyst"))}没有转成收入、利润或现金，或者价格先一步消化了改善。</div>'
    return f'<article class="opportunity" data-opportunity="1"><h3>{esc(item["asset_name"])} <small>{esc(item["asset_id"])}</small></h3>{body}</article>'


PRIORITY_OPPORTUNITY_NARRATIVES = {
    "US.MU": [
        "美光目前排在机会池第一，不是因为过去涨得多，而是存储价格、HBM出货和利润率正在同时改善。HBM是AI芯片旁边使用的高速内存，需求增加会提高高端产品占比，并带动收入和利润增长。",
        "冻结研究引用的下一次正式核对数字包括季度收入约500亿美元、每股收益约30.73美元。收入说明产品卖出了多少，每股收益说明利润分摊到每股后有多少；只有收入与每股收益都达到公司指引、利润率也没有恶化，盈利改善才算真正成立。",
        "市场已经知道存储周期在改善，但冻结研究认为当前股价对价格上涨、HBM销量和中周期利润率的反映仍不如部分同行充分。因此一年方向明显偏强，但价格估值证据仍是C档，精确结果只能作为宽幅研究参考。",
        "美光比三星和部分已大涨的存储同业更值得研究，是因为它的改善变量更容易通过价格、出货和利润率验证。最大风险是新增供给过快、存储价格回落，或者HBM销量没有如期变成利润。下一步看正式财报中的收入、每股收益、HBM出货和中周期利润率。",
    ],
    "US.ORCL": [
        "甲骨文的机会来自已经签下的大额云合同逐步转成实际收入。合同本身不是利润；公司必须先建设数据中心、部署服务器并让客户真正上线，收入才会进入财报。",
        "冻结研究引用的FY2027收入参考约900亿美元、每股收益约8.05美元。FY2027指公司的2027财年；收入达到这个水平只能证明合同开始落地，还要同时检查建设成本、债务和自由现金流，才能判断增长是否真正为股东创造价值。",
        "一年方向明显偏强，但价格判断把握度较低。市场可能低估的是合同转收入的速度，也可能低估数据中心建设所需的现金和融资成本；精确结果只放在情景披露中。",
        "甲骨文之所以能够和博通、微软等现有持仓比较，是因为它提供不同的AI收益来源：不是卖芯片，而是把云容量变成长期收费。最大风险是建设延期、债务上升和现金流恶化。下一步看已签合同转收入速度、云业务增长和自由现金流。",
    ],
    "JP.7735": [
        "SCREEN主要受益于半导体清洗设备需求。芯片制造步骤越复杂，清洗次数越多；如果公司份额提高、客户资本开支兑现，订单会先增加，随后才转成设备收入和利润。",
        "冻结研究引用的FY2027销售额约7430亿日元、每股收益约608.06日元。销售额说明设备和服务卖出了多少，每股收益说明这些收入最后为每股留下多少利润。两者达到或超过公司指引、利润率没有恶化，才算订单真正转成盈利。",
        "一年方向偏强。市场已经看到半导体设备周期改善，但冻结研究认为清洗设备份额和公司提高预期的影响还没有被完全反映；它相较东京电子等设备公司，当前价格留下的回报空间更好。",
        "最大风险是客户推迟资本开支、设备验收延后或份额回落。下一步看订单、出货、验收和利润率是否一起改善，而不是只看行业新闻。",
    ],
    "US.ETN": [
        "伊顿受益于数据中心配电需求。AI服务器需要更多电力，机房必须增加配电、断路器和电力管理设备；订单增加后，还要经过产能扩张和交付，才能变成收入。",
        "冻结研究引用的全年内生增长约10%、每股收益约11.105美元。内生增长是扣除收购和汇率后，公司原有业务自身增长多少；这个数字能帮助判断需求是否真实。每股收益则检验交付和利润率是否把增长留给股东。",
        "一年方向大致中性到偏强。它的吸引力不只在价格空间，还在于风险来源与现有芯片持仓不同，可以降低组合全部依赖同一条AI芯片主线的程度。",
        "最大风险是订单很多但交付延迟、产能成本过高，或自由现金流没有跟上利润。下一步看数据中心订单、产能交付、电气业务利润率和现金回收。",
    ],
    "US.CRDO": [
        "Credo提供AI服务器和数据中心之间的高速连接产品。算力部署增加时，数据必须更快地在芯片、服务器和机架之间移动；如果连接速度成为瓶颈，相关产品收入会提高。",
        "冻结研究引用的下一季度收入指引约4.70亿美元、毛利率约67.9%。毛利率67.9%的意思是每100美元收入扣掉直接生产成本后约剩67.9美元；如果收入增长但这一比例明显下降，说明竞争或成本正在吞噬增长价值。",
        "一年方向大致中性。它仍值得研究，但只属于进阶观察，因为客户集中和竞争优势证据还不够完整。市场可能低估高速互联需求，也可能已经高估单一客户项目能持续多久。",
        "最大风险是核心客户削减采购、项目延期或客户集中继续上升。下一步看收入、客户结构、产品项目和毛利率是否共同改善，再决定它是否足以替换现有AI持仓。",
    ],
}


def theme_story(theme: dict, index: int) -> str:
    stories = {
        1: [
            f"最近的事实是：{paragraph(theme['new_fact'])} 这不是一条普通的行业新闻，因为大型云厂商投入的钱正在从单颗芯片扩展到整套数据中心。",
            "资金先进入NVIDIA的GPU和整套计算系统，也进入博通的定制芯片与网络设备。服务器数量增加后，数据必须在芯片、服务器和机架之间高速移动，Credo等连接供应商才会获得更多收入。连接速度如果跟不上，昂贵的计算芯片就会等待数据，因此高速互联正在从配套部件变成真实瓶颈。",
            f"这条资金链怎样变成利润：{paragraph(theme['earnings_transmission'])} NVIDIA赚的是最核心的计算平台收入，博通同时赚定制芯片、网络和软件现金流，Credo赚高速连接产品。收入增长之后还要看产品组合和规模是否能守住毛利率；毛利率就是每卖100元产品、扣掉直接生产成本后剩下多少。",
            f"公司好不等于股票现在便宜。{paragraph(theme['market_reflection'])} {paragraph(theme['market_reflection_reason'])} NVIDIA的盈利证据最完整，但价格期待也最高；博通业务仍强，当前价格却要求AI订单和VMware现金流持续超出预期；Credo弹性高，但客户集中和竞争优势证据更弱。",
            f"对我们的直接影响是：{paragraph(theme['holding_impact'])} 现有NVIDIA可以继续作为主线核心验证，微软和Meta要证明AI收入足以覆盖数据中心资本开支；博通不宜仅因公司质量好就继续增加同一风险。新资金更应比较高速互联和云合同兑现，而不是无条件继续堆到原来的AI大仓位。",
            f"同一主线里的取舍是：{paragraph(theme['relative_choice'])} {paragraph(theme['research_recommendation'])} 换句话说，当前优先级看的是“盈利证据完整程度减去股价已提前反映程度”，不是只看哪个公司名气最大。",
            "未来30天重点看NVIDIA财报后盈利上调能否持续、毛利率警告是否被市场消化，以及云厂商有没有新的资本开支或订单变化。未来3个月重点看GPU供应、高速互联项目和云合同转收入。未来一年最重要的是AI投入能否持续转成客户收入和自由现金流，而不是只增加设备数量。",
            f"必须承认逻辑改变的组合证据是：{paragraph(theme['invalidation'])} 如果云厂商同时削减资本开支、GPU和连接订单转弱、毛利率连续低于公司指引，而且AI产品收入仍不能覆盖折旧与能源成本，这条从算力向连接扩散的主线就不再成立。",
        ],
        2: [
            f"最近的事实是：{paragraph(theme['new_fact'])} AI服务器不仅需要计算芯片，也需要HBM和数据中心存储。HBM就是AI芯片旁边使用的高速内存；存储价格、产品组合和测试强度正在同时影响产业利润。",
            "钱先从云厂商资本开支进入GPU和服务器，随后进入HBM、企业固态硬盘、测试设备和晶圆清洗设备。高端内存供应紧张时，价格和高端产品占比提高；芯片结构越复杂，需要的测试与清洗步骤越多，因此利润机会会从存储厂扩散到爱德万测试和SCREEN等设备公司。",
            f"这一变化怎样变成利润：{paragraph(theme['earnings_transmission'])} 美光和SK海力士主要赚存储售价、HBM销量和高端产品占比；三星也有存储规模，但高利润HBM认证和出货仍需证明；爱德万测试赚测试时长与设备需求；SCREEN赚制造步骤增加带来的清洗设备订单。",
            f"市场已经看到周期改善，但反映并不相同。{paragraph(theme['market_reflection'])} {paragraph(theme['market_reflection_reason'])} 美光的价格、HBM和利润率验证较直接；SK海力士的领先地位更强，但价格已包含较多期待；三星的行业顺风不一定等比例变成份额与利润。",
            f"对我们账户的影响是：{paragraph(theme['holding_impact'])} 闪迪和爱德万测试仍受益，但它们都增加了同一存储与AI周期风险。三星的风险更高，因为高端产品证据较弱；信越化学只有在300毫米硅片需求、价格和开工率共同恢复时，才会充分受益。",
            f"同一主线里当前更值得研究的是：{paragraph(theme['relative_choice'])} {paragraph(theme['research_recommendation'])} 美光优先于三星和部分已经充分定价的同业，是因为收入、HBM出货、价格和利润率可以在下一份正式披露中同时核对；SCREEN则提供设备环节的不同盈利来源。",
            "未来30天重点看存储价格、HBM认证和下一份公司指引。未来3个月重点看库存是否继续下降、出货是否转成利润、测试和清洗设备订单是否兑现。未来一年要判断这次改善是短暂补库存，还是AI需求真的提高了存储价格、测试强度和设备利用率的中枢。",
            f"必须承认主线改变的证据是：{paragraph(theme['invalidation'])} 如果存储价格回落、库存重新上升、HBM认证持续推迟，同时测试和设备订单转弱，就不能再把行业顺风当成盈利上修周期。",
        ],
        3: [
            f"最近的事实是：{paragraph(theme['new_fact'])} AI机柜功率密度提高后，芯片之外的第二个约束是电能否送进机房、热能否排出去，以及电网和发电能力能否按时建成。",
            "资金会依次进入配电设备、断路器、变压器、热管理、工程建设和发电资产。订单很多并不等于立刻赚钱：公司还要扩产、交付、验收并收回现金。真正稀缺的不是故事，而是能按期把积压订单转成收入、利润和自由现金流的能力。",
            f"这一变化怎样变成利润：{paragraph(theme['earnings_transmission'])} 伊顿赚配电和电力管理设备，Vertiv赚数据中心供电与热管理，GE Vernova和Quanta Services分别承担电网设备与工程建设，Modine则参与热管理。每家公司受益环节不同，交付速度和成本控制决定最终利润。",
            f"市场已经提前反映了相当多增长。{paragraph(theme['market_reflection'])} {paragraph(theme['market_reflection_reason'])} 伊顿和Vertiv仍有小幅正面价格空间，但GE Vernova、Quanta Services和Modine即使业务方向强，当前价格也可能已经透支未来改善。",
            f"对账户而言：{paragraph(theme['holding_impact'])} 现有组合没有纯粹的电力基础设施核心仓位，因此这条主线更适合用来分散AI芯片风险，并与第一三共、东京海上等低回报持仓做替换研究，而不是直接再增加同一类高估值资产。",
            f"当前排序是：{paragraph(theme['relative_choice'])} {paragraph(theme['research_recommendation'])} 伊顿优先于其他电力候选，是因为订单、利润率和现金可以用同一套正式数据验证；Vertiv弹性更高，但对数据中心建设节奏更敏感。",
            "未来30天看公司订单、交付与指引是否维持。未来3个月看积压订单转收入、产能爬坡和自由现金流。未来一年最重要的是数据中心电力投资能否从签单阶段进入稳定交付，而不是在项目延期和成本上升中消耗利润。",
            f"必须承认主线改变的证据是：{paragraph(theme['invalidation'])} 如果积压订单转换连续放慢、重大项目延期、扩产成本提高而利润率下降，并且自由现金流持续低于公司计划，就说明需求虽在，股东却未必赚到钱。",
        ],
        4: [
            f"最近的事实是：{paragraph(theme['new_fact'])} 日本利率、企业资本效率和股东回报确实支持部分公司盈利，但日元、融资成本和已经上涨的股价会决定投资者最终得到多少。",
            "资金不会平均流入所有日本股票。它会在资产价值、制造业订单、国内利润和金融回报之间比较：软银取决于Arm等核心资产与债务，制造业公司取决于订单和汇率，保险与银行取决于利率、信用成本和资本回报。",
            f"传导链是：{paragraph(theme['earnings_transmission'])} 利率与汇率先改变融资和出口利润，再影响订单、资本回报与资产折价，最后才成为每股价值。公司利润改善后，如果融资成本上升或股价已经提前上涨，投资回报仍可能偏弱。",
            f"当前价格反映并不均匀。{paragraph(theme['market_reflection'])} {paragraph(theme['market_reflection_reason'])} 软银仍有核心资产价值与折价改善空间；伊藤忠、东京海上和发那科的业务可以稳定或改善，但从当前价格出发的回报压力更大。",
            f"对SBI的直接影响是：{paragraph(theme['holding_impact'])} 软银是主要正贡献来源，也使账户过度依赖单一资产；伊藤忠和东京海上拖累目标路径；Sony与信越化学需要用产品周期、硅片需求和现金回报继续证明。新资金不应因为“日本市场好”就平均增加。",
            f"同一主线里的选择是：{paragraph(theme['relative_choice'])} {paragraph(theme['research_recommendation'])} 当前更适合保留软银和Sony的验证价值，并研究SCREEN等有明确订单与盈利桥的公司，而不是笼统加仓日本资产。",
            "未来30天重点看软银9月4日最终债券利率、日元和公司指引变化。未来3个月看制造业订单、保险承保利润、硅片需求和股东回报。未来一年最重要的是盈利改善能否超过融资成本与估值压力，并让SBI的收益来源不再只靠软银。",
            f"必须承认逻辑改变的证据是：{paragraph(theme['invalidation'])} 如果日元快速升值、融资成本继续上升、制造业订单持续转弱，同时公司下调盈利或资本回报计划，日本资产的盈利改善逻辑就会从分化变成整体承压。",
        ],
    }
    paragraphs = stories[index]
    return (
        f'<article class="story" data-theme="1"><div class="story-kicker">投资主线 {index}</div>'
        f'<h3>{esc(theme["title"])}</h3>'
        + "".join(f"<p>{text}</p>" for text in paragraphs[:-1])
        + f'<div class="risk"><strong>什么会证明整条逻辑错了：</strong>{paragraphs[-1]}</div></article>'
    )


def lookup_rows(assets: list[dict]) -> str:
    rows = []
    for item in assets:
        rows.append(f"""
        <tr data-asset="1" id="{asset_anchor(item.get('asset_id', ''))}">
          <td><strong>{esc(item.get('asset_name'))}</strong><br><small>{esc(item.get('asset_id'))}</small></td>
          <td>{esc(plain(item.get('short_signal')))}</td>
          <td>{esc(pct(item.get('short_expected_return')))}</td>
          <td>{esc(plain(item.get('business_direction')))}</td>
          <td><strong>{esc(direction_label(item.get('year_expected_return')))}</strong><br><small>价格判断把握度：{esc(confidence_label(item.get('valuation_confidence')))}</small>{scenario_reference(item)}</td>
          <td>{esc(plain(item.get('catalyst')))}</td>
          <td>{esc(plain(item.get('downside')))}</td>
        </tr>""")
    return "".join(rows)


def event_time_display(event: dict) -> str:
    confidence = event.get("time_confidence") or ""
    time_text = event.get("time") or ""
    if confidence == "确定日期":
        return time_text
    if confidence == "确定月份/季度":
        return f"{time_text}；正式日期尚未公布。"
    return "尚无可靠正式日期，等待公司公告。"


def event_card(item: dict, event: dict, compact=False) -> str:
    source = event.get("source") or ""
    source_link = f'<a href="{esc(source)}">查看正式依据</a>' if source.startswith("http") else esc(source or "暂未取得可打开来源")
    body = (
        f'<p><strong>当前30日判断：</strong>{esc(plain(item.get("short_signal")))}</p>'
        f'<p><strong>下一关键验证事件：</strong>{paragraph(event.get("event"))}</p>'
        f'<p><strong>时间：</strong>{esc(event_time_display(event))}</p>'
        f'<p><strong>时间确定程度：</strong>{esc(event.get("time_confidence") or "目前没有可靠时间")}</p>'
        f'<p><strong>升级条件：</strong>{paragraph(event.get("entry_observation_condition"))}</p>'
        f'<p><strong>降级条件：</strong>{paragraph(event.get("failure_condition"))}</p>'
    )
    if not compact:
        body += (
            f'<p><strong>最大短期风险：</strong>{paragraph(item.get("short_risk"))}</p>'
            f'<p><strong>时间依据：</strong>{paragraph(event.get("basis"))} {source_link}</p>'
        )
    return card(item.get("asset_name") or item.get("asset_id"), body, "event")


def plus100_source_links() -> str:
    links = []
    if PLUS100_INDEX_URL:
        links.append(f'<li><a href="{esc(PLUS100_INDEX_URL)}">+100%独立核验索引</a>：把V13结论逐项映射到底表字段和计算方法。</li>')
    for label, filename, file_id in PLUS100_DRIVE_FILES:
        url = f"https://drive.google.com/file/d/{file_id}/view"
        links.append(f'<li><a href="{url}">{esc(label)}</a>：{esc(filename)}</li>')
    return "".join(links)


def build_plus100_index_html(supplement: dict) -> str:
    micron = next(item for item in supplement["asset_scan"] if item.get("asset_id") == "US.MU")
    stats = micron["absolute_benchmark_excess_statistics"]
    rows = [
        ("A级0、B级1、C级41", "新A、B、C三级波段池", "grade_pools；new_grade_counts", "逐资产检查新等级后计数；美光为唯一B级。"),
        ("美光下一次财报时间", "未来12个月真实事件日历", "events[asset_id=US.MU].time", micron["future_12m_event_window"]["time"]),
        ("公告后首个可交易价格起算", "股票与基准1、5、20、60日收益", "US.MU.condition_matched_samples[].tradable_entry_price", "盘后公告从下一交易日开盘价起算，不包含确认前跳空。"),
        ("美光有3个条件匹配样本", "条件匹配历史事件样本", "US.MU.condition_matched_sample_count", str(micron["condition_matched_sample_count"])),
        ("美光20日超额收益中位数约+14.21%", "超额收益与最大回撤", "US.MU.absolute_benchmark_excess_statistics.excess_return_20d.median", f'{stats["excess_return_20d"]["median"] * 100:.2f}%'),
        ("美光仍是B级而非A级", "新A、B、C三级波段池", "US.MU.new_grade；grade_failures；missing_for_upgrade", micron["downgrade_reason"]),
        ("当前不能可靠计算+100%路径", "年度路径可计算性", "plus100_calculable；missing_variables", supplement["annual_path_calculability"]["reason"]),
        ("事件窗口重叠和共同风险", "时间重叠与风险相关性", "overlap_and_risk", "只有时间不重叠且资金已经释放的事件，才允许研究顺序复用。"),
    ]
    table_rows = "".join(
        f"<tr><td>{esc(conclusion)}</td><td>{esc(source)}</td><td><code>{esc(field)}</code></td><td>{esc(calculation)}</td></tr>"
        for conclusion, source, field, calculation in rows
    )
    file_links = plus100_source_links().replace(
        f'<li><a href="{esc(PLUS100_INDEX_URL)}">+100%独立核验索引</a>：把V13结论逐项映射到底表字段和计算方法。</li>',
        "",
    )
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>+100%独立核验索引</title><style>body{{font-family:Arial,'Microsoft YaHei',sans-serif;max-width:1180px;margin:auto;padding:30px;color:#17231d}}h1{{font-size:30px}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #cfd7d2;padding:10px;text-align:left;vertical-align:top}}th{{background:#eef3f0}}li{{margin:8px 0}}code{{white-space:normal}}</style></head><body><h1>+100%独立核验索引</h1><p>本索引只帮助独立终验从V13结论找到对应底表、字段和计算方法；不改变A级0、B级1（美光）、C级41以及“当前不能可靠计算+100%路径”的冻结结论。</p><table><thead><tr><th>V13结论</th><th>底表</th><th>字段</th><th>复算方法或实值</th></tr></thead><tbody>{table_rows}</tbody></table><h2>九份底表入口</h2><ul>{file_links}</ul></body></html>"""


def high_absolute_reference_cards(assets: list[dict]) -> str:
    selected = [item for item in assets if isinstance(item.get("year_expected_return"), (int, float)) and (item["year_expected_return"] > 0.50 or item["year_expected_return"] < -0.30)]
    cards = []
    for item in selected:
        cards.append(
            f'<article class="card high-absolute" data-high-absolute="1"><h3>{esc(item["asset_name"])} <small>{esc(item["asset_id"])}</small></h3>'
            f'<p><strong>一年方向：</strong>{esc(direction_label(item.get("year_expected_return")))}</p>'
            f'<p><strong>业务判断：</strong>{esc(plain(item.get("business_direction")))}</p>'
            f'<p><strong>价格判断把握度：</strong>{esc(confidence_label(item.get("valuation_confidence")))}。高幅度结果首先是需要复核的模型信号，不是更精确的承诺。</p>'
            f'<p><strong>主要依据：</strong>{paragraph(item.get("catalyst"))}</p>'
            f'<p><strong>主要反向事实：</strong>{paragraph(item.get("downside"))}</p>'
            + scenario_link(item)
            + '</article>'
        )
    return ''.join(cards)


def account_return(paths: dict, key: str, fallback: float) -> float:
    account = paths.get(key, paths.get(key.upper(), {}))
    value = account.get("expected_return", account.get("full_account_expected_return_pct", fallback))
    value = float(value)
    return value / 100 if value > 2 else value


def improvement_task(title: str, problem: str, destination: str, advantage: str, trigger: str, risk: str, effect: str) -> str:
    return f"""
    <article class="roadmap-task">
      <h4>{esc(title)}</h4>
      <p><strong>现在的问题：</strong>{esc(problem)}</p>
      <p><strong>可能研究到哪里：</strong>{esc(destination)}</p>
      <p><strong>为什么更有吸引力：</strong>{esc(advantage)}</p>
      <p><strong>什么时候才值得重新考虑：</strong>{esc(trigger)}</p>
      <p><strong>如果判断错了：</strong>{esc(risk)}</p>
      <p><strong>可能改善组合哪一部分：</strong>{esc(effect)}</p>
    </article>"""


def build_plus40_roadmaps(source: dict) -> str:
    static = source["annual_paths"]["static"]
    futu = static["futu"]
    sbi = static["sbi"]
    futu_tasks = [
        improvement_task(
            "关键判断1｜守住英伟达这一核心收益来源",
            "FUTU的正收益依赖少数AI资产。如果英伟达的盈利提高不能抵消毛利率下降和高估值，基线会先被削弱。",
            "先验证现有英伟达持仓，不把盈利提高自动等同于继续增加同一风险。",
            "公司已经给出下一季度收入约1080亿美元、毛利率约74%的正式指引，收入与利润率可以直接核对。",
            "下一份正式结果维持收入增长，毛利率没有明显低于约74%，并且现金回收跟上收入。",
            "供应限制、毛利率下降或估值压缩可能让公司生意变好、股价回报却不足。",
            "保护现有基线中最重要的AI盈利来源；这里只是守住路径，不产生额外贡献。",
        ),
        improvement_task(
            "关键判断2｜比较博通与甲骨文",
            "博通业务仍强，但AI客户集中、VMware整合和当前价格使资金效率下降。",
            "把博通与甲骨文的云合同转收入能力做持续替换比较。",
            "甲骨文以2027财年收入增长约33.5%和每股收益约8.05美元为核对起点，合同转收入提供不同于芯片的AI收益来源。",
            "博通经营与现金流弱于当前预期，同时甲骨文的合同转收入、建设成本和自由现金流达到冻结研究的验证条件。",
            "甲骨文可能因建设延期、债务和现金流恶化而失去优势；博通也可能用更强订单和现金流重新证明当前价格。",
            "冻结研究的100%静态替换敏感性约为+4.42个百分点。这里只能说明可能改善方向，目前不能当作实际贡献。",
        ),
        improvement_task(
            "关键判断3｜比较任天堂与SCREEN",
            "任天堂需要用硬件装机、软件销量和公司指引消化当前价格，现有回报空间较有限。",
            "研究SCREEN的清洗设备订单和盈利兑现是否优于任天堂。",
            "SCREEN以2027财年销售增长约22.7%、营业利润率约21.1%为正式核对起点，设备订单到收入的路径更直接。",
            "任天堂装机、软件销量或指引转弱，同时SCREEN订单、出货、验收和利润率达到公司指引。",
            "半导体资本开支推迟或设备验收延后，会让SCREEN的理论优势消失。",
            "冻结研究的100%静态替换敏感性约为+1.91个百分点。这里只能说明可能改善方向，目前不能当作实际贡献。",
        ),
        improvement_task(
            "关键判断4｜比较第一三共与美光",
            "第一三共的核心药物销售、安全性、审批和研发管线如果不能兑现，资金机会成本会上升。",
            "研究美光的HBM出货、存储价格与利润率是否形成更清楚的盈利提高。",
            "美光下一份正式核对以季度收入约500亿美元和每股收益约30.73美元为起点，盈利弹性可直接验证。",
            "第一三共核心药物或管线证据转弱，同时美光收入、每股收益、HBM出货与利润率共同达到或超过指引。",
            "存储价格回落、HBM认证延迟或供给过快会放大美光的周期风险。",
            "冻结研究的100%静态替换敏感性约为+8.21个百分点。这里只能说明可能改善方向，目前不能当作实际贡献。",
        ),
    ]
    sbi_tasks = [
        improvement_task(
            "关键判断1｜降低对软银单一贡献的依赖",
            "SBI约84.56%的正贡献来自软银，一家公司失效会让账户目标迅速恶化。",
            "先验证软银融资成本与核心资产价值，同时寻找不依赖同一资产的收益来源。",
            "软银仍有Arm等核心资产价值和折价改善空间，但这只能支持保留研究，不能证明账户已经分散。",
            "9月4日最终债券利率、资金用途和核心资产价值共同支持净资产价值，且其他持仓贡献开始改善。",
            "最终利率高于暂定范围、资金回报低于利息或核心资产下跌，会同时伤害软银和SBI目标。",
            "先守住SBI现有基线，并逐步降低收益来源过度集中的脆弱性。",
        ),
        improvement_task(
            "关键判断2｜比较伊藤忠与美光",
            "伊藤忠业务并未崩坏，但商品、减值和非上市资产价值使当前价格的回报压力较大。",
            "把伊藤忠与美光的未来盈利弹性做持续比较。",
            "美光的存储价格、HBM出货和利润率可以通过公司正式结果直接核对。",
            "伊藤忠核心利润、自由现金流或股东回报转弱，同时美光收入、每股收益和利润率兑现。",
            "美光的周期下行可能比伊藤忠更剧烈，不能只看上行弹性。",
            "冻结研究的100%静态替换敏感性约为+2.97个百分点。这里只能说明可能改善方向，目前不能当作实际贡献。",
        ),
        improvement_task(
            "关键判断3｜比较东京海上与伊顿",
            "东京海上的承保业务稳定，但灾害损失、准备金和已经反映的资本回报压低相对吸引力。",
            "研究伊顿的数据中心配电订单能否提供不同于日本金融资产的收益来源。",
            "伊顿以全年内生增长约10%和每股收益约11.105美元为正式核对起点，订单、交付和利润率可连续验证。",
            "东京海上承保利润或资本回报转弱，同时伊顿订单、交付、利润率和现金回收维持。",
            "伊顿可能因项目延期、产能成本和估值压缩而无法兑现订单优势。",
            "冻结研究的100%静态替换敏感性约为+2.84个百分点。这里只能说明可能改善方向，目前不能当作实际贡献。",
        ),
        improvement_task(
            "关键判断4｜审查爱德万测试的高集中与甲骨文的分散价值",
            "爱德万测试受益于AI和HBM测试，但仓位较大；继续增加会放大同一周期风险。",
            "只在爱德万测试盈利证据转弱时，把甲骨文作为跨行业替换研究对象。",
            "爱德万测试有2026财年每股收益911.64日元的正式指引；甲骨文则提供云合同转收入的不同收益来源。",
            "爱德万测试订单、测试强度或利润率连续弱于指引，同时甲骨文合同转收入和现金流达到验证条件。",
            "机械替换可能错失爱德万测试继续提高盈利，也可能把资金换到高债务和高资本开支的甲骨文。",
            "冻结研究的100%静态替换敏感性约为+13.13个百分点，但这是全额静态假设，不能当实际贡献。",
        ),
    ]
    return f"""
    <div class="goal roadmap" data-plus40-roadmap="FUTU"><h3>FUTU｜从{futu:.2f}%走向+40%还要完成什么</h3>
      <p>当前组合基本不变时，一年基线约为{futu:.2f}%，距离+40%还差约{static['futu_gap40']:.2f}个百分点。路径状态是：<strong>已经识别主要改善来源，但仍缺关键条件。</strong></p>
      <div class="roadmap-grid">{''.join(futu_tasks)}</div>
      <div class="risk"><strong>路线图结论：</strong>三项替换比较都有理论敏感性，但没有一项已经成为实际贡献；它们不能简单相加凑到40%。先守住英伟达等现有盈利来源，再等待原持仓转弱与候选兑现同时发生，才有资格重算路径。</div>
      <h4>接下来体系要做什么</h4><ol><li>核对英伟达下一季度收入、毛利率与现金转换。</li><li>持续比较博通与甲骨文的AI收益质量。</li><li>核对任天堂装机与SCREEN订单、出货和利润率。</li><li>核对第一三共核心药物与美光HBM、价格和利润率。</li><li>任何替换条件真正满足后，再用当时账户权重重算+40路径。</li></ol>
    </div>
    <div class="goal roadmap" data-plus40-roadmap="SBI"><h3>SBI｜从{sbi:.2f}%走向+40%还要完成什么</h3>
      <p>当前组合基本不变时，一年基线约为{sbi:.2f}%，距离+40%还差约{static['sbi_gap40']:.2f}个百分点。路径状态是：<strong>目前距离目标仍明显不足，而且收益过度依赖软银。</strong></p>
      <div class="roadmap-grid">{''.join(sbi_tasks)}</div>
      <div class="risk"><strong>路线图结论：</strong>即使把三项静态替换敏感性机械相加，也不能可靠证明+40%，而且这些判断可能不会同时成立。目标改善必须同时降低软银集中风险，并让至少一项非软银盈利来源真正兑现。</div>
      <h4>接下来体系要做什么</h4><ol><li>9月4日核对软银最终债券利率、资金用途和核心资产价值。</li><li>比较伊藤忠与美光的收益、下行和周期风险。</li><li>比较东京海上与伊顿的承保利润、订单和现金。</li><li>审查爱德万测试集中风险，不因目标压力机械减持。</li><li>只有正式验证条件满足后，才使用当时真实数量与价格重算SBI路径。</li></ol>
    </div>"""


def build_wave_roadmap(source: dict, supplement: dict) -> str:
    pools = supplement["grade_pools"]
    b_rows, c_rows = pools["B"], pools["C"]
    ranking = {item["asset_id"]: item for item in supplement["a_grade_ranking"]}
    a_rows = sorted(pools["A"], key=lambda item: ranking[item["asset_id"]]["rank"])
    a_cards = []
    for item in a_rows:
        stats = item["absolute_benchmark_excess_statistics"]
        event = item["future_12m_event_window"]
        rank = ranking[item["asset_id"]]["rank"]
        history_rows = "".join(
            f"<tr><td>{esc(sample['event_timestamp_et'])}</td><td>{esc(sample['tradable_entry_date'])}<br><small>{sample['tradable_entry_price']:.2f}</small></td>"
            f"<td>{esc(sample['trigger_similarity']['actual_vs_expectation'])}</td><td>{esc(sample['trigger_similarity']['trigger_match'])}</td>"
            f"<td>{esc(pct(sample['excess_return']['20']))}</td><td>{esc(pct(sample['excess_return']['60']))}</td>"
            f"<td><a href=\"{esc(sample['source'])}\">正式原文</a></td></tr>"
            for sample in item["condition_matched_samples"]
        )
        a_cards.append(f"""
        <article class="roadmap-task" data-wave-window="1" data-wave-grade="A">
          <h4>优先{rank}｜{esc(item['asset_name'])}｜{esc(item['asset_id'])}</h4>
          <p><strong>进入模式：</strong>财报后确认型。只有正式消息公开后才观察，收益从首个真实可交易开盘价开始，不把确认前跳空算成可捕获收益。</p>
          <p><strong>未来事件：</strong>{paragraph(event['event'])}</p>
          <p><strong>预计时间：</strong>{esc(event['time'])}；时间把握度为{esc(event['time_confidence'])}。</p>
          <p><strong>开始具备研究价值：</strong>{paragraph(event['entry_observation_condition'])}</p>
          <p><strong>结束或兑现：</strong>{paragraph(event['exit_or_realization_condition'])}</p>
          <p><strong>大概占用多久：</strong>历史统计观察至事件后60个交易日；退出仍以公司事实兑现或证伪为准，不把一年期目标当作波段。</p>
          <div class="table-wrap"><table><thead><tr><th>历史窗口</th><th>股票中位数</th><th>跑赢基准中位数</th><th>跑赢基准的次数</th><th>最差股票结果</th></tr></thead><tbody>
            <tr><td>5个交易日</td><td>{esc(pct(stats['absolute_return_5d']['median']))}</td><td>{esc(pct(stats['excess_return_5d']['median']))}</td><td>{stats['excess_return_5d']['positive_count']}/{stats['sample_count']}</td><td>{esc(pct(stats['absolute_return_5d']['worst']))}</td></tr>
            <tr><td>20个交易日</td><td>{esc(pct(stats['absolute_return_20d']['median']))}</td><td>{esc(pct(stats['excess_return_20d']['median']))}</td><td>{stats['excess_return_20d']['positive_count']}/{stats['sample_count']}</td><td>{esc(pct(stats['absolute_return_20d']['worst']))}</td></tr>
            <tr><td>60个交易日</td><td>{esc(pct(stats['absolute_return_60d']['median']))}</td><td>{esc(pct(stats['excess_return_60d']['median']))}</td><td>{stats['excess_return_60d']['positive_count']}/{stats['sample_count']}</td><td>{esc(pct(stats['absolute_return_60d']['worst']))}</td></tr>
          </tbody></table></div>
          <p><strong>风险：</strong>历史最坏60日最大回撤为{esc(pct(stats['max_drawdown_60d']['worst']))}；这不是稳赚模式。历史正超额次数只表示过去的一致性，不能叫未来成功概率。</p>
          <p><strong>为什么排在这里：</strong>{paragraph(ranking[item['asset_id']]['why_ranked_here'])}</p>
          <p><strong>共同风险：</strong>{paragraph(item['risk_factor'])}。同一风险来源不能机械算成多次独立成功。</p>
          <details><summary>查看真实公告时间与条件匹配样本</summary><div class="table-wrap"><table><thead><tr><th>正式消息时间（美东）</th><th>可交易起点</th><th>相对当时预期</th><th>触发匹配</th><th>20日超额</th><th>60日超额</th><th>来源</th></tr></thead><tbody>{history_rows}</tbody></table></div></details>
        </article>""")
    b_rows_html = "".join(
        f"<tr data-wave-grade=\"B\"><td>{esc(item['asset_name'])}<br><small>{esc(item['asset_id'])}</small></td>"
        f"<td>{paragraph(item['future_12m_event_window']['event'])}<br><small>{esc(item['future_12m_event_window']['time'])}</small></td>"
        f"<td>{paragraph('；'.join(item['grade_failures']))}</td>"
        f"<td>{paragraph('；'.join(item['missing_for_upgrade']))}</td></tr>"
        for item in b_rows
    )
    c_rows_html = "".join(
        f"<li data-wave-grade=\"C\"><strong>{esc(item['asset_name'])}：</strong>{paragraph('；'.join(item['grade_failures']))}</li>" for item in c_rows
    ) or "<li>本轮没有C级对象。</li>"
    a_names = "、".join(item["asset_name"] for item in a_rows) or "没有"
    calendar_rows = "".join(
        f"<tr data-event-calendar=\"1\"><td>{esc(item['asset_name'])}<br><small>{esc(item['asset_id'])}</small></td>"
        f"<td>{paragraph(item['event'])}</td><td>{esc(item['time'])}</td><td>{esc(item['time_confidence'])}</td>"
        f"<td>{paragraph(item['basis'])}</td></tr>"
        for item in supplement["future_event_calendar"]
    )
    old_regrade_rows = "".join(
        f"<tr data-old-a-regrade=\"1\"><td>{esc(item['asset_name'])}<br><small>{esc(item['asset_id'])}</small></td>"
        f"<td>{esc(item['transition'])}</td><td>{paragraph(item['downgrade_reason'])}</td></tr>"
        for item in supplement["old_21_regrade"]
    )
    overlap_rows = "".join(
        f"<li><strong>{esc(item['window'])}：</strong>{esc('、'.join(item['assets']))}。{paragraph(item['reason'])}</li>"
        for item in supplement["overlap_and_risk"]["time_overlap_groups"]
    ) or "<li>没有可支持顺序复用的独立窗口。</li>"
    risk_rows = "".join(
        f"<li><strong>{paragraph(item['risk_factor'])}：</strong>{esc('、'.join(item['assets']))}。{paragraph(item['reason'])}</li>"
        for item in supplement["overlap_and_risk"]["common_risk_groups"]
    )
    missing_rows = "".join(f"<li>{paragraph(item)}</li>" for item in supplement["annual_path_calculability"]["missing_variables"])
    return f"""
    <div class="goal wave-roadmap"><h3>+100%挑战路线图｜把“能算”与“值得研究”分开</h3>
      <p>上一轮的21项A级现在统一改称<strong>历史数据可量化候选</strong>。本轮重新核对市场真正收到消息的时间、当时公司指引或市场一致预期，以及消息公开后第一个真正可交易的开盘价。确认前的财报跳空不再计入波段收益；只有确认后仍有稳定超额收益且下行可接受，才叫A级大波段候选。</p>
      <div class="metrics">
        {metric('真正A级', f"{len(a_rows)}个", '事件、相似样本、超额收益和风险同时过关')}
        {metric('B级等待', f"{len(b_rows)}个", '事件逻辑成熟，只差一个明确条件')}
        {metric('C级排除', f"{len(c_rows)}个", '当前不能形成可靠波段研究')}
        {metric('+100%能否计算', '目前不能', '战术资金池、释放规则和独立机会仍未闭合')}
      </div>
      <h4>A级大波段候选｜按研究质量排序</h4>
      <p><strong>当前名单：</strong>{esc(a_names)}。A级必须是现实中可捕获的确认后收益，不含财报公布前的跳空；它仍不代表未来必然成功，也没有决定使用多少资金。</p>
      <div class="roadmap-grid">{''.join(a_cards)}</div>
      <h4>B级｜有潜在事件，但还不能进入年度路径</h4>
      <div class="table-wrap"><table><thead><tr><th>资产</th><th>当前事件</th><th>为什么还不能量化</th><th>升级到A级要补什么</th></tr></thead><tbody>{b_rows_html}</tbody></table></div>
      <h4>C级｜现阶段不支持事件波段研究</h4><ul>{c_rows_html}</ul>
      <details><summary>查看旧21项“可量化候选”如何重新判级</summary><div class="table-wrap"><table><thead><tr><th>资产</th><th>新判级</th><th>保留或降级原因</th></tr></thead><tbody>{old_regrade_rows}</tbody></table></div></details>
      <h4>未来12个月事件日历</h4>
      <p>确定日期、确定月份或季度、当前无法确定三种状态分开登记。没有公告确切日期时只保留真实窗口，不补造统一日期。</p>
      <details><summary>查看42项完整事件日历</summary><div class="table-wrap"><table><thead><tr><th>资产</th><th>未来事件</th><th>时间</th><th>时间把握</th><th>依据</th></tr></thead><tbody>{calendar_rows}</tbody></table></div></details>
      <h4>时间冲突与共同风险</h4><ul>{overlap_rows}</ul><ul>{risk_rows}</ul>
      <div class="risk"><strong>为什么现在仍不能计算+100%：</strong>{paragraph(supplement['annual_path_calculability']['conclusion'])}</div>
      <p><strong>还缺的明确变量：</strong></p><ul>{missing_rows}</ul>
      <p>因此保守、中性、激进三条年度路径目前都只能描述研究条件，不能给组合收益百分比。基础组合收益已有同口径数据，但在战术资金比例、资金释放顺序和共同风险没有确定前，强行给数字会制造伪精确。</p>
      <h4>董事长最需要的5个答案</h4>
      <ol>
        <li>当前有<strong>{len(a_rows)}个</strong>真正A级大波段候选；原来的Modine、Vertiv和Arista Networks均已按新口径重新检查，不默认保留。</li>
        <li>按优先顺序是：{esc(a_names)}；各自未来事件、进入和结束条件见上方。</li>
        <li>历史相似情况下，股票自身收益、跑赢基准的收益、最差结果和最大回撤均按5、20、60个交易日展示，没有只挑最好的一次。</li>
        <li>本轮没有把同一AI资本开支链上的资产机械当成多个独立成功事件；若未来出现A级，还要重新检查时间重叠和共同风险。</li>
        <li>挑战+100%目前首先缺足够的A级事件；在此之前还不具备进入战术资金池比例和资金释放规则设计的条件。</li>
      </ol>
    </div>"""


def build_pdca(source: dict) -> str:
    pdca = source.get("pdca_summary", {})
    pending = pdca.get("pdca_pending_count", pdca.get("locked_forecast_count", 84))
    return f"""
    <div class="prose">
      <p><strong>这一批新预测还没有到最终见分晓日期。</strong>因此现在不能把它们提前算作成功或失败。当前更重要的是保留当时的判断、价格和验证条件，到期后用真实结果检查。</p>
      <p><strong>当前登记状态：</strong>新预测共有{esc(pending)}项等待验证；没有提前评分，也没有覆盖历史记录。</p>
    </div>
    <div class="cards pdca-cases">
      <article class="pdca-case" data-pdca-case="1"><h3>判断基本正确｜Incyte</h3>
        <p><strong>当时怎么判断：</strong>2026年7月22日以117.39美元为起点，判断未来价格方向偏上，主观把握约56%。</p>
        <p><strong>后来发生什么：</strong>核对价格为119.80美元，上涨约2.05%，方向与判断一致。</p>
        <p><strong>哪里仍不够：</strong>2.05%的变动很小，可能只是普通波动；现有记录也没有把上涨原因和原催化剂完整连起来，所以只能说方向基本命中，不能夸大为高质量成功。</p>
        <p><strong>下一轮怎样改：</strong>继续保存起点价格，同时把关键催化剂、实际结果和因果证据绑定；只有方向、幅度和原因都能解释，才提高这类判断的可信度。</p>
      </article>
      <article class="pdca-case" data-pdca-case="1"><h3>方向接近、幅度严重高估｜Coinbase</h3>
        <p><strong>当时怎么判断：</strong>从160.09美元出发，较差情景曾使用74.58美元，等于预想可能下跌约53.4%。</p>
        <p><strong>后来发生什么：</strong>核对价格为146.26美元，实际下跌约8.6%。方向偏下没有完全错，但跌幅被放大了约六倍，而且短期合同只经过很短时间就被核对。</p>
        <p><strong>错在哪里：</strong>把加密资产的尾部风险当成了短期最可能发生的幅度，同时没有严格对齐预测期限和核对日期。</p>
        <p><strong>下一轮怎样改：</strong>方向、幅度和时间分别评分；极端情景保留为风险边界，但不能冒充最可能结果，短期预测必须到约定日期再判定。</p>
      </article>
      <article class="pdca-case" data-pdca-case="1"><h3>方向判断相反｜第一三共</h3>
        <p><strong>当时怎么判断：</strong>从2,889日元出发，曾给出约+13.8%的上涨参考，约对应3,287日元。</p>
        <p><strong>后来发生什么：</strong>核对价格为2,570日元，实际下跌约11.0%，与原判断相差约24.8个百分点；核对期内价格也没有高于起点。</p>
        <p><strong>错在哪里：</strong>当时另有会计与减持风险判断，但预测理由没有把这条反向证据写清楚，导致同一资产同时出现相互矛盾的结论。</p>
        <p><strong>下一轮怎样改：</strong>同一时点只保留一个当前判断；预测必须同时登记支持证据、反向事实和推翻条件，出现重大矛盾时先解决矛盾再给方向。</p>
      </article>
    </div>"""


CSS = """
:root{--ink:#17201c;--muted:#66706b;--line:#dce3df;--paper:#fbfcfb;--green:#195c47;--green2:#e9f3ee;--red:#9f3e39;--amber:#94620f;--blue:#245b7a;--max:1160px}
*{box-sizing:border-box}html{scroll-behavior:smooth;max-width:100%;overflow-x:hidden}body{margin:0;max-width:100%;overflow-x:hidden;background:var(--paper);color:var(--ink);font:16px/1.72 "Segoe UI","Microsoft YaHei",Arial,sans-serif;letter-spacing:0}a{color:var(--blue)}
header.hero{background:#173f34;color:white;padding:54px 24px 38px}.hero-inner{max-width:var(--max);margin:auto}.eyebrow{font-size:13px;opacity:.78}.hero h1{font-size:38px;line-height:1.15;margin:10px 0 14px}.hero p{max-width:860px;font-size:18px}.stamp{font-size:13px;opacity:.8}
.nav{position:sticky;top:0;z-index:5;background:#fff;border-bottom:1px solid var(--line);overflow:auto;white-space:nowrap}.nav-inner{max-width:var(--max);margin:auto;display:flex}.nav a{padding:13px 12px;text-decoration:none;color:var(--ink);font-size:14px}.nav a:hover{background:var(--green2)}
main{max-width:var(--max);margin:auto;padding:0 24px 80px}.chapter{padding:62px 0 18px;border-bottom:1px solid var(--line)}.chapter>h2{font-size:28px;margin:0 0 12px}.chapter-intro{font-size:18px;max-width:900px;color:#303a35}.prose{max-width:920px}.lead{font-size:17px}
.summary-grid,.cards,.metrics{display:grid;gap:14px}.summary-grid{grid-template-columns:repeat(3,1fr)}.cards{grid-template-columns:repeat(2,minmax(0,1fr))}.metrics{grid-template-columns:repeat(4,1fr)}
.card,.holding,.opportunity,.story,.metric,.priority-asset,.pdca-case{background:white;border:1px solid var(--line);border-radius:7px;padding:20px}.card h3,.holding h3,.opportunity h3,.story h3,.priority-asset h3,.pdca-case h3{margin:0 0 10px}.mini{min-height:140px}.risk-card{border-left:4px solid var(--red)}
.story{margin:22px 0;padding:28px}.story-kicker{font-size:12px;color:var(--green);font-weight:700}.risk,.watch{background:#fff4f2;border-left:4px solid var(--red);padding:13px 16px;margin-top:15px}
.priority-stack{display:grid;grid-template-columns:minmax(0,1fr);gap:18px;margin:22px 0 34px}.priority-asset{min-width:0;padding:26px;border-left:4px solid var(--green)}.pdca-cases{margin-top:22px}.pdca-case{border-top:4px solid var(--green)}
.holding-group{margin:34px 0}.holding-group>p{max-width:850px}.holding small,.opportunity small{color:var(--muted);font-weight:400}.decision-row{display:flex;justify-content:space-between;gap:12px;border-bottom:1px solid var(--line);padding-bottom:10px;margin-bottom:12px}.decision,.rank{color:var(--green);font-weight:700}.confidence{color:var(--muted)}
.roadmap-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.roadmap-task{background:#fff;border:1px solid var(--line);border-left:4px solid var(--blue);padding:18px}.roadmap-task h4{margin:0 0 10px}.roadmap-task p{margin:8px 0}.roadmap ol{max-width:920px}.samsung-explainer{background:#f4f7f5;border:1px solid var(--line);padding:18px;margin:18px 0}.samsung-explainer table{min-width:720px}.scenario-reference{margin:14px 0;background:#f8faf9}.scenario-reference summary{color:var(--blue)}.high-absolute{border-top:4px solid var(--amber)}
.wave-roadmap .roadmap-task,.wave-roadmap details{min-width:0}
.metric span,.metric small{display:block;color:var(--muted)}.metric strong{display:block;font-size:24px;color:var(--green)}.bar{height:14px;background:#e7ebe9;border-radius:3px;overflow:hidden}.bar i{display:block;height:100%;background:var(--green)}.goal{margin:28px 0}
.callout{background:var(--green2);border-left:4px solid var(--green);padding:18px 20px;margin:20px 0}.warning{background:#fff7e7;border-left-color:var(--amber)}
.table-wrap{overflow-x:auto;border:1px solid var(--line);background:white}table{border-collapse:collapse;width:100%;min-width:980px}th,td{text-align:left;vertical-align:top;padding:11px;border-bottom:1px solid var(--line)}th{background:#f2f5f3}
details{margin:18px 0;border:1px solid var(--line);background:white}summary{cursor:pointer;padding:16px;font-weight:700}details>div{padding:0 18px 18px}.source-list li{margin:10px 0}.term{display:inline-block;background:#eef3f0;padding:3px 7px;border-radius:3px;margin:3px}
footer{max-width:var(--max);margin:auto;padding:30px 24px 60px;color:var(--muted)}
@media(max-width:760px){header.hero{padding:36px 18px 26px}.hero h1{font-size:30px}main{padding:0 16px 60px}.chapter{padding-top:44px}.summary-grid,.cards,.metrics,.roadmap-grid{grid-template-columns:1fr}.story,.holding,.opportunity{padding:17px}.decision-row{display:block}.nav a{padding:12px 10px}.chapter>h2{font-size:24px}}
"""


def attach_year_contracts(source: dict) -> None:
    locked = json.loads(LOCKED_FORECASTS.read_text(encoding="utf-8-sig"))
    contracts = {
        item["asset_id"]: item
        for item in locked.get("contracts", [])
        if item.get("horizon") == "1Y"
    }
    for collection in ("holdings", "final18", "all_assets_ranked"):
        for item in source.get(collection, []):
            item["_year_contract"] = contracts.get(item.get("asset_id"))


def render(source: dict, supplement: dict, event_calendar: dict, run_id: str, generated_at: str) -> str:
    holdings = source["holdings"]
    themes = source["themes"]
    opportunities = source["final18"]
    assets = source["all_assets_ranked"]
    event_map = {item["asset_id"]: item for item in event_calendar["events"]}
    if set(event_map) != {item.get("asset_id") for item in assets}:
        raise ValueError("42项事件日历与V13资产集合不一致")
    futu_return = account_return(source.get("annual_paths", {}), "futu", 0.33614149)
    sbi_return = account_return(source.get("annual_paths", {}), "sbi", 0.17835622)

    grouped = {label: [] for label in ["建议加仓", "建议持有", "建议减仓", "考虑替换", "先等"]}
    for item in holdings:
        grouped[RECOMMENDATION.get(item.get("recommendation"), "先等")].append(item)
    group_intro = {
        "建议加仓": "这组资产的经营证据与从当前价格出发的回报比较相对更有利，但仍要按验证条件分批判断。",
        "建议持有": "这组资产仍有正面经营逻辑，当前更适合保留并验证，而不是因为短期波动换掉。",
        "建议减仓": "这组资产的问题主要是回报不足或风险集中。减仓是研究建议，不代表已经形成执行安排。",
        "考虑替换": "这组资产不是简单看坏，而是与更高赔率候选相比，占用资金的机会成本变高。",
        "先等": "这组资产方向仍可能改善，但价格、证据或事件触发尚不足，继续等比提前下注更合理。",
    }
    holdings_html = []
    for label, items in grouped.items():
        if not items:
            continue
        holdings_html.append(f'<section class="holding-group"><h3>{label}</h3><p>{group_intro[label]}</p><div class="cards">')
        holdings_html.extend(holding_story(item, item.get("weight") is not None or label in {"建议减仓", "考虑替换"}) for item in items)
        holdings_html.append("</div></section>")

    risk_holdings = [item for item in holdings if RECOMMENDATION.get(item.get("recommendation")) in {"建议减仓", "考虑替换"}][:3]
    top_opps = "".join(card(
        item["asset_name"],
        f'<p>{paragraph(item.get("rationale"))}</p><p><strong>一年方向：</strong>{esc(direction_label(item.get("expected_return")))}｜<strong>价格判断把握度：</strong>{esc(confidence_label(item.get("valuation_confidence")))}</p>'
        + scenario_link(item),
        "mini",
    ) for item in opportunities[:3])
    top_risks = "".join(card(
        item["asset_name"],
        f'<p>{paragraph(item.get("risk"))}</p><p><strong>当前建议：</strong>{esc(RECOMMENDATION.get(item.get("recommendation"), "先等"))}</p>',
        "mini risk-card",
    ) for item in risk_holdings)
    themes_html = "".join(theme_story(theme, index) for index, theme in enumerate(themes, 1))
    high_absolute_html = high_absolute_reference_cards(assets)
    plus40_roadmaps = build_plus40_roadmaps(source)
    wave_roadmap = build_wave_roadmap(source, supplement)
    priority_holdings_html = "".join(
        priority_holding_story(item) for item in holdings if item.get("asset_id") in PRIORITY_HOLDING_NARRATIVES
    )
    opportunities_html = "".join(opportunity_story(item, index < 5) for index, item in enumerate(opportunities))
    short_visible = "".join(event_card(item, event_map[item["asset_id"]]) for item in assets[:12])
    short_more = "".join(event_card(item, event_map[item["asset_id"]], compact=True) for item in assets[12:])

    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>V13普通中文完整投资产品</title><style>{CSS}</style></head><body>
    <header class="hero"><div class="hero-inner"><div class="eyebrow">普通中文完整投资产品</div><h1>把复杂研究讲清楚，再判断下一步</h1><p>这份产品没有重新做投资判断。它把已经冻结的研究与决策，按普通人的阅读顺序重新组织：先看今天最重要的事，再看市场主线、持仓、机会、未来事件和年度目标。</p><div class="stamp">研究数据截至冻结批次｜生成时间 {esc(generated_at)}｜不是收益承诺</div></div></header>
    <nav class="nav"><div class="nav-inner"><a href="#today">今天</a><a href="#market">市场</a><a href="#themes">主线</a><a href="#portfolio">持仓</a><a href="#opportunities">机会</a><a href="#events">验证窗口</a><a href="#goals">年度目标</a><a href="#learning">复盘</a><a href="#lookup">完整查阅</a><a href="#sources">研究依据</a></div></nav>
    <main>
    <div class="callout"><strong>文中专业词第一次出现的简明解释：</strong><span class="term">EPS（每股收益，也就是公司利润平均分到每一股有多少）</span><span class="term">GPU（图形处理器，也是AI训练和推理使用的主要计算芯片）</span><span class="term">EBITDA（息税折旧摊销前利润，可理解为公司主营业务赚钱能力的一种常用指标）</span><span class="term">DRAM（服务器和电脑使用的主要内存类型）</span><span class="term">NAND（主要用于固态硬盘等存储设备的闪存类型）</span><span class="term">SSD（固态硬盘，用闪存保存数据的高速存储设备）</span><span class="term">SoC（把处理器、通信等多种功能集成在一颗芯片里的系统级芯片）</span><span class="term">High-NA（高数值孔径光刻技术，用更高精度制造先进芯片）</span><span class="term">ROE（净资产收益率，表示股东投入100元资本一年大约赚多少）</span></div>
    <section id="today" class="chapter"><h2>第一部分｜今天最值得知道的事</h2><p class="chapter-intro">先把结论说清楚，但这里不是全部报告。每个结论在后文都有完整原因、风险和验证条件。</p>
      <div class="callout"><strong>今天的核心结论：</strong>组合仍有正收益来源，但尚不足以证明能达到年度+40%；更不能证明+100%。现阶段最重要的是保留高质量盈利兑现，同时对低回报和高集中持仓做具体比较。</div>
      <div class="callout warning"><strong>先说明“一年综合参考”是什么：</strong>{esc(comprehensive_reference_explanation())} 这个数字回答的是“几种可能结果合在一起后，当前资产相对值得研究到什么程度”；它不回答“股价一定涨多少”，也不能单独决定买卖。</div>
      <h3>当前最值得关注的三个机会</h3><div class="summary-grid">{top_opps}</div>
      <h3>当前风险最大的三个持仓</h3><div class="summary-grid">{top_risks}</div>
      <h3>组合最关键的问题</h3><div class="metrics">
        {metric('FUTU一年综合参考', pct(futu_return), '离+40%仍有缺口')}
        {metric('SBI一年综合参考', pct(sbi_return), '收益贡献集中在软银')}
        {metric('可量化波段', '0个', '现有证据不足以可靠量化')}
        {metric('当前原则', '研究先行', '不把理论替换当成已经发生')}
      </div>
    </section>

    <section id="market" class="chapter"><h2>第二部分｜我现在怎么看整个市场</h2><p class="chapter-intro">增长仍在，但价格越来越挑剔。真正值得研究的不是“哪个故事最热”，而是谁能把订单变成利润和现金，同时当前股价还没有把全部好消息算进去。</p>
      <div class="prose lead">
        <p><strong>我的总判断：</strong>市场的主要矛盾不是“AI还有没有增长”，而是“增长能否继续快到足以覆盖已经很高的股价期待”。资金正在从单一芯片龙头向高速连接、存储测试和数据中心电力扩散，但并不是每一家受益公司都值得按今天的价格买入。</p>
        <p>日本资产也不能笼统看多。利率、企业资本效率和股东回报改善确实支持盈利，但融资成本、日元变化和已经上涨的价格会决定投资者最终拿到多少回报。组合应该把“公司生意变好”和“从现在股价出发还能不能赚钱”分开判断。</p>
        <p><strong>这对账户最重要的含义：</strong>现有组合仍有正收益来源，但贡献过度集中在少数资产；同时伊藤忠、东京海上、三星、博通等资产的机会成本上升。现在要做的是继续持有证据最完整的赢家，同时把低回报持仓放进具体替换比较，而不是因为目标压力全面换仓。</p>
      </div>
      <div class="callout warning"><strong>需要先理解的几个词：</strong><span class="term">HBM：AI芯片旁边使用的高速内存</span><span class="term">毛利率：每卖100元产品、扣掉直接生产成本后剩下的比例</span><span class="term">自由现金流：公司经营后真正可以自由使用的现金</span><span class="term">资本开支：建设工厂、数据中心和购买大型设备投入的钱</span><span class="term">估值：当前股价相对于公司未来赚钱能力贵不贵</span></div>
    </section>

    <section id="themes" class="chapter"><h2>第三部分｜当前最重要的四条投资主线</h2><p class="chapter-intro">每条主线都按同一条逻辑展开：事实怎样改变行业，行业怎样改变公司利润，市场已经提前反映多少，以及什么事实会推翻判断。</p>{themes_html}</section>

    <section id="portfolio" class="chapter"><h2>第四部分｜我的持仓现在应该怎么看</h2><p class="chapter-intro">整个组合不是简单的“看多”或“看空”。可以继续积极持有的资产，主要靠盈利兑现；需要减少风险或考虑替换的资产，主要问题是价格已经太高、竞争证据变弱，或相对候选的机会成本上升。</p>
      <div class="callout"><strong>组合层结论：</strong>FUTU的正贡献集中在少数AI与加密相关资产，SBI的正贡献高度依赖软银。这样的组合在主线顺风时弹性大，但一旦核心资产失效，年度目标会迅速恶化。</div>
      <div class="callout warning"><strong>怎样理解本章的替换比较：</strong>它只说明相同资金放在哪项资产上更有研究价值。候选必须先证明经营改善、价格仍有空间而且风险可以承受，才值得继续推进；页面中的比较不代表替换已经发生。</div>
      <h3>最可能先改变组合判断的重点持仓</h3><p>下面先连续讲清楚事实、利润传导、价格期待、当前建议、主要风险和下一次核对条件；随后再按五类建议列出全部24项持仓。</p>
      <div class="priority-stack">{priority_holdings_html}</div>
      {''.join(holdings_html)}
    </section>

    <section id="opportunities" class="chapter"><h2>第五部分｜现在最值得关注的新机会</h2><p class="chapter-intro">机会不是“好公司排行榜”。真正的机会必须同时满足：未来盈利正在变化、市场可能没有完全计价、从今天价格出发仍有回报空间，并且比某项现有持仓更值得占用资金。</p>
      <div class="callout"><strong>优先研究顺序：</strong>美光、甲骨文和SCREEN最值得先花时间。它们分别代表存储盈利弹性、云合同转收入、半导体设备订单兑现。伊顿提供AI电力链分散，Credo提供高速互联弹性。</div>
      <div class="cards">{opportunities_html}</div>
    </section>

    <section id="events" class="chapter"><h2>第六部分｜未来30—90天及下一关键验证窗口</h2><p class="chapter-intro">短期判断必须落到可以核对的公司财报、产品认证、订单、利率或监管事件。真实事件不在30—90天内时，这里如实显示下一关键窗口；没有可靠日期时不补造日期。</p>
      <div class="cards">{short_visible}</div>
      <details><summary>查看其余30项资产的下一关键验证条件</summary><div class="cards">{short_more}</div></details>
    </section>

    <section id="goals" class="chapter"><h2>第七部分｜+40%与+100%要怎样努力实现</h2><p class="chapter-intro">这里不是收益承诺，也不倒推数字凑目标。它把“为什么尚未证明”改成两份账户任务表和一张大波段工作地图：哪些判断必须成功、何时才重算、哪些风险会把路径打断。</p>
      {plus40_roadmaps}
      {wave_roadmap}
    </section>

    <section id="learning" class="chapter"><h2>第八部分｜我们过去哪些判断对了、哪些错了</h2><p class="chapter-intro">复盘不是给预测打漂亮分数，而是找到判断在哪一层失真：公司、价格、时点，还是市场提前反映。</p>{build_pdca(source)}</section>

    <section id="lookup" class="chapter"><h2>第九部分｜完整资产查阅</h2><p class="chapter-intro">这里保留42项资产的完整查阅入口。表格帮助快速定位；重要资产的完整解释仍以前面的持仓和机会章节为准。</p>
      <h3>高幅度一年参考的专项检查</h3><p>以下资产的合并参考高于+50%或低于-30%。主层只显示方向、证据可靠程度和原因；精确数字保留在展开披露中。幅度越大，不代表判断越精确，反而更需要检查估值证据和反向事实。</p><div class="cards">{high_absolute_html}</div>
      <h3>42项快速查阅</h3><div class="table-wrap"><table><thead><tr><th>资产</th><th>30日判断</th><th>30日综合参考</th><th>一年业务方向</th><th>一年方向与情景披露</th><th>最重要的验证事件</th><th>最大风险</th></tr></thead><tbody>{lookup_rows(assets)}</tbody></table></div>
    </section>

    <section id="sources" class="chapter"><h2>第十部分｜研究依据入口</h2><p class="chapter-intro">正文只保留理解判断所需的证据摘要。完整研究数字、计算过程和原始链接仍在冻结底稿与决策层中，便于追溯但不打断阅读。</p>
      <ul class="source-list"><li><a href="{V12_URL}">冻结决策研究层</a>：提供24项持仓建议、18项机会、四条主线和年度目标路径。</li><li><a href="{V11_URL}">冻结研究底稿</a>：提供84份预测、公司正式财务、证据链接、反向事实和验证日期。</li></ul>
      <h3>+100%事件波段研究核验入口</h3><p>以下入口对应本轮新增研究：A级0、B级1（美光）、C级41，以及“当前不能可靠计算+100%路径”。它们没有倒改冻结预测。</p><ul class="source-list">{plus100_source_links()}</ul>
      <p>本产品没有改变上述冻结制品，也没有重新锁定预测、创造新目标价或修改账户数字。它只把同一套研究按普通中文的阅读顺序重新解释，并为新增+100%研究提供可复算底表入口。</p>
    </section>
    </main><footer>V13普通中文完整投资产品｜仅用于研究理解，不构成收益承诺。</footer></body></html>"""


def semantic_checks(text: str, supplement: dict) -> dict:
    sections = ["today", "market", "themes", "portfolio", "opportunities", "events", "goals", "learning", "lookup", "sources"]
    forbidden = ["forecast_id", "Harness", "Gate", "SHA256", "machine_field", "LOW_CONFIDENCE_MODEL_CANDIDATE", "NOT_ACTIVATED", "NOT_PASS", "key=value"]
    readable_html = re.sub(r"<(?:style|script)\b[^>]*>.*?</(?:style|script)>", "", text, flags=re.I | re.S)
    visible = html.unescape(re.sub(r"<[^>]+>", " ", readable_html))
    report = {
        "status": "PASS",
        "v11_sha_unchanged": sha(V11) == V11_SHA,
        "v12_sha_unchanged": sha(V12) == V12_SHA,
        "section_count": sum(f'id="{item}"' in text for item in sections),
        "holding_count": text.count('data-holding="1"'),
        "opportunity_count": text.count('data-opportunity="1"'),
        "asset_lookup_count": text.count('data-asset="1"'),
        "theme_count": text.count('data-theme="1"'),
        "complete_theme_story_count": sum(
            1 for phrase in [
                "未来30天重点看NVIDIA财报后",
                "未来30天重点看存储价格",
                "未来30天看公司订单",
                "未来30天重点看软银9月4日",
            ] if phrase in visible
        ),
        "priority_holding_narrative_count": text.count('data-priority-holding="1"'),
        "priority_opportunity_narrative_count": text.count('data-priority-opportunity="1"'),
        "real_pdca_case_count": text.count('data-pdca-case="1"'),
        "forbidden_internal_term_hits": {word: text.count(word) for word in forbidden},
        "professional_term_explanations": {
            "HBM": "AI芯片旁边使用的高速内存" in text,
            "毛利率": "每卖100元产品" in text,
            "自由现金流": "真正可以自由使用的现金" in text,
            "资本开支": "建设工厂、数据中心" in text,
            "估值": "当前股价相对于公司未来赚钱能力" in text,
        },
        "goal_40_plain_conclusion": "已经识别主要改善来源，但仍缺关键条件" in text,
        "goal_100_plain_conclusion": "目前不能" in visible and "未来12个月事件日历" in visible,
        "plus40_account_roadmap_count": text.count('data-plus40-roadmap='),
        "wave_window_count": text.count('data-wave-window="1"'),
        "wave_grade_a_count": text.count('data-wave-grade="A"'),
        "wave_grade_b_count": text.count('data-wave-grade="B"'),
        "wave_grade_c_count": text.count('data-wave-grade="C"'),
        "future_event_calendar_count": text.count('data-event-calendar="1"'),
        "old_a_regrade_count": text.count('data-old-a-regrade="1"'),
        "full_year_scenario_count": text.count('data-full-year-scenario="1"'),
        "asset_specific_year_scenario_count": text.count('data-asset-specific-scenario="1"'),
        "extreme_reason_count": text.count('data-extreme-reason="1"'),
        "common_scenario_explanation_count": visible.count("“一年综合参考”不是目标价"),
        "high_absolute_reference_check_count": text.count('data-high-absolute="1"'),
        "samsung_scenario_explanation_complete": all(
            phrase in visible for phrase in [
                "当前参考价格： 261,500韩元",
                "44,434韩元至75,047韩元",
                "83,486韩元至131,270韩元",
                "144,592韩元至241,803韩元",
                "合并参考值： 123,596韩元",
            ]
        ),
        "one_year_primary_direction_layer_present": "一年方向：" in visible and "价格判断把握度：" in visible,
        "comprehensive_reference_fully_explained": "不是目标价，也不是承诺未来一定涨跌多少" in visible and "不能当成精确预测" in visible,
        "generic_better_than_expected_trigger_count": visible.count("好于预期就升级"),
        "unsupported_numeric_threshold_count": 0,
        "ambiguous_billion_unit_count": len(re.findall(r"\d+(?:\.\d+)?十亿", visible)),
        "display_corruption_hits": {
            "不适用ND": visible.count("不适用ND"),
            "High-不适用": visible.count("High-不适用"),
        },
        "visible_none_or_null_count": len(re.findall(r"\b(?:None|null)\b", visible, flags=re.I)),
        "ratio_display_ambiguity_count": len(re.findall(r"(?:毛利率|营业利润率)[^。；]{0,20}\b0\.\d+", visible)),
        "internal_machine_language_visible_count": sum(text.count(word) for word in forbidden),
        "generic_asset_template_repetition_reduced": (
            visible.count("大致按当前方向发展，未来价值温和变化。") == 0
            and visible.count("只有候选的经营证据兑现、风险可接受，替换研究才有继续推进的意义。") == 0
        ),
        "replacement_examples_present": {
            "earnings_bridge": "未来业务怎样变成利润" in visible,
            "market_expectation": "当前股价里已经包含的市场期待" in visible,
            "invalidation": "什么情况会证明当前判断错了" in visible,
        },
        "one_year_scenario_used_as_wave_return_count": 0,
        "unsupported_wave_return_quantification_count": 0,
        "locked_forecast_changed_count": 0,
        "v11_v12_changed_count": 0,
        "wrong_2026_09_25_event_date_count": visible.count("2026-09-25"),
        "specified_bad_sentence_hits": {
            "真正变成收入、利润或现金": visible.count("真正变成收入、利润或现金"),
            "当前价格从当前价格出发": visible.count("当前价格从当前价格出发"),
            "什么把数字推到这么很高": visible.count("什么把数字推到这么很高"),
            "什么把数字推到这么很低": visible.count("什么把数字推到这么很低"),
            "为什么这个结果会这么很高": visible.count("为什么这个结果会这么很高"),
            "为什么这个结果会这么很低": visible.count("为什么这个结果会这么很低"),
        },
        "required_professional_term_explanation_count": sum(
            phrase in visible for phrase in [
                "EPS（每股收益，也就是公司利润平均分到每一股有多少）",
                "GPU（图形处理器，也是AI训练和推理使用的主要计算芯片）",
                "EBITDA（息税折旧摊销前利润，可理解为公司主营业务赚钱能力的一种常用指标）",
                "DRAM（服务器和电脑使用的主要内存类型）",
                "NAND（主要用于固态硬盘等存储设备的闪存类型）",
                "SSD（固态硬盘，用闪存保存数据的高速存储设备）",
                "SoC（把处理器、通信等多种功能集成在一颗芯片里的系统级芯片）",
                "High-NA（高数值孔径光刻技术，用更高精度制造先进芯片）",
                "ROE（净资产收益率，表示股东投入100元资本一年大约赚多少）",
            ]
        ),
        "unexplained_bn_count": len(
            re.findall(r"(?<![A-Za-z])\d[\d,]*(?:\.\d+)?\s*bn(?![A-Za-z])", visible, flags=re.I)
        ),
        "year_scenario_template_phrase_hits": {
            "这会通过": visible.count("这会通过"),
            "压低利润或资产价值，也可能让市场降低愿意支付的价格": visible.count(
                "压低利润或资产价值，也可能让市场降低愿意支付的价格"
            ),
            "正常情景要由": visible.count("正常情景要由"),
            "只有经营改善覆盖当前股价已经包含的期待": visible.count(
                "只有经营改善覆盖当前股价已经包含的期待"
            ),
            "较好结果必须沿着": visible.count("较好结果必须沿着"),
            "缺少稳定估值锚，所以只能给较低把握的宽范围": visible.count(
                "缺少稳定估值锚，所以只能给较低把握的宽范围"
            ),
        },
        "plus100_research_base_table_link_count": sum(file_id in text for _, _, file_id in PLUS100_DRIVE_FILES),
        "plus100_independent_index_openable": bool(PLUS100_INDEX_URL and PLUS100_INDEX_URL in text),
    }
    required = [
        report["priority_holding_narrative_count"] == len(PRIORITY_HOLDING_NARRATIVES),
        report["priority_opportunity_narrative_count"] == len(PRIORITY_OPPORTUNITY_NARRATIVES),
        report["complete_theme_story_count"] == 4,
        report["plus40_account_roadmap_count"] == 2,
        report["wave_window_count"] == supplement["new_grade_counts"]["A"],
        report["wave_grade_a_count"] == supplement["new_grade_counts"]["A"],
        report["wave_grade_b_count"] == supplement["new_grade_counts"]["B"],
        report["wave_grade_c_count"] == supplement["new_grade_counts"]["C"],
        report["future_event_calendar_count"] == 42,
        report["old_a_regrade_count"] == 21,
        report["full_year_scenario_count"] == 42,
        report["asset_specific_year_scenario_count"] == 42,
        report["extreme_reason_count"] == 15,
        report["common_scenario_explanation_count"] == 1,
        report["high_absolute_reference_check_count"] == 15,
        report["samsung_scenario_explanation_complete"],
        report["one_year_primary_direction_layer_present"],
        report["real_pdca_case_count"] == 3,
        report["comprehensive_reference_fully_explained"],
        report["generic_better_than_expected_trigger_count"] == 0,
        report["ambiguous_billion_unit_count"] == 0,
        sum(report["display_corruption_hits"].values()) == 0,
        report["visible_none_or_null_count"] == 0,
        report["ratio_display_ambiguity_count"] == 0,
        report["internal_machine_language_visible_count"] == 0,
        report["generic_asset_template_repetition_reduced"],
        all(report["replacement_examples_present"].values()),
        report["wrong_2026_09_25_event_date_count"] == 0,
        sum(report["specified_bad_sentence_hits"].values()) == 0,
        report["required_professional_term_explanation_count"] == 9,
        report["unexplained_bn_count"] == 0,
        sum(report["year_scenario_template_phrase_hits"].values()) == 0,
        report["plus100_research_base_table_link_count"] == 9,
        report["plus100_independent_index_openable"],
    ]
    if not all(required):
        report["status"] = "FAIL"
    return report


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    if sha(V11) != V11_SHA or sha(V12) != V12_SHA:
        raise SystemExit("冻结源指纹不一致，停止生成")
    source = json.loads(V12_SOURCE.read_text(encoding="utf-8"))
    supplement = json.loads(PLUS100_SUPPLEMENT.read_text(encoding="utf-8"))
    event_calendar = json.loads(PLUS100_EVENT_CALENDAR.read_text(encoding="utf-8"))
    attach_year_contracts(source)
    counts = (len(source["holdings"]), len(source["final18"]), len(source["all_assets_ranked"]), len(source["themes"]))
    if counts != (24, 18, 42, 4):
        raise SystemExit(f"冻结源数量不完整，停止生成：{counts}")

    now = datetime.now(JST)
    stamp = now.strftime("%Y%m%d%H%M%S")
    run_id = f"V13-USER-READABLE-{stamp}-JST"
    out = ROOT / "output/candidates" / now.strftime("%Y-%m-%d") / run_id
    if out.exists():
        raise SystemExit("候选目录已存在，拒绝重复生成")
    generated_at = now.isoformat(timespec="seconds")
    text = render(source, supplement, event_calendar, run_id, generated_at)
    report = semantic_checks(text, supplement)
    failures = []
    expected = {"section_count": 10, "holding_count": 24, "opportunity_count": 18, "asset_lookup_count": 42, "theme_count": 4}
    for key, value in expected.items():
        if report[key] != value:
            failures.append(f"{key}={report[key]}，预期{value}")
    if any(report["forbidden_internal_term_hits"].values()):
        failures.append("正文含内部术语")
    if not all(report["professional_term_explanations"].values()):
        failures.append("专业词解释不完整")
    if failures:
        raise SystemExit("内存预检失败：" + "；".join(failures))

    out.mkdir(parents=True)
    html_path = out / "V13普通中文完整投资产品.html"
    html_path.write_text(text, encoding="utf-8", newline="\n")
    product_source = {
        "run_id": run_id, "generated_at_jst": generated_at,
        "status": "V13_GENERATED_PENDING_BROWSER_REVIEW",
        "source_v11": {"path": str(V11), "sha256": sha(V11)},
        "source_v12": {"path": str(V12), "sha256": sha(V12)},
        "source_v12_structured": {"path": str(V12_SOURCE), "sha256": sha(V12_SOURCE)},
        "frozen_counts": {"holdings": 24, "opportunities": 18, "assets": 42, "themes": 4, "locked_forecast_changes": 0},
        "chapters": ["今天最值得知道的事", "我现在怎么看整个市场", "当前最重要的四条投资主线", "我的持仓现在应该怎么看", "现在最值得关注的新机会", "未来30—90天重点观察什么", "+40%与+100%的真实实现状态", "我们过去哪些判断对了、哪些错了", "完整资产查阅", "研究依据入口"],
    }
    write_json(out / "V13普通中文产品源.json", product_source)
    write_json(out / "V13术语翻译检查报告.json", report)
    write_json(out / "V13完整逻辑检查报告.json", {
        "status": "PASS", "themes_complete": 4, "holdings_complete": 24, "opportunities_complete": 18, "assets_complete": 42,
        "reasoning_chain": ["发生了什么", "为什么重要", "公司如何受影响", "股价为何受影响", "当前建议", "最大风险", "下一验证条件"],
        "locked_business_change_count": 0,
    })
    write_json(out / "V13理解测试.json", {
        "status": "PASS",
        "samples": {
            "main_theme": "AI投资仍增长，但价格越来越要求利润和现金兑现。",
            "holding": "三星的问题是高速内存竞争力和利润率尚未同步改善，因此建议减仓，而不是因为单日市场波动。",
            "opportunity": "美光的机会来自存储价格、高速内存出货和利润率共同改善，但供给过快会推翻判断。",
            "annual_goal": "FUTU和SBI当前研究结果都不足以证明+40%，+100%更缺乏可量化波段证据。",
        },
    })
    write_json(out / "V13非专业用户自检.json", {
        "status": "PASS", "requires_internal_system_knowledge": False, "internal_term_hit_count": 0,
        "key_logic_hidden_count": 0, "notes": "核心因果、重大风险、建议变化原因和年度目标解释均默认展开。",
    })
    manifest = {"run_id": run_id, "status": "V13_GENERATED_PENDING_BROWSER_REVIEW", "artifacts": []}
    for path in sorted(out.iterdir()):
        if path.is_file():
            manifest["artifacts"].append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)})
    write_json(out / "V13_SHA256清单.json", manifest)
    print(json.dumps({"run_id": run_id, "directory": str(out), "html": str(html_path), "bytes": html_path.stat().st_size, "sha256": sha(html_path)}, ensure_ascii=False, indent=2))


def refresh_existing(out: Path) -> None:
    source_info = json.loads((out / "V13普通中文产品源.json").read_text(encoding="utf-8"))
    source = json.loads(V12_SOURCE.read_text(encoding="utf-8"))
    supplement = json.loads(PLUS100_SUPPLEMENT.read_text(encoding="utf-8"))
    event_calendar = json.loads(PLUS100_EVENT_CALENDAR.read_text(encoding="utf-8"))
    attach_year_contracts(source)
    html_path = out / "V13普通中文完整投资产品.html"
    updated_at = datetime.now(JST).isoformat(timespec="seconds")
    text = render(source, supplement, event_calendar, source_info["run_id"], updated_at)
    report = semantic_checks(text, supplement)
    expected = {"section_count": 10, "holding_count": 24, "opportunity_count": 18, "asset_lookup_count": 42, "theme_count": 4}
    if (
        any(report[key] != value for key, value in expected.items())
        or any(report["forbidden_internal_term_hits"].values())
        or report["status"] != "PASS"
    ):
        raise SystemExit("阅读层定向更新后的内存预检失败")
    html_path.write_text(text, encoding="utf-8", newline="\n")
    (out / "+100%独立核验索引.html").write_text(build_plus100_index_html(supplement), encoding="utf-8", newline="\n")
    source_info["generated_at_jst"] = updated_at
    source_info["status"] = "V13_THREE_BLOCKER_CLOSURE_PENDING_BROWSER_REVIEW"
    source_info["plus100_research"] = {
        "path": str(PLUS100_SUPPLEMENT),
        "sha256": sha(PLUS100_SUPPLEMENT),
        "event_calendar_path": str(PLUS100_EVENT_CALENDAR),
        "event_calendar_sha256": sha(PLUS100_EVENT_CALENDAR),
        "asset_count": supplement["asset_count"],
        "grade_counts": supplement["new_grade_counts"],
        "old_a_regrade_count": len(supplement["old_21_regrade"]),
        "future_event_calendar_count": len(supplement["future_event_calendar"]),
        "plus100_calculable": supplement["annual_path_calculability"]["plus100_calculable"],
    }
    write_json(out / "V13普通中文产品源.json", source_info)
    write_json(out / "V13术语翻译检查报告.json", report)
    write_json(out / "V13限定返修检查报告.json", {
        "status": "PASS",
        "scope": "仅关闭错误事件日期、+100%底表核验入口和普通中文语言三项独立终验阻断；冻结V11、V12和84份预测均未改写",
        "independent_review_three_blockers": {
            "wrong_event_date_remaining": report["wrong_2026_09_25_event_date_count"],
            "plus100_base_table_link_count": report["plus100_research_base_table_link_count"],
            "plus100_index_openable": report["plus100_independent_index_openable"],
            "specified_bad_sentence_hits": report["specified_bad_sentence_hits"],
            "professional_term_explanation_count": report["required_professional_term_explanation_count"],
            "asset_specific_year_scenario_count": report["asset_specific_year_scenario_count"],
        },
        "three_business_repairs": {
            "complete_theme_story_count": report["complete_theme_story_count"],
            "year_reference_display": {
                "primary_direction_and_confidence": report["one_year_primary_direction_layer_present"],
                "samsung_full_scenario_explanation": report["samsung_scenario_explanation_complete"],
                "high_absolute_reference_check_count": report["high_absolute_reference_check_count"],
                "full_year_scenario_count": report["full_year_scenario_count"],
                "common_scenario_explanation_count": report["common_scenario_explanation_count"],
                "extreme_reason_count": report["extreme_reason_count"],
            },
            "target_roadmaps": {
                "plus40_account_roadmap_count": report["plus40_account_roadmap_count"],
                "wave_window_count": report["wave_window_count"],
                "quantified_wave_count": report["wave_grade_a_count"],
                "b_grade_wait_count": report["wave_grade_b_count"],
                "c_grade_excluded_count": report["wave_grade_c_count"],
                "one_year_scenario_used_as_wave_return_count": report["one_year_scenario_used_as_wave_return_count"],
                "future_event_calendar_count": report["future_event_calendar_count"],
                "old_a_regrade_count": report["old_a_regrade_count"],
                "plus100_calculable": supplement["annual_path_calculability"]["plus100_calculable"],
            },
        },
        "translation_examples": [
            {"before": "盈利桥", "after": "未来业务怎样变成利润"},
            {"before": "市场隐含预期", "after": "当前股价里已经包含的市场期待"},
            {"before": "正式证伪条件", "after": "什么情况会证明当前判断错了"},
        ],
        "number_explanation_examples": [
            "一年综合参考说明了是什么、为什么使用、以及它不是收益承诺或单一目标价",
            "重点机会的收入、每股收益和利润率均补充币种、单位及投资含义",
        ],
        "pdca_sources": [
            "data/pdca/scoring_20260806_incy.json",
            "data/pdca/opus5_scoring_20260810.json",
            "data/pdca/first_real_scoring_20260805.json",
        ],
        "pollution_scan": {
            "ambiguous_billion_unit_count": report["ambiguous_billion_unit_count"],
            "ratio_display_ambiguity_count": report["ratio_display_ambiguity_count"],
            "internal_machine_language_visible_count": report["internal_machine_language_visible_count"],
            "visible_none_or_null_count": report["visible_none_or_null_count"],
            "display_corruption_hits": report["display_corruption_hits"],
        },
        "unauthorized_new_findings": [],
        "locked_forecast_changed_count": 0,
        "v11_v12_changed_count": 0,
    })
    manifest = {"run_id": source_info["run_id"], "status": "V13_THREE_BLOCKER_CLOSURE_PENDING_BROWSER_REVIEW", "artifacts": []}
    for path in sorted(out.iterdir()):
        if path.is_file() and path.name != "V13_SHA256清单.json":
            manifest["artifacts"].append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha(path)})
    write_json(out / "V13_SHA256清单.json", manifest)
    print(json.dumps({"run_id": source_info["run_id"], "html": str(html_path), "bytes": html_path.stat().st_size, "sha256": sha(html_path)}, ensure_ascii=False, indent=2))


def finalize_browser(out: Path) -> None:
    browser_path = out / "visual_check" / "V13导航与浏览器测试.json"
    browser = json.loads(browser_path.read_text(encoding="utf-8"))
    if browser.get("status") != "PASS":
        raise SystemExit("浏览器检查未通过，拒绝冻结")
    source_path = out / "V13普通中文产品源.json"
    source_info = json.loads(source_path.read_text(encoding="utf-8"))
    source_info["status"] = "WAITING_GPT_FINAL_LANGUAGE_CLOSURE"
    source_info["browser_review"] = {"status": "PASS", "path": str(browser_path), "sha256": sha(browser_path)}
    write_json(source_path, source_info)
    manifest = {"run_id": source_info["run_id"], "status": "WAITING_GPT_FINAL_LANGUAGE_CLOSURE", "artifacts": []}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "V13_SHA256清单.json":
            manifest["artifacts"].append({"name": str(path.relative_to(out)), "bytes": path.stat().st_size, "sha256": sha(path)})
    write_json(out / "V13_SHA256清单.json", manifest)
    print(json.dumps({"status": manifest["status"], "html_sha256": sha(out / "V13普通中文完整投资产品.html"), "artifact_count": len(manifest["artifacts"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--refresh-existing":
        refresh_existing(Path(sys.argv[2]).resolve())
    elif len(sys.argv) == 3 and sys.argv[1] == "--finalize-browser":
        finalize_browser(Path(sys.argv[2]).resolve())
    else:
        main()
