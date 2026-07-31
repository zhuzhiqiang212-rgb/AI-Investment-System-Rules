# -*- coding: utf-8 -*-
"""CODE-24 无人触发验证：由 Windows 计划任务自动起来调用真实 Opus 5(claude-opus-5)。
证明 scheduler → claude --model claude-opus-5 无人链路成立。不手动 /run。"""
import subprocess, json, time, os

ROOT = r"G:\我的云端硬盘\AI_Investment_System"
OUT = os.path.join(ROOT, r"data\logs\opus5_scheduled_result_20260729.json")
claude = os.path.join(os.environ.get("APPDATA", ""), "npm", "claude.cmd")
started = time.strftime("%Y-%m-%dT%H:%M:%S+09:00")
rec = {"触发方式": "Windows计划任务自动firing(非手动/run)", "started_at": started, "claude_cmd": claude}
try:
    r = subprocess.run([claude, "--model", "claude-opus-5", "-p",
                        "只回复一个词:SCHEDULED_OPUS5", "--output-format", "json"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       stdin=subprocess.DEVNULL, timeout=120)
    rec["rc"] = r.returncode
    try:
        d = json.loads(r.stdout)
        mu = d.get("modelUsage", {})
        rec["modelUsage_keys"] = list(mu.keys())
        rec["opus5_present"] = "claude-opus-5" in mu
        rec["opus5_主推理"] = (mu.get("claude-opus-5", {}).get("inputTokens", 0) >
                            max([v.get("inputTokens", 0) for k, v in mu.items() if k != "claude-opus-5"] + [0]))
        rec["result"] = d.get("result")
        rec["is_error"] = d.get("is_error")
        rec["raw_result_json"] = r.stdout
    except Exception as e:
        rec["parse_error"] = str(e); rec["raw_stdout"] = r.stdout[:2000]; rec["raw_stderr"] = r.stderr[:1000]
except Exception as e:
    rec["exception"] = str(e)
rec["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S+09:00")
open(OUT, "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False, indent=2))
