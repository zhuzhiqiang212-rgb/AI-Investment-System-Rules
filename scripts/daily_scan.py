# -*- coding: utf-8 -*-
"""A1·生产链第0步(critical):扫当日数据。1当日20只价(OpenD) 2涨跌>5%榜 3当日新闻 4Drive新增(按修改时间) 5USDJPY。
硬闸:1/2/3/4任一缺失→退出码≠0(整轮停·不进渲染)。输出 data/market/daily_scan_{date}.json。
Code 只取数不做投资判断。"""
import sys, os, json, time, pathlib, argparse
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9))
ROOT = pathlib.Path(__file__).resolve().parent.parent
SCR = ROOT / "scripts"
sys.path.insert(0, str(SCR))

def now_jst():
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

def load_codes(date):
    p = ROOT / "data" / "accounts" / f"holdings_true_{date}.json"
    if not p.exists():
        # step0在①持仓之前跑·当日持仓表尚未生成→回退到最近一份(20只代码稳定·仅用于取价代码列表)
        import glob as _g
        cands = sorted(_g.glob(str(ROOT / "data" / "accounts" / "holdings_true_*.json")))
        if not cands:
            return []
        p = pathlib.Path(cands[-1])
    d = json.loads(p.read_text(encoding="utf-8"))
    hs = d.get("holdings", d if isinstance(d, list) else [])
    out = []
    for x in hs:
        code = x.get("symbol") or x.get("code")
        qty = x.get("total_quantity") or x.get("quantity")
        nm = x.get("name") or ""
        if code:
            out.append({"code": code, "qty": float(qty) if qty else None, "name": nm})
    return out

def scan_prices(codes):
    """OpenD 快照:last_price/prev_close_price/update_time。返回(rows, ok, err)。"""
    try:
        from realtime_price import connect_quote_context
        from futu import RET_OK
    except Exception as e:
        return {}, False, "futu 导入失败: %s" % e
    ctx, attempts = connect_quote_context(max_retries=3, wait_seconds=3)
    if ctx is None:
        return {}, False, "OpenD 连接失败: %s" % attempts
    rows = {}
    try:
        cl = [c["code"] for c in codes]
        # 分批快照(每批≤30·避配额)
        for i in range(0, len(cl), 20):
            ret, data = ctx.get_market_snapshot(cl[i:i + 20])
            if ret != RET_OK:
                return rows, False, "get_market_snapshot 失败: %s" % str(data)[:120]
            recs = data.to_dict("records") if hasattr(data, "to_dict") else []
            for r in recs:
                rows[r.get("code")] = {
                    "last_price": r.get("last_price"), "prev_close_price": r.get("prev_close_price"),
                    "open_price": r.get("open_price"), "high_price": r.get("high_price"),
                    "low_price": r.get("low_price"), "update_time": r.get("update_time"),
                    "sec_status": r.get("sec_status"),
                }
            time.sleep(1)
    except Exception as e:
        return rows, False, "快照异常: %s" % e
    finally:
        try: ctx.close()
        except Exception: pass
    return rows, True, None

