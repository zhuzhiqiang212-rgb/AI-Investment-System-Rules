# -*- coding: utf-8 -*-
"""★★★轮180 Release Gate(制度ID INST-RELEASE-GATE·v1)——GPT V6总控裁定2026-08-04第六节【程序化】。

★立法依据(非Code主意):GPT V6裁定原话「真正的问题不是有人不知道制度·而是即使知道仍可能绕过终验·所以必须由机器阻止」。
★触发事实:Opus5两次跳过GPT终验(初验完直接交董事长/验收完自行决定下一步)——立规者第一个不守。
★结论:靠自觉的约束=没有约束。约束必须落机器·且不能由【被约束者】自己解除。

★正式发布唯一合法路径:开发完成→Deployment Audit→GPT Final Review→【Release Gate】→允许生成正式PDF→进正式目录→交董事长。

★判定基于【结构化字段】(承CLAUDE.md §5.4·不得靠自由文本关键词):
   data/review/gpt_final_review_{YYYYMMDD}.json:review_date/target_run_id/verdict/reviewer/nine_criteria/blocking_items/issued_at。

六道判定(任一不过=拦停·不得生成PDF·不得进正式目录):
   R1 终验章存在
   R2 target_run_id == 待发布产品run_id(防拿昨天的章盖今天的产品)
   R3 issued_at 晚于产品run_id时间(防事后补章)
   R4 verdict == PASS(PARTIAL/FAIL一律拦停)
   R5 ★reviewer == GPT_V6(★★被约束者不得签发解除自己约束的凭证)
   R6 blocking_items 为空

★★R5核心:若reviewer∈{OPUS_5,CLAUDE_4_8,CODE}或任何非GPT_V6→不但拦停·还在台账记【疑似自签越权】。
   ★这一条防的就是Opus5自己写个章放行自己。

三态 release_status:released(全过)/ self_test(无终验章·未过闸=整改自测件)/ blocked(有章但不合规:自签越权/FAIL/run_id不符/补章)。
"""
import sys, json, argparse, hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
REVIEW_DIR = ROOT / "data" / "review"
GATE_LOG = ROOT / "data" / "logs" / "release_gate_log.json"

VALID_VERDICTS = {"PASS", "PARTIAL", "FAIL"}
GPT_REVIEWER = "GPT_V6"
CONSTRAINED_REVIEWERS = {"OPUS_5", "CLAUDE_4_8", "CODE", "CLAUDE_CODE", "FABLE_5", "CLAUDE_CLI"}  # 被约束者·不得自签放行自己


