# -*- coding: utf-8 -*-
"""
today_events_extract.py — 今日事件抽取器（地基第一块 T1）

作用（大白话）：
    把每天拉到的真数据，算成"今天真发生/变动了什么"的一张“今日事件列表”。
    这是系统自己的独立事件源，专治两个毛病：
      1) 用“静态状态”冒充“今日事件”（例如某股一直在年线下方，这不是今天发生的事）；
      2) “湖水反客为主”——把行情快照的一堆背景数字当成今天的动作。

    只认“今天真变动”的才算事件：
      · 宏观/总闸：当日涨跌幅明显(|%|≥阈值)的写成事件；10年美债利率总是报一条（全球资金总水位）；
                   收益率曲线只有“倒挂”才算预警事件，未倒挂只是背景、不算。
      · 板块：费城半导体(SOXX)当日涨跌写成事件。
      · 持仓：只有“今天新穿越”50日线/年线(200日线)的才算事件；
              “本来就在下方”属于静态状态，不算今日事件。
              判断办法：拿今天的价位相对均线的位置，跟“上一份快照”的位置比，位置翻面了才算穿越。

只读现有数据，不改任何文件、不碰 OpenD、不下单。
"""

import os
import re
import sys
import json
import io

# 让 Windows 控制台也能正常打印中文（避免 gbk 报错）
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
except Exception:
    pass

# ---- 路径：脚本在 scripts/ 下，数据在同级 ../data/ 下 ----
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(BASE_DIR, "data")

# ---- 阈值：宏观资产当日涨跌幅达到多少才算“事件” ----
MACRO_MOVE_THRESHOLD = 0.5   # 单位 %


def _load_json(path):
    """读一个 json，读不到返回 None（并如实标缺）。"""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _find_prev_ma_file(date):
    """在 data/holdings/ 里找“上一份”ma_levels 快照（日期 < 今天，取最近的一份）。
    找不到返回 None。用于判断‘今天是否新穿越关键线’。"""
    holdings_dir = os.path.join(DATA_DIR, "holdings")
    if not os.path.isdir(holdings_dir):
        return None
    best_date = None
    best_path = None
    for fn in os.listdir(holdings_dir):
        m = re.match(r"^ma_levels_(\d{8})\.json$", fn)
        if not m:
            continue
        d = m.group(1)
        if d < str(date):
            if best_date is None or d > best_date:
                best_date = d
                best_path = os.path.join(holdings_dir, fn)
    return (best_date, best_path) if best_path else None


def _position(price, ma):
    """价位相对某条均线的位置：在上/在下；数据不全返回 None。"""
    if price is None or ma is None:
        return None
    return "above" if float(price) >= float(ma) else "below"


