# TASK PACKAGE
# TASK-2026-06-10-015 REV-A

TASK_ID: TASK-2026-06-10-015 REV-A
任务名称: SKILL_GATE_RUNTIME_INTEGRATION_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 实施类（代码）
影响范围: scripts/governance_runtime.py（新建）
          scripts/skill_gate.py（只读，不修改）
APPROVAL_REQUIRED: YES
审批状态: PENDING（REV-A，等待 ChatGPT 重新审批）
旧版本状态: TASK-2026-06-10-015 原始版自动作废
是否涉及账户操作: NO
是否涉及规则变更: NO

---

## 审批变更项（已合并，共5项）

1. governance_runtime.py 是强制入口，不是旁路脚本
   Codex 每次执行任何任务前，必须先通过此入口。

2. 标准运行命令格式
   任务包必须给出 Codex 每次使用的标准命令。

3. 失败后阻断规则
   PROCESS_VIOLATION 触发后：停止任务 / 不生成日报 /
   不写入正式结果 / 不进入下一步 / 等待 RESUME_AFTER_VIOLATION。

4. 验收包五项新字段
   Skill Gate 是否从"存在"变为"被调用" /
   四项测试是否通过 / 三条违规日志是否写入 /
   合规场景是否放行 / 后续任务是否强制走此入口。

5. 下一任务实测要求
   本任务完成后，下一个 Codex 任务必须故意设置违规场景，
   验证 Skill Gate 是否自动拦截。

---

## 交付内容

### 文件1：scripts/governance_runtime.py（新建，强制入口）

内容规范：

```python
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
```

---

### 标准运行命令（变更项2，每次任务前使用）

```powershell
# Codex 每次执行正式任务前，必须先运行此命令
# 返回 0 = 通过，继续执行
# 返回 1 = BLOCKED，任务中止

python scripts/governance_runtime.py `
  --task-id      "TASK-2026-06-10-XXX" `
  --stage        "implementation" `
  --approved     "true" `
  --executor     "Codex" `
  --acceptor     "ChatGPT" `
  --thread       "AI投研总控台 + 正式日报生产" `
  --task-type    "governance" `
  --affects-account "false"

# 检查返回值
if ($LASTEXITCODE -ne 0) {
    Write-Host "BLOCKED: Skill Gate 未通过，任务中止。"
    Write-Host "等待用户输出 RESUME_AFTER_VIOLATION 后方可继续。"
    exit 1
}

# 通过后执行任务主体
```

---

### 四项测试（写入验收包）

测试1：PV-003 · Codex 未获 APPROVAL
```python
ctx = {
    "task_id": "TASK-2026-06-10-015-TEST1",
    "stage": "implementation",
    "approved": False,          # 未批准 → PV-003
    "executor": "Codex",
    "acceptor": "ChatGPT",
    "thread": "AI投研总控台 + 正式日报生产",
    "task_type": "governance",
    "affects_account": False,
    "user_confirmed": False,
    "acceptance_package_path": "",
}
result = run_governance_check(ctx)
assert result == False
# 验证日志含 PROCESS_VIOLATION + PV-003
assert "PV-003" in log_text
assert "PROCESS_VIOLATION" in log_text
print("[TEST-1] PASS")
```

测试2：PV-004 · Claude 自验（executor = acceptor）
```python
ctx["approved"] = True
ctx["executor"] = "Claude"
ctx["acceptor"] = "Claude"     # 自验 → PV-004
ctx["task_id"] = "TASK-2026-06-10-015-TEST2"
result = run_governance_check(ctx)
assert result == False
assert "PV-004" in log_text
print("[TEST-2] PASS")
```

测试3：PV-006 · ChatGPT 在维护线程执行日报
```python
ctx["executor"] = "ChatGPT"
ctx["acceptor"] = "User"
ctx["thread"] = "AI系统维护"    # 维护线程
ctx["task_type"] = "daily_report"  # 正式日报 → PV-006
ctx["task_id"] = "TASK-2026-06-10-015-TEST3"
result = run_governance_check(ctx)
assert result == False
assert "PV-006" in log_text
print("[TEST-3] PASS")
```

