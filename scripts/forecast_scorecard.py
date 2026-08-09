# -*- coding: utf-8 -*-
"""★★★轮222:跨两源胜率计数器(机械聚合·不替Opus5判)。
分母 = 已评 且 非(计分==false 或 状态含『不可记分』);分子 = 状态==『已评·命中』 且 可严格评分!=false。
★可严格评分==false → 进分母不进分子(NK不可严格评分·轮222董事长规则)。
输出:合计 / pdca源 / forecast源(按尺度)·写两个 registry 顶层『架构师胜率累计(跨源合计)』。★不改被读的锁定内容。"""
import sys, json, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import registry_sources as rs


def _counts(entries):
    r = {"短期": {"已评": 0, "命中": 0}, "长期": {"已评": 0, "命中": 0}}
    for e in entries:
        if not e["已评"]:
            continue
        状态 = str(e["状态"] or "")
        if e.get("计分") is False or "不可记分" in 状态:
            continue                              # 不进分母也不进分子
        sc = e["尺度"] if e["尺度"] in r else "短期"
        r[sc]["已评"] += 1                          # 进分母
        if 状态 == "已评·命中" and e.get("可严格评分") is not False:
            r[sc]["命中"] += 1                      # 进分子(可严格评分false→不进分子)
    return r


def _pct(c):
    return {s: {**v, "胜率": ("%.0f%%" % (100.0 * v["命中"] / v["已评"]) if v["已评"] else "—")} for s, v in c.items()}


def run(dd):
    allx = rs.load_all()
    pdca = [e for e in allx if e["源"] == "pdca"]
    fc = [e for e in allx if e["源"] == "forecast"]
    合计, cp, cf = _counts(allx), _counts(pdca), _counts(fc)
    payload = {"_注": "★跨两源合计(pdca+forecast)·轮222统一读取口径·不合并内容",
               "更新": time.strftime("%Y-%m-%d %H:%M JST"),
               "合计": _pct(合计), "pdca源": _pct(cp), "forecast源": _pct(cf)}
    # 写两个 registry 顶层(同一份跨源合计)
    for path in (rs.PDCA, rs.FORECAST):
        if not path.exists():
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        d["架构师胜率累计"] = {"短期": {"命中": 合计["短期"]["命中"], "已评": 合计["短期"]["已评"]},
                        "长期": {"命中": 合计["长期"]["命中"], "已评": 合计["长期"]["已评"]}}
        d["架构师胜率累计_跨源明细"] = payload
        txt = json.dumps(d, ensure_ascii=False, indent=1)
        path.write_bytes(txt.replace("\n", "\r\n").encode("utf-8"))
    (ROOT / "data/pdca" / ("scorecard_crosssource_%s.json" % dd)).write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return payload


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    dd = time.strftime("%Y%m%d")
    for i, a in enumerate(sys.argv):
        if a == "--date" and i + 1 < len(sys.argv):
            dd = sys.argv[i + 1].replace("-", "")
    p = run(dd)
    for scope in ("合计", "pdca源", "forecast源"):
        s = p[scope]["短期"]
        print("%-10s 短期 已评%d/命中%d (%s)" % (scope, s["已评"], s["命中"], s["胜率"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
