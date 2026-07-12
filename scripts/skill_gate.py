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
            with urllib.request.urlopen(url, timeout=10) as resp:
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

    # 检查8：禁止 Markdown 用户日报正文内嵌原始系统卡片全文。
    # dashboard.html 属于页面容器，允许使用 <details>/<pre> 做折叠与排版；
    # Markdown 正文不允许用这些 HTML 标记把后台原文整段塞进用户日报。
    is_dashboard_html = report_path.name.lower() == "dashboard.html" and report_path.suffix.lower() == ".html"
    if not is_dashboard_html:
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



# ═══════════════════════════════════════════════════════
# Constitution compliance gate
# TASK-2026-07-02-037
# 本模块只做形式检查：是否写出“总则对照”声明及第六条防静态化自评。
# 不判断声明语义是否正确，语义判断留给 Claude 第二质检与董事长终审。
# ═══════════════════════════════════════════════════════

CONSTITUTION_GATE_REQUIRED_MARKERS = ["总则对照", "第六条", "防静态化", "自评"]


def is_constitution_task_package(target: Path) -> bool:
    """Only docs/tasks/TASK-* packages are hard-blocked by the formal declaration gate.

    Final products such as daily report HTML are exempt here because their
    compliance is guaranteed by the producing task package and later semantic QA.
    """
    normalized = str(target).replace("\\", "/")
    return "/docs/tasks/TASK-" in normalized or normalized.startswith("docs/tasks/TASK-")


def constitution_gate(task_or_report_path: Path) -> tuple[bool, list[str]]:
    """
    总则合规形式检查。
    PASS：目标文件存在，正文包含“总则对照”，并包含第六条防静态化自评相关关键词。
    FAIL：缺文件或缺声明块。只做形式检查，不锁死具体答案。
    """
    target = Path(task_or_report_path)
    failures: list[str] = []
    if not target.exists():
        failures.append(f"目标文件不存在：{target}")
        return False, failures
    if not is_constitution_task_package(target):
        return True, []
    content = target.read_text(encoding="utf-8-sig", errors="ignore")
    if not all(marker in content for marker in CONSTITUTION_GATE_REQUIRED_MARKERS):
        failures.append("缺总则六条对照声明；此硬闸仅适用于 docs/tasks/TASK-* 任务包，最终产品日报由生产任务担保并在语义质检中复核")
    return len(failures) == 0, failures


def run_constitution_gate(path: Path) -> bool:
    """
    对外主函数。PASS 返回 True；FAIL 返回 False 并复用 write_failure_log 记录。
    """
    target = Path(path)
    passed, failures = constitution_gate(target)
    if passed:
        print(f"[constitution_gate] PASS：{target.name} 已包含总则对照与第六条防静态化自评。")
        return True
    print(f"[constitution_gate] FAIL：{target.name} 未通过总则合规形式检查。")
    for failure in failures:
        print(f"  ✗ {failure}")
    write_failure_log(target, failures)
    return False

# ═══════════════════════════════════════════════════════
# CEO self-discipline gate
# TASK-2026-07-03-067
# 本模块只做形式检查：CEO 设计或第二质检产出是否写明依据与质检清单。
# 不判断声明语义是否正确，语义判断留给 Claude 第二质检与董事长终审。
# ═══════════════════════════════════════════════════════

CEO_BASIS_POINTERS = ["总则", "蓝图", "董事长"]
CEO_QA_CHECKLIST_MARKERS = [
    "质检清单",
    "独立读实际文件",
    "核对真数据",
    "验证动态性",
    "无乱码",
    "对照总则六条",
    "结构完整",
]


def ceo_design_gate(design_or_review_path: Path) -> tuple[bool, list[str]]:
    """
    CEO 自律形式检查。
    PASS：目标文件存在，正文含设计依据声明，且含第二质检六项清单。
    FAIL：缺依据声明或缺质检清单。只做形式检查，不锁死具体答案。
    """
    target = Path(design_or_review_path)
    failures: list[str] = []
    if not target.exists():
        failures.append(f"目标文件不存在：{target}")
        return False, failures
    content = target.read_text(encoding="utf-8-sig", errors="ignore")
    has_basis = "依据" in content and any(pointer in content for pointer in CEO_BASIS_POINTERS)
    if not has_basis:
        failures.append("CEO设计缺依据声明")
    missing_checklist = [marker for marker in CEO_QA_CHECKLIST_MARKERS if marker not in content]
    if missing_checklist:
        failures.append("缺质检清单：" + "、".join(missing_checklist))
    return len(failures) == 0, failures


def run_ceo_gate(path: Path) -> bool:
    """
    对外主函数。PASS 返回 True；FAIL 返回 False 并复用 write_failure_log 记录。
    """
    target = Path(path)
    passed, failures = ceo_design_gate(target)
    if passed:
        print(f"[ceo_design_gate] PASS：{target.name} 已包含设计依据与第二质检清单。")
        return True
    print(f"[ceo_design_gate] FAIL：{target.name} 未通过 CEO 自律形式检查。")
    for failure in failures:
        print(f"  ✗ {failure}")
    write_failure_log(target, failures)
    return False

# ═══════════════════════════════════════════════════════
# AI_PROJECT_GOVERNANCE_V2  流程合规检查模块
# TASK-2026-06-10-001 REV-A
# 生效时间：2026-06-10 JST
# 本模块不修改投资逻辑，只检查任务流程合规性。
# 仅在兼容性检查确认缺失时，补充必要 import（见下方注释）。
# ═══════════════════════════════════════════════════════

# [兼容性 import 占位]
# 第一阶段检查确认 ROOT / datetime / timezone / timedelta 均已存在。
# 本追加区块不补充 import，避免修改现有 import 区域。

