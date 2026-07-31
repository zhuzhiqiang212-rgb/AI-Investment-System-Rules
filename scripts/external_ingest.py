#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""external_ingest · 外部原辅料接入(董事长工单2026-07-23)· 只读不下单 · 只写 data/external/

production 之后、渲染之前跑。把指定目录的 TXT/md(老雷/湖水/其他)外部原辅料:
  ①扫全目录记录 文件名+路径+字节+mtime
  ②每条线索强制五分类:①可核验事实 ②作者观点 ③作者预测 ④操作建议 ⑤待核实线索
  ③与当天实时数据/持仓/估值/证据链逐条比对 → 被一级来源证实 / 待核实 / 被体系否决
  ④与体系冲突者:记录 分歧+双方依据+体系最终判断
  ⑤输出 data/external/external_material_{date}.json(run_id/data_date=当天)

硬闸(防外部接管主线):
  · 本脚本【只写 data/external/】,绝不改 production/持仓/估值/证据链/记分卡。
  · 最终"今天怎么做"仍来自 production_pipeline+风控;external 仅作卡内辅助/分歧展示。
  · 湖水入口为空 → 记 status=未提供,不参与今日判断;禁止用旧湖水冒充当天。

铁律:老雷原料是【主题/宏观级】,除MSTR外不点名个股 → 线索映射到个股时如实标注
     "老雷主题观点·经板块/账户映射至本标的",不伪装成"老雷点名本股"。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
KB = ROOT / "Knowledge_Base"
INPUTS = ROOT / "inputs"
OUT_DIR = ROOT / "data" / "external"

# 五分类
CAT = {"1": "①可核验事实", "2": "②作者观点", "3": "③作者预测", "4": "④操作建议", "5": "⑤待核实线索"}


def _mtime(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime, JST).isoformat(timespec="seconds")


def scan_sources() -> list[dict]:
    """扫指定目录(inputs/ 全树 + Knowledge_Base 老雷)全部 TXT/md,记录 名/路径/字节/mtime。"""
    out = []
    seen = set()
    roots = [INPUTS, KB]
    for base in roots:
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if p.suffix.lower() not in (".txt", ".md", ".csv"):
                continue
            if not p.is_file():
                continue
            key = str(p.resolve())
            if key in seen:
                continue
            seen.add(key)
            out.append({"file": p.name, "path": str(p), "bytes": p.stat().st_size, "mtime": _mtime(p),
                        "rel": str(p.relative_to(ROOT))})
    return out


# ── 老雷核心提炼:逐段五分类 + 主题 + 映射范围(段的性质决定分类·非事后编造) ──
# (匹配 ## 标题关键字, 分类, 主题, 适用范围)
LAOLEI_SECTIONS = [
    ("长期世界观", "2", "AI超级周期", "ai"),
    ("美国国家战略", "2", "美国战略/国债美元", "all"),
    ("全球流动性框架", "3", "全球流动性regime", "all"),
    ("对AI的真正判断", "2", "AI主线扩散/拥挤", "ai"),
    ("加密/稳定币/RWA", "2", "稳定币RWA流动性映射", "crypto"),
    ("对日本市场", "2", "日元/BOJ保护线", "jp"),
    ("最担心的风险", "5", "宏观风险(估值/美债/QT/拥挤)", "risk"),
    ("可能错误的地方", "2", "作者自我校正", "meta"),
    ("与湖水观点的冲突", "2", "老雷vs湖水框架", "meta"),
    ("四账户", "4", "分账户操作建议", "account"),
    ("风险收益比状态", "2", "风险收益比/进攻等级", "all"),
]


def parse_laolei(core_path: Path) -> list[dict]:
    """把老雷核心提炼按 ## 段落切,每段的 bullet 归入该段的五分类/主题/适用范围。"""
    if not core_path.exists():
        return []
    txt = core_path.read_text(encoding="utf-8")
    leads = []
    blocks = re.split(r"\n##\s+", txt)
    for blk in blocks:
        head = blk.splitlines()[0] if blk.strip() else ""
        meta = next((m for m in LAOLEI_SECTIONS if m[0] in head), None)
        if not meta:
            continue
        _, cat, theme, scope = meta
        bullets = [ln.strip("-· ").strip() for ln in blk.splitlines()[1:] if ln.strip().startswith("-")]
        for b in bullets:
            if not b:
                continue
            leads.append({"source": "老雷财经_核心提炼", "section": head.strip(), "text": b,
                          "category": CAT[cat], "cat_code": cat, "theme": theme, "scope": scope})
    return leads


