# -*- coding: utf-8 -*-
"""★★★轮218 GPT V7:日股決算短信 A 档扫描(接入每日生产链·第⑨b2步·【非关键环】)。
★第一版只扫【日股持仓】(不扩全市场·GPT明令不得延误·先小范围真跑)。
★产出 data/funnel/jp_A_gate_{当日}.json(格式照 jp_A_gate_shinetsu_20260806.json)。
★失败处理(CLAUDE.md 2.7铁律):
  - J-Quants 连不上 → 如实报「连不上·未扫描」·【不得用旧数据顶充】。
  - 某只无決算短信 → 记「无短信·A档关闭」·非错误·不阻断当日生产。
  - 本步非关键:失败只告警·不停整条生产线。
★A 档判定全部经 verifier(轮217 GPT V7终验通过·本脚本不碰验证逻辑)。"""
import sys, json, glob, time, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import jquants_pipeline as jp   # ★复用五环管道(内含verifier)·本脚本只做编排+聚合


def _jp_holdings():
    """日股持仓代码(读 holding_dossier_JP_<code>.json)。"""
    codes = []
    for f in glob.glob(str(ROOT / "data/accounts/holding_dossier_JP_*.json")):
        m = re.search(r"holding_dossier_JP_(\d{4})\.json", f.replace("\\", "/"))
        if m:
            codes.append(m.group(1))
    return sorted(set(codes))


def _is_conn_fail(o):
    return "认证/取数失败" in (o.get("★断点") or "") or "invalid" in (o.get("★断点") or "").lower()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    d = time.strftime("%Y%m%d")
    argv = sys.argv
    for i, a in enumerate(argv):
        if a == "--date" and i + 1 < len(argv):
            d = argv[i + 1].replace("-", "")
    codes = _jp_holdings()
    out = {"_说明": "★轮218 日股決算短信A档扫描(每日⑨b2·非关键环)·第一版只扫日股持仓·A档判定经verifier(轮217终验)",
           "date": "%s-%s-%s" % (d[:4], d[4:6], d[6:8]), "as_of": time.strftime("%Y-%m-%d %H:%M JST"),
           "扫描代码": codes, "结果": {}}
    A = noshin = err = 0
    conn = "未知"
    for code in codes:
        try:
            o = jp.run(code, "JP." + code)
        except Exception as e:
            err += 1
            out["结果"][code] = {"A档开放": False, "错误": str(e)[:100]}
            continue
        if _is_conn_fail(o):
            # ★J-Quants连不上→立即停止扫描·不顶充·不反复敲(CLAUDE 2.7)
            conn = "连不上"
            out["结果"][code] = {"A档开放": False, "断点": o.get("★断点")}
            out["★告警"] = "J-Quants连不上(在%s处)·未完成扫描·【不顶充旧数据】·非关键环不阻断当日生产" % code
            break
        conn = "OK"
        a_open = bool(o.get("★A档开放"))
        ev = o.get("★证据") or {}
        det = ev.get("六项逐项") or {}
        rec = {"A档开放": a_open, "断点": o.get("★断点")}
        if a_open:
            # ★★★轮219 补漏1:A档开出必须留【证据原文】(散文=命中句/表式=来源行文本)·不得null。
            证据原文 = ev.get("证据原文") or (det.get("_表式证据") or {}).get("来源行文本") or ev.get("原文片段")
            if not 证据原文:
                # ★取不到原文→A档不开(与pipeline硬闸一致·双保险)
                rec["A档开放"] = False
                rec["断点"] = "A档取不到可核证据原文→不开(无法复核的证据不算证据)"
                out["结果"][code] = rec
                continue
            A += 1
            rec.update({"五元组": ev.get("五元组"), "六项逐项": det, "_事实路径": ev.get("_事实路径") or det.get("_事实路径"),
                        "证据原文": 证据原文, "表格原文行": (det.get("_表式证据") or {}).get("来源行文本")})
        elif "无決算短信" in (o.get("★断点") or ""):
            noshin += 1
            rec["状态"] = "无決算短信·A档关闭(非错误)"
        out["结果"][code] = rec
    out["汇总"] = {"扫描数": len(codes), "已处理": len(out["结果"]), "A档开出": A,
                  "无決算短信": noshin, "出错": err, "连接": conn}
    (ROOT / "data/funnel").mkdir(parents=True, exist_ok=True)
    (ROOT / "data/funnel" / ("jp_A_gate_%s.json" % d)).write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("日股A档扫描: 扫%d只·已处理%d·A档开出%d·无短信%d·出错%d·连接%s"
          % (len(codes), len(out["结果"]), A, noshin, err, conn))
    if conn == "连不上":
        print("  ⚠ J-Quants连不上·如实报未扫描·不顶充(非关键环·不停生产线)")
    return 0   # ★非关键环:恒返回0·不阻断当日生产


if __name__ == "__main__":
    raise SystemExit(main())
