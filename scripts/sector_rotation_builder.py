# -*- coding: utf-8 -*-
"""★轮84 BC3:第④层板块轮动(整层未建→建)。完工判据4项:承接节点涨跌齐 + 板块净流入有数 + 轮动信号 + 大盘指数齐。
 BC3-1 承接节点当日涨跌(激活清单板块格·每格代表标的)→逐格涨跌。
 BC3-2 大盘指数:SOXX已接·补 纳指^IXIC / 日经^N225 / 标普^GSPC(Yahoo·无密钥)。
 BC3-3 板块净流入:免密钥源无真实资金净流入·成交额≠净流入·★取不到标『未接·原因』(严禁估算/代理冒充)。
 BC3-4 轮动信号:硬件↔软件(SOXX↔IGV)、成长↔价值(IWF↔IWD)近5日/20日相对强弱(可算·用ETF相对涨跌)。
输出 data/market/sector_rotation_{date}.json + ★接通 N/4。"""
import sys, json, argparse, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0"}


def _get(url, to=12):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=to).read().decode("utf-8", "replace")


def _series(sym, rng="1mo"):
    """Yahoo chart → (closes[], last_date)。失败→(None,err)。"""
    try:
        j = json.loads(_get("https://query1.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=1d" % (sym, rng)))
        r = j["chart"]["result"][0]
        cl = [c for c in r["indicators"]["quote"][0]["close"] if c is not None]
        ts = r.get("timestamp", [])
        d = datetime.fromtimestamp(ts[-1], timezone.utc).strftime("%Y-%m-%d") if ts else None
        return (cl, d) if cl else (None, "无收盘")
    except Exception as e:
        return None, "%s:%s" % (sym, type(e).__name__)


def _ret(cl, n):
    return round((cl[-1] / cl[-1 - n] - 1) * 100, 2) if cl and len(cl) > n else None


def _daychg(cl):
    return round((cl[-1] / cl[-2] - 1) * 100, 2) if cl and len(cl) >= 2 else None


