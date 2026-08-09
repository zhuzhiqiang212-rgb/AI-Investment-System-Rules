# -*- coding: utf-8 -*-
"""★轮109 NO2/NN1:把 B1 新模板20只并入七册的册2a/2b(持仓深研)·统一 run_id·加定性层08-02标注(NO4)+glossary锚。"""
import sys, re, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SEE = ROOT / "00_请先看这里"
BOOKS = [("1", "总览闭环"), ("2a", "持仓深研上"), ("2b", "持仓深研下"), ("3", "机会板块"), ("4", "组合记分"), ("5", "规则附件")]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); ap.add_argument("--run-id", required=True)
    a = ap.parse_args(); dh = a.date; rid = a.run_id
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    b1 = (SEE / f"★20只持仓深研_B1_{dh}.html").read_text(encoding="utf-8")
    head = b1[:re.search(r"<body[^>]*>", b1).end()]
    nm6 = re.search(r'<div class="nm6">.*?</div>\s*(?=<div class="nm3")', b1, re.S).group(0)
    nm3 = re.search(r'<div class="nm3">.*?</div>', b1, re.S).group(0)
    gloss = re.search(r'<details id="glossary".*?</details>', b1, re.S).group(0)
    idxs = [m.start() for m in re.finditer(r'<div class="card" id="deepB1-', b1)] + [b1.rfind("</body>")]
    cards = [b1[idxs[i]:idxs[i + 1]] for i in range(len(idxs) - 1)]

    def nav(cur):
        return " ｜ ".join((f"<b>[{n} {nm}]</b>" if n == cur else
                           f'<a href="★每日产品_{dh}_{n}_{nm}.html" style="color:#2c6e9a">[{n} {nm}]</a>') for n, nm in BOOKS)

    def strip(no, nm):
        return (f'<div style="background:#12324e;color:#dfeeff;border:2px solid #4f9fdf;border-radius:9px;padding:9px 14px;margin:6px 0 12px;font-size:13px">'
                f'<div style="font-size:17px;font-weight:900;color:#7ec0ff">★每日投资产品 · 第 {no}/6 册 · {nm}（B1新模板·20只重生成）</div>'
                f'<div>数据日 <b>{dh}</b>（交易日）｜ 价格 JP开盘实时/US隔夜（OpenD实测）｜ run_id <b>{rid}</b>（七册同源·L2）</div>'
                f'<div style="background:#3a2a1e;color:#ffe8cf;border:1px solid #d08030;border-radius:5px;padding:3px 8px;margin:4px 0">★定性层（八节/regime/逐只判断文字）＝<b>08-02 沿用</b>·Opus5 {dh}正文未出·B4概率重校在Opus5侧进行中；★量化层（20只到价/K线/账户闭合）＝{dh}真数据。不得当整册都是{dh}判断。</div>'
                f'<div style="margin-top:4px;font-size:12px">七册导航：{nav(no)}</div></div>')

    tail = "</body></html>"
    out = {"2a": head + strip("2a", "持仓深研上") + nm6 + gloss + "".join(cards[:10]) + tail,
           "2b": head + strip("2b", "持仓深研下") + nm3 + "".join(cards[10:]) + tail}
    for no, html in out.items():
        nm = dict(BOOKS)[no]
        fn = SEE / f"★每日产品_{dh}_{no}_{nm}.html"
        fn.write_text(html, encoding="utf-8")
        bt = html.encode("utf-8")
        opn = len(re.findall(r"<(?:div|section|details)\b(?![^>]*/>)", html)); cls = len(re.findall(r"</(?:div|section|details)>", html))
        print("%s: %dKB 乱码%d %s" % (fn.name[-22:], len(bt) / 1024, bt.count(b"\xef\xbf\xbd"), "良构" if opn == cls else f"★不平衡{opn}/{cls}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
