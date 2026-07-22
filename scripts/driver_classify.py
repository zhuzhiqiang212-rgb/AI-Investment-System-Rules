#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""驱动分流·标的类型优先（派工单J1·2026-07-22）。别再用单一PE阈值(软银PE11控股被误判过去)。
先看标的类型再定驱动:
 - 控股/投资公司(软银9984)→控股/资产价值驱动·禁trailing·用NAV/SOTP
 - 加密资产代理(MSTR/COIN/CRCL)→加密资产价值驱动·禁trailing·用mNAV/持币NAV
 - 未上市(SpaceX)→未来/资产价值驱动·禁trailing·一级估值
 - 周期股(存储/半导体设备)→周期驱动·trailing高低都可能基数失真·禁简单trailing判贵·看跨周期常态
 - 稳态价值股(丰田/伊藤忠/东京海上/公用/军工/医药/诊断)→过去基本面驱动·trailing有效
 - 成长股→PE>40或高PEG=未来驱动·否则过去
★类型归类=Code据行业/公开事实判·须架构师核。阈值暂行。
被 gate3_v2.py / gate3_v2_holdings.py 共用(同口径不漂移)。"""

FUTURE_PE = 40.0

HOLDING_INVEST = {"JP.9984"}                       # 控股/投资公司→NAV
CRYPTO_PROXY = {"US.MSTR", "US.COIN", "US.CRCL"}     # 加密资产代理→mNAV/币价β
UNLISTED = {"US.SPCX"}                              # 未上市→一级估值
CYCLICAL = {"US.SNDK", "US.STX", "US.WDC", "US.KLAC", "JP.6857"}  # 存储/半导体设备→跨周期
STABLE_VALUE = {"JP.7203", "JP.8001", "JP.8766",   # 丰田/伊藤忠/东京海上
                "US.D", "US.PEG",                   # 公用
                "US.HII",                           # 军工
                "US.DGX", "US.GSK", "US.INCY", "JP.4568"}  # 诊断/医药(trailing代理·管线未来价值另需DCF)


def classify(code, pe, growth=None, industry=None):
    """返回 dict: 标的类型/驱动/禁trailing判贵(bool)/依据/估值口径。"""
    if code in HOLDING_INVEST:
        return {"标的类型": "控股/投资公司", "驱动": "控股/资产价值驱动(NAV)", "禁trailing判贵": True,
                "依据": f"控股/投资公司·价值=持仓资产NAV·trailing PE({pe})不反映(如软银PE低但价值在持仓)·禁用",
                "估值口径": "NAV/分部加总(SOTP)·待架构师/理解岗"}
    if code in CRYPTO_PROXY:
        return {"标的类型": "加密资产代理", "驱动": "加密资产价值驱动(mNAV/币价β)", "禁trailing判贵": True,
                "依据": "价值随加密资产(BTC等)波动·trailing PE无意义·禁用",
                "估值口径": "mNAV/持币NAV(见mnav_daily)"}
    if code in UNLISTED:
        return {"标的类型": "未上市", "驱动": "未来/资产价值驱动(未上市)", "禁trailing判贵": True,
                "依据": "未上市pre-IPO·无trailing PE·纯未来/一级估值",
                "估值口径": "一级市场估值/最新融资轮次·待架构师"}
    if code in CYCLICAL:
        return {"标的类型": "周期股(存储/半导体设备)", "驱动": "周期驱动(trailing基数失真风险)", "禁trailing判贵": True,
                "依据": f"跨周期·当前EPS可能处周期高/低点→trailing PE({pe})高低都可能基数失真·禁简单trailing判贵",
                "估值口径": "跨周期常态化EPS/PB周期底·待架构师"}
    if code in STABLE_VALUE:
        return {"标的类型": "稳态价值股", "驱动": "过去基本面驱动", "禁trailing判贵": False,
                "依据": f"稳态价值(消费/公用/保险/军工/医药)·trailing PE({pe})有效",
                "估值口径": "trailing PE/股息/DCF(医药管线未来价值另需DCF·标待接)"}
    # 默认成长股
    future = (pe is not None and pe > FUTURE_PE)
    return {"标的类型": "成长股", "驱动": ("未来预期驱动" if future else "过去基本面驱动"),
            "禁trailing判贵": future,
            "依据": (f"成长股·trailing PE={pe}>{FUTURE_PE}→市场为未来定价" if future
                   else f"成长股·trailing PE={pe}≤{FUTURE_PE}→现价基本由过去盈利支撑"),
            "估值口径": "成长PE/PEG"}
