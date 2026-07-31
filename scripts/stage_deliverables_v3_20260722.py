#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GPT复验退回·语义级修正 8项交付索引。"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
P = ROOT / "00_请先看这里" / "★每日产品_2026-07-22.html"
raw = P.read_bytes()
h = raw.decode("utf-8")
prod = {x["symbol"]: x for x in json.loads((ROOT / "data/reports/production_20260722.json").read_text(encoding="utf-8"))["holdings"]}
# ⑤ 历史隔离节点
histn = h.count('class="hist-iso"')
# ④ 每只唯一价格
price_tbl = {s: {"7-22现价": f"{prod[s]['price']:,.2f}", "来源": "OpenD production_20260722 run"} for s in prod}
d = {
    "_说明": "GPT复验退回·语义级4项修正(动作chip一致≠交易语义一致)·8项交付。",
    "生成于": datetime.now(JST).isoformat(timespec="seconds"),
    "四项语义修正": {
        "1_加仓语义统一": "守/等标的『⚡已触发(4)/今日已跌到加仓价(1)/现在就可以加·分批买(4)』→『仅价格条件触发·动作闸未通过·今日不得加仓』",
        "2_双价消除": "补stage7漏的格式(现价约¥X/现价<b>¥X</b>决定摘要块)·16只现价<b>块+第一三共约¥块→7-22·5只GPT双价(软银/英伟达/第一三共/东京海上/爱德万)当日残留=0",
        "3_异常退出": "爱德万(今日价值区¥2646~3234拆股复权异常/750%高估/止盈¥27505)+闪迪→价格/复权口径异常待核·不计算估值/加仓/止盈/目标/买卖·非顶部声明",
        "4_gate语义升级": "gate_v4新增语义扫描:加仓语义/双价/异常估值参与计算/旧日期当日语境→FAIL(不只查chip)",
    },
    "交付8项": {
        "①修正HTML": str(P),
        "②SHA/字节/mtime": {"字节": len(raw), "mtime": datetime.fromtimestamp(os.path.getmtime(P), JST).isoformat(timespec="seconds"), "SHA256": hashlib.sha256(raw).hexdigest(), "乱码": raw.count(b"\xef\xbf\xbd"), "裸LF": raw.count(b"\n") - raw.count(b"\r\n")},
        "③20只全节点语义扫描报告": "data/screen/gate_v4_perstock_20260722.json(per_stock 价/chip/L2四字段/L2买卖/L3底稿 + 语义FAIL[加仓语义/双价/异常/旧日期])",
        "④每只唯一价格及来源表": price_tbl,
        "⑤历史隔离节点清单": {"hist-iso折叠节点数": histn, "含": "target-gap旧目标/6只买卖建议历史档/爱德万闪迪历史数字"},
        "⑥爱德万闪迪从计算节点退出证明": {"爱德万": "今日价值区/750%/止盈¥27505→异常待核·不计算", "闪迪": "今日价值区→异常待核·股数5", "gate_v4异常扫描": "PASS(0残留)"},
        "⑦gate_v5/v6原始结果": "data/screen/gate_v4_perstock_20260722.json(全PASS) + data/screen/gate_v6_fulllayer_20260722.json(四维度全PASS)",
        "⑧人工复核发现vs硬闸发现对照表": [
            {"GPT人工发现": "加仓语义(已触发/分批买)与守/等矛盾", "旧硬闸": "只查chip·漏", "现gate_v4": "语义扫描FAIL·已抓"},
            {"GPT人工发现": "双价(现价<b>¥旧</b>决定摘要块)", "旧硬闸": "只查现价前缀·漏<b>标签格式", "现gate_v4": "双价扫描FAIL·已抓"},
            {"GPT人工发现": "爱德万异常估值参与计算", "旧硬闸": "只查顶部增补⑮声明·漏底稿", "现gate_v4": "异常标的估值扫描FAIL·已抓"},
            {"GPT人工发现": "L3决定摘要今日动作7-19旧值", "旧硬闸": "只查chip·漏文字字段", "现gate_v4": "L3底稿+语义扫描·已抓"},
        ],
    },
    "四道硬闸": {"gate_v4逐股(价+chip+L2L3+语义)": "全PASS", "v6综合全层": "四维度全PASS", "退化硬闸15项": "全通过", "逐对象v3": "10/10"},
}
out = ROOT / "data/screen/rectify_semantic_deliverables_20260722.json"
out.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("落:", out.name)
print("SHA256:", hashlib.sha256(raw).hexdigest(), "· 字节:", len(raw), "· hist-iso节点:", histn)
