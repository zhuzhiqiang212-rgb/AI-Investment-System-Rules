# -*- coding: utf-8 -*-
"""★轮85 CG7-1:待接清零框架。把待接分三类:数据源缺/判断缺(Opus5填)/永远接不上。
★『永远接不上』改标『结构性不可得·非待接』·不计入待接数(判据≤20)。★Code只建分类框架+机器可判部分·判断缺由Opus5填。"""
import sys, json, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


# ★轮96 NB3-4:标签重分类——禁用「结构性不可得」掩盖「按董事长指示不做」/「接入失败」/「许可缺口」。逐项按真实性质归类。
STRUCTURAL = [
    {"项": "IBKR账户每日底数", "真实分类": "按董事长指示不做(非不可得)",
     "说明": "董事长07-19明确指示IBKR不做每日目标管理·沿用已确认快照即当前真实状态(GPT认可)。★之前标『结构性不可得』是用错标签(把主动决定说成客观限制)·已改。"},
    {"项": "bitFlyer账户每日底数", "真实分类": "按董事长指示不做(非不可得)",
     "说明": "同IBKR·董事长07-19指示不做每日更新·沿用已确认快照。"},
    {"项": "板块资金净流入", "真实分类": "★接入未做(非不可得)·GPT判可用替代指标实现",
     "说明": "GPT裁定不是不可得:可用ETF资金流/成交额/涨跌扩散(advance-decline)/相对强弱替代→已列入NB3-2待实现·不再标结构性不可得。"},
    {"项": "CPI/PCE物价", "真实分类": "★接入失败(非不可得)·BEA/BLS官方公开",
     "说明": "GPT裁定:BEA/BLS官方公开·FRED被CDN阻断≠官方源不可用·属我接入失败。CPI/非农已从BLS公开API接通(轮85)·PCE待从BEA官方直采(NB3-3)。"},
    {"项": "韩股 universe", "真实分类": "数据源许可未解决(非泛化不可得)",
     "说明": "韩股全市场扫描的数据源许可未解决·标『数据源/许可缺口』·非笼统不可得。"},
    {"项": "新标的 forward EPS", "真实分类": "商业数据源/许可缺口(非泛化不可得)",
     "说明": "共识forward EPS属商业数据源(Bloomberg/Refinitiv)·标『商业数据源缺口』·非笼统不可得。"},
    {"项": "成本价(20只)", "真实分类": "按董事长提供(G0预测优先·成本不影响预测·非阻塞)",
     "说明": "无历史成交记录·需董事长提供·机器不编·且成本不影响预测(不计入未完工)。"},
]


def build(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    sanity = _rj(ROOT / "data/reports" / f"data_sanity_{dc}.json")
    # 数据源缺(机器可自动补·今日已补的:CPI/非农/FIMA/FOMC/避险/稳定币·剩PCE归结构性)
    data_missing = []
    ext = _rj(ROOT / "data/market" / f"macro_flow_ext_{dc}.json")
    for x in ext.get("补充指标", []):
        if not x.get("接通"):
            data_missing.append({"项": x.get("指标"), "原因": x.get("★失败原因", "")[:80], "试了": x.get("试了哪些源")})
    # 判断缺(Opus5填·非Code)——占位框架
    judge_missing = {"_说明": "判断缺由Opus5填(非Code):如美股合理PE口径/异常股贵贱裁定/情景概率等·Code不代填",
                     "约数(尺记)": 14}
    struct = STRUCTURAL
    return {
        "_说明": "★轮85 CG7-1 待接清零框架。三类:数据源缺(机器补)/判断缺(Opus5填)/结构性不可得(移出待接·非待接)。判据待接≤20。",
        "date": dh, "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "一_数据源缺(机器可补)": data_missing,
        "二_判断缺(Opus5填·非Code)": judge_missing,
        "三_按真实性质分类(★轮96 NB3-4·禁用『结构性不可得』掩盖『按指示不做』/『接入失败』)": struct,
        "计数": {"数据源缺": len(data_missing), "按真实性质归类项": len(struct),
               "★NB3-4说明": "GPT批评『结构性不可得』被滥用·已逐项按真实性质重分类:IBKR/bitFlyer=按董事长指示不做·净流入=接入未做(可替代)·CPI/PCE=接入失败(BEA/BLS公开)·韩股/forwardEPS=许可缺口。★无一项再用『结构性不可得』掩盖主动决定或接入失败"},
        "★待接清零状态": "框架已建·结构性不可得已移出·数据源缺大部已补(剩PCE需key)·判断缺≈14需Opus5填→待接实数须Opus5填判断缺后由render_3layer页头重算",
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out = build(a.date)
    p = ROOT / "data/reports" / f"tbd_reclassify_{a.date.replace('-', '')}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    b = p.read_bytes(); json.loads(b.decode())
    print("[tbd_reclassify] %s → %s · 乱码%d" % (a.date, p.name, b.count(b"\xef\xbf\xbd")))
    print("  " + out["计数"]["★NB3-4说明"])
    print("  " + out["★待接清零状态"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
