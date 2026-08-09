# -*- coding: utf-8 -*-
"""★★★轮211 · J-Quants(V2) → 六项验证 端到端管道(五环)。
安全铁律:API Key【只从 secrets 文件读·用完即弃·绝不显示/写入任何日志/文件/GitHub】。
五环:①获取公告(J-Quants /v2/td) ②正文解析(PDF→pypdf·XBRL→逐值) ③五元组抽取 ④六项验证(身份区=证券代码) ⑤台账。
★每环留痕(输入/输出/耗时)·断在哪如实报·不跳过·不用模拟数据。"""
import sys, json, time, ssl, io, re
import urllib.request, urllib.error
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verifier

_SECRET = Path("C:/AI_Investment_System/secrets/jquants-api-key.txt")
_BASE = "https://api.jquants.com/v2"
_CTX = ssl.create_default_context()


def _key():
    """★只从secrets读·调用处用完即弃(del)。绝不返回给日志/回报。"""
    return _SECRET.read_text(encoding="utf-8").strip()


def _api(path, key, params=None):
    u = _BASE + path + (("?" + urllib.parse.urlencode(params)) if params else "")
    req = urllib.request.Request(u, headers={"x-api-key": key, "User-Agent": "AIIS-research"})
    try:
        r = urllib.request.urlopen(req, timeout=25, context=_CTX)
        return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return None, str(e).encode("utf-8")


import urllib.parse


