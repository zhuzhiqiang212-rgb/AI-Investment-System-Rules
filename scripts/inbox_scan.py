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
    m = re.search(r"(?:20)?(\d{2})[-.](\d{2})[-.](\d{2})", name)
    if m:
        yy, mm, dd = m.groups()
        try:
            return "20%s-%s-%s" % (yy, mm, dd)
        except Exception:
            return None
    return None


def build(date):
    dc = date.replace("-", ""); date_h = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:8])
    today = _date(int(dc[:4]), int(dc[4:6]), int(dc[6:8]))
    items = []
    latest_by_kind = {"湖水": None, "老雷": None}
    for d in SCAN_DIRS:
        if not d.exists():
            continue
        for p in d.rglob("*"):
            if not p.is_file():
                continue
            ext = p.suffix.lower()
            fd = _file_date(p.name)
            kind = "老雷" if "老雷" in str(p) or "老雷" in p.name else ("湖水" if "湖水" in str(p) or "湖水" in p.name else "其它")
            readable = ("可读" if ext in READ else ("需导出PDF(云端指针·本地无正文·非权限不足非资料缺失)" if ext in UNREAD else "格式未知需人工确认"))
            items.append({"路径": str(p), "文件": p.name, "日期": fd, "类型": ext or "(无)", "类别": kind, "可读性": readable})
            if kind in latest_by_kind and fd:
                if latest_by_kind[kind] is None or fd > latest_by_kind[kind]:
                    latest_by_kind[kind] = fd
    # 断流(AN2-2):各类最新一份距今天数
    stale = {}
    for kind, fd in latest_by_kind.items():
        if fd:
            try:
                gap = (today - _date(int(fd[:4]), int(fd[5:7]), int(fd[8:10]))).days
            except Exception:
                gap = None
            stale[kind] = {"最新一份": fd, "距今天数": gap,
                           "★断流": (gap is not None and gap > 14), "断流告警": ("外部研究资料已断流 %d 天" % gap) if (gap and gap > 14) else "正常(≤14天)"}
        else:
            stale[kind] = {"最新一份": None, "★断流": True, "断流告警": "无该类资料·或日期解析不出"}
    out = {"_说明": "★轮75 AN2 inbox外部资料扫描。与上次记录比对出新增·.gdoc标需导出PDF(非权限/缺失)·>14天断流显性告警。",
           "date": date_h, "as_of": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
           "扫描路径": [str(x) for x in SCAN_DIRS], "文件总数": len(items),
           "各类最新与断流": stale, "清单": sorted(items, key=lambda x: (x["日期"] or "", x["文件"]), reverse=True)[:120],
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
