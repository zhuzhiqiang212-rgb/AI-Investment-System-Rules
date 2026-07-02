# CODEX EXECUTION ORDER
# TASK-2026-06-10-014 REV-A · READY_FOR_IMPLEMENTATION

【执行对话】AI投研总控台 + 正式日报生产
禁止执行对话: 【维护对话】AI系统维护

TASK_ID: TASK-2026-06-10-014 REV-A
任务名称: P0_MVP_DEPLOYMENT_V1
执行人: Codex
验收人: ChatGPT / AI投研总控台 V4
审批状态: APPROVED（ChatGPT，2026-06-10）
TASK_PACKAGE路径: AI_Investment_System/docs/tasks/TASK-2026-06-10-014-REV-A_TASK_PACKAGE.md
TASK_PACKAGE Drive ID: 1B6ad_fi4cRD9P2Vpv7GDvkCKN0UWIoFT

规则: Codex 只依据 Drive 中的 TASK_PACKAGE 执行。
      本文件是执行授权凭证，不是执行内容来源。
      执行内容以 TASK_PACKAGE（ID: 1B6ad_fi4cRD9P2Vpv7GDvkCKN0UWIoFT）为准。

---

## 执行授权

本执行包由 Claude 编写，经 ChatGPT / AI投研总控台 V4 审批通过。
授权 Codex 按 TASK_PACKAGE REV-A 执行以下任务。

---

## 执行摘要

部署 P0 MVP 四份文件到 Drive：

文件1: SYSTEM_INDEX.md
  路径: G:\我的云端硬盘\AI_Investment_System\docs\SYSTEM_INDEX.md
  内容来源: TASK_PACKAGE REV-A 第"文件1"规范

文件2: daily_briefing_template_v1.md（唯一入口）
  路径: G:\我的云端硬盘\AI_Investment_System\docs\daily_briefing_template_v1.md
  内容来源: TASK_PACKAGE REV-A 第"文件2"规范

文件3: trade_record_log_v1.md
  路径: G:\我的云端硬盘\AI_Investment_System\docs\trade_record_log_v1.md
  内容来源: TASK_PACKAGE REV-A 第"文件3"规范

文件4: P0_MVP_USER_ACCEPTANCE_PACKAGE.md（用户侧验收包）
  路径: G:\我的云端硬盘\AI_Investment_System\reports\validation\P0_MVP_USER_ACCEPTANCE_PACKAGE.md
  内容来源: TASK_PACKAGE REV-A 第"文件4"规范

---

## 执行顺序

步骤1: 读取 TASK_PACKAGE（Drive ID: 1B6ad_fi4cRD9P2Vpv7GDvkCKN0UWIoFT）
       确认内容完整，准备生成四份文件

步骤2: 生成并写入 SYSTEM_INDEX.md
       写入后记录实际文件大小和修改时间

步骤3: 生成并写入 daily_briefing_template_v1.md
       写入后记录实际文件大小和修改时间

步骤4: 生成并写入 trade_record_log_v1.md
       写入后记录实际文件大小和修改时间

步骤5: 更新 SYSTEM_INDEX.md 中的"文件更新时间区"
       填入步骤2-4的实际修改时间

步骤6: 生成 P0_MVP_USER_ACCEPTANCE_PACKAGE.md
       填写技术验收三份文件实际数据
       逐项检查 U1-U7，填写 YES/NO
       根据结果填写 MVP_READY: YES / NO
       任意项 NO → 填写 MVP_NOT_READY，禁止填 MVP_READY: YES

步骤7: 写入 P0_MVP_USER_ACCEPTANCE_PACKAGE.md
       路径: reports/validation/

---

## 验收包要求

完成后生成:
  task-2026-06-10-014_validation_package.md
  路径: G:\我的云端硬盘\AI_Investment_System\reports\validation\

验收包必须包含:
  section 1: 四份文件写入结果（文件名/路径/大小/修改时间/状态）
  section 2: U1-U7七项逐项结果（YES/NO）
  section 3: MVP_READY: YES / NO 判定
  section 4: 12项验收字段

---

## 禁止事项

禁止修改任何策略内容
禁止修改 skill_gate.py 或 dashboard.html
禁止生成日报
禁止涉及账户操作
禁止自行最终验收
禁止在 U1-U7 任意项为 NO 时填写 MVP_READY: YES
禁止写入 P0 四份以外的任何文件（P1/P2 留待后续任务）
禁止在任何文件中修改已批准的策略内容

---

## CLOSE_CONDITION（供 ChatGPT 验收使用）

1. 四份文件全部写入正确路径 ✓
2. U1-U7全部YES，MVP_READY: YES ✓
3. task-2026-06-10-014_validation_package.md 生成，12项字段完整 ✓
4. ChatGPT 输出 PASS 及 TASK_CLOSED ✓

若 U1-U7 任意项 NO:
  状态: MVP_NOT_READY
  ChatGPT 指明失败项
  Codex 修复后重新生成验收包
  不得 CLOSE
