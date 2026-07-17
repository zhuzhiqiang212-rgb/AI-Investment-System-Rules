#!/usr/bin/env python3
"""记分卡预测式打分（董事局工单2026-07-17·乙）· 只读不下单

规格（架构师定·董事长拍板）：
  每层每天记一条【有期限、可结算】的预测（如"未来5交易日 SOXX 不收破20日线·把握中"），
  **到期结算对/错才进判对率**；状态读数照展示，但**不再当预测计入判对率**。
  判对率口径改为"预测结算"，旧的"状态当预测"废弃。

为什么要改：旧口径把"今天状态=走弱"当成一条预测记分——但那只是描述今天，不是预测明天，
  判对率因此没有意义。新口径每条预测都写死"赌什么、赌到哪天、拿什么结算"，到期用真数据判。

⚠边界：预测【内容】由各层的规则引擎按当日状态机械生成(不是我拍脑袋)，
  结算也用真行情数据机械判定；缺真源→标"无法结算·不计入"，不编。

产物：data/pdca/forecast_ledger.json
用法：python scripts/forecast_ledger.py --date 20260717     # 下预测 + 结算到期的
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
LEDGER = ROOT / "data" / "pdca" / "forecast_ledger.json"
HORIZON_DAYS = 5          # 预测期限：未来5个交易日


def _load() -> dict:
    if LEDGER.exists():
        try:
            return json.loads(LEDGER.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"forecasts": []}


def _daily(date: str) -> dict:
    try:
        return json.loads((ROOT / "data" / "evidence_chain" / f"daily_{date}.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def _bench(date: str, code: str):
    """取某日某参照物的涨跌%(真源=day_change_scan)。缺→None(不编)。"""
    try:
        d = json.loads((ROOT / "data" / "market" / f"day_change_{date}.json").read_text(encoding="utf-8"))
        v = (d.get("changes") or {}).get(code) or {}
        return v.get("change_pct") if v.get("status") == "OK" else None
    except Exception:
        return None


# 每层下什么预测：由当日状态机械推出「赌什么·拿什么结算」
def _make(layer: str, state: str, strength: str, date: str) -> dict | None:
    due = (datetime.strptime(date, "%Y%m%d") + timedelta(days=HORIZON_DAYS + 2)).strftime("%Y%m%d")
    conf = {"强": "高", "中": "中", "弱": "低"}.get(str(strength).strip(), "中")
    if "板块" in layer:
        if "走弱" in state:
            return {"claim": f"未来 {HORIZON_DAYS} 个交易日内，半导体(SOXX)不会出现累计 +5% 以上的强反弹",
                    "settle_by": "SOXX 区间累计涨跌%", "code": "US.SOXX", "op": "lt", "target": 5.0}
        if "走强" in state:
            return {"claim": f"未来 {HORIZON_DAYS} 个交易日内，半导体(SOXX)不会累计跌破 -5%",
                    "settle_by": "SOXX 区间累计涨跌%", "code": "US.SOXX", "op": "gt", "target": -5.0}
        return None
    if "资金" in layer:
        if "不避险" in state or "中性" in state:
            return {"claim": f"未来 {HORIZON_DAYS} 个交易日内，市场不会转入明显避险（标普不累计跌破 -5%）",
                    "settle_by": "SPY 区间累计涨跌%", "code": "US.SPY", "op": "gt", "target": -5.0}
        return {"claim": f"未来 {HORIZON_DAYS} 个交易日内，避险情绪不会立刻消退（标普不累计涨过 +5%）",
                "settle_by": "SPY 区间累计涨跌%", "code": "US.SPY", "op": "lt", "target": 5.0}
    if "战略" in layer:
        return {"claim": f"未来 {HORIZON_DAYS} 个交易日内，AI 主线不会被证伪（半导体不累计跌破 -10%）",
                "settle_by": "SOXX 区间累计涨跌%", "code": "US.SOXX", "op": "gt", "target": -10.0}
    if "总闸" in layer or "世界" in layer or "总命题" in layer:
        # 这两层是"事件驱动、以周为单位"→预测"本期内不出反向大事"，用当日新闻机械结算
        return {"claim": f"未来 {HORIZON_DAYS} 个交易日内，这一层不会出现翻转级事件（状态维持「{state}」）",
                "settle_by": "该层状态是否翻转", "code": "", "op": "state_hold", "target": state}
    return None


def _settle(f: dict, today: str) -> dict | None:
    """到期结算：用真数据判对/错。缺真源→标"无法结算·不计入"。"""
    if f.get("result"):
        return None
    if today < str(f["due_date"]):
        return None
    op, code = f["op"], f.get("code")
    if op == "state_hold":
        d = _daily(today)
        cur = ""
        for L in d.get("links", []) or []:
            if f["layer"] in str(L.get("node", "")):
                cur = str(L.get("_state") or L.get("direction") or "")
                break
        if not cur:
            return {"result": "无法结算", "why": "到期日没有该层的状态真数据 → 不计入判对率(不编)"}
        hold = str(f["target"]) in cur or cur in str(f["target"])
        return {"result": "对" if hold else "错", "actual": cur,
                "why": f"预测「维持{f['target']}」；到期实际是「{cur}」→ {'兑现' if hold else '没兑现'}"}
    # 区间累计涨跌%：把下预测那天到今天的每日涨跌复利起来(真源=day_change)
    d0 = datetime.strptime(str(f["date"]), "%Y%m%d")
    acc, n, miss = 1.0, 0, 0
    for i in range(1, HORIZON_DAYS + 3):
        dt = (d0 + timedelta(days=i)).strftime("%Y%m%d")
        if dt > today:
            break
        c = _bench(dt, code)
        if c is None:
            miss += 1
            continue
        acc *= (1 + c / 100.0)
        n += 1
    if n == 0:
        return {"result": "无法结算", "why": f"这段时间没有 {code} 的真涨跌数据（缺 {miss} 天）→ 不计入判对率(不编)"}
    pct = (acc - 1) * 100
    ok = (pct < f["target"]) if op == "lt" else (pct > f["target"])
    return {"result": "对" if ok else "错", "actual": round(pct, 2),
            "why": f"{code} 这 {n} 个交易日累计 {pct:+.2f}%；预测要求 {'低于' if op == 'lt' else '高于'} "
                   f"{f['target']:+.0f}% → {'兑现' if ok else '没兑现'}"}


def build(date: str) -> dict:
    led = _load()
    fs = led.get("forecasts", [])
    d = _daily(date)
    # ① 结算所有到期的
    settled = 0
    for f in fs:
        r = _settle(f, date)
        if r:
            f.update(r)
            f["settled_at"] = date
            settled += 1
    # ② 给今天每层下一条新预测(同层同日只下一条)
    added = []
    for L in d.get("links", []) or []:
        layer = str(L.get("node", ""))
        state = str(L.get("_state") or L.get("direction") or "")
        if not layer or not state:
            continue
        if any(x["layer"] == layer and x["date"] == date for x in fs):
            continue
        m = _make(layer, state, str(L.get("strength", "")), date)
        if not m:
            continue
        due = (datetime.strptime(date, "%Y%m%d") + timedelta(days=HORIZON_DAYS + 2)).strftime("%Y%m%d")
        f = {"layer": layer, "date": date, "due_date": due, "state_when_made": state,
             "confidence": {"强": "高", "中": "中", "弱": "低"}.get(str(L.get("strength", "")).strip(), "中"),
             "result": "", **m}
        fs.append(f)
        added.append(f)
    fs.sort(key=lambda x: (str(x["date"]), x["layer"]))
    # ③ 判对率 = 只数【已结算】的(无法结算的不计入)
    done = [f for f in fs if f.get("result") in ("对", "错")]
    hit = sum(1 for f in done if f["result"] == "对")
    by_layer = {}
    for f in done:
        b = by_layer.setdefault(f["layer"], {"n": 0, "hit": 0})
        b["n"] += 1
        b["hit"] += 1 if f["result"] == "对" else 0
    return {"forecasts": fs, "added": added, "settled": settled,
            "accuracy": {"settled_total": len(done), "hit": hit,
                         "rate_pct": (round(hit / len(done) * 100, 1) if done else None),
                         "by_layer": by_layer,
                         "pending": len([f for f in fs if not f.get("result")]),
                         "unsettleable": len([f for f in fs if f.get("result") == "无法结算"])}}


def main() -> int:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="记分卡预测式打分")
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    r = build(a.date)
    doc = {"_说明": "预测式打分台账。每层每天下一条【有期限可结算】的预测，到期用真数据判对/错，"
                   "**只有已结算的才进判对率**。状态读数照展示但不当预测计分——"
                   "旧的『状态当预测』口径已废弃(那只是描述今天、不是预测明天)。",
           "_期限": f"{HORIZON_DAYS} 个交易日",
           "date": a.date, "generated_at": datetime.now(JST).isoformat(timespec="seconds"),
           "accuracy": r["accuracy"], "forecasts": r["forecasts"][-80:]}
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    acc = r["accuracy"]
    print(f"wrote {LEDGER.name} · 今日新下 {len(r['added'])} 条 · 本次结算 {r['settled']} 条")
    for f in r["added"]:
        print(f"   + {f['layer'][:12]:14s} {f['claim'][:52]} (把握{f['confidence']}·到期{f['due_date']})")
    print(f"   判对率(只算已结算)：{acc['hit']}/{acc['settled_total']}"
          + (f" = {acc['rate_pct']}%" if acc["rate_pct"] is not None else " → 还没有到期的，先攒着")
          + f" · 未到期 {acc['pending']} 条 · 无法结算 {acc['unsettleable']} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
