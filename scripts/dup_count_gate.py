# -*- coding: utf-8 -*-
"""★★★轮195 A · 重复计数强闸（GPT V7 新增强制项·本轮最高优先）。
立规背景（★立规当天自己犯三次同型错）：
  ①微软护城河:『研发12%却毛利68%』一个事实→品牌/网络/无形三维重复计分；
  ②SNDK驱动:NAND合约价一个上游→拆成 D1/D2/D4 三条独立驱动；
  ③置信度乘法:情景概率已含不确定性→再乘置信度系数=重复打折。

★每项证据必须带六字段（缺一不得进下一层）：
  证据ID / 驱动簇ID / 传导路径 / 独立性判断{独立:bool,理由} / 计数位置[列表] / 不确定性计入位置[列表]

★闸判定（§5.4 全靠结构化字段）——★轮197 扩为【四类】：
  判定1 同一 证据ID 出现在 ≥2 个计数位置 → 跨维度重复加分（FAIL）
  判定2 同一 驱动簇ID 被拆成 ≥2 个【独立】驱动 → 重复增加概率/空间（FAIL）
  判定3 同一不确定性在 ≥2 处计入（如情景概率里算了·置信度又算一次）→ 重复打折（FAIL）
  ★判定4 共享模型输入风险（★轮197新增·GPT V7）：同一 anchor_id 被 ≥2 标的共用 →
        【共享输入】★不是FAIL·是【必须留痕并联动】(anchor失效则挂它的标的同时失效重算)。
        ★GPT原话:「不得把六个输出反过来当成六项独立证据证明锚点正确」。
        ★附 PE期间一致性硬校验(PE口径 vs EPS期间打架→FAIL)·敏感性三档·失效联动。

★处置规则（GPT 明确）：
  · 未通过同源去重+不确定性去重 → 不得进入下一层
  · 已发现重复计数但【未合并重算】→ L3/L4 直接 FAIL
"""
import sys, json, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_ALLOWED_UNC = {"情景概率", "置信度", "区间", "无"}  # 不确定性只允许计在这些位置之一(不得两处都计)
# ★轮200:加【事实ID】(拆多证据ID也拦·证明2)。★轮200-B A-2:加【事实内容】——对内容做指纹·换个事实ID也拦。
_REQUIRED_FIELDS = ["证据ID", "事实ID", "事实内容", "驱动簇ID", "传导路径", "独立性判断", "计数位置", "不确定性计入位置"]

import re as _re

# ★轮201 A:实体归一(公司名中英文/简称/代码→统一ticker)。★可扩展·未命中则保留原词(不误并)。
_ENTITY_MAP = {
    "axcelis": "US.ACLS", "阿克塞利斯": "US.ACLS", "acls": "US.ACLS", "us.acls": "US.ACLS",
    "nvidia": "US.NVDA", "英伟达": "US.NVDA", "nvda": "US.NVDA",
    "microsoft": "US.MSFT", "微软": "US.MSFT", "msft": "US.MSFT",
    "sandisk": "US.SNDK", "闪迪": "US.SNDK", "sndk": "US.SNDK",
}
# ★同义词归一(多字词先替·防子串)。指标/方向/期间各归一到规范token。
_SYN = [
    (["在手订单", "新订单", "订单", "orders", "order"], "订单"),
    (["资本开支", "capex", "资本支出"], "capex"),
    (["同比", "较去年", "较上年", "去年同期", "yoy", "同期"], "yoy"),
    (["环比", "较上季", "qoq"], "qoq"),
    (["增长", "增加", "上升", "提升", "上涨", "growth", "up"], "↑"),
    (["下降", "减少", "下滑", "回落", "下跌", "down"], "↓"),
    (["毛利率", "毛利", "gross"], "毛利"),
    (["营收", "收入", "revenue", "sales"], "营收"),
]
_CN_DIGIT = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _cn_num(s):
    """中文数字(0-99)→阿拉伯:十二→12·二十三→23·十→10·五→5。"""
    if "十" in s:
        a, _, b = s.partition("十")
        tens = _CN_DIGIT.get(a, 1) if a else 1
        ones = _CN_DIGIT.get(b, 0) if b else 0
        return tens * 10 + ones
    if len(s) == 1 and s in _CN_DIGIT:
        return _CN_DIGIT[s]
    v = 0
    for ch in s:
        if ch in _CN_DIGIT:
            v = v * 10 + _CN_DIGIT[ch]
    return v


