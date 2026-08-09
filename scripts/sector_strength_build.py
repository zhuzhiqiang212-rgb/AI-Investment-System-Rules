# -*- coding: utf-8 -*-
"""板块趋势/轮动最小可跑版(裁定08-07·解冻轮动模块)。
★用每格【真实成分股篮子】(今天归类产出)算板块强度·不用单只代表股(IBKR事故根源)。
成分股源:pending_activation(待判格) + candidate_pool(true格)。
K线:OpenD history_kline K_DAY 60交易日(退避重试·分批)·benchmark ^GSPC/^N225 用 Yahoo chart。
输出:每格 5/20/60日收益率 + 相对强度(vs大盘) + 轮动方向。★只产事实·不判激活(约束2)。"""
import sys, os, json, time, urllib.request
from pathlib import Path
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _yahoo_closes(sym, rng="6mo"):
    """Yahoo chart→收盘价list(最近在末)。失败→None。"""
    try:
        req = urllib.request.Request("https://query1.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=1d" % (sym, rng),
                                     headers={"User-Agent": "Mozilla/5.0"})
        j = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())
        q = j["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        return [x for x in q if x is not None]
    except Exception:
        return None


def _ret(closes, n):
    """n个交易日收益率:close[-1]/close[-1-n]-1。不足→None。"""
    if not closes or len(closes) < n + 1:
        return None
    a, b = closes[-1], closes[-1 - n]
    if not b:
        return None
    return round((a / b - 1.0) * 100, 3)


def build(date, enable_cell19=False):   # ★C3:格19默认不注入(未经GPT批准启用·须显式--enable-cell19开)
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    pa = _rj(ROOT / "data/opportunity" / f"pending_activation_{dh}.json")
    cp = _rj(ROOT / "data/opportunity" / f"candidate_pool_{dh}.json")
    # 1) 每格成分股(格号/格名/群/状态/成分股list)
    cells = {}
    for g in pa.get("按格分组(降序)", []):
        cells[g["格名"]] = {"格号": g["格号"], "格名": g["格名"], "群": g["群"], "状态": "待判",
                           "成分股": [s["symbol"] for s in g.get("池内标的", [])]}
    # true格(AI存储):candidate_pool候选(含被排除持仓→补回·成分股口径含持仓)
    _true = {}
    for c in cp.get("candidates", []):
        _sym = c.get("code") or c.get("ticker")   # ★修:candidate_pool 用 ticker 键(非 code)·防 KeyError 崩整轮
        _cell = c.get("sector_cell")
        if _sym and _cell:
            _true.setdefault(_cell, set()).add(_sym)
    # 补回被KA2-2排除的持仓(成分股口径算强度须含持仓·如闪迪)
    for h in _rj(ROOT / "data/reports" / f"production_{dc}.json").get("holdings", []):
        pass  # 持仓归属格未在candidate_pool记·此处只用candidate候选(如实·持仓归属另需归类·最小版不补)
    for cell, codes in _true.items():
        cells[cell] = {"格号": None, "格名": cell, "群": None, "状态": "true", "成分股": sorted(codes)}
    # 补格号/群(从激活清单)
    import glob as _g
    # ★★★C1(EA4/§5.4):禁 sorted(glob)[-1](实测会选中未终验的rejudge稿)。改:排除TEMPLATE + 要求「★可用于生产」is True + data_date≤当日 + 最新·无则据实空。
    _cf = []
    for _f in _g.glob(str(ROOT / "data/market/sector_activation_*.json")):
        if "TEMPLATE" in Path(_f).name.upper():
            continue
        _fj = _rj(_f)
        if _fj.get("★可用于生产") is not True:
            continue
        _dt = _fj.get("data_date", "")
        if _dt and _dt <= dh:
            _cf.append((_dt, _f))
    _cf.sort()
    act = _rj(_cf[-1][1]) if _cf else {}
    _act_file = Path(_cf[-1][1]).name if _cf else "★无可用激活清单(可用于生产=True)"
    meta = {(b.get("格名") or b.get("板块")): b for b in act.get("板块", [])}
    for nm, cell in cells.items():
        m = meta.get(nm, {})
        if cell["格号"] is None:
            cell["格号"] = m.get("格号")
        cell["群"] = cell["群"] or m.get("群")

    # ★★★白名单核心口径(拆格v3落入Current):有核心的格【只用核心篮子】算强度·邻接单列不参与。
    #   ★★轮330修:必须在拉K线【之前】做完核心过滤+格18/格19注入·否则核心/新格成分股不进 all_syms·K线取不到(原在拉K线后→格19核心K线0)。
    import re as _re2
    _wl = _rj(ROOT / "data/market/sector_core_whitelist.json")
    _core_by_no = {}
    for _k, _v in _wl.items():
        if isinstance(_v, dict) and _v.get("核心"):
            _mo = _re2.search(r"(\d+)", str(_k))
            if _mo:
                _core_by_no[int(_mo.group(1))] = {"核心": set(_v.get("核心", [])),
                                                   "邻接": set(_v.get("邻接", [])), "格名": _v.get("格名", str(_k))}
    # 现有格(pending来的):过滤到核心·把非核心成分并入邻接单列
    for _nm, _cell in cells.items():
        _no = _cell.get("格号")
        if _no in _core_by_no:
            _core = _core_by_no[_no]["核心"]
            _cell["★邻接(不参与强度/候选)"] = sorted(set(_cell.get("★邻接(不参与强度/候选)", []))
                                                    | set(s for s in _cell["成分股"] if s not in _core)
                                                    | _core_by_no[_no]["邻接"])
            _cell["成分股"] = [s for s in _cell["成分股"] if s in _core]
            _cell["★口径"] = "只核心篮子(白名单v3·邻接不参与)"
    # ★注入白名单格(格18/格19)——pending未带则从白名单核心建·保证格18/格19恒显示(A4:格19不得从产品消失)。
    _existing_nos = {c.get("格号") for c in cells.values()}
    for _no, _info in sorted(_core_by_no.items()):
        if _no in _existing_nos or not _info["核心"]:
            continue
        if _no == 19 and not enable_cell19:            # ★格19须 --enable-cell19(GPT V7 2026-08-09 已批准·生产开)
            continue
        cells["%s(格%d)" % (_info["格名"], _no)] = {
            "格号": _no, "格名": _info["格名"], "群": ("进攻" if _no == 19 else "防御"), "状态": "待判",
            "成分股": sorted(_info["核心"]), "★邻接(不参与强度/候选)": sorted(_info["邻接"]),
            "★口径": "只核心篮子(白名单v3·邻接不参与)"}

    # 2) 拉K线(OpenD K_DAY·退避重试·分批)。★A2:邻接也拉K线(供单列表现+敏感性·仍不进核心平均)。
    all_syms = sorted(set(
        [s for cell in cells.values() for s in cell["成分股"]]
        + [s for cell in cells.values() for s in cell.get("★邻接(不参与强度/候选)", [])]))
    closes = {}; k_fail = {}
    start = (datetime.now(JST).date() - timedelta(days=130)).strftime("%Y-%m-%d")
    try:
        import futu as ft
        ctx = ft.OpenQuoteContext(host="127.0.0.1", port=11111)
        try:
            for i, c in enumerate(all_syms):
                got = False
                for att in range(4):
                    try:
                        ret, kl, _ = ctx.request_history_kline(c, start=start, ktype=ft.KLType.K_DAY, autype=ft.AuType.QFQ, max_count=200)
                        if ret == ft.RET_OK:
                            recs = kl["close"].tolist() if hasattr(kl, "__getitem__") else []
                            cl = [float(x) for x in recs if x is not None]
                            if cl:
                                closes[c] = cl; got = True
                            break
                        er = str(kl)
                        if any(k in er for k in ("30秒", "频率", "请求失败", "限", "10次", "太高")) and att < 3:
                            time.sleep(6.0 * (att + 1)); continue
                        k_fail[c] = er[:60]; break
                    except Exception as e:
                        k_fail[c] = "异常:%s" % type(e).__name__
                        time.sleep(3.0)
                if not got and c not in k_fail:
                    k_fail[c] = "K_DAY无数据"
                time.sleep(0.35)
        finally:
            ctx.close()
    except Exception as e:
        return {"date": dh, "produced": False, "reason": "OpenD不可用:%s" % type(e).__name__, "K线失败": len(all_syms)}, {}
    # benchmark(Yahoo)
    bench = {"^GSPC": _yahoo_closes("^GSPC"), "^N225": _yahoo_closes("^N225")}
    bret = {k: {n: _ret(v, n) for n in (5, 20, 60)} for k, v in bench.items() if v}

    # 3/4) 每格算收益率+相对强度+轮动方向
    def _mk(sym):  # 该股基准:US→^GSPC · JP→^N225
        return "^N225" if str(sym).startswith("JP.") else "^GSPC"
    rows = []
    for nm, cell in cells.items():
        syms = cell["成分股"]; got = [s for s in syms if s in closes]; drop = [s for s in syms if s not in closes]
        per_stock = []
        rr = {5: [], 20: [], 60: []}; rs = {5: [], 20: [], 60: []}
        contrib = {}
        for s in got:
            r = {n: _ret(closes[s], n) for n in (5, 20, 60)}
            bk = _mk(s); cl = closes[s]
            _ep = {n: ((cl[-1 - n], cl[-1]) if len(cl) >= n + 1 else (None, None)) for n in (5, 20, 60)}
            per_stock.append({"symbol": s, "5日%": r[5], "20日%": r[20], "60日%": r[60],
                              "起终收盘价": {("%d日" % n): {"起": _ep[n][0], "终": _ep[n][1]} for n in (5, 20, 60)}})
            contrib[s] = {}
            for n in (5, 20, 60):
                b = bret.get(bk, {}).get(n)
                if r[n] is not None:
                    rr[n].append(r[n])
                    if b is not None:
                        rs[n].append((s, r[n] - b))
        # ★C2:分周期统计有效样本·某周期<3只【只该周期】不出数·其余照常(不因缺60日剔5/20日)。
        n_valid = {n: len(rs[n]) for n in (5, 20, 60)}
        miss_by_n = {n: [s for s in got if _ret(closes[s], n) is None] for n in (5, 20, 60)}
        rs_g = {n: (round(sum(v for _, v in rs[n]) / len(rs[n]), 3) if len(rs[n]) >= 3 else None) for n in (5, 20, 60)}
        ret_g = {n: (round(sum(rr[n]) / len(rr[n]), 3) if len(rr[n]) >= 3 else None) for n in (5, 20, 60)}
        # ★R3⑩:每只贡献度(=个股相对强度/该周期有效样本数·等权)+还原校验(合计应=格级)
        for s in got:
            for n in (5, 20, 60):
                _rv = next((v for ss, v in rs[n] if ss == s), None)
                contrib[s][n] = round(_rv / n_valid[n], 4) if (_rv is not None and n_valid[n]) else None
        recon = {}
        for n in (5, 20, 60):
            if rs_g[n] is not None:
                _sum = round(sum(contrib[s][n] for s in got if contrib[s][n] is not None), 3)
                recon["%d日" % n] = {"贡献合计": _sum, "格级": rs_g[n], "差": round(_sum - rs_g[n], 4)}
        # ★A2:邻接单列表现(不进核心平均)+短历史/邻接敏感性(含它vs不含它·仅敏感性·非第二正式答案)
        adj_syms = cell.get("★邻接(不参与强度/候选)", []) or []
        adj_perf = []; adj_sens = {}
        for a in adj_syms:
            if a not in closes:
                adj_perf.append({"symbol": a, "note": "K线未取到·单列略"}); continue
            bk = _mk(a); acl = closes[a]
            a_rs = {n: (round(_ret(acl, n) - bret.get(bk, {}).get(n), 3)
                        if (_ret(acl, n) is not None and bret.get(bk, {}).get(n) is not None) else None)
                    for n in (5, 20, 60)}
            adj_perf.append({"symbol": a, "5日%": _ret(acl, 5), "20日%": _ret(acl, 20), "60日%": _ret(acl, 60),
                             "5日相对强度": a_rs[5], "20日相对强度": a_rs[20], "60日相对强度": a_rs[60],
                             "★口径": "邻接·单列·不进核心平均(A2)"})
            sens = {}
            for n in (5, 20, 60):
                if rs_g[n] is not None and a_rs[n] is not None:
                    incl = round((sum(v for _, v in rs[n]) + a_rs[n]) / (n_valid[n] + 1), 3)
                    sens["%d日" % n] = {"含它": incl, "不含它(正式)": rs_g[n], "它令格级变动": round(incl - rs_g[n], 3)}
                else:
                    sens["%d日" % n] = {"含它": None, "不含它(正式)": rs_g[n], "它令格级变动": None,
                                        "注": "该周期核心样本不足或该股无此周期历史·不出敏感性"}
            adj_sens[a] = sens
        rot_5_20 = round(rs_g[5] - rs_g[20], 3) if (rs_g[5] is not None and rs_g[20] is not None) else None
        rot_20_60 = round(rs_g[20] - rs_g[60], 3) if (rs_g[20] is not None and rs_g[60] is not None) else None
        rows.append({
            "格号": cell["格号"], "格名": nm, "群": cell["群"], "当前激活状态": cell["状态"],
            "成分股数": len(syms), "K线取到数": len(got), "剔除数": len(drop),
            "有效样本数": {("%d日" % n): n_valid[n] for n in (5, 20, 60)},
            "该周期缺数的成分股": {("%d日" % n): miss_by_n[n] for n in (5, 20, 60) if miss_by_n[n]},
            "★口径": cell.get("★口径", "全成分等权"),
            "5日收益率%": ret_g[5], "20日收益率%": ret_g[20], "60日收益率%": ret_g[60],
            "5日相对强度": rs_g[5], "20日相对强度": rs_g[20], "60日相对强度": rs_g[60],
            "轮动方向(5-20·短期获/失动能)": rot_5_20,
            "轮动方向(20-60·中期)": rot_20_60,
            "★每只贡献度(等权·还原格级)": contrib,
            "★还原校验(贡献合计vs格级·差应=0)": recon,
            "★邻接(不参与)": cell.get("★邻接(不参与强度/候选)", []),
            "★邻接单列表现(A2·不进核心平均)": adj_perf,
            "★短历史/邻接敏感性(含它vs不含它·仅敏感性·非第二正式答案)": adj_sens,
            "剔除股(K线未取到)": drop,
            "成分股逐只涨跌": per_stock,
        })
    # 按5日相对强度降序(None沉底)
    rows.sort(key=lambda x: (x["5日相对强度"] is None, -(x["5日相对强度"] or 0)))
    # ★甲1(轮331):A4文案用【当日实算】格19 60日强度填占位符{r60}·消灭与固定常量+33.84打架(L5)。
    _g19row = next((r for r in rows if r.get("格号") == 19), None)
    _r60 = (_g19row or {}).get("60日相对强度")
    _r60s = ("%+.2f" % _r60) if isinstance(_r60, (int, float)) else "N/A(样本不足)"
    _a4_tmpl = (_wl.get("19", {}) or {}).get("★A4文案模板(GPT句式·数字占位·机器填当日值)", "")
    _a4_text = _a4_tmpl.replace("{r60}", _r60s) if _a4_tmpl else ""
    out = {
        "date": dh, "produced": True, "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
        "_说明": "★板块趋势/轮动最小可跑版。★用每格真实成分股篮子(非单只代表股·IBKR事故教训)算相对强度+轮动方向。★只产【事实】·不判激活(约束2:是否激活是董事长判断·本文件无任何『建议激活』表述)。",
        "★核心口径": "sector_core_whitelist.json %s · 状态=%s" % (
            _wl.get("version", "?"),
            (_wl.get("★★★本白名单当前状态", {}) or {}).get("GPT V7 复验结论", "?")),
        "★格19两字段(A3)": {
            "cell19_enabled": bool((_wl.get("19", {}) or {}).get("cell19_enabled")),
            "cell19_activated": bool((_wl.get("19", {}) or {}).get("cell19_activated")),
            "说明": "enabled=已启用(不从产品消失)·activated=激活(=false·强趋势观察·驱动待核·★不得由Code依价格改true)",
            "★A4固定文案": _a4_text,          # ★甲1:模板{r60}已用当日实算值填(不再是写死+33.84)
            "★A4文案_60日实算值": _r60s,
        },
        "★激活清单来源(C1)": _act_file,
        "★计算元数据(R3·GPT必核)": {
            "基准代码": {"美股": "^GSPC(标普500)", "日股": "^N225(日经225)"},
            "基准各周期起终值": {"^GSPC": bret.get("^GSPC"), "^N225": bret.get("^N225")},
            "复权方式": "ft.AuType.QFQ(前复权·OpenD request_history_kline K_DAY)",
            "数据截止": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST") + "(日股08-07收盘/美股08-06收盘)",
            "汇率是否进入计算": "★否。日股与^N225均为日元、美股与^GSPC均为美元·相对强度在各自币种内算·汇率不进入。",
            "权重": "等权(每只成分等权·相对强度=个股相对强度均值)",
            "缺失值处理": "跳过·不补值·不插值·不拿母公司历史顶替(某周期缺→只该周期不计入·见各格『有效样本数』)",
            "格19启用(C3)": ("已启用(--enable-cell19)" if enable_cell19 else "★默认关闭·输出不含格19(未经GPT批准)"),
        },
        "★口径": "收益率=成分股等权(剔除缺K线·分周期统计);相对强度=成分股(个股−其市场基准[US→^GSPC/JP→^N225])均值;轮动方向=短期相对强度−长期相对强度。60日回溯。",
        "大盘基准(Yahoo)": {"标普500^GSPC": bret.get("^GSPC"), "日经225^N225": bret.get("^N225")},
        "K线": {"拉取": len(all_syms), "成功": len(closes), "失败": len(k_fail), "失败明细": k_fail},
        "18格强度(按5日相对强度降序)": rows,
    }
    return out, {}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True)
    ap.add_argument("--enable-cell19", action="store_true", default=False)   # ★C3:默认不启用格19
    a = ap.parse_args()
    t0 = time.time()
    out, _ = build(a.date, enable_cell19=a.enable_cell19)
    dh = a.date if "-" in a.date else "%s-%s-%s" % (a.date[:4], a.date[4:6], a.date[6:])
    p = ROOT / "data/market" / f"sector_strength_{dh}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    # ★缺件报(裁定08-07):未产出→写「[板块强度] 今日未产出·原因X」到缺件文件
    if not out.get("produced"):
        miss = ROOT / "00_请先看这里" / "★★今日缺件_卡在谁.txt"
        try:
            _ln = miss.read_text(encoding="utf-8").splitlines() if miss.exists() else []
        except Exception:
            _ln = []
        _ln.append("[板块强度] 今日未产出·原因:%s" % (out.get("reason") or "K线取到%s/%s(部分失败)" % (out.get("K线", {}).get("成功"), out.get("K线", {}).get("拉取"))))
        miss.write_text("\n".join(_ln) + "\n", encoding="utf-8")
    b = p.read_bytes()
    print("[sector_strength] %s · produced=%s · K线成功%s/%s · 耗时%.0fs · 乱码%d" % (
        a.date, out.get("produced"), out.get("K线", {}).get("成功"), out.get("K线", {}).get("拉取"),
        time.time() - t0, b.count(b"\xef\xbf\xbd")))
    return 0


if __name__ == "__main__":
    # ★轮337 丙1:接 exit_guard——退出0却没产出 sector_strength_{date}.json → 强制非0。
    import argparse as _ap
    _p = _ap.ArgumentParser(); _p.add_argument("--date", default=""); _p.add_argument("--enable-cell19", action="store_true")
    _dd = (_p.parse_known_args()[0].date or "")
    _dh = _dd if "-" in _dd else ("%s-%s-%s" % (_dd[:4], _dd[4:6], _dd[6:]) if len(_dd) == 8 else _dd)
    from exit_guard import guarded
    guarded(main, produced=(lambda: (ROOT / "data" / "market" / f"sector_strength_{_dh}.json").exists()) if _dh else None)
