# -*- coding: utf-8 -*-
"""★轮102 A4:把单册 ★每日产品_{date}.html 拆成【五册】(每册≤400KB·可通读)·恢复 CLAUDE.md 原五册规范。
根因(董事长点破):单册1800KB→Opus5读不完→只核元数据→正文错漏网。
★安全拆分:正文整体裹在持续容器里(balance从不归0)→用【开标签栈重建】——每册在切点重新打开该处仍开着的容器·末尾闭合·保证每册HTML良构。
五册共享同一 data_date/run_id(从单册横幅提取)→L2同源闸过。每册标【本册可用/本册缺项】(A4-4)。"""
import re, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEE = ROOT / "00_请先看这里"

# 册定义:(序号, 册名, 起marker, 止marker, 本册涵盖, 本册缺项)。marker=None 表示文首/文末。
BOOKS = [
    ("1", "总览闭环", None, 'id="glossary"',
     "页头/决策逻辑链7层/第一三共卖出执行方案(A1)/Opus5八节正文/世界观/资金流动/板块轮动/复盘/判断完整性(L19)/目标倒推/风险配仓四规矩/术语表",
     "全账户现金融资闭合未接·③④层部分指标未直采·各假设证伪信号见分晓窗口未到"),
    ("2a", "持仓深研上", 'id="glossary"', 'id="deep-US.COIN"',
     "术语表+持仓总览+目标/风险明细·个股深研卡(第一三共/英伟达/微软/MSTR)",
     "异常股价格复权口径待核·不出贵贱结论·第一三共见执行方案(第1册)"),
    ("2b", "持仓深研下", 'id="deep-US.COIN"', 'id="inst-top"',
     "个股深研卡(Coinbase/软银/东京海上/索尼/爱德万/丰田/伊藤忠/万代/任天堂/博通/Circle/闪迪/台积电/META/IBKR/SpaceX)",
     "爱德万超单只20%上限·SBI账户部分待董事长确认·SpaceX非上市按融资轮估"),
    ("3", "机会板块", 'id="inst-top"', 'id="sec-conc"',
     "机会池五关漏斗/候选池/替换引擎/板块深度尺龙头五维/大环境六层世界观",
     "简易估值仅B级·不进买卖依据·护城河/个股深度多项待接"),
    ("4", "组合记分", 'id="sec-conc"', 'id="sec-rulers"',
     "组合集中度/三条主风险+可观测信号/复盘记分卡三件魂/预测记分",
     "到期验证首条08-03·命中率样本不足·全账户闭合未接影响集中度分母"),
    ("5", "规则附件", 'id="sec-rulers"', None,
     "规则附件6把尺(世界观/国家战略/资金/板块/过滤五关/持仓档案)/承接节点加仓价/今日变化差分/逻辑闭环",
     "6把尺属规则底子(相对静态)·承接节点价位映射部分待接"),
]


def _stack_at(body, pos):
    """body[:pos] 结束时仍打开的容器(div/section/details)栈·元素=(tag, 完整开标签串)。"""
    stack = []
    for m in re.finditer(r'<(/?)(div|section|details)\b([^>]*?)(/?)>', body[:pos]):
        closing, tag, selfclose = m.group(1), m.group(2), m.group(4)
        if closing:
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0] == tag:
                    del stack[i]; break
        elif selfclose != "/":
            stack.append((tag, m.group(0)))
    return stack


def _emit(body, a, b):
    """截取 body[a:b]·前置 a 处开着的容器开标签·后置 b 处开着的容器闭标签→良构片段。"""
    sa = _stack_at(body, a)
    sb = _stack_at(body, b)
    prefix = "".join(t[1] for t in sa)
    suffix = "".join("</%s>" % t[0] for t in reversed(sb))
    return prefix + body[a:b] + suffix


def _find(body, marker, default):
    if marker is None:
        return default
    i = body.find(marker)
    if i < 0:
        return default
    # 回退到该 marker 所在标签的 '<' 起点(切在标签边界·不切标签中间)
    lt = body.rfind("<", 0, i)
    return lt if lt >= 0 else i


