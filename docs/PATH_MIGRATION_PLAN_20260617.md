# PATH_MIGRATION_REPORT.md
# AI投研总控台 文件系统迁移方案
# 生成时间：2026-06-17 JST

## 迁移目标

迁移前：C:\Users\zhu20\OneDrive\桌面\股票分析与研究（OneDrive同步，导致冲突卡顿）
迁移后：C:\AI_Investment_System（本地路径，桌面保留快捷方式入口）

## 新目录结构

C:\AI_Investment_System\
├── reports\daily_report\   ← 00_今日日报
├── reports\trade_record\   ← 执行卡记录
├── research\               ← RESEARCH-001~004
├── docs\                   ← 制度文件
├── archive\                ← 旧版归档
├── scripts\                ← auto_briefing.py
├── data\                   ← 持仓快照JSON
├── path_config.json        ← 路径配置（所有脚本读此）
└── PATH_MIGRATION_REPORT.md

## 禁止输出路径

禁止：C:\Users\zhu20\OneDrive\桌面\
禁止：C:\Users\zhu20\Documents\
允许：C:\AI_Investment_System\（及子目录）

## Codex执行指令

1. 下载 path_migration.py 到 C:\temp\
2. 以管理员身份运行：python C:\temp\path_migration.py
3. 确认 C:\AI_Investment_System\ 已创建
4. 双击桌面"股票分析与研究"快捷方式验证
5. 不删除旧路径数据

## 仍依赖OneDrive

- Google Drive：不受影响
- 历史PDF/MD：手动归档到 archive\
- GitHub：如在OneDrive下需重新clone
