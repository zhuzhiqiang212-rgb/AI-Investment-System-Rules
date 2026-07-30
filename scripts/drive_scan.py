# -*- coding: utf-8 -*-
"""④(38号续)·全 Drive 根目录扫描闸。扫 G:\\我的云端硬盘 全部顶层文件夹(递归·近14天)·防『我没有数据』再发生。
输出 data/logs/drive_scan_{date}.json:近14天新增/修改全部文件(路径/修改时间/扩展/可读性)+ 未消化清单 + 每条标 已读/未读/为何不读。
Code 只发现与登记·不做投资判断。"""
import os, json, time, pathlib, argparse
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9))
ROOT = pathlib.Path(__file__).resolve().parent.parent
DRIVE = pathlib.Path("G:/我的云端硬盘")
READ = {".pdf", ".md", ".txt", ".csv", ".docx", ".pptx", ".xlsx", ".png", ".jpg", ".jpeg"}
UNREAD = {".gdoc", ".gsheet", ".gslides"}
SKIP_TOP = {".claude"}                 # 本机配置·非资料
LIMIT_TO_INBOX = {"AI_Investment_System"}  # 项目本体·只看 inbox(避免扫数千项目文件)

def readability(ext):
    if ext in READ: return "可读"
    if ext in UNREAD: return "不可读(云端指针·需董事长导出)"
    return "格式未知·需人工确认"

def load_ledger():
    p = ROOT / "data" / "inbox" / "digest_ledger.json"
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            return {r["file"]: r for r in (d if isinstance(d, list) else d.get("entries", []))}
        except Exception: pass
    return {}

def build(date, days=14, cap=600):
    cutoff = time.time() - days * 86400
    ledger = load_ledger()
    tops = []
    found = []
    n = 0
    for top in sorted(DRIVE.iterdir(), key=lambda p: p.name):
        try:
            if not top.is_dir():
                tops.append({"名": top.name, "类型": "文件"}); continue
        except Exception:
            continue
        if top.name in SKIP_TOP:
            tops.append({"名": top.name, "扫描": "跳过(本机配置)"}); continue
        base = top / "inbox" if top.name in LIMIT_TO_INBOX else top
        cnt = 0
        try:
            for p in base.rglob("*"):
                if n >= cap: break
                try:
                    if not p.is_file(): continue
                    st = p.stat()
                    if st.st_mtime >= cutoff:
                        ext = p.suffix.lower()
                        rel = str(p)
                        digested = ledger.get(rel, {}).get("digested", False)
                        used = ledger.get(rel, {}).get("used_in", "")
                        found.append({
                            "路径": rel, "修改时间": datetime.fromtimestamp(st.st_mtime, JST).strftime("%Y-%m-%d %H:%M"),
                            "扩展名": ext or "(无)", "可读性": readability(ext), "字节": st.st_size,
                            "顶层": top.name,
                            "消化状态": ("已读" if digested else ("未读·" + ("不可读(云端指针)" if ext in UNREAD else "尚未纳入产品/底稿"))),
                            "用于": used or "(未使用)"})
                        cnt += 1; n += 1
                except Exception: continue
        except Exception as e:
            tops.append({"名": top.name, "扫描": "失败:%s" % str(e)[:40]}); continue
        tops.append({"名": top.name, "扫描根": ("inbox" if top.name in LIMIT_TO_INBOX else "整个文件夹递归"), "近%d天文件数" % days: cnt})
    found.sort(key=lambda x: x["修改时间"], reverse=True)
    undigested = [f for f in found if f["消化状态"].startswith("未读")]
    return {
        "_说明": "全Drive根目录扫描·近%d天·Code只发现登记不做判断" % days,
        "date": date, "扫描时刻": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"),
        "扫描根": str(DRIVE), "顶层清单(无遗漏)": tops,
        "近%d天新增/修改总数" % days: len(found), "达上限截断": n >= cap,
        "未消化清单(产品第一层须显示)": undigested,
        "全部近14天文件": found,
        "硬闸": {"清单是否产出": True, "说明": "产品第一层必须显示『今天Drive有几份新资料·读了几份·没读的是哪些·为什么』·此清单缺失→产品判FAIL"},
    }

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--date", default=datetime.now(JST).strftime("%Y%m%d")); a = ap.parse_args()
    res = build(a.date)
    out = ROOT / "data" / "logs" / f"drive_scan_{a.date}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print("drive_scan %s → %s" % (a.date, out.name))
    print("顶层文件夹(无遗漏):")
    for t in res["顶层清单(无遗漏)"]:
        print("  ", t)
    print("近14天新增/修改:", res["近14天新增/修改总数"], "· 未消化:", len(res["未消化清单(产品第一层须显示)"]))
    for f in res["未消化清单(产品第一层须显示)"][:12]:
        print("   未读:", f["路径"].split("我的云端硬盘")[-1], "|", f["可读性"])
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
