# TASK PACKAGE
# TASK-2026-06-10-021 REV-A

TASK_ID: TASK-2026-06-10-021 REV-A
任务名称: DATA_FETCH_USER_AGENT_FIX_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 实施类（代码修复）
影响范围: scripts/daily_data_fetch.py（修复超时机制）
APPROVAL_REQUIRED: YES
审批状态: PENDING（REV-A，等待 ChatGPT 重新审批）
旧版本状态: TASK-2026-06-10-021 原始版不通过验收，自动作废
是否涉及账户操作: NO
是否涉及规则变更: NO
是否生成交易指令: NO
是否新增功能: NO

---

## 根因更新（ChatGPT 审核结论）

旧根因（已废弃）：Yahoo Finance 拒绝无 User-Agent 请求
新根因（已确认）：HTTP 请求卡死——urlopen 在用户本地环境
                  无限等待，导致脚本挂起，不是数据源拒绝。

症状：
  用户本地运行耗时 13.31 秒（4项全卡死）
  Codex 环境运行耗时 2.92 秒（4项全 OK）
  差异来源：用户本地网络对 Yahoo Finance 的 TCP 连接
            未能在合理时间内完成，且无超时保护导致卡死

修复方向：
  不是修改 User-Agent（已保留，无害）
  而是增加：
    单项请求硬超时（10秒）
    总任务硬超时（45秒）
    [FETCH_START] 逐项日志（用户能看到哪项在卡）
    HARD_TIMEOUT 自动降级 DATA_GAP（不允许无限等待）

---

## 精确修复规范

### 修复1：单项请求硬超时（10秒）

四个 fetch 函数中，将 timeout 从 8 改为 10，
并用 threading.Timer 实现硬超时保护：

```python
import threading
import urllib.request

ITEM_TIMEOUT = 10   # 单项请求超时秒数
TOTAL_TIMEOUT = 45  # 总任务超时秒数

def _fetch_with_hard_timeout(url: str, timeout: int = ITEM_TIMEOUT) -> bytes:
    """
    带硬超时的 HTTP 请求。
    timeout 内未完成则抛出 TimeoutError，
    防止 urlopen 卡死。
    """
    result = [None]
    error  = [None]

    def _do_request():
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": BROWSER_UA}
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                result[0] = r.read()
        except Exception as e:
            error[0] = e

    t = threading.Thread(target=_do_request, daemon=True)
    t.start()
    t.join(timeout + 1)          # 额外1秒缓冲

    if t.is_alive():
        raise TimeoutError(
            f"HARD_TIMEOUT: 请求超过 {timeout} 秒未完成，强制降级 DATA_GAP")
    if error[0] is not None:
        raise error[0]
    return result[0]
```

### 修复2：四个 fetch 函数改用 _fetch_with_hard_timeout

修复前（fetch_vix 示例）：
```python
req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
with urllib.request.urlopen(req, timeout=8) as r:
    data = json.loads(r.read())
```

修复后：
```python
raw = _fetch_with_hard_timeout(url, timeout=ITEM_TIMEOUT)
data = json.loads(raw)
```

四个函数（fetch_vix / fetch_tnx / fetch_spx_change / fetch_btc_change）
全部替换为同一模式。

### 修复3：[FETCH_START] 逐项日志

在每个 fetch 函数入口处增加日志输出：
```python
print(f"[FETCH_START] {name} ...")
# 执行请求
print(f"[FETCH_DONE]  {name} → {status} ({elapsed:.2f}s)")
```

用户能实时看到哪项在请求、哪项超时降级。

### 修复4：总任务硬超时（45秒）

在 main() 中，用 threading.Timer 实现总超时：
```python
def _total_timeout_handler():
    print("\nHARD_TIMEOUT: 总任务超过 45 秒，强制退出。")
    print("所有未完成项已降级为 DATA_GAP。")
    sys.exit(2)

total_timer = threading.Timer(TOTAL_TIMEOUT, _total_timeout_handler)
total_timer.daemon = True
total_timer.start()

# ... 执行数据获取 ...

total_timer.cancel()   # 正常完成后取消定时器
```

---

## 禁止事项（修复范围限制）

禁止新增任何功能
禁止修改数据写入逻辑
禁止修改用户确认步骤
禁止修改历史保护逻辑
禁止修改确认日志逻辑
禁止修改 display_data_status()
禁止修改 skill_gate.py / governance_runtime.py
禁止修改 dashboard.html
禁止生成日报
禁止涉及账户操作
禁止自行最终验收
禁止在用户本地验证前填写 AUTO_READY: YES

---

## ACCEPTANCE_CRITERIA

1. _fetch_with_hard_timeout() 函数已新增
2. ITEM_TIMEOUT = 10 常量已定义
3. TOTAL_TIMEOUT = 45 常量已定义
4. 四个 fetch 函数已改用 _fetch_with_hard_timeout
5. [FETCH_START] / [FETCH_DONE] 逐项日志已实现
6. main() 已加入总任务硬超时（45秒）
7. 超时触发时输出 HARD_TIMEOUT 并降级 DATA_GAP
8. governance_runtime.py 前置检查通过
9. dry-run 测试：脚本在 45 秒内必须退出（无卡死）
10. 验收包 12 项字段完整
11. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. daily_data_fetch.py 四处修复完成 ✓
2. 脚本在 45 秒内必须退出（含超时降级） ✓
3. [FETCH_START] 日志出现在 dry-run 输出中 ✓
4. 用户本地重新运行，脚本不再卡死 ✓
5. 验收包 12 项字段完整 ✓
6. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

步骤0：governance_runtime.py 前置检查
  python scripts/governance_runtime.py \
    --task-id "TASK-2026-06-10-021-REV-A" \
    --stage "implementation" \
    --approved "true" \
    --executor "Codex" \
    --acceptor "ChatGPT" \
    --thread "AI投研总控台 + 正式日报生产" \
    --task-type "governance" \
    --affects-account "false"

步骤1：读取现有 daily_data_fetch.py
  记录修复前文件大小

步骤2：按修复规范修改 daily_data_fetch.py
  新增 ITEM_TIMEOUT / TOTAL_TIMEOUT 常量
  新增 _fetch_with_hard_timeout() 函数
  修改四个 fetch 函数改用新函数
  新增 [FETCH_START] / [FETCH_DONE] 日志
  main() 新增总任务硬超时
  记录修复后文件大小

步骤3：dry-run 测试
  python scripts/daily_data_fetch.py --dry-run
  计时：脚本是否在 45 秒内退出
  记录：[FETCH_START] 日志是否出现
  记录：各项 OK / DATA_GAP / HARD_TIMEOUT

步骤4：生成验收包
  路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
        task-2026-06-10-021-rev-a_validation_package.md
  须含：
    section 1：修复前后对比（新增函数/常量/日志）
    section 2：实际修改文件位置和大小
    section 3：dry-run 实际输出（含 [FETCH_START] 日志）
    section 4：脚本退出时间（是否 ≤45 秒）
    section 5：用户本地复测指引
    section 6：AUTO_READY 判定（待用户验证）
    section 7：12项标准验收字段
