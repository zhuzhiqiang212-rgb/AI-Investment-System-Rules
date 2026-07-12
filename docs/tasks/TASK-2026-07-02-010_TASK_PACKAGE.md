# TASK PACKAGE
# TASK-2026-07-02-010

任务编号: TASK-2026-07-02-010
任务名称: FUTU_CASH_TO_UNIFIED_HOLDINGS（接富途现金字段 → 四账户总资产补全）
提案人: 董事长
执行人: Codex
验收人: Claude（第二质检）→ 董事长终审
类型: 实施类
是否涉及账户操作: 否（只读账户资金信息，不下单、不改单、不碰密码）
是否涉及规则变更: 否
审批状态: APPROVED_BY_USER_IN_THREAD
创建时间: 2026-07-02 18:52:57 JST

---

## 一、目标

通过富途 OpenD 只读接口读取账户现金/资金字段，将富途现金写入
`data/accounts/unified_holdings_latest.json` 的 `cash` 富途条目，并重算 summary 与四账户日报展示。

## 二、执行范围

1. 只读调用 OpenD 账户资金接口（例如 accinfo / get_funds / accinfo_query，Codex 以 SDK 实际可用为准）。
2. 若读到多币种现金（USD/HKD/JPY 等），必须分币种写入，不合并成一个模糊数字。
3. 写入字段至少包括：币种、金额、折 USD、OpenD 字段名、读取时间戳。
4. 更新 `summary.known_cash_usd`、已知总资产、现金展示、现金 pending 标记。
5. 更新四账户日报 §9 富途现金、§3 顶部已知总资产和现金合计。

## 三、铁律

- 只读，不下单、不改单、不取消订单、不保存密码。
- OpenD 没连上或字段读不出：富途现金保持“待补”，不填 0、不用别的账户估、不伪造。
- UTF-8 写入；每个文件写完必须重读确认无乱码。
- 回报必须贴：OpenD 是否连上；原始数字+币种+OpenD字段名+时间戳；新的已知总资产及较 $1,714,301 增量；失败则说明卡点。

## 四、预计产出

- `docs/tasks/TASK-2026-07-02-010_TASK_PACKAGE.md`
- `data/accounts/unified_holdings_latest.json`
- `00_请先看这里/日报_2026-07-02_四账户完整版.html`
- `reports/validation/TASK-2026-07-02-010_futu_cash_validation.md`
