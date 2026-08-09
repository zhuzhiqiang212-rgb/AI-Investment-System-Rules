# -*- coding: utf-8 -*-
# ★★★GPT V7 轮209 终验通过 · 2026-08-05
# ★本闸施工【停止线】：除非出现新的真实绕过证据，不得继续修改
# ★★如需修改，须先提交绕过证据并经 GPT 批准
# ★★★轮217(2026-08-06)GPT V7【批准】追加:日本決算短信表式増減率识别(parse_tanshin_ratio)。
#     判据固定(△/▲=減·纯数字=増·0.0=持平·空白/取不到=不判断)·只表内取值·方向幅度必须同栏·不借用表外文字。
#     ★only在散文式方向/四项同窗取不到时兜底·six_align主逻辑未改。
"""★★★轮205 · 外部来源【联网验证器·六项对齐核验】(根治跨事实错配·非字符串命中)。
GPT攻破:example.com只含"Example"·五元组「ACLS订单同比增长20%」竟开放A档→验证器形同虚设(只做字符串命中)。
本轮:
  A 六项对齐(公司主体/指标/方向/幅度/期间/来源正文)·任一不齐→不合格。
  B 证书核验改回正常(check_hostname=True·CERT_REQUIRED)·证书失败→不合格(不降级)。
  C 来源等级表(机器可判)·A档只接受一级(监管)/二级(公司官网IR)。
★验证结果只入独立台账·提交者自报标志一律不读。
"""
import sys, json, time, ssl, hashlib, re
import urllib.request
import urllib.error
from pathlib import Path

VERIFIER_VERSION = "verifier-2.1-20260806-sixalign+tanshin"
AVAILABLE = True
# ★台账路径健壮化(自包含内联时无ROOT→退内存台账·不崩)
try:
    _LEDGER_PATH = Path(__file__).resolve().parents[1] / "data/funnel/verification_ledger.json"
except Exception:
    _LEDGER_PATH = None
_LEDGER = {}
if _LEDGER_PATH is not None and _LEDGER_PATH.exists():
    try:
        _LEDGER = json.loads(_LEDGER_PATH.read_text(encoding="utf-8"))
    except Exception:
        _LEDGER = {}

_UA = "AIIS-verifier/2.0 (compliance@ai-investment.local)"
# ★★★B:证书核验【改回正常】——验证对方确是它声称的网站。证书失败→不合格(不降级·不CERT_NONE)。
_CTX = ssl.create_default_context()
_CTX.check_hostname = True
_CTX.verify_mode = ssl.CERT_REQUIRED

# ═══ 实体→公司名(判"页面确在讲这家公司"·非碰巧出现代码) ═══
_ENTITY_NAMES = {
    "US.ACLS": ["Axcelis", "阿克塞利斯"], "US.NVDA": ["NVIDIA", "英伟达"], "US.MSFT": ["Microsoft", "微软"],
    "US.SNDK": ["SanDisk", "Sandisk", "闪迪"], "US.AVGO": ["Broadcom", "博通"], "US.TSM": ["Taiwan Semiconductor", "台积电", "TSMC"],
}
# ═══ 指标/方向/期间 同义词(中英) ═══
_IND_SYN = {"订单": ["订单", "orders", "order", "bookings", "backlog"],
            "营收": ["营收", "收入", "revenue", "sales"], "毛利": ["毛利", "gross margin", "gross profit"]}
_DIR_UP = ["增长", "增加", "上升", "上涨", "提升", "growth", "grew", "increase", "increased", "rose", "up", "higher"]
_DIR_DOWN = ["下降", "减少", "下滑", "下跌", "decline", "declined", "decrease", "fell", "down", "lower"]
_PER_SYN = {"同比": ["同比", "较去年", "较上年", "year-over-year", "year over year", "yoy", "y/y", "from a year"],
            "环比": ["环比", "较上季", "quarter-over-quarter", "qoq", "q/q", "sequential"],
            "季度": ["季度", "quarter", "quarterly", "q1", "q2", "q3", "q4"]}

# ═══════════ ★★★轮208 日语适配层【独立·只ADD不改中英文】 ═══════════
# ★中英文原有条目一字不动(上方)·此处仅【追加】日语同义词。回归:NVDA/MSFT不受影响。
_JP_ENTITY = {"JP.9984": ["ソフトバンクグループ", "ソフトバンク", "9984"],
              "JP.6857": ["アドバンテスト", "6857"], "JP.4063": ["信越化学工業", "信越化学", "4063"]}
