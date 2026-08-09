# -*- coding: utf-8 -*-
"""★轮149 A:阶段E十项自检——★按董事长计划编号(完整产品执行计划.html 阶段E)重出·纠正轮148编号错位。
★轮148错位:把『多路径入口』标成E4·实为董事长的E5(往前错一位)。本版对齐董事长 E1~E10 定义。
★C-2:逐项报 建成/部分/待·不美化。判定=结构化文件存在+关键字段核(§5.4)。E编号/命名=董事长框架·Code只核对应机制真建成否。"""
import sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DC = "20260804"


def _ex(rel):
    return (ROOT / rel).exists()


def _glob(pat):
    return sorted(ROOT.glob(pat))


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def build():
    items = []

    # E1 ①层证据映射器(G16)
    e1 = _ex("scripts/layer1_evidence_mapper.py")
    items.append({"E": "E1", "董事长定义": "①层改证据映射器(G16·四类输入→映射右栏6尺印证/动摇·今日无事件禁用)",
                  "Code机制": "layer1_evidence_mapper.py", "★判定": "建成" if e1 else "待"})

    # E2 新闻源多源冗余(G18)
    e2 = _ex("scripts/macro_news_intake.py") or _ex("scripts/news_chain_diagnose.py")
    items.append({"E": "E2", "董事长定义": "新闻源多源冗余(G18·CNBC+Yahoo+Google·取消无事件出口)",
                  "Code机制": "macro_news_intake / news多源", "★判定": "建成" if e2 else "待"})

    # E3 候选宇宙=富途全市场(G19)
    e3 = bool(_glob("data/universe/futu_universe_*.json"))
    items.append({"E": "E3", "董事长定义": "候选宇宙=富途全市场(G19·US/JP/HK~1.03万·A股暂缓·韩股Yahoo)",
                  "Code机制": "futu_universe_*.json", "★判定": "建成" if e3 else "待"})

    # E4 漏斗跑通至第3关(★董事长标✓完成)
    tg3 = _rj(sorted(ROOT.glob("data/universe/type_gate3_*.json"))[-1]) if _glob("data/universe/type_gate3_*.json") else {}
    e4 = bool(tg3) and tg3.get("过两关") and tg3.get("★B成长股过第3关(成长PE0<PE≤40默认)") is not None
    items.append({"E": "E4", "董事长定义": "漏斗跑通至第3关(22151→归类→过两关234→成长71→过第3关30)",
                  "Code机制": "type_gate3(过两关%s·成长%s·过第3关%s)" % (tg3.get("过两关"), tg3.get("★A成长股"), tg3.get("★B成长股过第3关(成长PE0<PE≤40默认)")),
                  "★判定": "建成" if e4 else "部分"})

    # E5 多路径入口(G20·★董事长标部分)——★轮145已更新:路径B捞出49只宇宙外新标的·路径C待建
    e5file = _ex("scripts/multi_path_entry.py")
    c异动新 = tg3.get("★C异动宇宙外新")
    items.append({"E": "E5", "董事长定义": "多路径入口(G20·路径A/B/C·上层从唯一闸门改参照系)",
                  "Code机制": "multi_path_entry.py",
                  "★判定": "部分",
                  "★轮145实况(纠正轮148过时信息)": "★路径B事件驱动【已捞出%s只宇宙外新标的】(异动±8%%/5日±15%%·如RBLX-26.9%%被错杀/AXTI+28.7%%突破)·非『源缺捞不出』;★路径C估值异常【待建】→故E5=部分" % c异动新})

    # E6 候选池存储结构(G22·★轮146建·唯一会返工项)
    cp = ROOT / "data/opportunity/candidate_pool.json"
    e6 = cp.exists() and bool(_rj(cp).get("★重跑触发(4条·G22)"))
    items.append({"E": "E6", "董事长定义": "候选池存储结构(G22·可缓存/复用/追踪变化+4触发+今日可动)",
                  "Code机制": "candidate_pool_build.py", "★判定": "建成" if e6 else "部分"})

    # E7 第4关护城河(★待·Opus5五维质性)
    items.append({"E": "E7", "董事长定义": "第4关护城河(moat只覆盖8持仓·234新标的0覆盖·需Opus5五维质性)",
                  "Code机制": "★非Code:Opus5质性(G2);gate4_moat.py框架在填充是Opus5", "★判定": "待(Opus5质性·非Code)"})

    # E8 右→左印证(G21要素二·★轮147建)
    e8 = _ex("scripts/right_left_gate.py") and bool(_glob("data/logs/right_left_gate_*.json"))
    items.append({"E": "E8", "董事长定义": "右→左印证(G21要素二·左栏判断标依据哪把尺+矛盾二选一·不许悄悄偏离)",
                  "Code机制": "right_left_gate.py + judgment_slots尺ID/矛盾字段", "★判定": "建成" if e8 else "待"})

    # E9 从下到上验证(G21要素三·★轮147建·当时称最大结构缺口)
    e9 = _ex("scripts/backward_attribution.py") and bool(_glob("data/pdca/backward_attribution_*.json"))
    repro = bool(_rj(sorted(ROOT.glob("data/pdca/backward_attribution_*.json"))[-1]).get("★两案例都复现正确？")) if e9 else False
    items.append({"E": "E9", "董事长定义": "从下到上验证(G21要素三·⑦→②①逐层回溯归因·错归因到具体层)",
                  "Code机制": "backward_attribution.py(两案例复现=%s)" % repro, "★判定": "建成" if (e9 and repro) else "待"})

    # E10 大闭环套小闭环(G21要素四·★轮148建)
    clf = ROOT / f"data/pdca/closed_loops_{DC}.json"
    gate_ok = bool(_rj(clf).get("★A3周期纪律硬闸", {}).get("全部正确")) if clf.exists() else False
    e10 = _ex("scripts/closed_loops.py") and clf.exists() and gate_ok
    items.append({"E": "E10", "董事长定义": "大闭环套小闭环(G21要素四·四闭环各周期·不许短周期推翻长周期)",
                  "Code机制": "closed_loops.py(A3硬闸全部用例正确=%s)" % gate_ok, "★判定": "建成" if e10 else "部分"})

    done = [i["E"] for i in items if i["★判定"].startswith("建成")]
    part = [i["E"] for i in items if i["★判定"].startswith("部分")]
    wait = [i["E"] for i in items if i["★判定"].startswith("待")]

    out = {
        "_说明": "★轮149 阶段E十项自检·★按董事长计划编号(完整产品执行计划.html)重出·纠正轮148错位(多路径入口=E5非E4)。E编号=董事长框架·Code核对应机制(§5.4结构化)。",
        "date": "2026-08-04",
        "★十项自检(董事长编号)": items,
        "★汇总": {"建成": done, "部分": part, "待/非Code": wait,
               "计数": "建成%d·部分%d·待%d" % (len(done), len(part), len(wait))},
        "★与轮148的纠正": ["轮148把『多路径入口』标E4·实为董事长E5(往前错一位)→本版对齐",
                       "轮148称『路径B源缺捞不出新标的』=过时·★轮145已捞出%s只宇宙外新标的→本版更新" % c异动新],
    }
    (ROOT / "data/logs" / "stage_e_selfcheck_20260804.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    o = build()
    print("=== 阶段E 十项自检(★董事长编号·纠正轮148错位) ===")
    for i in o["★十项自检(董事长编号)"]:
        print("  %-4s %-14s | %s" % (i["E"], i["★判定"], i["董事长定义"][:40]))
    print("汇总:", o["★汇总"]["计数"], "· 建成", o["★汇总"]["建成"], "· 部分", o["★汇总"]["部分"], "· 待", o["★汇总"]["待/非Code"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
