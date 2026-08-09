# -*- coding: utf-8 -*-
"""★轮102 A1:第一三共(JP.4568)卖出执行方案·组合净影响【纯算术·Code做】。
用与产品同一个 portfolio_concentration(同FX/同防御判定)算 before/after→保证与产品别处数字一致(不撞L18)。
★限价档位/跳空阈值/分笔方式＝风险判断＝Opus5(Code不代编·标待Opus5)。★现金基数=null(未接)→现金占比不编·只报卖出所得增量。"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from full_product_render import portfolio_concentration, resolve_usdjpy, _mv_usd


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def build(date):
    dc = date.replace("-", "")
    prod = _rj(ROOT / "data/reports" / f"production_{dc}.json")
    holds = prod.get("holdings", [])
    SYM = "JP.4568"
    sell = next((h for h in holds if h.get("symbol") == SYM), None)
    if not sell:
        print("[exec_plan] 未找到 JP.4568"); return 2
    usdjpy, fx_src = resolve_usdjpy()
    # ★人话化FX来源(不印内部json文件名/裸字段·治L4c/L46泄露)
    import re as _re
    fx_src = _re.sub(r"[\w-]+\.json", "统一持仓快照", str(fx_src))
    fx_src = _re.sub(r"fx\.USDJPY", "USDJPY", fx_src).replace("·统一持仓快照", "统一持仓快照").strip("·. ")

    def jp_ratio(hs, total_usd):
        jp = 0.0
        for h in hs:
            if str(h.get("symbol", "")).startswith("JP."):
                u, _ = _mv_usd(h, usdjpy)
                jp += (u or 0.0)
        return (jp / total_usd * 100.0) if total_usd else None, jp

    before = portfolio_concentration(holds)
    after_holds = [h for h in holds if h.get("symbol") != SYM]
    after = portfolio_concentration(after_holds)
    tb, ta = before.get("total_usd"), after.get("total_usd")
    jpb, jpb_usd = jp_ratio(holds, tb)
    jpa, jpa_usd = jp_ratio(after_holds, ta)
    defb = ((before.get("categories", {}) or {}).get("防御", {}) or {}).get("pct")
    defa = ((after.get("categories", {}) or {}).get("防御", {}) or {}).get("pct")
    sell_usd, _ = _mv_usd(sell, usdjpy)

    # 账户拆分(董事长给定·来自 holdings_true accounts)
    ht = _rj(ROOT / "data/accounts" / f"holdings_true_{dc}.json")
    acc = next((x.get("accounts", []) for x in ht.get("holdings", []) if x.get("symbol") == SYM), [])
    split = {a.get("account") or a.get("broker") or a.get("券商"): a.get("quantity") or a.get("shares") or a.get("数量") for a in acc}

    out = {
        "_说明": "★轮102 A1 第一三共卖出执行方案·组合净影响(纯算术·Code)。限价/跳空/分笔=Opus5判断(待补)。现金占比=null未接不编。",
        "date": date, "价格对应交易日": "2026-07-31（周五收盘·周一开盘可能跳空）",
        "标的": "第一三共 JP.4568", "参考价_JPY": sell.get("price"),
        "总股数": sell.get("quantity"),
        "账户拆分": {"SBI": 3400, "富途": 6500, "_来源": "董事长给定·holdings_true accounts", "_holdings_true实读": split},
        "卖出市值_JPY": sell.get("market_value"),
        "卖出所得折美元": round(sell_usd, 0) if sell_usd else None,
        "FX_USDJPY": usdjpy, "FX来源": fx_src,
        "组合净影响": {
            "★口径": "分母＝已扫持仓市值合计(非现金融资全账户闭合)·与产品规矩4同源",
            "总持仓市值_USD": {"卖出前": round(tb, 0), "卖出后": round(ta, 0), "变化": round((ta or 0) - (tb or 0), 0)},
            "日股占比_pct": {"卖出前": round(jpb, 2) if jpb else None, "卖出后": round(jpa, 2) if jpa else None},
            "防御仓占比_pct": {"卖出前": round(defb, 2) if defb is not None else None, "卖出后": round(defa, 2) if defa is not None else None,
                          "★注": "第一三共属防御(三共/医药信号)·卖出后防御占比下降·防御下限15%"},
            "现金占比_pct": "★待接(不编)：现金基数=null(portfolio_check现金各账户为空)·无法算现金占比·只能报卖出所得增量 $%s" % (round(sell_usd, 0) if sell_usd else "?"),
        },
        "★执行判断_待Opus5(Code不代编·投资判断非算术)": {
            "限价档位": "★待Opus5：建议挂单价区间与理由=风险判断。Opus5当前只给『周一开盘卖出全部9900股·市价级』(opus5_content 五之今天周一做什么)·未给限价档位。",
            "跳空低开处理X%": "★待Opus5：低开X%以内照卖/超过如何=风险阈值判断·Opus5未给。",
            "分笔方式": "★待Opus5：一次性or分几笔·时间间隔=执行策略判断·Opus5未给。",
            "Opus5已给的执行指令(原样)": "周一开盘卖出全部 9,900 股（SBI 3,400 ＋ 富途 6,500），转现金不买入（opus5_content『五_今天周一做什么』）。",
        },
        "★防御下限提示": "防御下限15%(CONC_LOWER_LIMITS)·卖出第一三共后防御占比进一步下降→若已破15%下限·卖出加剧·此为结构性提示(Opus5判是否需补防御)。",
    }
    op = ROOT / "data/accounts" / f"exec_plan_4568_{dc}.json"
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[exec_plan] 写出", op.name)
    print("  总持仓 前 $%s → 后 $%s" % (round(tb), round(ta)))
    print("  日股占比 前 %.2f%% → 后 %.2f%%" % (jpb, jpa))
    print("  防御占比 前 %.2f%% → 后 %.2f%%" % (defb, defa))
    print("  卖出所得 ≈ $%s (FX=%.2f·%s)" % (round(sell_usd), usdjpy, fx_src))
    print("  现金占比：待接(现金null·不编)")
    return 0


if __name__ == "__main__":
    import argparse
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    raise SystemExit(build(a.date))
