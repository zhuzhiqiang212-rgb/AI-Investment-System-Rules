# -*- coding: utf-8 -*-
"""★轮88 GA3:候选池由【全市场扫描】产出·不从承接节点取(违反看板G2/总则第六条已作废)。
链条:first_scan2 的 universe→硬门槛入围(fin_score) → ★按激活板块行业归类过滤 → candidate_pool。
GA3-2:行业分类用 first_scan2 的 get_owner_plate(plate_name·OpenD真源)·无则报『行业分类源未接』不自编。
GA3-3:承接节点代表标的降级为【校验用】——核对每个激活格归类结果是否含代表标的·不含→报出不静默。
GA3-4:韩股 universe 未接(first_scan2 只扫US+JP)→三星/SK海力士等如实标未接·不用定向2只冒充。
输出 data/opportunity/candidate_pool_{date}.json(覆盖·scan产出) + data/opportunity/classify_audit_{date}.json。"""
import sys, json, argparse, glob
from datetime import datetime, timezone, timedelta
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
SCREEN = ROOT / "data" / "screen"

def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


# ★HA1-1:关键词映射表从可读文件读(不写死代码)
_MAP = _rj(ROOT / "data/market/plate_to_sector_map.json")
CELL_KW = _MAP.get("激活格关键词", {})
# ★v2:排除词(排除优先于命中·防IBKR/NVDA类误配)+地域判据(盟友链须JP./KR.)。Code只实现机制·内容(关键词/排除词)由Opus5改表。
EXCL = _MAP.get("★★★排除词（排除优先于命中·防误配）", {}) or {}
SEMI_BROAD = _MAP.get("半导体大类关键词(细分不可分时的标记·非归格)", ["半导体", "芯片", "集成电路"])
# ★轮93 LA1-3:与半导体/AI格明显冲突的行业属性(商社/银行/保险/有色金属/批发)——落这些格=sector_conflict
CONFLICT_IND = ["综合商社", "商社", "批发业", "银行", "保险", "证券公司", "有色金属", "钢铁", "贸易", "综合金融", "铜・电线", "运输", "地产", "REIT"]


