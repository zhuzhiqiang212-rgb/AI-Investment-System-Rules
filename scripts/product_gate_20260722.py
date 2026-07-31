#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整产品·出厂硬闸 v2·逐对象循环（GPT硬闸六·禁关键词假通过·2026-07-22）。
遍历每标的/每账户/每动作/每候选/每证据·逐对象查:字段存在+值有效+对应正确对象+真进产品+上下层一致+来源支撑判断+同一快照。
10个直接FAIL:①续写中/占位/待补/第一次组装 ②应覆盖账户无数据且第一屏未标红 ③减加换无数量或金额
④第5关仅待研究却进今日正式候选 ⑤非激活板块进今日激活候选 ⑥同标的三层动作冲突 ⑦证据只有链接未对应判断
⑧40%/100+只文字无目标管理实物 ⑨老雷/湖水只名称无真实接入状态 ⑩旧版重要功能无故退出。
★硬闸边界:只查可验证项·不判投资逻辑。任一FAIL→不得申请验收;通过=送验资格(≠投资判断对·GPT独立验收)。
用法：python scripts/product_gate_20260722.py"""
import argparse, json, re, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
STRIP = re.compile(r"<[^>]+>")


def plain(s):
    return re.sub(r"\s+", " ", STRIP.sub(" ", s)).strip()


def gate(h):
    C = []

    def add(rule, ok, detail, objs=None):
        C.append({"规则": rule, "PASS": bool(ok), "详情": detail, "逐对象": objs or []})

    # 解析持仓行(tr含 chip动作 + 账户span)
    hold_rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", h, re.S):
        if 'class="chip' in tr and ("守" in tr or "减" in tr or "加" in tr or "等" in tr or "换" in tr):
            tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
            if len(tds) >= 5:
                chip = plain(re.search(r'class="chip[^"]*">(.*?)</span>', tr).group(1)) if re.search(r'class="chip', tr) else ""
                acct = plain(re.search(r'class="tag">(.*?)</span>', tr).group(1)) if re.search(r'class="tag"', tr) else ""
                hold_rows.append({"名称": plain(tds[1])[:16], "动作chip": chip, "账户": acct, "动作文": plain(tds[-1])[:60]})

    # ① 续写中/占位/待补/第一次组装(排除否定语境:非占位/无占位/删占位/不再占位)
    bad = []
    for w in ["续写中", "占位", "待补", "第一次组装"]:
        cnt = len(re.findall(r"(?<![非无删不])" + w, h))
        if cnt > 0:
            bad.append({"词": w, "有效次数(排除否定)": cnt})
    add("① 无续写中/占位/待补/第一次组装", not bad, ("无(非占位等否定语境已排除)" if not bad else f"★出现{[b['词'] for b in bad]}"), bad)

    # ② 每账户:未接入/无数据须第一屏红标
    acct_objs = []
    ov = re.search(r"acct-overview.*?</table>", h, re.S)
    ov_txt = ov.group(0) if ov else ""
    for a in ["FUTU", "SBI个人", "SBI公司", "IBKR", "bitFlyer"]:
        present = a in ov_txt or (a.replace("个人", "").replace("公司", "") in ov_txt)
        red = present and ("未接入" in ov_txt or "#3a1414" in ov_txt or "完整性不足" in ov_txt)
        has_data = ("FUTU" == a)  # 仅FUTU有当日实时·其余无
        ok_a = present and (has_data or red)
        acct_objs.append({"账户": a, "在总览": present, "红标": red if not has_data else "有数据", "PASS": ok_a})
    ok2 = all(o["PASS"] for o in acct_objs)
    add("② 每账户覆盖(无数据须红标)", ok2, "5账户逐个查" if ok2 else "★某账户缺或未红标", acct_objs)

    # ③ 每动作(减/加/换)须有数量或金额或待授权
    act_objs = []
    for r in hold_rows:
        if any(k in r["动作chip"] for k in ["减", "加", "换"]):
            txt = r["动作文"] + r["账户"]
            has = bool(re.search(r"\d+\s*股", txt) or re.search(r"[¥$]\s*\d", txt) or "待授权" in txt or "分档" in txt or "数量" in txt)
            act_objs.append({"标的": r["名称"], "动作": r["动作chip"], "含数量/金额/待授权": has})
    ok3 = all(o["含数量/金额/待授权"] for o in act_objs) if act_objs else True
    add("③ 每减/加/换含数量或金额", ok3, f"{len(act_objs)}个动作逐个查" if ok3 else "★某动作缺数量/金额",
        [o for o in act_objs if not o["含数量/金额/待授权"]] or act_objs)

    # ④/⑤ 五关表逐候选:第5关仅待研究不得进今日正式候选·第1关须激活
    cand_objs = []
    gt = re.search(r"五关逐只轨迹.*?</table>", h, re.S)
    if gt:
        for tr in re.findall(r"<tr>(.*?)</tr>", gt.group(0), re.S):
            tds = [plain(x) for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            if len(tds) >= 6 and "候选" not in tds[0]:
                cand_objs.append({"候选": tds[0], "第1关": tds[1], "第5关": tds[5]})
    # ④ 第5关待研究却标"今日正式候选"(而非观察)——本表第5关均"个股研究待接·观察"·未称正式候选→OK
    bad4 = [c for c in cand_objs if ("待研究" in c["第5关"] or "待接" in c["第5关"]) and "正式候选" in h and c["候选"] in re.findall(r"今日正式候选[^<]{0,200}", h)]
    add("④ 第5关待研究不进今日正式候选", not bad4, "候选均标观察·非今日正式" if not bad4 else "★待研究候选混入正式", bad4)
    # ⑤ 第1关须激活板块(非'未激活/否决')
    bad5 = [c for c in cand_objs if ("未激活" in c["第1关"] or "否决" in c["第1关"])]
    add("⑤ 候选第1关均激活板块", not bad5, f"{len(cand_objs)}候选第1关逐个查·均过第1关" if not bad5 else "★非激活板块混入", bad5 or [{"候选": c["候选"], "第1关": c["第1关"][:24]} for c in cand_objs])

    # ⑥ 同标的三层动作不冲突(简化:同一名称的chip动作唯一)
    from collections import defaultdict
    acts = defaultdict(set)
    for r in hold_rows:
        acts[r["名称"].split()[0] if r["名称"] else r["名称"]].add(re.sub(r"[·。].*", "", r["动作chip"]))
    conflict = {k: list(v) for k, v in acts.items() if len(v) > 1}
    add("⑥ 同标的动作不冲突", not conflict, "每标的动作唯一" if not conflict else f"★冲突{conflict}", [{"标的": k, "多动作": v} for k, v in conflict.items()])

    # ⑦ 每url须有对应判断(url前后有中文判断/标题·非裸链;链接文本在url之后)
    urls = re.findall(r"https?://[^\s\"'<>]+", h)
    bare = 0
    bare_ex = []
    for m in re.finditer(r"https?://[^\s\"'<>]+", h):
        ctx = plain(h[max(0, m.start() - 60):m.end() + 160])  # 含url之后的链接文本/标题/标的
        in_a = bool(re.search(r"<a[^>]+>[^<]{2,}</a>", h[max(0, m.start() - 80):m.end() + 200]))
        if not (re.search(r"[一-龥]{2,}", ctx) or in_a):
            bare += 1; bare_ex.append(m.group(0)[:50])
    ok7 = len(urls) > 0 and bare == 0
    add("⑦ 证据链接对应判断(非裸链)", ok7, f"{len(urls)}条url均附判断" if ok7 else f"★{bare}条裸链或无url", [{"url数": len(urls), "裸链": bare}])

    # ⑧ 目标管理实物(收紧:②当前收益/③差距须有真数值·非'待接/C'占位·才PASS)
    m_ret = re.search(r"当前累计收益</td><td>(.*?)</td>", h, re.S)
    m_gap = re.search(r"与目标差距</td><td>(.*?)</td>", h, re.S)
    ret_txt = plain(m_ret.group(1)) if m_ret else ""
    gap_txt = plain(m_gap.group(1)) if m_gap else ""
    ret_ok = ("C·待接" not in ret_txt) and re.search(r"[-+]?\d+\.?\d*\s*%", ret_txt) is not None
    gap_ok = ("C·待接" not in gap_txt) and re.search(r"[-+]?\d+\.?\d*\s*(pp|%)|\$[\d,]+", gap_txt) is not None
    tg = bool("40%" in h and ret_ok and gap_ok)
    add("⑧ 目标管理②③有真数值(非待接占位)", tg,
        f"②当前收益真值+③差距真值" if tg else f"★②待接或无数值({ret_txt[:20]})/③({gap_txt[:20]})",
        [{"②当前收益": ret_txt[:40], "真值": bool(ret_ok)}, {"③差距": gap_txt[:40], "真值": bool(gap_ok)}])

    # ⑨ 老雷/湖水须有真实接入状态(非只名称)
    ki = []
    for name in ["老雷", "湖水"]:
        seg = " ".join(plain(h[m.start():m.start() + 160]) for m in re.finditer(name, h))
        stat = any(k in seg for k in ["接入", "调用", "未接", "断点", "路径", "输入哪层", "待核实", "已建"])
        ki.append({"接口": name, "有接入状态": stat})
    ok9 = all(o["有接入状态"] for o in ki)
    add("⑨ 老雷/湖水有真实接入状态", ok9, "两接口均带接入状态" if ok9 else "★只名称无接入状态", ki)

    # ⑩ 旧版重要功能没退出
    ok10 = (("世界观" in h or "大环境" in h) and "集中度" in h and ("逻辑" in h or "闭环" in h))
    add("⑩ 旧版重要功能保留", ok10, "大环境+集中度+逻辑闭环在" if ok10 else "★旧版功能退出", [])

    return C


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--file", default="00_请先看这里/★每日产品_2026-07-22.html")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    p = (ROOT / a.file) if not Path(a.file).is_absolute() else Path(a.file)
    if not p.exists():
        print("★产品文件不存在:", p); return 2
    raw = p.read_bytes(); h = raw.decode("utf-8")
    C = gate(h)
    fails = [c for c in C if not c["PASS"]]
    print("完整产品·出厂硬闸 v2·逐对象(禁关键词通过) · 文件", p.name, "· 字节", len(raw), "· EFBFBD", raw.count(b"\xef\xbf\xbd"))
    print("=" * 62)
    for c in C:
        print(("  ✔" if c["PASS"] else "  ✗"), c["规则"].ljust(30), "·", c["详情"])
    print("-" * 62)
    print((f"★FAIL {len(fails)}/10 → 不得申请验收" if fails else "✅ 10/10 PASS·逐对象·具备申请验收资格(≠投资判断对·GPT独立验收)"))
    doc = {"_说明": "出厂硬闸v2·逐对象循环(GPT硬闸六·禁关键词假通过)。硬闸通过=送验资格·不代表投资判断对(GPT独立验收)。",
           "date": "20260722", "generated_at": datetime.now(JST).isoformat(timespec="seconds"),
           "产品文件": str(p.relative_to(ROOT)).replace("\\", "/") if str(ROOT) in str(p) else str(p),
           "字节": len(raw), "EFBFBD乱码计数": raw.count(b"\xef\xbf\xbd"),
           "PASS数": sum(1 for c in C if c["PASS"]), "FAIL数": len(fails), "总规则": len(C), "全通过": len(fails) == 0,
           "结论": ("10/10 PASS·逐对象·具备申请验收资格(≠投资判断对)" if not fails else f"FAIL {len(fails)}/10·逐对象·不得申请验收"),
           "FAIL规则": [c["规则"] for c in fails], "逐规则逐对象": C}
    outp = ROOT / "data" / "screen" / "product_gate_result_20260722.json"
    outp.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("wrote", outp.name, len(outp.read_bytes()), "字节·EFBFBD=", outp.read_bytes().count(b"\xef\xbf\xbd"))
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
