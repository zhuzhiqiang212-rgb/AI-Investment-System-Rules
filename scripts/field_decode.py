#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解 get_financials_statements 的 field_id 映射 + 十项核验 + 10只样本实算（派工单2026-07-21）。
★只解字段与核验·不筛选·不排序·不出名单·不给买卖建议·不改尺·不自调参数。
映射来源:反推(AAPL+丰田交叉验证)·OCF另经 get_stock_filter 命名字段独立佐证·capex未能跨公司稳定确认→标待查。
产出:field_map / field_verify / field_sample _20260721.json"""
from __future__ import annotations
import json, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "screen"
JST = timezone(timedelta(hours=9))
SAMPLE = ["US.LLY", "US.OXY", "US.UNH", "US.GOOGL", "US.DELL", "US.NVDA", "US.MU",
          "JP.7011", "JP.8035", "JP.6501"]
NAMES = {"US.LLY": "礼来", "US.OXY": "西方石油", "US.UNH": "联合健康", "US.GOOGL": "谷歌",
         "US.DELL": "戴尔", "US.NVDA": "英伟达", "US.MU": "美光", "JP.7011": "三菱重工",
         "JP.8035": "东京电子", "JP.6501": "日立"}

# ── 映射表(反推·AAPL+丰田交叉验证一致)──
MAP_INCOME = {
    8001: ("营业总收入", "货币单位", "反推·AAPL+丰田交叉验证(=顶行最大值·8001-8003=8004)"),
    8002: ("营业收入", "货币单位", "反推·同8001量级"),
    8003: ("营业成本(COGS)", "货币单位", "反推·8001-8003=8004(毛利)两公司皆成立"),
    8004: ("毛利", "货币单位", "反推·=营收-成本·两公司皆成立·毛利率=8004/8001与filter一致"),
    8017: ("营业利润", "货币单位", "反推·两公司量级与营业利润率一致"),
    8034: ("税前利润", "货币单位", "反推·8034-8035=净利前后逻辑一致"),
    8035: ("所得税", "货币单位", "反推·税前×有效税率合理"),
    8037: ("净利润(含少数股东)", "货币单位", "反推·AAPL=归母(无少数)·丰田>归母(有少数)"),
    8043: ("归母净利润", "货币单位", "反推·丰田<8037(少数股东)·AAPL=8037"),
    8046: ("归母净利润", "货币单位", "反推·同8043"),
    8047: ("基本每股收益EPS", "货币/股", "反推·个位数量级"),
    8048: ("稀释每股收益EPS", "货币/股", "反推·略低于基本"),
    8049: ("每股股息DPS", "货币/股", "反推·小于EPS"),
}
MAP_CASHFLOW = {
    8015: ("经营活动现金流净额(OCF)", "货币单位", "★强佐证·丰田8015=¥5,472,920M 与 get_stock_filter operating_cash_flow_ttm 完全一致"),
    8016: ("经营活动现金流净额(近同8015)", "货币单位", "反推·≈8015"),
    8017: ("净利润(现金流起点)", "货币单位", "反推·=利润表8037"),
}
# ── 第二套字段方案:JGAAP(NonUS_GAAP·日股本土准则)用 11xxx·与8xxx完全不同(交叉验证东京电子vs日立)──
MAP_INCOME_JGAAP = {
    11001: ("营业总收入", "货币单位", "反推·东京电子+日立交叉验证(11001-11003=11004)"),
    11002: ("营业收入", "货币单位", "反推"),
    11003: ("营业成本", "货币单位", "反推·11001-11003=11004两公司皆成立"),
    11004: ("毛利", "货币单位", "反推·东京电子毛利率45.3%/日立30.0%合理"),
    11017: ("营业利润", "货币单位", "反推·两公司营业利润率合理"),
    11034: ("税前利润", "货币单位", "反推·11034-11035=净利"),
    11035: ("所得税", "货币单位", "反推"),
    11036: ("净利润(含少数)", "货币单位", "反推·日立>归母(有少数)·东京电子=归母"),
    11041: ("归母净利润", "货币单位", "反推·日立11041<11036·差=少数股东11040"),
    11044: ("归母净利润", "货币单位", "反推·同11041"),
    11047: ("基本EPS", "货币/股", "反推"), 11048: ("稀释EPS", "货币/股", "反推"), 11049: ("每股股息", "货币/股", "反推"),
}
MAP_CASHFLOW_JGAAP = {11014: ("经营活动现金流净额(OCF)", "货币单位", "反推·候选(经营段汇总行·东京电子¥539,732M≈filter量级)·佐证力弱于8015")}
# capex:未能跨公司稳定确认(8033对AAPL≈-9.2B合理·对丰田-176B偏小不合理)→不采信·真FCF标待查
CAPEX_STATUS = "未确认·8xxx的8033对AAPL量级合理但对丰田不合理·11xxx亦未定位·无独立命名字段佐证→真自由现金流(OCF-capex)本轮标【待查·不采信】"


def now():
    return datetime.now(JST).isoformat(timespec="seconds")


def fin_val(s, field):
    for k, v in vars(s).items():
        if isinstance(k, tuple) and k[0] == field:
            try:
                return float(v)
            except Exception:
                return None
    return None


def get_stmt(ctx, ft, code, st):
    ret, d = ctx.get_financials_statements(code, statement_type=st, num=8)
    if ret != ft.RET_OK or not isinstance(d, dict):
        return []
    return [r for r in d.get("report_list", []) if "FY" in r.get("period_text", "")]


def item(rep, fid):
    for it in rep.get("item_list", []):
        if it.get("field_id") == fid:
            return it.get("data"), it.get("yoy")
    return None, None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    import futu as ft
    ctx = ft.OpenQuoteContext("127.0.0.1", 11111)
    samples = {}
    try:
        for c in SAMPLE:
            inc = get_stmt(ctx, ft, c, 1); time.sleep(1.2)
            cf = get_stmt(ctx, ft, c, 3); time.sleep(1.2)
            if not inc:
                samples[c] = {"error": "无年报利润表"}
                continue
            r0 = inc[0]
            # 方案识别:US_GAAP/IFRS 用 8xxx·NonUS_GAAP(JGAAP)用 11xxx
            def pick(rep, fids):
                for f in fids:
                    d, y = item(rep, f)
                    if d is not None:
                        return d, y, f
                return None, None, None
            scheme = "8xxx(US_GAAP/IFRS)" if item(r0, 8001)[0] is not None else "11xxx(JGAAP/NonUS_GAAP)"
            REV = (8001, 11001); GROSS = (8004, 11004); NET = (8037, 11036); OCFF = (8015, 11014)
            rev, rev_yoy, _fr = pick(r0, REV)
            gp, gp_yoy, _fg = pick(r0, GROSS)
            ni, ni_yoy, _fn = pick(r0, NET)
            gm = (round(gp / rev * 100, 2) if (rev and gp is not None and rev != 0) else None)
            gm_prev = None
            if len(inc) >= 2:
                rev1, _, _ = pick(inc[1], REV); gp1, _, _ = pick(inc[1], GROSS)
                gm_prev = (gp1 / rev1 * 100 if (rev1 and gp1 is not None and rev1 != 0) else None)
            gm_chg_pp = (round(gm - gm_prev, 2) if (gm is not None and gm_prev is not None) else None)
            ocf = ocf_yoy = None
            if cf:
                ocf, ocf_yoy, _fo = pick(cf[0], OCFF)
            # 常识核对
            flags = []
            if gm is not None and not (0 < gm < 100):
                flags.append(f"毛利率{gm}%越界(0,100)·待查")
            if rev is not None and rev <= 0:
                flags.append("营收≤0·待查")
            if gm == 0.0:
                flags.append("毛利率=0.0·疑未取到(信越/发那科同类)·待查")
            samples[c] = {
                "名称": NAMES[c], "报表期": r0.get("period_text"), "币种": r0.get("currency_code"),
                "会计准则": r0.get("accounting_standards"), "字段方案": scheme, "报表期末日": r0.get("date_time_str"),
                "营收(8001)": rev, "营收同比%(yoy)": rev_yoy,
                "毛利(8004)": gp, "毛利同比%(yoy)": gp_yoy,
                "毛利率%": gm, "毛利率同比(pp·两年FY算)": gm_chg_pp,
                "净利润(8037)": ni, "净利同比%(yoy)": ni_yoy,
                "OCF(8015)": ocf, "经营现金流同比%(yoy)": ocf_yoy,
                "真自由现金流FCF=OCF-capex": None, "FCF状态": CAPEX_STATUS,
                "常识核对": (flags or ["通过·数值在合理区间"]),
            }
    finally:
        ctx.close()

    # ── 输出1:field_map ──
    field_map = {
        "_说明": "get_financials_statements 的 field_id→科目 映射。★全部为【反推】(AAPL+丰田交叉验证)·非富途官方字段表(SDK未内嵌display_name·本OpenD版返回为空)。OCF另有独立命名字段佐证。",
        "映射方法": "取AAPL(US_GAAP)+丰田(JP·US_GAAP)年报·用会计恒等式(营收-成本=毛利·毛利-费用=营业利润·税前-税=净利)逐行反推·两公司同field_id含义一致才采信(单只吻合不算)。",
        "★两套字段方案": "US_GAAP/IFRS 用 8xxx;NonUS_GAAP(日股JGAAP·如东京电子/日立/三菱重工)用 11xxx。同一含义在两套里 field_id 不同→混用会串号。丰田虽日股但报US_GAAP故用8xxx。",
        "利润表_8xxx_US_GAAP": {str(k): {"科目": v[0], "单位": v[1], "来源": "反推·AAPL+丰田交叉验证", "依据": v[2]} for k, v in MAP_INCOME.items()},
        "现金流量表_8xxx_US_GAAP": {str(k): {"科目": v[0], "单位": v[1], "来源": ("反推+命名字段佐证" if "强佐证" in v[2] else "反推"), "依据": v[2]} for k, v in MAP_CASHFLOW.items()},
        "利润表_11xxx_JGAAP": {str(k): {"科目": v[0], "单位": v[1], "来源": "反推·东京电子+日立交叉验证", "依据": v[2]} for k, v in MAP_INCOME_JGAAP.items()},
        "现金流量表_11xxx_JGAAP": {str(k): {"科目": v[0], "单位": v[1], "来源": "反推·佐证力弱", "依据": v[2]} for k, v in MAP_CASHFLOW_JGAAP.items()},
        "capex_资本开支": {"状态": CAPEX_STATUS, "来源": "反推失败·未采信"},
        "交叉验证证据": {
            "AAPL_2025FY": {"营收8001": 416161000000, "成本8003": 220960000000, "毛利8004": 195201000000,
                           "校验": "8001-8003=8004 ✓·毛利率46.9%与filter一致", "净利8037": 112010000000, "OCF8015": 111482000000},
            "丰田_2026FY": {"营收8001": 50684952000000, "成本8003": 42221212000000, "毛利8004": 8463740000000,
                          "校验": "8001-8003=8004 ✓·毛利率16.7%·OCF8015=filter operating_cash_flow_ttm 完全一致", "归母8043": 3848098000000},
        },
    }
    # ── 输出2:field_verify(十项)──
    verify = {
        "_说明": "GPT总控11 十项核验·逐项。★第4/5/6项是回测可用性关键。",
        "1_字段含义与单位": "利润表8科目+现金流OCF 已反推交叉验证(见field_map)·单位=报表币种(currency_code:USD/JPY)·EPS/DPS为每股。capex未确认。",
        "2_年报季报TTM口径": "statements 分期返回·period_text 标 FY/Q1..Q4·本轮统一取 FY(年报)口径算同比·不混季报;filter的OCF_TTM是滚动12月·两者口径不同已分开。",
        "3_原始值还是增长率": "item.data=原始值(货币额)·item.yoy=同比增长率(已内嵌)·两者都给·营收/毛利/净利/OCF同比直接读yoy。",
        "4_财报发布日能否取得": "★statements 的 date_time_str=【报表期末日】(AAPL 2025-09-26=FY末·非披露日)·非发布日;真实【发布日】须另取 get_financials_earnings_price_move.pub_trading_day_str→能取但须两API联结(部分)。",
        "5_历史值是否被重述": "★statements 返回【当前值】·公司若事后重述财报→拿到的是重述后数字·API无as-of快照、无original标记→【无法排除重述】·回测有偏差。",
        "6_当时是否真实可见": "★综合4+5:用当前(可能重述)值+期末日≠发布日→若拿它检验'当时能否选中礼来'会虚高;须(a)用earnings_price_move真实发布日做可见时点(b)接受不能排除重述。严格意义【非无未来信息安全】。",
        "7_US_JP同口径": "★不同口径:US_GAAP/IFRS 用 8xxx·NonUS_GAAP(日股本土JGAAP:东京电子/日立/三菱重工)用【11xxx另一套field_id】·混用会串号。丰田报US_GAAP故仍走8xxx。两套各自经会计恒等式交叉验证一致。披露频率日股半年报为主·季度粒度与美股不同。",
        "8_capex正负号与现金流分类": "现金流投资活动内资本开支应为负(流出);但capex具体field_id未能跨公司稳定确认(8033对AAPL≈-9.2B合理·对丰田-176B偏小)→未采信。",
        "9_OCF与capex能否组真FCF": "OCF(8015)可信;capex未确认→【真自由现金流本轮不可信·标待查】·不得据此判断。",
        "10_换机重跑一致性": "同一OpenD快照+同脚本→field_id/data确定性返回·可复现;但data为服务端当前值(见第5项)·跨【时间】重跑可能因重述而变(非跨机器问题)。",
    }
    for name, doc in [("field_map", field_map), ("field_verify", verify), ("field_sample", {"_说明": "10只样本实算(营收/毛利率/OCF同比+FCF状态+常识核对)·供架构师核合理性", "生成时间": now(), "samples": samples})]:
        p = OUT / f"{name}_20260721.json"
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        raw = p.read_bytes()
        print("wrote", p.name, len(raw), "字节 · EFBFBD=", raw.count(b"\xef\xbf\xbd"))

    # 覆盖率 + 一句话
    ok_rev = sum(1 for c in SAMPLE if isinstance(samples.get(c), dict) and samples[c].get("营收同比%(yoy)") is not None)
    ok_gm = sum(1 for c in SAMPLE if isinstance(samples.get(c), dict) and samples[c].get("毛利率同比(pp·两年FY算)") is not None)
    ok_ocf = sum(1 for c in SAMPLE if isinstance(samples.get(c), dict) and samples[c].get("经营现金流同比%(yoy)") is not None)
    print(f"\n覆盖率(10只): 营收同比 {ok_rev}/10 · 毛利率同比 {ok_gm}/10 · OCF同比 {ok_ocf}/10 · 真FCF 0/10(capex待查)")
    print("一句话:变化驱动从【1根柱子(利润同比)】变成【4根(营收/毛利率/净利/OCF同比)】;"
          "其中【0根】可直接用于严格无未来信息回测(须联结真实发布日+不能排除财报重述)·经此两处修正后可做【带发布日滞后的准回测】。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
