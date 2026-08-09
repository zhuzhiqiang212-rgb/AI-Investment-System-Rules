# -*- coding: utf-8 -*-
"""★★轮195 B · 四层漏斗字段与分流(Code建结构+闸+L1/L2粗估·★A/B/C分档与预测卡内容=Opus5的活)。
GPT V7 限定五项之一。★不建大型平台·不恢复正式产品·不扩充制度。

L1(501只): 沿用现有筛选分 + 新增L2粗估收益
  · 粗估空间 = (锚点价 − 现价) ÷ 现价
  · 锚点按可得性依次: ①分析师目标价(缺→NK4) ②同业PE中位×EPS ③历史PE中枢×EPS ④三年最高价
  · 优先级 = 粗估空间 × 命中路径数 ÷ 已跟踪天数
  · 输出约30只 → 交 Opus5 做 L2三档分流 + L3预测卡

L2三档(★只有B可淘汰·分档=Opus5): A有可信驱动→L3 / B确认无驱动(须查过留痕)→淘汰 / C证据不足→观察池
L3轻量预测卡(10项·与L4同字段名同格式·填=Opus5)
B-4 置信度:★排序公式不含置信度 = 预期收益 ÷ 兑现期限年数 ÷ 下行空间;置信度独立列
"""
import sys, json, argparse, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _yahoo(code):
    """本项目代码→Yahoo符号。"""
    try:
        mk, sym = code.split(".")
    except ValueError:
        return None
    if mk == "HK":
        return sym.lstrip("0").zfill(4) + ".HK"
    if mk == "JP":
        return sym + ".T"
    if mk == "US":
        return sym
    return None


# ═══ L2 三档分流字段schema(空·待Opus5填·B必须有『查过』证据留痕否则视为C) ═══
def l2_triage_schema():
    return {
        "档": None,  # A/B/C ★=Opus5判·★Code不含任何自动升降档逻辑(B-1硬约束)
        "A_有可信驱动": {"主要上涨依赖": None, "证据": None},
        "B_确认无实质驱动": {"无新催化": None, "无业绩拐点": None, "无估值修复空间": None,
                        "★查过的检索证据": None, "★缺此留痕则视为C": True},
        "C_证据不足": c_bucket_schema(),   # ★轮197 B:C档六字段
    }


# ═══ ★轮197 B · C档必须保留的六字段(GPT明列) ═══
def c_bucket_schema():
    return {
        "缺少什么证据": None,        # ★分类(驱动/预期/估值基准…)
        "需要哪个数据源": None,      # ★新闻流/催化剂库/一致预期
        "首次进入日期": None,
        "最后检查日期": None,
        "新事件触发条件": None,      # ★★★可机器检测
        "队列老化状态": "新",        # ★枚举:新/观察中/已老化(★非自动·由检查动作更新·不自动升降档)
        "★去向": "证据不足观察池(保留系统盲区·非股票没机会)",
    }


# ═══ ★轮197 B-1 · 30天=队列治理【升级线】·★★不得自动升A/判B(GPT复验会查) ═══
def queue_governance_30d(c_bucket, days_since_first):
    """★30天定位:满30天仍无证据→【重新检查数据断点】·决定继续观察或移出活动队列。
    ★★★硬约束:本函数【绝不自动改档(升A/判B)】·只输出【需人工/Opus5复检】的治理提示。
    ★返回不含任何 档=A/档=B 的赋值——升降档只能由Opus5判。"""
    if days_since_first is None:
        return {"治理动作": "缺首次进入日期·无法判老化", "★是否自动改档": False}
    if days_since_first >= 30:
        return {"治理动作": "★满30天仍无证据→重新检查数据断点·由Opus5决定继续观察或移出活动队列",
                "队列老化状态建议": "已老化", "★是否自动升A": False, "★是否自动判B": False,
                "★是否自动改档": False, "★说明": "30天=队列治理升级线·非投资复查周期·不自动升降档(B-1)"}
    return {"治理动作": "未满30天·维持观察", "队列老化状态建议": ("观察中" if days_since_first >= 1 else "新"),
            "★是否自动改档": False}


# ═══ L3 轻量标准预测卡(10项必填·与L4同字段名同格式·填=Opus5) ═══
def l3_card_schema():
    return {
        "①核心上涨驱动(最多3项)": [],
        "②同源驱动去重结果": None,      # ★经 dup_count_gate 去重后
        "③决定性反证(≥1项)": [],
        "④市场已知/已定价程度": None,
        "⑤粗略上涨区间": None,
        "⑥粗略下行区间": None,
        "⑦兑现期限(交易日)": None,       # ★须交易日
        "⑧证据置信度": None,           # ★独立列·不进排序乘法
        "⑨重大事件风险": None,
        "⑩是否值得进L4": None,
        "★8只→3只排序键": "粗略上涨中值÷粗略下行(★禁用命中路径数/PE分位/5日异动)",
    }


def rank_key_L3(card):
    """B-3:8只→3只必须用『粗略上涨中值÷粗略下行』。缺则NK4末位。"""
    up = card.get("⑤粗略上涨区间"); dn = card.get("⑥粗略下行区间")
    try:
        um = sum(up) / len(up) if isinstance(up, list) else float(up)
        d = abs(float(dn[0]) if isinstance(dn, list) else float(dn))
        return um / d if d else 0
    except Exception:
        return -1  # NK4末位


def sort_key_L4(row):
    """B-4:排序公式★不含置信度 = 预期收益 ÷ 兑现期限年数 ÷ 下行空间。置信度作独立列。"""
    try:
        er = float(row["预期收益"]); yrs = max(float(row["兑现期限年数"]), 1e-6); dn = max(abs(float(row["下行空间"])), 1e-6)
        return er / yrs / dn
    except Exception:
        return -1


