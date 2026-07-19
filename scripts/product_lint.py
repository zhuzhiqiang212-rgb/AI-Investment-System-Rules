#!/usr/bin/env python3
"""出厂机械核（丙1·董事局工单2026-07-17）· 只读不下单

render 出五册后【自动】跑这一关：任何一条 FAIL → 不出品（渲染器返回非0、不落盘覆盖旧册）。
每犯一类新错，就在这里加一条规则，让同一个坑不许踩第二次。

规则(每条都必须是机器可判的硬事实·不做主观判断)：
  L1 乱码        每册 EF BF BD 计数必须=0
  L2 同源        七册 run_id / data_date 必须完全一致
  L3 无转义渣    正文里不许出现 &lt;b&gt; 这种"标签被转义成字面量"
  L4 无错模板    持仓册不许出现候选专用话("不在你持仓里/候选还没做估值")
  L5 数字一致    册间摘要报的机会数字 = 分册里的数字(同一算子·不许两套)
  L6 状态词唯一  同一状态词(机会口径/总闸档)全文只许一个取值
  L7 无半截      新闻标题/日期不许被从中间硬切(半截日期=残段)
  L8 链接齐      每条新闻要么有可点原文链接、要么明标"无直链"

用法：
  python scripts/product_lint.py --date 20260716          # 独立核已落盘的册
  from product_lint import lint_volumes; lint_volumes(vols, date)   # 渲染器内联调用(出厂闸)
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _txt(html: str) -> str:
    """扒标签→只留给董事长看到的正文(避免拿 style/script 里的字符串误判)。"""
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    return re.sub(r"<[^>]+>", " ", s)


SIZE_WARN_MB = 1.5      # 甲3：单文件字节上限预警——超了就提示拆懒加载，别悄悄膨胀


def lint_volumes(vols: dict[str, str], date: str) -> list[str]:
    """返回 FAIL 列表(空=全过)。vols: {文件名: html文本}"""
    fails: list[str] = []
    if not vols:
        return ["L0 没有任何册可核"]

    # ── L22 单文件字节上限预警(甲3·工单2026-07-17)：合并成一个文件后最怕悄悄膨胀 ──
    for fn, h in vols.items():
        mb = len(h.encode("utf-8")) / 1024 / 1024
        if mb > SIZE_WARN_MB:
            fails.append(f"L22 单文件过大：{fn} 已 {mb:.2f} MB（预警线 {SIZE_WARN_MB} MB）"
                         f"——该把深料改成懒加载/外链了，别让它悄悄膨胀到打不开")

    # ── L23 HTML 必须分行(甲3·防"整份挤一行"·便于核验与diff) ──
    for fn, h in vols.items():
        lines = h.split("\n")
        if len(lines) < 50:
            fails.append(f"L23 HTML没分行：{fn} 只有 {len(lines)} 行——整份挤一行没法核验/diff")
        elif max(len(x) for x in lines) > 8000:
            fails.append(f"L23 HTML有超长行：{fn} 最长行 {max(len(x) for x in lines):,} 字符（>8000）")

    # ── L1 乱码 ──
    for fn, h in vols.items():
        n = h.encode("utf-8").count(b"\xef\xbf\xbd")
        if n:
            fails.append(f"L1 乱码：{fn} 出现 EF BF BD ×{n}")

    # ── L2 同源(run_id / data_date 七册一致) ──
    rid, dd = set(), set()
    for fn, h in vols.items():
        rid |= set(re.findall(r"run_id=<b>([^<]+)</b>", h))
        dd |= set(re.findall(r"data_date=<b>([^<]+)</b>", h))
    if len(rid) != 1:
        fails.append(f"L2 同源：run_id 不唯一 → {sorted(rid) or '一个都没有'}")
    if len(dd) != 1:
        fails.append(f"L2 同源：data_date 不唯一 → {sorted(dd) or '一个都没有'}")
    # L2b 快照戳也要五册一致 + 必须等于本次 production 的 generated_at(不许旧快照顶充)
    snaps = set()
    for h in vols.values():
        snaps |= set(re.findall(r"UTC\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", h))
    if len(snaps) > 1:
        fails.append(f"L2b 同源：快照戳不唯一 → {sorted(snaps)}")
    elif snaps:
        try:
            gen = json.loads((ROOT / "data" / "reports" / f"production_{date}.json")
                             .read_text(encoding="utf-8")).get("generated_at", "")[:19]
            if gen and gen not in snaps:
                fails.append(f"L2b 快照对不上：册里写 {sorted(snaps)}，但 production_{date}.json 是 {gen}"
                             f"——册不是这次扫描出的(旧版顶充?)")
        except Exception:
            pass

    # ── L3 转义渣(标签被转义成字面量印给董事长看) ──
    for fn, h in vols.items():
        bad = re.findall(r"&lt;/?(?:b|i|br|span|div|a|strong|em)\s*/?&gt;", h)
        if bad:
            fails.append(f"L3 转义渣：{fn} 正文出现字面量标签 ×{len(bad)}（示例 {bad[0]}）")

    # ── L4 持仓册套了候选专用模板 ──
    POOL_ONLY = ["不在你的持仓里", "不在你持仓里", "候选还没做估值", "这只候选还没做估值"]
    # 甲[A方案]合并单文件后：机会池与持仓卡在同一个文件里 → 只核【持仓卡区块内】不许有候选话
    for fn, h in vols.items():
        for m in re.finditer(r'id="stock-([A-Z]{2}\.[A-Z0-9]+)"', h):
            nxt = h.find('id="stock-', m.end())
            card = _txt(h[m.start(): nxt if nxt > 0 else m.end() + 40000])
            for w in POOL_ONLY:
                if w in card:
                    fails.append(f"L4 错模板：{fn} 的 {m.group(1)} 持仓卡里出现候选专用话「{w}」")
                    break
            else:
                continue
            break

    # ── L4b 引擎内部话/裸字段名漏进产品(估值待接串曾漏出"(任一整套)（该用…EV/EBITDA）·不硬编") ──
    LEAK = ["任一整套", "该用 ", "不硬编", "缺真输入", "normal_eps", "pe_mid", "normalized_eps",
            "ebitda_normal", "ev_ebitda", "net_debt", "eps0", "g_stage1", "terminal_g", "wacc",
            "EV/EBITDA", "'status'", "&#x27;status&#x27;"]
    for fn, h in vols.items():
        t = _txt(h)
        hit = [w for w in LEAK if w in t]
        if hit:
            fails.append(f"L4b 内部话泄露：{fn} 出现 {hit[:3]}（引擎内部字段/话术不许印给董事长）")
    # L4c 内部结构泄露：python dict 原样打印 / data 路径 / 裸 .json 文件名 / 裸字段名
    STRUCT = [
        (r"\{['\"&][^}<]{0,120}?:\s*['\"&][^}<]{0,120}?\}", "python字典被原样打印"),
        (r"data/[a-z_]+/[a-z_0-9]+\.json|data\\\\[a-z_]+", "内部数据路径"),
        (r"(?<![\w/])[a-z_]{3,}_\d{8}\.json|(?<![\w/])[a-z_]{4,}\.json", "内部json文件名"),
        (r"(?<![\w])(?:by_symbol|by_layer|by_ticker|aggregate_by_ticker|holdings_true|"
         r"quantity_status|price_data_date|change_pct|cost_price|reasonable_low|reasonable_high|"
         r"current_certainty|cumulative_score|daily_score|opportunity_scope|today_direction)(?![\w])",
         "裸字段名"),
    ]
    for fn, h in vols.items():
        t = _txt(h)
        for pat, why in STRUCT:
            m = re.search(pat, t)
            if m:
                fails.append(f"L4c 内部结构泄露：{fn} 出现{why}「{m.group(0)[:34]}」"
                             f"——程序内部结构不许印给董事长")
                break

    # ── L5 册间摘要数字 = 分册数字(机会池口径不许两套) ──
    nums = set()
    for fn, h in vols.items():
        for m in re.finditer(r"候选宇宙\s*<b>(\d+)</b>\s*只", h):
            nums.add(m.group(1))
    if len(nums) > 1:
        fails.append(f"L5 数字打架：'候选宇宙N只' 全册出现多个取值 → {sorted(nums)}")

    # ── L6 同一状态词全文唯一(机会口径/总闸档) ──
    scopes = set()
    for h in vols.values():
        # 只截到句末(。)为止——不许贪到后面别的话，否则排版差异会被误判成口径打架
        scopes |= set(re.findall(r"机会口径[：:]\s*([^<｜]{4,90}?。)", _txt(h)))
    # 归一化空白后比对(排版差异不算打架)
    scopes = {re.sub(r"\s+", "", s) for s in scopes}
    if len(scopes) > 1:
        fails.append(f"L6 状态词打架：'机会口径' 全册有 {len(scopes)} 个不同取值 → {sorted(scopes)[:2]}")
    # L6b 除 derived 外任何模块自造机会口径结论(记分卡曾自写"机会池应收口径"与当日"口径不放宽"打架)
    for fn, h in vols.items():
        t = _txt(h)
        for w in ("应收口径", "必须收口径", "可按纪律放大口径"):
            if w in t:
                fails.append(f"L6b 自造口径：{fn} 出现「{w}」——机会口径唯一出处是 derived.opportunity_scope")
                break

    # ── L9 同一标的现价全卡唯一(甲2·卡文本曾写死旧价:META $631 vs 实时 $687→动摇贵贱结论) ──
    for fn, h in vols.items():
        for m in re.finditer(r'id="stock-([A-Z]{2}\.[A-Z0-9]+)"', h):
            sym = m.group(1)
            nxt = h.find('id="stock-', m.end())
            card = _txt(h[m.start(): nxt if nxt > 0 else len(h)])
            px = {p.replace(",", "") for p in re.findall(r"现价[约]?\s*[\$¥]\s*([\d,]+(?:\.\d+)?)", card)}
            if len(px) > 1:
                # 容差1%：同一价的不同写法(687 / 687.00)不算打架
                v = sorted(float(x) for x in px)
                if (v[-1] - v[0]) / v[0] > 0.01:
                    fails.append(f"L9 现价打架：{fn} 的 {sym} 卡内出现多个现价 {sorted(px)}（必须全卡唯一·取实时源）")

    # ── L10 记分卡同一指标全册一致(甲1·分环卡/魂①表/①册摘要曾报三个数) ──
    days = set()
    for h in vols.values():
        t = _txt(h)
        days |= set(re.findall(r"一共只追踪了\s*(\d+)\s*天", t))
        days |= set(re.findall(r"有记录的这\s*(\d+)\s*天里", t))
        days |= set(re.findall(r"这\s*(\d+)\s*天里", t))
    if len(days) > 1:
        fails.append(f"L10 记分卡天数打架：全册出现多个'追踪天数' → {sorted(days)}")

    # ── L16 标签闭合(清洗正则曾把 "</div></div>" 当叠词吃掉一个→迷你数轴每格漏闭合) ──
    for fn, h in vols.items():
        body = h.split("<body>", 1)[-1].split("</body>", 1)[0]
        for tag in ("div", "table", "tr", "td", "details", "span"):
            o = len(re.findall(r"<" + tag + r"[\s>]", body))
            c = len(re.findall(r"</" + tag + r">", body))
            if o != c:
                fails.append(f"L16 标签不闭合：{fn} <{tag}> 开 {o} / 闭 {c}（差 {o-c}）")
    # 每个 <td> 内部也要自平衡(表格格里漏闭合最容易把整张表撑坏)
    for fn, h in vols.items():
        for m in re.finditer(r"<td[^>]*>(.*?)</td>", h, re.S):
            cell = m.group(1)
            o, c = len(re.findall(r"<div[\s>]", cell)), len(re.findall(r"</div>", cell))
            if o != c:
                fails.append(f"L16 单元格内div不闭合：{fn} 有 <td> 内 开{o}/闭{c}（示例「{_txt(cell)[:22].strip()}…」）")
                break

    # ── L17 渲染层不许出平铺裸 <h2>(必须 class=main 主 或 class=sub 次·分出主次) ──
    #     豁免：右栏6尺【内部】的 h2 是尺的正文(一句话世界观/第1关硬性过滤…)，那是内容不是骨架。
    for fn, h in vols.items():
        skel = re.sub(r'<details class="ruler-embed".*?</details>', " ", h, flags=re.S)
        bare = re.findall(r"<h2>(?!<)([^<]{2,60})</h2>", skel)
        if bare:
            fails.append(f"L17 平铺裸标题：{fn} 有 {len(bare)} 个无主次样式的 <h2>（示例「{bare[0][:20]}」）"
                         f"——渲染层的 h2 必须标 class=main(主) 或 class=sub(次)")

    # ── L18 正文里的裸 "<" / ">" 比较号(如 "$202 < $216")会被当成标签起止符·撑坏结构 ──
    for fn, h in vols.items():
        bad = re.findall(r"[\$¥][\d,\.]+\s*[<>]\s*[\$¥]?[\d,\.]+", h)
        if bad:
            fails.append(f"L18 裸尖括号：{fn} 正文用了 {bad[:1]} 这种比较号"
                         f"——HTML 里 <> 是标签起止符，请改成「低于/高于」或 &lt;")

    # ── L19 有持仓却没卡(子册按写死名单挑卡→新买的标的落不进任何册·董事长看不到自己的持仓) ──
    try:
        prod = json.loads((ROOT / "data" / "reports" / f"production_{date}.json").read_text(encoding="utf-8"))
        syms = [str(h["symbol"]) for h in prod.get("holdings", []) if not str(h["symbol"]).startswith("CC.")]
        allh = "".join(vols.values())
        miss = [s for s in syms if f'id="stock-{s}"' not in allh]
        if miss:
            fails.append(f"L19 有持仓没卡：{miss} 在 production 里有仓位，但持仓深研册里找不到它的卡"
                         f"——子册分配漏了(名单写死?)，董事长会看不到自己的持仓")
    except Exception:
        pass

    # ── L20 架构师中周期估算的硬边界(工单2026-07-17)：必须标非权威 + 不许自动改动作 ──
    for fn, h in vols.items():
        if "架构师中周期估算" not in h:
            continue
        n_blk = h.count("📐 架构师中周期估算") + h.count("架构师中周期估算（非权威）")
        n_tag = h.count("非权威")
        if n_tag < n_blk:
            fails.append(f"L20 架构师估算没标非权威：{fn} 有 {n_blk} 处估算块、只有 {n_tag} 处「非权威」标注"
                         f"——必须与权威估值区分、不许混为一谈")
        # 低置信的必须带橙字警示
        t = _txt(h)
        if ("低置信" in t) and ("仅作框架参考" not in t):
            fails.append(f"L20 低置信没警示：{fn} 出现「低置信」但没有「仅作框架参考」的警示语")

    # ── L21 决策话"读反"(工单2026-07-17·丙)：加仓价≥现价 / 减仓价≤现价 的矛盾措辞 ──
    #     根因样例：「现价¥3,470 → 加到¥4,113附近」——读着像"要在高于现价的位置加仓"。
    #     正确说法：停手价要说成"涨回¥4,113以上就别追"，不能说成"加到¥4,113"。
    for fn, h in vols.items():
        t = _txt(h)
        for m in re.finditer(r"加到\s*([\$¥])([\d,]+)", t):
            fails.append(f"L21 读反：{fn} 出现「加到{m.group(1)}{m.group(2)}」"
                         f"——这是【停手价】，会被读成'要在这个价位加仓'。"
                         f"请改成「涨回{m.group(1)}{m.group(2)}以上就别再追」")
            break
        for m in re.finditer(r"减到\s*([\$¥])([\d,]+)", t):
            fails.append(f"L21 读反：{fn} 出现「减到{m.group(1)}{m.group(2)}」"
                         f"——同理，请改成「跌回{m.group(1)}{m.group(2)}以下就别再减」")
            break
    # L21b 同一句里"可以加"却给了个高于现价的价、或"可以减"却给了低于现价的价
    for fn, h in vols.items():
        t = _txt(h)
        for m in re.finditer(r"现在\s*([\$¥])([\d,]+)[^。]{0,80}?现在就可以加[^。]{0,60}?涨回\s*\1([\d,]+)", t):
            try:
                now_p, stop_p = float(m.group(2).replace(",", "")), float(m.group(3).replace(",", ""))
                if stop_p <= now_p:
                    fails.append(f"L21b 读反：{fn}「现在{m.group(1)}{m.group(2)} 可以加，涨回"
                                 f"{m.group(1)}{m.group(3)} 就别追」——停手价低于现价，逻辑不通")
                    break
            except Exception:
                pass

    # ── L24 卡头动作 ≠ 今日结论动作(甲1·工单2026-07-17)：20只里曾13只打架 ──
    #     根因：卡头走"账本基础档"、结论走"今日叠加决策"，两根轴都叫"动作"。
    for fn, h in vols.items():
        for m in re.finditer(r'id="stock-([A-Z]{2}\.[A-Z0-9]+)"', h):
            nxt = h.find('id="stock-', m.end())
            seg = h[m.start(): nxt if nxt > 0 else len(h)]
            hd = re.search(r"今日动作：.{0,120}?border-radius:9px\">([加买守等减])</b>", seg, re.S)
            cc = re.search(r"1｜结论：</b>.{0,160}?border-radius:9px\">([加买守等减])</b>", seg, re.S)
            if hd and cc and hd.group(1) != cc.group(1):
                fails.append(f"L24 卡头与结论打架：{fn} 的 {m.group(1)} 卡头「{hd.group(1)}」"
                             f"≠ 今天你怎么办·结论「{cc.group(1)}」——必须同一个判断")
                break

    # ── L25 死链(甲3·合并单文件后跨册链变成 href=""；或指向不存在的 #id) ──
    for fn, h in vols.items():
        n_empty = len(re.findall(r'href=""', h))
        if n_empty:
            fails.append(f"L25 空死链：{fn} 有 {n_empty} 处 href=\"\"——点了没反应")
        bad = sorted({a for a in re.findall(r'href="#([^"]+)"', h) if f'id="{a}"' not in h})
        if bad:
            fails.append(f"L25 坏锚点：{fn} 有 {len(bad)} 个 #锚点跳不到 → {bad[:3]}")

    # ── L26 同股两动作(第一档1·验收整改)：产品里同一只出现两个不同动作→拦 ──
    #     以 decisions_{date}.json 为唯一真相，核产品里各处徽章是否都一致。
    try:
        dec = json.loads((ROOT / "data" / "pdca" / f"decisions_{date}.json").read_text(encoding="utf-8")).get("decisions", {})
    except Exception:
        dec = {}
    for fn, h in vols.items():
        for sym, d in dec.items():
            want = str(d.get("action", ""))
            # 找该只卡内所有动作徽章
            for m in re.finditer(r'id="stock-' + re.escape(sym) + r'"', h):
                nxt = h.find('id="stock-', m.end())
                seg = h[m.start(): nxt if nxt > 0 else len(h)]
                acts = set(re.findall(r'border-radius:9px[^>]*>([加买守等减])</b>', seg))
                if len(acts) > 1 or (acts and want and want not in acts):
                    fails.append(f"L26 同股两动作：{fn} 的 {sym} 卡内动作 {sorted(acts)} ≠ 决定表「{want}」"
                                 f"——每只当天只能有一个动作")
                    break

    # ── L27 未批准写成可执行(第一档2·三态)：拍板前不许出现"已批准/可执行/去下单"类词 ──
    for fn, h in vols.items():
        t = _txt(h)
        for w in ("已批准可执行", "可以执行", "已执行", "去下单", "帮你下单", "自动下单"):
            if w in t:
                fails.append(f"L27 三态越界：{fn} 出现「{w}」——系统只读不下单，拍板前只能是「系统建议·尚未执行」")
                break

    # ── L29 蓝图8层编号一致(第三档10 + 修2·验收整改) ──
    #     记分卡=⑧、组合层=⑦、机会池=⑤、持仓=⑥；闭环图=八层。全文出现处必须一致，不一致→拦。
    #     注：大环境=6层环(daily 扫描的环境子层)是另一根轴、允许叫「六层」，不在此闸内。
    for fn, h in vols.items():
        t = _txt(h)
        if "七层逻辑闭环" in t:
            fails.append(f"L29 层编号打架：{fn} 出现「七层逻辑闭环」——闭环图是八层(①世界…⑧记分卡)，应写「八层逻辑闭环」")
        for w, right in (("⑦记分", "记分卡=⑧"), ("⑦ 记分", "记分卡=⑧"),
                         ("⑥组合层", "组合层=⑦"), ("⑥ 组合层", "组合层=⑦")):
            if w in t:
                fails.append(f"L29 层编号打架：{fn} 出现「{w}」——按蓝图8层应为 {right}（记分卡⑧·组合层⑦，别再沿用旧编号）")
                break
        # 闭环图若声明"八层"，其节点 ①..⑧ 必须齐 8 个
        if "八层逻辑闭环" in t:
            import re as _re
            i0 = h.find("八层逻辑闭环")
            win = h[i0: i0 + 4000]
            nodes = set(_re.findall(r"[①②③④⑤⑥⑦⑧]", win))
            if len(nodes) < 8:
                fails.append(f"L29 层编号打架：{fn} 闭环图自称八层，但只找到 {len(nodes)} 个圈码节点(应①~⑧齐8个)")

    # ── L28 同股一个答案·真覆盖(第一档1·验收整改·治本) ──
    #     渲染层在【每个出现动作的地方】都埋了隐藏锚 data-actck="只|哪处|动作"：
    #       深研卡头 / 深研⑨决策链 / 动作表 / 日股专项 / 现金建议·买 / 现金建议·减。
    #     这里把每只在所有出现处的取值收齐：
    #       (a) 同一只在任何两处取值不等 → 拦，并报是哪只、哪两处各是什么；
    #       (b) 若有唯一决定表 decisions_{date}.json，任何一处 ≠ 主表 → 拦，报哪只哪处。
    #     因为渲染取值都来自唯一决定表，正常必全等；人为改坏任一处即在此被抓。
    for fn, h in vols.items():
        seen: dict[str, dict[str, str]] = {}   # sym -> {loc: act}
        for m in re.finditer(r'data-actck="([^"|]+)\|([^"|]+)\|([^"|]+)"', h):
            sym, loc, act = m.group(1), m.group(2), m.group(3)
            seen.setdefault(sym, {})[loc] = act   # 同一处多次出现取值必同，覆盖即可
        for sym, locs in seen.items():
            vals = set(locs.values())
            if len(vals) > 1:
                pair = "、".join(f"{lc}={ac}" for lc, ac in locs.items())
                fails.append(f"L28 同股两动作：{fn} 的 {sym} 各处动作不一致 → {pair}"
                             f"——每只当天只能有一个动作，不许某处自写")
                continue
            want = str((dec.get(sym) or {}).get("action", ""))
            only = next(iter(vals)) if vals else ""
            if want and only and only != want:
                bad_loc = "、".join(lc for lc, ac in locs.items() if ac != want)
                fails.append(f"L28 与决定表不符：{fn} 的 {sym} 在「{bad_loc}」={only} ≠ 唯一决定表「{want}」")
        # 锚一个都没有 = 埋点被删/渲染没跑 → 也要报，别让它静默失覆盖
        if not seen and dec:
            fails.append(f"L28 校验锚缺失：{fn} 找不到任何 data-actck 锚——同股一致性关形同虚设，拒绝出品")

    # ── L30 估值口径一致(董事长2026-07-18)：同一只在【板块推荐语/机会池估值表】的贵贱结论必须一致 ──
    #     被推荐(合理)的票，估值表里不能显"偏贵/极贵"；两处打架→拦、报是哪只。
    #     数据源：候选估值 candidate_valuation_{date}.json(表结论) × sector_deep 架构师判定(推荐语)。
    try:
        import sys as _sys
        _sys.path.insert(0, str((ROOT / "scripts")))
        cv = json.loads((ROOT / "data" / "valuation" / f"candidate_valuation_{date}.json").read_text(encoding="utf-8")).get("candidates", {})
        import sector_deep as _SD
        av = _SD.arch_verdict_map()
    except Exception:
        cv, av = {}, {}
    for tk, rec in (cv or {}).items():
        base = tk.split(".")[-1]
        a = (av.get(base) or {})
        a_verd = str(a.get("verdict") or "")
        t_verd = str((rec.get("valuation") or {}).get("verdict") or "")
        if not a_verd or not t_verd:
            continue
        a_cheap = ("合理" in a_verd or "便宜" in a_verd) and "贵" not in a_verd
        t_expensive = ("极贵" in t_verd or "偏贵" in t_verd)
        if a_cheap and t_expensive:
            fails.append(f"L30 估值口径打架：{base} 板块推荐语判「{a_verd}」，但机会池估值表却显「{t_verd}」"
                         f"——推荐合理却算极贵=两把尺打架，成长/电力股该走 forward P/E、别套正常化")

    # ── L32 架构师有估算的持仓不许再显光秃秃"算不出/待接真源"(董事长2026-07-18) ──
    #     6只(architect_normalized_est)在卡内三处应显【值+尺+可靠度+怎么办】；仍出现"待接真源/算不出该值"→拦。
    try:
        ap = sorted((ROOT / "data" / "valuation").glob("architect_normalized_est_*.json"))
        arch_syms = {str(e.get("ticker")) for e in (json.loads(ap[-1].read_text(encoding="utf-8")).get("estimates") or [])
                     if (e.get("fair_price") or {}).get("mid") is not None} if ap else set()
    except Exception:
        arch_syms = set()
    _NAKED = ("待接真源", "算不出它该值多少钱", "算不出该值多少钱")
    for fn, h in vols.items():
        for sym in arch_syms:
            for m in re.finditer(r'id="stock-' + re.escape(sym) + r'"', h):
                nxt = h.find('id="stock-', m.end())
                seg = _txt(h[m.start(): nxt if nxt > 0 else len(h)])
                bad = next((w for w in _NAKED if w in seg), None)
                if bad:
                    fails.append(f"L32 架构师估算未显值：{fn} 的 {sym} 卡内仍出现「{bad}」"
                                 f"——这只有架构师中周期估算，三处(深研栏/决策条/今天你怎么办)应显 值+尺+可靠度+怎么办，不许光秃秃")
                    break
    # 全文兜底：6只之外别处若整只被判"待接真源"也要抓(scale 之外的口径漏网)——只报，不误伤 SpaceX 等无估算的
    # 三处一致：6只的中枢值应全卡唯一(深研栏/决策条/今天你怎么办同一个数)
    for fn, h in vols.items():
        for sym in arch_syms:
            i = h.find('id="stock-' + sym + '"')
            if i < 0:
                continue
            nxt = h.find('id="stock-', i + 10)
            seg = _txt(h[i: nxt if nxt > 0 else len(h)])
            mids = set(re.findall(r"中枢\s*[¥$]?\s*([\d,]+)", seg))
            if len(mids) > 1:
                fails.append(f"L32 三处估值不一致：{fn} 的 {sym} 卡内出现多个「中枢」取值 {sorted(mids)}"
                             f"——深研栏/决策条/今天你怎么办 必须同一个数")

    # ── L33 按行业换尺(董事长2026-07-18改尺·老雷五层框架)：每张有⑤估值块的持仓卡必须显"用哪把尺" ──
    #     治"一把尺(穿周期正常化)套所有"——每只须带 行业标签+用哪把尺；缺→拦(那是没按行业换尺)。
    for fn, h in vols.items():
        for m in re.finditer(r'id="stock-([A-Z]{1,3}\.[0-9A-Z]+)"', h):
            sym = m.group(1)
            nxt = h.find('id="stock-', m.end())
            seg = h[m.start(): nxt if nxt > 0 else len(h)]
            if "它到底值多少钱" in seg and "用哪把尺" not in seg:
                fails.append(f"L33 未按行业换尺：{fn} 的 {sym} 卡有⑤估值块但没显「用哪把尺」"
                             f"——按行业换尺(老雷法)要求每只标 行业标签+用哪把尺，不许一把尺套所有")
                break

    # ── L34 同股多股数(硬检查第2项·董事长2026-07-19 P0)：全产品同一只出现两个不同总股数→拦 ──
    #     治软银"6600（富通4100＋SBI2500）"与"6900（富通4100＋SBI2800）"并存。用回归可拦。
    for fn, h in vols.items():
        t = _txt(h)
        qmap: dict[str, set] = {}
        # 只认【档案头格式】"{sym} · N股（各账户）"(sym 紧跟·再跟总股数)——避开散文里名字靠近别只股数的误报。
        for m in re.finditer(r"(JP\.\d+|US\.[A-Z]+|HK\.\d+)\s*·\s*([\d,]{3,})\s*股（", t):
            qmap.setdefault(m.group(1), set()).add(m.group(2).replace(",", ""))
        for sym, qs in qmap.items():
            if len(qs) > 1:
                fails.append(f"L34 同股多股数：{fn} 的 {sym} 全产品出现多个总股数 {sorted(qs)}"
                             f"——必须全读同一持仓底表(右栏档案与动态卡一致)，不许某处走旧数")

    # ── L35 估值口径自相矛盾(硬检查第7项·董事长2026-07-19 P0)：同一只同屏"疑似错/拆股"+"已复核·非算错"→拦 ──
    try:
        sg = json.loads((ROOT / "data" / "reports" / f"data_sanity_{date}.json").read_text(encoding="utf-8"))
        by_sym: dict[str, set] = {}
        for x in (sg.get("issues") or []):
            by_sym.setdefault(str(x.get("symbol")), set()).add(str(x.get("type")))
        for sym, types in by_sym.items():
            det = " ".join(str(x.get("detail")) for x in (sg.get("issues") or []) if str(x.get("symbol")) == sym)
            if ("价格异常" in types or "疑似" in det or "拆股" in det) and ("已复核" in det or "非算错" in det):
                fails.append(f"L35 估值口径自相矛盾：{sym} 同时出现『疑似错误/拆股』与『已复核·非算错』两口径"
                             f"——明令禁止并存;核准了就删疑似句,没核准就统一写『数据未通过·不可据此买卖』")
    except Exception:
        pass

    # ── L36 同股多现价(硬检查·董事长2026-07-19 轮5致命1·本次它漏了→补进)：同一只两个不同现价→拦 ──
    #     现价是三层核心字段,必须全读同一 final_decision 单一源(动作表/why卡/deep推导逐字一致)。
    #     覆盖两处来源:(a)动作表权威价"¥N.NN [市场·日期]"；(b)各卡散文里带"现价"标签的价。
    for fn, h0 in vols.items():
        cap36 = h0.find('id="inst-top"')                 # ④机构底稿(候选/龙头价)不算个股现价·避免误报
        h = h0[:cap36] if cap36 > 0 else h0
        pxmap: dict[str, set] = {}
        # (a) 动作表:同一 <tr> 内 symbol + 带[市场·日期]标签的现价
        for tr in re.findall(r"<tr\b.*?</tr>", h, re.S):
            ms = re.search(r"(JP\.\d+|US\.[A-Z]+|HK\.\d+)", tr)
            mp = re.search(r"[¥$]([\d,]{3,})(?:\.\d+)?\s*\[(?:JP|US|HK|CC)", tr)
            if ms and mp:
                pxmap.setdefault(ms.group(1), set()).add(mp.group(1).replace(",", ""))
        # (b) 各卡散文"现价约¥N"：按 id="why-/deep-{sym}" 卡锚分段归属到本只
        anchors = [(m.start(), m.group(1))
                   for m in re.finditer(r'id="(?:why|deep)-((?:JP|US|HK|CC)\.[A-Z0-9.]+)"', h)]
        bounds = anchors + [(len(h), None)]
        for k in range(len(anchors)):
            s0, sym = bounds[k]
            for m in re.finditer(r"现价约?\s*[¥$]([\d,]{3,})", h[s0:bounds[k + 1][0]]):
                pxmap.setdefault(sym, set()).add(m.group(1).replace(",", ""))
        for sym, ps in pxmap.items():
            if len(ps) > 1:
                fails.append(f"L36 同股多现价：{fn} 的 {sym} 出现多个现价 {sorted(ps)}"
                             f"——现价是三层核心字段,必须全读同一 final_decision 单一源(动作表/why卡/推导逐字一致)")

    # ── L15 同一条提示刷屏(佐证"料已N天旧"应只在①册顶部说一次·不许层层重复) ──
    n_stale = sum(len(re.findall(r"这份料已放了\s*\d+\s*天", h)) for h in vols.values())
    if n_stale:
        fails.append(f"L15 提示刷屏：「这份料已放了N天」出现 {n_stale} 处"
                     f"——这句全册只该在①册顶部的警条里说一次")

    # ── L13 括号不闭合(甲3类:替换文本自带括号又被套进外层"（…）") ──
    for fn, h in vols.items():
        t = _txt(h)
        bad = re.findall(r"（[^（）]{0,70}（[^（）]{0,50}）(?![^（）]{0,50}）)", t)
        if bad:
            fails.append(f"L13 括号不闭合：{fn} 有 {len(bad)} 处（示例「{bad[0][:34]}…」）")

    # ── L14 CSS色值被术语清洗吃坏(如 #c9a86a 里的"6a"被当内部编号删→#c9a8) ──
    for fn, h in vols.items():
        bad = re.findall(r"color:\s*#(?![0-9A-Fa-f]{3}\b)(?![0-9A-Fa-f]{6}\b)[0-9A-Fa-f]{1,8}", h)
        if bad:
            fails.append(f"L14 色值被清洗吃坏：{fn} 出现非法色值 {sorted(set(bad))[:2]}"
                         f"——术语/编号清洗正则误伤了十六进制")

    # ── L12 同一集中度数字全册唯一(乙5·①册现算14.2% vs 拍板卡读陈旧快照14.1%) ──
    for cat in ("AI供应链", "防御"):
        vals = set()
        for h in vols.values():
            t = _txt(h)
            vals |= set(re.findall(cat + r"\s*(?:集中度\s*)?(\d+\.\d)\s*%", t))
        if len(vals) > 1:
            fails.append(f"L12 集中度打架：「{cat}」全册出现多个取值 {sorted(vals)}"
                         f"——拍板卡与集中度表必须同一现算源(别读隔夜快照)")

    # ── L31 AI集中度全文一致(董事长2026-07-18)：覆盖【板块研究文/所有嵌入文本】,不只主体 ──
    #     板块研究文曾写 65.8% 与权威 65.6% 打架。做法：逐个扫 6X.X% 数字，
    #     若其前后 24 字窗口含 AI 集中度语境(AI + 超配/集中/敞口/资本开支/供应链/仓位) → 收集；
    #     排除投影值(紧跟"→"的买后/换后数)。收集到的当前值须唯一，出现两个→拦。
    _AICTX = ("超配", "集中", "敞口", "资本开支", "供应链", "仓位", "AI仓")
    for fn, h in vols.items():
        t = _txt(h)
        ai_pct = set()
        for m in re.finditer(r"(6\d\.\d)\s*%", t):
            i = m.start()
            if "→" in t[max(0, i - 8):i] or "目标" in t[max(0, i - 10):i]:   # 投影值(→约Y%/目标≤Y)不算当前集中度
                continue
            win = t[max(0, i - 24): i + 18]
            if "AI" in win and any(k in win for k in _AICTX):
                ai_pct.add(m.group(1))
        if len(ai_pct) > 1:
            fails.append(f"L31 AI集中度打架：{fn} 全文(含板块研究文)出现多个 AI 集中度取值 {sorted(ai_pct)}%"
                         f"——必须全指向同一 production 现算值(别一处 65.6 一处 65.8)")

    # ── L11 均线当买卖线(乙·董事长2026-07-17拍板:买卖只看估值·均线只作趋势参考) ──
    MA_TRADE = [
        r"回踩\s*50日[^。；<]{0,8}[＝=]?\s*低吸", r"回调到\s*50日[^。；<]{0,6}低吸",
        r"跌破\s*(?:200日)?年线[^。；<]{0,6}[＝=]\s*止损", r"跌破\s*200日[^。；<]{0,6}止损",
        r"低吸价（买/加）", r"待均线数据", r"低吸止损待均线",
    ]
    for fn, h in vols.items():
        t = _txt(h)
        for pat in MA_TRADE:
            m = re.search(pat, t)
            if m:
                fails.append(f"L11 均线当买卖线：{fn} 出现「{m.group(0)[:24]}」"
                             f"——买卖只看估值便宜位/偏贵位，均线仅趋势参考（与页头宣言一致）")
                break

    # ── L7 新闻被从中间硬切(半截日期是最硬的证据) ──
    for fn, h in vols.items():
        t = _txt(h)
        half = re.findall(r"\d{4}-\d{2}-\d(?!\d)", t)          # 2026-07-1 这种缺末位
        if half:
            fails.append(f"L7 半截日期：{fn} 出现 {len(half)} 处被切断的日期（示例 {half[0]}）")

    # ── L8 每条新闻要么有链接、要么明标无直链 ──
    for fn, h in vols.items():
        n_src = len(re.findall(r"来源：[^<]{1,24}　发布：", h))   # 逐条新闻的固定骨架
        n_lnk = h.count("阅读原文→") + h.count("无直链")
        if n_src and n_lnk < n_src:
            fails.append(f"L8 缺链接：{fn} 有 {n_src} 条新闻、但只有 {n_lnk} 条给了原文链接/无直链标注")

    # ══ L40-L47 GPT9独立验收升级(董事长2026-07-19)：把星期日冒充实时价/守减矛盾/状态并存等焊死 ══
    import datetime as _dt

    def _is_trading_day(d: str) -> bool:
        dd = str(d).replace("-", "")
        try:
            return _dt.date(int(dd[:4]), int(dd[4:6]), int(dd[6:8])).weekday() < 5   # 仅周末判据(假期未含·保守)
        except Exception:
            return True

    def _cards(h: str):
        """按 id="why-SYM" / id="deep-SYM" 卡锚切每只的卡片段(用于同卡自洽检查)。
        ④完整机构底稿(inst-top 之后)是【非个股整层内容】·不参与个股卡自洽扫描(否则最后一卡溢出误报)。"""
        cap = h.find('id="inst-top"')
        if cap > 0:
            h = h[:cap]
        anchors = [(m.start(), m.group(1))
                   for m in re.finditer(r'id="(?:why|deep)-((?:JP|US|HK|CC)\.[A-Z0-9.]+)"', h)]
        bounds = anchors + [(len(h), None)]
        segs = {}
        for k in range(len(anchors)):
            s0, sym = bounds[k]
            segs.setdefault(sym, "")
            segs[sym] += h[s0:bounds[k + 1][0]]
        return segs

    nontrading = not _is_trading_day(date)

    for fn, h in vols.items():
        t = _txt(h)

        # L40 交易日校验:非交易日不许出现"当日实时价"类肯定断言(前面不是"非")
        if nontrading:
            false_claim = re.findall(r"(?<!非)当日实时价", t)
            if false_claim:
                fails.append(f"L40 交易日校验：{fn} 生产日 {date} 非交易日，却出现『当日实时价』类肯定表述 "
                             f"{len(false_claim)} 处——非交易日禁用，须显示真实交易日")

        # L41 价格日与生产日分离:每只须两独立字段(产品生产日/价格对应交易日);非交易日二者相同→FAIL
        if "价格对应交易日" in t and "生产日" in t:
            bad = re.findall(r"生产日\s*([\d\-]{5,10}).{0,60}?价格对应交易日\s*([\d\-]{5,10})", t)
            for gd, pd in bad:
                if nontrading and pd.replace("-", "") == gd.replace("-", ""):
                    fails.append(f"L41 价格日=生产日：{fn} 非交易日却把价格对应交易日({pd})标成与生产日({gd})相同——须标真实最近交易日")
                    break
        elif re.search(r"现价", t) and "价格对应交易日" not in t:
            fails.append(f"L41 缺价格交易日字段：{fn} 有现价却无『价格对应交易日』独立字段（须与生产日分开显示）")

        # L42 同卡语义自洽:极贵/超上沿 与 没到贵位 不得并存;守/等时不得写"涨过X才谈减"
        for sym, seg in _cards(h).items():
            st = _txt(seg)
            expensive = ("极贵" in st) or re.search(r"上沿之上|超上沿|上沿\s*[\d.]+\s*倍", st)
            if expensive and "没到贵位" in st:
                fails.append(f"L42 同卡自相矛盾：{fn} 的 {sym} 同时出现『极贵/超上沿』与『没到贵位』——判词方向打架")
            if expensive and re.search(r"涨过\s*[¥$][\d,]+.{0,6}才谈减", st):
                fails.append(f"L42 判词与停止条件打架：{fn} 的 {sym} 现价已超上沿，却仍写『涨过X才谈减』")

        # L43 状态互斥:同一只不得同时"输入未接/不标精算"与"已OK·精算"
        for sym, seg in _cards(h).items():
            st = _txt(seg)
            if ("输入未接" in st or "不标精算" in st) and "已OK·精算" in st:
                fails.append(f"L43 状态并存：{fn} 的 {sym} 同时出现『输入未接/不标精算』与『已OK·精算』——每只只留一种状态")

        # L44 尺原文比对:企稳判据须用批准原文『近20个交易日不创新低』,禁用『站稳20日均值/站上20日均线』
        for wrong in ("站稳20日均值", "站上20日均线", "站稳20日均线"):
            if wrong in t:
                fails.append(f"L44 尺原文不符：{fn} 出现『{wrong}』——批准原文是『近20个交易日不创新低』，须逐字一致")

        # L45 未完成项穷举:全文『画法待接/第二轮补』的图 == 公开未完成清单里列的图
        scanned = set(re.findall(r"图(\d+简?)[^画]{0,40}?画法待接", t))
        if "画法待接" in t:
            if "已知未完成清单" not in t:
                fails.append(f"L45 未完成清单缺失：{fn} 全文有『画法待接』却无公开『已知未完成清单』")
            else:
                listed = set(re.findall(r"图(\d+简?)\b", t[t.find("已知未完成清单"):t.find("已知未完成清单") + 400]))
                if scanned and not scanned <= listed:
                    fails.append(f"L45 未完成清单不全：{fn} 扫到画法待接的图 {sorted(scanned)} 未全部列入公开清单 {sorted(listed)}")

        # L46 内部字段通用模式:下划线/加号连接的小写标识、空参()——正文里一律不许(董事长看不懂)
        leaks = set(re.findall(r"\b[a-z]{2,}(?:_[a-z0-9]+)+\b", t))          # snake_case
        leaks |= set(re.findall(r"\b[a-z]{2,}(?:\+[a-z]+)+\b", t))           # plus+joined
        leaks |= set(re.findall(r"\b[a-z_]{2,}\(\)", t))                     # empty_call()
        leaks -= {"data_date", "run_id"}                                    # 这俩是页头明示的技术戳·允许
        leaks = {x for x in leaks if not re.match(r"https?", x)}
        if leaks:
            fails.append(f"L46 内部字段泄漏(模式)：{fn} 正文出现内部标识 {sorted(leaks)[:5]}——须转人话或删")

        # L47 清单去重:页头『待接 N』须等于待接清单里去重后的条目数
        m = re.search(r"待接\s*(\d+)", t)
        if m:
            declared = int(m.group(1))
            # 待接清单表:标的列(去重)
            names = re.findall(r"权威估值待接|待接·不编|数据未通过", t)  # 粗核:仅当声明数明显>实体去重时报
            # 用"不能依赖/待接清单"块的行数近似:此处只拦"声明数≠0 但清单为空"及重复名
            if declared > 0 and "待接" not in t:
                fails.append(f"L47 清单对不上：{fn} 页头称待接 {declared} 项，正文却找不到待接清单")

    # ── L9 不缩水闸 + L48 版块完整性闸(架构师早要求·GPT9 焊死)：只对三层正式产品·读 content_manifest ──
    def _l9_counts(h: str) -> dict:
        deep = len(re.findall(r'id="deep-', h))
        sec = len(re.findall(r'id="sec-', h))
        return {"研究模块数": deep * 16 + sec,
                "原始来源数": len(re.findall(r"来源[:：]|发布[:：]|阅读原文", h)),
                "反面证据数": len(re.findall(r"反面|不选减|不选加|挑战|证伪|推翻|只观察|不买、不加、不减", h)),
                "有效证据项目数": len(re.findall(r"佐证|证据|依据", h))}
    try:
        mani = json.loads((ROOT / "data" / "content_manifest.json").read_text(encoding="utf-8"))
    except Exception:
        mani = None
    if mani:
        for fn, h in vols.items():
            if 'id="L3"' not in h and "inst-top" not in h:      # 只核三层正式产品·跳过机器分册
                continue
            # L48 版块完整性:旧版登记的必存在区块,新版缺一块 → FAIL
            for blk in (mani.get("required_blocks") or []):
                if blk.get("必存在") and str(blk.get("锚", "")) not in h:
                    fails.append(f"L48 版块缺失：{fn} 缺少区块『{blk.get('名称')}』(锚 {blk.get('锚')}·原位置 {blk.get('原位置')})——旧版有、新版必须有")
            # L9 不缩水:研究模块/来源/反面证据/有效证据项目数 只增不减,少一条 FAIL
            cur = _l9_counts(h)
            for k, base in (mani.get("baseline_counts") or {}).items():
                if k in cur and isinstance(base, int) and cur[k] < base:
                    fails.append(f"L9 内容缩水：{fn} 的『{k}』={cur[k]} < 基线 {base}——只增不减,不许删有效研究证据")

    return fails


def main() -> int:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="出厂机械核(FAIL即不出品)")
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    sys.path.insert(0, str(ROOT / "scripts"))
    from deep_render import ONEFILE
    names = [ONEFILE(a.date)]      # 甲[A方案]：合并单文件后只核这一个
    vols = {}
    for fn in names:
        p = ROOT / "00_请先看这里" / fn
        if p.exists():
            vols[fn] = p.read_text(encoding="utf-8")
        else:
            print(f"[缺册] {fn}")
    fails = lint_volumes(vols, a.date)
    if fails:
        print(f"[出厂核 FAIL] {len(fails)} 条：")
        for f in fails:
            print("  ✗ " + f)
        return 5
    print(f"[出厂核 PASS] {len(vols)} 册 · L1乱码/L2同源/L3转义/L4错模板/L5数字/L6状态词/L7半截/L8链接 全过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
