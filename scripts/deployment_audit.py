# -*- coding: utf-8 -*-
"""★轮170 P0-3:Deployment Audit(部署审计·董事长提·写进永久验收)。
问题根因:「开发完成」≠「生产生效」——新建脚本没接进 daily_auto_produce·且★无任何机制检测「新模块有没有被daily调用」。
本审计:扫【已建模块 scripts/*.py】 vs 【daily_auto_produce 实际可达的模块(STEPS + inline run_step + 传递import闭包)】→ 报【已建但未被daily调用】(＝欠账清单)。
★五项Production Ready判据:①开发完成 ②已进入生产管道 ③生产调用版本正确 ④配置已切换 ⑤自动任务使用新版本(最终判据)。
本审计核②⑤:模块是否在daily可达闭包内。"""
import sys, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
DAILY = SCRIPTS / "daily_auto_produce.py"
# ★非生产脚本(工具/一次性/探针/测试·不算欠账)——白名单
NONPROD = {"deployment_audit.py", "data_probe.py", "field_decode.py", "field_report.py", "field_map.py",
           "first_scan.py", "first_scan2.py", "first_scan2_report.py", "data_probe2.py"}


def _module_refs_in(text):
    """扫文本里引用的本地脚本名(run_step("..","X.py")·STEPS元组·import X)。"""
    refs = set()
    for m in re.findall(r'["\']([A-Za-z0-9_]+\.py)["\']', text):
        refs.add(m)
    for m in re.findall(r'^\s*(?:from|import)\s+([A-Za-z0-9_]+)', text, re.M):
        if (SCRIPTS / (m + ".py")).exists():
            refs.add(m + ".py")
    return refs


def _import_closure(seed):
    """从seed脚本集·沿本地import传递闭包。"""
    seen = set(seed); stack = list(seed)
    while stack:
        s = stack.pop()
        p = SCRIPTS / s
        if not p.exists():
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for m in re.findall(r'^\s*(?:from|import)\s+([A-Za-z0-9_]+)', txt, re.M):
            cand = m + ".py"
            if (SCRIPTS / cand).exists() and cand not in seen:
                seen.add(cand); stack.append(cand)
    return seen


def build(dc):
    daily_txt = DAILY.read_text(encoding="utf-8", errors="replace")
    # daily直接引用的脚本(STEPS + inline run_step + import)
    direct = _module_refs_in(daily_txt)
    direct.add("daily_auto_produce.py")
    # 传递import闭包(daily→其调用脚本→其import的脚本)
    reachable = _import_closure(direct)
    all_scripts = set(p.name for p in SCRIPTS.glob("*.py") if not p.name.startswith("_"))
    orphans = sorted(all_scripts - reachable - NONPROD)
    # ★重点标注:近轮建的一级逻辑模块是否投产
    focus = {
        "right_left_gate.py": "轮147 E8右→左印证闸",
        "backward_attribution.py": "轮147 E9从下到上验证",
        "closed_loops.py": "轮148 E10四闭环+周期硬闸",
        "sector_direction_v2.py": "轮163/170 ④方向重写(本轮已接daily·验证)",
        "path_c_valuation_anomaly.py": "轮150 路径C估值异常",
        "candidate_priority_rank.py": "轮151 候选优先级",
        "path_b_reason.py": "轮157 路径B异动原因",
        "announcement_check.py": "轮158 公告日历",
        "anomaly_earnings.py": "轮159 异动财报",
        "guidance_extract.py": "轮160 指引提取",
        "inventory_capex.py": "轮165/166 库存capex",
        "danger_deepdive.py": "轮167 危险组合深查",
    }
    focus_status = []
    for mod, desc in focus.items():
        wired = mod in reachable
        focus_status.append({"模块": mod, "说明": desc, "★已接daily生产": wired,
                             "状态": "✅已投产" if wired else "★★未投产(已建但daily不调用)"})
    out = {
        "_说明": "★轮170 部署审计。扫 scripts/*.py vs daily可达闭包(STEPS+inline+import传递)。★已建但未被daily调用=欠账。★五项判据核②⑤(是否进生产/自动任务是否用)。工具/探针类白名单不算欠账。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "已建脚本总数": len(all_scripts), "daily可达数": len(reachable & all_scripts), "白名单(工具)": len(NONPROD & all_scripts),
        "★★已建但未被daily调用(欠账清单)": orphans, "欠账数": len(orphans),
        "★近轮一级逻辑模块投产状态": focus_status,
        "★未投产的一级逻辑(待接)": [f["模块"] for f in focus_status if not f["★已接daily生产"]],
    }
    (ROOT / f"data/logs/deployment_audit_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("已建%d · daily可达%d · 欠账%d" % (o["已建脚本总数"], o["daily可达数"], o["欠账数"]))
    print("★近轮一级逻辑投产状态:")
    for f in o["★近轮一级逻辑模块投产状态"]:
        print("  %-32s %s" % (f["模块"], f["状态"]))
    print("★未投产的一级逻辑(待接):", o["★未投产的一级逻辑(待接)"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