def _fetch_owner_plates(codes, dc):
    """★HA1-1:查全板块列表(get_owner_plate·多板块)·缓存。★按市场分组+小批(get_owner_plate混市场/大批会静默漏US)。
    覆盖不全(有码无板块)→重抓该码。OpenD不可用→用缓存·仍无→空。"""
    cache = ROOT / "data/screen" / f"owner_plates_{dc}.json"
    cached = _rj(cache)
    plates = dict(cached.get("plates", {}))
    # 缺板块的码(不在缓存 或 缓存里为空)→需(重)抓
    todo = [c for c in codes if not plates.get(c)]
    if not todo:
        return plates, cached.get("源", "缓存(全覆盖)")
    src = cached.get("源", "缓存")
    try:
        import futu as ft, time as _t
        q = ft.OpenQuoteContext(host="127.0.0.1", port=11111)
        try:
            # ★按市场分组·每组小批100(避免混市场静默漏)
            by_mk = {}
            for c in todo:
                by_mk.setdefault(str(c).split(".")[0], []).append(c)
            for mk, cs in by_mk.items():
                for i in range(0, len(cs), 100):
                    part = cs[i:i + 100]
                    try:
                        ret, df = q.get_owner_plate(part)
                        if ret == ft.RET_OK:
                            for _, r in df.iterrows():
                                plates.setdefault(str(r.get("code")), []).append(str(r.get("plate_name")))
                    except Exception:
                        pass
                    _t.sleep(1.2)
            src = "OpenD get_owner_plate(全板块列表·分市场小批)"
        finally:
            q.close()
        cache.write_text(json.dumps({"源": src, "plates": plates}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        src = "OpenD不可用(%s)·用缓存" % type(e).__name__
    return plates, src


def _fetch_names(codes, dc):
    """查股名(get_stock_basicinfo·本地化业务名)·缓存 names_{dc}.json。供IA1业务词细分解析。"""
    if not codes:
        return {}, "无"
    cache = ROOT / "data/screen" / f"names_{dc}.json"
    names = dict(_rj(cache).get("names", {}))
    todo = [c for c in codes if c not in names]
    if not todo:
        return names, "缓存"
    try:
        import futu as ft, time as _t
        q = ft.OpenQuoteContext(host="127.0.0.1", port=11111)
        try:
            by_mk = {}
            for c in todo:
                by_mk.setdefault(str(c).split(".")[0], []).append(c)
            for mk, cs in by_mk.items():
                MK = ft.Market.US if mk == "US" else ft.Market.JP
                for i in range(0, len(cs), 100):
                    try:
                        ret, df = q.get_stock_basicinfo(MK, ft.SecurityType.STOCK, code_list=cs[i:i + 100])
                        if ret == ft.RET_OK:
                            for _, r in df.iterrows():
                                names[str(r["code"])] = str(r.get("name", ""))
                    except Exception:
                        pass
                    _t.sleep(1.0)
        finally:
            q.close()
        cache.write_text(json.dumps({"names": names}, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return names, "OpenD get_stock_basicinfo"


def _fetch_snapshot(codes, dc):
    """查snapshot(EPS/PE_TTM/price/市值)·供IA2简易估值。"""
    if not codes:
        return {}, "无"
    out = {}
    try:
        import futu as ft, time as _t
        q = ft.OpenQuoteContext(host="127.0.0.1", port=11111)
        try:
            for i in range(0, len(codes), 100):
                try:
                    ret, s = q.get_market_snapshot(codes[i:i + 100])
                    if ret == ft.RET_OK:
                        for _, r in s.iterrows():
                            out[str(r["code"])] = {"eps": float(r.get("earning_per_share")) if r.get("earning_per_share") not in (None, "N/A") else None,
                                                   "pe_ttm": float(r.get("pe_ttm_ratio")) if r.get("pe_ttm_ratio") not in (None, "N/A") else None,
                                                   "price": float(r.get("last_price")) if r.get("last_price") not in (None, "N/A") else None,
                                                   "market_val": float(r.get("total_market_val")) if r.get("total_market_val") not in (None, "N/A") else None}
                except Exception:
                    pass
                _t.sleep(1.0)
        finally:
            q.close()
    except Exception:
        pass
    return out, "OpenD get_market_snapshot"


def build(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    # 1) 全市场扫描入围(fin_score:scores=入围码+industry) + gate(per_stock有turnover/mktval)
    fs = _rj(SCREEN / f"fin_score_{dc}.json")
    gate = _rj(SCREEN / f"gate_{dc}.json")
    uni = _rj(SCREEN / f"universe_{dc}.json")
    scores = fs.get("scores", {})
    per = gate.get("per_stock", {})
    if not scores:
        return {"date": dh, "produced": False,
                "reason": "★first_scan2 全市场扫描未产出 fin_score(universe/入围)·候选池无法由扫描产出·据实未产出(不从承接节点凑)",
                "candidates": []}, {}
    # 2) 激活清单(选取:排除TEMPLATE·data_date最新≤当日·EA2)
    _cf = []
    for f in glob.glob(str(ROOT / "data/market/sector_activation_*.json")):
        if "TEMPLATE" in Path(f).name.upper():
            continue
        _fj = _rj(f)
        if _fj.get("★可用于生产") is not True:   # ★★★收尾:跳过未终验清单(可用于生产!=true)·防未经GPT终验的重判稿被自动选用
            continue
        _dt = _fj.get("data_date", "")
        if _dt and _dt <= dh:
            _cf.append((_dt, f))
    _cf.sort()
    if not _cf:
        return {"date": dh, "produced": False, "reason": "无有效激活清单", "candidates": []}, {}
    act = _rj(_cf[-1][1])
    cells_all = act.get("板块", [])
    def _cellnm(cc):
        return (cc.get("格名") or cc.get("板块"))

    def _cellstatus(cc):   # ★★★第1关三分(裁定08-07):格 true(已查证激活)/false(已查证不活跃)/待判(证据不足)
        if cc.get("激活") is True:
            return "true"
        if cc.get("激活") is False or str(cc.get("状态")).lower() == "false":
            return "false"
        return "待判"
    active_names = [_cellnm(c) for c in cells_all if _cellstatus(c) == "true"]      # true→①候选
    false_names = [_cellnm(c) for c in cells_all if _cellstatus(c) == "false"]      # false→②淘汰(真第1关否决)
    pending_names = [_cellnm(c) for c in cells_all if _cellstatus(c) == "待判"]      # 待判→③待激活观察池(不淘汰·不进候选)
    cell_names = active_names  # ★兼容下游(半导体细分只归激活格·true)
    _cell_group = {_cellnm(c): c.get("群") for c in cells_all}
    _cell_no = {_cellnm(c): c.get("格号") for c in cells_all}
    # ★★★裁定《归类失败不等于淘汰》(08-07):三分——①归类成功+格激活→候选池 ②归类成功+格未激活→淘汰(第1关否决) ③归类失败→待归类池(★不淘汰)。
    # ★噪音过滤名单v2(Opus维护·Code只执行)——六类噪音词dict + 例外清单。兼容v1的 noise_substrings。
    _NF = _rj(ROOT / "data/market/plate_noise_filter.json")
    NOISE_WORDS, EXCEPT_WORDS = list(_NF.get("noise_substrings", []) or []), []
    for _k, _v in _NF.items():
        if isinstance(_v, dict) and "词" in _v:
            (EXCEPT_WORDS if "例外" in str(_k) else NOISE_WORDS).extend(_v.get("词", []) or [])

    def _clean_plates(pls):   # ★净化(v2):①例外清单优先命中→保留 ②否则六类噪音词命中→剔除(归类最前一步)
        out = []
        for p in pls:
            ps = str(p)
            if any(str(ex) in ps for ex in EXCEPT_WORDS):   # ①例外(智能驾驶概念股等·带概念股后缀但真方向)→保留
                out.append(p); continue
            if any(str(nz) in ps for nz in NOISE_WORDS):     # ②六类噪音词(榜单/题材/过宽标签/券商清单/上市状态/人物持仓)→剔除
                continue
            out.append(p)
        return out

    def _match(code, pls_join, names):   # 顺序:地域→★免除词→排除词→关键词(免除机制·通用·裁定08-07)
        m = []
        for nm in names:
            ex_cfg = EXCL.get(nm, {}) or {}
            ex_words = ex_cfg.get("排除", []) or []
            geo = ex_cfg.get("★必须同时满足的地域条件") or ex_cfg.get("地域条件")
            if geo and not (str(code).startswith(("JP.", "KR.")) or str(code).endswith((".T", ".KS", ".KQ"))):
                continue
            # ★★★免除机制(通用):板块名含免除词(如网络安全概念/信息安全)→该格排除词对它不生效(真网安即使是软件公司也留)。
            exempt = ex_cfg.get("★★★免除排除（豁免词·命中则排除词不生效）") or ex_cfg.get("免除排除") or []
            _exempted = bool(exempt) and any(str(x).lower() in pls_join.lower() for x in exempt)
            if ex_words and not _exempted and any(str(x).lower() in pls_join.lower() for x in ex_words):
                continue
            if any(k.lower() in pls_join.lower() for k in CELL_KW.get(nm, [])):
                m.append(nm)
        return m
    # 3) ★HA1-1:按激活格行业归类——全板块列表·顺序=噪音过滤→地域→排除→关键词
    all_plates, plate_src = _fetch_owner_plates(list(scores.keys()), dc)
    pool = {}                 # ①激活格 → [候选码]
    semi_unclassified = []    # 命中半导体大类但无细分格→业务词细分(HA1-3)
    unmapped = []             # ③归类失败(待归类池·★不淘汰)
    eliminated_false = []     # ②淘汰(归到false格·已查证不活跃·真第1关一票否决)
    pending_pool = []         # ★★★③待激活观察池(归到待判格·★不淘汰·★不进候选·出口只有格判true/false)
    all_noise_filtered = []   # 板块名全被噪音过滤光(彻底没信息)→计入③
    conflicts = []            # ★LA1-3:行业冲突(商社/银行落半导体/AI格)→排除·报出
    for c, sc in scores.items():
        raw_pls = all_plates.get(c, [])
        pls = _clean_plates(raw_pls)   # ★噪音过滤(最前一步)
        pls_join = " ".join(pls)
        rec = {"code": c, "板块列表": pls, "raw_板块列表": raw_pls,
               "market_val": per.get(c, {}).get("market_val"),
               "avg_turnover_60d_usd": per.get(c, {}).get("avg_turnover_60d_usd"),
               "financial_quality_score": sc.get("financial_quality_score")}
        if not pls:   # 板块名全被噪音过滤光→彻底没信息→③待归类(单独标)
            r3 = dict(rec); r3["为什么没归上"] = "板块名全部被噪音过滤(券商清单/上市状态/人物概念)·无行业板块名可判"
            all_noise_filtered.append(r3); unmapped.append(r3); continue
        matched = _match(c, pls_join, active_names)   # 先匹配激活格
        if matched:
            conflict_ind = [w for w in CONFLICT_IND if any(w in p for p in pls)]
            semi_ai_cells = [m for m in matched if ("半导体" in m or "AI" in m or "代工" in m or "材料" in m)]
            if conflict_ind and semi_ai_cells:
                rec2 = dict(rec); rec2["sector_conflict"] = True; rec2["冲突行业"] = conflict_ind; rec2["误落格"] = matched
                conflicts.append(rec2); continue
            rec["归类置信度"] = "低(多格冲突)" if len(set(matched)) >= 2 else "高(专属词命中)"
            for nm in matched:
                pool.setdefault(nm, []).append(rec)
            continue
        # ★★★第1关三分(裁定08-07):关键词匹配(激活→false→待判)【先于】半导体大类兜底。
        # ⑤b false格→②淘汰(真第1关一票否决·格已查证不活跃)
        matched_false = _match(c, pls_join, false_names)
        if matched_false:
            r2 = dict(rec); r2["归类到(false格·已判不活跃)"] = matched_false; r2["处置"] = "淘汰·第1关一票否决(格已查证不活跃)"
            eliminated_false.append(r2); continue
        # ⑤c 待判格→★③待激活观察池(★不淘汰·★不进候选·出口只有格判true/false)
        matched_pending = _match(c, pls_join, pending_names)
        if matched_pending:
            r3p = dict(rec); r3p["归类到(待判格)"] = matched_pending
            r3p["处置"] = "★待激活观察池(格待判·证据不足)·不淘汰·不进候选·不进第2-5关·出口只有该格被判true(→候选)/false(→淘汰)"
            pending_pool.append(r3p); continue
        # ⑥ 半导体大类兜底(★仅完全没匹配任何格·才进):试业务词解析到激活细分格
        if any(b.lower() in pls_join.lower() for b in SEMI_BROAD):
            semi_unclassified.append(rec); continue   # 半导体大类·下一步业务词细分(仍找激活格)
        # ⑦ 啥格都不中→③待归类(归类失败·★不淘汰)
        r3 = dict(rec); r3["为什么没归上"] = "板块名不含任何格(true/false/待判)的关键词·或命中排除词→匹配不上任何格"
        unmapped.append(r3)
    # ★轮90 IA1:对半导体大类不可分的·用【业务词(股名)】映射表解析细分格(绕开分类法天花板)
    biz_map = _rj(ROOT / "data/market/business_keyword_to_sector_map.json").get("细分格业务关键词", {})
    fine_names, _ = _fetch_names([r["code"] for r in semi_unclassified], dc)
    fine_resolved, fine_unresolved = 0, []
    for r in semi_unclassified:
        nmtxt = str(fine_names.get(r["code"], ""))
        hit_cell = None
        for cell, kws in biz_map.items():
            if cell in cell_names and any(k.lower() in nmtxt.lower() for k in kws):
                hit_cell = cell; break
        if hit_cell:
            r2 = dict(r); r2["股名"] = nmtxt; r2["细分解析来源"] = "业务词(股名)匹配"
            pool.setdefault(hit_cell, []).append(r2); fine_resolved += 1
        else:
            fine_unresolved.append({"code": r["code"], "股名": nmtxt, "板块列表": r.get("板块列表"),
                                    "sector_fine_unresolved": True, "说明": "半导体大类·股名无业务词命中·真业务描述需IR源(未接免密钥)·不自编不硬塞(IA1-4)"})
    # ★轮91 JA3-1/2:把业务词(股名)解析扩到 unmapped(catch TSM 台积电→代工·补plate盲区)。仅补·不覆盖已归类。
    ja3_names, _ = _fetch_names([u["code"] for u in unmapped], dc)
    ja3_resolved = 0; still_unmapped = []
    for u in unmapped:
        nmtxt = str(ja3_names.get(u["code"], ""))
        hit = None
        for cell, kws in biz_map.items():
            if cell in cell_names and any(k.lower() in nmtxt.lower() for k in kws):
                hit = cell; break
        if hit:
            u2 = dict(u); u2.update({"股名": nmtxt, "细分解析来源": "业务词(股名·JA3扩unmapped)",
                                     "market_val": per.get(u["code"], {}).get("market_val"),
                                     "avg_turnover_60d_usd": per.get(u["code"], {}).get("avg_turnover_60d_usd"),
                                     "financial_quality_score": scores.get(u["code"], {}).get("financial_quality_score")})
            pool.setdefault(hit, []).append(u2); ja3_resolved += 1
        else:
            still_unmapped.append(u)
    unmapped = still_unmapped
    # 4) GA3-3 校验:每个激活格 代表标的(非KR) 是否在归类结果里
    audit = {"_说明": "★GA3-3 承接节点代表标的降级为校验用。核对归类结果是否含代表标的·不含→归类可能有问题(报出·不静默)。",
             "date": dh, "逐格": [], "★韩股未接(GA3-4)": []}
    for cell in [b for b in cells_all if b.get("激活") is True]:
        nm = (cell.get("格名") or cell.get("板块")); reps = cell.get("承接节点", cell.get("代表标的", [])) or []  # ★P0-3:兼容格名
        got_codes = [x["code"] for x in pool.get(nm, [])]
        rep_check = []
        for r in reps:
            if str(r).endswith(".KS") or str(r).endswith(".KQ"):
                audit["★韩股未接(GA3-4)"].append({"格": nm, "代表": r, "说明": "韩股universe未接(first_scan2只扫US+JP)·无法进池·不用定向2只冒充"})
                continue
            # 规范化 SNDK→US.SNDK 等(代表可能无前缀)
            cand_forms = {r, "US." + r, "JP." + r} if "." not in r else {r}
            hit = any(f in got_codes for f in cand_forms)
            rep_check.append({"代表标的": r, "在归类结果": hit})
        audit["逐格"].append({"激活格": nm, "归类到几只": len(got_codes),
                            "代表标的校验": rep_check,
                            "★校验": ("通过(代表标的都在)" if rep_check and all(x["在归类结果"] for x in rep_check)
                                     else ("★不通过·代表标的不在归类结果→行业分类粒度/映射有问题·报出" if rep_check else "无非韩代表标的可校验"))})
    n_classified = len(set(x["code"] for lst in pool.values() for x in lst))
    audit["IA1_半导体细分业务词解析"] = {"大类不可分总数": len(semi_unclassified),
                                 "★业务词解析出细分": fine_resolved,
                                 "仍不可分(sector_fine_unresolved)": len(fine_unresolved),
                                 "unresolved样本": fine_unresolved[:15]}
    audit["HA1-3_完全未归类(sector_unmapped·无板块或板块无激活格关键词)"] = {"数": len(unmapped), "样本": [s["code"] for s in unmapped[:25]]}
    audit["板块源"] = plate_src
    audit["★HA1-4校验汇总"] = {"通过格": [r["激活格"] for r in audit["逐格"] if "通过" in r["★校验"]],
                          "不通过格": [r["激活格"] for r in audit["逐格"] if "不通过" in r["★校验"]]}
    # ★轮92 KA2-2:现有20持仓不进【新候选池】(走⑥持仓层)·除组内换仓对照(标 role=换仓对照)
    prod = _rj(ROOT / "data/reports" / f"production_{dc}.json")
    held = set(str(h.get("symbol")) for h in prod.get("holdings", []))
    # 5) candidate_pool(★由扫描产出·非承接节点·去重同格·排除持仓)
    cands = []
    n_excl_held = 0
    # ★★★候选放行只从【核心篮子】走(拆格裁定08-07):有白名单核心的格·邻接股永不自动进候选。
    _wl_c = _rj(ROOT / "data/market/sector_core_whitelist.json")
    _core_no = {}
    import re as _re3
    for _k, _v in _wl_c.items():
        if isinstance(_v, dict) and _v.get("核心"):
            _mo = _re3.search(r"(\d+)", str(_k))
            if _mo:
                _core_no[int(_mo.group(1))] = set(_v.get("核心", []))
    for nm, lst in pool.items():
        cell = next((b for b in cells_all if (b.get("格名") or b.get("板块")) == nm), {})  # ★P0-3:兼容格名
        _cell_core = _core_no.get(cell.get("格号"))   # 该格白名单核心(有则邻接不放行)
        seen = set()
        for x in lst:
            if x["code"] in seen:
                continue
            seen.add(x["code"])
            if _cell_core is not None and x["code"] not in _cell_core:
                continue   # ★★★该格有白名单核心·此股属邻接→不自动进候选(拆格裁定08-07·邻接只观察不放行)
            if x["code"] in held:
                n_excl_held += 1
                continue   # 持仓不进新候选池(KA2-2·组内换仓对照另行·本轮无换仓需求)
            cands.append({"sector_cell": nm, "group": cell.get("群"), "driver_group": cell.get("驱动类型"),
                          "code": x["code"], "板块列表": x.get("板块列表"),
                          "归类置信度": x.get("归类置信度", "高(专属词命中)"),
                          "market_val": x["market_val"], "avg_turnover_60d_usd": x["avg_turnover_60d_usd"],
                          "financial_quality_score": x["financial_quality_score"],
                          "fair_value": {"value": 0, "method": "", "as_of": "", "confidence": "C", "hardcoded": False},
                          "note": "★scan产出(universe硬门槛入围→全板块列表归类)·非承接节点·待第2/3关(估值引擎)"})
    # ★轮90 IA2:简易估值(snapshot EPS/PE·板块中位PE作锚)→fair_value·★B/C级不标A·只供S1排序初筛(IA2-3)
    snap, _ = _fetch_snapshot([c["code"] for c in cands], dc)
    # 每格中位PE(有正PE者)
    from statistics import median
    bycell_pe = {}
    for c in cands:
        pe = (snap.get(c["code"], {}) or {}).get("pe_ttm")
        if isinstance(pe, (int, float)) and 0 < pe < 200:
            bycell_pe.setdefault(c["sector_cell"], []).append(pe)
    cell_med_pe = {k: median(v) for k, v in bycell_pe.items() if v}
    n_valued = 0; n_lowconf_skip = 0
    for c in cands:
        s = snap.get(c["code"], {}) or {}
        eps = s.get("eps"); px = s.get("price"); med = cell_med_pe.get(c["sector_cell"])
        # ★轮93 LA1-1:归类置信度【低】不出简易估值(标pending_valuation·不参与S1排序·防归类错→假高上行)
        if str(c.get("归类置信度", "")).startswith("低"):
            c["fair_value"] = {"value": 0, "method": "★归类置信度低→不出简易估值(LA1-1·防归类错传导成假高上行)", "confidence": "C", "hardcoded": False}
            c["price"] = px if isinstance(px, (int, float)) else None; n_lowconf_skip += 1
            continue
        if isinstance(eps, (int, float)) and eps > 0 and med and isinstance(px, (int, float)) and px > 0:
            fv = round(eps * med, 4)
            c["fair_value"] = {"value": fv, "method": "简易:EPS×板块中位PE(%.1f)" % med, "as_of": dh,
                               "confidence": "B", "hardcoded": False,
                               "★用途限定": "仅供S1排序初筛·不得进产品当买卖依据(IA2-3)·进产品须走完整估值"}
            c["price"] = px; n_valued += 1
        else:
            c["fair_value"] = {"value": 0, "method": "简易估值算不出(EPS≤0或无板块中位PE)", "confidence": "C", "hardcoded": False}
    cov = round(n_classified / len(scores) * 100, 1) if scores else 0
    out = {
        "_说明": "★轮88建/轮89 HA1改全板块列表:候选池【由全市场扫描产出】(universe→硬门槛入围→按激活板块【全板块列表】归类)·★不从承接节点取。",
        "date": dh, "produced": True, "candidates": cands, "板块源": plate_src,
        "来源链": "全市场扫描(universe US+JP→市值/成交额/OCF硬门槛→入围) → 全板块列表(get_owner_plate多板块) → 映射表归激活格",
        "激活格数": len(active_names), "入围总数": len(scores),
        "★★★第1关三分(裁定《待判≠淘汰》08-07)": {
            "①进候选池(归类到true格·走第2-5关)": n_classified,
            "②淘汰·第1关一票否决(归类到false格·已查证不活跃)": len(eliminated_false),
            "③待激活观察池(归类到待判格·★不淘汰·★不进候选)": len(pending_pool),
            "另-待归类池(归类失败·无任何格·不淘汰)": len(unmapped) + len(fine_unresolved),
            "另-排除·行业冲突(商社/银行落半导体AI格·待复核)": len(conflicts),
            "★合计校验(应=入围)": n_classified + len(eliminated_false) + len(pending_pool) + len(unmapped) + len(fine_unresolved) + len(conflicts),
            "入围总数": len(scores),
            "★格状态分布": {"true激活": len(active_names), "false不活跃": len(false_names), "待判": len(pending_names)},
            "★板块名全被噪音过滤光(计入待归类·彻底没信息)": len(all_noise_filtered),
        },
        "★核心口径": "sector_core_whitelist.json v2 · 状态=GPT V7 未通过 · 仅限制不放宽(邻接不进候选)",
        "归类到激活格的入围数": n_classified, "归类覆盖率pct": cov,
        "归类进候选池(含多格)": len(cands),
        "★IA1半导体细分:业务词解析出": fine_resolved, "仍不可分(sector_fine_unresolved)": len(fine_unresolved),
        "★JA3业务词扩unmapped补归类数": ja3_resolved,
        "★KA2-2排除的现有持仓数(走⑥持仓层)": n_excl_held,
        "★LA1-3 sector_conflict排除数(商社/银行/有色金属落半导体/AI格)": len(conflicts),
        "★LA1-3冲突样本": [{"code": x["code"], "冲突行业": x.get("冲突行业"), "误落格": x.get("误落格")} for x in conflicts[:10]],
        "★LA1-1 归类置信度低→不出简易估值数": n_lowconf_skip,
        "★IA2简易估值(B级·EPS×板块中位PE·仅供S1排序)算出fair_value数": n_valued,
        "完全未归类数(sector_unmapped)": len(unmapped),
        "★HA4-1韩股": "universe未接(只扫US+JP)·三星005930.KS/SK海力士000660.KS无法进池·不冒充",
        "★HA4-2美股": "US basicinfo超时→美股入围走市值(SimpleFilter)路径·非全basicinfo枚举·覆盖以过市值门槛者为准(全集完整性受basicinfo超时限制·如实标)",
    }
    # ★待归类池(③归类失败·不淘汰)明细 + 按板块名聚类前20(给董事长复核:关键词漏 or 18格没覆盖的新方向)
    from collections import Counter as _Ct
    _uncls = unmapped + fine_unresolved
    _clu = _Ct()
    for u in _uncls:
        for pn in (u.get("板块列表") or u.get("raw_板块列表") or []):
            _clu[str(pn)] += 1
    out["★待归类池明细(③·不淘汰·待Opus复核)"] = _uncls
    out["★待归类池前20类板块名(按频次·给Opus复核)"] = _clu.most_common(20)
    out["★淘汰明细(②·归类到false格·已查证不活跃)"] = eliminated_false
    # ★★★待激活观察池:按格分组·按挡住数降序(每格待判天数=激活清单无判定日字段→None·如实标需补)
    _by_cell = {}
    for r in pending_pool:
        for g in (r.get("归类到(待判格)") or []):
            _by_cell.setdefault(g, []).append({"symbol": r["code"], "financial_quality_score": r.get("financial_quality_score"), "命中板块名": r.get("板块列表")})
    _groups = sorted(_by_cell.items(), key=lambda kv: -len(kv[1]))
    out["★★★待激活观察池(按格分组·降序·不淘汰·不进候选·出口只有格判true/false)"] = [
        {"格号": _cell_no.get(g), "格名": g, "群": _cell_group.get(g), "格状态": "待判",
         "挡住只数": len(lst), "已待判天数": None, "★天数说明": "激活清单无【每格最近判定日】字段→算不出·需董事长补该字段",
         "池内标的": lst} for g, lst in _groups]
    out["★观察池无个股级出口(总则一)"] = "★候选池 candidates 只从 pool(true格)构建·pending_pool 写入独立文件 pending_activation·【无任何代码路径】把观察池标的写进 candidates/第2-5关/决策清单——即使 financial_quality_score 再高也不单独捞出(自下而上选股·总则第一条禁)。出口只有该格被判 true/false。"
    return out, audit


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out, audit = build(a.date)
    D = ROOT / "data" / "opportunity"; D.mkdir(parents=True, exist_ok=True)
    p = D / f"candidate_pool_{a.date[:4]}-{a.date[4:6]}-{a.date[6:]}.json" if "-" not in a.date else D / f"candidate_pool_{a.date}.json"
    dh = a.date if "-" in a.date else f"{a.date[:4]}-{a.date[4:6]}-{a.date[6:]}"
    p = D / f"candidate_pool_{dh}.json"
    # ★P0-4:⑥e3(全市场扫描)只在【真有产出】才覆盖 candidate_pool_{date}.json;scan空→写诊断文件·★不抹掉⑥e2已产出结果。
    if out.get("produced") or out.get("candidates"):
        p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        p = D / f"candidate_pool_scan_{dh}.json"
        p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("  ★P0-4:scan未产出(produced=False)→写 %s·未覆盖 candidate_pool_%s.json(保留⑥e2产出)" % (p.name, dh))
    if audit:
        (D / f"classify_audit_{a.date.replace('-','')}.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # ★裁定《归类失败≠淘汰》:待归类池(③·不淘汰)落盘 data/screen/unclassified_{date}.json(给Opus复核)
    _ucls = out.get("★待归类池明细(③·不淘汰·待Opus复核)", []) or []
    _sd = a.date.replace("-", "")
    (ROOT / "data" / "screen" / f"unclassified_{_sd}.json").write_text(
        json.dumps({"date": dh, "_说明": "★归类失败(匹配不上任何格)=待归类·不淘汰(裁定08-07)。给Opus复核:关键词漏 or 18格没覆盖的新方向。",
                    "数": len(_ucls), "前20类板块名(按频次)": out.get("★待归类池前20类板块名(按频次·给Opus复核)", []),
                    "明细": _ucls}, ensure_ascii=False, indent=2), encoding="utf-8")
    # ★★★裁定《待判≠淘汰》:待激活观察池落盘 data/opportunity/pending_activation_{date}.json(按格分组降序·★不淘汰·★不进候选·无个股级出口)
    _pend = out.get("★★★待激活观察池(按格分组·降序·不淘汰·不进候选·出口只有格判true/false)", []) or []
    (ROOT / "data" / "opportunity" / f"pending_activation_{dh}.json").write_text(
        json.dumps({"date": dh,
                    "_说明": "★待激活观察池:归类到【待判格】的入围股。格待判(证据不足)≠格不活跃(false)。★这些股不淘汰·不进候选·不进第2-5关·不进决策清单/动作卡。出口只有该格被判 true(→候选)/false(→淘汰)。★不得因财务分高单独捞出(自下而上选股·总则第一条禁)。",
                    "★无个股级出口": out.get("★观察池无个股级出口(总则一)"),
                    "格状态分布": (out.get("★★★第1关三分(裁定《待判≠淘汰》08-07)", {}) or {}).get("★格状态分布"),
                    "观察池总只数": sum(g["挡住只数"] for g in _pend),
                    "按格分组(降序)": _pend}, ensure_ascii=False, indent=2), encoding="utf-8")
    b = p.read_bytes(); json.loads(b.decode())
    print("[universe_to_candidate_pool] %s · produced=%s · 板块源=%s" % (a.date, out.get("produced"), out.get("板块源")))
    print("  入围%s → 归类到激活格 %s 只(覆盖率%s%%·上轮7)·候选(含多格)%s · ★半导体细分业务词解析出%s·仍不可分%s · 完全未归类%s · 乱码%d" % (
        out.get("入围总数"), out.get("归类到激活格的入围数"), out.get("归类覆盖率pct"),
        out.get("归类进候选池(含多格)"), out.get("★IA1半导体细分:业务词解析出"),
        out.get("仍不可分(sector_fine_unresolved)"), out.get("完全未归类数(sector_unmapped)"), b.count(b"\xef\xbf\xbd")))
    if not out.get("produced"):
        print("  ★" + out.get("reason", "")); return 0
    for row in audit.get("逐格", []):
        print("  格[%s] 归类%d只 · %s" % (row["激活格"][:16], row["归类到几只"], str(row.get("★校验", ""))[:44]))
    print("  ★HA1-4校验 通过格:", audit.get("★HA1-4校验汇总", {}).get("通过格"))
    print("  ★HA1-4校验 不通过格:", audit.get("★HA1-4校验汇总", {}).get("不通过格"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
