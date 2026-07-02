# 资料增量处理机制 V1

## 固定入口
新增资料统一放入：G:\我的云端硬盘\AI_Investment_System\inbox\

## 验资料扫描范围
只扫描 inbox，不再扫描整个 Drive。

## 处理后归档
处理完成后自动移动到：G:\我的云端硬盘\AI_Investment_System\processed\YYYY-MM-DD\

## 去重规则
已处理资料必须写入：G:\我的云端硬盘\AI_Investment_System\system\processed_manifest.json

如果文件已经在 manifest 里，禁止重复处理。

## 历史路径
湖水资讯、老雷财经、reports、daily 只作为历史路径，不作为新增资料入口。

## Google Docs / .gdoc 读取规则

1. 如果 inbox 里是 `.gdoc` 文件，不得按本地普通文本路径读取。
2. 必须优先通过 Google Drive 云端方式读取 Google Docs 正文或导出正文。
3. 如果当前本地环境无法读取 Google Docs 正文，必须明确要求用户将 Google Docs 导出为 PDF / TXT / DOCX 后重新放入 inbox。
4. `.gdoc` 不得误判为资料丢失。
5. `.gdoc` 不得删除；无法读取时只标记读取失败，并说明原因。
6. `.gdoc` 正文未读取成功前，不得进入日报结论或账户动作。

## 图片型 PDF 读取规则

1. PDF 必须先检测文本层。
2. 如果有文本层，提取文字。
3. 如果没有文本层，标记为图片型 PDF，需要 OCR 或用户上传给 ChatGPT 人工判断。
4. 未读取正文的图片型 PDF 不得进入日报结论。
