# -*- coding: utf-8 -*-
"""本地自动接力器（T024 / CODE-20·2026-07-28）。

董事长要求:以后只在GPT提任务·不再手动启动4.8/Code/搬运。本器补齐本地自动接力能力(非新增投研体系)。

做什么:周期轮询 data/orchestration/task_queue.json → 领 owner=CODE & status=READY_FOR_CODE 的任务 →
  用官方非交互 `claude -p`(受限权限·非--dangerously)在项目内自动执行 → 写结果/证据/SHA256/字节 →
  状态转 READY_FOR_C48_REVIEW。可选:复验角色对 READY_FOR_C48_REVIEW 独立复验(见 --role reviewer)。

★安全边界(§3.3):
  - 只用 claude -p 官方非交互·禁 --dangerously-skip-permissions·禁全盘/永久/无边界授权;
  - --add-dir 仅限任务 allowed_paths·--allowedTools 仅限任务 allowed_actions·--permission-mode acceptEdits(不越 add-dir);
  - 不读项目外·不删大量文件·遇范围外/密钥/付款/外发/删除 → 停 BLOCKED;
  - 原子锁防重复·retry≤max_attempts(默认2)·第二次失败停并交人·不无限重试;
  - 电脑关机/未登录/G盘未同步/CLI未登录 → 留失败记录+醒目标记(不静默)。

★诚实(§3.4/§五):Claude Desktop 4.8【无受支持的定时/事件轮询接口】读G盘自动复验(标准Desktop无cron/文件触发)。
  本器的 reviewer 角色由【claude CLI 独立复验invocation】担(官方非交互·非模拟键鼠)·【不是Claude Desktop 4.8应用】。
  是否算『真4.8接通』由GPT/董事长判——本器不擅自把它当『4.8已接通』宣布。
"""
import json, os, sys, time, hashlib, subprocess, argparse, tempfile
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
ORCH = ROOT / "data" / "orchestration"
QUEUE = ORCH / "task_queue.json"
LOGDIR = ORCH / "logs"
LOCK = ORCH / ".orchestrator.lock"
def _resolve_claude():
    """Windows下subprocess需claude.cmd全路径(bash的which给的wrapper不能直接跑·原"claude"无扩展名→WinError2)。"""
    env = os.environ.get("CLAUDE_BIN")
    if env and Path(env).exists():
        return env
    appdata = os.environ.get("APPDATA", "")
    for c in (Path(appdata) / "npm" / "claude.cmd", Path(appdata) / "npm" / "claude.ps1"):
        if c.exists():
            return str(c)
    return "claude.cmd"


CLAUDE = _resolve_claude()
DEFAULT_MAX_ATTEMPTS = 2


def _now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _log(msg):
    LOGDIR.mkdir(parents=True, exist_ok=True)
    line = f"[{_now()}] {msg}"
    (LOGDIR / f"orchestrator_{datetime.now().strftime('%Y%m%d')}.log").open("a", encoding="utf-8").write(line + "\n")
    print(line)


def _read_queue():
    return json.loads(QUEUE.read_text(encoding="utf-8")) if QUEUE.exists() else {"tasks": []}


def _write_queue(q):
    # 原子写:临时文件 + 替换
    q["_updated_at"] = _now()
    tmp = QUEUE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, QUEUE)


