# 报表生产链路规则 V1.1（修订版）
# 生效时间：2026-06-17 JST
# 修订原因：报表只放新路径，用户在旧文件夹看不到

## 正式流程

1. Claude读Drive → 分析 → 输出JSON数据
2. Codex本机生成PDF+PNG
3. 输出到两个位置（缺一不可）：
   - C:\AI_Investment_System\reports\daily_report\（新路径存档）
   - C:\Users\zhu20\OneDrive\桌面\股票分析与研究\（旧文件夹，用户可见）
4. 文件名 00_ 开头 → 排在旧文件夹第一个
5. PNG可直接微信转发

## 禁止链路

禁止：Claude生成PNG → Codex复制
禁止：依赖 Downloads / OneDrive同步 / Google Drive下载 / Claude附件

## 验收标准

□ 旧文件夹第一个位置：00_今日研报_YYYYMMDD.png
□ 旧文件夹第一个位置：00_今日研报_YYYYMMDD.pdf
□ 新路径同时存档
□ 图片内容中文显示正常
□ 可微信转发
