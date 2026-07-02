# RESEARCH_ENGINE_STANDARD
# V6研报系统标准 V1.2
# 版本: V1.2（研报职责边界 + 用户可读验收原则 + Markdown→PDF流程）
# 生效时间: 2026-06-15 JST
# 审批人: ChatGPT V6
# SSOT: GitHub knowledge/ + Drive知识库目录
# 废弃: V1.0 / V1.1（以本版本为准）

---

## 零、机会发现优先原则（V1.1继承）

研报不仅负责风险分析。
研报必须同等回答机会与风险。

研报必须回答以下问题（不得只回答风险）:
  哪里有机会 / 为什么是机会 / 什么时候出手 / 什么时候放弃
  主线是什么 / 备选主线是什么 / 资金从哪里流向哪里
  当前是防守期还是进攻期
  是否属于强趋势窗口期
  是否属于A级主动出击机会
  是否属于B级埋伏机会

研报三部分必须同时存在:
  第一部分: 风险分析（不可省略）
  第二部分: 机会判断（不可省略，不得弱化）
  第三部分: 行动计划（不可省略，必须具体到账户和标的）

---

## 一、研报职责边界（V1.2新增，最高优先级）

### 职责定义

**Claude 负责:**
  研究与分析（唯一研究者）
  以Markdown格式生成研报正文
  将Markdown文本写入Drive drafts目录（文本文件，无大小限制，传输可靠）
  维护research_index状态（草稿→审阅→发布）
  将研报结论一行写回日报配置

**Codex 负责:**
  从Drive读取研报Markdown文本
  在本地生成PDF（使用wqy-zenhei.ttc字体）
  将PDF写入桌面两个路径
  将research_index.md同步至GitHub knowledge/
  报告完成状态（文件大小、两路径确认）

**ChatGPT V6 负责:**
  制度审批
  研报内容质量验收
  发布最终裁决

**用户 负责:**
  打开研报（WPS双击）
  阅读研报内容
  做投资决策
  截图确认可读（验收步骤）

### 禁止事项（永久生效）

禁止: Claude通过base64传输二进制PDF文件（传输不可靠）
禁止: 要求用户下载文件
禁止: 要求用户复制文件
禁止: 要求用户搬运文件
禁止: 要求用户通知Codex
禁止: 以"文件存在"代替"用户可读"作为发布条件

---

## 二、用户可读验收原则（V1.2新增）

### 核心原则

文件存在 ≠ 发布成功
用户能打开 + 用户能阅读 + 用户截图确认 = 正式发布

### 验收顺序（必须严格遵守）

```
步骤1: 研报生成（Claude输出Markdown）
步骤2: 写入Drive drafts目录（Claude执行，文本写入）
步骤3: ChatGPT V6审阅内容（通过Drive链接或对话Markdown）
步骤4: 批准后Codex生成PDF并写入桌面两路径
步骤5: Codex报告文件大小（应>50KB）和路径确认
步骤6: 用户WPS打开，截图确认中文正常显示
步骤7: ChatGPT V6最终确认发布
步骤8: research_index状态更新为Published
步骤9: 研报结论写回日报
```

### 发布状态定义

| 状态 | 含义 | 用户可读？|
|------|------|---------|
| Draft | Claude正在生成 | 否 |
| Review | 内容提交ChatGPT V6审阅 | 否 |
| Published Failed | 发布流程失败（文件损坏/不可读）| 否 |
| Published (Beta-1) | 通过用户可读验收 + ChatGPT V6批准 | 是 |
| Published (Stable) | 模板已定稿，流程完全验证 | 是 |
| Archived | 已归档，超期不再参考 | 存档 |

---

## 三、研报生成流程 V1.0（修订版，V1.2生效）

### Markdown → PDF 流程（唯一正确流程）

