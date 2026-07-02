# 报表生产链路规则
# 生效时间：2026-06-17 JST
# 状态：永久有效

## 正式规则

Claude输出：Markdown / JSON / 表格数据（纯文字）
Codex本机执行：生成PNG + PDF
输出到：C:\AI_Investment_System\reports\daily_report\

## 禁止链路

禁止：Claude生成PNG → Codex复制
禁止：依赖 Downloads
禁止：依赖 OneDrive
禁止：依赖 Google Drive下载
禁止：依赖 Claude附件下载

## 正确流程

1. Claude读Drive → 分析 → 输出JSON数据
2. Codex收到JSON → 本机运行Python → 生成PDF+PNG
3. 输出到 C:\AI_Investment_System\reports\daily_report\
4. 文件名 00_开头 → 排在旧文件夹第一个
5. PNG可直接微信转发
