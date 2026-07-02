# V6最终目标方案 V1.1（待ChatGPT V6审批）
# 基于V1.0，五项增强修订
# 日期：2026-06-16 JST

---

## 目标

用最高质量证据链，发现最有价值机会，形成最优投资决策

---

## 七层引擎

Layer 1  EVENT ENGINE（触发层）
  回答：什么事件正在发生或即将发生
  原则：重大事件自动驱动，用户不负责提醒
  输出：事件预警（T-3日）/ 事件分析（T-2至T-1）/ 事件总控（T0）/ 事件复盘（T+1）
  现状：雏形存在，自动预警未实现（BUG-017 Open）

Layer 2  TREND ENGINE（背景层）
  回答：钱往哪里流，主线如何轮动
  输出：当前主线资金流向 / 主线内部轮动信号 / 主线切换触发条件
  现状：未建设（Phase 3）

Layer 3  OPPORTUNITY ENGINE（筛选层）
  回答：哪个标的值得行动，下一轮机会在哪里
  输出：当前机会排序（A/B/C级）/ 下一主线 / 下一轮资金流方向 / 下一轮进攻方向
  现状：未建设（Phase 3）

Layer 4  EVIDENCE ENGINE（验证层）
  回答：为什么这样判断
  原则：Evidence View优先，Evidence Database后置
  输出：Evidence View（支持证据/反对证据/权重/失效条件/最终结论）
  现状：完全缺失，Phase 2唯一目标

Layer 5  DECISION ENGINE（输出层）
  回答：今天做什么，为什么今天这么做
  输出：00B_今日总控页（含"为什么"指向Evidence具体位置）
  现状：形式完成，"为什么"缺失，BUG-018 Open

Layer 6  EXECUTION ENGINE（行动层）
  回答：买多少 / 卖多少 / 什么时候
  输出：执行卡
  现状：执行卡存在，非系统性，需实时价格接入（Phase 3）

Layer 7  VALIDATION ENGINE（验证层）
  回答：体系的判断准不准
  输出：预测→结果→命中率→归因分析
  现状：未建设（Phase 4）

---

## 四个阶段

Phase 1  Delivery Engine  ✅完成
Phase 2  Evidence Engine  ⏳当前（Phase 2禁止Trend/Opportunity/Execution扩展）
Phase 3  Trend+Opportunity+Execution  🔒冻结
Phase 4  Validation Engine  🔒冻结

---

## V1.0→V1.1差异

Opportunity Engine：增加下一主线/下一轮资金流/下一轮进攻方向
Trend Engine：增加轮动信号/主线切换触发条件
Evidence Engine：不变（方向已确认正确）
Event Engine：增加核心原则「重大事件自动驱动，用户不负责提醒」
Decision Engine：增加「为什么今天这么做」，指向Evidence具体位置
