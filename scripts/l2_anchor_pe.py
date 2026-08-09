# -*- coding: utf-8 -*-
"""★★★轮196 B · 补 L2 基本面锚点②(同业PE中位 × EPS)。
背景(董事长验收点破):轮195 top30 用④三年最高价兜底=【跌幅排序】非【预期收益排序】——
  三年高是曾经的价格·不是合理估值·不能拿去做L2三档分流。本轮补锚点②让L2粗估真正跑起来。

B-1 取EPS:富途snapshot earning_per_share(★TTM口径·全189一致·不混EDGAR/EDINET多口径)。
    ★港股EPS经富途现有设施可得(非新接EDINET·未越"不接港股财务源"红线)。
B-2 同业PE中位:owner_plate INDUSTRY分类 → get_plate_stock成员 → snapshot pe_ttm>0且有EPS →
    ★样本<10只标NK4(承§5.5小样本不下结论)·★用中位数非平均(防极值)。
B-3 锚点②=同业PE中位×本公司EPS;粗估空间②=(锚点②−现价)/现价;★与④三年高【并列】不覆盖。
B-4 重排top30:优先②·②不可得降级④并★标明·每只标明用哪个锚点。
"""
import sys, json, time, argparse, statistics
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def rank_by_space2(rows, limit=30):
    """★轮200(证明1):重排【只读『空间②』】。三年高/空间④等键一律不参与排序。
    ★纯函数·可被攻击测试证明:扰动 rows 里的 参考_空间④/三年最高价 → 本函数输出的排序结果不变。"""
    elig = [r for r in rows if r.get("空间②") is not None]
    return sorted(elig, key=lambda r: -r["空间②"])[:limit]


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _snap_batch(q, codes):
    """分批snapshot(≤300/批·限速)。返回 {code: row_dict}。"""
    out = {}
    for i in range(0, len(codes), 300):
        chunk = codes[i:i + 300]
        for _try in range(3):
            ret, df = q.get_market_snapshot(chunk)
            if ret == 0:
                for _, r in df.iterrows():
                    out[r["code"]] = {"eps": r.get("earning_per_share"), "pe_ttm": r.get("pe_ttm_ratio"),
                                      "price": r.get("last_price"), "hi52": r.get("highest52weeks_price"),
                                      "name": r.get("name")}
                break
            time.sleep(2)   # 限速/配额退避
        time.sleep(0.4)
    return out