def run(code="4063", entity="JP.4063"):
    """对一只持仓日股跑五环。code=证券代码(TDnet索引=文档身份区)。"""
    log = {"标的": code, "entity": entity, "五环": []}

    def env(no, name, ok, det, t0):
        log["五环"].append({"环": no, "名": name, "通过": bool(ok), "耗时秒": round(time.time() - t0, 3), "详情": det})
        return ok

    # ① 获取公告(J-Quants /v2/td/list → 索引)。★轮216:对齐V2真实字段(DiscNo/DiscDate/Title/Docs)
    t0 = time.time()
    key = _key()
    s, body = _api("/td/list", key, {"code": code})
    ok1 = (s == 200)
    if not ok1:
        del key   # ★用完即弃
        txt = body.decode("utf-8", errors="replace")[:200]
        env(1, "获取公告(J-Quants API)", False, {"http": s, "响应": txt, "★注": "端点/认证头(x-api-key)·此为API返回·未显示key"}, t0)
        log["★断点"] = "第①环:J-Quants API认证/取数失败(%s)" % txt[:80]
        return log
    try:
        idx = json.loads(body)
    except Exception:
        idx = {}
    items = idx.get("data") or idx.get("td_list") or idx.get("list") or []
    # 升序排序·优先决算短信(正文含売上高/営業利益等量化)·取最新一份
    if isinstance(items, list):
        items.sort(key=lambda x: (str(x.get("DiscDate")), str(x.get("DiscTime"))))
    kessan = [it for it in items
              if "決算短信" in (it.get("Title") or "")
              and "Financial Results" not in (it.get("Title") or "")]  # ★日本基準決算短信·排英文版/業績予想
    # ★★★轮218 GPT V7修正1:无決算短信【不得退回选任意最新公告】·必须停止并保持A档关闭
    latest = kessan[-1] if kessan else None
    env(1, "获取公告(J-Quants API)", bool(latest),
        {"索引条数": len(items), "决算短信数": len(kessan), "选定标题": (latest or {}).get("Title", "")[:60],
         "DiscDate": (latest or {}).get("DiscDate"), "DiscNo": (latest or {}).get("DiscNo")}, t0)
    if not latest:
        del key
        log["★断点"] = "第①环:该标的无決算短信(索引%d条)·A档保持关闭" % len(items)
        log["★A档开放"] = False
        return log

    # ② 正文解析(经 /v2/td/files?discNo= 取签名PDF URL → pypdf)
    t0 = time.time()
    disc_no = latest.get("DiscNo")
    text = ""; fmt = None; file_url = None
    try:
        fs, fb = _api("/td/files", key, {"discNo": disc_no})
        if fs == 200:
            files = (json.loads(fb) or {}).get("files") or {}
            file_url = files.get("pdf") or files.get("PDF") or files.get("xbrl")
        else:
            fmt = "files端点HTTP%s" % fs
    finally:
        del key   # ★用完即弃(取到签名URL后即弃key·URL本身已含临时签名)
    if file_url:
        try:
            r = urllib.request.urlopen(urllib.request.Request(file_url, headers={"User-Agent": "AIIS"}), timeout=30, context=_CTX)
            raw = r.read()
            if raw[:5] == b"%PDF-":
                from pypdf import PdfReader
                text = " ".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(raw)).pages); fmt = "PDF"
            else:
                text = raw.decode("utf-8", errors="replace"); fmt = "XBRL/HTML"
        except Exception as e:
            text = ""; fmt = "取文件失败:" + str(e)[:40]
    ok2 = bool(text)
    env(2, "正文解析", ok2, {"文件格式": fmt, "正文字节": len(text), "标题": latest.get("Title"), "DiscNo": disc_no}, t0)
    if not ok2:
        log["★断点"] = "第②环:正文解析失败(%s)" % fmt
        return log

    # ③ 五元组抽取(散文式 或 決算短信サマリー表式)
    t0 = time.time()

    def _z2h(x):  # 全角数字/记号→半角
        return re.sub(r"[０-９]", lambda c: "0123456789"[ord(c.group()) - ord("０")], x).replace("．", ".").replace("，", ",")

    # パターンA: 散文 "売上高は前年同期比5.4％増"
    m = re.search(r"(売上高|売上収益)[^。]{0,40}?(前年同期比|前期比)[^。]{0,25}?([0-9０-９.．]+)\s*[%％][^。]{0,6}?(増|減)", text)
    w = None
    if m:
        amp = float(_z2h(m.group(3))) / 100
        w = {"实体": entity, "指标": "营收", "方向": ("增长" if m.group(4) == "増" else "下降"), "幅度": amp, "期间": "同比", "_出处": "散文"}
    else:
        # パターンB: 決算短信サマリー表 "売上高…百万円 ％…<期間> <売上高額> <増減率>"(△▲-=減·無=増)
        mt = re.search(r"売上高[^。]{0,40}?百万円\s*[%％].{0,120}?(第[0-9０-９一二三四]{1,2}四半期|通期|年度)\s*([0-9０-９][0-9０-９,，]*)\s+([△▲\-]?)\s*([0-9０-９]+[.．][0-9０-９]+)", text, re.S)
        if mt:
            amp = float(_z2h(mt.group(4))) / 100
            w = {"实体": entity, "指标": "营收", "方向": ("下降" if mt.group(3) else "增长"), "幅度": amp, "期间": "同比", "_出处": "決算短信表",
                 "_売上高": _z2h(mt.group(2))}
            m = mt
    ok3 = bool(w)
    env(3, "五元组抽取", ok3, {"五元组": w, "原文片段": m.group(0)[:90] if m else None}, t0)
    if not ok3:
        log["★断点"] = "第③环:正文未找到规范量化句(散文/決算短信表均未命中)"
        return log

    # ④ 六项验证(★身份区=证券代码 index_code·四项事实同窗)
    t0 = time.time()
    aligned, detail = verifier.six_align(text, w, index_code=code)
    env(4, "六项验证(身份区+事实证据窗)", aligned, {"六项逐项": detail, "身份=证券代码index": code}, t0)

    # ⑤ 证据台账(verifier写台账·此处记录判定)
    t0 = time.time()
    # ★★★轮219 补漏1:统一【证据原文】(散文式=命中句·表式=来源行文本)·两路径都要留原文。
    _路径 = detail.get("_事实路径")
    if _路径 == "決算短信表式":
        证据原文 = (detail.get("_表式证据") or {}).get("来源行文本")
    else:
        证据原文 = m.group(0)[:120] if m else None
    # ★硬要求(照GPT对表外借用的判法):无法复核的证据不算证据→取不到原文则A档不开。
    if aligned and not 证据原文:
        aligned = False
        log["★断点"] = "第⑤环:六项对齐但取不到可核证据原文→A档不开(无法复核的证据不算证据)"
    log["★A档开放"] = aligned
    log["★证据"] = {"证券代码": code, "五元组": w, "六项逐项": detail,
                   "证据原文": 证据原文, "_事实路径": _路径, "原文片段": (m.group(0)[:120] if m else None)}
    env(5, "证据台账留痕", True, {"A档开放": aligned, "证据原文非空": bool(证据原文)}, t0)
    if not aligned and not log.get("★断点"):
        log["★断点"] = "第④环:六项对齐未全·卡在:" + str([k for k, v in detail.items() if not v])
    return log


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    code = sys.argv[1] if len(sys.argv) > 1 else "4063"
    ent = {"4063": "JP.4063", "9984": "JP.9984", "6857": "JP.6857", "7203": "JP.7203"}.get(code, "JP." + code)
    o = run(code, ent)
    (ROOT / "data/funnel").mkdir(parents=True, exist_ok=True)
    # ★★★轮218 GPT V7修正2:输出文件名按【实际运行日期】自动生成·不得写死(防误命名酿"假A档日期")
    _d = time.strftime("%Y%m%d")
    (ROOT / "data/funnel" / ("jquants_pipeline_result_%s.json" % _d)).write_text(json.dumps(o, ensure_ascii=False, indent=1), encoding="utf-8")
    for e in o["五环"]:
        print("环%s %-24s 通过=%s 耗时%.3fs" % (e["环"], e["名"], e["通过"], e["耗时秒"]))
    print("★断点:", o.get("★断点", "无·五环全通"))
    print("★A档开放:", o.get("★A档开放"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