def _rj(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d if d is not None else {}


def _runid_epoch(dc, run_id):
    """产品run_id的真实生成epoch:优先runid_history边车(真epoch)·回退解析 R-YYYYMMDD-HHMMSS。"""
    if not run_id:
        return None
    h = _rj(ROOT / "data" / "logs" / f"runid_history_{dc}.json")
    ep = (h.get("epochs") or {}).get(run_id)
    if ep:
        return int(ep)
    try:
        _, d, hms = run_id.split("-")   # R, YYYYMMDD, HHMMSS
        dt = datetime(int(d[:4]), int(d[4:6]), int(d[6:8]), int(hms[:2]), int(hms[2:4]), int(hms[4:6]), tzinfo=JST)
        return int(dt.timestamp())
    except Exception:
        return None


def _iso_epoch(iso):
    if not iso:
        return None
    try:
        return int(datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp())
    except Exception:
        return None


def _write_gate_log(events):
    """★轮182 A-3:台账写盘唯一入口·【严格追加·不静默截断·不丢事件】。保留is_test结构。"""
    GATE_LOG.parent.mkdir(parents=True, exist_ok=True)
    GATE_LOG.write_text(json.dumps({
        "_说明": "Release Gate 治理台账(轮180建·轮181加R7·★★只增不改)。★is_test=true为测试事件(查询可过滤·但永久保留)·false为真实治理事件。"
                 "★轮181曾违规清空·轮182已补录并加防清空保护(--purge须--confirm-chairman且留清理事件)。",
        "制度ID": "INST-RELEASE-GATE", "n": len(events),
        "真实事件数": sum(1 for e in events if not e.get("is_test")),
        "测试事件数": sum(1 for e in events if e.get("is_test")),
        "events": events},   # ★不截断(治理事件不可丢·只增不改)
        ensure_ascii=False, indent=2), encoding="utf-8")


def _log_gate(rec, is_test=False):
    """Release Gate 专用台账(★只增不改·A-3不静默截断)。自签越权等治理事件在此留痕。"""
    hist = _rj(GATE_LOG, {}).get("events", []) if GATE_LOG.exists() else []
    rec = dict(rec); rec.setdefault("is_test", is_test)
    hist.append(rec)
    _write_gate_log(hist)


def evaluate(date, product_run_id, log=True, is_test=False):
    """对(date, 待发布产品run_id)判定是否可发布。返回结构化判定+release_status+自签越权标记。
    ★is_test:测试调用标True→台账记is_test(轮181教训:测试事件也永久留痕·标记而非事后删)。"""
    dc = str(date).replace("-", "")
    rv = _rj(REVIEW_DIR / f"gpt_final_review_{dc}.json")
    reviewer = rv.get("reviewer") if rv else None
    verdict = rv.get("verdict") if rv else None
    blocking = rv.get("blocking_items") if rv else None

    # ── R5 先算(供自签越权检测·独立于其它闸) ──
    r5 = (reviewer == GPT_REVIEWER)
    self_sign = None
    if rv and not r5:
        if reviewer in CONSTRAINED_REVIEWERS:
            self_sign = ("★★★疑似自签越权:reviewer=%s(被约束者)签发放行章·而放行权仅GPT_V6。"
                         "★被约束者不得签发解除自己约束的凭证(R5)。" % reviewer)
        else:
            self_sign = "reviewer非法值=%s(须固定GPT_V6)·拒绝作为发布依据" % reviewer

    # ── ★★★轮181 R7:誊写溯源(Opus5自己找出的漏洞)——R5只验reviewer字段的【值】·验不了「这段话真的是谁说的」。
    #   GPT V6是对话模型→给的是文本裁定→须有人【誊写】成json→若誊写人是Opus5·可写reviewer:"GPT_V6"而内容自编·R5照放。
    #   ★誊写≠签发:transcribed_by允许OPUS_5(誊写不越权)·但reviewer仍须GPT_V6(R5不变)·★内容真伪由【董事长】确认(chairman_confirmed)。
    #   ★这是整条链唯一的人类锚点·不能也不该自动化。
    tb = rv.get("transcribed_by") if rv else None
    st = rv.get("source_text") if rv else None
    ssha = rv.get("source_sha256") if rv else None
    cc = rv.get("chairman_confirmed") if rv else None
    actual_sha = hashlib.sha256(st.encode("utf-8")).hexdigest() if isinstance(st, str) and st else None
    # A-4:誊写人冒充签发人(transcribed_by == reviewer)→同R5记疑似自签越权(GPT对话模型不可能自己誊写文件)
    if rv and tb and reviewer and (tb == reviewer):
        _imp = "★★★疑似自签越权(誊写冒充):transcribed_by=%s == reviewer=%s——GPT V6是对话模型不可能自誊写文件·此为冒充签发。" % (tb, reviewer)
        self_sign = (self_sign + " | " + _imp) if self_sign else _imp

    # ── 判定(R1-R6 + R7誊写溯源) ──
    pe = _runid_epoch(dc, product_run_id)
    ie = _iso_epoch(rv.get("issued_at")) if rv else None
    checks = {
        "R1_终验章存在": bool(rv),
        "R2_target_run_id匹配待发布产品": bool(rv) and bool(product_run_id) and (rv.get("target_run_id") == product_run_id),
        "R3_issued_at晚于产品run_id时间": bool(pe and ie and ie > pe),
        "R4_verdict是PASS": (verdict == "PASS"),
        "R5_reviewer是GPT_V6(防自签越权)": r5,
        "R6_blocking_items为空": bool(rv) and (not blocking),
        # ★R7 誊写溯源四条(缺一即拦停)
        "R7a_transcribed_by填写(谁誊写)": bool(tb),
        "R7b_source_text原文≥200字符(防塞个PASS)": bool(st) and (len(str(st)) > 200),
        "R7c_source_sha256与原文实算一致(防事后改原文)": bool(ssha) and bool(actual_sha) and (str(ssha) == actual_sha),
        "R7d_chairman_confirmed(★唯一人类锚点)": (cc is True),
    }
    # verdict 合法性(枚举·非三选一即视为无效章)
    verdict_valid = verdict in VALID_VERDICTS
    all_pass = all(checks.values()) and verdict_valid

    # ── 三态 ──
    if all_pass:
        status = "released"
    elif not rv:
        status = "self_test"   # 无终验章:未过闸=整改自测件(诚实·非错误)
    else:
        status = "blocked"     # 有章但不合规(自签越权/FAIL/run_id不符/补章/非法verdict)

    fails = [k for k, v in checks.items() if not v]
    if not verdict_valid and rv:
        fails.append("verdict非法(非PASS/PARTIAL/FAIL)")

    result = {
        "制度ID": "INST-RELEASE-GATE", "尺": "正式尺_Release_Gate_v1",
        "date": "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:8]),
        "待发布产品run_id": product_run_id,
        "★release_status": status,
        "★可发布(released)": all_pass,
        "判定(R1-R7·十条)": checks,
        "未过项": fails,
        "★★疑似自签越权": self_sign or "无",
        "★★R7誊写溯源": {"transcribed_by(谁誊写·非reviewer)": tb, "chairman_confirmed(★人类锚点)": cc,
                     "source_text长度": (len(str(st)) if st else 0), "source_sha256一致": (bool(ssha) and str(ssha) == actual_sha),
                     "★誊写≠签发": "transcribed_by允许OPUS_5(誊写不越权)·但内容真伪由董事长chairman_confirmed确认·reviewer仍须GPT_V6"},
        "终验章": {"reviewer": reviewer, "verdict": verdict, "target_run_id": (rv.get("target_run_id") if rv else None),
                 "issued_at": (rv.get("issued_at") if rv else None), "blocking_items": blocking,
                 "transcribed_by": tb, "chairman_confirmed": cc} if rv else "★无终验章(未经GPT Final Review)",
        "判定时刻": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "★动作": ("允许:生成正式PDF·进正式目录·标正式产品·交董事长" if all_pass else
                 "拦停:HTML可留供内部核·★不生成PDF·★不进正式目录作正式产品·★不标正式产品(台账标%s)" % status),
    }
    if log:
        _log_gate({"判定时刻": result["判定时刻"], "date": result["date"], "run_id": product_run_id,
                   "release_status": status, "未过项": fails, "疑似自签越权": self_sign,
                   "reviewer": reviewer, "verdict": verdict,
                   "transcribed_by": tb, "chairman_confirmed": cc}, is_test=is_test)   # ★A-4台账记誊写人·A-1标is_test
    return result


def backfill_runlog():
    """★C:追溯定性历史产品。auto_produce_runs.json 每条OK产品:有合规终验章标released·否则self_test(不删不回滚·仅标)。"""
    rl = ROOT / "data" / "logs" / "auto_produce_runs.json"
    o = _rj(rl)
    runs = o.get("runs", [])
    changed = 0
    for r in runs:
        if r.get("status") != "OK":
            r.setdefault("release_status", "n/a(未出品)")
            continue
        rid = r.get("run_id") or ""
        dc = str(r.get("date") or "").replace("-", "")
        res = evaluate(dc, rid, log=False)
        r["release_status"] = res["★release_status"]
        r["release_追溯"] = "轮180追溯:%s(%s)" % (res["★release_status"], "有合规GPT终验章" if res["★可发布(released)"] else "无合规终验章→整改自测件")
        changed += 1
    o["runs"] = runs
    o["_release_gate追溯"] = "★轮180 Release Gate 追溯:有合规GPT_V6终验章的产品标released·其余self_test(不删不回滚·保留成果·仅定性)。"
    rl.write_text(json.dumps(o, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return changed, [{"date": r.get("date"), "run_id": r.get("run_id"), "release_status": r.get("release_status")} for r in runs if r.get("status") == "OK"][-10:]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Release Gate(INST-RELEASE-GATE·GPT V6裁定程序化)")
    ap.add_argument("--date", default=None)
    ap.add_argument("--run-id", default=None, help="待发布产品run_id(缺省取runid_history最新)")
    ap.add_argument("--backfill", action="store_true", help="C:追溯定性历史产品release_status")
    ap.add_argument("--purge", action="store_true", help="★A-3:清理治理台账(危险)·须同时--confirm-chairman")
    ap.add_argument("--confirm-chairman", action="store_true", help="★A-3:确认董事长已授权清理(缺则拒绝清空)")
    ap.add_argument("--test", action="store_true", help="★A-1:测试调用·台账事件标 is_test=true(不污染真实事件·免事后删)")
    a = ap.parse_args()
    # ★★★A-3 防清空保护:台账不能被静默清空(轮181教训:删记录=删证据·同删文件需签字)
    if a.purge:
        if not a.confirm_chairman:
            print("★★拒绝清理:治理台账「只增不改」·清空须董事长授权。正确用法:--purge --confirm-chairman(缺--confirm-chairman一律拒绝)。")
            return 3
        # ★即便授权清理:也不真删——归档旧台账+新台账留一条「清理事件」(谁清·何时·防静默清空)
        old = _rj(GATE_LOG, {})
        bak = GATE_LOG.with_name("release_gate_log_归档_%s.json" % datetime.now(JST).strftime("%Y%m%d%H%M%S"))
        if GATE_LOG.exists():
            bak.write_text(json.dumps(old, ensure_ascii=False, indent=2), encoding="utf-8")
        _write_gate_log([{"is_test": False, "事件类型": "★台账清理事件(已授权)", "判定时刻": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
                          "授权": "--confirm-chairman", "旧台账归档至": bak.name, "旧事件数": len(old.get("events", [])),
                          "note": "★台账被授权清理·旧台账已归档非删除·此条留痕防静默清空(A-3)。"}])
        print("★台账已(授权)清理:旧台账归档至 %s·新台账留清理事件留痕。" % bak.name)
        return 0
    dc = (a.date or "").replace("-", "")
    if not dc:
        print("★需 --date(或用 --backfill/--purge)")
        return 2
    if a.backfill:
        n, tail = backfill_runlog()
        print("[Release Gate 追溯] 定性 %d 条OK产品·近10条:" % n)
        for t in tail:
            print("  %s · %s · %s" % (t["date"], t["run_id"], t["release_status"]))
        return 0
    rid = a.run_id or (_rj(ROOT / "data" / "logs" / f"runid_history_{dc}.json").get("latest") or "")
    res = evaluate(dc, rid, is_test=a.test)   # ★--test:测试调用·台账标is_test(不污染真实事件)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res["★可发布(released)"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