def build(date):
    codes = load_codes(date)
    scan = {"_说明": "A1第0步·当日数据扫描·Code只取数不做判断", "date": date, "scanned_at": now_jst(),
            "items": {}, "gate": {}}
    # 1+2 当日价 + 涨跌>5%榜
    rows, ok, err = scan_prices(codes)
    quotes = []
    movers = []
    for c in codes:
        q = rows.get(c["code"], {})
        lp, pc = q.get("last_price"), q.get("prev_close_price")
        chg = None
        if isinstance(lp, (int, float)) and isinstance(pc, (int, float)) and pc:
            chg = round((lp - pc) / pc * 100, 2)
        rec = {"code": c["code"], "name": c["name"], "qty": c["qty"], "last_price": lp,
               "prev_close_price": pc, "chg_pct": chg, "update_time": q.get("update_time"),
               "sec_status": q.get("sec_status")}
        quotes.append(rec)
        if chg is not None and abs(chg) > 5:
            movers.append({"code": c["code"], "name": c["name"], "chg_pct": chg, "last_price": lp, "prev_close_price": pc})
    n_priced = sum(1 for q in quotes if isinstance(q["last_price"], (int, float)))
    scan["items"]["1_当日20只价"] = {"来源": "OpenD get_market_snapshot", "扫到": n_priced, "应有": len(codes),
                                "present": ok and n_priced >= max(1, len(codes) - 1), "err": err, "逐只": quotes}
    scan["items"]["2_涨跌>5%榜"] = {"present": ok and n_priced > 0, "单日绝对涨跌>5%": sorted(movers, key=lambda x: -abs(x["chg_pct"]))}
    # 爱德万单列(日股·东证盘中/收盘标注)
    adv = next((q for q in quotes if q["code"] == "JP.6857"), None)
    if adv:
        h = datetime.now(JST).hour + datetime.now(JST).minute / 60
        is_close = h >= 15.0
        scan["items"]["2b_爱德万JP6857"] = {**adv,
            "价格性质": ("东证正式收盘价(≥15:00)" if is_close else "东证盘中价(<15:00·非正式收盘)"),
            "东证是否已收盘": is_close, "夜间盘参考": "28,120(+11.59% vs前收25,200·Opus5正文)"}
    # 3 当日新闻(计数·复用 evidence_chain daily)
    ev = ROOT / "data" / "evidence_chain" / f"daily_{date}.json"
    n_news = 0
    if ev.exists():
        try:
            ed = json.loads(ev.read_text(encoding="utf-8"))
            mn = ed.get("rule_engine", {}).get("macro_news")
            if isinstance(mn, list): n_news += len(mn)
            elif isinstance(mn, dict): n_news += sum(len(v) if isinstance(v, (list, dict)) else 1 for v in mn.values())
            lk = ed.get("links")
            if isinstance(lk, list): n_news += len(lk)
        except Exception: pass
    # ★轮66 AE3(依赖顺序修):新闻由 ②a evidence_autobuild(--with-macro-news→macro_news_intake)更晚才抓，
    #   evidence_chain/daily_{date}.json 在 ⓪ 这一步(新日期首跑)【尚不存在】→ 原来把新闻放进 ⓪ 硬闸必然
    #   把新日期第一跑拦停(rc=7·07-31 07:30 正是此故·非超时非源不可达)。修法:⓪ 只【记录】新闻计数不硬拦，
    #   真正的新闻硬闸移到 evidence_autobuild 抓完之后(daily_auto_produce verify_output 对 evidence_autobuild
    #   加『news_present』强校验)——闸没降级、没跳过，只是挪到新闻真被抓之后再判(AE3-2)。
    scan["items"]["3_当日新闻"] = {"来源": "data/evidence_chain/daily_%s.json" % date, "条数近似": n_news,
                                 "present": ev.exists() and n_news > 0,
                                 "★硬闸位置": "已移至 evidence_autobuild 抓完后核(轮66 AE3)·本步只记录不硬拦"}
    # 4 Drive 新增/变更(按修改时间·近3天)
    scan_dirs = [pathlib.Path("G:/我的云端硬盘/湖水资讯"), pathlib.Path("G:/我的云端硬盘/老雷"),
                 ROOT / "inbox", pathlib.Path("G:/我的云端硬盘")]
    READ = {".pdf", ".md", ".txt", ".csv", ".docx", ".pptx", ".xlsx"}
    UNREAD = {".gdoc", ".gsheet", ".gslides"}
    cutoff = time.time() - 3 * 86400
    found = []
    scan_ok = False
    try:
        seen = set()
        for d in scan_dirs:
            if not d.exists(): continue
            top_only = (d == pathlib.Path("G:/我的云端硬盘"))  # 根目录只列顶层文件+文件夹名·不深扫
            it = d.iterdir() if top_only else d.rglob("*")
            for p in it:
                try:
                    if not p.is_file(): continue
                    if str(p) in seen: continue
                    st = p.stat()
                    if st.st_mtime >= cutoff:
                        seen.add(str(p))
                        ext = p.suffix.lower()
                        found.append({"路径": str(p), "修改时间": datetime.fromtimestamp(st.st_mtime, JST).strftime("%Y-%m-%d %H:%M"),
                                      "扩展名": ext or "(无)", "可读": ("可读" if ext in READ else ("不可读(云端指针)" if ext in UNREAD else "格式未知需人工确认")),
                                      "字节": st.st_size})
                except Exception: continue
        scan_ok = True
    except Exception as e:
        scan["items"]["4_Drive新增"] = {"present": False, "err": str(e)}
    if scan_ok:
        scan["items"]["4_Drive新增"] = {"扫描路径": [str(x) for x in scan_dirs], "规则": "按文件修改时间·近3天·不按文件名",
                                     "present": True, "近3天新增/修改数": len(found), "清单": sorted(found, key=lambda x: x["修改时间"], reverse=True)[:80]}
    # 5 USDJPY(沿用须标)
    scan["items"]["5_USDJPY"] = {"值": 162.536, "来源": "沿用(沿用值·当日实时未接)", "沿用": True, "present": True}
    # 硬闸:1/2/3/4 present
    g1 = scan["items"]["1_当日20只价"]["present"]; g2 = scan["items"]["2_涨跌>5%榜"]["present"]
    g4 = scan["items"]["4_Drive新增"]["present"]
    # ★轮66 AE3:新闻(3_当日新闻)从 ⓪ 硬闸移除(见上·evidence 更晚才抓)。ⓠ 只硬拦本步真能产出的:价/涨跌榜/Drive新增。
    #   新闻硬闸=daily_auto_produce 对 ②a evidence_autobuild 的 news_present 强校验(抓完后判·失败整轮停)。
    missing = [n for n, ok_ in [("1_当日20只价", g1), ("2_涨跌>5%榜", g2), ("4_Drive新增", g4)] if not ok_]
    scan["gate"] = {"须齐": ["1_当日20只价", "2_涨跌>5%榜", "4_Drive新增"], "缺失": missing, "通过": not missing,
                    "★新闻硬闸": "已移至 evidence_autobuild 抓完后核(轮66 AE3·闸未降级只挪位)"}
    return scan

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d"))
    a = ap.parse_args()
    scan = build(a.date)
    out = ROOT / "data" / "market" / f"daily_scan_{a.date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scan, ensure_ascii=False, indent=2), encoding="utf-8")
    g = scan["gate"]
    print("daily_scan %s → %s" % (a.date, out.name))
    for k, v in scan["items"].items():
        print("  %-14s present=%s %s" % (k, v.get("present"), ("· " + str(v.get("err")) if v.get("err") else "")))
    print("涨跌>5%:", [(m["name"], m["chg_pct"]) for m in scan["items"]["2_涨跌>5%榜"]["单日绝对涨跌>5%"]])
    print("Drive近3天新增:", scan["items"]["4_Drive新增"].get("近3天新增/修改数"))
    print("硬闸:", "通过" if g["通过"] else ("★缺失 " + str(g["缺失"]) + " → 整轮停·不进渲染"))
    return 0 if g["通过"] else 7

if __name__ == "__main__":
    raise SystemExit(main())