def _num_normalize(s):
    """数值归一:百分之十二→12%·百分之12→12%·中文数字→阿拉伯。"""
    # 百分之 + (中文/阿拉伯) → N%
    def _pct(m):
        t = m.group(1)
        n = _cn_num(t) if _re.search(r"[零一二两三四五六七八九十]", t) else t
        return "%s%%" % n
    s = _re.sub(r"百分之([零一二两三四五六七八九十]+|[0-9]+)", _pct, s)
    # 独立中文数字串→阿拉伯
    s = _re.sub(r"[零一二两三四五六七八九十]+", lambda m: str(_cn_num(m.group(0))), s)
    return s


def _fact_fp(text):
    """★轮201 A加固:事实内容指纹——结构化归一后比对(跨语言/同义/数字写法都归一)。
    步骤:①小写 ②实体名→ticker ③数值归一(中文↔阿拉伯·百分之↔%) ④同义词归一 ⑤数字→N(幅度差异也视同类) ⑥去标点空白。
    → GPT攻击「Axcelis订单同比增长12%」与「阿克塞利斯新订单较去年增加百分之十二」归一后同指纹·被拦。"""
    s = str(text or "").lower()
    for alias, tk in sorted(_ENTITY_MAP.items(), key=lambda kv: -len(kv[0])):  # 长别名先替
        s = s.replace(alias.lower(), tk.lower())
    s = _num_normalize(s)
    for group, canon in _SYN:
        for w in sorted(group, key=lambda x: -len(x)):
            s = s.replace(w, canon)
    s = _re.sub(r"[0-9]+(?:\.[0-9]+)?%?", "N", s)      # 数字/百分比→N
    s = _re.sub(r"[^0-9a-z一-鿿↑↓%]", "", s)          # 去标点/空白(保留规范token)
    return s


def _canon_token(w, canon_default=None):
    """按同义词表归一单token(实体→ticker·指标/方向归一)。"""
    t = str(w or "").strip().lower()
    if t in _ENTITY_MAP or t in {k.lower(): v for k, v in _ENTITY_MAP.items()}:
        return _ENTITY_MAP.get(w) or {k.lower(): v for k, v in _ENTITY_MAP.items()}.get(t, w)
    for group, canon in _SYN:
        if any(t == g.lower() or g in str(w) for g in group):
            return canon
    return canon_default if canon_default is not None else t


def _fact_fp_ev(ev):
    """★轮201:证据事实指纹——★优先用【五元组】结构化(实体+指标+方向+幅度+期间)·更稳;缺则回退文本指纹。
    五元组各字段经实体/同义/数值归一→跨语言/同义/数字写法都收敛到同指纹。"""
    w = ev.get("五元组")
    if isinstance(w, dict) and w:
        实体 = _canon_token(w.get("实体"))
        指标 = _canon_token(w.get("指标"))
        方向 = _canon_token(w.get("方向"))
        期间 = _canon_token(w.get("期间"))
        # 幅度→N(数值差异视同类·防+12/+15绕过)
        return "五元组|%s|%s|%s|N|%s" % (实体, 指标, 方向, 期间)
    if ev.get("事实内容") is not None:
        return _fact_fp(ev.get("事实内容"))
    return "ID:" + str(ev.get("事实ID"))


def _field_ok(ev):
    """字段完整性(缺一即不合格·不得进下一层)。"""
    miss = [f for f in _REQUIRED_FIELDS if f not in ev]
    if miss:
        return False, "缺字段:%s" % miss
    if not isinstance(ev.get("独立性判断"), dict) or "独立" not in ev["独立性判断"]:
        return False, "独立性判断须为{独立:bool,理由}"
    if not isinstance(ev.get("计数位置"), list):
        return False, "计数位置须为列表"
    if not isinstance(ev.get("不确定性计入位置"), list):
        return False, "不确定性计入位置须为列表"
    bad = [u for u in ev["不确定性计入位置"] if u not in _ALLOWED_UNC]
    if bad:
        return False, "不确定性计入位置非法枚举:%s(仅%s)" % (bad, sorted(_ALLOWED_UNC))
    return True, ""


def _has_wuyuanzu(ev):
    w = ev.get("五元组")
    return isinstance(w, dict) and all(str(w.get(k) or "").strip() for k in ["实体", "指标", "方向", "期间"]) and (w.get("幅度") is not None)


