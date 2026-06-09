# Skill Runtime Integration Design V1
# Skill 运行时接入设计

生效日期：2026-06-09 JST
设计人：Claude
执行人：Codex
最终验收人：ChatGPT / AI投研总控台 V4

---

## 核心问题诊断

当前所有 Skill 文件均为静态文档。
日报生成脚本（如 user_daily_report_v1.md 的生成）完全不读取任何 Skill。
这导致 223,992 bytes 的日报能被生成并写入 dashboard，没有任何检查点阻断它。

解决方案：最小改造原则。
不新增 Skill，不新增规则，不重写日报。
只在现有执行脚本中，增加一个前置检查函数，在写入 dashboard.html 之前强制执行。

---

## 改造架构：三个文件，一个原则

### 原则
所有写入 dashboard.html 的操作，必须先通过 skill_gate() 检查。
skill_gate() 返回 PASS 才允许写入。
skill_gate() 返回 FAIL 必须阻断写入，将失败原因写入 skill_gate_failure_log.md。

### 文件1：入口检查器（新增）
路径：AI_Investment_System/scripts/skill_gate.py
职责：读取 user_report_quality_gate.skill，执行所有硬阻断检查，返回 PASS 或 FAIL。
被谁调用：所有日报生成脚本在写入 dashboard.html 之前调用。

### 文件2：失败日志（自动生成）
路径：AI_Investment_System/reports/validation/skill_gate_failure_log.md
职责：记录每次 skill_gate() 返回 FAIL 的时间、原因、被阻断的文件路径。
由谁写入：skill_gate.py 在检查失败时自动写入。

### 文件3：现有日报生成脚本（修改）
涉及文件：所有在 scripts/ 目录下写入 dashboard.html 或 user_daily_report_v1.md 的 .py 脚本。
修改内容：在 dashboard.html 写入操作之前，插入对 skill_gate() 的调用。
如果 skill_gate() 返回 FAIL，立即停止写入，print 阻断原因，退出脚本。

---

## skill_gate.py 完整实现

```python
# skill_gate.py
# AI投研总控台 V4 Skill 运行时质量门控
# 在所有 dashboard.html 写入操作前调用此函数

from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(r"G:\我的云端硬盘\AI_Investment_System")

def skill_gate(report_path: Path) -> tuple[bool, list[str]]:
    """
    执行 Skill 硬阻断检查。
    返回 (True, []) 表示 PASS，允许写入。
    返回 (False, [原因列表]) 表示 FAIL，必须阻断写入。
    """
    failures = []

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
```

---

## 现有脚本的修改模式

所有现有日报生成脚本，在写入 dashboard.html 之前，插入以下代码：

```python
# === Skill Gate 检查（必须在写入 dashboard 之前执行）===
import sys
sys.path.insert(0, str(ROOT / "scripts"))
from skill_gate import run_gate

report_file = ROOT / "reports/daily/user_daily_report_v1.md"
if not run_gate(report_file):
    print("[阻断] Skill Gate 检查未通过，dashboard.html 写入已取消。")
    print("[阻断] 请查看：reports/validation/skill_gate_failure_log.md")
    sys.exit(1)
# === Skill Gate 检查结束，以下为正常写入 ===
```

这段代码插入位置：在 `w("reports/daily/dashboard.html", ...)` 调用之前。

---

## 哪个文件是入口

入口文件：skill_gate.py
调用时机：所有日报生成脚本写入 dashboard.html 之前。

---

## 哪个文件负责阻断

阻断逻辑在：skill_gate.py 的 skill_gate() 函数。
阻断行为：返回 False，调用方执行 sys.exit(1)，写入操作不执行。

---

## 哪个文件负责记录失败原因

失败日志：AI_Investment_System/reports/validation/skill_gate_failure_log.md
格式：时间戳 + 被阻断文件路径 + 失败原因列表，新记录追加在顶部。

---

## 覆盖的 Skill 硬阻断规则

skill_gate.py 的 8 项检查，对应以下 Skill 的规则：

| 检查项 | 对应 Skill |
|---|---|
| 文件大小 > 20,000 bytes | user_report_constitution_v1.md（新增规则） |
| 系统后台字段出现在正文 | user_report_quality_gate.skill |
| 缺少 Delta 卡 | user_report_constitution_v1.md |
| 缺少四账户动作 | user_report_constitution_v1.md |
| 缺少失效条件 | user_report_constitution_v1.md |
| 缺少昨日验证 | user_report_constitution_v1.md |
| 原始系统卡片嵌入正文 | Role & Quality Drift Audit V1 结论 |
| 报告文件不存在 | 基础完整性检查 |

---

## 223,992 bytes 日报的自动 FAIL 验证

user_daily_report_v1.md 大小：223,992 bytes
skill_gate 检查2：文件大小 > 20,000 bytes → 立即 FAIL
skill_gate 检查3：文件包含 `<details`、`<pre>` 标记 → 追加 FAIL
skill_gate 检查3：文件包含「account_database_v1.json」路径字段 → 追加 FAIL

结论：如果 skill_gate.py 存在，user_daily_report_v1.md 将在写入 dashboard 之前被自动阻断，
      失败原因写入 skill_gate_failure_log.md，dashboard.html 不会被更新。

---

SKILL_RUNTIME_INTEGRATION_DESIGN_READY: YES

状态：PASS（设计完成，等待 Codex 实现并由 ChatGPT 验收）
执行人：Claude（设计）/ Codex（实现）
预检人：Claude
最终验收人：ChatGPT / AI投研总控台 V4
发给谁：ChatGPT / AI投研总控台 V4
下一步唯一动作：Codex 将 skill_gate.py 写入 scripts/ 目录，
               并在任意一个现有日报生成脚本中添加 skill_gate 调用，
               测试 user_daily_report_v1.md（223,992 bytes）是否被正确阻断
可直接执行指令：Codex 执行以下操作：
  1. 将 skill_gate.py 完整代码写入
     AI_Investment_System/scripts/skill_gate.py
  2. 将本设计文档写入
     AI_Investment_System/docs/skill_runtime_integration_design_v1.md
  3. 测试：对 user_daily_report_v1.md 运行 run_gate()，确认返回 False
  4. 将测试结果写入验收包
     AI_Investment_System/reports/validation/
     skill_runtime_integration_design_v1_validation_package.md
  5. 验收包必须包含：
     - skill_gate.py 是否成功写入
     - 对 user_daily_report_v1.md 的测试结果（PASS/FAIL）
     - 具体的阻断原因列表
     - skill_gate_failure_log.md 是否生成
     - 文件大小检查结果
  6. 不能自动下单，不能改账户数据，不能自己最终验收