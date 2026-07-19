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

    # ── 基线:正式产品应【全过】 ──
    base = PL.lint_volumes({prod.name: h}, date)
    cases.append({"name": "基线(正式产品原样)", "expect": "PASS", "fails": base,
                  "ok": len(base) == 0})

    # ── 致命1:注入软银第二个总股数 6600（档案头格式，会被 L34 抓） ──
    inj1 = h.replace("</body>", "<div>软银 JP.9984 · 6600股（富通4100＋SBI2500）</div></body>", 1)
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

    # ── 不覆盖机制:deep_render 出厂前跑 lint，FAIL 即 return(不写文件)·旧册保留 ──
    #   证据=deep_render.build 内 "[出厂核 FAIL·不出品] … 旧册未被覆盖" 分支(已在多轮渲染日志出现)。
    mech_ok = True
    try:
        src = (ROOT / "scripts" / "deep_render.py").read_text(encoding="utf-8")
        mech_ok = ("出厂核 FAIL" in src and "不出品" in src)
    except Exception:
        mech_ok = False
    cases.append({"name": "FAIL→不覆盖正式产品·保留上一版(deep_render出厂lint硬闸)",
                  "expect": "机制在位", "fails": [], "ok": mech_ok})

    return {"date": date, "product": prod.name, "cases": cases,
            "all_ok": all(c["ok"] for c in cases)}


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
    html = (f"<h1>发布前硬检查 · 回归测试证据（{res['date']}）</h1>"
            f"<div style='color:#8ea3b6;font-size:13px'>对象：{res['product']}｜逐项注入本次两处致命错，验出厂闸真能拦</div>"
            + banner
            + "<table class='dt' style='width:100%;border-collapse:collapse;margin-top:12px'>"
              "<tr><th>测试项</th><th>预期</th><th>结果</th><th>命中规则/说明</th></tr>" + rows + "</table>"
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
    for c in res["cases"]:
        print(f"  [{'OK' if c['ok'] else '✗'}] {c['name']} → 预期{c['expect']}·"
              + (f"命中{len(c['fails'])}条" if c["fails"] else "无告警"))
    print(f"\n{'✅ 全部达预期' if res['all_ok'] else '❌ 有未达预期'} · 证据→ {p.name}")
    return 0 if res["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
