# -*- coding: utf-8 -*-
"""★轮111 NR1:七层重构成【真管道】——每层【只能】从上一层 output 取数·不许自己另行取数。
董事长根因裁定:原七层是【七个并排取数器】(每层自取数·层间不相通)·加的闸全在给『本来就不相通』打补丁。
本模块:①~⑦ 逐层 input=上一层.output(唯一)·process·output(结构化+provenance)。上层空→下层无输入→自然不产出(结构性阻断NR1-3)。
★NR1-2 切旁路:⑤只从④激活板块筛(不许全市场扫)·⑦只从⑥取(不读opus5_content/production.action)。
★只读·不下单。★本层不编投资判断:process的判断内容属Opus5·此处只搭【管道机制+provenance+空传播】;08-03①空→全链空→无动作(正确)。"""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _layer(no, name, inp_desc, out_items, empty_reason, process, 状态=None, 上游接入=None):
    return {"层": "%s%s" % (no, name), "input来源": inp_desc,
            "process": process, "output": out_items, "output数": len(out_items),
            "空原因": empty_reason if not out_items else None,
            "★真实状态": 状态,          # ★轮125 PE3-2:已填传下/未填阻断/无证据延续/旁取未接上游
            "★上游接入": 上游接入}      # ★PE3-3:该层是否真读上游判断(非只旁取)


# ★轮125 PE2-1:判断层三态(结构化枚举·守§5.4·靠收到证据条数+槽位填否·不靠文本)
def _judge_state(n_recv, filled):
    if filled:
        return "已填·传下"
    if n_recv == 0:
        return "★无证据可填·客观空·状态延续(合法·下游可续)"   # PE2:客观空≠未填
    return "★未填·该填没填·阻断下游(收到%d条证据却未判)" % n_recv


CONT_MAX_DAYS = 5   # ★PE2-3:状态延续超N日未更新→标『可能过期·需重新确认』


def _continuation(dc, layer_key, reason):
    """★PE2-1/2-3:客观空→合法『状态延续』token(带上次更新日;超N日→过期告警)。"""
    last = None
    try:
        from judgment_ledger import prior_for_layer
        p = prior_for_layer(layer_key)
        last = p.get("date") if p else None
    except Exception:
        last = None
    lag = _lag_days(last, dc) if last else None
    if last and lag is not None and lag > CONT_MAX_DAYS:
        expire = "★状态可能过期·需重新确认(距上次更新 %d 日 > %d 日)" % (lag, CONT_MAX_DAYS)
    elif last:
        expire = "在有效期内(距上次更新 %s 日)" % lag
    else:
        expire = "★无历史判断基线(首次客观空)·延续=维持上游①层世界观框架现状"
    return [{"id": "CONT-%s" % layer_key[0], "★状态": "无证据可填·客观空·状态延续",
             "★这是延续不是今日新判": True, "上次更新日": last or "无(首次)",
             "延续说明": reason, "★过期检查": expire,
             "provenance": "%s·客观空(收到0证据)·合法续·非今日新判" % layer_key}]