def build_L1_L2(date, limit=30, pull=True):
    dc = date.replace("-", "")
    audit = _rj(ROOT / "data/universe" / f"p4_candidate_audit_{dc}.json")
    rows = audit.get("逐只", []) or []
    # L1:全宇宙(沿用筛选分=流动性作可得代理·标NK4处不补造) + L2粗估字段骨架
    L1 = []
    for r in rows:
        num = r.get("原始数值", {}) or {}
        L1.append({
            "代码": r.get("代码"),
            "L1筛选分_流动性USD": num.get("avg60成交额USD"),
            "现价": num.get("price"), "ma200": num.get("ma200"),
            "g1流动性": r.get("g1流动性"), "g2年线": r.get("g2年线"), "pass2": r.get("pass2"),
            "path_c估值异常": r.get("第3关估值异常(path_c)"),
            "到哪层": r.get("★到哪层"),
        })
    # L2粗估:仅对 pass2=true(过K线两关)算(其余留在L1·不占用拉数)
    cand = [x for x in L1 if x.get("pass2")]
    est = []
    for x in cand:
        px = x.get("现价")
        anchor = None; anchor_src = None
        # 锚点优先级 ①分析师目标价 ②同业PE×EPS ③历史PE中枢×EPS —— 系统无基本面源→NK4(不补造)
        # ④三年最高价 —— 可从Yahoo拉
        hi3 = None
        if pull and px:
            ysym = _yahoo(x["代码"])
            if ysym:
                try:
                    import yfinance as yf
                    h = yf.Ticker(ysym).history(period="3y")
                    if len(h):
                        hi3 = float(h["High"].max())
                except Exception:
                    hi3 = None
        if hi3:
            hi3 = round(hi3, 2); anchor = hi3; anchor_src = "④三年最高价(Yahoo)"
        # 命中路径数:g1+g2(+path_c)
        paths = sum([1 if x.get("g1流动性") else 0, 1 if x.get("g2年线") else 0, 1 if x.get("path_c估值异常") else 0])
        tracked_days = 1  # ★宇宙候选=今日首次进池(除以天数防反复占用·holdings另有历史·此处保守=1并明示)
        space = round((anchor - px) / px, 4) if (anchor and px) else None
        prio = round(space * paths / tracked_days, 4) if space is not None else None
        est.append({
            "代码": x["代码"], "现价": px,
            "锚点价": anchor, "锚点来源": anchor_src or "①②③基本面源缺→NK4·④待拉",
            "①分析师目标价": "NK4(系统无源·不补造)", "②同业PE×EPS": "NK4(无基本面)",
            "③历史PE中枢×EPS": "NK4(无基本面)", "④三年最高价": hi3 or "NK4(Yahoo未取到)",
            "粗估空间": space, "命中路径数": paths, "已跟踪天数": tracked_days,
            "优先级": prio,
            "L2三档分流": l2_triage_schema(),   # ★空·待Opus5
            "L3预测卡": l3_card_schema(),        # ★空·待Opus5
        })
    est_valid = [e for e in est if e.get("优先级") is not None]
    est_nk4 = [e for e in est if e.get("优先级") is None]
    est_valid.sort(key=lambda e: -e["优先级"])
    top = est_valid[:limit]
    out = {
        "date": date, "_说明": "★轮195 B·四层漏斗L1/L2粗估(Code建结构+算粗估·A/B/C分档与预测卡=Opus5)。锚点①②③无基本面源标NK4不补造·④三年最高价Yahoo实拉。",
        "L1宇宙数": len(L1), "过K线两关(进L2粗估)数": len(cand),
        "L2粗估成功(有锚点)数": len(est_valid), "L2锚点NK4数": len(est_nk4),
        "★优先级公式": "粗估空间 × 命中路径数 ÷ 已跟踪天数",
        "★锚点优先级": "①分析师目标价(NK4)→②同业PE×EPS(NK4)→③历史PE中枢×EPS(NK4)→④三年最高价(实拉)",
        "★置信度处理(B-4)": "排序不含置信度=预期收益÷兑现期限年数÷下行空间;置信度独立列;低置信→区间放宽+悲观概率≥40%+动作降级",
        "★交Opus5": "以下约%d只做L2三档分流(A→L3/B淘汰须查过留痕/C证据不足观察池)+填L3轻量预测卡" % len(top),
        f"★L1_L2约{limit}只清单": top,
        "L2锚点NK4只(全④未取到·不补造)": [e["代码"] for e in est_nk4],
    }
    (ROOT / "data/funnel").mkdir(parents=True, exist_ok=True)
    (ROOT / "data/funnel" / f"L1_L2_estimate_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-08-05")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--no-pull", action="store_true", help="不拉Yahoo(仅建结构·测试用)")
    a = ap.parse_args()
    o = build_L1_L2(a.date, a.limit, pull=(not a.no_pull))
    print("[funnel] L1宇宙%d · 过两关进L2粗估%d · 粗估成功%d · NK4 %d · 输出top%d" % (
        o["L1宇宙数"], o["过K线两关(进L2粗估)数"], o["L2粗估成功(有锚点)数"], o["L2锚点NK4数"], min(a.limit, o["L2粗估成功(有锚点)数"])))
    for e in o[f"★L1_L2约{a.limit}只清单"][:12]:
        sp = "%.1f%%" % (e["粗估空间"] * 100) if e["粗估空间"] is not None else "NK4"
        print("  %-11s 现价%-9s 锚点%-9s 空间%-7s 路径%d 优先级%.3f" % (
            e["代码"], e["现价"], e["锚点价"], sp, e["命中路径数"], e["优先级"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
