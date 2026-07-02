# TASK PACKAGE
# TASK-2026-06-10-021

TASK_ID: TASK-2026-06-10-021
任务名称: DATA_FETCH_USER_AGENT_FIX_V1
执行对话: 【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护
提案人: Claude
执行人: Codex
验收人: ChatGPT / AI投研总控台 V4（≠ 执行人）
任务类型: 实施类（代码修复）
影响范围: scripts/daily_data_fetch.py（修复4处 HTTP 请求头）
APPROVAL_REQUIRED: YES
审批状态: PENDING
是否涉及账户操作: NO
是否涉及规则变更: NO
是否生成交易指令: NO
是否修改账户数据: NO

---

## 问题根因

两个完全不同的执行环境（Codex云端 + 用户本地NEC Windows）
均100% DATA_GAP，排除网络问题。

根因：
  urllib.request.urlopen(url) 默认发送：
    User-Agent: Python-urllib/3.x
  Yahoo Finance 识别非浏览器请求并拒绝（401/429）。

修复方案：
  将四个 fetch 函数中的 urlopen(url) 替换为
  带标准浏览器 User-Agent 的 Request 对象。
  仅修改 HTTP 请求头，不改变任何业务逻辑。

---

## 修复规范（精确定位，禁止大范围改动）

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

### 修复位置1：fetch_vix()
修复前：
  with urllib.request.urlopen(url, timeout=8) as r:

修复后：
  req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
  with urllib.request.urlopen(req, timeout=8) as r:

### 修复位置2：fetch_tnx()
同上

### 修复位置3：fetch_spx_change()
同上

### 修复位置4：fetch_btc_change()
同上

---

## ACCEPTANCE_CRITERIA

1. daily_data_fetch.py 修复后大小已记录
2. governance_runtime.py 前置检查通过
3. Codex 环境 dry-run 测试：
   至少1项 OK（证明 User-Agent 修复有效）
   注：Codex 环境可能仍有网络限制，
       以用户本地验证为主要验收标准
4. 用户本地重新运行 --dry-run：
   OK 项数量 ≥ 3
5. AUTO_READY 判定已写入验收包：
   OK≥3 → AUTO_READY: YES
   OK<3 → AUTO_READY: NO + 新增诊断
6. 验收包 12 项字段完整
7. ChatGPT 明确输出 PASS

---

## CLOSE_CONDITION

1. daily_data_fetch.py 四处修复完成 ✓
2. 用户本地 OK ≥ 3 ✓
3. AUTO_READY: YES 写入验收包 ✓
4. 验收包 12 项字段完整 ✓
5. ChatGPT 输出 PASS ✓

---

## CODEX_EXECUTION

步骤0：governance_runtime.py 前置检查
  python scripts/governance_runtime.py \
    --task-id "TASK-2026-06-10-021" \
    --stage "implementation" \
    --approved "true" \
    --executor "Codex" \
    --acceptor "ChatGPT" \
    --thread "AI投研总控台 + 正式日报生产" \
    --task-type "governance" \
    --affects-account "false"

步骤1：读取现有 daily_data_fetch.py
  路径：G:\我的云端硬盘\AI_Investment_System\scripts\daily_data_fetch.py
  记录修复前文件大小

步骤2：在文件顶部常量区新增
  BROWSER_UA = (
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36"
  )

步骤3：修复四处 urlopen 调用
  fetch_vix() / fetch_tnx() / fetch_spx_change() / fetch_btc_change()
  每处将 urlopen(url, timeout=8)
  替换为 urlopen(Request(url, headers={"User-Agent": BROWSER_UA}), timeout=8)
  禁止修改任何其他代码

步骤4：记录修复后文件大小

步骤5：Codex 环境 dry-run 测试
  python scripts/daily_data_fetch.py --dry-run
  记录实际输出和 OK/DATA_GAP 数量

步骤6：生成验收包
  路径：G:\我的云端硬盘\AI_Investment_System\reports\validation\
        task-2026-06-10-021_validation_package.md
  须含：
    section 1：governance_runtime 前置检查
    section 2：修复前后文件大小对比
    section 3：四处修复位置确认（逐一列出）
    section 4：Codex 环境 dry-run 结果
    section 5：AUTO_READY 预判
    section 6：用户本地验证指引
    section 7：12项标准验收字段

---

## 用户本地验证（Codex 验收包生成后）

Codex 完成修复后，用户在本地运行：
  python scripts/daily_data_fetch.py --dry-run

将结果发回，Claude 更新 AUTO_READY 判定。

---

## 禁止事项

禁止修改 fetch 函数中 urlopen 以外的任何代码
禁止修改 skill_gate.py / governance_runtime.py
禁止修改 dashboard.html
禁止生成日报
禁止涉及账户操作
禁止自动下单
禁止自行最终验收
禁止在用户本地验证前宣布 AUTO_READY: YES
