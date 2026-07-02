# 数据缺口阻断检查

更新时间：2026-06-06 14:42:17 +09:00

| 检查项 | 当前结果 | 是否红色阻断 | 原因 | 处理动作 |
| --- | ---- | ------ | -- | ---- |
| 是否有关键行情缺口未降级 | NO | NO | 行情缺失已按黄色降级，缺价格不输出确定动作 | 持续写入latest_market_validation和PDCA |
| 是否有关键宏观缺口未降级 | NO | NO | 无稳定源宏观项已降级为背景/事件状态 | 进入明日宏观PDCA |
| 是否有账户数据缺失但输出动作 | NO | NO | 四账户动作卡加入缺口触发器，缺持仓/现金/成本不输出确定动作 | 保持结构参考与人工复核 |
| 是否有资金流C级代理被当作A/B级 | NO | NO | 资金流与ETF Flow规则明确C级代理不得单独改变动作 | 维持C级辅助提示 |
| 是否有旧快照被当作当前数据 | NO | NO | 旧快照规则已建立，旧快照不进入当前价主表 | 持续价格现实检查 |
| 是否有START_HERE入口异常 | NO | NO | START_HERE显示当前任务与数据缺口入口 | 每日写回检查 |
| 是否有dashboard入口异常 | NO | NO | readable_dashboard已加入数据缺口提示 | 入口一致性复核 |
| 是否有JSON状态冲突 | NO | NO | master_task_status与evidence_chain_status保持一致 | daily_writeback_check |
| 是否有next_task NONE异常 | NO | NO | 当前next_task为P1-027，不是NONE | 禁止未收口时显示NONE |
| 是否有未验收任务被标绿 | NO | NO | P1-027保持yellow / pending_validation | 等待ChatGPT验收 |

