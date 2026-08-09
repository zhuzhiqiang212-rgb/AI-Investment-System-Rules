# -*- coding: utf-8 -*-
"""★轮137建/★轮139 v2:归类规则(★Opus5 定·Code按此实现)。
设计原则(Opus5):①CONCEPT为主(跨市场通用) ②INDUSTRY辅助/校准 ③宽进严出(粗筛宽·后面第2/3/4关去筛)
④★只用富途结构化标签·不用公司名/业务描述关键词匹配(守§5.4)。
★轮139 B 立规矩:★非富途源标的(如Yahoo韩股·无富途标签)的归类·★必须附【客观依据】+标【手工归类】·★不许无依据指定
  (防07-31手填名单错重犯)——见 MANUAL。
★轮139 C:get_plate_stock 加限流重试+间隔·并记【每板块成分取全否】(取不全的不当准确数)。
落盘 data/universe/classified_{date}.json。"""
import sys, json, argparse, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

# ★规则表 v2(Opus5·轮139选定)。DNF:每板块=clause列表·满足任一clause即入池。clause={"I":set,"C":set}(都有=AND·单一=该类)。
RULES = {
    "AI算力·AI芯片": [{"C": {"人工智能", "AI概念", "芯片股", "半导体精选"}}, {"I": {"半导体"}}],
    "AI半导体设备": [{"I": {"半导体设备与材料"}}, {"I": {"电气设备"}, "C": {"半导体"}},
                    {"C": {"半导体产业", "第三代半导体", "半导体设备概念"}}, {"I": {"专用设备"}}],  # ★v2补SH/SZ
    "AI存储": [{"C": {"存储概念"}}, {"I": {"半导体"}, "C": {"半导体", "芯片股"}}],
    "AI云·数据中心": [{"C": {"云计算", "数据中心", "云计算服务商", "IDC概念"}}, {"I": {"软件基础设施", "信息技术服务"}}],  # ★v2补US
    "AI应用软件": [{"C": {"AI应用软件股", "AI应用", "AI医疗", "AI PC"}}],  # ★JP无对应标签·不补(缺口客观·不硬凑)
    "电力·能源(AI耗电)": [{"I": {"电力", "公用事业", "独立电力生产商", "电力及天然气"}}, {"C": {"电力设备股", "绿电概念", "核电"}}],  # ★v2补JP/HK
    "机器人·自动化": [{"I": {"自动化设备", "专用设备", "专用工业机械", "重型机械"}}, {"C": {"机器人", "物理AI", "机器人概念股"}}],  # ★v2补US/HK
    "材料(半导体上游)": [{"I": {"电子元件", "光学光电子", "化学制品", "特种材料", "半导体设备与材料", "特殊化工用品"}}, {"C": {"半导体材料", "半导体"}}],  # ★v2 AND→OR+补HK
}

# ★轮139 B:非富途源标的手工归类(Opus5裁定·★必须附客观依据+标手工·守B-4规矩·不许无依据指定)
MANUAL = {
    "KR.005930": {"板块": "AI存储", "归类方式": "★手工(Opus5裁定·轮139)", "来源": "Yahoo(富途无INDUSTRY/CONCEPT标签)",
                  "★客观依据": "三星电子＝全球DRAM市场前二大厂商 + HBM(高带宽存储)主要供应商(行业公认格局·非个人印象)"},
    "KR.000660": {"板块": "AI存储", "归类方式": "★手工(Opus5裁定·轮139)", "来源": "Yahoo(富途无INDUSTRY/CONCEPT标签)",
                  "★客观依据": "SK海力士＝全球DRAM市场前二大厂商 + HBM主要供应商(行业公认格局·非个人印象)"},
}
HOLDINGS = {"JP.4568", "US.NVDA", "US.MSFT", "US.MSTR", "US.COIN", "JP.9984", "JP.8766", "JP.6758",
            "JP.6857", "JP.7203", "JP.8001", "JP.7832", "JP.7974", "US.AVGO", "US.CRCL", "US.SNDK",
            "US.TSM", "US.META", "US.IBKR", "US.SPCX"}
MKTS = ["US", "JP", "HK", "SH", "SZ"]
GAP_S = 3.6   # ★C:限流间隔(get_plate_stock·>3s 保 <10/30s)


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _all_tags():
    I, C = set(), set()
    for clauses in RULES.values():
        for cl in clauses:
            I |= cl.get("I", set()); C |= cl.get("C", set())
    return I, C


def _eval(clauses, Iset, Cset):
    for cl in clauses:
        ci = cl.get("I"); cc = cl.get("C")
        if ci and cc:
            if (Iset & ci) and (Cset & cc):
                return True
        elif ci:
            if Iset & ci:
                return True
        elif cc:
            if Cset & cc:
                return True
    return False


def _fetch_plate(ctx, code):
    """★C:限流重试·成功→(df)·失败→None。"""
    from futu import RET_OK
    for a in range(5):
        try:
            r, d = ctx.get_plate_stock(code)
            if r == RET_OK:
                return d
            time.sleep(GAP_S + a * 2)   # 限流→越等越久
        except Exception:
            time.sleep(GAP_S + a * 2)
    return None