def check(evidences, 已合并重算=None, require_wuyuanzu=False):
    """evidences: list[证据dict]。已合并重算: set[事实指纹/事实ID/驱动簇ID]。
    ★轮202 C(路B):require_wuyuanzu=True → 无【五元组】的证据【入口拒绝·不进计分】(自由文本一律拒绝·未登记实体从入口挡)。
    ★轮200:判定1/2按事实指纹/驱动簇结构化聚合;缺字段=硬FAIL。任一命中且未合并重算 → pass=False。"""
    已合并重算 = set(已合并重算 or [])
    结果 = {"字段完整性": [], "入口拒绝_非五元组(路B)": [], "判定1_跨维度重复": [], "判定2_驱动簇拆分": [], "判定3_不确定性重复": []}

    # ★路B入口闸:要求五元组时·自由文本证据一律拒绝进入计分(不尝试解析)
    if require_wuyuanzu:
        for ev in evidences:
            if not _has_wuyuanzu(ev):
                结果["入口拒绝_非五元组(路B)"].append({"证据ID": ev.get("证据ID", "?"),
                                             "说明": "无五元组(实体+指标+方向+幅度+期间)→自由文本拒绝进入计分(路B·未登记实体从入口挡)"})

    # 0 字段完整性(★缺字段=硬FAIL·不得放行)
    for ev in evidences:
        ok, why = _field_ok(ev)
        if not ok:
            结果["字段完整性"].append({"证据ID": ev.get("证据ID", "?"), "问题": why})

    # 判定1:★按【事实内容指纹】聚合(★A-2:不只比事实ID·换个事实ID但内容同→同指纹仍抓)的计数位置去重≥2 → 跨维度重复。
    fact_pos = {}
    for ev in evidences:
        fp = _fact_fp_ev(ev)   # ★优先五元组·回退文本指纹
        fact_pos.setdefault(fp, {"pos": [], "evs": [], "fids": [], "内容样例": ev.get("事实内容")})
        fact_pos[fp]["pos"].extend(ev.get("计数位置", []) or [])
        fact_pos[fp]["evs"].append(ev.get("证据ID"))
        fact_pos[fp]["fids"].append(ev.get("事实ID"))
    for fp, d in fact_pos.items():
        pos = list(dict.fromkeys(d["pos"]))
        fids = list(dict.fromkeys(d["fids"]))
        豁免 = (fp in 已合并重算) or any(x in 已合并重算 for x in fids)
        if len(pos) >= 2 and not 豁免:
            结果["判定1_跨维度重复"].append({"事实指纹": fp, "涉及事实ID": fids, "计数位置": pos,
                                    "涉及证据": list(dict.fromkeys(d["evs"])), "内容样例": d["内容样例"],
                                    "说明": "同一事实(内容指纹)被计入%d维度=跨维度重复(拆多证据ID/换事实ID都抓·A-2)" % len(pos)})

    # 判定2:★同一【驱动簇ID】的计数位置(跨所有证据·★不看自报独立)去重后 ≥2 → 拆分重复。
    #   ★不依赖自报『独立』:把独立标False也绕不过(证明3)。
    簇 = {}
    for ev in evidences:
        cid = ev.get("驱动簇ID")
        if cid is None:
            continue
        簇.setdefault(cid, {"pos": [], "evs": []})
        簇[cid]["pos"].extend(ev.get("计数位置", []) or [ev.get("证据ID")])
        簇[cid]["evs"].append(ev.get("证据ID"))
    for cid, d in 簇.items():
        drivers = list(dict.fromkeys(d["pos"]))
        if len(drivers) >= 2 and cid not in 已合并重算:
            结果["判定2_驱动簇拆分"].append({"驱动簇ID": cid, "被拆成的驱动": drivers,
                                    "涉及证据": list(dict.fromkeys(d["evs"])),
                                    "说明": "同一上游(%s)被拆成%d条驱动=重复增加概率/空间(不看自报独立·结构判定)" % (cid, len(drivers))})

    # 判定3:同一不确定性在 ≥2 处计入(如概率里算了·置信度又算一次) → 重复打折
    for ev in evidences:
        unc = [u for u in (ev.get("不确定性计入位置", []) or []) if u != "无"]
        unc_d = list(dict.fromkeys(unc))
        if len(unc_d) >= 2 and ev.get("证据ID") not in 已合并重算:
            结果["判定3_不确定性重复"].append({"证据ID": ev.get("证据ID"), "计入位置": unc_d,
                                     "说明": "同一不确定性在%d处计入(不得概率+置信度都算)=重复打折" % len(unc_d)})
    # 判定3补:同一驱动簇的不确定性跨证据既在情景概率又在置信度(乘法双计)
    for cid, evs in {c: [e for e in evidences if e.get("驱动簇ID") == c] for c in {x.get("驱动簇ID") for x in evidences}}.items():
        if cid is None or cid in 已合并重算:
            continue
        union = set()
        for e in evs:
            union |= {u for u in (e.get("不确定性计入位置", []) or []) if u != "无"}
        if "情景概率" in union and "置信度" in union:
            结果["判定3_不确定性重复"].append({"驱动簇ID": cid, "计入位置": ["情景概率", "置信度"],
                                     "说明": "簇(%s)不确定性既进情景概率又进置信度=置信度乘法双计" % cid})

    命中 = {k: v for k, v in 结果.items() if v}
    pass_ = (len(命中) == 0)
    return {
        "pass": pass_,
        "不得进入下一层": (not pass_),
        "L3_L4处置": ("放行" if pass_ else "★★★直接FAIL(已发现重复计数·未合并重算=L3/L4 FAIL)"),
        "命中判定": list(命中.keys()),
        "明细": 结果,
        "评估证据数": len(evidences),
        "已合并重算(豁免)": sorted(已合并重算),
    }


