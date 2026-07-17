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