测试4：合规基准 · 标准场景放行
```python
ctx = {
    "task_id": "TASK-2026-06-10-015-TEST4",
    "stage": "implementation",
    "approved": True,
    "executor": "Codex",
    "acceptor": "ChatGPT",
    "thread": "AI投研总控台 + 正式日报生产",
    "task_type": "governance",
    "affects_account": False,
    "user_confirmed": False,
    "acceptance_package_path": "",
}
result = run_governance_check(ctx)
assert result == True
print("[TEST-4] PASS — 合规场景正常放行")
print("[ALL TESTS] PASS")
```

---

### 下一任务实测要求（变更项5）

本任务 TASK_CLOSED 后，下一个 Codex 任务（TASK-2026-06-10-016）
必须在执行前故意传入一个违规场景运行 governance_runtime.py，
验证 Skill Gate 在真实任务流程中能够自动拦截。
违规场景建议：approved=false（PV-003）。
实测结果写入 TASK-016 验收包的 section 1。

---

## ACCEPTANCE_CRITERIA

1. governance_runtime.py 已写入 scripts/（变更项1：强制入口）
2. 标准运行命令已在文件中注释说明（变更项2）
3. 测试1：PV-003 自动触发，日志确认（变更项3）
4. 测试2：PV-004 自动触发，日志确认（变更项3）
5. 测试3：PV-006 自动触发，日志确认（变更项3）
6. 测试4：合规场景返回 True，无违规输出
7. 四项 assert 全部通过
8. skill_gate_failure_log.md 有三条新 PROCESS_VIOLATION 记录

验收包五项新字段（变更项4）：
9.  Skill Gate 是否从"存在"变为"被调用"：YES/NO
10. 四项测试是否全部通过：YES/NO
11. 三条违规日志是否实际写入：YES/NO
12. 合规场景是否放行：YES/NO
13. 后续 Codex 任务是否强制走 governance_runtime.py：YES/NO

14. 验收包 12 项标准字段完整
15. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. governance_runtime.py 已写入 scripts/ ✓
2. 四项测试全部 assert 通过 ✓
3. 三条 PROCESS_VIOLATION 日志记录存在 ✓
4. 验收包五项新字段全部 YES ✓
5. 验收包 12 项标准字段完整 ✓
6. ChatGPT 输出 PASS ✓
7. TASK-016 实测要求已记录（不要求本任务完成，但须在验收包说明）✓

---

## CODEX_EXECUTION

步骤1：确认 skill_gate.py 中存在
       process_gate() 和 emit_process_violation()
       路径：G:\我的云端硬盘\AI_Investment_System\scripts\skill_gate.py

步骤2：生成 governance_runtime.py
       按本 TASK_PACKAGE 中的完整代码规范生成
       写入：G:\我的云端硬盘\AI_Investment_System\scripts\governance_runtime.py

步骤3：运行四项测试
       记录每项实际输出、assert 结果、日志写入确认

步骤4：读取 skill_gate_failure_log.md
       确认三条新 PROCESS_VIOLATION 记录（TEST1/2/3）

步骤5：生成验收包
       路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
             task-2026-06-10-015_validation_package.md
       须含：
         section 1：governance_runtime.py 写入确认
         section 2：四项测试实际输出和 assert 结果
         section 3：日志 PROCESS_VIOLATION 出现次数
         section 4：验收包五项新字段（变更项4）
         section 5：TASK-016 实测要求说明
         section 6：12项标准验收字段

---

## 禁止事项

禁止修改 skill_gate.py 任何现有函数
禁止修改 dashboard.html
禁止生成日报
禁止涉及账户操作
禁止自行最终验收
禁止在任意 assert 失败时填写状态 PASS
禁止在四项测试未全部通过时宣布 Skill Gate 已接入
禁止在 PROCESS_VIOLATION 触发后继续执行任务主体
