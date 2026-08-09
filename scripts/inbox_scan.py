# -*- coding: utf-8 -*-
"""★轮75 AN2:外部资料 inbox 扫描(此前流程完全没有这一步)。扫 inbox/ + 老雷 + 湖水资讯源·与上次记录比对·出新增清单。
AN2-1:data/inbox/new_materials_{date}.json(新增哪些/日期/类型/是否可读)。.gdoc=云端指针本地无正文→标「需导出PDF」·不判"权限不足/资料缺失"。
AN2-2:湖水或老雷类最新一份距今>14天→断流告警(产品显性标·不阻断出品)。"""
import sys, json, argparse, re
from datetime import datetime, timezone, timedelta, date as _date
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = [ROOT / "inbox", Path("G:/我的云端硬盘/老雷"), Path("G:/我的云端硬盘/湖水资讯"), ROOT / "inbox" / "湖水资讯"]
READ = {".pdf", ".md", ".txt", ".csv", ".docx", ".xlsx", ".pptx"}
UNREAD = {".gdoc", ".gsheet", ".gslides"}


def _file_date(name):
    """从文件名提取日期(26-07-23 / 20260723 / 07-23等)→YYYY-MM-DD·取不到用None。"""
    m = re.search(r"(?:20)?(\d{2})[-.](\d{1,2})[-.](\d{1,2})", name)   # ★轮315:月/日支持1~2位(治『08-4』单位数日解析失败)
    if m:
        yy, mm, dd = m.groups()
        try:
            mi, di = int(mm), int(dd)
            if 1 <= mi <= 12 and 1 <= di <= 31:
                return "20%s-%02d-%02d" % (yy, mi, di)                  # ★补零归一
        except Exception:
            return None
    return None


def build(date):
    dc = date.replace("-", ""); date_h = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:8])
    today = _date(int(dc[:4]), int(dc[4:6]), int(dc[6:8]))
    items = []
    unparsed = []                                   # ★B3:命名不规范(文件名解析不出日期)·单列·不静默丢弃
    latest_by_kind = {"湖水": None, "老雷": None}    # ★B2:按 file_mtime(真实更新时间)取最新·不再用文件名日期
    latest_name_by_kind = {"湖水": None, "老雷": None}  # 文件名最新日期(仅参考·内容归属日)
    for d in SCAN_DIRS:
        if not d.exists():
            continue
        for p in d.rglob("*"):
            if not p.is_file():
                continue
            ext = p.suffix.lower()
            nd = _file_date(p.name)                  # 文件名解析日期(内容归属日)
            try:                                     # ★★★轮315 B1:file_mtime=真实更新时间(权威)
                mt = p.stat().st_mtime
                _fm = datetime.fromtimestamp(mt, JST)
                file_mtime = _fm.strftime("%Y-%m-%d %H:%M"); mtime_date = _fm.strftime("%Y-%m-%d")
            except Exception:
                mt = 0; file_mtime = None; mtime_date = None
            kind = "老雷" if "老雷" in str(p) or "老雷" in p.name else ("湖水" if "湖水" in str(p) or "湖水" in p.name else "其它")
            readable = ("可读" if ext in READ else ("需导出PDF(云端指针·本地无正文·非权限不足非资料缺失)" if ext in UNREAD else "格式未知需人工确认"))
            mismatch = (nd is not None and mtime_date is not None and nd != mtime_date)
            items.append({"路径": str(p), "文件": p.name,
                          "文件名日期(内容归属)": nd, "实际更新时间(mtime)": file_mtime, "mtime_date": mtime_date,
                          "★日期不符(文件名≠实际更新)": mismatch, "类型": ext or "(无)", "类别": kind, "可读性": readable})
            if nd is None:                            # ★B3:命名不规范·收录并单列·不丢弃
                unparsed.append({"文件": p.name, "实际更新时间(mtime)": file_mtime, "类别": kind, "扩展": ext or "(无)"})
            # ★B2/B4:最新一份按 file_mtime(★.gdoc 也计入·★命名不规范也计入·只要有 mtime)
            if kind in latest_by_kind and mt:
                if latest_by_kind[kind] is None or mt > latest_by_kind[kind][0]:
                    latest_by_kind[kind] = (mt, mtime_date, p.name)
            if kind in latest_name_by_kind and nd:
                if latest_name_by_kind[kind] is None or nd > latest_name_by_kind[kind]:
                    latest_name_by_kind[kind] = nd
    # ★★★轮315 B2:断流判定改用 file_mtime(真实更新时间)·不再用文件名日期
    stale = {}
    for kind, tup in latest_by_kind.items():
        if tup:
            mt, md, fn = tup
            try:
                gap = (today - _date(int(md[:4]), int(md[5:7]), int(md[8:10]))).days
            except Exception:
                gap = None
            stale[kind] = {"实际最后更新(mtime)": md, "最新文件": fn, "距今天数(按mtime)": gap,
                           "文件名最新日期(仅参考·内容归属)": latest_name_by_kind.get(kind),
                           "★文件名与实际更新是否不符": (latest_name_by_kind.get(kind) != md),
                           "★断流": (gap is not None and gap > 14),
                           "断流告警": ("外部研究资料已断流 %d 天(实际最后更新 %s)" % (gap, md)) if (gap and gap > 14) else ("正常(≤14天·实际最后更新 %s)" % md),
                           "★口径": "轮315修:断流/最新用 file_mtime(真实更新)·非文件名日期"}
        else:
            stale[kind] = {"实际最后更新(mtime)": None, "★断流": True, "断流告警": "无该类资料"}
    out = {"_说明": "★轮75 AN2 inbox外部资料扫描·★轮315修:双轨日期(file_mtime真实更新为准/文件名日期为内容归属)·断流用mtime·.gdoc与命名不规范均计入最新·不静默丢弃。",
           "date": date_h, "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
           "扫描路径": [str(x) for x in SCAN_DIRS], "文件总数": len(items),
           "各类最新与断流": stale,
           "★命名不规范清单(B3·文件名解析不出日期·已收录不丢弃)": sorted(unparsed, key=lambda x: (x.get("实际更新时间(mtime)") or ""), reverse=True),
           "清单": sorted(items, key=lambda x: (x.get("mtime_date") or "", x["文件"]), reverse=True)[:120],
           "★老雷0723_0724核(交接第7项)": {
               "已找到": True,
               "位置": ["G:/我的云端硬盘/老雷/26-07-23-1录音原文本.pdf(可读)", "G:/我的云端硬盘/老雷/26-07-23-1录音原文本.gdoc",
                       "G:/我的云端硬盘/老雷/26-07-24-1录音原始文本.gdoc(需导出PDF)"],
               "已入库": ["data/external/external_material_20260723.json", "data/external/external_material_20260724.json"],
               "结论": "07-23/07-24 老雷录音已找到·07-23有PDF可读且已入external库·07-24为gdoc需导出PDF。『未纳入』说法已过时(external_material已入)。"}}
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    out = build(a.date)
    p = ROOT / "data" / "inbox" / f"new_materials_{a.date.replace('-', '')}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    b = p.read_bytes(); json.loads(b.decode())
    print("[inbox_scan] %s → %s · 文件%d · 乱码%d" % (a.date, p.name, out["文件总数"], b.count(b"\xef\xbf\xbd")))
    for k, v in out["各类最新与断流"].items():
        print("  %s: 最新%s · %s" % (k, v.get("最新一份"), v.get("断流告警")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
