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
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _txt(html: str) -> str:
    """扒标签→只留给董事长看到的正文(避免拿 style/script 里的字符串误判)。"""
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    return re.sub(r"<[^>]+>", " ", s)


def lint_volumes(vols: dict[str, str], date: str) -> list[str]:
    """返回 FAIL 列表(空=全过)。vols: {文件名: html文本}"""
    fails: list[str] = []
    if not vols:
        return ["L0 没有任何册可核"]

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

    # ── L3 转义渣(标签被转义成字面量印给董事长看) ──
    for fn, h in vols.items():
        bad = re.findall(r"&lt;/?(?:b|i|br|span|div|a|strong|em)\s*/?&gt;", h)
        if bad:
            fails.append(f"L3 转义渣：{fn} 正文出现字面量标签 ×{len(bad)}（示例 {bad[0]}）")

    # ── L4 持仓册套了候选专用模板 ──
    POOL_ONLY = ["不在你的持仓里", "不在你持仓里", "候选还没做估值", "这只候选还没做估值"]
    for fn, h in vols.items():
        if "机会池" in fn:
            continue          # 机会池册本来就该说这些
        t = _txt(h)
        for w in POOL_ONLY:
            if w in t:
                fails.append(f"L4 错模板：{fn}(持仓/其它册) 出现候选专用话「{w}」")
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
        if "持仓深研" not in fn:
            continue
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
    from deep_render import VOL, VOL2, VOL2_SUBS
    names = [VOL(a.date, n) for n in (1, 3, 4, 5)] + [VOL2(a.date, s) for s, _n, _y in VOL2_SUBS]
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
