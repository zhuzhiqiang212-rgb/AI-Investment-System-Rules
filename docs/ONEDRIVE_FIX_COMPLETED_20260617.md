# OneDrive故障修复记录
# 日期：2026-06-17 JST
# 状态：已解决

## 问题描述
- Windows桌面被OneDrive接管，股票分析与研究文件夹在OneDrive同步路径下
- OneDrive长期同步错误，导致资源管理器卡顿、删除异常、预览异常
- 快捷方式曾错误指向 G:\我的云端硬盘\AI_Investment_System（Google Drive盘符）

## 修复过程
1. 创建 C:\AI_Investment_System 及子目录结构
2. 写入 path_config.json，所有脚本改从此文件读取输出路径
3. 删除错误快捷方式（指向G盘）
4. 重建正确快捷方式（指向C:\AI_Investment_System）
5. 用户彻底删除OneDrive

## 最终状态
- 新路径：C:\AI_Investment_System
- 桌面快捷方式：正确指向 C:\AI_Investment_System（IsCorrect: True）
- OneDrive：已删除，同步冲突彻底消除
- 所有历史数据：未删除，保留原位

## 路径规则（生效）
- 允许输出：C:\AI_Investment_System\
- 禁止输出：任何OneDrive路径（OneDrive已不存在）
- Google Drive：不受影响，继续正常使用

## 关闭条件
用户确认双击快捷方式可正常打开 C:\AI_Investment_System
