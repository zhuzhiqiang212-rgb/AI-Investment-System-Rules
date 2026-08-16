#!/usr/bin/env python3
"""Build the returned v0.4 candidate into the complete v0.5 candidate."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
SOURCE_RUN = "V7-V04-COMPLETE-20260817-012432-JST"
SOURCE = ROOT / "output/candidates/2026-08-17" / SOURCE_RUN
FUTU = ROOT / "data/accounts/futu_positions_20260817.json"
DAILY = ROOT / "00_请先看这里/00_今日日报.pdf"
USDJPY = 159.304993


VALUATIONS: dict[str, dict[str, str]] = {
    "US.MSFT": {"method": "自由现金流收益率、预期市盈率和Azure增长交叉验证。", "view": "合理至合理偏高，继续持有观察。", "basis": "盈利质量和现金流强，但AI资本开支高，价格需要由Azure增长与自由现金流继续支撑。"},
    "US.META": {"method": "自由现金流收益率、预期市盈率和广告增长，并单列AI资本开支。", "view": "合理至合理偏高，继续持有观察。", "basis": "广告现金流与利润率提供支撑，主要折价因素是资本开支上升和监管风险。"},
    "JP.8766": {"method": "市净率、净资产收益率、综合成本率和投资收益。", "view": "合理至合理偏高，继续持有观察。", "basis": "利率正常化可能改善投资收益，但灾害损失和市场波动会改变合理估值。"},
    "JP.6758": {"method": "分部加总估值，结合持续经营利润、市盈率和娱乐资产价值。", "view": "合理至合理偏高，继续持有观察。", "basis": "必须以持续经营业务为主，不能把拆分造成的总体会计亏损直接当作核心经营恶化。"},
    "JP.7203": {"method": "中周期市盈率、市净率、汽车营业利润率和净现金。", "view": "合理至合理偏高，继续持有观察。", "basis": "规模和混动优势提供支撑，汇率、关税与周期利润率限制上行空间。"},
    "JP.8001": {"method": "资产净值折价、市盈率、净资产收益率和股东回报。", "view": "合理至合理偏高，继续持有观察。", "basis": "多元业务与资本配置提供分散，商品周期和资产处置收益需分开看。"},
    "JP.4063": {"method": "中周期市盈率、企业价值/息税折旧摊销前利润和利润率。", "view": "合理至合理偏高，继续持有观察。", "basis": "材料壁垒和高利润率支撑估值，但半导体及PVC周期仍会造成盈利波动。"},
    "JP.4568": {"method": "风险调整后的管线价值与成熟产品利润，并用市盈率交叉检查。", "view": "合理至合理偏高，继续持有观察。", "basis": "核心管线兑现决定主要价值，监管、临床和商业化失败会迅速改变判断。"},
    "JP.7974": {"method": "净现金调整后市盈率、硬件装机量和软件生命周期利润。", "view": "合理至合理偏高，继续持有观察。", "basis": "平台和IP质量高，但硬件周期与软件兑现已被市场部分计价。"},
    "US.IBKR": {"method": "市盈率、市净率、净资产收益率和客户资产增长。", "view": "合理至合理偏高，继续持有观察。", "basis": "低成本平台和利息收入支撑盈利，利率回落及交易活跃度下降会压缩估值。"},
    "US.NVDA": {"method": "预期市盈率、增长调整市盈率、数据中心收入和毛利率。", "view": "估值偏高或周期位置较高。", "basis": "Blackwell与Rubin需求仍强，但高增长预期、融资链和客户自研已要求更大安全垫。"},
    "US.AVGO": {"method": "预期市盈率、自由现金流收益率、AI收入与VMware协同。", "view": "估值偏高或周期位置较高。", "basis": "定制芯片和网络需求强，客户集中、整合兑现和高估值同时放大失望风险。"},
    "JP.9984": {"method": "持有资产净值折价，扣除净债务并单列上市与非上市资产。", "view": "估值偏高或周期位置较高。", "basis": "AI代理敞口提供弹性，但净值折价、融资结构和高久期资产会放大波动。"},
    "JP.6857": {"method": "中周期预期市盈率、订单、测试需求和营业利润率。", "view": "估值偏高或周期位置较高。", "basis": "AI测试需求强，但设备周期和高预期使订单或利润率放缓的杀伤更大。"},
    "US.SNDK": {"method": "中周期市盈率、企业价值/息税折旧摊销前利润、NAND价格和企业SSD利润率。", "view": "估值偏高或周期位置较高。", "basis": "价格、拆股和正式财报已闭合；券商收益率25.21%与成本计算19.19%的差异继续隔离，不支持估值或动作。"},
    "US.TSM": {"method": "预期市盈率、自由现金流、先进制程利用率和毛利率。", "view": "估值偏高或周期位置较高。", "basis": "AI/HPC和先进制程质量高，但资本开支、地缘风险和高预期要求等待更好价格或财报确认。"},
    "JP.6954": {"method": "中周期市盈率、净现金、订单和自动化周期利润率。", "view": "估值偏高或周期位置较高。", "basis": "资产负债表稳健，但订单恢复尚未完全验证，周期高点估值不宜外推。"},
    "US.MSTR": {"method": "每股比特币净资产溢价、可转债与优先融资义务、稀释风险。", "view": "传统估值适用性弱，投机性和不确定性高。", "basis": "本质是带资本结构放大的比特币敞口；净资产溢价和融资条件比传统利润倍数更重要。"},
    "US.COIN": {"method": "企业价值/调整后利润、交易费率、订阅服务收入和加密周期。", "view": "传统估值适用性较弱，投机性和不确定性高。", "basis": "收入来源相对多元，但交易量、监管和加密价格会使利润与估值剧烈变化。"},
    "US.CRCL": {"method": "收入倍数、储备收入、USDC流通量和利率敏感性。", "view": "传统估值适用性较弱，投机性和不确定性高。", "basis": "稳定币基础设施逻辑存在，但收入受利率、监管和USDC增长共同影响。"},
    "US.SPCX": {"method": "非上市同业与收入倍数，加入流动性折价和公开信息折价。", "view": "传统估值适用性较弱，投机性和不确定性高。", "basis": "公开财务和流动性不足，无法形成可靠内在价值或可执行价格动作。"},
    "BTC": {"method": "不使用企业现金流模型；观察网络采用、流动性、监管和周期位置。", "view": "传统估值不适用，投机性和不确定性高。", "basis": "没有经营现金流锚，价格主要由流动性、采用率和风险偏好决定。"},
    "ETH": {"method": "不使用企业现金流模型；观察网络使用、质押经济、费用和监管。", "view": "传统估值不适用，投机性和不确定性高。", "basis": "协议价值与网络活动相关，但竞争、技术和监管会显著改变定价。"},
    "KRX.005930": {"method": "市净率、分部加总、存储周期盈利和股东回报。", "view": "基本面估值可能处于合理区，但旧账户价格不产生交易动作。", "basis": "存储修复和资产质量提供支撑；账户价格日期为2026-08-04，不能冒充当日价格。"},
}


HOLDING_TIMES: dict[str, dict[str, str]] = {
    "US.MSFT": {"short": "未来1—3个月看Azure增速、AI资本开支和自由现金流。", "long": "未来6—12个月看AI投入能否转化为云收入和每股现金流。", "success": "Azure增速与自由现金流同步改善。", "failure": "资本开支上升但云增速和利润率持续下滑。", "review": "下一次微软季度财报及指引发布后。"},
    "JP.9984": {"short": "看日元、利率、上市资产净值和融资成本。", "long": "看AI资产退出、Arm及非上市资产价值兑现。", "success": "净值增长且折价不扩大。", "failure": "净债务压力上升或主要AI资产估值持续下修。", "review": "下一次软银季度业绩及BOJ政策会议后。"},
    "US.NVDA": {"short": "看Blackwell交付、数据中心指引、毛利率和融资链风险。", "long": "看Rubin换代、客户资本开支和自研芯片替代速度。", "success": "收入与毛利率达到或超过公司指引。", "failure": "订单、毛利率或主要客户资本开支连续下修。", "review": "下一次NVIDIA季度财报及主要云厂资本开支更新后。"},
    "JP.6857": {"short": "看测试设备订单、交付和利润率。", "long": "看AI芯片复杂度能否抵消设备周期回落。", "success": "订单和利润率同时兑现。", "failure": "订单拐头向下且利润率恶化。", "review": "下一次爱德万测试季度业绩发布后。"},
    "JP.4568": {"short": "看核心管线监管节点和商业化进度。", "long": "看新产品销售能否替代成熟产品波动。", "success": "关键临床或监管节点达成且销售爬坡。", "failure": "核心管线失败、延期或商业化明显低于计划。", "review": "下一次核心管线数据或第一三共季度业绩后。"},
    "JP.7974": {"short": "看硬件销量、供货和首批软件销量。", "long": "看装机量、第一方软件和利润率形成新周期。", "success": "硬件与高毛利软件同步超预期。", "failure": "装机或软件转化持续低于公司目标。", "review": "下一次任天堂销量更新和季度财报后。"},
    "JP.4063": {"short": "看半导体材料订单、PVC价格和利润率。", "long": "看先进制程材料份额与周期利润中枢。", "success": "高附加值材料增长抵消周期业务波动。", "failure": "主要产品量价齐跌并压缩现金流。", "review": "下一次信越化学季度业绩后。"},
    "US.MSTR": {"short": "看比特币价格、净资产溢价和融资条款。", "long": "看稀释、债务与比特币每股敞口是否改善。", "success": "每股比特币敞口增长且融资成本可控。", "failure": "净资产溢价收缩并伴随融资或再融资压力。", "review": "下一次Strategy财报或重大融资公告后。"},
    "BTC": {"short": "看全球流动性、监管和现货资金流。", "long": "看机构采用、网络安全和周期回撤结构。", "success": "采用和流动性改善且回撤受控。", "failure": "监管、托管或流动性冲击导致结构性需求下降。", "review": "下一次月度风险复盘及重大监管事件后。"},
    "ETH": {"short": "看链上活动、质押收益和监管。", "long": "看扩容、费用捕获和竞争链份额。", "success": "网络使用与费用价值同步改善。", "failure": "活动和费用持续流失或监管限制升级。", "review": "下一次月度链上复盘及协议重大升级后。"},
    "US.SNDK": {"short": "看NAND价格、企业SSD合同兑现、利润率及券商收益率口径说明。", "long": "看供需纪律、企业级份额和自由现金流穿越周期。", "success": "价格与企业SSD收入上升并转化为利润和现金流。", "failure": "供应扩张压低价格，或利润率与合同兑现转弱。", "review": "下一次Sandisk季度财报及券商成本口径核对后。"},
    "US.AVGO": {"short": "看AI网络、定制芯片收入和VMware利润。", "long": "看客户集中度、定制芯片份额和整合现金流。", "success": "AI收入与自由现金流持续高增长。", "failure": "主要客户削减订单或VMware兑现低于计划。", "review": "下一次Broadcom季度财报后。"},
    "US.META": {"short": "看广告增长、AI资本开支和自由现金流。", "long": "看AI推荐与广告效率能否覆盖基础设施投入。", "success": "收入与现金流增速足以覆盖资本开支。", "failure": "投入上升而广告增速和利润率连续下滑。", "review": "下一次Meta季度财报及资本开支指引后。"},
    "JP.8766": {"short": "看保费、综合成本率、投资收益和灾害损失。", "long": "看利率正常化对净资产收益率和股东回报的提升。", "success": "承保利润和投资收益同步改善。", "failure": "灾害损失或市场波动持续侵蚀资本。", "review": "下一次东京海上季度业绩及BOJ会议后。"},
    "US.COIN": {"short": "看交易量、费率、订阅收入和监管进展。", "long": "看非交易收入能否降低加密周期依赖。", "success": "调整后利润为正且收入结构继续多元化。", "failure": "交易份额、费率和监管环境同时恶化。", "review": "下一次Coinbase季度财报和重大监管决定后。"},
    "US.CRCL": {"short": "看USDC流通量、储备收入和监管落地。", "long": "看支付、结算和银行基础设施能否形成持续收入。", "success": "USDC增长并降低单纯利息收入依赖。", "failure": "利率下降、份额流失或监管限制压缩盈利。", "review": "下一次Circle季度财报及监管更新后。"},
    "JP.6758": {"short": "看持续经营利润、游戏影视音乐分部和拆分影响。", "long": "看娱乐IP、传感器和资本配置能否提升整体回报。", "success": "持续经营利润与现金流稳定增长。", "failure": "核心分部利润持续下修且拆分未释放价值。", "review": "下一次Sony季度业绩和分部披露后。"},
    "JP.6954": {"short": "看自动化订单、机器人需求和利润率。", "long": "看制造业资本开支周期与中国需求恢复。", "success": "订单恢复并转化为利润和现金流。", "failure": "订单持续疲弱或价格竞争压缩利润率。", "review": "下一次发那科季度订单与业绩后。"},
    "JP.7203": {"short": "看销量、汇率、关税和营业利润率。", "long": "看混动优势、软件投入和资本回报。", "success": "销量与利润率在关税压力下保持韧性。", "failure": "主要市场销量和利润率同步下滑。", "review": "下一次丰田季度业绩及销量更新后。"},
    "JP.8001": {"short": "看资源价格、非资源利润和股东回报。", "long": "看资产组合优化和净资产收益率。", "success": "非资源增长与回购分红共同提升每股价值。", "failure": "商品周期和投资减值显著拖累现金流。", "review": "下一次伊藤忠季度业绩与资本配置公告后。"},
    "US.SPCX": {"short": "看公开披露、融资、流动性和发射执行。", "long": "看Starlink现金流、发射频率和资本需求。", "success": "经营里程碑兑现且公开财务透明度提高。", "failure": "融资条件恶化、执行延误或流动性折价扩大。", "review": "下一次SpaceX正式披露或重大融资公告后。"},
    "KRX.005930": {"short": "看DRAM/NAND价格、HBM进度和韩元汇率。", "long": "看存储周期、先进封装和资本回报。", "success": "存储利润恢复且HBM竞争力改善。", "failure": "价格转弱或先进存储份额持续落后。", "review": "下一次Samsung季度业绩；账户动作等待新截图。"},
    "US.IBKR": {"short": "看客户资产、净利息收入和交易活跃度。", "long": "看账户增长、费用效率和资本回报。", "success": "客户资产和每股盈利持续增长。", "failure": "利率回落与交易降温共同压缩利润。", "review": "下一次IBKR月度账户数据和季度财报后。"},
    "US.TSM": {"short": "看月度收入、AI/HPC需求、先进制程利用率和毛利率。", "long": "看2纳米、海外产能和资本开支回报。", "success": "先进制程收入和毛利率达到指引。", "failure": "客户削减订单、毛利率下修或地缘风险升级。", "review": "下一次TSM月度营收与季度财报后。"},
}


CANDIDATE_GATE5: dict[str, dict[str, str]] = {
    "US.ETN": {"catalyst": "数据中心订单、积压转收入和利润率提升。", "risk": "订单放缓、积压取消或利润率恶化。", "failure": "连续两个披露期订单或利润率明显低于指引。"},
    "US.CEG": {"catalyst": "长期电力合同、核电利用率和数据中心电力需求。", "risk": "资本开支、负自由现金流和项目执行。", "failure": "资本开支与负自由现金流持续恶化，合同回报不能覆盖资金成本。"},
    "JP.8306": {"catalyst": "净息差、BOJ正常化、信贷增长和股东回报。", "risk": "加息推迟、信用成本上升或债券损失。", "failure": "净息差不改善且信用成本显著上升。"},
    "JP.8316": {"catalyst": "净息差、BOJ政策、费用收入和资本回报。", "risk": "加息推迟、海外信用风险和市场损失。", "failure": "利率利好未转化为利润，信用成本持续超预期。"},
    "JP.8411": {"catalyst": "净息差、BOJ政策、重组效率和股东回报。", "risk": "加息推迟、信用成本和执行落差。", "failure": "成本改善停滞并伴随资产质量恶化。"},
    "US.TSM": {"catalyst": "AI/HPC收入、先进制程利用率和毛利率。", "risk": "客户削减订单、资本开支回报与地缘风险。", "failure": "先进制程订单或毛利率下修，或地缘风险明显升级。"},
    "US.VRT": {"catalyst": "数据中心订单积压、收入兑现和利润率。", "risk": "积压转化放缓、供应瓶颈或估值压缩。", "failure": "积压转收入速度和利润率连续低于指引。"},
    "US.ASML": {"catalyst": "EUV订单、High-NA进度和客户资本开支。", "risk": "订单削减、出口限制和交付延迟。", "failure": "EUV订单显著下修或出口限制扩大到核心市场。"},
    "US.CRDO": {"catalyst": "高速连接收入和新客户放量。", "risk": "客户集中、产品周期和高估值。", "failure": "核心客户需求下修或新客户扩张未兑现。"},
    "US.MU": {"catalyst": "HBM供需、存储价格和产能利用率。", "risk": "供应扩张过快、价格回落和周期反转。", "failure": "HBM或传统存储价格与利润率同时下跌。"},
    "US.WDC": {"catalyst": "硬盘及存储周期、企业需求和自由现金流。", "risk": "价格与需求同步转弱或资本开支失控。", "failure": "平均售价、出货和自由现金流连续恶化。"},
    "US.XOM": {"catalyst": "油价、产量增长、资本纪律和股东回报。", "risk": "油价持续下跌、成本上升或项目回报下降。", "failure": "低油价与资本开支上升同时侵蚀自由现金流。"},
    "US.CVX": {"catalyst": "产量、项目投产、资本纪律和回购分红。", "risk": "油价下跌、并购整合和项目执行。", "failure": "项目延误或资本纪律恶化导致自由现金流持续低于计划。"},
    "US.NVDA": {"catalyst": "Blackwell/Rubin交付、数据中心需求和毛利率。", "risk": "融资链、客户自研、出口限制和高估值。", "failure": "数据中心指引或毛利率连续下修。"},
    "US.AVGO": {"catalyst": "AI网络、定制芯片和VMware现金流兑现。", "risk": "客户集中、整合落差和资本开支放缓。", "failure": "AI收入指引下修或VMware现金流不达计划。"},
    "US.SNDK": {"catalyst": "NAND价格、企业SSD合同兑现和利润率。", "risk": "供应扩张、价格回落及券商收益率口径未解释。", "failure": "NAND价格、企业SSD收入和利润率同时转弱。"},
    "US.PLTR": {"catalyst": "收入增长、客户扩张和营业利润率。", "risk": "高估值是当前主要阻断，合同兑现不足会放大回撤。", "failure": "客户增速或利润率下修，无法支持当前估值。"},
    "US.ON": {"catalyst": "汽车及工业去库存、SiC进展和利润率恢复。", "risk": "当前极高市盈率、周期需求和SiC执行。", "failure": "去库存延长、SiC进展落后或盈利不能支持估值。"},
    "US.COHR": {"catalyst": "光通信增长、数据中心需求和自由现金流改善。", "risk": "负自由现金流、债务和需求波动。", "failure": "光通信增长未转化为正自由现金流。"},
    "US.LITE": {"catalyst": "光器件需求、收购整合和异常损益消退。", "risk": "现金流、会计项目和整合成本尚未闭合。", "failure": "收购后收入未兑现且现金流或异常损益继续恶化。"},
    "US.NRG": {"catalyst": "电力需求、并购协同、负债下降和资本回报。", "risk": "杠杆、监管和零售电力利润波动。", "failure": "并购后负债不降或监管变化显著压缩回报。"},
}


CANDIDATE_TIMES: dict[str, dict[str, str]] = {
    "US.ETN": {"short": "1—3个月看订单、积压和利润率。", "long": "6—12个月看数据中心电力收入与资本回报。", "success": "订单和利润率共同提升。", "failure": "订单或利润率连续放缓。", "review": "下一次ETN季度财报。"},
    "US.CEG": {"short": "看电力合同、核电利用率和自由现金流。", "long": "看数据中心负荷与资本开支回报。", "success": "合同回报覆盖资本开支。", "failure": "负自由现金流持续恶化。", "review": "下一次CEG季度财报或长期电力合同公告。"},
    "JP.8306": {"short": "看BOJ会议、净息差和信用成本。", "long": "看利率正常化与股东回报。", "success": "净息差改善且信用成本受控。", "failure": "加息推迟并伴随信用成本上升。", "review": "下一次BOJ会议和MUFG季度业绩。"},
    "JP.8316": {"short": "看BOJ会议、净息差和海外信用风险。", "long": "看费用收入与资本效率。", "success": "利润与股东回报同步改善。", "failure": "海外损失抵消利率收益。", "review": "下一次BOJ会议和SMFG季度业绩。"},
    "JP.8411": {"short": "看净息差、成本改革和信用损失。", "long": "看重组效率和资本回报。", "success": "成本下降且净息差改善。", "failure": "资产质量或成本控制恶化。", "review": "下一次BOJ会议和瑞穗季度业绩。"},
    "US.TSM": {"short": "看月度收入、先进制程和毛利率。", "long": "看2纳米、海外产能和资本回报。", "success": "AI/HPC与毛利率达到指引。", "failure": "订单、毛利率或地缘风险恶化。", "review": "下一次月度营收与季度财报。"},
    "US.VRT": {"short": "看积压转收入和利润率。", "long": "看数据中心扩建周期与服务收入。", "success": "积压、收入和利润率同步兑现。", "failure": "积压转化明显减速。", "review": "下一次VRT季度财报。"},
    "US.ASML": {"short": "看EUV订单和High-NA交付。", "long": "看先进制程设备需求与出口边界。", "success": "订单和交付维持增长。", "failure": "订单削减或出口限制扩大。", "review": "下一次ASML订单与季度业绩。"},
    "US.CRDO": {"short": "看高速连接收入和客户集中度。", "long": "看多客户扩张与产品份额。", "success": "核心收入增长且集中度下降。", "failure": "核心客户需求下修。", "review": "下一次CRDO季度财报。"},
    "US.MU": {"short": "看HBM供需、价格和产能。", "long": "看存储周期利润和现金流。", "success": "价格与利润率保持上升。", "failure": "供应扩张导致价格下跌。", "review": "下一次MU季度财报与存储价格更新。"},
    "US.WDC": {"short": "看硬盘价格、需求和现金流。", "long": "看企业存储周期与资本纪律。", "success": "售价和自由现金流改善。", "failure": "价格与需求同时转弱。", "review": "下一次WDC季度财报。"},
    "US.XOM": {"short": "看油价、产量和资本开支。", "long": "看低成本项目和股东回报。", "success": "自由现金流覆盖投资与回报。", "failure": "油价下跌并伴随资本纪律恶化。", "review": "下一次XOM季度财报及月度油价复核。"},
    "US.CVX": {"short": "看产量、项目投产和并购整合。", "long": "看资本效率与股东回报。", "success": "项目按期并改善自由现金流。", "failure": "项目延误或资本纪律恶化。", "review": "下一次CVX季度财报及项目更新。"},
    "US.NVDA": {"short": "看Blackwell交付、毛利率和融资链。", "long": "看Rubin、客户资本开支和自研芯片。", "success": "收入和毛利率达到指引。", "failure": "需求或毛利率连续下修。", "review": "下一次NVIDIA季度财报。"},
    "US.AVGO": {"short": "看AI网络、定制芯片和VMware。", "long": "看客户多元化与整合现金流。", "success": "AI收入和自由现金流高增长。", "failure": "客户削单或整合不达计划。", "review": "下一次Broadcom季度财报。"},
    "US.SNDK": {"short": "看NAND价格、企业SSD和利润率。", "long": "看供需纪律与自由现金流。", "success": "合同兑现并改善利润和现金流。", "failure": "价格与利润率同步转弱。", "review": "下一次Sandisk财报及券商口径核对。"},
    "US.PLTR": {"short": "看收入、客户数和利润率。", "long": "看商业客户扩张与合同续约。", "success": "增长与利润支持估值。", "failure": "增长下修且估值仍高。", "review": "下一次PLTR季度财报。"},
    "US.ON": {"short": "看汽车工业去库存和SiC。", "long": "看汽车平台份额与利润率恢复。", "success": "库存正常化并改善盈利。", "failure": "需求疲弱或SiC落后。", "review": "下一次ON季度财报。"},
    "US.COHR": {"short": "看光通信收入与经营现金流。", "long": "看数据中心份额和债务下降。", "success": "增长转化为正自由现金流。", "failure": "负自由现金流持续。", "review": "下一次COHR完整财报。"},
    "US.LITE": {"short": "看光器件需求、收购和异常损益。", "long": "看整合后的现金流和客户结构。", "success": "收入兑现且现金流转正。", "failure": "整合与会计项目继续恶化。", "review": "下一次LITE完整财报和收购更新。"},
    "US.NRG": {"short": "看电力需求、并购和负债。", "long": "看监管、协同和资本回报。", "success": "负债下降且并购提升现金流。", "failure": "杠杆或监管压力持续上升。", "review": "下一次NRG季度财报和监管更新。"},
}


SECTOR_STATUS = {
    "US.ETN": "数据中心电力与基础设施：已激活研究",
    "US.CEG": "数据中心电力与基础设施：已激活研究",
    "US.VRT": "数据中心电力与基础设施：已激活研究",
    "US.NRG": "数据中心电力与基础设施：已激活研究，但杠杆和监管约束",
    "JP.8306": "日本银行与利率正常化：条件激活，BOJ加息尚非正式决定",
    "JP.8316": "日本银行与利率正常化：条件激活，BOJ加息尚非正式决定",
    "JP.8411": "日本银行与利率正常化：条件激活，BOJ加息尚非正式决定",
    "US.XOM": "石油能源：组合分散研究，不是当前主要增长方向",
    "US.CVX": "石油能源：组合分散研究，不是当前主要增长方向",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def stamp(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "size": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, JST).isoformat(timespec="seconds"),
        "sha256": sha256(path),
    }


def tag_fragment(markup: str):
    return BeautifulSoup(markup, "html.parser")


def replace_labelled_paragraph(detail, label: str, body: str) -> None:
    for paragraph in detail.find_all("p"):
        bold = paragraph.find("b")
        if bold and label in bold.get_text(strip=True):
            replacement = tag_fragment(f"<p><b>{html.escape(label)}</b>{html.escape(body)}</p>").p
            paragraph.replace_with(replacement)
            return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id")
    args = parser.parse_args()
    now = datetime.now(JST)
    run_id = args.run_id or f"V7-V05-COMPLETE-{now.strftime('%Y%m%d-%H%M%S')}-JST"
    out = ROOT / "output/candidates/2026-08-17" / run_id
    out.mkdir(parents=True, exist_ok=False)

    source_html = SOURCE / "★2026-08-17完整投研产品候选_v0.4.html"
    soup = BeautifulSoup(source_html.read_text(encoding="utf-8"), "html.parser")
    holdings = read_json(SOURCE / "04_24类持仓完整性矩阵_20260817.json")
    candidates = read_json(SOURCE / "05_21只候选五关轨迹_20260817.json")
    trace = read_json(SOURCE / "09_结论证据规则追踪表_20260817.json")
    futu = read_json(FUTU)

    by_symbol = {row["symbol"]: row for row in futu["futu_positions"]}
    total_assets = float(futu["futu_cash"]["total_assets"])
    direct_value = sum(float(by_symbol[code]["broker_market_val"]) for code in ["US.NVDA", "US.MSFT", "US.AVGO", "US.TSM", "US.SNDK"])
    softbank_value = float(by_symbol["JP.9984"]["broker_market_val"]) / USDJPY
    direct_pct = direct_value / total_assets * 100
    broad_pct = (direct_value + softbank_value) / total_assets * 100
    stress = {
        "direct_20": direct_pct * 0.20,
        "direct_35": direct_pct * 0.35,
        "broad_20": broad_pct * 0.20,
        "broad_35": broad_pct * 0.35,
    }

    if set(VALUATIONS) != {item["code"] for item in holdings["items"]}:
        raise RuntimeError("Holding valuation map does not cover exactly 24 holdings")
    if set(HOLDING_TIMES) != set(VALUATIONS):
        raise RuntimeError("Holding time-scale map is incomplete")
    if set(CANDIDATE_GATE5) != {item["code"] for item in candidates["items"]}:
        raise RuntimeError("Candidate fifth-gate map does not cover exactly 21 candidates")
    if set(CANDIDATE_TIMES) != set(CANDIDATE_GATE5):
        raise RuntimeError("Candidate time-scale map is incomplete")

    for item in holdings["items"]:
        code = item["code"]
        valuation = VALUATIONS[code]
        timing = HOLDING_TIMES[code]
        item["valuation_method"] = valuation["method"]
        item["valuation_judgment"] = valuation["view"]
        item["valuation_basis"] = valuation["basis"]
        item["valuation"] = f"{valuation['method']} 当前判断：{valuation['view']} 判断依据：{valuation['basis']}"
        item["dual_time_scale"] = timing
        item["observation_band"]["definition"] = "观察带只是重新研究的触发价格，不是通过估值模型计算出的内在价值，也不是自动买卖线。"
        detail = soup.find("details", id=f"holding-{code.replace('.', '-')}")
        if detail is None:
            raise RuntimeError(f"Missing holding card: {code}")
        replace_labelled_paragraph(detail, "估值方法和当前判断：", f"{valuation['method']} 当前判断：{valuation['view']} 判断依据：{valuation['basis']}")
        replace_labelled_paragraph(detail, "便宜/合理/偏贵：", valuation["view"])
        replace_labelled_paragraph(detail, "PDCA验证：", f"{timing['review']} 成功标准：{timing['success']} 失败标准：{timing['failure']}")
        block = tag_fragment(
            "<div class='time-scale'><h4>双时间尺度</h4><p><b>未来1—3个月：</b>"
            + html.escape(timing["short"])
            + "</p><p><b>未来6—12个月：</b>"
            + html.escape(timing["long"])
            + "</p><p><b>成功／失败：</b>"
            + html.escape(timing["success"] + " / " + timing["failure"])
            + "</p><p><b>明确复核：</b>"
            + html.escape(timing["review"])
            + "</p></div>"
        ).div
        detail.select_one(".asset-body").append(block)

    priority = ["US.ETN", "US.CEG", "JP.8306", "US.TSM", "US.VRT"]
    for item in candidates["items"]:
        code = item["code"]
        gate5 = CANDIDATE_GATE5[code]
        timing = CANDIDATE_TIMES[code]
        sector = SECTOR_STATUS.get(code, "AI半导体、代工和存储：已激活研究，但受估值与同一驱动风险约束")
        item["sector_research_status"] = sector
        item["five_gates"][0]["input"] = sector + "；当前可执行新机会仍为0。"
        item["five_gates"][0]["evidence_status"] = "GPT总控已裁定研究状态"
        item["five_gates"][3]["input"] = item["five_gates"][3]["input"].replace("GPT总控判断", "后续正式财报验证")
        item["five_gates"][4]["input"] = f"催化剂：{gate5['catalyst']} 反向风险：{gate5['risk']} 失效条件：{gate5['failure']}"
        item["gate5_specific"] = gate5
        item["dual_time_scale"] = timing
        item["research_priority"] = priority.index(code) + 1 if code in priority else None
        detail = soup.find("details", id=f"candidate-{code.replace('.', '-')}")
        if detail is None:
            raise RuntimeError(f"Missing candidate card: {code}")
        gate_items = detail.select("ol.gates > li")
        gate_items[0].clear()
        gate1_label = soup.new_tag("b")
        gate1_label.string = "第1关："
        gate_items[0].append(gate1_label)
        gate_items[0].append(item["five_gates"][0]["input"])
        gate_items[3].clear()
        gate4_label = soup.new_tag("b")
        gate4_label.string = "第4关："
        gate_items[3].append(gate4_label)
        gate_items[3].append(item["five_gates"][3]["input"])
        gate_items[4].clear()
        gate5_label = soup.new_tag("b")
        gate5_label.string = "第5关："
        gate_items[4].append(gate5_label)
        gate_items[4].append(item["five_gates"][4]["input"])
        replace_labelled_paragraph(detail, "现在怎么办：", item["judgment"] + "；这是研究及等待触发顺序，不是立即买入顺序。")
        time_block = tag_fragment(
            "<div class='time-scale'><h4>双时间尺度与复核</h4><p><b>未来1—3个月：</b>"
            + html.escape(timing["short"])
            + "</p><p><b>未来6—12个月：</b>"
            + html.escape(timing["long"])
            + "</p><p><b>成功／失败：</b>"
            + html.escape(timing["success"] + " / " + timing["failure"])
            + "</p><p><b>明确复核：</b>"
            + html.escape(timing["review"])
            + "</p></div>"
        ).div
        detail.select_one(".asset-body").append(time_block)

    candidate_trace_updates = {
        f"CON-CAND-{code.replace('.', '-')}":
        f"催化剂：{values['catalyst']} 反向风险：{values['risk']} 失效条件：{values['failure']}"
        for code, values in CANDIDATE_GATE5.items()
    }
    for row in trace["items"]:
        conclusion_id = row.get("conclusion_id")
        if conclusion_id in candidate_trace_updates:
            row["reverse_evidence"] = candidate_trace_updates[conclusion_id]
    for table_row in soup.find_all("tr"):
        cells = table_row.find_all("td")
        if cells and cells[0].get_text(strip=True) in candidate_trace_updates:
            cells[-1].string = candidate_trace_updates[cells[0].get_text(strip=True)]
    # Remove the superseded SNDK correction item; only the broker-return gap remains.
    for row in soup.find_all("tr"):
        first_cell = row.find("td")
        if first_cell and first_cell.get_text(strip=True) == "OPEN-002":
            row.decompose()
        elif first_cell and first_cell.get_text(strip=True) == "FURTHER-V04-01":
            cells = row.find_all("td")
            cells[1].string = "券商收益率25.21%与现价、成本计算收益率19.19%之间的计算基础尚未解释。"
            cells[2].string = "影响账面收益解释，但不影响券商市值进入账户风险。"
            cells[3].string = "券商收益率计算基础。"
            cells[4].string = "券商收益率继续与估值和动作隔离。"

    seven_layers = [
        [1, "世界观", "事实：2026-08-14/15；判断：2026-08-17", "美国消费偏弱与AI融资并存，主题收益更依赖盈利和现金流。", "折现率可能下降，但增长与融资风险上升。", "传给宏观与资本成本。", "新闻事实早于生产日，未冒充8月17新事件。"],
        [2, "国家与宏观战略", "事实截至2026-08-15；判断：2026-08-17", "美联储利率与BOJ加息报道形成美日利率差变量。", "日本银行仅条件激活；BOJ加息尚非正式决定。", "传给资金流和日股压力。", "不得写成BOJ已经决定加息。"],
        [3, "资金流", "事实截至2026-08-15；判断：2026-08-17", "风险偏好仍在，但杠杆和拥挤提高同向回撤概率。", "AI链对坏消息更敏感，现金具有等待价值。", "传给板块和压力测试。", "外部观点与价格事实并列，不替代官方数据。"],
        [4, "板块轮动", "事实截至2026-08-15；裁定：2026-08-17", "数据中心电力与基础设施已激活；AI半导体代工存储已激活但受估值约束；日本银行条件激活；能源作分散。", "研究已激活不等于立即买入。", "传给21只候选。", "当前可执行新机会为0。"],
        [5, "机会池", "扫描：2026-08-15；裁定：2026-08-17", "21只保留研究；最新前五顺序为ETN→CEG→MUFG→TSM→VRT。", "按触发条件和风险收益比排序。", "传给持仓替代比较。", "这是研究顺序，不是买入顺序。"],
        [6, "持仓与替代", "富途2026-08-17；其他账户最后已知状态", f"富途OpenD只读刷新；AI直接{direct_pct:.6f}%，含软银广义{broad_pct:.6f}%；加密保留顺序COIN→CRCL→MSTR。", "不机械按比例交易；新增AI前先比较替代价值。", "传给今日行动和目标管理。", "广义口径使用8月17持仓和8月14 USD/JPY 159.304993。"],
        [7, "复盘与PDCA", "统计截至2026-08-17", "5个独立系列、57个跟踪点；29点已判定，28点一致、1点不一致，28点待验证。", "96.552%仅为已判定跟踪点一致率。", "形成逐标的复核事件。", "样本太少，不称预测准确率或投资胜率。"],
    ]
    layer_heading = next(h for h in soup.find_all("h3") if h.get_text(strip=True) == "七层因果链")
    old_layer_table = layer_heading.find_next_sibling("div", class_="table-wrap")
    rows = "".join("<tr>" + "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row) + "</tr>" for row in seven_layers)
    old_layer_table.replace_with(tag_fragment("<div class='table-wrap'><table><thead><tr><th>层</th><th>名称</th><th>日期</th><th>事实</th><th>结论</th><th>传导</th><th>边界</th></tr></thead><tbody>" + rows + "</tbody></table></div>").div)
    chain_heading = next(h for h in soup.find_all("h3") if h.get_text(strip=True) == "完整传导")
    old_chain_table = chain_heading.find_next_sibling("div", class_="table-wrap")
    old_chain_table.replace_with(tag_fragment(
        f"<div class='table-wrap'><table><thead><tr><th>链路</th><th>事实到行动</th></tr></thead><tbody>"
        f"<tr><td>AI链</td><td>需求与融资仍支持AI基础设施 → 估值和拥挤提高同向风险 → 8月17日AI直接{direct_pct:.6f}%、广义{broad_pct:.6f}% → 新增前先比较替代价值，当前不生成订单</td></tr>"
        "<tr><td>日本链</td><td>BOJ加息报道但尚非决定 → 日本银行条件激活 → MUFG优先，SMFG和瑞穗继续等待政策与净息差验证 → 日股高久期资产同步做压力测试</td></tr>"
        "</tbody></table></div>"
    ).div)

    target_rows = [
        ["-10%", "+55.6%", "+122.2%"],
        ["0%", "+40.0%", "+100.0%"],
        ["+10%", "+27.3%", "+81.8%"],
        ["+20%", "+16.7%", "+66.7%"],
    ]
    target = {
        "run_id": run_id,
        "formula": "剩余要求=(1+目标收益率)/(1+假设当前年度进度)-1",
        "actual_progress": "年初统一基准缺失，表中进度是假设，不代表实际完成度。",
        "conditional_table": [
            {"assumed_progress": row[0], "needed_for_40": row[1], "needed_for_100": row[2]} for row in target_rows
        ],
        "supports_40_if": ["核心持仓盈利与现金流兑现", "AI同一驱动回撤受控", "第一层候选在更好估值或证据触发后提供增量贡献"],
        "cannot_prove_100_because": ["缺统一年初基准", "高弹性机会尚无可执行安全垫", "AI同一驱动已经较高，不能靠追高或杠杆补目标"],
        "not_chasing": {"positive": "降低高位回撤和永久损失风险，保留现金等待更高胜率。", "negative": "若市场持续单边上涨，现金会拖累短期相对收益。"},
        "prepare": "若判断正确，提前维护ETN、CEG、MUFG、TSM、VRT的财报、估值和事件触发条件。",
        "next_review": ["下一次日本市场收盘后", "下一次美国市场收盘后", "上述重点公司重要财报发布后"],
    }
    target_section = soup.find("section", id="target")
    target_section.clear()
    target_section.append(tag_fragment(
        "<h2>＋40%／＋100%目标路径</h2><div class='callout'><b>真实边界：</b>年初统一基准缺失，以下只衡量任务难度，不代表实际完成度。</div>"
        "<p><b>条件公式：</b>剩余要求＝（1＋目标收益率）÷（1＋假设当前年度进度）－1。</p>"
        "<div class='table-wrap'><table><thead><tr><th>假设当前年度进度</th><th>达到＋40%还需</th><th>达到＋100%还需</th></tr></thead><tbody>"
        + "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in target_rows)
        + "</tbody></table></div>"
        "<h3>组合怎样支撑目标</h3><p><b>＋40%的条件：</b>核心持仓盈利和现金流兑现；AI同一驱动回撤受控；第一层候选只在估值或证据触发后提供增量贡献。</p>"
        "<p><b>为什么不能证明＋100%可达：</b>缺统一年初基准，高弹性机会没有可执行安全垫，且现有AI同一驱动已高，不能靠追高或杠杆补目标。</p>"
        "<p><b>今天不追高的正面：</b>降低高位回撤和永久损失风险，保留现金等待更高胜率。<b>负面：</b>若市场持续单边上涨，现金会拖累短期相对收益。</p>"
        "<p><b>提前准备：</b>维护ETN、CEG、MUFG、TSM、VRT的财报、估值和事件触发条件，不提前下单。</p>"
        "<p><b>下一次复核：</b>下一次日本市场收盘、美国市场收盘及重要财报发布后。</p>"
    ))

    # Put the condition table on the first layer too, so the task difficulty is visible immediately.
    first_closure = soup.find("section", id="first-screen-closure")
    if first_closure:
        first_closure.replace_with(tag_fragment(
            "<section id='first-screen-closure' class='layer-closure'><h3>＋40%／＋100%目标差距</h3>"
            "<p>年初统一基准缺失，不能虚构实际完成度。条件公式为：（1＋目标）÷（1＋假设当前进度）－1。</p>"
            "<div class='table-wrap'><table><thead><tr><th>假设当前进度</th><th>＋40%还需</th><th>＋100%还需</th></tr></thead><tbody>"
            + "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in target_rows)
            + "</tbody></table></div><p>该表只判断任务难度，不代表实际完成度。当前不追高可减少高位回撤，但若市场持续上涨，现金会拖累短期收益。</p>"
            "<h3>重点机会及为什么暂不买</h3><p>最新研究顺序为ETN→CEG→MUFG→TSM→VRT；这是研究及等待触发顺序，不是立即买入顺序。估值、安全边际或下一次财报确认仍不足，当前可执行新机会为0。</p>"
            "<h3>数据缺口怎样影响今天</h3><p>人工账户仍是最后已知状态，SNDK只剩券商收益率计算基础未解释，富途其他净资产只有汇总。因此可以做风险和研究排序，但不能计算实际年度完成度或生成订单。</p></section>"
        ).section)

    repair = {
        "run_id": run_id,
        "source_run_id": SOURCE_RUN,
        "items": [
            {"id": 1, "before": "24只均写未获授权制定估值", "after": "24只分别登记估值方法、总控分类和具体依据", "status": "CLOSED"},
            {"id": 2, "before": "21只板块状态等待总控", "after": "四类研究板块状态和最新前五顺序已登记", "status": "CLOSED"},
            {"id": 3, "before": "第五关存在共用模板", "after": "21只逐只写催化剂、反向风险和失效条件", "status": "CLOSED"},
            {"id": 4, "before": "SNDK进一步了解存在旧矛盾", "after": "只保留券商25.21%与成本计算19.19%的基础差异", "status": "CLOSED"},
            {"id": 5, "before": "七层沿用8月15账户、旧敞口标签和旧排序", "after": f"富途更新至8月17；AI直接{direct_pct:.6f}%、广义{broad_pct:.6f}%；顺序ETN→CEG→MUFG→TSM→VRT", "status": "CLOSED"},
            {"id": 6, "before": "目标管理只有文字情景", "after": "增加条件公式、四档剩余要求、组合条件、追高得失和复核时间", "status": "CLOSED"},
        ],
    }
    exposure = {
        "run_id": run_id,
        "data_date": "2026-08-17",
        "futu_run_id": futu["run_id"],
        "total_assets_usd": total_assets,
        "direct_symbols": ["US.NVDA", "US.MSFT", "US.AVGO", "US.TSM", "US.SNDK"],
        "direct_market_value_usd": round(direct_value, 6),
        "direct_exposure_pct": round(direct_pct, 6),
        "softbank_market_value_jpy": by_symbol["JP.9984"]["broker_market_val"],
        "usd_jpy": USDJPY,
        "fx_date": "2026-08-14",
        "softbank_proxy_usd": round(softbank_value, 6),
        "broad_exposure_pct": round(broad_pct, 6),
        "stress_pct": {key: round(value, 6) for key, value in stress.items()},
        "boundary": "8月17日持仓按8月14日USD/JPY换算；用于风险观察，不是30%硬线。",
    }

    # Update every visible stale value after DOM-level changes.
    product = str(soup)
    replacements = {
        "v0.4": "v0.5",
        SOURCE_RUN: run_id,
        "2026-08-17T01:24:32+09:00": now.isoformat(timespec="seconds"),
        "48.148% / 61.476%": f"{direct_pct:.6f}% / {broad_pct:.6f}%",
        "48.148%": f"{direct_pct:.6f}%",
        "61.476%": f"{broad_pct:.6f}%",
        "组合损失约9.630%": f"组合损失约{stress['direct_20']:.6f}%",
        "约16.852%": f"约{stress['direct_35']:.6f}%",
        "约12.295%": f"约{stress['broad_20']:.6f}%",
        "约21.516%": f"约{stress['broad_35']:.6f}%",
        "VRT第一、TSM第二、CRDO第三": "ETN第一、CEG第二、MUFG第三、TSM第四、VRT第五",
        "VRT→TSM→CRDO": "ETN→CEG→MUFG→TSM→VRT",
        "富途2026-08-15": "富途2026-08-17",
        "不由Codex改变正式激活状态": "研究板块状态已由GPT总控裁定",
        "未获授权制定当前估值或价值区间；只在GPT总控提供后进入正式产品。": "估值方法、当前判断和依据已按GPT总控v0.5返修令登记。",
        "下一次正式财报、账户新实物或总控指定验证日": "见每只标的的双时间尺度与明确复核事件",
        "这是观察区间，不是订单或精确内在价值。": "观察带只是重新研究的触发价格，不是通过估值模型计算出的内在价值，也不是自动买卖线。",
    }
    for old, new in replacements.items():
        product = product.replace(old, new)
    forbidden = [
        "未获授权制定当前估值或价值区间",
        "正式板块激活仍由GPT总控裁定",
        "催化剂：正式财报和行业需求",
        "反向风险：估值、竞争和兑现",
        "失效条件：正式证据和业务判断闭合",
        "SNDK价格、拆股与财务口径",
        "富途2026-08-15",
        "VRT→TSM→CRDO",
        "下一次正式财报、账户新实物或总控指定验证日",
    ]
    hits = [text for text in forbidden if text in product]
    if hits:
        raise RuntimeError(f"Forbidden stale text remains: {hits}")

    title = "★2026-08-17完整投研产品候选_v0.5"
    html_path = out / f"{title}.html"
    html_path.write_text(product, encoding="utf-8")
    write_json(out / "03_六项返修对照表_20260817.json", repair)
    write_json(out / "04_更新后的24类持仓矩阵_20260817.json", {"run_id": run_id, "count": 24, "items": holdings["items"]})
    write_json(out / "05_更新后的21只五关轨迹_20260817.json", {"run_id": run_id, "count": 21, "priority": priority, "items": candidates["items"]})
    write_json(out / "06_AI敞口重算表_20260817.json", exposure)
    write_json(out / "07_目标条件计算表_20260817.json", target)
    write_json(out / "08_结论证据规则追踪表_20260817.json", {**trace, "run_id": run_id})
    log = {
        "run_id": run_id,
        "generated_at": now.isoformat(timespec="seconds"),
        "source_v04": stamp(source_html),
        "daily_before": stamp(DAILY),
        "futu_input": stamp(FUTU),
        "changes": repair["items"],
        "status": {"business_pass": "PENDING_INDEPENDENT_REVIEW", "final_product_pass": "PENDING_INDEPENDENT_REVIEW", "release_status": "NOT_AUTHORIZED", "current_executable": False},
        "boundaries": {"release_registered": False, "daily_overwritten": False, "trade_functions_called": False, "orders_generated": False, "current_rules_modified": False},
    }
    write_json(out / "12_完整施工日志_20260817.json", log)
    print(json.dumps({"run_id": run_id, "output_dir": str(out), "html": stamp(html_path), "direct_ai_pct": round(direct_pct, 6), "broad_ai_pct": round(broad_pct, 6)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