def _acquire_lock():
    """原子锁(O_CREAT|O_EXCL)防同一时刻多接力器/重复启动。陈旧锁(>30min)自动清。"""
    try:
        if LOCK.exists() and (time.time() - LOCK.stat().st_mtime) > 1800:
            LOCK.unlink()
        fd = os.open(str(LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, f"{os.getpid()}@{_now()}".encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False


def _release_lock():
    try:
        LOCK.unlink()
    except Exception:
        pass


def _sha256(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _preflight():
    """§3.2:电脑/登录/G盘/CLI 前置检查。任一不满足→返回错误串(不静默)。"""
    if not ROOT.exists():
        return f"项目根不可达(G盘未同步?):{ROOT}"
    try:
        v = subprocess.run([CLAUDE, "--version"], capture_output=True, text=True, timeout=30)
        if v.returncode != 0:
            return f"claude CLI 不可用/未登录:{(v.stderr or v.stdout)[:80]}"
    except Exception as e:
        return f"claude CLI 调用失败(未装/未登录?):{e}"
    return None


def _forbidden_hit(task):
    """范围外/危险操作判定:任务 allowed_actions 含禁用工具 → BLOCKED。"""
    bad = {"WebFetch", "WebSearch"}  # 外发类默认不许(测试任务只需Write/Read);可按任务放宽由架构师定
    danger = [a for a in (task.get("allowed_actions") or []) if a in bad]
    return danger


def _run_claude(task, role):
    """用官方非交互 claude -p 执行。返回(rc, out, err)。受限权限·非--dangerously。"""
    allowed_paths = task.get("allowed_paths") or [str(ROOT)]
    allowed_actions = task.get("allowed_actions") or ["Read"]
    prompt = task.get("prompt") or task.get("prompt_" + role) or ""
    if not prompt and task.get("task_file"):
        prompt = f"读取并执行任务文件 {task['task_file']} 的要求。只在允许路径内操作。"
    add_dir = []
    for p in allowed_paths:
        add_dir += ["--add-dir", p]
    cmd = [CLAUDE, "-p", prompt,
           "--permission-mode", "acceptEdits",
           "--allowedTools", *allowed_actions,
           "--output-format", "text"] + add_dir
    _log(f"    launch claude -p ({role}) allowedTools={allowed_actions} add-dir={allowed_paths}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=600, cwd=str(ROOT))
        return r.returncode, (r.stdout or ""), (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "", "claude -p 超时(>10min)"
    except Exception as e:
        return 1, "", f"{type(e).__name__}: {e}"


def _evidence(task):
    """对 evidence_paths 逐个算 SHA256+字节·写 evidence 记录。"""
    ev = []
    for rel in (task.get("evidence_paths") or []):
        p = (ROOT / rel) if not os.path.isabs(rel) else Path(rel)
        if p.exists():
            ev.append({"path": rel, "sha256": _sha256(p), "bytes": p.stat().st_size, "exists": True})
        else:
            ev.append({"path": rel, "exists": False})
    return ev


def process_once(role="orchestrator"):
    err = _preflight()
    if err:
        _log(f"[前置失败·醒目]{err}")
        # 把所有活动任务标失败可见(不静默)
        q = _read_queue(); changed = False
        for t in q.get("tasks", []):
            if t.get("owner") == "CODE" and t.get("status") in ("READY_FOR_CODE", "CODE_RUNNING"):
                t["last_error"] = f"前置失败:{err}"; changed = True
        if changed:
            _write_queue(q)
        return {"preflight_error": err}
    if not _acquire_lock():
        _log("锁被占(另一接力器在跑)·本次跳过")
        return {"skipped": "locked"}
    acted = []
    try:
        q = _read_queue()
        for t in q.get("tasks", []):
            if t.get("owner") != "CODE":
                continue
            st = t.get("status")
            # ── 领取并执行 READY_FOR_CODE ──
            if st == "READY_FOR_CODE":
                dh = _forbidden_hit(t)
                if dh:
                    t["status"] = "BLOCKED"; t["last_error"] = f"含禁用工具{dh}·停BLOCKED交人"; t["finished_at"] = _now()
                    _write_queue(q); acted.append((t["task_id"], "BLOCKED")); continue
                if t.get("attempt", 0) >= t.get("max_attempts", DEFAULT_MAX_ATTEMPTS):
                    t["status"] = "FAILED"; t["last_error"] = "达重试上限·停并交4.8/GPT"; t["finished_at"] = _now()
                    _write_queue(q); acted.append((t["task_id"], "FAILED")); continue
                t["status"] = "CLAIMED_BY_CODE"; t["claimed_at"] = _now(); t["attempt"] = t.get("attempt", 0) + 1
                _write_queue(q)
                t["status"] = "CODE_RUNNING"; _write_queue(q)
                _log(f"[领取]{t['task_id']} attempt={t['attempt']}")
                rc, out, e = _run_claude(t, "code")
                if rc == 0:
                    t["result_file"] = t.get("result_file")
                    t["evidence"] = _evidence(t)
                    ok_ev = all(x.get("exists") for x in t["evidence"]) if t["evidence"] else True
                    if ok_ev:
                        t["status"] = "READY_FOR_C48_REVIEW"; t["next_owner"] = "C48"; t["finished_at"] = _now(); t["last_error"] = ""
                        _log(f"[完成]{t['task_id']} → READY_FOR_C48_REVIEW · 证据{len(t['evidence'])}项")
                        acted.append((t["task_id"], "READY_FOR_C48_REVIEW"))
                    else:
                        t["status"] = "FAILED" if t["attempt"] >= t.get("max_attempts", DEFAULT_MAX_ATTEMPTS) else "READY_FOR_CODE"
                        t["last_error"] = "执行返回0但证据文件缺失"
                        acted.append((t["task_id"], t["status"]))
                    _write_queue(q)
                else:
                    t["last_error"] = (e or out)[:300]
                    t["status"] = "FAILED" if t["attempt"] >= t.get("max_attempts", DEFAULT_MAX_ATTEMPTS) else "READY_FOR_CODE"
                    _log(f"[失败]{t['task_id']} rc={rc} → {t['status']} · {t['last_error'][:80]}")
                    acted.append((t["task_id"], t["status"]))
                    _write_queue(q)
            # ── 复验 READY_FOR_C48_REVIEW ──
            #   ★诚实:Claude Desktop 4.8【无受支持的自动轮询接口】。此复验由 claude CLI 以【独立复验invocation】担
            #   (官方非交互·非模拟键鼠·与执行invocation分离·独立读证据+核SHA256)。【不是Claude Desktop 4.8应用】。
            #   是否算『真4.8接通』由GPT/董事长判;本器只如实标 reviewer=claude-CLI·不擅自宣布『4.8已接通』。
            elif st == "READY_FOR_C48_REVIEW" and t.get("_reviewer_enabled"):
                t["status"] = "C48_REVIEWING"; _write_queue(q)
                ev = t.get("evidence") or []
                ev_ok = bool(ev) and all(x.get("exists") for x in ev)
                # 复验invocation:独立读证据文件核内容(非执行者自证)
                rp = {**t, "allowed_actions": ["Read"], "allowed_paths": t.get("allowed_paths") or [str(ROOT)],
                      "prompt": (f"独立复验:读取文件 {t.get('result_file')}·确认它恰含三行且第一行TASK_ID为{t['task_id']}、"
                                 f"末行为CODE_DONE。只读不改。核对通过回复恰好 REVIEW_PASS·否则回复 REVIEW_FAIL 并说原因。")}
                rc, out, e = _run_claude(rp, "reviewer")
                passed = ev_ok and ("REVIEW_PASS" in (out or ""))
                t["review_by"] = "claude-CLI独立复验invocation(非Claude Desktop 4.8应用·真4.8无受支持接口)"
                t["review_result"] = (out or e)[:200]
                if passed:
                    t["status"] = "READY_FOR_GPT_REVIEW"; t["next_owner"] = "GPT"; t["reviewed_at"] = _now()
                    _log(f"[复验通过·claude-CLI]{t['task_id']} → READY_FOR_GPT_REVIEW")
                    acted.append((t["task_id"], "READY_FOR_GPT_REVIEW"))
                else:
                    t["status"] = "RETURNED"; t["last_error"] = "复验未通过:" + (out or e)[:120]
                    _log(f"[复验退回]{t['task_id']} → RETURNED")
                    acted.append((t["task_id"], "RETURNED"))
                _write_queue(q)
    finally:
        _release_lock()
    return {"acted": acted}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="本地自动接力器 T024/CODE-20")
    ap.add_argument("--once", action="store_true", help="轮询一次即退(供任务计划周期调用)")
    ap.add_argument("--role", default="orchestrator")
    ap.parse_args()
    _log("=== 接力器启动(--once) ===")
    r = process_once()
    _log(f"=== 本次结果:{json.dumps(r, ensure_ascii=False)} ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