def extract_today_events(date):
    """
    抽取指定日期的“今日事件列表”。
    返回 list[dict]，每条：
        {theme, text, number, direction, source}
        theme ∈ {资金流动/总闸, 板块轮动, 持仓}
    只收录“今天真变动”的事件；缺数据的主题会明确标“待接入”。
    """
    date = str(date)
    events = []

    # ============ 1) 资金流动 / 总闸（宏观） ============
    snap = _load_json(os.path.join(DATA_DIR, "market", "latest_market_snapshot.json"))
    yc_path = os.path.join(DATA_DIR, "market", "yield_curve_%s.json" % date)
    yc = _load_json(yc_path)

    # 名字 → 中文说明，方便写大白话
    macro_alias = {
        "^VIX": "VIX恐慌指数",
        "VIX": "VIX恐慌指数",
        "US10Y": "10年美债利率",
        "DXY": "美元指数",
        "USDJPY": "美元兑日元",
        "SPX": "标普500",
    }

    if snap is None or "assets" not in snap:
        events.append({
            "theme": "资金流动/总闸",
            "text": "今日资金流动/总闸事件待接入（行情快照数据未拉全）",
            "number": None,
            "direction": "待接入",
            "source": "latest_market_snapshot.json 缺失或结构异常",
        })
    else:
        assets = {a.get("symbol"): a for a in snap.get("assets", [])}

        # 1a) 10年美债利率——总是报一条（全球资金的总水位）
        if "US10Y" in assets:
            a = assets["US10Y"]
            cp = a.get("change_percent")
            direction = "持平"
            if cp is not None:
                direction = "升" if cp > 0 else ("降" if cp < 0 else "持平")
            val = a.get("price")
            cp_txt = ""
            if cp is not None:
                cp_txt = "，较上一交易日%s%.2f%%" % (direction, abs(cp))
            events.append({
                "theme": "资金流动/总闸",
                "text": "今天10年美债利率%.3f%%（%s）%s——这是全球资金的总水位，越高越抽血" % (
                    float(val), direction, cp_txt),
                "number": float(val) if val is not None else None,
                "direction": direction,
                "source": "latest_market_snapshot.json · US10Y",
            })

        # 1b) VIX / 美元指数 / 美元日元等：当日涨跌幅达阈值才算事件
        for sym in ("^VIX", "DXY", "USDJPY"):
            a = assets.get(sym)
            if not a:
                continue
            cp = a.get("change_percent")
            if cp is None or abs(cp) < MACRO_MOVE_THRESHOLD:
                continue  # 波动没达阈值 = 背景，不算今日事件
            nm = macro_alias.get(sym, a.get("name", sym))
            direction = "涨" if cp > 0 else "跌"
            extra = ""
            if sym == "^VIX":
                extra = "（恐慌指数%s，数字越低市场越稳）" % ("回落" if cp < 0 else "抬头")
            events.append({
                "theme": "资金流动/总闸",
                "text": "今天%s%s%.2f%%%s" % (nm, direction, abs(cp), extra),
                "number": round(float(cp), 4),
                "direction": direction,
                "source": "latest_market_snapshot.json · %s" % sym,
            })

    # 1c) 收益率曲线：只有“倒挂”才算预警事件；未倒挂=背景，不算
    if yc is None:
        events.append({
            "theme": "资金流动/总闸",
            "text": "今日收益率曲线事件待接入（yield_curve_%s.json 未拉全）" % date,
            "number": None,
            "direction": "待接入",
            "source": "yield_curve_%s.json 缺失" % date,
        })
    else:
        if yc.get("inverted") is True:
            spread = yc.get("spread_10y_3m")
            events.append({
                "theme": "资金流动/总闸",
                "text": "今天收益率曲线倒挂（10年-3月利差%.3f%%，为负）——历史上常提前预警衰退" % (
                    float(spread) if spread is not None else 0.0),
                "number": float(spread) if spread is not None else None,
                "direction": "倒挂预警",
                "source": "yield_curve_%s.json" % date,
            })
        # 未倒挂：不生成事件（属于背景状态，避免静态状态冒充今日事件）

    # ============ 2) 板块轮动（费城半导体 SOXX） ============
    if snap is not None and "assets" in snap:
        assets = {a.get("symbol"): a for a in snap.get("assets", [])}
        a = assets.get("SOXX")
        if a is not None:
            cp = a.get("change_percent")
            if cp is not None and abs(cp) >= MACRO_MOVE_THRESHOLD:
                direction = "涨" if cp > 0 else "跌"
                events.append({
                    "theme": "板块轮动",
                    "text": "今天SOXX（费城半导体ETF，芯片股风向标）%s%.2f%%" % (direction, abs(cp)),
                    "number": round(float(cp), 4),
                    "direction": direction,
                    "source": "latest_market_snapshot.json · SOXX",
                })
            # 波动没达阈值 = 背景，不算事件
        else:
            events.append({
                "theme": "板块轮动",
                "text": "今日板块轮动事件待接入（快照里没有 SOXX/费半数据）",
                "number": None,
                "direction": "待接入",
                "source": "latest_market_snapshot.json 无 SOXX",
            })
    else:
        events.append({
            "theme": "板块轮动",
            "text": "今日板块轮动事件待接入（行情快照数据未拉全）",
            "number": None,
            "direction": "待接入",
            "source": "latest_market_snapshot.json 缺失",
        })

    # ============ 3) 持仓（关键线新穿越） ============
    today_ma = _load_json(os.path.join(DATA_DIR, "holdings", "ma_levels_%s.json" % date))
    if today_ma is None or "holdings" not in today_ma:
        events.append({
            "theme": "持仓",
            "text": "今日持仓事件待接入（ma_levels_%s.json 未拉全）" % date,
            "number": None,
            "direction": "待接入",
            "source": "ma_levels_%s.json 缺失" % date,
        })
    else:
        prev = _find_prev_ma_file(date)
        if not prev:
            # 没有上一份对照，就无法判断“今天是否新穿越”；如实标待接入，绝不拿静态状态冒充
            events.append({
                "theme": "持仓",
                "text": "今日持仓穿越事件待接入（找不到上一份 ma_levels 快照做对照，"
                        "无法区分‘今天新穿越’与‘本来就在线下方’的静态状态）",
                "number": None,
                "direction": "待接入",
                "source": "缺上一份 ma_levels_*.json 对照",
            })
        else:
            prev_date, prev_path = prev
            prev_ma = _load_json(prev_path) or {}
            prev_map = {h.get("symbol"): h for h in prev_ma.get("holdings", [])}

            crossings = 0
            compared = 0
            no_ma_syms = []
            for h in today_ma.get("holdings", []):
                sym = h.get("symbol")
                name = h.get("name", sym)
                price = h.get("realtime_price")
                ma50 = h.get("ma50")
                ma200 = h.get("ma200")
                if ma50 is None and ma200 is None:
                    no_ma_syms.append(name)  # 例如加密，暂无均线
                    continue
                ph = prev_map.get(sym)
                if not ph:
                    continue
                compared += 1
                # 年线(200日) 穿越
                for ma_key, ma_name in ((("ma200"), "年线（200日均线）"),
                                        (("ma50"), "50日线")):
                    today_pos = _position(price, h.get(ma_key))
                    prev_pos = _position(ph.get("realtime_price"), ph.get(ma_key))
                    if today_pos is None or prev_pos is None:
                        continue
                    if today_pos == prev_pos:
                        continue  # 位置没翻面 = 没穿越 = 静态状态，不算今日事件
                    crossings += 1
                    if prev_pos == "above" and today_pos == "below":
                        txt = "今天%s跌破%s——从上方掉到下方，趋势转弱信号" % (name, ma_name)
                        direction = "跌破"
                    else:
                        txt = "今天%s站上%s——重回%s上方" % (
                            name, ma_name, ma_name)
                        direction = "站上"
                    events.append({
                        "theme": "持仓",
                        "text": txt,
                        "number": h.get(ma_key),
                        "direction": direction,
                        "source": "ma_levels_%s.json vs %s（对照）· %s" % (date, os.path.basename(prev_path), sym),
                    })

            if crossings == 0:
                extra = ""
                if no_ma_syms:
                    extra = "；另 %s 暂无均线数据（该类不算均线），穿越判断待接入" % "、".join(no_ma_syms)
                events.append({
                    "theme": "持仓",
                    "text": ("今日持仓无新的关键线穿越（对照上一份 %s 快照，%d只有均线的持仓，"
                             "相对50日线/年线的位置均未翻面；‘本来就在线下方’属静态状态、不算今日事件）%s"
                             "（注：可对照的上一份快照为 %s，非紧邻交易日，期间来回穿越可能漏捕，"
                             "待每日连续快照接入后精度更高）" % (
                                 prev_date, compared, extra, prev_date)),
                    "number": 0,
                    "direction": "无",
                    "source": "ma_levels_%s.json vs ma_levels_%s.json" % (date, prev_date),
                })

    return events


if __name__ == "__main__":
    the_date = sys.argv[1] if len(sys.argv) > 1 else "20260709"
    result = extract_today_events(the_date)

    out = {
        "date": the_date,
        "generated_by": "today_events_extract.py",
        "note": "系统独立事件源：只收录‘今天真变动’的事件；未达阈值/未倒挂/未穿越的静态状态不算事件。",
        "safety": {"read_only": True, "place_order_called": False, "openD_called": False},
        "event_count": len(result),
        "today_events": result,
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))

    # 同时落一份到 evidence_chain 供后续判断层引用
    ev_dir = os.path.join(DATA_DIR, "evidence_chain")
    try:
        os.makedirs(ev_dir, exist_ok=True)
        out_path = os.path.join(ev_dir, "today_events_%s.json" % the_date)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print("\n[written] %s" % out_path)
    except Exception as e:
        print("\n[write-failed] %s" % e)