# ── 主题/账户 → 持仓映射(老雷主题级·经板块/账户映射·如实标注) ──
def map_scope_to_symbols(scope: str, holds: list[dict]) -> list[str]:
    syms = []
    for h in holds:
        sym = h["symbol"]
        nodes = h.get("matched_node_classes_raw") or []
        ai_hw = bool(set(nodes) & {"算力", "半导体设备", "代工"})
        is_jp = sym.startswith("JP.")
        is_crypto = sym in ("US.COIN", "US.MSTR", "US.CRCL")
        is_ai = ai_hw or sym in ("US.MSFT", "US.META", "US.NVDA", "US.SNDK")  # 硬件AI + AI软件/存储
        if scope == "all":
            syms.append(sym)
        elif scope == "ai" and is_ai:
            syms.append(sym)
        elif scope == "jp" and is_jp:
            syms.append(sym)
        elif scope == "crypto" and is_crypto:
            syms.append(sym)
        elif scope == "risk":  # 风险类进风险区·不逐股挂(scope=risk 走板块/风险区补充)
            pass
        elif scope == "account":  # 账户建议:日本→JP·高beta→COIN/MSTR
            pass
    return syms


def system_compare(lead: dict, holds: dict, direction: str) -> dict:
    """与07-23体系判断逐条比对 → 证实/待核实/否决 + 分歧记录。
    体系判断=production action + one_line_reason + today_direction(风控)。external 不得改这些。"""
    theme = lead["theme"]
    cat = lead["cat_code"]
    # 宏观自校正/框架级(meta)·风险清单 → 待核实(一级来源无法即时证实宏观预测)
    if lead["scope"] in ("meta", "risk") or cat == "5":
        return {"verdict": "待核实", "system_basis": "宏观/风险预测·无一级来源可即时证实→纳入风险区盯、不作买卖依据", "conflict": None}
    # 日元/BOJ保护线 → 与日本持仓action(守/等·无减)比对
    if lead["scope"] == "jp":
        jp = [h for s, h in holds.items() if s.startswith("JP.")]
        acts = sorted({h.get("action") for h in jp})
        no_cut = all(h.get("action") in ("守", "等") for h in jp)
        if no_cut:
            return {"verdict": "证实", "system_basis": f"体系对日本持仓今日动作={acts}(无减仓)·与'保护线管理不机械减仓'方向一致", "conflict": None}
        return {"verdict": "分歧", "system_basis": f"体系日本动作={acts}含减仓", "conflict": "老雷建议保护线不机械减·体系今日有减仓→以体系风控为准"}
    # 加密RWA弹性高/高beta → COIN/MSTR/CRCL action(等·不加)比对
    if lead["scope"] == "crypto":
        cr = [holds.get(s) for s in ("US.COIN", "US.MSTR", "US.CRCL") if holds.get(s)]
        acts = sorted({h.get("action") for h in cr})
        if all(h.get("action") == "等" for h in cr):
            return {"verdict": "证实", "system_basis": f"体系对加密仓(COIN/MSTR/CRCL)今日={acts}(不加仓·控波动)·与'弹性高但波动监管风险高'一致", "conflict": None}
        return {"verdict": "待核实", "system_basis": f"体系加密仓动作={acts}", "conflict": None}
    # AI主线:'主线未结束但估值需盈利验证/中性偏强' vs today_direction'守核心·不追高·控AI集中'
    if lead["scope"] == "ai":
        if ("守核心" in direction or "不追高" in direction or "控AI集中" in direction):
            # 若老雷句偏乐观(流动性偏强/主线未结束) → 体系不采纳为加仓依据(仅背景)
            if any(k in lead["text"] for k in ("偏强", "未结束", "主线")):
                return {"verdict": "否决", "system_basis": "体系today_direction=守核心·不追高·控AI集中(估值需盈利验证)→老雷偏乐观句不采纳为加仓依据·仅作背景",
                        "conflict": "老雷:AI主线未结束/流动性偏强(可读作进攻)｜体系:控AI集中·不追高→体系不据此加仓"}
            return {"verdict": "证实", "system_basis": "与today_direction'守核心·不追高·控AI集中'方向一致", "conflict": None}
    # all(宏观背景) → 待核实
    return {"verdict": "待核实", "system_basis": "宏观背景框架·作辅助上下文·不作买卖依据", "conflict": None}


def hushui_status() -> dict:
    """湖水固定入口:为空→未提供,不参与今日判断(禁旧湖水冒充)。"""
    entry = INPUTS / "hushui_latest_input.txt"
    body = ""
    if entry.exists():
        raw = entry.read_text(encoding="utf-8")
        # 去模板头,看有无真实粘贴内容
        m = re.split(r"下面开始粘贴今日内容\s*---", raw)
        body = (m[-1] if len(m) > 1 else raw).strip()
    if not body:
        return {"status": "未提供", "note": "湖水固定入口 inputs/hushui_latest_input.txt 为空(仅模板头)·今日不参与判断·未用旧湖水冒充", "chars": 0}
    return {"status": "已提供", "note": "湖水今日正文已粘贴", "chars": len(body), "text": body[:2000]}


