# -*- coding: utf-8 -*-
"""★★★轮217 GPT V7批准·決算短信表式増減率识别 6条测试(GPT明令:就这6条·不再加)。
★import 真 verifier.parse_tanshin_ratio(不复制逻辑)。正例3(①信越真PDF表·②△減·③0.0持平)+反例3(④空白不判·⑤够不到表外·⑥跨行错配防止)。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verifier import parse_tanshin_ratio, six_align  # ★真验证器

SYN = ["売上高", "売上収益", "营收"]
# ①信越真实決算短信サマリー表(TDnet公開データ·DiscNo 20260724598954·非机密)
SHINETSU = ("（１）連結経営成績（累計） （％表示は、対前年同四半期増減率）\n"
            "売上高 営業利益 経常利益 親会社株主に帰属する\n四半期純利益\n"
            "百万円 ％ 百万円 ％ 百万円 ％ 百万円 ％\n"
            "2027年３月期第１四半期 662,424 5.4 173,798 4.2 192,129 5.8 130,829 3.5\n"
            "2026年３月期第１四半期 628,549 5.1 166,803 △12.7 181,621 △17.4 126,428 △12.2")


def _row(ratio):  # 合成表(売上高栏の増減率を差し替え)
    return ("（％表示は、対前年同期増減率）\n売上高 営業利益\n百万円 ％ 百万円 ％\n"
            "2027年３月期第１四半期 100,000 %s 50,000 3.1" % ratio)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    P = F = 0

    def chk(name, cond):
        nonlocal P, F
        P += bool(cond); F += (not cond)
        print(("✅" if cond else "❌") + " " + name)

    # 正例①:信越真PDF表→売上高 662,424 · +5.4% · 増 → A档相当(方向/幅度匹配)
    r1 = parse_tanshin_ratio(SHINETSU, SYN, {"方向": "增长", "幅度": 0.054})
    chk("①信越真表→増长+5.4増減率匹配·栏位={}·原文={}".format((r1 or {}).get("来源栏位"), (r1 or {}).get("增減率原文")),
        r1 and r1["方向"] == "增长" and r1["方向匹配"] and r1["幅度匹配"] and r1["指標值原文"] == "662,424")
    # ②△开头→減
    r2 = parse_tanshin_ratio(_row("△5.4"), SYN, {"方向": "下降", "幅度": 0.054})
    chk("②△5.4→減", r2 and r2["方向"] == "下降" and r2["方向匹配"])
    # ③0.0→持平
    r3 = parse_tanshin_ratio(_row("0.0"), SYN, {"方向": "持平", "幅度": 0.0})
    chk("③0.0→持平", r3 and r3["方向"] == "持平" and r3["方向匹配"] and r3["幅度匹配"])
    # ④増減率栏空白→不判断(不得默认増)
    blank = "（％表示は、対前年同期増減率）\n売上高 営業利益\n百万円 ％ 百万円 ％\n2027年３月期第１四半期 100,000"
    chk("④空白→None(不判断方向)", parse_tanshin_ratio(blank, SYN, {"方向": "增长", "幅度": 0.05}) is None)
    # ⑤表内無値·正文远处(320字外)有総資産増加→仍不判断(证明够不到表外)
    far = blank + "　" * 360 + "総資産は前年比大幅に増加した。"
    chk("⑤够不到表外(総資産増加)→None", parse_tanshin_ratio(far, SYN, {"方向": "增长", "幅度": 0.05}) is None)
    # ⑥跨行错配:方向と幅度は同一トークン由来→构造的に防止(来源栏位単一·来源行単一)
    chk("⑥方向幅度同栏同源(防跨行错配)", r1 and r1["来源栏位"] == "第1指標(増減率栏)" and "662,424 5.4" in r1["来源行文本"])

    # ★端到端:six_align 用信越真表 → 四项事实同窗 True · 路径=決算短信表式
    W = {"实体": "JP.4063", "指标": "营收", "方向": "增长", "幅度": 0.054, "期间": "同比"}
    aligned, det = six_align(SHINETSU, W, index_code="4063")
    chk("★six_align端到端:四项事实同窗=%s·路径=%s" % (det.get("四项事实同窗"), det.get("_事实路径")),
        det.get("四项事实同窗") and det.get("_事实路径") == "決算短信表式")

    print("═══ 表式6条测试: 通过 %d · 失败 %d ═══" % (P, F))
    return 0 if F == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
