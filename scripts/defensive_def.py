# -*- coding: utf-8 -*-
"""★★★轮224 董事长裁定《防御仓定义统一》(00_请先看这里/裁定_防御仓定义统一_20260806.html):
全系统【单一防御判据·唯一真相源】。防御 = 行业属性·【不是名单】·【不是「不是AI」】。三条缺一不可:
  ①行业属性 ∈ {医药/制药/保险/公用事业/电信/必需消费}
  ②现金流稳定(收入不依赖资本开支周期/大宗商品价格)——由防御行业隐含(收入非周期/非大宗)
  ③低AI关联(不属AI供应链任一节点)
★只满足③ = 分散·【非防御】。可选消费(游戏/玩具/消费电子)/汽车/商社 → 非防御。
★行业归类=客观事实分类(非"防御标的死名单")·防御从行业【派生】(总则六:锚定义不锚死名单)·不锚公司名。"""

# ①防御行业集(定义·非名单)——满足①②的行业
DEFENSIVE_INDUSTRIES = {"医药", "制药", "保险", "公用事业", "电信", "必需消费"}
# ③AI供应链节点(低AI关联判据:属此则非防御)
_AI_TICKERS = {"NVDA", "MSFT", "META", "AVGO", "TSM", "SNDK", "6857", "9984"}
_CRYPTO = {"MSTR", "COIN", "CRCL", "BTC", "ETH", "BTCUSD", "ETHUSD"}
# 行业客观分类(ticker→行业·事实·非防御名单;数据无sector字段时的分类源)
_INDUSTRY = {
    "4568": "医药", "8766": "保险",           # ★防御(医药/保险·非AI·现金流稳定)
    "7203": "汽车", "8001": "商社", "7832": "可选消费", "7974": "可选消费", "6758": "消费电子",  # ★非防御
    "IBKR": "金融",
}
# 回退:从 node_class/name 的【纯行业词】推断(★不锚公司名·只认行业词)
_IND_WORDS = (("保険", "保险"), ("保险", "保险"), ("医薬", "医药"), ("医药", "医药"), ("製薬", "制药"), ("制药", "制药"),
              ("公用", "公用事业"), ("電力", "公用事业"), ("电力", "公用事业"), ("通信", "电信"), ("电信", "电信"),
              ("必需消費", "必需消费"), ("必需消费", "必需消费"), ("生活必需", "必需消费"))


def _base(sym):
    return str(sym or "").split(".")[-1]


def is_ai(sym):
    return _base(sym) in _AI_TICKERS


def is_crypto(sym):
    return _base(sym) in _CRYPTO


def industry_of(sym, node_class="", name=""):
    """客观行业分类。优先 ticker 分类·回退 node_class/name 的纯行业词(不锚公司名)。"""
    b = _base(sym)
    if b in _INDUSTRY:
        return _INDUSTRY[b]
    text = f"{node_class or ''} {name or ''}"
    for kw, ind in _IND_WORDS:
        if kw in text:
            return ind
    return None


def is_defensive(sym, node_class="", name="", matched_classes=None):
    """★★★统一防御判据(唯一真相源·三条缺一不可)。返回 bool。"""
    if is_ai(sym) or is_crypto(sym):          # ③低AI关联(不满足→非防御)
        return False
    ind = industry_of(sym, node_class, name)   # ①行业属性(②现金流稳定由防御行业隐含)
    return ind in DEFENSIVE_INDUSTRIES


def classify(sym, node_class="", name=""):
    """给渲染/体检用:返回 (是否防御, 行业, 理由)。"""
    if is_crypto(sym):
        return False, "加密", "③加密·非防御"
    if is_ai(sym):
        return False, "AI供应链", "③属AI供应链节点·非防御"
    ind = industry_of(sym, node_class, name)
    if ind in DEFENSIVE_INDUSTRIES:
        return True, ind, "①防御行业+②现金流稳定+③非AI → 防御"
    return False, (ind or "其他"), "①行业非防御集(%s)→分散非防御" % (ind or "未分类")
