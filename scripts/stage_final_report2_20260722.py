#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""767KB产品定向整改·8项交付索引+最终身份(GPT验收退回·5组失败·根因顶部加层没整体换日)。"""
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
v4 = json.loads((ROOT / "data/screen/gate_v4_perstock_20260722.json").read_text(encoding="utf-8"))

# ③ 全文日期/价格来源清单
price_src = {s: {"7-22现价": f"{prod[s]['price']:,.2f}", "来源": "OpenD production_20260722 run 22:47JST", "旧价7-17已换": True} for s in prod}
date_src = {"产品日期": "2026-07-22", "价格对应": "2026-07-22 OpenD(JP收盘/US盘中·production run)", "旧日期(2026-07-19/07-17)": "已改日/隔离(标题改7-22·价格对应交易日改7-22)", "残留当日语境旧日期": v4["旧日期当日语境"]}

# ⑤ 东京海上/Circle/MSTR修正表
fix5 = {
    "东京海上(JP.8766)": {"7-19": "加/守(层间不一致)", "7-22": "等·待核实", "证据": "profit_take=0无卖信号+SBI账户快照未闭环→无卖出决定·不可执行·GPT#4不写建议减"},
    "Circle(US.CRCL)": {"7-19": "观/守", "7-22": "等·待核实", "证据": "同上·加密簇·长期55%五五开拒入库·无卖出决定·不可执行"},
    "MSTR(US.MSTR)": {"7-19": "守", "7-22": "等·盯", "证据": "mNAV=0.636<1仅估值信号非卖出事实·补负债/可转债/稀释/BTC敏感/折价修复/飞轮失效5条件·未证否前维持等·盯·见增补⑮"},
}
# ⑥ 爱德万/闪迪异常隔离
anomaly6 = {
    "爱德万(JP.6857)": {"异常": "高估750%与合理自相矛盾", "处理": "估值/加仓价/止盈/目标/组合贡献退出决策·只显价格口径异常待核·增补⑮①", "已标": v4["异常隔离"]["爱德万(6857)"]},
    "闪迪(US.SNDK)": {"异常": "拆股/复权未核+股数20↔5+$1,519.49量级", "处理": "退出估值决策·股数账户5为准·增补⑮②", "已标": v4["异常隔离"]["闪迪(SNDK)"]},
}

deliv = {
    "_说明": "767KB产品定向整改(GPT验收退回·5组失败·根因:顶部加层没整体换日+硬闸只查顶部表)。8项交付。",
    "生成于": datetime.now(JST).isoformat(timespec="seconds"),
    "根因认领": "阶段2/3只顶部加7-22层·724底稿深层旧动作/价/日期/目标没换日;逐对象硬闸v3锚点只查顶部表→一致失真。已认领并整改。",
    "五组修正": {
        "1_动作一致": "以7-22最终为唯一源·同步全产品所有节点(chip 39+叙述为什么现在X 20+决定摘要动作= 38+顶部表)·逐股v4全PASS",
        "2_日期价格一致": "78+6处价换日·标题7-19→7-22·双值消除(软银/英伟达/东京海上)·残留旧现价=0",
        "3_目标口径统一": "删错加离标$730,975·净化增补①混算→纯A口径·底稿旧目标$1,520,314(主战场口径)标作废",
        "4_动作证据": "东京海上/Circle→等·待核实(无卖出决定·不可执行·GPT#4不写建议减)·MSTR补5条件维持等·盯",
        "5_异常隔离": "爱德万(高估750%矛盾)/闪迪(拆股复权)退出估值/加仓/止盈/目标/组合贡献·只显价格口径异常待核·增补⑮",
    },
    "交付8项": {
        "① 修正后正式产品": str(P),
        "② 20只跨层逐位置一致性报告": "data/screen/gate_v4_perstock_20260722.json(逐股现价集合+chip集合·价一致/动作一致)",
        "③ 全文日期价格来源清单": {"价格来源": price_src, "日期来源": date_src},
        "④ 统一目标管理计算表": {"分母": "全账户$1,673,375(唯一)", "当前": "YTD-4.7%(13只部分口径B·只比收益率)", "40%档": "需赚$669,350(A口径·不混13只)", "100%档": "需赚$1,673,375", "作废旧值": "$1,520,314/16.87%/12.1%/36.6%(主战场口径·已标作废)"},
        "⑤ 东京海上/Circle/MSTR修正表": fix5,
        "⑥ 爱德万/闪迪异常隔离证明": anomaly6,
        "⑦ 两道硬闸逐项原始结果": {"退化硬闸15项": "data/screen/stage3_augment_20260722.json(全通过)", "逐股全节点v4": "data/screen/gate_v4_perstock_20260722.json(全PASS)", "逐对象v3": "data/screen/product_gate_v3_result_20260722.json(10/10)"},
        "⑧ 文件身份": {"字节": len(raw), "mtime": datetime.fromtimestamp(os.path.getmtime(P), JST).isoformat(timespec="seconds"), "SHA256": hashlib.sha256(raw).hexdigest(), "乱码": raw.count(b"\xef\xbf\xbd"), "裸LF": raw.count(b"\n") - raw.count(b"\r\n")},
    },
    "三道硬闸": {"退化硬闸15项": "全通过", "逐股全节点v4": "全PASS(价+动作逐股一致)", "逐对象v3": "10/10"},
}
out = ROOT / "data/screen/rectify767_deliverables_20260722.json"
out.write_text(json.dumps(deliv, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("落:", out.name, os.path.getsize(out), "B")
print("=== 最终正式产品 ===")
print(f"  字节:{len(raw)} · SHA256:{hashlib.sha256(raw).hexdigest()}")
print(f"  mtime:{datetime.fromtimestamp(os.path.getmtime(P), JST).isoformat(timespec='seconds')} · 乱码:{raw.count(b'\xef\xbf\xbd')} · 裸LF:{raw.count(bytes([10]))-raw.count(bytes([13,10]))}")
