# V6最终目标方案 V1.0（冻结版）
# 状态：ChatGPT V6正式批准，92/100
# 日期：2026-06-16 JST
# 冻结：是。新想法先判断属于哪一层，不立即实现。

---

## 根本目标

用最高质量证据链，发现最有价值机会，形成最优投资决策。

不是：生成日报、生成PDF、生成研报。这些只是工具。

---

## 四个阶段（冻结）

### Phase 1：Delivery Engine（已完成）
目标：把东西送到用户手里
完成内容：GitHub → Draft → PDF → 桌面 → 验收
评价：投研基础设施完成，不是投研完成
状态：Conditional Pass

### Phase 2：Evidence Engine（当前阶段）
目标：让用户知道"为什么"
核心输出：Evidence View（证据权重矩阵）
禁止：Trend Engine建设、Opportunity Engine建设、Execution Engine扩展
路径：Evidence View → 用户验收 → Evidence Database（顺序不得颠倒）
状态：待启动（FOMC复盘后）

### Phase 3：Trend Engine + Opportunity Engine
目标：找到别人没发现的机会
前提：Evidence Engine完成并通过验收

### Phase 4：Validation Engine
目标：证明体系是否真的有效
输出：预测 → 结果 → 命中率 → 归因
前提：Phase 3完成

---

## 七层引擎（冻结顺序）

Layer 1  EVENT ENGINE（触发层）
  回答：什么事件正在发生或即将发生
  输出：事件预警 / 事件分析 / 事件复盘
  现状：雏形存在（RESEARCH-004），自动预警未实现（BUG-017）

Layer 2  TREND ENGINE（背景层）
  回答：钱往哪里流（6-18个月视角）
  输出：主线 / 子主线 / 趋势排序
  现状：未建设（Phase 3）

Layer 3  OPPORTUNITY ENGINE（筛选层）
  回答：哪个标的值得行动
  输出：A级主动出击 / B级埋伏 / C级观察
  现状：未建设（Phase 3）

Layer 4  EVIDENCE ENGINE（验证层）
  回答：为什么这样判断
  输出：Evidence View（证据权重矩阵）
  结构：支持证据 / 反对证据 / 权重 / 失效条件 / 最终结论
  现状：完全缺失，Phase 2唯一目标

Layer 5  DECISION ENGINE（输出层）
  回答：今天怎么办
  输出：00B_今日总控页
  现状：形式完成，内容缺Evidence支撑，BUG-018 Open

Layer 6  EXECUTION ENGINE（行动层）
  回答：买多少 / 卖多少 / 什么时候
  输出：执行卡
  现状：执行卡存在，但非系统性，需实时价格接入（Phase 3）

Layer 7  VALIDATION ENGINE（验证层）
  回答：体系的判断准不准
  输出：命中率 / 归因分析 / 体系迭代
  现状：未建设（Phase 4）
  说明：没有Validation，永远不知道体系有没有进步

---

## 用户最终看到

00_今日日报      ← 发生什么（Event Engine输出）
00B_今日总控页   ← 今天怎么办（Decision Engine输出）
01_最新研报      ← 为什么这样办（Evidence Engine输出）

---

## Evidence View格式（冻结）

用户看到的是一张证据权重矩阵，不是多个文件。

结构：
  标的 + 当前结论
  支持证据（描述 / 来源 / 数据 / 时间 / 权重★1-5）
  反对证据（同上）
  权重评估（支持 vs 反对总权重对比）
  市场共识 vs 超额认知
  失效条件（具体数字，可当天验证）
  最终结论（一句话，放最后）

原则：
  View优先于Database
  结论放最后，不放开头
  失效条件必须是可验证的具体数字

---

## 冻结规则

1. 新想法先判断属于哪一层引擎，不立即实现
2. Phase 2期间禁止：Trend Engine建设、Opportunity Engine建设、Execution Engine扩展
3. Evidence View没有用户验收通过前，不建立Evidence Database
4. 不再开放式建设

---

## 当前状态

等待：FOMC结果（预计2026-06-18 JST）
FOMC后：RESEARCH-004事件验证复盘
复盘后：Evidence Engine第一张View（软银/RESEARCH-003）

禁止：启动RESEARCH-005 / 新增研报 / 新增PDF / 新增制度
