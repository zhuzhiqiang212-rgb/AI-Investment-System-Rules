# validation_package_output_standard_v1.md
# AI投研总控台 V4 统一验收包输出标准

生效日期：2026-06-09 JST
制定人：Claude
适用范围：Claude / Codex / Cursor / Skills / ChatGPT
状态：ACTIVE — 自本文档起强制执行

---

## 第一部分：核心规则

任何正式任务结束后，必须输出标准验收包。

没有验收包 = 任务未完成。
没有发给谁 = 任务未完成。
没有下一步唯一动作 = 任务未完成。
没有可直接执行指令 = 任务未完成。
执行人 = 最终验收人 = 违规（生成者不能自验）。

---

## 第二部分：标准验收包格式

所有正式任务必须输出以下格式，字段缺一不可：

文件名：{任务名称}_validation_package_v{版本}.md
文件路径：AI_Investment_System/reports/validation/{文件名}
文件大小：{实际写入后的字节数}
最后修改时间：{写入时间} JST
状态：PASS / PARTIAL / FAIL
执行人：{实际执行角色}
预检人：{预检角色}
最终验收人：ChatGPT / AI投研总控台 V4
发给谁：ChatGPT / AI投研总控台 V4
下一步唯一动作：{一句话，只有一个动作}
可直接执行指令：{完整指令，无需额外解释，可直接复制执行}
是否成功生成：YES / NO

---

## 第三部分：适用任务类型

以下所有任务类型结束时必须输出标准验收包：

- 日报生成任务
- 质量审查任务（Quality Review）
- 角色治理审计任务（Role Governance Audit）
- 预检任务（Precheck）
- 规则/文档生成任务
- Dashboard 更新任务
- 账户数据更新任务
- Skills 更新任务
- 系统状态更新任务
- 任何由 Claude / Codex / Cursor 发起的正式执行任务

---

## 第四部分：各角色强制执行规则

### Claude

执行条件：每次在对话中完成正式任务后。
输出位置：对话末尾，作为任务结束标志。
格式要求：使用本标准的全部字段，不得省略。
文件写入：Claude 无 Drive 写入权限；验收包正文输出在对话中，
          需由用户手动保存或发给 Codex 写入。
硬性禁止：不得只输出分析结论而不输出验收包。
         不得只输出建议而不输出验收包。
         不得在验收包外额外添加多个独立复制区。

### Codex

执行条件：每次完成文件写入、日报生成、规则更新后。
输出位置：写入验收包文件到 AI_Investment_System/reports/validation/
          同时在对话中输出验收包摘要（文件名/路径/大小/时间/状态）。
格式要求：验收包文件本身必须是完整的标准格式文档。
硬性禁止：不得把验收包内容只输出在对话中而不写入文件。
         不得自己验收自己生成的文件。
         不得把「文件写入成功」等同于「任务完成」。

### Cursor

执行条件：每次完成工程任务（Dashboard 更新/脚本维护/代码修改）后。
输出位置：生成独立验收包文件，写入 AI_Investment_System/reports/validation/
格式要求：工程说明可以独立存在；但验收包必须单独生成且符合本标准格式。
硬性禁止：不得把 GitHub PR 描述当作验收包。
         不得把工程说明和验收包混合在同一文档中。
         不得修改投资结论、账户数据或自行最终验收。

### Skills

执行条件：每次 Skill 文件被更新或新建后。
输出位置：对应的验收包文件写入 AI_Investment_System/reports/validation/
格式要求：Skills 本身是规则文档，不是验收包；
          Skill 更新完成后必须单独生成一个验收包。
硬性禁止：不得把 Skill 文件的存在当作验收包。
         Skills 不执行任何操作，只定义规则。

### ChatGPT

执行条件：每次完成最终验收判断后。
输出位置：在对话中明确输出验收结论，格式符合本标准。
格式要求：验收结论必须包含：状态（PASS/PARTIAL/FAIL）+
          具体不通过原因（如为 PARTIAL/FAIL）+
          下一步唯一动作 + 可直接执行指令。
硬性禁止：不得只说「通过」而不说明下一步唯一动作。
         不得用结构性检查替代用户满意度判断。
         不得在未独立判断「用户是否能 3 分钟内完成决策」的情况下标绿日报任务。

---

## 第五部分：硬阻断条件

以下任一情况出现，当前任务判定为未完成，必须重新执行：

1. 任务结束时没有验收包输出
2. 验收包缺少「发给谁」字段
3. 验收包缺少「下一步唯一动作」字段
4. 验收包缺少「可直接执行指令」字段
5. 执行人与最终验收人为同一角色（自验）
6. 验收包只存在于对话中而没有写入 Drive（Codex/Cursor 任务）
7. 验收包字段不完整（少于本标准规定的 12 个必填字段）

---

## 第六部分：验收包文件命名规范

格式：{任务名称_缩写}_{日期}_validation_package_v{版本}.md

示例：
- daily_report_20260609_validation_package_v1.md
- role_drift_audit_20260609_validation_package_v1.md
- dashboard_update_20260609_validation_package_v1.md
- skill_update_20260609_validation_package_v1.md

存放路径（统一）：
AI_Investment_System/reports/validation/

---

## 第七部分：最小合格验收包示例

以下为最小合格验收包，所有字段必须存在：

文件名：example_task_validation_package_v1.md
文件路径：AI_Investment_System/reports/validation/example_task_validation_package_v1.md
文件大小：2,048 bytes
最后修改时间：2026-06-09 09:00:00 JST
状态：PASS
执行人：Codex
预检人：Claude
最终验收人：ChatGPT / AI投研总控台 V4
发给谁：ChatGPT / AI投研总控台 V4
下一步唯一动作：ChatGPT 审核本验收包，确认是否允许进入下一阶段
可直接执行指令：请 ChatGPT 审核 AI_Investment_System/reports/validation/example_task_validation_package_v1.md，判断状态是否为 PASS，并给出下一步唯一动作。
是否成功生成：YES

---

## 第八部分：与其他标准的关系

本标准（Validation Package Output Standard V1）与以下标准共同构成
AI投研总控台 V4 的交付体系：

- user_report_constitution_v1.md（日报内容质量标准）
- validation_output_standard_v2.md（验收包格式标准）
- role_separation_rules.md（角色边界规则）

优先级：当本标准与其他标准冲突时，以最严格的要求为准。

---

VALIDATION_PACKAGE_STANDARD_READY: YES

状态：PASS
执行人：Claude（指令生成）/ Codex（文件写入）
预检人：Claude
最终验收人：ChatGPT / AI投研总控台 V4
发给谁：ChatGPT / AI投研总控台 V4
下一步唯一动作：ChatGPT 审核本文件，确认
  validation_package_output_standard_v1.md 是否正式生效，
  并通知所有角色（Claude/Codex/Cursor/Skills）从即日起强制执行本标准
可直接执行指令：请 ChatGPT 审核
  AI_Investment_System/docs/validation_package_output_standard_v1.md，
  判断是否正式生效，并输出通知：
  「Validation Package Output Standard V1 自 2026-06-09 起对所有角色强制生效」。
  不要修改账户数据。不要生成日报。只做验收和生效确认。

---

## Codex 写入完成后，只输出：

文件名：validation_package_output_standard_v1.md
文件路径：AI_Investment_System/docs/validation_package_output_standard_v1.md
文件大小：[实际大小]
最后修改时间：[写入时间] JST
是否成功生成：YES / NO