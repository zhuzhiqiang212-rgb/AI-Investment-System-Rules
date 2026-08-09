# -*- coding: utf-8 -*-
"""★轮94 MA1:外部资料(湖水/老雷)结构化提取——把机器接不到的四维度事实提进机器。
★MA5铁律:Code只提【事实数值/日期/来源】·★不提观点/结论/买卖建议(那是判断岗Opus5的活)。
四类:MA1-1仓位维度(净杠杆/AI硬件净暴露/历史对比)·MA1-2资金流向分主体·MA1-3事件日历·MA1-4宏观数据点。
每条标来源(原文件+日期)+B级(外部资料非机器直采)。输出 data/external/indicators_{date}.json。"""
import sys, json, argparse, glob, os, re
from datetime import datetime, timezone, timedelta, date as _date
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
TEXT = ROOT / "data" / "external" / "text"


def _norm(t):
    """PDF提取常见全角/异体→半角·便于正则。"""
    tb = {"⼀": "一", "⼆": "二", "⼆": "二", "⾦": "金", "⽔": "水", "⼯": "工", "⼩": "小", "⼤": "大",
          "⽉": "月", "⽇": "日", "⾮": "非", "⼼": "心", "⾏": "行", "⼊": "入", "�]": "]", "⼨": "寸", "⾄": "至"}
    for k, v in tb.items():
        t = t.replace(k, v)
    t = t.replace("，", ",").replace("．", ".").replace("　", " ")
    # 全角数字→半角
    t = t.translate(str.maketrans("０１２３４５６７８９％", "0123456789%"))
    return t


def _src(txt, fn):
    m = re.search(r"【日期】([\d-]+)", txt)
    return {"原文件": fn, "资料日期": m.group(1) if m else "?"}


def extract_one(txt, fn):
    txt = _norm(txt)
    src = _src(txt, fn)
    out = {"仓位维度": [], "资金流向": [], "事件日历": [], "宏观数据点": []}
    # MA1-1 仓位维度:net leverage / 净杠杆 + 值
    for m in re.finditer(r"net leverage[^\d]{0,30}?(\d{2,3})\s*%", txt, re.I):
        out["仓位维度"].append({"指标": "对冲基金净杠杆(net leverage)", "值": m.group(1) + "%", **src, "级别": "B级·外部资料"})
    # 历史对比值(25年同期78%·25年8月最低76% 等)
    for m in re.finditer(r"(2[0-9]年(?:同期|\d{1,2}月最低点?)[^\d]{0,8})\s*(?:是)?\s*(\d{2,3})\s*%", txt):
        out["仓位维度"].append({"指标": "历史对比·" + re.sub(r"\s+", "", m.group(1)), "值": m.group(2) + "%", **src, "级别": "B级·外部资料"})
    # AI硬件净暴露/仓位
    for m in re.finditer(r"(AI硬件[^\d。]{0,20}?(?:净暴露|暴露|仓位))[^\d]{0,15}?(\d{1,3})\s*%", txt):
        out["仓位维度"].append({"指标": re.sub(r"\s+", "", m.group(1)), "值": m.group(2) + "%", **src, "级别": "B级·外部资料"})
    # MA1-2 资金流向·分主体净买卖(散户/外资/券商/本地机构/hedge fund + net buyer/seller + 额)
    for m in re.finditer(r"(散户|外资|券商和?本地机构|本地机构|hedge fund|Long Only)[^。\n]{0,8}?(net buyer|net seller|small net seller|small net buyer|net sell|net buy)[^。\n]{0,6}?([\d.]+\s*(?:bln|bn|billion|million|mln)?)", txt, re.I):
        amt = m.group(3).strip()
        out["资金流向"].append({"主体": m.group(1), "方向": m.group(2).lower(), "净额": amt if re.search(r"\d", amt) else "N/A", **src, "级别": "B级·外部资料"})
    # 集中标的(外资买盘集中在 X 和 Y)
    for m in re.finditer(r"(外资|散户)[^。\n]{0,10}?(?:集中在|买盘.{0,6}集中)[^。\n]{0,30}?([A-Za-z一-鿿]{2,}(?:和|、)[A-Za-z一-鿿]{2,})", txt):
        out["资金流向"].append({"集中标的_主体": m.group(1), "集中标的": m.group(2), **src, "级别": "B级·外部资料"})
    # MA1-3 事件日历(★事件锚定·日期取事件前后最近的合法MM/DD·PDF易切乱→附原文片段供核)
    for m in re.finditer(r"(AI硬件[^\n。]{0,4}?财报|财报|非农|CPI|PCE|FOMC|升级)", txt):
        ev = m.group(1); a, b = max(0, m.start() - 14), m.end() + 6
        win = txt[a:b]
        dm = re.search(r"(0?[1-9]|1[0-2])[/.](0?[1-9]|[12]\d|3[01])", win)   # 合法 月/日
        dt = ("%02d/%02d" % (int(dm.group(1)), int(dm.group(2)))) if dm else "日期见原文"
        out["事件日历"].append({"日期": dt, "事件": ev, "原文片段": re.sub(r"\s+", "", win)[:40], **src, "级别": "B级·外部资料·日期以原文为准"})
    # MA1-4 宏观数据点(核心PCE/CPI/非农 + 值 + 预期比较·窗口内找预期词)
    for m in re.finditer(r"(核心PCE|核心CPI|CPI|非农就业|非农|PCE)\s*([\d.]+\s*%)", txt):
        win = txt[m.start():m.end() + 20]
        cm = re.search(r"(低于预期|高于预期|符合预期|超预期|不及预期)", win)
        out["宏观数据点"].append({"指标": m.group(1), "值": m.group(2).strip(), "对比预期": cm.group(1) if cm else "?",
                            "原文片段": re.sub(r"\s+", "", win)[:40], **src, "级别": "B级·外部资料·待机器直采确认"})
    return out


