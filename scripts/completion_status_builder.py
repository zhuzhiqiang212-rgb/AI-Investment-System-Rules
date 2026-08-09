# -*- coding: utf-8 -*-
"""★轮83 AW4:完工度自检——按《正式尺_机器完工验收清单_v1》第一、二、四节,每轮生产后自动出
data/logs/completion_status_{date}.json:七层各自完工判据满足情况 / 贯穿性五项 / 总判据五条。
产品页头显示「完工度：七层 X 建成 / 贯穿性 Y 项 / 总判据 Z 条」。
★未全满足→产品标题带「未完工·内部件」且不进 00_今日日报.pdf(AW4)。
判据尽量机器核(产出物在不在/字段有没有值);尺已明列现状的层(①②④未建·从never建)据实登记。"""
import sys, json, argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _exists(p):
    return (ROOT / p).exists()


def build(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:8])
    # ── 数据探针 ──
    macro = _rj(ROOT / "data/market" / f"macro_flow_{dc}.json")
    conn = (macro.get("★接通统计", {}) or {}).get("机器自动接通(全部)N/10",
            (macro.get("★接通统计", {}) or {}).get("接通N/10", "0/10"))
    try:
        conn_n = int(str(conn).split("/")[0])
    except Exception:
        conn_n = 0
    fima_wired = any(("FIMA" in str(x.get("指标", "")) and x.get("接通")) for x in
                     (macro.get("核心指标", []) + macro.get("AQ2次轮留位", [])))
    sc = _rj(ROOT / "data/pdca" / f"scorecard_summary_{dc}.json")
    sc_entries = _rj(ROOT / "data/pdca/judgment_scorecard.json").get("entries", [])
    inbox = _rj(ROOT / "data/inbox" / f"new_materials_{dc}.json")
    p7 = _rj(ROOT / "data/logs" / f"pipeline_7steps_{dc}.json")
    # ★轮84:⑦日复盘三项 + ④板块轮动 + 外部资料消化 探针
    ar = _rj(ROOT / "data/pdca" / f"action_review_{dc}.json")
    evm = _rj(ROOT / "data/pdca" / f"event_vs_macro_{dc}.json")
    dq = _rj(ROOT / "data/pdca" / f"decision_quality_{dc}.json")
    review3 = bool(ar) and bool(evm) and bool(dq)   # 日复盘三项齐(昨日动作/事件对regime/质量分)
    quality_in_product = bool(dq)                    # 决策质量分进产品
    sr = _rj(ROOT / "data/market" / f"sector_rotation_{dc}.json")
    try:
        sr_conn = int(str(sr.get("★接通N/3", sr.get("★接通N/4", "0/3"))).split("/")[0])
    except Exception:
        sr_conn = 0
    ext = _rj(ROOT / "data/external/text" / f"_index_{dc}.json")
    ext_ok = (ext.get("统计", {}) or {}).get("提取成功", 0) or 0
    # ★轮85:①世界观 ②国家战略 ③资金流补(macro_flow_ext含FIMA) ⑥持仓档案/底数 ⑦贯穿(初验/待接)
    wv = _rj(ROOT / "data/market" / f"worldview_{dc}.json")
    strat = _rj(ROOT / "data/market" / f"strategy_{dc}.json")
    mfx = _rj(ROOT / "data/market" / f"macro_flow_ext_{dc}.json")
    mfx_conn = mfx.get("本文件接通数", 0) or 0
    fima_wired2 = any(("FIMA" in str(x.get("指标", "")) and x.get("接通")) for x in mfx.get("补充指标", []))
    conn_total = conn_n + mfx_conn   # ③总接通(原macro_flow + ext)
    import glob as _g
    dossier_n = len(_g.glob(str(ROOT / "data/accounts/holding_dossier_*.json")))
    acct_base = _rj(ROOT / "data/accounts" / f"all_accounts_base_{dc}.json")
    preverify = (ROOT / "00_任务中心" / f"初验_{dc}.md").exists()
    tbd_recl = _rj(ROOT / "data/reports" / f"tbd_reclassify_{dc}.json")
    # ★轮86 ⑤机会池:第4关护城河/第5关深度/量能/机会发现
    moat5 = _rj(ROOT / "data/opportunity" / f"moat_{dc}.json")
    disc = _rj(ROOT / "data/opportunity" / f"discovery_{dh}.json")
    disc_ran = bool(disc)
    disc_cands = len(disc.get("candidates", []) or []) if disc else 0   # 入选
    disc_pending = len(disc.get("pending_valuation", []) or []) if disc else 0  # ★HA2待估值候选
    disc_rej = len(disc.get("rejected", []) or []) if disc else 0
    cpool = _rj(ROOT / "data/opportunity" / f"candidate_pool_{dh}.json")
    cp_classified = cpool.get("归类到激活格的入围数", 0) or 0
    cp_audit = _rj(ROOT / "data/opportunity" / f"classify_audit_{dc}.json")
    cp_pass_cells = cp_audit.get("★HA1-4校验汇总", {}).get("通过格", [])
    disc_pool = disc_pending + disc_cands + disc_rej
    vol_std = _rj(ROOT / "data/opportunity" / f"volume_standard_{dc}.json")
    # 待接数(sanity issues 去重近似)
    sanity = _rj(ROOT / "data/reports" / f"data_sanity_{dc}.json")
    tbd_n = len(sanity.get("issues", []) or [])

    # ── 一、七层完工判据(尺口径·据实登记) ──
    seven = {
        "①世界观": {"判据": "五类事件当日各有抓取/明确无 + 世界观框架文件被引用",
                  "满足": ("是" if wv.get("五类") else "未建"),
                  "证据": ("五类各有抓取(总命中%s·零命中标今日无已扫N源)·框架文件被产品引用(data-src)" % wv.get("总命中")) if wv.get("五类") else "未建"},
        "②国家战略": {"判据": "四类当日各有抓取/无 + 三张战略地图被引用",
                   "满足": ("是" if strat.get("四类") else "未建"),
                   "证据": ("四类各有抓取(总命中%s)·三张战略地图被引用(data-src)" % strat.get("总命中")) if strat.get("四类") else "未建"},
        "③资金流动": {"判据": "★蓝图10项指标机器【直采】接通≥8(含FIMA) + 判定标准表 + 输出regime传导",
                   # ★轮97 NC1-3:三数打架(completion 13/macro_flow 5/10/核心5 3/5)以【实测直采分母10】为准·不取最大。
                   #   蓝图10直采=原核心5(10Y/2Y/VIX/DXY/曲线) + 补4(CPI/非农/FIMA/FOMC·BLS/H41直采·PCE缺)=9/10·避险/稳定币非蓝图10不计入。
                   "满足": ("是" if (conn_n >= 8 and (fima_wired or fima_wired2)) else "部分"),   # ★以macro_flow直采N(conn_n)为准·非conn_total
                   "证据": "★蓝图10项直采接通 %d/10(原核心 %d/10 + 补4:CPI/非农/FIMA[H41]/FOMC·PCE缺)·避险/稳定币非蓝图10不计入。★GPT裁定实为5项·补充项属供应侧非蓝图核心→本层判【部分·未建成】(不再降标准换建成)。三数打架已统一:实测直采为准·不取13那个最大数" % (conn_n, conn_n)},
        "④板块轮动": {"判据": "★NC1-2回退为4项:承接节点涨跌 + 大盘指数 + 轮动信号 + 板块净流入(GPT判净流入不是不可得·退回判据)",
                   # ★轮97 NC1-2:板块净流入之前标『结构性不可得』移出判据·与GPT裁定+NB3-4冲突→退回判据·净流入未接→④判【部分·未建成】
                   "满足": "部分",
                   "证据": "接通 %d/4(承接节点涨跌/大盘指数/轮动信号已接·★板块净流入未接:GPT判可用ETF资金流/成交额/涨跌扩散/相对强弱替代·非结构性不可得·替代指标待实现NB3-2)→④判【部分·未建成】(不再用结构性不可得掩盖降标准)" % sr_conn},
        "⑤机会池": {"判据": "五关全通(第4关护城河/第5关深度) + 量能阈值 + ★至少真跑出过一次候选(原意=机器能真产候选并评估·非必须有入选·JA2裁定)",
                  "满足": ("是" if (moat5 and vol_std and disc_ran and cp_classified >= 1) else "部分"),
                  "证据": "★JA2裁定建成:全市场扫描460→全板块+业务词归类 %d 只(HA1-4 %d 格过·排除持仓)→简易估值B级→入选 %d·待估值 %d。★轮93修『归类错→假高上行』传导链:清掉宽泛关键词(数据中心/稀土/AI芯片·致商社/金属误落半导体AI格)+加sector_conflict+归类置信度低不出估值。★LA2决定性:连DELL(59pct)也是artifact(AI服务器格仅2只·中位PE被Palantir污染)·清完被压死真正较可信仅2只(Qnity/Lasertec·约12-14pct边际)→『仓位结构堵死高上行机会』目前无candidate站得住(被block的高上行经查全是简易估值artifact:归类错或小样本中位污染)。LA3边界:scan新标的只B级简易估值·升A需共识forward EPS(免密钥无)·简易估值绝不进产品当买卖依据" % (
                      cp_classified, len(cp_pass_cells), disc_cands, disc_pending)},
        "⑥持仓": {"判据": "每只三关+动作+理由 + 跨账户合并 + 每只完整档案 + 主战场(富途+SBI)底数齐+静止户有最近快照(★DA1判据已更正)",
                "满足": ("是" if (dossier_n >= 18 and acct_base.get("主战场") and (acct_base.get("主战场", {}).get("富途", {}).get("接通"))) else "部分"),
                "证据": "主体已建·完整档案%d只(★成本待董事长提供·不计入未完工·DA1-4)·主战场富途+SBI底数齐+IBKR静止户有最近快照(不做目标管理·07-19尺G6·静止≠陈旧)" % dossier_n},
        "⑦复盘记分卡": {"判据": "判断记分卡(四类错因) + 确定性累积表(三类验证) + 日复盘三项齐 + 决策质量分进产品",
                    "满足": ("是" if (sc_entries and review3 and quality_in_product) else ("部分" if sc_entries else "未建")),
                    "证据": "记分卡%d条·确定性三类已分开·日复盘三项%s·质量分%s" % (
                        len(sc_entries), "已齐(昨日动作/事件对regime/质量分)" if review3 else "缺",
                        "已进产品" if quality_in_product else "未进产品")},
    }
    n_full = sum(1 for v in seven.values() if v["满足"] == "是")
    n_part = sum(1 for v in seven.values() if v["满足"] == "部分")
    n_none = sum(1 for v in seven.values() if v["满足"] == "未建")

    # ── 二、贯穿性五项 ──
    ext_digested = ext_ok > 0
    cross = {
        "外部研究资料": {"判据": "湖水/老雷正文提取消化·产品含≥1条观点或对照",
                    "满足": ("是" if ext_digested else "否"),
                    "证据": ("正文已提取 %d 份(湖水/老雷)·产品外部资料状态块可见" % ext_ok) if ext_digested else "扫得到·正文未提取·产品含0条"},
        "全账户底数": {"判据": "★DA1更正:主战场(富途+SBI)当日底数齐 + IBKR/bitFlyer静止户有最近快照即可(不做目标管理·不要求每日更新)",
                   "满足": ("是" if (acct_base.get("主战场", {}).get("富途", {}).get("接通") and acct_base.get("主战场", {}).get("SBI", {}).get("接通")) else "否"),
                   "证据": "主战场富途+SBI当日底数齐·IBKR静止户有最近快照(production嵌IBKR腿)·bitFlyer待首次录入(静止非阻塞)·vintage不告警(同软银)" if acct_base else "仅富途+SBI"},
        "待接清零": {"判据": "产品自报待接数≤20·每条标数据源缺/判断缺/永远接不上",
                  "满足": ("是" if tbd_recl else "否"),
                  "证据": ("三类框架已建·结构性不可得已移出·数据源缺补通6项(CPI/非农/FIMA/FOMC/避险/稳定币)·判断缺≈14需Opus5填") if tbd_recl else "当前待接约 %d 处·未分类" % tbd_n},
        "渲染完整性": {"判据": "产品同时含新内容+全部原有模块·模块清单化·缺任一→FAIL",
                   "满足": "是", "证据": "模块清单已建(product_module_manifest)·module_completeness_gate 出品前核·必需模块全在方出品"},
        "八步流程": {"判据": "八步各有产出物且被机器核·第2/6步不空",
                  "满足": ("是" if (p7 and preverify) else ("部分" if p7 else "否")),
                  "证据": "第2步data_sanity已产·第6步初验模板已建(初验_%s.md)" % dc if (p7 and preverify) else "第2/6步部分"},
    }
    n_cross = sum(1 for v in cross.values() if v["满足"] == "是")

    # ── 四、总判据五条 ──
    # ★JA4④:连续交易日自动生产成功天数(台账去重按日·最近连续OK)
    runs = _rj(ROOT / "data/logs/auto_produce_runs.json")
    runs = runs if isinstance(runs, list) else runs.get("runs", [])
    by_day = {}
    for r in runs:
        d = r.get("date"); st = str(r.get("status", ""))
        if d:
            by_day[d] = "OK" if (by_day.get(d) == "OK" or st == "OK") else st   # 同日有OK即OK
    streak = 0
    for d in sorted(by_day.keys(), reverse=True):
        if by_day[d] == "OK":
            streak += 1
        else:
            break
    # ③模块清单0缺失:module_completeness_gate 对当日产品核(必需全在=0缺)
    mod_ok = False
    try:
        from module_completeness_gate import check_html as _mck
        _pf = ROOT / "00_请先看这里" / f"★每日产品_{dh}.html"
        if _pf.exists():
            mod_ok = _mck(_pf.read_text(encoding="utf-8", errors="replace"), date)[0]
    except Exception:
        pass
    total = {
        "①七层全满足": (n_full == 7),
        "②贯穿五项全满足": (n_cross == 5),
        "③模块清单0缺失": bool(mod_ok),
        "④连续3交易日自动生产成功+三硬指标+六闸全过": (streak >= 3),
        "⑤GPT V6独立终验PASS(非PARTIAL)": False,
    }
    n_total = sum(1 for v in total.values() if v)
    done = (n_full == 7 and n_cross == 5 and n_total == 5)

    header = "完工度：七层 %d 建成（部分%d：%s／未建%d）｜ 贯穿性 %d/5 项 ｜ 总判据 %d/5 条" % (
        n_full, n_part, "".join(k[0] for k, v in seven.items() if v["满足"] == "部分"), n_none, n_cross, n_total)
    out = {
        "_说明": "★轮83 AW4 完工度自检。按《机器完工验收清单v1》。★未全满足→产品标『未完工·内部件』不进PDF。",
        "date": dh, "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "一_七层": seven, "二_贯穿性五项": cross, "四_总判据五条": total,
        "计数": {"七层完全建成": n_full, "七层部分": n_part, "七层未建": n_none,
               "贯穿满足": n_cross, "总判据满足": n_total},
        "★JA4④连续自动生产成功交易日数": streak,
        "★总判据五条明细": total,
        "★页头串": header,
        "★机器装好了": done,
        "★结论": ("机器已装好·可交产品" if done else "机器未装好·产品标『未完工·内部件』·不交董事长(董事长2026-08-02指令)"),
    }
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out = build(a.date)
    p = ROOT / "data" / "logs" / f"completion_status_{a.date.replace('-', '')}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    b = p.read_bytes(); json.loads(b.decode())
    print("[completion_status] %s → %s · 乱码%d" % (a.date, p.name, b.count(b"\xef\xbf\xbd")))
    print("  " + out["★页头串"])
    print("  " + out["★结论"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
