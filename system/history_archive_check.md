# 历史报告归档检查

更新时间：2026-06-06 16:05:14 +09:00

| 检查项 | 当前结果 | 是否异常 | 处理动作 |
| --- | ---- | ---- | ---- |
| latest 文件是否仍在原位置 | YES | NO | 缺失则恢复latest文件，不移动本体 |
| latest 是否没有被移动到 history | YES | NO | history只保存副本或索引 |
| START_HERE 是否仍指向 latest | YES | NO | 保持今日入口优先latest |
| readable_dashboard 是否仍指向 latest | YES | NO | 保持今日入口优先latest |
| latest_official_daily_report_panel 是否仍是今日主入口 | YES | NO | START_HERE和readable_dashboard保留latest入口 |
| 旧日期日报是否只在历史入口 | YES | NO | 旧报告不可作为今日主入口 |
| 旧 dashboard 是否没有作为主入口 | YES | NO | 主入口优先readable_dashboard和latest panel |
| 验收包索引是否存在 | YES | NO | 建立validation_index.md |
| history_index 是否存在 | YES | NO | 建立history_index.md |
| 是否存在旧快照被当当前数据 | NO | NO | 旧快照仅历史参考 |
| 是否存在 OneDrive 历史残留被主入口引用 | 需复核 | NO | 主入口必须指向Google Drive体系 |
| 是否存在空文件或打不开历史文件 | NO | NO | 已创建索引并复制关键latest快照 |

