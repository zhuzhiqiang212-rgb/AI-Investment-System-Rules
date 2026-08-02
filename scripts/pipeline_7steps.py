# -*- coding: utf-8 -*-
"""★轮75 AN1:七步流程固化进机器(正式尺_每日生产流程_七步定义_20260802)。
每步登记应产出物·跑完核实物在不在·缺→该步FAIL。出 data/logs/pipeline_7steps_{date}.json(七步各自谁做/做没做/产出物/耗时)。
AN1-3:第3步(Opus5正文)无当日正文交付件→渲染步(第4步)FAIL·不许用上一日正文/模板顶替。
AN1-4:Opus5开工盘点 data/logs/opus5_checklist_{date}.json 未留痕→标『本轮未做开工盘点』。"""
import sys, json, argparse, glob
from datetime import datetime, timezone, timedelta
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent


def _exists_any(patterns):
    hits = []
    for pat in patterns:
        hits += glob.glob(str(ROOT / pat))
    return hits


def _opus5_zhengwen(date):
    """第3步产出=Opus5当日正文交付件(.md·00_任务中心/)。★AN1-3:找当日的·不许上一日顶替。"""
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:8])
    # 匹配 101_Opus5正文交付_{data日}_*.md 等·文件名含 Opus5正文 且含数据日
    cands = glob.glob(str(ROOT / "00_任务中心" / "*Opus5正文*.md")) + glob.glob(str(ROOT / "00_任务中心" / "*正文交付*.md"))
    today_ones = [c for c in cands if dc in Path(c).name or dh in Path(c).name]
    return today_ones, cands


def build(date, data_date=None):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:8])
    dd = (data_date or date).replace("-", "")   # 数据日(周末产品data_date=当日·价格是上一交易日)
    STEPS = [
        ("第1步 数据层", "Code", [f"data/market/daily_scan_{dc}.json", f"data/reports/production_{dc}.json",
                                f"data/accounts/futu_positions_{dc}.json", f"data/evidence_chain/daily_{dc}.json",
                                f"data/inbox/new_materials_{dc}.json", "data/market/latest_market_snapshot.json",
                                f"data/market/macro_flow_{dc}.json"]),   # ★轮77 AQ3-3:第③层资金流
        ("第2步 材料整理", "Claude 4.8", [f"data/reports/data_sanity_{dc}.json"]),   # 缺项/冲突/新鲜度(近似:data_sanity)
        ("第3步 投资判断", "Opus 5", "★正文交付件(.md)"),   # 特判(见下)
        ("第4步 渲染出品", "Code", [f"00_请先看这里/★每日产品_{dh}.html", "data/product_manifest.json"]),
        ("第5步 产品初验", "Opus 5", glob.glob("_never_") or [f"00_任务中心/*初验*{dc}*.md"]),
        ("第6步 独立终验", "GPT V6", [f"00_任务中心/*终验*{dc}*.md"]),
        ("第7步 董事长", "董事长", "拍板(人工·机器不判)"),
    ]
    rows = []
    render_block = False   # AN1-3:第3步缺→第4步渲染应FAIL
    for name, who, spec in STEPS:
        if name.startswith("第3步"):
            today_zw, all_zw = _opus5_zhengwen(dd)
            done = bool(today_zw)
            rows.append({"步": name, "谁做": who, "做没做": ("已做" if done else "★未做(无当日正文·不许上一日顶替)"),
                         "产出物": today_zw or "（无当日Opus5正文交付件·数据日%s）" % dh,
                         "★AN1-3": ("当日正文在·渲染可进" if done else "★缺当日正文→第4步渲染应FAIL(AN1-3)")})
            if not done:
                render_block = True
            continue
        if isinstance(spec, str):
            rows.append({"步": name, "谁做": who, "做没做": "人工/非机器判", "产出物": spec})
            continue
        hits = _exists_any(spec) if all("*" not in s for s in spec) else sum([glob.glob(str(ROOT / s)) for s in spec], [])
        done = bool(hits)
        rows.append({"步": name, "谁做": who, "做没做": ("已做" if done else "★未做/产出物缺"),
                     "产出物": [Path(h).name for h in hits][:6] or "（缺：%s）" % "、".join(spec)})
    # ★轮77 AQ3-3:第1步产出物加「资金流层指标接通 N/10」
    _mf = ROOT / "data" / "market" / f"macro_flow_{dc}.json"
    if _mf.exists():
        try:
            _st = json.loads(_mf.read_text(encoding="utf-8")).get("★接通统计", {})
            _conn = _st.get("机器自动接通(全部)N/10", _st.get("接通N/10", "?/10"))
        except Exception:
            _conn = "?/10"
        for _r in rows:
            if _r["步"].startswith("第1步"):
                _r["资金流层指标接通"] = _conn
    # AN1-4 opus5盘点
    chk = ROOT / "data" / "logs" / f"opus5_checklist_{dc}.json"
    opus5_checklist = "已留痕" if chk.exists() else "★本轮未做开工盘点(无 opus5_checklist)"
    out = {"_说明": "★轮75 AN1 七步流程固化。每步谁做/做没做/产出物。★产品末尾附此表·判据=产品里能看出七步各自做没做。"
                    "第3步缺当日Opus5正文→第4步渲染FAIL(AN1-3)。",
           "date": dh, "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
           "七步": rows, "★第4步渲染是否应拦(AN1-3)": render_block,
           "opus5开工盘点(AN1-4)": opus5_checklist}
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True)
    ap.add_argument("--data-date", default=None, help="数据日(周末产品=当日·价格是上一交易日)")
    a = ap.parse_args()
    out = build(a.date, a.data_date)
    p = ROOT / "data" / "logs" / f"pipeline_7steps_{a.date.replace('-', '')}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    b = p.read_bytes(); json.loads(b.decode())
    print("[pipeline_7steps] %s → %s · 乱码%d" % (a.date, p.name, b.count(b"\xef\xbf\xbd")))
    for r in out["七步"]:
        print("  %s（%s）：%s" % (r["步"], r["谁做"], r["做没做"]))
    print("  ★第4步渲染应拦(AN1-3):", out["★第4步渲染是否应拦(AN1-3)"], "· opus5盘点:", out["opus5开工盘点(AN1-4)"])
    # AN1-3:第3步缺→退出码7(供渲染步/管线判)
    return 7 if out["★第4步渲染是否应拦(AN1-3)"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
