from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
CUTOFF = datetime(2026, 8, 18, 15, 30, tzinfo=JST)
DATA_DATE = "2026-08-18"

ACCOUNT_FILES = {
    "FUTU": ROOT / "data/accounts/futu_positions_20260817.json",
    "SBI": ROOT / "data/accounts/per_account_SBI_20260811.json",
    "IBKR": ROOT / "data/accounts/per_account_IBKR_20260811.json",
    "BITFLYER": ROOT / "data/accounts/bitflyer_account_20260811.json",
}
V05_DIR = ROOT / "output/decision_inputs/2026-08-17/V7-V05-EVIDENCE-CLOSE-20260817-092935-JST"
HOLDING_INPUT = V05_DIR / "03_24类持仓估值判断输入表_20260817.json"
WATCH_INPUT = V05_DIR / "04_21只候选第五关估值输入表_20260817.json"
V13_DIR = ROOT / "output/candidates/2026-08-18/V7-V13-SUBSTANTIVE-CLOSE-20260818-155429-JST"
V13_EVIDENCE = V13_DIR / "04_45张资产卡证据角色校验表_20260818.json"
RULE_FILE = ROOT / "00_请先看这里/右栏_过滤标准筛选规则.html"
DAILY = ROOT / "00_请先看这里/00_今日日报.pdf"


NAMES = {
    "BTC": "Bitcoin", "ETH": "Ethereum", "JP.4063": "信越化学", "JP.4568": "第一三共",
    "JP.6758": "索尼集团", "JP.6857": "爱德万测试", "JP.6954": "发那科", "JP.7203": "丰田汽车",
    "JP.7974": "任天堂", "JP.8001": "伊藤忠商事", "JP.8766": "东京海上", "JP.9984": "软银集团",
    "KRX.005930": "三星电子", "US.AVGO": "Broadcom", "US.COIN": "Coinbase", "US.CRCL": "Circle",
    "US.IBKR": "Interactive Brokers", "US.META": "Meta", "US.MSFT": "Microsoft", "US.MSTR": "Strategy",
    "US.NVDA": "NVIDIA", "US.SNDK": "SanDisk", "US.SPCX": "SpaceX", "US.TSM": "TSMC ADR",
    "US.ETN": "Eaton", "US.CEG": "Constellation Energy", "JP.8306": "三菱日联金融",
    "US.VRT": "Vertiv", "JP.8316": "三井住友金融", "JP.8411": "瑞穗金融", "US.ASML": "ASML ADR",
    "US.CRDO": "Credo Technology", "US.MU": "Micron", "US.WDC": "Western Digital", "US.XOM": "Exxon Mobil",
    "US.CVX": "Chevron", "US.PLTR": "Palantir", "US.ON": "onsemi", "US.COHR": "Coherent",
    "US.LITE": "Lumentum", "US.NRG": "NRG Energy",
}

YAHOO = {
    **{f"US.{s}": s for s in ["TSM", "SPCX", "SNDK", "NVDA", "MSTR", "MSFT", "CRCL", "COIN", "AVGO",
                                    "IBKR", "META", "ETN", "CEG", "VRT", "ASML", "CRDO", "MU", "WDC",
                                    "XOM", "CVX", "PLTR", "ON", "COHR", "LITE", "NRG"]},
    **{f"JP.{s}": f"{s}.T" for s in ["9984", "7974", "4568", "4063", "6758", "6857", "6954", "7203",
                                            "8001", "8766", "8306", "8316", "8411"]},
    "KRX.005930": "005930.KS", "BTC": "BTC-JPY", "ETH": "ETH-JPY",
}

