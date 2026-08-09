# -*- coding: utf-8 -*-
"""★轮134 A:扩候选宇宙。★候选宇宙来源＝【板块地图(sector_activation)激活板块的『承接节点』】·★不全市场扫(守轮111)·★不Code编名单(守G2)。
每个承接节点标的来自板块地图已有的『节点→标的』对应(承接节点字段)。★若板块地图无标的→如实报缺·不自行编。
输出 data/market/candidate_universe_{dc}.json:每标的带 板块/群/是否宇宙外新/来源节点。★守§5.4:选文件按data_date最新且排除TEMPLATE。"""
import sys, json, argparse, glob, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

HOLDINGS = {"JP.4568", "US.NVDA", "US.MSFT", "US.MSTR", "US.COIN", "JP.9984", "JP.8766", "JP.6758",
            "JP.6857", "JP.7203", "JP.8001", "JP.7832", "JP.7974", "US.AVGO", "US.CRCL", "US.SNDK",
            "US.TSM", "US.META", "US.IBKR", "US.SPCX"}


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _norm(t):
    """板块地图承接节点票号→归一(纯字母=美股加US.;已带前缀保留;.KS/.KQ韩股;数字.T日股)。"""
    t = str(t).strip()
    if t.startswith(("US.", "JP.", "HK.", "CC.", "KR.")):
        return t
    if t.endswith((".KS", ".KQ")):
        return "KR." + t.split(".")[0]
    if re.fullmatch(r"[A-Z]{1,5}", t):
        return "US." + t
    return t


def _latest_activation():
    """★§5.4:选 sector_activation 最新【非TEMPLATE】·按 data_date(非sorted[-1])。"""
    cands = []
    for p in glob.glob(str(ROOT / "data/market/sector_activation_*.json")):
        if "TEMPLATE" in Path(p).name:
            continue
        j = _rj(p)
        if j.get("★可用于生产") is not True:   # ★★★收尾:跳过未终验清单(可用于生产!=true)·防重判稿被自动选用
            continue
        cands.append((j.get("data_date") or Path(p).stem.split("_")[-1], p, j))
    if not cands:
        return None, {}
    cands.sort(key=lambda x: str(x[0]))
    return cands[-1][1], cands[-1][2]


def build(dc):
    src, sa = _latest_activation()
    univ = {}
    empty_nodes = []
    for b in (sa.get("板块", []) or []):
        if not b.get("激活"):
            continue
        nodes = b.get("承接节点") or []
        if not nodes:
            empty_nodes.append(b.get("格名") or b.get("板块"))    # ★P0-3兼容格名·板块地图有节点定义但无标的→如实报缺·不编
            continue
        for t in nodes:
            s = _norm(t)
            rec = univ.setdefault(s, {"symbol": s, "raw": t, "板块": [], "群": b.get("群"), "宇宙外新": s not in HOLDINGS})
            rec["板块"].append(b.get("格名") or b.get("板块"))  # ★P0-3:兼容格名
    out = {
        "_说明": "★轮134 候选宇宙＝板块地图(sector_activation)激活板块的承接节点。",
        "★★来源声明(PJ3·轮135)": ("★承接节点＝【Opus5 手填】(sector_activation 判定人=Opus5·投资判断·★非机器产出) — "
                                  "董事长07-31举例的股票经手填入清单·★不是机器发现的。总则第六条:只锚定义不锚具体标的死名单。"
                                  "★裁定:标的宇宙应改为【富途可拉全市场】+【Opus5定归类规则】(见轮135回报PJ1)·本清单为过渡·不冒充机器产物。"),
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "板块地图源": Path(src).name if src else None, "板块地图data_date": sa.get("data_date"), "★判定人": sa.get("判定人"),
        "★候选宇宙(承接节点)": sorted(univ.values(), key=lambda x: (not x["宇宙外新"], x["symbol"])),
        "宇宙标的数": len(univ), "★宇宙外新标的数": sum(1 for v in univ.values() if v["宇宙外新"]),
        "★板块有定义无标的(缺口·不编)": empty_nodes,
    }
    (ROOT / "data/market" / f"candidate_universe_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date.replace("-", ""))
    print("[候选宇宙] 源=%s · 共%d标的(★宇宙外新%d) · 板块无标的缺口%d" % (
        o["板块地图源"], o["宇宙标的数"], o["★宇宙外新标的数"], len(o["★板块有定义无标的(缺口·不编)"])))
    for v in o["★候选宇宙(承接节点)"]:
        print("  %s%s ← %s" % (v["symbol"], "(★宇宙外新)" if v["宇宙外新"] else "(持仓内)", "·".join(v["板块"][:2])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
