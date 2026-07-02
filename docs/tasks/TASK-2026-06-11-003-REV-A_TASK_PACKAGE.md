# TASK PACKAGE
# TASK-2026-06-11-003 REV-A

TASK_ID: TASK-2026-06-11-003 REV-A
任务名称: AUTO_DECISION_BRIEFING_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 实施类（代码）
影响范围: scripts/auto_briefing.py（新建）
APPROVAL_REQUIRED: YES
审批状态: PENDING（REV-A，等待 ChatGPT 重新审批）
旧版本状态: TASK-2026-06-11-003 原始版自动作废
是否涉及账户操作: NO
是否涉及规则变更: NO
是否生成交易指令: NO
是否修改账户数据: NO

---

## 审批变更项（已合并，共3项）

1. 输出末尾必须包含：
   NEXT_OWNER / NEXT_ACTION / NEXT_THREAD

2. briefing 生成后自动记录：
   TASK_ID / 生成时间 / 数据时间

3. 明确禁止：
   自动下单 / 自动生成交易指令 /
   修改账户文件 / 写入执行卡
   仅输出：第0层结论 / 第1层结论 / 第2层结论

---

## 交付内容

### scripts/auto_briefing.py（新建）

完整代码规范：

```python
#!/usr/bin/env python3
"""
auto_briefing.py
自动决策简报 V1
TASK-2026-06-11-003 REV-A

功能：
  1. 调用 daily_data_fetch 获取数据
  2. 自动六步查表
  3. 输出第0/1/2层结论 + NEXT_OWNER/ACTION/THREAD
  4. 用户 Y 确认后写入 daily_briefing_template_v1.md
  5. 生成 briefing 记录（TASK_ID + 生成时间 + 数据时间）

禁止：
  自动下单 / 自动生成交易指令 /
  修改账户文件 / 写入执行卡

运行命令：
  python scripts/auto_briefing.py
  python scripts/auto_briefing.py --dry-run
"""

import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(r"G:\我的云端硬盘\AI_Investment_System")
JST  = timezone(timedelta(hours=9))
BRIEFING_LOG_PATH = ROOT / "data" / "auto_briefing_log.json"
TEMPLATE_PATH     = ROOT / "docs" / "daily_briefing_template_v1.md"

# 复用 daily_data_fetch 的 fetch 函数
sys.path.insert(0, str(Path(__file__).parent))
from daily_data_fetch import (
    fetch_vix, fetch_tnx, fetch_spx_change,
    fetch_btc_change, fetch_user_config,
    display_data_status,
)

# ─────────────────────────────────────────────
# 六步自动查表
# ─────────────────────────────────────────────

def step1_cycle(vix, tnx) -> tuple[str, str]:
    """步骤1：周期定位 → (周期标签, 置信度)"""
    if vix is None or tnx is None:
        return "UNKNOWN", "C"
    if vix < 20 and tnx < 4.5:
        return "BULL_MID", "A"
    if vix < 20:
        return "BULL_MID", "B"
    if vix <= 25:
        return "TRANSITION", "B"
    return "BEAR", "B"


def step2_allocation(crypto_pct) -> str:
    """步骤2：配置偏离检查"""
    if crypto_pct is None:
        return "DATA_GAP"
    return "YES（需再平衡）" if crypto_pct > 10 else "NO"


def step3_signal(spx, btc) -> dict:
    """步骤3：信号等级"""
    signals = {}
    if spx is None:
        signals["美股"] = "C（数据缺失）"
    elif spx > 0.5:
        signals["美股"] = "B"
    elif spx < -1.0:
        signals["美股"] = "无（防守）"
    else:
        signals["美股"] = "C"

    if btc is None:
        signals["加密"] = "C（DATA_GAP）"
    elif btc > 1.0:
        signals["加密"] = "B"
    else:
        signals["加密"] = "C"

    signals["日股"] = "观察"
    signals["A股"]  = "观察"
    return signals


def generate_conclusions(cycle: str, confidence: str,
                          signals: dict, crypto_pct) -> dict:
    """生成第0/1/2层结论"""

    # 第0层：今日结论
    conclusion_map = {
        ("BULL_MID", "A"): "允许分批布局AI核心，流动性支撑充足",
        ("BULL_MID", "B"): "谨慎布局，控制仓位，等待更强确认信号",
        ("TRANSITION", "B"): "今天进入观察期，数据冲突，暂缓新仓",
        ("BEAR",       "B"): "进入防守模式，持有现金，禁止新增高Beta",
        ("UNKNOWN",    "C"): "证据不足，仅观察，不执行任何操作",
    }
    layer0 = conclusion_map.get(
        (cycle, confidence),
        f"当前周期 {cycle}，置信度 {confidence}，请手动判断"
    )

    # 第1层：今日唯一动作
    has_b_signal = any("B" in v for v in signals.values())
    if confidence == "C" or cycle in ("UNKNOWN", "BEAR"):
        layer1 = "观察"
    elif has_b_signal and confidence in ("A", "B"):
        layer1 = "分批建仓 [账户待确认 / 标的待确认]"
    else:
        layer1 = "持有"

    # 第2层：最不能做
    forbidden = []
    if cycle in ("TRANSITION", "BEAR", "UNKNOWN"):
        forbidden.append("禁止加杠杆")
    if signals.get("美股", "").startswith("无"):
        forbidden.append("禁止抄底")
    if crypto_pct is not None and crypto_pct > 8:
        forbidden.append("禁止加仓加密（接近上限）")
    if not forbidden:
        forbidden.append("禁止追高")

    return {
        "layer0": layer0,
        "layer1": layer1,
        "layer2": forbidden,
        "cycle": cycle,
        "confidence": confidence,
    }


# ─────────────────────────────────────────────
# NEXT_OWNER / NEXT_ACTION / NEXT_THREAD（变更项1）
# ─────────────────────────────────────────────

def generate_next_steps(confidence: str, layer1: str) -> dict:
    """根据置信度和唯一动作输出 NEXT 三元组"""
    if confidence == "C":
        return {
            "NEXT_OWNER":  "用户",
            "NEXT_ACTION": "仅观察，不执行操作，明日重新运行 auto_briefing.py",
            "NEXT_THREAD": "AI投研总控台 + 正式日报生产",
        }
    if "分批建仓" in layer1:
        return {
            "NEXT_OWNER":  "用户",
            "NEXT_ACTION": "确认账户和标的后，在券商手动下单（不自动执行）",
            "NEXT_THREAD": "AI投研总控台 + 正式日报生产",
        }
    return {
        "NEXT_OWNER":  "用户",
        "NEXT_ACTION": "持有当前仓位，明日重新运行 auto_briefing.py",
        "NEXT_THREAD": "AI投研总控台 + 正式日报生产",
    }


# ─────────────────────────────────────────────
# Briefing 记录（变更项2）
# ─────────────────────────────────────────────

def write_briefing_log(conclusions: dict, data_results: dict,
                        today_str: str) -> None:
    """记录 TASK_ID / 生成时间 / 数据时间"""
    BRIEFING_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if BRIEFING_LOG_PATH.exists():
        try:
            existing = json.loads(
                BRIEFING_LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            existing = []

    entry = {
        "task_id":       "TASK-2026-06-11-003-REV-A",
        "generated_at":  datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "data_date":     today_str,
        "data_times": {
            "vix": data_results["vix"].get("updated_at", "—"),
            "tnx": data_results["tnx"].get("updated_at", "—"),
            "spx": data_results["spx"].get("updated_at", "—"),
            "btc": data_results["btc"].get("updated_at", "—"),
        },
        "layer0":     conclusions["layer0"],
        "layer1":     conclusions["layer1"],
        "layer2":     conclusions["layer2"],
        "cycle":      conclusions["cycle"],
        "confidence": conclusions["confidence"],
    }
    existing.append(entry)
    BRIEFING_LOG_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"[BRIEFING_LOG] 记录已写入：{BRIEFING_LOG_PATH}")


# ─────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────

def main():
    print("[MAIN_START] auto_briefing 启动")
    import argparse
    parser = argparse.ArgumentParser(description="自动决策简报")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(sys.argv[1:])
    print(f"[ARGS_PARSED] dry_run={args.dry_run}")

    today_str = datetime.now(JST).strftime("%Y-%m-%d")
    t_start = time.time()

    # 获取数据
    print("\n[FETCH] 获取市场数据...")
    results = {
        "vix":    fetch_vix(),
        "tnx":    fetch_tnx(),
        "spx":    fetch_spx_change(),
        "btc":    fetch_btc_change(),
        "config": fetch_user_config(),
    }
    display_data_status(results)

    # 六步查表
    vix_val     = results["vix"]["value"]
    tnx_val     = results["tnx"]["value"]
    spx_val     = results["spx"]["value"]
    btc_val     = results["btc"]["value"]
    crypto_pct  = results["config"]["crypto_position_pct"]

    cycle, confidence = step1_cycle(vix_val, tnx_val)
    allocation        = step2_allocation(crypto_pct)
    signals           = step3_signal(spx_val, btc_val)
    conclusions       = generate_conclusions(
        cycle, confidence, signals, crypto_pct)
    next_steps        = generate_next_steps(
        confidence, conclusions["layer1"])

    # 输出结论（变更项3：仅输出三层结论）
    print("\n" + "=" * 60)
    print("AUTO DECISION BRIEFING")
    print(f"日期: {today_str}  周期: {cycle}  置信度: {confidence}")
    print("=" * 60)
    print(f"第0层 今日结论  : {conclusions['layer0']}")
    print(f"第1层 唯一动作  : {conclusions['layer1']}")
    print(f"第2层 最不能做  : {' / '.join(conclusions['layer2'])}")
    print("-" * 60)
    print(f"NEXT_OWNER  : {next_steps['NEXT_OWNER']}")
    print(f"NEXT_ACTION : {next_steps['NEXT_ACTION']}")
    print(f"NEXT_THREAD : {next_steps['NEXT_THREAD']}")
    print("=" * 60)
    print()
    print("⚠️  本输出仅供参考。禁止自动下单。禁止修改账户文件。")
    print("    执行前必须用户人工确认。")

    t_elapsed = time.time() - t_start
    print(f"\n总耗时: {t_elapsed:.2f} 秒")

    if args.dry_run:
        print("[DRY RUN] 完成，未写入任何文件。")
        sys.exit(0)

    # 用户确认（不可跳过）
    print("\n以上结论是否写入 daily_briefing_template_v1.md？")
    print("输入 Y 确认写入，输入 N 取消：")
    answer = input("  > ").strip().upper()
    if answer != "Y":
        print("已取消。")
        sys.exit(0)

    # 写入模板（追加当日区块）
    today_marker = f"日期: {today_str}"
    template_text = TEMPLATE_PATH.read_text(
        encoding="utf-8", errors="ignore")
    if today_marker in template_text:
        print(f"⚠ 当日记录已存在，禁止覆盖。")
        sys.exit(1)

    block = f"""
────────────────────────────────────────
AUTO BRIEFING [{today_str}]（由 auto_briefing.py 自动写入）
────────────────────────────────────────
日期: {today_str}
周期: {cycle}  置信度: {confidence}
第0层 今日结论 : {conclusions['layer0']}
第1层 唯一动作 : {conclusions['layer1']}
第2层 最不能做 : {' / '.join(conclusions['layer2'])}
NEXT_OWNER     : {next_steps['NEXT_OWNER']}
NEXT_ACTION    : {next_steps['NEXT_ACTION']}
NEXT_THREAD    : {next_steps['NEXT_THREAD']}
"""
    with open(TEMPLATE_PATH, "a", encoding="utf-8") as f:
        f.write(block)
    print(f"✓ 结论已写入模板 [{today_str}]")

    # 写入 briefing 记录（变更项2）
    write_briefing_log(conclusions, results, today_str)
    sys.exit(0)


if __name__ == "__main__":
    main()
```