_ENTITY_NAMES.update(_JP_ENTITY)
# 日语指标(A-1):追加进对应中文指标的同义列;并新增几类
_IND_SYN["营收"] += ["売上高", "売上収益", "売上", "純売上高"]
_IND_SYN.setdefault("营业利润", ["营业利润", "operating income", "operating profit"]).extend(["営業利益"])
_IND_SYN.setdefault("经常利润", ["経常利益", "ordinary income", "ordinary profit"])
_IND_SYN.setdefault("净利润", ["净利润", "net income", "net profit"]).extend(["純利益", "当期純利益"])
_IND_SYN["订单"] += ["受注高", "受注残高", "受注"]
# 日语方向(A-2):增侧/降侧【追加】
_DIR_UP += ["増加", "増収", "増益", "上昇", "拡大", "上方修正", "増"]
_DIR_DOWN += ["減少", "減収", "減益", "下落", "縮小", "下方修正", "減"]
# 日语期间(A-3):追加进同比;新增通期/四半期
_PER_SYN["同比"] += ["前年同期比", "前年同期", "前年比"]
_PER_SYN.setdefault("环比", []).append("前期比")
_PER_SYN.setdefault("通期", ["通期", "通期予想", "full-year", "full year"])
_PER_SYN.setdefault("四半期", ["四半期", "第1四半期", "第2四半期", "第3四半期", "第4四半期", "第一四半期", "第二四半期", "第三四半期"])

# ═══ C:来源等级表(★轮206:严格主机域名边界·防子串伪装) ═══
_LEVEL1 = ["sec.gov", "edinet-fsa.go.jp", "jpx.co.jp", "sec.report", "hkexnews.hk"]  # 监管/交易所
_LEVEL3 = ["reuters.com", "bloomberg.com", "cnbc.com", "wsj.com", "ft.com", "nikkei.com", "marketwatch.com"]  # 主流财经媒体
# ★二级=公司官网/IR:须【注册域名】在白名单(ir.前缀不能单独授二级·还须核公司主体归属)
_LEVEL2_IR = {"axcelis.com": "US.ACLS", "nvidia.com": "US.NVDA", "microsoft.com": "US.MSFT",
              "shinetsu.co.jp": "JP.4063", "advantest.com": "JP.6857", "group.softbank": "JP.9984"}


def _host_of(url):
    m = re.search(r"https?://([^/:]+)", str(url or "").lower())
    return m.group(1) if m else str(url or "").lower().split("/")[0]


def _domain_suffix_match(host, d):
    """★B-4:严格域名边界——host 等于 d 或以 .d 结尾(注册域名边界)。子串不算。
    如 sec.gov.attacker.com 不匹配 sec.gov(它以 .attacker.com 结尾)。"""
    host = host.strip(".")
    return host == d or host.endswith("." + d)


def source_level(url, entity=None):
    """★C(轮206严格版):域名→来源等级·按【注册域名边界】判(防 sec.gov.attacker.com 伪装)。
    ★二级须注册域名在IR白名单且公司主体归属匹配(entity)。"""
    host = _host_of(url)
    if any(_domain_suffix_match(host, d) for d in _LEVEL1):
        return 1, "一级·监管/交易所"
    # 二级:注册域名在IR白名单(严格边界)·且(若给entity)归属一致
    for d, ent in _LEVEL2_IR.items():
        if _domain_suffix_match(host, d) and (entity is None or ent == entity):
            return 2, "二级·公司官网/IR(%s)" % d
    if any(_domain_suffix_match(host, d) for d in _LEVEL3):
        return 3, "三级·主流财经媒体"
    return 4, "四级·其他(默认最低·未在等级表/伪装域名)"


def is_available():
    return AVAILABLE


def _key(url, wuyuanzu):
    return hashlib.sha256(("%s||%s" % (url, json.dumps(wuyuanzu or {}, ensure_ascii=False, sort_keys=True))).encode("utf-8")).hexdigest()[:16]


def lookup(url, wuyuanzu=None):
    return _LEDGER.get(_key(url, wuyuanzu))


