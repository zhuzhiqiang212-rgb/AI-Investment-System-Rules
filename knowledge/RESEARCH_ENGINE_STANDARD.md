# RESEARCH_ENGINE_STANDARD
# V6研报系统标准 V1.3
# 版本: V1.3（新增Research Draft Repository规则，BUG-014修复）
# 生效时间: 2026-06-16 JST
# 审批人: ChatGPT V6
# 废弃: V1.0 / V1.1 / V1.2（以本版本为准）

---

## 零、机会发现优先原则

研报必须同等回答机会与风险。研报三部分必须同时存在：
  第一部分: 风险分析（不可省略）
  第二部分: 机会判断（不可省略，不得弱化）
  第三部分: 行动计划（不可省略，必须具体到账户和标的）

---

## 一、研报职责边界（V1.2继承）

Claude 负责: 研究分析、生成Markdown正文、维护research_index、将草稿push到GitHub research_drafts/
Codex 负责: fetch GitHub Raw链接读取草稿、本地生成PDF、写入桌面两路径、同步GitHub
ChatGPT V6 负责: 制度审批、内容质量验收、发布最终裁决
用户 负责: 打开研报阅读、做投资决策、截图确认可读

禁止: Claude通过base64传输二进制PDF
禁止: 要求用户下载/复制/搬运文件
禁止: 以文件存在代替用户可读作为发布条件

---

## 二、用户可读验收原则（V1.2继承）

文件存在 ≠ 发布成功
用户能打开 + 用户能阅读 + 用户截图确认 = 正式发布

验收顺序:
步骤1: Claude生成Markdown → 步骤2: push到GitHub research_drafts/
步骤3: ChatGPT V6审阅 → 步骤4: Codex fetch Raw → 本地生成PDF → 写入桌面
步骤5: 步骤3.5双路径SHA256验证 → 步骤6: 用户WPS打开截图
步骤7: ChatGPT V6最终确认 → 步骤8: research_index更新为Published

---

## 三、Research Draft Repository规则（V1.3新增，BUG-014修复）

### 研报草稿存储位置

GitHub仓库: AI-Investment-System-Rules
目录: research_drafts/
文件格式: RESEARCH-XXX.md + RESEARCH-XXX.meta.json

### 为什么必须用GitHub（永久制度）

Drive私有文件无法被Codex可靠读取（返回Google登录页/400错误，RESEARCH-001和RESEARCH-002均已证明）。
GitHub Raw链接无需认证，100%可靠，是Codex读取研报草稿的唯一正确方式。

### 禁止事项（永久生效）

禁止: 通过Drive文件ID让Codex读取研报内容
禁止: 将Drive私有文件作为Codex的PDF生成输入源
禁止: Codex执行卡中出现Drive文件ID作为研报内容来源

### 正确流程

Claude生成研报Markdown → push到GitHub research_drafts/RESEARCH-XXX.md
    ↓
Codex fetch Raw链接:
https://raw.githubusercontent.com/zhuzhiqiang212-rgb/AI-Investment-System-Rules/main/research_drafts/RESEARCH-XXX.md
    ↓
Codex本地生成PDF → 写入桌面两路径 → 步骤3.5验证

### Drive的定位（变更）

Drive用途: 备份（Claude写入，仅供人工查阅）
Drive不可用于: Codex读取研报草稿
GitHub用途: 研报草稿SSOT + Codex唯一输入源

### Codex执行卡规范（每次研报PDF生成必须遵守）

执行卡必须包含:
  GitHub Raw URL: https://raw.githubusercontent.com/zhuzhiqiang212-rgb/AI-Investment-System-Rules/main/research_drafts/RESEARCH-XXX.md
  验证关键词（用于确认读取内容正确）

执行卡禁止包含:
  Drive文件ID作为研报内容来源

---

## 四、研报生成流程 V1.1（更新版）

阶段1: Claude生成研报Markdown正文
阶段2: Claude发执行卡→Codex将Markdown push到GitHub research_drafts/
阶段3: Claude fetch Raw验证内容正确（系统自证）
阶段4: ChatGPT V6 fetch Raw审阅内容
阶段5: 批准后→Codex fetch Raw生成PDF→写入桌面→步骤3.5验证
阶段6: 用户WPS打开截图确认
阶段7: ChatGPT V6最终确认→Claude更新research_index

---

## 五、研报类型定义（继承V1.2）

类型1: 事件专题研报 | 触发: ★★★★以上事件在3日内
类型2: 个股深度研报 | 触发: 浮盈>+50%或浮亏<-30%
类型3: 趋势轮动研报 | 触发: 每周五/子周期独立强势
类型4: 进攻机会研报 | 触发: 周期升级BULL A级
类型5: 月度归因报告 | 触发: 每月末

---

## 六、发布状态定义（六状态体系，V1.3更新）

| 状态 | 含义 | 日报可引用？|
|------|------|-----------|
| Draft | Claude正在生成或修订中 | 否 |
| Review | 已提交ChatGPT V6审阅 | 否 |
| Published Failed | 发布流程失败 | 否 |
| Published(Beta-1) | 通过用户WPS可读验收+ChatGPT V6批准 | 是 |
| Expired | 已过有效期，禁止引用 | 否 |
| Archived | 已归档，超期不再参考 | 否 |

---

## 七、研报禁止事项

禁止: 只写风险不写机会
禁止: Claude通过base64传输二进制文件
禁止: 要求用户参与任何文件操作
禁止: 以文件存在代替用户可读作为发布条件
禁止: Drive文件ID作为Codex研报输入源（BUG-014）
禁止: Codex生成研报正文（研报正文由Claude生成）
