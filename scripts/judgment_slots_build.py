# -*- coding: utf-8 -*-
"""★轮115 NV2:②~⑦层「证据→判断」结构化通道。为每层产出【待填工单】judgment_slots_{date}.json：
· 该层收到的证据(从①层映射来·带尺/维度/来源/等级·带证据ID)
· ★待填槽位:本层判断+依据+证伪信号(★Code不预填·不代编)
· ★填写必须引用①层证据ID(NV2-4·防凭空写)
NV3:★动摇类证据进⑥层工单·标『须复核既有判断』·原判断保留台账不覆盖·Opus5复核后填 维持/修正/撤回+理由+新证伪信号。
★Code只搭槽位·填任何判断内容都是越权。"""
import sys, json, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
# 证据下游层 → 管道层工单键
LAYER_KEYS = ["②国家战略", "③资金流动", "④板块轮动", "⑤机会池", "⑥持仓比较", "⑦交易动作"]
ROUTE = {"①世界观": None, "②国家战略": "②国家战略", "③资金流动": "③资金流动",
         "④板块轮动": "④板块轮动", "⑤机会池": "⑤机会池", "⑥持仓比较": "⑥持仓比较"}


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _empty_slot(ev_ids):
    return {"本层判断": None, "依据": None, "证伪信号": None,
            "★引用证据ID(NV2-4·必填·不许凭空)": [], "_可引用的证据ID": ev_ids,
            # ★★轮147 E8(右→左印证·G21要素二):Opus5填判断时必填【依据右栏哪把尺】+【与尺是否矛盾】(结构化·§5.4)。
            "★依据右栏哪把尺(①~⑥·E8必填)": None,   # 枚举:①世界观/②国家战略/③资金流动/④板块地图/⑤过滤五关/⑥持仓档案
            "★与尺是否矛盾(E8枚举·必填)": None,       # 枚举:无矛盾 / ★修正判断(判断向尺靠) / ★提改尺(须董事长签字)
            "★改尺提案(仅当上项=提改尺·须董事长签字)": None,
            # ★★轮148 E10(大闭环套小闭环·G21要素四):每条判断标属于哪个闭环(结构化枚举)→定周期纪律(A-3:只能被同或更长周期证据推翻)。
            "★属于哪个闭环(E10枚举·必填)": None,   # 枚举:执行闭环(日/周) / 板块闭环(周/月) / 候选闭环(月/季) / 格局闭环(季/年)
            # ★★轮164 B(适用范围·防判断外推过头致下游误报矛盾):本判断适用于哪些驱动/板块·明确排除哪些(如利率敏感型成长股适用·行业周期驱动板块不适用)。
            "★本判断的适用范围(B1·必填)": {"适用驱动类型/板块": None, "★明确排除(不适用的驱动/板块)": None},
            "_填写人": "Opus5", "_状态": "待判断(Opus5未填·Code不代编)"}


