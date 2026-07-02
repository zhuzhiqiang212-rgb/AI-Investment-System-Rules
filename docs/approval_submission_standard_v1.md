# APPROVAL_SUBMISSION_STANDARD_V1
# 统一 ChatGPT 审批提交格式

版本: V1.0
生效时间: 2026-06-10 JST
制度层级: AI_PROJECT_GOVERNANCE_V2 补充条款
关联 Addendum: governance_v2_addendum_task_package_and_initiator.md
文件路径: AI_Investment_System/docs/approval_submission_standard_v1.md

---

## 1. 制度目的

禁止用户自行判断向 ChatGPT 提交什么内容。
Claude 在 PRE_ACCEPTANCE 阶段自动判断 APPROVAL_LEVEL，
并按对应 Level 的固定格式输出提交内容。
用户只需将 Claude 输出的提交块转发给 ChatGPT，无需额外判断。

---

## 2. APPROVAL_LEVEL 判断规则

Claude 在 PRE_ACCEPTANCE 阶段必须自动判断并输出 APPROVAL_LEVEL。
禁止用户自行判断。

| APPROVAL_LEVEL | 任务类型 | 典型例子 |
|---------------|---------|---------|
| LEVEL-1 | 治理制度类 | Governance / Task Package / GitHub Rule / Skill Gate / 流程制度 / Addendum |
| LEVEL-2 | 策略类 | 资产配置引擎 / 仓位引擎 / 买入触发器 / 止盈系统 / 周期定位 / 日报结构 |
| LEVEL-3 | 代码类 | skill_gate.py / dashboard.html / report_generator.py / 任何脚本修改 |

判断优先级：LEVEL-3 > LEVEL-2 > LEVEL-1
（任务同时涉及代码和制度时，取最高级别）

---

## 3. LEVEL-1 提交格式（治理制度类）

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
APPROVAL_LEVEL   : LEVEL-1
TASK_ID          : [任务编号]
文件名            : [文件名]
文件路径          : [Drive 完整路径]
文件大小          : [字节数]
Drive ID         : [文件 ID]
最后修改时间      : [JST 时间戳]
Claude 预检结果   : PASS / INCOMPLETE / FAIL
发给谁            : ChatGPT / AI投研总控台 V4
下一步唯一动作    : [一句话说明]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

无需复制文件正文。ChatGPT 通过 Drive ID 自行读取。

---

## 4. LEVEL-2 提交格式（策略类）

LEVEL-1 全部字段，再附加：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[LEVEL-1 全部字段]
────────────────────────────────
策略摘要          :
  [100字以内核心策略说明]
策略文件内容      :
  [策略文件全文，或关键章节全文]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 5. LEVEL-3 提交格式（代码类）

LEVEL-1 全部字段，再附加：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[LEVEL-1 全部字段]
────────────────────────────────
代码变更说明      :
  [修改了什么，为什么修改]
代码内容          :
  [修改代码全文]
  或
  [代码 diff]
  或
  [验收包关键内容（含测试结果）]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 6. Claude PRE_ACCEPTANCE 输出规范

Claude 在 PRE_ACCEPTANCE 阶段必须：

1. 自动判断 APPROVAL_LEVEL（LEVEL-1 / LEVEL-2 / LEVEL-3）
2. 明确输出 `APPROVAL_LEVEL: LEVEL-X`
3. 按对应 Level 格式输出完整提交块
4. 在提交块末尾附注：`[以上内容可直接转发给 ChatGPT]`

禁止：
- 只输出文件名而不输出完整提交块
- 要求用户自行判断 Level
- 输出超出对应 Level 要求的冗余内容（LEVEL-1 禁止附加正文）

---

## 7. 违规判定

| 违规场景 | 结果 |
|---------|------|
| Claude 未输出 APPROVAL_LEVEL | PRE_ACCEPTANCE = INCOMPLETE |
| Claude 输出 LEVEL 错误（低报） | PRE_ACCEPTANCE = INCOMPLETE |
| LEVEL-1 附加了不必要正文 | 格式违规，须重新输出 |
| LEVEL-2/3 缺少策略/代码内容 | PRE_ACCEPTANCE = INCOMPLETE |
| 用户自行判断 Level | 无效，须由 Claude 重新判断输出 |
