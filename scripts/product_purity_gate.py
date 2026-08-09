# -*- coding: utf-8 -*-
"""★★★轮185 正式目录纯净度闸(★内容判据版·不靠文件名)——承 CLAUDE.md §5.4：判据要结构化·不靠名字猜。
轮184靠文件名前缀(★每日产品*/★正式产品*)会永远漏老命名(完整产品_20260720=真产品·漏了)。本版改【内容特征】。

★【产品】结构化判据(5条·董事长轮185建议·Code校准后采用):
  C1 持仓标的清单(≥5只带代码 [A-Z]{2}.xxx)   ← ★锚:尺/样稿/计划都C1=0(讨论产品但无真持仓)·真产品C1≥5
  C2 买卖/持有动作字样(买入/卖出/减仓/加仓/换仓/退出/不动/持有)
  C3 页头(run_id R-YYYYMMDD-HHMMSS 或 data_date/数据日/生成时间)
  C4 产品专有小节(今天做什么/逐只判断/第一屏/今天发生/对你的钱/机器状态)
  C5 标题含 决策台/日报/每日投资/每日产品

★★判定(Code校准·与董事长原"任意2条"的出入见回报):
  · 确定产品(move) = C1(≥5持仓) AND (C5决策台 OR C4产品小节 OR run_id) ——★真持仓+明确产品结构·高置信
  · 判不准(不动·列给董事长) = C1≥5 但无(C5/C4/run_id) ——真持仓但无明确产品结构(可能产品变体或研究附件)·★宁可漏移不误移
  · 非产品(保留) = C1<5(无真持仓清单) → 按标题标记归 尺/样稿/计划/说明/其他 ——★尺C1=0·永不误移
  ★董事长点名产品(轮185)override→确定产品;★综合底稿_机器版_*→draft(董事长C裁定·含真持仓移data/products/draft/)。

★对确定产品且 release_status!=released:加追溯横幅+移到 data/products/self_test/(不删不回滚·不改正文·bytes保CRLF)。"""
import sys, json, re, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
ZHENG = ROOT / "00_请先看这里"
ST_DIR = ROOT / "data" / "products" / "self_test"
DRAFT_DIR = ROOT / "data" / "products" / "draft"
RUNID_RE = re.compile(r"R3?-20\d{6}-\d{6}")
# 不扫:主控/开工必读/状态说明(基础设施·非产品)
SKIP = {"★开工必读_主控文件.html", "00_当前无正式产品_说明.html", "文件索引.html", "0_最新交付_从这里看.html"}
# 董事长轮185点名的产品(即便无C4/C5也移)
NAMED_PRODUCTS = ("完整产品_20260720", "完整产品_20260715_机器版", "完整产品_20260715_深度版")


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _signals(html):
    tickers = set(re.findall(r"[A-Z]{2}\.[A-Z0-9]{2,6}", html))
    return {
        "ticker数": len(tickers),
        "C1持仓≥5": len(tickers) >= 5,
        "C2动作": bool(re.search(r"买入|卖出|减仓|加仓|换仓|退出|不动|持有", html)),
        "C3页头": bool(RUNID_RE.search(html)) or bool(re.search(r"data_date|数据日|生成时间|生成于|生产于", html)),
        "C3_run_id": bool(RUNID_RE.search(html)),
        "C4产品小节": [s for s in ["今天做什么", "逐只判断", "第一屏", "今天发生", "对你的钱", "机器状态"] if s in html],
        "C5决策台标题": bool(re.search(r"决策台|日报|每日投资|每日产品", html[:3000])),
    }


def _marker_category(name):
    """治理文档类型标记(尺/样稿/计划/说明)。★用于KEEP(只会保留·永不误移)——先于判不准判·防obvious尺/报告混入判不准。"""
    if re.search(r"标准|验收|规范|框架|准绳|方法学|机制|口径|判据|筛选规则|世界观|战略地图|板块地图|资金流动完整|资金流动层|持仓完整档案|总纲|自律|护城河分析|基本面质量|催化剂库|目标倒推|机会发现规范|预测优先|层间传导|复盘记分卡层设计|完工验收清单|生产流程|风险配仓|七步定义|Release_Gate|Opus5被机器约束|产品形态四要素", name):
        return "尺"
    if re.search(r"定样|样式|样稿|深度样|深度标准|模板卡|样板|骨架模板|成品级深度样", name):
        return "样稿"
    if re.search(r"执行计划|统一问题清单|完整设计方案|设计方案|工作计划|生产任务清单|问题清单|呈现升级|正式施工指令|生成架构设计", name):
        return "计划"
    if re.search(r"说明|报告|复盘|裁定|交接|看板|指令|核查|证据|探针|对账|小结|进度|意见|映射与核验|完工报告|数据能力|复验|独立验收|架构师|盲区|硬检查|统一整改|转发指令|线程|给Code的指令|派工单|新线程|Cowork|职责|手册|片段|能力对照|质量关补数|根本问题", name):
        return "说明/其他"
    return None