# ═══════════ ★轮197 判定4 · 共享模型输入风险(anchor_id) ═══════════
# ★轮200-B A-3:身份属性穷举——任一变即不同锚点。加【计算方法】。
_ANCHOR_FIELDS = ["anchor_id", "同业样本", "期间", "币种", "异常值处理", "PE口径", "EPS期间", "计算方法", "使用标的"]
_IDENTITY_ATTRS = ["期间", "币种", "PE口径", "EPS期间", "异常值处理", "计算方法", "value"]  # 变了就该是不同anchor_id


def _identity_fp(a):
    """A-3:锚点身份指纹=所有会改变锚点含义的属性(期间/币种/口径/EPS期间/异常值处理/计算方法/取值/样本集)。"""
    core = tuple(str(a.get(k)) for k in _IDENTITY_ATTRS)
    samp = tuple(sorted(str(x) for x in (a.get("同业样本") or [])))
    return core + (samp,)


def make_anchor_id(a, prefix="PE_MED"):
    """★A-3:由【全部身份属性】派生 anchor_id·任一属性不同→id不同(不得共用身份)。"""
    import hashlib as _h
    fp = repr(_identity_fp(a))
    return "%s_%s" % (prefix, _h.sha256(fp.encode("utf-8")).hexdigest()[:12])
_PERIOD_CLASS = {  # PE口径/EPS期间 → 归一期间类(比对用)
    "TTM": "TTM", "滚动": "TTM", "滚动TTM": "TTM",
    "静态": "最近财年", "最近财年": "最近财年", "LFY": "最近财年",
    "预测": "预测年", "预测年": "预测年", "FWD": "预测年",
}


def _period_class(x):
    x = str(x or "")
    for k, v in _PERIOD_CLASS.items():
        if k in x:
            return v
    return "未知"


def check_anchors(anchors):
    """判定4:共享模型输入风险 + A-3六项完整性 + A-4 PE期间一致性硬校验。
    ★轮200加固:
      · 未知/冲突期间=FAIL(不放行·证明6):PE口径或EPS期间归一后为『未知』→FAIL(不再靠两者都未知而相等蒙混)。
      · 身份碰撞=FAIL(证明4):同一 anchor_id 却对应不同 value/同业样本 → 身份混淆FAIL。
    anchors: list[锚点记录(_ANCHOR_FIELDS)]。"""
    结果 = {"字段完整性": [], "共享输入(留痕·非FAIL)": [], "PE期间一致性FAIL": [], "身份碰撞FAIL": [], "未知期间FAIL": []}
    # 身份碰撞(★A-3扩:全身份属性指纹·任一属性不同却共用id→碰撞):同 anchor_id 多条且身份指纹不一致
    id_seen = {}
    for a in anchors:
        aid = a.get("anchor_id", "?")
        fp = _identity_fp(a)
        if aid in id_seen and id_seen[aid] != fp:
            diff = [k for k in _IDENTITY_ATTRS if str(a.get(k)) != str(id_seen[aid][_IDENTITY_ATTRS.index(k)])]
            结果["身份碰撞FAIL"].append({"anchor_id": aid, "不同属性": diff or ["同业样本"],
                                    "说明": "同一anchor_id对应不同身份属性%s=身份混淆(A-3·任一属性变应为不同锚点)" % (diff or ["同业样本"])})
        id_seen.setdefault(aid, fp)
    # ★A-3正向:anchor_id 是否确实由身份属性派生(不同身份→不同id)。同身份不同id=允许;不同身份同id=上面已拦。
    for a in anchors:
        aid = a.get("anchor_id", "?")
        # A-3 六项完整性
        miss = [f for f in _ANCHOR_FIELDS if f not in a]
        if miss:
            结果["字段完整性"].append({"anchor_id": aid, "缺字段": miss})
        # A-2 共享输入:使用标的≥2 → 留痕(不是FAIL)
        用 = list(dict.fromkeys(a.get("使用标的", []) or []))
        if len(用) >= 2:
            结果["共享输入(留痕·非FAIL)"].append({"anchor_id": aid, "使用标的数": len(用), "使用标的": 用,
                                           "联动": "若该anchor_id失效→这%d只同时失效重算(不得只改一只)" % len(用)})
        # A-4 PE期间一致性 + ★未知期间FAIL(证明6)
        pc = _period_class(a.get("PE口径")); ec = _period_class(a.get("EPS期间"))
        if pc == "未知" or ec == "未知":
            结果["未知期间FAIL"].append({"anchor_id": aid, "PE口径": a.get("PE口径"), "EPS期间": a.get("EPS期间"),
                                     "PE归一": pc, "EPS归一": ec, "说明": "期间无法识别(未知)→不放行FAIL(证明6·不得蒙混)"})
        elif pc != ec:
            结果["PE期间一致性FAIL"].append({"anchor_id": aid, "PE口径归一": pc, "EPS期间归一": ec,
                                       "说明": "PE用%s但EPS用%s→口径打架FAIL(A-4)" % (pc, ec)})
    有FAIL = bool(结果["字段完整性"] or 结果["PE期间一致性FAIL"] or 结果["身份碰撞FAIL"] or 结果["未知期间FAIL"])
    return {
        "pass_期间与字段": (not 有FAIL),   # ★字段缺/期间打架/未知期间/身份碰撞=FAIL;共享输入只留痕不影响pass
        "有共享输入需联动": bool(结果["共享输入(留痕·非FAIL)"]),
        "命中": {k: v for k, v in 结果.items() if v},
        "明细": 结果, "评估锚点数": len(anchors),
    }


