# -*- coding: utf-8 -*-
"""★轮100 NG0 产品交付判据闸(五条·全部可当日核)。满足即可出正式产品(机器完工判据不拦交付)。
①无自相矛盾(L17过) ②无未真算数字带结论(L17 NB1-3) ③当日判断已做(需复核仍挂=0·未做显性列·L19) ④口径写明(data_date/价格日/分母/依据等级) ⑤缺项显性标注。"""
import sys, json, argparse, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
SEE = ROOT / "00_请先看这里"


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def check(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    prod = SEE / f"★每日产品_{dh}.html"
    if not prod.exists():
        return ["产品HTML不存在"], []
    html = prod.read_text(encoding="utf-8", errors="replace")
    sys.path.insert(0, str(ROOT / "scripts"))
    fails, oks = [], []
    # ①无自相矛盾(L17)
    try:
        from product_lint import _l17_consistency
        l17 = _l17_consistency({prod.name: html}, date)
        (oks if not l17 else fails).append("①无自相矛盾(L17)：%s" % ("通过" if not l17 else "FAIL %d条" % len(l17)))
    except Exception as e:
        fails.append("①L17异常:%s" % e)
    # ②无未真算数字带结论(data-computed=false 不进判断区)
    bad = [m for m in re.findall(r'data-computed\s*=\s*"false"[^>]*>(.*?)</', html, re.S)
           if re.search(r"超\s*\d+\s*%|超限|合规\s*[✔√]|建议[加减买卖]", re.sub(r"<[^>]+>", " ", m))]
    (oks if not bad else fails).append("②无未真算数带结论：%s" % ("通过" if not bad else "FAIL %d处" % len(bad)))
    # ③当日判断已做(需复核仍挂=0·未做显性列)
    jc = _rj(ROOT / "data/pdca" / f"judgment_completeness_{dc}.json")
    pending = jc.get("★需复核仍挂", 99)
    undone_listed = ("判断未做" in html) if jc.get("③判断未做", 0) else True
    if pending == 0 and undone_listed:
        oks.append("③当日判断已做：需复核仍挂0·未做%d只已显性列" % jc.get("③判断未做", 0))
    else:
        fails.append("③当日判断：需复核仍挂%s(须0)·未做是否显性列=%s" % (pending, undone_listed))
    # ④口径写明(数据日/价格对应交易日/分母/依据等级)
    has_date = ("数据日" in html) or (dh in html)
    kou = has_date and ("价格对应交易日" in html) and ("分母" in html) and \
        ("依据等级" in html or "参数出处等级" in html or "特级" in html or "B级" in html)
    (oks if kou else fails).append("④口径写明(data_date/价格日/分母/依据等级)：%s" % ("通过" if kou else "缺"))
    # ⑤缺项显性标注
    gap = "本册已知缺项" in html or "缺什么" in html
    (oks if gap else fails).append("⑤缺项显性标注(缺什么/为什么/何时补)：%s" % ("通过" if gap else "缺"))
    return fails, oks


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    fails, oks = check(a.date)
    for o in oks:
        print("  ✔", o)
    for f in fails:
        print("  ✗", f)
    if fails:
        print("[产品交付判据 FAIL] %d/5 未过→不得出正式产品" % len(fails)); return 6
    print("[产品交付判据 PASS] 五条全过→可出正式产品(机器完工判据不拦交付·缺项已局部标注)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
