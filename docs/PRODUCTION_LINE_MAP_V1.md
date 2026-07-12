# PRODUCTION_LINE_MAP_V1：决策生产线总装接线图

> 状态：v1。目标是一眼看清进料、加工、质检、出料、复盘各设备如何接线。

## 一页总图

```text
进料口
  ├─ 资料入库：scripts/kb_intake_pipeline.py（半通：能搬近7天资料进 Knowledge_Base/incoming）
  └─ 研究预筛：scripts/research_intake_prescreen.py（通：能出 candidates_YYYYMMDD.json）
      ↓
加工线
  └─ 决策生产线：scripts/decision_line_build.py（骨架：生成20只标的决策卡，理解字段待 Claude 填）
      ↓
质检
  └─ 四道闸门：scripts/quality_chain_check.py（通：数据→估值→风险→动作→日报）
      ↓
出料
  └─ 日报：00_请先看这里/日报_2026-07-02_四账户完整版.html（通：正式完整日报）
      ↓
复盘
  └─ PDCA：docs/PDCA_REVIEW_FRAMEWORK_V1.md（骨架：明天起接次日/周/月/季/年复盘）
```

## 设备清单
| 环节 | 设备 | 文件 | 当前状态 | 说明 |
|---|---|---|---|---|
| 进料口 | 资料入库管道 | `scripts/kb_intake_pipeline.py` | 半通 | 只搬近7天新增资料，不判重要性 |
| 进料口 | 研究预筛 | `scripts/research_intake_prescreen.py` | 通 | 去重、持仓相关、高价值源兜底 |
| 加工 | 决策生产线 | `scripts/decision_line_build.py` | 骨架 | 生成标的决策卡，Claude 填理解判断 |
| 质检 | 四道闸门 | `scripts/quality_chain_check.py` | 通 | 任一打回不得进 dashboard |
| 出料 | 日报产品 | `00_请先看这里/日报_2026-07-02_四账户完整版.html` | 通 | 已接研究理解背景版 |
| 复盘 | PDCA 复盘位 | `docs/PDCA_REVIEW_FRAMEWORK_V1.md` | 骨架 | 明天起用 |

## 铁律
- 进料与加工脚本只读只生成，不下单，不发布。
- 缺数据标待补，不伪造。
- Claude 理解岗负责“因为→所以”和反方翻盘信号。
- 董事长只看大方向进、成品出，不做流水线质检工。