def sensitivity_three(anchor_value, using_rows, factors=(1.0, 0.75, 1.25)):
    """A-5 敏感性:对共享锚点算三档(中位/×0.75/×1.25)·输出各标的空间②。
    using_rows: [{代码,现价,EPS}]。空间②=(锚点档×EPS−现价)/现价。"""
    out = []
    for r in using_rows:
        px = r.get("现价"); eps = r.get("EPS")
        row = {"代码": r.get("代码"), "现价": px, "EPS": eps}
        for f in factors:
            pe = anchor_value * f
            sp = round((pe * eps - px) / px, 4) if (px and eps is not None) else None
            row["空间②@×%.2f" % f] = sp
        out.append(row)
    return {"锚点中位": anchor_value, "档位": list(factors), "逐只三档空间②": out}


def invalidate_anchor(anchors, anchor_id, rows=None):
    """A-6/A-4 失效联动·★双向核对(登记表↔逐只引用·多条记录一个不漏)：
    · 登记表侧:所有 anchor_id 匹配的【多条】记录的 使用标的 合并(A-4:多条记录);
    · 逐只引用侧:rows 里 anchor_id 字段引用它的 代码;
    · 双向取并集·并分别标出【登记有但rows无】【rows有但登记漏】·全部纳入失效重算。"""
    from_list = []
    for a in anchors:                      # ★A-4:多条记录都并入(不止第一条)
        if a.get("anchor_id") == anchor_id:
            from_list.extend(a.get("使用标的", []) or [])
    from_list = list(dict.fromkeys(x for x in from_list if x is not None))
    from_rows = list(dict.fromkeys(r.get("代码") for r in (rows or []) if r.get("anchor_id") == anchor_id and r.get("代码")))
    union = list(dict.fromkeys(from_list + from_rows))
    仅登记 = [x for x in from_list if x not in from_rows]   # 登记有·rows无
    仅rows = [x for x in from_rows if x not in from_list]   # rows有·登记漏(★A-4要抓的遗漏)
    return {"anchor_id": anchor_id, "失效": True, "须同时重算的标的": union, "只数": len(union),
            "登记表侧只数": len(from_list), "rows引用侧只数": len(from_rows),
            "★仅登记表有(rows未引用)": 仅登记, "★仅rows引用有(登记表漏登记)": 仅rows,
            "双向一致": (not 仅登记 and not 仅rows),
            "★约束": "不得只改其中一只·登记表∪rows引用 全部同时失效重算·双向核对无遗漏"}


# ═══════════ A-4 反向测试(★必做·「没测过的闸等于没有」·三向) ═══════════
def _E(eid, content, cid, pos, unc, fid=None, indep=True):
    """构造证据(七字段·含事实内容)。"""
    return {"证据ID": eid, "事实ID": fid or eid, "事实内容": content, "驱动簇ID": cid, "传导路径": "→",
            "独立性判断": {"独立": indep, "理由": "样本"}, "计数位置": pos, "不确定性计入位置": unc}


def _sample_cross_dim():
    """反向①:一事实计3维(★微软『研发12%毛利68%』计入品牌/网络/无形)。闸必须拦。"""
    return [_E("E-MSFT", "微软研发12%毛利68%", "研发投入效率",
               ["护城河:品牌", "护城河:网络效应", "护城河:无形资产"], ["情景概率"], fid="MSFT-研发毛利")]


