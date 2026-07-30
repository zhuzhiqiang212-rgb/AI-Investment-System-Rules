# -*- coding: utf-8 -*-
"""数据层文案禁夹带 HTML 标签闸（轮20 J4·裁定2026-07-27）。

根因：evidence_autobuild.py 文案里写着 <b>先不翻</b>，只有阻尼regime触发那天才暴露（07-27命中）→
      渲染层 esc() 把它转成字面量 &lt;b&gt; 印给董事长（L3 转义渣）。这类只在特定分支触发·会反复发作。
铁规矩（并进 CLAUDE.md §5.5）：★数据层不带样式——强调用「」，样式（<b>/<span>…）归渲染层。

本闸扫【数据层脚本】的字符串字面量：出现 HTML 标签（<b>/<br>/<span>/<i>/<strong>/<em>/<div>/<a>）→ 告警。
渲染器（deep_render/render_3layer/full_product_render/product_lint/deliver*/product_manifest）合法用 HTML·豁免。
同时扫 data/evidence_chain + data/reports 的 today_direction/note 类文本字段（运行期兜底）。
非关键·只告警不阻断（写 data/logs/data_html_leak_{date}.json）。行内 '# html-ok' 可豁免某行。
"""
import re, json, argparse, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 渲染器/出厂/交付：合法产 HTML → 豁免
RENDERER_EXEMPT = {"deep_render.py", "render_3layer.py", "full_product_render.py", "product_lint.py",
                   "product_manifest.py", "data_html_leak_gate.py"}
HTML_TAG = re.compile(r"<\s*/?\s*(?:b|br|span|i|strong|em|div|a|p|ul|li|table|tr|td)\b[^>]*>", re.I)
STRLIT = re.compile(r"""(['"])(?:\\.|(?!\1).)*\1""")   # 粗匹配字符串字面量


CJK = re.compile(r"[一-鿿]")
# 解析/正则类行(HTML是被读的对象·非生成)→豁免
PARSE_HINT = re.compile(r"re\.(search|finditer|findall|match|sub|compile)|\.(find|rfind|index|split|replace|count)\s*\(|re\.escape|r['\"]")


def scan_scripts() -> list:
    """只flag【生成的中文文案里夹带HTML样式标签】(如 f\"…→ <b>先不翻</b>，维持…\")。
    排除:渲染器/_diag诊断/deliver;排除解析类行(regex/.find·HTML是被读对象非生成);
    只命中『字符串含HTML标签 且 含中文』(纯regex模式无中文→跳)。行内 '# html-ok' 豁免。"""
    hits = []
    for p in sorted((ROOT / "scripts").glob("*.py")):
        # 渲染器/报告生成器/诊断脚本 合法产HTML → 豁免;只留【写data/*.json的数据层脚本】
        if (p.name in RENDERER_EXEMPT or "deliver" in p.name or "render" in p.name
                or "report" in p.name or "_run" in p.name or p.name == "auto_daily_run.py"
                or p.name.startswith("_diag") or p.name.startswith("_") or "stage" in p.name
                or p.name.startswith("gate") or "manifest" in p.name
                or "hardcheck" in p.name or "auto_produce" in p.name
                or "product_gate" in p.name or "dashboard" in p.name
                or "worklist" in p.name):   # 测试fixture/主控HTML/产品解析闸/仪表盘/填报工单→合法豁免
            continue
        try:
            lines = p.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for i, ln in enumerate(lines, 1):
            if "# html-ok" in ln or PARSE_HINT.search(ln):
                continue
            for m in STRLIT.finditer(ln):
                s = m.group(0)
                if HTML_TAG.search(s) and CJK.search(s):   # 中文文案+HTML标签=样式漏进数据层
                    hits.append({"file": f"scripts/{p.name}", "line": i,
                                 "tag": HTML_TAG.search(s).group(0)[:20],
                                 "ctx": ln.strip()[:100]})
                    break
    return hits


def scan_data(date: str) -> list:
    """运行期兜底:扫当日 evidence/reports 的文本字段有没有 HTML(数据不该带样式)。"""
    hits = []
    for sub, pat in (("evidence_chain", f"daily_{date}.json"), ("reports", f"production_{date}.json")):
        fp = ROOT / "data" / sub / pat
        if not fp.exists():
            continue
        try:
            txt = fp.read_text(encoding="utf-8")
        except Exception:
            continue
        # JSON 里 HTML 标签会被转义成 < 或保留 <;两种都查
        for m in re.finditer(r"(?:<|\\u003c)\s*/?\s*(?:b|br|span|i|strong|em)\b", txt, re.I):
            seg = txt[max(0, m.start() - 40):m.start() + 20]
            hits.append({"file": f"data/{sub}/{pat}", "sample": re.sub(r"\s+", " ", seg)[-60:]})
            if len(hits) >= 10:
                break
    return hits


def run(date: str) -> dict:
    sh = scan_scripts()
    dh = scan_data(date)
    return {"as_of": date, "gate": "数据层文案禁夹带HTML标签闸",
            "summary": {"脚本命中": len(sh), "数据命中": len(dh)},
            "script_hits": sh, "data_hits": dh,
            "rule": "数据层不带样式:强调用「」·样式(<b>/<span>…)归渲染层。行内加 '# html-ok' 豁免。",
            "note": "非关键·只告警不阻断。渲染器合法用HTML已豁免。"}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="数据层文案禁夹带HTML标签闸")
    ap.add_argument("--date", required=True)
    args = ap.parse_args()
    out = run(args.date)
    (ROOT / "data" / "logs").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "logs" / f"data_html_leak_{args.date}.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    s = out["summary"]
    print(f"数据层HTML闸 {args.date}: 脚本命中{s['脚本命中']} 数据命中{s['数据命中']}")
    for h in out["script_hits"][:15]:
        print(f"  ⚠ {h['file']}:{h['line']} [{h['tag']}] {h['ctx'][:70]}")
    for h in out["data_hits"][:5]:
        print(f"  ⚠ {h['file']}: …{h['sample']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