def build(date, limit=30):
    dc = date.replace("-", "")
    from futu import OpenQuoteContext
    import warnings; warnings.filterwarnings("ignore")
    audit = _rj(ROOT / "data/universe" / f"p4_candidate_audit_{dc}.json")
    cand = [{"代码": r["代码"], "现价": (r.get("原始数值") or {}).get("price")} for r in audit.get("逐只", []) if r.get("pass2")]
    codes = [c["代码"] for c in cand]
    # ④三年高(轮195已拉·并列保留不覆盖)
    L12 = _rj(ROOT / "data/funnel" / f"L1_L2_estimate_{dc}.json")
    hi3_by = {}
    for k in L12:
        if k.startswith("★L1_L2约"):
            for e in L12[k]:
                hi3_by[e["代码"]] = e.get("④三年最高价")
    # NK4列表里的④也可能有(轮195只对top30填④·其余需从④=兜底)。此处④仅用于并列展示·主排序用②。

    q = OpenQuoteContext(host="127.0.0.1", port=11111)
    print("[l2] snapshot 189候选…", flush=True)
    snap = _snap_batch(q, codes)
    # owner_plate INDUSTRY 分类
    print("[l2] owner_plate 189…", flush=True)
    ind_by = {}
    for i in range(0, len(codes), 200):
        ret, df = q.get_owner_plate(codes[i:i + 200])
        if ret == 0:
            sub = df[df["plate_type"] == "INDUSTRY"] if "plate_type" in df.columns else df
            for _, r in sub.iterrows():
                ind_by.setdefault(r["code"], {"plate_code": r["plate_code"], "plate_name": r["plate_name"]})
        time.sleep(0.4)
    # 每个行业成员 → 并union → snapshot取pe_ttm → 中位(样本≥10)
    plates = {v["plate_code"]: v["plate_name"] for v in ind_by.values()}
    print("[l2] 涉及行业数=%d · 拉成员…" % len(plates), flush=True)
    members_by_plate = {}
    all_members = set()
    for pc in plates:
        for _try in range(3):
            ret, dfm = q.get_plate_stock(pc)
            if ret == 0:
                ms = list(dfm["code"])
                members_by_plate[pc] = ms
                all_members.update(ms)
                break
            time.sleep(2)
        time.sleep(0.3)
    all_members = sorted(all_members)
    print("[l2] 同业成员union=%d · snapshot取pe_ttm(限速·可能数千·耐心)…" % len(all_members), flush=True)
    peer_snap = _snap_batch(q, all_members)
    q.close()

    # 行业PE中位(pe_ttm>0且有EPS·样本≥10·中位)
    ind_median = {}
    for pc, ms in members_by_plate.items():
        vals = []
        for m in ms:
            s = peer_snap.get(m) or {}
            pe = s.get("pe_ttm"); eps = s.get("eps")
            if pe is not None and pe > 0 and eps is not None and eps != 0:
                vals.append(pe)
        if len(vals) >= 10:
            ind_median[pc] = {"median_pe": round(statistics.median(vals), 2), "sample": len(vals)}
        else:
            ind_median[pc] = {"median_pe": None, "sample": len(vals), "NK4": "样本<10(§5.5小样本不下结论)"}

    # ★轮197 A-3:每个行业PE中位=一个锚点·分配 anchor_id + 六项留痕(同业样本/期间/币种/异常值处理/PE口径/EPS期间)
    plate_ccy = lambda pc: ("JPY" if str(pc).startswith("JP.") else "HKD" if str(pc).startswith("HK.") else "USD")
    anchor_records = {}   # pc -> anchor记录
    for pc, m in ind_median.items():
        if not m.get("median_pe"):
            continue
        # 同业样本清单(参与中位·可回溯):该行业内 pe_ttm>0且有eps 的成员
        sample_codes = [mm for mm in members_by_plate.get(pc, [])
                        if (peer_snap.get(mm) or {}).get("pe_ttm", 0) and (peer_snap.get(mm) or {}).get("pe_ttm") > 0
                        and (peer_snap.get(mm) or {}).get("eps") not in (None, 0)]
        rec = {
            "value": m["median_pe"], "行业": plates.get(pc),
            "同业样本": sample_codes, "期间": "TTM", "币种": plate_ccy(pc),
            "异常值处理": "未剔除极值·用中位数(median)抗极值", "PE口径": "滚动TTM", "EPS期间": "TTM",
            "计算方法": "同业PE中位×本公司EPS",   # ★A-3:计算方法进身份
            "使用标的": [],   # 下面回填
        }
        # ★轮200-B A-3:anchor_id 由【全部身份属性(期间/币种/口径/EPS期间/异常值处理/计算方法/取值/样本集)】派生·
        #   plate_code 作可读前缀·后接身份指纹哈希→任一身份属性变即不同 anchor_id。
        import dup_count_gate as _dg
        rec["anchor_id"] = "PE_MED_%s_%s" % (pc, _dg.make_anchor_id(rec).split("_")[-1])
        anchor_records[pc] = rec

    # 逐候选:锚点②(★性质=待验证·非公允价值) + 三年高降级为参考列(★不作排序锚点·C-1)
    rows = []
    for c in cand:
        code = c["代码"]; s = snap.get(code) or {}
        eps = s.get("eps"); px = s.get("price") or c.get("现价")
        ind = ind_by.get(code, {}); pc = ind.get("plate_code")
        med = ind_median.get(pc, {}) if pc else {}
        med_pe = med.get("median_pe")
        anchor2 = None; space2 = None; anchor2_note = None; aid = None
        if eps is not None and eps > 0 and med_pe:
            anchor2 = round(med_pe * eps, 2)
            space2 = round((anchor2 - px) / px, 4) if px else None
            aid = anchor_records.get(pc, {}).get("anchor_id")
            if pc in anchor_records:
                anchor_records[pc]["使用标的"].append(code)
        elif eps is None or eps <= 0:
            anchor2_note = "EPS≤0或缺→锚点②不适用"
        elif not med_pe:
            anchor2_note = "同业样本<10→PE中位NK4"
        hi3 = hi3_by.get(code)
        space4 = round((hi3 - px) / px, 4) if (hi3 and isinstance(hi3, (int, float)) and px) else None
        rows.append({
            "代码": code, "名称": s.get("name"), "现价": px,
            "EPS_TTM": eps, "口径": "TTM·富途snapshot",
            "行业": ind.get("plate_name"), "行业plate": pc,
            "同业PE中位": med_pe, "同业样本数": med.get("sample"), "anchor_id": aid,
            "★锚点②(同业PE中位×EPS)": anchor2, "空间②": space2, "锚点②备注": anchor2_note,
            "★锚点性质": "待验证(非公允价值·待Opus5核)",   # ★C-2
            "参考列_三年最高价(★不作排序锚点·C-1)": hi3 if isinstance(hi3, (int, float)) else None,
            "参考_空间④(仅参考·不排序)": space4,
            "★排序用锚点": ("②同业PE(待验证)" if anchor2 is not None else "NK4(无②·三年高仅参考不排序)"),
        })

    # C 三数字
    c1_eps = sum(1 for r in rows if r["EPS_TTM"] is not None and r["EPS_TTM"] != 0)
    c1_eps_pos = sum(1 for r in rows if r["EPS_TTM"] is not None and r["EPS_TTM"] > 0)
    inds_ok = sorted({pc for pc, m in ind_median.items() if m.get("median_pe")})
    c2_ind = len(inds_ok)
    c3_use2 = sum(1 for r in rows if r["空间②"] is not None)
    c3_nk4 = sum(1 for r in rows if r["空间②"] is None)

    # ②vs④差异巨大(参考信息:跌得多但按盈利不便宜)——④仅参考·不用于排序
    big_gap = []
    for r in rows:
        s2 = r["空间②"]; s4 = r["参考_空间④(仅参考·不排序)"]
        if s2 is not None and s4 is not None and abs(s4 - s2) >= 0.5:
            big_gap.append({"代码": r["代码"], "名称": r["名称"], "空间②": s2, "参考空间④": s4,
                            "解读": "④(跌幅)大但②(按盈利)小→跌得多但按盈利不便宜" if s2 < s4 else "②>④"})
    big_gap.sort(key=lambda x: -(x["参考空间④"] - x["空间②"]))

    # ★C-1:重排top30【只用锚点②(待验证)】·三年高不作排序锚点(C-1)·无②的不进top
    # ★轮200(证明1):用独立函数 rank_by_space2·★只读『空间②』一个键·三年高/空间④绝不进排序路径(可被攻击测试证明)。
    top = rank_by_space2(rows, limit)

    # ★轮197 A-5:对每个【共享锚点(使用标的≥2)】算敏感性三档(中位/×0.75/×1.25)
    import dup_count_gate as dg
    anchors_list = [a for a in anchor_records.values() if len(a["使用标的"]) >= 1]
    shared_anchors = [a for a in anchor_records.values() if len(a["使用标的"]) >= 2]
    eps_by = {r["代码"]: r["EPS_TTM"] for r in rows}
    px_by = {r["代码"]: r["现价"] for r in rows}
    sens = []
    for a in sorted(shared_anchors, key=lambda x: -len(x["使用标的"])):
        using_rows = [{"代码": cc, "现价": px_by.get(cc), "EPS": eps_by.get(cc)} for cc in a["使用标的"]]
        s3 = dg.sensitivity_three(a["value"], using_rows)
        sens.append({"anchor_id": a["anchor_id"], "行业": a["行业"], "锚点中位PE": a["value"],
                     "共用标的数": len(a["使用标的"]), "三档敏感性": s3})
    # ★轮197 判定4:锚点闸(共享输入留痕+PE期间一致性+字段完整)
    anchor_gate = dg.check_anchors(anchors_list)

    out = {
        "date": date,
        "_说明": "★轮197修正版·L2基本面锚点②(同业PE中位×EPS)。★锚点性质=待验证(非公允价值)。★三年高降级为参考列(不作排序锚点·C-1)。★共享锚点anchor_id留痕+敏感性三档+PE期间一致性校验(判定4)。★L2三档分流=Opus5(Code只补锚点)。",
        "★C-1_189有EPS数": c1_eps, "★C-1_其中EPS大于0": c1_eps_pos,
        "★C-2_可算同业PE中位的行业数(样本≥10)": c2_ind,
        "★C-3_最终能用锚点②数": c3_use2, "★C-3_NK4数(无②)": c3_nk4,
        "★L2粗估运行条件判定": ("★具备(能用②≥30只)" if c3_use2 >= 30 else "★★仍不具备运行条件(能用②的<30只)·如实报不硬凑"),
        "★锚点性质声明": "②同业PE×EPS=待验证估值锚点·非公允价值·不得自动视为可信(C-2)。三年高=参考列·不作排序锚点(C-1)。",
        "②与④差异巨大只数": len(big_gap), "②vs④差异巨大(参考信息)": big_gap[:15],
        "★轮197_共享锚点留痕(判定4)": anchor_gate,
        "★轮197_敏感性三档(中位/×0.75/×1.25)": sens,
        "★锚点记录(六项留痕·A-3)": list(anchor_records.values()),
        f"★重排top{limit}(★只用锚点②·三年高仅参考)": top,
        "全189逐只": rows,
    }
    (ROOT / "data/funnel").mkdir(parents=True, exist_ok=True)
    (ROOT / "data/funnel" / f"L2_anchor_pe_{dc}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="2026-08-05"); ap.add_argument("--limit", type=int, default=30)
    a = ap.parse_args()
    o = build(a.date, a.limit)
    print("═══ 轮197 L2锚点②(修正版) ═══")
    print("C-1 有EPS %d/189(EPS>0 %d) · C-2 可算同业PE中位行业 %d · C-3 用②%d/NK4 %d" % (
        o["★C-1_189有EPS数"], o["★C-1_其中EPS大于0"], o["★C-2_可算同业PE中位的行业数(样本≥10)"],
        o["★C-3_最终能用锚点②数"], o["★C-3_NK4数(无②)"]))
    print(o["★L2粗估运行条件判定"])
    ag = o["★轮197_共享锚点留痕(判定4)"]
    print("判定4:共享输入需联动=%s · PE期间FAIL数=%d · 敏感性锚点数=%d" % (
        ag["有共享输入需联动"], len(ag["明细"].get("PE期间一致性FAIL", [])), len(o["★轮197_敏感性三档(中位/×0.75/×1.25)"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
