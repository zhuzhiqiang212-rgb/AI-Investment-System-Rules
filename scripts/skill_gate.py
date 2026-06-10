# skill_gate.py
# AI投研总控台 V4 Skill 运行时质量门控
# 在所有 dashboard.html 写入操作前调用此函数
# Rule Source: GitHub primary, local fallback until GitHub push/auth is confirmed.

from pathlib import Path
from datetime import datetime, timezone, timedelta
import os
import urllib.request

ROOT = Path(r"G:\我的云端硬盘\AI_Investment_System")
GITHUB_RULE_REPO = "https://github.com/zhuzhiqiang212-rgb/AI-Investment-System-Rules"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/zhuzhiqiang212-rgb/AI-Investment-System-Rules/main/"
RULE_SOURCE_MODE = os.environ.get("AI_RULE_SOURCE_MODE", "github_primary_local_fallback")
RULE_SOURCE_FILES = [
    "rules/user_report_constitution_v1.md",
    "rules/q1_003_decision_evidence_standard_v1.rule",
    "skills/user_report_quality_gate.skill",
    "rules/validation_workflow.rule",
]


def load_rule_source(relative_path: str) -> tuple[str, str]:
    """
    读取规则源。
    默认策略：GitHub primary, local fallback。
    返回 (source, text)，source 为 github / local / missing。
    注意：该函数不修改投资逻辑，只为运行时门控提供规则源状态。
    """
    if RULE_SOURCE_MODE in {"github", "github_primary", "github_primary_local_fallback"}:
        url = GITHUB_RAW_BASE + relative_path.replace("\\", "/")
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                data = resp.read().decode("utf-8", errors="ignore")
            if data.strip():
                return "github", data
        except Exception:
            if RULE_SOURCE_MODE == "github":
                return "missing", ""

    local_path = ROOT / relative_path
    if local_path.exists():
        return "local", local_path.read_text(encoding="utf-8-sig", errors="ignore")
    return "missing", ""


def rule_source_status() -> dict[str, str]:
    """返回每个关键规则文件当前从 GitHub 还是本地 fallback 读取。"""
    return {rel: load_rule_source(rel)[0] for rel in RULE_SOURCE_FILES}


def skill_gate(report_path: Path) -> tuple[bool, list[str]]:
    """
    执行 Skill 硬阻断检查。
    返回 (True, []) 表示 PASS，允许写入。
    返回 (False, [原因列表]) 表示 FAIL，必须阻断写入。
    """
    failures = []

    # 规则源状态检查：GitHub 为主，本地为降级保护。
    # 当前不把 local fallback 作为硬阻断，避免 GitHub 凭据/网络短暂失败导致本地日报流程完全不可诊断。
    sources = rule_source_status()
    if all(src == "missing" for src in sources.values()):
        failures.append("规则源不可用：GitHub 与本地 fallback 均无法读取关键规则文件。")

    # 检查1：报告文件是否存在
    if not report_path.exists():
        failures.append(f"报告文件不存在：{report_path}")
        return False, failures

    # 检查2：文件大小硬上限 20,000 bytes
    file_size = report_path.stat().st_size
    if file_size > 20000:
        failures.append(
            f"文件大小超限：{file_size} bytes > 20,000 bytes 上限。"
            f"日报必须拆分，不允许进入 dashboard。"
        )

    # 检查3：禁止系统后台字段出现在报告正文
    content = report_path.read_text(encoding="utf-8-sig", errors="ignore")

    backend_markers = [
        "数据库路径",
        "account_database_v1.json",
        "chatgpt_validated",
        "pending_validation",
        "color: yellow",
        "quality_goal_task_status",
        "是否达标：YES",
        "是否达标：NO",
        "闭环10项必答",
        "QUALITY-GOAL-STATUS",
    ]
    for marker in backend_markers:
        if marker in content:
            failures.append(f"系统后台字段出现在用户报告正文中：「{marker}」")

    # 检查4：必须包含 Delta 卡
    if "今日 Delta" not in content and "今日Delta" not in content:
        failures.append("缺少今日 Delta 卡：报告必须包含「今日 Delta」模块。")

    # 检查5：必须包含四账户唯一动作
    required_accounts = ["富途", "IBKR", "SBI", "BF"]
    for acct in required_accounts:
        if acct not in content:
            failures.append(f"缺少账户动作：报告未包含「{acct}」账户的今日动作。")

    # 检查6：必须包含失效条件
    if "失效条件" not in content:
        failures.append("缺少失效条件：报告必须至少包含一处「失效条件」。")

    # 检查7：必须包含昨日验证
    if "昨日验证" not in content and "昨日判断" not in content:
        failures.append("缺少昨日验证：报告必须包含「昨日验证」或「昨日判断」模块。")

    # 检查8：禁止出现原始系统卡片全文标记
    raw_markers = ["<details", "<pre>", "</pre>", "</details>"]
    for marker in raw_markers:
        if marker in content:
            failures.append(
                f"原始系统卡片全文被嵌入报告（检测到「{marker}」标记）。"
                f"完整卡片必须存为独立文件，不得内嵌在用户日报中。"
            )
            break  # 只报告一次

    return len(failures) == 0, failures


def write_failure_log(report_path: Path, failures: list[str]):
    """将失败原因写入 skill_gate_failure_log.md"""
    now = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S JST")
    log_path = ROOT / "reports/validation/skill_gate_failure_log.md"

    existing = ""
    if log_path.exists():
        existing = log_path.read_text(encoding="utf-8", errors="ignore")

    entry = f"""
## 阻断记录 {now}

被阻断文件：{report_path}
规则源模式：{RULE_SOURCE_MODE}
规则源状态：{rule_source_status()}
阻断原因：
"""
    for i, f in enumerate(failures, 1):
        entry += f"  {i}. {f}\n"

    entry += "\n---\n"

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(entry + existing, encoding="utf-8")
    print(f"[skill_gate] 失败日志已写入：{log_path}")


def run_gate(report_path: Path) -> bool:
    """
    对外暴露的主函数。
    返回 True = PASS，调用方可以继续写入 dashboard。
    返回 False = FAIL，调用方必须停止，不写入 dashboard。
    """
    passed, failures = skill_gate(report_path)

    if passed:
        print(f"[skill_gate] PASS：{report_path.name} 通过所有检查，允许写入 dashboard。")
        return True
    else:
        print(f"[skill_gate] FAIL：{report_path.name} 未通过检查，阻断写入。")
        for f in failures:
            print(f"  ✗ {f}")
        write_failure_log(report_path, failures)
        return False