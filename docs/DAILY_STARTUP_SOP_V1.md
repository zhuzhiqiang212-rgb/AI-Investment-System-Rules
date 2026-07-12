# 每日开机流程 SOP V1

本流程把世界观证据链放在每日生产第一位。持仓只接受审查，不作为推导起点。

| 步骤 | 名称 | 输入 | 输出 | 自动或人 | 对应脚本 |
|---|---|---|---|---|---|
| ⓪ | 复盘昨天 | 昨日求证表、昨日决策卡、今日行情 | 每日复盘骨架 | 自动取数，人判归因 | scripts/daily_review.py |
| ① | 进料 | 资料库、行情源、研究源 | 入库与候选资料 | 自动 | scripts/kb_intake_pipeline.py、scripts/research_intake_prescreen.py |
| ② | 填当日求证表 | 今日事实与来源 | data/evidence_chain/daily_YYYYMMDD.json | 人 | docs/EVIDENCE_CHAIN_DAILY_TEMPLATE_V1.md |
| ③ | 机会发现 | 当日求证表、行情板块 | 链驱动机会池 | 自动 | scripts/opportunity_chain_driven.py |
| ④ | 日报上半截 | 当日求证表 | 第1至第7层结构 | 自动 | scripts/daily_upper_from_chain.py |
| ⑤ | 审持仓 | 当日求证表、统一持仓库 | 持仓符合性对照 | 自动 | scripts/holdings_review_against_chain.py |
| ⑥ | 填决策卡 | 机会池、持仓审查、研究理解 | 标的决策卡 | 人 | data/decisions/decision_cards_YYYYMMDD.json |
| ⑦ | 四闸门 | 日报、统一持仓库 | PASS或打回 | 自动 | scripts/quality_chain_check.py |
| ⑧ | 组装日报 | 上半截、决策卡、风险、复盘靶子 | 正式日报 | 人机协作 | 日报渲染脚本 |
| ⑨ | 董事长签字 | 正式日报与闸门结果 | 终审确认 | 人 | 董事长终审 |
| ⑩ | 存档供复盘 | 求证表、决策卡、日报、闸门结果 | 历史档案 | 自动 | data/evidence_chain、data/decisions、reports |
| ⑪ | 周月季年复盘 | 历史档案 | 分层复盘与体系迭代 | 到点触发，人判 | docs/PDCA_REVIEW_FRAMEWORK_V2.md |

执行铁律：第②步未完成时，不得跑③④⑤⑦；任何自动脚本不得下单、不得发布、不得补写事实。