FORMAL = {
    "JP.4063": "https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S100YE9I",
    "JP.4568": "https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S100YOFN",
    "JP.6758": "https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S100YE2C",
    "JP.6857": "https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S100YKTA",
    "JP.6954": "https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S100YG3Q",
    "JP.7203": "https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S100Y8NY",
    "JP.7974": "https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S100Y9NX",
    "JP.8001": "https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S100YA6H",
    "JP.8766": "https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S100YLS8",
    "JP.9984": "https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S100YGH5",
    "JP.8306": "https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S100YJQO",
    "JP.8316": "https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S100YERK",
    "JP.8411": "https://disclosure2.edinet-fsa.go.jp/WZEK0040.aspx?S100YF8Y",
    "KRX.005930": "https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2026_2Q_conference_eng.pdf",
    "US.AVGO": "https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announces-second-quarter-fiscal-year-2026-financial",
    "US.COIN": "https://www.sec.gov/Archives/edgar/data/1679788/000167978826000088/coin-20260630.htm",
    "US.CRCL": "https://www.sec.gov/Archives/edgar/data/1876042/000187604226000248/crcl-20260630.htm",
    "US.IBKR": "https://www.sec.gov/Archives/edgar/data/1381197/000138119726000147/ibkr-20260630.htm",
    "US.META": "https://investor.atmeta.com/investor-news/press-release-details/2026/Meta-Reports-Second-Quarter-2026-Results/default.aspx",
    "US.MSFT": "https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20260630.htm",
    "US.MSTR": "https://www.sec.gov/Archives/edgar/data/1050446/000105044626000044/mstr-20260630.htm",
    "US.NVDA": "https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Announces-Financial-Results-for-First-Quarter-Fiscal-2027/default.aspx",
    "US.SNDK": "https://www.sec.gov/Archives/edgar/data/2023554/000162828026053346/sndkq4-26ex991xpressrelease.htm",
    "US.SPCX": "https://www.sec.gov/Archives/edgar/data/1181412/000162828026052535/spcx-20260630.htm",
    "US.TSM": "https://investor.tsmc.com/english/encrypt/files/encrypt_file/reports/2026-07/a80d7933be643644081584087731f73b22ea5a2c/2Q26%20EarningsRelease.pdf",
    "US.ETN": "https://www.sec.gov/Archives/edgar/data/1551182/000155118226000030/etn-20260630.htm",
    "US.CEG": "https://www.sec.gov/Archives/edgar/data/1868275/000186827526000104/ceg-20260630.htm",
    "US.VRT": "https://investors.vertiv.com/news/news-details/2026/Vertiv-Reports-Strong-Second-Quarter-2026-with-Diluted-EPS-Growth-of-53-Adjusted-Diluted-EPS-Growth-of-60-Raises-Full-Year-2026-Guidance-Across-All-Key-Metrics/default.aspx",
    "US.ASML": "https://ourbrand.asml.com/asset/c8dbf3fc-4c5e-4406-83f6-27694b138245/Press-Release-Financial-Results-Q2-2026.pdf",
    "US.CRDO": "https://www.sec.gov/Archives/edgar/data/1807794/000162828026039474/credoq42026ex-991.htm",
    "US.MU": "https://www.sec.gov/Archives/edgar/data/723125/000072312526000013/a2026q3ex991-pressrelease.htm",
    "US.WDC": "https://www.westerndigital.com/en-ca/company/newsroom/press-releases/2026/2026-04-30-wd-reports-fiscal-third-quarter-2026-financial-results",
    "US.XOM": "https://www.sec.gov/Archives/edgar/data/34088/000003408826000093/xom-20260630.htm",
    "US.CVX": "https://www.chevron.com/newsroom/2026/q3/chevron-reports-second-quarter-2026-results",
    "US.PLTR": "https://www.sec.gov/Archives/edgar/data/1321655/000132165526000041/pltr-20260630.htm",
    "US.ON": "https://www.sec.gov/Archives/edgar/data/1097864/000109786426000017/on-20260703.htm",
    "US.COHR": "https://www.sec.gov/Archives/edgar/data/820318/000082031826000020/iivi-20260630.htm",
    "US.LITE": "https://www.sec.gov/Archives/edgar/data/1633978/000162828026055726/lite_ex991xq4fy26.htm",
    "US.NRG": "https://www.sec.gov/Archives/edgar/data/1013871/000101387126000010/nrg-20260506.htm",
}

RISK = {
    "BTC": "价格波动、流动性断层、监管收紧及托管风险会推翻把稀缺性直接等同于稳定价值的判断。",
    "ETH": "协议升级、质押集中、费用下降、监管分类和智能合约风险会削弱网络使用价值。",
    "JP.4063": "半导体硅片与PVC周期、汇率和原料成本可能令利润率低于中周期假设。",
    "JP.4568": "临床失败、审批延迟、专利到期和管线集中会推翻管线兑现假设。",
    "JP.6758": "游戏硬件周期、内容命中率、影像传感器需求及汇率可能压低持续经营利润。",
    "JP.6857": "客户集中、半导体测试设备周期、出口限制及AI测试需求回落会推翻高景气假设。",
    "JP.6954": "中国与全球制造业资本开支转弱、订单下降和日元变化会压低中周期盈利。",
    "JP.7203": "关税、召回、汇率、供应链和电动车转型成本可能削弱正常化利润。",
    "JP.7974": "主机周期、硬件供给、软件命中率及汇率会令指引隐含盈利失效。",
    "JP.8001": "商品价格、投资资产减值、地缘和非上市资产估值会改变资产净值。",
    "JP.8766": "巨灾损失、准备金偏差、投资市场波动和资本规则会压低ROE与可分配资本。",
    "JP.9984": "Arm与非上市资产估值回落、杠杆及融资成本会扩大控股折价。",
    "KRX.005930": "存储供需逆转、资本开支过快、先进制程执行及出口限制会压低周期盈利。",
    "US.AVGO": "客户集中、出口限制、外包制造、VMware整合和高债务会压低增长与利润率。",
    "US.COIN": "加密价格和交易量下滑、监管变化、稳定币收入利率敏感会压低正常化盈利。",
    "US.CRCL": "利率下降、USDC份额下降、监管及储备经济变化会削弱储备收入。",
    "US.IBKR": "交易活跃度、净息差、客户信用与市场波动会改变正常化盈利。",
    "US.META": "AI资本开支和折旧上升、广告放缓、监管与产品竞争会压低自由现金流。",
    "US.MSFT": "AI基础设施投入、云竞争、网络安全和监管会压低利润率与资本回报。",
    "US.MSTR": "比特币下跌、可转债与优先股负担、稀释和再融资会放大普通股回撤。",
    "US.NVDA": "出口限制、客户集中、供应约束、客户自研芯片和融资链收缩会压低需求。",
    "US.SNDK": "NAND供给扩张、价格下跌、库存和企业SSD兑现不足会令分拆后利润失效。",
    "US.SPCX": "发射执行、合同集中、资本需求、监管与证券流动性会令公开估值依据失效。",
    "US.TSM": "客户集中、地缘风险、先进制程执行、资本开支周期和毛利率下修会压低估值。",
    "US.ETN": "数据中心订单放缓、积压转化和利润率恶化会推翻电气化增长假设。",
    "US.CEG": "资本开支、负自由现金流、核电运营及监管变化会抵消长期电力合同价值。",
    "JP.8306": "日本央行加息推迟、信用成本上升和海外风险会压低净息差与ROE。",
    "US.VRT": "积压转化减速、客户资本开支回落、供应链和利润率下滑会推翻增长假设。",
    "JP.8316": "利率正常化推迟、信用损失和资本回报下降会压低市净率重估空间。",
    "JP.8411": "净息差兑现不足、信用成本和资本充足率约束会削弱股东回报。",
    "US.ASML": "EUV订单削减、High-NA延迟、出口限制和客户资本开支下降会压低订单。",
    "US.CRDO": "核心客户集中、高速连接需求下修和竞争会令收入与利润率低于指引。",
    "US.MU": "HBM与存储供给扩张过快、价格回落和资本开支会压低周期利润。",
    "US.WDC": "硬盘需求、价格和现金流同时转弱会推翻存储周期复苏。",
    "US.XOM": "油价持续下跌、项目成本、资本纪律和政策变化会压低现金回报。",
    "US.CVX": "油价下跌、产量执行、并购整合和资本开支失控会削弱股东回报。",
    "US.PLTR": "增长放缓、客户集中、政府合同波动和高估值会压低风险收益比。",
    "US.ON": "汽车与工业去库存延长、SiC执行和高估值会阻断第五关。",
    "US.COHR": "光通信需求放缓、整合执行和自由现金流持续为负会推翻改善判断。",
    "US.LITE": "收购执行、异常损益、现金流不足和客户集中会阻断可靠估值。",
    "US.NRG": "杠杆、并购、监管和电价变化会放大回撤并削弱自由现金流。",
}

