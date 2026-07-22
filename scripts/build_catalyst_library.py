#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""建催化剂库·来源三要素（派工单P1·2026-07-22）。架构师尺《催化剂库_来源三要素规范_v1.html》落地。
每条=唯一ID + 三要素(①来源:可追溯出处 ②时间:具体日期/窗口 ③影响:方向+量级+可信度)。可信度三档:已确认/预期/传闻。
准入闸:三要素缺任一→『不完整·不得进决策依据』(只能挂待补);可信度=传闻→可入库观察·不得单独支撑一个预测方向。
初始5条全部取自已锁预测/尺真实示范·不编新的(TSM涨价/爱德万上修/软银OpenAI IPO/COIN Clarity Act/MSTR飞轮反转)。
输出 data/catalyst/catalyst_library.json。用法：python scripts/build_catalyst_library.py --date 20260722"""
import argparse, json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))

# 5条真实示范(逐字取自尺表格·不编)。量级:尺明标则录·未量化则标『定性·尺未量化』不编数。
RAW = [
    {"n": "001", "标的": "US.TSM", "名称": "台积电", "催化剂": "2027年起涨价约10%",
     "来源": "公司法说会官方指引(2026Q2 法说会)", "时间": "2027年起(涨价生效)",
     "方向": "偏上行", "机制": "定价权→毛利率提升", "量级": "大(定价权)", "可信度": "已确认"},
    {"n": "002", "标的": "JP.6857", "名称": "爱德万", "催化剂": "全年营业利润上修至7300亿日元",
     "来源": "公司自身指引上修", "时间": "下季财报约2026-10(验证点)",
     "方向": "偏上行", "机制": "AI测试需求→利润上修兑现", "量级": "利润指引上修至7300亿(尺量)", "可信度": "已确认(指引)"},
    {"n": "003", "标的": "JP.9984", "名称": "软银", "催化剂": "OpenAI IPO 兑现",
     "来源": "软银持股 + OpenAI 上市进展", "时间": "时间窗 2026H2–2027",
     "方向": "偏上行", "机制": "NAV重估→折价收窄", "量级": "大(NAV重估)", "可信度": "预期"},
    {"n": "004", "标的": "US.COIN", "名称": "Coinbase", "催化剂": "Clarity Act 立法推进",
     "来源": "美国国会立法进展", "时间": "待法案表决",
     "方向": "偏上行", "机制": "合规交易所利好", "量级": "定性·尺未量化", "可信度": "预期"},
    {"n": "005", "标的": "US.MSTR", "名称": "MSTR", "催化剂": "mNAV<1 飞轮反转",
     "来源": "市值 vs 持币量实时计算(mnav_daily)", "时间": "持续监控(连续3日<1为扳机)",
     "方向": "偏下行", "机制": "飞轮反转(市值低于持币价值)", "量级": "定性·尺未量化", "可信度": "已确认(数据)"},
]


def now():
    return datetime.now(JST).isoformat(timespec="seconds")


def build_entry(r, date):
    yaosu = {
        "①来源": r["来源"],
        "②时间": r["时间"],
        "③影响": {"方向": r["方向"], "机制": r["机制"], "量级": r["量级"], "可信度": r["可信度"]},
    }
    complete = bool(r["来源"] and r["时间"] and r["方向"] and r["可信度"])
    is_rumor = ("传闻" in str(r["可信度"]))
    return {
        "id": f"CAT-{date}-{r['n']}",
        "标的": r["标的"], "名称": r["名称"], "催化剂": r["催化剂"],
        "三要素": yaosu,
        "三要素完整": complete,
        "准入状态": ("可进决策依据" if complete else "不完整·不得进决策依据(只能挂待补来源/待定时间)"),
        "可单独支撑预测方向": (complete and not is_rumor),
        "★可单独支撑说明": ("可" if (complete and not is_rumor) else ("传闻·可入库观察但不得单独支撑方向" if is_rumor else "三要素不完整·不得进决策依据")),
        "来源出处": "架构师尺《催化剂库_来源三要素规范_v1.html》真实示范(取自已锁预测·不编)",
    }


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default="20260722"); a = ap.parse_args()
    d = a.date
    sys.stdout.reconfigure(encoding="utf-8")
    entries = [build_entry(r, d) for r in RAW]
    idx = {}
    for e in entries:
        idx.setdefault(e["标的"], []).append(e["id"])
    doc = {
        "_说明": "催化剂库·来源三要素规范v1(架构师尺落地·P1)。催化剂=能推动股价的具体未来事件·非趋势空话。每条=唯一ID+三要素(来源/时间/影响·方向+量级+可信度)。",
        "_尺": "00_请先看这里/催化剂库_来源三要素规范_v1.html",
        "version": "v1", "date": d, "generated_at": now(),
        "可信度三档": {"已确认": "已发生/官方已定·只等价格反映", "预期": "合理但未落地·有兑现不确定性",
                   "传闻": "小道消息/未证实·可记录但不得单独作决策依据"},
        "★准入闸": "三要素缺任一→标『不完整·不得进决策依据』(只能挂待补来源/待定时间);可信度=传闻→可入库观察但不得单独支撑一个预测方向。",
        "库条数": len(entries),
        "完整可入决策依据条数": sum(1 for e in entries if e["三要素完整"]),
        "可单独支撑方向条数": sum(1 for e in entries if e["可单独支撑预测方向"]),
        "索引_按标的": idx,
        "催化剂": entries,
    }
    out = ROOT / "data" / "catalyst" / "catalyst_library.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    raw = out.read_bytes()
    try:
        json.load(open(out, encoding="utf-8")); jl = True
    except Exception as e:
        jl = False; print("★json.load失败", e)
    print("wrote", out, len(raw), "字节·EFBFBD=", raw.count(b"\xef\xbf\xbd"), "·json.load通过=", jl)
    print("库条数:", len(entries), "·完整可入决策:", doc["完整可入决策依据条数"], "·可单独支撑方向:", doc["可单独支撑方向条数"])
    for e in entries:
        print(f"  {e['id']} {e['标的'].ljust(9)} {e['名称'][:4].ljust(4)} 可信度={e['三要素']['③影响']['可信度']} · {e['准入状态'][:6]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
