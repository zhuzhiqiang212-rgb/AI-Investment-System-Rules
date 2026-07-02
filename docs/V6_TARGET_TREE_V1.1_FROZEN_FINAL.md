# V6最终目标方案 V1.1（正式冻结版）
# ChatGPT V6批准 | 日期：2026-06-16 JST
# Phase 2方向锁定

---

## 根本目标

用最高质量证据链，发现最有价值机会，形成最优投资决策。

---

## 体系定位（冻结）

V1.1是高质量分析系统蓝图，不是完整机会发现系统。
机会发现系统在Phase 3解决。
Phase 2禁止同时建设主动机会发现系统。

---

## 七层引擎（冻结）

Layer 1  EVENT ENGINE（触发层）
  回答：什么事件正在发生或即将发生
  原则：重大事件自动驱动，用户不负责提醒
  输出：事件预警（T-3日）/ 事件分析（T-2至T-1）/ 事件总控（T0）/ 事件复盘（T+1）
  现状：雏形存在，自动预警未实现（BUG-017）

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
  输出：Evidence View（证据权重矩阵）
    支持证据（描述/来源/数据/时间/权重★/信息源等级）
    反对证据（同上）
    证据权重评估
    信息源等级（一手原文 / 分析性来源 / 推断性来源）
    市场共识 vs 超额认知
    失效条件（具体数字，可当天验证）
    横向比较：为什么这个机会仍值得关注，是否有更好的替代机会
    最终结论（一句话，放最后）
  硬性边界：每张Evidence View必须包含横向比较，不得退化为持仓合理化系统
  现状：完全缺失，Phase 2唯一目标

Layer 5  DECISION ENGINE（输出层）
  回答：今天做什么，为什么今天这么做
  输出：00B_今日总控页
    今天做什么
    为什么这么做（指向Evidence Engine具体位置）
    今天不做什么
    最大风险
    最大机会
    当前整体姿态（防守/中性/进攻）+原因
    下一动作
  现状：形式完成，为什么缺失，BUG-018 Open

Layer 6  EXECUTION ENGINE（行动层）
  回答：买多少 / 卖多少 / 什么时候
  输出：执行卡
  现状：执行卡存在，非系统性（Phase 3）

Layer 7  VALIDATION ENGINE（验证层）
  回答：体系的判断准不准，体系是否在进步
  输出：预测→结果→命中率→归因分析
  现状：未建设（Phase 4）

---

## 用户最终看到

00_今日日报      ← 发生什么（Event Engine）
00B_今日总控页   ← 今天做什么+为什么（Decision Engine）
01_最新研报      ← 为什么这样办，包含证据链和横向比较（Evidence Engine）

---

## 四个阶段（冻结）

Phase 1  Delivery Engine  ✅ 完成
Phase 2  Evidence Engine  ⏳ 当前（唯一目标）
Phase 3  Trend + Opportunity + 外向扫描 + Execution  🔒 冻结
Phase 4  Validation Engine  🔒 冻结

---

## Phase 2 允许做（ChatGPT V6批准）

1. Evidence View最终用户界面设计
2. RESEARCH-002/003/004各抽一个核心结论，做Evidence View样板
3. 每张Evidence View必须包含：
   - 支持证据
   - 反对证据
   - 证据权重
   - 信息源等级
   - 市场共识 vs 超额认知
   - 失效条件
   - 横向比较（为什么这个机会仍值得关注，是否有更好的替代机会）
   - 最终结论

## Phase 2 禁止做

- 主动全市场扫描
- Trend Engine建设
- Opportunity Engine建设
- RESEARCH-005
- 新增PDF
- 新增制度
- Evidence Database
- 大量evidence文件

---

## Phase 3 再处理（冻结，不得提前）

SpaceX / 机器人 / ASIC / 核电 / 国防AI 等用户未知机会的主动发现问题。

---

## Evidence View硬性边界（ChatGPT V6补充）

每一张Evidence View必须包含横向比较视角：
"这个标的/机会，相对其他可选机会，为什么仍然值得关注？"

Phase 2的分析虽然围绕已知标的，但必须加入横向比较，
让用户知道：有没有比当前持仓更好的机会。

---

## 冻结规则

1. 新想法先判断属于哪一层引擎，不立即实现
2. Phase 2期间禁止：Trend/Opportunity/Execution扩展
3. Evidence View用户验收通过前，不建立Evidence Database
4. 不再开放式建设
5. Phase 2不得退化为持仓合理化系统

---

## 当前状态

等待：FOMC结果（预计2026-06-18 JST）
FOMC后：RESEARCH-004事件验证复盘
复盘后：Evidence View第一张样板（从RESEARCH-003软银开始）
