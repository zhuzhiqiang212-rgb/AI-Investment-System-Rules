#!/usr/bin/env python3
"""发布前硬检查·回归测试出证(董事长2026-07-19 P0-3)

对当日正式产品【注入本次两处致命错】，证明出厂闸真能拦：
  致命1(硬检查第2项·同股多股数): 注入软银第二个总股数 6600（富通4100＋SBI2500）→ L34 必须 FAIL。
  致命2(硬检查第7项·估值口径矛盾): 注入爱德万"疑似拆股"价格异常，与已复核并存 → L35 必须 FAIL。
并演示: FAIL → 不覆盖正式产品(deep_render 出厂lint硬闸机制) → 保留上一版 → 生成红色失败报告。

用法: python scripts/hardcheck_regression.py --date 20260719
产物: 00_请先看这里/硬检查回归测试证据_{date}.html(红色失败报告样例+逐项pass/fail)
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import product_lint as PL  # noqa: E402


def run(date: str) -> dict:
    prod = ROOT / "00_请先看这里" / f"★每日产品_{date[:4]}-{date[4:6]}-{date[6:]}.html"
    h = prod.read_text(encoding="utf-8")
    cases = []

    # 正式产品=三层:与 render_3layer 出厂闸同一套 curated lint(跳过机器册专属结构规则·保留全部内容安全规则)
    _SKIP = ("L2 ", "L2b", "L19", "L28", "L29")
    curated = lambda fails: [x for x in fails if not x.startswith(_SKIP)]

    # ── 基线:正式产品应【全过】(curated·与出厂闸同口径) ──
    base = curated(PL.lint_volumes({prod.name: h}, date))
    cases.append({"name": "基线(正式产品原样·出厂闸同口径)", "expect": "PASS", "fails": base,
                  "ok": len(base) == 0})

    # ── 致命1:注入软银两个相互矛盾的总股数(6600 与 6900)→ L34 同股多股数必抓 ──
    inj1 = h.replace("</body>",
                     "<div>软银 JP.9984 · 6600股（富通4100＋SBI2500）</div>"
                     "<div>软银 JP.9984 · 6900股（富通4100＋SBI2800）</div></body>", 1)
    f1 = [x for x in PL.lint_volumes({prod.name: inj1}, date) if x.startswith("L34")]
    cases.append({"name": "致命1·同股多股数(注入软银6600)", "expect": "FAIL·L34", "fails": f1,
                  "ok": len(f1) >= 1})

    # ── 致命2:注入爱德万"疑似拆股"价格异常(与已复核并存) → L35 ──
    sp = ROOT / "data" / "reports" / f"data_sanity_{date}.json"
    sd = json.loads(sp.read_text(encoding="utf-8"))
    sd_bak = json.dumps(sd, ensure_ascii=False)
    sd["issues"].append({"level": "红", "type": "价格异常", "symbol": "JP.6857",
                         "name": "爱德万", "detail": "疑似拆股未换算·口径不符"})
    sp.write_text(json.dumps(sd, ensure_ascii=False), encoding="utf-8")
    f2 = [x for x in PL.lint_volumes({prod.name: h}, date) if x.startswith("L35")]
    sp.write_text(sd_bak, encoding="utf-8")   # 还原
    cases.append({"name": "致命2·估值口径矛盾(注入爱德万疑似拆股)", "expect": "FAIL·L35", "fails": f2,
                  "ok": len(f2) >= 1})

    # ── 致命3:注入同股第二个现价(第一三共deep卡 ¥2,758 与动作表 ¥2,791 并存)→ L36 ──
    inj3 = h.replace('id="deep-JP.4568"', 'id="deep-JP.4568"><span>现价约¥2,758</span', 1)
    f3 = [x for x in curated(PL.lint_volumes({prod.name: inj3}, date)) if x.startswith("L36")]
    cases.append({"name": "致命3·同股多现价(注入第一三共第二个现价)", "expect": "FAIL·L36", "fails": f3,
                  "ok": len(f3) >= 1})

    # ── 真实测:FAIL→正式产品不被覆盖·保留上一版(哈希前后比对·董事长2026-07-19补做) ──
    #   做法:①记正式产品(★每日产品_·三层)当前哈希/mtime ②注入爱德万价格异常(制造 L35 FAIL)
    #   ③真跑 render_3layer(出厂lint硬闸) ④比对哈希——FAIL 应 rc≠0 且哈希/mtime 不变(没被覆盖)。
    import hashlib
    import subprocess
    def _sha(p):
        return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "(文件不存在)"
    sanity_path = sp
    cmd = [sys.executable, str(ROOT / "scripts" / "render_3layer.py"), "--date", date]
    h_before = _sha(prod)
    mt_before = prod.stat().st_mtime if prod.exists() else 0
    sz_before = prod.stat().st_size if prod.exists() else 0
    sd2 = json.loads(sp.read_text(encoding="utf-8"))
    sd2_bak = json.dumps(sd2, ensure_ascii=False)
    sd2["issues"].append({"level": "红", "type": "价格异常", "symbol": "JP.6857",
                          "name": "爱德万", "detail": "疑似拆股未换算·口径不符"})
    sp.write_text(json.dumps(sd2, ensure_ascii=False), encoding="utf-8")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=300)
        rc = r.returncode
        full_out = ((r.stdout or "") + (r.stderr or "")).strip()
    finally:
        sp.write_text(sd2_bak, encoding="utf-8")     # 还原
    h_after = _sha(prod)
    mt_after = prod.stat().st_mtime if prod.exists() else 0
    not_overwritten = (h_before == h_after) and (mt_before == mt_after)
    cases.append({"name": "FAIL→正式产品不被覆盖·保留上一版(真实测·哈希前后比对)",
                  "expect": "FAIL(rc≠0)且哈希不变",
                  "fails": [f"注入L35后 rc={rc}（≠0=正确拦下）",
                            f"SHA256 前 {h_before[:16]}… → 后 {h_after[:16]}…（相同=没被覆盖）",
                            f"mtime {'未变' if mt_before==mt_after else '变了!'}",
                            f"渲染器输出首行：{full_out.splitlines()[:1]}"],
                  "ok": (rc != 0) and not_overwritten})

    # ── 可重跑证据包原始值(董事长2026-07-19致命4:结论表不算数·须任何人可重算) ──
    raw = {
        "生成时刻": _now_stamp(),
        "命令": " ".join(f'"{x}"' if " " in x else x for x in cmd),
        "注入": "在 data/reports/data_sanity_{d}.json 追加一条爱德万『价格异常·疑似拆股』→制造 L35 FAIL（跑后自动还原）".format(d=date),
        "算法": "SHA256（Python hashlib.sha256(file_bytes).hexdigest()）",
        "正式产品": {"路径": str(prod.relative_to(ROOT)),
                     "SHA256_前": h_before, "SHA256_后": h_after,
                     "mtime_前": mt_before, "mtime_后": mt_after,
                     "字节_前": sz_before, "字节_后": (prod.stat().st_size if prod.exists() else 0)},
        "渲染器返回码": rc, "是否未被覆盖": not_overwritten,
        "渲染器完整输出": full_out,
        "参与脚本指纹": {str(p.relative_to(ROOT)): _sha(p) for p in [
            ROOT / "scripts" / "render_3layer.py", ROOT / "scripts" / "product_lint.py",
            ROOT / "scripts" / "hardcheck_regression.py"]},
        "输入文件指纹": {str(sanity_path.relative_to(ROOT)): _sha(sanity_path)},
        "运行环境": {"python": sys.version.split()[0], "platform": sys.platform},
    }
    return {"date": date, "product": prod.name, "cases": cases,
            "all_ok": all(c["ok"] for c in cases), "raw": raw}


def _now_stamp() -> str:
    # 证据包生成时刻(供人工核对时间线一致)。避免 import 时点漂移·运行时取。
    import datetime
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


def write_bundle(res: dict) -> Path:
    """可重跑证据包:目录含 manifest.json(全原始值+算法) + 重跑步骤.txt(逐字命令) + 运行输出.txt。
    任何人按『重跑步骤.txt』执行,再用 hashlib 重算,即可复现 manifest 里的 SHA256——不是自述结论表。"""
    date = res["date"]
    raw = res.get("raw", {})
    bdir = ROOT / "00_请先看这里" / f"硬检查可重跑证据包_{date}"
    bdir.mkdir(parents=True, exist_ok=True)
    (bdir / "manifest.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (bdir / "运行输出.txt").write_text(str(raw.get("渲染器完整输出", "")) + "\n", encoding="utf-8")
    steps = (
        "硬检查『FAIL不覆盖正式产品』— 可重跑步骤（任何人可独立复现，不依赖本报告的自述）\n"
        f"生成时刻：{raw.get('生成时刻','')}\n"
        f"运行环境：Python {raw.get('运行环境',{}).get('python','')} / {raw.get('运行环境',{}).get('platform','')}\n"
        "算法：SHA256 = Python hashlib.sha256(open(路径,'rb').read()).hexdigest()\n\n"
        "① 先记正式产品当前指纹（应与 manifest『SHA256_后』一致——因跑完已还原、未被覆盖）：\n"
        f"   python -c \"import hashlib;print(hashlib.sha256(open(r'{raw.get('正式产品',{}).get('路径','')}','rb').read()).hexdigest())\"\n\n"
        "② 复现『FAIL 不覆盖』：手动跑一次硬检查回归（内部会注入 L35 FAIL、真跑渲染器、再自动还原）：\n"
        f"   {raw.get('命令','')}\n"
        "   期望：渲染器打印『[三层·出厂核 FAIL·不出品] …旧版未被覆盖』且返回码≠0。\n\n"
        "③ 跑完再记一次指纹，应与①【完全相同】=正式产品没被那次 FAIL 覆盖：\n"
        f"   （同①命令）\n\n"
        "④ 逐项原始值（前/后 SHA256、mtime、字节、参与脚本指纹、输入文件指纹）见 manifest.json；\n"
        "   渲染器那次的完整 stdout/stderr 见 运行输出.txt。\n"
    )
    (bdir / "重跑步骤.txt").write_text(steps, encoding="utf-8")
    return bdir


def write_report(res: dict) -> Path:
    rows = ""
    for c in res["cases"]:
        color = "#7ee0a0" if c["ok"] else "#ff5c5c"
        mark = "✅ 通过" if c["ok"] else "❌ 未达预期"
        detail = "；".join(c["fails"])[:300] if c["fails"] else ("（无告警=正确）" if c["expect"] == "PASS" else "（未触发·异常）")
        rows += (f'<tr><td>{c["name"]}</td><td>{c["expect"]}</td>'
                 f'<td style="color:{color};font-weight:700">{mark}</td>'
                 f'<td style="font-size:12px;color:#c8d4de">{detail}</td></tr>')
    banner = ("<div style='background:#0f2e1c;border:2px solid #4fbf87;color:#8cf5be;padding:10px;border-radius:6px;font-weight:800'>"
              "✅ 硬检查回归全部达预期：注入两处致命错均被出厂闸拦下、机制在位</div>"
              if res["all_ok"] else
              "<div style='background:#3a1414;border:2px solid #ff5c5c;color:#ffd0d0;padding:10px;border-radius:6px;font-weight:800'>"
              "❌ 硬检查回归未全达预期——闸门有漏，须先修</div>")
    # 红色失败报告样例(演示 FAIL 时董事长会看到什么)
    sample = ("<div style='background:#3a1414;border:2px solid #ff5c5c;border-radius:8px;padding:12px;margin-top:14px'>"
              "<div style='font-size:18px;font-weight:900;color:#ff5c5c'>🔴 发布前硬检查·失败——不出品</div>"
              "<div style='color:#ffd0d0;margin-top:6px;font-size:13px'>本次产品触发硬检查失败项，<b>正式产品未被覆盖·保留上一版</b>：</div>"
              "<ul style='color:#ffd0d0;font-size:13px'>"
              "<li>L34 同股多股数：软银出现 6600 与 6900 两个总股数</li>"
              "<li>L35 估值口径矛盾：爱德万同时『疑似拆股』与『已复核·非算错』</li></ul>"
              "<div style='color:#ffb454;font-size:12px'>修好后重跑生产即可。报『没做到』不扣分。</div></div>")
    # ── 可重跑证据包(董事长2026-07-19致命4:结论表≠验证·须任何人可重算) ──
    raw = res.get("raw", {})
    pp = raw.get("正式产品", {})
    def _esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    scripts_fp = "".join(f"<li><code>{_esc(k)}</code> — SHA256 <code>{v[:32]}…</code></li>"
                         for k, v in (raw.get("参与脚本指纹", {}) or {}).items())
    inputs_fp = "".join(f"<li><code>{_esc(k)}</code> — SHA256 <code>{v[:32]}…</code></li>"
                        for k, v in (raw.get("输入文件指纹", {}) or {}).items())
    pkg = (
        "<h2 style='margin-top:20px'>🔁 可重跑证据包（不是自述结论·任何人可独立重算）</h2>"
        "<div style='background:#10202e;border:1px solid #33566e;border-radius:8px;padding:12px;font-size:13px;color:#cfe0ee'>"
        f"<div>证据包目录：<code>00_请先看这里/硬检查可重跑证据包_{res['date']}/</code>"
        "（含 <code>manifest.json</code> 全原始值 + <code>重跑步骤.txt</code> 逐字命令 + <code>运行输出.txt</code> 完整stdout）</div>"
        f"<div style='margin-top:6px'>生成时刻：<b>{_esc(raw.get('生成时刻',''))}</b>｜环境：Python "
        f"{_esc(raw.get('运行环境',{}).get('python',''))} / {_esc(raw.get('运行环境',{}).get('platform',''))}</div>"
        f"<div style='margin-top:6px'>算法：<code>{_esc(raw.get('算法',''))}</code></div>"
        "<div style='margin-top:6px'>重跑命令（复制即可跑·内部注入L35 FAIL后自动还原）：<br>"
        f"<code>{_esc(raw.get('命令',''))}</code></div>"
        "<table style='width:100%;border-collapse:collapse;margin-top:8px;font-size:12.5px'>"
        "<tr><th style='text-align:left'>正式产品</th><th style='text-align:left'>FAIL 注入前</th><th style='text-align:left'>FAIL 注入后</th></tr>"
        f"<tr><td>SHA256</td><td><code>{pp.get('SHA256_前','')[:24]}…</code></td><td><code>{pp.get('SHA256_后','')[:24]}…</code></td></tr>"
        f"<tr><td>mtime</td><td>{pp.get('mtime_前','')}</td><td>{pp.get('mtime_后','')}</td></tr>"
        f"<tr><td>字节</td><td>{pp.get('字节_前','')}</td><td>{pp.get('字节_后','')}</td></tr></table>"
        f"<div style='margin-top:6px;color:#8cf5be'>渲染器返回码 <b>{raw.get('渲染器返回码','')}</b>（≠0=正确拦下）；"
        f"前后 SHA256/mtime/字节 <b>{'完全相同=正式产品没被覆盖' if raw.get('是否未被覆盖') else '发生变化!'}</b>。</div>"
        f"<div style='margin-top:8px'>参与脚本指纹（版本可核）：<ul>{scripts_fp}</ul></div>"
        f"<div>注入的输入文件指纹（还原后）：<ul>{inputs_fp}</ul></div>"
        "<div style='margin-top:6px'>渲染器那次的完整输出：<pre style='white-space:pre-wrap;background:#0a141d;padding:8px;border-radius:5px;font-size:11.5px;color:#bcd'>"
        f"{_esc(raw.get('渲染器完整输出',''))[:1200]}</pre></div>"
        "</div>")
    html = (f"<h1>发布前硬检查 · 回归测试证据（{res['date']}）</h1>"
            f"<div style='color:#8ea3b6;font-size:13px'>对象：{res['product']}｜逐项注入本次致命错，验出厂闸真能拦</div>"
            + banner
            + "<table class='dt' style='width:100%;border-collapse:collapse;margin-top:12px'>"
              "<tr><th>测试项</th><th>预期</th><th>结果</th><th>命中规则/说明</th></tr>" + rows + "</table>"
            + pkg
            + "<h2 style='margin-top:18px'>红色失败报告样例（FAIL 时董事长看到的）</h2>" + sample)
    p = ROOT / "00_请先看这里" / f"硬检查回归测试证据_{res['date']}.html"
    p.write_text(html, encoding="utf-8")
    return p


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    a = ap.parse_args()
    res = run(a.date)
    p = write_report(res)
    bdir = write_bundle(res)
    for c in res["cases"]:
        print(f"  [{'OK' if c['ok'] else '✗'}] {c['name']} → 预期{c['expect']}·"
              + (f"命中{len(c['fails'])}条" if c["fails"] else "无告警"))
    print(f"\n{'✅ 全部达预期' if res['all_ok'] else '❌ 有未达预期'} · 证据→ {p.name}")
    print(f"可重跑证据包→ {bdir.relative_to(ROOT)}/（manifest.json + 重跑步骤.txt + 运行输出.txt）")
    return 0 if res["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
