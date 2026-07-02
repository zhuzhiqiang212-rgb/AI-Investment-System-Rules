# 报表生产链路规则 V1.0（正式版）
# 生效时间：2026-06-17 JST
# 状态：已验收通过，永久有效

## 正式流程（已验证可行）

1. Claude读Drive → 分析 → 输出JSON数据（纯文字）
2. Codex收到JSON → 本机运行Python → 生成PDF+PNG
3. 输出到 C:\AI_Investment_System\reports\daily_report\
4. 文件名 00_ 开头 → 排在旧文件夹第一个
5. PNG可直接微信转发

## 禁止链路（永久禁止）

禁止：Claude生成PNG → Codex复制
禁止：依赖 Downloads
禁止：依赖 OneDrive
禁止：依赖 Google Drive下载
禁止：依赖 Claude附件下载

## 今日验收记录（2026-06-17）

PDF: C:\AI_Investment_System\reports\daily_report\00_今日研报_20260617.pdf  160KB
PNG: C:\AI_Investment_System\reports\daily_report\00_今日研报_20260617.png  588KB
中文内容显示正常：YES
未删除数据：YES
未自动下单：YES

## 注意事项

- pdftoppm/magick不可用时，Codex用同一DATA数据直接渲染PNG
- Codex执行时需设置 PYTHONIOENCODING=utf-8
- 字体优先：msyh.ttc → simsun.ttc → simhei.ttf