def build(dc):
    plates = _rj(ROOT / "data/universe" / "futu_plates_20260803.json")
    I_tags, C_tags = _all_tags()
    from futu import OpenQuoteContext
    ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
    stock_tags = {}
    tag_ok, tag_fail = {}, {}   # (m,kind,tag)→count / →True(取不到)
    for m in MKTS:
        name2code = {}
        for kind, key in (("I", "INDUSTRY"), ("C", "CONCEPT")):
            for p in (plates.get(m, {}) or {}).get(key, []):
                name2code[(kind, p["name"])] = p["code"]
        for kind, tags in (("I", I_tags), ("C", C_tags)):
            for t in tags:
                code = name2code.get((kind, t))
                if not code:
                    continue      # 该市场无此标签(缺口·非取不到)
                d = _fetch_plate(ctx, code)
                if d is None:
                    tag_fail[(m, kind, t)] = True; time.sleep(GAP_S); continue
                tag_ok[(m, kind, t)] = len(d)
                for _, row in d.iterrows():
                    rec = stock_tags.setdefault(row["code"], {"I": set(), "C": set(), "market": m})
                    rec[kind].add(t)
                time.sleep(GAP_S)
    ctx.close()
    # 逐股套规则
    result = {b: [] for b in RULES}
    for sc, rec in stock_tags.items():
        for b, clauses in RULES.items():
            if _eval(clauses, rec["I"], rec["C"]):
                result[b].append(sc)
    # ★B:手工归类并入(标手工·附依据)
    for sc, mc in MANUAL.items():
        b = mc["板块"]
        if sc not in result.get(b, []):
            result.setdefault(b, []).append(sc)
    # ★C:每板块【成分取全否】——该板块触发标签在各市场·凡存在的plate是否都fetch成功
    complete = {}
    for b, clauses in RULES.items():
        need = set()
        for cl in clauses:
            for t in cl.get("I", set()):
                need.add(("I", t))
        for cl in clauses:
            for t in cl.get("C", set()):
                need.add(("C", t))
        failed = []
        for m in MKTS:
            havI = set(p["name"] for p in (plates.get(m, {}) or {}).get("INDUSTRY", []))
            havC = set(p["name"] for p in (plates.get(m, {}) or {}).get("CONCEPT", []))
            for kind, t in need:
                exists = t in (havI if kind == "I" else havC)
                if exists and (m, kind, t) in tag_fail:
                    failed.append("%s/%s/%s" % (m, kind, t))
        complete[b] = {"★成分取全": len(failed) == 0, "取不到的标签": failed}
    # C-3 缺口(板块×市场无触发标签)
    gap = {}
    for b, clauses in RULES.items():
        need_I = set(); need_C = set()
        for cl in clauses:
            need_I |= cl.get("I", set()); need_C |= cl.get("C", set())
        g = []
        for m in MKTS:
            havI = set(p["name"] for p in (plates.get(m, {}) or {}).get("INDUSTRY", []))
            havC = set(p["name"] for p in (plates.get(m, {}) or {}).get("CONCEPT", []))
            if not ((need_I & havI) or (need_C & havC)):
                g.append(m)
        if g:
            gap[b] = g
    out = {
        "_说明": "★轮139 归类规则v2(Opus5定)。原则:CONCEPT主+INDUSTRY辅·宽进严出·只用结构化标签(§5.4)。★非富途源标的手工归类须附依据+标手工(MANUAL)。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]), "版本": "v2",
        "★规则表v2(Opus5·DNF)": {b: [{k: sorted(v) for k, v in cl.items()} for cl in cls] for b, cls in RULES.items()},
        "★手工归类(非富途源·附依据·标手工)": MANUAL,
        "★各板块归出": {b: {"总只数": len(v), "★新标的数(持仓外)": sum(1 for x in v if x not in HOLDINGS),
                          "★成分取全": complete.get(b, {}).get("★成分取全", True),
                          "取不到的标签": complete.get(b, {}).get("取不到的标签", []),
                          "样例": sorted(v)[:10],
                          "全量code(供分层筛选·不进产品)": sorted(set(v))} for b, v in result.items()},
        "★缺口清单(板块→无触发标签的市场)": gap,
        "★标签成分数(可追溯·取全的)": {"%s/%s/%s" % k: v for k, v in sorted(tag_ok.items())},
        "★限流取不到的标签(如实·不当0)": ["%s/%s/%s" % k for k in sorted(tag_fail.keys())],
    }
    (ROOT / "data/universe" / f"classified_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("=== v2 各板块归出(总/新/取全) ===")
    for b, v in o["★各板块归出"].items():
        print("  %s: %d只(新%d) · 取全=%s%s" % (b, v["总只数"], v["★新标的数(持仓外)"], v["★成分取全"],
              ("·取不到:" + "·".join(v["取不到的标签"])) if v["取不到的标签"] else ""))
    print("手工归类:", list(o["★手工归类(非富途源·附依据·标手工)"].keys()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