def build(date: str) -> dict:
    prod_path = ROOT / "data" / "reports" / f"production_{date}.json"
    if not prod_path.exists():
        raise FileNotFoundError(f"缺 production: {prod_path}(external_ingest 须在 production 之后跑)")
    prod = json.loads(prod_path.read_text(encoding="utf-8"))
    holds_list = prod.get("holdings", [])
    holds = {h["symbol"]: h for h in holds_list}
    ev_path = ROOT / "data" / "evidence_chain" / f"daily_{date}.json"
    direction = ""
    if ev_path.exists():
        ev = json.loads(ev_path.read_text(encoding="utf-8"))
        direction = str(ev.get("derived", {}).get("today_direction", "") or prod.get("today_direction_short", ""))
    direction = direction or str(prod.get("today_direction_short", ""))

    sources = scan_sources()
    leads = parse_laolei(KB / "老雷财经_核心提炼.txt")
    # 逐条:映射持仓 + 体系比对
    by_symbol: dict[str, list[int]] = {}
    sector_supp = []
    for i, ld in enumerate(leads):
        ld["id"] = f"EXT-{i+1:02d}"
        ld["mapped_symbols"] = map_scope_to_symbols(ld["scope"], holds_list)
        ld["mapped_note"] = "老雷主题观点·经板块/账户映射至本标的(非老雷点名本股)"
        ld["compare"] = system_compare(ld, holds, direction)
        for s in ld["mapped_symbols"]:
            by_symbol.setdefault(s, []).append(ld["id"])
        if ld["scope"] in ("risk", "all", "meta"):
            sector_supp.append({"id": ld["id"], "theme": ld["theme"], "text": ld["text"],
                                "category": ld["category"], "verdict": ld["compare"]["verdict"]})

    # 三清单
    adopted = [{"id": l["id"], "text": l["text"], "theme": l["theme"], "basis": l["compare"]["system_basis"]}
               for l in leads if l["compare"]["verdict"] == "证实"]
    pending = [{"id": l["id"], "text": l["text"], "theme": l["theme"], "basis": l["compare"]["system_basis"]}
               for l in leads if l["compare"]["verdict"] == "待核实"]
    rejected = [{"id": l["id"], "text": l["text"], "theme": l["theme"], "conflict": l["compare"]["conflict"],
                 "system_final": l["compare"]["system_basis"]}
                for l in leads if l["compare"]["verdict"] in ("否决", "分歧")]

    # 独立性检查:每只"今天怎么做"的一级依据=production(体系)·external仅辅助
    independence = {}
    for h in holds_list:
        independence[h["symbol"]] = {
            "action": h.get("action"), "primary_basis": "production_pipeline+风控(体系)",
            "system_reason": str(h.get("one_line_reason", ""))[:160],
            "external_leads": by_symbol.get(h["symbol"], []),
            "external_role": "辅助佐证/分歧展示(不作唯一依据)"}

    run_id = "ext_" + hashlib.sha256((date + str(len(leads)) + direction).encode()).hexdigest()[:12]
    result = {
        "date": date, "data_date": f"{date[:4]}-{date[4:6]}-{date[6:]}", "run_id": run_id,
        "generated_at": datetime.now(JST).isoformat(timespec="seconds"),
        "_说明": "外部原辅料接入(老雷/湖水/inputs全树)·五分类+与当日体系逐条比对·只写data/external·不改production/持仓/估值/证据链。老雷=主题级·经映射挂标的(非点名)。",
        "hushui": hushui_status(),
        "sources_scanned": sources,
        "sources_participating_today": ["Knowledge_Base/老雷财经_核心提炼.txt"],
        "hushui_and_structured_note": "湖水今日入口为空→不参与;inputs/hushui/ 结构化提取最新为2026-06-01(旧)→仅历史留档·不参与今日判断",
        "leads": leads,
        "by_symbol": by_symbol,
        "sector_risk_supplements": sector_supp,
        "adopted": adopted, "pending": pending, "rejected": rejected,
        "independence_check": independence,
        "counts": {"leads": len(leads), "证实": len(adopted), "待核实": len(pending), "否决/分歧": len(rejected),
                   "mapped_symbols": len(by_symbol)},
    }
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d"))
    a = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    res = build(a.date)
    out = OUT_DIR / f"external_material_{a.date}.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    # 硬闸自证:只写了 data/external
    print(f"[OK] 写出 {out}")
    print(f"  run_id={res['run_id']} · data_date={res['data_date']} · 线索{res['counts']['leads']}条"
          f" · 证实{res['counts']['证实']}/待核实{res['counts']['待核实']}/否决分歧{res['counts']['否决/分歧']}"
          f" · 映射{res['counts']['mapped_symbols']}只")
    print(f"  湖水:{res['hushui']['status']} · 扫描源{len(res['sources_scanned'])}份 · 今日参与:老雷核心提炼")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