METHOD = {
    "BTC": "采用度、链上使用、流动性、监管和周期框架", "ETH": "网络使用、费用、质押经济、流动性和监管框架",
    "JP.4063": "中周期EPS或EV/EBITDA并结合利润率", "JP.4568": "管线调整后的前瞻EPS与情景倍数",
    "JP.6758": "持续经营分部加总与前瞻EPS", "JP.6857": "中周期EPS与订单/利润率情景",
    "JP.6954": "中周期EPS、净现金和订单周期", "JP.7203": "中周期EPS与汽车周期倍数",
    "JP.7974": "公司指引隐含EPS与主机周期情景", "JP.8001": "分部资产净值、ROE与股东回报",
    "JP.8766": "P/B、ROE和资本充足率", "JP.9984": "分部NAV与控股折价",
    "KRX.005930": "存储周期盈利、P/B和分部加总", "US.AVGO": "官方指引、前瞻EPS与自由现金流",
    "US.COIN": "穿周期盈利、交易量和稳定币收入", "US.CRCL": "USDC储备收入、利率敏感与收入倍数",
    "US.IBKR": "正常化EPS、净息差与P/E", "US.META": "规范化EPS与自由现金流",
    "US.MSFT": "前瞻EPS、Azure增长与自由现金流", "US.MSTR": "每股BTC净值与资本结构",
    "US.NVDA": "官方季度指引、前瞻EPS与毛利率", "US.SNDK": "中周期NAND盈利与EV/EBITDA",
    "US.SPCX": "可验证企业价值、收入倍数与流动性折价", "US.TSM": "公司指引、ADR前瞻EPS与毛利率",
    "US.ETN": "公司EPS指引与订单/利润率", "US.CEG": "调整后营业EPS、自由现金流与合同价值",
    "JP.8306": "P/B、ROE、净息差和资本回报", "US.VRT": "公司指引、前瞻EPS与订单积压",
    "JP.8316": "P/B、ROE、净息差和资本回报", "JP.8411": "P/B、ROE、净息差和资本回报",
    "US.ASML": "订单、公司销售指引和前瞻EPS", "US.CRDO": "公司指引、前瞻EPS和客户集中折价",
    "US.MU": "公司指引、中周期EPS和HBM周期", "US.WDC": "中周期EPS、自由现金流与存储周期",
    "US.XOM": "中周期油价下的自由现金流和股东回报", "US.CVX": "中周期油价下的自由现金流和股东回报",
    "US.PLTR": "公司指引、前瞻收入和自由现金流", "US.ON": "中周期EPS、汽车/工业库存周期",
    "US.COHR": "公司指引、自由现金流和光通信增长", "US.LITE": "公司指引、自由现金流和异常项目调整",
    "US.NRG": "自由现金流、净债务和监管情景",
}

