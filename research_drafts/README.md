# Research Drafts Directory
# V6投研体系 研报草稿仓库
# 建立时间: 2026-06-16 JST
# 审批人: ChatGPT V6
# SSOT: 本目录为研报草稿唯一可靠输入源（BUG-014修复）

---

## 用途

本目录存放所有V6研报的Markdown草稿正文。

## 为什么用GitHub而不用Drive（BUG-014）

Drive私有文件无法被Codex可靠读取（返回Google登录页/400错误）。
GitHub Raw链接无需认证，100%可靠，是Codex读取研报草稿的唯一正确方式。

## 访问方式

Codex读取研报草稿时，必须使用以下格式的Raw链接：
https://raw.githubusercontent.com/zhuzhiqiang212-rgb/AI-Investment-System-Rules/main/research_drafts/RESEARCH-XXX.md

## 目录结构

| 文件 | 说明 |
|------|------|
| README.md | 本文件，目录说明 |
| RESEARCH-001.md | BOJ议息专题，Published(Beta-1)，已关闭 |
| RESEARCH-001.meta.json | RESEARCH-001元数据 |
| RESEARCH-002.md | MSTR风险处置专题，Published(Beta-1)，已关闭 |
| RESEARCH-002.meta.json | RESEARCH-002元数据 |

## 禁止事项

禁止: 通过Drive文件ID让Codex读取研报内容
禁止: 将Drive私有文件作为Codex的PDF生成输入源
正确: Claude将内容push到本目录 → Codex fetch Raw链接 → 本地生成PDF