```
[阶段1] Claude生成研报Markdown
  Claude在对话中完成研报分析
  输出Markdown格式（纯文本，可靠传输）
  写入Drive: AI_Investment_System/reports/drafts/
  文件名: RESEARCH-XXX_draft.md

[阶段2] ChatGPT V6审阅
  通过Drive读取或对话Markdown审阅
  审阅三部分：风险/机会/行动计划
  批准后进入下一阶段

[阶段3] Codex发布执行（单条指令，一次完成）
  从Drive读取 RESEARCH-XXX_draft.md
  本地生成PDF（wqy-zenhei.ttc字体，确保中文可读）
  写入路径1: 桌面\研报\[类型]\[文件名].pdf
  写入路径2: 桌面\股票分析与研究\[文件名].pdf
  同步research_index.md至GitHub knowledge/
  报告：文件大小 / 两路径状态

[阶段4] 用户可读验收
  用户双击PDF，WPS打开
  确认中文正常显示
  截图发回对话

[阶段5] 正式发布
  ChatGPT V6确认发布
  Claude更新research_index状态为Published
  Claude将研报结论一行写入日报配置
```

### 禁止的传输方式

禁止: Claude通过base64将PDF传输到Drive（大文件截断导致损坏）
禁止: 要求用户手动传输文件
正确: Claude写Markdown文本 → Codex本地生成PDF → 本地写入桌面

---

## 四、研报类型定义（继承V1.1）

### 类型1: 事件专题研报
触发条件: 事件日历★★★★以上事件在未来3日内
命名规则: 事件专题_[事件名]_YYYY-MM-DD.pdf
Markdown草稿: RESEARCH-XXX_事件专题_[事件名]_draft.md

### 类型2: 个股深度研报
触发条件: 浮盈>+50% 或 浮亏<-30% 或用户请求
命名规则: 个股研究_[代码]_[主题]_YYYY-MM-DD.pdf

### 类型3: 趋势轮动研报
触发条件: 每周五 / 子周期独立强势
命名规则: 趋势轮动_YYYY-WXX.pdf

### 类型4: 进攻机会研报
触发条件: 周期升级BULL A级 / 强趋势窗口期
命名规则: 进攻机会_[标的板块]_YYYY-MM-DD.pdf

### 类型5: 月度归因报告
触发条件: 每月末
命名规则: 月度归因_YYYY-MM.pdf

---

## 五、事件驱动触发规则（继承V1.1）

| 触发条件 | 生成研报类型 | 优先级 |
|---------|------------|--------|
| 事件日历★★★★以上事件在未来3日内 | 事件专题研报 | P0 |
| 任一持仓浮亏 < -30% | 个股深度研报 | P0 |
| 总周期升级为BULL_MID A级 | 进攻机会研报 | P0 |
| 任一持仓浮盈 > +50% | 个股深度研报 | P1 |
| 子周期出现独立强势信号 | 趋势轮动研报 | P1 |
| 连续3日layer1为"观察" | 机会扫描研报 | P2 |
| 每周五 | 趋势轮动周报 | P1 |
| 每月末 | 月度归因报告 | P1 |

---

## 六、研报输出目录

Drive草稿路径:
  AI_Investment_System/reports/drafts/RESEARCH-XXX_draft.md

本地桌面路径（Codex写入）:
  C:\Users\zhu20\OneDrive\桌面\股票分析与研究\研报\事件专题\
  C:\Users\zhu20\OneDrive\桌面\股票分析与研究\研报\个股研究\
  C:\Users\zhu20\OneDrive\桌面\股票分析与研究\研报\趋势轮动\
  C:\Users\zhu20\OneDrive\桌面\股票分析与研究\研报\月度归因\

备用路径（Codex同时写入）:
  C:\Users\zhu20\OneDrive\桌面\股票分析与研究\[文件名].pdf

---

## 七、研报禁止事项（V1.2强化）

禁止: 只写风险不写机会
禁止: Claude通过base64传输二进制文件
禁止: 要求用户参与任何文件操作
禁止: 以文件存在代替用户可读作为发布条件
禁止: 未经用户WPS打开确认就宣布发布成功
禁止: Codex生成研报正文（研报正文由Claude生成）
禁止: 研报未经ChatGPT V6审批修改投资规则

---

## 八、RESEARCH-001状态说明

编号: RESEARCH-001
主题: BOJ议息专题 2026-06-16
研究内容: 通过（ChatGPT V6审批）
发布流程: 失败（base64传输导致PDF损坏）
当前状态: Published Failed
修复方案: 按本V1.2流程重新发布（Markdown→Codex→PDF→用户验收）