def build(date):
    dc = date.replace("-", "")
    # ★轮119 NY1-2:创建当日工单【前】·先把最近的往日工单沉淀进台账(防跨日清空丢判断历史·台账只增不改·重沉幂等)
    try:
        import glob as _g2, re as _re2
        from judgment_ledger import sediment as _sed
        priors = sorted(d for p in _g2.glob(str(ROOT / "data/pipeline/judgment_slots_*.json"))
                        if (m := _re2.search(r"judgment_slots_(\d{8})\.json$", Path(p).name)) and (d := m.group(1)) < dc)
        if priors:
            _sed(priors[-1])  # 沉淀最近往日(只增不改·已沉过不重复)
        # ★轮123 PC2-2:重建【当日】工单前·先把当日已填(第一三共复核等)沉进台账(幂等·防重建丢判断历史)
        if (ROOT / "data/pipeline" / f"judgment_slots_{dc}.json").exists():
            _sed(dc)
    except Exception:
        pass
    em = _rj(ROOT / "data/market" / f"evidence_map_{dc}.json")
    # 证据台账(带ID)
    ledger = []
    for i, e in enumerate(em.get("路1_对6尺持续验证(★动摇置顶)", []) + em.get("路2_对下游维度依据", []), 1):
        pass
    # 用路1(带完整字段)为主台账·★轮123 PC1-3:优先用①层mapper给的稳定插入序ID(台账引用E1/E2/E4须恒指同一条·不随排序变)
    ledger = []
    for i, e in enumerate(em.get("路1_对6尺持续验证(★动摇置顶)", []), 1):
        ledger.append({"id": e.get("id") or ("E%d" % i), "证据": e.get("证据"), "对应尺": e.get("对应尺"),
                       "印证动摇": e.get("印证动摇"), "下游层": e.get("下游层"), "维度": e.get("维度"),
                       "方向": e.get("方向"), "来源": e.get("来源"), "是否独立信源": e.get("是否独立信源"),
                       "依据等级": e.get("依据等级"), "as_of": e.get("as_of")})
    # 按下游层归集证据ID
    by_layer = {k: [] for k in LAYER_KEYS}
    for e in ledger:
        tgt = ROUTE.get(e.get("下游层"))
        if tgt in by_layer:
            by_layer[tgt].append(e["id"])

    slots = {}
    # ★轮119 NY2-2:次日工单显示台账既有判断供对照(Opus5须显式选延续/修正/推翻·不默认继承)
    try:
        from judgment_ledger import prior_for_layer, prior_recheck
    except Exception:
        prior_for_layer = prior_recheck = lambda *a: None
    # ★NY2-3:forecast_lock 见分晓日未到→标『锁定中·勿重出』
    import glob as _g, re as _re, datetime as _dt
    _locked = {}
    _today = _dt.date(int(dc[:4]), int(dc[4:6]), int(dc[6:8]))
    for _p in _g.glob(str(ROOT / "data/forecast/forecast_*.json")):
        if _re.match(r"forecast_\d{4}-\d{2}-\d{2}\.json$", Path(_p).name):
            for _f in (_rj(_p).get("forecasts") or []):
                _vd = str(_f.get("verdict_date") or "")
                try:
                    if _vd and _dt.date(int(_vd[:4]), int(_vd[5:7]), int(_vd[8:10])) >= _today:
                        _locked[_f.get("ticker")] = _vd
                except Exception:
                    pass
    for k in LAYER_KEYS:
        evids = by_layer.get(k, [])
        prior = prior_for_layer(k)
        slot = {"收到证据ID": evids, "input来源": ("①层证据(路2映射)" if k != "⑦交易动作" else "★⑥.output(唯一·不读opus5/production)"),
                "★台账既有判断(供对照·NY2-2·须显式选延续/修正/推翻·不默认继承)": (
                    "该层上次判断=%s（%s·引用%s）" % (str(prior.get("判断"))[:40], prior.get("date"), prior.get("引用证据ID")) if prior else "台账无该层历史(首次)"),
                "槽位": _empty_slot(evids)}
        # ★★★轮186 C-3(GPT B-2裁定):③资金流动层「本层判断」改【六格】结构·★Code只搭槽位·内容Opus5填(不代填)。
        #   起因:GPT原话「两天不足以确认趋势·但已足以称【初步转松】」→须区分 事实/初步判断/置信度/产品影响/确认条件/失效条件·防把初步信号说成"趋势转松"。
        if k == "③资金流动":
            slot["槽位"]["本层判断"] = {
                "①事实(客观数据·如10Y 4.74→4.63·VIX 20.66→16.5)": None,
                "②初步判断(如『初步转松』·★不是『趋势转松』)": None,
                "③置信度(初步/待确认/确认·枚举)": None,
                "④产品影响(对板块/持仓/配仓的影响)": None,
                "⑤确认条件(满足什么才升级为趋势·须可机器检测)": None,
                "⑥失效条件(出现什么则本判断作废·须可机器检测)": None,
                "_填写人": "Opus5", "_状态": "★待Opus5填六格·Code只搭结构不代填(C-3)"}
            slot["★C-3六格说明"] = "GPT B-2裁定:两天不构成趋势但可称初步转松→③层判断拆六格·防把初步信号说成趋势转松·★Code只搭结构内容Opus5填。"
        # ★NV3:⑥层——动摇类证据须复核既有判断
        if k == "⑥持仓比较":
            shake = [e for e in ledger if "动摇" in str(e.get("印证动摇")) and e.get("下游层") == "⑥持仓比较"]
            recheck = []
            op = _rj(ROOT / "data/content" / f"opus5_content_{dc}.json")
            orig = {}
            for x in op.get("三_逐只判断", []):
                if not isinstance(x, dict):   # ★轮186:正文三_逐只判断可能含非dict元素(如说明字符串)·跳过防AttributeError
                    continue
                import re as _re
                m = _re.search(r"([A-Z]{2}\.[0-9A-Z]+)", str(x.get("标的", "")))
                if m:
                    orig[m.group(1)] = "%s / %s" % (x.get("分类"), str(x.get("今天做什么"))[:40])
            for e in shake:
                # 从证据文本认标的
                tk = "JP.4568" if "第一三共" in str(e.get("证据")) else None
                _pr = prior_recheck(tk) if tk else None
                recheck.append({
                    "标的": tk or "见证据", "动摇证据ID": e["id"], "动摇内容": e.get("证据"),
                    "★须复核既有判断": True,
                    "★台账上次复核(供对照·NY2-2·须显式选延续/修正/推翻)": (
                        "上次复核=%s（%s·引用%s）" % (_pr.get("复核结论"), _pr.get("date"), _pr.get("引用证据ID")) if _pr else "台账无该标的复核历史(首次)"),
                    "★原判断(保留台账·不覆盖·NV3-3)": orig.get(tk, "待接原判断源"),
                    "★复核槽位(Opus5填)": {"维持原判/修正/撤回": None, "理由": None, "新证伪信号": None,
                                     "★引用证据ID": [], "_状态": "待Opus5复核"},
                })
            slot["★须复核既有判断(NV3)"] = recheck
            # ★轮126 PF1-1:⑥→⑦【结构化决策清单】(Opus5填·⑦据此+exec_params组装可执行动作)。
            #   ★方向/标的/股数/账户＝判断(⑥出)·执行参数(到价/分笔/跳空)＝exec_params(⑦机器接)。空=不产出动作。
            slot["★决策清单(可执行·Opus5填·⑦读此+exec_params组装·空则⑦不产出)"] = {
                "_说明": "每笔一项:{标的:如JP.4568, 方向:买入/卖出/换出/换入, 股数:整数或『全部』, 账户:如主账户}·★仅方向/标的/股数/账户由⑥判断给·价格分笔跳空由exec_params机器算",
                "决策": [], "_填写人": "Opus5", "_状态": "待Opus5填(空→⑦接线就绪但不产出动作)"}
            # ★★轮134 C:替换比较5字段(GPT遗漏项2)——★Code只搭结构不填内容。①~④待Opus5·⑤换仓后集中度变化=机器算(币种归一)。
            slot["★替换比较(换新是否值得卖旧·GPT五要素·C·Code只搭字段)"] = {
                "_说明": "『新机会是否值得卖掉现有持仓去换』——五要素·前四由Opus5填·第五(集中度变化)机器算",
                "①候选预期收益": None, "②被替换持仓预期收益": None, "③风险差": None, "④税费/汇率/机会成本": None,
                "⑤换仓后集中度变化(机器算·币种归一)": "★待⑥决策清单填(标的/方向/股数)后·由 account_concentration_delta 机器算 单只/驱动集中度前后变化",
                "_填写人": "Opus5(①~④) / 机器(⑤)", "_状态": "待判断(①~④ Opus5未填·⑤待决策清单)"}
        slots[k] = slot

    # ★轮118:★保留 Opus5 已填(同日重跑不覆盖·防daily链/重渲把已填判断洗掉)。新日期无旧文件→全新空槽。
    prev = _rj(ROOT / "data/pipeline" / f"judgment_slots_{dc}.json")
    prev_slots = prev.get("②~⑦层工单", {}) or {}
    for k, s in slots.items():
        ps = prev_slots.get(k, {}) or {}
        # 保留本层判断槽的已填内容
        if (ps.get("槽位", {}) or {}).get("本层判断"):
            s["槽位"] = ps["槽位"]
        # 保留⑥复核槽的已填内容(维持/修正/撤回等)
        # ★轮123 PC2-2:★按【标的】匹配(不按动摇证据ID)——新增A类新闻会移动证据顺序·若按ID会漏配→第一三共复核丢失。标的稳定。
        if k == "⑥持仓比较" and ps.get("★须复核既有判断(NV3)"):
            pmap_t = {r.get("标的"): r for r in ps["★须复核既有判断(NV3)"]}
            pmap_id = {r.get("动摇证据ID"): r for r in ps["★须复核既有判断(NV3)"]}
            for r in s.get("★须复核既有判断(NV3)", []):
                pr = pmap_t.get(r.get("标的")) or pmap_id.get(r.get("动摇证据ID"))
                if pr and (pr.get("★复核槽位(Opus5填)", {}) or {}).get("维持原判/修正/撤回"):
                    r["★复核槽位(Opus5填)"] = pr["★复核槽位(Opus5填)"]
        # ★轮126 PF1-1:保留⑥决策清单已填(同日重跑不洗·⑦据此组装)
        if k == "⑥持仓比较":
            _pdl = ps.get("★决策清单(可执行·Opus5填·⑦读此+exec_params组装·空则⑦不产出)", {}) or {}
            if _pdl.get("决策"):
                s["★决策清单(可执行·Opus5填·⑦读此+exec_params组装·空则⑦不产出)"] = _pdl
    out = {
        "_说明": "★轮115 NV2 ②~⑦层证据→判断结构化通道。每层待填工单:收到证据ID+空槽位(本层判断/依据/证伪信号)。★轮118:同日重跑保留Opus5已填(不洗)。"
                 "★Code不预填不代编·Opus5按层填·填写必须引用①层证据ID(NV2-4)。未填层→待判断→下游不产出(NV2-3)。",
        "date": date, "生成时刻": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "①层证据台账(带ID·供引用)": ledger,
        "②~⑦层工单": slots,
        "★NY2-3 forecast_lock 锁定中(见分晓日未到·勿重出·守PDCA分母)": _locked,
        "★填写规矩": ["本层判断/依据/证伪信号 由Opus5填", "★必须引用①层证据ID(不许凭空)", "未填→待判断→下游不产出不放行",
                  "★动摇条须回答 维持/修正/撤回+理由+新证伪信号", "原判断保留台账不覆盖(PDCA)",
                  "★NY2-2:工单显示台账既有判断供对照·Opus5须显式选延续/修正/推翻·不默认继承",
                  "★NY2-3:锁定中(forecast_lock见分晓未到)的标的勿重出·否则记分卡分母作废",
                  "★NY1-2:填完须先沉淀台账(judgment_ledger)再清工单·未沉淀不许清"],
        "_Code声明": "★本工单所有判断槽位均为 null(Code未填任何判断内容·不代编)",
    }
    op = ROOT / "data/pipeline" / f"judgment_slots_{dc}.json"
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def read_layer_output(dc, layer_key):
    """★NV2-2:读某层已填判断→作该层output。未填(本层判断=null)→返回None(待判断·下游不产出)。
    ★轮125 PE1-2:同时返回【传给下层的输出】(如③的传给④三方向)+全槽·供下游层读【判断内容】而非只数条数。"""
    js = _rj(ROOT / "data/pipeline" / f"judgment_slots_{dc}.json")
    slot = (js.get("②~⑦层工单", {}) or {}).get(layer_key, {})
    g = (slot.get("槽位", {}) or {})
    j = g.get("本层判断")
    if j:
        _pass = next((v for k, v in g.items() if "传给" in k), None)   # ③『传给④层的输出』等·泛化取
        return {"判断": j, "依据": g.get("依据"), "证伪信号": g.get("证伪信号"),
                "引用证据ID": g.get("★引用证据ID(NV2-4·必填·不许凭空)"),
                "★传给下层的输出": _pass,
                "全槽": {k: v for k, v in g.items() if not k.startswith("_")}}
    return None


def received_count(dc, layer_key):
    """★轮125 PE2-2:读某层【收到证据条数】(结构化字段·不靠文本)。==0→客观空;>0且槽位null→未填(该填没填)。"""
    js = _rj(ROOT / "data/pipeline" / f"judgment_slots_{dc}.json")
    return len(((js.get("②~⑦层工单", {}) or {}).get(layer_key, {}) or {}).get("收到证据ID", []) or [])


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    o = build(a.date)
    print("①层证据台账:", len(o["①层证据台账(带ID·供引用)"]), "条(带ID)")
    for k, s in o["②~⑦层工单"].items():
        rc = s.get("★须复核既有判断(NV3)")
        extra = ("·★须复核%d条(含%s)" % (len(rc), rc[0]["标的"]) if rc else "")
        print("  %s: 收到证据 %d 条·槽位[本层判断=%s]%s" % (k, len(s["收到证据ID"]), s["槽位"]["本层判断"], extra))
    print("★Code声明:", o["_Code声明"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