---

## ACCEPTANCE_CRITERIA

1. auto_briefing.py 已写入 scripts/
2. governance_runtime.py 前置检查通过
3. 第0/1/2层结论基于真实数据输出（非硬编码）
4. 输出末尾含 NEXT_OWNER / NEXT_ACTION / NEXT_THREAD（变更项1）
5. data/auto_briefing_log.json 写入含
   TASK_ID / 生成时间 / 数据时间（变更项2）
6. 禁止自动下单 / 禁止修改账户文件 /
   禁止写入执行卡 / 仅输出三层结论（变更项3）
7. 用户确认步骤存在（Y/N，不可跳过）
8. Codex dry-run：45秒内完成，三层结论出现
9. 用户本地运行：三层结论出现，NEXT_OWNER 出现
10. 验收包 12 项字段完整
11. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. auto_briefing.py 写入 scripts/ ✓
2. 三项变更全部合并 ✓
3. 用户本地运行 ≤45秒，三层结论出现 ✓
4. auto_briefing_log.json 已生成 ✓
5. 验收包 12 项字段完整 ✓
6. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

步骤0：governance_runtime.py 前置检查
  python scripts/governance_runtime.py \
    --task-id "TASK-2026-06-11-003-REV-A" \
    --stage "implementation" \
    --approved "true" \
    --executor "Codex" \
    --acceptor "ChatGPT" \
    --thread "AI投研总控台 + 正式日报生产" \
    --task-type "governance" \
    --affects-account "false"

步骤1：生成 auto_briefing.py，写入 scripts/

步骤2：Codex dry-run 测试
  python scripts/auto_briefing.py --dry-run
  记录：三层结论内容 / NEXT_OWNER 出现 / 耗时

步骤3：生成验收包
  路径：reports/validation/task-2026-06-11-003_validation_package.md
  须含：
    section 1：governance_runtime 前置检查
    section 2：auto_briefing.py 写入确认
    section 3：dry-run 实际输出
      含三层结论文本 / NEXT_OWNER / NEXT_ACTION / NEXT_THREAD
    section 4：三项变更逐项确认
    section 5：用户本地复测指引
    section 6：12项标准验收字段

---

## 禁止事项

禁止自动下单
禁止生成交易指令
禁止修改账户文件
禁止写入执行卡
禁止修改 daily_data_fetch.py
禁止修改 skill_gate.py / governance_runtime.py
禁止修改 dashboard.html
禁止生成日报
禁止自行最终验收
