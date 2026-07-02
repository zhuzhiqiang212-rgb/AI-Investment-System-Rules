#!/usr/bin/env python3
"""
governance_runtime.py
AI_PROJECT_GOVERNANCE_V2 运行时强制入口
TASK-2026-06-10-015 REV-A

规则：
  Codex 执行任何正式任务前，必须先运行本脚本。
  通过（返回0）才允许继续执行任务。
  失败（返回1）则阻断所有后续步骤，等待 RESUME_AFTER_VIOLATION。

标准运行命令（变更项2）：
  python scripts/governance_runtime.py \
    --task-id      "TASK-XXXX-XX-XX-XXX" \
    --stage        "implementation" \
    --approved     "true" \
    --executor     "Codex" \
    --acceptor     "ChatGPT" \
    --thread       "AI投研总控台 + 正式日报生产" \
    --task-type    "governance" \
    --affects-account "false"

返回值：
  0 = PASS，允许继续执行
  1 = BLOCKED，任务中止，等待 RESUME_AFTER_VIOLATION
"""

import argparse
import sys
from pathlib import Path

# 引入现有 skill_gate 中的函数（不修改 skill_gate.py）
sys.path.insert(0, str(Path(__file__).parent))
from skill_gate import process_gate, emit_process_violation


def run_governance_check(task_context: dict) -> bool:
    """
    强制 Gate Check。
    Codex 每次执行任务前必须调用。
    返回 True = 通过，允许继续。
    返回 False = 阻断，任务中止。
    """
    task_id = task_context.get("task_id", "UNKNOWN")

    print(f"[governance_runtime] Gate Check 开始 — TASK_ID: {task_id}")

    passed, violations = process_gate(task_context)

    if not passed:
        # 变更项3：失败后阻断规则
        emit_process_violation(
            violations=violations,
            role=task_context.get("executor", "UNKNOWN"),
            stage=task_context.get("stage", "UNKNOWN"),
            task_id=task_id,
        )
        print("=" * 60)
        print("BLOCKED")
        print("Skill Gate 未通过，任务中止。")
        print("禁止：生成日报 / 写入正式结果 / 进入下一步")
        print("解除：用户输出 RESUME_AFTER_VIOLATION + 原因")
        print("=" * 60)
        return False

    print(f"[governance_runtime] Gate Check 通过 — TASK_ID: {task_id} — 允许继续执行")
    return True


def validate_task_package(task_package_path: str) -> bool:
    """
    验证 TASK_PACKAGE.md 的 13 个必填字段是否完整。
    缺失字段触发 PV-002。
    """
    required_fields = [
        "TASK_ID", "任务名称", "执行对话", "提案人", "执行人",
        "验收人", "任务类型", "影响范围", "APPROVAL_REQUIRED",
        "审批状态", "CODEX_EXECUTION", "ACCEPTANCE_CRITERIA", "CLOSE_CONDITION",
    ]
    try:
        content = Path(task_package_path).read_text(encoding="utf-8", errors="ignore")
        missing = [f for f in required_fields if f not in content]
        if missing:
            print(f"[governance_runtime] PV-002: 缺失字段 → {', '.join(missing)}")
            return False
        return True
    except FileNotFoundError:
        print(f"[governance_runtime] TASK_PACKAGE 文件未找到: {task_package_path}")
        return False


def check_thread_compliance(thread: str, task_type: str) -> bool:
    """线程合规检查。"""
    if "系统维护" in thread and task_type == "daily_report":
        print("[governance_runtime] PV-006: 维护线程禁止执行正式日报生产任务")
        return False
    if "投研总控台" in thread and task_type == "temp_test":
        print("[governance_runtime] PV-007: 主线程禁止做无关临时测试")
        return False
    return True


def check_approver_executor_split(executor: str, acceptor: str) -> bool:
    """审批人与执行人分离检查。"""
    if executor and acceptor and executor == acceptor:
        print(f"[governance_runtime] PV-004: 执行人 = 验收人（{executor}），自验违规")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="AI_PROJECT_GOVERNANCE_V2 运行时强制入口"
    )
    parser.add_argument("--task-id",        required=True)
    parser.add_argument("--stage",          required=True)
    parser.add_argument("--approved",       required=True)
    parser.add_argument("--executor",       required=True)
    parser.add_argument("--acceptor",       required=True)
    parser.add_argument("--thread",         required=True)
    parser.add_argument("--task-type",      required=True)
    parser.add_argument("--affects-account", default="false")
    parser.add_argument("--user-confirmed", default="false")
    parser.add_argument("--acceptance-package-path", default="")
    args = parser.parse_args()

    task_context = {
        "task_id":                  args.task_id,
        "stage":                    args.stage,
        "approved":                 args.approved.lower() == "true",
        "executor":                 args.executor,
        "acceptor":                 args.acceptor,
        "thread":                   args.thread,
        "task_type":                args.task_type,
        "affects_account":          args.affects_account.lower() == "true",
        "user_confirmed":           args.user_confirmed.lower() == "true",
        "acceptance_package_path":  args.acceptance_package_path,
    }

    passed = run_governance_check(task_context)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