def _sample_sndk_split():
    """反向②:★★★SNDK D1/D2/D4真实——NAND合约价一个上游拆成三驱动。闸必须拦。"""
    C = "NAND合约价上涨"; cid = "NAND合约价"
    return [
        _E("SNDK-D1", C, cid, ["驱动:D1_营收"], ["情景概率"], fid=C),
        _E("SNDK-D2", C, cid, ["驱动:D2_毛利"], ["情景概率"], fid=C),
        _E("SNDK-D4", C, cid, ["驱动:D4_库存重估"], ["情景概率"], fid=C),
    ]


def _sample_uncertainty_double():
    """反向③补:置信度乘法——同簇不确定性既进情景概率又进置信度。闸必须拦。"""
    return [_E("E-概率含不确定", "AI资本开支一事实", "AI资本开支", ["驱动:D1"], ["情景概率", "置信度"])]


def _sample_clean():
    """反向④:合规样本(每事实一维·各驱动簇独立·不确定性单处)。★必须放行(不误杀)。"""
    return [
        _E("OK-1", "AI资本开支上行", "AI资本开支", ["驱动:D1_营收"], ["情景概率"]),
        _E("OK-2", "医保集采落地", "医保集采政策", ["驱动:D2_政策"], ["置信度"]),
    ]


# ═══ ★轮200 攻击样本 ═══
def _attack_fact_split():
    """攻击(证明2):同一事实拆成2个【不同证据ID】·同事实ID·各计1位置。★必须被拦。"""
    return [_E("E-A", "同一毛利事实描述", "簇X", ["护城河:品牌"], ["情景概率"], fid="同一毛利事实"),
            _E("E-B", "同一毛利事实描述", "簇Y", ["护城河:无形资产"], ["情景概率"], fid="同一毛利事实")]


def _attack_fact_relabel():
    """★轮201 A-2攻击:★★用GPT原文两句——换事实ID+中英文改写+数字改写。归一后同指纹·★必须被拦。"""
    return [_E("R-1", "Axcelis订单同比增长12%", "簇1", ["驱动:营收"], ["情景概率"], fid="事实ID甲"),
            _E("R-2", "阿克塞利斯新订单较去年增加百分之十二", "簇2", ["驱动:毛利"], ["情景概率"], fid="事实ID乙")]


def _attack_selfreport_false():
    """攻击(证明3):驱动簇拆3驱动·全把『独立』自报False想关闸。★必须被拦(不看自报)。"""
    cid = "同一上游"
    return [_E("S1", "上游因素表述1", cid, ["驱动:A"], ["情景概率"], fid="f1", indep=False),
            _E("S2", "上游因素表述2", cid, ["驱动:B"], ["情景概率"], fid="f2", indep=False),
            _E("S3", "上游因素表述3", cid, ["驱动:C"], ["情景概率"], fid="f3", indep=False)]


def _attack_missing_field():
    """攻击:少『事实内容』字段想绕过内容指纹。★必须硬FAIL(字段完整性)。"""
    return [{"证据ID": "NoContent", "事实ID": "x", "驱动簇ID": "簇", "传导路径": "→",
             "独立性判断": {"独立": True, "理由": "x"}, "计数位置": ["A", "B"], "不确定性计入位置": ["情景概率"]}]


def _A(aid, val, samp, use, 期="TTM", 币="USD", 异="未剔除极值·中位数", pe="滚动TTM", eps="TTM", 算="同业PE中位×EPS"):
    return {"anchor_id": aid, "value": val, "同业样本": samp, "期间": 期, "币种": 币,
            "异常值处理": 异, "PE口径": pe, "EPS期间": eps, "计算方法": 算, "使用标的": use}


def _sample_anchor_shared():
    """判定4反向A:半导体设备PE中位77.62被6只共用。闸必须留痕+联动。"""
    return [_A("PE_MED_半导体设备_20260805", 77.62,
               ["US.KLAC", "US.LRCX", "US.AMAT", "US.ASML", "US.ACLS", "US.ACMR"],
               ["US.ACLS", "US.KLAC", "US.LRCX", "US.ASML", "US.AMAT", "US.ACMR"])]


def _sample_anchor_period_bad():
    """判定4反向B:PE用TTM但EPS用预测年→口径打架FAIL。闸必须拦。"""
    return [_A("PE_BAD_口径打架", 30.0, ["A", "B"], ["US.X"], eps="预测年")]


def _sample_anchor_clean():
    """判定4合规:单标的用·PE与EPS同口径·全字段齐。必须放行(不误杀)。"""
    return [_A("PE_OK_单用", 20.0, ["A", "B"], ["US.Y"], 异="中位数")]


