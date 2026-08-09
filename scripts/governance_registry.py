# -*- coding: utf-8 -*-
"""★★轮181 B:主线B治理三项(Version/Status/Dependency)——GPT裁定第四节顺序·29份正式制度。
建 data/governance/institution_registry.json:
  B-1 Version:每份制度版本号(台账已标/文件名取·取不到标 v1(推定)·如实标推定)。
  B-2 Status:六态生命周期(draft/active/superseded/deprecated/void/template)。
     ★状态变更仅董事长可裁定——★脚本只【初判】(由文件位置/内容判)·不擅改。承§5.4结构化字段·不靠「作废」二字。
     ★TEMPLATE文件一律 template·永不当实际数据读。在_历史归档/废止→deprecated。
  B-3 Dependency:实扫制度正文里的【制度ID引用】+【文件名/名称引用】→depends_on/depended_by。
     ★取不到如实标空·★★不猜(董事长07-21被猜坑过)。
★Code只摆结构化事实·状态/依赖真伪的裁定权在董事长(G2)。"""
import sys, json, re, glob
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
LEDGER = ROOT / "00_任务中心" / "制度资产台账_20260804.json"
OUT = ROOT / "data" / "governance" / "institution_registry.json"
SEARCH_DIRS = [ROOT / "00_请先看这里"]

# 名称→搜索核token:剥离通用前缀·留可辨别核(≥3字)供依赖扫描
_PREFIX = ["右栏_", "正式尺_", "元制度_", "项目宪法_", "体系建设总则_"]


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _strip_html(t):
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S | re.I)
    return re.sub(r"<[^>]+>", " ", t)


def _core_token(name):
    s = str(name)
    for p in _PREFIX:
        if s.startswith(p):
            s = s[len(p):]
    s = re.split(r"[_（(]", s)[0]   # 取第一段(去日期/版本后缀)
    return s.strip()


def _find_file(name):
    """名称→文件路径。优先stem含完整名称·退而含核token。返回(path, 归档否)。"""
    core = _core_token(name)
    cands = []
    for d in SEARCH_DIRS:
        for p in d.rglob("*.html"):
            stem = p.stem
            if str(name) in stem or (core and len(core) >= 3 and core in stem):
                arch = ("_历史归档" in str(p)) or ("废止" in str(p))
                # 评分:完整名称匹配>核token·非归档>归档
                score = (2 if str(name) in stem else 1) + (0 if arch else 1)
                cands.append((score, len(stem), p, arch))
    if not cands:
        return None, False
    cands.sort(key=lambda x: (-x[0], x[1]))   # 高分优先·短文件名优先(更精确)
    return cands[0][2], cands[0][3]


def _version(rec, path):
    v = rec.get("版本")
    if v and str(v) not in ("未标注", "None", ""):
        return str(v), False
    # 从文件名取 _vN / _v1.1
    if path:
        m = re.search(r"_v(\d+(?:\.\d+)?)", path.stem)
        if m:
            return "v" + m.group(1), False
    return "v1", True   # 推定


def _status(path, arch, name):
    """B-2 初判(结构化·由文件位置/名称判·非文本关键词)。状态变更仅董事长可裁定。"""
    if path is None:
        return "draft", "未在正式目录找到文件→draft(待定·如实标)"
    if "TEMPLATE" in path.stem.upper() or "模板" in path.stem:
        return "template", "文件名含TEMPLATE/模板→template(★永不当实际数据读)"
    if arch:
        return "deprecated", "文件在_历史归档/废止目录→deprecated"
    return "active", "在正式目录00_请先看这里且非模板→active(初判·变更须董事长)"


