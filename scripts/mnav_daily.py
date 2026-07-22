#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mNAV 每日接通（架构师定源2026-07-22）· 只读OpenD·不下单。
mNAV = MSTR市值 / (MSTR持有BTC数 × BTC现价)。走人条件:mNAV持续<1则飞轮反转→记分卡预警。
① BTC持仓数:MSTR官方8-K/IR录入(公司一手·三要素);当前用理解岗07-02估值845256·★缺8-K链接/公告日·降级待补
② BTC价:不追历史·从今天起每日自存现价(OpenD·同PIT点时思路·append不覆盖)
③ 每日算 mNAV·持续<1进预警
用法:python scripts/mnav_daily.py [--btc-holdings N] [--date YYYYMMDD]"""
import argparse, json, socket, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
SERIES = ROOT / "data" / "screen" / "mnav_series.jsonl"     # 每日自存(append·不覆盖)
BTC_PIT = ROOT / "data" / "pit" / "btc_price_series.jsonl"   # BTC现价点时自存


def now():
    return datetime.now(JST).isoformat(timespec="seconds")


def port_open(t=2.0):
    s = socket.socket(); s.settimeout(t)
    try:
        s.connect(("127.0.0.1", 11111)); return True
    except Exception:
        return False
    finally:
        s.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d"))
    ap.add_argument("--btc-holdings", type=float, default=None)
    ap.add_argument("--hold-asof", default=None, help="8-K持仓as-of日期")
    ap.add_argument("--hold-filed", default=None, help="8-K公告(filed)日期")
    ap.add_argument("--hold-link", default=None, help="SEC 8-K/IR 官方链接")
    ap.add_argument("--hold-note", default=None, help="来源附注(均价/口径)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    # BTC持仓数:命令行优先(8-K/IR一手录入·带三要素)·否则读估值模型·并标来源
    hold_src = {"值": None, "来源": None, "三要素齐全": False}
    if a.btc_holdings:
        complete = bool(a.hold_link and (a.hold_filed or a.hold_asof))
        hold_src = {"值": a.btc_holdings,
                    "三要素_标题": "Strategy(MSTR) Form 8-K · 比特币持仓披露",
                    "三要素_链接": a.hold_link or "★缺·未附链接",
                    "三要素_公告日期(filed)": a.hold_filed or "★缺",
                    "持仓as-of日期": a.hold_asof or "★缺",
                    "来源": "MSTR官方8-K/IR一手录入" + (f"·{a.hold_note}" if a.hold_note else ""),
                    "三要素齐全": complete}
    else:
        try:
            m = json.loads((ROOT / "data/valuation/model_instances/MSTR.json").read_text(encoding="utf-8"))
            raw = str(m["inputs"]["btc_holdings"])
            import re
            n = re.search(r"(\d[\d,]*)", raw)
            hold_src = {"值": float(n.group(1).replace(",", "")) if n else None,
                        "来源": f"估值模型MSTR.json·{m.get('source')}", "原文": raw,
                        "三要素齐全": False, "★缺": "8-K公告日期+官方链接(现为理解岗07-02估值·非公司一手8-K)·须补"}
        except Exception as e:
            hold_src = {"值": None, "来源": f"读估值模型失败:{e}"}
    HOLD = hold_src["值"]

    doc = {"date": a.date, "generated_at": now(), "BTC持仓数": hold_src}
    if not port_open():
        doc["FATAL"] = "OpenD 未连·未生产·不顶充"
        (ROOT / "data/screen" / f"mnav_{a.date}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("OpenD未连·如实记未生产"); return 1

    import futu as ft
    ctx = ft.OpenQuoteContext("127.0.0.1", 11111)
    btc = mstr_mv = None
    try:
        ret, df = ctx.get_market_snapshot(["CC.BTCUSD"])
        if ret == ft.RET_OK:
            btc = float(df.iloc[0]["last_price"])
        sf = ft.SimpleFilter(); sf.stock_field = ft.StockField.MARKET_VAL; sf.filter_min = 1e9
        sf.is_no_filter = False; sf.sort = ft.SortDir.DESCEND
        begin = 0
        while True:
            ret, ls = ctx.get_stock_filter(market=ft.Market.US, filter_list=[sf], begin=begin, num=200)
            if ret != ft.RET_OK:
                break
            last, cnt, lst = ls
            for s in lst:
                if s.stock_code == "US.MSTR":
                    mstr_mv = float(s.market_val)
            begin += len(lst)
            if mstr_mv is not None or last or begin >= cnt:
                break
            time.sleep(3)
    finally:
        ctx.close()

    # BTC现价自存(append·不覆盖)
    BTC_PIT.parent.mkdir(parents=True, exist_ok=True)
    if btc is not None:
        with BTC_PIT.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"date": a.date, "btc_usd": btc, "源": "OpenD CC.BTCUSD 现价", "抓取": now()}, ensure_ascii=False) + "\n")

    btc_nav = (HOLD * btc if (HOLD and btc) else None)
    mnav = (mstr_mv / btc_nav if (mstr_mv and btc_nav) else None)
    doc.update({"BTC现价": btc, "MSTR市值": mstr_mv, "BTC持币NAV": btc_nav, "mNAV": (round(mnav, 4) if mnav else None),
                "口径": "mNAV = MSTR市值 / (BTC持仓数 × BTC现价)"})

    # 每日mNAV自存 + 持续<1判定
    below = None
    if mnav is not None:
        with SERIES.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"date": a.date, "mnav": round(mnav, 4), "btc": btc, "mstr_mv": mstr_mv, "hold": HOLD, "at": now()}, ensure_ascii=False) + "\n")
        # 连续<1天数(读series去重按date取最后)
        seen = {}
        for line in SERIES.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    r = json.loads(line); seen[r["date"]] = r["mnav"]
                except Exception:
                    pass
        dates = sorted(seen)
        streak = 0
        for d in reversed(dates):
            if seen[d] < 1:
                streak += 1
            else:
                break
        below = {"今日mNAV<1": mnav < 1, "连续<1天数": streak,
                 "预警": (mnav < 1 and streak >= 3), "持续判据": "连续≥3日<1视为『持续』→记分卡预警(暂行·可调)"}
    doc["预警_mNAV持续小于1"] = below
    doc["走人条件"] = "持仓档案:mNAV持续<1则飞轮反转(加密高Beta非战略持仓)"

    p = ROOT / "data/screen" / f"mnav_{a.date}.json"
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    raw = p.read_bytes()
    print("wrote", p.name, len(raw), "字节·EFBFBD=", raw.count(b"\xef\xbf\xbd"))
    print(f"BTC现价 ${btc} · MSTR市值 ${round(mstr_mv/1e9,2) if mstr_mv else None}B · BTC持仓 {HOLD}")
    print(f"★今日 mNAV = {round(mnav,4) if mnav else None}" + (f" (<1·连续{below['连续<1天数']}日·预警={below['预警']})" if below else ""))
    print("BTC现价已自存(append):", BTC_PIT.name, "· mNAV序列:", SERIES.name)
    print("★BTC持仓数来源:", hold_src.get("来源"), "·三要素:", hold_src.get("★缺", hold_src.get("三要素齐全")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