def _attack_anchor_unknown_period():
    """攻击(证明6):PE口径/EPS期间都写成无法识别的词·想靠『两者都未知而相等』蒙混。★必须FAIL。"""
    return [_A("PE_未知期间", 30.0, ["A", "B"], ["US.Z"], pe="自定义口径X", eps="自定义口径X")]


def _attack_anchor_collision():
    """攻击(A-3·证明4):两个锚点身份属性不同(value/样本/异常值处理…)却复用同一 anchor_id。★必须FAIL。"""
    return [_A("SAME_ID", 20.0, ["A", "B", "C"], ["US.P"], 异="中位数"),
            _A("SAME_ID", 55.0, ["X", "Y", "Z"], ["US.Q"], 异="剔除极值后均值")]  # ★value/样本/异常值处理全不同


def _attack_anchor_attr_change():
    """★A-3攻击:两锚点仅【异常值处理】不同(其余同)·却共用同id。★必须判碰撞FAIL(任一属性变即不同锚点)。"""
    return [_A("ATTR_ID", 30.0, ["A", "B"], ["US.M"], 异="未剔除极值·中位数"),
            _A("ATTR_ID", 30.0, ["A", "B"], ["US.N"], 异="剔除前后5%极值")]  # ★只异常值处理不同


def _attack_invalidate_leak():
    """攻击(证明5):锚点使用标的list漏登记US.LEAK·但rows里US.LEAK引用了该anchor_id。★失效须覆盖US.LEAK。"""
    anchors = [_A("AID1", 30.0, ["A"], ["US.KNOWN"], 异="中位数")]  # ★使用标的漏了US.LEAK
    rows = [{"代码": "US.KNOWN", "anchor_id": "AID1"}, {"代码": "US.LEAK", "anchor_id": "AID1"}]
    return anchors, rows


def _attack_multi_record_invalidate():
    """★A-4攻击:同一anchor_id【多条登记记录】·各记一部分标的·失效须并全部+双向核对不漏。"""
    anchors = [_A("MULTI", 30.0, ["A"], ["US.R1", "US.R2"], 异="中位数"),
               _A("MULTI", 30.0, ["A"], ["US.R3"], 异="中位数")]           # 同id两条·分别登记
    rows = [{"代码": "US.R1", "anchor_id": "MULTI"}, {"代码": "US.R2", "anchor_id": "MULTI"},
            {"代码": "US.R3", "anchor_id": "MULTI"}, {"代码": "US.R4", "anchor_id": "MULTI"}]  # US.R4只在rows·登记漏
    return anchors, rows


def selftest():
    cases = [
        ("反向①·同证据ID计3维(微软)", _sample_cross_dim(), True),   # True=期望被拦
        ("反向②·同驱动簇拆3驱动(SNDK D1/D2/D4真实)", _sample_sndk_split(), True),
        ("反向③·置信度乘法双计", _sample_uncertainty_double(), True),
        ("反向④·合规样本", _sample_clean(), False),               # False=期望放行
    ]
    print("═══ A-4 重复计数强闸 · 三向+合规 反向测试 ═══")
    allgood = True
    for name, evs, expect_block in cases:
        r = check(evs)
        blocked = not r["pass"]
        ok = (blocked == expect_block)
        allgood = allgood and ok
        print("%s %-36s 期望%s→实际%s 命中%s" % (
            "✅" if ok else "❌FAIL", name,
            "拦" if expect_block else "放行", "拦" if blocked else "放行", r["命中判定"]))
        if name.startswith("反向②"):
            d = r["明细"]["判定2_驱动簇拆分"]
            print("     ↳ SNDK: 驱动簇=%s 被拆成 %s → 闸拦(合并重算前不得进L4)" % (d[0]["驱动簇ID"], d[0]["被拆成的驱动"]))
    # 处置规则验证:SNDK 若已合并重算(NAND作单一驱动+单一事实)→应放行
    r2 = check(_sample_sndk_split(), 已合并重算={"NAND合约价", "NAND合约价上涨"})
    ok2 = r2["pass"]
    allgood = allgood and ok2
    print("%s 处置规则·SNDK合并重算后(NAND单一驱动)→期望放行→实际%s" % ("✅" if ok2 else "❌FAIL", "放行" if r2["pass"] else "仍拦"))
    # ★轮197 判定4:共享输入留痕 / PE期间打架FAIL / 合规放行
    print("─── 判定4 · 共享模型输入风险(anchor) ───")
    ra = check_anchors(_sample_anchor_shared())
    okA = (ra["有共享输入需联动"] is True) and (ra["pass_期间与字段"] is True)
    allgood = allgood and okA
    print("%s 反向A·77.62被6只共用→期望留痕联动→实际留痕=%s(联动%d只)·期间字段pass=%s" % (
        "✅" if okA else "❌", ra["有共享输入需联动"],
        ra["明细"]["共享输入(留痕·非FAIL)"][0]["使用标的数"] if ra["明细"]["共享输入(留痕·非FAIL)"] else 0, ra["pass_期间与字段"]))
    rb = check_anchors(_sample_anchor_period_bad())
    okB = (rb["pass_期间与字段"] is False)
    allgood = allgood and okB
    print("%s 反向B·PE(TTM)vs EPS(预测年)→期望FAIL→实际pass=%s" % ("✅" if okB else "❌", rb["pass_期间与字段"]))
    rc = check_anchors(_sample_anchor_clean())
    okC = (rc["pass_期间与字段"] is True) and (rc["有共享输入需联动"] is False)
    allgood = allgood and okC
    print("%s 反向C·单用同口径六项齐→期望放行不误杀→实际pass=%s 共享=%s" % ("✅" if okC else "❌", rc["pass_期间与字段"], rc["有共享输入需联动"]))
    # A-6 失效联动
    inv = invalidate_anchor(_sample_anchor_shared(), "PE_MED_半导体设备_20260805")
    okD = (inv["只数"] == 6)
    allgood = allgood and okD
    print("%s A-6失效联动·标锚点失效→期望6只同时重算→实际%d只" % ("✅" if okD else "❌", inv["只数"]))
    print("═══ 结论:%s ═══" % ("★全部通过(四类闸真拦真放·SNDK真实数据被拦·共享输入留痕联动)" if allgood else "★★有用例未达预期"))
    return 0 if allgood else 1