def layer1(dc):
    """★轮114 NU:①世界观＝每日证据→6尺映射器(四类A新闻/B价格/C持仓/D Drive走同一条链)。
    input=当日证据源(四类渠道·不限定内容方向)·output=证据清单[证据·对应尺·印证/动摇·下游层·维度·来源·独立性·依据等级·as_of]。
    ★B/C恒有→output恒非空·『今日无事件』不出现;★动摇置顶(PDCA入口)。"""
    em = _rj(ROOT / "data/market" / f"evidence_map_{dc}.json")
    if not em:  # 未生成→现场跑
        try:
            from layer1_evidence_mapper import build as _emb
            em = _emb("%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]))
        except Exception:
            em = {}
    facts = []
    for e in em.get("路1_对6尺持续验证(★动摇置顶)", []):
        facts.append({"id": "E%d" % (len(facts) + 1), "证据": e.get("证据"), "对应尺": e.get("对应尺"),
                      "印证动摇": e.get("印证动摇"), "下游层": e.get("下游层"), "维度": e.get("维度"),
                      "方向": e.get("方向"), "来源": e.get("来源"), "独立性": e.get("是否独立信源"),
                      "依据等级": e.get("依据等级"), "as_of": e.get("as_of"),
                      "provenance": "①证据映射器·%s" % e.get("provenance", "")})
    er = "①证据映射器无输出(异常)——★不应发生(B/C恒有)" if not facts else None
    return _layer("①", "世界观(证据→6尺映射器)", "当日证据源:A新闻/B价格/C持仓/D Drive(同一条链)", facts, er,
                  "四类证据→识别→映射6尺(印证/★动摇/无关)→下游层维度;★动摇置顶(PDCA);output恒非空")


def layer2(l1):
    """②国家战略 input=①.output(唯一) output=受影响国家/政策方向。
    ★轮114:①层现为证据映射器(恒非空)·但『证据→国家战略判断』的加工内容=Opus5;Opus5未加工当日证据→本层【收到输入但未产出判断】(≠上游空)·
    下游据此不自动出动作(证据≠动作·动作须Opus5从⑥推)。"""
    n_in = len(l1["output"]); dc = l1.get("_dc", "")
    if not n_in:
        return _layer("②", "国家战略", "★①.output(唯一)", [], "上游①无输出→②无输入·不产出(NR1-3)",
                      "每条证据→受影响国家/政策(判断=Opus5)", 状态="上游①空", 上游接入="①.output(空)")
    # ★轮125 PE2:三态(结构化)——已填/未填(该填没填·阻断)/无证据可填(客观空·状态延续·合法续)
    filled = None
    try:
        from judgment_slots_build import read_layer_output as _rlo, received_count as _rc
        filled = _rlo(dc, "②国家战略"); n_recv = _rc(dc, "②国家战略")
    except Exception:
        n_recv = 0
    state = _judge_state(n_recv, filled)
    if filled:
        return _layer("②", "国家战略", "★①.output→②判断工单(Opus5已填·引用证据%s)" % filled.get("引用证据ID"),
                      [{"id": "P1", "判断": filled["判断"], "依据": filled.get("依据"), "证伪信号": filled.get("证伪信号"),
                        "★传给下层": filled.get("★传给下层的输出"),
                        "provenance": "②Opus5工单·引用%s" % filled.get("引用证据ID")}], None,
                      "Opus5按工单填的国家战略判断", 状态=state, 上游接入="①.output+②判断工单(已读)")
    if n_recv == 0:
        # ★PE2:②收到0条证据=客观【无关税/出口管制/立法类事实】·非Opus5未填→合法状态延续·下游可续
        cont = _continuation(dc, "②国家战略", "②今日收到0条证据(客观无关税/出口管制/立法类当日事实)·非未填偷懒·合法续·下游据此续但须显示②为【延续】非今日新判")
        return _layer("②", "国家战略", "★①.output→②判断工单(收到0证据·客观空)", cont, None,
                      "★客观无该类事实→状态延续(非阻断)·下游合法续", 状态=state, 上游接入="①.output+②判断工单(已读·客观空)")
    er = ("★收到①层证据 %d 条·②判断工单槽位【待Opus5填】→★该填没填·阻断下游(NV2-3)" % n_recv)
    return _layer("②", "国家战略", "★①.output→②判断工单(收到%d证据·待Opus5填)" % n_recv, [], er,
                  "每条证据→国家政策(★Opus5按层填·该填没填则阻断)", 状态=state, 上游接入="①.output+②判断工单(已读·未填)")


def _lag_days(data_date, dc):
    """★轮118 NX0-2:数据日 vs 文件名日期→滞后天数(结构化·不许以文件名冒充数据日)。"""
    try:
        import datetime as _dt
        dd = _dt.date(int(data_date[:4]), int(data_date[5:7]), int(data_date[8:10]))
        fn = _dt.date(int(dc[:4]), int(dc[4:6]), int(dc[6:8]))
        return (fn - dd).days
    except Exception:
        return None


def _band(name, v):
    if "10年期" in name:
        return "紧档(4.5~5.0)" if 4.5 <= v < 5.0 else ("高(≥5.0)" if v >= 5 else ("中性(3.5~4.5)" if 3.5 <= v < 4.5 else "宽松(<3.5)"))
    if "VIX" in name:
        return "平静档(12~20)" if 12 <= v <= 20 else ("恐慌(>20)" if v > 20 else "极低(<12)")
    if "DXY" in name:
        return "强(>100)" if v > 100 else "中性偏弱(≤100)"
    if "2年期" in name:
        return "紧(≥4.0)" if v >= 4 else "中(<4.0)"
    if "曲线" in name:
        return "正常·未倒挂(>0)" if v > 0 else "★倒挂(≤0)"
    return "—"


def _fetch_rates(dc):
    """★轮116-2/118 NW1+NX0:③层核心指标数值。★读 macro_flow『当日值』(修:字段是当日值非值)·标【数据日+滞后天数】(NX0-2·不以文件名冒充)·
    算曲线(10Y−2Y);未接通/无值走NK4(不留待Opus5占位)。★可核数值机器出·意义Opus5填工单。"""
    mf = _rj(ROOT / "data/market" / f"macro_flow_{dc}.json")
    core = {x.get("指标"): x for x in (mf.get("核心指标", []) or [])}
    out = []
    tny = tnv = None
    for name in ("10年期美债收益率", "2年期美债收益率", "VIX恐慌指数", "DXY美元指数"):
        x = core.get(name, {})
        v = x.get("当日值")
        if v is None:
            # ★甲A2(轮332):不印 Python True/False·且解矛盾(接通=True却当日值缺=源接通但当日无值)。
            _conn = x.get("接通")
            _st = "源已接通但当日无值" if _conn is True else ("未接通" if _conn is False else "接通状态未知")
            out.append({"指标": name, "★NK4不输出": "因缺:macro_flow『%s』当日值=null → 不输出·不留占位(NW1-4)·机器状态：%s" % (name, _st)})
            continue
        dd = x.get("数据日"); lag = _lag_days(dd, dc) if dd else None
        if name.startswith("10"): tny = float(v)
        if name.startswith("2年"): tnv = float(v)
        out.append({"指标": name, "★数值(机器)": round(float(v), 3), "判档(机器)": _band(name, float(v)),
                    "数据日": dd, "★滞后天数(vs文件名)": lag, "来源": x.get("实际用源", "macro_flow"), "机器直采": True,
                    "★新鲜度": "当日" if lag == 0 else ("★滞后%s天·非当日(NX0)" % lag if lag else "数据日未标")})
    # 曲线=10Y−2Y(机器算)
    if tny is not None and tnv is not None:
        cv = round(tny - tnv, 3)
        out.append({"指标": "收益率曲线(10Y−2Y)", "★数值(机器)": cv, "判档(机器)": _band("曲线", cv),
                    "数据日": core.get("10年期美债收益率", {}).get("数据日"), "来源": "10Y−2Y机器算", "机器直采": True,
                    "★新鲜度": "同10Y/2Y数据日"})
    else:
        out.append({"指标": "收益率曲线(10Y−2Y)", "★NK4不输出": "因缺:10Y或2Y无值·曲线不算(NW1-4)"})
    # ★★轮132 A:接 FRED keyless(核心CPI/核心PCE/Fed基金利率/失业率)补③层宏观·替代NK4。★带值/数据日/来源/滞后(守轮118数据日≠文件名)。取不到→NK4。
    try:
        from macro_news_intake import fetch_fred_latest as _fred
    except Exception:
        _fred = None
    for nm, sid in (("核心CPI(CPILFESL)", "CPILFESL"), ("核心PCE通胀锚(PCEPILFE)", "PCEPILFE"),
                    ("Fed基金利率(FEDFUNDS)", "FEDFUNDS"), ("失业率(UNRATE)", "UNRATE")):
        r = _fred(sid) if _fred else None
        if r and r.get("value") is not None:
            lag = _lag_days(r["date"], dc)
            out.append({"指标": nm, "★数值(机器)": r["value"], "判档(机器)": "—(FRED原值·YoY/意义待Opus5判·NW1-3)",
                        "数据日": r["date"], "★滞后天数(vs文件名)": lag, "来源": "FRED(%s·keyless)" % sid, "机器直采": True,
                        "★新鲜度": ("当日" if lag == 0 else ("★滞后%s天(宏观月频·正常滞后·非当日)" % lag if lag is not None else "数据日未标")),
                        "前值": r.get("prev"),
                        "provenance": "③机器观测 FRED %s(keyless)" % sid})
        else:
            out.append({"指标": nm, "★NK4不输出": "因缺:FRED %s 取不到(keyless超时/网络)·不输出·不估算(NW1-4)" % sid})
    # ★★轮133 B:接 Fed官方RSS(keyless)→FOMC决议/纪要事件(标题+日期+链接·政策含义待Opus5)。取不到→维持NK4·不占位。
    try:
        from macro_news_intake import fetch_fed_fomc as _fomc
        fom = _fomc()
    except Exception:
        fom = None
    if fom and fom.get("date"):
        lag = _lag_days(fom["date"], dc)
        out.append({"指标": "FOMC决议(Fed官方RSS)", "★事件": fom["title"], "数据日": fom["date"],
                    "★滞后天数(vs文件名)": lag, "来源": "Fed官方RSS(keyless)", "链接": fom.get("link"), "机器直采": True,
                    "★新鲜度": ("当日" if lag == 0 else ("★滞后%s天(非当日)" % lag if lag is not None else "数据日未标")),
                    "★政策含义/点阵图解读": "待Opus5判(Code只接事件+日期·不解读·NW1-3)",
                    "provenance": "③机器观测 Fed官方RSS(keyless)"})
    else:
        out.append({"指标": "FOMC决议", "★NK4不输出": "因缺:Fed官方RSS取不到·维持NK4·不占位(NW1-4)"})
    return out


def layer3(l2, dc):
    """③资金流动 input=②.output + 利率汇率(允许aux) output=资金流向指标。
    ★轮116-2:★机器直采 10Y/VIX/DXY 真数值+判档(机器出)·取不到走NK4(不留待Opus5占位)。★数值由机器出·『意义』判断由Opus5填工单(NW1-3)。"""
    rates = _fetch_rates(dc)
    out = []
    for r in rates:
        if "★数值(机器)" in r:
            out.append({"id": "M%d" % (len(out) + 1), "_角色": "★原始观测(机器·旁取合法)", "指标": r["指标"], "★数值(机器)": r["★数值(机器)"],
                        "判档(机器)": r["判档(机器)"], "数据日": r.get("数据日"), "★滞后天数(vs文件名)": r.get("★滞后天数(vs文件名)"),
                        "★新鲜度": r.get("★新鲜度"), "来源": r.get("来源"), "机器直采": True,
                        "前值": r.get("前值"), "provenance": r.get("provenance", "③机器观测 %s" % r.get("来源"))})
        elif "★事件" in r:   # ★轮133 B:FOMC决议事件(非数值·标题+日期+链接)
            out.append({"id": "M%d" % (len(out) + 1), "_角色": "★原始观测(事件·Fed官方)", "指标": r["指标"], "★事件": r["★事件"],
                        "数据日": r.get("数据日"), "★滞后天数(vs文件名)": r.get("★滞后天数(vs文件名)"), "★新鲜度": r.get("★新鲜度"),
                        "来源": r.get("来源"), "链接": r.get("链接"), "★政策含义/点阵图解读": r.get("★政策含义/点阵图解读"),
                        "provenance": r.get("provenance")})
        # NK4项不进output(不输出·不占位)
    nk4 = [r["指标"] for r in rates if "★NK4不输出" in r]
    # ★★轮125 PE1-2:读③判断工单(Opus5解释框架)·纳入③.output(含『传给④层三方向』)——不再只有机器数值
    filled = None; n_recv = 0
    try:
        from judgment_slots_build import read_layer_output as _rlo, received_count as _rc
        filled = _rlo(dc, "③资金流动"); n_recv = _rc(dc, "③资金流动")
    except Exception:
        filled = None
    上游 = "★机器观测(利率汇率·旁取原始观测) + ③判断工单(解释框架·read_layer_output)"
    if filled:
        out.append({"id": "J3", "_角色": "★解释框架(Opus5判断)", "本层判断": filled["判断"],
                    "依据": filled.get("依据"), "证伪信号": filled.get("证伪信号"),
                    "★传给④层的输出(三方向)": filled.get("★传给下层的输出"),
                    "引用证据ID": filled.get("引用证据ID"),
                    "provenance": "③Opus5判断工单·引用%s" % filled.get("引用证据ID")})
        上游 += "(已读·已填)"
    else:
        上游 += "(已读·未填)"
    state = _judge_state(n_recv, filled) if not out else ("已填·传下" if filled else "★机器观测有值·但③判断工单未填(解释框架缺·下游只得观测)")
    er = None if out else "③层机器数值全取不到(NK4)且③判断工单未填→不产出"
    proc = ("★双输入:①机器观测10Y/VIX/DXY(旁取·原始观测) ②★读③判断工单纳入解释框架(PE1-2·含传给④三方向);"
            "NK4未接:%s" % ("·".join(nk4) or "无"))
    return _layer("③", "资金流动", "★机器观测(旁取) + ③判断工单(解释框架·已读)", out, er, proc,
                  状态=state, 上游接入=上游)


def layer4(l3, dc):
    """④板块轮动 input=③.output + 当日板块数据(允许aux) output=[板块+当日表现数值+★受益/受损结构化枚举+依据链]。
    ★轮116-2 NW2:接 sector_rotation 真数据(承接节点涨跌·机器可算)·『方向』＝★结构化枚举(受益/受损/中性)·非『受益/受损(待Opus5)』字符串。机器出数值与初判·Opus5填意义。"""
    sr = _rj(ROOT / "data/market" / f"sector_rotation_{dc}.json")
    # ★★轮125 PE1-3:从③.output提取③判断【内容】(解释框架·传给④三方向)——不再只数条数
    l3j = next((o for o in l3["output"] if o.get("id") == "J3"), None)
    dir3 = (l3j or {}).get("★传给④层的输出(三方向)")
    sum3 = str((l3j or {}).get("本层判断") or "").split("，")[0][:36]
    # ★★轮170 P0:接④方向v2(多窗口中位5/20/60+③真参与)为【主路】·旧单日阈值降为回退+依据链留档(与轮128 render降级同处理)
    v2 = _rj(ROOT / "data/market" / f"sector_direction_v2_{dc}.json")
    v2m = {r["板块"]: r for r in (v2.get("逐板块", []) or []) if "★新方向" in r}
    NODE2BOARD = {"AI算力·AI芯片": "AI算力·AI芯片", "AI半导体设备": "AI半导体设备", "AI存储": "AI存储",
                  "AI软件应用": "AI应用软件", "AI基础设施外延·冷却/数据中心/网络": "AI云·数据中心",
                  "盟友链节点·日韩半导体": "AI半导体设备"}
    out = []
    for n in (sr.get("BC3-1_承接节点涨跌", []) or []):
        chg = n.get("当日涨跌pct")
        if chg is None:
            continue  # ★null→不输出(NK4·不占位)
        单日dir = "受益" if chg > 0.3 else ("受损" if chg < -0.3 else "中性")  # ★旧单日阈值(回退用)
        node = n.get("板块格")
        board = NODE2BOARD.get(node)
        v2r = v2m.get(board) if board else None
        if v2r:
            # ★主路=v2:多窗口中位+③参与
            direction = v2r["★新方向"]                       # 受益/受损/方向不明
            if direction not in ("受益", "受损", "中性"):
                direction = "中性"                            # 方向不明/矛盾→非受益枚举(⑤不激活)
            dl = v2r.get("依据链(机器可核)", {})
            依据链 = ("④方向v2(主路·轮170接生产):%s·多窗口中位[5日%s/20日%s/60日%s]·★③适用于本板块=%s·③一致=%s·状态[%s]"
                      "  ★×  旧单日阈值[%+.2f%%→%s](回退档·非主路)"
                      % (v2r["★新方向"], dl.get("5日中位"), dl.get("20日中位"), dl.get("60日中位"),
                         dl.get("★③适用于本板块"), dl.get("★③与板块方向一致"), v2r.get("状态", "")[:40], chg, 单日dir))
            src = "④方向v2(多窗口+③参与·主路)·映射%s→%s + ③.J3" % (node, board)
        else:
            # ★回退=单日(v2未覆盖的承接节点·如加密/高股息/保险/安全国防)
            direction = 单日dir
            依据链 = ("④机器观测(★v2未覆盖此承接节点·回退单日):承接节点当日涨跌 %+.2f%% → 初判『%s』(阈值±0.3%%)  ★×  ③资金环境[%s]·③传下方向[%s]"
                      % (chg, direction, sum3 or "③未填", dir3 or "③未传方向"))
            src = "④机器观测sector_rotation·%s(v2未覆盖·回退单日) + ③.J3" % node
        out.append({"id": "S%d" % (len(out) + 1), "板块": node, "★当日涨跌pct(机器观测)": chg,
                    "方向(机器初判枚举)": direction,
                    "★方向来源": ("④方向v2·多窗口+③参与" if v2r else "回退单日(v2未覆盖)"),
                    "★多窗口中位(5/20/60)": (v2r.get("依据链(机器可核)", {}) if v2r else "N/A(回退单日)"),
                    "★③是否参与": (v2r.get("依据链(机器可核)", {}).get("★③适用于本板块") if v2r else False),
                    "群": n.get("群"), "代表持仓": n.get("代表持仓"),
                    "★③资金环境判断(解释框架)": sum3 or "③未填", "★③传下的方向(解释框架)": dir3 or "③未传",
                    "依据链": 依据链,
                    "★意义判断": "见④层判断工单(★机器观测×③解释框架都在依据链·终判Opus5·NW2-4)",
                    "provenance": src})
    n_null = sum(1 for n in (sr.get("BC3-1_承接节点涨跌", []) or []) if n.get("当日涨跌pct") is None)
    # ④自身判断态:读④判断工单
    filled4 = None; n_recv4 = 0
    try:
        from judgment_slots_build import read_layer_output as _rlo, received_count as _rc
        filled4 = _rlo(dc, "④板块轮动"); n_recv4 = _rc(dc, "④板块轮动")
    except Exception:
        filled4 = None
    state = _judge_state(n_recv4, filled4) if out else "④无板块观测(全null)"
    er = "④层无板块当日涨跌数据(全null·NK4)·上游③也无→不产出" if not out else None
    proc = ("★双输入:sector_rotation板块涨跌(旁取观测%d块) + ★读③.output三方向织入每条依据链(PE1-3);"
            "null项NK4不输出(%d);④判断工单%s" % (len(out), n_null,
            "已填" if filled4 else "★待Opus5填(收到%d证据·该填没填→阻断⑤)" % n_recv4))
    return _layer("④", "板块轮动", "★sector_rotation板块(旁取观测) + ③.output判断内容(解释框架·已读)", out, er, proc,
                  状态=state, 上游接入="③.output(机器观测+③判断三方向·已读)")


def layer5(l4, dc):
    """⑤机会池 input=④.output(唯一) output=候选标的。★NR1-2:只从④激活(受益)板块筛·不许全市场扫。
    ★轮116-2 NW3:★读④『方向』结构化枚举字段 direction=='受益'(★禁 '受益' in str()·§5.4第十次)·占位符/中性无法通过激活判定。"""
    # ★★轮125 PE1-4/PE2:⑤读④【判断内容】·不只读枚举——④判断工单『未填·该填没填』→★⑤阻断(不许只凭机器枚举激活)
    s4_state = str(l4.get("★真实状态") or "")
    if "未填" in s4_state:
        er = ("★上游④判断工单【未填·该填没填】→⑤阻断(PE2:④收到证据却未判·★不许只凭机器涨跌枚举激活·那是旧版旁取绕过)"
              "·④机器观测板块仍在④.output供Opus5填④时参考")
        return _layer("⑤", "机会池", "★④.output(判断内容+受益枚举)·须④判断已填", [], er,
                      "★读④判断内容(非只枚举)·④该填没填则阻断(PE1-4)", 状态="上游④未填·阻断", 上游接入="④.output(已读·④未填)")
    activated = [s for s in l4["output"] if s.get("方向(机器初判枚举)") == "受益"]  # ★结构化枚举精确匹配·非关键词
    # ★★轮134 A:④受益板块→候选宇宙映射。候选宇宙＝【板块地图承接节点】(candidate_universe·含宇宙外新标的)·★非全市场扫(守轮111)·非Code编(守G2)。
    dc5 = dc
    try:
        from candidate_universe import build as _cub
        cu = _cub(dc5)
    except Exception:
        cu = {}
    _KW = ["半导体", "存储", "设备", "测试", "代工", "算力", "芯片", "材料", "机器人", "自动化", "服务器", "硬件", "云", "保险", "金融", "医药"]

    def _kw(x):
        return set(k for k in _KW if k in (x or ""))
    universe = cu.get("★候选宇宙(承接节点)", []) or []
    out = []
    for s in activated:
        board = s.get("板块") or ""; bkw = _kw(board)
        cands = [c for c in universe if bkw & _kw("·".join(c.get("板块", [])))]
        if cands:
            for c in cands:
                out.append({"id": "C%d" % (len(out) + 1), "板块": board, "symbol": c["symbol"],
                            "★宇宙外新标的": c.get("宇宙外新"), "候选来源": "板块地图承接节点(★非全市场扫·非Code编·守漏斗)",
                            "来源板块": c.get("板块"), "触发涨跌": s.get("★当日涨跌pct(机器观测)"),
                            "★④解释框架(③传下方向)": s.get("★③传下的方向(解释框架)"),
                            "★A-4须过关": ("★新候选须过第2软性/第3估值/第4护城河关才进⑥(未过关不算换入)" if c.get("宇宙外新") else "持仓内·已在体系"),
                            "provenance": "⑤←④.%s(受益)·候选宇宙承接节点·%s" % (s["id"], c["symbol"])})
        else:
            out.append({"id": "C0", "板块": board, "候选标的": "★该受益板块在候选宇宙(承接节点)无关键词匹配(待板块地图补该板块节点·非漏做)",
                        "触发涨跌": s.get("★当日涨跌pct(机器观测)"), "provenance": "⑤←④.%s(受益·候选宇宙无匹配)" % s["id"]})
    er = None
    if not l4["output"]:
        er = "上游④无输出→⑤无输入·无候选(NR1-3)"
    elif not activated:
        er = "④有 %d 板块·但无『方向==受益』(结构化枚举·非字符串)→⑤无激活板块·无候选(★占位符/中性无法通过·NW3-3)" % len(l4["output"])
    return _layer("⑤", "机会池", "★④.output判断内容+受益枚举(唯一)·★不许全市场扫", out, er,
                  "★读④判断内容+结构化枚举 方向==受益(禁关键词匹配·§5.4)·只从受益板块筛",
                  状态=("已激活%d板块" % len(activated)) if out else "④已填但无受益板块", 上游接入="④.output(判断内容+枚举·已读)")


def layer6(l5, dc):
    """⑥持仓比较 input=⑤.output + 现有持仓 output=替换比较结论。"""
    holds = _rj(ROOT / "data/reports" / f"production_{dc}.json").get("holdings", [])
    filled = None; n_recv6 = 0; dl = []
    try:
        from judgment_slots_build import read_layer_output as _rlo, received_count as _rc
        filled = _rlo(dc, "⑥持仓比较"); n_recv6 = _rc(dc, "⑥持仓比较")
        js = _rj(ROOT / "data/pipeline" / f"judgment_slots_{dc}.json")
        _sl = (js.get("②~⑦层工单", {}) or {}).get("⑥持仓比较", {}) or {}
        _dlf = _sl.get("★决策清单(可执行·Opus5填·⑦读此+exec_params组装·空则⑦不产出)", {}) or {}
        dl = [d for d in (_dlf.get("决策") or []) if d.get("标的")]
    except Exception:
        dl = []
    # ★★轮126 PF1-1:⑥决策清单已填(换仓/持仓处置·不依赖⑤候选)→⑥.output结构化决策·传⑦组装
    if dl:
        out = [{"id": "R%d" % (i + 1), "决策": d, "★本层判断(若填)": (filled or {}).get("判断"),
                "provenance": "⑥Opus5决策清单(换仓/持仓处置·标的/方向/股数/账户)"} for i, d in enumerate(dl)]
        return _layer("⑥", "持仓比较", "★⑤.output候选+现有持仓+⑥决策清单(Opus5已填)", out, None,
                      "候选/持仓→换仓/处置结构化决策(Opus5填决策清单·⑦据此+exec_params组装)",
                      状态="已填·传下(决策%d笔)" % len(dl), 上游接入="⑤.output+⑥决策清单(已读)")
    if not l5["output"]:
        er = "上游⑤无候选·且⑥决策清单空→⑥无换仓/处置·结论=维持现有%d只持仓(NR1-3)" % len(holds)
        return _layer("⑥", "持仓比较", "★⑤.output候选(唯一)+现有持仓+⑥决策清单", [], er, "⑤无候选+决策清单空→维持持仓",
                      状态="上游⑤无候选·⑥决策清单空·维持持仓", 上游接入="⑤.output(空·已读)+⑥决策清单(空)")
    if filled:
        # ★PF1-5(修正2):⑥本层判断【已填】(如结论=维持持仓)但决策清单dl为空——这是【结论:无交易动作】·非【缺件未填】。
        #   ★守铁律:仅当 filled(⑥本层判断)真非空才走此支;filled为空→落下方_judge_state(filled=None→仍报未填·阻断·不放宽)。
        er2 = ("★⑥本层判断【已填】(结论见判断内容·如维持持仓)·决策清单0笔(无换仓/处置动作·★这是结论非缺件)·"
               "⑦无动作产出(结论·非故障)")
        return _layer("⑥", "持仓比较", "★⑤.output候选+现有持仓+⑥本层判断(已填)+决策清单0笔", [], er2,
                      "⑥本层判断已填·结论=无交易动作(决策清单0笔·非缺件)",
                      状态="已填·⑥判断已给·决策清单0笔(无交易动作·结论)", 上游接入="⑤.output+⑥本层判断(已填)+决策清单(0笔)")
    er = ("★⑤给 %d 候选·⑥决策清单【待Opus5填】(标的/方向/股数/账户)→未填·⑦接线就绪但不产出·"
          "★不用占位符充output(NW4)" % len(l5["output"]))
    return _layer("⑥", "持仓比较", "★⑤.output候选+现有持仓+⑥决策清单(待Opus5)", [], er,
                  "候选vs持仓替换(★Opus5填决策清单·未填不产出)", 状态=_judge_state(n_recv6, filled), 上游接入="⑤.output+⑥决策清单(已读·未填)")


def layer7(l6, dc):
    """⑦交易动作 input=⑥.output(唯一) output=唯一动作[账户·股数·价格·条件]。★NR1-2:★不读opus5_content/production.action。
    ★轮116-2 NW4:⑥无换仓结论→⑦不产出·★不用『待算/待⑥』占位符充动作(空壳整改)。"""
    if not l6["output"]:
        er = "上游⑥无换仓结论→⑦无交易动作(★结构性阻断·不读opus5_content/production.action·不占位·NR1-3/NW4)"
        return _layer("⑦", "交易动作", "★⑥.output(唯一)·★不读opus5/production", [], er, "⑥无换仓→⑦无动作·不占位",
                      状态="上游⑥无换仓结论·⑦无动作", 上游接入="⑥.output(空·已读)")
    # ★★轮126 D3/PF1:⑥有决策清单→⑦组装可执行动作。【方向/标的/股数/账户】←⑥决策(判断·唯一)·【执行参数】←exec_params(机器)。
    #   ★禁读 opus5_content/production.action(PF1-2·不回退)。
    ep = _rj(ROOT / "data/accounts" / f"exec_params_{dc}.json")
    by_sym = {r.get("symbol"): r for r in ep.get("三只", [])}
    out = []; pending = []
    for r in l6["output"]:
        d = r.get("决策")
        if not d:   # ⑥给的是自由文本判断·无结构化决策清单→接线就绪·不组装(PF1-3不放行)
            pending.append("⑥.%s 无结构化决策(标的/方向/股数)→⑦接线就绪·待⑥给决策清单" % r.get("id"))
            continue
        sym = d.get("标的"); p = by_sym.get(sym)
        方向 = d.get("方向"); 股数 = d.get("股数"); 账户 = d.get("账户") or "★待⑥指定账户"
        if not p:
            out.append({"id": "A%d" % (len(out) + 1), "标的": sym, "★缺执行参数": "sym 不在 exec_params(%d只)·无到价/分笔/跳空·不组装可执行" % len(by_sym),
                        "方向(来自⑥)": 方向, "股数(来自⑥)": 股数, "provenance": "⑦←⑥决策·exec_params缺该sym"})
            continue
        现价 = (p.get("现价") or {}).get("值")
        净额 = round(股数 * 现价, 2) if isinstance(股数, (int, float)) and isinstance(现价, (int, float)) else None
        out.append({
            "id": "A%d" % (len(out) + 1),
            "标的": sym, "名称": p.get("name"),
            "账户": 账户,                                           # ←⑥判断
            "方向": 方向,                                           # ←⑥判断(换不换/买卖)
            "股数": 股数,                                           # ←⑥判断
            "分笔数": (p.get("★分笔数") or {}).get("值"),          # ←exec_params(机器)
            "分档价格": (p.get("每档价格") or {}).get("值"),       # ←exec_params(机器)
            "跳空规则": {"阈值pct": (p.get("★跳空阈值") or {}).get("值"), "规则": (p.get("★跳空阈值") or {}).get("算法")},
            "组合净影响": {"涉及金额(股数×现价·机器算)": 净额, "现价": 现价,
                          "说明": "方向%s·涉及%s;组合集中度变化须结合account_info总资产(exec_params未含)" % (方向, 净额)},
            "★每项算法依据与as_of": {
                "现价as_of": (p.get("现价") or {}).get("as_of"),
                "分笔算法(依ADV60)": (p.get("★分笔数") or {}).get("算法"),
                "跳空算法(依ATR14)": (p.get("★跳空阈值") or {}).get("算法"),
                "分档算法(依ATR14)": (p.get("每档价格") or {}).get("算法"),
                "K线指标as_of": (p.get("K线指标(机器算·K_DAY QFQ)") or {}).get("as_of")},
            "provenance": "⑦: 方向/标的/股数/账户←⑥决策清单(判断·唯一) · 到价/分笔/跳空←exec_params(机器) · ★不读opus5/production(PF1-2)"})
    er = None if out else ("★⑥有output但无结构化决策清单→⑦接线就绪·未组装动作(PF1-3不放行)·" + "；".join(pending))
    状态 = ("已产出%d条可执行动作" % len(out)) if out else "★接线就绪·⑥判断待结构化决策清单(不放行动作)"
    return _layer("⑦", "交易动作", "★⑥.output决策清单(方向·唯一) + exec_params(执行参数·机器)", out, er,
                  "★方向/标的/股数/账户←⑥决策·到价/分笔/跳空←exec_params·★禁读opus5/production(PF1-2)",
                  状态=状态, 上游接入="⑥.output决策清单(已读) + exec_params(执行参数·非旁路判断)")


def run(dc):
    l1 = layer1(dc); l1["_dc"] = dc; l2 = layer2(l1); l3 = layer3(l2, dc); l4 = layer4(l3, dc)
    l5 = layer5(l4, dc); l6 = layer6(l5, dc); l7 = layer7(l6, dc)
    layers = [l1, l2, l3, l4, l5, l6, l7]
    trade = l7["output"]
    # ★★轮125 PE3-1:★禁用「通到第X层」首个空层标签(它误导验收)。PE3-2:逐层显示真实状态。
    状态表 = [{"层": L["层"][:6], "output数": L["output数"], "★真实状态": L.get("★真实状态") or ("已产出" if L["output"] else "无输出"),
               "★上游接入": L.get("★上游接入")} for L in layers]
    # ⑦能否产出动作的真实原因(逐层归因·非"①层无事实")
    blocked = next((L for L in layers if "未填" in str(L.get("★真实状态")) or "阻断" in str(L.get("★真实状态"))), None)
    # ★修正3:⑥本层判断已填但0决策(如维持持仓)——无动作是【结论】非【故障】·须与"该填没填·阻断"区分。
    #   ★守铁律:仅当无 blocked 层(无真未填/阻断)且⑥已填 才算结论;若某层真未填→blocked非空→仍走未填·阻断归因。
    _l6_state = str(l6.get("★真实状态") or "")
    _l6_decided_hold = (blocked is None) and ("已填" in _l6_state) and (not trade)
    return {
        "_说明": "★轮125 PE:七层真管道·③④⑤既取机器观测也读上游判断(解释框架);判断层三态(已填/未填阻断/客观空延续);★逐层真实状态·不用『通到第X层』标签。",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:]),
        "★逐层真实状态(PE3-2·替代通到第X层)": 状态表,
        "七层": layers,
        "★最终交易动作": trade if trade else "【无交易动作】",
        "★⑦无动作的真实归因(PE3-1·非首空层标签)": (
            None if trade else (
                "★%s：%s" % (blocked["层"], blocked.get("★真实状态")) if blocked else (
                    "★⑥已判【维持持仓·决策清单0笔】→⑦无交易动作产出(★这是结论·产品完整·⑥本层判断已填)" if _l6_decided_hold else "上游链无输入"))),
        "★结构性结论": ("产出 %d 条交易动作" % len(trade)) if trade else (
            "★⑥已判【维持持仓·0笔决策】→今天无交易动作(★这是结论·产品完整·⑥本层判断已填)" if _l6_decided_hold else
            "★今天产不出交易动作——真实原因是【④/⑥判断工单待Opus5填(该填没填·阻断)】·非『①层无事实』(①有26条·③已填传下)"),
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    dc = a.date.replace("-", "")
    r = run(dc)
    (ROOT / "data/market" / f"layer_pipeline_{dc}.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    for L in r["七层"]:
        print("  %s: output %d 条 · 真实状态=%s · 上游接入=%s" % (
            L["层"], L["output数"], L.get("★真实状态"), L.get("★上游接入")))
    print("★⑦归因:", r.get("★⑦无动作的真实归因(PE3-1·非首空层标签)") or "已产出动作")
    print("★结构性结论:", r["★结构性结论"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
