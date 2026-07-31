#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EDINET(日本金融厅)财报接入·安全版(董事长2026-07-25 EDINET安全铁律)。

★安全铁律(逐条守):
  1. 密钥只从文件读:C:\\AI_Investment_System\\secrets\\edinet-api-key.txt(读进内存·用完即弃)·不硬编·不经聊天。
  2. 密钥绝不打印/写日志/入HTML:任何输出一律脱敏(_mask:前2位+***)。
  3. secrets/ 已入 .gitignore;密钥在C盘·不在G盘GDrive同步范围。
  4. 只用密钥·不换不轮换。
  5. 不改任何已验收产品(locked_v*);本脚本只读EDINET·写 data/valuation/。

用途:①最小连通验证(documents.json)②(后续)按证券码取XBRL财报→日股EPS进估值。
用法:python scripts/edinet_financials.py --verify --date 20260724
"""
import argparse
import json
import ssl
import sys
import urllib.request
from pathlib import Path

KEY_FILE = Path("C:/AI_Investment_System/secrets/edinet-api-key.txt")
API_BASE = "https://api.edinet-fsa.go.jp/api/v2"
ROOT = Path("G:/我的云端硬盘/AI_Investment_System")


def _load_key() -> str:
    """从密钥文件读进内存。绝不返回给调用方打印·只在请求头内部用。"""
    if not KEY_FILE.exists():
        raise FileNotFoundError(f"密钥文件不存在:{KEY_FILE}")
    k = KEY_FILE.read_text(encoding="utf-8").strip()
    if not k:
        raise ValueError("密钥文件为空")
    return k


def _mask(k: str) -> str:
    """脱敏:只显前2位+***·长度不显真值。用于任何要提及密钥的场合。"""
    return (k[:2] + "***") if len(k) >= 2 else "***"


def verify(date: str) -> dict:
    """最小连通验证:调 documents.json·带订阅key请求头·返 HTTP状态+条数。密钥不出现在返回里。"""
    url = f"{API_BASE}/documents.json?date={date[:4]}-{date[4:6]}-{date[6:]}&type=2"
    key = _load_key()                       # 内存持有·下面用完即弃
    masked = _mask(key)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        "Ocp-Apim-Subscription-Key": key,   # 密钥只进请求头·不落任何输出
        "User-Agent": "AI-Invest-System/1.0",
    })
    status, count, ok, note = None, None, False, ""
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
            status = r.status
            body = r.read().decode("utf-8", errors="replace")
        try:
            j = json.loads(body)
            results = j.get("results") or j.get("documents") or []
            count = len(results)
            meta_status = (j.get("metadata") or {}).get("status")
            ok = (status == 200) and (str(meta_status) in ("200", "None", "") or meta_status is None) and isinstance(results, list)
            note = f"metadata.status={meta_status}"
        except Exception as e:
            note = f"返回非JSON:{type(e).__name__}"
    except urllib.error.HTTPError as e:
        status = e.code
        note = f"HTTPError {e.code}"
    except Exception as e:
        note = f"{type(e).__name__}:{str(e)[:80]}"
    finally:
        key = None                          # 用完即弃(内存置空)
        del key
    return {"url": url, "http_status": status, "count": count, "ok": ok,
            "key_used_masked": masked, "note": note}


# ── 一·证券码↔EDINET码 映射(keyless·下 Edinetcode.zip) ──
CODELIST_ZIP = "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/codelist/Edinetcode.zip"
CACHE = ROOT / "data" / "valuation"
# 20只持仓里的日股(JP.*)·ticker→证券码5位(EDINET用4位ticker+尾0)
JP_HOLDINGS = {
    "JP.4568": "第一三共", "JP.9984": "软银", "JP.6857": "爱德万", "JP.7203": "丰田",
    "JP.6758": "索尼", "JP.8766": "东京海上", "JP.8001": "伊藤忠", "JP.7832": "万代", "JP.7974": "任天堂",
}


def _ctx():
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def download_codelist() -> Path:
    """下 Edinetcode.zip(keyless)→存 CSV 缓存。返 CSV 路径。"""
    import io
    import zipfile
    CACHE.mkdir(parents=True, exist_ok=True)
    csv_path = CACHE / "edinet_codelist.csv"
    req = urllib.request.Request(CODELIST_ZIP, headers={"User-Agent": "AI-Invest-System/1.0"})
    with urllib.request.urlopen(req, timeout=60, context=_ctx()) as r:
        data = r.read()
    zf = zipfile.ZipFile(io.BytesIO(data))
    name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
    raw = zf.read(name)
    csv_path.write_bytes(raw)
    return csv_path


def build_secmap() -> dict:
    """证券码(4位)→{edinet码,名称}。CSV 是 CP932·第2行表头·含『ＥＤＩＮＥＴコード』『証券コード』列。"""
    csv_path = CACHE / "edinet_codelist.csv"
    if not csv_path.exists():
        download_codelist()
    txt = csv_path.read_bytes().decode("cp932", errors="replace")
    import csv as _csv
    lines = txt.splitlines()
    # 找表头行(含 EDINET コード)
    hdr_i = next((i for i, ln in enumerate(lines) if "ＥＤＩＮＥＴコード" in ln or "EDINETコード" in ln), 1)
    rdr = list(_csv.reader(lines[hdr_i:]))
    hdr = rdr[0]
    def col(kw):
        return next((i for i, h in enumerate(hdr) if kw in h), None)
    ci_ed = col("ＥＤＩＮＥＴコード") if col("ＥＤＩＮＥＴコード") is not None else col("EDINET")
    ci_sec = col("証券コード")
    ci_nm = col("提出者名")
    m = {}
    for row in rdr[1:]:
        if len(row) <= max(x for x in (ci_ed, ci_sec, ci_nm) if x is not None):
            continue
        sec = (row[ci_sec] or "").strip() if ci_sec is not None else ""
        if sec and sec[:4].isdigit():
            m[sec[:4]] = {"edinet": (row[ci_ed] or "").strip(), "name": (row[ci_nm] or "").strip()}
    return m


def find_annual_doc(edinet_code: str, key: str, days_back: int = 400) -> dict:
    """扫最近 days_back 天 documents.json·找该 edinet码 的『有価証券報告書』(docTypeCode=120)最新一份。返 {docID,date,desc}。"""
    import datetime as _dt
    base = _dt.date(2026, 7, 24)   # 数据日锚(系统当日·真实API按此返)
    for d in range(0, days_back):
        day = base - _dt.timedelta(days=d)
        url = f"{API_BASE}/documents.json?date={day.isoformat()}&type=2"
        req = urllib.request.Request(url, headers={"Ocp-Apim-Subscription-Key": key, "User-Agent": "AI-Invest-System/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=30, context=_ctx()) as r:
                j = json.loads(r.read().decode("utf-8", errors="replace"))
        except Exception:
            continue
        for doc in (j.get("results") or []):
            if str(doc.get("edinetCode")) == edinet_code and str(doc.get("docTypeCode")) == "120":
                return {"docID": doc.get("docID"), "date": day.isoformat(),
                        "desc": doc.get("docDescription", ""), "period": doc.get("periodEnd", "")}
    return {}


def fetch_xbrl_financials(doc_id: str, key: str) -> dict:
    """下 XBRL(type=1 zip)→解日本准则税目:营收 NetSales / 净利 ProfitLoss / EPS。取『概要(SummaryOfBusinessResults)』最近年值。"""
    import io
    import re as _re
    import zipfile
    url = f"{API_BASE}/documents/{doc_id}?type=1"
    req = urllib.request.Request(url, headers={"Ocp-Apim-Subscription-Key": key, "User-Agent": "AI-Invest-System/1.0"})
    with urllib.request.urlopen(req, timeout=60, context=_ctx()) as r:
        data = r.read()
    zf = zipfile.ZipFile(io.BytesIO(data))
    xbrl_name = next((n for n in zf.namelist() if n.endswith(".xbrl") and "PublicDoc" in n), None) \
        or next((n for n in zf.namelist() if n.endswith(".xbrl")), None)
    if not xbrl_name:
        return {"error": "zip内无.xbrl"}
    xml = zf.read(xbrl_name).decode("utf-8", errors="replace")
    # 概要税目(逐年·取 CurrentYear 上下文)
    def grab(tag_kw):
        # 匹配 <...:TagKw contextRef="...CurrentYear...">value</...>
        for m in _re.finditer(rf'<[\w]+:({tag_kw})[^>]*contextRef="([^"]*)"[^>]*>([^<]+)</', xml):
            if "CurrentYear" in m.group(2) and "NonConsolidated" not in m.group(2):
                return m.group(3).strip()
        for m in _re.finditer(rf'<[\w]+:({tag_kw})[^>]*contextRef="([^"]*)"[^>]*>([^<]+)</', xml):
            if "CurrentYear" in m.group(2):
                return m.group(3).strip()
        return None
    net_sales = grab("NetSalesSummaryOfBusinessResults") or grab("RevenueIFRSSummaryOfBusinessResults") or grab("NetSales")
    eps = grab("BasicEarningsLossPerShareSummaryOfBusinessResults") or grab("BasicEarningsPerShareIFRSSummaryOfBusinessResults") or grab("BasicEarningsLossPerShare")
    profit = grab("NetIncomeLossSummaryOfBusinessResults") or grab("ProfitLossAttributableToOwnersOfParentIFRSSummaryOfBusinessResults") or grab("ProfitLoss")
    return {"net_sales": net_sales, "profit": profit, "eps": eps, "xbrl_file": xbrl_name.split("/")[-1]}


def run_one(sym: str) -> dict:
    """1只全链:证券码→EDINET码→找有報→下XBRL→解EPS。"""
    key = _load_key()
    try:
        secmap = build_secmap()
        tk = sym.split(".")[-1]
        info = secmap.get(tk) or {}
        ed = info.get("edinet")
        if not ed:
            return {"sym": sym, "ok": False, "note": f"证券码{tk}未在EDINET代码表找到"}
        doc = find_annual_doc(ed, key)
        if not doc.get("docID"):
            return {"sym": sym, "ok": False, "edinet": ed, "name": info.get("name"), "note": "近400天未找到有価証券報告書(docTypeCode=120)"}
        fin = fetch_xbrl_financials(doc["docID"], key)
        ok = bool(fin.get("eps") or fin.get("net_sales"))
        return {"sym": sym, "ok": ok, "edinet": ed, "name": info.get("name"),
                "docID": doc["docID"], "filed": doc["date"], "period": doc.get("period"),
                "net_sales": fin.get("net_sales"), "profit": fin.get("profit"), "eps": fin.get("eps"),
                "note": ("解出财报" if ok else "找到有報但税目未解出:" + str(fin))}
    finally:
        key = None
        del key


def run_all(date: str, days_back: int = 400) -> dict:
    """铺开9只日股:单遍扫日期·一次收齐所有EDINET码的有報 docID(比逐只快)→逐个下XBRL解财报→写 edinet_financials_{date}.json(EDGAR同格式)。"""
    import datetime as _dt
    key = _load_key()
    out = {"_说明": "EDINET(日本金融厅)日股财报·日本准则XBRL税目·与美股EDGAR同格式进估值。密钥安全:只从secrets文件读·不落盘。",
           "date": date, "generated_at": _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=9))).isoformat(timespec="seconds"),
           "source": "EDINET API v2 (api.edinet-fsa.go.jp) · 有価証券報告書XBRL", "symbols": {}}
    try:
        secmap = build_secmap()
        want = {}   # edinetCode → sym
        for sym in JP_HOLDINGS:
            ed = (secmap.get(sym.split(".")[-1]) or {}).get("edinet")
            if ed:
                want[ed] = sym
                out["symbols"][sym] = {"status": "待接", "edinet": ed, "name": (secmap.get(sym.split(".")[-1]) or {}).get("name")}
        found = {}   # edinetCode → doc
        base = _dt.date(int(date[:4]), int(date[4:6]), int(date[6:]))
        for d in range(0, days_back):
            if len(found) >= len(want):
                break
            day = base - _dt.timedelta(days=d)
            url = f"{API_BASE}/documents.json?date={day.isoformat()}&type=2"
            req = urllib.request.Request(url, headers={"Ocp-Apim-Subscription-Key": key, "User-Agent": "AI-Invest-System/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=30, context=_ctx()) as r:
                    j = json.loads(r.read().decode("utf-8", errors="replace"))
            except Exception:
                continue
            for doc in (j.get("results") or []):
                ec = str(doc.get("edinetCode"))
                if ec in want and ec not in found and str(doc.get("docTypeCode")) == "120":
                    found[ec] = {"docID": doc.get("docID"), "filed": day.isoformat(), "period": doc.get("periodEnd", "")}
        for ec, doc in found.items():
            sym = want[ec]
            try:
                fin = fetch_xbrl_financials(doc["docID"], key)
            except Exception as e:
                fin = {"error": str(e)[:60]}
            ok = bool(fin.get("eps") or fin.get("net_sales"))
            out["symbols"][sym].update({"status": "OK" if ok else "解析失败", "docID": doc["docID"],
                                        "filed": doc["filed"], "period": doc["period"],
                                        "net_sales": fin.get("net_sales"), "profit": fin.get("profit"), "eps": fin.get("eps")})
    finally:
        key = None
        del key
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"edinet_financials_{date}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    out["_path"] = str(p)
    return out


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--codelist", action="store_true")
    ap.add_argument("--one", default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--date", default="20260724")
    a = ap.parse_args()
    if a.all:
        r = run_all(a.date)
        ok = sum(1 for v in r["symbols"].values() if v.get("status") == "OK")
        print(f"=== 日股9只EDINET铺开 · OK={ok}/{len(r['symbols'])} · 写:{r.get('_path')} ===")
        for sym, v in r["symbols"].items():
            print(f"  {sym} {v.get('name','')[:14]}: {v.get('status')} EPS={v.get('eps')} 营收={v.get('net_sales')} FY={v.get('period')}")
        return 0
    if a.codelist:
        p = download_codelist()
        m = build_secmap()
        print(f"代码表下好:{p}·条数{len(m)}")
        for s, nm in JP_HOLDINGS.items():
            tk = s.split(".")[-1]
            print(f"  {s} {nm} → 证券码{tk} → EDINET码 {m.get(tk, {}).get('edinet', '未找到')}·{m.get(tk, {}).get('name', '')}")
        return 0
    if a.one:
        r = run_one(a.one)
        print("=== 1只EDINET财报链验证 ===")
        for k, v in r.items():
            print(f"  {k}: {v}")
        return 0 if r.get("ok") else 1
    if a.verify:
        r = verify(a.date)
        # ★只打印脱敏摘要·密钥一个字不出现
        print("=== EDINET 最小连通验证 ===")
        print(f"① 接入文件:scripts/edinet_financials.py · 读密钥:{KEY_FILE}")
        print(f"② 接口URL(不含密钥):{r['url']}")
        print(f"③ HTTP状态码:{r['http_status']}")
        print(f"④ 返回数据条数:{r['count']}")
        print(f"⑤ 结果:{'成功' if r['ok'] else '失败'} · {r['note']}")
        print(f"   (密钥已脱敏使用:{r['key_used_masked']}·真值不显)")
        return 0 if r["ok"] else 1
    print("用法:--verify --date YYYYMMDD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