def build(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    cutoff = _date(int(dc[:4]), int(dc[4:6]), int(dc[6:8])) - timedelta(days=7)
    agg = {"仓位维度": [], "资金流向": [], "事件日历": [], "宏观数据点": []}
    n_files = 0
    for f in sorted(glob.glob(str(TEXT / "*.txt"))):
        txt = Path(f).read_text(encoding="utf-8", errors="replace")
        m = re.search(r"【日期】([\d-]+)", txt)
        try:
            fd = _date(*[int(x) for x in m.group(1).split("-")]) if m else None
        except Exception:
            fd = None
        if fd and fd < cutoff:
            continue
        n_files += 1
        one = extract_one(txt, os.path.basename(f))
        for k in agg:
            agg[k].extend(one[k])
    # 去重(同指标+值+来源)
    def _dedup(lst):
        seen, out = set(), []
        for x in lst:
            key = json.dumps({k: x[k] for k in x if k != "原文件"}, ensure_ascii=False, sort_keys=True)
            if key not in seen:
                seen.add(key); out.append(x)
        return out
    for k in agg:
        agg[k] = _dedup(agg[k])
    return {
        "_说明": "★轮94 MA1 外部资料结构化提取(湖水/老雷)。★Code只提事实数值/日期/来源·不提观点(MA5)。四维度均机器接不到·B级(外部资料非机器直采)。",
        "date": dh, "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "扫描文件数": n_files, "窗口起始": cutoff.isoformat(),
        "MA1-1_仓位维度": agg["仓位维度"], "MA1-2_资金流向": agg["资金流向"],
        "MA1-3_事件日历": agg["事件日历"], "MA1-4_宏观数据点": agg["宏观数据点"],
        "计数": {k: len(agg[k]) for k in agg},
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out = build(a.date)
    p = ROOT / "data" / "external" / f"indicators_{a.date.replace('-', '')}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    b = p.read_bytes(); json.loads(b.decode())
    print("[external_indicators_extract] %s · 文件%d · 乱码%d · 计数 %s" % (
        a.date, out["扫描文件数"], b.count(b"\xef\xbf\xbd"), out["计数"]))
    for k in ("MA1-1_仓位维度", "MA1-2_资金流向", "MA1-3_事件日历", "MA1-4_宏观数据点"):
        for x in out[k][:4]:
            print("  [%s] %s" % (k[:6], json.dumps({kk: vv for kk, vv in x.items() if kk not in ("原文件", "级别")}, ensure_ascii=False)[:90]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