def _write_ledger(key, rec):
    _LEDGER[key] = rec
    if _LEDGER_PATH is None:
        return   # 内存台账(自包含内联)
    try:
        _LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        _LEDGER_PATH.write_text(json.dumps(_LEDGER, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _term_in(term, text):
    """★B-3:完整词匹配(词边界)——防 update 含 up 误判。
    含中日韩字的词用子串(CJK无空格);纯拉丁词用 \\b 词边界。"""
    term = str(term or "").lower()
    if not term:
        return False
    if re.search(r"[一-鿿ぁ-んァ-ヶ]", term):   # 含CJK→子串
        return term in text
    return re.search(r"\b" + re.escape(term) + r"\b", text) is not None


_FW = "０１２３４５６７８９"   # 全角数字


def _to_fullwidth(num):
    return "".join(_FW[int(c)] if c.isdigit() else ("．" if c == "." else c) for c in num)


def _pct_forms(amp):
    """★B-2:幅度→百分比精确形态(带边界·防 20% 被 120% 冒充)。返回 [(正则, 展示串)]。
    ★轮208 A-4日语适配:追加全角(２０％)/パーセント形态·边界仍成立(全角120%不冒充全角20%)。"""
    try:
        pct = round(float(amp) * 100, 4) if abs(float(amp)) <= 1 else float(amp)
    except Exception:
        return []
    num = ("%g" % pct)
    fw = _to_fullwidth(num)   # 全角数字
    return [
        (r"(?<![\d.])" + re.escape(num) + r"\s*(?:%|percent)", num + "%"),          # 半角(原·不动)
        (r"(?<![\d.])" + re.escape(num) + r"\s*パーセント", num + "パーセント"),     # 半角数字+パーセント
        (r"(?<![０-９．])" + re.escape(fw) + r"\s*(?:％|パーセント)", fw + "％"),    # 全角数字+全角％/パーセント
    ]


# ═══════════ ★★★轮209:文档身份区(确认公司主体)——【域名—证券代码—法律实体】正式映射表(A-3) ═══════════
# ★A-4:平台域名(SEC/EDINET/TDnet)是共用平台·【不得】用平台域名确认主体·只能靠公告证券代码/申报主体字段/页头。
_PLATFORM_DOMAINS = ["sec.gov", "edinet-fsa.go.jp", "release.tdnet.info", "jpx.co.jp", "hkexnews.hk", "jpx-jquants"]
# 域名(注册域名)→(证券代码, 法律实体)。★未登记域名不得凭名称获资格(A-3)。
_DOMAIN_MAP = {
    "shinetsu.co.jp": ("4063", "信越化学工業株式会社"),
    "advantest.com": ("6857", "株式会社アドバンテスト"),
    "group.softbank": ("9984", "ソフトバンクグループ株式会社"),
    "nvidia.com": ("NVDA", "NVIDIA Corporation"),
    "microsoft.com": ("MSFT", "Microsoft Corporation"),
    "axcelis.com": ("ACLS", "Axcelis Technologies, Inc."),
}


def _identity_code(entity):
    """五元组实体→证券代码(JP取后4位数字;US取ticker)。"""
    e = str(entity or "")
    if e.startswith("JP.") or e.startswith("HK."):
        return e.split(".")[-1]
    if e.startswith("US."):
        return e.split(".")[-1]
    return e


def _code_in_header(code, header):
    """证券代码在页头(词边界/コード番号语境)。"""
    if not code:
        return False
    return re.search(r"(?<![0-9A-Za-z])" + re.escape(str(code)) + r"(?![0-9A-Za-z])", header, re.I) is not None


def confirm_identity(text, entity, url=None, index_code=None):
    """★A-1/A-3/A-4 文档身份区。返回(确认:bool, 方式:str/None, 硬失败:bool, 源可信:bool)。
    ①②申报/索引证券代码 ③页头公司名/证券代码(仅可信源) ④登记IR域名(非平台)。
    ★index_code给了但不一致→硬失败(拦②⑧·不许回退)。★未登记域名=源不可信→③失效(⑨)。"""
    code = _identity_code(entity)
    names = [n.lower() for n in _ENTITY_NAMES.get(str(entity), [])]
    header = str(text or "")[:700]; hl = header.lower()
    host = _host_of(url) if url else None
    is_platform = bool(host) and any(_domain_suffix_match(host, p) for p in _PLATFORM_DOMAINS)
    is_registered = bool(host) and any(_domain_suffix_match(host, dom) for dom in _DOMAIN_MAP)
    源可信 = (host is None) or is_platform or is_registered
    # ①②申报/索引证券代码——不一致=硬失败(不回退)
    if index_code is not None:
        if str(index_code).strip().upper() == str(code).strip().upper():
            return True, "①②申报/索引证券代码严格一致", False, 源可信
        return False, "①②索引证券代码与五元组不一致(硬拦)", True, 源可信
    # ③页头公司名/证券代码(★仅可信源)
    if 源可信 and ((names and any(n in hl for n in names)) or _code_in_header(code, header)):
        return True, "③页头公司名/证券代码", False, 源可信
    # ④登记IR域名(非平台·归属==五元组代码)
    if host and not is_platform:
        for dom, (dcode, _ent) in _DOMAIN_MAP.items():
            if _domain_suffix_match(host, dom) and str(dcode).upper() == str(code).upper():
                return True, "④登记IR域名(%s·非平台)" % dom, False, 源可信
    return False, None, False, 源可信


def _z2h(x):
    """全角数字/记号→半角。"""
    return re.sub(r"[０-９]", lambda c: "0123456789"[ord(c.group()) - ord("０")], str(x)).replace("．", ".").replace("，", ",")


def parse_tanshin_ratio(text, metric_syns, w=None):
    """★★★轮217 GPT V7批准:日本決算短信サマリー表の増減率→方向+幅度。
    ★判据固定(不得改):△/▲=減·纯数字=増·0.0=持平·空白/－/取不到=None(不判断方向)。
    ★只表内取值(表头注記の直後320字以内)·方向と幅度は同一トークン由来·表外文字は一切見ない。
    返回 dict(方向/幅度/来源行文本/来源栏位/期间/增減率原文/方向匹配/幅度匹配) or None。"""
    t = str(text or "")
    # ① 表头注記:「(…対前年同期…増減率)」or「(…前期…増減率)」同一括弧内(★方向の期間根拠)
    hm = re.search(r"[（(][^）)]{0,40}?(対?前年同(?:期|四半期)|対?前期)[^）)]{0,20}?増減率[^）)]{0,10}?[）)]", t)
    if not hm:
        hm = re.search(r"[（(][^）)]{0,40}?増減率[^）)]{0,20}?(前年同期|前期)[^）)]{0,10}?[）)]", t)
    if not hm:
        return None
    period = "対前年同期" if "前年" in hm.group(0) else "対前期"
    tail = t[hm.end(): hm.end() + 320]          # ★表領域上限320字(表外の「総資産増加」等に物理的に届かない)
    # ② 指標名ヘッダ(注記直後~最初の「百万円」)→ 対象指標の列インデックス
    u = tail.find("百万円")
    header_seg = tail[:u] if 0 < u < 200 else tail[:120]
    order = re.findall(r"売上高|売上収益|営業利益|経常利益|税引前[^\s　]*利益|親会社株主に帰属する[^\s　]*利益|純利益", header_seg)
    idx = None
    for i, nm in enumerate(order):
        if any((str(m) in nm or nm in str(m)) for m in metric_syns):
            idx = i
            break
    if idx is None:
        return None                              # 指標が表頭に無い→不判断
    # ③ 最初のデータ行(年月期で始まる)→ ラベル以降の数値トークン
    dm = re.search(r"(?:19|20)[0-9０-９]{2}年[0-9０-９]{1,2}月期(?:第[0-9０-９一二三四]{1,2}四半期|通期|中間期|年度)?", tail)
    if not dm:
        return None
    row_label = dm.group(0)
    after = tail[dm.end(): dm.end() + 140]
    toks = re.findall(r"[△▲]?\s*[0-9０-９][0-9０-９,，.．]*", after)
    ratio_pos = 2 * idx + 1                       # (値,増減率)ペア→増減率トークン位置
    if ratio_pos >= len(toks):
        return None                              # ★該当栏空白/取れず→不判断(方向を他所から借用しない)
    val_tok = toks[2 * idx].replace(" ", "")
    ratio_tok = toks[ratio_pos].replace(" ", "")
    # ④ 方向判定(GPT判据·方向と幅度は同一トークン由来·★A行B行跨りを構造的に排除)
    if ratio_tok in ("", "－", "-", "—", "―"):
        return None
    neg = ratio_tok[0] in "△▲"
    num = _z2h(re.sub(r"^[△▲]\s*", "", ratio_tok)).replace(",", "")
    try:
        amp = float(num) / 100.0
    except ValueError:
        return None
    direction = "持平" if amp == 0.0 else ("下降" if neg else "增长")
    res = {"方向": direction, "幅度": amp, "来源栏位": "第%d指標(増減率栏)" % (idx + 1), "期间": period,
           "增減率原文": ratio_tok, "指標值原文": val_tok, "来源行文本": (row_label + after[:50]).strip()[:80]}
    if w is not None:
        wamp = w.get("幅度")
        res["方向匹配"] = (str(w.get("方向") or "") == direction)
        res["幅度匹配"] = (wamp is not None and abs(float(wamp) - amp) < 0.0002)
    return res


def six_align(text, w, url=None, index_code=None, window=220):
    """★★★轮209改良版(a)『文档身份区 + 事实证据窗』:
    ★身份区(A-1):公司主体由 页头/证券代码/申报主体字段/登记IR域名 确认(须与五元组证券代码一致);无可信身份→退回【公司主体须进事实窗】。
    ★事实证据窗(A-2·★不放宽):指标+方向+精确幅度+期间【四项】仍必须同一±220窗口。
    ★A-4:平台域名(SEC/EDINET/TDnet)不确认主体。"""
    t = str(text or ""); tl = t.lower()
    ind_syn = [s.lower() for s in _IND_SYN.get(str(w.get("指标") or ""), [str(w.get("指标") or "")]) if s]
    direction = str(w.get("方向") or "")
    dir_syn = [s.lower() for s in (_DIR_UP if any(k in direction for k in ["增", "升", "涨", "up", "grow"]) else (_DIR_DOWN if direction else []))]
    per_syn = [s.lower() for s in _PER_SYN.get(str(w.get("期间") or ""), [str(w.get("期间") or "")]) if s]
    amp_pats = _pct_forms(w.get("幅度"))
    names = [n.lower() for n in _ENTITY_NAMES.get(str(w.get("实体")), [])]

    d = {}
    d["指标"] = any(_term_in(s, tl) for s in ind_syn)
    d["方向"] = any(_term_in(s, tl) for s in dir_syn)
    d["幅度"] = any(re.search(p, tl) for p, _ in amp_pats)
    d["期间"] = any(_term_in(s, tl) for s in per_syn)
    # ★A-2 事实证据窗:【指标+方向+幅度+期间】同一±220窗(★不含公司主体·不放宽)。记录窗口用于退回判定。
    d["四项事实同窗"] = False; _fact_win = None
    for m in re.finditer("|".join(re.escape(s) for s in ind_syn) or r"(?!x)x", tl):
        i = m.start(); win = tl[max(0, i - window):i + window]
        if (any(_term_in(s, win) for s in ind_syn) and any(_term_in(s, win) for s in dir_syn)
                and any(re.search(p, win) for p, _ in amp_pats) and any(_term_in(s, win) for s in per_syn)):
            d["四项事实同窗"] = True; _fact_win = win; break
    # ★留痕(B-1):默认散文式;若走表式兜底则改标記
    d["_事实路径"] = "散文式" if d["四项事实同窗"] else None
    # ★★★轮217 GPT V7批准:決算短信表式増減率兜底。★only在散文式四项同窗取不到时·且方向/幅度须与五元组一致(防造假)。
    if not d["四项事实同窗"]:
        _syns_raw = _IND_SYN.get(str(w.get("指标") or ""), [str(w.get("指标") or "")])
        tan = parse_tanshin_ratio(t, _syns_raw, w)
        if tan and tan.get("方向匹配") and tan.get("幅度匹配"):
            # 表式:指标(表頭)+方向(増減率符号)+幅度(同栏)+期间(表頭注記)同属一表格结构→同窗成立(GPT裁定B)
            d["方向"] = True
            d["四项事实同窗"] = True
            d["_事实路径"] = "決算短信表式"
            d["_表式证据"] = {"来源行文本": tan["来源行文本"], "来源栏位": tan["来源栏位"],
                            "期间": tan["期间"], "增減率原文": tan["增減率原文"], "指標值": tan["指標值原文"]}
    # ★A-1 身份区:确认公司主体
    conf, method, hard_fail, 源可信 = confirm_identity(text, w.get("实体"), url=url, index_code=index_code)
    if hard_fail:
        conf = False   # ★⑧index证券代码不一致=硬失败·不回退
    elif not conf:
        # ★退回原规则:无可信身份→公司主体必须进【事实窗】·★但仅在【源可信】时(⑨未登记域名不得凭页头/窗内名)
        conf = 源可信 and bool(_fact_win) and (names and any(n in _fact_win for n in names))
        method = ("退回·公司主体进事实窗" if conf else None)
    d["公司主体确认"] = bool(conf); d["身份确认方式"] = method
    # 兼容旧键(自包含/对抗用):六项同窗共现 = 四项事实同窗 且 身份确认
    d["六项同窗共现"] = d["四项事实同窗"] and d["公司主体确认"]
    全对齐 = d["指标"] and d["方向"] and d["幅度"] and d["期间"] and d["四项事实同窗"] and d["公司主体确认"]
    return 全对齐, d


def _fetch(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    return urllib.request.urlopen(req, timeout=timeout, context=_CTX)


def verify_source(url, wuyuanzu=None, for_A=True, timeout=12, index_code=None):
    """★真发HTTP(正常证书)+身份区/事实证据窗+来源等级。合格条件:2xx·证书有效·(A档:来源≤二级)·身份确认+四项事实同窗。
    ★index_code=TDnet/J-Quants/SEC申报主体证券代码(平台外带入·确认主体)。★任一不满足→不合格(不降级/不待核)。"""
    t0 = time.time()
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    ent = (wuyuanzu or {}).get("实体")
    lvl, lvl_name = source_level(url, entity=ent)
    rec = {"验证时刻": ts, "url": url, "五元组": wuyuanzu, "验证器版本": VERIFIER_VERSION, "来源等级": lvl, "来源等级名": lvl_name}
    # ★C:A档只接受一级/二级
    if for_A and lvl > 2:
        rec["合格"] = False; rec["不合格原因"] = "来源等级%d(%s)·A档只接受一级/二级" % (lvl, lvl_name)
        _write_ledger(_key(url, wuyuanzu), rec); return rec
    try:
        r = _fetch(url, timeout=timeout)
        status = getattr(r, "status", None) or r.getcode()
        final = r.geturl()
        # ★B-4:重定向后最终域名重新核等级·取更严(worst)
        flvl, flvl_name = source_level(final, entity=ent)
        rec["最终URL"] = final; rec["最终URL等级"] = flvl
        if for_A and flvl > 2:
            rec["状态码"] = status; rec["响应时间秒"] = round(time.time() - t0, 3)
            rec["合格"] = False; rec["不合格原因"] = "重定向后最终域名等级%d(%s)·A档只接受一级/二级" % (flvl, flvl_name)
            _write_ledger(_key(url, wuyuanzu), rec); return rec
        raw = r.read(4000000)
        # ★轮209 fetch层适配:PDF(EDINET/IR决算短信常为PDF)→pypdf提取正文;否则按HTML/文本。★不动六项对齐/域名/TLS/边界。
        ctype = (r.headers.get("Content-Type") or "").lower()
        if raw[:5] == b"%PDF-" or "application/pdf" in ctype:
            try:
                import io as _io
                from pypdf import PdfReader as _PR
                text = " ".join((p.extract_text() or "") for p in _PR(_io.BytesIO(raw)).pages)
                rec["源格式"] = "PDF(pypdf提取)"
            except Exception as _pe:
                text = ""; rec["源格式"] = "PDF(提取失败:%s)" % str(_pe)[:40]
        else:
            text = raw.decode("utf-8", errors="replace"); rec["源格式"] = "HTML/文本"
        rec["状态码"] = status; rec["响应时间秒"] = round(time.time() - t0, 3)
        if not (200 <= int(status) < 300):
            rec["合格"] = False; rec["不合格原因"] = "HTTP %s(非2xx)" % status
        elif wuyuanzu:
            aligned, detail = six_align(text, wuyuanzu, url=final, index_code=index_code)
            rec["六项对齐"] = detail
            if aligned:
                rec["合格"] = True
            else:
                不齐 = [k for k, v in detail.items() if not v]
                rec["合格"] = False; rec["不合格原因"] = "六项对齐不全(缺:%s)·跨事实错配防护" % 不齐
        else:
            rec["合格"] = False; rec["不合格原因"] = "未提供五元组·无法做六项对齐"
    except ssl.SSLCertVerificationError as e:
        rec["状态码"] = None; rec["响应时间秒"] = round(time.time() - t0, 3)
        rec["合格"] = False; rec["不合格原因"] = "★证书核验失败:%s(不降级)" % str(e)[:60]
    except urllib.error.HTTPError as e:
        rec["状态码"] = e.code; rec["合格"] = False; rec["不合格原因"] = "HTTPError %s" % e.code
    except Exception as e:
        rec["状态码"] = None; rec["响应时间秒"] = round(time.time() - t0, 3)
        rec["合格"] = False; rec["不合格原因"] = "%s:%s" % (type(e).__name__, str(e)[:80])
    _write_ledger(_key(url, wuyuanzu), rec)
    return rec


def status():
    return {"验证器可用": AVAILABLE, "版本": VERIFIER_VERSION, "台账条数": len(_LEDGER),
            "证书核验": "check_hostname=True·CERT_REQUIRED(正常)", "六项对齐": True,
            "说明": "联网验证器·六项对齐(防跨事实错配)+正常证书+来源等级(A档只一级/二级)。自报标志不读。"}


def _selftest():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("═══ verifier v2.0 · 六项对齐(轮206修B-1~B-4) · GPT五攻击纯逻辑测 ═══")
    W = {"实体": "US.ACLS", "指标": "订单", "方向": "增长", "幅度": 0.20, "期间": "同比"}
    allok = True

    def chk(name, cond):
        nonlocal allok
        allok = allok and cond
        print("%s %s" % ("✅" if cond else "❌", name))

    # 合规:六项真共现→对齐
    aligned = "Axcelis Technologies reported 订单 增长 20% 同比 (year-over-year)."
    a, d = six_align(aligned, W); chk("合规六项同窗共现→对齐=True %s" % d, a)
    # ★B-1:散落500字符(公司主体/期间远离)→不对齐
    scattered = "Axcelis" + ("x" * 500) + "同比" + ("y" * 500) + "订单 增长 20%"
    a1, d1 = six_align(scattered, W); chk("★B-1 散落500字符→六项同窗共现=%s(应False)" % d1.get("六项同窗共现"), not a1)
    # ★B-2:120%冒充20%→幅度不命中
    amp120 = "Axcelis 订单 增长 120% 同比"; a2, d2 = six_align(amp120, W)
    chk("★B-2 正文120%%·五元组20%%→幅度=%s(应False)" % d2.get("幅度"), not d2.get("幅度"))
    # ★B-3:update含up→方向不命中(词边界)
    upd = "Axcelis order update 20% year-over-year"
    a3, d3 = six_align(upd, {"实体": "US.ACLS", "指标": "订单", "方向": "增长", "幅度": 0.20, "期间": "同比"})
    chk("★B-3 'update'冒充'up'→方向=%s(应False)" % d3.get("方向"), not d3.get("方向"))
    # ★B-4:四个伪装域名→均判四级(不开A)
    fakes = ["https://evilsec.gov.attacker.com/x", "https://sec.gov.attacker.com/x",
             "https://ir.attacker.com/x", "https://investor.attacker.com/x"]
    lv = [source_level(u, entity="US.ACLS")[0] for u in fakes]
    chk("★B-4 四伪装域名等级=%s(应全4·不开A)" % lv, all(x == 4 for x in lv))
    # 严格边界正例:真SEC/真IR等级
    chk("真sec.gov=1·真axcelis.com(归属ACLS)=2·reuters=3", source_level("https://www.sec.gov/x")[0] == 1
        and source_level("https://ir.axcelis.com/x", entity="US.ACLS")[0] == 2 and source_level("https://reuters.com/x")[0] == 3)
    # ★★★A-3端到端:example.com+ACLS五元组→拦(联网)
    try:
        r = verify_source("https://example.com/", W); ok_a3 = (r.get("合格") is False)
        chk("★★★A-3联网:example.com+ACLS五元组→合格=%s(必须False)" % r.get("合格"), ok_a3)
    except Exception as e:
        print("   (A-3联网跳过:%s)" % str(e)[:40])
    print("═══ %s ═══" % ("★全过(B-1散落/B-2数值/B-3词边界/B-4域名伪装 五攻击全拦)" if allok else "★★有未达预期"))
    return 0 if allok else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
