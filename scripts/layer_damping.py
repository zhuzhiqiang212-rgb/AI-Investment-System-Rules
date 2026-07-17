#!/usr/bin/env python3
"""层间阻尼（董事局工单2026-07-17·乙）· 只读不下单

治「单日噪声翻状态」：SOXX 今天 ±1% 就把板块从"走强"翻成"走弱"，明天又翻回来——
董事长看到的是天天变卦，其实只是噪声。

规格（架构师定）：每层取 2-3 个读数 + 5 日平滑 + 滞后带——
  **翻状态需 ①连续 2 日同向 或 ②超 2 倍阈值**；否则维持上一状态。

  · 板块：SOXX 现 ±1% → 改为需 ±2%(2倍)、或连 2 日 ±1%
  · 资金：VIX + 曲线(10Y-3M) + 高收益利差 三读数同理

⚠这是【改尺】：董事长 2026-07-17 已拍板采纳架构师规格，本模块按规格实现，不自行加码。
判断口径不变——只是把"翻不翻"从"看今天一天"改成"看连续2日/超2倍"。

产物：data/evidence_chain/damping_{date}.json（记每层的读数序列/是否翻/为什么）
用法：from layer_damping import damp; damp(layer, today_state, readings, date)
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOOTH_DAYS = 5          # 5日平滑窗
NEED_CONSEC = 2          # 连续2日同向才准翻
BIG_MULT = 2.0           # 或超2倍阈值可当日翻


def _prev_dates(date: str, n: int) -> list:
    try:
        d = datetime.strptime(date, "%Y%m%d").date()
    except Exception:
        return []
    return [(d - timedelta(days=i)).strftime("%Y%m%d") for i in range(1, n + 1)]


def _hist_state(layer: str, date: str, n: int) -> list:
    """往回读真实历史的该层状态(近n天·缺就跳过·不编)。"""
    out = []
    for d in _prev_dates(date, n * 2):        # 多找几天(周末没数据)
        p = ROOT / "data" / "evidence_chain" / f"daily_{d}.json"
        if not p.exists():
            continue
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for L in j.get("links", []) or []:
            if layer in str(L.get("node", "")):
                out.append({"date": d, "state": str(L.get("_state") or L.get("direction") or "")})
                break
        if len(out) >= n:
            break
    return out


def damp(layer: str, raw_state: str, readings: list, date: str, threshold: float | None = None) -> dict:
    """把"今天算出来的裸状态"过一遍阻尼，返回该不该真翻。

    layer      层名(如"板块轮动")
    raw_state  今天按阈值算出的裸状态
    readings   [{"name":"SOXX","value":-4.46,"threshold":1.0}, ...] 本层的2-3个读数
    返回 {"state": 采用的状态, "flipped": 是否真翻, "why": 人话原因, ...}
    """
    hist = _hist_state(layer, date, SMOOTH_DAYS)
    prev = hist[0]["state"] if hist else ""
    if not prev or raw_state == prev:
        return {"state": raw_state, "flipped": False, "prev": prev, "damped": False,
                "why": ("首日·无上一状态可比" if not prev else f"与上一状态一致（{prev}）→ 不涉及翻不翻"),
                "readings": readings, "hist": hist}
    # ① 超 2 倍阈值 → 当日就准翻(真出大事了·不该压)
    big = []
    for r in readings:
        th = r.get("threshold") or threshold
        v = r.get("value")
        if th and isinstance(v, (int, float)) and abs(v) >= abs(th) * BIG_MULT:
            big.append(f'{r.get("name")} {v:+.2f}（超阈值{abs(th):.1f}的{BIG_MULT:g}倍）')
    if big:
        return {"state": raw_state, "flipped": True, "prev": prev, "damped": False,
                "why": f"动静够大→当日就认：{'、'.join(big)}；不用等第二天确认",
                "readings": readings, "hist": hist, "rule": "超2倍阈值"}
    # ② 连续 2 日同向 → 准翻
    same = 1 + sum(1 for h in hist[:NEED_CONSEC - 1] if h["state"] == raw_state)
    if same >= NEED_CONSEC:
        return {"state": raw_state, "flipped": True, "prev": prev, "damped": False,
                "why": f"已经连续 {same} 天都是「{raw_state}」→ 不是一天的噪声，认了",
                "readings": readings, "hist": hist, "rule": "连续2日同向"}
    # ③ 都不满足 → 压住，维持上一状态
    rd = "、".join(f'{r.get("name")} {r.get("value"):+.2f}' for r in readings
                   if isinstance(r.get("value"), (int, float)))
    return {"state": prev, "flipped": False, "prev": prev, "damped": True, "raw_state": raw_state,
            "why": (f"今天的数（{rd}）按老规矩会翻成「{raw_state}」，但<b>只动了这一天、也没超两倍阈值</b>"
                    f"→ 按阻尼规矩<b>先不翻</b>，维持「{prev}」。"
                    f"要么明天还这样、要么动静再大一倍，才算数——治的就是天天变卦。"),
            "readings": readings, "hist": hist, "rule": "未达连续2日/未超2倍→压住"}


def log(date: str, recs: dict) -> None:
    p = ROOT / "data" / "evidence_chain" / f"damping_{date}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(
        {"_说明": "层间阻尼台账：每层今天的裸状态/读数/是否真翻/为什么。"
                  "规矩=翻状态需【连续2日同向】或【超2倍阈值】，否则维持上一状态(治单日噪声翻状态)。",
         "date": date, "smooth_days": SMOOTH_DAYS, "need_consecutive": NEED_CONSEC,
         "big_multiple": BIG_MULT, "layers": recs},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
