# -*- coding: utf-8 -*-
"""甲(轮372) 档案—当日实测差集闸。每日比对五项出差集·§5.4结构化字段(code集/股数/布尔·非自由文本):
①当日实际持仓(recompute/OpenD/账户快照) ②持仓档案(right-column/holdings_review) ③估值档案(datapack/val_inputs/model_instances)
④账户快照(per_account_*) ⑤上市状态与估值状态(是否上市/有无CIK/能否估值/是否标私司)。
差集非空→告警并列逐项差异。★先设告警不拦停(挂daily_auto_produce·跑稳两天再议升级)。
用法:python scripts/archive_reality_diff_gate.py --date 20260810"""
import sys, json, glob, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parents[1]

def rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}

def codes_of(obj):
    """从任意结构里抽 code 列表(结构化·找含'code'或'symbol'键的dict list)。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, list) and v and isinstance(v[0], dict) and any(("code" in x or "symbol" in x) for x in v):
                return [(x.get("code") or x.get("symbol")) for x in v if (x.get("code") or x.get("symbol"))]
            r = codes_of(v)
            if r:
                return r
    return []

# ★轮373甲:键名归一(§5.4·读 symbol_alias_map·五源比对前先归一)
_ALIAS2CANON = None
def _load_alias():
    global _ALIAS2CANON
    if _ALIAS2CANON is None:
        m = rj(ROOT / "data/governance/symbol_alias_map.json").get("canonical→aliases", {})
        _ALIAS2CANON = {}
        for canon, al in m.items():
            _ALIAS2CANON[canon] = canon
            for a in al:
                _ALIAS2CANON[str(a)] = canon
    return _ALIAS2CANON

def norm(k):
    """任意别名→canonical(US.XXXX/JP.NNNN)。未知→兜底规则(裸码/中文/后缀)·仍未知则原样。"""
    if k is None:
        return None
    a = _load_alias()
    ks = str(k).strip()
    if ks in a:
        return a[ks]
    ku = ks.upper().replace("US_", "US.").replace("_RELATIVE", "").replace("_DATAPACK", "")
    if ku in a:
        return a[ku]
    if ku.startswith(("US.", "JP.")):
        return ku
    if ks.isdigit() and len(ks) == 4:
        return "JP." + ks
    return ks

def nset(codes):
    return set(norm(c) for c in codes if c)

def run(date, suffix=""):
    dc = date.replace("-", "")
    dh = f"{dc[:4]}-{dc[4:6]}-{dc[6:]}"
    _load_alias()
    raw_keys = {}   # 甲4:每源归一前的原始键(供报归一前/后键数+合并了哪些别名)
    # ① 当日实际持仓(recompute=权威当前)·归一
    recompute = rj(ROOT / "data/accounts" / f"formal_daily_recompute_{dc}.json")
    _r1 = [h.get("code") for h in recompute.get("逐只", []) if h.get("code")]
    raw_keys["①实测持仓"] = sorted(set(_r1)); real_codes = nset(_r1)
    # ④ 账户快照(per_account union)·归一
    per_acc = {}
    raw_keys["④账户快照"] = {}
    for acc in ("富途", "SBI", "IBKR"):
        d = rj(ROOT / "data/accounts" / f"per_account_{acc}_{dc}.json")
        _c = codes_of(d)
        raw_keys["④账户快照"][acc] = sorted(set(_c))
        per_acc[acc] = nset(_c)
    acc_union = set().union(*per_acc.values()) if per_acc else set()
    # ② 持仓档案(holdings_review)·归一
    hr = rj(ROOT / "data/holdings" / f"holdings_review_{dc}.json")
    _a = codes_of(hr); raw_keys["②持仓档案"] = sorted(set(_a)); archive_codes = nset(_a)
    # ③ 估值档案(datapack/val_inputs holdings键/model_instances文件名)·★全部归一
    _val_raw = set()
    for f in glob.glob(str(ROOT / "data/valuation" / f"*_datapack_{dc}.json")):
        _val_raw.add(Path(f).name.split("_datapack")[0])
    vi = rj(ROOT / "data/valuation/val_inputs.json")
    _val_raw |= set((vi.get("holdings") or {}).keys())   # ★val_inputs是按code的dict·取键(前版codes_of取不到→假阳性根因)
    for f in glob.glob(str(ROOT / "data/valuation/model_instances/*.json")):
        _val_raw.add(Path(f).stem)
    raw_keys["③估值档案"] = sorted(_val_raw)
    dp_codes = set(); vi_codes = set(); mi_codes = set()  # (保留占位·合并到val_any)
    val_any_pre = _val_raw; val_any = nset(_val_raw)
    # ⑤ 上市/估值状态(edgar_field_availability·SPCX等)
    edgar = rj(ROOT / "data/valuation" / f"edgar_field_availability_{dc[:4]}-{dc[4:6]}-11.json") or rj(ROOT / "data/valuation/edgar_field_availability_20260811.json")
    upmark = []
    for r in edgar.get("逐只", []):
        st = str(r.get("★上市状态", "")) + str(r.get("status", "")) + str(r.get("原误标", ""))
        if "已上市" in st or "纠正" in st or "私司" in st:
            upmark.append({"code": r.get("code"), "状态": r.get("★上市状态") or r.get("status"), "原误标": r.get("原误标")})

    diffs = []
    # 差集1:账户快照有·实测无(档案多出/未更新·如万代已清仓)
    for c in sorted(acc_union - real_codes):
        acc_in = [a for a in per_acc if c in per_acc[a]]
        diffs.append({"类型": "账户快照有·当日实测无", "code": c, "在账户": acc_in,
                      "含义": "档案/快照仍列此标的但当日重算无→疑已清仓或快照未更新·须核实盘股数", "阻断": False})
    # 差集2:实测有·账户快照无(快照缺)
    for c in sorted(real_codes - acc_union):
        diffs.append({"类型": "当日实测有·账户快照无", "code": c,
                      "含义": "当日重算含此标的但per_account快照未覆盖→账户快照缺/不全·须补该只快照", "阻断": False})
    # 差集3:实测有·持仓档案(holdings_review)无
    for c in sorted(real_codes - archive_codes):
        diffs.append({"类型": "当日实测有·持仓档案(holdings_review)无", "code": c, "含义": "档案缺该只·须补档案", "阻断": False})
    for c in sorted(archive_codes - real_codes):
        diffs.append({"类型": "持仓档案有·当日实测无", "code": c, "含义": "档案多该只·疑已清仓·档案标已清仓留档", "阻断": False})
    # 差集4:实测有·估值档案(datapack/val_inputs归一后/model_instances归一后)全无
    for c in sorted(real_codes - val_any):
        diffs.append({"类型": "当日实测有·估值档案全无(datapack/val_inputs/model)", "code": c,
                      "含义": "该持仓无任何估值档案→估值覆盖缺口(部分为小仓/新上市/待建仓·须逐只确认·非键名假阳性)", "阻断": False})
    # 差集5:上市/估值状态曾误标(edgar已纠正)·归一
    for u in upmark:
        if u.get("原误标") or "纠正" in str(u.get("状态", "")):
            diffs.append({"类型": "上市/估值状态曾误标(已纠正)", "code": norm(u["code"]),
                          "含义": f"曾标{u.get('原误标','私司/无法估值')}·实际{u.get('状态')}→档案估值状态须同步", "阻断": True})
    # ★戊2:结构化字段 是否阻断发布(布尔)——四类真实差集命中即true(闸本身不拦停·但让终验一眼看到)
    for d in diffs:
        t = d["类型"]
        d["是否阻断发布"] = bool(
            ("账户快照" in t and "实测" in t) or   # 真实持仓漏记/账户快照与实测不一致
            ("上市" in t or "估值状态" in t) or     # 上市/估值状态错误
            d.get("阻断") is True)
        d.pop("阻断", None)

    # ★轮374丙:账户新鲜度判定(总则第十三条之二·接口/手动两类分开判·§5.4结构化字段·不猜)
    SRC = {"富途": "接口", "SBI": "手动", "IBKR": "手动", "bitFlyer": "手动"}
    acc_fresh = {}
    for acc, kind in SRC.items():
        # 找该账户最新快照(优先当日dc·否则最近)
        cand = sorted(glob.glob(str(ROOT / "data/accounts" / f"per_account_{acc}_*.json"))) if acc != "bitFlyer" \
            else sorted(glob.glob(str(ROOT / "data/accounts" / "bitflyer_*.json")))
        d = rj(cand[-1]) if cand else {}
        if kind == "接口":
            ddate = d.get("data_date") or d.get("源日") or ""
            ok = (str(ddate)[:10] == dh)
            acc_fresh[acc] = {"数据来源类别": "接口", "数据日期": ddate,
                              "判定": ("正常" if ok else "★故障(接口账户数据日期≠当日·须报修·不得沿用)"),
                              "是否阻断发布": (not ok)}
        else:
            conf = d.get("董事长确认")  # 此后无交易 / 有交易·已更新 / null
            shot = d.get("截图日期")
            if conf == "此后无交易":
                verdict, block = "有效(董事长确认此后无交易·不因日期久判过期)", False
            elif conf == "有交易·已更新":
                verdict, block = "有效(以新截图为准)", False
            else:
                verdict, block = "★状态不明(董事长确认字段=null·不猜·不假设有效也不假设过期)", True
            acc_fresh[acc] = {"数据来源类别": "手动", "截图日期": shot, "董事长确认": conf,
                              "判定": verdict, "是否阻断发布": block}
    # 把账户级阻断并入总阻断字段(供终验一眼看)
    _acc_block = sorted(a for a, v in acc_fresh.items() if v.get("是否阻断发布"))

    out = {
        "_闸": "甲 档案—当日实测差集闸(轮372建·轮374丙加账户新鲜度两类判·§5.4结构化·先告警不拦停)",
        "date": dh, "生成时刻": datetime.now(JST).isoformat(),
        "★账户新鲜度判定(丙·总则第十三条之二)": acc_fresh,
        "★账户级阻断发布(手动null或接口非当日)": _acc_block,
        "五项源": {
            "①当日实测持仓(recompute)": sorted(real_codes),
            "②持仓档案(holdings_review)": sorted(archive_codes),
            "③估值档案(datapack/val_inputs/model)": sorted(val_any),
            "④账户快照union(per_account)": sorted(acc_union),
            "⑤上市/估值状态标记(edgar)": upmark,
        },
        "账户快照分账户": {a: sorted(per_acc[a]) for a in per_acc},
        "★归一前后键数(甲4)": {
            "①实测持仓": {"归一前": len(raw_keys["①实测持仓"]), "归一后": len(real_codes)},
            "②持仓档案": {"归一前": len(raw_keys["②持仓档案"]), "归一后": len(archive_codes), "归一前键": raw_keys["②持仓档案"]},
            "③估值档案": {"归一前": len(raw_keys["③估值档案"]), "归一后": len(val_any),
                        "归一前键(含别名微软/MSTR/US_TSM_relative等)": raw_keys["③估值档案"], "归一后": sorted(val_any)},
            "④账户快照": {a: {"归一前": len(raw_keys["④账户快照"][a]), "归一后": len(per_acc[a])} for a in per_acc},
        },
        "★戊2_是否阻断发布(结构化)": {"命中阻断的差集数": sum(1 for d in diffs if d.get("是否阻断发布")),
            "阻断的code": sorted(set(d["code"] for d in diffs if d.get("是否阻断发布"))),
            "口径": "真实持仓漏记/账户快照与实测不一致/上市状态或估值状态错误/差集无法解释→是否阻断发布=true(闸本身告警不拦停·此字段供终验)"},
        "★差集数": len(diffs), "★差集清单": diffs,
        "结论": ("发现%d处档案—实测差集·告警(不拦停·跑稳两天再议升级)" % len(diffs)) if diffs else "无差集",
    }
    p = ROOT / "data/governance" / f"archive_reality_diff_{dc}{suffix}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out, p

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--suffix", default="")
    a = ap.parse_args()
    out, p = run(a.date, suffix=a.suffix)
    print(f"[档案-实测差集闸] {a.date} · 差集 {out['★差集数']} 处 → {p}")
    for d in out["★差集清单"]:
        print(f"  · {d['类型']}: {d['code']}")
    # 告警不拦停:恒 rc=0(附差集数)
    return 0

if __name__ == "__main__":
    sys.exit(main())
