# 数据缺口补数据路径

更新时间：2026-06-06 14:42:17 +09:00

| 缺口类别 | 用户应该补什么 | 放到哪里 | 文件命名建议 | Codex怎么读取 | ChatGPT怎么验收 |
| ---- | ------- | ---- | ------ | --------- | ----------- |
| 行情数据 | latest_market_validation.md / market_source_stability_check.md | G:\我的云端硬盘\AI_Investment_System\data\market\ | latest_market_validation_YYYY-MM-DD.md | 读取公开延迟行情校验文件，缺失则标数据不足 | 上传 validation 包，核对核心标的和旧快照降级 |
| 宏观数据 | macro_to_account_action_map.md / macro_risk_dashboard.md / macro_signal_invalidation_rules.md | G:\我的云端硬盘\AI_Investment_System\reports\macro\ 或 inputs\ | macro_latest_YYYY-MM-DD.md | 读取宏观映射、风险灯号与失效条件 | 核对是否每个宏观变量都有动作边界 |
| ETF Flow / 资金流 | etf_flow_source_rules.md / latest_etf_flow_check.md / latest_fund_flow_source_check.md | G:\我的云端硬盘\AI_Investment_System\reports\flow\ | latest_etf_flow_check_YYYY-MM-DD.md | 读取ETF Flow和资金流检查，C级代理降级 | 核对A/B/C/D分级和不得单独触发动作 |
| 财报三指标 | 财报PDF / 公司财报摘要 / fundamental_three_metrics_cards.md | G:\我的云端硬盘\AI_Investment_System\inbox\ 或 reports\fundamental\ | ticker_财报_YYYYQX.pdf | 提取FCF、资产负债表、毛利率；失败则标数据不足 | 核对三指标卡是否不编造数字 |
| 护城河 | moat_score_cards.md / moat_score_summary.md | G:\我的云端硬盘\AI_Investment_System\reports\rotation\ | moat_score_cards_YYYY-MM-DD.md | 读取护城河评分卡和摘要 | 核对评分维度、动作含义和失效条件 |
| 账户快照 | 用户账户截图 / latest_account_snapshot.md / account_action_matrix.md | G:\我的云端硬盘\AI_Investment_System\inbox\ 或 reports\accounts\ | 账户名_YYYY-MM-DD.png 或 latest_account_snapshot.md | 优先读取人工确认快照；截图只作参考入库 | 核对是否仅作结构参考、人工确认后执行 |
| 湖水资讯 | inputs/hushui_latest_input.txt / inbox/hushui* | G:\我的云端硬盘\AI_Investment_System\inbox\ 或 inputs\ | hushui_YYYY-MM-DD.txt/pdf/docx | 读取txt/pdf/docx；gdoc需云端导出，否则失败记录 | 核对提取内容是否进入证据链/PDCA |
| 老雷财经 | inputs/laolei_latest_input.txt / inbox/laolei* | G:\我的云端硬盘\AI_Investment_System\inbox\ 或 inputs\ | laolei_YYYY-MM-DD.txt/pdf/docx | 读取txt/pdf/docx；gdoc指针不本地读取 | 核对失败日志和是否避免猜正文 |
| 用户直接文本 | manual_text_latest.md | G:\我的云端硬盘\AI_Investment_System\inputs\ | manual_text_latest.md | 直接读取文本并标注来源为用户直接文本 | 核对是否只作为观点/纪律，不当交易指令 |
| PDF/截图/视频 | inbox_extracted / validation失败日志 | G:\我的云端硬盘\AI_Investment_System\inbox\ 或 inputs\ | source_YYYY-MM-DD.pdf/png/txt | PDF有文本层则提取；图片型PDF/OCR失败则记录失败 | 核对 failed_materials_log 和用户需补文件 |
| 入口状态 | START_HERE.html / readable_dashboard.html / dashboard入口检查文件 | G:\我的云端硬盘\AI_Investment_System\ | START_HERE.html | 检查唯一入口、按钮、next_task、latest优先 | 核对用户从唯一入口能看到最新状态 |