def dump_test_evidence(path):
    """★D:把三向(证据)+判定4(锚点)测试的【真实输入+实际输出】存文件供GPT代码级复验(★非文字转述)。"""
    ev_cases = {
        "反向①_同证据ID计3维_微软": _sample_cross_dim(),
        "反向②_同驱动簇拆3驱动_SNDK真实D1D2D4": _sample_sndk_split(),
        "反向③_置信度乘法双计": _sample_uncertainty_double(),
        "反向④_合规样本": _sample_clean(),
    }
    anchor_cases = {
        "判定4反向A_77.62被6只共用": _sample_anchor_shared(),
        "判定4反向B_PE_TTM_vs_EPS预测年打架": _sample_anchor_period_bad(),
        "判定4合规C_单用同口径": _sample_anchor_clean(),
    }
    out = {"_说明": "★轮197 D·重复计数强闸【真实输入+实际输出】供GPT代码级复验闸是否漏拦/误杀·非文字转述。期望:①②③拦·④放·判4A留痕联动·判4B FAIL·判4C放。",
           "证据类(判定1-3)": [], "锚点类(判定4)": [], "处置规则": None, "失效联动A-6": None}
    for name, evs in ev_cases.items():
        r = check(evs)
        out["证据类(判定1-3)"].append({"用例": name, "期望": ("拦" if not name.startswith("反向④") else "放行"),
                                  "输入": evs, "实际输出": r, "实际": ("拦" if not r["pass"] else "放行")})
    out["处置规则"] = {"用例": "SNDK合并重算后(NAND单一驱动)", "输入": _sample_sndk_split(),
                   "已合并重算": ["NAND合约价"], "实际输出": check(_sample_sndk_split(), 已合并重算={"NAND合约价"})}
    for name, ancs in anchor_cases.items():
        out["锚点类(判定4)"].append({"用例": name, "输入": ancs, "实际输出": check_anchors(ancs)})
    out["失效联动A-6"] = {"用例": "标半导体设备PE中位失效", "实际输出": invalidate_anchor(_sample_anchor_shared(), "PE_MED_半导体设备_20260805")}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--evidence", help="证据json路径(list[六字段])")
    ap.add_argument("--dump-evidence", help="★D:把测试真实输入+输出存到该路径供GPT代码级复验")
    a = ap.parse_args()
    if a.dump_evidence:
        o = dump_test_evidence(a.dump_evidence)
        print("[dump] 测试证据已写:%s · 证据类%d用例 · 锚点类%d用例" % (a.dump_evidence, len(o["证据类(判定1-3)"]), len(o["锚点类(判定4)"])))
        return 0
    if a.selftest:
        return selftest()
    if a.evidence:
        evs = json.loads(Path(a.evidence).read_text(encoding="utf-8"))
        print(json.dumps(check(evs), ensure_ascii=False, indent=2))
        return 0
    return selftest()


if __name__ == "__main__":
    raise SystemExit(main())