PROCESS_VIOLATION_CODES = {
    "PV-001": "未提交 PROPOSAL 直接要求 IMPLEMENTATION",
    "PV-002": "PROPOSAL 必填字段缺失",
    "PV-003": "未获得 APPROVAL 直接执行任务",
    "PV-004": "执行人 = 验收人（自验违规）",
    "PV-005": "执行超出 APPROVAL 批准范围",
    "PV-006": "维护线程禁止执行正式日报生产任务",
    "PV-007": "主线程禁止做无关临时测试",
    "PV-008": "任务未经验收即宣布 CLOSE",
    "PV-009": "验收包缺少必填字段",
    "PV-010": "账户操作未经用户确认",
}

PROPOSAL_REQUIRED_FIELDS = [
    "任务名称", "执行对话", "提案人", "预期执行人",
    "预期验收人", "任务类型", "影响范围",
    "是否涉及账户操作", "是否涉及规则变更",
]

ACCEPTANCE_REQUIRED_FIELDS = [
    "文件名", "文件路径", "文件大小", "最后修改时间",
    "状态", "执行人", "预检人", "最终验收人",
    "发给谁", "下一步唯一动作", "可直接执行指令", "是否成功生成",
]


def process_gate(task_context: dict) -> tuple[bool, list[str]]:
    """
    AI_PROJECT_GOVERNANCE_V2 流程合规检查。

    task_context 字段说明：
      stage                  : str   当前阶段
                                     proposal / approval /
                                     implementation / acceptance / close
      proposer               : str   提案人
      executor               : str   执行人
      acceptor               : str   验收人
      approved               : bool  是否已获 APPROVAL
      thread                 : str   执行对话线程标识
      task_type              : str   daily_report / maintenance /
                                     governance / analysis / temp_test
      affects_account        : bool  是否涉及账户操作
      user_confirmed         : bool  账户操作是否经用户确认
      proposal_text          : str   PROPOSAL 原文（字段完整性检查用）
      acceptance_package_path: str   验收包路径（close 阶段必填）

    返回：
      (True,  [])            → 合规，调用方可继续执行
      (False, [违规列表])    → 违规，调用方必须调用
                               emit_process_violation() 后停止
    """
    violations = []
    stage = task_context.get("stage", "")

    # PROPOSAL 阶段：必填字段完整性检查
    if stage == "proposal":
        proposal_text = task_context.get("proposal_text", "")
        missing = [f for f in PROPOSAL_REQUIRED_FIELDS
                   if f not in proposal_text]
        if missing:
            violations.append(
                f"PV-002: PROPOSAL 必填字段缺失 → {', '.join(missing)}"
            )

    # IMPLEMENTATION 阶段
    if stage == "implementation":
        if not task_context.get("approved"):
            violations.append(
                "PV-003: 未获得 APPROVAL，禁止 IMPLEMENTATION"
            )

        executor = task_context.get("executor", "")
        acceptor = task_context.get("acceptor", "")
        if executor and acceptor and executor == acceptor:
            violations.append(
                "PV-004: 执行人 = 验收人，自验违规"
            )

        thread    = task_context.get("thread", "")
        task_type = task_context.get("task_type", "")
        if "系统维护" in thread and task_type == "daily_report":
            violations.append(
                "PV-006: 维护线程禁止执行正式日报生产任务"
            )
        if "投研总控台" in thread and task_type == "temp_test":
            violations.append(
                "PV-007: 主线程禁止做无关临时测试"
            )

    # CLOSE 阶段
    if stage == "close":
        if not task_context.get("acceptance_package_path"):
            violations.append(
                "PV-008: 任务未经验收，禁止 CLOSE"
            )

    # 任何阶段：账户操作检查
    if (task_context.get("affects_account")
            and not task_context.get("user_confirmed")):
        violations.append(
            "PV-010: 账户操作未经用户确认"
        )

    return len(violations) == 0, violations


def emit_process_violation(
    violations: list[str],
    role: str,
    stage: str,
    task_id: str = "",
) -> None:
    """
    输出标准 PROCESS_VIOLATION 并写入 skill_gate_failure_log.md。

    调用方职责：
      process_gate() 返回 violations 后，调用方必须：
        1. 调用本函数输出违规记录
        2. 停止所有后续任务
        3. 等待用户输出 RESUME_AFTER_VIOLATION 后方可继续
    """
    now = datetime.now(
        timezone(timedelta(hours=9))
    ).strftime("%Y-%m-%d %H:%M:%S JST")

    # 标准输出
    print("PROCESS_VIOLATION")
    if task_id:
        print(f"TASK_ID：{task_id}")
    for v in violations:
        print(f"  违规：{v}")
    print(f"违规角色：{role}")
    print(f"当前阶段：{stage}")
    print(f"发生时间：{now}")
    print(
        "阻断效果：后续所有任务已暂停，"
        "等待用户手动输出 RESUME_AFTER_VIOLATION 解除"
    )

    # 写入失败日志
    log_path = ROOT / "reports/validation/skill_gate_failure_log.md"
    existing = ""
    if log_path.exists():
        existing = log_path.read_text(encoding="utf-8", errors="ignore")

    entry = f"\n## PROCESS_VIOLATION 记录 {now}\n\n"
    if task_id:
        entry += f"TASK_ID：{task_id}\n"
    entry += f"违规角色：{role}\n"
    entry += f"当前阶段：{stage}\n"
    entry += "违规内容：\n"
    for v in violations:
        entry += f"  - {v}\n"
    entry += (
        "阻断状态：所有后续任务暂停\n"
        "解除方式：用户输出 RESUME_AFTER_VIOLATION + 原因\n\n---\n"
    )

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(entry + existing, encoding="utf-8")
    print(f"[process_gate] 违规日志已写入：{log_path}")