def build():
    ledger = _rj(LEDGER)
    insts = ledger.get("台账", [])
    # 先给每条定位文件+核token
    recs = []
    for r in insts:
        name = r.get("名称")
        path, arch = _find_file(name)
        ver, presumed = _version(r, path)
        status, status_why = _status(path, arch, name)
        recs.append({
            "制度ID": r.get("制度ID"), "名称": name,
            "路径": (str(path.relative_to(ROOT)).replace("\\", "/") if path else None),
            "version": ver, "version推定": presumed,
            "立法日期": r.get("生效日"), "级别": r.get("级别"),
            "程序化": (r.get("闸已接生产") == "是"), "闸已接生产(台账)": r.get("闸已接生产"),
            "status": status, "status初判理由": status_why,
            "_core": _core_token(name), "_text": (_strip_html(path.read_text(encoding="utf-8", errors="replace")) if path else ""),
        })
    # B-3 依赖实扫:A正文引用了B(制度ID / 名称 / 核token / 文件stem)→A depends_on B
    id2i = {x["制度ID"]: i for i, x in enumerate(recs)}
    for a in recs:
        deps = set()
        txt = a["_text"]
        if not txt:
            continue
        for b in recs:
            if b["制度ID"] == a["制度ID"]:
                continue
            hit = False
            # ①制度ID引用(最可靠)
            if b["制度ID"] and re.search(r"\b" + re.escape(b["制度ID"]) + r"\b", txt):
                hit = True
            # ②完整名称引用
            elif b["名称"] and str(b["名称"]) in txt:
                hit = True
            # ③核token引用(≥4字·防误命中通用短词)
            elif b["_core"] and len(b["_core"]) >= 4 and b["_core"] in txt:
                hit = True
            # ④文件stem引用
            elif b["路径"] and Path(b["路径"]).stem in txt:
                hit = True
            if hit:
                deps.add(b["制度ID"])
        a["depends_on"] = sorted(deps)
    # depended_by = 反向
    for a in recs:
        a["depended_by"] = sorted(b["制度ID"] for b in recs if a["制度ID"] in b.get("depends_on", []))
    # 清理临时字段
    n_dep = 0
    for a in recs:
        a.pop("_text", None); a.pop("_core", None)
        a["depends_on"] = a.get("depends_on", [])
        n_dep += len(a["depends_on"])
    out = {
        "_说明": "★轮181 B 治理三项(Version/Status/Dependency)。★status/version是结构化字段(§5.4)。"
                 "★status初判由文件位置判·【变更仅董事长可裁定·脚本不擅改】。★依赖为实扫正文引用·取不到标空·★不猜(董事长07-21被猜坑过)。",
        "date": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "制度总数": len(recs),
        "status分布": {s: sum(1 for a in recs if a["status"] == s) for s in ["active", "deprecated", "template", "draft", "superseded", "void"]},
        "version推定数(未标注→v1推定)": sum(1 for a in recs if a["version推定"]),
        "★依赖边总数(实扫)": n_dep,
        "未定位文件数": sum(1 for a in recs if not a["路径"]),
        "★注": "status变更须董事长裁定·脚本只初判;依赖只扫到的·未扫到=空(不猜)。",
        "制度": recs,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def alert_line():
    """B-4:一级制度 status==active 但 程序化==false → 告警(非阻断·Health Check雏形)。"""
    o = _rj(OUT)
    if not o:
        return "institution_registry 未建", 0, []
    bad = [a for a in o.get("制度", []) if a.get("级别") == 1 and a.get("status") == "active" and not a.get("程序化")]
    return ("★一级制度 active 但未程序化 %d 份(治理欠账·Health Check雏形·非阻断)" % len(bad)), len(bad), \
           [{"制度ID": a["制度ID"], "名称": a["名称"]} for a in bad]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)   # ★daily统一传--date·本步不用日期(建自台账)·收下忽略
    ap.parse_args()
    o = build()
    print("[institution_registry] %d份 · status分布 %s · version推定%d · ★依赖边%d · 未定位文件%d" % (
        o["制度总数"], json.dumps({k: v for k, v in o["status分布"].items() if v}, ensure_ascii=False),
        o["version推定数(未标注→v1推定)"], o["★依赖边总数(实扫)"], o["未定位文件数"]))
    line, n, bad = alert_line()
    print("  B-4告警:", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
