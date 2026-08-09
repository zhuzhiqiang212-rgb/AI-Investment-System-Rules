# -*- coding: utf-8 -*-
"""归类回归测试闸(告警闸·不阻断·裁定08-07固化)。
三条(防误配·今晚证明价值:格18转true后IBKR若误入直接进候选·被排除词挡住):
 ① US.NVDA 不得归入【AI半导体设备】
 ② 任何券商(含 US.IBKR) 不得归入【AI基础设施外延】或【安全/国防】
 ③ 任何美股 不得归入【盟友链节点·日韩半导体】
★挂daily归类步之后·任一不过→报FAIL并写缺件文件·★不停生产线(exit 0)。"""
import sys, os, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _matchers():
    m = _rj(ROOT / "data/market/plate_to_sector_map.json")
    CK = m.get("激活格关键词", {}); EX = m.get("★★★排除词（排除优先于命中·防误配）", {})
    nf = _rj(ROOT / "data/market/plate_noise_filter.json"); NW, EW = list(nf.get("noise_substrings", []) or []), []
    for k, v in nf.items():
        if isinstance(v, dict) and "词" in v:
            (EW if "例外" in str(k) else NW).extend(v.get("词", []) or [])

    def clean(pls):
        out = []
        for p in pls:
            ps = str(p)
            if any(str(e) in ps for e in EW):
                out.append(p); continue
            if any(str(n) in ps for n in NW):
                continue
            out.append(p)
        return out

    def match(code, pls):
        j = " ".join(clean(pls)); r = []
        for nm in CK:
            e = EX.get(nm, {}) or {}; ew = e.get("排除", []) or []; g = e.get("★必须同时满足的地域条件") or e.get("地域条件")
            if g and not (str(code).startswith(("JP.", "KR.")) or str(code).endswith((".T", ".KS", ".KQ"))):
                continue
            exempt = e.get("★★★免除排除（豁免词·命中则排除词不生效）") or e.get("免除排除") or []   # ★免除机制(通用)
            _exempted = bool(exempt) and any(str(x) in j for x in exempt)
            if ew and not _exempted and any(str(x) in j for x in ew):
                continue
            if any(str(k).lower() in j.lower() for k in CK[nm]):
                r.append(nm)
        return r
    return match


def run():
    match = _matchers()
    fails = []
    # ① NVDA 不入 AI半导体设备
    r1 = match("US.NVDA", ["GPU", "AI芯片", "半导体", "热门美股"])
    if "AI半导体设备" in r1:
        fails.append("第1条不过·US.NVDA 被误归入 AI半导体设备(归到%s)" % r1)
    # ② 券商(IBKR)不入 AI基础设施/安全国防
    r2 = match("US.IBKR", ["券商", "证券经纪", "互联网券商", "网络", "美股科技股"])
    bad2 = [x for x in r2 if x in ("AI基础设施外延·冷却/数据中心/网络", "安全/国防·军工/太空/网络安全")]
    if bad2:
        fails.append("第2条不过·券商 US.IBKR 被误归入 %s" % bad2)
    # ③ 美股不入 盟友链·日韩半导体
    r3 = match("US.AMAT", ["半导体材料", "半导体", "特种气体"])
    if "盟友链节点·日韩半导体" in r3:
        fails.append("第3条不过·美股 US.AMAT 被误归入 盟友链节点·日韩半导体")
    return fails


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=False); ap.parse_known_args()  # ★接受daily传的--date(本闸不需日期·忽略)
    fails = run()
    if fails:
        # ★写缺件文件(告警·不阻断)
        miss = ROOT / "00_请先看这里" / "★★今日缺件_卡在谁.txt"
        try:
            lines = miss.read_text(encoding="utf-8").splitlines() if miss.exists() else []
        except Exception:
            lines = []
        for i, f in enumerate(fails, 1):
            lines.append("[归类回归] %s" % f)
        miss.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("[归类回归] ★FAIL %d条:" % len(fails))
        for f in fails:
            print("  -", f)
    else:
        print("[归类回归] PASS 三条全过(NVDA不入设备/券商不入基础设施国防/美股不入盟友链)")
    return 0   # ★告警闸·永不阻断生产线(exit 0)


if __name__ == "__main__":
    raise SystemExit(main())