def _classify(name, html):
    s = _signals(html)
    hits = [k for k in ["C1持仓≥5", "C2动作", "C3页头", "C4产品小节", "C5决策台标题"] if s[k]]
    stem = name
    if name.startswith("综合底稿_机器版"):
        return "产品底稿", s, hits, "draft", "含真实持仓数据(C1=%d)·董事长C裁定→移draft(本就不声称产品)" % s["ticker数"]
    if any(stem.startswith(n) for n in NAMED_PRODUCTS):
        return "产品", s, hits, "self_test", "★董事长轮185点名产品(持仓%d只)" % s["ticker数"]
    if s["C1持仓≥5"] and (s["C5决策台标题"] or s["C4产品小节"] or s["C3_run_id"]):
        return "产品", s, hits, "self_test", "持仓≥5 + (决策台/产品小节/run_id)·高置信产品"
    # ★治理文档标记(尺/样稿/计划/说明)→ 保留(只会keep·永不误移·先于判不准)
    mc = _marker_category(stem)
    if mc:
        return mc, s, hits, "保留", ("C1=%d但文件是%s类治理文档(标记明确)·保留" % (s["ticker数"], mc)) if s["C1持仓≥5"] else "C1<5·%s类·保留" % mc
    # ★C1≥5 且无产品结构 且无治理标记 → 判不准(真正模糊·列给董事长·宁可漏移不误移)
    if s["C1持仓≥5"]:
        return "判不准(待董事长裁)", s, hits, "不动·列给董事长", "持仓%d只·无决策台/产品小节/run_id·无治理标记·真正模糊·★不擅自移" % s["ticker数"]
    return "其他", s, hits, "保留", "C1<5(无真持仓清单)·无明确标记·其他"


def _released_status(date, run_id):
    if not run_id or not date:
        return "无run_id→无法核released→按非released"
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import release_gate as rg
        return rg.evaluate(date.replace("-", ""), run_id, log=False)["★release_status"]
    except Exception as e:
        return "评估失败(%s)→按非released" % type(e).__name__


def _date_of(name, html):
    m = re.search(r"(20\d{2})-?(\d{2})-?(\d{2})", name)
    if m:
        return "%s-%s-%s" % (m.group(1), m.group(2), m.group(3))
    m = RUNID_RE.search(html or "")
    if m:
        d = m.group(0).split("-")[1]
        return "%s-%s-%s" % (d[:4], d[4:6], d[6:8])
    return None


def _banner(date, status):
    return ('<div style="background:#7a1414;color:#ffdede;padding:14px 18px;font-size:18px;font-weight:900;'
            'text-align:center;border-bottom:4px solid #d24b4b">★★整改自测件 · 未过 GPT 终验 · 非正式产品（追溯定性）'
            '<br><span style="font-size:13px;font-weight:600">★本产品生产于 %s · 于 2026-08-05 按 INST-RELEASE-GATE 追溯定性（release_status=%s）·仅供内部核对</span></div>'
            % (date, status)).encode("utf-8")


def scan(move=True):
    ST_DIR.mkdir(parents=True, exist_ok=True)
    DRAFT_DIR.mkdir(parents=True, exist_ok=True)
    rows, moved, undecided = [], [], []
    for p in sorted(ZHENG.glob("*.html")):
        if p.name in SKIP:
            continue
        try:
            html = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        cat, s, hits, action, why = _classify(p.name, html)
        date = _date_of(p.name, html)
        rec = {"文件": p.name, "判定": cat, "命中判据": hits, "ticker数": s["ticker数"], "动作": action, "依据": why, "date": date}
        if cat in ("产品", "产品底稿"):
            run_id = (RUNID_RE.search(html).group(0) if RUNID_RE.search(html) else None)
            status = _released_status(date, run_id) if cat == "产品" else "draft(不声称产品)"
            rec["release_status"] = status
            if cat == "产品" and status == "released":
                rec["动作"] = "保留(已released)"
            elif not move:
                # ★★★轮297 董事长裁定:取消auto-move。未released只告警、不移动、不加横幅、不删。
                rec["动作"] = "★告警:release_status=%s(未released)·轮297裁定仅标注不移动·产品留在正式目录" % status
            else:
                # ★仅当显式 --move 才移动(轮297默认关·保留能力供特殊需要)
                tgt = ST_DIR if cat == "产品" else DRAFT_DIR
                raw = p.read_bytes()
                if cat == "产品" and b"<body" in raw and "追溯定性".encode() not in raw:
                    raw = re.sub(rb"<body[^>]*>", lambda m: m.group(0) + _banner(date, status), raw, count=1)
                suffix = "_追溯自测件" if cat == "产品" else "_底稿"
                dst = tgt / (p.stem + suffix + p.suffix)
                dst.write_bytes(raw)
                p.unlink()
                rec["已移到"] = str(dst.relative_to(ROOT)).replace("\\", "/")
                moved.append(rec["已移到"])
        elif cat.startswith("判不准"):
            undecided.append(rec)
        rows.append(rec)
    return {"rows": rows, "moved": moved, "undecided": undecided}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="正式目录纯净度闸(内容判据·轮185)")
    ap.add_argument("--date", default=None)
    ap.add_argument("--scan-only", action="store_true")
    ap.add_argument("--move", action="store_true", help="★轮297:显式才移动。默认(daily调用)=只告警不移动，董事长裁定取消auto-move。")
    ap.add_argument("--dump", default=None, help="逐份判定表输出json路径")
    a = ap.parse_args()
    # ★★★轮297 董事长裁定(2026-08-08):取消 auto-move。默认只告警不移动·仅 --move 显式启用移动能力(保留不删)。
    res = scan(move=(a.move and not a.scan_only))
    from collections import Counter
    cnt = Counter(r["判定"] for r in res["rows"])
    print("[纯净度闸·内容判据] 扫 %d 份 · 分类 %s · 移出 %d · 判不准 %d" % (
        len(res["rows"]), dict(cnt), len(res["moved"]), len(res["undecided"])))
    for r in res["rows"]:
        if r["判定"] in ("产品", "产品底稿") or r["判定"].startswith("判不准"):
            print("  [%s] %-40s 命中%s ticker%d → %s" % (r["判定"][:6], r["文件"][:40], r["命中判据"], r["ticker数"], r.get("已移到", r["动作"])))
    if a.dump:
        Path(a.dump).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        print("  逐份判定表 →", a.dump)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