def build(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    conn = {}   # 4项接通标记

    # ── BC3-2 大盘指数 ──
    idx_syms = {"标普500": "^GSPC", "纳指": "^IXIC", "日经225": "^N225", "半导体SOXX": "SOXX"}
    indices = {}; idx_ok = 0
    for nm, sym in idx_syms.items():
        cl, d = _series(sym, "5d")
        if cl:
            indices[nm] = {"代码": sym, "当日涨跌pct": _daychg(cl), "收盘": cl[-1], "数据日": d, "源": "Yahoo"}
            idx_ok += 1
        else:
            indices[nm] = {"代码": sym, "当日涨跌pct": None, "★未接": str(d)}
    conn["大盘指数齐"] = (idx_ok >= 3)   # 4个里≥3接通算齐(允许某指数偶发失败)

    # ── BC3-4 轮动信号(硬件↔软件·成长↔价值·相对强弱) ──
    pairs = {"硬件↔软件": ("SOXX", "IGV"), "成长↔价值": ("IWF", "IWD")}
    rotation = {}; rot_ok = 0
    for nm, (a, b) in pairs.items():
        ca, _ = _series(a, "2mo"); cb, _ = _series(b, "2mo")
        if ca and cb:
            r5 = None if _ret(ca, 5) is None or _ret(cb, 5) is None else round(_ret(ca, 5) - _ret(cb, 5), 2)
            r20 = None if _ret(ca, 20) is None or _ret(cb, 20) is None else round(_ret(ca, 20) - _ret(cb, 20), 2)
            lead = "均衡"
            if r5 is not None:
                lead = (nm.split("↔")[0] + "领先") if r5 > 0.5 else ((nm.split("↔")[1] + "领先") if r5 < -0.5 else "均衡")
            rotation[nm] = {"代表": "%s vs %s" % (a, b), "近5日相对强弱pp": r5, "近20日相对强弱pp": r20, "当前": lead}
            rot_ok += 1
        else:
            rotation[nm] = {"代表": "%s vs %s" % (a, b), "★未接": "序列取不到"}
    conn["轮动信号"] = (rot_ok >= 1)

    # ── BC3-1 承接节点当日涨跌(激活清单板块格·代表标的) ──
    act = {}
    import glob as _g
    cands = sorted(_g.glob(str(ROOT / "data/market/sector_activation_*.json")))
    if cands:
        act = json.loads(Path(cands[-1]).read_text(encoding="utf-8"))
    scan = json.loads((ROOT / "data/market" / f"daily_scan_{dc}.json").read_text(encoding="utf-8")) \
        if (ROOT / "data/market" / f"daily_scan_{dc}.json").exists() else {}
    px_chg, px_name = {}, {}
    for q in ((scan.get("items", {}).get("1_当日20只价", {}) or {}).get("逐只", []) or []):
        px_chg[q.get("code")] = q.get("chg_pct")
        px_name[q.get("code")] = q.get("name")
    # 事实映射:板块格名关键词→代表持仓代码(分类·非投资判断)
    SEC_MAP = [("存储", "US.SNDK"), ("半导体", "US.NVDA"), ("AI算力", "US.NVDA"), ("软件", "US.MSFT"),
               ("云", "US.MSFT"), ("加密", "US.MSTR"), ("稳定币", "US.CRCL"), ("数字资产", "US.COIN"),
               ("互联网平台", "US.META"), ("社交", "US.META"), ("游戏", "JP.7974"), ("娱乐", "JP.6758"),
               ("电子", "JP.6758"), ("测试", "JP.6857"), ("汽车", "JP.7203"), ("综合商社", "JP.8001"),
               ("保险", "JP.8766"), ("医药", "JP.4568"), ("生物", "JP.4568"), ("通信", "JP.9984"), ("网络", "US.IBKR")]
    grid = act.get("板块", [])
    nodes = []
    for g in (grid or [])[:20]:
        nm = g.get("板块") or g.get("name") or "?"
        rep = None
        for kw, code in SEC_MAP:
            if kw in str(nm):
                rep = code; break
        nodes.append({"板块格": str(nm)[:24], "群": g.get("群"), "激活": g.get("激活"),
                      "状态词": str(g.get("状态词", ""))[:20],
                      "代表持仓": (px_name.get(rep) or rep) if rep else "待映射",
                      "当日涨跌pct": px_chg.get(rep) if rep else None})
    _n_with_chg = sum(1 for n in nodes if n["当日涨跌pct"] is not None)
    conn["承接节点涨跌齐"] = (len(nodes) >= 10 and _n_with_chg >= 5)

    # ── BC3-3 板块净流入(★轮86 DC3-2收口:结构性不可得·非待接·从④判据移除) ──
    netflow = {"★分类": "结构性不可得·非待接(DC3-2·董事长/Opus5授权)",
               "为何": "净流入=ETF份额日变动×NAV·需份额【历史日序列】·免密钥源只给【当前单点份额】(SSGA/iShares页/EDGAR N-PORT均可达但无免密钥每日份额历史)·成交额≠净流入不可代理",
               "试了哪些源(轮85+轮86)": [
                   "Yahoo quoteSummary→HTTP401(已废弃)", "Yahoo chart→仅成交量",
                   "FRED→Akamai阻", "ETF.com/VettaFi→需JS",
                   "SEC EDGAR N-PORT→可达但月频+复杂XBRL·非每日", "SSGA/iShares官网→可达但仅当前份额单点·无免密钥每日历史序列"],
               "★结论": "从④层判据移除(不长期挂未接)·④判据改为3项(承接节点涨跌/大盘指数/轮动信号)",
               "★未来真数路径(非本轮·非阻塞)": "每日抓当前份额自建历史快照·≥2日后可算真份额日变×NAV净流入"}
    # ★DC3-2:净流入不计入接通判据(结构性不可得已移除)·conn只留3项

    n_conn = sum(1 for v in conn.values() if v)
    out = {
        "★★★已废弃标注": "★本文件(sector_rotation)已被 sector_strength_{date}.json 取代·★内容不可用(读TEMPLATE/激活全null/IBKR代表国防军工/只有当日涨跌·无成分股篮子)·★不得进产品渲染·保留仅作历史。裁定08-07·用真实成分股篮子的 sector_strength 替代单只代表股。",
        "_说明": "★轮84建/轮86 DC3-2收口:第④层板块轮动。判据3项(承接节点涨跌/大盘指数/轮动信号)——板块净流入已按结构性不可得从判据移除(免密钥无每日份额历史·不长期挂未接)。",
        "date": dh, "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "BC3-2_大盘指数": indices, "BC3-4_轮动信号": rotation,
        "BC3-1_承接节点涨跌": nodes, "BC3-3_板块净流入(结构性不可得·非判据)": netflow,
        "★接通": conn, "★接通N/3": "%d/3" % n_conn, "★接通N/4": "%d/4" % n_conn,
    }
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out = build(a.date)
    p = ROOT / "data" / "market" / f"sector_rotation_{a.date.replace('-', '')}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    b = p.read_bytes(); json.loads(b.decode())
    print("[sector_rotation] %s → %s · 乱码%d · 接通 %s" % (a.date, p.name, b.count(b"\xef\xbf\xbd"), out.get("★接通N/3",out["★接通N/4"])))
    for nm, d in out["BC3-2_大盘指数"].items():
        print("  指数 %s: %s" % (nm, d.get("当日涨跌pct") if d.get("当日涨跌pct") is not None else d.get("★未接")))
    for nm, d in out["BC3-4_轮动信号"].items():
        print("  轮动 %s: 5日%s / 20日%s → %s" % (nm, d.get("近5日相对强弱pp"), d.get("近20日相对强弱pp"), d.get("当前", d.get("★未接"))))
    print("  承接节点 %d 格 · 净流入:未接(免密钥无真源)" % len(out["BC3-1_承接节点涨跌"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
