# AI投研体系 系统索引 SYSTEM_INDEX V1.0



════════════════════════════════════════

AI投研体系 系统索引 SYSTEM_INDEX V1.0

════════════════════════════════════════



## 唯一入口声明（变更项2）



UNIQUE_ENTRY_POINT : daily_briefing_template_v1.md

UNIQUE_ENTRY_PATH  : AI_Investment_System/docs/daily_briefing_template_v1.md



禁止从以下路径进入系统：

  ✕ 禁止从日报进入

  ✕ 禁止从 Direction Card 进入

  ✕ 禁止从 Risk Card 进入

  ✕ 禁止从 Execution Card 进入

用户必须从唯一入口开始每日决策流程。



## 文件更新时间（变更项4）

SYSTEM_INDEX.md              最后更新: 2026-06-10 21:56:06 JST
daily_briefing_template_v1.md      最后更新: 2026-06-10 21:56:06 JST
trade_record_log_v1.md             最后更新: 2026-06-10 18:24:17 JST
cycle_positioning_engine_v1.md     最后更新: 2026-06-10 21:56:03 JST    状态: 已部署
asset_allocation_engine_v1.md      最后更新: 2026-06-10 21:56:03 JST    状态: 已部署
buy_trigger_engine_v1.md           最后更新: 2026-06-10 21:56:06 JST    状态: 已部署
position_sizing_engine_v1.md       最后更新: 2026-06-10 21:56:06 JST    状态: 已部署
take_profit_system_v1.md           最后更新: 2026-06-10 21:56:06 JST    状态: 已部署

（Codex 写入文件后填入实际修改时间）

## 使用顺序



第1步: 打开 daily_briefing_template_v1.md（唯一入口）

第2步: 首次使用者先读"首次使用说明"（第一页）

第3步: 填写必填字段（约2分钟）

第4步: 按需填写选填字段（约1分钟）

第5步: 完成6步查表，得出第0/1/2行结论

第6步: 按需打开P1引擎文档查表细节

第7步: 交易发生时打开 trade_record_log_v1.md 记录



## P0 文件（MVP，每日必用）



  daily_briefing_template_v1.md  ← 唯一入口，每日第一个打开

  trade_record_log_v1.md         ← 交易发生时记录

  SYSTEM_INDEX.md                ← 本索引文件（首次使用时阅读）



## P1 文件（引擎，查表时按需打开）



  cycle_positioning_engine_v1.md     步骤1 周期定位    状态: 已部署

  asset_allocation_engine_v1.md      步骤2 资产配置    状态: 已部署

  buy_trigger_engine_v1.md           步骤3 买入触发    状态: 已部署

  position_sizing_engine_v1.md       步骤4 仓位计算    状态: 已部署

  take_profit_system_v1.md           步骤5 止盈系统    状态: 已部署


## P2 文件（规范参考，不是操作文件）



  strategy_attribution_system_v1.md  归因系统规范

  daily_decision_briefing_v1.md      简报格式规范



## 文件依赖关系



daily_briefing_template_v1.md（唯一入口）

  步骤1 → cycle_positioning_engine_v1.md

  步骤2 → asset_allocation_engine_v1.md

  步骤3 → buy_trigger_engine_v1.md

  步骤4 → position_sizing_engine_v1.md

  步骤5 → take_profit_system_v1.md

  步骤6 → strategy_attribution_system_v1.md（预警）



trade_record_log_v1.md

  记录格式 → strategy_attribution_system_v1.md

  信号等级 → buy_trigger_engine_v1.md



## P1已部署使用规则



P1引擎未部署时，查表区对应步骤标注：

  "[引擎文档待部署，依据已知规则手动判断]"

  不阻断简报输出，不自动降低置信度。