def split(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    src = SEE / f"★每日产品_{dh}.html"
    if not src.exists():
        print("[五册拆分] 源单册不存在:", src.name); return 2
    doc = src.read_text(encoding="utf-8")
    # 头(至 <body ...> 止) + 尾
    mb = re.search(r"<body\b[^>]*>", doc)
    head = doc[:mb.end()] if mb else doc[:doc.find(">") + 1]
    tail = "</body></html>"
    body_start = mb.end() if mb else 0
    be = doc.rfind("</body>")
    body = doc[body_start: be if be > 0 else len(doc)]
    # 提取 run_id / data_date(五册同源)
    rid = (re.search(r"run_id[^R]{0,6}(R-?3?-\d{8}-\d{6})", doc) or [None, "?"])[1]
    ddm = (re.search(r"data_date[=：: ]{0,3}(\d{4}-\d{2}-\d{2})", doc) or [None, dh])[1]
    total = len(BOOKS)
    # 清理旧分册(命名或册数变化时不留残册)
    keep = {f"★每日产品_{dh}_{no}_{nm}.html" for no, nm, *_ in BOOKS}
    import glob as _g
    for old in _g.glob(str(SEE / f"★每日产品_{dh}_*.html")):
        if Path(old).name not in keep:
            try:
                Path(old).unlink(); print("  清理旧册:", Path(old).name)
            except Exception:
                pass
    written = []
    # 预算 offset
    cuts = []
    for i, (no, nm, a_mk, b_mk, cov, gap) in enumerate(BOOKS):
        a = _find(body, a_mk, 0)
        b = _find(body, b_mk, len(body))
        cuts.append((a, b))
    for i, (no, nm, a_mk, b_mk, cov, gap) in enumerate(BOOKS):
        a, b = cuts[i]
        frag = _emit(body, a, b)
        # ★分册后:页内 #锚跳到别册→坏锚(L25)。分册供【通读正文】·册间靠导航条(.html链接)·此处把页内#跳链降级为纯文本(去坏锚)。
        frag = re.sub(r'<a\b[^>]*href="#[^"]*"[^>]*>(.*?)</a>', r"\1", frag, flags=re.S)
        # 册间导航
        nav = " ｜ ".join(
            (f"<b>[{bno} {bnm}]</b>" if bno == no else
             f'<a href="★每日产品_{dh}_{bno}_{bnm}.html" style="color:#7ee0a0">[{bno} {bnm}]</a>')
            for bno, bnm, *_ in BOOKS)
        strip = (
            f'<div style="background:#12324e;color:#dfeeff;border:2px solid #4f9fdf;border-radius:9px;padding:9px 14px;margin:6px 0 12px;font-size:13.5px">'
            f'<div style="font-size:17px;font-weight:900;color:#7ec0ff">★每日投资产品 · 第 {no}/{total} 册 · {nm}</div>'
            f'<div>数据日 <b>{ddm}</b> ｜ 价格对应交易日 <b>2026-07-31</b>（周末休市·取最近交易日收盘）｜ run_id <b>{rid}</b>（五册同源·L2闸校验）</div>'
            f'<div style="background:#3a1e1e;color:#ff9a9a;border:1px solid #c0392b;border-radius:5px;padding:3px 8px;margin:4px 0;font-weight:800">★机器完工度 总判据 2/5 · GPT V6 终验 FAIL · ★不得用于真实交易（A5）</div>'
            f'<div style="color:#bfe6d3"><b>本册可用：</b>{cov}</div>'
            f'<div style="color:#ffcf70"><b>本册缺项：</b>{gap}</div>'
            f'<div style="margin-top:5px;font-size:12px">五册导航：{nav}</div></div>')
        out = head + strip + frag + tail
        # 良构自检:容器开闭平衡
        opn = len(re.findall(r'<(?:div|section|details)\b(?![^>]*/>)', out))
        cls = len(re.findall(r'</(?:div|section|details)>', out))
        fn = SEE / f"★每日产品_{dh}_{no}_{nm}.html"
        fn.write_text(out, encoding="utf-8")
        kb = round(len(out.encode("utf-8")) / 1024)
        bad = out.encode("utf-8").count(b"\xef\xbf\xbd")
        bal = "良构✔" if opn == cls else f"★不平衡 开{opn}/闭{cls}"
        over = "★超400KB!" if kb > 400 else ""
        written.append((fn.name, kb, bal, bad, over))
        print(f"  第{no}册 {nm}: {kb}KB {bal} 乱码{bad} {over}")
    print(f"[五册拆分] 完成 · run_id={rid} · data_date={ddm}")
    return 0 if all(b[2] == "良构✔" and b[3] == 0 and not b[4] for b in written) else 6


if __name__ == "__main__":
    import argparse
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    raise SystemExit(split(a.date))