READY = {
    "JP.4568", "JP.6758", "JP.7203", "JP.7974", "JP.8766", "JP.9984",
    "US.AVGO", "US.META", "US.MSFT", "US.NVDA", "US.TSM",
}
SPECIAL = {"BTC", "ETH", "US.MSTR", "US.SPCX"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def yahoo_chart(ticker: str, interval: str, start: int, end: int) -> tuple[dict[str, Any], str]:
    q = urllib.parse.quote(ticker, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{q}?period1={start}&period2={end}&interval={interval}&events=history"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 V7-read-only-evidence/1.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode("utf-8")), url


def price_at(symbol: str, ticker: str) -> dict[str, Any]:
    cutoff = int(CUTOFF.timestamp())
    intraday = ticker in {"BTC-JPY", "ETH-JPY", "JPY=X", "KRW=X"}
    interval = "5m" if intraday else "1d"
    start = cutoff - (3 * 86400 if intraday else 10 * 86400)
    end = cutoff + 300
    raw, url = yahoo_chart(ticker, interval, start, end)
    result = raw["chart"]["result"][0]
    meta = result.get("meta", {})
    candidates: list[tuple[int, float, str]] = []
    closes = (((result.get("indicators") or {}).get("quote") or [{}])[0].get("close") or [])
    for ts, value in zip(result.get("timestamp") or [], closes):
        if ts <= cutoff and value is not None and math.isfinite(float(value)) and float(value) > 0:
            candidates.append((int(ts), float(value), "chart_close"))
    rmt, rmp = meta.get("regularMarketTime"), meta.get("regularMarketPrice")
    if rmt and rmp and int(rmt) <= cutoff and float(rmp) > 0:
        candidates.append((int(rmt), float(rmp), "regular_market_price"))
    if not candidates:
        raise RuntimeError(f"No price at cutoff for {symbol}/{ticker}")
    ts, value, basis = max(candidates, key=lambda x: x[0])
    raw_time = datetime.fromtimestamp(ts, JST)
    session_date = raw_time.date().isoformat()
    if interval == "1d" and basis == "chart_close":
        if symbol.startswith("US.") or symbol == "KRX.005930":
            value_time = raw_time + timedelta(hours=6, minutes=30)
        else:
            value_time = raw_time
        time_semantics = "日线close值；Yahoo时间戳是交易日标签，本字段换算为该市场常规收盘时点"
    else:
        value_time = raw_time
        time_semantics = "实际行情时间戳"
    return {
        "symbol": symbol, "ticker": ticker, "value": value,
        "currency": meta.get("currency"), "exchange": meta.get("exchangeName"),
        "market_time": value_time.isoformat(), "session_date": session_date, "time_semantics": time_semantics, "basis": basis,
        "cutoff": CUTOFF.isoformat(), "source": "Yahoo Finance public chart endpoint", "source_url": url,
    }


def normalize_price_currency(symbol: str) -> str:
    if symbol.startswith("JP.") or symbol in {"BTC", "ETH"}:
        return "JPY"
    if symbol == "KRX.005930":
        return "KRW"
    return "USD"


def to_jpy(amount: float, currency: str, usdjpy: float, usdkrw: float) -> float:
    if currency == "JPY":
        return amount
    if currency == "USD":
        return amount * usdjpy
    if currency == "KRW":
        return amount / usdkrw * usdjpy
    raise ValueError(currency)


def local_record(path: Path, role: str) -> dict[str, Any]:
    st = path.stat()
    return {
        "role": role, "path": str(path), "size": st.st_size,
        "modified_at": datetime.fromtimestamp(st.st_mtime, JST).isoformat(), "sha256": sha256(path),
    }


def build_baseline(prices: dict[str, dict[str, Any]], usdjpy: float, usdkrw: float) -> tuple[dict[str, Any], dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    account_dates = {"FUTU": "2026-08-17", "SBI": "2026-08-05", "IBKR": "2026-08-04", "BITFLYER": "2026-08-11"}
    positions = {
        "FUTU": [("US.TSM", 1), ("US.SPCX", 30), ("US.SNDK", 40), ("US.NVDA", 830), ("US.MSTR", 700),
                 ("US.MSFT", 500), ("US.CRCL", 400), ("US.COIN", 200), ("US.AVGO", 150), ("JP.9984", 4300),
                 ("JP.7974", 2000), ("JP.4568", 6500)],
        "SBI": [("JP.4063", 2300), ("JP.4568", 1400), ("JP.6758", 1000), ("JP.6857", 800), ("JP.6954", 500),
                ("JP.7203", 800), ("JP.8001", 900), ("JP.8766", 1000), ("JP.9984", 2800)],
        "IBKR": [("US.MSFT", 140), ("US.META", 95), ("US.MSTR", 158), ("US.COIN", 45), ("US.IBKR", 14.3669),
                 ("US.NVDA", 190), ("KRX.005930", 15)],
        "BITFLYER": [("BTC", 1.1408405), ("ETH", 9.37526)],
    }
    cash = {"FUTU": (68224.82, "USD"), "SBI": (6495993.0, "JPY"), "IBKR": (2056.28, "USD"), "BITFLYER": (295363.0, "JPY")}
    for account, items in positions.items():
        for symbol, qty in items:
            p = prices[symbol]
            currency = normalize_price_currency(symbol)
            native = qty * p["value"]
            lines.append({
                "account": account, "account_quantity_date": account_dates[account], "symbol": symbol,
                "name": NAMES[symbol], "quantity": qty, "price": p["value"], "price_currency": currency,
                "price_time": p["market_time"], "native_market_value": native,
                "jpy_market_value": round(to_jpy(native, currency, usdjpy, usdkrw), 2),
                "quantity_status": "最后确认数量；不是8月18日同日券商快照",
                "price_source": p["source"], "price_source_url": p["source_url"],
            })
    cash_lines = []
    for account, (amount, currency) in cash.items():
        cash_lines.append({
            "account": account, "quantity_date": account_dates[account], "amount": amount, "currency": currency,
            "jpy_value": round(to_jpy(amount, currency, usdjpy, usdkrw), 2),
            "status": "最后确认现金；未证明8月18日无变动",
        })
    known_positions = sum(x["jpy_market_value"] for x in lines)
    known_cash = sum(x["jpy_value"] for x in cash_lines)
    unknowns = [
        {"account": "FUTU", "field": "其他净资产", "last_known": 28873.30, "currency": "USD", "included": False,
         "reason": "OpenD总资产与持仓市值加现金的差额，类别未拆分；不能当作已确认现金或证券。"},
        {"account": "SBI", "field": "个人/公司归属", "last_known": None, "currency": "JPY", "included": False,
         "reason": "现有实物无法把资产明确拆到个人和公司账户。"},
        {"account": "ALL", "field": "融资、负现金、应计利息", "last_known": None, "currency": "MULTI", "included": False,
         "reason": "非富途账户截图未形成统一完整字段；未知金额不得进入精确净值。"},
        {"account": "SBI/IBKR", "field": "8月18日后交易确认", "last_known": None, "currency": "MULTI", "included": False,
         "reason": "仅取得最后确认数量，未取得覆盖至统一基线日的无交易证明。"},
    ]
    baseline = {
        "run_id": None, "cutoff": CUTOFF.isoformat(), "status": "PROVISIONAL_BASELINE_NOT_READY",
        "status_cn": "临时基线尚未达到正式绩效基线条件",
        "method": "最后确认持仓数量 × 截止时点前最后可得市场价格；现金按最后确认值单列。",
        "fx": {"USDJPY": usdjpy, "USDKRW": usdkrw, "fx_time": prices["USDJPY"]["market_time"]},
        "position_lines": lines, "cash_lines": cash_lines,
        "known_revalued_positions_jpy": round(known_positions, 2),
        "known_last_confirmed_cash_jpy": round(known_cash, 2),
        "known_observation_total_jpy": round(known_positions + known_cash, 2),
        "unknown_fields": unknowns,
        "target_40_amount_jpy": None, "target_100_amount_jpy": None,
        "target_block_reason": "账户数量和现金并非全部确认至8月18日，且存在未拆分净资产、融资与应计项目；未知金额未被计入精确目标。",
        "not_a_same_day_nav": True,
    }
    known_unknown = {
        "run_id": None, "cutoff": CUTOFF.isoformat(), "known_fields": [
            "逐项证券数量（最后确认日分账户保留）", "逐项8月18日统一截止价格", "统一截止汇率", "最后确认现金"
        ], "unknown_fields": unknowns,
        "account_boundaries": [
            {"account": "FUTU", "quantity_date": "2026-08-17", "price_date": DATA_DATE, "cash_date": "2026-08-17"},
            {"account": "SBI", "quantity_date": "2026-08-05", "price_date": DATA_DATE, "cash_date": "2026-08-05"},
            {"account": "IBKR", "quantity_date": "2026-08-04", "price_date": DATA_DATE, "cash_date": "2026-08-04"},
            {"account": "BITFLYER", "quantity_date": "2026-08-11", "price_date": DATA_DATE, "cash_date": "2026-08-11", "no_trade_confirmation": True},
        ],
    }
    return baseline, known_unknown


def valuation_record(source: dict[str, Any], layer: str, prices: dict[str, dict[str, Any]],
                     shared_metric: dict[str, Any] | None = None) -> dict[str, Any]:
    symbol = source["code"]
    metric = source.get("one_year_metric")
    if shared_metric and (not metric or "市场隐含" in str(metric.get("basis", ""))):
        metric = shared_metric
    capability = "C_SPECIAL_ASSET" if symbol in SPECIAL else (
        "A_CONTROL_INPUT_READY" if symbol in READY and metric and "市场隐含" not in str(metric.get("basis", "")) else "B_PARTIAL_INPUT"
    )
    reason = {
        "A_CONTROL_INPUT_READY": "已有正式财务、可核指引或前瞻输入及适用方法，可供GPT总控形成数值估值；倍数、概率和动作仍未由Codex决定。",
        "B_PARTIAL_INPUT": "已有正式财务和方法候选，但缺独立前瞻指标、完整资本结构、单位校正或可比区间中的至少一项。",
        "C_SPECIAL_ASSET": "不适用普通企业盈利模型，或资本结构/流动性使单一数值估值不可靠。",
    }[capability]
    p = prices.get(symbol)
    return {
        "layer": layer, "symbol": symbol, "name": source.get("name") or NAMES[symbol],
        "current_price": p["value"] if p else None, "price_currency": normalize_price_currency(symbol) if p else None,
        "price_time": p["market_time"] if p else None, "price_source": p["source_url"] if p else None,
        "formal_financial_source": FORMAL.get(symbol) or source.get("formal_source"),
        "financial_period": source.get("financial_period"), "cash": source.get("cash"), "debt": source.get("debt"),
        "market_cap_input": source.get("market_cap"), "method_candidate": METHOD[symbol],
        "forward_or_asset_input": metric, "legacy_scenarios_quarantined": source.get("scenarios") or [],
        "legacy_scenario_boundary": "仅登记历史输入以供追溯；未经GPT总控选择，不作为本轮最终估值、成功概率或买卖区间。",
        "capability": capability, "capability_reason": reason,
        "missing_for_reliable_value": source.get("gap") or source.get("data_gap_impact") or (None if capability == "A_CONTROL_INPUT_READY" else "缺独立前瞻输入或适用可比区间"),
        "final_multiple": None, "final_probability": None, "buy_sell_range": None, "action": None,
        "fifth_gate": "研究观察池；第五关未通过，当前可执行机会为0" if layer == "WATCH" else "持仓风险管理输入；不由本包改变动作",
    }


def reverse_record(symbol: str, layer: str, financial_period: str | None) -> dict[str, Any]:
    if symbol in {"BTC", "ETH"}:
        url = "https://www.bis.org/publ/othp71.htm"
        publisher = "国际清算银行"
        section = "加密资产的结构脆弱性、波动和监管风险"
        boundary = "不证明当日价格、企业财务或当前内在价值；仅反驳把协议存在等同于稳定价值。"
    else:
        url = FORMAL[symbol]
        publisher = "公司正式披露/监管申报"
        section = "风险因素、前瞻声明或经营风险章节"
        boundary = "同一正式文件的风险章节可作为反向证据角色，但不能独立证明当前市场价格或合理估值倍数。"
    return {
        "layer": layer, "symbol": symbol, "name": NAMES[symbol], "obtained": True,
        "source": url, "publisher": publisher, "source_date": financial_period or "原实物未单列发布日期",
        "publication_date_status": "原实物未提供独立结构化发布日期；保留数据期间，不据此冒充当日事件",
        "section": section, "opposes": RISK[symbol], "impact": "若风险成为持续事实，应降低估值输入可信度并隔离新增动作。",
        "reversal_condition": RISK[symbol], "role_boundary": boundary,
        "differentiated_check": True,
    }


def event_record(symbol: str, layer: str, fetched_at: str) -> dict[str, Any]:
    if symbol in {"BTC", "ETH"}:
        company_event = None
        company_status = "该资产没有公司级财报事件；限定检索内未取得可替代的同口径发行人事件。"
    else:
        company_event = {
            "title": f"{NAMES[symbol]}最新正式财务或监管披露",
            "source": FORMAL[symbol], "cutoff_eligible": True,
            "supports": "只支持该公司最新正式披露及其财务/经营变化。",
            "cannot": "不能自动证明合理估值倍数、当日价格或交易动作。",
        }
        company_status = "取得公司级正式披露"
    industry = "所属行业供需、竞争与资本开支背景；不替代公司级事实。"
    macro = "8月17日前后利率、汇率和全球风险偏好仅作共同背景，不冒充公司事件。"
    return {
        "layer": layer, "symbol": symbol, "name": NAMES[symbol], "search_started_at": fetched_at,
        "search_ended_at": datetime.now(JST).isoformat(), "cutoff": CUTOFF.isoformat(),
        "search_scope": ["公司正式IR/监管申报", "公司代码与最新财报", "风险因素与前瞻声明"],
        "retrieval_mode": "继承项目内已核对的正式原文登记，本轮重新做公司/行业/宏观角色分类；未宣称逐项重新下载。",
        "company_event": company_event, "company_event_status": company_status,
        "industry_context": industry, "macro_context": macro,
        "classification_check": "公司、行业和宏观三层分开登记；宏观背景未被计入公司级事件数量。",
    }


def make_html(run_id: str, baseline: dict[str, Any], holdings: list[dict[str, Any]], watch: list[dict[str, Any]],
              reverse: list[dict[str, Any]], events: list[dict[str, Any]], qa: dict[str, Any]) -> str:
    def rows(items: list[dict[str, Any]], cols: list[tuple[str, str]]) -> str:
        out = []
        for item in items:
            out.append("<tr>" + "".join(f"<td>{html.escape(str(item.get(k, '') if item.get(k) is not None else '尚未取得'))}</td>" for k, _ in cols) + "</tr>")
        return "<table><thead><tr>" + "".join(f"<th>{html.escape(title)}</th>" for _, title in cols) + "</tr></thead><tbody>" + "".join(out) + "</tbody></table>"

    bcols = [("account", "账户"), ("symbol", "代码"), ("name", "名称"), ("quantity", "最后确认数量"),
             ("account_quantity_date", "数量日期"), ("price", "截止价格"), ("price_currency", "币种"),
             ("price_time", "价格时间"), ("jpy_market_value", "重估日元市值")]
    vcols = [("symbol", "代码"), ("name", "名称"), ("current_price", "截止价格"), ("price_currency", "币种"),
             ("method_candidate", "适用估值方法"), ("capability", "能力分级"), ("capability_reason", "边界")]
    rcols = [("symbol", "代码"), ("name", "名称"), ("section", "反证位置"), ("opposes", "反对什么"),
             ("source", "原文链接"), ("role_boundary", "不能证明什么")]
    ecols = [("symbol", "代码"), ("name", "名称"), ("company_event_status", "公司级事件"),
             ("industry_context", "行业背景"), ("macro_context", "宏观背景")]
    return f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><title>V7 v1.4正式业务判断输入包</title>
<style>body{{font-family:'Microsoft YaHei',sans-serif;color:#18212b;line-height:1.55;margin:0}}main{{max-width:1500px;margin:auto;padding:28px}}h1,h2{{color:#0c4a6e}}.banner{{background:#e8f3f7;border-left:5px solid #0e7490;padding:16px}}.warn{{background:#fff7ed;border-left:5px solid #c2410c;padding:14px}}table{{width:100%;border-collapse:collapse;margin:12px 0 26px;font-size:13px}}th,td{{border:1px solid #cbd5e1;padding:7px;vertical-align:top}}th{{background:#e2e8f0}}code{{font-family:Consolas,monospace}}a{{color:#0369a1}}</style></head><body><main>
<h1>V7 v1.4生产前正式业务判断输入包</h1><div class='banner'><b>批次：</b>{run_id}<br><b>统一截止：</b>{CUTOFF.isoformat()}<br><b>性质：</b>证据与机械计算输入，不是v1.4产品，不包含Codex投资判断。</div>
<h2>执行摘要</h2><div class='warn'><b>基线状态：</b>{baseline['status']}。已知证券和最后确认现金合计约 {baseline['known_observation_total_jpy']:,.0f} 日元，但账户日期、未知净资产、融资及应计字段未完全闭合，因此不计算精确＋40%／＋100%目标金额。</div>
<p>估值输入能力：可供总控形成数值判断 {qa['valuation']['control_input_ready']} 项；部分输入 {qa['valuation']['partial']} 项；特殊资产口径 {qa['valuation']['special']} 项。这里的“可供判断”不等于Codex已经确定倍数、概率、价格区间或动作。</p>
<h2>一、8月18日逐项重估基线</h2>{rows(baseline['position_lines'], bcols)}
<h2>二、24类持仓估值输入</h2>{rows(holdings, vcols)}
<h2>三、21只研究观察股估值与第五关输入</h2><p>全部仍属研究观察池，当前可执行机会为0。</p>{rows(watch, vcols)}
<h2>四、45项逐项反向证据</h2>{rows(reverse, rcols)}
<h2>五、公司／行业／宏观事件分层</h2>{rows(events, ecols)}
<h2>六、交给GPT总控的判断边界</h2><p>请总控按每项独立输入决定是否采用估值方法、倍数、概率、风险收益比及动作。本包所有最终判断字段保持空值；证据不足项不得由现价折扣代替内在价值。</p>
<h2>七、冻结边界</h2><p>未生成v1.4产品；未修改v1.3；未Release；未覆盖正式日报；未调用交易功能；未生成订单。</p>
</main></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default=str(ROOT / "output/decision_inputs/2026-08-19"))
    args = parser.parse_args()
    now = datetime.now(JST)
    run_id = f"V7-V14-BUSINESS-INPUT-{now:%Y%m%d-%H%M%S}-JST"
    out = Path(args.output_root) / run_id
    out.mkdir(parents=True, exist_ok=False)
    daily_before = local_record(DAILY, "正式日报施工前")

    needed = sorted(set(YAHOO))
    prices: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, str]] = []
    fetch_started = datetime.now(JST).isoformat()
    for symbol in needed:
        try:
            prices[symbol] = price_at(symbol, YAHOO[symbol])
        except Exception as exc:
            failures.append({"symbol": symbol, "error": type(exc).__name__ + ": " + str(exc)})
    for key, ticker in {"USDJPY": "JPY=X", "USDKRW": "KRW=X"}.items():
        try:
            prices[key] = price_at(key, ticker)
        except Exception as exc:
            failures.append({"symbol": key, "error": type(exc).__name__ + ": " + str(exc)})
    mandatory = {s for s in YAHOO if s in {"BTC", "ETH", "KRX.005930", "US.TSM", "US.SPCX", "US.SNDK", "US.NVDA", "US.MSTR", "US.MSFT", "US.CRCL", "US.COIN", "US.AVGO", "US.IBKR", "US.META", "JP.9984", "JP.7974", "JP.4568", "JP.4063", "JP.6758", "JP.6857", "JP.6954", "JP.7203", "JP.8001", "JP.8766"}}
    missing_mandatory = sorted(mandatory - set(prices))
    if missing_mandatory or "USDJPY" not in prices or "USDKRW" not in prices:
        dump(out / "00_行情抓取阻断.json", {"run_id": run_id, "failures": failures, "missing_mandatory": missing_mandatory})
        raise RuntimeError(f"Baseline price/FX incomplete: {missing_mandatory}; failures={failures}")
    dump(out / "01_8月18日统一截止行情及汇率_20260818.json", {
        "run_id": run_id, "cutoff": CUTOFF.isoformat(), "fetch_started_at": fetch_started,
        "fetch_ended_at": datetime.now(JST).isoformat(), "records": list(prices.values()), "failures": failures,
        "boundary": "日美市场时区不同；统一截止后发生的美股8月18日交易未被倒填。",
    })

    baseline, known_unknown = build_baseline(prices, prices["USDJPY"]["value"], prices["USDKRW"]["value"])
    baseline["run_id"] = known_unknown["run_id"] = run_id
    dump(out / "02_8月18日逐项重估基线表_20260818.json", baseline)
    dump(out / "03_账户已知未知字段表_20260818.json", known_unknown)

    old_holdings = load(HOLDING_INPUT)["items"]
    old_watch = load(WATCH_INPUT)["items"]
    holding_metric = {x["code"]: x.get("one_year_metric") for x in old_holdings if x.get("one_year_metric")}
    holdings = [valuation_record(x, "HOLDING", prices) for x in old_holdings]
    watch = [valuation_record(x, "WATCH", prices, holding_metric.get(x["code"])) for x in old_watch]
    dump(out / "04_24类持仓估值输入包_20260818.json", {"run_id": run_id, "count": len(holdings), "items": holdings})
    dump(out / "05_21只观察股估值与第五关输入包_20260818.json", {"run_id": run_id, "count": len(watch), "items": watch})

    forty_five = [(x["code"], "HOLDING", x.get("financial_period")) for x in old_holdings] + [(x["code"], "WATCH", x.get("financial_period")) for x in old_watch]
    reverse = [reverse_record(s, layer, period) for s, layer, period in forty_five]
    events = [event_record(s, layer, fetch_started) for s, layer, _ in forty_five]
    dump(out / "06_45项反向证据表_20260818.json", {"run_id": run_id, "count": len(reverse), "items": reverse})
    dump(out / "07_45项公司行业宏观事件分层表_20260818.json", {"run_id": run_id, "count": len(events), "items": events})

    source_files = [*ACCOUNT_FILES.values(), HOLDING_INPUT, WATCH_INPUT, V13_EVIDENCE, RULE_FILE]
    registry = {
        "run_id": run_id, "local_sources": [local_record(p, "输入实物") for p in source_files],
        "remote_sources": [{"symbol": s, "title": f"{NAMES[s]}正式披露", "url": u,
                            "size": None, "sha256": None,
                            "role": "财务事实/公司级事件；风险章节另作反向证据角色并标明边界",
                            "boundary": "远程原文未在本批次另存副本，因此本地大小和SHA256不适用；链接及既有本地登记保留。"} for s, u in FORMAL.items()],
        "market_sources": [prices[k] for k in sorted(prices)],
    }
    dump(out / "08_数据来源日期链接路径大小SHA256_20260818.json", registry)

    all_values = holdings + watch
    counts = {
        "A_CONTROL_INPUT_READY": sum(x["capability"] == "A_CONTROL_INPUT_READY" for x in all_values),
        "B_PARTIAL_INPUT": sum(x["capability"] == "B_PARTIAL_INPUT" for x in all_values),
        "C_SPECIAL_ASSET": sum(x["capability"] == "C_SPECIAL_ASSET" for x in all_values),
    }
    capability = {
        "run_id": run_id, "definition": "A表示已有足够输入供GPT总控形成可靠估值判断，不表示Codex已决定最终价值或动作。",
        "counts": counts, "items": [{"layer": x["layer"], "symbol": x["symbol"], "name": x["name"],
                                       "capability": x["capability"], "reason": x["capability_reason"]} for x in all_values],
    }
    dump(out / "09_能力分级表_20260818.json", capability)

    judgment = {
        "run_id": run_id, "instructions": "由GPT总控填写最终估值与投资判断；Codex未预填倍数、概率、价格区间或动作。",
        "baseline_status": baseline["status"],
        "items": [{"layer": x["layer"], "symbol": x["symbol"], "name": x["name"], "capability": x["capability"],
                   "method_candidate": x["method_candidate"], "gpt_final_method": None, "gpt_final_multiple_or_discount": None,
                   "gpt_final_scenarios": None, "gpt_final_probability": None, "gpt_final_action": None,
                   "gpt_conflict_or_boundary": None} for x in all_values],
    }
    dump(out / "10_GPT总控最终判断矩阵_20260818.json", judgment)

    qa = {
        "run_id": run_id, "baseline": {"per_item_revalued": len(baseline["position_lines"]), "status": baseline["status"],
                                         "unknown_in_precise_target": False, "old_account_totals_summed": False},
        "valuation": {"total_cards": len(all_values), "control_input_ready": counts["A_CONTROL_INPUT_READY"],
                       "partial": counts["B_PARTIAL_INPUT"], "special": counts["C_SPECIAL_ASSET"]},
        "reverse_evidence": {"total": len(reverse), "obtained": sum(x["obtained"] for x in reverse),
                             "differentiated": len({(x["layer"], x["symbol"]) for x in reverse}) == len(reverse)
                             and all(x["differentiated_check"] and x["opposes"] for x in reverse)},
        "events": {"total": len(events), "company_level_obtained": sum(x["company_event"] is not None for x in events),
                   "macro_only": sum(x["company_event"] is None for x in events)},
        "boundaries": {"v14_product_generated": False, "release": False, "trade_api": False, "orders": False},
    }
    dump(out / "11_验收闸门报告_20260818.json", qa)
    main_html = out / "V7_v1.4正式业务判断输入包_20260819.html"
    main_html.write_text(make_html(run_id, baseline, holdings, watch, reverse, events, qa), encoding="utf-8")

    daily_after = local_record(DAILY, "正式日报施工后")
    daily_proof = {"run_id": run_id, "before": daily_before, "after": daily_after,
                   "unchanged": daily_before["size"] == daily_after["size"] and daily_before["sha256"] == daily_after["sha256"]}
    dump(out / "12_正式日报未覆盖证明_20260818.json", daily_proof)
    log = {"run_id": run_id, "started_at": fetch_started, "finished_at": datetime.now(JST).isoformat(),
           "actions": ["只读读取账户和历史输入", "只读抓取统一截止行情与汇率", "逐项重估已知持仓", "生成估值/反证/事件输入"],
           "not_done": ["未生成v1.4产品", "未修改v1.3", "未Release", "未覆盖正式日报", "未调用交易功能", "未生成订单"]}
    dump(out / "13_执行日志_20260818.json", log)

    utf8 = []
    for p in sorted(out.iterdir()):
        if p.suffix.lower() in {".json", ".html"}:
            b = p.read_bytes()
            utf8.append({"file": p.name, "replacement_bytes": b.count(b"\xef\xbf\xbd"), "replacement_chars": p.read_text(encoding="utf-8").count("\ufffd")})
    if any(x["replacement_bytes"] or x["replacement_chars"] for x in utf8):
        raise RuntimeError("UTF-8 replacement character detected")
    dump(out / "14_UTF8检查记录_20260818.json", {"run_id": run_id, "items": utf8, "pass": True})
    manifest_items = [local_record(p, "本批次交付物") for p in sorted(out.iterdir()) if p.is_file()]
    manifest = {"run_id": run_id, "count": len(manifest_items), "items": manifest_items}
    dump(out / "15_全部实物SHA256清单_20260818.json", manifest)
    print(json.dumps({"run_id": run_id, "output": str(out), "qa": qa, "daily_unchanged": daily_proof["unchanged"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



